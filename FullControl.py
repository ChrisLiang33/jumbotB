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

print("Moving to home position safely...")
home_time = 2000 

def homing():
    # Home Leg 1
    safe_move(leg1,       2, 120,  move_time=home_time)
    safe_move(hip_pitch1, 1, 50,  move_time=home_time)
    safe_move(hip_yaw1,   3, 115, move_time=home_time)
    safe_move(hip_roll1,  4, 120, move_time=home_time)

    # Home Leg 2
    safe_move(leg2,       5, 115, move_time=home_time)
    safe_move(hip_pitch2, 6, 185, move_time=home_time)
    safe_move(hip_yaw2,   7, 120, move_time=home_time)
    safe_move(hip_roll2,  8, 115, move_time=home_time)
    time.sleep(2.5) 

homing()

print("Starting dynamic movement...")
start_time = time.time()

# === DRASTIC GAIT PARAMETERS ===
WALK_SPEED = 3.5      
STRIDE_LENGTH = 30    
SWAY_AMOUNT = 10      

while True:
    try:
        phase = (time.time() - start_time) * WALK_SPEED
        
        # 1. Stride
        pitch_wave1 = math.sin(phase) * STRIDE_LENGTH
        pitch_wave2 = math.sin(phase) * STRIDE_LENGTH  
        
        # 2. Lift: Custom amplitudes to reach your exact targets
        # Leg 1 amplitude is 120 so it goes from 120 down to 0
        lift_wave1 = max(0, math.sin(phase)) * 120
        
        # Leg 2 amplitude is 115 so it bends properly but returns to 230 when planted
        lift_wave2 = max(0, math.sin(phase + math.pi)) * 115
        
        # 3. Sway
        sway_wave = math.cos(phase) * SWAY_AMOUNT

        # --- APPLY WAVES ---
        hip1_pitch_angle = 50 + pitch_wave1   
        leg1_angle       = 120 - lift_wave1   # Starts at 120, hits exactly 0 at peak lift      
        hip1_yaw_angle   = 115                            
        hip1_roll_angle  = 120 + sway_wave                           

        hip2_pitch_angle = 185 + pitch_wave2   
        leg2_angle       = 230 - lift_wave2   # Starts at 230, bends, and returns to exactly 230
        hip2_yaw_angle   = 120                            
        hip2_roll_angle  = 115 + sway_wave 

        # Execute safe moves for Leg 1
        safe_move(hip_pitch1, 1, hip1_pitch_angle, move_time=100)
        safe_move(leg1,       2, leg1_angle,       move_time=100)
        safe_move(hip_yaw1,   3, hip1_yaw_angle,   move_time=50)
        safe_move(hip_roll1,  4, hip1_roll_angle,  move_time=50)

        # Execute safe moves for Leg 2
        safe_move(leg2,       5, leg2_angle,       move_time=100)
        safe_move(hip_pitch2, 6, hip2_pitch_angle, move_time=100)
        safe_move(hip_yaw2,   7, hip2_yaw_angle,   move_time=50)
        safe_move(hip_roll2,  8, hip2_roll_angle,  move_time=50)

        time.sleep(0.02)
        
    except KeyboardInterrupt:
        print("\nStopping motors safely...")
        homing()
        break