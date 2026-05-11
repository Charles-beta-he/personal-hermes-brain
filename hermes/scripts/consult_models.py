#!/usr/bin/env python3
"""
consult_models.py — 多脑 fan-out 编排器 v3 (替代 consult-models.sh)

Phase 0 shadow → Phase 3 steady: 读取 quorum.yaml, 选择 planner, fan-out 调用,
运行 consensus, emit protocol 消息, 清理工作目录。

用法:
  python3 consult_models.py run <state.json> [--tier T2] [--shadow]
  python3 consult_models.py run <state.json> --quorum 2 --tier T1
  python3 consult_models.py status  # 读取 quorum.yaml 当前配置

与 v2(shell) 的区别:
  - 读取 quorum.yaml (不再硬编码)
  - L2 agent_protocol emit (全链路可追踪)
  - TICK_DIR 自动清理 (除非 --keep)
  - 每 planner 有 timeout (默认 120s)
  - Python 原生错误处理 (无 2>/dev/null)
"""

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional, Tuple

try:
    import yaml
except ImportError:  # PyYAML is optional for import-time safety in tests/tools.
    yaml = None

# ── 路径 ──
HERMES_HOME = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))
SCRIPTS_DIR = os.path.join(HERMES_HOME, "scripts")
CONFIG_DIR = os.path.join(HERMES_HOME, "config")
LOG_DIR = os.path.join(HERMES_HOME, "logs")

# ── L2 协议导入 ──
sys.path.insert(0, SCRIPTS_DIR)
from agent_protocol import (
    wrap as protocol_wrap,
    emit as protocol_emit,
    ProtocolError,
)

# ── SPL encoding (optional, for token savings) ──
try:
    sys.path.insert(0, os.path.join(HERMES_HOME, "hermes-agent"))
    from agent.spl import SPLEncoder, SPLTier, spl_prompt_for_model
    _spl_encoder = SPLEncoder()
    _spl_available = True
except ImportError:
    _spl_available = False

DEFAULT_TIMEOUT = 120  # per-planner timeout (seconds)
TICK_CLEANUP_AGE = 86400  # 24h — 清理旧 TICK_DIR
SUPPORTED_HERMES_PROVIDERS = {
    "openai-codex", "anthropic", "xiaomi", "openrouter", "gemini", "xai",
    "ollama-cloud", "huggingface", "zai", "kimi-coding", "kimi-coding-cn",
    "stepfun", "minimax", "minimax-cn", "kilocode", "arcee", "nvidia",
}

try:
    import model_quota
except Exception:  # quota must be best-effort, never break legacy fan-out import
    model_quota = None


def load_quorum() -> dict:
    """读取 quorum.yaml"""
    path = os.path.join(CONFIG_DIR, "quorum.yaml")
    if yaml is None:
        print("[consult_models] PyYAML unavailable; quorum.yaml skipped", file=sys.stderr)
        return {}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, FileNotFoundError, OSError) as e:
        print(f"[consult_models] quorum.yaml load failed: {e}", file=sys.stderr)
        return {}


def load_config() -> dict:
    """读取 config.yaml"""
    path = os.path.join(HERMES_HOME, "config.yaml")
    if yaml is None:
        return {}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, FileNotFoundError, OSError):
        return {}


def get_tier_planners(quorum: dict, tier: str, skip_claude: bool = False) -> Tuple[List[str], int, int]:
    """
    从 quorum.yaml 读取 tier 配置。

    返回 (planner_list, quorum_count, min_quorum)
    """
    tiers = quorum.get("tiers", {})
    tier_cfg = tiers.get(tier, {})
    planners = tier_cfg.get("planners", [])

    # Claude budget guard
    if skip_claude or _claude_excluded(quorum):
        planners = [m for m in planners if "claude" not in m.lower()]

    q = tier_cfg.get("quorum", 3)
    mq = tier_cfg.get("min_quorum", 2)

    return planners, q, mq


def _claude_excluded(quorum: dict) -> bool:
    """检查 Claude budget 是否排除"""
    budget_guard = quorum.get("claude_budget_guard", {})
    if budget_guard.get("exclude_below_5_usd"):
        # 简单检查: 如果 budget tracker 说不能使用
        try:
            r = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS_DIR, "claude-budget-tracker.py"),
                 "can-use"],
                capture_output=True, text=True, timeout=10,
            )
            return r.returncode != 0
        except Exception:
            return True  # 无法确认 → 保守排除
    return False


def cleanup_old_ticks():
    """清理超过 TICK_CLEANUP_AGE 的旧 TICK_DIR"""
    import shutil
    now = time.time()
    for entry in os.listdir(HERMES_HOME):
        path = os.path.join(HERMES_HOME, entry)
        if entry.startswith("tick-") and os.path.isdir(path):
            try:
                mtime = os.path.getmtime(path)
                if now - mtime > TICK_CLEANUP_AGE:
                    shutil.rmtree(path)
                    print(f"[consult_models] Cleaned old tick: {entry}", file=sys.stderr)
            except OSError:
                pass


def compute_state_hash(state_file: str) -> str:
    """计算 state.json 的 SHA256"""
    with open(state_file, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _env_int(name: str, default: Any) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return int(default)


def _strict_true(value: Any) -> bool:
    """Return True only for a real JSON boolean true, never truthy strings."""
    return value is True


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
        return parsed if math.isfinite(float(parsed)) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _strict_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


MAX_PLANNER_STATE_CHARS = _env_int("HERMES_MULTI_BRAIN_MAX_STATE_CHARS", "24000")
CRITICAL_STATE_FIELDS = [
    "schema", "question", "constraints", "acceptance_criteria", "non_goals",
    "risk_level", "budget", "claims", "evidence", "evidence_bundle", "truth_gate",
    "state_owner", "implementation_target",
]

COMM_PACKET_SCHEMA_VERSION = "multi_model_comm_packet_v1"
CERTIFICATION_MANIFEST_SCHEMA_VERSION = "certification_manifest_v1"
EVIDENCE_FULFILLMENT_SCHEMA_VERSION = "evidence_fulfillment_v1"
MAX_COMM_TEXT_CHARS = _env_int("HERMES_MULTI_BRAIN_MAX_COMM_TEXT_CHARS", "320")
MAX_EVIDENCE_OUTPUT_CHARS = _env_int("HERMES_MULTI_BRAIN_EVIDENCE_OUTPUT_CHARS", "4000")


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json_file(path: str, default: Any = None) -> Any:
    try:
        with open(os.path.expanduser(path)) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json_atomic(path: str, data: Any) -> None:
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def _safe_artifact_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "unknown")).strip("._") or "unknown"


def _normalize_target_file(value: Any) -> str:
    """Normalize model-reported target paths before issue grouping.

    Reviewers may say `consult_models.py` while repo artifacts use
    `scripts/consult_models.py`; without normalization, RMCS inflates one real
    disagreement into multiple blockers and cannot converge.
    """
    target = str(value or "<unknown>").replace("\\", "/").strip()
    if target in ("", "."):
        return "<unknown>"
    while target.startswith("./"):
        target = target[2:]
    if target.startswith(f"{os.path.basename(HERMES_HOME)}/"):
        target = target.split("/", 1)[1]
    if "/" not in target:
        candidate = os.path.join(HERMES_HOME, "scripts", target)
        if os.path.exists(candidate):
            return f"scripts/{target}"
    return target


def _short_hash(obj: Any) -> str:
    return hashlib.sha256(_stable_json(obj).encode("utf-8")).hexdigest()[:16]


def _truncate_text(value: Any, limit: int = MAX_COMM_TEXT_CHARS) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 24)] + f"…<truncated:{len(text)}>"


