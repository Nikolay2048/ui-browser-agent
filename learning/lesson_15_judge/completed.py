"""Lesson 15 summary: finish is routed to Judge before pass/fail."""

from browser_agent.models import ExpectedResultCheck, JudgeVerdict


def route_after_judge(state) -> str:
    if state["verdict"].passed:
        return "pass_run"
    return "fail_run"


__all__ = ["ExpectedResultCheck", "JudgeVerdict", "route_after_judge"]
