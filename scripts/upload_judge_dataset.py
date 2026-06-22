import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.judge_evaluation import JudgeEvaluationCase


DATASET_NAME = "ui-browser-agent-judge-v1"


def load_cases(path: Path) -> list[JudgeEvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))

    return [
        JudgeEvaluationCase.model_validate(raw_case)
        for raw_case in raw_cases
    ]


def main() -> None:
    cases = load_cases(
        PROJECT_ROOT / "evaluations" / "judge_cases.json"
    )

    client = Client()

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description=(
            "Trusted pass/fail labels for Judge evaluation."
        ),
    )

    examples = []

    for case in cases:
        examples.append({
            "inputs": {
                "test_case": case.test_case.model_dump(mode="json"),
                "page_snapshot": case.page_snapshot,
                "route": [
                    step.model_dump(mode="json")
                    for step in case.route
                ],
            },
            "outputs": {
                "passed": case.expected_passed,
            },
            "metadata": {
                "case_id": case.id,
            },
        })

    client.create_examples(
        dataset_id=dataset.id,
        examples=examples,
    )

    print(f"Created dataset: {dataset.name}")
    print(f"Uploaded examples: {len(examples)}")


if __name__ == "__main__":
    main()