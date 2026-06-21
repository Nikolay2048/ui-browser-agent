# Browser Testing Agent

Учебный проект по разработке агентной системы для автоматического тестирования
веб-сайтов.

## Где работать

Актуальный код:

```text
src/browser_agent/
├── models.py
├── state.py
├── planner.py
├── observer.py
├── executor.py
├── browser.py
├── graph.py
└── runner.py
```

В каждый момент развивается только один граф:

```text
src/browser_agent/graph.py
```

Завершенные учебные этапы находятся в [`learning/`](learning/README.md). Их не
нужно изменять при выполнении новых заданий.

## Текущее задание

Урок 25: [Policy-based approval](learning/lesson_25_approval_policy/README.md).

Нужно:

- оценивать риск BrowserAction детерминированной policy;
- автоматически выполнять безопасные действия;
- запрашивать человека только для рискованных действий;
- сохранить решение policy в AgentState и LangSmith trace.

После прохождения тестов:

```powershell
python scripts\run_real_agent.py
```

## Проверка

Только актуальный агент:

```powershell
python -m pytest -q
```

Тесты прошлых уроков по умолчанию не запускаются.

## Стек

- Pydantic — контракты данных;
- LangChain — prompt, LLM и structured output;
- LangGraph — состояние, переходы и цикл;
- Playwright — управление настоящим браузером;
- Ollama `qwen3.5:35b` — локальная модель.
