#!/usr/bin/env python3
"""Semantic Scholar Graph API client. Free tier; uses bulk-search endpoint."""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
MAX_RESULTS = 2000


def fetch_page(query: str, year: str, token: str | None, fields: str) -> dict:
    params = {"query": query, "year": year, "fields": fields}
    if token:
        params["token"] = token
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "slr-agent"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def normalize(p: dict) -> dict:
    return {
        "id": f"S2:{p.get('paperId')}",
        "doi": (p.get("externalIds") or {}).get("DOI"),
        "title": p.get("title"),
        "abstract": p.get("abstract") or (p.get("tldr") or {}).get("text"),
        "authors": [a.get("name") for a in (p.get("authors") or []) if a.get("name")],
        "year": p.get("year"),
        "venue": p.get("venue"),
        "source": "semantic_scholar",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.queries) as f:
        cfg = json.load(f)["semantic_scholar"]

    query = cfg["query"]
    year = cfg.get("year", "2005-")
    fields = cfg.get("fields", "title,abstract,year,authors,externalIds,tldr,venue")

    token = None
    total = 0
    with open(args.out, "w") as out:
        while total < MAX_RESULTS:
            try:
                page = fetch_page(query, year, token, fields)
            except Exception as e:
                print(f"semantic_scholar error: {e}", file=sys.stderr)
                break
            data = page.get("data") or []
            if not data:
                break
            for p in data:
                out.write(json.dumps(normalize(p)) + "\n")
                total += 1
                if total >= MAX_RESULTS:
                    break
            token = page.get("token")
            if not token:
                break
            time.sleep(1.0)  # S2 free tier is rate-limited

    print(f"semantic_scholar: wrote {total} records to {args.out}")


if __name__ == "__main__":
    main()
