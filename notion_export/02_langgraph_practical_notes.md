# LangGraph Practical Notes

## Что такое LangGraph

LangGraph - библиотека для построения stateful agent workflows.

Она помогает описать:

- state;
- nodes;
- edges;
- conditional routing;
- loops;
- checkpointing;
- human-in-the-loop interrupts.

Если LangChain - это про runnable components, prompts and models, то LangGraph -
это про управление процессом.

## Базовые элементы

### State

State - общий dict-like объект, который проходит через граф.

Пример:

```python
class AgentState(TypedDict):
    test_case: Required[TestCase]
    page_snapshot: NotRequired[str]
    proposed_action: NotRequired[BrowserAction]
    route: NotRequired[list[ExecutionStep]]
```

### Node

Node - функция, которая принимает state и возвращает partial update.

```python
def observe(state: AgentState) -> dict:
    return {
        "page_snapshot": browser.snapshot(),
        "current_url": browser.current_url,
    }
```

Node не обязан возвращать весь state. Только изменившиеся поля.

### Edge

Edge - переход между nodes.

```python
builder.add_edge("observe", "plan")
```

### Conditional Edge

Conditional edge вызывает router function.

```python
builder.add_conditional_edges(
    "plan",
    route_planned_action,
    {
        "judge": "judge",
        "execute": "execute",
    },
)
```

Router возвращает ключ:

```python
def route_planned_action(state: AgentState) -> str:
    if state["proposed_action"].action == BrowserActionType.FINISH:
        return "judge"
    return "execute"
```

## `add_node`

Да, обычно:

```python
builder.add_node("node_name", function)
```

Первый аргумент - имя node в graph.

Второй аргумент - callable, который будет выполнен.

Пример:

```python
builder.add_node("plan", make_plan_node(model))
```

Здесь `make_plan_node(model)` возвращает функцию:

```python
def plan(state: AgentState) -> dict:
    ...
```

Почему фабрика:

Node должна иметь доступ к `model`, но LangGraph будет вызывать ее только со
state. Closure позволяет захватить model.

## `add_edge`

Обычно:

```python
builder.add_edge("from_node", "to_node")
```

Обе строки - имена nodes.

Особые nodes:

```python
START
END
```

Пример:

```python
builder.add_edge(START, "initialize")
builder.add_edge("pass_run", END)
```

## Node vs Router

Node:

- делает работу;
- может вызвать LLM/tool;
- возвращает state update.

Router:

- не делает side effects;
- смотрит на state;
- возвращает имя следующего пути.

Плохо:

```python
def route(state):
    browser.click(...)
    return "observe"
```

Хорошо:

```python
def route(state):
    if state["last_result"].success:
        return "observe"
    return "fail_run"
```

## Цикл агента

Пример:

```text
observe -> plan -> execute -> observe
```

В LangGraph цикл делается обычным edge назад:

```python
builder.add_conditional_edges(
    "execute",
    route_after_execution,
    {
        "observe": "observe",
        "fail_run": "fail_run",
    },
)
```

## Почему нужны лимиты

Любой автономный agent loop должен иметь ограничения:

- `max_steps`;
- `max_failures`;
- timeout;
- budget;
- approval boundary.

Без лимитов агент может повторять ошибку бесконечно.

## Partial State Updates

Node возвращает partial update:

```python
return {"proposed_action": action}
```

LangGraph объединяет update с текущим state.

Практическое правило:

```text
Node не должен возвращать весь state без необходимости.
```

## Не мутировать входной state

Плохо:

```python
state["route"].append(step)
return {"route": state["route"]}
```

Лучше:

```python
return {"route": [*state["route"], step]}
```

Почему:

- проще тестировать;
- меньше hidden side effects;
- лучше для checkpoint/replay;
- легче искать, где изменился state.

## `stream()` vs `invoke()`

`invoke()`:

```python
result = graph.invoke({"test_case": test_case})
```

Возвращает итоговое состояние.

`stream()`:

```python
for state in graph.stream(..., stream_mode="values"):
    print(state)
```

Позволяет видеть промежуточные states.

Для debug UI-agent лучше `stream()`, потому что видно:

- что planner предложил;
- что executor сделал;
- где route изменился;
- когда Judge сработал.

## Checkpointing

Checkpointing сохраняет graph state по `thread_id`.

```python
config = {
    "configurable": {"thread_id": thread_id}
}
```

Зачем:

- resume;
- human approval;
- debug;
- долгие workflows.

Важно:

```text
checkpointer без thread_id - ошибка архитектуры
```

## Interrupt / Human-in-the-loop

LangGraph `interrupt()` позволяет остановить graph и ждать input человека.

Пример:

```python
resume_value = interrupt(payload)
decision = ActionApproval.model_validate(resume_value)
```

Flow:

```text
plan
  -> request_approval
  -> interrupt
  -> human input
  -> resume
  -> execute or reject
```

## Типичная структура graph builder

```python
def build_agent_graph(model, browser, checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("initialize", initialize)
    builder.add_node("observe", make_observe_node(browser))
    builder.add_node("plan", make_plan_node(model))
    builder.add_node("execute", make_execute_node(browser))
    builder.add_node("judge", make_judge_node(model))

    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "observe")
    builder.add_edge("observe", "plan")

    builder.add_conditional_edges(...)

    return builder.compile(checkpointer=checkpointer)
```

## Checklist для нового LangGraph агента

- [ ] Есть TypedDict/Pydantic state contract.
- [ ] Есть initialize node.
- [ ] Все nodes возвращают partial updates.
- [ ] Routers не имеют side effects.
- [ ] Есть START и END paths.
- [ ] Все loops ограничены.
- [ ] Есть failure path.
- [ ] Есть tests для routers.
- [ ] Есть tests для graph happy path.
- [ ] Есть tests для failure path.
- [ ] Если есть interrupt, есть checkpointing/thread_id.
- [ ] Есть visualization/debug способ.
- [ ] Есть streaming output для диагностики.

## Частые ошибки

### Node не возвращает dict

LangGraph ожидает update. Если вернуть модель или строку, state merge сломается.

### Router возвращает ключ, которого нет в mapping

Проверяй:

```python
return "execute"
```

и mapping:

```python
{"execute": "execute"}
```

### Состояние не инициализировано

Если `route` не создан в initialize, planner/executor могут упасть.

### Слишком большая node

Node не должна делать все. Разделяй:

```text
observe
plan
execute
judge
classify
report
```

### Graph node читает внешний файл

Лучше передать данные в state до запуска или через injected dependency.

### Смешивать workflow и domain logic

Graph должен связывать компоненты, а не содержать всю бизнес-логику.
