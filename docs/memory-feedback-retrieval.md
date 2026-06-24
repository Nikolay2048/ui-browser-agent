# Memory, Persistence, Feedback And Retrieval

## Карта памяти агента

В проекте есть несколько разных видов памяти. Их важно не смешивать.

```text
AgentState
  краткосрочная рабочая память одного запуска

LangGraph checkpoint
  техническое сохранение state thread-а

RunReport
  стабильный итоговый артефакт одного запуска

RunHistoryRecord
  append-only эпизодическая память о завершенных runs

HumanFeedbackRecord
  человеческая коррекция поведения агента

Feedback retrieval
  выбор релевантных feedback records для нового запуска

memory_context
  текстовый блок, который planner получает в prompt
```

## AgentState

`AgentState` живет внутри одного запуска LangGraph.

Он содержит transient fields:

- текущий snapshot;
- proposed action;
- last result;
- route;
- status;
- counters;
- intermediate verdict/classification/report.

Почему AgentState не сохраняется как долговременная история:

- формат может меняться при развитии graph;
- там могут быть transient поля;
- не все поля нужны пользователю;
- state является runtime contract, а не stable artifact.

Поэтому для итогового результата есть `RunReport`.

## Checkpointing

Checkpointing нужен для thread-level persistence.

Пример:

```python
checkpointer = InMemorySaver()
thread_id = f"{test_case.id}:{uuid4()}"
config = build_thread_config(test_case, thread_id)
```

Зачем:

- human-in-the-loop approval;
- resume;
- debug snapshot;
- просмотр `snapshot.next`;
- восстановление выполнения graph.

Checkpoint не заменяет:

- run report;
- run history;
- feedback memory.

Он отвечает на вопрос:

```text
Где сейчас находится graph thread?
```

А run history отвечает:

```text
Что произошло в завершенном запуске?
```

## RunReport

Файл:

```text
src/browser_agent/reporting.py
```

`RunReport` строится из финального `AgentState`:

```python
RunReport(
    test_case=state["test_case"],
    status=state["status"],
    final_url=state["current_url"],
    final_snapshot=state["page_snapshot"],
    step_count=state["step_count"],
    failure_count=state["failure_count"],
    route=state["route"],
    termination=state["termination"],
    verdict=state.get("verdict"),
    classification=state.get("classification"),
    bug_report=state.get("bug_report"),
)
```

`RunReport` сохраняется в двух форматах:

- JSON для программного чтения;
- Markdown для человека.

Markdown создается через Jinja2, а не LLM. Это осознанное решение: report
должен быть deterministic rendering уже известных фактов.

## RunHistoryRecord

Файл:

```text
src/browser_agent/run_history.py
```

Модель:

```python
class RunHistoryRecord(BaseModel):
    run_id: str
    recorded_at: datetime
    report: RunReport
```

Зачем нужен отдельный record:

`RunReport` описывает результат запуска, но не содержит identity самого
сохранения. История добавляет:

- `run_id`;
- `recorded_at`;
- append-only semantics.

## JsonlRunHistoryStore

Запись:

```python
history_file.write(record.model_dump_json() + "\n")
```

Чтение:

```python
RunHistoryRecord.model_validate_json(line)
```

Почему JSONL:

- простой append;
- одна строка = один record;
- удобно grep/read;
- легко мигрировать в базу;
- достаточно для учебного проекта.

Ограничения:

- нет concurrency control;
- нет индексов;
- поврежденная строка ломает чтение;
- нет schema migration.

Для production можно заменить на:

- SQLite;
- Postgres;
- object storage;
- event log;
- LangSmith dataset.

## HumanFeedbackRecord

Файл:

```text
src/browser_agent/feedback.py
```

Модель:

```python
class HumanFeedbackRecord(BaseModel):
    feedback_id: str
    run_id: str
    test_case_id: str
    created_at: datetime
    scope: FeedbackScope
    step_number: int | None
    summary: str
    correction: str
    tags: list[str]
```

Feedback отвечает на вопрос:

```text
Что человек понял после просмотра результата?
```

Это отличается от run history:

```text
RunHistoryRecord     -> что агент сделал
HumanFeedbackRecord  -> что человек советует изменить
```

## FeedbackScope

Scopes:

```text
run
step
planner
judge
bug_report
```

Правило:

- если `scope == step`, `step_number` обязателен;
- если `scope != step`, `step_number` должен быть `None`.

