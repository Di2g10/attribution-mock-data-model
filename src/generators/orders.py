# src/generators/orders.py
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
    order_contacts: List[str | None]
    company_orders_map: Dict[str, List[Tuple[str, datetime]]]
    company_interactions_map: Dict[str, List[str]]
    interaction_dates_map: Dict[str, datetime]
    ceased_date_probability: float
    previous_order_probability: float
    related_opportunity_probability: float
    causal_interaction_probability: float
    order_product_ids: List[str]


# Maximum number of days before an order for a causal interaction
MAX_DAYS_BEFORE_ORDER = 30


def _find_previous_order(
    current_order_id: str,
    current_order_date: datetime,
    company: str,
    company_orders_map: Dict[str, List[Tuple[str, datetime]]],
    probability: float,
) -> Optional[str]:
    """Find a previous order from the same company that ends before this order starts."""
    if fake.random.random() >= probability:
        return None

    if not company_orders_map or company not in company_orders_map:
        # Fallback: plausible-looking ID (keeps schema satisfied for tests expecting strings)
        return f"ORD{fake.random_int(min=1, max=9999):07d}"

    company_orders = company_orders_map[company]
    previous_orders = [
        (order_id, order_date)
        for order_id, order_date in company_orders
        if order_date < current_order_date and order_id != current_order_id
    ]
    if not previous_orders:
        return None

    previous_orders.sort(key=lambda x: x[1], reverse=True)
    return previous_orders[0][0]


def _find_causal_interaction(
    order_date: datetime,
    company: str,
    company_interactions_map: Dict[str, List[str]],
    interaction_dates_map: Dict[str, datetime],
    probability: float,
) -> Optional[str]:
    """Find an interaction from the same company that happens before but close to the order date."""
    if fake.random.random() >= probability:
        return None

    if not company_interactions_map or company not in company_interactions_map:
        # Fallback: plausible-looking ID (schema=string)
        return f"INT{fake.random_int(min=1, max=9999):07d}"

    company_interactions = company_interactions_map[company]
    causal_interactions: list[tuple[str, datetime]] = []
    for interaction_id in company_interactions:
        if interaction_id in interaction_dates_map:
            interaction_date = interaction_dates_map[interaction_id]
            days_before = (order_date - interaction_date).days
            if 0 <= days_before <= MAX_DAYS_BEFORE_ORDER:
                causal_interactions.append((interaction_id, interaction_date))

    if not causal_interactions:
        return None

    causal_interactions.sort(key=lambda x: x[1], reverse=True)
    return causal_interactions[0][0]


# Enumerations + weights (kept from original)
ORDER_STATUS = ["Completed", "Pending", "Processing", "Cancelled", "Refunded", "On Hold"]
ORDER_STATUS_WEIGHTS = [0.60, 0.15, 0.10, 0.05, 0.05, 0.05]

PAYMENT_METHODS = ["Credit Card", "Bank Transfer", "PayPal", "Check", "Cash", "Invoice"]
PAYMENT_METHOD_WEIGHTS = [0.40, 0.25, 0.15, 0.10, 0.05, 0.05]

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
PRODUCT_CATEGORY_WEIGHTS = [0.20, 0.20, 0.15, 0.10, 0.10, 0.10, 0.05, 0.05, 0.05]

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
CANCEL_REASON_WEIGHTS = [
    0.15,
    0.15,
    0.12,
    0.10,
    0.10,
    0.08,
    0.07,
    0.06,
    0.05,
    0.04,
    0.03,
    0.02,
    0.02,
    0.01,
]

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
CESSATION_REASON_WEIGHTS = [
    0.15,
    0.12,
    0.10,
    0.10,
    0.08,
    0.08,
    0.07,
    0.07,
    0.05,
    0.05,
    0.04,
    0.03,
    0.03,
    0.02,
    0.01,
]


def _extract_prior_data(
    prior: Dict[str, Any],
) -> Tuple[
    pl.DataFrame | None,
    pl.DataFrame | None,
    pl.DataFrame | None,
    pl.DataFrame | None,
    pl.DataFrame | None,
]:
    """Extract dependent tables from prior runs.

    Returns a 5-tuple: Company, Person, Interactions, Person Company Role, Products.
    Missing tables are returned as None to keep the generator robust to ordering.
    """
    company_df = prior.get("Company")
    person_df = prior.get("Person")
    interaction_df = prior.get("Interactions")
    person_company_role_df = prior.get("Person Company Role")
    product_df = prior.get("Products")
    return company_df, person_df, interaction_df, person_company_role_df, product_df


