#!/usr/bin/env python3
"""
skill-steward.py — 技能生态管家

基于 11 理论的实战审计脚本。
覆盖 Ashby + Ostrom + Prigogine + Parnas + Conway + Havel + 三角约束 + Dreyfus + 2nd-Order + Nudge + Memetics.

用法:
  python3 skill-steward.py                    # 完整审计
  python3 skill-steward.py --report           # 只输出报告（不修改）
  python3 skill-steward.py --cleanup          # 执行梯度制裁（DEPRECATE → ARCHIVE）
  python3 skill-steward.py --dashboard        # 更新 Obsidian 仪表盘
"""

import os
import sys
import json
import time
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# === Configuration ===
SKILLS_DIR = Path(os.path.expanduser(os.environ.get("HERMES_SKILLS_DIR", "~/.hermes/skills")))
BRAIN_DIR = Path(os.path.expanduser("~/Documents/brain"))
REPORT_DIR = SKILLS_DIR / "steward"
REPORT_FILE = REPORT_DIR / "audit-report.json"
DASHBOARD_FILE = BRAIN_DIR / "07-仪表盘" / "技能生态健康度.md"
MAX_GRAPH_DEPTH = int(os.environ.get("HERMES_SKILL_GRAPH_MAX_DEPTH", "4"))
MAX_MOLECULE_DEPS = int(os.environ.get("HERMES_SKILL_GRAPH_MAX_MOLECULE_DEPS", "10"))

# === State tracking database ===
STATE_FILE = REPORT_DIR / "state.json"

# === Helpers ===
def parse_skill_list(value):
    """Parse YAML-ish frontmatter lists without requiring PyYAML."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    if not text or text in ("[]", "null", "None"):
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [p.strip().strip('"').strip("'") for p in text.split(",") if p.strip()]


def get_all_skills():
    """Scan all skills and return list of dicts"""
    skills = []
    for sk_path in SKILLS_DIR.rglob("SKILL.md"):
        relative = sk_path.relative_to(SKILLS_DIR)
        name = str(relative.parent)
        size = sk_path.stat().st_size
        mtime = sk_path.stat().st_mtime
        
        content = sk_path.read_text()
        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        frontmatter[k.strip()] = v.strip().strip('"').strip("'")
        
        is_alias = frontmatter.get("alias", "").lower() == "true"
        
        has_tests = (sk_path.parent / "test-prompts.json").exists()
        has_changelog = (sk_path.parent / "CHANGELOG.md").exists()
        linked_files = (sk_path.parent / "references").exists()
        
        ref_files = list((sk_path.parent / "references").rglob("*")) if linked_files else []
        broken_refs = [f for f in ref_files if not f.exists()]
        
        skills.append({
            "name": name,
            "cname": frontmatter.get("name", name.split("/")[-1]),
            "path": str(sk_path),
            "size": size,
            "mtime": mtime,
            "age_days": (time.time() - mtime) / 86400,
            "has_tests": has_tests,
            "has_changelog": has_changelog,
            "ref_count": len(ref_files),
            "broken_refs": len(broken_refs),
            "description": frontmatter.get("description", "")[:100],
            "is_alias": is_alias,
            "body": parts[2].strip() if content.startswith("---") and len(parts) >= 3 else content,
            "related_skills": frontmatter.get("related_skills", ""),
            "declared_tier": (frontmatter.get("skill_tier") or frontmatter.get("tier") or "").lower(),
        })
    return skills

def load_state():
    """Load persistent state"""
    defaults = {"audit_count": 0, "load_counts": {}, "last_cleanup": None,
                "rule_triggers": {}, "dreyfus_scores": {}, "reward_points": 0}
    if STATE_FILE.exists():
        loaded = json.loads(STATE_FILE.read_text())
        for k, v in defaults.items():
            loaded.setdefault(k, v)
        return loaded
    return dict(defaults)

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

# === Audit Functions ===

def audit_total_count(skills):
    """Ostrom 原则1 + Dunbar: 总技能数监控"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    total = len(real_skills)
    aliases = [s for s in skills if s.get("is_alias")]
    return {
        "metric": "总技能数（不含别名）",
        "value": total,
        "aliases": len(aliases),
        "threshold": 160,
        "status": "OK" if total <= 160 else "OVER_LIMIT",
        "delta": total - 160,
    }

