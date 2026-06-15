from __future__ import annotations

import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from testing_agent.config import get_planning_llm
from testing_agent.models import TestCase, TestStep
from testing_agent.utils import extract_json

_SYSTEM = """You are a QA engineer. Parse a free-form test description into a structured test case.

Split the description into logical steps — each step is one user action plus what to verify.
Infer a clear expected result for every step even if the text does not spell it out explicitly.

Return ONLY valid JSON:
{
  "id": "tc_generated",
  "name": "Short descriptive name (5-10 words)",
  "description": "One sentence describing what this test validates",
  "start_url": "https://...",
  "severity": "critical|high|medium|low",
  "tags": ["tag1", "tag2"],
  "steps": [
    {
      "step": "Natural language action: what the user does",
      "expected": "What should be visible / what should happen after this action"
    }
  ]
}

Rules:
- If the input has numbered items (1) 2) 3) or 1. 2. 3.), each numbered item = EXACTLY ONE step.
  NEVER split a numbered item into sub-steps even if it contains multiple actions or "and"/"и".
- If the input has no numbers, split on clear topic changes only (e.g. login → product → checkout).
- Each step description must include ALL the actions from that numbered item — do not omit anything.
- Expected result must be specific and verifiable (visible text, URL change, element state)
- Infer start_url from context clues in the text
- Generate a short snake_case id like tc_cart_checkout
- PRESERVE navigation: if the input says "open product page X" or "navigate to X", the step MUST say "Open product page for X" — do NOT simplify to "click Add button"
- Keep the exact product names, credentials, and data values from the input in step descriptions
"""


def parse_txt(path: str | Path) -> TestCase:
    text = Path(path).read_text(encoding="utf-8").strip()

    url_override = None
    name_override = None
    for line in text.splitlines():
        low = line.strip().lower()
        if low.startswith("url:"):
            url_override = line.split(":", 1)[1].strip()
        elif low.startswith("name:"):
            name_override = line.split(":", 1)[1].strip()

    llm = get_planning_llm()

    # Count numbered items before calling LLM so we can enforce exact step count
    import re as _re
    numbered = _re.findall(r"(?m)^\s*\d+[\)\.]\s", text)
    step_count_hint = (
        f"\n\nCRITICAL: this input has exactly {len(numbered)} numbered items "
        f"({', '.join(str(i+1)+'.' for i in range(len(numbered)))}). "
        f"Your 'steps' array MUST have exactly {len(numbered)} elements — no more, no less."
    ) if len(numbered) >= 2 else ""

    print("  [TXT parser] Parsing free-form description into test case...")
    data: dict = {}
    for attempt in range(1, 4):
        raw = llm.invoke([SystemMessage(_SYSTEM), HumanMessage(text + step_count_hint)]).content
        data = extract_json(raw)
        steps_list = data.get("steps", [])
        # Validate step count when input has numbered items
        if steps_list and len(numbered) >= 2 and len(steps_list) != len(numbered):
            print(f"  [TXT parser] attempt {attempt}: got {len(steps_list)} steps, expected {len(numbered)} — retrying")
            data = {}
            continue
        if steps_list:
            break
        if not raw or not raw.strip():
            print(f"  [TXT parser] attempt {attempt}: LLM returned EMPTY string (len={len(raw)})")
        elif not data:
            print(f"  [TXT parser] attempt {attempt}: LLM returned unparseable output (len={len(raw)}): {raw[:200]!r}")
        else:
            print(f"  [TXT parser] attempt {attempt}: JSON has no 'steps' key. Keys: {list(data.keys())}. Output: {raw[:200]!r}")
        if attempt < 3:
            print("  [TXT parser] retrying...")

    if url_override:
        data["start_url"] = url_override
    if name_override:
        data["name"] = name_override

    steps = []
    for i, s in enumerate(data.get("steps", []), start=1):
        steps.append(TestStep(
            step_number=i,
            step=s.get("step", f"Step {i}"),
            expected=s.get("expected", ""),
        ))

    tc_id = data.get("id") or f"tc_{uuid.uuid4().hex[:8]}"

    print(f"  [TXT parser] '{data.get('name', tc_id)}' - {len(steps)} steps extracted")
    return TestCase(
        id=tc_id,
        name=data.get("name", tc_id),
        description=data.get("description", ""),
        start_url=data.get("start_url", ""),
        preconditions=[],
        steps=steps,
        tags=data.get("tags", []),
        severity=data.get("severity", "medium"),
    )
