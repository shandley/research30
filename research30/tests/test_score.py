"""Tests for score module."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import schema, score


def test_peer_review_does_not_change_score():
    """Peer-review status is a badge, not a score input. With relevance and
    date held equal, a preprint and its published version score the same."""
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
    assert scored[0].score == scored[1].score
    # The peer-review signal is preserved on the item for the badge.
    assert scored[1].engagement.published_doi == '10.1038/xxx'


def test_arxiv_category_does_not_change_score():
    """Category is not a quality signal. Same relevance and date, same score."""
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
    assert scored[0].score == scored[1].score


def test_journal_does_not_change_score():
    """Journal publication is a badge, not a score bonus. Two items with the
    same relevance and date score identically regardless of journal."""
    with_journal = schema.PubmedItem(
        id='1', pmid='p1', title='Journal Paper', authors='', abstract='',
        journal='Nature', doi='10.1038/xxx', url='',
        date='2025-01-15', date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(published_journal='Nature'),
    )
    without_journal = schema.PubmedItem(
        id='2', pmid='p2', title='No Journal', authors='', abstract='',
        journal='', doi=None, url='',
        date='2025-01-15', date_confidence='high', relevance=0.8,
        engagement=schema.AcademicEngagement(),
    )
    scored = score.score_pubmed_items([with_journal, without_journal])
    assert scored[0].score == scored[1].score
    assert scored[0].score > 0
    # score is relevance + recency only, no academic component
    assert scored[0].subs.engagement == 0


def test_hf_downloads_do_not_change_score():
    """Deliberate: HuggingFace uses the same relevance+recency score as every
    other source. Downloads and likes are real per-model signals, but they are
    shown as badges rather than folded into the number, for consistency."""
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
    assert scored[0].score == scored[1].score
    # Download counts remain available for the badge.
    assert scored[0].engagement.downloads == 10000


def test_score_is_relevance_plus_recency():
    """The score is 0.70*relevance + 0.30*recency (high date confidence)."""
    item = schema.BiorxivItem(
        id='1', preprint_doi='d1', title='T', authors='', abstract='',
        category='', source='biorxiv', url='', date='2025-01-15',
        date_confidence='high', relevance=0.9,
        engagement=schema.AcademicEngagement(),
    )
    scored = score.score_biorxiv_items([item])
    rel = scored[0].subs.relevance  # 90
    rec = scored[0].subs.recency
    expected = int(0.70 * rel + 0.30 * rec)
    assert scored[0].score == max(0, min(100, expected))


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
