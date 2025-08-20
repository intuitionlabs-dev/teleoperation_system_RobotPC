"""
Bimanual YAM Follower Robot - Controls two YAM arms simultaneously.
"""

import logging
import sys
import threading
import time
from pathlib import Path
from functools import cached_property
from typing import Any, Dict

from omegaconf import OmegaConf

from robots.robot import Robot
from .config import BimanualYAMFollowerConfig

logger = logging.getLogger(__name__)


class BimanualYAMFollower(Robot):
    """
    A bimanual robot composed of two YAM follower arms.
    """
    
    config_class = BimanualYAMFollowerConfig
    name = "bimanual_yam_follower"
    
    def __init__(self, config: BimanualYAMFollowerConfig):
        super().__init__(config)
        self.config = config
        self._is_connected = False
        
        # Add gello_software to path - handle both absolute and relative paths
        if Path(config.gello_path).is_absolute():
            gello_path = Path(config.gello_path)
        else:
            # Relative to teleoperation_system_RobotPC directory
            base_dir = Path(__file__).parent.parent.parent
            gello_path = (base_dir / config.gello_path).resolve()
        
        if not gello_path.exists():
            logger.error(f"Could not find gello_software at: {gello_path}")
            raise RuntimeError(f"gello_software not found at {gello_path}")
        
        if str(gello_path) not in sys.path:
            sys.path.append(str(gello_path))
        
        # Will be initialized on connect
        self.left_robot = None
        self.right_robot = None
    
    @property
    def _motors_ft(self) -> dict[str, type]:
        """Motor features for both arms."""
        base_features = {
            "joint_0.pos": float,
            "joint_1.pos": float,
            "joint_2.pos": float,
            "joint_3.pos": float,
            "joint_4.pos": float,
            "joint_5.pos": float,
            "joint_6.pos": float,
        }
        combined_features = {}
        for key in base_features:
            combined_features[f"left_{key}"] = base_features[key]
            combined_features[f"right_{key}"] = base_features[key]
        return combined_features
    
    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        return self._motors_ft
    
    @cached_property
    def action_features(self) -> dict[str, type]:
        return self._motors_ft
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    def connect(self, calibrate: bool = True) -> None:
        """Connect to the YAM follower arms."""
        if self._is_connected:
            raise RuntimeError(f"{self.name} already connected")
        
        logger.info(f"Connecting {self.name}...")
        
        # Setup hardware for each arm
        self._setup_hardware()
        
        self._is_connected = True
        logger.info(f"{self.name} connected.")
    
    def _setup_hardware(self):
        """Setup YAM robot hardware using direct motor control interfaces."""
        # Import necessary modules for direct motor control
        try:
            from i2rt.motor_drivers.dm_driver import DMChainCanInterface, ReceiveMode
            import numpy as np
        except ImportError as e:
            logger.error(f"Failed to import i2rt modules: {e}")
            logger.error("Make sure i2rt is in PYTHONPATH")
            raise
        
        # Motor configuration for YAM (7 motors per arm including gripper)
        motor_list = [
            [0x01, "DM4340"],
            [0x02, "DM4340"], 
            [0x03, "DM4340"],
            [0x04, "DM4310"],
            [0x05, "DM4310"],
            [0x06, "DM4310"],
            [0x07, "DM4310"],  # Gripper
        ]
        motor_offsets = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        motor_directions = [1, 1, 1, 1, 1, 1, 1]
        
        # Setup left arm
        logger.info(f"Setting up left YAM arm on channel {self.config.left_arm.channel}")
        try:
            # Create motor chain for left arm
            self.left_motor_chain = DMChainCanInterface(
                motor_list,
                motor_offsets,
                motor_directions,
                self.config.left_arm.channel,
                motor_chain_name="yam_left",
                receive_mode=ReceiveMode.p16,
                start_thread=True,  # Start control thread
            )
            
            # Store initial positions
            motor_states = self.left_motor_chain.read_states()
            self.left_positions = [m.pos for m in motor_states]
            logger.info("Left YAM arm initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize left YAM arm: {e}")
            raise
        
        # Setup right arm
        logger.info("Waiting 3 seconds before initializing right arm (CAN bus delay)...")
        time.sleep(3)
        
        logger.info(f"Setting up right YAM arm on channel {self.config.right_arm.channel}")
        try:
            # Create motor chain for right arm
            self.right_motor_chain = DMChainCanInterface(
                motor_list,
                motor_offsets,
                motor_directions,
                self.config.right_arm.channel,
                motor_chain_name="yam_right",
                receive_mode=ReceiveMode.p16,
                start_thread=True,  # Start control thread
            )
            
            # Store initial positions
            motor_states = self.right_motor_chain.read_states()
            self.right_positions = [m.pos for m in motor_states]
            logger.info("Right YAM arm initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize right YAM arm: {e}")
            raise
        
        logger.info("Both YAM arms initialized successfully")
    
    @property
    def is_calibrated(self) -> bool:
        """YAM robots don't require calibration."""
        return True
    
    def calibrate(self) -> None:
        """Calibration not needed for YAM robots."""
        logger.info("YAM robots don't require calibration")
    
    def configure(self) -> None:
        """Configure the YAM arms."""
        logger.info(f"{self.name} configured.")
    
    def get_observation(self) -> dict[str, Any]:
        """Get observations from both YAM arms."""
        if not self._is_connected:
            raise RuntimeError(f"{self.name} is not connected")
        
        obs = {}
        
        # Get left arm observation
        left_states = self.left_motor_chain.get_motor_states()
        for i, state in enumerate(left_states):
            obs[f"left_joint_{i}.pos"] = state.pos
            obs[f"left_joint_{i}.vel"] = state.vel
            obs[f"left_joint_{i}.eff"] = state.eff
        
        # Get right arm observation
        right_states = self.right_motor_chain.get_motor_states()
        for i, state in enumerate(right_states):
            obs[f"right_joint_{i}.pos"] = state.pos
            obs[f"right_joint_{i}.vel"] = state.vel
            obs[f"right_joint_{i}.eff"] = state.eff
        
        return obs
    
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send action to both YAM arms."""
        if not self._is_connected:
            raise RuntimeError(f"{self.name} is not connected")
        
        # Extract positions for left arm
        left_positions = []
        for i in range(7):
            key = f"left_joint_{i}.pos"
            if key in action:
                left_positions.append(action[key])
            else:
                # Use current position if not specified
                left_positions.append(self.left_positions[i])
        
        # Extract positions for right arm
        right_positions = []
        for i in range(7):
            key = f"right_joint_{i}.pos"
            if key in action:
                right_positions.append(action[key])
            else:
                # Use current position if not specified
                right_positions.append(self.right_positions[i])
        
        # Send commands to motors using the correct method
        try:
            # Create motor commands for position control
            from i2rt.motor_drivers.dm_driver import MotorCmd
            
            left_cmds = [MotorCmd(type='pos', pos=pos, kp=10.0, kd=1.0) for pos in left_positions]
            self.left_motor_chain.send_motor_commands(left_cmds)
            self.left_positions = left_positions
            
            right_cmds = [MotorCmd(type='pos', pos=pos, kp=10.0, kd=1.0) for pos in right_positions]
            self.right_motor_chain.send_motor_commands(right_cmds)
            self.right_positions = right_positions
        except Exception as e:
            logger.error(f"Error sending motor commands: {e}")
        
        return action
    
    def disconnect(self):
        """Disconnect from the YAM arms."""
        if not self._is_connected:
            return
        
        logger.info(f"Disconnecting {self.name}...")
        
        # Close motor chains
        if hasattr(self, 'left_motor_chain') and self.left_motor_chain:
            try:
                self.left_motor_chain.close()
            except Exception as e:
                logger.warning(f"Error closing left motor chain: {e}")
        
        if hasattr(self, 'right_motor_chain') and self.right_motor_chain:
            try:
                self.right_motor_chain.close()
            except Exception as e:
                logger.warning(f"Error closing right motor chain: {e}")
        
        self._is_connected = False
        logger.info(f"{self.name} disconnected.")