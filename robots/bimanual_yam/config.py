"""Configuration for bimanual YAM follower robot."""

from dataclasses import dataclass
from typing import Optional

from robots.config import RobotConfig


@dataclass
class YAMConfig(RobotConfig):
    """Configuration for a single YAM arm."""
    channel: str = "can_follow_l"
    """CAN channel for the YAM arm (e.g., can_follow_l, can_follow_r)."""
    
    hardware_port: int = 6001
    """ZMQ server port for hardware communication."""


@dataclass
class BimanualYAMFollowerConfig(RobotConfig):
    """Configuration for bimanual YAM follower robot."""
    left_arm: YAMConfig = None
    right_arm: YAMConfig = None
    
    # Virtual environment path for gello_software (relative to teleoperation_system_RobotPC)
    venv_path: str = "../gello_software/.venv"
    
    # Gello software path (relative to teleoperation_system_RobotPC)
    gello_path: str = "../gello_software"