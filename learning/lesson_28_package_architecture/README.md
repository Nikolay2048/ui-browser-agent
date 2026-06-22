# Урок 28. Production package architecture

## Цель

Проект вырос из нескольких файлов до системы с domain-моделями, четырьмя
LLM-ролями, workflow, persistence, reporting и evaluation.

Плоская структура пока работает:

```text
browser_agent/
├── models.py
├── planner.py
├── judge.py
├── graph.py
├── reporting.py
├── planner_evaluation.py
└── judge_evaluation.py
```

Но дальнейшее добавление RAG, reliability и end-to-end evaluation сделает
владение компонентами неочевидным.

В этом уроке мы не переносим весь проект. Осваиваем безопасный migration
pattern на двух границах:

```text
domain/
evaluation/
```

## Почему не переносим всё сразу

Mass refactor изменил бы десятки импортов одновременно:

```text
models
state
agents
workflow
browser
reporting
scripts
tests
```

Если тест упадёт, будет трудно определить причину. Production-рефакторинг
делают небольшими шагами:

```text
выбрать границу
→ создать новый public API
→ переместить implementation
→ оставить compatibility shim
→ обновить consumers
→ удалить shim позднее
```

## Целевая структура этого урока

```text
browser_agent/
├── domain/
│   ├── __init__.py
│   └── models.py
├── evaluation/
│   ├── __init__.py
│   ├── planner.py
│   └── judge.py
├── models.py               # compatibility shim
├── planner_evaluation.py   # compatibility shim
└── judge_evaluation.py     # compatibility shim
```

## Source of truth

После миграции определения должны физически находиться в новых модулях:

```python
TestCase.__module__ == "browser_agent.domain.models"
```

Если новый модуль только импортирует старый:

```python
from browser_agent.models import TestCase
```

то класс остаётся принадлежащим старому модулю:

```python
TestCase.__module__ == "browser_agent.models"
```

Это bridge, но ещё не завершённая миграция.

## Identity типов

Нельзя создать копию класса:

```python
# old models.py
class TestCase(BaseModel): ...

# new domain/models.py
class TestCase(BaseModel): ...
```

Это два разных Python-типа:

```python
old.TestCase is new.TestCase  # False
```

Объекты могут выглядеть одинаково, но `isinstance`, schema registration и
structured output будут работать с разными классами.

Правильно:

```python
# domain/models.py
class TestCase(BaseModel): ...

# models.py
from browser_agent.domain.models import TestCase
```

Тогда:

```python
old.TestCase is new.TestCase  # True
```

## Compatibility shim

Shim — временный модуль, сохраняющий старый import path:

```python
"""Backward-compatible imports. Use browser_agent.domain instead."""

from browser_agent.domain.models import (
    TestCase,
    BrowserAction,
    ...
)

__all__ = [
    "TestCase",
    "BrowserAction",
    ...
]
```

Зачем:

- старые consumers не ломаются сразу;
- миграция может быть поэтапной;
- rollback проще;
- тесты отделяют перенос от изменения поведения.

Shim не должен содержать бизнес-логику.

## `__init__.py` как public API

Пользователь пакета не обязан знать внутренний файл:

```python
from browser_agent.domain.models import TestCase
```

Можно дать более стабильный API:

```python
from browser_agent.domain import TestCase
```

`domain/__init__.py`:

```python
from browser_agent.domain.models import (
    BrowserAction,
    BrowserTarget,
    TestCase,
)

__all__ = [
    "BrowserAction",
    "BrowserTarget",
    "TestCase",
]
```

В `__all__` помещают только поддерживаемый публичный контракт, а не каждый
служебный импорт модуля.

## Направление зависимостей

Желаемое правило:

```text
domain ничего не знает о других слоях
agents зависят от domain
workflow зависит от agents и domain
infrastructure реализует внешние адаптеры
application собирает систему
evaluation вызывает production components
```

Недопустимо:

```text
domain -> LangGraph
domain -> Playwright
domain -> LangSmith
```

Domain-модели должны оставаться обычными Pydantic-контрактами.

## Задание 28.1. Перенос domain models

1. Перенеси содержимое старого `models.py` в:

```text
src/browser_agent/domain/models.py
```

