"""Contains a function to generate campaign data."""

from __future__ import annotations

from typing import Any
from datetime import timedelta

import polars as pl

from ..random_utils import fake, make_ids, random_date, make_ids_with_duplicates, weighted_sample

__all__ = ["generate"]

# Constants for probability values
PARTNER_PROBABILITY = 0.5

# Campaign types with weights
CAMPAIGN_TYPES = [
    "Email",
    "Social Media",
    "Display",
    "Search",
    "Content Marketing",
    "Event",
    "Webinar",
    "Direct Mail",
    "Telemarketing",
    "Partner",
]

# Weights for campaign types (higher weight = more common)
CAMPAIGN_TYPE_WEIGHTS = [
    0.25,  # Email
    0.20,  # Social Media
    0.15,  # Display
    0.15,  # Search
    0.10,  # Content Marketing
    0.05,  # Event
    0.05,  # Webinar
    0.02,  # Direct Mail
    0.02,  # Telemarketing
    0.01,  # Partner
]

# Campaign status with weights
CAMPAIGN_STATUS = ["Active", "Completed", "Planned", "Paused", "Cancelled"]

# Weights for campaign status (higher weight = more common)
CAMPAIGN_STATUS_WEIGHTS = [
    0.40,  # Active
    0.30,  # Completed
    0.15,  # Planned
    0.10,  # Paused
    0.05,  # Cancelled
]

# BT products with weights
BT_PRODUCTS = [
    "BTnet",
    "BT Cloud",
    "BT Mobile",
    "BT Broadband",
    "BT Business",
    "BT Enterprise",
    "BT Wholesale",
    "BT Security",
    "BT Global",
    "BT Fibre",
    "BT Connect",
    "BT One",
]

# Weights for BT products (higher weight = more common)
BT_PRODUCT_WEIGHTS = [
    0.15,  # BTnet
    0.15,  # BT Cloud
    0.15,  # BT Mobile
    0.15,  # BT Broadband
    0.10,  # BT Business
    0.10,  # BT Enterprise
    0.05,  # BT Wholesale
    0.05,  # BT Security
    0.05,  # BT Global
    0.02,  # BT Fibre
    0.02,  # BT Connect
    0.01,  # BT One
]

# Campaign situations with weights
CAMPAIGN_SITUATIONS = [
    "acquisition",
    "retention",
    "upsell",
    "cross-sell",
    "awareness",
    "launch",
    "promotion",
    "reactivation",
    "loyalty",
    "winback",
]

# Weights for campaign situations (higher weight = more common)
CAMPAIGN_SITUATION_WEIGHTS = [
    0.20,  # acquisition
    0.20,  # retention
    0.15,  # upsell
    0.15,  # cross-sell
    0.10,  # awareness
    0.05,  # launch
    0.05,  # promotion
    0.05,  # reactivation
    0.03,  # loyalty
    0.02,  # winback
]

# Campaign years (recent years are more common)
CAMPAIGN_YEARS = ["2020", "2021", "2022", "2023", "2024"]
CAMPAIGN_YEAR_WEIGHTS = [0.05, 0.10, 0.20, 0.30, 0.35]

OBJECTIVE = [
    "Welcome",
    "Acquisition",
    "Upsell",
    "Cross-sell",
    "Retention",
    "In-Life",
    "Service",
    "Migration",
    "Out of Contract",
]
OBJECTIVE_WEIGHTS = [0.20, 0.05, 0.05, 0.15, 0.05, 0.10, 0.10, 0.10, 0.10]

# DMO owners
DMO_OWNERS = [
    "Abilash Jai",
    "Baskaran Amit",
    "Kumar Arushi",
    "Nanda Boglarka Erdei",
    "Curt Goff",
    "Dan Mullins",
    "Deepak Kumar",
    "Dominique Mahon",
    "Heran Patel",
    "Jim Flack",
    "Jordan Lewis",
    "Leigh-Anne Sainthouse",
    "Matt Berry",
    "Matt Perry",
    "Muskan Kaur",
    "No Owner",
    "Rebecca Wilson",
    "Sanjay Patel",
    "Shruti Bhola",
    "Sourabh Gupta",
    "Swati Rautela",
    "Victor Oppong",
]

# BT Marketing Partners
BT_PARTNERS = [
    "Google",
    "Microsoft",
    "Cisco",
    "Vodafone",
    "EE",
    "Amazon Web Services",
    "Oracle",
    "IBM",
    "Salesforce",
    "Adobe",
    "Dell Technologies",
    "HPE",
    "SAP",
    "Ericsson",
    "Nokia",
    "Huawei",
    "Accenture",
    "Deloitte Digital",
    "PwC Digital",
    "KPMG Digital",
    "Fujitsu",
    "Intel",
    "Apple",
    "Samsung",
    "LinkedIn",
    "Twitter",
    "Facebook",
    "Instagram",
    "TikTok",
    "YouTube",
    "Spotify",
    "Xero",
    "BBC",
    "Sky",
    "Channel 4",
    "ITV",
    "The Telegraph",
    "The Guardian",
    "Financial Times",
    "Wunderman Thompson",
    "Ogilvy",
    "Saatchi & Saatchi",
    "McCann",
    "WPP",
    "Publicis Groupe",
    "Omnicom Group",
    "IPG Mediabrands",
]

