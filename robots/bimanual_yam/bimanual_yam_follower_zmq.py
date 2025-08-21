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
        self._last_left_positions = None  # Store last valid left arm positions
        self._last_right_positions = None  # Store last valid right arm positions
        
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
        
        import numpy as np
        
        obs = {}
        
        # Get left arm observation
        left_obs = self.left_client.get_observations()
        # The observation might be a numpy array or dict with 'qpos', 'qvel', 'qeff'
        if isinstance(left_obs, dict):
            if "qpos" in left_obs:
                # Format: {'qpos': array, 'qvel': array, 'qeff': array}
                for i in range(min(7, len(left_obs["qpos"]))):
                    obs[f"left_joint_{i}.pos"] = float(left_obs["qpos"][i])
                    obs[f"left_joint_{i}.vel"] = float(left_obs.get("qvel", np.zeros(7))[i])
                    obs[f"left_joint_{i}.eff"] = float(left_obs.get("qeff", np.zeros(7))[i])
            elif "pos" in left_obs:
                # Format: {'pos': array, 'vel': array, 'eff': array}
                for i in range(min(7, len(left_obs["pos"]))):
                    obs[f"left_joint_{i}.pos"] = float(left_obs["pos"][i])
                    obs[f"left_joint_{i}.vel"] = float(left_obs.get("vel", np.zeros(7))[i])
                    obs[f"left_joint_{i}.eff"] = float(left_obs.get("eff", np.zeros(7))[i])
            else:
                # Try direct numpy array access
                for i in range(7):
                    obs[f"left_joint_{i}.pos"] = float(left_obs.get(i, 0.0))
                    obs[f"left_joint_{i}.vel"] = 0.0
                    obs[f"left_joint_{i}.eff"] = 0.0
        else:
            # Assume it's a numpy array of positions
            for i in range(min(7, len(left_obs))):
                obs[f"left_joint_{i}.pos"] = float(left_obs[i])
                obs[f"left_joint_{i}.vel"] = 0.0
                obs[f"left_joint_{i}.eff"] = 0.0
        
        # Get right arm observation  
        right_obs = self.right_client.get_observations()
        if isinstance(right_obs, dict):
            if "qpos" in right_obs:
                # Format: {'qpos': array, 'qvel': array, 'qeff': array}
                for i in range(min(7, len(right_obs["qpos"]))):
                    obs[f"right_joint_{i}.pos"] = float(right_obs["qpos"][i])
                    obs[f"right_joint_{i}.vel"] = float(right_obs.get("qvel", np.zeros(7))[i])
                    obs[f"right_joint_{i}.eff"] = float(right_obs.get("qeff", np.zeros(7))[i])
            elif "pos" in right_obs:
                # Format: {'pos': array, 'vel': array, 'eff': array}
                for i in range(min(7, len(right_obs["pos"]))):
                    obs[f"right_joint_{i}.pos"] = float(right_obs["pos"][i])
                    obs[f"right_joint_{i}.vel"] = float(right_obs.get("vel", np.zeros(7))[i])
                    obs[f"right_joint_{i}.eff"] = float(right_obs.get("eff", np.zeros(7))[i])
            else:
                # Try direct numpy array access
                for i in range(7):
                    obs[f"right_joint_{i}.pos"] = float(right_obs.get(i, 0.0))
                    obs[f"right_joint_{i}.vel"] = 0.0
                    obs[f"right_joint_{i}.eff"] = 0.0
        else:
            # Assume it's a numpy array of positions
            for i in range(min(7, len(right_obs))):
                obs[f"right_joint_{i}.pos"] = float(right_obs[i])
                obs[f"right_joint_{i}.vel"] = 0.0
                obs[f"right_joint_{i}.eff"] = 0.0
        
        return obs
    
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send action to both YAM arms."""
        if not self._is_connected:
            raise RuntimeError(f"{self.name} is not connected")
        
        import numpy as np
        
        # Check if this is a valid action
        has_left_keys = any(k.startswith("left_joint") for k in action.keys())
        has_right_keys = any(k.startswith("right_joint") for k in action.keys())
        
        if not has_left_keys and not has_right_keys:
            logger.warning("No valid YAM action keys found - ignoring action to prevent unwanted movement")
            return action
        
        # Initialize last positions if needed
        if self._last_left_positions is None:
            try:
                obs = self.get_observation()
                self._last_left_positions = [obs.get(f"left_joint_{i}.pos", 0.0) for i in range(7)]
                self._last_right_positions = [obs.get(f"right_joint_{i}.pos", 0.0) for i in range(7)]
            except:
                self._last_left_positions = [0.0] * 7
                self._last_right_positions = [0.0] * 7
        
        # Extract positions for left arm, using last valid positions as fallback
        left_positions = []
        for i in range(7):
            key = f"left_joint_{i}.pos"
            if key in action:
                left_positions.append(action[key])
            else:
                # Use last valid position instead of zero
                left_positions.append(self._last_left_positions[i])
        
        # Extract positions for right arm, using last valid positions as fallback
        right_positions = []
        for i in range(7):
            key = f"right_joint_{i}.pos"
            if key in action:
                right_positions.append(action[key])
            else:
                # Use last valid position instead of zero
                right_positions.append(self._last_right_positions[i])
        
        # Update last valid positions
        self._last_left_positions = left_positions
        self._last_right_positions = right_positions
        
        # Send commands to arms via ZMQ
        try:
            # The ZMQ client expects numpy arrays directly via command_joint_state
            # Send position commands to left arm
            self.left_client.command_joint_state(np.array(left_positions))
            
            # Send position commands to right arm
            self.right_client.command_joint_state(np.array(right_positions))
            
            logger.debug(f"Sent left positions: {left_positions[:3]}...")
            logger.debug(f"Sent right positions: {right_positions[:3]}...")
            
        except Exception as e:
            logger.error(f"Error sending commands via ZMQ: {e}")
            logger.error(f"Left positions: {left_positions}")
            logger.error(f"Right positions: {right_positions}")
        
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