# Урок 25. Policy-based approval

## Цель

Урок 24 останавливал каждое реальное browser action:

```text
plan -> request_approval -> execute
```

Это безопасно, но превращает автоматизацию в ручное тестирование. В production
human review обычно включают только для рискованных операций:

```text
plan
  -> assess_action_risk
       -> safe  -> execute
       -> risky -> request_approval
```

После этого урока approval-блок считаем завершённым и переходим к Evaluation.

## Почему policy не должна быть LLM

Правила безопасности должны быть:

- предсказуемыми;
- воспроизводимыми;
- покрытыми unit-тестами;
- независимыми от формулировки prompt;
- доступными для аудита.

LLM предлагает действие, но не выдаёт себе разрешение:

```text
Planner (недетерминированный) -> BrowserAction
Policy (детерминированная)    -> requires_approval
Executor                      -> side effect
```

## Контракт решения

Реализуй в `models.py`:

```python
class ApprovalPolicyDecision(BaseModel):
    requires_approval: bool
    reason: str = Field(min_length=1)
```

Это лучше голого `bool`: причина видна в state, checkpoint и LangSmith.

### Задание 25.1

Реализуй модель.

## Минимальная policy

Создадим простые правила:

```text
finish                         -> safe
assert_text                    -> safe
fill обычного поля             -> safe
fill password/token/card/cvv   -> risky
press Enter                    -> risky
click delete/remove/pay/...    -> risky
остальные действия             -> safe
```

Это не универсальная безопасность. Это первый прозрачный policy layer.

### Нормализация target

Собери текст из:

```python
action.target.value
action.target.name
```

Например:

```python
parts = [action.target.value]
if action.target.name:
    parts.append(action.target.name)
target_text = " ".join(parts).lower()
```

Для `target=None` используй пустую строку.

### Ключевые слова

Рискованный click:

```python
{
    "delete",
    "remove",
    "pay",
    "purchase",
    "checkout",
    "confirm",
    "publish",
    "send",
    "submit",
}
```

Чувствительный fill:

```python
{
    "password",
    "passcode",
    "token",
    "secret",
    "card",
    "cvv",
}
```

Проверка:

```python
any(keyword in target_text for keyword in keywords)
```

### Задание 25.2

Реализуй `assess_action_risk()` в `approval_policy.py`.

Возвращай `ApprovalPolicyDecision` во всех ветках. Причина должна объяснять
сработавшее правило.

## Policy node

```python
def make_assess_action_node(policy=assess_action_risk):
    def assess(state: AgentState) -> dict:
        decision = policy(state["proposed_action"])
        return {"approval_policy_decision": decision}

    return assess
```

Фабрика позволяет позднее передать policy конкретной организации.

### Задание 25.3

Реализуй node factory.

## Router

```python
def route_after_risk_assessment(state: AgentState) -> str:
    if state["approval_policy_decision"].requires_approval:
        return "request_approval"
    return "execute"
```

### Задание 25.4

Реализуй router.

Проверка заданий 25.1-25.4:

```powershell
python -m pytest tests\test_approval_policy.py -q --basetemp=.pytest-tmp
```

Ожидается:

```text
10 passed
```

## Интеграция графа

Добавь параметр:

```python
approval_policy_enabled: bool = False
```

Запрещаем одновременно включать два режима:

```python
if require_approval and approval_policy_enabled:
    raise ValueError(
        "require_approval and approval_policy_enabled are mutually exclusive"
    )
```

Три режима:

```text
оба False                  -> plan -> execute
require_approval=True      -> plan -> request_approval
approval_policy_enabled=True -> plan -> assess_action_risk
```

При policy mode зарегистрируй:

```python
builder.add_node(
    "assess_action_risk",
    make_assess_action_node(),
)
```

Approval-ноды нужны в обоих approval-режимах:

```python
approval_enabled = require_approval or approval_policy_enabled
```

Destination результата `"execute"`:

```python
if require_approval:
    execute_destination = "request_approval"
elif approval_policy_enabled:
    execute_destination = "assess_action_risk"
else:
    execute_destination = "execute"
```

Для policy node:

```python
builder.add_conditional_edges(
    "assess_action_risk",
    route_after_risk_assessment,
    {
        "request_approval": "request_approval",
        "execute": "execute",
    },
)
```

### Задание 25.5

Интегрируй policy в `graph.py`.

Проверка:

```powershell
python -m pytest tests\test_approval_policy_graph.py -q --basetemp=.pytest-tmp
```

Ожидается:

```text
2 passed
```

## Интерактивный скрипт

В `run_agent_with_approval.py` замени:

```python
require_approval=True
```

на:

```python
approval_policy_enabled=True
```

На текущем fixture действия `fill Task` и `click Add` считаются безопасными,
поэтому interrupt может не возникнуть. Для ручной проверки рискованной ветки
нужна страница или test case с кнопкой `Delete`, `Pay`, `Submit` и т.п.

## Ограничения keyword policy

Keyword rules могут:

- пропустить опасную кнопку с необычным названием;
- остановить безопасную кнопку с совпавшим словом;
- не понять контекст страницы;
- не учитывать домен и права пользователя.

Production policy обычно комбинирует:

```text
тип tool/action
target semantics
domain allowlist
данные поля
роль пользователя
стоимость/необратимость
организационные правила
```

Но даже простая детерминированная policy лучше, чем решение самой LLM о том,
нужно ли проверять её действие.

## Полная проверка

```powershell
python -m pytest -q --basetemp=.pytest-tmp
```

Ожидается:

```text
128 passed
```

## Самопроверка

1. Почему Planner не должен сам решать, требуется ли approval?
2. Почему решение policy хранится моделью, а не только boolean?
3. Чем режим `all` отличается от `risky`?
4. Почему policy node находится между Planner и Executor?
5. Какие ошибки возможны у keyword policy?

## Дальше

Следующий урок — Evaluation: datasets, метрики и измеримое сравнение качества
Planner, Judge и полного агента.
