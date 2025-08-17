#!/bin/bash
# Script to run the host broadcast for bimanual Piper robot

python -m host_broadcast \
    --left_arm_port left_piper \
    --right_arm_port right_piper \
    --port_zmq_cmd 5555 \
    --port_zmq_observations 5556 \
    --port_cmd_broadcast 5557 \
    --port_obs_broadcast 5558