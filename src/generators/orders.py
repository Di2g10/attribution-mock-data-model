"""Contains a function to generate order data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timedelta

import polars as pl

from ..random_utils import fake, make_ids, random_date, weighted_sample

__all__ = ["generate"]


@dataclass
class OrderData:
    """Container for order data parameters."""

    n: int
    ids: List[str]
    order_dates: List[datetime]
    delivery_dates: List[datetime]
    order_amounts: List[float]
    order_companies: List[str]
    order_contacts: List[str]
    company_orders_map: Dict[str, List[Tuple[str, datetime]]]
    company_interactions_map: Dict[str, List[str]]
    interaction_dates_map: Dict[str, datetime]
    ceased_date_probability: float
    previous_order_probability: float
    related_opportunity_probability: float
    causal_interaction_probability: float


# Maximum number of days before an order for a causal interaction
MAX_DAYS_BEFORE_ORDER = 30


def _find_previous_order(
    current_order_id: str,
    current_order_date: datetime,
    company: str,
    company_orders_map: Dict[str, List[Tuple[str, datetime]]],
    probability: float,
) -> Optional[str]:
    """Find a previous order from the same company that ends before this order starts.

    :param current_order_id: ID of the current order
    :param current_order_date: Date of the current order
    :param company: Company ID or name
    :param company_orders_map: Mapping of companies to their orders
    :param probability: Probability of having a previous order
    :returns: ID of a previous order or None
    """
    # Apply probability check first
    if fake.random.random() >= probability:
        return None

    # If we don't have company orders data or this company has no orders, return None
    if not company_orders_map or company not in company_orders_map:
        return f"ORD{fake.random_int(min=1, max=9999):07d}"  # Fallback to random ID

    # Get all orders for this company
    company_orders = company_orders_map[company]

    # Find orders that are earlier than the current order
    previous_orders = [
        (order_id, order_date)
        for order_id, order_date in company_orders
        if order_date < current_order_date and order_id != current_order_id
    ]

    # If no previous orders, return None
    if not previous_orders:
        return None

    # Sort by date (most recent first)
    previous_orders.sort(key=lambda x: x[1], reverse=True)

    # Return the most recent previous order
    return previous_orders[0][0]


def _find_causal_interaction(
    order_date: datetime,
    company: str,
    company_interactions_map: Dict[str, List[str]],
    interaction_dates_map: Dict[str, datetime],
    probability: float,
) -> Optional[str]:
    """Find an interaction from the same company that happens before but close to the order date.

    :param order_date: Date of the order
    :param company: Company ID or name
    :param company_interactions_map: Mapping of companies to their interactions
    :param interaction_dates_map: Mapping of interaction IDs to their dates
    :param probability: Probability of having a causal interaction
    :returns: ID of a causal interaction or None
    """
    # Apply probability check first
    if fake.random.random() >= probability:
        return None

    # If we don't have company interactions data or this company has no interactions, return None
    if not company_interactions_map or company not in company_interactions_map:
        return f"INT{fake.random_int(min=1, max=9999):07d}"  # Fallback to random ID

    # Get all interactions for this company
    company_interactions = company_interactions_map[company]

    # Find interactions that happened before the order date but within 30 days
    causal_interactions = []
    for interaction_id in company_interactions:
        if interaction_id in interaction_dates_map:
            interaction_date = interaction_dates_map[interaction_id]
            days_before = (order_date - interaction_date).days
            if 0 <= days_before <= MAX_DAYS_BEFORE_ORDER:  # Within days limit before the order
                causal_interactions.append((interaction_id, interaction_date))

    # If no causal interactions, return None
    if not causal_interactions:
        return None

    # Sort by date (most recent first)
    causal_interactions.sort(key=lambda x: x[1], reverse=True)

    # Return the most recent causal interaction
    return causal_interactions[0][0]


# Order status with weights
ORDER_STATUS = ["Completed", "Pending", "Processing", "Cancelled", "Refunded", "On Hold"]

# Weights for order status (higher weight = more common)
ORDER_STATUS_WEIGHTS = [
    0.60,  # Completed
    0.15,  # Pending
    0.10,  # Processing
    0.05,  # Cancelled
    0.05,  # Refunded
    0.05,  # On Hold
]

# Payment methods with weights
PAYMENT_METHODS = ["Credit Card", "Bank Transfer", "PayPal", "Check", "Cash", "Invoice"]

# Weights for payment methods (higher weight = more common)
PAYMENT_METHOD_WEIGHTS = [
    0.40,  # Credit Card
    0.25,  # Bank Transfer
    0.15,  # PayPal
    0.10,  # Check
    0.05,  # Cash
    0.05,  # Invoice
]

# Product categories with weights
PRODUCT_CATEGORIES = [
    "Hardware",
    "Software",
    "Services",
    "Consulting",
    "Training",
    "Support",
    "Maintenance",
    "Subscription",
    "License",
]

# Weights for product categories (higher weight = more common)
PRODUCT_CATEGORY_WEIGHTS = [
    0.20,  # Hardware
    0.20,  # Software
    0.15,  # Services
    0.10,  # Consulting
    0.10,  # Training
    0.10,  # Support
    0.05,  # Maintenance
    0.05,  # Subscription
    0.05,  # License
]


# Standardized cancel reasons (stopped without using or applying)
CANCEL_REASONS = [
    "Customer changed business requirements",
    "Budget constraints/funding issues",
    "Found alternative solution",
    "Ordered incorrect product/service",
    "Duplicate order placed in error",
    "Requested adjustment then decided against change",
    "Pricing concerns after order placement",
    "Delivery timeframe too long",
    "Project cancelled or postponed",
    "Consolidating with existing services",
    "Regulatory compliance issues",
    "Company restructuring/acquisition",
    "Technical incompatibility identified post-order",
    "Contract terms unacceptable upon review",
]

# Weights for cancel reasons (higher weight = more common)
CANCEL_REASON_WEIGHTS = [
    0.15,  # Customer changed business requirements
    0.15,  # Budget constraints/funding issues
    0.12,  # Found alternative solution
    0.10,  # Ordered incorrect product/service
    0.10,  # Duplicate order placed in error
    0.08,  # Requested adjustment then decided against change
    0.07,  # Pricing concerns after order placement
    0.06,  # Delivery timeframe too long
    0.05,  # Project cancelled or postponed
    0.04,  # Consolidating with existing services
    0.03,  # Regulatory compliance issues
    0.02,  # Company restructuring/acquisition
    0.02,  # Technical incompatibility identified post-order
    0.01,  # Contract terms unacceptable upon review
]

# Standardized cessation reasons (stopped after use)
CESSATION_REASONS = [
    "End of contract term",
    "Business closure/downsizing",
    "Migration to new technology/platform",
    "Service performance issues",
    "Moving to competitor service",
    "Cost reduction initiative",
    "Service no longer required",
    "Consolidation of services",
    "Relocation of business premises",
    "Merger/acquisition",
    "Upgrade to different BT service",
    "Seasonal business requirement ended",
    "Regulatory/compliance changes",
    "Technical incompatibility with other systems",
    "Change in business strategy",
]

# Weights for cessation reasons (higher weight = more common)
CESSATION_REASON_WEIGHTS = [
    0.15,  # End of contract term
    0.12,  # Business closure/downsizing
    0.10,  # Migration to new technology/platform
    0.10,  # Service performance issues
    0.08,  # Moving to competitor service
    0.08,  # Cost reduction initiative
    0.07,  # Service no longer required
    0.07,  # Consolidation of services
    0.05,  # Relocation of business premises
    0.05,  # Merger/acquisition
    0.04,  # Upgrade to different BT service
    0.03,  # Seasonal business requirement ended
    0.03,  # Regulatory/compliance changes
    0.02,  # Technical incompatibility with other systems
    0.01,  # Change in business strategy
]


def _extract_prior_data(prior: Dict[str, Any]) -> Tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Extract company, person, and interaction data from prior data.

    :param prior: Dictionary of prior generated data
    :returns: Tuple of (company_df, person_df, interaction_df)
    """
    # Extract company data if available
    company_df = prior.get("Company")

    # Extract person data if available
    person_df = prior.get("Person")

    # Extract interaction data if available
    interaction_df = prior.get("Interactions")

    return company_df, person_df, interaction_df


