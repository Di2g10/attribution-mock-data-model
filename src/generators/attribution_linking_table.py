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
    return pl.concat([df1, df2]).sort(["from_id", "to_id"])


def _define_schema() -> pl.DataFrame:
    """Define the Expected return schema."""
    # Create an empty DataFrame
    return pl.DataFrame(schema=_schema)


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate the attribution linking table deterministically from existing data."""
    prior: dict[str, pl.DataFrame] = kwargs.get("prior", {})

    interaction_df = prior.get("Interactions")
    person_df = prior.get("Person")
    company_df = prior.get("Company")
    order_df = prior.get("Orders")
    person_company_role_df = prior.get("Person Company Role")

    person_company_link_df = _generate_links_though_person_company(
        person_df, interaction_df, company_df, order_df, person_company_role_df
    )
    # Generate other link objects e.g. Interaction -> Company, Interaction -> Order

    combined_links = person_company_link_df  # Concatentate these once others created

    # Filter on dates and add date difference
    filtered_links = _date_difference_filter(combined_links, interaction_df, order_df)

    # Add activity IDs

    # Add person IDs

    # Add Product Distance

    # Generate Link IDs
    link_ids = pl.Series("link_id", make_ids(filtered_links.height, "LINK"))

    return filtered_links.with_columns(link_ids)


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
