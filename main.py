"""Main entry point for the application."""

from src.orchestrator import build
from pathlib import Path


def main() -> None:
    """Run the application to generate the mock data."""
    structure_file_path = Path("data", "input", "Low Level Field Detail Design(4).xlsx")
    build(structure_file_path, overwrite=True)


if __name__ == "__main__":
    main()
