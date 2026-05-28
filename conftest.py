"""
Root conftest.py — ensures the project root is on sys.path for all tests
so that `from server.app import app` and `from tools.xxx import ...` resolve
regardless of how pytest is invoked.
"""
import sys
from pathlib import Path

# Project root (one level above this file)
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
