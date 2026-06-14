from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from langchain_core.tools import tool

from testing_agent.browser_manager import BrowserManager


def _page():
    return BrowserManager.get_instance().page


def _save_screenshot(name: str) -> str:
    mgr = BrowserManager.get_instance()
    filename = f"{name}_{uuid.uuid4().hex[:6]}.png"
    path = str(Path(mgr.screenshots_dir) / filename)
    _page().screenshot(path=path, full_page=False)
    return path


@tool
def navigate_to_url(url: str) -> str:
    """Navigate the browser to a URL and wait for the page to load."""
    try:
        page = _page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(0.5)
        return f"Navigated to {url}. Title: '{page.title()}', URL: {page.url}"
    except Exception as e:
        return f"ERROR navigating to {url}: {e}"


@tool
def take_screenshot(name: str) -> str:
    """Take a screenshot and save it. Returns the file path. Use descriptive names."""
    try:
        path = _save_screenshot(name)
        return f"Screenshot saved: {path}"
    except Exception as e:
        return f"ERROR taking screenshot: {e}"


@tool
def get_page_context() -> str:
    """Get the current page state: URL, title, visible headings, alerts, and interactive elements.
    Call this first before deciding what action to take."""
    try:
        page = _page()
        url = page.url
        title = page.title()

        elements: list[str] = []

        for btn in page.locator("button:visible, [role='button']:visible, input[type='submit']:visible, input[type='button']:visible").all()[:20]:
            try:
                text = (
                    btn.inner_text().strip()
                    or btn.get_attribute("value") or ""
                    or btn.get_attribute("aria-label") or ""
                ).strip()
                if text:
                    elements.append(f"button: '{text}'")
            except Exception:
                pass

        for inp in page.locator("input:visible:not([type='hidden']):not([type='submit']):not([type='button']), textarea:visible, select:visible").all()[:20]:
            try:
                label = (
                    inp.get_attribute("placeholder")
                    or inp.get_attribute("aria-label")
                    or inp.get_attribute("name")
                    or inp.get_attribute("id")
                    or ""
                ).strip()
                itype = inp.get_attribute("type") or inp.evaluate("el => el.tagName.toLowerCase()") or "text"
                elements.append(f"input[{itype}]: placeholder/label='{label}'")
            except Exception:
                pass

        for link in page.locator("a:visible").all()[:15]:
            try:
                text = link.inner_text().strip()
                if text:
                    elements.append(f"link: '{text}'")
            except Exception:
                pass

        headings = []
        for h in page.locator("h1:visible, h2:visible, h3:visible").all()[:5]:
            try:
                headings.append(h.inner_text().strip())
            except Exception:
                pass

        alerts = []
        for alert in page.locator(
            "[class*='error']:visible, [class*='success']:visible, [class*='alert']:visible, "
            "[role='alert']:visible, .flash:visible, #flash:visible"
        ).all()[:5]:
            try:
                text = alert.inner_text().strip()
                if text:
                    alerts.append(text)
            except Exception:
                pass

        return json.dumps(
            {
                "url": url,
                "title": title,
                "headings": headings,
                "alerts_messages": alerts,
                "interactive_elements": elements[:40],
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return f"ERROR getting page context: {e}"


@tool
def click_by_text(text: str, exact: bool = False) -> str:
    """Click a visible element by its text content.
    exact=True for exact string match, False for partial match."""
    try:
        page = _page()
        locator = page.get_by_text(text, exact=exact)
        count = locator.count()
        if count == 0:
            return f"NOT_FOUND: No element with text '{text}'"
        locator.first.click(timeout=5000)
        time.sleep(0.5)
        return f"Clicked '{text}'. Now on: {page.url}"
    except Exception as e:
        return f"ERROR clicking text '{text}': {e}"


@tool
def click_by_role(role: str, name: str) -> str:
    """Click element by ARIA role and accessible name.
    role examples: button, link, menuitem, tab, checkbox, radio, combobox, textbox
    name: visible label or accessible name of the element"""
    try:
        page = _page()
        locator = page.get_by_role(role, name=name)  # type: ignore[arg-type]
        count = locator.count()
        if count == 0:
            return f"NOT_FOUND: No {role} with name '{name}'"
        locator.first.click(timeout=5000)
        time.sleep(0.5)
        return f"Clicked {role} '{name}'. Now on: {page.url}"
    except Exception as e:
        return f"ERROR clicking role={role} name='{name}': {e}"


@tool
def click_by_css(selector: str) -> str:
    """Click element by CSS selector. Use when role/text locators don't work."""
    try:
        page = _page()
        page.click(selector, timeout=5000)
        time.sleep(0.5)
        return f"Clicked '{selector}'. Now on: {page.url}"
    except Exception as e:
        return f"ERROR clicking CSS '{selector}': {e}"


@tool
def fill_by_label(label: str, value: str) -> str:
    """Fill an input field identified by its label text. Clears the field first."""
    try:
        page = _page()
        locator = page.get_by_label(label)
        if locator.count() == 0:
            return f"NOT_FOUND: No input with label '{label}'"
        locator.first.fill(value, timeout=5000)
        return f"Filled '{label}' with '{value}'"
    except Exception as e:
        return f"ERROR filling label '{label}': {e}"


@tool
def fill_by_placeholder(placeholder: str, value: str) -> str:
    """Fill an input field identified by its placeholder text."""
    try:
        page = _page()
        locator = page.get_by_placeholder(placeholder)
        if locator.count() == 0:
            return f"NOT_FOUND: No input with placeholder '{placeholder}'"
        locator.first.fill(value, timeout=5000)
        return f"Filled placeholder='{placeholder}' with '{value}'"
    except Exception as e:
        return f"ERROR filling placeholder '{placeholder}': {e}"


@tool
def fill_by_css(selector: str, value: str) -> str:
    """Fill an input by CSS selector."""
    try:
        _page().fill(selector, value, timeout=5000)
        return f"Filled CSS '{selector}' with '{value}'"
    except Exception as e:
        return f"ERROR filling CSS '{selector}': {e}"


@tool
def press_key(key: str) -> str:
    """Press a keyboard key. Examples: Enter, Tab, Escape, ArrowDown, Space, Backspace."""
    try:
        _page().keyboard.press(key)
        time.sleep(0.3)
        return f"Pressed '{key}'"
    except Exception as e:
        return f"ERROR pressing key '{key}': {e}"


@tool
def wait_for_text(text: str, timeout_ms: int = 8000) -> str:
    """Wait for specific text to appear on the page."""
    try:
        _page().wait_for_selector(f"text={text}", timeout=timeout_ms)
        return f"Text '{text}' appeared on page"
    except Exception as e:
        return f"TIMEOUT: '{text}' did not appear within {timeout_ms}ms"


@tool
def verify_text_visible(text: str) -> str:
    """Check if text is currently visible on the page. Returns VISIBLE or NOT_VISIBLE."""
    try:
        page = _page()
        locator = page.get_by_text(text)
        if locator.count() > 0 and locator.first.is_visible():
            return f"VISIBLE: '{text}' is visible"
        return f"NOT_VISIBLE: '{text}' is NOT visible on page"
    except Exception as e:
        return f"ERROR checking '{text}': {e}"


@tool
def verify_element_visible(selector: str) -> str:
    """Check if a CSS selector matches a visible element."""
    try:
        page = _page()
        el = page.locator(selector)
        if el.count() > 0 and el.first.is_visible():
            return f"VISIBLE: '{selector}'"
        return f"NOT_VISIBLE: '{selector}'"
    except Exception as e:
        return f"ERROR checking '{selector}': {e}"


@tool
def get_element_text(selector: str) -> str:
    """Get the text content of an element by CSS selector."""
    try:
        text = _page().locator(selector).first.inner_text(timeout=5000)
        return f"Text: '{text}'"
    except Exception as e:
        return f"ERROR getting text '{selector}': {e}"


@tool
def select_option(selector: str, value: str) -> str:
    """Select an option in a <select> element by CSS selector. value can be the option text or value attribute."""
    try:
        page = _page()
        try:
            page.select_option(selector, label=value, timeout=5000)
        except Exception:
            page.select_option(selector, value=value, timeout=5000)
        return f"Selected '{value}' in '{selector}'"
    except Exception as e:
        return f"ERROR selecting option: {e}"


@tool
def scroll_page(direction: str = "down") -> str:
    """Scroll the page. direction: up | down | top | bottom"""
    try:
        page = _page()
        actions = {
            "down": lambda: page.mouse.wheel(0, 400),
            "up": lambda: page.mouse.wheel(0, -400),
            "top": lambda: page.evaluate("window.scrollTo(0, 0)"),
            "bottom": lambda: page.evaluate("window.scrollTo(0, document.body.scrollHeight)"),
        }
        actions.get(direction, actions["down"])()
        time.sleep(0.3)
        return f"Scrolled {direction}"
    except Exception as e:
        return f"ERROR scrolling: {e}"


@tool
def mark_step_complete(status: str, actual_result: str, screenshot_name: str = "") -> str:
    """Mark the current test step as complete. MUST be called at the end of each step.
    status: 'passed' | 'failed' | 'broken'
    actual_result: describe what actually happened (what you observed on the page)
    screenshot_name: optional name for a final screenshot (leave empty to skip)"""
    try:
        screenshot_path = None
        if screenshot_name:
            screenshot_path = _save_screenshot(screenshot_name)

        BrowserManager.get_instance()._last_step_result = {
            "status": status,
            "actual_result": actual_result,
            "screenshot_path": screenshot_path,
        }
        return f"STEP_COMPLETE::{status}::{actual_result}"
    except Exception as e:
        return f"ERROR marking complete: {e}"


BROWSER_TOOLS = [
    navigate_to_url,
    take_screenshot,
    get_page_context,
    click_by_text,
    click_by_role,
    click_by_css,
    fill_by_label,
    fill_by_placeholder,
    fill_by_css,
    press_key,
    wait_for_text,
    verify_text_visible,
    verify_element_visible,
    get_element_text,
    select_option,
    scroll_page,
    mark_step_complete,
]
