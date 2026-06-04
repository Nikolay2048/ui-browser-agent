from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="qwen3:14b",
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    temperature=0,
)

response = llm.invoke("Ответь одним словом: работает?")
print(response.content)