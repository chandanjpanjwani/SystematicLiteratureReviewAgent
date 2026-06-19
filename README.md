# SLR Agent — Systematic Literature Review with Claude Code

A Claude Code project that performs a PRISMA-compliant systematic literature review on **"What effect do platform strategies have in biotech companies?"**, with automatic model routing across Haiku, Sonnet, and Opus.

Built as a course prototype for an MSc in New Product Development.

## What it does

Runs the four PRISMA phases (Identification → Screening → Eligibility → Inclusion) and produces:
- `output/slr_report.docx` — the SLR report
- `output/prisma_flow.svg` — the PRISMA 2020 flow diagram
- `output/synthesis.md` — the analytical core
- `data/05_extracted/extraction.jsonl` — the extraction table

## How the model routing works

Each subagent declares its own model in YAML frontmatter. The orchestrator never picks the model — the routing is encoded in the agent definitions, so cost behavior is deterministic.

| Tier | Used for |
|---|---|
| **Haiku** | API calls, deduplication, retrieval, keyword pre-filter |
| **Sonnet** | Query building, title/abstract screening, data extraction, quality scoring |
| **Opus** | Cross-corpus synthesis, final report writing |

The high-volume work (screening hundreds of abstracts, extracting from dozens of papers) runs on Haiku and Sonnet. Opus is reserved for synthesis and writing, which happen once over the included corpus. That is where the cost asymmetry pays off.

## Setup

Requirements: Python 3.10+, Node 18+, and Claude Code installed.

```bash
cd slr-agent
# Python deps are stdlib only — no pip install needed
claude
```

Inside the Claude Code session, the orchestrator reads `CLAUDE.md` and `protocol.md` automatically. To start the review:

```
Run the SLR workflow from phase 1.
```

The orchestrator will dispatch subagents in order, persist data between phases, and report counts after each phase.

## File layout

```
.
├── CLAUDE.md                    # Orchestrator instructions
├── protocol.md                  # Research question, criteria, search strategy
├── .claude/
│   ├── settings.json            # Tool permissions
│   └── agents/                  # 10 subagent definitions, one .md each
├── scripts/                     # Python clients for the 4 databases + dedupe + PRISMA SVG
├── data/                        # Intermediate outputs, one folder per phase
└── output/                      # Final deliverables
```

## Customizing for a different topic

Change `protocol.md`:
- Update the research question and sub-questions
- Update PICOC
- Update inclusion/exclusion criteria
- Update the base search query

Then re-run from phase 1. Everything else adapts to the protocol — agents are topic-agnostic.

## Cost discipline beyond model routing

The model routing is the headline, but four additional moves matter:

1. **Batching.** Screening processes 10 papers per call; extraction processes 5. Single-paper calls are the most common cost mistake.
2. **Prompt caching.** The protocol gets sent on every screening call — Claude Code applies prompt caching automatically when you keep the same prefix.
3. **Haiku pre-filter.** Before Sonnet sees an abstract, a Haiku keyword pass drops obviously irrelevant records (no platform terms AND no biotech terms).
4. **Persistence between phases.** Each phase writes to disk. A rerun doesn't redo the expensive parts unless you delete the intermediate files.

For a hard budget cap, set `CLAUDE_CODE_SUBAGENT_MODEL=haiku` to force every subagent to Haiku — useful for a "budget mode" demo where you want to show the workflow shape without the Opus call.

## What's not in this prototype

- **Dual independent screening.** A real SLR uses two human screeners with kappa reliability. This prototype is single-screener; the writer agent notes this as a limitation.
- **Grey literature.** No conference proceedings, theses, or reports beyond what OpenAlex/CrossRef index.
- **Forward/backward citation chasing.** A real SLR also screens references of included papers and papers that cite them. Easy extension: add a `citation-chaser` subagent that queries OpenAlex's referenced_works and cited_by fields.
- **Risk-of-bias for quantitative studies.** MMAT is the chosen tool; for clinical RCTs you'd use Cochrane RoB 2.

These are good extensions for the next iteration of the prototype — and worth mentioning in the startup pitch as "v2 features."

## Pitch framing for the course

The defensible claim is *cost asymmetry through task-appropriate routing*. SLRs cost senior-researcher time at the highest tier; most of that time is spent on the lowest-judgment tasks. The agent moves the high-volume / low-judgment work to cheap models and reserves expensive reasoning for synthesis. The PRISMA flowchart and the auditable per-phase data files are the artifacts that signal "real research method," not just "chatbot output."