def _approx_tokens(text_or_chars: Any) -> int:
    if isinstance(text_or_chars, int):
        chars = text_or_chars
    else:
        chars = len(str(text_or_chars or ""))
    return max(1, (chars + 3) // 4)


def _artifact_ref(name: str, payload: Any) -> dict:
    raw = _stable_json(payload)
    return {
        "name": name,
        "sha256_16": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
        "chars": len(raw),
        "approx_tokens": _approx_tokens(len(raw)),
        "policy": "not_inlined_full_payload; request specific evidence if needed",
    }


def _summarize_patches(patches: List[dict], limit: int = 8) -> List[dict]:
    out: List[dict] = []
    for patch in (patches or [])[:limit]:
        if not isinstance(patch, dict):
            continue
        out.append({
            "id": patch.get("id") or _patch_signature(patch),
            "target_file": patch.get("target_file") or patch.get("file") or "",
            "op": patch.get("op", ""),
            "risk": patch.get("risk", ""),
            "blast_radius": patch.get("blast_radius", ""),
            "depends_on": patch.get("depends_on", []) or [],
            "rationale": _truncate_text(patch.get("rationale", ""), 180),
        })
    if len(patches or []) > limit:
        out.append({"id": "<omitted>", "omitted_patch_count": len(patches or []) - limit})
    return out


def _summarize_fanout_certification(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    keep = {
        key: value.get(key)
        for key in (
            "schema_version", "status", "certified", "multi_model_certified",
            "certification_scope", "below_min_quorum", "success_count", "fail_count",
            "planner_count", "min_quorum", "reason",
        )
        if key in value
    }
    keep["source_hash"] = _short_hash(value)
    keep["source_chars"] = len(_stable_json(value))
    if "reason" in keep:
        keep["reason"] = _truncate_text(keep["reason"], 220)
    keep["policy"] = "bounded_summary_only"
    return keep


def _summarize_truth_gate(truth_gate: dict) -> dict:
    if not isinstance(truth_gate, dict):
        return {}
    compact = {
        "truth_status": truth_gate.get("truth_status"),
        "can_certify_truth": truth_gate.get("can_certify_truth"),
        "claim_count": truth_gate.get("claim_count"),
        "verified_claim_count": truth_gate.get("verified_claim_count"),
        "evidence_coverage": truth_gate.get("evidence_coverage"),
        "unsupported_high_severity_claim_ids": (truth_gate.get("unsupported_high_severity_claim_ids") or [])[:20],
        "contradicted_high_severity_claim_ids": (truth_gate.get("contradicted_high_severity_claim_ids") or [])[:20],
        "unsupported_claim_ids": (truth_gate.get("unsupported_claim_ids") or [])[:20],
        "contradicted_claim_ids": (truth_gate.get("contradicted_claim_ids") or [])[:20],
        "reasons": [_truncate_text(r, 220) for r in (truth_gate.get("reasons") or [])[:8]],
        "source_hash": _short_hash(truth_gate),
        "source_chars": len(_stable_json(truth_gate)),
    }
    return {k: v for k, v in compact.items() if v not in (None, [], {})}


def _finalize_packet_token_budget(packet: dict, raw_chars: int) -> dict:
    packet.setdefault("token_budget", {})
    no_savings_mode_set = False
    for _ in range(50):
        actual_packet_chars = len(json.dumps(packet, ensure_ascii=False))
        chars_saved = max(0, raw_chars - actual_packet_chars)
        if chars_saved <= 0 and not no_savings_mode_set:
            packet["mode"] = "manifest_delta_no_savings"
            packet["token_budget"]["policy"] = "no savings claimed; packet retained for schema consistency"
            no_savings_mode_set = True
            continue
        packet["token_budget"].update({
            "raw_context_chars": raw_chars,
            "packet_chars": actual_packet_chars,
            "estimated_chars_saved": chars_saved,
            "estimated_tokens_saved": 0 if chars_saved <= 0 else _approx_tokens(chars_saved),
            "compression_ratio": round(actual_packet_chars / raw_chars, 4) if raw_chars else 1.0,
        })
        if len(json.dumps(packet, ensure_ascii=False)) == actual_packet_chars:
            return packet
    # Extremely unlikely fallback: keep telemetry honest even if JSON digit lengths did
    # not converge inside the safety cap.
    actual_packet_chars = len(json.dumps(packet, ensure_ascii=False))
    packet["token_budget"].update({
        "raw_context_chars": raw_chars,
        "packet_chars": actual_packet_chars,
        "estimated_chars_saved": 0,
        "estimated_tokens_saved": 0,
        "compression_ratio": round(actual_packet_chars / raw_chars, 4) if raw_chars else 1.0,
        "policy": "size telemetry did not converge; no savings claimed",
    })
    return packet


def _summarize_current_best(current_best: dict) -> dict:
    current_best = current_best or {}
    diagnosis = current_best.get("diagnosis") if isinstance(current_best.get("diagnosis"), dict) else {}
    return {
        "diagnosis_summary": _truncate_text(diagnosis.get("summary") or current_best.get("summary", ""), 360),
        "patches": _summarize_patches(current_best.get("patches", []) or []),
        "certification_status": current_best.get("certification_status") or current_best.get("status"),
        "degradation_reasons": current_best.get("degradation_reasons", [])[:5] if isinstance(current_best.get("degradation_reasons"), list) else [],
        "fanout_certification": _summarize_fanout_certification(current_best.get("fanout_certification", {})),
        "planner_patch_summary": current_best.get("planner_patch_summary") if isinstance(current_best.get("planner_patch_summary"), dict) else {},
        "source_hash": _short_hash(current_best),
    }


def _summarize_issues(issues: List[dict], limit: int = 12) -> List[dict]:
    compact: List[dict] = []
    for issue in (issues or [])[:limit]:
        if not isinstance(issue, dict):
            continue
        compact.append({
            "id": issue.get("id"),
            "status": issue.get("status"),
            "severity": issue.get("severity"),
            "target_file": issue.get("target_file") or issue.get("target_model"),
            "models": issue.get("models", [])[:8] if isinstance(issue.get("models"), list) else issue.get("models"),
            "missing_models": issue.get("missing_models", [])[:8] if isinstance(issue.get("missing_models"), list) else issue.get("missing_models"),
            "claim": _truncate_text(issue.get("claim", ""), 260),
            "resolution": _truncate_text(issue.get("resolution", ""), 220),
            "evidence_refs": _compact_evidence_refs(issue.get("evidence")),
        })
    if len(issues or []) > limit:
        compact.append({"id": "<omitted>", "omitted_issue_count": len(issues or []) - limit})
    return compact


def _compact_evidence_refs(evidence: Any, limit: int = 5) -> List[dict]:
    if not isinstance(evidence, list):
        if evidence:
            return [{"summary": _truncate_text(evidence, 160)}]
        return []
    refs = []
    for item in evidence[:limit]:
        if isinstance(item, dict):
            refs.append({
                "id": item.get("id") or item.get("patch_id") or item.get("evidence_id"),
                "model": item.get("model"),
                "op": item.get("op"),
                "summary": _truncate_text(item.get("summary") or item.get("rationale") or item.get("text") or "", 160),
            })
        else:
            refs.append({"summary": _truncate_text(item, 160)})
    if len(evidence) > limit:
        refs.append({"id": "<omitted>", "omitted_evidence_count": len(evidence) - limit})
    return refs


def _summarize_evidence_bundle(evidence_bundle: dict) -> dict:
    evidence_bundle = evidence_bundle or {}
    grounding = evidence_bundle.get("grounding") if isinstance(evidence_bundle.get("grounding"), dict) else {}
    compact_grounding = {}
    for claim_id, info in list(grounding.items())[:20]:
        if not isinstance(info, dict):
            continue
        compact_grounding[claim_id] = {
            "truth_status": info.get("truth_status"),
            "supporting_evidence_ids": info.get("supporting_evidence_ids", [])[:8],
            "contradicting_evidence_ids": info.get("contradicting_evidence_ids", [])[:8],
        }
    return {
        "schema_version": evidence_bundle.get("schema_version"),
        "claim_count": len(evidence_bundle.get("claims", []) or []),
        "evidence_count": len(evidence_bundle.get("evidence", []) or []),
        "grounding": compact_grounding,
        "source_hash": _short_hash(evidence_bundle),
        "note": "Full evidence bodies are omitted; use evidence_requests for missing claim/evidence details.",
    }


def build_discussion_comm_packet(
    current_best: dict,
    unresolved_issues: List[dict],
    evidence_bundle: dict,
    truth_gate: dict,
    round_no: int,
    previous_transcript: Optional[List[dict]] = None,
) -> dict:
    """Build a compact manifest/delta discussion packet for reviewer models.

    The packet avoids repeatedly broadcasting full merged plans and evidence bodies to
    every model. It sends hashes/manifests, patch/issue summaries, the current truth
    gate, and only the current unresolved delta. Reviewers must request specific
    evidence instead of assuming omitted payloads.
    """
    previous_transcript = previous_transcript or []
    raw_context = {
        "current_best": current_best,
        "unresolved_issues": unresolved_issues,
        "evidence_bundle": evidence_bundle,
        "truth_gate": truth_gate,
        "previous_transcript": previous_transcript,
    }
    last_round = previous_transcript[-1] if previous_transcript else {}
    last_votes = []
    for vote in (last_round.get("votes", []) if isinstance(last_round, dict) else [])[:8]:
        if isinstance(vote, dict):
            last_votes.append({"model": vote.get("model"), "vote": vote.get("vote"), "best_within_constraints": _strict_true(vote.get("best_within_constraints"))})
    packet = {
        "schema": COMM_PACKET_SCHEMA_VERSION,
        "mode": "manifest_delta",
        "artifact_manifest": {
            "current_best": _artifact_ref("current_best", current_best),
            "evidence_bundle": _artifact_ref("evidence_bundle", evidence_bundle),
            "truth_gate": _artifact_ref("truth_gate", truth_gate),
            "previous_transcript": _artifact_ref("previous_transcript", previous_transcript),
        },
        "round_delta": {
            "round": round_no,
            "unresolved_issues": _summarize_issues(unresolved_issues),
            "previous_round_status": (last_round.get("status") if isinstance(last_round, dict) else None),
            "previous_round_votes": last_votes,
        },
        "current_best_summary": _summarize_current_best(current_best),
        "evidence_summary": _summarize_evidence_bundle(evidence_bundle),
        "truth_gate": _summarize_truth_gate(truth_gate),
        "instructions": [
            "Use only this packet plus cited evidence summaries; do not assume omitted payload bodies.",
            "Discuss only unresolved round_delta issues and novel severity>=3 blockers.",
            "If a fact needs omitted detail, emit evidence_requests rather than restating full context.",
            "Vote approve only if best_within_constraints and truth_gate permits certification.",
            "An empty current_best_summary.patches list is not by itself a blocker when current_best_summary.planner_patch_summary.certification_intent == 'no_action_certification' and concrete_patch_count == 0; treat it as evidence that planners explicitly signed off with noop/advisory patches, not as a dropped-patch contradiction.",
        ],
        "required_output": {
            "critiques": [{"target_model": "...", "severity": 1, "claim": "...", "evidence": "evidence id/ref, not full blob", "correction": "...", "novel": True}],
            "evidence_requests": [{"claim_id": "C-001", "tool_needed": "terminal|file|web|brainctl", "command": "read-only command/query", "why": "what this would verify"}],
            "vote": "approve|amend|reject",
            "best_within_constraints": True,
            "reasoning": "<=600 chars, cite issue/evidence ids",
        },
    }
    raw_chars = len(json.dumps(raw_context, ensure_ascii=False))
    return _finalize_packet_token_budget(packet, raw_chars)


def _planner_state_payload(state: dict) -> Tuple[str, bool]:
    """Return planner-visible state without silently dropping truth-critical fields.

    Historical prompts sliced state_json at 8k chars. That can remove claims/evidence
    after the truth gate attaches them. If the state is too large, compact to critical
    fields and mark the payload as truncated so reviewers can request missing context.
    """
    raw = json.dumps(state, indent=2, ensure_ascii=False)
    if len(raw) <= MAX_PLANNER_STATE_CHARS:
        return raw, False
    compact = {k: state.get(k) for k in CRITICAL_STATE_FIELDS if k in state}
    compact["state_truncated"] = True
    compact["omitted_fields"] = [k for k in state.keys() if k not in compact]
    compact["truncation_policy"] = (
        "Original state exceeded planner prompt budget; orchestrator preserved "
        "claims/evidence/evidence_bundle/truth_gate and omitted non-critical fields."
    )
    return json.dumps(compact, indent=2, ensure_ascii=False), True


def build_planner_prompt(state: dict, state_hash: str, model: str, tier: str) -> str:
    """构建 planner 提示词 (同 consult-models.sh v2 格式)"""
    state_json, state_truncated = _planner_state_payload(state)
    truncation_notice = ""
    if state_truncated:
        truncation_notice = (
            "\nSTATE_TRUNCATION_NOTICE: non-critical fields were omitted, but "
            "claims/evidence/evidence_bundle/truth_gate were preserved. Request evidence "
            "instead of certifying any omitted fact.\n"
        )
    return f"""You are a Hermes Agent architecture planner.

Read the state below and produce a structured improvement plan.

STATE (sha256: {state_hash}):{truncation_notice}
{state_json}

Output ONLY valid JSON matching this schema:
{{
  "meta": {{"planner_model": "{model}", "planner_role": "architect", "state_hash": "{state_hash}", "tier_target": "{tier}", "confidence": 0.0-1.0}},
  "diagnosis": {{"root_cause_class": "regression|router_skew|verifier_gap|kill_switch_oscillation|consensus_drift|pricing_overrun|schema_mismatch|no_action", "evidence_field_ids": ["field1"], "summary": "..."}},
  "patches": [{{"id": "unique", "target_file": "path", "op": "tune_threshold|swap_model|add_verifier|modify_router_weight|raise_tier|lower_tier|noop", "rationale": "...", "risk": "low|med|high", "blast_radius": "single_tier|router|all_tiers|kill_switch", "depends_on": []}}],
  "verification": {{"expected_metric_delta": {{"main_pass_rate": 0.0}}, "guard_metrics": ["main_pass_rate"], "tier_eval_plan": "T0_only|T0_T1|T1_T2|full_T0_T3"}},
  "evidence_requests": [{{"claim_id": "C-001", "tool_needed": "terminal|file|web", "command": "read-only command/query", "why": "missing evidence needed before truth certification"}}],
  "rollback_signal": {{"auto_rollback_if": "main_pass_rate < pre - 0.05", "kill_switch_inc": false}}
}}

Rules:
- Multi-model agreement is not truth verification.
- Cite evidence_bundle.grounding when relying on factual claims.
- If evidence is missing, add evidence_requests instead of asserting you verified it.
- Use `patches` only for concrete implementation deltas. Conditional verifier ideas
  ("add a test if missing", "only if fresh tick fails", "verify whether coverage exists")
  are evidence_requests/advisories, not patches. If orchestrator evidence already
  proves the verifier exists, output a noop patch citing that evidence instead of a
  conditional `add_verifier` patch.

Keep patches ≤ 5. Be concrete. Confidence must be honest."""


def model_provider(config: dict, model: str) -> str:
    """Resolve provider for a model from pricing config."""
    return (
        config.get("pricing", {})
        .get("models", {})
        .get(model, {})
        .get("provider", "")
    )


def _provider_map_for_models(models: List[str], config: dict) -> Dict[str, str]:
    providers: Dict[str, str] = {}
    for model in models:
        provider = model_provider(config, model)
        if not provider and model_quota:
            provider = model_quota.provider_for_model(model, config)
        providers[model] = provider or "unknown"
    return providers


def filter_planners_by_quota(
    planners: List[str],
    config: dict,
    quota_snapshot: Optional[dict] = None,
) -> Tuple[List[str], List[dict], dict]:
    """Filter exhausted planners while preserving exact/estimated quota provenance.

    Unknown/unobservable quota is allowed but attached to state/output. Only explicit
    `status=exhausted` is a hard gate.
    """
    if not model_quota:
        return planners, [], {}
    providers = _provider_map_for_models(planners, config)
    snapshots = quota_snapshot or model_quota.snapshot_models(planners, config=config)
    # Ensure every selected planner has an attached snapshot, even when the caller
    # supplied a partial test/fixture snapshot.
    attached = dict(snapshots)
    for model in planners:
        provider = providers.get(model, "unknown")
        key = model_quota.quota_key(provider, model)
        default = model_quota.default_snapshot(model, provider)
        supplied = attached.get(key) or attached.get(model) or {}
        merged = dict(default)
        merged.update(supplied)
        attached[key] = merged
    allowed, skipped = model_quota.gate_models(planners, attached, providers=providers)
    return allowed, skipped, attached


def select_planners_for_fanout(
    planners: List[str],
    q_count: int,
    config: dict,
    quota_snapshot: Optional[dict] = None,
) -> Tuple[List[str], List[dict], dict]:
    """Apply quota gate before quorum trimming.

    If the first N planners are exhausted, later healthy planners should still be
    eligible to satisfy quorum. This preserves the configured preference order while
    preventing head-of-list exhaustion from masquerading as a multi-model outage.
    """
    allowed, skipped, attached = filter_planners_by_quota(
        planners, config=config, quota_snapshot=quota_snapshot
    )
    return allowed[:q_count], skipped, attached


def build_state(
    question: str,
    context: Optional[dict] = None,
    constraints: Optional[List[str]] = None,
    acceptance_criteria: Optional[List[str]] = None,
    implementation_target: Optional[dict] = None,
    non_goals: Optional[List[str]] = None,
    risk_level: str = "medium",
    budget: Optional[dict] = None,
    claims: Optional[List[Any]] = None,
    evidence: Optional[List[dict]] = None,
) -> dict:
    """Build the orchestrator-owned state.json facts/bounds for true multi-model discussion.

    This is deliberately not a candidate solution. Candidate plans are produced later by
    independent models from this shared state. `claims` and `evidence` are the optional
    truth-provenance contract: models may critique it or request more evidence, but they
    must not treat unsupported claims as tool-verified facts.
    """
    return {
        "schema": "multi_model_state_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "context": context or {},
        "constraints": constraints or [],
        "acceptance_criteria": acceptance_criteria or [],
        "non_goals": non_goals or [],
        "risk_level": risk_level,
        "budget": budget or {},
        "claims": claims or [],
        "evidence": evidence or [],
        "implementation_target": implementation_target or {
            "files": [],
            "verify_commands": [],
            "forbidden_changes": [],
        },
        "is_candidate_solution": False,
        "state_owner": "main_orchestrator",
    }


EVIDENCE_BUNDLE_SCHEMA_VERSION = 1
TRUTH_GATE_SCHEMA_VERSION = 1


def _normalize_claims(raw_claims: List[Any]) -> List[dict]:
    claims: List[dict] = []
    for i, raw in enumerate(raw_claims or [], start=1):
        if isinstance(raw, str):
            claim = {"id": f"C-{i:03d}", "text": raw, "severity": 3}
        elif isinstance(raw, dict):
            claim = dict(raw)
            claim.setdefault("id", f"C-{i:03d}")
            claim.setdefault("text", claim.get("claim") or claim.get("summary") or "")
            claim.setdefault("severity", 3)
        else:
            claim = {"id": f"C-{i:03d}", "text": str(raw), "severity": 3}
        claim["id"] = str(claim.get("id") or f"C-{i:03d}")
        claim["text"] = str(claim.get("text") or "").strip()
        try:
            claim["severity"] = int(claim.get("severity", 3) or 3)
        except (TypeError, ValueError):
            claim["severity"] = 3
        claims.append(claim)
    return claims


def _normalize_evidence(raw_evidence: List[dict]) -> List[dict]:
    evidence: List[dict] = []
    for i, raw in enumerate(raw_evidence or [], start=1):
        if not isinstance(raw, dict):
            raw = {"summary": str(raw)}
        item = dict(raw)
        item.setdefault("id", f"E-{i:03d}")
        item.setdefault("type", "note")
        item.setdefault("summary", item.get("content") or item.get("stdout") or "")
        item.setdefault("supports", item.get("claim_ids") or item.get("claims_supported") or item.get("supported_claim_ids") or [])
        item.setdefault("contradicts", [])
        if isinstance(item.get("supports"), str):
            item["supports"] = [item["supports"]]
        if isinstance(item.get("contradicts"), str):
            item["contradicts"] = [item["contradicts"]]
        item["id"] = str(item.get("id") or f"E-{i:03d}")
        item["supports"] = [str(x) for x in (item.get("supports") or [])]
        item["contradicts"] = [str(x) for x in (item.get("contradicts") or [])]
        # A failed command may still be evidence, but it must not support a claim.
        if item.get("type") == "command" and item.get("exit_code") not in (None, 0):
            item["supports"] = []
            item.setdefault("validity", "command_failed")
        evidence.append(item)
    return evidence


def _evidence_counts_as_verification(evidence_item: dict) -> bool:
    """Return whether an evidence item can verify a factual claim.

    Gate requirements, policies, and provenance-only records are useful audit
    context, but they are not proof that the required execution happened.
    """
    kind = str(evidence_item.get("kind") or "").strip().casefold()
    typ = str(evidence_item.get("type") or "").strip().casefold()
    non_verifying_kinds = {
        "gate",
        "gate_requirement",
        "requirement",
        "policy",
        "policy_only",
        "obligation",
        "acceptance_criterion",
        "provenance",
        "provenance_only",
        "audit_provenance",
    }
    if kind in non_verifying_kinds or typ in non_verifying_kinds:
        return False
    if evidence_item.get("validity") == "command_failed":
        return False
    return True


def build_evidence_bundle(state: dict) -> dict:
    """Build a grounded evidence bundle from orchestrator-collected claims/evidence.

    This separates multi-model agreement from factual verification. Models can only
    certify factual claims that have explicit supporting evidence IDs. Missing evidence
    remains visible as `unsupported` and can generate evidence_requests.
    """
    context = state.get("context", {}) if isinstance(state, dict) else {}
    raw_claims = state.get("claims") or (context.get("claims") if isinstance(context, dict) else []) or []
    raw_evidence = state.get("evidence") or (context.get("evidence") if isinstance(context, dict) else []) or []
    claims = _normalize_claims(raw_claims)
    evidence = _normalize_evidence(raw_evidence)
    has_unlinked_raw_evidence = bool(evidence) and not any((e.get("supports") or e.get("contradicts")) for e in evidence)

    grounding: Dict[str, dict] = {}
    for claim in claims:
        cid = claim["id"]
        supporting = [e["id"] for e in evidence if cid in (e.get("supports") or []) and _evidence_counts_as_verification(e)]
        non_verifying_supporting = [e["id"] for e in evidence if cid in (e.get("supports") or []) and not _evidence_counts_as_verification(e)]
        contradicting = [e["id"] for e in evidence if cid in (e.get("contradicts") or [])]
        if contradicting:
            truth_status = "contradicted_by_evidence"
        elif supporting:
            truth_status = "verified_by_evidence"
        elif non_verifying_supporting:
            truth_status = "unsupported"
        elif has_unlinked_raw_evidence:
            truth_status = "needs_link_review"
        else:
            truth_status = "unsupported"
        grounding[cid] = {
            "claim_id": cid,
            "claim_text": claim.get("text", ""),
            "severity": claim.get("severity", 3),
            "truth_status": truth_status,
            "supporting_evidence_ids": supporting,
            "non_verifying_supporting_evidence_ids": non_verifying_supporting,
            "contradicting_evidence_ids": contradicting,
            "candidate_evidence_ids": [e["id"] for e in evidence] if truth_status == "needs_link_review" else [],
        }

    verified_count = sum(1 for g in grounding.values() if g["truth_status"] == "verified_by_evidence")
    coverage = (verified_count / len(claims)) if claims else 1.0
    return {
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claims": claims,
        "evidence": evidence,
        "grounding": grounding,
        "evidence_coverage": coverage,
        "verified_claim_count": verified_count,
        "claim_count": len(claims),
    }


def evaluate_truth_gate(evidence_bundle: Optional[dict]) -> dict:
    """Fail-closed truth gate for multi-brain certification artifacts."""
    bundle = evidence_bundle or build_evidence_bundle({})
    grounding = bundle.get("grounding", {}) if isinstance(bundle, dict) else {}
    unsupported = [cid for cid, g in grounding.items() if g.get("truth_status") == "unsupported"]
    needs_link_review = [cid for cid, g in grounding.items() if g.get("truth_status") == "needs_link_review"]
    contradicted = [cid for cid, g in grounding.items() if g.get("truth_status") == "contradicted_by_evidence"]
    unsupported_high = [cid for cid, g in grounding.items() if g.get("truth_status") == "unsupported" and _safe_int(g.get("severity", 3), 3) >= 3]
    needs_link_review_high = [cid for cid, g in grounding.items() if g.get("truth_status") == "needs_link_review" and _safe_int(g.get("severity", 3), 3) >= 3]
    contradicted_high = [cid for cid, g in grounding.items() if g.get("truth_status") == "contradicted_by_evidence" and _safe_int(g.get("severity", 3), 3) >= 3]
    claim_count = _safe_int(bundle.get("claim_count", len(grounding)), len(grounding)) if isinstance(bundle, dict) else 0
    verified_count = _safe_int(bundle.get("verified_claim_count", 0), 0) if isinstance(bundle, dict) else 0

    if claim_count == 0:
        truth_status = "no_claims"
    elif contradicted:
        truth_status = "contradicted"
    elif needs_link_review:
        truth_status = "needs_link_review"
    elif unsupported and verified_count > 0:
        truth_status = "partially_grounded"
    elif unsupported:
        truth_status = "unsupported"
    else:
        truth_status = "grounded"

    reasons = []
    if unsupported:
        reasons.append(f"unsupported factual claims: {unsupported}")
    if needs_link_review:
        reasons.append(f"raw evidence present but claim/evidence links need review: {needs_link_review}")
    if contradicted:
        reasons.append(f"contradicted factual claims: {contradicted}")
    can_certify_truth = not unsupported and not contradicted and not needs_link_review
    return {
        "schema_version": TRUTH_GATE_SCHEMA_VERSION,
        "truth_status": truth_status,
        "can_certify_truth": can_certify_truth,
        "claim_count": claim_count,
        "verified_claim_count": verified_count,
        "evidence_coverage": bundle.get("evidence_coverage", 1.0) if isinstance(bundle, dict) else 1.0,
        "unsupported_claim_ids": unsupported,
        "unsupported_high_severity_claim_ids": unsupported_high,
        "needs_link_review_claim_ids": needs_link_review,
        "needs_link_review_high_severity_claim_ids": needs_link_review_high,
        "contradicted_claim_ids": contradicted,
        "contradicted_high_severity_claim_ids": contradicted_high,
        "reasons": reasons,
    }


def _coerce_evidence_request_items(raw: Any) -> List[Any]:
    """Normalize evidence_requests containers without silently dropping malformed scalars."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if isinstance(raw.get("evidence_requests"), list):
            return raw.get("evidence_requests") or []
        return [raw]
    return [raw]


def collect_evidence_requests(outputs: List[dict]) -> List[dict]:
    """Collect structured evidence requests from planner/discussion outputs.

    Peer models do not get to claim they used tools in the text-only multi-brain path.
    They can instead ask the main orchestrator for read-only evidence to acquire.
    """
    requests: List[dict] = []
    seen = set()
    for output in outputs or []:
        if not isinstance(output, dict):
            continue
        model = _plan_model(output, "unknown")
        raw_requests = []
        raw_requests.extend(_coerce_evidence_request_items(output.get("evidence_requests")))
        diagnosis = output.get("diagnosis") or {}
        if isinstance(diagnosis, dict):
            raw_requests.extend(_coerce_evidence_request_items(diagnosis.get("evidence_requests")))
        for i, raw in enumerate(raw_requests, start=1):
            if not isinstance(raw, dict):
                requests.append({
                    "id": f"ER-{len(requests) + 1:03d}",
                    "requested_by": model,
                    "claim_id": "",
                    "claim": "",
                    "tool_needed": "unknown",
                    "command": "",
                    "why": "",
                    "status": "malformed",
                    "safety": "rejected_malformed_request",
                    "malformed_request": True,
                    "malformed_reason": "evidence request must be an object",
                    "raw_type": type(raw).__name__,
                })
                continue
            command = str(raw.get("command") or raw.get("query") or "").strip()
            claim_id = str(raw.get("claim_id") or "").strip()
            claim = str(raw.get("claim") or "").strip()
            tool_needed = str(raw.get("tool_needed") or raw.get("tool") or "unknown").strip()
            why = str(raw.get("why") or raw.get("reason") or "").strip()
            key = (model, claim_id, claim, tool_needed, command, why)
            if key in seen:
                continue
            seen.add(key)
            requests.append({
                "id": f"ER-{len(requests) + 1:03d}",
                "requested_by": model,
                "claim_id": claim_id,
                "claim": claim,
                "tool_needed": tool_needed,
                "command": command,
                "why": why,
                "status": "requested",
                "safety": "read_only_or_orchestrator_approved",
            })
    return requests


_SECRET_REDACTION_PATTERNS = [
    # JSON/YAML/TOML/env-style key/value secrets. Match prefixed keys such as
    # aws_secret_access_key and serviceAccountToken, not only exact key names.
    re.compile(r"(?i)['\"]?[A-Za-z0-9_.-]*(api[_-]?key|access[_-]?key|secret|password|passwd|token|authorization|credential|private[_-]?key|service[_-]?account)[A-Za-z0-9_.-]*['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
    re.compile(r"(?i)[A-Za-z0-9_.-]*(api[_-]?key|access[_-]?key|secret|password|passwd|token|authorization|credential|bearer|private[_-]?key|service[_-]?account)[A-Za-z0-9_.-]*\s*[:=]\s*['\"]?[^\s'\",}]{6,}"),
    re.compile(r"(?is)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:~|/|\./|\.\./)[^\s'\"]*(?:\.env|auth\.json|\.npmrc|\.netrc|\.pypirc|\.aws/|aws/credentials|\.ssh/|id_rsa|id_ed25519|credentials?|secrets?|private[_-]?key|\.pem|key\.json|service[_-]?account|cookies?|keychain)[^\s'\"]*"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def redact_evidence_text(text: Any, limit: int = MAX_EVIDENCE_OUTPUT_CHARS) -> str:
    """Redact credential-shaped substrings before storing model-visible evidence."""
    value = str(text or "")
    for pat in _SECRET_REDACTION_PATTERNS:
        value = pat.sub("[REDACTED]", value)
    if len(value) > limit:
        value = value[: max(0, limit - 32)] + f"\n...[truncated:{len(value)}]"
    return value


def _command_has_forbidden_tokens(command: str) -> bool:
    forbidden = (";", "&&", "||", "|", "`", "$(`", "$(", ">", "<", "\n", "\r")
    return any(tok in command for tok in forbidden)


def _mentions_credential_path(command: str) -> bool:
    lowered = command.lower()
    credential_markers = (
        ".env", "auth.json", ".npmrc", ".netrc", ".pypirc", ".aws/", "aws/credentials",
        ".ssh/", "id_rsa", "id_ed25519", "known_hosts", "credentials", "credential",
        "secret", "secrets", "private_key", "private-key", ".pem", "key.json",
        "service_account", "service-account", "cookie", "cookies", "keychain",
    )
    return any(marker in lowered for marker in credential_markers)


def _safe_split_command(command: str) -> Tuple[Optional[List[str]], str]:
    command = str(command or "").strip()
    if not command:
        return None, "empty command"
    if _command_has_forbidden_tokens(command):
        return None, "shell metacharacters/pipelines are not allowed for evidence fulfillment"
    if _mentions_credential_path(command):
        return None, "credential-bearing paths are not allowed in evidence requests"
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return None, f"cannot parse command: {e}"
    if not parts:
        return None, "empty command"
    return parts, ""


def _trusted_git_executable() -> Optional[str]:
    git = shutil.which("git", path="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin")
    if not git:
        return None
    real = os.path.realpath(git)
    # Reject cwd/tmp-controlled binaries; keep deterministic system/homebrew git.
    if real.startswith(("/tmp/", "/private/tmp/", os.getcwd() + os.sep)):
        return None
    return real


def _is_allowed_git_evidence_command(parts: List[str]) -> bool:
    """Strict read-only git evidence allowlist.

    Keep this deliberately narrow. Avoid arbitrary `--*` forwarding, ext-diff,
    no-index, output files, blob selectors, or path forms that can disclose
    secret-bearing files. The model may ask for broader evidence, but the
    orchestrator should collect it manually instead of executing it here.
    """
    if not parts or parts[0] != "git" or len(parts) < 2:
        return False
    subcmd = parts[1]
    args = parts[2:]
    if subcmd == "status":
        return args in ([], ["--short"], ["--porcelain"], ["--branch"], ["--short", "--branch"])
    if subcmd == "diff":
        return args in (
            ["--stat"],
            ["--name-only"],
            ["--cached", "--check"],
            ["--check"],
        )
    if subcmd == "log":
        if args == ["--oneline"]:
            return True
        if len(args) == 2 and args[0] == "--oneline" and re.fullmatch(r"-\d{1,3}", args[1]):
            return True
        return False
    if subcmd == "show":
        if len(args) != 2 or args[0] != "--stat":
            return False
        ref = args[1]
        # No `rev:path` blob selectors and no branch names with path-like slashes.
        return bool(re.fullmatch(r"HEAD(?:~\d{1,3}|\^\d{0,2})?|[0-9a-fA-F]{7,40}", ref))
    return False


def _canonical_script_path(script_name: str) -> str:
    return os.path.realpath(os.path.join(HERMES_HOME, "scripts", script_name))


def _is_canonical_helper_script(parts: List[str], script_name: str) -> bool:
    if len(parts) < 2:
        return False
    interpreter = os.path.realpath(os.path.expanduser(parts[0]))
    if interpreter != os.path.realpath(sys.executable):
        return False
    requested = os.path.realpath(os.path.expanduser(parts[1]))
    return requested == _canonical_script_path(script_name)


def _flag_value(args: List[str], flag: str) -> Optional[str]:
    """Return the single-token value following a flag, if present."""
    if flag not in args:
        return None
    idx = args.index(flag)
    if idx + 1 >= len(args):
        return None
    return args[idx + 1]


def _is_safe_small_int(value: Optional[str], *, min_value: int = 0, max_value: int = 1000) -> bool:
    if value is None or not re.fullmatch(r"\d{1,4}", str(value)):
        return False
    parsed = int(str(value))
    return min_value <= parsed <= max_value


def _token_has_path_or_secret_risk(value: str) -> bool:
    token = str(value or "")
    if _mentions_credential_path(token):
        return True
    return any(part in token for part in ("/", "\\", "..", "~"))


def _validate_flag_shape(args: List[str], allowed_flags: set, flags_with_values: set, valueless_flags: set) -> bool:
    """Validate flag names and arity; reject unknown flags and dangling values."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("-"):
            if arg not in allowed_flags:
                return False
            if arg in flags_with_values:
                if i + 1 >= len(args) or args[i + 1].startswith("-"):
                    return False
                i += 2
                continue
            if arg not in valueless_flags:
                return False
        i += 1
    return True


def _is_allowed_brainctl_command(parts: List[str]) -> bool:
    # brainctl search/evidence can disclose private brain excerpts and may mutate
    # local indexes/WAL. Automatic model-requested evidence fulfillment therefore
    # does not execute brainctl at all; orchestrator-owned verification can run it
    # outside this gate when explicitly needed.
    return False


def _is_allowed_anti_drift_command(parts: List[str]) -> bool:
    # Automatic evidence fulfillment is read-only and model-requested. The
    # anti_drift helper accepts path-valued flags and historical write/report
    # flags such as --out, so it is not safe as a generic model-requested
    # allowlist target. Orchestrator-owned verification can run it outside this
    # evidence-fulfillment gate when explicitly needed.
    return False


def _implementation_verify_commands(state: dict) -> List[str]:
    if not isinstance(state, dict):
        return []
    target = state.get("implementation_target") if isinstance(state.get("implementation_target"), dict) else {}
    return [str(cmd).strip() for cmd in (target.get("verify_commands") or []) if str(cmd).strip()]


def _trusted_claim_command_allowlist(state: dict) -> Dict[str, List[str]]:
    """Return orchestrator-owned command→claim support policy.

    Model-supplied `claim_id` is only a candidate link. A fulfilled command can
    verify a claim only when the state itself contains an explicit trusted mapping:

      evidence_fulfillment_policy.claim_command_allowlist = {
        "C-001": ["python3 scripts/self-test.py"]
      }

    This prevents a reviewer from grounding arbitrary claims by attaching them to
    unrelated successful read-only commands such as `git status --short`.
    """
    if not isinstance(state, dict):
        return {}
    policy = state.get("evidence_fulfillment_policy") if isinstance(state.get("evidence_fulfillment_policy"), dict) else {}
    raw = policy.get("claim_command_allowlist") if isinstance(policy.get("claim_command_allowlist"), dict) else {}
    normalized: Dict[str, List[str]] = {}
    for claim_id, commands in raw.items():
        if isinstance(commands, str):
            commands = [commands]
        if not isinstance(commands, list):
            continue
        normalized[str(claim_id)] = [str(cmd).strip() for cmd in commands if str(cmd).strip()]
    return normalized


def _command_has_trusted_claim_policy(request: dict, state: dict, command: str) -> bool:
    claim_id = str((request or {}).get("claim_id") or "").strip()
    if not claim_id or not command:
        return False
    return command in _trusted_claim_command_allowlist(state).get(claim_id, [])


def _request_has_trusted_claim_support(request: dict, safety: dict, state: dict) -> bool:
    claim_id = str((request or {}).get("claim_id") or "").strip()
    command = str(safety.get("command") or (request or {}).get("command") or "").strip()
    if not claim_id or not command:
        return False
    return command in _trusted_claim_command_allowlist(state).get(claim_id, [])


def _evidence_subprocess_env() -> dict:
    """Minimal environment for fulfilled evidence subprocesses.

    Do not inherit provider tokens, API keys, shell secrets, or user credential
    variables. Commands that need secrets are not read-only evidence commands.
    """
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "HERMES_MULTI_BRAIN_OFFLINE": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }


def _redacted_command(command: str) -> str:
    return redact_evidence_text(command, limit=800)


def classify_evidence_request_safety(request: dict, state: Optional[dict] = None) -> dict:
    """Fail-closed allowlist for model-requested evidence execution.

    Reviewer models may request evidence, but only the orchestrator executes a
    narrow read-only subset. Anything malformed, shell-like, secret-bearing, or
    outside the allowlist is rejected before subprocess execution.
    """
    if not isinstance(request, dict):
        return {"allowed": False, "reason": "request must be an object", "command": "", "tool_needed": ""}
    if request.get("malformed_request") or str(request.get("status") or "") == "malformed":
        return {"allowed": False, "reason": str(request.get("malformed_reason") or "malformed evidence request"), "command": str(request.get("command") or ""), "tool_needed": str(request.get("tool_needed") or "")}
    command = str((request or {}).get("command") or "").strip()
    tool_needed = str((request or {}).get("tool_needed") or (request or {}).get("tool") or "").strip().lower()
    parts, reason = _safe_split_command(command)
    if parts is None:
        return {"allowed": False, "reason": reason, "command": command, "tool_needed": tool_needed}

    # Never approve model-requested evidence merely because it appears in
    # implementation_target.verify_commands. Those commands can be arbitrary
    # build/test scripts and are executed by the orchestrator elsewhere; the
    # evidence-fulfillment gate remains a narrower read-only allowlist. Trusted
    # claim policy only controls whether an already-approved command may support
    # a claim, not whether the command may execute.
    if _is_allowed_git_evidence_command(parts):
        git = _trusted_git_executable()
        if not git:
            return {"allowed": False, "reason": "trusted git executable not found", "command": command, "tool_needed": tool_needed, "argv": parts}
        return {"allowed": True, "reason": "read-only git command allowlist", "command": command, "tool_needed": tool_needed, "argv": [git] + parts[1:]}
    if _is_allowed_brainctl_command(parts):
        return {"allowed": True, "reason": "read-only brainctl allowlist", "command": command, "tool_needed": tool_needed, "argv": parts}
    if _is_allowed_anti_drift_command(parts):
        return {"allowed": True, "reason": "read-only anti_drift_guard allowlist", "command": command, "tool_needed": tool_needed, "argv": parts}
    return {"allowed": False, "reason": "command is outside evidence fulfillment allowlist", "command": command, "tool_needed": tool_needed, "argv": parts}


def _malformed_evidence_request(reason: str, raw: Any = None, *, requested_by: str = "external") -> dict:
    return {
        "id": "ER-MALFORMED-001",
        "requested_by": requested_by,
        "tool_needed": "unknown",
        "command": "",
        "why": "",
        "status": "malformed",
        "safety": "rejected_malformed_request",
        "malformed_request": True,
        "malformed_reason": reason,
        "raw_type": type(raw).__name__,
    }


def load_evidence_requests_from_file(path: str) -> List[dict]:
    data = _read_json_file(path, default=None)
    if data is None:
        return [_malformed_evidence_request("requests file is missing or invalid JSON", data)]
    if isinstance(data, list):
        return collect_evidence_requests([{"meta": {"planner_model": "external"}, "evidence_requests": data}])
    if isinstance(data, dict):
        # Top-level dict can be either a single request or a planner-style object.
        # If it declares evidence_requests, let the collector classify malformed
        # nested scalars. Otherwise wrap the dict as one external request.
        data.setdefault("meta", {"planner_model": "external"})
        if "evidence_requests" in data or "diagnosis" in data:
            return collect_evidence_requests([data])
        return collect_evidence_requests([{"meta": {"planner_model": "external"}, "evidence_requests": [data]}])
    return collect_evidence_requests([{"meta": {"planner_model": "external"}, "evidence_requests": data}])


def load_evidence_requests_from_tick(tick_dir: str) -> List[dict]:
    outputs: List[dict] = []
    tick_dir = os.path.expanduser(tick_dir)
    for rel in ("discussion_result.json", "merged_plan.json"):
        data = _read_json_file(os.path.join(tick_dir, rel), default=None)
        if isinstance(data, dict):
            outputs.append(data)
    plans_dir = os.path.join(tick_dir, "plans")
    if os.path.isdir(plans_dir):
        for name in sorted(os.listdir(plans_dir)):
            if not name.endswith(".json"):
                continue
            data = _read_json_file(os.path.join(plans_dir, name), default=None)
            if isinstance(data, dict):
                outputs.append(data)
    return collect_evidence_requests(outputs)


def fulfill_evidence_requests(
    requests: List[dict],
    state: Optional[dict] = None,
    cwd: str = HERMES_HOME,
    timeout: int = 30,
    max_requests: int = 20,
    dry_run: bool = False,
) -> dict:
    """Execute approved read-only evidence requests and return an auditable report."""
    state = state or {}
    report = {
        "schema_version": EVIDENCE_FULFILLMENT_SCHEMA_VERSION,
        "generated_at": _utc_now_iso(),
        "dry_run": bool(dry_run),
        "cwd": os.path.abspath(os.path.expanduser(cwd)),
        "requested_count": len(requests or []),
        "processed_count": 0,
        "approved_count": 0,
        "rejected_count": 0,
        "succeeded_count": 0,
        "failed_count": 0,
        "results": [],
        "evidence": [],
    }
    safe_cwd = os.path.abspath(os.path.expanduser(cwd))
    for req in (requests or [])[:max_requests]:
        report["processed_count"] += 1
        if not isinstance(req, dict):
            report["rejected_count"] += 1
            report["results"].append({
                "request_id": f"ER-{report['processed_count']:03d}",
                "claim_id": "",
                "requested_by": "unknown",
                "command": "",
                "command_sha256_16": "",
                "safety": {"allowed": False, "reason": "request must be an object"},
                "status": "rejected",
                "reason": "request must be an object",
            })
            continue
        safety = classify_evidence_request_safety(req, state=state)
        command = safety.get("command") or str(req.get("command") or "")
        redacted_command = _redacted_command(command)
        result = {
            "request_id": req.get("id") or f"ER-{report['processed_count']:03d}",
            "claim_id": str(req.get("claim_id") or ""),
            "requested_by": req.get("requested_by") or "unknown",
            "command": redacted_command,
            "command_sha256_16": hashlib.sha256(str(command).encode("utf-8")).hexdigest()[:16] if command else "",
            "safety": {k: v for k, v in safety.items() if k != "argv" and k != "command"},
            "status": "rejected",
        }
        if not safety.get("allowed"):
            report["rejected_count"] += 1
            result["reason"] = safety.get("reason")
            report["results"].append(result)
            continue
        report["approved_count"] += 1
        if dry_run:
            result["status"] = "approved_dry_run"
            report["results"].append(result)
            continue
        try:
            proc = subprocess.run(
                safety.get("argv") or [],
                cwd=safe_cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=_evidence_subprocess_env(),
            )
            stdout = redact_evidence_text(proc.stdout)
            stderr = redact_evidence_text(proc.stderr)
            raw_output_hash = hashlib.sha256(((proc.stdout or "") + "\n" + (proc.stderr or "")).encode("utf-8")).hexdigest()[:16]
            result.update({
                "status": "succeeded" if proc.returncode == 0 else "failed",
                "exit_code": proc.returncode,
                "stdout_excerpt": stdout,
                "stderr_excerpt": stderr,
                "output_sha256_16": raw_output_hash,
                "output_hash_basis": "raw_stdout_stderr_before_redaction",
            })
        except subprocess.TimeoutExpired as e:
            result.update({
                "status": "timeout",
                "exit_code": None,
                "stdout_excerpt": redact_evidence_text(e.stdout or ""),
                "stderr_excerpt": redact_evidence_text(e.stderr or ""),
                "reason": f"timeout after {timeout}s",
            })
        except OSError as e:
            result.update({
                "status": "failed",
                "exit_code": None,
                "stdout_excerpt": "",
                "stderr_excerpt": redact_evidence_text(str(e)),
                "reason": "subprocess execution failed",
            })
        if result["status"] == "succeeded":
            report["succeeded_count"] += 1
        else:
            report["failed_count"] += 1
        evidence_id = f"E-fulfill-{report['processed_count']:03d}"
        trusted_support = result.get("status") == "succeeded" and _request_has_trusted_claim_support(req, safety, state)
        candidate_claim_ids = [result["claim_id"]] if result.get("claim_id") and not trusted_support else []
        evidence = {
            "id": evidence_id,
            "type": "tool_result",
            "kind": "orchestrator_fulfilled_evidence",
            "summary": f"Evidence request {result['request_id']} executed: {result['command']} -> {result['status']}",
            "supports": [result["claim_id"]] if trusted_support else [],
            "candidate_claim_ids": candidate_claim_ids,
            "claim_linkage": "trusted_state_policy" if trusted_support else "candidate_needs_orchestrator_link_review",
            "contradicts": [],
            "evidence_request_id": result["request_id"],
            "requested_by": result.get("requested_by"),
            "command": result["command"],
            "command_sha256_16": result.get("command_sha256_16"),
            "exit_code": result.get("exit_code"),
            "stdout_excerpt": result.get("stdout_excerpt", ""),
            "stderr_excerpt": result.get("stderr_excerpt", ""),
            "output_sha256_16": result.get("output_sha256_16"),
            "output_hash_basis": result.get("output_hash_basis"),
            "executed_at": _utc_now_iso(),
            "redaction": "credential patterns redacted; output truncated",
        }
        if result["status"] != "succeeded":
            evidence["validity"] = "command_failed"
        report["evidence"].append(evidence)
        report["results"].append(result)
    if len(requests or []) > max_requests:
        report["truncated_request_count"] = len(requests or []) - max_requests
    return report


def update_state_with_fulfilled_evidence(state: dict, fulfillment_report: dict) -> dict:
    updated = dict(state or {})
    evidence = list(updated.get("evidence") or [])
    evidence.extend(fulfillment_report.get("evidence") or [])
    updated["evidence"] = evidence
    updated.setdefault("evidence_fulfillment_reports", [])
    summary = {
        "schema_version": fulfillment_report.get("schema_version"),
        "generated_at": fulfillment_report.get("generated_at"),
        "requested_count": fulfillment_report.get("requested_count"),
        "processed_count": fulfillment_report.get("processed_count"),
        "approved_count": fulfillment_report.get("approved_count"),
        "rejected_count": fulfillment_report.get("rejected_count"),
        "succeeded_count": fulfillment_report.get("succeeded_count"),
        "failed_count": fulfillment_report.get("failed_count"),
        "dry_run": fulfillment_report.get("dry_run"),
        "results": fulfillment_report.get("results", []),
    }
    if fulfillment_report.get("truncated_request_count"):
        summary["truncated_request_count"] = fulfillment_report.get("truncated_request_count")
    updated["evidence_fulfillment_reports"].append(summary)
    bundle = build_evidence_bundle(updated)
    updated["evidence_bundle"] = bundle
    updated["truth_gate"] = evaluate_truth_gate(bundle)
    return updated


def _plan_model(plan: dict, fallback: str = "unknown") -> str:
    meta = plan.get("meta", {}) if isinstance(plan, dict) else {}
    return meta.get("planner_model") or meta.get("model") or fallback


def _is_conditional_advisory_patch(patch: dict) -> bool:
    """Return true for non-authoritative, conditional verifier suggestions.

    Planner output sometimes uses an `add_verifier` patch to say "if direct
    inspection shows a gap, add a test". That is an evidence request/advisory,
    not a concrete implementation delta, and must not manufacture a severity>=3
    blocker when the orchestrator evidence already contains the verifier result.
    Concrete unconditional verifier additions still count as real patches.
    """
    if not isinstance(patch, dict):
        return False
    op = str(patch.get("op", "")).strip().lower()
    if op != "add_verifier":
        return False
    rationale = str(patch.get("rationale", "")).strip().lower()
    conditional_markers = (
        "only if",
        "conditional",
        "if absent",
        "if missing",
        "if fresh",
        "if direct inspection",
        "if verification",
        "if tests",
        "if the named test",
        "if the verifier",
        "verify whether",
    )
    return any(marker in rationale for marker in conditional_markers)


def _plan_declares_no_action(plan: dict) -> bool:
    """Return true when a planner explicitly frames its output as no-action certification."""
    if not isinstance(plan, dict):
        return False
    diagnosis = plan.get("diagnosis") if isinstance(plan.get("diagnosis"), dict) else {}
    root = str(diagnosis.get("root_cause_class") or "").strip().lower()
    summary = str(diagnosis.get("summary") or "").strip().lower()
    if root in {"no_action", "noop", "certification_only", "already_satisfied"}:
        return True
    no_action_markers = (
        "all acceptance criteria satisfied",
        "no severity>=3 blockers remain",
        "no blockers remain",
        "no change needed",
        "operating as designed",
        "current gates already pass",
    )
    return any(marker in summary for marker in no_action_markers)


def _is_no_action_advisory_patch(patch: dict, plan: dict) -> bool:
    """Classify low-risk follow-up ideas under a no-action plan as advisory.

    Some planners certify the current system as complete but still emit low-risk
    tune/document/observability follow-ups. Treating those as concrete blockers
    creates a false noop-vs-change contradiction and prevents certification even
    though the same plan says the acceptance criteria are already satisfied.
    """
    if not isinstance(patch, dict) or not _plan_declares_no_action(plan):
        return False
    op = str(patch.get("op", "")).strip().lower()
    if op not in {"tune_threshold", "document", "update_docs", "add_observability", "add_metric"}:
        return False
    risk = str(patch.get("risk", "")).strip().lower()
    blast = str(patch.get("blast_radius", "")).strip().lower()
    if risk and risk not in {"low", "p2", "p3", "minor"}:
        return False
    rationale = str(patch.get("rationale", "")).strip().lower()
    advisory_markers = (
        "non-blocking",
        "warning",
        "observability",
        "document",
        "maintainer",
        "tech debt",
        "current gates already pass",
        "without breaking current flow",
    )
    safe_scope = (not blast) or blast in {"single_tier", "single-file", "single_file", "none"}
    return safe_scope and any(marker in rationale for marker in advisory_markers)


def _planner_patch_summary(plans: List[dict]) -> dict:
    """Summarize planner patch intent after advisory/noop normalization.

    Consensus merging may legitimately produce `patches=[]` for certification-only
    ticks where every planner either signs off with noop or emits conditional
    evidence-request/advisory verifier ideas. Preserve that intent explicitly so
    discussion reviewers do not mistake an empty merged patch list for a dropped
    implementation patch.
    """
    summary = {
        "schema_version": 1,
        "planner_count": 0,
        "total_patch_count": 0,
        "noop_patch_count": 0,
        "conditional_advisory_patch_count": 0,
        "concrete_patch_count": 0,
        "malformed_plan_count": 0,
        "plans_missing_patches_count": 0,
        "plans_non_list_patches_count": 0,
        "non_dict_patch_count": 0,
        "models_with_concrete_patches": [],
        "certification_intent": "unknown",
    }
    concrete_models: List[str] = []
    for idx, plan in enumerate(plans or []):
        if not isinstance(plan, dict):
            summary["malformed_plan_count"] += 1
            continue
        summary["planner_count"] += 1
        model = _plan_model(plan, f"model_{idx}")
        model_has_concrete = False
        if "patches" not in plan:
            summary["plans_missing_patches_count"] += 1
            continue
        patches = plan.get("patches")
        if not isinstance(patches, list):
            summary["plans_non_list_patches_count"] += 1
            continue
        for patch_obj in patches:
            if not isinstance(patch_obj, dict):
                summary["non_dict_patch_count"] += 1
                continue
            summary["total_patch_count"] += 1
            op = str(patch_obj.get("op", "")).strip().lower()
            if op == "noop":
                summary["noop_patch_count"] += 1
            elif _is_conditional_advisory_patch(patch_obj) or _is_no_action_advisory_patch(patch_obj, plan):
                summary["conditional_advisory_patch_count"] += 1
            else:
                summary["concrete_patch_count"] += 1
                model_has_concrete = True
        if model_has_concrete:
            concrete_models.append(model)
    summary["models_with_concrete_patches"] = sorted(set(concrete_models))
    malformed_count = (
        summary["malformed_plan_count"]
        + summary["plans_missing_patches_count"]
        + summary["plans_non_list_patches_count"]
        + summary["non_dict_patch_count"]
    )
    if malformed_count:
        summary["certification_intent"] = "malformed_patch_data"
    elif summary["concrete_patch_count"] == 0 and summary["planner_count"] > 0:
        summary["certification_intent"] = "no_action_certification"
    elif summary["concrete_patch_count"] > 0:
        summary["certification_intent"] = "implementation_required"
    else:
        summary["certification_intent"] = "no_patches_reported"
    return summary


def _patch_signature(patch: dict) -> str:
    """Stable signature for comparing plan patches across models."""
    if patch.get("id"):
        return str(patch.get("id"))
    body = "|".join([
        _normalize_target_file(patch.get("target_file") or patch.get("file") or ""),
        str(patch.get("op", "")),
        str(patch.get("rationale", "")),
    ])
    return hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]


