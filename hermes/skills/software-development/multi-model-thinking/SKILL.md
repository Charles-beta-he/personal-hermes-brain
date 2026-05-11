---
name: multi-model-thinking
description: "真正多模型思考协议 — Claude Code + Codex/gpt-5.5 + DeepSeek + MiMo 独立方案、交叉质疑、来回讨论、补充红队、最终多方认证最佳方案。含任务池自动介入 pipeline（并行 step、T2/T3 tier 选择、convergence 追踪）。触发词: 多模型思考, 真多模型, 多模型讨论, 双脑, 四脑, multi-model thinking, debate, ratification, parallel step, taskpool intervention"
license: MIT
---

# True Multi-Model Thinking Protocol — 真多模型思考协议

> 正确性 > 完整性 > 速度。先做对，再做全，最后做快。
>
> 旧版“两模型：主设计 → 第二模型验证 → 合并”只能算 cross-check，不算真正讨论。
> 真多模型必须满足：N>=3 独立模型、结构化交叉质疑、提案方回应/修订、补充红队、最终多方认证当前方案为约束内最佳。

## Evidence-First Rule (must apply during Phases 2-7)

Model agreement is not evidence. The main orchestrator owns tool execution and evidence collection; reviewer models own critique, evidence requests, and risk analysis.

### Ratification-first anti-shell rule

When the user asks for ratification/certification, do not frame the work as “deterministic completion already exists; add a formal multi-model certification shell outside it.” Ratification is a first-class lifecycle gate, not presentation metadata. The correct order is: claims/evidence bundle → issue ledger → cross-critique/rebuttal or explicit evidence-request loop → ratification votes/agreement matrix → final status transition. Deterministic gates remain necessary evidence, but they do not create a certified state by themselves. If `discussion_result.json` or an equivalent ratification artifact is missing, timed out, or contains unresolved severity>=3 blockers, the final status must be `not_certified` or `certified_with_minor_risks`, never “fully certified with a caveat.”

When using `consult_models.py`:
- Put factual assertions in the top-level `state.claims` array and tool outputs in `state.evidence`; do not hide claim candidates in prose-only fields like `claims_to_check`, or the truth gate may return `truth_status=no_claims` even though models answered.
- Link evidence to the exact claim IDs with `evidence[].supports` / equivalent grounding before fan-out; otherwise consensus can succeed while certification remains unsupported.
- Require each model to cite `evidence_bundle.grounding` for factual claims.
- If evidence is missing, the model must emit `evidence_requests` with the read-only command/query needed.
- Ratification cannot certify severity>=3 claims that are unsupported or contradicted, even if every model agrees.
- Do not enable SPL compression unless explicitly needed (`HERMES_MULTI_BRAIN_USE_SPL=1`); state compression must not hide claims/evidence.

This keeps the roles clean: orchestrator = tool/evidence brain; planners/reviewers = reasoning brains.

For external web articles that are Cloudflare-protected or dynamic, use `references/web-article-advisory-review.md`: fetch via browser first, fall back to Jina Reader when direct access returns 403/challenge, package article excerpts as claim-linked evidence, and label timed-out planner-only runs as `multi-view advisory` rather than certification.

For tool-backed fact checking inside multi-model review, use the Evidence Request Fulfillment Loop in `references/evidence-request-fulfillment-loop.md`: reviewer models request evidence, the orchestrator executes read-only allowlisted tools, then the result is fed back as evidence. Do not let every reviewer run arbitrary tools by default.

For multi-model GitHub repository/codebase analysis, use `references/repository-audit-evidence-packaging.md`: run deterministic read-only reconnaissance and project gates first, package each severity>=3 claim with explicit file/line or command evidence, link evidence to claims so the truth gate does not fall to `evidence_coverage=0.0`, and if the outer `consult_models.py` command times out, inspect the latest `~/.hermes/tick-*` artifacts before rerunning or claiming certification.

When the user asks to analyze an external repo and add the result to the local evolution/task pool, also use `references/external-repo-to-evolution-taskpool-advisory.md`: seed a canonical `brain_task_orchestrator.py add --lane evolution` task with architecture alignment fields, patch the note with advisory/certification caveats and P0/P1/P2 slices, then verify list/dispatch/lifecycle/proof/dashboard/reindex/search. A `not_certified` multi-model discussion can seed an evolution task only as `truth_grounded_advisory`, not as patch-level certification.

When the user asks to analyze a methodology/framework/concept and add landing work to the local taskpool (for example Missions / mission-command / OPORD), use `references/methodology-to-taskpool-advisory.md`: resolve ambiguous sources conservatively, inspect existing canonical tasks before adding, patch or archive duplicates, keep the landing set class-level (P0 schema/gates, P1 DAG/router/artifacts, P2 proof-gated runner), and verify the real vault with list/lifecycle/proof/selfcheck/dashboard/reindex/search. If the landing work also needs an enforceable Mission Envelope or is tied to a taskpool closeout incident (`claimed -> review`, invalid evidence shape, stale dispatch), use `references/mission-envelope-taskpool-closeout.md` for the concrete validator/test/lifecycle pattern.

Important evidence-packaging pitfall: passing one raw `--evidence-json` object that merely contains a list of citations is not enough. If evidence entries lack claim linkage (`supports` / claim IDs, or equivalent verified grounding), `discussion_result` may correctly report `truth_not_certified`, `needs_link_review`, and `evidence_coverage=0.0` even though the orchestrator read the files. Also keep claim IDs canonical: if `consult_models.py state --claim` creates `C-001` / `C-002`, evidence must support those exact IDs, not aliases like `C1` / `C2`; otherwise planner fan-out can succeed while the truth gate reports `unsupported` and `evidence_coverage=0.0`. Do not try to fix this in prose after the fact: rerun `consult_models.py state` with correctly linked `--evidence-json '{"supports":["C-001"]}'` entries, or patch the state artifact before `run` only if the tool explicitly supports that workflow. For adoption reviews, create claim-specific evidence objects or run the Evidence Request Fulfillment Loop before ratification; never upgrade fan-out consensus to certification just because the raw evidence is in context.

Implementation-closeout pitfall: a state built only from a broad task prompt, target files, and verification commands may produce `truth_status=no_claims` plus a low-consensus noop-vs-implementation split (`current_best.patches=[]` while `certification_intent=implementation_required`). This is not certification. For code changes, create claims after reading/patching evidence (e.g. C-001 behavior implemented, C-002 existing route preserved, C-003 targeted tests passed, C-004 build passed) and attach command/file evidence to those exact claim IDs before `run --discussion`. If `consult_models.py state ... --verify ...` is blocked by the shell/process wrapper as a suspected long-lived command because verify strings mention dev/watch/build tools, do not drop claims or run an ungrounded consult. Either re-run with safer quoting/shorter verify labels, or manually write a `schema: multi_model_state_v1` JSON from a known-good prior state shape with `claims[]`, `evidence[]`, `supports[]`, `implementation_target.files`, and `verify_commands`, validate it with `python3 -m json.tool`, then run `consult_models.py run` on that state. If a claim/evidence rerun would consume the closeout budget, report the prior run as advisory/not-certified and do not block commit/TG solely on the malformed state.

For code changes, MCP/tool changes, and cross-repo/API decisions, add a code-evidence gate before ratification. Use `references/gitnexus-code-evidence-mcp-pattern.md` for the GitNexus-inspired Hermes-native pattern: impact-before-edit, stale-index checks, detect-changes-before-commit, tool/shape contract checks, canonical contract IDs, and RRF only for evidence ranking (not truth certification). Do not import GitNexus runtime or copy code without license/supply-chain review.

When executing Lark/product work through a project profile, load `references/project-profile-injection-pattern.md` and enforce any `backend_contract_policy` / `regression_coverage_policy` fields from the profile. Frontend unit/build/mock regression is not enough for tasks whose acceptance depends on backend source-of-truth semantics; require backend source inspection, backend TDD when the backend is the correct fix point, and separate evidence labels for frontend, mock, real-backend, and remote-build gates.

For product/PRD/Lark task closeout, add a product-document evidence gate before ratification: automatically read the task body plus current PRD/product-doc evidence, UI test ledger, product-user-logic ledger, ADRs, and relevant backend/frontend source before declaring done. Package claims separately for (a) task-specific acceptance and (b) product-document consistency. If the task and product doc conflict, follow the explicit task for the current delivery, but record the conflict, the reason for task precedence, and any product-doc/backlog update needed. Never certify a product task from frontend compatibility alone when backend source-of-truth semantics (money, status, notification time, risk, KYC) remain unchecked.

