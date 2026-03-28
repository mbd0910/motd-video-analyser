"""Pytest configuration and shared fixtures for MOTD analyser tests."""

import pytest
from pathlib import Path


def pytest_configure(config):
    """Register custom markers for test categorisation."""
    config.addinivalue_line(
        "markers",
        "unit: Unit tests (pure logic, no external services)"
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (requires external services)"
    )


@pytest.fixture
def project_root() -> Path:
    """Return project root directory."""
    return Path(__file__).parent.parent
