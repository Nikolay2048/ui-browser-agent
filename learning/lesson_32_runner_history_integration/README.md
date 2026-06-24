# Урок 32. Подключаем историю запусков к runner

## Цель урока

На прошлом уроке мы сделали отдельный механизм долговременной памяти:

```text
RunReport -> RunHistoryRecord -> JsonlRunHistoryStore
```

Но пока это изолированный модуль. Он умеет сохранять историю, но реальный запуск
агента сам эту историю не пишет.

В этом уроке нужно подключить историю к `run_agent()` так, чтобы после завершения
запуска агент мог автоматически сохранить запись в append-only историю.

Важно: мы не передаем историю в planner и не используем ее для принятия решений.
Сейчас задача проще и важнее: правильно встроить persistence в жизненный цикл
запуска.

## Где мы сейчас в архитектуре

Упрощенно текущий запуск выглядит так:

```text
run_agent()
  -> browser.open(start_url)
  -> build_agent_graph(model, browser)
  -> graph.stream(...)
  -> final_state
  -> optional build_run_report(final_state)
  -> optional save_run_report(report_dir)
```

После урока 32 он должен выглядеть так:

```text
run_agent()
  -> browser.open(start_url)
  -> build_agent_graph(model, browser)
  -> graph.stream(...)
  -> final_state
  -> build RunReport when needed
  -> optional save_run_report(report_dir)
  -> optional history_store.append(RunHistoryRecord)
```

## Почему это делаем в `runner.py`, а не в нодах графа

Это важный архитектурный принцип.

Ноды графа должны выполнять агентную работу:

- observe: получить snapshot страницы;
- plan: выбрать следующее действие;
- execute: выполнить действие;
- judge: проверить результат;
- classify/report: оформить сбой.

А `runner.py` отвечает за composition:

- открыть браузер;
- собрать graph;
- передать runtime config;
- стримить состояния;
- сохранить итоговые артефакты.

История завершенных запусков — это не действие агента внутри цикла. Это внешняя
инфраструктурная запись после завершения запуска. Поэтому правильное место для
нее — `runner.py`.

Если писать историю внутри ноды графа, появятся проблемы:

- одна и та же нода может выполниться повторно при resume/checkpoint;
- запись может появиться до финального состояния;
- граф станет зависеть от файлового хранилища;
- тестировать агентное поведение станет сложнее.

## Что такое dependency inversion

Плохой вариант:

```python
from browser_agent.run_history import JsonlRunHistoryStore

def run_agent(..., history_path: str | None = None):
    if history_path is not None:
        store = JsonlRunHistoryStore(history_path)
        store.append(...)
```

Почему плохо:

- `runner.py` начинает знать про конкретный формат хранения;
- позже будет сложнее заменить JSONL на SQLite, Postgres, S3 или LangSmith;
- тестам придется работать с файловой системой даже там, где это не нужно.

Лучший вариант:

```python
def run_agent(..., history_store=None):
    if history_store is not None:
        history_store.append(record)
```

`runner.py` знает только одно: у объекта есть метод `append(record)`.
Конкретное хранилище может быть любым:

- `JsonlRunHistoryStore`;
- fake store в тестах;
- база данных;
- API-клиент;
- in-memory store для экспериментов.

Это и есть dependency inversion: верхний уровень не зависит от конкретной
реализации нижнего уровня, а получает зависимость снаружи.

## Зачем нужен `Protocol`

В Python можно просто принять `history_store=None` и вызвать `.append()`.
Это сработает.

Но для читаемости и типизации лучше описать минимальный контракт:

```python
from typing import Protocol

class RunHistoryStore(Protocol):
    def append(self, record: RunHistoryRecord) -> None:
        ...
```

Это не базовый класс и не интерфейс в Java-смысле. `Protocol` говорит:

> Нам не важно, от какого класса наследуется объект. Если у него есть подходящий
> метод `append`, он подходит.

Такой подход называется structural typing.

Пример:

```python
class JsonlRunHistoryStore:
    def append(self, record: RunHistoryRecord) -> None:
        ...
```

Этот класс не обязан наследоваться от `RunHistoryStore`. Он уже подходит, потому
что имеет нужный метод.

## Почему `RunReport` нужно строить один раз

В `runner.py` уже есть сохранение отчета:

```python
if report_dir is not None:
    report = build_run_report(final_state)
    save_run_report(report, report_dir)
```

Теперь появится еще одна причина построить report:

```python
if history_store is not None:
    record = build_run_history_record(report)
    history_store.append(record)
```

Плохой вариант:

```python
if report_dir is not None:
    save_run_report(build_run_report(final_state), report_dir)

if history_store is not None:
    history_store.append(
        build_run_history_record(build_run_report(final_state))
    )
```

