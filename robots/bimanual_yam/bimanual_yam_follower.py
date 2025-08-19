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
        
        # Import gello modules after adding to path
        try:
            from gello.zmq_core.robot_node import ZMQClientRobot, ZMQServerRobot
        except ImportError as e:
            logger.error(f"Failed to import gello modules: {e}")
            logger.error("Make sure gello_software is properly installed")
            raise
        
        self._ZMQClientRobot = ZMQClientRobot
        self._ZMQServerRobot = ZMQServerRobot
        
        # Will be initialized on connect
        self.left_robot = None
        self.right_robot = None
        self.left_server = None
        self.right_server = None
        self.left_client = None
        self.right_client = None
        self.left_thread = None
        self.right_thread = None
    
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
        
        # Setup hardware servers for each arm
        self._setup_hardware_servers()
        
        self._is_connected = True
        logger.info(f"{self.name} connected.")
    
    def _setup_hardware_servers(self):
        """Setup ZMQ servers for hardware communication."""
        # Import YAMRobot directly
        try:
            from gello.robots.yam import YAMRobot
        except ImportError as e:
            logger.error(f"Failed to import YAMRobot: {e}")
            raise
        
        # Left arm
        logger.info(f"Setting up left YAM arm on channel {self.config.left_arm.channel}, port {self.config.left_arm.hardware_port}")
        
        # Create left robot directly with channel name
        self.left_robot = YAMRobot(channel=self.config.left_arm.channel)
        
        # Create ZMQ server for left arm
        self.left_server = self._ZMQServerRobot(
            self.left_robot,
            port=self.config.left_arm.hardware_port,
            host="127.0.0.1"
        )
        self.left_thread = threading.Thread(target=self.left_server.serve, daemon=False)
        self.left_thread.start()
        
        # Wait and create client
        time.sleep(0.5)
        self.left_client = self._ZMQClientRobot(
            port=self.config.left_arm.hardware_port,
            host="127.0.0.1"
        )
        
        # Right arm
        logger.info("Waiting 3 seconds before initializing right arm (CAN bus delay)...")
        time.sleep(3)
        
        logger.info(f"Setting up right YAM arm on channel {self.config.right_arm.channel}, port {self.config.right_arm.hardware_port}")
        
        # Create right robot directly with channel name
        self.right_robot = YAMRobot(channel=self.config.right_arm.channel)
        
        # Create ZMQ server for right arm
        self.right_server = self._ZMQServerRobot(
            self.right_robot,
            port=self.config.right_arm.hardware_port,
            host="127.0.0.1"
        )
        self.right_thread = threading.Thread(target=self.right_server.serve, daemon=False)
        self.right_thread.start()
        
        # Wait and create client
        time.sleep(0.5)
        self.right_client = self._ZMQClientRobot(
            port=self.config.right_arm.hardware_port,
            host="127.0.0.1"
        )
    
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
        left_obs = self.left_client.get_observation()
        for key, val in left_obs.items():
            obs[f"left_{key}"] = val
        
        # Get right arm observation
        right_obs = self.right_client.get_observation()
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
        
        # Send to arms
        if left_action:
            self.left_client.send_action(left_action)
        else:
            logger.warning("No left arm actions in command")
        
        if right_action:
            self.right_client.send_action(right_action)
        else:
            logger.warning("No right arm actions in command")
        
        return action
    
    def disconnect(self):
        """Disconnect from the YAM arms."""
        if not self._is_connected:
            return
        
        logger.info(f"Disconnecting {self.name}...")
        
        # Close clients
        if self.left_client:
            self.left_client.close()
        if self.right_client:
            self.right_client.close()
        
        # Close servers
        if self.left_server:
            self.left_server.close()
        if self.right_server:
            self.right_server.close()
        
        # Wait for threads
        if self.left_thread:
            self.left_thread.join(timeout=2)
        if self.right_thread:
            self.right_thread.join(timeout=2)
        
        self._is_connected = False
        logger.info(f"{self.name} disconnected.")