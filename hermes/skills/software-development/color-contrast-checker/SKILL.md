---
name: color-contrast-checker
description: "自动验证 Web 应用所有文字的 WCAG 对比率。扫描 CSS 变量/硬编码颜色，计算前景/背景对比度，输出 A/AA/AAA 合规报告。用于 UIMax 审计的无障碍维度评分。"
license: MIT
tags: [accessibility, wcag, contrast, a11y, uimax]
---

# Color Contrast Checker — WCAG 文字对比度自动验证

> 扫描项目所有 CSS/JSX 中的颜色组合，计算对比度，输出 WCAG AA/AAA 合规报告。

## When to Use

- UIMax 审计中「无障碍」维度评分
- 主题切换后验证新配色合规性
- 新增组件时检查文字可读性
- 用户说「对比度」「可读性」「WCAG」

## WCAG 对比率标准

| 级别 | 普通文字 (<18px) | 大文字 (≥18px bold / ≥24px) |
|------|-----------------|---------------------------|
| AA   | ≥ 4.5:1          | ≥ 3:1                     |
| AAA  | ≥ 7:1            | ≥ 4.5:1                   |

## Workflow

### Phase 1: 收集颜色定义

扫描 CSS 变量和硬编码颜色：

```bash
# CSS 变量定义
rg '--[a-z-]+:\s*#[0-9a-fA-F]{3,8}' apps/web/src/ -g '*.css'

# 硬编码颜色 (JSX inline)
rg '(?:color|background).*#[0-9a-fA-F]{3,8}' apps/web/src/ -g '*.jsx'
```

### Phase 2: 提取主题颜色对

从 CSS 文件中提取每个主题的前景/背景配对：

```
[data-theme="sci-fi"]:
  --bg-primary: #050a14
  --text-primary: #e0f4ff
  --text-secondary: #7ab8d9
  --text-muted: #3a6a8a
  --accent-primary: #00d4ff
```

关键配对（必须检查）：
1. `text-primary` on `bg-primary` — 主文字
2. `text-secondary` on `bg-primary` — 次要文字
3. `text-muted` on `bg-primary` — 弱化文字
4. `text-primary` on `bg-surface` — 卡片文字
5. `accent-primary` on `bg-primary` — 强调色
6. `accent-danger` on `bg-primary` — 错误文字
7. `accent-success` on `bg-primary` — 成功文字

### Phase 3: 计算对比度

使用相对亮度公式 (WCAG 2.0):

```python
def relative_luminance(r, g, b):
    """计算相对亮度 (0-1)"""
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

def contrast_ratio(hex1, hex2):
    """计算两个颜色的对比度"""
    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    l1 = relative_luminance(*hex_to_rgb(hex1))
    l2 = relative_luminance(*hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
```

### Phase 4: 生成报告

输出格式：

```
=== WCAG Contrast Report ===

Theme: sci-fi

| 配对 | 前景 | 背景 | 对比率 | AA | AAA |
|------|------|------|--------|----|----|
| text-primary / bg-primary | #e0f4ff | #050a14 | 15.2:1 | ✅ | ✅ |
| text-secondary / bg-primary | #7ab8d9 | #050a14 | 7.8:1 | ✅ | ✅ |
| text-muted / bg-primary | #3a6a8a | #050a14 | 3.1:1 | ⚠️ | ❌ |
| accent-primary / bg-primary | #00d4ff | #050a14 | 9.4:1 | ✅ | ✅ |

⚠️ text-muted on bg-primary: 3.1:1 < 4.5:1 (AA 普通文字不达标)
   建议: 仅用于大文字(≥18px)或装饰性文字
```

### Phase 5: 修复建议

对不达标的配对，提供修复方案：

```css
/* 不达标: 对比率 3.1:1 */
--text-muted: #3a6a8a;

/* 修复: 提亮至 4.5:1+ */
--text-muted: #5a8aaa;
```

## 评分标准 (UIMax)

| 合规率 | 评分 |
|--------|------|
| 100% AA | A+ |
| 90%+ AA | A |
| 80%+ AA | B+ |
| 70%+ AA | B |
| <70% AA | C 或更低 |

## 自动化脚本

使用 Python 一键扫描：

```python
# scripts/contrast-check.py
import re, sys

def scan_css_vars(css_file):
    """从 CSS 文件提取主题变量"""
    themes = {}
    current_theme = None
    with open(css_file) as f:
        for line in f:
            m = re.search(r'\[data-theme="([^"]+)"\]', line)
            if m:
                current_theme = m.group(1)
                themes[current_theme] = {}
            m = re.search(r'(--[\w-]+):\s*(#[0-9a-fA-F]{3,8})', line)
            if m and current_theme:
                themes[current_theme][m.group(1)] = m.group(2)
    return themes

# ... contrast_ratio 函数见上 ...
# ... 输出报告 ...
```

## 修复技巧：保持主题色调

修复不达标配对时，避免使用纯灰值（会破坏主题一致性）。按比例提亮原始色：

```python
def find_tinted_fix(bg_hex, orig_hex, target=4.5):
    """按比例提亮原始色（保持色调）直到达标"""
    or_, og, ob = hex_to_rgb(orig_hex)
    for scale in range(100, 260):
        r = min(255, or_ * scale // 100)
        g = min(255, og * scale // 100)
        b = min(255, ob * scale // 100)
        candidate = f'#{r:02x}{g:02x}{b:02x}'
        if contrast_ratio(candidate, bg_hex) >= target:
            return candidate
    return '#999999'  # fallback
```

示例：sci-fi 的 `--text-muted: #3a6a8a`（蓝色调）→ `#457ea4`（仍为蓝色，4.5:1）

## Pitfalls

1. **CSS var() fallback 色**: `var(--accent-danger, #f87171)` 中 fallback 色可能与实际渲染色不同，需解析实际 CSS 变量
2. **渐变/透明背景**: `color-mix()` 和 `rgba()` 需要计算最终混合色
3. **大文字判定**: bold ≥18px 或 normal ≥24px 适用 3:1 标准
4. **装饰性元素**: 图标、分隔线等不需满足对比度要求
5. **⚠️ CSS 重复选择器**: 某些 CSS 文件中 `[data-theme="xxx"]` 出现多次（如变量定义 + grid background）。解析时**必须用 `if theme not in themes` 保护**，否则后面的空规则会覆盖已解析的变量：
   ```python
   # ❌ 错误 — 第二次出现会清空已解析的变量
   themes[current] = {}
   # ✅ 正确 — 仅首次创建
   if current not in themes:
       themes[current] = {}
   ```
6. **⚠️ RGB 空格分隔格式**: CSS 中 `--ink-rgb: 224 244 255` 是空格分隔（非逗号），且用于 `rgb(var(--ink-rgb) / <alpha-value>)`。需额外解析此格式并映射到标准变量名
