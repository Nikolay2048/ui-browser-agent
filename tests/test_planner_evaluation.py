from langchain_core.runnables import RunnableLambda

from browser_agent.models import (
    BrowserAction,
    BrowserTarget,
)
from browser_agent.planner_evaluation import (
    PlannerActionScore,
    PlannerEvaluationCase,
    evaluate_planner_case,
    make_planner_target,
    planner_action_evaluator,
    score_planner_action,
    summarize_planner_scores,
)
from browser_agent.models import TestCase as AgentTestCase


def fill_action(
    *,
    target_value: str = "Username",
    value: str = "standard_user",
    reason: str = "Enter username.",
) -> BrowserAction:
    return BrowserAction(
        action="fill",
        target=BrowserTarget(strategy="label", value=target_value),
        value=value,
        reason=reason,
    )


def make_case() -> PlannerEvaluationCase:
    return PlannerEvaluationCase(
        id="fill-username",
        test_case=AgentTestCase(
            id="login",
            name="Login",
            start_url="https://example.com/login",
            goal="Log in",
            test_data={"username": "standard_user"},
        ),
        page_snapshot='- textbox "Username"',
        expected_action=fill_action(),
    )


class FixedPlannerModel:
    def __init__(self, action: BrowserAction) -> None:
        self.action = action

    def with_structured_output(self, _schema):
        return RunnableLambda(lambda _prompt: self.action)


def test_exact_action_receives_full_score() -> None:
    score = score_planner_action(fill_action(), fill_action())

    assert score.action_match is True
    assert score.target_match is True
    assert score.value_match is True
    assert score.exact_match is True
    assert score.score == 1.0


def test_reason_is_not_part_of_behavioral_exact_match() -> None:
    score = score_planner_action(
        fill_action(reason="Reference explanation."),
        fill_action(reason="Different but valid explanation."),
    )

    assert score.exact_match is True


def test_partial_match_exposes_wrong_target() -> None:
    score = score_planner_action(
        fill_action(target_value="Username"),
        fill_action(target_value="Password"),
    )

    assert score.action_match is True
    assert score.target_match is False
    assert score.value_match is True
    assert score.exact_match is False
    assert score.score == 2 / 3


def test_summary_aggregates_component_metrics() -> None:
    scores = [
        PlannerActionScore(
            action_match=True,
            target_match=True,
            value_match=True,
            exact_match=True,
            score=1.0,
        ),
        PlannerActionScore(
            action_match=True,
            target_match=False,
            value_match=True,
            exact_match=False,
            score=2 / 3,
        ),
    ]

    summary = summarize_planner_scores(scores)

    assert summary.total_cases == 2
    assert summary.exact_matches == 1
    assert summary.exact_accuracy == 0.5
    assert summary.action_accuracy == 1.0
    assert summary.target_accuracy == 0.5
    assert summary.value_accuracy == 1.0


def test_summary_rejects_empty_experiment() -> None:
    try:
        summarize_planner_scores([])
    except ValueError as error:
        assert "scores" in str(error)
    else:
        raise AssertionError("Expected ValueError for empty scores")


def test_evaluate_case_runs_real_planner_contract() -> None:
    case = make_case()

    actual, score = evaluate_planner_case(
        FixedPlannerModel(fill_action()),
        case,
    )

    assert actual == fill_action()
    assert score.exact_match is True


def test_langsmith_target_returns_json_compatible_action() -> None:
    target = make_planner_target(FixedPlannerModel(fill_action()))

    output = target(
        {
            "test_case": make_case().test_case.model_dump(mode="json"),
            "page_snapshot": make_case().page_snapshot,
            "route": [],
        }
    )

    assert output["action"]["action"] == "fill"
    assert output["action"]["target"]["strategy"] == "label"


def test_langsmith_evaluator_returns_exact_match_feedback() -> None:
    expected = fill_action().model_dump(mode="json")

    feedback = planner_action_evaluator(
        inputs={},
        outputs={"action": expected},
        reference_outputs={"action": expected},
    )

    assert feedback == {
        "key": "planner_exact_match",
        "score": 1.0,
    }
