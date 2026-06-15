from browser_agent.graph import route_after_judge, route_planned_action
from browser_agent.models import (
    BrowserAction,
    ExpectedResultCheck,
    JudgeVerdict,
)


def make_verdict(passed: bool) -> JudgeVerdict:
    return JudgeVerdict(
        passed=passed,
        checks=[
            ExpectedResultCheck(
                expected="Task is visible",
                passed=passed,
                evidence="Task is visible." if passed else "No task evidence.",
            )
        ],
        summary="Passed." if passed else "Expected result is not proven.",
    )


def test_finish_routes_to_judge_not_directly_to_pass() -> None:
    finish = BrowserAction(
        action="finish",
        target=None,
        value=None,
        reason="Planner believes the goal is reached.",
    )

    assert route_planned_action({"proposed_action": finish}) == "judge"


def test_route_after_judge_uses_independent_verdict() -> None:
    assert route_after_judge({"verdict": make_verdict(True)}) == "pass_run"
    assert route_after_judge({"verdict": make_verdict(False)}) == "fail_run"
