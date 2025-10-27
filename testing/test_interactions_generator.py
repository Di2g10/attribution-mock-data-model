"""Tests for the interactions generator module."""

import unittest
from pathlib import Path
from typing import Dict

import polars as pl

from src.generators.interactions import (
    generate as generate_interactions,
    DEFAULT_CHANNEL_INTERACTION_TYPES,
)
from src.config_loader import Config
from src.schema_registry import SchemaRegistry

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 20
SMALL_SAMPLE_SIZE = 10
TINY_SAMPLE_SIZE = 5


def minimal_prior_with_activities() -> Dict[str, pl.DataFrame]:
    """Create minimal valid prior data for interactions with person/company and activity links."""
    company_df = pl.DataFrame(
        {
            "company_id": ["CO0000001", "CO0000002"],
            "company_name": ["Company A", "Company B"],
        }
    )

    person_df = pl.DataFrame(
        {
            "person_id": ["PER0000001", "PER0000002"],
            "first_name": ["John", "Jane"],
            "company_id": ["CO0000001", "CO0000002"],
        }
    )

    activity_df = pl.DataFrame(
        {
            "marketing_activity_id": ["ACT0000001", "ACT0000002"],
            "targeted_person_id": ["PER0000001", "PER0000002"],
            "targeted_company_id": ["CO0000001", "CO0000002"],
        }
    )

    return {
        "Company": company_df,
        "Person": person_df,
        "Marketing Activity": activity_df,  # Can also add "Pull Activity" if needed
    }


def test_interactions_unique_ids() -> None:
    """Test that generated interaction IDs are unique."""
    df = generate_interactions(LARGE_SAMPLE_SIZE, prior=minimal_prior_with_activities())
    ids = df.select("interaction_id").to_series()
    assert ids.is_unique().all(), "interaction_id values should be unique"
    assert df.height == LARGE_SAMPLE_SIZE


def test_interactions_with_related_objects() -> None:
    """Test that interactions correctly relate to persons, companies, and activities."""
    # Arrange: load mock prior data with companies, persons, and push activities
    prior = minimal_prior_with_activities()
    df = generate_interactions(LARGE_SAMPLE_SIZE, prior=prior, keep_channel=True)

    assert df.height == LARGE_SAMPLE_SIZE
    assert "interaction_id" in df.columns

    # --- Test 1: Company IDs are valid ---
    company_ids = set(prior["Company"]["company_id"].to_list())
    company_interacted = set(df["interacted_company_id"].drop_nulls().to_list())
    assert company_interacted.issubset(
        company_ids
    ), f"Unexpected company IDs: {company_interacted - company_ids}"

    # --- Test 2: Person IDs are valid ---
    person_ids = set(prior["Person"]["person_id"].to_list())
    person_interacted = set(df["interacted_person_id"].drop_nulls().to_list())
    assert person_interacted.issubset(
        person_ids
    ), f"Unexpected person IDs: {person_interacted - person_ids}"

    # --- Test 3: Activity IDs are valid ---
    activity_ids = set(prior["Marketing Activity"]["marketing_activity_id"].to_list())
    activities = set(df["marketing_activity_id"].drop_nulls().to_list())
    assert activities.issubset(
        activity_ids
    ), f"Unexpected activity IDs: {activities - activity_ids}"

    # --- Test 4: Follow-up interactions share the same person as their reference ---
    follow_ups = df.filter(pl.col("follow_from_interaction_id").is_not_null())
    if follow_ups.height > 0:
        lookup = df.select(["interaction_id", "interacted_person_id"]).to_dict(as_series=False)
        id_to_person = dict(zip(lookup["interaction_id"], lookup["interacted_person_id"]))

        for row in follow_ups.iter_rows(named=True):
            follow_from_id = row["follow_from_interaction_id"]
            person_id = row["interacted_person_id"]
            assert person_id == id_to_person.get(
                follow_from_id
            ), f"Follow-up person mismatch: {row['interaction_id']} vs {follow_from_id}"

    # --- Test 5: Each person always maps to the same company (if company exists) ---
    person_to_company: dict[str, str] = {}
    for row in df.iter_rows(named=True):
        person_id = row["interacted_person_id"]
        company_id = row["interacted_company_id"]

        if company_id is not None:
            if person_id in person_to_company:
                assert (
                    person_to_company[person_id] == company_id
                ), f"Person {person_id} has inconsistent company mappings."
            else:
                person_to_company[person_id] = company_id

    # --- Test 6: Interactions match the person/company on the related activity ---
    activity_df = prior["Marketing Activity"].select(
        [
            pl.col("marketing_activity_id").alias("marketing_activity_id"),
            pl.col("targeted_person_id").alias("expected_person_id"),
            pl.col("targeted_company_id").alias("expected_company_id"),
        ]
    )
    merged = df.join(activity_df, on="marketing_activity_id", how="inner")

    mismatched = merged.filter(
        (pl.col("interacted_person_id") != pl.col("expected_person_id"))
        | (pl.col("interacted_company_id") != pl.col("expected_company_id"))
    )
    assert mismatched.is_empty(), (
        f"Some interactions do not match their activity's person/company:\n"
        f"{mismatched.select(['interaction_id', 'marketing_activity_id', 'interacted_person_id', 'expected_person_id', 'interacted_company_id', 'expected_company_id'])}"
    )


