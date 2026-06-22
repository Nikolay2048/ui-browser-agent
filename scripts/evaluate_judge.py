"""Run Judge evaluation locally against a fixed JSON dataset."""

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

from browser_agent.evaluation.judge import (
    JudgeEvaluationCase,
    evaluate_judge_case,
    summarize_judge_scores,
)


def load_cases(path: Path) -> list[JudgeEvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return [
        JudgeEvaluationCase.model_validate(raw_case)
        for raw_case in raw_cases
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evaluations" / "judge_cases.json",
    )
    args = parser.parse_args()

    model_name = os.getenv("OLLAMA_MODEL", "qwen3.5:35b")
    model = ChatOllama(
        model=model_name,
        temperature=0,
        validate_model_on_init=True,
    )

    scores = []
    for case in load_cases(args.dataset):
        actual, score = evaluate_judge_case(model, case)
        scores.append(score)
        print(
            f"{case.id}: expected={case.expected_passed} "
            f"actual={actual.passed} outcome={score.outcome}"
        )

    print("\nSUMMARY")
    print(summarize_judge_scores(scores).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
