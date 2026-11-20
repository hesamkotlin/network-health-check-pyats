"""Domain exceptions for the Network Health Check Automation System.

In Kotlin/Android terms, this hierarchy is similar to a sealed exception hierarchy
in the Domain layer so callers can catch specific failure categories explicitly.
"""

from __future__ import annotations


class NetworkHealthError(Exception):
    """Base exception for all domain and execution errors in Network Health Check."""


class ConfigurationError(NetworkHealthError):
    """Raised when configuration or expected state files are missing or invalid."""


class DeviceConnectionError(NetworkHealthError):
    """Raised when a device (simulated or real) cannot be reached or connected."""


class CommandExecutionError(NetworkHealthError):
    """Raised when a CLI command fails or returns an unparseable response."""


class ValidationError(NetworkHealthError):
    """Raised when actual device state does not match expected network health rules."""
