"""Characterization tests for the example target repository."""

from __future__ import annotations

import unittest

from example_target import add_adjusted


class CalculatorCharacterizationTests(unittest.TestCase):
    """Tests that describe the fixture's current behavior."""

    def test_add_adjusted_keeps_existing_behavior(self) -> None:
        """Addition includes the optional adjustment value."""
        self.assertEqual(add_adjusted(2, 3, adjustment=4), 9)

    def test_add_adjusted_defaults_to_plain_addition(self) -> None:
        """The default adjustment preserves plain addition."""
        self.assertEqual(add_adjusted(2, 3), 5)


if __name__ == "__main__":
    unittest.main()
