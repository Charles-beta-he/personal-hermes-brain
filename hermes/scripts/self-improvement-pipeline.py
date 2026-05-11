#!/usr/bin/env python3
"""
Self-Improvement Pipeline — 自进化优先调度层
统一信号聚合 → 优先级排序 → 自主执行

用法:
  # 查看所有信号源的分析和建议
  python3 ~/.hermes/scripts/self-improvement-pipeline.py

  # 全量分析 + 写入 action list
  python3 ~/.hermes/scripts/self-improvement-pipeline.py --write

  # 自主执行模式（自动 dispatch 到各 actuator）
  python3 ~/.hermes/scripts/self-improvement-pipeline.py --auto-exec

  # 只读模式查看当前优先级队列
  python3 ~/.hermes/scripts/self-improvement-pipeline.py --preview
"""

import os, sys, json, datetime, math
from collections import Counter, defaultdict
from pathlib import Path

NOTES_DIR = os.path.expanduser("~/.hermes/notes")
SIGNALS_PATH = os.path.join(NOTES_DIR, "improvement-signals.jsonl")
HEALTH_PATH = os.path.join(NOTES_DIR, "engineering-cybernetics", "health-history.jsonl")
PATTERNS_PATH = os.path.join(NOTES_DIR, "user-routine-patterns.json")
DARWIN_RESULTS = os.path.expanduser("~/.hermes/skills/darwin-skill/results.tsv")
ACTION_PATH = os.path.join(NOTES_DIR, "improvement-action-plan.json")
EVOLUTION_PATH = os.path.expanduser("~/.pua/evolution.md")
USAGE_SCORE_PATH = os.path.expanduser("~/.hermes/state/usage-score.json")
STALE_TRANSIENT_HOURS = 72
STALE_TRANSIENT_MAX_HOURS = 168
EVOLVE_LOG_PATH = os.path.expanduser("~/.hermes/logs/evolve.log")
DIAGNOSTICS_DIR = os.path.join(NOTES_DIR, "tool-failure-diagnostics")
ACTIONABLE_ROI_MIN = 2.0
ACTIONABLE_IMPACT_MIN = 4

os.makedirs(NOTES_DIR, exist_ok=True)

def parse_iso(ts):
    """Parse common ISO timestamps used by Hermes notes/logs."""
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def signal_age_hours(sig):
    t = parse_iso(sig.get("_parent_timestamp") or sig.get("timestamp"))
    if not t:
        return None
    return (datetime.datetime.now() - t).total_seconds() / 3600


def current_ops_healthy():
    """Return True when current operational checks show the old transient errors are closed."""
    try:
        data = json.loads(Path(USAGE_SCORE_PATH).read_text())
        cron = data.get("components", {}).get("cron_green", {})
        return data.get("grade") == "A" and int(cron.get("bad") or 0) == 0
    except Exception:
        return False


def is_stale_transient_signal(sig):
    """Suppress old tool-failure ghosts once closed, and always after 7d.

    Tool-failure autopsy records are point-in-time evidence. Keeping an old
    terminal failure HIGH forever creates a ghost queue: the pipeline keeps
    asking for work even after current traces/self-tests are healthy. Live
    failures will be re-emitted by fresh autopsy records inside the 7d window.
    """
    if sig.get("type") != "tool_failures":
        return False
    age = signal_age_hours(sig)
    if age is None:
        return False
    if age > STALE_TRANSIENT_MAX_HOURS:
        return True
    return current_ops_healthy() and age > STALE_TRANSIENT_HOURS


# ─── Signal Sources ───

def load_signals(max_age_days=30):
    """从 improvement-signals.jsonl 加载信号"""
    signals = []
    if not os.path.exists(SIGNALS_PATH):
        return signals
    cutoff = datetime.datetime.now() - datetime.timedelta(days=max_age_days)
    with open(SIGNALS_PATH, "r") as f:
        for line in f:
            try:
                s = json.loads(line)
                ts = s.get("timestamp", "")
                if ts:
                    try:
                        t = datetime.datetime.fromisoformat(ts)
                        if t < cutoff:
                            continue
                    except ValueError:
                        pass
                for sig in s.get("signals", []):
                    sig.setdefault("_parent_timestamp", ts)
                signals.append(s)
            except json.JSONDecodeError:
                continue
    return signals