For certification tasks where deterministic gates already pass, use `references/ratification-gate-pattern.md`: build a target-bound claims/evidence bundle and issue ledger, fail closed on missing/unscoped `discussion_result.json`, preserve degraded T3 attempts as provenance only, and allow status promotion only through an explicit ratification gate. For taskpool pass-state code or task-note repair, also use `references/taskpool-artifact-verification-regression.md`: `multimodel_status: certified` is not enough; load the local JSON artifact and run the target-bound ratification gate against the exact task before treating it as passed. For RMCS/`consult_models.py` certification infrastructure specifically, also apply the false-certification hardening notes in `references/resumable-multimodel-certification-system.md`: never trust `discussion_result.status` alone, require independent fanout/truth/vote/agreement gates, and treat post-certification reviewer blockers as requiring a fresh T3 tick. When changing fanout certification, validator/auditor, deterministic selfcheck, or global self-test integration, also apply `references/fanout-certification-fail-closed.md`: generator and validator must both reject malformed numeric fields, impossible count relationships, and handcrafted cross-field inconsistencies without crashing.

If certification is blocked by a provider/adapter runtime failure rather than a model dissent or missing evidence, use `references/provider-adapter-fallback-ratification.md`: preserve the native tick as not-certified, call the same model through an official read-only alternate route against the exact same grounded state, write a separate supplemental certification artifact, and label the result with an explicit runtime adapter caveat. This can close the target decision gate only when truth grounding, issue ledger, and all votes pass; it never certifies the broken adapter itself.

When the failing adapter is Claude Code with `--output-format json`, also use `references/claude-code-wrapper-runtime-errors.md`: Claude can return `returncode == 0` while the stdout wrapper contains `is_error=true` or `api_error_status=403`; decode the wrapper before plan parsing, classify provider/runtime failures separately from malformed model JSON, and do not retry auth/quota/runtime failures with a stricter JSON prompt.

For hook automation, task creation automation, agent continuation loops, or state-machine wiring, use `references/hook-automation-verifier-gates.md`: start with logging-only runtime fixtures, prove hook payload/order/blocking behavior, document state and aggregate schemas, enforce debounce/idempotency/recursion/session-project isolation, and keep write-capable behavior fail-closed until rollback/kill-switch evidence exists.

When the user asks to make such an idea a long-term project, land a project Workpad, or says “落地融合 / loop 多模型思考自检”, use `references/code-evidence-long-term-landing.md`: create project/P10/P9/playbook/review/task/evolution artifacts or the lighter Project Workpad variant, add a local-first self-check script, run sync/reindex/search + structural audit, preserve `dissent`/`not_certified` caveats, then make a scoped local commit. For external memory/RAG/retrieval/KG systems specifically, also load the Obsidian reference `references/external-memory-system-landing.md` and keep `~/Documents/brain` canonical while treating runtime indexes as derived caches unless explicitly decided otherwise.

When the input is an image, infographic, or social-post screenshot and the user asks for multi-model analysis plus adding an optimization plan to the local task pool, use `references/image-to-taskpool-optimization-advisory.md`: extract visible claims with vision/OCR, build claim-linked evidence, run fan-out/discussion as risk requires, and add a task note that honestly distinguishes `truth-grounded advisory` from `implementation-certified`. A not-certified discussion can seed a task, but the task must carry the unresolved issue/evidence-request caveat and must not imply patch-level certification.

When applying control theory, systems theory, metacognition, or skill-governance keypoints to multi-model thinking, do not default to “four brains for every keypoint”. Route by complexity, uncertainty, reflexivity, and blast radius: T0 for deterministic tool checks, T1 for lightweight reviewer, T2 for seed fanout + local gates, T3 for P10/canonical/self-evolution/high-risk rules. If this routing is landed into the local brain, prefer a keypoint-to-multimodel route matrix as a semantic/control-plane overlay rather than rewriting the Obsidian main hierarchy; use the Obsidian reference `references/local-brain-hierarchy-overlay-routing.md`.

For user work/product delivery, do not let multi-model discussion slow down an already evidence-clear fix. This does not mean skipping multi-model review; it means sequence it correctly: deterministic source/docs/tests first, implement the smallest safe fix when the defect and acceptance path are clear, then use T1/T2 reviewer or T3 ratification only for unresolved semantic/API/money/security ambiguity or final high-risk closeout. Avoid “multi-brain ceremony” where models restate known facts while code/tests wait. For task-pool scheduling, classify `work/product delivery` separately from `evolution/self-improvement`; P0/P1 returned work blockers should not be starved by open-ended Hermes self-improvement research.

## Provider-Specific Ratification Pitfalls

When running 4-model concurrent ratification, four provider-specific issues can block certification:

1. **MiMo returns empty content when called concurrently** — Xiaomi's API drops responses when hit simultaneously with other providers. Must run MiMo sequentially AFTER the concurrent trio (Claude+GPT+DeepSeek). Retry 3x with exponential backoff if still empty.

2. **DeepSeek reasoning tokens consume max_tokens budget** — `deepseek-v4-pro` emits chain-of-thought in `reasoning_content` which counts against `max_tokens`. With `max_tokens=500`, reasoning eats 2000+ chars and actual content truncates to ~50 chars with `finish_reason: length`. Need `max_tokens>=2000` for ratification prompts.

3. **MiMo wraps JSON in ```json blocks** — The `extract_json()` function must handle markdown code block wrapping. Regex: `re.search(r'```(?:json)?\\s*(\\{.*?\\})\\s*```', s, re.S)`. Always fall through to `{`/`}` boundary extraction as last resort.

4. **Claude `-p` mode hits max_turns on complex prompts** — `claude -p` with structured ratification prompts returns `error_max_turns` even with `--max-turns 1`. Claude's internal reasoning counts as turns. Fix: use `hermes chat -q --provider anthropic` for ratification instead of `claude -p`. Workaround: simplify prompt to bare JSON request if `-p` is required.

4. **GPT-5.5 via openai-codex prefixes output** — May output `⚠️ Reached maximum iterations (1). Requesting summary...` before JSON. The `extract_json()` function must handle text before the JSON object via `s.find('{')` / `s.rfind('}')`.

Recommended 4-model ratification sequence:
```python
# Phase 1: concurrent trio
with ThreadPoolExecutor(max_workers=3) as ex:
    futs = {ex.submit(fn): model for model, fn in [
        ('claude', call_claude), ('gpt', call_gpt), ('deepseek', call_deepseek)
    ]}
    for fut in as_completed(futs):
        # collect results

# Phase 2: MiMo sequential (with 3x retry)
parsed = extract_json(call_mimo_with_retry())
```

Robust `extract_json()`:
```python
def extract_json(s):
    s = (s or '').strip()
    if not s: raise ValueError('empty response')
    try: return json.loads(s)
    except Exception: pass
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.S)
    if m: return json.loads(m.group(1))
    a = s.find('{'); b = s.rfind('}')
    if a >= 0 and b > a: return json.loads(s[a:b+1])
    raise ValueError(f'no json object ({len(s)} chars): {s[:200]}')
```

Full details, detection signals, and code patterns: `references/provider-concurrency-and-token-budget-pitfalls.md`.

## 默认模型组合

默认使用 4 个互补模型：

- Claude Code / Claude: P10 架构、约束归一化、最终 synthesis；适合长上下文和复杂权衡。
- Codex / gpt-5.5: codegen/API/类型/工程落地审查；当前会话若是 Codex，可作为本方模型。
- DeepSeek: 独立低成本 reviewer / adversarial challenger；擅长逻辑漏洞和替代路线，但不要单独仲裁。
- MiMo-v2.5-pro: 低成本 sanity、实现成本/速度/简单性审查；适合快速发现明显问题和成本过高方案。

最小可接受：N=3 且 provider 至少 3 类。用户明确要求 Claude Code+Codex+DeepSeek+MiMo 时，必须 N=4，不得用 quorum=3 偷省一个模型。

执行器并发限制不是降级理由：如果 `delegate_task` 或本地配置最多同时跑 3 个 child/reviewer，就拆成 `3 + 1` 两批执行，并在最终状态里合并 4 票。不要因为 `max_concurrent_children=3` 就把 4/4 认证降成 3/4；缺任一模型时只能标 `not_fully_certified` / advisory。

## 标准流程：8 阶段，不可跳过核心讨论

```
Phase 0: Framing / State
  - 由主模型/编排器准备 state.json：明确 question、repo/context、constraints、acceptance criteria、non-goals、budget、risk level。
  - state.json 是事实输入和落地边界，不是候选方案；必须尽量客观、紧凑、可复现。
  - 主模型同时准备 implementation target / 落地方案骨架：目标文件、验收命令、风险边界、禁止改动项。
  - 计算 state_hash。所有模型看到同一份 state.json，避免上下文不一致。

Phase 1: Blind Seed Proposals
  - 4 个模型独立生成方案，禁止先看彼此答案，避免 anchoring。
  - 每份方案必须包含 assumptions、risks、implementation phases、cost controls、tests。

Phase 2: Normalize + Disagreement Ledger
  - 归一化为统一 schema。
  - 抽取 agreement / disagreement / missing evidence。
  - 建立 issue ledger：每个争议点有 id、severity、owner、status。

Phase 3: Cross-Critique / Challenge
  - 每个模型收到其他模型方案 + disagreement ledger。
  - 对每个其他方案输出 AGREE / AMEND / REJECT。
  - 质疑必须具体：引用原文/代码路径/成本数字/失败模式；必须给 correction 或 experiment。