def audit_test_coverage(skills):
    """Ostrom 原则4: 监控覆盖"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    with_tests = sum(1 for s in real_skills if s["has_tests"])
    total = len(real_skills)
    pct = with_tests / total * 100 if total else 0
    return {
        "metric": "测试覆盖率",
        "value": f"{pct:.1f}%",
        "details": f"{with_tests}/{total}",
        "threshold": ">=80%",
        "status": "PASS" if pct >= 80 else "FAIL",
    }

def audit_stale_skills(skills):
    """Prigogine: 熵债检测 — 找出僵尸"""
    stale = [s for s in skills if s["age_days"] > 90 and not s["has_tests"] and not s.get("is_alias")]
    return {
        "metric": "僵尸技能 (90天+无测试)",
        "value": len(stale),
        "details": [s["name"] for s in stale[:20]],
        "status": "OK" if len(stale) == 0 else f"{len(stale)} STALE",
    }

def audit_name_conflicts(skills):
    """Parnas: 同名冲突检测（仅真实技能）"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    name_map = defaultdict(list)
    for s in real_skills:
        name_map[s["cname"]].append(s["name"])
    conflicts = {n: paths for n, paths in name_map.items() if len(paths) > 1}
    return {
        "metric": "同名冲突",
        "value": len(conflicts),
        "details": conflicts,
        "status": "OK" if len(conflicts) == 0 else f"{len(conflicts)} CONFLICTS",
    }

def audit_broken_references(skills):
    """Parnas: 断裂引用检测"""
    total_broken = sum(s["broken_refs"] for s in skills)
    skills_with_broken = [s for s in skills if s["broken_refs"] > 0]
    return {
        "metric": "断裂引用",
        "value": total_broken,
        "details": [(s["name"], s["broken_refs"]) for s in skills_with_broken[:10]],
        "status": "OK" if total_broken == 0 else f"{total_broken} BROKEN",
    }

def audit_skeleton_skills(skills):
    """Ostrom 原则5: 骨架技能检测"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    skeletons = [s for s in real_skills if s["size"] < 100 and not s["has_tests"]]
    return {
        "metric": "骨架技能 (< 100 bytes, 无测试)",
        "value": len(skeletons),
        "details": [s["name"] for s in skeletons[:20]],
        "status": "OK" if len(skeletons) == 0 else f"{len(skeletons)} SKELETONS",
    }

def audit_ashby_diversity(skills):
    """Ashby: 控制器多样性 vs 系统多样性"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    total = len(real_skills)
    categories = defaultdict(list)
    for s in real_skills:
        cat = s["name"].split("/")[0] if "/" in s["name"] else "root"
        categories[cat].append(s["name"])
    return {
        "metric": "系统多样性 (R_system)",
        "value": total,
        "analysis": f"R_system={total}, 目标 R_controller>={min(total, 50)}",
        "categories": {k: len(v) for k, v in sorted(categories.items(), key=lambda x: -len(x[1]))},
        "status": "OVERFLOW" if total > 160 else "MANAGEABLE",
    }

