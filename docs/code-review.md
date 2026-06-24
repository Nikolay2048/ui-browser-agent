# Senior Code Review

## Summary

Проект находится в хорошем состоянии для v0.1 educational demo.

Сильные стороны:

- понятное разделение domain / graph / roles / browser / runner / memory /
  evaluation;
- широкое тестовое покрытие;
- LLM outputs типизированы через Pydantic;
- browser side effects вынесены в deterministic executor;
- есть независимый Judge;
- есть failure classification и bug reporting;
- есть run reports, run history, feedback memory и retrieval;
- есть demo feedback example;
- есть scripts для локального запуска и LangSmith experiments.

Основные production gaps:

- нет typed protocol для feedback store;
- JSONL stores не защищены от поврежденных строк и concurrent writes;
- нет сохранения `used_feedback_ids` в report;
- нет memory evaluation "with vs without feedback";
- нет prompt versioning;
- нет retries/timeouts policy на уровне browser actions;
- есть несколько style/type cleanup items.

## Findings

### P2. Browser method annotations say `str`, but runtime expects `BrowserTarget`

File:

```text
src/browser_agent/browser.py:48
src/browser_agent/browser.py:51
src/browser_agent/browser.py:54
src/browser_agent/browser.py:57
```

Current signatures:

```python
def click(self, target: str) -> None:
def fill(self, target: str, value: str) -> None:
def press(self, target: str, value: str) -> None:
def assert_text(self, target: str) -> None:
```

But `_resolve_target()` requires:

```python
def _resolve_target(self, target: BrowserTarget):
```

Impact:

- type hints are misleading;
- future IDE/type-checker support will be weaker;
- a developer might pass a string and get runtime `TypeError`.

Recommendation:

```python
def click(self, target: BrowserTarget) -> None:
def fill(self, target: BrowserTarget, value: str) -> None:
def press(self, target: BrowserTarget, value: str) -> None:
def assert_text(self, target: BrowserTarget) -> None:
```

Also remove unused import:

```text
src/browser_agent/browser.py:3
```

`import re` is currently unused.

### P2. `feedback_store` is duck-typed but not documented as a Protocol

File:

```text
src/browser_agent/runner.py:22
src/browser_agent/runner.py:42
src/browser_agent/feedback_retrieval.py:46
```

`RunHistoryStore` has a `Protocol`, but feedback store does not.

Impact:

- less clear public contract;
- tests use in-memory store, but type signature does not explain required
  methods;
- future replacement with DB/vector store has less guidance.

Recommendation:

Add:

```python
class FeedbackStore(Protocol):
    def load_all(self) -> list[HumanFeedbackRecord]:
        ...
```

Then type:

```python
feedback_store: FeedbackStore | None = None
```

Do not overbuild a repository abstraction yet. One minimal Protocol is enough.

### P2. Used feedback is not recorded in final report

Files:

```text
src/browser_agent/runner.py:69
src/browser_agent/reporting.py
src/browser_agent/domain/models.py
```

Runner builds `memory_context`, but final `RunReport` does not record:

- which feedback records were retrieved;
- which scopes/tags were used;
- memory context hash;
- whether memory was enabled.

Impact:

- hard to debug memory effects;
- impossible to audit "why did planner choose this";
- hard to evaluate memory quality.

Recommendation:

Introduce a small domain model later:

```python
class MemoryUsage(BaseModel):
    enabled: bool
    feedback_ids: list[str]
    query_scopes: list[FeedbackScope]
```

Then include it in `RunReport`.

### P2. JSONL stores do not handle corrupted lines

Files:

```text
src/browser_agent/run_history.py:65
src/browser_agent/feedback.py:91
```

Current behavior:

```python
RunHistoryRecord.model_validate_json(line)
HumanFeedbackRecord.model_validate_json(line)
```

If one line is invalid, the whole load fails.

Impact:

- one bad line can break all history/feedback loading;
- manual editing of JSONL becomes risky.

Recommendation:

For v0.2, decide policy:

1. fail fast with line number;
2. skip invalid lines and collect errors;
3. quarantine invalid records.

For learning, fail fast is acceptable, but error should include path and line
number.

### P2. `created_at` and `recorded_at` timezone awareness is not enforced

Files:

```text
src/browser_agent/run_history.py:17
src/browser_agent/feedback.py:22
```

