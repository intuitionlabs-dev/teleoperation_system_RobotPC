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
    port_zmq_observations: int = 5556
    port_cmd_broadcast: int = 5557
    port_obs_broadcast: int = 5558
    
    # Loop frequency
    max_loop_freq_hz: int = 60
    
    # Enable listener for motor control
    port_enable_listener: int = 5559


def main(cfg: BroadcastHostConfig):
    """Minimal host broadcast main loop"""
    print(f"Starting minimal host broadcast...")
    print(f"Left arm: {cfg.left_arm_port}")
    print(f"Right arm: {cfg.right_arm_port}")
    print(f"Command port: {cfg.port_zmq_cmd}")
    print(f"Observation port: {cfg.port_zmq_observations}")
    print(f"Max frequency: {cfg.max_loop_freq_hz} Hz")
    
    # Setup ZMQ context
    context = zmq.Context()
    
    # Command receiver (PULL)
    pull_cmd = context.socket(zmq.PULL)
    pull_cmd.setsockopt(zmq.RCVTIMEO, 35)  # 35ms timeout for 30Hz operation
    pull_cmd.bind(f"tcp://*:{cfg.port_zmq_cmd}")
    
    # Observation sender (PUSH) 
    push_obs = context.socket(zmq.PUSH)
    push_obs.setsockopt(zmq.SNDTIMEO, 100)  # 100ms timeout
    push_obs.bind(f"tcp://*:{cfg.port_zmq_observations}")
    
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
                robot.send_action(action)
                cmd_received = True
        except zmq.Again:
            pass  # No command available
        
        # Get observation
        obs = robot.get_observation()
        
        # Send observation
        try:
            obs_data = {
                "left_pos": obs["observation.left_piper.position"].tolist(),
                "left_vel": obs["observation.left_piper.velocity"].tolist(),
                "left_load": obs["observation.left_piper.load"].tolist() if "observation.left_piper.load" in obs else None,
                "right_pos": obs["observation.right_piper.position"].tolist(),
                "right_vel": obs["observation.right_piper.velocity"].tolist(),
                "right_load": obs["observation.right_piper.load"].tolist() if "observation.right_piper.load" in obs else None,
                "left_gripper": obs.get("observation.left_piper.gripper_position", 0.0),
                "right_gripper": obs.get("observation.right_piper.gripper_position", 0.0),
                "timestamp": time.time()
            }
            push_obs.send_string(json.dumps(obs_data))
        except zmq.Again:
            print("Warning: Failed to send observation")
        
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
    parser.add_argument("--port_zmq_observations", type=int, default=5556)
    parser.add_argument("--port_cmd_broadcast", type=int, default=5557)
    parser.add_argument("--port_obs_broadcast", type=int, default=5558)
    parser.add_argument("--port_enable_listener", type=int, default=5559)
    parser.add_argument("--max_loop_freq_hz", type=int, default=60)
    
    args = parser.parse_args()
    
    config = BroadcastHostConfig(
        left_arm_port=args.left_arm_port,
        right_arm_port=args.right_arm_port,
        port_zmq_cmd=args.port_zmq_cmd,
        port_zmq_observations=args.port_zmq_observations,
        port_cmd_broadcast=args.port_cmd_broadcast,
        port_obs_broadcast=args.port_obs_broadcast,
        port_enable_listener=args.port_enable_listener,
        max_loop_freq_hz=args.max_loop_freq_hz
    )
    
    main(config)
