"""CLI entrypoint to run offline network health checks and generate reports."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from network_health.core.config import load_health_policy
from network_health.core.models import TestOutcome
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


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Execute Offline Network Health Check and generate reports."
    )
    parser.add_argument(
        "--scenario",
        choices=["healthy", "unhealthy", "unreachable"],
        default="healthy",
        help="Offline simulation scenario to execute.",
    )
    args = parser.parse_args()

    policy_path = PROJECT_ROOT / "test_data" / "expected_health_policy.yaml"
    reports_dir = PROJECT_ROOT / "reports"

    policy = load_health_policy(policy_path)
    scenario = SimulationScenario(args.scenario)

    device = SimulatedIosXeDevice(hostname=policy.hostname, scenario=scenario)
    if scenario != SimulationScenario.UNREACHABLE:
        device.connect()

    snapshot = device.collect_snapshot()
    device.disconnect()

    report = evaluate_device_health(
        snapshot=snapshot,
        policy=policy,
        scenario_name=scenario.value,
    )
    json_path = save_json_report(report, reports_dir)
    md_path = save_markdown_report(report, reports_dir)

    print(format_markdown_report(report))
    print(f"Saved JSON report:     {json_path}")
    print(f"Saved Markdown report: {md_path}")

    return 0 if report.overall_outcome == TestOutcome.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
