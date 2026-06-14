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
| 11 | Трасса выполнения | текущее задание в рабочем коде |

## Где писать новый код

Архивные файлы нужны для чтения и сравнения. Обычный `pytest` их не запускает,
а рабочий агент их не импортирует.

Текущая реализация находится в:

```text
src/browser_agent/
```

Текущее задание урока 11 выполняется в:

```text
src/browser_agent/models.py
src/browser_agent/state.py
src/browser_agent/executor.py
```

Основные тесты задания находятся в:

```text
tests/test_execution_trace.py
```

Старые примеры отражают структуру проекта на соответствующем этапе обучения.
Поэтому некоторые из них могут не запускаться напрямую с текущей версией
остальных модулей. Это снимки развития проекта, а не часть рабочего приложения.
