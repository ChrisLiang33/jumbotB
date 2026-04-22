from pylx16a.lx16a import *
import time
import math
import matplotlib.pyplot as plt

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

# 50, 185
def homing():
    # Home Leg 1
    safe_move(leg1,       2, 120,  move_time=home_time)
    safe_move(hip_pitch1, 1, 40,  move_time=home_time)
    safe_move(hip_yaw1,   3, 115, move_time=home_time)
    safe_move(hip_roll1,  4, 120, move_time=home_time)

    # Home Leg 2
    safe_move(leg2,       5, 115, move_time=home_time)
    safe_move(hip_pitch2, 6, 195, move_time=home_time)
    safe_move(hip_yaw2,   7, 120, move_time=home_time)
    safe_move(hip_roll2,  8, 115, move_time=home_time)
    time.sleep(2.5)

homing()

# --- DATA LOGGING ---
servos = [
    (1, "Hip Pitch 1", hip_pitch1),
    (2, "Leg 1",       leg1),
    (3, "Hip Yaw 1",   hip_yaw1),
    (4, "Hip Roll 1",  hip_roll1),
    (5, "Leg 2",       leg2),
    (6, "Hip Pitch 2", hip_pitch2),
    (7, "Hip Yaw 2",   hip_yaw2),
    (8, "Hip Roll 2",  hip_roll2),
]

log_time = []
log_pos  = {sid: [] for sid, _, _ in servos}
log_vel  = {sid: [] for sid, _, _ in servos}
log_temp = {sid: [] for sid, _, _ in servos}
log_vin  = {sid: [] for sid, _, _ in servos}
prev_pos = {}

print("Starting baby steps...")
start_time = time.time()

# === BABY STEP PARAMETERS ===
WALK_SPEED    = 3.0
STRIDE_LENGTH = 20
LIFT_AMOUNT1  = 30
LIFT_AMOUNT2  = 30
SWAY_AMOUNT   = 5

while True:
    try:
        now = time.time()
        elapsed = now - start_time
        phase = elapsed * WALK_SPEED

        # 1. Stride - tiny pitch oscillation
        pitch_wave1 = math.sin(phase) * STRIDE_LENGTH
        pitch_wave2 = math.sin(phase) * STRIDE_LENGTH

        # 2. Lift - small leg lifts, alternating
        lift_wave1 = max(0, math.sin(phase)) * LIFT_AMOUNT1
        lift_wave2 = max(0, math.sin(phase + math.pi)) * LIFT_AMOUNT2

        # 3. Sway - gentle weight shift
        sway_wave = math.cos(phase) * SWAY_AMOUNT

        # --- APPLY WAVES ---
        hip1_pitch_angle = 40 + pitch_wave1
        leg1_angle       = 120 - lift_wave1
        hip1_yaw_angle   = 115
        hip1_roll_angle  = 120 + sway_wave

        hip2_pitch_angle = 195 + pitch_wave2
        leg2_angle       = 115 - lift_wave2
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

        # --- READ & LOG SERVO DATA ---
        # Collect all readings first, then append together so arrays stay equal length
        snap_pos = {}
        snap_vel = {}
        snap_temp = {}
        snap_vin = {}
        all_ok = True
        for sid, name, servo in servos:
            try:
                pos  = servo.get_physical_angle()
                temp = servo.get_temp()
                vin  = servo.get_vin()

                vel = 0.0
                if sid in prev_pos and log_time:
                    dt = elapsed - log_time[-1]
                    if dt > 0:
                        vel = (pos - prev_pos[sid]) / dt
                prev_pos[sid] = pos

                snap_pos[sid] = pos
                snap_vel[sid] = vel
                snap_temp[sid] = temp
                snap_vin[sid] = vin
            except KeyboardInterrupt:
                raise
            except Exception:
                all_ok = False
                break

        if all_ok:
            log_time.append(elapsed)
            for sid, _, _ in servos:
                log_pos[sid].append(snap_pos[sid])
                log_vel[sid].append(snap_vel[sid])
                log_temp[sid].append(snap_temp[sid])
                log_vin[sid].append(snap_vin[sid])

        time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nStopping motors safely...")
        homing()

        # --- PLOT GRAPHS ---
        if len(log_time) < 2:
            print("Not enough data to plot.")
            break

        fig, ax = plt.subplots(figsize=(12, 6))
        fig.suptitle("Motor Angle vs Time")

        colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3',
                  '#ff7f00', '#a65628', '#f781bf', '#999999']

        for i, (sid, name, _) in enumerate(servos):
            ax.plot(log_time, log_pos[sid], label=name, color=colors[i], linewidth=0.8)

        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Angle (deg)")
        ax.legend(loc="upper right", fontsize=8, ncol=4)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("baby_steps_data.png", dpi=150)
        print("Saved plot to baby_steps_data.png")
        plt.show()
        break
