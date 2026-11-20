"""FastAPI REST API & Service Layer for Network Health Check (Phase 6).

Endpoints implemented:
- `POST /api/v1/runs`              -> Start a new test run & persist result in SQLite.
- `GET  /api/v1/runs/{run_id}/status` -> Retrieve lightweight test run status.
- `GET  /api/v1/runs/{run_id}`        -> Retrieve full test results for a run.
- `GET  /api/v1/runs`              -> Retrieve test execution history.

Notice how API routing logic is kept cleanly separated from pyATS/Genie execution
logic via `HealthCheckExecutionService`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from network_health.core.concurrency import DeviceCheckTarget, execute_single_device_check
from network_health.database.repository import SQLiteHealthRepository
from network_health.simulation.simulated_device import SimulationScenario

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "test_data" / "expected_health_policy.yaml"
DEFAULT_DB_PATH = PROJECT_ROOT / "reports" / "network_health_history.db"


class HealthCheckExecutionService:
    """Application service coordinating test runs and SQLite persistence."""

    def __init__(
        self,
        repository: SQLiteHealthRepository | None = None,
        policy_path: str | Path = DEFAULT_POLICY_PATH,
    ) -> None:
        self._repository = repository or SQLiteHealthRepository(DEFAULT_DB_PATH)
        self._policy_path = Path(policy_path)

    def start_test_run(
        self,
        hostname: str = "sim-rtr-core-01",
        scenario: str = "healthy",
    ) -> dict[str, Any]:
        """Trigger a health check run, persist it to SQLite, and return the report dict."""
        sim_scenario = SimulationScenario(scenario.lower())
        target = DeviceCheckTarget(
            hostname=hostname,
            policy_path=self._policy_path,
            scenario=sim_scenario,
        )
        report = execute_single_device_check(target)
        self._repository.save_report(report, status="COMPLETED")
        return report.to_dict()

    def get_run_status(self, run_id: str) -> dict[str, Any] | None:
        return self._repository.get_run_status(run_id)

    def get_run_results(self, run_id: str) -> dict[str, Any] | None:
        report = self._repository.get_report(run_id)
        return report.to_dict() if report is not None else None

    def get_run_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._repository.list_history(limit=limit)


def create_fastapi_app(
    service: HealthCheckExecutionService | None = None,
) -> Any:
    """Factory creating the FastAPI application instance."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field

    app_service = service or HealthCheckExecutionService()
    app = FastAPI(
        title="Network Health Check Automation API",
        version="0.1.0",
        description="REST API exposing Cisco pyATS / Genie network health check runs and SQLite history.",
    )

    class StartRunRequest(BaseModel):
        hostname: str = Field(default="sim-rtr-core-01", description="Target router hostname")
        scenario: str = Field(
            default="healthy",
            pattern="^(healthy|unhealthy|unreachable)$",
            description="Offline simulation scenario: healthy, unhealthy, or unreachable",
        )

    @app.post("/api/v1/runs", status_code=201)
    def start_test_run(payload: StartRunRequest) -> dict[str, Any]:
        """Start a network health check test run and store results in SQLite."""
        return app_service.start_test_run(
            hostname=payload.hostname,
            scenario=payload.scenario,
        )

    @app.get("/api/v1/runs/{run_id}/status")
    def get_test_run_status(run_id: str) -> dict[str, Any]:
        """Retrieve execution status summary for a test run."""
        status_data = app_service.get_run_status(run_id)
        if status_data is None:
            raise HTTPException(status_code=404, detail=f"Test run '{run_id}' not found.")
        return status_data

    @app.get("/api/v1/runs/{run_id}")
    def get_test_run_results(run_id: str) -> dict[str, Any]:
        """Retrieve complete assertion results for a test run."""
        result_data = app_service.get_run_results(run_id)
        if result_data is None:
            raise HTTPException(status_code=404, detail=f"Test run '{run_id}' not found.")
        return result_data

    @app.get("/api/v1/runs")
    def list_test_run_history(limit: int = 20) -> dict[str, Any]:
        """Retrieve recent test run execution history."""
        items = app_service.get_run_history(limit=limit)
        return {"count": len(items), "items": items}

    return app
