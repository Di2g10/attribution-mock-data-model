"""Contains functions to generate date dimension data."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, List

import polars as pl


__all__ = ["generate"]


def generate_date_range(start_date: datetime, end_date: datetime) -> List[datetime]:
    """Generate a range of dates.

    :param start_date: Start date of the range
    :param end_date: End date of the range
    :returns: List of dates in the range
    """
    date_list = []
    current_date = start_date

    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)

    return date_list


def extract_date_components(dates: List[datetime]) -> dict[str, List[Any]]:
    """Extract various date components from a list of dates.

    :param dates: List of datetime objects
    :returns: Dictionary of date components
    """
    # Initialize lists for each component
    date_keys = []
    full_dates = []
    dates_str = []  # For the 'date' field required by the spreadsheet
    years = []
    quarters = []
    months = []
    month_names = []
    days = []
    day_of_week = []
    day_name = []
    week_of_year = []
    isweekend = []
    isholiday = []
    fiscal_year = []
    fiscal_quarter = []
    financial_year = []  # For the 'financialyear' field required by the spreadsheet
    financial_month_number = []  # For the 'financialmonthnumber' field required by the spreadsheet
    financial_quarter = []  # For the 'financialquarter' field required by the spreadsheet

    # Common holidays (simplified)
    holidays = [
        (1, 1),  # New Year's Day
        (12, 25),  # Christmas
        (7, 4),  # Independence Day (US)
        (11, 11),  # Veterans Day (US) / Remembrance Day (UK)
        (5, 25),  # Memorial Day (approximate - last Monday in May)
        (9, 1),  # Labor Day (approximate - first Monday in September)
    ]

    # Extract components for each date
    for i, date in enumerate(dates):
        date_keys.append(f"DATE{i:06d}")
        full_dates.append(date.strftime("%Y-%m-%d"))
        dates_str.append(date.strftime("%Y-%m-%d"))  # For the 'date' field
        years.append(date.year)

        # Calculate quarter
        quarter = (date.month - 1) // 3 + 1
        quarters.append(f"Q{quarter}")

        months.append(date.month)
        month_names.append(date.strftime("%B"))
        days.append(date.day)
        day_of_week.append(date.weekday())
        day_name.append(date.strftime("%A"))
        week_of_year.append(date.strftime("%U"))

        # Check if weekend
        isweekend.append(date.weekday() >= 5)  # noqa:PLR2004 5 = Saturday, 6 = Sunday

        # Check if holiday (simplified)
        isholiday.append((date.month, date.day) in holidays)

        # Fiscal year and quarter (assuming fiscal year starts in April)
        if date.month >= 4:  # noqa: PLR2004
            fiscal_year.append(f"FY{date.year}")
            fiscal_quarter.append(f"FQ{(date.month - 4) // 3 + 1}")

            # Financial year (for the 'financialyear' field)
            financial_year.append(date.year)

            # Financial month number (for the 'financialmonthnumber' field)
            # If fiscal year starts in April, then April is month 1, May is month 2, etc.
            financial_month_number.append(date.month - 3)

            # Financial quarter (for the 'financialquarter' field)
            financial_quarter.append(quarter)
        else:
            fiscal_year.append(f"FY{date.year - 1}")
            fiscal_quarter.append(f"FQ{(date.month + 8) // 3 + 1}")

            # Financial year (for the 'financialyear' field)
            financial_year.append(date.year - 1)

            # Financial month number (for the 'financialmonthnumber' field)
            # If fiscal year starts in April, then January is month 10, February is month 11, March is month 12
            financial_month_number.append(date.month + 9)

            # Financial quarter (for the 'financialquarter' field)
            # If fiscal year starts in April, then Q1 is Apr-Jun, Q2 is Jul-Sep, Q3 is Oct-Dec, Q4 is Jan-Mar
            financial_quarter.append((date.month + 8) // 3 + 1)

    # Only include fields that are defined in the spreadsheet
    return {
        "date_key": date_keys,
        "date": dates_str,
        "financial_year": financial_year,
        "financial_month_number": financial_month_number,
        "financial_quarter": financial_quarter,
        "is_holiday": isholiday,
        "is_weekend": isweekend,
    }


def generate(n: int, **kwargs: Any) -> pl.DataFrame:
    """Generate a DataFrame of date dimension data.

    :param n: Number of dates to generate
    :param kwargs: Additional keyword arguments
    :returns: DataFrame containing generated date dimension data
    """
    # Generate dates for the past year, current year, and next year
    today = datetime.now()

    start_date = today - timedelta(days=n - 1)
    end_date = today

    # Generate date range
    dates = generate_date_range(start_date, end_date)

    # If we have more dates than requested, sample them
    if len(dates) > n:
        # Sample n dates evenly from the range
        step = len(dates) // n
        sampled_indices = [i * step for i in range(n)]
        dates = [dates[i] for i in sampled_indices]

    # Extract date components
    date_components = extract_date_components(dates)

    # Create DataFrame
    return pl.DataFrame(date_components)
