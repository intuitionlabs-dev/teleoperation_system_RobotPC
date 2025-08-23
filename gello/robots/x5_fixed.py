from typing import Dict
import sys
import os

import numpy as np

from gello.robots.robot import Robot


class X5RobotFixed(Robot):
    """Fixed X5 robot that handles joint limits properly."""

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
            initial_pos = self.robot.get_joint_positions()
            print(f"X5 robot initialized. Initial position: {initial_pos}")
        except Exception as e:
            print(f"Warning: Could not read initial position: {e}")

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
        
        # IMPORTANT: Define joint offsets to handle the limits
        # Joints 1 and 2 have min=0, so we add offsets to shift negative values to positive range
        self._joint_offsets = np.array([
            0.0,   # Joint 0: no offset needed
            1.5,   # Joint 1: add 1.5 rad to shift range from [-1.5, 2.15] to [0, 3.65]
            1.5,   # Joint 2: add 1.5 rad to shift range from [-1.5, 1.64] to [0, 3.14]  
            0.0,   # Joint 3: no offset needed
            0.0,   # Joint 4: no offset needed
            0.0,   # Joint 5: no offset needed
            0.0,   # Gripper: no offset needed
        ])

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
            
            # REMOVE offsets when reading (so external sees original range)
            self._joint_state[:6] -= self._joint_offsets[:6]
            
            return self._joint_state
        except Exception as e:
            print(f"Error getting joint state: {e}")
            return np.zeros(7)

    def command_joint_state(self, joint_state: np.ndarray) -> None:
        assert (
            len(joint_state) == self.num_dofs()
        ), f"Expected {self.num_dofs()} joint values, got {len(joint_state)}"

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
        # REMOVE offsets when reading
        joint_pos[:6] -= self._joint_offsets[:6]
        return joint_pos

    def command_joint_pos(self, target_pos):
        # X5 expects 6 joints, extract gripper separately
        try:
            if len(target_pos) >= 7:
                # We receive 7 joints from Dynamixel
                # First 6 are arm joints, 7th is gripper
                arm_pos = target_pos[:6].copy()
                self._gripper_state = target_pos[6]
                
                # ADD offsets before sending to robot (to shift to valid range)
                arm_pos_with_offset = arm_pos + self._joint_offsets[:6]
                
                # Debug to understand the transformation
                print(f"X5 Fixed - Command transformation:")
                print(f"  Input joints: {target_pos}")
                print(f"  Joint 1: {arm_pos[1]:.4f} -> {arm_pos_with_offset[1]:.4f} (offset +{self._joint_offsets[1]})")
                print(f"  Joint 2: {arm_pos[2]:.4f} -> {arm_pos_with_offset[2]:.4f} (offset +{self._joint_offsets[2]})")
                
            else:
                arm_pos = target_pos
                arm_pos_with_offset = arm_pos + self._joint_offsets[:len(arm_pos)]
            
            # Check for reasonable values to prevent torque limit errors
            # X5 joints typically have limits around +/- 3.14 radians
            # But joints 1 and 2 have [0, 3.65] and [0, 3.14] respectively
            joint_limits = np.array([
                [-3.14, 3.14],  # Joint 0
                [0, 3.65],      # Joint 1 - cannot go negative!
                [0, 3.14],      # Joint 2 - cannot go negative!
                [-1.57, 1.57],  # Joint 3
                [-1.57, 1.57],  # Joint 4
                [-2.09, 2.09],  # Joint 5
            ])
            
            # Clip positions to safe range
            arm_pos_before_clip = arm_pos_with_offset.copy()
            for i in range(6):
                arm_pos_with_offset[i] = np.clip(arm_pos_with_offset[i], 
                                                  joint_limits[i][0], 
                                                  joint_limits[i][1])
            
            # Check if clipping changed anything
            if not np.array_equal(arm_pos_before_clip, arm_pos_with_offset):
                print(f"WARNING: Clipping changed values!")
                for i in range(6):
                    if arm_pos_before_clip[i] != arm_pos_with_offset[i]:
                        print(f"  Joint {i}: {arm_pos_before_clip[i]:.4f} -> {arm_pos_with_offset[i]:.4f}")
            
            # Command the X5 robot (only arm joints, gripper control TBD)
            self.robot.set_joint_positions(arm_pos_with_offset)
            
        except RuntimeError as e:
            if "关节力矩超限" in str(e) or "torque" in str(e).lower():
                print(f"Warning: Joint torque limit exceeded. Positions: {arm_pos_with_offset}")
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
    robot = X5RobotFixed()
    print(robot.get_observations())


if __name__ == "__main__":
    main()