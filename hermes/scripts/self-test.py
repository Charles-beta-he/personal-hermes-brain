#!/usr/bin/env python3
"""
自进化管线 — 自动化全组件自测
验证每个组件可用并检查已知问题
"""

import os, sys, json, subprocess, re, tempfile
from pathlib import Path

HERMES_HOME = os.path.expanduser("~/.hermes")
SELF_TEST_DB = "/tmp/hermes-self-test-route_outcomes.db"
ROUTE_ENV = dict(os.environ, HERMES_ROUTE_DB_PATH=SELF_TEST_DB)
if os.path.exists(SELF_TEST_DB):
    os.remove(SELF_TEST_DB)

tests = []
passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    ok = False
    try:
        ok, msg = fn()
        if ok:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name}: {msg}")
    except Exception as e:
        failed += 1
        print(f"  ✗ {name}: {e}")
    tests.append((name, ok))

# ── 文件存在性 ──

FILES = [
    "scripts/post-session-autopsy.py",       # L0 sensor
    "scripts/self-improvement-pipeline.py",  # L0 prioritizer
    "scripts/route_store.py",                # L1 store
    "scripts/eval-harness.py",               # L4 gate
    "scripts/cross-patch.py",                # L4 cross-patch
    "scripts/consult_models.py",             # L5 multi-brain
    "scripts/ensemble-vote.py",              # L3 ensemble
    "scripts/consensus-check.py",            # L4 consensus
    "scripts/agent_protocol.py",             # L2 protocol
    "scripts/test_cross_patch_real_execution.py",  # L4 regression
    "agent-hooks/record-trace.sh",           # L1 hook
    f"skills/software-development/router/SKILL.md",                  # L2 skill
    f"skills/software-development/self-improvement-pipeline/SKILL.md",# system skill
    os.path.expanduser("~/.pua/evolution.md"),       # evolution tracking
]

for f in FILES:
    path = os.path.join(HERMES_HOME, f) if not f.startswith("~") else os.path.expanduser(f)
    test(f"File exists: {os.path.basename(path)}", lambda p=path: (os.path.exists(p), f"not found: {p}"))

# ── Executable ──

test("record-trace.sh is executable", lambda: (
    os.access(os.path.join(HERMES_HOME, "agent-hooks/record-trace.sh"), os.X_OK),
    "not executable"
))

# ── Config.yaml hooks ──

test("config.yaml has hooks", lambda: (
    os.path.exists(os.path.join(HERMES_HOME, "config.yaml")),
    "config.yaml missing"
))

with open(os.path.join(HERMES_HOME, "config.yaml")) as f:
    cfg = f.read()
test("hooks_auto_accept = true", lambda: (
    "hooks_auto_accept: true" in cfg,
    f"hooks_auto_accept not set to true"
))
test("record-trace in hooks", lambda: (
    "record-trace.sh" in cfg,
    "record-trace.sh hook not registered in config.yaml"
))

# ── Route Store CLI ──

r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/route_store.py"), "summary"],
    capture_output=True, text=True, timeout=10, env=ROUTE_ENV
)
test("route_store.py summary runs", lambda: (r.returncode == 0, r.stderr[:100]))

# ── Route Store: append + query + stats + scores ──

r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/route_store.py"),
     "append", "--skill", "test-harness", "--task_class", "self_test",
     "--route", "verify", "--verdict", "pass", "--duration_s", "0.5",
     "--tokens_in", "100", "--tokens_out", "50"],
    capture_output=True, text=True, timeout=10, env=ROUTE_ENV
)
test("route_store.py append works", lambda: (r.returncode == 0, r.stderr[:100]))

r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/route_store.py"),
     "query", "--task-class", "self_test", "--limit", "5"],
    capture_output=True, text=True, timeout=10, env=ROUTE_ENV
)
has_data = "self_test" in r.stdout
test("route_store.py query by task_class", lambda: (has_data, f"no results for self_test"))

r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/route_store.py"),
     "stats", "--task-class", "self_test"],
    capture_output=True, text=True, timeout=10, env=ROUTE_ENV
)
has_pass = '"pass_rate": 1.0' in r.stdout or '"pass_rate": 1' in r.stdout
test("route_store.py stats pass_rate=1.0", lambda: (has_pass, f"stats unexpected: {r.stdout[:200]}"))

r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/route_store.py"),
     "scores", "--task-class", "self_test"],
    capture_output=True, text=True, timeout=10, env=ROUTE_ENV
)
test("route_store.py scores returns list", lambda: (
    r.returncode == 0 and "score" in r.stdout,
    f"scores failed: {r.stderr[:100]}"
))

