#!/usr/bin/env python3
"""
code-intel.py — Hermes 原生代码智能引擎 v2 (支持 TypeScript/JavaScript)
轻量级替代 GitNexus: 不装 npm, 不用 tree-sitter, Python 标准库

支持语言: Python (.py), TypeScript (.ts/.tsx), JavaScript (.js/.jsx), Shell (.sh)
目标: gomoku-react (34K TS文件) 等已有项目的 1→N 维护

用法:
  python3 code-intel.py summary --repo /path/to/project
  python3 code-intel.py blast-radius --repo /path/to/project --file apps/web/src/board.tsx
  python3 code-intel.py import-graph --repo /path/to/project
  python3 code-intel.py call-chain --repo /path/to/project --function handleCellClick
"""

import argparse, os, re, sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

HERMES = Path.home() / ".hermes"
SCRIPTS = HERMES / "scripts"
SKILLS = HERMES / "skills"

# ═══════════════════════════════════════════
#  TS/JS 静态分析 (regex-based, 零依赖)
# ═══════════════════════════════════════════

def parse_ts_imports(filepath: Path) -> List[Tuple[str, str]]:
    """提取 TypeScript/JavaScript import: [(from_path, imported_name), ...]"""
    imports = []
    try:
        content = filepath.read_text()
    except:
        return imports
    # import { X } from 'path'
    for m in re.finditer(r"""import\s+(?:type\s+)?(?:\{[^}]+\}|[\w*]+)\s+from\s+['"]([^'"]+)['"]""", content):
        imports.append((m.group(1), "named"))
    # import 'path' (side-effect)
    for m in re.finditer(r"""import\s+['"]([^'"]+)['"]""", content):
        imports.append((m.group(1), "side-effect"))
    # import * as X from 'path'
    for m in re.finditer(r"""import\s+\*\s+as\s+(\w+)\s+from\s+['"]([^'"]+)['"]""", content):
        imports.append((m.group(2), f"*:{m.group(1)}"))
    # require('path')
    for m in re.finditer(r"""require\s*\(\s*['"]([^'"]+)['"]""", content):
        imports.append((m.group(1), "require"))
    return imports


def parse_ts_exports(filepath: Path) -> List[str]:
    """提取 TypeScript/JavaScript export 名称"""
    exports = []
    try:
        content = filepath.read_text()
    except:
        return exports
    for m in re.finditer(r"""export\s+(?:const|let|var|function|class|interface|type|enum|default)\s+(\w+)""", content):
        exports.append(m.group(1))
    # export { X, Y }
    for m in re.finditer(r"""export\s+\{([^}]+)\}""", content):
        names = re.findall(r"(\w+)", m.group(1))
        exports.extend(names)
    return exports


def parse_ts_functions(filepath: Path) -> List[str]:
    """提取函数/方法定义"""
    funcs = []
    try:
        content = filepath.read_text()
    except:
        return funcs
    for m in re.finditer(r"""(?:function|const)\s+(\w+)\s*[=(]""", content):
        funcs.append(m.group(1))
    for m in re.finditer(r"""(\w+)\s*\([^)]*\)\s*\{""", content):
        funcs.append(m.group(1))
    return funcs


def resolve_ts_path(import_path: str, from_file: Path) -> str:
    """解析 TS import 路径为实际文件"""
    if import_path.startswith("."):
        base = from_file.parent
        resolved = (base / import_path).resolve()
        for ext in [".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"]:
            p = Path(str(resolved) + ext)
            if p.exists():
                return str(p)
        # 去掉扩展名重试
        if resolved.exists() and resolved.is_dir():
            for ext in ["index.ts", "index.tsx", "index.js"]:
                p = resolved / ext
                if p.exists():
                    return str(p)
    return import_path


def find_ts_files(root: Path, max_files: int = 5000) -> List[Path]:
    """收集 TypeScript/JavaScript 文件"""
    files = []
    for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
        found = list(root.rglob(ext))
        # 排除 node_modules, dist, .git
        found = [f for f in found if "node_modules" not in str(f) 
                 and "dist" not in str(f) and ".git" not in str(f)]
        files.extend(found)
        if len(files) >= max_files:
            break
    return files[:max_files]


def ts_import_graph(repo_path: str, max_files: int = 3000) -> Tuple[Dict, Dict]:
    """构建 TypeScript import 依赖图"""
    root = Path(repo_path)
    files = find_ts_files(root, max_files)
    
    # 建立文件名 → 路径映射
    name_to_paths = defaultdict(list)
    for f in files:
        name_to_paths[f.name].append(str(f))
        name_to_paths[str(f.relative_to(root))].append(str(f))
    
    imports_of = defaultdict(set)      # file → what it imports
    imported_by = defaultdict(set)     # file → who imports it
    
    for f in files:
        rel = str(f.relative_to(root))
        for import_path, kind in parse_ts_imports(f):
            resolved = resolve_ts_path(import_path, f)
            # 标准化
            if resolved.startswith(str(root)):
                resolved = resolved[len(str(root)) + 1:]
            imports_of[rel].add(resolved)
            imported_by[resolved].add(rel)
    
    return dict(imports_of), dict(imported_by)


