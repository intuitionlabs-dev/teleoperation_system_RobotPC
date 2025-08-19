#!/bin/bash
# Script to run the host broadcast for bimanual robots (Piper or YAM)

# Default configuration
SYSTEM="piper-so101"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --system)
            SYSTEM="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--system SYSTEM]"
            echo "  --system: piper-so101 or yam-dynamixel (default: piper-so101)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting robot host broadcast"
echo "System: $SYSTEM"

# Activate virtual environment if using YAM system
if [ "$SYSTEM" = "yam-dynamixel" ]; then
    VENV_PATH="/home/francesco/meta-tele-RTX/clean_version/i2rt/gello_software/.venv"
    if [ -f "$VENV_PATH/bin/activate" ]; then
        echo "Activating virtual environment for YAM system..."
        source "$VENV_PATH/bin/activate"
    fi
fi

# Run the host broadcast with system-specific configuration
if [ "$SYSTEM" = "piper-so101" ]; then
    python -m host_broadcast \
        --system "$SYSTEM" \
        --left_arm_port left_piper \
        --right_arm_port right_piper \
        --port_zmq_cmd 5555 \
        --port_zmq_observations 5556 \
        --port_cmd_broadcast 5557 \
        --port_obs_broadcast 5558
elif [ "$SYSTEM" = "yam-dynamixel" ]; then
    python -m host_broadcast \
        --system "$SYSTEM"
    # YAM ports are automatically selected based on --system flag (5565-5568)
else
    echo "Unknown system: $SYSTEM"
    exit 1
fi