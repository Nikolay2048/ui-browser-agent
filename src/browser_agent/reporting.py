"""Build and persist the final report of an agent run."""

from pathlib import Path

from browser_agent.models import RunReport
from browser_agent.state import AgentState
from jinja2 import Environment, PackageLoader, StrictUndefined

environment = Environment(
    loader=PackageLoader("browser_agent", "templates"),
    undefined=StrictUndefined,
    autoescape=False,
    keep_trailing_newline=True,
)


def build_run_report(state: AgentState) -> RunReport:
    """Convert transient LangGraph state into a stable domain model."""

    return RunReport(
        test_case=state["test_case"],
        status=state["status"],
        final_url=state["current_url"],
        final_snapshot=state["page_snapshot"],
        step_count=state["step_count"],
        failure_count=state["failure_count"],
        route=state["route"],
        termination=state["termination"],
        verdict=state.get("verdict"),
        classification=state.get("classification"),
        bug_report=state.get("bug_report"),
    )


def render_run_report_markdown(report: RunReport) -> str:
    """Render a human-readable report without calling an LLM."""
    template = environment.get_template("run_report.md.j2")
    return template.render(report=report)


def save_run_report(
    report: RunReport,
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """Save JSON and Markdown files and return their paths."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / f"{report.test_case.id}.json"
    markdown_path = output_path / f"{report.test_case.id}.md"

    json_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    markdown_path.write_text(
        render_run_report_markdown(report),
        encoding="utf-8",
    )

    return json_path, markdown_path
