"""Configuration for bimanual Piper follower"""
from dataclasses import dataclass
from piper_robot import PiperConfig


@dataclass  
class BimanualPiperFollowerConfig:
    """Configuration for a bimanual Piper robot system"""
    left_robot: PiperConfig = None
    right_robot: PiperConfig = None
    
    def __post_init__(self):
        if self.left_robot is None:
            self.left_robot = PiperConfig(device_path="left_piper")
        if self.right_robot is None:
            self.right_robot = PiperConfig(device_path="right_piper")
