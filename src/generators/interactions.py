"""Contains functions to generate interaction data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

import polars as pl

from ..random_utils import (
    fake,
    generate_mapped_values,
    make_ids,
    random_date,
    weighted_sample,
    require_df,
)

__all__ = [
    "create_interactions_dataframe",
    "generate",
    "generate_basic_data",
    "generate_channels",
    "generate_interaction_types",
    "get_channel_data_from_registry",
]

from ..validation import extract_id_column

# Default weights for channels (higher weight = more common)
DEFAULT_CHANNEL_WEIGHTS = {
    "Paid Digital Ads": 0.04,
    "Content Syndication": 0.04,
    "Web": 0.04,
    "Above the Line - Non Digital": 0.04,
    "Social Posts": 0.04,
    "Social Outbound Messages": 0.04,
    "Virtual Events": 0.04,
    "F2F Events": 0.04,
    "Webinars": 0.04,
    "Direct Mail": 0.04,
    "Whatsapp": 0.04,
    "RCS": 0.04,
    "Email": 0.30,
    "SMS": 0.04,
    "MMS": 0.04,
    "App Push Notification": 0.04,
    "Telemarketing": 0.25,
    "Online Chat": 0.10,
    "Salesperson Meetings": 0.04,
    "Salesperson Calls": 0.04,
    "Salesperson Email": 0.04,
    "Inbound Calls": 0.04,
}

# Interaction direction with weights
INTERACTION_DIRECTIONS = ["Inbound", "Outbound"]

# Weights for interaction directions (higher weight = more common)
INTERACTION_DIRECTION_WEIGHTS = [0.40, 0.60]  # Inbound  # Outbound

# Interaction outcome with weights
INTERACTION_OUTCOMES = ["Positive", "Neutral", "Negative", "Follow-up Required", "No Response"]

# Weights for interaction outcomes (higher weight = more common)
INTERACTION_OUTCOME_WEIGHTS = [
    0.40,  # Positive
    0.30,  # Neutral
    0.10,  # Negative
    0.15,  # Follow-up Required
    0.05,  # No Response
]

# Fallback interaction types to use when a channel doesn't have specific types
FALLBACK_INTERACTION_TYPES = ["Viewed", "Clicked", "Responded"]


def generate_basic_data(n: int) -> Tuple[List[str], List[Any], List[int]]:
    """Generate basic interaction data.

    :param n: Number of interactions to generate
    :returns: Tuple of (ids, interaction_dates, durations)
    """
    # Generate interaction IDs
    ids = make_ids(n, "INT")

    # Generate interaction dates
    interaction_dates = [random_date() for _ in range(n)]

    # Generate durations (in minutes)
    durations = [fake.random_int(min=1, max=120) for _ in range(n)]

    return ids, interaction_dates, durations


def get_channel_data_from_registry(registry: Any) -> Dict[str, List[str]]:
    """Get channels and interaction types from registry.

    :param registry: The schema registry containing channel and interaction type data
    :returns: Tuple of (channel_interaction_types, channel_weights)
    """
    if registry is None:
        raise ValueError("Registry is required to load channel and interaction types.")

    channel_interaction_types: Dict[str, List[str]] = {}

    # Get interaction types from registry
    interaction_types_df = registry.cfg.interaction_types
    if interaction_types_df.is_empty():
        raise ValueError("No interaction types found in the registry.")

    # Create mapping of channels to interaction types
    for row in interaction_types_df.iter_rows(named=True):
        channel = row.get("Channel Name")

        # Extract all non-empty values except "Channel" as interaction types
        interaction_types: List[str] = [
            cell
            for col, cell in row.items()
            if col not in ["Channel Name", "Interactions Concatenated"] and cell
        ]
        if interaction_types:
            channel_interaction_types[channel] = interaction_types

    empties = [ch for ch, types in channel_interaction_types.items() if len(types) == 0]
    if empties:
        raise ValueError(f"Channels with empty interaction type lists: {empties}.")

    return channel_interaction_types


def generate_channels(n: int, channel_weights: Dict[str, float]) -> List[str]:
    """Generate channels for each interaction.

    :param n: Number of interactions to generate
    :param channel_weights: Dictionary mapping channel names to weights
    :returns: List of channel names
    """
    return weighted_sample(
        list(channel_weights.keys()),
        list(channel_weights.values()),
        n,
    )


def generate_interaction_types(
    channels: List[str], channel_interaction_types: Dict[str, List[str]]
) -> List[str]:
    """Generate interaction types appropriate for each channel.

    :param channels: List of channel names
    :param channel_interaction_types: Dictionary mapping channel names to lists of interaction types
    :returns: List of interaction types

    This function uses the generate_mapped_values helper for efficient mapping and
    performance optimization, especially for large datasets.
    """
    # Use the generate_mapped_values helper function to efficiently map channels to interaction types
    # This provides better performance through vectorized operations and pre-generation of values
    return generate_mapped_values(
        parent_values=channels,
        mapping_dict=channel_interaction_types,
        verbose=True,
    )


@dataclass
class InteractionData:
    """Container for interaction data parameters."""

    n: int
    ids: List[str]
    interaction_dates: List[str]
    durations: List[int]
    channels: List[str]
    interaction_types: List[str]
    company_ids: List[str] | None = None
    person_ids: List[str] | None = None
    marketing_activity_ids: List[str] | None = None


def _generate_person_data(data: InteractionData) -> List[str]:
    """Generate person data for interactions.

    :param data: Interaction data parameters
    :returns: List of person names or IDs
    """
    if data.person_ids is None or len(data.person_ids) == 0:
        return [fake.name() for _ in data.ids]
    # Randomly select person IDs
    return [fake.random.choice(data.person_ids) for _ in data.ids]


def _generate_activity_data(data: InteractionData) -> List[str]:
    """Generate activity data for interactions.

    :param data: Interaction data parameters
    :returns: List of activity descriptions or IDs
    """
    if data.marketing_activity_ids is None or len(data.marketing_activity_ids) == 0:
        return [fake.sentence(nb_words=6) for _ in data.ids]
    # Randomly select activity IDs
    return [fake.random.choice(data.marketing_activity_ids) for _ in data.ids]


def _generate_followup_data(
    data: InteractionData, person_interacted: List[str]
) -> Tuple[List[str | None], Dict[str, str]]:
    """Generate follow-up interaction data.

    :param data: Interaction data parameters
    :param person_interacted: List of person names or IDs
    :returns: Tuple of (followfrom_interactions, interaction_to_person)
    """
    # Probability of an interaction having a follow-up interaction
    follow_up_probability = 0.2

    followfrom_interactions = []
    # Dictionary to track which person is associated with which interaction
    interaction_to_person: Dict[str, str] = {}

    for i in range(data.n):
        # Decide if this is a follow-up interaction
        if fake.random.random() < follow_up_probability and i > 0:
            # Select a random previous interaction
            prev_idx = fake.random_int(min=0, max=i - 1)
            prev_interaction_id = data.ids[prev_idx]
            followfrom_interactions.append(prev_interaction_id)

            # Use the same person as the previous interaction
            if prev_interaction_id in interaction_to_person:
                person_interacted[i] = interaction_to_person[prev_interaction_id]
        else:
            followfrom_interactions.append(None)

        # Record which person is associated with this interaction
        interaction_to_person[data.ids[i]] = person_interacted[i]

    return followfrom_interactions, interaction_to_person


def _generate_company_data(
    data: InteractionData,
    person_interacted: List[str],
    followfrom_interactions: List[str | None],
    interaction_to_person: Dict[str, str],
) -> List[str | None]:
    """Generate company data for interactions.

    :param data: Interaction data parameters
    :param person_interacted: List of person names or IDs
    :param followfrom_interactions: List of follow-up interaction IDs
    :param interaction_to_person: Dictionary mapping interaction IDs to person IDs
    :returns: List of company names or IDs
    """
    # Probability of a company being blank
    company_blank_probability = 0.1

    # Dictionary to track which company is associated with which person
    person_to_company: Dict[str, str | None] = {}

    if data.company_ids is None or len(data.company_ids) == 0:
        return [fake.company() for _ in data.ids]

    company_interacted = []
    for i in range(data.n):
        person = person_interacted[i]
        follow_from = followfrom_interactions[i]

        # If this is a follow-up interaction, use the same company as the original interaction
        if follow_from is not None and follow_from in interaction_to_person:
            original_person = interaction_to_person[follow_from]
            if (
                original_person in person_to_company
                and person_to_company[original_person] is not None
            ):
                company_interacted.append(person_to_company[original_person])
                continue

        # If this person already has a company, use it
        if person in person_to_company:
            company_interacted.append(person_to_company[person])
        else:
            # Otherwise, randomly select a company or None
            company = (
                None
                if fake.random.random() < company_blank_probability
                else fake.random.choice(data.company_ids)
            )
            company_interacted.append(company)
            # Record which company is associated with this person
            person_to_company[person] = company

    return company_interacted


def create_interactions_dataframe(data: InteractionData) -> pl.DataFrame:
    """Create a DataFrame with all interaction fields.

    :param data: Container with all interaction data parameters
    :returns: DataFrame containing all interaction data
    """
    # Generate person and activity data
    person_interacted = _generate_person_data(data)
    activity = _generate_activity_data(data)

    # Generate follow-up interactions
    followfrom_interactions, interaction_to_person = _generate_followup_data(
        data, person_interacted
    )

    # Generate company data
    company_interacted = _generate_company_data(
        data, person_interacted, followfrom_interactions, interaction_to_person
    )

    return pl.DataFrame(
        {
            "interaction_id": data.ids,
            "identification_method_type": weighted_sample(
                [
                    "Known From outbound Communication",
                    "Self Identification",
                    "Cookie match",
                    "IP Company Match",
                    None,
                ],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                data.n,
            ),
            "channel": data.channels,
            "interaction_type": data.interaction_types,
            "data_source_name": weighted_sample(
                ["CRM", "Marketing Automation", "Web Analytics", "Social Media", "Survey"],
                [0.3, 0.2, 0.2, 0.2, 0.1],
                data.n,
            ),
            "interacted Person ID": person_interacted,
            "interacted Company ID": company_interacted,
            "marketing_activity_id": activity,
            "interaction_date": data.interaction_dates,
            "interaction_dur": data.durations,
            "follow_from_interaction_id": followfrom_interactions,
        }
    )


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a high-performance DataFrame of interaction data using vectorised logic.

    :param n: Number of lf to generate
    :param kwargs: Supports `prior`, `registry`, `keep_channel`
    :raises ValueError: If required activity or relationship data is missing
    :returns: Polars DataFrame with interaction data
    """
    prior = kwargs.get("prior", {})
    registry = kwargs.get("registry")

    # --- 1. Gather activities from Marketing Activity sources ---
    marketing_activity_df = require_df(prior.get("Marketing Activity"), "Marketing Activity")
    person_df = require_df(prior.get("Person"), "Person")
    channel_df = require_df(prior.get("Channels"), "Channels")
    if not {"person_id", "company_id"}.issubset(person_df.columns):
        raise ValueError(
            "Missing the required person/company columns ['person_id', 'company_id'] in Person data."
        )

    if marketing_activity_df is None or not {
        "marketing_activity_id",
        "targeted_person_id",
        "targeted_company_id",
    }.issubset(marketing_activity_df.columns):
        raise ValueError("No activity data with valid person/company references found.")

    person_ids = extract_id_column(person_df, "person_id")
    fallback_series = pl.Series(
        "random_person_id",
        weighted_sample(person_ids, n=marketing_activity_df.height),
    )
    activities_df = (
        marketing_activity_df.join(channel_df, on="channel_id", how="inner", validate="m:1")
        .with_columns(fallback_series)
        .select(
            [
                pl.col("marketing_activity_id").alias("marketing_activity_id"),
                pl.coalesce(
                    pl.col("targeted_person_id"),
                    pl.col("random_person_id"),
                    pl.col("random_person_id"),
                ).alias("interacted_person_id"),
                pl.col("targeted_company_id").alias("interacted_company_id"),
                pl.col("channel_name").alias("channel_name"),
            ]
        )
    )

    # --- 2. Prioritise Person Company for company derivation if available ---

    # Build a deterministic person -> company map and prefer it over targeted_company_id
    person_company_map = (
        person_df.select(
            [
                pl.col("person_id").alias("interacted_person_id"),
                pl.col("company_id").alias("_person_company_id"),
            ]
        )
        .unique()
        .group_by("interacted_person_id")
        .agg(pl.first("_person_company_id").alias("_person_company_id"))
    )

    activities_df = (
        activities_df.join(person_company_map, on="interacted_person_id", how="left")
        .with_columns(
            pl.coalesce([pl.col("_person_company_id"), pl.col("interacted_company_id")]).alias(
                "interacted_company_id"
            )
        )
        .drop("_person_company_id")
    )

    # --- 3. Sample activities for interaction base ---
    interaction_ids = make_ids(n, "INT")
    sampled_df = activities_df.sample(n=n, with_replacement=True).with_columns(
        [
            pl.Series("interaction_id", interaction_ids),
            pl.Series("interaction_date", [random_date() for _ in range(n)]),
            pl.Series("interaction_dur", [fake.random_int(1, 120) for _ in range(n)]),
        ]
    )

    # --- 4. Assign follow_from_interaction_id with memory-efficient tracking ---
    followfrom: list[str | None] = [None] * n
    last_seen_by_person: dict[str, str] = {}
    follow_on_likelihood = 0.2
    for i in range(n):
        raw_person = sampled_df[i, "interacted_person_id"]
        person: Optional[str] = raw_person if isinstance(raw_person, str) else None
        if (
            person is not None
            and fake.random.random() < follow_on_likelihood
            and person in last_seen_by_person
        ):
            followfrom[i] = last_seen_by_person[person]
        if person is not None:
            last_seen_by_person[person] = sampled_df[i, "interaction_id"]

    sampled_df = sampled_df.with_columns(
        pl.Series("follow_from_interaction_id", followfrom),
    )

    # --- 5. Add remaining columns (channel, type, metadata) ---
    channel_map = get_channel_data_from_registry(registry)

    sampled_df = sampled_df.with_columns(
        [
            pl.col("channel_name").alias("channel_name"),
            pl.col("channel_name")
            .replace_strict(channel_map, default=["Error"])
            .list.sample(n=1)
            .list.first()
            .alias("interaction_type"),
            pl.Series(
                "identification_method_type",
                weighted_sample(
                    [
                        "Known From outbound Communication",
                        "Self Identification",
                        "Cookie match",
                        "IP Company Match",
                        None,
                    ],
                    [0.3, 0.3, 0.2, 0.1, 0.1],
                    n=n,
                ),
            ),
            pl.Series(
                "data_source_name",
                weighted_sample(
                    ["CRM", "Marketing Automation", "Web Analytics", "Social Media", "Survey"],
                    [0.3, 0.2, 0.2, 0.2, 0.1],
                    n=n,
                ),
            ),
        ]
    )

    # get if sample df interaction type is error and return the channel that caused the error.
    error_rows = sampled_df.filter(pl.col("interaction_type") == "Error")
    if not error_rows.is_empty():
        error_channels = set(error_rows.get_column("channel_name").to_list())
        raise ValueError(f"Error in interaction type from channel mapping:{error_channels}")

    # For IP-based identification, person may be unknown while company is known.
    # Force interacted_person_id to None in those cases to enable company-only linkage downstream.
    refs = (
        sampled_df.select(
            pl.col("follow_from_interaction_id").cast(pl.Utf8).alias("interaction_id")
        )
        .drop_nulls()
        .unique()
    )

    sampled_df = (
        sampled_df.join(
            refs.with_columns(pl.lit(True).alias("_is_referenced_flag")),
            on="interaction_id",
            how="left",
        )
        .with_columns(pl.col("_is_referenced_flag").fill_null(False).alias("_is_referenced"))
        .drop("_is_referenced_flag")
    )

    sampled_df = sampled_df.with_columns(
        pl.when(
            (pl.col("identification_method_type") == "IP Company Match")
            & pl.col("follow_from_interaction_id").is_null()
            & (~pl.col("_is_referenced"))
            & pl.col("interacted_company_id").is_null()
        )
        .then(pl.lit(None))
        .otherwise(pl.col("interacted_person_id"))
        .alias("interacted_person_id")
    ).drop("_is_referenced")

    # Ensure interacted_company_id is populated for IP Company Match lf
    # If role/targeted company did not supply a company, fill from the Company table.
    try:
        company_ids_list = extract_id_column(prior.get("Company"), "company_id")
    except Exception:
        company_ids_list = []

    if company_ids_list:
        # Choose a single fallback company to keep None-person company mapping consistent across lf
        fallback_company = fake.random.choice(company_ids_list)
        sampled_df = sampled_df.with_columns(pl.lit(fallback_company).alias("_ip_fill_company"))
        sampled_df = sampled_df.with_columns(
            pl.when(
                (pl.col("identification_method_type") == "IP Company Match")
                & pl.col("interacted_company_id").is_null()
            )
            .then(pl.col("_ip_fill_company"))
            .otherwise(pl.col("interacted_company_id"))
            .alias("interacted_company_id")
        ).drop("_ip_fill_company")

    # Add source fields and align names to spreadsheet expectations
    source_tables = weighted_sample(
        [
            "SFDC_TASK",
            "WEB_ANALYTICS",
            "MA_ACTIVITY",
            "SERVICE_DESK",
            "MANUAL_LOAD",
        ],
        [0.45, 0.2, 0.2, 0.1, 0.05],
        n,
    )
    sampled_df = sampled_df.with_columns(
        [
            pl.Series("sourcetable", source_tables),
            pl.Series(
                "sourceid", [f"SRC-{fake.random_int(min=100000, max=999999)}" for _ in range(n)]
            ),
            pl.Series(
                "sourceidfield",
                weighted_sample(
                    [
                        "Salesforce TaskId",
                        "GA4 Event Id",
                        "Marketo Activity Id",
                        "Jira Ticket Key",
                        "Manual Id",
                    ],
                    [0.45, 0.2, 0.2, 0.1, 0.05],
                    n,
                ),
            ),
        ]
    )

    # Ensure duration type is integer
    sampled_df = sampled_df.with_columns(
        [
            pl.col("interaction_dur").cast(pl.Int64, strict=False),
        ]
    )

    # Optionally drop channel column to maintain prior behaviour
    if kwargs.get("keep_channel", False):
        return sampled_df
    return sampled_df.drop("channel_name")
