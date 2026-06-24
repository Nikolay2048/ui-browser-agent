# Concepts And Engineering Decisions

Этот документ собирает ключевые темы, которые были изучены через проект.

## Pydantic Domain Models

Что это:

Pydantic-модели описывают структуру данных и валидируют ее во время выполнения.

Зачем используется:

- LLM output должен быть проверяемым;
- тест-кейс, action, verdict, report и feedback должны иметь стабильный контракт;
- данные нужно сериализовать в JSON;
- ошибки должны обнаруживаться рядом с границей данных.

Как реализовано:

```text
src/browser_agent/domain/models.py
```

Примеры:

```python
class BrowserAction(BaseModel):
    action: BrowserActionType
    target: BrowserTarget | None
    value: str | None
    reason: str
```

`BrowserAction` валидирует, что `click`, `fill`, `press`, `assert_text`
получают target, а `fill` и `press` получают value.

Альтернативы:

- dataclasses;
- TypedDict;
- plain dict;
- JSON Schema validation отдельно.

Почему выбрали Pydantic:

- хорошо работает с LangChain structured output;
- удобная JSON-сериализация;
- строгие validators;
- читаемые тесты.

Типичные ошибки:

- валидировать только в prompt, а не в коде;
- позволять `dict[str, Any]` везде;
- делать domain-модели зависимыми от Playwright или LangGraph;
- смешивать transient state и stable report.

## Structured Output

Что это:

Механизм, при котором LLM должна вернуть данные в заданной структуре.

Зачем:

Executor не должен разбирать свободный текст. Ему нужен валидный
`BrowserAction`.

Как реализовано:

```python
structured_model = model.with_structured_output(BrowserAction)
return prompt | structured_model
```

В проекте structured output используется для:

- Planner -> `BrowserAction`;
- Judge -> `JudgeVerdict`;
- Classifier -> `FailureClassification`;
- Reporter -> `BugReport`.

Альтернативы:

- tool calling;
- JSON mode;
- ручной парсинг JSON;
- regex extraction.

Типичные ошибки:

- принимать natural language response и пытаться "догадаться";
- не тестировать schema mismatch;
- не объяснять модели допустимый target language;
- не валидировать бизнес-правила после parse.

## LangChain Runnable Chain

Что это:

LCEL позволяет соединять компоненты через оператор `|`.

Пример:

```python
prompt | structured_model
```

Зачем:

- единый интерфейс `.invoke()`;
- prompt formatting и model call становятся composable;
- легко тестировать fake model через `RunnableLambda`.

Как реализовано:

```text
planner.py
judge.py
classifier.py
reporter.py
```

Типичные ошибки:

- думать, что `prompt | model` сразу вызывает модель. Вызов происходит только на
  `.invoke(...)`;
- передавать не все переменные prompt-а;
- не понимать, что `invoke` принимает input dict для prompt variables.

## LangGraph StateGraph

Что это:

LangGraph описывает stateful workflow из nodes и edges.

Зачем:

- агенту нужен цикл observe-plan-execute;
- нужны conditional routes;
- нужны checkpointing и interrupt;
- нужно видеть state на каждом шаге.

Как реализовано:

```text
src/browser_agent/graph.py
```

Альтернативы:

- обычный while-loop;
- custom state machine;
- workflow engines;
- AutoGen/CrewAI-style frameworks.

Почему LangGraph:

- state-first модель хорошо подходит для агента;
- удобно добавлять approval и checkpointing;
- граф легче визуализировать и тестировать.

Типичные ошибки:

- делать routers с side effects;
- мутировать входной state;
- смешивать graph wiring и бизнес-логику;
- забывать terminal edges;
- не ограничивать циклы.

## AgentState

Что это:

Рабочая память одного запуска агента.

Зачем:

Ноды графа обмениваются данными через state.

Как реализовано:

```python
class AgentState(TypedDict):
    test_case: Required[TestCase]
    page_snapshot: NotRequired[str]
    proposed_action: NotRequired[BrowserAction]
    route: NotRequired[list[ExecutionStep]]
```

Альтернативы:

- Pydantic model для state;
- dataclass;
- обычный dict без typing.

Почему TypedDict:

- легкий runtime;
- хорошо подходит к partial updates;
- достаточно типизации для учебного проекта.

Типичные ошибки:

- считать state долговременным хранилищем;
- сохранять весь AgentState как report;
- мутировать nested values;
- класть в state внешние ресурсы вроде browser/page.

## Dependency Injection

Что это:

Передача зависимости снаружи вместо создания ее внутри функции.

Пример:

```python
def run_agent(model, browser, test_case, ...):
```

`run_agent` не создает model и browser сам.

Зачем:

- тесты могут передать fake model/browser;
- можно менять Ollama на другую модель;
- можно менять browser adapter;
- код становится composable.

Как реализовано:

- `build_agent_graph(model, browser)`;
- `make_plan_node(model)`;
- `make_execute_node(browser)`;
- `run_agent(..., history_store=None, feedback_store=None)`.

Альтернативы:

- global singleton;
- service locator;
- создание зависимостей внутри функций.

Типичные ошибки:

- импортировать конкретный store/model внутри низкоуровневого компонента;
- делать скрытые зависимости через env везде;
- усложнять DI framework-ом там, где достаточно аргументов функции.

## Dependency Inversion

Что это:

Высокоуровневый код зависит не от конкретной реализации, а от минимального
контракта.

Как реализовано:

```python
class RunHistoryStore(Protocol):
    def append(self, record: RunHistoryRecord) -> None:
        ...
```

`runner.py` принимает `history_store`, но не обязан знать, JSONL это или база.

Также `feedback_store` в runner используется по методу `load_all()`, а retrieval
принимает store параметром.

Альтернативы:

- прямой импорт `JsonlRunHistoryStore`;
- передача пути и создание store внутри runner;
- наследование от abstract base class.

Типичные ошибки:

- перепутать inversion с усложнением;
- делать большой interface вместо минимального;
- преждевременно строить generic repository.

## Protocol

Что это:

Структурный контракт в Python typing: объект подходит, если у него есть нужные
методы.

Зачем:

Не нужно заставлять `JsonlRunHistoryStore` наследоваться от базового класса.

Как реализовано:

```python
class RunHistoryStore(Protocol):
    def append(self, record: RunHistoryRecord) -> None:
        ...
```

Типичные ошибки:

- думать, что Protocol что-то проверяет runtime автоматически;
- делать Protocol слишком широким;
- использовать наследование там, где достаточно structural typing.

## Browser Adapter

Что это:

Слой, который переводит доменные browser actions в Playwright calls.

Зачем:

LLM не должна знать Playwright API.

Как реализовано:

```text
src/browser_agent/browser.py
```

`BrowserTarget` переводится в:

- `page.get_by_role`;
- `page.get_by_label`;
- `page.get_by_text`;
- `page.locator`.

Альтернативы:

- позволить LLM генерировать Playwright code;
- использовать raw CSS selectors;
- использовать vision-only click coordinates.

Типичные ошибки:

- смешивать locator language со snapshot syntax;
- принимать target как строку без schema;
- разрешать модели выполнять произвольный код.

## Deterministic Executor

Что это:

Исполнитель, который без LLM выполняет `BrowserAction`.

Зачем:

Side effects должны быть предсказуемыми.

Как реализовано:

```python
if action.action == BrowserActionType.CLICK:
    browser.click(action.target)
```

Executor сохраняет:

- `url_before`;
- `url_after`;
- screenshot;
- error;
- success flag.

Типичные ошибки:

- вызывать LLM внутри executor;
- не делать screenshot при ошибке;
- не записывать failed action в route;
- выбрасывать exception вместо `ActionResult` там, где нужна recoverability.

## Independent Judge

Что это:

Отдельная LLM-роль, которая проверяет expected results.

Зачем:

Planner может ошибочно решить, что задача выполнена.

Как реализовано:

```text
judge.py -> JudgeVerdict
```

Judge получает:

- expected results;
- execution history;
- current page snapshot.

Типичные ошибки:

- доверять `finish` от planner;
- считать success action доказательством бизнес-результата;
- не требовать evidence по каждому expected result.

## Failure Classification

Что это:

Объяснение failed run.

Зачем:

Failed run может быть:

- багом продукта;
- ошибкой агента;
- ошибкой автоматизации;
- проблемой окружения;
- недостатком evidence.

Как реализовано:

```text
classifier.py -> FailureClassification
```

Типичные ошибки:

- заводить баг на каждое падение;
- не отделять product bug от automation failure;
- не сохранять rationale/evidence.

