"""Tests for score module."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import schema, score


def test_score_biorxiv_peer_reviewed_bonus():
    """Test that peer-reviewed papers get higher academic score."""
    preprint = schema.BiorxivItem(
        id='1', preprint_doi='d1', title='Preprint', authors='', abstract='',
        category='', source='biorxiv', url='', date='2025-01-15',
        date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(),
    )
    peer_reviewed = schema.BiorxivItem(
        id='2', preprint_doi='d2', title='Published', authors='', abstract='',
        category='', source='biorxiv', url='', date='2025-01-15',
        date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(published_doi='10.1038/xxx'),
    )

    scored = score.score_biorxiv_items([preprint, peer_reviewed])
    assert scored[1].score > scored[0].score


def test_score_arxiv_popular_category_bonus():
    """Test that popular categories get bonus."""
    popular = schema.ArxivItem(
        id='1', arxiv_id='a1', title='ML Paper', authors='', abstract='',
        primary_category='cs.LG', categories=['cs.LG'], url='',
        date='2025-01-15', date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(),
    )
    niche = schema.ArxivItem(
        id='2', arxiv_id='a2', title='Niche Paper', authors='', abstract='',
        primary_category='hep-th', categories=['hep-th'], url='',
        date='2025-01-15', date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(),
    )

    scored = score.score_arxiv_items([popular, niche])
    assert scored[0].score >= scored[1].score  # popular category gets bonus


def test_score_pubmed_journal_bonus():
    """Test that journal publication gives bonus."""
    item = schema.PubmedItem(
        id='1', pmid='p1', title='Journal Paper', authors='', abstract='',
        journal='Nature', doi='10.1038/xxx', url='',
        date='2025-01-15', date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(published_journal='Nature'),
    )
    scored = score.score_pubmed_items([item])
    assert scored[0].score > 0
    assert scored[0].subs.engagement > 40  # base + journal bonus


def test_score_huggingface_downloads_likes():
    """Test that downloads and likes affect HF score."""
    popular = schema.HuggingFaceItem(
        id='1', hf_id='h1', title='Popular Model', author='', item_type='model',
        tags=[], url='', date='2025-01-15', date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(downloads=10000, likes=500),
    )
    unpopular = schema.HuggingFaceItem(
        id='2', hf_id='h2', title='Unpopular Model', author='', item_type='model',
        tags=[], url='', date='2025-01-15', date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(downloads=5, likes=1),
    )

    scored = score.score_huggingface_items([popular, unpopular])
    assert scored[0].score > scored[1].score


def test_score_low_date_confidence_penalty():
    """Test that low date confidence reduces score."""
    high = schema.BiorxivItem(
        id='1', preprint_doi='d1', title='T', authors='', abstract='',
        category='', source='biorxiv', url='', date='2025-01-15',
        date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(),
    )
    low = schema.BiorxivItem(
        id='2', preprint_doi='d2', title='T', authors='', abstract='',
        category='', source='biorxiv', url='', date=None,
        date_confidence='low', relevance=0.8,
        engagement=schema.AcademicEngagement(),
    )

    scored = score.score_biorxiv_items([high, low])
    assert scored[0].score > scored[1].score


def test_sort_items():
    """Test sorting by score descending."""
    items = [
        schema.BiorxivItem(id='1', preprint_doi='d1', title='Low', authors='', abstract='',
                           category='', source='biorxiv', url='', score=30),
        schema.BiorxivItem(id='2', preprint_doi='d2', title='High', authors='', abstract='',
                           category='', source='biorxiv', url='', score=80),
        schema.BiorxivItem(id='3', preprint_doi='d3', title='Mid', authors='', abstract='',
                           category='', source='biorxiv', url='', score=50),
    ]
    sorted_items = score.sort_items(items)
    assert sorted_items[0].title == 'High'
    assert sorted_items[1].title == 'Mid'
    assert sorted_items[2].title == 'Low'


def test_scores_clamped_0_100():
    """Test that scores are clamped between 0 and 100."""
    item = schema.PubmedItem(
        id='1', pmid='p1', title='T', authors='', abstract='',
        journal='', doi=None, url='', date='2025-01-15',
        date_confidence='high', relevance=1.0,
        engagement=schema.AcademicEngagement(
            published_journal='Nature', citation_count=10000
        ),
    )
    scored = score.score_pubmed_items([item])
    assert 0 <= scored[0].score <= 100
