"""Completed browser observer after lesson 9."""

from browser_agent.state import AgentState


def observe_browser(browser) -> dict:
    snapshot = browser.snapshot()
    return {
        "current_url": browser.current_url,
        "page_snapshot": snapshot,
    }


def make_observe_node(browser):
    def observe(_state: AgentState) -> dict:
        return observe_browser(browser)

    return observe
