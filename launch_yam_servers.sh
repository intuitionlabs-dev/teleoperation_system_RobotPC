#!/bin/bash
# Launch YAM hardware servers for teleoperation

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment
VENV_PATH="$SCRIPT_DIR/../i2rt/gello_software/.venv"
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
else
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Add i2rt to PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR/../i2rt:$PYTHONPATH"

# Navigate to gello_software directory
cd "$SCRIPT_DIR/../i2rt/gello_software"

echo "Starting YAM left arm hardware server on port 6001..."
python experiments/launch_yaml.py \
    --left-config-path configs/yam_auto_generated_left.yaml &
LEFT_PID=$!

# Wait for left server to initialize
sleep 5

echo "Starting YAM right arm hardware server on port 6003..."
# Need to modify the port in the config or pass it as parameter
python -c "
import sys
sys.path.insert(0, '.')
from experiments.launch_yaml import main
import experiments.launch_yaml as launch_module

# Temporarily override the hardware port
original_main = launch_module.main
def modified_main():
    import experiments.launch_yaml
    # Store original cfg.get
    original_get = dict.get
    def modified_get(self, key, default=None):
        if key == 'hardware_server_port':
            return 6003
        return original_get(self, key, default)
    dict.get = modified_get
    original_main()
    dict.get = original_get

launch_module.main = modified_main
main()
" --left-config-path configs/yam_auto_generated_right.yaml &
RIGHT_PID=$!

echo "YAM hardware servers started:"
echo "  Left arm server PID: $LEFT_PID (port 6001)"
echo "  Right arm server PID: $RIGHT_PID (port 6003)"

# Function to kill servers on exit
cleanup() {
    echo "Stopping YAM hardware servers..."
    kill $LEFT_PID 2>/dev/null
    kill $RIGHT_PID 2>/dev/null
}

trap cleanup EXIT

# Wait for servers
wait