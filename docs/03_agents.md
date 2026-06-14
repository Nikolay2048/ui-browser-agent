# Агенты системы

Система состоит из четырёх агентов. Каждый — отдельный узел в LangGraph-графе.

---

## 1. Planner (Планировщик)

**Файл:** `src/testing_agent/agents/planner.py`  
**Модель:** `qwen3.5:35b` с `format="json"`  
**Вход:** `AgentState` с заполненным `test_case`  
**Выход:** `execution_plan`, `plan_reasoning`

### Что делает

Читает тест-кейс на русском языке и создаёт детальный `ExecutionPlan` — список конкретных действий с браузером (`PlannedAction`), которые нужно выполнить.

### Как работает

1. Система генерирует описание доступных инструментов **динамически** из `BROWSER_TOOLS` (не хардкод):
   ```python
   _TOOLS_LISTING = "\n".join(
       f"- {t.name}: {t.description.splitlines()[0]}"
       for t in BROWSER_TOOLS
   )
   ```
2. LLM получает тест-кейс и список инструментов, возвращает JSON.
3. Используется `ChatOllama(format="json")` — принудительный JSON-режим на уровне Ollama. Это надёжнее, чем `with_structured_output`, который ломается при нестандартном выводе модели.
4. JSON парсится через `_extract_json()` — сначала прямой `json.loads`, затем поиск `{}` с удалением `<think>` тегов qwen3.

### Стратегия в промпте

Промпт содержит только **правила поведения**, а не каталог инструментов:
- Первое действие всегда `navigate_to_url`
- Приоритет локаторов: `click_by_role > click_by_text > click_by_css`
- После смены страницы — `verify_text_visible`
- Последнее действие каждого шага — `mark_step_complete`

### Fallback

Если JSON не удалось распарсить — создаётся минимальный план:
- Первое действие: `navigate_to_url(start_url)`
- Одно действие `get_page_context` на каждый шаг тест-кейса
- Executor сам разбирается что делать, опираясь на описание шага

### Поле reasoning

Планировщик обязан заполнить поле `reasoning` — объяснение стратегии: почему выбраны конкретные локаторы, какие риски есть, как трактуются шаги. Это поле сохраняется в Allure как markdown-вложение «Рассуждения планировщика».

---

## 2. Executor (Исполнитель)

**Файл:** `src/testing_agent/agents/executor.py`  
**Модель:** `qwen3.5:35b` с `bind_tools(BROWSER_TOOLS)`  
**Вход:** одно `PlannedAction` из `execution_plan`  
**Выход:** один `StepResult`

### Что делает

Выполняет **одно** `PlannedAction` за вызов. Использует паттерн **ReAct** (Reason + Act): в цикле вызывает LLM, тот решает какой инструмент использовать, инструмент выполняется, результат передаётся обратно в LLM.

### ReAct-цикл

```python
for _ in range(MAX_STEP_ITERATIONS):  # обычно 20
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    for tool_call in response.tool_calls:
        result = _run_tool(tool_call)
        messages.append(ToolMessage(result, tool_call_id=...))

        if tool_call["name"] == "mark_step_complete":
            step_result = BrowserManager._last_step_result
            break  # шаг завершён
```

LLM сам решает:
- Какой инструмент вызвать следующим
- Как интерпретировать результат
- Когда считать шаг выполненным

### Завершение шага

Специальный инструмент `mark_step_complete(status, actual_result, screenshot_name)`:
- Сохраняет результат в `BrowserManager._last_step_result`
- Возвращает строку `STEP_COMPLETE::status::actual_result`
- Executor обнаруживает это и останавливает цикл

### Контекст для LLM

Каждый шаг LLM получает:
```
Execute step 3: Нажать кнопку Login
Expected result: Пользователь перенаправлен на /inventory.html

Test start URL: https://www.saucedemo.com/
Planner suggestion — tool: click_by_role, args: {"role": "button", "name": "Login"}
Start with get_page_context() first...
```

### Директива `/no_think`

