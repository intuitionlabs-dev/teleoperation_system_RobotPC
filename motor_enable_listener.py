#!/usr/bin/env python3
"""
Motor Enable Listener - Robot PC Side
====================================
Listens for enable commands from teleoperator and enables ALL 7 motors per arm:
- 6 arm joint motors (1-6)
- 1 gripper motor (7)

Run this on the robot PC alongside host_broadcast.py.

Usage:
    python motor_enable_listener.py --left_arm_port left_piper --right_arm_port right_piper
"""

import argparse
import json
import time
import zmq
import threading
import logging
from typing import Optional, Dict
from dataclasses import dataclass

# Import piper SDK
from piper_sdk import C_PiperInterface_V2

@dataclass
class MotorEnableConfig:
    left_arm_port: str = "left_piper"
    right_arm_port: str = "right_piper" 
    enable_port: int = 5559
    max_enable_attempts: int = 100
    enable_timeout_sec: float = 5.0
    default_enable_mode: str = "partial"  # "partial" or "full"
    status_update_interval: float = 1.0  # seconds between status updates

class ArmController:
    """Controller for a single Piper arm"""
    
    def __init__(self, can_port: str, arm_name: str):
        self.can_port = can_port
        self.arm_name = arm_name
        self.piper: Optional[C_PiperInterface_V2] = None
        self.connected = False
        self.lock = threading.Lock()
        
    def connect(self) -> bool:
        """Connect to the arm"""
        try:
            print(f"🔌 Connecting to {self.arm_name} arm on {self.can_port}...")
            self.piper = C_PiperInterface_V2(self.can_port)
            self.piper.ConnectPort()
            self.connected = True
            print(f"✅ {self.arm_name} arm connected!")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to {self.arm_name} arm: {e}")
            return False
    
    def get_enable_status(self) -> tuple[int, str]:
        """Get current enable status of the arm"""
        if not self.connected or not self.piper:
            return 0, "disconnected"
            
        try:
            enable_status = self.piper.GetArmEnableStatus()
            enabled_count = sum(enable_status) if enable_status else 0
            
            status = self.piper.GetArmStatus()
            status_str = f"ctrl:{status.arm_status.ctrl_mode} arm:{status.arm_status.arm_status}"
            
            return enabled_count, status_str
        except Exception as e:
            return 0, f"error: {e}"
    
    def get_detailed_motor_status(self) -> list:
        """Get detailed status of each motor (arm joints 1-6) including ALL diagnostic states"""
        if not self.connected or not self.piper:
            return []
            
        try:
            motor_info = self.piper.GetArmLowSpdInfoMsgs()
            motor_statuses = []
            
            for i in range(1, 7):  # Motors 1-6 (arm joints)
                motor_attr = getattr(motor_info, f'motor_{i}')
                foc = motor_attr.foc_status
                
                # Get ALL available status flags
                status = {
                    'motor_num': i,
                    'enabled': foc.driver_enable_status,
                    'has_error': foc.driver_error_status,
                    'collision': foc.collision_status,
                    'stall': foc.stall_status,
                    'overheating': foc.driver_overheating or foc.motor_overheating,
                    'overcurrent': foc.driver_overcurrent,
                    'voltage_low': foc.voltage_too_low,
                    
                    # Additional diagnostic flags that might explain zombie states
                    'driver_overheating': foc.driver_overheating,
                    'motor_overheating': foc.motor_overheating,
                    'voltage_too_high': getattr(foc, 'voltage_too_high', False),
                    'driver_fault': getattr(foc, 'driver_fault', False),
                    'motor_fault': getattr(foc, 'motor_fault', False),
                    'communication_error': getattr(foc, 'communication_error', False),
                    'watchdog_triggered': getattr(foc, 'watchdog_triggered', False),
                    'emergency_stop': getattr(foc, 'emergency_stop', False),
                    
                    # Raw status for debugging
                    'raw_driver_status': getattr(foc, 'driver_status', 'unknown'),
                    'raw_motor_status': getattr(foc, 'motor_status', 'unknown'),
                }
                motor_statuses.append(status)
                
            return motor_statuses
        except Exception as e:
            print(f"❌ Failed to get detailed motor status: {e}")
            return []
    
    def get_gripper_status(self) -> dict:
        """Get gripper status (motor 7)"""
        if not self.connected or not self.piper:
            return {}
            
        try:
            gripper_info = self.piper.GetArmGripperMsgs()
            gripper = gripper_info.gripper_state
            
            status = {
                'motor_num': 7,  # Gripper is motor 7
                'enabled': gripper.foc_status.driver_enable_status,
                'has_error': gripper.foc_status.driver_error_status,
                'collision': False,  # Gripper doesn't have collision detection
                'stall': False,     # Gripper doesn't have stall detection  
                'overheating': gripper.foc_status.driver_overheating or gripper.foc_status.motor_overheating,
                'overcurrent': gripper.foc_status.driver_overcurrent,
                'voltage_low': gripper.foc_status.voltage_too_low
            }
            
            return status
        except Exception as e:
            print(f"❌ Failed to get gripper status: {e}")
            return {}
    
    def get_all_motor_status(self) -> list:
        """Get status of ALL motors (arm joints 1-6 + gripper 7)"""
        arm_statuses = self.get_detailed_motor_status()
        gripper_status = self.get_gripper_status()
        
        if gripper_status:  # Only add if gripper status was retrieved successfully
            return arm_statuses + [gripper_status]
        else:
            return arm_statuses
    
    def needs_enable(self, motor_status: dict) -> bool:
        """Check if a motor needs to be enabled/reset based on its status"""
        # Obviously disabled motors need enabling
        if not motor_status['enabled']:
            return True
        
        # Standard error conditions
        if (motor_status['has_error'] or 
            motor_status['collision'] or 
            motor_status['stall']):
            return True
        
        # Additional problematic states that could cause zombie behavior
        if (motor_status.get('driver_overheating', False) or
            motor_status.get('motor_overheating', False) or
            motor_status.get('overcurrent', False) or
            motor_status.get('voltage_low', False) or
            motor_status.get('voltage_too_high', False) or
            motor_status.get('driver_fault', False) or
            motor_status.get('motor_fault', False) or
            motor_status.get('communication_error', False) or
            motor_status.get('watchdog_triggered', False) or
            motor_status.get('emergency_stop', False)):
            return True
            
        return False
    
    def enable_gripper(self) -> bool:
        """Enable gripper (motor 7)"""
        if not self.connected or not self.piper:
            return False
            
        try:
            print(f"   🔋 Enabling {self.arm_name} gripper...")
            # Enable gripper and clear errors
            self.piper.GripperCtrl(0, 1000, 0x03, 0)  # Enable and clear errors
            time.sleep(0.5)
            
            # Verify enabled
            gripper_status = self.get_gripper_status()
            if gripper_status and gripper_status['enabled']:
                print(f"   ✅ {self.arm_name} gripper enabled successfully")
                return True
            else:
                print(f"   ❌ {self.arm_name} gripper failed to enable")
                return False
        except Exception as e:
            print(f"   ❌ Error enabling {self.arm_name} gripper: {e}")
            return False
    
    def disable_gripper(self) -> bool:
        """Disable gripper (motor 7)"""
        if not self.connected or not self.piper:
            return False
            
        try:
            print(f"   🔄 Disabling {self.arm_name} gripper...")
            # Disable gripper
            self.piper.GripperCtrl(0, 0, 0x00, 0)  # Pure disable
            time.sleep(0.5)
            
            # Verify disabled
            gripper_status = self.get_gripper_status()
            if gripper_status and not gripper_status['enabled']:
                print(f"   ✅ {self.arm_name} gripper disabled successfully")
                return True
            else:
                print(f"   ❌ {self.arm_name} gripper failed to disable")
                return False
        except Exception as e:
            print(f"   ❌ Error disabling {self.arm_name} gripper: {e}")
            return False

    def enable_motors(self, max_attempts: int = 100, partial_enable: bool = False) -> bool:
        """Enable motors on this arm
        
        Args:
            max_attempts: Maximum attempts for enabling
            partial_enable: If True, only enable motors that need it. If False, enable all motors.
        """
        if not self.connected or not self.piper:
            print(f"❌ {self.arm_name} arm not connected!")
            return False
            
        with self.lock:
            try:
                if partial_enable:
                    return self._partial_enable_motors(max_attempts)
                else:
                    return self._full_enable_motors(max_attempts)
                    
            except Exception as e:
                print(f"❌ {self.arm_name} enable failed: {e}")
                return False
    
    def _partial_enable_motors(self, max_attempts: int = 100) -> bool:
        """Selectively enable only motors that need it (INCLUDING GRIPPER)"""
        print(f"🔋 Partial enable for {self.arm_name} arm (smart mode - ALL 7 motors)...")
        
        # Get detailed status of ALL motors (arm joints 1-6 + gripper 7)
        all_motor_statuses = self.get_all_motor_status()
        if not all_motor_statuses:
            print(f"❌ Could not get motor status for {self.arm_name}")
            return False
        
        # Identify which motors need enabling
        arm_motors_to_enable = []
        gripper_needs_enable = False
        gripper_reason = ""
        
        print(f"   🔍 Analyzing motor statuses...")
        
        for status in all_motor_statuses:
            motor_num = status['motor_num']
            needs_fix = self.needs_enable(status)
            
            print(f"     Motor {motor_num}: enabled={status['enabled']}, needs_fix={needs_fix}")
            
            if needs_fix:
                reason = []
                if not status['enabled']:
                    reason.append("disabled")
                if status['has_error']:
                    reason.append("error")
                if status['collision']:
                    reason.append("collision")
                if status['stall']:
                    reason.append("stall")
                
                # Add zombie-state reasons
                if status.get('driver_overheating'):
                    reason.append("driver-hot")
                if status.get('motor_overheating'):
                    reason.append("motor-hot")
                if status.get('overcurrent'):
                    reason.append("overcurrent")
                if status.get('voltage_low'):
                    reason.append("low-volt")
                if status.get('voltage_too_high'):
                    reason.append("high-volt")
                if status.get('driver_fault'):
                    reason.append("driver-fault")
                if status.get('motor_fault'):
                    reason.append("motor-fault")
                if status.get('communication_error'):
                    reason.append("comm-error")
                if status.get('watchdog_triggered'):
                    reason.append("watchdog")
                if status.get('emergency_stop'):
                    reason.append("e-stop")
                
                reason_str = ", ".join(reason) if reason else "unknown-issue"
                
                if status['motor_num'] == 7:  # Gripper
                    gripper_needs_enable = True
                    gripper_reason = reason_str
                    print(f"     ➜ Gripper marked for enable: {reason_str}")
                else:  # Arm motors 1-6
                    arm_motors_to_enable.append((status['motor_num'], reason_str))
                    print(f"     ➜ Motor {motor_num} marked for enable: {reason_str}")
        
        if not arm_motors_to_enable and not gripper_needs_enable:
            print(f"✅ {self.arm_name}: All 7 motors are already working properly!")
            return True
        
        # Check for collision/thermal scenarios that require full reset
        collision_detected = any('collision' in reason for _, reason in arm_motors_to_enable)
        thermal_detected = any('motor-hot' in reason for _, reason in arm_motors_to_enable)
        
        if collision_detected or thermal_detected:
            print(f"🚨 {self.arm_name}: Collision/thermal issues detected - switching to full reset mode")
            print(f"   Collision: {collision_detected}, Thermal: {thermal_detected}")
            print(f"   Reason: Smart enable can cause cascading failures with thermal/collision issues")
            return self._full_enable_motors(max_attempts)
        
        # Display what needs enabling
        motors_needing_enable = [f'M{num} ({reason})' for num, reason in arm_motors_to_enable]
        if gripper_needs_enable:
            motors_needing_enable.append(f'Gripper ({gripper_reason})')
        print(f"   Motors needing enable: {motors_needing_enable}")
        
        # Aggressive error clearing for arm motors that need it
        error_arm_motors = [num for num, _ in arm_motors_to_enable]
        if error_arm_motors:
            print(f"   🧹 Aggressive error clearing for arm motors: {error_arm_motors}")
            
            # Step 1: Clear emergency stops
            print(f"     Step 1: Clearing emergency stops...")
            self.piper.EmergencyStop(0x02)  # Resume from emergency stop
            time.sleep(0.5)
            
            # Step 2: Individual motor error clearing
            print(f"     Step 2: Clearing individual motor errors...")
            for motor_num in error_arm_motors:
                print(f"       Clearing errors for motor {motor_num}...")
                self.piper.JointConfig(joint_num=motor_num, clear_err=0xAE)
                time.sleep(0.2)  # More time for clearing
            
            # Step 3: Global error clearing
            print(f"     Step 3: Global error clearing...")
            self.piper.JointConfig(joint_num=7, clear_err=0xAE)  # Clear all joint errors
            time.sleep(0.5)
            
            # Step 4: Additional reset attempts for zombie states
            print(f"     Step 4: Additional zombie state clearing...")
            try:
                # Try to disable and re-enable the problematic motors to clear zombie states
                for motor_num in error_arm_motors:
                    print(f"       Zombie reset for motor {motor_num}...")
                    self.piper.DisableArm(motor_num, 0x01)  # Disable first
                    time.sleep(0.1)
                    self.piper.JointConfig(joint_num=motor_num, clear_err=0xAE)  # Clear errors
                    time.sleep(0.1)
            except Exception as e:
                print(f"       ⚠️ Zombie reset failed: {e}")
        
        # Enable each arm motor individually
        success_count = 0
        total_to_enable = len(arm_motors_to_enable) + (1 if gripper_needs_enable else 0)
        
        for motor_num, reason in arm_motors_to_enable:
            print(f"   🔋 Enabling motor {motor_num} ({reason})...")
            attempts = 0
            
            # Check status before enabling
            pre_status = self.get_detailed_motor_status()
            if pre_status and motor_num <= len(pre_status):
                pre_motor = pre_status[motor_num-1]
                print(f"     Before: enabled={pre_motor['enabled']}, error={pre_motor['has_error']}, collision={pre_motor['collision']}, stall={pre_motor['stall']}")
            
            while attempts < max_attempts:
                print(f"     Attempt {attempts+1}: Sending EnableArm({motor_num}, 0x02)...")
                self.piper.EnableArm(motor_num, 0x02)  # Enable individual motor
                time.sleep(0.1)  # Increased delay to prevent CAN bus overload
                
                # Check if this motor is now enabled
                current_status = self.get_detailed_motor_status()
                if current_status and motor_num <= len(current_status):
                    current_motor = current_status[motor_num-1]
                    enabled = current_motor['enabled']
                    has_issues = self.needs_enable(current_motor)
                    
                    print(f"     After attempt {attempts+1}: enabled={enabled}, still_has_issues={has_issues}")
                    
                    if enabled and not has_issues:
                        print(f"   ✅ Motor {motor_num} enabled successfully!")
                        success_count += 1
                        
                        # Power management delay - let voltage stabilize before next motor
                        current_index = next(i for i, (num, _) in enumerate(arm_motors_to_enable) if num == motor_num)
                        if current_index < len(arm_motors_to_enable) - 1:  # Not the last motor
                            print(f"     💡 Power stabilization delay...")
                            time.sleep(0.5)
                        break
                    elif enabled and has_issues:
                        print(f"     ⚠️ Motor {motor_num} enabled but still has issues (zombie state)")
                    else:
                        print(f"     ❌ Motor {motor_num} still disabled")
                else:
                    print(f"     ❌ Could not read status for motor {motor_num}")
                    
                attempts += 1
                if attempts % 10 == 0:
                    print(f"   Motor {motor_num}: Attempt {attempts}/{max_attempts}...")
                    
                # Add longer delay after failed attempts to prevent bus overload
                if attempts % 5 == 0:
                    time.sleep(0.2)
            
            if attempts >= max_attempts:
                print(f"   ❌ Motor {motor_num} failed to enable after {max_attempts} attempts")
                print(f"   🚨 Switching to full reset mode for remaining motors...")
                return self._full_enable_motors(max_attempts)
                
                # Show final status for debugging
                final_status = self.get_detailed_motor_status()
                if final_status and motor_num <= len(final_status):
                    final_motor = final_status[motor_num-1]
                    print(f"     Final state: {final_motor}")
        
        # Enable gripper if needed
        if gripper_needs_enable:
            print(f"   Enabling gripper ({gripper_reason})...")
            if self.enable_gripper():
                success_count += 1
        
        # Check final status (arm motors only for backward compatibility)
        enabled_count, status_str = self.get_enable_status()
        
        # Also check gripper status
        gripper_status = self.get_gripper_status()
        gripper_enabled = gripper_status.get('enabled', False) if gripper_status else False
        
        print(f"   📊 {self.arm_name}: {enabled_count}/6 arm motors + {'1' if gripper_enabled else '0'}/1 gripper enabled")
        
        if success_count == total_to_enable:
            print(f"🎉 {self.arm_name} arm: All problem motors enabled successfully! (ALL 7 motors)")
            
            # Restore MIT mode for teleoperation
            print(f"   🎯 Restoring MIT mode for {self.arm_name} arm...")
            try:
                # Set MIT mode: ctrl_mode=0x01 (CAN control), move_mode=0x01 (MOVE J), speed=0, is_mit_mode=0xAD
                self.piper.MotionCtrl_2(0x01, 0x01, 0, 0xAD)
                print(f"   ✅ MIT mode restored for {self.arm_name} arm - ready for teleoperation!")
            except Exception as e:
                print(f"   ⚠️ Could not restore MIT mode: {e}")
                print(f"   ℹ️ You may need to restart the teleoperation system")
            
            return True
        else:
            print(f"⚠️  {self.arm_name} arm: {success_count}/{total_to_enable} problem motors enabled")
            return False
    
    def _full_enable_motors(self, max_attempts: int = 100) -> bool:
        """Enable all motors (original behavior)"""
        print(f"🔋 Full enable for {self.arm_name} arm (reset all motors)...")
        
        # Step 1: Clear emergency stops and errors
        print(f"   Clearing emergency stops for {self.arm_name}...")
        self.piper.EmergencyStop(0x02)  # Resume from emergency stop
        time.sleep(0.5)
        
        print(f"   Clearing joint errors for {self.arm_name}...")
        self.piper.JointConfig(joint_num=7, clear_err=0xAE)  # Clear all joint errors
        time.sleep(0.5)
        
        # Step 2: Enable using SDK sequence (same as CAN debug scripts)
        print(f"   Attempting to enable {self.arm_name} arm (may take several attempts)...")
        attempts = 0
        
        while not self.piper.EnablePiper() and attempts < max_attempts:
            time.sleep(0.01)  # Same timing as SDK demo
            attempts += 1
            if attempts % 25 == 0:  # Progress indicator
                print(f"   {self.arm_name}: Attempt {attempts}/{max_attempts}...")
        
        if attempts >= max_attempts:
            print(f"   ❌ {self.arm_name}: Failed to enable after maximum attempts")
            print(f"   Trying alternative enable method for {self.arm_name}...")
            
            # Alternative: Try EnableArm directly
            self.piper.EnableArm(0xFF, 0x02)  # 0xFF means all motors, 0x02 means enable
            time.sleep(1)
            
        else:
            print(f"   ✅ {self.arm_name}: Enabled successfully after {attempts} attempts!")
        
        # Step 3: Reset gripper to zero position
        print(f"   Resetting {self.arm_name} gripper...")
        self.piper.GripperCtrl(0, 1000, 0x03, 0)      # Enable gripper and clear errors
        time.sleep(0.5)
        self.piper.GripperCtrl(0, 1000, 0x01, 0)      # Move to position 0 (enabled)
        time.sleep(1.5)
        self.piper.GripperCtrl(0, 1000, 0x01, 0xAE)   # Set current position as zero (enabled)
        time.sleep(0.5)
        
        # Check final status (arm motors + gripper)
        enabled_count, status_str = self.get_enable_status()
        
        # Also check gripper status
        gripper_status = self.get_gripper_status()
        gripper_enabled = gripper_status.get('enabled', False) if gripper_status else False
        
        print(f"   📊 {self.arm_name}: {enabled_count}/6 arm motors + {'1' if gripper_enabled else '0'}/1 gripper enabled")
        
        if enabled_count == 6 and gripper_enabled:
            print(f"🎉 {self.arm_name} arm: All 7 motors enabled successfully!")
            
            # Step 4: Restore MIT mode for teleoperation
            print(f"   🎯 Restoring MIT mode for {self.arm_name} arm...")
            try:
                # Set MIT mode: ctrl_mode=0x01 (CAN control), move_mode=0x01 (MOVE J), speed=0, is_mit_mode=0xAD
                self.piper.MotionCtrl_2(0x01, 0x01, 0, 0xAD)
                print(f"   ✅ MIT mode restored for {self.arm_name} arm - ready for teleoperation!")
            except Exception as e:
                print(f"   ⚠️ Could not restore MIT mode: {e}")
                print(f"   ℹ️ You may need to restart the teleoperation system")
            
            return True
        else:
            total_enabled = enabled_count + (1 if gripper_enabled else 0)
            print(f"⚠️  {self.arm_name} arm: Only {total_enabled}/7 motors enabled")
            return False

