"""Bounded recovery policy completed in lesson 17."""


def route_after_execution(state) -> str:
    if state["step_count"] >= state["test_case"].max_steps:
        return "fail_run"
    if state["last_result"].success:
        return "observe"
    if state["failure_count"] >= state["test_case"].max_failures:
        return "fail_run"
    return "observe"