В системном промпте executor стоит `/no_think` — специальная директива для моделей qwen3. Без неё модель генерирует длинные `<think>...</think>` блоки перед каждым вызовом инструмента, что замедляет работу и может сбивать с толку логику определения завершения шага.

### Сбой шага

Если за `MAX_STEP_ITERATIONS` итераций `mark_step_complete` не был вызван — шаг получает статус `broken` с сообщением «Step did not complete — max iterations reached».

---

## 3. Observer (Наблюдатель)

**Файл:** `src/testing_agent/agents/observer.py`  
**Модель:** `qwen3.5:35b` с `format="json"` (через `_JsonLLM`)  
**Вход:** все `StepResult` + исходный `TestCase`  
**Выход:** `bugs`, `clarification`, `overall_status`, `analysis_reasoning`

### Что делает

Анализирует результаты выполнения всех шагов и выдаёт два типа выводов:
1. **Баг-репорты** — реальные дефекты сайта
2. **Запросы уточнений** — вопросы по неоднозначным шагам тест-кейса

### Правила баг-репортов

Observer строго разделяет:

**Считается багом сайта:**
- Неверный текст сообщения об ошибке
- Отсутствует UI-элемент, который должен быть
- Редирект ведёт не туда
- Форма принимает невалидные данные
- Функциональность из expected result не работает

**НЕ считается багом:**
- Ошибки агентских инструментов
- Проблемы с LLM
- Медленная сеть
- Неоднозначные шаги тест-кейса

### Правила статуса

```
passed  — ВСЕ шаги passed И багов нет
failed  — один или более шагов failed (расхождение expected vs actual)
broken  — один или более шагов broken (ошибка выполнения / таймаут)
```

### Запросы уточнений (ClarificationRequest)

Observer флагует шаги, если:
- Действие неоднозначно (несколько элементов подходят)
- Expected result слишком расплывчатый («должно работать корректно»)
- Не хватает данных (нет учётных данных, значений)
- Пропущено предусловие (нужен вход, но не описан)
- Шаг можно разбить на более атомарные

Если тест-кейс написан чётко — `needs_clarification: false`.

### Поле reasoning

Observer обязан объяснить своё решение в поле `reasoning`:
- Почему он пришёл к данному статусу
- Что именно указывает на баг (или его отсутствие)
- Как он интерпретировал расхождения

Сохраняется в Allure как «Рассуждения аналитика (Observer)».

---

## 4. TestGenerator (Генератор тестов)

**Файл:** `src/testing_agent/agents/test_generator.py`  
**Модель:** `qwen2.5-coder:14b-instruct`  
**Вход:** пройденные `StepResult` + `TestCase`  
**Выход:** файл `generated_tests/test_{id}.py`

### Что делает

Генерирует готовый pytest-тест с Allure-разметкой на основе **реально выполненных** шагов. Использует `qwen2.5-coder` — специализированную модель для генерации кода.

### Что входит в промпт

- Название, описание и severity тест-кейса
- Для каждого пройденного шага: описание, вызванные инструменты, фактический результат

LLM сам решает, как перевести инструментальные вызовы агента в читаемый Playwright-код.

### Формат генерируемого теста

```python
import pytest
import allure
from playwright.sync_api import Page, expect

@allure.title("Успешный вход — стандартный пользователь")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc_01(page: Page) -> None:
    with allure.step("Перейти на страницу входа"):
        page.goto("https://www.saucedemo.com/")
        page.wait_for_load_state("domcontentloaded")

    with allure.step("Ввести учётные данные"):
        page.get_by_placeholder("Username").fill("standard_user")
        page.get_by_placeholder("Password").fill("secret_sauce")

    with allure.step("Нажать Login и проверить редирект"):
        page.get_by_role("button", name="Login").click()
        expect(page).to_have_url(re.compile(".*/inventory.html"))
```

### Fallback

Если ни один шаг не прошёл — генерируется заглушка с `pytest.skip()` и комментарием проверить Allure-отчёт.
