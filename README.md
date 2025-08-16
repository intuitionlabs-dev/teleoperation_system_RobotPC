# Teleoperation Host (Robot PC)

Minimal ZMQ server for bimanual Piper robot control.

## Requirements
- Python with `lerobot` conda environment
- `piper_sdk` package
- ZeroMQ (pyzmq)
- CAN interfaces: `left_piper` and `right_piper`

## Launch
```bash
conda activate lerobot
./run_host_broadcast.sh
```

## Options
- `--left_arm_port`: Left arm CAN port (default: left_piper)
- `--right_arm_port`: Right arm CAN port (default: right_piper)
- `--port_zmq_cmd`: Command receive port (default: 5555)
- `--port_zmq_observations`: Observation send port (default: 5556)
- `--max_loop_freq_hz`: Loop frequency (default: 60Hz)

## Architecture
- Receive commands via ZMQ PULL
- Send observations via ZMQ PUSH at 60Hz
- Motors auto-enabled on first command
- 35ms receive timeout for 30Hz operation
