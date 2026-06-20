# Урок 21. RunReport и сохранение результата

## Цель

После завершения графа результат существует только в `AgentState`. Это удобно
во время выполнения, но неудобно для внешних потребителей:

- `AgentState` содержит временные поля planner и executor;
- словарь легко получить в неполном состоянии;
- после завершения процесса он исчезает;
- Jira, CI и человек ожидают стабильный документ.

В этом уроке построим границу:

```text
AgentState -> RunReport -> JSON + Markdown
```

Здесь нет новой LLM-роли. Преобразование должно быть детерминированным.

## State и итоговый артефакт

`AgentState` является рабочей памятью графа. В нём находятся как итоговые, так
и промежуточные значения:

```text
page_snapshot
proposed_action
last_result
route
verdict
termination
classification
bug_report
```

`RunReport` является публичным результатом одного законченного запуска. Он
содержит только данные, которые нужно сохранить и передать дальше.

Это разные ответственности:

```text
AgentState = как агент работает
RunReport  = что агент получил в результате
```

Нельзя просто сохранять весь state. В будущем внутренние поля графа изменятся,
а формат отчёта должен оставаться стабильным.

## Модель RunReport

Реализуй в `src/browser_agent/models.py`:

```python
class RunReport(BaseModel):
    test_case: TestCase
    status: Literal["passed", "failed"]
    final_url: str = Field(min_length=1)
    final_snapshot: str = Field(min_length=1)
    step_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    route: list[ExecutionStep]
    termination: RunTermination
    verdict: JudgeVerdict | None = None
    classification: FailureClassification | None = None
    bug_report: BugReport | None = None
```

Почему `final_snapshot` обязателен: отчёт без наблюдаемого конечного состояния
теряет важнейшее evidence.

Почему optional-поля имеют `None`: успешный запуск не требует classification и
bug report, а завершение по лимиту может не иметь Judge verdict.

### Задание 21.1

Реализуй модель и проверь:

```powershell
python -m pytest tests\test_run_report_models.py -q --basetemp=.pytest-tmp
```

Ожидается `4 passed`.

## Сборка отчёта

Функция `build_run_report(state)` является адаптером между двумя контрактами.
Она не должна менять `state` и не должна обращаться к LLM.

Соответствие полей:

```text
state["test_case"]       -> report.test_case
state["status"]          -> report.status
state["current_url"]     -> report.final_url
state["page_snapshot"]   -> report.final_snapshot
state["step_count"]      -> report.step_count
state["failure_count"]   -> report.failure_count
state["route"]           -> report.route
state["termination"]     -> report.termination
state.get("verdict")     -> report.verdict
state.get("classification") -> report.classification
state.get("bug_report")  -> report.bug_report
```

Обязательные поля читаем через `state["..."]`. Если граф нарушил контракт, нам
нужна явная ошибка, а не тихое значение по умолчанию.

Optional-поля читаем через `state.get(...)`.

### Задание 21.2

Реализуй `build_run_report()` в
`src/browser_agent/reporting.py`.

## Markdown renderer

JSON нужен машине, Markdown нужен человеку. Renderer не должен повторно
анализировать результат или придумывать evidence. Он только форматирует модель.

Минимальные разделы:

```markdown
# Test Run: <test case name>

## Summary
**Status:** passed
**Test case:** saved-report
**Final URL:** https://example.com/tasks
**Steps:** 0
**Failures:** 0

## Goal
...

## Expected Results
- ...

## Termination
...

## Judge Verdict
...

## Failure Classification
...

## Bug Report
...
```

Если optional-секция отсутствует, напиши это явно:

```text
No Judge verdict was recorded.
No failure classification was required.
No bug report was created.
```

Так читатель отличает «данных нет по смыслу» от «renderer забыл поле».

Для route добавь раздел `## Execution Route`. Каждый шаг может содержать номер,
действие, target, success и error. При пустом маршруте выведи:

```text
No browser actions were executed.
```

Для BugReport выведи хотя бы title, severity, expected, actual, reproduction
steps и evidence.

### Задание 21.3

Реализуй `render_run_report_markdown()`.

Не используй LLM и не собирай Markdown внутри `build_run_report()`. Построение
доменных данных и их представление являются разными слоями.

## Сохранение

Функция:

```python
save_run_report(report, output_dir) -> tuple[Path, Path]
```

должна:

1. преобразовать `output_dir` в `Path`;
2. создать каталог через `mkdir(parents=True, exist_ok=True)`;
3. сохранить JSON как `<test_case.id>.json`;
4. сохранить Markdown как `<test_case.id>.md`;
5. использовать UTF-8;
6. вернуть `(json_path, markdown_path)`.

Pydantic умеет сериализовать вложенные модели и enum:

```python
report.model_dump_json(indent=2)
```

Запись:

```python
json_path.write_text(json_text, encoding="utf-8")
```

### Задание 21.4

Реализуй `save_run_report()`.

Проверка заданий 21.2-21.4:

```powershell
python -m pytest tests\test_reporting.py -q --basetemp=.pytest-tmp
```

Ожидается `4 passed`.

## Интеграция в runner

Сохранение отчёта не является нодой графа. Граф отвечает за агентное выполнение,
а composition layer решает, что делать с законченным результатом.

Расширь сигнатуру:

```python
def run_agent(
    model,
    browser,
    test_case: TestCase,
    on_state: Callable[[dict], None] | None = None,
    report_dir: str | Path | None = None,
) -> dict:
```

После проверки `final_state is not None`:

```python
if report_dir is not None:
    report = build_run_report(final_state)
    save_run_report(report, report_dir)
```

Почему это выполняется после stream: только последний state содержит
окончательные status, termination, classification и bug report.

Почему `report_dir=None`: старые вызовы `run_agent()` сохраняют прежнее
поведение и ничего не записывают на диск.

### Задание 21.5

1. Импортируй `Path`, `build_run_report` и `save_run_report`.
2. Добавь параметр `report_dir`.
3. Сохраняй отчёт только после полного завершения графа.

Проверка:

```powershell
python -m pytest tests\test_runner_reporting.py -q --basetemp=.pytest-tmp
```

Ожидается `1 passed`.

## Подключение реального запуска

В `scripts/run_real_agent.py` передай:

```python
report_dir=PROJECT_ROOT / "artifacts" / test_case.id / "report",
```

После реального запуска должны появиться:

```text
artifacts/<test-case-id>/report/<test-case-id>.json
artifacts/<test-case-id>/report/<test-case-id>.md
```

Это часть задания, но отдельный unit-тест для script не нужен.

## Полная проверка

```powershell
python -m pytest -q --basetemp=.pytest-tmp
```

Ожидается:

```text
95 passed
```

## Вопросы для самопроверки

1. Почему нельзя использовать `AgentState` как публичный формат отчёта?
2. Почему сборка `RunReport` не должна обращаться к LLM?
3. Зачем разделять модель отчёта и Markdown renderer?
4. Почему optional-поля нужно явно показывать в Markdown?
5. Почему отчёт сохраняется после завершения stream?
6. Почему сохранение файла находится в runner, а не внутри ноды графа?

## Что будет дальше

В уроке 22 подключим LangSmith. Научимся видеть отдельные LLM-вызовы Planner,
Judge, Classifier и Reporter, измерять latency и разбирать ошибочные решения не
по `print()`, а по полноценной трассе выполнения.
