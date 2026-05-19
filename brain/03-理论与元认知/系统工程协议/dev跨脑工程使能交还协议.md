---
title: dev跨脑工程使能交还协议 v1
created: 2026-05-19
status: protocol-v1
capability_delta: 明确 dev 脑在多脑系统中的工程补洞、验证、交还边界，防止 dev 越权成领域判断脑
related:
  - hermes/brains/dev/brain.yaml
  - brain/04-知识原子/atoms/社会系统工程三层.md
---

# dev跨脑工程使能交还协议 v1

## 1. dev 的位置

dev 是工程能力打通与交付中心：

- 主脑直接调用：开发、修复、测试、构建、browser harness、API/contract、CI、交付验证。
- 其他脑间接调用：当专业脑缺少工具、connector、脚本、验证链路或运行时能力时，dev 负责补齐。

不变红线：dev 不替 research 判定来源真伪，不替 design 判定设计方向，不替 media/mlops 做领域专家结论，不替 main 做最终仲裁。

## 2. 请求契约

请求方必须给 dev：

```yaml
cross_brain_enablement_request:
  requesting_brain: research|design|media|mlops|workflow|main|hermes-core
  original_task: "..."
  missing_capability: "..."
  desired_artifact: script|cli|connector|browser_harness|test|dashboard|adapter|validator
  input_contract: "..."
  output_contract: "..."
  acceptance_evidence: "..."
  return_to_brain: "..."
```

## 3. dev 交还契约

```yaml
cross_brain_enablement_handback:
  delivered_artifact: "path_or_command"
  invocation_example: "..."
  verification:
    commands: []
    results: []
  limits:
    known_failures: []
    unsupported_cases: []
  evidence_bundle:
    - artifact:...
    - proof:...
  return_to_brain: "..."
  next_step_for_requesting_brain: "..."
```

## 4. 生命周期

1. main 或 registry 将 capability_gap 路由到 dev。
2. dev 明确最小工程交付物和验收命令。
3. dev 实现 + 测试 + 自检。
4. dev 写 handback。
5. 请求脑恢复原任务并做领域验收。
6. workflow 决定是否沉淀 skill/protocol。

## 5. 验收门

- artifact 存在且可调用。
- invocation_example 能被复制执行。
- 至少一个验证命令 PASS。
- handback 明确 return_to_brain。
- 领域结论由请求脑/main 验收，不由 dev 自证。

## 6. 与钱学森系统工程的对应

- dev = 执行/生产子系统。
- main = 总体设计部。
- research/workflow = 知识体系。
- hermes-core = 控制与观测系统。
- handback = 分解协调后的集成接口。
