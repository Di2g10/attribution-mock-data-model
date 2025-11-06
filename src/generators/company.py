"""Contains a function to generate company data."""

from __future__ import annotations

from math import floor
from typing import Any

import numpy as np
import polars as pl

from ..random_utils import (
    fake,
    generate_mapped_values,
    make_ids,
    make_ids_with_duplicates,
    weighted_sample,
)

__all__ = ["generate"]

from enum import StrEnum


class CompanyField(StrEnum):
    """Enumerates all output columns for the Company generator, aligned to spreadsheet naming (snake_case)."""

    company_id = "company_id"
    parent_company_id = "parent_company_id"
    company_business_type = "company_business_type"
    company_business_start_year_number = "company_business_start_year_number"
    company_number_of_sites_count = "company_number_of_sites_count"
    company_trading_status = "company_trading_status"
    company_territory_name = "company_territory_name"
    company_sector_name = "company_sector_name"
    sic_code = "sic_code"
    billing_state_name = "billing_state_name"
    company_old_market_channel_code = "company_old_market_channel_code"
    company_active_ind = "company_active_ind"
    soho_marketing_cohort_code = "soho_marketing_cohort_code"
    soho_marketing_promotion_code = "soho_marketing_promotion_code"
    deleted_flag = "deleted_flag"
    company_status = "company_status"
    billing_country_name = "billing_country_name"
    billing_street_name = "billing_street_name"
    bt_customer_ind = "bt_customer_ind"
    company_registered_post_code = "company_registered_post_code"
    company_live_sites_count = "company_live_sites_count"
    company_overall_suppression_ind = "company_overall_suppression_ind"
    billing_postal_code = "billing_postal_code"
    sales_person_id = "sales_person_id"
    company_registered_country_name = "company_registered_country_name"
    annual_revenue_amount = "annual_revenue_amount"
    website_name = "website_name"
    company_name = "company_name"
    company_market_channel_code = "company_market_channel_code"
    source_id = "source_id"
    billing_city_name = "billing_city_name"
    employees_count = "employees_count"
    company_trading_unit_code = "company_trading_unit_code"
    source_id_field = "source_id_field"
    company_old_trading_unit_code = "company_old_trading_unit_code"
    company_death_reason_desc = "company_death_reason_desc"
    company_aic_code = "company_aic_code"
    industry_name = "industry_name"
    sales_account_id = "sales_account_id"
    source_table = "source_table"
    soho_month_cohort_code = "soho_month_cohort_code"
    ee_customer_ind = "ee_customer_ind"


# Weights for verticals (higher weight = more common)
BT_VERTICAL_WEIGHTS: dict[str, float] = {
    "Financial Services": 0.1081,
    "Healthcare": 0.0901,
    "Manufacturing": 0.0721,
    "Retail (Enterprise)": 0.0631,
    "Public Sector & Non-Profit": 0.0631,
    "Professional Services": 0.0631,
    "Education": 0.0541,
    "Technology": 0.0450,
    "Media & Entertainment": 0.0450,
    "Energy & Utilities": 0.0360,
    "Transport & Automotive": 0.0360,
    "Logistics & Distribution": 0.0360,
    "Construction & Trades": 0.0450,
    "Telecommunications": 0.0270,
    "Hospitality & Tourism": 0.0270,
    "Pharmaceuticals": 0.0180,
    "Insurance": 0.0180,
    "Agriculture & Rural": 0.0180,
    "Creative & Digital Agencies": 0.0180,
    "Sports & Leisure": 0.0180,
    "Micro-Retail & Local Services": 0.0541,
    "Food & Beverage": 0.0360,
}
# Define a small epsilon value for floating-point comparison
EPSILON = 1e-6

# quick sanity-check
try:
    assert abs(sum(BT_VERTICAL_WEIGHTS.values()) - 1.0) < EPSILON
except AssertionError:
    print(f"BT_VERTICAL_WEIGHTS: {BT_VERTICAL_WEIGHTS}")


