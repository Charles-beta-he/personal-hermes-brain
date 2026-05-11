#!/usr/bin/env python3
"""
consensus-check.py — 多模型输出一致性检测器 (L4)
判断 N 个模型的输出是否一致，用于 T2/T3 verification 的 short-circuit 决策

检测策略:
  - Python 代码: AST parse → 归一化 → hash
  - JSON: key sort → hash  
  - 纯文本: 规范化空白 → 精确匹配
  - (v2) 散文: embedding cosine similarity

用法:
  python3 consensus-check.py check --outputs '["def foo():...","def foo():..."]'
  python3 consensus-check.py check --files out1.py out2.py
  python3 consensus-check.py similarity --a "text1" --b "text2"
"""

import argparse
import ast
import hashlib
import json
import os
import sys
import time
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from agent_protocol import wrap as protocol_wrap, emit as protocol_emit, ProtocolError


def normalize_code(code: str) -> str:
    """代码归一化: AST parse → 去注释/空白规范化 → 序列化"""
    try:
        tree = ast.parse(code)
        # 移除 docstring 和注释 (AST 不保留注释)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                # 保留结构但清除 docstring
                pass
        return ast.unparse(tree)
    except SyntaxError:
        # 代码片段 (非完整模块): 尝试精确匹配
        return code.strip()


def normalize_json(text: str) -> str:
    """JSON 归一化: key sort → compact"""
    try:
        obj = json.loads(text)
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        return text.strip()


def normalize_text(text: str) -> str:
    """文本归一化: 空白规范化"""
    return " ".join(text.split())


def hash_content(content: str) -> str:
    """SHA256 哈希"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def detect_type(text: str) -> str:
    """检测内容类型"""
    text = text.strip()
    # JSON 检测
    if text.startswith("{") or text.startswith("["):
        try:
            json.loads(text)
            return "json"
        except json.JSONDecodeError:
            pass
    # Python 代码检测
    if any(kw in text for kw in ["def ", "class ", "import ", "from "]):
        try:
            ast.parse(text)
            return "code"
        except SyntaxError:
            pass
    return "text"


def check_consensus(
    outputs: List[str],
    content_type: str = None,
    threshold: float = 0.9,
) -> dict:
    """
    检查 N 个输出的一致性
    
    Returns:
      {
        agree: bool,
        consensus_type: "exact_match" | "high_similarity" | "dissent",
        hashes: [...],
        pairs: [{a: idx, b: idx, match: bool, similarity: float}, ...]
      }
    """
    if len(outputs) < 2:
        result = {"agree": True, "consensus_type": "single_output", "hashes": [], "pairs": []}
        _emit_consensus_check(result)
        return result

    # 检测或使用指定类型
    if content_type is None:
        types = [detect_type(o) for o in outputs]
        # 多数投票
        content_type = max(set(types), key=types.count)

    # 归一化
    if content_type == "code":
        normalized = [normalize_code(o) for o in outputs]
    elif content_type == "json":
        normalized = [normalize_json(o) for o in outputs]
    else:
        normalized = [normalize_text(o) for o in outputs]

    hashes = [hash_content(n) for n in normalized]

    # 全匹配检测
    if len(set(hashes)) == 1:
        result = {
            "agree": True,
            "consensus_type": "exact_match",
            "content_type": content_type,
            "hashes": hashes,
            "pairs": [],
            "unique_hashes": 1,
        }
        _emit_consensus_check(result)
        return result

    # 两两相似度
    pairs = []
    match_count = 0
    total_pairs = 0
    
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            total_pairs += 1
            if hashes[i] == hashes[j]:
                similarity = 1.0
            elif content_type in ("text",):
                # 简单 Jaccard: 词集重叠
                words_i = set(normalized[i].split())
                words_j = set(normalized[j].split())
                union = len(words_i | words_j)
                similarity = len(words_i & words_j) / union if union else 0
            else:
                similarity = 0.0  # 代码/JSON 不同 hash = 完全不同
            
            match = similarity >= threshold
            if match:
                match_count += 1
            
            pairs.append({
                "a": i,
                "b": j,
                "match": match,
                "similarity": round(similarity, 4),
            })

    # 共识判定: 所有对都匹配
    agree = match_count == total_pairs
    
    result = {
        "agree": agree,
        "consensus_type": "high_similarity" if agree else "dissent",
        "content_type": content_type,
        "hashes": hashes,
        "pairs": pairs,
        "unique_hashes": len(set(hashes)),
        "match_ratio": round(match_count / total_pairs, 2) if total_pairs else 1.0,
    }
    _emit_consensus_check(result)
    return result


def _emit_consensus_check(result: dict) -> None:
    """Emit L2 protocol message for consensus-check results."""
    try:
        timestamp = time.strftime("%Y%m%dT%H%M%S")
        msg = protocol_wrap(
            agent_id="consensus-check",
            task_id="check-" + timestamp,
            verdict="pass" if result["agree"] else "dissent",
            verification_pattern="consensus_check",
            extensions={
                "match_ratio": result.get("match_ratio", 1.0),
                "hashes": result.get("hashes", []),
            },
        )
        protocol_emit(msg)
    except ProtocolError:
        pass


def similarity(a: str, b: str) -> float:
    """计算两个文本的相似度"""
    result = check_consensus([a, b])
    pairs = result.get("pairs", [])
    if pairs:
        return pairs[0]["similarity"]
    return 0.0


def cli():
    parser = argparse.ArgumentParser(description="Consensus Checker — 多模型输出一致性检测")
    sub = parser.add_subparsers(dest="cmd")

    chk = sub.add_parser("check", help="检查多输出一致性")
    chk.add_argument("--outputs", default="", help="JSON 数组: ['out1','out2',...]")
    chk.add_argument("--files", nargs="*", default=[], help="从文件读取")
    chk.add_argument("--stdin", action="store_true", help="从 stdin 读取 (每行一个输出)")
    chk.add_argument("--type", default=None, choices=["code", "json", "text"])
    chk.add_argument("--threshold", type=float, default=0.9)

    sim = sub.add_parser("similarity", help="计算两个文本相似度")
    sim.add_argument("--a", required=True)
    sim.add_argument("--b", required=True)

    args = parser.parse_args()

    if args.cmd == "check":
        outputs = []
        
        if args.outputs:
            outputs = json.loads(args.outputs)
        elif args.files:
            for f in args.files:
                with open(f) as fh:
                    outputs.append(fh.read())
        elif args.stdin:
            outputs = [line.rstrip("\n") for line in sys.stdin if line.strip()]
        
        if len(outputs) < 2:
            print(json.dumps({"error": "need at least 2 outputs"}))
            sys.exit(1)
        
        result = check_consensus(outputs, args.type, args.threshold)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if not result["agree"]:
            sys.exit(1)

    elif args.cmd == "similarity":
        sim_val = similarity(args.a, args.b)
        print(json.dumps({"similarity": round(sim_val, 4)}))

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
