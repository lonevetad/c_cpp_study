"""Pytest configuration."""

import sys
from pathlib import Path

# Add parent directory to path so tests can import fcpp_bridge
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root.parent))
