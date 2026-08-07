"""Normalization of raw API data to canonical schema + keyword relevance."""

import re
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Union

from . import dates, schema

T = TypeVar("T", schema.BiorxivItem, schema.ArxivItem, schema.PubmedItem, schema.HuggingFaceItem, schema.OpenAlexItem, schema.SemanticScholarItem)


def _present(text_lower: str, needle: str, word_boundary: bool) -> bool:
    """Test whether needle appears in text.

    Substring match by default (the topic path, unchanged). With
    word_boundary=True the needle must sit on word boundaries, so the alias
    "MI" no longer matches inside "administration". Used for aliases, where
    substring false positives would compound across every synonym.
    """
    if not needle:
        return False
    if word_boundary:
        return re.search(r'\b' + re.escape(needle) + r'\b', text_lower) is not None
    return needle in text_lower


def _count_bigram_matches(topic_words: list, text: str, word_boundary: bool = False) -> int:
    """Count how many consecutive topic word pairs appear together in text.

    For topic "labor market AI impacts", bigrams are:
    "labor market", "market ai", "ai impacts".
    Each bigram found in text counts as a match.
    """
    if len(topic_words) < 2:
        return 0
    text_lower = text.lower()
    count = 0
    for i in range(len(topic_words) - 1):
        bigram = f"{topic_words[i]} {topic_words[i+1]}"
        if _present(text_lower, bigram, word_boundary):
            count += 1
    return count


def _score_single_phrase(
    phrase: str, title: str, abstract: str, word_boundary: bool = False,
) -> Tuple[float, str]:
    """Score one phrase against title+abstract.

    Tokenizes the phrase into words, matches against title (2x weight) +
    abstract (1x). Boosts for exact phrase match, bigram matches, and
    all-words-present. word_boundary controls substring vs whole-word matching
    (see _present).

    Returns:
        Tuple of (score 0.0-1.0, explanation string)
    """
    if not phrase:
        return 0.0, "no topic"

    phrase_lower = phrase.lower()
    title_lower = title.lower() if title else ''
    abstract_lower = abstract.lower() if abstract else ''

    # Tokenize phrase into words
    phrase_words = re.findall(r'\w+', phrase_lower)
    if not phrase_words:
        return 0.0, "no topic words"

    score = 0.0
    reasons = []

    # Exact phrase match (strongest signal)
    if _present(title_lower, phrase_lower, word_boundary):
        score += 0.4
        reasons.append("exact phrase in title")
    elif _present(abstract_lower, phrase_lower, word_boundary):
        score += 0.2
        reasons.append("exact phrase in abstract")

    # Word-level matching
    title_word_matches = sum(1 for w in phrase_words if _present(title_lower, w, word_boundary))
    abstract_word_matches = sum(1 for w in phrase_words if _present(abstract_lower, w, word_boundary))

    # Title matches (2x weight)
    title_ratio = title_word_matches / len(phrase_words) if phrase_words else 0
    abstract_ratio = abstract_word_matches / len(phrase_words) if phrase_words else 0

    word_score = (title_ratio * 0.3 * 2) + (abstract_ratio * 0.3)
    score += word_score

    if title_word_matches > 0:
        reasons.append(f"{title_word_matches}/{len(phrase_words)} words in title")
    if abstract_word_matches > 0:
        reasons.append(f"{abstract_word_matches}/{len(phrase_words)} words in abstract")

    # Bigram matching — consecutive phrase words appearing together
    # This rewards "labor market" over "labor" + unrelated "market"
    if len(phrase_words) >= 2:
        max_bigrams = len(phrase_words) - 1
        title_bigrams = _count_bigram_matches(phrase_words, title_lower, word_boundary)
        abstract_bigrams = _count_bigram_matches(phrase_words, abstract_lower, word_boundary)
        bigram_ratio = max(
            title_bigrams / max_bigrams,
            abstract_bigrams / max_bigrams * 0.5,
        )
        bigram_bonus = bigram_ratio * 0.15
        score += bigram_bonus
        total_bigrams = max(title_bigrams, abstract_bigrams)
        if total_bigrams > 0:
            reasons.append(f"{total_bigrams}/{max_bigrams} bigrams matched")

    # All-words-present bonus
    all_in_title = title_word_matches == len(phrase_words)
    all_in_abstract = abstract_word_matches == len(phrase_words)
    if all_in_title:
        score += 0.1
        reasons.append("all words in title")
    elif all_in_abstract:
        score += 0.05
        reasons.append("all words in abstract")

    score = min(1.0, max(0.0, score))
    why = '; '.join(reasons) if reasons else "low keyword match"

    return round(score, 3), why


