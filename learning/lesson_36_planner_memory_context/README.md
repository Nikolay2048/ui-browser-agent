# Урок 36. Planner memory context

## Цель урока

Мы уже сделали:

```text
HumanFeedbackRecord
JsonlFeedbackStore
Feedback retrieval
format_feedback_for_prompt()
```

Теперь нужно подготовить planner к использованию этой памяти.

Важно: в этом уроке мы **не читаем feedback-файл внутри planner** и **не меняем
runner**.

Сегодня задача уже и точнее:

```text
planner должен уметь принять готовый memory_context и добавить его в prompt
```

То есть:

```python
plan_next_action(
    model=model,
    test_case=test_case,
    page_snapshot=page_snapshot,
    route=route,
    memory_context="Previous human feedback: ..."
)
```

А в следующем уроке мы подключим retrieval:

```text
feedback store -> retrieve_feedback -> format_feedback_for_prompt -> planner
```

## Почему не читать feedback внутри planner

Плохой вариант:

```python
def plan_next_action(...):
    store = JsonlFeedbackStore("artifacts/feedback/feedback.jsonl")
    records = store.load_all()
    ...
```

Почему это плохо:

- planner становится зависимым от файловой системы;
- unit tests planner-а становятся тяжелее;
- нельзя легко подменить память в evaluation;
- нельзя запускать planner в режиме "без памяти";
- нельзя сравнить baseline vs memory;
- prompt-логика смешивается с retrieval-логикой.

Правильный вариант:

```text
retrieval layer готовит memory_context
planner только вставляет memory_context в prompt
```

Это разделение ответственности:

```text
feedback_retrieval.py
  отвечает за выбор памяти

planner.py
  отвечает за превращение runtime context в BrowserAction
```

## Что такое memory context

`memory_context` — это уже готовый текстовый блок, который можно дать модели:

```text
Previous human feedback:
1. [planner] Planner selected a fragile locator.
   Correction: Use label=Task for the task input.
   Tags: planner, locator
```

Planner не должен знать:

- откуда пришел этот текст;
- из JSONL он или из vector DB;
- сколько records было найдено;
- какие retrieval-правила использовались.

Planner получает строку и использует ее как дополнительный контекст.

## Почему memory context должен быть optional

Обычный режим агента должен продолжить работать:

```python
plan_next_action(model, test_case, page_snapshot)
```

Новый режим:

```python
plan_next_action(
    model,
    test_case,
    page_snapshot,
    memory_context="..."
)
```

Это важно для evaluation:

```text
baseline planner
planner + memory
```

Если memory context обязательный, baseline станет неудобным.

## Как prompt должен говорить модели о feedback

Feedback — это не приказ выполнить конкретное действие всегда.

Плохо:

```text
Always follow previous feedback.
```

Почему плохо:

- feedback может быть устаревшим;
- feedback может относиться к похожему, но не идентичному сценарию;
- feedback может конфликтовать с текущим snapshot;
- модель может начать игнорировать реальные элементы страницы.

Лучше:

```text
Use previous human feedback when it is relevant to the current goal and page.
Do not follow feedback that contradicts the current page snapshot.
```

Ключевой принцип:

```text
snapshot остается источником правды о текущей странице
feedback — вспомогательная подсказка
```

Это особенно важно для UI-агента. Нельзя нажимать кнопку только потому, что
когда-то feedback сказал "нажимай Save", если в текущем snapshot нет такой
кнопки.

## Где вставлять memory в prompt

Сейчас human prompt примерно такой:

```text
Goal:
...

Test data:
...

Expected results:
...

Execution history:
...

Current page:
...
```

Добавим блок:

```text
Previous human feedback:
{memory_context}
```

Лучше поставить его перед `Execution history`.

Почему:

- goal/test data/expected описывают задачу;
- feedback дает прошлые уроки;
- execution history описывает текущий запуск;
- current page остается последним и самым свежим контекстом.

Порядок:

```text
Goal
Test data
Expected
Previous human feedback
Execution history
Current page
```

## Что делать, если memory_context пустой

Нельзя оставлять странный пустой раздел:

```text
Previous human feedback:


Execution history:
...
```

Лучше передавать явную фразу:

```text
No previous human feedback is available.
```

Зачем:

- prompt стабильнее;
- тесты проще;
- модель не додумывает, что блок случайно потерялся.

В этом уроке добавим функцию:

```python
format_memory_context(memory_context: str | None) -> str
```

Правила:

- `None` -> `"No previous human feedback is available."`
- `""` -> `"No previous human feedback is available."`
- строка из пробелов -> `"No previous human feedback is available."`
- нормальная строка -> stripped string

## Задание 36.1. Добавить `format_memory_context`

Файл:

```text
src/browser_agent/planner.py
```

Функция:

```python
def format_memory_context(memory_context: str | None) -> str:
    ...
```

## Задание 36.2. Добавить memory в prompt

В `build_planner_prompt()` добавь в human message:

```text
Previous human feedback:
{memory_context}
```

И в system prompt добавь смысловое правило:

```text
Use previous human feedback when it is relevant to the current goal and page.
Do not follow feedback that contradicts the current page snapshot.
```

Не нужно переписывать весь prompt. Добавь только необходимое.

## Задание 36.3. Расширить `plan_next_action`

Сейчас:

```python
def plan_next_action(model, test_case, page_snapshot, route=None):
```

Нужно:

```python
def plan_next_action(
    model,
    test_case,
    page_snapshot,
    route=None,
    memory_context: str | None = None,
):
```

В `chain.invoke(...)` добавить:

```python
"memory_context": format_memory_context(memory_context)
```

## Задание 36.4. Расширить `make_plan_node`

Пока `AgentState` еще не содержит memory. Но node может безопасно читать:

```python
state.get("memory_context")
```

Передай это в `plan_next_action`.

## Задание 36.5. Обновить `AgentState`

Файл:

```text
src/browser_agent/state.py
```

Добавь:

```python
memory_context: NotRequired[str]
```

Это не значит, что graph уже сам заполняет это поле. Мы просто разрешаем state
нести такой контекст.

## Задание 36.6. Tests

Я добавил тесты в:

```text
tests/test_planner_memory_context.py
```

Запуск:

```powershell
python -m pytest tests\test_planner_memory_context.py -q
```

Потом:

```powershell
python -m pytest -q
```

## Критерий готовности

Урок завершен, когда:

- `format_memory_context()` работает;
- planner prompt содержит блок previous human feedback;
- `plan_next_action()` принимает `memory_context`;
- `make_plan_node()` прокидывает `state.get("memory_context")`;
- старые planner tests не сломаны;
- полный `pytest` проходит.
