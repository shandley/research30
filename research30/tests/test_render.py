"""Tests for render module."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import render, schema


def _make_report():
    """Create a test report."""
    return schema.Report(
        topic="CRISPR gene editing",
        range_from="2025-01-01",
        range_to="2025-01-31",
        generated_at="2025-01-20T12:00:00Z",
        mode="all",
        biorxiv=[
            schema.BiorxivItem(
                id='biorxiv:d1', preprint_doi='10.1101/d1', title='CRISPR in T Cells',
                authors='Smith J', abstract='About CRISPR', category='Molecular Biology',
                source='biorxiv', url='https://doi.org/10.1101/d1', date='2025-01-15',
                date_confidence='high', relevance=0.9, why_relevant='exact phrase',
                score=75,
                engagement=schema.AcademicEngagement(published_doi='10.1038/pub1'),
            ),
        ],
        arxiv=[
            schema.ArxivItem(
                id='arxiv:a1', arxiv_id='2501.12345', title='Deep Learning for CRISPR',
                authors='Zhang A', abstract='ML for gRNA', primary_category='cs.LG',
                categories=['cs.LG', 'q-bio.GN'], url='http://arxiv.org/abs/2501.12345',
                date='2025-01-14', date_confidence='high', relevance=0.8,
                why_relevant='keyword match', score=70,
            ),
        ],
        pubmed=[
            schema.PubmedItem(
                id='pubmed:1', pmid='39000001', title='Clinical CRISPR Trial',
                authors='Thompson R', abstract='Clinical trial results', journal='Nature Biotechnology',
                doi='10.1038/nbt.001', url='https://pubmed.ncbi.nlm.nih.gov/39000001/',
                date='2025-01-15', date_confidence='high', relevance=0.95,
                why_relevant='highly relevant', score=85,
            ),
        ],
        huggingface=[
            schema.HuggingFaceItem(
                id='hf:m1', hf_id='biolab/crispr-model', title='crispr-model',
                author='biolab', item_type='model', tags=['crispr'],
                url='https://huggingface.co/biolab/crispr-model',
                date='2025-01-12', date_confidence='high', relevance=0.7,
                why_relevant='tag match', score=60,
                engagement=schema.AcademicEngagement(downloads=1500, likes=42),
            ),
        ],
    )


def test_render_compact_header():
    """Test compact output has proper header."""
    report = _make_report()
    output = render.render_compact(report)
    assert "CRISPR gene editing" in output
    assert "2025-01-01" in output
    assert "2025-01-31" in output


def test_render_compact_sources():
    """Test compact output includes all sources."""
    report = _make_report()
    output = render.render_compact(report)
    assert "bioRxiv Preprints" in output
    assert "arXiv Papers" in output
    assert "PubMed Articles" in output
    assert "HuggingFace" in output


def test_render_compact_peer_reviewed_flag():
    """Test that peer reviewed items are flagged."""
    report = _make_report()
    output = render.render_compact(report)
    assert "PEER REVIEWED" in output


def test_render_compact_scores():
    """Test that scores are shown."""
    report = _make_report()
    output = render.render_compact(report)
    assert "score:75" in output
    assert "score:85" in output


def test_render_compact_errors():
    """Test that errors are shown."""
    report = _make_report()
    report.arxiv_error = "Connection timeout"
    report.arxiv = []
    output = render.render_compact(report)
    assert "ERROR" in output
    assert "Connection timeout" in output


def test_render_compact_empty_report():
    """Test rendering with no items."""
    report = schema.Report(
        topic="nothing", range_from="2025-01-01", range_to="2025-01-31",
        generated_at="2025-01-20T12:00:00Z", mode="all",
    )
    output = render.render_compact(report)
    assert "nothing" in output
    assert "LIMITED RECENT DATA" in output


def test_render_context_snippet():
    """Test context snippet output."""
    report = _make_report()
    output = render.render_context_snippet(report)
    assert "Context" in output
    assert "CRISPR gene editing" in output
    assert "Key Sources" in output


def test_render_full_report():
    """Test full markdown report."""
    report = _make_report()
    output = render.render_full_report(report)
    assert "# CRISPR gene editing" in output
    assert "Nature Biotechnology" in output
    assert "arXiv" in output
    assert "PubMed" in output


def test_render_huggingface_implementations():
    """Test HuggingFace implementation rendering."""
    report = _make_report()
    output = render.render_compact(report)
    assert "HuggingFace Implementations" in output
    assert "1500 downloads" in output
    assert "42 likes" in output


def test_render_cached_indicator():
    """Test cached results indicator."""
    report = _make_report()
    report.from_cache = True
    report.cache_age_hours = 2.5
    output = render.render_compact(report)
    assert "CACHED" in output
    assert "2.5h" in output