Builders use:

```python
datetime.now(timezone.utc)
```

But explicit `created_at` / `recorded_at` can be naive.

Impact:

- sorting feedback by `created_at` can become ambiguous;
- cross-machine data may have inconsistent timestamps.

Recommendation:

Add validators:

```python
if value.tzinfo is None or value.utcoffset() is None:
    raise ValueError("created_at must be timezone-aware")
```

### P3. JSONL store logic is duplicated

Files:

```text
src/browser_agent/run_history.py
src/browser_agent/feedback.py
```

Both implement:

- create parent;
- append one JSON line;
- load all lines;
- filter by id.

Impact:

- duplicated code;
- fixes to line handling must be applied twice.

Recommendation:

Do not rush into generic abstraction in the learning phase. For v0.2 consider a
small internal helper:

```python
append_jsonl(path, model)
load_jsonl(path, schema)
```

Avoid a heavy repository framework.

### P3. Prompt versions are implicit

Files:

```text
src/browser_agent/planner.py
src/browser_agent/judge.py
src/browser_agent/classifier.py
src/browser_agent/reporter.py
```

Prompts are constants, but not versioned.

Impact:

- hard to compare evaluation runs after prompt changes;
- LangSmith traces show text, but project-level versioning is not explicit.

Recommendation:

Add constants:

```python
PLANNER_PROMPT_VERSION = "planner-v3"
JUDGE_PROMPT_VERSION = "judge-v1"
```

Include prompt version in trace metadata and evaluation outputs.

### P3. `run_real_agent.py` is useful but still a demo script

File:

```text
scripts/run_real_agent.py
```

Current script is fine for demo, but not a production CLI.

Missing:

- `--headless`;
- `--slow-mo`;
- `--model`;
- `--report-dir`;
- `--history-path`;
- `--no-feedback`;
- structured exit code;
- non-interactive mode without `input()`.

Recommendation:

Keep current script for learning. If turning into product CLI, add arguments
gradually and tests for parser behavior.

### P3. Some formatting style issues remain

Examples:

```text
src/browser_agent/feedback.py:71
src/browser_agent/judge.py
src/browser_agent/reporter.py
```

Issues:

- missing two blank lines between top-level definitions;
- long lines;
- inconsistent indentation.

Impact:

Low. Tests pass, but readability suffers.

Recommendation:

Add formatter later:

- `ruff`;
- `black`;
- `mypy` or `pyright`.

## Strong Decisions Worth Keeping

### Domain models are independent

`domain/models.py` has no dependency on LangGraph, LangChain, Playwright,
LangSmith or persistence. This is correct.

### LLM roles are separate

Planner, Judge, Classifier and Reporter are separate modules. This is correct
because each role has different output schema and evaluation criteria.

### Executor is deterministic

LLM proposes; executor executes. This is the right safety boundary.

### Runner is the composition layer

`runner.py` owns graph construction, trace/checkpoint config, memory context,
reporting and history persistence. This keeps graph nodes focused.

### Feedback is data, not prompt edits

Human corrections are stored as `HumanFeedbackRecord`, then retrieved and
formatted. This is the right foundation for future RAG/memory work.

### Evaluation is separated by component

Planner/Judge/E2E evaluation are different concerns. This makes debugging
agent behavior much easier.

## Production Readiness Assessment

Current status:

```text
Educational demo: strong
Internal prototype: acceptable with care
Production system: not yet
```

What blocks production:

- no robust storage;
- no auth/secrets management beyond `.env`;
- no browser resource pooling;
- no concurrency control;
- no retries/timeouts strategy;
- no prompt versioning;
- no memory audit trail;
- no UI/API for test case ingestion;
- no generated regression test output;
- no deployment packaging.

## Recommended v0.2 Fixes

1. Add `FeedbackStore Protocol`.
2. Fix browser target type hints.
3. Add timezone-aware validators.
4. Add `used_feedback_ids` or `MemoryUsage` to final report.
5. Add prompt versions.
6. Add `ruff` formatting/linting.
7. Add `--headless`, `--model`, `--feedback-path`, `--history-path` to CLI.
8. Add memory evaluation: with vs without feedback.
9. Add robust JSONL line error reporting.
10. Add examples for failed run and bug report generation.
