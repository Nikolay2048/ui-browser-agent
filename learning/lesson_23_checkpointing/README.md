# Урок 23. Checkpointing и thread_id

## Цель

До этого `AgentState` существовал только во время одного вызова:

```text
graph.stream(...)
    -> state меняется
    -> graph завершается
    -> final_state возвращается runner-ом
```

Теперь добавим persistence:

```text
LangGraph
    -> выполняет ноду
    -> сохраняет StateSnapshot
    -> выполняет следующую ноду
    -> сохраняет новый StateSnapshot
```

Это основа для:

- продолжения после паузы;
- human-in-the-loop;
- восстановления после ошибки;
- просмотра истории состояния;
- time travel;
- отказоустойчивости.

## Три понятия

### Checkpoint

Снимок состояния графа в конкретный момент. Он содержит не только values из
`AgentState`, но и служебную информацию LangGraph о следующей ноде и текущей
позиции выполнения.

### Checkpointer

Компонент, который записывает и читает checkpoints:

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

### Thread

Последовательность checkpoint-ов одного логического запуска:

```text
thread_id=run-42
├── checkpoint 1
├── checkpoint 2
├── checkpoint 3
└── checkpoint 4
```

`thread_id` не является Python thread или процессом ОС. Это ключ, по которому
checkpointer находит историю.

## Почему нельзя использовать только test_case.id

Один test case может запускаться много раз:

```text
login-test, запуск утром
login-test, запуск после исправления
login-test, запуск в CI
```

Если всегда использовать `thread_id="login-test"`, независимые запуски попадут
в одну историю.

В production лучше использовать уникальный run ID:

```python
from uuid import uuid4

thread_id = f"{test_case.id}:{uuid4()}"
```

Для обучения thread ID передаём явно, чтобы видеть связь между config и
checkpoint.

## RunnableConfig

В прошлом уроке config содержал observability:

```python
{
    "run_name": "ui-test:checkpoint-case",
    "tags": ["browser-agent", "ui-test"],
    "metadata": {...},
}
```

Для persistence добавляется:

```python
{
    "configurable": {
        "thread_id": "run-123",
    }
}
```

Один `RunnableConfig` одновременно управляет trace и checkpointing.

## Задание 23.1. Thread config

Реализуй в `src/browser_agent/persistence.py`:

```python
def build_thread_config(
    test_case: TestCase,
    thread_id: str,
) -> RunnableConfig:
```

Алгоритм:

1. Отклонить пустой или состоящий из пробелов `thread_id`.
2. Получить config через `build_trace_config(test_case)`.
3. Добавить `configurable`.
4. Вернуть config.

Один из вариантов:

```python
if not thread_id.strip():
    raise ValueError("thread_id must not be blank")

config = build_trace_config(test_case)
config["configurable"] = {"thread_id": thread_id}
return config
```

Мы изменяем новый локальный словарь `config`, а не объект, переданный извне.

Проверка:

```powershell
python -m pytest tests\test_persistence.py -q --basetemp=.pytest-tmp
```

Ожидается `4 passed`.

## Задание 23.2. Компиляция с checkpointer

Расширь `build_agent_graph()`:

```python
def build_agent_graph(
    model,
    browser,
    judge_model=None,
    classifier_model=None,
    reporter_model=None,
    checkpointer=None,
):
```

Измени последнюю строку:

```python
return builder.compile(checkpointer=checkpointer)
```

Когда `checkpointer=None`, поведение остаётся прежним.

Проверка:

```powershell
python -m pytest tests\test_graph_persistence.py -q --basetemp=.pytest-tmp
```

Ожидается `1 passed`.

## Задание 23.3. Runner

Расширь сигнатуру:

```python
def run_agent(
    model,
    browser,
    test_case: TestCase,
    on_state=None,
    report_dir=None,
    checkpointer=None,
    thread_id: str | None = None,
) -> dict:
```

Правило:

```python
if checkpointer is not None and thread_id is None:
    raise ValueError("thread_id is required when checkpointer is enabled")
```

Затем передай checkpointer:

```python
graph = build_agent_graph(
    model,
    browser,
    checkpointer=checkpointer,
)
```

Выбери config:

```python
if checkpointer is None:
    run_config = build_trace_config(test_case)
else:
    run_config = build_thread_config(test_case, thread_id)
```

И передай его в `graph.stream()`.

Почему нельзя создать `InMemorySaver()` внутри `run_agent`: после возврата из
функции вызывающий код потеряет ссылку на хранилище и не сможет получить
checkpoint или использовать его снова.

Проверка:

```powershell
python -m pytest tests\test_runner_persistence.py -q --basetemp=.pytest-tmp
```

Ожидается `2 passed`.

## Задание 23.4. Реальный запуск

В `scripts/run_real_agent.py`:

```python
from uuid import uuid4
from langgraph.checkpoint.memory import InMemorySaver
```

До `run_agent()`:

```python
checkpointer = InMemorySaver()
thread_id = f"{test_case.id}:{uuid4()}"
```

Передай:

```python
checkpointer=checkpointer,
thread_id=thread_id,
```

После завершения можно собрать тот же config и прочитать snapshot:

```python
from browser_agent.persistence import build_thread_config

config = build_thread_config(test_case, thread_id)
graph = build_agent_graph(model, browser, checkpointer=checkpointer)
snapshot = graph.get_state(config)

print(f"checkpoint thread: {thread_id}")
print(f"checkpoint status: {snapshot.values['status']}")
print(f"checkpoint next: {snapshot.next}")
```

У завершённого графа `snapshot.next` обычно пуст. Это означает, что ожидающих
выполнения нод нет.

Для этого задания допустимо сначала только подключить checkpointer к реальному
run. Чтение snapshot можно сделать отдельным экспериментальным скриптом, чтобы
не усложнять основной runner.

## InMemorySaver не является production storage

Он хранит checkpoints только в памяти процесса:

```text
Python завершился -> checkpoints исчезли
```

Он подходит для:

- обучения;
- unit-тестов;
- локального прототипа.

Для production нужен durable checkpointer, например база данных. Конкретный
backend выберем позже после проектирования deployment.

## Важное ограничение UI-агента

Checkpoint сохраняет:

```text
AgentState
позицию графа
служебные данные выполнения
```

Но он не сохраняет:

```text
объект Playwright Page
процесс Chromium
открытые websocket-соединения
состояние DOM вне state
```

Если Python-процесс остался жив и браузер открыт, граф можно продолжить с тем же
browser adapter. После перезапуска процесса одного checkpoint недостаточно.

Для межпроцессного восстановления UI-теста потребуются:

1. durable checkpointer;
2. восстановление browser context/storage state;
3. открытие сохранённого URL;
4. повторный snapshot;
5. проверка, что UI соответствует checkpoint;
6. безопасное продолжение.

Это важное инженерное отличие браузерного агента от текстового chatbot.

## Checkpointer и Store

```text
Checkpointer -> состояние одного thread
Store        -> знания между разными thread
```

Пример Store:

```text
известные особенности сайта
стабильные locator hints
документация продукта
предыдущие подтверждённые баги
```

RAG и долговременную память нельзя заменять checkpoint-ами.

## Полная проверка

```powershell
python -m pytest -q --basetemp=.pytest-tmp
```

Ожидается:

```text
106 passed
```

## Вопросы для самопроверки

1. Чем checkpoint отличается от финального `RunReport`?
2. Что именно идентифицирует `thread_id`?
3. Почему один `test_case.id` не всегда подходит как thread ID?
4. Почему checkpointer передаётся при `compile()`, а thread ID при запуске?
5. Почему нельзя создавать `InMemorySaver` внутри runner?
6. Почему checkpoint не гарантирует восстановление Playwright после рестарта?
7. Чем checkpointer отличается от Store?

## Следующий урок

В уроке 24 добавим настоящий human-in-the-loop interrupt перед выполнением
опасного или сомнительного browser action. Граф остановится, сохранит состояние
и продолжится через `Command(resume=...)` с тем же `thread_id`.