def build_issue_ledger(plans: List[dict]) -> List[dict]:
    """Build explicit unresolved issues from disagreement between model plans.

    The first version focuses on concrete implementation disagreements: different
    patch signatures/ops aimed at the same target file, and missing patches that only
    one model proposed. This gives Phase 3 a bounded issue ledger to debate.
    """
    by_target: Dict[str, List[Tuple[str, dict, str]]] = {}
    noop_only_models: List[str] = []
    all_models = [_plan_model(p, f"model_{i}") for i, p in enumerate(plans)]
    for i, plan in enumerate(plans):
        model = _plan_model(plan, f"model_{i}")
        patches = plan.get("patches", []) if isinstance(plan, dict) else []
        if not isinstance(patches, list):
            patches = []
        non_noop_seen = False
        noop_seen = False
        for patch in patches:
            if not isinstance(patch, dict):
                continue
            op = str(patch.get("op", "")).lower()
            # A noop patch is an explicit certification/no-change vote, not a proposed
            # implementation delta. Heterogeneous noop ids alone should not create false
            # blockers, but noop-vs-real-change is still a real disagreement below.
            if op == "noop" or _is_conditional_advisory_patch(patch) or _is_no_action_advisory_patch(patch, plan):
                noop_seen = True
                continue
            non_noop_seen = True
            target = _normalize_target_file(patch.get("target_file") or patch.get("file") or "<unknown>")
            by_target.setdefault(target, []).append((model, patch, _patch_signature(patch)))
        if noop_seen and not non_noop_seen:
            noop_only_models.append(model)

    issues = []
    next_id = 1
    noop_only_set = set(noop_only_models)
    for target, entries in sorted(by_target.items()):
        sigs = {sig for _, _, sig in entries}
        models_present = {model for model, _, _ in entries}
        missing_models = set(all_models) - models_present
        ops = {str(patch.get("op", "")) for _, patch, _ in entries}
        single_patch_missing_non_noop_model = len(entries) == 1 and bool(missing_models - noop_only_set)
        if len(sigs) > 1 or single_patch_missing_non_noop_model:
            severity = 4 if len(ops) > 1 else 3
            issues.append({
                "id": f"I-{next_id:03d}",
                "status": "unresolved",
                "severity": severity,
                "target_file": target,
                "models": sorted(models_present),
                "missing_models": sorted(set(all_models) - models_present),
                "claim": f"Models disagree on patches for {target}",
                "evidence": [
                    {"model": model, "patch_id": sig, "op": patch.get("op"), "rationale": patch.get("rationale", "")}
                    for model, patch, sig in entries
                ],
                "resolution": "",
            })
            next_id += 1

    # Conditional verifier/advisory ideas are skipped before `by_target`; any
    # remaining non-noop entry is a concrete implementation delta. Even an N-1
    # noop majority must not hide a concrete minority patch, because that would
    # turn model agreement into evidence and mask a real implementation blocker.
    if by_target and noop_only_models:
        issues.append({
            "id": f"I-{next_id:03d}",
            "status": "unresolved",
            "severity": 3,
            "target_file": "<mixed-noop-vs-change>",
            "models": sorted(set(all_models) - set(noop_only_models)),
            "missing_models": sorted(noop_only_models),
            "claim": "Some models voted noop/no-change while others proposed implementation patches",
            "evidence": [
                {"model": model, "patch_id": "noop", "op": "noop", "rationale": "noop/no-change vote"}
                for model in sorted(noop_only_models)
            ],
            "resolution": "",
        })

    return issues


FANOUT_CERTIFICATION_SCHEMA_VERSION = 1
FANOUT_CERTIFICATION_REQUIRED_FIELDS = (
    "schema_version",
    "status",
    "certified",
    "multi_model_certified",
    "certification_scope",
    "below_min_quorum",
    "success_count",
    "fail_count",
    "planner_count",
    "min_quorum",
    "reason",
)
FANOUT_CERTIFICATION_STATUSES = {
    "all_failed",
    "degraded_not_certified",
    "single_model_quorum_met",
    "fanout_quorum_met",
}


