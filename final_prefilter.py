#!/usr/bin/env python3
"""
Keyword pre-filter for biotech platform SLR.
Drop only if ALL are true: no platform term, no biotech term, short text (<100 chars combined).
"""
import json
import os

os.chdir('/home/npdrpi1/ClaudeAgents/slr-agent-master')

PLATFORM_TERMS = {"platform", "modular", "multi-sided", "two-sided", "ecosystem", "complementor"}
BIOTECH_TERMS = {
    "biotech", "biotechnology", "life sciences", "drug discovery", "therapeutic",
    "biopharma", "pharmaceutical", "diagnostic", "agbiotech", "industrial biotech",
    "synthetic biology"
}

def has_keyword(text, keywords):
    if text is None:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)

def should_keep(record):
    title = record.get("title", "")
    abstract = record.get("abstract", "")

    has_platform = has_keyword(title, PLATFORM_TERMS) or has_keyword(abstract, PLATFORM_TERMS)
    has_biotech = has_keyword(title, BIOTECH_TERMS) or has_keyword(abstract, BIOTECH_TERMS)
    combined_text = (title or "") + (abstract or "")
    text_long_enough = len(combined_text) >= 100

    # DROP: no platform AND no biotech AND short text
    if not has_platform and not has_biotech and not text_long_enough:
        return False
    return True

total_in = 0
total_kept = 0

with open("data/02_deduped/corpus.jsonl", 'r', encoding='utf-8') as infile:
    with open("data/02_deduped/prefiltered.jsonl", 'w', encoding='utf-8') as outfile:
        for line in infile:
            total_in += 1
            try:
                record = json.loads(line)
                if should_keep(record):
                    total_kept += 1
                    outfile.write(json.dumps(record) + '\n')
            except json.JSONDecodeError:
                pass

drop_rate = (total_in - total_kept) / total_in * 100 if total_in > 0 else 0.0

print("="*60)
print("PREFILTER COMPLETE")
print("="*60)
print(f"Total in:  {total_in:,}")
print(f"Total out: {total_kept:,}")
print(f"Dropped:   {total_in - total_kept:,}")
print(f"Drop rate: {drop_rate:.2f}%")
print("="*60)

if drop_rate > 70:
    print("WARNING: Drop rate exceeds 70%")

with open("output/prisma_counts.json", 'a', encoding='utf-8') as f:
    f.write(json.dumps({"phase": "after_prefilter", "n": total_kept}) + '\n')
