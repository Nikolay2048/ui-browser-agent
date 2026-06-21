"""Run Planner evaluation locally and optionally upload it to LangSmith."""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.planner_evaluation import (
    PlannerEvaluationCase,
    evaluate_planner_case,
    summarize_planner_scores,
)


def load_cases(path: Path) -> list[PlannerEvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return [
        PlannerEvaluationCase.model_validate(raw_case)
        for raw_case in raw_cases
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evaluations" / "planner_cases.json",
    )
    args = parser.parse_args()

    model_name = os.getenv("OLLAMA_MODEL", "qwen3.6:35b")
    model = ChatOllama(
        model=model_name,
        temperature=0,
        validate_model_on_init=True,
    )

    cases = load_cases(args.dataset)
    scores = []

    for case in cases:
        actual, score = evaluate_planner_case(model, case)
        scores.append(score)
        print(
            f"{case.id}: exact={score.exact_match} "
            f"score={score.score:.2f} action={actual.action}"
        )

    summary = summarize_planner_scores(scores)
    print("\nSUMMARY")
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
