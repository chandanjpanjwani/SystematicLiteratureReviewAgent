"""
Convert all paper-record JSONL files to Excel, then delete the JSONL files.

Keeps (not deleted):
  .claude/settings.json        — agent permissions
  data/01_raw/queries.json     — search queries / pipeline config
  output/prisma_counts.json    — PRISMA bookkeeping for flowchart

Converts then deletes:
  data/01_raw/{openalex,crossref,epmc,s2}.jsonl  → output/excel/Raw_Search_Results.xlsx
  data/02_deduped/corpus.jsonl                   → output/excel/Corpus.xlsx
  data/02_deduped/prefiltered.jsonl              → output/excel/Corpus.xlsx (2nd sheet)
  data/02_deduped/chunks/*.jsonl                 → (merged into corpus, just deleted)
  data/03_screened/decisions.jsonl               → output/excel/Screening_Decisions.xlsx
  data/03_screened/batches/                      → (intermediate, just deleted)
  data/05_extracted/extraction.jsonl             → output/excel/Extraction.xlsx
  data/05_extracted/quality.jsonl                → output/excel/Quality_MMAT.xlsx
"""

import json
import os
import shutil
import glob
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
OUT  = BASE / "output" / "excel"
OUT.mkdir(parents=True, exist_ok=True)


def read_jsonl(path):
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def flatten(record):
    """Flatten nested dicts/lists to strings for Excel."""
    flat = {}
    for k, v in record.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                flat[f"{k}.{sub_k}"] = sub_v if not isinstance(sub_v, (dict, list)) else json.dumps(sub_v)
        elif isinstance(v, list):
            flat[k] = "; ".join(str(i) for i in v)
        else:
            flat[k] = v
    return flat


def write_sheet(writer, sheet_name, records, flatten_records=True):
    if not records:
        pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"  {sheet_name}: 0 rows (empty)")
        return
    rows = [flatten(r) for r in records] if flatten_records else records
    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"  {sheet_name}: {len(df)} rows, {len(df.columns)} cols")


# ---------------------------------------------------------------------------
# 1. Raw search results
# ---------------------------------------------------------------------------
print("Writing Raw_Search_Results.xlsx ...")
raw_path = BASE / "output" / "excel" / "Raw_Search_Results.xlsx"
with pd.ExcelWriter(raw_path, engine="openpyxl") as writer:
    for db in ("openalex", "crossref", "epmc", "s2"):
        src = BASE / "data" / "01_raw" / f"{db}.jsonl"
        records = read_jsonl(src) if src.exists() else []
        write_sheet(writer, db.upper(), records)

# ---------------------------------------------------------------------------
# 2. Corpus + prefiltered
# ---------------------------------------------------------------------------
print("Writing Corpus.xlsx ...")
with pd.ExcelWriter(OUT / "Corpus.xlsx", engine="openpyxl") as writer:
    write_sheet(writer, "Corpus",      read_jsonl(BASE / "data" / "02_deduped" / "corpus.jsonl"))
    write_sheet(writer, "Prefiltered", read_jsonl(BASE / "data" / "02_deduped" / "prefiltered.jsonl"))

# ---------------------------------------------------------------------------
# 3. Screening decisions
# ---------------------------------------------------------------------------
print("Writing Screening_Decisions.xlsx ...")
with pd.ExcelWriter(OUT / "Screening_Decisions.xlsx", engine="openpyxl") as writer:
    write_sheet(writer, "Decisions", read_jsonl(BASE / "data" / "03_screened" / "decisions.jsonl"))

# ---------------------------------------------------------------------------
# 4. Extraction
# ---------------------------------------------------------------------------
print("Writing Extraction.xlsx ...")
with pd.ExcelWriter(OUT / "Extraction.xlsx", engine="openpyxl") as writer:
    write_sheet(writer, "Extraction", read_jsonl(BASE / "data" / "05_extracted" / "extraction.jsonl"))

# ---------------------------------------------------------------------------
# 5. Quality assessment
# ---------------------------------------------------------------------------
print("Writing Quality_MMAT.xlsx ...")
with pd.ExcelWriter(OUT / "Quality_MMAT.xlsx", engine="openpyxl") as writer:
    write_sheet(writer, "Quality_MMAT", read_jsonl(BASE / "data" / "05_extracted" / "quality.jsonl"))

# ---------------------------------------------------------------------------
# 6. Combined workbook
# ---------------------------------------------------------------------------
print("Writing slr_data.xlsx (combined) ...")
with pd.ExcelWriter(OUT / "slr_data.xlsx", engine="openpyxl") as writer:
    write_sheet(writer, "Raw_OpenAlex",  read_jsonl(BASE / "data" / "01_raw" / "openalex.jsonl"))
    write_sheet(writer, "Raw_CrossRef",  read_jsonl(BASE / "data" / "01_raw" / "crossref.jsonl"))
    write_sheet(writer, "Raw_EuropePMC", read_jsonl(BASE / "data" / "01_raw" / "epmc.jsonl"))
    write_sheet(writer, "Corpus",        read_jsonl(BASE / "data" / "02_deduped" / "corpus.jsonl"))
    write_sheet(writer, "Screening",     read_jsonl(BASE / "data" / "03_screened" / "decisions.jsonl"))
    write_sheet(writer, "Extraction",    read_jsonl(BASE / "data" / "05_extracted" / "extraction.jsonl"))
    write_sheet(writer, "Quality_MMAT",  read_jsonl(BASE / "data" / "05_extracted" / "quality.jsonl"))

# ---------------------------------------------------------------------------
# 7. Delete all paper-record JSONL files
# ---------------------------------------------------------------------------
print("\nDeleting paper-record JSONL files ...")

to_delete_files = [
    BASE / "data" / "01_raw" / "openalex.jsonl",
    BASE / "data" / "01_raw" / "crossref.jsonl",
    BASE / "data" / "01_raw" / "epmc.jsonl",
    BASE / "data" / "01_raw" / "s2.jsonl",
    BASE / "data" / "02_deduped" / "corpus.jsonl",
    BASE / "data" / "02_deduped" / "prefiltered.jsonl",
    BASE / "data" / "03_screened" / "decisions.jsonl",
    BASE / "data" / "05_extracted" / "extraction.jsonl",
    BASE / "data" / "05_extracted" / "quality.jsonl",
]

to_delete_dirs = [
    BASE / "data" / "02_deduped" / "chunks",
    BASE / "data" / "03_screened" / "batches",
]

for p in to_delete_files:
    if p.exists():
        p.unlink()
        print(f"  deleted {p.relative_to(BASE)}")
    else:
        print(f"  skipped (not found): {p.relative_to(BASE)}")

for d in to_delete_dirs:
    if d.exists():
        shutil.rmtree(d)
        print(f"  deleted dir {d.relative_to(BASE)}/")
    else:
        print(f"  skipped (not found): {d.relative_to(BASE)}/")

print("\nDone. Excel files in output/excel/")
print("Kept: data/01_raw/queries.json, output/prisma_counts.json, .claude/settings.json")
