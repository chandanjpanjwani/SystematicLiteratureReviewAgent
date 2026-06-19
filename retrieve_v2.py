"""
Full-text retrieval v2 for 74 unavailable papers.
"""
import json
import os
import re
import time
import io
import urllib.request
import urllib.error
from html.parser import HTMLParser

FULL_TEXT_DIR = "data/04_full_text"
STATUS_FILE = os.path.join(FULL_TEXT_DIR, "_status.jsonl")
EMAIL = "slr-agent@example.com"
TIMEOUT = 20
SLEEP = 0.5

TARGET_DOIS = [
    "10.5912/jcb112", "10.1108/bjm-11-2015-0223",
    "10.2174/2213809907999200330164359", "10.5912/jcb748",
    "10.1093/oso/9780195084009.003.0005", "10.5912/jcb1329",
    "10.1111/j.1467-6486.2008.00777.x", "10.1371/journal.pone.0243813",
    "10.1093/icc/dtt022", "10.1016/j.drudis.2025.104583",
    "10.1016/j.drudis.2011.06.006", "10.1007/10_2018_59",
    "10.2515/therapie:2006059", "10.1186/s40497-015-0034-7",
    "10.1186/2192-5372-3-2", "10.1111/jpim.12218",
    "10.24840/2183-0606_007.002_0005", "10.1080/09537325.2010.488062",
    "10.3390/su9010108", "10.1007/s10460-021-10237-7",
    "10.1186/s13731-015-0027-3", "10.3846/jbem.2019.6880",
    "10.1051/bioconf/20237608003", "10.53728/2765-6500.1459",
    "10.1515/jib-2022-0031", "10.62270/jirms.vi.14",
    "10.1186/s44398-025-00004-7", "10.35808/ersj/2087",
    "10.1371/journal.pone.0276204", "10.18461/ijfsd.v7i2.724",
    "10.3389/fbloc.2020.586525", "10.3390/su16062339",
    "10.1177/0007650319826307", "10.3390/su13073599",
    "10.1017/s109285292200092x", "10.24212/2179-3565.2014v5i1p19-38",
    "10.1186/s40852-017-0061-4", "10.5912/jcb1280",
    "10.35808/ersj/2088", "10.5755/j01.ee.21.4.11711",
    "10.4324/9781003274322-4", "10.1177/2472630317744283",
    "10.1186/1478-4505-9-37", "10.1002/imt2.251",
    "10.1186/1472-698x-10-s1-s1", "10.1002/bse.70062",
    "10.5912/jcb154", "10.1186/1471-2105-15-s1-s2",
    "10.1177/2393957516647260", "10.1177/20552076241311740",
    "10.1108/md-08-2025-374", "10.18235/0004947",
    "10.18063/jmds.v1i1.119", "10.3389/fbloc.2025.1510429",
    "10.26686/wgtn.16959421", "10.1051/e3sconf/202125702014",
    "10.1007/s00122-025-05060-1", "10.1242/dmm.050672",
    "10.1002/psp4.12393", "10.1177/2472630320982580",
    "10.1016/j.slast.2022.01.001", "10.1177/2472630318812656",
    "10.1051/bioconf/20235701002", "10.3390/books978-3-0365-7969-6",
    "10.4018/979-8-3373-1117-3.ch003", "10.1002/9781118273166.notes",
    "10.1002/sej.1543", "10.2172/1580116",
    "10.25394/pgs.15019377.v1", "10.1007/s44337-025-00313-w",
    "10.3389/fbioe.2025.1688121",
]


def safe_id(doi):
    return re.sub(r'[/:?=]', '_', doi)


def fetch_url(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SLR-Agent/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read() if binary else resp.read().decode("utf-8", errors="replace")


class TagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.text_parts.append(data)

    def get_text(self):
        return " ".join(self.text_parts)


def html_to_text(html):
    parser = TagStripper()
    parser.feed(html)
    text = parser.get_text()
    # Compress whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def pdf_to_text(pdf_bytes):
    try:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(pdf_bytes))
    except Exception:
        return None


def load_status():
    records = {}
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                records[rec["id"]] = rec
    return records


def save_status(records):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        for rec in records.values():
            f.write(json.dumps(rec) + "\n")


