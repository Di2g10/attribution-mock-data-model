"""defines the Config class, which holds the configuration for the mock data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import polars as pl

__all__ = ["Config"]


class Config:
    """Loads an Excel workbook into Polars DataFrames.

    The loader is *dynamic*: new columns or sheets appear automatically with
    no code changes required.
    """

    def __init__(self, workbook: str | Path):
        """Initialize the Config object with the workbook path."""
        self.workbook = Path(workbook)
        self._cache: dict[str, pl.DataFrame] = {}

    def sheet(self, name: str, *, missing_ok: bool = False) -> pl.DataFrame:
        """Load a sheet into a Polars DataFrame."""
        if name in self._cache:
            return self._cache[name]
        try:
            pdf = pd.read_excel(self.workbook, sheet_name=name)
            # Workaround for mixed-type columns in 'objects' sheet (e.g., numeric & 'Dependant')
            if str(name).strip().lower() == "objects":
                for col in list(pdf.columns):
                    if str(col).strip().lower().replace(" ", "_") in {
                        "generate_rows",
                        "generate_rows?",
                    }:
                        pdf[col] = pdf[col].astype(str)
            df = pl.from_pandas(pdf).fill_null("")
        except ValueError:
            if not missing_ok:
                raise
            df = pl.DataFrame()
        self._cache[name] = df
        return df

    # Convenience properties -------------------------------------------
    @property
    def objects(self) -> pl.DataFrame:
        """Return the object's sheet as a Polars DataFrame."""
        return self.sheet("objects")

    @property
    def channels(self) -> pl.DataFrame:
        """Return the channel's sheet as a Polars DataFrame."""
        return self.sheet("Channels")

    @property
    def interaction_types(self) -> pl.DataFrame:
        """Return the interaction types sheet as a Polars DataFrame."""
        return self.sheet("Interaction Types")

    @property
    def params(self) -> dict[str, str]:
        """Return the params sheet as a dictionary."""
        if "params" not in self.sheet_names:
            return {}
        df = self.sheet("params")
        return dict(zip(df["key"], df["value"]))

    # ------------------------------------------------------------------
    @property
    def sheet_names(self) -> list[str]:
        """Return the names of the sheets in the workbook."""
        import openpyxl  # lightweight dependency only for listing sheets

        wb = openpyxl.load_workbook(self.workbook, read_only=True)
        return wb.sheetnames
