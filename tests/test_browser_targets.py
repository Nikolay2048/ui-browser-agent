import pytest
from pydantic import ValidationError

from browser_agent.domain import BrowserTarget, BrowserTargetStrategy


def test_label_target_renders_locator_string() -> None:
    target = BrowserTarget(strategy="label", value="Task")

    assert target.strategy == BrowserTargetStrategy.LABEL
    assert target.value == "Task"
    assert target.name is None
    assert str(target) == "label=Task"


def test_role_target_requires_name_and_renders_locator_string() -> None:
    target = BrowserTarget(strategy="role", value="button", name="Add")

    assert target.strategy == BrowserTargetStrategy.ROLE
    assert target.value == "button"
    assert target.name == "Add"
    assert str(target) == 'role=button[name="Add"]'


@pytest.mark.parametrize(
    "target",
    [
        BrowserTarget(strategy="text", value="Learn AI Agents"),
        BrowserTarget(strategy="css", value=".todo-list li"),
    ],
)
def test_text_and_css_targets_do_not_use_name(target: BrowserTarget) -> None:
    assert target.name is None


@pytest.mark.parametrize(
    "payload",
    [
        {"strategy": "role", "value": "button"},
        {"strategy": "label", "value": "Task", "name": "Unexpected"},
        {"strategy": "text", "value": '"Learn AI Agents"'},
        {"strategy": "unknown", "value": "Task"},
        {"strategy": "label", "value": ""},
    ],
)
def test_browser_target_rejects_invalid_contract(payload: dict) -> None:
    with pytest.raises(ValidationError):
        BrowserTarget.model_validate(payload)