def save_text(filename, text):
    path = os.path.join(FULL_TEXT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def try_unpaywall(doi):
    """Returns (text, source_label) or None."""
    url = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
    try:
        data = json.loads(fetch_url(url))
    except Exception as e:
        print(f"  Unpaywall error for {doi}: {e}")
        return None

    # Collect candidate locations
    locations = []
    best = data.get("best_oa_location")
    if best:
        locations.append(best)
    for loc in data.get("oa_locations", []):
        if loc not in locations:
            locations.append(loc)

    for loc in locations:
        pdf_url = loc.get("url_for_pdf")
        landing_url = loc.get("url_for_landing_page")

        if pdf_url:
            try:
                time.sleep(SLEEP)
                pdf_bytes = fetch_url(pdf_url, binary=True)
                if pdf_bytes[:4] == b'%PDF':
                    text = pdf_to_text(pdf_bytes)
                    if text and len(text.strip()) > 100:
                        return text, f"unpaywall_pdf:{pdf_url}"
                    else:
                        # Save raw pdf
                        sid = safe_id(doi)
                        path = os.path.join(FULL_TEXT_DIR, sid + ".pdf")
                        with open(path, "wb") as f:
                            f.write(pdf_bytes)
                        return f"[PDF saved: {sid}.pdf]", f"unpaywall_pdf_raw:{pdf_url}"
                else:
                    # Maybe it's HTML
                    text = html_to_text(pdf_bytes.decode("utf-8", errors="replace"))
                    if len(text) > 200:
                        return text, f"unpaywall_html:{pdf_url}"
            except Exception as e:
                print(f"    PDF url error {pdf_url}: {e}")

        if landing_url:
            try:
                time.sleep(SLEEP)
                html = fetch_url(landing_url)
                text = html_to_text(html)
                if len(text) > 200:
                    return text, f"unpaywall_landing:{landing_url}"
            except Exception as e:
                print(f"    Landing url error {landing_url}: {e}")

    return None


def try_europepmc(doi):
    """Try EuropePMC search to get PMID then fetch full text XML."""
    # First search for the DOI
    search_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&format=json&resulttype=core"
    try:
        data = json.loads(fetch_url(search_url))
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return None
        pmid = results[0].get("pmid") or results[0].get("id")
        if not pmid:
            return None
        source = results[0].get("source", "MED")
        xml_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/article/{source}/{pmid}/fullTextXML"
        time.sleep(SLEEP)
        xml_text = fetch_url(xml_url)
        # Strip XML tags
        text = re.sub(r'<[^>]+>', ' ', xml_text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 200:
            return text, f"europepmc_xml:{xml_url}"
    except Exception as e:
        print(f"  EuropePMC error for {doi}: {e}")
    return None


def try_doi_landing(doi):
    """Follow DOI redirect and fetch landing page."""
    url = f"https://doi.org/{doi}"
    try:
        html = fetch_url(url)
        text = html_to_text(html)
        if len(text) > 200:
            return text, f"doi_landing:{url}"
    except Exception as e:
        print(f"  DOI landing error for {doi}: {e}")
    return None


def main():
    os.makedirs(FULL_TEXT_DIR, exist_ok=True)
    records = load_status()

    # Build DOI -> record_id mapping
    doi_to_id = {}
    for rec_id, rec in records.items():
        doi = rec.get("doi", "")
        if doi:
            doi_to_id[doi] = rec_id

    newly_retrieved = 0
    still_unavailable = 0

    for doi in TARGET_DOIS:
        rec_id = doi_to_id.get(doi)
        if rec_id is None:
            # Create a new record
            rec_id = f"CR:{doi}"
            records[rec_id] = {"id": rec_id, "doi": doi, "status": "unavailable", "source": "none"}

        rec = records[rec_id]
        if rec.get("status") in ("retrieved", "retrieved_pdf"):
            print(f"SKIP (already retrieved): {doi}")
            continue

        print(f"Processing: {doi}")
        result = None

        # Strategy 1: Unpaywall
        time.sleep(SLEEP)
        result = try_unpaywall(doi)

        # Strategy 2: EuropePMC
        if result is None:
            time.sleep(SLEEP)
            result = try_europepmc(doi)

        # Strategy 3: DOI landing page
        if result is None:
            time.sleep(SLEEP)
            result = try_doi_landing(doi)

        if result:
            text, source_label = result
            sid = safe_id(doi)
            filename = sid + ".txt"
            save_text(filename, text)
            rec["status"] = "retrieved"
            rec["source"] = source_label
            newly_retrieved += 1
            print(f"  SUCCESS: {source_label[:60]}")
        else:
            rec["status"] = "unavailable"
            rec["source"] = "none"
            still_unavailable += 1
            print(f"  FAILED: still unavailable")

    save_status(records)

    # Count total retrieved
    total_retrieved = sum(1 for r in records.values() if r.get("status") in ("retrieved", "retrieved_pdf"))

    print(f"\n=== RESULTS ===")
    print(f"Newly retrieved: {newly_retrieved}")
    print(f"Still unavailable: {still_unavailable}")
    print(f"Total retrieved (all): {total_retrieved}")

    # Update prisma_counts.json
    prisma_path = "output/prisma_counts.json"
    if os.path.exists(prisma_path):
        with open(prisma_path, "r", encoding="utf-8") as f:
            prisma = json.load(f)
    else:
        prisma = []

    prisma.append({"phase": "full_text_retrieved_v2", "n": total_retrieved})
    with open(prisma_path, "w", encoding="utf-8") as f:
        json.dump(prisma, f, indent=2)

    print(f"Updated {prisma_path} with total_retrieved={total_retrieved}")


if __name__ == "__main__":
    main()
