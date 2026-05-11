#!/usr/bin/env python3
"""
ensemble-vote.py — 多模型投票/仲裁 (L3)
基于 delegate_task batch 模式实现的多模型并行执行与结果聚合

策略:
  - majority: 多数投票
  - weighted: 按 model_stats 的 score 加权
  - arbiter: 额外的裁判模型审查所有结果后决定

用法:
  python3 ensemble-vote.py vote --task "Review auth.py for bugs" --models gpt-5.4,claude-opus-4-7 --strategy majority
  python3 ensemble-vote.py vote --task "..." --strategy weighted --models gpt-5.4,claude-sonnet-4-6,claude-opus-4-7
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional

# L2 协议导入
sys.path.insert(0, os.path.dirname(__file__))
from agent_protocol import (
    wrap as protocol_wrap,
    try_wrap as protocol_try_wrap,
    emit as protocol_emit,
    ProtocolError,
)


HERMES_HOME = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))

# ── SPL encoding (optional, for token savings) ──
try:
    sys.path.insert(0, os.path.join(HERMES_HOME, "hermes-agent"))
    from agent.spl import SPLEncoder
    _spl_encoder = SPLEncoder()
    _spl_available = True
except ImportError:
    _spl_available = False

LOG_FILE = os.environ.get(
    "ENSEMBLE_VOTE_LOG_FILE",
    os.path.join(HERMES_HOME, "logs", "ensemble-votes.jsonl"),
)
LOG_FILE = os.path.expanduser(LOG_FILE)
QUORUM_FILE = os.environ.get(
    "HERMES_QUORUM_FILE",
    os.path.join(HERMES_HOME, "config", "quorum.yaml"),
)
QUORUM_FILE = os.path.expanduser(QUORUM_FILE)
ENSEMBLE_LOG_SCHEMA_VERSION = 1
SUPPORTED_HERMES_PROVIDERS = {
    "openai-codex", "anthropic", "xiaomi", "openrouter", "gemini", "xai",
    "ollama-cloud", "huggingface", "zai", "kimi-coding", "kimi-coding-cn",
    "stepfun", "minimax", "minimax-cn", "kilocode", "arcee", "nvidia",
}


def load_config() -> dict:
    """Load Hermes config for model→provider resolution."""
    try:
        import yaml
    except ImportError:
        return {}
    try:
        with open(os.path.join(HERMES_HOME, "config.yaml")) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def load_quorum() -> dict:
    """Load quorum.yaml for tier→arbiter resolution. Cached per-process."""
    try:
        import yaml
    except ImportError:
        return {}
    try:
        with open(QUORUM_FILE) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def resolve_arbiter_model(tier: Optional[str] = None) -> Optional[str]:
    """Resolve arbiter model from quorum.yaml.

    Precedence:
      1. tiers.<tier>.arbiter (if tier given and tier-level arbiter set)
      2. multi_brain.default_arbiter
      3. None (caller must skip arbiter)
    """
    q = load_quorum()
    if tier:
        t = (q.get("tiers") or {}).get(tier) or {}
        v = t.get("arbiter")
        if v:
            return v
    mb = q.get("multi_brain") or {}
    return mb.get("default_arbiter")


def model_provider(model: str, config: Optional[dict] = None) -> str:
    """Resolve provider from pricing.models so ensemble votes call the intended backend."""
    config = config if config is not None else load_config()
    return (
        config.get("pricing", {})
        .get("models", {})
        .get(model, {})
        .get("provider", "")
    )


def get_model_weights(models: List[str]) -> Dict[str, float]:
    """从 route_store 获取模型权重"""
    store_path = os.path.join(HERMES_HOME, "scripts", "route_store.py")
    try:
        r = subprocess.run(
            [sys.executable, store_path, "model-stats", "--hours", "168"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            stats = json.loads(r.stdout)
            weights = {}
            for s in stats:
                if s["model"] in models:
                    # score + 0.01 避免零权重
                    weights[s["model"]] = s["score"] + 0.01
            # 未在统计中的模型给默认权重
            for m in models:
                if m not in weights:
                    weights[m] = 0.5
            # 归一化
            total = sum(weights.values())
            if total > 0:
                weights = {k: round(v/total, 4) for k, v in weights.items()}
            return weights
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        print(f"[ensemble-vote] get_model_weights failed: {e}", file=sys.stderr)
        pass
    # 默认: 均匀权重
    return {m: round(1.0/len(models), 4) for m in models}


def majority_vote(results: List[dict]) -> dict:
    """多数投票聚合"""
    # 按 verdict 分布统计
    votes = {}
    for r in results:
        verdict = r.get("verdict", "unknown")
        votes[verdict] = votes.get(verdict, 0) + 1
    
    winner = max(votes, key=votes.get)
    return {
        "strategy": "majority",
        "verdict": winner,
        "votes": votes,
        "total_voters": len(results),
        "consensus": votes[winner] == len(results),
    }


def weighted_vote(results: List[dict], weights: Dict[str, float]) -> dict:
    """加权投票聚合"""
    score_by_verdict = {}
    for r in results:
        model = r.get("model", "unknown")
        verdict = r.get("verdict", "unknown")
        w = weights.get(model, 1.0)
        score_by_verdict[verdict] = score_by_verdict.get(verdict, 0) + w
    
    winner = max(score_by_verdict, key=score_by_verdict.get)
    total = sum(score_by_verdict.values())
    return {
        "strategy": "weighted",
        "verdict": winner,
        "weighted_scores": {k: round(v/total, 4) for k, v in score_by_verdict.items()},
        "weights_used": weights,
        "total_weight": round(total, 4),
    }


def vote(
    task: str,
    models: List[str],
    strategy: str = "majority",
    workdir: str = None,
    execute: bool = True,
    tier: Optional[str] = None,
) -> dict:
    """
    执行多模型投票。

    execute=True (默认): 实际调用每个模型 (via hermes chat -q),
    收集 verdict，运行聚合策略。

    execute=False: 仅输出框架 (兼容旧行为，用于 delegate_task 场景)。

    tier (T0-T3): 用于 strategy='arbiter' 时从 quorum.yaml 解析 arbiter
    模型；为 None 时回退到 multi_brain.default_arbiter。
    """
    weights = get_model_weights(models)

    result = {
        "task": task,
        "models": models,
        "strategy": strategy,
        "tier": tier,
        "schema_version": ENSEMBLE_LOG_SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_weights": weights,
        "execute": bool(execute),
    }

    if not execute:
        # 兼容旧行为: 仅框架输出
        result["consensus"] = False
        result["verdict"] = "skipped"
        result["votes_count"] = 0
        result["note"] = (
            "Framework mode — set execute=True or use delegate_task "
            "for actual parallel model execution."
        )
        _log_and_emit(result, strategy, models, weights)
        return result

    # ── 实际执行: 顺序调用每个模型 ──
    results = []
    for model in models:
        model_result = _call_model(task, model, workdir)
        results.append(model_result)

    # ── 聚合 ──
    if strategy == "weighted":
        aggregated = weighted_vote(results, weights)
    elif strategy == "arbiter":
        # Arbiter: 所有结果喂给 quorum.yaml 决定的 arbiter 模型
        aggregated = _arbiter_vote(results, task, tier=tier)
    else:
        aggregated = majority_vote(results)

    result["model_results"] = results
    result.update(aggregated)
    # 强制写入 verdict + votes_count, 供 schema-enforced logger 校验
    result.setdefault("verdict", aggregated.get("verdict", "unknown"))
    result["votes_count"] = sum(
        1 for r in results if r.get("verdict") not in (None, "unknown", "timeout")
    )
    result["consensus"] = aggregated.get(
        "consensus",
        aggregated.get("verdict", "unknown") not in ("unknown", "timeout"),
    )

    _log_and_emit(result, strategy, models, weights)
    return result


def _call_model(task: str, model: str, workdir: str = None) -> dict:
    """
    通过 hermes chat -q 调用模型执行投票任务。

    返回 {"model": str, "verdict": str, "output": str|None}
    """
    import shutil
    hermes = shutil.which("hermes")
    if not hermes:
        return {"model": model, "verdict": "unknown",
                "output": None, "error": "hermes command not found"}

    prompt = (
        f"You are an expert code reviewer. Review this task and respond with your verdict.\n\n"
        f"TASK:\n{task}\n\n"
        f"Output ONLY a JSON object with:\n"
        f'{{"verdict": "pass"|"fail"|"partial", "summary": "<brief reason>"}}'
    )

    # Try SPL encoding for token savings
    if _spl_available:
        try:
            spl_msg = _spl_encoder.encode_vote_call(
                task=task, model=model,
            )
            prompt = json.dumps(spl_msg, ensure_ascii=False)
        except Exception:
            pass  # fall back to original prompt
    provider = model_provider(model)
    cmd = [hermes, "chat", "-q", prompt, "--model", model,
           "--quiet", "--max-turns", "1", "--source", "ensemble-vote", "--ignore-rules"]
    if provider in SUPPORTED_HERMES_PROVIDERS:
        cmd += ["--provider", provider]

    try:
        r = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=120,
            cwd=workdir,
        )
        # 从输出提取 verdict。Hermes 可能先打印 session_id，因此不能只 json.loads(stdout)。
        try:
            match = re.search(r"\{.*\}", r.stdout, re.DOTALL)
            data = json.loads(match.group(0) if match else r.stdout)
            verdict = data.get("verdict", "unknown")
        except (json.JSONDecodeError, AttributeError):
            # 尝试从输出文本中探测
            out_lower = r.stdout.lower()
            if "pass" in out_lower and "fail" not in out_lower:
                verdict = "pass"
            elif "fail" in out_lower:
                verdict = "fail"
            else:
                verdict = "unknown"

        return {
            "model": model,
            "provider": provider,
            "adapter": "hermes-chat",
            "verdict": verdict,
            "output": r.stdout[:500],
            "exit_code": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"model": model, "verdict": "timeout", "output": None}
    except (OSError, ValueError) as e:
        return {"model": model, "verdict": "unknown", "output": None, "error": str(e)}


def _arbiter_vote(results: List[dict], task: str, tier: Optional[str] = None) -> dict:
    """仲裁投票: 将结果喂给仲裁模型 (从 quorum.yaml 解析).

    tier 决定 arbiter 选择:
      tiers.<tier>.arbiter > multi_brain.default_arbiter > None.
    若无可用 arbiter, 返回 verdict='unknown' reason='no_arbiter_configured'.
    """
    summary = "\n".join(
        f"- {r['model']}: verdict={r['verdict']}"
        for r in results
    )
    prompt = (
        f"You are the final arbiter. Review these model verdicts and decide.\n\n"
        f"TASK: {task}\n\n"
        f"VOTES:\n{summary}\n\n"
        f"Output ONLY: {{\"verdict\": \"pass\"|\"fail\"|\"partial\", \"reason\": \"...\"}}"
    )

    import shutil
    hermes = shutil.which("hermes")
    if not hermes:
        return {"strategy": "arbiter", "verdict": "unknown", "reason": "hermes not found",
                "tier": tier}

    arbiter_model = resolve_arbiter_model(tier)
    if not arbiter_model:
        return {"strategy": "arbiter", "verdict": "unknown",
                "reason": "no_arbiter_configured", "tier": tier}
    provider = model_provider(arbiter_model)
    cmd = [hermes, "chat", "-q", prompt, "--model", arbiter_model,
           "--quiet", "--max-turns", "1", "--source", "ensemble-vote", "--ignore-rules"]
    if provider in SUPPORTED_HERMES_PROVIDERS:
        cmd += ["--provider", provider]

    try:
        r = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
        )
        try:
            match = re.search(r"\{.*\}", r.stdout, re.DOTALL)
            data = json.loads(match.group(0) if match else r.stdout)
            return {"strategy": "arbiter", "arbiter_model": arbiter_model,
                    "arbiter_provider": provider, "tier": tier,
                    "verdict": data.get("verdict", "unknown"),
                    "arbiter_reason": data.get("reason", data.get("summary", ""))}
        except json.JSONDecodeError:
            return {"strategy": "arbiter", "verdict": "unknown",
                    "arbiter_model": arbiter_model, "tier": tier,
                    "raw": r.stdout[:200]}
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"strategy": "arbiter", "verdict": "timeout",
                "arbiter_model": arbiter_model, "tier": tier, "error": str(e)}


def _log_and_emit(result: dict, strategy: str, models: List[str], weights: dict):
    """记录日志 + L2 协议 emit (schema-enforced).

    保证写入字段: ts, task, strategy, verdict, votes_count, models,
    schema_version, tier. 不达标的条目 fail-closed 不写入并 stderr 警告.
    """
    # 序列化安全副本
    log_entry = {k: v for k, v in result.items() if k not in ("model_results",)}
    # schema 校验
    log_entry.setdefault("schema_version", ENSEMBLE_LOG_SCHEMA_VERSION)
    required = ("ts", "task", "strategy", "verdict", "votes_count", "models")
    missing = [f for f in required if log_entry.get(f) is None]
    if missing:
        print(
            f"[ensemble-vote] WARN: missing required fields {missing}; "
            f"skipping log write to keep schema clean.",
            file=sys.stderr,
        )
    else:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    # ── L2 协议 emit ──
    try:
        consensus = result.get("consensus", False)
        protocol_msg = protocol_wrap(
            agent_id="ensemble-vote",
            task_id="vote-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
            verdict="pass" if consensus else "partial",
            verification_pattern="ensemble_vote",
            extensions={
                "strategy": strategy,
                "models": models,
                "weights": weights,
                "tier": result.get("tier"),
                "votes_count": result.get("votes_count", 0),
                "metadata": result.get("weighted_scores", result.get("votes", {})),
            },
        )
        result["agent_protocol"] = protocol_msg
        protocol_emit(protocol_msg)
    except ProtocolError as e:
        print(f"[ensemble-vote] Protocol emit failed: {e}", file=sys.stderr)


def cli():
    parser = argparse.ArgumentParser(description="Ensemble Vote — 多模型投票")
    sub = parser.add_subparsers(dest="cmd")

    vt = sub.add_parser("vote", help="执行多模型投票")
    vt.add_argument("--task", required=True, help="任务描述")
    vt.add_argument("--models", required=True, help="逗号分隔的模型列表")
    vt.add_argument("--strategy", default="majority", 
                    choices=["majority", "weighted", "arbiter"])
    vt.add_argument("--execute", action="store_true", default=False,
                    help="Actually call models (default: framework-only)")
    vt.add_argument("--workdir", default=None, help="工作目录")
    vt.add_argument("--tier", default=None, choices=["T0", "T1", "T2", "T3"],
                    help="任务层级 (用于 strategy=arbiter 时解析 arbiter 模型)")

    sub.add_parser("history", help="查看投票历史")

    args = parser.parse_args()

    if args.cmd == "vote":
        models = [m.strip() for m in args.models.split(",") if m.strip()]
        if len(models) < 2:
            print("Need at least 2 models for voting", file=sys.stderr)
            sys.exit(1)
        
        result = vote(
            task=args.task,
            models=models,
            strategy=args.strategy,
            workdir=args.workdir,
            execute=args.execute,
            tier=args.tier,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.cmd == "history":
        if not os.path.exists(LOG_FILE):
            print("No vote history yet.")
            return
        with open(LOG_FILE) as f:
            entries = f.readlines()
        print(f"Vote history ({len(entries)} entries):")
        for line in entries[-20:]:
            try:
                d = json.loads(line)
                print(f"  {d['ts']} task={d['task'][:50]} models={d['models']} strategy={d['strategy']}")
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
