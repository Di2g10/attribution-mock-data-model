"""Contains a function to generate order data."""

from __future__ import annotations

from typing import Any
from datetime import timedelta

import polars as pl

from ..random_utils import fake, make_ids, random_date, weighted_sample

__all__ = ["generate"]

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


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of order data."""
    # Extract prior data if available
    # prior = kwargs.get("prior", {})
    # Note: We're not currently using prior data

    # Generate order IDs
    ids = make_ids(n, "ORD")

    # Note: We're not currently using company_df or person_df
    # but keeping the parameters for future use

    # Generate order dates
    order_dates = [random_date() for _ in ids]

    # Generate delivery dates (between 1 and 30 days after order date)
    delivery_dates = []
    for order_date in order_dates:
        delivery_delay = timedelta(days=fake.random_int(min=1, max=30))
        delivery_dates.append(order_date + delivery_delay)

    # Generate order amounts
    order_amounts = [round(fake.random.uniform(100, 10000), 2) for _ in ids]

    # Probabilities for various fields
    ceased_date_probability = 0.2
    cancel_reason_probability = 0.1
    cessation_reason_probability = 0.1
    previous_order_probability = 0.3
    related_opportunity_probability = 0.5
    causal_interaction_probability = 0.4

    # Generate order data with fields from the spreadsheet
    return pl.DataFrame(
        {
            "id": ids,
            "name": [f"Order {i}" for i in ids],
            "company": [fake.company() for _ in ids],
            "product": [fake.bs() for _ in ids],
            "product_family": weighted_sample(
                ["Hardware", "Software", "Services", "Consulting", "Support"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                n,
            ),
            "product_group": weighted_sample(
                ["Enterprise", "SMB", "Consumer", "Government", "Education"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                n,
            ),
            "product_price_type": weighted_sample(
                ["Fixed", "Variable", "Tiered", "Subscription", "Usage-based"],
                [0.3, 0.3, 0.2, 0.1, 0.1],
                n,
            ),
            "product_quantity": [fake.random_int(min=1, max=100) for _ in ids],
            "date_raised": order_dates,
            "date_completed": delivery_dates,
            "ceased_date": [
                random_date() if fake.random.random() < ceased_date_probability else None
                for _ in ids
            ],
            "transaction_date": [random_date() for _ in ids],
            "transaction_channel": weighted_sample(
                ["Online", "Phone", "In-person", "Email", "Partner"], [0.4, 0.3, 0.1, 0.1, 0.1], n
            ),
            "sales_order_value": order_amounts,
            "sales_order_value_gross_margin": [
                round(amount * 0.4, 2) for amount in order_amounts
            ],  # 40% margin
            "initial_contract_value": [
                round(amount * 1.5, 2) for amount in order_amounts
            ],  # 1.5x order amount
            "initial_contract_value_gross_margin": [
                round(amount * 0.4 * 1.5, 2) for amount in order_amounts
            ],  # 40% margin on 1.5x
            "average_revenue_per_unit": [
                round(amount / fake.random_int(min=1, max=10), 2) for amount in order_amounts
            ],
            "contract_term": [fake.random_int(min=1, max=36) for _ in ids],  # in months
            "action_type": weighted_sample(
                ["New", "Renewal", "Upgrade", "Downgrade", "Cancellation"],
                [0.4, 0.3, 0.1, 0.1, 0.1],
                n,
            ),
            "cancel_reason": [
                (
                    fake.text(max_nb_chars=50)
                    if fake.random.random() < cancel_reason_probability
                    else None
                )
                for _ in ids
            ],
            "cessetion_reason": [
                (
                    fake.text(max_nb_chars=50)
                    if fake.random.random() < cessation_reason_probability
                    else None
                )
                for _ in ids
            ],
            "contact": [fake.name() for _ in ids],
            "previous_order_id": [
                (
                    f"ORD{fake.random_int(min=1, max=9999):07d}"
                    if fake.random.random() < previous_order_probability
                    else None
                )
                for _ in ids
            ],
            "related_opportunity": [
                (
                    f"OPP{fake.random_int(min=1, max=9999):07d}"
                    if fake.random.random() < related_opportunity_probability
                    else None
                )
                for _ in ids
            ],
            "causal_interaction": [
                (
                    f"INT{fake.random_int(min=1, max=9999):07d}"
                    if fake.random.random() < causal_interaction_probability
                    else None
                )
                for _ in ids
            ],
        }
    )
