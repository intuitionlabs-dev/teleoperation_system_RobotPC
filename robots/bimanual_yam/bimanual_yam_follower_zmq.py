"""
Bimanual YAM Follower Robot - Controls two YAM arms via ZMQ servers.
"""

import logging
import sys
import time
from pathlib import Path
from functools import cached_property
from typing import Any, Dict

from robots.robot import Robot
from .config import BimanualYAMFollowerConfig

logger = logging.getLogger(__name__)


class BimanualYAMFollowerZMQ(Robot):
    """
    A bimanual robot composed of two YAM follower arms connected via ZMQ.
    """
    
    config_class = BimanualYAMFollowerConfig
    name = "bimanual_yam_follower_zmq"
    
    def __init__(self, config: BimanualYAMFollowerConfig):
        super().__init__(config)
        self.config = config
        self._is_connected = False
        
        # Add gello_software to path
        if Path(config.gello_path).is_absolute():
            gello_path = Path(config.gello_path)
        else:
            base_dir = Path(__file__).parent.parent.parent
            gello_path = (base_dir / config.gello_path).resolve()
        
        if not gello_path.exists():
            logger.error(f"Could not find gello_software at: {gello_path}")
            raise RuntimeError(f"gello_software not found at {gello_path}")
        
        if str(gello_path) not in sys.path:
            sys.path.append(str(gello_path))
        
        # Will be initialized on connect
        self.left_client = None
        self.right_client = None
    
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
        """Connect to the YAM follower arms via ZMQ."""
        if self._is_connected:
            raise RuntimeError(f"{self.name} already connected")
        
        logger.info(f"Connecting {self.name} via ZMQ...")
        
        # Import ZMQ client
        try:
            from gello.zmq_core.robot_node import ZMQClientRobot
        except ImportError as e:
            logger.error(f"Failed to import gello modules: {e}")
            raise
        
        # Connect to left arm server (port 6001)
        left_port = 6001
        logger.info(f"Connecting to left YAM arm on port {left_port}...")
        try:
            self.left_client = ZMQClientRobot(port=left_port, host="127.0.0.1")
            logger.info("Left YAM arm connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to left YAM arm: {e}")
            raise
        
        # Wait before connecting to right arm
        time.sleep(2)
        
        # Connect to right arm server (port 6003)
        right_port = 6003
        logger.info(f"Connecting to right YAM arm on port {right_port}...")
        try:
            self.right_client = ZMQClientRobot(port=right_port, host="127.0.0.1")
            logger.info("Right YAM arm connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to right YAM arm: {e}")
            # Clean up left client
            if self.left_client:
                self.left_client.close()
            raise
        
        self._is_connected = True
        logger.info(f"{self.name} connected via ZMQ.")
    
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
        left_obs = self.left_client.get_observations()
        for i in range(7):
            obs[f"left_joint_{i}.pos"] = left_obs["pos"][i]
            obs[f"left_joint_{i}.vel"] = left_obs["vel"][i]
            obs[f"left_joint_{i}.eff"] = left_obs["eff"][i]
        
        # Get right arm observation  
        right_obs = self.right_client.get_observations()
        for i in range(7):
            obs[f"right_joint_{i}.pos"] = right_obs["pos"][i]
            obs[f"right_joint_{i}.vel"] = right_obs["vel"][i]
            obs[f"right_joint_{i}.eff"] = right_obs["eff"][i]
        
        return obs
    
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send action to both YAM arms."""
        if not self._is_connected:
            raise RuntimeError(f"{self.name} is not connected")
        
        import numpy as np
        
        # Extract positions for left arm
        left_positions = []
        for i in range(7):
            key = f"left_joint_{i}.pos"
            if key in action:
                left_positions.append(action[key])
            else:
                # Get current position if not specified
                left_obs = self.left_client.get_observations()
                left_positions.append(left_obs["pos"][i])
        
        # Extract positions for right arm
        right_positions = []
        for i in range(7):
            key = f"right_joint_{i}.pos"
            if key in action:
                right_positions.append(action[key])
            else:
                # Get current position if not specified
                right_obs = self.right_client.get_observations()
                right_positions.append(right_obs["pos"][i])
        
        # Send commands to arms via ZMQ
        try:
            # Send to left arm
            left_action = {"pos": np.array(left_positions)}
            self.left_client.command_joint_state(left_action)
            
            # Send to right arm
            right_action = {"pos": np.array(right_positions)}
            self.right_client.command_joint_state(right_action)
            
        except Exception as e:
            logger.error(f"Error sending commands via ZMQ: {e}")
        
        return action
    
    def disconnect(self):
        """Disconnect from the YAM arms."""
        if not self._is_connected:
            return
        
        logger.info(f"Disconnecting {self.name}...")
        
        # Close ZMQ clients
        if self.left_client:
            try:
                self.left_client.close()
            except Exception as e:
                logger.warning(f"Error closing left client: {e}")
        
        if self.right_client:
            try:
                self.right_client.close()
            except Exception as e:
                logger.warning(f"Error closing right client: {e}")
        
        self._is_connected = False
        logger.info(f"{self.name} disconnected.")