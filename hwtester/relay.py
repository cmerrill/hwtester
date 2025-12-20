"""Relay controller with Intel Hex protocol support."""

import threading
from typing import Optional

import serial

from .utils import calculate_intel_hex_checksum


class RelayController:
    """
    Controls relay board via serial port using Intel Hex format commands.

    Protocol format: :FE0500[XX][YY]00[ZZ]<CRLF>
    - FE = record type marker
    - 05 = byte count
    - 00 = address high byte
    - XX = relay number (00-0F)
    - YY = state (FF=ON, 00=OFF)
    - 00 = padding
    - ZZ = checksum

    Thread-safe for concurrent access.
    """

    RELAY_ON = 0xFF
    RELAY_OFF = 0x00
    MIN_RELAY = 0
    MAX_RELAY = 15

    def __init__(self, port: str, timeout: float = 1.0):
        """
        Initialize relay controller.

        Args:
            port: Serial port name (e.g., 'COM3' or '/dev/ttyUSB0')
            timeout: Serial read timeout in seconds
        """
        self.port = port
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        """
        Open serial connection to relay board.

        Raises:
            serial.SerialException: If port cannot be opened
        """
        self._serial = serial.Serial(
            port=self.port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
        )

    def disconnect(self) -> None:
        """Close serial connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def _build_command(self, relay_num: int, state: int) -> bytes:
        """
        Build Intel Hex format command for relay control.

        Args:
            relay_num: Relay number (0-15)
            state: RELAY_ON (0xFF) or RELAY_OFF (0x00)

        Returns:
            Complete command bytes including CRLF
        """
        # Build the data portion: FE 05 00 [relay] [state] 00
        data_bytes = bytes([0xFE, 0x05, 0x00, relay_num, state, 0x00])
        checksum = calculate_intel_hex_checksum(data_bytes)

        # Format as Intel Hex string
        hex_str = "".join(f"{b:02X}" for b in data_bytes)
        command = f":{hex_str}{checksum:02X}\r\n"
        return command.encode("ascii")

    def set_relay(self, relay_num: int, on: bool) -> None:
        """
        Set relay state.

        Args:
            relay_num: Relay number (0-15)
            on: True for ON, False for OFF

        Raises:
            ValueError: If relay number is out of range
            RuntimeError: If not connected
            serial.SerialException: On communication error
        """
        if not self.MIN_RELAY <= relay_num <= self.MAX_RELAY:
            raise ValueError(
                f"Relay number must be {self.MIN_RELAY}-{self.MAX_RELAY}, got {relay_num}"
            )

        if not self._serial or not self._serial.is_open:
            raise RuntimeError("Not connected to relay board")

        state = self.RELAY_ON if on else self.RELAY_OFF
        command = self._build_command(relay_num, state)

        with self._lock:
            self._serial.write(command)
            self._serial.flush()

    def relay_on(self, relay_num: int) -> None:
        """Turn relay ON."""
        self.set_relay(relay_num, on=True)

    def relay_off(self, relay_num: int) -> None:
        """Turn relay OFF."""
        self.set_relay(relay_num, on=False)

    def send_raw(self, data: bytes) -> None:
        """
        Send raw bytes to relay port (for debugging/advanced use).

        Args:
            data: Raw bytes to send
        """
        if not self._serial or not self._serial.is_open:
            raise RuntimeError("Not connected to relay board")

        with self._lock:
            self._serial.write(data)
            self._serial.flush()

    def __enter__(self) -> "RelayController":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
