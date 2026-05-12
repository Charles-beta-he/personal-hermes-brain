# Iron Plate Consolidation Pattern

Session: 2026-05-11 Complex Giant Systems + GenericAgent analysis
Theory: 钱学森开放复杂巨系统 + 西蒙近可分解性 + 霍兰CAS

## When to Apply

- Cron jobs > 20 with visible redundancy
- Multiple scripts doing overlapping health checks
- No centralized health signal
- Missing dead man's switch / retry / escalation
- User says "铁板" / "无缝" / "一体化"

## Methodology

### Phase 1: Audit (Multi-Model)
Run 2+ models to identify:
- **Redundancies (R1-Rn)**: duplicate scripts, overlapping monitoring, same-cadence meta-jobs
- **Gaps (G1-Gn)**: missing features, no retry, no unified dashboard, script argument bugs

### Phase 2: 5-Layer Architecture
Consolidate into 5 layers:

| Layer | Cadence | Absorbs | Purpose |
|-------|---------|---------|---------|
| L1 Ops | */30m | tick, controller, executor, bridge, selfcheck | Operational heartbeat |
| L2 Health | */6h | V(x), self-scan, smoke, usage, memory | Composite health signal |
| L3 Evolve | 02:00 | skill-steward, self-improvement, pa, failure | Nightly evolution |
| L4 Watchdog | */10m | cron-health, missed-run, dead-man-switch | Meta-observability |
| L5 Report | 08:00 | daily-digest, GC, eval-audit, canary | Reporting & cleanup |

### Phase 3: Multi-Model Ratification
Vote on consolidation. All 5 layers must pass. Common concerns:
- L3 (evolve): too many things in one nightly job → split into phases within same script
- L1 (ops): too frequent for heavy operations → ensure each sub-component has timeout

### Phase 4: Implementation
- Create wrapper scripts (avoid script argument space bug)
- Add retry/escalation logic
- Add dependency ordering (L1 before L2)
- Add unified logging

## GenericAgent Patterns to Adopt

1. **5-Layer Memory Density (L0-L4)**
   - L0: meta-rules (when to write memory)
   - L1: ≤30 line index (scene→knowledge routing)
   - L2: stable facts/configs
   - L3: reusable skills/SOPs
   - L4: compressed session archives

2. **Task→SOP Crystallization**
   After each task completes, extract key decisions → auto-generate skill file

3. **File IPC Sub-Agent**
   input.txt → worker → output.txt → supervisor
   Zero shared state, fully debuggable, intervention via _stop/_keyinfo files

## Pitfalls

1. Script argument space bug: `script="brain_task_orchestrator.py selfcheck"` may be treated as single filename. Use wrapper scripts.
2. Don't consolidate too aggressively — keep kill switches per-layer
3. L3 evolve must be dependency-ordered (audit → pipeline → steward → pa → taxonomy)
4. Dead man's switch must be EXTERNAL (not cron-based) to detect scheduler death
