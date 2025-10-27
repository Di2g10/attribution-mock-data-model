"""Contains Test of the company role generator module."""

import unittest
import polars as pl

from src.generators.person_company_role import generate as generate_person_company_role

LARGE_SAMPLE_SIZE = 20  # keep or reuse existing constant if already defined elsewhere


def _first_present(df: pl.DataFrame, candidates: list[str]) -> str:
    """Return the first matching column name present in df."""
    for c in candidates:
        if c in df.columns:
            return c
    raise AssertionError(f"Expected one of {candidates} in columns: {df.columns}")


def _minimal_prior_people_companies(n: int) -> dict[str, pl.DataFrame]:
    """Minimal prior containing Person and Company IDs."""
    persons = pl.DataFrame({"person_id": [f"PER{str(i).zfill(7)}" for i in range(1, n + 1)]})
    companies = pl.DataFrame({"company_id": [f"CO{str(i).zfill(7)}" for i in range(1, n + 1)]})
    # Provide both Title Case and snake_case keys for safety, if generators vary
    return {
        "Person": persons,
        "Company": companies,
        "person": persons,
        "company": companies,
    }


class TestPersonCompanyRole(unittest.TestCase):
    """Tests for the Person Company Role generator."""

    def setUp(self) -> None:
        """Create prior needed for tests."""
        self.prior = _minimal_prior_people_companies(LARGE_SAMPLE_SIZE)

    def test_person_company_role_dates(self) -> None:
        """Start date must precede end date when end date is present."""
        df = generate_person_company_role(LARGE_SAMPLE_SIZE, prior=self.prior)

        start_col = _first_present(df, ["start_date", "Start Date"])
        end_col = _first_present(df, ["end_date", "End Date"])

        with_end = df.filter(pl.col(end_col).is_not_null())
        if with_end.height == 0:
            # No bounded roles; nothing to assert on ordering.
            return

        ok = with_end.select(pl.col(start_col) < pl.col(end_col)).to_series().all()
        self.assertTrue(ok, "Found lf where start_date is not before end_date")
