"""Key reporting contracts completed in lesson 21."""

from browser_agent.models import RunReport
from browser_agent.reporting import (
    build_run_report,
    render_run_report_markdown,
    save_run_report,
)

__all__ = [
    "RunReport",
    "build_run_report",
    "render_run_report_markdown",
    "save_run_report",
]
