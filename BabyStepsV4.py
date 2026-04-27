"""
BabyStepsV4 — small fast steps to minimize single-leg airborne time.

Philosophy: instead of bigger strides (which give the body time to tip over
during single-leg support), take tiny rapid shuffles. Each leg is in the
air for as little time as possible. The robot stays close to double-support
most of the cycle.

All other geometry (sign convention, body-frame envelope, lift-leads-swing)
is inherited from V3.
"""

from pylx16a.lx16a import *
import time
import math

LX16A.initialize('/dev/ttyUSB0')

def connect_servo(id):
    try:
        return LX16A(id)
    except ServoTimeoutError:
        print(f"Servo {id} is not responding. Exiting.")
        exit()

# --- LEG 1 (Right) ---
hip_pitch1 = connect_servo(1)
leg1       = connect_servo(2)
hip_yaw1   = connect_servo(3)
hip_roll1  = connect_servo(4)

# --- LEG 2 (Left) ---
leg2       = connect_servo(5)
hip_pitch2 = connect_servo(6)
hip_yaw2   = connect_servo(7)
hip_roll2  = connect_servo(8)

LIMITS = {
    1: (10, 125), 2: (0, 160),  3: (20, 200), 4: (25, 165),
    5: (70, 230), 6: (110, 225), 7: (25, 203), 8: (70, 210),
}

HOME = {
    1: 40, 2: 120, 3: 115, 4: 120,
    5: 115, 6: 195, 7: 120, 8: 115,
}

# Sign convention determined from hand-walked CapturePoses data:
# motor 1 DECREASES  -> leg 1 forward in body frame
# motor 6 INCREASES  -> leg 2 forward in body frame
PITCH_FORWARD_SIGN = {1: -1, 6: +1}

def safe_move(motor_obj, motor_id, target_angle, move_time=50):
    min_angle, max_angle = LIMITS[motor_id]
    safe_angle = max(min_angle, min(target_angle, max_angle))
    motor_obj.move(safe_angle, time=move_time)

def homing(move_time=2000):
    safe_move(leg1,       2, HOME[2], move_time=move_time)
    safe_move(hip_pitch1, 1, HOME[1], move_time=move_time)
    safe_move(hip_yaw1,   3, HOME[3], move_time=move_time)
    safe_move(hip_roll1,  4, HOME[4], move_time=move_time)
    safe_move(leg2,       5, HOME[5], move_time=move_time)
    safe_move(hip_pitch2, 6, HOME[6], move_time=move_time)
    safe_move(hip_yaw2,   7, HOME[7], move_time=move_time)
    safe_move(hip_roll2,  8, HOME[8], move_time=move_time)
    time.sleep(2.5)

print("Moving to home position safely...")
homing()

# ============================================================
# V4 GAIT KNOBS  --  small + fast philosophy
# ============================================================
WALK_SPEED      = 4.5    # ~1.4s per full cycle, ~0.7s per leg in air
                         # (V3 was 2.5 -> ~1.25s air time. V4 ~halves that.)

# --- HIP PITCH (small swing range) ---
PITCH_MIN       = -3     # tiny back push
PITCH_MAX       = +12    # tiny forward swing

# Where the leg sits at the extremes of its motion:
SWING_PITCH     = +12    # forward extreme
STANCE_PITCH    = -3     # backward extreme

# --- foot lift (small knee bend, just enough to clear) ---
LIFT_AMOUNT     = 15     # was 40 in V3 -- huge bend isn't needed for tiny steps
LIFT_LEAD       = math.pi / 4   # lift leads swing peak by 45 deg

# --- stance extension (gentle push-off, dialed back since steps are smaller) ---
STANCE_EXTEND   = 10

# --- lateral sway ---
SWAY_AMOUNT     = 4      # small, since steps are quick

# --- hip yaw oscillation ---
YAW_AMOUNT      = 3      # small yaw nudge

# --- servo move time ---
MOVE_TIME       = 50     # was 100 in V3 -- snappier tracking for fast cycle
# ============================================================

