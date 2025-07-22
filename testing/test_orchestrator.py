"""Tests for the orchestrator module."""

from pathlib import Path

from src.orchestrator import build

# Constants for expected row counts
EXPECTED_COMPANY_ROWS = 10


def test_orchestrator_build(tmp_path: Path, workbook_path: Path) -> None:
    """Test the build function of the orchestrator module."""
    out_dir = tmp_path / "out"
    dfs = build(workbook_path, output_path=out_dir, overwrite=True)

    # Expect Company CSV to be present and match row count
    comp_csv = Path(out_dir) / "Company.csv"
    assert comp_csv.exists()

    company_df = dfs["Company"]
    assert company_df.height == EXPECTED_COMPANY_ROWS
