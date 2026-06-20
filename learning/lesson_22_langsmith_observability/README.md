# Урок 22. Наблюдаемость агента через LangSmith

## Цель

До этого мы диагностировали агента через:

- вывод state в консоль;
- unit-тесты;
- скриншоты;
- JSON и Markdown отчёты.

Этого недостаточно для анализа LLM-системы. Нам важно увидеть:

```text
какая нода выполнялась
какой prompt получил Planner
какой структурированный ответ вернула модель
сколько занял каждый вызов
почему граф выбрал конкретную ветку
```

LangSmith записывает выполнение как trace:

```text
один запуск test case
└── LangGraph
    ├── initialize
    ├── observe
    ├── plan
    │   └── ChatOllama
    ├── execute
    ├── judge
    │   └── ChatOllama
    ├── classify_failure
    │   └── ChatOllama
    └── report_bug
        └── ChatOllama
```

Trace — полный путь одного запроса. Вложенный элемент trace часто называют
run или span.

## LangSmith не является памятью агента

LangSmith наблюдает за выполнением, но не управляет им:

```text
LangGraph   -> выполняет workflow
AgentState  -> хранит рабочее состояние
LangSmith   -> записывает, что происходило
RunReport   -> сохраняет доменный результат
```

Удаление trace не изменяет результат агента. Отключение LangSmith не должно
ломать выполнение теста.

## Настройка ключа

Не записывай API key в Python, README, `.env.example` или Git.

Для текущего PowerShell-сеанса:

```powershell
$env:LANGSMITH_TRACING="true"
$env:LANGSMITH_API_KEY="<твой ключ>"
$env:LANGSMITH_PROJECT="ui-browser-agent-dev"
```

Проверить наличие, не печатая ключ:

```powershell
Write-Host "Tracing: $env:LANGSMITH_TRACING"
Write-Host "Project: $env:LANGSMITH_PROJECT"
Write-Host "Key configured: $([bool]$env:LANGSMITH_API_KEY)"
```

Если ключ связан с несколькими workspace:

```powershell
$env:LANGSMITH_WORKSPACE_ID="<workspace id>"
```

Для EU-региона может потребоваться:

```powershell
$env:LANGSMITH_ENDPOINT="https://eu.api.smith.langchain.com"
```

В обычном US-регионе endpoint задавать не нужно.

## Задание 22.1. Первая автоматическая trace

После установки переменных запусти:

```powershell
python scripts\run_real_agent.py
```

Мы используем LangChain-компоненты внутри LangGraph, поэтому дополнительный
callback для базовой трассировки не нужен.

Открой:

```text
https://smith.langchain.com
```

Далее:

1. `Tracing`;
2. проект `ui-browser-agent-dev`;
3. последняя строка trace;
4. представление `Details`.

Проверь:

- виден корневой запуск графа;
- видны ноды `initialize`, `observe`, `plan`, `execute`, `judge`;
- внутри LLM-нод есть вызовы `ChatOllama`;
- доступны inputs, outputs и latency.

Если trace не появилась сразу, подожди несколько секунд. Отправка выполняется
в фоне.

## Почему нужны run_name, tags и metadata

Когда trace одна, её легко найти. Когда их тысячи, названия вроде
`LangGraph` мало помогают.

Нам нужен верхнеуровневый запуск:

```text
run_name: ui-test:first-real-agent
tags: browser-agent, ui-test
metadata:
  test_case_id: first-real-agent
  test_case_name: Create a task using the autonomous agent
  start_url: file:///...
  max_steps: 5
  max_failures: 2
```

Назначение:

- `run_name` — читаемое имя строки в UI;
- `tags` — небольшое множество категорий;
- `metadata` — именованные значения для фильтрации и анализа.

Конфигурация верхнего runnable наследуется вложенными вызовами.

## Безопасность metadata

Не помещай в metadata:

- пароль;
- token;
- cookie;
- API key;
- полное `test_data`;
- персональные данные.

Поэтому в задании мы переносим только идентификаторы и лимиты. Это не решает
всю задачу privacy: inputs LangGraph и prompts тоже могут содержать test data.
Позднее добавим sanitization и правила скрытия чувствительных данных.

## Задание 22.2. Trace config

Реализуй в `src/browser_agent/observability.py`:

```python
def build_trace_config(test_case: TestCase) -> RunnableConfig:
    return {
        "run_name": f"ui-test:{test_case.id}",
        "tags": ["browser-agent", "ui-test"],
        "metadata": {
            "test_case_id": test_case.id,
            "test_case_name": test_case.name,
            "start_url": test_case.start_url,
            "max_steps": test_case.max_steps,
            "max_failures": test_case.max_failures,
        },
    }
```

Проверка:

```powershell
python -m pytest tests\test_observability.py -q --basetemp=.pytest-tmp
```

Ожидается:

```text
3 passed
```

## Задание 22.3. Подключение к runner

В `runner.py` импортируй:

```python
from browser_agent.observability import build_trace_config
```

До цикла:

```python
trace_config = build_trace_config(test_case)
```

Передай config в stream:

```python
for state in graph.stream(
    {"test_case": test_case},
    config=trace_config,
    stream_mode="values",
):
```

`RunnableConfig` не является `AgentState`. Это управляющая конфигурация
конкретного запуска: callbacks, tags, metadata, run name и другие параметры.

Проверка:

```powershell
python -m pytest tests\test_runner_observability.py -q --basetemp=.pytest-tmp
```

Ожидается:

```text
1 passed
```

## Задание 22.4. Имя локальной модели

При создании `ChatOllama` в `scripts/run_real_agent.py` добавь:

```python
metadata={
    "ls_model_name": model_name,
    "ls_provider": "ollama",
},
```

Это помогает LangSmith отображать понятный идентификатор локальной модели.
Для Ollama стоимость обычно не вычисляется как для платного API, но latency и
структура вызовов остаются полезными.

## Что смотреть в LangSmith

### Верхний trace

Сначала проверь:

- итоговый output;
- общую длительность;
- ошибку верхнего уровня;
- metadata test case;
- последовательность нод.

### Planner

Открой `plan` и вложенный вызов модели:

- какой snapshot увидела модель;
- был ли передан execution history;
- какой target она выбрала;
- соответствует ли target нашему контракту.

### Judge

Проверь:

- все expected results;
- финальный snapshot;
- evidence для каждого check;
- согласованность `passed` и отдельных checks.

### Classifier

Для failed run:

- категорию;
- confidence;
- evidence;
- почему `should_create_bug` получил конкретное значение.

### Reporter

Если создан баг:

- не появились ли выдуманные шаги;
- совпадает ли expected с test case;
- основан ли actual на evidence;
- разумна ли severity.

## Типичные ошибки

### Проект пуст

Проверь:

```powershell
$env:LANGSMITH_TRACING
$env:LANGSMITH_PROJECT
$env:LANGSMITH_API_KEY.Length
```

Переменные должны быть установлены в том PowerShell-сеансе, из которого
запускается Python.

### 401 или invalid API key

Возможные причины:

- неверный ключ;
- ключ относится к другому workspace;
- нужен `LANGSMITH_WORKSPACE_ID`;
- аккаунт находится не в US-регионе и нужен правильный endpoint.

### Последняя trace не успела отправиться

Для коротких CLI-скриптов можно дождаться фоновой отправки:

```python
from langchain_core.tracers.langchain import wait_for_all_tracers

try:
    main()
finally:
    wait_for_all_tracers()
```

В нашем скрипте браузер ждёт Enter, поэтому обычно фоновой отправке хватает
времени. Пока не добавляй этот код: сначала проверь обычное поведение.

## Полная проверка

```powershell
python -m pytest -q --basetemp=.pytest-tmp
```

После выполнения ожидается:

```text
99 passed
```

Unit-тесты не отправляют trace в LangSmith. Интеграцию с облачным сервисом
проверяем отдельным ручным smoke test.

## LangSmith и Langfuse

Оба продукта решают сходные задачи:

- traces и вложенные spans;
- prompts, model responses и latency;
- metadata, tags и filtering;
- evaluation;
- datasets;
- мониторинг production LLM-приложений.

Ключевое практическое отличие для нас:

```text
LangSmith -> нативная интеграция с LangChain и LangGraph
Langfuse  -> framework-neutral платформа с open-source self-hosting
```

Langfuse можно использовать как облачный сервис или развернуть самостоятельно.
Self-hosting полезен при требованиях к размещению данных внутри собственной
инфраструктуры, но добавляет эксплуатацию Postgres, ClickHouse, Redis/Valkey и
object storage для production-развёртывания.

Для этого проекта сначала используем LangSmith, потому что он позволит увидеть
наш LangGraph почти без дополнительной инструментализации. Позже сделаем
отдельный сравнительный эксперимент с Langfuse или OpenTelemetry.

## Вопросы для самопроверки

1. Чем trace отличается от `AgentState`?
2. Почему LangSmith не должен влиять на решение graph router?
3. Чем tags отличаются от metadata?
4. Почему нельзя добавлять всё `test_data` в metadata?
5. Почему configuration передаётся отдельно от input state?
6. Что нужно проверить внутри trace Planner?
7. Когда self-hosted Langfuse может быть предпочтительнее?

## Что дальше

Урок 23 будет посвящён checkpointing LangGraph: сохранению состояния между
шагами, идентификатору thread и возобновлению незавершённого запуска.