2. Не копируй определения. Новый файл становится единственным source of truth.
3. Замени старый `models.py` на compatibility shim с явными импортами.
4. Добавь `__all__` в новый модуль.
5. Экспортируй основные модели из `domain/__init__.py`.

Минимальный public API `domain` должен включать все модели, которые сейчас
импортируются рабочим кодом и тестами.

Проверка:

```powershell
python -m pytest tests\test_package_architecture.py -q --basetemp=.pytest-tmp
```

После 28.1 должны пройти первые два теста.

## Задание 28.2. Обновление внутренних импортов

В runtime-коде замени:

```python
from browser_agent.models import ...
```

на:

```python
from browser_agent.domain import ...
```

или, для большого списка:

```python
from browser_agent.domain.models import ...
```

Compatibility shim нужен внешним и архивным consumers, но новый production-код
не должен продолжать зависеть от legacy path.

Найти оставшиеся импорты:

```powershell
rg "from browser_agent\.models" src\browser_agent
```

Допустимым результатом должен остаться только сам shim, если он использует этот
текст в docstring, либо ни одной строки.

После шага запусти полный `pytest`.

## Задание 28.3. Перенос Planner evaluation

Перенеси implementation:

```text
planner_evaluation.py
→ evaluation/planner.py
```

Старый файл преврати в shim:

```python
from browser_agent.evaluation.planner import (
    PlannerActionScore,
    PlannerEvaluationCase,
    PlannerEvaluationSummary,
    evaluate_planner_case,
    make_planner_target,
    planner_action_evaluator,
    score_planner_action,
    summarize_planner_scores,
)
```

Не оставляй две копии scorer-ов.

## Задание 28.4. Перенос Judge evaluation

Аналогично:

```text
judge_evaluation.py
→ evaluation/judge.py
```

Старый модуль становится shim.

## Задание 28.5. Evaluation public API

В `evaluation/__init__.py` экспортируй:

```python
PlannerEvaluationCase
JudgeEvaluationCase
```

и основные функции scorer/summary/target.

Scripts переведи на новые импорты:

```python
from browser_agent.evaluation.planner import ...
from browser_agent.evaluation.judge import ...
```

## Почему tests могут оставаться на legacy imports

Часть существующих тестов импортирует:

```python
browser_agent.models
```

Это полезная проверка compatibility shim. Новые тесты должны использовать новый
public API.

Так мы одновременно доказываем:

```text
новый путь работает
старый путь пока не сломан
оба пути возвращают тот же объект
```

## Задание 28.6. Удаление устаревшей точки входа

Проверь `src/main.py`. Это старый эксперимент, который:

- выполняется при импорте;
- создаёт `browser=None`;
- использует неправильный import path;
- дублирует scripts.

Удалить его безопаснее, чем поддерживать ложную точку входа.

`src/graph.png` также является сгенерированным артефактом. Перемести генерацию в
`artifacts/` или удали файл из source tree.

## Проверка

Архитектурные тесты:

```powershell
python -m pytest tests\test_package_architecture.py -q --basetemp=.pytest-tmp
```

Ожидается:

```text
5 passed
```

Полная проверка:

```powershell
python -m pytest -q --basetemp=.pytest-tmp
```

Ожидается:

```text
152 passed
```

Локальные evaluation после переноса:

```powershell
python scripts\evaluate_planner.py
python scripts\evaluate_judge.py
```

## Что пока не переносим

В этом уроке не создавай пустые подпакеты ради структуры:

```text
agents/
workflow/
infrastructure/
application/
```

Мы выделим их, когда появится практическая причина и сможем мигрировать один
слой за раз. Пустая архитектура не создаёт границ автоматически.

## Самопроверка

1. Что такое source of truth?
2. Почему нельзя скопировать Pydantic-классы в новый модуль?
3. Что проверяет identity через `is`?
4. Зачем нужен compatibility shim?
5. Чем internal module отличается от public API package?
6. Почему domain не должен импортировать LangGraph?
7. Почему массовый перенос всех файлов рискованнее поэтапной миграции?

## Следующий урок

После рефакторинга построим end-to-end evaluation полного агента, используя уже
разделённый пакет `evaluation`.