def load_health_records(max_count=100):
    """从 health-history.jsonl 加载健康记录"""
    records = []
    if not os.path.exists(HEALTH_PATH):
        return records
    with open(HEALTH_PATH, "r") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records[-max_count:]


def load_patterns():
    """加载用户行为模式"""
    if not os.path.exists(PATTERNS_PATH):
        return {"task_types": {}, "time_slots": {}, "preferences": {}}
    with open(PATTERNS_PATH, "r") as f:
        return json.load(f)


def load_darwin_results(max_count=None):
    """加载 Darwin 优化记录。

    Use all rows by default: priority generation later collapses to the latest
    row per skill, and truncating raw rows can drop the actual latest accepted
    fix while retaining an older low baseline.
    """
    records = []
    if not os.path.exists(DARWIN_RESULTS):
        return records
    with open(DARWIN_RESULTS, "r") as f:
        # 跳过表头
        header = f.readline()
        for line in f:
            try:
                cols = line.strip().split("\t")
                if len(cols) >= 8:
                    records.append({
                        "timestamp": cols[0], "skill": cols[2],
                        "old_score": cols[3], "new_score": cols[4],
                        "status": cols[5], "note": cols[7] if len(cols) > 7 else "",
                    })
            except (IndexError, ValueError):
                continue
    return records[-max_count:] if max_count else records


# ─── Prioritization Engine ───

class ActionItem:
    """表示一个可执行的改进动作"""

    # Impact categories (higher = more valuable)
    IMPACT_LEVELS = {
        "critical": 10,   # 影响每次 session
        "high": 7,        # 影响多数 session
        "medium": 4,      # 偶尔有用
        "low": 2,         # 锦上添花
        "info": 1,        # 了解就行
    }

    # Effort categories (lower = easier)
    EFFORT_LEVELS = {
        "trivial": 1,     # 1 行改动
        "small": 2,       # 改一个文件
        "medium": 4,      # 改多个文件
        "large": 7,       # 新建脚本/skill
        "complex": 10,    # 跨模块改造
    }

    def __init__(self, act_type, summary, impact, effort,
                 detail="", suggestion="", source="", category=""):
        self.act_type = act_type
        self.summary = summary
        self.impact = self.IMPACT_LEVELS.get(impact, 3)
        self.impact_label = impact
        self.effort = self.EFFORT_LEVELS.get(effort, 3)
        self.effort_label = effort
        self.detail = detail
        self.suggestion = suggestion
        self.source = source
        self.category = category
        self.roi = self.impact / max(self.effort, 0.5)
        self.created_at = datetime.datetime.now().isoformat()

    def __repr__(self):
        sev = {10: "!!", 7: "! ", 4: "- ", 2: ". ", 1: "  "}.get(self.impact, "  ")
        return f"{sev} [roi={self.roi:.1f}] {self.summary} ({self.impact_label}/{self.effort_label})"