def _generate_basic_order_data(
    n: int,
) -> Tuple[List[str], List[datetime], List[datetime], List[float]]:
    ids = make_ids(n, "ORD")
    order_dates = [random_date() for _ in ids]
    delivery_dates = [od + timedelta(days=fake.random_int(min=1, max=30)) for od in order_dates]
    order_amounts = [round(fake.random.uniform(100, 10000), 2) for _ in ids]
    return ids, order_dates, delivery_dates, order_amounts


def _create_company_person_map(
    company_ids: List[str],
    person_ids: List[str],
    interaction_df: Optional[pl.DataFrame] = None,
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """Build coarse mappings (company -> persons, person -> companies).

    NOTE: since you're moving to Person having a direct company reference,
    the authoritative mapping will be enforced later in a lazy join.
    This helper remains to pick plausible contacts for orders initially.
    """
    company_person_map: Dict[str, List[str]] = {}
    person_company_map: Dict[str, List[str]] = {}

    # If we have interactions, link interacted person/company
    if (
        interaction_df is not None
        and "interacted_company_id" in interaction_df.columns
        and "interacted_person_id" in interaction_df.columns
    ):
        for row in interaction_df.iter_rows(named=True):
            cid = row.get("interacted_company_id")
            pid = row.get("interacted_person_id")
            if cid and pid:
                company_person_map.setdefault(cid, [])
                if pid not in company_person_map[cid]:
                    company_person_map[cid].append(pid)
                person_company_map.setdefault(pid, [])
                if cid not in person_company_map[pid]:
                    person_company_map[pid].append(cid)

    # If no interactions, just create a light random mapping
    if not company_person_map and company_ids and person_ids:
        for cid in company_ids:
            k = fake.random_int(min=1, max=min(5, len(person_ids)))
            selected = fake.random.sample(person_ids, k)
            company_person_map[cid] = selected
            for pid in selected:
                person_company_map.setdefault(pid, []).append(cid)

    return company_person_map, person_company_map


def _assign_companies_to_orders(company_ids: List[str], ids: List[str]) -> List[str]:
    order_companies = []
    for _ in ids:
        order_companies.append(fake.random.choice(company_ids) if company_ids else fake.company())
    return order_companies


def _build_interaction_based_map(interaction_df: Optional[pl.DataFrame]) -> Dict[str, List[str]]:
    interaction_based: Dict[str, List[str]] = {}
    if (
        interaction_df is not None
        and "interacted_company_id" in interaction_df.columns
        and "interacted_person_id" in interaction_df.columns
    ):
        for row in interaction_df.iter_rows(named=True):
            cid = row.get("interacted_company_id")
            pid = row.get("interacted_person_id")
            if cid and pid:
                interaction_based.setdefault(cid, [])
                if pid not in interaction_based[cid]:
                    interaction_based[cid].append(pid)
    return interaction_based


def _select_contact_for_company(
    company: str,
    company_person_map: Dict[str, List[str]],
    interaction_based_company_person_map: Dict[str, List[str]],
) -> Optional[str]:
    """Select a contact candidate for a company, needs improvement."""
    # Fake company label → generate a fake contact name
    if isinstance(company, str) and not company.startswith("CO"):
        raise ValueError(f"Invalid company label: {company}")

    # Real company: prefer someone who interacted
    if interaction_based_company_person_map.get(company):
        return fake.random.choice(interaction_based_company_person_map[company])

    # Otherwise any person mapped to that company
    if company_person_map.get(company):
        return fake.random.choice(company_person_map[company])

    return None


def _create_company_person_relationships(
    company_df: Optional[pl.DataFrame],
    person_df: Optional[pl.DataFrame],
    person_company_role_df: Optional[pl.DataFrame],
    ids: List[str],
    interaction_df: Optional[pl.DataFrame] = None,
) -> Tuple[
    List[str], List[str], Dict[str, List[str]], Dict[str, List[str]], List[str], List[str | None]
]:
    company_ids: List[str] = []
    person_ids: List[str] = []

    if company_df is not None and "company_id" in company_df.columns:
        company_ids = company_df["company_id"].to_list()
    if person_df is not None and "person_id" in person_df.columns:
        person_ids = person_df["person_id"].to_list()

    company_person_map, person_company_map = _create_company_person_map(
        company_ids, person_ids, interaction_df
    )
    order_companies = _assign_companies_to_orders(company_ids, ids)
    interaction_based_company_person_map = _build_interaction_based_map(interaction_df)

    order_contacts: List[Optional[str]] = []
    for company in order_companies:
        order_contacts.append(
            _select_contact_for_company(
                company, company_person_map, interaction_based_company_person_map
            )
        )

    return (
        company_ids,
        person_ids,
        company_person_map,
        person_company_map,
        order_companies,
        order_contacts,
    )


def _process_interaction_data(
    interaction_df: Optional[pl.DataFrame],
) -> Tuple[Dict[str, List[str]], Dict[str, datetime]]:
    """Produce maps for causal interaction selection."""
    company_interactions_map: Dict[str, List[str]] = {}
    interaction_dates_map: Dict[str, datetime] = {}

    if interaction_df is not None and "interaction_id" in interaction_df.columns:
        # robustly pick a date column
        date_col = (
            "date"
            if "date" in interaction_df.columns
            else ("interaction_date" if "interaction_date" in interaction_df.columns else None)
        )
        if date_col is not None:
            for row in interaction_df.iter_rows(named=True):
                iid = row.get("interaction_id")
                cid = row.get("interacted_company_id")
                d = row.get(date_col)
                if iid and d:
                    interaction_dates_map[iid] = d
                    if cid:
                        company_interactions_map.setdefault(cid, []).append(iid)

    return company_interactions_map, interaction_dates_map


def _create_order_company_mappings(
    ids: List[str], order_dates: List[datetime], order_companies: List[str]
) -> Dict[str, List[Tuple[str, datetime]]]:
    order_data = list(zip(ids, order_dates, order_companies))
    order_data.sort(key=lambda x: x[1])

    company_orders_map: Dict[str, List[Tuple[str, datetime]]] = {}
    for order_id, order_date, company in order_data:
        company_orders_map.setdefault(company, []).append((order_id, order_date))
    return company_orders_map


def _build_orders_dataframe(data: OrderData) -> pl.DataFrame:
    """Build the final orders frame (pre-hardening)."""
    # Guard: if no products provided, make a synthetic list
    product_ids = (
        data.order_product_ids if data.order_product_ids else [f"PRD{fake.random_int(1, 9999):07d}"]
    )

    df = pl.DataFrame(
        {
            "order_id": data.ids,
            "name": [f"Order {i}" for i in data.ids],
            "company_id": data.order_companies,
            "product_id": weighted_sample(product_ids, n=data.n),
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
            ],
            "initial_contract_value": [round(amount * 1.5, 2) for amount in data.order_amounts],
            "initial_contract_value_gross_margin": [
                round(amount * 0.4 * 1.5, 2) for amount in data.order_amounts
            ],
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
            "person_id": data.order_contacts,
            "previous_order_id": [
                _find_previous_order(
                    order_id,
                    order_date,
                    company,
                    data.company_orders_map,
                    data.previous_order_probability,
                )
                for order_id, order_date, company in zip(
                    data.ids, data.order_dates, data.order_companies
                )
            ],
            "related_opportunity_id": [
                (
                    f"OPP{fake.random_int(min=1, max=9999):07d}"
                    if fake.random.random() < data.related_opportunity_probability
                    else None
                )
                for _ in data.ids
            ],
            "causal_interaction_id": [
                _find_causal_interaction(
                    order_date,
                    company,
                    data.company_interactions_map,
                    data.interaction_dates_map,
                    data.causal_interaction_probability,
                )
                for order_date, company in zip(data.order_dates, data.order_companies)
            ],
        }
    )

    # Derived/renamed fields to align with downstream spreadsheet/tests
    df = df.with_columns(
        [
            pl.col("date_completed").alias("outcomedate"),
            pl.col("transaction_channel").alias("saleschannel"),
            pl.Series("valuedeltas", [round(fake.random.uniform(-0.2, 0.2), 4) for _ in data.ids]),
            pl.Series(
                "valuedeltaswithretention",
                [
                    round(v * fake.random.uniform(0.9, 1.1), 4)
                    for v in [fake.random.uniform(-0.2, 0.2) for _ in data.ids]
                ],
            ),
            pl.Series("arpudelta", [round(fake.random.uniform(-10.0, 10.0), 2) for _ in data.ids]),
            pl.Series(
                "renewalquantitydifference", [fake.random_int(min=-5, max=5) for _ in data.ids]
            ),
            pl.Series(
                "cessetionreasongroup",
                weighted_sample(
                    ["Contract", "Commercial", "Service", "Migration", "Business Change"],
                    [0.3, 0.25, 0.2, 0.15, 0.1],
                    data.n,
                ),
            ),
            pl.col("cessetion_reason").alias("cessetionreasonsubgroup"),
            pl.Series(
                "sourcetable",
                weighted_sample(
                    ["SFDC_ORDER", "LEGACY_ORDER", "MANUAL_LOAD"], [0.7, 0.2, 0.1], data.n
                ),
            ),
            pl.Series(
                "sourceid", [f"SRC-{fake.random_int(min=100000, max=999999)}" for _ in data.ids]
            ),
            pl.Series(
                "sourceidfield",
                weighted_sample(
                    ["Salesforce OrderId", "LegacyOrderId", "ManualId"], [0.7, 0.2, 0.1], data.n
                ),
            ),
        ]
    )

    # Remove transient fields
    return df.drop(["transaction_channel", "cessetion_reason"])


