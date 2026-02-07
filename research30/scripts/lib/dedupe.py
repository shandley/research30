"""Deduplication for research30 skill.

Two-pass strategy:
1. DOI-based exact dedup across all sources (O(n), fast)
2. Jaccard title similarity with 3-grams, threshold 0.7

Cross-source priority: PubMed > OpenAlex > bioRxiv > medRxiv > arXiv > HuggingFace
"""

import re
from typing import Any, Dict, List, Set, Tuple, Union

from . import schema

# Source priority for dedup (lower = higher priority, keep this one)
SOURCE_PRIORITY = {
    'pubmed': 0,
    'openalex': 1,
    'biorxiv': 2,
    'medrxiv': 3,
    'arxiv': 4,
    'huggingface': 5,
}


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_ngrams(text: str, n: int = 3) -> Set[str]:
    """Get character n-grams from text."""
    text = normalize_text(text)
    if len(text) < n:
        return {text}
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _get_source(item) -> str:
    """Get source identifier for an item."""
    if isinstance(item, schema.BiorxivItem):
        return item.source  # "biorxiv" or "medrxiv"
    elif isinstance(item, schema.ArxivItem):
        return 'arxiv'
    elif isinstance(item, schema.PubmedItem):
        return 'pubmed'
    elif isinstance(item, schema.HuggingFaceItem):
        return 'huggingface'
    elif isinstance(item, schema.OpenAlexItem):
        return 'openalex'
    return 'unknown'


def _get_dois(item) -> List[str]:
    """Get all DOIs associated with an item."""
    dois = []
    if isinstance(item, schema.BiorxivItem):
        if item.preprint_doi:
            dois.append(item.preprint_doi)
    if isinstance(item, schema.PubmedItem):
        if item.doi:
            dois.append(item.doi)
    if isinstance(item, schema.OpenAlexItem):
        if item.doi:
            dois.append(item.doi)
    # Check engagement for published_doi (preprints may have published DOI)
    eng = getattr(item, 'engagement', None)
    if eng and eng.published_doi:
        dois.append(eng.published_doi)
    return [d.lower().strip() for d in dois if d]


def _get_title(item) -> str:
    """Get title text from an item."""
    return getattr(item, 'title', '')


def _source_priority(item) -> int:
    """Get source priority (lower = keep)."""
    return SOURCE_PRIORITY.get(_get_source(item), 99)


def dedupe_cross_source(
    all_items: List,
    threshold: float = 0.7,
) -> List:
    """Remove duplicates across all sources.

    Two-pass strategy:
    1. DOI-based exact match
    2. Jaccard title similarity

    When duplicates found, keeps the item from higher-priority source.
    If same source, keeps higher-scored item.

    Args:
        all_items: Combined list of items from all sources
        threshold: Jaccard similarity threshold

    Returns:
        Deduplicated list
    """
    if len(all_items) <= 1:
        return all_items

    to_remove = set()

    # Pass 1: DOI-based exact dedup
    # Map each DOI to all item indices that reference it
    doi_map: Dict[str, List[int]] = {}
    for idx, item in enumerate(all_items):
        for doi in _get_dois(item):
            doi_map.setdefault(doi, []).append(idx)

    for doi, indices in doi_map.items():
        if len(indices) <= 1:
            continue
        # Keep the highest-priority source; if tied, highest score
        best_idx = min(indices, key=lambda i: (_source_priority(all_items[i]), -all_items[i].score))
        for idx in indices:
            if idx != best_idx:
                to_remove.add(idx)

    # Pass 2: Jaccard title similarity
    remaining = [(idx, item) for idx, item in enumerate(all_items) if idx not in to_remove]

    ngrams = [(idx, get_ngrams(_get_title(item))) for idx, item in remaining]

    for i in range(len(ngrams)):
        if ngrams[i][0] in to_remove:
            continue
        for j in range(i + 1, len(ngrams)):
            if ngrams[j][0] in to_remove:
                continue

            similarity = jaccard_similarity(ngrams[i][1], ngrams[j][1])
            if similarity >= threshold:
                idx_i, idx_j = ngrams[i][0], ngrams[j][0]
                item_i, item_j = all_items[idx_i], all_items[idx_j]

                # Keep higher-priority source; if tied, higher score
                pri_i = (_source_priority(item_i), -item_i.score)
                pri_j = (_source_priority(item_j), -item_j.score)

                if pri_i <= pri_j:
                    to_remove.add(idx_j)
                else:
                    to_remove.add(idx_i)

    return [item for idx, item in enumerate(all_items) if idx not in to_remove]


def dedupe_within_source(
    items: List,
    threshold: float = 0.7,
) -> List:
    """Remove near-duplicates within a single source list.

    Keeps highest-scored item when duplicates found.
    """
    if len(items) <= 1:
        return items

    ngrams = [get_ngrams(_get_title(item)) for item in items]
    to_remove = set()

    for i in range(len(items)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(items)):
            if j in to_remove:
                continue
            similarity = jaccard_similarity(ngrams[i], ngrams[j])
            if similarity >= threshold:
                if items[i].score >= items[j].score:
                    to_remove.add(j)
                else:
                    to_remove.add(i)

    return [item for idx, item in enumerate(items) if idx not in to_remove]
