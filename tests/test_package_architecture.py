from importlib.util import find_spec

from browser_agent.domain import TestCase as DomainTestCase
from browser_agent.domain.models import BrowserAction
from browser_agent.evaluation import (
    JudgeEvaluationCase,
    PlannerEvaluationCase,
)
from browser_agent.evaluation.judge import score_judge_verdict
from browser_agent.evaluation.planner import score_planner_action


def test_domain_models_are_owned_by_domain_package() -> None:
    assert DomainTestCase.__module__ == "browser_agent.domain.models"
    assert BrowserAction.__module__ == "browser_agent.domain.models"


def test_legacy_model_module_is_removed() -> None:
    assert find_spec("browser_agent.models") is None


def test_evaluation_implementations_are_owned_by_evaluation_package() -> None:
    assert (
        score_planner_action.__module__
        == "browser_agent.evaluation.planner"
    )
    assert (
        score_judge_verdict.__module__
        == "browser_agent.evaluation.judge"
    )


def test_legacy_evaluation_modules_are_removed() -> None:
    assert find_spec("browser_agent.planner_evaluation") is None
    assert find_spec("browser_agent.judge_evaluation") is None


def test_package_initializers_expose_intentional_public_api() -> None:
    assert PlannerEvaluationCase.__module__ == "browser_agent.evaluation.planner"
    assert JudgeEvaluationCase.__module__ == "browser_agent.evaluation.judge"
