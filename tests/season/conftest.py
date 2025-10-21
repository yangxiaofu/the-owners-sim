"""
Pytest configuration for season tests.
"""

import sys
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))
