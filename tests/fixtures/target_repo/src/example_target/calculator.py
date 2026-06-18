"""Small behavior surface for target-repo characterization tests."""


def add_adjusted(left: int, right: int, adjustment: int = 0) -> int:
    """Return the sum of two values plus an optional adjustment.

    Args:
        left: First value to add.
        right: Second value to add.
        adjustment: Optional adjustment applied after the sum.

    Returns:
        The adjusted sum.
    """
    return left + right + adjustment
