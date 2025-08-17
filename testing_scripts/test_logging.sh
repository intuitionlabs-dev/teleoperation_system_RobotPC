#!/bin/bash
# Test script to demonstrate logging functionality

echo "Testing logging script with sample data..."

# Create some sample output that mimics the teleoperation system
{
    echo "[SDK] Starting system..."
    echo "[DEBUG left_piper] Final: J0=7336, J1=2704, J2=0, J3=0, J4=64331, J5=-54295, J6=55762"
    echo "--------------------------------"
    sleep 0.5
    echo "[DEBUG right_piper] Final: J0=-6754, J1=0, J2=-2232, J3=0, J4=68802, J5=47647, J6=1229"
    echo "--------------------------------"
    sleep 0.5
    echo "[DEBUG left_piper] Final: J0=3369, J1=76245, J2=-52792, J3=0, J4=-10903, J5=-4746, J6=49157"
    echo "--------------------------------"
    sleep 0.5
    echo "[DEBUG right_piper] Final: J0=-11279, J1=34760, J2=-47480, J3=0, J4=-20576, J5=-10546, J6=50647"
    echo "--------------------------------"
    echo "[SDK] Test complete"
} | python testing_scripts/log_commands.py

echo ""
echo "Check the logs directory for the created log file"
ls -la logs/
