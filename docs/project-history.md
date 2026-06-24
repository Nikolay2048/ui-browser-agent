# Project History And Learning Path

## Как строился проект

Проект разрабатывался в формате наставничества.

Роль наставника:

- объяснять теорию агентных систем;
- проектировать следующий небольшой шаг;
- давать задание;
- писать контрактные тесты;
- объяснять ошибки;
- проводить review;
- удерживать архитектурную целостность проекта.

Роль ученика:

- самостоятельно реализовывать код;
- запускать тесты;
- читать ошибки;
- исправлять реализацию;
- задавать вопросы по непонятным местам;
- постепенно собирать систему из маленьких компонентов.

Это был не режим "готовый код сразу", а TDD/mentorship-подход:

```text
theory -> assignment -> tests -> самостоятельная реализация -> review -> fix -> next lesson
```

Такой формат особенно полезен для AI engineering, потому что агентные системы
нельзя хорошо понять только по готовому коду. Нужно руками пройти через state,
граф, prompt, executor, routing, evaluation, memory и feedback.

## Этап 1. Доменные контракты и первый граф

Уроки 1-4 заложили основу:

- `TestCase`;
- `BrowserAction`;
- `AgentState`;
- первый `StateGraph`;
- условные переходы;
- цикл агента;
- `max_steps` как защита от бесконечного loop.

Ключевой принцип: перед тем как подключать LLM, нужно описать контракт данных.
Если агент "думает" в неструктурированных строках, его трудно тестировать,
отлаживать и ограничивать.

## Этап 2. Planner и LangChain

Уроки 5-6 добавили первый LLM-компонент:

- `ChatPromptTemplate`;
- `model.with_structured_output(BrowserAction)`;
- LCEL-цепочку `prompt | structured_model`;
- вызов `.invoke(...)`;
- planner как node LangGraph.

Важное понимание:

```text
prompt | structured_model
```

создает runnable chain. При вызове `.invoke(...)` сначала форматируется prompt,
потом вызывается модель, затем результат приводится к Pydantic-схеме.

Structured output стал обязательным решением: executor не должен парсить
произвольный текст модели.

## Этап 3. Executor, Observer и автономный loop

Уроки 7-11 добавили:

- deterministic executor;
- browser adapter abstraction;
- observer;
- observe-plan-execute loop;
- route записи `ExecutionStep`;
- immutability-подход к обновлению state.

Важное инженерное решение:

```python
route=[*state["route"], step]
```

вместо мутации:

```python
state["route"].append(step)
```

Почему: LangGraph, replay, checkpointing и тесты проще, если node возвращает
новое partial update, а не мутирует входной state.

## Этап 4. Playwright и первый реальный UI-агент

Уроки 12-13 подключили реальный браузер:

- `PlaywrightBrowser`;
- accessibility snapshot;
- `get_by_role`, `get_by_label`, `get_by_text`, `locator`;
- скриншоты;
- `scripts/run_real_agent.py`;
- `runner.py` как composition root.

Ключевое решение: LLM не генерирует Playwright-код. Она выбирает
структурированный `BrowserAction`, а deterministic adapter переводит его в
Playwright call.

Это снижает риск небезопасного или невалидного кода от модели.

## Этап 5. Planner memory, Judge и typed targets

Уроки 14-16 улучшили надежность:

- planner начал видеть execution history;
- появился независимый Judge;
- `BrowserTarget` стал типизированным объектом;
- prompt запретил копировать snapshot syntax напрямую.

Проблема, которую решали: модель часто возвращала targets вроде:

```text
textbox="Task"
textbox[label=Task]
```

А executor ожидал поддерживаемый target language. Поэтому был введен строгий
формат:

```json
{"strategy": "label", "value": "Task"}
```

## Этап 6. Recovery, termination, classifier, bug reporter

Уроки 17-20 добавили failure handling:

- `max_failures`;
- `RunTermination`;
- `FailureClassification`;
- `BugReport`;
- отдельный Reporter role.

Теперь failed run не просто "упал", а получает объяснение:

```text
step_limit
failure_limit
judge_failed
human_rejected
```

А потом классифицируется:

```text
product_bug
agent_error
automation_error
environment_error
insufficient_evidence
```

Bug report создается только когда classification говорит, что это product bug.

## Этап 7. Reports, observability, checkpointing, approval

Уроки 21-25 добавили production-like features:

- `RunReport`;
- JSON и Markdown report через Jinja2;
- LangSmith trace config;
- checkpointing через `thread_id`;
- human-in-the-loop через `interrupt`;
- deterministic approval policy.

Важное разделение:

- checkpoint нужен для продолжения выполнения graph thread;
- run report нужен как итоговый пользовательский артефакт;
- LangSmith нужен для observability и evaluation;
- approval policy нужна для safety routing.

## Этап 8. Evaluation

Уроки 26-30 добавили оценку:

- Planner component evaluation;
- Judge evaluation и confusion matrix;
- deterministic end-to-end evaluation;
- live end-to-end evaluation с Ollama и Playwright;
- LangSmith datasets and experiments.

Ключевой вывод: агентные системы нельзя оценивать только "запустил один раз,
кажется работает". Нужны:

- фиксированные cases;
- reference outputs;
- метрики;
- повторные прогоны;
- разделение infrastructure errors и model behavior.

## Этап 9. Memory and feedback

Уроки 31-37 добавили память:

- `RunHistoryRecord`;
- `JsonlRunHistoryStore`;
- интеграция history в runner;
- `HumanFeedbackRecord`;
- `JsonlFeedbackStore`;
- CLI для добавления feedback;
- deterministic feedback retrieval;
- planner memory context;
- автоматическое подключение feedback memory в `run_agent`.

Итоговая цепочка:

```text
completed run
  -> RunReport
  -> RunHistoryRecord
  -> human feedback
  -> retrieval
  -> memory_context
  -> planner prompt
```

## Что было изучено

Были изучены:

- Pydantic domain modeling;
- LangChain runnable chains;
- structured output;
- LangGraph nodes, edges, routers, cycles;
- stateful agent design;
- Playwright browser automation;
- accessibility snapshots;
- separation of LLM reasoning and deterministic execution;
- independent judging;
- failure classification;
- bug report generation;
- Jinja2 reporting;
- LangSmith observability and evaluation;
- checkpointing and resume;
- human-in-the-loop;
- deterministic safety policies;
- append-only JSONL persistence;
- dependency injection;
- dependency inversion;
- Python `Protocol`;
- feedback memory;
- deterministic retrieval;
- prompt memory context;
- component and end-to-end testing.

## Что достигнуто

Проект дошел до состояния v0.1 educational demo:

- архитектура достаточно разделена по ответственностям;
- основные agentic компоненты покрыты тестами;
- есть реальный browser run;
- есть история и feedback memory;
- есть база learning-материалов;
- есть путь для следующего проекта: memory evaluation, RAG, semantic retrieval,
  generated tests и production hardening.
