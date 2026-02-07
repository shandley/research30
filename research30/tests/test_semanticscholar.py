"""Tests for semanticscholar module."""

import json
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
FIXTURES_DIR = TESTS_DIR.parent / "fixtures"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import semanticscholar


def _load_fixture():
    """Load sample Semantic Scholar fixture."""
    with open(FIXTURES_DIR / "semanticscholar_sample.json") as f:
        return json.load(f)


def test_search_s2_mock():
    """Test search with mock data returns relevant results."""
    fixture = _load_fixture()
    results, error = semanticscholar.search_semantic_scholar(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['data']
    )
    assert error is None
    assert len(results) >= 1
    titles = [r['title'] for r in results]
    assert any('virome' in t.lower() for t in titles)
    # Should NOT include the zinc finger paper
    assert not any('zinc finger' in t.lower() for t in titles)


def test_search_s2_relevance_filter():
    """Test that irrelevant results are filtered out."""
    fixture = _load_fixture()
    results, error = semanticscholar.search_semantic_scholar(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['data']
    )
    assert error is None
    for r in results:
        assert r['relevance'] > 0.3


def test_relevance_scores_populated():
    """Test that relevance scores and explanations are populated."""
    fixture = _load_fixture()
    results, error = semanticscholar.search_semantic_scholar(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['data']
    )
    assert error is None
    for r in results:
        assert r['relevance'] > 0
        assert len(r['why_relevant']) > 0


def test_depth_limits():
    """Test that depth limits cap results."""
    fixture = _load_fixture()
    results, error = semanticscholar.search_semantic_scholar(
        "virome", "2025-01-01", "2025-01-31", depth="quick",
        mock_data=fixture['data']
    )
    assert error is None
    assert len(results) <= semanticscholar.DEPTH_LIMITS['quick']


def test_extract_authors():
    """Test author extraction from S2 authors list."""
    authors = [
        {"authorId": "1", "name": "Alice Chen"},
        {"authorId": "2", "name": "Bob Smith"},
    ]
    result = semanticscholar._extract_authors(authors)
    assert result == "Alice Chen, Bob Smith"
    assert semanticscholar._extract_authors([]) == ""


def test_extract_doi():
    """Test DOI extraction from externalIds."""
    assert semanticscholar._extract_doi({"DOI": "10.1038/xxx"}) == "10.1038/xxx"
    assert semanticscholar._extract_doi({"ArXiv": "2501.12345"}) is None
    assert semanticscholar._extract_doi(None) is None
    assert semanticscholar._extract_doi({}) is None


def test_build_url_prefers_oa():
    """Test URL building prefers open access PDF."""
    paper = {
        "openAccessPdf": {"url": "https://example.com/paper.pdf"},
        "externalIds": {"DOI": "10.1038/xxx"},
        "url": "https://www.semanticscholar.org/paper/abc",
    }
    assert semanticscholar._build_url(paper) == "https://example.com/paper.pdf"


def test_build_url_falls_back_to_doi():
    """Test URL building falls back to DOI when no OA PDF."""
    paper = {
        "openAccessPdf": None,
        "externalIds": {"DOI": "10.1038/xxx"},
        "url": "https://www.semanticscholar.org/paper/abc",
    }
    assert semanticscholar._build_url(paper) == "https://doi.org/10.1038/xxx"


def test_mock_result_fields():
    """Test that mock results contain all expected fields."""
    fixture = _load_fixture()
    results, error = semanticscholar.search_semantic_scholar(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['data']
    )
    assert error is None
    assert len(results) > 0
    item = results[0]
    required_fields = [
        'paper_id', 'title', 'authors', 'abstract', 'doi',
        'venue', 'publication_types', 'cited_by_count',
        'influential_citations', 'publication_date', 'url',
        'relevance', 'why_relevant', 'source',
    ]
    for field in required_fields:
        assert field in item, f"Missing field: {field}"


def test_citation_data_preserved():
    """Test that citation counts are preserved in results."""
    fixture = _load_fixture()
    results, error = semanticscholar.search_semantic_scholar(
        "virome", "2025-01-01", "2025-01-31", mock_data=fixture['data']
    )
    assert error is None
    # First result should have citations
    gut_paper = [r for r in results if 'gut' in r['title'].lower()]
    assert len(gut_paper) > 0
    assert gut_paper[0]['cited_by_count'] == 12
    assert gut_paper[0]['influential_citations'] == 3
