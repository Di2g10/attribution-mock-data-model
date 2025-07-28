"""Contains a function to generate push activity data."""

from __future__ import annotations

from random import random
from typing import Any

import polars as pl

from ..random_utils import fake, make_ids, random_date, weighted_sample, generate_source_id_mappings

__all__ = ["generate"]

from ..validation import extract_id_column

# Push activity types with weights
PUSH_ACTIVITY_TYPES = [
    "Email",
    "Direct Mail",
    "SMS",
    "Push Notification",
    "Social Media Ad",
    "Display Ad",
    "Search Ad",
    "Telemarketing",
    "Event Invitation",
    "Newsletter",
]

# Weights for push activity types (higher weight = more common)
PUSH_ACTIVITY_TYPE_WEIGHTS = [
    0.30,  # Email
    0.05,  # Direct Mail
    0.10,  # SMS
    0.10,  # Push Notification
    0.15,  # Social Media Ad
    0.10,  # Display Ad
    0.10,  # Search Ad
    0.03,  # Telemarketing
    0.02,  # Event Invitation
    0.05,  # Newsletter
]

# Push activity status with weights
PUSH_ACTIVITY_STATUS = ["Sent", "Delivered", "Bounced", "Failed", "Scheduled"]

# Weights for push activity status (higher weight = more common)
PUSH_ACTIVITY_STATUS_WEIGHTS = [
    0.60,  # Sent
    0.25,  # Delivered
    0.08,  # Bounced
    0.05,  # Failed
    0.02,  # Scheduled
]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of push activity data."""
    # Extract prior data if available
    prior = kwargs.get("prior", {})
    # company_df = prior.get("Company", None)
    # campaign_df = prior.get("Campaigns", None)
    # person_df = prior.get("Person", None)
    marketing_asset_ids = extract_id_column(
        df=prior.get("Marketing Assets", None),
        id_field="marketing_asset_id",
    )
    company_ids = extract_id_column(
        df=prior.get("Company", None),
        id_field="company_id",
    )
    person_ids = extract_id_column(
        df=prior.get("Person", None),
        id_field="person_id",
    )
    campaign_ids = extract_id_column(
        df=prior.get("Campaigns", None),
        id_field="campaign_id",
    )
    audience_ids = extract_id_column(
        df=prior.get("Audience", None),
        id_field="audience_id",
    )

    company_targeted_ratio = 0.3
    # Randomly decide whether each row is targeted at a company or a person
    is_company_target = [random() < company_targeted_ratio for _ in range(n)]

    # Sample real person/company IDs accordingly
    targeted_person_ids = [
        None if is_company else fake.random_element(person_ids) for is_company in is_company_target
    ]
    targeted_company_ids = [
        fake.random_element(company_ids) if is_company else None for is_company in is_company_target
    ]

    # Generate push activity IDs
    ids = make_ids(n, "PUSH")

    # Note: We're not currently using company_df, campaign_df, or person_df
    # but keeping the parameters for future use

    # Generate activity dates
    activity_dates = [random_date() for _ in ids]

    # Probability of an activity being a control group
    control_group_probability = 0.5

    source_info = generate_source_id_mappings(
        [("marketo", "Activity_GUID"), ("Adobe Analytics", "View_ID")], n
    )

    # Generate push activity data
    return pl.DataFrame(
        {
            "id": ids,
            "name": [f"Push Activity {i}" for i in ids],
            "date": activity_dates,
            "control": [fake.random.random() < control_group_probability for _ in ids],
            "systemid": [f"SYS{fake.random_int(min=1000, max=9999)}" for _ in ids],
            "audience_id": weighted_sample(audience_ids, n=n),
            "campaign_id": weighted_sample(campaign_ids, n=n),
            "targeted_person_id": targeted_person_ids,
            "targeted_company_id": targeted_company_ids,
            "marketing_asset_id": weighted_sample(marketing_asset_ids, n=n),
            "status": weighted_sample(PUSH_ACTIVITY_STATUS, PUSH_ACTIVITY_STATUS_WEIGHTS, n),
        }
    ).hstack(source_info)
