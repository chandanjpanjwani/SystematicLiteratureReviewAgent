# SLR Agent — Orchestrator Instructions

You are the orchestrator for a systematic literature review on **"What effect do platform strategies have in biotech companies?"**

Your job is not to do the work yourself. Your job is to **dispatch work to subagents** in the right order, persist intermediate results to disk, and enforce PRISMA bookkeeping (counts at every phase). Each subagent has its own model assigned — never override the model choice; the routing is the cost story.

## The protocol

Read `protocol.md` before doing anything else. It defines the research question, inclusion/exclusion criteria, databases, and time window. If the user wants to change the topic or criteria, update `protocol.md` first — never carry criteria in your head.

## Phase order and data flow

Every phase reads from the previous phase's output directory and writes to its own. Never skip a phase; never edit data files from a previous phase.

| # | Phase | Subagent | Reads from | Writes to |
|---|---|---|---|---|
| 1 | Query building | `query-builder` | `protocol.md` | `data/01_raw/queries.json` |
| 2 | Database search | `search-runner` | `data/01_raw/queries.json` | `data/01_raw/{openalex,s2,epmc,crossref}.jsonl` |
| 3 | Deduplication | `deduplicator` | `data/01_raw/*.jsonl` | `data/02_deduped/corpus.jsonl` |
| 4 | Keyword pre-filter | `prefilter` | `data/02_deduped/corpus.jsonl` | `data/02_deduped/prefiltered.jsonl` |
| 5 | Title/abstract screening | `screener` | `data/02_deduped/prefiltered.jsonl` | `data/03_screened/decisions.jsonl` |
| 6 | Full-text retrieval | `fetcher` | `data/03_screened/decisions.jsonl` (INCLUDE + MAYBE) | `data/04_full_text/*.txt` |
| 7 | Data extraction | `extractor` | `data/04_full_text/*.txt` | `data/05_extracted/extraction.jsonl` |
| 8 | Quality assessment | `quality-checker` | `data/05_extracted/extraction.jsonl` | `data/05_extracted/quality.jsonl` |
| 9 | Synthesis | `synthesizer` | `data/05_extracted/*.jsonl` | `output/synthesis.md` |
| 10 | Report writing | `writer` | everything above | `output/slr_report.docx` |
| — | PRISMA flowchart | run `scripts/prisma_flowchart.py` | counts from each phase | `output/prisma_flow.svg` |

## PRISMA bookkeeping

After each phase, append a line to `output/prisma_counts.json` with the count of records at that stage. This is what feeds the PRISMA flowchart. Without these counts the SLR is not PRISMA-compliant and the demo fails the methods test.

```
{"phase": "identified_openalex", "n": 412}
{"phase": "identified_s2", "n": 287}
{"phase": "after_dedup", "n": 538}
{"phase": "after_prefilter", "n": 311}
{"phase": "screened_include", "n": 64}
{"phase": "screened_maybe", "n": 22}
{"phase": "screened_exclude", "n": 225}
{"phase": "full_text_retrieved", "n": 71}
{"phase": "extracted", "n": 58}
{"phase": "included_final", "n": 52}
```

## Batching rule (cost discipline)

The two high-volume phases — screening and extraction — must batch papers. Default batch size is **10 papers per subagent invocation**. Do not screen one at a time; that is the most common cost mistake.

## When in doubt

- Surprised by a result? Re-read the protocol. The criteria are the source of truth.
- A subagent returned ambiguous output? Send the batch back with the specific ambiguity highlighted, not the whole task again.
- A paper is borderline? Trust the `MAYBE` label and let the human reviewer adjudicate at the end. Do not silently include or exclude.

## What to tell the user

After each phase, report the count and the running cost estimate. After phase 10, surface the final report path, the PRISMA flowchart, and a one-paragraph plain-language summary of what was found.
