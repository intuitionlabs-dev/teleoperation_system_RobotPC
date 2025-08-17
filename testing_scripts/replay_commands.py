#!/usr/bin/env python3
"""
Replay logged robot joint commands using the Piper SDK.
Reads commands from a log file and sends them to the robot arms.
"""

import json
import time
import argparse
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from piper_sdk_interface import PiperSDKInterface


class CommandReplayer:
    def __init__(self, left_port="left_piper", right_port="right_piper"):
        """Initialize the replayer with both robot arms."""
        print("Initializing robot arms...")
        
        # Initialize SDK interfaces (will handle motor enabling internally)
        self.left_arm = PiperSDKInterface(port=left_port)
        self.right_arm = PiperSDKInterface(port=right_port)
        
        # Enable motors
        print("Enabling motors...")
        self.left_arm.enable_motors()
        self.right_arm.enable_motors()
        
        print("Robot arms ready for replay")
        
    def send_raw_command(self, arm_name, joints):
        """Send raw joint command values directly to the robot."""
        # Determine which arm to use
        if arm_name == "left_piper":
            sdk = self.left_arm
        elif arm_name == "right_piper":
            sdk = self.right_arm
        else:
            print(f"Unknown arm: {arm_name}")
            return
        
        # Send command using same logic as original
        try:
            # Set MIT control mode
            sdk.piper.MotionCtrl_2(0x01, 0x01, 100, 0xAD)
            
            # Send joint command (values are already in 0.001 degree units)
            sdk.piper.JointCtrl(
                joints['J0'], joints['J1'], joints['J2'],
                joints['J3'], joints['J4'], joints['J5']
            )
            
            # Send gripper command
            sdk.piper.GripperCtrl(joints['J6'], 1000, 0x01, 0)
            
        except Exception as e:
            print(f"Error sending command to {arm_name}: {e}")
    
    def replay_file(self, log_file, speed_factor=1.0, loop=False):
        """Replay commands from a log file."""
        print(f"Replaying commands from: {log_file}")
        print(f"Speed factor: {speed_factor}x")
        print(f"Loop: {loop}")
        print("Press Ctrl+C to stop")
        
        try:
            while True:  # Outer loop for looping functionality
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                if not lines:
                    print("No commands in log file")
                    return
                
                print(f"\nReplaying {len(lines)} commands...")
                
                # Parse all commands
                commands = []
                for line in lines:
                    try:
                        cmd = json.loads(line.strip())
                        commands.append(cmd)
                    except json.JSONDecodeError:
                        continue
                
                if not commands:
                    print("No valid commands found")
                    return
                
                # Calculate time delays
                start_time = commands[0]['timestamp']
                replay_start = time.time()
                
                for i, cmd in enumerate(commands):
                    # Calculate when this command should be sent
                    cmd_time = cmd['timestamp'] - start_time
                    target_time = replay_start + (cmd_time / speed_factor)
                    
                    # Wait until it's time to send this command
                    wait_time = target_time - time.time()
                    if wait_time > 0:
                        time.sleep(wait_time)
                    
                    # Send the command
                    print(f"\r[{i+1}/{len(commands)}] Sending command to {cmd['arm']}...", end='', flush=True)
                    self.send_raw_command(cmd['arm'], cmd['joints'])
                
                print(f"\nReplay complete!")
                
                if not loop:
                    break
                
                print("\nLooping... Press Ctrl+C to stop")
                time.sleep(1)  # Brief pause before looping
                
        except KeyboardInterrupt:
            print("\n\nReplay stopped by user")
        except Exception as e:
            print(f"\n\nError during replay: {e}")
            raise
    
    def close(self):
        """Clean up resources."""
        print("\nDisabling motors...")
        self.left_arm.disable_motors()
        self.right_arm.disable_motors()


def main():
    parser = argparse.ArgumentParser(description='Replay logged robot commands')
    parser.add_argument('log_file', help='Path to the log file (JSONL format)')
    parser.add_argument('--speed', type=float, default=1.0,
                        help='Playback speed factor (default: 1.0)')
    parser.add_argument('--loop', action='store_true',
                        help='Loop the replay continuously')
    parser.add_argument('--left-port', default='left_piper',
                        help='Left arm CAN port (default: left_piper)')
    parser.add_argument('--right-port', default='right_piper',
                        help='Right arm CAN port (default: right_piper)')
    
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
                for f in sorted(log_files):
                    print(f"  - {f.name}")
        sys.exit(1)
    
    # Create replayer and run
    replayer = CommandReplayer(args.left_port, args.right_port)
    
    try:
        replayer.replay_file(log_file, args.speed, args.loop)
    finally:
        replayer.close()


if __name__ == "__main__":
    main()
