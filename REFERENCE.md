# hwtester Reference Documentation

## Package Overview

`hwtester` is a Python CLI tool for hardware testing automation. It controls relay boards via serial and logs DUT (Device Under Test) serial output.

## Installation

The hwtester module is bundled with this skill. Just ensure the dependencies are installed:

```bash
pip install pyserial

# For Python < 3.11 only:
pip install tomli
```

Run the bundled module from the skill directory:

```bash
python -m hwtester [args]
```

## CLI Usage

```bash
python -m hwtester [-c CONFIG] [-r PORT] [-d PORTS...] [-b RATE] [-l DIR] [-t] [-p PREFIX]
                   [-s SEQ | -f | -i] [-v | -q]
```

### Arguments

| Flag | Long Form | Description |
|------|-----------|-------------|
| `-c` | `--config` | TOML configuration file |
| `-r` | `--relay-port` | Serial port for relay board |
| `-d` | `--dut-ports` | Serial port(s) for DUT logging |
| `-b` | `--baud-rate` | DUT baud rate (default: 115200) |
| `-l` | `--log-dir` | Log file directory (default: ./logs) |
| `-t` | `--timestamp-lines` | Add timestamp to each logged line |
| `-p` | `--log-prefix` | Prefix for log filenames |
| `-v` | `--verbose` | Verbose output |
| `-q` | `--quiet` | Suppress non-error output |

### Operating Modes (mutually exclusive)

| Flag | Mode | Description |
|------|------|-------------|
| `-s` | Sequence | Execute commands from CLI string |
| `-f` | File | Execute sequence from config file |
| `-i` | Interactive | Manual REPL control |

### Examples

```bash
# Run sequence from config file
python -m hwtester -c tests/test_pairing.toml -f

# Run inline sequence
python -m hwtester -r COM9 -s "R1:ON,D2000,R1:OFF"

# With DUT logging
python -m hwtester -r COM9 -d COM4 COM5 -s "R1:ON,D5000,R1:OFF"

# Interactive mode
python -m hwtester -r COM9 -d COM4 -i

# Just log DUT ports for 30 seconds (no relay)
python -m hwtester -d COM4 COM5 -s "D30000"
```

## TOML Configuration Format

### Complete Example

```toml
# Relay Board Configuration
[relay]
port = "COM9"  # Windows: COMx | Linux: /dev/ttyUSBx

# Relay Aliases (optional but recommended)
[relay.aliases]
dut1_power = 1
dut1_reset = 2
dut1_boot_mode = 3
dut2_power = 4
dut2_reset = 5

# DUT Serial Port Configuration
[dut]
# Simple format (uses default 115200 baud):
# ports = ["COM4", "COM5"]

# Detailed format (recommended):
ports = [
    { port = "COM4", baud_rate = 115200, name = "dut1" },
    { port = "COM5", baud_rate = 115200, name = "dut2" },
]

# Logging Configuration
[logging]
directory = "./logs"
timestamp_lines = true
prefix = "test_"

# Command Sequence
[sequence]
# String format:
# commands = "I,R1:ON,D2000,R1:OFF"

# Array format (recommended):
commands = [
    "I",                       # Initialize all OFF
    "Rdut1_power:ON",          # Power on
    "D2000",                   # Wait 2 seconds
    "Rdut1_power:OFF",         # Power off
]
```

### Configuration Precedence

1. CLI arguments (highest priority)
2. Config file values
3. Built-in defaults (lowest priority)

## Command Reference

### Relay Commands

| Command | Description |
|---------|-------------|
| `R<1-16>:ON` | Turn relay ON (by number) |
| `R<1-16>:OFF` | Turn relay OFF (by number) |
| `R<alias>:ON` | Turn relay ON (by alias name) |
| `R<alias>:OFF` | Turn relay OFF (by alias name) |

### Control Commands

| Command | Description |
|---------|-------------|
| `I` | Initialize - turn all relays OFF |
| `D<ms>` | Delay for specified milliseconds |

### Command Patterns

Commands are case-insensitive. Regex patterns used internally:
- Relay: `^R([a-z0-9_]+):(ON|OFF)$`
- Delay: `^D(\d+)$`
- Reset: `^I$`

## Python API

### RelayController

```python
from hwtester import RelayController

relay = RelayController("COM9")
relay.connect()

relay.relay_on(1)        # Turn relay 1 ON
relay.relay_off(1)       # Turn relay 1 OFF
relay.set_relay(2, True) # Set relay 2 state
relay.reset_all_relays() # All relays OFF

relay.disconnect()

# Context manager
with RelayController("COM9") as relay:
    relay.relay_on(1)
```

