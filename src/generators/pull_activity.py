"""Contains a function to generate pull activity data."""

from __future__ import annotations

from typing import Any

import polars as pl

from ..random_utils import fake, make_ids, random_date, weighted_sample

__all__ = ["generate"]

# Pull activity types with weights
PULL_ACTIVITY_TYPES = [
    "Website Visit",
    "Form Submission",
    "Content Download",
    "Webinar Registration",
    "Event Registration",
    "Demo Request",
    "Free Trial",
    "Contact Us",
    "Newsletter Signup",
    "Product Page View",
]

# Weights for pull activity types (higher weight = more common)
PULL_ACTIVITY_TYPE_WEIGHTS = [
    0.30,  # Website Visit
    0.15,  # Form Submission
    0.10,  # Content Download
    0.05,  # Webinar Registration
    0.05,  # Event Registration
    0.10,  # Demo Request
    0.10,  # Free Trial
    0.05,  # Contact Us
    0.05,  # Newsletter Signup
    0.05,  # Product Page View
]

# Pull activity source with weights
PULL_ACTIVITY_SOURCES = [
    "Organic Search",
    "Paid Search",
    "Direct",
    "Email",
    "Social Media",
    "Referral",
    "Display",
    "Affiliate",
    "Other",
]

# Weights for pull activity sources (higher weight = more common)
PULL_ACTIVITY_SOURCE_WEIGHTS = [
    0.25,  # Organic Search
    0.20,  # Paid Search
    0.15,  # Direct
    0.15,  # Email
    0.10,  # Social Media
    0.05,  # Referral
    0.05,  # Display
    0.03,  # Affiliate
    0.02,  # Other
]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of pull activity data."""
    # Extract prior data if available
    # prior = kwargs.get("prior", {})
    # company_df = prior.get("Company", None)
    # campaign_df = prior.get("Campaigns", None)
    # person_df = prior.get("Person", None)
    # Note: We're not currently using prior or these variables

    # Generate pull activity IDs
    ids = make_ids(n, "PULL")

    # Note: We're not currently using company_df, campaign_df, or person_df
    # but keeping the parameters for future use

    # Generate pull activity data with fields required by the spreadsheet
    return pl.DataFrame(
        {
            "id": ids,
            "name": [f"Pull Activity {i}" for i in ids],
            "reachindividuals": [fake.random_int(min=10, max=10000) for _ in ids],
            "datasource": weighted_sample(
                ["Web Analytics", "CRM", "Marketing Automation", "Social Media", "Survey"],
                [0.3, 0.2, 0.2, 0.2, 0.1],
                n,
            ),
            "audienceid": [f"AUD{fake.random_int(min=1000, max=9999)}" for _ in ids],
            "reachcompanies": [fake.random_int(min=1, max=1000) for _ in ids],
            "startdate": [random_date() for _ in ids],
            "enddate": [random_date() for _ in ids],
        }
    )
