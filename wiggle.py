from pylx16a.lx16a import *
import time

# Initialize the serial connection
LX16A.initialize('/dev/ttyUSB0')

def wiggle_motor(motor_id):
    try:
        motor = LX16A(motor_id)
        
        # Read the current angle so we don't snap it to a dangerous position
        current_pos = motor.get_physical_angle()
        print(f"Motor {motor_id} found at angle {current_pos:.1f}. Wiggling...")
        
        # Twitch +15 degrees, -15 degrees, then back to start
        motor.move(current_pos + 15, time=300)
        time.sleep(0.4)
        motor.move(current_pos - 15, time=300)
        time.sleep(0.4)
        motor.move(current_pos, time=300)
        time.sleep(0.4)
        
        print("Wiggle complete.\n")
        
    except ServoTimeoutError:
        print(f"Error: Motor {motor_id} is not responding. Are you sure it's plugged in and has this ID?\n")

print("--- LX-16A Motor Identifier ---")
print("Enter a motor ID to wiggle it. Type 'q' to quit.")

while True:
    user_input = input("Enter Motor ID (e.g., 1 to 8): ")
    
    if user_input.lower() == 'q':
        print("Exiting identifier.")
        break
        
    if user_input.isdigit():
        wiggle_motor(int(user_input))
    else:
        print("Please enter a valid number or 'q' to quit.")