---
name: python-multiline-grep-engine
description: Build a Python-native multiline grep engine to replace shell `grep -rn`. 5-layer pipeline architecture with pluggable engines, git-aware incremental mode, parallel search, count mode, and context display. 52-test coverage.
tags:
  - grep
  - multiline
  - regex
  - python
  - pipeline
related_skills:
  - systematic-debugging
  - save-workflow-as-skill
triggers:
  - "需要跨行 grep"
  - "grep 不支持多行"
  - "替换 shell grep"
  - "multiline grep"
  - "跨行模式检测"
  - "Python 原生 grep"
  - "git-aware grep"
  - "code search engine"
  - "取代 grep -rn"
---

# Python Multiline Grep Engine (v2 — Pipeline Architecture)

## When to use

- You have a Python project that shells out to `grep -rn` and needs **cross-line matching**
- You want to **eliminate shell dependency** for grep operations (portability, error handling)
- You're adding a grep tool to an **agent tool registry** (like executor.py)
- You need a **scalable, testable** grep engine for a long-term project
- You need **git-aware incremental search** (only search changed files)

## Architecture: 5-Layer Pipeline

```
GrepConfig (单一 dataclass 贯穿全线)
    │
    ▼
FileDiscoverer
    ├── 全量 rglob（默认排除 node_modules/.venv/__pycache__ 等）
    └── git-aware（git diff --name-only + git ls-files --others）
    │
    ▼
PatternEngine (可插拔)
    ├── re (默认, Python stdlib)
    └── regex (PCRE2, 需 pip install regex)
    │   支线: line / multiline / count 三模式
    ▼
ResultAggregator
    ├── 全局 max_results 强制执行（非 per-file）
    ├── stats 统计（files_scanned / files_matched / files_skipped）
    └── parallel 支持（ThreadPoolExecutor）
    │
    ▼
OutputFormatter
    ├── format_results() — context +/- 前缀、多行展开
    ├── format_count() — 文件级匹配计数
    ├── format_stats() — 完整统计
    └── grep_json() — 程序化消费
```

## Implementation

### Step 1: GrepConfig — 单一配置

```python
@dataclass
class GrepConfig:
    pattern: str
    path: str = "."
    multiline: bool = False
    auto_detect: bool = True
    file_glob: Optional[str] = None
    exclude: list = field(default_factory=list)   # 自定义排除 glob
    git_aware: bool = False                       # 仅 git diff 文件
    max_results: int = 200
    context: int = 0
    count_mode: bool = False                      # 每文件仅 1 结果
    max_file_size: int = 10 * 1024 * 1024
    parallel: bool = False
    parallel_workers: int = 4
    pattern_engine: str = "re"                    # re | regex

    def __post_init__(self):
        if self.auto_detect and not self.multiline and '\\n' in self.pattern:
            self.multiline = True
```

### Step 2: FileDiscoverer — 全量 / git-aware 双支线

```python
# 默认排除目录 — 覆盖 node_modules/.venv/__pycache__/dist/build/target 等
_DEFAULT_EXCLUDE = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv',
    '.tox', '.eggs', 'dist', 'build', '.next', '.turbo',
    '.nyc_output', 'coverage', '.pytest_cache', '.mypy_cache',
    '.ruff_cache', '.cache', '.gitlab', '.svn', '.hg',
    '.idea', '.vscode', 'target', 'bin', 'obj',
}

def discover_files(config: GrepConfig) -> list:
    if config.git_aware:
        return _discover_git_files(base, exclude_set)

    # 全量 rglob + 排除
    for fpath in base.rglob(pattern):
        if not fpath.is_file():
            continue
        if any(part in exclude_set for part in fpath.parts):
            continue
        files.append(str(fpath))
    return sorted(files)

def _discover_git_files(base, exclude_set):
    """三路收集: staged + working + untracked。
    
    若没有任何 git 变更（干净 checkout），fallback 到全量扫描。
    """
    # git diff --name-only --cached (staged)
    # git diff --name-only (working)
    # git ls-files --others --exclude-standard (untracked)
```

### Step 3: PatternEngine — 可插拔

```python
class PatternEngine:
    def compile(self, pattern, multiline): ...
    def search(self, compiled, text): ...
    def finditer(self, compiled, text): ...

class ReEngine(PatternEngine):
    """Python re — 默认引擎。"""
    def compile(self, pattern, multiline):
        flags = re.DOTALL | re.MULTILINE if multiline else re.MULTILINE
        try:
            return re.compile(pattern, flags)
        except re.error:
            raise ValueError(f"Invalid regex pattern: {pattern}")

# regex 引擎（可选，需 pip install regex）
class RegexEngine(PatternEngine):
    """PCRE2 兼容 — lookbehind, possessive quantifiers, recursion。"""
    ...
```

### Step 4: _search_file — 三模式统一入口

```python
def _search_file(file_path, cfg, engine) -> list[GrepMatch]:
    """单个文件搜索。"""

def _search_file_line(file_path, cfg, engine):
    """逐行匹配。count mode: 找到第一条就返回。"""

def _search_file_multiline(file_path, cfg, engine):
    """跨行匹配 (re.DOTALL)。count mode: 仅检测有无。"""
```

### Step 5: run_pipeline — 全局 max_results 强制执行