def _generate_basic_order_data(
    n: int,
) -> Tuple[List[str], List[datetime], List[datetime], List[float]]:
    """Generate basic order data including IDs, dates, and amounts.

    :param n: Number of orders to generate
    :returns: Tuple of (ids, order_dates, delivery_dates, order_amounts)
    """
    # Generate order IDs
    ids = make_ids(n, "ORD")

    # Generate order dates
    order_dates = [random_date() for _ in ids]

    # Generate delivery dates (between 1 and 30 days after order date)
    delivery_dates = []
    for order_date in order_dates:
        delivery_delay = timedelta(days=fake.random_int(min=1, max=30))
        delivery_dates.append(order_date + delivery_delay)

    # Generate order amounts
    order_amounts = [round(fake.random.uniform(100, 10000), 2) for _ in ids]

    return ids, order_dates, delivery_dates, order_amounts


def _create_company_person_relationships(
    company_df: Optional[pl.DataFrame], person_df: Optional[pl.DataFrame], ids: List[str]
) -> Tuple[List[str], List[str], Dict[str, List[str]], List[str], List[str]]:
    """Create company-person relationships and assign to orders.

    :param company_df: DataFrame containing company data
    :param person_df: DataFrame containing person data
    :param ids: List of order IDs
    :returns: Tuple of (company_ids, person_ids, company_person_map, order_companies, order_contacts)
    """
    # Create mappings for company-person relationships
    company_person_map = {}
    company_ids = []
    person_ids = []

    # If we have company data, extract company IDs
    if company_df is not None and "company_id" in company_df.columns:
        company_ids = company_df["company_id"].to_list()

    # If we have person data, extract person IDs
    if person_df is not None and "person_id" in person_df.columns:
        person_ids = person_df["person_id"].to_list()

    # Create a mapping of companies to persons if we have both
    if company_ids and person_ids:
        # Assign multiple persons to each company
        for company_id in company_ids:
            # Assign 1-5 random persons to each company
            num_persons = fake.random_int(min=1, max=min(5, len(person_ids)))
            company_person_map[company_id] = fake.random.sample(person_ids, num_persons)

    # Assign companies to orders
    order_companies = []
    for _ in ids:
        if company_ids:
            # Use a real company ID
            order_companies.append(fake.random.choice(company_ids))
        else:
            # Generate a fake company name
            order_companies.append(fake.company())

    # Assign contacts to orders based on company-person mapping
    order_contacts = []
    for company in order_companies:
        if isinstance(company, str) and not company.startswith("CO"):
            # This is a fake company name, generate a fake contact
            order_contacts.append(fake.name())
        elif company_person_map.get(company):
            # This is a real company ID with associated persons
            order_contacts.append(fake.random.choice(company_person_map[company]))
        elif person_ids:
            # This is a real company ID but no specific persons, use any person
            order_contacts.append(fake.random.choice(person_ids))
        else:
            # No person data available, generate a fake contact
            order_contacts.append(fake.name())

    return company_ids, person_ids, company_person_map, order_companies, order_contacts


