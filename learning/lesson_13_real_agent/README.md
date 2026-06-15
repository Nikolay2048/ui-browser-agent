# Урок 13. Первый настоящий UI-агент

## Результат урока

Мы впервые соединим все созданные компоненты:

```text
TestCase
   ↓
LangGraph
   ↓
Observer → accessibility snapshot
   ↓
Ollama → BrowserAction
   ↓
Executor → ExecutionStep
   ↓
PlaywrightBrowser → видимый Chromium
```

Агент самостоятельно откроет страницу, прочитает её, выберет и выполнит
действия, сохранит трассу и продолжит цикл до завершения.

Это первая вертикальная интеграция проекта: один тест-кейс проходит через все
слои системы.

## Что такое composition root

**Composition root** — место, где приложение создаёт реальные зависимости:

```python
model = ChatOllama(...)
chromium = playwright.chromium.launch(...)
page = chromium.new_page()
browser = PlaywrightBrowser(page)
graph = build_agent_graph(model, browser)
```

У нас будет два уровня.

### CLI-скрипт

```text
scripts/run_real_agent.py
```

Он владеет внешними ресурсами:

- конфигурацией Ollama;
- процессом Playwright;
- Chromium и страницей;
- ожиданием перед закрытием окна.

Кто создал ресурс, тот обычно и закрывает его.

### Runner

```text
src/browser_agent/runner.py
```

Он получает готовые зависимости:

```python
run_agent(model, browser, test_case, on_state)
```

и отвечает только за orchestration:

```text
open start_url → build graph → stream states → return final state
```

Runner не должен импортировать `ChatOllama` или `sync_playwright`. Благодаря
dependency injection его можно тестировать без внешних процессов.

## Почему URL открывает runner

Нода `initialize` записывает URL в словарь:

```python
{"current_url": test_case.start_url}
```

Но изменение `AgentState` не выполняет навигацию Chromium. Настоящее воздействие:

```python
browser.open(test_case.start_url)
```

должно произойти до первого `observe`. Иначе observer прочитает `about:blank`.

```text
browser.open()
    ↓
graph starts
    ↓
initialize
    ↓
observe reads the opened page
```

## `invoke()` и `stream()`

### `invoke`

```python
result = graph.invoke({"test_case": test_case})
```

Запускает граф до конца и возвращает финальное состояние.

### `stream_mode="updates"`

Возвращает частичное обновление каждой ноды:

```python
{"observe": {"page_snapshot": "..."}}
{"plan": {"proposed_action": ...}}
```

### `stream_mode="values"`

После каждого шага возвращает полное объединённое состояние:

```python
{
    "route": [...],
    "step_count": 1,
    "status": "running",
    "page_snapshot": "...",
    "proposed_action": ...,
    "last_result": ...,
}
```

Для консольного интерфейса и будущего web UI удобнее полное состояние. Поэтому
runner использует:

```python
graph.stream({"test_case": test_case}, stream_mode="values")
```

## Callback `on_state`

Runner принимает необязательную функцию:

```python
on_state: Callable[[dict], None] | None
```

После каждого состояния:

```python
if on_state is not None:
    on_state(state)
```

CLI может печатать состояние:

```python
run_agent(..., on_state=print_state)
```

Тест может собирать его:

```python
states = []
run_agent(..., on_state=states.append)
```

Будущий web UI сможет публиковать его через WebSocket. Runner сообщает о
событии, но не решает, как его отображать. Это inversion of control.

## Как получить финальное состояние из stream

`graph.stream()` возвращает iterator. Нужно сохранить последнее значение:

```python
final_state = None

for state in graph.stream(...):
    final_state = state

if final_state is None:
    raise RuntimeError("Agent graph produced no state")

return final_state
```

Явная проверка документирует инвариант: успешно запущенный граф обязан выдать
хотя бы одно состояние.

## Контракт между snapshot и target

Accessibility snapshot выглядит так:

```text
- textbox "Task"
- button "Add"
```

Но adapter принимает не описание snapshot, а наш язык локаторов:

```text
role=button[name="Add"]
label=Task
text=Learn AI Agents
css=.some-selector
```

Planner должен знать преобразование:

```text
snapshot: textbox "Task"
target:   label=Task

snapshot: button "Add"
target:   role=button[name="Add"]
```

Pydantic проверяет форму `BrowserAction`, но обычный тип `str` не проверяет
грамматику target. Поэтому формат описывается в system prompt, а adapter
проводит окончательную runtime-проверку.

