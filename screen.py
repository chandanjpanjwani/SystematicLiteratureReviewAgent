"""
Heuristic screener for SLR: platform strategies in biotech.
Reads data/02_deduped/prefiltered.jsonl
Writes data/03_screened/decisions.jsonl
Appends counts to output/prisma_counts.json
"""

import json
import os
import re

# ── paths ──────────────────────────────────────────────────────────────────
BASE = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent"
INPUT  = os.path.join(BASE, "data", "02_deduped", "prefiltered.jsonl")
OUT_DIR = os.path.join(BASE, "data", "03_screened")
OUTPUT = os.path.join(OUT_DIR, "decisions.jsonl")
PRISMA = os.path.join(BASE, "output", "prisma_counts.json")

os.makedirs(OUT_DIR, exist_ok=True)

# ── term lists ──────────────────────────────────────────────────────────────
STRATEGIC_TERMS = [
    r"\bbusiness model\b",
    r"\becosystem\b",
    r"\bmulti.sided\b",
    r"\btwo.sided\b",
    r"\bplatform strategy\b",
    r"\bplatform governance\b",
    r"\bplatform competition\b",
    r"\bcomplementor\b",
    r"\bvalue creation\b",
    r"\bfirm performance\b",
    r"\bcompetitive advantage\b",
    r"\bstrategic alliance\b",
    r"\bopen innovation\b",
    r"\bpartnership\b",
    r"\bplatform leader\b",
    r"\bnetwork effect\b",
    r"\bplatform owner\b",
    r"\bdigital platform\b",
    r"\bplatform.based\b",
    r"\bplatform firm\b",
    r"\bplatform market\b",
    r"\bplatform model\b",
]

BIOTECH_TERMS = [
    r"\bbiotech\b",
    r"\bbiotechnology\b",
    r"\bbiopharma\b",
    r"\bbiopharmaceutical\b",
    r"\blife sciences?\b",
    r"\bstartup\b",
    r"\bstart.up\b",
    r"\bventure\b",
    r"\btherapeutics?\b",
    r"\bgenomic\b",
    r"\bgenomic[s]?\b",
    r"\bprecision medicine\b",
    r"\bmedtech\b",
    r"\bbio.based\b",
]

OUTCOME_TERMS = [
    r"\bperformance\b",
    r"\bgrowth\b",
    r"\binnovation\b",
    r"\bvalue\b",
    r"\bcompetition\b",
    r"\bstrateg",
    r"\balliance\b",
    r"\bpartnership\b",
    r"\bmarket\b",
    r"\bfirm\b",
    r"\bsuccess\b",
    r"\bcommerciali[sz]",
    r"\beco.system\b",
    r"\bventure\b",
]

# Technical-only platform patterns (EC3)
TECH_PLATFORM_PATTERNS = [
    r"\bsequencing platform\b",
    r"\bpcr platform\b",
    r"\bassay platform\b",
    r"\bcell platform\b",
    r"\bexpression platform\b",
    r"\bdelivery platform\b",
    r"\bscreening platform\b",
    r"\bimaging platform\b",
    r"\bdiagnostic platform\b",
    r"\bdetection platform\b",
    r"\banalytical platform\b",
    r"\bngs platform\b",
    r"\bomics platform\b",
    r"\btechnology platform\b",  # can be tech-only
    r"\bresearch platform\b",
]

# EC4: pharma-only signals
PHARMA_ONLY_TERMS = [r"\bpharmaceutical\b", r"\bpharma\b"]
BIOTECH_INCLUSIVE = [
    r"\bbiotech\b", r"\bbiotechnology\b", r"\bbiopharma\b",
    r"\bbiopharmaceutical\b", r"\blife sciences?\b", r"\bstartup\b",
    r"\bstart.up\b", r"\bventure\b",
]

PLATFORM_TERM = re.compile(r"\bplatform\b", re.I)


def match_any(text, patterns):
    for p in patterns:
        if re.search(p, text, re.I):
            return True
    return False


