---
name: hwtester
description: Execute firmware tests on real hardware using hwtester. Use when the user asks to run hardware tests, execute firmware tests, control relays, log DUT serial output, or work with test TOML configuration files. Triggers on keywords like "hardware test", "firmware test", "relay", "DUT", "hwtester", or "/hwtester".
---

# Hardware Firmware Testing Skill

This skill enables Claude to execute firmware tests on real hardware using the `hwtester` Python package. It controls relay boards to manipulate hardware signals and logs serial output from Devices Under Test (DUTs).

## Prerequisites Check

The hwtester module is bundled with this skill in the `hwtester/` subdirectory. Before running any test, verify pyserial is installed:

```bash
pip show pyserial
```

If not installed:

```bash
pip install pyserial
```

For Python < 3.11, also install tomli:

```bash
pip install tomli
```

### Running the Bundled hwtester

Run hwtester using Python's `-m` flag from the skill directory:

```bash
# From the skill directory (.claude/skills/hwtester/)
python -m hwtester [args]
```

Or use the full module path with PYTHONPATH:

```bash
PYTHONPATH=/path/to/.claude/skills/hwtester python -m hwtester [args]
```

On Windows:
```bash
set PYTHONPATH=C:\path\to\.claude\skills\hwtester && python -m hwtester [args]
```

## Finding Test Configuration Files

Look for TOML configuration files in this order:

1. User-specified path (if provided)
2. `tests/` directory in current project
3. `test/` directory in current project
4. Current working directory

Use glob patterns: `tests/**/*.toml`, `test/**/*.toml`, `*.toml`

## Configuration File Analysis

When a TOML file is found, analyze its contents and determine what's missing:

### Complete Configuration (Ready to Run)
A complete config has all of:
- `[relay]` section with `port`
- `[relay.aliases]` section with relay definitions (only REQUIRED if there is no sequence)
- `[dut]` section with `ports`
- `[sequence]` section with `commands`

**Action:** Execute the test directly with `python -m hwtester -c <config.toml> -f`

### Missing Serial Ports
If `[relay]` port or `[dut]` ports are missing:

1. List available serial ports on the system:
   ```bash
   python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"
   ```

2. Ask the user to identify:
   - Which port is the relay board
   - Which ports are DUT serial connections
   - Baud rates for each DUT (default: 115200)

3. Update or create the config file with this information

### Missing Command Sequence (But Has Aliases)
If config has relay aliases but no `[sequence]` commands:

1. Ask the user for a test description (what should the test do?)
2. Interpret the description and create a command sequence
3. Present the sequence for approval (summary first, full on request)
4. Execute once approved

### Missing Both Aliases and Sequence
If config lacks both `[relay.aliases]` and `[sequence]`:

1. Ask the user to describe each relay's function:
   - "Relay 1 controls what?"
   - "Relay 2 controls what?"
   - etc.

2. Create meaningful aliases from descriptions
3. Then ask for test description and create sequence
4. Present for approval and execute

## Command Sequence Syntax

Valid commands for sequences:

| Command | Description | Example |
|---------|-------------|---------|
| `R<n>:ON` | Turn relay n (1-16) ON | `R1:ON` |
| `R<n>:OFF` | Turn relay n (1-16) OFF | `R1:OFF` |
| `R<alias>:ON` | Turn aliased relay ON | `Rdut1_reset:ON` |
| `R<alias>:OFF` | Turn aliased relay OFF | `Rdut1_reset:OFF` |
| `D<ms>` | Delay for milliseconds | `D2000` |
| `I` | Initialize (all relays OFF) | `I` |

## Presenting Command Sequences for Approval

When presenting a generated sequence:

### Summary View (Default)
```
Test Sequence Summary:
- 5 relay operations
- 3 delay operations (total: 5.3 seconds)
- Affects relays: dut1_reset, dut1_power, test_signal

Would you like to see the full sequence, or approve and run?
```

### Full View (On Request)
```
Full Command Sequence:
1. I                    # Initialize all relays OFF
2. Rdut1_reset:ON       # Hold DUT1 in reset
3. Rdut1_power:ON       # Apply power to DUT1
4. D100                 # Wait 100ms for power stable
5. Rdut1_reset:OFF      # Release reset
6. D2000                # Wait 2s for boot
...
```

## Executing Tests

### Single Test
```bash
python -m hwtester -c <config.toml> -f
```

### Batch Mode (Multiple Tests)
When running all tests in a directory:

1. Find all `.toml` files in the specified directory
2. Present a list of tests found
3. Ask user to confirm running all, or select specific tests
4. Execute each test sequentially
5. Collect and summarize results

## Analyzing Test Results

After test execution, analyze the DUT log files:

1. Find log files in the configured `logging.directory` (default: `./logs`)
2. Look for patterns indicating:
   - **Success**: Boot messages, expected output, completion markers
   - **Failure**: Error messages, timeouts, unexpected behavior
   - **Partial**: Some expected output but incomplete

3. Present analysis to user:
   ```
   Test Results Analysis:

   DUT1 (logs/pairing_test_dut1_20250120_143022.log):
   - Boot: SUCCESS (detected "System initialized" at 2.3s)
   - Pairing: SUCCESS (detected "Paired with device" at 15.7s)

   DUT2 (logs/pairing_test_dut2_20250120_143022.log):
   - Boot: SUCCESS
   - Pairing: FAILED (timeout, no pairing message after 30s)
   ```

## Example Workflows

### Workflow 1: Complete Config File
```
User: Run the pairing test
Claude: Found tests/test_pairing.toml with complete configuration.
        Executing: python -m hwtester -c tests/test_pairing.toml -f
        [Shows output]
        Analyzing logs...
        [Shows results]
```

### Workflow 2: Missing Sequence
```
User: Run a power cycle test on DUT1
Claude: Found tests/dut1_config.toml with relay aliases but no sequence.
        Creating sequence for "power cycle test on DUT1":

        Summary: 4 operations, 3.1s total
        - Power off, wait, power on, wait for boot

        Show full sequence or approve to run?
User: approve
Claude: Executing test...
```

### Workflow 3: No Config
```
User: /hwtester
Claude: No test configuration found. Let me check available serial ports...

        Available ports: COM3, COM4, COM5, COM9

        Which port is connected to the relay board?
```

## Error Handling

- **Serial port not found**: List available ports, ask user to verify connections
- **Permission denied**: Suggest running with appropriate permissions
- **Relay board not responding**: Check baud rate (9600 for relay board)
- **DUT not logging**: Verify baud rate matches DUT configuration
- **Test timeout**: Note in results, suggest checking hardware connections

## Reference

For complete hwtester documentation, see [REFERENCE.md](REFERENCE.md).
