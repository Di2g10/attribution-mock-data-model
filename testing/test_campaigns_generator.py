"""Tests for the campaigns generator module."""

from src.generators.campaigns import generate

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 20
SMALL_SAMPLE_SIZE = 10


def test_campaigns_unique_ids() -> None:
    """Test that generated campaign IDs are unique."""
    df = generate(LARGE_SAMPLE_SIZE)
    ids = df.select("campaign_id").to_series()
    assert ids.is_unique().all(), "campaign_id values should be unique"
    assert df.height == LARGE_SAMPLE_SIZE


def test_campaigns_with_company() -> None:
    """Test campaign generation with company data."""
    # Create a mock company DataFrame
    import polars as pl

    company_df = pl.DataFrame(
        {
            "company_id": ["CO0000001", "CO0000002", "CO0000003"],
            "company_name": ["Company A", "Company B", "Company C"],
        }
    )

    # Generate campaigns with company data
    df = generate(SMALL_SAMPLE_SIZE, prior={"Company": company_df})

    # Check that company_id column exists
    assert "company_id" in df.columns

    # Check that all company_ids are from the provided list
    company_ids = df.select("company_id").to_series().to_list()
    for company_id in company_ids:
        assert company_id in ["CO0000001", "CO0000002", "CO0000003"]


def test_campaign_dates() -> None:
    """Test that campaign end dates are after start dates."""
    df = generate(SMALL_SAMPLE_SIZE)

    # Convert to Python datetime objects for comparison
    start_dates = df.select("start_date").to_series().to_list()
    end_dates = df.select("end_date").to_series().to_list()

    # Check that each end date is after its corresponding start date
    for i in range(len(start_dates)):
        assert (
            end_dates[i] > start_dates[i]
        ), f"End date should be after start date for campaign {i}"
