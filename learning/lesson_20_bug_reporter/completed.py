"""Key contracts completed in lesson 20."""

from browser_agent.domain import BugReport, BugSeverity
from browser_agent.reporter import (
    build_reporter_chain,
    build_reporter_prompt,
    create_bug_report,
    make_reporter_node,
)

__all__ = [
    "BugReport",
    "BugSeverity",
    "build_reporter_chain",
    "build_reporter_prompt",
    "create_bug_report",
    "make_reporter_node",
]
