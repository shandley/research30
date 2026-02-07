"""Academic-signal scoring for research30 skill."""

import math
from typing import List, Optional, Union

from . import dates, schema

# Papers: 0.50 relevance + 0.25 recency + 0.25 academic
PAPER_WEIGHT_RELEVANCE = 0.50
PAPER_WEIGHT_RECENCY = 0.25
PAPER_WEIGHT_ACADEMIC = 0.25

# HuggingFace models/datasets: 0.45 relevance + 0.25 recency + 0.30 academic
HF_WEIGHT_RELEVANCE = 0.45
HF_WEIGHT_RECENCY = 0.25
HF_WEIGHT_ACADEMIC = 0.30


def log1p_safe(x: Optional[int]) -> float:
    """Safe log1p that handles None and negative values."""
    if x is None or x < 0:
        return 0.0
    return math.log1p(x)


def compute_biorxiv_academic(engagement: Optional[schema.AcademicEngagement]) -> int:
    """Compute academic signal score for bioRxiv/medRxiv item (0-100)."""
    if engagement is None:
        return 20  # base

    score = 20  # base
    if engagement.published_doi:
        score += 50  # peer reviewed
    if engagement.author_count and engagement.author_count >= 5:
        score += 10  # high author count
    return min(100, score)


def compute_arxiv_academic(
    engagement: Optional[schema.AcademicEngagement],
    primary_category: str = "",
) -> int:
    """Compute academic signal score for arXiv item (0-100)."""
    popular_categories = {'cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE', 'stat.ML',
                          'q-bio', 'physics', 'math'}
    score = 30  # base

    if any(primary_category.startswith(cat) for cat in popular_categories):
        score += 10

    if engagement and engagement.author_count and engagement.author_count >= 5:
        score += 10

    return min(100, score)


def compute_pubmed_academic(engagement: Optional[schema.AcademicEngagement]) -> int:
    """Compute academic signal score for PubMed item (0-100)."""
    if engagement is None:
        return 40  # base

    score = 40  # base
    if engagement.published_journal:
        score += 20
    if engagement.citation_count and engagement.citation_count > 0:
        score += int(log1p_safe(engagement.citation_count) * 15)
    return min(100, score)


def compute_huggingface_academic(engagement: Optional[schema.AcademicEngagement]) -> int:
    """Compute academic signal score for HuggingFace item (0-100)."""
    if engagement is None:
        return 10  # base

    score = 10  # base
    score += int(log1p_safe(engagement.downloads) * 8)
    score += int(log1p_safe(engagement.likes) * 12)
    return min(100, score)


def compute_openalex_academic(engagement: Optional[schema.AcademicEngagement], work_type: str = "") -> int:
    """Compute academic signal score for OpenAlex item (0-100).

    OpenAlex provides rich metadata: citation counts, journal info, work type.
    """
    if engagement is None:
        return 30  # base

    score = 30  # base
    if engagement.published_journal:
        score += 20  # published in a journal
    if engagement.citation_count and engagement.citation_count > 0:
        score += int(log1p_safe(engagement.citation_count) * 12)
    if engagement.author_count and engagement.author_count >= 5:
        score += 10
    return min(100, score)


def compute_semanticscholar_academic(engagement: Optional[schema.AcademicEngagement]) -> int:
    """Compute academic signal score for Semantic Scholar item (0-100).

    S2 provides citation counts and venue info.
    """
    if engagement is None:
        return 30  # base

    score = 30  # base
    if engagement.published_journal:
        score += 20  # published in a venue
    if engagement.citation_count and engagement.citation_count > 0:
        score += int(log1p_safe(engagement.citation_count) * 12)
    if engagement.author_count and engagement.author_count >= 5:
        score += 10
    return min(100, score)


def score_biorxiv_items(items: List[schema.BiorxivItem]) -> List[schema.BiorxivItem]:
    """Compute scores for bioRxiv/medRxiv items."""
    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)
        acad_score = compute_biorxiv_academic(item.engagement)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=acad_score,
        )

        overall = (
            PAPER_WEIGHT_RELEVANCE * rel_score +
            PAPER_WEIGHT_RECENCY * rec_score +
            PAPER_WEIGHT_ACADEMIC * acad_score
        )

        if item.date_confidence == "low":
            overall -= 10

        item.score = max(0, min(100, int(overall)))

    return items


def score_arxiv_items(items: List[schema.ArxivItem]) -> List[schema.ArxivItem]:
    """Compute scores for arXiv items."""
    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)
        acad_score = compute_arxiv_academic(item.engagement, item.primary_category)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=acad_score,
        )

        overall = (
            PAPER_WEIGHT_RELEVANCE * rel_score +
            PAPER_WEIGHT_RECENCY * rec_score +
            PAPER_WEIGHT_ACADEMIC * acad_score
        )

        if item.date_confidence == "low":
            overall -= 10

        item.score = max(0, min(100, int(overall)))

    return items


def score_pubmed_items(items: List[schema.PubmedItem]) -> List[schema.PubmedItem]:
    """Compute scores for PubMed items."""
    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)
        acad_score = compute_pubmed_academic(item.engagement)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=acad_score,
        )

        overall = (
            PAPER_WEIGHT_RELEVANCE * rel_score +
            PAPER_WEIGHT_RECENCY * rec_score +
            PAPER_WEIGHT_ACADEMIC * acad_score
        )

        if item.date_confidence == "low":
            overall -= 10

        item.score = max(0, min(100, int(overall)))

    return items


def score_huggingface_items(items: List[schema.HuggingFaceItem]) -> List[schema.HuggingFaceItem]:
    """Compute scores for HuggingFace items."""
    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)
        acad_score = compute_huggingface_academic(item.engagement)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=acad_score,
        )

        overall = (
            HF_WEIGHT_RELEVANCE * rel_score +
            HF_WEIGHT_RECENCY * rec_score +
            HF_WEIGHT_ACADEMIC * acad_score
        )

        if item.date_confidence == "low":
            overall -= 10

        item.score = max(0, min(100, int(overall)))

    return items


def score_openalex_items(items: List[schema.OpenAlexItem]) -> List[schema.OpenAlexItem]:
    """Compute scores for OpenAlex items."""
    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)
        acad_score = compute_openalex_academic(item.engagement, item.work_type)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=acad_score,
        )

        overall = (
            PAPER_WEIGHT_RELEVANCE * rel_score +
            PAPER_WEIGHT_RECENCY * rec_score +
            PAPER_WEIGHT_ACADEMIC * acad_score
        )

        if item.date_confidence == "low":
            overall -= 10

        item.score = max(0, min(100, int(overall)))

    return items


def score_semanticscholar_items(items: List[schema.SemanticScholarItem]) -> List[schema.SemanticScholarItem]:
    """Compute scores for Semantic Scholar items."""
    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)
        acad_score = compute_semanticscholar_academic(item.engagement)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=acad_score,
        )

        overall = (
            PAPER_WEIGHT_RELEVANCE * rel_score +
            PAPER_WEIGHT_RECENCY * rec_score +
            PAPER_WEIGHT_ACADEMIC * acad_score
        )

        if item.date_confidence == "low":
            overall -= 10

        item.score = max(0, min(100, int(overall)))

    return items


def sort_items(items: List) -> List:
    """Sort items by score descending, then date descending."""
    def sort_key(item):
        score = -item.score
        date = item.date or "0000-00-00"
        date_key = -int(date.replace("-", ""))
        title = getattr(item, "title", "")
        return (score, date_key, title)

    return sorted(items, key=sort_key)
