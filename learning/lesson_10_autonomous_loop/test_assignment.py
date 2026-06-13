"""Original assignment tests are active in tests/test_graph.py.

This file records the expected scenarios without being collected by the current
pytest configuration.
"""

EXPECTED_CASES = [
    "finish action routes to pass_run",
    "ordinary action routes to execute",
    "successful execution routes to observe",
    "failed execution routes to fail_run",
    "step limit routes to fail_run",
    "full loop observes until planner returns finish",
]
