# Robot PC - Bimanual Piper Control

Controls two Piper follower arms via network commands.

## Setup

```bash
# Create environment
conda create -n robot_teleop python=3.10 -y
conda activate robot_teleop

# Install dependencies
pip install -r requirements.txt
```

## Run

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

## Network
- Listens on ports 5555-5558
- Ensure firewall allows these ports
- Note your IP address for Teleoperator PC configuration