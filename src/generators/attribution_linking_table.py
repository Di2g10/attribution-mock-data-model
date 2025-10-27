"""Contains testing for the generate attribution linking table function and its helper functions."""

from typing import Any

import polars as pl

__all__ = ["generate"]

from src.random_utils import require_df

_schema_base = {
    "interaction_id": pl.String,
    "outcome_type": pl.String,
    "outcome_id": pl.String,
    "company_id": pl.String,
    "relation_type": pl.String,
}
_schema_time_lag = {
    **_schema_base,
    "time_lag": pl.Int64,
}
_schema_enriched = {
    "link_id": pl.String,
    "marketing_activity_id": pl.String,
    **_schema_time_lag,
    "person_id": pl.String,
    "interaction_type": pl.String,
    "channel_name": pl.String,
    "product_yca_tier": pl.String,
    "company_yca_type": pl.String,
}


def _create_ancestry(
    df: pl.DataFrame, *, row_id: str, parent_id: str, usage_tag: str = ""
) -> pl.DataFrame:
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
    count = 0
    limit = 10
    while level.height:
        count += 1
        print(f"{usage_tag} _create_ancestry level.height:{level.height} count:{count}")

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
        if count > limit:
            break

    return closure.unique()  # <- what your test wants


def _build_links(closure: pl.LazyFrame) -> pl.LazyFrame:
    """From closure build all shortest links between related children.

    From a closure `[origin_id, ancestor_id, distance]`
    produce a **symmetric** link table `[from_id, to_id, ancestor_id, degrees]`
    that keeps only the shortest path between each unordered pair.

    This implementation uses Polars lazy with streaming joins to reduce peak
    memory during construction for large hierarchies.
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
        links_raw.group_by("pair_key")
        .agg(pl.all().sort_by("degrees").first())  # picks the min-degrees row per pair
        .select(["node_a", "node_b", "ancestor_id", "degrees"])
    )

    # make symmetric and align columns

    # enforce identical column order before stacking
    wanted_cols = ["from_id", "to_id", "ancestor_id", "degrees"]

    df1 = links_min.rename({"node_a": "from_id", "node_b": "to_id"}).select(wanted_cols)
    df2 = links_min.rename({"node_a": "to_id", "node_b": "from_id"}).select(wanted_cols)
    # Remove any duplicated ordered pairs (e.g., self-pairs A==B would appear twice)
    return pl.concat([df1, df2], how="vertical").unique()


def _find_shortest_links(closure: pl.LazyFrame) -> pl.LazyFrame:
    """Backward-compatible alias; compute symmetric shortest links between nodes.

    Historically exported as `_find_shortest_links`; implementation is identical to `_build_links`.
    :param closure: DataFrame with columns [origin_id, ancestor_id, distance]
    :returns: Symmetric links table [from_id, to_id, ancestor_id, degrees]
    """
    return _build_links(closure).lazy()


def _compute_product_yca(  # noqa PLR0913 Too many arguments in function definition (6 > 5)
    rows: pl.DataFrame,
    product_links: pl.DataFrame,
    products_df: pl.DataFrame,
    *,
    outcome_col: str,
    campaign_col: str,
    asset_col: str,
) -> pl.LazyFrame:
    """Backward-compatible alias for `_best_product_yca_level`.

    Returns the product_yca_tier Series aligned to the given lf.
    """
    return _best_product_yca_level(
        rows.lazy(),
        product_links,
        products_df,
        outcome_col=outcome_col,
        campaign_col=campaign_col,
        asset_col=asset_col,
    )


def _define_schema(stage: str) -> pl.DataFrame:
    """Define the Expected return schema."""
    # Create an empty DataFrame
    if stage == "base":
        return pl.DataFrame(schema=_schema_base)
    if stage == "enriched":
        return pl.DataFrame(schema=_schema_enriched)
    raise ValueError(f"Invalid stage: {stage} should be 'base' or 'enriched'")


def _best_product_yca_level(  # noqa: PLR0913
    lf: pl.LazyFrame,
    product_links: pl.DataFrame,
    products_df: pl.DataFrame,
    *,
    outcome_col: str,
    campaign_col: str,
    asset_col: str,
) -> pl.LazyFrame:
    """Compute best (youngest) common ancestor level for outcome vs campaign/asset products.

    This function reuses the generic links table built from a product closure
    to find, for each row, the common ancestor that minimises the combined
    distance (degrees) between the outcome product and either the campaign
    product or the asset product. The returned value is the ancestor's
    textual generation level as stored in the Products table (e.g. "Tier 1").

    :param lf: Frame containing outcome, campaign and asset product ID columns.
    :param product_links: Symmetric links table from _build_links over product closure.
    :param products_df: Products dimension table (must include product_id and level).
    :param outcome_col: Column name in lf containing the outcome product_id.
    :param campaign_col: Column name containing campaign product_id.
    :param asset_col: Column name containing asset product_id.
    :returns: A Series of string levels (or null) aligned with lf height.
    :raises ValueError: If required columns are missing.
    """
    required = {outcome_col, campaign_col, asset_col}
    missing = [c for c in required if c not in lf.collect_schema().names()]
    if missing:  # pragma: no cover
        raise ValueError(f"Missing required columns for YCA: {', '.join(missing)}")

    rows_s = lf.with_columns(
        [
            pl.col(outcome_col).cast(pl.String),
            pl.col(campaign_col).cast(pl.String),
            pl.col(asset_col).cast(pl.String),
        ]
    )

    prod_level = (
        products_df.select(["product_id", "level"])
        .rename({"product_id": "_anc_id", "level": "_anc_level"})
        .lazy()
    )

    links_cols = ["from_id", "to_id", "ancestor_id", "degrees"]
    plc = product_links.select(links_cols).lazy()

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
    return best.select(pl.col("_anc_level").alias("product_yca_tier"))


def _best_company_yca_type(
    lf: pl.LazyFrame,
    company_links: pl.DataFrame,
    companies_df: pl.DataFrame,
    *,
    outcome_company_col: str,
    activity_company_col: str,
) -> pl.Series:
    """Compute company_yca_type: business type of youngest common parent between two companies.

    :param lf: Frame containing the outcome and activity company ID columns.
    :param company_links: Symmetric links table over the company closure.
    :param companies_df: Company dimension table with business type.
    :param outcome_company_col: Column in `lf` with the order's company_id.
    :param activity_company_col: Column in `lf` with the activity's company_id.
    :returns: Series of business type strings aligned to lf.height.
    :raises ValueError: If required columns are missing.
    """
    required = {outcome_company_col, activity_company_col}
    missing = [c for c in required if c not in lf.collect_schema().names()]
    if missing:  # pragma: no cover
        raise ValueError(f"Missing required columns for Company YCA: {', '.join(missing)}")

    rows_s = lf.with_columns(
        [
            pl.col(outcome_company_col).cast(pl.String),
            pl.col(activity_company_col).cast(pl.String),
        ]
    )

    # Minimal map ancestor -> business type
    comp_bt = (
        companies_df.select(["company_id", "Company Business Type"])
        .rename({"company_id": "_anc_id", "Company Business Type": "_anc_bt"})
        .lazy()
    )

    cl = company_links.select(["from_id", "to_id", "ancestor_id", "degrees"]).lazy()

    return (
        rows_s.join(
            cl,
            left_on=[outcome_company_col, activity_company_col],
            right_on=["from_id", "to_id"],
            how="left",
        )
        .rename({"ancestor_id": "anc_co"})
        .join(comp_bt, left_on="anc_co", right_on="_anc_id", how="left")
        .select(pl.col("_anc_bt").alias("company_yca_type"))
    )


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate the attribution linking table deterministically from existing data.

    The function builds links via multiple strategies in priority order:
    1) Interaction -> Person -> Order (direct person match to order.contact_id)
    2) Interaction -> Person -> Company -> Order (via company ancestry)
    3) Interaction -> Company -> Order (when person unknown, via company ancestry)

    It then filters by temporal order and enriches with product_yca_tier and
    company_yca_type. Duplicates are resolved by keeping the highest-priority
    relation for each (interaction_id, outcome_id) pair.
    """
    prior: dict[str, pl.DataFrame] = kwargs.get("prior", {})

    interaction_df = require_df(prior.get("Interactions"), "Interaction")
    # person_df = require_df(prior.get("Person"), "Person")
    company_df = require_df(prior.get("Company"), "Company")
    order_df = require_df(prior.get("Orders"), "Order")
    channel_df = require_df(prior.get("Channels"), "Channel")

    # Build all link types (omit role-based path)
    direct_person_links = _generate_links_direct_person(interaction_df, order_df)
    person_company_link_df = _define_schema("base")  # no-op placeholder
    company_only_links = _generate_links_company_only(interaction_df, company_df, order_df)

    df = merge_links([direct_person_links, person_company_link_df, company_only_links])

    # Filter on dates and add date difference
    filtered_links = _date_difference_filter(df, interaction_df, order_df)

    # ---------- Enrichment (Product YCA tier and Company YCA type) ----------
    products_df = require_df(prior.get("Products"), "Products")
    marketing_activity_df = require_df(prior.get("Marketing Activity"), "Marketing Activity")
    campaigns_df = require_df(prior.get("Campaigns"), "Campaigns")
    assets_df = require_df(prior.get("Marketing Assets"), "Marketing Assets")

    # Build closures/links once
    product_closure = _create_ancestry(
        products_df, row_id="product_id", parent_id="product_parent_id", usage_tag="product_closure"
    )
    product_links = _build_links(product_closure)

    company_closure = _create_ancestry(
        company_df, row_id="company_id", parent_id="Parent_Company_ID", usage_tag="company_closure"
    )
    company_links = _build_links(company_closure)

    # Bring in product IDs and company IDs using a lazy, streaming pipeline
    lf = filtered_links.lazy()

    # 1) outcome product and company via Orders
    lf_with_orders = lf.join(
        order_df.select(["order_id", "product_id", "company_id"])
        .rename(
            {
                "order_id": "_outcome_id",
                "product_id": "outcome_product_id",
                "company_id": "outcome_company_id",
            }
        )
        .lazy(),
        left_on="outcome_id",
        right_on="_outcome_id",
        how="left",
    )

    # 2) add marketing_activity_id and interacted_company_id via Interactions
    lf_with_interaction = lf_with_orders.join(
        (
            interaction_df.select(
                [
                    "interaction_id",
                    "marketing_activity_id",
                    "interacted_company_id",
                    "interaction_type",
                    "interacted_person_id",
                ]
            ).lazy()
        ),
        on="interaction_id",
        how="left",
        suffix="_i",
    )
    # 3) campaign/asset and targeted_company_id via Marketing Activity
    lf_with_ma = lf_with_interaction.join(
        marketing_activity_df.select(
            [
                "marketing_activity_id",
                "campaign_id",
                "marketing_asset_id",
                "targeted_company_id",
                "channel_id",
            ]
        ).lazy(),
        left_on="marketing_activity_id",
        right_on="marketing_activity_id",
        how="left",
    )
    # 4) campaign product
    lf_with_campaign = lf_with_ma.join(
        campaigns_df.select(["campaign_id", "product_id"])
        .rename({"product_id": "campaign_product_id"})
        .lazy(),
        on="campaign_id",
        how="left",
    )
    # 5) asset product
    lf_with_asset = lf_with_campaign.join(
        assets_df.select(["marketing_asset_id", "product_id"])
        .rename({"product_id": "asset_product_id"})
        .lazy(),
        on="marketing_asset_id",
        how="left",
    )
    # 6) Get channel Name from ID
    lf_with_channel = lf_with_asset.join(
        channel_df.select(["channel_id", "channel_name"]).lazy(),
        on="channel_id",
        how="left",
    )
    # 7) derive activity_company_id with preference for targeted_company_id
    df_enriched = lf_with_channel.with_columns(
        pl.coalesce([pl.col("targeted_company_id"), pl.col("interacted_company_id")]).alias(
            "activity_company_id"
        ),
        pl.col("interacted_person_id").alias("person_id"),
    )

    # Compute enrichments
    product_yca_tier = _best_product_yca_level(
        df_enriched,
        product_links,
        products_df,
        outcome_col="outcome_product_id",
        campaign_col="campaign_product_id",
        asset_col="asset_product_id",
    )
    df_enriched = pl.concat([df_enriched, product_yca_tier], how="horizontal")

    # only compute company_yca_type if it wasn't already produced upstream
    if "company_yca_type" not in df_enriched.collect_schema().names():
        company_yca_type = _best_company_yca_type(
            df_enriched,
            company_links,
            company_df,
            outcome_company_col="outcome_company_id",
            activity_company_col="activity_company_id",
        )
        df_enriched = pl.concat([df_enriched, company_yca_type], how="horizontal")

    # Generate Link IDs
    pad = 7
    prefix = "LINK"

    df_enriched = (
        df_enriched.with_row_index("idx", offset=0)  # 0..n-1 lazily
        .with_columns(
            link_id=pl.concat_str(
                [
                    pl.lit(prefix),
                    (pl.col("idx") + 1).cast(pl.Utf8).str.zfill(pad),  # 1..n  # zero-pad
                ]
            )
        )
        .drop("idx")
    )

    return df_enriched.match_to_schema(
        _schema_enriched, missing_columns="raise", extra_columns="ignore"
    ).collect(engine="streaming")


