---
type: playbook
status: active
created: 2026-05-07
project: resumable-multimodel-certification
---

# 10-可恢复多模型认证系统Playbook

## Trigger

当任务需要完整多模型认证，且影响 hook、state machine、cron、gateway、self-evolution 或高风险架构时使用。

## Operating Mode

### Quick path: weak fanout only

用于低风险 framing：

```bash
python3 ~/.hermes/scripts/consult_models.py run /tmp/state.json --tier T2 --quorum 4 --keep
```

输出只能称为 fanout/weak consensus，不能称为 certified。

### Certification path: resumable discussion

长期目标形态：

```bash
python3 ~/.hermes/scripts/consult_models.py run /tmp/state.json --tier T3 --quorum 4 --discussion --keep
python3 ~/.hermes/scripts/consult_models.py audit-certification ~/.hermes/tick-...
```

如果超时：

```bash
python3 ~/.hermes/scripts/consult_models.py resume-discussion ~/.hermes/tick-...
python3 ~/.hermes/scripts/consult_models.py audit-certification ~/.hermes/tick-...
```

## Certification Rule

Certified only if all are true:

- `discussion_result.json` exists;
- `certification_manifest.json` exists;
- truth gate can certify;
- no unresolved severity >= 3 blocker;
- votes satisfy ratification threshold;
- partial/degraded/timeout markers absent or explicitly accepted as minor risk.

## Fail-closed Rule

Any of these returns not certified:

- missing discussion_result;
- missing certification_manifest;
- corrupt checkpoint;
- unsupported high-severity claim;
- model call timeout without complete round;
- stale heartbeat;
- quota/budget exceeded;
- parse failure not accounted for.

## TaskCreate -> ralph Policy

Do not start implementation until this playbook has executable support through checkpoint, resume, audit, and background-safe status. The TaskCreate feature must be reopened as a separate high-risk project after RMCS P0-P2 PASS.
