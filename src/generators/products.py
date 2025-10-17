"""Contains a function to generate product data."""

from __future__ import annotations

from typing import Any, List, Tuple

import polars as pl

from ..random_utils import fake, make_ids, _rng as rng, weighted_sample

__all__ = ["generate"]

# BT product categories with weights
BT_PRODUCT_CATEGORIES = [
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

# Weights for product categories (higher weight = more common)
BT_PRODUCT_CATEGORY_WEIGHTS = [
    0.20,  # Connectivity
    0.15,  # Voice
    0.15,  # Mobility
    0.10,  # Security
    0.10,  # Cloud
    0.10,  # Collaboration
    0.05,  # IoT
    0.05,  # Data
    0.05,  # Managed Services
    0.05,  # Professional Services
]

# BT product subcategories by category
BT_PRODUCT_SUBCATEGORIES = {
    "Connectivity": ["Broadband", "Ethernet", "MPLS", "SD-WAN", "Internet Access"],
    "Voice": [
        "SIP Trunking",
        "Cloud Voice",
        "Hosted PBX",
        "Contact Centre",
        "Unified Communications",
    ],
    "Mobility": [
        "Mobile Voice",
        "Mobile Data",
        "Mobile Devices",
        "Mobile Applications",
        "Mobile Security",
    ],
    "Security": [
        "Firewall",
        "DDoS Protection",
        "Endpoint Security",
        "Identity Management",
        "Threat Intelligence",
    ],
    "Cloud": ["Public Cloud", "Private Cloud", "Hybrid Cloud", "Cloud Storage", "Cloud Compute"],
    "Collaboration": [
        "Video Conferencing",
        "Team Collaboration",
        "Messaging",
        "File Sharing",
        "Virtual Events",
    ],
    "IoT": ["IoT Connectivity", "IoT Platforms", "IoT Analytics", "IoT Security", "IoT Devices"],
    "Data": [
        "Data Analytics",
        "Big Data",
        "Data Warehousing",
        "Business Intelligence",
        "Data Visualization",
    ],
    "Managed Services": [
        "Network Management",
        "Security Management",
        "Cloud Management",
        "Device Management",
        "Service Desk",
    ],
    "Professional Services": ["Consulting", "Implementation", "Training", "Support", "Maintenance"],
}

# BT specific products by subcategory
BT_SPECIFIC_PRODUCTS = {
    "Broadband": [
        "BT Business Broadband",
        "BT Superfast Fibre",
        "BT Ultrafast Fibre",
        "BT Full Fibre",
    ],
    "Ethernet": ["BT Ethernet Connect", "BT Ethernet Connect E-Line", "BT Ethernet Connect E-LAN"],
    "MPLS": ["BT IP Connect Global", "BT IP Connect UK", "BT IP Connect Web-VPN"],
    "SD-WAN": ["BT Agile Connect", "BT Connect Intelligence", "BT Connect Edge"],
    "Internet Access": [
        "BT Internet Connect",
        "BT Internet Connect Reach",
        "BT Internet Connect Direct",
    ],
    "SIP Trunking": ["BT SIP Trunk", "BT SIP Trunk Security", "BT SIP Trunk Resilience"],
    "Cloud Voice": ["BT Cloud Voice", "BT Cloud Voice Express", "BT Cloud Voice SIP"],
    "Hosted PBX": ["BT Hosted Communications", "BT Hosted Contact", "BT Hosted Collaboration"],
    "Contact Centre": ["BT Contact", "BT Auto Contact", "BT Cloud Contact"],
    "Unified Communications": ["BT One Enterprise", "BT One Cloud", "BT One Mobile"],
    "Mobile Voice": ["BT Business Mobile", "BT One Phone", "BT 4G Calling"],
    "Mobile Data": ["BT Business Mobile Data", "BT Mobile Broadband", "BT Mobile Internet"],
    "Mobile Devices": ["BT Mobile Handsets", "BT Mobile Tablets", "BT Mobile Accessories"],
    "Mobile Applications": ["BT Mobile Apps", "BT Mobile Solutions", "BT Mobile Workspace"],
    "Mobile Security": [
        "BT Mobile Protect",
        "BT Mobile Device Security",
        "BT Mobile Threat Defense",
    ],
    # Add more specific products for other subcategories as needed
}


# Helper functions for product generation
def generate_level1_products(
    level1_count: int, level1_ids: List[str]
) -> Tuple[List[str], pl.DataFrame]:
    """Generate level 1 products (top level categories).

    :param level1_count: Number of level 1 products to generate
    :param level1_ids: List of IDs for level 1 products
    :returns: Tuple of (level1_categories, level1_df)
    """
    # Ensure unique categories by using random.sample instead of weighted_sample
    # If we need more categories than available, we'll repeat some but add a number suffix
    available_categories = BT_PRODUCT_CATEGORIES.copy()
    level1_categories = []

    for i in range(level1_count):
        if available_categories:
            # Use weights to select the next category
            weights = [
                BT_PRODUCT_CATEGORY_WEIGHTS[BT_PRODUCT_CATEGORIES.index(cat)]
                for cat in available_categories
            ]
            # Normalize weights
            total = sum(weights)
            weights = [w / total for w in weights]
            # Select a category
            category = rng.choice(available_categories, p=weights)
            level1_categories.append(category)
            # Remove the selected category to ensure uniqueness
            available_categories.remove(category)
        else:
            # If we've used all categories, add a numbered suffix to distinguish duplicates
            category = rng.choice(BT_PRODUCT_CATEGORIES, p=BT_PRODUCT_CATEGORY_WEIGHTS)
            level1_categories.append(f"{category} {i+1}")

    level1_df = pl.DataFrame(
        {
            "product_id": level1_ids,
            "product_parent_id": [""]
            * level1_count,  # No parent for top level (empty string instead of None)
            "name": level1_categories,
            "level": ["Tier 1"] * level1_count,
            "source_table": ["Product Catalog"] * level1_count,
            "source_id_field": ["product_id"] * level1_count,
            "source_id": [f"CAT{i:04d}" for i in range(1, level1_count + 1)],
            "renewalrate": weighted_sample([0.9, 0.8, 0.7, 0.6, 0.5], n=level1_count),
        }
    )

    return level1_categories, level1_df


def generate_level2_products(
    level2_count: int, level2_ids: List[str], level1_ids: List[str], level1_categories: List[str]
) -> Tuple[List[str], pl.DataFrame]:
    """Generate level 2 products (subcategories).

    :param level2_count: Number of level 2 products to generate
    :param level2_ids: List of IDs for level 2 products
    :param level1_ids: List of IDs for level 1 products
    :param level1_categories: List of category names for level 1 products
    :returns: Tuple of (level2_names, level2_df)
    """
    level2_parent_ids = []
    level2_names = []
    level1_count = len(level1_ids)

    # Track used subcategories for each parent category to avoid duplicates
    used_subcategories: dict[str, set[str]] = {parent_id: set() for parent_id in level1_ids}

    # Track parent categories for easier reference
    parent_id_to_category = {level1_ids[i]: level1_categories[i] for i in range(level1_count)}

    # Assign each level 2 product to a random level 1 parent
    for i in range(level2_count):
        # Try to find a parent that still has available subcategories
        available_parents = []
        for parent_id in level1_ids:
            parent_category = parent_id_to_category[parent_id]
            if parent_category in BT_PRODUCT_SUBCATEGORIES:
                subcategories = BT_PRODUCT_SUBCATEGORIES[parent_category]
                # Check if there are unused subcategories for this parent
                if len(used_subcategories[parent_id]) < len(subcategories):
                    available_parents.append(parent_id)

        # If no parents have available subcategories, reset and allow duplicates with suffixes
        if not available_parents:
            parent_id = rng.choice(level1_ids)
            parent_category = parent_id_to_category[parent_id]

            if parent_category in BT_PRODUCT_SUBCATEGORIES:
                subcategories = BT_PRODUCT_SUBCATEGORIES[parent_category]
                subcategory = rng.choice(subcategories)
                # Add a suffix to make it unique
                subcategory = f"{subcategory} {i+1}"
            else:
                # Fallback if category not found
                subcategory = f"{parent_category} {fake.word().capitalize()}"
        else:
            # Select a random parent from those with available subcategories
            parent_id = rng.choice(available_parents)
            parent_category = parent_id_to_category[parent_id]

            if parent_category in BT_PRODUCT_SUBCATEGORIES:
                subcategories = BT_PRODUCT_SUBCATEGORIES[parent_category]
                # Filter out already used subcategories for this parent
                available_subcategories = [
                    s for s in subcategories if s not in used_subcategories[parent_id]
                ]
                subcategory = rng.choice(available_subcategories)
                # Mark this subcategory as used for this parent
                used_subcategories[parent_id].add(subcategory)
            else:
                # Fallback if category not found
                subcategory = f"{parent_category} {fake.word().capitalize()}"

        level2_parent_ids.append(parent_id)
        level2_names.append(subcategory)

    level2_df = pl.DataFrame(
        {
            "product_id": level2_ids,
            "product_parent_id": level2_parent_ids,
            "name": level2_names,
            "level": ["Tier 2"] * level2_count,
            "source_table": ["Product Catalog"] * level2_count,
            "source_id_field": ["product_id"] * level2_count,
            "source_id": [f"SUB{i:04d}" for i in range(1, level2_count + 1)],
            "renewalrate": weighted_sample([0.9, 0.8, 0.7, 0.6, 0.5], n=level2_count),
        }
    )

    return level2_names, level2_df


def generate_level3_products(
    level3_count: int, level3_ids: List[str], level2_ids: List[str], level2_names: List[str]
) -> pl.DataFrame:
    """Generate level 3 products (specific products).

    :param level3_count: Number of level 3 products to generate
    :param level3_ids: List of IDs for level 3 products
    :param level2_ids: List of IDs for level 2 products
    :param level2_names: List of subcategory names for level 2 products
    :returns: DataFrame containing level 3 products
    """
    level3_parent_ids = []
    level3_names = []
    level2_count = len(level2_ids)

    # Track used specific products for each parent subcategory to avoid duplicates
    used_specific_products: dict[str, set[str]] = {parent_id: set() for parent_id in level2_ids}

    # Track parent subcategories for easier reference
    parent_id_to_subcategory = {level2_ids[i]: level2_names[i] for i in range(level2_count)}

    # Assign each level 3 product to a random level 2 parent
    for i in range(level3_count):
        # Try to find a parent that still has available specific products
        available_parents = []
        for parent_id in level2_ids:
            parent_subcategory = parent_id_to_subcategory[parent_id]
            if parent_subcategory in BT_SPECIFIC_PRODUCTS:
                specific_products = BT_SPECIFIC_PRODUCTS[parent_subcategory]
                # Check if there are unused specific products for this parent
                if len(used_specific_products[parent_id]) < len(specific_products):
                    available_parents.append(parent_id)

        # If no parents have available specific products, select any parent and add a unique suffix
        if not available_parents:
            parent_id = rng.choice(level2_ids)
            parent_subcategory = parent_id_to_subcategory[parent_id]

            if parent_subcategory in BT_SPECIFIC_PRODUCTS:
                specific_products = BT_SPECIFIC_PRODUCTS[parent_subcategory]
                specific_product = rng.choice(specific_products)
                # Add a unique identifier to make it unique
                specific_product = f"{specific_product} {fake.word().capitalize()}"
            else:
                # Fallback if subcategory not found
                specific_product = f"BT {parent_subcategory} {fake.word().capitalize()}"
        else:
            # Select a random parent from those with available specific products
            parent_id = rng.choice(available_parents)
            parent_subcategory = parent_id_to_subcategory[parent_id]

            if parent_subcategory in BT_SPECIFIC_PRODUCTS:
                specific_products = BT_SPECIFIC_PRODUCTS[parent_subcategory]
                # Filter out already used specific products for this parent
                available_specific_products = [
                    p for p in specific_products if p not in used_specific_products[parent_id]
                ]
                specific_product = rng.choice(available_specific_products)
                # Mark this specific product as used for this parent
                used_specific_products[parent_id].add(specific_product)
            else:
                # Fallback if subcategory not found
                specific_product = f"BT {parent_subcategory} {fake.word().capitalize()}"

        level3_parent_ids.append(parent_id)
        level3_names.append(specific_product)

    return pl.DataFrame(
        {
            "product_id": level3_ids,
            "product_parent_id": level3_parent_ids,
            "name": level3_names,
            "level": ["Tier 3"] * level3_count,
            "source_table": ["Product Catalog"] * level3_count,
            "source_id_field": ["product_id"] * level3_count,
            "source_id": [f"PROD{i:04d}" for i in range(1, level3_count + 1)],
            "renewalrate": weighted_sample([0.9, 0.8, 0.7, 0.6, 0.5], n=level3_count),
        }
    )


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of product data with a 3-tier hierarchy.

    :param n: Number of products to generate
    :param kwargs: Additional keyword arguments
    :returns: DataFrame containing generated product data
    """
    # Determine the number of products at each level
    # Level 1 (top level): ~10% of products
    # Level 2 (middle level): ~30% of products
    # Level 3 (bottom level): ~60% of products
    level1_count = max(1, round(n * 0.1))
    remaining = n - level1_count

    level2_count = min(remaining, round(n * 0.3))
    remaining -= level2_count

    level3_count = remaining

    # Generate product IDs for each level
    all_ids = make_ids(n, "PROD")
    level1_ids = all_ids[:level1_count]
    level2_ids = all_ids[level1_count : level1_count + level2_count]
    level3_ids = all_ids[level1_count + level2_count :]

    # Generate products for each level
    level1_categories, level1_df = generate_level1_products(level1_count, level1_ids)

    level2_names: List[str] = []
    level2_df = pl.DataFrame()
    if level2_count:
        level2_names, level2_df = generate_level2_products(
            level2_count, level2_ids, level1_ids, level1_categories
        )

    level3_df = pl.DataFrame()
    if level3_count:
        level3_df = generate_level3_products(level3_count, level3_ids, level2_ids, level2_names)

    # Combine all levels into a single DataFrame
    frames = [df for df in (level1_df, level2_df, level3_df) if df.height]
    return pl.concat(frames)
