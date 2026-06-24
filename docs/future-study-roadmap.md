# Future Study Roadmap

Проект завершен как v0.1 educational demo. Дальше лучше не перегружать этот
репозиторий всеми идеями сразу, а использовать его как базу и переходить к
следующим темам осознанно.

## Главные пробелы, которые стоит изучить глубже

### 1. Memory evaluation

Что изучить:

- сравнение with memory / without memory;
- controlled cases, где feedback должен менять action;
- metrics для memory usefulness;
- negative tests, где feedback не должен применяться.

Почему важно:

Мы подключили feedback memory, но не доказали метриками, что она улучшает
поведение.

Практическое задание:

```text
same TestCase
same page_snapshot
planner without memory -> wrong target
planner with memory -> correct target
```

### 2. RAG and semantic retrieval

Что изучить:

- embeddings;
- vector stores;
- chunking;
- similarity search;
- hybrid retrieval;
- reranking;
- retrieval evaluation.

Почему важно:

Текущий retrieval ищет exact `test_case_id`. Это хорошо для начала, но не найдет
feedback для похожего сценария с другим id.

Практическое задание:

```text
feedback for profile-save
new case account-settings-save
semantic retrieval finds relevant correction
```

### 3. Prompt versioning and experiment tracking

Что изучить:

- prompt versions;
- dataset snapshots;
- experiment comparison;
- regression dashboards;
- rollback prompt changes.

Почему важно:

Без версий трудно понять, какой prompt дал какой результат.

### 4. Production browser automation

Что изучить:

- retries;
- timeouts;
- waiting strategies;
- flaky UI handling;
- browser contexts;
- parallel runs;
- artifact management.

Почему важно:

Playwright в demo проще, чем реальный web testing at scale.

### 5. Test case ingestion

Что изучить:

- JSON/YAML/Markdown test case format;
- validation errors;
- schema evolution;
- data-driven test suites.

Практическое задание:

```text
python scripts\run_case.py examples/cases/create-task.json
```

### 6. Bug deduplication

Что изучить:

- сравнение bug reports;
- semantic similarity;
- fingerprinting;
- duplicate detection;
- updating existing issue instead of creating new one.

Почему важно:

Автотестирующий агент может найти один и тот же баг много раз.

### 7. Multi-agent architecture

Что изучить:

- planner/executor/judge как роли;
- supervisor;
- specialist agents;
- message passing;
- shared memory;
- failure isolation.

Текущий проект уже имеет несколько LLM-roles, но они не общаются как отдельные
агенты. Это хороший следующий шаг.

### 8. Safety and human control

Что изучить:

- approval policies;
- risk classification;
- action sandboxing;
- audit logs;
- irreversible actions;
- human override.

Почему важно:

UI agents могут нажимать реальные кнопки. Safety нельзя отдавать только LLM.

### 9. Generated tests

Что изучить:

- превращение successful route в Playwright test;
- selector stabilization;
- assertions;
- fixtures;
- test maintenance.

Цель:

```text
agent explored scenario
  -> produced route
  -> generated deterministic Playwright regression test
```

### 10. Production storage

Что изучить:

- SQLite/Postgres schema;
- migrations;
- event log;
- idempotency;
- concurrent writes;
- retention policy.

JSONL подходит для learning, но production memory needs stronger storage.

## Предлагаемый следующий проект

Если хочется изучать RAG отдельно, хороший следующий проект:

```text
AI Feedback Memory Lab
```

Цель:

- взять feedback records;
- сделать deterministic retrieval;
- добавить embeddings;
- сравнить deterministic vs semantic vs hybrid;
- измерить качество retrieval.

Минимальные модули:

```text
domain.py
stores.py
embeddings.py
retrieval.py
evaluation.py
datasets/
```

Почему отдельный проект:

- меньше шума от Playwright/LangGraph;
- легче сосредоточиться на retrieval quality;
- можно экспериментировать с vector DB;
- потом перенести лучшие идеи обратно в `UiBrowserAgent`.

## Предлагаемый v0.2 для текущего проекта

Если продолжать именно этот репозиторий:

1. Add `FeedbackStore Protocol`.
2. Add `MemoryUsage` to `RunReport`.
3. Add prompt versions.
4. Add memory evaluation dataset.
5. Add CLI args to `run_real_agent.py`.
6. Add generated Playwright test prototype.
7. Add failed-run demo fixture.
8. Add bug report demo.
9. Add `ruff` and `mypy`/`pyright`.
10. Add docs screenshots or Mermaid diagrams to README.

## Что уже можно показывать как результат

Проект уже демонстрирует:

- real LangGraph workflow;
- local LLM through Ollama;
- typed structured output;
- real browser automation;
- route recording;
- independent judge;
- failure classification;
- bug report generation;
- report rendering;
- LangSmith-ready tracing/evaluation;
- run history;
- human feedback memory;
- retrieval into planner prompt.

Это хороший фундамент для портфолио AI engineer, особенно если README и docs
будут поддерживаться в актуальном состоянии.

## Как развивать личную экспертизу дальше

1. Разбирать чужие agent frameworks, но не копировать слепо.
2. Всегда спрашивать: где state, где memory, где side effects, где eval?
3. Писать маленькие тестируемые components.
4. Отделять LLM reasoning от deterministic execution.
5. Делать eval до усложнения prompt.
6. Хранить feedback как данные, а не только как prompt edits.
7. Измерять улучшения.
8. Документировать архитектурные решения.
9. Делать controlled fixtures для экспериментов.
10. Не считать "работает один раз" доказательством надежности.
