"""Test with actual txt_parser prompt."""
import requests
from pathlib import Path

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
- PRESERVE navigation: if the input says "open product page X" or "navigate to X", the step MUST say "Open product page for X"
- Keep the exact product names (Sauce Labs Backpack, etc.) in step descriptions
"""

text = Path("test_cases/saucedemo/tc_multi_cart_checkout.txt").read_text(encoding="utf-8").strip()

for np in [4096, 8000, 16000]:
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": "qwen3.5:35b",
        "messages": [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": text}],
        "stream": False, "format": "json",
        "options": {"temperature": 0, "num_predict": np, "num_ctx": 8192}
    }, timeout=300).json()
    content = r.get("message", {}).get("content", "")
    thinking_len = len(r.get("message", {}).get("thinking", ""))
    done = r.get("done_reason", "?")
    print(f"np={np}: content_len={len(content)}, think_len={thinking_len}, done={done} | {repr(content[:60])}")
