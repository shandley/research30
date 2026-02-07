"""PubMed E-utilities client for research30 skill.

Step 1 ESearch: esearch.fcgi?db=pubmed&term={topic}&reldate=30&datetype=pdat&retmax=100&retmode=json
Step 2 EFetch: efetch.fcgi?db=pubmed&id={pmids}&rettype=abstract&retmode=xml

Optional NCBI_API_KEY for 10/sec vs 3/sec rate limit.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from . import http, xml_parse, normalize as norm_mod

# Known phrases that should be kept as a unit (not split into individual words)
_KNOWN_PHRASES = {
    'machine learning', 'deep learning', 'gene editing', 'gene therapy',
    'sickle cell', 'stem cell', 'clinical trial', 'single cell',
    'genome wide', 'public health', 'mental health',
}


DEPTH_LIMITS = {
    'quick': 30,
    'default': 100,
    'deep': 200,
}

ESEARCH_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Rate limits
RATE_LIMIT_NO_KEY = 0.34  # 3/sec → ~334ms between requests
RATE_LIMIT_WITH_KEY = 0.1  # 10/sec → 100ms between requests

# Batch size for EFetch
EFETCH_BATCH_SIZE = 200


def search_pubmed(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    api_key: Optional[str] = None,
    mock_esearch: Optional[dict] = None,
    mock_efetch: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search PubMed for articles matching a topic.

    Args:
        topic: Search query
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: "quick", "default", or "deep"
        api_key: Optional NCBI API key
        mock_esearch: Optional mock ESearch JSON for testing
        mock_efetch: Optional mock EFetch XML for testing

    Returns:
        Tuple of (list of article dicts, error_message or None)
    """
    max_results = DEPTH_LIMITS.get(depth, DEPTH_LIMITS['default'])
    rate_delay = RATE_LIMIT_WITH_KEY if api_key else RATE_LIMIT_NO_KEY
    error = None
    query_translation = ''

    # Step 1: ESearch to get PMIDs
    if mock_esearch is not None:
        pmids, query_translation = xml_parse.parse_pubmed_esearch(mock_esearch)
    else:
        try:
            pmids, query_translation = _esearch(topic, max_results, api_key)
        except http.HTTPError as e:
            return [], str(e)
        except Exception as e:
            return [], f"{type(e).__name__}: {e}"

    if not pmids:
        return [], None

    time.sleep(rate_delay)

    # Step 2: EFetch to get article details
    if mock_efetch is not None:
        articles = xml_parse.parse_pubmed_efetch(mock_efetch)
    else:
        articles = []
        try:
            # Batch PMIDs
            for i in range(0, len(pmids), EFETCH_BATCH_SIZE):
                batch = pmids[i:i + EFETCH_BATCH_SIZE]
                batch_articles = _efetch(batch, api_key)
                articles.extend(batch_articles)

                if i + EFETCH_BATCH_SIZE < len(pmids):
                    time.sleep(rate_delay)
        except http.HTTPError as e:
            error = str(e)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"

    # Compute keyword relevance for scoring
    for article in articles:
        rel, why = norm_mod.compute_keyword_relevance(
            topic,
            article.get('title', ''),
            article.get('abstract', ''),
        )
        article['relevance'] = rel
        article['why_relevant'] = why
        article['query_translation'] = query_translation

    return articles, error


def _build_query(topic: str) -> str:
    """Build a TIAB-tagged PubMed query from a topic string.

    Uses [TIAB] (Title/Abstract) field tags to avoid PubMed's Automatic
    Term Mapping which can misfire (e.g., "gut" matching the journal *Gut*).

    Single-word or known-phrase topics produce: {topic}[TIAB]
    Multi-word topics produce:
        ("{topic}"[TIAB] OR ({word1}[TIAB] AND {word2}[TIAB] AND ...))
    """
    words = topic.split()
    if len(words) <= 1 or topic.lower() in _KNOWN_PHRASES:
        return f'{topic}[TIAB]'

    # Multi-word: combine exact phrase with individual AND terms
    and_part = ' AND '.join(f'{w}[TIAB]' for w in words)
    return f'("{topic}"[TIAB] OR ({and_part}))'


def _esearch(topic: str, max_results: int, api_key: Optional[str] = None) -> Tuple[List[str], str]:
    """Run ESearch to find PMIDs.

    Returns:
        Tuple of (list of PMID strings, querytranslation string).
    """
    query = _build_query(topic)
    encoded_query = quote(query)
    url = (
        f"{ESEARCH_BASE}"
        f"?db=pubmed"
        f"&term={encoded_query}"
        f"&reldate=30"
        f"&datetype=pdat"
        f"&retmax={max_results}"
        f"&retmode=json"
    )
    if api_key:
        url += f"&api_key={api_key}"

    data = http.get(url, timeout=30)
    pmids, query_translation = xml_parse.parse_pubmed_esearch(data)
    http.log(f"PubMed querytranslation: {query_translation}")
    return pmids, query_translation


def _efetch(pmids: List[str], api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Run EFetch to get article details."""
    ids = ','.join(pmids)
    url = (
        f"{EFETCH_BASE}"
        f"?db=pubmed"
        f"&id={ids}"
        f"&rettype=abstract"
        f"&retmode=xml"
    )
    if api_key:
        url += f"&api_key={api_key}"

    xml_text = http.get_text(url, timeout=60)
    return xml_parse.parse_pubmed_efetch(xml_text)
