"""Contains a function to generate campaign data."""

from __future__ import annotations

from typing import Any
from datetime import timedelta

import polars as pl

from ..random_utils import (
    fake,
    make_ids,
    random_date,
    weighted_sample,
    require_df,
)

__all__ = ["CampaignField", "generate"]

# src/generators/campaign_fields_enum.py
from enum import StrEnum  # if needed: fallback to `class CampaignField(str, Enum): ...`


class CampaignField(StrEnum):
    """Field names for campaign data."""

    campaign_id = "campaign_id"
    campaign_name = "campaign_name"
    dmo_monday_id = "dmo_monday_id"
    activity_status = "activity_status"
    marketing_lead_name = "marketing_lead_name"
    contributer_name = "contributer_name"  # matches sheet spelling
    campaign_planned_start_date = "campaign_planned_start_date"
    campaign_live_date = "campaign_live_date"
    engaged_team_name = "engaged_team_name"
    campaign_summary = "campaign_summary"
    engagement_stage_classification = "engagement_stage_classification"
    activity_type = "activity_type"
    impacted_segment_name = "impacted_segment_name"
    campaign_theme_name = "campaign_theme_name"
    product_area = "product_area"
    impacted_region = "impacted_region"
    strategic_pillar = "strategic_pillar"
    campaign_purpose = "campaign_purpose"
    business_vertical = "business_vertical"
    partner_name = "partner_name"
    agency_support_ind = "agency_support_ind"
    agency_name = "agency_name"
    brand_name = "brand_name"
    estimated_outcome_gross_margin = "estimated_outcome_gross_margin"
    estimated_outcome_sov = "estimated_outcome_sov"
    estimated_outcome_roix1 = "estimated_outcome_roix1"
    overall_timeline_start = "overall_timeline_start"
    overall_timeline_end = "overall_timeline_end"
    outcome_linear_roi_flag = "outcome_linear_roi_flag"
    monday_record_creation_dtm = "monday_record_creation_dtm"
    product_id = "product_id"
    source_table = "source_table"
    source_id_field = "source_id_field"
    source_id = "source_id"


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
    "",
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
    0.7,
]


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of campaign data."""
    # Extract company data from prior if available
    prior = kwargs.get("prior", {})
    product_df = require_df(prior.get("Products"), "Products")

    product_ids = product_df.select("product_id").to_series().to_list()

    # Generate campaign IDs
    ids = make_ids(n, "CAM")

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

    # Generate campaign data aligned to spreadsheet (snake_case names)
    monday_creation = [random_date() for _ in ids]
    agency_support = [fake.random_element([True, False]) for _ in ids]
    segments = weighted_sample(["SMB", "CPS", "Global", "Wholesale"], [0.5, 0.3, 0.1, 0.1], n)

    # Derive planned/live dates relative to overall timeline
    planned_starts = start_dates
    live_dates = [s + timedelta(days=fake.random_int(min=0, max=14)) for s in planned_starts]

    return pl.DataFrame(
        {
            CampaignField.campaign_id: ids,
            CampaignField.campaign_name: campaign_names,
            CampaignField.overall_timeline_start: start_dates,
            CampaignField.overall_timeline_end: end_dates,
            CampaignField.monday_record_creation_dtm: monday_creation,
            CampaignField.campaign_summary: [fake.text(max_nb_chars=80) for _ in ids],
            CampaignField.brand_name: ["bt"] * n,  # was "brand"
            CampaignField.marketing_lead_name: weighted_sample(
                DMO_OWNERS, n=n
            ),  # was marketing_lead
            CampaignField.partner_name: weighted_sample(
                BT_PARTNERS, BT_PARTNER_WEIGHTS, n
            ),  # was partner
            CampaignField.product_id: weighted_sample(product_ids, n=n),
            CampaignField.impacted_segment_name: segments,  # was "segment"
            CampaignField.campaign_planned_start_date: planned_starts,
            CampaignField.campaign_live_date: live_dates,
            CampaignField.activity_type: weighted_sample(CAMPAIGN_TYPES, CAMPAIGN_TYPE_WEIGHTS, n),
            CampaignField.activity_status: weighted_sample(
                CAMPAIGN_STATUS, CAMPAIGN_STATUS_WEIGHTS, n
            ),
            CampaignField.campaign_purpose: weighted_sample(
                ["acquisition", "retention", "upsell", "awareness"], n=n
            ),  # was "purpose"
            CampaignField.engagement_stage_classification: weighted_sample(
                ["TOFU", "MOFU", "BOFU"], [0.4, 0.4, 0.2], n
            ),
            CampaignField.product_area: weighted_sample(BT_PRODUCTS, BT_PRODUCT_WEIGHTS, n),
            CampaignField.business_vertical: weighted_sample(
                CAMPAIGN_SITUATIONS, CAMPAIGN_SITUATION_WEIGHTS, n
            ),  # was "vertical" earlier; choose *one* source: segments or situations
            CampaignField.agency_name: [
                (
                    weighted_sample(BT_PARTNERS, BT_PARTNER_WEIGHTS, 1)[0]
                    if agency_support[i]
                    else None
                )
                for i in range(n)
            ],
            CampaignField.agency_support_ind: agency_support,  # was "agency_support_flag"
            CampaignField.campaign_theme_name: weighted_sample(
                ["launch", "promo", "brand", "retail"], n=n
            ),
            CampaignField.strategic_pillar: weighted_sample(
                ["growth", "retention", "efficiency"], n=n
            ),
            CampaignField.impacted_region: weighted_sample(
                ["UK", "EMEA", "Global"], [0.8, 0.15, 0.05], n
            ),
            CampaignField.contributer_name: [
                fake.name() for _ in ids
            ],  # was "contributers" (typo retained per sheet)
            CampaignField.engaged_team_name: weighted_sample(
                ["Demand Gen", "Brand", "Product Marketing", "Field"], n=n
            ),  # was "team"
            CampaignField.dmo_monday_id: [
                f"MON{fake.random_int(min=1000, max=999999)}" for _ in ids
            ],
            CampaignField.outcome_linear_roi_flag: weighted_sample([True, False], [0.2, 0.8], n),
            CampaignField.estimated_outcome_roix1: [
                round(fake.random_number(digits=2, fix_len=False) / 10, 2) for _ in ids
            ],  # was "estimated_outcome_roi_x1"
            CampaignField.estimated_outcome_sov: [
                round(fake.random_number(digits=2, fix_len=False) / 10, 2) for _ in ids
            ],
            CampaignField.estimated_outcome_gross_margin: [
                fake.random_int(min=10, max=90) for _ in ids
            ],
            # provenance
            CampaignField.source_table: ["campaign_management"] * n,
            CampaignField.source_id_field: ["campaign_id"] * n,
            CampaignField.source_id: [f"cmp{i:04d}" for i in range(1, n + 1)],
        }
    )