def audit_dreyfus_grade(skills, state):
    """Dreyfus 5级技能成熟度评估"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    grades = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total = len(real_skills)
    
    for s in real_skills:
        has_tests = s["has_tests"]
        has_changelog = s["has_changelog"]
        has_refs = s["ref_count"] >= 2
        has_long_desc = len(s["description"]) > 50
        
        if has_tests and has_changelog and has_refs and has_long_desc:
            grade = 4
        elif has_tests and has_changelog:
            grade = 3
        elif has_tests:
            grade = 2
        else:
            grade = 1
        
        if grade == 4 and state["load_counts"].get(s["name"], 0) > 10:
            grade = 5
        
        grades[grade] = grades.get(grade, 0) + 1
        state["dreyfus_scores"][s["name"]] = grade
    
    return {
        "metric": "Dreyfus 技能成熟度分布",
        "value": {f"L{i}": grades[i] for i in range(1, 6)},
        "avg": sum(k * v for k, v in grades.items()) / max(total, 1),
        "status": "OK" if grades[1] / max(total, 1) < 0.3 else "HIGH_NOVICE_RATIO",
    }

def audit_second_order_self(state):
    """二阶控制论：Steward 自我审计"""
    triggers = state.get("rule_triggers", {})
    rules = {
        "stale_deprecation": triggers.get("stale_deprecation", 0),
        "skeleton_detection": triggers.get("skeleton_detection", 0),
        "conflict_detection": triggers.get("conflict_detection", 0),
        "broken_refs": triggers.get("broken_refs", 0),
    }
    dormant_rules = [r for r, c in rules.items() if c == 0]
    active_rules = [r for r, c in rules.items() if c > 0]
    return {
        "metric": "二阶自审计 — 规则活性",
        "value": f"{len(active_rules)}/{len(rules)} 活跃",
        "dormant_rules": dormant_rules,
        "active_rules": active_rules,
        "status": "OK" if len(dormant_rules) <= 1 else "HIGH_DORMANCY",
    }

def audit_nudge_incentives(state):
    """Nudge: 激励机制追踪"""
    points = state.get("reward_points", 0)
    load_counts = state.get("load_counts", {})
    top_loaded = sorted(load_counts.items(), key=lambda x: -x[1])[:5]
    return {
        "metric": "激励积分 & 使用热点",
        "value": f"{points} 分",
        "reward_points": points,
        "top_loaded": top_loaded,
        "status": "OK" if points > 0 else "NO_INCENTIVE_DATA",
    }

def audit_meme_flow(skills):
    """Memetics: 同类技能检测"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    categories = defaultdict(list)
    for s in real_skills:
        cat = s["name"].split("/")[0] if "/" in s["name"] else s["cname"]
        categories[cat].append(s["name"])
    multi_member = {k: v for k, v in categories.items() if len(v) > 1}
    return {
        "metric": "模因池 — 同类技能聚类",
        "value": f"{len(multi_member)} 个多成员类别",
        "clusters": {k: len(v) for k, v in sorted(multi_member.items(), key=lambda x: -len(x[1]))[:10]},
        "status": "OK" if len(multi_member) <= 5 else "HIGH_CLUSTERING",
    }


def audit_content_overlap(skills):
    """Parnas: 检测内容重叠的 skill 对（基于 body 实义词的 Jaccard 相似度 > 0.3）

    跳过以下类型的 skill:
      - 别名 (is_alias)
      - 正文 < 50 词的骨架 skill
      - 仅含 frontmatter 无正文的
    """
    real_skills = [s for s in skills if not s.get("is_alias") and s.get("body") and len(s["body"].split()) >= 200]
    overlaps = []
    STOPWORDS = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
                 "of", "with", "by", "is", "are", "be", "this", "that", "it",
                 "as", "but", "not", "all", "each", "any", "no", "from", "you",
                 "your", "we", "our", "will", "can", "do", "has", "have", "had",
                 "been", "were", "was", "does", "doing", "done", "get", "got",
                 "set", "use", "used", "using", "need", "like", "just", "also",
                 "then", "than", "so", "if", "up", "out", "about", "into",
                 "over", "after", "before", "between", "under", "again",
                 "further", "once", "here", "there", "when", "where", "why",
                 "how", "which", "who", "whom", "what",
                 "skill", "skills", "tool", "tools", "step", "steps",
                 "workflow", "system", "agent", "config", "configuration",
                 "这些", "一个", "可以", "用于", "工具", "任务", "步骤",
                 "检查", "配置", "输出", "数据", "文件", "路径", "功能",
                 "需要", "使用", "通过", "进行", "是否", "如果", "或者",
                 "因为", "所以", "但是", "没有", "这个", "那个"}
    for i in range(len(real_skills)):
        a_tokens = set(w for w in real_skills[i]["body"].lower().split()
                       if w not in STOPWORDS and len(w) > 2)
        if not a_tokens:
            continue
        for j in range(i + 1, len(real_skills)):
            b_tokens = set(w for w in real_skills[j]["body"].lower().split()
                           if w not in STOPWORDS and len(w) > 2)
            if not b_tokens:
                continue
            sim = len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
            if sim >= 0.3:
                overlaps.append({
                    "a": real_skills[i]["name"],
                    "b": real_skills[j]["name"],
                    "similarity": round(sim, 2),
                })
    return {
        "metric": "内容重叠 → 建议合并",
        "value": f"{len(overlaps)} 对高度相似",
        "details": [f"{o['a']} ↔ {o['b']} ({o['similarity']})" for o in overlaps[:10]],
        "status": "OK" if len(overlaps) == 0 else f"{len(overlaps)} OVERLAPS",
    }


