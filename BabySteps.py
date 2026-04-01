from pylx16a.lx16a import *
import time

# Initialize the serial connection
LX16A.initialize('/dev/ttyUSB0')

def connect_servo(id):
    try:
        return LX16A(id)
    except ServoTimeoutError:
        print(f"Servo {id} is not responding. Exiting.")
        exit()

# --- LEG 1 ---
motor1 = connect_servo(1)  # Leg
motor2 = connect_servo(2)  # Hip Pitch
motor3 = connect_servo(3)  # Hip Yaw
motor4 = connect_servo(4)  # Hip Roll

# --- LEG 2 ---
motor5 = connect_servo(5)  # Leg
motor6 = connect_servo(6)  # Hip Pitch
motor7 = connect_servo(7)  # Hip Yaw
motor8 = connect_servo(8)  # Hip Roll

# --- TESTED SAFETY LIMITS ---
LIMITS = {
    1: (85, 235),   # Leg
    2: (95, 190),   # Hip Pitch
    3: (20, 200),   # Hip Yaw
    4: (30, 210),   # Hip Roll
    5: (85, 235),   # Leg
    6: (95, 190),   # Hip Pitch
    7: (20, 200),   # Hip Yaw
    8: (30, 210)    # Hip Roll
}

# --- HOME POSITIONS ---
HOME = {
    1: 135, 2: 130, 3: 113, 4: 120,
    5: 135, 6: 130, 7: 113, 8: 120,
}

# --- BABY STEP INCREMENTS (small deltas from home) ---
STEP_LEG_LIFT   = 5    # degrees to lift a leg
STEP_PITCH      = 4    # degrees to swing hip forward/back
STEP_ROLL       = 3    # degrees to shift weight laterally
STEP_YAW        = 2    # degrees for slight yaw correction

# Timing (ms) for each micro-movement
PHASE_TIME = 600
PAUSE = 0.4  # seconds to settle between phases

motors = {
    1: motor1, 2: motor2, 3: motor3, 4: motor4,
    5: motor5, 6: motor6, 7: motor7, 8: motor8,
}

def safe_move(motor, motor_id, target_angle, move_time=50):
    min_angle, max_angle = LIMITS[motor_id]
    safe_angle = max(min_angle, min(target_angle, max_angle))
    if safe_angle != target_angle:
        print(f"  Clamped motor {motor_id}: {target_angle:.1f} -> {safe_angle:.1f}")
    motor.move(safe_angle, time=move_time)

def move_to(positions, move_time=PHASE_TIME):
    """Move multiple servos. positions = {motor_id: angle, ...}"""
    for mid, angle in positions.items():
        safe_move(motors[mid], mid, angle, move_time)

def home_all(move_time=2000):
    """Return every servo to home position."""
    move_to(HOME, move_time)

# ---------------------------------------------------------------
# BABY STEP GAIT
#
# Each full step cycle is broken into 6 small phases:
#   1. Shift weight onto the stance leg (roll)
#   2. Lift the swing leg slightly
#   3. Swing the lifted leg forward a tiny bit (pitch)
#   4. Place the swing leg down
#   5. Shift weight to center
#   6. Brief double-support pause
#
# Then repeat mirrored for the other leg.
# ---------------------------------------------------------------

def baby_step_right_forward():
    """Advance right leg (leg 2, motors 5-8) one baby step."""
    h = HOME

    # Phase 1 - shift weight onto left leg (leg 1)
    print("  Phase 1: weight -> left leg")
    move_to({
        4: h[4] - STEP_ROLL,   # left hip roll: lean left
        8: h[8] - STEP_ROLL,   # right hip roll: assist lean
    })
    time.sleep(PAUSE)

    # Phase 2 - lift right leg slightly
    print("  Phase 2: lift right leg")
    move_to({
        5: h[5] - STEP_LEG_LIFT,  # right leg: retract (lift)
    })
    time.sleep(PAUSE)

    # Phase 3 - swing right leg forward (small pitch change)
    print("  Phase 3: swing right leg forward")
    move_to({
        6: h[6] + STEP_PITCH,     # right hip pitch: forward
        2: h[2] - STEP_PITCH,     # left hip pitch: slight back for balance
        7: h[7] + STEP_YAW,       # slight yaw nudge
    })
    time.sleep(PAUSE)

    # Phase 4 - place right leg down
    print("  Phase 4: place right leg down")
    move_to({
        5: h[5],                   # right leg: extend back to home
    })
    time.sleep(PAUSE)

    # Phase 5 - center weight
    print("  Phase 5: center weight")
    move_to({
        4: h[4],
        8: h[8],
        7: h[7],
    })
    time.sleep(PAUSE)

    # Phase 6 - return pitch to home (double support)
    print("  Phase 6: settle")
    move_to({
        6: h[6],
        2: h[2],
    })
    time.sleep(PAUSE)


def baby_step_left_forward():
    """Advance left leg (leg 1, motors 1-4) one baby step."""
    h = HOME

    # Phase 1 - shift weight onto right leg (leg 2)
    print("  Phase 1: weight -> right leg")
    move_to({
        4: h[4] + STEP_ROLL,
        8: h[8] + STEP_ROLL,
    })
    time.sleep(PAUSE)

    # Phase 2 - lift left leg slightly
    print("  Phase 2: lift left leg")
    move_to({
        1: h[1] - STEP_LEG_LIFT,
    })
    time.sleep(PAUSE)

    # Phase 3 - swing left leg forward
    print("  Phase 3: swing left leg forward")
    move_to({
        2: h[2] + STEP_PITCH,
        6: h[6] - STEP_PITCH,
        3: h[3] - STEP_YAW,
    })
    time.sleep(PAUSE)

    # Phase 4 - place left leg down
    print("  Phase 4: place left leg down")
    move_to({
        1: h[1],
    })
    time.sleep(PAUSE)

    # Phase 5 - center weight
    print("  Phase 5: center weight")
    move_to({
        4: h[4],
        8: h[8],
        3: h[3],
    })
    time.sleep(PAUSE)

    # Phase 6 - settle
    print("  Phase 6: settle")
    move_to({
        2: h[2],
        6: h[6],
    })
    time.sleep(PAUSE)


# --- MAIN ---
print("Homing all servos...")
home_all()
time.sleep(2.5)

print("Starting baby steps (Ctrl+C to stop)...\n")
step_count = 0

try:
    while True:
        step_count += 1
        print(f"--- Step {step_count}: right leg forward ---")
        baby_step_right_forward()

        step_count += 1
        print(f"--- Step {step_count}: left leg forward ---")
        baby_step_left_forward()

except KeyboardInterrupt:
    print("\nStopping... returning to home position.")
    home_all(move_time=1000)
    time.sleep(1.2)
    print("Done.")
