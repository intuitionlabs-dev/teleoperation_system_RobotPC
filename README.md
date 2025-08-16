# Teleoperation Follower (Robot PC side)

ZMQ server for bimanual Piper robot control.


## Installation
```bash
git clone https://github.com/intuitionlabs-dev/teleoperation_system_RobotPC.git
cd teleoperation_system_RobotPC
conda create -n teleoperate-RobotPC python=3.10
conda activate teleoperate-RobotPC
python -m pip install -r requirements.txt
```

## Launch
```bash
cd teleoperation_system_RobotPC
conda activate teleoperate-RobotPC
./run_host_broadcast.sh
```

## Options
- `--left_arm_port`: Left arm CAN port (default: left_piper)
- `--right_arm_port`: Right arm CAN port (default: right_piper)
- `--port_zmq_cmd`: Command receive port (default: 5555)
- `--max_loop_freq_hz`: Loop frequency (default: 60Hz)
