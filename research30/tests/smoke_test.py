#!/usr/bin/env python3
"""Live smoke test for research30.

Unlike the unit tests (offline, fixture-backed), this makes real network
calls to every source and checks that each one still returns recent results.
It exists to catch upstream API drift: a source whose schema or endpoint
changed will come back empty or error, and this run turns red before a user
hits it.

Each source is driven through the real CLI with --refresh (so a cached good
result cannot mask a live breakage) and its own query chosen to be reliably
populated within a 30-day window. A source is:

    OK     results >= --min (default 1), no error
    EMPTY  no error but zero results  -> likely silent breakage
    ERROR  a hard error (404, parse failure, schema mismatch)
    WARN   a transient error (rate limit, 5xx, timeout) after retries

Exit code is 0 unless a source is EMPTY or ERROR. A WARN does not fail the
run: the keyless Semantic Scholar path is rate-limited (HTTP 429) often
enough that treating it as breakage would cry wolf. Transient conditions
say nothing about whether an API's schema drifted, which is what this
test exists to catch.

Usage:
    python3 tests/smoke_test.py                       # all sources
    python3 tests/smoke_test.py --sources=pubmed,arxiv
    python3 tests/smoke_test.py --json                # machine-readable
    python3 tests/smoke_test.py --min=3 --timeout=120
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "research30.py"

# Errors that reflect load, not breakage. Matched as substrings of the
# reported error. These become WARN, not FAIL.
TRANSIENT_MARKERS = ("429", "500", "502", "503", "504", "timeout", "temporarily")

# Backoff (seconds) between retries when the prior attempt was transient.
BACKOFF = (3, 8)

# One query per source, each picked to reliably return recent hits.
# Bio sources use a high-volume clinical term; arXiv/HF use ML terms.
SOURCE_QUERIES = {
    "openalex": "cancer",
    "semanticscholar": "cancer",
    "pubmed": "cancer",
    "arxiv": "neural network",
    "huggingface": "language model",
}


def is_transient(error: str) -> bool:
    """True if the error reflects load/rate-limiting rather than breakage."""
    low = (error or "").lower()
    return any(m in low for m in TRANSIENT_MARKERS)


def run_source(source: str, query: str, timeout: int, retries: int = 2) -> dict:
    """Run one source live and return {status, count, error}.

    Retries with backoff while the failure looks transient; a hard error
    (non-transient) is returned immediately without burning retries.
    """
    last = {"status": "ERROR", "count": 0, "error": "no attempt"}
    for attempt in range(retries + 1):
        try:
            proc = subprocess.run(
                [
                    sys.executable, str(SCRIPT), query,
                    f"--sources={source}", "--quick", "--refresh", "--emit=json",
                ],
                capture_output=True, text=True, timeout=timeout,
            )
            if proc.returncode != 0:
                tail = (proc.stderr or "").strip().splitlines()[-1:] or ["nonzero exit"]
                last = {"status": "ERROR", "count": 0, "error": tail[0]}
            else:
                try:
                    data = json.loads(proc.stdout)
                    err = data.get(f"{source}_error")
                    count = len(data.get(source, []) or [])
                    if err:
                        last = {"status": "ERROR", "count": count, "error": err}
                    else:
                        return {"status": "OK", "count": count, "error": None}
                except json.JSONDecodeError:
                    last = {"status": "ERROR", "count": 0, "error": "unparseable JSON output"}
        except subprocess.TimeoutExpired:
            last = {"status": "ERROR", "count": 0, "error": f"timeout after {timeout}s"}

        # Only a transient failure is worth retrying; hard errors won't self-heal.
        if not is_transient(last["error"]) or attempt == retries:
            break
        time.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
    return last


def main() -> int:
    parser = argparse.ArgumentParser(description="Live smoke test for research30 sources.")
    parser.add_argument("--sources", default="all",
                        help="Comma-separated sources, or 'all' (default).")
    parser.add_argument("--min", type=int, default=1,
                        help="Minimum results for a source to count as OK (default 1).")
    parser.add_argument("--timeout", type=int, default=90,
                        help="Per-source timeout in seconds (default 90).")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON summary.")
    args = parser.parse_args()

    if args.sources == "all":
        sources = list(SOURCE_QUERIES)
    else:
        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
        unknown = [s for s in sources if s not in SOURCE_QUERIES]
        if unknown:
            print(f"Unknown source(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"Known: {', '.join(SOURCE_QUERIES)}", file=sys.stderr)
            return 2

    results = {}
    for source in sources:
        r = run_source(source, SOURCE_QUERIES[source], args.timeout)
        if r["status"] == "OK" and r["count"] < args.min:
            r["status"] = "EMPTY"
            r["error"] = f"{r['count']} results (< min {args.min})"
        elif r["status"] == "ERROR" and is_transient(r["error"]):
            r["status"] = "WARN"
        results[source] = r

    # Only EMPTY/ERROR fail the run; WARN (transient) does not.
    failures = [s for s, r in results.items() if r["status"] in ("EMPTY", "ERROR")]
    warns = [s for s, r in results.items() if r["status"] == "WARN"]

    if args.json:
        print(json.dumps({"results": results, "failures": failures, "warns": warns}, indent=2))
    else:
        print(f"research30 live smoke test  ({len(sources)} sources)\n")
        for source in sources:
            r = results[source]
            mark = {"OK": "PASS", "EMPTY": "FAIL", "ERROR": "FAIL", "WARN": "WARN"}[r["status"]]
            detail = f"{r['count']} results" if r["status"] == "OK" else (r["error"] or "")
            print(f"  [{mark}] {source:<16} {detail}")
        print()
        if failures:
            print(f"FAILED: {', '.join(failures)} — possible API drift, investigate.")
        elif warns:
            print(f"OK, with transient warnings: {', '.join(warns)} (rate limit / server load).")
        else:
            print("All sources returned recent results.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
