# selective-adoption — 方法论记录
> 从第三方仓库选择性借鉴并落地为 Hermes 原生 skill 的 5 步工作流
> 本会话中应用于: gstack (3 skills), agent-skills (7 skills), GitNexus (code-intel.py)

## 5 步流程

1. **Remote Scan** — curl API: repo info, README, 目录列表, 采样文件。绝不 clone。
2. **Framework Audit Score** — 6 维度 × 权重 → /100 分 (framework-audit 方法论)
3. **Map Net-New** — 逐项对比 Hermes 已有能力, 跳过重叠, 标记净新增
4. **Extract Methodology** — 读原始 SKILL.md, 提取流程/原则/验证标准, 剥离平台依赖
5. **Write Hermes SKILL.md** — YAML frontmatter + 编号步骤 + 反模式 + 验证清单, 控制在 3KB 内

## 历史成果

| 来源 | 评分 | 结果 | 产物 |
|------|------|------|------|
| gstack | 62/100 | selective | browser-qa, design-audit, ship |
| GitNexus | 76/100 | reference | code-intel.py v2 (轻量替代) |
| agent-skills | 87.5/100 | selective | 7 净新 SKILL.md |
