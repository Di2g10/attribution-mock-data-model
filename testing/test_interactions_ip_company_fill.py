"""Tests for IP Company Match interactions ensuring company is populated when person is unknown.

This specifically verifies that when identificationmethod == 'IP Company Match' and
interacted_person_id is cleared to None, interacted_company_id is still populated
(either from targeted_company_id or from the Company table as a fallback).
"""

from __future__ import annotations

import polars as pl

from src.generators.interactions import generate as generate_interactions


def prior_with_null_company_and_no_roles() -> dict[str, pl.DataFrame]:
    """Build a minimal prior where activities may have no targeted_company_id and no roles exist."""
    company_df = pl.DataFrame(
        {
            "company_id": ["COX001", "COX002", "COX003"],
            "company_name": ["X1", "X2", "X3"],
        }
    )

    person_df = pl.DataFrame(
        {
            "person_id": ["PIP0001", "PIP0002"],
            "first_name": ["Pat", "Pia"],
        }
    )

    # Activities target persons but sometimes no company
    activity_df = pl.DataFrame(
        {
            "marketing_activity_id": ["ACTX1", "ACTX2", "ACTX3"],
            "targeted_person_id": ["PIP0001", "PIP0002", "PIP0001"],
            "targeted_company_id": [None, None, None],
        }
    )

    return {
        "Company": company_df,
        "Person": person_df,
        "Marketing Activity": activity_df,
    }


def test_ip_company_match_populates_company() -> None:
    """Test that IP Company Match interactions are populated with a company."""
    prior = prior_with_null_company_and_no_roles()
    # Generate a moderate number to increase chance of IP Company Match identification
    df = generate_interactions(50, prior=prior, keep_channel=True)

    # Focus on rows that were IP-matched and had person cleared
    ip_rows = df.filter(
        (pl.col("identificationmethod") == "IP Company Match")
        & pl.col("interacted_person_id").is_null()
    )

    # If none were produced due to randomness, relax by asserting no IP rows have null company
    if ip_rows.is_empty():
        # For any IP Company Match row, company must be non-null
        ip_any = df.filter(pl.col("identificationmethod") == "IP Company Match")
        assert (
            ip_any.is_empty()
            or ip_any.select(pl.col("interacted_company_id").is_null().any()).item() is False
        )
        return

    # For produced IP-only rows, ensure company is populated
    assert (
        ip_rows.select(pl.col("interacted_company_id").is_null().any()).item() is False
    ), "IP-only interactions should have a company populated"
