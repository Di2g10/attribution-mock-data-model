"""For manual running of the print population rates script."""

from pathlib import Path

from src.validation import print_population_rates


def main() -> None:
    """Check the distribution of relation types in the attribution linking table."""
    path = Path(
        "C:/Users", "DavidIrvine", "PycharmProjects", "bt-attribution-mock-data", "mock_output"
    )
    print_population_rates(path)


if __name__ == "__main__":
    main()