def _process_interaction_data(
    interaction_df: Optional[pl.DataFrame],
) -> Tuple[Dict[str, List[str]], Dict[str, datetime]]:
    """Process interaction data for causal interactions.

    :param interaction_df: DataFrame containing interaction data
    :returns: Tuple of (company_interactions_map, interaction_dates_map)
    """
    # Create a mapping of company to interactions for causal interactions
    company_interactions_map: Dict[str, List[str]] = {}
    interaction_dates_map: Dict[str, datetime] = {}

    # If we have interaction data, extract interaction IDs and dates
    if (
        interaction_df is not None
        and "interactionid" in interaction_df.columns
        and "date" in interaction_df.columns
    ):
        # Create a mapping of companies to interactions
        for row in interaction_df.iter_rows(named=True):
            interaction_id = row.get("interactionid")
            company = row.get("companyinteracted")
            date = row.get("date")

            if interaction_id and date:
                # Store the date for this interaction
                interaction_dates_map[interaction_id] = date

                # If company is available, add to company-interactions map
                if company:
                    if company not in company_interactions_map:
                        company_interactions_map[company] = []
                    company_interactions_map[company].append(interaction_id)

    return company_interactions_map, interaction_dates_map


def _create_order_company_mappings(
    ids: List[str], order_dates: List[datetime], order_companies: List[str]
) -> Dict[str, List[Tuple[str, datetime]]]:
    """Create order-company mappings for previous orders.

    :param ids: List of order IDs
    :param order_dates: List of order dates
    :param order_companies: List of company IDs or names
    :returns: Mapping of companies to their orders
    """
    # Sort orders by date for previous_order_id assignment
    order_data = list(zip(ids, order_dates, order_companies))
    order_data.sort(key=lambda x: x[1])  # Sort by date

    # Create a mapping of company to orders for previous_order_id
    company_orders_map: Dict[str, List[Tuple[str, datetime]]] = {}
    for order_id, order_date, company in order_data:
        if company not in company_orders_map:
            company_orders_map[company] = []
        company_orders_map[company].append((order_id, order_date))

    return company_orders_map


