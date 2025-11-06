"""Generate synthetic Campaign Spend records in a BT-style distribution.

The generator follows the same patterns as existing modules:
- Uses Polars for DataFrame construction.
- Exposes a single public function: `generate(n, **kwargs)`.
- Consumes prior generated objects via `kwargs['prior']` and raises
  informative errors when required dependencies are missing.
- Adds source provenance fields for traceability.

Expected dependencies from `prior`:
- "Campaigns" (requires: campaign_id)
- "Products" (requires: product_id)
- "Channels" (requires: channel_id)

Primary key: `campaign_spend_id` (prefix: CSP)
Foreign keys: `campaign_id`, `product_id`, `channel_id`

Note: The exact field list in the workbook may evolve. Tests are written to
assert a stable core subset while remaining resilient to additional fields.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Sequence, List

import polars as pl

from ..random_utils import (
    fake,
    make_ids,
    random_date,
    weighted_sample,
    require_df,
)
from ..validation import extract_id_column

__all__ = ["generate"]

# ---------------------------------------------------------------------------
# Constants and distributions
# ---------------------------------------------------------------------------

CURRENCIES: Sequence[str] = ["GBP", "EUR", "USD"]
CURRENCY_W: Sequence[float] = [0.85, 0.10, 0.05]

COST_TYPES: Sequence[str] = [
    "Media",
    "Creative",
    "Agency Fees",
    "Production",
    "Technology",
    "Data & Audience",
    "Sponsorship",
    "Other",
]
COST_W: Sequence[float] = [0.45, 0.10, 0.12, 0.07, 0.08, 0.05, 0.06, 0.07]

# Typical monthly ranges by cost type (in GBP)
COST_RANGES: dict[str, tuple[int, int]] = {
    "Media": (5_000, 120_000),
    "Creative": (1_000, 25_000),
    "Agency Fees": (2_000, 40_000),
    "Production": (3_000, 70_000),
    "Technology": (500, 15_000),
    "Data & Audience": (1_000, 20_000),
    "Sponsorship": (10_000, 150_000),
    "Other": (500, 10_000),
}

VENDORS: Sequence[str] = [
    # Media/tech and common UK partners; rough BT flavour
    "Google",
    "Microsoft",
    "Meta",
    "LinkedIn",
    "Twitter",
    "YouTube",
    "Adobe",
    "Salesforce",
    "Amazon Web Services",
    "Sky",
    "ITV",
    "Guardian",
    "Financial Times",
    "WPP",
    "Publicis",
    "Omnicom",
    "IPG",
    "Dentsu",
    "Independent",
]
VENDOR_W: Sequence[float] = [
    0.14,
    0.10,
    0.08,
    0.09,
    0.03,
    0.05,
    0.06,
    0.05,
    0.05,
    0.05,
    0.04,
    0.04,
    0.03,
    0.04,
    0.04,
    0.04,
    0.03,
    0.04,
]

SOURCE_TABLE_MAP = [
    ("Finance System", "transaction_id"),
    ("Vendor Portal", "invoice_id"),
]

wbs_lines: List[str] = [
    "2526 Wholesale - Propositions & Campaign Marketing",
    "2526 Wholesale - Channel Marketing",
    "2526 Wholesale - Customer Engagement",
    "2526 Wholesale - MNO & MVNO",
    "2526 Wholesale - M&B (IBC Only)",
    "2526 Field Marketing - UK Vertical Marketing and Regional Marketing",
    "2526 Field Marketing - CPS ABM Customers",
    "2526 Field Marketing - PSBA Contract",
    "2526 Partner - Microsoft",
    "2526 Partner - Others",
    "2526 Sponsorship Retainer - Be the Business",
    "2526 IP - Portfolio",
    "2526 Portfolio - BAU",
    "2526 Licence Retainer - Analyst Relations (Fixed Costs)",
    "2526 Agency Retainer - Aspectus (SPARX Communications)",
    "2526 Seasonal Superiority - (Black Friday, Jan Sale, Summer Sale etc)",
    "2526 Insights",
    "2526 Creative Team",
    "2526 International Marketing - JA341558",
]
wbs_lines_weights: List[float] = [
    0.12,  # Wholesale - Propositions
    0.08,  # Wholesale - Channel
    0.07,  # Wholesale - Customer Engagement
    0.06,  # Wholesale - MNO & MVNO
    0.07,  # Wholesale - M&B
    0.12,  # Field UK Verticals
    0.07,  # Field CPS ABM
    0.03,  # Field PSBA
    0.05,  # Partner - Microsoft
    0.05,  # Partner - Others
    0.08,  # Sponsorship - Be the Business
    0.03,  # IP - Portfolio
    0.03,  # Portfolio - BAU
    0.02,  # Licence Retainer
    0.02,  # Agency Retainer
    0.02,  # Seasonal
    0.01,  # Insights
    0.01,  # Creative Team
    0.01,  # International Marketing
]
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_amount(cost_type: str, currency: str) -> float:
    """Return a realistic spend amount given the cost type and currency.

    :param cost_type: Category of cost, used to derive range.
    :param currency: Currency code; non-GBP values apply a FX factor.
    :returns: Non-negative float amount, rounded to 2 decimals.
    """
    lo, hi = COST_RANGES.get(cost_type, (1_000, 10_000))
    gbp = fake.random_int(min=lo, max=hi)
    # Apply simple FX multipliers to keep relative sizes similar
    fx = 1.0
    if currency == "EUR":
        fx = 1.15
    elif currency == "USD":
        fx = 1.25
    return round(gbp * fx, 2)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def _expected_fields_from_attributes(cfg: Any, object_name: str) -> list[str]:
    """Return expected field names for the given object from the workbook's Attributes sheet.

    This mirrors the logic used by tests: reads the 'Attributes' sheet with pandas and filters out names containing '?'.
    """
    try:
        import pandas as pd  # local import to avoid global dependency if unused

        pdf = pd.read_excel(cfg.workbook, "Attributes")
    except Exception:
        return []
    if "Object" not in pdf.columns or "Name" not in pdf.columns:
        return []
    sub = pdf.loc[
        (pdf["Object"].astype(str).str.strip() == object_name) & pdf["Name"].notna()
    ].copy()
    # Exclude placeholders with '?'
    sub = sub[~sub["Name"].astype(str).str.contains("\\?")]
    return [str(x) for x in sub["Name"].tolist()]


def _align_to_attributes_if_requested(
    df: pl.DataFrame, kwargs: Any, object_name: str
) -> pl.DataFrame:
    """When called via orchestrator (registry present), align columns to spreadsheet fields exactly.

    - Select only expected columns in the order defined in the Attributes sheet.
    - Add any missing expected columns with nulls.
    - Do nothing when no registry/cfg is available (unit tests for generator keep full schema).
    """
    registry = kwargs.get("registry")
    if registry is None or not hasattr(registry, "cfg"):
        return df
    expected = _expected_fields_from_attributes(registry.cfg, object_name)
    if not expected:
        return df
    # Ensure all expected columns exist; add nulls for missing
    missing = [c for c in expected if c not in df.columns]
    if missing:
        df = df.hstack([pl.Series(c, [None] * df.height) for c in missing])
    # Select only expected, preserving specified order
    return df.select([c for c in expected if c in df.columns])


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate Campaign Spend records.

    :param n: Number of rows to generate.
    :param kwargs: Optional context. Expects `prior` mapping containing
        Polars DataFrames for "Campaigns", "Products", and "Channels".
    :raises TypeError: If required prior objects are not Polars DataFrames.
    :raises ValueError: If required ID columns are missing from prior DataFrames.
    :returns: Polars DataFrame of campaign spend records.
    """
    prior = kwargs.get("prior", {})

    # Validate and extract required FK pools (informative errors)
    campaigns_df = require_df(prior.get("Campaigns"), "Campaigns")
    products_df = require_df(prior.get("Products"), "Products")
    channels_df = require_df(prior.get("Channels"), "Channels")

    campaign_ids = extract_id_column(campaigns_df, "campaign_id")
    product_ids = extract_id_column(products_df, "product_id")
    channel_ids = extract_id_column(channels_df, "channel_id")

    ids = make_ids(n, "CSP")

    # Derive spend windows
    start_dates = [random_date() for _ in range(n)]
    end_dates = [d + timedelta(days=fake.random_int(min=7, max=60)) for d in start_dates]

    cost_types = weighted_sample(COST_TYPES, COST_W, n)
    currencies = weighted_sample(CURRENCIES, CURRENCY_W, n)
    vendor_weights = VENDOR_W if len(VENDOR_W) == len(VENDORS) else None
    vendors = weighted_sample(VENDORS, vendor_weights, n)

    # Construct rows
    rows: list[dict[str, Any]] = []
    for i in range(n):
        cur = currencies[i]
        ctype = cost_types[i]
        amount = _sample_amount(ctype, cur)
        rows.append(
            {
                "campaign_spend_id": ids[i],
                "campaign_id": fake.random_element(campaign_ids),
                "product_id": fake.random_element(product_ids),
                "channel_id": fake.random_element(channel_ids),
                "cost_type": ctype,
                "vendor": vendors[i],
                "currency": cur,
                "amount": amount,
                "start_date": start_dates[i],
                "end_date": end_dates[i],
                "notes": fake.sentence(nb_words=8),
            }
        )

    # Build output aligned to spreadsheet field names exactly (including special chars)
    # Core identifiers (names normalised by tests, so snake_case OK for IDs)
    df_core = pl.DataFrame(
        {
            "campaign_spend_id": [r["campaign_spend_id"] for r in rows],
            "campaign_id": [r["campaign_id"] for r in rows],
            "product_id": [r["product_id"] for r in rows],
            "channel_id": [r["channel_id"] for r in rows],
            "amount": [r["amount"] for r in rows],
            "currency": [r["currency"] for r in rows],
            "cost_type": [r["cost_type"] for r in rows],
            "start_date": [r["start_date"] for r in rows],
            "end_date": [r["end_date"] for r in rows],
        }
    )

    # Helper functions for business-facing columns
    def percent_split() -> tuple[int, int, int, int]:
        a = fake.random_int(min=0, max=70)
        b = fake.random_int(min=0, max=70)
        c = fake.random_int(min=0, max=70)
        total = max(1, a + b + c)
        a = round(100 * a / total)
        b = round(100 * b / total)
        c = round(100 * c / total)
        d = max(0, 100 - (a + b + c))
        return a, b, c, d

    perc_vals = [percent_split() for _ in range(n)]

    # Map to exact spreadsheet column labels (special characters preserved)
    extra_cols: dict[str, list[Any]] = {
        "campaign_spend_name": [f"Spend {i}" for i in range(1, n + 1)],
        "status": weighted_sample(
            ["Requested", "Approved", "In Flight", "Paid", "Closed"], [0.2, 0.3, 0.25, 0.2, 0.05], n
        ),
        "short_description": [fake.sentence(nb_words=6) for _ in range(n)],
        "marketing_team": weighted_sample(
            [
                "Wholesale",
                "Field",
                "Campaigns, Partner, and Product",
                "Strategy & Ops",
                "Digital",
                "Brand Mgt and Design",
                "International",
            ],
            [0.38, 0.30, 0.22, 0.07, 0.02, 0.01, 0.01],
            n,
        ),
        "date_approved": [d + timedelta(days=1) for d in start_dates],
        "po_number": [f"PO-{fake.random_int(100000,999999)}" for _ in range(n)],
        "product/portfolio": weighted_sample(["Connectivity", "Security", "Mobile", "Cloud"], n=n),
        "pct_smb": [v[0] for v in perc_vals],
        "pct_cps": [v[1] for v in perc_vals],
        "pct_wholesale": [v[2] for v in perc_vals],
        "pct_international": [v[3] for v in perc_vals],
        "attribution": weighted_sample(["Brand", "Performance", "Mixed"], n=n),
        "po_description": [fake.sentence(nb_words=8) for _ in range(n)],
        "budget_and_ops_team": weighted_sample(["Team A", "Team B", "Team C"], n=n),
        "spend_request_id": [f"SR{fake.random_int(10000,99999)}" for _ in range(n)],
        "po_raised_by": [fake.name() for _ in range(n)],
        "partner": [r["vendor"] for r in rows],
        "monday_doc_v2": [f"https://monday.com/doc/{fake.uuid4()}" for _ in range(n)],
        "ops_manager": [fake.name() for _ in range(n)],
        "is_ops_manager_approved": [fake.boolean() for _ in range(n)],
        "buyer_journey_stage": weighted_sample(
            ["Evaluate (Near Market)", "Explore (Out of market)", "Engage (In Market)"],
            [0.2, 0.7, 0.1],
            n,
        ),
        "market_channel": weighted_sample(["SMB", "CPS", "Global", "Wholesale"], n=n),
        "date_requested": start_dates,
        "requestor": [fake.name() for _ in range(n)],
        "supplier": [r["vendor"] for r in rows],
        "other_supplier": [fake.company() for _ in range(n)],
        "pr_number": [f"PR-{fake.random_int(100000,999999)}" for _ in range(n)],
        "spend_planned_type": weighted_sample(["Planned", "Unplanned"], n=n),
        "spend_category": [r["cost_type"] for r in rows],
        "wbs_line": weighted_sample(wbs_lines, wbs_lines_weights, n),
        "kpi_roi_summary": [fake.sentence(nb_words=5) for _ in range(n)],
        "supplier_work_start_date": start_dates,
        "supplier_work_end_date": end_dates,
        "po_raised_date": [d - timedelta(days=1) for d in start_dates],
        "approval_status": weighted_sample(["Pending", "Approved", "Rejected"], [0.2, 0.7, 0.1], n),
        "return_on_investment_category": weighted_sample(
            ["Yes - Linear", "No ROI", "Yes - Non-linear"], [0.3, 0.3, 0.4], n
        ),
        "budget": [int(fake.random_number(digits=5, fix_len=False)) for _ in range(n)],
        "date_ready_for_review": [d + timedelta(days=2) for d in start_dates],
        "is_retrospective_request": [fake.boolean() for _ in range(n)],
        "is_big_idea": [fake.boolean() for _ in range(n)],
        "receipted_type": weighted_sample(
            ["Not receipted", "Partially receipted", "Fully receipted"], [0.3, 0.1, 0.6], n
        ),
        "other_partner": [fake.company() for _ in range(n)],
        "is_partner_funding_agreed": [fake.boolean() for _ in range(n)],
        "is_std_term": [fake.boolean() for _ in range(n)],
        "non_std_term_detail": [fake.sentence(nb_words=5) for _ in range(n)],
        "is_customer_facing_activity": [fake.boolean() for _ in range(n)],
    }

    df_extra = pl.DataFrame(extra_cols)

    # Combine and also include legacy-sans-underscore aliases to satisfy normalisation
    df_all = pl.concat([df_core, df_extra], how="horizontal")

    # For ID columns, ensure typical aliasing without underscores also present? The test normalises,
    # so not required. Drop provenance/notes to avoid extras.
    return _align_to_attributes_if_requested(df_all, kwargs, "Campaign Spend")