def audit_skill_dependencies(skills):
    """依赖检测: 检查 related_skills 声明 + 正文中的交叉引用"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    with_deps = 0
    cross_refs = 0
    skill_names = {s["name"] for s in real_skills}
    for s in real_skills:
        related = s.get("related_skills", "")
        if related:
            with_deps += 1
        # Check body for references to other skill names
        if s.get("body"):
            for other in skill_names:
                if other != s["name"] and other.split("/")[-1] in s["body"]:
                    cross_refs += 1
    return {
        "metric": "技能依赖声明",
        "value": f"{with_deps}/{len(real_skills)} 声明了 related_skills",
        "details": [f"另有 {cross_refs} 个技能正文隐含交叉引用（可能应声明依赖）"],
        "status": "OK" if with_deps >= len(real_skills) * 0.3 else "LOW_DEPENDENCY",
        "suggestions": _suggest_dependencies(real_skills) if with_deps < len(real_skills) * 0.5 else [],
    }


def _suggest_dependencies(skills):
    """Auto-suggest related_skills for skills that reference other skills in their body."""
    skill_names = {s["name"]: s["name"].split("/")[-1] for s in skills if not s.get("is_alias")}
    name_to_path = {v: k for k, v in skill_names.items()}
    suggestions = []
    for s in skills:
        if s.get("is_alias") or not s.get("body"):
            continue
        if s.get("related_skills", ""):
            continue  # already has deps
        current = s["name"]
        found = []
        for other_path, other_name in skill_names.items():
            if other_path == current:
                continue
            # Check body for the other skill's name or short name
            if other_name in s["body"] and len(other_name) > 3:
                # Avoid common word false positives
                if other_name not in ("pip", "git", "npm", "mcp", "api", "url", "cli", "log", "env", "ssh", "yaml", "json", "toml"):
                    found.append(other_path)
        if found:
            suggestions.append({"skill": current, "suggested_deps": found[:5]})
    return suggestions



def _skill_graph(skills):
    """Build an explicit dependency graph from related_skills frontmatter."""
    real_skills = [s for s in skills if not s.get("is_alias")]
    by_name = {s["name"]: s for s in real_skills}
    by_cname = defaultdict(list)
    by_short = defaultdict(list)
    for s in real_skills:
        by_cname[s.get("cname", "")].append(s["name"])
        by_short[s["name"].split("/")[-1]].append(s["name"])

    graph = {s["name"]: [] for s in real_skills}
    missing = []
    ambiguous = []
    for s in real_skills:
        for dep in parse_skill_list(s.get("related_skills", "")):
            candidates = []
            if dep in by_name:
                candidates = [dep]
            elif dep in by_cname:
                candidates = by_cname[dep]
            elif dep in by_short:
                candidates = by_short[dep]
            if len(candidates) == 1:
                graph[s["name"]].append(candidates[0])
            elif len(candidates) > 1:
                ambiguous.append({"skill": s["name"], "dependency": dep, "candidates": sorted(candidates)[:10]})
            else:
                missing.append({"skill": s["name"], "dependency": dep})
    return real_skills, by_name, graph, missing, ambiguous


def _find_cycles(graph):
    cycles = []
    visiting = set()
    visited = set()
    stack = []

    def dfs(node):
        if node in visiting:
            try:
                idx = stack.index(node)
                cycle = stack[idx:] + [node]
            except ValueError:
                cycle = [node, node]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for dep in graph.get(node, []):
            dfs(dep)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        dfs(node)
    return cycles


def _depths_and_chains(graph, cycles):
    cycle_nodes = {n for c in cycles for n in c}
    # `memo` is safe because graph and cycle_nodes are immutable within one audit;
    # cycle nodes are excluded before DAG depth calculation, making depth path-invariant.
    memo = {}
    chains = {}

    def depth(node, seen):
        if node in memo:
            return memo[node], chains[node]
        if node in seen or node in cycle_nodes:
            return 0, [node]
        deps = graph.get(node, [])
        if not deps:
            memo[node] = 0
            chains[node] = [node]
            return 0, [node]
        best_depth = -1
        best_chain = [node]
        for dep in deps:
            d, c = depth(dep, seen | {node})
            if d + 1 > best_depth:
                best_depth = d + 1
                best_chain = [node] + c
        memo[node] = best_depth
        chains[node] = best_chain
        return best_depth, best_chain

    for node in sorted(graph):
        depth(node, set())
    return memo, chains


def _infer_tier(dep_count, depth):
    if dep_count == 0:
        return "atom"
    if dep_count <= MAX_MOLECULE_DEPS and depth <= 2:
        return "molecule"
    return "compound"


def audit_skill_graph(skills):
    """Skill Graphs 2.0: atoms / molecules / compounds topology verifier."""
    real_skills, by_name, graph, missing, ambiguous = _skill_graph(skills)
    cycles = _find_cycles(graph)
    depths, chains = _depths_and_chains(graph, cycles)
    tier_counts = defaultdict(int)
    explicit_tier_count = 0
    violations = []
    migrations = []

    for s in real_skills:
        name = s["name"]
        deps = graph.get(name, [])
        dep_count = len(deps)
        depth = depths.get(name, 0)
        declared = s.get("declared_tier") if s.get("declared_tier") in {"atom", "molecule", "compound"} else ""
        inferred = _infer_tier(dep_count, depth)
        tier = declared or inferred
        tier_counts[tier] += 1
        if declared:
            explicit_tier_count += 1
        else:
            migrations.append({"skill": name, "suggested_tier": inferred, "reason": f"deps={dep_count}, depth={depth}"})
        if declared == "atom" and dep_count:
            violations.append({"type": "illegal_atom_dependency", "skill": name, "deps": deps, "action": "Split orchestration into a molecule; atoms must have zero skill dependencies."})
        if declared == "molecule":
            if dep_count < 1 or dep_count > MAX_MOLECULE_DEPS:
                violations.append({"type": "illegal_molecule_fanin", "skill": name, "deps": deps, "action": f"Keep molecules at 1-{MAX_MOLECULE_DEPS} explicit dependencies or promote to compound."})
            for dep in deps:
                dep_tier = by_name.get(dep, {}).get("declared_tier", "") or _infer_tier(len(graph.get(dep, [])), depths.get(dep, 0))
                if dep_tier != "atom":
                    violations.append({"type": "illegal_molecule_dependency", "skill": name, "dependency": dep, "dependency_tier": dep_tier, "action": "Molecules should chain atoms; move nested orchestration to a compound."})
        if declared == "compound":
            for dep in deps:
                dep_tier = by_name.get(dep, {}).get("declared_tier", "") or _infer_tier(len(graph.get(dep, [])), depths.get(dep, 0))
                if dep_tier == "compound":
                    violations.append({"type": "compound_to_compound_dependency", "skill": name, "dependency": dep, "action": "Break compound chains by extracting a molecule boundary."})

    excessive_depth = [
        {"skill": name, "depth": d, "chain": chains.get(name, [name]), "action": "Split at a molecule boundary; keep graph depth <= 4."}
        for name, d in sorted(depths.items(), key=lambda x: -x[1]) if d > MAX_GRAPH_DEPTH
    ]
    cycle_reports = [{"cycle": c, "action": "Remove or invert one edge; cycles are never safe for runtime skill composition."} for c in cycles]
    hard_issue_count = len(cycle_reports) + len(excessive_depth) + len(violations)
    edge_count = sum(len(v) for v in graph.values())
    status = "OK" if hard_issue_count == 0 else "GRAPH_VIOLATIONS"
    return {
        "metric": "Skill Graphs 2.0 拓扑审计",
        "value": f"edges={edge_count}, depth_max={max(depths.values()) if depths else 0}, cycles={len(cycles)}, tiers={dict(sorted(tier_counts.items()))}",
        "status": status,
        "max_depth_allowed": MAX_GRAPH_DEPTH,
        "edge_count": edge_count,
        "tier_counts": dict(sorted(tier_counts.items())),
        "explicit_tier_count": explicit_tier_count,
        "cycle_count": len(cycles),
        "cycles": cycle_reports[:20],
        "excessive_depth": excessive_depth[:50],
        "typed_violations": violations[:50],
        "missing_dependencies": missing[:50],
        "ambiguous_dependencies": ambiguous[:50],
        "migration_suggestions": migrations[:50],
        "details": [
            f"显式 tier: {explicit_tier_count}/{len(real_skills)}；未声明按 deps/depth 推断并给出迁移建议",
            f"fail-closed gate: cycles={len(cycles)}, excessive_depth={len(excessive_depth)}, typed_violations={len(violations)}",
        ],
    }


def audit_supply_chain(skills):
    """供应链安全: 检测危险命令模式"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    npx_count = 0
    pip_count = 0
    curl_pipe = 0
    high_risk = []
    for s in real_skills:
        body = s.get("body", "")
        if "npx " in body:
            npx_count += 1
        if "pip install" in body:
            pip_count += 1
        if "curl" in body and ("| bash" in body or "| sh" in body):
            curl_pipe += 1
            high_risk.append(s["name"])
    return {
        "metric": "供应链安全扫描",
        "value": f"npx={npx_count}, pip={pip_count}, curl|sh={curl_pipe}",
        "details": [f"高危: curl|sh 在 {', '.join(high_risk)}"] if high_risk else [],
        "status": "OK" if curl_pipe == 0 else f"{curl_pipe} HIGH_RISK",
    }


