#!/usr/bin/env python3
"""Deduplicate raw search results across databases.

Strategy:
1. Group by DOI where available (canonical match).
2. For DOI-less records, group by (normalized_title, first_author_surname, year).
3. Merge groups: prefer the version with the longest abstract.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def normalize_title(t: str | None) -> str:
    if not t:
        return ""
    t = t.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def first_author_surname(authors: list[str] | None) -> str:
    if not authors:
        return ""
    a = authors[0]
    parts = a.strip().split()
    return parts[-1].lower() if parts else ""


def merge(records: list[dict]) -> dict:
    """Pick the record with the longest abstract; merge sources."""
    records = sorted(records, key=lambda r: len(r.get("abstract") or ""), reverse=True)
    primary = dict(records[0])
    sources = []
    for r in records:
        s = r.get("source")
        if s and s not in sources:
            sources.append(s)
    primary["source"] = sources
    # Promote any non-null DOI we found across the group
    for r in records:
        if not primary.get("doi") and r.get("doi"):
            primary["doi"] = r["doi"]
            break
    return primary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    indir = Path(args.indir)
    all_records: list[dict] = []
    for jl in sorted(indir.glob("*.jsonl")):
        with open(jl) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    all_records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    raw_total = len(all_records)

    # Bucket: DOI first
    by_doi: dict[str, list[dict]] = {}
    by_key: dict[tuple, list[dict]] = {}
    for r in all_records:
        doi = (r.get("doi") or "").lower().strip() or None
        if doi:
            by_doi.setdefault(doi, []).append(r)
        else:
            key = (normalize_title(r.get("title")), first_author_surname(r.get("authors")), r.get("year"))
            if not key[0]:
                continue  # no title, no useful key
            by_key.setdefault(key, []).append(r)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(out, "w") as f:
        for group in by_doi.values():
            f.write(json.dumps(merge(group)) + "\n")
            written += 1
        for group in by_key.values():
            f.write(json.dumps(merge(group)) + "\n")
            written += 1

    print(f"dedupe: {raw_total} raw → {written} unique ({raw_total - written} duplicates removed)", file=sys.stderr)


if __name__ == "__main__":
    main()
