#!/bin/bash
# Fix CAN interfaces

echo "Fixing CAN interfaces..."
echo "=========================="

# Function to reset a CAN interface
reset_can_interface() {
    local interface=$1
    echo ""
    echo "Resetting $interface..."
    
    # Bring down the interface
    echo "  Bringing down $interface..."
    sudo ip link set $interface down
    
    # Clear any error states
    echo "  Clearing error states..."
    sudo ip link set $interface type can restart-ms 100
    
    # Set bitrate and bring up
    echo "  Setting bitrate and bringing up..."
    sudo ip link set $interface up type can bitrate 1000000
    
    # Check status
    echo "  Checking status..."
    ip -details link show $interface | grep -E "state|can"
    
    # Check for errors
    echo "  Checking statistics..."
    ip -s link show $interface | grep -A2 "RX:\|TX:"
}

# Reset both interfaces
reset_can_interface can_follow_l
reset_can_interface can_follow_r

echo ""
echo "=========================="
echo "CAN interfaces reset complete"
echo ""

# Test if they're working
echo "Testing CAN interfaces..."
echo "------------------------"

# Try candump for a second to see if there's any traffic
echo "Listening on can_follow_l for 1 second..."
timeout 1 candump can_follow_l 2>/dev/null || echo "No traffic detected"

echo "Listening on can_follow_r for 1 second..."
timeout 1 candump can_follow_r 2>/dev/null || echo "No traffic detected"

echo ""
echo "If you still see errors, try:"
echo "  1. Check physical CAN connections"
echo "  2. Ensure 120Ω termination resistors are in place at both ends"
echo "  3. Power cycle the motors"
echo "  4. Check if the correct CAN transceiver is being used"