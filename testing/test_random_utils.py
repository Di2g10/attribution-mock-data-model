"""Tests for random_utils module, focusing on generate_mapped_values function."""

import sys
from pathlib import Path
from typing import Mapping, Sequence, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.random_utils import generate_mapped_values, seed_everything


def test_empty_parent_values() -> None:
    """Test with empty parent values list."""
    seed_everything(42)
    mapping = {"A": ["x", "y"], "B": ["z"]}
    result = generate_mapped_values([], mapping)
    assert result == []


def test_empty_mapping_dict_no_fallback() -> None:
    """Test with empty mapping dict and no fallback values."""
    seed_everything(42)
    result = generate_mapped_values(["A", "B", "C"], {})
    assert result == [None, None, None]


def test_empty_mapping_dict_with_fallback() -> None:
    """Test with empty mapping dict but with fallback values."""
    seed_everything(42)
    fallback = ["default1", "default2"]
    result = generate_mapped_values(["A", "B", "C"], {}, fallback_values=fallback)
    target_lenth = 3
    assert len(result) == target_lenth
    # All results should be from fallback values
    for val in result:
        assert val in fallback


def test_basic_mapping() -> None:
    """Test basic mapping functionality with simple data."""
    seed_everything(42)
    parent_values = ["Channel_A", "Channel_B", "Channel_A"]
    mapping = {
        "Channel_A": ["Type1", "Type2"],
        "Channel_B": ["Type3", "Type4"],
    }
    result = generate_mapped_values(parent_values, mapping)
    target_lenth = 3
    assert len(result) == target_lenth
    # First and third should be from Channel_A's types
    assert result[0] in mapping["Channel_A"]
    assert result[2] in mapping["Channel_A"]
    # Second should be from Channel_B's types
    assert result[1] in mapping["Channel_B"]


def test_unmapped_parent_with_fallback() -> None:
    """Test behavior when parent is not in mapping but fallback exists."""
    seed_everything(42)
    parent_values = ["Known", "Unknown", "Known"]
    mapping = {"Known": ["A", "B"]}
    fallback = ["FallbackX", "FallbackY"]

    result = generate_mapped_values(parent_values, mapping, fallback_values=fallback)
    target_lenth = 3
    assert len(result) == target_lenth
    # First and third should be from Known mapping
    assert result[0] in mapping["Known"]
    assert result[2] in mapping["Known"]
    # Second (Unknown) should be from fallback
    assert result[1] in fallback


def test_unmapped_parent_without_fallback() -> None:
    """Test behavior when parent is not in mapping and no fallback."""
    seed_everything(42)
    parent_values = ["Known", "Unknown"]
    mapping = {"Known": ["A", "B"]}

    result = generate_mapped_values(parent_values, mapping)
    target_lenth = 2
    assert len(result) == target_lenth
    assert result[0] in mapping["Known"]
    assert result[1] is None


def test_single_value_per_parent() -> None:
    """Test mapping where each parent has only one possible child value."""
    seed_everything(42)
    parent_values = ["A", "B", "A", "B"]
    mapping = {"A": ["only_x"], "B": ["only_y"]}

    result = generate_mapped_values(parent_values, mapping)
    target_lenth = 4
    assert len(result) == target_lenth
    assert result[0] == "only_x"
    assert result[1] == "only_y"
    assert result[2] == "only_x"
    assert result[3] == "only_y"


def test_large_dataset() -> None:
    """Test with a larger dataset to verify performance and correctness."""
    seed_everything(42)
    # Create a large list of parent values
    parent_values = ["Channel_A"] * 1000 + ["Channel_B"] * 1000 + ["Channel_C"] * 500
    mapping = {
        "Channel_A": ["Type1", "Type2", "Type3"],
        "Channel_B": ["Type4", "Type5"],
        "Channel_C": ["Type6"],
    }

    result = generate_mapped_values(parent_values, mapping)
    target_lenth = 2500
    assert len(result) == target_lenth
    # Verify all values come from their respective mappings
    for i, parent in enumerate(parent_values):
        assert result[i] in mapping[parent]


def test_empty_child_values_list() -> None:
    """Test behavior when a parent maps to an empty list of child values."""
    seed_everything(42)
    parent_values = ["A", "B"]
    mapping = {"A": [], "B": ["value1", "value2"]}
    fallback = ["fallback"]

    result = generate_mapped_values(parent_values, mapping, fallback_values=fallback)
    target_lenth = 2
    assert len(result) == target_lenth
    # A should use fallback since it has empty child values
    assert result[0] in fallback
    # B should use its mapping
    assert result[1] in mapping["B"]