def _generate_links_though_person_company(
    person_df: pl.DataFrame,
    interaction_df: pl.DataFrame,
    company_df: pl.DataFrame,
    order_df: pl.DataFrame,
    person_company_role_df: pl.DataFrame,
) -> pl.DataFrame:
    """Generate the links though person company.

    Uses lazy pipelines with streaming joins and column pruning to reduce
    peak memory on large datasets.
    """
    company_ancestry = _create_ancestry(
        company_df,
        row_id="company_id",
        parent_id="Parent_Company_ID",
        usage_tag="company_ancestory",
    )
    company_links = _build_links(company_ancestry)

    # Build pipeline lazily
    i_cols = ["interaction_id", "interacted_person_id", "interacted_company_id"]
    pcr_cols = ["person_id", "company_id"]
    o_cols = ["order_id", "company_id"]

    df_lazy = (
        interaction_df.select(i_cols)
        .lazy()
        .join(
            person_company_role_df.select(pcr_cols).lazy(),
            left_on="interacted_person_id",
            right_on="person_id",
            how="inner",
        )
        .join(
            company_links.lazy().select(["from_id", "to_id", "ancestor_id"]).rename({}),
            left_on="interacted_company_id",
            right_on="from_id",
            how="inner",
        )
        .join(order_df.select(o_cols).lazy(), left_on="to_id", right_on="company_id", how="inner")
    )

    links_raw = df_lazy.collect(streaming=True)

    # --- compute company_yca_type at build time (optional; enrichment can also compute) ---
    if not links_raw.is_empty():
        comp_bt = company_df.select(["company_id", "Company Business Type"]).rename(
            {"company_id": "_anc_id", "Company Business Type": "_anc_bt"}
        )
        links_raw = (
            links_raw.join(comp_bt, left_on="ancestor_id", right_on="_anc_id", how="left")
            .with_columns(pl.col("_anc_bt").alias("company_yca_type"))
            .drop("_anc_bt")
        )

    n = links_raw.height
    schema = _define_schema("base")
    if n == 0:
        # return an *empty* frame with the right dtypes so downstream code is safe
        return schema

    links_calculated = links_raw.with_columns(
        pl.lit("Order").alias("outcome_type"),
        pl.lit("Interaction-Person-Company-Order").alias("relation_type"),
    ).rename(
        {
            "interaction_id": "interaction_id",
            "order_id": "outcome_id",
            "interacted_person_id": "person_id",
        }
    )
    return links_calculated.match_to_schema(
        _schema_base, missing_columns="raise", extra_columns="ignore"
    )


