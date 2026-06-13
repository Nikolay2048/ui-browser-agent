# Урок 3. Условные переходы

## Зачем графу router

Предыдущий граф всегда выполнял один маршрут:

```text
START -> initialize -> complete -> END
```

Настоящий агент должен выбирать продолжение на основании состояния:

```text
START -> initialize -> route_start_url
                              | HTTP/HTTPS -> pass_run -> END
                              | другое     -> fail_run -> END
```

Router не изменяет state. Он только возвращает имя следующего узла.

## Детерминированное решение и LLM-решение

Проверка URL не требует LLM:

```python
if url.startswith(("http://", "https://")):
    return "pass_run"
return "fail_run"
```

Это важный принцип агентных систем:

> Используйте LLM только там, где действительно требуется интерпретация.

Формат URL, лимит шагов, разрешенный домен и наличие обязательных аргументов
должны проверяться обычным кодом.

## Задание

Работайте в `src/browser_agent/routing_graph.py`.

### 1. `route_start_url`

Функция получает `AgentState`.

Она возвращает:

- `"pass_run"` для URL с `http://` или `https://`;
- `"fail_run"` для остальных URL.

Не изменяйте state внутри router.

### 2. Терминальные узлы

```python
def pass_run(state: AgentState) -> dict:
    return {"status": "passed"}


def fail_run(state: AgentState) -> dict:
    return {"status": "failed"}
```

### 3. Граф

Переиспользуйте `initialize` из `browser_agent.graph`.

Добавьте узлы:

- `initialize`;
- `pass_run`;
- `fail_run`.

Обычное ребро:

```text
START -> initialize
```

После `initialize` используйте `add_conditional_edges`.

Можно передать mapping явно:

```python
{
    "pass_run": "pass_run",
    "fail_run": "fail_run",
}
```

Оба терминальных узла соедините с `END`.

## Как выполняется conditional edge

После `initialize` LangGraph:

1. передает актуальный state в `route_start_url`;
2. получает строку, например `"pass_run"`;
3. находит ее в mapping;
4. запускает соответствующий node.

Router — это диспетчер перехода, а не рабочий node.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_routing_graph.py -q
```

Новые тесты сначала падают. Итог этапа:

```text
19 passed
```

После выполнения будьте готовы объяснить:

1. Почему router не должен менять state.
2. Почему проверку URL не следует отдавать LLM.
3. Чем `add_edge` отличается от `add_conditional_edges`.
4. Какой state получает router после `initialize`.
