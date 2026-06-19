from browser_agent.graph import build_agent_graph
from src.browser_agent.models import TestCase

graph = build_agent_graph()

test_case =TestCase(

    id="1",
    name="test case",
    start_url="",
    goal="test_case",
)
result = graph.invoke({
    "test_case": test_case,
})

print(result)