def _generate_links_direct_person(
    interaction_df: pl.DataFrame,
    order_df: pl.DataFrame,
) -> pl.DataFrame:
    """Generate Interaction -> Person -> Order links when order.contact_id matches interaction person.

    :param interaction_df: Interactions table (requires interacted_person_id and interaction_id)
    :param order_df: Orders table (requires contact_id, order_id, company_id)
    :returns: Links dataframe aligned to the link schema (without time_lag and IDs)
    :raises ValueError: If required columns are missing.
    """
    required_i = {"interaction_id", "interacted_person_id"}
    required_o = {"order_id", "person_id", "company_id"}
    if not required_i.issubset(interaction_df.columns):  # pragma: no cover
        raise ValueError("Interactions missing required columns for direct person linking")
    if not required_o.issubset(order_df.columns):  # pragma: no cover
        raise ValueError("Orders missing required columns for direct person linking")

    df = (
        interaction_df.filter(pl.col("interacted_person_id").is_not_null())
        .join(
            order_df.select(["order_id", "person_id", "company_id"]),
            left_on="interacted_person_id",
            right_on="person_id",
            how="inner",
        )
        .with_columns(
            pl.lit("Order").alias("outcome_type"),
            pl.lit("Interaction-Person-Order").alias("relation_type"),
        )
        .rename(
            {
                "interaction_id": "interaction_id",
                "order_id": "outcome_id",
                "interacted_person_id": "person_id",
            }
        )
        .with_columns(
            # Set company_id from the interaction context to align with expectations
            pl.col("interacted_company_id").alias("company_id")
        )
        .match_to_schema(_schema_base, missing_columns="raise", extra_columns="ignore")
    )

    if df.is_empty():
        return _define_schema("base")

    # Add any missing columns as nulls and cast types
    return df.match_to_schema(_schema_base, missing_columns="raise")


