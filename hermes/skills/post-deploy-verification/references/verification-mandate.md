# Verification Mandate — 强制验证规范

> ch03 稳定性: 每轮验证 = 负反馈；无验证结果不进入下一轮

## 核心规则

**每次代码修改后，必须执行以下至少一项验证：**

| 验证类型 | 适用场景 | 工具 | 通过标准 |
|---------|---------|------|---------|
| **单元测试** | 逻辑修改 | `pnpm test` / `pytest` / `jest` | 全部通过 |
| **构建验证** | 任何文件改动 | `pnpm build` / `npm run build` | 0 错误 |
| **浏览器验证** | UI/前端改动 | `browser_navigate` + `browser_vision` | 视觉正常 |
| **Lint/Format** | 代码风格 | `eslint` / `prettier --check` | 0 警告 |
| **Type Check** | TS 项目 | `tsc --noEmit` | 0 类型错误 |

## 验证顺序

```
1. Lint/Format (最快，先排雷)
2. Type Check (编译期错误)
3. Unit Test (逻辑正确性)
4. Build (集成正确性)
5. Browser (视觉正确性)
```

## 失败处理

**验证失败时，禁止进入下一轮。** 必须：
1. 分析失败原因（根因，不是症状）
2. 修复问题
3. 重新执行全部验证
4. 全部通过后才继续

## 冰山法则

**同一类问题在同一 session 中不得出现 3 次以上。**
- 第 1 次: 修复
- 第 2 次: 修复 + 检查同类代码
- 第 3 次: 触发极限环告警，切换策略（见 ooda-agent 对抗性 OODA）

## 与 Darwin-skill 集成

每次验证结果影响 skill 置信度：
- 验证通过 → 当前 skill alpha + 0.5
- 验证失败 → 当前 skill beta + 1
- 连续 3 次失败同一 skill → 降级为 D 级，触发 darwin-skill 优化
