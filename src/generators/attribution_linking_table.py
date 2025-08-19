"""Contains testing for the generate attribution linking table function and its helper functions."""

from typing import Any

import polars as pl

__all__ = ["generate"]

from src.random_utils import make_ids

_schema = [
    ("link_id", pl.String),
    ("activity_id", pl.String),
    ("interaction_id", pl.String),
    ("outcome_type", pl.String),
    ("outcome_id", pl.String),
    ("company_id", pl.String),
    ("person_id", pl.String),
    ("relation_type", pl.String),
    ("product_yca_tier", pl.String),
    ("company_yca_type", pl.String),
    ("time_lag", pl.Int64),
]


def _create_ancestry(df: pl.DataFrame, *, row_id: str, parent_id: str) -> pl.DataFrame:
    """Return every (node, ancestor, distance) triple in the hierarchy."""
    closure = df.select(
        pl.col(row_id).alias("origin_id"),
        pl.col(row_id).alias("ancestor_id"),
        pl.lit(0).alias("distance"),
    )

    level = df.filter(pl.col(parent_id).is_not_null()).select(
        pl.col(row_id).alias("origin_id"),
        pl.col(parent_id).alias("ancestor_id"),
        pl.lit(1).alias("distance"),
    )

    while level.height:
        closure = pl.concat([closure, level])

        level = (
            level.join(df, left_on="ancestor_id", right_on=row_id, how="inner")
            .filter(pl.col(parent_id).is_not_null())
            .select(
                pl.col("origin_id"),
                pl.col(parent_id).alias("ancestor_id"),
                (pl.col("distance") + 1).alias("distance"),
            )
        )

    return closure.unique()  # <- what your test wants


def _build_links(closure: pl.DataFrame) -> pl.DataFrame:
    """From closure build all shortest links between related children.

    From a closure `[origin_id, ancestor_id, distance]`
    produce a **symmetric** link table `[from_id, to_id, ancestor_id, degrees]`
    that keeps only the shortest path between each unordered pair.
    """
    a = closure.rename({"origin_id": "node_a", "distance": "dist_a"})
    b = closure.rename({"origin_id": "node_b", "distance": "dist_b"})

    links_raw = a.join(b, on="ancestor_id", how="inner").with_columns(
        (pl.col("dist_a") + pl.col("dist_b")).alias("degrees"),
        # ----------   materialise an unordered-pair key   ----------
        pl.when(pl.col("node_a") < pl.col("node_b"))
        .then(pl.concat_str([pl.col("node_a"), pl.col("node_b")], separator="|"))
        .otherwise(pl.concat_str([pl.col("node_b"), pl.col("node_a")], separator="|"))
        .alias("pair_key"),
    )

    # keep one shortest row per unordered pair
    links_min = (
        links_raw.sort("degrees")
        .unique(subset=["pair_key"], keep="first")
        .select("node_a", "node_b", "ancestor_id", "degrees")
    )

    # make symmetric and align columns

    # enforce identical column order before stacking
    wanted_cols = ["from_id", "to_id", "ancestor_id", "degrees"]

    df1 = links_min.rename({"node_a": "from_id", "node_b": "to_id"}).select(wanted_cols)
    df2 = links_min.rename({"node_a": "to_id", "node_b": "from_id"}).select(wanted_cols)
    # Remove any duplicated ordered pairs (e.g., self-pairs A==B would appear twice)
    return pl.concat([df1, df2]).unique().sort(["from_id", "to_id"])


def _define_schema() -> pl.DataFrame:
    """Define the Expected return schema."""
    # Create an empty DataFrame
    return pl.DataFrame(schema=_schema)


