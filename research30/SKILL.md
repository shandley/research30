---
name: research30
description: Research scientific papers from the last 30 days across OpenAlex, Semantic Scholar, PubMed, arXiv, and HuggingFace
argument-hint: "[research topic]"
context: fork
agent: Explore
disable-model-invocation: true
allowed-tools: Bash, Read, Write, AskUserQuestion, WebSearch
---

# research30: Scientific Literature from the Last 30 Days

Search multiple academic databases for recent scientific papers, preprints, models, and datasets related to any topic.

**Sources searched:** OpenAlex (250M+ works, topic-augmented), Semantic Scholar (semantic/embedding search), PubMed (peer-reviewed journals), arXiv (preprints), HuggingFace Hub (models/datasets).

**No API keys required.** Optionally set `S2_API_KEY` for Semantic Scholar and `NCBI_API_KEY` for faster PubMed.

## Step 1: Run the research script

```bash
python3 ~/.claude/skills/research30/scripts/research30.py "$TOPIC" --emit=compact 2>&1
```

Depth options:
- `--quick` - Top 10 results, faster
- (default) - Top 25 results, balanced
- `--deep` - Top 50 results, comprehensive

Source filtering:
- `--sources=all` (default) - All sources
- `--sources=preprints` - bioRxiv + medRxiv + arXiv only
- `--sources=pubmed` - PubMed only
- `--sources=huggingface` - HuggingFace only
- `--sources=arxiv` - arXiv only
- `--sources=openalex` - OpenAlex only
- `--sources=semanticscholar` - Semantic Scholar only

## Step 2: Synthesize the results

The script outputs a **flat ranked list** sorted by score (0-100). Each item includes:
- Score, title, source tag, date, URL
- Metadata (journal, DOI, MeSH terms, citations, downloads)
- **Abstract snippet** (first 200 chars) — use these to understand what each paper is about
- Relevance explanation (why it matched)

**Read every abstract snippet.** They are the most important signal for understanding what's actually being studied. Use them to:

1. **Identify themes** — Group papers by what they study, not just that they matched keywords. Papers with score 70+ that share abstract themes represent active research fronts.

2. **Synthesize findings** — Combine insights across papers. If 3 papers describe similar methods or results, that's a trend. If one paper contradicts others, that's notable.

3. **Assess quality signals:**
   - PubMed articles are peer-reviewed (highest reliability)
   - "PEER REVIEWED" flag on bioRxiv items means the preprint was later published in a journal
   - Higher citation counts indicate established impact
   - Semantic Scholar results may use different terminology for the same concepts (it does semantic matching, not just keyword matching)

4. **Note source diversity** — A finding reported across OpenAlex, PubMed, AND Semantic Scholar is higher confidence than one from a single source.

## Step 3: Present the synthesis

```markdown
## Recent Research: {TOPIC} (Last 30 Days)

**Summary:** [2-3 sentence overview of the research landscape — what are scientists actively working on? Any breakthroughs or shifts?]

**Key Findings:**

1. [Major finding with specific paper reference(s)]
   - What: [what was discovered/demonstrated]
   - Why it matters: [significance]

2. [Second finding...]

3. [Third finding...]

**Active Research Fronts:**
- [Theme 1: brief description with paper references]
- [Theme 2: brief description with paper references]

**Notable Methods/Tools:**
- [New method or tool, if any emerged from the abstracts]

**Gaps & Opportunities:**
- [What's underrepresented or missing from current research]

---
*Based on {N} papers from {sources}. Scores reflect relevance + recency + academic signals.*
```

Key principles for synthesis:
- **Be specific.** Reference actual papers by number from the ranked list (e.g., "Paper #3 demonstrates...").
- **Synthesize, don't summarize.** Don't just list papers — identify patterns, contradictions, and trends across them.
- **Prioritize by score but verify with abstracts.** A score of 85 means high relevance + recency + academic signal, but the abstract tells you *what* is relevant.
- **Flag limitations.** If the results are sparse (few items) or heavily weighted to one source, note this.

## Follow-up Mode

After showing the synthesis:
- Answer follow-up questions from the research findings
- If asked about a specific paper, provide details from the data
- If asked about implementations, highlight HuggingFace models/datasets
- If asked to go deeper, re-run with `--deep` or a more specific topic
- Only run new research if the user asks about a DIFFERENT topic

## Optional Setup

**Semantic Scholar API key** (recommended — enables semantic search):
```bash
mkdir -p ~/.config/research30
echo 'S2_API_KEY=your_key_here' >> ~/.config/research30/.env
chmod 600 ~/.config/research30/.env
```
Get a free key at: https://www.semanticscholar.org/product/api#api-key-form

**NCBI API key** (for faster PubMed, optional):
```bash
echo 'NCBI_API_KEY=your_key_here' >> ~/.config/research30/.env
```
Get a free key at: https://www.ncbi.nlm.nih.gov/account/settings/
