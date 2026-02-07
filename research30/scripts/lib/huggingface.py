"""HuggingFace Hub API client for research30 skill.

Models: GET https://huggingface.co/api/models?search={topic}&sort=likes&limit=50
Datasets: GET https://huggingface.co/api/datasets?search={topic}&sort=likes&limit=50
Daily papers: GET https://huggingface.co/api/daily_papers

All JSON, filter by date locally. No API key needed.
"""

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from . import http, normalize as norm_mod


DEPTH_LIMITS = {
    'quick': 20,
    'default': 50,
    'deep': 100,
}


def search_huggingface(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_models: Optional[List[Dict[str, Any]]] = None,
    mock_papers: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search HuggingFace for models, datasets, and papers.

    Args:
        topic: Search query
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: "quick", "default", or "deep"
        mock_models: Optional mock models data for testing
        mock_papers: Optional mock papers data for testing

    Returns:
        Tuple of (list of HF item dicts, error_message or None)
    """
    limit = DEPTH_LIMITS.get(depth, DEPTH_LIMITS['default'])
    all_items = []
    errors = []

    # Search models
    if mock_models is not None:
        models = mock_models
    else:
        models, err = _search_models(topic, limit)
        if err:
            errors.append(f"models: {err}")

    for m in models:
        item = _normalize_model(m, topic)
        if item and item.get('date', '') >= from_date:
            all_items.append(item)

    # Search datasets
    if mock_models is None:
        datasets, err = _search_datasets(topic, limit)
        if err:
            errors.append(f"datasets: {err}")
        for d in datasets:
            item = _normalize_dataset(d, topic)
            if item and item.get('date', '') >= from_date:
                all_items.append(item)

    # Search daily papers
    if mock_papers is not None:
        papers = mock_papers
    else:
        papers, err = _search_papers(topic, from_date)
        if err:
            errors.append(f"papers: {err}")

    for p in papers:
        item = _normalize_paper(p, topic)
        if item and item.get('date', '') >= from_date:
            all_items.append(item)

    error = '; '.join(errors) if errors else None
    return all_items, error


def _search_models(topic: str, limit: int) -> Tuple[List[Dict], Optional[str]]:
    """Search HuggingFace models."""
    encoded = quote(topic)
    url = f"https://huggingface.co/api/models?search={encoded}&sort=likes&direction=-1&limit={limit}"

    try:
        data = http.get(url, timeout=30)
        if isinstance(data, list):
            return data, None
        return [], None
    except http.HTTPError as e:
        return [], str(e)
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def _search_datasets(topic: str, limit: int) -> Tuple[List[Dict], Optional[str]]:
    """Search HuggingFace datasets."""
    encoded = quote(topic)
    url = f"https://huggingface.co/api/datasets?search={encoded}&sort=likes&direction=-1&limit={limit}"

    try:
        data = http.get(url, timeout=30)
        if isinstance(data, list):
            return data, None
        return [], None
    except http.HTTPError as e:
        return [], str(e)
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def _search_papers(topic: str, from_date: str) -> Tuple[List[Dict], Optional[str]]:
    """Fetch daily papers and filter by topic."""
    url = "https://huggingface.co/api/daily_papers"

    try:
        data = http.get(url, timeout=30)
        if not isinstance(data, list):
            return [], None

        # Filter by topic relevance
        relevant = []
        for paper in data:
            title = paper.get('title', '') or ''
            # daily_papers may have nested paper object
            if 'paper' in paper and isinstance(paper['paper'], dict):
                title = paper['paper'].get('title', title)

            rel, _ = norm_mod.compute_keyword_relevance(
                topic, title, ''
            )
            if rel > 0.1:
                relevant.append(paper)

        return relevant, None
    except http.HTTPError as e:
        return [], str(e)
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def _normalize_model(raw: Dict[str, Any], topic: str) -> Optional[Dict[str, Any]]:
    """Normalize a HuggingFace model to standard dict."""
    model_id = raw.get('modelId') or raw.get('id', '')
    if not model_id:
        return None

    title = model_id.split('/')[-1] if '/' in model_id else model_id
    author = model_id.split('/')[0] if '/' in model_id else ''

    # Parse date from lastModified or createdAt
    date = None
    for field in ('lastModified', 'createdAt'):
        val = raw.get(field, '')
        if val and len(val) >= 10:
            date = val[:10]
            break

    downloads = raw.get('downloads', 0)
    likes = raw.get('likes', 0)
    tags = raw.get('tags', []) or []

    rel, why = norm_mod.compute_keyword_relevance(topic, title, ' '.join(tags))

    return {
        'hf_id': model_id,
        'title': title,
        'author': author,
        'item_type': 'model',
        'tags': tags,
        'date': date,
        'downloads': downloads,
        'likes': likes,
        'relevance': rel,
        'why_relevant': why,
        'url': f"https://huggingface.co/{model_id}",
    }


def _normalize_dataset(raw: Dict[str, Any], topic: str) -> Optional[Dict[str, Any]]:
    """Normalize a HuggingFace dataset to standard dict."""
    ds_id = raw.get('id', '')
    if not ds_id:
        return None

    title = ds_id.split('/')[-1] if '/' in ds_id else ds_id
    author = ds_id.split('/')[0] if '/' in ds_id else ''

    date = None
    for field in ('lastModified', 'createdAt'):
        val = raw.get(field, '')
        if val and len(val) >= 10:
            date = val[:10]
            break

    downloads = raw.get('downloads', 0)
    likes = raw.get('likes', 0)
    tags = raw.get('tags', []) or []

    rel, why = norm_mod.compute_keyword_relevance(topic, title, ' '.join(tags))

    return {
        'hf_id': ds_id,
        'title': title,
        'author': author,
        'item_type': 'dataset',
        'tags': tags,
        'date': date,
        'downloads': downloads,
        'likes': likes,
        'relevance': rel,
        'why_relevant': why,
        'url': f"https://huggingface.co/datasets/{ds_id}",
    }


def _normalize_paper(raw: Dict[str, Any], topic: str) -> Optional[Dict[str, Any]]:
    """Normalize a HuggingFace daily paper to standard dict."""
    # daily_papers API returns objects with nested 'paper' field
    paper = raw.get('paper', raw)
    paper_id = paper.get('id', '') or raw.get('id', '')
    title = paper.get('title', '') or raw.get('title', '')

    if not title:
        return None

    # Authors
    authors = paper.get('authors', [])
    if isinstance(authors, list):
        author_names = []
        for a in authors[:3]:
            if isinstance(a, dict):
                author_names.append(a.get('name', ''))
            elif isinstance(a, str):
                author_names.append(a)
        author = ', '.join(filter(None, author_names))
    else:
        author = str(authors)

    # Date
    date = raw.get('publishedAt', '') or paper.get('publishedAt', '')
    if date and len(date) >= 10:
        date = date[:10]
    else:
        date = None

    # Summary/abstract
    summary = paper.get('summary', '') or ''

    rel, why = norm_mod.compute_keyword_relevance(topic, title, summary)

    upvotes = raw.get('paper', {}).get('upvotes', 0) if isinstance(raw.get('paper'), dict) else 0

    return {
        'hf_id': paper_id,
        'title': title,
        'author': author,
        'item_type': 'paper',
        'tags': [],
        'date': date,
        'downloads': 0,
        'likes': upvotes,
        'relevance': rel,
        'why_relevant': why,
        'url': f"https://huggingface.co/papers/{paper_id}",
    }
