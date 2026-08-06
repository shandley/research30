"""bioRxiv + medRxiv preprint search via Europe PMC.

The bioRxiv details API (api.biorxiv.org) has no keyword search: it only
lists preprints by date, so finding matches means downloading every preprint
in the window (6000+ per month, 30 per page, oldest first) and filtering
locally. That is too slow for a default source and undersamples the newest
work.

Europe PMC indexes both servers and offers a real query API. We search each
server with a PUBLISHER filter, then apply the same title+abstract relevance
filter the rest of the pipeline uses. Results are mapped into the raw dict
shape normalize_biorxiv_items() expects, so scoring, dedup, and rendering are
unchanged.

API: GET https://www.ebi.ac.uk/europepmc/webservices/rest/search
     ?query=<terms> AND PUBLISHER:"bioRxiv" AND (FIRST_PDATE:[from TO to])
     &format=json&resultType=core&pageSize=100&cursorMark=*
"""

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from . import http, normalize as norm_mod

log = logging.getLogger(__name__)

EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# How many relevant matches to collect per server.
DEPTH_LIMITS = {
    'quick': 20,
    'default': 50,
    'deep': 200,
}

# Europe PMC page size (max 100 for the core result type).
PAGE_SIZE = 100

# Safety cap on pages fetched per server, independent of depth.
MAX_PAGES = 5

# Minimum title+abstract relevance for a preprint to be kept.
RELEVANCE_THRESHOLD = 0.1

# server name -> Europe PMC PUBLISHER value
_PUBLISHER = {"biorxiv": "bioRxiv", "medrxiv": "medRxiv"}

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_markup(text: str) -> str:
    """Europe PMC abstracts carry inline markup (<title>Abstract</title><p>..).

    Remove tags and collapse whitespace so the relevance scorer and the
    snippet both see clean text.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", text)).strip()


def _map_result(result: Dict[str, Any], server: str) -> Dict[str, Any]:
    """Map a Europe PMC result into the raw bioRxiv-item dict shape."""
    # authorString is comma-separated; normalize_biorxiv_items counts authors
    # by splitting on ';', so join with ';'.
    author_string = result.get("authorString", "") or ""
    authors = "; ".join(a.strip() for a in author_string.split(",") if a.strip())
    return {
        "doi": result.get("doi", "") or "",
        "title": result.get("title", "") or "",
        "abstract": _strip_markup(result.get("abstractText", "") or ""),
        "authors": authors,
        "category": "",
        "date": result.get("firstPublicationDate", "") or "",
        "source": server,
    }


def _score_and_filter(topic: str, raw_items: List[Dict[str, Any]], server: str,
                      max_relevant: int) -> List[Dict[str, Any]]:
    """Attach relevance to mapped items and keep the relevant ones."""
    matches = []
    for item in raw_items:
        rel, why = norm_mod.compute_keyword_relevance(
            topic, item.get("title", ""), item.get("abstract", ""),
        )
        if rel > RELEVANCE_THRESHOLD:
            item["relevance"] = rel
            item["why_relevant"] = why
            item["source"] = server
            matches.append(item)
        if len(matches) >= max_relevant:
            break
    return matches[:max_relevant]


def search_preprint_server(
    server: str,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_data: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search a preprint server (biorxiv or medrxiv) for a topic via Europe PMC.

    Args:
        server: "biorxiv" or "medrxiv"
        topic: Search topic
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: "quick", "default", or "deep"
        mock_data: Optional list of Europe PMC result dicts for testing

    Returns:
        Tuple of (list of matching paper dicts, error_message or None)
    """
    max_relevant = DEPTH_LIMITS.get(depth, DEPTH_LIMITS['default'])

    if mock_data is not None:
        mapped = [_map_result(r, server) for r in mock_data]
        return _score_and_filter(topic, mapped, server, max_relevant), None

    publisher = _PUBLISHER.get(server)
    if publisher is None:
        return [], f"unknown preprint server: {server}"

    query = (
        f'({topic}) AND PUBLISHER:"{publisher}" '
        f'AND (FIRST_PDATE:[{from_date} TO {to_date}])'
    )

    results: List[Dict[str, Any]] = []
    cursor = "*"
    try:
        for _ in range(MAX_PAGES):
            params = {
                "query": query,
                "format": "json",
                "resultType": "core",
                "pageSize": PAGE_SIZE,
                "cursorMark": cursor,
            }
            url = f"{EPMC_SEARCH}?{urllib.parse.urlencode(params)}"
            try:
                data = http.get(url, timeout=30)
            except http.HTTPError as e:
                # Return what we have; surface the error only if we have nothing.
                return (results[:max_relevant], str(e)) if not results else (results[:max_relevant], None)

            page = data.get("resultList", {}).get("result", [])
            if not page:
                break
            results.extend(_map_result(r, server) for r in page)

            next_cursor = data.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

            if len(results) >= max_relevant * 2:
                # Enough raw candidates to fill the depth limit after filtering.
                break
    except Exception as e:
        return _score_and_filter(topic, results, server, max_relevant), f"{type(e).__name__}: {e}"

    return _score_and_filter(topic, results, server, max_relevant), None


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
