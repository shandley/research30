"""arXiv API client for research30 skill.

API: GET http://export.arxiv.org/api/query?search_query=...&sortBy=submittedDate&sortOrder=descending
Returns Atom XML. Rate limit: ~1 req/3 sec.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from . import http, xml_parse, normalize as norm_mod


DEPTH_LIMITS = {
    'quick': 30,
    'default': 100,
    'deep': 200,
}


def search_arxiv(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_data: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search arXiv for papers matching a topic.

    Args:
        topic: Search query
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: "quick", "default", or "deep"
        mock_data: Optional mock XML string for testing

    Returns:
        Tuple of (list of paper dicts, error_message or None)
    """
    max_results = DEPTH_LIMITS.get(depth, DEPTH_LIMITS['default'])
    error = None

    if mock_data is not None:
        papers = xml_parse.parse_arxiv_atom(mock_data)
        for paper in papers:
            rel, why = norm_mod.compute_keyword_relevance(
                topic,
                paper.get('title', ''),
                paper.get('abstract', ''),
            )
            paper['relevance'] = rel
            paper['why_relevant'] = why
        return papers, None

    # Build query: arXiv search supports keyword search
    # Use quotes for multi-word phrases to get exact phrase matching
    # Date filter via submittedDate range
    # Format dates for arXiv: YYYYMMDDHHMMSS
    from_arxiv = from_date.replace('-', '') + "0000"
    to_arxiv = to_date.replace('-', '') + "2359"

    # Quote multi-word topics for phrase matching
    topic_words = topic.strip().split()
    if len(topic_words) > 1:
        search_term = quote(f'"{topic}"')
    else:
        search_term = quote(topic)

    query = f"all:{search_term}+AND+submittedDate:[{from_arxiv}+TO+{to_arxiv}]"

    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&start=0&max_results={max_results}"
    )

    try:
        xml_text = http.get_text(url, timeout=60)
        papers = xml_parse.parse_arxiv_atom(xml_text)

        # Compute keyword relevance for scoring
        for paper in papers:
            rel, why = norm_mod.compute_keyword_relevance(
                topic,
                paper.get('title', ''),
                paper.get('abstract', ''),
            )
            paper['relevance'] = rel
            paper['why_relevant'] = why

    except http.HTTPError as e:
        error = str(e)
        papers = []
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        papers = []

    return papers, error
