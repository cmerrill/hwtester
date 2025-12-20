"""Threaded DUT serial port logging."""

import threading
from pathlib import Path
from typing import Optional, TextIO

import serial

from .utils import format_timestamp, format_line_timestamp


class DUTLogger:
    """
    Logs serial output from a DUT port to a file.

    Runs in a background thread, reading from serial and writing to log file.
    Thread-safe start/stop operations.
    """

    def __init__(
        self,
        port: str,
        log_dir: Path,
        baud_rate: int = 115200,
        timestamp_lines: bool = False,
        port_name: Optional[str] = None,
        log_prefix: Optional[str] = None,
    ):
        """
        Initialize DUT logger.

        Args:
            port: Serial port name
            log_dir: Directory to write log files
            baud_rate: Serial baud rate (default 115200)
            timestamp_lines: If True, prepend timestamp to each line
            port_name: Friendly name for log file (defaults to port name)
            log_prefix: Prefix to prepend to log filenames
        """
        self.port = port
        self.log_dir = Path(log_dir)
        self.baud_rate = baud_rate
        self.timestamp_lines = timestamp_lines
        self.port_name = port_name or port.replace("/", "_").replace("\\", "_").replace(":", "")
        self.log_prefix = log_prefix

        self._serial: Optional[serial.Serial] = None
        self._log_file: Optional[TextIO] = None
        self._log_path: Optional[Path] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def _generate_log_filename(self) -> Path:
        """Generate log filename with timestamp."""
        timestamp = format_timestamp()
        if self.log_prefix:
            filename = f"{self.log_prefix}{self.port_name}_{timestamp}.log"
        else:
            filename = f"{self.port_name}_{timestamp}.log"
        return self.log_dir / filename

    def _log_loop(self) -> None:
        """Main logging loop running in background thread."""
        buffer = b""

        while not self._stop_event.is_set():
            try:
                # Read available data with timeout
                if self._serial and self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    buffer += data

                    # Process complete lines
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        # Strip \r and whitespace from line endings
                        decoded_line = line.decode("utf-8", errors="replace").rstrip()
                        self._write_line(decoded_line)
                else:
                    # Small sleep to prevent busy-waiting
                    self._stop_event.wait(timeout=0.01)

            except serial.SerialException as e:
                self._write_line(f"[SERIAL ERROR: {e}]")
                break

        # Flush remaining buffer
        if buffer:
            self._write_line(buffer.decode("utf-8", errors="replace"))

    def _write_line(self, line: str) -> None:
        """Write a line to log file with optional timestamp."""
        with self._lock:
            if self._log_file:
                if self.timestamp_lines:
                    line = format_line_timestamp() + line
                self._log_file.write(line + "\n")
                self._log_file.flush()

    def start(self) -> Path:
        """
        Start logging.

        Returns:
            Path to the log file

        Raises:
            serial.SerialException: If port cannot be opened
            OSError: If log directory cannot be created
        """
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Open log file
        self._log_path = self._generate_log_filename()
        self._log_file = open(self._log_path, "w", encoding="utf-8")

        # Open serial port
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baud_rate,
            timeout=0.1,
        )

        # Start logging thread
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._log_loop, daemon=True)
        self._thread.start()

        return self._log_path

    def stop(self) -> None:
        """Stop logging and close resources."""
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None

        with self._lock:
            if self._log_file:
                self._log_file.close()
                self._log_file = None

    @property
    def log_path(self) -> Optional[Path]:
        """Return the current log file path."""
        return self._log_path

    def __enter__(self) -> "DUTLogger":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


class DUTLoggerManager:
    """Manages multiple DUT loggers."""

    def __init__(self):
        self._loggers: list[DUTLogger] = []

    def add_logger(self, logger: DUTLogger) -> None:
        """Add a logger to manage."""
        self._loggers.append(logger)

    def start_all(self) -> list[Path]:
        """Start all loggers, return list of log file paths."""
        paths = []
        for logger in self._loggers:
            try:
                path = logger.start()
                paths.append(path)
                print(f"Logging {logger.port} -> {path}")
            except serial.SerialException as e:
                print(f"Warning: Could not open {logger.port}: {e}")
        return paths

    def stop_all(self) -> None:
        """Stop all loggers."""
        for logger in self._loggers:
            logger.stop()

    def __enter__(self) -> "DUTLoggerManager":
        self.start_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop_all()
