"""Bimanual YAM robot module."""

from .bimanual_yam_follower import BimanualYAMFollower
from .config import BimanualYAMFollowerConfig, YAMConfig

__all__ = [
    "BimanualYAMFollower",
    "BimanualYAMFollowerConfig",
    "YAMConfig",
]