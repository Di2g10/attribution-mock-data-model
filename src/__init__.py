"""BT attribution mock data."""

from importlib import import_module  # noqa: F401 - re-export path convenience
from .orchestrator import build

__all__ = [
    "build",
]
