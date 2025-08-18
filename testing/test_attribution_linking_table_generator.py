"""Test the attribution linking table generator and supporting functions."""

import unittest
import polars as pl

from src.generators.attribution_linking_table import (
    _create_ancestry,
    _build_links,
    _best_product_yca_level,
)


# import the function you just wrote
# from my_module.hierarchy import create_ancestory   # ⇦ adjust as needed


class TestBestProductYCA(unittest.TestCase):
    """Tests for _best_product_yca_level over a tiny product hierarchy."""

    def setUp(self) -> None:
        """Create a small product hierarchy for testing."""
        # Build a 3-level product tree:
        #   P1 (Tier 1)
        #   ├─ P2 (Tier 2)
        #   │    └─ P4 (Tier 3)
        #   └─ P3 (Tier 2)
        self.products = pl.DataFrame(
            {
                "product_id": ["P1", "P2", "P3", "P4"],
                "product_parent_id": [None, "P1", "P1", "P2"],
                "level": ["Tier 1", "Tier 2", "Tier 2", "Tier 3"],
            }
        )
        closure = _create_ancestry(
            self.products, row_id="product_id", parent_id="product_parent_id"
        )
        self.links = _build_links(closure)

    def test_prefers_closest_campaign(self) -> None:
        """When campaign is closer, use it."""
        # outcome P4, campaign P2 (closest common ancestor P2 => Tier 2), asset P3 (YCA P1 => Tier 1)
        rows = pl.DataFrame(
            {
                "outcome_product_id": ["P4"],
                "campaign_product_id": ["P2"],
                "asset_product_id": ["P3"],
            }
        )
        result = _best_product_yca_level(
            rows,
            self.links,
            self.products,
            outcome_col="outcome_product_id",
            campaign_col="campaign_product_id",
            asset_col="asset_product_id",
        )
        self.assertEqual(result.item(), "Tier 2")

    def test_uses_asset_when_better_or_only(self) -> None:
        """When asset is better or only, use it."""
        # outcome P4, campaign P3 (YCA P1 => Tier 1, degrees 3), asset P2 (YCA P2 => Tier 2, degrees 1)
        rows = pl.DataFrame(
            {
                "outcome_product_id": ["P4"],
                "campaign_product_id": ["P3"],
                "asset_product_id": ["P2"],
            }
        )
        result = _best_product_yca_level(
            rows,
            self.links,
            self.products,
            outcome_col="outcome_product_id",
            campaign_col="campaign_product_id",
            asset_col="asset_product_id",
        )
        self.assertEqual(result.item(), "Tier 2")

    def test_null_when_no_ids(self) -> None:
        """When all IDs are null, return None."""
        rows = pl.DataFrame(
            {
                "outcome_product_id": [None],
                "campaign_product_id": [None],
                "asset_product_id": [None],
            }
        )
        result = _best_product_yca_level(
            rows,
            self.links,
            self.products,
            outcome_col="outcome_product_id",
            campaign_col="campaign_product_id",
            asset_col="asset_product_id",
        )
        self.assertIsNone(result.item())


class TestCreateAncestory(unittest.TestCase):
    """Tests for the create_ancestory utility."""

    # 👇 tell mypy these attributes exist and what they are
    df: pl.DataFrame
    closure: pl.DataFrame

    def setUp(self) -> None:
        """Create company tree used in all test cases.

         1
        ├─2
        │ └─4
        └─3

        """
        self.df = pl.DataFrame(
            {
                "company_id": [1, 2, 3, 4],
                "parent_id": [None, 1, 1, 2],
            }
        )

        # full closure we expect back
        self.expected_rows: set[tuple[int, int, int]] = {
            (1, 1, 0),
            (2, 2, 0),
            (2, 1, 1),
            (3, 3, 0),
            (3, 1, 1),
            (4, 4, 0),
            (4, 2, 1),
            (4, 1, 2),
        }

    # ------------------------------------------------------------------
    def test_closure_rows(self) -> None:
        """All (node, ancestor, distance) rows should be present."""
        closure = _create_ancestry(self.df, row_id="company_id", parent_id="parent_id")

        self.assertSetEqual(
            set(map(tuple, closure.rows())),
            self.expected_rows,
            msg="Closure rows or distances are incorrect",
        )

    # ------------------------------------------------------------------
    def test_column_schema(self) -> None:
        """Returned DataFrame must keep the canonical column names."""
        closure = _create_ancestry(self.df, row_id="company_id", parent_id="parent_id")
        self.assertListEqual(
            closure.columns,
            ["origin_id", "ancestor_id", "distance"],
        )


