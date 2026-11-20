"""Configuration loader for Expected Device Health Policies (YAML / Dict)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from network_health.core.exceptions import ConfigurationError
from network_health.core.models import (
    ExpectedDeviceHealthPolicy,
    ExpectedInterfaceRule,
    ExpectedRouteRule,
    InterfaceAdminStatus,
    InterfaceOperStatus,
)


def parse_health_policy_dict(raw_data: dict[str, Any]) -> ExpectedDeviceHealthPolicy:
    """Validate and convert a raw dictionary into an ExpectedDeviceHealthPolicy."""
    if not isinstance(raw_data, dict):
        raise ConfigurationError("Health policy configuration must be a YAML/JSON mapping.")

    device_section = raw_data.get("device")
    if not isinstance(device_section, dict):
        raise ConfigurationError("Missing required 'device' section in health policy.")

    hostname = device_section.get("hostname")
    os_type = device_section.get("os_type", "iosxe")
    if not hostname or not isinstance(hostname, str):
        raise ConfigurationError("Device 'hostname' must be a non-empty string.")

    raw_interfaces = raw_data.get("expected_interfaces", [])
    if not isinstance(raw_interfaces, list) or not raw_interfaces:
        raise ConfigurationError("'expected_interfaces' must be a non-empty list.")

    interface_rules: list[ExpectedInterfaceRule] = []
    for item in raw_interfaces:
        try:
            interface_rules.append(
                ExpectedInterfaceRule(
                    name=str(item["name"]),
                    expected_admin_status=InterfaceAdminStatus(
                        str(item.get("admin_status", "up")).lower()
                    ),
                    expected_oper_status=InterfaceOperStatus(
                        str(item.get("oper_status", "up")).lower()
                    ),
                    expected_ip_address=item.get("ip_address"),
                    expected_prefix_length=(
                        int(item["prefix_length"])
                        if item.get("prefix_length") is not None
                        else None
                    ),
                )
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise ConfigurationError(f"Invalid interface rule definition: {item}") from exc

    raw_routes = raw_data.get("expected_routes", [])
    if not isinstance(raw_routes, list):
        raise ConfigurationError("'expected_routes' must be a list.")

    route_rules: list[ExpectedRouteRule] = []
    for item in raw_routes:
        try:
            route_rules.append(
                ExpectedRouteRule(
                    prefix=str(item["prefix"]),
                    expected_protocol=item.get("protocol"),
                    expected_next_hop=item.get("next_hop"),
                    expected_outgoing_interface=item.get("outgoing_interface"),
                    must_be_active=bool(item.get("must_be_active", True)),
                )
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise ConfigurationError(f"Invalid route rule definition: {item}") from exc

    return ExpectedDeviceHealthPolicy(
        hostname=hostname,
        os_type=str(os_type),
        interfaces=tuple(interface_rules),
        routes=tuple(route_rules),
    )


def load_health_policy(policy_path: str | Path) -> ExpectedDeviceHealthPolicy:
    """Load an ExpectedDeviceHealthPolicy from a YAML file on disk."""
    path = Path(policy_path)
    if not path.exists():
        raise ConfigurationError(f"Health policy file does not exist: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            raw_data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Failed to parse YAML policy file '{path}': {exc}") from exc

    if raw_data is None:
        raise ConfigurationError(f"Health policy file '{path}' is empty.")

    return parse_health_policy_dict(raw_data)
