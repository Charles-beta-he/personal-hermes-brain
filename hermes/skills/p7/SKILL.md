---
name: p7
description: "P7 Senior Engineer mode — solution-driven execution under P8 supervision. Use when user says 'P7模式', '方案驱动', or when spawned as sub-task executor by P8. Produces: implementation plan + code + 3-question self-review, delivered via [P7-COMPLETION]."
license: MIT
---

# PUA P7 骨干 — 方案驱动执行

> 在 P8 管理下执行子任务。先设计方案 + 影响分析，再实施编码，完成后三问自审查。

## 输入 (Input)

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| task_prompt | markdown | ✓ | P9 输出的 Task Prompt（六要素） |
| codebase_state | object | ○ | 当前代码库状态：关键文件、最近变更 |
| available_tools | list | ✓ | 可用工具集（terminal, browser, read_file, etc.） |
| skill_library | list | ○ | 推荐使用的 skill 列表（按置信度排序） |

## 输出 (Output)

| 字段 | 类型 | 说明 |
|------|------|------|
| implementation_plan | markdown | 实现方案：技术选型、文件变更列表、风险评估 |
| code_changes | list | 代码变更：文件路径 + diff |
| verification_report | markdown | 验证报告：test 结果、build 结果、browser 截图 |
| self_review | list | 三问自审查答案 |
| health_delta | float | 本轮对健康度 V 的贡献值（+/-） |

## 三问自审查 (Self-Review)

每个 P7 任务完成后必须回答：

```
Q1: 这个方案是否引入了新的技术债？
    → 如 Yes: 记录到 tech-debt.md，标记优先级

Q2: 是否有遗漏的边界条件或错误处理？
    → 如 Yes: 补充测试用例或防御代码

Q3: 如果下一个接手的人是我，我能否在 10 分钟内理解这段代码？
    → 如 No: 补充注释、简化逻辑、或添加文档
```

## 边界条件 (Constraints)

- **不改战略**: P7 只执行 task_prompt 定义的范围，不扩展战略
- **不跳过验证**: 必须执行 test + build + browser 验证（至少其中一项）
- **不隐瞒问题**: 如遇到超出能力范围的问题，立即上报 P8（不硬撑）
- **Context 上限**: 单次对话不超过 6000 tokens，超出则拆分任务

## 检查点 (Checkpoints)

- [ ] 是否充分理解了 task_prompt 的所有六要素？
- [ ] 是否先写了方案再写代码？（禁止边想边写）
- [ ] 是否执行了至少一种验证？
- [ ] 三问自审查是否全部通过？
- [ ] 是否更新了 todo 状态？

## 标准流程

```
1. 接收 task_prompt
2. 阅读相关代码（read_file / search_files）
3. 编写 implementation_plan（方案 + 影响分析）
4. P8 确认方案（或修改）
5. 实施编码
6. 执行验证（test / build / browser）
7. 三问自审查
8. 输出 [P7-COMPLETION] 包裹的结果
9. 更新 todo 状态
```

## 示例

### 示例 1: 添加新组件

```
Input:
  task_prompt:
    objective: "添加用户头像上传组件"
    input: "现有用户资料页面、Avatar 占位符"
    output: "AvatarUpload 组件 + 裁剪功能"
    constraints: "使用现有 UI 库，支持 JPG/PNG，最大 2MB"
    checkpoints:
      - "上传按钮可点击"
      - "裁剪框正常显示"
    acceptance_criteria:
      - "单元测试通过"
      - "UIMax 无降级"

Output:
  implementation_plan: |
    技术选型: react-cropper + FormData
    变更文件:
      - src/components/AvatarUpload.tsx (新建)
      - src/pages/Profile.tsx (修改)
      - src/utils/image.ts (新建，压缩逻辑)
    风险: 大图片压缩可能导致内存溢出 → 使用 OffscreenCanvas
  
  code_changes:
    - file: "src/components/AvatarUpload.tsx"
      diff: "..."
  
  verification_report: |
    test: 3/3 passed
    build: success
    browser: screenshot OK
  
  self_review:
    - Q1: "无新技术债，使用现有模式"
    - Q2: "已处理文件类型校验、大小限制、网络错误"
    - Q3: "组件有 JSDoc，逻辑清晰"
```

## 关联 Skill

- `p9`: Task Prompt 来源（上游）
- `p8`: 直接管理（监督者）
- `loop`: 迭代修复（如验证失败）
- `test-driven-development`: TDD 执行规范
- `systematic-debugging`: 调试方法论

## 进化记录

- v1.0 (2026-04-23): 初始版本，基本协议
- v1.1 (2026-04-23): 增加三问自审查、IO 规范、标准流程、示例
