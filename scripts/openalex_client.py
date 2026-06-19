#!/usr/bin/env python3
"""OpenAlex search client. Reads query from queries.json, writes JSONL records."""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

OPENALEX = "https://api.openalex.org/works"
MAX_RESULTS = 2000
PER_PAGE = 200
# Polite pool: putting an email in the mailto param gets you faster, more reliable service.
MAILTO = "slr-agent@example.com"


def fetch_page(search: str, filter_str: str, cursor: str) -> dict:
    params = {
        "filter": filter_str,
        "per-page": PER_PAGE,
        "cursor": cursor,
        "mailto": MAILTO,
    }
    if search:
        params["search"] = search
    url = f"{OPENALEX}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": f"slr-agent ({MAILTO})"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def normalize(work: dict) -> dict:
    # OpenAlex stores abstracts as inverted indexes; rebuild plain text.
    abstract = None
    inv = work.get("abstract_inverted_index")
    if inv:
        positions = {}
        for word, idxs in inv.items():
            for i in idxs:
                positions[i] = word
        abstract = " ".join(positions[i] for i in sorted(positions))

    authors = [
        a.get("author", {}).get("display_name")
        for a in (work.get("authorships") or [])
        if a.get("author", {}).get("display_name")
    ]

    return {
        "id": work.get("id"),
        "doi": (work.get("doi") or "").replace("https://doi.org/", "") or None,
        "title": work.get("title"),
        "abstract": abstract,
        "authors": authors,
        "year": work.get("publication_year"),
        "venue": ((work.get("primary_location") or {}).get("source") or {}).get("display_name"),
        "oa_url": (work.get("open_access") or {}).get("oa_url"),
        "source": "openalex",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queries", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    with open(args.queries) as f:
        cfg = json.load(f)["openalex"]

    search = cfg.get("search", "")
    filter_str = cfg.get("filter", "")

    cursor = "*"
    total = 0
    with open(args.out, "w") as out:
        while cursor and total < MAX_RESULTS:
            try:
                page = fetch_page(search, filter_str, cursor)
            except Exception as e:
                print(f"openalex error: {e}", file=sys.stderr)
                break
            results = page.get("results", [])
            if not results:
                break
            for w in results:
                out.write(json.dumps(normalize(w)) + "\n")
                total += 1
                if total >= MAX_RESULTS:
                    break
            cursor = page.get("meta", {}).get("next_cursor")
            time.sleep(0.1)  # be polite

    print(f"openalex: wrote {total} records to {args.out}")


if __name__ == "__main__":
    main()
