#!/usr/bin/env python3
"""Apply prefilter to corpus.jsonl"""
import json
import os

os.chdir('/home/npdrpi1/ClaudeAgents/slr-agent-master')

PLATFORM = {"platform", "modular", "multi-sided", "two-sided", "ecosystem", "complementor"}
BIOTECH = {"biotech", "biotechnology", "life sciences", "drug discovery", "therapeutic", "biopharma", "pharmaceutical", "diagnostic", "agbiotech", "industrial biotech", "synthetic biology"}

total_in, total_out = 0, 0

with open("data/02_deduped/corpus.jsonl", 'r') as inp, open("data/02_deduped/prefiltered.jsonl", 'w') as out:
    for line in inp:
        total_in += 1
        try:
            r = json.loads(line)
            t, a = (r.get("title") or "").lower(), (r.get("abstract") or "").lower()
            if any(kw in t or kw in a for kw in PLATFORM) or any(kw in t or kw in a for kw in BIOTECH) or len((r.get("title") or "") + (r.get("abstract") or "")) >= 100:
                total_out += 1
                out.write(json.dumps(r) + '\n')
        except:
            pass

drop = (total_in - total_out) / total_in * 100 if total_in else 0

with open("output/prisma_counts.json", 'a') as f:
    json.dump({"phase": "after_prefilter", "n": total_out}, f)
    f.write('\n')

print(f"IN: {total_in} | OUT: {total_out} | DROP: {drop:.2f}%")
