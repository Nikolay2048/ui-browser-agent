import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langsmith import Client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.judge_evaluation import (
    judge_correctness_evaluator,
    judge_false_positive_evaluator,
    make_judge_target,
)


DATASET_NAME = "ui-browser-agent-judge-v1"


def main() -> None:
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

    client = Client()

    results = client.evaluate(
        make_judge_target(model),
        data=DATASET_NAME,
        evaluators=[
            judge_correctness_evaluator,
            judge_false_positive_evaluator,
        ],
        experiment_prefix=(
            f"judge-{model_name.replace(':', '-')}"
        ),
        description=(
            "Judge pass/fail evaluation using the current prompt."
        ),
        metadata={
            "model": model_name,
            "component": "judge",
            "prompt_version": "v1",
        },
        max_concurrency=1,
    )

    print(results)


if __name__ == "__main__":
    main()