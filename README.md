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
├── domain/                # public API доменных контрактов
├── evaluation/            # component и end-to-end evaluation
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
├── run_history.py         # append-only history of completed runs
├── feedback.py            # human feedback records
├── feedback_cli.py        # CLI helpers for collecting feedback
├── feedback_retrieval.py  # deterministic retrieval over feedback records
├── approval.py            # interrupt/resume
├── approval_policy.py     # детерминированная risk policy
├── persistence.py         # thread config
└── observability.py       # LangSmith config
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

LangSmith experiments:

```powershell
python scripts\run_planner_experiment.py
python scripts\run_judge_experiment.py
```

## Demo Run

Run the local fixture with visible Chromium:

```powershell
python scripts\run_real_agent.py
```

Run the same agent with a committed feedback-memory example:

```powershell
python scripts\run_real_agent.py --feedback-path examples\feedback\first-real-agent.feedback.jsonl
```

Add your own local feedback after a run:

```powershell
python scripts\add_feedback.py `
  --run-id "manual-seed" `
  --test-case-id first-real-agent `
  --scope planner `
  --summary "Planner should use stable locator for the task input." `
  --correction 'For the task input, prefer label=Task.' `
  --tags planner,locator
```

Local runtime files are written to `artifacts/` and should not be committed.
Reusable demo inputs belong in `examples/`.

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

Текущий урок 37: [Runner feedback memory](learning/lesson_37_runner_feedback_memory/README.md).

Нужно подключить feedback memory к полному запуску агента: `run_agent()` должен
опционально принимать feedback store, доставать релевантные подсказки,
формировать `memory_context` и передавать его в LangGraph state.

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
