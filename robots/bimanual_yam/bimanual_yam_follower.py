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
        """Setup YAM robot hardware using direct motor control."""
        # Import necessary modules
        try:
            from i2rt.robots.get_robot import get_yam_robot
        except ImportError as e:
            logger.error(f"Failed to import i2rt modules: {e}")
            logger.error("Make sure i2rt is in PYTHONPATH")
            raise
        
        # Setup left arm directly
        logger.info(f"Setting up left YAM arm on channel {self.config.left_arm.channel}")
        try:
            # Create robot using i2rt's get_yam_robot function
            self.left_robot = get_yam_robot(channel=self.config.left_arm.channel)
            logger.info("Left YAM arm initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize left YAM arm: {e}")
            raise
        
        # Setup right arm
        logger.info("Waiting 3 seconds before initializing right arm (CAN bus delay)...")
        time.sleep(3)
        
        logger.info(f"Setting up right YAM arm on channel {self.config.right_arm.channel}")
        try:
            # Create robot using i2rt's get_yam_robot function
            self.right_robot = get_yam_robot(channel=self.config.right_arm.channel)
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
        
        # Get left arm observation directly
        left_obs = self.left_robot.get_observation()
        for key, val in left_obs.items():
            obs[f"left_{key}"] = val
        
        # Get right arm observation directly
        right_obs = self.right_robot.get_observation()
        for key, val in right_obs.items():
            obs[f"right_{key}"] = val
        
        return obs
    
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send action to both YAM arms."""
        if not self._is_connected:
            raise RuntimeError(f"{self.name} is not connected")
        
        # Split action into left and right components
        left_action = {}
        right_action = {}
        
        for key, val in action.items():
            if key.startswith("left_"):
                # Remove prefix for the individual arm
                left_action[key.removeprefix("left_")] = val
            elif key.startswith("right_"):
                # Remove prefix for the individual arm
                right_action[key.removeprefix("right_")] = val
            else:
                logger.warning(f"Action key without arm prefix: {key}")
        
        # Send directly to robots
        if left_action:
            self.left_robot.send_action(left_action)
        else:
            logger.warning("No left arm actions in command")
        
        if right_action:
            self.right_robot.send_action(right_action)
        else:
            logger.warning("No right arm actions in command")
        
        return action
    
    def disconnect(self):
        """Disconnect from the YAM arms."""
        if not self._is_connected:
            return
        
        logger.info(f"Disconnecting {self.name}...")
        
        # The i2rt robots handle their own cleanup
        # No explicit disconnect needed
        
        self._is_connected = False
        logger.info(f"{self.name} disconnected.")