#!/usr/bin/env python3
"""brainctl.py — local-first Hermes/Obsidian evidence memory control plane.

Canonical truth source: ~/Documents/brain (or HERMES_BRAIN_VAULT).
Derived state: ~/.hermes/memory/index.sqlite and ~/.hermes/memory/wal.jsonl.

This script deliberately keeps Obsidian CLI optional. Filesystem + SQLite FTS5
must work even when Obsidian is not installed/running.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html as html_lib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - PyYAML is optional in fallback environments
    yaml = None
from pathlib import Path
from typing import Iterable, Iterator, Sequence

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
]

DEFAULT_IGNORES = [
    ".obsidian/**",
    ".git/**",
    "99-hermes-notes/.git/**",
]


@dataclass(frozen=True)
class Paths:
    vault: Path
    memory_home: Path
    index: Path
    wal: Path
    sync_script: Path


@dataclass(frozen=True)
class Block:
    rel_path: str
    heading: str
    line_start: int
    line_end: int
    text: str
    content_hash: str
    excerpt: str


def resolve_paths() -> Paths:
    home = Path.home()
    vault = Path(os.environ.get("HERMES_BRAIN_VAULT", str(home / "Documents" / "brain"))).expanduser()
    memory_home = Path(os.environ.get("HERMES_MEMORY_HOME", str(home / ".hermes" / "memory"))).expanduser()
    index = Path(os.environ.get("HERMES_BRAIN_INDEX", str(memory_home / "index.sqlite"))).expanduser()
    wal = Path(os.environ.get("HERMES_BRAIN_WAL", str(memory_home / "wal.jsonl"))).expanduser()
    sync_script = Path(os.environ.get("HERMES_SYNC_BRAIN_SCRIPT", str(home / ".hermes" / "scripts" / "sync-brain.py"))).expanduser()
    return Paths(vault=vault, memory_home=memory_home, index=index, wal=wal, sync_script=sync_script)


def obsidian_cli() -> str | None:
    return shutil.which("obsidian") or shutil.which("obsidian-cli")


def now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def has_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def sanitize_value(value):
    if isinstance(value, str):
        redacted = value
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    if isinstance(value, dict):
        return {str(k): sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value(v) for v in value]
    return value


def ensure_memory(paths: Paths) -> None:
    paths.memory_home.mkdir(parents=True, exist_ok=True)
    paths.index.parent.mkdir(parents=True, exist_ok=True)
    paths.wal.parent.mkdir(parents=True, exist_ok=True)


def append_wal(op: str, details: dict | None = None, *, paths: Paths | None = None) -> dict:
    paths = paths or resolve_paths()
    ensure_memory(paths)
    safe_details = sanitize_value(details or {})
    entry = {"ts": now_ts(), "op": op, "details": safe_details}
    with paths.wal.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return entry


def read_ignore_patterns(vault: Path) -> list[str]:
    patterns = list(DEFAULT_IGNORES)
    ignore_file = vault / ".brainignore"
    if ignore_file.exists():
        for raw in ignore_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
    return patterns


def ignored(rel_path: str, patterns: Sequence[str]) -> bool:
    rel = rel_path.replace(os.sep, "/")
    for pattern in patterns:
        pat = pattern.strip().replace(os.sep, "/")
        if not pat:
            continue
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch("/" + rel, pat):
            return True
        if pat.endswith("/**") and rel.startswith(pat[:-3].rstrip("/") + "/"):
            return True
    return False


def iter_markdown_files(vault: Path, patterns: Sequence[str]) -> Iterator[Path]:
    if not vault.exists():
        return
    for path in sorted(vault.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(vault).as_posix()
        except ValueError:
            continue
        if ignored(rel, patterns):
            continue
        yield path


def heading_text(line: str) -> str | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None
    return match.group(2).strip()


def make_excerpt(text: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def blocks_from_file(path: Path, vault: Path) -> tuple[list[Block], int]:
    rel = path.relative_to(vault).as_posix()
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    current_heading = path.stem
    start_line = 1
    buf: list[str] = []
    blocks: list[Block] = []
    skipped_secret = 0

    def flush(end_line: int) -> None:
        nonlocal buf, start_line, skipped_secret
        text = "\n".join(buf).strip()
        if not text:
            buf = []
            return
        if has_secret(text):
            skipped_secret += 1
            buf = []
            return
        digest = sha256_text(f"{rel}\n{current_heading}\n{start_line}\n{end_line}\n{text}")
        blocks.append(
            Block(
                rel_path=rel,
                heading=current_heading,
                line_start=start_line,
                line_end=max(start_line, end_line),
                text=text,
                content_hash=digest,
                excerpt=make_excerpt(text),
            )
        )
        buf = []

    for idx, line in enumerate(lines, start=1):
        h = heading_text(line)
        if h is not None:
            flush(idx - 1)
            current_heading = h
            start_line = idx
            buf = [line]
        else:
            if not buf:
                start_line = idx
            buf.append(line)
    flush(len(lines))
    return blocks, skipped_secret


def connect_index(paths: Paths | None = None) -> sqlite3.Connection:
    paths = paths or resolve_paths()
    ensure_memory(paths)
    con = sqlite3.connect(paths.index)
    con.row_factory = sqlite3.Row
    return con


def init_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table if not exists blocks (
          id integer primary key,
          path text not null,
          heading text not null,
          line_start integer not null,
          line_end integer not null,
          content_hash text not null unique,
          excerpt text not null,
          body text not null,
          mtime real not null
        );
        create virtual table if not exists blocks_fts using fts5(
          path unindexed,
          heading,
          body,
          content='blocks',
          content_rowid='id'
        );
        create table if not exists metadata (
          key text primary key,
          value text not null
        );
        """
    )
    con.commit()


def reset_index(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        drop table if exists blocks_fts;
        drop table if exists blocks;
        drop table if exists metadata;
        """
    )
    con.commit()
    init_schema(con)


def reindex(*, json_mode: bool = False) -> dict:
    paths = resolve_paths()
    ensure_memory(paths)
    patterns = read_ignore_patterns(paths.vault)
    con = connect_index(paths)
    indexed = 0
    skipped_secret = 0
    skipped_ignored = 0
    try:
        reset_index(con)
        for md in iter_markdown_files(paths.vault, patterns):
            rel = md.relative_to(paths.vault).as_posix()
            if ignored(rel, patterns):
                skipped_ignored += 1
                continue
            blocks, skipped = blocks_from_file(md, paths.vault)
            skipped_secret += skipped
            mtime = md.stat().st_mtime
            for block in blocks:
                cur = con.execute(
                    """
                    insert into blocks(path, heading, line_start, line_end, content_hash, excerpt, body, mtime)
                    values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        block.rel_path,
                        block.heading,
                        block.line_start,
                        block.line_end,
                        block.content_hash,
                        block.excerpt,
                        block.text,
                        mtime,
                    ),
                )
                rowid = cur.lastrowid
                con.execute(
                    "insert into blocks_fts(rowid, path, heading, body) values (?, ?, ?, ?)",
                    (rowid, block.rel_path, block.heading, block.text),
                )
                indexed += 1
        con.execute("insert or replace into metadata(key, value) values('indexed_at', ?)", (now_ts(),))
        con.execute("insert or replace into metadata(key, value) values('vault', ?)", (str(paths.vault),))
        con.commit()
    finally:
        con.close()
    result = {
        "vault": str(paths.vault),
        "index": str(paths.index),
        "indexed_blocks": indexed,
        "skipped_secret_blocks": skipped_secret,
        "skipped_ignored_files": skipped_ignored,
    }
    append_wal(
        "reindex",
        {
            "vault": str(paths.vault),
            "indexed_blocks": indexed,
            "skipped_secret_blocks": skipped_secret,
            "skipped_ignored_files": skipped_ignored,
        },
        paths=paths,
    )
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def fts_query(query: str) -> str:
    # Keep FTS syntax conservative. Quote every token so punctuation-heavy
    # queries (for example secrets containing '-') cannot be parsed as column
    # filters or operators by FTS5.
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", query, flags=re.UNICODE)
    if not tokens:
        return '""'
    return " ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def search(query: str, *, limit: int = 10, json_mode: bool = False) -> list[dict]:
    paths = resolve_paths()
    if not paths.index.exists():
        reindex(json_mode=True)
    con = connect_index(paths)
    results: list[dict] = []
    try:
        init_schema(con)
        rows = con.execute(
            """
            select b.path, b.heading, b.line_start, b.line_end, b.content_hash, b.excerpt,
                   bm25(blocks_fts) as rank
            from blocks_fts
            join blocks b on b.id = blocks_fts.rowid
            where blocks_fts match ?
            order by rank
            limit ?
            """,
            (fts_query(query), limit),
        ).fetchall()
        for row in rows:
            results.append(
                {
                    "path": row["path"],
                    "heading": row["heading"],
                    "line_start": int(row["line_start"]),
                    "line_end": int(row["line_end"]),
                    "content_hash": row["content_hash"],
                    "excerpt": row["excerpt"],
                    "score": float(-row["rank"]),
                }
            )
    finally:
        con.close()
    append_wal(
        "search",
        {"query_hash": sha256_text(query), "limit": limit, "result_count": len(results), "query_redacted": has_secret(query)},
        paths=paths,
    )
    if not json_mode:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return results


