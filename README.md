# Robot PC - Teleoperation System

Controls follower arms (Piper or YAM) via network commands from remote leader arms.

## Quick Start

### 1. Install uv (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 2. Clone and Setup
```bash
git clone https://github.com/intuitionlabs-dev/teleoperation_system_RobotPC.git
cd teleoperation_system_RobotPC

# Create environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# For Piper system only - install piper_sdk
cd piper_sdk && pip install -e . && cd ..
```

### 3. Launch System

#### For YAM System (Dual Arms)
```bash
# One command launches everything!
./launch_yam_system.sh
```

This automatically:
- Cleans CAN interfaces (runs cleanup_can_motors.sh and force_reset_can.sh)
- Launches left arm hardware server (port 6001)
- Launches right arm hardware server (port 6003)  
- Starts host broadcast (ports 5565-5568)
- Waits for remote commands

#### For Piper System
```bash
./run_host_broadcast.sh
```

## System Architecture

### YAM System
```
Remote Leader Arms → Network → Host Broadcast → Hardware Servers → CAN/Motors
                    (5565-5568)            (6001/6003)        (can_follow_l/r)
```

### Piper System
```
Remote Leader Arms → Network → Host Broadcast → Piper SDK → Motors
                    (5555-5558)              (USB serial)
```

## Network Ports

| System | Purpose | Ports |
|--------|---------|-------|
| Piper | Teleoperation | 5555-5558 |
| Piper | Motor enable | 5559 |
| YAM | Teleoperation | 5565-5568 |
| YAM | Motor enable | 5569 |
| YAM | Hardware servers | 6001 (left), 6003 (right) |

## Troubleshooting

### CAN Issues
```bash
# Manual CAN reset (already done automatically by launch_yam_system.sh)
sh scripts/cleanup_can_motors.sh
sudo sh scripts/force_reset_can.sh
```

### Individual Component Launch

#### YAM Hardware Servers
```bash
# Terminal 1 - Left arm
python launch_hardware_server.py --arm left

# Terminal 2 - Right arm  
python launch_hardware_server.py --arm right

# Terminal 3 - Host broadcast
python -m host_broadcast --system yam-dynamixel
```

#### Motor Enable Listener (Optional)
```bash
# YAM system
python yam_motor_enable_listener.py

# Piper system
python motor_enable_listener.py
```

## Configuration

- YAM configs: `configs/yam_auto_generated_*.yaml`
- Piper configs: Set via command line arguments
- Network IPs: Configure in Tailscale or update host_broadcast.py