```python
def run_pipeline(cfg) -> tuple[list[GrepMatch], GrepStats]:
    engine = _get_engine(cfg)
    files = discover_files(cfg)     # 发现 + 过滤合并

    for f in files:
        # 全局 max_results — 在 pipeline 层 enforce，非 per-file
        if not cfg.count_mode and len(all_results) >= cfg.max_results:
            break
        file_results = _search_file(f, cfg, engine)
        ...
```

### Step 6: OutputFormatter

```python
def format_results(results, max_chars=4000, show_context=True):
    """context 显示: - 前缀 before, + 前缀 after。"""

def format_count(results, stats):
    """文件级匹配数: path:count"""

def format_stats(stats, results):
    """完整统计。"""
```

### Step 7: 向后兼容 public API

```python
def multiline_grep(pattern, path=".", multiline=False, file_glob=None,
                   max_results=200, context=0, auto_detect=True,
                   git_aware=False, exclude=None, count_mode=False,
                   parallel=False, pattern_engine="re"):
    """与 v1 完全兼容的签名，内部用 pipeline 实现。"""
    cfg = GrepConfig(...)
    results, _ = run_pipeline(cfg)
    return results
```

### Step 8: 集成到工具注册

```python
# Schema — 新增 multiline 参数
{
    "name": "grep_search",
    "input_schema": {
        "properties": {
            "pattern": {"type": "string"},
            "multiline": {"type": "boolean",
                          "description": "Enable cross-line matching. Auto-detected if pattern contains \\n."},
        },
    },
}

# Handler — 完全替换 subprocess
def _tool_grep_search(inputs, cwd):
    import multiline_grep as _mg
    try:
        results = _mg.multiline_grep(
            pattern=inputs["pattern"],
            path=_resolve(inputs.get("directory", "."), cwd),
            multiline=inputs.get("multiline", False),
            file_glob=inputs.get("file_glob"),
        )
        return _mg.format_results(results)
    except ValueError as e:
        return f"ERROR: invalid regex pattern: {e}"
```

## Test Strategy (52 tests)

| Area | Tests | Covers |
|------|-------|--------|
| GrepConfig (4) | auto_detect switch/no-switch/override/disabled | Config layer |
| FileDiscovery (4) | all py, single file, custom exclude, default exclude dirs | Default excludes, git-aware |
| FileFilter (6) | empty, large, nonexistent, exclude glob, binary sniff, text ext | Skip logic |
| Line mode (7) | basic, no match, line numbers, empty file, max_results, single file, case | v1 compatibility |
| Multiline (5) | cross-line import, dotall, line number accuracy, multi-match, no match | v1 compatibility |
| Auto-detect (3) | switch, disabled, explicit override | Auto mode |
| Context (3) | captured, rendered in format, hidden when disabled | New feature |
| Count mode (2) | per-file return, format_count | New feature |
| Stats (1) | format_stats | New feature |
| Format (5) | empty, single, multiline, truncation, JSON | Output layer |
| Parallel (2) | same results, single file | New feature |
| Pipeline (2) | results+stats, count mode | Pipeline integration |
| Error (3) | invalid regex line/multiline, regex engine import | Error paths |
| Executor (5) | basic, no match, multiline, invalid regex, outside dir | Backward compat |

## Known Pitfalls

### 1. `re.error` is NOT `ValueError`

Python 3.14 raises `re.PatternError` (subclass of `re.error`, NOT of `ValueError`). Catch `re.error` internally, raise `ValueError` outward.

```python
except re.error:
    raise ValueError(f"Invalid regex pattern: {pattern}") from None
```

### 2. Global max_results must be enforced at pipeline level

Per-file early exit (`if len(results) >= max_results: return results`) only stops within a single file. The pipeline loop in `run_pipeline()` must also check:

```python
for f in files:
    if not cfg.count_mode and len(all_results) >= cfg.max_results:
        break
```

### 3. Count mode returns exactly 1 result per matched file

In count mode, `_search_file_line` returns a single empty `GrepMatch` as soon as the first match is found. Same for multiline mode with `compiled.search(content)` instead of `finditer`.

### 4. `from ... import ...` matches "import" grep pattern

If your test expects `grep("import")` to return N results, remember that `from pathlib import Path` also matches. Count accordingly.

### 5. Large file protection

Always add `_MAX_FILE_SIZE` guard. Without it, reading a 1GB log file into memory for multiline mode will OOM.

### 6. Binary file protection

Not all files with unknown extensions are text. The null-byte sniff (`b'\0'` in first 8KB) catches `.dat`, `.bin`, `.so`, `.dylib` without needing an exhaustive extension list.

### 7. Line number accuracy in multiline mode

When matching cross-line, `line_number` represents the **start** line of the match. Compute via `content[:m.start()].count('\n') + 1`.

### 8. git-aware fallback

If `git_aware=True` but the repo has no changes (clean checkout), fall back to full scan instead of returning empty results.

### 9. Exclude pattern matching

Use `Path(path).match(ex)` for glob-based exclude patterns. This supports patterns like `*.log`, `tests/fixtures`, `build/**/*`.

### 10. Binary sniff must precede extension check

In `_is_binary_file` (v2) / `_is_text_file` (v1), check extension first (fast path), then sniff. Reversed order would read files unnecessarily.
