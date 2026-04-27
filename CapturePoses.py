"""
Capture arbitrarily many poses while you physically pose the robot by hand.

Workflow:
  1. Run script. Torque is DISABLED on all servos -- SUPPORT the robot.
  2. Pose the robot. Press Enter to capture (auto-labeled step_1, step_2, ...).
     OR type a custom label (like "heel_strike_left") then Enter.
  3. Repeat as many times as you want.
  4. Type 'q' or 'done' to finish.
  5. Script prints a summary table, plots joint angles across the sequence,
     and saves to poses.json + poses_plot.png.
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

servos = {
    1: connect_servo(1),
    2: connect_servo(2),
    3: connect_servo(3),
    4: connect_servo(4),
    5: connect_servo(5),
    6: connect_servo(6),
    7: connect_servo(7),
    8: connect_servo(8),
}

NAMES = {
    1: "hip_pitch1", 2: "leg1", 3: "hip_yaw1", 4: "hip_roll1",
    5: "leg2",       6: "hip_pitch2", 7: "hip_yaw2", 8: "hip_roll2",
}

# Group joints into matched pairs (leg 1, leg 2) for plotting comparisons
JOINT_PAIRS = [
    ("Hip Pitch", 1, 6),
    ("Leg / Knee", 2, 5),
    ("Hip Yaw",   3, 7),
    ("Hip Roll",  4, 8),
]


def disable_all():
    print("Disabling torque on all motors. Robot will go limp -- SUPPORT IT.")
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
    pose = {}
    for sid, servo in servos.items():
        for _ in range(3):
            try:
                pose[sid] = float(servo.get_physical_angle())
                break
            except Exception:
                time.sleep(0.05)
        else:
            pose[sid] = None
            print(f"  motor {sid}: read failed")
    return pose


# -------------------- main --------------------
print("=" * 70)
print("  CAPTURE POSES")
print("  Press Enter to capture, type label+Enter to name, type 'q' to finish.")
print("=" * 70)
print()

disable_all()

captures = []   # list of (label, pose_dict)
step_idx = 0

while True:
    step_idx += 1
    default_label = f"step_{step_idx}"
    prompt = f"Capture #{step_idx} (Enter for '{default_label}', or type a label, or 'q' to finish): "
    raw = input(prompt).strip()
    if raw.lower() in ("q", "done", "quit", "exit"):
        step_idx -= 1   # undo increment since we didn't capture
        break
    label = raw if raw else default_label
    pose = read_pose()
    captures.append((label, pose))
    # Quick echo
    nice = ", ".join(f"{NAMES[sid]}={pose[sid]:.1f}" if pose[sid] is not None else f"{NAMES[sid]}=??"
                     for sid in sorted(pose.keys()))
    print(f"  captured '{label}': {nice}")

if not captures:
    print("No captures. Exiting.")
    exit()

print(f"\nTotal captures: {len(captures)}")

# -------------------- summary table --------------------
print()
print("=" * 90)
print("  SUMMARY TABLE  (motor angles in degrees)")
print("=" * 90)

# Column widths
label_w = max(len(lbl) for lbl, _ in captures)
label_w = max(label_w, 8)

header = f"{'motor':<14}"
for lbl, _ in captures:
    header += f" {lbl:>{label_w}}"
print(header)
print("-" * len(header))
for sid in sorted(servos.keys()):
    row = f"{sid} {NAMES[sid]:<11}"
    for _, pose in captures:
        v = pose.get(sid)
        row += f" {('---' if v is None else f'{v:.1f}'):>{label_w}}"
    print(row)

# -------------------- delta table (each step relative to step 1) --------------------
print()
print("  DELTAS  (each step relative to capture 1)")
print("-" * len(header))
base = captures[0][1]
for sid in sorted(servos.keys()):
    row = f"{sid} {NAMES[sid]:<11}"
    for lbl, pose in captures:
        v = pose.get(sid)
        b = base.get(sid)
        if v is None or b is None:
            row += f" {'---':>{label_w}}"
        else:
            row += f" {f'{v-b:+.1f}':>{label_w}}"
    print(row)

# -------------------- save JSON --------------------
out_json = "poses.json"
with open(out_json, "w") as f:
    json.dump(
        [{"label": lbl, "angles": pose} for lbl, pose in captures],
        f, indent=2
    )
print(f"\nSaved JSON: {out_json}")

# -------------------- plot --------------------
try:
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib not installed -- skipping plot. (pip install matplotlib)")
else:
    labels = [lbl for lbl, _ in captures]
    x = list(range(1, len(captures) + 1))

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    fig.suptitle("Joint angles across captured poses (paired by joint type)")

    for ax, (joint_name, sid_a, sid_b) in zip(axes.flat, JOINT_PAIRS):
        ya = [c[1].get(sid_a) for c in captures]
        yb = [c[1].get(sid_b) for c in captures]
        ax.plot(x, ya, "-o", label=NAMES[sid_a])
        ax.plot(x, yb, "-o", label=NAMES[sid_b])
        ax.set_title(joint_name)
        ax.set_ylabel("angle (deg)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    for ax in axes[-1, :]:
        ax.set_xlabel("capture #")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)

    plt.tight_layout()
    out_png = "poses_plot.png"
    plt.savefig(out_png, dpi=150)
    print(f"Saved plot: {out_png}")
    plt.show()

# -------------------- re-enable torque? --------------------
print()
ans = input("Re-enable torque to lock the robot in its current pose? (y/n) ").strip().lower()
if ans == "y":
    enable_all()
    print("Torque enabled.")
else:
    print("Torque left disabled. Support the robot before letting go.")
