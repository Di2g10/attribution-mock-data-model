"""Validation utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

__all__ = [
    "compute_population_rates",
    "ensure_output_dir",
    "print_population_rates",
    "validate_object",
]

from src.schema_registry import SchemaRegistry


def validate_object(
    df: pl.DataFrame,
    name: str,
    registry: SchemaRegistry,
    prior: Any,
    *,
    skip_row_count: bool = False,
) -> None:
    """Check that the DataFrame matches the schema.

    Placeholder for FK & uniqueness checks (expand later).

    :param df: Generated DataFrame to validate.
    :param name: Object name.
    :param registry: Schema registry for configured expectations.
    :param prior: Previously generated objects (for FK checks in future).
    :param skip_row_count: When True, do not enforce strict row count checks.
    :raises ValueError: If validation fails.
    """
    if not skip_row_count and not registry.check_row_count(name, df.height):
        raise ValueError(f"{name}: expected {registry.row_count(name)} rows, got {df.height}")


def ensure_output_dir(path: str | Path, overwrite: bool) -> None:
    """Ensure the output directory exists."""
    p = Path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(f"{p} exists; set overwrite=True or choose another directory")
    p.mkdir(parents=True, exist_ok=True)


def extract_id_column(df: Any, id_field: str) -> list[str]:
    """Validate a Polars DataFrame and extracts a list of IDs from the specified field.

    Args:
        df: The object expected to be a Polars DataFrame.
        id_field: The name of the ID column to extract.

    Returns:
        A list of string IDs from the specified column.

    Raises:
        TypeError: If df is not a Polars DataFrame.
        ValueError: If id_field is not present in the DataFrame.

    """
    if not isinstance(df, pl.DataFrame):
        raise TypeError("Expected a Polars DataFrame.")

    if id_field not in df.columns:
        raise ValueError(f"'{id_field}' column not found in DataFrame.")

    return df.get_column(id_field).to_list()


def compute_population_rates(output_path: str | Path) -> pl.DataFrame:
    """Compute population rates (non-null counts) for each field in each CSV file.

    :param output_path: Directory containing CSV files to analyse (e.g., 'mock_output').
    :raises FileNotFoundError: If the directory does not exist or has no CSV files.
    :returns: A tidy Polars DataFrame with columns:
        - file: CSV file name
        - field: Column name within the CSV
        - total_rows: Total number of rows in the CSV
        - populated: Number of non-null values for the column
        - pct_populated: populated / total_rows as a float in [0, 1]
    """
    p = Path(output_path)
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Directory not found: {p}")

    csv_files = sorted([f for f in p.iterdir() if f.suffix.lower() == ".csv"])
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {p}")

    summaries: list[pl.DataFrame] = []

    for csv in csv_files:
        # Discover columns cheaply without loading the file
        try:
            schema_probe = pl.read_csv(csv, n_rows=0)
            columns = list(schema_probe.columns)
        except Exception as exc:
            # Skip unreadable files with a clear message but continue others
            print(f"[population] warning: could not read schema for {csv.name}: {exc}")
            continue

        if not columns:
            continue

        # Build lazy scan for efficient counting on large files
        lf = pl.scan_csv(csv)
        total_rows = lf.select(pl.len().alias("__rows__")).collect().item()

        # Compute non-null counts per column in one pass
        exprs = [pl.col(col).is_not_null().sum().alias(col) for col in columns]
        non_null_counts_wide = lf.select(exprs).collect()
        # Unpivot to long format: column -> populated
        long = non_null_counts_wide.unpivot(variable_name="field", value_name="populated")
        long = long.with_columns(
            [
                pl.lit(csv.name).alias("file"),
                pl.lit(int(total_rows)).alias("total_rows"),
            ]
        )
        # Compute percentage in a separate step to avoid self-reference issues
        long = long.with_columns(
            (pl.col("populated").cast(pl.Int64) / pl.col("total_rows").cast(pl.Float64)).alias(
                "pct_populated"
            )
        ).select(["file", "field", "total_rows", "populated", "pct_populated"])

        summaries.append(long)

    if not summaries:
        raise FileNotFoundError(f"No analysable CSV files found in: {p}")

    return pl.concat(summaries, how="vertical_relaxed")


def print_population_rates(output_path: str | Path) -> None:
    """Pretty-print population rates for all CSVs in a directory.

    :param output_path: Directory containing CSV files (e.g., 'mock_output').
    :returns: None. Prints a concise summary grouped by file.
    """
    df = compute_population_rates(output_path)

    # Group by file and print a small table per file
    for file_name in df.select("file").unique().to_series().to_list():
        print(f"\n=== {file_name} ===")
        sub = df.filter(pl.col("file") == file_name).sort([pl.col("pct_populated")])
        # Show as: field, populated/total, pct%
        for row in sub.iter_rows(named=True):
            pct = float(row["pct_populated"]) * 100 if row["total_rows"] else 0.0
            print(f"{row['field']}: {row['populated']}/{row['total_rows']} populated ({pct:.1f}%)")
