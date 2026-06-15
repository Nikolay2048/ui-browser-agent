from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from testing_agent.config import NUM_CTX, PLANNING_MODEL
from testing_agent.models import TestCase, TestStep

_SYSTEM = """/no_think
You are a QA engineer. Parse a free-form test description into a structured test case.

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
- Each step must be a single coherent action (login, add item, remove item, fill form, click button)
- Expected result must be specific and verifiable (visible text, URL change, element state)
- Infer start_url from context clues in the text
- Generate a short snake_case id like tc_cart_checkout
- PRESERVE navigation: if the input says "open product page X" or "navigate to X", the step MUST say "Open product page for X" — do NOT simplify to "click Add button"
- Keep the exact product names (Sauce Labs Backpack, etc.) in step descriptions
"""


def parse_txt(path: str | Path) -> TestCase:
    text = Path(path).read_text(encoding="utf-8").strip()

    # Extract explicit url: and name: directives to override LLM output afterwards
    url_override = None
    name_override = None
    for line in text.splitlines():
        low = line.strip().lower()
        if low.startswith("url:"):
            url_override = line.split(":", 1)[1].strip()
        elif low.startswith("name:"):
            name_override = line.split(":", 1)[1].strip()

    # Pass the full file text to the LLM — it handles url:/name: lines fine
    context = text

    llm = ChatOllama(
        model=PLANNING_MODEL,
        temperature=0,
        num_ctx=NUM_CTX,
        num_predict=4096,
        reasoning=False,
    )

    print("  [TXT parser] Parsing free-form description into test case...")
    data: dict = {}
    for attempt in range(1, 4):
        raw = llm.invoke([SystemMessage(_SYSTEM), HumanMessage(context)]).content
        data = _parse_json(raw)
        if data.get("steps"):
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


def _parse_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {}
