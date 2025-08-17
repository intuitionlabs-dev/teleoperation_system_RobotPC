"""
Bimanual Piper Follower Robot - Controls two Piper arms simultaneously.
"""

import logging
from functools import cached_property
from typing import Any

from robots.robot import Robot
from robots.piper.piper import Piper
from .config import BimanualPiperFollowerConfig

logger = logging.getLogger(__name__)


class BimanualPiperFollower(Robot):
    """
    A bimanual robot composed of two Piper follower arms.
    """
    
    config_class = BimanualPiperFollowerConfig
    name = "bimanual_piper_follower"
    
    def __init__(self, config: BimanualPiperFollowerConfig):
        super().__init__(config)
        self.config = config
        self.left_arm = Piper(config.left_arm)
        self.right_arm = Piper(config.right_arm)
    
    @property
    def _motors_ft(self) -> dict[str, type]:
        left_motors_ft = self.left_arm.action_features
        right_motors_ft = self.right_arm.action_features
        combined_motors_ft = {}
        for key in left_motors_ft:
            combined_motors_ft[f"left_{key}"] = left_motors_ft[key]
        for key in right_motors_ft:
            combined_motors_ft[f"right_{key}"] = right_motors_ft[key]
        return combined_motors_ft
    
    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        return self._motors_ft
    
    @cached_property
    def action_features(self) -> dict[str, type]:
        return self._motors_ft
    
    @property
    def is_connected(self) -> bool:
        return self.left_arm.is_connected and self.right_arm.is_connected
    
    def connect(self, calibrate: bool = True) -> None:
        if self.is_connected:
            raise RuntimeError(f"{self} already connected")
        
        self.left_arm.connect(calibrate=calibrate)
        self.right_arm.connect(calibrate=calibrate)
        
        logger.info(f"{self} connected.")
    
    @property
    def is_calibrated(self) -> bool:
        return self.left_arm.is_calibrated and self.right_arm.is_calibrated
    
    def calibrate(self) -> None:
        raise NotImplementedError("Calibration for BimanualPiperFollower is not implemented.")
    
    def configure(self) -> None:
        self.left_arm.configure()
        self.right_arm.configure()
        logger.info(f"{self} configured.")
    
    def get_observation(self) -> dict[str, Any]:
        left_obs = self.left_arm.get_observation()
        right_obs = self.right_arm.get_observation()
        combined_obs = {}
        for key, value in left_obs.items():
            combined_obs[f"left_{key}"] = value
        for key, value in right_obs.items():
            combined_obs[f"right_{key}"] = value
        
        return combined_obs
    
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        if not self.is_connected:
            raise RuntimeError(f"{self} is not connected.")
        
        left_action = {key.removeprefix("left_"): val for key, val in action.items() if key.startswith("left_")}
        right_action = {key.removeprefix("right_"): val for key, val in action.items() if key.startswith("right_")}
        
        if not left_action:
            logger.warning("Received action without left_ keys - left arm will not move.")
        if not right_action:
            logger.warning("Received action without right_ keys - right arm will not move.")
        
        self.left_arm.send_action(left_action)
        self.right_arm.send_action(right_action)
        
        return action
    
    def disconnect(self):
        if not self.is_connected:
            raise RuntimeError(f"{self} is not connected.")
        
        self.left_arm.disconnect()
        self.right_arm.disconnect()
        
        logger.info(f"{self} disconnected.")