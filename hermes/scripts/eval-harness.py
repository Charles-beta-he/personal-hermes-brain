#!/usr/bin/env python3
"""
eval-harness — L4 准入门
评估 skills/prompts 改动是否退化。

用法:
  # 初始化基线
  python3 ~/.hermes/scripts/eval-harness.py --init-baseline

  # 评估 staging 目录中的 skill 改动
  python3 ~/.hermes/scripts/eval-harness.py --evaluate <skill_name>

  # 比较 staging vs baseline
  python3 ~/.hermes/scripts/eval-harness.py --compare <skill_name>

  # 更新基线 (promote)
  python3 ~/.hermes/scripts/eval-harness.py --promote <skill_name>

  # 查看当前基线
  python3 ~/.hermes/scripts/eval-harness.py --status
"""

import os, sys, json, datetime, subprocess, re, math

EVAL_DIR = os.path.expanduser("~/.hermes/eval")
BASELINE_PATH = os.path.join(EVAL_DIR, "eval-baseline.json")
STAGING_DIR = os.path.expanduser("~/.hermes/skills-staging")
SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
PROMOTE_LOG = os.path.join(EVAL_DIR, "promote-log.jsonl")
os.makedirs(EVAL_DIR, exist_ok=True)

# ─── 基线测试集 (从外部 JSON 文件加载) ───

BASELINE_PROMPTS_PATH = os.path.join(EVAL_DIR, "baseline-prompts.json")

def load_baseline_prompts():
    if os.path.exists(BASELINE_PROMPTS_PATH):
        with open(BASELINE_PROMPTS_PATH) as f:
            return json.load(f)
    # fallback: 内置最小集
    return [
        {"id": "fallback-1", "task_class": "general",
         "prompt": "Explain the concept of dependency injection with a practical example",
         "expected": ["dependency", "injection", "example"]},
        {"id": "fallback-2", "task_class": "general",
         "prompt": "Write a Python decorator that measures function execution time",
         "expected": ["decorator", "time", "function"]},
    ]

BASELINE_PROMPTS = load_baseline_prompts()


def load_or_init_baseline():
    """加载或初始化基线"""
    if os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH) as f:
            return json.load(f)
    # 初始化: 每个测试项暂设为 None (等待首次评估)
    baseline = {
        "version": 1,
        "created": datetime.datetime.now().isoformat(),
        "prompts": BASELINE_PROMPTS,
        "results": {p["id"]: None for p in BASELINE_PROMPTS},
        "summary": None,
    }
    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)
    return baseline


def score_output(output, expected_keywords):
    """简单评分: 检查输出是否包含预期关键词"""
    lower = output.lower()
    found = sum(1 for kw in expected_keywords if kw.lower() in lower)
    total = len(expected_keywords)
    return {
        "pass": found >= total * 0.5,  # 至少一半关键词命中
        "keyword_hit_rate": found / max(total, 1),
        "keywords_found": found,
        "keywords_total": total,
    }


# ─── 五种 Infra Failure 分类 ───

INFRA_CATEGORIES = {
    "timeout": "执行超时",
    "empty_output": "无有效输出",
    "provider_unavailable": "provider 不可用",
    "configuration_error": "配置错误",
    "unexpected_exception": "未预期异常",
}

def classify_infra_failure(output, stderr):
    """根据输出和 stderr 分类 infra failure"""
    combined = (output or "") + " " + (stderr or "")
    if "timeout" in combined.lower():
        return "timeout"
    if "unavailable" in combined.lower() or "rate limit" in combined.lower() or "429" in combined:
        return "provider_unavailable"
    if "configuration" in combined.lower() or "config" in combined.lower() or "auth" in combined.lower():
        return "configuration_error"
    if not (output or "").strip():
        return "empty_output"
    return "unexpected_exception"


