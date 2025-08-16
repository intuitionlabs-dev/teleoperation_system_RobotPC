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
            # Add delay for right arm to avoid conflicts
            if "right" in port:
                print("[SDK] Waiting 1s before enabling right arm motors...")
                time.sleep(1.0)
            self.enable_motors()
    
    def enable_motors(self):
        """Enable robot motors"""
        max_retries = 5
        for i in range(max_retries):
            try:
                result = self.piper.EnablePiper()
                print(f"[DEBUG] EnablePiper on {self.device_path} returned: {result}")
                if result:
                    self.piper.GripperCtrl(0, 1000, 0x01, 0)  # Enable gripper
                    print(f"[SDK] Motors enabled on {self.device_path}")
                    return True
                else:
                    print(f"[SDK] EnablePiper failed on {self.device_path}, retry {i+1}/{max_retries}")
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
        # Convert from normalized (-100 to 100) to degrees
        # The Piper SDK expects positions in units of 0.001 degrees
        joint_positions_deg = []
        
        for i in range(6):  # Joints
            # Map -100 to 100 range to actual joint limits in degrees
            normalized = positions[i]  # Already -100 to 100
            # Map to joint range
            center = (self.min_pos[i] + self.max_pos[i]) / 2.0
            range_half = (self.max_pos[i] - self.min_pos[i]) / 2.0
            actual_deg = center + (normalized / 100.0) * range_half
            joint_positions_deg.append(actual_deg)
        
        # Apply joint inversions and convert to 0.001 degrees
        joint_0 = int(-joint_positions_deg[0] * 1000)  # Inverted
        joint_1 = int(joint_positions_deg[1] * 1000)
        joint_2 = int(joint_positions_deg[2] * 1000)
        joint_3 = int(-joint_positions_deg[3] * 1000)  # Inverted
        joint_4 = int(joint_positions_deg[4] * 1000)
        joint_5 = int(-joint_positions_deg[5] * 1000)  # Inverted
        
        # Gripper: map 0-100 to actual range in mm
        gripper_pct = positions[6]
        gripper_mm = self.min_pos[6] + (self.max_pos[6] - self.min_pos[6]) * gripper_pct / 100
        gripper = int(gripper_mm * 10000)  # Convert to 0.0001 mm
        
        # Debug: print first position command
        if not hasattr(self, '_first_pos_logged'):
            print(f"[DEBUG] Sending positions to CAN: j0={joint_0}, j1={joint_1}, j2={joint_2}, j3={joint_3}, j4={joint_4}, j5={joint_5}, gripper={gripper}")
            self._first_pos_logged = True
        
        self.piper.GripperCtrl(gripper, 1000, 0x01, 0)
        self.piper.JointCtrl(joint_0, joint_1, joint_2, joint_3, joint_4, joint_5)
    
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
