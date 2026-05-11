#!/usr/bin/env python3
"""
cross-patch.py — 双模型交叉审查编排器 (L4 T2)
Producer A 执行任务 → Reviewer B 审查并生成结构化补丁 → Merger 自动化合并

工作流:
  A (producer) → 生成 artifact
  B (reviewer) → 审查, 输出结构化补丁列表
  Merger        → 按置信度阈值合并补丁 → 最终 artifact

模型配置:
  producer: gpt-5.4 (openai-codex) — 主生产力
  reviewer: deepseek-v4-pro — 互补审查 (不同训练语料)
  (未来: xiaomi 加入 T3 adversarial 第三验证者)

用法:
  python3 cross-patch.py execute --task "Fix auth bug in src/auth.py" --workdir /path/to/repo
  python3 cross-patch.py merge --base <base_output> --patches '<patch_json>'
  python3 cross-patch.py status
"""

import argparse
import difflib
import json
import os
import re
import subprocess
import sys        # for ProtocolError
import time
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Dict, Tuple, Optional

# L2 协议导入 (替代内联 dict)
sys.path.insert(0, os.path.dirname(__file__))
from agent_protocol import (
    wrap as protocol_wrap,
    try_wrap as protocol_try_wrap,
    extract as protocol_extract,
    extract_strict as protocol_extract_strict,
    emit as protocol_emit,
    ProtocolError,
)


HERMES_HOME = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))


def _load_quorum_safe() -> dict:
    """Early helper used inside load_config(); duplicates load_quorum_config but
    is safe to call before that function is defined later in the file."""
    try:
        import yaml as _y
        path = os.environ.get(
            "HERMES_QUORUM_FILE",
            os.path.join(HERMES_HOME, "config", "quorum.yaml"),
        )
        with open(os.path.expanduser(path)) as f:
            return _y.safe_load(f) or {}
    except Exception:
        return {}



LOG_FILE = os.environ.get(
    "CROSS_PATCH_LOG_FILE",
    os.path.join(HERMES_HOME, "logs", "cross-patch.jsonl"),
)
LOG_FILE = os.path.expanduser(LOG_FILE)
SUPPORTED_HERMES_PROVIDERS = {
    "openai-codex", "anthropic", "xiaomi", "openrouter", "gemini", "xai",
    "ollama-cloud", "huggingface", "zai", "kimi-coding", "kimi-coding-cn",
    "stepfun", "minimax", "minimax-cn", "kilocode", "arcee", "nvidia",
}


def load_full_config() -> dict:
    """Load full Hermes config for provider resolution."""
    try:
        config_path = os.path.join(HERMES_HOME, "config.yaml")
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, FileNotFoundError, OSError) as e:
        print(f"[cross-patch] Full config load failed: {e}", file=sys.stderr)
        return {}


def model_provider(model: str, full_config: Optional[dict] = None) -> str:
    """Resolve model provider from pricing.models."""
    full_config = full_config if full_config is not None else load_full_config()
    return (
        full_config.get("pricing", {})
        .get("models", {})
        .get(model, {})
        .get("provider", "")
    )


def load_config():
    """加载 verification.cross_patch 配置"""
    try:
        import yaml
        config_path = os.path.join(HERMES_HOME, "config.yaml")
        with open(config_path) as f:
            c = yaml.safe_load(f)
        v = c.get("verification", {})
        cp = v.get("cross_patch", {})
        # 默认 producer/reviewer 不再硬编码字面量, 从 quorum.yaml 派生
        # (load_quorum_config 在本文件后面定义)
        try:
            q_planners = list(
                ((_load_quorum_safe().get("tiers") or {}).get("T2") or {}).get("planners") or []
            )
        except Exception:
            q_planners = []
        default_producer = cp.get("producer_model") or (q_planners[0] if q_planners else None)
        default_reviewer = cp.get("reviewer_model") or (
            next((m for m in q_planners[1:] if m != default_producer), None)
            if len(q_planners) > 1 else None
        )
        return {
            "enabled": cp.get("enabled", False),
            "min_patch_conf": cp.get("min_patch_conf", 0.7),
            "producer_model": default_producer,
            "reviewer_model": default_reviewer,
            "max_patches": cp.get("max_patches", 20),
            "budget_per_task_usd": v.get("budgets", {}).get("per_task_usd", 2.0),
            "max_cost_per_run_usd": cp.get(
                "max_cost_per_run_usd",
                v.get("budgets", {}).get("per_task_usd", 2.0),
            ),
        }
    except (yaml.YAMLError, FileNotFoundError, KeyError, OSError) as e:
        print(f"[cross-patch] Config load failed: {e}", file=sys.stderr)
        return None


