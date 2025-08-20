"""Generator for the 'Attribution Model' object.

This produces a single row (or the number requested by the registry)
representing the attribution model configuration. Fields are aligned to the
Attributes sheet when available.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from ..random_utils import make_ids

__all__ = ["generate"]


def _norm(s: str) -> str:
    """Normalise a column/object name: strip, lower, remove spaces/underscores."""
    return str(s).strip().lower().replace(" ", "").replace("_", "")


def _get_attribute_columns(registry: Any, object_name: str) -> list[str] | None:
    """Return ordered list of column names for the given object from Attributes sheet.

    :param registry: SchemaRegistry (expected to hold cfg.workbook)
    :param object_name: Name of the object in the workbook
    :returns: List of column names or None if workbook/attributes not available
    """
    try:
        if (
            registry is None
            or not hasattr(registry, "cfg")
            or not hasattr(registry.cfg, "workbook")
        ):
            return None
        import pandas as pd  # only at runtime, not a project dep for generation logic

        pdf = pd.read_excel(registry.cfg.workbook, sheet_name="Attributes")
        rows = pdf[pdf.get("Object").fillna("").astype(str) == object_name]
        if rows.empty or "Name" not in rows.columns:
            return None
        return [str(x) for x in rows["Name"].dropna().tolist() if str(x).strip()]
        # Preserve order as in sheet
    except Exception:
        return None


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate the Attribution Model table.

    The table is minimal and workbook-driven. It attempts to honour the
    Attributes sheet for column selection. If the sheet is unavailable, a
    small sensible default is returned.

    :param n: Number of rows to generate (typically 1).
    :param kwargs: Additional context. Recognised keys: ``registry``.
    :returns: Polars DataFrame of the Attribution Model object.
    :raises ValueError: If ``n`` is less than 1.
    """
    if n < 1:
        raise ValueError("Attribution Model requires at least one row (n >= 1)")

    registry = kwargs.get("registry")

    # Build some base fields we can map into the expected columns
    model_ids = pl.Series("attribution_model_id", make_ids(n, prefix="AMOD"))
    name_values = pl.Series("name", ["Mock Attribution Model"] * n, dtype=pl.String)
    description_values = pl.Series(
        "description", ["Auto-generated mock model"] * n, dtype=pl.String
    )

    base = pl.DataFrame(
        {
            "attribution_model_id": model_ids,
            "name": name_values,
            "description": description_values,
        }
    )

    # If Attributes sheet is defined, shape/align to it
    attr_cols = _get_attribute_columns(registry, "Attribution Model")
    if attr_cols:
        # Build mapping by normalised keys to available base columns
        norm_to_col = {_norm(c): c for c in base.columns}

        # Prepare output columns in the order of the attributes sheet
        out_cols: dict[str, pl.Series] = {}
        for col in attr_cols:
            key = _norm(col)
            # Common variants for IDs
            if key in norm_to_col:
                out_cols[col] = base.get_column(norm_to_col[key])
            elif key in {"id", "modelid", "attributionmodelid"}:
                out_cols[col] = base.get_column("attribution_model_id").rename(col)
            elif key in {"modelname", "model", "attributionmodelname"}:
                out_cols[col] = base.get_column("name").rename(col)
            elif key in {"desc", "description"}:
                out_cols[col] = base.get_column("description").rename(col)
            else:
                # Default to null strings; types are not strictly validated here
                out_cols[col] = pl.Series(col, [None] * n, dtype=pl.String)

        return pl.DataFrame(out_cols)

    # Fallback default when workbook Attributes are unavailable
    return base.rename(
        {
            "attribution_model_id": "Attribution Model ID",
            "name": "Name",
            "description": "Description",
        }
    )
