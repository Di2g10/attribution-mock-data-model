"""Contains a function to generate person-company role data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import polars as pl

from ..random_utils import fake, random_date, weighted_sample

__all__ = ["generate"]

# Constants for probability values
END_DATE_PROBABILITY = 0.2  # 20% chance of role being ended
END_PREVIOUS_ROLES_PROBABILITY = 0.8  # 80% chance to end previous roles
DUMMY_END_DATE_PROBABILITY = 0.8  # 80% chance of having an end date


def _create_person_company_relationships(
    person_df: Optional[pl.DataFrame], company_df: Optional[pl.DataFrame], n: int
) -> pl.DataFrame:
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

    # Create a df from all person_ids
    df = pl.DataFrame({"person_id": person_ids})
    # assign each row a random company_id
    df = df.with_columns(
        pl.Series(
            "company_id",
            fake.random_elements(elements=company_ids, length=len(person_ids), unique=False),
        )
    )
    # give each row a random roletype
    df = df.with_columns(
        pl.Series(
            "roletype",
            weighted_sample(
                ["Primary", "Secondary", "Influencer", "Decision Maker", "End User"],
                n=len(person_ids),
            ),
        )
    )
    # give each row a random start_date
    df = df.with_columns(pl.Series("start_date", [random_date() for _ in range(len(person_ids))]))
    # Randomly keep a fraction of assignments so some people have no roles (improves downstream consistency)
    role_assignment_rate = 0.8
    keep_mask = [fake.random.random() < role_assignment_rate for _ in range(len(person_ids))]
    df = df.with_columns(pl.Series("_keep", keep_mask)).filter(pl.col("_keep")).drop("_keep")
    # give a random subset a duration then calculate the end_date

    # Use current row count so lengths match after any filtering
    current_n = df.height
    df = df.with_columns(
        pl.Series(
            "week_duration",
            [
                (
                    fake.random_int(min=1, max=156)
                    if fake.random.random() < END_DATE_PROBABILITY
                    else None
                )
                for _ in range(current_n)
            ],
        )
    )
    # calcualte end date from start date = duration
    df = df.with_columns(
        pl.when(pl.col("week_duration") is not None)
        .then(pl.col("start_date") + pl.duration(weeks=pl.col("week_duration")))
        .otherwise(None)
        .alias("end_date")
    )

    return df.drop("week_duration")


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of person-company role data.

    :param n: Not Used Here
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
    if relationships.height == 0:
        raise ValueError("No person-company relationships found")

    # Convert relationships to DataFrame
    return relationships
