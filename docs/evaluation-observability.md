# Evaluation And Observability

## Почему evaluation важен для AI-агентов

Агентные системы недетерминированы сильнее обычного кода:

- LLM может изменить ответ;
- prompt может неожиданно повлиять на поведение;
- browser timing может флакать;
- внешний сайт может измениться;
- route может стать длиннее или короче;
- Judge может ошибиться.

Поэтому "один раз запустил и увидел, что работает" недостаточно.

В проекте evaluation строилась постепенно:

```text
unit tests
  -> component evaluation
  -> end-to-end deterministic evaluation
  -> live Playwright evaluation
  -> LangSmith datasets/experiments
```

## Pytest как базовая защита

Проект покрыт большим набором тестов:

- domain model validation;
- planner prompt/structured output;
- executor behavior;
- graph routing;
- recovery limits;
- judge;
- classifier;
- reporter;
- reporting;
- persistence;
- feedback;
- retrieval;
- runner integrations.

Почему это важно:

- можно менять prompt и видеть regressions;
- можно менять graph wiring и ловить broken edges;
- можно тестировать без реального Ollama/Playwright;
- можно учиться через failing tests.

## Deterministic fakes

Большинство тестов не используют реальную модель.

Пример fake model:

```python
class PromptRecordingModel:
    def with_structured_output(self, schema):
        return RunnableLambda(respond)
```

Зачем:

- unit tests быстрые;
- нет зависимости от локальной модели;
- можно точно проверить prompt content;
- можно симулировать разные schema outputs.

Типичная ошибка:

Fake model читает весь prompt и случайно матчится на examples из system prompt.
В проекте это реально случилось: fake model искала `textbox "Task"` во всем
prompt, а эта строка была в instructions. Правильнее читать только блок
`Current page`.

## Planner Evaluation

Файл:

```text
src/browser_agent/evaluation/planner.py
```

Planner evaluation case:

```python
class PlannerEvaluationCase(BaseModel):
    id: str
    test_case: TestCase
    page_snapshot: str
    route: list[ExecutionStep]
    expected_action: BrowserAction
```

Метрики:

- `action_match`;
- `target_match`;
- `value_match`;
- `exact_match`;
- `score`.

Зачем:

Planner можно оценивать отдельно от browser и graph.

Пример вопроса:

```text
При snapshot "- textbox Username - button Login"
должен ли planner выбрать fill Username?
```

Альтернативы:

- только end-to-end tests;
- ручной просмотр traces;
- LLM-as-judge evaluation.

Почему component evaluation полезен:

Если полный агент ошибся, нужно понимать, где ошибка:

- planner выбрал wrong action;
- executor не выполнил action;
- judge неверно оценил;
- graph неправильно routed.

## Judge Evaluation

Файл:

```text
src/browser_agent/evaluation/judge.py
```

Judge - это классификатор pass/fail, поэтому используются:

- true positive;
- true negative;
- false positive;
- false negative;
- accuracy;
- precision;
- recall;
- false positive rate;
- false negative rate.

Почему false positive опасен:

Judge сказал "passed", хотя expected result не доказан. Для тестирующего агента
это хуже, чем false negative, потому что система пропускает баг.

## End-To-End Evaluation

Файл:

```text
src/browser_agent/evaluation/end_to_end.py
```

E2E expectation:

```python
class EndToEndExpectation(BaseModel):
    status: Literal["passed", "failed"]
    max_steps: int
    termination_kind: TerminationKind
    expects_recovery: bool = False
```

Метрики:

- status match;
- termination match;
- within step budget;
- recovery observed/match;
- exact match;
- average steps;
- average failures.

Зачем:

Полезно знать не только "прошел/не прошел", но и:

- уложился ли агент в budget;
- правильная ли причина завершения;
- было ли восстановление после ошибки;
- не стал ли route неоправданно длинным.

## Live End-To-End Evaluation

Файл:

```text
scripts/evaluate_live_end_to_end.py
```

Запускает реальный:

- Ollama model;
- Playwright browser;
- controlled local fixture.

Почему controlled fixture:

Внешние сайты меняются. Для базовой оценки лучше иметь стабильный HTML fixture:

```text
examples/playwright_fixture.html
```

Live evaluation отличает:

- model/agent behavior;
- infrastructure errors.

Это важно: если браузер не открылся, это не значит, что planner стал хуже.

## LangSmith Observability

Файл:

```text
src/browser_agent/observability.py
```

Trace config:

```python
{
    "run_name": f"ui-test:{test_case.id}",
    "tags": ["browser-agent", "ui-test"],
    "metadata": {
        "test_case_id": test_case.id,
        "test_case_name": test_case.name,
        "start_url": test_case.start_url,
        "max_steps": test_case.max_steps,
        "max_failures": test_case.max_failures,
    },
}
```

Зачем metadata:

- искать traces по test case;
- сравнивать runs;
- видеть модель и сценарий;
- строить experiments.

## LangSmith Experiments

Скрипты:

```text
scripts/run_planner_experiment.py
scripts/run_judge_experiment.py
```

Dataset scripts:

```text
scripts/upload_planner_dataset.py
scripts/upload_judge_dataset.py
```

Что изучалось:

- datasets;
- reference outputs;
- code evaluators;
- experiment comparison;
- latency/tokens/cost в LangSmith UI.

## Checkpoint Observability

Файлы:

```text
persistence.py
run_real_agent.py
```

После запуска можно получить:

```python
snapshot = checkpoint_graph.get_state(config)
```

И посмотреть:

```text
checkpoint thread
checkpoint status
checkpoint next
```

Это полезно для:

- debugging graph state;
- human-in-the-loop;
- understanding interrupted workflows.

## Что еще стоит добавить

### Memory evaluation

Следующий логичный evaluation:

```text
same case without feedback memory
same case with feedback memory
compare action/route/result
```

Зачем:

Память не должна считаться полезной "на глаз". Нужно измерять.

### Used feedback ids

Сейчас report не сохраняет, какие feedback records использовались.

В production нужно:

```text
used_feedback_ids
memory_context_hash
retrieval_query
```

Зачем:

- объяснимость;
- debugging;
- rollback плохой подсказки;
- evaluation.

### Prompt versioning

Prompt менялся много раз. Для production стоит версионировать:

- planner prompt version;
- judge prompt version;
- reporter prompt version;
- memory prompt version.

### Regression datasets

Нужны datasets:

- planner locator cases;
- judge false positive cases;
- recovery cases;
- feedback memory cases;
- bug reporting cases.

## Типичные ошибки evaluation

### Оценивать только финальный статус

Агент может пройти тест, но сделать 15 лишних шагов. Поэтому нужны step budget и
route metrics.

### Смешивать component и E2E evaluation

Если E2E failed, причина может быть в любом слое. Component evaluation помогает
локализовать.

### Не фиксировать reference outputs

Без reference невозможно понять, улучшилась модель или просто изменилась.

### Использовать только live external websites

Внешний сайт меняется. Нужен controlled fixture.

### Не отделять infrastructure errors

Падение браузера, сети или окружения не должно портить метрику модели.

### Не проверять dangerous false positives

Для UI testing judge false positive особенно опасен: баг пропущен.