Phase 4: Rebuttal + Revision
  - 每个模型必须逐条回应别人对自己的质疑：accept / reject-with-evidence / defer-to-risk。
  - 如接受质疑，输出 revision diff；如拒绝，必须给可验证理由。
  - 未回应的质疑不得进入“已认证”。

Phase 5: Supplementary Red-Team
  - 指定 devil's advocate 产出“当前最佳反例”。默认奇数轮 Codex，偶数轮 MiMo；高风险架构可让 DeepSeek 做逻辑红队。
  - 如果出现 novel severity>=3 critique，回到 Phase 3 聚焦该 issue。
  - 如果红队也只能 sign off，进入认证。

Phase 6: Convergence + Ratification
  - 每个模型独立投票：APPROVE / AMEND / REJECT。
  - 认证不是固定轮数，而是满足 stop condition。
  - 任何 severity=5 且未被技术性反驳的 dissent 都阻断认证。

Phase 7: Final Synthesis + Provenance
  - 合并最终方案，记录共识、分歧、采纳理由、未解决风险。
  - 输出可直接实施的 final_design.md / final_plan.json。
```

## 讨论循环

每轮讨论只围绕 unresolved issue ledger，避免全文反复发送：

```
round r:
  1. build_context = compact(problem_statement + current_best + unresolved_issues + prior_resolutions)
  2. challengers critique unresolved issues
  3. owners rebut or revise
  4. arbiter/judge 更新 issue status 和 agreement matrix
  5. red-team 尝试提出 novel blocker
  6. 若满足 stop_condition → ratify；否则继续下一轮