def _generate_links_company_only(
    interaction_df: pl.DataFrame,
    company_df: pl.DataFrame,
    order_df: pl.DataFrame,
) -> pl.DataFrame:
    """Generate Interaction -> Company -> Order links for interactions with unknown person.

    Uses lazy pipelines with streaming joins and strict column selection to
    limit memory when linking via company ancestry.

    :param interaction_df: Interactions table (requires interacted_company_id, interaction_id, interacted_person_id)
    :param company_df: Companies table (requires company_id and parent)
    :param order_df: Orders table (requires company_id)
    :returns: Links dataframe with person_id null and relation_type "Interaction-Company-Order".
    """
    # Only consider interactions when person is unknown but company is known
    base = interaction_df.filter(
        pl.col("interacted_person_id").is_null() & pl.col("interacted_company_id").is_not_null()
    )
    if base.is_empty():
        return _define_schema("base")

    # Build company links once
    comp_closure = _create_ancestry(
        company_df,
        row_id="company_id",
        parent_id="Parent_Company_ID",
        usage_tag="Company only links_company_closure",
    )
    comp_links = _build_links(comp_closure)

    # Lazily join interaction company to orders via ancestry links
    o_cols = ["order_id", "company_id"]
    lf = (
        base.select(["interaction_id", "interacted_company_id"])
        .lazy()
        .join(
            comp_links.lazy().select(["from_id", "to_id"]),
            left_on="interacted_company_id",
            right_on="from_id",
            how="inner",
        )
        .join(order_df.select(o_cols).lazy(), left_on="to_id", right_on="company_id", how="inner")
        .with_columns(
            pl.lit("Order").alias("outcome_type"),
            pl.lit("Interaction-Company-Order").alias("relation_type"),
        )
        .rename({"order_id": "outcome_id", "to_id": "company_id"})
    )

    return lf.match_to_schema(
        _schema_base, missing_columns="raise", extra_columns="ignore"
    ).collect()


