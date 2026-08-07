"""Scoring for research30 skill.

The score is a blend of how well an item matches the topic (relevance) and how
recent it is (recency), both 0-100:

    score = 0.70 * relevance + 0.30 * recency   (minus 10 for a low-confidence date)

It deliberately does NOT fold in a quality/impact term. For the last-30-days
window, citation counts are essentially zero for every item, so a per-source
"academic" component collapsed into a constant (PubMed always 60, arXiv always
30, ...) and acted as a hidden source prior — ranking a paper above a preprint
just for its database, independent of the paper. Quality and reliability signals
(peer-review status, journal, citations, downloads) are still carried on each
item and shown as badges in the output, for the reader and the synthesis step to
weigh, rather than smuggled into the number.
"""

from typing import List

from . import dates, schema

# score = 0.70 * relevance + 0.30 * recency
WEIGHT_RELEVANCE = 0.70
WEIGHT_RECENCY = 0.30

# Penalty applied when an item's date could not be confidently placed in range.
LOW_DATE_CONFIDENCE_PENALTY = 10


def _apply_score(items: List) -> List:
    """Score each item from its relevance and recency (in place).

    Works for every source type: each item carries .relevance (0.0-1.0),
    .date, and .date_confidence.
    """
    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)

        item.subs = schema.SubScores(relevance=rel_score, recency=rec_score)

        overall = WEIGHT_RELEVANCE * rel_score + WEIGHT_RECENCY * rec_score
        if item.date_confidence == "low":
            overall -= LOW_DATE_CONFIDENCE_PENALTY

        item.score = max(0, min(100, int(overall)))

    return items


# Per-source entry points. Scoring is uniform across sources; these names are
# kept so callers can stay source-explicit.
def score_biorxiv_items(items: List[schema.BiorxivItem]) -> List[schema.BiorxivItem]:
    return _apply_score(items)


def score_arxiv_items(items: List[schema.ArxivItem]) -> List[schema.ArxivItem]:
    return _apply_score(items)


def score_pubmed_items(items: List[schema.PubmedItem]) -> List[schema.PubmedItem]:
    return _apply_score(items)


def score_huggingface_items(items: List[schema.HuggingFaceItem]) -> List[schema.HuggingFaceItem]:
    return _apply_score(items)


def score_openalex_items(items: List[schema.OpenAlexItem]) -> List[schema.OpenAlexItem]:
    return _apply_score(items)


def score_semanticscholar_items(items: List[schema.SemanticScholarItem]) -> List[schema.SemanticScholarItem]:
    return _apply_score(items)


def sort_items(items: List) -> List:
    """Sort items by score descending, then date descending."""
    def sort_key(item):
        score = -item.score
        date = (item.date or "0000-00-00")[:10]  # truncate to YYYY-MM-DD
        date_key = -int(date.replace("-", "") or "0")
        title = getattr(item, "title", "")
        return (score, date_key, title)

    return sorted(items, key=sort_key)
