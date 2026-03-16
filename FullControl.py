from pylx16a.lx16a import *
import time
import math

# Initialize the serial connection
LX16A.initialize('/dev/ttyUSB0')

def connect_servo(id):
    try:
        return LX16A(id)
    except ServoTimeoutError:
        print(f"Servo {id} is not responding. Exiting.")
        exit()

# --- LEG 1 ---
motor1 = connect_servo(1) # Leg 
motor2 = connect_servo(2) # Hip Pitch
motor3 = connect_servo(3) # Hip Yaw
motor4 = connect_servo(4) # Hip Roll

# --- LEG 2 ---
motor5 = connect_servo(5) # Leg 
motor6 = connect_servo(6) # Hip Pitch
motor7 = connect_servo(7) # Hip Yaw
motor8 = connect_servo(8) # Hip Roll

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

# --- DYNAMIC LOOP ---
print("Starting dynamic movement...")
t = 0
start_time = time.time()

while True:
    try:
        elapsed = time.time() - start_time
        
        # --- LEG 1 TRAJECTORIES ---
        leg1_angle = (math.sin(t) * 20) + 135         
        hip1_pitch_angle = (math.cos(t) * 15) + 130   
        hip1_yaw_angle = 113                            
        hip1_roll_angle = 120                           

        # --- LEG 2 TRAJECTORIES ---
        offset = math.pi
        leg2_angle = (math.sin(t + offset) * 20) + 135         
        hip2_pitch_angle = (math.cos(t + offset) * 15) + 130   
        hip2_yaw_angle = 113                            
        hip2_roll_angle = 120                           

        # Execute safe moves for Leg 1
        safe_move(motor1, 1, leg1_angle, move_time=200)
        safe_move(motor2, 2, hip1_pitch_angle, move_time=200)
        safe_move(motor3, 3, hip1_yaw_angle, move_time=50)
        safe_move(motor4, 4, hip1_roll_angle, move_time=50)

        # Execute safe moves for Leg 2
        safe_move(motor5, 5, leg2_angle, move_time=200)
        safe_move(motor6, 6, hip2_pitch_angle, move_time=200)
        safe_move(motor7, 7, hip2_yaw_angle, move_time=50)
        safe_move(motor8, 8, hip2_roll_angle, move_time=50)

        time.sleep(0.05)
        t += 0.25
        
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