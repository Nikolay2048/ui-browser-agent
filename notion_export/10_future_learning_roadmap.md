# Future Learning Roadmap

Эта заметка отвечает на вопрос: что изучать дальше, чтобы уверенно разрабатывать агентские системы, а не просто собирать цепочки вызовов LLM.

Проект `UiBrowserAgent` уже дал базовый каркас:

```text
test case -> planner -> browser executor -> observer -> judge -> report
             ^                                      |
             |                                      v
          memory / feedback / retrieval        evaluation
```

Следующий рост - не в том, чтобы добавить больше узлов, а в том, чтобы сделать систему измеримой, воспроизводимой, расширяемой и безопасной.

## Главный принцип дальнейшего обучения

Не изучай AI agents как набор модных библиотек.

Изучай их как инженерную дисциплину:

```text
contracts
state
control flow
tool boundaries
verification
memory
evaluation
observability
deployment
```

LangChain, LangGraph, RAG, vector DB, LangSmith, LangFuse, tool calling - это инструменты. Сильный AI engineer понимает, какую проблему решает каждый инструмент и когда он избыточен.

## Уровень 1. Укрепить фундамент агентских систем

Цель: свободно проектировать агента до написания кода.

Что нужно уметь:

- описывать задачу как систему состояний;
- выделять роли: Planner, Executor, Observer, Judge, Reporter;
- понимать, где нужен LLM, а где обычный deterministic code;
- проектировать Pydantic-контракты;
- писать graph nodes без side effects;
- делать routing как чистую функцию;
- ограничивать циклы и ошибки;
- сохранять route/evidence.

Практика:

1. Возьми простой сайт с формой.
2. Опиши `TestCase`, `BrowserAction`, `ActionResult`, `JudgeVerdict`.
3. Нарисуй граф до кода.
4. Реализуй минимальный запуск.
5. Напиши тесты на каждый router отдельно.

Критерий понимания:

Ты можешь объяснить, почему конкретная логика находится в node, router, executor или judge.

## Уровень 2. Evaluation-first разработка

Цель: перестать оценивать агента ощущениями.

В агентских системах субъективное "вроде работает" быстро ломается. Нужно измерять:

- выбрал ли Planner правильное действие;
- выполнил ли Executor действие;
- правильно ли Judge оценил результат;
- уложился ли агент в бюджет шагов;
- была ли recovery-попытка;
- не ухудшилась ли система после изменения prompt;
- помогла ли память или retrieval.

Минимальный набор eval:

```text
planner eval
judge eval
retrieval eval
end-to-end eval
regression dataset
```

Практика:

1. Создай 20 planner cases.
2. Создай 20 judge cases.
3. Создай 5 end-to-end scenarios.
4. Прогони baseline.
5. Измени prompt.
6. Сравни метрики до/после.

Хорошие метрики:

- exact action match;
- strategy match;
- target match;
- task success rate;
- termination accuracy;
- recovery accuracy;
- average steps;
- average failures;
- regression count.

Плохая метрика:

```text
"Мне кажется, модель стала отвечать лучше."
```

Критерий понимания:

Ты можешь сказать: "Это изменение улучшило planner exact match с 0.73 до 0.86, но увеличило среднее число шагов с 2.1 до 2.8".

## Уровень 3. Prompt engineering как инженерный артефакт

Цель: писать prompt так, чтобы он был тестируемым и сопровождаемым.

Prompt в production - это не текст в коде "на глаз". Это часть поведения системы.

Хороший prompt содержит:

- роль;
- задачу;
- ограничения;
- формат входных данных;
- формат выходных данных;
- допустимый target/action language;
- правила при неуверенности;
- правила использования memory;
- негативные примеры;
- версию.

Плохой prompt:

```text
You are a smart agent. Do the task.
```

Хороший prompt:

```text
Choose exactly one next browser action.
Use only the supported target schema.
Do not copy raw snapshot text into target.value.
If the goal is already satisfied, return finish.
Use memory only as guidance, not as current page truth.
```

Что изучить:

- few-shot examples;
- negative examples;
- structured output prompting;
- prompt versioning;
- prompt regression tests;
- model-specific behavior;
- prompt injection risks.

Критерий понимания:

Ты можешь изменить prompt и доказать через eval, что изменение стало лучше.

## Уровень 4. RAG и retrieval

Цель: научиться давать агенту нужный прошлый опыт, не перегружая context window.