class MotorEnableListener:
    """Main listener for enable commands"""
    
    def __init__(self, config: MotorEnableConfig):
        self.config = config
        self.context = zmq.Context()
        self.socket = None
        self.running = False
        
        # Initialize arm controllers
        self.arms: Dict[str, ArmController] = {
            "left": ArmController(config.left_arm_port, "left"),
            "right": ArmController(config.right_arm_port, "right")
        }
        
    def connect_arms(self) -> bool:
        """Connect to both arms"""
        success = True
        for arm_name, arm_controller in self.arms.items():
            if not arm_controller.connect():
                success = False
        return success
    
    def setup_zmq(self) -> bool:
        """Setup ZMQ subscriber socket"""
        try:
            self.socket = self.context.socket(zmq.SUB)
            self.socket.bind(f"tcp://*:{self.config.enable_port}")
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages
            print(f"🎧 Listening for enable commands on port {self.config.enable_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to setup ZMQ: {e}")
            return False
    
    def show_status(self):
        """Show current status of both arms (ALL 7 motors each) with detailed breakdown"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n📊 DETAILED ARM STATUS ({timestamp}):")
        print("=" * 80)
        
        for arm_name, arm_controller in self.arms.items():
            enabled_count, status_str = arm_controller.get_enable_status()
            
            # Get detailed motor status
            motor_statuses = arm_controller.get_detailed_motor_status()
            gripper_status = arm_controller.get_gripper_status()
            
            print(f"\n🔧 {arm_name.upper()} ARM ({status_str}):")
            
            # Show individual arm motor statuses
            disabled_motors = []
            error_motors = []
            collision_motors = []
            stall_motors = []
            zombie_motors = []  # Motors that are "enabled" but have issues
            
            for status in motor_statuses:
                motor_num = status['motor_num']
                enabled = status['enabled']
                has_error = status['has_error']
                collision = status['collision']
                stall = status['stall']
                
                status_parts = []
                if enabled:
                    status_parts.append("✅ enabled")
                else:
                    status_parts.append("❌ disabled")
                    disabled_motors.append(motor_num)
                
                # Check for error conditions
                issues = []
                if has_error:
                    issues.append("⚠️ error")
                    error_motors.append(motor_num)
                if collision:
                    issues.append("💥 collision")
                    collision_motors.append(motor_num)
                if stall:
                    issues.append("🔒 stall")
                    stall_motors.append(motor_num)
                
                # Check for additional diagnostic issues that could explain zombie behavior
                if status.get('driver_overheating'):
                    issues.append("🌡️ driver-hot")
                if status.get('motor_overheating'):
                    issues.append("🔥 motor-hot")
                if status.get('overcurrent'):
                    issues.append("⚡ overcurrent")
                if status.get('voltage_low'):
                    issues.append("🔋 low-volt")
                if status.get('voltage_too_high'):
                    issues.append("⚡ high-volt")
                if status.get('driver_fault'):
                    issues.append("🔧 driver-fault")
                if status.get('motor_fault'):
                    issues.append("⚙️ motor-fault")
                if status.get('communication_error'):
                    issues.append("📡 comm-error")
                if status.get('watchdog_triggered'):
                    issues.append("🐕 watchdog")
                if status.get('emergency_stop'):
                    issues.append("🛑 e-stop")
                
                # Detect zombie state: enabled but has issues
                if enabled and issues:
                    zombie_motors.append((motor_num, issues))
                    status_parts.append("🧟 ZOMBIE")
                
                if issues:
                    status_parts.extend(issues)
                
                status_str = ", ".join(status_parts)
                print(f"     Motor {motor_num}: {status_str}")
                
                # Show raw status for debugging if there are issues
                if issues or not enabled:
                    raw_driver = status.get('raw_driver_status', 'unknown')
                    raw_motor = status.get('raw_motor_status', 'unknown')
                    print(f"       🔍 Debug: driver={raw_driver}, motor={raw_motor}")
            
            # Show gripper status
            if gripper_status:
                gripper_enabled = gripper_status.get('enabled', False)
                gripper_error = gripper_status.get('has_error', False)
                
                gripper_parts = []
                if gripper_enabled:
                    gripper_parts.append("✅ enabled")
                else:
                    gripper_parts.append("❌ disabled")
                if gripper_error:
                    gripper_parts.append("⚠️ error")
                
                gripper_str = ", ".join(gripper_parts)
                print(f"     Gripper: {gripper_str}")
            else:
                print(f"     Gripper: ❌ status unavailable")
            
            # Summary with problematic motors highlighted
            gripper_enabled = gripper_status.get('enabled', False) if gripper_status else False
            total_enabled = enabled_count + (1 if gripper_enabled else 0)
            
            summary_parts = [f"{enabled_count}/6 arm motors"]
            if gripper_enabled:
                summary_parts.append("1/1 gripper")
            else:
                summary_parts.append("0/1 gripper")
            
            print(f"     📊 Summary: {' + '.join(summary_parts)} = {total_enabled}/7 total")
            
            # Highlight problems
            if disabled_motors:
                print(f"     🚫 DISABLED: Motors {disabled_motors}")
            if error_motors:
                print(f"     ⚠️  ERRORS: Motors {error_motors}")
            if collision_motors:
                print(f"     💥 COLLISION: Motors {collision_motors}")
            if stall_motors:
                print(f"     🔒 STALLED: Motors {stall_motors}")
            if zombie_motors:
                zombie_list = [f"M{num}({','.join(issues)})" for num, issues in zombie_motors]
                print(f"     🧟 ZOMBIE MOTORS: {zombie_list}")
                print(f"     ⚠️  ^ These motors are 'enabled' but have issues - likely cause of lag!")
            
            if not disabled_motors and not error_motors and not collision_motors and not stall_motors and not zombie_motors and gripper_enabled:
                print(f"     ✅ ALL MOTORS HEALTHY")
            elif zombie_motors:
                print(f"     🚨 ZOMBIE STATE DETECTED - Motors enabled but problematic!")
        
        print("=" * 80)
    
    def process_enable_command(self, command: dict):
        """Process received enable command"""
        try:
            if command.get("type") != "enable":
                return
                
            arm = command.get("arm", "").lower()
            timestamp = command.get("timestamp", 0)
            enable_mode = command.get("enable_mode", self.config.default_enable_mode).lower()
            
            if enable_mode not in ["partial", "full"]:
                enable_mode = self.config.default_enable_mode
                
            partial_enable = (enable_mode == "partial")
            mode_desc = "smart mode (only disabled motors)" if partial_enable else "full reset mode (all motors)"
            
            print(f"\n📨 Received enable command: {arm} arm ({mode_desc}) (ts: {timestamp:.3f})")
            
            if arm in self.arms:
                success = self.arms[arm].enable_motors(
                    max_attempts=self.config.max_enable_attempts,
                    partial_enable=partial_enable
                )
                if success:
                    print(f"✅ {arm.upper()} arm enable command completed successfully!")
                else:
                    print(f"❌ {arm.upper()} arm enable command failed!")
            else:
                print(f"❌ Unknown arm: {arm}")
                
        except Exception as e:
            print(f"❌ Error processing enable command: {e}")
    
    def run(self):
        """Main run loop"""
        self.running = True
        print(f"\n🎮 MOTOR ENABLE LISTENER ACTIVE")
        print("=" * 60)
        print(f"Default enable mode: {self.config.default_enable_mode.upper()}")
        print("  'partial' = Smart mode (only enables problem motors - ALL 7 motors)")
        print("  'full' = Full reset (all motors, may cause arm to fall - ALL 7 motors)")
        print("")
        print("Waiting for enable commands from teleoperator...")
        print("Commands: {'type': 'enable', 'arm': 'left'|'right', 'enable_mode': 'partial'|'full'}")
        print("Each arm has 7 motors: 6 arm joints + 1 gripper")
        print(f"📱 Status updates every {self.config.status_update_interval}s for real-time monitoring")
        print("=" * 60)
        
        # Show initial status
        self.show_status()
        
        last_status_update = time.time()
        status_update_interval = self.config.status_update_interval
        
        try:
            while self.running:
                try:
                    # Check for messages with timeout
                    if self.socket.poll(1000):  # 1 second timeout
                        message = self.socket.recv_string(zmq.NOBLOCK)
                        command = json.loads(message)
                        self.process_enable_command(command)
                        
                        # Show status after command
                        self.show_status()
                        last_status_update = time.time()  # Reset timer after command
                    else:
                        # No message received, check if we should update status
                        current_time = time.time()
                        if current_time - last_status_update >= status_update_interval:
                            self.show_status()
                            last_status_update = current_time
                        
                except zmq.Again:
                    # This shouldn't happen since we use poll(), but just in case
                    pass
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON received: {e}")
                except Exception as e:
                    print(f"❌ Error in main loop: {e}")
                    
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        finally:
            self.running = False
    
    def cleanup(self):
        """Cleanup resources"""
        if self.socket:
            self.socket.close()
        self.context.term()

def main():
    parser = argparse.ArgumentParser(description="Motor Enable Listener for Robot PC (ALL 7 motors per arm)")
    parser.add_argument("--left_arm_port", default="left_piper",
                        help="CAN port for left arm")
    parser.add_argument("--right_arm_port", default="right_piper", 
                        help="CAN port for right arm")
    parser.add_argument("--enable_port", type=int, default=5559,
                        help="ZMQ port for enable commands")
    parser.add_argument("--max_enable_attempts", type=int, default=100,
                        help="Maximum attempts for enabling motors")
    parser.add_argument("--default_enable_mode", default="partial", 
                        choices=["partial", "full"],
                        help="Default enable mode: 'partial' (smart, only disabled motors - ALL 7 motors) or 'full' (reset all motors - ALL 7 motors)")
    parser.add_argument("--status_update_interval", type=float, default=1.0,
                        help="Seconds between real-time status updates (default: 1.0)")
    
    args = parser.parse_args()
    
    config = MotorEnableConfig(
        left_arm_port=args.left_arm_port,
        right_arm_port=args.right_arm_port,
        enable_port=args.enable_port,
        max_enable_attempts=args.max_enable_attempts,
        default_enable_mode=args.default_enable_mode,
        status_update_interval=args.status_update_interval
    )
    
    listener = MotorEnableListener(config)
    
    try:
        # Connect to arms
        if not listener.connect_arms():
            print("❌ Failed to connect to one or more arms!")
            return 1
            
        # Setup ZMQ
        if not listener.setup_zmq():
            print("❌ Failed to setup ZMQ listener!")
            return 1
            
        # Run listener
        listener.run()
        
    finally:
        listener.cleanup()
    
    return 0

if __name__ == "__main__":
    exit(main())