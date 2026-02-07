"""Tests for biorxiv module."""

import json
import sys
from pathlib import Path

# Add scripts to path
TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import biorxiv


FIXTURES_DIR = TESTS_DIR.parent / "fixtures"


def load_fixture():
    with open(FIXTURES_DIR / "biorxiv_sample.json") as f:
        return json.load(f)


def test_search_biorxiv_mock():
    """Test bioRxiv search with mock data."""
    fixture = load_fixture()
    items, error = biorxiv.search_biorxiv(
        topic="CRISPR gene editing",
        from_date="2025-01-01",
        to_date="2025-01-31",
        depth="quick",
        mock_data=fixture.get('collection', []),
    )
    assert error is None
    assert len(items) >= 1
    # Check that CRISPR-relevant items are found
    assert any("CRISPR" in item.get('title', '').upper() or "CRISPR" in item.get('abstract', '').upper()
               for item in items)


def test_search_biorxiv_relevance_filter():
    """Test that irrelevant items are filtered out."""
    fixture = load_fixture()
    items, error = biorxiv.search_biorxiv(
        topic="quantum computing",
        from_date="2025-01-01",
        to_date="2025-01-31",
        depth="quick",
        mock_data=fixture.get('collection', []),
    )
    assert error is None
    # None of the CRISPR fixtures should match quantum computing
    assert len(items) == 0


def test_search_medrxiv_mock():
    """Test medRxiv search shares same code path."""
    fixture = load_fixture()
    # Pretend it's medrxiv data
    for item in fixture.get('collection', []):
        item['source'] = 'medrxiv'

    items, error = biorxiv.search_medrxiv(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        depth="quick",
        mock_data=fixture.get('collection', []),
    )
    assert error is None
    assert len(items) >= 1
    # Verify source is set
    for item in items:
        assert item.get('source') == 'medrxiv'


def test_relevance_scores_populated():
    """Test that relevance scores are populated."""
    fixture = load_fixture()
    items, _ = biorxiv.search_biorxiv(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        depth="quick",
        mock_data=fixture.get('collection', []),
    )
    for item in items:
        assert 'relevance' in item
        assert 'why_relevant' in item
        assert item['relevance'] > 0.1


def test_depth_limits():
    """Test that depth config limits are applied."""
    assert biorxiv.DEPTH_LIMITS['quick'] < biorxiv.DEPTH_LIMITS['default']
    assert biorxiv.DEPTH_LIMITS['default'] < biorxiv.DEPTH_LIMITS['deep']
