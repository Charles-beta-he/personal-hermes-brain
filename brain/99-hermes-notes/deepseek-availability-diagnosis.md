# DeepSeek 可用性诊断 — 2026-04-28

## 问题
multi-model-architecture 检查发现 deepseek-v4-pro 在 route_outcomes (1628 行) 中
被调用次数 = 0，尽管 quorum.yaml T1/T2/T3 planners 列表都包含它。

## 实际诊断结果 (model-router probe)
- ✅ DEEPSEEK_API_KEY 已在 ~/.hermes/.env 中配置 (经 _model_available 三层检查通过)
- ✅ probe_all_providers 报告 deepseek-v4-pro/v4-flash/v4-flash-thinking 全部 available
- ✅ provider_availability.json 中 deepseek 三个模型 status=available

## 根因
不是 auth 缺失，而是 **model-router select_pair 永远不选 DeepSeek**：

1. select_pair 用 ε-greedy 评分，DeepSeek 由于:
   - 历史 trace = 0 → score = None
   - cold start: ε-greedy 在 ε=0.1 默认下偏向 exploit
   - exploit 时只看有 score 的模型 (mimo/gpt-5.4/gpt-5.5/claude)

2. 5 次 select-pair 抽样: 全部为 (gpt-5.5, mimo-v2.5-pro)
   候选列表包含 deepseek 但 model_scores 显示 deepseek-v4-pro=None

## 不修复的理由
属于设计内行为 (skill memory 第 10 条 pitfall):
> model-router cold start: 只有所有候选都 cold 时才强制 epsilon=1；
> 若 gpt-5.5 等 warm model 已有足够 trace, 保留 ε-greedy

强行让 DeepSeek 在 cold 状态被选中，会污染 baseline 评分体系。
正确做法是让 consult-models 多脑流程 (Phase 6) 主动调用 DeepSeek 一次，
让它有 trace 数据，自然进入 ε-greedy 评分循环。

## 后续行动
- consult-models nightly cron (Phase 6) 启用后会主动调用 T1 planners
  (含 deepseek-v4-pro)，每天 ~1 次 trace
- 7 天后 (累计 ≥10 trace)，min_traces_per_model 阈值满足，DeepSeek 自动进入
  ε-greedy 评分排序
- 期间可用 model-router select --task-class manual --epsilon 1.0 强制探索