BT_VERTICALS_TO_INDUSTRIES: dict[str, list[str]] = {
    "Technology": [
        "Customer-Data & Personalisation (CDP/RT-CDP) Software",
        "Low-Code Application Platforms",
        "IoT Device Security",
        "Blockchain Infrastructure Services",
        "UK SaaS Scale-Ups (≤250 staff)",
    ],
    "Healthcare": [
        "AI-Driven Medical Imaging Diagnostics",
        "GP Surgery Practice Management Systems",
        "Care-Home Tele-health Providers",
        "Independent Pharmacies (≤10 branches)",
    ],
    "Financial Services": [
        "RegTech Compliance Automation Platforms",
        "Peer-to-Peer Lending Marketplaces",
        "Local Credit Unions & Building Societies",
        "Independent Insurance Brokers",
    ],
    "Manufacturing": [
        "Additive (3-D) Printing Equipment",
        "Digital-Twin Simulation Software",
        "SME Precision-Engineering Workshops",
        "Artisan Food Producers & Packaging Plants",
    ],
    "Retail (Enterprise)": [
        "High-Street Chain Fashion Stores",
        "Omnichannel Inventory Optimisation SaaS",
        "In-Store Computer-Vision Checkout",
        "Marketplace-First DTC Brands",
    ],
    "Telecommunications": [
        "5G Network-Slice Orchestration",
        "Edge-Compute Content Delivery",
        "UK Alt-Net Fibre Providers",
        "Satellite Broadband Resellers",
    ],
    "Energy & Utilities": [
        "Utility-Scale Battery Storage Providers",
        "Renewable PPA Marketplaces",
        "Smart-Grid Demand-Response Platforms",
        "Rural Community Energy Co-ops",
    ],
    "Education": [
        "MOOC-Based Micro-Credential Platforms",
        "K-12 Learning-Analytics Dashboards",
        "Vocational VR/AR Training Studios",
        "Local Tuition Centres & Tutoring Apps",
    ],
    "Transport & Automotive": [
        "Autonomous Fleet Management SaaS",
        "Last-Mile e-Bike Logistics Start-ups",
        "Independent EV Charging-Point Installers",
        "Urban Micromobility Rental Schemes",
    ],
    "Media & Entertainment": [
        "Programmatic CTV Ad Exchanges",
        "Podcast Ad-Insertion Tech",
        "Metaverse Content Studios",
        "Regional Radio & Community TV Stations",
    ],
    "Micro-Retail & Local Services": [
        "Corner Shops & Newsagents",
        "Independent Florists",
        "Mobile Phone Repair Kiosks",
        "Beauty Salons & Barber Shops",
    ],
    "Food & Beverage": [
        "Neighbourhood Cafés & Bakeries",
        "Family-Owned Restaurants",
        "Craft Breweries & Taprooms",
        "Street-Food Vendors",
    ],
    "Hospitality & Tourism": [
        "Boutique Hotels (<50 rooms)",
        "Holiday Parks & Caravan Sites",
        "Local Tour Operators",
        "Community-Run Museums & Heritage Centres",
    ],
    "Pharmaceuticals": [
        "Contract Research Organisations (CROs)",
        "Generic Drug Manufacturers",
        "Biotechnology Scale-Ups",
        "Clinical-Trial Management Platforms",
        "Specialty Pharma (Orphan Drugs)",
        "Cold-Chain Pharma Logistics",
    ],
    "Insurance": [
        "InsurTech Comparison Aggregators",
        "Specialty Lines (Pet, Cyber, Travel)",
        "Mutual & Friendly Societies",
        "Claims-Processing BPO Providers",
        "Reinsurance Brokers",
        "Usage-Based (Telematics) Auto Cover",
    ],
    "Public Sector & Non-Profit": [
        "Town & Parish Councils",
        "Charity Shops & Fund-Raising HQs",
        "Social Housing Associations",
        "Volunteer-Led Sports Clubs",
    ],
    "Construction & Trades": [
        "Small Electrical & Plumbing Contractors",
        "Regional House-Builders",
        "Specialist Heritage Restoration Firms",
        "Scaffolding & Plant Hire SMEs",
    ],
    "Professional Services": [
        "High-Street Solicitors",
        "Local Accountancy Practices",
        "Independent Financial Advisers",
        "Estate & Letting Agents",
    ],
    "Logistics & Distribution": [
        "Regional Hauliers (1-50 HGVs)",
        "Same-Day Courier Franchises",
        "Third-Party Fulfilment Warehouses",
        "Parcel-Shop Networks",
    ],
    "Agriculture & Rural": [
        "Arable & Livestock Family Farms",
        "Agritech Sensor Suppliers",
        "Farm Shops & Pick-Your-Own",
        "Rural Broadband Community Projects",
    ],
    "Creative & Digital Agencies": [
        "Independent Graphic-Design Studios",
        "Video Production Companies",
        "Local Web-Dev & SEO Boutiques",
        "Experiential Event Agencies",
    ],
    "Sports & Leisure": [
        "Gyms & Fitness Studios (<10 sites)",
        "Amateur Football & Rugby Clubs",
        "Indoor Climbing Centres",
        "Golf-Course Pro Shops",
    ],
}