Почему плохо:

- `build_run_report()` вызывается два раза;
- если позже в report появится время, id или вычисляемые поля, можно получить
  два разных отчета;
- сложнее тестировать.

Хороший вариант:

```python
report = None

if report_dir is not None or history_store is not None:
    report = build_run_report(final_state)

if report_dir is not None:
    save_run_report(report, report_dir)

if history_store is not None:
    history_store.append(build_run_history_record(report))
```

Один final state -> один report -> разные способы сохранения.

## Что делать с ошибкой записи истории

В production есть несколько стратегий:

1. Fail fast: если история не сохранилась, весь запуск считается ошибочным.
2. Best effort: запуск успешен, а ошибка истории только логируется.
3. Retry/outbox: запись кладется в очередь и повторяется позже.

Для учебного проекта сейчас выбираем самый простой и честный вариант:

```text
если history_store.append() упал, пусть ошибка поднимется наружу
```

Почему:

- мы сразу увидим проблему;
- тесты будут проще;
- пока у нас нет нормального логирования, retry и очередей.

Позже, когда будем говорить про production reliability, можно будет добавить
best-effort режим.

## Задание 32.1. Описать контракт хранилища

Файл:

```text
src/browser_agent/run_history.py
```

Добавь `Protocol`:

```python
from typing import Protocol

class RunHistoryStore(Protocol):
    def append(self, record: RunHistoryRecord) -> None:
        ...
```

`JsonlRunHistoryStore` менять не нужно. Он уже подходит под этот контракт,
потому что у него есть метод `append()`.

## Задание 32.2. Расширить `run_agent`

Файл:

```text
src/browser_agent/runner.py
```

Нужно добавить параметры:

```python
history_store: RunHistoryStore | None = None,
run_id: str | None = None,
```

`run_id` нужен для тестов и воспроизводимости. Если его не передали, `uuid4`
создастся внутри `build_run_history_record()`.

Логика после завершения graph должна быть такой:

1. Если `final_state is None`, как и раньше, выбрасываем `RuntimeError`.
2. Если нужен report или history, строим `RunReport`.
3. Если `report_dir` передан, сохраняем JSON и Markdown.
4. Если `history_store` передан, строим `RunHistoryRecord` и вызываем
   `history_store.append(record)`.
5. Возвращаем `final_state`, как и раньше.

## Задание 32.3. Написать тест на history integration

Файл:

```text
tests/test_runner_history.py
```

Сделай fake store:

```python
class InMemoryHistoryStore:
    def __init__(self) -> None:
        self.records = []

    def append(self, record) -> None:
        self.records.append(record)
```

Тест должен проверять:

- `run_agent(..., history_store=store, run_id="test-run-1")` завершился успешно;
- в `store.records` появилась ровно одна запись;
- `record.run_id == "test-run-1"`;
- `record.report.test_case.id` совпадает с id test case;
- `record.report.status == "passed"`;
- `record.report.step_count` совпадает с `final_state["step_count"]`.

Можно переиспользовать fake model/browser из `tests/test_runner.py`, но лучше не
импортировать тестовые классы из другого test-файла. В production-проектах тесты
становятся хрупкими, когда один test module зависит от другого. Просто скопируй
минимальные fake-классы или вынеси их позже в `tests/fakes.py`.

## Задание 32.4. Проверить, что report и history используют один результат

Добавь второй тест:

```text
run_agent(..., report_dir=tmp_path, history_store=store)
```

Проверь:

- markdown/json report создались;
- history record создался;
- `store.records[0].report.test_case.id` совпадает с именем JSON-файла;
- статус в history такой же, как в final state.

## Как запускать

Сначала точечно:

```powershell
python -m pytest tests\test_runner_history.py -q
```

Потом связанные тесты:

```powershell
python -m pytest tests\test_runner.py tests\test_runner_reporting.py tests\test_run_history.py tests\test_runner_history.py -q
```

И в конце весь проект:

```powershell
python -m pytest -q
```

## Что должно стать понятнее после урока

После этого урока ты должен понимать:

- почему долговременная память подключается в composition layer;
- почему не нужно писать историю внутри graph node;
- зачем передавать dependency снаружи;
- чем `Protocol` отличается от наследования;
- почему итоговый `RunReport` лучше строить один раз;
- как тестировать integration без реального файла и без реального браузера.

## Критерий готовности

Урок считается завершенным, когда:

- `RunHistoryStore` описан через `Protocol`;
- `run_agent()` умеет принимать `history_store`;
- завершенный запуск сохраняет один `RunHistoryRecord`;
- старое сохранение report не сломано;
- новые и старые тесты проходят.