def fanout_certification_status(success_count: int, planner_count: int, min_quorum: int, fail_count: int = 0) -> dict:
    """Return auditable certification status for planner fan-out quorum.

    Multi-model outputs below min_quorum may still be useful as degraded planning
    signals, but they must not be represented as certified multi-model results.
    T0/single-planner fan-out can satisfy its own quick-plan threshold while still
    being explicitly marked as non-multi-model certification.
    """
    success_count = max(0, _safe_int(success_count, 0))
    planner_count = max(0, _safe_int(planner_count, 0))
    min_quorum = max(1, _safe_int(min_quorum, 1))
    fail_count = max(0, _safe_int(fail_count, 0))

    impossible_count_reasons: List[str] = []
    if success_count > planner_count:
        impossible_count_reasons.append("success_count exceeds planner_count")
    if fail_count > planner_count:
        impossible_count_reasons.append("fail_count exceeds planner_count")
    if success_count + fail_count > planner_count:
        impossible_count_reasons.append("success_count + fail_count exceeds planner_count")

    below_min = success_count < min_quorum
    all_failed = planner_count > 0 and success_count == 0
    single_planner = planner_count == 1

    if impossible_count_reasons:
        status = "degraded_not_certified"
        certified = False
        reason = "inconsistent fan-out counts: " + "; ".join(impossible_count_reasons)
    elif all_failed:
        status = "all_failed"
        certified = False
        reason = "all planners failed"
    elif below_min:
        status = "degraded_not_certified"
        certified = False
        reason = f"planner fan-out below min_quorum: {success_count}/{min_quorum}"
    elif single_planner:
        status = "single_model_quorum_met"
        certified = True
        reason = "single planner quorum met; not multi-model certified"
    else:
        status = "fanout_quorum_met"
        certified = True
        reason = f"planner fan-out met min_quorum: {success_count}/{min_quorum}"

    multi_model_certified = bool(certified and success_count >= 2 and planner_count >= 2 and not impossible_count_reasons)
    certification_scope = "multi_model" if multi_model_certified else "single_model"

    return {
        "schema_version": FANOUT_CERTIFICATION_SCHEMA_VERSION,
        "status": status,
        "certified": certified,
        "multi_model_certified": multi_model_certified,
        "certification_scope": certification_scope,
        "below_min_quorum": below_min,
        "success_count": success_count,
        "fail_count": fail_count,
        "planner_count": planner_count,
        "min_quorum": min_quorum,
        "reason": reason,
    }


def validate_fanout_certification_status(status: dict) -> Tuple[bool, List[str]]:
    """Validate fanout_certification before writing merged/discussion artifacts.

    This intentionally uses stdlib-only semantic checks instead of requiring the
    external jsonschema package inside operational scripts.
    """
    errors: List[str] = []
    if not isinstance(status, dict):
        return False, ["fanout_certification must be an object"]
    for field in FANOUT_CERTIFICATION_REQUIRED_FIELDS:
        if field not in status:
            errors.append(f"missing field: {field}")
    if errors:
        return False, errors

    if status.get("schema_version") != FANOUT_CERTIFICATION_SCHEMA_VERSION:
        errors.append(f"schema_version must be {FANOUT_CERTIFICATION_SCHEMA_VERSION}")
    if status.get("status") not in FANOUT_CERTIFICATION_STATUSES:
        errors.append(f"invalid status: {status.get('status')}")
    for field in ("certified", "multi_model_certified", "below_min_quorum"):
        if not isinstance(status.get(field), bool):
            errors.append(f"{field} must be boolean")
    for field in ("success_count", "fail_count", "planner_count", "min_quorum"):
        value = status.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append(f"{field} must be non-negative integer")
    valid_count_fields = all(isinstance(status.get(field), int) and not isinstance(status.get(field), bool) for field in ("success_count", "fail_count", "planner_count", "min_quorum"))
    if valid_count_fields and status.get("min_quorum", 0) < 1:
        errors.append("min_quorum must be >= 1")
    success_count = status.get("success_count", 0)
    fail_count = status.get("fail_count", 0)
    planner_count = status.get("planner_count", 0)
    min_quorum = status.get("min_quorum", 0)
    if valid_count_fields:
        if success_count > planner_count:
            errors.append("success_count cannot exceed planner_count")
        if fail_count > planner_count:
            errors.append("fail_count cannot exceed planner_count")
        if success_count + fail_count > planner_count:
            errors.append("success_count + fail_count cannot exceed planner_count")
        if status.get("certified") and planner_count < 1:
            errors.append("certified fanout requires planner_count >= 1")
        if status.get("certified") and success_count < min_quorum:
            errors.append("certified fanout requires success_count >= min_quorum")
    if status.get("certification_scope") not in {"single_model", "multi_model"}:
        errors.append("certification_scope must be single_model or multi_model")
    if status.get("multi_model_certified") and status.get("certification_scope") != "multi_model":
        errors.append("multi_model_certified requires certification_scope=multi_model")
    if status.get("multi_model_certified") and status.get("certified") is not True:
        errors.append("multi_model_certified requires certified=true")
    if valid_count_fields:
        if status.get("multi_model_certified") and success_count < 2:
            errors.append("multi_model_certified requires success_count >= 2")
        if status.get("multi_model_certified") and planner_count < 2:
            errors.append("multi_model_certified requires planner_count >= 2")
    if status.get("status") == "degraded_not_certified":
        if status.get("certified"):
            errors.append("degraded_not_certified cannot be certified")
        if status.get("multi_model_certified"):
            errors.append("degraded_not_certified cannot be multi_model_certified")
    if status.get("status") == "all_failed":
        if status.get("success_count") != 0:
            errors.append("all_failed requires success_count=0")
        if status.get("certified") or status.get("multi_model_certified"):
            errors.append("all_failed cannot be certified")
    if status.get("status") == "single_model_quorum_met":
        if status.get("multi_model_certified"):
            errors.append("single_model_quorum_met cannot be multi_model_certified")
        if valid_count_fields and planner_count != 1:
            errors.append("single_model_quorum_met requires planner_count=1")
    if status.get("status") == "fanout_quorum_met":
        if status.get("certified") is not True:
            errors.append("fanout_quorum_met requires certified=true")
        if valid_count_fields and success_count < min_quorum:
            errors.append("fanout_quorum_met requires success_count >= min_quorum")
    if not str(status.get("reason", "")).strip():
        errors.append("reason must be non-empty")
    return not errors, errors


def quota_observability_summary(quota_snapshot: dict) -> dict:
    """Summarize quota confidence without treating unknown/unobservable as healthy.

    Exhausted quotas are gated elsewhere. This summary is for artifact visibility:
    exact/estimated are higher confidence; unknown/unobservable require explicit
    degraded-confidence handling by humans or cron wrappers.
    """
    summary = {
        "schema_version": 1,
        "exact_count": 0,
        "estimated_count": 0,
        "unknown_count": 0,
        "unobservable_count": 0,
        "exhausted_count": 0,
        "has_low_confidence_quota": False,
        "low_confidence_models": [],
    }
    for snap in (quota_snapshot or {}).values():
        if not isinstance(snap, dict):
            continue
        model = snap.get("model") or snap.get("name") or "unknown"
        status = str(snap.get("status") or "unknown").lower()
        observability = str(snap.get("observability") or snap.get("quota_type") or status or "unknown").lower()
        if status == "exhausted":
            summary["exhausted_count"] += 1
        if observability == "exact":
            summary["exact_count"] += 1
        elif observability == "estimated":
            summary["estimated_count"] += 1
        elif observability == "unobservable" or status == "unobservable":
            summary["unobservable_count"] += 1
            summary["low_confidence_models"].append(model)
        else:
            summary["unknown_count"] += 1
            summary["low_confidence_models"].append(model)
    summary["low_confidence_models"] = sorted(set(summary["low_confidence_models"]))
    summary["has_low_confidence_quota"] = bool(summary["low_confidence_models"])
    return summary


def _append_analysis_check(report: dict, category: str, name: str, ok: bool, detail: Any = None, severity: str = "error") -> None:
    """Append one deterministic multi-model analysis self-check result."""
    entry = {"category": category, "name": name, "ok": bool(ok), "severity": severity}
    if detail is not None:
        entry["detail"] = detail
    report.setdefault("checks", []).append(entry)
    if ok:
        report["summary"]["passed"] += 1
    elif severity == "warning":
        report["summary"]["warnings"] += 1
    else:
        report["summary"]["failed"] += 1