### DUTLogger

```python
from pathlib import Path
from hwtester import DUTLogger

logger = DUTLogger(
    port="COM4",
    log_dir=Path("./logs"),
    baud_rate=115200,
    timestamp_lines=True,
    port_name="dut1",
    log_prefix="test_"
)

log_path = logger.start()  # Returns path to log file
# ... test runs, logging in background ...
logger.stop()

# Context manager
with DUTLogger("COM4", Path("./logs")) as logger:
    pass  # Logging happens automatically
```

### SequenceExecutor

```python
from hwtester import RelayController, SequenceExecutor

relay = RelayController("COM9")
relay.connect()

executor = SequenceExecutor(
    relay,
    verbose=True,
    relay_aliases={"dut1_power": 1, "dut1_reset": 2}
)

executor.execute_string("I,Rdut1_power:ON,D2000,Rdut1_reset:OFF")

relay.disconnect()
```

### Config Loading

```python
from pathlib import Path
from hwtester import load_config

config = load_config(Path("tests/test.toml"))

print(config.relay_port)      # "COM9"
print(config.relay_aliases)   # {"dut1_power": 1, ...}
print(config.dut_ports)       # [DUTPortConfig(...), ...]
print(config.sequence)        # "I,R1:ON,..."
```

## Hardware Protocol

### Relay Board Communication

- **Baud rate**: 9600
- **Protocol**: Intel Hex format
- **Relays**: 1-16 (user-facing), 0-15 (internal)

### DUT Serial Logging

- **Default baud**: 115200
- **Encoding**: UTF-8 with fallback
- **Line buffering**: Newline-delimited
- **Threading**: Background daemon threads

## Log File Format

### Filename Pattern
```
[PREFIX]{port_name}_{YYYYMMDD_HHMMSS}.log
```

Example: `pairing_test_dut1_20250120_143022.log`

### Line Timestamp Format (if enabled)
```
[YYYY-MM-DD HH:MM:SS.mmm] {line_content}
```

Example: `[2025-01-20 14:30:22.450] Device boot complete`

## Interactive Mode Commands

| Command | Description |
|---------|-------------|
| `r<N> on` | Turn relay N on |
| `r<N> off` | Turn relay N off |
| `I` | Reset all relays |
| `d<ms>` | Delay milliseconds |
| `seq <cmds>` | Execute command sequence |
| `raw <hex>` | Send raw hex bytes |
| `status` | Show connection status |
| `help` | Show help |
| `quit` | Exit |

## Common Test Patterns

### Power Cycle Test
```toml
commands = [
    "I",                    # Ensure clean state
    "Rdut_power:OFF",       # Power off
    "D500",                 # Wait for discharge
    "Rdut_power:ON",        # Power on
    "D3000",                # Wait for boot
]
```

### Reset Test
```toml
commands = [
    "Rdut_reset:ON",        # Assert reset
    "D100",                 # Hold reset
    "Rdut_reset:OFF",       # Release reset
    "D2000",                # Wait for boot
]
```

### Boot Mode Selection
```toml
commands = [
    "I",                    # Clean state
    "Rdut_boot_mode:ON",    # Set boot mode pin
    "Rdut_reset:ON",        # Assert reset
    "Rdut_power:ON",        # Apply power
    "D100",                 # Stabilize
    "Rdut_reset:OFF",       # Release reset
    "D2000",                # Wait for boot
]
```

### Pairing/Communication Test
```toml
commands = [
    "I",                    # Clean state
    "Rdut1_reset:ON",       # Reset both devices
    "Rdut2_reset:ON",
    "D100",
    "Rdut1_reset:OFF",      # Boot devices
    "Rdut2_reset:OFF",
    "D2000",                # Wait for boot
    "Rdut1_pair:ON",        # Initiate pairing
    "D200",
    "Rdut2_pair:ON",        # Accept pairing
    "D10000",               # Wait for pairing
    "I",                    # Clean up
]
```

## Troubleshooting

### Serial Port Issues

```bash
# List available ports (Python)
python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"

# Windows: Check Device Manager
# Linux: ls /dev/ttyUSB* /dev/ttyACM*
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Port not found | Wrong port name | List ports, verify connection |
| Permission denied | Access rights | Run as admin / add user to dialout group |
| No response | Wrong baud rate | Relay board uses 9600 baud |
| Garbled output | Baud mismatch | Verify DUT baud rate |
| Timeout | Hardware issue | Check cables, power |
