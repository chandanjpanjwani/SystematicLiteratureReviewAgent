#!/usr/bin/env python3
"""
Complete prefilter implementation - runs inline.
"""
import json
import os
import sys

# Change to working directory
os.chdir('/home/npdrpi1/ClaudeAgents/slr-agent-master')

# Keywords
PLATFORM = {"platform", "modular", "multi-sided", "two-sided", "ecosystem", "complementor"}
BIOTECH = {"biotech", "biotechnology", "life sciences", "drug discovery", "therapeutic", "biopharma", "pharmaceutical", "diagnostic", "agbiotech", "industrial biotech", "synthetic biology"}

def check_keep(record):
    """Apply prefilter logic"""
    title = record.get("title") or ""
    abstract = record.get("abstract") or ""

    # Check keywords
    has_platform = any(kw in title.lower() or kw in abstract.lower() for kw in PLATFORM)
    has_biotech = any(kw in title.lower() or kw in abstract.lower() for kw in BIOTECH)

    # Check text length
    combined_len = len(title + abstract)

    # DROP only if: NO platform AND NO biotech AND text < 100 chars
    # Otherwise KEEP
    if not has_platform and not has_biotech and combined_len < 100:
        return False  # DROP
    return True  # KEEP

# Process corpus
total_in = 0
total_kept = 0

print("Processing corpus...")
with open("data/02_deduped/corpus.jsonl", 'r', encoding='utf-8') as infile:
    with open("data/02_deduped/prefiltered.jsonl", 'w', encoding='utf-8') as outfile:
        for line_num, line in enumerate(infile, 1):
            total_in += 1
            try:
                record = json.loads(line)
                if check_keep(record):
                    total_kept += 1
                    outfile.write(json.dumps(record) + '\n')

                if line_num % 1000 == 0:
                    print(f"  Processed {line_num} records...")
            except json.JSONDecodeError as e:
                print(f"JSON error at line {line_num}: {e}", file=sys.stderr)
                continue

# Calculate metrics
dropped = total_in - total_kept
drop_rate = (dropped / total_in * 100) if total_in > 0 else 0.0

# Report
print("\n" + "="*70)
print("PREFILTER RESULTS")
print("="*70)
print(f"Total records in:       {total_in:>6,}")
print(f"Total records kept:     {total_kept:>6,}")
print(f"Total records dropped:  {dropped:>6,}")
print(f"Drop rate:              {drop_rate:>6.2f}%")
print("="*70)

if drop_rate > 70:
    print("\nWARNING: Drop rate exceeds 70%!")
    print("The protocol query may be too broad.")

# Update PRISMA counts
prisma_file = "output/prisma_counts.json"
print(f"\nAppending PRISMA count to {prisma_file}...")
try:
    with open(prisma_file, 'a', encoding='utf-8') as f:
        json.dump({"phase": "after_prefilter", "n": total_kept}, f)
        f.write('\n')
    print(f"Successfully wrote: {{'phase': 'after_prefilter', 'n': {total_kept}}}")
except IOError as e:
    print(f"ERROR writing PRISMA file: {e}", file=sys.stderr)
    sys.exit(1)

print("\nPrefilter complete!")
