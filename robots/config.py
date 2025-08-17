"""
Base configuration for robots.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RobotConfig:
    """Base configuration class for robots."""
    id: str = "default"
    calibration_dir: Optional[Path] = None