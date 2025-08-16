#!/usr/bin/env python
"""Minimal host broadcast for Robot PC - core teleoperation only"""
import json
import time
from dataclasses import dataclass
import zmq
import numpy as np
from pathlib import Path
import sys

# Add path for robot imports
sys.path.append(str(Path(__file__).parent))

# Import robot classes (we'll copy these next)
from bimanual_piper_follower import BimanualPiperFollower
from bimanual_piper_config import BimanualPiperFollowerConfig
from piper_robot import Piper, PiperConfig


@dataclass
class BroadcastHostConfig:
    # Robot arm ports
    left_arm_port: str = "left_piper"
    right_arm_port: str = "right_piper"
    
    # ZMQ ports
    port_zmq_cmd: int = 5555
    
    # Loop frequency
    max_loop_freq_hz: int = 60
    
    # Enable listener for motor control
    port_enable_listener: int = 5559


def main(cfg: BroadcastHostConfig):
    """Minimal host broadcast main loop - command receiver only"""
    print(f"Starting minimal host broadcast...")
    print(f"Left arm: {cfg.left_arm_port}")
    print(f"Right arm: {cfg.right_arm_port}")
    print(f"Command port: {cfg.port_zmq_cmd}")
    print(f"Max frequency: {cfg.max_loop_freq_hz} Hz")
    
    # Setup ZMQ context
    context = zmq.Context()
    
    # Command receiver (PULL)
    pull_cmd = context.socket(zmq.PULL)
    pull_cmd.setsockopt(zmq.RCVTIMEO, 35)  # 35ms timeout for 30Hz operation
    pull_cmd.bind(f"tcp://*:{cfg.port_zmq_cmd}")
    
    # Enable listener (SUB)
    sub_enable = context.socket(zmq.SUB)
    sub_enable.setsockopt(zmq.SUBSCRIBE, b"")
    sub_enable.setsockopt(zmq.RCVTIMEO, 35)  # Non-blocking check
    sub_enable.bind(f"tcp://*:{cfg.port_enable_listener}")
    
    # Initialize robot
    robot_config = BimanualPiperFollowerConfig(
        left_robot=PiperConfig(
            robot_type="piper",
            device_path=cfg.left_arm_port,
        ),
        right_robot=PiperConfig(
            robot_type="piper", 
            device_path=cfg.right_arm_port,
        ),
    )
    
    robot = BimanualPiperFollower(config=robot_config)
    robot.connect()
    robot.set_motors_engaged(True)
    
    # Main loop
    loop_time = 1.0 / cfg.max_loop_freq_hz
    last_time = time.time()
    
    print("\nStarting main loop...")
    
    while True:
        loop_start = time.time()
        
        # Check for enable/disable commands
        try:
            enable_msg = sub_enable.recv_string()
            enable_data = json.loads(enable_msg)
            if "enable" in enable_data:
                robot.set_motors_engaged(enable_data["enable"])
                print(f"Motors {'enabled' if enable_data['enable'] else 'disabled'}")
        except zmq.Again:
            pass  # No enable message
        
        # Try to receive command
        cmd_received = False
        try:
            cmd_str = pull_cmd.recv_string()
            cmd = json.loads(cmd_str)
            
            # Apply command to robot
            if "action" in cmd:
                action = cmd["action"]
                
                # Debug: print first command to see format
                if not hasattr(robot, '_first_cmd_logged'):
                    print(f"[DEBUG] First command received")
                    robot._first_cmd_logged = True
                
                robot.send_action(action)
                cmd_received = True
        except zmq.Again:
            pass  # No command available
        
        # Rate limiting
        elapsed = time.time() - loop_start
        if elapsed < loop_time:
            time.sleep(loop_time - elapsed)
        
        # Simple status every 2 seconds
        if time.time() - last_time > 2.0:
            rate = 1.0 / (time.time() - loop_start) if (time.time() - loop_start) > 0 else 0
            status = "ACTIVE" if cmd_received else "IDLE"
            print(f"[{status}] Rate: {rate:.1f} Hz")
            last_time = time.time()


if __name__ == "__main__":
    # Simple argument parsing
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--left_arm_port", type=str, default="left_piper")
    parser.add_argument("--right_arm_port", type=str, default="right_piper")
    parser.add_argument("--port_zmq_cmd", type=int, default=5555)
    parser.add_argument("--port_enable_listener", type=int, default=5559)
    parser.add_argument("--max_loop_freq_hz", type=int, default=60)
    
    args = parser.parse_args()
    
    config = BroadcastHostConfig(
        left_arm_port=args.left_arm_port,
        right_arm_port=args.right_arm_port,
        port_zmq_cmd=args.port_zmq_cmd,
        port_enable_listener=args.port_enable_listener,
        max_loop_freq_hz=args.max_loop_freq_hz
    )
    
    main(config)
