# AI Agents: Core Concepts

## Что такое AI-агент

AI-агент - это система, которая:

1. получает цель;
2. наблюдает текущее состояние среды;
3. выбирает следующее действие;
4. выполняет действие;
5. смотрит на результат;
6. повторяет цикл до успеха, ошибки или лимита.

Минимальная схема:

```text
Goal
  -> Observe
  -> Plan
  -> Act
  -> Observe
  -> ...
  -> Verify
```

В UI-agent проекте:

```text
TestCase
  -> page snapshot
  -> BrowserAction
  -> Playwright action
  -> screenshot/result
  -> Judge verdict
```

## Агент vs обычный LLM call

Обычный LLM call:

```text
input -> model -> output
```

Агент:

```text
input -> model -> action -> environment -> observation -> model -> ...
```

Ключевое отличие: агент взаимодействует со средой и меняет ее состояние.

## Главный цикл агента

```text
Observe
  Что сейчас видно?

Plan
  Что нужно сделать дальше?

Execute
  Выполнить действие во внешней среде.

Record
  Сохранить маршрут и evidence.

Judge
  Проверить, достигнута ли цель.
```

## State

State - это рабочая память одного запуска.

Пример:

```python
{
    "test_case": test_case,
    "page_snapshot": '- textbox "Task"',
    "route": [],
    "step_count": 0,
    "status": "running",
}
```

State нужен, чтобы:

- ноды графа могли обмениваться данными;
- маршрут выполнения был воспроизводим;
- можно было checkpoint/resume;
- можно было строить отчеты.

Типичная ошибка: использовать state как долговременную базу данных. State живет
внутри одного run. Для истории нужны отдельные модели.

## Planner

Planner выбирает следующее действие.

В хорошем агенте planner не должен:

- выполнять side effects;
- ходить в браузер напрямую;
- писать в файлы;
- знать детали Playwright API;
- решать, что тест точно passed без независимой проверки.

Planner должен:

```text
context -> one structured next action
```

Пример output:

```json
{
  "action": "fill",
  "target": {"strategy": "label", "value": "Task"},
  "value": "Learn AI Agents",
  "reason": "Fill the task input before clicking Add."
}
```

## Executor

Executor выполняет action.

Он должен быть deterministic:

```python
if action.action == "fill":
    browser.fill(action.target, action.value)
```

Почему executor не LLM:

- side effects должны быть ограничены;
- легче тестировать;
- меньше риск небезопасного поведения;
- меньше prompt injection surface.

## Tool

Tool - контролируемый способ воздействовать на внешний мир.

Примеры:

- browser click;
- browser fill;
- API call;
- database query;
- file read/write;
- email send.

Tool должен иметь:

- ясную schema;
- валидацию входа;
- ограниченную область действия;
- предсказуемый output;
- error handling.

## Observer

Observer превращает внешнюю среду в compact context.

В UI agent:

```text
browser page -> accessibility snapshot
```

Хороший observer:

- дает достаточно информации для решения;
- не перегружает prompt;
- не включает секреты;
- делает состояние сравнимым между шагами.

## Judge

Judge независимо проверяет, достигнута ли цель.

Почему нужен:

Planner может сказать `finish`, но это не доказательство.

Judge должен:

- использовать evidence;
- проверять каждое expected result;
- не доверять успешному click/fill как бизнес-результату;
- fail при недостатке evidence.

## Memory

Memory - информация из прошлого, которая помогает будущим запускам.

Виды памяти:

```text
Working memory      AgentState одного run
Checkpoint memory   технический resume
Episodic memory     история прошлых запусков
Feedback memory     человеческие коррекции
Semantic memory     знания, найденные через retrieval/RAG
```

Важно: не вся память должна попадать в prompt. Нужен retrieval.

## Retrieval

Retrieval - выбор релевантной части памяти.

Это не обязательно vector search.

Примеры:

```text
test_case_id exact match
scope filter
tag filter
semantic similarity
hybrid score
```

Правило:

```text
Memory без retrieval быстро становится мусором в prompt.
```

## Feedback Loop

Feedback loop:

```text
agent run
  -> human reviews result
  -> human writes correction
  -> correction stored as data
  -> future run retrieves correction
  -> planner uses correction
  -> evaluation checks improvement
```

Не путать с ручной правкой prompt. Prompt edits полезны, но не масштабируются как
основной механизм обучения системы.

## Evaluation

Evaluation отвечает на вопрос:

```text
Стало ли лучше?
```

Типы:

- unit tests;
- component eval;
- end-to-end eval;
- live eval;
- regression eval;
- human eval;
- LLM-as-judge eval.

Для агентов важно оценивать не только финальный success, но и:

- число шагов;
- recovery;
- false positives;
- route quality;
- safety;
- cost/latency.

## Observability

Observability позволяет понять:

- какой prompt ушел модели;
- какой structured output вернулся;
- какая нода выполнилась;
- почему graph пошел по ветке;
- где случился failure;
- какие memory records использовались.

Без observability агент превращается в черный ящик.

## Safety

UI agents могут нажимать реальные кнопки.

Safety boundaries:

- deterministic approval policy;
- human approval;
- action allowlist;
- domain restrictions;
- dry-run mode;
- audit log;
- irreversible action checks.

Нельзя полагаться только на "модель поймет, что это опасно".

## Базовый mental model

Когда проектируешь нового агента, отвечай на вопросы:

1. Какая цель?
2. Какая среда?
3. Что агент может наблюдать?
4. Какие действия разрешены?
5. Как выглядит state?
6. Кто выбирает действие?
7. Кто выполняет действие?
8. Кто проверяет результат?
9. Где route и evidence?
10. Какие лимиты?
11. Какая память?
12. Как измеряем качество?
