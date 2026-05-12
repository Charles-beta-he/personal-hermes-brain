#!/usr/bin/env python3
"""
Post-Session Autopsy — 自进化传感器层
从 session JSON 对话中挖掘改进信号

用法:
  # 分析特定 session 文件
  python3 ~/.hermes/scripts/post-session-autopsy.py --file <path>

  # 分析最近 N 个 session（默认最近 5 个）
  python3 ~/.hermes/scripts/post-session-autopsy.py --recent 5

  # 分析今天的所有 session
  python3 ~/.hermes/scripts/post-session-autopsy.py --today

  # 全量扫描并写入 improvement-signals.jsonl
  python3 ~/.hermes/scripts/post-session-autopsy.py --recent 10 --write

输出: 改进信号列表 + 可选的信号文件写入
"""

import os, sys, json, re, datetime
from collections import Counter, defaultdict

SESSIONS_DIR = os.path.expanduser("~/.hermes/sessions")
SIGNALS_PATH = os.path.expanduser("~/.hermes/notes/improvement-signals.jsonl")
NOTES_DIR = os.path.expanduser("~/.hermes/notes")
os.makedirs(NOTES_DIR, exist_ok=True)

# ─── Correction Patterns ───

USER_CORRECTION_SIGNS = [
    # 英文否定
    r"\bno[,\.!]?\s", r"\bstop\b", r"\bwrong\b", r"\bthat['\u2019s]?\s+(not|isn|is not)",
    r"\byou\s+(misunderstood|missed|forgot|ignored)\b",
    r"\bi\s+(didn['\u2019t]t\s+say|said|meant)\b",
    r"\byou\s+(didn['\u2019t]t?|don['\u2019t]t?|did not)\s+(understand|listen|read)\b",
    r"\bnot\s+(what\s+i|right|correct)\b",
    r"\binstead\b", r"\bactually[,\.!]?\s",
    r"\btry\s+again\b", r"\bretry\b",
    r"\bthat['\u2019s]?\s+wrong\b",
    r"\bdid you\s+(even\s+)?(read|check|look)\b",
    # 中文否定/纠偏
    r"\b不对\b", r"\b错了\b", r"\b不是\b", r"\b不要\b",
    r"\b我说了\b", r"\b我说过\b",
    r"\b你(没|没有)\s*(听懂|理解|明白|看|检查)\b",
    r"\b重来\b", r"\b等一下\b",
    r"\b重新\b", r"\b换一种\b",
    r"\b我说的是\b", r"揪出来", r"是否会触发", r"自我修正",
]

ITERATION_BUDGET_SIGNS = [
    r"Iteration budget reached",
    r"maximum number of tool-calling iterations allowed",
    r"max(?:imum)?\s+(?:turns|iterations)\b",
    r"tool[- ]?call(?:ing)?\s+(?:limit|budget)",
    r"工具(?:调用)?上限",
    r"工具调用次数",
    r"上下文压缩.*工具",
]

# 不再用正则匹配原始字符串（JSON 包含 "error": null 等 key 名文本）
# 改用解析 JSON 后按字段判断
TOOL_FAILURE_EXIT_CODE_RANGE = range(1, 200)  # 非零即失败


def _is_tool_failure(content_str):
    """正确解析工具返回，判断是否真的失败"""
    # 尝试解析 JSON
    try:
        # 先尝试完整 JSON
        data = json.loads(content_str)
        if isinstance(data, dict):
            exit_code = data.get("exit_code")
            error = data.get("error")
            if exit_code is not None and exit_code != 0:
                return True
            if error and str(error).lower() not in ("null", "none", ""):
                return True
            return False
    except (json.JSONDecodeError, ValueError):
        pass

    # 尝试找到 JSON 块 (部分工具返回带 JSON 的文本)
    import re as _re
    json_match = _re.search(r'\{[^{}]*"exit_code"[^{}]*\}', content_str)
    if json_match:
        try:
            data = json.loads(json_match.group())
            exit_code = data.get("exit_code")
            error = data.get("error")
            if exit_code is not None and exit_code != 0:
                return True
            if error and str(error).lower() not in ("null", "none", ""):
                return True
        except (json.JSONDecodeError, ValueError):
            pass

    # 非 JSON 格式的文本，用更精确的 pattern 检测真正的失败
    fail_signals = [
        r"(?:^|\n)(?:error|exception|traceback)[\s:]",
        r"command not found",
        r"permission denied",
        r"(?:connection|network).*(?:refused|reset|timeout)",
        r"(?:module|import).*(?:not found|error)",
        r"make: \*\*\*.*Error",
        r"npm ERR!",
        r"fatal: (?!no upstream|ambiguous)",
        r"BUILD FAILED",
        r"Test FAILED",
        r"exit code \d+",
    ]
    for p in fail_signals:
        if _re.search(p, content_str, _re.IGNORECASE):
            return True
    return False


