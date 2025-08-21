#!/usr/bin/env python
"""
Hardware server launcher for YAM follower arms.
This script launches a ZMQ server that exposes the YAM robot for remote control.
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
    parser = argparse.ArgumentParser(description="Launch YAM hardware server")
    parser.add_argument(
        "--arm",
        type=str,
        choices=["left", "right"],
        required=True,
        help="Which arm to launch (left or right)"
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

    # Set defaults based on arm
    if args.arm == "left":
        port = args.port or 6001
        can_channel = args.can_channel or "can_follow_l"
    else:  # right
        port = args.port or 6003
        can_channel = args.can_channel or "can_follow_r"

    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Initializing YAM {args.arm} arm on CAN channel: {can_channel}")
    
    # Create YAM robot
    robot = YAMRobot(channel=can_channel)
    
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
    print(f"YAM {args.arm.upper()} ARM Hardware Server Running")
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