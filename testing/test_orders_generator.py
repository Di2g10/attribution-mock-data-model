"""Pytest tests for the orders generator module."""

import pytest
import polars as pl

from src.generators.orders import generate as generate_orders
from src.generators.company import generate as generate_company
from src.generators.person import generate as generate_person
from src.generators.products import generate as generate_products
from src.generators.interactions import generate as generate_interactions
from src.generators.channels import generate as generate_channels
from src.generators.marketing_assets import generate as generate_marketing_assets
from src.generators.marketing_activity import generate as generate_marketing_activity

# Sample sizes used across tests
LARGE_SAMPLE_SIZE = 20
SMALL_SAMPLE_SIZE = 10

# Maximum days between causal interaction and order
MAX_DAYS_INTERACTION_TO_ORDER = 30

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def products_df() -> pl.DataFrame:
    """Provide a Products DataFrame containing only `product_id`."""
    df = generate_products(SMALL_SAMPLE_SIZE)
    # `select` already returns a DataFrame; no need for `to_frame()`
    return df.select("product_id")


@pytest.fixture(scope="module")
def basic_prior(products_df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """Minimal prior dict containing just Products."""
    return {"Products": products_df}


# Related entities -----------------------------------------------------------


@pytest.fixture(scope="module")
def company_df() -> pl.DataFrame:
    """Generate a small sample of company data for testing."""
    return generate_company(SMALL_SAMPLE_SIZE)


@pytest.fixture(scope="module")
def person_df() -> pl.DataFrame:
    """Generate a small sample of person data for testing."""
    return generate_person(SMALL_SAMPLE_SIZE)


@pytest.fixture(scope="module")
def marketing_assets_df(products_df: pl.DataFrame) -> pl.DataFrame:
    """Generate marketing assets data with product relationships for testing."""
    return generate_marketing_assets(SMALL_SAMPLE_SIZE, prior={"Products": products_df})


@pytest.fixture(scope="module")
def campaigns_df() -> pl.DataFrame:
    """Create a simple campaigns DataFrame with IDs and names for testing."""
    ids = [f"CAM{str(i).zfill(7)}" for i in range(1, SMALL_SAMPLE_SIZE + 1)]
    names = [f"Campaign {i}" for i in range(1, SMALL_SAMPLE_SIZE + 1)]
    return pl.DataFrame({"campaign_id": ids, "name": names})


@pytest.fixture(scope="module")
def audience_df() -> pl.DataFrame:
    """Create a simple audience DataFrame with IDs and names for testing."""
    ids = [f"AUD{str(i).zfill(7)}" for i in range(1, SMALL_SAMPLE_SIZE + 1)]
    names = [f"Audience {i}" for i in range(1, SMALL_SAMPLE_SIZE + 1)]
    return pl.DataFrame({"audience_id": ids, "name": names})


@pytest.fixture(scope="module")
def channels_df() -> pl.DataFrame:
    """Generate a small sample of channels data for testing."""
    return generate_channels(SMALL_SAMPLE_SIZE)


@pytest.fixture(scope="module")
def marketing_base_prior(
    marketing_assets_df: pl.DataFrame,
    campaigns_df: pl.DataFrame,
    channels_df: pl.DataFrame,
) -> dict[str, pl.DataFrame]:
    """Create a base prior dictionary with marketing-related entities."""
    return {
        "Marketing Assets": marketing_assets_df,
        "Campaigns": campaigns_df,
        "Channels": channels_df,
    }


@pytest.fixture(scope="module")
def marketing_activity_prior(
    marketing_base_prior: dict[str, pl.DataFrame],
    company_df: pl.DataFrame,
    person_df: pl.DataFrame,
    audience_df: pl.DataFrame,
) -> dict[str, pl.DataFrame]:
    """Create a prior dictionary with all required entities for marketing activity generation."""
    return {
        **marketing_base_prior,
        "Company": company_df,
        "Person": person_df,
        "Audience": audience_df,
    }


@pytest.fixture(scope="module")
def marketing_activity_df(marketing_activity_prior: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Generate marketing activity data using the combined prior entities."""
    # generate a slightly larger pool for sampling
    return generate_marketing_activity(SMALL_SAMPLE_SIZE * 2, prior=marketing_activity_prior)


@pytest.fixture(scope="module")
def interactions_df(
    company_df: pl.DataFrame,
    person_df: pl.DataFrame,
    marketing_activity_df: pl.DataFrame,
) -> pl.DataFrame:
    """Generate interactions data with company, person, and marketing activity relationships."""
    prior = {
        "Company": company_df,
        "Person": person_df,
        "Marketing Activity": marketing_activity_df,
    }
    return generate_interactions(SMALL_SAMPLE_SIZE, prior=prior, keep_channel=True)


@pytest.fixture(scope="module")
def orders_df(
    company_df: pl.DataFrame,
    person_df: pl.DataFrame,
    products_df: pl.DataFrame,
    interactions_df: pl.DataFrame,
) -> pl.DataFrame:
    """Full Orders DataFrame with rich prior context."""
    prior = {
        "Company": company_df,
        "Person": person_df,
        "Products": products_df,
        "Interactions": interactions_df,
    }
    return generate_orders(SMALL_SAMPLE_SIZE, prior=prior)


# ---------------------------------------------------------------------------
# Tests that use only a minimal prior (Products)
# ---------------------------------------------------------------------------


def test_orders_unique_ids(basic_prior: dict[str, pl.DataFrame]) -> None:
    """Ensure `order_id` values are unique and row count correct."""
    df = generate_orders(LARGE_SAMPLE_SIZE, prior=basic_prior)
    ids = df.select("order_id").to_series()
    assert ids.is_unique().all()
    assert df.height == LARGE_SAMPLE_SIZE


def test_orders_with_related_objects(
    company_df: pl.DataFrame, person_df: pl.DataFrame, basic_prior: dict[str, pl.DataFrame]
) -> None:
    """Test order generation with company and person data in the prior context."""
    prior = {**basic_prior, "Company": company_df, "Person": person_df}
    df = generate_orders(SMALL_SAMPLE_SIZE, prior=prior)
    assert df.height == SMALL_SAMPLE_SIZE
    assert "order_id" in df.columns


def test_order_dates(basic_prior: dict[str, pl.DataFrame]) -> None:
    """Test that order completion dates are always after order raised dates."""
    df = generate_orders(SMALL_SAMPLE_SIZE, prior=basic_prior)
    starts = df.select("date_raised").to_series()
    ends = df.select("date_completed").to_series()
    assert all(e > s for s, e in zip(starts, ends))


def test_order_amounts(basic_prior: dict[str, pl.DataFrame]) -> None:
    """Test that order monetary values are positive numbers."""
    df = generate_orders(SMALL_SAMPLE_SIZE, prior=basic_prior)
    for col in ["sales_order_value", "initial_contract_value"]:
        vals = df.select(col).to_series()
        assert all((isinstance(v, (int, float)) and v > 0) for v in vals)


# ---------------------------------------------------------------------------
# Tests that require full prior context
# ---------------------------------------------------------------------------


def test_contact_links_to_person(orders_df: pl.DataFrame, person_df: pl.DataFrame) -> None:
    """Test that order contacts are valid person IDs from the person data."""
    contact_ids = set(orders_df.select("person_id").to_series().drop_nulls())
    person_ids = set(person_df.select("person_id").to_series())
    assert contact_ids.intersection(person_ids)


def test_contact_consistent_with_company(
    orders_df: pl.DataFrame, interactions_df: pl.DataFrame
) -> None:
    """Ensure contacts assigned to orders are consistent with company-person relationships from interactions.

    This test verifies that when an order has both a company and a contact assigned,
    the contact must have previously interacted with that company according to the
    interactions data. This maintains data consistency and reflects real-world business
    relationships where orders typically come from established contacts.

    :param orders_df: DataFrame containing order data
    :param interactions_df: DataFrame containing interaction data
    """
    mapping: dict[str, set[str]] = {}
    for row in interactions_df.iter_rows(named=True):
        comp, pers = row.get("interacted_company_id"), row.get("interacted_person_id")
        if comp and pers:
            mapping.setdefault(comp, set()).add(pers)
    df = orders_df.filter(pl.col("company_id").is_not_null() & pl.col("person_id").is_not_null())
    for row in df.iter_rows(named=True):
        comp, cont = row.get("company_id"), row.get("person_id")
        if comp in mapping:
            assert cont in mapping[comp]


def test_previous_order_id_consistency(orders_df: pl.DataFrame) -> None:
    """Test that previous order dates are always before the current order date."""
    id_to_date = dict(zip(orders_df["order_id"], orders_df["date_raised"]))
    prev = orders_df.filter(pl.col("previous_order_id").is_not_null())
    for row in prev.iter_rows(named=True):
        assert id_to_date[row["previous_order_id"]] < row["date_raised"]


def test_causal_interaction_consistency(
    orders_df: pl.DataFrame, interactions_df: pl.DataFrame
) -> None:
    """Test that causal interactions occur before orders and within the expected timeframe."""
    int_map = dict(zip(interactions_df["interaction_id"], interactions_df["interaction_date"]))
    df = orders_df.filter(pl.col("causal_interaction_id").is_not_null())
    for row in df.iter_rows(named=True):
        ci_date = int_map.get(row["causal_interaction_id"])
        if ci_date:
            diff = (row["date_raised"] - ci_date).days
            assert 0 <= diff <= MAX_DAYS_INTERACTION_TO_ORDER
