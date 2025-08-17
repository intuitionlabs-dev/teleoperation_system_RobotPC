#!/usr/bin/env python
"""
Host broadcast module for bimanual Piper robot teleoperation.
Receives commands from teleoperator and sends observations back.
"""

import json
import logging
import time
from dataclasses import dataclass

import draccus
import zmq

from robots.bimanual_piper.bimanual_piper_follower import BimanualPiperFollower
from robots.bimanual_piper.config import BimanualPiperFollowerConfig
from robots.piper.config import PiperConfig


@dataclass
class BroadcastHostConfig:
    """Configuration for the broadcast host."""
    left_arm_port: str = "left_piper"
    right_arm_port: str = "right_piper"
    port_zmq_cmd: int = 5555
    port_zmq_observations: int = 5556
    port_cmd_broadcast: int = 5557
    port_obs_broadcast: int = 5558
    max_loop_freq_hz: int = 60


@draccus.wrap()
def main(cfg: BroadcastHostConfig):
    """
    Launch a bimanual Piper host and relay all commands & observations.
    
    - Receives actions from teleoperator (PULL socket on cfg.port_zmq_cmd)
    - Sends observations back to teleoperator (PUSH on cfg.port_zmq_observations)
    - Additionally publishes each action on cfg.port_cmd_broadcast (PUB)
    - Publishes each observation on cfg.port_obs_broadcast (PUB)
    """
    # Configure robot
    robot_config = BimanualPiperFollowerConfig(
        left_arm=PiperConfig(port=cfg.left_arm_port),
        right_arm=PiperConfig(port=cfg.right_arm_port),
    )
    
    logging.info("Configuring Bimanual Piper")
    robot = BimanualPiperFollower(robot_config)
    robot.connect()
    
    # Setup ZMQ sockets
    context = zmq.Context()
    
    pull_cmd = context.socket(zmq.PULL)
    pull_cmd.setsockopt(zmq.CONFLATE, 1)
    pull_cmd.bind(f"tcp://*:{cfg.port_zmq_cmd}")
    
    push_obs = context.socket(zmq.PUSH)
    push_obs.setsockopt(zmq.CONFLATE, 1)
    push_obs.bind(f"tcp://*:{cfg.port_zmq_observations}")
    
    # Extra PUB sockets for broadcast
    pub_cmd = context.socket(zmq.PUB)
    pub_cmd.bind(f"tcp://*:{cfg.port_cmd_broadcast}")
    
    pub_obs = context.socket(zmq.PUB)
    pub_obs.bind(f"tcp://*:{cfg.port_obs_broadcast}")
    
    first_cmd = False
    max_loop_hz = cfg.max_loop_freq_hz
    
    logging.info("Bimanual Piper Host with broadcast ready - waiting for teleop...")
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