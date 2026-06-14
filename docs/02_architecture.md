# Архитектура системы

## Граф LangGraph

Система построена на **LangGraph StateGraph** — направленном графе, где каждый узел — это агент или действие. Состояние передаётся между узлами через `AgentState`.

```
START
  │
  ▼
[planner]            ← Читает тест-кейс, создаёт ExecutionPlan
  │
  ▼
[execute_step] ◄─┐   ← Выполняет одно PlannedAction через ReAct-цикл
  │              │
  │  ещё есть    │
  ├─ действия ───┘
  │
  │  все выполнены
  ▼
[observer]           ← Анализирует результаты, находит баги
  │
  ▼
[test_generator]     ← Генерирует pytest-тест по пройденным шагам
  │
  ▼
[allure_reporter]    ← Записывает JSON-результаты в allure-results/
  │
  ▼
END
```

### Условная маршрутизация

После каждого вызова `execute_step` функция `_route_after_step` проверяет:
- Если `current_step_index < len(planned_actions)` → возврат в `execute_step`
- Иначе → переход к `observer`

Это реализует **цикл выполнения шагов** без рекурсии.

## Состояние (AgentState)

Все данные передаются через единый TypedDict:

```python
class AgentState(TypedDict):
    test_case: TestCase              # Исходный тест-кейс из YAML
    execution_plan: ExecutionPlan    # План от планировщика
    current_step_index: int          # Индекс текущего шага
    step_results: list[StepResult]  # Накопленные результаты (merge)
    bugs: list[BugReport]           # Найденные баги (merge)
    messages: list                   # История LLM-сообщений
    generated_test_code: str         # Сгенерированный pytest-код
    overall_status: str              # passed | failed | broken
    clarification: ClarificationRequest | None
    plan_reasoning: str              # Рассуждения планировщика
    analysis_reasoning: str          # Рассуждения наблюдателя
    error: str | None
```

Поля `step_results` и `bugs` используют **Annotated merge-reducer** — при каждом вызове `execute_step` новый `StepResult` добавляется в список, а не перезаписывает его.

## Модели данных

```
TestCase
  ├── id: str
  ├── name: str
  ├── start_url: str
  ├── severity: critical|high|medium|low
  ├── tags: list[str]
  └── steps: list[TestStep]
            ├── step_number: int
            ├── step: str          ← естественный язык
            └── expected: str      ← ожидаемый результат

ExecutionPlan
  ├── test_case_id: str
  ├── reasoning: str               ← объяснение стратегии планировщика
  └── planned_actions: list[PlannedAction]
            ├── step_number: int
            ├── description: str
            ├── tool_name: str     ← какой инструмент использовать
            ├── tool_args: dict    ← аргументы инструмента
            └── expected_result: str

StepResult
  ├── step_number: int
  ├── status: passed|failed|broken
  ├── actual_result: str
  ├── expected_result: str
  ├── screenshot_path: str | None
  ├── duration_ms: int
  └── tool_calls: list[str]       ← лог вызовов инструментов

BugReport
  ├── id: str (uuid)
  ├── title: str
  ├── severity: critical|high|medium|low
  ├── type: Functional|UI|UX|Performance
  ├── description: str
  ├── steps_to_reproduce: list[str]
  ├── expected_result: str
  ├── actual_result: str
  └── screenshots: list[str]
```

## Управление браузером (BrowserManager)

`BrowserManager` — **синглтон**, который хранит единственный экземпляр браузера на время выполнения одного тест-кейса.

```python
BrowserManager.get_instance()  # создаёт или возвращает экземпляр
browser.start(headless=False)  # запускает Chromium с slow_mo=150ms
browser.stop()                 # закрывает браузер
BrowserManager._instance = None  # сброс между тест-кейсами
```

Специальное поле `_last_step_result: dict | None` используется для передачи результата из инструмента `mark_step_complete` обратно в executor без усложнения сигнатур.

## Жизненный цикл одного тест-кейса

```
1. run_tests.py загружает YAML → TestCase
2. BrowserManager.start() — открывается Chrome
3. graph.invoke(initial_state) — запуск графа
4. planner_node:
     - LLM читает TestCase
     - Возвращает ExecutionPlan с N planned_actions
5. execute_step (повторяется N раз):
     - LLM получает одно PlannedAction
     - ReAct-цикл: LLM → tool → LLM → tool → ... → mark_step_complete
     - Записывает StepResult в state["step_results"]
6. observer_node:
     - LLM анализирует все StepResult
     - Возвращает bugs + clarification + status
7. test_generator_node:
     - LLM генерирует pytest-код по пройденным шагам
     - Сохраняет в generated_tests/test_{id}.py
8. allure_reporter (_allure_node):
     - Записывает {uuid}-result.json в allure-results/
     - Отдельный result.json на каждый баг [BUG-HIGH]
9. BrowserManager.stop() + _instance = None
```
