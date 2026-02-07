"""bioRxiv + medRxiv API client for research30 skill.

API: GET https://api.biorxiv.org/details/{server}/{from_date}/{to_date}/{cursor}/json
No keyword search — fetches by date range and filters locally.
100 results/page. After the first sequential request reveals the total,
remaining pages are fetched in parallel via ThreadPoolExecutor.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from . import http, normalize as norm_mod

log = logging.getLogger(__name__)

# Depth config: how many relevant matches to collect
DEPTH_LIMITS = {
    'quick': 20,
    'default': 50,
    'deep': 200,
}

# Max pages to fetch before giving up (safety valve)
MAX_PAGES = 30

# Number of concurrent workers for parallel page fetches
PARALLEL_WORKERS = 5


def _fetch_page(server: str, from_date: str, to_date: str, cursor: int) -> Dict[str, Any]:
    """Fetch a single page from the preprint API. Used by the thread pool."""
    url = f"https://api.biorxiv.org/details/{server}/{from_date}/{to_date}/{cursor}/json"
    return http.get(url, timeout=30)


def _filter_page(topic: str, server: str, collection: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter a page of results for keyword relevance."""
    matches = []
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
            matches.append(item)
    return matches


def search_preprint_server(
    server: str,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_data: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search a preprint server (biorxiv or medrxiv) for a topic.

    Strategy: fetch first page to learn total count, then fan out
    remaining pages in parallel. Filter by keyword match on
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
    error = None

    try:
        # --- First page: sequential, to learn total count ---
        try:
            first_data = _fetch_page(server, from_date, to_date, 0)
        except http.HTTPError as e:
            return [], str(e)

        collection = first_data.get('collection', [])
        if not collection:
            return [], None

        results.extend(_filter_page(topic, server, collection))
        if len(results) >= max_relevant:
            return results[:max_relevant], None

        # Determine remaining cursors from the first page metadata
        messages = first_data.get('messages', [])
        if not messages:
            return results[:max_relevant], None

        msg = messages[0]
        total = int(msg.get('total', 0))
        count = int(msg.get('count', 0))
        if count >= total:
            return results[:max_relevant], None

        # Build list of cursors for remaining pages, capped at MAX_PAGES
        remaining_cursors = []
        c = count
        while c < total and len(remaining_cursors) < MAX_PAGES - 1:
            remaining_cursors.append(c)
            c += 100  # API page size

        if not remaining_cursors:
            return results[:max_relevant], None

        log.debug(
            "%s: %d total papers, fetching %d remaining pages in parallel",
            server, total, len(remaining_cursors),
        )

        # --- Remaining pages: parallel via ThreadPoolExecutor ---
        with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as pool:
            future_to_cursor = {
                pool.submit(_fetch_page, server, from_date, to_date, cur): cur
                for cur in remaining_cursors
            }

            for future in as_completed(future_to_cursor):
                cur = future_to_cursor[future]
                try:
                    data = future.result()
                except http.HTTPError as e:
                    log.debug("%s: page at cursor %d failed: %s", server, cur, e)
                    continue
                except Exception as e:
                    log.debug("%s: page at cursor %d error: %s", server, cur, e)
                    continue

                page_collection = data.get('collection', [])
                if page_collection:
                    results.extend(_filter_page(topic, server, page_collection))

                # Early stop: cancel remaining futures if we have enough
                if len(results) >= max_relevant:
                    for f in future_to_cursor:
                        f.cancel()
                    break

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
