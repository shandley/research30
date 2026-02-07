"""Output rendering for research30 skill."""

import json
from html import escape
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
        lines.append(f"**CACHED RESULTS** ({age_str}) — use `--refresh` for fresh data")
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

    # Flat ranked list — sort by score desc, then date desc for tiebreaking
    all_items.sort(key=lambda i: (-i.score, -(int((i.date or '0000-00-00')[:10].replace('-', '') or '0'))))
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


def render_html(report: schema.Report, limit: int = 25) -> str:
    """Render self-contained HTML report with score badges and collapsible abstracts."""
    all_items = _collect_all_items(report)
    all_items.sort(key=lambda i: (-i.score, -(int((i.date or '0000-00-00')[:10].replace('-', '') or '0'))))
    showing = all_items[:limit]

    source_counts = _source_counts(report)
    summary_parts = [f"{name}: {count}" for name, count in source_counts if count > 0]
    total = len(all_items)

    freshness = _assess_data_freshness(report)

    rows_html = []
    for idx, item in enumerate(showing, 1):
        rows_html.append(_html_item(idx, item))

    errors_html = _html_errors(report)
    cache_html = ""
    if report.from_cache:
        age_str = f"{report.cache_age_hours:.1f}h old" if report.cache_age_hours else "cached"
        cache_html = f'<div class="notice">Cached results ({escape(age_str)}) — use --refresh for fresh data</div>'

    sparse_html = ""
    if freshness['is_sparse']:
        sparse_html = f'<div class="notice warning">Limited recent data — only {freshness["total_recent"]} item(s) from {escape(report.range_from)} to {escape(report.range_to)}</div>'

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research: {escape(report.topic)}</title>
<style>
{_html_css()}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>{escape(report.topic)}</h1>
    <div class="meta">
      <span>{escape(report.range_from)} to {escape(report.range_to)}</span>
      <span class="sep">|</span>
      <span>{escape(' | '.join(summary_parts))}</span>
      <span class="sep">|</span>
      <span>{total} total, showing top {len(showing)}</span>
    </div>
  </header>
  {sparse_html}
  {cache_html}
  {errors_html}
  <ol class="results">
    {''.join(rows_html)}
  </ol>
  <footer>
    Generated {escape(report.generated_at[:10])} by research30
  </footer>
</div>
</body>
</html>"""
    return body


def _html_css() -> str:
    """Return inline CSS for the HTML report."""
    return """
