"""Generate synthetic Marketing Activity lf (Pull + Push logic enforced)."""

from __future__ import annotations
from datetime import timedelta
from random import random
from typing import Any, Sequence, List, Dict, Optional
from enum import StrEnum

import polars as pl
from polars import Datetime

from .campaigns import CampaignField
from .channels import ChannelField
from .company import CompanyField
from .person import PersonField
from ..random_utils import (
    fake,
    make_ids,
    random_date,
    weighted_sample,
    generate_source_id_mappings,
)
from ..validation import extract_id_column

__all__ = ["MARKETING_ACTIVITY_SCHEMA", "MarketingActivityField", "generate"]

CONTROL_PROBABILITY = 0.10
COMPANY_TARGET_RATIO = 0.50  # for Push lf: 50 % company, 50 % person

STATUS: Sequence[str] = ["Sent", "Delivered", "Viewed", "Bounced", "Failed", "Scheduled"]
STATUS_W: Sequence[float] = [0.25, 0.25, 0.20, 0.10, 0.08, 0.12]

SOURCE_TABLE_MAP: List[tuple[str, str]] = [
    ("marketo", "Activity_GUID"),
    ("Adobe Analytics", "View_ID"),
    ("GA4", "event_id"),
]


# -----------------------------------------------------------------------------
# ENUM + SCHEMA
# -----------------------------------------------------------------------------
class MarketingActivityField(StrEnum):
    """Defines all output columns for the Marketing Activity object."""

    audience_id = "audience_id"
    campaign_id = "campaign_id"
    channel_id = "channel_id"
    end_date = "end_date"
    marketing_activity_id = "marketing_activity_id"
    marketing_asset_id = "marketing_asset_id"
    name = "name"
    reach_companies = "reach_companies"
    reach_individuals = "reach_individuals"
    source_id = "source_id"
    source_id_field = "source_id_field"
    source_table = "source_table"
    start_date = "start_date"
    status = "status"
    system_id = "system_id"
    targeted_company_id = "targeted_company_id"
    targeted_person_id = "targeted_person_id"


MARKETING_ACTIVITY_SCHEMA: Dict[StrEnum, pl.DataType] = {
    MarketingActivityField.audience_id: pl.String,
    MarketingActivityField.campaign_id: pl.String,
    MarketingActivityField.channel_id: pl.String,
    MarketingActivityField.end_date: pl.Datetime,
    MarketingActivityField.marketing_activity_id: pl.String,
    MarketingActivityField.marketing_asset_id: pl.String,
    MarketingActivityField.name: pl.String,
    MarketingActivityField.reach_companies: pl.Int64,
    MarketingActivityField.reach_individuals: pl.Int64,
    MarketingActivityField.source_id: pl.String,
    MarketingActivityField.source_id_field: pl.String,
    MarketingActivityField.source_table: pl.String,
    MarketingActivityField.start_date: pl.Datetime,
    MarketingActivityField.status: pl.String,
    MarketingActivityField.system_id: pl.String,
    MarketingActivityField.targeted_company_id: pl.String,
    MarketingActivityField.targeted_person_id: pl.String,
}


# -----------------------------------------------------------------------------
# GENERATOR
# -----------------------------------------------------------------------------
def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of marketing activity data."""
    prior = kwargs.get("prior", {})

    # FK pools -----------------------------------------------------------------
    marketing_asset_ids = extract_id_column(prior.get("Marketing Assets"), "marketing_asset_id")
    company_ids = extract_id_column(prior.get("Company"), CompanyField.company_id)
    person_ids = extract_id_column(prior.get("Person"), PersonField.person_id)
    campaign_ids = extract_id_column(prior.get("Campaigns"), CampaignField.campaign_id)
    audience_ids = extract_id_column(prior.get("Audience"), "audience_id")

    # Channel table **must** expose communication_mode = "Pull" or "Push"
    channel_df = prior.get("Channels")
    expected_columns = [ChannelField.channel_id, ChannelField.communication_mode]
    for col in expected_columns:
        if col not in channel_df.columns:
            raise ValueError(f"Channel table must have column {col}")

    channels: list[tuple[str, str]] = list(
        channel_df.select([ChannelField.channel_id, ChannelField.communication_mode]).rows()
    )

    def maybe_choice(pool: list[str] | None) -> str | None:
        return fake.random_element(pool) if pool else None

    # Generate core data -------------------------------------------------------
    ids = make_ids(n, "ACT")
    start_dates = [random_date() for _ in range(n)]
    status_vals = weighted_sample(STATUS, STATUS_W, n)
    system_ids = [f"SYS{fake.random_int(1000, 9999)}" for _ in range(n)]
    names = [f"Marketing Activity {i}" for i in ids]

    rows: list[dict[str, Any]] = []
    for i in range(n):
        chan_id, mode = fake.random_element(channels)
        if mode.lower() == "pull":
            # Pull-type
            end_d: Optional[Datetime] = start_dates[i] + timedelta(days=fake.random_int(0, 7))
            reach_co = fake.random_int(1, 1_000)
            reach_ind = reach_co * fake.random_int(1, 5)
            tgt_comp = tgt_pers = None
        else:
            # Push-type
            end_d = reach_co = reach_ind = None
            if random() < COMPANY_TARGET_RATIO:
                tgt_comp, tgt_pers = maybe_choice(company_ids), None
            else:
                tgt_comp, tgt_pers = None, maybe_choice(person_ids)

        rows.append(
            {
                MarketingActivityField.marketing_activity_id: ids[i],
                MarketingActivityField.audience_id: maybe_choice(audience_ids),
                MarketingActivityField.campaign_id: maybe_choice(campaign_ids),
                MarketingActivityField.marketing_asset_id: maybe_choice(marketing_asset_ids),
                MarketingActivityField.system_id: system_ids[i],
                MarketingActivityField.channel_id: chan_id,
                MarketingActivityField.targeted_company_id: tgt_comp,
                MarketingActivityField.targeted_person_id: tgt_pers,
                MarketingActivityField.end_date: end_d,
                MarketingActivityField.name: names[i],
                MarketingActivityField.reach_companies: reach_co,
                MarketingActivityField.reach_individuals: reach_ind,
                MarketingActivityField.start_date: start_dates[i],
                MarketingActivityField.status: status_vals[i],
            }
        )

    df = pl.DataFrame(rows).hstack(generate_source_id_mappings(SOURCE_TABLE_MAP, n))

    # Enforce correct order and dtypes via schema ------------------------------
    return df.select(list(MARKETING_ACTIVITY_SCHEMA.keys())).cast(MARKETING_ACTIVITY_SCHEMA)
