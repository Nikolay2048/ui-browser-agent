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

    observation = observe_browser(browser)

    assert observation == {
        "current_url": "https://example.com/login",
        "page_snapshot": '- textbox "Username"\n- button "Login"',
    }
    assert browser.snapshot_calls == 1


def test_observe_node_returns_partial_state_update() -> None:
    browser = FakeBrowser()
    observe_node = make_observe_node(browser)

    update = observe_node({"status": "running"})

    assert update == {
        "current_url": "https://example.com/login",
        "page_snapshot": '- textbox "Username"\n- button "Login"',
    }