def _harden_person_company_consistency(
    orders_df: pl.DataFrame,
    person_df: Optional[pl.DataFrame],
) -> pl.DataFrame:
    """Ensure person/company consistency.

    Rules:
    1) If company_id is NULL and person_id has a company in Person → fill company_id from Person.
    2) If both company_id and person_id exist, but Person.company_id != company_id → NULL-out person_id.

    Implemented lazily to avoid Python loops.
    """
    if person_df is None or not {"person_id", "company_id"} <= set(person_df.columns):
        return orders_df

    # Prepare a tiny person->company projection to join
    person_comp = person_df.select(
        pl.col("person_id").cast(pl.String),
        pl.col("company_id").cast(pl.String).alias("person_company_id"),
    )

    return (
        orders_df.lazy()
        .with_columns(
            pl.col("person_id").cast(pl.String),
            pl.col("company_id").cast(pl.String),
        )
        .join(person_comp.lazy(), on="person_id", how="left")
        .with_columns(
            # If order has no company but person has one → fill it
            pl.when(pl.col("company_id").is_null() & pl.col("person_company_id").is_not_null())
            .then(pl.col("person_company_id"))
            .otherwise(pl.col("company_id"))
            .alias("company_id"),
        )
        .with_columns(
            # If both exist and disagree → NULL person_id to avoid a false link
            pl.when(
                pl.col("person_id").is_not_null()
                & pl.col("company_id").is_not_null()
                & (pl.col("person_company_id").is_not_null())
                & (pl.col("person_company_id") != pl.col("company_id"))
            )
            .then(pl.lit(None, dtype=pl.String))
            .otherwise(pl.col("person_id"))
            .alias("person_id")
        )
        .drop("person_company_id")
        .collect()
    )


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of order data."""
    prior = kwargs.get("prior", {})

    company_df, person_df, interaction_df, person_company_role_df, product_df = _extract_prior_data(
        prior
    )
    ids, order_dates, delivery_dates, order_amounts = _generate_basic_order_data(n)

    ceased_date_probability = 0.2
    previous_order_probability = 0.3
    related_opportunity_probability = 0.5
    causal_interaction_probability = 0.4

    (
        company_ids,
        person_ids,
        company_person_map,
        person_company_map,
        order_companies,
        order_contacts,
    ) = _create_company_person_relationships(
        company_df, person_df, person_company_role_df, ids, interaction_df
    )

    company_interactions_map, interaction_dates_map = _process_interaction_data(interaction_df)
    company_orders_map = _create_order_company_mappings(ids, order_dates, order_companies)

    # Products list
    order_product_ids = (
        product_df.select("product_id").to_series().to_list()
        if (product_df is not None and "product_id" in product_df.columns)
        else []
    )

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
        order_product_ids=order_product_ids,
    )

    df = _build_orders_dataframe(order_data)
    return _harden_person_company_consistency(df, person_df)
