# Урок 29. End-to-end evaluation полного агента

## Цель

Мы уже оцениваем компоненты:

```text
Planner evaluation -> правильное следующее действие
Judge evaluation   -> правильный pass/fail verdict
```

Но хорошая работа компонентов по отдельности не гарантирует успешную систему.

Пример:

```text
Planner сделал одну ошибку
→ recovery исправил маршрут
→ Judge дал правильный verdict
→ тест прошёл, но за 8 шагов вместо 2
```

С точки зрения component evaluation Planner ошибся. С точки зрения end-to-end
система достигла цели, но была неэффективной.

End-to-end evaluation отвечает:

```text
Завершила ли вся система test case с ожидаемым результатом,
причиной завершения и допустимым количеством шагов?
```

## Три уровня тестирования

### Unit tests

Проверяют детерминированный Python-код:

```text
router
validator
scorer
formatter
```

### Component evaluation

Проверяет отдельную LLM-роль:

```text
Planner
Judge
Classifier
```

### End-to-end evaluation

Запускает:

```text
TestCase
→ Observer
→ Planner
→ Executor
→ recovery
→ Judge
→ termination
```

и оценивает итоговый state.

## Почему scorer отделён от runner

Полный запуск может использовать:

- fake browser и deterministic model;
- реальный Playwright fixture;
- локальную Ollama;
- удалённый сайт;
- CI environment.

Метрики не должны зависеть от способа запуска:

```python
final_state = run_case(test_case)
score = score_agent_run(expected, final_state)
```

Это даёт две независимые границы:

```text
execution harness -> как получить final state
scorer            -> как оценить final state
```

## Модель ожиданий

```python
class EndToEndExpectation(BaseModel):
    status: Literal["passed", "failed"]
    max_steps: int
    termination_kind: TerminationKind
    expects_recovery: bool = False
```

Мы не сравниваем весь `AgentState`: в нём есть внутренние поля Planner,
snapshot и last result. Reference должен описывать значимое поведение системы.

## Метрики одного запуска

### Status match

```python
final_state["status"] == expected.status
```

### Termination match

```python
final_state["termination"].kind == expected.termination_kind
```

Одинаковый status может иметь разные причины:

```text
failed + judge_failed
failed + failure_limit
failed + human_rejected
```

### Step budget

```python
step_count <= expected.max_steps
```

Агент может решить задачу, но сделать слишком много действий. Step budget
измеряет эффективность.

### Recovery observed

В текущей системе recovery считаем наблюдаемым, если:

```python
status == "passed" and failure_count > 0
```

То есть агент встретил хотя бы одну ошибку действия, но всё равно завершился
успешно.

Это упрощённая метрика. Позже route analyzer сможет определять точный recovery
pattern.

### Exact match

```text
status match
AND termination match
AND within step budget
AND recovery expectation match
```

### Component score

Среднее четырёх boolean-компонентов:

```python
sum([
    status_match,
    termination_match,
    within_step_budget,
    recovery_match,
]) / 4
```

## Задание 29.1. Scorer одного run

Реализуй `score_agent_run()` в:

```text
src/browser_agent/evaluation/end_to_end.py
```

Чтение обязательных полей:

```python
status = final_state["status"]
step_count = final_state["step_count"]
failure_count = final_state["failure_count"]
termination = RunTermination.model_validate(
    final_state["termination"]
)
```

`model_validate()` принимает и готовый `RunTermination`, и обычный dict.

Вычисли:

```python
status_match = status == expected.status
termination_match = (
    termination.kind == expected.termination_kind
)
within_step_budget = step_count <= expected.max_steps
recovery_observed = (
    status == "passed"
    and failure_count > 0
)
recovery_match = (
    recovery_observed == expected.expects_recovery
)
```

Верни `EndToEndRunScore`.

## Задание 29.2. Summary

Реализуй `summarize_agent_runs()`.

Если список пуст:

```python
raise ValueError("scores must not be empty")
```