def _build_orders_dataframe(data: OrderData) -> pl.DataFrame:
    """Build the final DataFrame with all order fields.

    :param data: Container with all order data parameters
    :returns: DataFrame containing all order data
    """
    # Generate order data with fields from the spreadsheet
    return pl.DataFrame(
        {
            "id": data.ids,
            "name": [f"Order {i}" for i in data.ids],
            "company": data.order_companies,
            "product": [fake.bs() for _ in data.ids],
            "product_family": weighted_sample(
                ["Hardware", "Software", "Services", "Consulting", "Support"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                data.n,
            ),
            "product_group": weighted_sample(
                ["Enterprise", "SMB", "Consumer", "Government", "Education"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                data.n,
            ),
            "product_price_type": weighted_sample(
                ["Fixed", "Variable", "Tiered", "Subscription", "Usage-based"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                data.n,
            ),
            "product_quantity": [fake.random_int(min=1, max=100) for _ in data.ids],
            "date_raised": data.order_dates,
            "date_completed": data.delivery_dates,
            "ceased_date": [
                random_date() if fake.random.random() < data.ceased_date_probability else None
                for _ in data.ids
            ],
            "transaction_date": [random_date() for _ in data.ids],
            "transaction_channel": weighted_sample(
                ["Online", "Phone", "In-person", "Email", "Partner"],
                [0.4, 0.3, 0.1, 0.1, 0.1],
                data.n,
            ),
            "sales_order_value": data.order_amounts,
            "sales_order_value_gross_margin": [
                round(amount * 0.4, 2) for amount in data.order_amounts
            ],  # 40% margin
            "initial_contract_value": [
                round(amount * 1.5, 2) for amount in data.order_amounts
            ],  # 1.5x order amount
            "initial_contract_value_gross_margin": [
                round(amount * 0.4 * 1.5, 2) for amount in data.order_amounts
            ],  # 40% margin on 1.5x
            "average_revenue_per_unit": [
                round(amount / fake.random_int(min=1, max=10), 2) for amount in data.order_amounts
            ],
            "contract_term": [fake.random_int(min=1, max=36) for _ in data.ids],  # in months
            "action_type": weighted_sample(
                ["No Action", "Cease", "Modify", "Provide", "Mixed"],
                [0.05, 0.3, 0.2, 0.4, 0.05],
                data.n,
            ),
            "cancel_reason": weighted_sample(CANCEL_REASONS, CANCEL_REASON_WEIGHTS, data.n),
            "cessetion_reason": weighted_sample(
                CESSATION_REASONS, CESSATION_REASON_WEIGHTS, data.n
            ),
            "contact_id": data.order_contacts,
            "previous_order_id": [
                (
                    # Find a previous order from the same company
                    # that ends before this order starts
                    _find_previous_order(
                        order_id,
                        order_date,
                        company,
                        data.company_orders_map,
                        data.previous_order_probability,
                    )
                )
                for order_id, order_date, company in zip(
                    data.ids, data.order_dates, data.order_companies
                )
            ],
            "related_opportunity": [
                (
                    # Placeholder for related_opportunity
                    # This would reference an opportunity table that doesn't exist yet
                    f"OPP{fake.random_int(min=1, max=9999):07d}"
                    if fake.random.random() < data.related_opportunity_probability
                    else None
                )
                for _ in data.ids
            ],
            "causal_interaction": [
                (
                    # Find an interaction from the same company
                    # that happens before but close to the order date
                    _find_causal_interaction(
                        order_date,
                        company,
                        data.company_interactions_map,
                        data.interaction_dates_map,
                        data.causal_interaction_probability,
                    )
                )
                for order_date, company in zip(data.order_dates, data.order_companies)
            ],
        }
    )


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of order data.

    :param n: Number of orders to generate
    :param kwargs: Additional keyword arguments including prior data
    :returns: DataFrame containing generated order data
    """
    # Extract prior data if available
    prior = kwargs.get("prior", {})

    # Extract company, person, and interaction data
    company_df, person_df, interaction_df = _extract_prior_data(prior)

    # Generate basic order data
    ids, order_dates, delivery_dates, order_amounts = _generate_basic_order_data(n)

    # Probabilities for various fields
    ceased_date_probability = 0.2
    previous_order_probability = 0.3
    related_opportunity_probability = 0.5
    causal_interaction_probability = 0.4

    # Create company-person relationships and assign to orders
    company_ids, person_ids, company_person_map, order_companies, order_contacts = (
        _create_company_person_relationships(company_df, person_df, ids)
    )

    # Process interaction data for causal interactions
    company_interactions_map, interaction_dates_map = _process_interaction_data(interaction_df)

    # Create order-company mappings for previous orders
    company_orders_map = _create_order_company_mappings(ids, order_dates, order_companies)

    # Create OrderData instance
    order_data = OrderData(
        n=n,
        ids=ids,
        order_dates=order_dates,
        delivery_dates=delivery_dates,
        order_amounts=order_amounts,
        order_companies=order_companies,
        order_contacts=order_contacts,
        company_orders_map=company_orders_map,
        company_interactions_map=company_interactions_map,
        interaction_dates_map=interaction_dates_map,
        ceased_date_probability=ceased_date_probability,
        previous_order_probability=previous_order_probability,
        related_opportunity_probability=related_opportunity_probability,
        causal_interaction_probability=causal_interaction_probability,
    )

    # Build the final DataFrame with all fields
    return _build_orders_dataframe(order_data)
