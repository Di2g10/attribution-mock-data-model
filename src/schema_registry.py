"""Contains the SchemaRegistry class."""

from __future__ import annotations

from typing import ClassVar, Any, Iterable


from .config_loader import Config

__all__ = ["SchemaRegistry"]


def _norm(s: str) -> str:
    """Normalise a column/object name: strip, lower, replace whitespace with underscores."""
    return " ".join(str(s).strip().split()).lower().replace(" ", "_")


def _truthy(val: Any) -> bool:
    """Return True for typical 'yes' markers."""
    s = str(val).strip().lower()
    return s in {"y", "yes", "true", "1"} or s.startswith("y")


def _first_present(row: dict[str, Any], keys: Iterable[str]) -> Any:
    """Return the first non-empty value for any of the candidate keys in the row."""
    for k in keys:
        if k in row and row[k] not in (None, "", "nan"):
            return row[k]
    return None


def _coerce_int(val: Any, default: int) -> int:
    """Coerce a value to int, returning default on failure."""
    try:
        # Polars may hand us int, float, or string here.
        return int(float(val))
    except (TypeError, ValueError):
        return default


class SchemaRegistry:
    """Discovers objects, their desired row counts, and generation order."""

    _DEFAULT_ORDER: ClassVar[list[str]] = [
        "Company",
        "Person",
        "Person Company Role",
        "Products",
        "Channels",
        "Facilitation Tool",
        "Marketing Assets",
        "Audience",
        "Campaigns",
        "Push Activity",
        "Pull Activity",
        "Interactions",
        "Orders",
        "Attribution Linking Table",
        "Attribution Model",
        "Attribution Model Output Table",
        "Date Dimension",
    ]

    def __init__(self, cfg: Config):
        """Initialise the SchemaRegistry object."""
        self.cfg = cfg
        self._objects: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []
        self._parse_objects()

    # ------------------------------------------------------------------
    def _parse_objects(self) -> None:
        """Parse the 'objects' sheet and populate `_objects` and `_order`.

        The parser is resilient to header variations by normalising column names.
        Generation ordering respects a `generation_order` column when present;
        otherwise it falls back to `_DEFAULT_ORDER` precedence.
        """
        objects_df = self.cfg.objects
        if objects_df.is_empty():
            self._objects = {}
            self._order = []
            return

        # Normalise column names once, to enable flexible matching
        rename_map = {col: _norm(col) for col in objects_df.columns}
        objects_df = objects_df.rename(rename_map)

        # If generation_order present, sort ascending (1,2,3,...)
        if "generation_order" in objects_df.columns:
            objects_df = objects_df.sort(by="generation_order", descending=False)

        # Build objects
        parsed: dict[str, dict[str, Any]] = {}
        order: list[str] = []

        # Candidate column names
        name_col = "name"
        gen_flag_cols = ("generate?", "generate", "gen", "enabled")
        row_count_cols = ("generate_rows", "Generate_Rows")
        generation_method_col = "generation_method"

        for row in objects_df.iter_rows(named=True):
            name_raw = row.get(name_col, "")
            name = str(name_raw).strip()
            if not name:
                continue

            # Should we generate?
            gen_val = _first_present(row, gen_flag_cols)
            if gen_val is not None and not _truthy(gen_val):
                continue  # explicitly disabled

            # Should we check row count?
            generation_method = row.get(generation_method_col, "")
            check_row_count = not (
                generation_method.lower() == "derived" or name == "Person Company Role"
            )

            # Determine row count, defaulting to 100 only if not specified
            rc_val = _first_present(row, row_count_cols)
            require_min_one = False
            if isinstance(rc_val, str) and rc_val.strip().lower() == "dependant":
                # For dependant objects, do not enforce exact count; require at least one row.
                check_row_count = False
                require_min_one = True
            row_count = _coerce_int(rc_val, default=100)
            # If someone explicitly put 0, keep a sensible minimum of 1 or default?
            # Preserve existing behaviour: when 0/empty, default 100.
            if row_count <= 0:
                row_count = 100

            parsed[name] = {
                "row_count": row_count,
                "meta": row,
                "check_count": check_row_count,
                "require_min_one": require_min_one,
            }
            order.append(name)

        # If no explicit generation_order provided, impose DEFAULT precedence
        if "generation_order" not in objects_df.columns:
            precedence = {n: i for i, n in enumerate(self._DEFAULT_ORDER)}
            order.sort(key=lambda n: precedence.get(n, len(precedence)))

        self._objects = parsed
        self._order = order

    # ------------------------------------------------------------------
    def check_row_count(self, name: str, row_count: int) -> bool:
        """Check if given row count matches expected row count for given object name.

        :param name: Object name as declared in the workbook.
        :param row_count: Row count to check against.
        :raises KeyError: If the object name is not present.
        :returns: True if the row count passes validation for this object.
        """
        if name not in self._objects:
            raise KeyError(f"Object '{name}' not found in workbook.")
        obj = self._objects[name]
        if not obj["check_count"]:
            # When exact checking is disabled, optionally require at least one row
            if obj.get("require_min_one"):
                return row_count >= 1
            return obj["row_count"] > 0
        return row_count == obj["row_count"]

    def row_count(self, name: str) -> int:
        """Return the configured row count for the given object name.

        :param name: Object name as declared in the workbook.
        :raises KeyError: If the object name is not present.
        :returns: Integer row count for the object, as parsed from the workbook.
        """
        if name not in self._objects:
            raise KeyError(f"Object '{name}' not found in workbook.")
        return self._objects[name]["row_count"]

    # ------------------------------------------------------------------
    def generation_order(self) -> list[str]:
        """Return the objects in the order they should be generated."""
        return list(self._order)
