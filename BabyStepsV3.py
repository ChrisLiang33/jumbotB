"""
BabyStepsV3 — gait built around the measured safe pitch range.

From PitchRangeTest the safe body-frame pitch range for each leg is:
    PITCH_MIN = -5 deg  (backward)
    PITCH_MAX = +25 deg (forward)
    Center    = +10 deg (the body wants to lean forward 10 deg)
    Amplitude = +/- 15 deg around center

The gait commands hip pitch in BODY-FRAME degrees and converts to motor
angles using the mirroring convention (motor 1 forward = +, motor 6 forward = -).
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
# V3 GAIT KNOBS — all in BODY-FRAME degrees
# ============================================================
WALK_SPEED      = 1.2

# --- HIP PITCH RANGE (the measured safe envelope) ---
# Each leg's body-frame angle stays within [PITCH_MIN, PITCH_MAX].
PITCH_MIN       = -5     # back limit  (set by PitchRangeTest)
PITCH_MAX       = +25    # forward limit (set by PitchRangeTest)

# --- ASYMMETRY: where the leg sits during stance vs swing ---
# Within the safe envelope, you can bias the swing-vs-stance position.
# Defaults below put each leg's full 30 deg of swing inside [-5, +25]:
#   stance leg (planted, pushing back) = PITCH_MIN
#   swing  leg (in the air, going forward) = PITCH_MAX
# To bias more time forward: raise both. To bias backward: lower both.
SWING_PITCH     = +25    # body-frame angle when the leg is at peak forward (in air)
STANCE_PITCH    = -5     # body-frame angle when the leg is at peak backward (push-off)

# --- foot lift (knee bend during swing — no ankle, so this is critical) ---
# Hand-walked data showed leg 1 knee bending up to 60 deg from home.
# Using 40 here as a comfortable cyclic equivalent.
LIFT_AMOUNT     = 40
LIFT_LEAD       = math.pi / 4   # lift leads the swing peak by 45 deg

# --- stance extension (the "fake ankle" — extends leg during stance) ---
# Hand-walked data showed support knee locked at +30 from home.
# This is the main forward-propulsion mechanism without an ankle.
STANCE_EXTEND   = 25

# --- lateral sway ---
SWAY_AMOUNT     = 6

# --- hip yaw oscillation ---
# Hand-walked data showed both yaws swinging together with ~25 deg total range.
# Synchronized (both legs same phase), oscillates with the gait.
YAW_AMOUNT      = 10
# ============================================================

# Derived: center and amplitude in body frame
PITCH_CENTER = (SWING_PITCH + STANCE_PITCH) / 2.0   # 10 with defaults
PITCH_AMP    = (SWING_PITCH - STANCE_PITCH) / 2.0   # 15 with defaults

print(f"Body-frame pitch envelope: [{PITCH_MIN}, {PITCH_MAX}]")
print(f"Gait center: {PITCH_CENTER:+.1f} deg, amplitude: ±{PITCH_AMP:.1f} deg")
print(f"Each leg will swing in body frame from {PITCH_CENTER - PITCH_AMP:+.1f} to {PITCH_CENTER + PITCH_AMP:+.1f}")

print("Starting baby steps V3 (Ctrl+C to stop)...")
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
        # leg 1 oscillates between SWING_PITCH (when sin > 0, swinging forward)
        # and STANCE_PITCH (when sin < 0, pushing back).
        # leg 2 is mirrored half-cycle later.
        s = math.sin(phase)
        leg1_pitch_bf = PITCH_CENTER + s * PITCH_AMP
        leg2_pitch_bf = PITCH_CENTER - s * PITCH_AMP   # mirrored phase

        # Clamp to safety envelope (defensive — should already be inside)
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
        safe_move(hip_pitch1, 1, hip1_pitch_angle, move_time=100)
        safe_move(leg1,       2, leg1_angle,       move_time=100)
        safe_move(hip_yaw1,   3, hip1_yaw_angle,   move_time=50)
        safe_move(hip_roll1,  4, hip1_roll_angle,  move_time=50)

        safe_move(leg2,       5, leg2_angle,       move_time=100)
        safe_move(hip_pitch2, 6, hip2_pitch_angle, move_time=100)
        safe_move(hip_yaw2,   7, hip2_yaw_angle,   move_time=50)
        safe_move(hip_roll2,  8, hip2_roll_angle,  move_time=50)

        time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nStopping motors safely...")
        homing()
        break
