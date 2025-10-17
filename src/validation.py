"""Validation utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

__all__ = [
    "ensure_output_dir",
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
