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
└── graph.py
```

В каждый момент развивается только один граф:

```text
src/browser_agent/graph.py
```

Завершенные учебные этапы находятся в [`learning/`](learning/README.md). Их не
нужно изменять при выполнении новых заданий.

## Текущее задание

Урок 10: [автономный цикл](learning/lesson_10_autonomous_loop/README.md).

Нужно реализовать в `src/browser_agent/graph.py`:

- `route_planned_action`;
- `route_after_execution`;
- `build_agent_graph`.

Целевой цикл:

```text
observe → plan → execute → observe
```

Он завершается при:

- действии `finish`;
- ошибке browser action;
- достижении `max_steps`.

## Проверка

Только актуальный агент:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Тесты прошлых уроков по умолчанию не запускаются.

## Стек

- Pydantic — контракты данных;
- LangChain — prompt, LLM и structured output;
- LangGraph — состояние, переходы и цикл;
- Playwright — браузерный adapter на следующем этапе;
- Ollama `qwen3.5:35b` — локальная модель.
