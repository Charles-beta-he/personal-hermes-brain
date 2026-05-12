---
type: review
status: active
created: 2026-05-12T01:28:04+08:00
review_subject: keypoint-coverage-ratchet-engineering-design
concepts: [deterministic-gate, keypoint-coverage, testing, false-positive-prevention]
---

# 关键点覆盖棘轮：工程实现/测试评审

## 结论

当前 `~/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py` 的方向正确：本地只读、fail-closed、JSON+Markdown 输出、fixture 单测、真实 gate 可复跑。最小可落地方案应继续沿用“规范数据结构 + 确定性解析 + 反作弊单测 + 真实验证命令”四件套，避免三类假阳性：

1. 同理论优化漏扫：只扫 22 个表格关键点会漏掉“同一理论/优化点”在路由矩阵、atom、dispatch/taskpool 中的落地边界。
2. 影响边漏修：只看关键点存在，不看 surfaces/landing target/gates，会遗漏脚本、taskpool、autorun、证据边界等受影响面。
3. 口头覆盖假阳性：只要文档写了 covered 或 22/22 就通过，而没有 artifact/evidence/gate 证明。

## 建议的数据结构

建议在脚本内保留 Python 常量，后续可抽成 YAML/JSON；最小结构如下：

```python
REQUIRED_ITEMS = [
  {
    "id": "KP21",
    "title": "少数意见/模型名不等于权威",
    "aliases": ["少数意见", "模型名不是证据", "model authority", "minority opinion"],
    "required_surfaces": [
      "review_table",
      "route_matrix",
      "minority_atom",
      "evidence_boundary"
    ],
    "required_gates": [
      "status_not_missing",
      "artifact_link_present",
      "issue_ledger_resolution_rule_present"
    ],
    "forbid_markers": ["missing", "uncovered", "TODO", "待补", "未覆盖"],
    "evidence_level_min": "E2"
  }
]

SURFACES = {
  "review_table": {
    "path": "06-治理与评审/reviews/2026-05-06-multimodel-thinking-keypoint-coverage-review.md",
    "parser": "markdown_keypoint_table"
  },
  "route_matrix": {
    "path": "05-实践与项目/实践方案/07-关键点多模型介入路由矩阵.md",
    "parser": "markdown_routing_matrix"
  },
  "routing_atom": {
    "path": "04-知识原子/atoms/keypoint-to-multimodel-routing.md",
    "parser": "text_required_terms"
  },
  "dispatch_tick": {
    "path": "~/.hermes/scripts/brain_task_dispatch_tick.py",
    "parser": "static_contract_terms"
  },
  "taskpool_dry_run": {
    "command": "python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --json",
    "parser": "json_contract"
  }
}

CHECK_RESULT = {
  "name": "route_matrix:KP21:tool_evidence_required",
  "ok": True,
  "severity": "blocker|warning|info",
  "surface": "route_matrix",
  "item_id": "KP21",
  "expected": "Tool evidence required=yes",
  "actual": "yes",
  "evidence": {"path": "...", "line": 67, "snippet": "..."}
}
```

关键点：

- 每个 keypoint 必须绑定 surfaces，而不是只绑定一个 review 表。
- 每个 surface 必须绑定 parser/contract，不能靠全文 substring 混过。
- 每个 check 结果必须有 severity、expected、actual、evidence，方便 CI/cron/人工复审定位。
- 报告里应区分 `knowledge_coverage`、`surface_coverage`、`gate_coverage`、`certification_status`，避免把“知识覆盖”说成“四模型认证”。

## 建议的解析规则

### 1. Review 表格解析

- 只解析标题为 `## 22 个关键点状态` 后、下一节标题前的表格，避免其他表格串扰。
- 表头必须包含 `# | 关键点 | 状态`，否则 fail closed。
- index 必须连续等于 1..22；重复 index、跳号、非数字都 fail。
- keypoint 必须精确匹配 canonical title；可允许 alias，但 alias 必须显式登记，不能模糊 contains。
- status 允许值应白名单化：`covered`、`covered-thin`、`covered by [[artifact]]`、`已覆盖`、`已落地`。
- status 中出现 `missing/uncovered/todo/gap/缺/未覆盖/待补` 任一词则 fail，即使同时包含 covered。
- `covered-thin` 可通过但应产生 warning 或 `thin_checks`，防止长期被 100% 掩盖。

### 2. Route matrix 解析

- 解析 Markdown 表头，按列名读取，而不是全文搜索 `T0/T1/T2/T3/yes`。
- 必需列：`Keypoint`、`多模型等级`、`First-order gate`、`Second-order gate`、`Tool evidence required`、`Landing target`、`Why`。
- 每个 route keypoint 至少一行；重复行 fail 或 warning。
- `Tool evidence required` 必须为 `yes`，不能只因全文某处有 `yes` 通过。
- T-level 必须匹配 token：`T0|T1|T2|T3`，禁止 `T30`、`T2-ish` 等 substring spoofing。
- 对高 blast radius 的 keypoint，要求至少 T2；涉及 canonical rule / self-evolution / safety 的要求 T3 或显式 accepted risk。

### 3. Atom / 文档 surface 解析

- 只检查结构化 anchor：标题、核心原则、规则、反模式、操作化 schema、链接；少用裸全文 contains。
- 对 artifact link 使用 wikilink/path 解析，确认目标文件存在。
- Evidence boundary 必须出现负向约束：`not_certified`、`dissent`、`timeout`、`不伪装认证`/`不篡改`。
- 对“模型名不是证据”这类规则，应要求至少一条正向处理口径和一条反模式。

