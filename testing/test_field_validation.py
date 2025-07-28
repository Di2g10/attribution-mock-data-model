"""Tests to validate that generator fields match the spreadsheet."""

import unittest
from pathlib import Path
from typing import List

import pandas as pd

from src.config_loader import Config
from src.schema_registry import SchemaRegistry
from src.orchestrator import build


def normalize_field_name(name: str) -> str:
    """Normalize a field name by converting to lowercase and removing spaces and underscores.

    This ensures that field names like 'causal_interaction' and 'causalinteractionid'
    are treated as equivalent.
    """
    return name.lower().replace(" ", "").replace("_", "")


def get_expected_fields_from_spreadsheet(excel_file_path: Path) -> dict[str, set[str]]:
    """Extract field names for each object from the spreadsheet.

    Args:
        excel_file_path: Path to the Excel file

    Returns:
        Dictionary mapping object names to sets of field names

    """
    # Load the Attributes sheet
    attributes_df = pd.read_excel(excel_file_path, "Attributes")

    # Group by object name (in the 'Object' column) and collect field names
    expected_fields = {}
    for obj_name, group in attributes_df.groupby("Object"):
        # Skip non-object entries
        if pd.isna(obj_name) or obj_name == "":
            continue

        # Normalize object name to match generator names
        normalized_name = obj_name.strip()

        # Extract field names and normalize them
        # Filter out field names that contain question marks (likely placeholders)
        field_names = set(
            normalize_field_name(str(x)) for x in group["Name"].dropna() if "?" not in str(x)
        )
        expected_fields[normalized_name] = field_names

    return expected_fields


class TestFieldValidation(unittest.TestCase):
    """Test that generator fields match the spreadsheet."""

    def setUp(self) -> None:
        """Set up the test."""
        # Use os.path.join for more robust path handling

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

        self.config = Config(self.structure_file_path)
        self.registry = SchemaRegistry(self.config)

        # Get expected fields from spreadsheet
        self.expected_fields = get_expected_fields_from_spreadsheet(self.structure_file_path)

    def test_generator_fields_match_spreadsheet(self) -> None:
        """Test that generator fields match the spreadsheet."""
        # Generate data for all objects
        generated_data = build(self.structure_file_path, overwrite=True)

        # Track errors for all objects
        error_messages: List[str] = []

        # Check each object
        for obj_name, df in generated_data.items():
            # Skip if object is not in expected fields
            if obj_name not in self.expected_fields:
                print(f"Warning: Object '{obj_name}' not found in spreadsheet")
                continue

            # Get actual fields from generated DataFrame and normalize them
            actual_fields = set(normalize_field_name(col) for col in df.columns)

            # Get expected fields from spreadsheet
            expected_fields = self.expected_fields[obj_name]

            # Check for missing fields
            missing_fields = expected_fields - actual_fields
            if missing_fields:
                error_messages.append(f"Object '{obj_name}' is missing fields: {missing_fields}")

            # Check for extra fields
            extra_fields = actual_fields - expected_fields
            if extra_fields:
                error_messages.append(f"Object '{obj_name}' has extra fields: {extra_fields}")

            if error_messages:
                all_errors = "\n".join(error_messages)
                self.fail(f"Field validation failed:\n{all_errors}")

            # If we get here, all fields match
            print(f"Object '{obj_name}' fields match spreadsheet")


if __name__ == "__main__":
    unittest.main()
