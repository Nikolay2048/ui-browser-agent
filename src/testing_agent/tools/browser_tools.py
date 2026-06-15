from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from testing_agent.browser_manager import BrowserManager


def _page():
    return BrowserManager.get_instance().page


def _save_screenshot(name: str) -> str:
    mgr = BrowserManager.get_instance()
    filename = f"{name}_{uuid.uuid4().hex[:6]}.png"
    path = str(Path(mgr.screenshots_dir) / filename)
    _page().screenshot(path=path, full_page=False)
    return path


def _selector_hint(el) -> str:
    """Return the most useful CSS selector hint for an element: data-test > id > empty."""
    dt = el.get_attribute("data-test") or ""
    if dt:
        return f" [data-test='{dt}']"
    eid = el.get_attribute("id") or ""
    if eid:
        return f" [id='{eid}']"
    return ""


@tool
def navigate_to_url(
    url: Annotated[str, Field(description="Full URL to navigate to, including scheme, e.g. 'https://example.com/path'")],
) -> str:
    """Navigate the browser to a URL and wait for the page to load."""
    try:
        page = _page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(0.5)
        return f"Navigated to {url}. Title: '{page.title()}', URL: {page.url}"
    except Exception as e:
        return f"ERROR navigating to {url}: {e}"


@tool
def get_page_context() -> str:
    """Get the current page state: URL, title, headings, alerts, and interactive elements with their CSS selectors.
    Always call this first before deciding which action to take.
    Elements show [data-test='...'] or [id='...'] hints when available — use these in click_by_css for precision."""
    try:
        page = _page()
        elements: list[str] = []

        for btn in page.locator(
            "button:visible, [role='button']:visible, input[type='submit']:visible, input[type='button']:visible"
        ).all()[:20]:
            try:
                text = (
                    btn.inner_text().strip()
                    or btn.get_attribute("value") or ""
                    or btn.get_attribute("aria-label") or ""
                ).strip()
                if text:
                    elements.append(f"button: '{text}'{_selector_hint(btn)}")
            except Exception:
                pass

        for inp in page.locator(
            "input:visible:not([type='hidden']):not([type='submit']):not([type='button']), textarea:visible"
        ).all()[:20]:
            try:
                label = (
                    inp.get_attribute("placeholder")
                    or inp.get_attribute("aria-label")
                    or inp.get_attribute("name")
                    or inp.get_attribute("id")
                    or ""
                ).strip()
                itype = inp.get_attribute("type") or inp.evaluate("el => el.tagName.toLowerCase()") or "text"
                elements.append(f"input[{itype}]: placeholder/label='{label}'{_selector_hint(inp)}")
            except Exception:
                pass

        for sel in page.locator("select:visible").all()[:10]:
            try:
                cls = (sel.get_attribute("class") or "").strip().split()[0] if sel.get_attribute("class") else ""
                sname = sel.get_attribute("name") or sel.get_attribute("id") or ""
                css = f"select.{cls}" if cls else (f"select[name='{sname}']" if sname else "select")
                current = sel.input_value()
                elements.append(f"select[css='{css}']: current_value='{current}'")
            except Exception:
                pass

        for link in page.locator("a:visible").all()[:15]:
            try:
                text = link.inner_text().strip()
                if text:
                    elements.append(f"link: '{text}'{_selector_hint(link)}")
            except Exception:
                pass

        headings = []
        for h in page.locator(
            "h1:visible, h2:visible, h3:visible, "
            "[class*='title']:visible, [class*='heading']:visible, [role='heading']:visible"
        ).all()[:8]:
            try:
                text = h.inner_text().strip()
                if text and text not in headings:
                    headings.append(text)
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
                "url": page.url,
                "title": page.title(),
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
def click_by_text(
    text: Annotated[str, Field(description="Visible text of the element to click — use the exact label as shown on page, e.g. 'Submit', 'Continue', 'Sign in'")],
    exact: Annotated[bool, Field(description="True for exact full-string match (recommended for buttons and links). False for partial match (use when text is a substring of a longer label).")] = False,
) -> str:
    """Click the first visible element matching the given text content.
    Prefer click_by_role when the element has a clear ARIA role."""
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
def click_by_role(
    role: Annotated[str, Field(description="ARIA role of the element. Common values: 'button', 'link', 'menuitem', 'tab', 'checkbox', 'radio', 'combobox', 'textbox'")],
    name: Annotated[str, Field(description="Accessible name or visible label of the element, e.g. 'Submit', 'Close', 'Username'. Case-insensitive partial match.")],
) -> str:
    """Click an element by its ARIA role and accessible name. This is the preferred click strategy."""
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
def click_by_css(
    selector: Annotated[str, Field(description="CSS selector targeting the element. Prefer data-test/data-id attributes for reliability, e.g. '[data-test=\"delete-item\"]'. Also useful for nth-child or sibling selectors when multiple elements share the same label.")],
) -> str:
    """Click an element by CSS selector. Use this when click_by_role and click_by_text both fail,
    or when targeting a specific item among many with identical labels (e.g. multiple Remove buttons).
    Check get_page_context() output for [data-test='...'] hints on each element."""
    try:
        page = _page()
        page.click(selector, timeout=5000)
        time.sleep(0.5)
        return f"Clicked '{selector}'. Now on: {page.url}"
    except Exception as e:
        return f"ERROR clicking CSS '{selector}': {e}"


