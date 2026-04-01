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
    # Leg 1 limits
    1: (85, 235),   # Leg
    2: (95, 190),   # Hip Pitch
    3: (20, 200),   # Hip Yaw
    4: (30, 210),   # Hip Roll

    # Leg 2 limits
    5: (85, 235),   # Leg
    6: (95, 190),   # Hip Pitch
    7: (20, 200),   # Hip Yaw
    8: (30, 210)    # Hip Roll
}

def safe_move(motor, motor_id, target_angle, move_time=50):
    min_angle, max_angle = LIMITS[motor_id]
    safe_angle = max(min_angle, min(target_angle, max_angle))

    if safe_angle != target_angle:
        print(f"Warning: Motor {motor_id} clamped from {target_angle:.1f} to {safe_angle:.1f}")

    motor.move(safe_angle, time=move_time)

# --- BABY STEP PARAMETERS ---
STEP_LEG_LIFT = 5     # degrees to lift a leg
STEP_PITCH    = 4     # degrees to swing hip forward/back
STEP_ROLL     = 3     # degrees to shift weight laterally
PHASE_TIME    = 600   # ms per micro-movement
PAUSE         = 0.4   # seconds to settle between phases

# --- HOMING SEQUENCE ---
print("Moving to home position safely...")
home_time = 2000

# Home Leg 1
safe_move(motor1, 1, 135, move_time=home_time)
safe_move(motor2, 2, 130, move_time=home_time)
safe_move(motor3, 3, 113, move_time=home_time)
safe_move(motor4, 4, 120, move_time=home_time)

# Home Leg 2
safe_move(motor5, 5, 135, move_time=home_time)
safe_move(motor6, 6, 130, move_time=home_time)
safe_move(motor7, 7, 113, move_time=home_time)
safe_move(motor8, 8, 120, move_time=home_time)

time.sleep(2.5)

# --- BABY STEP LOOP ---
# Each step cycle per leg:
#   1. Shift weight onto stance leg (roll)
#   2. Lift swing leg slightly
#   3. Swing lifted leg forward (pitch)
#   4. Place swing leg down
#   5. Center weight back
#   6. Settle (return pitch to neutral)

print("Starting baby steps (Ctrl+C to stop)...")
step_count = 0

while True:
    try:
        # ======= RIGHT LEG (leg 2) STEPS FORWARD =======
        step_count += 1
        print(f"--- Step {step_count}: right leg forward ---")

        # Phase 1 - shift weight onto left leg
        safe_move(motor4, 4, 120 - STEP_ROLL, move_time=PHASE_TIME)
        safe_move(motor8, 8, 120 - STEP_ROLL, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 2 - lift right leg slightly
        safe_move(motor5, 5, 135 - STEP_LEG_LIFT, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 3 - swing right leg forward, left leg nudges back
        safe_move(motor6, 6, 130 - STEP_PITCH, move_time=PHASE_TIME)
        safe_move(motor2, 2, 130 + STEP_PITCH, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 4 - place right leg down
        safe_move(motor5, 5, 135, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 5 - center weight
        safe_move(motor4, 4, 120, move_time=PHASE_TIME)
        safe_move(motor8, 8, 120, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 6 - settle pitch back to home
        safe_move(motor6, 6, 130, move_time=PHASE_TIME)
        safe_move(motor2, 2, 130, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # ======= LEFT LEG (leg 1) STEPS FORWARD =======
        step_count += 1
        print(f"--- Step {step_count}: left leg forward ---")

        # Phase 1 - shift weight onto right leg
        safe_move(motor4, 4, 120 + STEP_ROLL, move_time=PHASE_TIME)
        safe_move(motor8, 8, 120 + STEP_ROLL, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 2 - lift left leg slightly
        safe_move(motor1, 1, 135 - STEP_LEG_LIFT, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 3 - swing left leg forward, right leg nudges back
        safe_move(motor2, 2, 130 - STEP_PITCH, move_time=PHASE_TIME)
        safe_move(motor6, 6, 130 + STEP_PITCH, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 4 - place left leg down
        safe_move(motor1, 1, 135, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 5 - center weight
        safe_move(motor4, 4, 120, move_time=PHASE_TIME)
        safe_move(motor8, 8, 120, move_time=PHASE_TIME)
        time.sleep(PAUSE)

        # Phase 6 - settle pitch back to home
        safe_move(motor2, 2, 130, move_time=PHASE_TIME)
        safe_move(motor6, 6, 130, move_time=PHASE_TIME)
        time.sleep(PAUSE)

    except KeyboardInterrupt:
        print("\nStopping motors safely...")
        shutdown_time = 1000

        # Leg 1 Park
        safe_move(motor1, 1, 135, move_time=shutdown_time)
        safe_move(motor2, 2, 110, move_time=shutdown_time)
        safe_move(motor3, 3, 113, move_time=shutdown_time)
        safe_move(motor4, 4, 120, move_time=shutdown_time)

        # Leg 2 Park
        safe_move(motor5, 5, 135, move_time=shutdown_time)
        safe_move(motor6, 6, 110, move_time=shutdown_time)
        safe_move(motor7, 7, 113, move_time=shutdown_time)
        safe_move(motor8, 8, 120, move_time=shutdown_time)

        time.sleep(1.2)
        break
