#!/usr/bin/env python3
"""
Extract structured data from full-text biotech/platform strategy papers.
Process 53 papers from data/04_full_text/, write JSONL to data/05_extracted/extraction.jsonl
"""

import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configuration
INPUT_DIR = Path("data/04_full_text")
OUTPUT_DIR = Path("data/05_extracted")
OUTPUT_FILE = OUTPUT_DIR / "extraction.jsonl"
PRISMA_COUNTS = Path("output/prisma_counts.json")

# Create output directory if needed
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_doi(text: str) -> Optional[str]:
    """Extract DOI from text."""
    patterns = [
        r"DOI\s*:\s*(10\.\d+/[\S]+)",
        r"https://doi\.org/(10\.\d+/[\S]+)",
        r"(10\.\d+/[\S]+?)[\s\n]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doi = match.group(1).strip().rstrip(".,;)")
            return doi
    return None


def extract_authors(text: str) -> Optional[str]:
    """Extract first few authors from top of document."""
    # Look for common author patterns in first 2000 chars
    first_section = text[:3000]

    # Pattern 1: "FirstName LastName, FirstName LastName and FirstName LastName"
    pattern1 = r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?)"

    # Pattern 2: Look for "Author: Name" or "Authors: Names"
    pattern2 = r"Author[s]?[\s:]*([A-Za-z\s,&]+?)(?:\n|Institution|Affiliation)"

    match = re.search(pattern2, first_section, re.IGNORECASE)
    if match:
        authors = match.group(1).strip()
        # Take first ~3 author names
        author_list = [a.strip() for a in re.split(r',|and|&', authors)]
        authors = ", ".join(author_list[:3])
        return authors if authors else None

    return None


def extract_year(text: str) -> Optional[str]:
    """Extract 4-digit year, prioritize recent years and publication contexts."""
    patterns = [
        r"Published\s*:\s*(\d{1,2})\s+\w+\s+(\d{4})",
        r"Date\s*:\s*(\d{4})",
        r"First Online\s*:\s*\d{1,2}\s+\w+\s+(\d{4})",
        r"©\s*(\d{4})\s",
        r"\b(\d{4})\s+(?:Springer|Elsevier|Published|Release)",
    ]

    years_found = []
    for pattern in patterns:
        matches = re.findall(pattern, text[:5000])
        for match in matches:
            if isinstance(match, tuple):
                year = match[-1]  # Get last group (year)
            else:
                year = match
            if year.isdigit() and 1990 <= int(year) <= 2030:
                years_found.append(int(year))

    if years_found:
        # Return most recent year found
        return str(max(years_found))

    return None


