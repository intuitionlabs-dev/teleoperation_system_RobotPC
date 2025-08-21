#!/bin/bash

# Comprehensive CAN and motor cleanup script
# Run this before starting any motor control programs

echo "========================================="
echo "CAN and Motor Cleanup Script"
echo "========================================="

# Function to forcefully reset a CAN interface
forceful_reset_can() {
    local interface=$1
    echo ""
    echo "Forcefully resetting $interface..."
    
    # Kill any processes using the CAN interface
    echo "  Killing processes using $interface..."
    sudo lsof 2>/dev/null | grep -w "$interface" | awk '{print $2}' | sort -u | xargs -r sudo kill -9 2>/dev/null
    
    # Force the interface down
    echo "  Force bringing down $interface..."
    sudo ip link set "$interface" down 2>/dev/null || true
    
    # Clear any bus-off or error states
    echo "  Clearing error states..."
    sudo ip link set "$interface" type can restart 2>/dev/null || true
    sudo ip link set "$interface" type can restart-ms 100 2>/dev/null || true
    
    # Wait a moment for the interface to settle
    sleep 0.5
    
    # Reconfigure and bring up the interface
    echo "  Reconfiguring $interface with bitrate 1000000..."
    sudo ip link set "$interface" up type can bitrate 1000000 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "  ✓ $interface successfully reset"
    else
        echo "  ⚠ Failed to bring up $interface, trying alternative method..."
        # Alternative method: delete and recreate
        sudo ip link delete "$interface" 2>/dev/null || true
        sleep 0.5
        # The interface should be recreated automatically by the system
        sudo ip link set "$interface" up type can bitrate 1000000 2>/dev/null
    fi
    
    # Verify the interface is up
    if ip link show "$interface" | grep -q "UP"; then
        echo "  ✓ $interface is UP"
    else
        echo "  ✗ Warning: $interface is not UP"
    fi
}

# Function to flush CAN buffer
flush_can_buffer() {
    local interface=$1
    echo "  Flushing $interface buffer..."
    # Use candump with timeout to flush any pending messages
    timeout 0.1 candump "$interface" -n 100 2>/dev/null >/dev/null || true
    # Also try to read with cansend to clear transmit queue
    sudo tc qdisc del dev "$interface" root 2>/dev/null || true
}

# Main cleanup process
echo ""
echo "Step 1: Killing any Python processes using motor drivers"
echo "---------------------------------------------------------"
pkill -f "motor_chain_robot.py" 2>/dev/null || true
pkill -f "dm_driver.py" 2>/dev/null || true
pkill -f "yam" 2>/dev/null || true
sleep 0.5

echo ""
echo "Step 2: Detecting CAN interfaces"
echo "---------------------------------"
can_interfaces=$(ip link show | grep -oP '(?<=: )(can\w+)' || true)

if [ -z "$can_interfaces" ]; then
    echo "No CAN interfaces found."
    echo "You may need to set up the CAN interfaces first."
    exit 1
fi

echo "Found CAN interfaces: $can_interfaces"

echo ""
echo "Step 3: Resetting CAN interfaces"
echo "---------------------------------"
for iface in $can_interfaces; do
    forceful_reset_can "$iface"
    flush_can_buffer "$iface"
done

echo ""
echo "Step 4: Verifying CAN interfaces"
echo "---------------------------------"
for iface in $can_interfaces; do
    echo -n "  $iface: "
    if ip link show "$iface" | grep -q "UP"; then
        # Check bitrate
        bitrate=$(ip -details link show "$iface" | grep -oP 'bitrate \K[0-9]+' || echo "unknown")
        echo "UP (bitrate: $bitrate)"
    else
        echo "DOWN - Warning!"
    fi
done

echo ""
echo "Step 5: Testing CAN communication"
echo "----------------------------------"
for iface in $can_interfaces; do
    echo "  Testing $iface..."
    # Send a test message to see if the bus is working
    # Using a safe arbitration ID that shouldn't interfere with motors
    cansend "$iface" "7FF#00" 2>/dev/null && echo "    ✓ Can send on $iface" || echo "    ✗ Cannot send on $iface"
done

echo ""
echo "========================================="
echo "Cleanup Complete!"
echo "========================================="
echo ""
echo "CAN interfaces have been reset and cleaned."
echo "You can now run your motor control programs."
echo ""
echo "If you still experience issues:"
echo "  1. Power cycle the motor controllers"
echo "  2. Check physical CAN connections"
echo "  3. Verify termination resistors (120Ω) are in place"
echo "  4. Try unplugging and replugging USB-CAN adapters"
echo ""