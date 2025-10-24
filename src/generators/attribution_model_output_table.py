"""Generator for the 'Attribution Model Output Table' object.

The output contains one row per link from the 'Attribution Linking Table'.
It aligns columns to the Attributes sheet when available.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from ..random_utils import make_ids

import random

__all__ = ["generate"]


def _norm(s: str) -> str:
    return str(s).strip().lower().replace(" ", "").replace("_", "")


def _get_attribute_columns(registry: Any, object_name: str) -> list[str] | None:
    try:
        if (
            registry is None
            or not hasattr(registry, "cfg")
            or not hasattr(registry.cfg, "workbook")
        ):
            return None
        import pandas as pd

        pdf = pd.read_excel(registry.cfg.workbook, sheet_name="Attributes")
        rows = pdf[pdf.get("Object").fillna("").astype(str) == object_name]
        if rows.empty or "Name" not in rows.columns:
            return None
        return [str(x) for x in rows["Name"].dropna().tolist() if str(x).strip()]
    except Exception:
        return None


def _require_df(value: Any, name: str, *, missing_ok: bool = False) -> pl.DataFrame:
    if isinstance(value, pl.DataFrame):
        return value
    if missing_ok:
        return pl.DataFrame()
    raise ValueError(f"'{name}' DataFrame is required prior to generating '{name} output'.")


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate the Attribution Model Output Table.

    - Requires prior outputs:
      * 'Attribution Linking Table' — one output row per link
      * 'Attribution Model' — used to attach the model id to all rows
    - Aligns to the workbook's Attributes sheet when available.

    :param n: Unused for this generator; row count is driven by number of links.
    :param kwargs: Expected to include ``prior`` and ``registry``.
    :returns: Polars DataFrame representing the output table.
    :raises ValueError: If required prior DataFrames are not present.
    """
    prior = kwargs.get("prior", {})
    registry = kwargs.get("registry")

    links = _require_df(
        prior.get("Attribution Linking Table"), "Attribution Linking Table", missing_ok=True
    )
    model_df = _require_df(prior.get("Attribution Model"), "Attribution Model", missing_ok=True)

    # Determine how many rows to emit
    links_available = (
        isinstance(links, pl.DataFrame) and ("link_id" in links.columns) and links.height > 0
    )
    row_count = links.height if links_available else int(n or 0)
    if row_count <= 0:
        # Produce an empty shaped frame if attributes available; else a safe empty default
        attr_cols = _get_attribute_columns(registry, "Attribution Model Output Table")
        if attr_cols:
            return pl.DataFrame({c: pl.Series(c, [], dtype=pl.String) for c in attr_cols})
        return pl.DataFrame({"link_id": pl.Series("link_id", [], dtype=pl.String)})

    # Extract the model id (pick the first if multiple exist)
    # Try a few potential column names from the model table
    model_id_value: str
    if isinstance(model_df, pl.DataFrame) and model_df.height > 0:
        model_id_col = None
        for candidate in model_df.columns:
            k = _norm(candidate)
            if k in {"id", "modelid", "attributionmodelid"}:
                model_id_col = candidate
                break
        if model_id_col is None:
            model_id_col = model_df.columns[0]
        model_id_value = str(model_df.get_column(model_id_col)[0])
    else:
        # default/fallback
        model_id_value = make_ids(1, prefix="AMO")[0]

    # Prepare base data per link (or per requested count if links absent)
    if not links_available:
        # In schema/field-validation contexts we may not have links yet. Return an empty, schema-aligned frame.
        attr_cols = _get_attribute_columns(registry, "Attribution Model Output Table")
        if attr_cols:
            return pl.DataFrame({c: pl.Series(c, [], dtype=pl.String) for c in attr_cols})
        # Safe minimal default
        return pl.DataFrame({"link_id": pl.Series("link_id", [], dtype=pl.String)})

    link_ids = links.get_column("link_id").cast(pl.String)

    weight_values = _compute_wieghts(links, row_count)

    return pl.DataFrame(
        {
            "link_id": link_ids,
            # Ensure deterministic ID for each output row if requested in attributes (we'll map later)
            "model_output_id": pl.Series(
                "attribution_model_output_id", make_ids(row_count, prefix="AMOUT")
            ),
            "model_id": pl.Series(
                "attribution_model_id", [model_id_value] * row_count, dtype=pl.String
            ),
            # Provide the computed weight (float 0..1)
            "attribution_weight": pl.Series("weight", weight_values, dtype=pl.Float64),
        }
    )


def _compute_wieghts(links: pl.DataFrame, row_count: int) -> list[float]:
    """Compute the weight values for each row.

    If links have an outcome grouping column, distribute weights per outcome so that
    the sum per outcome is < 1.
    """
    # ------------------ Compute weights ------------------
    # If links have an outcome grouping column, distribute weights per outcome so that
    # the sum per outcome is < 1. Otherwise assign independent random weights.
    weight_values: list[float]

    # Determine outcome grouping column
    outcome_col = None
    for cand in ("outcome_id", "order_id", "outcome"):
        if cand in links.columns:
            outcome_col = cand
            break

    if outcome_col is None:
        raise ValueError("Outcome grouping column is required to compute weights")

    outcome_vals = links.get_column(outcome_col).to_list()  # preserve order
    index_by_outcome: dict[str, list[int]] = {}
    for idx, outv in enumerate(outcome_vals):
        key = str(outv)
        index_by_outcome.setdefault(key, []).append(idx)

    weight_values = [0.0] * row_count
    for indices in index_by_outcome.values():
        k: int = len(indices)
        s = random.uniform(0.3, 0.95)

        # Generate k positive random values and normalise to sum to s
        raw = [max(1e-9, random.random()) for _ in range(k)]
        total = sum(raw)

        share = (
            [s / k] * k if total <= 0 else [s * (x / total) for x in raw]  # Avoid division by zero
        )
        for i, w in zip(indices, share):
            weight_values[i] = float(w)

    return weight_values
