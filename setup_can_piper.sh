#!/bin/bash
# Setup CAN interfaces for dual Piper arms

echo "Setting up CAN interfaces for dual Piper arms..."

# Load the gs_usb module
sudo modprobe gs_usb

# Get list of CAN interfaces
CAN_INTERFACES=$(ip -br link show type can | awk '{print $1}')

if [ -z "$CAN_INTERFACES" ]; then
    echo "Error: No CAN interfaces detected. Please ensure the CAN-USB adapters are connected."
    exit 1
fi

# Convert to array
CAN_ARRAY=($CAN_INTERFACES)
NUM_INTERFACES=${#CAN_ARRAY[@]}

echo "Found $NUM_INTERFACES CAN interface(s): ${CAN_ARRAY[*]}"

if [ $NUM_INTERFACES -lt 2 ]; then
    echo "Error: Need at least 2 CAN interfaces for dual Piper setup, found $NUM_INTERFACES"
    exit 1
fi

# Setup left Piper arm
LEFT_CAN=${CAN_ARRAY[0]}
echo "Configuring $LEFT_CAN as left_piper..."
sudo ip link set $LEFT_CAN down
sudo ip link set $LEFT_CAN type can bitrate 1000000
sudo ip link set $LEFT_CAN name left_piper
sudo ip link set left_piper up

# Setup right Piper arm
RIGHT_CAN=${CAN_ARRAY[1]}
echo "Configuring $RIGHT_CAN as right_piper..."
sudo ip link set $RIGHT_CAN down
sudo ip link set $RIGHT_CAN type can bitrate 1000000
sudo ip link set $RIGHT_CAN name right_piper
sudo ip link set right_piper up

echo "CAN interfaces configured successfully!"
echo "  - left_piper (was $LEFT_CAN)"
echo "  - right_piper (was $RIGHT_CAN)"

# Verify setup
echo ""
echo "Current CAN interfaces:"
ip link show type can