# Autonomous certification scope and provider evidence

Use this reference when the user asks whether Hermes/autonomous execution can be called “fully certified”, especially after provider, router, quota, or post-update fusion work.

## Core rule

Do not certify autonomy globally from green deterministic subchecks. Full autonomous certification is a scoped claim over:

- provider set
- execution mode (`dispatch-hint`, `budget-handoff`, `autonomous-execution`)
- writable surfaces
- budget caps
- revocation conditions
- exact git/config/state artifact hashes

If the scope is not explicit, the safe status is `not_certified` or `truth_grounded_advisory`.

## Provider quota observability gate

A provider can participate in budget-handoff or autonomous-execution certification only when quota/budget evidence is fresh and usable for that provider. Exact balance/window evidence may qualify; empty headers, unobservable OAuth subscription limits, or model self-report do not.

Valid certification routes:

1. **All-provider certification**: every configured provider in scope has usable quota evidence and all downstream gates pass.
2. **Provider-limited certification**: certify only a smaller provider set with usable quota evidence. Non-certified providers may remain advisory/low-risk only.
3. **Risk-accepted operation**: use hard caps, kill switch, audit trail, and manual budget ceilings for unobservable providers. Label as risk-accepted limited autonomy, not clean full certification.

Never solve quota blindness by router fallback, lowering confidence thresholds, treating unknown as OK, or changing policy language to make failure look green.

## Required gate chain

Full certification requires all of these, in order:

1. Fresh claim/evidence bundle with exact claim IDs and evidence linkage.
2. Quota confidence `PASS` for the certified provider set:
   - `failure_count == 0`
   - every checked model/provider has explicit snapshot/evidence
   - evidence is fresh enough for the declared TTL
   - confidence is finite and `>= expected_min_confidence`
3. Router readiness `PASS`:
   - monitor returncode 0
   - strict positive schema present
   - no gate_failed/warnings that affect readiness
   - no automatic rebalance/route mutation unless explicitly part of the certified operation
4. Budget-handoff preconditions `PASS`:
   - explicit numeric caps for USD/tokens/requests/wall-clock/tool-calls/hops
   - missing, NaN, negative, or self-declared zero thresholds fail closed
5. Autonomous execution precondition `PASS`:
   - explicit local enable file exists
   - enable file is unexpired, scope-bound, and tied to the certification artifact hash
   - revocation conditions are defined
6. Write guard `PASS` for each surface:
   - explicit allowlist, not `*`
   - dry-run/proof/rollback path
   - real caller invokes `guard_or_raise` before mutation
7. Fresh T3 ratification artifact:
   - approval_count >= N-1
   - reject_count == 0
   - agreement matrix >= 0.85 on framing/approach/order
   - no unresolved severity >=3 issue
   - `can_certify_truth == true`

## Ratification issue handling

A deterministic gate pass does not override reviewer blockers. If ratification reports reject votes, unresolved severity>=3 risks, unsupported claims, or missing discussion artifacts, output `not_certified` until a fresh run resolves them.

For high-severity risks, require an issue ledger entry with owner, mitigation, evidence, verification command, and final status (`resolved` or evidence-backed downgrade). Avoid `accepted_risk` for severity>=4 if the desired label is clean full certification.

## Certification manifest

A final autonomous certification artifact should bind the claim to immutable evidence:

- certification_id and timestamp
- git commit and clean/dirty state
- config/policy hashes
- quota snapshot hash
- router readiness output hash
- budget/autonomy/write-guard output hashes
- p10-health/self-test output hashes
- T3 discussion result path/hash
- certified provider/mode/surface/budget scope
- revocation conditions

Correct wording:

- `FULL AUTONOMOUS CERTIFIED for scope S: provider set P, surfaces W, budget caps B, commit X, artifact Y.`
- `Non-certified providers remain advisory/low-risk only.`

Incorrect wording:

- `Fully certified` when some in-scope provider quota is unobservable.
- `Fully certified with caveats` when ratification still has reject votes or unresolved severity>=3 issues.
- `Router is ready` based only on diversity or dominance metrics while quota confidence failed.
