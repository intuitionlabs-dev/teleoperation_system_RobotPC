#!/usr/bin/env python3
"""
Simple CAN test - check if CAN interfaces exist and are up.
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_can_interface(interface: str):
    """Check if a CAN interface exists and is up."""
    logger.info(f"\nChecking {interface}...")
    logger.info("-" * 40)
    
    # Check if interface exists
    try:
        result = subprocess.run(
            ["ip", "link", "show", interface],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"✗ Interface {interface} does not exist")
            logger.info(f"  To create: sudo ip link add {interface} type can")
            return False
            
        # Check if interface is UP
        if "UP" in result.stdout:
            logger.info(f"✓ Interface {interface} exists and is UP")
        else:
            logger.warning(f"⚠ Interface {interface} exists but is DOWN")
            logger.info(f"  To bring up: sudo ip link set {interface} up type can bitrate 1000000")
            return False
            
        # Check CAN statistics
        result = subprocess.run(
            ["ip", "-details", "-statistics", "link", "show", interface],
            capture_output=True,
            text=True,
            check=False
        )
        
        if "can" in result.stdout:
            logger.info(f"✓ {interface} is configured as CAN")
            # Extract bitrate if available
            if "bitrate" in result.stdout:
                for line in result.stdout.split('\n'):
                    if "bitrate" in line:
                        logger.info(f"  {line.strip()}")
                        break
        
        # Check for CAN errors
        result = subprocess.run(
            ["ip", "-s", "link", "show", interface],
            capture_output=True,
            text=True,
            check=False
        )
        logger.info(f"  Statistics:")
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if "RX:" in line and i+1 < len(lines):
                logger.info(f"    RX: {lines[i+1].strip()}")
            elif "TX:" in line and i+1 < len(lines):
                logger.info(f"    TX: {lines[i+1].strip()}")
                
        return True
        
    except Exception as e:
        logger.error(f"✗ Error checking {interface}: {e}")
        return False


def check_can_devices():
    """Check which CAN devices are available."""
    logger.info("\nChecking CAN devices in /sys/class/net/...")
    logger.info("-" * 40)
    
    try:
        result = subprocess.run(
            ["ls", "/sys/class/net/"],
            capture_output=True,
            text=True,
            check=False
        )
        
        devices = result.stdout.split()
        can_devices = [d for d in devices if d.startswith("can")]
        
        if can_devices:
            logger.info(f"Found CAN devices: {can_devices}")
        else:
            logger.warning("No CAN devices found")
            logger.info("You may need to:")
            logger.info("  1. Load CAN kernel modules: sudo modprobe can")
            logger.info("  2. Create virtual CAN: sudo ip link add can0 type vcan")
            logger.info("  3. Or setup physical CAN: sudo ip link set can0 type can bitrate 1000000")
            
    except Exception as e:
        logger.error(f"Error listing devices: {e}")


def main():
    """Check CAN interfaces for YAM arms."""
    
    logger.info("=" * 50)
    logger.info("CAN Interface Status Check")
    logger.info("=" * 50)
    
    # Check what CAN devices exist
    check_can_devices()
    
    # Check specific interfaces
    left_ok = check_can_interface("can_follow_l")
    right_ok = check_can_interface("can_follow_r")
    
    # Summary
    logger.info("\n" + "=" * 50)
    if left_ok and right_ok:
        logger.info("✓ Both CAN interfaces are ready")
    else:
        logger.error("✗ CAN interfaces are not properly configured")
        logger.info("\nTo set up CAN interfaces:")
        logger.info("  sudo ip link add can_follow_l type can")
        logger.info("  sudo ip link set can_follow_l up type can bitrate 1000000")
        logger.info("  sudo ip link add can_follow_r type can")
        logger.info("  sudo ip link set can_follow_r up type can bitrate 1000000")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()