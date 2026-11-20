"""Report generator saving HealthCheckReport as structured JSON and Markdown."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from network_health.core.models import HealthCheckReport

logger = logging.getLogger(__name__)


def save_json_report(report: HealthCheckReport, output_dir: str | Path) -> Path:
    """Write a HealthCheckReport to a JSON file in `output_dir`."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / f"health_report_{report.scenario_name}.json"

    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2)

    logger.info("Saved JSON health report to %s", file_path)
    return file_path


def format_markdown_report(report: HealthCheckReport) -> str:
    """Format a HealthCheckReport into a clean Markdown document."""
    mode_str = "Offline Simulation (Simulated Device)" if report.is_simulated else "Real Cisco Device"
    lines: list[str] = [
        f"# Network Health Check Report — `{report.device_hostname}`",
        "",
        f"- **Run ID:** `{report.run_id}`",
        f"- **Execution Mode:** `{mode_str}`",
        f"- **Scenario:** `{report.scenario_name}`",
        f"- **Executed At (UTC):** `{report.executed_at}`",
        f"- **Overall Outcome:** **{report.overall_outcome.value}**",
        f"- **Summary:** `{report.passed_count} PASSED` / `{report.failed_count} FAILED` "
        f"(Total: `{len(report.results)}`)",
        "",
        "## Detailed Check Results",
        "",
        "| Check Name | Category | Outcome | Expected | Actual | Message |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for item in report.results:
        lines.append(
            f"| `{item.check_name}` | `{item.category}` | **{item.outcome.value}** | "
            f"`{item.expected}` | `{item.actual}` | {item.message} |"
        )

    lines.append("")
    return "\n".join(lines)


def save_markdown_report(report: HealthCheckReport, output_dir: str | Path) -> Path:
    """Write a HealthCheckReport to a Markdown file in `output_dir`."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / f"health_report_{report.scenario_name}.md"

    with file_path.open("w", encoding="utf-8") as handle:
        handle.write(format_markdown_report(report))

    logger.info("Saved Markdown health report to %s", file_path)
    return file_path