def evaluate_skill(skill_name):
    """评估 skill 性能: 调用 hermes chat -q 逐一测试"""
    baseline = load_or_init_baseline()
    prompts = baseline["prompts"]
    results = {}
    infra_failure_count = 0
    evaluable_count = 0

    os.makedirs(STAGING_DIR, exist_ok=True)

    for p in prompts:
        pid = p["id"]
        prompt = p["prompt"]
        expected = p["expected"]

        print(f"  [{pid}] Running...", end="", flush=True)
        start = datetime.datetime.now()

        try:
            # 构造调用: hermes chat -q <prompt>  使用 staging 中的 skill 内容 (如果有)
            cmd = ["hermes", "chat", "-q", prompt]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            duration = (datetime.datetime.now() - start).total_seconds()
            output = (out.stdout or "").strip()
            stderr = (out.stderr or "").strip()

            infra_category = "ok"
            is_infra = False

            if not output or out.returncode != 0:
                is_infra = True
                infra_category = classify_infra_failure(output, stderr)
                infra_failure_count += 1
                score = {"pass": False, "keyword_hit_rate": 0.0, "keywords_found": 0, "keywords_total": len(expected)}
            else:
                score = score_output(output, expected)
                if not score["pass"] and len(output) < 20:
                    # 输出过短且未命中 — 可能也是 infra 问题
                    is_infra = True
                    infra_category = "empty_output"
                    infra_failure_count += 1
                else:
                    evaluable_count += 1

            results[pid] = {
                "score": score,
                "exec": {
                    "duration_s": round(duration, 2),
                    "method": "hermes_chat",
                    "infra_failure": is_infra,
                    "infra_category": infra_category,
                },
            }
            print(f" {'PASS' if score['pass'] else 'FAIL'} ({score['keyword_hit_rate']:.0%} / {duration:.1f}s)", flush=True)

        except subprocess.TimeoutExpired:
            duration = (datetime.datetime.now() - start).total_seconds()
            results[pid] = {
                "score": {"pass": False, "keyword_hit_rate": 0.0, "keywords_found": 0, "keywords_total": len(expected)},
                "exec": {"duration_s": round(duration, 2), "method": "hermes_chat", "infra_failure": True, "infra_category": "timeout"},
            }
            infra_failure_count += 1
            print(f" TIMEOUT ({duration:.1f}s)", flush=True)

        except Exception as e:
            results[pid] = {
                "score": {"pass": False, "keyword_hit_rate": 0.0, "keywords_found": 0, "keywords_total": len(expected)},
                "exec": {"duration_s": 0, "method": "hermes_chat", "infra_failure": True, "infra_category": "unexpected_exception"},
            }
            infra_failure_count += 1
            print(f" ERROR: {str(e)[:40]}", flush=True)

    # 计算摘要
    if infra_failure_count == len(results):
        # 全部 infra failure — 整体标记
        passed = 0
        total = 0
        avg_duration = 0.0
        avg_keyword_hit = 0.0
        overall_status = "infrastructure_failure"
    else:
        passed = sum(1 for r in results.values() if r["score"]["pass"])
        total = evaluable_count
        avg_duration = sum(r["exec"]["duration_s"] for r in results.values()) / max(len(results), 1)
        avg_keyword_hit = sum(r["score"]["keyword_hit_rate"] for r in results.values()
                               if not r["exec"]["infra_failure"]) / max(evaluable_count, 1)
        overall_status = "success" if infra_failure_count == 0 else "partial_infra_failure"

    report = {
        "skill": skill_name,
        "timestamp": datetime.datetime.now().isoformat(),
        "method": "hermes_chat",
        "status": overall_status,
        "infra_failure_count": infra_failure_count,
        "total_infra_categories": {},
        "summary": {
            "pass_rate": round(passed / max(total, 1), 3),
            "passed": passed,
            "total": total,
            "avg_duration_s": round(avg_duration, 1),
            "avg_keyword_hit_rate": round(avg_keyword_hit, 3),
        },
        "results": results,
    }

    # Aggregate infra categories across all results
    categories = {}
    for pid, r in results.items():
        inf = r.get("exec", {}).get("infra_category")
        if inf and inf != "ok":
            cat = r["exec"].get("infra_category", "unknown")
            categories.setdefault(cat, 0)
            categories[cat] += 1
    report["total_infra_categories"] = categories

    # 保存临时结果
    result_path = os.path.join(EVAL_DIR, f"eval-{skill_name}.json")
    with open(result_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"Evaluation saved to {result_path}")

    return report


