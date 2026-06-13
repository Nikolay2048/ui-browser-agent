# Урок 4. Цикл агента

## Почему цикл важен

До сих пор наши графы двигались только вперед:

```text
START -> initialize -> branch -> END
```

Браузерный агент работает циклически:

```text
observe -> plan -> execute -> observe -> ...
```

На этом уроке пока не будет браузера и LLM. Мы построим детерминированную
модель цикла:

```text
START
  -> initialize
  -> perform_step
  -> router
       | продолжать -> perform_step
       | лимит      -> finish_run
  -> END
```

## Что такое цикл в LangGraph

Цикл появляется, когда ребро ведет к уже выполнявшемуся узлу:

```text
perform_step -> perform_step
```

Но переход выполняется не всегда. Router проверяет состояние и решает:

- повторить `perform_step`;
- перейти в `finish_run`.

Это основа будущего agent loop. Вместо искусственного счетчика позже будут:

- snapshot страницы;
- решение LLM;
- действие Playwright;
- результат действия;
- проверка достижения цели.

## Задание 4.1: шаг

В `src/browser_agent/loop_graph.py` реализуйте:

```python
def perform_step(state: AgentState) -> dict:
```

Функция должна вернуть увеличенный счетчик:

```python
{"step_count": state["step_count"] + 1}
```

Не изменяйте переданный словарь напрямую:

```python
# Так пока не делаем
state["step_count"] += 1
return state
```

Узел должен вернуть частичное обновление.

## Задание 4.2: router

```python
def route_after_step(state: AgentState) -> str:
```

После `perform_step` router получает уже обновленный `step_count`.

Если:

```python
state["step_count"] < state["test_case"].max_steps
```

верните:

```python
"perform_step"
```

Иначе:

```python
"finish_run"
```

Обратите внимание на два разных типа доступа:

```python
state["step_count"]             # TypedDict, поэтому ключ
state["test_case"].max_steps    # Pydantic-модель, поэтому атрибут
```

## Задание 4.3: завершение

```python
def finish_run(state: AgentState) -> dict:
    return {"status": "passed"}
```

## Задание 4.4: граф

Переиспользуйте `initialize`.

Зарегистрируйте:

- `initialize`;
- `perform_step`;
- `finish_run`.

Переходы:

```text
START -> initialize
initialize -> perform_step
```

После `perform_step` добавьте conditional edges:

```python
{
    "perform_step": "perform_step",
    "finish_run": "finish_run",
}
```

Завершение:

```text
finish_run -> END
```

## Пошаговое выполнение при `max_steps=3`

После `initialize`:

```python
step_count = 0
```

Первый `perform_step`:

```python
step_count = 1
```

Router возвращает `"perform_step"`.

Второй шаг:

```python
step_count = 2
```

Router снова возвращает `"perform_step"`.

Третий шаг:

```python
step_count = 3
```

Теперь условие `3 < 3` ложно, поэтому router возвращает `"finish_run"`.

## Почему нужен `max_steps`

LLM может:

- повторять одно действие;
- не замечать достижения цели;
- предлагать неработающий локатор;
- зациклиться между двумя состояниями.

`max_steps` является детерминированным предохранителем. Даже если reasoning
ошибается, граф обязан завершиться.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_loop_graph.py -q
```

Итог всех уроков:

```text
24 passed
```

После выполнения будьте готовы объяснить:

1. Как в графе образуется цикл.
2. Почему router видит уже обновленный счетчик.
3. Почему нельзя полагаться на LLM для ограничения числа шагов.
4. Чем этот учебный цикл похож на будущий browser-agent loop.
