# tests/conftest.py
# Ensure the project root is on sys.path so that
# "import interactive_learning_tool" works in tests.

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
