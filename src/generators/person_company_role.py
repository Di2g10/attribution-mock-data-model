"""Contains a function to generate person-company role data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import polars as pl

from ..random_utils import fake, random_date, weighted_sample

__all__ = ["generate"]

# Constants for probability values
END_DATE_PROBABILITY = 0.2  # 20% chance of role being ended
END_PREVIOUS_ROLES_PROBABILITY = 0.8  # 80% chance to end previous roles
DUMMY_END_DATE_PROBABILITY = 0.8  # 80% chance of having an end date


def _create_person_company_relationships(
    person_df: Optional[pl.DataFrame], company_df: Optional[pl.DataFrame], n: int
) -> List[Dict[str, Any]]:
    """Create relationships between people and companies.

    :param person_df: DataFrame containing person data
    :param company_df: DataFrame containing company data
    :param n: Number of relationships to generate
    :returns: List of dictionaries containing relationship data
    """
    relationships: List[Dict[str, Any]] = []
    person_ids: List[str] = []
    company_ids: List[str] = []

    # Extract person IDs if available
    if person_df is not None and "person_id" in person_df.columns:
        person_ids = person_df["person_id"].to_list()

    # Extract company IDs if available
    if company_df is not None and "company_id" in company_df.columns:
        company_ids = company_df["company_id"].to_list()

    # If we don't have person or company data, return empty list
    if not person_ids or not company_ids:
        return relationships

    # Track active roles for each person to ensure most people have only one active role at a time
    person_active_roles: Dict[str, List[Dict[str, Any]]] = {}

    # Generate n relationships
    for _ in range(n):
        # Select a random person and company
        person_id = fake.random.choice(person_ids)
        company_id = fake.random.choice(company_ids)

        # Generate start and end dates
        start_date = random_date()

        # Determine if role has an end date (to allow for some current roles)
        has_end_date = fake.random.random() < END_DATE_PROBABILITY

        # End date is between 1 month and 2 years after start date
        end_date = None
        if has_end_date:
            days_active = fake.random_int(min=30, max=730)  # Between 1 month and 2 years
            end_date = start_date + timedelta(days=days_active)

        # Create the relationship
        relationship = {
            "person_id": person_id,
            "company_id": company_id,
            "roletype": weighted_sample(
                ["Primary", "Secondary", "Influencer", "Decision Maker", "End User"]
            )[0],
            "start_date": start_date,
            "end_date": end_date,
        }

        # Check for overlapping active roles for this person
        if person_id not in person_active_roles:
            person_active_roles[person_id] = []

        # If this person already has active roles, chance to end previous roles
        # before this one starts (to ensure most people have only one active role at a time)
        if person_active_roles[person_id] and fake.random.random() < END_PREVIOUS_ROLES_PROBABILITY:
            for active_role in person_active_roles[person_id]:
                # If the active role doesn't have an end date, give it one
                if active_role["end_date"] is None:
                    # End date is before the new role starts but after the active role's start date
                    active_role_start = active_role["start_date"]
                    # Calculate the maximum number of days before the new role starts
                    # that we can set the end date to, ensuring it's after the active role's start date
                    max_days_before = min(30, (start_date - active_role_start).days - 1)

                    # If there's not enough time between the active role's start date and the new role's start date,
                    # set the end date to be 1 day after the active role's start date
                    if max_days_before < 1:
                        active_role["end_date"] = active_role_start + timedelta(days=1)
                    else:
                        days_before = fake.random_int(min=1, max=max_days_before)
                        active_role["end_date"] = start_date - timedelta(days=days_before)

        # Add this relationship to the person's active roles
        person_active_roles[person_id].append(relationship)

        # Add the relationship to our list
        relationships.append(relationship)

    return relationships


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of person-company role data.

    :param n: Number of person-company role relationships to generate
    :param kwargs: Additional keyword arguments
        - prior: Dictionary of previously generated DataFrames
    :returns: DataFrame containing generated person-company role data
    """
    # Extract prior data if available
    prior = kwargs.get("prior", {})

    # Extract person and company data
    person_df = prior.get("Person")
    company_df = prior.get("Company")

    # Create person-company relationships
    relationships = _create_person_company_relationships(person_df, company_df, n)

    # If we couldn't create relationships (no person or company data), create dummy data
    if not relationships:
        # Generate start dates first
        start_dates = [random_date() for _ in range(n)]

        # Generate end dates based on start dates to ensure they're always after
        end_dates: List[Optional[datetime]] = []
        for start_date in start_dates:
            if fake.random.random() < DUMMY_END_DATE_PROBABILITY:  # Chance of having an end date
                days_active = fake.random_int(min=30, max=730)  # Between 1 month and 2 years
                end_dates.append(start_date + timedelta(days=days_active))
            else:
                end_dates.append(None)

        return pl.DataFrame(
            {
                "person_id": [f"PER{fake.random_int(min=1, max=9999):07d}" for _ in range(n)],
                "company_id": [f"CO{fake.random_int(min=1, max=9999):07d}" for _ in range(n)],
                "roletype": weighted_sample(
                    ["Primary", "Secondary", "Influencer", "Decision Maker", "End User"], None, n
                ),
                "start_date": start_dates,
                "end_date": end_dates,
            }
        )

    # Convert relationships to DataFrame
    return pl.DataFrame(
        {
            "person_id": [r["person_id"] for r in relationships],
            "company_id": [r["company_id"] for r in relationships],
            "roletype": [r["roletype"] for r in relationships],
            "start_date": [r["start_date"] for r in relationships],
            "end_date": [r["end_date"] for r in relationships],
        }
    )
