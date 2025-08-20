#!/usr/bin/env python3
"""
Raw CAN test - send enable command and listen for any responses.
"""

import can
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_can_raw(channel: str):
    """Test raw CAN communication."""
    logger.info(f"\nTesting {channel} with raw CAN...")
    logger.info("-" * 40)
    
    try:
        # Create CAN bus
        bus = can.interface.Bus(channel=channel, bustype='socketcan', bitrate=1000000)
        logger.info(f"✓ CAN bus created on {channel}")
        
        # Flush any pending messages
        while True:
            msg = bus.recv(timeout=0.001)
            if msg is None:
                break
                
        # Test each motor ID
        for motor_id in range(1, 8):
            logger.info(f"  Testing motor {motor_id}...")
            
            # Send enable command (0xFC)
            data = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC]
            msg = can.Message(
                arbitration_id=motor_id,
                data=data,
                is_extended_id=False
            )
            
            try:
                bus.send(msg)
                logger.info(f"    → Sent enable command to motor {motor_id}")
                
                # Wait for response
                response = bus.recv(timeout=0.1)
                
                if response:
                    logger.info(f"    ← Received response: ID={response.arbitration_id:03X}, Data={response.data.hex()}")
                else:
                    logger.warning(f"    ✗ No response from motor {motor_id}")
                    
            except Exception as e:
                logger.error(f"    ✗ Error: {e}")
                
            time.sleep(0.05)
            
        bus.shutdown()
        
    except Exception as e:
        logger.error(f"✗ Failed to create CAN bus on {channel}: {e}")


def listen_can(channel: str, duration: float = 2.0):
    """Just listen on CAN bus for any traffic."""
    logger.info(f"\nListening on {channel} for {duration} seconds...")
    logger.info("-" * 40)
    
    try:
        bus = can.interface.Bus(channel=channel, bustype='socketcan', bitrate=1000000)
        logger.info(f"Listening for CAN messages...")
        
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < duration:
            msg = bus.recv(timeout=0.1)
            if msg:
                message_count += 1
                logger.info(f"  Message {message_count}: ID={msg.arbitration_id:03X}, Data={msg.data.hex()}")
                
        if message_count == 0:
            logger.warning(f"No messages received in {duration} seconds")
        else:
            logger.info(f"Received {message_count} messages")
            
        bus.shutdown()
        
    except Exception as e:
        logger.error(f"✗ Error: {e}")


def main():
    """Test raw CAN communication."""
    
    logger.info("=" * 50)
    logger.info("Raw CAN Communication Test")
    logger.info("=" * 50)
    
    # First just listen to see if there's any traffic
    listen_can("can_follow_l", 2.0)
    listen_can("can_follow_r", 2.0)
    
    # Then try to communicate with motors
    test_can_raw("can_follow_l")
    test_can_raw("can_follow_r")
    
    logger.info("\n" + "=" * 50)
    logger.info("Test complete")
    logger.info("If no responses were received, check:")
    logger.info("  1. Motor power supply is ON")
    logger.info("  2. CAN cables are properly connected")
    logger.info("  3. CAN termination resistors are in place")
    logger.info("  4. Motors are not in error state")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()