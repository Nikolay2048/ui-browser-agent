# Отчётность: Allure и LangSmith

## Allure

### Как работает

Система пишет Allure-результаты **напрямую** в формате JSON, без allure-pytest. Это позволяет публиковать результаты от агентского запуска (не pytest-сессии).

После каждого тест-кейса `allure_reporter.py` создаёт файлы в `allure-results/`:

```
allure-results/
├── {uuid}-result.json          ← Основной результат тест-кейса
├── {uuid}-result.json          ← Отдельный результат на каждый баг [BUG-HIGH]
├── {uuid}-attachment.png       ← Скриншоты
├── {uuid}-attachment.json      ← Список баг-репортов (JSON)
├── {uuid}-attachment.py        ← Сгенерированный pytest-код
├── {uuid}-attachment.md        ← Рассуждения планировщика
├── {uuid}-attachment.md        ← Рассуждения аналитика (Observer)
└── {uuid}-attachment.md        ← Запросы уточнений (если есть)
```

### Что видно в отчёте

**Основной тест:**
- Статус: passed / failed / broken
- Severity и теги
- Каждый шаг с expected/actual параметрами
- Скриншот после каждого действия
- Лог вызванных инструментов (agent tool calls)

**Вложения к тесту:**
- `Bug Reports (N found)` — JSON с полными баг-репортами
- `Generated Playwright test` — готовый pytest-код
- `Рассуждения планировщика` — markdown с объяснением стратегии
- `Рассуждения аналитика (Observer)` — markdown с анализом результатов
- `Clarification Requests` — вопросы к тест-кейсу (если нужны)

**Баги как отдельные записи:**
Каждый найденный баг создаётся как отдельный тест-результат с именем `[BUG-HIGH] Название бага`. В секции Allure они выглядят как упавшие тесты с описанием шагов воспроизведения.

### Запуск Allure

```bash
# Запустить сервер (открывает браузер автоматически)
& "C:\Program Files\allure-2.42.1\bin\allure.bat" serve allure-results

# Сгенерировать статичный отчёт
& "C:\Program Files\allure-2.42.1\bin\allure.bat" generate allure-results -o allure-report
```

### Очистка результатов

```bash
# Удалить все результаты перед новым прогоном
Remove-Item -Recurse -Force allure-results
```

---

## LangSmith

LangSmith — платформа для трассировки LLM-вызовов. Позволяет видеть:
- Какие сообщения отправлялись в LLM
- Что LLM ответил
- Дерево вызовов инструментов
- Токены и задержки

### Настройка

В файле `.env`:
```
LANGSMITH_API_KEY=lsv2_pt_xxxxxxxx...
LANGCHAIN_PROJECT=website-testing-agent
```

Если ключ начинается с `your_` — трассировка отключается автоматически (защита от случайной утечки).

### Что трассируется

- Каждый вызов LLM в planner, executor, observer, test_generator
- Tool calls с аргументами и результатами
- ReAct-цикл executor как последовательность сообщений
- Вложенные узлы графа LangGraph

---

## Скриншоты

Сохраняются в `screenshots/` и копируются в `allure-results/` при формировании отчёта.

Executor делает скриншоты:
- По указанию планировщика (после важных шагов)
- При вызове `mark_step_complete(screenshot_name=...)` — финальный скриншот шага
- По собственному решению LLM (вызов `take_screenshot`)

---

## Сгенерированные тесты

Файлы в `generated_tests/test_{id}.py` — это **воспроизводимые pytest-тесты**. Их можно запустить отдельно:

```bash
# Запустить сгенерированный тест
pytest generated_tests/test_tc_01.py --alluredir=allure-results

# Запустить все сгенерированные тесты
pytest generated_tests/ --alluredir=allure-results
```

Для этого нужен `generated_tests/conftest.py` с фикстурами `browser` и `page`.
