"""Contains classes and functions for testing the end to end project code."""

import unittest


class TestEndToEnd(unittest.TestCase):
    """Test the end to end code."""

    def test_standard_run(self) -> None:
        """Test the standard run of the code."""
        self.assertEqual(True, False)  # add assertion here


if __name__ == "__main__":
    unittest.main()
