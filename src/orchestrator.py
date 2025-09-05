"""Coordinates generation steps and writes outputs."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType
from time import perf_counter
from datetime import datetime

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
    """High-level façade called by users & tests.

    Adds lightweight terminal progress outputs with timings for each phase to
    help identify where time is spent during mock data generation.

    :param workbook: Path to the Excel workbook that defines schemas and counts.
    :param output_path: Directory where CSVs will be written.
    :param overwrite: Whether to overwrite the output directory if it exists.
    :returns: Mapping of object name to generated Polars DataFrame.
    """
    start_all = perf_counter()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[orchestrator] {ts} Starting build")
    print(f"[orchestrator] Workbook: {Path(workbook)}")
    print(f"[orchestrator] Output path: {Path(output_path)} (overwrite={overwrite})")

    cfg = Config(workbook)
    registry = SchemaRegistry(cfg)
    order = registry.generation_order()
    print(f"[orchestrator] Objects to generate: {len(order)} -> {', '.join(order)}")

    objs: dict[str, pl.DataFrame] = {}

    for idx, obj_name in enumerate(order, start=1):
        module_name = obj_name.lower().replace(" ", "_")
        try:
            row_count = registry.row_count(obj_name)
            print(
                f"[orchestrator] [{idx}/{len(order)}] Generating '{obj_name}' (rows={row_count}) …"
            )
            t0 = perf_counter()
            gen_module: ModuleType = import_module(f"src.generators.{module_name}")
            df = gen_module.generate(row_count, registry=registry, prior=objs)
            gen_dur = perf_counter() - t0

            t1 = perf_counter()
            validate_object(df, obj_name, registry, prior=objs)
            val_dur = perf_counter() - t1

            objs[obj_name] = df
            print(
                f"[orchestrator] Completed '{obj_name}': rows={df.height}, gen={gen_dur:.2f}s, validate={val_dur:.2f}s"
            )
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f"Could not find generator module for '{obj_name}'. Tried: 'src.generators.{module_name}'"
            ) from e

    print("[orchestrator] Writing CSV files …")
    ensure_output_dir(output_path, overwrite)

    write_start = perf_counter()
    for name, df in objs.items():
        t_write = perf_counter()
        out_file = Path(output_path) / f"{name}.csv"
        df.write_csv(out_file)
        print(
            f"[orchestrator] Wrote {name}.csv (rows={df.height}) in {perf_counter() - t_write:.2f}s -> {out_file}"
        )
    print(f"[orchestrator] Finished writing CSVs in {perf_counter() - write_start:.2f}s")

    total_dur = perf_counter() - start_all
    print(f"[orchestrator] Build completed in {total_dur:.2f}s")

    return objs