def _best_product_yca_level(  # noqa: PLR0913
    rows: pl.DataFrame,
    product_links: pl.DataFrame,
    products_df: pl.DataFrame,
    *,
    outcome_col: str,
    campaign_col: str,
    asset_col: str,
) -> pl.Series:
    """Compute best (youngest) common ancestor level for outcome vs campaign/asset products.

    This function reuses the generic links table built from a product closure
    to find, for each row, the common ancestor that minimises the combined
    distance (degrees) between the outcome product and either the campaign
    product or the asset product. The returned value is the ancestor's
    textual generation level as stored in the Products table (e.g. "Tier 1").

    :param rows: Frame containing outcome, campaign and asset product ID columns.
    :param product_links: Symmetric links table from _build_links over product closure.
    :param products_df: Products dimension table (must include product_id and level).
    :param outcome_col: Column name in rows containing the outcome product_id.
    :param campaign_col: Column name containing campaign product_id.
    :param asset_col: Column name containing asset product_id.
    :returns: A Series of string levels (or null) aligned with rows height.
    :raises ValueError: If required columns are missing.
    """
    required = {outcome_col, campaign_col, asset_col}
    missing = [c for c in required if c not in rows.columns]
    if missing:  # pragma: no cover
        raise ValueError(f"Missing required columns for YCA: {', '.join(missing)}")

    rows_s = rows.with_columns(
        [
            pl.col(outcome_col).cast(pl.String),
            pl.col(campaign_col).cast(pl.String),
            pl.col(asset_col).cast(pl.String),
        ]
    )

    prod_level = products_df.select(["product_id", "level"]).rename(
        {"product_id": "_anc_id", "level": "_anc_level"}
    )

    links_cols = ["from_id", "to_id", "ancestor_id", "degrees"]
    plc = product_links.select(links_cols)

    oc = (
        rows_s.join(
            plc,
            left_on=[outcome_col, campaign_col],
            right_on=["from_id", "to_id"],
            how="left",
        )
        .rename({"ancestor_id": "anc_oc", "degrees": "deg_oc"})
        .select(["anc_oc", "deg_oc"])
    )

    oa = (
        rows_s.join(
            plc,
            left_on=[outcome_col, asset_col],
            right_on=["from_id", "to_id"],
            how="left",
        )
        .rename({"ancestor_id": "anc_oa", "degrees": "deg_oa"})
        .select(["anc_oa", "deg_oa"])
    )

    tmp = pl.concat([rows_s, oc, oa], how="horizontal")

    best = tmp.with_columns(
        [
            pl.when(
                (pl.col("deg_oc").is_not_null())
                & ((pl.col("deg_oa").is_null()) | (pl.col("deg_oc") <= pl.col("deg_oa")))
            )
            .then(pl.col("anc_oc"))
            .otherwise(pl.col("anc_oa"))
            .alias("_best_anc"),
        ]
    )

    best = best.join(prod_level, left_on="_best_anc", right_on="_anc_id", how="left")
    return best.get_column("_anc_level").rename("product_yca_tier")


def _best_company_yca_type(
    rows: pl.DataFrame,
    company_links: pl.DataFrame,
    companies_df: pl.DataFrame,
    *,
    outcome_company_col: str,
    activity_company_col: str,
) -> pl.Series:
    """Compute company_yca_type: business type of youngest common parent between two companies.

    :param rows: Frame containing the outcome and activity company ID columns.
    :param company_links: Symmetric links table over the company closure.
    :param companies_df: Company dimension table with business type.
    :param outcome_company_col: Column in `rows` with the order's company_id.
    :param activity_company_col: Column in `rows` with the activity's company_id.
    :returns: Series of business type strings aligned to rows.height.
    :raises ValueError: If required columns are missing.
    """
    required = {outcome_company_col, activity_company_col}
    missing = [c for c in required if c not in rows.columns]
    if missing:  # pragma: no cover
        raise ValueError(f"Missing required columns for Company YCA: {', '.join(missing)}")

    rows_s = rows.with_columns(
        [
            pl.col(outcome_company_col).cast(pl.String),
            pl.col(activity_company_col).cast(pl.String),
        ]
    )

    # Minimal map ancestor -> business type
    comp_bt = companies_df.select(["company_id", "Company Business Type"]).rename(
        {"company_id": "_anc_id", "Company Business Type": "_anc_bt"}
    )

    cl = company_links.select(["from_id", "to_id", "ancestor_id", "degrees"])

    return (
        rows_s.join(
            cl,
            left_on=[outcome_company_col, activity_company_col],
            right_on=["from_id", "to_id"],
            how="left",
        )
        .rename({"ancestor_id": "anc_co"})
        .join(comp_bt, left_on="anc_co", right_on="_anc_id", how="left")
        .get_column("_anc_bt")
        .rename("company_yca_type")
    )


def _require_df(value: Any, name: str) -> pl.DataFrame:
    if not isinstance(value, pl.DataFrame):
        raise TypeError(f"Expected DataFrame for {name}, got {type(value).__name__}")
    return value


