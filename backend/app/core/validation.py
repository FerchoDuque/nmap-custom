"""Strict input validation for scan targets, ports and schedule configs.

Kept free of network I/O: hostnames are validated syntactically and are not
resolved here. Used by API schemas before anything is queued or persisted.
"""

import ipaddress
import re
from typing import Any, Dict, Optional

from app.models.scan import ScanType

IPV4_LIKE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
HOSTNAME_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
PORT_TOKEN = re.compile(r"^(\d{1,5})(?:-(\d{1,5}))?$")

MAX_HOSTNAME_LENGTH = 253
MIN_PORT = 1
MAX_PORT = 65535
DEFAULT_MAX_HOSTS = 1024
DEFAULT_MAX_PORTS = 65535


def _host_count(network: ipaddress._BaseNetwork) -> int:
    """Usable host count without materializing large ranges."""
    if network.version == 4 and network.prefixlen < 31:
        return max(network.num_addresses - 2, 0)
    return network.num_addresses


def _is_valid_hostname(value: str) -> bool:
    if not value or len(value) > MAX_HOSTNAME_LENGTH:
        return False

    labels = value.rstrip(".").split(".")
    return bool(labels) and all(HOSTNAME_LABEL.match(label) for label in labels)


def normalize_target(value: Any, max_hosts: int = DEFAULT_MAX_HOSTS) -> str:
    """Return a stripped target or raise ``ValueError`` if unsupported.

    Accepted: IPv4/IPv6 address, CIDR range, dotted IPv4 range
    (``start-end``) and syntactically valid hostnames. Ranges larger than
    ``max_hosts`` are rejected instead of being silently truncated.
    """
    if not isinstance(value, str):
        raise ValueError("Target must be a string")

    target = value.strip()
    if not target:
        raise ValueError("Target cannot be empty")

    if "/" in target:
        address, _, prefix = target.partition("/")
        if not address or not prefix.isdigit():
            raise ValueError("Invalid CIDR prefix")
        try:
            network = ipaddress.ip_network(target, strict=False)
        except ValueError as exc:
            raise ValueError("Invalid CIDR range") from exc
        if _host_count(network) > max_hosts:
            raise ValueError(f"Target exceeds maximum of {max_hosts} hosts")
        return target

    if "-" in target and "." in target:
        start_text, _, end_text = target.partition("-")
        try:
            start = ipaddress.ip_address(start_text.strip())
            end = ipaddress.ip_address(end_text.strip())
        except ValueError:
            start = end = None

        if start is not None and end is not None:
            if start.version != end.version:
                raise ValueError("IP range endpoints must use the same family")
            if int(start) > int(end):
                raise ValueError("IP range end must not precede start")
            if int(end) - int(start) + 1 > max_hosts:
                raise ValueError(f"Target exceeds maximum of {max_hosts} hosts")
            return f"{start}-{end}"

    if IPV4_LIKE.match(target):
        try:
            ipaddress.IPv4Address(target)
        except ValueError as exc:
            raise ValueError("Invalid IPv4 address") from exc
        return target

    if ":" in target:
        try:
            ipaddress.IPv6Address(target)
        except ValueError as exc:
            raise ValueError("Invalid IPv6 address") from exc
        return target

    if not _is_valid_hostname(target):
        raise ValueError("Invalid target format")
    return target


def normalize_port_range(
    value: Any, max_ports: int = DEFAULT_MAX_PORTS
) -> Optional[str]:
    """Normalize a comma-separated port list/ranges, or return ``None``."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Port range must be a string")

    range_text = value.strip()
    if not range_text:
        return None

    normalized = []
    total_ports = 0
    for raw_token in range_text.split(","):
        token = raw_token.strip()
        if not token:
            raise ValueError("Empty port entry")

        match = PORT_TOKEN.match(token)
        if not match:
            raise ValueError("Use ports like 22,80,443 or ranges like 1-1000")

        start = int(match.group(1))
        end = int(match.group(2) or start)

        if start < MIN_PORT or start > MAX_PORT or end < MIN_PORT or end > MAX_PORT:
            raise ValueError("Ports must be between 1 and 65535")
        if end < start:
            raise ValueError("Invalid port range (end before start)")

        total_ports += end - start + 1
        if total_ports > max_ports:
            raise ValueError(f"Port range exceeds maximum of {max_ports} ports")

        normalized.append(f"{start}-{end}" if match.group(2) else str(start))

    return ",".join(normalized)


def normalize_scan_config(
    config: Any,
    max_hosts: int = DEFAULT_MAX_HOSTS,
    max_ports: int = DEFAULT_MAX_PORTS,
) -> Dict[str, Any]:
    """Validate and normalize a schedule ``scan_config`` payload."""
    if not isinstance(config, dict):
        raise ValueError("scan_config must be an object")
    if "target" not in config:
        raise ValueError("scan_config.target is required")

    normalized = dict(config)
    normalized["target"] = normalize_target(config["target"], max_hosts=max_hosts)

    if "scan_type" in config:
        try:
            normalized["scan_type"] = ScanType(config["scan_type"]).value
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unsupported scan_type: {config['scan_type']!r}") from exc

    if config.get("port_range") is not None:
        normalized["port_range"] = normalize_port_range(
            config["port_range"], max_ports=max_ports
        )

    return normalized
