---
type: review
layer: L6
status: active
created: 2026-05-06T18:07:23+08:00
project: local-brain-mempalace-derived
multi_model_status: not_certified
---

# 2026-05-06 MemPalace-derived Local Brain Multi-model Self-check

## Status

not_certified as a true four-model discussion certification。

Reason: `consult_models.py run /tmp/local-brain-mempalace-state.json --tier T3 --quorum 4 --discussion --max-rounds 5 --keep` reached four seed planners but timed out after 600s during consensus/discussion; timeout caveat recorded. DeepSeek seed output also had a JSON parse failure in the recorded plan. Therefore this review is provenance, not ratification。

model agreement is not evidence。P10 completion is judged by deterministic local gates, not by model agreement。

## Models / provenance

- Claude Opus seed: recommended artifact contract, playbook, review/task/evolution/atoms, self-check, brainctl audit gate。
- GPT-5.5 seed: identified verifier/provenance gap and required deterministic proof before P10 close。
- MiMo seed: emphasized execution gap and quota/certification caveat。
- DeepSeek: attempted but plan parse failed; issue remains caveat, not blocker for deterministic landing。

## issue_ledger

| id | severity | status | issue | resolution |
|---|---:|---|---|---|
| I-001 | 5 | resolved | MemPalace/Chroma palace could become a second source of truth | P10 invariant: Markdown vault remains canonical; derived caches are rebuildable |
| I-002 | 4 | resolved | Lossy summaries/AAAK/Closets may be mistaken for evidence | Drawer / Closet rule and atom [[04-知识原子/atoms/evidence-boundary-lossy-summary]] |
| I-003 | 4 | resolved | External LLM/API could leak local brain content | local-first default; `--no-llm`; no external calls in self-check |
| I-004 | 3 | accepted_risk | True four-model discussion did not certify | Marked `not_certified`; use deterministic gates for P10 closure |
| I-005 | 3 | accepted_risk | Chinese embedding quality in MemPalace default stack uncertain | P1 isolated benchmark only; no production dependency |

## Ratification votes

No certified ratification votes. Seed plans are treated as design input only。

## P10 synthesis

Best-within-current-constraints direction:

1. Do not adopt MemPalace runtime as the local brain。
2. Land MemPalace ideas as a Hermes-native derived index strategy。
3. Make evidence boundary explicit。
4. Require proof via self-check + `brainctl sync/reindex/search` + structural audit。

## Caveats

- Multi-model output is not enough to certify factual claims。
- This landing does not install MemPalace and does not run it on the vault。
- P1 experiments must stay outside the canonical vault。
