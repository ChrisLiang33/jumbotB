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
WALK_SPEED      = 1.5    # cycle rate (V1 was 3.0). slower = less dynamic kickback.

# --- foot lift ---
LIFT_AMOUNT     = 12     # how much the knee bends to lift the foot (V1 was 30).
                         # smaller = less squat + less foot tilt (no ankle joint!)
LIFT_LEAD       = math.pi / 4   # lift peaks BEFORE swing peak (45 deg early).
                                # this lets the foot rise before it swings forward.

# --- hip pitch (asymmetric: push back harder than swing forward) ---
STRIDE_FORWARD  = 15     # forward swing amplitude (swing leg through air)
STRIDE_BACK     = 22     # backward push amplitude (stance leg propelling body)
                         # STRIDE_BACK > STRIDE_FORWARD biases body forward each cycle.

# --- stance extension (counter the squat) ---
STANCE_EXTEND   = 5      # extra leg extension on the support leg.
                         # keeps body height steady during single-leg stance.

# --- forward bias on support leg (counter backward tip) ---
SUPPORT_BIAS    = 3      # extra back-push degrees on whichever leg is the support.
                         # actively pushes torso forward each step.

# --- lateral sway ---
SWAY_AMOUNT     = 5      # weight shift side to side
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
        hip1_pitch_angle = 40  + pitch_wave + pitch_bias1
        leg1_angle       = 120 - lift_wave1 + stance_extend1
        hip1_yaw_angle   = 115
        hip1_roll_angle  = 120 + sway_wave

        hip2_pitch_angle = 195 + pitch_wave + pitch_bias2
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
