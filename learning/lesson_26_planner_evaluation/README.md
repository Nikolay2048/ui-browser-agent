# Урок 26. Evaluation Planner

## Зачем нужен evaluation

Unit-тест отвечает:

```text
Правильно ли работает наш Python-код?
```

Evaluation отвечает:

```text
Насколько хорошо LLM решает набор реальных задач?
```

Например, unit-тест доказывает, что Planner возвращает `BrowserAction`.
Но он не доказывает, что модель выбрала правильное поле или кнопку.

Изменение prompt может исправить один сценарий и сломать другой. Поэтому
production-разработка LLM-систем использует повторяемые эксперименты:

```text
фиксированный dataset
→ версия model + prompt
→ outputs
→ scorers
→ metrics
→ сравнение с предыдущей версией
```

## Три части evaluation

### Dataset

Набор примеров:

```text
inputs:
  test_case
  page_snapshot
  route

reference output:
  expected BrowserAction
```

Reference action должен быть подтверждён человеком или надёжным правилом.

### Target

Часть приложения, которую проверяем. В этом уроке target — только Planner:

```python
plan_next_action(...)
```

Мы не запускаем browser, Judge и полный LangGraph. Это component evaluation.

### Evaluator

Функция, сравнивающая actual и reference output.

## Почему не сравниваем reason

Два корректных ответа:

```text
"Enter the username."
"Fill the username field using test data."
```

Текст различается, но browser behavior одинаков:

```text
action=fill
target=label Username
value=standard_user
```

Поэтому оцениваем:

- `action`;
- `target`;
- `value`;
- exact match этих трёх полей.

## Метрики

Для одного примера:

```python
PlannerActionScore(
    action_match=True,
    target_match=False,
    value_match=True,
    exact_match=False,
    score=2 / 3,
)
```

`score` является средней долей совпавших компонентов.

Для эксперимента:

```text
exact_accuracy
action_accuracy
target_accuracy
value_accuracy
average_score
```

Exact accuracy — главная метрика. Частичные метрики помогают понять причину
ошибки.

## Задание 26.1. Scorer

Реализуй `score_planner_action()` в `planner_evaluation.py`.

Алгоритм:

```python
action_match = expected.action == actual.action
target_match = expected.target == actual.target
value_match = expected.value == actual.value
exact_match = action_match and target_match and value_match

component_score = sum(
    [action_match, target_match, value_match]
) / 3
```

В Python `bool` участвует в арифметике как `0` или `1`.

Верни `PlannerActionScore`.

## Задание 26.2. Aggregate metrics

Если `scores` пуст:

```python
raise ValueError("scores must not be empty")
```

Для accuracy:

```python
sum(score.action_match for score in scores) / len(scores)
```

`exact_matches` — целое количество, `exact_accuracy` — доля.

Реализуй `summarize_planner_scores()`.

## Задание 26.3. Запуск одного case

```python
actual = plan_next_action(
    model=model,
    test_case=case.test_case,
    page_snapshot=case.page_snapshot,
    route=case.route,
)
score = score_planner_action(case.expected_action, actual)
return actual, score
```

Здесь вызывается настоящий production Planner, а не дублирующая evaluation
реализация. Иначе мы будем тестировать другой код.

Проверка 26.1-26.3:

```powershell
python -m pytest tests\test_planner_evaluation.py -q --basetemp=.pytest-tmp
```

После этих заданий первые шесть тестов должны пройти.

## Локальный dataset

Файл:

```text
evaluations/planner_cases.json
```

Сейчас в нём три простых примера:

- заполнение Username;
- нажатие Login;
- finish после появления результата.

Это smoke dataset, а не достаточный production benchmark. Позже добавим:

- похожие кнопки;
- неудачную history;
- изменённый DOM;
- неоднозначные страницы;
- negative cases;
- реальные ошибки из LangSmith traces.

## Локальный эксперимент

После реализации функций:

```powershell
python scripts\evaluate_planner.py
```

Пример результата:

```text
fill-username: exact=True score=1.00 action=fill
click-login: exact=False score=0.67 action=click
finish-visible-result: exact=True score=1.00 action=finish

SUMMARY
{
  "total_cases": 3,
  "exact_accuracy": 0.666...
}
```

Низкий результат не означает ошибку evaluation. Он показывает текущее качество
конкретной модели и prompt.

