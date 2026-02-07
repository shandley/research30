---
name: research30
description: Research scientific papers from the last 30 days across bioRxiv, medRxiv, arXiv, PubMed, and HuggingFace
argument-hint: "[research topic]"
context: fork
agent: Explore
disable-model-invocation: true
allowed-tools: Bash, Read, Write, AskUserQuestion, WebSearch
---

# research30: Scientific Literature from the Last 30 Days

Search bioRxiv, medRxiv, arXiv, PubMed, and HuggingFace Hub for recent scientific papers, preprints, models, and datasets related to any topic.

**No API keys required.** Optionally set `NCBI_API_KEY` for faster PubMed queries.

## CRITICAL: Parse User Intent

Extract from the user's input:
1. **TOPIC**: The scientific subject to research
2. **SCOPE**: What kind of output they want:
   - **SURVEY** - "what's new in X", "recent advances in X" - broad overview
   - **SPECIFIC** - "papers about X method for Y" - focused search
   - **IMPLEMENTATIONS** - "models for X", "datasets for X" - HuggingFace focus

## Research Execution

**Step 1: Run the research script**
```bash
python3 ~/.claude/skills/research30/scripts/research30.py "$TOPIC" --emit=compact 2>&1
```

Depth options:
- `--quick` - Fewer results, faster
- (default) - Balanced
- `--deep` - Comprehensive search

Source filtering:
- `--sources=all` (default) - All 5 sources
- `--sources=preprints` - bioRxiv + medRxiv + arXiv only
- `--sources=pubmed` - PubMed only
- `--sources=huggingface` - HuggingFace only
- `--sources=arxiv` - arXiv only

**Step 2: Synthesize findings**

After the script returns, analyze the results:

1. **Key papers** - Identify the most important/cited papers
2. **Methodological trends** - What techniques are emerging?
3. **Research gaps** - What's missing or underexplored?
4. **Top authors/groups** - Who is leading this area?
5. **Cross-source patterns** - Papers appearing in multiple sources are high signal

Weight sources by reliability:
- PubMed (peer-reviewed) > bioRxiv/medRxiv (preprints) > arXiv > HuggingFace
- Higher-scored items are more relevant and recent

## Show Summary

Display findings in this format:

```
## Recent Research: {TOPIC}

**Key findings from the last 30 days:**

1. [Major finding/paper with citation]
2. [Emerging method/approach]
3. [Notable trend]

**Top papers:**
- [Title] - [Authors] ([Source], score: X)
  [Brief why this matters]
- ...

**Emerging trends:**
- [Trend 1]
- [Trend 2]

---
Sources: {n} bioRxiv | {n} medRxiv | {n} arXiv | {n} PubMed | {n} HuggingFace
```

## Follow-up Mode

After showing the summary:
- Answer follow-up questions from the research findings
- If asked about a specific paper, provide details from the data
- If asked about implementations, highlight HuggingFace models/datasets
- Only run new research if the user asks about a DIFFERENT topic

## Optional Setup (for faster PubMed)

```bash
mkdir -p ~/.config/research30
echo 'NCBI_API_KEY=your_key_here' > ~/.config/research30/.env
chmod 600 ~/.config/research30/.env
```

Get a free NCBI API key at: https://www.ncbi.nlm.nih.gov/account/settings/
