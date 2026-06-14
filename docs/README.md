# Документация AI Website Testing Agent

## Содержание

| Файл | Описание |
|------|----------|
| [01_overview.md](01_overview.md) | Что это, зачем, стек технологий, быстрый старт |
| [02_architecture.md](02_architecture.md) | Граф LangGraph, состояние, модели данных, жизненный цикл |
| [03_agents.md](03_agents.md) | Четыре агента: Planner, Executor, Observer, TestGenerator |
| [04_tools.md](04_tools.md) | 17 инструментов браузера: описание, приоритеты, примеры |
| [05_test_cases.md](05_test_cases.md) | Формат YAML, принципы написания, все текущие кейсы |
| [06_reporting.md](06_reporting.md) | Allure-отчёт, LangSmith, скриншоты, сгенерированные тесты |
| [07_configuration.md](07_configuration.md) | .env, модели Ollama, структура директорий |
| [08_running.md](08_running.md) | Команды запуска, типичное время, отладка |

## Схема системы одной картинкой

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Website Testing Agent                      │
│                                                                  │
│   test_cases/tc_01.yaml  (естественный язык на русском)         │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────┐   ExecutionPlan    ┌─────────────────────────┐   │
│   │ Planner  │ ────────────────►  │   execute_step (loop)   │   │
│   │qwen3.5   │                   │                          │   │
│   └──────────┘                   │  LLM ◄──► Browser Tools  │   │
│                                   │  (ReAct pattern)         │   │
│                                   │                          │   │
│                                   │  get_page_context()      │   │
│                                   │  click_by_role()         │   │
│                                   │  fill_by_label()         │   │
│                                   │  verify_text_visible()   │   │
│                                   │  mark_step_complete()    │   │
│                                   └──────────┬──────────────┘   │
│                                              │ StepResult[]      │
│                                              ▼                   │
│   ┌──────────────┐              ┌────────────────────┐          │
│   │ TestGenerator│              │      Observer      │          │
│   │qwen2.5-coder │◄────────────│     qwen3.5        │          │
│   └──────┬───────┘              └────────┬───────────┘          │
│          │ pytest code                   │ bugs[] + status       │
│          ▼                               ▼                       │
│   generated_tests/              ┌─────────────────┐             │
│   test_tc_01.py                 │ Allure Reporter  │             │
│                                  └────────┬────────┘             │
│                                           │                      │
│                                  allure-results/                 │
│                                  ├── *-result.json  (тест)      │
│                                  ├── *-result.json  (каждый баг)│
│                                  ├── *.png          (скриншоты) │
│                                  ├── *.md  (рассуждения агентов)│
│                                  └── *.py  (сгенерированный тест)│
└─────────────────────────────────────────────────────────────────┘
```
