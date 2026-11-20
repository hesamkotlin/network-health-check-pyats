"""Core domain models for the Network Health Check Automation System.

Kotlin / Android Comparison:
- `@dataclass(frozen=True)` in Python is equivalent to an immutable `data class` in Kotlin
  where all properties are declared with `val`.
- `Enum` in Python is equivalent to `enum class` in Kotlin.
- `from __future__ import annotations` allows modern union syntax (`str | None`)
  even on Python 3.9.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class InterfaceAdminStatus(str, Enum):
    """Administrative state of a network interface (e.g. 'up' or 'administratively down')."""

    UP = "up"
    DOWN = "down"


class InterfaceOperStatus(str, Enum):
    """Operational (line protocol) status of a network interface."""

    UP = "up"
    DOWN = "down"


class TestOutcome(str, Enum):
    """Standard PASS / FAIL / ERROR outcome of a single health check assertion."""

    __test__ = False  # Prevents pytest from mistaking this Enum for a test class

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class InterfaceState:
    """Observed state of a single router interface.

    Kotlin equivalent:
        data class InterfaceState(
            val name: String,
            val ipAddress: String?,
            val prefixLength: Int?,
            val adminStatus: InterfaceAdminStatus,
            val operStatus: InterfaceOperStatus,
            val enabled: Boolean,
        )
    """

    name: str
    ip_address: str | None
    prefix_length: int | None
    admin_status: InterfaceAdminStatus
    oper_status: InterfaceOperStatus
    enabled: bool

    @property
    def is_healthy(self) -> bool:
        """Return True if the interface is administratively enabled and operationally UP."""
        return (
            self.enabled
            and self.admin_status == InterfaceAdminStatus.UP
            and self.oper_status == InterfaceOperStatus.UP
        )

    @property
    def cidr(self) -> str | None:
        """Return IP in CIDR notation (e.g. '192.168.1.1/24') if an IP is configured."""
        if self.ip_address and self.prefix_length is not None:
            return f"{self.ip_address}/{self.prefix_length}"
        return None


@dataclass(frozen=True)
class RouteEntry:
    """Observed IPv4 route entry from the router's routing table."""

    prefix: str
    protocol: str
    active: bool
    next_hop: str | None = None
    outgoing_interface: str | None = None
    administrative_distance: int | None = None
    metric: int | None = None


@dataclass(frozen=True)
class DeviceSnapshot:
    """Complete point-in-time snapshot of a router's observed state."""

    hostname: str
    os_type: str
    is_simulated: bool
    reachable: bool
    interfaces: dict[str, InterfaceState] = field(default_factory=dict)
    routes: dict[str, RouteEntry] = field(default_factory=dict)
    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class ExpectedInterfaceRule:
    """Expected state rule for a single network interface."""

    name: str
    expected_admin_status: InterfaceAdminStatus = InterfaceAdminStatus.UP
    expected_oper_status: InterfaceOperStatus = InterfaceOperStatus.UP
    expected_ip_address: str | None = None
    expected_prefix_length: int | None = None


@dataclass(frozen=True)
class ExpectedRouteRule:
    """Expected route rule in the device routing table."""

    prefix: str
    expected_protocol: str | None = None
    expected_next_hop: str | None = None
    expected_outgoing_interface: str | None = None
    must_be_active: bool = True


@dataclass(frozen=True)
class ExpectedDeviceHealthPolicy:
    """Complete expected network state policy for a target device."""

    hostname: str
    os_type: str
    interfaces: tuple[ExpectedInterfaceRule, ...]
    routes: tuple[ExpectedRouteRule, ...]

    @property
    def required_interface_names(self) -> set[str]:
        """Return a Set of interface names that must exist on the device."""
        return {rule.name for rule in self.interfaces}

    @property
    def required_route_prefixes(self) -> set[str]:
        """Return a Set of route prefixes that must exist in the routing table."""
        return {rule.prefix for rule in self.routes}


@dataclass(frozen=True)
class CheckAssertionResult:
    """Result of evaluating a single expected vs actual health check rule."""

    check_name: str
    category: str
    outcome: TestOutcome
    expected: str
    actual: str
    message: str


@dataclass(frozen=True)
class HealthCheckReport:
    """Aggregated report for an entire device health check run."""

    run_id: str
    device_hostname: str
    is_simulated: bool
    scenario_name: str
    overall_outcome: TestOutcome
    results: tuple[CheckAssertionResult, ...]
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def passed_count(self) -> int:
        return sum(1 for item in self.results if item.outcome == TestOutcome.PASS)

    @property
    def failed_count(self) -> int:
        return sum(
            1
            for item in self.results
            if item.outcome in (TestOutcome.FAIL, TestOutcome.ERROR)
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize report into a JSON-compatible dictionary."""
        return {
            "run_id": self.run_id,
            "device_hostname": self.device_hostname,
            "is_simulated": self.is_simulated,
            "scenario_name": self.scenario_name,
            "overall_outcome": self.overall_outcome.value,
            "executed_at": self.executed_at,
            "summary": {
                "total": len(self.results),
                "passed": self.passed_count,
                "failed": self.failed_count,
            },
            "results": [
                {
                    "check_name": r.check_name,
                    "category": r.category,
                    "outcome": r.outcome.value,
                    "expected": r.expected,
                    "actual": r.actual,
                    "message": r.message,
                }
                for r in self.results
            ],
        }
