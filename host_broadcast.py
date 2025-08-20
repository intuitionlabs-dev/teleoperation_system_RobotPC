#!/usr/bin/env python
"""
Host broadcast module for bimanual robot teleoperation (Piper or YAM).
Receives commands from teleoperator and sends observations back.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Literal

import draccus
import zmq

from robots.bimanual_piper.bimanual_piper_follower import BimanualPiperFollower
from robots.bimanual_piper.config import BimanualPiperFollowerConfig
from robots.piper.config import PiperConfig


@dataclass
class BroadcastHostConfig:
    """Configuration for the broadcast host."""
    # System selection
    system: Literal["piper-so101", "yam-dynamixel"] = "piper-so101"
    """Which robot system to use."""
    
    # Piper configuration
    left_arm_port: str = "left_piper"
    right_arm_port: str = "right_piper"
    
    # YAM configuration - just CAN channels like Piper uses ports
    yam_left_channel: str = "can_follow_l"
    yam_right_channel: str = "can_follow_r"
    yam_use_zmq: bool = True  # Use ZMQ connection to hardware servers
    yam_gello_path: str = "../gello_software"  # Relative to teleoperation_system_RobotPC
    
    # Network configuration
    port_zmq_cmd: int = 5555
    port_zmq_observations: int = 5556
    port_cmd_broadcast: int = 5557
    port_obs_broadcast: int = 5558
    max_loop_freq_hz: int = 60
    
    # YAM system uses different ports to avoid conflicts
    yam_port_zmq_cmd: int = 5565
    yam_port_zmq_observations: int = 5566
    yam_port_cmd_broadcast: int = 5567
    yam_port_obs_broadcast: int = 5568


@draccus.wrap()
def main(cfg: BroadcastHostConfig):
    """
    Launch a bimanual robot host and relay all commands & observations.
    
    - Receives actions from teleoperator (PULL socket on cfg.port_zmq_cmd)
    - Sends observations back to teleoperator (PUSH on cfg.port_zmq_observations)
    - Additionally publishes each action on cfg.port_cmd_broadcast (PUB)
    - Publishes each observation on cfg.port_obs_broadcast (PUB)
    """
    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Configure robot based on system type
    if cfg.system == "piper-so101":
        robot_config = BimanualPiperFollowerConfig(
            left_arm=PiperConfig(port=cfg.left_arm_port),
            right_arm=PiperConfig(port=cfg.right_arm_port),
        )
        logging.info("Configuring Bimanual Piper")
        robot = BimanualPiperFollower(robot_config)
        
    elif cfg.system == "yam-dynamixel":
        # Import directly to avoid triggering piper_sdk import check
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        if cfg.yam_use_zmq:
            # Use ZMQ connection to existing hardware servers
            from robots.bimanual_yam.bimanual_yam_follower_zmq import BimanualYAMFollowerZMQ
            from robots.bimanual_yam.config import BimanualYAMFollowerConfig, YAMConfig
            
            robot_config = BimanualYAMFollowerConfig(
                left_arm=YAMConfig(
                    channel=cfg.yam_left_channel,
                    hardware_port=6001,
                    id="left"
                ),
                right_arm=YAMConfig(
                    channel=cfg.yam_right_channel,
                    hardware_port=6003,  # Different port for right arm
                    id="right"
                ),
                gello_path=cfg.yam_gello_path,
                id="bimanual",
            )
            logging.info("Configuring Bimanual YAM with ZMQ connection to hardware servers")
            robot = BimanualYAMFollowerZMQ(robot_config)
        else:
            # Direct motor control (not recommended when hardware servers are running)
            from robots.bimanual_yam.bimanual_yam_follower import BimanualYAMFollower
            from robots.bimanual_yam.config import BimanualYAMFollowerConfig, YAMConfig
            
            robot_config = BimanualYAMFollowerConfig(
                left_arm=YAMConfig(
                    channel=cfg.yam_left_channel,
                    hardware_port=6001,
                    id="left"
                ),
                right_arm=YAMConfig(
                    channel=cfg.yam_right_channel,
                    hardware_port=6003,
                    id="right"
                ),
                gello_path=cfg.yam_gello_path,
                id="bimanual",
            )
            logging.info("Configuring Bimanual YAM with direct motor control")
            robot = BimanualYAMFollower(robot_config)
        
    else:
        raise ValueError(f"Unknown system: {cfg.system}")
    
    logging.info(f"Starting {cfg.system} robot host")
    robot.connect()
    
    # Select ports based on system type
    if cfg.system == "yam-dynamixel":
        port_cmd = cfg.yam_port_zmq_cmd
        port_obs = cfg.yam_port_zmq_observations
        port_cmd_broadcast = cfg.yam_port_cmd_broadcast
        port_obs_broadcast = cfg.yam_port_obs_broadcast
    else:  # piper-so101
        port_cmd = cfg.port_zmq_cmd
        port_obs = cfg.port_zmq_observations
        port_cmd_broadcast = cfg.port_cmd_broadcast
        port_obs_broadcast = cfg.port_obs_broadcast
    
    # Setup ZMQ sockets
    context = zmq.Context()
    
    pull_cmd = context.socket(zmq.PULL)
    pull_cmd.setsockopt(zmq.CONFLATE, 1)
    pull_cmd.bind(f"tcp://*:{port_cmd}")
    
    push_obs = context.socket(zmq.PUSH)
    push_obs.setsockopt(zmq.CONFLATE, 1)
    push_obs.bind(f"tcp://*:{port_obs}")
    
    # Extra PUB sockets for broadcast
    pub_cmd = context.socket(zmq.PUB)
    pub_cmd.bind(f"tcp://*:{port_cmd_broadcast}")
    
    pub_obs = context.socket(zmq.PUB)
    pub_obs.bind(f"tcp://*:{port_obs_broadcast}")
    
    first_cmd = False
    max_loop_hz = cfg.max_loop_freq_hz
    
    logging.info(f"{cfg.system} Host ready on ports {port_cmd}-{port_obs_broadcast} - waiting for teleop...")
    try:
        while True:
            loop_start = time.time()
            try:
                msg = pull_cmd.recv_string(flags=zmq.NOBLOCK)
                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    logging.warning("Received a malformed JSON message, skipping.")
                    continue
                if not first_cmd:
                    logging.info("First teleop action received - starting loop.")
                    first_cmd = True
                logging.debug(f"Host received action: {data}")
                robot.send_action(data)
                
                # Broadcast command
                pub_cmd.send_string(msg)
            except zmq.Again:
                pass
            
            # Get observation each cycle
            obs = robot.get_observation()
            try:
                push_obs.send_string(json.dumps(obs), flags=zmq.NOBLOCK)
            except zmq.Again:
                logging.debug("Teleop client not ready - dropping obs")
            
            # Broadcast observation
            try:
                pub_obs.send_string(json.dumps(obs), flags=zmq.NOBLOCK)
            except zmq.Again:
                pass
            
            # Loop timing
            sleep_dt = max(1.0 / max_loop_hz - (time.time() - loop_start), 0)
            time.sleep(sleep_dt)
    except KeyboardInterrupt:
        logging.info("Host interrupted - shutting down.")
    finally:
        robot.disconnect()
        pull_cmd.close()
        push_obs.close()
        pub_cmd.close()
        pub_obs.close()
        context.term()


if __name__ == "__main__":
    main()