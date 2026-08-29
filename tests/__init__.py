"""Test package for the Automation Hub.

Marking tests as a package makes `unittest discover -s tests` treat the repo
root as the top level, so `import hub` works no matter where the runner is
started from.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
