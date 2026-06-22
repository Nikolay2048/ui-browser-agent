# Browser Testing Agent

Учебный проект по разработке агентной системы для автоматического тестирования
веб-сайтов.

Система принимает `TestCase`, управляет браузером через Playwright, сохраняет
маршрут выполнения, проверяет ожидаемые результаты, классифицирует сбои и
формирует отчёт о запуске.

## Архитектура

Актуальный код:

```text
src/browser_agent/
├── domain/                # новый public API доменных контрактов
├── evaluation/            # новый public API offline evaluation
├── models.py              # временный compatibility path
├── state.py               # AgentState
├── graph.py               # LangGraph workflow
├── runner.py              # composition layer
├── planner.py             # выбор следующего действия
├── observer.py            # получение page snapshot
├── executor.py            # выполнение BrowserAction
├── browser.py             # Playwright adapter
├── judge.py               # проверка expected results
├── classifier.py          # классификация failed run
├── reporter.py            # создание BugReport
├── reporting.py           # RunReport, JSON и Markdown
├── approval.py            # interrupt/resume
├── approval_policy.py     # детерминированная risk policy
├── persistence.py         # thread config
├── observability.py       # LangSmith config
├── planner_evaluation.py  # compatibility path
└── judge_evaluation.py    # compatibility path
```

Подробная схема: [docs/architecture.md](docs/architecture.md).

## Основные команды

Установка проекта:

```powershell
python -m pip install -e ".[dev]"
playwright install chromium
```

Unit и integration tests:

```powershell
python -m pytest -q
```

Реальный автономный агент:

```powershell
python scripts\run_real_agent.py
```

Агент с human approval:

```powershell
python scripts\run_agent_with_approval.py
```

Локальная evaluation Planner:

```powershell
python scripts\evaluate_planner.py
```

Локальная evaluation Judge:

```powershell
python scripts\evaluate_judge.py
```

LangSmith experiment:

```powershell
python scripts\run_planner_experiment.py
```

## Конфигурация

Локальные значения хранятся в `.env`, который не добавляется в Git.
Поддерживаемые переменные приведены в [.env.example](.env.example).

Минимальный набор:

```text
OLLAMA_MODEL=qwen3.5:35b
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=ui-browser-agent-dev
```

## Текущий этап

Урок 28 завершён: [Production package architecture](learning/lesson_28_package_architecture/README.md).

Реализовано:

- `domain` стал source of truth для Pydantic-контрактов;
- `evaluation` владеет Planner/Judge evaluation;
- старые import paths сохранены через compatibility shims;
- production-код и scripts используют новые public API;
- удалены устаревшие `src/main.py` и `src/graph.png`;
- identity типов и функций защищена архитектурными тестами.

Следующий этап — end-to-end evaluation полного агента.

Завершённые учебные этапы находятся в [learning/](learning/README.md). Архивные
файлы не импортируются рабочим приложением и не входят в основной `pytest`.

## Стек

- Pydantic — контракты данных;
- LangChain — prompt, LLM и structured output;
- LangGraph — состояние, переходы и цикл;
- Playwright — управление настоящим браузером;
- Ollama `qwen3.5:35b` — локальная модель;
- LangSmith — traces, datasets и evaluation experiments;
- Jinja2 — Markdown-шаблон итогового отчёта.
