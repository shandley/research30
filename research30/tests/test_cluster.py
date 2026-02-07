"""Tests for cluster module."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import cluster, schema


def _make_openalex(title, topic_name, topic_score=0.9, score=80):
    return schema.OpenAlexItem(
        id=f"openalex:{title[:10]}",
        openalex_id=f"W{hash(title) % 100000}",
        title=title,
        authors="Author A",
        abstract=f"Abstract about {title}",
        doi=None,
        source_name="Test Journal",
        source_type="journal",
        work_type="article",
        url=f"https://example.com/{title[:5]}",
        primary_topic_name=topic_name,
        primary_topic_score=topic_score,
        date="2025-01-15",
        date_confidence="high",
        relevance=0.9,
        why_relevant="test",
        score=score,
    )


def _make_pubmed(title, mesh_terms=None, score=75):
    return schema.PubmedItem(
        id=f"pubmed:{hash(title) % 100000}",
        pmid=str(hash(title) % 100000),
        title=title,
        authors="Author B",
        abstract=f"Abstract about {title}",
        journal="Test Journal",
        doi=None,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{hash(title) % 100000}/",
        mesh_terms=mesh_terms or [],
        date="2025-01-15",
        date_confidence="high",
        relevance=0.8,
        why_relevant="test",
        score=score,
    )


def _make_arxiv(title, category="cs.AI", score=70):
    return schema.ArxivItem(
        id=f"arxiv:{hash(title) % 100000}",
        arxiv_id=f"2501.{hash(title) % 100000}",
        title=title,
        authors="Author C",
        abstract=f"Abstract about {title}",
        primary_category=category,
        categories=[category],
        url=f"https://arxiv.org/abs/2501.{hash(title) % 100000}",
        date="2025-01-15",
        date_confidence="high",
        relevance=0.7,
        why_relevant="test",
        score=score,
    )


def _make_s2(title, score=72):
    return schema.SemanticScholarItem(
        id=f"s2:{hash(title) % 100000}",
        paper_id=str(hash(title) % 100000),
        title=title,
        authors="Author D",
        abstract=f"Abstract about {title}",
        doi=None,
        venue="Test Venue",
        publication_types=["JournalArticle"],
        url=f"https://example.com/{hash(title) % 100000}",
        date="2025-01-15",
        date_confidence="high",
        relevance=0.7,
        why_relevant="test",
        score=score,
    )


def _make_biorxiv(title, category="Molecular Biology", score=65):
    return schema.BiorxivItem(
        id=f"biorxiv:{hash(title) % 100000}",
        preprint_doi=f"10.1101/{hash(title) % 100000}",
        title=title,
        authors="Author E",
        abstract=f"Abstract about {title}",
        category=category,
        source="biorxiv",
        url=f"https://doi.org/10.1101/{hash(title) % 100000}",
        date="2025-01-15",
        date_confidence="high",
        relevance=0.7,
        why_relevant="test",
        score=score,
    )


# --- Tests ---

def test_cluster_empty_input():
    """Empty input returns empty clusters."""
    result = cluster.cluster_by_theme([])
    assert result == []


def test_cluster_openalex_seeds():
    """OpenAlex items grouped by primary_topic_name."""
    items = [
        _make_openalex("CRISPR editing in plants", "CRISPR and Genetic Engineering", score=80),
        _make_openalex("Base editing advances", "CRISPR and Genetic Engineering", score=75),
        _make_openalex("Deep learning for proteins", "Machine Learning", score=70),
        _make_openalex("Neural network architectures", "Machine Learning", score=65),
    ]
    result = cluster.cluster_by_theme(items)
    names = [c.name for c in result]
    assert "CRISPR and Genetic Engineering" in names
    assert "Machine Learning" in names

    crispr = next(c for c in result if c.name == "CRISPR and Genetic Engineering")
    assert crispr.count == 2


def test_cluster_low_topic_score_excluded():
    """OpenAlex items with low topic scores don't seed clusters."""
    items = [
        _make_openalex("Low confidence topic", "Vague Topic", topic_score=0.3, score=60),
        _make_openalex("High confidence topic", "Good Topic", topic_score=0.9, score=80),
    ]
    result = cluster.cluster_by_theme(items)
    names = [c.name for c in result]
    assert "Good Topic" in names
    assert "Vague Topic" not in names


def test_cluster_pubmed_mesh_assignment():
    """PubMed items assigned to clusters via MeSH terms."""
    items = [
        _make_openalex("Genetic engineering advances", "Genetic Engineering", score=80),
        _make_pubmed(
            "CRISPR therapy for genetic diseases",
            mesh_terms=["Gene Editing", "Genetic Engineering", "CRISPR-Cas Systems"],
            score=75,
        ),
    ]
    result = cluster.cluster_by_theme(items)

    ge = next(c for c in result if c.name == "Genetic Engineering")
    assert ge.count == 2
    sources = {type(i).__name__ for i in ge.items}
    assert "PubmedItem" in sources
    assert "OpenAlexItem" in sources


def test_cluster_arxiv_category_assignment():
    """arXiv items assigned via category mapping."""
    items = [
        _make_openalex("Machine learning model", "Machine Learning", score=80),
        _make_arxiv("Neural network optimization", category="cs.LG", score=70),
    ]
    result = cluster.cluster_by_theme(items)

    ml = next(c for c in result if c.name == "Machine Learning")
    assert ml.count == 2


def test_cluster_title_fallback():
    """Items assigned via title keyword overlap when no better signal."""
    items = [
        _make_openalex("Cancer immunotherapy breakthroughs", "Cancer Immunotherapy", score=80),
        _make_s2("Novel cancer immunotherapy approaches using checkpoint inhibitors", score=72),
    ]
    result = cluster.cluster_by_theme(items)

    cancer = next(c for c in result if c.name == "Cancer Immunotherapy")
    assert cancer.count == 2


