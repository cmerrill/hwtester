"""TOML configuration loading and validation."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Python 3.11+ has tomllib built-in
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class DUTPortConfig:
    """Configuration for a single DUT port."""

    port: str
    baud_rate: int = 115200
    name: Optional[str] = None


@dataclass
class Config:
    """Complete application configuration."""

    # Relay settings
    relay_port: Optional[str] = None
    relay_aliases: dict[str, int] = field(default_factory=dict)

    # DUT port settings
    dut_ports: list[DUTPortConfig] = field(default_factory=list)

    # Logging settings
    log_dir: Path = field(default_factory=lambda: Path("./logs"))
    timestamp_lines: bool = False

    # Sequence (for file mode)
    sequence: Optional[str] = None


def load_config(config_path: Path) -> Config:
    """
    Load configuration from TOML file.

    Args:
        config_path: Path to TOML config file

    Returns:
        Parsed Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        tomllib.TOMLDecodeError: If TOML is invalid
        ValueError: If config values are invalid
    """
    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    config = Config()

    # Relay port
    if "relay" in data:
        relay_section = data["relay"]
        config.relay_port = relay_section.get("port")

        # Load relay aliases
        if "aliases" in relay_section:
            aliases = relay_section["aliases"]
            for name, relay_num in aliases.items():
                if not isinstance(relay_num, int) or not 1 <= relay_num <= 16:
                    raise ValueError(f"Relay alias '{name}' has invalid relay number: {relay_num}")
                config.relay_aliases[name] = relay_num

    # DUT ports
    if "dut" in data:
        dut_section = data["dut"]

        # Can be a list of ports or a dict with port configs
        if "ports" in dut_section:
            for port_config in dut_section["ports"]:
                if isinstance(port_config, str):
                    config.dut_ports.append(DUTPortConfig(port=port_config))
                elif isinstance(port_config, dict):
                    config.dut_ports.append(
                        DUTPortConfig(
                            port=port_config["port"],
                            baud_rate=port_config.get("baud_rate", 115200),
                            name=port_config.get("name"),
                        )
                    )

    # Logging settings
    if "logging" in data:
        log_section = data["logging"]
        if "directory" in log_section:
            config.log_dir = Path(log_section["directory"])
        config.timestamp_lines = log_section.get("timestamp_lines", False)

    # Sequence
    if "sequence" in data:
        seq_section = data["sequence"]
        if "commands" in seq_section:
            # Can be string or list
            commands = seq_section["commands"]
            if isinstance(commands, list):
                config.sequence = ",".join(commands)
            else:
                config.sequence = commands

    return config


def merge_config_with_args(config: Config, args) -> Config:
    """
    Merge CLI arguments over config file values.

    CLI args take precedence over config file.
    """
    if hasattr(args, "relay_port") and args.relay_port:
        config.relay_port = args.relay_port

    if hasattr(args, "log_dir") and args.log_dir:
        config.log_dir = Path(args.log_dir)

    if hasattr(args, "dut_ports") and args.dut_ports:
        # CLI DUT ports override config
        baud_rate = getattr(args, "baud_rate", 115200) or 115200
        config.dut_ports = [DUTPortConfig(port=p, baud_rate=baud_rate) for p in args.dut_ports]

    if hasattr(args, "sequence") and args.sequence:
        config.sequence = args.sequence

    if hasattr(args, "timestamp_lines") and args.timestamp_lines:
        config.timestamp_lines = True

    return config