def extract_venue(text: str) -> Optional[str]:
    """Extract journal/conference venue name."""
    patterns = [
        r"(?:Published in|Journal|Journal Name|Venue)\s*:\s*([^\n]+)",
        r"(?:Journal|Conference)\s+([^\n]+?)(?:\n|,|©)",
        r"(?:volume|vol\.)\s+\d+.*?([A-Z][^\n]{10,50}?)(?:\n|\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text[:3000], re.IGNORECASE)
        if match:
            venue = match.group(1).strip()
            # Clean up common junk
            venue = re.sub(r"^\d+\s+|pp\.\s+\d+.*$", "", venue).strip()
            if len(venue) > 5 and len(venue) < 200:
                return venue

    # Try to extract from "Advances in..." or journal titles
    if "Advances in" in text[:2000]:
        match = re.search(r"(Advances in [^\n]+?)(?:\n|,|vol\.)", text[:2000])
        if match:
            return match.group(1).strip()

    return None


def extract_theoretical_lens(text: str) -> Optional[str]:
    """Extract theoretical framework or lens."""
    keywords = {
        "resource-based view": [r"resource.?based\s+view", r"RBV"],
        "dynamic capabilities": [r"dynamic\s+capabilities?"],
        "platform theory": [r"platform\s+theory", r"platform\s+economy", r"platform\s+strategies?"],
        "ecosystem": [r"\becosystem(?:s)?\b"],
        "transaction cost": [r"transaction\s+cost\s+economics?", r"TCE"],
        "institutional theory": [r"institutional\s+(?:theory|logic)"],
        "network effects": [r"network\s+effects?"],
    }

    text_lower = text.lower()
    for lens, patterns in keywords.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return lens

    return None


def extract_method(text: str) -> Optional[str]:
    """Classify research method."""
    text_lower = text.lower()

    method_keywords = {
        "case study": [r"\bcase\s+stud(?:y|ies)\b", r"case\s+study\s+(?:of|on)"],
        "regression": [r"\b(?:multiple\s+)?regression\b", r"OLS|panel\s+regression"],
        "panel data": [r"panel\s+data", r"fixed.?effects?"],
        "event study": [r"event\s+study"],
        "conceptual": [r"conceptual\s+(?:model|framework|paper)"],
        "qualitative": [r"\bqualitative\s+(?:method|analysis|research)", r"thematic\s+analysis"],
        "quantitative": [r"\bquantitative\s+(?:method|analysis|research)", r"statistical\s+analysis"],
        "mixed method": [r"mixed\s+method"],
        "survey": [r"\bsurvey\b", r"questionnaire"],
        "interview": [r"\binterview[s]?\b"],
    }

    # Check for primary method type
    for method, patterns in method_keywords.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return method

    return None


def extract_sample(text: str) -> Dict[str, Any]:
    """Extract sample information: n_firms, geography, period."""
    result = {"n_firms": None, "geography": None, "period": None}

    # Extract sample size
    patterns = [
        r"(?:N\s*=\s*|sample\s+of\s+|sample\s+included\s+)(\d+)\s+(?:firms?|companies?|organizations?)",
        r"(\d+)\s+(?:firms?|companies?|organizations?)\s+(?:were|participated|included)",
    ]

    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            n = match.group(1)
            result["n_firms"] = int(n)
            break

    # Extract geography
    countries = ["United States", "USA", "China", "Europe", "Germany", "UK", "Canada",
                 "Japan", "India", "Brazil", "Australia"]
    for country in countries:
        if country.lower() in text_lower[:3000]:
            result["geography"] = country
            break

    # Extract period/year range
    year_pattern = r"(\d{4})\s*-\s*(\d{4})"
    match = re.search(year_pattern, text)
    if match:
        result["period"] = f"{match.group(1)}-{match.group(2)}"

    return result


def extract_platform_definition(text: str) -> Optional[str]:
    """Extract explicit platform definition."""
    patterns = [
        r"(?:we\s+define|define|platform\s+is\s+defined\s+as)\s+['\"]?([^'\"\.;\n]{30,300})['\"]?[\.\n]",
        r"(?:platform|Platform)\s+(?:is\s+)?(?:defined\s+as|refers\s+to)\s+([^\.;\n]{30,300})\.",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            definition = match.group(1).strip()
            if len(definition) > 20:
                return definition

    return None


def extract_platform_type(text: str) -> Optional[str]:
    """Classify platform type based on keywords."""
    text_lower = text.lower()

    types = {
        "technology": [r"\btechnology\s+platform\b", r"technology.?driven\s+platform"],
        "multi-sided": [r"multi.?sided\s+platform", r"multi.?platform", r"two.?sided\s+market"],
        "modular": [r"modular\s+platform", r"modular\s+architecture"],
        "R&D": [r"R&D\s+platform", r"research\s+and\s+development\s+platform"],
    }

    for ptype, patterns in types.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return ptype

    # Default to 'other' if any platform mention but no specific type
    if "platform" in text_lower:
        return "other"

    return None


def extract_outcomes(text: str) -> List[str]:
    """Extract outcome variables measured."""
    outcomes_map = {
        "innovation": [r"\binnovation\b", r"innovative\s+(?:product|capability)"],
        "performance": [r"\bperformance\b", r"financial\s+performance"],
        "valuation": [r"\bvaluation\b", r"firm\s+value"],
        "partnership": [r"\bpartnership[s]?\b", r"partnership\s+formation"],
        "alliance": [r"\balliance[s]?\b"],
        "survival": [r"\bsurvival\b", r"firm\s+survival"],
        "growth": [r"\bgrowth\b", r"revenue\s+growth"],
        "competitive advantage": [r"competitive\s+advantage", r"sustained\s+advantage"],
    }

    outcomes = []
    text_lower = text.lower()

    for outcome, patterns in outcomes_map.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                outcomes.append(outcome)
                break

    return outcomes if outcomes else []


def extract_effect_direction(text: str) -> Optional[str]:
    """Infer effect direction from text."""
    text_lower = text.lower()

    positive_patterns = [
        r"(?:positive|significantly|strongly|increase[sd]?|improve[sd]?|enhance[sd]?|boost[sd]?)\s+(?:effect|impact|relationship)",
        r"(?:lead[s]?\s+to|result[s]?\s+in)\s+(?:higher|greater|improved|positive)",
    ]

    negative_patterns = [
        r"(?:negative|significantly|decreases?|reduces?|inhibit[s]?|lower[s]?|diminish[es]?)\s+(?:effect|impact|relationship)",
        r"(?:lead[s]?\s+to|result[s]?\s+in)\s+(?:lower|fewer|negative|decline)",
    ]

    # Check for explicit mentions
    for pattern in positive_patterns:
        if re.search(pattern, text_lower):
            return "positive"

    for pattern in negative_patterns:
        if re.search(pattern, text_lower):
            return "negative"

    # Check for conditional language
    if re.search(r"(?:depend[s]?\s+on|contingent\s+on|conditional\s+on|moderat[ed|ing])", text_lower):
        return "conditional"

    if re.search(r"(?:mixed|both\s+positive\s+and\s+negative)", text_lower):
        return "mixed"

    return None


def extract_effect_summary(text: str) -> Optional[str]:
    """Extract key finding or conclusion sentence."""
    # Look for abstract or conclusion sections
    patterns = [
        r"(?:Abstract|ABSTRACT)(.*?)(?:Keywords|KEYWORDS|Introduction|INTRODUCTION)",
        r"(?:Conclusion|CONCLUSION)(.*?)(?:References|REFERENCES|$)",
        r"(?:findings?|finding)[:\s]+([^\.]{30,300})\.",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            section = match.group(1).strip()
            # Extract first substantial sentence
            sentences = re.split(r'[\.!\?]\s+', section)
            for sent in sentences:
                sent = sent.strip()
                if len(sent) > 50 and len(sent) < 300:
                    return sent

    return None


def extract_boundary_conditions(text: str) -> List[str]:
    """Extract boundary conditions or moderating factors."""
    conditions = []

    patterns = [
        r"(?:boundary\s+condition|moderating|moderator|contingent\s+(?:on|upon)|when|if).*?([A-Za-z\s]{20,150}?)(?:[\.\n]|moderates?)",
    ]

    text_lower = text.lower()

    # Simple keyword search
    keywords = ["boundary condition", "moderating", "moderator", "contingent"]
    for keyword in keywords:
        if keyword in text_lower:
            conditions.append(keyword)

    return conditions if conditions else []


def extract_stated_gaps(text: str) -> List[str]:
    """Extract stated gaps or future research areas."""
    gaps = []

    patterns = [
        r"(?:future\s+research|gap|limitation|further\s+research|unclear)\s+(?:is|remains|include[s]?|are)\s+([^\.]{20,150})\.",
        r"(?:gap|limitation)[:\s]+([^\.]{20,150})\.",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            match = match.strip()
            if len(match) > 10 and match not in gaps:
                gaps.append(match)

    return gaps[:3] if gaps else []  # Return top 3


def process_file(filepath: Path) -> Dict[str, Any]:
    """Process a single file and extract all structured data."""

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return {"id": filepath.stem, "extraction_status": "read_error"}

    # Check if text is sufficient
    if len(text) < 1000:
        return {
            "id": filepath.stem,
            "extraction_status": "insufficient_text",
            "doi": None,
            "authors": None,
            "year": None,
            "venue": None,
            "theoretical_lens": None,
            "method": None,
            "sample": None,
            "platform_definition": None,
            "platform_type": None,
            "outcomes_measured": None,
            "effect_direction": None,
            "effect_summary": None,
            "boundary_conditions": None,
            "stated_gaps": None,
            "notable_quotes": None,
        }

    # Extract all fields
    return {
        "id": filepath.stem,
        "extraction_status": "extracted",
        "doi": extract_doi(text),
        "authors": extract_authors(text),
        "year": extract_year(text),
        "venue": extract_venue(text),
        "theoretical_lens": extract_theoretical_lens(text),
        "method": extract_method(text),
        "sample": extract_sample(text),
        "platform_definition": extract_platform_definition(text),
        "platform_type": extract_platform_type(text),
        "outcomes_measured": extract_outcomes(text),
        "effect_direction": extract_effect_direction(text),
        "effect_summary": extract_effect_summary(text),
        "boundary_conditions": extract_boundary_conditions(text),
        "stated_gaps": extract_stated_gaps(text),
        "notable_quotes": [],
    }


def main():
    """Main execution: process all files and write output."""

    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Find all .txt files
    txt_files = sorted([
        f for f in INPUT_DIR.glob("*.txt")
        if f.name not in ["_status.jsonl", ".gitkeep"]
    ])

    print(f"Found {len(txt_files)} files to process")

    total = 0
    extracted = 0
    insufficient = 0

    # Process all files
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outf:
        for filepath in txt_files:
            print(f"Processing {filepath.name}...", end=" ")

            result = process_file(filepath)
            outf.write(json.dumps(result) + "\n")

            total += 1
            if result.get("extraction_status") == "insufficient_text":
                insufficient += 1
                print("INSUFFICIENT")
            elif result.get("extraction_status") == "extracted":
                extracted += 1
                print("OK")
            else:
                print(f"ERROR: {result.get('extraction_status')}")

    print("\n" + "="*60)
    print(f"EXTRACTION COMPLETE")
    print(f"Total files: {total}")
    print(f"Successfully extracted: {extracted}")
    print(f"Insufficient text: {insufficient}")
    print(f"Output written to: {OUTPUT_FILE}")

    # Update PRISMA counts
    try:
        with open(PRISMA_COUNTS, 'r') as f:
            counts = json.load(f)
    except:
        counts = []

    # Add or update the extracted phase
    counts = [c for c in counts if c.get("phase") != "extracted"]
    counts.append({"phase": "extracted", "n": extracted})

    with open(PRISMA_COUNTS, 'w') as f:
        json.dump(counts, f, indent=2)

    print(f"Updated {PRISMA_COUNTS}")
    print("="*60)


if __name__ == "__main__":
    main()