### 4. Taskpool / dispatch 解析

- shell command 必须用 `shlex.split` 后 token 级检查；已做，应保留。
- `--tier T3`、`--quorum 4`、`--discussion`、`--keep` 必须精确 token 存在。
- autorun expensive step 必须双门控：CLI flag + env var；ambient env 单独存在必须 skip。
- timeout 必须结构化返回 JSON，包含 reason、timeout_seconds、stdout/stderr tail、process_group_terminated/killed，不能 traceback 泄露。

## 建议补充的单测

现有 7 个测试覆盖了 happy path、缺关键点、T3/quorum4、substring spoofing、timeout、autorun 双门控、CLI 输出。建议最小新增以下测试：

1. `test_review_rejects_declared_22_22_with_only_21_rows`
   - 删除一行但保留 frontmatter `coverage: 22/22`。
   - 期望 `review:table_row_count_22` 和对应 keypoint fail。

2. `test_review_rejects_duplicate_keypoint_even_when_row_count_is_22`
   - 用重复 KP1 替换 KP21，行数仍 22。
   - 期望 duplicate canonical keypoint fail，KP21 fail。

3. `test_review_rejects_status_with_mixed_covered_and_missing`
   - status 写 `covered but missing artifact`。
   - 期望 fail，防止 bad marker 被 covered 前缀绕过。

4. `test_review_table_parser_is_section_scoped`
   - 在正文其他位置放一个伪造 22 行表，但正式章节缺项。
   - 期望 fail，防止全文任意表格污染。

5. `test_route_matrix_requires_tool_evidence_per_row_not_global_yes`
   - 全文保留一个 `yes`，但某 keypoint 的 Tool evidence required 为空/no。
   - 期望该 route_matrix check fail。

6. `test_route_matrix_rejects_t_level_substring_spoofing`
   - 矩阵等级写 `T30` 或 `T2-ish`。
   - 期望 fail，和 taskpool command spoofing 对齐。

7. `test_artifact_link_must_exist_for_covered_by`
   - status 写 `covered by [[missing-atom]]`。
   - 期望 fail，防止口头 artifact。

8. `test_evidence_boundary_must_preserve_negative_labels`
   - 删除 `not_certified/dissent/timeout` 任意一项。
   - 期望 caveat check fail。

9. `test_skip_taskpool_is_reported_as_skipped_not_passed`
   - 用 `skip_taskpool=True`。
   - 期望 report 中 taskpool.status 为 SKIPPED，且最终结论说明 gate_scope 是 partial，避免把跳过真实 gate 当完整 PASS。

10. `test_static_dispatch_rejects_env_only_autorun_even_with_flag_defined_elsewhere`
    - 源码中有 flag 定义但执行分支只看 env。
    - 期望 double gate fail。

## 建议的验证命令

最小本地验证：

```bash
python3 -m py_compile \
  /Users/charles/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py \
  /Users/charles/.hermes/scripts/test_multimodel_keypoint_coverage_ratchet.py

python3 /Users/charles/.hermes/scripts/test_multimodel_keypoint_coverage_ratchet.py

python3 /Users/charles/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py \
  --skip-taskpool --json > /tmp/multimodel_keypoint_coverage_ratchet.skip.json

python3 /Users/charles/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py \
  --json > /tmp/multimodel_keypoint_coverage_ratchet.real.json
```

可选真实落地验证：

```bash
python3 /Users/charles/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py \
  --write-json /Users/charles/Documents/brain/06-治理与评审/reviews/multimodel-keypoint-ratchet-report.json \
  --write-report /Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-12-multimodel-keypoint-ratchet-coverage.md

python3 /Users/charles/.hermes/scripts/brainctl.py --json sync
python3 /Users/charles/.hermes/scripts/brainctl.py --json reindex
python3 /Users/charles/.hermes/scripts/brainctl.py --json search "多模型关键点棘轮覆盖" --limit 10
python3 /Users/charles/.hermes/scripts/brainctl.py --json search "少数意见 模型名不是证据" --limit 10
```

## 本次实际验证结果

已在本机执行：

```bash
python3 -m py_compile /Users/charles/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py /Users/charles/.hermes/scripts/test_multimodel_keypoint_coverage_ratchet.py
python3 /Users/charles/.hermes/scripts/test_multimodel_keypoint_coverage_ratchet.py
python3 /Users/charles/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py --skip-taskpool --json
python3 /Users/charles/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py --json
```

结果：

- py_compile：PASS
- script tests：PASS 7 tests
- skip-taskpool gate：PASS；keypoints 22/22；gate checks 56/56；failed []
- real gate：PASS；keypoints 22/22；gate checks 62/62；taskpool PASS；queued 17；selected `2026-05-10-多模型分析-rowboatlabs-rowboat-并完善-hermes-自身`；failed []

## 最小改造优先级

P0：把 route matrix 从 substring 检查升级成表格列解析；新增 per-row tool evidence/T-level 测试。

P0：新增 duplicate/missing/mixed-status/section-scoped review table 测试，堵住 22/22 口头覆盖假阳性。

P1：把 REQUIRED_KEYPOINTS 扩成带 id/aliases/surfaces/gates 的结构，报告中输出每个 keypoint 的 surface coverage。

P1：对 `covered by [[artifact]]` 做 wikilink 目标存在性检查。

P2：将规则常量抽到 YAML，脚本只负责解析和 gate，便于后续理论/优化点新增时做 schema review。