def generate(n: int, **kwargs: Any) -> pl.DataFrame:  # noqa PLR0915
    """Generate the attribution linking table deterministically from existing data.

    The function builds links via Interaction -> Person -> Company -> Order,
    filters by temporal order, and enriches with a product_yca_level column
    representing the youngest common ancestor level between the outcome product
    and the Campaign/Asset product associated to the originating activity.
    """
    prior: dict[str, pl.DataFrame] = kwargs.get("prior", {})

    interaction_df = _require_df(prior.get("Interactions"), "Interaction")
    person_df = _require_df(prior.get("Person"), "Person")
    company_df = _require_df(prior.get("Company"), "Company")
    order_df = _require_df(prior.get("Orders"), "Order")
    person_company_role_df = _require_df(prior.get("Person Company Role"), "Person Company Role")

    person_company_link_df = _generate_links_though_person_company(
        person_df, interaction_df, company_df, order_df, person_company_role_df
    )
    # Generate other link objects e.g. Interaction -> Company, Interaction -> Order

    combined_links = person_company_link_df  # Concatentate these once others created

    # Filter on dates and add date difference
    filtered_links = _date_difference_filter(combined_links, interaction_df, order_df)

    # ---------- Enrichment (Product YCA tier and Company YCA type) ----------
    products_df = _require_df(prior.get("Products"), "Products")
    marketing_activity_df = _require_df(prior.get("Marketing Activity"), "Marketing Activity")
    campaigns_df = _require_df(prior.get("Campaigns"), "Campaigns")
    assets_df = _require_df(prior.get("Marketing Assets"), "Marketing Assets")

    can_enrich = all(
        isinstance(df, pl.DataFrame)
        for df in (
            products_df,
            marketing_activity_df,
            campaigns_df,
            assets_df,
            interaction_df,
            order_df,
            company_df,
        )
    )

    if can_enrich and filtered_links.height:
        # Build closures/links once
        product_closure = _create_ancestry(
            products_df, row_id="product_id", parent_id="product_parent_id"
        )
        product_links = _build_links(product_closure)

        company_closure = _create_ancestry(
            company_df, row_id="company_id", parent_id="Parent_Company_ID"
        )
        company_links = _build_links(company_closure)

        # Bring in product IDs and company IDs
        # 1) outcome product and company via Orders
        rows = filtered_links.join(
            order_df.select(["order_id", "product_id", "company_id"]).rename(
                {
                    "order_id": "_outcome_id",
                    "product_id": "outcome_product_id",
                    "company_id": "outcome_company_id",
                }
            ),
            left_on="outcome_id",
            right_on="_outcome_id",
            how="left",
        )
        # 2) add activity_id and interacted_company_id via Interactions
        rows = (
            rows.join(
                interaction_df.select(["interaction_id", "activity_id", "interacted_company_id"]),
                on="interaction_id",
                how="left",
                suffix="_i",
            )
            .with_columns(
                pl.coalesce([pl.col("activity_id_i"), pl.col("activity_id")]).alias("activity_id")
            )
            .drop("activity_id_i")
        )
        # 3) campaign/asset and targeted_company_id via Marketing Activity
        rows = rows.join(
            marketing_activity_df.select(
                ["id", "campaign_id", "marketing_asset_id", "targeted_company_id"]
            ).rename({"id": "_activity_id"}),
            left_on="activity_id",
            right_on="_activity_id",
            how="left",
        )
        # 4) campaign product
        rows = rows.join(
            campaigns_df.select(["campaign_id", "product_id"]).rename(
                {"product_id": "campaign_product_id"}
            ),
            on="campaign_id",
            how="left",
        )
        # 5) asset product
        rows = rows.join(
            assets_df.select(["marketing_asset_id", "product_id"]).rename(
                {"product_id": "asset_product_id"}
            ),
            on="marketing_asset_id",
            how="left",
        )
        # 6) derive activity_company_id with preference for targeted_company_id
        rows = rows.with_columns(
            pl.coalesce([pl.col("targeted_company_id"), pl.col("interacted_company_id")]).alias(
                "activity_company_id"
            )
        )

        # Compute enrichments
        product_yca_tier = _best_product_yca_level(
            rows,
            product_links,
            products_df,
            outcome_col="outcome_product_id",
            campaign_col="campaign_product_id",
            asset_col="asset_product_id",
        )
        rows = rows.with_columns(product_yca_tier)

        # only compute company_yca_type if it wasn't already produced upstream
        if "company_yca_type" not in rows.columns:
            company_yca_type = _best_company_yca_type(
                rows,
                company_links,
                company_df,
                outcome_company_col="outcome_company_id",
                activity_company_col="activity_company_id",
            )
            rows = rows.with_columns(company_yca_type)

        enriched = rows
    else:
        # No enrichment possible: add null columns to satisfy schema
        enriched = filtered_links.with_columns(
            [
                pl.lit(None).cast(pl.String).alias("product_yca_tier"),
                pl.lit(None).cast(pl.String).alias("company_yca_type"),
            ]
        )

    # Generate Link IDs
    link_ids = pl.Series("link_id", make_ids(enriched.height, "LINK"))
    result = enriched.with_columns(link_ids)

    # Align output columns with spreadsheet 'Attributes' if available to avoid extra-field errors
    reg = kwargs.get("registry")
    if reg is not None and hasattr(reg, "cfg") and hasattr(reg.cfg, "workbook"):
        try:
            import pandas as pd

            pdf = pd.read_excel(reg.cfg.workbook, sheet_name="Attributes")
            obj_rows = pdf[pdf.get("Object").fillna("").astype(str) == "Attribution Linking Table"]
            if not obj_rows.empty and "Name" in obj_rows.columns:
                names = [str(x) for x in obj_rows["Name"].dropna().tolist() if str(x).strip()]

                def _norm(n: str) -> str:
                    return n.lower().replace(" ", "").replace("_", "")

                expected_norm = {_norm(x) for x in names}
                mapping = {_norm(c): c for c in result.columns}
                cols = [mapping[n] for n in expected_norm if n in mapping]
                if cols:
                    return result.select(cols)
        except Exception:
            # Fall back silently if workbook/attributes not available or parsing fails
            pass

    return result