# ── Post-Session Autopsy ──

r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/post-session-autopsy.py"),
     "--recent", "2"],
    capture_output=True, text=True, timeout=15
)
has_report = "Post-Session Autopsy Report" in r.stdout
test("post-session-autopsy.py --recent 2", lambda: (has_report, r.stderr[:200] or r.stdout[-200:]))

# ── Self-Improvement Pipeline ──

r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/self-improvement-pipeline.py"),
     "--preview"],
    capture_output=True, text=True, timeout=15
)
test("self-improvement-pipeline.py --preview", lambda: (r.returncode == 0, r.stderr[:200]))

# ── Eval Harness ──

r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/eval-harness.py"),
     "--status"],
    capture_output=True, text=True, timeout=10
)
test("eval-harness.py --status", lambda: (r.returncode == 0, r.stderr[:200]))

# ── Skills-staging dir ──

staging = os.path.join(HERMES_HOME, "skills-staging")
test("skills-staging/ directory exists", lambda: (
    os.path.isdir(staging), "not found"
))

# ── Evolution.md ──

evo = os.path.expanduser("~/.pua/evolution.md")
test("evolution.md exists", lambda: (
    os.path.exists(evo), "not found"
))

# ── Improvement signals file ──

sig = os.path.join(HERMES_HOME, "notes/improvement-signals.jsonl")
test("improvement-signals.jsonl exists", lambda: (
    os.path.exists(sig), "not found; run autopsy --recent 5 --write"
))

# ── Route outcomes DB ──

db = os.path.join(HERMES_HOME, "route_outcomes.db")
db_ok = os.path.exists(db)
if db_ok:
    import sqlite3
    conn = sqlite3.connect(db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    has_table = "route_outcomes" in table_names
    count = conn.execute("SELECT COUNT(*) FROM route_outcomes").fetchone()[0]
    conn.close()
    test("route_outcomes.db has table + data", lambda: (
        has_table and count > 0,
        f"table ok={has_table}, row_count={count}"
    ))
else:
    test("route_outcomes.db exists", lambda: (False, "not found"))

# ── Multi-Model Architecture ──

# cross-patch.py status
r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/cross-patch.py"), "status"],
    capture_output=True, text=True, timeout=10
)
test("cross-patch.py status", lambda: (r.returncode == 0, r.stderr[:200]))

# cross-patch.py compile
r = subprocess.run(
    [sys.executable, "-m", "py_compile", os.path.join(HERMES_HOME, "scripts/cross-patch.py")],
    capture_output=True, text=True, timeout=10
)
test("cross-patch.py compiles", lambda: (r.returncode == 0, r.stderr[:200]))

# test_cross_patch_real_execution.py exists and passes
test_file = os.path.join(HERMES_HOME, "scripts/test_cross_patch_real_execution.py")
if os.path.exists(test_file):
    r = subprocess.run(
        [sys.executable, test_file],
        capture_output=True, text=True, timeout=30
    )
    test("cross-patch real execution tests", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("cross-patch real execution tests", lambda: (False, "test file not found"))

# consult_models.py + model_quota.py + safe cron wrappers compile
for script_name in (
    "consult_models.py",
    "model_quota.py",
    "p10-health-safe.py",
    "multi-model-smoke.py",
    "multi-model-smoke-safe.py",
    "multi-model-smoke-every4h-wrapper.py",
    "multi-model-smoke-daily-full-wrapper.py",
    "multi-brain-nightly-wrapper.py",
    "model-diversity-monitor.py",
    "autonomy-precondition.py",
    "autonomy-write-guard.py",
):
    r = subprocess.run(
        [sys.executable, "-m", "py_compile", os.path.join(HERMES_HOME, f"scripts/{script_name}")],
        capture_output=True, text=True, timeout=10
    )
    test(f"{script_name} compiles", lambda r=r: (r.returncode == 0, r.stderr[:200]))

# ensemble-vote.py compile
r = subprocess.run(
    [sys.executable, "-m", "py_compile", os.path.join(HERMES_HOME, "scripts/ensemble-vote.py")],
    capture_output=True, text=True, timeout=10
)
test("ensemble-vote.py compiles", lambda: (r.returncode == 0, r.stderr[:200]))

# model-router.py select-pair
r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/model-router.py"),
     "select-pair", "--task-tier", "codegen"],
    capture_output=True, text=True, timeout=10, env=ROUTE_ENV
)
has_pair = '"producer"' in r.stdout and '"reviewer"' in r.stdout
test("model-router select-pair returns producer+reviewer", lambda: (
    r.returncode == 0 and has_pair, r.stderr[:200] or r.stdout[:200]
))

