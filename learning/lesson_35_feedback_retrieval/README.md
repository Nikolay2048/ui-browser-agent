# Урок 35. Feedback retrieval

## Цель урока

Мы уже умеем:

```text
создавать HumanFeedbackRecord
сохранять feedback через CLI
хранить feedback в artifacts/feedback/feedback.jsonl
```

Но агент пока не может найти полезные подсказки для нового запуска.

В этом уроке делаем первый retrieval-слой:

```text
TestCase + feedback records -> relevant feedback records
```

Пока без embeddings и vector database. Только простые, понятные правила:

- точное совпадение `test_case.id`;
- фильтрация по scope;
- фильтрация по tags;
- ограничение количества результатов;
- порядок от новых к старым.

Это не "игрушечный" этап. В production часто начинают именно так: сначала
детерминированные правила, потом embeddings там, где правил уже не хватает.

## Где retrieval находится в memory pipeline

Наша цепочка постепенно становится такой:

```text
agent run
  -> run history
  -> human feedback
  -> feedback retrieval
  -> prompt memory context
  -> planner uses memory
```

Уроки:

```text
31-32: run history
33: feedback records
34: feedback collection CLI
35: feedback retrieval
36: memory context for planner
37: planner uses feedback
```

Сегодня мы делаем только retrieval.

Planner пока не меняем.

## Что такое retrieval

Retrieval — это не обязательно RAG и не обязательно vector search.

Retrieval означает:

```text
из большой памяти выбрать маленький релевантный кусок
```

Почему нельзя просто передавать весь feedback в prompt:

- prompt раздуется;
- модель начнет видеть нерелевантные подсказки;
- разные сайты и сценарии будут мешать друг другу;
- стоимость и latency вырастут;
- поведение станет менее предсказуемым.

Нам нужен фильтр:

```text
вот текущий TestCase
вот все HumanFeedbackRecord
верни только те, которые могут помочь
```

## Deterministic retrieval vs semantic retrieval

Deterministic retrieval:

```text
test_case.id == feedback.test_case_id
tag in feedback.tags
scope in allowed_scopes
```

Плюсы:

- просто тестировать;
- предсказуемо;
- не нужен embedding model;
- легко объяснить, почему запись выбрана.

Минусы:

- не найдет похожий сценарий с другим id;
- плохо работает с переформулировками;
- требует хороших tags.

Semantic retrieval:

```text
embedding(test_case.goal) близок к embedding(feedback.correction)
```

Плюсы:

- находит похожие ситуации;
- работает с разными формулировками.

Минусы:

- сложнее тестировать;
- нужны embeddings;
- возможны странные совпадения;
- сложнее объяснить результат.

Поэтому правильный учебный порядок:

```text
сначала deterministic retrieval
потом semantic retrieval
потом hybrid retrieval
```

## Почему порядок должен быть от новых к старым

Feedback — это знание, которое может устаревать.

Например:

```text
месяц назад: "Use text=Save"
сегодня: "Use role=button[name='Save profile']"
```

Если вернуть старую подсказку первой, planner может выбрать хуже.

Поэтому в retrieval обычно действует правило:

```text
сначала самые свежие записи
```

Наш JSONL store хранит записи в append order:

```text
старые -> новые
```

А retrieval должен вернуть:

```text
новые -> старые
```

## Зачем нужен limit

Даже если найдено 30 записей, planner-у не нужно видеть все.

Нам нужен параметр:

```python
limit: int = 5
```

Он защищает prompt от разрастания.

Правило:

```text
limit должен быть >= 1
```

Если передать `limit=0`, это ошибка вызова.

## Как фильтровать tags

В этом уроке используем простое правило:

```text
если required_tags пустой список, tags не фильтруем
если required_tags задан, record подходит, когда у него есть хотя бы один required tag
```

Пример:

```python
required_tags = ["planner", "locator"]
record.tags = ["planner", "memory"]
```

Запись подходит, потому что есть пересечение:

```text
planner
```

Это называется "any match".

Почему не требуем все tags сразу:

```text
["planner", "locator"] subset of record.tags
```

Потому что на раннем этапе feedback может быть размечен неидеально. Более мягкое
правило даст больше полезных результатов. Позже можно будет добавить режим
`match_all_tags`.

## Какой модуль создаем

Файл:

```text
src/browser_agent/feedback_retrieval.py
```

Он не должен знать про JSONL-файл напрямую.

Правильно:

```python
records = store.load_all()
retrieve_feedback_for_test_case(test_case, records)
```

Почему:

- retrieval легче тестировать;
- потом источник records может быть SQLite, LangSmith, vector DB;
- функция не зависит от файловой системы.

Это тот же принцип dependency inversion, который мы уже применяли в `runner`.

## Задание 35.1. Создать параметры retrieval

Создай Pydantic-модель:

```python
class FeedbackRetrievalQuery(BaseModel):
    test_case: TestCase
    scopes: list[FeedbackScope] = Field(default_factory=list)
    required_tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)
```

Смысл:

- `test_case` — для какого сценария ищем feedback;
- `scopes` — какие типы feedback нужны;
- `required_tags` — какие tags нас интересуют;
- `limit` — сколько максимум записей вернуть.

Если `scopes=[]`, scope не фильтруем.

Если `required_tags=[]`, tags не фильтруем.

## Задание 35.2. Реализовать retrieval

Функция:

```python
def retrieve_feedback(
    query: FeedbackRetrievalQuery,
    records: list[HumanFeedbackRecord],
) -> list[HumanFeedbackRecord]:
    ...
```

Правила:

1. Берем только записи, где:

```python
record.test_case_id == query.test_case.id
```

2. Если `query.scopes` не пустой:

```python
record.scope in query.scopes
```

3. Если `query.required_tags` не пустой:

```python
set(record.tags) intersects set(query.required_tags)
```

4. Возвращаем записи в порядке от новых к старым.
5. Возвращаем максимум `query.limit` записей.

## Задание 35.3. Convenience-функция для store

Функция:

```python
def retrieve_feedback_from_store(
    query: FeedbackRetrievalQuery,
    store,
) -> list[HumanFeedbackRecord]:
    ...
```

Она должна:

```python
records = store.load_all()
return retrieve_feedback(query, records)
```

Store специально не типизируем жестко. Достаточно, чтобы у объекта был метод
`load_all()`.

## Задание 35.4. Форматирование для prompt

Пока planner не меняем, но подготовим функцию:

```python
def format_feedback_for_prompt(records: list[HumanFeedbackRecord]) -> str:
    ...
```

Правила:

- если records пустой, вернуть пустую строку;
- иначе вернуть текстовый блок;
- каждая запись должна содержать scope, summary, correction и tags;
- порядок записей сохранять таким, каким он пришел в функцию.

Пример:

```text
Previous human feedback:
1. [planner] Planner selected a fragile locator.
   Correction: Use label=Task for the task input.
   Tags: planner, locator
```

Эта функция понадобится в следующем уроке, когда будем подключать memory context к
planner prompt.

## Задание 35.5. Tests

Я добавил тесты:

```text
tests/test_feedback_retrieval.py
```

Сначала они будут падать. Это нормально.

Запуск:

```powershell
python -m pytest tests\test_feedback_retrieval.py -q
```

Потом:

```powershell
python -m pytest -q
```

## Критерий готовности

Урок завершен, когда:

- реализован `FeedbackRetrievalQuery`;
- `retrieve_feedback()` фильтрует по test case, scope, tags;
- результаты возвращаются от новых к старым;
- работает `limit`;
- работает `retrieve_feedback_from_store()`;
- работает `format_feedback_for_prompt()`;
- все тесты проходят.
