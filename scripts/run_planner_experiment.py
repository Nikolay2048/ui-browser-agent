import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langsmith import Client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.planner_evaluation import (
    make_planner_target,
    planner_action_evaluator,
)


DATASET_NAME = "ui-browser-agent-planner-v1"


def main() -> None:
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.6:35b")

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
        make_planner_target(model),
        data=DATASET_NAME,
        evaluators=[planner_action_evaluator],
        experiment_prefix=f"planner-{model_name.replace(':', '-')}",
        description=(
            "Planner evaluation using the current prompt and local Ollama model."
        ),
        metadata={
            "model": model_name,
            "component": "planner",
            "prompt_version": "v1",
        },
        max_concurrency=1,
    )

    print(results)


if __name__ == "__main__":
    main()