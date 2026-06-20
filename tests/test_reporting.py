import json

from browser_agent.models import (
    RunTermination,
    TerminationKind,
    TestCase as AgentTestCase,
)
from browser_agent.reporting import (
    build_run_report,
    render_run_report_markdown,
    save_run_report,
)


def make_final_state() -> dict:
    return {
        "test_case": AgentTestCase(
            id="saved-report",
            name="Create task",
            start_url="https://example.com/tasks",
            goal="Create task Learn agents",
            test_data={"task": "Learn agents"},
            expected=["Learn agents is visible"],
        ),
        "status": "passed",
        "current_url": "https://example.com/tasks",
        "step_count": 0,
        "failure_count": 0,
        "route": [],
        "page_snapshot": 'listitem "Learn agents"',
        "termination": RunTermination(
            kind=TerminationKind.JUDGE_PASSED,
            message="All expected results passed.",
        ),
    }


def test_build_run_report_copies_stable_final_fields() -> None:
    report = build_run_report(make_final_state())

    assert report.test_case.id == "saved-report"
    assert report.final_url == "https://example.com/tasks"
    assert report.final_snapshot == 'listitem "Learn agents"'
    assert report.status == "passed"
    assert report.verdict is None
    assert report.classification is None
    assert report.bug_report is None


def test_markdown_contains_run_summary_and_expected_results() -> None:
    report = build_run_report(make_final_state())

    markdown = render_run_report_markdown(report)

    assert "# Test Run: Create task" in markdown
    assert "**Status:** passed" in markdown
    assert "Learn agents is visible" in markdown
    assert "All expected results passed." in markdown


def test_markdown_explains_missing_optional_sections() -> None:
    report = build_run_report(make_final_state())

    markdown = render_run_report_markdown(report)

    assert "No Judge verdict was recorded." in markdown
    assert "No failure classification was required." in markdown
    assert "No bug report was created." in markdown


def test_save_run_report_creates_json_and_markdown(tmp_path) -> None:
    report = build_run_report(make_final_state())

    json_path, markdown_path = save_run_report(report, tmp_path)

    assert json_path == tmp_path / "saved-report.json"
    assert markdown_path == tmp_path / "saved-report.md"
    assert json_path.is_file()
    assert markdown_path.is_file()

    saved_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved_json["test_case"]["id"] == "saved-report"
    assert saved_json["termination"]["kind"] == "judge_passed"
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Test Run: Create task"
    )
