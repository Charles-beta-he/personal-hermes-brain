# UVISA frontend+backend sync multi-model review pattern

Use when a batch of Lark tasks needs both frontend and backend changes, and the user asks for "多模型思考最佳落地方案" (multi-model review for best implementation approach).

## Workflow

1. **Backend codebase audit first**: delegate a comprehensive analysis to identify:
   - Current API endpoint shapes and response contracts
   - Database models and existing encryption/masking
   - Auth middleware and token validation flow
   - Test coverage gaps
   - Write findings to `/tmp/uvisa-fe-be-sync-state.json` or similar

2. **Multi-model parallel review** with 3 distinct review lenses:
   - **Architecture/Correctness**: does the approach match the codebase? backward compat? test gaps?
   - **Red-Team/Security**: adversarial review — data leaks, race conditions, blast radius
   - **Practical/Simplicity**: effort estimates, simpler alternatives, blockers

3. **Synthesize consensus**: each reviewer produces structured APPROVE/AMEND verdicts per task. The orchestrator synthesizes:
   - Agreement points (implement as-is)
   - Amendment points (apply reviewer's fix)
   - Disagreements (document rationale, pick the safer option)

4. **Write to project profile**: add a new section to the project Workpad with the certified implementation plan, risk matrix, and implementation order.

5. **Implement in risk order**: lowest risk first (builds confidence), highest risk last (gets full attention).

## Key findings from 2026-05-11 UVISA review

- Red-Team found ACTIVE DATA LEAK in TopupController that neither the Architecture nor Practical reviewer caught — the authenticated endpoints returned raw bank data while the public endpoint was already sanitized.
- SSO approach was revised from DB session_version to Redis Active-Session based on all 3 reviewers agreeing on lower blast radius.
- Implementation order was revised: notification (low) → data masking (medium, but critical security fix) → SSO (high blast radius, touches every request).

## Pitfall

- Don't use `delegate_task` for the multi-model review if you need all 3 reviewers to read the same state file — the state file at `/tmp/` may not be accessible to all workers. Instead, include the key context directly in each task's `context` field.
- Each reviewer should independently verify claims by reading actual source files, not just trusting the state file summary.

## Actual outcomes (2026-05-11 implementation)

All 3 non-blocked tasks from the certified plan were implemented and pushed:

| Task | Approach | Outcome |
|------|----------|---------|
| Notification subType (6906ef6e) | BE: `mapSubType()` in toItem(); FE: prefer `raw.subType` with `inferTransactionType()` fallback | ✅ 531 tests, pushed |
| Data masking (ee902251) | BE: `maskReceivingFields()` in TopupController; FE already used sanitized endpoint | ✅ Compile verified, pushed |
| SSO (ed1cb905) | Redis Active-Session with `sid` JWT claim, per-request validation, SESSION_EXPIRED toast | ✅ 541 tests, pushed |

Key implementation pitfall: `maskReceivingFields()` was initially placed inside `TopupService` (inner class) but called from `TopupController` (outer class) — Java compiler couldn't resolve it. Fix: move masking methods to the controller class where the endpoints are defined.

DB encryption (c1ec1131) deferred — requires KMS/key management decision.
