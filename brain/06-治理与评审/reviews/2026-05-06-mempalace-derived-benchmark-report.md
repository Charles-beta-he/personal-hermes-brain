---
type: review
layer: L6
status: completed
created: 2026-05-06T13:35:54Z
source: local_brain_mempalace_benchmark.py --no-llm
---

# MemPalace derived-index benchmark report

## Evidence Boundary

This report compares deterministic local search signals on an isolated sample. It does not adopt MemPalace runtime and does not write derived facts into the canonical vault.

## Result JSON

```json
{
  "schema": "local_brain_mempalace_derived_benchmark_v1",
  "generated_at": "2026-05-06T13:35:54Z",
  "source_vault": "/Users/charles/Documents/brain",
  "sample_dir": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh",
  "sample_file_count": 20,
  "derived_only": true,
  "no_llm": true,
  "writes_to_source_vault": false,
  "queries": [
    {
      "query": "MemPalace派生索引 P10 source of truth",
      "brainctl_like": [
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/prefs/local-first-obsidian-memory-preferences.md",
          "phrase_score": 0,
          "token_overlap": 3,
          "excerpt": "--- type: preference-mirror layer: L5 status: active created: 2026-05-06T08:10:29Z source: repeated_user_preference_and_environment_setup --- # Local-first Obsidian memory preferences This is a human-readable mirror of stable local-brain pr"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/Hermes Local Brain Memory Hierarchy.md",
          "phrase_score": 0,
          "token_overlap": 3,
          "excerpt": "--- type: system-design status: active created: 2026-05-06T07:41:43Z updated: 2026-05-06T12:56:02Z source: hermes_multi_model_review review_artifact: /Users/charles/.hermes/tick-20260506-073039 models_consulted: - claude-opus-4-7 - gpt-5.5 "
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/00-索引/00-大脑索引.md",
          "phrase_score": 0,
          "token_overlap": 2,
          "excerpt": "--- type: moc layer: L0 status: active created: 2026-05-06T19:29:36+08:00 concepts: [local-brain-main-hierarchy, migrated-hierarchy, semantic-control-plane] --- # 00-大脑索引 ## Canonical main hierarchy after migration 主层级已迁移为 P10 control-plane"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/brain-audit-proof-2026-05-06-pua-loop-fill.md",
          "phrase_score": 0,
          "token_overlap": 2,
          "excerpt": "--- type: proof-note status: verified created: 2026-05-06T09:05:00Z state_hash: f6b4466cd32124fef3ce7dbdcab7a29a6ac714fd4dc4b8aa579e87f596bd3bc5 multi_model_artifact: /Users/charles/.hermes/tick-20260506-083543 --- # Brain Audit Proof — PUA"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/02-证据与原文/evidence/00-evidence索引.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: moc status: active created: 2026-05-06T08:48:00Z folder: 00-evidence --- # L0 Evidence 原始证据层 ## 用途 保存事实输入、截图 OCR、链接、工具输出摘要；只放可追溯证据，不放推论。 ## 收录规则 - 只收与本目录语义直接相关的 Markdown artifact。 - 每个新增笔记应有清晰标题、来源/边界、与其他目录的链接。 - 任务/WIP 放入 `05-实践与"
        }
      ],
      "derived_token_overlap": [
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/prefs/local-first-obsidian-memory-preferences.md",
          "phrase_score": 0,
          "token_overlap": 3,
          "excerpt": "--- type: preference-mirror layer: L5 status: active created: 2026-05-06T08:10:29Z source: repeated_user_preference_and_environment_setup --- # Local-first Obsidian memory preferences This is a human-readable mirror of stable local-brain pr"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/Hermes Local Brain Memory Hierarchy.md",
          "phrase_score": 0,
          "token_overlap": 3,
          "excerpt": "--- type: system-design status: active created: 2026-05-06T07:41:43Z updated: 2026-05-06T12:56:02Z source: hermes_multi_model_review review_artifact: /Users/charles/.hermes/tick-20260506-073039 models_consulted: - claude-opus-4-7 - gpt-5.5 "
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/00-索引/00-大脑索引.md",
          "phrase_score": 0,
          "token_overlap": 2,
          "excerpt": "--- type: moc layer: L0 status: active created: 2026-05-06T19:29:36+08:00 concepts: [local-brain-main-hierarchy, migrated-hierarchy, semantic-control-plane] --- # 00-大脑索引 ## Canonical main hierarchy after migration 主层级已迁移为 P10 control-plane"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/brain-audit-proof-2026-05-06-pua-loop-fill.md",
          "phrase_score": 0,
          "token_overlap": 2,
          "excerpt": "--- type: proof-note status: verified created: 2026-05-06T09:05:00Z state_hash: f6b4466cd32124fef3ce7dbdcab7a29a6ac714fd4dc4b8aa579e87f596bd3bc5 multi_model_artifact: /Users/charles/.hermes/tick-20260506-083543 --- # Brain Audit Proof — PUA"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/02-证据与原文/evidence/00-evidence索引.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: moc status: active created: 2026-05-06T08:48:00Z folder: 00-evidence --- # L0 Evidence 原始证据层 ## 用途 保存事实输入、截图 OCR、链接、工具输出摘要；只放可追溯证据，不放推论。 ## 收录规则 - 只收与本目录语义直接相关的 Markdown artifact。 - 每个新增笔记应有清晰标题、来源/边界、与其他目录的链接。 - 任务/WIP 放入 `05-实践与"
        }
      ]
    },
    {
      "query": "temporal facts bilingual query benchmark",
      "brainctl_like": [
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/Hermes Local Brain Memory Hierarchy.md",
          "phrase_score": 0,
          "token_overlap": 2,
          "excerpt": "--- type: system-design status: active created: 2026-05-06T07:41:43Z updated: 2026-05-06T12:56:02Z source: hermes_multi_model_review review_artifact: /Users/charles/.hermes/tick-20260506-073039 models_consulted: - claude-opus-4-7 - gpt-5.5 "
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/prefs/local-first-obsidian-memory-preferences.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: preference-mirror layer: L5 status: active created: 2026-05-06T08:10:29Z source: repeated_user_preference_and_environment_setup --- # Local-first Obsidian memory preferences This is a human-readable mirror of stable local-brain pr"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/Obsidian Setup - Hermes Local Brain.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: setup-note status: active created: 2026-05-06T07:41:43Z updated: 2026-05-06T07:41:43Z app: Obsidian 1.12.7 canonical_vault: /Users/charles/Documents/brain legacy_vault: /Users/charles/Documents/Obsidian Vault --- # Obsidian Setup "
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/brain-audit-proof-2026-05-06-pua-loop-fill.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: proof-note status: verified created: 2026-05-06T09:05:00Z state_hash: f6b4466cd32124fef3ce7dbdcab7a29a6ac714fd4dc4b8aa579e87f596bd3bc5 multi_model_artifact: /Users/charles/.hermes/tick-20260506-083543 --- # Brain Audit Proof — PUA"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/02-证据与原文/evidence/2026-05-06-symphony-source-and-obsidian-cli-evidence.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: evidence layer: L0 status: active created: 2026-05-06T08:10:29Z source_event: 2026-05-06-symphony-obsidian-local-brain sensitivity: public --- # Evidence: Symphony source and Obsidian CLI enablement ## Raw source signal User suppl"
        }
      ],
      "derived_token_overlap": [
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/Hermes Local Brain Memory Hierarchy.md",
          "phrase_score": 0,
          "token_overlap": 2,
          "excerpt": "--- type: system-design status: active created: 2026-05-06T07:41:43Z updated: 2026-05-06T12:56:02Z source: hermes_multi_model_review review_artifact: /Users/charles/.hermes/tick-20260506-073039 models_consulted: - claude-opus-4-7 - gpt-5.5 "
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/prefs/local-first-obsidian-memory-preferences.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: preference-mirror layer: L5 status: active created: 2026-05-06T08:10:29Z source: repeated_user_preference_and_environment_setup --- # Local-first Obsidian memory preferences This is a human-readable mirror of stable local-brain pr"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/Obsidian Setup - Hermes Local Brain.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: setup-note status: active created: 2026-05-06T07:41:43Z updated: 2026-05-06T07:41:43Z app: Obsidian 1.12.7 canonical_vault: /Users/charles/Documents/brain legacy_vault: /Users/charles/Documents/Obsidian Vault --- # Obsidian Setup "
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/01-系统与偏好/system/brain-audit-proof-2026-05-06-pua-loop-fill.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: proof-note status: verified created: 2026-05-06T09:05:00Z state_hash: f6b4466cd32124fef3ce7dbdcab7a29a6ac714fd4dc4b8aa579e87f596bd3bc5 multi_model_artifact: /Users/charles/.hermes/tick-20260506-083543 --- # Brain Audit Proof — PUA"
        },
        {
          "path": "/var/folders/1h/g3g460m9029dd5_71xl27nz00000gn/T/hermes-mempalace-sample-2v7x0onh/02-证据与原文/evidence/2026-05-06-symphony-source-and-obsidian-cli-evidence.md",
          "phrase_score": 0,
          "token_overlap": 1,
          "excerpt": "--- type: evidence layer: L0 status: active created: 2026-05-06T08:10:29Z source_event: 2026-05-06-symphony-obsidian-local-brain sensitivity: public --- # Evidence: Symphony source and Obsidian CLI enablement ## Raw source signal User suppl"
        }
      ]
    }
  ],
  "promotion_gate": "no_promotion_without_precision_gain_and_no_recall_loss"
}
```
