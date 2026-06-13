"""Browser observer from lesson 9.

Implement the observation function and node factory described in
docs/lessons/09-browser-observer.md.
"""
from browser_agent.state import AgentState


def observe_browser(browser) -> dict:
    """read the current URL and page snapshot from the browser adapter."""
    snapshot = browser.snapshot()
    return {
        "current_url": browser.current_url,
        "page_snapshot": snapshot,
    }


def make_observe_node(browser):
    """return a LangGraph node that writes observation into state."""

    def observe(_state: AgentState) -> dict:
        return observe_browser(browser)

    return observe