def test_cluster_unassigned_to_other():
    """Items with no match go to Other."""
    items = [
        _make_openalex("Genetic engineering topic", "Genetic Engineering", score=80),
        _make_s2("Completely unrelated quantum physics paper", score=50),
    ]
    result = cluster.cluster_by_theme(items)

    names = [c.name for c in result]
    assert "Other" in names
    other = next(c for c in result if c.name == "Other")
    assert other.count >= 1


def test_cluster_no_openalex_fallback():
    """When no OpenAlex items, fallback to categories."""
    items = [
        _make_arxiv("Deep learning for images", category="cs.CV", score=80),
        _make_arxiv("Object detection methods", category="cs.CV", score=75),
        _make_biorxiv("Protein folding study", category="Biophysics", score=70),
        _make_biorxiv("Membrane dynamics", category="Biophysics", score=65),
    ]
    result = cluster.cluster_by_theme(items)

    names = [c.name for c in result]
    assert "Computer Vision" in names
    assert "Biophysics" in names


def test_cluster_single_fallback():
    """When no clustering signals at all, single cluster."""
    items = [
        _make_s2("Paper one", score=80),
        _make_s2("Paper two", score=70),
    ]
    result = cluster.cluster_by_theme(items, fallback_name="My Topic")
    assert len(result) == 1
    assert result[0].name == "My Topic"
    assert result[0].count == 2


def test_cluster_small_merge():
    """Clusters with < MIN_CLUSTER_SIZE items get merged or go to Other."""
    items = [
        _make_openalex("Topic A paper 1", "Topic A", score=80),
        _make_openalex("Topic A paper 2", "Topic A", score=75),
        _make_openalex("Topic B lonely paper", "Topic B", score=60),
    ]
    result = cluster.cluster_by_theme(items)

    # Topic B has only 1 item, should be merged into Other or a similar cluster
    topic_b = [c for c in result if c.name == "Topic B"]
    assert len(topic_b) == 0  # Should not exist as standalone


def test_cluster_sorted_by_total_score():
    """Clusters sorted by total score descending."""
    items = [
        _make_openalex("Low score 1", "Low Score Topic", score=30),
        _make_openalex("Low score 2", "Low Score Topic", score=25),
        _make_openalex("High score 1", "High Score Topic", score=90),
        _make_openalex("High score 2", "High Score Topic", score=85),
    ]
    result = cluster.cluster_by_theme(items)

    # Filter out "Other" for this check
    themed = [c for c in result if c.name != "Other"]
    if len(themed) >= 2:
        assert themed[0].total_score >= themed[1].total_score


def test_cluster_items_sorted_by_score():
    """Items within a cluster sorted by score descending."""
    items = [
        _make_openalex("Low score paper", "My Topic", score=50),
        _make_openalex("High score paper", "My Topic", score=90),
        _make_openalex("Mid score paper", "My Topic", score=70),
    ]
    result = cluster.cluster_by_theme(items)

    topic = next(c for c in result if c.name == "My Topic")
    scores = [i.score for i in topic.items]
    assert scores == sorted(scores, reverse=True)


def test_tokenize():
    """Tokenize extracts meaningful words, skips stop words."""
    tokens = cluster._tokenize("The CRISPR and Genetic Engineering approach")
    assert "crispr" in tokens
    assert "genetic" in tokens
    assert "engineering" in tokens
    assert "the" not in tokens
    assert "and" not in tokens


def test_tokenize_short_words():
    """Tokenize skips words shorter than 3 chars."""
    tokens = cluster._tokenize("A is of ML to AI")
    # All words are < 3 chars or stop words
    assert len(tokens) == 0


def test_mesh_affinity():
    """MeSH affinity matches cluster name words in MeSH terms."""
    mesh = ["Gene Editing", "CRISPR-Cas Systems", "Plant Breeding"]
    # "Genetic Engineering" -> tokenize -> {"genetic", "engineering"}
    # "Gene Editing" contains "gene" but not "genetic" or "engineering"
    score = cluster._mesh_affinity(mesh, "Gene Editing")
    assert score > 0

    score_zero = cluster._mesh_affinity([], "Gene Editing")
    assert score_zero == 0.0


def test_title_affinity():
    """Title affinity matches cluster name words in title."""
    score = cluster._title_affinity(
        "CRISPR-based genetic engineering in crops",
        "Genetic Engineering",
    )
    assert score > 0

    score_zero = cluster._title_affinity(
        "Quantum computing advances",
        "Genetic Engineering",
    )
    assert score_zero == 0.0


def test_compute_affinity_pubmed():
    """compute_affinity uses MeSH for PubMed items."""
    item = _make_pubmed(
        "Some paper title",
        mesh_terms=["Genetic Engineering", "CRISPR-Cas Systems"],
    )
    score = cluster.compute_affinity(item, "Genetic Engineering")
    assert score > 0


def test_compute_affinity_arxiv():
    """compute_affinity uses category mapping for arXiv items."""
    item = _make_arxiv("Some ML paper", category="cs.LG")
    score = cluster.compute_affinity(item, "Machine Learning")
    assert score > 0


def test_biorxiv_category_fallback():
    """bioRxiv items with categories create fallback clusters."""
    items = [
        _make_biorxiv("Study one", category="Neuroscience", score=80),
        _make_biorxiv("Study two", category="Neuroscience", score=75),
    ]
    result = cluster.cluster_by_theme(items)

    names = [c.name for c in result]
    assert "Neuroscience" in names
