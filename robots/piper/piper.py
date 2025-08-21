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
        self._last_valid_positions = None  # Store last valid positions
    
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
        
        # Debug: Log received action
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Piper received action keys: {list(action.keys())}")
        logger.debug(f"Piper received action values: {action}")
        
        # Check if this is a valid action (has the expected keys)
        expected_keys = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", 
                        "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]
        alt_keys = [f"joint_{i}.pos" for i in range(7)]
        
        has_expected_keys = any(key in action for key in expected_keys)
        has_alt_keys = any(key in action for key in alt_keys)
        
        if not has_expected_keys and not has_alt_keys:
            # No valid action keys found - don't move the robot
            logger.warning("No valid action keys found - ignoring action to prevent unwanted movement")
            return action
        
        # Map the action from the leader to joints for the follower
        # Use last valid positions as fallback instead of 0
        if self._last_valid_positions is None:
            # First time - get current positions from robot
            try:
                current_obs = self.get_observation()
                self._last_valid_positions = [
                    current_obs.get(f"joint_{i}.pos", 0) for i in range(7)
                ]
            except:
                # If we can't get current positions, use safe defaults
                self._last_valid_positions = [0, 0, 0, 0, 0, 0, 0]
        
        # Build positions array, using last valid positions as defaults
        positions = [
            action.get("shoulder_pan.pos", action.get("joint_0.pos", self._last_valid_positions[0])),
            action.get("shoulder_lift.pos", action.get("joint_1.pos", self._last_valid_positions[1])),
            action.get("elbow_flex.pos", action.get("joint_2.pos", self._last_valid_positions[2])),
            action.get("joint_3.pos", self._last_valid_positions[3]),
            action.get("wrist_flex.pos", action.get("joint_4.pos", self._last_valid_positions[4])),
            action.get("wrist_roll.pos", action.get("joint_5.pos", self._last_valid_positions[5])),
            action.get("gripper.pos", action.get("joint_6.pos", self._last_valid_positions[6])),
        ]
        
        # Update last valid positions
        self._last_valid_positions = positions
        
        logger.debug(f"Sending positions to SDK: {positions}")
        
        self.sdk.set_joint_positions(positions)
        return action
    
    def stop(self):
        if not self._is_connected:
            return
        current_pos = self.sdk.get_status()
        self.send_action(current_pos)