def evidence(query: str, *, limit: int = 10, json_mode: bool = False) -> list[dict]:
    return search(query, limit=limit, json_mode=json_mode)


def wal_tail(*, limit: int = 20, json_mode: bool = False) -> list[dict]:
    paths = resolve_paths()
    if not paths.wal.exists():
        entries: list[dict] = []
    else:
        lines = paths.wal.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        entries = []
        for line in lines:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append({"malformed": True, "line_hash": sha256_text(line)})
    if not json_mode:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
    return entries


def status(*, json_mode: bool = False) -> dict:
    paths = resolve_paths()
    cli = obsidian_cli()
    indexed_at = None
    block_count = 0
    if paths.index.exists():
        try:
            con = connect_index(paths)
            init_schema(con)
            row = con.execute("select value from metadata where key='indexed_at'").fetchone()
            indexed_at = row[0] if row else None
            block_count = con.execute("select count(*) from blocks").fetchone()[0]
            con.close()
        except sqlite3.Error:
            indexed_at = None
    data = {
        "vault": str(paths.vault),
        "vault_exists": paths.vault.exists(),
        "legacy_vault": str(Path.home() / "Documents" / "Obsidian Vault"),
        "index": str(paths.index),
        "index_exists": paths.index.exists(),
        "indexed_at": indexed_at,
        "indexed_blocks": block_count,
        "wal": str(paths.wal),
        "wal_exists": paths.wal.exists(),
        "sync_script": str(paths.sync_script),
        "sync_script_exists": paths.sync_script.exists(),
        "obsidian_cli": cli,
        "obsidian_cli_available": bool(cli),
        "mode": "obsidian_cli_available" if cli else "filesystem_fallback",
    }
    if not json_mode:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def sync(*, json_mode: bool = False) -> dict:
    paths = resolve_paths()
    if not paths.sync_script.exists():
        result = {"exit_code": 127, "stdout": "", "stderr": f"sync script not found: {paths.sync_script}"}
    else:
        proc = subprocess.run(
            [sys.executable, str(paths.sync_script)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        result = {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    append_wal("sync", {"exit_code": result["exit_code"], "stdout_hash": sha256_text(result["stdout"]), "stderr_hash": sha256_text(result["stderr"])}, paths=paths)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def open_note(path: str, *, json_mode: bool = False, launch: bool = False) -> dict:
    paths = resolve_paths()
    rel = Path(path).as_posix().lstrip("/")
    target = paths.vault / rel
    uri = f"obsidian://open?path={target.as_posix()}"
    cli = obsidian_cli()
    launched = False
    if launch:
        if cli:
            subprocess.run([cli, "open", str(target)], check=False)
            launched = True
        else:
            webbrowser.open(uri)
            launched = True
    result = {"path": str(target), "uri": uri, "obsidian_cli_available": bool(cli), "launched": launched}
    append_wal("open", {"path": rel, "launched": launched}, paths=paths)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].splitlines()
    meta: dict[str, str] = {}
    for line in raw:
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"\'')
    return meta, text[end + len("\n---"):].lstrip("\n")


def iter_notes_with_meta(paths: Paths | None = None) -> Iterator[dict]:
    paths = paths or resolve_paths()
    patterns = read_ignore_patterns(paths.vault)
    for md in iter_markdown_files(paths.vault, patterns):
        rel = md.relative_to(paths.vault).as_posix()
        text = md.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(text)
        yield {"path": md, "rel_path": rel, "meta": meta, "body": body, "text": text}


def parse_iso_epoch(value: str | None) -> float | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return time.mktime(time.strptime(raw[:19] if fmt.endswith("S") else raw[:10], fmt.replace("%z", "")))
        except (ValueError, TypeError):
            continue
    return None


def is_terminal_status(status_value: str | None) -> bool:
    return (status_value or "").strip().lower() in {"completed", "done", "cancelled", "canceled", "archived", "expired", "closed"}


def is_l3(note: dict) -> bool:
    meta = note["meta"]
    rel = note["rel_path"]
    name = Path(rel).name
    note_type = str(meta.get("type", "")).lower()
    derived_flag = str(meta.get("derived", "")).lower() in {"true", "yes", "1"}
    non_task_views = {
        "task_inbox",
        "derived_task_pool",
        "dashboard",
        "moc",
        "proof",
        "review",
        "evolution_log",
    }
    if derived_flag or note_type in non_task_views or note_type.startswith("derived_"):
        return meta.get("layer", "").upper() == "L3"
    if name.startswith("00-") or name.endswith(".json.md"):
        return meta.get("layer", "").upper() == "L3"
    return meta.get("layer", "").upper() == "L3" or "/tasks/" in f"/{rel}"


def has_evidence_boundary(text: str) -> bool:
    low = text.lower()
    return "evidence boundary" in low or "证据边界" in text


def has_closure_or_validation(text: str) -> bool:
    low = text.lower()
    return any(term in low for term in ["closure links", "validation queries", "tool output", "command output", "proof"])


def l3_expiry_items(paths: Paths | None = None) -> list[dict]:
    now = time.time()
    items: list[dict] = []
    for note in iter_notes_with_meta(paths):
        if not is_l3(note):
            continue
        meta = note["meta"]
        if is_terminal_status(meta.get("status")):
            continue
        expiry = meta.get("expires_at") or meta.get("expiry") or meta.get("valid_to")
        expiry_epoch = parse_iso_epoch(expiry)
        if not expiry:
            items.append({"path": note["rel_path"], "status": "missing_expiry", "expires_at": None})
        elif expiry_epoch is not None and expiry_epoch < now:
            items.append({"path": note["rel_path"], "status": "expired", "expires_at": expiry})
    return items


def governance_violations(paths: Paths | None = None) -> tuple[list[dict], dict]:
    notes = list(iter_notes_with_meta(paths))
    violations: list[dict] = []
    for note in notes:
        meta = note["meta"]
        rel = note["rel_path"]
        if note["text"].startswith("---\n"):
            for key in ("type", "status"):
                if key not in meta:
                    violations.append({"type": "frontmatter_missing_key", "path": rel, "key": key})
        if is_l3(note) and not is_terminal_status(meta.get("status")):
            expiry = meta.get("expires_at") or meta.get("expiry") or meta.get("valid_to")
            if not expiry:
                violations.append({"type": "missing_l3_expiry", "path": rel})
        is_review = meta.get("type", "").lower() == "review" or meta.get("layer", "").upper() == "L6" or "/reviews/" in f"/{rel}"
        if is_review and not has_evidence_boundary(note["text"]):
            violations.append({"type": "review_missing_evidence_boundary", "path": rel})
    summary = {"notes_scanned": len(notes), "l3_expiry_open": len(l3_expiry_items(paths))}
    return violations, summary


def write_governance_dashboard(result: dict, paths: Paths | None = None) -> Path:
    paths = paths or resolve_paths()
    target = paths.vault / "07-仪表盘" / "本地大脑治理健康度.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    violations = result.get("violations", [])
    by_type: dict[str, int] = {}
    for violation in violations:
        by_type[violation.get("type", "unknown")] = by_type.get(violation.get("type", "unknown"), 0) + 1
    lines = [
        "---",
        "type: dashboard",
        "layer: L5",
        f"status: {'current' if result.get('passed') else 'attention'}",
        f"updated: {now_ts()}",
        "source: brainctl validate --write-dashboard",
        "---",
        "",
        "# 本地大脑治理健康度",
        "",
        "## current snapshot",
        "",
        f"- generated_at: `{result.get('generated_at')}`",
        f"- validate_passed: `{result.get('passed')}`",
        f"- notes_scanned: `{result.get('summary', {}).get('notes_scanned', 0)}`",
        f"- l3_expiry_open: `{result.get('summary', {}).get('l3_expiry_open', 0)}`",
        f"- violation_count: `{len(violations)}`",
        "",
        "## open actions",
        "",
    ]
    if by_type:
        lines.extend(f"- {k}: {v}" for k, v in sorted(by_type.items()))
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## historical snapshot",
        "",
        "- Previous manual dashboard content is superseded by this generated current snapshot; historical reviews remain under `06-治理与评审/reviews/`.",
        "",
        "## accepted risks",
        "",
        "- Derived indexes remain rebuildable caches; Markdown vault remains canonical truth.",
        "- Multi-model agreement remains provenance until evidence requests are satisfied.",
        "",
        "## validation queries",
        "",
        "- 本地大脑治理健康度 structural stop gate ghost prevention",
        "- brainctl validate expire promote review record",
        "",
    ])
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target


