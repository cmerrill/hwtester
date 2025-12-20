"""Sequence parsing and execution."""

import re
import time
from dataclasses import dataclass
from typing import Union

from .relay import RelayController


@dataclass
class RelayCommand:
    """Relay on/off command."""

    relay_num: int
    on: bool

    def __str__(self) -> str:
        state = "ON" if self.on else "OFF"
        return f"R{self.relay_num}:{state}"


@dataclass
class DelayCommand:
    """Delay command in milliseconds."""

    duration_ms: int

    def __str__(self) -> str:
        return f"D{self.duration_ms}"


@dataclass
class ResetCommand:
    """Reset all relays to OFF."""

    def __str__(self) -> str:
        return "I"


Command = Union[RelayCommand, DelayCommand, ResetCommand]


class SequenceParser:
    """Parses relay command sequences."""

    # Pattern for relay command: R1:ON, R16:OFF, Ralias:ON, etc.
    RELAY_PATTERN = re.compile(r"^R([a-z0-9_]+):(ON|OFF)$", re.IGNORECASE)

    # Pattern for delay: D500, D1000, etc.
    DELAY_PATTERN = re.compile(r"^D(\d+)$", re.IGNORECASE)

    # Pattern for reset: I
    RESET_PATTERN = re.compile(r"^I$", re.IGNORECASE)

    @classmethod
    def parse(cls, sequence_str: str, relay_aliases: dict[str, int] = None) -> list[Command]:
        """
        Parse comma-separated sequence string.

        Args:
            sequence_str: e.g., "R1:ON,D500,R1:OFF" or "Rdut1_reset:ON,D500,Rdut1_reset:OFF"
            relay_aliases: Optional dict mapping alias names to relay numbers

        Returns:
            List of Command objects

        Raises:
            ValueError: If sequence contains invalid commands
        """
        commands = []
        relay_aliases = relay_aliases or {}

        parts = [p.strip() for p in sequence_str.split(",")]

        for part in parts:
            if not part:
                continue

            # Try relay pattern
            relay_match = cls.RELAY_PATTERN.match(part)
            if relay_match:
                relay_id = relay_match.group(1).lower()
                on = relay_match.group(2).upper() == "ON"

                # Try to parse as number first, then check aliases
                try:
                    relay_num = int(relay_id)
                except ValueError:
                    # Not a number, check if it's an alias
                    if relay_id in relay_aliases:
                        relay_num = relay_aliases[relay_id]
                    else:
                        raise ValueError(f"Unknown relay alias: {relay_id}")

                if not 1 <= relay_num <= 16:
                    raise ValueError(f"Relay number must be 1-16, got {relay_num}")

                commands.append(RelayCommand(relay_num=relay_num, on=on))
                continue

            # Try delay pattern
            delay_match = cls.DELAY_PATTERN.match(part)
            if delay_match:
                duration = int(delay_match.group(1))
                commands.append(DelayCommand(duration_ms=duration))
                continue

            # Try reset pattern
            reset_match = cls.RESET_PATTERN.match(part)
            if reset_match:
                commands.append(ResetCommand())
                continue

            raise ValueError(f"Invalid command: {part}")

        return commands


class SequenceExecutor:
    """Executes parsed command sequences."""

    def __init__(
        self, relay_controller: RelayController, verbose: bool = True, relay_aliases: dict[str, int] = None
    ):
        """
        Initialize executor.

        Args:
            relay_controller: Connected relay controller
            verbose: If True, print commands as they execute
            relay_aliases: Optional dict mapping alias names to relay numbers
        """
        self.relay = relay_controller
        self.verbose = verbose
        self.relay_aliases = relay_aliases or {}

    def execute(self, commands: list[Command]) -> None:
        """
        Execute a sequence of commands.

        Args:
            commands: List of parsed commands
        """
        for cmd in commands:
            if self.verbose:
                print(f"Executing: {cmd}")

            if isinstance(cmd, RelayCommand):
                self.relay.set_relay(cmd.relay_num, cmd.on)

            elif isinstance(cmd, DelayCommand):
                time.sleep(cmd.duration_ms / 1000.0)

            elif isinstance(cmd, ResetCommand):
                self.relay.reset_all_relays()

    def execute_string(self, sequence_str: str) -> None:
        """Parse and execute a sequence string."""
        commands = SequenceParser.parse(sequence_str, relay_aliases=self.relay_aliases)
        self.execute(commands)
