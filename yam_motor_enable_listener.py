#!/usr/bin/env python
"""
YAM Motor Enable Listener - Monitors and enables YAM robot motors remotely.
Receives enable commands via ZMQ and manages motor states through CAN interface.
"""

import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import zmq

# Add i2rt to path
sys.path.append(str(Path(__file__).parent.parent / "i2rt"))

from i2rt.motor_drivers.dm_driver import (
    DMChainCanInterface,
    MotorErrorCode,
    MotorInfo,
    ReceiveMode,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class YAMMotorEnableConfig:
    """Configuration for YAM motor enable listener."""
    # CAN configuration
    left_can_channel: str = "can0"
    right_can_channel: str = "can1"
    
    # Network configuration
    listen_port: int = 5569  # YAM uses 5569 for motor enable
    
    # Motor configuration
    num_motors_per_arm: int = 7  # 6 joints + 1 gripper
    
    # Enable behavior
    default_enable_mode: str = "partial"  # "partial" or "full"


class YAMMotorEnableListener:
    """Listens for motor enable commands and manages YAM motor states."""
    
    def __init__(self, config: YAMMotorEnableConfig):
        self.config = config
        self.left_motor_chain = None
        self.right_motor_chain = None
        self._is_connected = False
        
        # Track motor states
        self.left_motor_states = {}
        self.right_motor_states = {}
        
        # ZMQ setup
        self.zmq_context = None
        self.zmq_socket = None
    
    def _create_motor_chain(self, channel: str, arm_name: str) -> Optional[DMChainCanInterface]:
        """Create a motor chain for monitoring and control."""
        try:
            # YAM motor configuration (same as in get_yam_robot)
            motor_list = [
                [0x01, "DM4340"],
                [0x02, "DM4340"],
                [0x03, "DM4340"],
                [0x04, "DM4310"],
                [0x05, "DM4310"],
                [0x06, "DM4310"],
                [0x07, "DM8009"],  # Gripper
            ]
            motor_offsets = [0.0] * 7
            motor_directions = [1] * 7
            
            motor_chain = DMChainCanInterface(
                motor_list,
                motor_offsets,
                motor_directions,
                channel,
                motor_chain_name=f"yam_{arm_name}_monitor",
                receive_mode=ReceiveMode.p16,
                use_buffered_reader=False,
            )
            
            logger.info(f"Created motor chain for {arm_name} arm on {channel}")
            return motor_chain
            
        except Exception as e:
            logger.error(f"Failed to create motor chain for {arm_name}: {e}")
            return None
    
    def connect(self):
        """Connect to YAM motors and setup ZMQ listener."""
        if self._is_connected:
            logger.warning("Already connected")
            return
        
        # Setup motor chains
        logger.info("Connecting to YAM motors...")
        self.left_motor_chain = self._create_motor_chain(
            self.config.left_can_channel, "left"
        )
        
        # Add delay to avoid CAN conflicts
        time.sleep(2)
        
        self.right_motor_chain = self._create_motor_chain(
            self.config.right_can_channel, "right"
        )
        
        if not self.left_motor_chain or not self.right_motor_chain:
            raise RuntimeError("Failed to connect to motor chains")
        
        # Setup ZMQ listener
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.PULL)
        self.zmq_socket.bind(f"tcp://*:{self.config.listen_port}")
        
        self._is_connected = True
        logger.info(f"YAM Motor Enable Listener ready on port {self.config.listen_port}")
    
    def get_motor_status(self, motor_chain: DMChainCanInterface) -> Dict[int, Dict]:
        """Get status of all motors in a chain."""
        try:
            motor_states = motor_chain.read_states()
            status = {}
            
            for state in motor_states:
                # Check if motor has error
                is_disabled = state.error_code != 0x1  # 0x1 is normal
                error_msg = MotorErrorCode.get_error_message(state.error_code)
                
                status[state.id] = {
                    "enabled": not is_disabled,
                    "error_code": state.error_code,
                    "error_message": error_msg,
                    "position": state.pos,
                    "velocity": state.vel,
                    "temperature": state.temperature,
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get motor status: {e}")
            return {}
    
    def enable_motors(self, arm: str, motor_ids: Optional[List[int]] = None, mode: str = "partial"):
        """Enable specified motors on an arm."""
        motor_chain = self.left_motor_chain if arm == "left" else self.right_motor_chain
        
        if not motor_chain:
            logger.error(f"No motor chain for {arm} arm")
            return False
        
        try:
            # Get current status
            current_status = self.get_motor_status(motor_chain)
            
            # Determine which motors to enable
            if motor_ids is None:
                if mode == "full":
                    # Enable all motors
                    motor_ids = list(range(1, 8))  # Motors 1-7
                else:  # partial mode
                    # Only enable disabled motors
                    motor_ids = [
                        mid for mid, status in current_status.items()
                        if not status["enabled"]
                    ]
            
            if not motor_ids:
                logger.info(f"No motors to enable on {arm} arm")
                return True
            
            # Clean errors for specified motors
            for motor_id in motor_ids:
                if motor_id in current_status:
                    logger.info(f"Enabling motor {motor_id} on {arm} arm")
                    motor_chain.clean_error(motor_id)
                    time.sleep(0.05)  # Small delay between motors
            
            # Verify motors are enabled
            time.sleep(0.2)
            new_status = self.get_motor_status(motor_chain)
            
            success = all(
                new_status.get(mid, {}).get("enabled", False)
                for mid in motor_ids
            )
            
            if success:
                logger.info(f"Successfully enabled {len(motor_ids)} motors on {arm} arm")
            else:
                logger.warning(f"Some motors failed to enable on {arm} arm")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to enable motors on {arm} arm: {e}")
            return False
    
    def process_command(self, command: Dict):
        """Process an enable command."""
        action = command.get("action", "enable")
        target = command.get("target", "both")
        mode = command.get("mode", self.config.default_enable_mode)
        motor_ids = command.get("motor_ids")
        
        logger.info(f"Processing command: action={action}, target={target}, mode={mode}")
        
        if action == "enable":
            if target in ["left", "both"]:
                self.enable_motors("left", motor_ids, mode)
            if target in ["right", "both"]:
                self.enable_motors("right", motor_ids, mode)
                
        elif action == "status":
            # Return current status
            status = {
                "left": self.get_motor_status(self.left_motor_chain),
                "right": self.get_motor_status(self.right_motor_chain),
            }
            logger.info(f"Motor status: {json.dumps(status, indent=2)}")
            return status
        
        elif action == "reset":
            # Reset all motors (full enable)
            if target in ["left", "both"]:
                self.enable_motors("left", mode="full")
            if target in ["right", "both"]:
                self.enable_motors("right", mode="full")
    
    def run(self):
        """Main loop to listen for commands."""
        if not self._is_connected:
            raise RuntimeError("Not connected. Call connect() first.")
        
        logger.info("Listening for motor enable commands...")
        
        # Periodically check motor status
        last_status_check = time.time()
        status_check_interval = 5.0  # Check every 5 seconds
        
        while True:
            try:
                # Check for incoming commands (non-blocking)
                try:
                    msg = self.zmq_socket.recv_string(flags=zmq.NOBLOCK)
                    command = json.loads(msg)
                    self.process_command(command)
                except zmq.Again:
                    # No message available
                    pass
                except json.JSONDecodeError:
                    logger.warning("Received malformed JSON command")
                
                # Periodic status check
                if time.time() - last_status_check > status_check_interval:
                    left_status = self.get_motor_status(self.left_motor_chain)
                    right_status = self.get_motor_status(self.right_motor_chain)
                    
                    # Log any disabled motors
                    disabled_left = [
                        mid for mid, status in left_status.items()
                        if not status["enabled"]
                    ]
                    disabled_right = [
                        mid for mid, status in right_status.items()
                        if not status["enabled"]
                    ]
                    
                    if disabled_left or disabled_right:
                        logger.warning(f"Disabled motors - Left: {disabled_left}, Right: {disabled_right}")
                    
                    last_status_check = time.time()
                
                time.sleep(0.1)  # Small delay to prevent CPU spinning
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)
    
    def disconnect(self):
        """Disconnect from motors and cleanup."""
        if not self._is_connected:
            return
        
        logger.info("Disconnecting...")
        
        if self.left_motor_chain:
            self.left_motor_chain.close()
        if self.right_motor_chain:
            self.right_motor_chain.close()
        
        if self.zmq_socket:
            self.zmq_socket.close()
        if self.zmq_context:
            self.zmq_context.term()
        
        self._is_connected = False
        logger.info("Disconnected")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="YAM Motor Enable Listener")
    parser.add_argument("--left-can", default="can0", help="Left arm CAN channel")
    parser.add_argument("--right-can", default="can1", help="Right arm CAN channel")
    parser.add_argument("--port", type=int, default=5569, help="Listen port")
    parser.add_argument("--mode", default="partial", choices=["partial", "full"],
                        help="Default enable mode")
    args = parser.parse_args()
    
    config = YAMMotorEnableConfig(
        left_can_channel=args.left_can,
        right_can_channel=args.right_can,
        listen_port=args.port,
        default_enable_mode=args.mode,
    )
    
    listener = YAMMotorEnableListener(config)
    
    try:
        listener.connect()
        listener.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        listener.disconnect()


if __name__ == "__main__":
    main()