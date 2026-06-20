import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from browser_agent.graph import build_agent_graph
from src.browser_agent.models import TestCase
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]

model_name = os.getenv("OLLAMA_MODEL", "qwen3.6:35b")
print(f"model name: {model_name}")
fixture_url = (
        PROJECT_ROOT / "examples" / "playwright_fixture.html"
    ).resolve().as_uri()
test_case = TestCase(
    id="first-real-agent",
    name="Create a task using the autonomous agent",
    start_url=fixture_url,
    goal="Add the task 'Learn AI Agents' to the task list",
    test_data={"task": "Learn AI Agents"},
    expected=["Learn AI Agents is visible in the task list"],
    max_steps=5,
)
model = ChatOllama(
    model=model_name,
    temperature=0,
    validate_model_on_init=True,
)

test_case =TestCase(

    id="1",
    name="test case",
    start_url="",
    goal="test_case",
)

browser= None
graph = build_agent_graph(model, browser)

print(graph.get_graph().draw_ascii())
png_data = graph.get_graph().draw_mermaid_png()

with open("graph.png", "wb") as f:
    f.write(png_data)

result = graph.invoke({
    "test_case": test_case,
})

print(result)
