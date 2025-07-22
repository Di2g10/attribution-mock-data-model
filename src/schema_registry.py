"""Contains the SchemaRegistry class."""

from __future__ import annotations

from typing import ClassVar, Any

from .config_loader import Config

__all__ = ["SchemaRegistry"]


class SchemaRegistry:
    """Discovers objects, their desired row counts, and generation order."""

    _DEFAULT_ORDER: ClassVar[list[str]] = [
        "Company",
        "Person",
        "Campaigns",
        "Push Activity",
        "Pull Activity",
        "Interactions",
        "Orders",
    ]

    def __init__(self, cfg: Config):
        """Initialize the SchemaRegistry object."""
        self.cfg = cfg
        self._objects = self._parse_objects()

    # ------------------------------------------------------------------
    def _parse_objects(self) -> dict[str, dict[str, Any]]:
        """Parse the 'objects' sheet.

        Sort by order_num, descending.
        """
        objs = {}

        # Check if generation_order column exists
        objects_df = self.cfg.objects
        if "generation_order" in objects_df.columns:
            objects_df = objects_df.sort(by="generation_order", descending=False)

        for row in objects_df.iter_rows(named=True):
            if str(row.get("generate?", "yes")).lower().startswith("n"):
                continue
            name = row["Name"]
            objs[name] = {
                "row_count": int(row.get("row_count", 0) or 100),
                "meta": row,
            }
        return objs

    # ------------------------------------------------------------------
    def row_count(self, name: str) -> int:
        """Return the row count for the given object name."""
        return self._objects[name]["row_count"]

    # ------------------------------------------------------------------
    def generation_order(self) -> list[str]:
        """Return the objects in the order they should be generated."""
        return [n for n in self._objects]