class TestBuildLinks(unittest.TestCase):
    """Tests for `build_links`, ensuring symmetry and shortest-path selection."""

    # 👇 tell mypy these attributes exist and what they are
    df: pl.DataFrame
    closure: pl.DataFrame
    links: pl.DataFrame

    @classmethod
    def setUpClass(cls) -> None:
        """Create Data For the Tests."""
        cls.df = pl.DataFrame(
            {
                "company_id": [1, 2, 3, 4],
                "parent_id": [None, 1, 1, 2],
            }
        )
        cls.closure = _create_ancestry(cls.df, row_id="company_id", parent_id="parent_id")
        cls.links = _build_links(cls.closure)

    # ------------------------------------------------------------------
    def test_schema(self) -> None:
        """Check the Links table has the expected columns in order."""
        self.assertListEqual(
            self.links.columns,
            ["from_id", "to_id", "ancestor_id", "degrees"],
        )

    # ------------------------------------------------------------------
    def test_expected_rows(self) -> None:
        """Verify a complete and symmetric set with minimal degrees."""
        expected = {
            (1, 2, 1, 1),
            (2, 1, 1, 1),
            (1, 3, 1, 1),
            (3, 1, 1, 1),
            (1, 4, 1, 2),
            (4, 1, 1, 2),
            (2, 3, 1, 2),
            (3, 2, 1, 2),
            (2, 4, 2, 1),
            (4, 2, 2, 1),
            (3, 4, 1, 3),
            (4, 3, 1, 3),
            (1, 1, 1, 0),
            (2, 2, 2, 0),
            (3, 3, 3, 0),
            (4, 4, 4, 0),
        }
        self.assertSetEqual(
            set(map(tuple, self.links.rows())),
            expected,
            msg="Link set is incomplete, non-symmetric, or contains wrong degrees.",
        )

    # ------------------------------------------------------------------
    def test_shortest_path_kept(self) -> None:
        """For any unordered pair {A,B} the degrees value must be *minimal*.

        E.g. 2↔4 should use ancestor 2 (degrees 1), not root 1 (degrees 3).
        """
        from_id, to_id = 2, 4
        subset = self.links.filter((pl.col("from_id") == from_id) & (pl.col("to_id") == to_id))
        self.assertEqual(
            subset.select("degrees").item(),
            1,
            msg="Non-minimal path retained for nodes 2 and 4.",
        )


class TestStringIds(unittest.TestCase):
    """Verify that create_ancestry and build_links work when IDs are strings.

    Hierarchy:   A
               ├─B
               │ └─D
               └─C
    """

    # 👇 tell mypy these attributes exist and what they are
    df: pl.DataFrame
    closure: pl.DataFrame
    links: pl.DataFrame

    @classmethod
    def setUpClass(cls) -> None:
        """Create closure and links from mock data, to enable tests."""
        cls.df = pl.DataFrame(
            {
                "company_id": ["A", "B", "C", "D"],
                "parent_id": [None, "A", "A", "B"],
            }
        )
        cls.closure = _create_ancestry(cls.df, row_id="company_id", parent_id="parent_id")
        cls.links = _build_links(cls.closure)

    # ------------------------------------------------------------------
    def test_closure_rows_string_ids(self) -> None:
        """Test closure function still works with strings."""
        expected = {
            ("A", "A", 0),
            ("B", "B", 0),
            ("B", "A", 1),
            ("C", "C", 0),
            ("C", "A", 1),
            ("D", "D", 0),
            ("D", "B", 1),
            ("D", "A", 2),
        }
        self.assertSetEqual(
            set(map(tuple, self.closure.rows())),
            expected,
            msg="String-ID closure incorrect.",
        )

    # ------------------------------------------------------------------
    def test_links_string_ids(self) -> None:
        """Ensure symmetric link table and correct hop counts with string IDs."""
        exp_links = {
            ("A", "A", "A", 0),  # self-link
            ("B", "B", "B", 0),
            ("C", "C", "C", 0),
            ("D", "D", "D", 0),
            ("A", "B", "A", 1),
            ("B", "A", "A", 1),
            ("A", "C", "A", 1),
            ("C", "A", "A", 1),
            ("A", "D", "A", 2),
            ("D", "A", "A", 2),
            ("B", "C", "A", 2),
            ("C", "B", "A", 2),
            ("B", "D", "B", 1),
            ("D", "B", "B", 1),
            ("C", "D", "A", 3),
            ("D", "C", "A", 3),
        }

        self.assertSetEqual(
            set(map(tuple, self.links.rows())),
            exp_links,
            msg="String-ID link table incorrect or non-symmetric.",
        )

    # ------------------------------------------------------------------
    def test_schema_string_ids(self) -> None:
        """Ensure symmetric link table and correct hop counts with string IDs."""
        self.assertListEqual(
            self.links.columns,
            ["from_id", "to_id", "ancestor_id", "degrees"],
        )


if __name__ == "__main__":
    unittest.main()
