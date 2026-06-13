# Урок 9. Observer: как агент видит окружение

## Почему нужен Observer

Предыдущий граф запускался так:

```python
graph.invoke({
    "test_case": test_case,
    "page_snapshot": '- textbox "Username"',
})
```

То есть внешний код заранее сообщал агенту, что находится на странице.

Настоящий агент должен самостоятельно получать наблюдение:

```text
browser -> observer -> page_snapshot -> planner
```

Новый граф:

```text
START
  -> initialize
  -> observe
  -> plan
  -> execute
  -> END
```

## Модель agent-environment loop

В теории агентов используются понятия:

- **environment** — внешняя среда;
- **observation** — информация о текущем состоянии среды;
- **action** — воздействие агента на среду.

Для нашего проекта:

```text
Environment = веб-страница в браузере
Observation = URL + accessibility snapshot
Action      = click / fill / press / assert
```

Цикл:

```text
observe environment
    -> choose action
    -> execute action
    -> environment changes
    -> observe again
```

Сейчас реализуем только первое наблюдение. Повторный цикл появится позже.

## Почему LLM не должна читать Playwright напрямую

Planner должен получать компактное представление:

```text
URL: https://example.com/login
- textbox "Username"
- textbox "Password"
- button "Login"
```

А не огромный HTML:

```html
<html>
  <div class="css-123-generated-name">
  ...
</html>
```

Observer является слоем преобразования:

```text
browser-specific state -> model-friendly observation
```

Позже он будет:

- получать accessibility tree;
- ограничивать размер текста;
- скрывать секреты;
- добавлять visible text;
- сохранять screenshot;
- отмечать интерактивные элементы.

## Browser adapter расширяется

До сих пор executor использовал:

```python
browser.current_url
browser.click(...)
browser.fill(...)
browser.screenshot()
```

Теперь observer ожидает:

```python
browser.snapshot()
```

Fake browser возвращает строку. Будущий Playwright adapter построит ее из
реальной страницы.

## Чистая функция `observe_browser`

```python
def observe_browser(browser) -> dict:
```

Она должна один раз вызвать:

```python
snapshot = browser.snapshot()
```

И вернуть:

```python
{
    "current_url": browser.current_url,
    "page_snapshot": snapshot,
}
```

Почему возвращается словарь, а не новая Pydantic-модель: результат сразу
совпадает с partial update для `AgentState`.

Можно было создать `PageObservation`, и в большом проекте это может быть
полезно. Пока дополнительная модель не дает достаточной выгоды.

## Observer node

Обычная функция `observe_browser` ничего не знает о LangGraph state.

Node должен иметь форму:

```python
node(state) -> partial update
```

Поэтому снова используем adapter:

```python
def make_observe_node(browser):
    def observe(state: AgentState) -> dict:
        return observe_browser(browser)

    return observe
```

В этом node параметр `state` пока не используется. Это нормально: LangGraph все
равно вызывает nodes с текущим state.

Можно назвать неиспользуемый параметр:

```python
def observe(_state: AgentState) -> dict:
```

Подчеркивание сообщает читателю, что аргумент требуется интерфейсом, но функция
его сознательно не читает.

## Когда происходит наблюдение

При сборке:

```python
observe_node = make_observe_node(browser)
```

Browser не вызывается. Создается closure.

При:

```python
graph.invoke(...)
```

LangGraph доходит до `observe`, вызывает node, а node вызывает:

```python
browser.snapshot()
```

## Задание 9.1

Реализуйте в `src/browser_agent/observer.py`:

```python
observe_browser(browser)
make_observe_node(browser)
```

Сначала добейтесь прохождения:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_observer.py -q
```

## Задание 9.2

Реализуйте `build_observing_agent_graph(model, browser)` в
`src/browser_agent/observing_agent_graph.py`.

Переиспользуйте:

```python
initialize
make_observe_node(browser)
make_plan_node(model)
make_execute_node(browser)
```

Граф:

```text
START -> initialize -> observe -> plan -> execute -> END
```

Вход теперь содержит только:

```python
{"test_case": test_case}
```

Snapshot появляется внутри графа.

## Порядок вызовов

Fake browser должен зафиксировать:

```python
[
    ("snapshot",),
    ("click", 'button "Login"'),
    ("screenshot",),
]
```

Это доказывает:

1. Сначала прочитано состояние.
2. Затем planner выбрал действие.
3. Затем executor изменил страницу.
4. После действия сохранен screenshot.

## Важное ограничение

После click URL изменился, но `state["current_url"]` все еще содержит URL,
полученный до действия. Актуальный URL есть в:

```python
state["last_result"].url_after
```

Почему: после execute мы еще раз не запускали observe.

В будущем цикл будет:

```text
observe -> plan -> execute -> observe
```

и `current_url` обновится.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_observer.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_observing_agent_graph.py -q
```

Итог:

```text
36 passed
```

## Что нужно понять

1. Что такое environment, observation и action.
2. Почему observer отделен от planner.
3. Почему model получает snapshot, а не объект browser.
4. В какой момент вызывается `browser.snapshot()`.
5. Почему URL в observation может устареть после execute.
