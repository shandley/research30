"""Tests for pubmed module."""

import json
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import pubmed, xml_parse

FIXTURES_DIR = TESTS_DIR.parent / "fixtures"


def load_esearch():
    with open(FIXTURES_DIR / "pubmed_esearch_sample.json") as f:
        return json.load(f)


def load_efetch():
    with open(FIXTURES_DIR / "pubmed_efetch_sample.xml") as f:
        return f.read()


def test_search_pubmed_mock():
    """Test PubMed search with mock data."""
    esearch = load_esearch()
    efetch = load_efetch()
    items, error = pubmed.search_pubmed(
        topic="CRISPR gene editing",
        from_date="2025-01-01",
        to_date="2025-01-31",
        depth="default",
        mock_esearch=esearch,
        mock_efetch=efetch,
    )
    assert error is None
    assert len(items) == 3


def test_pubmed_article_fields():
    """Test that articles have all required fields."""
    esearch = load_esearch()
    efetch = load_efetch()
    items, _ = pubmed.search_pubmed(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_esearch=esearch,
        mock_efetch=efetch,
    )
    assert len(items) > 0
    article = items[0]
    assert 'pmid' in article
    assert 'title' in article
    assert 'authors' in article
    assert 'abstract' in article
    assert 'journal' in article
    assert 'doi' in article
    assert 'pub_date' in article
    assert 'relevance' in article


def test_pubmed_journal_names():
    """Test that journal names are extracted."""
    esearch = load_esearch()
    efetch = load_efetch()
    items, _ = pubmed.search_pubmed(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_esearch=esearch,
        mock_efetch=efetch,
    )
    journals = [i['journal'] for i in items]
    assert "Nature Biotechnology" in journals
    assert "Science" in journals
    assert "Cell" in journals


def test_pubmed_dois():
    """Test that DOIs are extracted."""
    esearch = load_esearch()
    efetch = load_efetch()
    items, _ = pubmed.search_pubmed(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_esearch=esearch,
        mock_efetch=efetch,
    )
    dois = [i['doi'] for i in items if i.get('doi')]
    assert len(dois) == 3
    assert "10.1038/nbt.2025.001" in dois


def test_pubmed_structured_abstract():
    """Test that structured abstracts are properly joined."""
    esearch = load_esearch()
    efetch = load_efetch()
    items, _ = pubmed.search_pubmed(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_esearch=esearch,
        mock_efetch=efetch,
    )
    # First article has structured abstract with labels
    article = [i for i in items if i['pmid'] == '39000001'][0]
    assert "BACKGROUND:" in article['abstract']
    assert "RESULTS:" in article['abstract']


def test_pubmed_mesh_terms():
    """Test that MeSH terms are extracted from the fixture."""
    esearch = load_esearch()
    efetch = load_efetch()
    items, _ = pubmed.search_pubmed(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_esearch=esearch,
        mock_efetch=efetch,
    )
    # First article: CRISPR retinal
    article1 = [i for i in items if i['pmid'] == '39000001'][0]
    assert article1['mesh_terms'] == ['CRISPR-Cas Systems', 'Gene Editing', 'Retinal Diseases']

    # Second article: sickle cell
    article2 = [i for i in items if i['pmid'] == '39000002'][0]
    assert article2['mesh_terms'] == ['Anemia, Sickle Cell', 'Gene Editing']

    # Third article: epigenetic
    article3 = [i for i in items if i['pmid'] == '39000003'][0]
    assert article3['mesh_terms'] == ['Epigenesis, Genetic', 'Gene Silencing', 'Neoplasms']


def test_pubmed_query_translation():
    """Test that querytranslation is captured from the esearch fixture."""
    esearch = load_esearch()
    efetch = load_efetch()
    items, _ = pubmed.search_pubmed(
        topic="CRISPR gene editing",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_esearch=esearch,
        mock_efetch=efetch,
    )
    assert len(items) > 0
    # Every article should carry the query_translation from esearch
    for article in items:
        assert 'query_translation' in article
        assert len(article['query_translation']) > 0
        assert 'TIAB' in article['query_translation']


def test_build_query_single_word():
    """Test _build_query with a single word produces TIAB tag."""
    result = pubmed._build_query("virome")
    assert result == "virome[TIAB]"


def test_build_query_multi_word():
    """Test _build_query with multi-word topic produces combined TIAB query."""
    result = pubmed._build_query("CRISPR gene editing")
    expected = '("CRISPR gene editing"[TIAB] OR (CRISPR[TIAB] AND gene[TIAB] AND editing[TIAB]))'
    assert result == expected