Зачем:

Без scope feedback превращается в свободный комментарий, который трудно
использовать в retrieval и prompt.

## Feedback CLI

Файлы:

```text
src/browser_agent/feedback_cli.py
scripts/add_feedback.py
```

Команда:

```powershell
python scripts\add_feedback.py `
  --run-id "manual-seed" `
  --test-case-id first-real-agent `
  --scope planner `
  --summary "Planner should use stable locator for the task input." `
  --correction 'For the task input, prefer label=Task.' `
  --tags planner,locator
```

Почему CLI разделен на два слоя:

```text
feedback_cli.py     тестируемая логика
add_feedback.py     тонкий entrypoint
```

Это production-like pattern: "fat library, thin script".

## Feedback Retrieval

Файл:

```text
src/browser_agent/feedback_retrieval.py
```

Query:

```python
class FeedbackRetrievalQuery(BaseModel):
    test_case: TestCase
    scopes: list[FeedbackScope] = []
    required_tags: list[str] = []
    limit: int = 5
```

Фильтрация:

1. `record.test_case_id == query.test_case.id`;
2. если scopes заданы, `record.scope in query.scopes`;
3. если tags заданы, есть пересечение tags;
4. сортировка `created_at` от новых к старым;
5. ограничение `limit`.

## Почему deterministic retrieval перед RAG

Deterministic retrieval:

- легко тестировать;
- понятно объяснять;
- не требует embeddings;
- предсказуемо работает на маленьком проекте.

Semantic retrieval/RAG:

- ищет похожие формулировки;
- полезен для большого объема feedback;
- требует embedding model/vector store;
- сложнее оценивать.

Правильный порядок обучения:

```text
structured feedback
  -> deterministic retrieval
  -> prompt memory context
  -> evaluation
  -> semantic retrieval / RAG
```

## Memory Context

Файл:

```text
src/browser_agent/planner.py
```

`format_feedback_for_prompt()` возвращает:

```text
Previous human feedback:
1. [planner] Summary
   Correction: Correction
   Tags: planner, locator
```

`format_memory_context()` превращает пустое значение в:

```text
No previous human feedback is available.
```

Зачем:

Prompt остается стабильным и явно показывает модели, есть feedback или нет.

## Как feedback попадает в planner

Файл:

```text
src/browser_agent/runner.py
```

Runner строит контекст:

```python
query = FeedbackRetrievalQuery(
    test_case=test_case,
    scopes=[FeedbackScope.PLANNER, FeedbackScope.STEP],
)
records = retrieve_feedback_from_store(query, feedback_store)
memory_context = format_feedback_for_prompt(records)
```

Потом передает initial state:

```python
initial_state = {"test_case": test_case}
if feedback_store is not None:
    initial_state["memory_context"] = memory_context
```

Planner node читает:

```python
state.get("memory_context")
```

## Почему runner, а не planner

Planner не должен:

- читать JSONL;
- знать путь к файлу;
- делать retrieval;
- зависеть от storage.

Planner должен:

```text
runtime context -> BrowserAction
```

Runner должен:

```text
compose model, browser, graph, stores, reporting, memory
```

Это сохраняет dependency direction.

## Demo feedback

Коммитабельный пример:

```text
examples/feedback/first-real-agent.feedback.jsonl
```

Запуск:

```powershell
python scripts\run_real_agent.py --feedback-path examples\feedback\first-real-agent.feedback.jsonl
```

Локальный runtime feedback:

```text
artifacts/feedback/feedback.jsonl
```

`artifacts/` не должен коммититься.

## Типичные ошибки в memory системах

### Сразу класть всю память в prompt

Проблема: prompt раздувается и смешивает нерелевантные советы.

Решение: retrieval + limit.

### Исправлять только system prompt

Проблема: prompt превращается в список частных случаев.

Решение: сохранять feedback как данные.

### Не сохранять feedback_id / run_id

Проблема: невозможно понять происхождение подсказки.

Решение: structured feedback record.

### Не разделять scopes

Проблема: feedback для Judge попадет в Planner.

Решение: `FeedbackScope`.

### Считать feedback истиной

Проблема: feedback может устареть.

Решение: planner prompt явно говорит не следовать feedback, который
противоречит current page snapshot.

### Не измерять влияние memory

Проблема: кажется, что стало лучше, но это не доказано.

Решение для будущего: memory evaluation with/without feedback.
