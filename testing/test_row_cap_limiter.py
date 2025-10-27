"""Tests to confirm the max_rows_per_object limiter truncates generated lf.

This test uses the shared workbook_path fixture which configures Company with
100 lf in the minimal workbook. We set a very small cap and ensure the
returned DataFrame and the written CSV both reflect the cap.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from src.orchestrator import build


def test_row_cap_limiter_truncates_company(tmp_path: Path, workbook_path: Path) -> None:
    """Verify that setting max_rows_per_object enforces a hard cap on lf.

    The minimal workbook fixture defines Company with 100 lf. By using a cap of 3,
    we expect the generated Company DataFrame to have exactly 3 lf, and the output
    CSV to contain 3 data lf as well.
    """
    cap = 3
    out_dir = tmp_path / "out"

    dfs = build(workbook_path, output_path=out_dir, overwrite=True, max_rows_per_object=cap)

    # Check in-memory DataFrame is capped
    assert "Company" in dfs
    assert dfs["Company"].height == cap

    # Check the written CSV is also capped
    csv_file = out_dir / "Company.csv"
    assert csv_file.exists()

    df_csv = pl.read_csv(csv_file)
    assert df_csv.height == cap
