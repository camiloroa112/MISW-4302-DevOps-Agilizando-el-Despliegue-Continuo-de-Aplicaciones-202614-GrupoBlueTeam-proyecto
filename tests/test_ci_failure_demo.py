# 3rd Party Imports
import pytest

# Intentional, reversible failure used only to demonstrate a failing CI pipeline run
def test_intentional_failure_demo() -> None:
    """
    Introduction:
        - This test always fails to show that the CI pipeline blocks the artifact when a test breaks
    Returns:
        - None
    """

    # Force a controlled failure so the build stage fails
    assert False, "Controlled CI failure demo"