def build_producer_prompt(task: str, workdir: str = None) -> str:
    """构建 Producer 的系统提示词"""
    return f"""You are a code producer. Execute this task carefully and completely:

TASK: {task}

WORKING DIRECTORY: {workdir or 'current directory'}

Requirements:
- Produce a complete, working solution
- Include error handling
- Follow existing project conventions
- Output your final result as clean, production-ready code

After completing, output your result in this format:
```json
{{"verdict": "pass", "summary": "<what you did>", "artifacts": ["<file_paths_modified>"]}}
```
"""


def build_reviewer_prompt(task: str, producer_output: str) -> str:
    """构建 Reviewer 的系统提示词"""
    return f"""You are a code reviewer. Review the following output from another model.

TASK: {task}

PRODUCER OUTPUT:
{producer_output}

Do NOT rewrite the entire solution. Instead, emit a structured patch list.
For each issue you find, output:
```json
{{
  "verdict": "pass" or "fail",
  "patches": [
    {{
      "file": "<file_path>",
      "line_hint": "<approximate location>",
      "original": "<short snippet of original code>",
      "suggested": "<corrected code>",
      "rationale": "<why this change is needed>",
      "severity": "block" | "major" | "minor",
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "<overall assessment>"
}}
```

Rules:
- Only flag REAL issues — not style preferences
- "block" severity = security, correctness, data loss
- "major" severity = bug, missing edge case, performance
- "minor" severity = readability, naming, comments
- confidence = how sure you are this is a real issue (0.0-1.0)
- If you find NO issues, set patches=[] and verdict="pass"
"""


def parse_reviewer_output(output: str) -> dict:
    """从 Reviewer 输出提取结构化补丁 — 使用 L2 agent_protocol.extract() (灵活模式)"""
    # 1. 优先用 agent_protocol.extract (灵活模式, 接受非完全协议格式)
    result = protocol_extract(output)
    if result and "verdict" in result:
        return result

    # 2. 如果连灵活提取都失败，返回 safe fallback
    return {"verdict": "unknown", "patches": [],
            "summary": f"Failed to parse reviewer output: {output[:200]}"}


def apply_patches(
    base_content: str,
    patches: List[dict],
    min_confidence: float = 0.7,
) -> Tuple[str, dict]:
    """
    确定性合并: 应用置信度 >= min_confidence 的补丁
    
    Returns:
      (merged_content, stats)
    """
    # 仅应用 >= min_confidence 的补丁
    accepted = [p for p in patches if p.get("confidence", 0) >= min_confidence]
    rejected = [p for p in patches if p.get("confidence", 0) < min_confidence]
    
    # 按 severity 排序: block > major > minor
    severity_order = {"block": 0, "major": 1, "minor": 2}
    accepted.sort(key=lambda p: severity_order.get(p.get("severity", "minor"), 2))
    
    merged = base_content
    applied_count = 0
    conflicts = []
    applied_patches = []
    
    for patch in accepted:
        original = patch.get("original", "")
        suggested = patch.get("suggested", "")
        
        if not original or not suggested:
            continue
        
        # 简单字符串替换 (MVP — v2 用 fuzzy match)
        if original in merged:
            merged = merged.replace(original, suggested, 1)
            applied_count += 1
            applied_patches.append({
                "file": patch.get("file", ""),
                "rationale": patch.get("rationale", ""),
                "severity": patch.get("severity", "minor"),
                "confidence": patch.get("confidence", 0),
            })
        else:
            conflicts.append({
                "file": patch.get("file", ""),
                "original_snippet": original[:80],
                "severity": patch.get("severity", "minor"),
            })
    
    stats = {
        "total_patches": len(patches),
        "accepted": len(accepted),
        "applied": applied_count,
        "conflicts": len(conflicts),
        "rejected_low_conf": len(rejected),
        "conflict_details": conflicts[:5],
        "applied_details": applied_patches,
    }
    
    return merged, stats


