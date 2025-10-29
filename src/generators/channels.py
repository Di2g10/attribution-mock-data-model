"""Generate Channel records with sensible `type` and Push/Pull mode."""

from __future__ import annotations

from typing import Any, Dict

import polars as pl

from ..random_utils import make_ids

__all__ = ["generate"]

# --------------------------------------------------------------------------- #
# Default vocabularies
# --------------------------------------------------------------------------- #

# Simple mapping - tweak / extend if you need finer control
PUSH_TYPES = {"Email", "SMS", "Telemarketing", "Direct Mail"}
# everything else will be treated as Pull

DEFAULT_GROUPS = ["ATL", "BTL", "Sales", "Other"]
DEFAULT_METHODS = ["Known Person", "Audience Inferred", "IP Inferred", "Unknown"]


# --------------------------------------------------------------------------- #
# Helper to read any pre-configured channels from the registry
# --------------------------------------------------------------------------- #
def _registry_channels(registry: Any | None) -> list[Dict[str, Any]]:
    if registry is None:
        raise ValueError("No SchemaRegistry provided")

    df = registry.cfg.channels
    return [row for row in df.iter_rows(named=True)]


# --------------------------------------------------------------------------- #
# Main generator
# --------------------------------------------------------------------------- #
def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Return *n* lf for the **Channel** dimension.

    If a registry is supplied (``registry=SchemaRegistry``), we reuse any
    pre-defined lf and then pad with synthetic ones until we reach *n*.
    """
    registry = kwargs.get("registry")
    rows = _registry_channels(registry)

    # ── Build DataFrame ────────────────────────────────────────────────────
    return pl.DataFrame(
        {
            "channel_id": make_ids(len(rows), "CHAN"),
            "channel_name": [r["Channel Name"] for r in rows],
            "group": [r["Group"] for r in rows],
            # "identifiable_method": [r["Identifiable method"] for r in lf],
            "type": [r["Type"] for r in rows],
        }
        # ── Derive the Push / Pull flag ---------------------------------------
    ).with_columns(
        pl.when(pl.col("type").is_in(PUSH_TYPES))
        .then(pl.lit("Push"))
        .otherwise(pl.lit("Pull"))
        .alias("communication_mode")  # << NEW COLUMN
    )
