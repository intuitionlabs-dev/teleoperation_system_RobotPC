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

#### Piper System
```bash
# Single step - Just run the host broadcast
./run_host_broadcast.sh
```

#### YAM System (Two-Layer Architecture)
```bash
# Step 0: Clean up CAN interfaces (RECOMMENDED before starting)
# This prevents stuck CAN bus issues from previous runs
cd /home/group/i2rt
sh scripts/cleanup_can_motors.sh
sh scripts/force_reset_can.sh
# Note: force_reset_can.sh requires sudo and will be more aggressive in resetting

# Step 1: Launch hardware servers (in separate terminals)
# These servers directly control the motors via CAN interfaces

# Terminal 1 - Left arm hardware server (port 6001)
cd /home/group/i2rt/gello_software
source .venv/bin/activate
python experiments/launch_yaml.py --left-config-path configs/yam_auto_generated_left.yaml

# Terminal 2 - Right arm hardware server (port 6003)
# IMPORTANT: Edit launch_yaml.py first to change hardware_port from 6001 to 6003
cd /home/group/i2rt/gello_software
source .venv/bin/activate
python experiments/launch_yaml.py --left-config-path configs/yam_auto_generated_right.yaml

# Step 2: Launch host broadcast (in a new terminal)
# This bridges between remote leader arms and local hardware servers
cd /home/group/i2rt/teleoperation_system_RobotPC
./run_host_broadcast.sh --system yam-dynamixel
```

### Architecture Overview

#### Piper System
- **Single Layer**: Host broadcast directly controls motors via Piper SDK
- Data flow: Remote Leader → Host Broadcast → Piper Motors

#### YAM System  
- **Two Layer**: Host broadcast connects to hardware servers via ZMQ
- Data flow: Remote Leader → Host Broadcast → Hardware Servers → CAN/Motors
- Hardware servers handle low-level motor control and CAN communication
- Host broadcast handles network communication and command routing

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
# Requires hardware servers to be running first (see Quick Start above)
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
# Quick start with defaults
./run_yam_motor_listener.sh

# Or manually specify options
python yam_motor_enable_listener.py \
    --left-can can_follow_l \
    --right-can can_follow_r \
    --port 5569 \
    --mode partial
```

Features:
- Monitors DM motor error codes via CAN bus
- Partial mode: Only cleans errors on disabled motors
- Full mode: Resets all motor errors
- Real-time status monitoring
- Automatic error detection and reporting
- Default CAN channels: can_follow_l (left), can_follow_r (right)

## Network Ports

### Piper-SO101 System (Default)
- Teleoperation: 5555-5558
- Motor enable: 5559

### YAM-Dynamixel System
- Teleoperation: 5565-5568 (separated to avoid conflicts)
- Motor enable: 5569
- Hardware servers: 
  - Left arm: 6001 (connects to can_follow_l)
  - Right arm: 6003 (connects to can_follow_r)

### Common
- Default IPs (via Tailscale):
  - Piper PC: 100.117.16.87
  - YAM PC: 100.119.166.86
- Ensure firewall allows these ports
- Note your IP address for Teleoperator PC configuration