# Robot PC - Multi-System Robot Control

Controls follower arms (Piper or YAM) via network commands.

## Supported Systems

- **piper-so101**: Dual Piper follower arms
- **yam-dynamixel**: Dual YAM follower arms

## Setup

### For Piper System
```bash
# Create environment
conda create -n robot_teleop python=3.10 -y
conda activate robot_teleop

# Install dependencies
pip install -r requirements.txt
cd piper_sdk
pip install -e .
```

### For YAM System
```bash
# Use the existing gello virtual environment
source /home/group/i2rt/gello_software/.venv/bin/activate

# Install additional dependencies if needed
uv pip install -r requirements.txt
```

## Run

### Quick Start

```bash
# For Piper system (default)
./run_host_broadcast.sh

# For YAM system
./run_host_broadcast.sh --system yam-dynamixel
```

### Manual Commands

#### Piper System
```bash
python -m host_broadcast \
    --system piper-so101 \
    --left_arm_port left_piper \
    --right_arm_port right_piper \
    --port_zmq_cmd 5555 \
    --port_zmq_observations 5556 \
    --port_cmd_broadcast 5557 \
    --port_obs_broadcast 5558
```

#### YAM System
```bash
python -m host_broadcast \
    --system yam-dynamixel \
    --yam_left_channel can_follow_l \
    --yam_right_channel can_follow_r
# Note: YAM system automatically uses ports 5565-5568 when --system yam-dynamixel is specified
# Channel names default to can_follow_l and can_follow_r if not specified
```

### Motor Enable Listener

#### Piper System
Run in a separate terminal to enable/reset Piper motors remotely:

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

#### YAM System
Run in a separate terminal to monitor and enable YAM motors:

```bash
python yam_motor_enable_listener.py \
    --left-can can0 \
    --right-can can1 \
    --port 5569 \
    --mode partial
```

Features:
- Monitors DM motor error codes via CAN bus
- Partial mode: Only cleans errors on disabled motors
- Full mode: Resets all motor errors
- Real-time status monitoring
- Automatic error detection and reporting

## Network Ports

### Piper-SO101 System (Default)
- Teleoperation: 5555-5558
- Motor enable: 5559

### YAM-Dynamixel System
- Teleoperation: 5565-5568 (separated to avoid conflicts)
- Motor enable: 5569
- Hardware servers: 6001-6002

### Common
- Default IP (via Tailscale): 100.117.16.87
- Ensure firewall allows these ports
- Note your IP address for Teleoperator PC configuration