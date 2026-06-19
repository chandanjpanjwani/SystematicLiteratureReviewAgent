#!/usr/bin/env python3
"""
Keyword pre-filter for biotech and platform SLR.
"""
import json
import os

# Ensure working directory
os.chdir('/home/npdrpi1/ClaudeAgents/slr-agent-master')

PLATFORM_TERMS = {"platform", "modular", "multi-sided", "two-sided", "ecosystem", "complementor"}
BIOTECH_TERMS = {
    "biotech", "biotechnology", "life sciences", "drug discovery", "therapeutic",
    "biopharma", "pharmaceutical", "diagnostic", "agbiotech", "industrial biotech",
    "synthetic biology"
}

def has_keyword(text, keywords):
    """Check if any keyword appears in text (case-insensitive)."""
    if text is None:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)

def should_keep(record):
    """
    DROP only if ALL three are true:
    1. No platform keyword
    2. No biotech keyword
    3. Combined title+abstract < 100 chars
    Otherwise KEEP.
    """
    title = record.get("title", "")
    abstract = record.get("abstract", "")

    has_platform = has_keyword(title, PLATFORM_TERMS) or has_keyword(abstract, PLATFORM_TERMS)
    has_biotech = has_keyword(title, BIOTECH_TERMS) or has_keyword(abstract, BIOTECH_TERMS)

    combined_text = (title or "") + (abstract or "")
    text_long_enough = len(combined_text) >= 100

    # DROP if: no platform AND no biotech AND short text
    if not has_platform and not has_biotech and not text_long_enough:
        return False  # DROP

    return True  # KEEP

def main():
    input_path = "data/02_deduped/corpus.jsonl"
    output_path = "data/02_deduped/prefiltered.jsonl"

    total_in = 0
    total_kept = 0

    print(f"Reading from: {input_path}")
    print(f"Writing to: {output_path}")

    # Process corpus
    with open(input_path, 'r', encoding='utf-8') as infile:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for line_num, line in enumerate(infile, 1):
                total_in += 1
                try:
                    record = json.loads(line)
                    if should_keep(record):
                        total_kept += 1
                        outfile.write(json.dumps(record) + '\n')
                except json.JSONDecodeError as e:
                    print(f"Warning: Line {line_num} parse error: {e}")
                    continue

    # Calculate metrics
    drop_count = total_in - total_kept
    drop_rate = (drop_count / total_in * 100) if total_in > 0 else 0.0

    # Report
    print("\n" + "="*60)
    print("PREFILTER RESULTS")
    print("="*60)
    print(f"Total records in:  {total_in:,}")
    print(f"Total records out: {total_kept:,}")
    print(f"Dropped:           {drop_count:,}")
    print(f"Drop rate:         {drop_rate:.2f}%")
    print("="*60)

    if drop_rate > 70:
        print("\nWARNING: Drop rate exceeds 70%!")
        print("The protocol query may be too broad.")
        print("Consider widening inclusion criteria.\n")
    else:
        print()

    # Update PRISMA counts
    prisma_path = "output/prisma_counts.json"
    try:
        with open(prisma_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"phase": "after_prefilter", "n": total_kept}) + '\n')
        print(f"PRISMA count written to: {prisma_path}")
    except IOError as e:
        print(f"Error writing PRISMA count: {e}")

    return total_in, total_kept

if __name__ == "__main__":
    total_in, total_kept = main()
