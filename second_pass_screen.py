"""
Second-pass screener for SLR MAYBE records.
Reclassifies MAYBE records using richer abstract-text heuristics.
"""

import json
import re
from pathlib import Path

BASE = Path(r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent")
DECISIONS_FILE = BASE / "data/03_screened/decisions.jsonl"
PREFILTERED_FILE = BASE / "data/02_deduped/prefiltered.jsonl"
PRISMA_FILE = BASE / "output/prisma_counts.json"

# --- Pattern sets ---

TECHNICAL_PLATFORM_PATTERNS = [
    r"sequencing platform",
    r"ngs platform",
    r"pcr platform",
    r"assay platform",
    r"expression platform",
    r"delivery platform",
    r"manufacturing platform",
    r"production platform",
    r"cell culture platform",
    r"screening platform",
    r"high[- ]throughput platform",
    r"omics platform",
    r"imaging platform",
    r"diagnostic platform",
]

STRATEGIC_TERMS = [
    r"business model",
    r"ecosystem",
    r"multi[- ]sided",
    r"two[- ]sided",
    r"network effect",
    r"complementor",
    r"platform governance",
    r"platform competition",
    r"platform strategy",
    r"platform firm",
    r"open innovation",
    r"strategic alliance",
    r"value creation",
    r"competitive advantage",
    r"firm performance",
    r"market platform",
    r"digital platform",
]

INCLUDE_PLATFORM_TERMS = [
    r"platform strateg",
    r"platform business",
    r"platform ecosystem",
    r"platform firm",
    r"platform governance",
    r"platform competition",
    r"multi[- ]sided platform",
    r"two[- ]sided platform",
    r"digital platform",
    r"market platform",
    r"open innovation platform",
    r"technology platform strateg",
    r"network effect",
    r"ecosystem strateg",
    r"innovation platform",
    r"business platform",
]

BIOTECH_CONTEXT_TERMS = [
    r"biotech",
    r"biopharm",
    r"life science",
    r"pharmaceutical firm",
    r"biopharma",
    r"drug compan",
    r"genomic",
    r"biotechnology firm",
    r"biomedical firm",
    r"biomedical compan",
    r"health tech",
    r"medtech",
    r"biotech startup",
    r"biotech compan",
    r"therapeutic compan",
    r"biologics",
]

FIRM_OUTCOME_TERMS = [
    r"firm performance",
    r"valuation",
    r"alliance",
    r"partnership",
    r"licensing",
    r"collaboration",
    r"survival",
    r"innovation output",
    r"ipo",
    r"venture capital",
    r"r&d performance",
    r"competitive advantage",
    r"market share",
    r"revenue",
    r"profitability",
    r"growth",
    r"investment",
    r"spin[- ]off",
    r"joint venture",
    r"acquisition",
    r"merger",
    r"startup performance",
    r"firm-level",
]

CLINICAL_ONLY_TERMS = [
    r"clinical trial",
    r"randomized controlled",
    r"pharmacokinetic",
    r"pharmacodynamic",
    r"in vitro",
    r"in vivo",
    r"cell line",
    r"mouse model",
    r"rat model",
    r"gene expression",
    r"protein structure",
    r"molecular mechanism",
    r"dose[- ]response",
    r"adverse event",
    r"drug efficacy",
    r"drug toxicity",
    r"therapeutic efficacy",
    r"biochemical pathway",
    r"enzyme activity",
    r"receptor binding",
    r"nucleotide sequence",
    r"amino acid",
    r"murine",
]


def matches_any(text, patterns):
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def count_matches(text, patterns):
    return sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))


