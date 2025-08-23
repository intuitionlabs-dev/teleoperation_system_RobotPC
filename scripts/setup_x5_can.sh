#!/bin/bash
# Setup CAN interfaces for X5 robots

# Setup can0 (right arm)
sudo ip link set can0 down 2>/dev/null || true
sudo slcand -o -c -f -s8 /dev/ttyACM0 can0 2>/dev/null || true
sudo ip link set can0 up 2>/dev/null || true
sudo ip link set can0 txqueuelen 1000 2>/dev/null || true

# Setup can1 (left arm)  
sudo ip link set can1 down 2>/dev/null || true
sudo slcand -o -c -f -s8 /dev/ttyACM1 can1 2>/dev/null || true
sudo ip link set can1 up 2>/dev/null || true
sudo ip link set can1 txqueuelen 1000 2>/dev/null || true

echo "CAN interfaces setup complete"