def run_analysis_selfcheck(quorum: Optional[dict] = None, config: Optional[dict] = None, include_temp_audit: bool = True) -> dict:
    """Deterministic self-check for multi-model analysis/certification semantics.

    This is intentionally local and model-free. It validates the analysis layer's
    invariants (quorum config, provider diversity, fanout certification, truth gate,
    discussion ratification, and RMCS audit) before any result can be called a
    P10-grade multi-model certification.
    """
    quorum = quorum if quorum is not None else load_quorum()
    config = config if config is not None else load_config()
    report = {
        "schema_version": "multi_model_analysis_selfcheck_v1",
        "generated_at": _utc_now_iso(),
        "status": "FAIL",
        "summary": {"passed": 0, "failed": 0, "warnings": 0},
        "checks": [],
        "tiers": {},
        "fanout_matrix": {},
        "truth_gate_matrix": {},
    }

    mb = quorum.get("multi_brain", {}) if isinstance(quorum, dict) else {}
    tiers = quorum.get("tiers", {}) if isinstance(quorum, dict) else {}
    _append_analysis_check(report, "config", "quorum_is_object", isinstance(quorum, dict), type(quorum).__name__)
    _append_analysis_check(report, "config", "multi_brain_present", isinstance(mb, dict) and bool(mb), mb)
    _append_analysis_check(report, "config", "multi_brain_enabled", mb.get("enabled") is True, mb.get("enabled"))
    _append_analysis_check(report, "config", "actual_mode_not_shadow", mb.get("shadow_mode") is False, mb.get("shadow_mode"))
    _append_analysis_check(report, "config", "default_arbiter_configured", bool(str(mb.get("default_arbiter") or "").strip()), mb.get("default_arbiter"))

    all_models: List[str] = []
    for tier_name in ("T0", "T1", "T2", "T3"):
        tier_cfg = tiers.get(tier_name, {}) if isinstance(tiers, dict) else {}
        planners = list(tier_cfg.get("planners") or []) if isinstance(tier_cfg.get("planners") or [], list) else []
        quorum_count = _safe_int(tier_cfg.get("quorum"), 0)
        min_quorum = _safe_int(tier_cfg.get("min_quorum"), 0)
        providers = {model: model_provider(config, model) for model in planners}
        unknown_providers = sorted([model for model, provider in providers.items() if not provider])
        provider_values = [provider for provider in providers.values() if provider]
        duplicate_providers = sorted({provider for provider in provider_values if provider_values.count(provider) > 1})
        diversity = str(tier_cfg.get("diversity") or "none")
        report["tiers"][tier_name] = {
            "planners": planners,
            "quorum": quorum_count,
            "min_quorum": min_quorum,
            "diversity": diversity,
            "providers": providers,
            "unknown_providers": unknown_providers,
            "duplicate_providers": duplicate_providers,
        }
        all_models.extend(planners)
        _append_analysis_check(report, "quorum", f"{tier_name}_planners_nonempty", bool(planners), planners)
        _append_analysis_check(report, "quorum", f"{tier_name}_quorum_within_planners", 1 <= quorum_count <= len(planners), {"quorum": quorum_count, "planner_count": len(planners)})
        _append_analysis_check(report, "quorum", f"{tier_name}_min_quorum_valid", 1 <= min_quorum <= quorum_count, {"min_quorum": min_quorum, "quorum": quorum_count})
        _append_analysis_check(report, "provider", f"{tier_name}_providers_resolved", not unknown_providers, {"unknown": unknown_providers, "providers": providers})
        if diversity == "provider" and len(planners) > 1:
            _append_analysis_check(report, "provider", f"{tier_name}_provider_diversity", not duplicate_providers and not unknown_providers, {"duplicates": duplicate_providers, "providers": providers})
        if tier_name in {"T1", "T2", "T3"} and len(planners) >= 2:
            _append_analysis_check(report, "quorum", f"{tier_name}_not_solo_certifiable", min_quorum >= 2, {"min_quorum": min_quorum})

    unique_models = sorted(set(all_models))
    _append_analysis_check(report, "config", "model_pool_has_diversity", len(unique_models) >= 3, unique_models)

    fanout_cases = {
        "all_failed": fanout_certification_status(0, 3, 2, 3),
        "below_min": fanout_certification_status(1, 3, 2, 2),
        "single_model": fanout_certification_status(1, 1, 1, 0),
        "multi_model": fanout_certification_status(3, 4, 2, 1),
        "success_exceeds_planners": fanout_certification_status(3, 2, 2, 0),
        "success_with_zero_planners": fanout_certification_status(2, 0, 1, 0),
        "failures_exceed_planners": fanout_certification_status(1, 2, 1, 2),
        "bad_numeric_inputs": fanout_certification_status("bad", "bad", "bad", "bad"),
    }
    report["fanout_matrix"] = fanout_cases
    impossible_fanout_cases = {"success_exceeds_planners", "success_with_zero_planners", "failures_exceed_planners"}
    for case_name, status in fanout_cases.items():
        ok, errors = validate_fanout_certification_status(status)
        if case_name in impossible_fanout_cases:
            _append_analysis_check(report, "fanout", f"{case_name}_validator_rejects_inconsistent_counts", not ok and bool(errors), errors or status)
        else:
            _append_analysis_check(report, "fanout", f"{case_name}_schema_valid", ok, errors or status)
    _append_analysis_check(report, "fanout", "below_min_not_certified", fanout_cases["below_min"].get("certified") is False and fanout_cases["below_min"].get("status") == "degraded_not_certified", fanout_cases["below_min"])
    _append_analysis_check(report, "fanout", "single_model_not_multi_model_certified", fanout_cases["single_model"].get("certification_scope") == "single_model" and fanout_cases["single_model"].get("multi_model_certified") is False, fanout_cases["single_model"])
    _append_analysis_check(report, "fanout", "multi_model_certified_requires_two_successes", fanout_cases["multi_model"].get("multi_model_certified") is True and fanout_cases["multi_model"].get("success_count", 0) >= 2, fanout_cases["multi_model"])
    _append_analysis_check(report, "fanout", "impossible_count_relationships_fail_closed", all(
        fanout_cases[name].get("certified") is False and fanout_cases[name].get("multi_model_certified") is False and fanout_cases[name].get("status") == "degraded_not_certified"
        for name in ("success_exceeds_planners", "success_with_zero_planners", "failures_exceed_planners")
    ), {name: fanout_cases[name] for name in ("success_exceeds_planners", "success_with_zero_planners", "failures_exceed_planners")})

    supported_bundle = build_evidence_bundle({
        "claims": [{"id": "C-OK", "text": "deterministic tests passed", "severity": 4}],
        "evidence": [{"id": "E-OK", "type": "command", "summary": "test output PASS", "supports": ["C-OK"], "exit_code": 0}],
    })
    unsupported_bundle = build_evidence_bundle({"claims": [{"id": "C-MISSING", "text": "unverified claim", "severity": 4}], "evidence": []})
    needs_link_bundle = build_evidence_bundle({
        "claims": [{"id": "C-LINK", "text": "raw evidence exists", "severity": 4}],
        "evidence": [{"id": "E-RAW", "type": "command", "summary": "raw output without explicit supports", "exit_code": 0}],
    })
    truth_cases = {
        "supported": evaluate_truth_gate(supported_bundle),
        "unsupported": evaluate_truth_gate(unsupported_bundle),
        "needs_link_review": evaluate_truth_gate(needs_link_bundle),
    }
    report["truth_gate_matrix"] = truth_cases
    _append_analysis_check(report, "truth_gate", "supported_claim_certifies", truth_cases["supported"].get("can_certify_truth") is True and truth_cases["supported"].get("truth_status") == "grounded", truth_cases["supported"])
    _append_analysis_check(report, "truth_gate", "unsupported_high_severity_fails_closed", truth_cases["unsupported"].get("can_certify_truth") is False and "C-MISSING" in truth_cases["unsupported"].get("unsupported_high_severity_claim_ids", []), truth_cases["unsupported"])
    _append_analysis_check(report, "truth_gate", "raw_unlinked_evidence_needs_link_review", truth_cases["needs_link_review"].get("can_certify_truth") is False and truth_cases["needs_link_review"].get("truth_status") == "needs_link_review", truth_cases["needs_link_review"])

    fulfill_state = build_state(
        question="selfcheck evidence fulfillment",
        claims=[{"id": "C-EXEC", "text": "approved verifier command ran", "severity": 4}],
        evidence=[],
        implementation_target={"files": [], "verify_commands": ["git status --short"], "forbidden_changes": []},
    )
    fulfill_state["evidence_fulfillment_policy"] = {
        "claim_command_allowlist": {"C-EXEC": [fulfill_state["implementation_target"]["verify_commands"][0]]}
    }
    fulfill_requests = [{
        "id": "ER-EXEC",
        "requested_by": "selfcheck",
        "claim_id": "C-EXEC",
        "tool_needed": "terminal",
        "command": fulfill_state["implementation_target"]["verify_commands"][0],
        "why": "prove approved verifier execution can ground a claim",
    }]
    unsafe_request = {"id": "ER-BAD", "claim_id": "C-EXEC", "tool_needed": "terminal", "command": "cat ~/.hermes/.env", "why": "should be rejected"}
    bare_diff_request = {"id": "ER-DIFF", "claim_id": "C-EXEC", "tool_needed": "terminal", "command": "git diff", "why": "full diff should be rejected"}
    anti_drift_request = {"id": "ER-DRIFT", "claim_id": "C-EXEC", "tool_needed": "terminal", "command": f"{sys.executable} {os.path.join(HERMES_HOME, 'scripts', 'anti_drift_guard.py')} check-anchors --json --out /tmp/drift.json", "why": "write flag should be rejected"}
    malformed_request = {"id": "ER-MAL", "status": "malformed", "malformed_request": True, "malformed_reason": "evidence request must be an object"}
    safe_check = classify_evidence_request_safety(fulfill_requests[0], state=fulfill_state)
    unsafe_check = classify_evidence_request_safety(unsafe_request, state=fulfill_state)
    bare_diff_check = classify_evidence_request_safety(bare_diff_request, state=fulfill_state)
    anti_drift_check = classify_evidence_request_safety(anti_drift_request, state=fulfill_state)
    malformed_check = classify_evidence_request_safety(malformed_request, state=fulfill_state)
    json_redacted = redact_evidence_text('{"api_key":"abcdef1234567890","safe":"visible"}')
    fulfill_report = fulfill_evidence_requests(fulfill_requests, state=fulfill_state, cwd=HERMES_HOME, timeout=10, max_requests=1, dry_run=False)
    updated_state = update_state_with_fulfilled_evidence(fulfill_state, fulfill_report)
    report["evidence_fulfillment_matrix"] = {
        "safe_allowed": {k: v for k, v in safe_check.items() if k != "argv"},
        "unsafe_allowed": unsafe_check,
        "bare_diff_allowed": bare_diff_check,
        "anti_drift_allowed": anti_drift_check,
        "malformed_allowed": malformed_check,
        "json_redaction_sample": json_redacted,
        "truth_gate": updated_state.get("truth_gate"),
        "fulfillment_summary": {k: fulfill_report.get(k) for k in ("processed_count", "approved_count", "rejected_count", "succeeded_count", "failed_count")},
    }
    _append_analysis_check(report, "evidence_fulfillment", "safe_verify_command_allowed", safe_check.get("allowed") is True, safe_check)
    _append_analysis_check(report, "evidence_fulfillment", "credential_path_rejected", unsafe_check.get("allowed") is False and "credential" in str(unsafe_check.get("reason", "")), unsafe_check)
    _append_analysis_check(report, "evidence_fulfillment", "full_git_diff_rejected", bare_diff_check.get("allowed") is False, bare_diff_check)
    _append_analysis_check(report, "evidence_fulfillment", "anti_drift_write_flag_rejected", anti_drift_check.get("allowed") is False, anti_drift_check)
    _append_analysis_check(report, "evidence_fulfillment", "malformed_request_rejected", malformed_check.get("allowed") is False and "object" in str(malformed_check.get("reason", "")), malformed_check)
    _append_analysis_check(report, "evidence_fulfillment", "json_style_secret_redacted", "abcdef1234567890" not in json_redacted and "[REDACTED]" in json_redacted and "visible" in json_redacted, json_redacted)
    _append_analysis_check(report, "evidence_fulfillment", "approved_request_executes", fulfill_report.get("succeeded_count") == 1 and fulfill_report.get("failed_count") == 0, fulfill_report)
    _append_analysis_check(report, "evidence_fulfillment", "fulfilled_evidence_updates_truth_gate", updated_state.get("truth_gate", {}).get("can_certify_truth") is True and updated_state.get("truth_gate", {}).get("truth_status") == "grounded", updated_state.get("truth_gate"))

    clean_plans = [
        {"meta": {"planner_model": "model-a"}, "patches": [{"op": "noop", "rationale": "no change needed"}]},
        {"meta": {"planner_model": "model-b"}, "patches": [{"op": "noop", "rationale": "no change needed"}]},
    ]
    clean_discussion = run_discussion_rounds(clean_plans, current_best={"patches": [], "planner_patch_summary": _planner_patch_summary(clean_plans)}, models=["model-a", "model-b"], offline=True, evidence_bundle=supported_bundle)
    conflict_plans = [
        {"meta": {"planner_model": "model-a"}, "patches": [{"op": "noop", "rationale": "no change needed"}]},
        {"meta": {"planner_model": "model-b"}, "patches": [{"target_file": "scripts/consult_models.py", "op": "add_guard", "rationale": "concrete unresolved change"}]},
    ]
    conflict_discussion = run_discussion_rounds(conflict_plans, current_best={"patches": []}, models=["model-a", "model-b"], offline=True, evidence_bundle=supported_bundle)
    advisory_plans = [
        {"meta": {"planner_model": "model-a"}, "patches": [{"op": "noop", "rationale": "no change needed"}]},
        {"meta": {"planner_model": "model-b"}, "patches": [{"op": "noop", "rationale": "no change needed"}]},
        {"meta": {"planner_model": "model-c"}, "patches": [{"op": "noop", "rationale": "no change needed"}]},
        {
            "meta": {"planner_model": "model-d"},
            "diagnosis": {"root_cause_class": "no_action", "summary": "all acceptance criteria satisfied; no severity>=3 blockers remain"},
            "patches": [
                {"target_file": "scripts/example.py", "op": "tune_threshold", "risk": "low", "rationale": "Non-blocking observability follow-up for a warning; current gates already pass."},
                {"target_file": "scripts/example.py", "op": "document", "risk": "low", "rationale": "Document intentional fail-closed behavior for maintainers."},
            ],
        },
    ]
    advisory_summary = _planner_patch_summary(advisory_plans)
    advisory_discussion = run_discussion_rounds(advisory_plans, current_best={"patches": [], "planner_patch_summary": advisory_summary}, models=["model-a", "model-b", "model-c", "model-d"], offline=True, evidence_bundle=supported_bundle)
    report["discussion_matrix"] = {"clean": clean_discussion.get("status"), "conflict": conflict_discussion.get("status"), "advisory": advisory_discussion.get("status")}
    _append_analysis_check(report, "discussion", "offline_clean_discussion_certifies", clean_discussion.get("status") in {"certified", "certified_with_minor_risks"}, clean_discussion.get("reasons"))
    _append_analysis_check(report, "discussion", "offline_conflict_discussion_fails_closed", conflict_discussion.get("status") == "not_certified" and conflict_discussion.get("remaining_risks"), {"status": conflict_discussion.get("status"), "risks": conflict_discussion.get("remaining_risks")})
    _append_analysis_check(report, "discussion", "offline_no_action_advisory_certifies", advisory_discussion.get("status") in {"certified", "certified_with_minor_risks"} and advisory_summary.get("certification_intent") == "no_action_certification" and advisory_summary.get("concrete_patch_count") == 0, {"status": advisory_discussion.get("status"), "summary": advisory_summary, "risks": advisory_discussion.get("remaining_risks")})

    if include_temp_audit:
        with tempfile.TemporaryDirectory(prefix="consult-models-selfcheck-") as td:
            tick = os.path.join(td, "tick-selfcheck")
            plans_dir = os.path.join(tick, "plans")
            os.makedirs(plans_dir, exist_ok=True)
            for model in ("model-a", "model-b"):
                _write_json_atomic(os.path.join(plans_dir, f"{model}.json"), {"meta": {"planner_model": model}, "patches": [{"op": "noop", "rationale": "selfcheck noop"}]})
            fanout = fanout_certification_status(2, 2, 2, 0)
            truth = evaluate_truth_gate(supported_bundle)
            merged = {"patches": [], "planner_patch_summary": _planner_patch_summary(_load_tick_plans(tick)), "fanout_certification": fanout, "truth_assessment": truth}
            votes = [{"model": model, "vote": "approve", "best_within_constraints": True} for model in ("model-a", "model-b")]
            discussion = {"status": "certified", "models_consulted": ["model-a", "model-b"], "expected_participants": ["model-a", "model-b"], "fanout_certification": fanout, "truth_assessment": truth, "issue_ledger": [], "ratification_votes": votes, "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95}}
            _write_json_atomic(os.path.join(tick, "merged_plan.json"), merged)
            _write_json_atomic(os.path.join(tick, "discussion_result.json"), discussion)
            manifest = audit_certification(tick, write=True)
            report["temp_audit_manifest_status"] = manifest.get("status")
            _append_analysis_check(report, "certification_audit", "valid_temp_tick_certifies", manifest.get("can_claim_complete_certification") is True, manifest)

            bad_tick = os.path.join(td, "tick-selfcheck-participant-alias")
            bad_plans_dir = os.path.join(bad_tick, "plans")
            os.makedirs(bad_plans_dir, exist_ok=True)
            alias_models = ["claude", "codex", "deepseek", "mimo"]
            canonical_models = ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"]
            for model in alias_models:
                _write_json_atomic(os.path.join(bad_plans_dir, f"{model}.json"), {"meta": {"planner_model": model}, "patches": [{"op": "noop", "rationale": "selfcheck noop"}]})
            bad_fanout = fanout_certification_status(4, 4, 4, 0)
            bad_merged = {"patches": [], "planner_patch_summary": _planner_patch_summary(_load_tick_plans(bad_tick)), "fanout_certification": bad_fanout, "truth_assessment": truth}
            bad_votes = [{"model": model, "vote": "approve", "best_within_constraints": True} for model in alias_models]
            bad_discussion = {"status": "certified", "models_consulted": alias_models, "expected_participants": canonical_models, "fanout_certification": bad_fanout, "truth_assessment": truth, "issue_ledger": [], "ratification_votes": bad_votes, "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95}}
            _write_json_atomic(os.path.join(bad_tick, "merged_plan.json"), bad_merged)
            _write_json_atomic(os.path.join(bad_tick, "discussion_result.json"), bad_discussion)
            bad_manifest = audit_certification(bad_tick, write=False)
            report["participant_identity_matrix"] = {
                "alias_vs_canonical_status": bad_manifest.get("status"),
                "alias_vs_canonical_reasons": bad_manifest.get("reasons", []),
            }
            _append_analysis_check(
                report,
                "certification_audit",
                "expected_participant_identity_fail_closed",
                bad_manifest.get("can_claim_complete_certification") is False
                and any("expected participants" in reason for reason in bad_manifest.get("reasons", [])),
                bad_manifest,
            )

    report["status"] = "PASS" if report["summary"]["failed"] == 0 else "FAIL"
    report["summary"]["total"] = len(report.get("checks", []))
    return report


def evaluate_ratification(
    votes: List[dict],
    agreement_matrix: dict,
    issue_ledger: List[dict],
    revised_this_round: bool,
    novel_redteam_blocker: bool,
    min_agreement: float = 0.85,
    truth_gate: Optional[dict] = None,
) -> dict:
    """Evaluate true multi-model stop condition.

    Multi-model approval is not factual verification. If an evidence/truth gate is
    supplied, unsupported or contradicted high-severity claims fail closed even when
    every reviewer votes approve.
    """
    reasons: List[str] = []
    n = len(votes)
    approvals = sum(1 for v in votes if str(v.get("vote", "")).lower() == "approve" and _strict_true(v.get("best_within_constraints")))
    rejects = [v for v in votes if str(v.get("vote", "")).lower() == "reject"]
    unsigned = [v for v in votes if not _strict_true(v.get("best_within_constraints"))]
    blockers = [i for i in issue_ledger if i.get("status") == "unresolved" and _safe_int(i.get("severity", 3), 3) >= 3]

    if approvals < max(1, n - 1):
        reasons.append(f"approval_count {approvals}/{n} below N-1")
    if rejects:
        reasons.append(f"reject votes present: {[v.get('model') for v in rejects]}")
    if unsigned:
        reasons.append(f"missing best_within_constraints signatures: {[v.get('model') for v in unsigned]}")
    for axis in ("framing", "approach", "implementation_order"):
        if _safe_float(agreement_matrix.get(axis, 0.0)) < min_agreement:
            reasons.append(f"agreement.{axis} below {min_agreement}")
    if revised_this_round:
        reasons.append("revision occurred this round")
    if novel_redteam_blocker:
        reasons.append("novel severity>=3 red-team blocker")
    if blockers:
        reasons.append(f"unresolved blockers: {[i.get('id') for i in blockers]}")
    if truth_gate:
        unsupported_high = truth_gate.get("unsupported_high_severity_claim_ids") or []
        contradicted_high = truth_gate.get("contradicted_high_severity_claim_ids") or []
        if unsupported_high:
            reasons.append(f"unsupported high-severity factual claims: {unsupported_high}")
        if contradicted_high:
            reasons.append(f"contradicted high-severity factual claims: {contradicted_high}")
        if not truth_gate.get("can_certify_truth", True) and not (unsupported_high or contradicted_high):
            reasons.append("truth gate not certified: " + "; ".join(truth_gate.get("reasons", [])))

    minor_risks = [i for i in issue_ledger if i.get("status") == "unresolved" and _safe_int(i.get("severity", 0)) <= 2]
    if reasons:
        status = "not_certified"
    elif minor_risks:
        status = "certified_with_minor_risks"
    else:
        status = "certified"
    return {
        "status": status,
        "approval_count": approvals,
        "reject_count": len(rejects),
        "reasons": reasons,
    }


def _agreement_from_issues(issue_ledger: List[dict]) -> dict:
    unresolved = [i for i in issue_ledger if i.get("status") == "unresolved"]
    blockers = [i for i in unresolved if _safe_int(i.get("severity", 3), 3) >= 3]
    if not unresolved:
        score = 0.95
    elif not blockers:
        score = 0.87
    else:
        score = 0.65
    return {"framing": score, "approach": score, "implementation_order": score}


def _offline_votes(models: List[str], issue_ledger: List[dict]) -> List[dict]:
    blockers = [i for i in issue_ledger if i.get("status") == "unresolved" and _safe_int(i.get("severity", 3), 3) >= 3]
    vote = "reject" if blockers else "approve"
    return [
        {
            "model": model,
            "vote": vote,
            "best_within_constraints": not blockers,
            "reasoning": "offline deterministic ratification; blockers present" if blockers else "offline deterministic ratification; no unresolved blockers",
        }
        for model in models
    ]


def write_discussion_checkpoint(
    checkpoint_dir: str,
    *,
    round_no: int,
    status: dict,
    votes: List[dict],
    issue_ledger: List[dict],
    transcript: List[dict],
    communication_round: dict,
    models: List[str],
) -> None:
    """Durably checkpoint one completed discussion round.

    RMCS is artifact-first: a killed process must leave enough cursor/state to
    audit that the run is partial_uncertified rather than silently pretending it
    never happened.
    """
    base = os.path.join(os.path.expanduser(checkpoint_dir), "discussion")
    round_dir = os.path.join(base, f"round_{round_no:03d}")
    unresolved = [i for i in issue_ledger if i.get("status") == "unresolved"]
    summary = {
        "schema_version": "discussion_round_checkpoint_v1",
        "round": round_no,
        "written_at": _utc_now_iso(),
        "status": status.get("status", "not_certified"),
        "status_detail": status,
        "votes": votes,
        "unresolved_issue_ids": [i.get("id") for i in unresolved],
        "unresolved_severity_ge_3_count": sum(1 for i in unresolved if _safe_int(i.get("severity", 3), 3) >= 3),
        "communication": communication_round,
    }
    cursor = {
        "schema_version": "discussion_cursor_v1",
        "updated_at": summary["written_at"],
        "rounds_completed": round_no,
        "latest_round_dir": os.path.relpath(round_dir, os.path.expanduser(checkpoint_dir)),
        "latest_status": summary["status"],
        "complete": summary["status"] in ("certified", "certified_with_minor_risks"),
    }
    state = {
        "schema_version": "discussion_state_v1",
        "updated_at": summary["written_at"],
        "status": summary["status"],
        "models": models,
        "rounds_completed": round_no,
        "issue_ledger": issue_ledger,
        "transcript": transcript,
    }
    heartbeat = {
        "schema_version": "discussion_heartbeat_v1",
        "updated_at": summary["written_at"],
        "round": round_no,
        "status": summary["status"],
    }
    _write_json_atomic(os.path.join(round_dir, "round_summary.json"), summary)
    _write_json_atomic(os.path.join(base, "cursor.json"), cursor)
    _write_json_atomic(os.path.join(base, "state.json"), state)
    _write_json_atomic(os.path.join(base, "heartbeat.json"), heartbeat)


def write_discussion_model_checkpoint(
    checkpoint_dir: str,
    *,
    round_no: int,
    model: str,
    models: List[str],
    models_completed: List[str],
    parse_status: str,
    raw_response: str,
    parsed_response: dict,
    issue_ledger: List[dict],
    transcript: List[dict],
) -> None:
    """Persist a single model response immediately after it returns.

    This is stricter than per-round checkpointing: SIGTERM after model 3/4 still
    leaves model-level raw/parsed/parse_status artifacts and a cursor pointing to
    the next incomplete model.
    """
    written_at = _utc_now_iso()
    base = os.path.join(os.path.expanduser(checkpoint_dir), "discussion")
    round_dir = os.path.join(base, f"round_{round_no:03d}")
    safe_model = _safe_artifact_name(model)
    response_artifact = {
        "schema_version": "discussion_model_response_v1",
        "round": round_no,
        "model": model,
        "written_at": written_at,
        "parse_status": parse_status,
        "raw_response": raw_response,
        "parsed_response": parsed_response,
    }
    parse_artifact = {
        "schema_version": "discussion_parse_status_v1",
        "round": round_no,
        "model": model,
        "written_at": written_at,
        "parse_status": parse_status,
        "vote": parsed_response.get("vote") if isinstance(parsed_response, dict) else None,
        "best_within_constraints": parsed_response.get("best_within_constraints") if isinstance(parsed_response, dict) else None,
    }
    remaining = [m for m in models if m not in set(models_completed)]
    cursor = {
        "schema_version": "discussion_cursor_v1",
        "updated_at": written_at,
        "rounds_completed": max(0, round_no - 1),
        "round_in_progress": round_no,
        "models_completed": models_completed,
        "next_model": remaining[0] if remaining else None,
        "latest_round_dir": os.path.relpath(round_dir, os.path.expanduser(checkpoint_dir)),
        "latest_status": "model_checkpointed",
        "complete": False,
    }
    state = {
        "schema_version": "discussion_state_v1",
        "updated_at": written_at,
        "status": "model_checkpointed",
        "models": models,
        "rounds_completed": max(0, round_no - 1),
        "round_in_progress": round_no,
        "models_completed": models_completed,
        "next_model": cursor["next_model"],
        "issue_ledger": issue_ledger,
        "transcript": transcript,
    }
    heartbeat = {
        "schema_version": "discussion_heartbeat_v1",
        "updated_at": written_at,
        "round": round_no,
        "model": model,
        "status": "model_checkpointed",
        "models_completed_count": len(models_completed),
        "models_total": len(models),
    }
    _write_json_atomic(os.path.join(round_dir, f"model_response_{safe_model}.json"), response_artifact)
    _write_json_atomic(os.path.join(round_dir, f"parse_status_{safe_model}.json"), parse_artifact)
    _write_json_atomic(os.path.join(base, "cursor.json"), cursor)
    _write_json_atomic(os.path.join(base, "state.json"), state)
    _write_json_atomic(os.path.join(base, "heartbeat.json"), heartbeat)


def run_discussion_rounds(
    plans: List[dict],
    current_best: dict,
    models: Optional[List[str]] = None,
    max_rounds: int = 5,
    offline: bool = False,
    call_model_fn=None,
    evidence_bundle: Optional[dict] = None,
    checkpoint_dir: Optional[str] = None,
) -> dict:
    """Run Phase 3-6 discussion/ratification loop.

    Offline mode is deterministic and used for tests/dry-runs. Online mode currently
    performs ratification prompts through call_model_fn when supplied; if no callable is
    supplied, it safely falls back to offline behavior rather than pretending certification.
    """
    models = models or [_plan_model(p, f"model_{i}") for i, p in enumerate(plans)]
    issue_ledger = build_issue_ledger(plans)
    evidence_bundle = evidence_bundle or build_evidence_bundle({})
    truth_gate = evaluate_truth_gate(evidence_bundle)
    evidence_requests = collect_evidence_requests(plans)
    rounds_used = 0
    transcript: List[dict] = []
    communication_rounds: List[dict] = []
    revised_this_round = False

    for round_no in range(1, max(1, max_rounds) + 1):
        novel_redteam_blocker = False
        rounds_used = round_no
        unresolved = [i for i in issue_ledger if i.get("status") == "unresolved"]
        round_prompt_chars: Dict[str, int] = {}
        parse_status_by_model: Dict[str, str] = {}
        round_token_budget: dict = {}
        round_prompt_mode = "offline"
        if offline or call_model_fn is None:
            # Deterministic dry-run: no blockers means every model can certify; blockers
            # remain unresolved and correctly prevent false certification.
            votes = _offline_votes(models, issue_ledger)
        else:
            votes = []
            new_critiques = []
            models_completed: List[str] = []
            prompt_context = build_discussion_comm_packet(
                current_best=current_best,
                unresolved_issues=unresolved,
                evidence_bundle=evidence_bundle,
                truth_gate=truth_gate,
                round_no=round_no,
                previous_transcript=transcript,
            )
            round_token_budget = dict(prompt_context.get("token_budget", {}))
            round_prompt_mode = str(prompt_context.get("mode") or "manifest_delta")
            for model in models:
                raw = ""
                parse_status = "ok"
                try:
                    prompt_text = json.dumps(prompt_context, ensure_ascii=False)
                    round_prompt_chars[model] = len(prompt_text)
                    raw = call_model_fn(model, prompt_text)
                    parsed = extract_plan_json(raw)
                except ModelRuntimeError as e:
                    parse_status = "runtime_error"
                    raw = getattr(e, "raw_response", "") or _truncate_runtime_error_text(str(e), 2000)
                    parsed = {
                        "vote": "amend",
                        "best_within_constraints": False,
                        "reasoning": f"discussion runtime/provider failure: {_truncate_runtime_error_text(str(e), 240)}",
                        "critiques": [],
                        "evidence_requests": [],
                    }
                except Exception as e:
                    parse_status = "retried"
                    if getattr(e, "raw_response", None):
                        raw = getattr(e, "raw_response", "") or raw
                    try:
                        strict_context = {
                            "unresolved_issues": unresolved,
                            "truth_gate": truth_gate,
                            "required_output": prompt_context["required_output"],
                        }
                        strict_prompt = (
                            "Return ONLY a JSON object matching this schema: "
                            '{"critiques":[],"evidence_requests":[],"vote":"approve|amend|reject",'
                            '"best_within_constraints":true,"reasoning":"..."}. '
                            "No markdown, no prose before or after JSON. Context: "
                            + json.dumps(strict_context, ensure_ascii=False)
                        )
                        raw = call_model_fn(model, strict_prompt)
                        parsed = extract_plan_json(raw)
                    except Exception as retry_e:
                        parse_status = "failed_closed"
                        if getattr(retry_e, "raw_response", None):
                            raw = getattr(retry_e, "raw_response", "") or raw
                        parsed = {
                            "vote": "amend",
                            "best_within_constraints": False,
                            "reasoning": f"discussion call failed/unparseable: initial={str(e)[:120]}; retry={str(retry_e)[:120]}",
                            "critiques": [],
                        }
                parse_status_by_model[model] = parse_status
                models_completed.append(model)
                if checkpoint_dir:
                    write_discussion_model_checkpoint(
                        checkpoint_dir,
                        round_no=round_no,
                        model=model,
                        models=models,
                        models_completed=list(models_completed),
                        parse_status=parse_status,
                        raw_response=raw,
                        parsed_response=parsed if isinstance(parsed, dict) else {},
                        issue_ledger=issue_ledger,
                        transcript=transcript,
                    )
                for critique in parsed.get("critiques", []) or []:
                    if not isinstance(critique, dict) or not critique.get("novel", True):
                        continue
                    severity = _safe_int(critique.get("severity", 3), 3)
                    if severity >= 3:
                        new_critiques.append({
                            "id": f"I-{len(issue_ledger) + len(new_critiques) + 1:03d}",
                            "status": "unresolved",
                            "severity": severity,
                            "models": [model],
                            "target_model": critique.get("target_model", "unknown"),
                            "claim": critique.get("claim", "model critique"),
                            "evidence": critique.get("evidence", ""),
                            "resolution": critique.get("correction", ""),
                        })
                for req in collect_evidence_requests([{**parsed, "meta": {"planner_model": model}}]):
                    key = (req.get("requested_by"), req.get("claim_id"), req.get("claim"), req.get("tool_needed"), req.get("command"), req.get("why"))
                    existing = {(r.get("requested_by"), r.get("claim_id"), r.get("claim"), r.get("tool_needed"), r.get("command"), r.get("why")) for r in evidence_requests}
                    if key not in existing:
                        evidence_requests.append(req)
                votes.append({"model": model, "vote": parsed.get("vote", "amend"), "best_within_constraints": _strict_true(parsed.get("best_within_constraints")), "reasoning": parsed.get("reasoning", "")})
            if new_critiques:
                issue_ledger.extend(new_critiques)
                novel_redteam_blocker = True

        agreement = _agreement_from_issues(issue_ledger)
        status = evaluate_ratification(votes, agreement, issue_ledger, revised_this_round, novel_redteam_blocker, truth_gate=truth_gate)
        round_comm = {
            "round": round_no,
            "mode": round_prompt_mode if round_token_budget else "offline",
            "prompt_chars_by_model": round_prompt_chars,
            "prompt_chars": sum(round_prompt_chars.values()),
            "raw_context_chars_per_model": round_token_budget.get("raw_context_chars", 0),
            "packet_chars_per_model": round_token_budget.get("packet_chars", 0),
            "estimated_chars_saved": int(round_token_budget.get("estimated_chars_saved", 0)) * len(round_prompt_chars),
            "estimated_tokens_saved": int(round_token_budget.get("estimated_tokens_saved", 0)) * len(round_prompt_chars),
            "compression_ratio": round_token_budget.get("compression_ratio", 1.0),
        }
        communication_rounds.append(round_comm)
        transcript.append({
            "round": round_no,
            "unresolved_issue_ids": [i.get("id") for i in unresolved],
            "votes": votes,
            "status": status,
            "prompt_chars": round_comm["prompt_chars"],
            "prompt_chars_by_model": round_comm["prompt_chars_by_model"],
            "parse_status_by_model": parse_status_by_model,
            "estimated_chars_saved": round_comm["estimated_chars_saved"],
        })
        if checkpoint_dir:
            write_discussion_checkpoint(
                checkpoint_dir,
                round_no=round_no,
                status=status,
                votes=votes,
                issue_ledger=issue_ledger,
                transcript=transcript,
                communication_round=round_comm,
                models=models,
            )
        if status["status"] in ("certified", "certified_with_minor_risks"):
            break
        # If there are blockers and no online model callable to resolve them, more
        # deterministic rounds cannot change the result. Stop honestly.
        if offline or call_model_fn is None:
            break

    final_status = transcript[-1]["status"] if transcript else {"status": "not_certified", "reasons": ["no rounds executed"]}
    comm_modes = {r.get("mode") for r in communication_rounds if r.get("mode")}
    if not comm_modes:
        communication_mode = "none"
    elif comm_modes == {"offline"}:
        communication_mode = "offline"
    elif "manifest_delta" in comm_modes:
        communication_mode = "manifest_delta"
    else:
        communication_mode = sorted(comm_modes)[0]
    communication_summary = {
        "schema": COMM_PACKET_SCHEMA_VERSION,
        "mode": communication_mode,
        "rounds": communication_rounds,
        "total_prompt_chars": sum(r.get("prompt_chars", 0) for r in communication_rounds),
        "estimated_chars_saved": sum(r.get("estimated_chars_saved", 0) for r in communication_rounds),
        "estimated_tokens_saved": sum(r.get("estimated_tokens_saved", 0) for r in communication_rounds),
        "policy": "send manifest+delta packets; keep full artifacts in tick files; request omitted evidence explicitly",
    }
    return {
        "status": final_status["status"],
        "models_consulted": models,
        "expected_participants": models,
        "rounds_used": rounds_used,
        "agreement_matrix": _agreement_from_issues(issue_ledger),
        "final_design": current_best,
        "issue_ledger": issue_ledger,
        "ratification_votes": transcript[-1]["votes"] if transcript else [],
        "discussion_transcript": transcript,
        "communication": communication_summary,
        "remaining_risks": [i for i in issue_ledger if i.get("status") != "resolved"],
        "truth_assessment": truth_gate,
        "evidence_bundle": evidence_bundle,
        "evidence_requests": evidence_requests,
        "provenance": [f"{_plan_model(plan, f'model_{i}')} contributed seed proposal" for i, plan in enumerate(plans)],
        "reasons": final_status.get("reasons", []),
    }


def _artifact_entry(path: str, base: str) -> dict:
    exists = os.path.exists(path)
    entry = {"path": os.path.relpath(path, base), "exists": exists}
    if exists:
        try:
            entry["bytes"] = os.path.getsize(path)
            with open(path, "rb") as f:
                entry["sha256"] = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            entry["read_error"] = True
    return entry


def audit_certification(tick_dir: str, write: bool = False) -> dict:
    """Audit a tick directory and fail closed unless ratification artifacts are complete.

    This is the RMCS deterministic ratifier: model agreement is provenance, but
    complete certification requires a discussion_result plus fanout/truth gates.
    """
    tick_dir = os.path.abspath(os.path.expanduser(tick_dir))
    plans_dir = os.path.join(tick_dir, "plans")
    merged_path = os.path.join(tick_dir, "merged_plan.json")
    discussion_path = os.path.join(tick_dir, "discussion_result.json")
    final_path = os.path.join(tick_dir, "final", "certification_manifest.json")
    plan_files = sorted(
        os.path.join(plans_dir, p)
        for p in os.listdir(plans_dir)
        if p.endswith(".json")
    ) if os.path.isdir(plans_dir) else []
    raw_merged = _read_json_file(merged_path, {})
    raw_discussion = _read_json_file(discussion_path, None)
    reasons: List[str] = []
    gates: Dict[str, Any] = {}
    merged = raw_merged if isinstance(raw_merged, dict) else {}
    discussion = raw_discussion if isinstance(raw_discussion, dict) else None
    if os.path.isfile(merged_path) and not isinstance(raw_merged, dict):
        reasons.append("merged_plan malformed")
    if os.path.isfile(discussion_path) and raw_discussion is not None and not isinstance(raw_discussion, dict):
        reasons.append("discussion_result malformed")

    gates["tick_dir_exists"] = os.path.isdir(tick_dir)
    gates["plans_present"] = len(plan_files) > 0
    gates["merged_plan_present"] = os.path.isfile(merged_path)
    gates["discussion_result_present"] = isinstance(discussion, dict)
    if not gates["tick_dir_exists"]:
        reasons.append("missing tick_dir")
    if not gates["plans_present"]:
        reasons.append("missing plans/*.json")
    if not gates["merged_plan_present"]:
        reasons.append("missing merged_plan.json")
    if not gates["discussion_result_present"]:
        reasons.append("missing discussion_result.json")

    source = discussion if isinstance(discussion, dict) else merged

    def _gate_from_source(primary: dict, fallback: dict, keys: Tuple[str, ...], reason_name: str) -> dict:
        for key in keys:
            if key in primary:
                value = primary.get(key)
                if isinstance(value, dict):
                    return value
                reasons.append(f"{reason_name} malformed")
                return {}
        for key in keys:
            if key in fallback:
                value = fallback.get(key)
                if isinstance(value, dict):
                    return value
                reasons.append(f"merged {reason_name} malformed")
                return {}
        return {}

    def _merged_patches_are_list(plan: dict) -> bool:
        return isinstance(plan, dict) and isinstance(plan.get("patches"), list)

    def _empty_patch_no_action_summary_valid(plan: dict) -> bool:
        patches = plan.get("patches") if isinstance(plan, dict) else None
        if not isinstance(patches, list):
            return False
        if len(patches) != 0:
            return True
        summary = plan.get("planner_patch_summary") if isinstance(plan.get("planner_patch_summary"), dict) else {}
        stored_no_action = (
            _strict_int(summary.get("concrete_patch_count")) == 0
            and str(summary.get("certification_intent", "")).strip().casefold() == "no_action_certification"
        )
        recomputed_no_action = (
            _strict_int(recomputed_patch_summary.get("concrete_patch_count")) == 0
            and str(recomputed_patch_summary.get("certification_intent", "")).strip().casefold() == "no_action_certification"
        )
        return stored_no_action and recomputed_no_action

    fanout = _gate_from_source(source, merged if source is not merged else {}, ("fanout_certification",), "fanout_certification")
    truth = _gate_from_source(source, merged if source is not merged else {}, ("truth_assessment", "truth_gate"), "truth_assessment")
    merged_fanout: dict = {}
    merged_truth: dict = {}
    if source is not merged:
        if "fanout_certification" in merged:
            value = merged.get("fanout_certification")
            if isinstance(value, dict):
                merged_fanout = value
            else:
                reasons.append("merged fanout_certification malformed")
        for key in ("truth_assessment", "truth_gate"):
            if key in merged:
                value = merged.get(key)
                if isinstance(value, dict):
                    merged_truth = value
                else:
                    reasons.append("merged truth_assessment malformed")
                break
    else:
        merged_fanout = fanout
        merged_truth = truth
    raw_issue_ledger = source.get("issue_ledger")
    issue_ledger = raw_issue_ledger if isinstance(raw_issue_ledger, list) else []
    raw_votes = source.get("ratification_votes")
    votes = raw_votes if isinstance(raw_votes, list) else []
    discussion_status = discussion.get("status") if isinstance(discussion, dict) else None
    plan_models: List[str] = []
    audit_plans: List[dict] = []
    for idx, plan_file in enumerate(plan_files):
        raw_plan = _read_json_file(plan_file, None)
        if not isinstance(raw_plan, dict):
            reasons.append(f"plan artifact malformed: {os.path.basename(plan_file)}")
            raw_plan = {}
        else:
            audit_plans.append(raw_plan)
        plan_models.append(_plan_model(raw_plan, f"model_{idx}"))
    recomputed_patch_summary = _planner_patch_summary(audit_plans)

    def _strict_nonempty_string_list(value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if not isinstance(value, list):
            return None
        parsed: List[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                return None
            parsed.append(item.strip())
        return parsed

    raw_expected_participants = source.get("expected_participants")
    if raw_expected_participants is None and source is not merged:
        raw_expected_participants = merged.get("expected_participants")
    expected_participants = _strict_nonempty_string_list(raw_expected_participants)
    raw_models_consulted = source.get("models_consulted")
    models_consulted = _strict_nonempty_string_list(raw_models_consulted)

    fanout_schema_ok = False
    fanout_schema_errors: List[str] = []
    merged_fanout_schema_ok = False
    merged_fanout_schema_errors: List[str] = []
    if fanout:
        fanout_schema_ok, fanout_schema_errors = validate_fanout_certification_status(fanout)
    if merged_fanout:
        merged_fanout_schema_ok, merged_fanout_schema_errors = validate_fanout_certification_status(merged_fanout)

    gates["fanout_certification_schema_valid"] = fanout_schema_ok
    gates["fanout_certification_schema_errors"] = fanout_schema_errors
    gates["merged_fanout_certification_schema_valid"] = merged_fanout_schema_ok
    gates["merged_fanout_certification_schema_errors"] = merged_fanout_schema_errors
    gates["fanout_certified"] = fanout_schema_ok and _strict_true(fanout.get("certified"))
    gates["multi_model_certified"] = fanout_schema_ok and _strict_true(fanout.get("multi_model_certified"))
    gates["truth_can_certify"] = _strict_true(truth.get("can_certify_truth"))
    gates["merged_fanout_certified"] = merged_fanout_schema_ok and _strict_true(merged_fanout.get("certified"))
    gates["merged_multi_model_certified"] = merged_fanout_schema_ok and _strict_true(merged_fanout.get("multi_model_certified"))
    gates["merged_truth_can_certify"] = _strict_true(merged_truth.get("can_certify_truth"))
    planner_count = _strict_int(fanout.get("planner_count"))
    success_count = _strict_int(fanout.get("success_count"))
    merged_planner_count = _strict_int(merged_fanout.get("planner_count")) if merged_fanout else None
    merged_success_count = _strict_int(merged_fanout.get("success_count")) if merged_fanout else None
    expected_vote_count = planner_count if planner_count is not None else len(plan_files)
    valid_votes = [v for v in votes if isinstance(v, dict)]
    vote_models = [str(v.get("model", "")).strip() for v in valid_votes]
    vote_model_set = set(vote_models)
    plan_model_set = set(plan_models)
    expected_model_set = set(expected_participants) if expected_participants is not None else plan_model_set
    duplicate_expected_participants = sorted({m for m in (expected_participants or []) if (expected_participants or []).count(m) > 1})
    duplicate_plan_models = sorted({m for m in plan_models if m and plan_models.count(m) > 1})
    duplicate_vote_models = sorted({m for m in vote_models if m and vote_models.count(m) > 1})
    duplicate_consulted_models = sorted({m for m in (models_consulted or []) if (models_consulted or []).count(m) > 1})
    anonymous_vote_count = sum(1 for m in vote_models if not m)
    unexpected_vote_models = sorted(vote_model_set - expected_model_set) if expected_model_set else []
    missing_vote_models = sorted(expected_model_set - vote_model_set) if expected_model_set else []
    unexpected_plan_models = sorted(plan_model_set - expected_model_set) if expected_participants is not None else []
    missing_plan_models = sorted(expected_model_set - plan_model_set) if expected_participants is not None else []
    consulted_model_set = set(models_consulted or [])
    unexpected_consulted_models = sorted(consulted_model_set - expected_model_set) if models_consulted is not None and expected_model_set else []
    missing_consulted_models = sorted(expected_model_set - consulted_model_set) if models_consulted is not None and expected_model_set else []
    approvals = [v for v in valid_votes if str(v.get("vote", "")).lower() == "approve" and _strict_true(v.get("best_within_constraints"))]
    approving_model_set = {str(v.get("model", "")).strip() for v in approvals if str(v.get("model", "")).strip()}
    missing_expected_approvals = sorted(expected_model_set - approving_model_set) if expected_participants is not None else []
    rejects = [v for v in valid_votes if str(v.get("vote", "")).lower() == "reject"]
    unsigned = [v for v in valid_votes if not _strict_true(v.get("best_within_constraints"))]
    gates["issue_ledger_present"] = isinstance(raw_issue_ledger, list)
    gates["issue_ledger_malformed_count"] = sum(1 for i in issue_ledger if not isinstance(i, dict))
    gates["ratification_votes_present"] = isinstance(raw_votes, list)
    gates["ratification_vote_count"] = len(valid_votes)
    gates["non_dict_vote_count"] = len(votes) - len(valid_votes) if isinstance(votes, list) else 0
    gates["expected_vote_count"] = expected_vote_count
    gates["planner_count"] = planner_count
    gates["success_count"] = success_count
    gates["merged_planner_count"] = merged_planner_count
    gates["merged_success_count"] = merged_success_count
    gates["plan_file_count"] = len(plan_files)
    gates["expected_participants_present"] = raw_expected_participants is not None
    gates["expected_participants_valid"] = raw_expected_participants is None or expected_participants is not None
    gates["expected_participant_count"] = len(expected_participants or [])
    gates["expected_participants_unique"] = not duplicate_expected_participants
    gates["models_consulted_present"] = raw_models_consulted is not None
    gates["models_consulted_valid"] = raw_models_consulted is None or models_consulted is not None
    gates["models_consulted_unique"] = not duplicate_consulted_models
    gates["plan_models_unique"] = not duplicate_plan_models
    gates["plan_models_match_expected"] = expected_participants is None or (not unexpected_plan_models and not missing_plan_models and not duplicate_plan_models)
    gates["models_consulted_match_expected"] = models_consulted is None or (not unexpected_consulted_models and not missing_consulted_models and not duplicate_consulted_models)
    gates["approval_count"] = len(approvals)
    gates["unique_approval_count"] = len(approving_model_set)
    gates["reject_count"] = len(rejects)
    gates["no_reject_votes"] = not rejects
    gates["all_votes_best_within_constraints"] = not unsigned
    gates["vote_models_unique"] = not duplicate_vote_models
    gates["vote_models_nonempty"] = anonymous_vote_count == 0
    gates["vote_models_expected"] = not unexpected_vote_models and (expected_participants is None or not missing_vote_models)
    gates["expected_participants_all_approved"] = expected_participants is None or not missing_expected_approvals
    gates["ratification_quorum_met"] = (
        gates["ratification_vote_count"] >= max(2, expected_vote_count - 1)
        and gates["unique_approval_count"] >= max(2, expected_vote_count - 1)
    )
    gates["unresolved_severity_ge_3_count"] = sum(
        1 for i in issue_ledger
        if isinstance(i, dict) and i.get("status") == "unresolved" and _safe_int(i.get("severity", 3), 3) >= 3
    )
    agreement = source.get("agreement_matrix") if isinstance(source.get("agreement_matrix"), dict) else {}
    gates["agreement_matrix_present"] = all(axis in agreement for axis in ("framing", "approach", "implementation_order"))
    gates["agreement_matrix_min"] = min([_safe_float(agreement.get(axis)) for axis in ("framing", "approach", "implementation_order")]) if gates["agreement_matrix_present"] else 0.0
    gates["agreement_matrix_pass"] = gates["agreement_matrix_present"] and gates["agreement_matrix_min"] >= 0.85
    gates["discussion_status"] = discussion_status or "missing"
    gates["merged_patches_are_list"] = _merged_patches_are_list(merged)
    gates["empty_patches_have_no_action_intent"] = _empty_patch_no_action_summary_valid(merged)
    gates["plan_patch_artifacts_well_formed"] = not any(
        _strict_int(recomputed_patch_summary.get(key)) or 0
        for key in (
            "malformed_plan_count",
            "plans_missing_patches_count",
            "plans_non_list_patches_count",
            "non_dict_patch_count",
        )
    )

    if not fanout:
        reasons.append("missing fanout_certification")
    elif fanout_schema_errors:
        reasons.append(f"fanout_certification invalid: {'; '.join(fanout_schema_errors)}")
    elif not gates["fanout_certified"]:
        reasons.append(f"fanout not certified: {fanout.get('status', 'unknown')}")
    if not fanout or not gates["multi_model_certified"]:
        reasons.append("fanout is not multi-model certified")
    if source is not merged:
        if not merged_fanout:
            reasons.append("missing merged fanout_certification")
        else:
            if merged_fanout_schema_errors:
                reasons.append(f"merged fanout_certification invalid: {'; '.join(merged_fanout_schema_errors)}")
            elif not gates["merged_fanout_certified"]:
                reasons.append(f"merged fanout not certified: {merged_fanout.get('status', 'unknown')}")
            if not gates["merged_multi_model_certified"]:
                reasons.append("merged fanout is not multi-model certified")
    if planner_count is None or success_count is None:
        reasons.append("fanout planner_count/success_count must be strict integers")
    elif planner_count < 2 or success_count < 2:
        reasons.append("fanout planner_count/success_count below 2")
    elif planner_count != len(plan_files) or success_count != len(plan_files):
        reasons.append("fanout counts inconsistent with plan files")
    if source is not merged and merged_fanout:
        if merged_planner_count is None or merged_success_count is None:
            reasons.append("merged fanout planner_count/success_count must be strict integers")
        elif merged_planner_count < 2 or merged_success_count < 2:
            reasons.append("merged fanout planner_count/success_count below 2")
        elif merged_planner_count != len(plan_files) or merged_success_count != len(plan_files):
            reasons.append("merged fanout counts inconsistent with plan files")
    if not gates["issue_ledger_present"]:
        reasons.append("issue_ledger missing or malformed")
    if gates["issue_ledger_malformed_count"]:
        reasons.append("issue_ledger contains malformed entries")
    if not gates["ratification_votes_present"]:
        reasons.append("ratification_votes missing or malformed")
    if gates["non_dict_vote_count"]:
        reasons.append("ratification_votes contains malformed entries")
    if not gates["vote_models_nonempty"]:
        reasons.append("ratification vote missing model identity")
    if not gates["expected_participants_valid"]:
        reasons.append("expected_participants missing or malformed")
    if not gates["expected_participants_unique"]:
        reasons.append(f"duplicate expected participants: {duplicate_expected_participants}")
    if not gates["models_consulted_valid"]:
        reasons.append("models_consulted missing or malformed")
    if not gates["models_consulted_unique"]:
        reasons.append(f"duplicate models_consulted entries: {duplicate_consulted_models}")
    if not gates["plan_models_unique"]:
        reasons.append(f"duplicate plan models: {duplicate_plan_models}")
    if not gates["plan_models_match_expected"]:
        reasons.append(f"plan models do not match expected participants: missing={missing_plan_models} unexpected={unexpected_plan_models}")
    if not gates["models_consulted_match_expected"]:
        reasons.append(f"models_consulted do not match expected participants: missing={missing_consulted_models} unexpected={unexpected_consulted_models}")
    if not gates["vote_models_unique"]:
        reasons.append(f"duplicate ratification votes: {duplicate_vote_models}")
    if not gates["vote_models_expected"]:
        if missing_vote_models:
            reasons.append(f"ratification votes missing expected participants: {missing_vote_models}")
        if unexpected_vote_models:
            reasons.append(f"unexpected ratification vote models: {unexpected_vote_models}")
    if not gates["expected_participants_all_approved"]:
        reasons.append(f"ratification approvals do not cover expected participants: missing={missing_expected_approvals}")
    if not truth:
        reasons.append("missing truth_assessment")
    elif not gates["truth_can_certify"]:
        reasons.append("truth gate cannot certify")
    if source is not merged:
        if not merged_truth:
            reasons.append("missing merged truth_assessment")
        elif not gates["merged_truth_can_certify"]:
            reasons.append("merged truth gate cannot certify")
    if not gates["ratification_quorum_met"]:
        reasons.append(f"ratification quorum not met: approvals={gates['approval_count']} votes={gates['ratification_vote_count']} expected={expected_vote_count}")
    if not gates["all_votes_best_within_constraints"]:
        reasons.append("ratification contains unsigned/non-true best_within_constraints")
    if not gates["no_reject_votes"]:
        reasons.append("ratification contains reject vote")
    if not gates["agreement_matrix_pass"]:
        reasons.append("agreement matrix missing or below 0.85")
    if gates["unresolved_severity_ge_3_count"]:
        reasons.append("unresolved severity>=3 issues remain")
    if not gates["plan_patch_artifacts_well_formed"]:
        reasons.append("plan patches missing or malformed")
    if not gates["merged_patches_are_list"]:
        reasons.append("merged_plan patches missing or malformed")
    elif not gates["empty_patches_have_no_action_intent"]:
        reasons.append("empty merged patches require planner_patch_summary no_action_certification")

    complete_statuses = {"certified", "certified_with_minor_risks"}
    if not gates["discussion_result_present"]:
        status = "partial_uncertified"
    elif discussion_status not in complete_statuses:
        status = discussion_status or "not_certified"
        reasons.append(f"discussion status is {status}")
    elif reasons:
        status = "not_certified"
    else:
        status = discussion_status

    can_claim = status in complete_statuses and not reasons
    manifest = {
        "schema_version": CERTIFICATION_MANIFEST_SCHEMA_VERSION,
        "generated_at": _utc_now_iso(),
        "tick_dir": tick_dir,
        "status": status,
        "can_claim_complete_certification": can_claim,
        "reasons": reasons,
        "gates": gates,
        "artifacts": {
            "plans": {"count": len(plan_files), "files": [_artifact_entry(p, tick_dir) for p in plan_files]},
            "merged_plan": _artifact_entry(merged_path, tick_dir),
            "discussion_result": _artifact_entry(discussion_path, tick_dir),
            "certification_manifest": {"path": os.path.relpath(final_path, tick_dir), "exists": bool(write or os.path.exists(final_path))},
        },
    }
    if write:
        _write_json_atomic(final_path, manifest)
    return manifest


def _load_tick_plans(tick_dir: str) -> List[dict]:
    plans_dir = os.path.join(os.path.expanduser(tick_dir), "plans")
    loaded = []
    if not os.path.isdir(plans_dir):
        return loaded
    for name in sorted(os.listdir(plans_dir)):
        if not name.endswith(".json"):
            continue
        plan = _read_json_file(os.path.join(plans_dir, name), None)
        if isinstance(plan, dict):
            loaded.append(plan)
    return loaded


def resume_discussion_from_tick_dir(
    tick_dir: str,
    *,
    offline: bool = False,
    max_rounds: int = 5,
    timeout: int = DEFAULT_TIMEOUT,
    force: bool = False,
    call_model_fn=None,
) -> dict:
    """Resume or create a missing discussion_result for an existing tick directory."""
    tick_dir = os.path.abspath(os.path.expanduser(tick_dir))
    discussion_path = os.path.join(tick_dir, "discussion_result.json")
    if os.path.exists(discussion_path) and not force:
        manifest = audit_certification(tick_dir, write=True)
        return {"tick_dir": tick_dir, "resumed": False, "discussion": _read_json_file(discussion_path, {}), "certification_manifest": manifest}

    plans = _load_tick_plans(tick_dir)
    merged = _read_json_file(os.path.join(tick_dir, "merged_plan.json"), {}) or {}
    if not plans:
        discussion = {"status": "not_certified", "reasons": ["no plans available for resume"]}
    else:
        models = [_plan_model(plan, f"model_{i}") for i, plan in enumerate(plans)]
        evidence_bundle = merged.get("evidence_bundle") if isinstance(merged.get("evidence_bundle"), dict) else build_evidence_bundle({})
        merged_truth = merged.get("truth_assessment") if isinstance(merged.get("truth_assessment"), dict) else merged.get("truth_gate") if isinstance(merged.get("truth_gate"), dict) else None
        if call_model_fn is None and not offline:
            config = load_config()
            call_model_fn = lambda model, prompt: call_discussion_model(model, prompt, config, timeout=timeout)
        discussion = run_discussion_rounds(
            plans,
            current_best=merged,
            models=models,
            max_rounds=max_rounds,
            offline=offline,
            call_model_fn=call_model_fn,
            evidence_bundle=evidence_bundle,
            checkpoint_dir=tick_dir,
        )
        discussion["fanout_certification"] = merged.get("fanout_certification", {})
        if isinstance(merged_truth, dict):
            discussion["truth_assessment"] = merged_truth
        else:
            discussion.setdefault("truth_assessment", merged.get("truth_assessment", discussion.get("truth_assessment", {})))
    _write_json_atomic(discussion_path, discussion)
    manifest = audit_certification(tick_dir, write=True)
    return {"tick_dir": tick_dir, "resumed": True, "discussion": discussion, "certification_manifest": manifest}


def run_rmcs_runner(
    root: str = HERMES_HOME,
    *,
    max_ticks: int = 5,
    resume_missing: bool = False,
    offline: bool = True,
    max_rounds: int = 2,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Bounded RMCS runner for cron/background use.

    It performs one finite scan of recent tick dirs and writes a durable last-run
    report. No unbounded loops, no implicit daemonization, and no recursive job
    creation.
    """
    root = os.path.abspath(os.path.expanduser(root))
    max_ticks = max(1, int(max_ticks or 1))
    tick_dirs = []
    if os.path.isdir(root):
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if name.startswith("tick-") and os.path.isdir(path):
                tick_dirs.append(path)
    tick_dirs = sorted(tick_dirs, key=lambda p: os.path.getmtime(p), reverse=True)[:max_ticks]
    status_path = os.path.join(root, "state", "rmcs-runner-status.json")
    _write_json_atomic(status_path, {
        "schema_version": "rmcs_runner_status_v1",
        "updated_at": _utc_now_iso(),
        "status": "running",
        "root": root,
        "max_ticks": max_ticks,
        "processed_count": 0,
        "current_tick": None,
    })
    processed = []
    for tick in tick_dirs:
        _write_json_atomic(status_path, {
            "schema_version": "rmcs_runner_status_v1",
            "updated_at": _utc_now_iso(),
            "status": "running",
            "root": root,
            "max_ticks": max_ticks,
            "processed_count": len(processed),
            "current_tick": tick,
        })
        before = audit_certification(tick, write=True)
        action = "audited"
        result = {"certification_manifest": before}
        if resume_missing and not before.get("gates", {}).get("discussion_result_present", False):
            result = resume_discussion_from_tick_dir(
                tick,
                offline=offline,
                max_rounds=max_rounds,
                timeout=timeout,
                force=False,
            )
            action = "resumed"
        after = result.get("certification_manifest") or audit_certification(tick, write=True)
        processed.append({
            "tick_dir": tick,
            "action": action,
            "status": after.get("status"),
            "can_claim_complete_certification": after.get("can_claim_complete_certification", False),
        })
    report = {
        "schema_version": "rmcs_runner_report_v1",
        "generated_at": _utc_now_iso(),
        "root": root,
        "bounded": {
            "max_ticks": max_ticks,
            "resume_missing": resume_missing,
            "offline": offline,
            "max_rounds": max_rounds,
            "timeout": timeout,
            "processed_count": len(processed),
        },
        "processed": processed,
    }
    _write_json_atomic(os.path.join(root, "state", "rmcs-runner-last.json"), report)
    _write_json_atomic(status_path, {
        "schema_version": "rmcs_runner_status_v1",
        "updated_at": report["generated_at"],
        "status": "complete",
        "root": root,
        "max_ticks": max_ticks,
        "processed_count": len(processed),
        "current_tick": None,
        "last_report": os.path.join(root, "state", "rmcs-runner-last.json"),
    })
    return report


def _load_env_file(path: Optional[str] = None) -> dict:
    """Load simple KEY=VALUE lines without overriding process env."""
    path = path or os.path.join(HERMES_HOME, ".env")
    data = {}
    try:
        with open(os.path.expanduser(path)) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


def call_deepseek_api(prompt: str, model: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Direct DeepSeek adapter used because Hermes CLI may not expose --provider deepseek."""
    import urllib.error
    import urllib.request

    env_file = _load_env_file()
    key = os.environ.get("DEEPSEEK_API_KEY") or env_file.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY missing")
    api_model = os.environ.get("DEEPSEEK_MODEL") or ("deepseek-reasoner" if "reasoner" in model else "deepseek-chat")
    payload = json.dumps({
        "model": api_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1800,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            if model_quota:
                model_quota.record_call(model=model, provider="deepseek", ok=True, headers=dict(resp.headers), usage={})
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        if model_quota:
            model_quota.record_call(model=model, provider="deepseek", ok=False, headers=dict(e.headers or {}), error=detail)
        raise RuntimeError(f"DeepSeek API HTTP {e.code}: {detail}") from e
    data = json.loads(body)
    return data["choices"][0]["message"]["content"]


class ModelRuntimeError(RuntimeError):
    """A provider/adapter failed before producing parseable model content."""

    def __init__(self, message: str, *, raw_response: str = "", status: Any = None):
        super().__init__(message)
        self.raw_response = raw_response or ""
        self.status = status


def _coerce_error_bool(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def _truncate_runtime_error_text(value: Any, limit: int = 500) -> str:
    return redact_evidence_text(value, limit=limit)


def _decode_claude_code_output(stdout: str) -> dict:
    """Decode `claude -p --output-format json` without mistaking API errors for JSON plans.

    Claude Code may return a JSON wrapper even for failures, e.g. returncode!=0 or
    `is_error=true` with `api_error_status=403`. Treat those as runtime/provider
    failures, not planner/discussion parse failures.
    """
    raw = stdout or ""
    decoded = {
        "raw": raw,
        "wrapper": None,
        "result_text": raw,
        "is_error": False,
        "api_error_status": None,
        "detail": "",
    }
    text = raw.strip()
    if not text:
        return decoded
    try:
        wrapped = json.loads(text)
    except json.JSONDecodeError:
        return decoded
    if not isinstance(wrapped, dict):
        return decoded

    wrapper_like = (
        "result" in wrapped
        or "is_error" in wrapped
        or "api_error_status" in wrapped
        or "error" in wrapped
        or "subtype" in wrapped
        or wrapped.get("type") in {"result", "error"}
    )
    if not wrapper_like:
        return decoded

    result = wrapped.get("result")
    if isinstance(result, str):
        result_text = result
    elif result is None:
        result_text = ""
    else:
        result_text = json.dumps(result, ensure_ascii=False)

    api_status = wrapped.get("api_error_status")
    subtype = str(wrapped.get("subtype") or wrapped.get("type") or "").strip().lower()
    is_error = (
        _coerce_error_bool(wrapped.get("is_error"))
        or api_status not in (None, 0, "0", "")
        or subtype.startswith(("error", "failed", "failure"))
        or wrapped.get("type") == "error"
    )
    detail = result_text or wrapped.get("error") or wrapped.get("message") or text
    decoded.update({
        "wrapper": wrapped,
        "result_text": result_text,
        "is_error": is_error,
        "api_error_status": api_status,
        "detail": _truncate_runtime_error_text(detail, 800),
    })
    return decoded


def _claude_code_failure_message(stdout: str, stderr: str, returncode: Optional[int] = None) -> str:
    decoded = _decode_claude_code_output(stdout)
    prefix = "Claude Code"
    if decoded.get("api_error_status") not in (None, 0, "0", ""):
        prefix += f" API error {decoded.get('api_error_status')}"
    elif returncode not in (None, 0):
        prefix += f" CLI exited {returncode}"
    else:
        prefix += " runtime error"
    detail = (stderr or "").strip() or decoded.get("detail") or decoded.get("result_text") or stdout
    return f"{prefix}: {_truncate_runtime_error_text(detail, 500)}"


def call_discussion_model(model: str, prompt: str, config: dict, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Call a model for discussion/challenge/ratification text output."""
    provider = model_provider(config, model)
    if provider == "deepseek":
        return call_deepseek_api(prompt, model, timeout=timeout)
    if "claude" in model.lower() and shutil.which("claude"):
        # Prefer Claude Code CLI for Claude models. It uses the user's working
        # Claude Max/OAuth session and avoids the Hermes Anthropic adapter path
        # that can misroute provider/model fields in some local configs.
        cmd = ["claude", "-p", prompt, "--model", model, "--max-turns", "1", "--output-format", "json"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            message = f"Claude Code CLI timed out after {timeout}s"
            if model_quota:
                model_quota.record_call(model=model, provider="claude-code", ok=False, headers={}, error=message[:500])
            raise ModelRuntimeError(message, raw_response=_truncate_runtime_error_text(getattr(e, "stdout", "") or getattr(e, "stderr", ""), 2000), status="timeout") from e
        except OSError as e:
            message = f"Claude Code CLI invocation failed: {_truncate_runtime_error_text(str(e), 500)}"
            if model_quota:
                model_quota.record_call(model=model, provider="claude-code", ok=False, headers={}, error=message[:500])
            raise ModelRuntimeError(message, status="oserror") from e
        decoded = _decode_claude_code_output(r.stdout)
        if r.returncode != 0 or decoded.get("is_error"):
            message = _claude_code_failure_message(r.stdout, r.stderr, r.returncode)
            if model_quota:
                model_quota.record_call(model=model, provider="claude-code", ok=False, headers={}, error=message[:500])
            raise ModelRuntimeError(message, raw_response=_truncate_runtime_error_text(r.stdout or r.stderr or message, 2000), status=decoded.get("api_error_status"))
        if model_quota:
            model_quota.record_call(model=model, provider="claude-code", ok=True, headers={}, usage={})
        return decoded.get("result_text") or r.stdout
    hermes_bin = shutil.which("hermes") or "hermes"
    cmd = [hermes_bin, "chat", "-q", prompt, "--model", model, "--quiet", "--max-turns", "1", "--source", "multi-brain-discussion", "--ignore-rules"]
    if provider in SUPPORTED_HERMES_PROVIDERS:
        cmd += ["--provider", provider]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        if model_quota:
            model_quota.record_call(model=model, provider=provider or model_quota.provider_for_model(model, config), ok=False, headers={}, error=(r.stderr or r.stdout)[:500])
        raise RuntimeError((r.stderr or r.stdout)[:500])
    if model_quota:
        model_quota.record_call(model=model, provider=provider or model_quota.provider_for_model(model, config), ok=True, headers={}, usage={})
    return r.stdout


def extract_plan_json(raw: str) -> dict:
    """Extract plan JSON from Claude wrapper, fenced JSON, or raw model output."""
    text = (raw or "").strip()
    if not text:
        raise json.JSONDecodeError("empty output", text, 0)

    decoded = _decode_claude_code_output(text)
    if decoded.get("wrapper") is not None:
        if decoded.get("is_error"):
            raise ModelRuntimeError(
                _claude_code_failure_message(text, "", None),
                raw_response=_truncate_runtime_error_text(text, 2000),
                status=decoded.get("api_error_status"),
            )
        text = (decoded.get("result_text") or "").strip()
        if not text:
            raise json.JSONDecodeError("empty Claude Code result", text, 0)

    try:
        outer = json.loads(text)
        if isinstance(outer, dict):
            return outer
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    return json.loads(text)


def normalize_plan(plan: dict, model: str, state_hash: str, tier: str,
                   chain_id: str, provider: str, adapter: str,
                   latency_ms: int) -> dict:
    """Fill required fields so downstream consensus can compare plans safely."""
    if not isinstance(plan, dict):
        raise ValueError("plan is not a JSON object")
    plan.setdefault("meta", {})
    plan["meta"].update({
        "planner_model": model,
        "planner_role": plan["meta"].get("planner_role", "architect"),
        "state_hash": state_hash,
        "tier_target": tier,
        "chain_id": chain_id,
        "provider": provider or "unknown",
        "adapter": adapter,
        "latency_ms": latency_ms,
    })
    plan["meta"]["confidence"] = float(plan["meta"].get("confidence", 0.5))
    plan.setdefault("diagnosis", {"root_cause_class": "no_action", "evidence_field_ids": [], "summary": ""})
    plan.setdefault("patches", [])
    for p in plan["patches"]:
        if not p.get("id"):
            body = "|".join([p.get("target_file", ""), p.get("op", ""), p.get("rationale", "")])
            p["id"] = hashlib.sha1(body.encode()).hexdigest()[:12]
    plan.setdefault("verification", {"expected_metric_delta": {"main_pass_rate": 0.0}, "guard_metrics": ["main_pass_rate"], "tier_eval_plan": "T0_only"})
    plan.setdefault("evidence_requests", [])
    plan.setdefault("rollback_signal", {"auto_rollback_if": "main_pass_rate < pre - 0.05", "kill_switch_inc": False})
    return plan


def call_planner_model(model: str, prompt: str, state_hash: str, tier: str,
                       chain_id: str, config: dict, timeout: int) -> Tuple[dict, dict]:
    """Actually invoke the requested planner model via its best available adapter."""
    hermes_bin = shutil.which("hermes") or "hermes"
    provider = model_provider(config, model)
    if os.environ.get("HERMES_MULTI_BRAIN_OFFLINE") == "1":
        plan = generate_shadow_plan(model, state_hash, tier, chain_id)
        plan["diagnosis"]["summary"] = f"Offline adapter dry-run for {model}"
        return plan, {"ok": True, "adapter": "offline", "provider": provider, "latency_ms": 0}

    # SPL can save tokens, but it must never drop the orchestrator-owned state/evidence.
    # Keep natural prompts by default until the SPL encoder supports full state payloads.
    if _spl_available and os.environ.get("HERMES_MULTI_BRAIN_USE_SPL") == "1":
        try:
            tier_enum = SPLTier[tier] if isinstance(tier, str) else tier
            spl_msg = _spl_encoder.encode_planner_call(
                model=model, state={},
                tier=tier_enum, state_hash=state_hash,
            )
            prompt = json.dumps(spl_msg, ensure_ascii=False)
        except Exception:
            pass  # fall back to original prompt

    adapter = ""
    cmd = []
    if provider == "deepseek":
        adapter = "deepseek-api"
        start = time.time()
        try:
            raw = call_deepseek_api(prompt, model, timeout=timeout)
            latency_ms = int((time.time() - start) * 1000)
            parsed = extract_plan_json(raw)
            plan = normalize_plan(parsed, model, state_hash, tier, chain_id, provider, adapter, latency_ms)
            return plan, {"ok": True, "adapter": adapter, "provider": provider, "latency_ms": latency_ms}
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            plan = generate_shadow_plan(model, state_hash, tier, chain_id)
            plan["meta"]["confidence"] = 0.2
            plan["diagnosis"]["summary"] = f"{model} direct DeepSeek adapter failed: {str(e)[:240]}"
            return plan, {"ok": False, "adapter": adapter, "provider": provider, "error": str(e)[:500], "latency_ms": latency_ms}
    if "claude" in model.lower() and shutil.which("claude"):
        adapter = "claude-code"
        cmd = ["claude", "-p", prompt, "--model", model,
               "--max-turns", "1", "--output-format", "json"]
    elif shutil.which("hermes"):
        adapter = "hermes-chat"
        cmd = [hermes_bin, "chat", "-q", prompt, "--model", model, "--quiet", "--max-turns", "1", "--source", "multi-brain", "--ignore-rules"]
        if provider in SUPPORTED_HERMES_PROVIDERS:
            cmd += ["--provider", provider]

    if not cmd:
        plan = generate_shadow_plan(model, state_hash, tier, chain_id)
        plan["meta"]["confidence"] = 0.2
        plan["diagnosis"]["summary"] = f"No adapter available for {model}"
        return plan, {"ok": False, "adapter": "none", "provider": provider, "error": "no_adapter"}

    start = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        latency_ms = int((time.time() - start) * 1000)
        if adapter == "claude-code":
            decoded = _decode_claude_code_output(r.stdout)
            if r.returncode != 0 or decoded.get("is_error"):
                message = _claude_code_failure_message(r.stdout, r.stderr, r.returncode)
                if model_quota:
                    model_quota.record_call(model=model, provider="claude-code", ok=False, headers={}, error=message[:500])
                plan = generate_shadow_plan(model, state_hash, tier, chain_id)
                plan["meta"]["confidence"] = 0.2
                plan["diagnosis"]["summary"] = f"{model} Claude Code runtime failed: {message[:240]}"
                return plan, {
                    "ok": False,
                    "adapter": adapter,
                    "provider": provider,
                    "exit_code": r.returncode,
                    "api_error_status": decoded.get("api_error_status"),
                    "error": message[:500],
                    "latency_ms": latency_ms,
                }
            raw_stdout = decoded.get("result_text") if decoded.get("wrapper") is not None else r.stdout
        else:
            if r.returncode != 0:
                if model_quota:
                    model_quota.record_call(model=model, provider=provider or model_quota.provider_for_model(model, config), ok=False, headers={}, error=(r.stderr or r.stdout)[:500])
                plan = generate_shadow_plan(model, state_hash, tier, chain_id)
                plan["meta"]["confidence"] = 0.2
                plan["diagnosis"]["summary"] = f"{model} adapter {adapter} failed: {_truncate_runtime_error_text(r.stderr or r.stdout, 240)}"
                return plan, {"ok": False, "adapter": adapter, "provider": provider, "exit_code": r.returncode, "latency_ms": latency_ms, "stderr": _truncate_runtime_error_text(r.stderr, 500)}
            raw_stdout = r.stdout
        parsed = extract_plan_json(raw_stdout)
        plan = normalize_plan(parsed, model, state_hash, tier, chain_id, provider, adapter, latency_ms)
        if model_quota:
            model_quota.record_call(model=model, provider=provider or model_quota.provider_for_model(model, config), ok=True, headers={}, usage={})
        return plan, {"ok": True, "adapter": adapter, "provider": provider, "latency_ms": latency_ms}
    except subprocess.TimeoutExpired:
        if model_quota:
            model_quota.record_call(model=model, provider=provider or model_quota.provider_for_model(model, config), ok=False, headers={}, error=f"timeout after {timeout}s")
        plan = generate_shadow_plan(model, state_hash, tier, chain_id)
        plan["meta"]["confidence"] = 0.2
        plan["diagnosis"]["summary"] = f"{model} timed out after {timeout}s via adapter"
        return plan, {"ok": False, "adapter": adapter, "provider": provider, "timeout_s": timeout}
    except ModelRuntimeError as e:
        message = _truncate_runtime_error_text(str(e), 500)
        if model_quota:
            model_quota.record_call(model=model, provider=provider or model_quota.provider_for_model(model, config), ok=False, headers={}, error=message[:500])
        plan = generate_shadow_plan(model, state_hash, tier, chain_id)
        plan["meta"]["confidence"] = 0.2
        plan["diagnosis"]["summary"] = f"{model} runtime failed: {message[:240]}"
        return plan, {"ok": False, "adapter": adapter, "provider": provider, "api_error_status": getattr(e, "status", None), "error": message[:500]}
    except (json.JSONDecodeError, ValueError, OSError) as e:
        if model_quota:
            model_quota.record_call(model=model, provider=provider or model_quota.provider_for_model(model, config), ok=False, headers={}, error=str(e)[:500])
        plan = generate_shadow_plan(model, state_hash, tier, chain_id)
        plan["meta"]["confidence"] = 0.2
        plan["diagnosis"]["summary"] = f"{model} output parse/invoke failed: {e}"
        return plan, {"ok": False, "adapter": adapter, "provider": provider, "error": str(e)[:500]}


def generate_shadow_plan(model: str, state_hash: str, tier: str, chain_id: str) -> dict:
    """生成 Phase 0 shadow 计划模板"""
    return {
        "meta": {
            "planner_model": model,
            "planner_role": "architect",
            "state_hash": state_hash,
            "tier_target": tier,
            "confidence": 0.8,
            "cost_usd": 0.01,
            "latency_ms": 5000,
            "chain_id": chain_id,
        },
        "diagnosis": {
            "root_cause_class": "no_action",
            "evidence_field_ids": [],
            "summary": f"Phase 0 shadow plan by {model} — no changes proposed"
        },
        "patches": [],
        "verification": {
            "expected_metric_delta": {"main_pass_rate": 0.0},
            "guard_metrics": ["main_pass_rate"],
            "tier_eval_plan": "T0_only"
        },
        "evidence_requests": [],
        "rollback_signal": {
            "auto_rollback_if": "main_pass_rate < pre - 0.10",
            "kill_switch_inc": False
        }
    }


def emit_phase_event(phase: str, chain_id: str, task_id: str,
                     verdict: str, summary: str,
                     extensions: Optional[dict] = None):
    """发射 L2 协议事件"""
    try:
        msg = protocol_wrap(
            agent_id="consult-models",
            task_id=task_id,
            verdict=verdict,
            summary=summary,
            chain_id=chain_id,
            verification_pattern="multi_brain",
            extensions=extensions,
        )
        protocol_emit(msg)
        return msg
    except ProtocolError as e:
        print(f"[consult_models] Protocol emit failed: {e}", file=sys.stderr)
        return None


def run_fanout(
    state_file: str,
    tier: str = "T2",
    quorum_override: Optional[int] = None,
    shadow: bool = False,
    keep_ticks: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    discussion: bool = False,
    max_rounds: int = 5,
) -> dict:
    """
    运行多脑 fan-out。

    Returns:
        {"merged_plan": dict, "chain_id": str, "tick_dir": str, "models_used": [...]}
    """
    cleanup_old_ticks()

    # ── 1. 加载配置 ──
    quorum = load_quorum()
    config = load_config()
    skip_claude = os.environ.get("SKIP_CLAUDE", "0") == "1"

    planners, q_count, min_q = get_tier_planners(quorum, tier, skip_claude)
    if quorum_override:
        q_count = quorum_override

    # 先做额度硬门控，再截取 quorum 数量。unknown/unobservable 允许，exhausted 跳过；
    # later healthy planners can backfill exhausted preferred planners.
    planners, skipped_due_to_quota, quota_snapshot = select_planners_for_fanout(
        planners, q_count, config=config
    )
    quota_confidence = quota_observability_summary(quota_snapshot)
    if not planners:
        print("[consult_models] No planners available after quota gate", file=sys.stderr)
        return {
            "error": "no_planners_after_quota_gate",
            "tier": tier,
            "skipped_due_to_quota": skipped_due_to_quota,
            "quota_snapshot": quota_snapshot,
            "quota_confidence": quota_confidence,
        }

    print(f"[consult_models] Tier={tier} Quorum={q_count} Min={min_q} "
          f"Planners={planners} Shadow={shadow} QuotaSkipped={len(skipped_due_to_quota)}", file=sys.stderr)

    # ── 2. 计算 state_hash ──
    state_hash = compute_state_hash(state_file)
    chain_id = str(uuid.uuid4())

    # ── 3. 创建 TICK_DIR ──
    tick_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tick_dir = os.path.join(HERMES_HOME, f"tick-{tick_id}")
    plans_dir = os.path.join(tick_dir, "plans")
    os.makedirs(plans_dir, exist_ok=True)

    # ── 4. 发射 FANOUT_START 事件 ──
    emit_phase_event("fanout_start", chain_id, f"multi-brain-{tick_id}",
                     "pending", f"Fan-out to {len(planners)} planners: {planners}",
                     {"tier": tier, "quorum": q_count, "planners": planners, "shadow": shadow,
                      "quota_snapshot": quota_snapshot, "quota_confidence": quota_confidence,
                      "skipped_due_to_quota": skipped_due_to_quota})

    # ── 5. 加载 state ──
    with open(state_file) as f:
        state = json.load(f)
    state.setdefault("budget", {})
    state["budget"]["model_quota_snapshot"] = quota_snapshot
    state["budget"]["model_quota_confidence"] = quota_confidence
    state["budget"]["skipped_due_to_quota"] = skipped_due_to_quota
    evidence_bundle = build_evidence_bundle(state)
    truth_gate = evaluate_truth_gate(evidence_bundle)
    state["evidence_bundle"] = evidence_bundle
    state["truth_gate"] = truth_gate
    _write_json_atomic(os.path.join(tick_dir, "state.json"), state)

    # ── 6. Fan-out: 为每个 planner 生成计划 ──
    plan_files = []
    success_count = 0
    fail_count = 0

    for model in planners:
        safe_name = model.replace("/", "_").replace(" ", "_")
        plan_file = os.path.join(plans_dir, f"{safe_name}.json")
        plan_files.append(plan_file)

        print(f"[consult_models] → {model} planning...", file=sys.stderr)

        if shadow:
            # Phase 0: 生成影子模板
            plan = generate_shadow_plan(model, state_hash, tier, chain_id)
            with open(plan_file, "w") as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
            success_count += 1
            emit_phase_event(
                "planner_done", chain_id, f"planner-{safe_name}",
                "pass", f"Shadow plan generated for {model}",
                {"model": model, "shadow": True}
            )
        else:
            # Phase 1+: 通过模型专属 adapter 实际调用，不再用 Claude 冒充所有 planner。
            prompt = build_planner_prompt(state, state_hash, model, tier)
            plan, adapter_info = call_planner_model(
                model=model,
                prompt=prompt,
                state_hash=state_hash,
                tier=tier,
                chain_id=chain_id,
                config=config,
                timeout=timeout,
            )
            with open(plan_file, "w") as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)

            ok = bool(adapter_info.get("ok"))
            if ok:
                success_count += 1
            else:
                fail_count += 1

            verdict = "pass" if ok else (
                "timeout" if "timeout_s" in adapter_info else "fail"
            )
            emit_phase_event(
                "planner_done", chain_id, f"planner-{safe_name}",
                verdict,
                f"{model} plan {'completed' if ok else 'failed'} via {adapter_info.get('adapter')}",
                {"model": model, "shadow": False, "adapter": adapter_info}
            )

    # ── 7. 降级检查 ──
    degradation = quorum.get("degradation", {})
    fanout_status = fanout_certification_status(
        success_count=success_count,
        planner_count=len(planners),
        min_quorum=min_q,
        fail_count=fail_count,
    )
    fanout_ok, fanout_errors = validate_fanout_certification_status(fanout_status)
    if not fanout_ok:
        print(f"[consult_models] Invalid fanout certification: {fanout_errors}", file=sys.stderr)
        fanout_status["status"] = "degraded_not_certified"
        fanout_status["certified"] = False
        fanout_status["multi_model_certified"] = False
        fanout_status["reason"] = "invalid fanout certification schema: " + "; ".join(fanout_errors)
    if fail_count >= len(planners):
        print("[consult_models] All planners failed — skip_tick", file=sys.stderr)
        emit_phase_event("fanout_end", chain_id, f"multi-brain-{tick_id}",
                         "fail", "All planners failed",
                         {"success": success_count, "fail": fail_count,
                          "fanout_certification": fanout_status,
                          "quota_confidence": quota_confidence})
        return {"error": "all_failed", "tick_dir": tick_dir, "chain_id": chain_id,
                "fanout_certification": fanout_status, "quota_confidence": quota_confidence}
    elif fail_count >= len(planners) - min_q + 1:
        print(f"[consult_models] Below min_quorum ({min_q}) — solo_plan_low_risk", file=sys.stderr)
        emit_phase_event("fanout_end", chain_id, f"multi-brain-{tick_id}",
                         "partial", f"Below min_quorum ({success_count}/{len(planners)})",
                         {"success": success_count, "fail": fail_count,
                          "fanout_certification": fanout_status,
                          "quota_confidence": quota_confidence})

    # ── 8. Consensus ──
    print(f"[consult_models] Running consensus on {len(plan_files)} plans...", file=sys.stderr)
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "consensus-plans.py"),
             "merge"] + plan_files,
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            merged = json.loads(r.stdout)
        else:
            merged = {"error": "consensus_failed", "detail": r.stderr[:500]}
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        merged = {"error": "consensus_error", "detail": str(e)}

    merged_file = os.path.join(tick_dir, "merged_plan.json")
    merged["quota_snapshot"] = quota_snapshot
    merged["quota_confidence"] = quota_confidence
    merged["skipped_due_to_quota"] = skipped_due_to_quota
    merged["fanout_certification"] = fanout_status
    loaded_plan_summaries = []
    for pf in plan_files:
        try:
            with open(pf) as f:
                loaded_plan_summaries.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    merged["planner_patch_summary"] = _planner_patch_summary(loaded_plan_summaries)
    merged["evidence_bundle"] = evidence_bundle
    merged["truth_assessment"] = truth_gate
    if not truth_gate.get("can_certify_truth", True):
        merged["certification_status"] = "truth_not_certified"
        merged.setdefault("degradation_reasons", []).extend(truth_gate.get("reasons", []))
    if fanout_status.get("below_min_quorum"):
        merged["certification_status"] = "degraded_not_certified"
        merged.setdefault("degradation_reasons", []).append(
            f"planner fan-out below min_quorum: {success_count}/{min_q}"
        )
    with open(merged_file, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    discussion_result = None
    if discussion:
        loaded_plans = []
        for pf in plan_files:
            try:
                with open(pf) as f:
                    loaded_plans.append(json.load(f))
            except (OSError, json.JSONDecodeError) as e:
                print(f"[consult_models] WARN: failed to load plan for discussion {pf}: {e}", file=sys.stderr)
        if loaded_plans:
            discussion_result = run_discussion_rounds(
                loaded_plans,
                current_best=merged,
                models=planners,
                max_rounds=max_rounds,
                offline=shadow or os.environ.get("HERMES_MULTI_BRAIN_OFFLINE") == "1",
                call_model_fn=(lambda model, prompt: call_discussion_model(model, prompt, config, timeout=timeout)),
                evidence_bundle=evidence_bundle,
                checkpoint_dir=tick_dir,
            )
        else:
            discussion_result = {"status": "not_certified", "reasons": ["no plans available for discussion"]}
        discussion_result["quota_snapshot"] = quota_snapshot
        discussion_result["quota_confidence"] = quota_confidence
        discussion_result["skipped_due_to_quota"] = skipped_due_to_quota
        discussion_result["fanout_certification"] = fanout_status
        discussion_result.setdefault("evidence_bundle", evidence_bundle)
        discussion_result.setdefault("truth_assessment", truth_gate)
        discussion_result.setdefault("evidence_requests", collect_evidence_requests(loaded_plans))
        if fanout_status.get("below_min_quorum"):
            discussion_result["status"] = "degraded_not_certified"
            discussion_result.setdefault("reasons", []).append(
                f"planner fan-out below min_quorum: {success_count}/{min_q}"
            )
        discussion_file = os.path.join(tick_dir, "discussion_result.json")
        with open(discussion_file, "w") as f:
            json.dump(discussion_result, f, indent=2, ensure_ascii=False)
        certification_manifest = audit_certification(tick_dir, write=True)
        merged["discussion"] = {
            "status": discussion_result.get("status"),
            "result_file": discussion_file,
            "rounds_used": discussion_result.get("rounds_used"),
            "models_consulted": discussion_result.get("models_consulted", []),
            "certification_manifest": os.path.join(tick_dir, "final", "certification_manifest.json"),
            "can_claim_complete_certification": certification_manifest.get("can_claim_complete_certification", False),
        }
        _write_json_atomic(merged_file, merged)

    # ── 9. 发射 FANOUT_END 事件 ──
    emit_phase_event("fanout_end", chain_id, f"multi-brain-{tick_id}",
                     "pass" if fanout_status.get("certified") and truth_gate.get("can_certify_truth", True) and "error" not in merged else "partial",
                     f"Consensus done — {success_count}/{len(planners)} planners succeeded" + 
                     (f" (degraded: {fail_count} failed)" if fail_count else ""),
                     {"success": success_count, "fail": fail_count,
                      "merged_file": merged_file, "tick_dir": tick_dir,
                      "fanout_certification": fanout_status,
                      "quota_confidence": quota_confidence,
                      "truth_assessment": truth_gate})

    # ── 10. 清理 (除非 --keep) ──
    if not keep_ticks:
        # 仅保留 merged_plan.json + plans/
        pass  # 保留 24h 内清理

    print(f"[consult_models] Done. Chain={chain_id} Artifacts in {tick_dir}/",
          file=sys.stderr)

    return {
        "merged_plan": merged,
        "chain_id": chain_id,
        "tick_dir": tick_dir,
        "plans_dir": plans_dir,
        "models_used": planners,
        "success_count": success_count,
        "fail_count": fail_count,
        "shadow": shadow,
        "discussion": discussion_result,
        "fanout_certification": fanout_status,
        "quota_snapshot": quota_snapshot,
        "quota_confidence": quota_confidence,
        "skipped_due_to_quota": skipped_due_to_quota,
        "evidence_bundle": evidence_bundle,
        "truth_assessment": truth_gate,
    }


def cli():
    parser = argparse.ArgumentParser(
        description="consult_models.py — 多脑 fan-out 编排器 v3"
    )
    sub = parser.add_subparsers(dest="cmd")

    # ── run ──
    run_p = sub.add_parser("run", help="Run multi-brain fan-out")
    run_p.add_argument("state_file", help="Path to state.json")
    run_p.add_argument("--tier", default="T2", help="Task tier (T0-T3)")
    run_p.add_argument("--quorum", type=int, default=None,
                       help="Override quorum count")
    run_p.add_argument("--shadow", action="store_true",
                       help="Phase 0 shadow mode (generate templates only)")
    run_p.add_argument("--keep", action="store_true",
                       help="Keep TICK_DIR after completion")
    run_p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                       help=f"Per-planner timeout in seconds (default: {DEFAULT_TIMEOUT})")
    run_p.add_argument("--discussion", action="store_true",
                       help="Run true multi-model discussion/ratification after fan-out")
    run_p.add_argument("--max-rounds", type=int, default=5,
                       help="Max discussion rounds before not_certified/certified_with_minor_risks")

    # ── state ──
    state_p = sub.add_parser("state", help="Create orchestrator-owned state.json from CLI inputs")
    state_p.add_argument("question", help="Problem/question for multi-model discussion")
    state_p.add_argument("--context-json", default="{}", help="JSON object with factual context")
    state_p.add_argument("--constraint", action="append", default=[], help="Constraint (repeatable)")
    state_p.add_argument("--accept", action="append", default=[], help="Acceptance criterion (repeatable)")
    state_p.add_argument("--file", action="append", default=[], help="Implementation target file (repeatable)")
    state_p.add_argument("--verify", action="append", default=[], help="Verification command (repeatable)")
    state_p.add_argument("--claim", action="append", default=[], help="Factual claim requiring evidence before truth certification; use id:text or plain text")
    state_p.add_argument("--evidence-json", action="append", default=[], help="JSON evidence object supporting/contradicting claims (repeatable)")
    state_p.add_argument("--out", default="", help="Write state JSON to this path instead of stdout")

    # ── status ──
    status_p = sub.add_parser("status", help="Show current quorum.yaml configuration")
    status_p.add_argument("--quota", action="store_true", help="Include current model quota snapshot")

    # ── deterministic analysis selfcheck ──
    selfcheck_p = sub.add_parser("selfcheck", help="Run deterministic multi-model analysis self-check (no model calls)")
    selfcheck_p.add_argument("--json", action="store_true", help="Emit full JSON report")
    selfcheck_p.add_argument("--no-temp-audit", action="store_true", help="Skip temporary RMCS certification fixture audit")

    # ── evidence request fulfillment ──
    fulfill_p = sub.add_parser("fulfill-evidence", help="Execute allowlisted read-only evidence_requests and optionally update state.json")
    fulfill_p.add_argument("--state-file", default="", help="State JSON to update/use for verify-command allowlist; defaults to <tick>/state.json when --tick-dir is set")
    fulfill_p.add_argument("--tick-dir", default="", help="Read evidence_requests from discussion/merged/plans in a tick dir")
    fulfill_p.add_argument("--requests-file", default="", help="JSON file containing evidence_requests or one request object")
    fulfill_p.add_argument("--request-json", action="append", default=[], help="Inline evidence request JSON object (repeatable)")
    fulfill_p.add_argument("--out-state", default="", help="Write updated state JSON with fulfilled evidence")
    fulfill_p.add_argument("--out-report", default="", help="Write fulfillment report JSON")
    fulfill_p.add_argument("--cwd", default=HERMES_HOME, help="Working directory for approved commands")
    fulfill_p.add_argument("--timeout", type=int, default=30, help="Per-command timeout in seconds")
    fulfill_p.add_argument("--max-requests", type=int, default=20, help="Maximum evidence requests to process")
    fulfill_p.add_argument("--dry-run", action="store_true", help="Classify/approve requests without executing")

    # ── cleanup ──
    sub.add_parser("cleanup", help="Clean all old TICK_DIRs")

    # ── RMCS audit/resume ──
    audit_p = sub.add_parser("audit-certification", help="Audit a tick dir and write final/certification_manifest.json")
    audit_p.add_argument("tick_dir", help="Existing ~/.hermes/tick-* directory")
    audit_p.add_argument("--no-write", action="store_true", help="Only print manifest; do not write final artifact")

    resume_p = sub.add_parser("resume-discussion", help="Resume/create discussion_result.json for an existing tick dir")
    resume_p.add_argument("tick_dir", help="Existing ~/.hermes/tick-* directory")
    resume_p.add_argument("--offline", action="store_true", help="Use deterministic offline ratification instead of model calls")
    resume_p.add_argument("--max-rounds", type=int, default=5, help="Max discussion rounds")
    resume_p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-model timeout in seconds")
    resume_p.add_argument("--force", action="store_true", help="Recreate discussion_result even if it already exists")

    discuss_existing_p = sub.add_parser("discuss-existing", help="Alias for resume-discussion")
    discuss_existing_p.add_argument("tick_dir", help="Existing ~/.hermes/tick-* directory")
    discuss_existing_p.add_argument("--offline", action="store_true", help="Use deterministic offline ratification instead of model calls")
    discuss_existing_p.add_argument("--max-rounds", type=int, default=5, help="Max discussion rounds")
    discuss_existing_p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-model timeout in seconds")
    discuss_existing_p.add_argument("--force", action="store_true", help="Recreate discussion_result even if it already exists")

    rmcs_runner_p = sub.add_parser("rmcs-runner", help="Bounded RMCS audit/resume scan for cron/background use")
    rmcs_runner_p.add_argument("--root", default=HERMES_HOME, help="Root containing tick-* dirs")
    rmcs_runner_p.add_argument("--max-ticks", type=int, default=5, help="Max tick dirs to process in this finite run")
    rmcs_runner_p.add_argument("--resume-missing", action="store_true", help="Create missing discussion_result.json via resume-discussion")
    rmcs_runner_p.add_argument("--offline", action="store_true", help="Use deterministic offline ratification for resumed ticks")
    rmcs_runner_p.add_argument("--max-rounds", type=int, default=2, help="Max discussion rounds for resumed ticks")
    rmcs_runner_p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-model timeout in seconds")

    args = parser.parse_args()

    if args.cmd == "run":
        if not os.path.isfile(args.state_file):
            print(f"Error: not a file: {args.state_file}", file=sys.stderr)
            sys.exit(1)

        result = run_fanout(
            state_file=args.state_file,
            tier=args.tier,
            quorum_override=args.quorum,
            shadow=args.shadow,
            keep_ticks=args.keep,
            timeout=args.timeout,
            discussion=args.discussion,
            max_rounds=args.max_rounds,
        )

        # 输出 merged_plan
        if "merged_plan" in result:
            print(json.dumps(result["merged_plan"], indent=2, ensure_ascii=False))
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)

    elif args.cmd == "state":
        try:
            context = json.loads(args.context_json)
            if not isinstance(context, dict):
                raise ValueError("--context-json must be a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error: invalid --context-json: {e}", file=sys.stderr)
            sys.exit(2)
        claims = []
        for i, raw_claim in enumerate(args.claim or [], start=1):
            if ":" in raw_claim and raw_claim.split(":", 1)[0].strip().startswith("C-"):
                cid, text = raw_claim.split(":", 1)
                claims.append({"id": cid.strip(), "text": text.strip(), "severity": 3})
            else:
                claims.append({"id": f"C-{i:03d}", "text": raw_claim, "severity": 3})
        evidence = []
        for raw_ev in args.evidence_json or []:
            try:
                ev = json.loads(raw_ev)
                if not isinstance(ev, dict):
                    raise ValueError("evidence JSON must be an object")
                evidence.append(ev)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error: invalid --evidence-json: {e}", file=sys.stderr)
                sys.exit(2)
        state = build_state(
            question=args.question,
            context=context,
            constraints=args.constraint,
            acceptance_criteria=args.accept,
            claims=claims,
            evidence=evidence,
            implementation_target={
                "files": args.file,
                "verify_commands": args.verify,
                "forbidden_changes": [],
            },
        )
        rendered = json.dumps(state, indent=2, ensure_ascii=False)
        if args.out:
            with open(args.out, "w") as f:
                f.write(rendered + "\n")
            print(args.out)
        else:
            print(rendered)

    elif args.cmd == "status":
        quorum = load_quorum()
        mb = quorum.get("multi_brain", {})
        tiers = quorum.get("tiers", {})
        offline = os.environ.get("HERMES_MULTI_BRAIN_OFFLINE") == "1"
        mode_label = "OFFLINE (dry-run, adapter only)" if offline else "ACTUAL (real model calls)"
        print(f"Mode:    {mode_label}")
        print(f"Phase:   {mb.get('phase', '?')}")
        print(f"Enabled: {mb.get('enabled', False)}")
        print(f"Shadow:  {mb.get('shadow_mode', True)}")
        print(f"Default arbiter: {mb.get('default_arbiter', '<none>')}")
        # Probe planner availability (best effort)
        avail_snapshot = {}
        snap_path = os.path.expanduser("~/.hermes/state/provider_availability.json")
        if os.path.exists(snap_path):
            try:
                with open(snap_path) as f:
                    avail_snapshot = json.load(f) or {}
            except Exception:
                avail_snapshot = {}
        for t_name in ["T0", "T1", "T2", "T3"]:
            t = tiers.get(t_name, {})
            planners = t.get("planners", [])
            skipped = []
            try:
                config = load_config()
                for m in planners:
                    p = model_provider(config, m)
                    key = f"{p}::{m}"
                    if avail_snapshot.get(key, {}).get("status") == "unavailable":
                        skipped.append(m)
            except Exception:
                pass
            extra = f" skipped={skipped}" if skipped else ""
            print(f"  {t_name}: quorum={t.get('quorum','?')} "
                  f"min={t.get('min_quorum','?')} "
                  f"arbiter={t.get('arbiter') or mb.get('default_arbiter') or '<none>'} "
                  f"planners={planners}{extra}")
        if getattr(args, "quota", False):
            print("\nQuota snapshot:")
            if model_quota:
                all_planners = []
                for t in tiers.values():
                    for m in t.get("planners", []) or []:
                        if m not in all_planners:
                            all_planners.append(m)
                snapshots = model_quota.snapshot_models(all_planners, config=load_config()) if all_planners else model_quota.load_state()
                print(model_quota.render_table(snapshots))
            else:
                print("  model_quota unavailable")

    elif args.cmd == "selfcheck":
        report = run_analysis_selfcheck(include_temp_audit=not args.no_temp_audit)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            summary = report.get("summary", {})
            print(f"multi-model analysis selfcheck: {report.get('status')} "
                  f"passed={summary.get('passed', 0)} failed={summary.get('failed', 0)} warnings={summary.get('warnings', 0)}")
            for check in report.get("checks", []):
                if not check.get("ok"):
                    print(f"  [{check.get('severity', 'error')}] {check.get('category')}.{check.get('name')}: {check.get('detail')}")
        if report.get("status") != "PASS":
            sys.exit(2)

    elif args.cmd == "fulfill-evidence":
        state_file = args.state_file
        if not state_file and args.tick_dir:
            candidate = os.path.join(os.path.expanduser(args.tick_dir), "state.json")
            if os.path.exists(candidate):
                state_file = candidate
        state = _read_json_file(state_file, default={}) if state_file else {}
        if state_file and not isinstance(state, dict):
            print(f"Error: invalid state JSON object: {state_file}", file=sys.stderr)
            sys.exit(2)
        requests: List[dict] = []
        if args.tick_dir:
            requests.extend(load_evidence_requests_from_tick(args.tick_dir))
        if args.requests_file:
            requests.extend(load_evidence_requests_from_file(args.requests_file))
        for raw_req in args.request_json or []:
            try:
                req = json.loads(raw_req)
                if not isinstance(req, dict):
                    raise ValueError("request JSON must be an object")
                requests.extend(collect_evidence_requests([{"meta": {"planner_model": "inline"}, "evidence_requests": [req]}]))
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error: invalid --request-json: {e}", file=sys.stderr)
                sys.exit(2)
        if not requests and isinstance(state, dict):
            requests.extend(collect_evidence_requests([state]))
        report = fulfill_evidence_requests(
            requests,
            state=state,
            cwd=args.cwd,
            timeout=args.timeout,
            max_requests=args.max_requests,
            dry_run=args.dry_run,
        )
        if args.out_report:
            _write_json_atomic(args.out_report, report)
        if args.out_state:
            if not isinstance(state, dict):
                print("Error: --out-state requires a valid state object", file=sys.stderr)
                sys.exit(2)
            updated = update_state_with_fulfilled_evidence(state, report)
            _write_json_atomic(args.out_state, updated)
            report["updated_state_file"] = os.path.abspath(os.path.expanduser(args.out_state))
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report.get("rejected_count", 0) or report.get("failed_count", 0):
            sys.exit(2)

    elif args.cmd == "cleanup":
        cleanup_old_ticks()
        print("[consult_models] Cleanup complete.")

    elif args.cmd == "audit-certification":
        manifest = audit_certification(args.tick_dir, write=not args.no_write)
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        if not manifest.get("can_claim_complete_certification", False):
            sys.exit(2)

    elif args.cmd in ("resume-discussion", "discuss-existing"):
        result = resume_discussion_from_tick_dir(
            args.tick_dir,
            offline=args.offline,
            max_rounds=args.max_rounds,
            timeout=args.timeout,
            force=args.force,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if not result.get("certification_manifest", {}).get("can_claim_complete_certification", False):
            sys.exit(2)

    elif args.cmd == "rmcs-runner":
        report = run_rmcs_runner(
            args.root,
            max_ticks=args.max_ticks,
            resume_missing=args.resume_missing,
            offline=args.offline,
            max_rounds=args.max_rounds,
            timeout=args.timeout,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
