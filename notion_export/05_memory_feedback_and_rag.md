# Memory, Feedback And RAG

## Главная идея memory

Memory нужна не для того, чтобы "запихнуть весь прошлый опыт в prompt".

Memory нужна, чтобы:

```text
store many facts
retrieve few relevant facts
format them for current task
measure whether they helped
```

## Виды памяти

### Working Memory

Живет внутри одного запуска.

Пример:

```text
AgentState
```

Содержит:

- текущий snapshot;
- route;
- step_count;
- proposed_action;
- last_result.

### Episodic Memory

История прошлых событий.

Пример:

```text
RunHistoryRecord
```

Отвечает:

```text
Что агент сделал в прошлом запуске?
```

### Feedback Memory

Человеческие коррекции.

Пример:

```text
HumanFeedbackRecord
```

Отвечает:

```text
Что человек советует делать иначе?
```

### Semantic Memory

Знания, которые ищутся по смысловой близости.

Пример:

```text
embedding search over feedback corrections
```

### Procedural Memory

Общие правила поведения.

Пример:

```text
Use label locators for input fields.
Never copy accessibility snapshot syntax into BrowserAction target.
```

Может быть в prompt, policy или learned examples.

## Feedback Record: минимальная schema

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

Почему нужны поля:

- `feedback_id` - ссылаться на подсказку;
- `run_id` - связать с запуском;
- `test_case_id` - exact retrieval;
- `scope` - понять, кому подсказка: planner/judge/reporter;
- `step_number` - привязать к route;
- `summary` - что было не так;
- `correction` - как делать лучше;
- `tags` - фильтрация.

## Хороший feedback

Плохо:

```text
Опять неправильно.
```

Хорошо:

```text
Summary:
Planner selected the wrong locator for the Task input.

Correction:
Use target {"strategy": "label", "value": "Task"}.
Do not copy snapshot text like textbox "Task" into target.

Tags:
planner, locator
```

## Feedback scopes

```text
run         общий комментарий ко всему запуску
step        конкретный route step
planner     выбор действия
judge       проверка результата
bug_report  качество bug report
```

Почему scope важен:

Feedback для Judge не должен автоматически попадать в Planner prompt.

## Deterministic Retrieval

Первый retrieval должен быть простым:

```python
query = FeedbackRetrievalQuery(
    test_case=test_case,
    scopes=[FeedbackScope.PLANNER, FeedbackScope.STEP],
    required_tags=[],
    limit=5,
)
```

Фильтры:

```text
same test_case_id
scope in allowed scopes
tags intersect required_tags
sort newest first
limit
```

Плюсы:

- легко тестировать;
- легко объяснять;
- не нужны embeddings.

Минусы:

- не найдет похожий сценарий с другим id.

## Semantic Retrieval / RAG

RAG pipeline:

```text
documents/records
  -> chunking
  -> embeddings
  -> vector store
  -> similarity search
  -> reranking/filtering
  -> prompt context
  -> answer/action
```

Для feedback:

```text
HumanFeedbackRecord
  -> text representation
  -> embedding
  -> vector search by current test_case.goal/page/problem
```

Пример searchable text:

```text
Scope: planner
Test case: first-real-agent
Summary: Planner selected fragile locator.
Correction: Use label=Task for task input.
Tags: planner, locator
```

## Hybrid Retrieval

Лучше всего часто работает hybrid:

```text
exact filters
  + semantic similarity
  + recency
  + tags/scope
```

Пример scoring:

```text
score =
  0.45 * semantic_similarity
  + 0.25 * same_test_case
  + 0.15 * tag_overlap
  + 0.15 * recency
```

Но начинать с этого рано. Сначала нужны deterministic tests.

## Memory Context

Memory context - это не raw records, а форматированный prompt block.

Пример:

```text
Previous human feedback:
1. [planner] Planner should prefer stable structured targets.
   Correction: Use label=Task for the task input.
   Tags: planner, locator
```

Правила:

- коротко;
- evidence-oriented;
- не противоречить snapshot;
- ограничить количество записей;
- сохранять порядок relevance.

## Memory не должна быть приказом

Prompt должен говорить:

```text
Use previous human feedback when relevant.
Do not follow feedback that contradicts the current page snapshot.
```

Почему:

- сайт мог измениться;
- feedback мог быть ошибочным;
- сценарий может быть похожим, но не идентичным.

## Что нужно логировать про memory

В production стоит сохранять:

```text
memory_enabled
retrieval_query
used_feedback_ids
memory_context
memory_context_hash
retrieval_scores
```

Зачем:

- объяснить поведение;
- откатить плохой feedback;
- оценить пользу memory;
- повторить run.

## Memory Evaluation

Минимальный эксперимент:

```text
case A without memory -> action X
case A with memory    -> action Y
expected action       -> Y
```

Метрики:

- action changed;
- exact match improved;
- route shorter;
- fewer failures;
- no new false positives.

Важно:

Memory может вредить. Нужны negative cases:

```text
irrelevant feedback exists
agent should ignore it
```

## Когда добавлять RAG

Добавляй RAG, когда:

- feedback records стало много;
- exact `test_case_id` недостаточно;
- есть похожие сценарии;
- есть evaluation dataset;
- есть способ измерить retrieval quality.

Не добавляй RAG, если:

- нет structured records;
- нет deterministic baseline;
- нет metrics;
- prompt и так нестабилен.

## RAG mistakes

### Chunking без смысла

Если chunk содержит половину feedback record, retrieval может вернуть
бессмысленный контекст.

Для structured feedback лучше embedding делать на целый record или специально
собранный text representation.

### Только cosine similarity

Semantic match может найти похожий текст, но wrong scope.

Нужны filters:

```text
scope=planner
test domain
tags
recency
```

### Нет eval

RAG без evaluation часто создает ощущение умности, но не факт улучшения.

### Слишком много retrieved context

Топ-20 подсказок могут навредить. Начинай с 3-5.

### Нет source ids

Если не сохранить feedback_id, невозможно понять, что повлияло на ответ.

## Memory design checklist

- [ ] Есть structured record schema.
- [ ] Есть stable ids.
- [ ] Есть created_at timezone-aware.
- [ ] Есть scope/type.
- [ ] Есть tags/metadata.
- [ ] Есть append-only persistence.
- [ ] Есть retrieval query.
- [ ] Есть formatting for prompt.
- [ ] Есть limit.
- [ ] Есть tests for relevant/irrelevant memory.
- [ ] Есть audit of used records.
- [ ] Есть evaluation with and without memory.

## Practical next project idea

`Feedback Memory Lab`

Цель:

```text
Compare deterministic retrieval, semantic retrieval and hybrid retrieval.
```

Dataset:

```text
feedback records
test cases
expected relevant feedback ids
```

Metrics:

- recall@k;
- precision@k;
- MRR;
- downstream action accuracy.

Это хороший отдельный проект для изучения RAG без шума Playwright/LangGraph.
