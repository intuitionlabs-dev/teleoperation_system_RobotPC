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
        self.piper = C_PiperInterface_V2(port)  # Use default parameters like SDK demos
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

        # Initialize limits to None - will be set after motors are enabled
        self.min_pos = None
        self.max_pos = None

    def set_joint_positions(self, positions):
        # positions: list of 7 floats, first 6 are joint and 7 is gripper position
        # postions are in -100% to 100% range, we need to map them on the min and max positions
        # so -100% is min_pos and 100% is max_pos
        
        # Check if we have valid limits
        if self.min_pos is None or self.max_pos is None:
            print(f"[SDK] ERROR: Motor limits not set on {self.port}, cannot send commands")
            return
        
        print(f"[DEBUG {self.port}] Joint Positions: {positions[:6]}")
        
        scaled_positions = [
            self.min_pos[i] + (self.max_pos[i] - self.min_pos[i]) * (pos + 100) / 200
            for i, pos in enumerate(positions[:6])
        ]
        
        print(f"[DEBUG {self.port}] Joint Positions (Rescaled to the unit of the motor): {scaled_positions[:6]}")
        
        scaled_positions = [100.0 * pos for pos in scaled_positions[:6]]  # Adjust factor

        print(f"[DEBUG {self.port}] Joint Positions (100x after rescaling): {scaled_positions[:6]}")

        print(f"[DEBUG {self.port}] Gripper Position: {positions[6]}")
        # the gripper is from 0 to 100% range
        scaled_positions.append(self.min_pos[6] + (self.max_pos[6] - self.min_pos[6]) * positions[6] / 100)
        print(f"[DEBUG {self.port}] Gripper Position (Rescaled to the unit of the motor): {scaled_positions[6]}")
        
        # scaled_positions.append(positions[6])
        scaled_positions[6] = int(scaled_positions[6] * 10000)  # Convert to mm
        print(f"[DEBUG {self.port}] Gripper Position (10000x after rescaling): {scaled_positions[6]}")
        
        print(f"[DEBUG {self.port}] Rescaled positions (Full 7 joints): {scaled_positions}")

        # joint 0, 3 and 5 are inverted
        joint_0 = int(-scaled_positions[0])
        joint_1 = int(scaled_positions[1])
        joint_2 = int(scaled_positions[2])
        joint_3 = int(-scaled_positions[3])
        joint_4 = int(scaled_positions[4])
        joint_5 = int(-scaled_positions[5])
        joint_6 = int(scaled_positions[6])
        
        print(f"[DEBUG {self.port}] Final: J0={joint_0}, J1={joint_1}, J2={joint_2}, J3={joint_3}, J4={joint_4}, J5={joint_5}, J6={joint_6}")

        print("--------------------------------")
        # # Debug first few commands
        # if not hasattr(self, '_cmd_count'):
        #     self._cmd_count = 0
        # if self._cmd_count < 3:
        #     print(f"[DEBUG {self.port}] Cmd {self._cmd_count}: Input={[round(p,1) for p in positions]}")
        #     print(f"[DEBUG {self.port}] Scaled before 100x={[round(p,1) for p in scaled_positions]}")
        #     print(f"[DEBUG {self.port}] Final: J0={joint_0}, J1={joint_1}, J2={joint_2}, J3={joint_3}, J4={joint_4}, J5={joint_5}")
        #     self._cmd_count += 1
        
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
        """Enable motors following proper sequence"""
        try:
            # Step 1: Clear any errors
            self.piper.EmergencyStop(0x00)  # 0x00 to clear emergency stop
            time.sleep(0.1)
            
            # Step 2: Enable the robot - work around SDK bug
            print(f"[SDK] Enabling robot on {self.port}...")
            
            # EnablePiper has a bug - it checks status BEFORE enabling
            # So we need to work around it:
            # 1. Call EnablePiper once to actually enable (ignore return value)
            self.piper.EnablePiper()
            time.sleep(0.5)  # Give motors time to enable
            
            # 2. Now check if motors are actually enabled
            enable_status = self.piper.GetArmEnableStatus()
            print(f"[SDK] Motor enable status on {self.port}: {enable_status}")
            
            if all(enable_status):
                print(f"[SDK] All motors enabled on {self.port}")
            else:
                # If not all enabled, try direct EnableArm
                enabled_count = sum(enable_status)
                print(f"[SDK] Only {enabled_count}/6 motors enabled, trying EnableArm(7) directly...")
                self.piper.EnableArm(7)
                time.sleep(0.5)
                
                # Check again
                enable_status = self.piper.GetArmEnableStatus()
                print(f"[SDK] Motor enable status after EnableArm(7): {enable_status}")
                
                if not all(enable_status):
                    # Try enabling individual motors that are disabled
                    print(f"[SDK] Trying to enable individual motors...")
                    for i, enabled in enumerate(enable_status):
                        if not enabled:
                            motor_num = i + 1  # Motor numbers are 1-based
                            print(f"[SDK] Enabling motor {motor_num} individually...")
                            self.piper.EnableArm(motor_num, 0x02)
                            time.sleep(0.2)
                    
                    # Final check after individual enables
                    time.sleep(0.5)
                    enable_status = self.piper.GetArmEnableStatus()
                    print(f"[SDK] Final motor enable status: {enable_status}")
                    
                    if all(enable_status):
                        print(f"[SDK] All motors now enabled on {self.port}")
                    else:
                        enabled_count = sum(enable_status)
                        disabled_motors = [i+1 for i, enabled in enumerate(enable_status) if not enabled]
                        print(f"[SDK] WARNING: Only {enabled_count}/6 motors enabled on {self.port}")
                        print(f"[SDK] Disabled motors: {disabled_motors}")
                        print(f"[SDK] Continuing anyway...")
            
            time.sleep(0.5)  # Give motors time to fully initialize
            
            # Step 3: Get motor limits after enabling
            if self.min_pos is None or self.max_pos is None:
                print(f"[SDK] Getting motor limits on {self.port}...")
                angel_status = self.piper.GetAllMotorAngleLimitMaxSpd()
                self.min_pos = [
                    pos.min_angle_limit for pos in angel_status.all_motor_angle_limit_max_spd.motor[1:7]
                ] + [0]
                self.max_pos = [
                    pos.max_angle_limit for pos in angel_status.all_motor_angle_limit_max_spd.motor[1:7]
                ] + [10]  # Gripper max position in mm
                
                # The limits are in 0.1 degree units
                print(f"[SDK] MOTOR LIMITS from GetAllMotorAngleLimitMaxSpd on {self.port}:")
                print(f"[SDK] Min (0.1°): {self.min_pos[:6]}")
                print(f"[SDK] Max (0.1°): {self.max_pos[:6]}")
                print(f"[SDK] Ranges (0.1°): {[self.max_pos[i] - self.min_pos[i] for i in range(6)]}")
                
                # Fallback to default limits if motor limits are all zero
                if all(x == 0 for x in self.min_pos[:6]) and all(x == 0 for x in self.max_pos[:6]):
                    print(f"[SDK] WARNING: Motor limits are zero on {self.port}, using default values")
                    print(f"[SDK] Default limits:")
                    print(f"[SDK] Min (0.1°): [-1500, 0, -1700, -1000, -700, -1200, 0]")
                    print(f"[SDK] Max (0.1°): [1500, 1800, 0, 1000, 700, 1200, 10]")
                    # Default Piper joint limits in 0.1 degree units
                    self.min_pos = [-1500, 0, -1700, -1000, -700, -1200, 0]
                    self.max_pos = [1500, 1800, 0, 1000, 700, 1200, 10]
            
            # Step 4: Set control mode
            print(f"[SDK] Setting control mode on {self.port}...")
            self.piper.MotionCtrl_2(0x01, 0x01, 100, 0xAD)  # MIT mode
            time.sleep(0.1)
            
            # Step 5: Initialize gripper
            self.piper.GripperCtrl(0, 1000, 0x01, 0)
            time.sleep(0.1)
            
            print(f"[SDK] Motors enabled on {self.port}")
            return True
            
        except Exception as e:
            print(f"[SDK] Failed to enable motors on {self.port}: {e}")
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