def classify_abstract(abstract: str):
    """
    Returns (decision, rationale) for a MAYBE record with a non-empty abstract.
    """
    txt = abstract.lower()

    has_technical_platform = matches_any(txt, TECHNICAL_PLATFORM_PATTERNS)
    has_strategic = matches_any(txt, STRATEGIC_TERMS)
    has_include_platform = matches_any(txt, INCLUDE_PLATFORM_TERMS)
    has_biotech = matches_any(txt, BIOTECH_CONTEXT_TERMS)
    has_firm_outcome = matches_any(txt, FIRM_OUTCOME_TERMS)
    has_clinical_only = matches_any(txt, CLINICAL_ONLY_TERMS)

    # Check if the word "platform" appears at all
    has_platform_word = bool(re.search(r'\bplatform\b', txt))

    # EC3: purely technical platform usage
    if has_technical_platform and not has_strategic and not has_include_platform:
        return "EXCLUDE", "EC3: Platform terms are exclusively technical; no strategic content."

    # EC2/EC4: purely clinical/molecular biology content
    if has_clinical_only and not has_platform_word and not has_strategic and not has_biotech:
        return "EXCLUDE", "EC2: Abstract is purely clinical/pharmacological with no platform or firm-strategy content."

    # Additional EC2: drug/clinical outcomes only, no firm strategy
    if has_clinical_only and not has_include_platform and not has_strategic and not has_firm_outcome:
        # Check for ANY business/strategy language
        biz_terms = [r"strateg", r"business", r"firm", r"compan", r"market", r"industry",
                     r"innovat", r"manag", r"governance", r"ecosystem"]
        has_any_biz = matches_any(txt, biz_terms)
        if not has_any_biz:
            return "EXCLUDE", "EC2: Purely clinical/molecular content with no firm-strategy or business-model language."

    # INCLUDE: platform strategy + biotech + firm outcome
    if has_include_platform and has_biotech and has_firm_outcome:
        return "INCLUDE", "IC3+: Platform strategy term + biotech context + firm-level outcome."

    # INCLUDE: strong strategic content + biotech context
    if has_strategic and has_biotech and has_firm_outcome:
        return "INCLUDE", "IC3+: Strategic platform term + biotech context + firm-level outcome."

    # Borderline INCLUDE: platform strategy clearly present + biotech
    if has_include_platform and has_biotech:
        return "INCLUDE", "IC3: Platform strategy term + biotech context (moderate confidence)."

    return "MAYBE", "Abstract ambiguous or insufficient signal for reclassification."


def main():
    # Load all decisions
    decisions = {}
    with open(DECISIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                decisions[rec["id"]] = rec

    maybe_ids = {rid for rid, rec in decisions.items() if rec["decision"] == "MAYBE"}
    print(f"Total MAYBE records: {len(maybe_ids)}")

    # Load full records for MAYBE IDs
    full_records = {}
    with open(PREFILTERED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                if rec["id"] in maybe_ids:
                    full_records[rec["id"]] = rec

    print(f"Full records found for MAYBE IDs: {len(full_records)}")

    # Reclassify
    reclassified_include = 0
    reclassified_exclude = 0
    remain_maybe = 0
    skipped_no_abstract = 0

    for rid in maybe_ids:
        full_rec = full_records.get(rid)
        abstract = (full_rec.get("abstract") or "") if full_rec else ""

        if len(abstract) <= 50:
            skipped_no_abstract += 1
            remain_maybe += 1
            continue

        new_decision, rationale = classify_abstract(abstract)

        if new_decision == "INCLUDE":
            reclassified_include += 1
            decisions[rid]["decision"] = "INCLUDE"
            decisions[rid]["rationale"] = rationale
            decisions[rid]["confidence"] = 0.75
            decisions[rid]["second_pass"] = True
        elif new_decision == "EXCLUDE":
            reclassified_exclude += 1
            decisions[rid]["decision"] = "EXCLUDE"
            decisions[rid]["rationale"] = rationale
            decisions[rid]["confidence"] = 0.75
            decisions[rid]["second_pass"] = True
        else:
            remain_maybe += 1

    print(f"\nReclassified to INCLUDE: {reclassified_include}")
    print(f"Reclassified to EXCLUDE: {reclassified_exclude}")
    print(f"Remain MAYBE: {remain_maybe}")
    print(f"  (of which {skipped_no_abstract} had null/short abstracts)")

    # Compute final totals
    total_include = sum(1 for r in decisions.values() if r["decision"] == "INCLUDE")
    total_exclude = sum(1 for r in decisions.values() if r["decision"] == "EXCLUDE")
    total_maybe = sum(1 for r in decisions.values() if r["decision"] == "MAYBE")

    print(f"\nFinal totals:")
    print(f"  INCLUDE: {total_include}")
    print(f"  EXCLUDE: {total_exclude}")
    print(f"  MAYBE:   {total_maybe}")
    print(f"  Total:   {total_include + total_exclude + total_maybe}")

    # Rewrite decisions.jsonl
    with open(DECISIONS_FILE, "w", encoding="utf-8") as f:
        for rec in decisions.values():
            f.write(json.dumps(rec) + "\n")
    print(f"\nRewritten decisions.jsonl ({len(decisions)} records).")

    # Append to prisma_counts.json
    with open(PRISMA_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"phase": "screened_include_final", "n": total_include}) + "\n")
        f.write(json.dumps({"phase": "screened_maybe_final", "n": total_maybe}) + "\n")
        f.write(json.dumps({"phase": "screened_exclude_final", "n": total_exclude}) + "\n")
    print("Appended final counts to prisma_counts.json.")


if __name__ == "__main__":
    main()
