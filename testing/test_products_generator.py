"""Tests for the products generator module."""

import unittest
from pathlib import Path

import polars as pl

from src.generators.products import generate, ProductField
from src.config_loader import Config
from src.schema_registry import SchemaRegistry

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 100
SMALL_SAMPLE_SIZE = 30
TINY_SAMPLE_SIZE = 10


def test_products_unique_ids() -> None:
    """Test that generated product IDs are unique."""
    df = generate(LARGE_SAMPLE_SIZE)
    ids = df.select(ProductField.product_id).to_series()
    assert ids.is_unique().all(), "product_id values should be unique"
    assert df.height == LARGE_SAMPLE_SIZE


def test_products_hierarchy() -> None:
    """Test that the product hierarchy is correctly structured."""
    df = generate(LARGE_SAMPLE_SIZE)

    # Check that we have products at all three tiers
    tier1_count = df.filter(pl.col(ProductField.level) == "Tier 1").height
    tier2_count = df.filter(pl.col(ProductField.level) == "Tier 2").height
    tier3_count = df.filter(pl.col(ProductField.level) == "Tier 3").height

    assert tier1_count > 0, "Should have at least one Tier 1 product"
    assert tier2_count > 0, "Should have at least one Tier 2 product"
    assert tier3_count > 0, "Should have at least one Tier 3 product"

    # Check that Tier 1 products have no parent (empty string)
    tier1_products = df.filter(pl.col(ProductField.level) == "Tier 1")
    assert (
        tier1_products[ProductField.product_parent_id] == ""
    ).all(), "Tier 1 products should have empty string as parent"

    # Check that Tier 2 products have a Tier 1 parent
    tier2_products = df.filter(pl.col(ProductField.level) == "Tier 2")
    tier2_parent_ids = tier2_products[ProductField.product_parent_id].to_list()
    tier1_ids = tier1_products[ProductField.product_id].to_list()

    for parent_id in tier2_parent_ids:
        assert (
            parent_id in tier1_ids
        ), f"Tier 2 product has parent {parent_id} which is not a Tier 1 product"

    # Check that Tier 3 products have a Tier 2 parent
    tier3_products = df.filter(pl.col(ProductField.level) == "Tier 3")
    tier3_parent_ids = tier3_products[ProductField.product_parent_id].to_list()
    tier2_ids = tier2_products[ProductField.product_id].to_list()

    for parent_id in tier3_parent_ids:
        assert (
            parent_id in tier2_ids
        ), f"Tier 3 product has parent {parent_id} which is not a Tier 2 product"


class TestProductsWithDesignFile(unittest.TestCase):
    """Test that products are generated with appropriate values from the design file."""

    def setUp(self) -> None:
        """Set up the test by loading the design file."""
        # Get the absolute path to the project root directory
        project_root = Path(__file__).parent.parent.absolute()
        self.structure_file_path = (
            project_root / "data" / "input" / "Low Level Field Detail Design.xlsx"
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

    def test_products_with_design_file(self) -> None:
        """Test that products are generated with appropriate values from the design file."""
        # Generate a sample of products
        df = generate(SMALL_SAMPLE_SIZE)

        # Verify that the generated products have the expected fields
        expected_fields = [f.value for f in ProductField]

        for field in expected_fields:
            self.assertIn(field, df.columns, f"Generated products should have a '{field}' field")

        # Verify that the level field has the expected values
        levels = df[ProductField.level].unique().to_list()
        expected_levels = ["Tier 1", "Tier 2", "Tier 3"]
        for level in expected_levels:
            self.assertIn(
                level, levels, f"Level '{level}' should be present in the generated products"
            )

        # Verify that product names are appropriate for BT
        # Check that all names are non-empty strings
        names = df["name"].to_list()
        for name in names:
            self.assertTrue(
                isinstance(name, str) and len(name) > 0, "Product names should be non-empty strings"
            )

        # Check that Tier 3 products have "BT" in their name
        tier3_products = df.filter(pl.col(ProductField.level) == "Tier 3")
        tier3_names = tier3_products["name"].to_list()
        for name in tier3_names:
            self.assertTrue(
                "BT" in name or name.startswith("BT"),
                f"Tier 3 product name '{name}' should include 'BT'",
            )

        # If we get here, all products have valid fields and values
        print(f"All {df.height} products have valid fields and values")


if __name__ == "__main__":
    unittest.main()