def validate(*, dry_run: bool = True, write_dashboard: bool = False, json_mode: bool = False) -> dict:
    paths = resolve_paths()
    violations, summary = governance_violations(paths)
    result = {
        "schema": "local_brain_validate_v1",
        "generated_at": now_ts(),
        "vault": str(paths.vault),
        "dry_run": dry_run,
        "passed": not violations,
        "summary": summary,
        "violations": violations,
        "dashboard_written": None,
    }
    if write_dashboard:
        result["dashboard_written"] = str(write_governance_dashboard(result, paths))
    append_wal("validate", {"passed": result["passed"], "violation_count": len(violations), "dashboard_written": bool(write_dashboard)}, paths=paths)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def expire(*, dry_run: bool = True, json_mode: bool = False) -> dict:
    paths = resolve_paths()
    items = l3_expiry_items(paths)
    result = {"schema": "local_brain_expire_v1", "generated_at": now_ts(), "vault": str(paths.vault), "dry_run": dry_run, "items": items}
    append_wal("expire", {"dry_run": dry_run, "item_count": len(items)}, paths=paths)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def promote(*, dry_run: bool = True, json_mode: bool = False) -> dict:
    paths = resolve_paths()
    candidates: list[dict] = []
    rejected: list[dict] = []
    for note in iter_notes_with_meta(paths):
        meta = note["meta"]
        status_value = (meta.get("status") or "").lower()
        if status_value not in {"completed", "done", "closed"}:
            continue
        if not (is_l3(note) or meta.get("layer", "").upper() == "L6"):
            continue
        record = {"path": note["rel_path"], "type": meta.get("type"), "layer": meta.get("layer")}
        if has_evidence_boundary(note["text"]) and has_closure_or_validation(note["text"]):
            candidates.append({**record, "reason": "evidence_backed_terminal_artifact"})
        else:
            rejected.append({**record, "reason": "insufficient_evidence_boundary_or_closure"})
    result = {"schema": "local_brain_promote_v1", "generated_at": now_ts(), "vault": str(paths.vault), "dry_run": dry_run, "candidates": candidates, "rejected": rejected}
    append_wal("promote", {"dry_run": dry_run, "candidate_count": len(candidates), "rejected_count": len(rejected)}, paths=paths)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def html_manifest_path(paths: Paths | None = None) -> Path:
    paths = paths or resolve_paths()
    return paths.memory_home / "html_sidecars.json"


