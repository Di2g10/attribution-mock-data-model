"""Generate Channel records with sensible `type` and Push/Pull mode."""

from __future__ import annotations

from random import randint
from typing import Any, Dict

import polars as pl

from ..random_utils import fake, make_ids

__all__ = ["generate"]

# --------------------------------------------------------------------------- #
# Default vocabularies
# --------------------------------------------------------------------------- #
DEFAULT_CHANNEL_TYPES: list[str] = [
    "Email",
    "Paid Search",
    "Display",
    "Organic Social",
    "Direct Mail",
    "SMS",
    "Telemarketing",
    "Web",
]
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
        return []
    try:
        df = registry.cfg.channels
        return [row for row in df.iter_rows(named=True)]
    except Exception as exc:
        print(f"[channels] warning: could not hydrate registry - {exc}")
        return []


# --------------------------------------------------------------------------- #
# Main generator
# --------------------------------------------------------------------------- #
def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Return *n* rows for the **Channel** dimension.

    If a registry is supplied (``registry=SchemaRegistry``), we reuse any
    pre-defined rows and then pad with synthetic ones until we reach *n*.
    """
    registry = kwargs.get("registry")
    seed_rows = _registry_channels(registry)

    # ── Pad out with synthetic rows if we still need more ──────────────────
    needed = max(0, n - len(seed_rows))

    for _ in range(needed):
        ch_type = fake.random_element(DEFAULT_CHANNEL_TYPES)
        seed_rows.append(
            {
                "Name": f"{ch_type} {randint(1, 9)}",  # type-flavoured name
                "Group": fake.random_element(DEFAULT_GROUPS),
                "Identifiable method": fake.random_element(DEFAULT_METHODS),
                "Type": ch_type,
            }
        )

    # ── Slice to exactly *n* rows (registry may have had too many) ─────────
    rows = seed_rows[:n]

    # ── Build DataFrame ────────────────────────────────────────────────────
    df = pl.DataFrame(
        {
            "channel_id": make_ids(n, "CHAN"),
            "name": [r["Name"] for r in rows],
            "group": [r["Group"] for r in rows],
            "identifiable_method": [r["Identifiable method"] for r in rows],
            "type": [r["Type"] for r in rows],
        }
    )

    # ── Derive the Push / Pull flag ---------------------------------------
    return df.with_columns(
        (
            pl.when(pl.col("type").is_in(PUSH_TYPES))
            .then(pl.lit("Push"))
            .otherwise(pl.lit("Pull"))
            .alias("communication_mode")  # << NEW COLUMN
        )
    )
