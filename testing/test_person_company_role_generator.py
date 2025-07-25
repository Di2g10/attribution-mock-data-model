"""Tests for the person_company_role generator module."""

import unittest

from src.generators.person_company_role import generate

# Constants for test sample sizes
LARGE_SAMPLE_SIZE = 20


class TestPersonCompanyRole(unittest.TestCase):
    """Test the person_company_role generator."""

    def test_person_company_role_dates(self) -> None:
        """Test that start_date is before end_date when end_date is not None."""
        df = generate(LARGE_SAMPLE_SIZE)

        # Filter for rows where end_date is not None
        df_with_end_date = df.filter(df["end_date"].is_not_null())

        # Verify that start_date is before end_date for all rows
        for row in df_with_end_date.iter_rows(named=True):
            start_date = row["start_date"]
            end_date = row["end_date"]
            self.assertLess(
                start_date, end_date, f"start_date {start_date} is not before end_date {end_date}"
            )
