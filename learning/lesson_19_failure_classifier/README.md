# Урок 19. Failure Classifier

## Что уже знает система

После урока 18 неуспешный запуск имеет:

```python
status="failed"
termination=RunTermination(
    kind="failure_limit",
    message="Failure limit 2 was reached.",
)
```

`termination` является фактом графа:

```text
Почему выполнение остановилось?
```

Но пользователь задаёт другой вопрос:

```text
Что, вероятнее всего, стало причиной проблемы?
```

Возможные ответы:

- дефект продукта;
- ошибка решения агента;
- проблема автоматизации;
- проблема окружения;
- недостаточно данных.

Для этого добавляем отдельную LLM-роль — Failure Classifier.

## Факт и интерпретация

Очень важно не смешивать:

```text
termination     → объективное решение policy графа
classification  → интерпретация evidence моделью
```

Пример:

```text
termination.kind = failure_limit
```

Classifier может решить:

```text
agent_error
```

потому что planner дважды выбрал отсутствующую кнопку.

Или:

```text
automation_error
```

потому что Playwright locator нестабилен.

Или:

```text
product_bug
```

если действия выполнились, но финальное состояние противоречит expected.

## Категории

```python
class FailureCategory(StrEnum):
    PRODUCT_BUG = "product_bug"
    AGENT_ERROR = "agent_error"
    AUTOMATION_ERROR = "automation_error"
    ENVIRONMENT_ERROR = "environment_error"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
```

### `product_bug`

Наблюдаемое поведение продукта противоречит expected result.

Пример:

```text
Клик Add успешен.
Snapshot после клика не содержит добавленную задачу.
Judge подтверждает отсутствие expected result.
```

### `agent_error`

Ошибка выбора или рассуждения planner-а.

Примеры:

- выбрал нерелевантный элемент;
- повторял уже неудачное действие;
- закончил сценарий слишком рано;
- неправильно использовал доступные данные.

### `automation_error`

Проблема browser automation, locator-а, ожидания или assertion.

Примеры:

- locator неоднозначен;
- Playwright timeout без доказательства дефекта продукта;
- assertion построен неправильно;
- browser adapter неверно сопоставил target.

### `environment_error`

Проблема внешней среды:

- сайт недоступен;
- DNS/network error;
- Chromium не запускается;
- тестовые credentials не работают;
- backend environment сломан.

### `insufficient_evidence`

Evidence недостаточно для надёжного вывода.

Это важная категория. Хорошая система должна уметь сказать:

```text
Я не знаю.
```

а не всегда придумывать уверенную причину.

## Модель классификации

```python
class FailureClassification(BaseModel):
    category: FailureCategory
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    should_create_bug: bool
```

### `category`

Машиночитаемый класс ошибки.

### `confidence`

Уверенность модели:

```text
0.0 → нет уверенности
1.0 → максимальная уверенность
```

Это не математическая вероятность. Это самооценка модели, которую позже можно
калибровать на evaluation dataset.

### `rationale`

Краткое объяснение выбора категории.

### `evidence`

Список конкретных фактов:

```text
Action error: Element is not clickable.
Judge check failed: Success message is absent.
Final snapshot contains error banner.
```

### `should_create_bug`

Отдельное решение:

```text
Достаточно ли evidence, чтобы передать данные Bug Reporter?
```

## Инвариант bug recommendation

Запрещаем:

```python
FailureClassification(
    category="automation_error",
    should_create_bug=True,
)
```

Bug report продукта можно рекомендовать только для:

```python
category == FailureCategory.PRODUCT_BUG
```

Validator:

```python
@model_validator(mode="after")
def validate_bug_recommendation(self):
    if (
        self.should_create_bug
        and self.category != FailureCategory.PRODUCT_BUG
    ):
        raise ValueError(
            "Only product_bug can recommend creating a bug"
        )
    return self
```

Для `product_bug` значение может быть и `False`, если confidence или evidence
недостаточны.

## Какие evidence получает classifier

Classifier получает:

- test goal;
- expected results;
- termination kind и message;
- execution history;
- final page snapshot;
- Judge verdict, если он существует.

Не все failed runs доходят до Judge:

```text
failure_limit → Judge не вызывался
step_limit    → Judge не вызывался
judge_failed  → verdict существует
```

Поэтому verdict является optional.

## Представление Judge verdict

Для prompt можно сформировать строку:

```text
No Judge verdict is available.
```

или:

```text
passed=False
summary=Expected result is not proven.
check=Success message is visible; passed=False; evidence=...
```

Форматирование должно быть детерминированным. Не нужен дополнительный LLM.

## Classifier prompt

System prompt уже находится в:

```text
src/browser_agent/classifier.py
```

Human message должен содержать переменные:

```text
Goal:
{goal}

Expected results:
{expected}

Termination:
{termination}

Judge verdict:
{judge_verdict}

Execution history:
{execution_history}

Final page snapshot:
{page_snapshot}
```