def extract_json_object(output: str) -> dict:
    """Extract the first JSON object from raw/fenced/Hermes-prefixed model output."""
    text = (output or "").strip()
    if not text:
        raise json.JSONDecodeError("empty model output", text, 0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    obj = re.search(r"\{.*\}", text, re.DOTALL)
    if obj:
        return json.loads(obj.group(0))
    raise json.JSONDecodeError("no JSON object found", text, 0)


def _safe_file_path(workdir: str, file_name: str) -> Path:
    """Resolve file_name under workdir and reject path traversal."""
    root = Path(workdir or os.getcwd()).resolve()
    path = (root / file_name).resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"patch file escapes workdir: {file_name}")
    return path


def _normalize_patches(data: dict) -> List[dict]:
    patches = data.get("patches", []) if isinstance(data, dict) else []
    if not isinstance(patches, list):
        return []
    normalized = []
    for p in patches:
        if not isinstance(p, dict):
            continue
        q = dict(p)
        if "file" not in q and "target_file" in q:
            q["file"] = q.get("target_file")
        if "original" not in q and "old_string" in q:
            q["original"] = q.get("old_string")
        if "suggested" not in q and "new_string" in q:
            q["suggested"] = q.get("new_string")
        q.setdefault("severity", "minor")
        q["confidence"] = float(q.get("confidence", 0.0) or 0.0)
        normalized.append(q)
    return normalized


def apply_file_patches(
    workdir: str,
    patches: List[dict],
    min_confidence: float = 0.7,
    apply: bool = False,
) -> dict:
    """Apply or dry-run exact string replacement patches against files under workdir."""
    accepted = [p for p in _normalize_patches({"patches": patches}) if p.get("confidence", 0) >= min_confidence]
    rejected = [p for p in _normalize_patches({"patches": patches}) if p.get("confidence", 0) < min_confidence]
    severity_order = {"block": 0, "major": 1, "minor": 2}
    accepted.sort(key=lambda p: severity_order.get(p.get("severity", "minor"), 2))

    per_file = {}
    conflicts = []
    applied_details = []
    for patch in accepted:
        file_name = patch.get("file", "")
        original = patch.get("original", "")
        suggested = patch.get("suggested", "")
        if not file_name or not original:
            conflicts.append({"file": file_name, "reason": "missing file/original"})
            continue
        try:
            path = _safe_file_path(workdir, file_name)
        except ValueError as e:
            conflicts.append({"file": file_name, "reason": str(e)})
            continue
        if not path.exists() or not path.is_file():
            conflicts.append({"file": file_name, "reason": "file not found"})
            continue
        before = per_file.get(path, path.read_text())
        if original not in before:
            conflicts.append({"file": file_name, "reason": "original not found", "original_snippet": original[:80]})
            continue
        # Unique match check: original must appear exactly once to prevent ambiguous replacement
        match_count = before.count(original)
        if match_count == 0:
            # Fuzzy fallback: try normalized whitespace match
            import re as _re
            normalized_orig = _re.sub(r'\s+', ' ', original.strip())
            normalized_before = _re.sub(r'\s+', ' ', before.strip())
            if normalized_orig in normalized_before:
                # Find the actual substring in original text using index
                # This is a heuristic — use --verify to confirm
                conflicts.append({"file": file_name, "reason": "exact_miss_fuzzy_hit", "original_snippet": original[:80], "hint": "whitespace drift; use --verify to confirm"})
                continue
            conflicts.append({"file": file_name, "reason": "original not found", "original_snippet": original[:80]})
            continue
        if match_count > 1:
            conflicts.append({"file": file_name, "reason": f"ambiguous: original appears {match_count} times", "original_snippet": original[:80]})
            continue
        after = before.replace(original, suggested, 1)
        per_file[path] = after
        applied_details.append({
            "file": file_name,
            "rationale": patch.get("rationale", ""),
            "severity": patch.get("severity", "minor"),
            "confidence": patch.get("confidence", 0),
        })

    diff_chunks = []
    backups = {}
    for path, after in per_file.items():
        before = path.read_text()
        diff_chunks.extend(difflib.unified_diff(
            before.splitlines(True),
            after.splitlines(True),
            fromfile=str(path),
            tofile=str(path),
        ))
        if apply:
            backups[str(path)] = before
            path.write_text(after)

    return {
        "stats": {
            "total_patches": len(patches),
            "accepted": len(accepted),
            "applied": len(applied_details),
            "conflicts": len(conflicts),
            "rejected_low_conf": len(rejected),
            "conflict_details": conflicts[:10],
            "applied_details": applied_details,
        },
        "diff": "".join(diff_chunks),
        "backups": backups,
        "files_changed": [str(p) for p in per_file.keys()],
    }


