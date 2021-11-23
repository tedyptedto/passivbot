"""
Python will always try to import sitecustomize.
We use that fact to try and support code coverage for sub-processes
"""
from __future__ import annotations

try:
    import coverage

    coverage.process_startup()
except ImportError:
    pass