*, *::before, *::after { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5;
  color: #1a1a1a;
  background: #f8f9fa;
  margin: 0;
  padding: 1rem;
}
.container { max-width: 900px; margin: 0 auto; }
header { margin-bottom: 1.5rem; }
h1 { margin: 0 0 0.25rem 0; font-size: 1.5rem; }
.meta { color: #555; font-size: 0.85rem; }
.meta .sep { margin: 0 0.35rem; color: #ccc; }
.notice {
  background: #e8f4fd; border-left: 3px solid #4a9eda;
  padding: 0.5rem 0.75rem; margin-bottom: 1rem; font-size: 0.85rem;
}
.notice.warning { background: #fff3cd; border-left-color: #d4a017; }
.notice.error { background: #fde8e8; border-left-color: #d44; }
.errors { margin-bottom: 1rem; }
.errors h2 { font-size: 1rem; margin: 0 0 0.5rem 0; }
.errors li { font-size: 0.85rem; color: #b33; }
ol.results { list-style: none; padding: 0; margin: 0; counter-reset: item; }
ol.results > li {
  counter-increment: item;
  background: #fff; border: 1px solid #e0e0e0; border-radius: 6px;
  padding: 0.75rem 1rem; margin-bottom: 0.5rem;
}
ol.results > li:hover { border-color: #bbb; }
.item-header { display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; }
.rank { color: #888; font-size: 0.85rem; min-width: 2rem; }
.score {
  display: inline-block; padding: 0.1rem 0.45rem; border-radius: 3px;
  font-size: 0.8rem; font-weight: 600; color: #fff;
}
.score-high { background: #2a7d3f; }
.score-mid { background: #b38600; }
.score-low { background: #888; }
.item-title { font-weight: 600; font-size: 0.95rem; }
.item-title a { color: #1a1a1a; text-decoration: none; }
.item-title a:hover { text-decoration: underline; }
.source-tag {
  display: inline-block; padding: 0.05rem 0.4rem; border-radius: 3px;
  font-size: 0.7rem; font-weight: 600; color: #fff; white-space: nowrap;
}
.src-pubmed { background: #2563a0; }
.src-s2 { background: #7c3aed; }
.src-openalex { background: #0d7377; }
.src-arxiv { background: #b31b1b; }
.src-biorxiv { background: #cf6a1e; }
.src-medrxiv { background: #a84e1e; }
.src-hf { background: #c49000; }
.src-unknown { background: #888; }
.item-meta { font-size: 0.8rem; color: #555; margin-top: 0.2rem; }
.item-meta a { color: #555; }
details { margin-top: 0.3rem; }
summary {
  font-size: 0.8rem; color: #666; cursor: pointer;
  user-select: none; list-style: none;
}
summary::-webkit-details-marker { display: none; }
summary::before { content: "Show abstract"; }
details[open] summary::before { content: "Hide abstract"; }
.abstract {
  font-size: 0.85rem; color: #333; margin-top: 0.25rem;
  padding: 0.5rem; background: #f5f5f5; border-radius: 4px;
}
.relevance { font-size: 0.75rem; color: #888; margin-top: 0.2rem; font-style: italic; }
footer {
  margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;
  font-size: 0.8rem; color: #888; text-align: center;
}
"""


def _html_source_class(item) -> str:
    """Return CSS class for source tag color."""
    if isinstance(item, schema.PubmedItem):
        return "src-pubmed"
    elif isinstance(item, schema.SemanticScholarItem):
        return "src-s2"
    elif isinstance(item, schema.OpenAlexItem):
        return "src-openalex"
    elif isinstance(item, schema.ArxivItem):
        return "src-arxiv"
    elif isinstance(item, schema.BiorxivItem):
        return "src-medrxiv" if item.source == "medrxiv" else "src-biorxiv"
    elif isinstance(item, schema.HuggingFaceItem):
        return "src-hf"
    return "src-unknown"


def _html_source_label(item) -> str:
    """Return display label for source tag."""
    if isinstance(item, schema.PubmedItem):
        return "PubMed"
    elif isinstance(item, schema.SemanticScholarItem):
        return "S2"
    elif isinstance(item, schema.OpenAlexItem):
        return "OpenAlex"
    elif isinstance(item, schema.ArxivItem):
        return "arXiv"
    elif isinstance(item, schema.BiorxivItem):
        return item.source
    elif isinstance(item, schema.HuggingFaceItem):
        return f"HF:{item.item_type}"
    return "?"


def _html_score_class(score: int) -> str:
    """Return CSS class for score badge color."""
    if score >= 80:
        return "score-high"
    elif score >= 60:
        return "score-mid"
    return "score-low"


def _html_item(idx: int, item) -> str:
    """Render a single result item as an HTML list element."""
    source_class = _html_source_class(item)
    source_label = _html_source_label(item)
    score_class = _html_score_class(item.score)
    url = escape(item.url or '')
    title = escape(item.title or '')
    date = escape((item.date or 'n/a')[:10])

    meta_parts = _item_metadata(item)
    meta_html = ""
    if meta_parts:
        escaped_parts = []
        for p in meta_parts:
            if p.startswith("DOI: "):
                doi = p[5:]
                escaped_parts.append(f'DOI: <a href="https://doi.org/{escape(doi)}" target="_blank">{escape(doi)}</a>')
            else:
                escaped_parts.append(escape(p))
        meta_html = f'<div class="item-meta">{" | ".join(escaped_parts)}</div>'

    abstract = getattr(item, 'abstract', '')
    abstract_html = ""
    if abstract:
        abstract_html = f"""<details>
      <summary></summary>
      <div class="abstract">{escape(abstract)}</div>
    </details>"""

    relevance_html = ""
    if item.why_relevant:
        relevance_html = f'<div class="relevance">{escape(item.why_relevant)}</div>'

    return f"""    <li>
      <div class="item-header">
        <span class="rank">{idx}.</span>
        <span class="score {score_class}">{item.score}</span>
        <span class="source-tag {source_class}">{escape(source_label)}</span>
        <span class="item-title"><a href="{url}" target="_blank">{title}</a></span>
      </div>
      <div class="item-meta">{date}</div>
      {meta_html}
      {abstract_html}
      {relevance_html}
    </li>
"""


def _html_errors(report: schema.Report) -> str:
    """Render source errors as HTML."""
    errors = []
    for src in ('openalex', 'semanticscholar', 'pubmed', 'biorxiv', 'medrxiv', 'arxiv', 'huggingface'):
        err = getattr(report, f'{src}_error', None)
        if err:
            errors.append((src, err))
    if not errors:
        return ""
    items = "".join(f"<li><strong>{escape(src)}:</strong> {escape(err)}</li>" for src, err in errors)
    return f'<div class="errors"><h2>Source Errors</h2><ul>{items}</ul></div>'


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

    with open(OUTPUT_DIR / "report.html", 'w') as f:
        f.write(render_html(report))

    with open(OUTPUT_DIR / "context.md", 'w') as f:
        f.write(render_context_snippet(report))


def get_context_path() -> str:
    """Get path to context file."""
    return str(OUTPUT_DIR / "context.md")