def load_html_manifest(paths: Paths | None = None) -> dict:
    path = html_manifest_path(paths)
    if not path.exists():
        return {"schema": "local_brain_html_manifest_v1", "items": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema": "local_brain_html_manifest_v1", "items": {}}
    if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
        return {"schema": "local_brain_html_manifest_v1", "items": {}}
    return data


def save_html_manifest(manifest: dict, paths: Paths | None = None) -> None:
    paths = paths or resolve_paths()
    ensure_memory(paths)
    target = html_manifest_path(paths)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_md_rel(value: str, vault: Path) -> str:
    raw = value.strip().replace("\\", "/")
    if raw.startswith(str(vault)):
        raw = str(Path(raw).relative_to(vault)).replace("\\", "/")
    if raw.startswith("/"):
        raw = raw.lstrip("/")
    if not raw.endswith(".md"):
        raw += ".md"
    return raw


def resolve_wikilink(target: str, vault: Path) -> str | None:
    clean = target.split("|", 1)[0].split("#", 1)[0].strip()
    if not clean:
        return None
    rel = normalize_md_rel(clean, vault)
    if (vault / rel).exists():
        return rel
    name = Path(rel).name
    matches = [p.relative_to(vault).as_posix() for p in vault.rglob(name) if p.is_file()]
    return sorted(matches)[0] if matches else rel


def html_sidecar_for_md(md_path: Path) -> Path:
    return md_path.with_suffix(".html")


def rel_href(from_html: Path, target: Path) -> str:
    return os.path.relpath(target, from_html.parent).replace(os.sep, "/")


def extract_html_dependencies(text: str, vault: Path) -> list[str]:
    deps: set[str] = set()
    for match in re.finditer(r"\[\[([^\]]+)\]\]", text):
        rel = resolve_wikilink(match.group(1), vault)
        if rel:
            deps.add(rel)
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        url = match.group(1).strip()
        if re.match(r"^[a-z]+://", url) or url.startswith("#"):
            continue
        if url.endswith(".md") or not Path(url).suffix:
            deps.add(normalize_md_rel(url, vault))
    return sorted(deps)


def render_inline_html(text: str, source_html: Path, vault: Path) -> str:
    def md_link(match: re.Match) -> str:
        label = html_lib.escape(match.group(1))
        url = match.group(2).strip()
        if re.match(r"^[a-z]+://", url):
            href = html_lib.escape(url, quote=True)
            extra = ' target="_blank" rel="noopener noreferrer"'
        else:
            url_path = url.split("#", 1)[0].split("?", 1)[0]
            if Path(url_path).suffix.lower() in {".html", ".htm"}:
                target = (source_html.parent / url).resolve() if not url.startswith("/") else vault / url.lstrip("/")
                href = html_lib.escape(rel_href(source_html, target), quote=True)
            else:
                href = html_lib.escape(rel_href(source_html, vault / normalize_md_rel(url, vault)), quote=True)
            extra = ""
        return f'<a href="{href}"{extra}>{label}</a>'

    def wiki_link(match: re.Match) -> str:
        raw = match.group(1)
        target, _, label = raw.partition("|")
        label_text = label or Path(target.split("#", 1)[0]).name
        rel = resolve_wikilink(target, vault) or normalize_md_rel(target, vault)
        href = html_lib.escape(rel_href(source_html, vault / rel), quote=True)
        return f'<a href="{href}">{html_lib.escape(label_text)}</a>'

    escaped = html_lib.escape(text)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", md_link, escaped)
    escaped = re.sub(r"\[\[([^\]]+)\]\]", wiki_link, escaped)
    return escaped


def render_markdown_html(text: str, source_rel: str, vault: Path) -> str:
    source_md = vault / source_rel
    source_html = html_sidecar_for_md(source_md)
    body: list[str] = []
    in_code = False
    code_buf: list[str] = []
    for raw in text.splitlines():
        if raw.startswith("```"):
            if in_code:
                body.append("<pre><code>" + html_lib.escape("\n".join(code_buf)) + "</code></pre>")
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(raw)
            continue
        if not raw.strip():
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", raw)
        if heading:
            level = len(heading.group(1))
            body.append(f"<h{level}>" + render_inline_html(heading.group(2), source_html, vault) + f"</h{level}>")
        elif raw.lstrip().startswith("- "):
            body.append("<ul><li>" + render_inline_html(raw.lstrip()[2:], source_html, vault) + "</li></ul>")
        else:
            body.append("<p>" + render_inline_html(raw, source_html, vault) + "</p>")
    if in_code:
        body.append("<pre><code>" + html_lib.escape("\n".join(code_buf)) + "</code></pre>")
    source_href = html_lib.escape(rel_href(source_html, source_md), quote=True)
    graph_href = html_lib.escape(rel_href(source_html, vault / "07-仪表盘" / "本地大脑图形导航.html"), quote=True)
    title = html_lib.escape(Path(source_rel).stem)
    return "\n".join([
        "<!doctype html>",
        '<html lang="zh-CN">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>{title}</title>",
        "  <style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;max-width:980px;margin:32px auto;padding:0 20px;line-height:1.65}a{color:#0b66c3}pre{background:#111;color:#eee;padding:12px;overflow:auto}.source{border:1px solid #ddd;padding:12px;border-radius:10px;background:#fafafa}</style>",
        "</head>",
        f'<body data-canonical-source="{html_lib.escape(source_rel, quote=True)}">',
        f'<nav class="source">Canonical source: <a href="{source_href}">{html_lib.escape(source_rel)}</a><br>Graph navigation: <a href="{graph_href}">本地大脑图形导航</a><br>Generated: {now_ts()}</nav>',
        *body,
        "</body>",
        "</html>",
        "",
    ])


def html_target_paths(requested: list[str] | None, paths: Paths | None = None) -> list[Path]:
    paths = paths or resolve_paths()
    if requested:
        return [paths.vault / normalize_md_rel(item, paths.vault) for item in requested]
    patterns = read_ignore_patterns(paths.vault)
    candidates = []
    for md in iter_markdown_files(paths.vault, patterns):
        rel = md.relative_to(paths.vault).as_posix()
        if rel in {"07-仪表盘/本地大脑HTML入口.md", "07-仪表盘/本地大脑HTML跳转测试.md"}:
            continue
        if rel.startswith(("07-仪表盘/", "06-治理与评审/reviews/", "05-实践与项目/projects/")):
            candidates.append(md)
    return candidates


def html_build(paths: list[str] | None = None, *, json_mode: bool = False) -> dict:
    resolved = resolve_paths()
    manifest = load_html_manifest(resolved)
    written: list[dict] = []
    for md in html_target_paths(paths, resolved):
        if not md.exists() or md.suffix != ".md":
            continue
        rel = md.relative_to(resolved.vault).as_posix()
        text = md.read_text(encoding="utf-8", errors="replace")
        deps = extract_html_dependencies(text, resolved.vault)
        html_path = html_sidecar_for_md(md)
        html_path.write_text(render_markdown_html(text, rel, resolved.vault), encoding="utf-8")
        dep_hashes = {dep: sha256_text((resolved.vault / dep).read_text(encoding="utf-8", errors="replace")) for dep in deps if (resolved.vault / dep).exists()}
        manifest["items"][rel] = {
            "source": rel,
            "sidecar": html_path.relative_to(resolved.vault).as_posix(),
            "generated_at": now_ts(),
            "source_hash": sha256_text(text),
            "dependencies": dep_hashes,
        }
        written.append({"source": rel, "sidecar": manifest["items"][rel]["sidecar"]})
    save_html_manifest(manifest, resolved)
    result = {"schema": "local_brain_html_build_v1", "written_count": len(written), "written": written}
    append_wal("html_build", {"written_count": len(written)}, paths=resolved)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def classify_html_status(source_rel: str, paths: Paths, manifest: dict) -> dict:
    md = paths.vault / source_rel
    html_path = html_sidecar_for_md(md)
    item = manifest.get("items", {}).get(source_rel)
    if not md.exists():
        return {"source": source_rel, "status": "missing_source"}
    if not html_path.exists() or not item:
        return {"source": source_rel, "sidecar": html_path.relative_to(paths.vault).as_posix(), "status": "missing"}
    text = md.read_text(encoding="utf-8", errors="replace")
    if sha256_text(text) != item.get("source_hash"):
        return {"source": source_rel, "sidecar": item.get("sidecar"), "status": "stale_source"}
    for dep, old_hash in item.get("dependencies", {}).items():
        dep_path = paths.vault / dep
        new_hash = sha256_text(dep_path.read_text(encoding="utf-8", errors="replace")) if dep_path.exists() else None
        if new_hash != old_hash:
            return {"source": source_rel, "sidecar": item.get("sidecar"), "status": "stale_dependency", "dependency": dep}
    return {"source": source_rel, "sidecar": item.get("sidecar"), "status": "fresh"}


def html_status(paths: list[str] | None = None, *, json_mode: bool = False) -> dict:
    resolved = resolve_paths()
    manifest = load_html_manifest(resolved)
    sources = [p.relative_to(resolved.vault).as_posix() for p in html_target_paths(paths, resolved)]
    result = {"schema": "local_brain_html_status_v1", "items": [classify_html_status(src, resolved, manifest) for src in sources]}
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def html_refresh(paths: list[str] | None = None, *, json_mode: bool = False) -> dict:
    status = html_status(paths=paths, json_mode=True)
    stale = [item["source"] for item in status["items"] if item.get("status") != "fresh" and item.get("status") != "missing_source"]
    if not stale:
        return {"schema": "local_brain_html_build_v1", "written_count": 0, "written": []}
    return html_build(paths=stale, json_mode=json_mode)


def html_watch(paths: list[str] | None = None, *, interval: float = 5.0, once: bool = False, json_mode: bool = False) -> dict:
    """Poll canonical sources and refresh stale HTML sidecars.

    `once=True` is a deterministic hook/test mode. Without `once`, this is a
    foreground watcher suitable for launchd/supervisor/manual terminals.
    """
    last: dict | None = None
    while True:
        last = html_refresh(paths=paths, json_mode=True)
        html_graph(json_mode=True)
        if not json_mode and last.get("written_count"):
            print(json.dumps(last, ensure_ascii=False, indent=2))
        if once:
            if not json_mode:
                print(json.dumps(last, ensure_ascii=False, indent=2))
            return {"schema": "local_brain_html_watch_v1", "mode": "once", "refresh": last}
        time.sleep(max(0.5, float(interval)))


def html_graph_path(paths: Paths | None = None) -> Path:
    paths = paths or resolve_paths()
    return paths.vault / "07-仪表盘" / "本地大脑图形导航.html"


def html_launcher_path(paths: Paths | None = None) -> Path:
    paths = paths or resolve_paths()
    return paths.vault / "07-仪表盘" / "本地大脑HTML入口.md"


def html_jump_test_path(paths: Paths | None = None) -> Path:
    paths = paths or resolve_paths()
    return paths.vault / "07-仪表盘" / "本地大脑HTML跳转测试.md"


def html_app_path(paths: Paths | None = None) -> Path:
    paths = paths or resolve_paths()
    return paths.vault / "07-仪表盘" / "local-brain-app" / "index.html"


def group_samples(model: dict) -> dict[str, dict]:
    samples: dict[str, dict] = {}
    preferred = ["dashboards", "projects", "reviews", "other"]
    for group in preferred:
        for node in model.get("nodes", []):
            if node.get("group") == group:
                samples[group] = node
                break
    return samples


def file_uri_for_sidecar(paths: Paths, sidecar_rel: str) -> str:
    return (paths.vault / sidecar_rel).resolve().as_uri()


def render_html_jump_test(graph_path: Path, paths: Paths, model: dict) -> str:
    graph_uri = graph_path.resolve().as_uri()
    app_path = html_app_path(paths)
    app_uri = app_path.resolve().as_uri()
    samples = group_samples(model)
    labels = {"dashboards": "仪表盘样例", "projects": "项目样例", "reviews": "治理评审样例", "other": "其他样例"}
    lines = [
        "---",
        "type: generated-test",
        "layer: L7",
        "generated: true",
        "source: brainctl html graph",
        "---",
        "",
        "# 本地大脑 HTML 跳转测试",
        "",
        "> 用于在 Obsidian 中人工抽样验证 HTML sidecar 跳转。此文件自动生成，不承载 canonical 状态。",
        "",
        "## 核心入口",
        "",
        f"- [React HTML App]({app_uri})",
        f"- [兼容图形导航入口]({graph_uri})",
        "- [[07-仪表盘/本地大脑HTML入口]]",
        "",
        "## 分层样例",
        "",
    ]
    for group, title in labels.items():
        node = samples.get(group)
        if not node:
            continue
        sidecar = node["sidecar"]
        lines.append(f"- {title}: [{sidecar}]({file_uri_for_sidecar(paths, sidecar)})")
    lines.extend([
        "",
        "## 验收步骤",
        "",
        "1. 在 Obsidian 打开本文件。",
        "2. 点击 React HTML App，确认浏览器打开新 Cockpit / Mission Control。",
        "3. 点击兼容图形导航入口，确认旧入口会自动跳到 React App。",
        "4. 点击分层样例，确认可以跳到对应 sidecar。",
        "5. 回到 `本地大脑HTML入口`，确认入口不承载业务状态。",
        "",
    ])
    return "\n".join(lines)


def render_html_launcher(graph_path: Path, paths: Paths, model: dict) -> str:
    graph_rel = graph_path.relative_to(paths.vault).as_posix()
    graph_uri = graph_path.resolve().as_uri()
    jump_path = html_jump_test_path(paths)
    jump_rel = jump_path.relative_to(paths.vault).as_posix()
    jump_uri = jump_path.resolve().as_uri()
    app_path = html_app_path(paths)
    app_rel = app_path.relative_to(paths.vault).as_posix()
    app_uri = app_path.resolve().as_uri()
    return "\n".join([
        "---",
        "type: generated-index",
        "layer: L7",
        "generated: true",
        "source: brainctl html graph",
        "primary_html_entry: 07-仪表盘/local-brain-app/index.html",
        "legacy_graph_entry: 07-仪表盘/本地大脑图形导航.html",
        "---",
        "",
        "# 本地大脑 HTML 入口",
        "",
        "> Obsidian 可见入口。此文件由 `brainctl html graph` 自动生成；React App 是当前主入口，HTML 是派生展示层，Markdown/JSON/kanban.db 仍为 canonical source。",
        "",
        f"- 主入口 React HTML App：[{app_rel}]({app_uri})",
        f"- 兼容入口/自动跳转页：[{graph_rel}]({graph_uri})",
        f"- 跳转测试文件：[{jump_rel}]({jump_uri})",
        f"- HTML 入口数：{len(model['nodes'])}",
        f"- 内部跳转数：{len(model['edges'])}",
        "",
        "## 常用入口",
        "",
        f"- [React HTML App]({app_uri})",
        f"- [兼容图形导航入口]({graph_uri})",
        "- [[07-仪表盘/00-仪表盘索引]]",
        "- [[07-仪表盘/待完成任务控制台]]",
        "- [[07-仪表盘/待完成任务运行态]]",
        "",
    ])


def classify_html_node(source_rel: str) -> tuple[str, str, str]:
    if source_rel.startswith("07-仪表盘/"):
        return "dashboards", "仪表盘", "#22d3ee"
    if source_rel.startswith("05-实践与项目/projects/"):
        return "projects", "项目", "#34d399"
    if source_rel.startswith("06-治理与评审/reviews/"):
        return "reviews", "治理评审", "#a78bfa"
    return "other", "其他", "#94a3b8"


def node_label(source_rel: str) -> str:
    stem = Path(source_rel).stem
    for prefix in ("Project - ", "P10 - ", "P9 - "):
        if stem.startswith(prefix):
            stem = stem[len(prefix):]
    return stem[:34] + ("…" if len(stem) > 34 else "")


def build_html_graph_model(manifest: dict) -> dict:
    items = manifest.get("items", {})
    nodes: list[dict] = []
    edges: list[dict] = []
    for source_rel, item in sorted(items.items()):
        group, group_label, color = classify_html_node(source_rel)
        nodes.append({
            "id": source_rel,
            "label": node_label(source_rel),
            "group": group,
            "group_label": group_label,
            "color": color,
            "sidecar": item.get("sidecar") or html_sidecar_for_md(Path(source_rel)).as_posix(),
        })
        for dep in sorted((item.get("dependencies") or {}).keys()):
            if dep in items:
                edges.append({"from": source_rel, "to": dep})
    return {"nodes": nodes, "edges": edges}


def parse_simple_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, object] = {}
    current_list_key: str | None = None
    for raw in text[4:end].splitlines():
        if not raw.strip():
            continue
        if raw.startswith("  - ") and current_list_key:
            current_items = data.setdefault(current_list_key, [])
            if isinstance(current_items, list):
                current_items.append(raw.strip()[2:].strip())
            continue
        current_list_key = None
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = value
    return data


