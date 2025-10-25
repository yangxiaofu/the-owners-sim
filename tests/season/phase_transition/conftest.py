"""
Pytest configuration for phase transition tests.

Ensures src/ is in Python path before test collection.
"""

import sys
from pathlib import Path

# Add src directory to Python path
# This must happen before any imports in test modules
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Force reload of calendar module to ensure we get the src/ version
if 'calendar' in sys.modules:
    del sys.modules['calendar']
if 'calendar.date_models' in sys.modules:
    del sys.modules['calendar.date_models']
