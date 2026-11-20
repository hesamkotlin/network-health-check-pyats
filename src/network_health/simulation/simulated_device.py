"""Deterministic Offline Network Device Simulator for Phase 3 & Phase 4.

CRITICAL ARCHITECTURE RULE (Rules 6 & 7):
- This simulator provides repeatable offline Cisco IOS-XE CLI command outputs
  from local JSON fixture files so developers can learn and run pyATS + Genie
  tests without physical hardware or a Cisco DevNet VPN/SSH session.
- It NEVER pretends to be a live router socket (`is_simulated` is always `True`).
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path

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
    parse_cli_with_genie,
)

logger = logging.getLogger(__name__)


class SimulationScenario(str, Enum):
    """Pre-defined deterministic simulation scenarios."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"


class SimulatedIosXeDevice(NetworkDeviceConnector):
    """Offline simulated Cisco IOS-XE router backed by deterministic CLI fixtures."""

    def __init__(
        self,
        hostname: str = "sim-rtr-core-01",
        scenario: SimulationScenario = SimulationScenario.HEALTHY,
        fixture_path: str | Path | None = None,
    ) -> None:
        self._hostname = hostname
        self._os_type = "iosxe"
        self._scenario = scenario
        self._connected = False
        self._fixture_path = (
            Path(fixture_path)
            if fixture_path is not None
            else self._default_fixture_path(scenario)
        )
        self._commands: dict[str, str] = {}

    @staticmethod
    def _default_fixture_path(scenario: SimulationScenario) -> Path:
        project_root = Path(__file__).resolve().parents[3]
        if scenario == SimulationScenario.UNHEALTHY:
            return project_root / "test_data" / "iosxe_unhealthy_outputs.json"
        return project_root / "test_data" / "iosxe_healthy_outputs.json"

    @property
    def hostname(self) -> str:
        return self._hostname

    @property
    def os_type(self) -> str:
        return self._os_type

    @property
    def is_simulated(self) -> bool:
        return True

    @property
    def scenario(self) -> SimulationScenario:
        return self._scenario

    def connect(self) -> None:
        """Load offline CLI fixtures or simulate connection failure if UNREACHABLE."""
        if self._scenario == SimulationScenario.UNREACHABLE:
            self._connected = False
            raise DeviceConnectionError(
                f"[SIMULATED] Connection timed out to offline device '{self._hostname}' "
                f"(scenario={self._scenario.value})."
            )

        if not self._fixture_path.exists():
            raise ConfigurationError(
                f"Simulation fixture file not found: {self._fixture_path}"
            )

        try:
            with self._fixture_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"Invalid JSON in simulation fixture '{self._fixture_path}': {exc}"
            ) from exc

        commands = payload.get("commands")
        if not isinstance(commands, dict):
            raise ConfigurationError(
                f"Simulation fixture '{self._fixture_path}' is missing 'commands' map."
            )

        self._commands = {str(k): str(v) for k, v in commands.items()}
        self._connected = True
        logger.info(
            "Initialized SimulatedIosXeDevice(hostname='%s', scenario='%s', fixture='%s')",
            self._hostname,
            self._scenario.value,
            self._fixture_path.name,
        )

    def disconnect(self) -> None:
        """Reset simulated connection state."""
        self._connected = False

    def execute_command(self, command: str) -> str:
        """Return pre-recorded CLI string for `command`."""
        if not self._connected:
            raise DeviceConnectionError(
                f"[SIMULATED] Cannot execute '{command}': device '{self._hostname}' is not connected."
            )

        normalized = command.strip()
        if normalized not in self._commands:
            raise CommandExecutionError(
                f"[SIMULATED] Command '{normalized}' is not defined in fixture '{self._fixture_path.name}'."
            )

        return self._commands[normalized]

    def collect_snapshot(self) -> DeviceSnapshot:
        """Execute show commands, parse outputs via Cisco Genie, and build a DeviceSnapshot."""
        if self._scenario == SimulationScenario.UNREACHABLE:
            return DeviceSnapshot(
                hostname=self._hostname,
                os_type=self._os_type,
                is_simulated=True,
                reachable=False,
            )

        if not self._connected:
            self.connect()

        raw_interfaces = self.execute_command("show interfaces")
        raw_routes = self.execute_command("show ip route")

        parsed_interfaces = parse_cli_with_genie(
            hostname=self._hostname,
            command="show interfaces",
            raw_output=raw_interfaces,
            os_type=self._os_type,
        )
        parsed_routes = parse_cli_with_genie(
            hostname=self._hostname,
            command="show ip route",
            raw_output=raw_routes,
            os_type=self._os_type,
        )

        interfaces = extract_interfaces_from_genie(parsed_interfaces)
        routes = extract_routes_from_genie(parsed_routes)

        return DeviceSnapshot(
            hostname=self._hostname,
            os_type=self._os_type,
            is_simulated=True,
            reachable=True,
            interfaces=interfaces,
            routes=routes,
        )