def aggregate_items(signals, health_records, patterns, darwin_records):
    """从所有信号源生成改进动作列表"""
    items = []

    # ── Source 1: Session Autopsy Signals ──
    # 按类型聚合
    type_signals = defaultdict(list)
    for s in signals:
        for sig in s.get("signals", []):
            type_signals[sig["type"]].append(sig)

    # 高频纠正 → memory/skill 动作
    correction_sigs = type_signals.get("frequent_corrections", [])
    if correction_sigs:
        total = sum(s.get("count", 0) for s in correction_sigs)
        items.append(ActionItem(
            "add_memory_or_skill", f"用户频繁纠正共 {total} 次，需补充对应记忆",
            "high", "small",
            detail=f"跨 {len(correction_sigs)} 个 session 累计 {total} 次纠正",
            suggestion="运行 post-session-autopsy.py --recent 10 查看具体纠正内容，确认是否需要补充 memory 或创建 skill",
            source="session_autopsy", category="user_experience"
        ))

    # 工具失败 → 配置/脚本修复
    failure_sigs = [s for s in type_signals.get("tool_failures", []) if not is_stale_transient_signal(s)]
    if failure_sigs:
        # Prefer structured failure groups. Keep old detail strings as fallback so
        # historical signals remain readable but no longer drive auto-config edits.
        grouped = Counter()
        group_payload = {}
        total_failures = sum(s.get("count", 0) for s in failure_sigs)
        for s in failure_sigs:
            groups = s.get("failure_groups") or []
            if isinstance(groups, list) and groups:
                for g in groups:
                    if not isinstance(g, dict):
                        continue
                    key = (
                        str(g.get("tool_name") or g.get("tool") or "unknown"),
                        str(g.get("error_signature") or "unknown"),
                        str(g.get("exit_code") if g.get("exit_code") is not None else ""),
                    )
                    count = int(g.get("count") or 1)
                    grouped[key] += count
                    merged = group_payload.setdefault(key, dict(g))
                    merged["count"] = grouped[key]
            else:
                detail = str(s.get("detail", "unknown_failure"))
                key = (detail[:80], "legacy_detail", "")
                grouped[key] += int(s.get("count") or 1)
                group_payload.setdefault(key, {
                    "tool_name": detail[:80],
                    "error_signature": "legacy_detail",
                    "exit_code": None,
                    "count": 0,
                    "stale_status": "unknown",
                })["count"] = grouped[key]
        if grouped:
            (tool, signature, exit_code), worst_count = grouped.most_common(1)[0]
            groups_out = []
            for key, count in grouped.most_common(10):
                g = dict(group_payload.get(key) or {})
                g.setdefault("tool_name", key[0])
                g.setdefault("error_signature", key[1])
                g.setdefault("exit_code", key[2] or None)
                g["count"] = count
                groups_out.append(g)
            detail_payload = json.dumps({"failure_groups": groups_out}, ensure_ascii=False, sort_keys=True)
            items.append(ActionItem(
                "fix_tool_config", f"工具失败 {total_failures} 次 ({tool}/{signature}: {worst_count} 次)",
                "high" if len(failure_sigs) >= 3 else "medium",
                "medium",
                detail=detail_payload,
                suggestion="生成只读工具失败诊断；不要在缺少精确 tool/error signature 前自动改配置",
                source="session_autopsy", category="reliability"
            ))

    # ── Source 2: Health Records ──
    if health_records:
        # 用户纠正率趋势
        recent = health_records[-20:]
        corr_counts = [r.get("user_corrections", 0) or 0 for r in recent]
        avg_corr = sum(corr_counts) / max(len(corr_counts), 1)
        if avg_corr >= 2:
            items.append(ActionItem(
                "improve_accuracy", f"近期平均纠正率 {avg_corr:.1f}/session，偏高",
                "medium", "medium",
                detail=f"最近 {len(recent)} 个 session 平均纠正 {avg_corr:.1f} 次",
                suggestion="检查 session 记录，识别最常出错的 task type",
                source="health_history", category="user_experience"
            ))

        # V 函数趋势
        v_values = [r.get("V", 1.0) for r in recent if r.get("V")]
        if len(v_values) >= 5:
            avg_v = sum(v_values) / len(v_values)
            if avg_v < 0.6:
                items.append(ActionItem(
                    "escalate_health", f"系统健康度 V={avg_v:.2f}，低于阈值 0.6",
                    "critical", "large",
                    detail=f"最近 {len(v_values)} 个 session 平均 V={avg_v:.2f}",
                    suggestion="运行 agent-health-monitor.py 诊断详细原因",
                    source="health_history", category="system_health"
                ))

    # ── Source 3: User Patterns ──
    task_types = patterns.get("task_types", {})
    if task_types:
        total_tasks = sum(task_types.values())
        # 检测新出现的频繁任务类型
        for ttype, count in sorted(task_types.items(), key=lambda x: x[1], reverse=True):
            ratio = count / max(total_tasks, 1)
            if ratio >= 0.3 and count >= 5:
                items.append(ActionItem(
                    "optimize_common_task", f"'{ttype}' 任务占比 {ratio:.0%} ({count}次)，应考虑 skill 优化",
                    "medium", "medium",
                    detail=f"高频任务类型，占比 {ratio:.0%}",
                    suggestion=f"检查是否有针对 '{ttype}' 的专用 skill",
                    source="user_patterns", category="task_coverage"
                ))

    # ── Source 4: Darwin Results ──
    if darwin_records:
        revert_count = sum(1 for r in darwin_records if r["status"] == "revert")
        if revert_count >= 3:
            items.append(ActionItem(
                "review_darwin_failures", f"Darwin 优化回滚 {revert_count} 次，需人工审查",
                "medium", "small",
                detail=f"最近 {len(darwin_records)} 条 Darwin 记录中 {revert_count} 次回滚",
                suggestion="检查 darwin-skill/results.tsv 了解具体回滚原因",
                source="darwin", category="skill_quality"
            ))

        # 低分 skill 列表：只看每个 skill 的最新 Darwin 记录，避免旧 baseline
        # 在已修复后继续产生幽灵优先级。
        latest_by_skill = {}
        for r in darwin_records:
            latest_by_skill[r.get("skill", "")] = r
        low_skills = set()
        for skill, r in latest_by_skill.items():
            if not skill:
                continue
            try:
                ns = int(r.get("new_score", 0))
                if ns < 60:
                    low_skills.add(skill)
            except (TypeError, ValueError):
                continue
        if low_skills:
            items.append(ActionItem(
                "improve_low_skills", f"{len(low_skills)} 个 skill 评分 < 60: {', '.join(list(low_skills)[:5])}",
                "medium", "medium",
                detail=f"低分 skill 列表: {', '.join(low_skills)}",
                suggestion="对最低分的 2-3 个 skill 执行 Darwin 优化",
                source="darwin", category="skill_quality"
            ))

    # 按 ROI 排序
    items.sort(key=lambda x: x.roi, reverse=True)
    return items


