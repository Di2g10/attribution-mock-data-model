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
    """Generate a DataFrame of person data.

    :param n: Number of lf to generate
    :param kwargs: May include `prior` mapping of previously generated objects
    :returns: Polars DataFrame of Person lf including `companyid`
    """
    # Try to source Company IDs from prior for FK coherence
    prior = kwargs.get("prior", {})
    company_df = prior.get("Company")
    if company_df is not None and "company_id" in company_df.columns:
        company_ids: list[str] = company_df.get_column("company_id").to_list()
    else:
        company_ids = []

    # Generate person IDs
    ids = make_ids(n, "PER")

    # Choose a company for each person (allow duplicates); None if not available
    company_id: list[str | None]
    company_id = weighted_sample(company_ids, n=n) if company_ids else [None] * n

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
            "company_id": company_id,
            "source_id": [f"SRC{fake.random_int(min=1000, max=9999)}" for _ in ids],
            "source_table": weighted_sample(
                ["CRM", "Marketing Automation", "Web Form", "Manual Entry", "Import"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                n,
            ),
            "source_id_field": [f"Field_{fake.random_int(min=1, max=100)}" for _ in ids],
            "…": [""] * n,
        }
    )
