"""SQLite persistence layer for Network Health Check execution history (Phase 6).

Architecture Rule (Phase 6):
- Uses Python's built-in `sqlite3` module with parameterized SQL queries (`?`)
  to prevent SQL Injection and avoid unnecessary ORM complexity in v1.
- In Android / Kotlin terms, this class plays the role of a Room `Dao` + `Repository`
  backed by SQLite.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from network_health.core.models import (
    CheckAssertionResult,
    HealthCheckReport,
    TestOutcome,
)


class SQLiteHealthRepository:
    """Stores and queries device metadata and test execution history in SQLite."""

    def __init__(self, db_path: str | Path = "reports/network_health_history.db") -> None:
        self._db_path = Path(db_path)
        if str(self._db_path) != ":memory:":
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_runs (
                    run_id TEXT PRIMARY KEY,
                    device_hostname TEXT NOT NULL,
                    is_simulated INTEGER NOT NULL,
                    scenario_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    overall_outcome TEXT NOT NULL,
                    total_checks INTEGER NOT NULL,
                    passed_checks INTEGER NOT NULL,
                    failed_checks INTEGER NOT NULL,
                    executed_at TEXT NOT NULL,
                    results_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_report(self, report: HealthCheckReport, status: str = "COMPLETED") -> None:
        """Insert or update a HealthCheckReport in SQLite."""
        results_payload = [
            {
                "check_name": r.check_name,
                "category": r.category,
                "outcome": r.outcome.value,
                "expected": r.expected,
                "actual": r.actual,
                "message": r.message,
            }
            for r in report.results
        ]

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO test_runs (
                    run_id,
                    device_hostname,
                    is_simulated,
                    scenario_name,
                    status,
                    overall_outcome,
                    total_checks,
                    passed_checks,
                    failed_checks,
                    executed_at,
                    results_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.run_id,
                    report.device_hostname,
                    1 if report.is_simulated else 0,
                    report.scenario_name,
                    status,
                    report.overall_outcome.value,
                    len(report.results),
                    report.passed_count,
                    report.failed_count,
                    report.executed_at,
                    json.dumps(results_payload),
                ),
            )
            conn.commit()

    def get_run_status(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve lightweight execution status metadata for a single test run."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, device_hostname, is_simulated, scenario_name,
                       status, overall_outcome, total_checks, passed_checks,
                       failed_checks, executed_at
                FROM test_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "run_id": row["run_id"],
            "device_hostname": row["device_hostname"],
            "is_simulated": bool(row["is_simulated"]),
            "scenario_name": row["scenario_name"],
            "status": row["status"],
            "overall_outcome": row["overall_outcome"],
            "summary": {
                "total": row["total_checks"],
                "passed": row["passed_checks"],
                "failed": row["failed_checks"],
            },
            "executed_at": row["executed_at"],
        }

    def get_report(self, run_id: str) -> HealthCheckReport | None:
        """Reconstruct a full HealthCheckReport domain object by `run_id`."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM test_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        raw_results = json.loads(row["results_json"])
        assertions = tuple(
            CheckAssertionResult(
                check_name=item["check_name"],
                category=item["category"],
                outcome=TestOutcome(item["outcome"]),
                expected=item["expected"],
                actual=item["actual"],
                message=item["message"],
            )
            for item in raw_results
        )

        return HealthCheckReport(
            run_id=row["run_id"],
            device_hostname=row["device_hostname"],
            is_simulated=bool(row["is_simulated"]),
            scenario_name=row["scenario_name"],
            overall_outcome=TestOutcome(row["overall_outcome"]),
            results=assertions,
            executed_at=row["executed_at"],
        )

    def list_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent test execution history ordered newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, device_hostname, is_simulated, scenario_name,
                       status, overall_outcome, total_checks, passed_checks,
                       failed_checks, executed_at
                FROM test_runs
                ORDER BY executed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "run_id": r["run_id"],
                "device_hostname": r["device_hostname"],
                "is_simulated": bool(r["is_simulated"]),
                "scenario_name": r["scenario_name"],
                "status": r["status"],
                "overall_outcome": r["overall_outcome"],
                "summary": {
                    "total": r["total_checks"],
                    "passed": r["passed_checks"],
                    "failed": r["failed_checks"],
                },
                "executed_at": r["executed_at"],
            }
            for r in rows
        ]
