# Архитектура Browser Testing Agent

## Текущий workflow

```mermaid
flowchart TD
    S["TestCase"] --> I["initialize"]
    I --> O["observe"]
    O --> P["plan"]
    P -->|"finish"| J["judge"]
    P -->|"browser action"| R{"approval mode"}
    R -->|"disabled"| E["execute"]
    R -->|"all actions"| A["request_approval"]
    R -->|"risk policy"| RP["assess_action_risk"]
    RP -->|"safe"| E
    RP -->|"risky"| A
    A -->|"approved"| E
    A -->|"rejected"| HR["reject_run"]
    E -->|"continue"| O
    E -->|"limits reached"| F["fail_run"]
    J -->|"passed"| PASS["pass_run"]
    J -->|"failed"| F
    F --> C["classify_failure"]
    C -->|"product bug"| B["report_bug"]
    C -->|"other failure"| END["END"]
    B --> END
    HR --> END
    PASS --> END
```

## Слои

### Domain

`domain/models.py` содержит Pydantic-контракты. Модели не должны зависеть от
LangGraph, Playwright, LangSmith или файловой системы.

### Agent roles

- `planner.py` выбирает одно следующее действие;
- `judge.py` проверяет expected results;
- `classifier.py` объясняет failed run;
- `reporter.py` создаёт структурированный `BugReport`.

Каждая LLM-роль имеет отдельный prompt и structured output.

### Deterministic policies

- `approval_policy.py` решает, требуется ли human review;
- routers в `graph.py` выбирают ветки;
- Pydantic валидирует границы данных.

Решения безопасности не должны зависеть только от LLM.

### Browser infrastructure

- `browser.py` адаптирует Playwright к интерфейсу агента;
- `observer.py` получает компактный snapshot;
- `executor.py` является единственным слоем, выполняющим browser side effects.

### Workflow

`graph.py` связывает роли, policies и tools. Ноды возвращают partial state
updates, а routers не выполняют side effects.

### Application

`runner.py` отвечает за composition:

- открывает start URL;
- компилирует и запускает граф;
- подключает tracing/checkpointing;
- сохраняет итоговый отчёт.

### Output

- `reporting.py` преобразует final `AgentState` в `RunReport`;
- `templates/run_report.md.j2` формирует Markdown;
- JSON используется для программных интеграций.

### Evaluation

`evaluation/` содержит:

- component evaluation Planner;
- component evaluation Judge;
- end-to-end evaluation полного запуска.

Evaluation не является частью production workflow и запускается отдельными
tests/scripts/experiments.

## Runtime data

```text
TestCase
  -> AgentState
  -> ExecutionStep[]
  -> JudgeVerdict / RunTermination
  -> FailureClassification / BugReport
  -> RunReport
```

Разные механизмы хранения:

```text
AgentState  -> рабочая память одного выполнения
checkpoint  -> снимки одного thread
LangSmith   -> observability и experiments
RunReport   -> итоговый пользовательский артефакт
```

## Production-направление

Первая часть миграции выполнена:

```text
browser_agent/
├── domain/
└── evaluation/
```

Старые модули `browser_agent.models`, `browser_agent.planner_evaluation` и
`browser_agent.judge_evaluation` удалены после перевода всех consumers на новые
public API:

```python
from browser_agent.domain import TestCase
from browser_agent.evaluation.planner import PlannerEvaluationCase
from browser_agent.evaluation.judge import JudgeEvaluationCase
```

Следующие подпакеты будут выделяться только при практической необходимости:

```text
agents/
workflow/
infrastructure/
application/
reporting/
```

Миграция выполняется по одной границе ответственности и сопровождается тестами
ownership, public API и отсутствия устаревших модулей.
