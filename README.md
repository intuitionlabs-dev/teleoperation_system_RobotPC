# Robot PC - Bimanual Piper Control

Controls two Piper follower arms via network commands.

## Setup

```bash
# Create environment
conda create -n robot_teleop python=3.10 -y
conda activate robot_teleop

# Install dependencies
pip install -r requirements.txt
cd piper_sdk
pip install -e .
```

## Run

### Main Teleoperation

```bash
./run_host_broadcast.sh
```

Or manually:
```bash
python -m host_broadcast \
    --left_arm_port left_piper \
    --right_arm_port right_piper \
    --port_zmq_cmd 5555 \
    --port_zmq_observations 5556 \
    --port_cmd_broadcast 5557 \
    --port_obs_broadcast 5558
```

### Motor Enable Listener (Optional)

Run in a separate terminal to enable/reset motors remotely:

```bash
python motor_enable_listener.py \
    --left_arm_port left_piper \
    --right_arm_port right_piper \
    --default_enable_mode partial
```

Features:
- Smart partial mode: Only enables disabled/problematic motors
- Full reset mode: Resets all 7 motors per arm (6 joints + gripper)
- Real-time status monitoring with detailed diagnostics
- Detects and fixes "zombie" motors (enabled but problematic)

## Network
- Main teleoperation: ports 5555-5558
- Motor enable listener: port 5559
- Ensure firewall allows these ports
- Note your IP address for Teleoperator PC configuration