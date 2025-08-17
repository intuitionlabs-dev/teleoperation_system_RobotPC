#!/usr/bin/env python3
"""
Log robot joint commands from the teleoperation system output.
Captures the Final: J0=..., J1=..., etc. debug output and saves to a log file.
"""

import sys
import re
import time
from datetime import datetime
from pathlib import Path
import json


def parse_joint_command(line):
    """Parse a debug line to extract arm name and joint values."""
    # Pattern: [DEBUG left_piper] Final: J0=7336, J1=2704, J2=0, J3=0, J4=64331, J5=-54295, J6=55762
    pattern = r'\[DEBUG (\w+)\] Final: J0=(-?\d+), J1=(-?\d+), J2=(-?\d+), J3=(-?\d+), J4=(-?\d+), J5=(-?\d+), J6=(-?\d+)'
    match = re.search(pattern, line)
    
    if match:
        arm = match.group(1)
        joints = [int(match.group(i)) for i in range(2, 9)]  # J0-J6
        return arm, joints
    return None, None


def main():
    # Create log directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"joint_commands_{timestamp}.jsonl"
    
    print(f"Logging joint commands to: {log_file}")
    print("Reading from stdin... (pipe the host_broadcast.py output here)")
    print("Press Ctrl+C to stop logging")
    
    command_count = 0
    
    try:
        with open(log_file, 'w') as f:
            for line in sys.stdin:
                # Print the line as is (pass-through)
                print(line, end='')
                
                # Check if this is a joint command line
                arm, joints = parse_joint_command(line)
                if arm and joints:
                    # Create log entry
                    log_entry = {
                        'timestamp': time.time(),
                        'datetime': datetime.now().isoformat(),
                        'arm': arm,
                        'joints': {
                            'J0': joints[0],
                            'J1': joints[1],
                            'J2': joints[2],
                            'J3': joints[3],
                            'J4': joints[4],
                            'J5': joints[5],
                            'J6': joints[6]
                        }
                    }
                    
                    # Write as JSON line
                    f.write(json.dumps(log_entry) + '\n')
                    f.flush()  # Ensure immediate write
                    command_count += 1
                    
    except KeyboardInterrupt:
        print(f"\n\nLogging stopped. Recorded {command_count} commands to {log_file}")
    except Exception as e:
        print(f"\nError during logging: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
