from pylx16a.lx16a import *
import time

LX16A.initialize('/dev/ttyUSB0')

def wiggle_motor(motor_id):
    try:
        motor = LX16A(motor_id)
        current_pos = motor.get_physical_angle()
        print(f"Motor {motor_id} found at angle {current_pos:.1f}. Wiggling...")
        
        motor.move(current_pos + 15, time=300)
        time.sleep(0.4)
        motor.move(current_pos - 15, time=300)
        time.sleep(0.4)
        motor.move(current_pos, time=300)
        time.sleep(0.4)
        
        print("Wiggle complete.\n")
        
    except ServoTimeoutError:
        print(f"Error: Motor {motor_id} is not responding.\n")

print("--- LX-16A Motor Identifier ---")
while True:
    user_input = input("Enter Motor ID (1-8) or 'q' to quit: ")
    if user_input.lower() == 'q':
        break
    if user_input.isdigit():
        wiggle_motor(int(user_input))