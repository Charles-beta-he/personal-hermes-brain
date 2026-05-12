#!/usr/bin/env python3
"""Fail-closed ratchet for multi-model keypoint coverage in the local brain.

This verifier turns the previously prose-only "22/22 covered" review into a
machine-checkable gate. It is local-first: no network, no LLM calls, no writes
unless --write-report is explicitly provided.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import signal
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TZ = timezone(timedelta(hours=8))
HOME = Path.home()
VAULT = Path(os.environ.get("HERMES_BRAIN_VAULT", str(HOME / "Documents" / "brain"))).expanduser()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser()

REVIEW = VAULT / "06-治理与评审" / "reviews" / "2026-05-06-multimodel-thinking-keypoint-coverage-review.md"
ROUTE_MATRIX = VAULT / "05-实践与项目" / "实践方案" / "07-关键点多模型介入路由矩阵.md"
ROUTING_ATOM = VAULT / "04-知识原子" / "atoms" / "keypoint-to-multimodel-routing.md"
MINORITY_ATOM = VAULT / "04-知识原子" / "atoms" / "minority-opinion-and-model-authority.md"

REQUIRED_KEYPOINTS = [
    "四模型/互补模型组合",
    "fanout/provenance 与认证分离",
    "多模型一致不是证据",
    "Evidence-first / 工具证据优先",
    "truth gate / unsupported claims 阻断认证",
    "state/state_hash/artifact 固定输入与可复现",
    "Blind seed proposals / 独立初始方案",
    "disagreement / issue ledger",
    "cross-critique / AMEND/REJECT/APPROVE",
    "rebuttal / revision / discussion round",
    "red-team / devil advocate",
    "ratification / stop condition",
    "communication budget / 索引卡+差异",
    "not_certified caveat 明确记录",
    "本地大脑分类落地：reviews/tasks/evidence/evolution",
    "sync/reindex/search 作为落地证明",
    "anti-drift 双轨：deterministic oracle + LLM critic",
    "模型角色边界：orchestrator 执行工具，reviewer 提证据请求/风险",
    "quorum/T2/T3/四模型不得偷省",
    "consult_models.py CLI/artifact 使用方式",
    "少数意见/模型名不等于权威",
    "final synthesis/provenance/remaining risks 记录",
]

ROUTE_KEYPOINTS = [
    "必要多样性",
    "反馈回路与稳定性",
    "置信度校准",
    "双环学习",
    "技能生态治理",
    "source of truth",
    "信息-通信-熵",
    "稳态/内稳态/自适应",
    "可靠性理论",
    "Parnas",
    "少数意见/模型名不是权威",
    "通信预算/上下文压缩",
]

RATCHET_RULES = [
    "coverage_count_exact_22_of_22",
    "every_required_keypoint_present_once_or_more",
    "every_keypoint_status_is_covered_or_thin_not_missing",
    "minority_opinion_has_independent_atom",
    "caveats_preserve_not_certified_dissent_timeout",
    "routing_matrix_has_T0_T1_T2_T3_and_tool_evidence",
    "routing_atom_has_four_axis_rule_complexity_uncertainty_reflexivity_blast_radius",
    "taskpool_dry_run_keeps_T3_quorum4_discussion_for_pua_loop_when_checked",
    "autorun_multimodel_step_is_double_gated_by_cli_flag_and_env",
    "autorun_long_running_timeout_is_structured_not_traceback",
]

TABLE_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")


def iso() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def ok_status(status: str) -> bool:
    s = status.strip().lower()
    if not s:
        return False
    bad_markers = ["missing", "uncovered", "todo", "gap", "缺", "未覆盖"]
    if any(x in s for x in bad_markers):
        return False
    return s.startswith("covered") or "已落地" in s or "已覆盖" in s


def parse_keypoint_table(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        m = TABLE_RE.match(line)
        if not m:
            continue
        idx, keypoint, status = m.groups()
        rows.append({"index": int(idx), "keypoint": keypoint.strip(), "status": status.strip(), "covered": ok_status(status)})
    return rows


def run_taskpool_dry_run(timeout: int = 120) -> dict[str, Any]:
    cmd = [sys.executable, str(HERMES_HOME / "scripts" / "brain_task_orchestrator.py"), "multimodel-intervention-dry-run", "--json"]
    proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process_group_terminated = terminate_process_group(proc, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=2)
            process_group_killed = False
        except subprocess.TimeoutExpired:
            process_group_killed = terminate_process_group(proc, signal.SIGKILL)
            out, err = proc.communicate()
        return {
            "status": "ERROR",
            "returncode": "timeout",
            "reason": "subprocess_timeout",
            "timeout_seconds": timeout,
            "process_group_terminated": process_group_terminated,
            "process_group_killed": process_group_killed,
            "stdout_tail": (out or "")[-2000:],
            "stderr_tail": (err or "")[-2000:],
        }
    if proc.returncode != 0:
        return {"status": "ERROR", "returncode": proc.returncode, "stdout_tail": (out or "")[-2000:], "stderr_tail": (err or "")[-2000:]}
    try:
        data = json.loads(out or "")
        data["_command"] = " ".join(cmd)
        return data
    except Exception as exc:
        return {"status": "ERROR", "returncode": proc.returncode, "reason": f"json_parse_failed:{type(exc).__name__}:{exc}", "stdout_tail": (out or "")[-2000:]}


def terminate_process_group(proc: subprocess.Popen[Any], sig: int) -> bool:
    try:
        os.killpg(os.getpgid(proc.pid), sig)
        return True
    except ProcessLookupError:
        return True
    except Exception:
        try:
            if sig == signal.SIGKILL:
                proc.kill()
            else:
                proc.terminate()
        except Exception:
            return False
        return False


def command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def has_exact_flag(tokens: list[str], flag: str, value: str | None = None) -> bool:
    for idx, token in enumerate(tokens):
        if token == flag:
            return value is None or (idx + 1 < len(tokens) and tokens[idx + 1] == value)
        if value is not None and token == f"{flag}={value}":
            return True
    return False


def check_dispatch_tick_source(tick_text: str) -> dict[str, Any]:
    """Static fail-closed checks for the autorun/multimodel tick contract."""
    checks = [
        {
            "name": "autorun:explicit_multimodel_step_flag",
            "ok": "--multimodel-step" in tick_text and "args.multimodel_step" in tick_text,
            "value": {"has_flag": "--multimodel-step" in tick_text, "uses_args_flag": "args.multimodel_step" in tick_text},
        },
        {
            "name": "autorun:multimodel_step_double_gated_by_flag_and_env",
            "ok": "args.multimodel_step and os.environ.get(\"HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL\") == \"1\"" in tick_text,
            "value": "explicit flag + HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1",
        },
        {
            "name": "autorun:ambient_env_without_flag_skips_expensive_step",
            "ok": "autorun_multimodel_disabled" in tick_text and "Ambient HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1" in tick_text,
            "value": {"has_skip_reason": "autorun_multimodel_disabled" in tick_text},
        },
        {
            "name": "autorun:long_running_timeout_is_structured",
            "ok": "subprocess.TimeoutExpired" in tick_text and "subprocess_timeout" in tick_text and "timeout_seconds" in tick_text and "start_new_session=True" in tick_text and "process_group_terminated" in tick_text,
            "value": {"timeout_exception": "subprocess.TimeoutExpired" in tick_text, "reason": "subprocess_timeout" in tick_text, "new_process_group": "start_new_session=True" in tick_text},
        },
    ]
    return {"status": "PASS" if all(c["ok"] for c in checks) else "FAIL", "checks": checks}


def check_taskpool(data: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    status_ok = data.get("status") == "OK"
    checks.append({"name": "taskpool:dry_run_status_ok", "ok": status_ok, "value": data.get("status")})
    selected = data.get("selected") if isinstance(data.get("selected"), dict) else {}
    pua_loop = selected.get("pua_loop") if isinstance(selected.get("pua_loop"), dict) else {}
    run_cmd = str(selected.get("run_discussion_command") or "")
    run_tokens = command_tokens(run_cmd)
    build_cmd = str(selected.get("build_state_command") or "")
    build_tokens = command_tokens(build_cmd)
    checks.extend([
        {"name": "taskpool:pua_loop_mode_present", "ok": pua_loop.get("mode") == "continue_until_multimodel_pass", "value": pua_loop.get("mode")},
        {"name": "taskpool:completion_signal_loop_done_bound_to_gate", "ok": "LOOP_DONE" in str(pua_loop.get("completion_signal") or "") and "4/4" in str(pua_loop.get("completion_signal") or ""), "value": pua_loop.get("completion_signal")},
        {"name": "taskpool:run_command_T3_quorum4_discussion", "ok": has_exact_flag(run_tokens, "--tier", "T3") and has_exact_flag(run_tokens, "--quorum", "4") and has_exact_flag(run_tokens, "--discussion") and has_exact_flag(run_tokens, "--keep"), "value": run_cmd},
        {"name": "taskpool:build_state_has_claims", "ok": build_tokens.count("--claim") >= 3 and has_exact_flag(build_tokens, "--evidence-json"), "value": {"claim_flags": build_tokens.count("--claim"), "has_evidence_json": has_exact_flag(build_tokens, "--evidence-json")}},
    ])
    conv = data.get("convergence") if isinstance(data.get("convergence"), dict) else {}
    checks.append({"name": "taskpool:convergence_stats_present", "ok": all(k in conv for k in ["total_active", "multimodel_passed", "multimodel_triggered", "pass_rate", "trigger_rate"]), "value": conv})
    return {"status": "PASS" if all(c["ok"] for c in checks) else "FAIL", "checks": checks, "selected_task_id": data.get("selected_task_id"), "queued_count": data.get("queued_count"), "convergence": conv}


def evaluate(vault: Path = VAULT, taskpool_json: dict[str, Any] | None = None, skip_taskpool: bool = False) -> dict[str, Any]:
    review = vault / "06-治理与评审" / "reviews" / "2026-05-06-multimodel-thinking-keypoint-coverage-review.md"
    route_matrix = vault / "05-实践与项目" / "实践方案" / "07-关键点多模型介入路由矩阵.md"
    routing_atom = vault / "04-知识原子" / "atoms" / "keypoint-to-multimodel-routing.md"
    minority_atom = vault / "04-知识原子" / "atoms" / "minority-opinion-and-model-authority.md"

    checks: list[dict[str, Any]] = []
    files = {"review": review, "route_matrix": route_matrix, "routing_atom": routing_atom, "minority_atom": minority_atom}
    texts: dict[str, str] = {}
    for name, path in files.items():
        exists = path.exists()
        checks.append({"name": f"file:{name}", "ok": exists, "path": str(path)})
        texts[name] = read(path) if exists else ""

    rows = parse_keypoint_table(texts.get("review", ""))
    by_keypoint = {r["keypoint"]: r for r in rows}
    declared = re.search(r"coverage:\s*(\d+)\s*/\s*(\d+)", texts.get("review", ""))
    declared_pair = (int(declared.group(1)), int(declared.group(2))) if declared else (None, None)
    checks.append({"name": "review:declared_coverage_22_22", "ok": declared_pair == (22, 22), "value": declared_pair})
    checks.append({"name": "review:table_row_count_22", "ok": len(rows) == 22, "value": len(rows)})
    for keypoint in REQUIRED_KEYPOINTS:
        row = by_keypoint.get(keypoint)
        checks.append({"name": f"keypoint:{keypoint}", "ok": bool(row and row.get("covered")), "status": row.get("status") if row else None})
    caveat_text = texts.get("review", "")
    checks.append({"name": "review:caveat_preserves_not_certified_dissent_timeout", "ok": all(x in caveat_text for x in ["not_certified", "dissent", "timeout"]), "value": {"not_certified": "not_certified" in caveat_text, "dissent": "dissent" in caveat_text, "timeout": "timeout" in caveat_text}})
    checks.append({"name": "minority_atom:model_name_not_authority", "ok": "模型名" in texts.get("minority_atom", "") and ("不是证据" in texts.get("minority_atom", "") or "不等于权威" in texts.get("minority_atom", "")), "path": str(minority_atom)})

    rm = texts.get("route_matrix", "")
    for keypoint in ROUTE_KEYPOINTS:
        checks.append({"name": f"route_matrix:{keypoint}", "ok": keypoint in rm})
    for level in ["T0", "T1", "T2", "T3"]:
        checks.append({"name": f"route_matrix:{level}", "ok": level in rm})
    checks.append({"name": "route_matrix:tool_evidence_required", "ok": "Tool evidence required" in rm and "yes" in rm})
    atom = texts.get("routing_atom", "")
    for axis in ["complexity", "uncertainty", "reflexivity", "blast radius"]:
        checks.append({"name": f"routing_atom:axis:{axis}", "ok": axis in atom})

    taskpool = {"status": "SKIPPED", "checks": []}
    if not skip_taskpool:
        raw = taskpool_json if taskpool_json is not None else run_taskpool_dry_run()
        taskpool = check_taskpool(raw)
        checks.extend(taskpool["checks"])

    tick_path = HERMES_HOME / "scripts" / "brain_task_dispatch_tick.py"
    tick_exists = tick_path.exists()
    checks.append({"name": "file:brain_task_dispatch_tick", "ok": tick_exists, "path": str(tick_path)})
    tick = check_dispatch_tick_source(read(tick_path) if tick_exists else "")
    checks.extend(tick["checks"])

    passed = [c for c in checks if c.get("ok")]
    failed = [c for c in checks if not c.get("ok")]
    coverage_denominator = len(checks)
    coverage_numerator = len(passed)
    keypoint_passed = sum(1 for k in REQUIRED_KEYPOINTS if (by_keypoint.get(k) or {}).get("covered"))
    report = {
        "schema": "multimodel_keypoint_coverage_ratchet_v1",
        "generated_at": iso(),
        "status": "PASS" if not failed else "FAIL",
        "vault": str(vault),
        "ratchet_rules": RATCHET_RULES,
        "coverage": {
            "declared": f"{declared_pair[0]}/{declared_pair[1]}" if declared_pair[0] is not None else None,
            "keypoints": {"covered": keypoint_passed, "total": len(REQUIRED_KEYPOINTS), "percent": round(keypoint_passed / len(REQUIRED_KEYPOINTS) * 100, 2)},
            "gate_checks": {"passed": coverage_numerator, "total": coverage_denominator, "percent": round(coverage_numerator / max(1, coverage_denominator) * 100, 2)},
        },
        "checks": checks,
        "failed_checks": failed,
        "taskpool": taskpool,
    }
    return report


def markdown_report(report: dict[str, Any]) -> str:
    cov = report["coverage"]
    failed = report.get("failed_checks") or []
    tp = report.get("taskpool") or {}
    lines = [
        "---",
        "type: review",
        "status: active",
        f"created: {report['generated_at']}",
        "review_subject: multimodel-keypoint-ratchet-coverage",
        f"coverage: {cov['keypoints']['covered']}/{cov['keypoints']['total']}",
        "concepts: [multi-model-thinking, keypoint-coverage, ratchet, taskpool-flow]",
        "---",
        "",
        "# 多模型关键点棘轮覆盖复审",
        "",
        "## 结论",
        "",
        f"- Gate status: `{report['status']}`",
        f"- 关键点覆盖: `{cov['keypoints']['covered']}/{cov['keypoints']['total']}` (`{cov['keypoints']['percent']}%`)",
        f"- 棘轮检查: `{cov['gate_checks']['passed']}/{cov['gate_checks']['total']}` (`{cov['gate_checks']['percent']}%`)",
        f"- 任务池 dry-run: `{tp.get('status')}`; queued=`{tp.get('queued_count')}`; selected=`{tp.get('selected_task_id')}`",
        "",
        "## 棘轮规则",
        "",
    ]
    lines.extend(f"- {rule}" for rule in report.get("ratchet_rules", []))
    lines.extend(["", "## 未通过检查", ""])
    if failed:
        for c in failed:
            lines.append(f"- `{c.get('name')}`: `{c.get('value', c.get('status', ''))}`")
    else:
        lines.append("- 无。当前“值得多模型分析”的关键点覆盖率达到 100%，且任务池 PUA-loop 生成命令保持 T3/quorum4/discussion 棘轮。")
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        "本复审是 deterministic ratchet gate，不伪造当前任务的四模型认证。任务池中仍为 not_certified/pending 的任务必须继续走目标绑定 T3 + ratification-gate；本页只证明关键点覆盖规则本身没有回退。",
        "",
        "## 中文检索别名",
        "",
        "多模型关键点棘轮覆盖 关键点覆盖 棘轮检查 任务池流转 T3 quorum4 discussion PUA-loop",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip-taskpool", action="store_true")
    ap.add_argument("--taskpool-json", type=Path)
    ap.add_argument("--write-report", type=Path, help="Write Markdown report to this path")
    ap.add_argument("--write-json", type=Path, help="Write JSON report to this path")
    args = ap.parse_args()

    taskpool_json = None
    if args.taskpool_json:
        taskpool_json = json.loads(args.taskpool_json.read_text(encoding="utf-8"))
    report = evaluate(VAULT, taskpool_json=taskpool_json, skip_taskpool=args.skip_taskpool)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(markdown_report(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report["status"])
        print(f"keypoint_coverage={report['coverage']['keypoints']['covered']}/{report['coverage']['keypoints']['total']} gate_coverage={report['coverage']['gate_checks']['passed']}/{report['coverage']['gate_checks']['total']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