class TestInteractionsWithDesignFile(unittest.TestCase):
    """Validate interactions against the design file (channels/types) and activity linkages."""

    def setUp(self) -> None:
        """Load the spreadsheet-backed registry and build the channel→type map."""
        # Get the absolute path to the project root directory
        project_root = Path(__file__).parent.parent.absolute()
        self.structure_file_path = (
            project_root / "data" / "input" / "Low Level Field Detail Design.xlsx"
        )

        # Locate a suitable spreadsheet file if the default path is missing
        if not self.structure_file_path.exists():
            print(f"Warning: File not found: {self.structure_file_path}")
            print("Checking for alternative files...")
            input_dir = project_root / "data" / "input"
            if input_dir.exists():
                excel_files = list(input_dir.glob("Low Level Field Detail Design*.xlsx"))
                if excel_files:
                    excel_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    self.structure_file_path = excel_files[0]
                    print(f"Using alternative file: {self.structure_file_path}")
                else:
                    self.fail("No suitable Excel files found in the input directory.")
            else:
                self.fail(f"Input directory not found: {input_dir}")

        # Registry derived from the design file
        self.config = Config(self.structure_file_path)
        self.registry = SchemaRegistry(self.config)

        # Spreadsheet-provided channel/type tables
        self.channels_df = self.config.channels
        self.interaction_types_df = self.config.interaction_types

        # Build a mapping: channel -> valid interaction types
        self.channel_to_interaction_types: dict[str, list[str]] = {}

        # First pull types from the spreadsheet
        if not self.interaction_types_df.is_empty():
            for row in self.interaction_types_df.iter_rows(named=True):
                channel = row.get("Channel", "")
                if channel:
                    interaction_types = [
                        value for key, value in row.items() if key != "Channel" and value
                    ]
                    if interaction_types:
                        self.channel_to_interaction_types[channel] = interaction_types

        # Then add any defaults not present in the spreadsheet
        for channel, interaction_types in DEFAULT_CHANNEL_INTERACTION_TYPES.items():
            if channel not in self.channel_to_interaction_types:
                self.channel_to_interaction_types[channel] = interaction_types

        # Minimal valid `prior` so the generator can link Interaction -> Activity -> Person/Company
        # We reuse the shared helper defined earlier in this module.
        self.prior = (
            minimal_prior_with_activities()
        )  # provides Push Activity with person/company targets

    def test_interactions_with_design_file(self) -> None:
        """Test Generated Interactions with Design File for channel and type.

        Ensure generated interactions have:
        - a 'channel' present in the spreadsheet/defaults
        - a 'type' valid for that channel according to the spreadsheet/defaults
        """
        if not self.channel_to_interaction_types:
            self.skipTest("No channels or interaction types found in the design file")

        # Generate interactions using the registry; include channel for validation.
        # We pass `prior` to satisfy the generator's requirement for activity linkage.
        df = generate_interactions(
            LARGE_SAMPLE_SIZE,
            registry=self.registry,
            prior=self.prior,
            keep_channel=True,
        )

        # Basic shape/columns
        self.assertIn("channel", df.columns, "Generated interactions should have a 'channel' field")
        self.assertIn(
            "interaction_type",
            df.columns,
            "Generated interactions should have an 'interaction_type' field",
        )

        # Channels must be known
        for channel in df["channel"].to_list():
            self.assertIn(
                channel,
                self.channel_to_interaction_types.keys(),
                f"Channel '{channel}' not found in the design file/defaults.",
            )

        # Types must be valid for the channel
        for row in df.iter_rows(named=True):
            channel = row["channel"]
            interaction_type = row["interaction_type"]
            valid_types = self.channel_to_interaction_types.get(channel, [])
            self.assertIn(
                interaction_type,
                valid_types,
                f"Interaction type '{interaction_type}' is not valid for channel '{channel}'. "
                f"Valid types are: {valid_types}",
            )

    def test_interaction_activity_alignment(self) -> None:
        """Test interaction alignment of Person and company ID.

        Ensure each interaction aligns with its activity targets:
        interacted_person_id == activity.targeted_person_id
        interacted_company_id == activity.targeted_company_id
        """
        df = generate_interactions(
            LARGE_SAMPLE_SIZE,
            registry=self.registry,
            prior=self.prior,
            keep_channel=True,
        )

        # Prepare expected targets from the Push Activity prior
        activity_df = self.prior["Marketing Activity"].select(
            [
                pl.col("marketing_activity_id").alias("marketing_activity_id"),
                pl.col("targeted_person_id").alias("expected_person_id"),
                pl.col("targeted_company_id").alias("expected_company_id"),
            ]
        )

        # Join to compare actual vs expected
        merged = df.join(activity_df, on="marketing_activity_id", how="inner")

        mismatched = merged.filter(
            (pl.col("interacted_person_id") != pl.col("expected_person_id"))
            | (pl.col("interacted_company_id") != pl.col("expected_company_id"))
        )

        # If any mismatches, surface a concise diff to aid debugging
        self.assertTrue(
            mismatched.is_empty(),
            msg=str(
                mismatched.select(
                    [
                        "interaction_id",
                        "marketing_activity_id",
                        "interacted_person_id",
                        "expected_person_id",
                        "interacted_company_id",
                        "expected_company_id",
                    ]
                )
            ),
        )
