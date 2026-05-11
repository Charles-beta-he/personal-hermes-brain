# Session Discipline Protocol — 控制论能控/能观基线

> ch04 线性设计: todo + memory + session_search = 状态观测基础设施

## 每个 Session 的强制规范

### 1. Todo 使用规范

**启动时:**
- [ ] 用 `todo` 工具读取当前列表
- [ ] 如无列表，创建新列表，内容来自上级 P9 的 task prompt
- [ ] 标记 `in_progress` 的任务不得超过 1 个

**执行中:**
- [ ] 每完成一个子任务，立即标记 `completed`
- [ ] 发现新任务时，追加到列表末尾
- [ ] 遇到阻塞时，将当前任务标记为 pending，添加阻塞原因

**结束时:**
- [ ] 所有任务必须处于 `completed` / `cancelled` / `pending`（明确原因）
- [ ] 输出本次 session 的完成摘要

### 2. Memory 使用规范

**写入时机:**
- 用户明确说"记住"或"以后..."
- 发现环境事实（OS、工具版本、项目结构）
- 用户偏好（编码风格、通信方式、质量要求）
- 项目约定（API 模式、命名规范、架构决策）
- 跨 session 仍然有用的经验

**写入格式:**
```
目标: user（用户偏好）或 memory（环境/项目事实）
格式: 声明式事实，不要指令
示例: "用户偏好简洁响应" ✓ — "Always respond concisely" ✗
```

**禁止写入:**
- 任务进度、session 结果、临时 TODO
- 容易重新发现的信息
- 过长的原始数据

### 3. Session Search 使用规范

**触发条件:**
- 用户说"之前"、"上次"、"记得"、"as I mentioned"
- 遇到似曾相识的问题
- 需要验证假设是否已讨论过

**搜索策略:**
- 先用 broad OR 查询（关键词用 OR 连接）
- 如无结果，尝试单个关键词
- 确认匹配后再引用，不要假设

---

## 负反馈闭环

每轮执行后必须产生可观测的反馈：
- test 结果 → pass/fail
- build 结果 → success/error
- browser 验证 → screenshot/diff

无反馈 = 状态不可观 = 控制失效