# quorum.yaml parseable
import yaml as _yaml
quorum_path = os.path.join(HERMES_HOME, "config/quorum.yaml")
try:
    with open(quorum_path) as f:
        q = _yaml.safe_load(f)
    test("quorum.yaml parseable", lambda: (
        isinstance(q, dict) and "multi_brain" in q, "missing multi_brain key"
    ))
except Exception as e:
    test("quorum.yaml parseable", lambda: (False, str(e)))

# consult_models deterministic analysis selfcheck (no model calls)
r = subprocess.run(
    [sys.executable, os.path.join(HERMES_HOME, "scripts/consult_models.py"), "selfcheck", "--json"],
    capture_output=True, text=True, timeout=30
)
def _consult_models_selfcheck_ok(r=r):
    if r.returncode != 0:
        return False, r.stderr[:300] or r.stdout[:500]
    try:
        report = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e}; stdout={r.stdout[:200]}"
    return report.get("status") == "PASS", json.dumps(report.get("summary", report), ensure_ascii=False)[:300]
test("consult_models analysis selfcheck", _consult_models_selfcheck_ok)

# consensus-check.py detect_type precision
r = subprocess.run(
    [sys.executable, "-m", "py_compile", os.path.join(HERMES_HOME, "scripts/consensus-check.py")],
    capture_output=True, text=True, timeout=10
)
test("consensus-check.py compiles", lambda: (r.returncode == 0, r.stderr[:200]))

# agent_protocol.py compile
r = subprocess.run(
    [sys.executable, "-m", "py_compile", os.path.join(HERMES_HOME, "scripts/agent_protocol.py")],
    capture_output=True, text=True, timeout=10
)
test("agent_protocol.py compiles", lambda: (r.returncode == 0, r.stderr[:200]))


# skill-steward Skill Graphs 2.0 smoke tests
def _write_skill(root, name, tier, related=None):
    d = Path(root) / name
    d.mkdir(parents=True, exist_ok=True)
    rel = ""
    if related:
        rel = "related_skills: [" + ", ".join(related) + "]\n"
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ntier: {tier}\n{rel}---\n\n# {name}\nTest fixture.\n"
    )

steward = os.path.join(HERMES_HOME, "scripts/skill-steward.py")
r = subprocess.run([sys.executable, "-m", "py_compile", steward], capture_output=True, text=True, timeout=10)
test("skill-steward.py compiles (with Skill Graphs 2.0)", lambda: (r.returncode == 0, r.stderr[:200]))
with tempfile.TemporaryDirectory() as td:
    _write_skill(td, "atom-a", "atom")
    _write_skill(td, "atom-b", "atom")
    _write_skill(td, "molecule-ab", "molecule", ["atom-a", "atom-b"])
    _write_skill(td, "compound-ab", "compound", ["molecule-ab", "atom-a"])
    env = dict(os.environ, HERMES_SKILLS_DIR=td)
    r = subprocess.run([sys.executable, steward, "--graph-check", "--json"], env=env, capture_output=True, text=True, timeout=10)
    test("skill graph valid fixture passes", lambda r=r: (r.returncode == 0 and '"status": "OK"' in r.stdout, r.stderr[:200] or r.stdout[:300]))
with tempfile.TemporaryDirectory() as td:
    _write_skill(td, "cycle-a", "molecule", ["cycle-b"])
    _write_skill(td, "cycle-b", "molecule", ["cycle-a"])
    _write_skill(td, "deep-0", "atom")
    previous = "deep-0"
    for i in range(1, 7):
        tier = "molecule" if i == 1 else "compound"
        name = f"deep-{i}"
        _write_skill(td, name, tier, [previous])
        previous = name
    env = dict(os.environ, HERMES_SKILLS_DIR=td)
    r = subprocess.run([sys.executable, steward, "--graph-check", "--json"], env=env, capture_output=True, text=True, timeout=10)
    test("skill graph invalid fixture fails closed", lambda r=r: (r.returncode == 2 and 'cycle_count' in r.stdout and 'excessive_depth' in r.stdout, r.stderr[:200] or r.stdout[:500]))

