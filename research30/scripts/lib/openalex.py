"""OpenAlex API client for research30 skill.

API: GET https://api.openalex.org/works?search={topic}&filter=from_publication_date:{from},to_publication_date:{to}
Full-text search with relevance ranking — no need to paginate everything.
"""

import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from . import http, normalize as norm_mod

log = logging.getLogger(__name__)

# Depth config: how many relevant matches to collect
DEPTH_LIMITS = {
    'quick': 30,
    'default': 100,
    'deep': 200,
}

# Max pages to fetch (safety valve)
MAX_PAGES = 5

# API page size
PAGE_SIZE = 100

# Contact email for polite pool (gets higher rate limits)
MAILTO = "research30-skill@users.noreply.github.com"


def _reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(word for _, word in word_positions)


def _extract_authors(authorships: List[Dict]) -> str:
    """Extract author names from OpenAlex authorships list."""
    names = []
    for a in authorships:
        author = a.get('author', {})
        name = author.get('display_name', '')
        if name:
            names.append(name)
    return ", ".join(names)


def _extract_source(primary_location: Optional[Dict]) -> Tuple[str, str]:
    """Extract source name and type from primary_location.

    Returns:
        Tuple of (source_name, source_type)
    """
    if not primary_location:
        return "", ""
    source = primary_location.get('source') or {}
    return source.get('display_name', ''), source.get('type', '')


def _extract_doi(doi_url: Optional[str]) -> Optional[str]:
    """Extract clean DOI from OpenAlex doi field (which is a full URL)."""
    if not doi_url:
        return None
    # OpenAlex returns "https://doi.org/10.1234/xxx"
    if doi_url.startswith("https://doi.org/"):
        return doi_url[len("https://doi.org/"):]
    if doi_url.startswith("http://doi.org/"):
        return doi_url[len("http://doi.org/"):]
    return doi_url


def _build_url(work: Dict) -> str:
    """Build best URL for a work."""
    doi = work.get('doi')
    if doi:
        return doi if doi.startswith('http') else f"https://doi.org/{doi}"
    oa = work.get('open_access', {})
    if oa.get('oa_url'):
        return oa['oa_url']
    return work.get('id', '')


def _fetch_page(topic: str, from_date: str, to_date: str, page: int) -> Dict[str, Any]:
    """Fetch a single page of OpenAlex results."""
    params = urllib.parse.urlencode({
        'search': topic,
        'filter': f'from_publication_date:{from_date},to_publication_date:{to_date}',
        'sort': 'relevance_score:desc',
        'per_page': PAGE_SIZE,
        'page': page,
        'mailto': MAILTO,
    })
    url = f"https://api.openalex.org/works?{params}"
    return http.get(url, timeout=30)


def search_openalex(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_data: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search OpenAlex for works matching topic in date range.

    OpenAlex provides full-text search with relevance ranking,
    so results come back pre-sorted by relevance. We still apply
    our keyword relevance filter for consistency with other sources.

    Args:
        topic: Search topic
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: "quick", "default", or "deep"
        mock_data: Optional mock data for testing (list of work dicts)

    Returns:
        Tuple of (list of matching item dicts, error_message or None)
    """
    max_results = DEPTH_LIMITS.get(depth, DEPTH_LIMITS['default'])

    if mock_data is not None:
        results = []
        for work in mock_data:
            abstract = work.get('abstract') or _reconstruct_abstract(
                work.get('abstract_inverted_index')
            )
            rel, why = norm_mod.compute_keyword_relevance(
                topic,
                work.get('title', ''),
                abstract,
            )
            if rel > 0.1:
                source_name, source_type = _extract_source(work.get('primary_location'))
                doi = _extract_doi(work.get('doi'))
                results.append({
                    'openalex_id': work.get('id', '').replace('https://openalex.org/', ''),
                    'title': work.get('title', ''),
                    'authors': _extract_authors(work.get('authorships', [])),
                    'abstract': abstract,
                    'doi': doi,
                    'publication_date': work.get('publication_date'),
                    'source_name': source_name,
                    'source_type': source_type,
                    'work_type': work.get('type', ''),
                    'cited_by_count': work.get('cited_by_count', 0),
                    'url': _build_url(work),
                    'relevance': rel,
                    'why_relevant': why,
                    'source': 'openalex',
                })
        return results[:max_results], None

    results = []
    error = None

    try:
        for page_num in range(1, MAX_PAGES + 1):
            try:
                data = _fetch_page(topic, from_date, to_date, page_num)
            except http.HTTPError as e:
                if page_num == 1:
                    return [], str(e)
                log.debug("openalex: page %d failed: %s", page_num, e)
                break

            works = data.get('results', [])
            if not works:
                break

            for work in works:
                abstract = _reconstruct_abstract(work.get('abstract_inverted_index'))
                rel, why = norm_mod.compute_keyword_relevance(
                    topic,
                    work.get('title', ''),
                    abstract,
                )
                if rel > 0.1:
                    source_name, source_type = _extract_source(work.get('primary_location'))
                    doi = _extract_doi(work.get('doi'))
                    results.append({
                        'openalex_id': work.get('id', '').replace('https://openalex.org/', ''),
                        'title': work.get('title', ''),
                        'authors': _extract_authors(work.get('authorships', [])),
                        'abstract': abstract,
                        'doi': doi,
                        'publication_date': work.get('publication_date'),
                        'source_name': source_name,
                        'source_type': source_type,
                        'work_type': work.get('type', ''),
                        'cited_by_count': work.get('cited_by_count', 0),
                        'url': _build_url(work),
                        'relevance': rel,
                        'why_relevant': why,
                        'source': 'openalex',
                    })

            # Check if we have enough or no more pages
            if len(results) >= max_results:
                break

            total = data.get('meta', {}).get('count', 0)
            if page_num * PAGE_SIZE >= total:
                break

            log.debug(
                "openalex: page %d done, %d results so far (%d total available)",
                page_num, len(results), total,
            )

    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    return results[:max_results], error
