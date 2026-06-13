# Урок 1. Доменные модели агента

## Зачем начинать с моделей

Агентная система состоит из недетерминированной LLM и детерминированного кода.
Между ними нужен строгий контракт. Без него модель может вернуть `selector`
вместо `target`, забыть `value` или придумать неизвестное действие.

Pydantic выполняет роль границы:

```text
LLM output -> Pydantic validation -> trusted application code
```

Модель данных не должна выполнять браузерные действия или вызывать LLM.

## Задание

Реализуйте три модели в `src/browser_agent/models.py`.

### `TestCase`

Поля:

- `id: str`;
- `name: str`;
- `start_url: str`;
- `goal: str`;
- `test_data: dict[str, Any]`, по умолчанию пустой словарь;
- `expected: list[str]`, по умолчанию пустой список;
- `max_steps: int`, по умолчанию `20`, допустимо от `1` до `100`.

Для `id` разрешите латинские буквы, цифры, `_` и `-`.

### `BrowserAction`

Поля:

- `action`;
- `target: str | None`;
- `value: str | None`;
- `reason: str`.

Допустимые действия первого этапа:

- `click`;
- `fill`;
- `press`;
- `assert_text`;
- `finish`.

Правила:

- `click`, `fill`, `press`, `assert_text` требуют `target`;
- `fill` и `press` требуют `value`;
- неизвестное действие должно отклоняться.

Подумайте, чем лучше представить набор действий: `Literal` или `Enum`.

### `ActionResult`

Поля:

- `success: bool`;
- `url_before: str`;
- `url_after: str`;
- `error: str | None = None`;
- `screenshot_path: str | None = None`.

## Ограничения

- Не меняйте тесты, чтобы они проходили.
- Не добавляйте LangGraph и Playwright.
- Не используйте `dict` вместо моделей.
- Не делайте поля необязательными только ради прохождения тестов.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Готово, когда все тесты проходят.

После реализации пришлите сообщение «готово». На review мы обсудим:

1. `Literal` против `Enum`;
2. mutable defaults в Pydantic;
3. model-level validation;
4. почему `finish` пока не требует `success`;
5. как эти модели станут structured output для LangChain.
