"""Package-level smoke tests."""

import ragflow_agent


def test_import_package_name() -> None:
    """The distribution exposes the confirmed import package."""
    assert ragflow_agent.__name__ == "ragflow_agent"
