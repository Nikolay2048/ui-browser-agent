# Урок 16. Типизированные browser targets

## Почему нужен этот урок

В реальных запусках мы увидели два класса ошибок:

```text
textbox[label=Task]
text="Learn AI Agents"
```

Обе строки прошли через Pydantic, потому что поле было объявлено так:

```python
target: str | None
```

Для Python это обычные строки. Но для нашего adapter-а они означают разные
вещи:

```text
text=Learn AI Agents     → найти текст Learn AI Agents
text="Learn AI Agents"   → найти текст "Learn AI Agents" вместе с кавычками
```

Проблема не только в prompt-е. Проблема в слишком слабом доменном контракте.

## Старый контракт

```python
BrowserAction(
    action="fill",
    target="label=Task",
    value="Learn AI Agents",
)
```

Это строковый мини-язык. Он компактный, но хрупкий:

- модель может поставить кавычки не там;
- модель может придумать новый синтаксис;
- Pydantic не понимает внутреннюю грамматику строки;
- adapter вынужден парсить строку;
- ошибки обнаруживаются поздно, уже во время действия в браузере.

## Новый контракт

```python
BrowserAction(
    action="fill",
    target=BrowserTarget(
        strategy="label",
        value="Task",
    ),
    value="Learn AI Agents",
)
```

Для role:

```python
BrowserTarget(
    strategy="role",
    value="button",
    name="Add",
)
```

Для text:

```python
BrowserTarget(
    strategy="text",
    value="Learn AI Agents",
)
```

Модель больше не генерирует mini-DSL. Она заполняет поля структуры.

## Tool arguments

В агентских системах лучше думать так:

```text
LLM выбирает инструмент и аргументы.
Приложение исполняет заранее написанный инструмент.
```

`BrowserAction` — это описание инструмента:

```python
action="fill"
target=...
value=...
```

`BrowserTarget` — это структурированный аргумент инструмента.

Мы не просим модель написать:

```text
page.get_by_label("Task").fill(...)
```

Мы просим модель вернуть данные:

```json
{
  "action": "fill",
  "target": {
    "strategy": "label",
    "value": "Task",
    "name": null
  },
  "value": "Learn AI Agents",
  "reason": "..."
}
```

## Стратегии target

Добавляем enum:

```python
class BrowserTargetStrategy(StrEnum):
    ROLE = "role"
    LABEL = "label"
    TEXT = "text"
    CSS = "css"
```

И модель:

```python
class BrowserTarget(BaseModel):
    strategy: BrowserTargetStrategy
    value: str = Field(min_length=1)
    name: str | None = None
```

Смысл полей:

| strategy | value | name |
|---|---|---|
| `role` | role, например `button` | accessible name, например `Add` |
| `label` | label text | всегда `None` |
| `text` | видимый текст | всегда `None` |
| `css` | CSS selector | всегда `None` |

## Инварианты

### `role` требует `name`

```python
BrowserTarget(strategy="role", value="button", name="Add")
```

Так можно точно получить:

```python
page.get_by_role("button", name="Add", exact=True)
```

Запрещаем:

```python
BrowserTarget(strategy="role", value="button")
```

Иначе target слишком расплывчатый.

### `label`, `text`, `css` не используют `name`

Запрещаем:

```python
BrowserTarget(strategy="label", value="Task", name="Unexpected")
```

Если поле не имеет смысла для стратегии, оно не должно быть заполнено.

### `text` не должен быть обёрнут в кавычки

Запрещаем:

```python
BrowserTarget(strategy="text", value='"Learn AI Agents"')
```

Нам нужен реальный текст:

```python
BrowserTarget(strategy="text", value="Learn AI Agents")
```

Это прямо закрывает ошибку Qwen.

## `__str__` для читаемой истории

История planner-а уже форматирует:

```python
f"target={step.action.target}"
```

Если target является объектом, без `__str__` получится шумное представление.

Добавим:

```python
def __str__(self) -> str:
    ...
```

Ожидаемые строки:

```text
role=button[name="Add"]
label=Task
text=Learn AI Agents
css=.todo-list li
```

