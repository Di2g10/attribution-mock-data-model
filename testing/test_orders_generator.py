"""Tests for the orders generator module."""

from src.generators.orders import generate

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 20
SMALL_SAMPLE_SIZE = 10


def test_orders_unique_ids() -> None:
    """Test that generated order IDs are unique."""
    df = generate(LARGE_SAMPLE_SIZE)
    ids = df.select("id").to_series()
    assert ids.is_unique().all(), "id values should be unique"
    assert df.height == LARGE_SAMPLE_SIZE


def test_orders_with_related_objects() -> None:
    """Test order generation with related objects."""
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

    # Generate orders with related data
    df = generate(SMALL_SAMPLE_SIZE, prior={"Company": company_df, "Person": person_df})

    # Just verify that the generation works with related data
    # We no longer include company_id, person_id, or sales_rep_id fields as per the spreadsheet
    assert df.height == SMALL_SAMPLE_SIZE
    assert "id" in df.columns


def test_order_dates() -> None:
    """Test that order completion dates are after raised dates."""
    df = generate(SMALL_SAMPLE_SIZE)

    # Get raised and completed dates
    raised_dates = df.select("date_raised").to_series().to_list()
    completed_dates = df.select("date_completed").to_series().to_list()

    # Check that each completed date is after its corresponding raised date
    for i in range(len(raised_dates)):
        assert (
            completed_dates[i] > raised_dates[i]
        ), f"Completed date should be after raised date for order {i}"


def test_order_amounts() -> None:
    """Test that order amounts are present and valid."""
    df = generate(SMALL_SAMPLE_SIZE)

    # Check that sales_order_value is present and contains valid numbers
    sales_order_values = df.select("sales_order_value").to_series().to_list()
    for value in sales_order_values:
        assert isinstance(value, (int, float)), "sales_order_value should be a number"
        assert value > 0, "sales_order_value should be positive"

    # Check that initial_contract_value is present and contains valid numbers
    contract_values = df.select("initial_contract_value").to_series().to_list()
    for value in contract_values:
        assert isinstance(value, (int, float)), "initial_contract_value should be a number"
        assert value > 0, "initial_contract_value should be positive"
