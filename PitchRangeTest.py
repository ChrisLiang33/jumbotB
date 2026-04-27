"""
Interactive tool to find the safe range of motion for the hip pitch motors.

Commands BOTH pitch motors mirror-symmetrically (so the robot leans/lunges
forward and backward as a whole rather than splitting its legs).
Reports motor angles + tracks the min/max body-frame offset you reach.

Usage:
    python PitchRangeTest.py

Then type at the prompt:
    <number>   set body-frame pitch offset directly
                  e.g.  +10  -> both legs forward 10 deg
                  e.g.  -20  -> both legs back 20 deg
    +N / -N    nudge from current offset by N degrees
    r          reset to home (offset 0)
    s          show explored range so far
    h          show home/limit info
    q          quit (homes the robot first)
"""

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

# --- Home positions (must match BabyStepsV2 / FullControl) ---
HOME = {
    1: 40,    # Hip Pitch 1
    2: 120,   # Leg 1
    3: 115,   # Hip Yaw 1
    4: 120,   # Hip Roll 1
    5: 115,   # Leg 2
    6: 195,   # Hip Pitch 2
    7: 120,   # Hip Yaw 2
    8: 115,   # Hip Roll 2
}

# Mapping from body-frame "forward swing" to motor angle direction.
# Motor 1 increases  -> leg 1 forward.       sign = +1
# Motor 6 decreases  -> leg 2 forward (mirrored). sign = -1
PITCH_FORWARD_SIGN = {
    1: +1,
    6: -1,
}

def safe_move(motor_obj, motor_id, target_angle, move_time=500):
    min_angle, max_angle = LIMITS[motor_id]
    safe_angle = max(min_angle, min(target_angle, max_angle))
    clamped = (safe_angle != target_angle)
    motor_obj.move(safe_angle, time=move_time)
    return safe_angle, clamped

def homing(move_time=2000):
    safe_move(leg1,       2, HOME[2], move_time=move_time)
    safe_move(hip_pitch1, 1, HOME[1], move_time=move_time)
    safe_move(hip_yaw1,   3, HOME[3], move_time=move_time)
    safe_move(hip_roll1,  4, HOME[4], move_time=move_time)
    safe_move(leg2,       5, HOME[5], move_time=move_time)
    safe_move(hip_pitch2, 6, HOME[6], move_time=move_time)
    safe_move(hip_yaw2,   7, HOME[7], move_time=move_time)
    safe_move(hip_roll2,  8, HOME[8], move_time=move_time)
    time.sleep(2.5)

def apply_offset(offset, move_time=500):
    """offset is body-frame degrees. positive = both legs forward."""
    target1 = HOME[1] + PITCH_FORWARD_SIGN[1] * offset
    target6 = HOME[6] + PITCH_FORWARD_SIGN[6] * offset
    a1, c1 = safe_move(hip_pitch1, 1, target1, move_time=move_time)
    a6, c6 = safe_move(hip_pitch2, 6, target6, move_time=move_time)
    return a1, a6, (c1 or c6)

def print_state(offset, a1, a6, clamped):
    print(f"  offset = {offset:+.1f} deg (body frame)")
    print(f"  motor 1 (Hip Pitch 1) = {a1:.1f}   limits {LIMITS[1]}   home {HOME[1]}")
    print(f"  motor 6 (Hip Pitch 2) = {a6:.1f}   limits {LIMITS[6]}   home {HOME[6]}")
    if clamped:
        print("  [!] one or both motors hit a hard limit on that move")

def print_help():
    print()
    print("Commands:")
    print("  <number>   set body-frame offset directly (e.g. -15, +8, 0)")
    print("  +N / -N    nudge by N from current offset")
    print("  r          reset to home (offset 0)")
    print("  s          show explored range")
    print("  h          show home/limit info")
    print("  q          quit (will home first)")
    print()

def print_home_info():
    print()
    print("Home positions:")
    print(f"  motor 1 home = {HOME[1]} (limits {LIMITS[1]})")
    print(f"  motor 6 home = {HOME[6]} (limits {LIMITS[6]})")
    print(f"Forward direction: motor 1 increases, motor 6 decreases.")
    print(f"Max possible body-frame forward offset (before hitting limits):")
    print(f"  motor 1: {LIMITS[1][1] - HOME[1]} deg")
    print(f"  motor 6: {HOME[6] - LIMITS[6][0]} deg")
    print(f"Max possible body-frame backward offset:")
    print(f"  motor 1: {HOME[1] - LIMITS[1][0]} deg")
    print(f"  motor 6: {LIMITS[6][1] - HOME[6]} deg")
    print()


# ----------------- main -----------------
print("Moving to home position...")
homing()

print()
print("=" * 60)
print("  PITCH RANGE TESTER")
print("=" * 60)
print_help()
print_home_info()

current_offset = 0.0
min_offset_seen = 0.0
max_offset_seen = 0.0

a1, a6, _ = apply_offset(current_offset, move_time=500)
print_state(current_offset, a1, a6, False)

while True:
    try:
        cmd = input("\noffset> ").strip()
        if not cmd:
            continue

        if cmd == "q":
            print("Homing and quitting...")
            homing(move_time=1500)
            time.sleep(1.5)
            print(f"Final explored range: {min_offset_seen:+.1f} to {max_offset_seen:+.1f} deg")
            break

        elif cmd == "r":
            current_offset = 0.0
            a1, a6, c = apply_offset(current_offset, move_time=1000)
            print_state(current_offset, a1, a6, c)

        elif cmd == "s":
            print(f"  explored range: {min_offset_seen:+.1f} to {max_offset_seen:+.1f} deg")
            print(f"  current offset: {current_offset:+.1f} deg")

        elif cmd == "h":
            print_home_info()

        else:
            # parse a number, possibly with leading + or -
            try:
                # +5 / -5 means nudge; bare number means absolute
                if cmd.startswith(("+", "-")) and len(cmd) > 1 and cmd[1:].replace(".", "", 1).isdigit():
                    delta = float(cmd)
                    current_offset += delta
                else:
                    current_offset = float(cmd)
            except ValueError:
                print(f"  unrecognized command: {cmd!r}")
                continue

            a1, a6, c = apply_offset(current_offset)
            print_state(current_offset, a1, a6, c)
            min_offset_seen = min(min_offset_seen, current_offset)
            max_offset_seen = max(max_offset_seen, current_offset)

    except KeyboardInterrupt:
        print("\nInterrupted — homing and quitting...")
        homing(move_time=1500)
        time.sleep(1.5)
        print(f"Final explored range: {min_offset_seen:+.1f} to {max_offset_seen:+.1f} deg")
        break
    except EOFError:
        print("\n(EOF) Homing and quitting...")
        homing(move_time=1500)
        time.sleep(1.5)
        break
