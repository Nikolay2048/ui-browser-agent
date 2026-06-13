# Урок 2. Состояние и первый LangGraph

## Что такое агент с точки зрения LangGraph

Агент — не одна функция, вызывающая LLM. Это конечный автомат:

```text
state -> node -> state update -> next node
```

`State` содержит память одного запуска. Узлы читают состояние и возвращают
только изменившиеся поля. Граф определяет порядок вызова узлов.

Это важное разделение:

- модели из первого урока описывают доменные данные;
- `AgentState` описывает состояние процесса;
- node выполняет одну операцию;
- graph управляет переходами.

## Задание 2.1: `AgentState`

В `src/browser_agent/state.py` создайте `AgentState` на основе `TypedDict`.

Поля:

- `test_case: TestCase`;
- `current_url: str`;
- `route: list[ActionResult]`;
- `step_count: int`;
- `status: Literal["running", "passed", "failed"]`.

`test_case` поступает на вход графа. Остальные поля создает узел `initialize`.
Подумайте, как выразить это через `Required` и `NotRequired`.

Пока reducer для `route` не нужен. Его добавим, когда несколько узлов начнут
добавлять шаги независимо.

## Задание 2.2: узлы

В `src/browser_agent/graph.py` реализуйте:

```python
def initialize(state: AgentState) -> dict:
    ...


def complete(state: AgentState) -> dict:
    ...
```

`initialize` возвращает:

```python
{
    "current_url": state["test_case"].start_url,
    "route": [],
    "step_count": 0,
    "status": "running",
}
```

`complete` возвращает только:

```python
{"status": "passed"}
```

Почему только изменившееся поле: LangGraph объединяет update с текущим state.
Если каждый узел возвращает полную копию, сложнее понимать владение данными и
легче случайно затереть результат другого узла.

## Задание 2.3: граф

Соберите:

```text
START -> initialize -> complete -> END
```

Используйте:

```python
from langgraph.graph import END, START, StateGraph
```

Функция `build_learning_graph()` должна возвращать скомпилированный граф.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

После первого урока должны проходить 11 тестов. Новые три теста сначала будут
падать. Итог второго урока:

```text
14 passed
```

## Что важно понять

Будьте готовы объяснить:

1. Почему state лучше представить `TypedDict`, а не глобальной переменной.
2. Чем state отличается от Pydantic-модели `TestCase`.
3. Почему nodes возвращают частичный update.
4. Что делает `compile()`.
5. Почему в этом графе пока нет ничего агентного.
