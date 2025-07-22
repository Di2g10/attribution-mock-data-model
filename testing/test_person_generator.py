"""Tests for the person generator module."""

from src.generators.person import generate

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 20
SMALL_SAMPLE_SIZE = 10


def test_person_unique_ids() -> None:
    """Test that generated person IDs are unique."""
    df = generate(LARGE_SAMPLE_SIZE)
    ids = df.select("person_id").to_series()
    assert ids.is_unique().all(), "person_id values should be unique"
    assert df.height == LARGE_SAMPLE_SIZE


def test_person_with_company() -> None:
    """Test person generation with company data."""
    # Create a mock company DataFrame
    import polars as pl

    company_df = pl.DataFrame(
        {
            "company_id": ["CO0000001", "CO0000002", "CO0000003"],
            "company_name": ["Company A", "Company B", "Company C"],
        }
    )

    # Generate persons with company data
    df = generate(SMALL_SAMPLE_SIZE, prior={"Company": company_df})

    # Just verify that the generation works with company data
    # We no longer include company_id in the person object as per the spreadsheet
    assert df.height == SMALL_SAMPLE_SIZE
    assert "person_id" in df.columns