## Bug Reporter

Что это:

LLM-роль, которая пишет structured product bug report.

Зачем:

Если классификация показала product bug, нужен воспроизводимый отчет.

Как реализовано:

```text
reporter.py -> BugReport
```

BugReport включает:

- title;
- severity;
- preconditions;
- steps to reproduce;
- expected result;
- actual result;
- evidence.

Типичные ошибки:

- придумывать детали, которых нет в evidence;
- писать слишком общий actual result;
- смешивать agent error и product bug.

## JSONL Persistence

Что это:

Формат, где каждая строка - отдельный JSON object.

Зачем:

- append-only запись;
- легко читать построчно;
- не нужно переписывать весь файл;
- удобно смотреть руками;
- легко мигрировать в базу позже.

Как реализовано:

```text
JsonlRunHistoryStore
JsonlFeedbackStore
```

Альтернативы:

- SQLite;
- Postgres;
- S3/object storage;
- LangSmith datasets;
- vector database.

Типичные ошибки:

- хранить runtime artifacts в Git;
- не использовать append-only;
- не валидировать строки при чтении;
- не учитывать concurrent writers.

## Checkpointing

Что это:

Сохранение state thread-а LangGraph для resume/debug.

Зачем:

- human-in-the-loop;
- восстановление после interruption;
- просмотр текущего state;
- long-running agent workflows.

Как реализовано:

```text
persistence.py -> build_thread_config()
run_real_agent.py -> InMemorySaver
```

Типичные ошибки:

- использовать checkpointer без `thread_id`;
- путать checkpoint и run history;
- считать checkpoint пользовательским отчетом.

## Human Feedback Memory

Что это:

Структурированная человеческая коррекция поведения агента.

Зачем:

Чтобы улучшать будущие запуски не только через prompt edits, а через данные.

Как реализовано:

```text
HumanFeedbackRecord
JsonlFeedbackStore
scripts/add_feedback.py
feedback_retrieval.py
memory_context in planner
```

Типичные ошибки:

- сразу вставлять все feedback records в system prompt;
- хранить feedback как свободный текст без run_id/test_case_id/scope;
- не отделять feedback для planner от feedback для judge/reporter;
- не иметь retrieval.

## Retrieval

Что это:

Выбор релевантной части памяти.

Зачем:

Prompt не должен получать всю память.

Как реализовано:

```python
FeedbackRetrievalQuery(
    test_case=test_case,
    scopes=[FeedbackScope.PLANNER, FeedbackScope.STEP],
)
```

Фильтры:

- `test_case.id`;
- scope;
- optional tags;
- newest first;
- limit.

Альтернативы:

- semantic retrieval через embeddings;
- hybrid retrieval;
- manual rules;
- query через SQL.

Типичные ошибки:

- называть retrieval только vector search;
- не ограничивать количество записей;
- не сортировать по freshness;
- не проверять, что feedback не противоречит snapshot.

## Jinja2 Reports

Что это:

Шаблонизатор для Markdown report.

Зачем:

Markdown report должен быть deterministic, без LLM.

Как реализовано:

```text
templates/run_report.md.j2
reporting.py
```

Типичные ошибки:

- генерировать итоговый отчет LLM-ом без необходимости;
- смешивать построение domain report и rendering;
- не сохранять JSON рядом с Markdown.

## LangSmith

Что это:

Инструмент observability/evaluation для LangChain/LangGraph запусков.

Зачем:

- видеть traces;
- сравнивать prompts;
- запускать experiments;
- хранить datasets.

Как реализовано:

```text
observability.py
scripts/run_planner_experiment.py
scripts/run_judge_experiment.py
```

Типичные ошибки:

- не добавлять searchable metadata;
- смотреть только single trace вместо dataset metrics;
- не отделять model error от infrastructure error.

## Test-Driven Mentorship

Что это:

Обучение через маленькие задания и failing tests.

Как реализовано:

- для новых lessons добавлялись contract tests;
- ученик писал реализацию;
- тесты падали;
- ошибки разбирались;
- код исправлялся;
- полный pytest подтверждал regression safety.

Типичные ошибки:

- сразу писать большой агент без тестов;
- тестировать только happy path;
- использовать реальные LLM/browser в unit tests;
- не иметь deterministic fakes.
