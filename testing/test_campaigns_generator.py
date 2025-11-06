"""Tests for the campaigns generator module."""

import pytest
import polars as pl
from src.generators.campaigns import generate
from src.random_utils import make_ids

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 20
SMALL_SAMPLE_SIZE = 10


@pytest.fixture(scope="module")
def products_df() -> pl.DataFrame:
    """Provide a dummy Products DataFrame for campaign generator tests."""
    product_ids = make_ids(LARGE_SAMPLE_SIZE, "PRD")
    return pl.DataFrame({"product_id": product_ids})


def test_campaigns_unique_ids(products_df: pl.DataFrame) -> None:
    """Test that generated campaign IDs are unique."""
    df = generate(LARGE_SAMPLE_SIZE, prior={"Products": products_df})
    ids = df.select("campaign_id").to_series()
    assert ids.is_unique().all(), "campaign_id values should be unique"
    assert df.height == LARGE_SAMPLE_SIZE


def test_campaign_dates(products_df: pl.DataFrame) -> None:
    """Test that overall timeline end dates are after start dates."""
    df = generate(SMALL_SAMPLE_SIZE, prior={"Products": products_df})

    # Convert to Python datetime objects for comparison
    start_dates = df.select("overall_timeline_start").to_series().to_list()
    end_dates = df.select("overall_timeline_end").to_series().to_list()

    # Check that each end date is after its corresponding start date
    for i in range(len(start_dates)):
        assert (
            end_dates[i] > start_dates[i]
        ), f"overall_timeline_end should be after overall_timeline_start for campaign {i}"
