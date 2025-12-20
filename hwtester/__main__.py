"""Main entry point for hwtester CLI."""

import signal
import sys
from pathlib import Path

from .cli import create_parser, validate_args
from .config import Config, DUTPortConfig, load_config, merge_config_with_args
from .dut_logger import DUTLogger, DUTLoggerManager
from .interactive import InteractiveMode
from .relay import RelayController
from .sequence import SequenceExecutor


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    validate_args(args)

    # Load config if provided
    if args.config:
        try:
            config = load_config(args.config)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1
    else:
        config = Config()

    # Merge CLI args over config
    config = merge_config_with_args(config, args)

    # Set default log directory
    if not config.log_dir:
        config.log_dir = Path("./logs")

    # Setup relay controller
    relay_controller = None
    if config.relay_port:
        relay_controller = RelayController(config.relay_port)

    # Setup DUT loggers
    logger_manager = DUTLoggerManager()
    for dut_config in config.dut_ports:
        logger = DUTLogger(
            port=dut_config.port,
            log_dir=config.log_dir,
            baud_rate=dut_config.baud_rate,
            timestamp_lines=config.timestamp_lines,
            port_name=dut_config.name,
        )
        logger_manager.add_logger(logger)

    # Setup signal handler for clean shutdown
    shutdown_requested = False

    def signal_handler(sig, frame):
        nonlocal shutdown_requested
        if shutdown_requested:
            # Force exit on second Ctrl+C
            sys.exit(1)
        shutdown_requested = True
        print("\nShutting down...")

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Connect relay if configured
        if relay_controller:
            try:
                relay_controller.connect()
                if not args.quiet:
                    print(f"Connected to relay board on {config.relay_port}")
            except Exception as e:
                print(f"Error connecting to relay port: {e}", file=sys.stderr)
                return 1

        # Start DUT logging
        log_paths = logger_manager.start_all()

        # Execute based on mode
        if args.interactive:
            # Interactive mode
            interactive = InteractiveMode(relay_controller, relay_aliases=config.relay_aliases)
            interactive.run()

        elif args.sequence:
            # Command mode - sequence from CLI
            if not relay_controller:
                print(
                    "Error: Relay port required for sequence execution",
                    file=sys.stderr,
                )
                return 1

            executor = SequenceExecutor(
                relay_controller, verbose=not args.quiet, relay_aliases=config.relay_aliases
            )
            try:
                executor.execute_string(args.sequence)
            except ValueError as e:
                print(f"Sequence error: {e}", file=sys.stderr)
                return 1

        elif args.file_mode:
            # File mode - sequence from config
            if not config.sequence:
                print("Error: No sequence defined in config file", file=sys.stderr)
                return 1

            if not relay_controller:
                print(
                    "Error: Relay port required for sequence execution",
                    file=sys.stderr,
                )
                return 1

            executor = SequenceExecutor(
                relay_controller, verbose=not args.quiet, relay_aliases=config.relay_aliases
            )
            try:
                executor.execute_string(config.sequence)
            except ValueError as e:
                print(f"Sequence error: {e}", file=sys.stderr)
                return 1

        else:
            # No mode specified - check if we have something to do
            if not config.dut_ports and not relay_controller:
                print("No operation specified. Use -s, -f, -i, or specify ports.")
                parser.print_help()
                return 1

            # Just log DUT ports if that's all we have
            if config.dut_ports and not relay_controller:
                if not args.quiet:
                    print("Logging DUT ports. Press Ctrl+C to stop.")
                try:
                    # Wait until interrupted
                    while not shutdown_requested:
                        signal.pause() if hasattr(signal, "pause") else __import__("time").sleep(0.1)
                except KeyboardInterrupt:
                    pass

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    finally:
        # Clean shutdown
        logger_manager.stop_all()
        if relay_controller:
            relay_controller.disconnect()

        if not args.quiet and log_paths:
            print("\nLog files:")
            for path in log_paths:
                print(f"  {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
