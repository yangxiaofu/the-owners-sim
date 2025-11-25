"""
Pytest configuration for UI tests.

Sets up proper import paths for ui.* and src.* modules.
"""

import sys
import os
from pathlib import Path

# Add project root to path for absolute imports (ui.* and src.*)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
