"""Device connection abstraction (Clean Architecture Data Source Contract).

Kotlin / Android Comparison:
- `NetworkDeviceConnector(ABC)` with `@abstractmethod` is the Python equivalent of
  a Kotlin `interface NetworkDeviceConnector`.
- Concrete implementations include:
  1. `SimulatedIosXeDevice` (Phase 3–4: deterministic offline simulation).
  2. `PyAtsRealDeviceConnector` (Phase 5: real Cisco DevNet Sandbox via Unicon/SSH).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from network_health.core.models import DeviceSnapshot


class NetworkDeviceConnector(ABC):
    """Abstract contract for inspecting a network device (simulated or real)."""

    @property
    @abstractmethod
    def hostname(self) -> str:
        """Return target device hostname."""

    @property
    @abstractmethod
    def os_type(self) -> str:
        """Return target Network OS identifier (e.g. 'iosxe')."""

    @property
    @abstractmethod
    def is_simulated(self) -> bool:
        """Return True if this connector is an offline simulation, False for real hardware."""

    @abstractmethod
    def connect(self) -> None:
        """Establish session to the device (or initialize offline simulation state)."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close active session cleanly."""

    @abstractmethod
    def execute_command(self, command: str) -> str:
        """Execute a show command and return raw CLI text output."""

    @abstractmethod
    def collect_snapshot(self) -> DeviceSnapshot:
        """Collect interfaces and routes and return a structured DeviceSnapshot."""