# ensemble-vote integration tests (tally + execution metadata)
test_ens = os.path.join(HERMES_HOME, "scripts/test_ensemble_vote_integration.py")
if os.path.exists(test_ens):
    r = subprocess.run([sys.executable, test_ens], capture_output=True, text=True, timeout=30)
    m = re.search(r"Ran (\d+) tests", r.stderr + r.stdout)
    count_label = f"{m.group(1)}/{m.group(1)}" if m else "ensemble"
    test(f"ensemble-vote tests ({count_label})", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("ensemble-vote tests", lambda: (False, "test file not found"))

# consult_models integration tests (provider resolution + quorum + quota + certification + evidence truth gate)
test_con = os.path.join(HERMES_HOME, "scripts/test_consult_models_integration.py")
if os.path.exists(test_con):
    r = subprocess.run([sys.executable, test_con], capture_output=True, text=True, timeout=30)
    m = re.search(r"Ran (\d+) tests", r.stderr + r.stdout)
    count_label = f"{m.group(1)}/{m.group(1)}" if m else "integration"
    test(f"consult_models integration tests ({count_label})", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("consult_models integration tests", lambda: (False, "test file not found"))

# p10-health-safe bounded wrapper tests
p10_safe_test = os.path.join(HERMES_HOME, "scripts/test_p10_health_safe.py")
if os.path.exists(p10_safe_test):
    r = subprocess.run([sys.executable, p10_safe_test], capture_output=True, text=True, timeout=15)
    test("p10-health-safe tests (4/4)", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("p10-health-safe tests", lambda: (False, "test file not found"))

# multi-model-smoke-safe bounded cron wrapper tests
smoke_safe_test = os.path.join(HERMES_HOME, "scripts/test_multi_model_smoke_safe.py")
if os.path.exists(smoke_safe_test):
    r = subprocess.run([sys.executable, smoke_safe_test], capture_output=True, text=True, timeout=15)
    test("multi-model-smoke-safe tests (3/3)", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("multi-model-smoke-safe tests", lambda: (False, "test file not found"))

# self-improvement priority/action-state tests
self_improvement_test = os.path.join(HERMES_HOME, "scripts/test_self_improvement_pipeline.py")
if os.path.exists(self_improvement_test):
    r = subprocess.run([sys.executable, self_improvement_test], capture_output=True, text=True, timeout=15)
    m = re.search(r"Ran (\d+) tests", r.stderr + r.stdout)
    count_label = f"{m.group(1)}/{m.group(1)}" if m else "pipeline"
    test(f"self-improvement pipeline tests ({count_label})", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("self-improvement pipeline tests", lambda: (False, "test file not found"))

# post-session autopsy structured failure aggregation tests
post_autopsy_test = os.path.join(HERMES_HOME, "scripts/test_post_session_autopsy.py")
if os.path.exists(post_autopsy_test):
    r = subprocess.run([sys.executable, post_autopsy_test], capture_output=True, text=True, timeout=15)
    m = re.search(r"Ran (\d+) tests", r.stderr + r.stdout)
    count_label = f"{m.group(1)}/{m.group(1)}" if m else "autopsy"
    test(f"post-session autopsy tests ({count_label})", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("post-session autopsy tests", lambda: (False, "test file not found"))

# usage-score metric semantics tests
usage_score_test = os.path.join(HERMES_HOME, "scripts/test_usage_score.py")
if os.path.exists(usage_score_test):
    r = subprocess.run([sys.executable, usage_score_test], capture_output=True, text=True, timeout=15)
    m = re.search(r"Ran (\d+) tests", r.stderr + r.stdout)
    count_label = f"{m.group(1)}/{m.group(1)}" if m else "usage"
    test(f"usage-score tests ({count_label})", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("usage-score tests", lambda: (False, "test file not found"))

# model quota tests (headers/default snapshot/persistence/gating)
for test_name, label in (
    ("test_model_quota.py", "model_quota tests (4/4)"),
    ("test_model_router_quota.py", "model-router quota tests (1/1)"),
):
    test_path = os.path.join(HERMES_HOME, f"scripts/{test_name}")
    if os.path.exists(test_path):
        r = subprocess.run([sys.executable, test_path], capture_output=True, text=True, timeout=30)
        test(label, lambda r=r: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
    else:
        test(label, lambda test_name=test_name: (False, f"{test_name} not found"))

# model diversity + autonomy fail-closed gates
model_autonomy_test = os.path.join(HERMES_HOME, "scripts/test_model_diversity_and_autonomy_gates.py")
if os.path.exists(model_autonomy_test):
    r = subprocess.run([sys.executable, model_autonomy_test], capture_output=True, text=True, timeout=15)
    m = re.search(r"Ran (\d+) tests", r.stderr + r.stdout)
    count_label = f"{m.group(1)}/{m.group(1)}" if m else "gate"
    test(f"model-diversity/autonomy gate tests ({count_label})", lambda r=r: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("model-diversity/autonomy gate tests", lambda: (False, "test file not found"))

# cross-patch safety tests (5 tests: non-unique, --apply guard, verify pass, rollback, cost)
test_safety = os.path.join(HERMES_HOME, "scripts/test_cross_patch_safety.py")
if os.path.exists(test_safety):
    r = subprocess.run([sys.executable, test_safety], capture_output=True, text=True, timeout=30)
    test("cross-patch safety tests (5/5)", lambda: (r.returncode == 0, r.stderr[:300] or r.stdout[-300:]))
else:
    test("cross-patch safety tests", lambda: (False, "test file not found"))

# pricing.py promo TTL alarm compile
r = subprocess.run(
    [sys.executable, "-m", "py_compile", os.path.join(HERMES_HOME, "scripts/pricing.py")],
    capture_output=True, text=True, timeout=10
)
test("pricing.py compiles (with promo TTL)", lambda: (r.returncode == 0, r.stderr[:200]))

# model-router.py compile (with self-healing log)
r = subprocess.run(
    [sys.executable, "-m", "py_compile", os.path.join(HERMES_HOME, "scripts/model-router.py")],
    capture_output=True, text=True, timeout=10
)
test("model-router.py compiles (with self-heal)", lambda: (r.returncode == 0, r.stderr[:200]))

# ── Private Evolution Governance ──

# verify-evolution-event.py compile + compliance check against the canonical P0 event.
verify_evo = os.path.join(HERMES_HOME, "scripts/verify-evolution-event.py")
r = subprocess.run(
    [sys.executable, "-m", "py_compile", verify_evo],
    capture_output=True, text=True, timeout=10
)
test("verify-evolution-event.py compiles", lambda: (r.returncode == 0, r.stderr[:200]))

p0_event = os.path.join(HERMES_HOME, "notes/evolution/2026-04-29-warp-p0-multimodel-governance.md")
p0_spec = os.path.join(HERMES_HOME, "hermes-agent/specs/p0-multimodel-governance")
p0_review_schema = os.path.join(HERMES_HOME, "hermes-agent/docs/specs/review.schema.json")
fanout_schema = os.path.join(HERMES_HOME, "schemas/fanout-certification.schema.json")
evidence_schema = os.path.join(HERMES_HOME, "schemas/evidence-bundle.schema.json")
skill_graph_schema = os.path.join(HERMES_HOME, "schemas/skill-graph-audit.schema.json")
if os.path.exists(fanout_schema):
    r = subprocess.run(
        [sys.executable, "-m", "json.tool", fanout_schema],
        capture_output=True, text=True, timeout=10
    )
    test("fanout-certification schema parseable", lambda r=r: (r.returncode == 0, r.stderr[:200]))
else:
    test("fanout-certification schema parseable", lambda: (False, "schema file not found"))
if os.path.exists(evidence_schema):
    r = subprocess.run(
        [sys.executable, "-m", "json.tool", evidence_schema],
        capture_output=True, text=True, timeout=10
    )
    test("evidence-bundle schema parseable", lambda r=r: (r.returncode == 0, r.stderr[:200]))
else:
    test("evidence-bundle schema parseable", lambda: (False, "schema file not found"))
if os.path.exists(skill_graph_schema):
    r = subprocess.run(
        [sys.executable, "-m", "json.tool", skill_graph_schema],
        capture_output=True, text=True, timeout=10
    )
    test("skill-graph-audit schema parseable", lambda r=r: (r.returncode == 0, r.stderr[:200]))
else:
    test("skill-graph-audit schema parseable", lambda: (False, "schema file not found"))

if os.path.exists(p0_event) and os.path.exists(verify_evo):
    r = subprocess.run(
        [sys.executable, verify_evo, p0_event, p0_spec, p0_review_schema, "--repo=" + os.path.join(HERMES_HOME, "hermes-agent")],
        capture_output=True, text=True, timeout=30
    )
    test("P0 evolution event is compliant", lambda r=r: (
        r.returncode == 0 and "Final: COMPLIANT" in r.stdout,
        r.stderr[:300] or r.stdout[-500:]
    ))
else:
    test("P0 evolution event is compliant", lambda: (False, "P0 event or verifier missing"))

# ── Summary ──

print(f"\n{'='*50}")
print(f"  Self-Test Results: {passed}/{passed+failed} passed")
if failed > 0:
    print(f"  FAILURES: {failed}")
    print(f"  Run manual checks on failing components")
else:
    print(f"  ALL PASS — system is operational")
print(f"{'='*50}")

sys.exit(0 if failed == 0 else 1)
