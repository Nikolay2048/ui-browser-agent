import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.evaluation.end_to_end import (
    EndToEndEvaluationCase,
    evaluate_end_to_end_case,
    summarize_agent_runs,
)
from browser_agent.evaluation.scenarios import build_scenario
from browser_agent.runner import run_agent


def load_cases() -> list[EndToEndEvaluationCase]:
    path = PROJECT_ROOT / "evaluations" / "end_to_end_cases.json"
    raw_cases = json.loads(path.read_text(encoding="utf-8"))

    return [
        EndToEndEvaluationCase.model_validate(item)
        for item in raw_cases
    ]


def main() -> None:
    scores = []

    for case in load_cases():
        model, browser = build_scenario(case.id)

        def run_case(test_case):
            return run_agent(
                model=model,
                browser=browser,
                test_case=test_case,
            )

        final_state, score = evaluate_end_to_end_case(
            run_case,
            case,
        )
        scores.append(score)

        print(
            f"{case.id}: "
            f"status={final_state['status']} "
            f"steps={final_state['step_count']} "
            f"failures={final_state['failure_count']} "
            f"exact={score.exact_match}"
        )

    summary = summarize_agent_runs(scores)

    print("\nSUMMARY")
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()