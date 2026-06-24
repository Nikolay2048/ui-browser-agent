# Common Mistakes In AI Agent Projects

## 1. Начинать с prompt вместо контрактов

Симптом:

```text
У нас есть большой prompt, но непонятно, какие данные входят и выходят.
```

Проблема:

- трудно тестировать;
- LLM output нестабилен;
- downstream code парсит строки;
- ошибки обнаруживаются поздно.

Правильно:

```text
Pydantic models -> prompt -> structured output
```

## 2. Давать LLM выполнять side effects напрямую

Плохо:

```text
LLM генерирует Python/Playwright код, приложение выполняет его.
```

Риски:

- prompt injection;
- небезопасные действия;
- невалидный код;
- нет allowlist;
- трудно audit.

Правильно:

```text
LLM proposes structured action.
Executor performs allowed action.
```

## 3. Путать snapshot syntax и target language

Snapshot:

```text
textbox "Task"
button "Add"
```

Target:

```json
{"strategy": "label", "value": "Task"}
{"strategy": "role", "value": "button", "name": "Add"}
```

Ошибка:

```json
{"target": "textbox \"Task\""}
```

Решение:

Prompt examples + Pydantic `BrowserTarget`.

## 4. Мутировать state в LangGraph node

Плохо:

```python
state["route"].append(step)
return {"route": state["route"]}
```

Почему плохо:

- hidden side effect;
- сложнее checkpoint/replay;
- тесты могут зависеть от порядка;
- труднее debugging.

Правильно:

```python
return {"route": [*state["route"], step]}
```

## 5. Делать router с side effects

Плохо:

```python
def route(state):
    browser.click(...)
    return "observe"
```

Router должен только выбирать путь.

Правильно:

```python
def route(state):
    return "observe" if state["last_result"].success else "fail_run"
```

## 6. Доверять Planner `finish`

Planner может решить, что задача выполнена, но это не доказательство.

Правильно:

```text
planner returns finish
  -> judge verifies expected results
  -> pass/fail
```

## 7. Смешивать Planner и Judge

Плохо:

```text
Одна модель выбирает действия и сама себя проверяет.
```

Риск:

Self-confirmation bias.

Правильно:

```text
Planner proposes.
Judge verifies independently.
```

## 8. Не ограничивать agent loop

Без лимитов агент может повторять действие бесконечно.

Минимум:

```text
max_steps
max_failures
timeout
```

## 9. Считать successful click доказательством успеха

Click success значит:

```text
браузер смог нажать
```

Но не значит:

```text
бизнес-результат достигнут
```

Нужен Judge/evidence.

## 10. Хранить feedback только в prompt

Плохо:

```text
После ошибки добавляем еще одно правило в system prompt.
```

Проблемы:

- prompt разрастается;
- нельзя искать;
- нельзя измерять;
- нельзя удалить точечно.

Правильно:

```text
HumanFeedbackRecord -> store -> retrieval -> memory_context
```

## 11. Передавать всю память в prompt

Память без retrieval становится шумом.

Правильно:

```text
retrieve top relevant records
limit 3-5
format compactly
```

## 12. Делать RAG без baseline evaluation

RAG может:

- улучшить;
- не повлиять;
- ухудшить.

Без baseline ты не узнаешь.

Правильно:

```text
deterministic retrieval baseline
semantic retrieval experiment
compare metrics
```

## 13. Использовать только live external websites для eval

Внешний сайт меняется.

Правильно:

```text
controlled fixture first
staging site second
external site last
```

## 14. Не отделять infrastructure errors

Ошибки разные:

```text
model returned wrong action
browser crashed
site unavailable
network failed
selector timed out
```

Нельзя считать их одной метрикой.

## 15. Fake model читает весь prompt

Ошибка из проекта:

Fake model искала:

```python
if 'textbox "Task"' in prompt_text:
```

Но строка была в system prompt examples. Модель всегда выбирала fill.

Правильно:

```python
current_page = prompt_text.rsplit("Current page:", 1)[-1]
```

## 16. Не обрабатывать все schemas в fake model

Graph может вызвать model как:

- Planner -> `BrowserAction`;
- Judge -> `JudgeVerdict`;
- Classifier -> `FailureClassification`;
- Reporter -> `BugReport`.

Fake model должна учитывать schema.

## 17. Смешивать runtime artifacts и examples

Плохо:

```text
commit artifacts/
```

Правильно:

```text
artifacts/  ignored runtime outputs
examples/   reproducible demo inputs
```

## 18. Писать всю CLI-логику в script

Плохо:

```text
scripts/add_feedback.py содержит parser, validation, save logic
```

Правильно:

```text
src/app/cli.py       testable logic
scripts/add_*.py     thin entrypoint
```

## 19. Делать premature abstraction

Не надо сразу строить огромный generic repository.

Сначала:

```text
JsonlRunHistoryStore
JsonlFeedbackStore
```

Когда duplication станет болезненной, выделить helper.

## 20. Не сохранять route/evidence

Без route нельзя:

- воспроизвести ошибку;
- написать bug report;
- понять, где агент ошибся;
- обучить feedback.

Каждый step должен иметь:

```text
step_number
page_snapshot
action
result
screenshot
```

## 21. Делать safety через LLM-only

Плохо:

```text
Ask model if action is dangerous.
```

Лучше:

```text
deterministic policy
human approval
allowlist/denylist
audit log
```

## 22. Не версионировать prompts

Если prompt поменялся, evaluation results тоже поменяются.

Нужно:

```text
planner_prompt_version
judge_prompt_version
reporter_prompt_version
```

## 23. Не сохранять used memory ids

Если агент ошибся из-за feedback, нужно знать какой feedback был использован.

Добавить в будущем:

```text
used_feedback_ids
retrieval_query
memory_context_hash
```

## 24. Делать "агента" вместо системы

Плохой mental model:

```text
Нужен умный LLM.
```

Хороший mental model:

```text
Нужна система: contracts + graph + tools + memory + eval + safety.
```

## 25. Не документировать решения

Через месяц непонятно, почему:

- Current page в конце prompt;
- runner подключает memory;
- Judge отдельный;
- JSONL выбран для history.

Решение:

Писать ADR/notes.

## Debug checklist

Когда агент ошибся:

1. Какой был input TestCase?
2. Какой page_snapshot видел planner?
3. Какой prompt ушел модели?
4. Какой structured output вернулся?
5. Прошел ли Pydantic validation?
6. Как executor выполнил action?
7. Какой screenshot?
8. Что в route?
9. Почему router выбрал эту ветку?
10. Что сказал Judge?
11. Какая termination reason?
12. Какая classification?
13. Был ли memory_context?
14. Какие feedback records использовались?
15. Это model error, automation error или product bug?