RAG в агенте - это не просто "найти похожий текст". Это выбор релевантного знания для текущего решения.

Типы retrieval:

```text
keyword retrieval
semantic retrieval
hybrid retrieval
metadata filtering
reranking
recency weighting
success-based weighting
```

Для UI testing agent полезные источники:

- human feedback;
- успешные маршруты;
- прошлые ошибки;
- locator guidelines;
- known app behavior;
- test documentation;
- bug history;
- component library docs.

Минимальный RAG pipeline:

```text
query builder
  -> retriever
  -> reranker
  -> formatter
  -> prompt
  -> used_memory_ids
  -> evaluation
```

Практика:

1. Сохрани 20 feedback records.
2. Реализуй keyword retrieval.
3. Реализуй semantic retrieval через embeddings.
4. Сравни precision@k.
5. Добавь used memory ids в route/report.

Главная ошибка:

```text
Добавить vector DB и считать, что memory теперь работает.
```

Memory работает только тогда, когда ты измерил, что правильные записи реально попадают в prompt и улучшают решение.

Критерий понимания:

Ты можешь объяснить, почему конкретная feedback-запись была выбрана и как она повлияла на action.

## Уровень 5. Human feedback loop

Цель: превратить ошибки агента в данные для улучшения.

Есть несколько уровней обратной связи:

```text
manual correction
approval before action
post-run annotation
dataset update
feedback memory
prompt update
fine-tuning data
```

Для учебного и early-stage проекта лучше начинать с:

- JSONL feedback;
- human-readable correction;
- scope: planner/judge/run/bug_report;
- tags;
- retrieval into next run;
- eval before/after.

Production-подход:

```text
agent run
  -> trace
  -> human review
  -> structured feedback
  -> triage
  -> dataset update
  -> regression eval
  -> prompt/tool/model change
```

Важно:

Не каждую ошибку нужно чинить prompt. Иногда причина в:

- плохом snapshot;
- слабом target language;
- executor limitation;
- неверном judge;
- отсутствии test data;
- неустойчивом сайте;
- плохом retrieval;
- слишком слабой модели.

Критерий понимания:

Ты можешь классифицировать ошибку агента и выбрать правильный способ исправления.

## Уровень 6. Production architecture

Цель: перейти от учебного скрипта к системе, которую можно поддерживать.

Production AI-agent обычно делится на слои:

```text
API / CLI / UI
application services
agent orchestration
domain contracts
LLM adapters
tool adapters
persistence
evaluation
observability
security
```

Что стоит добавить в будущих проектах:

- configuration layer;
- secrets management;
- structured logging;
- trace ids;
- prompt registry;
- dataset registry;
- storage migrations;
- retry policy;
- timeout policy;
- rate limiting;
- async execution;
- worker queue;
- auth;
- audit log;
- human review UI.

Архитектурный принцип:

```text
Business logic should not depend directly on vendor SDKs.
```

Вместо этого:

```text
domain -> protocols -> adapters
```

Пример:

```python
class RunHistoryStore(Protocol):
    def append(self, record: RunHistoryRecord) -> None: ...
```

Такой подход позволяет заменить JSONL на PostgreSQL, S3 или LangSmith export без переписывания агента.

Критерий понимания:

Ты можешь заменить browser adapter, LLM adapter или storage adapter без изменения domain models.

## Уровень 7. Multi-agent systems

Цель: понимать, когда несколько агентов действительно нужны.

Не начинай с multi-agent. В большинстве случаев достаточно одного графа с ролями.

Multi-agent полезен, когда:

- разные роли требуют разных моделей;
- есть независимые потоки анализа;
- нужен debate/critique;
- задачи можно распараллелить;
- нужен reviewer над worker-агентом;
- есть разные доменные специализации.

Примеры для UI testing:

```text
Planner agent
Visual observer agent
Accessibility checker agent
Bug reporter agent
Test generator agent
Reviewer agent
```

Но сначала нужно иметь:

- clear contracts;
- shared state model;
- evaluation;
- traceability;
- budget limits.

Главная ошибка:

```text
Добавить 5 агентов, когда один агент еще не измерен.
```

Критерий понимания:

Ты можешь обосновать, почему второй агент лучше, чем дополнительная node в существующем графе.

## Уровень 8. Safety и governance

Цель: уметь запускать агента в реальном окружении без неожиданных последствий.

Для browser agent важны:

- allowlist доменов;
- запрет destructive actions без approval;
- запрет платежей и отправки реальных форм;
- masking secrets;
- ограничения на downloads/uploads;
- screenshot retention policy;
- audit log;
- human approval для risky actions;
- read-only режим;
- dry-run режим.

Safety нельзя оставлять только LLM.

Нужны deterministic checks:

```text
action -> policy -> allowed/blocked/needs_approval
```

Критерий понимания:

Ты можешь показать, какие actions агент физически не сможет выполнить без policy approval.

## Уровень 9. Генерация автотестов

Цель проекта изначально включала: пройти тест-кейс, записать маршрут, а затем написать автотесты.

Следующий логичный этап:

```text
agent route
  -> normalized steps
  -> stable locators
  -> generated Playwright test
  -> test validation
  -> review
```

Что нужно решить:

- какие steps можно кодогенерировать;
- как выбирать stable locators;
- как хранить assertions;
- как не генерировать flaky tests;
- как переиспользовать fixtures;
- как валидировать generated test;
- как оформлять PR.

Пример целевого результата:

```python
def test_add_task(page):
    page.goto("...")
    page.get_by_label("Task").fill("Learn AI Agents")
    page.get_by_role("button", name="Add").click()
    expect(page.get_by_text("Learn AI Agents")).to_be_visible()
```

Важно:

Автотест не должен быть простой расшифровкой route. Route может содержать неудачные попытки, recovery и лишние шаги. Нужна отдельная стадия normalization.

Критерий понимания:

Ты можешь объяснить, почему generated test отличается от raw agent route.

## Уровень 10. Deployment и эксплуатация

Цель: понимать, как такой агент живет вне локального ноутбука.

Возможные варианты:

```text
local CLI
internal web service
CI job
scheduled monitor
QA assistant
bug triage worker
test generation worker
```

Для production нужно:

- Docker image;
- isolated browser environment;
- artifact storage;
- database;
- queue;
- observability;
- secrets;
- role-based access;
- retry/backoff;
- cancellation;
- cost tracking;
- model fallback;
- incident debugging.

Критерий понимания:

Ты можешь ответить: что произойдет, если модель недоступна, браузер завис, сайт вернул 500, или judge дал неверный verdict.

## 30-Day Plan

Цель: закрепить текущий проект.

1. Прочитать все файлы `notion_export/`.
2. Нарисовать архитектуру `UiBrowserAgent` по памяти.
3. Добавить 10 planner eval cases.
4. Добавить 10 judge eval cases.
5. Добавить 3 live end-to-end scenarios.
6. Добавить prompt version field.
7. Добавить used memory ids в отчет.
8. Сделать один controlled failure и feedback correction.
9. Проверить, что feedback улучшает следующий запуск.
10. Написать краткую статью "Как работает мой browser agent".

## 60-Day Plan

Цель: перейти к более взрослой инженерной практике.

1. Добавить semantic retrieval.
2. Сравнить keyword vs semantic vs hybrid retrieval.
3. Добавить LangSmith dataset для retrieval eval.
4. Добавить prompt registry.
5. Добавить generated Playwright test prototype.
6. Добавить policy layer для risky actions.
7. Сделать bug report в структурированном формате.
8. Добавить storage adapter interface для feedback/history.
9. Реализовать SQLite или PostgreSQL adapter.
10. Подготовить demo video/script.

## 90-Day Plan

Цель: собрать portfolio-grade проект.

1. Вынести агент в сервисный API.
2. Добавить UI для запуска test case.
3. Добавить UI для review route/screenshots.
4. Добавить human feedback форму.
5. Добавить bug tracker integration mock.
6. Добавить test generation from route.
7. Добавить CI pipeline.
8. Добавить observability dashboard.
9. Добавить несколько моделей и model comparison.
10. Написать полноценный case study.

## Что изучать глубже

### LangGraph

- checkpointing;
- interrupts;
- subgraphs;
- parallel branches;
- state reducers;
- durable execution;
- graph visualization;
- persistence backends.

### LangChain

- Runnable interface;
- structured output;
- tools;
- retrievers;
- output parsers;
- callbacks;
- tracing;
- model adapters.

### LLM Engineering

- prompt design;
- tool calling;
- function calling;
- JSON mode;
- schema validation;
- retries;
- hallucination boundaries;
- context compression;
- model comparison.

### Evaluation

- golden datasets;
- synthetic datasets;
- LLM-as-judge;
- deterministic scoring;
- confusion matrix;
- regression testing;
- online monitoring;
- human review workflow.

