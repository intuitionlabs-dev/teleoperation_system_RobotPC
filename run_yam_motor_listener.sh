#!/bin/bash
# Launch script for YAM motor enable listener

# Activate virtual environment
source /home/group/i2rt/gello_software/.venv/bin/activate

# Default configuration
LEFT_CAN="can_follow_l"
RIGHT_CAN="can_follow_r"
PORT=5569
MODE="partial"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --left-can)
            LEFT_CAN="$2"
            shift 2
            ;;
        --right-can)
            RIGHT_CAN="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--left-can CAN] [--right-can CAN] [--port PORT] [--mode MODE]"
            echo "  --left-can: Left arm CAN channel (default: can_follow_l)"
            echo "  --right-can: Right arm CAN channel (default: can_follow_r)"
            echo "  --port: Listen port (default: 5569)"
            echo "  --mode: Default enable mode - partial or full (default: partial)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting YAM Motor Enable Listener"
echo "Left CAN: $LEFT_CAN"
echo "Right CAN: $RIGHT_CAN"
echo "Listen port: $PORT"
echo "Default mode: $MODE"

python yam_motor_enable_listener.py \
    --left-can "$LEFT_CAN" \
    --right-can "$RIGHT_CAN" \
    --port "$PORT" \
    --mode "$MODE"