"""
Pytest Configuration and Shared Fixtures
"""

import pytest
from typing import Dict, List


@pytest.fixture
def known_entities() -> Dict[str, List[str]]:
    """
    Fixture providing known entities for disambiguation tests.
    """
    return {
        "company": [
            "Delta Air Lines",
            "Delta Corp", 
            "Delta Technologies",
            "Microsoft Corporation",
            "Mercury Systems",
            "Mercury Insurance",
            "Apple Inc.",
            "Google LLC"
        ],
        "category": [
            "VC", "PE", "Angel", 
            "Startup", "Enterprise", 
            "Mid-Market", "SMB"
        ],
        "ceo": [
            "Satya Nadella",
            "John Smith",
            "Tim Cook",
            "Jeff Bezos",
            " Elon Musk"
        ],
        "competitor": [
            "Apple Inc.",
            "Microsoft Corporation",
            "Google LLC",
            "Amazon.com Inc."
        ],
        "investor": [
            "Sequoia Capital US",
            "Sequoia China",
            "Sequoia India",
            "Accel Partners",
            "Andreessen Horowitz",
            "Kleiner Perkins"
        ],
        "association": [
            "IEEE",
            "ISO",
            "ANSI",
            "NIST",
            "W3C"
        ]
    }


@pytest.fixture
def valid_categories() -> List[str]:
    """
    Fixture providing valid business categories.
    """
    return [
        "Startup", "Enterprise", "Mid-Market", "SMB",
        "Investor", "VC", "PE", "Angel"
    ]


@pytest.fixture
def valid_legal_structures() -> List[str]:
    """
    Fixture providing valid legal structure types.
    """
    return [
        "Private", "Public", "Non-Profit", "Government",
        "Partnership", "Sole Proprietorship", "LLP", "LLC"
    ]


@pytest.fixture
def valid_remote_policies() -> List[str]:
    """
    Fixture providing valid remote work policies.
    """
    return [
        "Fully Remote", "Hybrid", "On-site", 
        "Flexible", "Unknown"
    ]


@pytest.fixture
def valid_sales_motions() -> List[str]:
    """
    Fixture providing valid sales motion types.
    """
    return [
        "Product-Led", "Sales-Led", 
        "Marketing-Led", "Partner-Led"
    ]


@pytest.fixture
def valid_profitability_statuses() -> List[str]:
    """
    Fixture providing valid profitability statuses.
    """
    return [
        "Profitable", "Non-Profit", 
        "Break Even", "Loss Making"
    ]


# Pytest configuration hook
def pytest_configure(config):
    """
    Register custom markers.
    """
    config.addinivalue_line(
        "markers", "valid: Tests for valid/positive inputs"
    )
    config.addinivalue_line(
        "markers", "invalid: Tests for invalid/negative inputs"
    )
    config.addinivalue_line(
        "markers", "format: Tests for format/pattern validation"
    )
    config.addinivalue_line(
        "markers", "crossfield: Tests for cross-field validation"
    )
    config.addinivalue_line(
        "markers", "temporal: Tests for temporal/date validation"
    )
    config.addinivalue_line(
        "markers", "datasource: Tests for data source validation"
    )