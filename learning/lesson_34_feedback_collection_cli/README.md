# Урок 34. Feedback collection CLI

## Цель урока

На прошлом уроке мы сделали модель и хранилище человеческой обратной связи:

```text
HumanFeedbackRecord -> JsonlFeedbackStore
```

Но пользоваться этим пока неудобно. Чтобы добавить feedback, нужно писать длинный
`python -c`, помнить названия полей и вручную создавать объект.

В этом уроке мы сделаем нормальную команду:

```powershell
python scripts\add_feedback.py `
  --run-id "first-real-agent:..." `
  --test-case-id first-real-agent `
  --scope step `
  --step-number 1 `
  --summary "Planner selected a fragile locator." `
  --correction "Use label=Task for the task input." `
  --tags planner,locator
```

Команда должна сохранить запись в:

```text
artifacts/feedback/feedback.jsonl
```

## Зачем нужен отдельный CLI

Сейчас мы строим agent memory pipeline:

```text
agent run
  -> run history
  -> human review
  -> feedback record
  -> feedback retrieval
  -> planner memory context
```

CLI нужен для третьего шага: **human review -> feedback record**.

Это не финальный интерфейс продукта. В production это может быть:

- кнопка в UI;
- форма в LangSmith/внутренней админке;
- комментарий в bug tracker;
- Slack workflow;
- review panel рядом с trace.

Но для обучения CLI идеален:

- прозрачно видно, какие поля мы сохраняем;
- легко тестировать;
- не нужно строить web UI;
- можно быстро собрать первые feedback examples.

## Почему не писать всю логику в `scripts/add_feedback.py`

Плохой вариант:

```text
scripts/add_feedback.py
  парсит аргументы
  чистит tags
  строит Pydantic-модель
  пишет JSONL
  печатает результат
```

Такой файл можно запускать, но его неудобно тестировать.

Лучше разделить:

```text
src/browser_agent/feedback_cli.py
  тестируемая логика CLI

scripts/add_feedback.py
  тонкая entrypoint-обертка
```

Тогда тесты импортируют обычные функции:

```python
from browser_agent.feedback_cli import build_feedback_parser
```

А пользователь запускает:

```powershell
python scripts\add_feedback.py ...
```

Это распространенный production-паттерн: **fat library, thin script**.

## Что делает `argparse`

`argparse` — стандартная библиотека Python для CLI.

Она решает задачи:

- описать аргументы;
- проверить обязательные поля;
- показать `--help`;
- преобразовать типы;
- завершить программу с понятной ошибкой, если аргументы неверные.

Пример:

```python
parser.add_argument("--run-id", required=True)
parser.add_argument("--step-number", type=int)
```

После:

```python
args = parser.parse_args()
```

мы получаем объект:

```python
args.run_id
args.step_number
```

Важно: `argparse` обычно возвращает простые типы: `str`, `int`, `bool`.
Доменную валидацию все равно должна делать наша Pydantic-модель.

## Почему scope лучше проверять через choices

У нас есть enum:

```python
class FeedbackScope(StrEnum):
    RUN = "run"
    STEP = "step"
    PLANNER = "planner"
    JUDGE = "judge"
    BUG_REPORT = "bug_report"
```

В parser можно добавить:

```python
parser.add_argument(
    "--scope",
    required=True,
    choices=[scope.value for scope in FeedbackScope],
)
```

Тогда пользователь не сможет передать:

```text
--scope something-weird
```

CLI остановится раньше, до создания Pydantic-модели.

Но правило:

```text
scope=step требует step_number
```

лучше оставить в `HumanFeedbackRecord`.

Почему: это доменное правило, оно должно работать не только в CLI, но и в любом
другом месте, где создается feedback: UI, API, тест, future LangSmith integration.

## Как обрабатывать tags

Пользователю удобно передавать tags одной строкой:

```powershell
--tags planner,locator,task-input
```

Внутри нам нужен список:

```python
["planner", "locator", "task-input"]
```

Нужна маленькая функция:

```python
def parse_tags(raw: str | None) -> list[str]:
    ...
