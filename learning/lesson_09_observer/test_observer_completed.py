from browser_agent.observer import make_observe_node, observe_browser


class FakeBrowser:
    def __init__(self) -> None:
        self.current_url = "https://example.com/login"
        self.snapshot_calls = 0

    def snapshot(self) -> str:
        self.snapshot_calls += 1
        return '- textbox "Username"\n- button "Login"'


def test_observe_browser_reads_browser_state() -> None:
    browser = FakeBrowser()
    assert observe_browser(browser) == {
        "current_url": "https://example.com/login",
        "page_snapshot": '- textbox "Username"\n- button "Login"',
    }


def test_observe_node_returns_partial_update() -> None:
    update = make_observe_node(FakeBrowser())({"status": "running"})
    assert "page_snapshot" in update
