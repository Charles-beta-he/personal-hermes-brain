#!/usr/bin/env python3
"""
_extract_plan_json.py — Claude Code output → JSON plan extractor

Takes the Claude Code --output-format json output and extracts
the plan JSON, handling multiple wrapper formats.

Usage: _extract_plan_json.py <input_file> <output_file>
"""
import sys, json, re

def extract(raw_text):
    # Try 1: direct parse — only accept if it has 'steps' (actual plan)
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and "steps" in data:
            return data
    except json.JSONDecodeError:
        pass

    # Try 2: Claude Code wrapped format (--output-format json)
    try:
        raw = json.loads(raw_text)
        inner = raw.get("result", raw.get("response", ""))
        if isinstance(inner, str):
            return json.loads(inner)
        elif isinstance(inner, dict):
            return inner
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    # Try 3: markdown ```json block
    block = re.search(r'```json\n?(.*?)```', raw_text, re.DOTALL)
    if block:
        try:
            return json.loads(block.group(1))
        except json.JSONDecodeError:
            pass

    # Try 4: markdown ``` block (no json tag, just code fence)
    block = re.search(r'```\n?(.*?)```', raw_text, re.DOTALL)
    if block:
        try:
            return json.loads(block.group(1))
        except json.JSONDecodeError:
            pass

    return {}

if __name__ == "__main__":
    infile = sys.argv[1]
    outfile = sys.argv[2]
    with open(infile) as f:
        raw = f.read()
    data = extract(raw)
    with open(outfile, "w") as f:
        json.dump(data, f, indent=2)