def count_matches(text, patterns):
    return sum(1 for p in patterns if re.search(p, text, re.I))


def screen(record):
    title = record.get("title") or ""
    abstract = record.get("abstract") or ""
    combined = (title + " " + abstract).lower()

    has_platform = bool(PLATFORM_TERM.search(combined))

    criteria_failed = []
    decision = None
    rationale = ""
    confidence = 0.5

    # ── EC4: pharma-only ───────────────────────────────────────────────────
    has_pharma = match_any(combined, PHARMA_ONLY_TERMS)
    has_biotech = match_any(combined, BIOTECH_INCLUSIVE)
    if has_pharma and not has_biotech:
        criteria_failed.append("EC4")
        decision = "EXCLUDE"
        rationale = "Pharma-only context; no biotech/life-sciences terms detected."
        confidence = 0.85
        return decision, rationale, confidence, criteria_failed

    # ── EC3: platform used only in technical/lab sense ─────────────────────
    if has_platform:
        has_tech_platform = match_any(combined, TECH_PLATFORM_PATTERNS)
        has_strategic = match_any(combined, STRATEGIC_TERMS)

        if has_tech_platform and not has_strategic:
            criteria_failed.append("EC3")
            decision = "EXCLUDE"
            rationale = "Platform used in technical/lab sense only; no strategic terms found."
            confidence = 0.80
            return decision, rationale, confidence, criteria_failed

    # ── INCLUDE: strong signal ─────────────────────────────────────────────
    if has_platform:
        n_strategic = count_matches(combined, STRATEGIC_TERMS)
        n_biotech   = count_matches(combined, BIOTECH_TERMS)
        n_outcome   = count_matches(combined, OUTCOME_TERMS)

        if n_strategic >= 1 and n_biotech >= 1 and n_outcome >= 2:
            decision = "INCLUDE"
            rationale = "Platform-strategy term + biotech context + outcome terms co-occur."
            confidence = min(0.7 + 0.05 * (n_strategic + n_biotech), 0.97)
            return decision, rationale, confidence, criteria_failed

        # Weaker signal → MAYBE
        if n_strategic >= 1 or n_biotech >= 1:
            decision = "MAYBE"
            rationale = "Some platform-strategy or biotech terms present; abstract ambiguous."
            confidence = 0.55
            return decision, rationale, confidence, criteria_failed

    # ── Default: MAYBE (passed prefilter, unclear here) ───────────────────
    decision = "MAYBE"
    rationale = "No clear platform-strategy signal; needs manual review."
    confidence = 0.50
    return decision, rationale, confidence, criteria_failed


# ── Main ───────────────────────────────────────────────────────────────────
counts = {"INCLUDE": 0, "MAYBE": 0, "EXCLUDE": 0}

with open(INPUT, encoding="utf-8") as fin, \
     open(OUTPUT, "w", encoding="utf-8") as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        decision, rationale, confidence, criteria_failed = screen(record)
        counts[decision] += 1
        out = {
            "id": record.get("id", ""),
            "doi": record.get("doi", ""),
            "title": record.get("title", ""),
            "decision": decision,
            "rationale": rationale,
            "confidence": round(confidence, 3),
            "criteria_failed": criteria_failed,
        }
        fout.write(json.dumps(out) + "\n")

print(f"INCLUDE: {counts['INCLUDE']}")
print(f"MAYBE:   {counts['MAYBE']}")
print(f"EXCLUDE: {counts['EXCLUDE']}")
print(f"Total:   {sum(counts.values())}")

# ── Append to prisma_counts.json ───────────────────────────────────────────
with open(PRISMA, "a", encoding="utf-8") as pf:
    pf.write(json.dumps({"phase": "screened_include", "n": counts["INCLUDE"]}) + "\n")
    pf.write(json.dumps({"phase": "screened_maybe",   "n": counts["MAYBE"]})   + "\n")
    pf.write(json.dumps({"phase": "screened_exclude", "n": counts["EXCLUDE"]}) + "\n")

print("Done. prisma_counts.json updated.")
