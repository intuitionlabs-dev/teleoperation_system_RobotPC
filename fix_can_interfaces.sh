#!/bin/bash
# Script to fix CAN interface issues for Piper robot

echo "Checking and fixing CAN interfaces..."

# Check if CAN interfaces exist
if ! ip link show left_piper &>/dev/null; then
    echo "Creating left_piper CAN interface..."
    sudo ip link add dev left_piper type can
fi

if ! ip link show right_piper &>/dev/null; then
    echo "Creating right_piper CAN interface..."
    sudo ip link add dev right_piper type can
fi

# Set CAN bitrate and bring interfaces up
echo "Configuring CAN interfaces..."
sudo ip link set left_piper type can bitrate 1000000
sudo ip link set right_piper type can bitrate 1000000

sudo ip link set left_piper up
sudo ip link set right_piper up

# Check status
echo ""
echo "CAN Interface Status:"
ip link show left_piper
ip link show right_piper

echo ""
echo "Testing CAN communication..."
# Try sending a test message
timeout 1 candump left_piper &
timeout 1 candump right_piper &

echo ""
echo "CAN interfaces configured. If you still see errors:"
echo "1. Check physical CAN connections"
echo "2. Verify robot power is on"
echo "3. Check CAN termination resistors (120 ohm)"
echo "4. Run: dmesg | grep -i can"