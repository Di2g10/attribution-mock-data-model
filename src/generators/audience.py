"""Contains functions to generate audience data."""

from __future__ import annotations

from typing import Any, List

import polars as pl

from ..random_utils import fake, make_ids

__all__ = ["generate"]


def generate_audience_names(n: int) -> List[str]:
    """Generate names for audiences.

    :param n: Number of audience names to generate
    :returns: List of audience names
    """
    # List of common audience prefixes
    prefixes = [
        "High Value",
        "Enterprise",
        "SMB",
        "Public Sector",
        "Healthcare",
        "Financial",
        "Retail",
        "Manufacturing",
        "Technology",
        "Education",
    ]

    # List of common audience segments
    segments = [
        "Decision Makers",
        "Influencers",
        "IT Managers",
        "C-Suite",
        "Procurement",
        "Operations",
        "Sales",
        "Marketing",
        "Customer Service",
        "Technical",
    ]

    # Generate unique audience names
    audience_names = []
    for i in range(n):
        prefix_idx = i % len(prefixes)
        segment_idx = i % len(segments)

        # Add a number suffix if we need more names than combinations
        suffix = f" {i//len(prefixes) + 1}" if i >= len(prefixes) * len(segments) else ""

        audience_name = f"{prefixes[prefix_idx]} {segments[segment_idx]}{suffix}"
        audience_names.append(audience_name)

    return audience_names


def generate_audience_types(n: int) -> List[str]:
    """Generate types for audiences.

    :param n: Number of audience types to generate
    :returns: List of audience types
    """
    audience_types = [
        "Demographic",
        "Behavioral",
        "Firmographic",
        "Technographic",
        "Intent",
        "Engagement",
        "Lookalike",
        "Custom",
        "Predictive",
        "Retargeting",
    ]

    return [audience_types[i % len(audience_types)] for i in range(n)]


def generate_audience_criteria_descriptions(n: int) -> List[str]:
    """Generate criteria descriptions for audiences.

    :param n: Number of criteria descriptions to generate
    :returns: List of criteria descriptions
    """
    descriptions = []
    for _ in range(n):
        description = fake.paragraph(nb_sentences=2, variable_nb_sentences=True)
        descriptions.append(description)

    return descriptions


def generate_audience_criteria_technical(n: int) -> List[str]:
    """Generate technical criteria for audiences.

    :param n: Number of technical criteria to generate
    :returns: List of technical criteria
    """
    technical_criteria = []
    for _ in range(n):
        # Generate a SQL-like query string
        industry = fake.random_element(
            ["Healthcare", "Financial", "Retail", "Manufacturing", "Technology"]
        )
        size = fake.random_element(["Small", "Medium", "Large", "Enterprise"])
        location = fake.country()
        revenue = fake.random_element(["<1M", "1M-10M", "10M-100M", ">100M"])

        criteria = f"SELECT * FROM companies WHERE industry = '{industry}' AND size = '{size}' AND location = '{location}' AND revenue = '{revenue}'"
        technical_criteria.append(criteria)

    return technical_criteria


def generate_propensity_models(n: int) -> List[str]:
    """Generate propensity model names for audiences.

    :param n: Number of propensity model names to generate
    :returns: List of propensity model names
    """
    models = [
        "Purchase Intent Model",
        "Churn Prediction Model",
        "Upsell Opportunity Model",
        "Cross-sell Propensity Model",
        "Engagement Likelihood Model",
        "Conversion Probability Model",
        "Customer Lifetime Value Model",
        "Product Adoption Model",
        "Service Usage Model",
        "Renewal Likelihood Model",
    ]

    return [models[i % len(models)] for i in range(n)]


def generate_size_individuals(n: int) -> List[int]:
    """Generate individual sizes for audiences.

    :param n: Number of individual sizes to generate
    :returns: List of individual sizes
    """
    return [fake.random_int(min=100, max=1000000) for _ in range(n)]


def generate_size_companies(n: int) -> List[int]:
    """Generate company sizes for audiences.

    :param n: Number of company sizes to generate
    :returns: List of company sizes
    """
    return [fake.random_int(min=10, max=50000) for _ in range(n)]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of audience data.

    :param n: Number of audiences to generate
    :param kwargs: Additional keyword arguments
    :returns: DataFrame containing generated audience data
    """
    # Generate IDs for all audiences
    audience_ids = make_ids(n, "AUD")

    # Generate audience names
    audience_names = generate_audience_names(n)

    # Generate audience types
    audience_types = generate_audience_types(n)

    # Generate audience criteria descriptions
    criteria_descriptions = generate_audience_criteria_descriptions(n)

    # Generate audience technical criteria
    criteria_technical = generate_audience_criteria_technical(n)

    # Generate propensity models
    propensity_models = generate_propensity_models(n)

    # Generate size individuals
    size_individuals = generate_size_individuals(n)

    # Generate size companies
    size_companies = generate_size_companies(n)

    # Create DataFrame
    return pl.DataFrame(
        {
            "audience_id": audience_ids,
            "name": audience_names,
            "type": audience_types,
            "audience_criteria_description": criteria_descriptions,
            "audience_criteria_technical": criteria_technical,
            "propensity_model_used": propensity_models,
            "size_individuals": size_individuals,
            "size_companies": size_companies,
        }
    )
