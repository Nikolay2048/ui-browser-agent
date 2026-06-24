# LangGraph Agent Flow

## AgentState

`AgentState` - рабочая память одного запуска. Он не является долговременной
памятью и не должен напрямую сохраняться как итоговый артефакт.

Ключевые поля:

```text
test_case              входной сценарий
current_url            текущий URL
page_snapshot          accessibility snapshot текущей страницы
route                  список ExecutionStep
step_count             число выполненных browser actions
failure_count          число failed ActionResult
status                 running / passed / failed
proposed_action        BrowserAction от planner
last_result            ActionResult последнего execute
verdict                JudgeVerdict
termination            RunTermination
classification         FailureClassification
bug_report             BugReport
memory_context         retrieved human feedback for planner
```

## Ноды графа

### initialize

Файл:

```text
graph.py
```

Инициализирует поля:

```python
{
    "current_url": state["test_case"].start_url,
    "route": [],
    "step_count": 0,
    "failure_count": 0,
    "status": "running",
}
```

### observe

Файл:

```text
observer.py
```

Считывает текущее состояние browser:

```python
{
    "current_url": browser.current_url,
    "page_snapshot": browser.snapshot(),
}
```

### plan

Файл:

```text
planner.py
```

Вызывает LLM chain:

```text
ChatPromptTemplate | model.with_structured_output(BrowserAction)
```

На вход получает:

- goal;
- test_data;
- expected results;
- previous human feedback;
- execution history;
- current page snapshot.

Возвращает:

```python
{"proposed_action": BrowserAction(...)}
```

### execute

Файл:

```text
executor.py
```

Выполняет `state["proposed_action"]` через browser adapter.

Возвращает:

```python
{
    "last_result": result,
    "step_count": next_step_number,
    "failure_count": next_failure_count,
    "route": [*state["route"], step],
}
```

Важный момент: route не мутируется через `.append()`. Создается новый список.

### judge

Файл:

```text
judge.py
```

Независимо проверяет expected results.

Возвращает:

```python
{"verdict": JudgeVerdict(...)}
```

### pass_run

Файл:

```text
graph.py
```

Ставит:

```python
{
    "status": "passed",
    "termination": RunTermination(kind=JUDGE_PASSED, ...)
}
```

### fail_run

Файл:

```text
graph.py
```

Определяет причину завершения:

- `STEP_LIMIT`;
- `FAILURE_LIMIT`;
- `JUDGE_FAILED`.

### classify_failure

Файл:

```text
classifier.py
```

LLM-классификатор выбирает failure category:

- product bug;
- agent error;
- automation error;
- environment error;
- insufficient evidence.

### report_bug

Файл:

```text
reporter.py
```

Создает `BugReport`, если classification говорит `should_create_bug=True`.

### request_approval / reject_run

Файл:

```text
approval.py
```

Использует LangGraph `interrupt()` для human-in-the-loop approval.

### assess_action_risk

Файл:

```text
approval_policy.py
```

Детерминированно проверяет action на risky keywords.

## Routers

### route_planned_action

```python
if proposed_action.action == FINISH:
    return "judge"
return "execute"
```

Planner не завершает run сам. Он только предлагает `finish`, после чего Judge
проверяет expected results.

### route_after_execution

Логика:

```text
если достигнут max_steps -> fail_run
если action success -> observe
если достигнут max_failures -> fail_run
иначе -> observe
```

Даже после failed action граф снова наблюдает страницу, пока не достигнут
failure limit. Это дает агенту шанс восстановиться.

### route_after_judge

```text
verdict.passed -> pass_run
else -> fail_run
```

### route_after_classification

```text
should_create_bug -> report_bug
else -> END
```

## Почему Current page в конце prompt

Planner prompt построен так:

```text
Goal
Test data
Expected results
Previous human feedback
Execution history
Current page
```

`Current page` находится в конце, потому что это самая свежая информация о
реальности. Feedback и history помогают, но snapshot должен оставаться
источником правды. Если feedback говорит "нажми Save", а на текущей странице нет
Save, модель не должна следовать feedback.

## Частые ошибки в LangGraph

### Мутировать state напрямую

Плохо:

```python
state["route"].append(step)
return {"route": state["route"]}
```

Лучше:

```python
return {"route": [*state["route"], step]}
```

### Путать node и router

Node выполняет работу и возвращает update.

Router выбирает следующий edge и не должен делать side effects.

### Завершать run planner-ом без Judge

Planner может ошибиться. Поэтому `finish` идет в `judge`, а не сразу в `pass_run`.

### Делать LLM ответственным за безопасность

Risk policy должна быть deterministic. LLM может объяснить, но не должна быть
единственным механизмом safety.

### Смешивать persistence с graph nodes

Report/history/feedback сохраняются в runner или dedicated stores, а не внутри
planner/executor/judge.

## Graph configuration

`build_agent_graph()` принимает:

```python
model
browser
judge_model=None
classifier_model=None
reporter_model=None
checkpointer=None
require_approval=False
approval_policy_enabled=False
```

Это дает flexibility:

- можно использовать одну модель для всех roles;
- можно подставить разные модели;
- можно включить checkpointing;
- можно включить manual approval;
- можно включить policy-based approval.

`require_approval` и `approval_policy_enabled` взаимно исключающие режимы.

## Stream vs invoke

`runner.py` использует:

```python
graph.stream(..., stream_mode="values")
```

Зачем:

- можно печатать каждое состояние через `on_state`;
- можно видеть route в реальном времени;
- удобно отлаживать;
- можно сохранить последнее состояние как `final_state`.

Обычный `invoke()` вернул бы только итог, но не дал бы такого удобного live
debug output.