## LangSmith target

LangSmith передаёт target обычные словари. Нужно восстановить Pydantic-модели:

```python
test_case = TestCase.model_validate(inputs["test_case"])
route = [
    ExecutionStep.model_validate(step)
    for step in inputs.get("route", [])
]
```

Затем вызвать Planner и вернуть JSON-compatible output:

```python
return {
    "action": action.model_dump(mode="json"),
}
```

### Задание 26.4

Реализуй `make_planner_target(model)`, который возвращает вложенную функцию:

```python
def target(inputs: dict) -> dict:
    ...
return target
```

## LangSmith code evaluator

Custom evaluator получает:

```python
inputs
outputs
reference_outputs
```

Нас интересуют:

```python
actual = BrowserAction.model_validate(outputs["action"])
expected = BrowserAction.model_validate(
    reference_outputs["action"]
)
```

Верни:

```python
{
    "key": "planner_exact_match",
    "score": float(score.exact_match),
}
```

### Задание 26.5

Реализуй `planner_action_evaluator()`.

После всех заданий:

```text
8 passed
```

## Загрузка dataset в LangSmith

Это ручная часть после локального evaluation. Основные компоненты LangSmith:

```text
Dataset   -> набор examples
Target    -> make_planner_target(model)
Evaluator -> planner_action_evaluator
Experiment -> результаты конкретной версии
```

Пример создания:

```python
from langsmith import Client

client = Client()
dataset = client.create_dataset(
    dataset_name="ui-browser-agent-planner-v1",
    description="Human-approved next actions for Planner evaluation.",
)

examples = [
    {
        "inputs": {
            "test_case": case.test_case.model_dump(mode="json"),
            "page_snapshot": case.page_snapshot,
            "route": [
                step.model_dump(mode="json")
                for step in case.route
            ],
        },
        "outputs": {
            "action": case.expected_action.model_dump(mode="json"),
        },
        "metadata": {"case_id": case.id},
    }
    for case in cases
]

client.create_examples(
    dataset_id=dataset.id,
    examples=examples,
)
```

Запуск:

```python
client.evaluate(
    make_planner_target(model),
    data="ui-browser-agent-planner-v1",
    evaluators=[planner_action_evaluator],
    experiment_prefix="planner-qwen-current-prompt",
    max_concurrency=1,
)
```

Для локальной Ollama используем `max_concurrency=1`, чтобы несколько больших
запросов не конкурировали за GPU.

В этом уроке не автоматизируем повторное создание dataset: сначала вручную
увидим структуру в LangSmith. В следующей итерации сделаем idempotent sync.

## Что смотреть в LangSmith

Открой:

```text
Datasets & Experiments
→ ui-browser-agent-planner-v1
→ experiment
```

Проверь:

- Inputs;
- Reference output;
- Actual output;
- `planner_exact_match`;
- ошибочные строки;
- trace Planner для каждой строки.

Сравнение двух версий:

```text
planner-qwen-prompt-v1
planner-qwen-prompt-v2
```

Промежуточная цель — не получить 100%, а обнаружить повторяемые классы ошибок.

## Unit test и evaluation

```text
pytest:
  scorer правильно считает?
  target правильно сериализует?
  пустой список отклоняется?

evaluation:
  модель выбрала правильное действие?
  новая версия prompt стала лучше?
  на каких типах страниц происходят ошибки?
```

Никогда не делай реальные LLM evaluation частью обычного `pytest`: они
медленные, недетерминированные и требуют внешней модели.

## Полная проверка

```powershell
python -m pytest -q --basetemp=.pytest-tmp
```

Ожидается:

```text
136 passed
```

## Вопросы для самопроверки

1. Чем dataset отличается от обычного списка unit-тестов?
2. Что является target в этом уроке?
3. Почему reason не участвует в exact match?
4. Зачем нужны component metrics, если есть exact accuracy?
5. Почему evaluation использует production `plan_next_action()`?
6. Почему реальный LLM evaluation не запускается через pytest?
7. Как experiment помогает сравнить две версии prompt?

## Следующий урок

Урок 27: Evaluation Judge, confusion matrix, false positive и false negative.
Для UI-тестирования особенно опасен false positive: дефект существует, но Judge
объявил запуск успешным.
