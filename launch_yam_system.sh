#!/bin/bash
# Unified launch script for YAM teleoperation system using tmux
# Creates 4 tmux windows: CAN cleanup, Left arm, Right arm, Host broadcast

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SESSION_NAME="yam_teleop"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}YAM Teleoperation System Launcher${NC}"
echo -e "${GREEN}=========================================${NC}"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}Error: tmux is not installed${NC}"
    echo "Please install tmux: sudo apt-get install tmux"
    exit 1
fi

# Kill existing session if it exists
echo "Cleaning up any existing sessions..."
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
fi

echo -e "\n${YELLOW}Step 1: Resetting CAN interfaces...${NC}"
# Only run the CAN reset, not the process killer
# The force_reset_can.sh doesn't kill processes, just resets CAN
if [ -f "scripts/force_reset_can.sh" ]; then
    sh scripts/force_reset_can.sh
    echo -e "${GREEN}CAN interfaces reset${NC}"
else
    echo -e "${YELLOW}Warning: force_reset_can.sh not found, skipping CAN reset${NC}"
fi

echo -e "\n${YELLOW}Creating tmux session with 3 windows...${NC}"

# Create new detached tmux session with first window for left arm
tmux new-session -d -s $SESSION_NAME -n "Left_Arm"

# Window 1: Left Arm
echo "  [1/3] Setting up left arm window..."
tmux send-keys -t $SESSION_NAME:0 "cd $SCRIPT_DIR" C-m
tmux send-keys -t $SESSION_NAME:0 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '==== LEFT ARM - Port 6001 ===='" C-m
tmux send-keys -t $SESSION_NAME:0 "python launch_hardware_server.py --arm left" C-m

# Wait for left arm to initialize
sleep 3

# Window 2: Right Arm
echo "  [2/3] Setting up right arm window..."
tmux new-window -t $SESSION_NAME:1 -n "Right_Arm"
tmux send-keys -t $SESSION_NAME:1 "cd $SCRIPT_DIR" C-m
tmux send-keys -t $SESSION_NAME:1 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:1 "echo '==== RIGHT ARM - Port 6003 ===='" C-m
tmux send-keys -t $SESSION_NAME:1 "python launch_hardware_server.py --arm right" C-m

# Wait for right arm to initialize
sleep 3

# Window 3: Host Broadcast
echo "  [3/3] Setting up host broadcast window..."
tmux new-window -t $SESSION_NAME:2 -n "Host_Broadcast"
tmux send-keys -t $SESSION_NAME:2 "cd $SCRIPT_DIR" C-m
tmux send-keys -t $SESSION_NAME:2 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:2 "echo '==== HOST BROADCAST - Ports 5565-5568 ===='" C-m
tmux send-keys -t $SESSION_NAME:2 "python -m host_broadcast --system yam-dynamixel" C-m

# Select the host broadcast window by default
tmux select-window -t $SESSION_NAME:2

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}✓ System Launch Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Tmux session '$SESSION_NAME' created with 3 windows:"
echo "  Window 0: Left Arm Server (port 6001)"
echo "  Window 1: Right Arm Server (port 6003)"
echo "  Window 2: Host Broadcast (ports 5565-5568)"
echo ""
echo -e "${YELLOW}Commands:${NC}"
echo "  View session:  tmux attach -t $SESSION_NAME"
echo "  Stop all:      tmux kill-session -t $SESSION_NAME"
echo "  List windows:  tmux list-windows -t $SESSION_NAME"
echo ""
echo -e "${YELLOW}Inside tmux:${NC}"
echo "  Ctrl-b + 0-2:  Switch to window 0-2"
echo "  Ctrl-b + n:    Next window"
echo "  Ctrl-b + p:    Previous window"
echo "  Ctrl-b + d:    Detach (keeps running)"
echo ""
echo -e "${GREEN}System is running in background. Attach to view.${NC}"