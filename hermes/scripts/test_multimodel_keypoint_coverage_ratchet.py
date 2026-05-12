#!/usr/bin/env python3
"""Tests for multimodel_keypoint_coverage_ratchet.py."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOME = Path.home()
SCRIPT = HOME / ".hermes" / "scripts" / "multimodel_keypoint_coverage_ratchet.py"


def load_module():
    spec = importlib.util.spec_from_file_location("multimodel_keypoint_coverage_ratchet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def build_vault(root: Path) -> Path:
    m = load_module()
    review_rows = "\n".join(
        f"| {i} | {kp} | covered |" for i, kp in enumerate(m.REQUIRED_KEYPOINTS, start=1)
    )
    write(root / "06-治理与评审" / "reviews" / "2026-05-06-multimodel-thinking-keypoint-coverage-review.md", f"""---
type: review
coverage: 22/22
---
# 多模型思考关键点覆盖复审

| # | 关键点 | 状态 |
|---|---|---|
{review_rows}

Caveat: not_certified, dissent, timeout labels are preserved.
""")
    write(root / "05-实践与项目" / "实践方案" / "07-关键点多模型介入路由矩阵.md", """
# 07 - 关键点多模型介入路由矩阵
| Keypoint | 多模型等级 | Tool evidence required |
| 必要多样性 | T2/T3 | yes |
| 反馈回路与稳定性 | T1/T2 | yes |
| 置信度校准 | T2/T3 | yes |
| 双环学习 | T2/T3 | yes |
| 技能生态治理 | T2/T3 | yes |
| 本地大脑 source of truth / evidence boundary | T2/T3 | yes |
| 信息-通信-熵 | T1/T2 | yes |
| 稳态/内稳态/自适应 | T2 | yes |
| 可靠性理论 | T1/T2 | yes |
| Parnas 信息隐藏/模块化 | T2 | yes |
| 少数意见/模型名不是权威 | T2/T3 | yes |
| 通信预算/上下文压缩 | T1/T2 | yes |
T0 T1 T2 T3
""")
    write(root / "04-知识原子" / "atoms" / "keypoint-to-multimodel-routing.md", """
# Keypoint-to-multimodel routing
关键点是否介入多模型思考，不按重要性单轴决定，而按 complexity、uncertainty、reflexivity、blast radius 四轴决定。
""")
    write(root / "04-知识原子" / "atoms" / "minority-opinion-and-model-authority.md", """
