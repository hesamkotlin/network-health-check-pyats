"""Multi-device Concurrency Engine for Network Health Check (Phase 7).

Covers three fundamental Python concurrency models (critical for technical interviews):
1. `Threading` (`ThreadPoolExecutor`):
   - Ideal for I/O-bound tasks (SSH sessions, network sockets, reading files).
   - Threads share the same memory space and are subject to the Python GIL (Global
     Interpreter Lock) for CPU bytecode, but the GIL is RELEASED during network/disk I/O!
2. `Multiprocessing` (`ProcessPoolExecutor`):
   - Ideal for CPU-bound tasks (heavy parsing of thousands of large CLI outputs).
   - Spawns separate OS processes, each with its own Python interpreter and GIL.
3. `Asyncio` (`asyncio.gather` + `asyncio.wait_for` + `asyncio.to_thread`):
   - Cooperative single-threaded event loop.
   - CRITICAL RULE: Running synchronous blocking code (like pyATS/Unicon orGenie
     parsing) directly inside an `async def` function blocks the entire event loop!
     We MUST offload synchronous functions to a worker thread via `asyncio.to_thread()`.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path

from network_health.core.config import load_health_policy
from network_health.core.models import (
    CheckAssertionResult,
    ExpectedDeviceHealthPolicy,
    HealthCheckReport,
    TestOutcome,
)
from network_health.core.validators import evaluate_device_health
from network_health.simulation.simulated_device import (
    SimulatedIosXeDevice,
    SimulationScenario,
)


@dataclass(frozen=True)
class DeviceCheckTarget:
    """Target specification for running a health check on a single device."""

    hostname: str
    policy_path: str | Path
    scenario: SimulationScenario = SimulationScenario.HEALTHY


def _build_error_report(
    target: DeviceCheckTarget,
    error_category: str,
    error_message: str,
) -> HealthCheckReport:
    """Isolate device failure/timeout into a safe HealthCheckReport without crashing peers."""
    return HealthCheckReport(
        run_id=f"err-{target.hostname}",
        device_hostname=target.hostname,
        is_simulated=True,
        scenario_name=target.scenario.value,
        overall_outcome=TestOutcome.ERROR,
        results=(
            CheckAssertionResult(
                check_name="concurrent_execution_guard",
                category=error_category,
                outcome=TestOutcome.ERROR,
                expected="completed_within_timeout",
                actual=error_category,
                message=error_message,
            ),
        ),
    )


def execute_single_device_check(target: DeviceCheckTarget) -> HealthCheckReport:
    """Synchronous worker function that checks one device and isolates errors."""
    try:
        base_policy = load_health_policy(target.policy_path)
        policy = ExpectedDeviceHealthPolicy(
            hostname=target.hostname,
            os_type=base_policy.os_type,
            interfaces=base_policy.interfaces,
            routes=base_policy.routes,
        )
        device = SimulatedIosXeDevice(
            hostname=target.hostname,
            scenario=target.scenario,
        )
        if target.scenario != SimulationScenario.UNREACHABLE:
            device.connect()
        snapshot = device.collect_snapshot()
        device.disconnect()

        return evaluate_device_health(
            snapshot=snapshot,
            policy=policy,
            scenario_name=target.scenario.value,
        )
    except Exception as exc:
        return _build_error_report(
            target=target,
            error_category="execution_exception",
            error_message=f"Device '{target.hostname}' check failed with exception: {exc}",
        )


def run_checks_with_threading(
    targets: list[DeviceCheckTarget],
    max_workers: int = 4,
    timeout_seconds: float = 15.0,
) -> list[HealthCheckReport]:
    """Run health checks concurrently across devices using ThreadPoolExecutor (I/O-bound)."""
    reports: list[HealthCheckReport] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(execute_single_device_check, target): target
            for target in targets
        }
        for future, target in future_map.items():
            try:
                report = future.result(timeout=timeout_seconds)
                reports.append(report)
            except FuturesTimeoutError:
                reports.append(
                    _build_error_report(
                        target=target,
                        error_category="connection_timeout",
                        error_message=(
                            f"Device '{target.hostname}' timed out after {timeout_seconds}s."
                        ),
                    )
                )
            except Exception as exc:
                reports.append(
                    _build_error_report(
                        target=target,
                        error_category="thread_error",
                        error_message=str(exc),
                    )
                )
    return reports


def run_checks_with_multiprocessing(
    targets: list[DeviceCheckTarget],
    max_workers: int = 2,
    timeout_seconds: float = 30.0,
) -> list[HealthCheckReport]:
    """Run health checks across separate OS processes using ProcessPoolExecutor (CPU-bound)."""
    reports: list[HealthCheckReport] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(execute_single_device_check, target): target
            for target in targets
        }
        for future, target in future_map.items():
            try:
                reports.append(future.result(timeout=timeout_seconds))
            except FuturesTimeoutError:
                reports.append(
                    _build_error_report(
                        target=target,
                        error_category="process_timeout",
                        error_message=(
                            f"Process for '{target.hostname}' timed out after {timeout_seconds}s."
                        ),
                    )
                )
            except Exception as exc:
                reports.append(
                    _build_error_report(
                        target=target,
                        error_category="process_error",
                        error_message=str(exc),
                    )
                )
    return reports


async def _async_check_one_device(
    target: DeviceCheckTarget,
    timeout_seconds: float,
) -> HealthCheckReport:
    """Offload synchronous pyATS/Genie check to a background thread safely inside asyncio."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(execute_single_device_check, target),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return _build_error_report(
            target=target,
            error_category="async_timeout",
            error_message=f"Async check for '{target.hostname}' timed out after {timeout_seconds}s.",
        )
    except Exception as exc:
        return _build_error_report(
            target=target,
            error_category="async_error",
            error_message=str(exc),
        )


async def run_checks_with_asyncio(
    targets: list[DeviceCheckTarget],
    timeout_seconds: float = 15.0,
) -> list[HealthCheckReport]:
    """Run multiple device checks concurrently via asyncio.gather + asyncio.to_thread."""
    tasks = [
        _async_check_one_device(target, timeout_seconds=timeout_seconds)
        for target in targets
    ]
    results = await asyncio.gather(*tasks)
    return list(results)
