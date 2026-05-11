#!/usr/bin/env python3
"""
consensus-plans.py — 多模型 plan 语义一致性检测与合并 (L4 consensus engine)

4 层语义对比:
  L1: diagnosis.root_cause_class 多数一致 (权重 0.4)
  L2: patches[*].id Jaccard ≥0.5 (权重 0.3)
  L3: 参数接近度 (同一 patch 的不同参数 ±20% 中位数) (权重 0.2)
  L4: 置信度加权投票 (权重 0.1)

合并策略: 交集优先 → 多数补充 → 少数仲裁

用法:
  python3 consensus-plans.py merge plan1.json plan2.json [plan3.json]
  python3 consensus-plans.py check plan1.json plan2.json  # 检查一致性 (exit 0/1)
"""

import argparse
import hashlib
import json
import os
import sys
import time
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from agent_protocol import wrap as protocol_wrap, emit as protocol_emit, ProtocolError


def load_plans(files: List[str]) -> List[dict]:
    plans = []
    for f in files:
        try:
            with open(f) as fh:
                plan = json.load(fh)
            if "meta" in plan and "diagnosis" in plan:
                plans.append(plan)
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"Warning: failed to load {f}", file=sys.stderr)
    return plans


def jaccard(set_a: set, set_b: set) -> float:
    union = len(set_a | set_b)
    return len(set_a & set_b) / union if union else 0.0


