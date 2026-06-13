# Урок 7. Детерминированный executor

## Где мы находимся

Planner уже умеет предложить действие:

```python
BrowserAction(
    action="fill",
    target="label=Username",
    value="standard_user",
    reason="Username is required.",
)
```

Но предложение LLM само ничего не меняет на странице.

Нужен отдельный executor:

```text
BrowserAction -> executor -> browser adapter -> ActionResult
```

Главный архитектурный принцип:

> LLM принимает смысловое решение, а обычный код выполняет ограниченную
> команду.

LLM не должна получать произвольный доступ к Playwright `Page`. Иначе она сможет
генерировать любой код, а маршрут станет сложнее контролировать и тестировать.

## Разделение ответственности

### Planner

Отвечает:

```text
Какое действие следует выполнить?
```

### Executor

Отвечает:

```text
Как безопасно выполнить известный тип действия?
```

### Browser adapter

Скрывает конкретную реализацию браузера:

```python
browser.click(target)
browser.fill(target, value)
browser.press(target, key)
browser.assert_text(target)
browser.screenshot()
```

Пока это fake browser. Позже создадим Playwright adapter с таким же интерфейсом.

## Почему adapter полезен

Если executor напрямую импортирует Playwright:

```python
def execute_action(page, action):
    page.get_by_text(...).click()
```

unit-тесту потребуется настоящий браузер.

С adapter тест подставляет:

```python
class FakeBrowser:
    def click(self, target):
        self.calls.append(("click", target))
```

Executor не знает, fake это или Playwright. Он знает только нужные методы.

Это dependency inversion:

```text
высокоуровневый executor зависит от интерфейса,
а не от конкретного Playwright
```

В Python интерфейс пока не объявлен формально. Используем duck typing:

> Если объект имеет нужные методы и ведет себя как browser adapter, он подходит.

Позже можно добавить `Protocol`.

## `execute_action`

Функция получает:

```python
browser
action: BrowserAction
```

И возвращает:

```python
ActionResult
```

Она не является LangGraph node. Это обычная доменная функция, которую можно
вызвать отдельно.

## Dispatch

Dispatch — выбор реализации по типу команды.

Простой вариант:

```python
if action.action == BrowserActionType.CLICK:
    browser.click(action.target)
elif action.action == BrowserActionType.FILL:
    browser.fill(action.target, action.value)
```

Можно использовать `match`, но `if/elif` сейчас проще.

Поддержите:

- `click`;
- `fill`;
- `press`;
- `assert_text`;
- `finish`.

Для `finish` browser-метод вызывать не нужно. Это управляющая команда, а не
действие страницы.

Однако в этом уроке `finish` может вернуть успешный `ActionResult`, чтобы
dispatch был полным. Позже router будет перехватывать `finish` до executor.

## Сбор URL и screenshot

До действия сохраните:

```python
url_before = browser.current_url
```

После действия:

```python
url_after = browser.current_url
screenshot_path = browser.screenshot()
```

Успешный результат:

```python
ActionResult(
    success=True,
    url_before=url_before,
    url_after=url_after,
    error=None,
    screenshot_path=screenshot_path,
)
```

## Обработка ошибки

Browser adapter может выбросить исключение:

```python
RuntimeError("Element not found")
```

На этом уровне мы не хотим останавливать весь Python-процесс. Ошибка действия
является ожидаемой частью работы агента.

Executor преобразует исключение в данные:

```python
ActionResult(
    success=False,
    url_before=url_before,
    url_after=browser.current_url,
    error=str(error),
    screenshot_path=browser.screenshot(),
)
```

Это называется error as data:

```text
exception -> ActionResult(success=False)
```

Тогда будущий Judge сможет решить:

- повторить действие;
- попросить planner выбрать другой target;
- завершить сценарий;
- записать automation error.

## Важный вопрос о screenshot

Screenshot нужен и после успеха, и после ошибки.

При ошибке он особенно полезен: показывает, что реально видел пользователь.

Для простоты урока предполагаем, что `screenshot()` работает. В production его
ошибку придется обрабатывать отдельно, чтобы ошибка evidence не скрыла исходную
ошибку действия.

## Задание 7.1: `execute_action`

Работайте в `src/browser_agent/executor.py`.

Импортируйте:

```python
from browser_agent.models import (
    ActionResult,
    BrowserAction,
    BrowserActionType,
)
```

Алгоритм:

1. Сохранить `url_before`.
2. В `try` выбрать browser-метод по `action.action`.
3. После действия сделать screenshot.
4. Вернуть успешный `ActionResult`.
5. В `except Exception as error` сделать screenshot и вернуть неуспешный
   `ActionResult`.

Pydantic validator уже гарантирует наличие `target` и `value` для нужных типов.
Но статический анализатор пока может считать их `None`. Для учебного варианта
можно использовать проверки:

```python
assert action.target is not None
assert action.value is not None
```

`assert` здесь не бизнес-валидация. Она сообщает Python и читателю, что после
Pydantic-контракта значение ожидается.

## Задание 7.2: node factory

Executor требует browser dependency, поэтому снова используем closure:

```python
def make_execute_node(browser):
    def execute(state: AgentState) -> dict:
        result = execute_action(
            browser=browser,
            action=state["proposed_action"],
        )

        return {
            "last_result": result,
            "step_count": state["step_count"] + 1,
        }

    return execute
```

Обратите внимание:

- node берет действие из state;
- обычная функция `execute_action` выполняет работу;
- node сохраняет результат обратно в state;
- счетчик увеличивается только после попытки исполнения;
- node возвращает partial update.

## Почему `last_result`, а не сразу `route`

Пока сохраняем только последний результат:

```python
last_result: ActionResult
```

На следующем этапе изучим reducer, который позволит добавлять результаты в
список `route`, не перезаписывая его.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_executor.py -q
```

Итог всех тестов:

```text
32 passed
```

## Что нужно понять

После урока объясните:

1. Почему planner не выполняет действие самостоятельно.
2. Что такое dispatch.
3. Зачем нужен browser adapter.
4. Почему исключение преобразуется в `ActionResult`.
5. Чем `execute_action` отличается от `execute` node.
6. Почему browser передается через closure.
