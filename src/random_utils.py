"""Utilities for generating random data."""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta
from typing import Sequence, TypeVar, Optional, Tuple, Dict, List, Any, Mapping

from numpy.random import Generator, default_rng
from faker import Faker

import polars as pl

__all__ = [
    "fake",
    "generate_mapped_values",
    "generate_source_id_mappings",
    "make_ids",
    "make_ids_with_duplicates",
    "random_date",
    "require_df",
    "seed_everything",
    "weighted_sample",
]

# Module-level Faker instance and NumPy Generator
fake = Faker("en_GB")
_rng: Generator = default_rng(42)

# ------------------------------------------------------------------
START_DT = datetime(2024, 1, 1)
END_DT = datetime(2025, 12, 30)
_DATE_RANGE_DAYS = (END_DT - START_DT).days


def seed_everything(seed: int | None = None) -> None:
    """Re-seed Python's random, NumPy's Generator, and Faker to make all randomness reproducible."""
    global _rng  # noqa: PLW0603
    seed = seed if seed is not None else 42

    # Python stdlib
    random.seed(seed)

    # NumPy's new Generator
    _rng = default_rng(seed)

    # Faker
    fake.seed_instance(seed)


def random_date() -> datetime:
    """Return a random datetime within the global range, using the new RNG."""
    days = int(_rng.integers(0, _DATE_RANGE_DAYS + 1))
    secs = int(_rng.integers(0, 86_400))
    return START_DT + timedelta(days=days, seconds=secs)


def make_ids(n: int, prefix: str) -> list[str]:
    """Generate sequential IDs with zero-padded integers."""
    return [f"{prefix}{i:07d}" for i in range(1, n + 1)]


def make_ids_with_duplicates(
    source_ids: Sequence[str],
    n: int,
    none_rate: float = 0.0,
) -> list[str | None]:
    """Produce a list of length n by sampling from source_ids with replacement.

    With probability `none_rate` each slot will be None instead of an ID.

    Performance optimizations:
    - Uses NumPy's vectorized random operations for better performance with large n
    - Generates all random values at once instead of in a loop
    - Handles the None case efficiently with vectorized operations
    """
    if not source_ids:
        return [None] * n

    # Use numpy's vectorized random operations for better performance
    if none_rate <= 0:
        # PERFORMANCE OPTIMIZATION: Generate all indices at once
        # Instead of calling random.choice n times in a loop, we generate
        # all random indices in a single vectorized operation
        indices = _rng.integers(0, len(source_ids), size=n)
        return [source_ids[i] for i in indices]
    # PERFORMANCE OPTIMIZATION: Vectorized handling of None values
    # Generate a boolean mask for None values in a single operation
    none_mask = _rng.random(n) < none_rate
    none_count = none_mask.sum()

    # Generate indices for non-None values all at once
    indices = _rng.integers(0, len(source_ids), size=n - none_count)

    # Create the result list
    result: list[str | None] = [None] * n
    non_none_idx = 0

    # This loop is still needed to map the indices to the right positions
    # based on the none_mask, but we've minimized the random operations
    for i in range(n):
        if none_mask[i]:
            result[i] = None
        else:
            result[i] = source_ids[indices[non_none_idx]]
            non_none_idx += 1

    return result


T = TypeVar("T")


def weighted_sample(
    population: Sequence[T], weights: Optional[Sequence[float]] = None, n: int = 1
) -> list[T]:
    """Return n samples from population with the given weights.

    Each pick is independent and with replacement.
    If weights are not provided, uniform weights will be used.
    """
    if weights is None:
        # Create uniform weights if none provided
        weights = [1.0] * len(population)
    return random.choices(population, weights=weights, k=n)


