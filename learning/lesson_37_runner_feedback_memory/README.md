# Урок 37. Runner feedback memory

## Цель урока

Мы уже подготовили все части по отдельности:

```text
feedback.jsonl
  -> JsonlFeedbackStore
  -> retrieve_feedback()
  -> format_feedback_for_prompt()
  -> planner memory_context
```

Но полный запуск агента пока сам это не связывает.

В этом уроке подключаем feedback memory в `run_agent()`:

```python
run_agent(
    model=model,
    browser=browser,
    test_case=test_case,
    feedback_store=JsonlFeedbackStore("artifacts/feedback/feedback.jsonl"),
)
```

Runner должен:

1. взять feedback records из store;
2. выбрать релевантные записи для текущего `test_case`;
3. отформатировать их в `memory_context`;
4. передать `memory_context` в initial state графа;
5. planner увидит эту память через `state["memory_context"]`.

## Где это находится в архитектуре

До урока:

```text
run_agent()
  -> graph.stream({"test_case": test_case})
  -> planner receives no feedback memory
```

После урока:

```text
run_agent()
  -> if feedback_store:
       retrieve feedback
       format memory_context
  -> graph.stream({
       "test_case": test_case,
       "memory_context": memory_context
     })
  -> planner receives memory_context
```

## Почему это делает runner, а не planner

Planner отвечает за:

```text
goal + snapshot + history + memory_context -> BrowserAction
```

Runner отвечает за composition:

```text
browser
graph
reporting
history
feedback memory
```

Если planner сам начнет читать `artifacts/feedback/feedback.jsonl`, он станет
зависеть от файловой системы и конкретного storage. Тогда будет сложнее:

- тестировать planner;
- запускать evaluation без памяти;
- сравнивать режимы with memory / without memory;
- заменить JSONL на vector DB.

Поэтому runner получает store снаружи и подготавливает context.

## Почему feedback_store optional

Baseline должен остаться простым:

```python
run_agent(model, browser, test_case)
```

Memory-enabled режим:

```python
run_agent(model, browser, test_case, feedback_store=store)
```

Это важно для evaluation:

```text
same test case
same model
without feedback memory -> result A
with feedback memory    -> result B
```

Если память всегда включена, сравнение будет сложнее.

## Какие feedback записи нужны planner

Не весь feedback одинаково полезен planner-у.

Например:

```text
scope=planner
scope=step
```

обычно полезны для выбора следующего действия.

А:

```text
scope=judge
scope=bug_report
```

лучше использовать позже в Judge или Reporter.

Поэтому в runner для planner memory используем scopes:

```python
[FeedbackScope.PLANNER, FeedbackScope.STEP]
```

Tags пока не фильтруем. Пусть retrieval вернет последние подсказки по текущему
test case для planner-related scopes.

## Почему memory_context должен быть в initial state

LangGraph state — это рабочая память запуска.

Если мы передаем:

```python
{"test_case": test_case, "memory_context": "..."}
```

то дальше все ноды могут видеть это поле.

Но в нашем графе использовать его будет только planner:

```python
state.get("memory_context")
```

Это нормально. State может содержать данные, нужные не всем нодам.

## Нужно ли сохранять memory_context в report?

Пока нет.

Почему:

- `RunReport` сейчас описывает результат выполнения;
- memory context может быть длинным;
- мы еще не решили, как показывать memory evidence в отчете;
- сейчас наша цель — проверить, что planner реально получает context.

Позже можно добавить:

```text
used_feedback_ids
memory_context_summary
```

Но не сейчас.

## Задание 37.1. Добавить helper в runner

Файл:

```text
src/browser_agent/runner.py
```

Создай функцию:

```python
def build_feedback_memory_context(
    test_case: TestCase,
    feedback_store,
) -> str:
    ...
```

Логика:

1. Создать `FeedbackRetrievalQuery`:

```python
FeedbackRetrievalQuery(
    test_case=test_case,
    scopes=[FeedbackScope.PLANNER, FeedbackScope.STEP],
)
```

2. Получить records:

```python
records = retrieve_feedback_from_store(query, feedback_store)
```

3. Вернуть:

```python
format_feedback_for_prompt(records)
```

Если records нет, formatter вернет пустую строку. Это нормально: planner потом
превратит пустую строку в `"No previous human feedback is available."`.

## Задание 37.2. Расширить `run_agent`

Добавь параметр:

```python
feedback_store=None
```

Перед `graph.stream(...)` сформируй initial state:

```python
initial_state = {"test_case": test_case}

if feedback_store is not None:
    initial_state["memory_context"] = build_feedback_memory_context(
        test_case,
        feedback_store,
    )
```

И передай:

```python
graph.stream(initial_state, ...)
```

вместо:

```python
graph.stream({"test_case": test_case}, ...)
```

## Задание 37.3. Tests

Я добавил тесты:

```text
tests/test_runner_feedback_memory.py
```

Они проверяют:

- без `feedback_store` runner работает как раньше;
- с `feedback_store` planner prompt получает relevant feedback;
- `scope=judge` не попадает в planner memory;
- feedback другого test case не попадает в prompt.

## Задание 37.4. Подключить к `run_real_agent.py`

После тестов можно подключить реальный запуск.

Файл:

```text
scripts/run_real_agent.py
```

Добавь:

```python
from browser_agent.feedback import JsonlFeedbackStore
```

Создай store:

```python
feedback_path = PROJECT_ROOT / "artifacts" / "feedback" / "feedback.jsonl"
feedback_store = JsonlFeedbackStore(feedback_path)
```

Передай в `run_agent()`:

```python
feedback_store=feedback_store,
```

И напечатай путь:

```python
print(f"feedback: {feedback_path}")
```

Если файла нет, `JsonlFeedbackStore.load_all()` вернет `[]`, запуск не должен
падать.

## Как проверить

Точечно:

```powershell
python -m pytest tests\test_runner_feedback_memory.py -q
```

Связанные тесты:

```powershell
python -m pytest tests\test_runner.py tests\test_planner_memory_context.py tests\test_feedback_retrieval.py tests\test_runner_feedback_memory.py -q
```

Полностью:

```powershell
python -m pytest -q
```

## Критерий готовности

Урок завершен, когда:

- `run_agent()` принимает `feedback_store`;
- runner строит `memory_context` до запуска графа;
- planner получает feedback memory через state;
- baseline без feedback_store не сломан;
- `run_real_agent.py` подключает `artifacts/feedback/feedback.jsonl`;
- все тесты проходят.
