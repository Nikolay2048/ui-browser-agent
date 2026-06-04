import asyncio

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = """
Ты UI testing agent.

Правила:
- Сначала используй browser_navigate.
- После навигации используй browser_snapshot.
- Для действий используй refs из browser_snapshot.
- Не используй browser_close.
- Не используй browser_run_code_unsafe.
- Не используй browser_evaluate.
- После каждого действия проверяй состояние через browser_snapshot.
"""


async def main():
    client = MultiServerMCPClient(
        {
            "playwright": {
                "transport": "stdio",
                "command": "npx",
                "args": ["@playwright/mcp@latest"],
            }
        }
    )

    async with client.session("playwright") as session:
        loaded_tools = await load_mcp_tools(session)

        allowed = {
            "browser_navigate",
            "browser_snapshot",
            "browser_click",
            "browser_type",
            "browser_press_key",
            "browser_wait_for",
        }

        tools = {
            tool.name: tool
            for tool in loaded_tools
            if tool.name in allowed
        }

        print("Loaded tools:")
        for name in tools:
            print("-", name)

        llm = ChatOpenAI(
            model="qwen3:14b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
            temperature=0,
        )

        llm_with_tools = llm.bind_tools(list(tools.values()))

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content="""
                Открой https://demo.playwright.dev/todomvc
                
                Создай две задачи:
                1. Learn MCP
                2. Learn LangChain
                
                Отметь первую задачу выполненной.
                
                В конце скажи:
                - сколько всего задач
                - сколько выполненных
                - сколько активных
                """
            ),
        ]

        for step in range(1, 30):
            print(f"\n=== STEP {step} ===")

            ai_msg = await llm_with_tools.ainvoke(messages)

            print("AI CONTENT:", ai_msg.content)
            print("TOOL CALLS:", ai_msg.tool_calls)

            messages.append(ai_msg)

            if not ai_msg.tool_calls:
                print("\n=== FINAL ===")
                print(ai_msg.content)
                return

            for tool_call in ai_msg.tool_calls:
                tool_name = tool_call["name"]
                args = tool_call["args"]
                tool_call_id = tool_call["id"]

                print(f"\nCALL TOOL: {tool_name}")
                print("ARGS:", args)

                try:
                    result = await tools[tool_name].ainvoke(args)
                    result_text = str(result)
                except Exception as e:
                    result_text = f"TOOL ERROR: {type(e).__name__}: {e}"

                messages.append(
                    ToolMessage(
                        content=result_text,
                        tool_call_id=tool_call_id,
                    )
                )


if __name__ == "__main__":
    asyncio.run(main())
