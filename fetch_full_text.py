#!/usr/bin/env python3
"""Fetch full text for INCLUDE records from the SLR screening pipeline."""

import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

# Paths
BASE = Path(r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent")
DECISIONS_FILE = BASE / "data/03_screened/decisions.jsonl"
PREFILTERED_FILE = BASE / "data/02_deduped/prefiltered.jsonl"
OUTPUT_DIR = BASE / "data/04_full_text"
PRISMA_FILE = BASE / "output/prisma_counts.json"
STATUS_FILE = OUTPUT_DIR / "_status.jsonl"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def strip_tags(text):
    return re.sub(r'<[^>]+>', ' ', text)

def fetch_url(url, timeout=30):
    """Fetch URL, return text or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "slr-agent/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            # Try UTF-8, fallback to latin-1
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1", errors="replace")
    except Exception as e:
        print(f"  FETCH ERROR {url[:80]}: {e}")
        return None

# Load INCLUDE decisions
include_ids = set()
with open(DECISIONS_FILE, encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        if rec.get("decision") == "INCLUDE":
            include_ids.add(rec["id"])

print(f"INCLUDE records: {len(include_ids)}")

# Load metadata for INCLUDE records
metadata = {}
with open(PREFILTERED_FILE, encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        if rec["id"] in include_ids:
            metadata[rec["id"]] = rec

print(f"Metadata found for: {len(metadata)} records")

# Track already done (resume support)
done_ids = set()
if STATUS_FILE.exists():
    with open(STATUS_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                done_ids.add(rec["id"])
            except:
                pass

print(f"Already retrieved: {len(done_ids)}")

status_log = []
source_counts = {"epmc": 0, "oa_url": 0, "unpaywall": 0, "none": 0}

for idx, paper_id in enumerate(sorted(include_ids)):
    if paper_id in done_ids:
        print(f"[{idx+1}/{len(include_ids)}] SKIP (already done): {paper_id}")
        continue

    meta = metadata.get(paper_id, {})
    doi = meta.get("doi") or ""
    oa_url = meta.get("oa_url") or ""
    pmid = meta.get("pmid") or ""

    safe_id = paper_id.replace("/", "_").replace(":", "_")
    out_file = OUTPUT_DIR / f"{safe_id}.txt"

    print(f"[{idx+1}/{len(include_ids)}] {paper_id}")

    text = None
    source = "none"
    attempts = 0

    # Attempt 1: EuropePMC full-text XML
    if pmid and attempts < 2:
        attempts += 1
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/article/MED/{pmid}/fullTextXML"
        print(f"  Trying EuropePMC: {url}")
        content = fetch_url(url)
        if content and len(content.strip()) > 200 and "<article" in content.lower():
            text = strip_tags(content)
            source = "epmc"
            print(f"  -> Retrieved via EuropePMC ({len(text)} chars)")

    # Attempt 2a: OA URL
    if text is None and oa_url and attempts < 2:
        attempts += 1
        print(f"  Trying OA URL: {oa_url[:80]}")
        content = fetch_url(oa_url)
        if content and len(content.strip()) > 200:
            text = strip_tags(content)
            source = "oa_url"
            print(f"  -> Retrieved via OA URL ({len(text)} chars)")

    # Attempt 2b: Unpaywall (if still no text and doi available, use as 2nd attempt slot)
    if text is None and doi and attempts < 2:
        attempts += 1
        uw_url = f"https://api.unpaywall.org/v2/{doi}?email=slr-agent@example.com"
        print(f"  Trying Unpaywall: {uw_url}")
        uw_content = fetch_url(uw_url)
        if uw_content:
            try:
                uw_data = json.loads(uw_content)
                best = uw_data.get("best_oa_location") or {}
                pdf_url = best.get("url_for_pdf") or best.get("url")
                if pdf_url:
                    print(f"  Unpaywall PDF URL: {pdf_url[:80]}")
                    content = fetch_url(pdf_url)
                    if content and len(content.strip()) > 200:
                        text = strip_tags(content)
                        source = "unpaywall"
                        print(f"  -> Retrieved via Unpaywall ({len(text)} chars)")
            except Exception as e:
                print(f"  Unpaywall parse error: {e}")

    # Save result
    status = "retrieved" if text else "unavailable"
    source_counts[source] += 1

    if text:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(text)

    status_rec = {"id": paper_id, "doi": doi, "status": status, "source": source}
    with open(STATUS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(status_rec) + "\n")

    print(f"  => {status} / {source}")
    time.sleep(0.5)  # polite delay

# ---- Summary ----
# Re-read full status file for accurate counts (including pre-done)
all_statuses = []
with open(STATUS_FILE, encoding="utf-8") as f:
    for line in f:
        try:
            all_statuses.append(json.loads(line))
        except:
            pass

retrieved = [s for s in all_statuses if s["status"] == "retrieved"]
unavailable = [s for s in all_statuses if s["status"] == "unavailable"]

src_breakdown = {}
for s in retrieved:
    src_breakdown[s["source"]] = src_breakdown.get(s["source"], 0) + 1

print("\n=== SUMMARY ===")
print(f"Total attempted: {len(include_ids)}")
print(f"Retrieved: {len(retrieved)}")
print(f"Unavailable: {len(unavailable)}")
print(f"Source breakdown: {src_breakdown}")

# Append to prisma_counts.json
prisma_entry = {"phase": "full_text_retrieved", "n": len(retrieved)}
prisma_data = []
if PRISMA_FILE.exists():
    with open(PRISMA_FILE, encoding="utf-8") as f:
        try:
            prisma_data = json.load(f)
        except:
            prisma_data = []

# Remove any existing full_text_retrieved entry to avoid duplicates on re-run
prisma_data = [e for e in prisma_data if e.get("phase") != "full_text_retrieved"]
prisma_data.append(prisma_entry)

with open(PRISMA_FILE, "w", encoding="utf-8") as f:
    json.dump(prisma_data, f, indent=2)

print(f"\nUpdated {PRISMA_FILE}")
print("Done.")
