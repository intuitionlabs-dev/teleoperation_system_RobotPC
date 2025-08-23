from typing import Dict
import sys
import os

import numpy as np

from gello.robots.robot import Robot


class X5Robot(Robot):
    """A class representing an ARX X5 robot."""

    def __init__(self, channel="can0"):
        import time
        
        # Add ARX X5 Python path
        arx_path = "/home/group/i2rt/ARX-dynamixel/RobotLearningGello/ARX_X5/py"
        if arx_path not in sys.path:
            sys.path.insert(0, arx_path)
        
        # Set environment variables for ARX
        os.environ['LD_LIBRARY_PATH'] = f"/home/group/i2rt/ARX-dynamixel/RobotLearningGello/ARX_X5/py/arx_x5_python/bimanual/api/arx_x5_src:{os.environ.get('LD_LIBRARY_PATH', '')}"
        os.environ['LD_LIBRARY_PATH'] = f"/home/group/i2rt/ARX-dynamixel/RobotLearningGello/ARX_X5/py/arx_x5_python/bimanual/api:{os.environ.get('LD_LIBRARY_PATH', '')}"
        
        # Import SingleArm from ARX
        from arx_x5_python.bimanual.script.single_arm import SingleArm
        
        # For X5, use direct CAN port mapping
        # can0 = right arm, can1 = left arm
        can_port = channel
        if channel == "can0":
            # Add delay for right arm to prevent CAN conflicts
            print(f"Adding 2 second delay for {channel} to prevent CAN initialization conflicts...")
            time.sleep(2)
        
        # Initialize X5 robot with config
        config = {
            "can_port": can_port,
            "type": 0,  # 0 for X5 robot
            "num_joints": 7,
            "dt": 0.05
        }
        print(f"Initializing X5 robot on {can_port}...")
        self.robot = SingleArm(config)
        
        # Wait a bit for initialization to complete
        time.sleep(0.5)
        
        # Try to read initial position to verify communication
        try:
            init_pos = self.robot.get_joint_positions()
            if init_pos is not None:
                print(f"X5 initialized successfully. Initial positions: {init_pos}")
            else:
                print("Warning: X5 initialized but couldn't read positions")
        except Exception as e:
            print(f"Warning: X5 initialization issue: {e}")

        # X5 has 7 joints (6 arm joints + 1 gripper)
        self._joint_names = [
            "joint1",
            "joint2",
            "joint3",
            "joint4",
            "joint5",
            "joint6",
            "gripper",
        ]
        self._joint_state = np.zeros(7)  # 7 joints
        self._joint_velocities = np.zeros(7)  # 7 joints
        self._gripper_state = 0.0

    def num_dofs(self) -> int:
        return 7  # X5 has 7 DOFs

    def get_joint_state(self) -> np.ndarray:
        # Get actual joint positions from X5 robot
        try:
            joint_pos = self.robot.get_joint_positions()
            
            # Handle different return formats
            if joint_pos is None:
                print("Warning: get_joint_positions() returned None")
                return np.zeros(7)
            
            # Convert to numpy array if needed
            if not isinstance(joint_pos, np.ndarray):
                joint_pos = np.array(joint_pos)
            
            # Debug output (commented out to reduce spam)
            # print(f"Raw joint positions from X5: {joint_pos}, shape: {joint_pos.shape}")
            
            # X5 might return 7 or 8 values depending on configuration
            if len(joint_pos) == 7:
                # Already has 7 joints
                self._joint_state = joint_pos
            elif len(joint_pos) == 6:
                # Add gripper as 7th joint
                self._joint_state = np.append(joint_pos, self._gripper_state)
            elif len(joint_pos) == 8:
                # Has extra value, take first 7
                print(f"Warning: Got 8 joints, using first 7")
                self._joint_state = joint_pos[:7]
            else:
                print(f"Warning: Unexpected joint count: {len(joint_pos)}")
                self._joint_state = np.zeros(7)
            
            return self._joint_state
        except Exception as e:
            print(f"Error getting joint state: {e}")
            return np.zeros(7)

    def command_joint_state(self, joint_state: np.ndarray) -> None:
        assert (
            len(joint_state) == self.num_dofs()
        ), f"Expected {self.num_dofs()} joint values, got {len(joint_state)}"

        # Debug: Show what we received (commented out)
        # print(f"X5 received command for {len(joint_state)} joints: {joint_state}")

        dt = 0.01
        self._joint_velocities = (joint_state - self._joint_state) / dt
        self._joint_state = joint_state

        # Command the X5 robot with all 7 joints (6 arm + 1 gripper)
        self.command_joint_pos(joint_state)

    def get_observations(self) -> Dict[str, np.ndarray]:
        ee_pos_quat = np.zeros(7)  # Placeholder for FK
        return {
            "joint_positions": self._joint_state,
            "joint_velocities": self._joint_velocities,
            "ee_pos_quat": ee_pos_quat,
            "gripper_position": np.array([self._gripper_state]),
        }

    def get_joint_pos(self):
        # Get 6 joints from X5 robot and add gripper
        joint_pos = self.robot.get_joint_positions()
        joint_pos = np.append(joint_pos, self._gripper_state)
        return joint_pos

    def command_joint_pos(self, target_pos):
        # X5 expects 6 joints, extract gripper separately
        try:
            if len(target_pos) >= 7:
                # We receive 7 joints from Dynamixel
                # First 6 are arm joints, 7th is gripper
                arm_pos = target_pos[:6]
                gripper_value = target_pos[6]
                
                # Update gripper state and send command
                # Always send gripper command for exact following
                self._gripper_state = gripper_value
                # X5 uses set_catch for gripper control
                # Map from normalized [0, 1] range to X5 gripper range
                # Based on ARX config: follower_gripper_open_rad: 5.2, follower_gripper_close_rad: 0.0
                # The X5 gripper expects radians where larger positive values = more open
                # Map [0,1] where 0=closed, 1=open to X5 range [0.0, 5.2]
                # This ensures 1.0 from leader = fully open on X5
                gripper_cmd = gripper_value * 5.2  # Maps [0,1] to [0.0, 5.2]
                try:
                    self.robot.set_catch_pos(gripper_cmd)
                    # Debug output to see what's happening (always print for now to debug)
                    print(f"  Gripper: {gripper_value:.3f} -> set_catch_pos({gripper_cmd:.3f})")
                except AttributeError as e:
                    print(f"  Gripper error: set_catch_pos method not found: {e}")
                except Exception as e:
                    print(f"  Gripper control error: {e}")
                
                # Debug output (reduce spam by commenting out)
                # print(f"X5 command - Input (7 joints): {target_pos}")
                # print(f"  Arm joints to X5 (6): {arm_pos}")
                
            else:
                arm_pos = target_pos
            
            # Check for reasonable values to prevent torque limit errors
            # X5 joints typically have limits around +/- 3.14 radians
            MAX_JOINT_POS = 3.14
            MIN_JOINT_POS = -3.14
            
            # Clip positions to safe range
            arm_pos_before_clip = arm_pos.copy()
            arm_pos = np.clip(arm_pos, MIN_JOINT_POS, MAX_JOINT_POS)
            
            # Check if clipping changed anything (commented to reduce spam)
            # if not np.array_equal(arm_pos_before_clip, arm_pos):
            #     print(f"WARNING: Clipping changed values!")
            #     print(f"  Before: {arm_pos_before_clip}")
            #     print(f"  After: {arm_pos}")
            
            # Command the X5 robot (only arm joints)
            self.robot.set_joint_positions(arm_pos)
            
        except RuntimeError as e:
            if "关节力矩超限" in str(e) or "torque" in str(e).lower():
                print(f"Warning: Joint torque limit exceeded. Positions: {arm_pos}")
                # Try to stop motion by commanding current position
                try:
                    current = self.robot.get_joint_positions()
                    if current is not None and len(current) >= 6:
                        self.robot.set_joint_positions(current[:6])
                except:
                    pass
            else:
                print(f"Error commanding joint positions: {e}")
        except Exception as e:
            print(f"Error commanding joint positions: {e}")


def main():
    robot = X5Robot()
    print(robot.get_observations())


if __name__ == "__main__":
    main()