def generate_mapped_values(
    parent_values: Sequence[str],
    mapping_dict: Mapping[str, Sequence[Any]],
    verbose: bool = False,
) -> list[Any]:
    """Generate child values based on parent categories using a mapping dictionary.

    This function efficiently maps parent categories to child values using a provided mapping dictionary.
    It optimizes performance by using NumPy's vectorized operations and pre-generating values.

    This is a generic helper function that can be used in various scenarios where you need to map
    parent categories to child values, such as:
    - Generating industries based on verticals (as in company.py)
    - Generating interaction types based on channels (as in interactions.py)
    - Any other case where you have a parent-child relationship defined by a mapping dictionary

    :param parent_values: List of parent category values (e.g., channels, verticals)
    :param mapping_dict: Dictionary mapping parent categories to lists of possible child values
    :param fallback_values: Values to use when a parent category is not in the mapping dictionary
    :returns: List of child values corresponding to each parent category

    Performance optimizations:
    - Uses NumPy's vectorized operations for better performance with large datasets
    - Pre-generates and reuses values instead of generating them on-demand
    - Minimizes individual random calls
    - Efficiently handles large datasets by batching operations

    Example usage:
    ```python
    # Generate industries based on verticals
    industries = generate_mapped_values(
        parent_values=verticals,
        mapping_dict=VERTICALS_TO_INDUSTRIES
    )

    # Generate interaction types based on channels with fallback values
    interaction_types = generate_mapped_values(
        parent_values=channels,
        mapping_dict=CHANNEL_INTERACTION_TYPES,
        fallback_values=FALLBACK_INTERACTION_TYPES
    )
    ```
    """
    if verbose:
        start_total = time.perf_counter()

    # If no parent values, return empty list
    if not parent_values:
        return []

    # If mapping_dict is empty and no fallback, return None for each parent
    if not mapping_dict:
        return [None] * len(parent_values)

    # Pre-generate child values for each parent category
    if verbose:
        start_pregen = time.perf_counter()

    # Pre-generate child values for each parent category
    child_map: dict[str, list[Any]] = {}
    n_values = len(parent_values)

    for parent, child_values in mapping_dict.items():
        if not child_values:
            # Skip empty child value lists
            continue

        # For each parent, randomly select child values using vectorized operations
        # Generate enough values to handle the worst case where all parents are the same
        n_values = len(parent_values)
        indices = _rng.integers(0, len(child_values), size=n_values)
        child_map[parent] = [child_values[i] for i in indices]

    if verbose:
        print(f"  Pre-generation: {time.perf_counter() - start_pregen:.4f}s")
        start_mapping = time.perf_counter()

    # Map each parent to its pre-generated child value
    result: list[Any] = []
    parent_counts: dict[str, int] = {}

    for parent in parent_values:
        # Keep track of how many times we've seen this parent
        parent_counts[parent] = parent_counts.get(parent, 0) + 1
        count = parent_counts[parent]

        if child_map.get(parent):
            # Use modulo to cycle through the pre-generated child values if needed
            result.append(child_map[parent][(count - 1) % len(parent_values)])
        else:
            # No mapping and no fallback
            result.append(None)
    if verbose:
        print(f"  Mapping: {time.perf_counter() - start_mapping:.4f}s")
        print(f"  Total: {time.perf_counter() - start_total:.4f}s")

    return result


def generate_source_id_mappings(
    sources: list[tuple[str, str]], n: int, seed: int = 42
) -> pl.DataFrame:
    """Generate a dummy mapping of source IDs across multiple source tables.

    :param sources: List of (source_table, source_id_field) pairs.
    :param n: Total number of lf to generate.
    :param seed: Random seed for reproducibility.
    :returns: Polars DataFrame with columns: ``Source Table``, ``Source ID Field``, ``Source ID``.
    """
    random.seed(seed)

    # Pre-generate IDs for each source table
    id_pools: Dict[Tuple[str, str], List[str]] = {
        (table, field): make_ids(n * 10, prefix=table[:3].upper()) for table, field in sources
    }

    # Track how many IDs we have used per source
    usage_tracker: Dict[Tuple[str, str], int] = {key: 0 for key in id_pools}

    # Explicit type so mypy is happy
    data: Dict[str, List[str]] = {
        "source_table": [],
        "source_id_field": [],
        "source_id": [],
    }

    for _ in range(n):
        table, field = random.choice(sources)
        key: Tuple[str, str] = (table, field)
        idx = usage_tracker[key]

        # Safeguard in case we go over
        if idx >= len(id_pools[key]):
            continue  # or raise if you prefer strict behaviour

        data["source_table"].append(table)
        data["source_id_field"].append(field)
        data["source_id"].append(id_pools[key][idx])
        usage_tracker[key] += 1

    return pl.DataFrame(data)


def require_df(value: Any, name: str) -> pl.DataFrame:
    """Check value is of type dataframe raising informative error on failure."""
    if not isinstance(value, pl.DataFrame):
        raise TypeError(f"Expected DataFrame for {name}, got {type(value).__name__}")
    return value