def ts_blast_radius(repo_path: str, target_file: str, max_files: int = 3000) -> dict:
    """TypeScript 影响范围分析"""
    imp_of, imp_by = ts_import_graph(repo_path, max_files)
    
    # 标准化 target
    target = target_file
    if target.startswith(str(Path(repo_path))):
        target = target[len(str(Path(repo_path))) + 1:]
    
    # 直接引用者
    direct = sorted(imp_by.get(target, set()))
    
    # 间接引用者 (depth 2)
    indirect = set()
    for d in direct:
        indirect.update(imp_by.get(d, set()))
    indirect = sorted(indirect - set(direct) - {target})
    
    return {
        "file": target,
        "directly_affected": direct,
        "indirectly_affected": indirect,
        "total_blast": len(direct) + len(indirect),
    }


def ts_call_chain(repo_path: str, function_name: str, max_files: int = 2000) -> list:
    """追踪函数调用链"""
    root = Path(repo_path)
    files = find_ts_files(root, max_files)
    
    callers = []
    for f in files:
        try:
            content = f.read_text()
        except:
            continue
        # 直接调用 function_name()
        if re.search(rf"\b{re.escape(function_name)}\s*\(", content):
            rel = str(f.relative_to(root))
            # 提取上下文
            for line in content.split("\n"):
                if function_name in line and "(" in line:
                    callers.append({"file": rel, "line": line.strip()[:120]})
                    break
    
    return callers[:30]


# ═══════════════════════════════════════════
#  Python 分析 (已有)
# ═══════════════════════════════════════════

def py_import_graph():
    """Python import 依赖图"""
    import ast
    files = sorted(SCRIPTS.glob("*.py"))
    graph = defaultdict(set)
    reverse = defaultdict(set)
    for f in files:
        try:
            tree = ast.parse(f.read_text())
        except:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    graph[f.name].add(("import", alias.name.split(".")[0]))
                    reverse[alias.name.split(".")[0]].add(f.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split(".")[0]
                    graph[f.name].add(("from", name))
                    reverse[name].add(f.name)
    return graph, reverse


# ═══════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════

def cli():
    parser = argparse.ArgumentParser(description="Code Intel v2 — TS/JS + Python 代码智能")
    sub = parser.add_subparsers(dest="cmd")

    ig = sub.add_parser("import-graph", help="import 依赖图 (Python=默认, TS=--repo)")
    ig.add_argument("--repo", default=None, help="TS/JS 项目路径")
    ig.add_argument("--max-files", type=int, default=3000)

    br = sub.add_parser("blast-radius", help="影响范围")
    br.add_argument("--repo", default=None, help="TS/JS 项目路径")
    br.add_argument("--file", required=True)
    br.add_argument("--max-files", type=int, default=3000)

    cc = sub.add_parser("call-chain", help="函数调用链 (TS only)")
    cc.add_argument("--repo", required=True)
    cc.add_argument("--function", required=True)
    cc.add_argument("--max-files", type=int, default=2000)

    sub.add_parser("summary", help="Hermes 自身代码健康摘要")

    args = parser.parse_args()

    if args.cmd == "import-graph":
        if args.repo:
            imp_of, imp_by = ts_import_graph(args.repo, args.max_files)
            print(f"TS Import Graph — {args.repo} ({len(imp_of)} files)")
            top = sorted(imp_by.items(), key=lambda x: len(x[1]), reverse=True)[:10]
            for file, importers in top:
                print(f"  {file:50s} ← {len(importers):3d} importers")
        else:
            graph, _ = py_import_graph()
            for script, imports in sorted(graph.items()):
                names = [n for _, n in imports]
                print(f"  {script:35s} → {', '.join(sorted(set(names))[:5])}")

    elif args.cmd == "blast-radius":
        if args.repo:
            result = ts_blast_radius(args.repo, args.file, args.max_files)
        else:
            # Python blast radius
            imp, _ = py_import_graph()
            base = args.file.replace(".py", "")
            affected = [s for s, imps in imp.items() if any(base in n for _, n in imps)]
            result = {
                "file": args.file,
                "directly_affected": sorted(affected),
                "indirectly_affected": [],
                "total_blast": len(affected),
            }
        print(f"Blast radius: {result['file']}")
        print(f"  Direct:  {len(result['directly_affected'])} files")
        if result.get("indirectly_affected"):
            print(f"  Indirect: {len(result['indirectly_affected'])} files")
        print(f"  Total:   {result['total_blast']} files")
        for f in result["directly_affected"][:15]:
            print(f"    - {f}")

    elif args.cmd == "call-chain":
        callers = ts_call_chain(args.repo, args.function, args.max_files)
        print(f"Call chain: {args.function}()")
        print(f"  Found in {len(callers)} files:")
        for c in callers:
            print(f"    {c['file']}")
            print(f"      → {c['line']}")

    elif args.cmd == "summary":
        import subprocess
        # 复用旧版 summary 逻辑
        r = subprocess.run([sys.executable, __file__.replace("v2", "").replace("-v2", ""), 
                           "import-graph"], capture_output=True, text=True)
        if r.returncode != 0:
            # fallback: 直接运行内联
            py_count = len(list(SCRIPTS.glob("*.py")))
            sh_count = len(list(SCRIPTS.glob("*.sh")))
            print(f"Hermes scripts: {py_count} .py + {sh_count} .sh")
            print("Use --repo for TS/JS project analysis")

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
