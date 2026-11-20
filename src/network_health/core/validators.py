"""Pure validation logic comparing ExpectedDeviceHealthPolicy against a DeviceSnapshot.

Keeping validation pure (no I/O, no network sockets) mirrors Clean Architecture's
Domain UseCases in Kotlin: easy to unit-test with 100% determinism and reusable
inside both pytest and pyATS AEtest testcases.
"""

from __future__ import annotations

import uuid

from network_health.core.models import (
    CheckAssertionResult,
    DeviceSnapshot,
    ExpectedDeviceHealthPolicy,
    ExpectedInterfaceRule,
    ExpectedRouteRule,
    HealthCheckReport,
    TestOutcome,
)


def validate_device_availability(
    snapshot: DeviceSnapshot,
    policy: ExpectedDeviceHealthPolicy,
) -> CheckAssertionResult:
    """Check 1: Verify device reachability and hostname match."""
    if not snapshot.reachable:
        return CheckAssertionResult(
            check_name="device_availability",
            category="availability",
            outcome=TestOutcome.FAIL,
            expected=f"reachable=True, hostname={policy.hostname}",
            actual=f"reachable=False, hostname={snapshot.hostname}",
            message=f"Device '{policy.hostname}' is unreachable.",
        )

    if snapshot.hostname != policy.hostname:
        return CheckAssertionResult(
            check_name="device_availability",
            category="availability",
            outcome=TestOutcome.FAIL,
            expected=f"hostname={policy.hostname}",
            actual=f"hostname={snapshot.hostname}",
            message=(
                f"Connected device hostname '{snapshot.hostname}' does not match "
                f"expected '{policy.hostname}'."
            ),
        )

    return CheckAssertionResult(
        check_name="device_availability",
        category="availability",
        outcome=TestOutcome.PASS,
        expected=f"reachable=True, hostname={policy.hostname}",
        actual=f"reachable=True, hostname={snapshot.hostname}",
        message=f"Device '{snapshot.hostname}' is reachable and identified.",
    )


def validate_interface_status(
    snapshot: DeviceSnapshot,
    rule: ExpectedInterfaceRule,
) -> CheckAssertionResult:
    """Check 2: Verify an interface exists and meets expected admin/operational status."""
    actual_iface = snapshot.interfaces.get(rule.name)
    expected_str = (
        f"admin={rule.expected_admin_status.value}, "
        f"oper={rule.expected_oper_status.value}"
    )

    if actual_iface is None:
        return CheckAssertionResult(
            check_name=f"interface_status[{rule.name}]",
            category="interface_status",
            outcome=TestOutcome.FAIL,
            expected=expected_str,
            actual="interface_missing",
            message=f"Interface '{rule.name}' was not found on device '{snapshot.hostname}'.",
        )

    actual_str = (
        f"admin={actual_iface.admin_status.value}, "
        f"oper={actual_iface.oper_status.value}"
    )

    if (
        actual_iface.admin_status != rule.expected_admin_status
        or actual_iface.oper_status != rule.expected_oper_status
    ):
        return CheckAssertionResult(
            check_name=f"interface_status[{rule.name}]",
            category="interface_status",
            outcome=TestOutcome.FAIL,
            expected=expected_str,
            actual=actual_str,
            message=(
                f"Interface '{rule.name}' status mismatch: expected ({expected_str}), "
                f"got ({actual_str})."
            ),
        )

    return CheckAssertionResult(
        check_name=f"interface_status[{rule.name}]",
        category="interface_status",
        outcome=TestOutcome.PASS,
        expected=expected_str,
        actual=actual_str,
        message=f"Interface '{rule.name}' is {actual_str}.",
    )


def validate_interface_ip(
    snapshot: DeviceSnapshot,
    rule: ExpectedInterfaceRule,
) -> CheckAssertionResult:
    """Check 3: Verify an interface has the expected IPv4 address and prefix length."""
    expected_cidr = (
        f"{rule.expected_ip_address}/{rule.expected_prefix_length}"
        if rule.expected_ip_address and rule.expected_prefix_length is not None
        else str(rule.expected_ip_address)
    )
    actual_iface = snapshot.interfaces.get(rule.name)

    if actual_iface is None:
        return CheckAssertionResult(
            check_name=f"interface_ip[{rule.name}]",
            category="interface_ip",
            outcome=TestOutcome.FAIL,
            expected=expected_cidr,
            actual="interface_missing",
            message=f"Cannot verify IP on missing interface '{rule.name}'.",
        )

    actual_cidr = actual_iface.cidr or "unassigned"
    ip_matches = actual_iface.ip_address == rule.expected_ip_address
    prefix_matches = (
        rule.expected_prefix_length is None
        or actual_iface.prefix_length == rule.expected_prefix_length
    )

    if not (ip_matches and prefix_matches):
        return CheckAssertionResult(
            check_name=f"interface_ip[{rule.name}]",
            category="interface_ip",
            outcome=TestOutcome.FAIL,
            expected=expected_cidr,
            actual=actual_cidr,
            message=(
                f"Interface '{rule.name}' IP mismatch: expected '{expected_cidr}', "
                f"got '{actual_cidr}'."
            ),
        )

    return CheckAssertionResult(
        check_name=f"interface_ip[{rule.name}]",
        category="interface_ip",
        outcome=TestOutcome.PASS,
        expected=expected_cidr,
        actual=actual_cidr,
        message=f"Interface '{rule.name}' has expected IP '{actual_cidr}'.",
    )