```

Правила:

- `None` -> `[]`;
- `""` -> `[]`;
- `"planner, locator"` -> `["planner", "locator"]`;
- пустые элементы игнорируем:

```text
"planner,,locator," -> ["planner", "locator"]
```

Такие маленькие функции полезно тестировать отдельно. В агентских системах много
качества держится на скучных адаптерах данных.

## Что должен возвращать CLI-слой

Функция сохранения должна не только писать файл, но и возвращать созданный record:

```python
record = save_feedback_from_args(args)
```

Зачем:

- удобно тестировать;
- можно напечатать `record.model_dump_json(indent=2)`;
- позже можно отправить этот record в LangSmith, базу или UI.

## Задание 34.1. Создать `feedback_cli.py`

Файл:

```text
src/browser_agent/feedback_cli.py
```

Добавь константу:

```python
DEFAULT_FEEDBACK_PATH = Path("artifacts") / "feedback" / "feedback.jsonl"
```

Почему относительный путь нормален: команду мы запускаем из корня проекта.
Позже можно будет сделать конфигурацию через env.

## Задание 34.2. Реализовать `parse_tags`

Сигнатура:

```python
def parse_tags(raw: str | None) -> list[str]:
    ...
```

Пример:

```python
parse_tags("planner, locator ,,") == ["planner", "locator"]
```

## Задание 34.3. Реализовать parser

Сигнатура:

```python
def build_feedback_parser() -> argparse.ArgumentParser:
    ...
```

Аргументы:

```text
--run-id          required
--test-case-id    required
--scope           required, choices from FeedbackScope
--summary         required
--correction      required
--step-number     optional int
--tags            optional string
--feedback-path   optional Path, default DEFAULT_FEEDBACK_PATH
```

## Задание 34.4. Реализовать сохранение

Сигнатура:

```python
def save_feedback_from_args(args: argparse.Namespace) -> HumanFeedbackRecord:
    ...
```

Логика:

1. Создать `JsonlFeedbackStore(args.feedback_path)`.
2. Создать record через `build_human_feedback_record(...)`.
3. Передать `scope=FeedbackScope(args.scope)`.
4. Передать `tags=parse_tags(args.tags)`.
5. Сохранить через `store.append(record)`.
6. Вернуть record.

## Задание 34.5. Реализовать `main`

Сигнатура:

```python
def main(argv: Sequence[str] | None = None) -> int:
    ...
```

Логика:

1. Создать parser.
2. Распарсить `argv`.
3. Сохранить feedback.
4. Напечатать JSON созданной записи.
5. Вернуть `0`.

Почему `argv` передается параметром: так `main()` можно тестировать без реального
командного запуска.

## Задание 34.6. Сделать script entrypoint

Файл:

```text
scripts/add_feedback.py
```

Он должен быть тонким:

```python
"""Add human feedback for a completed agent run."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.feedback_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

## Как запускать тесты

Сначала:

```powershell
python -m pytest tests\test_feedback_cli.py -q
```

Потом:

```powershell
python -m pytest tests\test_feedback.py tests\test_feedback_cli.py -q
```

В конце:

```powershell
python -m pytest -q
```

## Как использовать после реализации

После запуска агента:

```powershell
python scripts\run_real_agent.py
```

скопируй `checkpoint thread`, например:

```text
first-real-agent:3f2d...
```

Затем добавь feedback:

```powershell
python scripts\add_feedback.py `
  --run-id "first-real-agent:3f2d..." `
  --test-case-id first-real-agent `
  --scope step `
  --step-number 1 `
  --summary "Planner selected a fragile locator." `
  --correction "Use label=Task for the task input." `
  --tags planner,locator
```

Проверить файл:

```powershell
Get-Content artifacts\feedback\feedback.jsonl
```

## Критерий готовности

Урок завершен, когда:

- реализован `src/browser_agent/feedback_cli.py`;
- работает `scripts/add_feedback.py`;
- feedback сохраняется в JSONL;
- `tests/test_feedback_cli.py` проходит;
- полный `pytest` проходит.
