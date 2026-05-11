# 双模型架构评分报告 — Claude Code vs Codex — 2026-04-27

## 结论

- Claude Code 评分: 78/100, verdict=ship_with_p1
- Codex/gpt-5.5 评分: 74/100, verdict=ship_with_p1
- 分歧: Codex 比 Claude 严格 4 分
- 共识: 无 P0 blocker，但存在必须收敛的 P1 风险

## Claude Code token/cost

- subtype: success
- num_turns: 1
- total_cost_usd: 0.35862950000000005
- usage: `{"input_tokens": 5, "cache_creation_input_tokens": 48946, "cache_read_input_tokens": 17034, "output_tokens": 1767, "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0}, "service_tier": "standard", "cache_creation": {"ephemeral_1h_input_tokens": 48946, "ephemeral_5m_input_tokens": 0}, "inference_geo": "", "iterations": [{"input_tokens": 5, "output_tokens": 1767, "cache_read_input_tokens": 17034, "cache_creation_input_tokens": 48946, "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 48946}, "type": "message"}], "speed": "standard"}`

## Claude dimension scores

```json
{
  "correctness": 82,
  "safety": 85,
  "observability": 72,
  "model_diversity": 70,
  "automation": 68,
  "test_coverage": 65,
  "operability": 78,
  "cost_control": 80
}
```

## Codex dimension scores

```json
{
  "correctness": 76,
  "safety": 78,
  "observability": 70,
  "model_diversity": 72,
  "automation": 74,
  "test_coverage": 62,
  "operability": 73,
  "cost_control": 61
}
```

## 双模型共识 P1

- Producer/reviewer binding lacks patch-id approval contract
- DeepSeek/OpenRouter unavailable but still appears in higher-tier/default paths
- New cross-patch real tests not integrated into self-test gate
- Exact-string-only patching is brittle
- --apply should require/strongly gate verification

## Claude P1 原文

```json
[
  {
    "id": "P1-1",
    "risk": "Exact-string-only patch matching brittle. Whitespace/encoding drift = silent reject. No fuzzy fallback.",
    "impact": "High reject rate on real repos, masked as low-conf rejection."
  },
  {
    "id": "P1-2",
    "risk": "No producer↔reviewer patch id cross-check. Reviewer can fabricate or duplicate patches outside producer set.",
    "impact": "Trust boundary leak; reviewer becomes shadow producer."
  },
  {
    "id": "P1-3",
    "risk": "test_cross_patch_real_execution.py not in self-test.py main list. Regression invisible to 24/24 gate.",
    "impact": "False green on Hermes self-test."
  },
  {
    "id": "P1-4",
    "risk": "T1 diversity collapsed to MiMo+gpt-5.5 since DeepSeek/OpenRouter down. Two-of-three quorum becomes solo if either fails.",
    "impact": "Diversity guarantee degrades silently; min_quorum=1 fallback hides it."
  },
  {
    "id": "P1-5",
    "risk": "--apply + --verify rollback restores file content but not git index/state. No dirty-tree pre-check.",
    "impact": "Mid-edit user changes overwritten; rollback may resurrect stale content."
  },
  {
    "id": "P1-6",
    "risk": "Reviewer model hand-picked via CLI flag. No router policy enforcing provider-diversity invariant at run time.",
    "impact": "Operator can accidentally pick same-provider reviewer (e.g. gpt-5.5 reviewing gpt-5.5)."
  },
  {
    "id": "P1-7",
    "risk": "call_model timeout fixed 120s, no retry/backoff, no circuit breaker. Codex abuse-protection 429 → hard fail.",
    "impact": "Producer flake = whole run fail; no graceful degradation."
  },
  {
    "id": "P1-8",
    "risk": "Log entry strips producer/reviewer raw output. Post-hoc audit of model behavior limited to plan JSON.",
    "impact": "Cannot reconstruct disagreements or debug parse failures from logs alone."
  }
]
```

## Codex P1 原文

