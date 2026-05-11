#!/usr/bin/env python3
"""
model-router.py — ε-greedy 模型选择器 (L1, v2: cost-aware)
基于 route_outcomes 的 model_stats + pricing.py 的时间感知成本自动选择最优模型

用法:
  python3 model-router.py select --task-class feature.frontend
  python3 model-router.py select --task-tier codegen --task-class bugfix
  python3 model-router.py select-pair --task-tier codegen  # 返回 (producer, reviewer)
  python3 model-router.py status

v2 新增: 时间感知评分 (pricing.py), task_tier 过滤, select_pair 配对, MiMo 候补
"""

import argparse
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import subprocess
import yaml

# 延迟导入
_pricing = None

HERMES_HOME = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))
LOG_FILE = os.path.join(HERMES_HOME, "logs", "model-routing.jsonl")
STICKY_FILE = os.path.join(HERMES_HOME, "state", "model-router-sticky.json")
CONFIG_PATH = os.path.join(HERMES_HOME, "config.yaml")

try:
    for _path in (os.path.join(HERMES_HOME, "scripts"), os.path.dirname(os.path.abspath(__file__))):
        if _path and _path not in sys.path:
            sys.path.insert(0, _path)
    import model_quota
except Exception:
    model_quota = None


def _get_pricing():
    global _pricing
    if _pricing is None:
        try:
            sys.path.insert(0, os.path.join(HERMES_HOME, "scripts"))
            from pricing import load_pricing
            _pricing = load_pricing(CONFIG_PATH)
        except (ImportError, AttributeError, yaml.YAMLError, OSError):
            pass
    return _pricing




