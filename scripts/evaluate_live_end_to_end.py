"""Evaluate the complete agent with Ollama and a real Playwright browser."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from playwright.sync_api import Browser, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.browser import PlaywrightBrowser
from browser_agent.domain import TestCase, TerminationKind
from browser_agent.evaluation import (
    EndToEndEvaluationCase,
    EndToEndExpectation,
    EndToEndRunScore,
    score_agent_run,
    summarize_agent_runs,
)
from browser_agent.runner import run_agent


def build_live_case() -> EndToEndEvaluationCase:
    """Build the controlled Playwright fixture case and its expectations."""
    fixture_path = PROJECT_ROOT / "examples" / "playwright_fixture.html"
    fixture_url = fixture_path.resolve().as_uri()

    test_case = TestCase(
        id="live-create-task",
        name="Create a task in the Playwright fixture",
        start_url=fixture_url,
        goal="Add the task 'Learn AI Agents' to the task list",
        test_data={
            "task": "Learn AI Agents",
        },
        expected=[
            "Learn AI Agents is visible in the task list",
        ],
        max_steps=5,
        max_failures=2,
    )

    expected = EndToEndExpectation(
        status="passed",
        max_steps=2,
        termination_kind=TerminationKind.JUDGE_PASSED,
        expects_recovery=False,
    )

    return EndToEndEvaluationCase(
        id="live-create-task",
        test_case=test_case,
        expected=expected,
    )


def run_once(
    *,
    model,
    chromium: Browser,
    case: EndToEndEvaluationCase,
    run_number: int,
) -> tuple[dict, EndToEndRunScore]:
    """Run one isolated browser session and score its final state."""
    context = chromium.new_context()
    page = context.new_page()

    artifact_dir = (
        PROJECT_ROOT
        / "artifacts"
        / "live-evaluation"
        / f"run-{run_number:03d}"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)

    try:
        browser = PlaywrightBrowser(
            page,
            artifacts_dir=artifact_dir,
        )

        final_state = run_agent(
            model=model,
            browser=browser,
            test_case=case.test_case,
        )

        score = score_agent_run(
            expected=case.expected,
            final_state=final_state,
        )

        return final_state, score
    finally:
        context.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=0)
    args = parser.parse_args()

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.slow_mo < 0:
        parser.error("--slow-mo must be non-negative")

    return args


def main() -> None:
    args = parse_args()
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.5:35b")

    model = ChatOllama(
        model=model_name,
        temperature=0,
        validate_model_on_init=True,
        metadata={
            "ls_model_name": model_name,
            "ls_provider": "ollama",
        },
    )

    case = build_live_case()
    scores: list[EndToEndRunScore] = []
    infrastructure_errors = 0

    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(
            headless=args.headless,
            slow_mo=args.slow_mo,
        )

        try:
            for run_number in range(1, args.repeat + 1):
                try:
                    final_state, score = run_once(
                        model=model,
                        chromium=chromium,
                        case=case,
                        run_number=run_number,
                    )
                except Exception as exc:
                    infrastructure_errors += 1
                    print(
                        f"run={run_number} infrastructure_error={exc}",
                        flush=True,
                    )
                    continue

                scores.append(score)

                print(
                    " ".join(
                        [
                            f"run={run_number}",
                            f"status={final_state['status']}",
                            f"steps={final_state['step_count']}",
                            f"failures={final_state['failure_count']}",
                            f"exact={score.exact_match}",
                        ]
                    ),
                    flush=True,
                )
        finally:
            chromium.close()

    if not scores:
        raise RuntimeError(
            "live evaluation produced no agent scores; "
            "all runs failed with infrastructure errors"
        )

    if infrastructure_errors:
        print(
            f"infrastructure_errors={infrastructure_errors}",
            flush=True,
        )

    summary = summarize_agent_runs(scores)

    print(
        summary.model_dump_json(indent=2),
        flush=True,
    )


if __name__ == "__main__":
    main()
