from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from testing_agent.models import BugReport, ClarificationRequest, StepResult, TestCase

ALLURE_RESULTS = Path("allure-results")


def _ts(iso: str) -> int:
    try:
        return int(datetime.fromisoformat(iso).timestamp() * 1000)
    except Exception:
        return int(datetime.now().timestamp() * 1000)


def _copy_attachment(src: str, suffix: str) -> str | None:
    if not src or not Path(src).exists():
        return None
    att_uuid = str(uuid.uuid4())
    name = f"{att_uuid}-attachment{suffix}"
    shutil.copy2(src, ALLURE_RESULTS / name)
    return name


def write_allure_result(
    test_case: TestCase,
    step_results: list[StepResult],
    bugs: list[BugReport],
    generated_code: str,
    overall_status: str,
    start_iso: str,
    duration_ms: int,
    clarification: ClarificationRequest | None = None,
    plan_reasoning: str = "",
    analysis_reasoning: str = "",
) -> Path:
    ALLURE_RESULTS.mkdir(exist_ok=True)

    result_uuid = str(uuid.uuid4())
    start_ts = _ts(start_iso)
    stop_ts = start_ts + duration_ms

    allure_steps = []
    for sr in step_results:
        attachments = []

        att = _copy_attachment(sr.screenshot_path or "", ".png")
        if att:
            attachments.append({"name": f"Screenshot — step {sr.step_number}", "source": att, "type": "image/png"})

        if sr.tool_calls:
            log_uuid = str(uuid.uuid4())
            log_name = f"{log_uuid}-attachment.txt"
            (ALLURE_RESULTS / log_name).write_text("\n".join(sr.tool_calls), encoding="utf-8")
            attachments.append({"name": "Agent tool calls", "source": log_name, "type": "text/plain"})

        allure_steps.append(
            {
                "name": f"Step {sr.step_number}: {sr.description}",
                "status": sr.status,
                "statusDetails": {
                    "message": sr.actual_result[:500],
                    "trace": sr.error_message or "",
                },
                "attachments": attachments,
                "parameters": [
                    {"name": "expected", "value": sr.expected_result[:300]},
                    {"name": "actual", "value": sr.actual_result[:300]},
                    {"name": "duration_ms", "value": str(sr.duration_ms)},
                ],
                "start": start_ts,
                "stop": start_ts + sr.duration_ms,
            }
        )

    top_attachments = []

    if bugs:
        bugs_json = json.dumps([b.model_dump() for b in bugs], ensure_ascii=False, indent=2)
        bugs_uuid = str(uuid.uuid4())
        bugs_name = f"{bugs_uuid}-attachment.json"
        (ALLURE_RESULTS / bugs_name).write_text(bugs_json, encoding="utf-8")
        top_attachments.append(
            {"name": f"Bug Reports ({len(bugs)} found)", "source": bugs_name, "type": "application/json"}
        )

    if generated_code:
        code_uuid = str(uuid.uuid4())
        code_name = f"{code_uuid}-attachment.py"
        (ALLURE_RESULTS / code_name).write_text(generated_code, encoding="utf-8")
        top_attachments.append({"name": "Generated Playwright test", "source": code_name, "type": "text/x-python"})

    if plan_reasoning:
        r_uuid = str(uuid.uuid4())
        r_name = f"{r_uuid}-attachment.md"
        (ALLURE_RESULTS / r_name).write_text(
            f"# Рассуждения планировщика\n\n{plan_reasoning}", encoding="utf-8"
        )
        top_attachments.append(
            {"name": "Рассуждения планировщика", "source": r_name, "type": "text/markdown"}
        )

    if analysis_reasoning:
        a_uuid = str(uuid.uuid4())
        a_name = f"{a_uuid}-attachment.md"
        (ALLURE_RESULTS / a_name).write_text(
            f"# Рассуждения аналитика\n\n{analysis_reasoning}", encoding="utf-8"
        )
        top_attachments.append(
            {"name": "Рассуждения аналитика (Observer)", "source": a_name, "type": "text/markdown"}
        )

    if clarification and clarification.needs_clarification:
        lines = ["# Test Case Clarification Requests\n"]
        for item in clarification.items:
            lines.append(f"## Step {item.step_number}")
            lines.append(f"**Question:** {item.question}")
            lines.append(f"**Suggestion:** {item.suggestion}\n")
        if clarification.general_suggestions:
            lines.append("## General Suggestions")
            for s in clarification.general_suggestions:
                lines.append(f"- {s}")
        cl_uuid = str(uuid.uuid4())
        cl_name = f"{cl_uuid}-attachment.md"
        (ALLURE_RESULTS / cl_name).write_text("\n".join(lines), encoding="utf-8")
        top_attachments.append(
            {"name": "Clarification Requests", "source": cl_name, "type": "text/markdown"}
        )

    labels = [
        {"name": "severity", "value": test_case.severity},
        {"name": "feature", "value": "AI Website Testing"},
        {"name": "framework", "value": "LangGraph + Playwright"},
    ]
    for tag in test_case.tags:
        labels.append({"name": "tag", "value": tag})
    if bugs:
        labels.append({"name": "tag", "value": f"{len(bugs)}_bugs"})

    result_json = {
        "uuid": result_uuid,
        "historyId": test_case.id,
        "name": test_case.name,
        "description": test_case.description,
        "fullName": f"{test_case.id}: {test_case.name}",
        "status": overall_status,
        "statusDetails": {
            "message": f"{len(bugs)} bug(s) found" if bugs else "No bugs found",
        },
        "labels": labels,
        "steps": allure_steps,
        "attachments": top_attachments,
        "parameters": [
            {"name": "url", "value": test_case.start_url},
            {"name": "test_case_id", "value": test_case.id},
            {"name": "bugs_count", "value": str(len(bugs))},
        ],
        "start": start_ts,
        "stop": stop_ts,
    }

    out = ALLURE_RESULTS / f"{result_uuid}-result.json"
    out.write_text(json.dumps(result_json, ensure_ascii=False, indent=2), encoding="utf-8")

    for bug in bugs:
        _write_bug_result(bug, test_case, start_ts)

    print(f"  Allure result: {out.name}")
    return out