def deduplicate_items(items):
    """去重：合并相同 act_type + category 的动作"""
    seen = {}
    for item in items:
        key = (item.act_type, item.category)
        if key in seen:
            # 保留 ROI 更高的
            if item.roi > seen[key].roi:
                seen[key] = item
        else:
            seen[key] = item
    return list(seen.values())


# ─── Report Generation ───

def print_pipeline(items, signals_count=0, health_count=0):
    """打印管线报告"""
    print(f"\n{'=' * 60}")
    print(f"  Self-Improvement Pipeline — Priority Queue")
    print(f"{'=' * 60}")
    print(f"  Signal sources: {signals_count} autopsy | {health_count} health records")

    if not items:
        print(f"\n  ✓ 无待办改进项 — 系统健康")
        print(f"{'=' * 60}\n")
        return

    print(f"\n  {'ROI':<6} {'Impact':<10} {'Effort':<8} {'Category':<16} {'Action'}")
    print(f"  {'─'*5} {'─'*9} {'─'*7} {'─'*15} {'─'*40}")

    critical = [it for it in items if it.impact >= 9]
    high = [it for it in items if 6 <= it.impact < 9]
    medium = [it for it in items if 3 <= it.impact < 6]
    low = [it for it in items if it.impact < 3]

    for group, label in [(critical, "!! CRITICAL"), (high, "! HIGH"), (medium, "- MEDIUM"), (low, ". LOW")]:
        if group:
            print(f"\n  [{label}]")
            for it in group:
                s = {10: "!!", 7: "! ", 4: "- ", 2: ". ", 1: "  "}.get(it.impact, "  ")
                print(f"  {it.roi:>4.1f}x  {it.impact_label:<8} {it.effort_label:<7} {it.category:<15} {it.summary[:65]}")

    print(f"\n{'─' * 60}")
    print(f"  总计: {len(items)} 个改进动作")
    print(f"  {len(critical)} critical, {len(high)} high, {len(medium)} medium, {len(low)} low")
    print(f"{'=' * 60}\n")


def print_action_plan(items):
    """打印详细执行计划"""
    print(f"\n{'=' * 60}")
    print(f"  Improvement Action Plan")
    print(f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 60}")

    for i, it in enumerate(items, 1):
        roi_bar = "▓" * min(int(it.roi), 10) + "░" * max(10 - min(int(it.roi), 10), 0)
        print(f"\n  #{i} [ROI {it.roi:.1f}x] {roi_bar}")
        print(f"  ├─ Type:     {it.act_type}")
        print(f"  ├─ Impact:   {it.impact_label} ({it.impact}/10)")
        print(f"  ├─ Effort:   {it.effort_label} ({it.effort}/10)")
        print(f"  ├─ Category: {it.category}")
        print(f"  ├─ Source:   {it.source}")
        print(f"  ├─ Detail:   {it.detail}")
        print(f"  └─ Action:   {it.suggestion}")


