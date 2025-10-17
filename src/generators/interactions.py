"""Contains functions to generate interaction data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

import polars as pl

from ..random_utils import fake, generate_mapped_values, make_ids, random_date, weighted_sample

__all__ = [
    "create_interactions_dataframe",
    "generate",
    "generate_basic_data",
    "generate_channels",
    "generate_interaction_types",
    "get_channel_data_from_registry",
]

from ..validation import extract_id_column

# Default channels with their associated interaction types
# This will be used as a fallback if the configuration doesn't provide this information
DEFAULT_CHANNEL_INTERACTION_TYPES: Dict[str, List[str]] = {
    "Paid Digital Ads": ["Viewed", "Clicked", "Submit Form"],
    "Content Syndication": ["Viewed", "Clicked", "Submit Form"],
    "Web": ["Page View", "Link Click", "Submit Form", "Watch Video", "Download", "Live Chat?"],
    "Above the Line - Non Digital": ["Viewed"],
    "Social Posts": ["Viewed", "Clicked", "Responded"],
    "Social Outbound Messages": ["Viewed", "Clicked", "Responded", "Opt-Out"],
    "Virtual Events": ["Registered", "Attended", "View on Demand"],
    "F2F Events": ["Registered", "Attended"],
    "Webinars": ["Registered", "Attended", "View on Demand"],
    "Direct Mail": ["Sent", "Delivered", "Bounced"],
    "Whatsapp": ["Sent", "Received", "Read", "Clicked", "Responded", "Opt-Out"],
    "RCS": ["Sent", "Received", "Read", "Clicked", "Responded", "Opt-Out"],
    "Email": ["Sent", "Received", "Bounced", "Opened", "Clicked", "Opt-Out", "Responded"],
    "SMS": ["Sent", "Received", "Bounced", "Clicked", "Responsed", "Opt-Out"],
    "MMS": ["Sent", "Received", "Bounced", "Clicked", "Responsed", "Opt-Out"],
    "App Push Notification": ["Sent", "Received", "Clicked"],
    "Sales Meetings": ["Invited", "Attended"],
    "Sales Calls": ["Dialled", "Answered", "Engaged"],
    "Sales Email": ["Sent", "Received", "Bounced", "Opened", "Clicked", "Opt-Out", "Responded"],
    "Inbound Calls": ["Called"],
    "Phone": ["Phone Call"],
    "In Person": ["Meeting", "Demo", "Training", "Consultation"],
    "Chat": ["Chat"],
    "Social Media": ["Social Media"],
    "Video": ["Video Call"],
    "Support": ["Support Ticket"],
}

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
    "Sales Meetings": 0.04,
    "Sales Calls": 0.04,
    "Sales Email": 0.04,
    "Inbound Calls": 0.04,
    "Phone": 0.25,
    "In Person": 0.15,
    "Chat": 0.10,
    "Social Media": 0.05,
    "Video": 0.05,
    "Support": 0.10,
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


def get_channel_data_from_registry(registry: Any) -> Tuple[Dict[str, List[str]], Dict[str, float]]:
    """Get channels and interaction types from registry.

    :param registry: The schema registry containing channel and interaction type data
    :returns: Tuple of (channel_interaction_types, channel_weights)
    """
    channel_interaction_types = DEFAULT_CHANNEL_INTERACTION_TYPES.copy()
    channel_weights = DEFAULT_CHANNEL_WEIGHTS.copy()

    if registry is None:
        return channel_interaction_types, channel_weights

    try:
        # Get channels from registry
        channels_df = registry.cfg.channels
        if not channels_df.is_empty():
            # Extract channel names
            channel_names = channels_df["Name"].to_list()
            # Update channel weights with equal weights if not already defined
            for channel in channel_names:
                if channel not in channel_weights:
                    channel_weights[channel] = 1.0 / len(channel_names)

            # Get interaction types from registry
            interaction_types_df = registry.cfg.interaction_types
            if not interaction_types_df.is_empty():
                # Create mapping of channels to interaction types
                for row in interaction_types_df.iter_rows(named=True):
                    channel = row.get("Channel", "")
                    if channel and channel in channel_names:
                        # Extract all non-empty values except "Channel" as interaction types
                        interaction_types = [
                            value for key, value in row.items() if key != "Channel" and value
                        ]
                        if interaction_types:
                            channel_interaction_types[channel] = interaction_types

            # Ensure every channel from the spreadsheet has a mapping; if missing, use fallback types
            for channel in channel_names:
                if channel not in channel_interaction_types:
                    channel_interaction_types[channel] = FALLBACK_INTERACTION_TYPES[:]
    except Exception as e:
        # If there's an error, use the defaults
        print(f"Error loading channels and interaction types: {e}")

    return channel_interaction_types, channel_weights


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
        fallback_values=FALLBACK_INTERACTION_TYPES,
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
            "identificationmethod": weighted_sample(
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
            "datasource": weighted_sample(
                ["CRM", "Marketing Automation", "Web Analytics", "Social Media", "Survey"],
                [0.3, 0.2, 0.2, 0.2, 0.1],
                data.n,
            ),
            "interacted Person ID": person_interacted,
            "interacted Company ID": company_interacted,
            "marketing_activity_id": activity,
            "date": data.interaction_dates,
            "duration": data.durations,
            "followfrominteraction": followfrom_interactions,
        }
    )


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a high-performance DataFrame of interaction data using vectorised logic.

    :param n: Number of rows to generate
    :param kwargs: Supports `prior`, `registry`, `keep_channel`
    :raises ValueError: If required activity or relationship data is missing
    :returns: Polars DataFrame with interaction data
    """
    prior = kwargs.get("prior", {})
    registry = kwargs.get("registry")

    # --- 1. Gather activities from Push and Pull sources ---
    marketing_activity_df = prior.get("Marketing Activity")
    if marketing_activity_df is None or not {
        "marketing_activity_id",
        "targeted_person_id",
        "targeted_company_id",
    }.issubset(marketing_activity_df.columns):
        raise ValueError("No activity data with valid person/company references found.")

    person_ids = extract_id_column(prior.get("Person"), "person_id")
    fallback_series = pl.Series(
        "random_person_id",
        weighted_sample(person_ids, n=marketing_activity_df.height),
    )
    activities_df = marketing_activity_df.with_columns(fallback_series).select(
        [
            pl.col("marketing_activity_id").alias("marketing_activity_id"),
            pl.when(pl.col("targeted_person_id").is_not_null())
            .then(pl.col("targeted_person_id"))
            .otherwise(pl.col("random_person_id"))
            .alias("interacted_person_id"),
            pl.col("targeted_company_id").alias("interacted_company_id"),
        ]
    )

    # --- 2. Prioritise Person Company Role for company derivation if available ---
    role_df = prior.get("Person Company Role")
    if role_df is not None and {"Person ID", "Company ID"}.issubset(role_df.columns):
        # Build a deterministic person -> company map and prefer it over targeted_company_id
        person_company_map = (
            role_df.select(
                [
                    pl.col("Person ID").alias("interacted_person_id"),
                    pl.col("Company ID").alias("_role_company_id"),
                ]
            )
            .unique()
            .group_by("interacted_person_id")
            .agg(pl.first("_role_company_id").alias("_role_company_id"))
        )

        activities_df = (
            activities_df.join(person_company_map, on="interacted_person_id", how="left")
            .with_columns(
                pl.coalesce([pl.col("_role_company_id"), pl.col("interacted_company_id")]).alias(
                    "interacted_company_id"
                )
            )
            .drop("_role_company_id")
        )

    # --- 3. Sample activities for interaction base ---
    interaction_ids = make_ids(n, "INT")
    sampled_df = activities_df.sample(n=n, with_replacement=True).with_columns(
        [
            pl.Series("interaction_id", interaction_ids),
            pl.Series("date", [random_date() for _ in range(n)]),
            pl.Series("duration", [fake.random_int(1, 120) for _ in range(n)]),
        ]
    )

    # --- 4. Assign followfrominteraction with memory-efficient tracking ---
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
        pl.Series("followfrominteraction", followfrom),
    )

    # --- 5. Add remaining columns (channel, type, metadata) ---
    channel_map, channel_weights = get_channel_data_from_registry(registry)
    channels = generate_channels(n, channel_weights)
    # Normalise channel synonyms to canonical names expected by design/defaults
    _channel_canonical = {"Online Chat": "Chat"}
    channels = [_channel_canonical.get(ch, ch) for ch in channels]
    interaction_types = generate_interaction_types(channels, channel_map)

    sampled_df = sampled_df.with_columns(
        [
            pl.Series("channel", channels),
            pl.Series("interaction_type", interaction_types),
            pl.Series(
                "identificationmethod",
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
                "datasource",
                weighted_sample(
                    ["CRM", "Marketing Automation", "Web Analytics", "Social Media", "Survey"],
                    [0.3, 0.2, 0.2, 0.2, 0.1],
                    n=n,
                ),
            ),
        ]
    )

    # For IP-based identification, person may be unknown while company is known.
    # Force interacted_person_id to None in those cases to enable company-only linkage downstream.
    sampled_df = sampled_df.with_columns(
        [
            # mark whether this interaction is referenced by any follow-up
            pl.col("interaction_id")
            .is_in(sampled_df.select("followfrominteraction").drop_nulls().unique().to_series())
            .alias("_is_referenced"),
        ]
    )

    sampled_df = sampled_df.with_columns(
        pl.when(
            (pl.col("identificationmethod") == "IP Company Match")
            & pl.col("followfrominteraction").is_null()
            & (~pl.col("_is_referenced"))
            & pl.col("interacted_company_id").is_null()
        )
        .then(pl.lit(None))
        .otherwise(pl.col("interacted_person_id"))
        .alias("interacted_person_id")
    ).drop("_is_referenced")

    # Ensure interacted_company_id is populated for IP Company Match rows
    # If role/targeted company did not supply a company, fill from the Company table.
    try:
        company_ids_list = extract_id_column(prior.get("Company"), "company_id")
    except Exception:
        company_ids_list = []

    if company_ids_list:
        # Choose a single fallback company to keep None-person company mapping consistent across rows
        fallback_company = fake.random.choice(company_ids_list)
        sampled_df = sampled_df.with_columns(pl.lit(fallback_company).alias("_ip_fill_company"))
        sampled_df = sampled_df.with_columns(
            pl.when(
                (pl.col("identificationmethod") == "IP Company Match")
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
            pl.col("duration").cast(pl.Int64, strict=False),
        ]
    )

    # When called by the orchestrator (registry provided), align column names to spreadsheet
    if registry is not None:
        sampled_df = sampled_df.rename(
            {
                "date": "interactiondate",
                "identificationmethod": "identificationmethodtype",
                "duration": "interactiondur",
                "followfrominteraction": "followfrominteractionid",
                "datasource": "datasourcename",
            }
        ).with_columns(pl.col("interactiondur").cast(pl.Int64, strict=False))

    # Optionally drop channel column to maintain prior behaviour
    if kwargs.get("keep_channel", False):
        return sampled_df
    return sampled_df.drop("channel")
