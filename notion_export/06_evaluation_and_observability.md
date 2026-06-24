# Evaluation And Observability For AI Agents

## Почему evaluation критичен

AI-agent может:

- получить правильный финальный результат неправильным путем;
- пройти один раз и упасть на втором запуске;
- начать хуже работать после маленького prompt change;
- использовать memory, которая на самом деле вредит;
- пропустить баг из-за false positive Judge.

Поэтому вопрос не:

```text
Запустилось?
```

А:

```text
Как мы измерили качество?
```

## Уровни evaluation

### 1. Unit tests

Проверяют deterministic code:

- Pydantic validators;
- routers;
- JSONL stores;
- formatting functions;
- CLI parsers.

### 2. Component evaluation

Проверяет один LLM-компонент:

- Planner;
- Judge;
- Classifier;
- Reporter.

### 3. Graph integration tests

Проверяют wiring:

- nodes;
- edges;
- conditional routing;
- loop limits;
- failure paths.

### 4. End-to-end deterministic evaluation

Fake model + fake browser, но весь graph.

Цель:

```text
Проверить system behavior без внешней нестабильности.
```

### 5. Live evaluation

Real model + real browser + controlled fixture.

Цель:

```text
Проверить реальную интеграцию.
```

### 6. Production monitoring

Traces, metrics, human review, failure analytics.

## Planner evaluation

Planner отвечает за next action.

Reference:

```python
expected_action = BrowserAction(...)
```

Score:

```text
action_match
target_match
value_match
exact_match
```

Почему не только exact:

Если action правильный, но target wrong, это другой тип ошибки, чем wrong
action.

## Judge evaluation

Judge - pass/fail classifier.

Используй confusion matrix:

```text
TP: expected pass, judge pass
TN: expected fail, judge fail
FP: expected fail, judge pass
FN: expected pass, judge fail
```

Самый опасный случай:

```text
False Positive
```

Judge сказал "passed", хотя результат не доказан.

Для QA-агента это означает "пропустили баг".

## End-to-end metrics

Оценивай:

- final status;
- termination kind;
- step budget;
- failure count;
- recovery behavior;
- route length;
- bug report creation;
- screenshots/evidence.

Пример:

```python
exact_match = (
    status_match
    and termination_match
    and within_step_budget
    and recovery_match
)
```

## Memory evaluation

Для memory нужна отдельная оценка.

Сравнение:

```text
without memory
with memory
```

Вопросы:

- изменилось ли действие?
- стало ли действие правильнее?
- сократился ли route?
- уменьшились ли failures?
- не стала ли модель следовать нерелевантному feedback?

## Retrieval evaluation

Если есть RAG/semantic retrieval, оценивай retrieval отдельно.

Dataset:

```text
query
expected_relevant_feedback_ids
```

Metrics:

- precision@k;
- recall@k;
- MRR;
- hit@k;
- downstream task success.

Важно:

Хороший retrieval не гарантирует хороший final answer, но плохой retrieval почти
всегда ограничивает качество.

## Observability

Что нужно видеть в trace:

- input test case;
- prompt;
- model output;
- structured output;
- graph node sequence;
- state changes;
- browser action;
- screenshot path;
- judge verdict;
- termination reason;
- classification;
- memory records used;
- final report.

## LangSmith

LangSmith полезен для:

- traces;
- dataset experiments;
- model comparison;
- prompt comparison;
- latency/tokens/cost;
- debugging chain inputs/outputs.

Trace metadata должна включать:

```text
test_case_id
test_case_name
start_url
max_steps
max_failures
model_name
prompt_version
memory_enabled
```

## Golden datasets

Golden dataset - набор проверенных cases с reference outputs.

Примеры:

```text
planner_cases.json
judge_cases.json
end_to_end_cases.json
feedback_memory_cases.json
```

Правила:

- small but high quality;
- покрывать tricky cases;
- хранить reference outputs;
- обновлять осознанно;
- использовать в CI.

## Fake model testing

Fake model нужен, чтобы unit tests не зависели от LLM.

Пример:

```python
class FixedPlannerModel:
    def with_structured_output(self, schema):
        return RunnableLambda(lambda _: expected_action)
```

Для graph tests fake model должен обрабатывать разные schemas:

```python
if schema is BrowserAction:
    ...
if schema is JudgeVerdict:
    ...
if schema is FailureClassification:
    ...
```

## Controlled browser fixture

Внешние сайты нестабильны. Для eval нужен controlled fixture:

```text
examples/playwright_fixture.html
```

Плюсы:

- воспроизводимость;
- не зависит от интернета;
- понятный expected behavior;
- легко создавать edge cases.

## Infrastructure errors vs agent errors

Разделяй:

```text
agent chose wrong action
browser crashed
model unavailable
site unavailable
selector timeout
```

Не смешивай их в одну метрику.

## Minimal evaluation checklist

Для нового агента:

- [ ] Unit tests для domain models.
- [ ] Unit tests для routers.
- [ ] Fake model tests для graph.
- [ ] Component eval для planner.
- [ ] Component eval для verifier/judge.
- [ ] E2E deterministic test.
- [ ] Live smoke test.
- [ ] Trace metadata.
- [ ] Failure classification.
- [ ] Regression dataset.

## Evaluation anti-patterns

### "Я посмотрел trace, вроде норм"

Trace полезен для debug, но не заменяет dataset metrics.

### "Один успешный run"

Один run не показывает стабильность.

### "LLM judge проверит все"

LLM-as-judge тоже ошибается. Нужны trusted references.

### "У нас нет времени на eval"

Без eval ты не знаешь, улучшаешь систему или просто меняешь ее.

### "Exact match слишком строгий"

Иногда да. Но тогда добавь component metrics, а не отказывайся от оценки.

## Observability checklist

- [ ] Каждый run имеет run_id.
- [ ] Есть test_case_id в metadata.
- [ ] Есть model_name.
- [ ] Есть prompt_version.
- [ ] Есть route.
- [ ] Есть screenshots.
- [ ] Есть final report.
- [ ] Есть termination reason.
- [ ] Есть classification.
- [ ] Есть used memory ids.
- [ ] Есть infrastructure error logging.

## Как думать как AI engineer

На любое изменение спрашивай:

1. Что должно улучшиться?
2. Какая метрика это покажет?
3. Какой baseline?
4. Есть ли negative cases?
5. Можно ли объяснить regression?
6. Можно ли откатить изменение?
7. Какие traces нужно смотреть?
8. Какие данные сохранить?