# Function removed as it was unused


def generate(n: int, **kwargs: Any) -> pl.DataFrame:  # registry/prior unused yet  # noqa: PLR0915
    """Generate a DataFrame of company data.

    Performance optimizations:
    - Uses NumPy's vectorized random operations for better performance with large datasets
    - Pre-generates and reuses values instead of generating them on-demand
    - Limits the number of expensive fake.city() calls by creating a reusable pool
    """
    # Use NumPy's RNG for better performance with vectorized operations
    rng = np.random.default_rng()

    ids = make_ids(n, "CO")

    # Generate verticals using weighted_sample (already optimized for batch operations)
    verticals = weighted_sample(
        list(BT_VERTICALS_TO_INDUSTRIES.keys()), list(BT_VERTICAL_WEIGHTS.values()), n
    )

    # PERFORMANCE OPTIMIZATION: Use generate_mapped_values helper function
    # This function efficiently maps parent categories (verticals) to child values (industries)
    # using NumPy's vectorized operations and pre-generation of values
    industries = generate_mapped_values(
        parent_values=verticals, mapping_dict=BT_VERTICALS_TO_INDUSTRIES
    )

    # PERFORMANCE OPTIMIZATION: Limit expensive fake.city() calls
    # Instead of generating n cities, we create a smaller pool and sample from it
    # This significantly reduces the number of calls to the expensive fake.city() function
    locations = [fake.city() for _ in range(min(1000, n))]  # Generate a pool of locations
    location_indices = rng.integers(0, len(locations), size=n)
    selected_locations = [locations[i] for i in location_indices]

    # Helper pools and mappings for additional fields
    # BT marketing channels are based on company size bands
    size_code_map: dict[str, str] = {
        "SMB": "SMB",
        "CPS": "CPS",
        "Global": "GLB",
        "Wholesale": "WHL",
    }
    wholesale_sic: set[str] = {"61100", "61200"}  # telco wholesale-like activities

    uk_territories = ["England", "Scotland", "Wales", "Northern Ireland"]
    uk_regions = [
        "Greater London",
        "West Midlands",
        "Greater Manchester",
        "West Yorkshire",
        "Glasgow City",
        "Cardiff",
        "Belfast",
        "Surrey",
        "Hampshire",
        "Essex",
    ]

    company_types = ["Limited", "PLC", "Sole Trader", "Partnership", "LLP"]
    company_statuses = ["Prospect", "Customer", "Former Customer", "Lead"]
    trading_statuses = ["Trading", "Dormant", "In Administration", "Liquidation"]
    death_reasons = ["Dissolved", "Bankruptcy", "Merged", "Acquired"]

    # A small pool of common UK SIC codes (as strings)
    sic_codes = [
        "62012",  # Business and domestic software development
        "61100",  # Wired telecommunications activities
        "61200",  # Wireless telecommunications activities
        "47910",  # Retail sale via mail order houses or via Internet
        "82990",  # Other business support service activities n.e.c.
        "70229",  # Management consultancy activities
        "63110",  # Data processing, hosting and related activities
        "47190",  # Other retail sale in non-specialised stores
        "62030",  # Computer facilities management activities
        "64202",  # Activities of production holding companies
    ]

    def make_uk_postcode(size: int) -> list[str]:
        """Generate UK-like postcodes (not guaranteed valid, but realistic pattern)."""
        letters = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        outward_second_digit_prob = 0.5  # probability for outward code to have single digit

        def one() -> str:
            a = rng.choice(letters)
            b = rng.choice(letters)
            num1 = rng.integers(0, 10)
            # Optional second digit in outward code
            if rng.random() < outward_second_digit_prob:
                outward = f"{a}{num1}"
            else:
                num2 = rng.integers(0, 10)
                outward = f"{a}{b}{num1}{num2}"
            inward = f"{rng.integers(0,10)}{rng.choice(letters)}{rng.choice(letters)}"
            return f"{outward} {inward}"

        return [one() for _ in range(size)]

    # Derive fields that depend on earlier ones

    business_start_year = rng.integers(1950, 2025, size=n)
    number_of_sites = rng.integers(1, 11, size=n)  # skew small later
    # livesites cannot exceed number_of_sites
    live_sites = np.minimum(number_of_sites, rng.integers(0, 11, size=n))

    territory = weighted_sample(uk_territories, [0.84, 0.08, 0.05, 0.03], n)
    sector_name = verticals  # align sector to our Vertical for simplicity

    sic = weighted_sample(sic_codes, [0.12, 0.12, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.08, 0.08], n)

    billing_country = ["United Kingdom"] * n
    billing_state = weighted_sample(
        uk_regions, [0.24, 0.1, 0.1, 0.08, 0.06, 0.06, 0.06, 0.1, 0.1, 0.1], n
    )
    billing_city = selected_locations
    billing_street = [fake.street_name() for _ in range(n)]
    billing_postcode = make_uk_postcode(n)

    # Registered country/postcode can differ from billing
    registered_country = ["United Kingdom"] * n
    registered_postcode = make_uk_postcode(n)

    company_business_type = weighted_sample(company_types, [0.6, 0.05, 0.2, 0.1, 0.05], n)
    trading_status = weighted_sample(trading_statuses, [0.88, 0.07, 0.03, 0.02], n)
    active_ind = ["Y" if s == "Trading" else "N" for s in trading_status]

    deleted_flag = weighted_sample(["N", "Y"], [0.98, 0.02], n)
    overall_suppression = weighted_sample(["N", "Y"], [0.97, 0.03], n)
    bt_customer = weighted_sample(["Y", "N"], [0.7, 0.3], n)
    ee_customer = weighted_sample(["N", "Y"], [0.8, 0.2], n)

    # Cohort codes and promos
    def make_month_code(i: int) -> str:
        year = int(business_start_year[i])
        # Cohort month anchored within 1..12 but give recent skew
        month = int(rng.integers(1, 13))
        return f"{year:04d}-{month:02d}"

    soho_month_cohort = [make_month_code(i) for i in range(n)]
    soho_marketing_cohort = [f"SOHO-{c}" for c in soho_month_cohort]
    soho_promo = [f"PROMO-{rng.integers(100, 1000):03d}" for _ in range(n)]

    # IDs
    salesperson_pool = make_ids(max(1, floor(n / 10)), "SP")
    salesperson_id = make_ids_with_duplicates(salesperson_pool, n)
    sales_account_pool = make_ids(max(1, floor(n / 8)), "SA")
    sales_account_id = make_ids_with_duplicates(sales_account_pool, n)

    # Source fields
    source_table = weighted_sample(
        ["SFDC_ACCOUNT", "LEGACY_ACCOUNT", "MANUAL_LOAD"], [0.7, 0.2, 0.1], n
    )
    source_id = [f"SRC-{rng.integers(100000, 999999)}" for _ in range(n)]
    source_id_field = weighted_sample(
        ["Salesforce AccountId", "LegacyAccountId", "ManualId"], [0.7, 0.2, 0.1], n
    )

    # Revenue and employees (keep SOHO-friendly, skew small)
    annual_revenue = [
        int(x) for x in rng.lognormal(mean=12, sigma=1.0, size=n)
    ]  # ~ GBP e^12 ~ 162k
    employees = [int(max(1, min(5000, e))) for e in rng.lognormal(mean=3.0, sigma=1.0, size=n)]

    # ── Derive BT size band and map to Marketing Channel ─────────────────────
    smb_max = 250
    cps_max = 999
    wholesale_probability = 0.25

    def _derive_size_band(i: int) -> str:
        """Return BT size band based on employees, with Wholesale overrides.

        :param i: Row index
        :returns: One of SIZE_BANDS ("SMB", "CPS", "Global", "Wholesale").
        """
        emp = employees[i]
        band = "SMB" if emp <= smb_max else ("CPS" if emp <= cps_max else "Global")
        # Override to Wholesale for some Telecoms/Wholesale-like SICs
        try:
            if (
                sic[i] in wholesale_sic or verticals[i] == "Telecommunications"
            ) and rng.random() < wholesale_probability:
                band = "Wholesale"
        except Exception:
            # Be robust if indices misalign; keep computed band
            pass
        return band

    size_bands = [_derive_size_band(i) for i in range(n)]
    # market_channels = size_bands
    market_channel_codes = [size_code_map[b] for b in size_bands]

    # Historical/old market channel code (may differ from current)
    old_market_channel = weighted_sample(list(size_code_map.values()), [0.55, 0.2, 0.2, 0.05], n)

    trading_unit_codes = ["BU1", "BU2", "BU3", "BU4"]
    trading_unit = weighted_sample(trading_unit_codes, [0.4, 0.3, 0.2, 0.1], n)
    old_trading_unit = weighted_sample(trading_unit_codes, [0.3, 0.3, 0.2, 0.2], n)

    company_ai_code = [f"AIC{rng.integers(1000, 9999)}" for _ in range(n)]

    # Company website and names
    website = [fake.domain_name() for _ in range(n)]

    # Status
    status = weighted_sample(company_statuses, [0.15, 0.6, 0.1, 0.15], n)

    # Death reason only when not active; else empty string
    death_reason = [
        death_reasons[rng.integers(0, len(death_reasons))] if a == "N" else "" for a in active_ind
    ]

    df = pl.DataFrame(
        {
            CompanyField.company_id: ids,
            CompanyField.parent_company_id: make_ids_with_duplicates(ids, n, 0.8),
            CompanyField.company_business_type: company_business_type,
            # Newly added / existing fields mapped to spreadsheet-aligned snake_case:
            CompanyField.company_business_start_year_number: business_start_year.tolist(),
            CompanyField.company_number_of_sites_count: number_of_sites.tolist(),
            CompanyField.company_trading_status: trading_status,
            CompanyField.company_territory_name: territory,
            CompanyField.company_sector_name: sector_name,
            CompanyField.sic_code: sic,
            CompanyField.billing_state_name: billing_state,
            CompanyField.company_old_market_channel_code: old_market_channel,
            CompanyField.company_active_ind: active_ind,
            CompanyField.soho_marketing_cohort_code: soho_marketing_cohort,
            CompanyField.soho_marketing_promotion_code: soho_promo,
            CompanyField.deleted_flag: deleted_flag,
            CompanyField.company_status: status,
            CompanyField.billing_country_name: billing_country,
            CompanyField.billing_street_name: billing_street,
            CompanyField.bt_customer_ind: bt_customer,
            CompanyField.company_registered_post_code: registered_postcode,
            CompanyField.company_live_sites_count: live_sites.tolist(),
            CompanyField.company_overall_suppression_ind: overall_suppression,
            CompanyField.billing_postal_code: billing_postcode,
            CompanyField.sales_person_id: salesperson_id,
            CompanyField.company_registered_country_name: registered_country,
            CompanyField.annual_revenue_amount: annual_revenue,
            CompanyField.website_name: website,
            CompanyField.company_name: [fake.company() for _ in range(n)],
            CompanyField.company_market_channel_code: market_channel_codes,
            CompanyField.source_id: source_id,
            CompanyField.billing_city_name: billing_city,
            CompanyField.employees_count: employees,
            CompanyField.company_trading_unit_code: trading_unit,
            CompanyField.source_id_field: source_id_field,
            CompanyField.company_old_trading_unit_code: old_trading_unit,
            CompanyField.company_death_reason_desc: death_reason,
            CompanyField.company_aic_code: company_ai_code,
            CompanyField.industry_name: industries,
            CompanyField.sales_account_id: sales_account_id,
            CompanyField.source_table: source_table,
            CompanyField.soho_month_cohort_code: soho_month_cohort,
            CompanyField.ee_customer_ind: ee_customer,
        }
    )
    # Also drop Owner_ID textual variant to avoid 'ownerid' extra after normalisation
    # Keep Owner_ID as it's part of spreadsheet? If flagged as extra, remove here
    drop_extras = {
        "name",
        "industry",
        "Owner_ID",
        "Vertical",
        "location",
        "Company Market Channel",
        "companytype",
    }
    keep_cols = [c for c in df.columns if c not in drop_extras]
    return df.select(keep_cols)
