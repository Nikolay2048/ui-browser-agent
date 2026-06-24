# Browser Testing Agent Knowledge Base

Эта папка фиксирует итоговую базу знаний по проекту `UiBrowserAgent`.

Проект разрабатывался как учебная система: наставник давал теорию, задания,
архитектурные объяснения и контрактные тесты; ученик самостоятельно писал код,
запускал тесты, отлаживал ошибки и постепенно собирал полноценного UI-агента.

## Как читать документацию

1. [project-history.md](project-history.md)  
   История обучения: как проект развивался от Pydantic-моделей до feedback
   memory.

2. [architecture.md](architecture.md)  
   Итоговая архитектура проекта: компоненты, связи, поток данных, поток
   управления и LangGraph workflow.

3. [langgraph-agent-flow.md](langgraph-agent-flow.md)  
   Подробное устройство графа: state, nodes, routers, циклы, ограничения,
   failure path.

4. [concepts-and-decisions.md](concepts-and-decisions.md)  
   Справочник изученных концепций: что это, зачем нужно, как реализовано,
   альтернативы и типичные ошибки.

5. [memory-feedback-retrieval.md](memory-feedback-retrieval.md)  
   Память агента: AgentState, checkpointing, run history, human feedback,
   retrieval и memory context.

6. [evaluation-observability.md](evaluation-observability.md)  
   Тестирование и оценка: pytest, deterministic fakes, Planner/Judge/E2E
   evaluation, LangSmith, traces.

7. [runbook.md](runbook.md)  
   Практические команды: установка, запуск, demo run, feedback, artifacts,
   troubleshooting.

8. [code-review.md](code-review.md)  
   Senior review текущего состояния: сильные стороны, риски, техдолг,
   рекомендуемые улучшения.

9. [future-study-roadmap.md](future-study-roadmap.md)  
   Пробелы в обучении и темы для следующего этапа: RAG, memory evaluation,
   production hardening, multi-agent systems.

## Что получилось в v0.1

В проекте есть рабочий образовательный AI-агент для UI-тестирования:

- принимает `TestCase`;
- открывает web-страницу через Playwright;
- наблюдает accessibility snapshot;
- планирует следующее действие через LLM + structured output;
- выполняет действия через deterministic executor;
- записывает route выполнения;
- проверяет результат независимым Judge;
- классифицирует failed run;
- формирует структурированный bug report;
- сохраняет итоговый JSON/Markdown run report;
- сохраняет append-only run history;
- принимает human feedback через CLI;
- извлекает релевантный feedback и передает его в planner prompt.

## Принцип проекта

Проект специально построен не как "один большой агент", а как система
инженерных компонентов:

```text
Domain contracts
  -> Graph state
  -> LLM roles
  -> Deterministic tools
  -> Runner composition
  -> Persistence
  -> Evaluation
  -> Feedback memory
```

Это важный вывод обучения: надежная агентная система состоит не только из LLM.
Качество создается контрактами, графом, state, тестами, наблюдаемостью,
ограничениями, проверками и обратной связью.
