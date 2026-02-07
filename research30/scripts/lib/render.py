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
    for src in ('biorxiv', 'medrxiv', 'arxiv', 'pubmed', 'huggingface'):
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


def render_compact(report: schema.Report, limit: int = 15) -> str:
    """Render compact output for Claude to synthesize."""
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
    lines.append(f"**Mode:** {report.mode}")
    lines.append("")

    # bioRxiv
    _render_biorxiv_section(lines, "bioRxiv Preprints", report.biorxiv, report.biorxiv_error, limit)

    # medRxiv
    _render_biorxiv_section(lines, "medRxiv Preprints", report.medrxiv, report.medrxiv_error, limit)

    # arXiv
    _render_arxiv_section(lines, report.arxiv, report.arxiv_error, limit)

    # PubMed
    _render_pubmed_section(lines, report.pubmed, report.pubmed_error, limit)

    # HuggingFace
    _render_huggingface_section(lines, report.huggingface, report.huggingface_error, limit)

    return "\n".join(lines)


def _render_biorxiv_section(
    lines: List[str],
    header: str,
    items: List[schema.BiorxivItem],
    error: Optional[str],
    limit: int,
):
    """Render bioRxiv/medRxiv section."""
    if error:
        lines.append(f"### {header}")
        lines.append("")
        lines.append(f"**ERROR:** {error}")
        lines.append("")
        return

    if not items:
        return

    lines.append(f"### {header}")
    lines.append("")

    for item in items[:limit]:
        peer_str = " [PEER REVIEWED]" if item.engagement and item.engagement.published_doi else ""
        date_str = f" ({item.date})" if item.date else ""

        lines.append(f"**{item.id}** (score:{item.score}){date_str}{peer_str}")
        lines.append(f"  {item.title}")
        lines.append(f"  {item.url}")
        lines.append(f"  Category: {item.category}")
        lines.append(f"  *{item.why_relevant}*")
        lines.append("")


def _render_arxiv_section(
    lines: List[str],
    items: List[schema.ArxivItem],
    error: Optional[str],
    limit: int,
):
    """Render arXiv section."""
    if error:
        lines.append("### arXiv Papers")
        lines.append("")
        lines.append(f"**ERROR:** {error}")
        lines.append("")
        return

    if not items:
        return

    lines.append("### arXiv Papers")
    lines.append("")

    for item in items[:limit]:
        date_str = f" ({item.date})" if item.date else ""
        cat_str = f" [{item.primary_category}]" if item.primary_category else ""

        lines.append(f"**{item.id}** (score:{item.score}){date_str}{cat_str}")
        lines.append(f"  {item.title}")
        lines.append(f"  {item.url}")
        lines.append(f"  *{item.why_relevant}*")
        lines.append("")


def _render_pubmed_section(
    lines: List[str],
    items: List[schema.PubmedItem],
    error: Optional[str],
    limit: int,
):
    """Render PubMed section."""
    if error:
        lines.append("### PubMed Articles")
        lines.append("")
        lines.append(f"**ERROR:** {error}")
        lines.append("")
        return

    if not items:
        return

    lines.append("### PubMed Articles")
    lines.append("")

    for item in items[:limit]:
        date_str = f" ({item.date})" if item.date else ""
        journal_str = f" [{item.journal}]" if item.journal else ""

        lines.append(f"**{item.id}** (score:{item.score}){date_str}{journal_str}")
        lines.append(f"  {item.title}")
        lines.append(f"  {item.url}")
        if item.doi:
            lines.append(f"  DOI: {item.doi}")
        lines.append(f"  *{item.why_relevant}*")
        lines.append("")


def _render_huggingface_section(
    lines: List[str],
    items: List[schema.HuggingFaceItem],
    error: Optional[str],
    limit: int,
):
    """Render HuggingFace section."""
    if error:
        lines.append("### HuggingFace")
        lines.append("")
        lines.append(f"**ERROR:** {error}")
        lines.append("")
        return

    if not items:
        return

    # Split into papers vs implementations
    papers = [i for i in items if i.item_type == 'paper']
    implementations = [i for i in items if i.item_type in ('model', 'dataset')]

    if papers:
        lines.append("### HuggingFace Papers")
        lines.append("")
        for item in papers[:limit]:
            date_str = f" ({item.date})" if item.date else ""
            eng_str = ""
            if item.engagement and item.engagement.likes:
                eng_str = f" [{item.engagement.likes} likes]"

            lines.append(f"**{item.id}** (score:{item.score}){date_str}{eng_str}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            lines.append(f"  *{item.why_relevant}*")
            lines.append("")

    if implementations:
        lines.append("### HuggingFace Implementations")
        lines.append("")
        for item in implementations[:limit]:
            date_str = f" ({item.date})" if item.date else ""
            type_str = f" [{item.item_type}]"
            eng_parts = []
            if item.engagement:
                if item.engagement.downloads:
                    eng_parts.append(f"{item.engagement.downloads} downloads")
                if item.engagement.likes:
                    eng_parts.append(f"{item.engagement.likes} likes")
            eng_str = f" [{', '.join(eng_parts)}]" if eng_parts else ""

            lines.append(f"**{item.id}** (score:{item.score}){type_str}{date_str}{eng_str}")
            lines.append(f"  {item.title}")
            lines.append(f"  by {item.author}")
            lines.append(f"  {item.url}")
            lines.append(f"  *{item.why_relevant}*")
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
    for src in ('pubmed', 'biorxiv', 'medrxiv', 'arxiv'):
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
