#!/usr/bin/env python3
"""
Generate plots from existing joint command log files.
Useful for analyzing previously recorded teleoperation sessions.
"""

import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from datetime import datetime


def load_log_file(log_file):
    """Load joint data from a JSONL log file."""
    joint_data = defaultdict(lambda: {
        'timestamps': [],
        'J0': [], 'J1': [], 'J2': [], 'J3': [], 
        'J4': [], 'J5': [], 'J6': []
    })
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                arm = entry['arm']
                timestamp = entry['timestamp']
                joints = entry['joints']
                
                joint_data[arm]['timestamps'].append(timestamp)
                for joint_name, value in joints.items():
                    joint_data[arm][joint_name].append(value)
                    
            except json.JSONDecodeError:
                continue
    
    return joint_data


def generate_plots(joint_data, log_file, output_dir):
    """Generate plots for joint movements."""
    print("\nGenerating plots...")
    
    # Set up plot style
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except:
        plt.style.use('default')
    
    # Extract timestamp from filename for plot naming
    timestamp = log_file.stem.replace('joint_commands_', '')
    
    # Process each arm
    plots_generated = []
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
        
        # Add statistics
        duration = time_seconds[-1] if time_seconds else 0
        num_samples = len(time_seconds)
        avg_rate = num_samples / duration if duration > 0 else 0
        
        stats_text = f'Duration: {duration:.1f}s | Samples: {num_samples} | Avg Rate: {avg_rate:.1f} Hz'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                verticalalignment='top', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Save plot
        plot_file = output_dir / f"joint_movements_{arm_name}_{timestamp}.png"
        plt.tight_layout()
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Saved plot: {plot_file}")
        plots_generated.append(plot_file)
    
    return plots_generated


def main():
    parser = argparse.ArgumentParser(description='Generate plots from joint command log files')
    parser.add_argument('log_file', help='Path to the JSONL log file')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory for plots (default: logs/curve/)')
    
    args = parser.parse_args()
    
    # Check if log file exists
    log_file = Path(args.log_file)
    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}")
        
        # Show available log files
        log_dir = Path(__file__).parent.parent / "logs"
        if log_dir.exists():
            log_files = list(log_dir.glob("joint_commands_*.jsonl"))
            if log_files:
                print("\nAvailable log files:")
                for f in sorted(log_files)[-10:]:  # Show last 10
                    print(f"  - {f.name}")
        return 1
    
    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent.parent / "logs" / "curve"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print(f"Loading data from: {log_file}")
    joint_data = load_log_file(log_file)
    
    if not joint_data:
        print("No valid data found in log file")
        return 1
    
    # Generate plots
    plots = generate_plots(joint_data, log_file, output_dir)
    
    if plots:
        print(f"\nGenerated {len(plots)} plots in {output_dir}")
    else:
        print("\nNo plots generated")
    
    return 0


if __name__ == "__main__":
    exit(main())
