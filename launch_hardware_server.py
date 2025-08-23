#!/usr/bin/env python
"""
Hardware server launcher for YAM/X5 follower arms.
This script launches a ZMQ server that exposes the YAM or X5 robot for remote control.
"""

import argparse
import atexit
import signal
import sys
import threading
import time
from pathlib import Path

# Add local libraries to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "i2rt_lib"))

import zmq.error
from omegaconf import OmegaConf

from gello.robots.yam import YAMRobot
from gello.robots.x5 import X5Robot
from gello.zmq_core.robot_node import ZMQServerRobot

# Global variables for cleanup
active_threads = []
active_servers = []
cleanup_in_progress = False


def cleanup():
    """Clean up resources before exit."""
    global cleanup_in_progress
    if cleanup_in_progress:
        return
    cleanup_in_progress = True

    print("Cleaning up resources...")
    for server in active_servers:
        try:
            if hasattr(server, "close"):
                server.close()
        except Exception as e:
            print(f"Error closing server: {e}")

    for thread in active_threads:
        if thread.is_alive():
            thread.join(timeout=2)

    print("Cleanup completed.")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    cleanup()
    import os
    os._exit(0)


def main():
    parser = argparse.ArgumentParser(description="Launch YAM/X5 hardware server")
    parser.add_argument(
        "--arm",
        type=str,
        choices=["left", "right"],
        required=True,
        help="Which arm to launch (left or right)"
    )
    parser.add_argument(
        "--system",
        type=str,
        choices=["yam", "x5"],
        default="yam",
        help="Which robot system to use (yam or x5)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="ZMQ server port (default: 6001 for left, 6003 for right)"
    )
    parser.add_argument(
        "--can-channel",
        type=str,
        default=None,
        help="CAN channel (default: can_follow_l for left, can_follow_r for right)"
    )
    args = parser.parse_args()

    # Set defaults based on arm and system
    if args.arm == "left":
        port = args.port or 6001
        if args.system == "x5":
            can_channel = args.can_channel or "can1"  # X5 left arm uses can1
        else:
            can_channel = args.can_channel or "can_follow_l"  # YAM left arm
    else:  # right
        port = args.port or 6003
        if args.system == "x5":
            can_channel = args.can_channel or "can0"  # X5 right arm uses can0
        else:
            can_channel = args.can_channel or "can_follow_r"  # YAM right arm

    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create robot based on system type
    if args.system == "x5":
        print(f"Initializing X5 {args.arm} arm on CAN channel: {can_channel}")
        robot = X5Robot(channel=can_channel)
        system_name = "X5"
        
        # SAFETY: Read current position but don't command initially
        print(f"Reading current position of X5 {args.arm} arm...")
        try:
            current_pos = robot.get_joint_state()
            print(f"Current position: {current_pos}")
            # Don't command position initially - wait for teleoperation
            # The robot should maintain its current physical position
            print(f"X5 {args.arm} arm ready - waiting for teleoperation commands")
        except Exception as e:
            print(f"Warning: Could not read initial position: {e}")
    else:
        print(f"Initializing YAM {args.arm} arm on CAN channel: {can_channel}")
        robot = YAMRobot(channel=can_channel)
        system_name = "YAM"
    
    # Create ZMQ server for the hardware robot
    hardware_host = "127.0.0.1"
    server = ZMQServerRobot(robot, port=port, host=hardware_host)
    
    # Start server in background
    server_thread = threading.Thread(target=server.serve, daemon=False)
    server_thread.start()
    
    # Track for cleanup
    active_threads.append(server_thread)
    active_servers.append(server)
    
    print("\n" + "="*50)
    print(f"{system_name} {args.arm.upper()} ARM Hardware Server Running")
    print(f"CAN Channel: {can_channel}")
    print(f"Listening on: {hardware_host}:{port}")
    print("Waiting for commands from host_broadcast...")
    print("Press Ctrl+C to stop")
    print("="*50 + "\n")
    
    # Keep the server running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()