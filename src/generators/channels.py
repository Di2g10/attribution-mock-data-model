"""Contains functions to generate channel data."""

from __future__ import annotations

from typing import Any, Dict, List

import polars as pl

from ..random_utils import make_ids

__all__ = ["generate"]


def get_channel_data_from_registry(registry: Any) -> List[Dict[str, Any]]:
    """Get channel data from registry.

    :param registry: The schema registry containing channel data
    :returns: List of dictionaries containing channel data
    """
    channels: List[Dict[str, Any]] = []

    if registry is None:
        return channels

    try:
        # Get channels from registry
        channels_df = registry.cfg.channels
        if not channels_df.is_empty():
            # Convert to list of dictionaries
            for row in channels_df.iter_rows(named=True):
                channel = {
                    "name": row.get("Name", ""),
                    "group": row.get("Group", ""),
                    "identifiable_method": row.get("Identifiable method", ""),
                    "type": row.get("Type", ""),
                }
                channels.append(channel)
    except Exception as e:
        # If there's an error, return empty list
        print(f"Error loading channels: {e}")

    return channels


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of channel data.

    :param n: Number of channels to generate
    :param kwargs: Additional keyword arguments
        - registry: SchemaRegistry object containing channel data
    :returns: DataFrame containing generated channel data
    """
    # Extract registry if available
    registry = kwargs.get("registry")

    # Get channel data from registry
    channels = get_channel_data_from_registry(registry)

    # If no channels found or n is greater than available channels, generate additional channels
    if not channels or n > len(channels):
        # Generate IDs for all channels
        channel_ids = make_ids(n, "CHAN")

        # Create a DataFrame with default values for additional channels
        default_groups = ["ATL", "BTL", "Sales", "Other"]
        default_methods = ["IP Inferred", "Audience Inferred", "Known Person", "Unknown"]

        # Use existing channels and add generated ones to reach n
        if channels:
            existing_count = len(channels)
            additional_count = n - existing_count

            # Extract data from existing channels
            channel_ids = channel_ids[:additional_count]
            names = [f"Channel {i+1}" for i in range(additional_count)]
            groups = [default_groups[i % len(default_groups)] for i in range(additional_count)]
            methods = [default_methods[i % len(default_methods)] for i in range(additional_count)]
            types = [None] * additional_count
            comments = [""] * additional_count

            # Create DataFrame for additional channels
            additional_df = pl.DataFrame(
                {
                    "channel_id": channel_ids,
                    "name": names,
                    "group": groups,
                    "identifiable_method": methods,
                    "type": types,
                    "comment": comments,
                }
            )

            # Create DataFrame for existing channels
            existing_df = pl.DataFrame(
                {
                    "channel_id": make_ids(existing_count, "CHAN"),
                    "name": [c["name"] for c in channels],
                    "group": [c["group"] for c in channels],
                    "identifiable_method": [c["identifiable_method"] for c in channels],
                    "type": [c["type"] for c in channels],
                    "comment": [c["comment"] for c in channels],
                }
            )

            # Combine existing and additional channels
            return pl.concat([existing_df, additional_df])
        # Generate all channels if none exist
        return pl.DataFrame(
            {
                "channel_id": channel_ids,
                "name": [f"Channel {i+1}" for i in range(n)],
                "group": [default_groups[i % len(default_groups)] for i in range(n)],
                "identifiable_method": [
                    default_methods[i % len(default_methods)] for i in range(n)
                ],
                "type": [None] * n,
            }
        )
    # If we have enough channels in the registry, use them
    channels = channels[:n]  # Limit to n channels

    return pl.DataFrame(
        {
            "channel_id": make_ids(n, "CHAN"),
            "name": [c["name"] for c in channels],
            "group": [c["group"] for c in channels],
            "identifiable_method": [c["identifiable_method"] for c in channels],
            "type": [c["type"] for c in channels],
        }
    )
