#!/usr/bin/env python3
"""
AI Website Testing Agent — CLI runner.

Usage:
  python run_tests.py test_cases/saucedemo/tc_01_login_valid.yaml
  python run_tests.py test_cases/saucedemo/ --headless
  python run_tests.py test_cases/ --pattern tc_0*.yaml

After running:
  allure serve allure-results/
"""
from __future__ import annotations

import argparse
import sys

# Force UTF-8 output on Windows (avoids UnicodeEncodeError for non-ASCII chars)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import os
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

# LangSmith tracing — set via .env (skip placeholder value)
_ls_key = os.getenv("LANGSMITH_API_KEY", "")
if _ls_key and not _ls_key.startswith("your_"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "website-testing-agent")
    print("[LangSmith] Tracing enabled")
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

from testing_agent.browser_manager import BrowserManager
from testing_agent.graph import run_test_case
from testing_agent.models import TestCase, TestStep
from testing_agent.txt_parser import parse_txt


def load_test_case(path: str | Path) -> TestCase:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    steps = []
    for i, raw in enumerate(data["steps"], start=1):
        # Support both new format {step, expected} and legacy {description/action/...}
        if "step" in raw:
            steps.append(TestStep(step_number=i, step=raw["step"], expected=raw["expected"]))
        else:
            # Legacy format: build natural language from fields
            desc = raw.get("description", "")
            action = raw.get("action", "")
            target = raw.get("target", "")
            value = raw.get("value", "")
            nl = desc
            if value:
                nl = f"{desc} (value: '{value}')"
            steps.append(
                TestStep(
                    step_number=i,
                    step=nl or f"{action} on {target}",
                    expected=raw.get("expected_result", ""),
                )
            )

    return TestCase(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        start_url=data["start_url"],
        preconditions=data.get("preconditions", []),
        steps=steps,
        tags=data.get("tags", []),
        severity=data.get("severity", "medium"),
    )


def collect_test_files(paths: list[str], pattern: str = "*.yaml") -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob(pattern)))
            # also collect .txt test cases from directories
            if "*.yaml" in pattern or pattern == "*.yaml":
                files.extend(sorted(path.rglob("*.txt")))
    return files


def _divider(char: str = "=", width: int = 65) -> str:
    return char * width


def run_single(yaml_path: Path, headless: bool = False) -> dict:
    tc = parse_txt(yaml_path) if yaml_path.suffix == ".txt" else load_test_case(yaml_path)

    print(f"\n{_divider()}")
    print(f"TC: [{tc.id}] {tc.name}")
    print(f"URL: {tc.start_url}")
    print(f"Steps: {len(tc.steps)} | Severity: {tc.severity.upper()}")
    print(_divider("-"))

    browser = BrowserManager.get_instance()
    browser.start(headless=headless)

    try:
        start = time.time()
        final_state = run_test_case(tc)
        elapsed = time.time() - start

        status = final_state.get("overall_status", "broken")
        step_results = final_state.get("step_results", [])
        bugs = final_state.get("bugs", [])

        print(_divider("-"))
        print(f"RESULT: {status.upper()}  ({elapsed:.1f}s)")
        print(f"Steps:  {len(step_results)} executed")
        passed = sum(1 for r in step_results if r.status == "passed")
        failed = sum(1 for r in step_results if r.status in ("failed", "broken"))
        print(f"        {passed} passed / {failed} failed")
        print(f"Bugs:   {len(bugs)} found")

        if bugs:
            print("\nBUGS FOUND:")
            for bug in bugs:
                print(f"  [{bug.severity.upper()}] ({bug.type}) {bug.title}")

        if final_state.get("generated_test_code"):
            print(f"\nAuto-test: generated_tests/test_{tc.id}.py")

        clarification = final_state.get("clarification")
        if clarification and clarification.needs_clarification:
            print(f"\nCLARIFICATION NEEDED ({len(clarification.items)} item(s)):")
            for item in clarification.items:
                print(f"  Step {item.step_number}: {item.question}")
                print(f"    -> {item.suggestion}")
            for s in clarification.general_suggestions:
                print(f"  General: {s}")

        return {
            "tc_id": tc.id,
            "tc_name": tc.name,
            "status": status,
            "bugs": len(bugs),
            "elapsed": elapsed,
        }
    finally:
        browser.stop()
        BrowserManager._instance = None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Website Testing Agent — runs YAML test cases with LangGraph + Playwright"
    )
    parser.add_argument(
        "targets",
        nargs="+",
        help="YAML test case files or directories to run",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no window)",
    )
    parser.add_argument(
        "--pattern",
        default="*.yaml",
        help="Glob pattern when scanning directories (default: *.yaml)",
    )
    args = parser.parse_args()

    files = collect_test_files(args.targets, pattern=args.pattern)
    if not files:
        print(f"No test files found in: {args.targets}")
        sys.exit(1)

    print(f"\nFound {len(files)} test case(s) to run:")
    for f in files:
        print(f"  {f}")

    summary: list[dict] = []
    for yaml_file in files:
        result = run_single(yaml_file, headless=args.headless)
        summary.append(result)

    print(f"\n{_divider()}")
    print("SUMMARY")
    print(_divider("-"))
    total_bugs = 0
    for r in summary:
        icon = "+" if r["status"] == "passed" else "-"
        print(
            f"  [{icon}] [{r['status'].upper():8}] {r['tc_id']:10} {r['tc_name'][:45]}"
            f"  bugs={r['bugs']}  {r['elapsed']:.1f}s"
        )
        total_bugs += r["bugs"]

    passed_count = sum(1 for r in summary if r["status"] == "passed")
    print(_divider("-"))
    print(f"Total: {len(summary)} test(s) | {passed_count} passed | {total_bugs} bug(s) found")
    print(f"\nAllure results -> allure-results/")
    print('To view report:  & "C:\\Program Files\\allure-2.42.1\\bin\\allure.bat" serve allure-results')
    print("Generated tests: generated_tests/")


if __name__ == "__main__":
    main()