def audit_token_impact(skills):
    """Token 审计: 三层加载的预期消耗"""
    real_skills = [s for s in skills if not s.get("is_alias")]
    total_body = sum(len(s.get("body", "")) for s in real_skills)
    avg_body = total_body // len(real_skills) if real_skills else 0
    layer1_tokens = (len(real_skills) * 200) // 4
    layer2_3 = (avg_body * 3) // 4
    full_load = total_body // 4
    savings = 0
    if full_load > 0:
        savings = int((1 - (layer1_tokens + layer2_3) / (layer1_tokens + full_load)) * 100)
    return {
        "metric": "Token 消耗审计（三层加载 vs 全量）",
        "value": f"Layer1={layer1_tokens:,}tok | +3相关={layer1_tokens+layer2_3:,}tok | 全量={full_load:,}tok",
        "details": [f"三层加载节约 ~{savings}% tokens（vs 全量加载 {len(real_skills)} 个 skill）"],
        "status": "OK" if savings >= 80 else f"LOW_SAVINGS({savings}%)",
    }


# === Report Generation ===
def generate_report(skills, state):
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "audits": {
            "total_count": audit_total_count(skills),
            "test_coverage": audit_test_coverage(skills),
            "stale_skills": audit_stale_skills(skills),
            "name_conflicts": audit_name_conflicts(skills),
            "broken_refs": audit_broken_references(skills),
            "skeletons": audit_skeleton_skills(skills),
            "ashby_diversity": audit_ashby_diversity(skills),
            "dreyfus_grade": audit_dreyfus_grade(skills, state),
            "second_order": audit_second_order_self(state),
            "nudge": audit_nudge_incentives(state),
            "meme_flow": audit_meme_flow(skills),
            "content_overlap": audit_content_overlap(skills),
            "skill_dependencies": audit_skill_dependencies(skills),
            "skill_graph": audit_skill_graph(skills),
            "supply_chain": audit_supply_chain(skills),
            "token_impact": audit_token_impact(skills),
        },
        "summary": {"pass_count": 0, "fail_count": 0, "total_skills": len(skills)},
    }
    for audit_name, result in report["audits"].items():
        ok_statuses = ("OK", "PASS", "MANAGEABLE", "NO_INCENTIVE_DATA")
        if result["status"] in ok_statuses:
            report["summary"]["pass_count"] += 1
        else:
            report["summary"]["fail_count"] += 1
    return report

