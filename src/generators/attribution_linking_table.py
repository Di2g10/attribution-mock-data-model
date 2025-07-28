"""Contains functions to generate attribution linking table data."""

from __future__ import annotations

from typing import Any, Iterable

import polars as pl

from ..random_utils import fake, make_ids

__all__ = ["generate"]


def _extract_ids(prior: dict[str, pl.DataFrame], key: str, col: str) -> list[str]:
    """Safely extract a list of IDs from ``prior[key][col]``.

    :param prior: Dictionary of previously generated DataFrames.
    :param key: Key of the DataFrame to read from ``prior``.
    :param col: Column name to extract.
    :returns: List of string IDs; empty list when missing.
    """
    df = prior.get(key)
    if df is not None and col in df.columns:
        # Cast to list[str] - Polars may return Any
        return [str(v) for v in df[col].to_list()]
    return []


def _sample_or_none(pool: list[str], n: int) -> list[str | None]:
    """Sample IDs from a pool or return ``None`` when the pool is empty.

    :param pool: Candidate IDs.
    :param n: Number of samples to produce.
    :returns: List of sampled IDs (or ``None`` when pool is empty).
    """
    if not pool:
        return [None] * n
    # Faker's random has stable API and is already used elsewhere in the codebase
    return [fake.random_element(pool) for _ in range(n)]


def _collect_activity_ids(prior: dict[str, pl.DataFrame], sources: Iterable[str]) -> list[str]:
    """Collect activity IDs from multiple prior sources.

    :param prior: Dictionary of previously generated DataFrames.
    :param sources: Iterable of prior keys that contain an ``id`` column.
    :returns: Combined list of activity IDs.
    """
    ids: list[str] = []
    for key in sources:
        ids.extend(_extract_ids(prior, key, "id"))
    return ids


def generate_outcome_types(n: int) -> list[str]:
    """Generate outcome types for attribution links.

    :param n: Number of outcome types to generate.
    :returns: List of outcome types.
    """
    outcome_types = [
        "Purchase",
        "Renewal",
        "Upgrade",
        "Cross-sell",
        "Upsell",
        "Inquiry",
        "Demo Request",
        "Trial",
        "Consultation",
        "Webinar Registration",
    ]
    return [outcome_types[i % len(outcome_types)] for i in range(n)]


def generate_relation_types(n: int) -> list[str]:
    """Generate relation types for attribution links.

    :param n: Number of relation types to generate.
    :returns: List of relation types.
    """
    relation_types = [
        "Direct",
        "Indirect",
        "Influencer",
        "First Touch",
        "Last Touch",
        "Middle Touch",
        "Assisting",
        "Primary",
        "Secondary",
        "Tertiary",
    ]
    return [relation_types[i % len(relation_types)] for i in range(n)]


def generate_time_lags(n: int) -> list[int]:
    """Generate time lags for attribution links.

    :param n: Number of time lags to generate.
    :returns: List of time lags in days.
    """
    return [fake.random_int(min=0, max=90) for _ in range(n)]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of attribution linking table data.

    Branching is intentionally minimised to satisfy linter constraints.

    :param n: Number of attribution links to generate.
    :param kwargs: Additional keyword arguments.
        - prior: Dictionary of previously generated DataFrames.
    :returns: DataFrame containing generated attribution linking table data.
    """
    prior: dict[str, pl.DataFrame] = kwargs.get("prior", {})

    # Collect ID pools from prior
    activity_ids = _collect_activity_ids(prior, ("Pull Activity", "Push Activity"))
    interaction_ids = _extract_ids(prior, "Interactions", "interactionid")
    company_ids = _extract_ids(prior, "Company", "company_id")
    person_ids = _extract_ids(prior, "Person", "person_id")

    # Core IDs
    link_ids = make_ids(n, "LINK")
    outcome_ids = make_ids(n, "OUT")

    # Deterministic categorical / numeric fields
    outcome_types = generate_outcome_types(n)
    relation_types = generate_relation_types(n)
    time_lags = generate_time_lags(n)

    # Sample optional foreign keys
    selected_activity_ids = _sample_or_none(activity_ids, n)
    selected_interaction_ids = _sample_or_none(interaction_ids, n)
    selected_company_ids = _sample_or_none(company_ids, n)
    selected_person_ids = _sample_or_none(person_ids, n)

    return pl.DataFrame(
        {
            "link_id": link_ids,
            "activity_id": selected_activity_ids,
            "interaction_id": selected_interaction_ids,
            "outcome_type": outcome_types,
            "outcome_id": outcome_ids,
            "company_id": selected_company_ids,
            "person_id": selected_person_ids,
            "relation_type": relation_types,
            "time_lag": time_lags,
        }
    )
