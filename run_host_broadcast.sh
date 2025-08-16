#!/bin/bash
# Simple launch script for Robot PC host broadcast

echo "Starting minimal host broadcast..."
echo "Make sure the conda environment 'lerobot' is activated"
echo ""

# Run with default settings (can override with command line args)
python host_broadcast.py \
    --left_arm_port left_piper \
    --right_arm_port right_piper \
    --port_zmq_cmd 5555 \
    --max_loop_freq_hz 60 \
    "$@"
