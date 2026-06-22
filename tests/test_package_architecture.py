import browser_agent.models as legacy_models
import browser_agent.planner_evaluation as legacy_planner_evaluation
import browser_agent.judge_evaluation as legacy_judge_evaluation

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


def test_legacy_model_imports_keep_same_class_identity() -> None:
    from browser_agent.domain.models import TestCase as DomainTestCase

    assert legacy_models.TestCase is DomainTestCase
    assert legacy_models.BrowserAction is BrowserAction


def test_evaluation_implementations_are_owned_by_evaluation_package() -> None:
    assert (
        score_planner_action.__module__
        == "browser_agent.evaluation.planner"
    )
    assert (
        score_judge_verdict.__module__
        == "browser_agent.evaluation.judge"
    )


def test_legacy_evaluation_imports_keep_function_identity() -> None:
    assert (
        legacy_planner_evaluation.score_planner_action
        is score_planner_action
    )
    assert (
        legacy_judge_evaluation.score_judge_verdict
        is score_judge_verdict
    )


def test_package_initializers_expose_intentional_public_api() -> None:
    assert PlannerEvaluationCase.__module__ == "browser_agent.evaluation.planner"
    assert JudgeEvaluationCase.__module__ == "browser_agent.evaluation.judge"
