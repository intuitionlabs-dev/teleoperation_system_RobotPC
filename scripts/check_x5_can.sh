#!/bin/bash
# Script to check X5 CAN communication

echo "========================================"
echo "X5 CAN Communication Check"
echo "========================================"

# Check CAN interfaces
echo -e "\n1. CAN Interface Status:"
ip link show | grep can

# Check CAN statistics
echo -e "\n2. CAN Statistics:"
for can in can0 can1; do
    if ip link show $can &>/dev/null; then
        echo "$can statistics:"
        ip -details -statistics link show $can | grep -A 5 "RX:"
    fi
done

# Try to dump CAN traffic
echo -e "\n3. Testing CAN traffic (5 seconds):"
echo "Monitoring can0..."
timeout 2 candump can0 2>/dev/null | head -5 &
echo "Monitoring can1..."  
timeout 2 candump can1 2>/dev/null | head -5 &
wait

# Check USB devices
echo -e "\n4. USB-CAN Adapters:"
ls -la /dev/ttyACM* 2>/dev/null || echo "No ACM devices found"

echo -e "\n========================================"
echo "If you see 'No buffer space available' errors,"
echo "the CAN interface might need reconfiguration."
echo ""
echo "To reset CAN interfaces:"
echo "  sudo ip link set can0 down"
echo "  sudo ip link set can1 down"
echo "  sudo slcand -o -c -f -s8 /dev/ttyACM0 can0"
echo "  sudo slcand -o -c -f -s8 /dev/ttyACM1 can1"
echo "  sudo ip link set can0 up"
echo "  sudo ip link set can1 up"
echo "========================================"