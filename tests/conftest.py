"""Pytest configuration and shared fixtures for MOTD analyser tests."""

import pytest
from pathlib import Path


def pytest_configure(config):
    """Register custom markers for test categorisation."""
    config.addinivalue_line(
        "markers",
        "unit: Unit tests (pure logic, no ML dependencies - can run without torch/easyocr)"
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (requires full ML stack - torch, easyocr, test images)"
    )


@pytest.fixture
def project_root() -> Path:
    """Return project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_team_codes() -> set:
    """
    Standard set of Premier League team codes for unit testing.

    Includes all 20 teams from 2025/26 season plus common variations.
    Use this fixture to avoid file I/O in unit tests.
    """
    return {
        # Current Premier League teams (2025/26)
        'ARS',  # Arsenal
        'AVL',  # Aston Villa
        'BOU',  # Bournemouth
        'BRE',  # Brentford
        'BHA', 'BRI',  # Brighton (both codes)
        'BUR',  # Burnley (promoted)
        'CHE',  # Chelsea
        'CRY', 'PAL',  # Crystal Palace (both codes)
        'EVE',  # Everton
        'FUL',  # Fulham
        'LEE',  # Leeds United
        'LIV',  # Liverpool
        'MCI', 'MNC',  # Manchester City (both codes)
        'MUN', 'MNU',  # Manchester United (both codes)
        'NEW',  # Newcastle United
        'NFO', 'FOR', 'NOT',  # Nottingham Forest (all codes)
        'SUN',  # Sunderland
        'TOT',  # Tottenham Hotspur
        'WHU',  # West Ham United
        'WOL',  # Wolverhampton Wanderers
    }
