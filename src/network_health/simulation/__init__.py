"""Offline network simulation and Genie parser helpers."""

from __future__ import annotations

from network_health.simulation.genie_parser import (
    create_offline_genie_device,
    extract_interfaces_from_genie,
    extract_routes_from_genie,
    parse_cli_with_genie,
)
from network_health.simulation.simulated_device import (
    SimulatedIosXeDevice,
    SimulationScenario,
)

__all__ = [
    "SimulatedIosXeDevice",
    "SimulationScenario",
    "create_offline_genie_device",
    "extract_interfaces_from_genie",
    "extract_routes_from_genie",
    "parse_cli_with_genie",
]
