# Урок 18. Причина завершения запуска

## Зачем недостаточно `passed` и `failed`

Сейчас финальный state содержит:

```python
status="passed"
```

или:

```python
status="failed"
```

Но `failed` может означать принципиально разные ситуации:

- Judge не подтвердил expected results;
- достигнут `max_steps`;
- достигнут `max_failures`.

Для пользователя, отчёта и будущего Failure Classifier это разные факты.

```text
status отвечает: чем закончился запуск?
termination отвечает: почему граф остановился?
```

## Status и termination

### Status

Status остаётся простым:

```text
running
passed
failed
```

Он удобен для фильтрации и API:

```python
if run.status == "failed":
    ...
```

### Termination

Причина завершения содержит более точную информацию:

```python
RunTermination(
    kind="failure_limit",
    message="Failure limit 2 was reached.",
)
```

Она нужна для:

- консольного вывода;
- Run Report;
- Failure Classifier;
- bug reporting;
- аналитики стабильности;
- принятия решения о повторном запуске.

## Почему это не Failure Classifier

Причина завершения:

```text
failure_limit
```

ещё не отвечает, кто виноват:

```text
product_bug?
agent_error?
automation_error?
environment_error?
```

Termination — объективный факт графа:

```text
Граф остановился, потому что исчерпал бюджет ошибок.
```

Classifier позже сделает интерпретацию:

```text
Почему возникли эти ошибки и к какой категории они относятся?
```

Нужно разделять факты и выводы.

## Enum причин

```python
class TerminationKind(StrEnum):
    JUDGE_PASSED = "judge_passed"
    JUDGE_FAILED = "judge_failed"
    STEP_LIMIT = "step_limit"
    FAILURE_LIMIT = "failure_limit"
```

### `judge_passed`

Planner предложил `finish`, Judge проверил evidence и подтвердил все expected.

### `judge_failed`

Planner предложил `finish`, но Judge не смог доказать один или несколько
expected results.

### `step_limit`

```python
step_count >= test_case.max_steps
```

Агент не завершил сценарий за разрешённое количество действий.

### `failure_limit`

```python
failure_count >= test_case.max_failures
```

Исчерпан бюджет failed browser actions.

## Почему используем enum

Можно было записывать строки:

```python
kind="steps ended"
kind="too many steps"
kind="step_limit"
```

Тогда разные части приложения начнут использовать разные значения.

Enum задаёт закрытый словарь:

```python
TerminationKind.STEP_LIMIT
```

Pydantic отклонит неизвестный kind.

Это полезно для машинной обработки, API и аналитики.

## Модель RunTermination

```python
class RunTermination(BaseModel):
    kind: TerminationKind
    message: str = Field(min_length=1)
```

`kind` нужен программе.

`message` нужен человеку:

```text
Step limit 5 was reached.
Failure limit 2 was reached.
Judge did not prove expected results: ...
```

Не стоит помещать в `kind` динамические числа или длинные пояснения.

## Где создаётся termination

Только терминальные ноды знают, что запуск действительно заканчивается:

```text
pass_run
fail_run
```

Router выбирает следующую ветку, но не изменяет state.

Поэтому:

```python
pass_run() → status + termination
fail_run() → status + termination
```

## `pass_run`

Успех сейчас возможен только после Judge:

```python
def pass_run(state: AgentState) -> dict:
    return {
        "status": "passed",
        "termination": RunTermination(
            kind=TerminationKind.JUDGE_PASSED,
            message="Judge proved every expected result.",
        ),
    }
```

Нода получает state, хотя для первой версии ей достаточно самого факта
перехода из Judge.

## `fail_run`

Одна нода вызывается из нескольких веток. Она должна определить причину по
state.

Рекомендуемый порядок:

```python
if state["step_count"] >= state["test_case"].max_steps:
    STEP_LIMIT
elif state["failure_count"] >= state["test_case"].max_failures:
    FAILURE_LIMIT
elif "verdict" in state and not state["verdict"].passed:
    JUDGE_FAILED
else:
    error
```

## Почему нужен порядок приоритетов

После одного действия одновременно может быть:

```text
step_count == max_steps
failure_count == max_failures
```

Router `route_after_execution()` сначала проверяет step limit. Поэтому
`fail_run()` должен использовать такой же приоритет:

```text
step_limit раньше failure_limit
```

Иначе router остановит граф из-за шагов, а termination сообщит другую причину.

Policy выбора ветки и объяснение результата должны быть согласованы.

## Judge failure проверяется после лимитов

`fail_run` после Judge обычно не имеет достигнутых лимитов. Но формально state
может содержать старые счётчики.

Для тестируемой и предсказуемой policy мы явно фиксируем приоритет:

```text
step limit
failure limit
judge failed
```

## Неожиданное состояние

Если `fail_run()` вызван, но ни одно условие не выполнено, это ошибка
архитектуры графа.

Не следует тихо придумывать причину:

```python
return RunTermination(kind="unknown", ...)
```

Полезнее:

```python
raise RuntimeError("Cannot determine failure termination reason")
```

Fail fast помогает обнаружить неправильное ребро или router.

## Поле AgentState

В state уже добавлено:

```python
termination: NotRequired[RunTermination]
```

До терминальной ноды поля нет. После завершения оно обязательно по фактическому
контракту запуска.

Позже мы выделим отдельную финальную модель `RunReport`, где termination будет
уже обязательным полем.

## Обновлённый консольный вывод

`scripts/run_real_agent.py` теперь выводит:

```text
failure_count
verdict
termination
```

Так можно увидеть не только действия, но и решение Judge и причину остановки.

## Задание 18.1. RunTermination

В `models.py` реализуй:

```python
class RunTermination(BaseModel):
    kind: TerminationKind
    message: str = Field(min_length=1)
```

Проверка:

```powershell
python -m pytest tests\test_termination.py -k message -q
```

## Задание 18.2. Успешное завершение

Измени сигнатуру:

```python
def pass_run(state: AgentState) -> dict:
```

Верни:

```python
{
    "status": "passed",
    "termination": RunTermination(
        kind=TerminationKind.JUDGE_PASSED,
        message="Judge proved every expected result.",
    ),
}
```

Проверка:

```powershell
python -m pytest tests\test_termination.py -k pass_run -q
```

## Задание 18.3. Неуспешное завершение

В `fail_run(state)` выбери причину в порядке:

1. `step_count >= max_steps`;
2. `failure_count >= max_failures`;
3. присутствует отрицательный Judge verdict;
4. иначе `RuntimeError`.

Для Judge message должен содержать summary:

```python
state["verdict"].summary
```

Для лимитов message должен содержать соответствующее число.

Проверка:

```powershell
python -m pytest tests\test_termination.py -q
```

## Полная проверка

```powershell
python -m pytest -q
```

Ожидается:

```text
69 passed
```

## Реальный запуск

```powershell
conda activate UiBrowserAgent
$env:OLLAMA_MODEL="gpt-oss:20b"
python scripts\run_real_agent.py
```

В успешном запуске ожидается:

```text
termination: judge_passed
```

## Что важно понять

1. Чем status отличается от termination?
2. Почему termination не является классификацией бага?
3. Почему причину создаёт terminal node, а не router?
4. Зачем согласовывать порядок проверок router и fail node?
5. Почему неизвестное terminal state лучше завершить `RuntimeError`?
6. Как termination поможет следующему Failure Classifier?