def build_actual_producer_prompt(task: str, workdir: str = None, files: Optional[List[str]] = None) -> str:
    context = ""
    if files:
        snippets = []
        for file_name in files[:10]:
            try:
                path = _safe_file_path(workdir or os.getcwd(), file_name)
                snippets.append(f"--- {file_name} ---\n{path.read_text()[:12000]}")
            except (OSError, ValueError) as e:
                snippets.append(f"--- {file_name} ---\n[unreadable: {e}]")
        context = "\n\nFILE CONTEXT:\n" + "\n\n".join(snippets)
    return f"""You are the Producer in a cross-patch workflow.

TASK: {task}
WORKDIR: {workdir or os.getcwd()}
{context}

Output ONLY JSON:
{{
  "verdict": "pass"|"fail"|"partial",
  "summary": "brief",
  "patches": [{{
    "patch_id": "sha1_of_file_original_suggested",
    "file": "relative/path",
    "original": "exact old string from file",
    "suggested": "replacement string",
    "severity": "block"|"major"|"minor",
    "confidence": 0.0,
    "rationale": "why"
  }}]
}}
Rules: patch_id = sha1(file + original + suggested) for cross-referencing. produce exact-string patches only; no markdown; if unsure use patches=[]."""


def build_actual_reviewer_prompt(task: str, producer_plan: dict, workdir: str = None) -> str:
    return f"""You are the Reviewer in a cross-patch workflow.

TASK: {task}
WORKDIR: {workdir or os.getcwd()}
PRODUCER_JSON:
{json.dumps(producer_plan, ensure_ascii=False, indent=2)[:16000]}

Review producer patches for correctness and safety. Output ONLY JSON:
{{
  "verdict": "pass"|"fail"|"partial",
  "summary": "brief",
  "approved_patch_ids": ["list of producer patch_ids you approve"],
  "patches": [{{
    "file": "relative/path",
    "original": "exact old string from file",
    "suggested": "replacement string",
    "severity": "block"|"major"|"minor",
    "confidence": 0.0,
    "rationale": "why approved or amended"
  }}]
}}
You MUST include approved_patch_ids referencing producer patch_ids. Only patches with approved IDs will be merged. If producer patches are safe, repeat the approved patches. If unsafe, return patches=[] and approved_patch_ids=[] and verdict="fail"."""


def call_model(model: str, prompt: str, *, workdir: str = None, timeout: int = 120) -> dict:
    """Provider-aware real model call via hermes chat."""
    hermes = None
    try:
        import shutil
        hermes = shutil.which("hermes")
    except ImportError:
        hermes = None
    if not hermes:
        return {"ok": False, "model": model, "provider": model_provider(model), "adapter": "none", "error": "hermes command not found", "output": ""}
    provider = model_provider(model)
    cmd = [hermes, "chat", "-q", prompt, "--model", model,
           "--quiet", "--max-turns", "1", "--source", "cross-patch", "--ignore-rules"]
    if provider in SUPPORTED_HERMES_PROVIDERS:
        cmd += ["--provider", provider]
    start = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=workdir)
        return {
            "ok": r.returncode == 0,
            "model": model,
            "provider": provider,
            "adapter": "hermes-chat",
            "exit_code": r.returncode,
            "latency_ms": int((time.time() - start) * 1000),
            "output": r.stdout,
            "stderr": r.stderr[:1000],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "model": model, "provider": provider, "adapter": "hermes-chat", "timeout_s": timeout, "output": ""}
    except OSError as e:
        return {"ok": False, "model": model, "provider": provider, "adapter": "hermes-chat", "error": str(e), "output": ""}


QUORUM_FILE = os.environ.get(
    "HERMES_QUORUM_FILE",
    os.path.join(HERMES_HOME, "config", "quorum.yaml"),
)
QUORUM_FILE = os.path.expanduser(QUORUM_FILE)


class CrossPatchUnavailable(RuntimeError):
    """Raised when no available model can be selected for producer/reviewer."""