def _parse_item_failure_groups(item):
    """Extract structured failure groups from an ActionItem detail field."""
    detail = item.detail or ""
    try:
        payload = json.loads(detail)
        groups = payload.get("failure_groups") if isinstance(payload, dict) else None
        if isinstance(groups, list) and groups:
            return [g for g in groups if isinstance(g, dict)]
    except Exception:
        pass
    return [{
        "tool_name": detail[:80] or "unknown",
        "error_signature": "legacy_detail" if detail else "unknown",
        "exit_code": None,
        "count": 1,
        "stale_status": "unknown",
        "stderr_tail": detail[:500],
    }]


def _load_usage_health_context():
    try:
        data = json.loads(Path(USAGE_SCORE_PATH).read_text())
    except Exception:
        return {"usage_grade": "unknown"}
    cron = data.get("components", {}).get("cron_green", {})
    semantic = data.get("semantic_grades", {})
    operational = semantic.get("operational_health", {}) if isinstance(semantic, dict) else {}
    return {
        "usage_grade": data.get("grade", "unknown"),
        "operational_health_grade": operational.get("grade"),
        "cron_bad_count": cron.get("bad"),
        "cron_recent_24h": cron.get("recent_24h"),
        "fallback_used": any(
            (c or {}).get("fallback_used") for c in (data.get("components") or {}).values() if isinstance(c, dict)
        ),
    }


