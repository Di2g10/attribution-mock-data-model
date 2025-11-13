"""Contains functions to generate facilitation tool data."""

from __future__ import annotations
from enum import StrEnum

from typing import Any

import polars as pl


__all__ = ["generate"]


class FacilitationToolField(StrEnum):
    """Enumerates all output columns for the Facilitation Tool generator (snake_case aligned)."""

    facilitation_tool_name = "facilitation_tool_name"
    owner = "owner"
    facilitation_tool_id = "facilitation_tool_id"
    yearly_cost = "yearly_cost"


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of facilitation tool data.

    :param n: Number of facilitation tools to generate
    :param kwargs: Additional keyword arguments
    :returns: DataFrame containing generated facilitation tool data
    """
    # Define the dataset as a list of dictionaries
    names = [
        "Marketo",
        "Sprinkler",
        "Sprout",
        "ACM",
        "Eloqua",
        "Dialer",
        "Go Inspire",
    ]

    owners = [
        "Alice Smith",
        "Bob Johnson",
        "Carla White",
        "David Jones",
        "Emma Taylor",
        "Frank Wright",
        "Grace Patel",
    ]

    tool_ids = [
        "TOOL001",
        "TOOL002",
        "TOOL003",
        "TOOL004",
        "TOOL005",
        "TOOL006",
        "TOOL007",
    ]

    yearly_costs = [
        14400,
        10800,
        8400,
        12000,
        15000,
        6000,
        11000,
    ]

    # Create a Polars DataFrame
    return pl.DataFrame(
        {
            FacilitationToolField.facilitation_tool_name: names,
            FacilitationToolField.owner: owners,
            FacilitationToolField.facilitation_tool_id: tool_ids,
            FacilitationToolField.yearly_cost: yearly_costs,
        }
    )
