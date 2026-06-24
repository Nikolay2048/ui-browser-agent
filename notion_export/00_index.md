# AI Agent Engineering Notes

Эта папка подготовлена как Notion-friendly база знаний по разработке AI-агентов.

Она основана на проекте `UiBrowserAgent`, но не ограничивается им. Здесь собраны
принципы, паттерны, ошибки и практические заготовки, которые можно переносить в
новые проекты.

## Как пользоваться

Импортируй папку в Notion как Markdown или копируй файлы по одному.

Рекомендуемый порядок чтения:

1. [01_ai_agents_core_concepts.md](01_ai_agents_core_concepts.md)
2. [02_langgraph_practical_notes.md](02_langgraph_practical_notes.md)
3. [03_langchain_and_structured_output.md](03_langchain_and_structured_output.md)
4. [04_agent_architecture_decisions.md](04_agent_architecture_decisions.md)
5. [05_memory_feedback_and_rag.md](05_memory_feedback_and_rag.md)
6. [06_evaluation_and_observability.md](06_evaluation_and_observability.md)
7. [07_reusable_code_patterns.md](07_reusable_code_patterns.md)
8. [08_common_mistakes.md](08_common_mistakes.md)
9. [09_project_templates_and_checklists.md](09_project_templates_and_checklists.md)
10. [10_future_learning_roadmap.md](10_future_learning_roadmap.md)

## Главная мысль

AI-агент - это не просто LLM с большим prompt.

Надежная агентная система состоит из:

```text
clear task contract
state
planner
tools/executor
observation
control flow
memory
evaluation
observability
human feedback
safety boundaries
```

LLM - только один компонент. Инженерная надежность появляется вокруг нее.

## Формула хорошего AI-agent проекта

```text
Typed inputs
  -> Explicit state
  -> Small graph nodes
  -> Structured model outputs
  -> Deterministic tools
  -> Independent verification
  -> Traceable persistence
  -> Evaluation
  -> Feedback loop
```

## Что переносить в новые проекты

- Начинай с Pydantic-контрактов.
- Не давай LLM выполнять side effects напрямую.
- Разделяй Planner / Executor / Judge.
- Используй structured output.
- Храни route и evidence.
- Делай deterministic evaluation до сложного RAG.
- Feedback сохраняй как данные, а не только как изменения prompt.
- Все внешние зависимости передавай через dependency injection.
- Отделяй runtime artifacts от reproducible examples.
- Пиши документацию архитектурных решений.

## Мини-словарь

| Термин | Коротко |
|---|---|
| Agent | Система, которая наблюдает, принимает решение и действует в среде |
| State | Рабочая память одного запуска |
| Node | Одна операция графа, возвращающая update state |
| Router | Детерминированный выбор следующего узла |
| Tool | Ограниченное действие во внешнем мире |
| Planner | Компонент, выбирающий следующий шаг |
| Executor | Компонент, выполняющий действие |
| Judge | Независимая проверка результата |
| Memory | Данные из прошлого, влияющие на будущие решения |
| Retrieval | Выбор релевантной части памяти |
| Feedback | Человеческая коррекция поведения системы |
| Evaluation | Измерение качества поведения |
| Observability | Возможность понять, что произошло внутри запуска |
