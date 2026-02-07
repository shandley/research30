#!/usr/bin/env python3
"""
research30 - Search scientific literature from the last 30 days.

Sources: OpenAlex, Semantic Scholar, PubMed, arXiv, HuggingFace Hub (+ bioRxiv/medRxiv on request)

Usage:
    python3 research30.py <topic> [options]

Options:
    --mock              Use fixtures instead of real API calls
    --emit=MODE         Output mode: compact|json|md|context|path (default: compact)
    --sources=MODE      Source filter: all|preprints|pubmed|huggingface|openalex|semanticscholar|biorxiv|arxiv (default: all)
    --quick             Fewer results per source
    --deep              More results per source
    --debug             Enable verbose debug logging
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from lib import (
    arxiv,
    biorxiv,
    cache,
    dates,
    dedupe,
    env,
    http,
    huggingface,
    normalize,
    openalex,
    pubmed,
    render,
    schema,
    score,
    semanticscholar,
    ui,
)


def load_fixture(name: str):
    """Load a fixture file."""
    fixture_path = SCRIPT_DIR.parent / "fixtures" / name
    if fixture_path.exists():
        with open(fixture_path) as f:
            content = f.read()
            if name.endswith('.json'):
                return json.loads(content)
            return content  # XML
    return None


def _search_biorxiv(topic, from_date, to_date, depth, mock):
    """Search bioRxiv (runs in thread)."""
    if mock:
        mock_data = load_fixture("biorxiv_sample.json")
        if mock_data:
            return biorxiv.search_biorxiv(topic, from_date, to_date, depth, mock_data=mock_data.get('collection', []))
    return biorxiv.search_biorxiv(topic, from_date, to_date, depth)


def _search_medrxiv(topic, from_date, to_date, depth, mock):
    """Search medRxiv (runs in thread)."""
    if mock:
        mock_data = load_fixture("biorxiv_sample.json")
        if mock_data:
            return biorxiv.search_medrxiv(topic, from_date, to_date, depth, mock_data=mock_data.get('collection', []))
    return biorxiv.search_medrxiv(topic, from_date, to_date, depth)


def _search_arxiv(topic, from_date, to_date, depth, mock):
    """Search arXiv (runs in thread)."""
    if mock:
        mock_data = load_fixture("arxiv_sample.xml")
        if mock_data:
            return arxiv.search_arxiv(topic, from_date, to_date, depth, mock_data=mock_data)
    return arxiv.search_arxiv(topic, from_date, to_date, depth)


def _search_pubmed(topic, from_date, to_date, depth, mock, api_key):
    """Search PubMed (runs in thread)."""
    if mock:
        mock_esearch = load_fixture("pubmed_esearch_sample.json")
        mock_efetch = load_fixture("pubmed_efetch_sample.xml")
        return pubmed.search_pubmed(topic, from_date, to_date, depth,
                                    api_key=api_key,
                                    mock_esearch=mock_esearch,
                                    mock_efetch=mock_efetch)
    return pubmed.search_pubmed(topic, from_date, to_date, depth, api_key=api_key)


def _search_huggingface(topic, from_date, to_date, depth, mock):
    """Search HuggingFace (runs in thread)."""
    if mock:
        mock_models = load_fixture("hf_models_sample.json")
        mock_papers = load_fixture("hf_papers_sample.json")
        return huggingface.search_huggingface(topic, from_date, to_date, depth,
                                               mock_models=mock_models,
                                               mock_papers=mock_papers)
    return huggingface.search_huggingface(topic, from_date, to_date, depth)


def _search_openalex(topic, from_date, to_date, depth, mock, topic_ids=None):
    """Search OpenAlex (runs in thread)."""
    if mock:
        mock_data = load_fixture("openalex_sample.json")
        if mock_data:
            return openalex.search_openalex(topic, from_date, to_date, depth,
                                            mock_data=mock_data.get('results', []))
    return openalex.search_openalex(topic, from_date, to_date, depth, topic_ids=topic_ids)


def _search_semanticscholar(topic, from_date, to_date, depth, mock, api_key):
    """Search Semantic Scholar (runs in thread)."""
    if mock:
        mock_data = load_fixture("semanticscholar_sample.json")
        if mock_data:
            return semanticscholar.search_semantic_scholar(
                topic, from_date, to_date, depth,
                api_key=api_key, mock_data=mock_data.get('data', []))
    return semanticscholar.search_semantic_scholar(
        topic, from_date, to_date, depth, api_key=api_key)


def determine_sources(requested: str) -> set:
    """Determine which sources to query."""
    source_map = {
        'all': {'openalex', 'semanticscholar', 'arxiv', 'pubmed', 'huggingface'},
        'preprints': {'openalex', 'arxiv'},
        'openalex': {'openalex'},
        'semanticscholar': {'semanticscholar'},
        'biorxiv': {'biorxiv'},
        'medrxiv': {'medrxiv'},
        'arxiv': {'arxiv'},
        'pubmed': {'pubmed'},
        'huggingface': {'huggingface'},
    }
    return source_map.get(requested, source_map['all'])


def run_research(
    topic: str,
    sources_set: set,
    config: dict,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock: bool = False,
    progress: ui.ProgressDisplay = None,
) -> dict:
    """Run the research pipeline across all sources in parallel.

    Returns dict with source keys mapping to (items, error) tuples.
    """
    ncbi_key = config.get('NCBI_API_KEY')
    s2_key = config.get('S2_API_KEY')
    results = {}

    # Discover OpenAlex topics before launching parallel searches.
    # This is a fast, lightweight call (~50ms) that enables topic-augmented search.
    topic_ids = None
    if 'openalex' in sources_set and not mock:
        topic_ids = openalex.discover_topics(topic)

    # Build futures
    search_funcs = {}
    if 'openalex' in sources_set:
        search_funcs['openalex'] = lambda: _search_openalex(topic, from_date, to_date, depth, mock, topic_ids)
    if 'semanticscholar' in sources_set:
        search_funcs['semanticscholar'] = lambda: _search_semanticscholar(topic, from_date, to_date, depth, mock, s2_key)
    if 'biorxiv' in sources_set:
        search_funcs['biorxiv'] = lambda: _search_biorxiv(topic, from_date, to_date, depth, mock)
    if 'medrxiv' in sources_set:
        search_funcs['medrxiv'] = lambda: _search_medrxiv(topic, from_date, to_date, depth, mock)
    if 'arxiv' in sources_set:
        search_funcs['arxiv'] = lambda: _search_arxiv(topic, from_date, to_date, depth, mock)
    if 'pubmed' in sources_set:
        search_funcs['pubmed'] = lambda: _search_pubmed(topic, from_date, to_date, depth, mock, ncbi_key)
    if 'huggingface' in sources_set:
        search_funcs['huggingface'] = lambda: _search_huggingface(topic, from_date, to_date, depth, mock)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for source, func in search_funcs.items():
            if progress:
                progress.start_source(source)
            futures[executor.submit(func)] = source

        for future in as_completed(futures):
            source = futures[future]
            try:
                items, error = future.result()
                results[source] = (items, error)
                if error and progress:
                    progress.show_error(f"{source}: {error}")
            except Exception as e:
                results[source] = ([], f"{type(e).__name__}: {e}")
                if progress:
                    progress.show_error(f"{source}: {e}")

            if progress:
                items_result = results[source][0]
                progress.end_source(source, len(items_result))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Search scientific literature from the last 30 days"
    )
    parser.add_argument("topic", nargs="?", help="Research topic")
    parser.add_argument("--mock", action="store_true", help="Use fixtures")
    parser.add_argument(
        "--emit",
        choices=["compact", "json", "md", "context", "path"],
        default="compact",
        help="Output mode",
    )
    parser.add_argument(
        "--sources",
        choices=["all", "preprints", "pubmed", "huggingface", "openalex", "semanticscholar", "biorxiv", "medrxiv", "arxiv"],
        default="all",
        help="Source filter",
    )
    parser.add_argument("--quick", action="store_true", help="Fewer results per source")
    parser.add_argument("--deep", action="store_true", help="More results per source")
    parser.add_argument("--refresh", action="store_true", help="Bypass cache, fetch fresh results")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    if args.debug:
        os.environ["RESEARCH30_DEBUG"] = "1"
        from lib import http as http_module
        http_module.DEBUG = True

    if args.quick and args.deep:
        print("Error: Cannot use both --quick and --deep", file=sys.stderr)
        sys.exit(1)

    depth = "quick" if args.quick else ("deep" if args.deep else "default")

    if not args.topic:
        print("Error: Please provide a research topic.", file=sys.stderr)
        print("Usage: python3 research30.py <topic> [options]", file=sys.stderr)
        sys.exit(1)

    # Load config
    config = env.get_config()

    # Get date range
    from_date, to_date = dates.get_date_range(30)

    # Determine sources
    sources_set = determine_sources(args.sources)

    # Check cache
    cache_key = cache.get_cache_key(args.topic, from_date, to_date, args.sources)
    if not args.mock and not args.refresh:
        cached_data, cache_age = cache.load_cache_with_age(cache_key)
        if cached_data:
            try:
                report = schema.Report.from_dict(cached_data)
            except (KeyError, TypeError):
                # Stale cache from older schema version — ignore and fetch fresh
                cached_data = None
            else:
                report.from_cache = True
                report.cache_age_hours = cache_age

                progress = ui.ProgressDisplay(args.topic, show_banner=True)
                progress.show_cached(cache_age)

                output_result(report, args.emit, depth)
                return

    # Initialize progress display
    progress = ui.ProgressDisplay(args.topic, show_banner=True)

    # Run research
    raw_results = run_research(
        args.topic, sources_set, config,
        from_date, to_date, depth, args.mock, progress,
    )

    # Processing phase
    progress.start_processing()

    # Normalize items from each source
    openalex_items = normalize.normalize_openalex_items(
        raw_results.get('openalex', ([], None))[0], from_date, to_date
    )
    s2_items = normalize.normalize_semanticscholar_items(
        raw_results.get('semanticscholar', ([], None))[0], from_date, to_date
    )
    biorxiv_items = normalize.normalize_biorxiv_items(
        raw_results.get('biorxiv', ([], None))[0], from_date, to_date, 'biorxiv'
    )
    medrxiv_items = normalize.normalize_biorxiv_items(
        raw_results.get('medrxiv', ([], None))[0], from_date, to_date, 'medrxiv'
    )
    arxiv_items = normalize.normalize_arxiv_items(
        raw_results.get('arxiv', ([], None))[0], from_date, to_date
    )
    pubmed_items = normalize.normalize_pubmed_items(
        raw_results.get('pubmed', ([], None))[0], from_date, to_date
    )
    hf_items = normalize.normalize_huggingface_items(
        raw_results.get('huggingface', ([], None))[0], from_date, to_date
    )

    # Date filter
    openalex_items = normalize.filter_by_date_range(openalex_items, from_date, to_date)
    s2_items = normalize.filter_by_date_range(s2_items, from_date, to_date)
    biorxiv_items = normalize.filter_by_date_range(biorxiv_items, from_date, to_date)
    medrxiv_items = normalize.filter_by_date_range(medrxiv_items, from_date, to_date)
    arxiv_items = normalize.filter_by_date_range(arxiv_items, from_date, to_date)
    pubmed_items = normalize.filter_by_date_range(pubmed_items, from_date, to_date)
    hf_items = normalize.filter_by_date_range(hf_items, from_date, to_date)

    # Score items
    openalex_items = score.score_openalex_items(openalex_items)
    s2_items = score.score_semanticscholar_items(s2_items)
    biorxiv_items = score.score_biorxiv_items(biorxiv_items)
    medrxiv_items = score.score_biorxiv_items(medrxiv_items)
    arxiv_items = score.score_arxiv_items(arxiv_items)
    pubmed_items = score.score_pubmed_items(pubmed_items)
    hf_items = score.score_huggingface_items(hf_items)

    # Sort items
    openalex_items = score.sort_items(openalex_items)
    s2_items = score.sort_items(s2_items)
    biorxiv_items = score.sort_items(biorxiv_items)
    medrxiv_items = score.sort_items(medrxiv_items)
    arxiv_items = score.sort_items(arxiv_items)
    pubmed_items = score.sort_items(pubmed_items)
    hf_items = score.sort_items(hf_items)

    # Dedupe within sources
    openalex_items = dedupe.dedupe_within_source(openalex_items)
    s2_items = dedupe.dedupe_within_source(s2_items)
    biorxiv_items = dedupe.dedupe_within_source(biorxiv_items)
    medrxiv_items = dedupe.dedupe_within_source(medrxiv_items)
    arxiv_items = dedupe.dedupe_within_source(arxiv_items)
    pubmed_items = dedupe.dedupe_within_source(pubmed_items)
    hf_items = dedupe.dedupe_within_source(hf_items)

    # Cross-source dedup
    all_items = openalex_items + s2_items + biorxiv_items + medrxiv_items + arxiv_items + pubmed_items + hf_items
    deduped_all = dedupe.dedupe_cross_source(all_items)

    # Rebuild per-source lists from deduped results
    openalex_final = [i for i in deduped_all if isinstance(i, schema.OpenAlexItem)]
    s2_final = [i for i in deduped_all if isinstance(i, schema.SemanticScholarItem)]
    biorxiv_final = [i for i in deduped_all if isinstance(i, schema.BiorxivItem) and i.source == 'biorxiv']
    medrxiv_final = [i for i in deduped_all if isinstance(i, schema.BiorxivItem) and i.source == 'medrxiv']
    arxiv_final = [i for i in deduped_all if isinstance(i, schema.ArxivItem)]
    pubmed_final = [i for i in deduped_all if isinstance(i, schema.PubmedItem)]
    hf_final = [i for i in deduped_all if isinstance(i, schema.HuggingFaceItem)]

    progress.end_processing()

    # Create report
    report = schema.create_report(args.topic, from_date, to_date, args.sources)
    report.openalex = openalex_final
    report.semanticscholar = s2_final
    report.biorxiv = biorxiv_final
    report.medrxiv = medrxiv_final
    report.arxiv = arxiv_final
    report.pubmed = pubmed_final
    report.huggingface = hf_final

    # Set per-source errors
    for src in ('openalex', 'semanticscholar', 'biorxiv', 'medrxiv', 'arxiv', 'pubmed', 'huggingface'):
        if src in raw_results:
            _, err = raw_results[src]
            if err:
                setattr(report, f'{src}_error', err)

    # Write outputs
    render.write_outputs(report)

    # Save to cache
    if not args.mock:
        cache.save_cache(cache_key, report.to_dict())

    # Show completion
    counts = {
        'OpenAlex': len(openalex_final),
        'S2': len(s2_final),
        'bioRxiv': len(biorxiv_final),
        'medRxiv': len(medrxiv_final),
        'arXiv': len(arxiv_final),
        'PubMed': len(pubmed_final),
        'HuggingFace': len(hf_final),
    }
    progress.show_complete(counts)

    # Output result
    output_result(report, args.emit, depth)


DISPLAY_LIMITS = {'quick': 10, 'default': 25, 'deep': 50}


def output_result(report: schema.Report, emit_mode: str, depth: str = "default"):
    """Output the result based on emit mode."""
    if emit_mode == "compact":
        limit = DISPLAY_LIMITS.get(depth, 25)
        print(render.render_compact(report, limit=limit))
    elif emit_mode == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif emit_mode == "md":
        print(render.render_full_report(report))
    elif emit_mode == "context":
        print(render.render_context_snippet(report))
    elif emit_mode == "path":
        print(render.get_context_path())


if __name__ == "__main__":
    main()
