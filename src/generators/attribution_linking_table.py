"""Contains testing for the generate attribution linking table function and its helper functions."""

from typing import Any

import polars as pl

__all__ = ["generate"]


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
    schema = [
        ("link_id", pl.String),
        ("activity_id", pl.String),
        ("interaction_id", pl.String),
        ("outcome_type", pl.String),
        ("outcome_id", pl.String),
        ("company_id", pl.String),
        ("person_id", pl.String),
        ("relation_type", pl.String),
        ("time_lag", pl.Int64),  # use pl.Float64 if you expect fractional lags
    ]

    # Create an empty DataFrame
    return pl.DataFrame(schema=schema)


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate the attribution linking table deterministically from existing data."""
    # prior: dict[str, pl.DataFrame] = kwargs.get("prior", {})

    # pull_activity_df = prior.get("pull_activity_df")
    # push_activity_df = prior.get("push_activity_df")
    # interaction_df = prior.get("interaction_df")
    # person_df = prior.get("person_df")
    # company_df = prior.get("company_df")
    # order_df = prior.get("order_df")
    return _define_schema()


def _generate_links_though_person_company(person_df: pl.DataFrame) -> pl.DataFrame:
    pass
