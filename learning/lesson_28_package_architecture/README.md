# Урок 28. Production package architecture

## Результат урока

Плоский пакет:

```text
browser_agent/
├── models.py
├── planner_evaluation.py
└── judge_evaluation.py
```

разделён по ответственности:

```text
browser_agent/
├── domain/
│   ├── __init__.py
│   └── models.py
└── evaluation/
    ├── __init__.py
    ├── planner.py
    ├── judge.py
    └── end_to_end.py
```

## Почему появилась новая структура

`domain` владеет стабильными бизнес-контрактами:

- `TestCase`;
- `BrowserAction`;
- `ExecutionStep`;
- `JudgeVerdict`;
- `RunTermination`;
- `BugReport`;
- `RunReport`.

`evaluation` владеет offline-кодом измерения качества:

- dataset contracts;
- scorers;
- summaries;
- LangSmith targets;
- LangSmith evaluators.

Evaluation вызывает production-компоненты, но production workflow не зависит от
evaluation.

## Source of truth

Каждый класс или scorer определяется только в одном модуле:

```python
TestCase.__module__ == "browser_agent.domain.models"
```

Нельзя копировать Pydantic-класс при переносе:

```python
old.TestCase is new.TestCase  # должно быть True во время миграции
```

Две одинаково выглядящие декларации всё равно являются разными Python-типами.

## Public API

`__init__.py` задаёт поддерживаемый путь:

```python
from browser_agent.domain import TestCase
from browser_agent.evaluation import PlannerEvaluationCase
```

Внутренний файл можно реорганизовать позже, не меняя imports consumers.

## Compatibility shims

Для публичной библиотеки миграцию обычно проводят поэтапно:

```text
новый source of truth
→ старый module становится shim
→ consumers переходят на новый API
→ deprecation period
→ shim удаляется в следующей major version
```

Наш проект является внутренним приложением, а все consumers находятся в одном
репозитории. Поэтому после обновления runtime, scripts, tests и учебных
Python-примеров временные shims были удалены сразу.

Удалены:

```text
browser_agent/models.py
browser_agent/planner_evaluation.py
browser_agent/judge_evaluation.py
```

## Направление зависимостей

```text
domain ничего не знает о LangGraph, Playwright и LangSmith
runtime agents зависят от domain
workflow зависит от agents и domain
evaluation вызывает production runtime
scripts собирают конкретные приложения и experiments
```

Недопустимо:

```text
domain -> workflow
domain -> Playwright
domain -> LangSmith
```

## Архитектурные тесты

Тесты проверяют:

- ownership классов через `__module__`;
- ownership scorer-функций;
- public API package initializers;
- отсутствие удалённых legacy-модулей.

```powershell
python -m pytest tests\test_package_architecture.py -q
```

## Удалённые артефакты

Также удалены:

- `src/main.py` — устаревшая точка входа с side effects при импорте;
- `src/graph.png` — сгенерированный файл внутри source tree.

Рабочие точки входа находятся в `scripts/`, артефакты должны сохраняться в
`artifacts/`.

## Что не переносили

Не создавались пустые подпакеты:

```text
agents/
workflow/
infrastructure/
application/
reporting/
```

Их следует выделять, когда конкретный слой становится достаточно большим.
Структура каталогов сама по себе не создаёт хорошую архитектуру.

## Итоговые принципы

1. Один source of truth.
2. Явный public API.
3. Зависимости направлены внутрь к domain.
4. Evaluation отделена от runtime.
5. Рефакторинг не меняет поведение.
6. Временные migration-механизмы удаляются после завершения миграции.
