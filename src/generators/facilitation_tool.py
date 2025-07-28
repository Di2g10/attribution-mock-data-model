"""Contains functions to generate facilitation tool data."""

from __future__ import annotations

from typing import Any

import polars as pl


__all__ = ["generate"]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of facilitation tool data.

    :param n: Number of facilitation tools to generate
    :param kwargs: Additional keyword arguments
    :returns: DataFrame containing generated facilitation tool data
    """
    # Define the dataset as a list of dictionaries
    data = [
        {
            "Name": "Marketo",
            "Owner": "Alice Smith",
            "Yearly Cost": 14400,
            "Tool_id": "TOOL001",
        },
        {
            "Name": "Sprinkler",
            "Owner": "Bob Johnson",
            "Yearly Cost": 10800,
            "Tool_id": "TOOL002",
        },
        {
            "Name": "Sprout",
            "Owner": "Carla White",
            "Yearly Cost": 8400,
            "Tool_id": "TOOL003",
        },
        {
            "Name": "ACM",
            "Owner": "David Jones",
            "Yearly Cost": 12000,
            "Tool_id": "TOOL004",
        },
        {
            "Name": "Eloqua",
            "Owner": "Emma Taylor",
            "Yearly Cost": 15000,
            "Tool_id": "TOOL005",
        },
        {
            "Name": "Dialer",
            "Owner": "Frank Wright",
            "Yearly Cost": 6000,
            "Tool_id": "TOOL006",
        },
        {
            "Name": "Go Inspire",
            "Owner": "Grace Patel",
            "Yearly Cost": 11000,
            "Tool_id": "TOOL007",
        },
    ]

    # Create a Polars DataFrame
    return pl.DataFrame(data)