def _tool_failure_payload(content_str):
    """Best-effort parse of a tool result into structured failure metadata."""
    payload = {"exit_code": None, "error": "", "output": content_str, "stderr_tail": content_str[:500]}
    try:
        data = json.loads(content_str)
        if isinstance(data, dict):
            payload["exit_code"] = data.get("exit_code")
            payload["error"] = str(data.get("error") or "")
            payload["output"] = str(data.get("output") or data.get("stdout") or "")
            payload["stderr_tail"] = str(data.get("stderr") or data.get("error") or data.get("output") or "")[-500:]
            return payload
    except (json.JSONDecodeError, ValueError):
        pass
    return payload


def _error_signature(payload):
    text = f"{payload.get('error','')}\n{payload.get('stderr_tail','')}\n{payload.get('output','')}".lower()
    exit_code = payload.get("exit_code")
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "permission denied" in text:
        return "permission_denied"
    if "command not found" in text:
        return "command_not_found"
    if "module" in text and ("not found" in text or "no module named" in text):
        return "module_not_found"
    if "file not found" in text or "no such file" in text or "not found" in text:
        return "not_found"
    if "traceback" in text:
        return "python_traceback"
    if exit_code not in (None, 0, "0"):
        return f"exit_code_{exit_code}"
    return "error"


def aggregate_failure_groups(failures, session_ts=""):
    """Aggregate failures by tool_name + error_signature + exit_code."""
    groups = {}
    for f in failures:
        key = (f.get("tool_name") or f.get("tool") or "unknown", f.get("error_signature") or "unknown", f.get("exit_code"))
        g = groups.setdefault(key, {
            "tool_name": key[0],
            "error_signature": key[1],
            "exit_code": key[2],
            "count": 0,
            "first_seen": session_ts or None,
            "last_seen": session_ts or None,
            "stale_status": "unknown",
            "stderr_tail": f.get("stderr_tail") or f.get("snippet", "")[:500],
        })
        g["count"] += 1
        if f.get("stderr_tail"):
            g["stderr_tail"] = f.get("stderr_tail")[-500:]
    return sorted(groups.values(), key=lambda g: g.get("count", 0), reverse=True)


def load_recent_sessions(n=5):
    """加载最近的 n 个 session JSON 文件"""
    if not os.path.isdir(SESSIONS_DIR):
        return []
    files = []
    for fname in os.listdir(SESSIONS_DIR):
        if fname.startswith("session_") and fname.endswith(".json"):
            path = os.path.join(SESSIONS_DIR, fname)
            try:
                mtime = os.path.getmtime(path)
                files.append((mtime, path, fname))
            except OSError:
                continue
    files.sort(reverse=True)
    return files[:n]


def load_today_sessions():
    """加载今天的 session"""
    today = datetime.date.today().isoformat()
    files = []
    for fname in os.listdir(SESSIONS_DIR):
        if fname.startswith("session_") and fname.endswith(".json"):
            parts = fname.replace("session_", "").split("_")
            if parts and parts[0] == today.replace("-", ""):
                path = os.path.join(SESSIONS_DIR, fname)
                try:
                    mtime = os.path.getmtime(path)
                    files.append((mtime, path, fname))
                except OSError:
                    continue
    files.sort(reverse=True)
    return files


