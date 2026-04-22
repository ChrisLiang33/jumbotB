# JumboT-B: Sim-to-Real RL Pipeline Checklist

Goal: train a locomotion policy (stand upright + walk straight) in MuJoCo and deploy it on the real robot.

---

## Stage 0 — Baseline (where you are now)

- [x] 8-servo biped assembled (LX-16A, 2 legs x 4 joints)
- [x] Serial control via `pylx16a` working
- [x] Homing + open-loop sinusoidal gait (`BabySteps.py`)
- [x] Position / temp / voltage logging + plotting
- [ ] Robot can hold weight standing but doesn't walk yet

---

## Stage 1 — Hardware prep

Before you can do anything in sim-to-real, the robot needs the sensors the policy will consume.

- [ ] Pick IMU: **BNO085** (recommended, built-in sensor fusion) or MPU6050 (cheaper, you'd run Madgwick filter yourself)
- [ ] Wire IMU to the onboard computer via I²C
- [ ] Write a Python reader that publishes base quaternion + angular velocity at 50 Hz
- [ ] Verify IMU axes match your URDF convention (X forward, Z up — sanity check by tilting)
- [ ] Add IMU reading into the main control loop alongside the servo reads
- [ ] Confirm control loop still hits ~50 Hz with IMU reads added

**Deliverable**: a function `read_robot_state()` that returns joint positions, joint velocities, base quaternion, base angular velocity.

---

## Stage 2 — Robot model (URDF/MJCF)

This is the bridge between Onshape and MuJoCo. The masses and inertias matter more than the meshes.

- [ ] In Onshape: each link is a separate Part Studio
- [ ] Assembly uses mate connectors for joints, named with `dof_` prefix convention
- [ ] **Set real material densities** on every part (PLA ≈ 1.25 g/cc, PETG ≈ 1.27 g/cc)
- [ ] Model servos, battery, electronics as separate parts with correct mass (weigh them!)
- [ ] Get Onshape API key, install `onshape-to-robot`
- [ ] Write `config.json` for the export
- [ ] Run export → get URDF + STL meshes
- [ ] Convert to MJCF (`mjcf` or MuJoCo's built-in URDF loader)
- [ ] Load in MuJoCo viewer, check joint axes rotate the right way
- [ ] Verify total mass matches scale reading (within 10%)
- [ ] Verify joint limits in MJCF match real servo limits

**Deliverable**: `jumbotb.xml` (MJCF) that loads cleanly in MuJoCo.

---

## Stage 3 — Simulator setup

- [ ] Install MuJoCo + `mujoco` Python bindings
- [ ] Build a scene file: ground plane, robot, a fixed keyframe for home pose
- [ ] Write a minimal env: `reset()`, `step(action)`, observation dict
- [ ] Action space = 8 target joint angles (same as real robot)
- [ ] PD actuator model in MJCF with stiffness/damping placeholders (tune in Stage 4)
- [ ] Visual check: drop robot from 10 cm, does it settle realistically?
- [ ] Keyframe: robot standing in home pose (matches `homing()` in `BabySteps.py`)

**Deliverable**: a gymnasium-style env you can `env.step(zero_action)` and watch it stand or fall over.

---

## Stage 4 — System ID (close the sim-real gap on motors)

The motor model is the single biggest source of sim-to-real error for a servo-driven robot.

- [ ] Write a sys-ID script: command step inputs of various sizes to one joint at a time
- [ ] Log commanded angle + real measured angle at 50 Hz
- [ ] Fit a first-order model: `kp` (stiffness), `kd` (damping), and a pure delay
- [ ] Apply the same step in MuJoCo, compare traces
- [ ] Iterate `kp`, `kd`, delay until sim and real traces overlap
- [ ] Also measure: servo deadband (min commanded change that produces motion), max angular velocity, backlash
- [ ] Plug identified params into the MJCF `<position>` actuators

**Deliverable**: sim step response matches real step response on at least 3 joints.

---

## Stage 5 — RL task + infrastructure

- [ ] Pick framework: **`stable-baselines3`** (simplest) or **Isaac Lab** (if you want GPU parallelism later)
- [ ] Define observation: [joint pos (8), joint vel (8), base quat (4), base ang vel (3), last action (8), commanded vel (3)] = 34 dims
- [ ] Define action: 8 target joint angle deltas from nominal pose, scaled to ±0.3 rad
- [ ] Reward terms:
  - forward velocity tracking (main signal)
  - upright bonus (dot(base_z, world_z))
  - action rate penalty (smoothness)
  - torque/energy penalty
  - alive bonus
- [ ] Termination: base tilt > 45° OR time limit (20 s)
- [ ] Domain randomization knobs (start with these disabled, enable before final training):
  - link masses ±15%
  - friction 0.5–1.2
  - motor kp ±20%
  - motor delay 0–30 ms
  - IMU noise + drift
  - observation latency 0–40 ms

**Deliverable**: a training script that runs one PPO update without crashing.

---

## Stage 6 — Training

- [ ] Curriculum stage 1: hold home pose, zero commanded velocity. Reward = upright + low action rate.
  - Success: robot stays standing for 20 s in sim.
- [ ] Curriculum stage 2: commanded forward velocity = 0.1 m/s. Small target.
  - Success: takes 1–2 steps forward without falling.
- [ ] Curriculum stage 3: commanded forward velocity 0.2–0.5 m/s.
  - Success: walks across the sim floor consistently.
- [ ] Enable domain randomization, retrain from the Stage 3 checkpoint
- [ ] Evaluate: 100 rollouts, report fall rate across randomized envs

**Deliverable**: a trained policy checkpoint that walks robustly in randomized sim.

---

## Stage 7 — Sim-to-real deployment

- [ ] Export policy to a format you can run on the robot's onboard computer (torchscript / ONNX)
- [ ] Write the real-robot inference loop: read state → policy forward pass → send joint targets → sleep to maintain 50 Hz
- [ ] **Safety harness first**: hang the robot or hold it — do NOT let it walk free on the first run
- [ ] Start with commanded velocity = 0 and verify the policy holds upright pose in the harness
- [ ] Gradually increase commanded velocity, watch for oscillation
- [ ] Let it walk on the ground only after hanging-test is stable
- [ ] If it falls: log the real observations, replay through the policy in sim, find the gap, iterate Stage 4 or Stage 5

**Deliverable**: robot walks forward unassisted on the floor.

---

## Cross-cutting

- [ ] Version control everything (URDF, MJCF, training configs, checkpoints)
- [ ] Record every successful and failed real-robot rollout for analysis
- [ ] Keep a journal of what randomization ranges worked and what didn't

---

## Open risks to watch

1. **Motor model accuracy** — the LX-16A's position-only interface hides torque limits and internal control loop behavior. Expect to iterate Stage 4 several times.
2. **IMU mounting rigidity** — loose IMU = noisy orientation = bad policy. Mount it solidly to the torso.
3. **Real-time loop jitter** — Python on Linux can drop frames. If you miss 50 Hz consistently, consider a C++ or Rust control loop.
4. **Battery voltage sag under load** — your voltage logs already show this. Servo behavior changes with vin; include voltage in sys-ID conditions.
