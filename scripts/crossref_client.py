#!/usr/bin/env python3
"""CrossRef search client. Primary use is metadata reconciliation."""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://api.crossref.org/works"
MAX_RESULTS = 2000
ROWS = 100
MAILTO = "slr-agent@example.com"


def fetch_page(query: str, filter_str: str, rows: int, offset: int, query_param: str = "query") -> dict:
    params = {query_param: query, "filter": filter_str, "rows": rows, "offset": offset}
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": f"slr-agent (mailto:{MAILTO})"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def normalize(item: dict) -> dict:
    title = item.get("title") or []
    abstract = item.get("abstract")
    if abstract:
        # CrossRef abstracts come as JATS XML — quick strip
        import re
        abstract = re.sub(r"<[^>]+>", " ", abstract).strip()

    authors = [
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in (item.get("author") or [])
    ]

    year = None
    date_parts = (item.get("issued") or {}).get("date-parts") or [[]]
    if date_parts and date_parts[0]:
        year = date_parts[0][0]

    return {
        "id": f"CR:{item.get('DOI')}",
        "doi": item.get("DOI"),
        "title": title[0] if title else None,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "venue": (item.get("container-title") or [None])[0],
        "source": "crossref",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.queries) as f:
        cfg = json.load(f)["crossref"]

    query = cfg.get("query.title") or cfg.get("query", "")
    query_param = "query.title" if "query.title" in cfg else "query"
    filter_str = cfg.get("filter", "from-pub-date:2005")
    offset = 0
    total = 0

    with open(args.out, "w") as out:
        while total < MAX_RESULTS:
            try:
                page = fetch_page(query, filter_str, ROWS, offset, query_param=query_param)
            except Exception as e:
                print(f"crossref error: {e}", file=sys.stderr)
                break
            items = (page.get("message") or {}).get("items") or []
            if not items:
                break
            for it in items:
                out.write(json.dumps(normalize(it)) + "\n")
                total += 1
                if total >= MAX_RESULTS:
                    break
            offset += ROWS
            time.sleep(0.1)

    print(f"crossref: wrote {total} records to {args.out}")


if __name__ == "__main__":
    main()
