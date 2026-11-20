"""Real Cisco Device Connector using pyATS Testbed, Unicon SSH, and Genie.

PHASE 5 ARCHITECTURE RULES (Rules 6, 7, 8, 10):
- Strictly separated from `SimulatedIosXeDevice`.
- `is_simulated` is always `False`.
- Never hardcodes credentials or connection parameters; requires environment
  variables (`CISCO_SANDBOX_HOST`, `CISCO_SANDBOX_PORT`, `CISCO_SANDBOX_USERNAME`,
  `CISCO_SANDBOX_PASSWORD`) resolved by pyATS Testbed `%ENV{...}` markup.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from pyats.topology import loader as topology_loader

from network_health.core.exceptions import (
    CommandExecutionError,
    ConfigurationError,
    DeviceConnectionError,
)
from network_health.core.models import DeviceSnapshot
from network_health.devices.base import NetworkDeviceConnector
from network_health.simulation.genie_parser import (
    extract_interfaces_from_genie,
    extract_routes_from_genie,
)

logger = logging.getLogger(__name__)

REQUIRED_SANDBOX_ENV_VARS: tuple[str, ...] = (
    "CISCO_SANDBOX_HOST",
    "CISCO_SANDBOX_PORT",
    "CISCO_SANDBOX_USERNAME",
    "CISCO_SANDBOX_PASSWORD",
)


def validate_real_device_env_vars() -> None:
    """Ensure required Cisco DevNet Sandbox environment variables are set and non-placeholder."""
    missing: list[str] = []
    for var_name in REQUIRED_SANDBOX_ENV_VARS:
        val = os.environ.get(var_name, "").strip()
        if not val or val.startswith("replace_with_"):
            missing.append(var_name)

    if missing:
        raise ConfigurationError(
            "Missing or placeholder environment variables for real Cisco device connection: "
            f"{', '.join(missing)}. Set them in your environment or .env before using real mode."
        )


class PyAtsRealDeviceConnector(NetworkDeviceConnector):
    """Connects to a real Cisco IOS-XE device via pyATS Testbed and Unicon SSH."""

    def __init__(
        self,
        hostname: str,
        testbed_path: str | Path,
        os_type: str = "iosxe",
        connection_timeout_seconds: int = 30,
    ) -> None:
        self._hostname = hostname
        self._os_type = os_type
        self._testbed_path = Path(testbed_path)
        self._timeout = connection_timeout_seconds
        self._pyats_device: Any = None

    @property
    def hostname(self) -> str:
        return self._hostname

    @property
    def os_type(self) -> str:
        return self._os_type

    @property
    def is_simulated(self) -> bool:
        return False

    def _load_pyats_device(self) -> Any:
        validate_real_device_env_vars()
        if not self._testbed_path.exists():
            raise ConfigurationError(
                f"pyATS testbed file not found: {self._testbed_path}"
            )

        testbed = topology_loader.load(str(self._testbed_path))
        if self._hostname not in testbed.devices:
            raise ConfigurationError(
                f"Device '{self._hostname}' not found in testbed '{testbed.name}'."
            )
        return testbed.devices[self._hostname]

    def connect(self) -> None:
        """Open a real Unicon SSH session to the Cisco device."""
        device = self._load_pyats_device()
        try:
            logger.info(
                "Connecting to real Cisco device '%s' via Unicon SSH (timeout=%ds)...",
                self._hostname,
                self._timeout,
            )
            device.connect(
                learn_hostname=True,
                init_exec_commands=[],
                init_config_commands=[],
                log_stdout=False,
                connection_timeout=self._timeout,
            )
            self._pyats_device = device
        except Exception as exc:
            raise DeviceConnectionError(
                f"Failed to establish Unicon SSH session to '{self._hostname}': {exc}"
            ) from exc

    def disconnect(self) -> None:
        """Disconnect active Unicon SSH session cleanly."""
        if self._pyats_device is not None and getattr(
            self._pyats_device, "connected", False
        ):
            try:
                self._pyats_device.disconnect()
            finally:
                self._pyats_device = None

    def execute_command(self, command: str) -> str:
        """Execute a raw CLI show command over the active Unicon SSH connection."""
        if self._pyats_device is None or not getattr(
            self._pyats_device, "connected", False
        ):
            raise DeviceConnectionError(
                f"Real device '{self._hostname}' is not connected."
            )
        try:
            output: str = self._pyats_device.execute(command, timeout=self._timeout)
            return output
        except Exception as exc:
            raise CommandExecutionError(
                f"Failed to execute command '{command}' on real device '{self._hostname}': {exc}"
            ) from exc

    def collect_snapshot(self) -> DeviceSnapshot:
        """Parse live device state via Genie over Unicon SSH and return a DeviceSnapshot."""
        if self._pyats_device is None:
            try:
                self.connect()
            except DeviceConnectionError:
                return DeviceSnapshot(
                    hostname=self._hostname,
                    os_type=self._os_type,
                    is_simulated=False,
                    reachable=False,
                )

        try:
            parsed_interfaces: dict[str, Any] = self._pyats_device.parse(
                "show interfaces"
            )
            parsed_routes: dict[str, Any] = self._pyats_device.parse("show ip route")
        except Exception as exc:
            raise CommandExecutionError(
                f"Genie live parse failed on real device '{self._hostname}': {exc}"
            ) from exc

        interfaces = extract_interfaces_from_genie(parsed_interfaces)
        routes = extract_routes_from_genie(parsed_routes)

        return DeviceSnapshot(
            hostname=self._hostname,
            os_type=self._os_type,
            is_simulated=False,
            reachable=True,
            interfaces=interfaces,
            routes=routes,
        )
