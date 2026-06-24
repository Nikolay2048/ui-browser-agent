from langchain_core.runnables import RunnableLambda

from browser_agent.domain import (
    BrowserAction,
    ExpectedResultCheck,
    JudgeVerdict,
    TestCase as AgentTestCase,
)
from browser_agent.runner import run_agent


class InMemoryHistoryStore:
    def __init__(self) -> None:
        self.records = []

    def append(self, record) -> None:
        self.records.append(record)


class FinishModel:
    def with_structured_output(self, schema):
        if schema is JudgeVerdict:
            return RunnableLambda(
                lambda _prompt: JudgeVerdict(
                    passed=True,
                    checks=[
                        ExpectedResultCheck(
                            expected="Page is available",
                            passed=True,
                            evidence="The page snapshot is available.",
                        )
                    ],
                    summary="Expected page is available.",
                )
            )

        return RunnableLambda(
            lambda _prompt: BrowserAction(
                action="finish",
                target=None,
                value=None,
                reason="The expected page is already available.",
            )
        )


class StaticBrowser:
    current_url = "about:blank"

    def open(self, url: str) -> None:
        self.current_url = url

    def snapshot(self) -> str:
        return 'heading "Example"'


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="runner-history",
        name="Open page",
        start_url="https://example.com",
        goal="Verify page is available",
        expected=["Page is available"],
    )


def test_run_agent_can_append_final_run_to_history() -> None:
    store = InMemoryHistoryStore()

    result = run_agent(
        FinishModel(),
        StaticBrowser(),
        make_case(),
        history_store=store,
        run_id="test-run-1",
    )

    assert result["status"] == "passed"
    assert len(store.records) == 1

    record = store.records[0]
    assert record.run_id == "test-run-1"
    assert record.report.test_case.id == "runner-history"
    assert record.report.status == "passed"
    assert record.report.step_count == result["step_count"]


def test_run_agent_can_save_report_and_append_history(tmp_path) -> None:
    store = InMemoryHistoryStore()

    result = run_agent(
        FinishModel(),
        StaticBrowser(),
        make_case(),
        report_dir=tmp_path,
        history_store=store,
    )

    assert result["status"] == "passed"
    assert (tmp_path / "runner-history.json").is_file()
    assert (tmp_path / "runner-history.md").is_file()

    assert len(store.records) == 1
    assert store.records[0].report.test_case.id == "runner-history"
    assert store.records[0].report.status == result["status"]
