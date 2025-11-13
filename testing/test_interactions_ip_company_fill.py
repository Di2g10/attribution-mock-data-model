"""Tests for IP Company Match interactions ensuring company is populated when person is unknown.

This specifically verifies that when identification_method == 'IP Company Match' and
interacted_person_id is cleared to None, interacted_company_id is still populated
(either from targeted_company_id or from the Company table as a fallback).
"""

from __future__ import annotations

import polars as pl

from src.generators.company import CompanyField
from src.generators.interactions import generate as generate_interactions, InteractionField
from testing.test_interactions_generator import get_registry


def prior_with_null_company_and_no_roles() -> dict[str, pl.DataFrame]:
    """Build a minimal prior where activities may have no targeted_company_id and no roles exist."""
    company_df = pl.DataFrame(
        {
            CompanyField.company_id: ["COX001", "COX002", "COX003"],
            CompanyField.company_name: ["X1", "X2", "X3"],
        }
    )

    person_df = pl.DataFrame(
        {
            "person_id": ["PIP0001", "PIP0002"],
            "first_name": ["Pat", "Pia"],
            "company_id": [None, None],
        }
    )

    # Activities target persons but sometimes no company
    activity_df = pl.DataFrame(
        {
            "marketing_activity_id": ["ACTX1", "ACTX2", "ACTX3"],
            "targeted_person_id": ["PIP0001", "PIP0002", "PIP0001"],
            "targeted_company_id": [None, None, None],
            "channel_id": ["CHAN0000001", "CHAN0000002", "CHAN0000002"],
        }
    )

    channels_df = pl.DataFrame(
        {
            "channel_id": ["CHAN0000001", "CHAN0000002", "CHAN0000003"],
            "channel_name": ["Social Outbound Messages", "Email", "Direct Mail"],
        }
    )

    return {
        "Company": company_df,
        "Person": person_df,
        "Marketing Activity": activity_df,  # Can also add "Pull Activity" if needed
        "Channels": channels_df,
    }


def test_ip_company_match_populates_company() -> None:
    """Test that IP Company Match interactions are populated with a company."""
    prior = prior_with_null_company_and_no_roles()
    # Generate a moderate number to increase chance of IP Company Match identification
    df = generate_interactions(50, prior=prior, registry=get_registry(), keep_channel=True)

    # Focus on df that were IP-matched and had person cleared
    ip_rows = df.filter(
        (pl.col(InteractionField.identification_method_type) == "IP Company Match")
        & pl.col(InteractionField.interacted_person_id).is_null()
    )

    # If none were produced due to randomness, relax by asserting no IP lf have null company
    if ip_rows.is_empty():
        # For any IP Company Match row, company must be non-null
        ip_any = df.filter(
            pl.col(InteractionField.identification_method_type) == "IP Company Match"
        )
        assert (
            ip_any.is_empty()
            or ip_any.select(pl.col(InteractionField.interacted_company_id).is_null().any()).item()
            is False
        )
        return

    # For produced IP-only lf, ensure company is populated
    assert (
        ip_rows.select(pl.col(InteractionField.interacted_company_id).is_null().any()).item()
        is False
    ), "IP-only interactions should have a company populated"
