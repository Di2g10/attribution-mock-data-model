"""Tests for the configuration loader module."""

from pathlib import Path

from src.config_loader import Config

# Constants for expected row counts
EXPECTED_CHANNEL_ROWS = 1


def test_loader_basic(workbook_path: Path) -> None:
    """Test basic functionality of the Config loader."""
    cfg = Config(workbook_path)
    assert "Company" in cfg.objects.select("Name").to_series().to_list()
    assert cfg.channels.height == EXPECTED_CHANNEL_ROWS  # one row of channel data
