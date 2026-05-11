#!/usr/bin/env python3
"""快速填充 eval-harness baseline — 用 DeepSeek API 调用"""
import os, json, datetime, sys, concurrent.futures, requests

BASELINE_PATH = os.path.expanduser("~/.hermes/eval/eval-baseline.json")

def get_deepseek_config():
    """从 hermes .env 加载 DeepSeek API key"""
    env_path = os.path.expanduser("~/.hermes/.env")
    config = {"base_url": "https://api.deepseek.com", "api_key": None}
    
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    config["api_key"] = line.split("=", 1)[1].strip()
                elif line.startswith("DEEPSEEK_BASE_URL="):
                    config["base_url"] = line.split("=", 1)[1].strip()
    
    return config

def call_deepseek(prompt, config):
    """调用 DeepSeek API"""
    if not config["api_key"]:
        return None, "No DeepSeek API key"
    
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        resp = requests.post(f"{config['base_url']}/chat/completions", 
                           headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, str(e)

def evaluate_one(p):
    pid = p["id"]
    prompt = p["prompt"]
    expected = p["expected"]
    
    try:
        config = get_deepseek_config()
        output, error = call_deepseek(prompt, config)
        
        if error:
            return (pid, {"score": {"pass": False, "keyword_hit_rate": 0.0,
                                     "keywords_found": 0, "keywords_total": len(expected)},
                          "exec": {"duration_s": 0, "method": "deepseek_api",
                                   "infra_failure": True, "infra_category": str(error)[:50]}},
                         f"ERROR: {error[:40]}")
        
        if not output:
            return (pid, {"score": {"pass": False, "keyword_hit_rate": 0.0,
                                     "keywords_found": 0, "keywords_total": len(expected)},
                          "exec": {"duration_s": 0, "method": "deepseek_api",
                                   "infra_failure": True, "infra_category": "empty_output"}},
                     "EMPTY")
        
        lower = output.lower()
        found_kws = [kw for kw in expected if kw.lower() in lower]
        hit_rate = len(found_kws) / max(len(expected), 1)
        result = {"score": {"pass": hit_rate >= 0.5, "keyword_hit_rate": hit_rate,
                            "keywords_found": len(found_kws), "keywords_total": len(expected)},
                  "exec": {"duration_s": 0, "method": "deepseek_api",
                           "infra_failure": False, "infra_category": "ok"}}
        tag = "PASS" if hit_rate >= 0.5 else "FAIL"
        return (pid, result, f"{tag} ({hit_rate:.0%}/0.0s)")
    
    except Exception as e:
        return (pid, {"score": {"pass": False, "keyword_hit_rate": 0.0,
                                 "keywords_found": 0, "keywords_total": len(expected)},
                      "exec": {"duration_s": 0, "method": "deepseek_api",
                               "infra_failure": True, "infra_category": str(e)[:50]}},
                 f"ERROR: {str(e)[:40]}")

def main():
    with open(BASELINE_PATH) as f:
        baseline = json.load(f)
    
    unfilled = [p for p in baseline["prompts"] if baseline["results"].get(p["id"]) is None]
    if not unfilled:
        print(f"All {len(baseline['prompts'])} prompts already filled.")
        return
    
    print(f"Filling {len(unfilled)} baseline prompts (DeepSeek API)...")
    print(f"{'='*60}")
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        fut_map = {pool.submit(evaluate_one, p): p for p in unfilled}
        done = 0
        total = len(unfilled)
        for fut in concurrent.futures.as_completed(fut_map):
            pid, result, tag = fut.result()
            results[pid] = result
            done += 1
            summary = result['score']
            print(f"  [{done}/{total}] [{pid}] {tag} | passed={summary['pass']} kw={summary['keyword_hit_rate']:.0%}", flush=True)
    
    # merge
    for pid, r in results.items():
        baseline["results"][pid] = r
    
    # 计算摘要
    evaluable = {pid: r for pid, r in baseline["results"].items()
                 if r and not r["exec"].get("infra_failure")}
    infra_count = sum(1 for r in baseline["results"].values()
                      if r and r["exec"].get("infra_failure"))
    evaluable_count = len(evaluable)
    passed = sum(1 for r in evaluable.values() if r["score"]["pass"])
    total = evaluable_count
    avg_duration = sum(r["exec"]["duration_s"] for r in evaluable.values()) / max(evaluable_count, 1)
    avg_keyword_hit = sum(r["score"]["keyword_hit_rate"] for r in evaluable.values()) / max(evaluable_count, 1)
    
    baseline["summary"] = {
        "pass_rate": round(passed / max(total, 1), 3),
        "passed": passed,
        "total": total,
        "avg_duration_s": round(avg_duration, 1),
        "avg_keyword_hit_rate": round(avg_keyword_hit, 3),
    }
    
    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False, default=str)
    
    total_filled = len(results)
    total_results = sum(1 for r in baseline["results"].values() if r is not None)
    print(f"\n{'='*50}")
    print(f"  Baseline: {total_filled} new, {total_results}/{len(baseline['prompts'])} total filled")
    print(f"  Pass rate:       {baseline['summary']['pass_rate']:.1%} ({passed}/{total})")
    print(f"  Avg duration:    {baseline['summary']['avg_duration_s']:.1f}s")
    print(f"  Keyword hit:     {baseline['summary']['avg_keyword_hit_rate']:.1%}")
    if infra_count:
        print(f"  Infra failures:  {infra_count}/{total_results}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