def median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n//2 - 1] + s[n//2]) / 2
    return s[n//2]


def check_consensus(plans: List[dict]) -> dict:
    """4 层语义一致性检测"""
    if len(plans) < 2:
        return {"consensus": True, "score": 1.0, "layers": {}, "verdict": "single_planner"}

    N = len(plans)
    quorum = N // 2 + 1  # 多数

    layers = {}

    # ── L1: diagnosis.root_cause_class 多数一致 ──
    diag_classes = {}
    for i, p in enumerate(plans):
        rc = p.get("diagnosis", {}).get("root_cause_class", "unknown")
        diag_classes[rc] = diag_classes.get(rc, 0) + 1

    top_class = max(diag_classes, key=diag_classes.get)
    l1_agree = diag_classes[top_class] >= quorum
    layers["L1_diagnosis"] = {
        "pass": l1_agree,
        "majority_class": top_class,
        "distribution": diag_classes,
        "weight": 0.4,
    }

    # ── L2: patches[*].id Jaccard ──
    patch_sets = []
    for p in plans:
        ids = set(pt["id"] for pt in p.get("patches", []))
        patch_sets.append(ids)

    # 计算所有对的 Jaccard 平均值
    jaccard_scores = []
    for i in range(len(patch_sets)):
        for j in range(i + 1, len(patch_sets)):
            jaccard_scores.append(jaccard(patch_sets[i], patch_sets[j]))

    avg_jaccard = sum(jaccard_scores) / len(jaccard_scores) if jaccard_scores else 0
    l2_pass = avg_jaccard >= 0.5
    layers["L2_patches"] = {
        "pass": l2_pass,
        "avg_jaccard": round(avg_jaccard, 3),
        "patch_sets": [sorted(list(s)) for s in patch_sets],
        "threshold": 0.5,
        "weight": 0.3,
    }

    # ── L3: 参数接近度 ──
    # 对每个共享 patch id，比较 new_value 参数
    param_conflicts = []
    all_patch_ids = set()
    for ps in patch_sets:
        all_patch_ids |= ps

    param_ok = True
    for pid in all_patch_ids:
        values = []
        for p in plans:
            for pt in p.get("patches", []):
                if pt["id"] == pid and "new_value" in pt:
                    values.append(pt["new_value"])
        
        if len(values) >= 2 and isinstance(values[0], (int, float)):
            med = median(values)
            max_dev = max(abs(v - med) for v in values) if values else 0
            range_v = max(values) - min(values)
            if range_v > 0 and max_dev / range_v > 0.2:
                param_ok = False
                param_conflicts.append({
                    "patch_id": pid,
                    "values": values,
                    "median": med,
                    "max_deviation_ratio": round(max_dev / range_v, 3) if range_v else 0,
                })

    layers["L3_params"] = {
        "pass": param_ok,
        "conflicts": param_conflicts,
        "weight": 0.2,
    }

    # ── L4: 置信度加权 ──
    confidences = [p.get("meta", {}).get("confidence", 0.5) for p in plans]
    # 每层 pass 加权
    layer_scores = []
    for layer_name in ["L1_diagnosis", "L2_patches", "L3_params"]:
        layer = layers[layer_name]
        layer_scores.append(1.0 if layer["pass"] else 0.0)

    weights = [0.4, 0.3, 0.2, 0.1]
    weighted_score = sum(s * w for s, w in zip(layer_scores + [sum(confidences)/len(confidences)], weights))

    layers["L4_confidence_weighted"] = {
        "score": round(weighted_score, 4),
        "confidences": confidences,
        "avg_confidence": round(sum(confidences) / len(confidences), 3),
        "weight": 0.1,
    }

    return {
        "consensus": weighted_score >= 0.5,
        "score": round(weighted_score, 4),
        "layers": layers,
        "verdict": "consensus" if weighted_score >= 0.7 else ("weak_consensus" if weighted_score >= 0.5 else "dissent"),
    }


def merge_plans(plans: List[dict]) -> dict:
    """交集优先合并"""
    result = check_consensus(plans)
    
    if len(plans) == 1:
        merged = plans[0].copy()
        merged["merge_info"] = {"strategy": "single_planner", "planners": 1}
        _emit_consensus_plans(merged)
        return merged

    N = len(plans)
    quorum = N // 2 + 1

    # 收集所有 patch
    patch_map: Dict[str, dict] = {}  # id → {patch, planners_count}
    for p in plans:
        for pt in p.get("patches", []):
            pid = pt["id"]
            if pid not in patch_map:
                patch_map[pid] = {"patch": pt, "count": 0, "planners": []}
            patch_map[pid]["count"] += 1
            patch_map[pid]["planners"].append(p.get("meta", {}).get("planner_model", "?"))

    # 分类
    unanimous = []
    majority = []
    minority = []

    for pid, info in patch_map.items():
        if info["count"] == N:
            unanimous.append(info["patch"])
        elif info["count"] >= quorum:
            majority.append(info["patch"])
        else:
            minority.append({"patch": info["patch"], "planners": info["planners"]})

    # 合并: 全票 → 直接; 多数 → 加; 少数 → 标记待仲裁
    merged_patches = unanimous + majority
    arbitration_needed = len(minority) > 0

    # 选最高置信度的 meta
    best_meta = max(plans, key=lambda p: p.get("meta", {}).get("confidence", 0)).get("meta", {})

    merged = {
        "meta": {
            "planner_model": f"ensemble:{len(plans)}",
            "planner_role": "merged",
            "state_hash": plans[0].get("meta", {}).get("state_hash", ""),
            "tier_target": best_meta.get("tier_target", "T2"),
            "confidence": result["score"],
            "source_plans": len(plans),
        },
        "diagnosis": {
            "root_cause_class": result["layers"]["L1_diagnosis"]["majority_class"],
            "summary": f"Merged from {len(plans)} planners, consensus score={result['score']:.3f}",
        },
        "patches": merged_patches,
        "merge_info": {
            "strategy": "intersection_first",
            "planners": len(plans),
            "quorum": quorum,
            "unanimous_count": len(unanimous),
            "majority_count": len(majority),
            "minority_count": len(minority),
            "arbitration_needed": arbitration_needed,
            "minority_patches": [m["patch"]["id"] for m in minority],
            "consensus_score": result["score"],
            "consensus_verdict": result["verdict"],
        },
        "verification": {
            "expected_metric_delta": {"main_pass_rate": 0.01},
            "guard_metrics": ["main_pass_rate"],
            "tier_eval_plan": "T0_T1",
        },
        "rollback_signal": {
            "auto_rollback_if": f"main_pass_rate < pre - 0.05",
            "kill_switch_inc": False,
        },
    }

    # 取最高 severity 的 blast_radius
    blast_order = {"kill_switch": 4, "all_tiers": 3, "router": 2, "single_tier": 1}
    max_blast = max(
        (blast_order.get(pt.get("blast_radius", "single_tier"), 0) for pt in merged_patches),
        default=0,
    )
    merged["merge_info"]["max_blast_radius"] = [k for k, v in blast_order.items() if v == max_blast][0] if max_blast > 0 else "single_tier"

    _emit_consensus_plans(merged)
    return merged


def _emit_consensus_plans(merged: dict) -> None:
    """Emit L2 protocol message for consensus-plans merge results."""
    try:
        timestamp = time.strftime("%Y%m%dT%H%M%S")
        merge_info = merged.get("merge_info", {})
        msg = protocol_wrap(
            agent_id="consensus-plans",
            task_id="merge-" + timestamp,
            verdict="pass",
            verification_pattern="consensus_plans",
            extensions={
                "source_plans": merge_info.get("planners", 0),
                "consensus_score": merge_info.get("consensus_score", 0.0),
            },
        )
        protocol_emit(msg)
    except ProtocolError:
        pass


def cli():
    parser = argparse.ArgumentParser(description="Consensus Plans — 多模型 plan 语义一致性")
    sub = parser.add_subparsers(dest="cmd")

    chk = sub.add_parser("check", help="检查一致性")
    chk.add_argument("files", nargs="+", help="plan JSON 文件列表")

    mg = sub.add_parser("merge", help="合并 plans")
    mg.add_argument("files", nargs="+", help="plan JSON 文件列表")

    args = parser.parse_args()

    if args.cmd in ("check", "merge"):
        plans = load_plans(args.files)
        if len(plans) < 2:
            print(json.dumps({"error": "Need at least 2 valid plans"}, indent=2))
            sys.exit(1)

        result = check_consensus(plans)
        
        if args.cmd == "check":
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(0 if result["consensus"] else 1)
        
        elif args.cmd == "merge":
            merged = merge_plans(plans)
            print(json.dumps(merged, indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
