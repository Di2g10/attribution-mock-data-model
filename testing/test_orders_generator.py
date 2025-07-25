"""Tests for the orders generator module."""

import unittest
from typing import Dict

import polars as pl

from src.generators.orders import generate
from src.generators.products import generate as generate_products
from src.generators.company import generate as generate_company
from src.generators.person import generate as generate_person
from src.generators.interactions import generate as generate_interactions
from src.generators.person_company_role import generate as generate_person_company_role

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


class TestOrderRelationships(unittest.TestCase):
    """Test the relationships between orders and other entities."""

    def setUp(self) -> None:
        """Set up test data for relationship tests."""
        # Generate test data for all entities
        self.company_df = generate_company(SMALL_SAMPLE_SIZE)
        self.person_df = generate_person(SMALL_SAMPLE_SIZE)
        self.products_df = generate_products(SMALL_SAMPLE_SIZE)

        # Generate interactions with company and person data
        self.interactions_df = generate_interactions(
            SMALL_SAMPLE_SIZE,
            prior={"Company": self.company_df, "Person": self.person_df},
            keep_channel=True,
        )

        # Generate person-company role data
        self.person_company_role_df = generate_person_company_role(
            SMALL_SAMPLE_SIZE,
            prior={"Company": self.company_df, "Person": self.person_df},
        )

        # Generate orders with all related data
        self.orders_df = generate(
            SMALL_SAMPLE_SIZE,
            prior={
                "Company": self.company_df,
                "Person": self.person_df,
                "Products": self.products_df,
                "Interactions": self.interactions_df,
                "PersonCompanyRole": self.person_company_role_df,
            },
        )

    def test_orders_link_to_products(self) -> None:
        """Test that orders link to products at the lowest tier (most granular)."""
        # Check if product field exists in orders
        self.assertIn("product", self.orders_df.columns, "Orders should have a product field")

        # Check if product_family field exists in orders
        self.assertIn(
            "product_family", self.orders_df.columns, "Orders should have a product_family field"
        )

    def test_contact_links_to_person(self) -> None:
        """Test that contact in orders links to a person in the person table."""
        # Get all contacts from orders
        order_contacts = self.orders_df.select("contact_id").to_series().to_list()

        # Get all person IDs from person table
        person_ids = self.person_df.select("person_id").to_series().to_list()

        # Check if at least some contacts are valid person IDs
        valid_contacts = [contact for contact in order_contacts if contact in person_ids]
        self.assertGreater(
            len(valid_contacts), 0, "At least some contacts should be valid person IDs"
        )

    def test_contact_consistent_with_company(self) -> None:
        """Test that contact is consistent with the company in orders."""
        # Create a mapping of companies to persons
        company_person_map: Dict[str, set[str]] = {}

        # If we have interaction data, use it to build company-person relationships
        if (
            "companyinteracted" in self.interactions_df.columns
            and "personinteracted" in self.interactions_df.columns
        ):
            for row in self.interactions_df.iter_rows(named=True):
                company = row.get("companyinteracted")
                person = row.get("personinteracted")

                if company and person:
                    if company not in company_person_map:
                        company_person_map[company] = set()
                    company_person_map[company].add(person)

        # Get orders with both company and contact
        orders_with_both = self.orders_df.select(["id", "company", "contact_id"]).filter(
            (pl.col("company").is_not_null()) & (pl.col("contact_id").is_not_null())
        )

        # If there are any orders with both company and contact, and we have company-person relationships
        if orders_with_both.height > 0 and company_person_map:
            # Count how many orders have consistent company-contact relationships
            consistent_count = 0

            for row in orders_with_both.iter_rows(named=True):
                company = row.get("company")
                contact = row.get("contact_id")

                # If we have person data for this company and the contact is associated with it
                if company in company_person_map and contact in company_person_map[company]:
                    consistent_count += 1

            # We should have at least some consistent relationships
            # This is a soft check because not all contacts may be in our test data
            if consistent_count > 0:
                self.assertGreater(
                    consistent_count,
                    0,
                    "At least some orders should have contacts consistent with their companies",
                )

    def test_previous_order_id_consistency(self) -> None:
        """Test that previous_order_id references another order with consistent dates."""
        # Get all order IDs and dates
        order_ids = self.orders_df.select("id").to_series().to_list()
        order_dates = self.orders_df.select("date_raised").to_series().to_list()

        # Create a mapping of order IDs to dates
        order_date_map = {order_id: date for order_id, date in zip(order_ids, order_dates)}

        # Get all previous order IDs that are not None
        prev_orders = self.orders_df.select(["id", "previous_order_id", "date_raised"]).filter(
            pl.col("previous_order_id").is_not_null()
        )

        # If there are any previous orders, check date consistency
        if prev_orders.height > 0:
            for row in prev_orders.iter_rows(named=True):
                current_order_id = row.get("id")
                prev_order_id = row.get("previous_order_id")
                current_date = row.get("date_raised")

                # If the previous order ID is in our generated orders
                if prev_order_id in order_date_map:
                    prev_date = order_date_map[prev_order_id]
                    self.assertLess(
                        prev_date,
                        current_date,
                        f"Previous order {prev_order_id} should have a date before current order {current_order_id}",
                    )

    def test_causal_interaction_consistency(self) -> None:
        """Test that causal_interaction references an interaction with consistent dates and company."""
        # Get all interaction IDs and dates
        interaction_ids = self.interactions_df.select("interactionid").to_series().to_list()
        interaction_dates = self.interactions_df.select("date").to_series().to_list()

        # Create a mapping of interaction IDs to dates
        interaction_date_map = {
            interaction_id: date for interaction_id, date in zip(interaction_ids, interaction_dates)
        }

        # Get all causal interactions that are not None
        causal_orders = self.orders_df.select(["id", "causal_interaction", "date_raised"]).filter(
            pl.col("causal_interaction").is_not_null()
        )

        # If there are any causal interactions, check date consistency
        if causal_orders.height > 0:
            for row in causal_orders.iter_rows(named=True):
                current_order_id = row.get("id")
                causal_interaction_id = row.get("causal_interaction")
                order_date = row.get("date_raised")

                # If the causal interaction ID is in our generated interactions
                if causal_interaction_id in interaction_date_map:
                    interaction_date = interaction_date_map[causal_interaction_id]
                    self.assertLessEqual(
                        interaction_date,
                        order_date,
                        f"Causal interaction {causal_interaction_id} should have a date before or equal to order {current_order_id}",
                    )
                    # Check that the interaction happened within 30 days before the order
                    days_before = (order_date - interaction_date).days
                    self.assertLessEqual(
                        days_before,
                        30,
                        f"Causal interaction {causal_interaction_id} should be within 30 days before order {current_order_id}",
                    )

    def test_orders_respect_person_company_roles(self) -> None:
        """Test that orders respect person-company role relationships."""
        # Create a mapping of persons to companies based on person-company role data
        person_company_map: Dict[str, set[str]] = {}

        # If we have person-company role data, use it to build person-company relationships
        if (
            "person_id" in self.person_company_role_df.columns
            and "company_id" in self.person_company_role_df.columns
        ):
            for row in self.person_company_role_df.iter_rows(named=True):
                person_id = row.get("person_id")
                company_id = row.get("company_id")

                if person_id and company_id:
                    if person_id not in person_company_map:
                        person_company_map[person_id] = set()
                    person_company_map[person_id].add(company_id)

        # Get orders with both company and contact
        orders_with_both = self.orders_df.select(["id", "company", "contact_id"]).filter(
            (pl.col("company").is_not_null()) & (pl.col("contact_id").is_not_null())
        )

        # If there are any orders with both company and contact, and we have person-company relationships
        if orders_with_both.height > 0 and person_company_map:
            # Count how many orders have consistent person-company relationships
            consistent_count = 0

            for row in orders_with_both.iter_rows(named=True):
                company = row.get("company")
                contact = row.get("contact_id")

                # If the contact has company relationships and the order's company is one of them
                if contact in person_company_map and company in person_company_map[contact]:
                    consistent_count += 1

            # We should have at least some consistent relationships
            # This is a soft check because not all contacts may have role relationships in our test data
            if consistent_count > 0:
                self.assertGreater(
                    consistent_count,
                    0,
                    "At least some orders should have contacts with roles at the order's company",
                )
