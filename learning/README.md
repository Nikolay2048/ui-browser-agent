# Архив учебных уроков

Каталог `learning` хранит код каждого пройденного этапа отдельно от текущей
реализации агента. Благодаря этому старые примеры не смешиваются с новым
заданием.

## Что означают файлы

- `README.md` — теория и формулировка задания.
- `completed.py` — код, получившийся после выполнения урока.
- `test_completed.py` — тесты этого этапа.
- `*_snapshot.py` — снимок связанной модели или состояния на момент урока.
- `starter.py` — стартовый шаблон ещё не завершённого урока.
- `test_assignment.py` — условия, которые должна выполнить самостоятельная работа.

## Карта уроков

| Урок | Тема | Сохранённый Python-код |
|---|---|---|
| 01 | Pydantic-модели | `completed.py`, `test_completed.py` |
| 02 | Состояние и первый граф | `completed.py`, `state_snapshot.py`, `test_completed.py` |
| 03 | Условный роутинг | `completed.py`, `test_completed.py` |
| 04 | Цикл агента | `completed.py`, `test_completed.py` |
| 05 | LLM planner | `completed.py`, `models_snapshot.py`, `smoke_planner.py`, `test_completed.py` |
| 06 | Planner как нода | `completed.py`, `state_snapshot.py`, `test_completed.py` |
| 07 | Executor | `completed.py`, `state_snapshot.py`, `test_completed.py` |
| 08 | Plan-execute граф | `completed.py`, `test_completed.py` |
| 09 | Observer | `completed.py`, `observer_completed.py`, два файла тестов |
| 10 | Автономный цикл | `starter.py`, `completed.py`, `test_assignment.py` |
| 11 | Трасса выполнения | снимки моделей, state и executor |
| 12 | Playwright adapter | `completed.py` |
| 13 | Реальный UI-агент | снимки planner contract и runner |
| 14 | Память planner-а | `completed.py` |
| 15 | Независимый Judge | `completed.py` |
| 16 | Типизированные browser targets | `completed.py` |
| 17 | Ограниченное восстановление | `completed.py` |
| 18 | Причина завершения | `completed.py` |
| 19 | Failure Classifier | `completed.py` |
| 20 | Bug Reporter | `completed.py` |
| 21 | RunReport, JSON и Markdown | `completed.py` |
| 22 | LangSmith observability | `completed.py` |
| 23 | Checkpointing и thread_id | `completed.py` |
| 24 | Human-in-the-loop: interrupt и resume | `completed.py` |
| 25 | Policy-based approval | `completed.py` |
| 26 | Evaluation Planner | `completed.py` |
| 27 | Evaluation Judge | `completed.py` |
| 28 | Production package architecture | `completed.py` |
| 29 | End-to-end evaluation | deterministic model, fake browser, полный граф |
| 30 | Live end-to-end evaluation | Ollama, Playwright, повторные полные запуски |
| 31 | Долговременная история запусков | `src/browser_agent/run_history.py`, `tests/test_run_history.py` |
| 32 | Подключение истории к runner | `src/browser_agent/runner.py`, `tests/test_runner_history.py` |
| 33 | Human feedback records | текущее задание в `src/browser_agent/feedback.py` |

## Где писать новый код

Архивные файлы нужны для чтения и сравнения. Обычный `pytest` их не запускает,
а рабочий агент их не импортирует.

Текущая реализация находится в:

```text
src/browser_agent/
```

Текущий код урока 33 находится в:

```text
src/browser_agent/feedback.py
tests/test_feedback.py
```

Теория и критерии выполнения находятся в
`learning/lesson_33_human_feedback_records/README.md`.

Старые примеры отражают структуру проекта на соответствующем этапе обучения.
Поэтому некоторые из них могут не запускаться напрямую с текущей версией
остальных модулей. Это снимки развития проекта, а не часть рабочего приложения.