def compare_with_baseline(skill_name):
    """比较 staging 评估结果 vs 基线"""
    result_path = os.path.join(EVAL_DIR, f"eval-{skill_name}.json")
    if not os.path.exists(result_path):
        print(f"No eval results found for {skill_name}. Run --evaluate first.")
        return None

    with open(result_path) as f:
        current = json.load(f)

    baseline = load_or_init_baseline()

    # Handle infra failure: if current eval is entirely infrastructure failure,
    # do not attempt to compare — return special status
    if current.get("status") == "infrastructure_failure":
        result = {
            "action": "skip",
            "reason": f"All {current.get('infra_failure_count', '?')} prompts were infrastructure failures "
                      f"(categories: {current.get('total_infra_categories', {})}). "
                      f"Cannot compare — fix infrastructure first.",
            "current_status": "infrastructure_failure",
            "infra_categories": current.get("total_infra_categories", {}),
        }
        print(f"  WARNING: Evaluation entirely infrastructure failure, skipping comparison.")
        print(f"  Infra categories: {current.get('total_infra_categories', {})}")
        return result

    # 如果有基线记录, 比较
    baseline_summary = baseline.get("summary")
    current_summary = current["summary"]

    if not baseline_summary:
        print("No baseline summary yet. This run becomes the baseline.")
        return {"action": "baseline_not_set"}

    # 三维比较
    pass_rate_delta = current_summary["pass_rate"] - baseline_summary.get("pass_rate", 0)
    duration_delta = current_summary["avg_duration_s"] - baseline_summary.get("avg_duration_s", 0)
    quality_delta = current_summary["avg_keyword_hit_rate"] - baseline_summary.get("avg_keyword_hit_rate", 0)

    comparison = {
        "pass_rate": {"baseline": baseline_summary.get("pass_rate"),
                      "current": current_summary["pass_rate"],
                      "delta": round(pass_rate_delta, 3)},
        "avg_duration_s": {"baseline": baseline_summary.get("avg_duration_s"),
                           "current": current_summary["avg_duration_s"],
                           "delta": round(duration_delta, 1)},
        "avg_keyword_hit_rate": {"baseline": baseline_summary.get("avg_keyword_hit_rate"),
                                 "current": current_summary["avg_keyword_hit_rate"],
                                 "delta": round(quality_delta, 3)},
    }
    result = {
        "action": "unknown",
        "comparison": comparison,
        "current_status": current.get("status", "unknown"),
        "infra_failure_count": current.get("infra_failure_count", 0),
    }

    # 决策逻辑 — 若有 partial_infra_failure, 在最终结论备注
    THRESHOLD = 0.05  # 5%

    worse_count = 0
    better_count = 0

    if pass_rate_delta < -THRESHOLD:
        worse_count += 1
    elif pass_rate_delta > THRESHOLD:
        better_count += 1

    if quality_delta < -THRESHOLD:
        worse_count += 1
    elif quality_delta > THRESHOLD:
        better_count += 1

    if duration_delta > THRESHOLD * 60:  # 超过 3 秒
        worse_count += 1
    elif duration_delta < -THRESHOLD * 60:
        better_count += 1

    if worse_count > 0 and better_count == 0:
        result["action"] = "reject"
        result["reason"] = f"{worse_count} dimension(s) worse than threshold ({THRESHOLD*100}%)"
    elif worse_count > 0 and better_count > 0:
        result["action"] = "canary"
        result["reason"] = f"Mixed: {better_count} better, {worse_count} worse"
    elif worse_count == 0 and better_count >= 1:
        result["action"] = "promote"
        result["reason"] = f"All dimensions stable or improved"
    else:
        result["action"] = "promote"
        result["reason"] = "No significant changes"

    # Append infra note
    infra_count = current.get("infra_failure_count", 0)
    if infra_count > 0:
        result["reason"] += f" (with {infra_count} infra failures: {current.get('total_infra_categories', {})})"

    return result


