"""Tests for openalex module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
FIXTURES_DIR = TESTS_DIR.parent / "fixtures"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import openalex


def _load_fixture():
    """Load sample OpenAlex fixture."""
    with open(FIXTURES_DIR / "openalex_sample.json") as f:
        return json.load(f)


def test_search_openalex_mock():
    """Test search with mock data returns relevant results."""
    fixture = _load_fixture()
    results, error = openalex.search_openalex(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['results']
    )
    assert error is None
    assert len(results) >= 1
    # Should find virome papers, not protein folding
    titles = [r['title'] for r in results]
    assert any('virome' in t.lower() for t in titles)
    assert not any('protein folding' in t.lower() for t in titles)


def test_search_openalex_relevance_filter():
    """Test that irrelevant results are filtered out."""
    fixture = _load_fixture()
    results, error = openalex.search_openalex(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['results']
    )
    assert error is None
    for r in results:
        assert r['relevance'] > 0.1


def test_relevance_scores_populated():
    """Test that relevance scores and explanations are populated."""
    fixture = _load_fixture()
    results, error = openalex.search_openalex(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['results']
    )
    assert error is None
    for r in results:
        assert 'relevance' in r
        assert 'why_relevant' in r
        assert r['relevance'] > 0
        assert len(r['why_relevant']) > 0


def test_depth_limits():
    """Test that depth limits cap results."""
    fixture = _load_fixture()
    results, error = openalex.search_openalex(
        "virome", "2025-01-01", "2025-01-31", depth="quick",
        mock_data=fixture['results']
    )
    assert error is None
    assert len(results) <= openalex.DEPTH_LIMITS['quick']


def test_reconstruct_abstract():
    """Test abstract reconstruction from inverted index."""
    inverted_index = {
        "The": [0],
        "quick": [1],
        "brown": [2],
        "fox": [3],
    }
    result = openalex._reconstruct_abstract(inverted_index)
    assert result == "The quick brown fox"


def test_reconstruct_abstract_empty():
    """Test abstract reconstruction with empty/None input."""
    assert openalex._reconstruct_abstract(None) == ""
    assert openalex._reconstruct_abstract({}) == ""


def test_extract_doi():
    """Test DOI extraction from OpenAlex URL format."""
    assert openalex._extract_doi("https://doi.org/10.1038/xxx") == "10.1038/xxx"
    assert openalex._extract_doi("http://doi.org/10.1038/xxx") == "10.1038/xxx"
    assert openalex._extract_doi(None) is None
    assert openalex._extract_doi("10.1038/xxx") == "10.1038/xxx"


def test_extract_authors():
    """Test author extraction from authorships list."""
    authorships = [
        {"author": {"display_name": "Alice Chen"}},
        {"author": {"display_name": "Bob Smith"}},
    ]
    result = openalex._extract_authors(authorships)
    assert result == "Alice Chen, Bob Smith"
    assert openalex._extract_authors([]) == ""


def test_mock_result_fields():
    """Test that mock results contain all expected fields."""
    fixture = _load_fixture()
    results, error = openalex.search_openalex(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['results']
    )
    assert error is None
    assert len(results) > 0
    item = results[0]
    required_fields = [
        'openalex_id', 'title', 'authors', 'abstract', 'doi',
        'publication_date', 'source_name', 'source_type', 'work_type',
        'cited_by_count', 'url', 'relevance', 'why_relevant', 'source',
        'primary_topic_name', 'primary_topic_score',
    ]
    for field in required_fields:
        assert field in item, f"Missing field: {field}"


def test_discover_topics():
    """Test discover_topics extracts topic IDs from API response."""
    mock_response = {
        "results": [
            {"id": "https://openalex.org/T11048", "display_name": "Bacteriophages and microbial interactions"},
            {"id": "https://openalex.org/T10066", "display_name": "Viral Metagenomics"},
            {"id": "https://openalex.org/T12345", "display_name": "Gut Microbiome"},
        ]
    }
    with patch.object(openalex.http, 'get', return_value=mock_response):
        ids = openalex.discover_topics("virome")
    assert ids == ["T11048", "T10066", "T12345"]


def test_discover_topics_error_returns_empty():
    """Test discover_topics returns empty list on error."""
    with patch.object(openalex.http, 'get', side_effect=Exception("network error")):
        ids = openalex.discover_topics("virome")
    assert ids == []


def test_discover_topics_empty_results():
    """Test discover_topics with no results returns empty list."""
    with patch.object(openalex.http, 'get', return_value={"results": []}):
        ids = openalex.discover_topics("xyznonexistent")
    assert ids == []


def test_primary_topic_extracted():
    """Test that mock results include primary_topic_name and primary_topic_score."""
    fixture = _load_fixture()
    results, error = openalex.search_openalex(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['results']
    )
    assert error is None
    assert len(results) > 0
    for r in results:
        assert 'primary_topic_name' in r, "Missing primary_topic_name"
        assert 'primary_topic_score' in r, "Missing primary_topic_score"
        # The virome papers should have the bacteriophage topic
        assert r['primary_topic_name'] == "Bacteriophages and microbial interactions"
        assert r['primary_topic_score'] == 0.9998
