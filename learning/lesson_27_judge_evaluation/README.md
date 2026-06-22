# Урок 27. Evaluation Judge

## Почему Judge нужно оценивать отдельно

Planner может выбрать неправильное действие. Judge может совершить более
опасную ошибку: объявить тест успешным, когда дефект существует.

```text
реальный результат failed
Judge вернул passed=True
→ дефект скрыт
→ bug report не создаётся
→ CI показывает зелёный результат
```

Поэтому общей accuracy недостаточно. Нужна confusion matrix.

## Positive и negative

Для этого урока:

```text
positive = expected result доказан, passed=True
negative = expected result не доказан, passed=False
```

Четыре исхода:

| Expected | Actual | Outcome | Значение |
|---|---|---|---|
| pass | pass | TP | корректный success |
| fail | fail | TN | корректно найденная проблема |
| fail | pass | FP | дефект пропущен |
| pass | fail | FN | исправный сценарий ошибочно упал |

`FP` является главным риском Judge.

## Метрики

```text
accuracy  = (TP + TN) / all
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
FPR       = FP / (FP + TN)
FNR       = FN / (FN + TP)
```

Если знаменатель равен нулю, в этом учебном проекте возвращаем `0.0`. В отчёте
production-системы дополнительно отмечают метрику как undefined.

## Dataset

Файл:

```text
evaluations/judge_cases.json
```

Вход:

```text
test_case.expected
page_snapshot
route
```

Reference:

```text
expected_passed
```

Label должен задаваться человеком или детерминированной проверкой, а не другим
вызовом той же Judge-модели.

## Задание 27.1. Outcome scorer

Реализуй `score_judge_verdict()`:

```python
actual_passed = actual.passed

if expected_passed and actual_passed:
    outcome = "tp"
elif not expected_passed and not actual_passed:
    outcome = "tn"
elif not expected_passed and actual_passed:
    outcome = "fp"
else:
    outcome = "fn"
```

`correct` истинно для `tp` и `tn`.

## Задание 27.2. Confusion matrix

В `summarize_judge_scores()`:

1. отклони пустой список;
2. посчитай каждый outcome;
3. вычисли метрики;
4. защити деление на ноль.

Удобный helper:

```python
def safe_divide(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
```

## Задание 27.3. Production Judge target

`evaluate_judge_case()` должен вызвать настоящий:

```python
judge_run(
    model=model,
    test_case=case.test_case,
    page_snapshot=case.page_snapshot,
    route=case.route,
)
```

Затем вызвать scorer.

Проверка первых заданий:

```powershell
python -m pytest tests\test_judge_evaluation.py -q --basetemp=.pytest-tmp
```

После 27.1-27.3 большая часть тестов должна пройти.

## Задание 27.4. LangSmith target

Как в Planner evaluation:

1. восстанови `TestCase`;
2. восстанови `ExecutionStep[]`;
3. вызови `judge_run()`;
4. верни:

```python
{
    "verdict": verdict.model_dump(mode="json"),
}
```

## Задание 27.5. Correctness evaluator

```python
actual = JudgeVerdict.model_validate(outputs["verdict"])
expected_passed = bool(reference_outputs["passed"])
score = score_judge_verdict(expected_passed, actual)

return {
    "key": "judge_correct",
    "score": float(score.correct),
}
```

## Задание 27.6. False-positive evaluator

Отдельная метрика должна явно подсвечивать опасную ошибку:

```python
return {
    "key": "judge_false_positive",
    "score": float(score.outcome == "fp"),
}
```

Здесь `1.0` означает наличие проблемы, в отличие от correctness. Название
метрики делает направление явным.

После всех заданий:

```text
11 passed
```

## Локальный запуск

```powershell
python scripts\evaluate_judge.py
```

Пример:

```text
task-visible-pass: expected=True actual=True outcome=tp
task-missing-fail: expected=False actual=True outcome=fp

SUMMARY
{
  "accuracy": 0.75,
  "false_positive_rate": 0.5
}
```

## LangSmith dataset

Создай dataset:

```text
ui-browser-agent-judge-v1
```

Каждый example:

```python
{
    "inputs": {
        "test_case": case.test_case.model_dump(mode="json"),
        "page_snapshot": case.page_snapshot,
        "route": [...],
    },
    "outputs": {
        "passed": case.expected_passed,
    },
    "metadata": {
        "case_id": case.id,
    },
}
```

## LangSmith experiment

Запуск аналогичен Planner:

```python
client.evaluate(
    make_judge_target(model),
    data="ui-browser-agent-judge-v1",
    evaluators=[
        judge_correctness_evaluator,
        judge_false_positive_evaluator,
    ],
    experiment_prefix="judge-current-prompt",
    max_concurrency=1,
)
```

Смотри две метрики:

```text
judge_correct          -> выше лучше
judge_false_positive   -> ниже лучше
```

## Почему не оцениваем evidence в этом уроке

Верный boolean с выдуманным evidence тоже является проблемой. Но оценка качества
evidence требует отдельного rubric:

- связано ли evidence со snapshot;
- доказывает ли оно конкретный expected result;
- нет ли выдуманных фактов.

Сначала строим надёжную pass/fail классификацию. Evidence evaluation добавим
после увеличения dataset.

## Полная проверка

```powershell
python -m pytest -q --basetemp=.pytest-tmp
```

Ожидается:

```text
147 passed
```

## Самопроверка

1. Почему accuracy недостаточно для Judge?
2. Чем FP опаснее FN в UI-тестировании?
3. Кто должен задавать reference label?
4. Почему Judge нельзя оценивать его собственным ответом?
5. Почему false positive вынесен в отдельную LangSmith metric?
6. Что означает нулевой знаменатель precision или recall?

## Следующий этап

После этого урока проведём контролируемую реорганизацию пакета по production
границам, а затем перейдём к end-to-end evaluation и RAG.
