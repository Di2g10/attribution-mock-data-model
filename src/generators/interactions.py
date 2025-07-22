"""Contains a function to generate interaction data."""

from __future__ import annotations

from typing import Any

import polars as pl

from ..random_utils import fake, make_ids, random_date, weighted_sample

__all__ = ["generate"]

# Interaction types with weights
INTERACTION_TYPES = [
    "Phone Call",
    "Email",
    "Meeting",
    "Chat",
    "Social Media",
    "Video Call",
    "Support Ticket",
    "Demo",
    "Training",
    "Consultation",
]

# Weights for interaction types (higher weight = more common)
INTERACTION_TYPE_WEIGHTS = [
    0.25,  # Phone Call
    0.30,  # Email
    0.15,  # Meeting
    0.10,  # Chat
    0.05,  # Social Media
    0.05,  # Video Call
    0.05,  # Support Ticket
    0.02,  # Demo
    0.02,  # Training
    0.01,  # Consultation
]

# Interaction direction with weights
INTERACTION_DIRECTIONS = ["Inbound", "Outbound"]

# Weights for interaction directions (higher weight = more common)
INTERACTION_DIRECTION_WEIGHTS = [0.40, 0.60]  # Inbound  # Outbound

# Interaction outcome with weights
INTERACTION_OUTCOMES = ["Positive", "Neutral", "Negative", "Follow-up Required", "No Response"]

# Weights for interaction outcomes (higher weight = more common)
INTERACTION_OUTCOME_WEIGHTS = [
    0.40,  # Positive
    0.30,  # Neutral
    0.10,  # Negative
    0.15,  # Follow-up Required
    0.05,  # No Response
]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of interaction data."""
    # Extract prior data if available
    # prior = kwargs.get("prior", {})
    # Note: We're not currently using prior data

    # Generate interaction IDs
    ids = make_ids(n, "INT")

    # Note: We're not currently using company_df or person_df
    # but keeping the parameters for future use

    # Generate interaction dates
    interaction_dates = [random_date() for _ in ids]

    # Generate durations (in minutes)
    durations = [fake.random_int(min=1, max=120) for _ in ids]

    # Probability of an interaction having a follow-up interaction
    follow_up_probability = 0.3

    # Generate interaction data with fields required by the spreadsheet
    return pl.DataFrame(
        {
            "interactionid": ids,
            "identificationmethod": weighted_sample(
                ["CRM", "Marketing Automation", "Web Analytics", "Manual Entry", "Social Media"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                n,
            ),
            "type": weighted_sample(INTERACTION_TYPES, INTERACTION_TYPE_WEIGHTS, n),
            "datasource": weighted_sample(
                ["CRM", "Marketing Automation", "Web Analytics", "Social Media", "Survey"],
                [0.3, 0.2, 0.2, 0.2, 0.1],
                n,
            ),
            "personinteracted": [fake.name() for _ in ids],
            "activity": [fake.sentence(nb_words=6) for _ in ids],
            "companyinteracted": [fake.company() for _ in ids],
            "date": interaction_dates,
            "duration": durations,
            "followfrominteraction": [
                (
                    f"INT{fake.random_int(min=1, max=9999):07d}"
                    if fake.random.random() < follow_up_probability
                    else None
                )
                for _ in ids
            ],
        }
    )
