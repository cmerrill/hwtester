"""Command-line interface definition."""

import argparse
import sys
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""

    parser = argparse.ArgumentParser(
        prog="hwtester",
        description="Hardware tester CLI - Control relays and log DUT serial output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run sequence from command line
  hwtester -r COM3 -s "R1:ON,D500,R1:OFF"

  # With DUT logging
  hwtester -r COM3 -d COM4 COM5 -s "R1:ON,D2000,R1:OFF"

  # Use config file
  hwtester -c config.toml -f

  # Interactive mode
  hwtester -r COM3 -d COM4 -i

  # Override config with CLI args
  hwtester -c config.toml -s "R2:ON,D1000,R2:OFF"

Sequence format:
  R<n>:ON   - Turn relay n on (0-15)
  R<n>:OFF  - Turn relay n off (0-15)
  D<ms>     - Delay in milliseconds

  Example: R1:ON,D500,R2:ON,D1000,R1:OFF,R2:OFF
""",
    )

    # Config file
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        metavar="FILE",
        help="TOML configuration file",
    )

    # Relay port
    parser.add_argument(
        "-r",
        "--relay-port",
        metavar="PORT",
        help="Serial port for relay board (e.g., COM3, /dev/ttyUSB0)",
    )

    # DUT ports
    parser.add_argument(
        "-d",
        "--dut-ports",
        nargs="+",
        metavar="PORT",
        help="Serial port(s) for DUT logging",
    )

    # DUT baud rate (applies to all CLI-specified ports)
    parser.add_argument(
        "-b",
        "--baud-rate",
        type=int,
        default=115200,
        metavar="RATE",
        help="Baud rate for DUT ports (default: 115200)",
    )

    # Log directory
    parser.add_argument(
        "-l",
        "--log-dir",
        type=Path,
        metavar="DIR",
        help="Directory for log files (default: ./logs)",
    )

    # Timestamp lines
    parser.add_argument(
        "-t",
        "--timestamp-lines",
        action="store_true",
        help="Prepend timestamp to each logged line",
    )

    # Log file prefix
    parser.add_argument(
        "-p",
        "--log-prefix",
        metavar="PREFIX",
        help="Prefix to prepend to log filenames",
    )

    # Operating modes (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()

    mode_group.add_argument(
        "-s",
        "--sequence",
        metavar="SEQ",
        help="Relay command sequence (command mode)",
    )

    mode_group.add_argument(
        "-f",
        "--file-mode",
        action="store_true",
        help="Use sequence from config file (file mode)",
    )

    mode_group.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive mode for manual control",
    )

    # Verbosity
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-error output",
    )

    return parser


def validate_args(args: argparse.Namespace) -> None:
    """
    Validate parsed arguments.

    Raises:
        SystemExit: On validation error
    """
    # If no config file, relay port is required for non-interactive modes
    if not args.config and not args.relay_port:
        if args.sequence or args.file_mode:
            print(
                "Error: Relay port (-r) required when not using config file",
                file=sys.stderr,
            )
            sys.exit(1)

    # File mode requires config
    if args.file_mode and not args.config:
        print("Error: File mode (-f) requires config file (-c)", file=sys.stderr)
        sys.exit(1)

    # Config file must exist if specified
    if args.config and not args.config.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
