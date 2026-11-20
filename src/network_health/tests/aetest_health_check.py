"""Cisco pyATS AEtest Network Health Check TestScript.

This script demonstrates the real pyATS AEtest execution model:
1. `CommonSetup`: Loads the pyATS Testbed topology, expected health policy YAML,
   and collects a device state snapshot (via Cisco Genie parsers).
2. `DeviceAvailabilityTestcase`: Validates device reachability and hostname identity.
3. `InterfaceHealthTestcase`: Validates operational/admin status and IPv4 CIDR of every
   expected interface.
4. `RoutingTableTestcase`: Validates expected IPv4 routes (default route + connected subnets).
5. `CommonCleanup`: Aggregates all assertion results, saves JSON and Markdown reports
   into `reports/`, and disconnects cleanly.

Usage (Direct AEtest standalone execution):
    python src/network_health/tests/aetest_health_check.py --scenario healthy
    python src/network_health/tests/aetest_health_check.py --scenario unhealthy
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from pyats import aetest
from pyats.topology import loader as topology_loader

from network_health.core.config import load_health_policy
from network_health.core.models import (
    DeviceSnapshot,
    ExpectedDeviceHealthPolicy,
    TestOutcome,
)
from network_health.core.validators import (
    evaluate_device_health,
    validate_device_availability,
    validate_interface_ip,
    validate_interface_status,
    validate_route_entry,
)
from network_health.devices.base import NetworkDeviceConnector
from network_health.reporting.reporter import save_json_report, save_markdown_report
from network_health.simulation.simulated_device import (
    SimulatedIosXeDevice,
    SimulationScenario,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "test_data" / "expected_health_policy.yaml"
DEFAULT_TESTBED_PATH = PROJECT_ROOT / "testbed" / "devices.yaml.example"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


class CommonSetup(aetest.CommonSetup):
    """AEtest CommonSetup: Prepare testbed, policy, and device snapshot."""

    @aetest.subsection
    def load_policy_and_testbed(
        self,
        policy_path: str | Path = DEFAULT_POLICY_PATH,
        testbed_path: str | Path = DEFAULT_TESTBED_PATH,
    ) -> None:
        """Load expected health policy YAML and verify pyATS testbed YAML."""
        # Provide safe default environment variables if not set so pyATS testbed loader
        # resolves %ENV{...} placeholders during offline simulation runs.
        os.environ.setdefault("CISCO_SANDBOX_HOST", "127.0.0.1")
        os.environ.setdefault("CISCO_SANDBOX_PORT", "22")
        os.environ.setdefault("CISCO_SANDBOX_USERNAME", "offline_sim_user")
        os.environ.setdefault("CISCO_SANDBOX_PASSWORD", "offline_sim_pass")

        policy = load_health_policy(policy_path)
        testbed = topology_loader.load(str(testbed_path))

        if policy.hostname not in testbed.devices:
            self.failed(
                f"Expected device '{policy.hostname}' not found in pyATS testbed '{testbed.name}'."
            )

        self.parent.parameters["policy"] = policy
        self.parent.parameters["testbed"] = testbed
        logger.info(
            "Loaded policy for device '%s' and pyATS testbed '%s' (%d interfaces in topology).",
            policy.hostname,
            testbed.name,
            len(testbed.devices[policy.hostname].interfaces),
        )

    @aetest.subsection
    def connect_and_collect_snapshot(
        self,
        scenario: str = "healthy",
    ) -> None:
        """Initialize the offline simulated device and parse CLI outputs via Genie."""
        policy: ExpectedDeviceHealthPolicy = self.parent.parameters["policy"]
        sim_scenario = SimulationScenario(scenario.lower())

        connector: NetworkDeviceConnector = SimulatedIosXeDevice(
            hostname=policy.hostname,
            scenario=sim_scenario,
        )
        self.parent.parameters["connector"] = connector
        self.parent.parameters["scenario_name"] = sim_scenario.value

        if sim_scenario != SimulationScenario.UNREACHABLE:
            connector.connect()

        snapshot = connector.collect_snapshot()
        self.parent.parameters["snapshot"] = snapshot
        logger.info(
            "Collected snapshot from '%s' (is_simulated=%s, reachable=%s, interfaces=%d, routes=%d)",
            snapshot.hostname,
            snapshot.is_simulated,
            snapshot.reachable,
            len(snapshot.interfaces),
            len(snapshot.routes),
        )


class DeviceAvailabilityTestcase(aetest.Testcase):
    """Testcase 1: Validate that the target network device is reachable and identified."""

    @aetest.test
    def verify_device_reachability_and_hostname(
        self,
        snapshot: DeviceSnapshot,
        policy: ExpectedDeviceHealthPolicy,
    ) -> None:
        result = validate_device_availability(snapshot, policy)
        logger.info("[%s] %s -> %s", result.outcome.value, result.check_name, result.message)
        if result.outcome != TestOutcome.PASS:
            self.failed(result.message)
        else:
            self.passed(result.message)


class InterfaceHealthTestcase(aetest.Testcase):
    """Testcase 2 & 3: Validate interface admin/operational status and IPv4 addressing."""

    @aetest.setup
    def check_interfaces_present(
        self,
        snapshot: DeviceSnapshot,
    ) -> None:
        if not snapshot.reachable:
            self.skipped("Skipping interface checks because device is unreachable.")

    @aetest.test
    def verify_interfaces_operational_status(
        self,
        snapshot: DeviceSnapshot,
        policy: ExpectedDeviceHealthPolicy,
    ) -> None:
        failures: list[str] = []
        for rule in policy.interfaces:
            result = validate_interface_status(snapshot, rule)
            logger.info("[%s] %s -> %s", result.outcome.value, result.check_name, result.message)
            if result.outcome != TestOutcome.PASS:
                failures.append(result.message)

        if failures:
            self.failed(" | ".join(failures))
        else:
            self.passed("All required interfaces are administratively and operationally UP.")

    @aetest.test
    def verify_interfaces_ipv4_configuration(
        self,
        snapshot: DeviceSnapshot,
        policy: ExpectedDeviceHealthPolicy,
    ) -> None:
        failures: list[str] = []
        for rule in policy.interfaces:
            if rule.expected_ip_address is None:
                continue
            result = validate_interface_ip(snapshot, rule)
            logger.info("[%s] %s -> %s", result.outcome.value, result.check_name, result.message)
            if result.outcome != TestOutcome.PASS:
                failures.append(result.message)

        if failures:
            self.failed(" | ".join(failures))
        else:
            self.passed("All required interfaces have expected IPv4 addresses and prefix lengths.")


class RoutingTableTestcase(aetest.Testcase):
    """Testcase 4: Validate expected IPv4 routes in the routing table."""

    @aetest.setup
    def check_routing_table_available(
        self,
        snapshot: DeviceSnapshot,
    ) -> None:
        if not snapshot.reachable:
            self.skipped("Skipping routing table checks because device is unreachable.")

    @aetest.test
    def verify_expected_routes(
        self,
        snapshot: DeviceSnapshot,
        policy: ExpectedDeviceHealthPolicy,
    ) -> None:
        failures: list[str] = []
        for rule in policy.routes:
            result = validate_route_entry(snapshot, rule)
            logger.info("[%s] %s -> %s", result.outcome.value, result.check_name, result.message)
            if result.outcome != TestOutcome.PASS:
                failures.append(result.message)

        if failures:
            self.failed(" | ".join(failures))
        else:
            self.passed("All required IPv4 routes are active and valid in the routing table.")


class CommonCleanup(aetest.CommonCleanup):
    """AEtest CommonCleanup: Generate structured reports and close device session."""

    @aetest.subsection
    def generate_reports_and_disconnect(
        self,
        reports_dir: str | Path = DEFAULT_REPORTS_DIR,
    ) -> None:
        snapshot: DeviceSnapshot | None = self.parent.parameters.get("snapshot")
        policy: ExpectedDeviceHealthPolicy | None = self.parent.parameters.get("policy")
        connector: NetworkDeviceConnector | None = self.parent.parameters.get("connector")
        scenario_name: str = self.parent.parameters.get("scenario_name", "healthy")

        if snapshot is not None and policy is not None:
            report = evaluate_device_health(
                snapshot=snapshot,
                policy=policy,
                scenario_name=scenario_name,
            )
            json_path = save_json_report(report, reports_dir)
            md_path = save_markdown_report(report, reports_dir)
            logger.info("Generated JSON report: %s", json_path)
            logger.info("Generated Markdown report: %s", md_path)

        if connector is not None:
            connector.disconnect()


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pyATS AEtest Network Health Check (Offline Simulation Mode)."
    )
    parser.add_argument(
        "--scenario",
        choices=["healthy", "unhealthy", "unreachable"],
        default="healthy",
        help="Offline simulation scenario to execute (default: healthy).",
    )
    parser.add_argument(
        "--policy",
        default=str(DEFAULT_POLICY_PATH),
        help="Path to expected health policy YAML file.",
    )
    parser.add_argument(
        "--testbed",
        default=str(DEFAULT_TESTBED_PATH),
        help="Path to pyATS testbed YAML file.",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(DEFAULT_REPORTS_DIR),
        help="Directory to write JSON and Markdown health reports.",
    )
    return parser.parse_known_args(argv)[0]


if __name__ == "__main__":
    args = parse_cli_args()
    aetest.main(
        scenario=args.scenario,
        policy_path=args.policy,
        testbed_path=args.testbed,
        reports_dir=args.reports_dir,
    )
