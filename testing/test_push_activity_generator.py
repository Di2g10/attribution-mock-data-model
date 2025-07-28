"""Unit tests for the Push Activity generator."""

from __future__ import annotations

import unittest
from typing import Dict, Set

import polars as pl

from src.generators.push_activity import generate as generate_push_activity
from src.generators.marketing_assets import generate as generate_marketing_assets
from src.generators.products import generate as generate_products
from src.generators.company import generate as generate_company
from src.generators.person import generate as generate_person

LARGE_SAMPLE_SIZE: int = 20


class TestPushActivityGenerator(unittest.TestCase):
    """Tests for the Push Activity generator using the unittest framework."""

    def setUp(self) -> None:
        """Create a minimal valid `prior` for Push Activity generation.

        Push Activity requires:
        - Marketing Assets (which itself requires Products)
        - Campaigns (expects a `campaign_id` column)
        - Audience (expects an `audience_id` column)
        - Company / Person to allow targeted IDs

        We generate Products, then Marketing Assets with Products in prior.
        Campaigns and Audience are provided as tiny in-memory DataFrames.
        Company and Person are generated via their generators.
        """
        # Base objects
        self.products_df = generate_products(LARGE_SAMPLE_SIZE)
        self.company_df = generate_company(LARGE_SAMPLE_SIZE)
        self.person_df = generate_person(LARGE_SAMPLE_SIZE)

        # Marketing Assets requires Products
        self.marketing_assets_df = generate_marketing_assets(
            LARGE_SAMPLE_SIZE,
            prior={"Products": self.products_df},
        )

        # Minimal Campaigns / Audience tables with the ID columns expected by the generator
        self.campaigns_df = pl.DataFrame(
            {
                "campaign_id": [f"CAM{str(i).zfill(7)}" for i in range(1, LARGE_SAMPLE_SIZE + 1)],
                "name": [f"Campaign {i}" for i in range(1, LARGE_SAMPLE_SIZE + 1)],
            }
        )
        self.audience_df = pl.DataFrame(
            {
                "audience_id": [f"AUD{str(i).zfill(7)}" for i in range(1, LARGE_SAMPLE_SIZE + 1)],
                "name": [f"Audience {i}" for i in range(1, LARGE_SAMPLE_SIZE + 1)],
            }
        )

        # Prior dictionary — include both Title Case and lowercase aliases
        # to be robust to any legacy lookups inside generators.
        self.prior: Dict[str, pl.DataFrame] = {
            "Products": self.products_df,
            "Marketing Assets": self.marketing_assets_df,
            "Campaigns": self.campaigns_df,
            "Audience": self.audience_df,
            "Company": self.company_df,
            "Person": self.person_df,
            # aliases
            "products": self.products_df,
            "marketing assets": self.marketing_assets_df,
            "campaigns": self.campaigns_df,
            "audience": self.audience_df,
            "company": self.company_df,
            "person": self.person_df,
        }

        # Cached ID sets for assertions
        self.valid_ma_ids: Set[str] = set(self.marketing_assets_df["marketing_asset_id"].to_list())
        self.valid_campaign_ids: Set[str] = set(self.campaigns_df["campaign_id"].to_list())
        self.valid_audience_ids: Set[str] = set(self.audience_df["audience_id"].to_list())
        self.valid_company_ids: Set[str] = set(self.company_df["company_id"].to_list())
        self.valid_person_ids: Set[str] = set(self.person_df["person_id"].to_list())

    # --------------------------------------------------------------------- #
    # Tests
    # --------------------------------------------------------------------- #

    def test_push_activity_unique_ids(self) -> None:
        """Generated Push Activity IDs must be unique and match the requested size."""
        df = generate_push_activity(LARGE_SAMPLE_SIZE, prior=self.prior)

        self.assertIn("id", df.columns, "Expected 'id' column in Push Activity output.")
        ids = df.select("id").to_series()
        self.assertTrue(ids.is_unique().all(), "Push Activity 'id' values should be unique.")
        self.assertEqual(df.height, LARGE_SAMPLE_SIZE, "Row count should match the requested size.")

    def test_push_activity_links_and_targets(self) -> None:
        """Validate links to Marketing Assets and the mutual exclusivity of targets.

        - `marketing_asset_id` must exist in Marketing Assets.
        - Exactly one of `targeted_person_id` or `targeted_company_id` should be populated.
        - Any populated target must reference a valid Person/Company ID.
        """
        df = generate_push_activity(LARGE_SAMPLE_SIZE, prior=self.prior)

        # Marketing Asset linkage
        self.assertIn(
            "marketing_asset_id",
            df.columns,
            f"Expected 'marketing_asset_id' column; got: {df.columns}",
        )
        used_ma = set(df["marketing_asset_id"].drop_nulls().to_list())
        unknown_ma = used_ma - self.valid_ma_ids
        self.assertFalse(
            unknown_ma,
            f"Unknown marketing_asset_id values referenced: {sorted(unknown_ma)}",
        )

        # Target columns presence
        for col in ("targeted_person_id", "targeted_company_id"):
            self.assertIn(col, df.columns, f"Expected '{col}' in Push Activity output.")

        # Mutual exclusivity & validity
        both_populated = df.filter(
            pl.col("targeted_person_id").is_not_null() & pl.col("targeted_company_id").is_not_null()
        )
        self.assertEqual(
            both_populated.height, 0, "Person and Company targets should not both be populated."
        )

        # Person targets valid
        person_used = set(df["targeted_person_id"].drop_nulls().to_list())
        invalid_persons = person_used - self.valid_person_ids
        self.assertFalse(
            invalid_persons, f"Unknown targeted_person_id values: {sorted(invalid_persons)}"
        )

        # Company targets valid
        company_used = set(df["targeted_company_id"].drop_nulls().to_list())
        invalid_companies = company_used - self.valid_company_ids
        self.assertFalse(
            invalid_companies, f"Unknown targeted_company_id values: {sorted(invalid_companies)}"
        )


if __name__ == "__main__":
    unittest.main()
