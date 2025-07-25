"""Tests for the interactions generator module."""

import unittest
from pathlib import Path
import json

import polars as pl

from src.generators.interactions import (
    generate,
    DEFAULT_CHANNEL_INTERACTION_TYPES,
    DEFAULT_CHANNEL_WEIGHTS,
)
from src.config_loader import Config
from src.schema_registry import SchemaRegistry

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 20
SMALL_SAMPLE_SIZE = 10
TINY_SAMPLE_SIZE = 5


def test_interactions_unique_ids() -> None:
    """Test that generated interaction IDs are unique."""
    df = generate(LARGE_SAMPLE_SIZE)
    ids = df.select("interactionid").to_series()
    assert ids.is_unique().all(), "interactionid values should be unique"
    assert df.height == LARGE_SAMPLE_SIZE


def test_interactions_with_related_objects() -> None:
    """Test interaction generation with related objects."""
    # Create mock DataFrames for related objects

    company_df = pl.DataFrame(
        {
            "company_id": ["CO0000001", "CO0000002", "CO0000003"],
            "company_name": ["Company A", "Company B", "Company C"],
        }
    )

    person_df = pl.DataFrame(
        {
            "person_id": ["PER0000001", "PER0000002", "PER0000003", "PER0000004"],
            "first_name": ["John", "Jane", "Bob", "Alice"],
        }
    )

    pull_activity_df = pl.DataFrame(
        {
            "id": ["PULL0000001", "PULL0000002", "PULL0000003"],
            "name": ["Pull Activity 1", "Pull Activity 2", "Pull Activity 3"],
        }
    )

    push_activity_df = pl.DataFrame(
        {
            "id": ["PUSH0000001", "PUSH0000002", "PUSH0000003"],
            "name": ["Push Activity 1", "Push Activity 2", "Push Activity 3"],
        }
    )

    # Generate a larger sample to ensure we have follow-up interactions
    df = generate(
        LARGE_SAMPLE_SIZE,
        prior={
            "Company": company_df,
            "Person": person_df,
            "Pull Activity": pull_activity_df,
            "Push Activity": push_activity_df,
        },
        keep_channel=True,  # Keep channel for testing
    )

    # Verify that the generation works with related data
    assert df.height == LARGE_SAMPLE_SIZE
    assert "interactionid" in df.columns

    # Verify that companyinteracted contains IDs from company_df or None
    company_ids = set(company_df["company_id"].to_list())
    company_interacted = set(df["companyinteracted"].drop_nulls().to_list())
    assert company_interacted.issubset(
        company_ids
    ), f"Company IDs {company_interacted - company_ids} not in {company_ids}"

    # Verify that personinteracted contains IDs from person_df
    person_ids = set(person_df["person_id"].to_list())
    person_interacted = set(df["personinteracted"].to_list())
    assert person_interacted.issubset(
        person_ids
    ), f"Person IDs {person_interacted - person_ids} not in {person_ids}"

    # Verify that activity contains IDs from pull_activity_df or push_activity_df
    activity_ids = set(pull_activity_df["id"].to_list() + push_activity_df["id"].to_list())
    activities = set(df["activity"].to_list())
    assert activities.issubset(
        activity_ids
    ), f"Activity IDs {activities - activity_ids} not in {activity_ids}"

    # Verify that follow-up interactions use the same person
    follow_ups = df.filter(pl.col("followfrominteraction").is_not_null())
    if follow_ups.height > 0:
        for row in follow_ups.iter_rows(named=True):
            follow_from_id = row["followfrominteraction"]
            person_id = row["personinteracted"]

            # Find the original interaction
            original = df.filter(pl.col("interactionid") == follow_from_id)
            if original.height > 0:
                original_person_id = original.select("personinteracted").item()
                assert (
                    person_id == original_person_id
                ), f"Follow-up interaction {row['interactionid']} has person {person_id} but original interaction {follow_from_id} has person {original_person_id}"

    # Verify that the same person always has the same company (if not None)
    person_companies: dict[str, str] = {}
    for row in df.iter_rows(named=True):
        person_id = row["personinteracted"]
        company_id = row["companyinteracted"]

        if company_id is not None:
            if person_id in person_companies:
                assert (
                    person_companies[person_id] == company_id
                ), f"Person {person_id} has different companies: {person_companies[person_id]} and {company_id}"
            else:
                person_companies[person_id] = company_id