def task_visual_state(status: str, claimed_by: str | None = None) -> str:
    normalized = (status or "unknown").lower()
    if normalized == "blocked":
        return "blocked_alarm"
    if normalized == "running":
        return "running_pulse"
    if normalized == "claimed" or claimed_by:
        return "claimed_glow"
    if normalized in {"ready", "pending"}:
        return "ready_lane"
    if normalized == "done":
        return "done_dimmed"
    return "unknown"


def iter_task_files(paths: Paths) -> Iterator[Path]:
    tasks_dir = paths.vault / "05-实践与项目/tasks"
    if not tasks_dir.exists():
        return
    for path in sorted(tasks_dir.glob("*.md")):
        if path.is_file():
            yield path


def build_local_brain_app_model(manifest: dict, paths: Paths | None = None) -> dict:
    paths = paths or resolve_paths()
    items = manifest.get("items", {})
    statuses = {item["source"]: item for item in html_status(json_mode=True).get("items", [])} if paths == resolve_paths() else {}
    nodes: list[dict] = []
    edges: list[dict] = []
    groups: dict[str, dict] = {}

    for source_rel, item in sorted(items.items()):
        group, group_label, color = classify_html_node(source_rel)
        groups.setdefault(group, {"id": group, "label": group_label, "color": color, "count": 0})["count"] += 1
        status = statuses.get(source_rel, {}).get("status", "unknown")
        sidecar = item.get("sidecar") or html_sidecar_for_md(Path(source_rel)).as_posix()
        nodes.append({
            "id": f"html:{source_rel}",
            "kind": "html",
            "label": node_label(source_rel),
            "group": group,
            "group_label": group_label,
            "color": color,
            "source_path": source_rel,
            "sidecar_path": sidecar,
            "status": status,
            "generated_at": item.get("generated_at"),
            "open_targets": {
                "canonical_markdown": source_rel,
                "html_sidecar": sidecar,
            },
        })
        for dep in sorted((item.get("dependencies") or {}).keys()):
            edges.append({"from": f"html:{source_rel}", "to": f"html:{dep}", "kind": "html_dependency"})

    task_summary: dict[str, int] = {}
    task_lanes: dict[str, dict[str, int]] = {}
    task_nodes: list[dict] = []
    for task_path in iter_task_files(paths) or []:
        source_rel = task_path.relative_to(paths.vault).as_posix()
        text = task_path.read_text(encoding="utf-8", errors="replace")
        fm = parse_simple_frontmatter(text)
        status = str(fm.get("status") or "unknown")
        priority = str(fm.get("priority") or "unprioritized")
        lane = str(fm.get("lane") or fm.get("project") or "default")
        claimed_by = fm.get("claimed_by")
        raw_evidence = fm.get("evidence")
        evidence = raw_evidence if isinstance(raw_evidence, list) else []
        task_summary[status] = task_summary.get(status, 0) + 1
        task_lanes.setdefault(priority, {})[status] = task_lanes.setdefault(priority, {}).get(status, 0) + 1
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        label = title_match.group(1).strip() if title_match else Path(source_rel).stem
        task_nodes.append({
            "id": f"task:{source_rel}",
            "kind": "task",
            "label": label,
            "group": "taskpool",
            "group_label": "任务池",
            "source_path": source_rel,
            "sidecar_path": html_sidecar_for_md(task_path).relative_to(paths.vault).as_posix(),
            "status": status,
            "priority": priority,
            "lane": lane,
            "claimed_by": claimed_by,
            "blocker_summary": fm.get("blocker_summary"),
            "open_targets": {"canonical_markdown": source_rel},
            "mission_control": {
                "visual_state": task_visual_state(status, str(claimed_by) if claimed_by else None),
                "multimodel_gate": fm.get("multimodel_last_gate_status"),
                "evidence_count": len(evidence),
            },
        })
    if task_nodes:
        groups["taskpool"] = {"id": "taskpool", "label": "任务池", "color": "#f59e0b", "count": len(task_nodes)}
        nodes.extend(task_nodes)

    return {
        "schema": "local_brain_app_model_v1",
        "generated_at": now_ts(),
        "canonical": {
            "vault": str(paths.vault),
            "html_is_derived": True,
            "truth_sources": ["Markdown", "JSON", "kanban.db"],
        },
        "counts": {"html_nodes": len(items), "tasks": len(task_nodes), "edges": len(edges)},
        "groups": list(groups.values()),
        "nodes": nodes,
        "edges": edges,
        "taskpool": {"summary": task_summary, "lanes": task_lanes},
    }


