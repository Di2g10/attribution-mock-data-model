"""Contains a function to generate campaign data."""

from __future__ import annotations

from typing import Any
from datetime import timedelta

import polars as pl

from ..random_utils import fake, make_ids, random_date, make_ids_with_duplicates, weighted_sample

__all__ = ["generate"]

# Constants for probability values
PARTNER_PROBABILITY = 0.5

# Campaign types with weights
CAMPAIGN_TYPES = [
    "Email",
    "Social Media",
    "Display",
    "Search",
    "Content Marketing",
    "Event",
    "Webinar",
    "Direct Mail",
    "Telemarketing",
    "Partner",
]

# Weights for campaign types (higher weight = more common)
CAMPAIGN_TYPE_WEIGHTS = [
    0.25,  # Email
    0.20,  # Social Media
    0.15,  # Display
    0.15,  # Search
    0.10,  # Content Marketing
    0.05,  # Event
    0.05,  # Webinar
    0.02,  # Direct Mail
    0.02,  # Telemarketing
    0.01,  # Partner
]

# Campaign status with weights
CAMPAIGN_STATUS = ["Active", "Completed", "Planned", "Paused", "Cancelled"]

# Weights for campaign status (higher weight = more common)
CAMPAIGN_STATUS_WEIGHTS = [
    0.40,  # Active
    0.30,  # Completed
    0.15,  # Planned
    0.10,  # Paused
    0.05,  # Cancelled
]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of campaign data."""
    # Extract company data from prior if available
    prior = kwargs.get("prior", {})
    company_df = prior.get("Company", None)

    # Generate campaign IDs
    ids = make_ids(n, "CAM")

    # Create company IDs to associate with campaigns
    company_ids = []
    if company_df is not None:
        # Use existing company IDs if available
        company_ids = company_df["company_id"].to_list()

    # Generate start dates
    start_dates = [random_date() for _ in ids]

    # Generate end dates (between 30 and 180 days after start date)
    end_dates = []
    for start_date in start_dates:
        duration = timedelta(days=fake.random_int(min=30, max=180))
        end_dates.append(start_date + duration)

    # Generate campaign data
    df = pl.DataFrame(
        {
            "campaign_id": ids,
            "campaign_name": [f"{fake.company()} {fake.word().capitalize()} Campaign" for _ in ids],
            "start_date": start_dates,
            "end_date": end_dates,
            "created_date": [random_date() for _ in ids],
            # Fields required by the spreadsheet
            "objective": [fake.sentence() for _ in ids],
            "outcome_targets": [fake.text(max_nb_chars=50) for _ in ids],
            "costs_actuals": [fake.random_int(min=1000, max=400000) for _ in ids],
            "costs_anticipated": [fake.random_int(min=5000, max=500000) for _ in ids],
            "brand": [fake.company() for _ in ids],
            "budget_timeframe": weighted_sample(
                ["Monthly", "Quarterly", "Annual", "One-time"], [0.3, 0.3, 0.3, 0.1], n
            ),
            "dmo_owner": [fake.name() for _ in ids],
            "partner": [
                fake.company() if fake.random.random() < PARTNER_PROBABILITY else None for _ in ids
            ],
            "product_family": [fake.word().capitalize() for _ in ids],
            "business_unit": weighted_sample(
                ["Marketing", "Sales", "Product", "Support", "Operations"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                n,
            ),
            "targeted_audience_id": [f"AUD{fake.random_int(min=1000, max=9999)}" for _ in ids],
        }
    )

    # Add company_id if company data is available
    if company_ids:
        df = df.with_columns(pl.Series("company_id", make_ids_with_duplicates(company_ids, n)))

    # Add parent_campaign_id (some campaigns are child campaigns of others)
    # About 30% of campaigns have a parent campaign
    return df.with_columns(pl.Series("parent_campaign_id", make_ids_with_duplicates(ids, n, 0.7)))
