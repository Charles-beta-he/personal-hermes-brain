#!/usr/bin/env python3
"""Convert a research qualitative claim packet into a bounded dev validation task draft.

Default is dry-run/read-only. The script intentionally does not write taskpool notes unless
--write is added by a future governance slice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED = [
    "requesting_brain",
    "return_to_brain",
    "claim",
    "source_packet",
    "confidence",
    "falsifier",
    "desired_artifact",
    "acceptance_evidence",
]

def slugify(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", text).strip("-").lower()
    return text[:72] or "qual-to-quant-validation"

def validate(packet: dict[str, Any]) -> list[str]:
    errors=[]
    for key in REQUIRED:
        if key not in packet or packet[key] in (None, "", []):
            errors.append(f"missing_required:{key}")
    if "confidence" in packet:
        try:
            confidence=float(packet["confidence"])
            if not 0 <= confidence <= 1:
                errors.append("confidence_out_of_range")
        except Exception:
            errors.append("confidence_not_number")
    source=packet.get("source_packet") or {}
    if isinstance(source, dict):
        if not source.get("verified") and not source.get("uncertain"):
            errors.append("source_packet_has_no_boundaries")
    else:
        errors.append("source_packet_not_object")
    if packet.get("requesting_brain") == "dev":
        errors.append("requesting_brain_should_not_be_dev_for_research_to_dev_contract")
    return errors

def build_task(packet: dict[str, Any]) -> dict[str, Any]:
    errors=validate(packet)
    claim=str(packet.get("claim", "validation"))
    digest=hashlib.sha1(json.dumps(packet, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:8]
    task_id=f"dev-validate-{slugify(claim)}-{digest}"
    note=f"""---
type: task
lane: evolution
status: proposed
priority: P2
project: hermes
architecture_target: local-brain
requesting_brain: {packet.get('requesting_brain')}
implementation_brain: dev
return_to_brain: {packet.get('return_to_brain')}
falsifier: {packet.get('falsifier')}
desired_artifact: {packet.get('desired_artifact')}
capability_delta: "dev_validation_artifact: {packet.get('desired_artifact')}"
anti_drift_check: dev validates falsifier and returns evidence; dev does not decide domain truth
acceptance_evidence: {packet.get('acceptance_evidence')}
truth_gate: source_packet -> falsifier -> dev artifact -> handback proof
created_by_contract: qual_to_quant_task_contract.py
contract_version: 1
---

# Proposed dev validation task: {claim}

## Source packet

```json
{json.dumps(packet.get('source_packet', {}), ensure_ascii=False, indent=2)}
```

## Falsifier

{packet.get('falsifier')}

## Desired dev artifact

{packet.get('desired_artifact')}

## Handback

Return artifact path, invocation example, verification result, limits, and residual uncertainty to `{packet.get('return_to_brain')}`.
"""
    return {"status":"FAIL" if errors else "OK", "errors":errors, "task_id":task_id, "task_note":note}

def demo_packet() -> dict[str, Any]:
    return {
        "requesting_brain":"research",
        "return_to_brain":"research",
        "claim":"某资料源可稳定支撑钱学森系统工程索引更新",
        "source_packet":{"verified":["本地索引文件存在"],"uncertain":["外部来源版本覆盖不足"],"missing":["出版版本页码核验"]},
        "confidence":0.62,
        "falsifier":"若脚本无法定位引用来源或发现冲突版本，则不得写入核心知识原子",
        "desired_artifact":"read-only source boundary checker",
        "acceptance_evidence":"checker dry-run JSON includes verified/uncertain/missing and exits nonzero on write attempt without approval",
    }

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--packet', help='JSON packet file. Omit with --demo for built-in smoke packet.')
    p.add_argument('--demo', action='store_true')
    p.add_argument('--json', action='store_true')
    p.add_argument('--write', action='store_true', help='Reserved; currently rejected to keep first slice safe.')
    args=p.parse_args()
    if args.write:
        out={"status":"FAIL","errors":["write_mode_not_enabled_in_gate1"],"message":"Gate1 contract is dry-run only."}
    else:
        packet=demo_packet() if args.demo or not args.packet else json.loads(Path(args.packet).read_text())
        out=build_task(packet)
    print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else out.get('task_note', json.dumps(out, ensure_ascii=False)))
    return 0 if out.get('status')=='OK' else 2
if __name__ == '__main__':
    raise SystemExit(main())
