"""bioRxiv + medRxiv API client for research30 skill.

API: GET https://api.biorxiv.org/details/{server}/{from_date}/{to_date}/{cursor}/json
No keyword search — fetches by date range and filters locally.
100 results/page, 1 req/sec rate limit.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from . import http, normalize as norm_mod


# Depth config: how many relevant matches to collect
DEPTH_LIMITS = {
    'quick': 20,
    'default': 50,
    'deep': 200,
}

# Max pages to fetch before giving up (safety valve)
MAX_PAGES = 30

# Rate limit: 1 request per second
RATE_LIMIT_DELAY = 1.0


def search_preprint_server(
    server: str,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_data: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search a preprint server (biorxiv or medrxiv) for a topic.

    Strategy: paginate through results, filter by keyword match on
    title+abstract, stop early once enough relevant matches found.

    Args:
        server: "biorxiv" or "medrxiv"
        topic: Search topic
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: "quick", "default", or "deep"
        mock_data: Optional mock data for testing

    Returns:
        Tuple of (list of matching paper dicts, error_message or None)
    """
    max_relevant = DEPTH_LIMITS.get(depth, DEPTH_LIMITS['default'])

    if mock_data is not None:
        # Filter mock data by keyword
        results = []
        for item in mock_data:
            rel, why = norm_mod.compute_keyword_relevance(
                topic,
                item.get('title', ''),
                item.get('abstract', ''),
            )
            if rel > 0.1:
                item['relevance'] = rel
                item['why_relevant'] = why
                item['source'] = server
                results.append(item)
        return results[:max_relevant], None

    results = []
    cursor = 0
    error = None

    try:
        for _page in range(MAX_PAGES):
            url = f"https://api.biorxiv.org/details/{server}/{from_date}/{to_date}/{cursor}/json"

            try:
                data = http.get(url, timeout=30)
            except http.HTTPError as e:
                error = str(e)
                break

            collection = data.get('collection', [])
            if not collection:
                break

            # Filter by keyword relevance
            for item in collection:
                rel, why = norm_mod.compute_keyword_relevance(
                    topic,
                    item.get('title', ''),
                    item.get('abstract', ''),
                )
                if rel > 0.1:
                    item['relevance'] = rel
                    item['why_relevant'] = why
                    item['source'] = server
                    results.append(item)

            # Check if we have enough
            if len(results) >= max_relevant:
                break

            # Check if there are more pages
            messages = data.get('messages', [])
            if messages:
                msg = messages[0]
                total = int(msg.get('total', 0))
                count = int(msg.get('count', 0))
                if cursor + count >= total:
                    break
                cursor += count
            else:
                break

            # Rate limit
            time.sleep(RATE_LIMIT_DELAY)

    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    return results[:max_relevant], error


def search_biorxiv(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_data: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search bioRxiv for a topic."""
    return search_preprint_server("biorxiv", topic, from_date, to_date, depth, mock_data)


def search_medrxiv(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_data: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search medRxiv for a topic."""
    return search_preprint_server("medrxiv", topic, from_date, to_date, depth, mock_data)
