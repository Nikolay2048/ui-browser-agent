# LangChain And Structured Output

## LangChain в проекте

В проекте LangChain используется не как "магический агентный framework", а как
композиционный слой для prompt + model + structured output.

Основной паттерн:

```python
prompt = ChatPromptTemplate.from_messages([...])
structured_model = model.with_structured_output(BrowserAction)
chain = prompt | structured_model
result = chain.invoke({...})
```

## `ChatPromptTemplate`

`ChatPromptTemplate` описывает сообщения:

```python
ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Goal:\n{goal}\n\nCurrent page:\n{page_snapshot}")
])
```

Плейсхолдеры:

```text
{goal}
{page_snapshot}
```

заполняются при `.invoke()`.

## `prompt | structured_model`

Это LCEL composition.

Важно:

```text
prompt | structured_model не вызывает модель сразу
```

Это создает chain.

Вызов происходит здесь:

```python
chain.invoke({
    "goal": test_case.goal,
    "page_snapshot": page_snapshot,
})
```

Execution order:

```text
input dict
  -> prompt formats messages
  -> model receives messages
  -> model returns structured output
  -> Pydantic object returned to code
```

## `.invoke()`

`.invoke()` - синхронный вызов Runnable.

Его можно применять к:

- prompt templates;
- models;
- composed chains;
- `RunnableLambda`;
- graph/runnable wrappers.

Он не "просто работает с историей сообщений". Он передает input конкретному
Runnable, а тот решает, что делать.

Для prompt:

```python
prompt.invoke({"goal": "Login"})
```

вернет prompt value/messages.

Для chain:

```python
(prompt | model).invoke({"goal": "Login"})
```

сначала форматирует prompt, потом вызывает model.

## `with_structured_output`

`model.with_structured_output(Schema)` говорит модели:

```text
Верни ответ, совместимый с этой структурой.
```

В зависимости от provider это может использовать:

- tool calling;
- JSON schema;
- function calling;
- provider-specific structured mode;
- output parser.

В коде:

```python
structured_model = model.with_structured_output(BrowserAction)
```

Результат:

```python
BrowserAction(...)
```

а не raw string.

## Почему structured output обязателен для tools

Executor ожидает:

```python
action.action
action.target
action.value
```

Если LLM вернет:

```text
Click the Add button
```

код не знает надежно:

- какой action type;
- какой target strategy;
- нужно ли value;
- есть ли reason.

Structured output превращает LLM answer в typed contract.

## Prompt design для UI planner

Planner prompt должен:

1. объяснить роль;
2. ограничить output одним действием;
3. описать target language;
4. запретить выдумывать элементы;
5. объяснить, что snapshot syntax не target;
6. показать examples;
7. дать runtime context;
8. сказать, когда finish.

Пример важного правила:

```text
The accessibility snapshot syntax is descriptive and is not a valid target.
Never copy snapshot entries directly into target.
```

Почему:

Snapshot может содержать:

```text
textbox "Task"
```

Но target должен быть:

```json
{"strategy": "label", "value": "Task"}
```

## System prompt vs human prompt

System prompt:

- постоянные правила;
- role;
- output contract;
- safety constraints;
- examples target language.

Human prompt:

- goal;
- test data;
- expected results;
- execution history;
- memory context;
- current page snapshot.

Практическое правило:

```text
Stable rules -> system
Runtime data -> human
```

## Current page в конце prompt

Порядок:

```text
Goal
Test data
Expected results
Previous human feedback
Execution history
Current page
```

Почему `Current page` в конце:

- это самый свежий runtime context;
- snapshot должен перебивать старую memory;
- planner выбирает действие из того, что видно сейчас;
- уменьшает риск следовать устаревшему feedback.

## Fake models в тестах

Чтобы не вызывать Ollama в unit tests:

```python
class FakeModel:
    def with_structured_output(self, schema):
        return RunnableLambda(lambda prompt: BrowserAction(...))
```

Плюсы:

- fast tests;
- deterministic behavior;
- можно проверять prompt text;
- можно симулировать разные schemas.

Осторожно:

Fake model не должна случайно матчить examples из system prompt.

Если нужно читать текущую страницу:

```python
prompt_text = prompt_value.to_string()
current_page = prompt_text.rsplit("Current page:", 1)[-1]
```

## Multi-role model

В тестах часто fake model делает:

```python
if schema is JudgeVerdict:
    return JudgeVerdict(...)
if schema is BrowserAction:
    return BrowserAction(...)
```

Почему:

Один model object может использоваться в planner, judge, classifier, reporter.

Типичная ошибка:

Не обработать schema для classifier, и fake model вернет `BrowserAction` там,
где graph ждет `FailureClassification`.

## Prompt testing

Что полезно проверять:

- prompt содержит goal;
- prompt содержит expected;
- prompt содержит page_snapshot;
- prompt содержит execution history;
- prompt содержит memory_context;
- prompt содержит target language rules;
- prompt запрещает invalid targets.

Пример:

```python
assert "No previous human feedback is available." in model.prompt_text
```

## Когда использовать LangChain

Используй LangChain, если нужно:

- prompt templates;
- model abstraction;
- structured output;
- runnable composition;
- LangSmith integration.

Не обязательно использовать LangChain для:

- обычной бизнес-логики;
- deterministic routing;
- JSONL persistence;
- simple CLI;
- domain validation.

## Типичные ошибки

### Считать LangChain агентом сам по себе

LangChain - toolkit. Архитектуру все равно проектируешь ты.

### Писать огромный prompt вместо схемы

Если можно описать контракт Pydantic-моделью, лучше сделать это.

### Смешивать runtime data и static rules

Не надо hardcode-ить test case в system prompt.

### Игнорировать output validation errors

Validation error - сигнал, что prompt/schema/model не согласованы.

### Не иметь fake model tests

Если каждый тест вызывает реальную LLM, разработка станет медленной и нестабильной.

## Checklist для LLM-компонента

- [ ] Есть Pydantic output schema.
- [ ] Есть отдельный system prompt.
- [ ] Runtime context передается через template variables.
- [ ] Есть unit tests без реальной модели.
- [ ] Есть tests на prompt content.
- [ ] Есть component evaluation dataset.
- [ ] Ошибки schema валидируются.
- [ ] Output не выполняется напрямую как код.
- [ ] Есть reason/evidence поле, если нужна объяснимость.
- [ ] Есть versioning plan для prompt.