## Chain

Технический паттерн уже знаком:

```python
prompt = build_classifier_prompt()
structured_model = model.with_structured_output(
    FailureClassification
)
return prompt | structured_model
```

У нас уже три разные роли на одном паттерне:

```text
Planner    → BrowserAction
Judge      → JudgeVerdict
Classifier → FailureClassification
```

Это демонстрирует, что агентская архитектура определяется не только моделью,
а ролью, prompt-ом, входным контекстом, output schema и местом в графе.

## Classifier node

```python
def make_classifier_node(model):
    def classify(state: AgentState) -> dict:
        classification = classify_failure(...)
        return {"classification": classification}

    return classify
```

Нода не меняет status и termination. Они уже зафиксированы.

## Новая ветка графа

Было:

```text
fail_run → END
```

Станет:

```text
fail_run → classify_failure → END
```

Успешная ветка:

```text
pass_run → END
```

остаётся без классификации.

Почему classifier идёт после `fail_run`:

- status уже `failed`;
- termination уже вычислена;
- classifier получает полную причину остановки;
- классификация не влияет на управление browser loop.

## Физические модели и роли

Новая сигнатура builder:

```python
def build_agent_graph(
    model,
    browser,
    judge_model=None,
    classifier_model=None,
):
```

Defaults:

```python
judge_model = judge_model or model
classifier_model = classifier_model or model
```

Сейчас один `ChatOllama` выполняет три роли. Позже можно использовать разные
модели и сравнивать качество/стоимость.

## Задание 19.1. Доменная модель

В `models.py` реализуй:

```python
class FailureClassification(BaseModel):
    category: FailureCategory
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    should_create_bug: bool
```

Добавь validator для `should_create_bug`.

Проверка:

```powershell
python -m pytest tests\test_classifier_models.py -q
```

Ожидается:

```text
4 passed
```

## Задание 19.2. Prompt

В `classifier.py` реализуй `build_classifier_prompt()`.

Используй:

```python
ChatPromptTemplate.from_messages(...)
```

и переменные:

```text
goal
expected
termination
judge_verdict
execution_history
page_snapshot
```

## Задание 19.3. Chain

Реализуй:

```python
def build_classifier_chain(model):
```

через:

```python
model.with_structured_output(FailureClassification)
```

## Задание 19.4. Вызов classifier

В `classify_failure()`:

1. сформируй `execution_history`;
2. сформируй строку Judge verdict или сообщение об отсутствии;
3. сформируй termination через:

```python
f"{termination.kind}: {termination.message}"
```

4. вызови chain с шестью переменными.

## Задание 19.5. Node

`make_classifier_node()` должен прочитать:

```python
state["test_case"]
state["termination"]
state["page_snapshot"]
state["route"]
state.get("verdict")
```

и вернуть:

```python
{"classification": classification}
```

Проверка заданий 19.2–19.5:

```powershell
python -m pytest tests\test_classifier.py -q
```

Ожидается:

```text
3 passed
```

## Задание 19.6. Интеграция в граф

В `graph.py`:

1. импортируй `make_classifier_node`;
2. добавь параметр `classifier_model=None`;
3. вычисли:

```python
classifier_model = classifier_model or model
```

4. зарегистрируй:

```python
builder.add_node(
    "classify_failure",
    make_classifier_node(classifier_model),
)
```

5. замени:

```python
builder.add_edge("fail_run", END)
```

на:

```python
builder.add_edge("fail_run", "classify_failure")
builder.add_edge("classify_failure", END)
```

Проверка:

```powershell
python -m pytest tests\test_classifier_graph.py tests\test_graph.py -q
```

## Полная проверка

```powershell
python -m pytest -q
```

Ожидается:

```text
77 passed
```

## Реальный запуск

```powershell
conda activate UiBrowserAgent
$env:OLLAMA_MODEL="gpt-oss:20b"
python scripts\run_real_agent.py
```

Успешный сценарий не получит classification.

Чтобы увидеть classifier в реальном запуске, позже добавим отдельный
предсказуемо падающий тест-кейс. Не стоит специально ломать рабочий demo.

## Ограничения текущего classifier

- self-reported confidence не откалиброван;
- classifier пока не анализирует screenshot;
- нет deterministic rules перед LLM;
- нет evaluation dataset;
- одна и та же модель может наследовать ошибки planner-а;
- classifier не создаёт bug report, только рекомендует его.

## Что важно понять

1. Чем termination отличается от classification?
2. Почему classification является гипотезой, а не фактом?
3. Зачем нужна категория `insufficient_evidence`?
4. Почему только product bug может рекомендовать bug report?
5. Почему classifier запускается после `fail_run`?
6. Почему успешный запуск не нужно классифицировать?
7. Может ли одна физическая LLM выполнять несколько агентских ролей?
