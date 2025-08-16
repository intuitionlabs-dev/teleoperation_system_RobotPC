"""Minimal Piper SDK interface"""
import time
from typing import Any, Dict

try:
    from piper_sdk import C_PiperInterface_V2
    from piper_sdk.piper_param import C_PiperParamManager
except ImportError:
    print("WARNING: piper_sdk not installed. Install with: pip install piper_sdk")
    C_PiperInterface_V2 = None
    C_PiperParamManager = None


class PiperSDKInterface:
    """Interface to Piper robot SDK"""
    
    def __init__(self, port: str = "can0", auto_enable_on_connect: bool = False):
        if C_PiperInterface_V2 is None:
            raise ImportError("piper_sdk is not installed")
        
        self.piper = C_PiperInterface_V2(port, start_sdk_joint_limit=True)
        self.piper.ConnectPort()
        
        # Get joint limits from SDK
        param_manager = C_PiperParamManager()
        piper_params = param_manager.GetCurrentPiperParam()
        joint_limits = piper_params["joint_limit"]
        
        # Convert radians to degrees for joints, keep mm for gripper
        self.min_pos = [
            joint_limits["j1"][0] * 180.0 / 3.14159,
            joint_limits["j2"][0] * 180.0 / 3.14159,
            joint_limits["j3"][0] * 180.0 / 3.14159,
            joint_limits["j4"][0] * 180.0 / 3.14159,
            joint_limits["j5"][0] * 180.0 / 3.14159,
            joint_limits["j6"][0] * 180.0 / 3.14159,
            piper_params["gripper_range"][0] * 1000  # m to mm
        ]
        self.max_pos = [
            joint_limits["j1"][1] * 180.0 / 3.14159,
            joint_limits["j2"][1] * 180.0 / 3.14159,
            joint_limits["j3"][1] * 180.0 / 3.14159,
            joint_limits["j4"][1] * 180.0 / 3.14159,
            joint_limits["j5"][1] * 180.0 / 3.14159,
            joint_limits["j6"][1] * 180.0 / 3.14159,
            piper_params["gripper_range"][1] * 1000  # m to mm
        ]
        
        print(f"[SDK] Connected to {port}")
        
        if auto_enable_on_connect:
            self.enable_motors()
    
    def enable_motors(self):
        """Enable robot motors"""
        max_retries = 5
        for i in range(max_retries):
            try:
                if self.piper.EnablePiper():
                    self.piper.GripperCtrl(0, 1000, 0x01, 0)  # Enable gripper
                    print("[SDK] Motors enabled")
                    return True
            except Exception as e:
                if i < max_retries - 1:
                    time.sleep(0.1)
                else:
                    print(f"[SDK] Failed to enable motors: {e}")
                    return False
        return False
    
    def disable_motors(self):
        """Disable robot motors"""
        try:
            self.piper.DisablePiper()
            print("[SDK] Motors disabled")
            return True
        except Exception as e:
            print(f"[SDK] Failed to disable motors: {e}")
            return False
    
    def set_joint_positions(self, positions):
        """Set joint positions
        positions: list of 7 floats in range [-100, 100] for joints, [0, 100] for gripper
        """
        # Scale from percentage to actual joint ranges
        scaled_positions = []
        for i in range(6):  # Joints
            pos_pct = positions[i]
            scaled = self.min_pos[i] + (self.max_pos[i] - self.min_pos[i]) * (pos_pct + 100) / 200
            scaled_positions.append(scaled * 1000.0)  # Convert to 0.001 degrees
        
        # Gripper: 0-100% range
        gripper_mm = self.min_pos[6] + (self.max_pos[6] - self.min_pos[6]) * positions[6] / 100
        scaled_positions.append(gripper_mm * 10000)  # Convert to 0.0001 mm
        
        # Apply joint inversions and send command
        joint_0 = int(-scaled_positions[0])  # Inverted
        joint_1 = int(scaled_positions[1])
        joint_2 = int(scaled_positions[2])
        joint_3 = int(-scaled_positions[3])  # Inverted
        joint_4 = int(scaled_positions[4])
        joint_5 = int(-scaled_positions[5])  # Inverted
        gripper = int(scaled_positions[6])
        
        self.piper.GripperCtrl(gripper, 1000, 0x01, 0)
        self.piper.JointCtrlROI(2047, 2047, 2047, 2047, 2047, 2047,
                                joint_0, joint_1, joint_2, joint_3, joint_4, joint_5)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current robot status"""
        # Request current status
        self.piper.GetJointStatus()
        
        # Get joint states
        joint_status = self.piper.GetJointStatus()
        joint_pos = joint_status.joint_curMoto_angle
        joint_vel = joint_status.joint_curMoto_speed
        joint_load = joint_status.joint_motor_torque
        gripper_pos = joint_status.gripper_moto_pulse
        
        # Convert from SDK units to percentages
        position_pct = []
        for i in range(6):
            # Convert from 0.001 degrees to percentage
            pos_deg = joint_pos[i] / 1000.0
            # Apply inversions
            if i in [0, 3, 5]:
                pos_deg = -pos_deg
            # Convert to percentage
            pct = (pos_deg - self.min_pos[i]) / (self.max_pos[i] - self.min_pos[i]) * 200 - 100
            position_pct.append(pct)
        
        # Gripper: convert from 0.0001 mm to percentage
        gripper_mm = gripper_pos / 10000.0
        gripper_pct = (gripper_mm - self.min_pos[6]) / (self.max_pos[6] - self.min_pos[6]) * 100
        position_pct.append(gripper_pct)
        
        # Velocity and load
        velocity_pct = [vel / 1000.0 for vel in joint_vel[:6]] + [0.0]  # No gripper velocity
        load_pct = [load / 1000.0 for load in joint_load[:6]] + [0.0]  # No gripper load
        
        return {
            "position": position_pct,
            "velocity": velocity_pct,
            "load": load_pct,
            "gripper_position": gripper_pct
        }
    
    def disconnect(self):
        """Disconnect from robot"""
        try:
            self.piper.DisconnectPort()
            print("[SDK] Disconnected")
        except Exception as e:
            print(f"[SDK] Error disconnecting: {e}")
