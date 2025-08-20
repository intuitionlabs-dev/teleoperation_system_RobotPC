#!/usr/bin/env python3
"""
Clear error states on YAM motors before launching.
"""

import sys
import time
import logging
from pathlib import Path

# Add i2rt to path
i2rt_path = Path(__file__).parent.parent / "i2rt"
if str(i2rt_path) not in sys.path:
    sys.path.append(str(i2rt_path))

from i2rt.motor_drivers.dm_driver import DMSingleMotorCanInterface

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_motor_errors(channel: str, motor_ids: list):
    """Clear error states on motors."""
    logger.info(f"Clearing motor errors on channel {channel}")
    
    try:
        # Create motor interface
        motor_interface = DMSingleMotorCanInterface(
            channel=channel,
            bustype="socketcan",
            name=f"error_clear_{channel}"
        )
        
        # Give it time to initialize
        time.sleep(0.5)
        
        # Try to clear errors on each motor
        for motor_id in motor_ids:
            logger.info(f"Clearing errors on motor {motor_id}")
            try:
                # Send reset/clear error command
                # DM motors typically clear errors by sending enable command
                data = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC]  # Enable motor
                motor_interface._send_message(motor_id, data)
                time.sleep(0.1)
                
                # Try to read motor state
                data = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFD]  # Read state
                motor_interface._send_message(motor_id, data)
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to clear motor {motor_id}: {e}")
                continue
        
        # Close interface
        motor_interface.close()
        logger.info(f"Finished clearing errors on {channel}")
        
    except Exception as e:
        logger.error(f"Failed to create motor interface on {channel}: {e}")


def main():
    """Clear errors on both YAM arms."""
    
    # Motor IDs for YAM arms (1-7 for each arm)
    motor_ids = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07]
    
    # Clear errors on left arm
    logger.info("=" * 50)
    logger.info("Clearing errors on LEFT arm (can_follow_l)")
    logger.info("=" * 50)
    clear_motor_errors("can_follow_l", motor_ids)
    
    # Wait between arms
    time.sleep(2)
    
    # Clear errors on right arm
    logger.info("=" * 50)
    logger.info("Clearing errors on RIGHT arm (can_follow_r)")
    logger.info("=" * 50)
    clear_motor_errors("can_follow_r", motor_ids)
    
    logger.info("=" * 50)
    logger.info("Motor error clearing complete!")
    logger.info("You can now launch the YAM hardware servers.")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()