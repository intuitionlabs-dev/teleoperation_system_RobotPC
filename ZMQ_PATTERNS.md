# ZMQ Communication Patterns for Teleoperation

## PUB/SUB vs PUSH/PULL

### PUSH/PULL Pattern (Previous Implementation)
- **Behavior**: Messages are queued and delivered in order
- **Delivery**: Guaranteed delivery of all messages
- **Problem for Teleoperation**: Old commands accumulate in queue, causing increasing lag
- **Use Case**: Good for task distribution where every message must be processed

### PUB/SUB Pattern (Current Implementation)
- **Behavior**: Only latest message is delivered, old messages discarded
- **Delivery**: Messages may be lost if subscriber not ready
- **Advantage for Teleoperation**: Real-time behavior, no lag accumulation
- **Use Case**: Perfect for teleoperation where only current position matters

## Common Misconception: TCP vs UDP

Both PUSH/PULL and PUB/SUB can use TCP or other transports:
- **tcp://**: Reliable, ordered delivery at transport level
- **ipc://**: Inter-process communication
- **inproc://**: In-process communication

The difference is in the messaging pattern, not the transport protocol:
- PUSH/PULL queues messages regardless of transport
- PUB/SUB delivers only latest regardless of transport

## Why PUB/SUB for Teleoperation?

In teleoperation, we care about:
1. **Current position** - not historical positions
2. **Low latency** - immediate response to operator input
3. **Real-time tracking** - follower should mirror leader now, not replay old moves

PUB/SUB provides exactly this behavior by discarding queued messages.

## Configuration Notes

### Publisher (Teleoperator):
```python
socket = context.socket(zmq.PUB)
socket.setsockopt(zmq.SNDHWM, 1)  # Keep only 1 message in send queue
socket.setsockopt(zmq.LINGER, 0)   # Don't block on close
```

### Subscriber (Robot):
```python
socket = context.socket(zmq.SUB)
socket.setsockopt(zmq.SUBSCRIBE, b"")  # Subscribe to all messages
socket.setsockopt(zmq.RCVTIMEO, 35)    # 35ms timeout for responsiveness
```

The 35ms timeout allows checking for other events (like enable/disable commands) while maintaining responsive teleoperation.