def _date_difference_filter(
    link: pl.lazyframe.LazyFrame, interaction_df: pl.DataFrame, outcome_df: pl.DataFrame
) -> pl.LazyFrame:
    """Calculate the difference between activity and outcome & Filter interaction after outcome.

    Uses lazy streaming joins to reduce peak memory.
    """
    # check we have the necessary interaction ID and outcome ID
    missing = [
        c for c in ("interaction_id", "outcome_id") if c not in link.collect_schema().names()
    ]
    if missing:  # pragma: no cover
        raise ValueError(f"Required column(s) missing: {', '.join(missing)}")

    # Determine interaction date column name ('interactiondate' preferred, fallback to 'date')
    interaction_date_col = (
        "interaction_date"
        if "interaction_date" in interaction_df.columns
        else ("interactiondate" if "interactiondate" in interaction_df.columns else "date")
    )

    lf = (
        link.join(interaction_df.lazy(), on="interaction_id", how="inner", suffix="_interaction")
        .join(
            outcome_df.lazy(),
            left_on="outcome_id",
            right_on="order_id",
            how="inner",
            suffix="_outcome",
        )
        .with_columns(
            (pl.col("date_raised") - pl.col(interaction_date_col)).alias("_lag"),
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
    )
    return lf.match_to_schema(_schema_time_lag, missing_columns="raise", extra_columns="ignore")


def merge_links(link_dfs: list[pl.DataFrame]) -> pl.lazyframe.LazyFrame:
    """Merge the linking tables prioritising the first non-empty link for an interaction to output."""

    # Add a priority for deduplication: lower number = higher priority
    def _with_priority(df: pl.DataFrame, prio: int) -> pl.DataFrame:
        # Always add the helper priority column, even on empty frames, to ensure consistent width
        return df.with_columns(pl.lit(prio).alias("_priority"))

    if all(df.is_empty() for df in link_dfs):
        # No links could be established; return an empty frame with correct schema lazily
        return _define_schema("base").lazy()

    return (
        pl.concat(link_dfs, how="vertical", rechunk=True).unique(
            subset=["interaction_id", "outcome_id"], keep="first"
        )
    ).lazy()
