#!/usr/bin/env python3
"""
Log robot joint commands from the teleoperation system output.
Captures the Final: J0=..., J1=..., etc. debug output and saves to a log file.
Also generates plots showing joint movements over time.
"""

import sys
import re
import time
from datetime import datetime
from pathlib import Path
import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict


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


def generate_plots(joint_data, timestamp, curve_dir):
    """Generate plots for joint movements."""
    print("\nGenerating plots...")
    
    # Set up plot style
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except:
        # Fallback to default if seaborn style not available
        plt.style.use('default')
    
    # Process each arm
    for arm_name in ['left_piper', 'right_piper']:
        if arm_name not in joint_data:
            print(f"No data for {arm_name}, skipping plot")
            continue
            
        arm_data = joint_data[arm_name]
        if not arm_data['timestamps']:
            print(f"No timestamps for {arm_name}, skipping plot")
            continue
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Convert timestamps to seconds from start
        start_time = arm_data['timestamps'][0]
        time_seconds = [(t - start_time) for t in arm_data['timestamps']]
        
        # Plot each joint
        colors = plt.cm.tab10(np.linspace(0, 1, 7))
        for joint_idx in range(7):
            joint_name = f'J{joint_idx}'
            joint_values = arm_data[joint_name]
            
            # Convert from 0.001 degree units to degrees
            joint_degrees = [val / 1000.0 for val in joint_values]
            
            ax.plot(time_seconds, joint_degrees, 
                   label=f'{joint_name}', 
                   color=colors[joint_idx],
                   linewidth=2)
        
        # Customize plot
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Joint Position (degrees)', fontsize=12)
        ax.set_title(f'{arm_name.replace("_", " ").title()} - Joint Positions Over Time\n{timestamp}', 
                    fontsize=14)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Save plot
        plot_file = curve_dir / f"joint_movements_{arm_name}_{timestamp}.png"
        plt.tight_layout()
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Saved plot: {plot_file}")


def main():
    # Create log directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Create curve directory for plots
    curve_dir = log_dir / "curve"
    curve_dir.mkdir(exist_ok=True)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"joint_commands_{timestamp}.jsonl"
    
    print(f"Logging joint commands to: {log_file}")
    print(f"Plots will be saved to: {curve_dir}")
    print("Reading from stdin... (pipe the host_broadcast.py output here)")
    print("Press Ctrl+C to stop logging")
    
    command_count = 0
    
    # Store data for plotting
    joint_data = defaultdict(lambda: {
        'timestamps': [],
        'J0': [], 'J1': [], 'J2': [], 'J3': [], 
        'J4': [], 'J5': [], 'J6': []
    })
    
    try:
        with open(log_file, 'w') as f:
            for line in sys.stdin:
                # Print the line as is (pass-through)
                print(line, end='')
                
                # Check if this is a joint command line
                arm, joints = parse_joint_command(line)
                if arm and joints:
                    current_time = time.time()
                    
                    # Create log entry
                    log_entry = {
                        'timestamp': current_time,
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
                    
                    # Store data for plotting
                    joint_data[arm]['timestamps'].append(current_time)
                    for i, joint_val in enumerate(joints):
                        joint_data[arm][f'J{i}'].append(joint_val)
                    
                    command_count += 1
                    
    except KeyboardInterrupt:
        print(f"\n\nLogging stopped. Recorded {command_count} commands to {log_file}")
        
        # Generate plots if we have data
        if any(joint_data[arm]['timestamps'] for arm in joint_data):
            generate_plots(joint_data, timestamp, curve_dir)
        else:
            print("No data to plot")
            
    except Exception as e:
        print(f"\nError during logging: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