def html_export_app_data(out: str | None = None, *, json_mode: bool = False) -> dict:
    resolved = resolve_paths()
    manifest = load_html_manifest(resolved)
    model = build_local_brain_app_model(manifest, resolved)
    target = Path(out).expanduser() if out else resolved.memory_home / "local-brain-model.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {
        "schema": "local_brain_app_export_v1",
        "path": str(target),
        "node_count": len(model["nodes"]),
        "task_count": model["counts"]["tasks"],
        "edge_count": len(model["edges"]),
    }
    append_wal("html_export_app_data", {"path": str(target), "node_count": result["node_count"], "task_count": result["task_count"]}, paths=resolved)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def render_html_graph(model: dict, paths: Paths) -> str:
    app_path = html_app_path(paths)
    app_href = html_lib.escape(rel_href(html_graph_path(paths), app_path), quote=True)
    app_uri = html_lib.escape(app_path.resolve().as_uri(), quote=True)
    launcher_uri = html_lib.escape(html_launcher_path(paths).resolve().as_uri(), quote=True)
    jump_uri = html_lib.escape(html_jump_test_path(paths).resolve().as_uri(), quote=True)
    total = len(model["nodes"])
    edge_count = len(model["edges"])
    generated = html_lib.escape(now_ts())
    return "\n".join([
        "<!doctype html>",
        '<html lang="zh-CN">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        '  <meta http-equiv="refresh" content="0; url=local-brain-app/index.html">',
        "  <title>本地大脑 HTML 入口</title>",
        "  <style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 20% 0%,rgba(34,211,238,.25),transparent 34rem),#020617;color:#dbeafe;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif}.card{width:min(720px,calc(100% - 32px));border:1px solid rgba(103,232,249,.3);border-radius:28px;padding:28px;background:rgba(15,23,42,.82);box-shadow:0 30px 90px rgba(0,0,0,.35)}a{color:#67e8f9}.kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:18px 0}.kpi{border:1px solid rgba(148,163,184,.2);border-radius:18px;padding:14px}.num{font-size:32px;font-weight:900}.muted{color:#94a3b8}@media(max-width:520px){.kpis{grid-template-columns:1fr}}</style>",
        "</head>",
        '<body data-local-brain-entry="react-app-redirect">',
        '<main class="card">',
        '<p class="muted">本地大脑 HTML 主入口</p>',
        '<h1>正在打开 React Cockpit / Mission Control</h1>',
        '<p class="muted">旧 `本地大脑图形导航.html` 已改为兼容跳转入口；当前主界面是 React/Tailwind/D3/Three-ready 的 local-first App。</p>',
        '<div class="kpis">',
        f'<div class="kpi"><div class="muted">HTML nodes</div><div class="num">{total}</div></div>',
        f'<div class="kpi"><div class="muted">Edges</div><div class="num">{edge_count}</div></div>',
        '</div>',
        f'<p>若未自动跳转：<a href="{app_href}">打开 React HTML App</a></p>',
        f'<p class="muted">App file URI: <a href="{app_uri}">{app_uri}</a></p>',
        f'<p class="muted">Obsidian 入口: <a href="{launcher_uri}">本地大脑HTML入口</a> · 跳转测试: <a href="{jump_uri}">本地大脑HTML跳转测试</a></p>',
        f'<p class="muted">Generated: {generated}</p>',
        '</main>',
        '</body></html>',
        "",
    ])


def html_graph(*, json_mode: bool = False) -> dict:
    resolved = resolve_paths()
    manifest = load_html_manifest(resolved)
    model = build_html_graph_model(manifest)
    target = html_graph_path(resolved)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html_graph(model, resolved), encoding="utf-8")
    launcher = html_launcher_path(resolved)
    jump_test = html_jump_test_path(resolved)
    jump_test.write_text(render_html_jump_test(target, resolved, model), encoding="utf-8")
    launcher.write_text(render_html_launcher(target, resolved, model), encoding="utf-8")
    result = {
        "schema": "local_brain_html_graph_v1",
        "path": target.relative_to(resolved.vault).as_posix(),
        "launcher": launcher.relative_to(resolved.vault).as_posix(),
        "jump_test": jump_test.relative_to(resolved.vault).as_posix(),
        "node_count": len(model["nodes"]),
        "edge_count": len(model["edges"]),
    }
    append_wal("html_graph", {"node_count": result["node_count"], "edge_count": result["edge_count"]}, paths=resolved)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result



def multibrain_root() -> Path:
    return Path(os.environ.get("HERMES_BRAINS_ROOT", str(Path.home() / ".hermes" / "brains"))).expanduser()


def multibrain_registry_path() -> Path:
    return Path(os.environ.get("HERMES_BRAINS_REGISTRY", str(multibrain_root() / "registry.yaml"))).expanduser()


