#!/usr/bin/env python3
"""
Test CAN communication with YAM motors.
"""

import sys
import time
import logging
from pathlib import Path

# Add i2rt to path
i2rt_path = Path(__file__).parent.parent / "i2rt"
if str(i2rt_path) not in sys.path:
    sys.path.append(str(i2rt_path))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_can_channel(channel: str):
    """Test if CAN channel is accessible and motors respond."""
    logger.info(f"\nTesting channel: {channel}")
    logger.info("-" * 40)
    
    try:
        from i2rt.motor_drivers.dm_driver import DMSingleMotorCanInterface
        
        # Create motor interface
        motor_interface = DMSingleMotorCanInterface(
            channel=channel,
            bustype="socketcan",
            name=f"test_{channel}"
        )
        
        logger.info(f"✓ CAN interface created on {channel}")
        
        # Give it time to initialize
        time.sleep(0.5)
        
        # Test each motor
        motor_types = {
            0x01: "DM4340",
            0x02: "DM4340", 
            0x03: "DM4340",
            0x04: "DM4310",
            0x05: "DM4310",
            0x06: "DM4310",
            0x07: "DM4310",  # Gripper
        }
        
        responsive_motors = []
        unresponsive_motors = []
        
        for motor_id, motor_type in motor_types.items():
            try:
                # Try to enable motor - but catch timeout issues
                logger.info(f"  Testing motor {motor_id} ({motor_type})...")
                
                # First, just try to send a message and see if we get any response
                # without using motor_on which might block
                try:
                    # Flush any pending messages
                    while motor_interface.try_receive_message(timeout=0.001):
                        pass
                    
                    # Send enable command directly
                    data = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC]
                    message = motor_interface.bus.send(
                        motor_interface._get_message(motor_id, data)
                    )
                    
                    # Try to receive response with short timeout
                    response = motor_interface.try_receive_message(timeout=0.1)
                    
                    if response and response.arbitration_id == motor_id:
                        responsive_motors.append(motor_id)
                        logger.info(f"    ✓ Motor {motor_id} responded")
                    else:
                        unresponsive_motors.append(motor_id)
                        logger.warning(f"    ✗ Motor {motor_id} did not respond (timeout)")
                        
                except Exception as e:
                    unresponsive_motors.append(motor_id)
                    logger.warning(f"    ✗ Motor {motor_id} error during test: {e}")
                    
                time.sleep(0.05)
                
            except Exception as e:
                unresponsive_motors.append(motor_id)
                logger.warning(f"    ✗ Motor {motor_id} error: {e}")
        
        # Summary
        logger.info(f"\nSummary for {channel}:")
        logger.info(f"  Responsive motors: {responsive_motors}")
        logger.info(f"  Unresponsive motors: {unresponsive_motors}")
        
        # Close interface
        motor_interface.close()
        
        return len(responsive_motors) > 0
        
    except Exception as e:
        logger.error(f"✗ Failed to create CAN interface on {channel}: {e}")
        logger.error(f"  Make sure the CAN interface exists: sudo ip link show {channel}")
        logger.error(f"  To create it: sudo ip link add {channel} type can")
        logger.error(f"  To bring it up: sudo ip link set {channel} up type can bitrate 1000000")
        return False


def main():
    """Test both YAM arm CAN channels."""
    
    logger.info("=" * 50)
    logger.info("YAM Motor CAN Communication Test")
    logger.info("=" * 50)
    
    # Test left arm
    left_ok = test_can_channel("can_follow_l")
    
    # Test right arm
    right_ok = test_can_channel("can_follow_r")
    
    # Overall result
    logger.info("\n" + "=" * 50)
    if left_ok and right_ok:
        logger.info("✓ Both arms have responsive motors")
        logger.info("You can proceed with launching the YAM hardware servers")
    elif left_ok:
        logger.warning("⚠ Only LEFT arm has responsive motors")
    elif right_ok:
        logger.warning("⚠ Only RIGHT arm has responsive motors")
    else:
        logger.error("✗ No motors responded on either arm")
        logger.error("Check:")
        logger.error("  1. Motor power is on")
        logger.error("  2. CAN cables are connected")
        logger.error("  3. CAN interfaces are configured correctly")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()