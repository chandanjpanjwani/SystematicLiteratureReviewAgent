#!/usr/bin/env python3
"""Master executor - runs the prefilter and reports results"""
import subprocess
import sys
import os

os.chdir('/home/npdrpi1/ClaudeAgents/slr-agent-master')

print("Starting prefilter execution...")
result = subprocess.run([sys.executable, 'final_prefilter.py'], capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

sys.exit(result.returncode)