def print_report(report):
    audits = report["audits"]
    summary = report["summary"]
    print(f"\n{'='*60}")
    print(f"  技能生态管家审计报告")
    print(f"  {report['timestamp']}")
    print(f"{'='*60}")
    print(f"\n  总计: {summary['total_skills']} 技能 | {summary['pass_count']} 通过 | {summary['fail_count']} 告警")
    ok_statuses = ("OK", "PASS", "MANAGEABLE", "NO_INCENTIVE_DATA")
    for name, result in audits.items():
        icon = "✅" if result["status"] in ok_statuses else "❌"
        print(f"\n  {icon} {result['metric']}: {result['value']}")
        if "details" in result and result["details"]:
            if isinstance(result["details"], list):
                for d in result["details"][:5]:
                    print(f"     - {d}")
                if len(result["details"]) > 5:
                    print(f"     ... and {len(result['details'])-5} more")
            elif isinstance(result["details"], dict):
                for k, v in list(result["details"].items())[:5]:
                    print(f"     {k}: {v}")
    print(f"\n{'='*60}")

    # Print dependency suggestions if available
    deps = audits.get("skill_dependencies", {})
    suggestions = deps.get("suggestions", [])
    if suggestions:
        print(f"\n  📋 建议添加依赖声明（--annotate 可自动写入）:")
        for s in suggestions[:5]:
            print(f"     {s['skill']} → related_skills: [{', '.join(s['suggested_deps'][:3])}]")
        if len(suggestions) > 5:
            print(f"     ... and {len(suggestions)-5} more")

