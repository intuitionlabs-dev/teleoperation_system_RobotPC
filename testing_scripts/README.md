# Robot Command Logging and Replay Scripts

This directory contains scripts for logging and replaying robot joint commands.

## Scripts

### 1. log_commands.py
Captures joint commands from the teleoperation system and saves them to a timestamped log file.
Also generates plots showing joint movements over time.

**Usage:**
```bash
# Pipe the output of run_host_broadcast.sh through the logger
./run_host_broadcast.sh 2>&1 | python testing_scripts/log_commands.py
```

The script will:
- Create a log file in `logs/joint_commands_YYYYMMDD_HHMMSS.jsonl`
- Pass through all output (you'll still see everything)
- Extract and save all "Final: J0=..., J1=..." commands
- Generate plots when stopped with Ctrl+C:
  - One plot for each arm (left_piper and right_piper)
  - Each plot shows all 7 joints (J0-J6) over time
  - Plots saved in `logs/curve/joint_movements_ARMNAME_TIMESTAMP.png`
- Show count of logged commands when stopped with Ctrl+C

**Log Format:**
Each line in the log is a JSON object containing:
```json
{
  "timestamp": 1234567890.123,
  "datetime": "2024-01-15T10:30:00",
  "arm": "left_piper",
  "joints": {
    "J0": 7336,
    "J1": 2704,
    "J2": 0,
    "J3": 0,
    "J4": 64331,
    "J5": -54295,
    "J6": 55762
  }
}
```

### 2. replay_commands.py
Replays logged commands to the robot arms using the same control mode.

**Usage:**
```bash
# Replay a specific log file
python testing_scripts/replay_commands.py logs/joint_commands_20240115_103000.jsonl

# Replay at 0.5x speed (slower)
python testing_scripts/replay_commands.py logs/joint_commands_20240115_103000.jsonl --speed 0.5

# Loop the replay continuously
python testing_scripts/replay_commands.py logs/joint_commands_20240115_103000.jsonl --loop

# Use different CAN ports
python testing_scripts/replay_commands.py logs/joint_commands_20240115_103000.jsonl \
    --left-port can0 --right-port can1
```

**Options:**
- `--speed FACTOR`: Playback speed multiplier (default: 1.0)
- `--loop`: Loop the replay continuously
- `--left-port PORT`: Left arm CAN port (default: left_piper)
- `--right-port PORT`: Right arm CAN port (default: right_piper)

## Example Workflow

1. **Record a teleoperation session:**
   ```bash
   ./run_host_broadcast.sh 2>&1 | python testing_scripts/log_commands.py
   # Perform your teleoperation movements
   # Press Ctrl+C when done
   # Plots will be automatically generated in logs/curve/
   ```

2. **Check available logs and plots:**
   ```bash
   # View log files
   ls -la logs/joint_commands_*.jsonl
   
   # View generated plots
   ls -la logs/curve/
   ```

3. **Generate plots from existing logs:**
   ```bash
   # If you need to regenerate plots or analyze old sessions
   python testing_scripts/plot_from_log.py logs/joint_commands_20240115_103000.jsonl
   ```

4. **Replay the recorded session:**
   ```bash
   python testing_scripts/replay_commands.py logs/joint_commands_20240115_103000.jsonl
   ```

## Notes

- The replay script uses the exact same MIT control mode (0xAD) as the teleoperation system
- Joint values are sent directly without any scaling (they're already in 0.001° units)
- The replay timing matches the original recording (adjustable with --speed)
- Both arms are controlled simultaneously, just like in teleoperation

### 3. plot_from_log.py
Generate plots from existing log files without running the teleoperation system.

**Usage:**
```bash
# Plot from a specific log file
python testing_scripts/plot_from_log.py logs/joint_commands_20240115_103000.jsonl

# Save plots to a custom directory
python testing_scripts/plot_from_log.py logs/joint_commands_20240115_103000.jsonl --output-dir /tmp/plots
```

**Features:**
- Loads data from existing JSONL log files
- Generates the same plots as log_commands.py
- Shows statistics (duration, sample count, average rate)
- Useful for post-analysis of recorded sessions