```text
prompt-инструкция
    +
structured output
    +
детерминированная проверка adapter
```

Prompt уменьшает вероятность ошибки. Код устанавливает настоящую границу.

## Один цикл настоящего агента

Первый snapshot:

```text
- textbox "Task"
- button "Add"
```

Первое решение LLM:

```python
BrowserAction(
    action="fill",
    target="label=Task",
    value="Learn AI Agents",
    reason="Enter the requested task.",
)
```

Executor вызывает Playwright, делает screenshot и создаёт `ExecutionStep 1`.
После нового observe модель выбирает:

```python
BrowserAction(
    action="click",
    target='role=button[name="Add"]',
    value=None,
    reason="Submit the task.",
)
```

Когда задача появляется на странице, planner возвращает `finish`.

## Важное ограничение

Сейчас planner сам решает, что цель достигнута. Поэтому `passed` пока означает:

```text
planner решил завершить сценарий
```

а не:

```text
независимая проверка доказала все expected results
```

Позже отдельный Judge будет проверять ожидаемые результаты по evidence.

## Задание 13.1. Target contract в prompt

Работай в:

```text
src/browser_agent/planner.py
```

Расширь `SYSTEM_PROMPT`. Он должен содержать точную фразу:

```text
Only use one of these target formats
```

И четыре примера:

```text
role=button[name="Login"]
label=Username
text=Products
css=.some-selector
```

Объясни модели:

- `role` использовать для кнопок и элементов с accessibility role;
- `label` использовать для полей формы;
- `text` использовать для видимого текста;
- `css` использовать только как запасной вариант;
- нельзя придумывать элемент, отсутствующий в snapshot.

Не меняй human prompt и Pydantic-модели.

Проверка:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_planner.py -q
```

## Задание 13.2. Runner

Работай в:

```text
src/browser_agent/runner.py
```

Импортируй:

```python
from browser_agent.graph import build_agent_graph
```

Реализуй:

1. `browser.open(test_case.start_url)`.
2. `graph = build_agent_graph(model, browser)`.
3. `final_state = None`.
4. Цикл по `graph.stream(..., stream_mode="values")`.
5. Сохранение каждого state в `final_state`.
6. Вызов `on_state(state)`, если callback передан.
7. `RuntimeError`, если ни одного state не получено.
8. Возврат финального state.

Проверка:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_runner.py -q
```

## Полная проверка

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Ожидается:

```text
39 passed
```

## Первый полный запуск

Проверь точное имя локальной модели:

```powershell
ollama list
```

Скрипт по умолчанию использует `qwen3.5:35b`. Если имя отличается:

```powershell
$env:OLLAMA_MODEL="точное-имя-модели"
```

После прохождения тестов:

```powershell
.\.venv\Scripts\python.exe scripts\run_real_agent.py
```

Он использует настоящую Ollama, видимый Chromium и локальную HTML-страницу.
Screenshots сохраняются в:

```text
artifacts/first-real-agent/
```

## Как отлаживать

Поставь breakpoints:

- `runner.py` — цикл `graph.stream`;
- `observer.py` — получение snapshot;
- `planner.py` — `chain.invoke`;
- `executor.py` — создание `ExecutionStep`;
- `browser.py` — `_resolve_target`;
- `graph.py` — router-функции.

Если target неверный, исследуй:

```text
snapshot → SYSTEM_PROMPT → proposed_action.target
```

Если target правильный, но действие упало:

```text
proposed_action.target → _resolve_target → Playwright locator
```

## Возможные сбои

- Ollama недоступна: запусти приложение или `ollama serve`.
- Модель не найдена: установи `OLLAMA_MODEL` по выводу `ollama list`.
- `Unsupported target`: модель нарушила target contract.
- Элемент не найден: target допустим, но не соответствует текущей странице.
- `max_steps`: planner повторяет действия или не распознаёт цель.

## Вопросы для самопроверки

1. Чем composition root отличается от логики агента?
2. Почему runner получает model и browser снаружи?
3. Почему `browser.open()` вызывается до первого observe?
4. Чем `stream_mode="values"` отличается от `"updates"`?
5. Зачем callback лучше встроенного `print()`?
6. Почему prompt не заменяет runtime-валидацию?
7. Сколько раз вызывается LLM при двух browser actions и `finish`?
8. Кто отвечает за закрытие Chromium?
9. Почему текущий `passed` ещё не является надёжным QA-вердиктом?
