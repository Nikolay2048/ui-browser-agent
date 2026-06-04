from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


@tool
def navigate(url: str) -> str:
    """Open page."""
    return f"Opened {url}"


llm = ChatOpenAI(
    model="qwen3:14b",
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    temperature=0,
)

llm_with_tools = llm.bind_tools([navigate])

response = llm_with_tools.invoke(
    "Открой example.com"
)

print(response)
print("CONTENT:", response.content)
print("TOOL_CALLS:", response.tool_calls)