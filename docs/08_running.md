# Запуск системы

## Предварительные требования

```bash
# 1. Установить зависимости Python
pip install -e .

# 2. Установить браузер Playwright
playwright install chromium

# 3. Запустить Ollama с нужными моделями
ollama pull qwen3.5:35b
ollama pull qwen2.5-coder:14b-instruct

# 4. Проверить что Ollama запущен
ollama list

# 5. Заполнить .env (скопировать из .env.example)
cp .env.example .env
```

## run_tests.py — основной запуск

```bash
# Один тест-кейс
python run_tests.py test_cases/saucedemo/tc_01_login_valid.yaml

# Несколько файлов
python run_tests.py test_cases/saucedemo/tc_01_login_valid.yaml \
                    test_cases/saucedemo/tc_02_login_invalid.yaml

# Целая папка
python run_tests.py test_cases/saucedemo/

# Вся библиотека
python run_tests.py test_cases/

# Headless-режим (без окна браузера)
python run_tests.py test_cases/saucedemo/ --headless

# По паттерну
python run_tests.py test_cases/ --pattern "tc_ae_*.yaml"
```

### Вывод в консоль

```
=================================================================
TC: [tc_01] Успешный вход — стандартный пользователь
URL: https://www.saucedemo.com/
Steps: 4 | Severity: CRITICAL
-----------------------------------------------------------------
  [Planner] 18 actions | Стратегия: навигация → проверка формы → ...
  Step 1 [PASSED] Перейти на страницу входа (13703ms)
  Step 2 [PASSED] Ввести стандартный пользователь и пароль (12118ms)
  Step 3 [PASSED] Нажать кнопку Login (11954ms)
  Step 4 [PASSED] Проверить страницу Products (7468ms)
  [Observer] Все шаги прошли успешно...
  Observer: PASSED | 0 bug(s) | clarification=not needed
  Generated test: generated_tests/test_tc_01.py
  Allure result: 31f258c6-...-result.json
-----------------------------------------------------------------
RESULT: PASSED  (249.6s)
Steps:  18 executed | 18 passed / 0 failed
Bugs:   0 found
```

## demo.py — демо-запуск

```bash
# Полная демонстрация (14 тест-кейсов, ~60-90 мин)
python demo.py

# Быстрая демо (5 кейсов, ~15-20 мин)
python demo.py --quick

# Только один сайт
python demo.py --site sd   # SauceDemo
python demo.py --site ae   # AutomationExercise
python demo.py --site ti   # The Internet

# Без открытия Allure в конце
python demo.py --quick --no-allure

# Headless
python demo.py --quick --headless
```

demo.py отличается от run_tests.py:
- Красивый баннер с описанием системы
- Группировка по сайтам
- Итоговая сводка
- Автоматическое открытие Allure-отчёта по завершении

## Просмотр отчёта

```bash
# Запустить Allure-сервер (открывает браузер)
& "C:\Program Files\allure-2.42.1\bin\allure.bat" serve allure-results

# Остановить — Ctrl+C в терминале
```

## Типичное время выполнения

| Кейс | Шагов | Время |
|------|-------|-------|
| tc_01 (вход) | 4 | ~4 мин |
| tc_04 (чекаут, 8 шагов) | 8 | ~8-10 мин |
| tc_ae_11 (сквозной, 13 шагов) | 13 | ~15-20 мин |

Основное время — работа LLM. qwen3.5:35b на CPU генерирует ~5-15 токенов/сек.

## Отладка

```bash
# Посмотреть что происходит — запустите без --headless (по умолчанию)
# Браузер будет виден на экране

# Включить LangSmith трассировку — добавьте в .env:
LANGSMITH_API_KEY=lsv2_pt_...
# Затем откройте https://smith.langchain.com

# Проверить что Ollama отвечает:
ollama run qwen3.5:35b "Say hello"
```

## Часто встречающиеся проблемы

**Planner уходит в fallback:**
- Признак: в логе `[Planner] using minimal fallback plan`
- Причина: LLM вернул некорректный JSON
- Следствие: система всё равно работает, но с менее детальным планом

**Шаг завершился со статусом broken:**
- Причина: LLM не вызвал `mark_step_complete` за 20 итераций
- Что делать: увеличить `MAX_STEP_ITERATIONS=30` в `.env`

**Браузер не открывается:**
- Проверьте: `playwright install chromium`
- Проверьте антивирус / файервол

**Allure не запускается:**
- Путь: `C:\Program Files\allure-2.42.1\bin\allure.bat`
- Убедитесь что Java установлена (Allure требует JRE 8+)