def test_deterministic_with_seed() -> None:
    """Test that results are deterministic when using the same seed."""
    parent_values = ["A", "B", "A"] * 10
    mapping = {"A": ["x", "y", "z"], "B": ["p", "q", "r"]}

    # First run
    seed_everything(123)
    result1 = generate_mapped_values(parent_values, mapping)

    # Second run with same seed
    seed_everything(123)
    result2 = generate_mapped_values(parent_values, mapping)

    assert result1 == result2


def test_different_seeds_produce_different_results() -> None:
    """Test that different seeds produce different results."""
    parent_values = ["A"] * 100
    mapping = {"A": ["x", "y", "z", "w"]}

    seed_everything(42)
    result1 = generate_mapped_values(parent_values, mapping)

    seed_everything(999)
    result2 = generate_mapped_values(parent_values, mapping)

    # Results should be different (very high probability)
    assert result1 != result2


def test_mixed_types_in_child_values() -> None:
    """Test that child values can be of various types (not just strings)."""
    seed_everything(42)
    parent_values = ["Category1", "Category2"]
    mapping: Mapping[str, Sequence[Any]] = {
        "Category1": [1, 2, 3],
        "Category2": [10.5, 20.7],
    }

    result = generate_mapped_values(parent_values, mapping)
    target_lenth = 2
    assert len(result) == target_lenth
    assert result[0] in mapping["Category1"]
    assert result[1] in mapping["Category2"]
    assert isinstance(result[0], int)
    assert isinstance(result[1], float)


def test_real_world_channel_interaction_scenario() -> None:
    """Test with realistic channel-to-interaction-type mapping."""
    seed_everything(42)
    channels = ["Email", "Social Media", "Email", "Webinar", "Social Media"]
    channel_to_interaction = {
        "Email": ["Email Open", "Email Click", "Email Reply"],
        "Social Media": ["Post Like", "Post Share", "Comment"],
        "Webinar": ["Webinar Registration", "Webinar Attendance"],
    }

    result = generate_mapped_values(channels, channel_to_interaction)

    target_lenth = 5
    assert len(result) == target_lenth
    # Verify each result matches its channel's possible interactions
    assert result[0] in channel_to_interaction["Email"]
    assert result[1] in channel_to_interaction["Social Media"]
    assert result[2] in channel_to_interaction["Email"]
    assert result[3] in channel_to_interaction["Webinar"]
    assert result[4] in channel_to_interaction["Social Media"]


def test_verbose_mode_timing() -> None:
    """Test that verbose mode works without errors."""
    seed_everything(42)
    parent_values = ["A", "B"] * 100
    mapping = {"A": ["x", "y"], "B": ["z"]}

    # Should not raise any exceptions
    result = generate_mapped_values(parent_values, mapping, verbose=True)
    target_lenth = 200
    assert len(result) == target_lenth


def test_performance_benchmark() -> None:
    """Benchmark performance with various dataset sizes."""
    import time

    test_cases = [
        (100, "small"),
        (1000, "medium"),
        (10000, "large"),
        (50000, "xlarge"),
    ]

    mapping = {
        "Channel_A": ["Type1", "Type2", "Type3", "Type4"],
        "Channel_B": ["Type5", "Type6"],
        "Channel_C": ["Type7", "Type8", "Type9"],
    }

    print("\n--- Performance Benchmark ---")
    for size, label in test_cases:
        seed_everything(42)
        parent_values = ["Channel_A", "Channel_B", "Channel_C"] * (size // 3)

        start = time.perf_counter()
        result = generate_mapped_values(parent_values, mapping)
        elapsed = time.perf_counter() - start

        assert len(result) == len(parent_values)
        print(f"{label:>8} ({size:>6} rows): {elapsed:.4f}s ({size/elapsed:,.0f} rows/sec)")


if __name__ == "__main__":
    # Run all test functions
    import inspect

    current_module = sys.modules[__name__]
    test_functions = [
        func
        for name, func in inspect.getmembers(current_module, inspect.isfunction)
        if name.startswith("test_")
    ]

    print(f"Running {len(test_functions)} tests...\n")
    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: ERROR - {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
