"""
Configuration for Bimanual Piper robots.
"""

from dataclasses import dataclass, field
from robots.config import RobotConfig
from robots.piper.config import PiperConfig


@dataclass
class BimanualPiperFollowerConfig(RobotConfig):
    """Configuration for a bimanual Piper follower robot."""
    left_arm: PiperConfig = field(default_factory=lambda: PiperConfig(port="left_piper"))
    right_arm: PiperConfig = field(default_factory=lambda: PiperConfig(port="right_piper"))