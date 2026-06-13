# Урок 6. Planner как узел LangGraph

## Что соединяем

До этого существовали два независимых механизма.

LangGraph управлял процессом:

```text
state -> node -> state update
```

LangChain planner преобразовывал контекст в действие:

```text
TestCase + snapshot -> LLM -> BrowserAction
```

Теперь planner станет одним из узлов графа:

```text
START -> initialize -> plan -> END
```

Пока граф выполнит только один LLM-шаг. Цикл и browser executor подключим позже.

## Движение данных

Начальный state:

```python
{
    "test_case": TestCase(...),
    "page_snapshot": '- button "Login"',
}
```

После `initialize`:

```python
{
    "test_case": TestCase(...),
    "page_snapshot": '- button "Login"',
    "current_url": "https://example.com/login",
    "route": [],
    "step_count": 0,
    "status": "running",
}
```

Обратите внимание: `initialize` не возвращает `page_snapshot`, но поле не
исчезает. LangGraph объединяет partial update с существующим state.

После `plan`:

```python
{
    ...,
    "proposed_action": BrowserAction(...),
}
```

Planner node не выполняет действие. Он только сохраняет предложение модели.

## Новые поля `AgentState`

В state уже добавлены:

```python
page_snapshot: NotRequired[str]
proposed_action: NotRequired[BrowserAction]
```

Почему `BrowserAction`, а не `dict`: после structured output данные уже прошли
Pydantic-валидацию. Следующим узлам выгодно работать с доверенным контрактом.

Почему поля `NotRequired`: старые учебные графы запускаются без snapshot и
proposed action. В основном агенте позже можно будет выделить отдельные input и
internal state schemas.

## Проблема: node должен получить model

Обычный LangGraph node имеет вид:

```python
def plan(state: AgentState) -> dict:
```

Но planner требует модель:

```python
plan_next_action(model, test_case, page_snapshot)
```

Можно использовать глобальную переменную:

```python
model = ChatOllama(...)

def plan(state):
    ...
```

Но это плохой вариант:

- тесты зависят от реальной Ollama;
- сложно менять модель;
- конфигурация скрыта;
- один глобальный объект используется всеми запусками.

## Фабрика node и closure

Создадим функцию, которая принимает model и возвращает node:

```python
def make_plan_node(model):
    def plan(state: AgentState) -> dict:
        ...

    return plan
```

`make_plan_node` вызывается при сборке графа:

```python
plan_node = make_plan_node(model)
```

Возвращенная функция `plan` запоминает `model`. Это называется closure,
замыкание.

Простой пример:

```python
def make_multiplier(multiplier):
    def multiply(number):
        return number * multiplier

    return multiply


double = make_multiplier(2)
double(5)  # 10
```

Функция `double` продолжает помнить значение `2`, хотя
`make_multiplier` уже завершилась.

Так же node будет помнить переданную модель:

```python
plan_node = make_plan_node(fake_model)
```

или:

```python
plan_node = make_plan_node(ollama_model)
```

## Задание 6.1: фабрика node

Работайте в `src/browser_agent/planner_graph.py`.

Импортируйте:

```python
from browser_agent.planner import plan_next_action
from browser_agent.state import AgentState
```

Реализуйте:

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

Разберите каждый уровень:

- внешняя функция получает зависимость `model`;
- внутренняя функция соответствует интерфейсу LangGraph node;
- node читает state;
- вызывает уже готовый LangChain planner;
- возвращает partial update;
- внешняя функция возвращает node, но не выполняет его.

## Когда выполняется LLM-запрос

```python
plan_node = make_plan_node(model)
```

Здесь LLM-запроса нет. Создается функция-замыкание.

```python
plan_node(state)
```

Здесь node вызывает `plan_next_action`, внутри которого выполняется
`chain.invoke()`. При реальной модели здесь будет запрос к Ollama.

При запуске графа:

```python
graph.invoke(initial_state)
```

LangGraph сам дойдет до узла `plan` и вызовет `plan_node(current_state)`.

## Задание 6.2: граф

Импортируйте:

```python
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from browser_agent.graph import initialize
```

Реализуйте:

```text
START -> initialize -> plan -> END
```

При регистрации:

```python
builder.add_node("plan", make_plan_node(model))
```

Здесь второй аргумент является уже готовой функцией node.

Полная последовательность сборки:

1. Создать `StateGraph(AgentState)`.
2. Зарегистрировать `initialize`.
3. Создать и зарегистрировать `plan`.
4. Добавить три ребра.
5. Вызвать `compile()`.

## Почему model передается в graph builder

```python
graph = build_planner_graph(model)
```

Builder отвечает за wiring, то есть связывание зависимостей:

```text
какие nodes существуют
какие функции они выполняют
какие зависимости получают
как соединены переходами
```

В production:

```python
graph = build_planner_graph(ChatOllama(...))
```

В unit-тесте:

```python
graph = build_planner_graph(FakeStructuredModel())
```

Сам граф остается одинаковым.

## Unit-тест без Ollama

Fake model возвращает фиксированный `BrowserAction`. Тест проверяет:

- node сохранил действие в `proposed_action`;
- node вернул только измененное поле;
- граф сохранил исходный snapshot;
- `initialize` добавил свои поля;
- узлы выполнились в нужном порядке.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_planner_graph.py -q
```

Итог всех тестов:

```text
29 passed
```

## Что нужно понять

После урока объясните своими словами:

1. Почему planner является node, а не отдельным графом.
2. Что запоминает closure.
3. Когда реально вызывается LLM.
4. Почему node возвращает `proposed_action`, но не выполняет действие.
5. Почему fake model и Ollama можно подставить в один graph builder.
