"""Tests for normalize module."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import normalize, schema


def test_compute_keyword_relevance_exact_phrase():
    """Test exact phrase match in title gets high score."""
    score, why = normalize.compute_keyword_relevance(
        "CRISPR gene editing",
        "CRISPR gene editing in human cells",
        "Abstract about the method.",
    )
    assert score >= 0.5
    assert "exact phrase in title" in why


def test_compute_keyword_relevance_partial_match():
    """Test partial keyword match."""
    score, why = normalize.compute_keyword_relevance(
        "CRISPR gene editing",
        "New approaches to gene therapy",
        "Using CRISPR tools for editing.",
    )
    assert 0.0 < score < 1.0


def test_compute_keyword_relevance_no_match():
    """Test no match returns low score."""
    score, why = normalize.compute_keyword_relevance(
        "quantum computing",
        "CRISPR gene editing in T cells",
        "This is about biology and genetics.",
    )
    assert score < 0.2


def test_compute_keyword_relevance_abstract_match():
    """Test phrase match in abstract."""
    score, why = normalize.compute_keyword_relevance(
        "machine learning",
        "A new computational method",
        "We applied machine learning to predict outcomes.",
    )
    assert score > 0.2
    assert "abstract" in why.lower()


def test_normalize_biorxiv_items():
    """Test normalizing bioRxiv items to schema."""
    raw = [{
        'doi': '10.1101/2025.01.15.123456',
        'title': 'Test Paper',
        'authors': 'Smith, J; Jones, A',
        'abstract': 'Test abstract',
        'category': 'Molecular Biology',
        'date': '2025-01-15',
        'source': 'biorxiv',
        'relevance': 0.8,
        'why_relevant': 'exact match',
    }]
    items = normalize.normalize_biorxiv_items(raw, '2025-01-01', '2025-01-31')
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, schema.BiorxivItem)
    assert item.preprint_doi == '10.1101/2025.01.15.123456'
    assert item.source == 'biorxiv'
    assert item.date_confidence == 'high'


def test_normalize_arxiv_items():
    """Test normalizing arXiv items to schema."""
    raw = [{
        'arxiv_id': '2501.12345v1',
        'title': 'Test ML Paper',
        'authors': 'Zhang, A, Kumar, B',
        'abstract': 'Test abstract',
        'published': '2025-01-14T18:00:00Z',
        'primary_category': 'cs.LG',
        'categories': ['cs.LG', 'q-bio.GN'],
        'link': 'http://arxiv.org/abs/2501.12345v1',
        'author_count': 2,
        'relevance': 0.7,
        'why_relevant': 'keyword match',
    }]
    items = normalize.normalize_arxiv_items(raw, '2025-01-01', '2025-01-31')
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, schema.ArxivItem)
    assert item.arxiv_id == '2501.12345v1'
    assert item.date == '2025-01-14'
    assert item.primary_category == 'cs.LG'


def test_normalize_pubmed_items():
    """Test normalizing PubMed items to schema."""
    raw = [{
        'pmid': '39000001',
        'title': 'Clinical Trial Paper',
        'authors': 'Thompson R, Liu W',
        'abstract': 'Test abstract about clinical trial',
        'journal': 'Nature Biotechnology',
        'doi': '10.1038/nbt.2025.001',
        'pub_date': '2025-01-15',
        'author_count': 2,
        'relevance': 0.9,
        'why_relevant': 'high relevance',
    }]
    items = normalize.normalize_pubmed_items(raw, '2025-01-01', '2025-01-31')
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, schema.PubmedItem)
    assert item.pmid == '39000001'
    assert item.journal == 'Nature Biotechnology'
    assert item.engagement.published_doi == '10.1038/nbt.2025.001'


def test_normalize_huggingface_items():
    """Test normalizing HuggingFace items to schema."""
    raw = [{
        'hf_id': 'biolab/crispr-model',
        'title': 'crispr-model',
        'author': 'biolab',
        'item_type': 'model',
        'tags': ['biology', 'crispr'],
        'date': '2025-01-12',
        'downloads': 1500,
        'likes': 42,
        'url': 'https://huggingface.co/biolab/crispr-model',
        'relevance': 0.6,
        'why_relevant': 'tag match',
    }]
    items = normalize.normalize_huggingface_items(raw, '2025-01-01', '2025-01-31')
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, schema.HuggingFaceItem)
    assert item.item_type == 'model'
    assert item.engagement.downloads == 1500
    assert item.engagement.likes == 42


def test_bigram_matching_boosts_consecutive_words():
    """Test that consecutive topic words appearing together get a bonus."""
    # "labor market" as a bigram should score higher than "labor" + "AI" separately
    score_with_bigram, why1 = normalize.compute_keyword_relevance(
        "labor market AI impacts",
        "Effects on the labor market from automation",
        "Analysis of labor market disruptions",
    )
    score_without_bigram, why2 = normalize.compute_keyword_relevance(
        "labor market AI impacts",
        "Labor relations in AI systems",
        "A study of labor in industrial settings",
    )
    assert score_with_bigram > score_without_bigram
    assert "bigram" in why1.lower()


def test_bigram_matching_single_word_topic():
    """Test that single-word topics don't crash on bigram matching."""
    score, why = normalize.compute_keyword_relevance(
        "CRISPR",
        "CRISPR in cells",
        "About CRISPR editing",
    )
    assert score > 0
    assert "bigram" not in why.lower()


def test_bigram_matching_two_word_topic():
    """Test bigram matching works with two-word topics."""
    score_match, _ = normalize.compute_keyword_relevance(
        "gene editing",
        "Advances in gene editing technology",
        "",
    )
    score_split, _ = normalize.compute_keyword_relevance(
        "gene editing",
        "Gene therapy and video editing tools",
        "",
    )
    assert score_match > score_split


def test_filter_by_date_range():
    """Test date filtering."""
    items = [
        schema.BiorxivItem(id='1', preprint_doi='d1', title='Old', authors='', abstract='', category='', source='biorxiv', url='', date='2024-12-01'),
        schema.BiorxivItem(id='2', preprint_doi='d2', title='In range', authors='', abstract='', category='', source='biorxiv', url='', date='2025-01-15'),
        schema.BiorxivItem(id='3', preprint_doi='d3', title='No date', authors='', abstract='', category='', source='biorxiv', url='', date=None),
        schema.BiorxivItem(id='4', preprint_doi='d4', title='Future', authors='', abstract='', category='', source='biorxiv', url='', date='2026-06-01'),
    ]
    filtered = normalize.filter_by_date_range(items, '2025-01-01', '2025-01-31')
    titles = [i.title for i in filtered]
    assert 'In range' in titles
    assert 'No date' in titles  # kept by default
    assert 'Old' not in titles
    assert 'Future' not in titles
