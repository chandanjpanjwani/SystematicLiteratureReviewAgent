#!/usr/bin/env python3
"""
Pre-filter the deduped corpus based on platform and biotech keywords.
DROP only if ALL three conditions are true:
1. No platform-related term
2. No biotech-related term
3. Title + abstract < 100 characters
Otherwise KEEP.
"""
import json

# Define keyword sets
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
    Determine if a record should be kept.
    DROP only if ALL of these are true:
    - No platform term
    - No biotech term
    - Title + abstract < 100 chars
    Otherwise KEEP.
    """
    title = record.get("title", "")
    abstract = record.get("abstract", "")

    # Check for platform keywords
    has_platform = has_keyword(title, PLATFORM_TERMS) or has_keyword(abstract, PLATFORM_TERMS)

    # Check for biotech keywords
    has_biotech = has_keyword(title, BIOTECH_TERMS) or has_keyword(abstract, BIOTECH_TERMS)

    # Check text length
    combined_text = (title or "") + (abstract or "")
    text_long_enough = len(combined_text) >= 100

    # DROP only if ALL of these are true:
    # - No platform keyword
    # - No biotech keyword
    # - Text is short
    if not has_platform and not has_biotech and not text_long_enough:
        return False  # DROP

    return True  # KEEP

def main():
    input_file = "/home/npdrpi1/ClaudeAgents/slr-agent-master/data/02_deduped/corpus.jsonl"
    output_file = "/home/npdrpi1/ClaudeAgents/slr-agent-master/data/02_deduped/prefiltered.jsonl"

    total_in = 0
    total_kept = 0

    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            total_in += 1
            try:
                record = json.loads(line)
                if should_keep(record):
                    total_kept += 1
                    outfile.write(json.dumps(record) + '\n')
            except json.JSONDecodeError as e:
                print(f"Error parsing line {total_in}: {e}")
                continue

    # Calculate drop rate
    drop_rate = (total_in - total_kept) / total_in * 100 if total_in > 0 else 0

    print(f"Total in: {total_in}")
    print(f"Total kept: {total_kept}")
    print(f"Drop rate: {drop_rate:.2f}%")

    if drop_rate > 70:
        print("WARNING: Drop rate exceeds 70%. The protocol query may be too broad.")

    # Append PRISMA count
    prisma_file = "/home/npdrpi1/ClaudeAgents/slr-agent-master/output/prisma_counts.json"
    with open(prisma_file, 'a') as f:
        f.write(json.dumps({"phase": "after_prefilter", "n": total_kept}) + '\n')

    print(f"PRISMA count appended to {prisma_file}")

if __name__ == "__main__":
    main()
