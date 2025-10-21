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
    max_rows_per_object: int | None = None,
) -> dict[str, pl.DataFrame]:
    """High-level façade called by users & tests.

    Adds lightweight terminal progress outputs with timings for each phase to
    help identify where time is spent during mock data generation.

    :param workbook: Path to the Excel workbook that defines schemas and counts.
    :param output_path: Directory where CSVs will be written.
    :param overwrite: Whether to overwrite the output directory if it exists.
    :param max_rows_per_object: Optional cap; if provided, each generated object's
        DataFrame will be truncated to at most this many rows. This does not
        modify the configured row counts in validation; tests using this option
        should avoid strict row-count assertions.
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
            # Apply optional per-object cap to speed up tests
            if max_rows_per_object is not None and df.height > max_rows_per_object:
                df = df.slice(0, max_rows_per_object)
            gen_dur = perf_counter() - t0

            t1 = perf_counter()
            validate_object(
                df,
                obj_name,
                registry,
                prior=objs,
                skip_row_count=(max_rows_per_object is not None),
            )
            val_dur = perf_counter() - t1

            df = _reorder_columns(obj_name, df)

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


# ---------------------------------------------------------------------------
# Column ordering helper: PK, then FKs, then others with dates grouped
# ---------------------------------------------------------------------------


def _reorder_columns(object_name: str, df: pl.DataFrame) -> pl.DataFrame:
    """Reorder a DataFrame's columns for consistent output ordering.

    Rules:
    - Primary Key (PK) first
    - Foreign Keys (FKs) next (all *_id except the PK)
    - Other fields after, with date-like fields grouped to the end of the frame

    The function preserves relative order within each group.

    :param object_name: Canonical object name used by the generators.
    :param df: Polars DataFrame to reorder.
    :returns: DataFrame with columns reordered.
    """
    import re

    cols = list(df.columns)
    if not cols:
        return df

    # Known PKs by object name (keep simple; extend when needed)
    pk_map = {
        "Company": "company_id",
        "Person": "person_id",
        "Person Company Role": "person_company_role_id",
        "Products": "product_id",
        "Campaigns": "campaign_id",
        "Audience": "audience_id",
        "Channels": "channel_id",
        "Marketing Assets": "marketing_asset_id",
        "Marketing Activity": "marketing_activity_id",
        "Interactions": "interaction_id",
        "Orders": "order_id",
        "Attribution Linking Table": "link_id",
        "Attribution Model": "model_id",
        "Attribution Model Output Table": "output_id",
        "Date Dimension": "date_id",
        "Facilitation Tool": "facilitation_tool_id",
    }

    pk = pk_map.get(object_name)
    if pk not in cols:
        # Fallback: choose the first *_id that ends with the object token (e.g. interaction_id)
        pattern = re.compile(r".*_id$")
        ids = [c for c in cols if pattern.match(c)]
        pk = ids[0] if ids else None

    def is_date(c: str) -> bool:
        cl = c.lower()
        return "date" in cl or cl in {"interactiondate", "outcomedate"}

    # Partition columns preserving original order
    pk_cols: list[str | None] = [pk] if pk in cols else []
    fk_cols: list[str] = [c for c in cols if c.endswith("_id") and c != pk]
    date_cols: list[str] = [c for c in cols if is_date(c) and c not in pk_cols and c not in fk_cols]
    other_cols: list[str] = [c for c in cols if c not in pk_cols + fk_cols + date_cols]

    new_order = pk_cols + fk_cols + other_cols + date_cols
    # Ensure we didn't drop anything accidentally
    if set(new_order) != set(cols) or len(new_order) != len(cols):
        return df  # safety: keep original if something went wrong
    return df.select(new_order)