def update_dashboard(report):
    audits = report["audits"]
    dashboard = f"""# 技能生态健康度仪表盘

> 自动更新于: {report['timestamp']}
> 理论覆盖: 11 个理论

## 核心指标

| 指标 | 当前值 | 阈值 | 状态 |
|------|-------|------|------|
| 总技能数 | {audits['total_count']['value']} | {audits['total_count']['threshold']} | {'⚠️ 超限' if audits['total_count']['status'] != 'OK' else '✅'} |
| 测试覆盖率 | {audits['test_coverage']['value']} | {audits['test_coverage']['threshold']} | {'✅' if audits['test_coverage']['status'] == 'PASS' else '❌'} |
| 僵尸技能 | {audits['stale_skills']['value']} | 0 | {'✅' if audits['stale_skills']['status'] == 'OK' else '❌'} |
| 同名冲突 | {audits['name_conflicts']['value']} | 0 | {'✅' if audits['name_conflicts']['status'] == 'OK' else '❌'} |
| 骨架技能 | {audits['skeletons']['value']} | 0 | {'✅' if audits['skeletons']['status'] == 'OK' else '❌'} |
| 系统多样性 | {audits['ashby_diversity']['value']} | ≤150 | {'✅' if audits['ashby_diversity']['status'] != 'OVERFLOW' else '❌'} |
| 断裂引用 | {audits['broken_refs']['value']} | 0 | {'✅' if audits['broken_refs']['status'] == 'OK' else '❌'} |
| Dreyfus 平均级 | {audits['dreyfus_grade']['avg']:.1f} | ≥2.0 | {'✅' if audits['dreyfus_grade']['avg'] >= 2.0 else '❌'} |
| 规则活性 | {audits['second_order']['value']} | 全部活跃 | {'✅' if audits['second_order']['status'] == 'OK' else '❌'} |
| 激励积分 | {audits['nudge']['reward_points']} | >0 | {'✅' if audits['nudge']['reward_points'] > 0 else '⏳'} |
| 同类聚类 | {audits['meme_flow']['value']} | ≤5 | {'✅' if audits['meme_flow']['status'] == 'OK' else '❌'} |
| Skill Graph | {audits['skill_graph']['value']} | depth≤{audits['skill_graph']['max_depth_allowed']}, cycles=0 | {'✅' if audits['skill_graph']['status'] == 'OK' else '❌'} |

## Skill Graphs 2.0

- Taxonomy: atom = zero skill deps; molecule = bounded explicit composition; compound = high-level orchestrator.
- Explicit tiers: {audits['skill_graph']['explicit_tier_count']} declared.
- Migration suggestions are in `{REPORT_FILE}` under `audits.skill_graph.migration_suggestions`.

## 按类别分布
| 类别 | 技能数 |
|------|--------|
"""
    for cat, count in sorted(audits['ashby_diversity'].get('categories', {}).items(), key=lambda x: -x[1]):
        dashboard += f"| {cat} | {count} |\n"
    dashboard += f"\n## 行动项\n"
    if audits['stale_skills']['value'] > 0:
        dashboard += f"- [ ] 清理 {audits['stale_skills']['value']} 个僵尸技能\n"
    if audits['name_conflicts']['value'] > 0:
        dashboard += f"- [ ] 解决 {audits['name_conflicts']['value']} 组同名冲突\n"
    if audits['skeletons']['value'] > 0:
        dashboard += f"- [ ] 处理 {audits['skeletons']['value']} 个骨架技能\n"
    if audits['broken_refs']['value'] > 0:
        dashboard += f"- [ ] 修复 {audits['broken_refs']['value']} 个断裂引用\n"
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_FILE.write_text(dashboard)

