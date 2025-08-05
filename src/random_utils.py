"""Utilities for generating random data."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Sequence, TypeVar, Optional, Tuple, Dict, List

from numpy.random import Generator, default_rng
from faker import Faker

import polars as pl

__all__ = [
    "fake",
    "generate_source_id_mappings",
    "make_ids",
    "random_date",
    "seed_everything",
]

# Module-level Faker instance and NumPy Generator
fake = Faker("en_GB")
_rng: Generator = default_rng(42)

# ------------------------------------------------------------------
START_DT = datetime(2024, 1, 1)
END_DT = datetime(2025, 6, 30)
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
    """
    out: list[str | None] = []
    for _ in range(n):
        if none_rate > 0 and random.random() < none_rate:
            out.append(None)
        else:
            out.append(random.choice(source_ids))
    return out


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


def generate_source_id_mappings(
    sources: list[tuple[str, str]], n: int, seed: int = 42
) -> pl.DataFrame:
    """Generate a dummy mapping of source IDs across multiple source tables.

    :param sources: List of (source_table, source_id_field) pairs.
    :param n: Total number of rows to generate.
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