def compute_keyword_relevance(
    topic: str, title: str, abstract: str, aliases: Optional[List[str]] = None,
) -> Tuple[float, str]:
    """Compute keyword relevance of title+abstract to the topic and its aliases.

    The score is the max over the topic and each alias, not the sum: a paper
    matching the topic plus three synonyms scores the same as one matching a
    single synonym, since the aliases are meant to be restatements of the same
    concept, not independent evidence. The topic keeps substring matching
    (unchanged); aliases use whole-word matching to contain false positives.

    Returns:
        Tuple of (score 0.0-1.0, explanation string). When an alias wins, the
        explanation names it so the match stays transparent to the reader.
    """
    score, why = _score_single_phrase(topic, title, abstract, word_boundary=False)

    winning_alias = None
    for alias in (aliases or []):
        a = alias.strip()
        if not a:
            continue
        alias_score, alias_why = _score_single_phrase(a, title, abstract, word_boundary=True)
        if alias_score > score:
            score, why, winning_alias = alias_score, alias_why, a

    if winning_alias:
        why = f"via alias '{winning_alias}': {why}"

    return score, why


def filter_by_date_range(
    items: List[T],
    from_date: str,
    to_date: str,
    require_date: bool = False,
) -> List[T]:
    """Hard filter: Remove items outside the date range."""
    result = []
    for item in items:
        if item.date is None:
            if not require_date:
                result.append(item)
            continue

        if item.date < from_date:
            continue
        if item.date > to_date:
            continue

        result.append(item)

    return result


def normalize_biorxiv_items(
    items: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
    server: str = "biorxiv",
) -> List[schema.BiorxivItem]:
    """Normalize raw bioRxiv/medRxiv items to schema."""
    normalized = []

    for item in items:
        doi = item.get('doi', '')
        date_str = item.get('date', '')
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)

        # Build engagement from published info
        engagement = schema.AcademicEngagement(
            published_doi=item.get('published_doi') or item.get('published') or None,
            published_journal=item.get('published_journal') or None,
            author_count=len(item.get('authors', '').split(';')) if item.get('authors') else None,
        )

        normalized.append(schema.BiorxivItem(
            id=f"{server}:{doi}",
            preprint_doi=doi,
            title=item.get('title', ''),
            authors=item.get('authors', ''),
            abstract=item.get('abstract', ''),
            category=item.get('category', ''),
            source=item.get('source', server),
            url=f"https://doi.org/{doi}" if doi else '',
            date=date_str if date_str else None,
            date_confidence=date_confidence,
            engagement=engagement,
            relevance=item.get('relevance', 0.0),
            why_relevant=item.get('why_relevant', ''),
        ))

    return normalized


def normalize_arxiv_items(
    items: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
) -> List[schema.ArxivItem]:
    """Normalize raw arXiv items to schema."""
    normalized = []

    for item in items:
        arxiv_id = item.get('arxiv_id', '')

        # Parse date from published field
        pub = item.get('published', '')
        date_str = pub[:10] if len(pub) >= 10 else None
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)

        engagement = schema.AcademicEngagement(
            author_count=item.get('author_count'),
        )

        normalized.append(schema.ArxivItem(
            id=f"arxiv:{arxiv_id}",
            arxiv_id=arxiv_id,
            title=item.get('title', ''),
            authors=item.get('authors', ''),
            abstract=item.get('abstract', ''),
            primary_category=item.get('primary_category', ''),
            categories=item.get('categories', []),
            url=item.get('link', f"https://arxiv.org/abs/{arxiv_id}"),
            date=date_str,
            date_confidence=date_confidence,
            engagement=engagement,
            relevance=item.get('relevance', 0.0),
            why_relevant=item.get('why_relevant', ''),
        ))

    return normalized


