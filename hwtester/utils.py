"""Shared utilities for checksum calculation and timestamps."""

import datetime


def calculate_intel_hex_checksum(data_bytes: bytes) -> int:
    """
    Calculate Intel Hex checksum.

    The checksum is the two's complement of the sum of all bytes
    in the record (excluding the colon and checksum itself).

    Args:
        data_bytes: The bytes to checksum (everything after ':' and before checksum)

    Returns:
        Single byte checksum value (0-255)
    """
    total = sum(data_bytes)
    checksum = (~total + 1) & 0xFF
    return checksum


def format_timestamp(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """Return current timestamp formatted for filenames."""
    return datetime.datetime.now().strftime(fmt)


def format_line_timestamp() -> str:
    """Return timestamp for log line prefixing."""
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "] "
