---
name: inference-sh
description: "Inference Sh workflow skill. See references/ for detailed guides."
license: MIT
metadata:
  hermes:
    tags: [inference, workflow]
    related_skills: [pua, loop]
---

# Inference Sh

> Inference Sh 相关的工作流 Skill

## 输入

- 用户请求的具体参数
- 相关上下文或文件路径

## 输出

- 执行结果或生成的文件
- 验证报告（如适用）

## 约束

- 遵循项目规范
- 不泄露敏感信息
- 在 context budget 内完成

## 边界条件

- 输入参数为空或缺失时，返回错误提示而非静默失败
- 超出 context budget 时，截断输入并告知用户
- 网络/API 不可用时，记录错误并重试（最多 3 次）

## 检查点

- [ ] 输入参数完整
- [ ] 输出符合预期格式
- [ ] 验证通过

## 示例

### 示例 1: 基本用法

```
Input:  用户请求 inference 相关操作
Output: 执行结果 + 验证报告
```

### 示例 2: 参数缺失

```
Input:  缺少必要参数
Output: 错误提示，列出必需参数
```

## 关联 Skill

- `pua`: 核心行为基线
- `loop`: 迭代管理
