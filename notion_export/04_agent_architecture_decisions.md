# Agent Architecture Decisions

Этот файл можно использовать как набор ADR-заметок для будущих проектов.

## Decision 1. Start With Domain Contracts

Решение:

Перед LLM, графом и браузером описать доменные модели.

Почему:

- агенту нужен язык данных;
- structured output требует schema;
- тесты проще писать от контрактов;
- ошибки в данных ловятся рано.

Пример:

```python
class TestCase(BaseModel):
    id: str
    start_url: str
    goal: str
    expected: list[str]
```

Альтернатива:

Начать с prompt и raw dict.

Почему хуже:

- быстро появляется хаос в полях;
- трудно понять, что модель должна вернуть;
- executor начинает парсить строки.

Применять в новых проектах:

Перед первым LLM call выписать:

- input models;
- output models;
- event models;
- error models;
- report models.

## Decision 2. LLM Proposes, Deterministic Code Executes

Решение:

Planner возвращает `BrowserAction`, executor выполняет action.

Почему:

- side effects должны быть контролируемыми;
- LLM не должна генерировать произвольный Playwright-код;
- проще тестировать;
- ниже риск prompt injection.

Плохо:

```text
LLM: page.get_by_label("Task").fill("...")
eval(llm_output)
```

Хорошо:

```json
{
  "action": "fill",
  "target": {"strategy": "label", "value": "Task"},
  "value": "Learn AI Agents"
}
```

Применять:

Для любого агента с tools:

```text
LLM chooses tool call parameters
Tool executes only allowed operation
```

## Decision 3. Separate Planner And Judge

Решение:

Planner не решает окончательно, что тест passed. Он может только предложить
`finish`. После этого Judge независимо проверяет expected results.

Почему:

- planner мотивирован завершить задачу;
- success action не доказывает business success;
- нужна независимая проверка evidence.

Применять:

В любом агенте, где важно качество результата:

```text
Generator
  -> Verifier/Judge
  -> accept/reject
```

Альтернатива:

Один LLM одновременно планирует и проверяет сам себя.

Риск:

Self-confirmation bias.

## Decision 4. Keep Graph Nodes Small

Решение:

Каждая node делает одну роль:

```text
observe
plan
execute
judge
classify
report
```

Почему:

- легче тестировать;
- легче читать traces;
- проще менять одну часть;
- graph показывает реальный workflow.

Плохо:

```python
def agent_node(state):
    observe()
    plan()
    execute()
    judge()
```

Хорошо:

```text
observe -> plan -> execute -> observe -> plan -> judge
```

## Decision 5. Runner Is Composition Root

Решение:

`runner.py` собирает model, browser, graph, tracing, checkpointing, reporting,
history and feedback.

Почему:

- graph nodes остаются чистыми;
- persistence не размазывается по ролям;
- легче тестировать `run_agent`;
- CLI/scripts остаются тоньше.

Применять:

В новом проекте выделять слой:

```text
application runner / service / orchestrator
```

Он связывает infrastructure и domain workflow.

## Decision 6. Feedback Is Data, Not Prompt Patch

Решение:

Human feedback сохраняется как `HumanFeedbackRecord`.

Почему:

- prompt не превращается в свалку частных случаев;
- feedback можно искать;
- можно измерять влияние;
- можно удалить плохую подсказку;
- можно переносить в RAG.

Плохо:

```text
System prompt:
Also for case X use label=Task.
Also for case Y click Save.
Also for case Z...
```

Хорошо:

```json
{
  "test_case_id": "first-real-agent",
  "scope": "planner",
  "correction": "For task input, prefer label=Task."
}
```

## Decision 7. Retrieval Before Prompt Injection

Решение:

Передавать planner-у только релевантный memory context.

Почему:

- вся память слишком шумная;
- prompt budget ограничен;
- нерелевантные подсказки вредят;
- легче объяснить поведение.

Применять:

Любая memory system:

```text
store all
retrieve few
format context
inject into prompt
```

## Decision 8. Use JSONL For Early Append-Only Memory

Решение:

Run history и feedback хранятся в JSONL.

Почему:

- просто;
- удобно append;
- не нужна база;
- можно читать руками;
- хорошо для обучения и прототипа.

Когда менять:

- появились concurrent writes;
- нужны индексы;
- нужен поиск по многим полям;
- нужна миграция schema;
- нужна аналитика.

Тогда переходить на SQLite/Postgres/vector DB.

## Decision 9. Controlled Fixture Before External Websites

Решение:

Для live evaluation использовать локальный fixture.

Почему:

- внешний сайт меняется;
- evaluation должна быть воспроизводимой;
- проще отделить model behavior от environment failure.

Применять:

Сначала:

```text
local fixture
```

Потом:

```text
staging site
```

И только потом:

```text
real external sites
```

## Decision 10. Component Evaluation Before Full RAG

Решение:

Сначала Planner/Judge/E2E evaluation, потом RAG.

Почему:

Если добавить RAG без evaluation, нельзя понять, стало лучше или хуже.

Применять:

Перед любым "улучшением" агента спросить:

```text
Как мы измерим эффект?
```

## Decision 11. Approval Policy Is Deterministic

Решение:

Risky actions проверяются deterministic policy.

Почему:

LLM может недооценить риск.

Пример:

```python
if action.action == CLICK and "delete" in target_text:
    requires_approval = True
```

Применять:

Для safety использовать:

- allowlists;
- deny keywords;
- domain restrictions;
- human approval;
- audit logs.

LLM может объяснять, но не быть единственной защитой.

## Decision 12. Reports Are Rendered, Not Generated

Решение:

RunReport строится как data model, Markdown рендерится через Jinja2.

Почему:

- отчет deterministic;
- можно сохранять JSON;
- можно менять шаблон без LLM;
- меньше hallucination.

Reporter LLM создает только `BugReport`, когда нужен semantic summary по
evidence. Финальный run report не нуждается в LLM.

## Decision 13. Tests Use Fakes, Not Real LLM

Решение:

Unit/integration tests используют fake models and fake browsers.

Почему:

- быстрые тесты;
- deterministic;
- не зависят от Ollama;
- можно проверять graph wiring.

Live tests/scripts существуют отдельно.

Применять:

```text
unit tests -> fakes
component eval -> controlled model or dataset
live eval -> real model/browser
```

## Decision 14. Keep Runtime Artifacts Out Of Git

Решение:

`artifacts/` ignored.

Почему:

- screenshots, reports, history локальны;
- они меняются при каждом запуске;
- могут содержать данные окружения.

Коммитить можно:

```text
examples/
evaluations/
docs/
learning/
tests/
src/
```

## Architecture Decision Template

Для будущих проектов можно использовать шаблон:

```markdown
# ADR: <decision>

## Context
Какая проблема?

## Decision
Что выбираем?

## Why
Почему именно так?

## Alternatives
Что еще рассматривали?

## Consequences
Что станет проще/сложнее?

## How To Test
Как проверить, что решение работает?
```

## Быстрый checklist архитектуры агента

- [ ] Есть domain models.
- [ ] Есть explicit state.
- [ ] LLM outputs structured.
- [ ] Tools deterministic.
- [ ] Side effects isolated.
- [ ] Есть independent verifier.
- [ ] Есть route/evidence.
- [ ] Есть limits.
- [ ] Есть failure classification.
- [ ] Есть reports.
- [ ] Есть memory model.
- [ ] Есть retrieval.
- [ ] Есть evaluation.
- [ ] Есть observability.
- [ ] Есть human override для risky actions.
