"""Contains a function to generate company data."""

from __future__ import annotations

from math import floor
from typing import Any, Callable

import numpy as np
import polars as pl

from ..random_utils import fake, make_ids, make_ids_with_duplicates, weighted_sample

__all__ = ["generate"]

# BT business customer verticals with weights
BT_BUSINESS_VERTICALS = [
    "Financial Services",
    "Healthcare",
    "Retail",
    "Manufacturing",
    "Public Sector",
    "Education",
    "Professional Services",
    "Media & Entertainment",
    "Technology",
    "Utilities",
    "Transportation & Logistics",
    "Construction",
    "Hospitality",
    "Telecommunications",
    "Pharmaceuticals",
    "Energy",
    "Insurance",
    "Real Estate",
    "Automotive",
    "Agriculture",
]

# Weights for verticals (higher weight = more common)
BT_BUSINESS_VERTICAL_WEIGHTS = [
    0.12,  # Financial Services
    0.10,  # Healthcare
    0.09,  # Retail
    0.09,  # Manufacturing
    0.08,  # Public Sector
    0.07,  # Education
    0.07,  # Professional Services
    0.06,  # Media & Entertainment
    0.06,  # Technology
    0.05,  # Utilities
    0.05,  # Transportation & Logistics
    0.04,  # Construction
    0.03,  # Hospitality
    0.03,  # Telecommunications
    0.02,  # Pharmaceuticals
    0.01,  # Energy
    0.01,  # Insurance
    0.01,  # Real Estate
    0.01,  # Automotive
    0.01,  # Agriculture
]


def _parent_company(company_ids: list[str]) -> Callable[[int], list[str | None]]:
    # Use the new Generator API from NumPy
    rng = np.random.default_rng()

    # Probability of a company having a parent company
    parent_company_probability = 0.10

    def _gen(n: int) -> list[str | None]:
        return [
            rng.choice(company_ids) if rng.random() < parent_company_probability else None
            for _ in range(n)
        ]

    return _gen


def generate(n: int, **kwargs: Any) -> pl.DataFrame:  # registry/prior unused yet
    """Generate a DataFrame of company data."""
    ids = make_ids(n, "CO")
    # Ensure at least one owner_id even for small values of n
    owner_count = max(1, floor(n / 20))
    owner_ids = make_ids(owner_count, "OWN")
    return pl.DataFrame(
        {
            "company_id": ids,
            "industry": [fake.job().split(",")[0] for _ in ids],
            "Owner_ID": make_ids_with_duplicates(owner_ids, n),
            "Parent_Company_ID": make_ids_with_duplicates(ids, n, 0.8),
            "Company Business Type": weighted_sample(
                ["CUG", "PHCO", "Billing Account"], [0.2, 0.3, 0.5], n
            ),
            "Vertical": weighted_sample(BT_BUSINESS_VERTICALS, BT_BUSINESS_VERTICAL_WEIGHTS, n),
            "location": [fake.city() for _ in ids],
            "Company Market Channel": weighted_sample(
                ["Direct", "Indirect", "Partner", "Online", "Retail"], [0.4, 0.2, 0.2, 0.1, 0.1], n
            ),
        }
    )