def _generate_links_though_person_company(
    person_df: pl.DataFrame,
    interaction_df: pl.DataFrame,
    company_df: pl.DataFrame,
    order_df: pl.DataFrame,
    person_company_role_df: pl.DataFrame,
) -> pl.DataFrame:
    """Generate the links though person company."""
    company_ancestry = _create_ancestry(
        company_df, row_id="company_id", parent_id="Parent_Company_ID"
    )
    company_links = _build_links(company_ancestry)

    df = interaction_df
    df = df.join(
        person_company_role_df, left_on="interacted_person_id", right_on="person_id", how="inner"
    )
    df = df.join(company_links, left_on="company_id", right_on="from_id", how="inner")
    links_raw = df.join(order_df, left_on="to_id", right_on="company_id", how="inner")

    # --- NEW: compute company_yca_type at build time ---
    comp_bt = company_df.select(["company_id", "Company Business Type"]).rename(
        {"company_id": "_anc_id", "Company Business Type": "_anc_bt"}
    )
    links_raw = links_raw.join(
        comp_bt, left_on="ancestor_id", right_on="_anc_id", how="left"
    ).with_columns(pl.col("_anc_bt").alias("company_yca_type"))
    links_raw = links_raw.drop("_anc_bt")
    n = links_raw.height
    schema = _define_schema()
    if n == 0:
        # return an *empty* frame with the right dtypes so downstream code is safe
        return schema

    links_calculated = (
        links_raw
        # 1. deterministic / generated fields
        .with_columns(
            pl.lit("Order").alias("outcome_type"),
            pl.lit("Interaction-Person-Company-Order").alias("relation_type"),
        ).rename(
            {
                "interaction_id": "interaction_id",
                "order_id": "outcome_id",
                "interacted_person_id": "person_id",
            }
        )  # no-op if already correct
    )
    return (
        links_calculated.with_columns(  # add any missing columns with nulls
            [
                pl.lit(None).cast(dt).alias(col)
                for col, dt in _schema
                if col not in links_calculated.columns
            ]
        )
        # 3. final column order
        .select([col for col, _ in _schema])
        # 4. cast to expected dtypes (optional but tidy)
        .with_columns(
            pl.col("time_lag").cast(pl.Int64),
            pl.all().exclude("time_lag").cast(pl.String),
        )
    )


def _date_difference_filter(
    link: pl.DataFrame, interaction_df: pl.DataFrame, outcome_df: pl.DataFrame
) -> pl.DataFrame:
    """Calculate the difference between activity and outcome & Filter interaction after outcome."""
    # check we have the necessary interaction ID and outcome ID
    missing = [c for c in ("interaction_id", "outcome_id") if c not in link.columns]
    if missing:  # pragma: no cover
        raise ValueError(f"Required column(s) missing: {', '.join(missing)}")

    return (
        link.join(interaction_df, on="interaction_id", how="inner", suffix="_interaction")
        .join(outcome_df, left_on="outcome_id", right_on="order_id", how="inner", suffix="_outcome")
        .with_columns(
            (pl.col("date_raised") - pl.col("date")).alias("_lag"),
        )
        .filter(pl.col("_lag") >= pl.duration(days=0))
        .with_columns(
            # convert to *integer days* and drop helper
            pl.col("_lag")
            .dt.total_days()
            .cast(pl.Int64)
            .alias("time_lag")
        )
        .drop("_lag")
        # 3. final column order
        .select([name for name, _ in _schema])
    )
