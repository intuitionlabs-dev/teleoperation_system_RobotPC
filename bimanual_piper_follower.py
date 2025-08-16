"""Minimal bimanual Piper follower robot"""
from typing import Any

from piper_robot import Piper, PiperConfig


class BimanualPiperFollower:
    """A bimanual robot composed of two Piper arms."""
    
    def __init__(self, config):
        self.config = config
        self.left_arm = Piper(config.left_robot)
        self.right_arm = Piper(config.right_robot)
        self._is_connected = False
    
    @property
    def is_connected(self) -> bool:
        return self.left_arm.is_connected and self.right_arm.is_connected
    
    def connect(self, calibrate: bool = True) -> None:
        if self.is_connected:
            print(f"Already connected")
            return
        
        self.left_arm.connect(calibrate=calibrate)
        self.right_arm.connect(calibrate=calibrate)
        self._is_connected = True
        print(f"BimanualPiperFollower connected.")
    
    def set_motors_engaged(self, engaged: bool) -> None:
        """Enable or disable motors on both arms"""
        self.left_arm.set_motors_engaged(engaged)
        self.right_arm.set_motors_engaged(engaged)
    
    def get_observation(self) -> dict[str, Any]:
        """Get observations from both arms"""
        left_obs = self.left_arm.get_observation()
        right_obs = self.right_arm.get_observation()
        
        combined_obs = {}
        # Combine observations with proper namespacing
        for key, value in left_obs.items():
            combined_obs[f"observation.left_piper.{key}"] = value
        for key, value in right_obs.items():
            combined_obs[f"observation.right_piper.{key}"] = value
        
        return combined_obs
    
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send actions to both arms"""
        if not self.is_connected:
            raise RuntimeError("Robot is not connected")
        
        # Extract left and right actions
        left_action = {}
        right_action = {}
        
        for key, val in action.items():
            if "left_piper" in key:
                # Extract the joint name after "action.left_piper."
                joint_key = key.split("action.left_piper.")[-1]
                left_action[joint_key] = val
            elif "right_piper" in key:
                # Extract the joint name after "action.right_piper."
                joint_key = key.split("action.right_piper.")[-1]
                right_action[joint_key] = val
        
        # Send actions to arms
        if left_action:
            self.left_arm.send_action(left_action)
        if right_action:
            self.right_arm.send_action(right_action)
        
        return action
    
    def disconnect(self) -> None:
        """Disconnect both arms"""
        if not self.is_connected:
            return
        
        self.left_arm.disconnect()
        self.right_arm.disconnect()
        self._is_connected = False
