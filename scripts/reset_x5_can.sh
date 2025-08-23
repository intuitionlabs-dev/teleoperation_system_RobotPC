#!/bin/bash
# Reset X5 CAN interfaces

echo "Resetting X5 CAN interfaces..."

# Down both interfaces
sudo ip link set can0 down 2>/dev/null
sudo ip link set can1 down 2>/dev/null

# Kill any existing slcand processes
sudo killall slcand 2>/dev/null

# Wait a moment
sleep 1

# Setup can1 for left arm (on ACM1)
echo "Setting up can1 (left arm) on /dev/ttyACM1..."
sudo slcand -o -c -f -s8 /dev/ttyACM1 can1
sudo ip link set can1 up
sudo ip link set can1 txqueuelen 1000

# Setup can0 for right arm (on ACM0)  
echo "Setting up can0 (right arm) on /dev/ttyACM0..."
sudo slcand -o -c -f -s8 /dev/ttyACM0 can0
sudo ip link set can0 up
sudo ip link set can0 txqueuelen 1000

# Verify
echo -e "\nVerifying CAN interfaces:"
ip link show | grep can

echo -e "\nCAN interfaces reset complete!"