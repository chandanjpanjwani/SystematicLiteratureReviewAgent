#!/usr/bin/env python3
"""
MMAT 2018 Quality Assessment for Mixed Methods Appraisal Tool
Applied to systematic literature review on biotech platform strategies.

Reads extracted papers and their full texts, applies MMAT criteria via keyword heuristics.
Outputs quality scores and summary statistics.
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import re

# Configuration
EXTRACTION_FILE = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent\data\05_extracted\extraction.jsonl"
FULL_TEXT_DIR = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent\data\04_full_text"
OUTPUT_FILE = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent\data\05_extracted\quality.jsonl"
PRISMA_FILE = r"C:\Users\cpanj\OneDrive\Desktop\DTE\AgenticAI\slr-agent\output\prisma_counts.json"


def map_method_to_category(method):
    """
    Map extracted method field to MMAT category.

    Returns: "qualitative", "qnt_descriptive", "qnt_nonrandomized", "mixed", or None
    """
    if method is None:
        return "qualitative"  # Default, note uncertainty

    method_lower = method.lower()

    # Qualitative
    if any(kw in method_lower for kw in ["qualitative", "case study", "case", "grounded theory",
                                           "ethnography", "phenomenology", "interview"]):
        return "qualitative"

    # Quantitative Descriptive
    if any(kw in method_lower for kw in ["quantitative panel", "panel", "survey", "descriptive"]):
        return "qnt_descriptive"

    # Quantitative Non-randomized
    if any(kw in method_lower for kw in ["event study", "event", "quasi-experiment", "experiment"]):
        return "qnt_nonrandomized"

    # Mixed Methods
    if any(kw in method_lower for kw in ["mixed method", "mixed methods", "mixed"]):
        return "mixed"

    # Regression is ambiguous but usually quantitative
    if "regression" in method_lower:
        return "qnt_descriptive"

    # Conceptual maps to qualitative
    if "conceptual" in method_lower:
        return "qualitative"

    # Default
    return "qualitative"


def read_full_text(paper_id):
    """
    Read full text from file. Returns text content or empty string if file not found.
    """
    filepath = os.path.join(FULL_TEXT_DIR, f"{paper_id}.txt")
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except FileNotFoundError:
        return ""


def score_qualitative(text):
    """
    Score qualitative research paper on 5 MMAT criteria.

    Q1: Appropriate approach? (1=keywords present, 0.5=method section exists, 0=no)
    Q2: Adequate data collection? (1=specific methods, 0.5=sources vague, 0=no)
    Q3: Adequate derivation? (1=coding/analysis keywords, 0.5=analysis section, 0=no)
    Q4: Interpretation substantiated? (1=quotes/evidence, 0.5=findings reference data, 0=no)
    Q5: Coherence? (1=RQ+method+findings alignment, 0.5=partial, 0=no)
    """
    text_lower = text.lower()
    scores = {}

    # Q1: Appropriate approach
    if any(kw in text_lower for kw in ["qualitative", "case study", "case analysis",
                                         "grounded theory", "ethnography", "phenomenology"]):
        scores['q1'] = 1.0
    elif re.search(r'(method|approach)\s*(section|chapter)', text_lower):
        scores['q1'] = 0.5
    else:
        scores['q1'] = 0.0

    # Q2: Adequate data collection
    if any(kw in text_lower for kw in ["interview", "interviews", "focus group", "focus groups",
                                         "observation", "observational", "document analysis",
                                         "archival", "archive", "data collection"]):
        scores['q2'] = 1.0
    elif any(kw in text_lower for kw in ["data source", "source of data", "primary data", "secondary data"]):
        scores['q2'] = 0.5
    else:
        scores['q2'] = 0.0

    # Q3: Adequate derivation of findings
    if any(kw in text_lower for kw in ["coding", "coded", "thematic analysis", "content analysis",
                                         "grounded theory analysis", "constant comparison"]):
        scores['q3'] = 1.0
    elif re.search(r'(analysis|analytic)\s*(section|chapter|method)', text_lower):
        scores['q3'] = 0.5
    else:
        scores['q3'] = 0.0

    # Q4: Interpretation substantiated with evidence
    if any(kw in text_lower for kw in ["quote", "quotes", "quoted", "excerpt", "excerpts",
                                         "verbatim", "illustrat", "evidence", "example"]):
        scores['q4'] = 1.0
    elif re.search(r'(finding|result|conclusion)\s+.{0,100}(data|evidence|support)', text_lower):
        scores['q4'] = 0.5
    else:
        scores['q4'] = 0.0

    # Q5: Coherence - RQ + method + findings alignment
    # Approximate: text length > 10000 chars + contains both method and finding sections
    has_method = any(kw in text_lower for kw in ["method", "methodology", "approach"])
    has_findings = any(kw in text_lower for kw in ["finding", "findings", "result", "results", "conclusion"])
    has_rq = any(kw in text_lower for kw in ["research question", "research objective", "research aim"])

    if len(text) > 10000 and has_method and has_findings and has_rq:
        scores['q5'] = 1.0
    elif (len(text) > 5000 and has_method and has_findings) or (len(text) > 8000 and has_findings):
        scores['q5'] = 0.5
    else:
        scores['q5'] = 0.0

    return scores


def score_qnt_descriptive(text):
    """
    Score quantitative descriptive research on 5 MMAT criteria.

    Q1: Relevant sampling? (1=sample/N mentioned, 0.5=partial, 0=no)
    Q2: Representative sample? (1=random/stratified/census, 0.5=described but unclear, 0=no)
    Q3: Appropriate measurements? (1=variable/measure/indicator, 0.5=partial, 0=no)
    Q4: Low non-response bias? (1=response rate, 0.5=sample size, 0=no)
    Q5: Appropriate statistical analysis? (1=regression/correlation/p-value, 0.5=partial, 0=no)
    """
    text_lower = text.lower()
    scores = {}

    # Q1: Relevant sampling
    if any(kw in text_lower for kw in ["sample", "sampling", "population", "firms", "companies", "n="]):
        scores['q1'] = 1.0
    elif any(kw in text_lower for kw in ["participants", "respondents"]):
        scores['q1'] = 0.5
    else:
        scores['q1'] = 0.0

    # Q2: Representative sample
    if any(kw in text_lower for kw in ["random", "randomized", "representative", "stratified", "census"]):
        scores['q2'] = 1.0
    elif any(kw in text_lower for kw in ["sample design", "sampling method", "sampling strategy"]):
        scores['q2'] = 0.5
    else:
        scores['q2'] = 0.0

    # Q3: Appropriate measurements
    if any(kw in text_lower for kw in ["variable", "variables", "measure", "measurement", "indicator",
                                         "scale", "proxy", "proxies"]):
        scores['q3'] = 1.0
    elif any(kw in text_lower for kw in ["metric", "data collection"]):
        scores['q3'] = 0.5
    else:
        scores['q3'] = 0.0

    # Q4: Low non-response bias
    if any(kw in text_lower for kw in ["response rate", "non-response", "response bias", "attrition"]):
        scores['q4'] = 1.0
    elif any(kw in text_lower for kw in ["sample size", "n="]):
        scores['q4'] = 0.5
    else:
        scores['q4'] = 0.0

    # Q5: Appropriate statistical analysis
    if any(kw in text_lower for kw in ["regression", "correlation", "anova", "t-test", "significance",
                                         "p-value", "p <", "coefficient", "statistical test"]):
        scores['q5'] = 1.0
    elif any(kw in text_lower for kw in ["analysis", "analyzed", "statistical"]):
        scores['q5'] = 0.5
    else:
        scores['q5'] = 0.0

    return scores


def score_qnt_nonrandomized(text):
    """
    Score quantitative non-randomized (quasi-experimental) research.
    Similar to descriptive but emphasizes control/comparison groups and temporal design.
    """
    text_lower = text.lower()
    scores = {}

    # Q1: Relevant sampling (including treatment/control)
    if any(kw in text_lower for kw in ["control group", "comparison group", "treatment group", "sample", "firms"]):
        scores['q1'] = 1.0
    elif any(kw in text_lower for kw in ["participants", "sample"]):
        scores['q1'] = 0.5
    else:
        scores['q1'] = 0.0

    # Q2: Representative sample / equivalent groups
    if any(kw in text_lower for kw in ["matched", "propensity", "comparable", "equivalent", "random assignment"]):
        scores['q2'] = 1.0
    elif any(kw in text_lower for kw in ["sample design", "control"]):
        scores['q2'] = 0.5
    else:
        scores['q2'] = 0.0

    # Q3: Appropriate measurements
    if any(kw in text_lower for kw in ["variable", "measure", "indicator", "outcome"]):
        scores['q3'] = 1.0
    elif any(kw in text_lower for kw in ["metric", "measurement"]):
        scores['q3'] = 0.5
    else:
        scores['q3'] = 0.0

    # Q4: Adequate intervention integrity / temporal design
    if any(kw in text_lower for kw in ["before-after", "pre-post", "pre and post", "intervention",
                                         "treatment effect", "treatment timing"]):
        scores['q4'] = 1.0
    elif any(kw in text_lower for kw in ["time", "period", "change"]):
        scores['q4'] = 0.5
    else:
        scores['q4'] = 0.0

    # Q5: Appropriate statistical analysis
    if any(kw in text_lower for kw in ["difference-in-differences", "dif-in-dif", "regression", "correlation",
                                         "p-value", "coefficient", "significance test"]):
        scores['q5'] = 1.0
    elif any(kw in text_lower for kw in ["statistical", "analysis", "test"]):
        scores['q5'] = 0.5
    else:
        scores['q5'] = 0.0

    return scores


def score_mixed_methods(text):
    """
    Score mixed methods research on 5 MMAT criteria.

    Q1: Rationale for mixed? (1=mixed method explicitly justified, 0.5=just mentioned, 0=no)
    Q2: Components effectively integrated? (1=triangulation/convergent language, 0.5=both present, 0=no)
    Q3: Adequate interpretation of qual? (1=qual interpretation substantiated, 0.5=qual present, 0=no)
    Q4: Adequate interpretation of quant? (1=statistical analysis rigorous, 0.5=present, 0=no)
    Q5: Divergences addressed? (1=explicitly discusses, 0.5=addresses limitations, 0=no)
    """
    text_lower = text.lower()
    scores = {}

    # Q1: Rationale for mixed methods
    if any(kw in text_lower for kw in ["mixed method", "mixed methods"]):
        if any(kw in text_lower for kw in ["rationale", "justify", "justification", "strength", "complement"]):
            scores['q1'] = 1.0
        else:
            scores['q1'] = 0.5
    else:
        scores['q1'] = 0.0

    # Q2: Components effectively integrated
    if any(kw in text_lower for kw in ["triangulation", "convergent", "integration", "integrated",
                                         "mixed analysis", "combined"]):
        scores['q2'] = 1.0
    else:
        # Check if both qual and quant elements present
        has_qual = any(kw in text_lower for kw in ["interview", "qualitative", "thematic"])
        has_quant = any(kw in text_lower for kw in ["regression", "quantitative", "statistical"])
        scores['q2'] = 0.5 if (has_qual and has_quant) else 0.0

    # Q3: Adequate interpretation of qualitative component
    qual_scores = score_qualitative(text)
    scores['q3'] = qual_scores['q3']  # Use derivation of findings as proxy

    # Q4: Adequate interpretation of quantitative component
    quant_scores = score_qnt_descriptive(text)
    scores['q4'] = quant_scores['q5']  # Use statistical analysis as proxy

    # Q5: Divergences/inconsistencies addressed
    if any(kw in text_lower for kw in ["discrepan", "divergen", "inconsisten", "conflict", "contradiction"]):
        scores['q5'] = 1.0
    elif any(kw in text_lower for kw in ["limitation", "limitations", "challenge"]):
        scores['q5'] = 0.5
    else:
        scores['q5'] = 0.0

    return scores


def score_paper(paper_id, method_category, text):
    """
    Score a paper based on its method category using appropriate MMAT criteria.
    Returns dict with scores and notes.
    """
    if not text or len(text) < 100:
        # Insufficient text - return neutral scores
        return {
            'scores': {'q1': 0.5, 'q2': 0.5, 'q3': 0.5, 'q4': 0.5, 'q5': 0.5},
            'total': 2.5,
            'notes': 'Insufficient text - file unreadable or too short'
        }

    if method_category == "qualitative":
        scores = score_qualitative(text)
    elif method_category == "qnt_descriptive":
        scores = score_qnt_descriptive(text)
    elif method_category == "qnt_nonrandomized":
        scores = score_qnt_nonrandomized(text)
    elif method_category == "mixed":
        scores = score_mixed_methods(text)
    else:
        # Default to qualitative if category unclear
        scores = score_qualitative(text)

    total = sum(scores.values())

    # Generate notes for papers with low scores
    low_score_criteria = [k for k, v in scores.items() if v < 0.5]
    notes = ""
    if low_score_criteria:
        notes = f"Low scores on: {', '.join(low_score_criteria)}"

    return {
        'scores': scores,
        'total': total,
        'notes': notes
    }


def main():
    print("=" * 80)
    print("MMAT 2018 QUALITY ASSESSMENT - Biotech Platform Strategies SLR")
    print("=" * 80)

    # Read extraction file
    papers = []
    with open(EXTRACTION_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    paper = json.loads(line)
                    papers.append(paper)
                except json.JSONDecodeError as e:
                    print(f"ERROR: Line {line_num} - Invalid JSON: {e}")
                    continue

    print(f"\nLoaded {len(papers)} papers from extraction.jsonl")

    # Filter out papers with insufficient_text status
    papers_to_score = [p for p in papers if p.get('extraction_status') != 'insufficient_text']
    skipped = len(papers) - len(papers_to_score)
    if skipped > 0:
        print(f"Skipped {skipped} papers with extraction_status == 'insufficient_text'")

    print(f"Scoring {len(papers_to_score)} papers\n")

    # Score each paper
    results = []
    method_categories = defaultdict(int)
    scores_by_criterion = defaultdict(list)
    file_read_errors = []

    for i, paper in enumerate(papers_to_score, 1):
        paper_id = paper.get('id')
        original_method = paper.get('method')
        extraction_status = paper.get('extraction_status')

        # Determine method category
        method_category = map_method_to_category(original_method)
        method_categories[method_category] += 1

        # Read full text
        text = read_full_text(paper_id)
        if not text:
            file_read_errors.append(paper_id)

        # Score paper
        assessment = score_paper(paper_id, method_category, text)

        # Build result
        result = {
            'id': paper_id,
            'method_category': method_category,
            'scores': assessment['scores'],
            'total': assessment['total'],
            'notes': assessment['notes'] if assessment['notes'] else None
        }

        results.append(result)

        # Track scores by criterion
        for criterion, score in assessment['scores'].items():
            scores_by_criterion[criterion].append(score)

        # Progress indicator
        if i % 10 == 0:
            print(f"  Processed {i}/{len(papers_to_score)} papers...")

    # Write output
    output_dir = os.path.dirname(OUTPUT_FILE)
    os.makedirs(output_dir, exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    print(f"\nWrote quality scores to {OUTPUT_FILE}")

    # Update prisma_counts.json
    with open(PRISMA_FILE, 'r', encoding='utf-8') as f:
        prisma_data = json.load(f)

    # Check if included_final phase already exists
    phase_exists = any(p.get('phase') == 'included_final' for p in prisma_data)
    if not phase_exists:
        prisma_data.append({'phase': 'included_final', 'n': len(papers_to_score)})

    with open(PRISMA_FILE, 'w', encoding='utf-8') as f:
        json.dump(prisma_data, f, indent=2)

    print(f"Updated {PRISMA_FILE}")

    # Print summary statistics
    print("\n" + "=" * 80)
    print("QUALITY ASSESSMENT SUMMARY")
    print("=" * 80)

    print(f"\nTotal papers assessed: {len(results)}")
    print(f"File read errors: {len(file_read_errors)}")
    if file_read_errors:
        print(f"  Papers: {', '.join(file_read_errors[:5])}")
        if len(file_read_errors) > 5:
            print(f"  ... and {len(file_read_errors) - 5} more")

    print(f"\nMethod category distribution:")
    for category in sorted(method_categories.keys()):
        count = method_categories[category]
        pct = 100 * count / len(results)
        print(f"  {category:20s}: {count:3d} ({pct:5.1f}%)")

    print(f"\nQuality score summary (by criterion):")
    all_totals = []
    for criterion in sorted(scores_by_criterion.keys()):
        scores = scores_by_criterion[criterion]
        avg = sum(scores) / len(scores)
        min_s = min(scores)
        max_s = max(scores)
        print(f"  {criterion}: avg={avg:.2f}, min={min_s:.1f}, max={max_s:.1f}")
        if criterion == 'q5':
            all_totals = [sum([scores_by_criterion[c][i] for c in ['q1', 'q2', 'q3', 'q4', 'q5']])
                         for i in range(len(scores))]

    if all_totals:
        avg_total = sum(all_totals) / len(all_totals)
        min_total = min(all_totals)
        max_total = max(all_totals)
        print(f"\nOverall quality scores:")
        print(f"  Average total score: {avg_total:.2f} / 5.0")
        print(f"  Min total score: {min_total:.1f}")
        print(f"  Max total score: {max_total:.1f}")

    # Score distribution
    print(f"\nTotal score distribution:")
    score_bins = defaultdict(int)
    for result in results:
        total = result['total']
        bin_label = f"{int(total*2)/2:.1f}"  # Round to nearest 0.5
        score_bins[bin_label] += 1

    for bin_label in sorted(score_bins.keys(), key=float):
        count = score_bins[bin_label]
        bar = "*" * count
        print(f"  {bin_label:4s}: {bar} ({count})")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
