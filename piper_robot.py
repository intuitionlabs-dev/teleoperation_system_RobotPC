"""Minimal Piper robot implementation"""
from dataclasses import dataclass
from typing import Any
from piper_sdk_interface import PiperSDKInterface


@dataclass
class PiperConfig:
    """Configuration for a single Piper arm"""
    robot_type: str = "piper"
    device_path: str = "can0"  # e.g., "left_piper" or "right_piper"


class Piper:
    """Single Piper arm robot"""
    
    def __init__(self, config: PiperConfig):
        self.config = config
        self.sdk = None
        self._is_connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    def connect(self, calibrate: bool = True) -> None:
        if self._is_connected:
            print(f"Piper on {self.config.device_path} already connected")
            return
        
        # Connect without auto-enable (host_broadcast will handle motor enable)
        self.sdk = PiperSDKInterface(port=self.config.device_path, auto_enable_on_connect=False)
        self._is_connected = True
        print(f"Piper connected on {self.config.device_path}")
    
    def set_motors_engaged(self, engaged: bool) -> None:
        """Enable or disable motors"""
        if not self._is_connected:
            return
        
        if engaged:
            self.sdk.enable_motors()
        else:
            self.sdk.disable_motors()
    
    def get_observation(self) -> dict[str, Any]:
        """Get current robot state"""
        if not self._is_connected:
            raise RuntimeError(f"Piper on {self.config.device_path} is not connected")
        
        return self.sdk.get_status()
    
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send action to robot"""
        if not self._is_connected:
            raise RuntimeError(f"Piper on {self.config.device_path} is not connected")
        
        # Map action keys to positions array
        # Handle both teleop style (e.g., "shoulder_pan.pos") and stop style (e.g., "joint_0.pos")
        positions = [
            action.get("shoulder_pan.pos", action.get("joint_0.pos", 0)),
            action.get("shoulder_lift.pos", action.get("joint_1.pos", 0)),
            action.get("elbow_flex.pos", action.get("joint_2.pos", 0)),
            action.get("joint_3.pos", 0),
            action.get("wrist_flex.pos", action.get("joint_4.pos", 0)),
            action.get("wrist_roll.pos", action.get("joint_5.pos", 0)),
            action.get("gripper.pos", action.get("joint_6.pos", 50)),  # Default to 50% open
        ]
        
        # Debug logging removed - see piper_sdk_interface for command details
        
        self.sdk.set_joint_positions(positions)
        return action
    
    def disconnect(self) -> None:
        """Disconnect from robot"""
        if not self._is_connected:
            return
        
        self.sdk.disconnect()
        self._is_connected = False
        print(f"Piper on {self.config.device_path} disconnected")