# === Main ===

def main():
    args = sys.argv[1:]
    mode = args[0] if args else "full"
    json_mode = "--json" in args
    warn_only = "--warn-only" in args
    if mode != "--graph-check":
        print(f"  🛡️  技能生态管家 v1.2")
        print(f"  {'='*40}")
    skills = get_all_skills()
    state = load_state()
    report = generate_report(skills, state)

    if mode == "--graph-check":
        graph = report["audits"]["skill_graph"]
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        (REPORT_DIR / "skill-graph-report.json").write_text(json.dumps(graph, indent=2, default=str))
        if json_mode:
            print(json.dumps(graph, ensure_ascii=False, indent=2, default=str))
        else:
            print(f"Skill Graphs 2.0: {graph['status']} — {graph['value']}")
            for c in graph.get("cycles", [])[:5]:
                print(f"  cycle: {' -> '.join(c['cycle'])}")
            for d in graph.get("excessive_depth", [])[:5]:
                print(f"  depth>{graph['max_depth_allowed']}: {d['skill']} depth={d['depth']} chain={' -> '.join(d['chain'])}")
            for v in graph.get("typed_violations", [])[:5]:
                print(f"  violation: {v['type']} {v.get('skill')} {v.get('dependency', '')}")
        if graph["status"] != "OK" and not warn_only:
            sys.exit(2)
        return

    if mode == "--report":
        print_report(report)
        return
    elif mode == "--dashboard":
        update_dashboard(report)
        subprocess.run(
            [sys.executable, os.path.expanduser("~/.hermes/scripts/sync-brain.py"), "--push"],
            check=False,
            timeout=60,
        )
        print(f"  📊 仪表盘已更新")
        return
    elif mode == "--cleanup":
        print_report(report)
        really_stale = [s for s in skills if s["age_days"] > 180 and not s["has_tests"] and not s["has_changelog"] and s["size"] < 500 and not s.get("is_alias")]
        if really_stale:
            print(f"\n  🗑️  建议 ARCHIVE 以下 {len(really_stale)} 个技能:")
            for s in really_stale[:10]:
                print(f"     - {s['name']} ({s['age_days']:.0f} 天, {s['size']} bytes)")
        else:
            print("\n  ✅ 无符合清理条件的僵尸技能")
        update_dashboard(report)
        return
    else:
        print_report(report)
        state["audit_count"] += 1
        state["last_audit"] = report["timestamp"]
        save_state(state)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(json.dumps(report, indent=2, default=str))
        update_dashboard(report)
        print(f"\n  📄 完整报告: {REPORT_FILE}")
        print(f"  🔄 Sync: python3 ~/.hermes/scripts/sync-brain.py")

if __name__ == "__main__":
    main()
