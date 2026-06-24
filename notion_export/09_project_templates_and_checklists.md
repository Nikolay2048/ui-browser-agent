# Project Templates And Checklists

## New AI Agent Project Template

Структура:

```text
my_agent/
  pyproject.toml
  README.md
  docs/
    architecture.md
    runbook.md
    evaluation.md
  examples/
    cases/
    feedback/
  src/my_agent/
    domain.py
    state.py
    planner.py
    executor.py
    observer.py
    judge.py
    graph.py
    runner.py
    reporting.py
    memory.py
    retrieval.py
    evaluation.py
  scripts/
    run_agent.py
    add_feedback.py
    evaluate.py
  tests/
    test_domain.py
    test_planner.py
    test_executor.py
    test_graph.py
    test_runner.py
    test_memory.py
    test_retrieval.py
```

## First Questions For Any Agent

1. What is the goal?
2. What is the environment?
3. What can the agent observe?
4. What can the agent do?
5. What should be impossible?
6. What is success?
7. Who verifies success?
8. What are the limits?
9. What should be recorded?
10. What can be replayed?
11. What memory is useful?
12. How will quality be measured?

## Domain Modeling Checklist

- [ ] Input task model.
- [ ] Action model.
- [ ] Tool target model.
- [ ] Tool result model.
- [ ] Step/trace model.
- [ ] Verdict model.
- [ ] Termination model.
- [ ] Error/failure model.
- [ ] Report model.
- [ ] Feedback model.
- [ ] Validators for business rules.
- [ ] JSON serialization tests.

## Planner Checklist

- [ ] Output is structured.
- [ ] Prompt says "one next action".
- [ ] Prompt includes current observation.
- [ ] Prompt includes goal.
- [ ] Prompt includes constraints.
- [ ] Prompt includes examples of valid target/action.
- [ ] Prompt rejects invalid target formats.
- [ ] Prompt includes execution history.
- [ ] Prompt includes memory context if available.
- [ ] Planner does not execute tools.
- [ ] Planner `finish` goes to verifier, not direct success.

## Executor Checklist

- [ ] Only supports allowlisted actions.
- [ ] Does not call LLM.
- [ ] Captures before/after state.
- [ ] Captures screenshot/evidence.
- [ ] Returns structured result.
- [ ] Handles exceptions.
- [ ] Records failed attempts.
- [ ] Does not hide tool errors.

## Judge Checklist

- [ ] Independent from planner.
- [ ] Uses evidence only.
- [ ] Checks every expected result.
- [ ] Fails on missing evidence.
- [ ] Returns structured verdict.
- [ ] Has false-positive evaluation.

## Graph Checklist

- [ ] START edge.
- [ ] initialize node.
- [ ] observe-plan-act loop.
- [ ] finish path to Judge.
- [ ] failure path.
- [ ] max steps.
- [ ] max failures.
- [ ] optional approval.
- [ ] terminal END paths.
- [ ] tests for happy path.
- [ ] tests for failure path.
- [ ] tests for recovery.

## Memory Checklist

- [ ] Memory record schema.
- [ ] Stable IDs.
- [ ] Timezone-aware timestamps.
- [ ] Scope/type.
- [ ] Tags/metadata.
- [ ] Store abstraction.
- [ ] Append-only persistence.
- [ ] Retrieval query.
- [ ] Format for prompt.
- [ ] Limit.
- [ ] Used memory audit.
- [ ] Memory evaluation.

## Evaluation Checklist

- [ ] Unit tests.
- [ ] Component eval.
- [ ] E2E deterministic eval.
- [ ] Live eval.
- [ ] Dataset with references.
- [ ] Metrics.
- [ ] Failure analysis.
- [ ] LangSmith or equivalent traces.
- [ ] Regression cases.
- [ ] Negative cases.

## Runbook Template

```markdown
# Runbook

## Setup
commands

## Configuration
env vars

## Run
commands

## Demo
commands

## Test
commands

## Artifacts
where outputs go

## Troubleshooting
known issues
```

## ADR Template

```markdown
# ADR: <title>

## Context
What problem are we solving?

## Decision
What did we choose?

## Why
Why this choice?

## Alternatives
What else was considered?

## Consequences
What becomes easier/harder?

## Tests
How do we know it works?
```

## Feedback Record Template

```json
{
  "feedback_id": "feedback-001",
  "run_id": "run-123",
  "test_case_id": "case-abc",
  "created_at": "2026-06-24T10:00:00Z",
  "scope": "planner",
  "step_number": null,
  "summary": "Planner selected a fragile locator.",
  "correction": "Use label=Email for the email input.",
  "tags": ["planner", "locator"]
}
```

## Evaluation Case Template

```json
{
  "id": "planner-login-fill-username",
  "inputs": {
    "test_case": {},
    "page_snapshot": "- textbox \"Username\"\n- button \"Login\"",
    "route": []
  },
  "reference_outputs": {
    "action": {
      "action": "fill",
      "target": {"strategy": "label", "value": "Username"},
      "value": "standard_user",
      "reason": "Enter username."
    }
  }
}
```

## Prompt Review Checklist

- [ ] Does prompt define role?
- [ ] Does prompt define output schema in words?
- [ ] Does prompt include valid examples?
- [ ] Does prompt include invalid examples?
- [ ] Does prompt say not to invent facts?
- [ ] Does prompt say what to do when uncertain?
- [ ] Does prompt include current context near the end?
- [ ] Does prompt distinguish memory from current truth?
- [ ] Is prompt test-covered?
- [ ] Is prompt versioned?

## Pre-Commit Checklist

- [ ] `python -m pytest -q`
- [ ] demo `--help` works
- [ ] no runtime artifacts staged
- [ ] README updated
- [ ] docs updated
- [ ] examples are reproducible
- [ ] no secrets in files
- [ ] evaluation data updated if behavior changed

## Production Readiness Checklist

- [ ] Auth/secrets management.
- [ ] Logging.
- [ ] Tracing.
- [ ] Metrics.
- [ ] Timeouts.
- [ ] Retries.
- [ ] Rate limits.
- [ ] Storage migrations.
- [ ] Concurrency safety.
- [ ] Audit logs.
- [ ] Human override.
- [ ] Prompt versions.
- [ ] Dataset regression.
- [ ] Deployment story.
