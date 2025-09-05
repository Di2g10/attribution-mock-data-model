"""Script for Adhock Checks."""

from pathlib import Path

import polars as pl


def main() -> None:
    """Check the distribution of relation types in the attribution linking table."""
    file = Path(__file__).parent.parent / "mock_output" / "Attribution Linking Table.csv"

    print(file)
    df = pl.read_csv(file)

    # group by relation_type, count occurrences, sort descending
    result = (
        df.group_by("relation_type")
        .agg(pl.count().alias("count"))
        .sort("count", descending=True)
        .with_columns(
            pl.col("relation_type").alias("relation_type"),
            pl.col("count").cast(pl.Int64).alias("count"),
        )
        .with_columns((pl.col("count") / pl.col("count").sum() * 100).alias("percentage"))
    )

    print(result)


if __name__ == "__main__":
    main()
