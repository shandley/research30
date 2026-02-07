# research30

A skill for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Anthropic's CLI coding agent) that searches the last 30 days of scientific literature and synthesizes findings. No API keys required.

```
/research30 CRISPR gene editing
/research30 microplastics health effects
/research30 large language model alignment
```

Claude searches 5 academic databases in parallel, scores and deduplicates results, then synthesizes key findings, trends, and gaps from the top 25 papers.

## Quick Start

**Prerequisites:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and Python 3.8+ (no pip packages needed — stdlib only)

**1. Clone the repo:**

```bash
git clone https://github.com/shandley/research30.git
cd research30
```

**2. Install the skill (run from the repo root):**

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/research30" ~/.claude/skills/research30
```

This creates a symlink so the skill stays in sync with the repo. The `$(pwd)` must expand to the repo root (the directory containing `research30/`, `README.md`, etc.).

**3. Use it:**

Start a new Claude Code session (skills are loaded at startup), then:

```
/research30 your topic here
```

This works from any directory — the skill is globally installed.

**Standalone (no Claude Code):** You can also run the script directly from the repo root:

```bash
python3 research30/scripts/research30.py "your topic here"
```

This outputs the raw ranked list. Claude Code adds the synthesis layer on top.

## What It Searches

| Source | What | Coverage |
|--------|------|----------|
| **OpenAlex** | Journals, preprints, conference papers | 250M+ works, topic-augmented full-text search |
| **Semantic Scholar** | Embedding-based semantic search | Conceptual matching beyond keywords (needs free API key) |
| **PubMed** | Peer-reviewed journal articles | TIAB field-tagged queries with MeSH metadata |
| **arXiv** | Physics, math, CS, q-bio preprints | Atom API keyword search |
| **HuggingFace** | ML models, datasets, daily papers | Hub API |

Additional sources available via `--sources=biorxiv` or `--sources=medrxiv` (slower, direct API pagination).

## Usage

```
python3 research30/scripts/research30.py <topic> [options]
```

| Flag | Description |
|------|-------------|
| `--quick` | Faster: fewer API results, shows top 10 |
| `--deep` | Thorough: more API results, shows top 50 |
| `--refresh` | Bypass 24h cache, fetch fresh results |
| `--sources=MODE` | `all` (default), `preprints`, `pubmed`, `huggingface`, `openalex`, `semanticscholar`, `biorxiv`, `medrxiv`, `arxiv` |
| `--emit=MODE` | `compact` (default), `json`, `md`, `context`, `path` |
| `--debug` | Verbose HTTP logs to stderr |
| `--mock` | Use bundled fixtures (for testing) |

### Examples

```bash
# Default: top 25 results from all sources
python3 research30/scripts/research30.py "CRISPR gene editing"

# Quick scan — top 10
python3 research30/scripts/research30.py "protein folding" --quick

# Deep dive — top 50
python3 research30/scripts/research30.py "single-cell transcriptomics" --deep

# PubMed only
python3 research30/scripts/research30.py "Alzheimer's disease biomarkers" --sources=pubmed

# JSON output for programmatic use
python3 research30/scripts/research30.py "protein folding" --emit=json
```

## Optional: API Keys

Both keys are optional. The skill works without them.

**Semantic Scholar** (recommended — adds semantic/embedding search):

```bash
# Get a free key at https://www.semanticscholar.org/product/api#api-key-form
mkdir -p ~/.config/research30
echo 'S2_API_KEY=your_key_here' >> ~/.config/research30/.env
chmod 600 ~/.config/research30/.env
```

**NCBI** (faster PubMed — 10 req/s instead of 3):

```bash
# Get a free key at https://www.ncbi.nlm.nih.gov/account/settings/
echo 'NCBI_API_KEY=your_key_here' >> ~/.config/research30/.env
```

## Output

Default output is a flat ranked list sorted by score (0-100). Each item includes score, title, source, date, URL, metadata, abstract snippet (first 200 chars), and relevance explanation. When used as a Claude Code skill, Claude reads these and synthesizes key findings, research fronts, methods, and gaps.

Full structured data is also written to `~/.local/share/research30/out/`:
- `report.json` — all results (not just top N)
- `report.md` — formatted markdown
- `context.md` — condensed context snippet

Results are cached for 24 hours at `~/.cache/research30/`. Use `--refresh` to bypass.

## How Scoring Works

Each result is scored 0-100:

**Papers** (50% relevance + 25% recency + 25% academic signal):
- Keyword relevance: title match 2x weighted, bigram matching for multi-word queries, position boost for OpenAlex/S2 results
- Recency: newer = higher
- Academic: peer review, citations, journal, author count

**HuggingFace** (45% relevance + 25% recency + 30% engagement):
- Downloads and likes as engagement signal

Cross-source deduplication uses DOI matching + Jaccard title similarity. Priority: PubMed > S2 > OpenAlex > bioRxiv > medRxiv > arXiv > HuggingFace.

## How Search Works

**OpenAlex** discovers relevant topic clusters first (e.g., "virome" maps to topic T11048), then searches within them — combining ML-classified topics with keyword ranking.

**PubMed** uses explicit `[TIAB]` field tags instead of Automatic Term Mapping (which can misfire). Multi-word queries get both exact-phrase and AND-combination: `("CRISPR gene editing"[TIAB] OR (CRISPR[TIAB] AND gene[TIAB] AND editing[TIAB]))`. MeSH terms are extracted as metadata.

**Semantic Scholar** provides embedding-based search — catches papers that use different terminology for the same concept. Post-filtered with a higher relevance threshold (0.3 vs 0.1).

## Development

### Running Tests

```bash
cd research30
python3 -m pytest tests/ -v
```

All tests use bundled fixtures and make no network requests.

### Project Structure

```
research30/
  SKILL.md              -- Claude Code skill manifest
  scripts/
    research30.py       -- Main orchestrator
    lib/
      openalex.py       -- OpenAlex API (topic discovery + works search)
      semanticscholar.py -- Semantic Scholar API (semantic search)
      pubmed.py         -- PubMed E-utilities (TIAB queries, MeSH)
      arxiv.py          -- arXiv Atom API
      huggingface.py    -- HuggingFace Hub API
      biorxiv.py        -- bioRxiv/medRxiv API (parallel pagination)
      schema.py         -- Data models
      normalize.py      -- Schema conversion + keyword relevance
      score.py          -- Academic-signal scoring
      dedupe.py         -- Cross-source deduplication
      render.py         -- Output formatting
      cache.py          -- 24-hour result caching
      http.py           -- HTTP client (stdlib only)
      xml_parse.py      -- XML parsers (arXiv Atom, PubMed)
      dates.py          -- Date utilities
      env.py            -- Configuration loading
      ui.py             -- Terminal progress display
  tests/                -- Unit tests (90 tests)
  fixtures/             -- Mock API responses
```

## License

MIT
