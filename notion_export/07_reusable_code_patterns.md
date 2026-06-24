# Reusable Code Patterns

## Pattern 1. Pydantic Action Schema

Когда использовать:

Любой LLM должен вернуть действие/tool call.

Шаблон:

```python
class ToolAction(BaseModel):
    action: Literal["search", "open", "finish"]
    target: str | None = None
    value: str | None = None
    reason: str

    @model_validator(mode="after")
    def validate_action(self):
        if self.action == "open" and self.target is None:
            raise ValueError("open requires target")
        return self
```

Принцип:

```text
Prompt asks. Schema enforces.
```

## Pattern 2. Node Factory With Dependency Injection

Когда использовать:

LangGraph node должна использовать model/browser/store.

Шаблон:

```python
def make_plan_node(model):
    def plan(state: AgentState) -> dict:
        action = plan_next_action(
            model=model,
            test_case=state["test_case"],
            page_snapshot=state["page_snapshot"],
        )
        return {"proposed_action": action}

    return plan
```

Почему:

LangGraph вызывает node только со state, а dependency захватывается closure.

## Pattern 3. Router Function

Когда использовать:

Нужно выбрать next edge.

Шаблон:

```python
def route_after_execution(state: AgentState) -> str:
    if state["step_count"] >= state["test_case"].max_steps:
        return "fail_run"
    if state["last_result"].success:
        return "observe"
    return "fail_run"
```

Правило:

Router не делает side effects.

## Pattern 4. Deterministic Executor

Когда использовать:

LLM выбрала action, нужно выполнить tool.

Шаблон:

```python
def execute_action(tool, action: ToolAction) -> ToolResult:
    try:
        if action.action == "search":
            data = tool.search(action.target)
        elif action.action == "open":
            data = tool.open(action.target)
        return ToolResult(success=True, data=data)
    except Exception as error:
        return ToolResult(success=False, error=str(error))
```

## Pattern 5. Append-Only JSONL Store

Когда использовать:

Нужна простая persistence для history/events/feedback.

Шаблон:

```python
class JsonlStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: BaseModel) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(record.model_dump_json() + "\n")

    def load_all(self) -> list[Record]:
        if not self.path.exists():
            return []
        return [
            Record.model_validate_json(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
```

Production improvement:

Add line-number error handling.

## Pattern 6. Builder With Injectable Time And ID

Когда использовать:

Создаешь records with generated id/time but want tests deterministic.

Шаблон:

```python
def build_record(
    *,
    data: str,
    record_id: str | None = None,
    created_at: datetime | None = None,
) -> Record:
    if record_id is None:
        record_id = str(uuid4())
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    return Record(record_id=record_id, created_at=created_at, data=data)
```

## Pattern 7. Structured Output Chain

Когда использовать:

LLM должен вернуть Pydantic object.

Шаблон:

```python
def build_chain(model):
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ])
    structured_model = model.with_structured_output(OutputSchema)
    return prompt | structured_model
```

## Pattern 8. Fake Model For Tests

Когда использовать:

Unit tests for prompt/graph without real LLM.

Шаблон:

```python
class FakeModel:
    def __init__(self):
        self.prompt_text = ""

    def with_structured_output(self, schema):
        def respond(prompt_value):
            self.prompt_text = prompt_value.to_string()
            if schema is BrowserAction:
                return BrowserAction(...)
            if schema is JudgeVerdict:
                return JudgeVerdict(...)
            raise AssertionError(f"Unexpected schema: {schema}")

        return RunnableLambda(respond)
```

## Pattern 9. Report Builder + Renderer

Когда использовать:

Нужно сохранить итоговый artifact.

Шаблон:

```python
def build_report(state: AgentState) -> RunReport:
    return RunReport(...)

def render_report(report: RunReport) -> str:
    return template.render(report=report)

def save_report(report: RunReport, output_dir: Path):
    write_json(report)
    write_markdown(render_report(report))
```

Принцип:

```text
Build data first. Render later.
```

## Pattern 10. Retrieval Query Object

Когда использовать:

Memory retrieval has multiple filters.

Шаблон:

```python
class RetrievalQuery(BaseModel):
    test_case: TestCase
    scopes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1)
```

Почему не просто параметры функции:

- query удобно логировать;
- можно сериализовать;
- можно расширять;
- удобно тестировать.

## Pattern 11. Format Context For Prompt

Когда использовать:

Records нужно вставить в prompt.

Шаблон:

```python
def format_records_for_prompt(records: list[Record]) -> str:
    if not records:
        return ""

    lines = ["Relevant memory:"]
    for i, record in enumerate(records, 1):
        lines.append(f"{i}. {record.summary}")
        lines.append(f"   Correction: {record.correction}")
    return "\n".join(lines)
```

Не вставляй raw JSON, если модели нужен human-readable context.

## Pattern 12. CLI Thin Entrypoint

Когда использовать:

Нужен script but testable logic.

Файлы:

```text
src/app/cli.py
scripts/run_app.py
```

`scripts/run_app.py`:

```python
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from app.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

Вся логика в `src`.

## Pattern 13. Composition Runner

Когда использовать:

Нужно собрать model, tools, graph, stores, reports.

Шаблон:

```python
def run_agent(
    model,
    tool,
    task,
    on_state=None,
    history_store=None,
    memory_store=None,
) -> dict:
    graph = build_graph(model, tool)
    initial_state = {"task": task}
    if memory_store:
        initial_state["memory_context"] = build_memory_context(task, memory_store)

    final_state = None
    for state in graph.stream(initial_state):
        final_state = state
        if on_state:
            on_state(state)

    if history_store:
        history_store.append(build_history_record(final_state))

    return final_state
```

## Pattern 14. Safety Policy

Когда использовать:

Actions могут быть risky.

Шаблон:

```python
def assess_risk(action: Action) -> ApprovalDecision:
    if action.type == "delete":
        return ApprovalDecision(requires_approval=True, reason="delete action")
    return ApprovalDecision(requires_approval=False, reason="safe")
```

Use deterministic code for safety.

## Pattern 15. End-To-End Score

Когда использовать:

Нужно оценить полный run.

Шаблон:

```python
class Expectation(BaseModel):
    status: Literal["passed", "failed"]
    max_steps: int
    termination: str

def score_run(expected, final_state):
    return {
        "status_match": final_state["status"] == expected.status,
        "within_budget": final_state["step_count"] <= expected.max_steps,
    }
```

## Quick Copy Checklist For New Agent

- [ ] `domain.py`
- [ ] `state.py`
- [ ] `planner.py`
- [ ] `executor.py`
- [ ] `observer.py`
- [ ] `judge.py`
- [ ] `graph.py`
- [ ] `runner.py`
- [ ] `reporting.py`
- [ ] `memory.py`
- [ ] `evaluation.py`
- [ ] `scripts/run_*.py`
- [ ] `tests/test_*`
- [ ] `docs/architecture.md`
