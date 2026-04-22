from pylx16a.lx16a import *
import time

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

servos = [
    (1, "Hip Pitch 1", hip_pitch1),
    (2, "Leg 1      ", leg1),
    (3, "Hip Yaw 1  ", hip_yaw1),
    (4, "Hip Roll 1 ", hip_roll1),
    (5, "Leg 2      ", leg2),
    (6, "Hip Pitch 2", hip_pitch2),
    (7, "Hip Yaw 2  ", hip_yaw2),
    (8, "Hip Roll 2 ", hip_roll2),
]

# Store previous positions to calculate velocity
prev_positions = {}
prev_time = None

SAMPLE_RATE = 0.1  # seconds between reads

print("Reading servo data (Ctrl+C to stop)...\n")
print(f"{'ID':<4} {'Name':<13} {'Pos (deg)':<10} {'Vel (deg/s)':<12} {'Temp (C)':<9} {'Vin (mV)':<9} {'Torque':<8}")
print("-" * 72)

while True:
    try:
        now = time.time()

        for sid, name, servo in servos:
            try:
                pos  = servo.get_physical_angle()
                temp = servo.get_temp()
                vin  = servo.get_vin()
                torque_on = servo.is_torque_enabled(poll_hardware=True)

                # Calculate velocity from position change
                vel = 0.0
                if sid in prev_positions and prev_time is not None:
                    dt = now - prev_time
                    if dt > 0:
                        vel = (pos - prev_positions[sid]) / dt

                prev_positions[sid] = pos

                print(f"{sid:<4} {name:<13} {pos:<10.1f} {vel:<12.1f} {temp:<9} {vin:<9} {'ON' if torque_on else 'OFF':<8}")

            except ServoTimeoutError:
                print(f"{sid:<4} {name:<13} --- TIMEOUT ---")

        prev_time = now
        print()
        time.sleep(SAMPLE_RATE)

    except KeyboardInterrupt:
        print("\nDone.")
        break
