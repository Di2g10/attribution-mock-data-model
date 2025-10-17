"""Main entry point for the application."""

from src.orchestrator import build
from pathlib import Path


def main() -> None:
    """Run the application to generate the mock data."""
    # Use absolute paths for more robust path handling
    # Get the absolute path to the project root directory
    project_root = Path(__file__).parent.absolute()
    structure_file_path = project_root / "data" / "input" / "Low Level Field Detail Design.xlsx"

    # Check if the file exists
    if not structure_file_path.exists():
        print(f"Error: File not found: {structure_file_path}")
        print("Checking for alternative files...")

        # Look for alternative files in the same directory
        input_dir = project_root / "data" / "input"
        if input_dir.exists():
            excel_files = list(input_dir.glob("Low Level Field Detail Design*.xlsx"))
            if excel_files:
                # Use the latest version available
                excel_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                structure_file_path = excel_files[0]
                print(f"Using alternative file: {structure_file_path}")
            else:
                print("No alternative files found.")
                return
        else:
            print(f"Input directory not found: {input_dir}")
            return

    # Allow optional per-object row cap via environment variable TEST_MAX_ROWS or default None
    import os

    max_rows_env = os.getenv("TEST_MAX_ROWS")
    max_rows = int(max_rows_env) if max_rows_env and max_rows_env.isdigit() else None

    build(structure_file_path, overwrite=True, max_rows_per_object=max_rows)


if __name__ == "__main__":
    main()
