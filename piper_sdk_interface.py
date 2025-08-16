# Piper SDK interface for LeRobot integration

import time
from typing import Any, Dict

try:
    from piper_sdk import C_PiperInterface_V2
except ImportError:
    print("Is the piper_sdk installed: pip install piper_sdk")
    C_PiperInterface_V2 = None  # For type checking and docs


class PiperSDKInterface:
    def __init__(self, port: str = "can0", auto_enable_on_connect: bool = False):
        if C_PiperInterface_V2 is None:
            raise ImportError("piper_sdk is not installed.")
        self.port = port  # Store for compatibility
        self.piper = C_PiperInterface_V2(port, start_sdk_joint_limit=True) # default is False
        self.piper.ConnectPort()
        # Optionally auto-enable on connect (legacy behavior). Default disabled for energy saving.
        if auto_enable_on_connect:
            # Harden against early-boot timing and transient CAN errors
            enable_deadline_s = time.time() + 10.0
            backoff = 0.02
            while True:
                try:
                    if self.piper.EnablePiper():
                        break
                except Exception:
                    # Swallow transient send failures during boot; retry shortly
                    pass
                if time.time() > enable_deadline_s:
                    # One last attempt before giving up
                    try:
                        if self.piper.EnablePiper():
                            break
                    except Exception:
                        pass
                    raise RuntimeError("EnablePiper failed after retries")
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 0.2)
            # Ensure gripper enabled in legacy mode
            self.piper.GripperCtrl(0, 1000, 0x01, 0)

        # Get the min and max positions for each joint and gripper
        angel_status = self.piper.GetAllMotorAngleLimitMaxSpd()
        self.min_pos = [
            pos.min_angle_limit for pos in angel_status.all_motor_angle_limit_max_spd.motor[1:7]
        ] + [0]
        self.max_pos = [
            pos.max_angle_limit for pos in angel_status.all_motor_angle_limit_max_spd.motor[1:7]
        ] + [10]  # Gripper max position in mm
        
        # Fallback to default limits if motor limits are all zero (CAN communication issue)
        if all(x == 0 for x in self.min_pos[:6]) and all(x == 0 for x in self.max_pos[:6]):
            print(f"[SDK] WARNING: Motor limits are zero on {port}, using default values")
            # Default Piper joint limits in degrees
            self.min_pos = [-90, -90, -90, -90, -90, -90, 0]
            self.max_pos = [90, 90, 90, 90, 90, 90, 10]
        
        print(f"[SDK] Motor limits from GetAllMotorAngleLimitMaxSpd on {port}:")
        print(f"[SDK] Min: {self.min_pos[:6]}")
        print(f"[SDK] Max: {self.max_pos[:6]}")
        print(f"[SDK] Ranges: {[self.max_pos[i] - self.min_pos[i] for i in range(6)]}")

    def set_joint_positions(self, positions):
        # positions: list of 7 floats, first 6 are joint and 7 is gripper position
        # postions are in -100% to 100% range, we need to map them on the min and max positions
        # so -100% is min_pos and 100% is max_pos
        scaled_positions = [
            self.min_pos[i] + (self.max_pos[i] - self.min_pos[i]) * (pos + 100) / 200
            for i, pos in enumerate(positions[:6])
        ]
        scaled_positions = [100.0 * pos for pos in scaled_positions]  # Adjust factor

        # the gripper is from 0 to 100% range
        scaled_positions.append(self.min_pos[6] + (self.max_pos[6] - self.min_pos[6]) * positions[6] / 100)
        scaled_positions[6] = int(scaled_positions[6] * 10000)  # Convert to mm

        # joint 0, 3 and 5 are inverted
        joint_0 = int(-scaled_positions[0])
        joint_1 = int(scaled_positions[1])
        joint_2 = int(scaled_positions[2])
        joint_3 = int(-scaled_positions[3])
        joint_4 = int(scaled_positions[4])
        joint_5 = int(-scaled_positions[5])
        joint_6 = int(scaled_positions[6])

        # Debug first few commands
        if not hasattr(self, '_cmd_count'):
            self._cmd_count = 0
        if self._cmd_count < 3:
            print(f"[DEBUG {self.port}] Cmd {self._cmd_count}: Input={[round(p,1) for p in positions]}")
            print(f"[DEBUG {self.port}] Scaled before 100x={[round(p,1) for p in scaled_positions[:6]]}")
            print(f"[DEBUG {self.port}] Final: J0={joint_0}, J1={joint_1}, J2={joint_2}, J3={joint_3}, J4={joint_4}, J5={joint_5}")
            self._cmd_count += 1
        
        # self.piper.MotionCtrl_2(0x01, 0x01, 100, 0x00) # default is position control
        try:
            self.piper.MotionCtrl_2(0x01, 0x01, 100, 0xAD) # set to mit control
            self.piper.JointCtrl(joint_0, joint_1, joint_2, joint_3, joint_4, joint_5)
            self.piper.GripperCtrl(joint_6, 1000, 0x01, 0)
        except Exception as e:
            # Log but don't crash on CAN send failures
            if "SEND_MESSAGE_FAILED" not in str(e):
                print(f"[SDK] Error sending command: {e}")

    def get_status(self) -> Dict[str, Any]:
        joint_status = self.piper.GetArmJointMsgs()
        gripper = self.piper.GetArmGripperMsgs()
        gripper.gripper_state.grippers_angle

        joint_state = joint_status.joint_state
        obs_dict = {
            "joint_0.pos": joint_state.joint_1,
            "joint_1.pos": joint_state.joint_2,
            "joint_2.pos": joint_state.joint_3,
            "joint_3.pos": joint_state.joint_4,
            "joint_4.pos": joint_state.joint_5,
            "joint_5.pos": joint_state.joint_6,
        }
        obs_dict.update(
            {
                "joint_6.pos": gripper.gripper_state.grippers_angle,
            }
        )

        return obs_dict

    def enable_motors(self):
        """Enable motors - compatibility method"""
        try:
            # Clear errors
            self.piper.EmergencyStop(0x02)
            self.piper.JointConfig(joint_num=7, clear_err=0xAE)
            time.sleep(0.1)
            
            # Enable with retries
            attempts = 0
            max_attempts = 50
            while not self.piper.EnablePiper() and attempts < max_attempts:
                time.sleep(0.02)
                attempts += 1
            
            # Ensure all motors enabled
            self.piper.EnableArm(0xFF, 0x02)
            time.sleep(0.1)
            
            # Set MIT mode
            self.piper.ModeCtrl(0x01, 0x04, 100, 0xAD)
            self.piper.MotionCtrl_2(0x01, 0x01, 100, 0xAD)
            time.sleep(0.1)
            
            # Initialize gripper
            self.piper.GripperCtrl(0, 1000, 0x03, 0)
            time.sleep(0.05)
            self.piper.GripperCtrl(0, 1000, 0x01, 0)
            time.sleep(0.1)
            self.piper.GripperCtrl(0, 1000, 0x01, 0xAE)
            time.sleep(0.05)
            
            print(f"[SDK] Motors enabled")
            return True
        except Exception as e:
            print(f"[SDK] Failed to enable motors: {e}")
            return False
    
    def disable_motors(self):
        """Disable motors - compatibility method"""
        try:
            self.piper.DisablePiper()
            print("[SDK] Motors disabled")
            return True
        except Exception as e:
            print(f"[SDK] Failed to disable motors: {e}")
            return False
    
    def disconnect(self):
        # No explicit disconnect
        pass