```json
[
  "Arbitration independence is internally inconsistent: quorum.yaml sets exclude_voters=true, but T2/T3 list claude-opus-4-7 both as planner and arbiter. That violates the stated independent-arbiter design.",
  "Config and smoke path diverge: cross_patch excerpt shows reviewer_model=deepseek-v4-pro and DeepSeek fallbacks, while known state says OpenRouter/DeepSeek is unavailable and real smoke used MiMo explicitly. Default production invocation may silently fail or degrade unless reviewer routing is fixed.",
  "Actual cross-patch has no producer patch id / reviewer approved_patch_ids binding. Reviewer patches are accepted directly if present, and producer patches are accepted if reviewer verdict is pass. This weakens the producer-reviewer separation and enables reviewer hallucinated edits.",
  "Actual apply mode permits --apply without mandatory --verify or git dirty checks. Rollback only protects files touched by this run and does not guard against dirty worktrees, generated files, partial side effects, or verification omission.",
  "Cost control is mostly declarative. Real script_actual calls do not appear to enforce per-task budget, token ceilings, abuse-protection backoff, Claude reserve checks, or actual-cost logging.",
  "Observability is incomplete: actual logs intentionally omit producer/reviewer objects, which removes raw output and normalized plan evidence from durable audit logs. Protocol metadata is useful but insufficient for postmortems.",
  "Fallback-to-shadow behavior can contaminate quorum reasoning if downstream consumers do not strictly separate failed real members from synthetic low-confidence shadow plans.",
  "Cross-patch real tests are only 2 cases and are not yet integrated into the main self-test suite, so regression protection is weaker than the reported 24/24 self-test implies.",
  "Exact-string patching is safe but brittle. It avoids fuzzy misapplication but will frequently fail on formatting/context drift, creating operational friction for real repositories.",
  "Provider-aware invocation is landed, but model/provider availability, auth readiness, and default-route validation are not yet proven across T0-T3 paths."
]
```

## Claude next actions

```json
[
  {
    "id": "A1",
    "action": "Add producer.patch_id ↔ reviewer.approved_patch_ids cross-check in run_cross_patch_actual; reject reviewer patches without matching producer id unless reviewer.severity=block with explicit rationale.",
    "owner": "cross-patch.py",
    "effort": "S"
  },
  {
    "id": "A2",
    "action": "Wire test_cross_patch_real_execution.py into self-test.py main list; gate p10-health on it.",
    "owner": "self-test.py",
    "effort": "XS"
  },
  {
    "id": "A3",
    "action": "Enforce provider-diversity invariant at CLI entry: if model_provider(producer)==model_provider(reviewer) → error unless --allow-same-provider; emit warning to logs/cross-patch.jsonl.",
    "owner": "cross-patch.py CLI",
    "effort": "XS"
  },
  {
    "id": "A4",
    "action": "Add fuzzy patch fallback: difflib.SequenceMatcher ratio>=0.85 within ±5 line window when exact match fails, gated behind min_confidence>=0.85 to keep safety.",
    "owner": "apply_file_patches",
    "effort": "M"
  },
  {
    "id": "A5",
    "action": "Pre-apply git dirty-tree check + post-apply git stash backup instead of in-memory dict; --verify failure → git checkout HEAD -- <files>.",
    "owner": "cross-patch.py apply path",
    "effort": "M"
  }
]
```

## Codex next actions

```json
[
  "Fix quorum.yaml so arbiters are never voters in the same decision. For T2/T3 either remove claude-opus-4-7 from planners when it is arbiter, or select an independent arbiter dynamically.",
  "Align cross_patch defaults with currently available providers: replace unavailable DeepSeek defaults/fallbacks or add a preflight that rejects unavailable reviewer/arbiter models before execution.",
  "Add patch identity and approval binding: producer emits patch_id, reviewer emits approved_patch_ids plus optional revised patches, and merger only applies explicitly approved or reviewer-authored patches with provenance.",
  "Make production apply safe by default: require clean git worktree or explicit override, require --verify for --apply unless --unsafe-no-verify is passed, and record rollback/dirty-state metadata.",
  "Integrate test_cross_patch_real_execution.py into self-test.py and add tests for provider resolution, unavailable model fallback, arbiter exclusion, reviewer/proposer mismatch, path traversal, dirty worktree, verify rollback, and cost-budget rejection."
]
```

## Evidence files

- Claude raw: /tmp/claude-mm-architecture-score.json
- Codex raw: /tmp/codex-mm-architecture-score.raw
- Parsed summary: /tmp/mm-architecture-dual-score-summary.json
- State input: /tmp/hermes-mm-architecture-score-state.json

## P10 judgement

当前架构可以继续 ship_with_p1，但不能自我感觉良好。真正的抓手不是再跑更多 smoke，而是把评分共识里的 P1 变成工程闭环：

1. cross-patch patch-id / approved_patch_ids 合约。
2. --apply 默认要求 --verify，或至少强警告/显式 --no-verify。
3. test_cross_patch_real_execution.py 纳入 self-test.py。
4. DeepSeek unavailable 时默认 reviewer 不应仍指向 deepseek-v4-pro；要么动态路由 reviewer，要么配置 fallback reviewer。
5. exact-string 后补 fuzzy/structural patch matching。
