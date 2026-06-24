"""Add human feedback for a completed agent run."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.feedback_cli import main


if __name__ == "__main__":
    raise SystemExit(main())