Метрики:

```text
exact_accuracy       -> доля exact_match
task_success_rate    -> доля status_match
termination_accuracy -> доля termination_match
step_budget_rate     -> доля within_step_budget
recovery_accuracy    -> доля recovery_match
average_steps
average_failures
average_score
```

Обрати внимание: `task_success_rate` здесь означает совпадение итогового status
с reference, а не просто долю `passed`. Dataset может содержать сценарии, где
правильным исходом является `failed`.

## Задание 29.3. Execution harness

```python
def evaluate_end_to_end_case(run_case, case):
    final_state = run_case(case.test_case)
    score = score_agent_run(case.expected, final_state)
    return final_state, score
```

`run_case` внедряется как зависимость. Evaluation-модуль не создаёт браузер и
модель самостоятельно.

Production runner можно адаптировать:

```python
def run_case(test_case):
    browser = browser_factory(test_case)
    return run_agent(model, browser, test_case)
```

Для unit tests передаётся обычная функция без LLM и Playwright.

## Задание 29.4. LangSmith target

LangSmith передаёт:

```python
{
    "test_case": {...}
}
```

Target должен:

1. восстановить `TestCase`;
2. вызвать `run_case`;
3. вернуть компактный output.

```python
return {
    "status": final_state["status"],
    "step_count": final_state["step_count"],
    "failure_count": final_state["failure_count"],
    "termination": termination.model_dump(mode="json"),
}
```

Почему не отправляем весь state:

- snapshots могут быть большими;
- route уже виден в trace;
- proposed action и last result являются внутренними деталями;
- evaluator использует только стабильный контракт.

## Задание 29.5. LangSmith evaluator

Reference output:

```python
{
    "expected": {
        "status": "passed",
        "max_steps": 2,
        "termination_kind": "judge_passed",
        "expects_recovery": false,
    }
}
```

Evaluator:

1. восстанавливает `EndToEndExpectation`;
2. превращает compact output обратно в минимальный final state;
3. вызывает `score_agent_run`;
4. возвращает:

```python
{
    "key": "e2e_exact_match",
    "score": float(score.exact_match),
}
```

## Dataset

Файл:

```text
evaluations/end_to_end_cases.json
```

Содержит:

- happy path;
- recovery после первой ошибки;
- завершение по failure budget.

Пока это спецификация scenarios. Реальный execution harness для них добавим
после реализации scorer-а, используя deterministic browser fixtures.

## Проверка

```powershell
python -m pytest tests\test_end_to_end_evaluation.py -q --basetemp=.pytest-tmp
```

Ожидается:

```text
8 passed
```

Полный набор:

```powershell
python -m pytest -q --basetemp=.pytest-tmp
```

Ожидается:

```text
160 passed
```

## Почему сначала deterministic E2E

Если сразу запустить Ollama и Playwright:

- тест будет медленным;
- результат может меняться;
- трудно понять, сломан agent или scorer;
- CI потребует GPU и браузер.

Сначала:

```text
детерминированный harness
→ проверка evaluation contract
→ реальный model/browser experiment
```

Это стандартный production-порядок.

## Ограничения текущих метрик

Пока не измеряем:

- latency;
- token usage;
- human intervention count;
- точность bug classification;
- качество bug report;
- evidence groundedness;
- визуальные расхождения.

Метрики добавляются только когда есть надёжный источник данных и понятная
интерпретация.

## Самопроверка

1. Чем end-to-end evaluation отличается от component evaluation?
2. Почему scorer не должен создавать browser?
3. Зачем отдельно проверять termination kind?
4. Почему успешный, но длинный маршрут не считается exact match?
5. Как определяется recovery в текущей версии?
6. Почему LangSmith target возвращает compact output?
7. Почему реальные LLM/browser experiments не входят в обычный pytest?

## Следующий шаг

После scorer-а создадим deterministic end-to-end harness для трёх scenarios,
затем запустим тот же контракт на реальном Playwright fixture.
