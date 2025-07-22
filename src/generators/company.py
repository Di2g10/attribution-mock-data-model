"""Contains a function to generate company data."""

from __future__ import annotations

from typing import Any

import polars as pl

from ..random_utils import fake, make_ids, random_date

__all__ = ["generate"]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:  # registry/prior unused yet
    """Generate a DataFrame of company data."""
    ids = make_ids(n, "CO")
    return pl.DataFrame(
        {
            "company_id": ids,
            "company_name": [fake.company() for _ in ids],
            "industry": [fake.job().split(",")[0] for _ in ids],
            "created_ts": [random_date() for _ in ids],
        }
    )
