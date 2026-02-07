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

## Step 3: Save the full synthesis to a file

**IMPORTANT:** Always save the full synthesis before showing anything to the user.

1. Create the reports directory:
```bash
mkdir -p ~/.local/share/research30/reports
```

2. Generate a filename from the topic: lowercase, replace spaces/special chars with hyphens, append today's date. Example: `crispr-gene-editing-2026-02-07.md`

3. Use the Write tool to save the **full synthesis** (using the format below) to:
   `~/.local/share/research30/reports/{slug}-{date}.md`

### Full synthesis format (saved to file):

```markdown
# Recent Research: {TOPIC}
*{date range} | Generated {today's date}*

## Summary
[2-3 sentence overview of the research landscape — what are scientists actively working on? Any breakthroughs or shifts?]

## Key Findings

### 1. [Major finding]
[What was discovered/demonstrated. Reference specific papers by title.]
**Why it matters:** [significance]

### 2. [Second finding]
...

### 3. [Third finding]
...

## Active Research Fronts
- **[Theme 1]:** [brief description with paper references]
- **[Theme 2]:** [brief description with paper references]

## Notable Methods & Tools
- [New method or tool, if any emerged from the abstracts]

## Gaps & Opportunities
- [What's underrepresented or missing from current research]

## Top Papers
[List the top 10 papers by score with title, source, date, URL, and a one-line description of what it contributes]

---
*Based on {N} papers from {sources}. Scores reflect relevance + recency + academic signals.*
```

Key principles for synthesis:
- **Be specific.** Reference actual papers by title.
- **Synthesize, don't summarize.** Identify patterns, contradictions, and trends across papers.
- **Prioritize by score but verify with abstracts.** A score of 85 means high relevance + recency + academic signal, but the abstract tells you *what* is relevant.
- **Flag limitations.** If results are sparse or heavily weighted to one source, note this.

## Step 4: Append to the research log

Append a summary entry to `~/.local/share/research30/research-log.md`. This builds a cumulative research journal over time.

Use the Read tool to read the existing log (if it exists), then use the Write tool to write the full content back with the new entry appended at the top (after the header). If the file doesn't exist, create it with a header.

### Log entry format:

```markdown
---
### {date}: {TOPIC}
**Sources:** {source summary} ({N} total)
**Summary:** [1-2 sentence summary]
**Key findings:** [finding 1] | [finding 2] | [finding 3]
**Report:** `~/.local/share/research30/reports/{slug}-{date}.md`
```

## Step 5: Show a brief summary in chat

Do NOT show the full synthesis in chat. Instead, show a **concise summary** (15 lines max):

```markdown
## {TOPIC} — Last 30 Days

[2-3 sentence summary]

**Key findings:**
1. [One-line finding]
2. [One-line finding]
3. [One-line finding]

**{N} papers** from {sources} | Top score: {max}

Full report saved to `~/.local/share/research30/reports/{slug}-{date}.md`
```

## Step 6: Offer follow-up actions

After the summary, ask what the user wants to do next:

> **What next?**
> - "deep dive on [finding]" — expand on a specific finding with paper details
> - "compare methods" — compare approaches across the top papers
> - "top papers" — show the full top 10 list with abstracts
> - "search [related topic]" — run a new search on a related area
> - "open report" — show the full saved report

## Follow-up Mode

When the user requests a follow-up:
- **Deep dive:** Pull details from the raw script output for the relevant papers. Show titles, full abstracts, URLs, and how they connect.
- **Compare methods:** Identify methodological approaches across papers and compare.
- **Top papers:** Show the top 10 from the script output with full abstract snippets.
- **Related search:** Run a new `/research30` search with the new topic.
- **Open report:** Use the Read tool to display the saved report file.
- Only run new research if the user asks about a DIFFERENT topic.

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
