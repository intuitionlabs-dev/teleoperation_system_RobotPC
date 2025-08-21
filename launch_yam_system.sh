#!/bin/bash
# Unified launch script for YAM teleoperation system
# This script launches both hardware servers and the host broadcast

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}YAM Teleoperation System Launcher${NC}"
echo -e "${GREEN}=========================================${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down all processes...${NC}"
    
    # Kill all child processes
    jobs -p | xargs -r kill 2>/dev/null
    
    # Kill processes by name as backup
    pkill -f "launch_hardware_server.py" 2>/dev/null
    pkill -f "host_broadcast" 2>/dev/null
    
    echo -e "${GREEN}Cleanup complete${NC}"
    exit 0
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Step 1: Clean CAN interfaces
echo -e "\n${YELLOW}Step 1: Cleaning CAN interfaces...${NC}"
if [ -f "scripts/cleanup_can_motors.sh" ]; then
    # Run in subshell to prevent early exit
    (sh scripts/cleanup_can_motors.sh)
    (sh scripts/force_reset_can.sh)
elif [ -f "../scripts/cleanup_can_motors.sh" ]; then
    # Fallback to parent directory if needed
    (sh ../scripts/cleanup_can_motors.sh)
    (sh ../scripts/force_reset_can.sh)
else
    echo -e "${RED}Warning: CAN cleanup scripts not found${NC}"
    echo -e "${RED}Please run manually:${NC}"
    echo "  sh scripts/cleanup_can_motors.sh"
    echo "  sh scripts/force_reset_can.sh"
fi

# Step 2: Activate virtual environment
echo -e "\n${YELLOW}Step 2: Setting up environment...${NC}"
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating with uv..."
    uv venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Step 3: Launch left arm hardware server
echo -e "\n${YELLOW}Step 3: Launching left arm hardware server...${NC}"
python launch_hardware_server.py --arm left &
LEFT_PID=$!
echo "Left arm server PID: $LEFT_PID"

# Wait a bit for left arm to initialize
sleep 3

# Step 4: Launch right arm hardware server
echo -e "\n${YELLOW}Step 4: Launching right arm hardware server...${NC}"
python launch_hardware_server.py --arm right &
RIGHT_PID=$!
echo "Right arm server PID: $RIGHT_PID"

# Wait for hardware servers to be ready
sleep 3

# Step 5: Launch host broadcast
echo -e "\n${YELLOW}Step 5: Launching host broadcast...${NC}"
python -m host_broadcast --system yam-dynamixel &
BROADCAST_PID=$!
echo "Host broadcast PID: $BROADCAST_PID"

# Summary
echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}System Launch Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Running processes:"
echo "  - Left arm server (PID: $LEFT_PID) on port 6001"
echo "  - Right arm server (PID: $RIGHT_PID) on port 6003"
echo "  - Host broadcast (PID: $BROADCAST_PID) on ports 5565-5568"
echo ""
echo "The system is ready to receive commands from the remote operator."
echo "Press Ctrl+C to stop all processes."
echo ""

# Keep script running
wait