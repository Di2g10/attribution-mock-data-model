"""Tests for the interactions generator module."""

from src.generators.interactions import generate

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
    import polars as pl

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

    # Generate interactions with related data
    df = generate(SMALL_SAMPLE_SIZE, prior={"Company": company_df, "Person": person_df})

    # Just verify that the generation works with related data
    # We no longer include company_id, person_id, or owner_id fields as per the spreadsheet
    assert df.height == SMALL_SAMPLE_SIZE
    assert "interactionid" in df.columns
