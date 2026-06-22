"""Planner memory completed in lesson 14."""

from browser_agent.domain import ExecutionStep


def format_execution_history(route: list[ExecutionStep]) -> str:
    if not route:
        return "No actions have been executed yet."

    history = []
    for step in route:
        lines = [
            f"Step {step.step_number}",
            f"action={step.action.action}",
            f"target={step.action.target}",
            f"value={step.action.value}",
            f"success={step.result.success}",
            f"url={step.result.url_before} -> {step.result.url_after}",
        ]
        if step.result.error is not None:
            lines.append(f"error={step.result.error}")
        history.append("\n".join(lines))

    return "\n\n".join(history)