# Weights for partners (technology partners have higher weights)
BT_PARTNER_WEIGHTS = [
    0.06,  # Google
    0.06,  # Microsoft
    0.06,  # Cisco
    0.05,  # Vodafone
    0.05,  # EE
    0.05,  # Amazon Web Services
    0.04,  # Oracle
    0.04,  # IBM
    0.04,  # Salesforce
    0.03,  # Adobe
    0.03,  # Dell Technologies
    0.03,  # HPE
    0.03,  # SAP
    0.03,  # Ericsson
    0.03,  # Nokia
    0.02,  # Huawei
    0.02,  # Accenture
    0.02,  # Deloitte Digital
    0.02,  # PwC Digital
    0.02,  # KPMG Digital
    0.02,  # Fujitsu
    0.02,  # Intel
    0.02,  # Apple
    0.02,  # Samsung
    0.01,  # LinkedIn
    0.01,  # Twitter
    0.01,  # Facebook
    0.01,  # Instagram
    0.01,  # TikTok
    0.01,  # YouTube
    0.01,  # Spotify
    0.01,  # Xero
    0.01,  # BBC
    0.01,  # Sky
    0.01,  # Channel 4
    0.01,  # ITV
    0.01,  # The Telegraph
    0.01,  # The Guardian
    0.01,  # Financial Times
    0.01,  # Wunderman Thompson
    0.01,  # Ogilvy
    0.01,  # Saatchi & Saatchi
    0.01,  # McCann
    0.01,  # WPP
    0.01,  # Publicis Groupe
    0.01,  # Omnicom Group
    0.01,  # IPG Mediabrands
]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of campaign data."""
    # Extract company data from prior if available
    prior = kwargs.get("prior", {})
    company_df = prior.get("Company")
    product_df = prior.get("Products")

    product_ids = product_df.select("product_id").to_series().to_list()

    # Generate campaign IDs
    ids = make_ids(n, "CAM")

    # Create company IDs to associate with campaigns
    company_ids = []
    if company_df is not None:
        # Use existing company IDs if available
        company_ids = company_df["company_id"].to_list()

    # Generate start dates
    start_dates = [random_date() for _ in ids]

    # Generate end dates (between 30 and 180 days after start date)
    end_dates = []
    for start_date in start_dates:
        duration = timedelta(days=fake.random_int(min=30, max=180))
        end_dates.append(start_date + duration)

    # Generate BT products, situations, and years for campaign names
    bt_products = weighted_sample(BT_PRODUCTS, BT_PRODUCT_WEIGHTS, n)
    situations = weighted_sample(CAMPAIGN_SITUATIONS, CAMPAIGN_SITUATION_WEIGHTS, n)
    years = weighted_sample(CAMPAIGN_YEARS, CAMPAIGN_YEAR_WEIGHTS, n)

    # Generate campaign names in the format "BT product situation year"
    campaign_names = [
        f"{product} {situation} {year}"
        for product, situation, year in zip(bt_products, situations, years)
    ]

    # Generate campaign data
    df = pl.DataFrame(
        {
            "campaign_id": ids,
            "campaign_name": campaign_names,
            "start_date": start_dates,
            "end_date": end_dates,
            "created_date": [random_date() for _ in ids],
            # Fields required by the spreadsheet
            "objective": weighted_sample(OBJECTIVE, OBJECTIVE_WEIGHTS, n),
            "outcome_targets": [fake.text(max_nb_chars=50) for _ in ids],
            "costs_actuals": [fake.random_int(min=1000, max=400000) for _ in ids],
            "costs_anticipated": [fake.random_int(min=5000, max=500000) for _ in ids],
            "brand": ["BT" for _ in ids],  # Set brand to BT since we're using BT products
            "budget_timeframe": weighted_sample(
                ["Monthly", "Quarterly", "Annual", "One-time"], [0.3, 0.3, 0.3, 0.1], n
            ),
            "dmo_owner": weighted_sample(DMO_OWNERS, n=n),
            "partner": [
                (
                    weighted_sample(BT_PARTNERS, BT_PARTNER_WEIGHTS, 1)[0]
                    if fake.random.random() < PARTNER_PROBABILITY
                    else None
                )
                for _ in ids
            ],
            "product_id": weighted_sample(product_ids, n=n),
            "business_unit": weighted_sample(
                ["SMB", "CPS", "Global", "Wholesale"],
                [0.5, 0.3, 0.1, 0.1],
                n,
            ),
            "targeted_audience_id": [f"AUD{fake.random_int(min=1000, max=9999)}" for _ in ids],
        }
    )

    # Add company_id if company data is available
    if company_ids:
        df = df.with_columns(pl.Series("company_id", make_ids_with_duplicates(company_ids, n)))

    # Add parent_campaign_id (some campaigns are child campaigns of others)
    # About 30% of campaigns have a parent campaign
    return df.with_columns(pl.Series("parent_campaign_id", make_ids_with_duplicates(ids, n, 0.7)))
