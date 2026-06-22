import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.evaluation.planner import PlannerEvaluationCase


DATASET_NAME = "ui-browser-agent-planner-v1"


def load_cases(path: Path) -> list[PlannerEvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))

    return [
        PlannerEvaluationCase.model_validate(raw_case)
        for raw_case in raw_cases
    ]


def main() -> None:
    cases = load_cases(
        PROJECT_ROOT / "evaluations" / "planner_cases.json"
    )

    client = Client()

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description=(
            "Human-approved next actions for Planner evaluation."
        ),
    )

    examples = []

    for case in cases:
        example = {
            "inputs": {
                "test_case": case.test_case.model_dump(mode="json"),
                "page_snapshot": case.page_snapshot,
                "route": [
                    step.model_dump(mode="json")
                    for step in case.route
                ],
            },
            "outputs": {
                "action": case.expected_action.model_dump(mode="json"),
            },
            "metadata": {
                "case_id": case.id,
            },
        }

        examples.append(example)

    client.create_examples(
        dataset_id=dataset.id,
        examples=examples,
    )

    print(f"Created dataset: {dataset.name}")
    print(f"Uploaded examples: {len(examples)}")


if __name__ == "__main__":
    main()