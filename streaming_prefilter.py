#!/usr/bin/env python3
"""
Streaming prefilter - processes large JSONL files efficiently.
Drop records only if: no platform keyword AND no biotech keyword AND short text (<100 chars).
"""
import json
import sys

def main():
    platform_kws = {"platform", "modular", "multi-sided", "two-sided", "ecosystem", "complementor"}
    biotech_kws = {"biotech", "biotechnology", "life sciences", "drug discovery", "therapeutic", "biopharma", "pharmaceutical", "diagnostic", "agbiotech", "industrial biotech", "synthetic biology"}

    def keep_record(record):
        t = (record.get("title") or "").lower()
        a = (record.get("abstract") or "").lower()

        has_platform = any(kw in t or kw in a for kw in platform_kws)
        has_biotech = any(kw in t or kw in a for kw in biotech_kws)
        has_length = len((record.get("title") or "") + (record.get("abstract") or "")) >= 100

        # KEEP if any of: has platform, has biotech, or long enough
        return has_platform or has_biotech or has_length

    in_path = "data/02_deduped/corpus.jsonl"
    out_path = "data/02_deduped/prefiltered.jsonl"

    total_in = 0
    total_out = 0

    with open(in_path, 'r', encoding='utf-8') as inf:
        with open(out_path, 'w', encoding='utf-8') as outf:
            for line in inf:
                total_in += 1
                try:
                    rec = json.loads(line)
                    if keep_record(rec):
                        total_out += 1
                        outf.write(json.dumps(rec) + '\n')
                except json.JSONDecodeError:
                    pass

    drop_pct = ((total_in - total_out) / total_in * 100) if total_in > 0 else 0.0

    print(f"Prefilter Results:")
    print(f"  Input:  {total_in:,}")
    print(f"  Output: {total_out:,}")
    print(f"  Drop Rate: {drop_pct:.2f}%")

    if drop_pct > 70:
        print("  WARNING: Drop rate exceeds 70%")

    # Write PRISMA count
    with open("output/prisma_counts.json", 'a', encoding='utf-8') as f:
        json.dump({"phase": "after_prefilter", "n": total_out}, f)
        f.write('\n')

    return total_in, total_out

if __name__ == "__main__":
    main()