### RAG

- embeddings;
- chunking;
- metadata filters;
- vector databases;
- hybrid search;
- reranking;
- query rewriting;
- retrieval evaluation;
- citation/evidence tracking.

### Software Architecture

- dependency injection;
- dependency inversion;
- ports and adapters;
- domain-driven design basics;
- clean architecture;
- configuration management;
- error taxonomy;
- persistence design.

## Практические мини-проекты

### Project 1. Support Ticket Agent

Вход:

```text
customer message
```

Агент:

- классифицирует проблему;
- ищет похожие кейсы через RAG;
- предлагает ответ;
- judge проверяет полноту;
- человек утверждает.

Что изучишь:

- retrieval;
- human approval;
- answer quality evaluation.

### Project 2. Code Review Agent

Вход:

```text
git diff
```

Агент:

- анализирует diff;
- ищет risky changes;
- классифицирует severity;
- предлагает comments;
- judge фильтрует weak findings.

Что изучишь:

- static context;
- structured review outputs;
- precision over recall.

### Project 3. Documentation Agent

Вход:

```text
repository
```

Агент:

- строит карту проекта;
- извлекает архитектурные решения;
- обновляет docs;
- проверяет consistency.

Что изучишь:

- long-context workflows;
- summarization;
- repository traversal.

### Project 4. QA Bug Triage Agent

Вход:

```text
bug report + logs + screenshots
```

Агент:

- нормализует баг;
- ищет похожие баги;
- оценивает severity;
- предлагает reproduction steps;
- создает issue draft.

Что изучишь:

- multimodal context later;
- RAG over bugs;
- structured issue generation.

## Как выбирать следующий проект

Хороший учебный AI-agent проект должен иметь:

- ясный вход;
- проверяемый выход;
- реальные ошибки;
- возможность собрать dataset;
- human feedback;
- понятную метрику качества;
- ограниченный scope.

Плохой учебный проект:

```text
"Сделать универсального агента, который делает все."
```

Хороший проект:

```text
"Агент принимает один UI test case, проходит его на локальном fixture-сайте,
сохраняет route, judge verdict, bug report и генерирует Playwright draft."
```

## Карта зрелости AI-agent проекта

### Level 0. Demo

- один script;
- один prompt;
- ручная проверка;
- нет eval.

### Level 1. Structured Prototype

- Pydantic models;
- graph;
- deterministic tools;
- basic tests;
- route persistence.

### Level 2. Measured Agent

- planner eval;
- judge eval;
- end-to-end eval;
- LangSmith traces;
- regression dataset.

### Level 3. Learning Agent

- feedback store;
- retrieval;
- memory context;
- used memory tracking;
- memory eval.

### Level 4. Product Prototype

- API/UI;
- auth;
- artifacts;
- human review;
- generated tests;
- bug tracker integration.

### Level 5. Production System

- deployment;
- monitoring;
- incident response;
- cost control;
- governance;
- continuous evaluation.

Текущий `UiBrowserAgent` находится примерно между Level 2 и Level 3:

- graph есть;
- structured outputs есть;
- evaluation есть;
- LangSmith есть;
- persistence есть;
- feedback/retrieval есть;
- production API/UI/deployment пока нет.

## Личный чеклист роста AI Engineer

Отмечай, когда можешь объяснить тему без подсказки:

- [ ] Что такое agent loop.
- [ ] Чем node отличается от router.
- [ ] Почему state лучше не мутировать.
- [ ] Как работает `prompt | model`.
- [ ] Что делает `.invoke()`.
- [ ] Зачем structured output.
- [ ] Почему executor должен быть deterministic.
- [ ] Почему judge должен быть отдельным.
- [ ] Как устроить retry/recovery.
- [ ] Как измерять Planner.
- [ ] Как измерять Judge.
- [ ] Как измерять end-to-end run.
- [ ] Как устроить feedback memory.
- [ ] Как выбрать retrieval strategy.
- [ ] Как не перегрузить prompt памятью.
- [ ] Как объяснить архитектуру проекта.
- [ ] Как заменить LLM provider.
- [ ] Как заменить storage.
- [ ] Как добавить safety policy.
- [ ] Как превратить route в generated test.

## Главный навык

Главный навык AI engineer - не "уметь вызвать LLM".

Главный навык:

```text
превращать вероятностное поведение модели
в наблюдаемую, тестируемую и улучшаемую инженерную систему
```

Это и есть то, что мы строили в проекте.
