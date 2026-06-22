from langchain_core.runnables import RunnableLambda

from browser_agent.domain import (
    BrowserAction,
    ExpectedResultCheck,
    JudgeVerdict,
    TestCase as AgentTestCase,
)
from browser_agent.runner import run_agent


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


def test_run_agent_can_save_final_report(tmp_path) -> None:
    test_case = AgentTestCase(
        id="runner-report",
        name="Open page",
        start_url="https://example.com",
        goal="Verify page is available",
        expected=["Page is available"],
    )

    result = run_agent(
        FinishModel(),
        StaticBrowser(),
        test_case,
        report_dir=tmp_path,
    )

    assert result["status"] == "passed"
    assert (tmp_path / "runner-report.json").is_file()
    assert (tmp_path / "runner-report.md").is_file()