```

推荐上限：MAX_ROUNDS=5。上限只是防无限循环，不是认证条件。
如果达到上限仍有 blocker，输出 `not_certified`，不得谎称“最佳方案”。

## Communication Budget Protocol — 防 token 内耗通信协议

`consult_models.py` 的 discussion round 默认使用 `multi_model_comm_packet_v1`，不要把 `merged_plan`、完整 `evidence_bundle`、完整 transcript 每轮广播给每个模型。

通信规则：
- 首轮 planner 可读取 state；后续 discussion 只收 `manifest_delta` packet。
- `artifact_manifest` 只传 full artifact 的 hash/char/token 统计，不传完整正文。
- `current_best_summary` 只传 patch id、target_file、op、risk、短 rationale、source_hash。
- `round_delta` 只传当前 unresolved issues、上轮 vote 摘要，不传长 reasoning 历史。
- `evidence_summary` 只传 claim/evidence count、grounding status、evidence ids；缺正文时 reviewer 必须输出 `evidence_requests`。
- 每轮 artifact 必须记录 `communication.estimated_chars_saved` / `estimated_tokens_saved`，让 token 成本可审计。
- 只有当 evidence_request 命中并由 orchestrator 执行后，才把新增 evidence 回填下一轮；禁止模型互相转述大段原文。

口令：模型之间传“索引卡 + 差异”，不传“全量小说”。

详细落地规范、telemetry 真实性规则、测试清单见 `references/communication-budget-protocol.md`。

## 停止条件：多方认证“当前最佳方案”

必须同时满足：

1. `approval_count >= N-1`，且 `reject_count == 0`。
2. agreement_matrix 在 problem framing、chosen approach、implementation order 三轴均 >= 0.85。
3. 本轮没有模型提交 revision diff。
4. Phase 5 没有 novel severity>=3 critique。
5. issue ledger 中没有 unresolved blocker；severity>=4 必须 resolved 或 explicitly accepted risk。
6. 每个模型都明确签署：`best_within_constraints=true`，并列出仍可能错的边界。
7. 没有 silent dissent：任何模型提出的质疑都必须收到 owner 回复。

硬上限触发时：
- 若只剩 severity<=2，可输出 certified_with_minor_risks。
- 若仍有 severity>=3 unresolved，输出 not_certified + escalation_needed，不执行实现。

## 质疑规则

禁止“你觉得呢”式泛问。每条 critique 使用结构化 schema：

```json
{
  "issue_id": "I-001",
  "target_model": "claude_code|codex|deepseek|mimo",
  "verdict": "agree|amend|reject",
  "severity": 1,
  "claim": "被质疑的具体主张",
  "evidence": "引用原文/代码路径/成本数字/失败模式",
  "reasoning": "为什么这是问题",
  "correction": "建议修正或替代方案",
  "experiment": "如何验证",
  "novel": true
}
```

规则：
- 每个模型必须给出最佳反方论点；如果无质疑，必须输出 signed_off=true 和为什么无法继续改进。
- 重复质疑无新证据时标记 duplicate，不延长循环。
- 质疑必须可行动：correction 或 experiment 至少一个非空。
- DeepSeek/MiMo 的少数意见不能因模型较便宜而直接忽略；按 severity 和 evidence 质量处理。
- Claude/Codex 也不能以权威身份压制其他模型；最终以 issue resolution 认证，不以模型名认证。
- 当把本协议落到本地大脑时，必须有独立可检索的原则卡覆盖“少数意见 / 模型名不等于权威”。推荐 atom 标题包含“少数意见：模型名不是证据，模型名不等于权威”，避免搜索只命中任务日志而不命中原则本体。

## 输出格式

最终输出必须包含：

```json
{
  "status": "certified|certified_with_minor_risks|not_certified",
  "models_consulted": ["claude_code", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"],
  "rounds_used": 3,
  "agreement_matrix": {"framing": 0.0, "approach": 0.0, "implementation_order": 0.0},
  "final_design": {},
  "issue_ledger": [
    {"id": "I-001", "status": "resolved|accepted_risk|unresolved", "severity": 3, "resolution": "..."}
  ],
  "ratification_votes": [
    {"model": "...", "vote": "approve|amend|reject", "best_within_constraints": true, "reasoning": "..."}
  ],
  "provenance": ["which model contributed which key insight"],
  "remaining_risks": []
}
```

## Dual-track anti-drift landing

当用户要求“长时自主开发防漂 / 双轨防漂 / estimator-controller 解耦 / Hermes 融合”时，不要只跑 LLM 互检。先把事实分层：

- Track A deterministic oracle：类型、测试、lint、scope contract、anchor lock、架构/视觉等机器可复现检查。Track A fail 一票否决，不能被多模型同意覆盖。
- Track B LLM critic：`consult_models.py --discussion`、DeepSeek/Codex/MiMo/Claude 互审、semantic drift/scope creep/anchor violation 语义嗅探。Track B fail 而 Track A pass 时默认 ask/escalate，而不是直接 block。
- Judge：合并 truth table；输出 JSON artifact，进入本地 brain/evidence index。

Hermes-native 起步脚本：

```bash
python3 ~/.hermes/scripts/anti_drift_guard.py --root /path/to/repo init --goal "immutable goal"
python3 ~/.hermes/scripts/anti_drift_guard.py --root /path/to/repo check-anchors
python3 ~/.hermes/scripts/anti_drift_guard.py --root /path/to/repo scope --contract .omc/state/tasks/TASK.contract.json
python3 ~/.hermes/scripts/anti_drift_guard.py --root /path/to/repo judge --track-a /tmp/track-a.json --track-b /tmp/track-b.json
python3 ~/.hermes/scripts/anti_drift_guard.py --root /path/to/repo consult-state --track-a /tmp/track-a.json --out /tmp/drift-review-state.json
```

核心约束：
- `.omc/anchors/.lock` 是不可变锚的 sha256 ledger；agent 修改 anchor 必须 halt/re-lock by explicit decision。
- task contract 用 JSON：`expected_files`、`allowed_globs`、`forbidden_files`、`forbidden_globs`、`loc_budget`。
- `consult-state` 只生成 evidence-first state；是否调用四脑由 orchestrator 决定，避免每次 edit 都烧多模型成本。
- Track A/Track B 的证据可以通过 `brainctl.py` 同步进 `~/Documents/brain`，SQLite index 只是可重建派生层。

## References

- `references/current-code-certification-after-amend.md` — post-ratification amendments or AMEND/not_certified current-code runs invalidate certification claims until blockers are converted into deterministic evidence and a fresh target-bound `discussion_result.json` plus `final/certification_manifest.json` pass with the exact 4-model set.
- `references/grounded-not-certified-amend-loop.md` — when truth evidence is grounded but T3 ratification is `not_certified`, inspect issue ledger/manifest, convert severity>=3 AMENDs into deterministic tests/evidence, commit, update state to current commits, and rerun fresh T3.
- `references/taskpool-artifact-verification-regression.md` — taskpool pass-state hardening: frontmatter `multimodel_status: certified` is only a hint; load the local `discussion_result.json`, bind it to the exact task, require canonical 4/4 votes for closeout, and repair stale/mismatched task notes to `not_certified` with proof-log caveats.
- `references/taskpool-multimodel-autorun-pitfalls.md` — **9 大 pitfalls**: build_state claims 注入、tick errors 初始化顺序、autonomy-write-allowlist、state_path 清理、1200s timeout、关键词误报爆炸、gate 双形态、convergence 统计解读、allowlist 配置。
- `references/taskpool-autonomy-readiness-and-evidence-spine.md` — taskpool autonomy readiness certification pattern: evidence-spine heartbeat, autonomy-readiness artifact, exact claim-linked T3 evidence, hollow-shell ratification selftests, proof-audit false-positive handling, timeout handoff, and 4/4 certification closeout discipline.
- `kanban-orchestrator:references/local-taskpool-system-repair.md` — system-repair pattern after taskpool status checks: fix deterministic proof/selfcheck/evidence/envelope gates first, then run a fresh current-state T3 certification; a grounded-but-not-certified planning tick can be used as advisory provenance but not as final certification.
- `references/long-term-taskpool-autorun-activation.md` — runbook for starting long-term local-brain taskpool autorun: prerequisite gates, no-arg cron wrappers, safe/autorun heartbeats, env-gated multimodel wrapper, cron proof, fail-closed `policy_missing`, closeout evidence, and rollback.
- `references/taskpool-pua-loop-hardening.md` — closeout pattern for PUA-loop/taskpool autonomy hardening: evidence-spine gate_status enforcement, cron secret redaction, malformed ratification artifact fail-closed tests, real-vault mission envelope repair, and scoped commit discipline.
- `references/provider-adapter-fallback-ratification.md` — consult_models.py adapter fallback
- `references/claude-code-wrapper-runtime-errors.md` — Claude Code `--output-format json` wrapper decoding: classify `is_error` / `api_error_status` runtime failures separately from malformed model JSON, with regression tests for planner/discussion paths.
- `references/direct-multi-model-ratification.md` — **Direct API ratification loop** with provider quirks: DeepSeek needs max_tokens>=2000, MiMo must be sequential (concurrent=empty), MiMo wraps JSON in code blocks. The 3+1 concurrent+sequential pattern, amend loops, certification levels.
- `references/vx-state-function-and-auto-trigger-chain.md` — **V(x) Lyapunov health function** from Complex Giant Systems theory, full auto-trigger chain (orchestrator→pipeline_tick→envelope_executor→kanban_bridge), PUA-loop + multi-model verification pattern, coverage audit methodology.
- `references/task-flow-deadlock-detection-and-fix.md` — **Task flow deadlock**: controller claims but never delegates, stale claims block dispatch. Detection via stale_claim field, fix via force-release + delegate_to_worker in controller.
- `references/iron-plate-consolidation-pattern.md` — **Iron plate consolidation**: 5-layer architecture (ops/health/evolve/watchdog/report) to merge 20+ cron jobs. GenericAgent patterns: 5-layer memory, task→SOP crystallization, file IPC sub-agents.

## Hermes 当前落地方式

`consult_models.py` 已落地基础 DiscussionOrchestrator 能力：state builder、issue ledger、ratification gate、`--discussion` CLI、DeepSeek direct API fallback。

### 1. 主模型/编排器生成 state.json

```bash
python3 ~/.hermes/scripts/consult_models.py state \
  '你的问题/落地目标' \
  --context-json '{"repo":"/path/to/repo"}' \
  --constraint 'use four models' \
  --accept 'ratification gates pass' \
  --file consult_models.py \
  --verify 'python3 -m unittest ~/.hermes/scripts/test_consult_models_integration.py -v' \
  --out /tmp/mm-state.json
```

### 2. 四模型 fan-out + 讨论认证

```bash
python3 ~/.hermes/scripts/consult_models.py run /tmp/mm-state.json \
  --tier T3 \
  --quorum 4 \
  --discussion \
  --max-rounds 5 \
  --keep
```

### 3. 离线/测试模式

```bash
HERMES_MULTI_BRAIN_OFFLINE=1 python3 ~/.hermes/scripts/consult_models.py run /tmp/mm-state.json \
  --tier T3 --quorum 4 --shadow --discussion --max-rounds 2 --keep
```

输出 tick 目录中会包含：
- `plans/*.json`：各模型 seed proposal。
- `merged_plan.json`：consensus merge。
- `discussion_result.json`：status、issue_ledger、ratification_votes、agreement_matrix、remaining_risks。

If the outer command times out after planner fan-out but before discussion/ratification finishes, inspect the tick directory before rerunning:

```bash
find ~/.hermes -maxdepth 1 -type d -name 'tick-*' -mmin -60 | sort | tail -5
ls ~/.hermes/tick-*/plans/*.json ~/.hermes/tick-*/merged_plan.json
```

Before `resume-discussion`, verify the tick belongs to the exact target state:
- compare `merged_plan.json.meta.state_hash` with the state file hash when available;
- inspect `evidence_bundle.claims` / `evidence_bundle.evidence` for the target repo, project name, and expected claim IDs;
- reject any tick whose claims mention another project, orchestrator, or old task even if it is the newest tick;
- if a resume output contains unrelated claims, mark it contaminated/not-certified and rerun with a fresh state rather than citing it.

Target-bound artifact hard gate for taskpool/Lark closeout:
- Do not trust a task note's `multimodel_status: certified` or `multimodel_ratification_artifact` at face value. Open the artifact and prove it is bound to the exact task before using it for done/closeout.
- Required checks: explicit task binding fields (`task_id`/`target_task_id`/`task_path`/nested context equivalents) match the target task, no explicit binding candidate points at another task, `models_consulted` and `ratification_votes` contain the expected full set, artifact claims/evidence paths mention the target task/proof/project rather than an unrelated task, and the state/question/target identifiers match the current decision.
- For this user's Lark/taskpool closeout, the expected full set is the canonical four-model panel: Claude + GPT/Codex + DeepSeek + MiMo. A 3/4 artifact is advisory/not-certified, not a closeout certificate, even if an older quorum/fanout field says certified.
- If `brain_task_orchestrator.py ratification-gate` returns PASS on a mismatched artifact, treat that as an infrastructure verifier gap, not as permission to close the task. Report `not_certified_for_target`, keep the task in `review`/`blocked`, and add/plan a target-binding verifier before automatic done/writeback.
- For diagnosis-only questions such as "is task Score X stuck?", separate facts: execution state (`running`/`claimed`/`stale_claim`), closeout state (`review`/human gate), implementation evidence, and certification artifact validity. A task can be not stuck and still not done because the correct gate is waiting for human/code review or remote/Lark closeout.
- When building a diagnostic state, avoid claims phrased as prohibitions that evidence objects can accidentally `contradict`; express positive factual claims (e.g. "old artifact lacks DeepSeek and is target-mismatched") so the truth gate does not fail due to claim/evidence wording rather than the underlying diagnosis.

Interpretation:
- `plans/*.json` for all requested models + `merged_plan.json` means fan-out produced useful evidence.
- To verify Claude Code specifically participated, inspect `plans/claude-*.json` and require `meta.adapter == "claude-code"` (or the expected Claude adapter), a non-empty `diagnosis`/`patches`, and a real `latency_ms`; this proves Claude contributed to seed planning, but does **not** prove final ratification.
- Missing `discussion_result.json` or timeout during consensus means the result is **weak consensus / not fully ratified**, even if 4 models answered.
- If one planned model failed (for example MiMo provider/adapter returns `Param Incorrect` / unsupported provider) while Claude/Codex/DeepSeek produced plans, report participant status per model: `claude_code=participated`, successful planners as advisory, failed planners as missing/failed, and keep final status below full four-model certification.
- Report `fanout_status`, `consensus_verdict`, `unanimous_count`, `majority_count`, `minority_count`, and `arbitration_needed` from `merged_plan.json`. Some merged-plan fields may be nested under `merge_info`; inspect both top-level and nested keys rather than assuming a flat schema.
- After `resume-discussion`, run or inspect `final/certification_manifest.json` when available. Treat it as the conservative gate if it reports count inconsistencies, unsigned `best_within_constraints`, adapter failures, or `discussion status is not_certified`, even when `fanout_certification.certified=true` and truth grounding is 1.0.
- Do not claim full multi-model certification unless the ratification artifact exists and stop conditions pass.
- Prefer summarizing existing artifacts over immediately rerunning an expensive T3 discussion; rerun only if the missing ratification materially changes the decision.

For long-running or repeatedly-timed-out discussions, see `references/long-running-discussion-and-resume.md` and `references/current-code-certification-after-amend.md`. Key point: `--max-rounds` and `--timeout` can extend discussion, but online discussion calls models serially and may retry JSON parsing, so run long T3 certification in the background with `--keep` and inspect `discussion_result.json` afterward. If the session/tool-call budget is near exhaustion, do not start a fresh long T3 run unless you can still poll/read the verdict; prefer preserving the exact state path, tick/process id, and `not_certified_yet` handoff. If interrupted while the background run is still running, the final answer must say ratification is incomplete and must not proceed to commits or imply certification. If a deterministic patch or amend happens after a prior certified tick (even a small safety/redaction fix), that old artifact becomes provenance/advisory for the previous code state only; build a fresh current-code state and require a new `discussion_result.json` + `final/certification_manifest.json` before claiming 4/4 current-code certification. If the blocker is missing runtime evidence, run an Evidence Request Fulfillment Loop before adding more rounds.

For evidence reports, rebase gap analysis, and implementation-order decisions, do not let a silent/long-running T3 consult block deterministic progress. Start `consult_models.py` with a saved state file and `--keep`, continue collecting source/test evidence, and if the consult produces no stdout/artifact within the task budget, label it as `started/no_ratification_artifact` or `not_certified`, stop/clean the background process, and proceed with a report grounded in code, git, docs, and test outputs. Never upgrade such a run to multi-model certification; use it only as advisory provenance if artifacts appear later. If the process tool cannot kill the background job (for example a local `psutil` import failure), clean it with terminal/PGID (`pgid=$(ps -o pgid= -p PID | tr -d ' '); kill -TERM -$pgid`).

For low/medium-risk scoped closeouts where `plans/*.json` and `merged_plan.json` exist but `discussion_result.json` is missing, use `references/fanout-advisory-closeout.md`: treat planner quorum as advisory, inspect reviewer `evidence_requests`, fulfill them with deterministic gates (tests/compile/no-writeback/no-secret/scoped git diff), and report `weak_consensus / not fully ratified` rather than rerunning expensive discussion by default. If you create guard tests for no-writeback/no-secret scans, avoid embedding the forbidden strings literally in the test source or later grep-based gates will self-match; construct those strings dynamically.

For autonomous loop work where the user wants every iteration checked by multiple models until they agree to stop, use the loop-runner pattern in `references/local-brain-taskpool-autorun-certification.md`: deterministic gates first, claim/evidence state second, live `consult_models.py --tier T3 --quorum 4 --discussion --keep` third, then an explicit `verify_ratification()` / `should_continue()` API that converts `discussion_result.json` into `LOOP_DONE` or `continue_loop`. If the request is to check taskpool progress or assess long-running self-run readiness, first use `references/taskpool-autorun-status-review-and-certification.md`: collect the read-only status suite, prove work-lane preemption with `parallel-dispatch-dry-run`, and package claim-linked evidence before T3. Do not pass only a raw `/tmp/status.json` via `--file` and expect truth certification; unlinked files commonly produce `truth_status=unsupported` / `evidence_coverage=0.0` and must be reported as advisory/not-certified. If the first live quorum flags ambiguity in the stop gate, patch the verifier API and rerun; do not claim completion from deterministic gates alone. If later live rounds fail because no-action advisory follow-ups are misclassified as implementation blockers, because an outer consult timeout raises a traceback, or because `consult_result.discussion_result_path` is missing/empty (`Path("")` becomes `.`), harden the merge/verifier path with regression tests and preserve `not_certified`/timeout/missing-discussion as structured fail-closed artifacts.

Local task-pool scheduling pitfall: recording a blocker or `returned_for_backend_completion` in a project Workpad/docs is evidence, not an executable queue item. Before telling the user a returned task will be modified automatically, verify it is a canonical task note under `~/Documents/brain/05-实践与项目/tasks` and appears in `brain_task_orchestrator.py dispatch-dry-run --json` / `taskpool_watch_report.py`; otherwise say it will not auto-run yet and either add a prioritized task via `brain_task_orchestrator.py add ...` or start the implementation immediately. Also report the relevant cron jobs (`local-brain-taskpool-auto-completer`, occasional report) with `next_run_at` so “什么时候会修改” is grounded in scheduler state, not assumptions.

Task-pool architecture-gate pitfall: when adding a new fail-closed metadata contract such as `lane: evolution` requiring `architecture_target` / `capability_delta` / `anti_drift_check` / `acceptance_evidence`, do not stop at temp-vault unit tests. Run the real canonical vault selfcheck/lifecycle with `HERMES_BRAIN_VAULT=/Users/charles/Documents/brain`; legacy Markdown tasks may immediately become invalid. Either provide a migration/repair command or patch the affected canonical task notes with truthful alignment fields, then rerun `selfcheck --json` and `lifecycle --json`. Treat `dispatch-dry-run` PASS alone as insufficient because it can skip misaligned historical tasks while `selfcheck` correctly fails.

Ratification verifiers must validate participant identity, not just counts. For full T3/four-brain certification, require the exact planned canonical participant IDs (for this Hermes stack: `claude-opus-4-7`, `gpt-5.5`, `deepseek-v4-pro`, `mimo-v2.5-pro`) unless a different expected set is explicitly configured in the state; family/role aliases such as `claude`, `codex`, `deepseek`, `mimo`, provider substrings, or same-family shadow names are not enough at the certification boundary. Approval votes must come from the exact consulted canonical IDs, every expected participant must either approve or be represented by an explicit fail-closed missing-vote reason, duplicate approval identities must block certification, and fake/unconsulted voters must not satisfy quorum. Do not derive quorum solely from self-attested `models_consulted`; missing the planned fourth model must fail closed rather than silently lowering the approval requirement. Truth gates must require explicit positive evidence fields: `can_certify_truth`/equivalent must be true, and negative-evidence arrays such as `unsupported_high_severity_claim_ids` and `contradicted_high_severity_claim_ids` must be present and well-typed; missing arrays are malformed evidence, not empty evidence. For PUA-loop/taskpool closeout gates, status/votes/truth shells are still insufficient: require explicit `criteria_satisfied` (accuracy, long-term goal, one-shot landing) or equivalent `final_design` proof, including a non-empty next slice, acceptance evidence, rollback boundary, and long-term goal alignment. If these fields are missing, return `continue_loop`; do not let a `certified` label stop the loop.

For router/readiness certification in autonomous or budget-handoff paths, treat monitor availability and semantic gate fields as first-class evidence. Readiness is not fail-closed if it only checks `dominance_warning`; it must also fail on monitor returncode != 0, empty/invalid JSON, missing required fields, `gate_failed`, warning counts, and route-diversity signals. Preserve parseable non-zero monitor output as actionable gate evidence instead of collapsing it to `*_unavailable`; only malformed/missing required fields should become unavailable. Accept documented JSON shape drift deliberately (for example `route_diversity_signals` may be an empty list or a keyed dict) and add a named regression for the observed shape. Reporting eligible alternates is advisory only: certification artifacts should explicitly prove no automatic rebalance or route mutation occurred.

For provider quota observability, exact evidence must not be downgraded by later empty response headers. Use `references/provider-quota-observability-and-rebalance.md`: preserve fresh higher-confidence balance/window evidence against lower-confidence unknown/header-empty snapshots, still let 429/rate-limit/exhausted safety blockers overwrite OK evidence, make refresh actions actionable rather than stale, and use bounded real smoke/warm-up calls (not synthetic traces) to resolve diversity dominance before re-running router/autonomy gates.

- `references/autonomous-certification-scope-and-provider-evidence.md` — certification must be scoped to explicit provider set/mode/write surfaces/budget/revocation conditions, quota-unobservable providers cannot participate in clean budget-handoff/autonomous-execution certification, and deterministic gate passes do not override reject votes or unresolved severity>=3 ratification risks. Prefer a provider-limited certification claim over globally certifying Hermes when Claude/Codex/MiMo quota evidence is unavailable; otherwise label the result as risk-accepted limited autonomy or truth-grounded advisory.
- `references/multi-model-root-cause-analysis.md` — **Root cause diagnosis with 6 theoretical frameworks**: Kahneman (System 1/2), Meadows (leverage points), Ousterhout (tactical/strategic), Pragmatic Programmer (DRY), Fowler (code smells), Evans (ubiquitous language). Use when user asks "why did the agent miss this?" or after a returned-for-improvement task.

Router quota/readiness success payloads must use a strict positive schema, not truthiness or defaulted success shells. A payload such as `{"ok": true}` is incomplete evidence and must fail closed. Require explicit `ok is True`, `status in {PASS, OK}`, `failure_count == 0` as a real non-bool int, and `failures == []` as an explicit list; do not default missing `status`, `failure_count`, or `failures` to passing values. For autonomy/budget-handoff readiness, also bind the artifact to the caller's expected threshold: `quota.min_confidence` must be present, finite, in range, and `>= expected_min_confidence`; per-model `passes`, `snapshots`, and `observability_evidence.by_model` must cover exactly the checked model set and include explicit model/status/confidence/timestamp evidence. Reject aggregate-only observability counts, hollow snapshots, missing confidence defaults, or self-declared `min_confidence: 0.0` shells even when `ok=true`. When tightening this gate, update old happy-path fixtures to include the full strict schema rather than weakening the verifier.

For long PUA-loop certification/fusion sessions, do the scoped commit as soon as deterministic gates pass and the evidence note is updated; do not leave commit until after extra exploratory checks if the tool/context budget is near exhaustion. Before committing inside a dirty Hermes repo, run `git diff --cached --stat` and `git status --short -- <task paths>`, `git restore --staged .` if unrelated paths are staged, then re-add only scoped task files. Immediately after commit, run `git log -1 --oneline` plus `git status --short -- <task paths>`; if any task path is still dirty because late fixes/tests landed after the commit, stage only those paths and `git commit --amend --no-edit`, then re-check. Delete or ignore transient runtime artifacts (for example synthetic selfcheck JSON under `~/.hermes/state/`) before declaring the scoped commit clean. If interrupted before commit or before this post-commit clean check, final output must say commit is not done/clean and list exact scoped paths plus next commands; never imply landed/local committed from tests alone.

For Hermes post-update fusion reviews (e.g. new v0.13 surfaces need integration with existing L0-L5+LX/local-brain/taskpool architecture), use `references/post-update-fusion-verifier-gates.md`: collect claim-linked update/health/provider evidence, fix verifier gaps such as p10-health self-test parser drift and model-diversity dominance false-health labels, map new upstream surfaces onto existing mechanisms instead of duplicating them, and keep the outcome as `truth_grounded_advisory` / `not_certified_for_autonomous_execution` until router diversity enforcement, provider/quota confidence, and autonomy precondition gates are actually fail-closed. When the fusion touches autonomy/write surfaces, also use `references/autonomy-write-guard-caller-integration.md`: prove the real caller invokes `guard_or_raise` before mutation, keep `dispatch-hint` bounded to claim+handoff+proof, and require surface allowlist even in dispatch-hint mode.

When repeated timeouts or recurring governance needs make this a long-term infrastructure project, use `references/resumable-multimodel-certification-system.md`: treat the target as RMCS (checkpoint → audit-certification → resume-discussion → background runner → evidence-first split), not as a one-off timeout increase. Defer dependent high-risk hook/state automation such as `TaskCreate -> next-round ralph` until RMCS P0-P2 pass.

注意：
- `~/.hermes/config/quorum.yaml` 的 T2/T3 虽列出 4 个 planners，但默认 quorum=3 会截断为 3 个模型；完整四模型必须 `--quorum 4`。
- 第三方框架/仓库评估可用多视角 delegate reviewers 作为轻量“多脑”替代，但最终必须标注为 multi-view review，而不是完整 `consult_models.py --discussion` certification；若用户要求真正四模型认证，仍需运行 `consult_models.py` 并保留 artifact。
- 从 Ruflo/外部编排框架评估中采纳治理原语时，优先 Hermes-native 小切片落地，不整体引入第三方运行时。P0 长期进化控制面是 `~/.hermes/scripts/long_evolution_guard.py`：
  - `inventory` / `witness` / `verify`：生成 capability inventory、本地 HMAC witness、检测 tool/skill/script 漂移。
  - `claim` / `claim-status` / `release` / `handoff` / `steal` / `ledger-verify`：给 cron、subagent、多模型任务建立 claim/lease/handoff ledger，使用 SQLite `BEGIN IMMEDIATE` 做本地互斥，并用 event hash chain 做篡改检测。
  - `budget-check`：对递归委派、多模型 fanout、agent 调 agent 强制 max_hops/max_tokens/max_usd/max_tool_calls/max_wall_seconds；缺失/NaN/负数/超限都 fail-loud。
  - `verify` 必须重建当前 inventory，检测 `inventory_drift` / `added_capability` / `hash_mismatch`，避免 witness 只检查旧清单。
  - 运行模式必须 local-first、no network、禁止 shell 模式执行；仅允许 bounded `git rev-parse HEAD` 作为 provenance；witness key 是本地 runtime secret，不提交 git。
- Claude Code 需要完整能力时优先 `claude -p`；Hermes Anthropic adapter 是 fallback。
- Codex/gpt-5.5 走 openai-codex provider。
- MiMo 走 xiaomi provider。
- Hermes CLI 当前不接受 `--provider deepseek` 时，`consult_models.py` 对 `provider: deepseek` 使用 DeepSeek direct API fallback。
- 所有跨模型上下文必须 structured summary relay；不要假设 provider 共享上下文。
- Claude budget 是硬约束；预算不足时可降级，但必须在 final output 写明缺席模型，不能声称完整四模型认证。
- `delegate_task`/子代理审查可以作为补充 reviewer，但不是完整 `consult_models.py --discussion` 的替代品；如果任何 reviewer 超时、被截断或未完成，最终状态必须降级为 `certified_with_minor_risks` 或 `not_certified`，并在 provenance 中写明缺席/超时模型和由主编排器补充的证据。
- 对本地任务池/cron/autorun 这类状态机自动化，区分“事实诊断已 grounded”和“实现方案已 certified”：truth gate 证明缺口存在，不等于 patch plan 可以落地。若 `discussion_result` 里 severity>=3 issue 未解决、`final_design.patches=[]` 但 planner patch summary 显示 `implementation_required`，最终保持 `not_certified` 或 `amend`。尤其不要把“自动执行 Markdown task body 并自动 done”当成认证方案；正确方向是 fail-closed 的 `auto-claim-and-handoff` + 外部 bounded runner + proof-gated `review -> done`。具体实现/验收模式见 `references/local-brain-taskpool-autorun-certification.md`：默认关闭、allowlist 默认拒绝、safe tick 默认 hint-only、autorun done 必须 proof hash-chain、`proof-check` 要审计 persisted autorun closure、提交时必须 scoped add 避免带入 Hermes runtime 脏文件。

## 何时使用

使用：
- 架构设计、新系统/模块、影响 >3 文件的关键决策。
- 高风险：安全、可靠性、成本、数据迁移、不可逆操作。
- 第三方 agent/orchestration 框架评估需要多视角时：至少拆成 architecture、security/supply-chain、product/workflow 三个独立 reviewer；固定 commit 和证据文件；最终 synthesis 必须区分"可借鉴治理原语"和"不应整体引入/需沙箱"的风险。
- 用户明确要求"多模型讨论 / 真多模型 / 四脑 / 来回讨论 / 多方认证"。
- 用户问"为什么你没发现这个"或要求分析架构盲点的根因 — 使用 `references/multi-model-root-cause-analysis.md` 的 6 理论框架诊断模式。

不用：
- 简单 bug fix、机械配置、低风险单文件改动。

## Cross-Cutting Concern Recognition (交叉关注点识别)

When a user or Lark task describes a **point fix** (e.g., "this input field accepts emoji"), the agent MUST classify the problem before executing:

1. **Point fix**: isolated to one screen/component, no similar patterns elsewhere → fix locally.
2. **Cross-cutting concern**: validation, security, error handling, data transforms, i18n, logging → must be implemented as **shared infrastructure**, not point fixes.

Classification signals:
- Same pattern duplicated in 2+ files (e.g., `cleanText()` in multiple screens)
- Existing shared infrastructure for the same concern (e.g., `validators.ts` already has `isValidEthAddress`)
- The fix prevents a class of problems, not a single instance
- Defense-in-depth requires the same rule at multiple layers (frontend + backend)

When a cross-cutting concern is identified, the correct action is:
1. Extract to shared infrastructure (e.g., `validators.ts`, `utils.ts`)
2. Update all existing consumers to use the shared version
3. Add tests at the infrastructure level
4. If backend exists, add matching validation as defense-in-depth

This pattern was established after the agent followed a Lark task literally ("fix bank name emoji validation at one location") without recognizing that validation is infrastructure. The user corrected: "有些对于项目属于基础设施或者常规限制，不能因为任务只说了一个地方就只改这一个地方."

**Theoretical grounding**: Kahneman's System 1 (literal task following) vs System 2 (architectural pattern recognition). Donella Meadows' leverage points: operate at "system structure" level, not "parameter tweaking." Pragmatic Programmer DRY principle.

For UVISA specifically: `src/lib/validators.ts` is the shared validation infrastructure location, `src/lib/utils.ts` is for general text utilities.

## 经验教训

1. 两模型验证不是讨论；没有 rebuttal/revision 就不是 debate。
2. quorum 列出 4 个模型不等于实际调用 4 个；检查 quorum 截断。
3. 停止条件不是"跑够 2-3 轮"，而是多方认证 + 无新高严重质疑。
4. 强模型的结论也必须经 issue ledger 验证；模型名不是证据。
5. 为防 token 爆炸，后续轮只传 unresolved issues + compact current_best，不传全量历史。
6. 到达 MAX_ROUNDS 仍有 blocker 时必须 `not_certified`，不能为了结束而声称最佳。
7. If a current-code run returns `AMEND` / `not_certified`, close it by reading the issue ledger, adding deterministic regression evidence for concrete blockers, committing/amending the scoped fix, then rerunning a fresh target-bound 4/4 tick. Do not reinterpret an AMEND tick as certification.
8. 评估 GitNexus 这类 code-intelligence MCP 时，最值得借鉴的是协议和 guardrail：impact-before-edit、detect_changes-before-commit、stale-index gate、contract_id、tool_map/shape_check。默认做 Hermes-native 方法论提取，不整体引入第三方运行时；RRF 只能排序证据，不能认证真理。
9. T2/T3 fanout 后如果只有 `plans/*.json` / `merged_plan.json`、没有 `discussion_result.json`，最多是 advisory；按 `references/fanout-advisory-closeout.md` 执行证据请求和确定性 gates，不要把 planner quorum 当认证。
9. 对运维治理类问题（如 FD exhaustion），即使 discussion/consensus 超时，也要读取每个 planner 的 `plans/*.json`，抽取交集：通常可安全落地"观测/报告/后续证据收集"这类非破坏性治理切片；但必须明确标注 `weak_consensus / not fully ratified`，禁止落地 auto-restart、kill、自动改状态等破坏性动作，直到 ratification 和确定性 gates 都通过。
10. MiMo 在 4 模型并发 ratification 时返回空响应（HTTP 200 + finish_reason=stop + 空 content）。必须串行执行：先并发 Claude+GPT+DeepSeek，再单独跑 MiMo。Retry 逻辑不够，只有串行才能解决。
11. DeepSeek reasoning_content 和 content 共享 max_tokens 预算。max_tokens=500 时 reasoning 占 400+ tokens，content 被截断。ratification 场景需 max_tokens>=2000。
12. MiMo 即使在 prompt 中明确要求 "no markdown" 仍会用 ```json 包裹输出。extract_json 必须处理代码块。
13. 多方向 ratification 中部分方向 amend 时，不要重跑全部方向。提取 amend 反馈的具體数字护栏（timeout/retry/threshold），修订后只重跑该方向，最后做一轮合并确认。详见 `references/multi-direction-amend-loop-pattern.md`。
14. 4 模型存在时必须 4/4 全跑，不得只跑 2 个就声称认证。串行模式: 并发 Claude+GPT+DeepSeek → 串行 MiMo。Claude 用 `hermes chat -q` 而非 `claude -p`（后者对复杂 prompt 触发 max_turns）。
15. 覆盖率审计必须区分"未覆盖"和"已替代/已内嵌"。旧脚本被新组件替代不算 gap；功能内嵌于其他组件也算 covered。只有真正的功能缺失才算未覆盖。
16. 任务流转死锁检测: 当 orchestrator 显示 claimed 任务数 > 0 但 dispatchable 减少、且无 RUNNING 状态时，用 `stale_claim` 字段诊断。修复: `release --force --reason` 释放死锁，然后修复 claim→delegate 断裂。根因通常是 controller 只 claim 不 spawn worker。详见 `references/task-flow-deadlock-detection-and-fix.md`。
17. "铁板"架构整合: 当 cron jobs 超过 20 个且有明显冗余/缺口时，按 5 层 (ops/health/evolve/watchdog/report) 合并。多模型分析应同时审计冗余(R1-Rn)和缺口(G1-Gn)，提出 N→M 整合方案。GenericAgent 的文件IPC子代理和任务后结晶模式值得采纳。详见 `references/iron-plate-consolidation-pattern.md`。
18. 工作任务需要项目画像注入: worker 执行前必须加载 project-profiles/{project}.json，包含 tech_stack/conventions/test_cmd/acceptance/forbidden。没有画像的任务用 hermes.json 默认画像。画像驱动 worker 行为，不是装饰。
19. 任务完成必须多模型验证: delegate_to_worker 输出后，用 verify_with_models() 让 GPT+MiMo 独立审查 proof 是否满足 acceptance criteria。只有 verified=true 才标记 DONE，否则 FAILED。单模型说"done"不算数。
20. 任务池需要 Guardian 守护进程: 专用 cron (every 10m) 自动检测并修复 stale claims、stuck envelopes、flow 停滞。没有 guardian 的任务池会反复死锁。详见 `references/task-pool-guardian-pattern.md`。
21. 能力路由: 按任务类型选择执行模型。代码类(修复/实现) → GPT-5.5(max_turns=30, timeout=600s)，分析类(评估/方案) → MiMo(max_turns=15, timeout=300s)。不要用同一模型同一配置执行所有任务。
22. 自优化验证闭环: verify_with_models 拒绝后，不是直接 FAILED，而是进入自优化循环: (a) save_rejection 记录拒绝历史; (b) analyze_rejection 识别模式(missing_build/test/screenshot/evidence); (c) generate_enhanced_criteria 从 4→8 criteria; (d) update_project_profile 将学到的规则写入画像; (e) retry max 3 次。安全: 不扩展 scope 只增强 evidence，3 次失败后人工介入。详见 `references/self-optimizing-verification-loop.md`。
23. 关键词触发误报爆炸: 在同类任务池(如全部 Hermes 开发任务)中，宽泛关键词(evidence/truth/architecture/skill/taskpool/方案/落地/loop/workflow)命中率可达 60-98%，等于没有区分度。正确模式是结构性优先+关键词补充: 强结构信号(P0+evolution/retry≥2/stale_claim)直接触发；弱结构信号需≥2个才触发；关键词仅在已有结构信号时补充、且仅搜索 title+concepts(不含 body/metadata)。部署前必须做关键词命中率分析，移除>50%命中的噪音词。详见 `references/local-brain-taskpool-autorun-certification.md` 的 "Intervention trigger design" 节。
24. ratification gate 必须支持双形态: consult_models.py 的 discussion 输出结构随版本演变。gate 必须同时支持 Shape A (显式 criteria_satisfied + final_design{next_slice,acceptance_evidence,rollback_boundary}) 和 Shape B (从 evidence_bundle.grounding/fanout_certification/verification/rollback_signal 推导)。truth gate 必须支持嵌套 truth_assessment 结构。如果 gate 只支持一种形态，另一种形态的 discussion 会全部 FAIL 即使模型已全票通过。
25. 收敛统计是任务池健康度的核心指标: multimodel_convergence_stats() 提供 total_active/passed/triggered/pass_rate/trigger_rate。pass_rate=0 意味着没有任何任务通过多模型认证；trigger_rate>0.8 意味着几乎所有任务都需要介入，可能是触发条件太松。这些指标应暴露在 dry-run 和 tick 输出中，便于监控。
26. 多模型自动执行必须有 env var 门控: HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 控制 multimodel-intervention-step。未设时返回 SKIP（不报错）。tick 集成时 allowed_statuses 必须包含 SKIP，否则 tick 会把未激活的 step 当 ERROR。shell=True 用于 subprocess 支持 && 链式命令（如 mkdir -p && python3 consult_models.py state ...）。gate PASS 后自动写入 task frontmatter（multimodel_status/certification_status/multimodel_ratification_artifact）。详细 pitfalls 见 `references/multimodel-intervention-step-pitfalls.md`（shell=True、state_path 清理、1200s timeout、allowlist、tick SKIP）。
27. build_state_command 必须注入显式 --claim 标志: consult_models.py state 无 --claim 时 truth_status=no_claims，gate 必然 FAIL。至少注入 3 个 claims 与 gate 的 criteria_satisfied 三轴对齐：C-001 accuracy（task decomposition）、C-002 one_shot_landing（next slice exists）、C-003 long_term_goal（lane/project preserved）。claims 在 discussion 阶段被模型验证后 truth_status 从 no_claims → unsupported → grounded。
28. dispatch tick 变量初始化顺序: errors = [] 必须在 multimodel_step block 之前初始化。Python 局部变量作用域在函数级，if block 内引用外层变量要求变量已赋值。症状：UnboundLocalError: local variable 'errors' referenced before assignment。
29. autonomy-write-allowlist.json 是 auto-claim 的前置条件: auto-claim-and-handoff 检查 autonomy_write_guard，其中 surface_allowlisted 需要 /Users/charles/.hermes/config/autonomy-write-allowlist.json 包含 "taskpool" 和 "kanban-worker"。文件不存在或为空 → FAIL_CLOSED。
30. state_path stale directory 清理: consult_models.py --out 要求目标是文件路径。如果之前的 mkdir 或错误操作把 state_path 创建为目录，IsADirectoryError。step command 中 build_state 前检查 state_path 是否为目录，是则 shutil.rmtree。
31. discussion timeout 经验值: 4 模型 × 5 rounds 每轮 ~2-3 分钟 = 10-15 分钟。DEFAULT_TIMEOUT=120s 是单模型超时，总进程 timeout 需 1200s。mimo-v2.5-pro 总是最后执行（串行模式），需要最多等待时间。round_001 的 mimo parse_status 通常是 "retried"（JSON 解析重试），这是正常的。
32. PUA-loop convergence 追踪: multimodel_convergence_stats() 输出 total_active/multimodel_passed/multimodel_triggered/pass_rate/trigger_rate。pass_rate=0 且 trigger_rate>0.8 意味着所有触发的任务都未通过认证。首次 pass_rate>0 需要选择证据充分、模型共识度高的简单任务。复杂修复/评估任务天然分歧高（agreement<0.7）。

## Taskpool 自动多模型介入 (2026-05-11)

本地大脑任务池已落地自动多模型介入 pipeline，无需手动触发"对 Hermes 说"。

### 架构

```
dispatch tick (每 N 分钟)
  ├── multimodel-intervention-dry-run  → 扫描任务池，计算触发队列
  ├── convergence stats               → total/passed/triggered/pass_rate
  └── multimodel-intervention-step    → (env var 门控)
      ├── build_state                 → consult_models.py state (120s)
      ├── run_discussion              → consult_models.py run --tier T3 --quorum 4 --discussion (closeout: ~15-20min)
      ├── ratification_gate           → 7 check fail-closed gate
      └── task_mutation               → 写入 multimodel_status 到 frontmatter

并行模式 (ThreadPoolExecutor):
  multimodel-intervention-parallel-step --max-workers 3
    ├── dry-run → 选择 top-N 不同边界任务
    ├── boundary 冲突检测（同边界只选一个）
    └── ThreadPoolExecutor(N)
        ├── worker 1: build→discussion→gate→mutate
        ├── worker 2: build→discussion→gate→mutate
        └── worker 3: build→discussion→gate→mutate
    └── 汇总 passed/failed/errors + convergence
```

### Tier 选择策略

| Tier | Models | Time/task | 适用场景 |
|------|--------|-----------|----------|
| T0 | mimo only | ~1min | 简单 sanity check |
| T1 | gpt + deepseek | ~3min | 低风险 review |
| T2 | gpt + deepseek + mimo | ~8min | Advisory/routing only; not valid for final taskpool/Lark closeout |
| T3 | claude + gpt + deepseek + mimo | ~15-20min | Required for high-score taskpool closeout, architecture decisions, safety-critical |

任务池 advisory/routing 可以用 T2（3 模型，~8min），但 PUA-loop closeout / Lark done / 高分任务最终认证必须用 T3（4 模型，~15-20min）并通过 ratification-gate。

### 触发策略 (结构性优先 + 关键词补充)

- 强结构: P0+evolution / retry>=2 / stale_claim → 直接触发
- 弱结构: running/review / P0 / evolution / architecture_target → 需 >=2 信号
- 关键词: 仅搜索 title+concepts，需已有结构信号才补充
- 关键词精度: 移除 >50% 命中率噪音词 (evidence/truth/local-brain/skill 等)
- 当前触发率: 32% (18/56 tasks)

### 关键命令

```bash
# 扫描 + 收敛统计
python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --json

# 串行执行一步 (需 env var)
HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-step --json

# 并行执行 (3 路并发，推荐)
HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-parallel-step --max-workers 3 --json

# ratification gate (双形态: Shape A 显式 criteria / Shape B 推导)
python3 ~/.hermes/scripts/brain_task_orchestrator.py ratification-gate --task TASK --discussion-result /path/to/discussion_result.json --json
```

### Gate 双形态

Shape A (显式): `criteria_satisfied.{accuracy, long_term_goal, one_shot_landing}` + `final_design.{next_slice, acceptance_evidence, rollback_boundary}`

Shape B (推导): `evidence_bundle.grounding` 全 verified → accuracy; `fanout_certification.multi_model_certified` → long_term_goal; `verification.guard_metrics` + `rollback_signal.auto_rollback_if` → one_shot_landing

Gate 模型数策略: taskpool automatic advisory/routing tiers may use tier-specific expected sets only when the state explicitly records that tier and the result is not being used for final Lark/done closeout. For closeout/certification under this user's policy, require the canonical 4-model set and fail 3/4 as `not_certified`. Never let self-attested `models_consulted` silently lower the closeout requirement.

### 自运行配置清单

开启自运行需要 3 个文件 + 2 个 env var:

```bash
# 1. env vars (持久化到 .zshrc)
export HERMES_LOCAL_BRAIN_AUTORUN=1
export HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1

# 2. autorun allowlist
~/.hermes/state/auto_run_allowlist.json  # ["project:xxx", "project:yyy"]

# 3. multimodel allowlist (可选，空=全部通过)
~/.hermes/state/multimodel_intervention_allowlist.json

# 4. autonomy-write-allowlist (必须，否则 auto-claim FAIL_CLOSED)
~/.hermes/config/autonomy-write-allowlist.json  # ["taskpool", "kanban-worker"]
```

### Cron

- job: `multimodel-intervention-step` (every 60m)
- 命令: `multimodel-intervention-parallel-step --max-workers 3 --json`
- job_id: `1883fd365c15`

### 新命令

```bash
# 并行 step（推荐，3 路并行，~48min 处理 18 任务）
HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-parallel-step --max-workers 3 --json

# 串行 step（单任务，调试用）
HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-step --json
```

### Pitfalls

1. discussion timeout: T3(4模型×5轮)需 1200s; T2(3模型×3轮)需 ~600s
2. state_path 清理: 防止 stale 目录导致 IsADirectoryError (shutil.rmtree)
3. shell=True: build/run 命令含 && 链，需 shell 执行
4. tick SKIP: allowed_statuses 必须含 SKIP，否则未激活 step 报 ERROR
5. scheduled-cron env gate: `multimodel-intervention-parallel-step` still requires `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`. If the exact user/cron command omits it, the command returns `SKIP: autorun_multimodel_disabled` (exit 2). In an autonomous cron run where the intent is clearly to process tasks, rerun inline with `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 ...`, then report both the initial SKIP and the effective run result rather than claiming no work. For durable cron activation, prefer a no-argument wrapper script (for example `multimodel_intervention_parallel_step.py`) that sets the env var and calls `brain_task_orchestrator.py multimodel-intervention-parallel-step --max-workers 3 --json`; cron script fields do not source `.zshrc` and should not rely on embedded argv.
6. mimo-v2.5-pro: provider=xiaomi，最后执行，retry status 常见
6. build_state 缺 claims: 无 --claim 时 truth_status=no_claims → gate 必然 FAIL
7. errors 变量顺序: tick 中 errors=[] 必须在引用前初始化
8. 并行 tick 匹配: 多个 discussion 并发时需 task_id[:40] 模糊匹配 + 10min 时间窗
9. autonomy-write-allowlist: 缺此文件导致 auto-claim FAIL_CLOSED
10. gate 模型数策略: advisory/routing tiers may be tier-specific, but final Lark/taskpool closeout for this user requires the canonical four-model set. Do not lower requirements from `models_consulted`; 3/4 is `not_certified` for closeout.
6. build_state_command 必须含 --claim: 否则 truth_status=no_claims，gate 必然 FAIL
7. tick errors 变量: errors = [] 必须在 step 引用前初始化，否则 UnboundLocalError
8. autonomy-write-allowlist: 缺失时 auto-claim 返回 FAIL_CLOSED (autonomy_write_guard_failed)
9. Gate 模型数策略: advisory/routing tiers may be tier-specific, but final Lark/taskpool closeout for this user requires the canonical four-model set. Do not lower requirements from `models_consulted`; 3/4 is `not_certified` for closeout.

## 关联 Skill
8. autonomy-write-allowlist: 缺失时 auto-claim 返回 FAIL_CLOSED (autonomy_write_guard_failed)
9. Gate 模型数策略: advisory/routing tiers may be tier-specific, but final Lark/taskpool closeout for this user requires the canonical four-model set. Do not lower requirements from `models_consulted`; 3/4 is `not_certified` for closeout.
6. 首次 not_certified 是正常行为: 复杂任务（如外部工具评估）通常不会第一次就通过 gate。gate 的 7 项检查（status/votes/agreement/issues/truth/criteria/design）会正确识别未收敛的讨论。not_certified 不等于失败，而是"模型有分歧，需要更多证据或方案修订"

### 实跑基准

见 `references/real-run-benchmark-2026-05-11.md`：5 rounds × 4 models ≈ 17min，mimo 始终 retried 但成功，首次 not_certified 是预期行为。

### 实跑基准 (2026-05-11)

task: openai-cli 沙箱评估 (P1 evolution)
- 5 rounds × 4 models = 20 model calls
- 总耗时: ~17 分钟 (1200s timeout 内完成)
- mimo: 每轮 retried 但 parse ok
- 结果: not_certified, agreement=0.65, 10 unresolved issues
- gate failures: 23 (status/votes/agreement/truth/issues 全部正确识别)
5. mimo-v2.5-pro: provider=xiaomi，最后执行，retry status 常见
6. build_state 无 --claim → truth_status=no_claims，gate 必然 FAIL。必须在 build_state_command 中注入显式 `--claim 'C-001:...'` 标志，与 gate 的 criteria_satisfied 三轴对齐
7. evidence linking: claims 存在但未链接 → truth_status=unsupported。consult_models.py 讨论阶段自动处理 evidence linking，但首轮 state 不含 --evidence-json 时 claims 不被验证
8. 评估类任务（evaluation/audit/review）天然产生 noop votes — 模型倾向"无需改动"。选择实跑验证任务时优先选有明确实现工作的任务
9. 4 模型 5 轮 discussion 耗时 ~15-20min（每轮 ~3-4min）。1200s timeout 刚好够 5 轮，如需更多轮次需增加 timeout
10. subprocess shell=True: build/run 命令含 && 链式（如 mkdir -p && python3 consult_models.py），必须 shell=True。shlex.split 不能处理 &&。实跑 findings、keyword noise 分析、gate fail patterns 见 `references/taskpool-multimodel-intervention-pitfalls.md`。

## 关联 Skill

- multi-model-architecture: L0-L5 多模型基础设施、quorum、consult_models.py。
- p10-architecture-self-check: P10 架构自检。
- incremental-implementation: 增量实施策略。
- post-update-patch-healing: 升级后 patch 恢复。
