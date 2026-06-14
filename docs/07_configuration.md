# Конфигурация

## Файл .env

Скопируйте `.env.example` в `.env` и заполните:

```bash
# Модели Ollama
PLANNING_MODEL=qwen3.5:35b          # Планировщик и Observer (по умолчанию)
EXECUTION_MODEL=qwen3.5:35b         # Executor (по умолчанию)
GENERATION_MODEL=qwen2.5-coder:14b-instruct  # Генератор pytest-кода

# Контекст LLM
NUM_CTX=8192                        # Размер контекста (токены)
MAX_STEP_ITERATIONS=20              # Максимум итераций ReAct на один шаг

# Браузер
BROWSER_HEADLESS=false              # true — без окна браузера

# LangSmith (опционально)
LANGSMITH_API_KEY=lsv2_pt_...      # Ключ от langsmith.com
LANGCHAIN_PROJECT=website-testing-agent
```

## Модели Ollama

### qwen3.5:35b — основная модель
- Используется для: планировщика, executor, observer
- Размер: ~23 GB
- Установка: `ollama pull qwen3.5:35b`
- Особенности: генерирует `<think>` теги — система их удаляет через `/no_think` и `re.sub`

### qwen2.5-coder:14b-instruct — генератор кода
- Используется для: test_generator
- Размер: ~9 GB
- Установка: `ollama pull qwen2.5-coder:14b-instruct`
- Специализирован на генерации кода

## Параметры браузера

`BrowserManager.start()` запускает Chromium с:
```python
slow_mo=150          # 150ms задержка между действиями (для стабильности)
viewport=1280x720    # Разрешение
headless=False       # Видимое окно (по умолчанию)
default_timeout=10s  # Таймаут Playwright по умолчанию
```

## Структура директорий

```
UiBrowserAgent/
├── src/testing_agent/
│   ├── agents/
│   │   ├── planner.py         ← Планировщик
│   │   ├── executor.py        ← Исполнитель (ReAct)
│   │   ├── observer.py        ← Наблюдатель / аналитик
│   │   └── test_generator.py  ← Генератор pytest-кода
│   ├── tools/
│   │   └── browser_tools.py   ← 17 инструментов Playwright
│   ├── reporting/
│   │   └── allure_reporter.py ← Запись Allure JSON
│   ├── browser_manager.py     ← Синглтон браузера
│   ├── config.py              ← Модели и настройки
│   ├── graph.py               ← LangGraph StateGraph
│   ├── models.py              ← Pydantic-модели
│   └── state.py               ← AgentState TypedDict
├── test_cases/
│   ├── saucedemo/             ← 9 тест-кейсов
│   ├── the_internet/          ← 2 тест-кейса
│   └── automationexercise/    ← 11 тест-кейсов
├── generated_tests/           ← Сгенерированные pytest-тесты
│   └── conftest.py            ← Фикстуры
├── allure-results/            ← JSON для Allure (создаётся автоматически)
├── screenshots/               ← Скриншоты (создаётся автоматически)
├── run_tests.py               ← CLI-запускатель
├── demo.py                    ← Демо-скрипт
├── pyproject.toml             ← Зависимости
└── .env                       ← Секреты и настройки
```
