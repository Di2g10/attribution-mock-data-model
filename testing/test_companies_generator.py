"""Tests for the company generator module."""

from src.generators.company import generate

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 20


def test_company_unique_ids() -> None:
    """Test that generated company IDs are unique."""
    df = generate(LARGE_SAMPLE_SIZE)
    ids = df.select("company_id").to_series()
    assert ids.is_unique().all(), "company_id values should be unique"
    assert df.height == LARGE_SAMPLE_SIZE