@tool
def hover(
    selector: Annotated[str, Field(description="CSS selector of the element to hover over, e.g. '.nav-menu', '[data-test=\"user-menu\"]'. Use to reveal dropdown menus or tooltips that appear on mouse-over.")],
) -> str:
    """Hover the mouse over an element without clicking. Use to trigger hover-only UI elements like dropdown menus or tooltips."""
    try:
        _page().hover(selector, timeout=5000)
        time.sleep(0.4)
        return f"Hovered over '{selector}'"
    except Exception as e:
        return f"ERROR hovering '{selector}': {e}"


@tool
def fill_by_label(
    label: Annotated[str, Field(description="Text of the <label> element associated with the input field, e.g. 'Email address', 'Password'. Must match the visible label text exactly.")],
    value: Annotated[str, Field(description="Value to type into the field. The field is cleared before typing.")],
) -> str:
    """Fill an input field identified by its visible label text. Preferred over fill_by_placeholder."""
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
def fill_by_placeholder(
    placeholder: Annotated[str, Field(description="Placeholder text visible inside the input when it is empty, e.g. 'Enter your email', 'Search...'. Use when no <label> element is present.")],
    value: Annotated[str, Field(description="Value to type into the field. The field is cleared before typing.")],
) -> str:
    """Fill an input field identified by its placeholder text. Use when fill_by_label returns NOT_FOUND."""
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
def fill_by_css(
    selector: Annotated[str, Field(description="CSS selector targeting the input element, e.g. '#username', 'input[name=\"email\"]'. Use as last resort when label and placeholder locators both fail.")],
    value: Annotated[str, Field(description="Value to type into the field. The field is cleared before typing.")],
) -> str:
    """Fill an input by CSS selector. Last-resort fallback after fill_by_label and fill_by_placeholder."""
    try:
        _page().fill(selector, value, timeout=5000)
        return f"Filled CSS '{selector}' with '{value}'"
    except Exception as e:
        return f"ERROR filling CSS '{selector}': {e}"


@tool
def press_key(
    key: Annotated[str, Field(description="Key name to press. Examples: 'Enter', 'Tab', 'Escape', 'ArrowDown', 'ArrowUp', 'Space', 'Backspace'. Use 'Enter' to submit forms.")],
) -> str:
    """Press a keyboard key on the currently focused element."""
    try:
        _page().keyboard.press(key)
        time.sleep(0.3)
        return f"Pressed '{key}'"
    except Exception as e:
        return f"ERROR pressing key '{key}': {e}"


@tool
def wait_for(
    target: Annotated[str, Field(description="What to wait for. Either visible text (e.g. 'Order confirmed') or a CSS selector (e.g. '[data-test=\"result-table\"]', '.spinner'). If the value starts with a CSS class, id, or bracket — it is treated as a selector; otherwise as text.")],
    timeout_ms: Annotated[int, Field(description="Maximum time to wait in milliseconds. Default 8000. Use 15000+ for slow page transitions or heavy async loads.")] = 8000,
) -> str:
    """Wait for text or a CSS element to become visible. Use after actions that trigger async updates, navigation, or dynamic content loading."""
    page = _page()
    is_selector = target.startswith((".", "#", "[", "//", "input", "button", "select", "a ", "div", "span"))
    try:
        if is_selector:
            page.wait_for_selector(target, state="visible", timeout=timeout_ms)
            return f"Element '{target}' is now visible"
        else:
            page.get_by_text(target).first.wait_for(state="visible", timeout=timeout_ms)
            return f"Text '{target}' appeared on page"
    except Exception:
        return f"TIMEOUT: '{target}' did not appear within {timeout_ms}ms"


@tool
def verify_text_visible(
    text: Annotated[str, Field(description="Text to check for visibility on the current page. Use the exact string as it appears in the UI, e.g. 'Order confirmed', 'Invalid credentials'.")],
) -> str:
    """Check if text is currently visible on the page. Returns VISIBLE or NOT_VISIBLE.
    Use to confirm expected results after each action."""
    try:
        page = _page()
        locator = page.get_by_text(text)
        if locator.count() > 0 and locator.first.is_visible():
            return f"VISIBLE: '{text}' is visible"
        return f"NOT_VISIBLE: '{text}' is NOT visible on page"
    except Exception as e:
        return f"ERROR checking '{text}': {e}"


