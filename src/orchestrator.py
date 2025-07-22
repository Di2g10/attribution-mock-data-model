"""Coordinates generation steps and writes outputs."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

import polars as pl

from .config_loader import Config
from .schema_registry import SchemaRegistry
from .validation import validate_object, ensure_output_dir

__all__ = ["build"]


def build(
    workbook: str | Path,
    output_path: str | Path = "mock_output",
    overwrite: bool = False,
) -> dict[str, pl.DataFrame]:
    """High-level façade called by users & tests."""
    cfg = Config(workbook)
    registry = SchemaRegistry(cfg)
    objs: dict[str, pl.DataFrame] = {}

    for obj_name in registry.generation_order():
        # Handle special case for "Companies" -> "company"
        module_name = obj_name.lower().replace(" ", "_")

        if module_name == "companies":
            module_name = "company"

        try:
            gen_module: ModuleType = import_module(f"src.generators.{module_name}")
            row_count = registry.row_count(obj_name)
            df = gen_module.generate(row_count, registry=registry, prior=objs)
            validate_object(df, obj_name, registry, prior=objs)
            objs[obj_name] = df
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f"Could not find generator module for '{obj_name}'. Tried: 'src.generators.{module_name}'"
            ) from e

    ensure_output_dir(output_path, overwrite)
    for name, df in objs.items():
        df.write_csv(Path(output_path) / f"{name}.csv")

    return objs
