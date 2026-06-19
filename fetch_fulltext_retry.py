"""
Retry full-text retrieval for unavailable records.
Uses EuropePMC PMCID lookup for records with pmids.
Also retries oa_url records with different approaches.
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


def sanitize_id(id_str):
    return re.sub(r'[^\w\-.]', '_', id_str)


def strip_tags(text):
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def fetch_url(url, timeout=TIMEOUT):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return resp, None
    except Exception as e:
        return None, str(e)


def is_paywall(resp):
    if resp.status_code in (401, 403):
        return True
    text = resp.text[:2000].lower()
    paywall_signals = ['access denied', 'subscription required', 'purchase access',
                       'sign in to access', 'login required', 'paywall']
    return any(s in text for s in paywall_signals)


def try_europepmc_via_pmcid(pmid):
    """Look up PMCID from pmid, then fetch full text XML."""
    url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{pmid}&format=json'
    resp, err = fetch_url(url)
    if err or resp is None or resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    results = data.get('resultList', {}).get('result', [])
    if not results:
        return None
    pmcid = results[0].get('pmcid')
    is_oa = results[0].get('isOpenAccess', 'N') == 'Y'
    if not pmcid or not is_oa:
        return None

    url2 = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
    resp2, err2 = fetch_url(url2)
    if err2 or resp2 is None or resp2.status_code != 200:
        return None
    text = strip_tags(resp2.text)
    return text if len(text) > 200 else None


def try_url(url):
    """Try fetching a direct URL."""
    resp, err = fetch_url(url)
    if err or resp is None:
        return None
    if resp.status_code != 200:
        return None
    if is_paywall(resp):
        return None
    ct = resp.headers.get('Content-Type', '').lower()
    if 'pdf' in ct:
        return None
    text = strip_tags(resp.text)
    return text if len(text) > 200 else None


def try_unpaywall(doi):
    """Try Unpaywall to find OA URL."""
    url = f"https://api.unpaywall.org/v2/{doi}?email=slr-agent@example.com"
    resp, err = fetch_url(url)
    if err or resp is None or resp.status_code != 200:
        return None, None
    try:
        data = resp.json()
    except Exception:
        return None, None
    best_oa = data.get('best_oa_location') or {}
    target_url = best_oa.get('url_for_pdf') or best_oa.get('url_for_landing_page')
    if not target_url:
        return None, None
    return target_url, best_oa


def main():
    # Load all records from prefiltered
    all_records = {}
    with open(PREFILTERED_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            all_records[rec['id']] = rec

    # Load current status
    current_status = {}
    if os.path.exists(STATUS_PATH):
        with open(STATUS_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                s = json.loads(line)
                current_status[s['id']] = s

    # Find unavailable records to retry
    to_retry = []
    for rid, s in current_status.items():
        if s['status'] == 'unavailable':
            rec = all_records.get(rid, {})
            to_retry.append(rec)

    print(f"Records to retry: {len(to_retry)}")

    newly_retrieved = 0
    updated_status = {}

    for i, rec in enumerate(to_retry):
        rec_id = rec.get('id', '')
        doi = rec.get('doi', '')
        pmid = rec.get('pmid')
        oa_url = rec.get('oa_url')
        safe_id = sanitize_id(rec_id)
        out_path = os.path.join(OUTPUT_DIR, f"{safe_id}.txt")

        print(f"[{i+1}/{len(to_retry)}] {rec_id[:60]}")

        text = None
        source = "none"

        # Try 1: EuropePMC via PMCID if pmid present
        if pmid:
            text = try_europepmc_via_pmcid(pmid)
            if text:
                source = "europepmc"
                print(f"  -> EuropePMC ({len(text)} chars)")
            else:
                print(f"  -> EuropePMC: not available/OA")

        # Try 2: Unpaywall if no text yet and has doi
        if not text and doi:
            target_url, oa_loc = try_unpaywall(doi)
            if target_url:
                # Only fetch if not PDF
                if 'pdf' not in target_url.lower():
                    text = try_url(target_url)
                    if text:
                        source = "unpaywall"
                        print(f"  -> Unpaywall ({len(text)} chars)")
                    else:
                        print(f"  -> Unpaywall URL failed: {target_url[:60]}")
                else:
                    print(f"  -> Unpaywall: PDF URL, skipping")
            else:
                print(f"  -> Unpaywall: no OA URL")

        if text:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(text)
            newly_retrieved += 1
            updated_status[rec_id] = {"id": rec_id, "doi": doi, "status": "retrieved", "source": source}
        else:
            updated_status[rec_id] = {"id": rec_id, "doi": doi, "status": "unavailable", "source": "none"}

        time.sleep(0.5)

    # Rewrite status file with updates
    with open(STATUS_PATH, 'w', encoding='utf-8') as sf:
        for rid, s in current_status.items():
            if rid in updated_status:
                sf.write(json.dumps(updated_status[rid]) + '\n')
            else:
                sf.write(json.dumps(s) + '\n')

    print(f"\nNewly retrieved: {newly_retrieved}")

    # Count final stats
    total_retrieved = 0
    source_counts = {}
    with open(STATUS_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            s = json.loads(line)
            if s['status'] == 'retrieved':
                total_retrieved += 1
                src = s.get('source', 'none')
                source_counts[src] = source_counts.get(src, 0) + 1

    print(f"Total retrieved: {total_retrieved}")
    print(f"By source: {source_counts}")

    # Update PRISMA
    prisma_entry = {"phase": "full_text_retrieved", "n": total_retrieved}
    existing = []
    if os.path.exists(PRISMA_PATH):
        with open(PRISMA_PATH, 'r', encoding='utf-8') as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = []
    existing = [e for e in existing if e.get('phase') != 'full_text_retrieved']
    existing.append(prisma_entry)
    with open(PRISMA_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2)

    return total_retrieved, source_counts


if __name__ == '__main__':
    main()
