"""Output rendering for research30 skill."""

import json
from pathlib import Path
from typing import List, Optional

from . import schema

OUTPUT_DIR = Path.home() / ".local" / "share" / "research30" / "out"


def ensure_output_dir():
    """Ensure output directory exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _assess_data_freshness(report: schema.Report) -> dict:
    """Assess how much data is actually from the last 30 days."""
    counts = {}
    for src in ('biorxiv', 'medrxiv', 'arxiv', 'pubmed', 'huggingface', 'openalex', 'semanticscholar'):
        items = getattr(report, src, [])
        recent = sum(1 for i in items if i.date and i.date >= report.range_from)
        counts[src] = {'recent': recent, 'total': len(items)}

    total_recent = sum(v['recent'] for v in counts.values())
    total_items = sum(v['total'] for v in counts.values())

    return {
        'counts': counts,
        'total_recent': total_recent,
        'total_items': total_items,
        'is_sparse': total_recent < 5,
    }


def render_compact(report: schema.Report, limit: int = 25) -> str:
    """Render flat ranked list of top results with abstracts for synthesis."""
    lines = []

    lines.append(f"## Scientific Research Results: {report.topic}")
    lines.append("")

    freshness = _assess_data_freshness(report)
    if freshness['is_sparse']:
        lines.append(f"**LIMITED RECENT DATA** - Only {freshness['total_recent']} item(s) from {report.range_from} to {report.range_to}.")
        lines.append("")

    if report.from_cache:
        age_str = f"{report.cache_age_hours:.1f}h old" if report.cache_age_hours else "cached"
        lines.append(f"**CACHED RESULTS** ({age_str}) - use `--refresh` for fresh data")
        lines.append("")

    lines.append(f"**Date Range:** {report.range_from} to {report.range_to}")

    # Source summary
    all_items = _collect_all_items(report)
    source_counts = _source_counts(report)
    summary_parts = [f"{name}: {count}" for name, count in source_counts if count > 0]
    total = len(all_items)
    showing = min(limit, total)
    lines.append(f"**Sources:** {' | '.join(summary_parts)} ({total} total, showing top {showing})")
    lines.append("")

    # Source errors
    _render_errors_section(lines, report)

    # Flat ranked list
    all_items.sort(key=lambda i: (-i.score,))
    for idx, item in enumerate(all_items[:limit], 1):
        _render_item(lines, idx, item)

    return "\n".join(lines)


def _collect_all_items(report: schema.Report) -> list:
    """Collect all items from report into a flat list."""
    items = []
    items.extend(report.openalex)
    items.extend(report.semanticscholar)
    items.extend(report.pubmed)
    items.extend(report.biorxiv)
    items.extend(report.medrxiv)
    items.extend(report.arxiv)
    items.extend(report.huggingface)
    return items


def _render_errors_section(lines: List[str], report: schema.Report):
    """Render any source errors at the top of the output."""
    errors = []
    for src in ('openalex', 'semanticscholar', 'pubmed', 'biorxiv', 'medrxiv', 'arxiv', 'huggingface'):
        err = getattr(report, f'{src}_error', None)
        if err:
            errors.append((src, err))

    if errors:
        lines.append("### Source Errors")
        lines.append("")
        for src, err in errors:
            lines.append(f"- **{src}:** {err}")
        lines.append("")


def _source_tag(item) -> str:
    """Return a bracketed source tag for display."""
    if isinstance(item, schema.OpenAlexItem):
        return "[OpenAlex]"
    elif isinstance(item, schema.SemanticScholarItem):
        return "[S2]"
    elif isinstance(item, schema.PubmedItem):
        return "[PubMed]"
    elif isinstance(item, schema.BiorxivItem):
        return f"[{item.source}]"
    elif isinstance(item, schema.ArxivItem):
        return "[arXiv]"
    elif isinstance(item, schema.HuggingFaceItem):
        return f"[HF:{item.item_type}]"
    return "[?]"


def _item_metadata(item) -> List[str]:
    """Extract key metadata strings for an item."""
    parts = []

    if isinstance(item, schema.PubmedItem):
        if item.journal:
            parts.append(item.journal)
        if item.doi:
            parts.append(f"DOI: {item.doi}")
        if item.mesh_terms:
            parts.append(f"MeSH: {', '.join(item.mesh_terms[:5])}")
    elif isinstance(item, schema.OpenAlexItem):
        if item.source_name:
            parts.append(item.source_name)
        if item.doi:
            parts.append(f"DOI: {item.doi}")
        if item.engagement and item.engagement.citation_count:
            parts.append(f"{item.engagement.citation_count} citations")
    elif isinstance(item, schema.SemanticScholarItem):
        if item.venue:
            parts.append(item.venue)
        if item.doi:
            parts.append(f"DOI: {item.doi}")
        if item.engagement and item.engagement.citation_count:
            parts.append(f"{item.engagement.citation_count} citations")
    elif isinstance(item, schema.ArxivItem):
        if item.primary_category:
            parts.append(item.primary_category)
    elif isinstance(item, schema.BiorxivItem):
        if item.category:
            parts.append(item.category)
        if item.engagement and item.engagement.published_doi:
            parts.append("PEER REVIEWED")
    elif isinstance(item, schema.HuggingFaceItem):
        if item.item_type:
            parts.append(item.item_type)
        eng_parts = []
        if item.engagement:
            if item.engagement.downloads:
                eng_parts.append(f"{item.engagement.downloads} downloads")
            if item.engagement.likes:
                eng_parts.append(f"{item.engagement.likes} likes")
        if eng_parts:
            parts.extend(eng_parts)

    return parts


def _source_counts(report: schema.Report) -> list:
    """Return list of (display_name, count) for each source."""
    return [
        ("OpenAlex", len(report.openalex)),
        ("S2", len(report.semanticscholar)),
        ("PubMed", len(report.pubmed)),
        ("biorxiv", len(report.biorxiv)),
        ("medRxiv", len(report.medrxiv)),
        ("arXiv", len(report.arxiv)),
        ("HF", len(report.huggingface)),
    ]


def _render_item(lines: List[str], idx: int, item):
    """Render a single numbered item with metadata and abstract."""
    source = _source_tag(item)

    lines.append(f"{idx}. **({item.score})** {item.title} {source}")
    lines.append(f"   {item.date or 'n/a'} | {item.url}")
    meta = _item_metadata(item)
    if meta:
        lines.append(f"   {' | '.join(meta)}")
    abstract = getattr(item, 'abstract', '')
    if abstract:
        lines.append(f"   > {abstract[:200].strip()}")
    lines.append(f"   *{item.why_relevant}*")
    lines.append("")


def render_context_snippet(report: schema.Report) -> str:
    """Render reusable context snippet."""
    lines = []
    lines.append(f"# Context: {report.topic} (Last 30 Days Scientific Research)")
    lines.append("")
    lines.append(f"*Generated: {report.generated_at[:10]} | Sources: {report.mode}*")
    lines.append("")

    lines.append("## Key Sources")
    lines.append("")

    all_items = []
    for src in ('pubmed', 'semanticscholar', 'openalex', 'biorxiv', 'medrxiv', 'arxiv'):
        for item in getattr(report, src, [])[:5]:
            all_items.append((item.score, src, item.title, item.url))
    for item in report.huggingface[:3]:
        all_items.append((item.score, 'HF', item.title, item.url))

    all_items.sort(key=lambda x: -x[0])
    for score, source, title, url in all_items[:10]:
        lines.append(f"- [{source}] {title[:80]}")

    lines.append("")
    return "\n".join(lines)


def render_full_report(report: schema.Report) -> str:
    """Render full markdown report."""
    lines = []
    lines.append(f"# {report.topic} - Scientific Research Report (Last 30 Days)")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Date Range:** {report.range_from} to {report.range_to}")
    lines.append(f"**Mode:** {report.mode}")
    lines.append("")

    for src in ('biorxiv', 'medrxiv'):
        items = getattr(report, src, [])
        if items:
            lines.append(f"## {src.capitalize()} Preprints")
            lines.append("")
            for item in items:
                lines.append(f"### {item.title}")
                lines.append(f"- **DOI:** {item.preprint_doi}")
                lines.append(f"- **Date:** {item.date or 'Unknown'}")
                lines.append(f"- **Category:** {item.category}")
                lines.append(f"- **Authors:** {item.authors}")
                lines.append(f"- **Score:** {item.score}/100")
                lines.append(f"- **URL:** {item.url}")
                if item.abstract:
                    lines.append(f"\n> {item.abstract[:300]}...")
                lines.append("")

    if report.arxiv:
        lines.append("## arXiv Papers")
        lines.append("")
        for item in report.arxiv:
            lines.append(f"### {item.title}")
            lines.append(f"- **arXiv ID:** {item.arxiv_id}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Category:** {item.primary_category}")
            lines.append(f"- **Authors:** {item.authors}")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **URL:** {item.url}")
            if item.abstract:
                lines.append(f"\n> {item.abstract[:300]}...")
            lines.append("")

    if report.pubmed:
        lines.append("## PubMed Articles")
        lines.append("")
        for item in report.pubmed:
            lines.append(f"### {item.title}")
            lines.append(f"- **PMID:** {item.pmid}")
            lines.append(f"- **Journal:** {item.journal}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **DOI:** {item.doi or 'N/A'}")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **URL:** {item.url}")
            if item.abstract:
                lines.append(f"\n> {item.abstract[:300]}...")
            lines.append("")

    if report.openalex:
        lines.append("## OpenAlex Works")
        lines.append("")
        for item in report.openalex:
            lines.append(f"### {item.title}")
            lines.append(f"- **OpenAlex ID:** {item.openalex_id}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Source:** {item.source_name}")
            lines.append(f"- **Type:** {item.work_type}")
            lines.append(f"- **Authors:** {item.authors}")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **URL:** {item.url}")
            if item.doi:
                lines.append(f"- **DOI:** {item.doi}")
            if item.abstract:
                lines.append(f"\n> {item.abstract[:300]}...")
            lines.append("")

    if report.semanticscholar:
        lines.append("## Semantic Scholar")
        lines.append("")
        for item in report.semanticscholar:
            lines.append(f"### {item.title}")
            lines.append(f"- **Paper ID:** {item.paper_id}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Venue:** {item.venue}")
            lines.append(f"- **Authors:** {item.authors}")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **URL:** {item.url}")
            if item.doi:
                lines.append(f"- **DOI:** {item.doi}")
            if item.abstract:
                lines.append(f"\n> {item.abstract[:300]}...")
            lines.append("")

    if report.huggingface:
        lines.append("## HuggingFace")
        lines.append("")
        for item in report.huggingface:
            lines.append(f"### {item.title} ({item.item_type})")
            lines.append(f"- **Author:** {item.author}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **URL:** {item.url}")
            lines.append("")

    return "\n".join(lines)


def write_outputs(report: schema.Report):
    """Write all output files."""
    ensure_output_dir()

    with open(OUTPUT_DIR / "report.json", 'w') as f:
        json.dump(report.to_dict(), f, indent=2)

    with open(OUTPUT_DIR / "report.md", 'w') as f:
        f.write(render_full_report(report))

    with open(OUTPUT_DIR / "context.md", 'w') as f:
        f.write(render_context_snippet(report))


def get_context_path() -> str:
    """Get path to context file."""
    return str(OUTPUT_DIR / "context.md")
