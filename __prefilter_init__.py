import json, os
os.chdir('/home/npdrpi1/ClaudeAgents/slr-agent-master')
P = {"platform", "modular", "multi-sided", "two-sided", "ecosystem", "complementor"}
B = {"biotech", "biotechnology", "life sciences", "drug discovery", "therapeutic", "biopharma", "pharmaceutical", "diagnostic", "agbiotech", "industrial biotech", "synthetic biology"}
total_in = total_out = 0
with open("data/02_deduped/corpus.jsonl") as inf, open("data/02_deduped/prefiltered.jsonl", "w") as outf:
    for line in inf:
        total_in += 1
        try:
            r = json.loads(line)
            t, a = (r.get("title") or "").lower(), (r.get("abstract") or "").lower()
            if any(kw in t or kw in a for kw in P) or any(kw in t or kw in a for kw in B) or len((r.get("title") or "") + (r.get("abstract") or "")) >= 100:
                total_out += 1
                outf.write(json.dumps(r) + '\n')
        except:
            pass
drop = (total_in - total_out) / total_in * 100
with open("output/prisma_counts.json", "a") as f:
    json.dump({"phase": "after_prefilter", "n": total_out}, f)
    f.write('\n')
print(f"PREFILTER: In={total_in} Out={total_out} Drop={drop:.2f}%")
