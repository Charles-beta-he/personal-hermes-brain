# GitHub 仓库分析 → 优化方案 执行策略

## 6 Phase 流程

### Phase 1: 快速扫描 (30s)
- clone 到本地 (避免网络延迟)
- `find + wc -l` 得到文件结构 + 行数
- 识别语言/框架/入口点
- README / docs 速读

### Phase 2: 架构理解 (2-3min)
- 读核心入口文件 (main, index, app)
- 追踪数据流 (输入→处理→输出)
- 识别 token 流经的每个节点
- 画出文本架构图

### Phase 3: 深潜关键模块 (3-5min)
- 读实现细节 (逐行理解, 不是扫一遍)
- 找常量/配置/阈值
- 找 hook 点/中间件/拦截层
- 找已有的优化机制

### Phase 4: 对比分析
- 与当前架构逐层对比
- 标记: ✅ 已有 / ⚠️ 差距 / ❌ 缺失
- 量化每个差距的 token 影响

### Phase 5: 方案设计
- 按 P0-P4 排优先级
- 每个方案: 原理 + 集成点 + 代码 + 效果估算
- 融合架构图

### Phase 6: 落地执行
- 先修 bug (CASI marker 不匹配)
- 再加新组件 (task_router, result_spiller)
- 最后改架构 (prefix cache 拆分)
- 每步验证编译 + 测试

## 关键原则
1. 先理解再改, 不盲抄
2. 复用已有拦截点, 不改核心循环
3. 每个优化有配置开关, 可回滚
4. 量化效果, 不靠感觉

## 实际教训
- OpenWolf 不是文件读取层, 是 hooks 系统 → 先读代码再下结论
- CASI marker 不匹配 → 改源码必须验证实际运行
- compress_tool_output 是 DEAD CODE → grep 确认调用点
- state.db FTS 膨胀 5.5x → 分析 dbstat 而非猜
