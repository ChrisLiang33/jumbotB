"""
Capture motor positions while you physically pose the robot by hand.

Workflow:
  1. Run the script. It DISABLES torque on all 8 servos so you can move them.
  2. Hold the robot in pose 1 (standing) and press Enter -> captures all 8 angles.
  3. Hold pose 2 (one leg in air, swinging forward) -> Enter -> captures.
  4. Hold pose 3 (one foot in front, one foot back) -> Enter -> captures.
  5. Script prints all three captures in formats you can paste into a gait.
  6. Saves to poses.json.
  7. Asks if you want to re-enable torque (locks robot in current pose).

Tip for poses 2 and 3: rest one foot on the ground and lift / move the other.
Hold the robot's torso steady while pressing Enter.
"""

from pylx16a.lx16a import *
import time
import json

LX16A.initialize('/dev/ttyUSB0')

def connect_servo(id):
    try:
        return LX16A(id)
    except ServoTimeoutError:
        print(f"Servo {id} is not responding. Exiting.")
        exit()

# Connect all 8 servos
servos = {
    1: connect_servo(1),  # Hip Pitch 1
    2: connect_servo(2),  # Leg 1
    3: connect_servo(3),  # Hip Yaw 1
    4: connect_servo(4),  # Hip Roll 1
    5: connect_servo(5),  # Leg 2
    6: connect_servo(6),  # Hip Pitch 2
    7: connect_servo(7),  # Hip Yaw 2
    8: connect_servo(8),  # Hip Roll 2
}

NAMES = {
    1: "hip_pitch1",
    2: "leg1",
    3: "hip_yaw1",
    4: "hip_roll1",
    5: "leg2",
    6: "hip_pitch2",
    7: "hip_yaw2",
    8: "hip_roll2",
}

POSES_TO_CAPTURE = [
    ("standing",        "Standing upright, both feet flat. Like the home pose."),
    ("swing_forward",   "One leg in the air, that leg swung FORWARD. Other leg planted."),
    ("mid_stride",      "One foot ahead of the body, the other foot behind. Mid-stride pose."),
]


def disable_all():
    print("Disabling torque on all motors. Robot will go limp — SUPPORT IT.")
    for sid, servo in servos.items():
        try:
            servo.disable_torque()
        except Exception as e:
            print(f"  motor {sid}: couldn't disable torque ({e})")
    time.sleep(0.3)

def enable_all():
    print("Re-enabling torque. Robot will hold its current pose.")
    for sid, servo in servos.items():
        try:
            servo.enable_torque()
        except Exception as e:
            print(f"  motor {sid}: couldn't enable torque ({e})")
    time.sleep(0.3)

def read_pose():
    """Read all 8 motor positions. Retries timeouts."""
    pose = {}
    for sid, servo in servos.items():
        for attempt in range(3):
            try:
                pose[sid] = float(servo.get_physical_angle())
                break
            except Exception:
                time.sleep(0.05)
        else:
            pose[sid] = None
            print(f"  motor {sid}: failed to read (timeout)")
    return pose

def print_pose(label, pose):
    print(f"\n--- {label} ---")
    for sid in sorted(pose.keys()):
        val = pose[sid]
        if val is None:
            print(f"  {sid} {NAMES[sid]:<12} : <read failed>")
        else:
            print(f"  {sid} {NAMES[sid]:<12} : {val:6.1f} deg")


# -------------------- main --------------------
print("=" * 70)
print("  CAPTURE POSES — pose the robot by hand, press Enter to capture.")
print("=" * 70)
print()

disable_all()

captured = {}

for label, instruction in POSES_TO_CAPTURE:
    print()
    print(f">>> POSE: {label}")
    print(f"    {instruction}")
    input(f"    Hold the robot still and press Enter to capture {label}... ")
    pose = read_pose()
    captured[label] = pose
    print_pose(label, pose)

# Print summary in a couple of formats
print()
print("=" * 70)
print("  SUMMARY")
print("=" * 70)

print("\n# All captured poses (motor_id -> angle, degrees):\n")
for label, pose in captured.items():
    print(f"{label} = {{")
    for sid in sorted(pose.keys()):
        val = pose[sid]
        if val is None:
            print(f"    {sid}: None,    # {NAMES[sid]} — read failed")
        else:
            print(f"    {sid}: {val:6.1f},  # {NAMES[sid]}")
    print("}")
    print()

# Side-by-side delta table — useful to see what changed between poses
print("\n# Side-by-side comparison (relative to 'standing'):\n")
print(f"{'motor':<14} {'standing':>10} {'swing_fwd':>10} {'mid_stride':>11} {'sw-st':>8} {'mid-st':>8}")
print("-" * 70)
standing = captured.get("standing", {})
swing    = captured.get("swing_forward", {})
mid      = captured.get("mid_stride", {})
for sid in sorted(servos.keys()):
    st = standing.get(sid)
    sw = swing.get(sid)
    md = mid.get(sid)
    st_s = f"{st:6.1f}" if st is not None else "  ---"
    sw_s = f"{sw:6.1f}" if sw is not None else "  ---"
    md_s = f"{md:6.1f}" if md is not None else "  ---"
    sw_d = f"{sw - st:+6.1f}" if (st is not None and sw is not None) else "  ---"
    md_d = f"{md - st:+6.1f}" if (st is not None and md is not None) else "  ---"
    print(f"{sid} {NAMES[sid]:<11} {st_s:>10} {sw_s:>10} {md_s:>11} {sw_d:>8} {md_d:>8}")

# Save JSON
out_path = "poses.json"
with open(out_path, "w") as f:
    json.dump(captured, f, indent=2)
print(f"\nSaved to {out_path}")

# Re-enable torque?
print()
ans = input("Re-enable torque to lock the robot in its current pose? (y/n) ").strip().lower()
if ans == "y":
    enable_all()
    print("Torque enabled. Robot is holding its current pose.")
else:
    print("Leaving torque disabled. Robot will stay limp — support it before letting go.")
