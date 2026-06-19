#!/usr/bin/env python3
import json
import sys

PLATFORM_TERMS = {"platform", "modular", "multi-sided", "two-sided", "ecosystem", "complementor"}
BIOTECH_TERMS = {"biotech", "biotechnology", "life sciences", "drug discovery", "therapeutic", "biopharma", "pharmaceutical", "diagnostic", "agbiotech", "industrial biotech", "synthetic biology"}

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
    if not has_platform and not has_biotech and not text_long_enough:
        return False
    return True

input_file = "/home/npdrpi1/ClaudeAgents/slr-agent-master/data/02_deduped/corpus.jsonl"
output_file = "/home/npdrpi1/ClaudeAgents/slr-agent-master/data/02_deduped/prefiltered.jsonl"

total_in = 0
total_kept = 0

with open(input_file, 'r', encoding='utf-8') as infile:
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            total_in += 1
            try:
                record = json.loads(line)
                if should_keep(record):
                    total_kept += 1
                    outfile.write(json.dumps(record) + '\n')
            except json.JSONDecodeError:
                pass

drop_rate = (total_in - total_kept) / total_in * 100 if total_in > 0 else 0
print(f"Total in: {total_in}")
print(f"Total kept: {total_kept}")
print(f"Drop rate: {drop_rate:.2f}%")
if drop_rate > 70:
    print("WARNING: Drop rate exceeds 70%")

prisma_file = "/home/npdrpi1/ClaudeAgents/slr-agent-master/output/prisma_counts.json"
with open(prisma_file, 'a', encoding='utf-8') as f:
    f.write(json.dumps({"phase": "after_prefilter", "n": total_kept}) + '\n')
