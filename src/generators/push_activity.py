"""Contains a function to generate push activity data."""

from __future__ import annotations

from typing import Any

import polars as pl

from ..random_utils import fake, make_ids, random_date, weighted_sample

__all__ = ["generate"]

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
    # prior = kwargs.get("prior", {})
    # company_df = prior.get("Company", None)
    # campaign_df = prior.get("Campaigns", None)
    # person_df = prior.get("Person", None)
    # Note: We're not currently using prior or these variables

    # Generate push activity IDs
    ids = make_ids(n, "PUSH")

    # Note: We're not currently using company_df, campaign_df, or person_df
    # but keeping the parameters for future use

    # Generate activity dates
    activity_dates = [random_date() for _ in ids]

    # Probability of an activity being a control group
    control_group_probability = 0.5

    # Generate push activity data
    return pl.DataFrame(
        {
            "id": ids,
            "name": [f"Push Activity {i}" for i in ids],
            "date": activity_dates,
            "control": [fake.random.random() < control_group_probability for _ in ids],
            "systemid": [f"SYS{fake.random_int(min=1000, max=9999)}" for _ in ids],
            "audienceid": [f"AUD{fake.random_int(min=1000, max=9999)}" for _ in ids],
            "campaign": [f"Campaign {fake.word().capitalize()}" for _ in ids],
            "companytargeted": [fake.company() for _ in ids],
            "persontargeted": [fake.name() for _ in ids],
            "marketingasset": [f"Asset {fake.word().capitalize()}" for _ in ids],
            "status": weighted_sample(PUSH_ACTIVITY_STATUS, PUSH_ACTIVITY_STATUS_WEIGHTS, n),
        }
    )
