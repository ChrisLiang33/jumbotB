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
    1: (10, 125),   # Hip Pitch 1
    2: (0, 160),    # Leg 1
    3: (20, 200),   # Hip Yaw 1
    4: (25, 165),   # Hip Roll 1
    5: (70, 230),   # Leg 2
    6: (110, 225),  # Hip Pitch 2
    7: (25, 203),   # Hip Yaw 2
    8: (70, 210)    # Hip Roll 2
}

def safe_move(motor_obj, motor_id, target_angle, move_time=50):
    min_angle, max_angle = LIMITS[motor_id]
    safe_angle = max(min_angle, min(target_angle, max_angle))
    motor_obj.move(safe_angle, time=move_time)

home_time = 2000

def homing():
    safe_move(leg1,       2, 120, move_time=home_time)
    safe_move(hip_pitch1, 1, 40,  move_time=home_time)
    safe_move(hip_yaw1,   3, 115, move_time=home_time)
    safe_move(hip_roll1,  4, 120, move_time=home_time)
    safe_move(leg2,       5, 115, move_time=home_time)
    safe_move(hip_pitch2, 6, 195, move_time=home_time)
    safe_move(hip_yaw2,   7, 120, move_time=home_time)
    safe_move(hip_roll2,  8, 115, move_time=home_time)
    time.sleep(2.5)

print("Moving to home position safely...")
homing()

# ============================================================
# V2 GAIT TUNING KNOBS  --  edit these and re-run
# ============================================================
WALK_SPEED      = 1.2    # slower so leg servo can track under load

# --- foot lift (knee bends to lift foot) ---
# With NO ankle joint, the knee is the only way to clear the foot.
# Needs to be big enough to actually lift foot off the floor.
LIFT_AMOUNT     = 25     # knee bend during swing (was 12 - barely visible)
LIFT_LEAD       = math.pi / 4   # lift peaks 45 deg BEFORE swing peak

# --- hip pitch (heavily biased toward back, almost no forward kick) ---
# The robot was kicking its leg up forward too much. Range should mostly
# be on the BACK side of neutral. Forward swing is just enough to clear
# foot to its next plant location.
STRIDE_FORWARD  = 5      # tiny forward swing — no more "kicking to the sky"
STRIDE_BACK     = 18     # bigger back push — most of the range is here

# --- TORSO LEAN (shifts entire pitch range further backward) ---
# A positive value rotates both legs backward in body frame.
# Equivalent to leaning the torso forward over the feet.
# Effective leg pitch range becomes: [-(STRIDE_BACK + TORSO_LEAN), +(STRIDE_FORWARD - TORSO_LEAN)]
# With current values: [-32, -7] -- legs always behind neutral. Good!
TORSO_LEAN      = 14     # shift the whole pitch range backward

# --- stance extension (the "fake ankle push-off") ---
# With the pitch range shifted way back, this carries even more of the
# forward propulsion. Keep moderate to avoid foot slipping backward.
STANCE_EXTEND   = 12

# --- forward bias on support leg ---
SUPPORT_BIAS    = 2      # subtle — TORSO_LEAN does most of the work now

# --- lateral sway (weight shift) ---
SWAY_AMOUNT     = 6      # slightly more to ensure weight transfers to support leg
# ============================================================

print("Starting baby steps V2 (Ctrl+C to stop)...")
start_time = time.time()

while True:
    try:
        elapsed = time.time() - start_time
        phase = elapsed * WALK_SPEED
        s = math.sin(phase)

        # === LIFT — peaks LIFT_LEAD radians BEFORE the swing peak ===
        # leg 1 lifts during sin(phase + LIFT_LEAD) > 0
        # leg 2 lifts on the opposite half cycle
        lift_signal1 = math.sin(phase + LIFT_LEAD)
        lift_signal2 = math.sin(phase + LIFT_LEAD + math.pi)
        lift_wave1 = max(0, lift_signal1) * LIFT_AMOUNT
        lift_wave2 = max(0, lift_signal2) * LIFT_AMOUNT

        # === STANCE EXTEND — when the OTHER leg is lifted, this leg pushes up slightly ===
        stance_extend1 = max(0, lift_signal2) * STANCE_EXTEND  # leg 1 extends when leg 2 swings
        stance_extend2 = max(0, lift_signal1) * STANCE_EXTEND  # leg 2 extends when leg 1 swings

        # === HIP PITCH — asymmetric forward/back amplitude ===
        # s > 0: leg 1 swings forward, leg 2 pushes back (in body frame, accounting for mirror)
        # s < 0: leg 2 swings forward, leg 1 pushes back
        if s > 0:
            pitch_wave = s * STRIDE_FORWARD   # leg 1 forward swing
        else:
            pitch_wave = s * STRIDE_BACK      # leg 1 back push (and leg 2 forward swing)

        # === SUPPORT BIAS — extra back-push on whichever leg is the support ===
        # motor 1: smaller angle = leg 1 backward in body frame  -> bias is NEGATIVE
        # motor 6: larger angle  = leg 2 backward in body frame  -> bias is POSITIVE (mirrored)
        if s < 0:   # leg 1 is the support
            pitch_bias1 = -SUPPORT_BIAS
            pitch_bias2 = 0
        else:       # leg 2 is the support
            pitch_bias1 = 0
            pitch_bias2 = +SUPPORT_BIAS

        # === SWAY ===
        sway_wave = math.cos(phase) * SWAY_AMOUNT

        # === APPLY ===
        # TORSO_LEAN: subtract from leg 1 motor (smaller angle = leg back in body frame),
        #             add to leg 2 motor (larger angle = leg back in body frame, since mirrored).
        # Both legs rotate backward in body frame -> torso effectively leans forward.
        hip1_pitch_angle = 40  + pitch_wave + pitch_bias1 - TORSO_LEAN
        leg1_angle       = 120 - lift_wave1 + stance_extend1
        hip1_yaw_angle   = 115
        hip1_roll_angle  = 120 + sway_wave

        hip2_pitch_angle = 195 + pitch_wave + pitch_bias2 + TORSO_LEAN
        leg2_angle       = 115 - lift_wave2 + stance_extend2
        hip2_yaw_angle   = 120
        hip2_roll_angle  = 115 + sway_wave

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
