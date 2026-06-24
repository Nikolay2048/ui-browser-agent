# Runbook

## Установка

```powershell
python -m pip install -e ".[dev]"
playwright install chromium
```

Если используется conda:

```powershell
conda activate UiBrowserAgent
python -m pip install -e ".[dev]"
playwright install chromium
```

## Переменные окружения

Локальные значения хранятся в `.env`.

Минимально:

```text
OLLAMA_MODEL=qwen3.5:35b
```

Для LangSmith:

```text
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=ui-browser-agent-dev
```

`.env` не коммитится.

## Тесты

Полный прогон:

```powershell
python -m pytest -q
```

Точечные группы:

```powershell
python -m pytest tests\test_planner.py -q
python -m pytest tests\test_graph.py -q
python -m pytest tests\test_runner_feedback_memory.py -q
python -m pytest tests\test_feedback_retrieval.py -q
```

Чтобы временные файлы не смешивались:

```powershell
python -m pytest -q --basetemp=.pytest-tmp-final
```

`.pytest-tmp*` можно удалять. Это временные pytest directories.

## Запуск реального агента

Видимый Chromium:

```powershell
python scripts\run_real_agent.py
```

Что происходит:

1. Загружается `.env`;
2. создается `ChatOllama`;
3. открывается `examples/playwright_fixture.html`;
4. запускается LangGraph agent;
5. печатаются промежуточные states;
6. сохраняются screenshots;
7. сохраняется report;
8. сохраняется run history;
9. подключается feedback memory, если есть feedback file.

## Запуск с demo feedback

Коммитабельный пример:

```text
examples/feedback/first-real-agent.feedback.jsonl
```

Запуск:

```powershell
python scripts\run_real_agent.py --feedback-path examples\feedback\first-real-agent.feedback.jsonl
```

Это позволяет показать memory pipeline без локального `artifacts/feedback`.

## Добавить локальный feedback

```powershell
python scripts\add_feedback.py `
  --run-id "manual-seed" `
  --test-case-id first-real-agent `
  --scope planner `
  --summary "Planner should use stable locator for the task input." `
  --correction 'For the task input, prefer label=Task.' `
  --tags planner,locator
```

По умолчанию запись попадет в:

```text
artifacts/feedback/feedback.jsonl
```

PowerShell warning:

Если в тексте нужны двойные кавычки, проще использовать одинарные кавычки вокруг
всей строки:

```powershell
--correction 'Use textbox "Task" only as observation, not as target.'
```

В PowerShell `\"` не работает как в bash.

## Просмотр артефактов

После запуска:

```text
artifacts/
  first-real-agent/
    step-001.png
    step-002.png
    report/
      first-real-agent.json
      first-real-agent.md
  run-history/
    runs.jsonl
  feedback/
    feedback.jsonl
```

`artifacts/` не коммитится.

## Примеры, которые можно коммитить

```text
examples/
  playwright_fixture.html
  feedback/
    first-real-agent.feedback.jsonl
```

Правило:

```text
examples/   reproducible demo inputs
artifacts/  local runtime outputs
```

## Evaluation scripts

Planner:

```powershell
python scripts\evaluate_planner.py
python scripts\run_planner_experiment.py
```

Judge:

```powershell
python scripts\evaluate_judge.py
python scripts\run_judge_experiment.py
```

End-to-end:

```powershell
python scripts\evaluate_end_to_end.py
python scripts\evaluate_live_end_to_end.py --repeat 3 --slow-mo 100
```

## Upload LangSmith datasets

```powershell
python scripts\upload_planner_dataset.py
python scripts\upload_judge_dataset.py
```

## Human approval run

```powershell
python scripts\run_agent_with_approval.py
```

Этот сценарий демонстрирует LangGraph interrupt/resume.

## Troubleshooting

### `ModuleNotFoundError: browser_agent`

Запусти из корня проекта:

```powershell
python -m pip install -e ".[dev]"
```

### Playwright не найден

```powershell
python -m pip install playwright
playwright install chromium
```

### Ollama model not found

Проверь:

```powershell
ollama list
```

И переменную:

```powershell
$env:OLLAMA_MODEL="qwen3.5:35b"
```

### Feedback не попадает в prompt

Проверь:

- `test_case_id` должен совпадать с `first-real-agent`;
- scope должен быть `planner` или `step`;
- файл передан через `--feedback-path` или лежит в `artifacts/feedback/feedback.jsonl`;
- JSONL должен быть валидным.

### В PowerShell ломаются кавычки

Используй одинарные кавычки вокруг длинного текста:

```powershell
--correction 'Prefer label=Task.'
```

### `.pytest_cache` permission warning

Если тесты проходят, warning можно игнорировать. Это проблема записи cache, а не
логики проекта.

## Команды финальной проверки

```powershell
python scripts\run_real_agent.py --help
python -m pytest -q
```

Если установлен Playwright/Ollama:

```powershell
python scripts\run_real_agent.py --feedback-path examples\feedback\first-real-agent.feedback.jsonl
```
