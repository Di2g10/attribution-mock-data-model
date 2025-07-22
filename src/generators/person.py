"""Contains a function to generate person data."""

from __future__ import annotations

from typing import Any

import polars as pl

from ..random_utils import fake, make_ids, weighted_sample

__all__ = ["generate"]

# Person roles with weights
PERSON_ROLES = [
    "Employee",
    "Contractor",
    "Consultant",
    "Manager",
    "Director",
    "Executive",
    "Customer",
    "Partner",
    "Vendor",
    "Investor",
]

# Weights for roles (higher weight = more common)
PERSON_ROLE_WEIGHTS = [
    0.30,  # Employee
    0.15,  # Contractor
    0.10,  # Consultant
    0.15,  # Manager
    0.10,  # Director
    0.05,  # Executive
    0.05,  # Customer
    0.05,  # Partner
    0.03,  # Vendor
    0.02,  # Investor
]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of person data."""
    # Extract company data from prior if available
    # prior = kwargs.get("prior", {})
    # company_df = prior.get("Company", None)
    # Note: We're not currently using prior or company_df

    # Generate person IDs
    ids = make_ids(n, "PER")

    # Note: We're not currently using company_df
    # but keeping the parameter for future use

    # Generate person data
    return pl.DataFrame(
        {
            "person_id": ids,
            # Fields required by the spreadsheet
            "persona": weighted_sample(
                ["Decision Maker", "Influencer", "End User", "Technical Buyer", "Economic Buyer"],
                [0.2, 0.3, 0.2, 0.15, 0.15],
                n,
            ),
            "source_id": [f"SRC{fake.random_int(min=1000, max=9999)}" for _ in ids],
            "source_table": weighted_sample(
                ["CRM", "Marketing Automation", "Web Form", "Manual Entry", "Import"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                n,
            ),
            "source_id_field": [f"Field_{fake.random_int(min=1, max=100)}" for _ in ids],
        }
    )