def init_baseline():
    """初始化或更新基线 — 使用 hermes chat -q 异步评估每个 prompt"""
    baseline = load_or_init_baseline()
    print(f"Baseline loaded: {len(baseline['prompts'])} prompts")
    print(f"Version: {baseline['version']}, created: {baseline['created'][:19]}")

    # 检查是否需要填充 — 已有全部结果则跳过
    unfilled = [pid for pid, r in baseline['results'].items() if r is None]
    if not unfilled:
        print(f"\nAll {len(baseline['prompts'])} prompts already have baseline results.")
        return baseline

    print(f"\n{len(unfilled)}/{len(baseline['prompts'])} prompts need baseline evaluation.")

    # 逐个评估未填充的 prompt（异步调用 hermes chat -q）
    results = {}
    for p in baseline['prompts']:
        pid = p['id']
        prompt = p['prompt']
        expected = p['expected']
        print(f"  [{pid}] Evaluating: {prompt[:60]}...", end=" ", flush=True)
        try:
            cmd = ["hermes", "chat", "-q", prompt]
            start = datetime.datetime.now()
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            duration = (datetime.datetime.now() - start).total_seconds()
            output = (out.stdout or out.stderr or "").strip()
            if not output:
                results[pid] = {"score": {"pass": False, "keyword_hit_rate": 0.0,
                                          "keywords_found": 0, "keywords_total": len(expected)},
                                "exec": {"duration_s": duration, "method": "hermes_chat",
                                         "infra_failure": True, "infra_category": "empty_output"}}
                print(f"EMPTY ({duration:.1f}s)")
            else:
                lower = output.lower()
                found_kws = [kw for kw in expected if kw.lower() in lower]
                hit_rate = len(found_kws) / max(len(expected), 1)
                results[pid] = {"score": {"pass": hit_rate >= 0.5, "keyword_hit_rate": hit_rate,
                                          "keywords_found": len(found_kws), "keywords_total": len(expected)},
                                "exec": {"duration_s": duration, "method": "hermes_chat",
                                         "infra_failure": False, "infra_category": "ok"}}
                tag = "PASS" if hit_rate >= 0.5 else "FAIL"
                print(f"{tag} ({hit_rate:.0%}/{duration:.1f}s)")
        except subprocess.TimeoutExpired:
            duration = 120
            results[pid] = {"score": {"pass": False, "keyword_hit_rate": 0.0,
                                      "keywords_found": 0, "keywords_total": len(expected)},
                            "exec": {"duration_s": duration, "method": "hermes_chat",
                                     "infra_failure": True, "infra_category": "timeout"}}
            print(f"TIMEOUT (120s)")
        except Exception as e:
            results[pid] = {"score": {"pass": False, "keyword_hit_rate": 0.0,
                                      "keywords_found": 0, "keywords_total": len(expected)},
                            "exec": {"duration_s": 0, "method": "hermes_chat",
                                     "infra_failure": True, "infra_category": str(e)[:50]}}
            print(f"ERROR: {str(e)[:40]}")

    # 计算摘要
    evaluable = {pid: r for pid, r in results.items()
                 if not r['exec'].get('infra_failure')}
    infra_count = sum(1 for r in results.values() if r['exec'].get('infra_failure'))
    evaluable_count = len(evaluable)
    passed = sum(1 for pid, r in evaluable.items() if r['score']['pass'])
    total = evaluable_count
    avg_duration = sum(r['exec']['duration_s'] for r in evaluable.values()) / max(evaluable_count, 1)
    avg_keyword_hit = sum(r['score']['keyword_hit_rate'] for r in evaluable.values()) / max(evaluable_count, 1)

    baseline['results'] = results
    baseline['summary'] = {
        'pass_rate': round(passed / max(total, 1), 3),
        'passed': passed,
        'total': total,
        'avg_duration_s': round(avg_duration, 1),
        'avg_keyword_hit_rate': round(avg_keyword_hit, 3),
    }
    with open(BASELINE_PATH, 'w') as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n{'='*50}")
    print(f"  Baseline initialized:")
    print(f"  Pass rate:       {baseline['summary']['pass_rate']:.1%} ({passed}/{total})")
    print(f"  Avg duration:    {baseline['summary']['avg_duration_s']:.1f}s")
    print(f"  Keyword hit:     {baseline['summary']['avg_keyword_hit_rate']:.1%}")
    if infra_count:
        print(f"  Infra failures:  {infra_count}/{len(results)}")
    print(f"{'='*50}")

    return baseline


