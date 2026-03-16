def wiggle_motor(motor_id):
    try:
        motor = LX16A(motor_id)
        current_pos = motor.get_physical_angle()
        print(f"Motor {motor_id} found at angle {current_pos:.1f}. Wiggling...")
        
        # Clamp the wiggle targets so they stay within the 0 to 240 boundary
        wiggle_up = min(240, current_pos + 15)
        wiggle_down = max(0, current_pos - 15)
        
        motor.move(wiggle_up, time=300)
        time.sleep(0.4)
        motor.move(wiggle_down, time=300)
        time.sleep(0.4)
        motor.move(current_pos, time=300)
        time.sleep(0.4)
        
        print("Wiggle complete.\n")
        
    except ServoTimeoutError:
        print(f"Error: Motor {motor_id} is not responding.\n")