Важно: `__str__` нужен для логов и prompt history. Adapter больше не должен
парсить эти строки.

## Adapter без парсинга

Было:

```python
if target.startswith("label="):
    ...
```

Станет:

```python
if target.strategy == BrowserTargetStrategy.LABEL:
    return self.page.get_by_label(target.value)
```

Adapter получает уже разобранный объект. Он не парсит строку, а просто
переводит enum в Playwright API.

## Prompt после миграции

Planner prompt должен объяснять не строковые targets, а объект:

```text
target must be an object.
```

Примеры:

```json
{"strategy": "role", "value": "button", "name": "Login"}
{"strategy": "label", "value": "Username", "name": null}
{"strategy": "text", "value": "Products", "name": null}
{"strategy": "css", "value": ".some-selector", "name": null}
```

Это важно для structured output: модель видит форму вложенного объекта.

## Что меняется по слоям

```text
models.py
  BrowserTarget
  BrowserAction.target

browser.py
  _resolve_target(BrowserTarget)

planner.py
  target object examples

tests
  fake models return BrowserTarget
```

Executor почти не меняется. Он продолжает передавать:

```python
browser.click(action.target)
```

Просто `action.target` теперь не строка, а `BrowserTarget`.

## Задание 16.1. BrowserTarget

Работай в:

```text
src/browser_agent/models.py
```

Реализуй `BrowserTarget`:

```python
class BrowserTarget(BaseModel):
    strategy: BrowserTargetStrategy
    value: str = Field(min_length=1)
    name: str | None = None
```

Добавь validator:

- `role` требует `name`;
- не-`role` запрещает `name`;
- `text` запрещает значение, которое начинается и заканчивается кавычками.

Добавь `__str__`.

Проверка:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_browser_targets.py tests\test_models.py -q
```

## Задание 16.2. PlaywrightBrowser

Работай в:

```text
src/browser_agent/browser.py
```

Импортируй:

```python
from browser_agent.models import BrowserTarget, BrowserTargetStrategy
```

Измени:

```python
def _resolve_target(self, target: BrowserTarget):
```

Если пришёл не `BrowserTarget`, выброси:

```python
TypeError("target must be BrowserTarget")
```

Сопоставление:

```python
ROLE  → page.get_by_role(target.value, name=target.name, exact=True)
LABEL → page.get_by_label(target.value)
TEXT  → page.get_by_text(target.value, exact=True)
CSS   → page.locator(target.value)
```

Проверка:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_browser.py -q
```

## Задание 16.3. Planner prompt

Работай в:

```text
src/browser_agent/planner.py
```

Замени старый string-target contract на object-target contract.

Prompt должен содержать:

```text
target must be an object
```

И JSON-примеры со стратегиями:

```text
"strategy": "role"
"strategy": "label"
"strategy": "text"
"strategy": "css"
```

Проверка:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_planner.py -q
```

## Задание 16.4. Остальные тесты

После моделей, adapter-а и prompt-а запусти:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Ожидается:

```text
59 passed
```

## Реальный запуск

После тестов:

```powershell
$env:OLLAMA_MODEL="gpt-oss:20b"
.\.venv\Scripts\python.exe scripts\run_real_agent.py
```

Смотри на `proposed_action.target`. Он должен быть вложенным объектом, а не
строкой.

## Что это даст

Ошибки вроде:

```text
text="Learn AI Agents"
textbox[label=Task]
```

будут отсечены до Playwright. Либо structured output не сможет создать
`BrowserAction`, либо Pydantic вернёт validation error.

Позже мы добавим recovery:

```text
invalid action → replan with validation error
```

Но сначала нужна строгая структура данных.

## Вопросы для самопроверки

1. Почему `target: str` был слишком слабым контрактом?
2. Чем `BrowserTarget` похож на аргументы tool calling?
3. Почему adapter больше не должен парсить строки?
4. Зачем `__str__`, если adapter работает с объектом?
5. Почему `role` требует `name`?
6. Почему `text` не должен содержать внешние кавычки?
7. Какой слой теперь ловит ошибку Qwen до Playwright?
