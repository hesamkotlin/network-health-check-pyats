"""Cisco pyATS Easypy Job file for running the Network Health Check AEtest script.

Usage:
    pyats run job src/network_health/tests/health_check_job.py --no-archive
"""

from __future__ import annotations

from pathlib import Path

from pyats.easypy import run

THIS_DIR = Path(__file__).resolve().parent
TESTSCRIPT_PATH = THIS_DIR / "aetest_health_check.py"


def main(runtime) -> None:  # type: ignore[no-untyped-def]
    """Execute the AEtest script in healthy scenario via pyATS Easypy runner."""
    run(
        testscript=str(TESTSCRIPT_PATH),
        runtime=runtime,
        taskid="Offline_Healthy_Router_Check",
        scenario="healthy",
    )