def normalize_pubmed_items(
    items: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
) -> List[schema.PubmedItem]:
    """Normalize raw PubMed items to schema."""
    normalized = []

    for item in items:
        pmid = item.get('pmid', '')
        date_str = item.get('pub_date')
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)

        engagement = schema.AcademicEngagement(
            published_doi=item.get('doi') or None,
            published_journal=item.get('journal') or None,
            author_count=item.get('author_count'),
        )

        normalized.append(schema.PubmedItem(
            id=f"pubmed:{pmid}",
            pmid=pmid,
            title=item.get('title', ''),
            authors=item.get('authors', ''),
            abstract=item.get('abstract', ''),
            journal=item.get('journal', ''),
            doi=item.get('doi'),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else '',
            mesh_terms=item.get('mesh_terms', []),
            date=date_str,
            date_confidence=date_confidence,
            engagement=engagement,
            relevance=item.get('relevance', 0.0),
            why_relevant=item.get('why_relevant', ''),
        ))

    return normalized


def normalize_huggingface_items(
    items: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
) -> List[schema.HuggingFaceItem]:
    """Normalize raw HuggingFace items to schema."""
    normalized = []

    for item in items:
        hf_id = item.get('hf_id', '')
        date_str = item.get('date')
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)

        engagement = schema.AcademicEngagement(
            downloads=item.get('downloads'),
            likes=item.get('likes'),
        )

        normalized.append(schema.HuggingFaceItem(
            id=f"hf:{hf_id}",
            hf_id=hf_id,
            title=item.get('title', ''),
            author=item.get('author', ''),
            item_type=item.get('item_type', 'model'),
            tags=item.get('tags', []),
            url=item.get('url', ''),
            date=date_str,
            date_confidence=date_confidence,
            engagement=engagement,
            relevance=item.get('relevance', 0.0),
            why_relevant=item.get('why_relevant', ''),
        ))

    return normalized


def normalize_openalex_items(
    items: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
) -> List[schema.OpenAlexItem]:
    """Normalize raw OpenAlex items to schema."""
    normalized = []

    for item in items:
        openalex_id = item.get('openalex_id', '')
        date_str = item.get('publication_date') or item.get('date')
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)

        doi_raw = item.get('doi')
        author_count = None
        authors_str = item.get('authors', '')
        if authors_str:
            author_count = len(authors_str.split(', '))

        engagement = schema.AcademicEngagement(
            published_doi=doi_raw,
            published_journal=item.get('source_name') or None,
            citation_count=item.get('cited_by_count'),
            author_count=author_count,
        )

        normalized.append(schema.OpenAlexItem(
            id=f"openalex:{openalex_id}",
            openalex_id=openalex_id,
            title=item.get('title', ''),
            authors=authors_str,
            abstract=item.get('abstract', ''),
            doi=doi_raw,
            source_name=item.get('source_name', ''),
            source_type=item.get('source_type', ''),
            work_type=item.get('work_type', ''),
            url=item.get('url', ''),
            primary_topic_name=item.get('primary_topic_name', ''),
            primary_topic_score=item.get('primary_topic_score', 0.0),
            date=date_str,
            date_confidence=date_confidence,
            engagement=engagement,
            relevance=item.get('relevance', 0.0),
            why_relevant=item.get('why_relevant', ''),
        ))

    return normalized


def normalize_semanticscholar_items(
    items: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
) -> List[schema.SemanticScholarItem]:
    """Normalize raw Semantic Scholar items to schema."""
    normalized = []

    for item in items:
        paper_id = item.get('paper_id', '')
        date_str = item.get('publication_date') or item.get('date')
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)

        doi = item.get('doi')
        authors_str = item.get('authors', '')
        author_count = len(authors_str.split(', ')) if authors_str else None

        engagement = schema.AcademicEngagement(
            published_doi=doi,
            published_journal=item.get('venue') or None,
            citation_count=item.get('cited_by_count'),
            author_count=author_count,
        )

        normalized.append(schema.SemanticScholarItem(
            id=f"s2:{paper_id}",
            paper_id=paper_id,
            title=item.get('title', ''),
            authors=authors_str,
            abstract=item.get('abstract', ''),
            doi=doi,
            venue=item.get('venue', ''),
            publication_types=item.get('publication_types', []),
            url=item.get('url', ''),
            date=date_str,
            date_confidence=date_confidence,
            engagement=engagement,
            relevance=item.get('relevance', 0.0),
            why_relevant=item.get('why_relevant', ''),
        ))

    return normalized
