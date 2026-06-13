# Урок 5. Первый LLM-компонент

## Что мы строим

Впервые подключаем LLM, но не браузер.

Planner получает:

- цель тест-кейса;
- тестовые данные;
- ожидаемый результат;
- текстовый snapshot страницы.

И возвращает ровно одно действие:

```python
BrowserAction(
    action="fill",
    target="label=Username",
    value="standard_user",
    reason="The login form requires a username.",
)
```

Planner не выполняет действие и не решает, завершился ли весь сценарий.

```text
TestCase + page snapshot
          |
          v
       Planner (LLM)
          |
          v
    BrowserAction
```

## Почему structured output обязателен

Без схемы LLM может вернуть обычный текст:

```text
I think we should fill in the username field.
```

Приложение не знает надежно:

- какое действие выполнять;
- где находится target;
- какое значение вводить;
- валиден ли тип действия.

LangChain может потребовать результат в формате Pydantic-модели:

```python
structured_model = model.with_structured_output(BrowserAction)
```

Тогда результат проходит через контракт первого урока.

## Три слоя LangChain

На этом уроке цепочка состоит из двух реальных стадий:

```text
input dict
  -> ChatPromptTemplate
  -> structured model
  -> BrowserAction
```

### Prompt template

Шаблон превращает входные переменные в сообщения:

```python
{
    "goal": "...",
    "test_data": "...",
    "expected": "...",
    "page_snapshot": "...",
}
```

### Chat model

`ChatOllama` отправляет сообщения локальной Ollama.

### Structured output

`with_structured_output(BrowserAction)` требует результат, соответствующий
Pydantic-схеме.

## Зачем передавать model аргументом

Не создавайте `ChatOllama` внутри `plan_next_action`.

Плохо:

```python
def plan_next_action(...):
    model = ChatOllama(...)
```

Такой код:

- трудно тестировать;
- привязан к одной модели;
- создает конфигурацию при каждом вызове;
- требует реальную Ollama даже в unit-тестах.

Лучше:

```python
def plan_next_action(model, test_case, page_snapshot):
```

В production передаем `ChatOllama`, в тесте — `FakeStructuredModel`.
Это dependency injection.

## Задание 5.1: system prompt

В `src/browser_agent/planner.py` заполните `SYSTEM_PROMPT`.

Он должен сообщать модели:

1. Она является planner браузерного тестирования.
2. Нужно выбрать только одно следующее действие.
3. Нельзя придумывать элементы, которых нет в snapshot.
4. Нужно использовать данные из test case.
5. Возвращаемое действие будет проверено схемой `BrowserAction`.

Не пишите огромный prompt. Сейчас достаточно 5–10 четких строк.

## Задание 5.2: prompt template

Импортируйте:

```python
from langchain_core.prompts import ChatPromptTemplate
```

Реализуйте:

```python
def build_planner_prompt() -> ChatPromptTemplate:
```

Используйте:

```python
ChatPromptTemplate.from_messages(...)
```

Первое сообщение:

```python
("system", SYSTEM_PROMPT)
```

В human-сообщении должны использоваться переменные:

- `{goal}`;
- `{test_data}`;
- `{expected}`;
- `{page_snapshot}`.

Пример структуры, не готовый обязательный текст:

```text
Goal:
{goal}

Test data:
{test_data}

Expected results:
{expected}

Current page:
{page_snapshot}
```

## Задание 5.3: chain

```python
def build_planner_chain(model):
```

Шаги:

1. Создать prompt.
2. Получить structured model:

```python
model.with_structured_output(BrowserAction)
```

3. Соединить их оператором `|`.

Оператор:

```python
prompt | structured_model
```

означает: результат prompt передать модели.

## Задание 5.4: invocation

```python
def plan_next_action(model, test_case, page_snapshot) -> BrowserAction:
```

Создайте chain и вызовите:

```python
chain.invoke({...})
```

Передайте:

```python
{
    "goal": test_case.goal,
    "test_data": test_case.test_data,
    "expected": test_case.expected,
    "page_snapshot": page_snapshot,
}
```

Верните результат `invoke()`.

Не преобразовывайте результат обратно в `dict`: нам нужен `BrowserAction`.

## Как работают unit-тесты без Ollama

В тестах используется `FakeStructuredModel`.

Он:

1. запоминает переданную схему;
2. получает отрендеренный prompt;
3. возвращает заранее подготовленный `BrowserAction`.

Таким образом unit-тест проверяет нашу композицию, не качество реальной модели.

Это принципиальное разделение:

- unit-тест проверяет наш код;
- smoke-test проверяет интеграцию с Ollama;
- evaluation позже измерит качество решений модели.

## Проверка unit-тестов

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_planner.py -q
```

Итог всех тестов:

```text
27 passed
```

## Ручная проверка Ollama

После прохождения тестов:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_planner.py
```

Ожидается JSON примерно такого вида:

```json
{
  "action": "fill",
  "target": "textbox \"Username\"",
  "value": "standard_user",
  "reason": "..."
}
```

Конкретный target и reason могут отличаться. Важнее:

- результат является `BrowserAction`;
- действие соответствует странице и цели;
- модель не возвращает свободный текст.

## Что нужно понять

После урока будьте готовы объяснить:

1. Чем prompt отличается от model.
2. Что делает оператор `|`.
3. Зачем нужен `with_structured_output`.
4. Почему модель передается аргументом.
5. Почему unit-тест не должен зависеть от Ollama.