@tool
def verify_element_visible(
    selector: Annotated[str, Field(description="CSS selector of the element to check, e.g. '.success-banner', '[data-test=\"submit-btn\"]', '#confirmation-message'. Returns VISIBLE or NOT_VISIBLE.")],
) -> str:
    """Check if a CSS selector matches a currently visible element on the page."""
    try:
        page = _page()
        el = page.locator(selector)
        if el.count() > 0 and el.first.is_visible():
            return f"VISIBLE: '{selector}'"
        return f"NOT_VISIBLE: '{selector}'"
    except Exception as e:
        return f"ERROR checking '{selector}': {e}"


@tool
def verify_url(
    expected: Annotated[str, Field(description="Expected URL or URL fragment to match. Can be a full URL ('https://example.com/dashboard') or a path/keyword contained in the URL ('/dashboard', 'checkout'). Partial match is used.")],
) -> str:
    """Verify the current page URL contains the expected string. Use after navigation or form submission to confirm the redirect happened."""
    page = _page()
    current = page.url
    if expected in current:
        return f"URL_MATCH: current URL '{current}' contains '{expected}'"
    return f"URL_MISMATCH: current URL '{current}' does not contain '{expected}'"


@tool
def get_element_count(
    selector: Annotated[str, Field(description="CSS selector to count matching elements, e.g. '.cart-item', 'tr.product-row', '[data-test^=\"item-\"]'.")],
) -> str:
    """Count how many visible elements match a CSS selector.
    Use to verify list lengths, cart item counts, search result counts."""
    try:
        count = _page().locator(selector).count()
        return f"COUNT: {count} element(s) match '{selector}'"
    except Exception as e:
        return f"ERROR counting '{selector}': {e}"


@tool
def get_element_text(
    selector: Annotated[str, Field(description="CSS selector of the element whose text content to read, e.g. 'span.cart-count', '.total-price', '#status-message'.")],
) -> str:
    """Get the visible text content of an element by CSS selector.
    Use to read dynamic values like counters, prices, or status messages."""
    try:
        text = _page().locator(selector).first.inner_text(timeout=5000)
        return f"Text: '{text}'"
    except Exception as e:
        return f"ERROR getting text '{selector}': {e}"


@tool
def get_element_attribute(
    selector: Annotated[str, Field(description="CSS selector targeting the element, e.g. '.product-image img', '#username', '[data-id=\"item-1\"]'")],
    attribute: Annotated[str, Field(description="HTML attribute name to read. Examples: 'src' for image URL, 'href' for link target, 'value' for input value, 'data-test' for test IDs, 'aria-label' for accessible names. Note: use get_element_text() for visible text, not 'innerText' here.")],
) -> str:
    """Get the value of an HTML attribute from an element.
    Use for checking image src, link href, input value, or data-*/aria-* attributes."""
    try:
        el = _page().locator(selector).first
        val = el.get_attribute(attribute, timeout=5000)
        if val is None:
            return f"ATTRIBUTE_NOT_FOUND: '{attribute}' not present on '{selector}'"
        return f"'{selector}' [{attribute}] = '{val}'"
    except Exception as e:
        return f"ERROR getting attribute '{attribute}' on '{selector}': {e}"


@tool
def select_option(
    selector: Annotated[str, Field(description="CSS selector of the <select> element, e.g. 'select.sort-dropdown', 'select[name=\"sort\"]'. Get the exact selector from get_page_context() output.")],
    value: Annotated[str, Field(description="Option to select — either the visible option text (e.g. 'Newest first') or the option's value attribute. The tool tries text match first, then value attribute.")],
) -> str:
    """Select an option in a <select> dropdown element."""
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
def scroll_page(
    direction: Annotated[str, Field(description="Scroll direction: 'down' (one viewport down), 'up' (one viewport up), 'top' (jump to page top), 'bottom' (jump to page bottom).")] = "down",
) -> str:
    """Scroll the page to reveal off-screen content. Use before verify_text_visible if element might be below the fold."""
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
def mark_step_complete(
    status: Annotated[str, Field(description="Step outcome: 'passed' if the expected result was observed, 'failed' if the actual result differs from expected, 'broken' if a tool error or unexpected exception prevented execution.")],
    actual_result: Annotated[str, Field(description="What actually happened — describe what you observed: current URL, visible text, element states, error messages. Be specific enough that a human could understand without seeing the browser.")],
    screenshot_name: Annotated[str, Field(description="Optional short name for a final screenshot, e.g. 'step1_login_passed', 'step3_error'. Leave empty to skip the screenshot.")] = "",
) -> str:
    """Mark the current test step as complete. MUST be the last tool call in every step.
    Do not call any other tools after this one."""
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
    get_page_context,
    click_by_role,
    click_by_text,
    click_by_css,
    hover,
    fill_by_label,
    fill_by_placeholder,
    fill_by_css,
    press_key,
    select_option,
    scroll_page,
    wait_for,
    verify_text_visible,
    verify_element_visible,
    verify_url,
    get_element_text,
    get_element_count,
    get_element_attribute,
    mark_step_complete,
]
