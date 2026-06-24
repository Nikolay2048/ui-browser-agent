# Урок 33. Human feedback records

## Цель урока

Мы уже умеем сохранять историю завершенных запусков:

```text
RunReport -> RunHistoryRecord -> JsonlRunHistoryStore
```

Теперь добавляем следующий слой памяти: **человеческую обратную связь**.

Пример ситуации:

```text
Агент дошел до результата, но сделал лишний шаг.
Человек хочет оставить подсказку:
"В этом сценарии не нужно нажимать Save повторно, если уже виден toast Profile saved".
```

Или:

```text
Агент упал, потому что выбрал неправильный locator.
Человек хочет оставить подсказку:
"Для поля Email используй label=Email, а не text=Email".
```

Такую информацию нельзя просто потерять в консоли или держать в голове.
Ее нужно сохранить как структурированный объект, чтобы позже:

- находить похожие feedback-записи;
- передавать их planner-у;
- анализировать частые ошибки агента;
- строить regression evaluation "до feedback" и "после feedback".

## Где это находится в общей системе

Пока у нас есть такая цепочка:

```text
test case
  -> agent run
  -> final state
  -> run report
  -> run history
```

После урока 33 появится параллельная цепочка:

```text
completed run
  -> human feedback
  -> feedback history
```

Важно: feedback не заменяет run history.

`RunHistoryRecord` отвечает на вопрос:

```text
Что агент реально сделал?
```

`HumanFeedbackRecord` отвечает на вопрос:

```text
Что человек понял после просмотра результата?
```

Это разные факты.

## Почему feedback не надо сразу писать в prompt

Новичков часто тянет сделать так:

```text
Открыл trace, увидел ошибку, добавил строку в system prompt.
```

Для обучения это нормально, но в production это плохо масштабируется.

Проблемы:

- prompt быстро превращается в свалку частных случаев;
- нельзя понять, какая подсказка помогла, а какая ухудшила поведение;
- нельзя измерить влияние feedback;
- разные сайты и разные test case начинают мешать друг другу;
- невозможно удалить устаревшую подсказку точечно.

Поэтому взрослый подход такой:

```text
1. Сохраняем feedback как данные.
2. Учимся искать релевантный feedback.
3. Передаем только найденный feedback в planner.
4. Измеряем, стало ли лучше.
```

Сегодня делаем только пункт 1.

## Какая память здесь появляется

У агента постепенно появляются разные уровни памяти:

```text
AgentState
  краткосрочная рабочая память одного запуска

Checkpoint
  техническая возможность продолжить выполнение graph

RunHistoryRecord
  эпизодическая память: что происходило в прошлых запусках

HumanFeedbackRecord
  обучающая память: что человек считает полезной коррекцией

Vector/RAG memory
  поиск похожих прошлых ситуаций
```

Feedback records — это мост между "агент просто выполняется" и "агент учится на
ошибках".

## Что именно сохранять в feedback

Нам нужен не просто текстовый комментарий.

Плохой feedback:

```text
"опять не туда нажал"
```

Почему плохо:

- непонятно, какой запуск;
- непонятно, какой test case;
- непонятно, какой шаг;
- непонятно, что делать иначе;
- такую запись сложно использовать в prompt.

Хороший feedback:

```text
run_id: "run-123"
test_case_id: "profile-save"
scope: "step"
step_number: 2
summary: "Planner selected the wrong Save button"
correction: "Use role=button[name='Save profile'], not text=Save"
tags: ["locator", "planner"]
```

Такая запись уже пригодна для retrieval и анализа.

## Scope feedback

Feedback может относиться к разным уровням:

```text
run
  комментарий ко всему запуску

step
  комментарий к конкретному шагу route

planner
  подсказка о выборе действия

judge
  подсказка о проверке результата

bug_report
  подсказка об оформлении бага
```

В этом уроке особенно важен `step`.

Если `scope == "step"`, то `step_number` обязателен.

Если `scope != "step"`, то `step_number` должен быть `None`.

Это доменное правило. Оно защищает нас от неясных записей:

```text
scope = step, но step_number отсутствует
```

или:

```text
scope = run, но почему-то указан step_number
```

## Почему снова JSONL

Для feedback используем тот же подход, что для run history:

```text
одна строка = один JSON object
```

Плюсы:

- легко append-ить;
- удобно читать построчно;
- не нужно переписывать весь файл;
- можно руками открыть и посмотреть;
- формат подходит для последующей миграции в базу.

В production позже это может стать таблицей:

```text
feedback_id
run_id
test_case_id
scope
step_number
summary
correction
tags
created_at
```

Но для учебного проекта JSONL сейчас лучше: меньше инфраструктуры, больше
понимания.

## Почему feedback отдельный модуль

Мы создаем отдельный файл:

```text
src/browser_agent/feedback.py
```

Не кладем это в `run_history.py`, потому что это другой смысл.

`run_history.py`:

```text
машинная история завершенных запусков
```

`feedback.py`:

```text
человеческие коррекции и подсказки
```

Разделение помогает не превратить один файл в "все про память".

## Задание 33.1. Feedback scope

Файл:

```text
src/browser_agent/feedback.py
```

Создай enum:

```python
class FeedbackScope(StrEnum):
    RUN = "run"
    STEP = "step"
    PLANNER = "planner"
    JUDGE = "judge"
    BUG_REPORT = "bug_report"
```

Используем `StrEnum`, как в доменных моделях проекта.

## Задание 33.2. HumanFeedbackRecord

В том же файле создай Pydantic-модель:

```python
class HumanFeedbackRecord(BaseModel):
    feedback_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    test_case_id: str = Field(min_length=1)
    created_at: datetime
    scope: FeedbackScope
    step_number: int | None = Field(default=None, ge=1)
    summary: str = Field(min_length=1)
    correction: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
```

Добавь validator:

```text
если scope == STEP, step_number обязателен
если scope != STEP, step_number должен быть None
```

## Задание 33.3. Builder-функция

Сделай функцию:

```python
def build_human_feedback_record(
    *,
    run_id: str,
    test_case_id: str,
    scope: FeedbackScope,
    summary: str,
    correction: str,
    step_number: int | None = None,
    tags: list[str] | None = None,
    feedback_id: str | None = None,
    created_at: datetime | None = None,
) -> HumanFeedbackRecord:
    ...
```

Правила:

- если `feedback_id is None`, сгенерировать `uuid4`;
- если `created_at is None`, использовать `datetime.now(timezone.utc)`;
- если `tags is None`, сохранить пустой список;
- вернуть `HumanFeedbackRecord`.

Обрати внимание: `tags: list[str] | None = None` в аргументах функции лучше,
чем `tags: list[str] = []`. Значение `[]` как default argument в Python может
создать неприятные shared mutable state эффекты.

## Задание 33.4. JsonlFeedbackStore

Сделай класс:

```python
class JsonlFeedbackStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: HumanFeedbackRecord) -> None:
        ...

    def load_all(self) -> list[HumanFeedbackRecord]:
        ...

    def find_by_test_case_id(self, test_case_id: str) -> list[HumanFeedbackRecord]:
        ...

    def find_by_run_id(self, run_id: str) -> list[HumanFeedbackRecord]:
        ...
```

Логика такая же, как в `JsonlRunHistoryStore`.

Да, здесь есть похожий код. Это нормально для текущего этапа.
Обобщать JSONL-store в generic abstraction пока рано: сначала мы должны увидеть
два реальных похожих случая, а потом уже решать, нужна ли абстракция.

## Задание 33.5. Tests

Я добавил тесты в:

```text
tests/test_feedback.py
```

Сначала они будут падать. Это нормально: это контракт задания.

Запускай точечно:

```powershell
python -m pytest tests\test_feedback.py -q
```

Потом весь проект:

```powershell
python -m pytest -q
```

## Что должно стать понятнее

После урока ты должен понимать:

- почему feedback — это данные, а не ручная правка prompt;
- чем feedback отличается от run history;
- зачем структурировать человеческую коррекцию;
- почему scope и step_number должны иметь доменные правила;
- зачем использовать builder-функцию;
- почему JSONL подходит для append-only памяти;
- почему не нужно преждевременно делать generic abstraction.

## Критерий готовности

Урок завершен, когда:

- создан `src/browser_agent/feedback.py`;
- реализованы `FeedbackScope`, `HumanFeedbackRecord`;
- работает `build_human_feedback_record()`;
- работает `JsonlFeedbackStore`;
- `tests/test_feedback.py` проходит;
- полный `pytest` проходит.