# Derived: center and amplitude in body frame
PITCH_CENTER = (SWING_PITCH + STANCE_PITCH) / 2.0   # 4.5 with defaults
PITCH_AMP    = (SWING_PITCH - STANCE_PITCH) / 2.0   # 7.5 with defaults

print(f"Body-frame pitch envelope: [{PITCH_MIN}, {PITCH_MAX}]")
print(f"Gait center: {PITCH_CENTER:+.1f} deg, amplitude: ±{PITCH_AMP:.1f} deg")
print(f"Cycle period: {2 * math.pi / WALK_SPEED:.2f}s")
print(f"Single-leg airborne time per cycle: ~{math.pi / WALK_SPEED:.2f}s")
print()

print("Starting baby steps V4 (small + fast). Ctrl+C to stop...")
start_time = time.time()

while True:
    try:
        elapsed = time.time() - start_time
        phase = elapsed * WALK_SPEED

        # --- LIFT (knee bend, leads swing) ---
        lift_signal1 = math.sin(phase + LIFT_LEAD)
        lift_signal2 = math.sin(phase + LIFT_LEAD + math.pi)
        lift_wave1 = max(0, lift_signal1) * LIFT_AMOUNT
        lift_wave2 = max(0, lift_signal2) * LIFT_AMOUNT

        # --- STANCE EXTEND (when other leg is lifted, this leg pushes up) ---
        stance_extend1 = max(0, lift_signal2) * STANCE_EXTEND
        stance_extend2 = max(0, lift_signal1) * STANCE_EXTEND

        # --- HIP PITCH in BODY-FRAME degrees ---
        s = math.sin(phase)
        leg1_pitch_bf = PITCH_CENTER + s * PITCH_AMP
        leg2_pitch_bf = PITCH_CENTER - s * PITCH_AMP   # mirrored

        # safety clamp to user-tested envelope
        leg1_pitch_bf = max(PITCH_MIN, min(PITCH_MAX, leg1_pitch_bf))
        leg2_pitch_bf = max(PITCH_MIN, min(PITCH_MAX, leg2_pitch_bf))

        # --- SWAY ---
        sway_wave = math.cos(phase) * SWAY_AMOUNT

        # --- YAW (both legs synchronized, in phase with the swing) ---
        yaw_wave = math.sin(phase) * YAW_AMOUNT

        # --- CONVERT body-frame pitch to motor angles ---
        hip1_pitch_angle = HOME[1] + PITCH_FORWARD_SIGN[1] * leg1_pitch_bf
        hip2_pitch_angle = HOME[6] + PITCH_FORWARD_SIGN[6] * leg2_pitch_bf

        leg1_angle       = HOME[2] - lift_wave1 + stance_extend1
        leg2_angle       = HOME[5] - lift_wave2 + stance_extend2

        hip1_yaw_angle   = HOME[3] + yaw_wave
        hip1_roll_angle  = HOME[4] + sway_wave
        hip2_yaw_angle   = HOME[7] + yaw_wave
        hip2_roll_angle  = HOME[8] + sway_wave

        # Apply
        safe_move(hip_pitch1, 1, hip1_pitch_angle, move_time=MOVE_TIME)
        safe_move(leg1,       2, leg1_angle,       move_time=MOVE_TIME)
        safe_move(hip_yaw1,   3, hip1_yaw_angle,   move_time=MOVE_TIME)
        safe_move(hip_roll1,  4, hip1_roll_angle,  move_time=MOVE_TIME)

        safe_move(leg2,       5, leg2_angle,       move_time=MOVE_TIME)
        safe_move(hip_pitch2, 6, hip2_pitch_angle, move_time=MOVE_TIME)
        safe_move(hip_yaw2,   7, hip2_yaw_angle,   move_time=MOVE_TIME)
        safe_move(hip_roll2,  8, hip2_roll_angle,  move_time=MOVE_TIME)

        time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nStopping motors safely...")
        homing()
        break
