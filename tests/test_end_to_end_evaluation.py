import pytest

from browser_agent.domain import (
    RunTermination,
    TerminationKind,
    TestCase as AgentTestCase,
)
from browser_agent.evaluation.end_to_end import (
    EndToEndEvaluationCase,
    EndToEndExpectation,
    EndToEndRunScore,
    end_to_end_evaluator,
    evaluate_end_to_end_case,
    make_end_to_end_target,
    score_agent_run,
    summarize_agent_runs,
)


def expectation(
    *,
    status: str = "passed",
    max_steps: int = 2,
    kind: TerminationKind = TerminationKind.JUDGE_PASSED,
    expects_recovery: bool = False,
) -> EndToEndExpectation:
    return EndToEndExpectation(
        status=status,
        max_steps=max_steps,
        termination_kind=kind,
        expects_recovery=expects_recovery,
    )


def final_state(
    *,
    status: str = "passed",
    step_count: int = 2,
    failure_count: int = 0,
    kind: TerminationKind = TerminationKind.JUDGE_PASSED,
) -> dict:
    return {
        "status": status,
        "step_count": step_count,
        "failure_count": failure_count,
        "termination": RunTermination(
            kind=kind,
            message="Evaluation fixture termination.",
        ),
    }


def test_score_agent_run_accepts_exact_happy_path() -> None:
    score = score_agent_run(expectation(), final_state())

    assert score.status_match is True
    assert score.termination_match is True
    assert score.within_step_budget is True
    assert score.recovery_observed is False
    assert score.recovery_match is True
    assert score.exact_match is True
    assert score.score == 1.0


def test_score_agent_run_detects_recovery() -> None:
    score = score_agent_run(
        expectation(expects_recovery=True),
        final_state(failure_count=1),
    )

    assert score.recovery_observed is True
    assert score.recovery_match is True
    assert score.exact_match is True


def test_score_agent_run_penalizes_wrong_status_and_step_budget() -> None:
    score = score_agent_run(
        expectation(),
        final_state(
            status="failed",
            step_count=4,
            kind=TerminationKind.FAILURE_LIMIT,
        ),
    )

    assert score.status_match is False
    assert score.termination_match is False
    assert score.within_step_budget is False
    assert score.exact_match is False
    assert score.score == 0.25


def test_summary_aggregates_system_metrics() -> None:
    scores = [
        EndToEndRunScore(
            status_match=True,
            termination_match=True,
            within_step_budget=True,
            recovery_observed=False,
            recovery_match=True,
            exact_match=True,
            score=1.0,
            step_count=2,
            failure_count=0,
        ),
        EndToEndRunScore(
            status_match=False,
            termination_match=True,
            within_step_budget=False,
            recovery_observed=True,
            recovery_match=False,
            exact_match=False,
            score=0.5,
            step_count=4,
            failure_count=1,
        ),
    ]

    summary = summarize_agent_runs(scores)

    assert summary.total_cases == 2
    assert summary.exact_matches == 1
    assert summary.exact_accuracy == 0.5
    assert summary.task_success_rate == 0.5
    assert summary.termination_accuracy == 1.0
    assert summary.step_budget_rate == 0.5
    assert summary.recovery_accuracy == 0.5
    assert summary.average_steps == 3.0
    assert summary.average_failures == 0.5
    assert summary.average_score == 0.75


def test_summary_rejects_empty_suite() -> None:
    with pytest.raises(ValueError, match="scores"):
        summarize_agent_runs([])


def make_case() -> EndToEndEvaluationCase:
    return EndToEndEvaluationCase(
        id="e2e-case",
        test_case=AgentTestCase(
            id="e2e-case",
            name="Complete scenario",
            start_url="https://example.com",
            goal="Complete scenario",
        ),
        expected=expectation(),
    )


def test_evaluate_case_uses_injected_complete_runner() -> None:
    received = []

    def run_case(test_case):
        received.append(test_case)
        return final_state()

    state, score = evaluate_end_to_end_case(run_case, make_case())

    assert received == [make_case().test_case]
    assert state["status"] == "passed"
    assert score.exact_match is True


def test_langsmith_target_returns_compact_run_output() -> None:
    target = make_end_to_end_target(lambda _case: final_state())

    output = target({
        "test_case": make_case().test_case.model_dump(mode="json"),
    })

    assert output == {
        "status": "passed",
        "step_count": 2,
        "failure_count": 0,
        "termination": {
            "kind": "judge_passed",
            "message": "Evaluation fixture termination.",
        },
    }


def test_langsmith_evaluator_scores_complete_run() -> None:
    expected = expectation().model_dump(mode="json")
    output = make_end_to_end_target(
        lambda _case: final_state()
    )({
        "test_case": make_case().test_case.model_dump(mode="json"),
    })

    feedback = end_to_end_evaluator(
        inputs={},
        outputs=output,
        reference_outputs={"expected": expected},
    )

    assert feedback == {
        "key": "e2e_exact_match",
        "score": 1.0,
    }
