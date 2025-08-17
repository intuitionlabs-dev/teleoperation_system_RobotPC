"""
Piper robot implementation.
"""

from typing import Any
from robots.robot import Robot
from robots.piper.config import PiperConfig
from robots.piper.piper_sdk_interface import PiperSDKInterface


class Piper(Robot):
    """Piper follower arm robot."""
    
    config_class = PiperConfig
    name = "piper"
    
    def __init__(self, config: PiperConfig):
        super().__init__(config)
        self.config = config
        self.sdk = None
        self._is_connected = False
    
    @property
    def _motors_ft(self) -> dict[str, type]:
        return {f"joint_{i}.pos": float for i in range(7)}
    
    @property
    def observation_features(self) -> dict:
        return self._motors_ft
    
    @property
    def action_features(self) -> dict:
        return self._motors_ft
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    def connect(self, calibrate: bool = True) -> None:
        if self._is_connected:
            raise RuntimeError(f"{self} is already connected.")
        self.sdk = PiperSDKInterface(port=self.config.port)
        self._is_connected = True
        self.configure()
    
    def disconnect(self) -> None:
        if not self._is_connected:
            return
        self.sdk.disconnect()
        self._is_connected = False
    
    @property
    def is_calibrated(self) -> bool:
        return True
    
    def calibrate(self) -> None:
        pass
    
    def configure(self) -> None:
        pass
    
    def get_observation(self) -> dict[str, Any]:
        if not self._is_connected:
            raise RuntimeError(f"{self} is not connected.")
        obs_dict = self.sdk.get_status()
        return obs_dict
    
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        if not self._is_connected:
            raise RuntimeError(f"{self} is not connected.")
        
        # Map the action from the leader to joints for the follower
        # Handle both key styles (shoulder_pan.pos and joint_0.pos)
        positions = [
            action.get("shoulder_pan.pos", action.get("joint_0.pos", 0)),
            action.get("shoulder_lift.pos", action.get("joint_1.pos", 0)),
            action.get("elbow_flex.pos", action.get("joint_2.pos", 0)),
            action.get("joint_3.pos", 0),
            action.get("wrist_flex.pos", action.get("joint_4.pos", 0)),
            action.get("wrist_roll.pos", action.get("joint_5.pos", 0)),
            action.get("gripper.pos", action.get("joint_6.pos", 0)),
        ]
        
        self.sdk.set_joint_positions(positions)
        return action
    
    def stop(self):
        if not self._is_connected:
            return
        current_pos = self.sdk.get_status()
        self.send_action(current_pos)