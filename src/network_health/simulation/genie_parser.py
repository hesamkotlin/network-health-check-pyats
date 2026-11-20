"""Cisco Genie CLI parser adapter for IOS-XE command outputs.

Important Technical Note on Genie Parsers:
1. Genie parsers are platform-specific (`os='iosxe'`, `os='nxos'`, `os='iosxr'`).
2. When running offline without an active SSH connection, we instantiate a
   `genie.conf.base.Device` (or invoke the specific `genie.libs.parser.iosxe`
   parser class with `output=raw_cli_output`) so Genie parses raw CLI strings
   into official Cisco structured dictionaries without opening any network socket.
"""

from __future__ import annotations

import logging
from typing import Any

from genie.conf.base import Device as GenieDevice
from genie.metaparser.util.exceptions import SchemaEmptyParserError

from network_health.core.exceptions import CommandExecutionError
from network_health.core.models import (
    InterfaceAdminStatus,
    InterfaceOperStatus,
    InterfaceState,
    RouteEntry,
)

logger = logging.getLogger(__name__)


def create_offline_genie_device(hostname: str, os_type: str = "iosxe") -> GenieDevice:
    """Create a Genie Device instance configured for offline CLI string parsing.

    Note: This object does NOT represent an active router connection. It provides
    the platform context (`os='iosxe'`) required by Genie's parser registry.
    """
    device = GenieDevice(name=hostname, os=os_type)
    device.custom.setdefault("abstraction", {})["order"] = ["os"]
    return device


def parse_cli_with_genie(
    hostname: str,
    command: str,
    raw_output: str,
    os_type: str = "iosxe",
) -> dict[str, Any]:
    """Parse raw Cisco CLI text using the official Genie parser for `command`.

    Args:
        hostname: Device hostname for Genie parser context.
        command: Exact Cisco CLI show command (e.g. 'show interfaces').
        raw_output: Raw CLI text captured from device or offline fixture.
        os_type: Network OS platform string (default: 'iosxe').

    Returns:
        Structured dictionary adhering to Cisco Genie's parser schema.

    Raises:
        CommandExecutionError: If Genie fails to parse the raw CLI output.
    """
    if not raw_output or not raw_output.strip():
        raise CommandExecutionError(f"Empty CLI output provided for command '{command}'.")

    genie_device = create_offline_genie_device(hostname=hostname, os_type=os_type)
    try:
        parsed: dict[str, Any] = genie_device.parse(command, output=raw_output)
        return parsed
    except SchemaEmptyParserError as exc:
        raise CommandExecutionError(
            f"Genie parser returned empty schema for command '{command}' on os='{os_type}'."
        ) from exc
    except Exception as exc:
        raise CommandExecutionError(
            f"Genie failed to parse command '{command}' on os='{os_type}': {exc}"
        ) from exc


def extract_interfaces_from_genie(
    parsed_show_interfaces: dict[str, Any],
) -> dict[str, InterfaceState]:
    """Convert Genie `show interfaces` dictionary into domain `InterfaceState` objects."""
    interfaces: dict[str, InterfaceState] = {}

    for iface_name, data in parsed_show_interfaces.items():
        if not isinstance(data, dict):
            continue

        enabled = bool(data.get("enabled", False))
        oper_raw = str(data.get("oper_status", "down")).lower()
        line_proto_raw = str(data.get("line_protocol", oper_raw)).lower()

        admin_status = (
            InterfaceAdminStatus.UP if enabled else InterfaceAdminStatus.DOWN
        )
        oper_status = (
            InterfaceOperStatus.UP
            if (oper_raw == "up" and line_proto_raw == "up")
            else InterfaceOperStatus.DOWN
        )

        ip_address: str | None = None
        prefix_length: int | None = None
        ipv4_block = data.get("ipv4")
        if isinstance(ipv4_block, dict):
            for cidr_or_ip, ip_info in ipv4_block.items():
                if isinstance(ip_info, dict) and "ip" in ip_info:
                    ip_address = str(ip_info["ip"])
                    if "prefix_length" in ip_info:
                        prefix_length = int(ip_info["prefix_length"])
                    break
                if "/" in str(cidr_or_ip):
                    ip_part, prefix_part = str(cidr_or_ip).split("/", 1)
                    ip_address = ip_part
                    prefix_length = int(prefix_part)
                    break

        interfaces[iface_name] = InterfaceState(
            name=iface_name,
            ip_address=ip_address,
            prefix_length=prefix_length,
            admin_status=admin_status,
            oper_status=oper_status,
            enabled=enabled,
        )

    return interfaces


def extract_routes_from_genie(
    parsed_show_ip_route: dict[str, Any],
) -> dict[str, RouteEntry]:
    """Convert Genie `show ip route` dictionary into domain `RouteEntry` objects."""
    routes: dict[str, RouteEntry] = {}

    vrf_map = parsed_show_ip_route.get("vrf", {})
    default_vrf = vrf_map.get("default", {})
    ipv4_af = default_vrf.get("address_family", {}).get("ipv4", {})
    raw_routes = ipv4_af.get("routes", {})

    for prefix, route_data in raw_routes.items():
        if not isinstance(route_data, dict):
            continue

        protocol = str(route_data.get("source_protocol", "unknown")).lower()
        active = bool(route_data.get("active", False))
        admin_distance = route_data.get("route_preference")
        metric = route_data.get("metric")

        next_hop: str | None = None
        outgoing_interface: str | None = None

        next_hop_block = route_data.get("next_hop", {})
        next_hop_list = next_hop_block.get("next_hop_list", {})
        if isinstance(next_hop_list, dict):
            for hop_info in next_hop_list.values():
                if isinstance(hop_info, dict):
                    if hop_info.get("next_hop"):
                        next_hop = str(hop_info["next_hop"])
                    if hop_info.get("outgoing_interface"):
                        outgoing_interface = str(hop_info["outgoing_interface"])
                    break

        outgoing_iface_map = next_hop_block.get("outgoing_interface", {})
        if outgoing_interface is None and isinstance(outgoing_iface_map, dict):
            for iface_key in outgoing_iface_map:
                outgoing_interface = str(iface_key)
                break

        routes[prefix] = RouteEntry(
            prefix=prefix,
            protocol=protocol,
            active=active,
            next_hop=next_hop,
            outgoing_interface=outgoing_interface,
            administrative_distance=(
                int(admin_distance) if admin_distance is not None else None
            ),
            metric=int(metric) if metric is not None else None,
        )

    return routes
