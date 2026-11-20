"""Unit and integration tests for Phases 5, 6, and 7 (Real Device config, SQLite/Service, Concurrency)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from network_health.api.app import HealthCheckExecutionService
from network_health.core.concurrency import (
    DeviceCheckTarget,
    run_checks_with_asyncio,
    run_checks_with_multiprocessing,
    run_checks_with_threading,
)
from network_health.core.exceptions import ConfigurationError
from network_health.core.models import TestOutcome
from network_health.database.repository import SQLiteHealthRepository
from network_health.devices.real_device import (
    PyAtsRealDeviceConnector,
    validate_real_device_env_vars,
)
from network_health.simulation.simulated_device import SimulationScenario

PROJECT_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = PROJECT_ROOT / "test_data" / "expected_health_policy.yaml"
TESTBED_PATH = PROJECT_ROOT / "testbed" / "devices.yaml.example"


# ---------------------------------------------------------------------------
# Phase 5 Tests: Real Cisco Device Connector & Environment Security Validation
# ---------------------------------------------------------------------------
def test_real_device_connector_rejects_missing_or_placeholder_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify real device mode never connects with missing or placeholder credentials."""
    monkeypatch.setenv("CISCO_SANDBOX_HOST", "sandbox-iosxe-latest-1.cisco.com")
    monkeypatch.setenv("CISCO_SANDBOX_PORT", "22")
    monkeypatch.setenv("CISCO_SANDBOX_USERNAME", "replace_with_sandbox_username")
    monkeypatch.setenv("CISCO_SANDBOX_PASSWORD", "")

    with pytest.raises(ConfigurationError):
        validate_real_device_env_vars()

    connector = PyAtsRealDeviceConnector(
        hostname="sim-rtr-core-01",
        testbed_path=TESTBED_PATH,
    )
    assert connector.is_simulated is False
    with pytest.raises(ConfigurationError):
        connector.connect()


# ---------------------------------------------------------------------------
# Phase 6 Tests: SQLite Persistence & Execution Service Layer
# ---------------------------------------------------------------------------
def test_sqlite_repository_and_execution_service(tmp_path: Path) -> None:
    """Verify starting test runs, querying status, full results, and execution history in SQLite."""
    db_file = tmp_path / "test_history.db"
    repo = SQLiteHealthRepository(db_path=db_file)
    service = HealthCheckExecutionService(repository=repo, policy_path=POLICY_PATH)

    healthy_run = service.start_test_run(hostname="sim-rtr-core-01", scenario="healthy")
    unhealthy_run = service.start_test_run(hostname="sim-rtr-core-01", scenario="unhealthy")

    run_id = healthy_run["run_id"]
    status = service.get_run_status(run_id)
    assert status is not None
    assert status["status"] == "COMPLETED"
    assert status["overall_outcome"] == "PASS"
    assert status["summary"]["passed"] == 10

    full_result = service.get_run_results(unhealthy_run["run_id"])
    assert full_result is not None
    assert full_result["overall_outcome"] == "FAIL"
    assert full_result["summary"]["failed"] == 5

    history = service.get_run_history(limit=10)
    assert len(history) == 2


# ---------------------------------------------------------------------------
# Phase 7 Tests: Concurrency (Threading, Multiprocessing, Asyncio & Isolation)
# ---------------------------------------------------------------------------
def _sample_multi_device_targets() -> list[DeviceCheckTarget]:
    return [
        DeviceCheckTarget(
            hostname="sim-rtr-core-01",
            policy_path=POLICY_PATH,
            scenario=SimulationScenario.HEALTHY,
        ),
        DeviceCheckTarget(
            hostname="sim-rtr-core-01",
            policy_path=POLICY_PATH,
            scenario=SimulationScenario.UNHEALTHY,
        ),
        DeviceCheckTarget(
            hostname="sim-rtr-core-01",
            policy_path=POLICY_PATH,
            scenario=SimulationScenario.UNREACHABLE,
        ),
    ]


def test_concurrent_device_checks_with_threading() -> None:
    """Verify ThreadPoolExecutor runs multiple device scenarios concurrently with error isolation."""
    targets = _sample_multi_device_targets()
    reports = run_checks_with_threading(targets, max_workers=3)

    assert len(reports) == 3
    outcomes = [r.overall_outcome for r in reports]
    assert outcomes == [TestOutcome.PASS, TestOutcome.FAIL, TestOutcome.FAIL]


def test_concurrent_device_checks_with_multiprocessing() -> None:
    """Verify ProcessPoolExecutor runs device checks across independent OS processes."""
    targets = _sample_multi_device_targets()[:2]
    reports = run_checks_with_multiprocessing(targets, max_workers=2)

    assert len(reports) == 2
    assert [r.overall_outcome for r in reports] == [TestOutcome.PASS, TestOutcome.FAIL]


def test_concurrent_device_checks_with_asyncio() -> None:
    """Verify asyncio.gather + asyncio.to_thread executes synchronous checks without blocking."""
    targets = _sample_multi_device_targets()
    reports = asyncio.run(run_checks_with_asyncio(targets))

    assert len(reports) == 3
    assert [r.overall_outcome for r in reports] == [
        TestOutcome.PASS,
        TestOutcome.FAIL,
        TestOutcome.FAIL,
    ]
