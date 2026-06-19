#!/usr/bin/env python3
"""Generate a PRISMA 2020 flow diagram as SVG from output/prisma_counts.json.

No external dependencies — emits raw SVG.
"""
import argparse
import json
from pathlib import Path


def get(counts: dict, phase: str, default: int = 0) -> int:
    return counts.get(phase, default)


def box(x: int, y: int, w: int, h: int, text: str) -> str:
    lines = text.split("\n")
    lh = 18
    ty = y + (h - lh * len(lines)) // 2 + 14
    tspans = "".join(
        f'<tspan x="{x + w // 2}" dy="{0 if i == 0 else lh}">{line}</tspan>'
        for i, line in enumerate(lines)
    )
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white" '
        f'stroke="#333" stroke-width="1.5" rx="4"/>'
        f'<text x="{x + w // 2}" y="{ty}" text-anchor="middle" '
        f'font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#111">{tspans}</text>'
    )


def arrow(x1: int, y1: int, x2: int, y2: int) -> str:
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#333" '
        f'stroke-width="1.5" marker-end="url(#arr)"/>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="output/prisma_counts.json")
    ap.add_argument("--out", default="output/prisma_flow.svg")
    args = ap.parse_args()

    # Read JSONL of count entries; collapse to a single dict keyed by phase.
    counts: dict[str, int] = {}
    p = Path(args.infile)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                counts[obj["phase"]] = obj["n"]
            except (json.JSONDecodeError, KeyError):
                continue

    identified_total = sum(
        v for k, v in counts.items() if k.startswith("identified_")
    )
    after_dedup = get(counts, "after_dedup")
    after_prefilter = get(counts, "after_prefilter")
    inc = get(counts, "screened_include")
    maybe = get(counts, "screened_maybe")
    exc = get(counts, "screened_exclude")
    fulltext = get(counts, "full_text_retrieved")
    extracted = get(counts, "extracted")
    final = get(counts, "included_final", extracted)

    # Layout
    W, H = 720, 920
    cx = W // 2
    bw, bh = 340, 70
    bx = cx - bw // 2

    boxes = []
    arrows = []

    y = 30
    boxes.append(box(bx, y, bw, bh, f"Records identified from databases\nn = {identified_total}"))
    y_prev = y + bh

    y += bh + 50
    boxes.append(box(bx, y, bw, bh, f"After duplicate removal\nn = {after_dedup}"))
    arrows.append(arrow(cx, y_prev, cx, y))
    # side note for dups removed
    dups = max(0, identified_total - after_dedup)
    boxes.append(box(bx + bw + 30, y, 180, bh, f"Duplicates removed\nn = {dups}"))
    arrows.append(arrow(bx + bw, y + bh // 2, bx + bw + 30, y + bh // 2))
    y_prev = y + bh

    y += bh + 50
    boxes.append(box(bx, y, bw, bh, f"After keyword pre-filter\nn = {after_prefilter}"))
    arrows.append(arrow(cx, y_prev, cx, y))
    boxes.append(box(bx + bw + 30, y, 180, bh, f"Pre-filter dropped\nn = {max(0, after_dedup - after_prefilter)}"))
    arrows.append(arrow(bx + bw, y + bh // 2, bx + bw + 30, y + bh // 2))
    y_prev = y + bh

    y += bh + 50
    boxes.append(box(bx, y, bw, bh, f"Title/abstract screened\nn = {after_prefilter}"))
    arrows.append(arrow(cx, y_prev, cx, y))
    boxes.append(box(bx + bw + 30, y, 180, bh, f"Excluded\nn = {exc}"))
    arrows.append(arrow(bx + bw, y + bh // 2, bx + bw + 30, y + bh // 2))
    y_prev = y + bh

    y += bh + 50
    boxes.append(box(bx, y, bw, bh, f"Sought for full text\nn = {inc + maybe}"))
    arrows.append(arrow(cx, y_prev, cx, y))
    y_prev = y + bh

    y += bh + 50
    boxes.append(box(bx, y, bw, bh, f"Full text retrieved\nn = {fulltext}"))
    arrows.append(arrow(cx, y_prev, cx, y))
    boxes.append(box(bx + bw + 30, y, 180, bh, f"Not retrievable\nn = {max(0, inc + maybe - fulltext)}"))
    arrows.append(arrow(bx + bw, y + bh // 2, bx + bw + 30, y + bh // 2))
    y_prev = y + bh

    y += bh + 50
    boxes.append(box(bx, y, bw, bh, f"Studies included in synthesis\nn = {final}"))
    arrows.append(arrow(cx, y_prev, cx, y))

    H = y + bh + 30

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">'
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#333"/></marker></defs>'
        '<rect width="100%" height="100%" fill="#fafafa"/>'
        + "".join(boxes)
        + "".join(arrows)
        + "</svg>"
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg)
    print(f"PRISMA flowchart written to {out}")


if __name__ == "__main__":
    main()