def _write_bug_result(bug: BugReport, tc: TestCase, start_ts: int) -> None:
    bug_uuid = str(uuid.uuid4())

    attachments = []
    for ss in bug.screenshots:
        att = _copy_attachment(ss, ".png")
        if att:
            attachments.append({"name": "Bug screenshot", "source": att, "type": "image/png"})

    result = {
        "uuid": bug_uuid,
        "historyId": f"bug_{bug.id}",
        "name": f"[BUG-{bug.severity.upper()}] {bug.title}",
        "description": bug.description,
        "fullName": f"Bug #{bug.id}: {bug.title}",
        "status": "failed",
        "statusDetails": {
            "message": bug.actual_result[:500],
            "trace": f"Expected: {bug.expected_result}\nActual: {bug.actual_result}",
        },
        "labels": [
            {"name": "severity", "value": bug.severity},
            {"name": "tag", "value": "BUG"},
            {"name": "tag", "value": bug.type},
            {"name": "feature", "value": "Bug Reports"},
            {"name": "story", "value": tc.name},
        ],
        "steps": [{"name": step, "status": "passed"} for step in bug.steps_to_reproduce],
        "attachments": attachments,
        "parameters": [
            {"name": "test_case", "value": tc.name},
            {"name": "severity", "value": bug.severity},
            {"name": "type", "value": bug.type},
            {"name": "step", "value": str(bug.step_number)},
        ],
        "start": start_ts,
        "stop": start_ts + 1000,
    }

    path = ALLURE_RESULTS / f"{bug_uuid}-result.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
