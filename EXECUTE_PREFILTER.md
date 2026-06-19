# Prefilter Execution Instructions

## Location
All prefilter scripts are located in `/home/npdrpi1/ClaudeAgents/slr-agent-master/`

## Available Executable Scripts

1. **apply_prefilter.py** - Minimal, clean implementation
   ```bash
   cd /home/npdrpi1/ClaudeAgents/slr-agent-master
   python3 apply_prefilter.py
   ```

2. **streaming_prefilter.py** - Enhanced version with progress tracking
   ```bash
   cd /home/npdrpi1/ClaudeAgents/slr-agent-master
   python3 streaming_prefilter.py
   ```

3. **master_run.py** - Full-featured version with detailed reporting
   ```bash
   cd /home/npdrpi1/ClaudeAgents/slr-agent-master
   python3 master_run.py
   ```

4. **final_exec.py** - Inline, highly optimized version
   ```bash
   python3 /home/npdrpi1/final_exec.py
   ```

## Filter Logic

DROP only if ALL are true:
- No platform keyword: "platform", "modular", "multi-sided", "two-sided", "ecosystem", "complementor"
- No biotech keyword: "biotech", "biotechnology", "life sciences", "drug discovery", "therapeutic", "biopharma", "pharmaceutical", "diagnostic", "agbiotech", "industrial biotech", "synthetic biology"
- Combined title+abstract < 100 characters

Otherwise: KEEP

## Input Files
- `/home/npdrpi1/ClaudeAgents/slr-agent-master/data/02_deduped/corpus.jsonl` (5815 records)

## Output Files
- `/home/npdrpi1/ClaudeAgents/slr-agent-master/data/02_deduped/prefiltered.jsonl`
- `/home/npdrpi1/ClaudeAgents/slr-agent-master/output/prisma_counts.json` (appended with prefilter count)

## Expected Results
- Input: 5815 records
- Output: Approximately 3000-4000 records (60-65% drop rate expected)
- Drop Rate: Should be < 70%
