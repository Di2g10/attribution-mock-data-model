"""Contains functions to generate marketing assets data."""

from __future__ import annotations

from typing import Any, List

import polars as pl

from ..random_utils import fake, make_ids, weighted_sample, generate_source_id_mappings

__all__ = ["generate"]


def generate_asset_names(n: int) -> List[str]:
    """Generate names for marketing assets.

    :param n: Number of asset names to generate
    :returns: List of asset names
    """
    # List of common marketing asset prefixes
    prefixes = [
        "BT Business",
        "BT Enterprise",
        "BT Global",
        "BT Connect",
        "BT Digital",
        "BT Cloud",
        "BT Security",
        "BT Mobile",
        "BT Network",
        "BT Solutions",
    ]

    # List of common asset types
    asset_types = [
        "Whitepaper",
        "Case Study",
        "Brochure",
        "Datasheet",
        "Infographic",
        "Video",
        "Webinar",
        "eBook",
        "Guide",
        "Report",
    ]

    # Generate unique asset names
    asset_names = []
    for i in range(n):
        prefix_idx = i % len(prefixes)
        asset_idx = i % len(asset_types)

        # Add a number suffix if we need more names than combinations
        suffix = f" {i//len(prefixes) + 1}" if i >= len(prefixes) * len(asset_types) else ""

        asset_name = f"{prefixes[prefix_idx]} {asset_types[asset_idx]}{suffix}"
        asset_names.append(asset_name)

    return asset_names


def generate_content(n: int) -> List[str]:
    """Generate content descriptions for marketing assets.

    :param n: Number of content descriptions to generate
    :returns: List of content descriptions
    """
    contents = []
    for _ in range(n):
        content = fake.paragraph(nb_sentences=3, variable_nb_sentences=True)
        contents.append(content)

    return contents


def generate_variants(n: int) -> List[str]:
    """Generate variants for marketing assets.

    :param n: Number of variants to generate
    :returns: List of variants
    """
    variants = [
        "Standard",
        "Extended",
        "Short Form",
        "Long Form",
        "Technical",
        "Executive",
        "Industry Specific",
        "Customer Focused",
        "Product Focused",
        "Solution Focused",
    ]

    return [variants[i % len(variants)] for i in range(n)]


def generate_product_families(n: int) -> List[str]:
    """Generate product families for marketing assets.

    :param n: Number of product families to generate
    :returns: List of product families
    """
    product_families = [
        "Connectivity",
        "Voice",
        "Mobility",
        "Security",
        "Cloud",
        "Collaboration",
        "IoT",
        "Data",
        "Managed Services",
        "Professional Services",
    ]

    return [product_families[i % len(product_families)] for i in range(n)]


def generate_products(n: int, product_families: List[str]) -> List[str]:
    """Generate products for marketing assets based on product families.

    :param n: Number of products to generate
    :param product_families: List of product families
    :returns: List of products
    """
    # Map of product families to specific products
    family_to_products = {
        "Connectivity": ["BT Business Broadband", "BT Superfast Fibre", "BT Ethernet Connect"],
        "Voice": ["BT SIP Trunk", "BT Cloud Voice", "BT Hosted Communications"],
        "Mobility": ["BT Business Mobile", "BT One Phone", "BT Mobile Data"],
        "Security": ["BT Firewall", "BT DDoS Protection", "BT Endpoint Security"],
        "Cloud": ["BT Public Cloud", "BT Private Cloud", "BT Hybrid Cloud"],
        "Collaboration": ["BT Video Conferencing", "BT Team Collaboration", "BT Messaging"],
        "IoT": ["BT IoT Connectivity", "BT IoT Platforms", "BT IoT Analytics"],
        "Data": ["BT Data Analytics", "BT Big Data", "BT Data Warehousing"],
        "Managed Services": [
            "BT Network Management",
            "BT Security Management",
            "BT Cloud Management",
        ],
        "Professional Services": ["BT Consulting", "BT Implementation", "BT Training"],
    }

    products = []
    for i in range(n):
        family = product_families[i]
        if family in family_to_products:
            family_products = family_to_products[family]
            product = family_products[i % len(family_products)]
        else:
            product = f"BT {family} Product {i+1}"

        products.append(product)

    return products


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of marketing assets data.

    :param n: Number of marketing assets to generate
    :param kwargs: Additional keyword arguments
    :returns: DataFrame containing generated marketing assets data
    """
    # Extract prior data if available
    prior = kwargs.get("prior", {})

    # Extract product IDs if available
    product_df = prior.get("Products", None)
    if product_df is None:
        raise ValueError("Missing product data")
    if "product_id" not in product_df.columns:
        raise ValueError("No product_id column in product data")

    product_ids = product_df["product_id"].to_list()

    # Generate IDs for all assets
    asset_ids = make_ids(n, "ASSET")

    # Generate asset names
    asset_names = generate_asset_names(n)

    # Generate content
    contents = generate_content(n)

    # Generate variants
    variants = generate_variants(n)

    # Generate Pega flags (boolean)
    pega_flags = [fake.boolean() for _ in range(n)]

    source_info = generate_source_id_mappings(
        [("marketo", "asset_id"), ("Adobe Analytics", "WebPage_ID")], n
    )

    # Create DataFrame
    return pl.DataFrame(
        {
            "marketing_asset_id": asset_ids,
            "name": asset_names,
            "uses_dynamic_content": contents,
            "pega_flag": pega_flags,
            "varient": variants,  # Note: using "varient" to match the field name in the spreadsheet
            "product_id": weighted_sample(product_ids, n=n),
        }
    ).hstack(source_info)