def promote(skill_name):
    """从 staging promote 到 production"""
    staging_md = os.path.join(STAGING_DIR, skill_name, "SKILL.md")
    if not os.path.exists(staging_md):
        print(f"No staging version found for {skill_name}")
        return False

    # 读 staging 内容
    with open(staging_md) as f:
        content = f.read()

    # 找到 production 路径
    import glob as _glob
    prod_paths = _glob.glob(os.path.join(SKILLS_DIR, "**", skill_name, "SKILL.md"), recursive=True)
    if not prod_paths:
        print(f"No production SKILL.md found for {skill_name}")
        return False

    prod_md = prod_paths[0]

    # 备份 production
    backup_path = prod_md + f".bak.{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    with open(prod_md) as f:
        with open(backup_path, "w") as b:
            b.write(f.read())

    # 写入新版本
    with open(prod_md, "w") as f:
        f.write(content)

    # 清理 staging
    os.remove(staging_md)
    try:
        os.rmdir(os.path.dirname(staging_md))
    except OSError:
        pass

    # 记录 promote log
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "skill": skill_name,
        "action": "promote",
        "backup": backup_path,
    }
    with open(PROMOTE_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"Promoted {skill_name} to production. Backup at {backup_path}")
    return True


def print_status():
    """打印当前状态"""
    baseline = load_or_init_baseline()
    print(f"\n{'='*60}")
    print(f"  Eval Harness Status")
    print(f"{'='*60}")
    print(f"  Baseline:    {len(baseline['prompts'])} prompts, v{baseline['version']}")
    print(f"  Created:     {baseline['created'][:19]}")

    summary = baseline.get("summary")
    if summary:
        print(f"\n  ┌──────────────┬──────────┐")
        print(f"  │ Metric       │ Baseline │")
        print(f"  ├──────────────┼──────────┤")
        print(f"  │ Pass rate    │ {summary.get('pass_rate', 'N/A'):>7.1%} │")
        print(f"  │ Avg duration │ {summary.get('avg_duration_s', 0):>7.1f}s  │")
        print(f"  │ Keyword hit  │ {summary.get('avg_keyword_hit_rate', 0):>7.1%} │")
        print(f"  └──────────────┴──────────┘")

    # staging 目录检查
    if os.path.exists(STAGING_DIR):
        stagings = [d for d in os.listdir(STAGING_DIR)
                    if os.path.isdir(os.path.join(STAGING_DIR, d))]
        if stagings:
            print(f"\n  Staging: {len(stagings)} skill(s) pending: {', '.join(stagings)}")
        else:
            print(f"\n  Staging: empty")
    else:
        print(f"\n  Staging: directory not created yet")

    # promote log
    promotes = []
    if os.path.exists(PROMOTE_LOG):
        with open(PROMOTE_LOG) as f:
            for line in f:
                try:
                    promotes.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if promotes:
        last = promotes[-1]
        print(f"  Last promote: {last['skill']} at {last['timestamp'][:19]}")

    print(f"{'='*60}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Eval Harness — L4 准入门")
    parser.add_argument("--init-baseline", action="store_true", help="初始化基线")
    parser.add_argument("--evaluate", metavar="SKILL", help="评估 skill 改动")
    parser.add_argument("--compare", metavar="SKILL", help="与基线比较")
    parser.add_argument("--promote", metavar="SKILL", help="promote staging 到 production")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    if args.init_baseline:
        init_baseline()
    elif args.evaluate:
        report = evaluate_skill(args.evaluate)
        if report:
            s = report["summary"]
            print(f"\nEvaluation: {args.evaluate}")
            print(f"  Pass rate:   {s['pass_rate']:.1%} ({s['passed']}/{s['total']})")
            print(f"  Duration:    {s['avg_duration_s']:.1f}s avg")
            print(f"  Keyword hit: {s['avg_keyword_hit_rate']:.1%}")
    elif args.compare:
        result = compare_with_baseline(args.compare)
        if result and result.get("action"):
            comp = result.get("comparison", {})
            print(f"\nComparison: {args.compare}")
            print(f"  Action: {result['action'].upper()} — {result.get('reason', '')}")
            for metric, vals in comp.items():
                d = vals.get("delta", 0)
                arrow = "↑" if d > 0 else ("↓" if d < 0 else "→")
                print(f"  {metric:20s}: {vals.get('baseline', 'N/A')} {arrow} {vals.get('current', 'N/A')} (Δ={d:+.3f})")
    elif args.promote:
        promote(args.promote)
    elif args.status:
        print_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
