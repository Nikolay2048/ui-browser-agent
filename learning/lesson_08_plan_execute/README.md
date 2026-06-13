# Урок 8. Первый сквозной граф: plan → execute

## Что уже готово

У нас есть независимые компоненты:

```text
initialize(state)
```

Создает внутренние поля запуска.

```text
make_plan_node(model)
```

Создает node, который вызывает LangChain planner и записывает:

```python
{"proposed_action": BrowserAction(...)}
```

```text
make_execute_node(browser)
```

Создает node, который выполняет `proposed_action` и записывает:

```python
{
    "last_result": ActionResult(...),
    "step_count": ...,
}
```

Теперь мы не пишем новую бизнес-логику. Мы соединяем готовые компоненты.

## Целевой граф

```text
START
  ↓
initialize
  ↓
plan
  ↓
execute
  ↓
END
```

Это первый сквозной проход:

```text
тест-кейс
  → planner выбирает действие
  → executor выполняет действие
  → результат сохраняется в state
```

Пока выполняется только одно действие. Цикл добавим позже.

## Состояние по шагам

### Вход

```python
{
    "test_case": TestCase(...),
    "page_snapshot": '- textbox "Username"',
}
```

### После `initialize`

```python
{
    "test_case": TestCase(...),
    "page_snapshot": '- textbox "Username"',
    "current_url": "https://example.com/login",
    "route": [],
    "step_count": 0,
    "status": "running",
}
```

### После `plan`

```python
{
    ...,
    "proposed_action": BrowserAction(
        action="fill",
        target="label=Username",
        value="standard_user",
        reason="...",
    ),
}
```

### После `execute`

```python
{
    ...,
    "last_result": ActionResult(
        success=True,
        url_before="https://example.com/login",
        url_after="https://example.com/login",
        screenshot_path="artifacts/001-fill.png",
    ),
    "step_count": 1,
}
```

## Что такое wiring

Wiring — сборка системы из компонентов:

```text
какой node использует какую функцию;
какой node получает какую зависимость;
в каком порядке выполняются nodes.
```

`agent_graph.py` должен заниматься wiring, а не содержать реализацию planner или
executor.

Плохо:

```python
def build_agent_graph(model, browser):
    def plan(state):
        # Повтор всей логики planner
        ...

    def execute(state):
        # Повтор dispatch executor
        ...
```

Хорошо:

```python
plan_node = make_plan_node(model)
execute_node = make_execute_node(browser)
```

Мы переиспользуем проверенные компоненты.

## Две зависимости

Graph builder принимает:

```python
def build_agent_graph(model, browser):
```

`model` нужен узлу `plan`.

`browser` нужен узлу `execute`.

Сам `initialize` внешних зависимостей не требует.

Сборщик графа является composition root — местом, где создаются и связываются
компоненты приложения.

В production:

```python
graph = build_agent_graph(
    model=ChatOllama(...),
    browser=PlaywrightBrowser(...),
)
```

В unit-тесте:

```python
graph = build_agent_graph(
    model=FakeStructuredModel(),
    browser=FakeBrowser(),
)
```

Структура графа одинакова. Отличаются только реализации зависимостей.

## Когда выполняются функции

При сборке:

```python
plan_node = make_plan_node(model)
execute_node = make_execute_node(browser)
```

Создаются closures. LLM и browser еще не вызываются.

При компиляции:

```python
graph = builder.compile()
```

LangGraph проверяет структуру. LLM и browser все еще не вызываются.

При запуске:

```python
result = graph.invoke(initial_state)
```

Тогда LangGraph выполняет:

```text
initialize(state)
plan_node(updated_state)     → вызов model
execute_node(updated_state)  → вызов browser
```

## Задание

Работайте в `src/browser_agent/agent_graph.py`.

Импортируйте:

```python
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from browser_agent.executor import make_execute_node
from browser_agent.graph import initialize
from browser_agent.planner_graph import make_plan_node
from browser_agent.state import AgentState
```

Реализуйте `build_agent_graph(model, browser)`.

### Шаг 1. Builder

```python
builder = StateGraph(AgentState)
```

### Шаг 2. Регистрация узлов

```python
builder.add_node("initialize", initialize)
builder.add_node("plan", make_plan_node(model))
builder.add_node("execute", make_execute_node(browser))
```

Обратите внимание:

```python
initialize
```

уже является node-функцией.

Но:

```python
make_plan_node(model)
```

сначала создает node-функцию.

То же относится к executor.

### Шаг 3. Ребра

```text
START → initialize
initialize → plan
plan → execute
execute → END
```

Все переходы безусловные, поэтому используется `add_edge`.

### Шаг 4. Компиляция

Верните:

```python
builder.compile()
```

## Что проверяет тест

Fake model предлагает `fill`.

Fake browser записывает вызовы:

```python
[
    ("fill", "label=Username", "standard_user"),
    ("screenshot",),
]
```

Затем тест проверяет итоговый state:

- действие planner сохранено;
- executor вернул успех;
- счетчик увеличен до `1`;
- статус остался `running`.

Почему `running`: граф закончился технически, но бизнес-сценарий еще не
завершен. `END` означает конец текущего графа, а не обязательно успешное
достижение пользовательской цели.

Позже Judge изменит статус на `passed` или `failed`.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agent_graph.py -q
```

Итог:

```text
33 passed
```

## Что нужно понять

1. Почему graph builder не содержит бизнес-логику planner и executor.
2. Почему model и browser передаются при сборке.
3. Почему при `compile()` ничего не выполняется.
4. Где во время `invoke()` вызывается LLM.
5. Почему `END` не означает автоматически `status="passed"`.