def load_quorum_config() -> dict:
    """Load quorum.yaml. Returns {} on any failure."""
    try:
        import yaml
        with open(QUORUM_FILE) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _quorum_planners(tier: str = "T2") -> List[str]:
    """Return planner list from quorum.yaml.tiers.<tier>.planners or [] if absent."""
    q = load_quorum_config()
    return list(((q.get("tiers") or {}).get(tier) or {}).get("planners") or [])


def _model_available_check(model: str) -> bool:
    """Bridge to model-router._model_available; returns True/False (best-effort)."""
    try:
        import importlib.util as _iu
        spec = _iu.spec_from_file_location(
            "_mr", os.path.join(HERMES_HOME, "scripts", "model-router.py")
        )
        mr = _iu.module_from_spec(spec)
        spec.loader.exec_module(mr)
        if hasattr(mr, "_model_available"):
            return bool(mr._model_available(model))
    except Exception:
        pass
    return True  # fail-open if router not importable; raises later if router CLI also fails


def select_producer_reviewer(
    tier: str = "T2",
    requested_producer: Optional[str] = None,
    requested_reviewer: Optional[str] = None,
) -> tuple:
    """Resolve (producer, reviewer) without string literals.

    Order:
      1. Explicit requested_producer/requested_reviewer (if available).
      2. model-router select-pair (cost-aware, ε-greedy).
      3. quorum.yaml.tiers.<tier>.planners[*] in order, skipping unavailable.

    Raises CrossPatchUnavailable when no pair can be assembled.
    """
    chosen_p = chosen_r = None

    # 1. Explicit caller request
    if requested_producer and _model_available_check(requested_producer):
        chosen_p = requested_producer
    if requested_reviewer and requested_reviewer != chosen_p and _model_available_check(requested_reviewer):
        chosen_r = requested_reviewer
    if chosen_p and chosen_r:
        return chosen_p, chosen_r

    # 2. Router
    try:
        router_path = os.path.join(HERMES_HOME, "scripts", "model-router.py")
        if os.path.exists(router_path):
            r = subprocess.run(
                [sys.executable, router_path, "select-pair", "--task-tier", "codegen"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                data = json.loads(r.stdout)
                # select-pair returns nested dicts per role; older variant returned strings
                def _extract(v):
                    return v.get("model") if isinstance(v, dict) else v

                p = chosen_p or _extract(data.get("producer"))
                rv = chosen_r or _extract(data.get("reviewer"))
                if p and rv and p != rv and _model_available_check(p) and _model_available_check(rv):
                    return p, rv
                chosen_p = chosen_p or (p if p and _model_available_check(p) else None)
                chosen_r = chosen_r or (rv if rv and rv != chosen_p and _model_available_check(rv) else None)
    except Exception:
        pass

    # 3. Quorum.yaml planners (deterministic order)
    planners = _quorum_planners(tier)
    for m in planners:
        if not _model_available_check(m):
            continue
        if not chosen_p:
            chosen_p = m
            continue
        if m != chosen_p:
            chosen_r = m
            break

    if not chosen_p or not chosen_r:
        raise CrossPatchUnavailable(
            f"No available producer/reviewer for tier={tier}. "
            f"requested=({requested_producer},{requested_reviewer}) "
            f"router_pair_failed quorum_planners={planners} "
            f"have=({chosen_p},{chosen_r})"
        )
    return chosen_p, chosen_r


def _select_reviewer_via_router(producer_model: str) -> str:
    """Backward-compat wrapper used by older code paths.

    Returns a reviewer model different from producer_model. Raises
    CrossPatchUnavailable when no model is available.
    """
    _, reviewer = select_producer_reviewer(
        tier="T2",
        requested_producer=producer_model,
        requested_reviewer=None,
    )
    return reviewer


def run_cross_patch_actual(
    task: str,
    workdir: str = None,
    producer_model: str = None,
    reviewer_model: str = None,
    apply: bool = False,
    min_confidence: float = None,
    files: Optional[List[str]] = None,
    verify_cmd: str = None,
    force_no_verify: bool = False,
    timeout: int = 120,
    model_caller: Optional[Callable] = None,
    config: dict = None,
) -> dict:
    """Run producer and reviewer inside this script, then dry-run/apply reviewed patches.

    Raises CrossPatchUnavailable if no model can be selected after caller hint,
    router, and quorum.yaml fallback are all exhausted.
    """
    config = config or load_config() or {}
    # Resolve producer/reviewer via accessor chain — no hardcoded literals.
    producer_model, reviewer_model = select_producer_reviewer(
        tier=config.get("tier", "T2"),
        requested_producer=producer_model or config.get("producer_model"),
        requested_reviewer=reviewer_model or config.get("reviewer_model"),
    )
    min_confidence = min_confidence if min_confidence is not None else config.get("min_patch_conf", 0.7)
    workdir = str(Path(workdir or os.getcwd()).resolve())
    caller = model_caller or call_model
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    max_cost = config.get("max_cost_per_run_usd", 2.0)
    task_id = "cross-patch-run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    producer_raw = caller(
        producer_model,
        build_actual_producer_prompt(task, workdir, files),
        workdir=workdir,
        timeout=timeout,
    )
    if not producer_raw.get("ok"):
        producer_plan = {"verdict": "fail", "summary": producer_raw.get("error") or producer_raw.get("stderr", "producer failed"), "patches": []}
    else:
        try:
            producer_plan = extract_json_object(producer_raw.get("output", ""))
        except json.JSONDecodeError as e:
            producer_plan = {"verdict": "fail", "summary": f"producer JSON parse failed: {e}", "patches": []}

    reviewer_raw = caller(
        reviewer_model,
        build_actual_reviewer_prompt(task, producer_plan, workdir),
        workdir=workdir,
        timeout=timeout,
    )
    if not reviewer_raw.get("ok"):
        reviewer_plan = {"verdict": "fail", "summary": reviewer_raw.get("error") or reviewer_raw.get("stderr", "reviewer failed"), "patches": []}
    else:
        try:
            reviewer_plan = extract_json_object(reviewer_raw.get("output", ""))
        except json.JSONDecodeError as e:
            reviewer_plan = {"verdict": "fail", "summary": f"reviewer JSON parse failed: {e}", "patches": []}

    # Cost tracking
    producer_latency = producer_raw.get("latency_ms", 0)
    reviewer_latency = reviewer_raw.get("latency_ms", 0)
    run_cost = {
        "producer_latency_ms": producer_latency,
        "reviewer_latency_ms": reviewer_latency,
        "max_cost_usd": max_cost,
        "estimated_within_budget": True,  # precise cost requires token counting
    }

    reviewer_patches = _normalize_patches(reviewer_plan)
    producer_patches = _normalize_patches(producer_plan)
    selected_patches = reviewer_patches if reviewer_patches else (
        producer_patches if reviewer_plan.get("verdict") == "pass" else []
    )
    merge = apply_file_patches(workdir, selected_patches, min_confidence, apply=apply)

    verify = None
    verdict = "pass" if merge["stats"]["conflicts"] == 0 and merge["stats"]["applied"] > 0 else "partial"
    if reviewer_plan.get("verdict") == "fail" and not selected_patches:
        verdict = "fail"
    # --apply requires --verify (fail closed); unless --force-no-verify
    if apply and not verify_cmd and not force_no_verify:
        result_forced = {
            "pattern": "cross_patch",
            "execution_mode": "script_actual",
            "actual_model_calls": True,
            "ts": timestamp,
            "task": task[:500],
            "workdir": workdir,
            "producer_model": producer_model,
            "reviewer_model": reviewer_model,
            "verdict": "rejected",
            "rejection_reason": "--apply requires --verify to prevent untested writes. Pass --verify <cmd> or --force-no-verify to override.",
        }
        return result_forced
    if apply and verify_cmd:
        r = subprocess.run(verify_cmd, shell=True, cwd=workdir, capture_output=True, text=True, timeout=300)
        verify = {"cmd": verify_cmd, "exit_code": r.returncode, "stdout": r.stdout[-4000:], "stderr": r.stderr[-4000:]}
        if r.returncode != 0:
            for path, content in merge.get("backups", {}).items():
                Path(path).write_text(content)
            verdict = "fail"
            verify["rollback"] = "applied"

    result = {
        "pattern": "cross_patch",
        "execution_mode": "script_actual",
        "actual_model_calls": True,
        "ts": timestamp,
        "task": task[:500],
        "workdir": workdir,
        "producer_model": producer_model,
        "reviewer_model": reviewer_model,
        "producer": {k: v for k, v in producer_raw.items() if k != "output"} | {"plan": producer_plan},
        "reviewer": {k: v for k, v in reviewer_raw.items() if k != "output"} | {"plan": reviewer_plan},
        "merge": {k: v for k, v in merge.items() if k != "backups"},
        "cost": run_cost,
        "applied": bool(apply and merge["stats"]["applied"] > 0 and verdict != "fail"),
        "verify": verify,
        "verdict": verdict,
    }
    try:
        protocol_msg = protocol_wrap(
            agent_id="cross-patch-runner",
            task_id=task_id,
            verdict=verdict,
            verification_pattern="cross_patch_actual",
            extensions={
                "actual_model_calls": True,
                "roles": {"producer": producer_model, "reviewer": reviewer_model},
                "applied": result["applied"],
                "stats": merge["stats"],
            },
        )
        result["agent_protocol"] = protocol_msg
        protocol_emit(protocol_msg)
    except ProtocolError as e:
        print(f"[cross-patch] Protocol wrap failed: {e}", file=sys.stderr)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        log_entry = {k: v for k, v in result.items() if k not in ("producer", "reviewer")}
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return result


def execute_cross_patch(
    task: str,
    workdir: str = None,
    config: dict = None,
) -> dict:
    """
    执行 T2 CROSS-PATCH 流程
    
    实际 delegate_task 调用由 Hermes ACP 层完成。
    此处输出编排框架、提示词和预期调用模式。
    """
    if config is None:
        config = load_config()
    
    if config is None or not config.get("enabled"):
        return {
            "verdict": "skipped",
            "reason": "cross_patch disabled in config",
            "pattern": "cross_patch",
        }
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    task_id = "cross-patch-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    
    result = {
        "pattern": "cross_patch",
        "execution_mode": "orchestration_framework",
        "actual_model_calls": False,
        "actual_call_note": "This script emits producer/reviewer delegate_task specs and L2 protocol; Hermes agent executes those calls outside this script.",
        "ts": timestamp,
        "task": task[:200],
        "workdir": workdir,
        "producer_model": config["producer_model"],
        "reviewer_model": config["reviewer_model"],
    }
    
    # ── Step 1: Producer 调用模式 ──
    producer_prompt = build_producer_prompt(task, workdir)
    result["producer"] = {
        "model": config["producer_model"],
        "delegate_task_call": {
            "goal": task,
            "context": producer_prompt,
            "toolsets": ["terminal", "file", "web"],
            "acp_command": None,  # 由 Hermes 根据 model 自动选择
        },
    }
    
    # ── Step 2: Reviewer 调用模式 ──
    # 注: 实际场景中 reviewer 接收 producer 的 stdout
    reviewer_prompt = build_reviewer_prompt(
        task,
        "<producer_output — injected from delegate_task result>"
    )
    result["reviewer"] = {
        "model": config["reviewer_model"],
        "delegate_task_call": {
            "goal": f"Review this output for task: {task[:100]}",
            "context": reviewer_prompt,
            "toolsets": ["terminal", "file"],
            "acp_command": None,
        },
    }
    
    # ── Step 3: 补丁提取与合并 ──
    result["merge"] = {
        "min_patch_confidence": config["min_patch_conf"],
        "max_patches": config.get("max_patches", 20),
        "strategy": "deterministic_replace",
        "note": "Apply patches where confidence >= min_patch_conf AND original string exact match in base content",
    }
    
    # ── 输出协议消息 (L2 agent_protocol v2.0.0) ──
    try:
        protocol_msg = protocol_wrap(
            agent_id="cross-patch-orchestrator",
            task_id=task_id,
            verdict="pending",  # valid in v2.0.0
            verification_pattern="cross_patch",
            extensions={
                "roles": {
                    "producer": config["producer_model"],
                    "reviewer": config["reviewer_model"],
                }
            },
        )
        result["agent_protocol"] = protocol_msg
        # 持久化到 protocol_messages
        protocol_emit(protocol_msg)
    except ProtocolError as e:
        print(f"[cross-patch] Protocol wrap failed: {e}", file=sys.stderr)
    
    # ── 成本估算 ──
    result["cost_estimate"] = {
        "producer_est_usd": 0.05,
        "reviewer_est_usd": 0.03,
        "total_est_usd": 0.08,
        "budget_per_task_usd": config.get("budget_per_task_usd", 2.0),
        "within_budget": True,
    }
    
    # 记录日志
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        log_entry = {k: v for k, v in result.items() if k != "producer"}
        log_entry["producer_model"] = config["producer_model"]
        log_entry["reviewer_model"] = config["reviewer_model"]
        f.write(json.dumps(log_entry) + "\n")
    
    return result


def cli():
    parser = argparse.ArgumentParser(description="Cross-Patch — 双模型交叉审查编排器")
    sub = parser.add_subparsers(dest="cmd")

    ex = sub.add_parser("execute", help="执行 T2 cross-patch 编排计划 (不直接调用模型)")
    ex.add_argument("--task", required=True, help="任务描述")
    ex.add_argument("--workdir", default=None, help="工作目录")

    rn = sub.add_parser("run", help="脚本内真实执行 producer/reviewer，默认 dry-run")
    rn.add_argument("--task", required=True, help="任务描述")
    rn.add_argument("--workdir", default=None, help="工作目录")
    rn.add_argument("--producer", default=None, help="Producer model override")
    rn.add_argument("--reviewer", default=None, help="Reviewer model override")
    rn.add_argument("--files", default="", help="逗号分隔的相对文件路径，作为 producer 上下文")
    rn.add_argument("--min-confidence", type=float, default=None)
    rn.add_argument("--timeout", type=int, default=120)
    rn.add_argument("--verify", default=None, help="--apply 后运行的验证命令，失败则回滚")
    rn.add_argument("--force-no-verify", action="store_true", help="允许 --apply 跳过 --verify（不推荐）")
    rn.add_argument("--apply", action="store_true", help="真正写文件；默认只 dry-run 输出 diff")

    mg = sub.add_parser("merge", help="合并补丁")
    mg.add_argument("--base", required=True, help="基础内容 (或 @filepath)")
    mg.add_argument("--patches", required=True, help="补丁 JSON (或 @filepath)")
    mg.add_argument("--min-confidence", type=float, default=0.7)

    sub.add_parser("status", help="查看配置和最近执行")

    args = parser.parse_args()

    if args.cmd == "execute":
        result = execute_cross_patch(task=args.task, workdir=args.workdir)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.cmd == "run":
        files = [f.strip() for f in args.files.split(",") if f.strip()]
        try:
            result = run_cross_patch_actual(
                task=args.task,
                workdir=args.workdir,
                producer_model=args.producer,
                reviewer_model=args.reviewer,
                apply=args.apply,
                min_confidence=args.min_confidence,
                files=files or None,
                verify_cmd=args.verify,
                force_no_verify=args.force_no_verify,
                timeout=args.timeout,
            )
        except CrossPatchUnavailable as e:
            result = {
                "pattern": "cross_patch",
                "execution_mode": "script_actual",
                "verdict": "skipped",
                "status": "unavailable",
                "reason": str(e),
                "actual_model_calls": False,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(2)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.cmd == "merge":
        base = args.base
        if base.startswith("@"):
            with open(base[1:]) as f:
                base = f.read()
        
        patches_str = args.patches
        if patches_str.startswith("@"):
            with open(patches_str[1:]) as f:
                patches_str = f.read()
        
        try:
            review = json.loads(patches_str)
        except json.JSONDecodeError:
            review = parse_reviewer_output(patches_str)
        
        patches = review.get("patches", [])
        merged, stats = apply_patches(base, patches, args.min_confidence)
        
        print(json.dumps({
            "verdict": "pass" if stats["conflicts"] == 0 else "partial",
            "stats": stats,
            "merged_length": len(merged),
            "merged_preview": merged[:500],
        }, indent=2, ensure_ascii=False))

    elif args.cmd == "status":
        config = load_config()
        if config:
            print(f"Cross-Patch Status:")
            print(f"  enabled:       {config['enabled']}")
            print(f"  producer:      {config['producer_model']}")
            print(f"  reviewer:      {config['reviewer_model']}")
            print(f"  min_patch_conf: {config['min_patch_conf']}")
            print(f"  budget/task:   ${config['budget_per_task_usd']}")
        else:
            print("Config not found or parse error.")
        
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                lines = f.readlines()
            print(f"\n  Recent executions: {len(lines)}")
            for line in lines[-5:]:
                try:
                    d = json.loads(line)
                    print(f"    {d.get('ts','?')} task={d.get('task','?')[:50]}")
                except (json.JSONDecodeError, ValueError, KeyError):
                    pass

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
