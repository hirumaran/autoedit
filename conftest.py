"""conftest.py — shared pytest configuration.

Adds the backend/ directory to sys.path so that internal imports like
``from editing_engine import ...`` work both when running tests from the
project root and when running them from inside backend/.
"""
import sys
from pathlib import Path

# Make backend/ importable as a root package for bare imports inside modules
BACKEND_DIR = Path(__file__).parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
