#!/bin/bash

# Force reset CAN interfaces - more aggressive version
# Use when normal reset doesn't work

echo "========================================="
echo "FORCE RESET CAN - Aggressive Mode"
echo "========================================="

# Check for sudo
if [ "$EUID" -ne 0 ]; then 
    echo "This script requires sudo. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

# Function to completely remove and recreate a CAN interface
nuclear_reset_can() {
    local interface=$1
    echo ""
    echo "Nuclear reset of $interface..."
    
    # Step 1: Kill ALL processes that might be using CAN
    echo "  [1/7] Terminating all CAN-related processes..."
    pkill -9 -f "can" 2>/dev/null || true
    pkill -9 -f "motor" 2>/dev/null || true
    pkill -9 -f "dm_driver" 2>/dev/null || true
    pkill -9 -f "yam" 2>/dev/null || true
    pkill -9 -f "python.*robot" 2>/dev/null || true
    
    # Step 2: Force down the interface
    echo "  [2/7] Force stopping $interface..."
    ip link set "$interface" down 2>/dev/null || true
    sleep 0.2
    
    # Step 3: Remove all qdisc
    echo "  [3/7] Removing traffic control..."
    tc qdisc del dev "$interface" root 2>/dev/null || true
    
    # Step 4: Reset module if it's USB-based
    echo "  [4/7] Checking for USB reset..."
    # Find USB device for the CAN adapter
    for usb in /sys/bus/usb/devices/*; do
        if [ -e "$usb/interface" ]; then
            if grep -q "CAN" "$usb/interface" 2>/dev/null; then
                echo "    Found USB CAN device, resetting..."
                echo "0" > "$usb/authorized" 2>/dev/null || true
                sleep 0.5
                echo "1" > "$usb/authorized" 2>/dev/null || true
                sleep 1
            fi
        fi
    done
    
    # Step 5: Try to unload and reload kernel module
    echo "  [5/7] Reloading kernel modules..."
    # Common CAN modules
    for module in can_raw can vcan slcan gs_usb peak_usb; do
        if lsmod | grep -q "^$module "; then
            rmmod "$module" 2>/dev/null || true
            sleep 0.1
            modprobe "$module" 2>/dev/null || true
        fi
    done
    
    # Step 6: Configure the interface
    echo "  [6/7] Configuring $interface..."
    # First try normal configuration
    ip link set "$interface" type can bitrate 1000000 2>/dev/null
    
    # Try with different queue lengths and restart settings
    ip link set "$interface" type can bitrate 1000000 restart-ms 100 2>/dev/null || true
    ip link set "$interface" txqueuelen 1000 2>/dev/null || true
    
    # Step 7: Bring up the interface
    echo "  [7/7] Bringing up $interface..."
    ip link set "$interface" up 2>/dev/null
    
    # Give it a moment to stabilize
    sleep 0.5
}

# Main process
echo ""
echo "Starting aggressive CAN reset process..."
echo ""

# Get all CAN interfaces
can_interfaces=$(ip link show 2>/dev/null | grep -oP '(?<=: )(can\w+)' || true)

if [ -z "$can_interfaces" ]; then
    echo "ERROR: No CAN interfaces found!"
    echo ""
    echo "Trying to detect disconnected interfaces..."
    
    # Check dmesg for CAN devices
    dmesg | tail -50 | grep -i "can" || true
    
    echo ""
    echo "You may need to:"
    echo "  1. Reconnect USB-CAN adapters"
    echo "  2. Load CAN kernel modules: sudo modprobe can can_raw"
    echo "  3. Check hardware connections"
    exit 1
fi

echo "Detected CAN interfaces: $can_interfaces"
echo ""

# Reset each interface
for iface in $can_interfaces; do
    nuclear_reset_can "$iface"
done

# Verification
echo ""
echo "========================================="
echo "Verification"
echo "========================================="

for iface in $can_interfaces; do
    echo ""
    echo "Interface: $iface"
    echo "-----------------"
    
    # Check if UP
    if ip link show "$iface" 2>/dev/null | grep -q "state UP"; then
        echo "  Status: UP ✓"
    else
        echo "  Status: DOWN ✗"
        echo "  Attempting one more bring-up..."
        ip link set "$iface" down 2>/dev/null || true
        sleep 0.2
        ip link set "$iface" up type can bitrate 1000000 2>/dev/null || true
        sleep 0.2
        if ip link show "$iface" 2>/dev/null | grep -q "state UP"; then
            echo "  Status: NOW UP ✓"
        else
            echo "  Status: STILL DOWN ✗"
        fi
    fi
    
    # Show details
    echo "  Details:"
    ip -details -statistics link show "$iface" 2>/dev/null | grep -E "(bitrate|state|qlen)" | sed 's/^/    /'
    
    # Test send
    echo "  Testing send capability..."
    if cansend "$iface" "7FF#00" 2>/dev/null; then
        echo "    Can send: YES ✓"
    else
        echo "    Can send: NO ✗"
    fi
done

echo ""
echo "========================================="
echo "Force Reset Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Run your motor program: python i2rt/robots/motor_chain_robot.py --channel can_follow_l --gripper_type yam_compact_small"
echo "  2. If still failing, power cycle the motor controllers"
echo "  3. If issues persist, unplug and replug the CAN adapter"
echo ""