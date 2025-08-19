"""Configuration for bimanual YAM follower robot."""

from dataclasses import dataclass
from typing import Optional

from robots.config import RobotConfig


@dataclass
class YAMConfig(RobotConfig):
    """Configuration for a single YAM arm."""
    config_path: str = ""
    """Path to the YAML configuration file for the arm."""
    
    hardware_port: int = 6001
    """ZMQ server port for hardware communication."""


@dataclass
class BimanualYAMFollowerConfig(RobotConfig):
    """Configuration for bimanual YAM follower robot."""
    left_arm: YAMConfig = None
    right_arm: YAMConfig = None
    
    # Virtual environment path for gello_software
    venv_path: str = "/home/francesco/meta-tele-RTX/clean_version/i2rt/gello_software/.venv"
    
    # Gello software path
    gello_path: str = "/home/francesco/meta-tele-RTX/clean_version/i2rt/gello_software"