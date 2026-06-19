# SLR Protocol

## Research question

**What effect do platform strategies have in biotech companies?**

Sub-questions:
1. What types of platform strategies are observed in biotech firms (technology platforms, multi-sided platforms, modular platforms, R&D platforms)?
2. What firm-level outcomes (innovation output, valuation, partnership formation, time-to-market, survival) are associated with platform strategies?
3. Under what conditions (firm size, therapeutic area, financing stage, ecosystem maturity) do platform strategies create or destroy value?
4. What boundary conditions and trade-offs are documented?

## PICOC framing

- **Population:** Biotechnology firms (incl. therapeutics, diagnostics, agbiotech, industrial biotech). Exclude pure pharma incumbents unless analyzed as a comparison group.
- **Intervention:** Adoption or use of a platform strategy (technology platform, multi-sided platform, modular product platform, R&D platform).
- **Comparison:** Non-platform / pipeline / single-asset strategies, or pre/post adoption.
- **Outcome:** Innovation output, financial performance, valuation, partnership/alliance formation, survival, time-to-market, ecosystem dynamics.
- **Context:** Any geography; commercial biotech firms (publicly or privately held).

## Inclusion criteria

A paper is INCLUDED if **all** of the following hold:
- Peer-reviewed journal article, conference paper, or established working paper (e.g., NBER, SSRN with citations)
- Empirical (qualitative, quantitative, mixed) OR a substantive conceptual/theory paper
- Explicitly addresses platform strategy AND a biotech / life sciences context
- Published 2005 or later
- English language
- Full text obtainable

## Exclusion criteria

EXCLUDE if any of:
- Editorial, book review, news item, blog post
- Platform strategy discussed only as background; biotech case is only an illustrative example
- "Platform" used purely in the technical/laboratory sense (e.g., "PCR platform") without strategic content
- Pharma-only with no biotech firms in the sample
- Pre-2005
- Non-English
- Full text inaccessible after two retrieval attempts

## Borderline guidance

Mark **MAYBE** (rather than EXCLUDE) if:
- The abstract is ambiguous about strategic content
- The biotech focus is partial (e.g., mixed sample including biotech firms)
- Methodology is unclear from the abstract

MAYBE items go to a second-pass Opus screen rather than being silently dropped.

## Databases

| Database | Coverage | Role |
|---|---|---|
| OpenAlex | General scholarly | Primary, broadest recall |
| Semantic Scholar | General scholarly + TLDRs | Cross-validation + abstract summaries |
| EuropePMC | Biomedical + OA full text | Biotech depth + retrieval |
| CrossRef | Metadata | Reconciliation, DOI canonicalization |

## Search strategy

Base query (English, free-text + boolean, will be translated per database in `query-builder`):

```
( "platform strateg*" OR "platform business model" OR "platform ecosystem" OR "multi platform" OR "platform architecture" OR "innovation platform" OR "technology platform" OR "digital platform" OR "platform-based" OR "platform competition" OR "platform governance" OR "knowledge platform" OR "modular platform" )
AND
( "biotechnology" OR "biotech" OR "biopharmaceutical" OR "biopharma" OR "life sciences" OR "biotech firm*" OR "biotech startup*" OR "biotech compan*" )
AND
( "innovation performance" OR "competitive advantage" OR "value creation" OR "open innovation" OR "firm performance" OR "strategic alliance*" OR "drug development" OR "collaboration" OR "scalabilit*" )
```

Date filter: 2005-01-01 to today.

## Data to extract per paper

- Bibliographic: authors, year, journal, DOI
- Theoretical lens (RBV, dynamic capabilities, platform theory, ecosystem, etc.)
- Method (case study, panel regression, event study, conceptual, etc.)
- Sample (N firms, geography, time window)
- Definition of "platform" used by the authors
- Type of platform strategy studied
- Outcomes measured
- Direction and magnitude of effect (positive/negative/conditional/null)
- Stated boundary conditions
- Identified research gaps

## Quality assessment

Apply MMAT (Mixed Methods Appraisal Tool) 2018, scoring 0–5 per paper. Quality scores are reported alongside findings; they do not gate inclusion at this stage (transparency over restriction).

## Synthesis approach

Thematic synthesis (Thomas & Harden, 2008): line-by-line coding of findings sections → descriptive themes → analytical themes mapped back to the sub-questions.

## Reporting

PRISMA 2020 statement. Flowchart auto-generated from `output/prisma_counts.json`. Final report in `output/slr_report.docx` with the standard sections: background, methods, results (descriptive + thematic), discussion, gaps, limitations, references.

## Version

v0.1 — initial protocol. Update version on any criteria change and log the change in a `protocol_changelog.md` (PRISMA requires transparency about post-hoc protocol amendments).