def write_tool_failure_diagnostic(item, status="pending_review", reason="not_auto_safe"):
    """Write a read-only diagnostic artifact for fix_tool_config.

    This intentionally does not edit config files. It turns vague queue items into
    evidence that a human or later safe actuator can review.
    """
    os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
    ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    safe_ts = ts.replace(":", "").replace("Z", "Z")
    path = os.path.join(DIAGNOSTICS_DIR, f"tool-failure-diagnostic-{safe_ts}.json")
    diagnostic = {
        "schema": "tool_failure_diagnostic_v1",
        "schema_version": "tool_failure_diagnostic_v1",
        "generated_at": ts,
        "source": item.source or "self-improvement-pipeline",
        "action_type": item.act_type,
        "summary": item.summary,
        "status": status,
        "auto_edit_config": False,
        "threshold": {"roi_min": ACTIONABLE_ROI_MIN, "impact_min": ACTIONABLE_IMPACT_MIN},
        "item": {
            "roi": round(item.roi, 2),
            "impact": item.impact,
            "impact_label": item.impact_label,
            "effort": item.effort,
            "effort_label": item.effort_label,
            "category": item.category,
        },
        "health_context": _load_usage_health_context(),
        "failures": _parse_item_failure_groups(item),
        "recommendation": {
            "safe_next_action": "human_review_or_targeted_fix",
            "reason": reason,
        },
        "safe_next_action": "human_review_or_targeted_fix",
    }
    Path(path).write_text(json.dumps(diagnostic, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _action_state_summary(items, executed_actions=None, diagnostic_paths=None):
    executed_actions = executed_actions or []
    diagnostic_paths = diagnostic_paths or []
    actionable = [it for it in items if it.roi >= ACTIONABLE_ROI_MIN and it.impact >= ACTIONABLE_IMPACT_MIN]
    skipped_below = [it for it in items if it not in actionable]
    pending_review_count = sum(1 for a in executed_actions if a.get("status") in {"pending_review", "manual", "needs_data"})
    executed_diagnostic_paths = {a.get("diagnostic_path") for a in executed_actions if a.get("diagnostic_path")}
    unlinked_diagnostic_count = sum(1 for p in diagnostic_paths if p not in executed_diagnostic_paths)
    # Diagnostic artifacts are evidence, not applied runtime changes.
    executed_count = sum(1 for a in executed_actions if a.get("status") in {"applied", "executed", "auto_fixed"})
    top = items[0] if items else None
    skipped_reason = None
    if top and top in skipped_below:
        if top.roi < ACTIONABLE_ROI_MIN:
            skipped_reason = "roi_below_threshold"
        elif top.impact < ACTIONABLE_IMPACT_MIN:
            skipped_reason = "impact_below_threshold"
        else:
            skipped_reason = "below_threshold"
    return {
        "generated_count": len(items),
        "actionable_count": len(actionable),
        "executed_count": executed_count,
        "pending_review_count": pending_review_count + unlinked_diagnostic_count,
        "skipped_below_threshold_count": len(skipped_below),
        "top_item_type": top.act_type if top else None,
        "top_item_roi": round(top.roi, 2) if top else None,
        "top_item_impact": top.impact if top else None,
        "skipped_reason": skipped_reason,
        "diagnostic_paths": diagnostic_paths,
        "actionable_threshold": {"roi_min": ACTIONABLE_ROI_MIN, "impact_min": ACTIONABLE_IMPACT_MIN},
        "useful_evolution": executed_count > 0,
    }


def append_evolution_closure(items, mode="run", execution_summary=None):
    """Append an observable closure/noop event for non-preview pipeline ticks."""
    os.makedirs(os.path.dirname(EVOLVE_LOG_PATH), exist_ok=True)
    high = sum(1 for it in items if 6 <= it.impact < 9)
    critical = sum(1 for it in items if it.impact >= 9)
    base_summary = _action_state_summary(items)
    summary = {**base_summary, **(execution_summary or {})}
    executed_count = int(summary.get("executed_count") or 0)
    if not items:
        eval_result = "noop"
        diagnosis = "no actionable improvement items"
        eval_applicable = False
    elif executed_count <= 0:
        eval_result = "not_evaluated_no_execution"
        diagnosis = f"priority queue has {len(items)} item(s), but no runtime patch executed; critical={critical}, high={high}"
        eval_applicable = False
    else:
        eval_result = "not_evaluated_execution_without_metric"
        diagnosis = f"{executed_count} action(s) executed, but no before/after eval metric was supplied"
        eval_applicable = False
    event = {
        "ts": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "source": "self-improvement-pipeline",
        "mode": mode,
        "eval_result": eval_result,
        "eval_applicable": eval_applicable,
        "useful_evolution": bool(summary.get("useful_evolution") and eval_applicable),
        "diagnosis": diagnosis,
        "steps_count": len(items),
        "critical": critical,
        "high": high,
        **summary,
    }
    with open(EVOLVE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def save_action_plan(items):
    """保存 action plan 到 JSON"""
    plan = {
        "generated_at": datetime.datetime.now().isoformat(),
        "total_items": len(items),
        "summary": {
            "critical": sum(1 for it in items if it.impact >= 9),
            "high": sum(1 for it in items if 6 <= it.impact < 9),
            "medium": sum(1 for it in items if 3 <= it.impact < 6),
            "low": sum(1 for it in items if it.impact < 3),
        },
        "items": [
            {
                "rank": i,
                "type": it.act_type,
                "summary": it.summary,
                "impact": it.impact_label,
                "impact_score": it.impact,
                "effort": it.effort_label,
                "effort_score": it.effort,
                "roi": round(it.roi, 2),
                "category": it.category,
                "source": it.source,
                "detail": it.detail,
                "suggestion": it.suggestion,
            }
            for i, it in enumerate(items, 1)
        ]
    }
    with open(ACTION_PATH, "w") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"\n  Action plan saved to {ACTION_PATH}")


# ─── Auto-Execute Mode ───

def auto_execute(items):
    """自主执行模式 — dispatch 到各 actuator.

    Returns an action-state summary. Read-only diagnostics are allowed; runtime
    config edits are not performed from vague `fix_tool_config` aggregates.
    """
    print(f"\n{'=' * 60}")
    print(f"  Auto-Execute Mode")
    print(f"{'=' * 60}")

    actionable = [it for it in items if it.roi >= ACTIONABLE_ROI_MIN and it.impact >= ACTIONABLE_IMPACT_MIN]
    skipped_below = [it for it in items if it not in actionable]
    executed = []
    diagnostic_paths = []

    for it in skipped_below:
        if it.act_type == "fix_tool_config":
            path = write_tool_failure_diagnostic(it, status="pending_review", reason="roi_below_threshold_or_not_auto_safe")
            diagnostic_paths.append(path)
            print(f"  → Read-only diagnostic written: {path}")

    if not actionable:
        print("  No high-ROI actions to execute")
        return _action_state_summary(items, executed, diagnostic_paths)

    for it in actionable:
        print(f"\n  Executing: {it.summary}")

        if it.act_type == "add_memory_or_skill":
            # 运行 autopsy 获取详细内容
            print(f"  → Need more data: run autopsy to find exact correction patterns")
            executed.append({"action": it.act_type, "status": "needs_data", "detail": it.detail})

        elif it.act_type == "fix_tool_config":
            path = write_tool_failure_diagnostic(it, status="pending_review", reason="requires_precise_review_before_config_change")
            diagnostic_paths.append(path)
            print(f"  → Read-only diagnostic written: {path}")
            executed.append({"action": it.act_type, "status": "pending_review", "detail": it.detail, "diagnostic_path": path})

        elif it.act_type == "improve_low_skills":
            print(f"  → Could dispatch to Darwin skill optimizer")
            executed.append({"action": it.act_type, "status": "can_auto_optimize", "detail": it.detail})

        else:
            print(f"  → Requires manual review")
            executed.append({"action": it.act_type, "status": "manual", "detail": it.detail})

    # 记录执行日志
    exec_log = {
        "timestamp": datetime.datetime.now().isoformat(),
        "actions": executed,
        "diagnostic_paths": diagnostic_paths,
    }
    exec_path = os.path.join(NOTES_DIR, "improvement-execution-log.jsonl")
    with open(exec_path, "a") as f:
        f.write(json.dumps(exec_log, ensure_ascii=False) + "\n")

    print(f"\n  {len(executed)} actions logged to {exec_path}")
    print(f"  Auto-execution complete. Review suggestions above.")
    return _action_state_summary(items, executed, diagnostic_paths)


# ─── Evolutionary Baseline (PUA Pro integration) ───

def ensure_evolution_baseline():
    """确保 evolution.md 存在（pro skill 需要）"""
    evolution_dir = os.path.dirname(EVOLUTION_PATH)
    os.makedirs(evolution_dir, exist_ok=True)

    if not os.path.exists(EVOLUTION_PATH):
        baseline = f"""# PUA Self-Evolution Baseline
Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

## Internalized Patterns (默认义务)
- [ ] 每次 session 结束自动运行 session-end-recorder
- [ ] 用户纠正 > 3 次时提出 memory/skill 建议
- [ ] 工具失败 > 5 次时检查配置

## Evolutionary Baseline (V函数初始值)
- V_initial: 1.0
- V_current: 1.0
- Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

## KPI History
| Date | V | Corrections | Tool Failures | Score |
|------|---|------------|---------------|-------|
"""
        with open(EVOLUTION_PATH, "w") as f:
            f.write(baseline)
        print(f"  ✦ Created evolution baseline: {EVOLUTION_PATH}")
        return True
    return False


# ─── Main ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Self-Improvement Pipeline")
    parser.add_argument("--write", action="store_true", help="写入 action plan JSON")
    parser.add_argument("--auto-exec", action="store_true", help="自主执行模式")
    parser.add_argument("--preview", action="store_true", help="只读模式预览")
    parser.add_argument("--init-baseline", action="store_true", help="初始化进化基线")

    args = parser.parse_args()

    # 初始化基线（如果不存在）
    created = ensure_evolution_baseline()

    # 加载信号
    signals = load_signals()
    health_records = load_health_records()
    patterns = load_patterns()
    darwin_records = load_darwin_results()

    # 聚合
    items = aggregate_items(signals, health_records, patterns, darwin_records)
    items = deduplicate_items(items)

    if args.preview or args.write or args.auto_exec or not any([args.write, args.auto_exec]):
        # 默认或 --preview: 打印报告
        print_pipeline(items, len(signals), len(health_records))

        if args.write or args.auto_exec:
            save_action_plan(items)
            print_action_plan(items[:5])  # Top 5

        if args.auto_exec:
            execution_summary = auto_execute(items)

    if not args.preview:
        event = append_evolution_closure(items, mode="auto_exec" if args.auto_exec else "write" if args.write else "run", execution_summary=locals().get("execution_summary"))
        print(f"\n  Evolution closure appended to {EVOLVE_LOG_PATH}: {event['eval_result']} ({event['steps_count']} item(s))")

    if created:
        print(f"\n  Next step: edit ~/.pua/evolution.md to add your first KPI entry")
        print(f"  Or run: python3 ~/.hermes/scripts/post-session-autopsy.py --recent 5 --write")


if __name__ == "__main__":
    main()
