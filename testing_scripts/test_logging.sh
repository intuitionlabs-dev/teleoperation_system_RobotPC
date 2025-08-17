#!/bin/bash
# Test script to demonstrate logging and plotting functionality

echo "Testing logging script with sample data..."
echo "This will generate sample joint movements and create plots..."

# Create some sample output that mimics the teleoperation system
# Simulate a simple sine wave motion for demonstration
{
    echo "[SDK] Starting system..."
    
    # Generate 50 samples of joint movements
    for i in {0..49}; do
        # Calculate sine wave values for smooth motion
        angle=$(echo "scale=4; $i * 3.14159 / 25" | bc -l)
        
        # Left arm - varying J0, J1, J4
        j0_left=$(echo "scale=0; 7000 + 3000 * s($angle)" | bc -l | cut -d. -f1)
        j1_left=$(echo "scale=0; 30000 + 20000 * c($angle)" | bc -l | cut -d. -f1)
        j4_left=$(echo "scale=0; 50000 + 15000 * s($angle * 2)" | bc -l | cut -d. -f1)
        
        # Right arm - varying J0, J2, J5
        j0_right=$(echo "scale=0; -7000 + 3000 * c($angle)" | bc -l | cut -d. -f1)
        j2_right=$(echo "scale=0; -30000 + 10000 * s($angle)" | bc -l | cut -d. -f1)
        j5_right=$(echo "scale=0; 40000 + 20000 * c($angle * 2)" | bc -l | cut -d. -f1)
        
        echo "[DEBUG left_piper] Final: J0=$j0_left, J1=$j1_left, J2=0, J3=0, J4=$j4_left, J5=-20000, J6=50000"
        echo "--------------------------------"
        
        echo "[DEBUG right_piper] Final: J0=$j0_right, J1=10000, J2=$j2_right, J3=0, J4=30000, J5=$j5_right, J6=30000"
        echo "--------------------------------"
        
        sleep 0.1
    done
    
    echo "[SDK] Test complete"
} | python testing_scripts/log_commands.py

echo ""
echo "Check the logs directory for the created log file and plots:"
echo "Log files:"
ls -la logs/joint_commands_*.jsonl | tail -5
echo ""
echo "Plot files:"
ls -la logs/curve/