# Known provider -> env var mapping for availability check
_PROVIDER_ENV = {
    "openai-codex": "OPENAI_API_KEY",  # or OAuth session
    "anthropic": "ANTHROPIC_API_KEY",
    "xiaomi": "XIAOMI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}

def _model_available(model: str, config: Optional[dict] = None, log_unavailable: bool = True) -> bool:
    """Check if a model's provider likely has credentials configured.
    Returns True if: (a) no env var known, (b) env var set, (c) OAuth-based provider.
    Returns False when a known provider's required auth is explicitly empty/unset.
    """
    provider = _provider_for_model(model, config=config) if config else ""
    if not provider:
        pt = _get_pricing()
        if not pt:
            return True  # can't check and no config provider, assume available
        provider = pt.get_provider(model)
    if not provider:
        return True  # no provider info, assume available
    # OAuth-based providers are always considered available (session-based auth)
    if provider in ("openai-codex", "nous", "qwen-oauth"):
        return True
    env_var = _PROVIDER_ENV.get(provider)
    if not env_var:
        return True  # unknown provider, assume available
    # Check: (1) shell env, (2) .env file, (3) hermes auth store
    available = bool(os.environ.get(env_var))
    if not available:
        # Check .env file (hermes loads these at startup)
        env_file = os.path.join(HERMES_HOME, ".env")
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#"):
                        continue
                    if "=" in line:
                        key = line.split("=", 1)[0].strip()
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if key == env_var and val and val != "***":
                            available = True
                            break
        except OSError:
            pass
    if not available and provider == "anthropic":
        # Claude CLI has its own auth (device code / session)
        import shutil
        available = shutil.which("claude") is not None
    if not available and log_unavailable:
        _log_unavailable_provider(provider, model, env_var)
    return available


def _log_unavailable_provider(provider: str, model: str, env_var: str):
    """Log unavailable provider with deduplication.

    Maintains state/provider_availability.json as the current snapshot keyed by
    (provider, model). Appends to state/unavailable_providers.jsonl ONLY on
    state transition (first time seen, or reason change). Avoids per-call
    explosion when _model_available is invoked many times per routing decision.
    """
    state_dir = os.path.join(HERMES_HOME, "state")
    snapshot_path = os.path.join(state_dir, "provider_availability.json")
    manifest_path = os.path.join(state_dir, "unavailable_providers.jsonl")
    try:
        os.makedirs(state_dir, exist_ok=True)
        # load snapshot
        snapshot = {}
        if os.path.exists(snapshot_path):
            try:
                with open(snapshot_path) as f:
                    snapshot = json.load(f) or {}
            except (json.JSONDecodeError, OSError):
                snapshot = {}

        key = f"{provider}::{model}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        prev = snapshot.get(key, {})
        is_new = not prev or prev.get("status") != "unavailable"
        snapshot[key] = {
            "provider": provider,
            "model": model,
            "missing_env": env_var,
            "status": "unavailable",
            "first_seen": prev.get("first_seen", now),
            "last_seen": now,
            "count": prev.get("count", 0) + 1,
            "last_reason": "missing_env_var",
        }
        # atomic write of snapshot
        tmp = snapshot_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(snapshot, f, indent=2)
        os.replace(tmp, snapshot_path)

        # only append to jsonl on state transition
        if is_new:
            entry = {
                "ts": now,
                "provider": provider,
                "model": model,
                "missing_env": env_var,
                "transition": "available_or_unknown -> unavailable",
                "action": "filtered_from_candidates",
            }
            with open(manifest_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # non-critical, don't fail routing


def probe_all_providers(verbose: bool = False) -> dict:
    """Probe every model in pricing.models and report availability state.

    Returns: {"available": [...], "unavailable": [{model,provider,reason}]}.
    Side effect: refreshes state/provider_availability.json snapshot.
    """
    pt = _get_pricing()
    if not pt:
        return {"error": "pricing table not loadable", "available": [], "unavailable": []}
    available, unavailable = [], []
    for model, info in pt.models.items():
        provider = info.get("provider", "")
        env_var = _PROVIDER_ENV.get(provider)
        ok = _model_available(model)
        entry = {"model": model, "provider": provider, "env_var": env_var}
        if ok:
            available.append(entry)
        else:
            entry["reason"] = f"missing {env_var or 'auth'}"
            unavailable.append(entry)
    # Mark previously-unavailable models that are now available as transitioned
    snapshot_path = os.path.join(HERMES_HOME, "state", "provider_availability.json")
    if os.path.exists(snapshot_path):
        try:
            with open(snapshot_path) as f:
                snap = json.load(f) or {}
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for a in available:
                key = f"{a['provider']}::{a['model']}"
                if key in snap and snap[key].get("status") == "unavailable":
                    snap[key]["status"] = "available"
                    snap[key]["recovered_at"] = now
                    # log transition
                    manifest = os.path.join(HERMES_HOME, "state", "unavailable_providers.jsonl")
                    with open(manifest, "a") as f:
                        f.write(json.dumps({
                            "ts": now, "provider": a["provider"], "model": a["model"],
                            "transition": "unavailable -> available", "action": "recovered",
                        }) + "\n")
            tmp = snapshot_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(snap, f, indent=2)
            os.replace(tmp, snapshot_path)
        except (json.JSONDecodeError, OSError):
            pass

    return {"available": available, "unavailable": unavailable}


def load_config():
    try:
        import yaml
    except ImportError:
        return None

    try:
        with open(CONFIG_PATH) as f:
            c = yaml.safe_load(f)
        routing = c.get("smart_model_routing", {})
        pt = _get_pricing()
        
        # 从 pricing 加载候选模型 (优先于 smart_model_routing 的静态列表)
        if pt:
            candidates = pt.get_candidate_models("codegen")  # 默认 codegen tier
        else:
            candidates = routing.get("candidate_models", [])
        
        return {
            "enabled": routing.get("enabled", False),
            "candidate_models": candidates,
            "epsilon": routing.get("epsilon", 0.1),
            "min_traces_per_model": routing.get("min_traces_per_model", 10),
            "default_model": c.get("model", {}).get("default", ""),
            "pricing": c.get("pricing", {}),
        }
    except (yaml.YAMLError, FileNotFoundError, OSError):
        return None


def get_model_stats(task_class=None, since_hours=168):
    import subprocess
    store_path = os.path.join(HERMES_HOME, "scripts", "route_store.py")
    args = [sys.executable, store_path, "model-stats", "--hours", str(since_hours)]
    if task_class:
        args += ["--task-class", task_class]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return []


def _effective_cost(model_name: str, tokens_est: int = 2000, now_utc=None) -> float:
    """时间感知的有效成本估算"""
    pt = _get_pricing()
    if pt is None:
        return 0.0
    return pt.estimate_cost(model_name, tokens_est, tokens_est // 2, now_utc)


def _schedule_label(model_name: str, now_utc=None) -> str:
    pt = _get_pricing()
    if pt is None:
        return "unknown"
    _, _, label = pt.effective_rate(model_name, now_utc)
    return label


def _provider_for_model(model_name: str, config: Optional[dict] = None) -> str:
    if config:
        provider = (
            config.get("pricing", {})
            .get("models", {})
            .get(model_name, {})
            .get("provider")
        )
        if provider:
            return provider
    pt = _get_pricing()
    if pt is not None:
        provider = pt.get_provider(model_name)
        if provider and provider != "unknown":
            return provider
    if model_quota:
        return model_quota.provider_for_model(model_name)
    return "unknown"


def _quota_filter_candidates(candidates: List[str], config: Optional[dict] = None) -> Tuple[List[str], List[str], dict]:
    """Hard-gate explicitly exhausted quota candidates.

    Unknown/unobservable snapshots stay eligible; only status=exhausted is skipped.
    """
    if not candidates:
        return candidates, [], {}
    if not model_quota:
        return [], list(candidates), {
            "__quota_gate__": {
                "status": "unavailable",
                "reason": "model_quota_import_failed",
                "models": list(candidates),
            }
        }
    providers = {m: _provider_for_model(m, config=config) for m in candidates}
    snapshots = model_quota.snapshot_models(candidates, config=config, providers=providers)
    allowed, skipped = model_quota.gate_models(candidates, snapshots, providers=providers)
    exhausted = [s.get("model") for s in skipped]
    return allowed, exhausted, snapshots


def _required_capabilities(task_tier: str, task_class: Optional[str] = None) -> set:
    text = f"{task_tier or ''} {task_class or ''}".lower()
    if any(word in text for word in ("code", "codegen", "bug", "bugfix", "test", "reviewer", "review")):
        return {"code", "codegen", "tool_calling"}
    if any(word in text for word in ("reason", "arbiter", "p10", "architecture")):
        return {"reasoning", "analysis"}
    if "long" in text or "context" in text:
        return {"long_context"}
    if "chat" in text:
        return {"chat"}
    return set()


def _model_declared_capabilities(model: str, config: Optional[dict] = None) -> set:
    info: Dict[str, Any] = {}
    pt = _get_pricing()
    if pt is not None:
        info.update(getattr(pt, "models", {}).get(model, {}) or {})
    if config:
        info.update(((config.get("pricing") or {}).get("models") or {}).get(model, {}) or {})
    caps = set()
    for key in ("capabilities", "strengths", "candidate_groups"):
        values = info.get(key) or []
        if isinstance(values, str):
            values = [values]
        caps.update(str(v).lower() for v in values if v)
    return caps


def _capability_filter_candidates(
    candidates: List[str],
    task_tier: str,
    task_class: Optional[str],
    config: Optional[dict],
) -> Tuple[List[str], List[str]]:
    required = _required_capabilities(task_tier, task_class)
    if not required:
        return candidates, []
    compatible: List[str] = []
    skipped: List[str] = []
    for model in candidates:
        caps = _model_declared_capabilities(model, config=config)
        if not caps or caps.intersection(required):
            compatible.append(model)
        else:
            skipped.append(model)
    if compatible:
        return compatible, skipped
    return [], skipped


def _sticky_scope(sticky_key: str, task_class: Optional[str], task_tier: str) -> str:
    return f"{task_tier or ''}::{task_class or ''}::{sticky_key}"


def _load_sticky() -> Dict[str, Any]:
    try:
        with open(STICKY_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _remember_sticky(sticky_key: Optional[str], task_class: Optional[str], task_tier: str, model: Optional[str]) -> None:
    if not sticky_key or not model:
        return
    try:
        os.makedirs(os.path.dirname(STICKY_FILE), exist_ok=True)
        data = _load_sticky()
        data[_sticky_scope(sticky_key, task_class, task_tier)] = {
            "model": model,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        tmp = STICKY_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, STICKY_FILE)
    except OSError:
        pass


def _sticky_candidate(sticky_key: Optional[str], task_class: Optional[str], task_tier: str, candidates: List[str]) -> Optional[str]:
    if not sticky_key:
        return None
    record = _load_sticky().get(_sticky_scope(sticky_key, task_class, task_tier), {})
    model = record.get("model") if isinstance(record, dict) else None
    return model if model in candidates else None


def select_model(
    task_class=None,
    task_tier="codegen",
    epsilon=None,
    config=None,
    now_utc=None,
    candidate_override: Optional[List[str]] = None,
    sticky_key: Optional[str] = None,
) -> dict:
    """ε-greedy 选择一个模型 (v2: cost-aware)
    
    新增:
    - task_tier: 从 pricing.candidate_groups 过滤候选
    - now_utc: 时间感知成本 (off-peak/peak/free)
    - 评分: pass_rate - λ_cost * effective_cost - λ_time * avg_dur
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    if config is None:
        config = load_config()
    if config is None:
        return {"model": None, "reason": "config_load_failed"}

    if not config["enabled"]:
        return {"model": config["default_model"], "reason": "routing_disabled"}

    # 按 tier 过滤候选；select_pair 可传入 candidate_override 保证 reviewer 不会退回 producer/provider。
    pt = _get_pricing()
    if candidate_override is not None:
        candidates = candidate_override
    elif pt:
        candidates = pt.get_candidate_models(task_tier)
        if not candidates:
            candidates = config.get("candidate_models", [])
    else:
        candidates = config.get("candidate_models", [])

    # Filter out models with unavailable providers, then hard-gate explicit quota exhaustion.
    available_candidates = [m for m in candidates if _model_available(m, config=config)]
    unavailable = [m for m in candidates if not _model_available(m, config=config)]
    if candidates and not available_candidates:
        return {
            "model": None,
            "reason": "no_available_providers",
            "epsilon_used": epsilon if epsilon is not None else config.get("epsilon", 0),
            "candidates": [],
            "unavailable_candidates": unavailable,
            "quota_exhausted_candidates": [],
            "capability_skipped_candidates": [],
            "quota_snapshot": {},
            "task_tier": task_tier,
            "schedule_label": "unknown",
            "effective_cost_est": 0,
            "model_scores": {},
        }
    candidates = available_candidates
    quota_allowed, quota_exhausted, quota_snapshot = _quota_filter_candidates(candidates, config=config)
    if quota_allowed:
        candidates = quota_allowed
    elif candidates and quota_exhausted:
        return {
            "model": None,
            "reason": "no_quota_candidates",
            "epsilon_used": epsilon if epsilon is not None else config.get("epsilon", 0),
            "candidates": [],
            "unavailable_candidates": unavailable,
            "quota_exhausted_candidates": quota_exhausted,
            "quota_snapshot": quota_snapshot,
            "task_tier": task_tier,
            "schedule_label": "unknown",
            "effective_cost_est": 0,
            "model_scores": {},
        }
    _log_unavailable = bool(unavailable)

    if not candidates:
        return {
            "model": None,
            "reason": "no_candidates",
            "epsilon_used": epsilon if epsilon is not None else config.get("epsilon", 0),
            "candidates": [],
            "unavailable_candidates": unavailable if _log_unavailable else [],
            "quota_exhausted_candidates": quota_exhausted,
            "capability_skipped_candidates": [],
            "quota_snapshot": quota_snapshot,
            "task_tier": task_tier,
            "schedule_label": "unknown",
            "effective_cost_est": 0,
            "model_scores": {},
        }

    candidates, capability_skipped = _capability_filter_candidates(candidates, task_tier, task_class, config)
    if not candidates and capability_skipped:
        return {
            "model": None,
            "reason": "no_capability_candidates",
            "epsilon_used": epsilon if epsilon is not None else config.get("epsilon", 0),
            "candidates": [],
            "unavailable_candidates": unavailable if _log_unavailable else [],
            "quota_exhausted_candidates": quota_exhausted,
            "capability_skipped_candidates": capability_skipped,
            "quota_snapshot": quota_snapshot,
            "task_tier": task_tier,
            "schedule_label": "unknown",
            "effective_cost_est": 0,
            "model_scores": {},
        }
    sticky_key = sticky_key or os.environ.get("HERMES_ROUTER_STICKY_KEY")
    sticky_model = _sticky_candidate(sticky_key, task_class, task_tier, candidates)
    if sticky_model:
        return {
            "model": sticky_model,
            "reason": "sticky_affinity",
            "epsilon_used": epsilon if epsilon is not None else config.get("epsilon", 0),
            "candidates": candidates,
            "unavailable_candidates": unavailable if _log_unavailable else [],
            "quota_exhausted_candidates": quota_exhausted,
            "capability_skipped_candidates": capability_skipped,
            "quota_snapshot": quota_snapshot,
            "task_tier": task_tier,
            "schedule_label": _schedule_label(sticky_model, now_utc),
            "effective_cost_est": _effective_cost(sticky_model, 2000, now_utc),
            "model_scores": {},
        }

    stats = get_model_stats(task_class=task_class)
    
    model_scores = {}
    for s in stats:
        model_scores[s["model"]] = s

    min_traces = config["min_traces_per_model"]
    cold_models = [
        m for m in candidates
        if m not in model_scores or model_scores[m]["count"] < min_traces
    ]
    warm_models = [m for m in candidates if m not in cold_models]

    if epsilon is None:
        epsilon = config["epsilon"]

    # 冷启动策略：只有当所有候选都缺乏样本时才强制探索。
    # 否则保留 ε-greedy，让已验证的 gpt-5.5/Codex 等 warm model 继续承担主力，
    # 但仍以 epsilon 概率探索冷模型。
    if cold_models and not warm_models:
        epsilon = 1.0
        reason = f"cold_start(all_{len(cold_models)}_models_need_warmup)"
    elif cold_models:
        reason = f"epsilon_greedy(epsilon={epsilon}, cold_available={len(cold_models)})"
    else:
        reason = f"epsilon_greedy(epsilon={epsilon})"

    # ε-greedy 选择
    if random.random() < epsilon:
        # 探索: 随机选 (off-peak 时偏向便宜模型)
        if cold_models:
            chosen = random.choice(cold_models)
            reason = f"explore_cold({reason})"
        else:
            # off-peak: 偏向低成本模型
            pt_now = _get_pricing()
            if pt_now and pt_now.is_off_peak(candidates[0], now_utc):
                cheap = sorted(candidates, key=lambda m: _effective_cost(m, 2000, now_utc))
                chosen = cheap[0]
                reason = f"explore_offpeak({reason})"
            else:
                chosen = random.choice(candidates)
                reason = f"explore({reason})"
    else:
        # 利用: 选最高 score (含时间感知成本)
        def score_model(m):
            ms = model_scores.get(m, {})
            count = ms.get("count", 0)
            pr = ms.get("pass_rate", 0.5)
            ec = _effective_cost(m, 2000, now_utc)
            avg_dur = ms.get("avg_dur", 10)
            base = pr - 0.1 * ec * 100 - 0.01 * avg_dur / 60  # λ_cost=0.1, λ_time=0.01
            # Cold-start warm-up bonus: models with <min_traces get a score boost
            # so they're competitive in exploit phase, not just the 10% explore.
            # Bonus decays linearly with trace count: 0 traces → +0.25, min_traces → +0
            if count < min_traces:
                warmup_bonus = 0.25 * (1.0 - count / max(min_traces, 1))
                base += warmup_bonus
            return base

        scored = [(m, score_model(m)) for m in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        chosen = scored[0][0]
        label = _schedule_label(chosen, now_utc)
        reason = f"exploit({reason}, score={scored[0][1]:.4f}, schedule={label})"

    _remember_sticky(sticky_key, task_class, task_tier, chosen)
    return {
        "model": chosen,
        "reason": reason,
        "epsilon_used": epsilon,
        "candidates": candidates,
        "unavailable_candidates": unavailable if _log_unavailable else [],
        "quota_exhausted_candidates": quota_exhausted,
        "capability_skipped_candidates": capability_skipped,
        "quota_snapshot": quota_snapshot,
        "task_tier": task_tier,
        "schedule_label": _schedule_label(chosen, now_utc),
        "effective_cost_est": _effective_cost(chosen, 2000, now_utc),
        "model_scores": {
            m: model_scores[m]["score"] if m in model_scores else None
            for m in candidates
        },
    }


def select_pair(
    task_tier="codegen",
    task_class=None,
    diversity_rule="provider_or_savings",
    config=None,
    now_utc=None,
) -> dict:
    """为 verification 选择 (producer, reviewer) 对
    
    diversity_rule:
    - "provider_or_savings": 优先不同 provider; 同 provider 仅当 off-peak 节省 >30% 且 pass_rate≥0.9
    """
    if config is None:
        config = load_config()
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    pt = _get_pricing()

    # 获取候选
    producer_candidates = pt.get_candidate_models(task_tier) if pt else config["candidate_models"]
    reviewer_candidates = pt.get_candidate_models("reviewer") if pt else config["candidate_models"]

    # 选择 producer
    prod = select_model(task_class=task_class, task_tier=task_tier, config=config, now_utc=now_utc)
    if not prod.get("model"):
        return {
            "producer": prod,
            "reviewer": {"model": None, "reason": "producer_unavailable"},
            "diversity_rule": diversity_rule,
            "same_provider": False,
        }

    # 选择 reviewer (排除 producer 的 provider 优先)
    prod_provider = _provider_for_model(prod["model"], config=config)
    
    # 过滤: 优先不同 provider
    diverse_reviewers = [
        m for m in reviewer_candidates
        if m != prod["model"] and _provider_for_model(m, config=config) != prod_provider
    ]
    
    if diverse_reviewers:
        # 在 diverse reviewers 中选最优
        # 使用与 select_model 相同的逻辑
        rev_config = dict(config)
        rev_config["candidate_models"] = diverse_reviewers
        reviewer = select_model(
            task_class=task_class,
            task_tier="reviewer",
            config=rev_config,
            now_utc=now_utc,
            candidate_override=diverse_reviewers,
        )
    else:
        # 无 diverse reviewer — 选同 provider 但要求 off-peak + 高 pass_rate
        same_provider = [
            m for m in reviewer_candidates
            if m != prod["model"] and _provider_for_model(m, config=config) == prod_provider
        ]
        reviewer = {"model": None, "reason": "no_diverse_reviewer"}
        if same_provider and pt and pt.is_off_peak(prod["model"], now_utc):
            stats = get_model_stats(task_class=task_class)
            stats_by_model = {s.get("model"): s for s in stats if isinstance(s, dict)}
            high_conf_same_provider = [
                m for m in same_provider
                if stats_by_model.get(m, {}).get("pass_rate", 0.5) >= 0.9
            ]
            if high_conf_same_provider:
                rev_config = dict(config)
                rev_config["candidate_models"] = high_conf_same_provider
                reviewer = select_model(
                    task_class=task_class,
                    task_tier="reviewer",
                    config=rev_config,
                    now_utc=now_utc,
                    candidate_override=high_conf_same_provider,
                )
                if reviewer.get("model"):
                    reviewer = dict(reviewer)
                    reviewer["reason"] = "same_provider_offpeak_highconf"

    return {
        "producer": prod,
        "reviewer": reviewer,
        "diversity_rule": diversity_rule,
        "same_provider": (
            _provider_for_model(prod["model"], config=config) == _provider_for_model(reviewer["model"], config=config)
            if reviewer.get("model")
            else False
        ),
    }


def _safe_quota_status(quota_snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return a secret-safe, schema-stable quota ledger projection."""
    safe: Dict[str, Dict[str, Any]] = {}
    allow = {
        "model", "provider", "status", "observability", "quota_type", "confidence",
        "reset_at", "reset_after_seconds", "remaining_tokens", "remaining_requests",
        "source", "error_class", "previous_status", "reset_elapsed",
    }
    for key, snap in (quota_snapshot or {}).items():
        if not isinstance(snap, dict):
            continue
        safe[str(key)] = {k: v for k, v in snap.items() if k in allow}
    return safe


def _skipped_model_entries(decision: Dict[str, Any]) -> List[Dict[str, Any]]:
    quota_status = _safe_quota_status(decision.get("quota_snapshot", {}))
    skipped: List[Dict[str, Any]] = []
    for model in decision.get("unavailable_candidates", []) or []:
        skipped.append({
            "model": model,
            "provider": _provider_for_model(model),
            "skip_reason": "provider_unavailable",
        })
    for model in decision.get("quota_exhausted_candidates", []) or []:
        provider = _provider_for_model(model)
        key = f"{provider}::{model}"
        snap = quota_status.get(key) or next(
            (v for v in quota_status.values() if v.get("model") == model),
            {},
        )
        skipped.append({
            "model": model,
            "provider": provider,
            "skip_reason": "quota_exhausted",
            "quota_status": snap.get("status"),
            "quota_confidence": snap.get("confidence"),
            "reset_at": snap.get("reset_at"),
            "reset_after_seconds": snap.get("reset_after_seconds"),
        })
    for model in decision.get("capability_skipped_candidates", []) or []:
        skipped.append({
            "model": model,
            "provider": _provider_for_model(model),
            "skip_reason": "capability_mismatch",
        })
    return skipped


def _run_json_command(cmd: List[str], timeout: int = 30) -> Tuple[Optional[dict], dict]:
    meta = {"cmd": cmd, "returncode": None, "stderr": "", "stdout_tail": ""}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:
        meta["error"] = repr(exc)
        return None, meta
    meta["returncode"] = proc.returncode
    meta["stderr"] = (proc.stderr or "")[-1000:]
    meta["stdout_tail"] = (proc.stdout or "")[-1000:]
    try:
        return json.loads(proc.stdout or "{}"), meta
    except Exception as exc:
        meta["error"] = f"json_parse_failed: {exc}"
        return None, meta


def _finite_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if math.isfinite(parsed) else None


def _nonnegative_int_value(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


def _valid_optional_unit_number(value: Any) -> bool:
    if value is None:
        return True
    parsed = _finite_number(value)
    return parsed is not None and 0.0 <= parsed <= 1.0


def _quota_gate_passed(quota: Any, expected_min_confidence: float = 0.50) -> bool:
    if not isinstance(quota, dict) or not quota:
        return False
    required_fields = {
        "schema_version",
        "ok",
        "status",
        "models_checked",
        "min_confidence",
        "pass_count",
        "failure_count",
        "passes",
        "failures",
        "snapshots",
        "observability_evidence",
    }
    if not required_fields.issubset(quota):
        return False
    if quota.get("schema_version") != 1:
        return False
    failure_count = _nonnegative_int_value(quota.get("failure_count"))
    pass_count = _nonnegative_int_value(quota.get("pass_count"))
    status_raw = quota.get("status")
    status = str(status_raw).strip().upper() if isinstance(status_raw, str) else ""
    models_checked = quota.get("models_checked")
    passes = quota.get("passes")
    failures = quota.get("failures")
    snapshots = quota.get("snapshots")
    observability = quota.get("observability_evidence")
    required_min = _finite_number(expected_min_confidence)
    if required_min is None or required_min < 0.0 or required_min > 1.0:
        return False
    min_confidence = _finite_number(quota.get("min_confidence"))
    if min_confidence is None or min_confidence < required_min or min_confidence > 1.0:
        return False
    if not isinstance(models_checked, list) or not models_checked or any(not isinstance(m, str) or not m.strip() for m in models_checked):
        return False
    models = [str(m).strip() for m in models_checked]
    if len(set(models)) != len(models):
        return False
    if not isinstance(passes, list) or len(passes) != len(models):
        return False
    if not isinstance(failures, list) or failures:
        return False
    if not isinstance(snapshots, dict) or not snapshots:
        return False
    if not isinstance(observability, dict) or not observability:
        return False
    if pass_count != len(models) or failure_count != 0:
        return False
    def _has_timestamp(entry: dict) -> bool:
        return bool(entry.get("last_updated") or entry.get("updated_at") or entry.get("last_seen_at") or entry.get("recorded_at") or entry.get("timestamp"))

    pass_models = set()
    for entry in passes:
        if not isinstance(entry, dict):
            return False
        model = str(entry.get("model") or "").strip()
        status_entry = str(entry.get("status") or "").strip().lower()
        if not model or status_entry not in {"ok", "pass", "available"}:
            return False
        pass_models.add(model)
        confidence = _finite_number(entry.get("confidence"))
        if confidence is None or confidence < min_confidence:
            return False
        if not _has_timestamp(entry):
            return False
    if pass_models != set(models):
        return False
    for model in models:
        snap = snapshots.get(model)
        if snap is None:
            for key, candidate in snapshots.items():
                if key == model or str(key).endswith("::" + model):
                    snap = candidate
                    break
                if isinstance(candidate, dict) and str(candidate.get("model") or "").strip() == model:
                    snap = candidate
                    break
        if not isinstance(snap, dict):
            return False
        if str(snap.get("model") or "").strip() != model:
            return False
        snap_status = str(snap.get("status") or "").strip().lower()
        if snap_status not in {"ok", "pass", "available"}:
            return False
        confidence = _finite_number(snap.get("confidence"))
        if confidence is None or confidence < min_confidence:
            return False
        if not _has_timestamp(snap):
            return False
    counts = observability.get("counts")
    by_model = observability.get("by_model")
    if not isinstance(counts, dict) or not isinstance(by_model, dict):
        return False
    usable = _nonnegative_int_value(counts.get("usable"))
    total = _nonnegative_int_value(counts.get("total"))
    if usable != len(models) or total != len(models):
        return False
    usable_models = set()
    snapshot_by_model = {}
    for model in models:
        snap = snapshots.get(model)
        if snap is None:
            for key, candidate in snapshots.items():
                if isinstance(candidate, dict) and str(candidate.get("model") or "").strip() == model:
                    snap = candidate
                    break
                if key == model or str(key).endswith("::" + model):
                    snap = candidate
                    break
        if isinstance(snap, dict):
            snapshot_by_model[model] = snap
    for key, entry in by_model.items():
        if not isinstance(entry, dict):
            return False
        model = str(entry.get("model") or "").strip()
        if not model and isinstance(key, str):
            model = key.split("::")[-1]
        if model not in models:
            continue
        if entry.get("evidence_state") != "usable":
            return False
        entry_status = str(entry.get("status") or "").strip().lower()
        if entry_status not in {"ok", "pass", "available"}:
            return False
        entry_confidence = _finite_number(entry.get("confidence"))
        if entry_confidence is None or entry_confidence < min_confidence:
            return False
        if not _has_timestamp(entry):
            return False
        snap = snapshot_by_model.get(model)
        if not snap:
            return False
        snap_confidence = _finite_number(snap.get("confidence"))
        if snap_confidence is None or abs(entry_confidence - snap_confidence) > 0.0001:
            return False
        usable_models.add(model)
    if usable_models != set(models):
        return False
    return quota.get("ok") is True and status in {"PASS", "OK"}


def _model_available_for_readiness(model: str, config: Optional[dict] = None) -> bool:
    try:
        return _model_available(model, config=config, log_unavailable=False)
    except TypeError:
        # Tests and downstream integrations may monkeypatch the older two-arg
        # callable. Preserve compatibility; the production implementation above
        # remains side-effect-free for readiness.
        return _model_available(model, config=config)


def _eligible_alternates(candidate_models: List[str], dominant_model: Optional[str], config: Optional[dict]) -> Tuple[List[str], dict]:
    # Readiness is an observe-only certification gate. Avoid provider availability
    # transition writes while computing advisory alternates.
    candidates = [m for m in candidate_models if m and m != dominant_model and _model_available_for_readiness(m, config=config)]
    allowed, skipped, snapshots = _quota_filter_candidates(candidates, config=config)
    return allowed, {"candidate_models": candidates, "quota_skipped": skipped, "quota_snapshot": snapshots, "read_only": True}


def _build_rebalance_plan(diversity: Optional[dict], alternates: List[str], threshold: float, window: int) -> dict:
    """Return a deterministic, non-mutating warm-up plan for diversity skew.

    The plan answers: if the current window is dominated by one model, how many
    future non-dominant calls must be routed before a fresh readiness check can
    plausibly pass? It never changes routing by itself.
    """
    if not isinstance(diversity, dict) or not diversity.get("dominance_warning"):
        return {
            "schema_version": 1,
            "action": "no_rebalance_needed",
            "required_non_dominant_calls": 0,
            "target_threshold": threshold,
            "window": window,
            "per_model_targets": {},
            "policy": "plan only; router readiness never mutates active routing automatically",
        }
    stats = diversity.get("model_stats") or {}
    total_calls = int(diversity.get("total_calls") or 0)
    dominant = diversity.get("dominant_model")
    dominant_total = 0
    if dominant in stats and isinstance(stats.get(dominant), dict):
        dominant_total = int(stats[dominant].get("total") or 0)
    elif total_calls and diversity.get("dominant_share") is not None:
        dominant_total = int(round(float(diversity.get("dominant_share") or 0) * total_calls))
    threshold = max(0.01, min(0.99, float(threshold or 0.80)))
    if not total_calls:
        total_calls = max(1, int(window or 1))
    required = max(0, math.ceil((dominant_total / threshold) - total_calls))
    if window and window > 0:
        required = min(required, int(window))
    per_model_targets: Dict[str, int] = {}
    if alternates and required:
        base, extra = divmod(required, len(alternates))
        for idx, model in enumerate(alternates):
            per_model_targets[model] = base + (1 if idx < extra else 0)
    return {
        "schema_version": 1,
        "action": "warm_up_non_dominant_alternates" if alternates else "blocked_no_eligible_alternates",
        "dominant_model": dominant,
        "current_dominant_calls": dominant_total,
        "current_total_calls": total_calls,
        "current_dominant_share": diversity.get("dominant_share"),
        "target_threshold": threshold,
        "window": window,
        "required_non_dominant_calls": required,
        "eligible_alternates": alternates,
        "per_model_targets": per_model_targets,
        "rerun_gate_after": "model-router.py readiness --json --gate",
        "policy": "plan only; router readiness never mutates active routing automatically",
    }


def router_readiness(
    threshold: float = 0.80,
    window: int = 500,
    min_quota_confidence: float = 0.50,
    config: Optional[dict] = None,
) -> dict:
    """Fail-closed router readiness gate for multi-model certification/autonomy.

    This gate intentionally does not mutate routing decisions. It makes router
    skew visible to promotion gates and identifies eligible non-dominant models
    before any caller may claim budget handoff/autonomous execution readiness.
    """
    config = config if config is not None else load_config()
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    diversity_cmd = [
        sys.executable, os.path.join(scripts_dir, "model-diversity-monitor.py"),
        "--json", "--threshold", str(threshold), "--window", str(window),
    ]
    diversity, diversity_meta = _run_json_command(diversity_cmd, timeout=60)
    quota_cmd = [
        sys.executable, os.path.join(scripts_dir, "model_quota.py"), "confidence-gate",
        "--json", "--min-confidence", str(min_quota_confidence),
    ]
    quota, quota_meta = _run_json_command(quota_cmd, timeout=60)
    pt = _get_pricing()
    if pt:
        candidate_models = sorted(set(pt.get_candidate_models("codegen") + pt.get_candidate_models("reviewer") + pt.get_candidate_models("arbiter")))
    elif config:
        candidate_models = list(config.get("candidate_models", []))
    else:
        candidate_models = []
    dominant_model = diversity.get("dominant_model") if isinstance(diversity, dict) else None
    alternates, alternate_meta = _eligible_alternates(candidate_models, dominant_model, config=config)
    failures: List[str] = []
    diversity_returncode = diversity_meta.get("returncode") if isinstance(diversity_meta, dict) else None
    quota_returncode = quota_meta.get("returncode") if isinstance(quota_meta, dict) else None
    route_diversity_signals = diversity.get("route_diversity_signals") if isinstance(diversity, dict) else None
    route_diversity_signals_shape_valid = isinstance(route_diversity_signals, (dict, list))
    diversity_warnings_value = _nonnegative_int_value(diversity.get("diversity_warnings")) if isinstance(diversity, dict) else None
    diversity_shape_valid = (
        isinstance(diversity, dict)
        and isinstance(diversity.get("dominance_warning"), bool)
        and isinstance(diversity.get("gate_failed"), bool)
        and diversity_warnings_value is not None
        and route_diversity_signals_shape_valid
        and _valid_optional_unit_number(diversity.get("dominant_share"))
        and ("total_calls" not in diversity or _nonnegative_int_value(diversity.get("total_calls")) is not None)
        and ("window" not in diversity or _nonnegative_int_value(diversity.get("window")) is not None)
        and ("min_samples" not in diversity or _nonnegative_int_value(diversity.get("min_samples")) is not None)
        and ("threshold" not in diversity or _valid_optional_unit_number(diversity.get("threshold")))
    )
    try:
        rebalance_plan = _build_rebalance_plan(
            diversity if diversity_shape_valid else None,
            alternates,
            threshold,
            window,
        )
        rebalance_plan_failed = False
    except Exception as exc:
        rebalance_plan = {
            "schema_version": 1,
            "action": "rebalance_plan_unavailable",
            "error": type(exc).__name__,
            "policy": "plan only; router readiness never mutates active routing automatically",
        }
        rebalance_plan_failed = True
    diversity_unavailable = (
        not isinstance(diversity, dict)
        or not diversity
        or not diversity_shape_valid
    )
    if diversity_unavailable:
        failures.append("diversity_report_unavailable")
    elif diversity_returncode not in (0, None):
        failures.append("diversity_monitor_nonzero_exit")
    if rebalance_plan_failed:
        failures.append("rebalance_plan_unavailable")
    if diversity_shape_valid:
        if diversity["dominance_warning"]:
            failures.append("dominance_warning")
            if not alternates:
                failures.append("no_eligible_non_dominant_alternates")
        if diversity["gate_failed"] or (diversity_warnings_value or 0) > 0 or bool(diversity["route_diversity_signals"]):
            failures.append("diversity_gate_failed")
    quota_ok = _quota_gate_passed(quota, expected_min_confidence=min_quota_confidence)
    if quota_returncode not in (0, None):
        failures.append("quota_confidence_unavailable")
    elif not isinstance(quota, dict) or not quota:
        failures.append("quota_confidence_unavailable")
    elif not quota_ok:
        failures.append("quota_confidence_failed")
    status = "PASS" if not failures else "FAIL_CLOSED"
    recommended_next_actions: List[str] = []
    if "dominance_warning" in failures:
        recommended_next_actions.append("warm_up_eligible_non_dominant_alternates")
    if "diversity_report_unavailable" in failures or "rebalance_plan_unavailable" in failures:
        recommended_next_actions.append("rerun_diversity_monitor_and_preserve_artifact")
    if "diversity_monitor_nonzero_exit" in failures:
        recommended_next_actions.append("inspect_preserved_diversity_gate_artifact")
    if "diversity_gate_failed" in failures:
        recommended_next_actions.append("resolve_diversity_gate_failures")
    if "quota_confidence_unavailable" in failures or "quota_confidence_failed" in failures or not quota_ok:
        recommended_next_actions.append("refresh_quota_confidence_or_lower_risk_tier")
    if not failures and not recommended_next_actions:
        recommended_next_actions.append("certification_gate_clear")
    certification_gate = {
        "schema_version": 1,
        "status": status,
        "can_certify_autonomy": not failures,
        "can_promote_budget_handoff": not failures,
        "automatic_rebalance_performed": False,
        "route_mutation_allowed": False,
        "blocking_failures": list(failures),
        "recommended_next_actions": recommended_next_actions,
        "policy": "readiness is a fail-closed certification gate only; it reports alternates but never changes the active model route automatically",
    }
    return {
        "schema_version": 1,
        "status": status,
        "ok": not failures,
        "failed_checks": failures,
        "certification_gate": certification_gate,
        "dominant_model": dominant_model,
        "dominant_share": diversity.get("dominant_share") if isinstance(diversity, dict) else None,
        "candidate_models": candidate_models,
        "eligible_non_dominant_alternates": alternates,
        "rebalance_required": bool(isinstance(diversity, dict) and diversity.get("dominance_warning")),
        "rebalance_plan": rebalance_plan,
        "rebalance_policy": "promotion/autonomy fails closed while dominance_warning is true; prefer eligible_non_dominant_alternates for warm-up before rerun",
        "diversity": diversity,
        "diversity_meta": diversity_meta,
        "quota_confidence": quota,
        "quota_meta": quota_meta,
        "alternate_meta": alternate_meta,
    }


def log_decision(decision, task_class=None):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    selected = decision.get("model")
    entry = {
        "schema_version": 2,
        "event": "routing_decision",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task_class": task_class or "",
        "task_tier": decision.get("task_tier", ""),
        "selected_model": selected,
        "selected_provider": _provider_for_model(selected) if selected else "unknown",
        "reason": decision.get("reason", ""),
        "epsilon_used": decision.get("epsilon_used", 0),
        "schedule_label": decision.get("schedule_label", "?"),
        "eff_cost_est": decision.get("effective_cost_est", 0),
        "candidate_models": decision.get("candidates", []) or [],
        "skipped_models": _skipped_model_entries(decision),
        "quota_status": _safe_quota_status(decision.get("quota_snapshot", {})),
        "model_scores": decision.get("model_scores", {}) or {},
        # Backward-compatible fields for existing status readers/parsers.
        "model": selected,
        "quota_exhausted_candidates": decision.get("quota_exhausted_candidates", []) or [],
        "capability_skipped_candidates": decision.get("capability_skipped_candidates", []) or [],
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def cli():
    parser = argparse.ArgumentParser(description="Model Router — ε-greedy 模型选择器 (v2: cost-aware)")
    sub = parser.add_subparsers(dest="cmd")

    sel = sub.add_parser("select", help="选择一个模型")
    sel.add_argument("--task-class", default="", help="任务分类")
    sel.add_argument("--task-tier", default="codegen", help="任务层级 (codegen/reviewer/arbiter/chat/tts)")
    sel.add_argument("--epsilon", type=float, default=None, help="探索率")
    sel.add_argument("--hour", type=int, default=None, help="模拟 UTC 小时 (0-23)")

    pair = sub.add_parser("select-pair", help="选择 (producer, reviewer) 对")
    pair.add_argument("--task-tier", default="codegen")
    pair.add_argument("--task-class", default="")
    pair.add_argument("--diversity-rule", default="provider_or_savings")
    pair.add_argument("--hour", type=int, default=None)

    status = sub.add_parser("status", help="显示路由状态")
    status.add_argument("--quota", action="store_true", help="显示 quota snapshot")

    readiness = sub.add_parser("readiness", help="Fail-closed router readiness gate for certification/autonomy")
    readiness.add_argument("--json", action="store_true")
    readiness.add_argument("--gate", action="store_true")
    readiness.add_argument("--threshold", type=float, default=0.80)
    readiness.add_argument("--window", type=int, default=500)
    readiness.add_argument("--min-quota-confidence", type=float, default=0.50)

    pr = sub.add_parser("probe", help="探测所有 provider 可用性 (auth check, no token spend)")
    pr.add_argument("--json", action="store_true", help="输出 JSON 而不是表格")

    args = parser.parse_args()
    
    now = datetime.now(timezone.utc)
    hour = getattr(args, "hour", None)
    if hour is not None:
        now = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    config = load_config()

    if args.cmd == "select":
        decision = select_model(
            task_class=args.task_class or None,
            task_tier=args.task_tier,
            epsilon=args.epsilon,
            config=config,
            now_utc=now,
        )
        log_decision(decision, task_class=args.task_class or None)
        if not decision.get("model"):
            print(json.dumps({"error": "model_selection_failed", "reason": decision.get("reason", "unknown")}, ensure_ascii=False), file=sys.stderr)
            sys.exit(2)
        print(decision["model"])

    elif args.cmd == "select-pair":
        result = select_pair(
            task_tier=args.task_tier,
            task_class=args.task_class or None,
            diversity_rule=args.diversity_rule,
            config=config,
            now_utc=now,
        )
        producer = result.get("producer") or {}
        reviewer = result.get("reviewer") or {}
        if not producer.get("model") or not reviewer.get("model"):
            error = {
                "error": "model_pair_selection_failed",
                "producer_reason": producer.get("reason", "unknown"),
                "reviewer_reason": reviewer.get("reason", "unknown"),
            }
            print(json.dumps(error, ensure_ascii=False, sort_keys=True), file=sys.stderr)
            sys.exit(2)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.cmd == "status":
        pt = _get_pricing()
        if config is None:
            print("Cannot load config")
            sys.exit(1)
        print(f"smart_model_routing: enabled={config['enabled']}")
        print(f"default model: {config['default_model']}")
        print(f"epsilon: {config['epsilon']}")
        print(f"min_traces: {config['min_traces_per_model']}")
        print(f"UTC hour: {now.hour:02d}:00")
        print()
        if pt:
            print("Pricing-aware candidates:")
            for tier in ["codegen", "reviewer", "arbiter", "chat", "tts"]:
                models = pt.get_candidate_models(tier)
                if models:
                    print(f"  {tier}: {models}")
        else:
            print(f"candidates (static): {config['candidate_models']}")
        print()
        stats = get_model_stats()
        if stats:
            print("Model stats (7d):")
            for s in stats:
                eff_cost = _effective_cost(s["model"], 2000, now)
                label = _schedule_label(s["model"], now)
                print(f"  {s['model']:25s} {s['count']:3d}x pass={s['pass_rate']:.0%} "
                      f"score={s['score']:.4f} eff_cost=${eff_cost:.5f} ({label})")
        print()
        if os.path.exists(LOG_FILE):
            print("Recent decisions:")
            with open(LOG_FILE) as f:
                lines = f.readlines()[-10:]
            for line in lines:
                try:
                    d = json.loads(line)
                    label = d.get("schedule_label", "?")
                    print(f"  {d['ts']} → {d['model']} ({d['reason'][:60]}) [{label}]")
                except json.JSONDecodeError:
                    pass
        if getattr(args, "quota", False) and model_quota:
            print("\nQuota snapshot:")
            models = []
            if pt:
                models = list(pt.models.keys())
            else:
                models = config.get("candidate_models", [])
            print(model_quota.render_table(model_quota.snapshot_models(models)))

    elif args.cmd == "readiness":
        report = router_readiness(
            threshold=args.threshold,
            window=args.window,
            min_quota_confidence=args.min_quota_confidence,
            config=config,
        )
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            print(f"router_readiness: {report['status']} failures={report['failed_checks']}")
            print(f"dominant={report.get('dominant_model')} share={report.get('dominant_share')} alternates={report.get('eligible_non_dominant_alternates')}")
        if args.gate and not report.get("ok"):
            sys.exit(2)

    elif args.cmd == "probe":
        report = probe_all_providers(verbose=False)
        if getattr(args, "json", False):
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("Provider availability probe (no token spend, auth check only):")
            print(f"\nAvailable ({len(report['available'])}):")
            for a in report["available"]:
                print(f"  ✓ {a['model']:30s} provider={a['provider']:15s} env={a.get('env_var') or '-'}")
            print(f"\nUnavailable ({len(report['unavailable'])}):")
            for u in report["unavailable"]:
                print(f"  ✗ {u['model']:30s} provider={u['provider']:15s} reason={u.get('reason')}")
            print(f"\nSnapshot: ~/.hermes/state/provider_availability.json")
            print(f"Transition log: ~/.hermes/state/unavailable_providers.jsonl")

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
