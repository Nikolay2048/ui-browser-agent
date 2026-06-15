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

Урок 15: [независимый Judge](learning/lesson_15_judge/README.md).

Нужно:

- создать структурированный `JudgeVerdict`;
- проверить каждый expected result по evidence;
- направлять planner `finish` в Judge, а не сразу в `passed`.

После прохождения тестов:

```powershell
.\.venv\Scripts\python.exe scripts\run_real_agent.py
```

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
- Playwright — управление настоящим браузером;
- Ollama `qwen3.5:35b` — локальная модель.
