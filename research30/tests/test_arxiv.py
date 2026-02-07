"""Tests for arxiv module."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import arxiv

FIXTURES_DIR = TESTS_DIR.parent / "fixtures"


def load_fixture():
    with open(FIXTURES_DIR / "arxiv_sample.xml") as f:
        return f.read()


def test_search_arxiv_mock():
    """Test arXiv search with mock XML."""
    xml = load_fixture()
    items, error = arxiv.search_arxiv(
        topic="CRISPR gene editing",
        from_date="2025-01-01",
        to_date="2025-01-31",
        depth="default",
        mock_data=xml,
    )
    assert error is None
    assert len(items) >= 1
    # Check that the CRISPR paper is found
    assert any("CRISPR" in item.get('title', '') for item in items)


def test_arxiv_paper_fields():
    """Test that parsed papers have all required fields."""
    xml = load_fixture()
    items, _ = arxiv.search_arxiv(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_data=xml,
    )
    assert len(items) > 0
    paper = items[0]
    assert 'arxiv_id' in paper
    assert 'title' in paper
    assert 'authors' in paper
    assert 'abstract' in paper
    assert 'published' in paper
    assert 'primary_category' in paper
    assert 'categories' in paper
    assert 'relevance' in paper
    assert 'why_relevant' in paper


def test_arxiv_categories():
    """Test that categories are properly parsed."""
    xml = load_fixture()
    items, _ = arxiv.search_arxiv(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_data=xml,
    )
    crispr_paper = [i for i in items if "CRISPR" in i['title']]
    assert len(crispr_paper) > 0
    assert crispr_paper[0]['primary_category'] == 'cs.LG'
    assert 'q-bio.GN' in crispr_paper[0]['categories']


def test_arxiv_relevance_scoring():
    """Test relevance scores are computed."""
    xml = load_fixture()
    items, _ = arxiv.search_arxiv(
        topic="attention mechanisms language models",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_data=xml,
    )
    # The attention paper should have higher relevance for this query
    attention_papers = [i for i in items if "Attention" in i['title']]
    crispr_papers = [i for i in items if "CRISPR" in i['title']]
    if attention_papers and crispr_papers:
        assert attention_papers[0]['relevance'] > crispr_papers[0]['relevance']
