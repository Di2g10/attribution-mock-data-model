"""Tests for additional linking methods and precedence in attribution linking table.

Covers:
- Direct person linking via order.contact_id has priority over person-company links.
- Company-only (IP inferred) linking for interactions without person does not overwrite stronger links.
"""

from __future__ import annotations

import unittest
import polars as pl

from src.generators.attribution_linking_table import generate as generate_links


class TestAttributionLinkingMethods(unittest.TestCase):
    """Tests for additional linking methods and precedence in attribution linking table."""

    def setUp(self) -> None:
        """Build minimal prior data needed for link generation and enrichment."""
        # Companies hierarchy C2 -> C1 (C1 is parent)
        self.company_df = pl.DataFrame(
            {
                "company_id": ["C1", "C2"],
                "Parent_Company_ID": [None, "C1"],
                "Company Business Type": ["Parent", "Child"],
            }
        )

        # People
        self.person_df = pl.DataFrame({"person_id": ["P1"]})

        # Person company role: P1 at C1
        self.pcr_df = pl.DataFrame(
            {
                "person_id": ["P1"],
                "company_id": ["C1"],
                "roletype": ["Primary"],
                "start_date": [__import__("datetime").datetime(2023, 1, 1)],
                "end_date": [None],
            }
        )

        # Interactions: I1 has person P1 (at C2 company context); I2 has unknown person but company C2
        self.interactions_df = pl.DataFrame(
            {
                "interaction_id": ["I1", "I2"],
                "interacted_person_id": ["P1", None],
                "interacted_company_id": ["C2", "C2"],
                "marketing_activity_id": ["A1", "A2"],
                "date": [
                    __import__("datetime").datetime(2024, 1, 1),
                    __import__("datetime").datetime(2024, 1, 2),
                ],
            }
        )

        # Orders: O1 belongs to company C1 and contact is P1
        self.orders_df = pl.DataFrame(
            {
                "order_id": ["O1"],
                "company_id": ["C1"],
                "contact_id": ["P1"],
                "product_id": ["PR1"],
                "date_raised": [__import__("datetime").datetime(2024, 1, 10)],
            }
        )

        # Minimal product/activity structures (empty or minimal) for enrichment path
        self.products_df = pl.DataFrame(
            {"product_id": ["PR1"], "product_parent_id": [None], "level": ["Tier 1"]}
        )
        self.marketing_activity_df = pl.DataFrame(
            {
                "marketing_activity_id": ["A1", "A2"],
                "campaign_id": [None, None],
                "marketing_asset_id": [None, None],
                "targeted_company_id": [None, None],
            }
        )
        self.campaigns_df = pl.DataFrame({"campaign_id": [], "product_id": []})
        self.assets_df = pl.DataFrame({"marketing_asset_id": [], "product_id": []})

        self.prior = {
            "Company": self.company_df,
            "Person": self.person_df,
            "Person Company Role": self.pcr_df,
            "Interactions": self.interactions_df,
            "Orders": self.orders_df,
            "Products": self.products_df,
            "Marketing Activity": self.marketing_activity_df,
            "Campaigns": self.campaigns_df,
            "Marketing Assets": self.assets_df,
        }

    def test_direct_person_linking_has_priority(self) -> None:
        """Direct person linking via order.contact_id has priority over person-company links."""
        df = generate_links(0, prior=self.prior)
        # Expect only one link for (I1, O1) and that it is the direct person relation
        subset = df.filter((pl.col("interaction_id") == "I1") & (pl.col("outcome_id") == "O1"))
        self.assertEqual(subset.height, 1)
        self.assertEqual(subset.select("relation_type").item(), "Interaction-Person-Order")
        self.assertEqual(subset.select("person_id").item(), "P1")
        self.assertEqual(subset.select("company_id").item(), "C1")  # from Order
        # time_lag should be non-negative
        self.assertGreaterEqual(subset.select("time_lag").item(), 0)

    def test_company_only_linking_when_person_unknown(self) -> None:
        """Company-only (IP inferred) linking for interactions without person does not overwrite stronger links."""
        df = generate_links(0, prior=self.prior)
        subset = df.filter((pl.col("interaction_id") == "I2") & (pl.col("outcome_id") == "O1"))
        self.assertEqual(subset.height, 1)
        self.assertEqual(subset.select("relation_type").item(), "Interaction-Company-Order")
        self.assertIsNone(subset.select("person_id").item())
        self.assertEqual(subset.select("company_id").item(), "C1")
        self.assertGreaterEqual(subset.select("time_lag").item(), 0)


if __name__ == "__main__":
    unittest.main()
