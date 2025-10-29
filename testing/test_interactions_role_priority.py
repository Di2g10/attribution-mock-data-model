"""Additional tests to verify company derivation priority in interactions generator.

These tests ensure that when a Person Company Role table is provided:
- interacted_company_id is derived from the person's role company where available;
- this role-derived value is prioritised over Marketing Activity.targeted_company_id;
- when targeted_company_id is null, the role is used as the fill.
"""

from typing import Dict

import polars as pl

from src.generators.interactions import generate as generate_interactions
from testing.test_interactions_generator import get_registry


def create_prior() -> Dict[str, pl.DataFrame]:
    """Build a minimal prior including a role table to drive company selection.

    We deliberately create a mismatch between the activity's targeted_company_id and
    the person's role company to verify that the role-derived company is prioritised.
    """
    company_df = pl.DataFrame(
        {
            "company_id": ["CO0000101", "CO0000102"],
            "company_name": ["Role Co", "Activity Co"],
        }
    )

    person_df = pl.DataFrame(
        {
            "person_id": ["PER0100001"],
            "first_name": ["Alex"],
            "company_id": ["CO0000101"],
        }
    )

    # Two activities that both target the same person:
    # - One with a conflicting targeted_company_id
    # - One with a null targeted_company_id
    activity_df = pl.DataFrame(
        {
            "marketing_activity_id": ["ACT0100001", "ACT0100002"],
            "targeted_person_id": ["PER0100001", "PER0100001"],
            "targeted_company_id": ["CO0000102", None],
            "channel_id": ["CHAN0000001", "CHAN0000002"],
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


def test_role_priority_over_targeted_company() -> None:
    """Role-based company should override targeted_company_id when they differ."""
    prior = create_prior()
    # Generate several df to sample both activities
    df = generate_interactions(20, prior=prior, registry=get_registry(), keep_channel=True)

    # All df for this person should point to the role company CO0000101
    rows = df.filter(pl.col("interacted_person_id") == "PER0100001")
    assert not rows.is_empty(), "Expected generated interactions for the test person"
    assert rows.select(pl.col("interacted_company_id").unique()).to_series().to_list() == [
        "CO0000101"
    ], "interacted_company_id should be derived from Person Company when available"


def test_role_fills_when_targeted_company_null() -> None:
    """When targeted_company_id is null, role-derived company must be used."""
    prior = create_prior()
    df = generate_interactions(10, prior=prior, registry=get_registry(), keep_channel=False)

    rows = df.filter(pl.col("marketing_activity_id") == "ACT0100002")
    assert not rows.is_empty(), "Expected interactions from the activity with null company"
    # All such lf should use the role company
    assert rows.select(pl.col("interacted_company_id").unique()).to_series().to_list() == [
        "CO0000101"
    ], "Null targeted_company_id should be filled from Person Company Role"


if __name__ == "__main__":
    test_role_priority_over_targeted_company()
