"""Interactive mode REPL."""

import re
import time
from typing import Optional

from .relay import RelayController
from .sequence import SequenceExecutor


class InteractiveMode:
    """
    Interactive command-line interface for manual control.

    Commands:
        r<N> on/off   - Turn relay N on or off (e.g., "r1 on", "r15 off")
        d<ms>         - Delay for milliseconds
        raw <hex>     - Send raw hex bytes to relay port
        seq <cmds>    - Execute command sequence
        status        - Show connection status
        help          - Show help
        quit/exit     - Exit interactive mode
    """

    def __init__(
        self,
        relay_controller: Optional[RelayController] = None,
        executor: Optional[SequenceExecutor] = None,
        relay_aliases: Optional[dict[str, int]] = None,
    ):
        self.relay = relay_controller
        self.executor = executor or (
            SequenceExecutor(relay_controller, verbose=True, relay_aliases=relay_aliases)
            if relay_controller
            else None
        )
        self.relay_aliases = relay_aliases or {}
        self._running = False

    def print_help(self) -> None:
        """Print help message."""
        help_text = """
Interactive Hardware Tester Commands:
=====================================
  r<N> on       Turn relay N on (0-15)
  r<N> off      Turn relay N off (0-15)
  d<ms>         Delay for milliseconds
  raw <hex>     Send raw hex bytes to relay port
  seq <cmds>    Execute sequence (e.g., seq R1:ON,D500,R1:OFF)
  status        Show connection status
  help          Show this help message
  quit/exit     Exit interactive mode

Examples:
  r1 on         Turn on relay 1
  r0 off        Turn off relay 0
  d1000         Wait 1 second
  raw FE050001FF00FD
  seq R1:ON,D500,R1:OFF
"""
        print(help_text)

        if self.relay_aliases:
            print("Configured Relay Aliases:")
            print("=" * 37)
            for alias, relay_num in sorted(self.relay_aliases.items()):
                print(f"  {alias:<20} -> Relay {relay_num}")
            print()

    def process_command(self, line: str) -> bool:
        """
        Process a single command.

        Returns:
            False if should exit, True to continue
        """
        line = line.strip()
        line_lower = line.lower()

        if not line:
            return True

        # Quit command
        if line_lower in ("quit", "exit", "q"):
            return False

        # Help command
        if line_lower == "help":
            self.print_help()
            return True

        # Status command
        if line_lower == "status":
            if self.relay and self.relay._serial and self.relay._serial.is_open:
                print(f"Relay port: {self.relay.port} (connected)")
            else:
                print("Relay port: not connected")
            return True

        # Relay command: r1 on, r15 off, or ralias on/off
        relay_match = re.match(r"^r([a-z0-9_]+)\s+(on|off)$", line_lower)
        if relay_match:
            if not self.relay:
                print("Error: No relay port configured")
                return True

            relay_id = relay_match.group(1)
            on = relay_match.group(2) == "on"

            # Try to parse as number first, then check aliases
            try:
                relay_num = int(relay_id)
            except ValueError:
                # Not a number, check if it's an alias
                if relay_id in self.relay_aliases:
                    relay_num = self.relay_aliases[relay_id]
                else:
                    print(f"Error: Unknown relay alias '{relay_id}'")
                    return True

            try:
                self.relay.set_relay(relay_num, on)
                state = "ON" if on else "OFF"
                if relay_id.isdigit():
                    print(f"Relay {relay_num} -> {state}")
                else:
                    print(f"Relay {relay_id} (#{relay_num}) -> {state}")
            except ValueError as e:
                print(f"Error: {e}")
            except Exception as e:
                print(f"Serial error: {e}")

            return True

        # Delay command: d500
        delay_match = re.match(r"^d(\d+)$", line_lower)
        if delay_match:
            duration_ms = int(delay_match.group(1))
            print(f"Waiting {duration_ms}ms...")
            time.sleep(duration_ms / 1000.0)
            return True

        # Raw command: raw FE0500...
        raw_match = re.match(r"^raw\s+([0-9a-f\s]+)$", line_lower)
        if raw_match:
            if not self.relay:
                print("Error: No relay port configured")
                return True

            hex_str = raw_match.group(1).replace(" ", "")
            try:
                data = bytes.fromhex(hex_str)
                self.relay.send_raw(data)
                print(f"Sent {len(data)} bytes")
            except ValueError:
                print("Error: Invalid hex string")

            return True

        # Sequence command: seq R1:ON,D500,R1:OFF
        seq_match = re.match(r"^seq\s+(.+)$", line, re.IGNORECASE)
        if seq_match:
            if not self.executor:
                print("Error: No relay port configured")
                return True

            try:
                self.executor.execute_string(seq_match.group(1))
            except ValueError as e:
                print(f"Sequence error: {e}")

            return True

        print(f"Unknown command: {line}")
        print("Type 'help' for available commands")
        return True

    def run(self) -> None:
        """Run interactive REPL."""
        print("Hardware Tester Interactive Mode")
        print("Type 'help' for commands, 'quit' to exit")
        print()

        self._running = True

        while self._running:
            try:
                line = input("hwtester> ")
                if not self.process_command(line):
                    break
            except EOFError:
                break
            except KeyboardInterrupt:
                print()  # Newline after ^C
                break

        print("Exiting interactive mode")
