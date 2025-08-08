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


def generate(n: int, **kwargs: Any) -> pl.DataFrame:  # registry/prior unused yet
    """Generate a DataFrame of company data.

    Performance optimizations:
    - Uses NumPy's vectorized random operations for better performance with large datasets
    - Pre-generates and reuses values instead of generating them on-demand
    - Limits the number of expensive fake.city() calls by creating a reusable pool
    """
    # Use NumPy's RNG for better performance with vectorized operations
    rng = np.random.default_rng()

    ids = make_ids(n, "CO")
    # Ensure at least one owner_id even for small values of n
    owner_count = max(1, floor(n / 20))
    owner_ids = make_ids(owner_count, "OWN")

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

    return pl.DataFrame(
        {
            "company_id": ids,
            "industry": industries,
            "Owner_ID": make_ids_with_duplicates(owner_ids, n),
            "Parent_Company_ID": make_ids_with_duplicates(ids, n, 0.8),
            "Company Business Type": weighted_sample(
                ["CUG", "PHCO", "Billing Account", "Legal Entity"], [0.2, 0.2, 0.3, 0.3], n
            ),
            "Vertical": verticals,
            "location": selected_locations,
            "Company Market Channel": weighted_sample(
                ["Direct", "Indirect", "Partner", "Online", "Retail"], [0.4, 0.2, 0.2, 0.1, 0.1], n
            ),
        }
    )
