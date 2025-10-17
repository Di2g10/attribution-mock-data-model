"""Contains testing for the generate attribution linking table function and its helper functions."""

from typing import Any

import polars as pl

__all__ = ["generate"]

from src.random_utils import make_ids

_schema = [
    ("link_id", pl.String),
    ("marketing_activity_id", pl.String),
    ("interaction_id", pl.String),
    ("outcome_type", pl.String),
    ("outcome_id", pl.String),
    ("company_id", pl.String),
    ("person_id", pl.String),
    ("relation_type", pl.String),
    ("product_yca_tier", pl.String),
    ("company_yca_type", pl.String),
    ("time_lag", pl.Int64),
    # Additional fields expected by spreadsheet
    ("interaction_type", pl.String),
    ("channel", pl.String),
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

    This implementation uses Polars lazy with streaming joins to reduce peak
    memory during construction for large hierarchies.
    """
    a = closure.lazy().rename({"origin_id": "node_a", "distance": "dist_a"})
    b = closure.lazy().rename({"origin_id": "node_b", "distance": "dist_b"})

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
        .select(["node_a", "node_b", "ancestor_id", "degrees"])
    )

    # make symmetric and align columns

    # enforce identical column order before stacking
    wanted_cols = ["from_id", "to_id", "ancestor_id", "degrees"]

    links_min_df = links_min.collect(streaming=True)
    df1 = links_min_df.rename({"node_a": "from_id", "node_b": "to_id"}).select(wanted_cols)
    df2 = links_min_df.rename({"node_a": "to_id", "node_b": "from_id"}).select(wanted_cols)
    # Remove any duplicated ordered pairs (e.g., self-pairs A==B would appear twice)
    return pl.concat([df1, df2], how="vertical").unique().sort(["from_id", "to_id"])


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


def generate(n: int, **kwargs: Any) -> pl.DataFrame:  # noqa: PLR0915
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

    interaction_df = _require_df(prior.get("Interactions"), "Interaction")
    person_df = _require_df(prior.get("Person"), "Person")
    company_df = _require_df(prior.get("Company"), "Company")
    order_df = _require_df(prior.get("Orders"), "Order")
    person_company_role_df = _require_df(prior.get("Person Company Role"), "Person Company Role")

    # Build all link types
    direct_person_links = _generate_links_direct_person(interaction_df, order_df)
    person_company_link_df = _generate_links_though_person_company(
        person_df, interaction_df, company_df, order_df, person_company_role_df
    )
    company_only_links = _generate_links_company_only(interaction_df, company_df, order_df)

    # Add a priority for deduplication: lower number = higher priority
    def _with_priority(df: pl.DataFrame, prio: int) -> pl.DataFrame:
        # Always add the helper priority column, even on empty frames, to ensure consistent width
        return df.with_columns(pl.lit(prio).alias("_priority"))

    stacked = (
        pl.concat(
            [
                _with_priority(direct_person_links, 0),
                _with_priority(person_company_link_df, 1),
                _with_priority(company_only_links, 2),
            ],
            how="vertical",
            rechunk=True,
        )
        if (
            not direct_person_links.is_empty()
            or not person_company_link_df.is_empty()
            or not company_only_links.is_empty()
        )
        else _define_schema().with_columns(pl.lit(1).alias("_priority"))
    )

    # Deduplicate per (interaction_id, outcome_id) keeping highest priority then drop helper
    combined_links = (
        stacked.sort(["_priority"])
        .unique(subset=["interaction_id", "outcome_id"], keep="first")
        .drop("_priority")
    )

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

        # Bring in product IDs and company IDs using a lazy, streaming pipeline
        rows = (
            filtered_links.lazy()
            # 1) outcome product and company via Orders
            .join(
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
            .join(
                interaction_df.select(
                    ["interaction_id", "marketing_activity_id", "interacted_company_id"]
                ).lazy(),
                on="interaction_id",
                how="left",
                suffix="_i",
            ).with_columns(
                pl.coalesce(
                    [pl.col("marketing_activity_id_i"), pl.col("marketing_activity_id")]
                ).alias("marketing_activity_id")
            )
            # 3) campaign/asset and targeted_company_id via Marketing Activity
            .join(
                marketing_activity_df.select(
                    [
                        "marketing_activity_id",
                        "campaign_id",
                        "marketing_asset_id",
                        "targeted_company_id",
                    ]
                ).lazy(),
                left_on="marketing_activity_id",
                right_on="marketing_activity_id",
                how="left",
            )
            # 4) campaign product
            .join(
                campaigns_df.select(["campaign_id", "product_id"])
                .rename({"product_id": "campaign_product_id"})
                .lazy(),
                on="campaign_id",
                how="left",
            )
            # 5) asset product
            .join(
                assets_df.select(["marketing_asset_id", "product_id"])
                .rename({"product_id": "asset_product_id"})
                .lazy(),
                on="marketing_asset_id",
                how="left",
            )
            # 6) derive activity_company_id with preference for targeted_company_id
            .with_columns(
                pl.coalesce([pl.col("targeted_company_id"), pl.col("interacted_company_id")]).alias(
                    "activity_company_id"
                )
            )
        ).collect(streaming=True)

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

    # Bring across activity and interaction descriptors
    try:
        inter_cols = [
            c
            for c in ("interaction_id", "marketing_activity_id", "interaction_type")
            if c in interaction_df.columns
        ]
        addl = interaction_df.select(inter_cols)
        enriched = enriched.join(addl, on="interaction_id", how="left").with_columns(
            pl.lit(None).cast(pl.String).alias("channel"),
        )
    except Exception:
        # If join fails, still ensure columns exist
        enriched = enriched.with_columns(
            pl.lit(None).cast(pl.String).alias("interaction_type"),
            pl.lit(None).cast(pl.String).alias("channel"),
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
    """Generate the links though person company.

    Uses lazy pipelines with streaming joins and column pruning to reduce
    peak memory on large datasets.
    """
    company_ancestry = _create_ancestry(
        company_df, row_id="company_id", parent_id="Parent_Company_ID"
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
    schema = _define_schema()
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
    return (
        links_calculated.with_columns(
            [
                pl.lit(None).cast(dt).alias(col)
                for col, dt in _schema
                if col not in links_calculated.columns
            ]
        )
        .select([col for col, _ in _schema])
        .with_columns(
            pl.col("time_lag").cast(pl.Int64),
            pl.all().exclude("time_lag").cast(pl.String),
        )
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
    required_o = {"order_id", "contact_id", "company_id"}
    if not required_i.issubset(interaction_df.columns):  # pragma: no cover
        raise ValueError("Interactions missing required columns for direct person linking")
    if not required_o.issubset(order_df.columns):  # pragma: no cover
        raise ValueError("Orders missing required columns for direct person linking")

    df = (
        interaction_df.filter(pl.col("interacted_person_id").is_not_null())
        .join(
            order_df.select(["order_id", "contact_id", "company_id"]),
            left_on="interacted_person_id",
            right_on="contact_id",
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
                # keep company_id from Orders join
            }
        )
        .select(
            [
                col
                for col, _ in _schema
                if col
                in (
                    "interaction_id",
                    "outcome_type",
                    "outcome_id",
                    "company_id",
                    "person_id",
                    "relation_type",
                )
            ]
        )
    )

    if df.is_empty():
        return _define_schema()

    # Add any missing columns as nulls and cast types
    return (
        df.with_columns(
            [pl.lit(None).cast(dt).alias(col) for col, dt in _schema if col not in df.columns]
        )
        .select([name for name, _ in _schema])
        .with_columns(
            pl.col("time_lag").cast(pl.Int64),
            pl.all().exclude("time_lag").cast(pl.String),
        )
    )


essential_company_cols = ["company_id", "Parent_Company_ID", "Company Business Type"]


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
    # Only consider interactions where person is unknown but company is known
    base = interaction_df.filter(
        pl.col("interacted_person_id").is_null() & pl.col("interacted_company_id").is_not_null()
    )
    if base.is_empty():
        return _define_schema()

    # Build company links once
    comp_closure = _create_ancestry(company_df, row_id="company_id", parent_id="Parent_Company_ID")
    comp_links = _build_links(comp_closure)

    # Lazily join interaction company to orders via ancestry links
    o_cols = ["order_id", "company_id"]
    df_lazy = (
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
        .rename({"order_id": "outcome_id"})
    )

    df = df_lazy.collect(streaming=True).with_columns(pl.col("to_id").alias("company_id"))

    # Keep schema-relevant columns; person_id null
    df2 = df.select(
        [
            pl.col("interaction_id"),
            pl.col("outcome_type"),
            pl.col("outcome_id"),
            pl.col("company_id"),  # from Orders
            pl.lit(None).cast(pl.String).alias("person_id"),
            pl.col("relation_type"),
        ]
    )

    return (
        df2.with_columns(
            [pl.lit(None).cast(dt).alias(col) for col, dt in _schema if col not in df2.columns]
        )
        .select([name for name, _ in _schema])
        .with_columns(
            pl.col("time_lag").cast(pl.Int64),
            pl.all().exclude("time_lag").cast(pl.String),
        )
    )


def _date_difference_filter(
    link: pl.DataFrame, interaction_df: pl.DataFrame, outcome_df: pl.DataFrame
) -> pl.DataFrame:
    """Calculate the difference between activity and outcome & Filter interaction after outcome.

    Uses lazy streaming joins to reduce peak memory.
    """
    # check we have the necessary interaction ID and outcome ID
    missing = [c for c in ("interaction_id", "outcome_id") if c not in link.columns]
    if missing:  # pragma: no cover
        raise ValueError(f"Required column(s) missing: {', '.join(missing)}")

    # Determine interaction date column name ('interactiondate' preferred, fallback to 'date')
    interaction_date_col = (
        "interactiondate" if "interactiondate" in interaction_df.columns else "date"
    )

    lf = (
        link.lazy()
        .join(interaction_df.lazy(), on="interaction_id", how="inner", suffix="_interaction")
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
        # 3. final column order
        .select([name for name, _ in _schema])
    )
    return lf.collect(streaming=True)
