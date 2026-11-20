"""Core domain models, configuration loaders, and state validators."""

from __future__ import annotations

from network_health.core.config import load_health_policy, parse_health_policy_dict
from network_health.core.exceptions import (
    CommandExecutionError,
    ConfigurationError,
    DeviceConnectionError,
    NetworkHealthError,
    ValidationError,
)
from network_health.core.models import (
    CheckAssertionResult,
    DeviceSnapshot,
    ExpectedDeviceHealthPolicy,
    ExpectedInterfaceRule,
    ExpectedRouteRule,
    HealthCheckReport,
    InterfaceAdminStatus,
    InterfaceOperStatus,
    RouteEntry,
    TestOutcome,
)
from network_health.core.validators import (
    evaluate_device_health,
    validate_device_availability,
    validate_interface_ip,
    validate_interface_status,
    validate_route_entry,
)

__all__ = [
    "CheckAssertionResult",
    "CommandExecutionError",
    "ConfigurationError",
    "DeviceConnectionError",
    "DeviceSnapshot",
    "ExpectedDeviceHealthPolicy",
    "ExpectedInterfaceRule",
    "ExpectedRouteRule",
    "HealthCheckReport",
    "InterfaceAdminStatus",
    "InterfaceOperStatus",
    "NetworkHealthError",
    "RouteEntry",
    "TestOutcome",
    "ValidationError",
    "evaluate_device_health",
    "load_health_policy",
    "parse_health_policy_dict",
    "validate_device_availability",
    "validate_interface_ip",
    "validate_interface_status",
    "validate_route_entry",
]
