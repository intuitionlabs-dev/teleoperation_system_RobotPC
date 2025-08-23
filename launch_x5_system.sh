#!/bin/bash
# Unified launch script for X5 teleoperation system using tmux
# Creates 3 tmux windows: Left arm, Right arm, Host broadcast

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SESSION_NAME="x5_teleop"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}X5 Teleoperation System Launcher${NC}"
echo -e "${GREEN}=========================================${NC}"

# Check if tmux is installed, install if needed
if ! command -v tmux &> /dev/null; then
    echo -e "${YELLOW}tmux is not installed. Installing automatically...${NC}"
    sudo apt-get update && sudo apt-get install -y tmux
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install tmux automatically${NC}"
        echo "Please install manually: sudo apt-get install tmux"
        exit 1
    fi
    echo -e "${GREEN}tmux installed successfully${NC}"
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

# Set library path for ARX module
export LD_LIBRARY_PATH=/home/group/i2rt/ARX-dynamixel/RobotLearningGello/ARX_X5/py/arx_x5_python/bimanual/lib/arx_x5_src:$LD_LIBRARY_PATH

echo -e "\n${YELLOW}Step 1: Resetting and setting up CAN interfaces for X5...${NC}"

# Function to setup CAN interfaces properly
setup_x5_can() {
    echo "Cleaning up existing CAN interfaces..."
    
    # Down both interfaces
    sudo ip link set can0 down 2>/dev/null
    sudo ip link set can1 down 2>/dev/null
    
    # Kill any existing slcand processes
    sudo killall slcand 2>/dev/null
    
    # Wait for cleanup
    sleep 1
    
    # Setup can1 for left arm (on ACM1)
    echo "Setting up can1 (left arm) on /dev/ttyACM1..."
    sudo slcand -o -c -f -s8 /dev/ttyACM1 can1
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to setup can1${NC}"
        return 1
    fi
    sudo ip link set can1 up
    sudo ip link set can1 txqueuelen 1000
    
    # Setup can0 for right arm (on ACM0)  
    echo "Setting up can0 (right arm) on /dev/ttyACM0..."
    sudo slcand -o -c -f -s8 /dev/ttyACM0 can0
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to setup can0${NC}"
        return 1
    fi
    sudo ip link set can0 up
    sudo ip link set can0 txqueuelen 1000
    
    # Verify interfaces are up
    echo -e "\nVerifying CAN interfaces:"
    can0_status=$(ip link show can0 2>/dev/null | grep -c "UP")
    can1_status=$(ip link show can1 2>/dev/null | grep -c "UP")
    
    if [ "$can0_status" -eq 0 ] || [ "$can1_status" -eq 0 ]; then
        echo -e "${RED}CAN interface verification failed!${NC}"
        ip link show | grep can
        return 1
    fi
    
    # Check for CAN traffic (give it a moment to start)
    echo "Checking CAN communication..."
    sleep 2
    
    # Check statistics
    can0_rx=$(ip -s link show can0 2>/dev/null | grep -A1 "RX:" | tail -1 | awk '{print $2}')
    can1_rx=$(ip -s link show can1 2>/dev/null | grep -A1 "RX:" | tail -1 | awk '{print $2}')
    
    echo "can0 RX packets: ${can0_rx:-0}"
    echo "can1 RX packets: ${can1_rx:-0}"
    
    if [ "${can1_rx:-0}" -eq 0 ]; then
        echo -e "${YELLOW}Warning: No traffic on can1 (left arm) yet${NC}"
        echo "This is normal if motors are not powered on"
    fi
    
    return 0
}

# Run CAN setup
setup_x5_can
if [ $? -ne 0 ]; then
    echo -e "${RED}CAN setup failed! Please check connections and try again.${NC}"
    echo "Troubleshooting:"
    echo "  1. Check USB-CAN adapters are connected to /dev/ttyACM0 and /dev/ttyACM1"
    echo "  2. Ensure X5 motors are powered on"
    echo "  3. Verify CAN cables are connected properly"
    exit 1
fi

echo -e "${GREEN}CAN interfaces configured successfully for X5${NC}"

echo -e "\n${YELLOW}Creating tmux session with 3 windows...${NC}"

# Create new detached tmux session with first window for left arm
tmux new-session -d -s $SESSION_NAME -n "X5_Left"

# Window 1: Left Arm
echo "  [1/3] Setting up X5 left arm window..."
tmux send-keys -t $SESSION_NAME:0 "cd $SCRIPT_DIR" C-m
tmux send-keys -t $SESSION_NAME:0 "export LD_LIBRARY_PATH=/home/group/i2rt/ARX-dynamixel/RobotLearningGello/ARX_X5/py/arx_x5_python/bimanual/lib/arx_x5_src:\$LD_LIBRARY_PATH" C-m
tmux send-keys -t $SESSION_NAME:0 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '==== X5 LEFT ARM - Port 6001, CAN1 ===='" C-m
tmux send-keys -t $SESSION_NAME:0 "python launch_hardware_server.py --arm left --system x5" C-m

# Wait for left arm to initialize
sleep 3

# Window 2: Right Arm
echo "  [2/3] Setting up X5 right arm window..."
tmux new-window -t $SESSION_NAME:1 -n "X5_Right"
tmux send-keys -t $SESSION_NAME:1 "cd $SCRIPT_DIR" C-m
tmux send-keys -t $SESSION_NAME:1 "export LD_LIBRARY_PATH=/home/group/i2rt/ARX-dynamixel/RobotLearningGello/ARX_X5/py/arx_x5_python/bimanual/lib/arx_x5_src:\$LD_LIBRARY_PATH" C-m
tmux send-keys -t $SESSION_NAME:1 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:1 "echo '==== X5 RIGHT ARM - Port 6003, CAN0 ===='" C-m
tmux send-keys -t $SESSION_NAME:1 "python launch_hardware_server.py --arm right --system x5" C-m

# Wait for right arm to initialize
sleep 3

# Window 3: Host Broadcast
echo "  [3/3] Setting up host broadcast window..."
tmux new-window -t $SESSION_NAME:2 -n "Host_Broadcast"
tmux send-keys -t $SESSION_NAME:2 "cd $SCRIPT_DIR" C-m
tmux send-keys -t $SESSION_NAME:2 "export LD_LIBRARY_PATH=/home/group/i2rt/ARX-dynamixel/RobotLearningGello/ARX_X5/py/arx_x5_python/bimanual/lib/arx_x5_src:\$LD_LIBRARY_PATH" C-m
tmux send-keys -t $SESSION_NAME:2 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:2 "echo '==== HOST BROADCAST - Ports 5575-5578 ===='" C-m
tmux send-keys -t $SESSION_NAME:2 "python -m host_broadcast --system x5-dynamixel" C-m

# Select the host broadcast window by default
tmux select-window -t $SESSION_NAME:2

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}✓ X5 System Launch Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Tmux session '$SESSION_NAME' created with 3 windows:"
echo "  Window 0: X5 Left Arm Server (port 6001, can1)"
echo "  Window 1: X5 Right Arm Server (port 6003, can0)"
echo "  Window 2: Host Broadcast (ports 5575-5578)"
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