def validate_route_entry(
    snapshot: DeviceSnapshot,
    rule: ExpectedRouteRule,
) -> CheckAssertionResult:
    """Check 4: Verify an expected IPv4 route exists and matches protocol/next-hop/interface."""
    actual_route = snapshot.routes.get(rule.prefix)
    expected_parts = [f"prefix={rule.prefix}", f"active={rule.must_be_active}"]
    if rule.expected_protocol:
        expected_parts.append(f"protocol={rule.expected_protocol}")
    if rule.expected_next_hop:
        expected_parts.append(f"next_hop={rule.expected_next_hop}")
    if rule.expected_outgoing_interface:
        expected_parts.append(f"interface={rule.expected_outgoing_interface}")
    expected_str = ", ".join(expected_parts)

    if actual_route is None:
        return CheckAssertionResult(
            check_name=f"route[{rule.prefix}]",
            category="routing",
            outcome=TestOutcome.FAIL,
            expected=expected_str,
            actual="route_missing",
            message=f"Route '{rule.prefix}' is missing from the routing table.",
        )

    actual_str = (
        f"prefix={actual_route.prefix}, active={actual_route.active}, "
        f"protocol={actual_route.protocol}, next_hop={actual_route.next_hop}, "
        f"interface={actual_route.outgoing_interface}"
    )

    mismatches: list[str] = []
    if actual_route.active != rule.must_be_active:
        mismatches.append(f"active={actual_route.active} (expected {rule.must_be_active})")
    if (
        rule.expected_protocol
        and actual_route.protocol.lower() != rule.expected_protocol.lower()
    ):
        mismatches.append(
            f"protocol='{actual_route.protocol}' (expected '{rule.expected_protocol}')"
        )
    if rule.expected_next_hop and actual_route.next_hop != rule.expected_next_hop:
        mismatches.append(
            f"next_hop='{actual_route.next_hop}' (expected '{rule.expected_next_hop}')"
        )
    if (
        rule.expected_outgoing_interface
        and actual_route.outgoing_interface != rule.expected_outgoing_interface
    ):
        mismatches.append(
            f"interface='{actual_route.outgoing_interface}' "
            f"(expected '{rule.expected_outgoing_interface}')"
        )

    if mismatches:
        return CheckAssertionResult(
            check_name=f"route[{rule.prefix}]",
            category="routing",
            outcome=TestOutcome.FAIL,
            expected=expected_str,
            actual=actual_str,
            message=f"Route '{rule.prefix}' validation failed: {'; '.join(mismatches)}.",
        )

    return CheckAssertionResult(
        check_name=f"route[{rule.prefix}]",
        category="routing",
        outcome=TestOutcome.PASS,
        expected=expected_str,
        actual=actual_str,
        message=f"Route '{rule.prefix}' is active and valid.",
    )


def evaluate_device_health(
    snapshot: DeviceSnapshot,
    policy: ExpectedDeviceHealthPolicy,
    scenario_name: str = "default",
    run_id: str | None = None,
) -> HealthCheckReport:
    """Check 5: Execute all policy rules against a DeviceSnapshot and build a HealthCheckReport."""
    assertions: list[CheckAssertionResult] = [
        validate_device_availability(snapshot, policy)
    ]

    for iface_rule in policy.interfaces:
        assertions.append(validate_interface_status(snapshot, iface_rule))
        if iface_rule.expected_ip_address is not None:
            assertions.append(validate_interface_ip(snapshot, iface_rule))

    for route_rule in policy.routes:
        assertions.append(validate_route_entry(snapshot, route_rule))

    overall = (
        TestOutcome.PASS
        if all(item.outcome == TestOutcome.PASS for item in assertions)
        else TestOutcome.FAIL
    )

    return HealthCheckReport(
        run_id=run_id or str(uuid.uuid4()),
        device_hostname=snapshot.hostname,
        is_simulated=snapshot.is_simulated,
        scenario_name=scenario_name,
        overall_outcome=overall,
        results=tuple(assertions),
    )