# 少数意见：模型名不是证据，模型名不等于权威
模型名不是证据；低价模型少数意见也必须进入 issue ledger。
""")
    return root


def taskpool_fixture() -> dict:
    return {
        "status": "OK",
        "selected_task_id": "task-1",
        "queued_count": 3,
        "convergence": {"total_active": 3, "multimodel_passed": 1, "multimodel_triggered": 2, "pass_rate": 0.33, "trigger_rate": 0.66},
        "selected": {
            "pua_loop": {
                "mode": "continue_until_multimodel_pass",
                "completion_signal": "LOOP_DONE only after target-bound 4/4 ratification-gate PASS",
            },
            "build_state_command": "consult_models.py state q --claim C1 --claim C2 --claim C3 --evidence-json {}",
            "run_discussion_command": "python3 consult_models.py run state.json --tier T3 --quorum 4 --discussion --keep",
        },
    }


def test_full_fixture_passes_with_100_percent_keypoint_coverage():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        report = module.evaluate(build_vault(Path(td)), taskpool_json=taskpool_fixture())
        assert report["status"] == "PASS", report["failed_checks"]
        assert report["coverage"]["keypoints"]["percent"] == 100.0, report
        assert report["coverage"]["keypoints"]["covered"] == 22, report


def test_missing_keypoint_fails_closed_even_if_declared_22_22():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        vault = build_vault(Path(td))
        review = vault / "06-治理与评审" / "reviews" / "2026-05-06-multimodel-thinking-keypoint-coverage-review.md"
        text = review.read_text(encoding="utf-8").replace("| 21 | 少数意见/模型名不等于权威 | covered |", "| 21 | 少数意见/模型名不等于权威 | missing |")
        review.write_text(text, encoding="utf-8")
        report = module.evaluate(vault, taskpool_json=taskpool_fixture())
        assert report["status"] == "FAIL", report
        names = {c["name"] for c in report["failed_checks"]}
        assert "keypoint:少数意见/模型名不等于权威" in names, names


def test_taskpool_command_must_remain_T3_quorum4_discussion():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        fixture = taskpool_fixture()
        fixture["selected"]["run_discussion_command"] = "python3 consult_models.py run state.json --tier T2 --quorum 3 --discussion --keep"
        report = module.evaluate(build_vault(Path(td)), taskpool_json=fixture)
        assert report["status"] == "FAIL", report
        names = {c["name"] for c in report["failed_checks"]}
        assert "taskpool:run_command_T3_quorum4_discussion" in names, names


def test_taskpool_command_rejects_substring_flag_spoofing():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        fixture = taskpool_fixture()
        fixture["selected"]["run_discussion_command"] = "python3 consult_models.py run state.json --tier T30 --quorum 40 --discussion --keep"
        report = module.evaluate(build_vault(Path(td)), taskpool_json=fixture)
        assert report["status"] == "FAIL", report
        names = {c["name"] for c in report["failed_checks"]}
        assert "taskpool:run_command_T3_quorum4_discussion" in names, names


def test_taskpool_dry_run_timeout_is_structured_and_kills_process_group():
    module = load_module()
    marker = "hermes-ratchet-timeout-fixture"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        scripts = root / "scripts"
        scripts.mkdir(parents=True)
        script = scripts / "brain_task_orchestrator.py"
        script.write_text(
            "import signal, subprocess, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "subprocess.Popen([sys.executable, '-c', 'import signal, time, sys; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)', 'hermes-ratchet-timeout-fixture'])\n"
            "time.sleep(30)\n",
            encoding="utf-8",
        )
        original_home = module.HERMES_HOME
        module.HERMES_HOME = root
        try:
            result = module.run_taskpool_dry_run(timeout=0.05)
        finally:
            module.HERMES_HOME = original_home
        assert result["status"] == "ERROR", result
        assert result["returncode"] == "timeout", result
        assert result["reason"] == "subprocess_timeout", result
        assert result["process_group_terminated"] is True, result
        assert result["process_group_killed"] is True, result
        time.sleep(0.2)
        ps = subprocess.check_output(["ps", "-axo", "command"], text=True)
        leftovers = [line for line in ps.splitlines() if marker in line and "ps -axo" not in line]
        assert leftovers == [], leftovers


def test_dispatch_tick_source_contract_fails_without_double_gate():
    module = load_module()
    broken = """
parser.add_argument("--multimodel-step")
if os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL") == "1":
    run_json(["multimodel-intervention-step"])
"""
    result = module.check_dispatch_tick_source(broken)
    assert result["status"] == "FAIL", result
    names = {c["name"] for c in result["checks"] if not c["ok"]}
    assert "autorun:multimodel_step_double_gated_by_flag_and_env" in names, names
    assert "autorun:ambient_env_without_flag_skips_expensive_step" in names, names
    assert "autorun:long_running_timeout_is_structured" in names, names


def test_cli_writes_json_and_markdown_report():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        vault = build_vault(root / "brain")
        fixture = write(root / "taskpool.json", json.dumps(taskpool_fixture()))
        out_json = root / "report.json"
        out_md = root / "report.md"
        env = dict(**__import__("os").environ, HERMES_BRAIN_VAULT=str(vault))
        r = subprocess.run([
            sys.executable,
            str(SCRIPT),
            "--taskpool-json",
            str(fixture),
            "--write-json",
            str(out_json),
            "--write-report",
            str(out_md),
            "--json",
        ], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr or r.stdout
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        assert payload["status"] == "PASS", payload
        assert "多模型关键点棘轮覆盖复审" in out_md.read_text(encoding="utf-8")


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    for name in tests:
        globals()[name]()
    print(f"PASS {len(tests)} tests")