def _read_yaml_file(path: Path) -> tuple[dict, str | None]:
    if not path.exists():
        return {}, f"missing: {path}"
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as exc:
        return {}, f"read_failed: {path}: {exc}"
    if yaml is None:
        # Minimal fallback: enough for status commands to avoid crashing, but not a full parser.
        data: dict[str, object] = {}
        for line in raw.splitlines():
            if ":" in line and not line.startswith(" ") and not line.lstrip().startswith("#"):
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip() or {}
        return data, None
    try:
        loaded = yaml.safe_load(raw) or {}
    except Exception as exc:
        return {}, f"yaml_invalid: {path}: {exc}"
    if not isinstance(loaded, dict):
        return {}, f"yaml_not_mapping: {path}"
    return loaded, None


def load_multibrain_registry() -> tuple[dict, list[str]]:
    registry, error = _read_yaml_file(multibrain_registry_path())
    return registry, ([error] if error else [])


def multibrain_status(*, json_mode: bool = False) -> dict:
    root = multibrain_root()
    registry, errors = load_multibrain_registry()
    subbrains = registry.get("subbrains", {}) if isinstance(registry, dict) else {}
    items: list[dict] = []
    if isinstance(subbrains, dict):
        for brain_id, meta in sorted(subbrains.items()):
            meta = meta if isinstance(meta, dict) else {}
            brain_path = Path(str(meta.get("path") or root / str(brain_id) / "brain.yaml")).expanduser()
            brain_data, err = _read_yaml_file(brain_path)
            if err:
                errors.append(err)
            items.append({
                "id": str(brain_id),
                "path": str(brain_path),
                "exists": brain_path.exists(),
                "version": meta.get("version") or brain_data.get("version"),
                "role": meta.get("role") or brain_data.get("purpose"),
                "status": brain_data.get("status"),
            })
    result = {
        "schema": "hermes_multibrain_status_v1",
        "generated_at": now_ts(),
        "root": str(root),
        "registry": str(multibrain_registry_path()),
        "registry_exists": multibrain_registry_path().exists(),
        "runtime": registry.get("runtime", {}) if isinstance(registry, dict) else {},
        "brain_repos": registry.get("brain_repos", {}) if isinstance(registry, dict) else {},
        "subbrains": items,
        "errors": errors,
        "passed": not errors and bool(items),
    }
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def multibrain_validate(*, json_mode: bool = False) -> dict:
    root = multibrain_root()
    registry, errors = load_multibrain_registry()
    warnings: list[str] = []
    checks: list[dict] = []

    def add_check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        if not passed:
            errors.append(f"{name}: {detail}")

    add_check("root_exists", root.exists() and root.is_dir(), str(root))
    add_check("registry_exists", multibrain_registry_path().exists(), str(multibrain_registry_path()))
    add_check("registry_version", bool(registry.get("version")), str(registry.get("version")))

    subbrains = registry.get("subbrains", {}) if isinstance(registry, dict) else {}
    add_check("subbrains_mapping", isinstance(subbrains, dict) and bool(subbrains), f"count={len(subbrains) if isinstance(subbrains, dict) else 0}")
    if isinstance(subbrains, dict):
        for brain_id, meta in sorted(subbrains.items()):
            meta = meta if isinstance(meta, dict) else {}
            brain_path = Path(str(meta.get("path") or root / str(brain_id) / "brain.yaml")).expanduser()
            brain_data, err = _read_yaml_file(brain_path)
            add_check(f"subbrain.{brain_id}.brain_yaml", err is None, err or str(brain_path))
            if err is None:
                add_check(f"subbrain.{brain_id}.id_match", brain_data.get("id") == brain_id, f"brain.yaml id={brain_data.get('id')!r}")

    runtime = registry.get("runtime", {}) if isinstance(registry, dict) else {}
    runtime_path = Path(str(runtime.get("path") or Path.home() / ".hermes" / "hermes-agent")).expanduser()
    add_check("runtime_repo_exists", (runtime_path / ".git").exists(), str(runtime_path))
    if (runtime_path / ".git").exists():
        def git(args: list[str]) -> tuple[int, str]:
            proc = subprocess.run(["git", *args], cwd=runtime_path, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            return proc.returncode, (proc.stdout or "").strip()
        rc, branch = git(["branch", "--show-current"])
        add_check("runtime_branch", rc == 0 and branch == runtime.get("stable_branch"), f"branch={branch}, expected={runtime.get('stable_branch')}")
        rc, origin = git(["remote", "get-url", "origin"])
        add_check("runtime_origin_private", rc == 0 and "Charles-beta-he/hermes-agent-private" in origin, origin)
        rc, upstream = git(["remote", "get-url", "upstream"])
        add_check("runtime_upstream_official", rc == 0 and "NousResearch/hermes-agent" in upstream, upstream)
        for forbidden in ("state.db", ".hermes"):
            add_check(f"runtime_no_{forbidden.replace('.', '_')}", not (runtime_path / forbidden).exists(), str(runtime_path / forbidden))
        for doc in runtime.get("governance_docs", []) or []:
            add_check(f"runtime_doc.{Path(str(doc)).name}", Path(str(doc)).expanduser().exists(), str(doc))

    brain_repos = registry.get("brain_repos", {}) if isinstance(registry, dict) else {}
    for repo_id, meta in sorted(brain_repos.items()) if isinstance(brain_repos, dict) else []:
        meta = meta if isinstance(meta, dict) else {}
        repo_path = Path(str(meta.get("path") or "")).expanduser()
        add_check(f"brain_repo.{repo_id}.exists", (repo_path / ".git").exists(), str(repo_path))
        for banned in ("state.db", ".hermes", "MEMORY.md", "USER.md"):
            if (repo_path / banned).exists():
                warnings.append(f"brain_repo.{repo_id}: top-level sensitive/runtime candidate exists: {banned}")

    routing = registry.get("routing", {}) if isinstance(registry, dict) else {}
    add_check("routing_default_entry", isinstance(routing, dict) and routing.get("default_entry") in (subbrains or {}), f"default_entry={routing.get('default_entry') if isinstance(routing, dict) else None}")
    result = {
        "schema": "hermes_multibrain_validate_v1",
        "generated_at": now_ts(),
        "root": str(root),
        "passed": not errors,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }
    append_wal("multibrain_validate", {"passed": result["passed"], "error_count": len(errors), "warning_count": len(warnings)}, paths=resolve_paths())
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def multibrain_route(query: str, *, json_mode: bool = False) -> dict:
    registry, errors = load_multibrain_registry()
    query_l = query.lower()
    brain = "main"
    reason = "default_entry"
    rules = [
        ("hermes-core", "hermes_private_repo_governance", ["hermes", "private", "私有仓", "upstream", "overlay", "post-update-check", "多模型", "taskpool", "任务池", "conductor", "brainctl", "多脑"]),
        ("dev", "general_software_project_changes", ["react", "vue", "typescript", "frontend", "backend", "uvisa", "测试", "实现", "bugfix"]),
    ]
    for candidate, rule, keywords in rules:
        if any(k.lower() in query_l or k in query for k in keywords):
            brain = candidate
            reason = rule
            break
    result = {
        "schema": "hermes_multibrain_route_v1",
        "generated_at": now_ts(),
        "query": query,
        "brain": brain,
        "reason": reason,
        "registry_errors": errors,
        "routing_table": registry.get("routing", {}) if isinstance(registry, dict) else {},
    }
    append_wal("multibrain_route", {"brain": brain, "reason": reason, "query_hash": sha256_text(query)}, paths=resolve_paths())
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result

def slugify(value: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff_-]+", "-", value.strip()).strip("-")
    return raw or "review"


def review_record(title: str, slug: str | None = None, evidence_requests: list[str] | None = None, votes: list[str] | None = None, final_adjudication: str = "pending", json_mode: bool = False) -> dict:
    paths = resolve_paths()
    safe_slug = slugify(slug or title)
    date = time.strftime("%Y-%m-%d", time.gmtime())
    target = paths.vault / "06-治理与评审" / "reviews" / f"{date}-{safe_slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    evidence_requests = evidence_requests or []
    votes = votes or []
    lines = [
        "---",
        "type: review",
        "layer: L6",
        "status: completed",
        f"created: {now_ts()}",
        "source: brainctl review record",
        "---",
        "",
        f"# {title}",
        "",
        "## Evidence Boundary",
        "",
        "Model agreement is provenance only; promotion requires satisfied tool/file/search evidence requests.",
        "",
        "## Evidence Requests",
        "",
    ]
    lines.extend(f"- {item}" for item in evidence_requests) if evidence_requests else lines.append("- none")
    lines.extend(["", "## Votes", ""])
    lines.extend(f"- {vote}" for vote in votes) if votes else lines.append("- none")
    lines.extend(["", "## Final Adjudication", "", final_adjudication.strip() or "pending", ""])
    target.write_text("\n".join(lines), encoding="utf-8")
    result = {"ok": True, "schema": "local_brain_review_record_v1", "path": str(target), "rel_path": target.relative_to(paths.vault).as_posix()}
    append_wal("review_record", {"path": result["rel_path"]}, paths=paths)
    if not json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes local brain control plane")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="show local brain status")
    sub.add_parser("reindex", help="rebuild SQLite FTS5 evidence index")

    p_search = sub.add_parser("search", help="search evidence index")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)

    p_evidence = sub.add_parser("evidence", help="search and return evidence objects")
    p_evidence.add_argument("query")
    p_evidence.add_argument("--limit", type=int, default=10)

    p_wal = sub.add_parser("wal", help="show WAL tail")
    p_wal.add_argument("--tail", type=int, default=20)

    sub.add_parser("sync", help="run existing sync-brain.py")

    p_open = sub.add_parser("open", help="print or launch Obsidian URI for a note")
    p_open.add_argument("path")
    p_open.add_argument("--launch", action="store_true")

    p_validate = sub.add_parser("validate", help="dry-run governance validation for local-brain notes")
    p_validate.add_argument("--dry-run", action="store_true", default=True)
    p_validate.add_argument("--write-dashboard", action="store_true")

    p_expire = sub.add_parser("expire", help="dry-run L3 expiry/ghost-memory report")
    p_expire.add_argument("--dry-run", action="store_true", default=True)

    p_promote = sub.add_parser("promote", help="dry-run evidence-backed promotion candidates")
    p_promote.add_argument("--dry-run", action="store_true", default=True)

    p_html = sub.add_parser("html", help="generate/status/refresh derived HTML sidecars")
    html_sub = p_html.add_subparsers(dest="html_cmd", required=True)
    for name, help_text in (
        ("build", "build HTML sidecars from canonical Markdown"),
        ("status", "report missing/fresh/stale HTML sidecars"),
        ("refresh", "rebuild missing or stale HTML sidecars"),
        ("watch", "poll canonical sources and refresh stale HTML sidecars"),
        ("graph", "build big-screen graph navigation from HTML sidecar manifest"),
        ("export-app-data", "export local_brain_app_model_v1 JSON for the React app"),
    ):
        p_html_cmd = html_sub.add_parser(name, help=help_text)
        p_html_cmd.add_argument("--path", action="append", default=[], help="canonical Markdown path, repeatable; defaults to high-value dynamic views")
        if name == "watch":
            p_html_cmd.add_argument("--interval", type=float, default=5.0)
            p_html_cmd.add_argument("--once", action="store_true", help="run one refresh cycle and exit")
        if name == "export-app-data":
            p_html_cmd.add_argument("--out", default=None, help="output JSON path; defaults to ~/.hermes/memory/local-brain-model.json")

    p_brains = sub.add_parser("brains", help="inspect and validate Hermes multi-brain overlay registry")
    brains_sub = p_brains.add_subparsers(dest="brains_cmd", required=True)
    brains_sub.add_parser("status", help="show multi-brain registry and subbrain status")
    brains_sub.add_parser("validate", help="validate multi-brain registry, repo boundaries, and routing")
    p_brains_route = brains_sub.add_parser("route", help="route a natural-language request to the owning brain")
    p_brains_route.add_argument("query")

    p_review = sub.add_parser("review", help="create a standardized L6 review artifact")
    review_sub = p_review.add_subparsers(dest="review_cmd", required=True)
    p_record = review_sub.add_parser("record", help="write a review record")
    p_record.add_argument("--title", required=True)
    p_record.add_argument("--slug", default=None)
    p_record.add_argument("--evidence-request", action="append", default=[])
    p_record.add_argument("--vote", action="append", default=[])
    p_record.add_argument("--final-adjudication", default="pending")
    return parser