def load_session(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return None


def extract_text(m):
    """从消息中提取文本内容"""
    content = m.get("content", "")
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    texts.append(part.get("text", ""))
                elif part.get("type") == "tool_result":
                    texts.append(str(part.get("content", "")))
        return "\n".join(texts)
    return str(content) if content else ""


def detect_corrections(messages):
    """检测用户纠正模式"""
    corrections = []
    for i, m in enumerate(messages):
        if m.get("role") != "user":
            continue
        text = extract_text(m)
        if not text:
            continue
        for pattern in USER_CORRECTION_SIGNS:
            if re.search(pattern, text, re.IGNORECASE):
                # 找到前一条 assistant 消息获取上下文
                context = ""
                for j in range(i - 1, max(i - 3, -1), -1):
                    if messages[j].get("role") == "assistant":
                        ctx = extract_text(messages[j])
                        context = ctx[:200] if ctx else ""
                        break
                corrections.append({
                    "idx": i,
                    "text": text[:150],
                    "pattern": pattern,
                    "context": context[:200],
                })
                break  # 一个消息只标一次
    return corrections


def detect_iteration_budget_events(messages):
    """Detect agent/tool-call iteration budget saturation mentioned in the session."""
    events = []
    for i, m in enumerate(messages):
        role = m.get("role", "")
        text = extract_text(m)
        if not text:
            continue
        for pattern in ITERATION_BUDGET_SIGNS:
            if re.search(pattern, text, re.IGNORECASE):
                context = ""
                for j in range(i - 1, max(i - 4, -1), -1):
                    ctx = extract_text(messages[j])
                    if ctx:
                        context = ctx[:200]
                        break
                events.append({
                    "idx": i,
                    "role": role,
                    "pattern": pattern,
                    "text": text[:200],
                    "context": context,
                    "classification": "control_system_saturation",
                    "recommended_loop": "bounded_tick_handoff_then_resume",
                })
                break
    return events


def detect_tool_failures(messages):
    """检测工具调用失败（正确解析 JSON exit_code 和 error 字段）"""
    failures = []
    for i, m in enumerate(messages):
        if m.get("role") != "tool":
            continue
        text = extract_text(m)
        if not text:
            continue

        if not _is_tool_failure(text):
            continue

        # 找到对应的 tool_call 消息
        tool_name = ""
        for j in range(i, max(i - 5, -1), -1):
            if messages[j].get("role") == "assistant":
                tc = messages[j].get("tool_calls")
                if tc:
                    if isinstance(tc, list) and tc:
                        tool_name = tc[0].get("function", {}).get("name", "") if isinstance(tc[0], dict) else ""
                    elif isinstance(tc, dict):
                        tool_name = tc.get("function", {}).get("name", "")
                break
        payload = _tool_failure_payload(text)
        signature = _error_signature(payload)
        failures.append({
            "idx": i,
            "tool": tool_name,
            "tool_name": tool_name,
            "exit_code": payload.get("exit_code"),
            "error_signature": signature,
            "stderr_tail": payload.get("stderr_tail", "")[-500:],
            "snippet": text[:200],
        })
    return failures


def detect_repetitive_patterns(messages):
    """检测重复模式：相同工具连续失败、同一类纠正"""
    tool_sequence = []
    for m in messages:
        if m.get("role") == "assistant":
            tc = m.get("tool_calls")
            if tc:
                if isinstance(tc, list) and tc:
                    for t in tc[:1]:
                        name = (t.get("function", {}).get("name", "") if isinstance(t, dict) else "")
                        tool_sequence.append(name)
                elif isinstance(tc, dict):
                    tool_sequence.append(tc.get("function", {}).get("name", ""))

    # 检测同一工具连续使用 > 3 次
    repetitive = []
    from itertools import groupby
    for tool, group in groupby(tool_sequence):
        count = sum(1 for _ in group)
        if count >= 4:
            repetitive.append({"type": "repetitive_tool", "tool": tool, "count": count})

    return repetitive


def estimate_task_type(messages):
    """估算任务类型"""
    user_texts = []
    for m in messages:
        if m.get("role") == "user":
            text = extract_text(m)
            if text:
                user_texts.append(text.strip())
    combined = " ".join(user_texts[:3]).lower()

    categories = {
        "code/development": ["implement", "代码", "feature", "bug", "修复", "dev", "build", "test", "deploy",
                             "refactor", "优化", "重构", "api", "function", "component"],
        "research/analysis": ["research", "分析", "analyze", "compare", "对比", "review", "audit", "审计",
                              "investigate", "调查", "study", "研究"],
        "writing/documentation": ["write", "文档", "doc", "readme", "report", "report", "总结"],
        "configuration/setup": ["configure", "配置", "setup", "install", "部署", "deploy", "setup"],
        "question/qa": ["what is", "how to", "what's", "why", "which", "区别", "是什么", "怎么"],
        "planning/design": ["plan", "规划", "design", "设计", "architecture", "架构"],
    }

    scores = {}
    for cat, keywords in categories.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score:
            scores[cat] = score

    if scores:
        best = max(scores, key=scores.get)
        return best, scores
    return "unknown", {}


def analyze_session(path, fname):
    """分析单个 session 文件"""
    session = load_session(path)
    if not session:
        return None

    messages = session.get("messages", [])
    model = session.get("model", "unknown")
    platform = session.get("platform", "unknown")

    task_type, type_scores = estimate_task_type(messages)
    corrections = detect_corrections(messages)
    iteration_budget_events = detect_iteration_budget_events(messages)
    tool_failures = detect_tool_failures(messages)
    failure_groups = aggregate_failure_groups(tool_failures, session.get("session_start", ""))
    repetitive = detect_repetitive_patterns(messages)

    # 汇总信号
    signals = []

    # 1. 用户纠正 → 记忆或 skill 信号
    if len(corrections) >= 3:
        # 多次纠正 → 高优先级
        context_excerpt = corrections[0].get("context", "")[:100]
        signals.append({
            "type": "frequent_corrections",
            "severity": "high" if len(corrections) >= 5 else "medium",
            "count": len(corrections),
            "detail": f"用户纠正 {len(corrections)} 次，可能缺少对应 skill 或记忆",
            "context": corrections[0].get("text", "")[:100],
            "suggestion": "检查是否需要添加 memory 或创建对应 skill"
        })
    elif len(corrections) >= 1:
        signals.append({
            "type": "correction",
            "severity": "low",
            "count": len(corrections),
            "detail": f"用户纠正 {len(corrections)} 次",
            "context": corrections[0].get("text", "")[:100],
            "suggestion": "关注纠正模式是否重复出现"
        })

    # 2. Iteration/tool-call budget saturation → bounded handoff loop, not generic failure
    if iteration_budget_events:
        signals.append({
            "type": "iteration_budget_saturation",
            "severity": "high",
            "count": len(iteration_budget_events),
            "detail": f"检测到 {len(iteration_budget_events)} 次工具/迭代预算饱和信号；应触发 bounded tick + durable handoff + resume proof loop",
            "context": iteration_budget_events[0].get("text", "")[:100],
            "classification": "control_system_saturation",
            "suggestion": "运行 iteration_budget_doctor.py 与 brain_task_budget_tick.py；不要仅提高 max_turns 或把 partial response 当完成",
        })

    # 3. 工具失败 → 配置/脚本问题
    if len(tool_failures) >= 3:
        # 统计失败的工具/错误签名
        worst_group = failure_groups[0] if failure_groups else {"tool_name": "unknown", "error_signature": "unknown", "count": len(tool_failures)}
        signals.append({
            "type": "tool_failures",
            "severity": "high",
            "count": len(tool_failures),
            "detail": f"工具失败 {len(tool_failures)} 次，最多: {worst_group.get('tool_name')}/{worst_group.get('error_signature')} ({worst_group.get('count')} 次)",
            "context": tool_failures[0].get("snippet", "")[:100],
            "failure_groups": failure_groups,
            "suggestion": f"生成只读诊断后再判断是否需要修复 {worst_group.get('tool_name')} 的配置或用法"
        })
    elif tool_failures:
        signals.append({
            "type": "tool_failures",
            "severity": "medium",
            "count": len(tool_failures),
            "detail": f"工具失败 {len(tool_failures)} 次",
            "context": tool_failures[0].get("snippet", "")[:100],
            "failure_groups": failure_groups,
            "suggestion": "关注失败工具是否需要配置修复"
        })

    # 4. 重复工具调用 → 可能需要优化 skill
    for r in repetitive:
        signals.append({
            "type": "repetitive_tool",
            "severity": "low",
            "count": r["count"],
            "detail": f"工具 {r['tool']} 连续使用 {r['count']} 次，可能效率低下",
            "suggestion": f"检查 {r['tool']} 的 workflow 是否可以优化"
        })

    # 5. 任务类型 → 如果任务类型经常出现但没有对应 skill
    if task_type == "unknown":
        signals.append({
            "type": "unknown_task_type",
            "severity": "info",
            "detail": "无法识别任务类型，可能缺少领域分类",
            "suggestion": "考虑补充该领域的 skill"
        })

    # 计算健康分 (0-100)
    correction_penalty = min(len(corrections) * 5, 30)
    budget_penalty = min(len(iteration_budget_events) * 12, 36)
    failure_penalty = min(len(tool_failures) * 8, 40)
    health_score = max(0, 100 - correction_penalty - budget_penalty - failure_penalty)

    result = {
        "session_id": session.get("session_id", fname),
        "file": fname,
        "timestamp": session.get("session_start", ""),
        "model": model,
        "platform": platform,
        "message_count": len(messages),
        "task_type": task_type,
        "type_scores": type_scores,
        "corrections_count": len(corrections),
        "iteration_budget_count": len(iteration_budget_events),
        "tool_failures_count": len(tool_failures),
        "health_score": health_score,
        "signals": signals,
        # 详情
        "correction_details": corrections[:3],  # 最多 3 条详情
        "iteration_budget_details": iteration_budget_events[:3],
        "failure_details": tool_failures[:3],
    }
    return result


def write_signals(result):
    """将分析结果写入 improvement-signals.jsonl"""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": result["session_id"],
        "session_time": result["timestamp"],
        "task_type": result["task_type"],
        "health_score": result["health_score"],
        "corrections": result["corrections_count"],
        "iteration_budget_events": result.get("iteration_budget_count", 0),
        "failures": result["tool_failures_count"],
        "signals": result["signals"],
        "model": result["model"],
        "platform": result["platform"],
    }
    with open(SIGNALS_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"  ✓ Written to {SIGNALS_PATH}")


