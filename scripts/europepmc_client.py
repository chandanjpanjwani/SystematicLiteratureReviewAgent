#!/usr/bin/env python3
"""EuropePMC search client. Biomedical focus, OA full text available where possible."""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MAX_RESULTS = 2000
PAGE_SIZE = 100


def fetch_page(query: str, page_size: int, cursor: str) -> dict:
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": page_size,
        "cursorMark": cursor,
    }
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "slr-agent"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def normalize(r: dict) -> dict:
    return {
        "id": f"EPMC:{r.get('id')}:{r.get('source')}",
        "doi": r.get("doi"),
        "pmid": r.get("pmid"),
        "title": r.get("title"),
        "abstract": r.get("abstractText"),
        "authors": [a.get("fullName") for a in (r.get("authorList") or {}).get("author", []) if a.get("fullName")],
        "year": int(r.get("pubYear")) if r.get("pubYear") else None,
        "venue": r.get("journalTitle"),
        "is_open_access": r.get("isOpenAccess") == "Y",
        "source": "europepmc",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.queries) as f:
        cfg = json.load(f)["europepmc"]

    query = cfg["query"]
    cursor = "*"
    total = 0

    with open(args.out, "w") as out:
        while total < MAX_RESULTS:
            try:
                page = fetch_page(query, PAGE_SIZE, cursor)
            except Exception as e:
                print(f"europepmc error: {e}", file=sys.stderr)
                break
            results = (page.get("resultList") or {}).get("result") or []
            if not results:
                break
            for r in results:
                out.write(json.dumps(normalize(r)) + "\n")
                total += 1
                if total >= MAX_RESULTS:
                    break
            next_cursor = page.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
            time.sleep(0.2)

    print(f"europepmc: wrote {total} records to {args.out}")


if __name__ == "__main__":
    main()