def emit_cli(result, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "status":
        emit_cli(status(json_mode=True), args.json)
    elif args.cmd == "reindex":
        emit_cli(reindex(json_mode=True), args.json)
    elif args.cmd == "search":
        emit_cli(search(args.query, limit=args.limit, json_mode=True), args.json)
    elif args.cmd == "evidence":
        emit_cli(evidence(args.query, limit=args.limit, json_mode=True), args.json)
    elif args.cmd == "wal":
        emit_cli(wal_tail(limit=args.tail, json_mode=True), args.json)
    elif args.cmd == "sync":
        result = sync(json_mode=True)
        emit_cli(result, args.json)
        return int(result.get("exit_code", 1))
    elif args.cmd == "open":
        emit_cli(open_note(args.path, json_mode=True, launch=args.launch), args.json)
    elif args.cmd == "validate":
        emit_cli(validate(dry_run=args.dry_run, write_dashboard=args.write_dashboard, json_mode=True), args.json)
    elif args.cmd == "expire":
        emit_cli(expire(dry_run=args.dry_run, json_mode=True), args.json)
    elif args.cmd == "promote":
        emit_cli(promote(dry_run=args.dry_run, json_mode=True), args.json)
    elif args.cmd == "html":
        selected_paths = args.path or None
        if args.html_cmd == "build":
            emit_cli(html_build(paths=selected_paths, json_mode=True), args.json)
        elif args.html_cmd == "status":
            emit_cli(html_status(paths=selected_paths, json_mode=True), args.json)
        elif args.html_cmd == "refresh":
            emit_cli(html_refresh(paths=selected_paths, json_mode=True), args.json)
        elif args.html_cmd == "watch":
            emit_cli(html_watch(paths=selected_paths, interval=args.interval, once=args.once, json_mode=True), args.json)
        elif args.html_cmd == "graph":
            emit_cli(html_graph(json_mode=True), args.json)
        elif args.html_cmd == "export-app-data":
            emit_cli(html_export_app_data(out=args.out, json_mode=True), args.json)
        else:
            raise AssertionError(args.html_cmd)
    elif args.cmd == "brains":
        if args.brains_cmd == "status":
            emit_cli(multibrain_status(json_mode=True), args.json)
        elif args.brains_cmd == "validate":
            result = multibrain_validate(json_mode=True)
            emit_cli(result, args.json)
            return 0 if result.get("passed") else 2
        elif args.brains_cmd == "route":
            emit_cli(multibrain_route(args.query, json_mode=True), args.json)
        else:
            raise AssertionError(args.brains_cmd)
    elif args.cmd == "review":
        if args.review_cmd == "record":
            emit_cli(
                review_record(
                    title=args.title,
                    slug=args.slug,
                    evidence_requests=args.evidence_request,
                    votes=args.vote,
                    final_adjudication=args.final_adjudication,
                    json_mode=True,
                ),
                args.json,
            )
        else:
            raise AssertionError(args.review_cmd)
    else:
        raise AssertionError(args.cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
