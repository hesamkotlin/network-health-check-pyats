"""Unit and offline integration tests for Phases 1 through 4 (pytest)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from network_health.core.config import load_health_policy, parse_health_policy_dict
from network_health.core.exceptions import ConfigurationError, DeviceConnectionError
from network_health.core.models import (
    InterfaceAdminStatus,
    InterfaceOperStatus,
    TestOutcome,
)
from network_health.core.validators import evaluate_device_health
from network_health.reporting.reporter import (
    format_markdown_report,
    save_json_report,
    save_markdown_report,
)
from network_health.simulation.simulated_device import (
    SimulatedIosXeDevice,
    SimulationScenario,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = PROJECT_ROOT / "test_data" / "expected_health_policy.yaml"


def test_load_expected_health_policy_from_yaml() -> None:
    """Verify YAML policy loading and immutable dataclass properties."""
    policy = load_health_policy(POLICY_PATH)

    assert policy.hostname == "sim-rtr-core-01"
    assert policy.os_type == "iosxe"
    assert policy.required_interface_names == {
        "GigabitEthernet1",
        "GigabitEthernet2",
        "Loopback0",
    }
    assert policy.required_route_prefixes == {
        "0.0.0.0/0",
        "10.10.20.0/24",
        "172.16.10.0/24",
    }


def test_invalid_policy_raises_configuration_error() -> None:
    """Verify explicit exception handling for malformed policy dictionaries."""
    with pytest.raises(ConfigurationError):
        parse_health_policy_dict({"device": {"hostname": ""}})


def test_healthy_simulated_device_passes_all_checks(tmp_path: Path) -> None:
    """Verify Genie parsing and full PASS evaluation on healthy simulated IOS-XE outputs."""
    policy = load_health_policy(POLICY_PATH)
    device = SimulatedIosXeDevice(
        hostname=policy.hostname,
        scenario=SimulationScenario.HEALTHY,
    )
    device.connect()
    snapshot = device.collect_snapshot()
    device.disconnect()

    assert snapshot.is_simulated is True
    assert snapshot.reachable is True
    assert snapshot.interfaces["GigabitEthernet1"].is_healthy is True
    assert snapshot.interfaces["GigabitEthernet1"].cidr == "10.10.20.1/24"
    assert snapshot.routes["0.0.0.0/0"].next_hop == "10.10.20.254"

    report = evaluate_device_health(
        snapshot=snapshot,
        policy=policy,
        scenario_name="healthy",
    )

    assert report.overall_outcome == TestOutcome.PASS
    assert report.failed_count == 0
    assert report.passed_count == 10

    json_file = save_json_report(report, tmp_path)
    md_file = save_markdown_report(report, tmp_path)
    assert json_file.exists()
    assert md_file.exists()

    saved_payload = json.loads(json_file.read_text(encoding="utf-8"))
    assert saved_payload["overall_outcome"] == "PASS"
    assert "Offline Simulation" in format_markdown_report(report)


def test_unhealthy_simulated_device_detects_exact_failures() -> None:
    """Verify FAIL evaluation when an interface is down, IP drifted, and routes are missing."""
    policy = load_health_policy(POLICY_PATH)
    device = SimulatedIosXeDevice(
        hostname=policy.hostname,
        scenario=SimulationScenario.UNHEALTHY,
    )
    device.connect()
    snapshot = device.collect_snapshot()
    device.disconnect()

    assert (
        snapshot.interfaces["GigabitEthernet2"].admin_status
        == InterfaceAdminStatus.DOWN
    )
    assert (
        snapshot.interfaces["GigabitEthernet2"].oper_status
        == InterfaceOperStatus.DOWN
    )
    assert snapshot.interfaces["GigabitEthernet1"].cidr == "10.10.99.1/24"
    assert "0.0.0.0/0" not in snapshot.routes

    report = evaluate_device_health(
        snapshot=snapshot,
        policy=policy,
        scenario_name="unhealthy",
    )

    assert report.overall_outcome == TestOutcome.FAIL
    assert report.failed_count == 5
    failed_names = {
        r.check_name for r in report.results if r.outcome == TestOutcome.FAIL
    }
    assert failed_names == {
        "interface_ip[GigabitEthernet1]",
        "interface_status[GigabitEthernet2]",
        "route[0.0.0.0/0]",
        "route[10.10.20.0/24]",
        "route[172.16.10.0/24]",
    }


def test_unreachable_simulated_device_raises_connection_error() -> None:
    """Verify explicit DeviceConnectionError on connect() for unreachable scenario."""
    device = SimulatedIosXeDevice(
        hostname="sim-rtr-core-01",
        scenario=SimulationScenario.UNREACHABLE,
    )
    with pytest.raises(DeviceConnectionError):
        device.connect()

    snapshot = device.collect_snapshot()
    assert snapshot.reachable is False
