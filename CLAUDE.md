# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hardware Tester CLI is a Python-based command-line tool for controlling relay boards and logging serial output from Device Under Test (DUT) units. It supports three modes: interactive REPL, sequence commands, and file-based automation.

## Development Commands

### Installation
```bash
# Install package in editable mode
pip install -e .

# Install with development dependencies
pip install -e .[dev]
```

### Running the Tool
```bash
# Using installed command
hwtester -c config.toml -i

# Direct module execution
python -m hwtester -c config.toml -i
```

### Testing
```bash
# Run tests (when test suite exists)
pytest

# Run with coverage
pytest --cov=hwtester
```

## Configuration

Copy `config.example.toml` to `config.toml` and modify. Configuration uses TOML format with these sections:

- **[relay]**: Relay board serial port and optional name aliases (1-16)
- **[dut]**: DUT serial ports with baud rates (simple list or detailed per-port config)
- **[logging]**: Log directory and timestamp preferences
- **[sequence]**: Pre-defined command sequences for file mode

CLI arguments override config file settings (explicit precedence).

## Architecture

### Core Data Flow
```
__main__.py → Orchestrates everything
    ├── cli.py → Parses arguments
    ├── config.py → Loads TOML config
    ├── relay.py → Controls relay board via Intel Hex protocol
    ├── dut_logger.py → Multi-threaded serial logging
    ├── sequence.py → Parses and executes commands
    └── interactive.py → REPL for manual control
```

### Key Components

**RelayController** (relay.py)
- Thread-safe relay control using Intel Hex format over serial (9600 baud)
- User-facing relay numbers: 1-16 (hardware uses 0-15 internally)
- Supports friendly name aliases from config
- Format: `:FE0500[XX][YY]00[ZZ]<CRLF>` where XX=relay, YY=state, ZZ=checksum

**DUTLogger/DUTLoggerManager** (dut_logger.py)
- Background threads for continuous serial port reading
- Default 115200 baud (configurable per port)
- Line-buffered with optional timestamps
- Handles multiple DUT ports simultaneously

**SequenceParser** (sequence.py)
- Parses commands: R<n>:ON, R<n>:OFF, D<ms>, I (reset all)
- Supports both relay numbers (1-16) and aliases
- Returns typed command objects (RelayCommand, DelayCommand, ResetCommand)

**Interactive Mode** (interactive.py)
- REPL for manual testing
- Same command syntax as sequence mode
- Real-time control with tab completion

### Thread Safety

Both RelayController and DUTLogger use `threading.Lock` for concurrent access. They also implement context managers (`with` statements) for proper resource cleanup.

### Relay Indexing

**IMPORTANT**: User-facing API uses relays 1-16. Hardware board uses 0-15. Conversion happens in RelayController. When working with relay code, pay attention to whether you're in user space (1-16) or hardware space (0-15).

## Protocol Details

### Intel Hex Format (Relay Control)
- Start: `:` (0x3A)
- Format: `FE 05 00 [relay] [state] 00 [checksum]`
- End: `<CR><LF>`
- Checksum: Two's complement of sum of all bytes (see utils.py)
- Reset command: `:FE0F00000010020000E1`

### Sequence Command Syntax
```
R<n>:ON       - Turn relay n on (n = 1-16)
R<n>:OFF      - Turn relay n off (n = 1-16)
R<alias>:ON   - Turn relay by alias on (uses config.toml [relay.aliases])
R<alias>:OFF  - Turn relay by alias off
I             - Reset all relays to OFF
D<ms>         - Delay for specified milliseconds
```

Commands can be comma-separated in sequence mode or entered interactively.

## Module Responsibilities

- **__main__.py**: Entry point, signal handling, mode selection
- **cli.py**: Argparse setup for CLI interface
- **config.py**: TOML parsing, config merging, validation
- **relay.py**: Serial communication with relay board
- **dut_logger.py**: Threaded serial logging from DUT ports
- **sequence.py**: Command parsing and execution engine
- **interactive.py**: REPL implementation with prompt_toolkit
- **utils.py**: Intel Hex checksum calculation, timestamp formatting

## Important Implementation Notes

### Config Loading Priority
1. CLI arguments (highest priority)
2. config.toml file
3. Built-in defaults

When modifying config.py, maintain this precedence order.

### Serial Port Configuration

DUT ports support two config formats:
```toml
# Simple (uses default 115200 baud)
ports = ["COM4", "COM5"]

# Detailed (per-port settings)
ports = [
    { port = "COM4", baud_rate = 115200, name = "main_uart" },
    { port = "COM5", baud_rate = 9600, name = "debug_uart" },
]
```

Config parser normalizes both to detailed format internally.

### Signal Handling

__main__.py sets up SIGINT (Ctrl+C) and SIGTERM handlers for graceful shutdown. Ensure cleanup code properly closes serial ports and stops logger threads.

## Package Structure

- Entry point: `hwtester` command (installed via pyproject.toml console_scripts)
- Public API exposed via __init__.py
- Python >=3.9 required
- Dependencies: pyserial>=3.5, tomli>=2.0 (Python <3.11)
- Build system: setuptools>=61.0 with PEP 517/518 compliance
