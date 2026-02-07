# research30

A Claude Code skill that searches the last 30 days of scientific literature across five sources: bioRxiv, medRxiv, arXiv, PubMed, and HuggingFace Hub.

No API keys are required. All sources use free, public APIs.

## What It Does

Given a research topic, research30 queries all five sources in parallel, scores results by relevance and academic signals, removes duplicates across sources, and outputs a ranked report. The entire pipeline runs in seconds using only Python's standard library.

Sources searched:
- **PubMed** -- peer-reviewed journal articles via NCBI E-utilities
- **bioRxiv** -- biology preprints
- **medRxiv** -- medical/clinical preprints
- **arXiv** -- physics, math, CS, and quantitative biology preprints
- **HuggingFace Hub** -- ML models, datasets, and daily papers

## Installation

### As a Claude Code Skill

Copy the `research30/` directory to your Claude Code skills folder:

```bash
cp -r research30 ~/.claude/skills/research30
```

Then use it in Claude Code:

```
/research30 CRISPR gene editing
/research30 large language models
/research30 single-cell RNA sequencing
```

### Standalone

Run the script directly with Python 3.8+:

```bash
cd research30
python3 scripts/research30.py "your topic here"
```

No dependencies to install -- the project uses only the Python standard library.

## Usage

```
python3 scripts/research30.py <topic> [options]
```

### Options

| Flag | Description |
|------|-------------|
| `--emit=MODE` | Output format: `compact` (default), `json`, `md`, `context`, `path` |
| `--sources=MODE` | Filter sources: `all` (default), `preprints`, `pubmed`, `huggingface`, `biorxiv`, `arxiv` |
| `--quick` | Fewer results per source, faster execution |
| `--deep` | More results per source, thorough search |
| `--debug` | Print verbose HTTP logs to stderr |
| `--mock` | Use bundled fixture data instead of live APIs (for testing) |

### Examples

Search all sources for a topic:

```bash
python3 scripts/research30.py "CRISPR gene editing"
```

Search only PubMed:

```bash
python3 scripts/research30.py "Alzheimer's disease biomarkers" --sources=pubmed
```

Get results as JSON:

```bash
python3 scripts/research30.py "protein folding" --emit=json
```

Quick scan of preprint servers:

```bash
python3 scripts/research30.py "single-cell transcriptomics" --sources=preprints --quick
```

## How Scoring Works

Each result is scored 0-100 based on three signals:

**For papers (bioRxiv, medRxiv, arXiv, PubMed):**
- 50% keyword relevance (title match weighted 2x over abstract)
- 25% recency (newer papers score higher)
- 25% academic signal (peer review status, journal, author count)

**For HuggingFace items (models, datasets, papers):**
- 45% keyword relevance
- 25% recency
- 30% academic signal (downloads, likes)

Papers that appear in multiple sources (e.g., a bioRxiv preprint that was later published in a journal indexed by PubMed) are deduplicated. The version from the higher-priority source is kept: PubMed > bioRxiv > medRxiv > arXiv > HuggingFace.

## Optional Configuration

### NCBI API Key

By default, PubMed queries are rate-limited to 3 requests per second. If you register for a free NCBI API key, this increases to 10 per second:

1. Get a key at https://www.ncbi.nlm.nih.gov/account/settings/
2. Save it:

```bash
mkdir -p ~/.config/research30
echo 'NCBI_API_KEY=your_key_here' > ~/.config/research30/.env
chmod 600 ~/.config/research30/.env
```

Or set it as an environment variable:

```bash
export NCBI_API_KEY=your_key_here
```

This is optional. The skill works fine without it.

## Output

Results are written to `~/.local/share/research30/out/`:
- `report.json` -- full structured data
- `report.md` -- formatted markdown report
- `context.md` -- condensed context snippet

Results are cached for 24 hours at `~/.cache/research30/`. Run with `--refresh` or delete the cache directory to force fresh queries.

## Running Tests

```bash
cd research30
python3 -m pytest tests/ -v
```

All tests use bundled fixture data in `fixtures/` and make no network requests.

## Project Structure

```
research30/
  SKILL.md              -- Claude Code skill manifest
  scripts/
    research30.py       -- Main entry point and orchestrator
    lib/
      schema.py         -- Data models (BiorxivItem, ArxivItem, PubmedItem, etc.)
      biorxiv.py        -- bioRxiv and medRxiv API client
      arxiv.py          -- arXiv API client
      pubmed.py         -- PubMed E-utilities client
      huggingface.py    -- HuggingFace Hub API client
      normalize.py      -- Raw data to schema conversion and keyword relevance
      score.py          -- Academic-signal scoring
      dedupe.py         -- DOI-based and title-similarity deduplication
      render.py         -- Output formatting (compact, markdown, JSON)
      cache.py          -- 24-hour result caching
      http.py           -- HTTP client (stdlib only)
      xml_parse.py      -- arXiv Atom and PubMed XML parsers
      dates.py          -- Date utilities
      env.py            -- Configuration loading
      ui.py             -- Terminal progress display
  tests/                -- Unit tests (54 tests)
  fixtures/             -- Mock API responses for testing
```

## License

MIT
