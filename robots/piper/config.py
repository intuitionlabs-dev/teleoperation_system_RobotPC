"""
Configuration for Piper robot.
"""

from dataclasses import dataclass
from robots.config import RobotConfig


@dataclass
class PiperConfig(RobotConfig):
    """Configuration for a Piper robot arm."""
    port: str = "piper"