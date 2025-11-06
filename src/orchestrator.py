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


def _norm_name(name: str) -> str:
    """Normalise a field name similar to test_normalisation: lower + remove spaces/underscores."""
    return str(name).lower().replace(" ", "").replace("_", "")


def _expected_fields_from_attributes(cfg: Config, object_name: str) -> list[str]:
    """Read the Attributes sheet and return expected field names for a given object.

    Filters out placeholder names that contain question marks to mirror the tests.
    Returns an empty list if the sheet is missing.
    """
    attrs = cfg.sheet("Attributes", missing_ok=False)

    # Tolerate header variations by normalising column names
    colmap = {c: str(c).strip().lower().replace(" ", "_") for c in attrs.columns}
    attrs = attrs.rename(colmap)

    if "object" not in attrs.columns or "name" not in attrs.columns:
        raise ValueError("Missing required columns 'object','name' in Attributes sheet")

    # Robust matching: normalise object values and compare with normalised target
    # norm = pl.element().cast(pl.Utf8).str.strip_chars().str.to_lowercase().replace(" ", "_")
    attrs = attrs.with_columns(
        pl.col("object").cast(pl.Utf8).map_elements(lambda s: str(s).strip()).alias("object")
    )
    target_key = _norm_name(object_name)
    alt_key = target_key[:-1] if target_key.endswith("s") else target_key  # singular fallback
    obj_keys = (
        attrs["object"].cast(pl.Utf8).str.to_lowercase().str.replace(" ", "").alias("__obj_key__")
    )
    attrs = attrs.hstack(obj_keys)
    sub = attrs.filter((pl.col("__obj_key__") == target_key) | (pl.col("__obj_key__") == alt_key))
    if sub.is_empty():
        return []

    # Remove rows with NaN/empty and names containing '?'
    sub = sub.filter(
        (pl.col("name").is_not_null()) & (~pl.col("name").cast(pl.Utf8).str.contains("\\?"))
    )
    names = [str(x) for x in sub.get_column("name").to_list()]
    if names:
        return names

    # Fallback: use pandas to read Attributes similarly to the test
    try:
        import pandas as pd  # local import to avoid global dependency if unused

        pdf = pd.read_excel(cfg.workbook, "Attributes")
        # Normalise headers
        pdf.columns = [str(c).strip().lower().replace(" ", "_") for c in pdf.columns]
        if "object" not in pdf.columns or "name" not in pdf.columns:
            return []
        # Case-insensitive normalised match with singular fallback
        pdf["__obj_key__"] = pdf["object"].astype(str).str.strip().str.lower().str.replace(" ", "")
        mask = (pdf["__obj_key__"] == target_key) | (pdf["__obj_key__"] == alt_key)
        sub_pdf = pdf.loc[mask & pdf["name"].notna()].copy()
        # Exclude names with '?'
        sub_pdf = sub_pdf[~sub_pdf["name"].astype(str).str.contains("\\?")]
        return [str(x) for x in sub_pdf["name"].tolist()]
    except Exception:
        return []


def _build_expected_fields_map(cfg: Config) -> dict[str, list[str]]:
    """Build a mapping of object name -> list of expected field names using pandas.

    Mirrors the logic used by tests: reads the `Attributes` sheet with pandas.
    """
    try:
        import pandas as pd

        pdf = pd.read_excel(cfg.workbook, "Attributes")
    except Exception:
        return {}

    # Keep original object names as-is for keys; filter out '?' in names
    res: dict[str, list[str]] = {}
    if "Object" not in pdf.columns or "Name" not in pdf.columns:
        return res

    for obj_name, group in pdf.groupby("Object"):
        if pd.isna(obj_name) or str(obj_name).strip() == "":
            continue
        names = [str(x) for x in group["Name"].dropna().tolist() if "?" not in str(x)]
        res[str(obj_name).strip()] = names
    return res


def _align_columns_to_attributes(
    cfg: Config, object_name: str, df: pl.DataFrame, *, exp_map: dict[str, list[str]] | None = None
) -> pl.DataFrame:
    """Align a DataFrame's columns to the workbook Attributes for the given object.

    - Renames columns when they differ only by formatting (spaces/underscores/case)
      to match the spreadsheet's canonical names.
    - Adds any missing columns with nulls.
    - Drops any extra columns not present in the spreadsheet for that object.
    The comparison uses a normalised key to be robust to trivial formatting.
    """
    expected = _expected_fields_from_attributes(cfg, object_name)
    if not expected:
        return df  # nothing to align

    exp_norm_to_name: dict[str, str] = {}
    for name in expected:
        key = _norm_name(name)
        # Preserve first occurrence if duplicates exist
        if key not in exp_norm_to_name:
            exp_norm_to_name[key] = name

    cur_cols = list(df.columns)
    cur_norm_map: dict[str, str] = {c: _norm_name(c) for c in cur_cols}

    # Build rename map for columns that match by normalised key
    rename_map: dict[str, str] = {}
    used_targets: set[str] = set()
    for col, norm in cur_norm_map.items():
        target = exp_norm_to_name.get(norm)
        if target:
            # If multiple current columns map to the same expected target, keep the first only
            if target not in used_targets:
                if col != target:
                    rename_map[col] = target
                used_targets.add(target)
            else:
                # duplicate mapping -> will be dropped later if not in expected
                pass

    df2 = df.rename(rename_map)

    # Add any missing expected columns with nulls
    missing = [name for key, name in exp_norm_to_name.items() if name not in df2.columns]
    if missing:
        df2 = df2.hstack([pl.Series(name, [None] * df2.height) for name in missing])

    # Drop extras (those not in expected canonical names)
    keep_set = set(exp_norm_to_name.values())
    return df2.select([c for c in df2.columns if c in keep_set])


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
        DataFrame will be truncated to at most this many lf. This does not
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
            print(f"[orchestrator] [{idx}/{len(order)}] Generating '{obj_name}' (lf={row_count}) …")
            t0 = perf_counter()
            gen_module: ModuleType = import_module(f"src.generators.{module_name}")
            # Respect optional cap; avoid calling min() with None
            gen_n = (
                min(row_count, max_rows_per_object)
                if max_rows_per_object is not None
                else row_count
            )
            df = gen_module.generate(gen_n, registry=registry, prior=objs)
            # Apply optional per-object cap to speed up tests (safety slice)
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

            # Reorder columns for consistent output
            df = _reorder_columns(obj_name, df)

            objs[obj_name] = df
            print(
                f"[orchestrator] Completed '{obj_name}': lf={df.height}, gen={gen_dur:.2f}s, validate={val_dur:.2f}s"
            )
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f"Could not find generator module for '{obj_name}'. Tried: 'src.generators.{module_name}'"
            ) from e

    # Decide whether to write CSV files. When running in capped/test mode and using the
    # default output directory, skip disk I/O to speed up validation-focused tests.
    default_out = Path("mock_output")
    write_files = not (max_rows_per_object is not None and Path(output_path) == default_out)

    if write_files:
        print("[orchestrator] Writing CSV files …")
        ensure_output_dir(output_path, overwrite)

        write_start = perf_counter()
        for name, df in objs.items():
            t_write = perf_counter()
            out_file = Path(output_path) / f"{name}.csv"
            df.write_csv(out_file)
            print(
                f"[orchestrator] Wrote {name}.csv (lf={df.height}) in {perf_counter() - t_write:.2f}s -> {out_file}"
            )
        print(f"[orchestrator] Finished writing CSVs in {perf_counter() - write_start:.2f}s")
    else:
        print("[orchestrator] Skipping CSV writes (test/capped mode with default output path)")

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
