"""
Full-text retrieval for INCLUDE records.
Tries in order: EuropePMC -> OpenAlex oa_url -> Unpaywall
Max 2 attempts per paper.
"""

import json
import os
import re
import time
import requests
from xml.etree import ElementTree as ET

OUTPUT_DIR = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent\data\04_full_text"
DECISIONS_PATH = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent\data\03_screened\decisions.jsonl"
PREFILTERED_PATH = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent\data\02_deduped\prefiltered.jsonl"
STATUS_PATH = os.path.join(OUTPUT_DIR, "_status.jsonl")
PRISMA_PATH = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent\output\prisma_counts.json"

HEADERS = {
    "User-Agent": "SLR-Agent/1.0 (slr-agent@example.com)"
}
TIMEOUT = 30

os.makedirs(OUTPUT_DIR, exist_ok=True)


def sanitize_id(id_str):
    """Replace special chars with underscores for filesystem safety."""
    return re.sub(r'[^\w\-.]', '_', id_str)


def strip_tags(text):
    """Strip XML/HTML tags from text."""
    # Remove tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Collapse whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def fetch_url(url, timeout=TIMEOUT):
    """Fetch a URL, return (response, error). Returns None response on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return resp, None
    except Exception as e:
        return None, str(e)


def is_paywall(resp):
    """Check if response looks like a paywall/auth block."""
    if resp.status_code in (401, 403):
        return True
    # Check for common paywall indicators in content
    text = resp.text[:2000].lower()
    paywall_signals = ['access denied', 'subscription required', 'purchase access',
                       'sign in to access', 'login required', 'paywall']
    return any(s in text for s in paywall_signals)


def try_europepmc(pmid):
    """Try EuropePMC full-text XML."""
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/article/MED/{pmid}/fullTextXML"
    resp, err = fetch_url(url)
    if err or resp is None:
        return None, "error"
    if resp.status_code != 200:
        return None, f"http_{resp.status_code}"
    if is_paywall(resp):
        return None, "paywall"
    try:
        # Parse XML and extract text
        root = ET.fromstring(resp.content)
        texts = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                texts.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                texts.append(elem.tail.strip())
        full_text = ' '.join(texts)
        if len(full_text) > 200:
            return full_text, "ok"
        return None, "too_short"
    except Exception as e:
        # Fallback: strip tags from raw XML text
        text = strip_tags(resp.text)
        if len(text) > 200:
            return text, "ok"
        return None, "parse_error"


def try_url(url):
    """Try fetching a direct URL (oa_url or pdf/landing page)."""
    resp, err = fetch_url(url)
    if err or resp is None:
        return None, "error"
    if resp.status_code != 200:
        return None, f"http_{resp.status_code}"
    if is_paywall(resp):
        return None, "paywall"
    # Check content type
    ct = resp.headers.get('Content-Type', '').lower()
    if 'pdf' in ct:
        # Can't easily extract PDF text, mark as unavailable
        return None, "pdf_binary"
    text = strip_tags(resp.text)
    if len(text) > 200:
        return text, "ok"
    return None, "too_short"


def try_unpaywall(doi):
    """Try Unpaywall to find OA URL, then fetch it."""
    url = f"https://api.unpaywall.org/v2/{doi}?email=slr-agent@example.com"
    resp, err = fetch_url(url)
    if err or resp is None:
        return None, "error"
    if resp.status_code != 200:
        return None, f"http_{resp.status_code}"
    try:
        data = resp.json()
    except Exception:
        return None, "json_error"

    best_oa = data.get('best_oa_location') or {}
    target_url = best_oa.get('url_for_pdf') or best_oa.get('url_for_landing_page')
    if not target_url:
        return None, "no_oa_url"

    # Now fetch that URL
    text, status = try_url(target_url)
    return text, status


def retrieve_paper(record, attempts_left):
    """Try to retrieve full text for a record. Returns (text, source) or (None, 'none')."""
    pmid = record.get('pmid')
    oa_url = record.get('oa_url')
    doi = record.get('doi')

    # Attempt 1: EuropePMC if pmid present
    if pmid and attempts_left > 0:
        attempts_left -= 1
        text, status = try_europepmc(pmid)
        if text:
            return text, "europepmc", attempts_left

    # Attempt 2: OpenAlex oa_url
    if oa_url and attempts_left > 0:
        attempts_left -= 1
        text, status = try_url(oa_url)
        if text:
            return text, "openalex", attempts_left

    # Attempt 3 (only if still have attempts): Unpaywall
    if doi and attempts_left > 0:
        attempts_left -= 1
        text, status = try_unpaywall(doi)
        if text:
            return text, "unpaywall", attempts_left

    return None, "none", 0


def main():
    # Load INCLUDE ids
    include_ids = set()
    with open(DECISIONS_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            if rec.get('decision') == 'INCLUDE':
                include_ids.add(rec['id'])

    print(f"INCLUDE records to process: {len(include_ids)}")

    # Load matching prefiltered records
    records = []
    with open(PREFILTERED_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            if rec.get('id') in include_ids:
                records.append(rec)

    print(f"Matched in prefiltered: {len(records)}")

    # Clear/create status file
    if os.path.exists(STATUS_PATH):
        os.remove(STATUS_PATH)

    retrieved = 0
    unavailable = 0
    source_counts = {"europepmc": 0, "openalex": 0, "unpaywall": 0, "none": 0}

    for i, rec in enumerate(records):
        rec_id = rec['id']
        doi = rec.get('doi', '')
        safe_id = sanitize_id(rec_id)
        out_path = os.path.join(OUTPUT_DIR, f"{safe_id}.txt")

        print(f"[{i+1}/{len(records)}] Processing: {rec_id[:60]}")

        # Skip if already retrieved
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            print(f"  -> Already exists, skipping")
            # Still need to write status - read what we have
            text, source = None, "none"
            retrieved += 1
            source_counts["openalex"] += 1  # approximate
            status_entry = {"id": rec_id, "doi": doi, "status": "retrieved", "source": "cached"}
            with open(STATUS_PATH, 'a', encoding='utf-8') as sf:
                sf.write(json.dumps(status_entry) + '\n')
            continue

        text, source, _ = retrieve_paper(rec, attempts_left=2)

        if text:
            # Save text
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(text)
            status = "retrieved"
            retrieved += 1
            source_counts[source] = source_counts.get(source, 0) + 1
            print(f"  -> Retrieved via {source} ({len(text)} chars)")
        else:
            status = "unavailable"
            unavailable += 1
            source_counts["none"] += 1
            print(f"  -> Unavailable")

        status_entry = {"id": rec_id, "doi": doi, "status": status, "source": source}
        with open(STATUS_PATH, 'a', encoding='utf-8') as sf:
            sf.write(json.dumps(status_entry) + '\n')

        # Small delay to be polite
        time.sleep(0.5)

    print(f"\n=== RESULTS ===")
    print(f"Total attempted: {len(records)}")
    print(f"Retrieved: {retrieved}")
    print(f"Unavailable: {unavailable}")
    print(f"By source: {source_counts}")

    # Update prisma_counts.json
    prisma_entry = {"phase": "full_text_retrieved", "n": retrieved}

    existing = []
    if os.path.exists(PRISMA_PATH):
        with open(PRISMA_PATH, 'r', encoding='utf-8') as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = []

    # Remove old full_text_retrieved entry if present
    existing = [e for e in existing if e.get('phase') != 'full_text_retrieved']
    existing.append(prisma_entry)

    with open(PRISMA_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2)

    print(f"\nPRISMA updated: full_text_retrieved = {retrieved}")

    return retrieved, unavailable, source_counts


if __name__ == '__main__':
    main()
