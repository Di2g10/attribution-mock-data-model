"""Generate synthetic Marketing Activity rows (Pull + Push logic enforced)."""

from __future__ import annotations

from datetime import timedelta
from random import random
from typing import Any, Sequence, List

import polars as pl

from ..random_utils import (
    fake,
    make_ids,
    random_date,
    weighted_sample,
    generate_source_id_mappings,
)
from ..validation import extract_id_column

__all__ = ["generate"]

CONTROL_PROBABILITY = 0.10
COMPANY_TARGET_RATIO = 0.50  # for Push rows: 50 % company, 50 % person

STATUS: Sequence[str] = ["Sent", "Delivered", "Viewed", "Bounced", "Failed", "Scheduled"]
STATUS_W: Sequence[float] = [0.25, 0.25, 0.20, 0.10, 0.08, 0.12]

SOURCE_TABLE_MAP: List[tuple[str, str]] = [
    ("marketo", "Activity_GUID"),
    ("Adobe Analytics", "View_ID"),
    ("GA4", "event_id"),
]


# -----------------------------------------------------------------------------
def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of marketing activity data."""
    prior = kwargs.get("prior", {})

    # FK pools -----------------------------------------------------------------
    marketing_asset_ids = extract_id_column(prior.get("Marketing Assets"), "marketing_asset_id")
    company_ids = extract_id_column(prior.get("Company"), "company_id")
    person_ids = extract_id_column(prior.get("Person"), "person_id")
    campaign_ids = extract_id_column(prior.get("Campaigns"), "campaign_id")
    audience_ids = extract_id_column(prior.get("Audience"), "audience_id")

    # Channel table **must** expose channel_type = "Pull" or "Push"
    channel_df = prior.get("Channels")

    expected_columns = ["channel_id", "communication_mode"]
    for col in expected_columns:
        if col not in channel_df.columns:
            raise ValueError(f"Channel table must have column {col}")

    channels: list[tuple[str, str]] = list(
        channel_df.select(["channel_id", "communication_mode"]).rows()
    )

    # Convenience helpers ------------------------------------------------------
    def sample_channel() -> tuple[str, str]:
        """Return (channel_id, type)."""
        return fake.random_element(channels)

    def maybe_choice(pool: list[str] | None) -> str | None:
        """Randomly choose an element _or_ return None if pool is empty."""
        return fake.random_element(pool) if pool else None

    # Core row generation ------------------------------------------------------
    ids = make_ids(n, "ACT")
    start_dates = [random_date() for _ in range(n)]
    status_vals = weighted_sample(STATUS, STATUS_W, n)
    system_ids = [f"SYS{fake.random_int(1000, 9999)}" for _ in range(n)]
    names = [f"Marketing Activity {i}" for i in ids]

    rows: list[dict[str, Any]] = []
    for i in range(n):
        chan_id, mode = fake.random_element(channels)

        if mode.lower() == "pull":
            # Pull-type: end/reach present, targets null
            end_d = start_dates[i] + timedelta(days=fake.random_int(0, 7))
            reach_co = fake.random_int(1, 1_000)
            reach_ind = reach_co * fake.random_int(1, 5)
            tgt_comp = None
            tgt_pers = None
        else:
            # Push-type: targets present, end/reach null
            end_d = None
            reach_co = None
            reach_ind = None
            if random() < COMPANY_TARGET_RATIO:
                tgt_comp, tgt_pers = maybe_choice(company_ids), None
            else:
                tgt_comp, tgt_pers = None, maybe_choice(person_ids)

        rows.append(
            {
                "marketing_activity_id": ids[i],
                "audience_id": maybe_choice(audience_ids),
                "campaign_id": maybe_choice(campaign_ids),
                "marketing_asset_id": maybe_choice(marketing_asset_ids),
                "system_id": system_ids[i],
                "channel_id": chan_id,
                "targeted_company_id": tgt_comp,
                "targeted_person_id": tgt_pers,
                "end_date": end_d,
                "name": names[i],
                "reach_companies": reach_co,
                "reach_individuals": reach_ind,
                "start_date": start_dates[i],
                "status": status_vals[i],
            }
        )

    df = pl.DataFrame(rows).hstack(generate_source_id_mappings(SOURCE_TABLE_MAP, n))

    # Final column order -------------------------------------------------------
    column_order = [
        "audience_id",
        "campaign_id",
        "channel_id",
        "end_date",
        "marketing_activity_id",
        "marketing_asset_id",
        "name",
        "reach_companies",
        "reach_individuals",
        "source_id",
        "source_id_field",
        "source_table",
        "start_date",
        "status",
        "system_id",
        "targeted_company_id",
        "targeted_person_id",
    ]
    return df.select(column_order)
