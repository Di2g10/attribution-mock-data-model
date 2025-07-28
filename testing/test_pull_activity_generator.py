"""Unit tests for the Pull Activity generator."""

from __future__ import annotations

import unittest
from typing import Dict

import polars as pl

from src.generators.pull_activity import generate as generate_pull_activity
from src.generators.marketing_assets import generate as generate_marketing_assets

# Sample sizes used across tests
LARGE_SAMPLE_SIZE: int = 20


class TestPullActivityGenerator(unittest.TestCase):
    """Tests for the Pull Activity generator using the unittest framework."""

    def setUp(self) -> None:
        """Create a minimal valid `prior` for Pull Activity generation.

        Pull Activity requires Marketing Assets, and Marketing Assets requires Products.
        We therefore create Products first and pass them to the marketing assets generator.
        """
        self.products_df = pl.DataFrame(
            {
                "product_id": [f"PROD{str(i).zfill(7)}" for i in range(1, LARGE_SAMPLE_SIZE + 1)],
                "name": [f"Product {i}" for i in range(1, LARGE_SAMPLE_SIZE + 1)],
            }
        )

        self.marketing_assets_df = generate_marketing_assets(
            LARGE_SAMPLE_SIZE,
            prior={"Products": self.products_df},
        )

        # Only the title-cased keys are required by the generator.
        self.prior: Dict[str, pl.DataFrame] = {
            "Products": self.products_df,
            "Marketing Assets": self.marketing_assets_df,
        }

    def test_pull_activity_unique_ids(self) -> None:
        """Ensure generated Pull Activity IDs are unique and the row count matches.

        :raises AssertionError: If IDs are not unique or row count mismatches.
        """
        df = generate_pull_activity(LARGE_SAMPLE_SIZE, prior=self.prior)

        self.assertIn("id", df.columns, "Expected 'id' column in Pull Activity output.")
        ids = df.select("id").to_series()
        self.assertTrue(ids.is_unique().all(), "Pull Activity 'id' values should be unique.")
        self.assertEqual(df.height, LARGE_SAMPLE_SIZE, "Row count should match the requested size.")

    def test_pull_activity_marketing_asset_links(self) -> None:
        """Verify that all `marketing_asset_id` values exist in the Marketing Assets table.

        :raises AssertionError: If the output lacks the column or references unknown IDs.
        """
        df = generate_pull_activity(LARGE_SAMPLE_SIZE, prior=self.prior)

        self.assertIn(
            "marketing_asset_id",
            df.columns,
            f"Expected 'marketing_asset_id' column; got: {df.columns}",
        )

        valid_ma_ids = set(self.marketing_assets_df["marketing_asset_id"].to_list())
        used_ma_ids = set(df["marketing_asset_id"].drop_nulls().to_list())

        unknown = used_ma_ids - valid_ma_ids
        self.assertFalse(
            unknown,
            f"Pull Activity references unknown marketing assets: {sorted(unknown)}",
        )


if __name__ == "__main__":
    unittest.main()
