# System Decomposition — 大系统分解原则

> ch13 大系统: 模块化skill降低耦合，模块间只交换最小信息

## Skill 模块分层

```
Layer 0 (基础设施):
  - mcp (filesystem, time, memory)
  - cronjob (定时任务)
  - terminal (命令执行)

Layer 1 (数据层):
  - bayesian-agent (置信度管理)
  - cognitive-load-agent (认知负荷)
  - darwin-skill (进化优化)
  - ooda-agent (迭代速度)

Layer 2 (控制层):
  - p10 (战略)
  - p9 (任务拆解)
  - p7 (执行)
  - loop (迭代)
  - pua (压力驱动)

Layer 3 (应用层):
  - github-* (GitHub 工作流)
  - dogfood (QA 测试)
  - cloudflare-pages-pnpm (部署)
  - uimax-audit (UI 审计)

Layer 4 (业务层):
  - gsd-bridge (GSD 集成)
  - arc-dispatch-executor (任务执行)
  - browser-harness-integration (浏览器验证)
```

## 耦合规则

```
允许:
  上层 → 下层: 调用 (Layer 3 调用 Layer 2 的 loop)
  同层 → 同层: 协作 (github-pr-workflow ↔ requesting-code-review)

禁止:
  下层 → 上层: 依赖倒置
  跨层跳跃: Layer 4 直接调用 Layer 0
  循环依赖: A → B → A
```

## 接口契约

每个 Layer 暴露的接口:

```yaml
Layer 2 (控制层):
  input:
    - task_spec: 任务描述
    - constraints: 约束条件
    - context_budget: 可用 token
  output:
    - result: 执行结果
    - verification: 验证报告
    - health_delta: 健康度变化
    - context_used: 实际消耗 token
  events:
    - on_success: 正常完成
    - on_failure: 失败告警
    - on_timeout: 超时处理
```

## 信息隐藏

```
Layer 3 (应用层) 不需要知道:
  - bayesian-agent 的 Beta 参数
  - cognitive-load 的 chunk 算法
  - darwin 的 scoring 标准

只需要知道:
  - 调用 skill 的触发条件
  - 预期输出格式
  - 失败时的 fallback 路径
```
