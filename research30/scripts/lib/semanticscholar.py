"""Semantic Scholar API client for research30 skill.

API: GET https://api.semanticscholar.org/graph/v1/paper/search
Full-text semantic search with citation data. Requires API key for
reliable access. Rate limit: 1 req/sec.
"""

import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from . import http, normalize as norm_mod

log = logging.getLogger(__name__)

API_BASE = "https://api.semanticscholar.org/graph/v1"

# Fields to request from the API
FIELDS = ",".join([
    "title", "abstract", "authors", "citationCount",
    "influentialCitationCount", "journal", "externalIds",
    "openAccessPdf", "publicationDate", "venue", "url",
    "publicationTypes",
])

# Depth config: how many relevant matches to collect
DEPTH_LIMITS = {
    'quick': 30,
    'default': 100,
    'deep': 200,
}

# Max pages (safety valve). At 100/page, 2 pages = 200 results.
MAX_PAGES = 3

# API page size (S2 max is 100)
PAGE_SIZE = 100

# Minimum keyword relevance to keep a result. Higher than other sources
# because S2 does semantic ranking server-side — we only need to filter
# out tangential abstract-only mentions.
RELEVANCE_THRESHOLD = 0.3


def _extract_authors(authors: List[Dict]) -> str:
    """Extract author names from S2 authors list."""
    return ", ".join(a.get('name', '') for a in authors if a.get('name'))


def _extract_doi(external_ids: Optional[Dict]) -> Optional[str]:
    """Extract DOI from externalIds dict."""
    if not external_ids:
        return None
    return external_ids.get('DOI')


def _build_url(paper: Dict) -> str:
    """Build best URL for a paper."""
    # Prefer open access PDF
    oa = paper.get('openAccessPdf')
    if oa and oa.get('url'):
        return oa['url']
    # Prefer DOI
    ext = paper.get('externalIds', {}) or {}
    doi = ext.get('DOI')
    if doi:
        return f"https://doi.org/{doi}"
    # Fall back to S2 URL
    return paper.get('url', '')


def search_semantic_scholar(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    api_key: Optional[str] = None,
    mock_data: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search Semantic Scholar for papers matching topic in date range.

    S2 provides semantic search — understands conceptual similarity,
    not just keyword matching. We still apply our keyword relevance
    filter for consistency with other sources.

    Args:
        topic: Search topic
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: "quick", "default", or "deep"
        api_key: Optional S2 API key for higher rate limits
        mock_data: Optional mock data for testing (list of paper dicts)

    Returns:
        Tuple of (list of matching item dicts, error_message or None)
    """
    max_results = DEPTH_LIMITS.get(depth, DEPTH_LIMITS['default'])

    if mock_data is not None:
        results = []
        for rank, paper in enumerate(mock_data):
            rel, why = norm_mod.compute_keyword_relevance(
                topic,
                paper.get('title', ''),
                paper.get('abstract', ''),
            )
            if rel > RELEVANCE_THRESHOLD:
                # Boost relevance based on API rank — S2 uses semantic
                # embedding search, so top results are conceptually closest.
                position_boost = max(0.0, 0.1 * (1 - rank / max(len(mock_data), 1)))
                boosted_rel = min(1.0, rel + position_boost)
                ext_ids = paper.get('externalIds', {}) or {}
                authors = paper.get('authors', [])
                pub_types = paper.get('publicationTypes') or []
                results.append({
                    'paper_id': paper.get('paperId', ''),
                    'title': paper.get('title', ''),
                    'authors': _extract_authors(authors),
                    'abstract': paper.get('abstract', ''),
                    'doi': _extract_doi(ext_ids),
                    'venue': paper.get('venue', '') or (paper.get('journal') or {}).get('name', ''),
                    'publication_types': pub_types,
                    'cited_by_count': paper.get('citationCount', 0),
                    'influential_citations': paper.get('influentialCitationCount', 0),
                    'publication_date': paper.get('publicationDate'),
                    'url': _build_url(paper),
                    'external_ids': ext_ids,
                    'relevance': boosted_rel,
                    'why_relevant': why,
                    'source': 'semanticscholar',
                })
        return results[:max_results], None

    results = []
    error = None
    headers = {}
    if api_key:
        headers['x-api-key'] = api_key

    try:
        offset = 0
        for _page in range(MAX_PAGES):
            params = urllib.parse.urlencode({
                'query': topic,
                'publicationDateOrYear': f'{from_date}:{to_date}',
                'limit': PAGE_SIZE,
                'offset': offset,
                'fields': FIELDS,
            })
            url = f"{API_BASE}/paper/search?{params}"

            try:
                data = http.get(url, headers=headers, timeout=30)
            except http.HTTPError as e:
                if offset == 0:
                    return [], str(e)
                log.debug("semanticscholar: page at offset %d failed: %s", offset, e)
                break

            papers = data.get('data', [])
            if not papers:
                break

            for idx, paper in enumerate(papers):
                global_rank = offset + idx
                abstract = paper.get('abstract', '') or ''
                rel, why = norm_mod.compute_keyword_relevance(
                    topic,
                    paper.get('title', ''),
                    abstract,
                )
                if rel > RELEVANCE_THRESHOLD:
                    # Boost relevance based on API rank — S2 uses semantic
                    # embedding search, so top results are conceptually closest.
                    position_boost = max(0.0, 0.1 * (1 - global_rank / max_results))
                    boosted_rel = min(1.0, rel + position_boost)
                    ext_ids = paper.get('externalIds', {}) or {}
                    authors = paper.get('authors', [])
                    pub_types = paper.get('publicationTypes') or []
                    venue = paper.get('venue', '') or ''
                    if not venue:
                        journal = paper.get('journal')
                        if journal:
                            venue = journal.get('name', '')

                    results.append({
                        'paper_id': paper.get('paperId', ''),
                        'title': paper.get('title', ''),
                        'authors': _extract_authors(authors),
                        'abstract': abstract,
                        'doi': _extract_doi(ext_ids),
                        'venue': venue,
                        'publication_types': pub_types,
                        'cited_by_count': paper.get('citationCount', 0),
                        'influential_citations': paper.get('influentialCitationCount', 0),
                        'publication_date': paper.get('publicationDate'),
                        'url': _build_url(paper),
                        'external_ids': ext_ids,
                        'relevance': boosted_rel,
                        'why_relevant': why,
                        'source': 'semanticscholar',
                    })

            if len(results) >= max_results:
                break

            total = data.get('total', 0)
            next_offset = data.get('next')
            if next_offset is None or offset + PAGE_SIZE >= total:
                break
            offset = next_offset

    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    return results[:max_results], error