class TestInteractionsWithDesignFile(unittest.TestCase):
    """Test that interactions are generated with appropriate values from the design file."""

    def setUp(self) -> None:
        """Set up the test by loading the design file."""
        # Get the absolute path to the project root directory
        project_root = Path(__file__).parent.parent.absolute()
        self.structure_file_path = (
            project_root / "data" / "input" / "Low Level Field Detail Design(6).xlsx"
        )

        # Check if the file exists
        if not self.structure_file_path.exists():
            print(f"Warning: File not found: {self.structure_file_path}")
            print("Checking for alternative files...")

            # Look for alternative files in the same directory
            input_dir = project_root / "data" / "input"
            if input_dir.exists():
                excel_files = list(input_dir.glob("Low Level Field Detail Design*.xlsx"))
                if excel_files:
                    # Use the latest version available
                    excel_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    self.structure_file_path = excel_files[0]
                    print(f"Using alternative file: {self.structure_file_path}")
                else:
                    self.fail("No suitable Excel files found in the input directory.")
            else:
                self.fail(f"Input directory not found: {input_dir}")

        # Load the configuration and create a registry
        self.config = Config(self.structure_file_path)
        self.registry = SchemaRegistry(self.config)

        # Extract channels and interaction types from the design file
        self.channels_df = self.config.channels
        self.interaction_types_df = self.config.interaction_types

        # Create a mapping of channels to their valid interaction types
        self.channel_to_interaction_types = {}

        # First, add channels and interaction types from the design file
        if not self.interaction_types_df.is_empty():
            for row in self.interaction_types_df.iter_rows(named=True):
                channel = row.get("Channel", "")
                if channel:
                    # Extract all non-empty values except "Channel" as interaction types
                    interaction_types = [
                        value for key, value in row.items() if key != "Channel" and value
                    ]
                    if interaction_types:
                        self.channel_to_interaction_types[channel] = interaction_types

        # Then, add default channels and interaction types if they're not already in the mapping
        for channel, interaction_types in DEFAULT_CHANNEL_INTERACTION_TYPES.items():
            if channel not in self.channel_to_interaction_types:
                self.channel_to_interaction_types[channel] = interaction_types

    def test_interactions_with_design_file(self) -> None:
        """Test that interactions are generated with appropriate values from the design file."""
        # Skip the test if no channels or interaction types were found
        if not self.channel_to_interaction_types:
            self.skipTest("No channels or interaction types found in the design file")

        # Generate a large sample of interactions using the registry
        # Pass keep_channel=True to ensure the channel field is included for validation
        df = generate(LARGE_SAMPLE_SIZE, registry=self.registry, keep_channel=True)

        # Verify that the generated interactions have the expected fields
        self.assertIn("channel", df.columns, "Generated interactions should have a 'channel' field")
        self.assertIn("type", df.columns, "Generated interactions should have a 'type' field")

        # Verify that each interaction has a valid channel
        channels = df["channel"].to_list()
        for channel in channels:
            self.assertIn(
                channel,
                self.channel_to_interaction_types.keys(),
                f"Channel '{channel}' not found in the design file",
            )

        # Verify that each interaction has a valid interaction type for its channel
        for i, row in enumerate(df.iter_rows(named=True)):
            channel = row["channel"]
            interaction_type = row["type"]
            valid_types = self.channel_to_interaction_types.get(channel, [])

            self.assertIn(
                interaction_type,
                valid_types,
                f"Interaction type '{interaction_type}' is not valid for channel '{channel}'. "
                f"Valid types are: {valid_types}",
            )

        # If we get here, all interactions have valid channels and interaction types
        print(f"All {df.height} interactions have valid channels and interaction types")

    def test_compare_defaults_with_spreadsheet(self) -> None:
        """Compare the default values in the code with the values in the spreadsheet.

        This test extracts the channels and interaction types from the spreadsheet,
        compares them with the default values in the code, and outputs detailed
        information about any mismatches. This information can be used to update
        the default values in the code to match the spreadsheet.
        """
        # Skip the test if no channels or interaction types were found
        if not self.channel_to_interaction_types:
            self.skipTest("No channels or interaction types found in the design file")

        # Get the channels from the spreadsheet
        spreadsheet_channels = set()
        if not self.channels_df.is_empty():
            spreadsheet_channels = set(self.channels_df["Name"].to_list())

        # Get the channels from the default values in the code
        default_channels = set(DEFAULT_CHANNEL_INTERACTION_TYPES.keys())

        # Compare the channels
        missing_channels = spreadsheet_channels - default_channels
        extra_channels = default_channels - spreadsheet_channels

        # Output the results of the channel comparison
        print("\n=== Channel Comparison ===")
        print(f"Channels in spreadsheet: {sorted(spreadsheet_channels)}")
        print(f"Channels in default values: {sorted(default_channels)}")
        print(f"Channels in spreadsheet but not in default values: {sorted(missing_channels)}")
        print(f"Channels in default values but not in spreadsheet: {sorted(extra_channels)}")

        # Get the interaction types for each channel from the spreadsheet
        spreadsheet_channel_interaction_types = {}
        if not self.interaction_types_df.is_empty():
            for row in self.interaction_types_df.iter_rows(named=True):
                channel = row.get("Channel", "")
                if channel:
                    # Extract all non-empty values except "Channel" as interaction types
                    interaction_types = [
                        value for key, value in row.items() if key != "Channel" and value
                    ]
                    if interaction_types:
                        spreadsheet_channel_interaction_types[channel] = interaction_types

        # Compare the interaction types for each channel
        print("\n=== Interaction Type Comparison ===")
        all_channels = sorted(
            set(
                list(spreadsheet_channel_interaction_types.keys())
                + list(DEFAULT_CHANNEL_INTERACTION_TYPES.keys())
            )
        )

        for channel in all_channels:
            spreadsheet_types = set(spreadsheet_channel_interaction_types.get(channel, []))
            default_types = set(DEFAULT_CHANNEL_INTERACTION_TYPES.get(channel, []))

            missing_types = spreadsheet_types - default_types
            extra_types = default_types - spreadsheet_types

            print(f"\nChannel: {channel}")
            print(f"  Interaction types in spreadsheet: {sorted(spreadsheet_types)}")
            print(f"  Interaction types in default values: {sorted(default_types)}")
            print(
                f"  Interaction types in spreadsheet but not in default values: {sorted(missing_types)}"
            )
            print(
                f"  Interaction types in default values but not in spreadsheet: {sorted(extra_types)}"
            )

        # Output the updated default values that can be used in the code
        print("\n=== Updated Default Values ===")
        updated_channel_interaction_types = {}

        # Start with the spreadsheet values
        for channel, types in spreadsheet_channel_interaction_types.items():
            updated_channel_interaction_types[channel] = types

        # Add any channels from the default values that aren't in the spreadsheet
        for channel, types in DEFAULT_CHANNEL_INTERACTION_TYPES.items():
            if channel not in updated_channel_interaction_types:
                updated_channel_interaction_types[channel] = types

        # Output the updated default values in a format that can be copied into the code
        print("DEFAULT_CHANNEL_INTERACTION_TYPES = {")
        for channel, types in sorted(updated_channel_interaction_types.items()):
            types_str = ", ".join([f'"{t}"' for t in types])
            print(f'    "{channel}": [{types_str}],')
        print("}")

        # Output the updated channel weights
        print("\nDEFAULT_CHANNEL_WEIGHTS = {")
        for channel in sorted(updated_channel_interaction_types.keys()):
            weight = DEFAULT_CHANNEL_WEIGHTS.get(
                channel, 1.0 / len(updated_channel_interaction_types)
            )
            print(f'    "{channel}": {weight:.2f},')
        print("}")

        # Write the updated default values to a JSON file for easy reference
        output_file = Path(__file__).parent / "updated_interaction_defaults.json"
        with output_file.open("w") as f:
            json.dump(
                {
                    "DEFAULT_CHANNEL_INTERACTION_TYPES": updated_channel_interaction_types,
                    "DEFAULT_CHANNEL_WEIGHTS": {
                        channel: DEFAULT_CHANNEL_WEIGHTS.get(
                            channel, 1.0 / len(updated_channel_interaction_types)
                        )
                        for channel in updated_channel_interaction_types
                    },
                },
                f,
                indent=4,
            )

        print(f"\nUpdated default values written to {output_file}")
