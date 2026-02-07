"""Tests for dedupe module."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import dedupe, schema


def test_doi_dedup():
    """Test DOI-based deduplication."""
    pubmed_item = schema.PubmedItem(
        id='pubmed:1', pmid='1', title='CRISPR Paper', authors='', abstract='',
        journal='Nature', doi='10.1038/xxx', url='', date='2025-01-15',
        score=80,
    )
    biorxiv_item = schema.BiorxivItem(
        id='biorxiv:1', preprint_doi='10.1101/yyy', title='CRISPR Paper Preprint',
        authors='', abstract='', category='', source='biorxiv', url='',
        date='2025-01-10', score=60,
        engagement=schema.AcademicEngagement(published_doi='10.1038/xxx'),
    )

    result = dedupe.dedupe_cross_source([pubmed_item, biorxiv_item])
    assert len(result) == 1
    # PubMed should be kept (higher priority)
    assert isinstance(result[0], schema.PubmedItem)


def test_jaccard_title_dedup():
    """Test Jaccard title similarity deduplication."""
    item1 = schema.ArxivItem(
        id='arxiv:1', arxiv_id='a1',
        title='Deep Learning for CRISPR Guide RNA Design Optimization',
        authors='', abstract='', primary_category='cs.LG', categories=[],
        url='', date='2025-01-15', score=70,
    )
    item2 = schema.BiorxivItem(
        id='biorxiv:1', preprint_doi='d1',
        title='Deep Learning for CRISPR Guide RNA Design and Optimization',
        authors='', abstract='', category='', source='biorxiv',
        url='', date='2025-01-14', score=60,
    )

    result = dedupe.dedupe_cross_source([item1, item2], threshold=0.7)
    # Should dedupe one — keep the higher priority source (biorxiv > arxiv)
    assert len(result) == 1


def test_no_false_dedup():
    """Test that dissimilar titles are NOT deduped."""
    item1 = schema.ArxivItem(
        id='arxiv:1', arxiv_id='a1',
        title='Deep Learning for Protein Folding',
        authors='', abstract='', primary_category='cs.LG', categories=[],
        url='', date='2025-01-15', score=70,
    )
    item2 = schema.PubmedItem(
        id='pubmed:1', pmid='1',
        title='Clinical Trial of CRISPR Gene Therapy',
        authors='', abstract='', journal='', doi=None, url='',
        date='2025-01-14', score=60,
    )

    result = dedupe.dedupe_cross_source([item1, item2])
    assert len(result) == 2


def test_source_priority():
    """Test that PubMed wins over arXiv when titles match."""
    pubmed = schema.PubmedItem(
        id='pubmed:1', pmid='1',
        title='Novel Gene Editing Method for Cancer Treatment',
        authors='', abstract='', journal='Nature', doi=None, url='',
        date='2025-01-15', score=60,
    )
    arxiv = schema.ArxivItem(
        id='arxiv:1', arxiv_id='a1',
        title='Novel Gene Editing Method for Cancer Treatment',
        authors='', abstract='', primary_category='cs.LG', categories=[],
        url='', date='2025-01-15', score=80,
    )

    result = dedupe.dedupe_cross_source([pubmed, arxiv])
    assert len(result) == 1
    assert isinstance(result[0], schema.PubmedItem)


def test_dedupe_within_source():
    """Test within-source deduplication."""
    items = [
        schema.ArxivItem(
            id='1', arxiv_id='a1', title='Method A for solving problem X',
            authors='', abstract='', primary_category='', categories=[], url='', score=80,
        ),
        schema.ArxivItem(
            id='2', arxiv_id='a2', title='Method A for solving problem X v2',
            authors='', abstract='', primary_category='', categories=[], url='', score=60,
        ),
        schema.ArxivItem(
            id='3', arxiv_id='a3', title='Completely different topic',
            authors='', abstract='', primary_category='', categories=[], url='', score=50,
        ),
    ]
    result = dedupe.dedupe_within_source(items, threshold=0.7)
    assert len(result) == 2  # first two are near-dupes


def test_empty_input():
    """Test with empty input."""
    assert dedupe.dedupe_cross_source([]) == []
    assert dedupe.dedupe_within_source([]) == []


def test_single_item():
    """Test with single item."""
    item = schema.ArxivItem(
        id='1', arxiv_id='a1', title='Solo paper', authors='', abstract='',
        primary_category='', categories=[], url='',
    )
    assert dedupe.dedupe_cross_source([item]) == [item]
    assert dedupe.dedupe_within_source([item]) == [item]


def test_normalize_text():
    """Test text normalization for comparison."""
    assert dedupe.normalize_text("Hello, World!") == "hello world"
    assert dedupe.normalize_text("  SPACES   EVERYWHERE  ") == "spaces everywhere"


def test_jaccard_similarity():
    """Test Jaccard similarity computation."""
    s1 = {'a', 'b', 'c'}
    s2 = {'b', 'c', 'd'}
    sim = dedupe.jaccard_similarity(s1, s2)
    assert abs(sim - 0.5) < 0.01  # 2/4 = 0.5
