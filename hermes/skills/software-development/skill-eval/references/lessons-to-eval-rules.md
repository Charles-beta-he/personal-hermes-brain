# From Lessons to Eval Rules — 实战案例

How to convert real project lessons into eval checks.

## Example 1: File Deletion Safety

**Memory lesson**: "删除文件前必须 grep 全项目残留引用 + 跑 pnpm build"

**Eval rule** (deterministic):
```python
def check_file_deletion_safety(deleted_file, project_root):
    import subprocess
    # Check for residual imports
    result = subprocess.run(
        ["grep", "-rn", f"from.*{deleted_file}", project_root],
        capture_output=True, text=True
    )
    return {
        "no_residual_imports": result.returncode != 0,
        "build_passes": subprocess.run(
            ["pnpm", "build"], cwd=project_root
        ).returncode == 0,
    }
```

**Prompt test case**: Delete a utility file and verify the skill greps for residual imports before and after.

## Example 2: Canvas Pixel Dimensions

**Memory lesson**: "canvas 元素必须显式设置 canvas.width/canvas.height 属性，CSS style 的 width/height 只是显示尺寸"

**Eval rule** (deterministic):
```python
def check_canvas_setup(js_content):
    import re
    has_canvas_width = bool(re.search(r'canvas\.width\s*=', js_content))
    has_canvas_height = bool(re.search(r'canvas\.height\s*=', js_content))
    return {
        "canvas_width_set": has_canvas_width,
        "canvas_height_set": has_canvas_height,
    }
```

**Prompt test case**: Create a canvas animation and verify canvas.width/height are set in code, not just CSS.

## Example 3: Responsive Breakpoints

**Memory lesson**: "px-8→px-4 sm:px-8，sm: 目标 2-3x md: 数量"

**Eval rule** (deterministic):
```python
def check_responsive_breakpoints(jsx_content):
    import re
    sm_count = len(re.findall(r'sm:', jsx_content))
    md_count = len(re.findall(r'md:', jsx_content))
    return {
        "sm_count": sm_count,
        "md_count": md_count,
        "sm_to_md_ratio": sm_count / max(md_count, 1),
        "mobile_first": sm_count >= md_count * 2,  # sm should be 2-3x md
    }
```

## Pattern: Lesson → Eval Rule

1. **Identify the lesson**: What specific behavior was wrong?
2. **Define the check**: What code/output proves the lesson was applied?
3. **Write deterministic check**: Can it be verified with grep/regex/file existence?
4. **If not deterministic**: Write as rubric check (LLM grades)
5. **Add to prompt test set**: Create a test case that triggers the scenario