def print_report(results):
    """打印分析报告"""
    print(f"\n{'=' * 60}")
    print(f"  Post-Session Autopsy Report")
    print(f"{'=' * 60}")

    total_corrections = 0
    total_budget_events = 0
    total_failures = 0
    all_signals = []

    for r in results:
        total_corrections += r["corrections_count"]
        total_budget_events += r.get("iteration_budget_count", 0)
        total_failures += r["tool_failures_count"]
        all_signals.extend(r["signals"])

        print(f"\n  Session:  {r['session_id'][:25]}...")
        print(f"  Model:    {r['model']}")
        print(f"  Messages: {r['message_count']}")
        print(f"  Task:     {r['task_type']}")
        print(f"  Health:   {r['health_score']}/100")
        print(f"  Correct:  {r['corrections_count']} | Budget: {r.get('iteration_budget_count', 0)} | Failures: {r['tool_failures_count']}")

        if r["signals"]:
            for s in r["signals"]:
                sev = {"high": "!!", "medium": "! ", "low": "- ", "info": "  "}.get(s["severity"], "  ")
                print(f"  {sev} [{s['type']}] {s['detail'][:100]}")

    print(f"\n{'─' * 60}")
    print(f"  总计: {len(results)} sessions")
    print(f"  纠正: {total_corrections} | 预算饱和: {total_budget_events} | 工具失败: {total_failures} | 信号: {len(all_signals)}")

    # 提取高优先级信号
    high = [s for s in all_signals if s["severity"] == "high"]
    if high:
        print(f"\n  !! 高优先级改进信号:")
        for s in high:
            print(f"    {s['type']}: {s['detail'][:80]}")
            if s.get("suggestion"):
                print(f"    建议: {s['suggestion']}")
    else:
        print(f"\n  ✓ 无高优先级信号")

    print(f"{'=' * 60}\n")

    return all_signals


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Post-Session Autopsy — 自进化传感器")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", help="分析特定 session JSON 文件")
    group.add_argument("--recent", type=int, default=0, help="分析最近 N 个 session")
    group.add_argument("--today", action="store_true", help="分析今天的 session")
    parser.add_argument("--write", action="store_true", help="写入 improvement-signals.jsonl")

    args = parser.parse_args()

    files = []
    if args.file:
        path = os.path.expanduser(args.file)
        if os.path.exists(path):
            files = [(0, path, os.path.basename(path))]
        else:
            print(f"File not found: {path}")
            sys.exit(1)
    elif args.today:
        files = load_today_sessions()
    elif args.recent > 0:
        files = load_recent_sessions(args.recent)
    else:
        # 默认：最近 5 个
        files = load_recent_sessions(5)

    if not files:
        print("No session files found")
        return

    print(f"Analyzing {len(files)} session file(s)...")
    results = []
    for mtime, path, fname in files:
        r = analyze_session(path, fname)
        if r:
            results.append(r)
            print(f"  {fname}: health={r['health_score']}, corr={r['corrections_count']}, budget={r.get('iteration_budget_count', 0)}, fail={r['tool_failures_count']}")

    if not results:
        print("No valid sessions found")
        return

    all_signals = print_report(results)

    if args.write and results:
        for r in results:
            write_signals(r)
        print(f"\n{len(results)} records written to improvement-signals.jsonl")


if __name__ == "__main__":
    main()
