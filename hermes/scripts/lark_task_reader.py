#!/usr/bin/env python3
from __future__ import annotations
"""Hermes-native read-only Lark Task Center reader.

Source-derived from the matured arc-dispatch/github-dispatch collectors, but
safe as a standalone helper: it only reads tasks/comments/docs and prints JSON;
it never enqueues, writes back to Lark, or mutates project repos.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LARK_API = "https://open.larksuite.com/open-apis"
DEFAULT_PREFERRED_SCOPES = ["UVISA-2.0新版开发"]
SCOPE_ALIASES = ["UVISA-2.0新版开发", "uvisa-app-2.0", "UVISA-2.0", "新版开发"]
VALID_SCOPE_MODES = {"prefer", "only", "off"}
_DOCX_RE = re.compile(r"https?://[a-z0-9.\-]+\.(?:larksuite|feishu)\.(?:com|cn)/docx/([A-Za-z0-9]+)")
_WIKI_RE = re.compile(r"https?://[a-z0-9.\-]+\.(?:larksuite|feishu)\.(?:com|cn)/wiki/([A-Za-z0-9]+)")
_URL_RE = re.compile(r"https?://[^\s)\]}>'\"]+")


def configured_preferred_scopes(preferred_scopes: list[str] | None = None) -> list[str]:
    if preferred_scopes:
        return [s.strip() for s in preferred_scopes if s and s.strip()]
    raw = os.environ.get("LARK_TASK_PREFERRED_SCOPES", "")
    if raw.strip():
        return [s.strip() for s in raw.split(",") if s.strip()]
    return list(DEFAULT_PREFERRED_SCOPES)


def configured_scope_mode(scope_mode: str | None = None) -> str:
    mode = (scope_mode or os.environ.get("LARK_TASK_SCOPE_MODE") or "prefer").strip().lower()
    if mode not in VALID_SCOPE_MODES:
        raise ValueError(f"Invalid LARK_TASK_SCOPE_MODE={mode!r}; expected one of {sorted(VALID_SCOPE_MODES)}")
    return mode


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _scope_haystack(task: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("summary", "title", "description", "url"):
        parts.append(_stringify(task.get(key)))
    for key in ("custom_fields", "tasklist", "tasklist_name", "container", "breadcrumb", "sections", "members"):
        parts.append(_stringify(task.get(key)))
    parts.append(_stringify(task))
    return "\n".join(p for p in parts if p)


def tasklist_names(task: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("tasklist_name", "tasklist_names"):
        value = task.get(key)
        if isinstance(value, str) and value:
            names.append(value)
        elif isinstance(value, list):
            names.extend(str(v) for v in value if v)
    for tl in task.get("tasklists", []) or []:
        if isinstance(tl, dict):
            name = tl.get("name") or tl.get("tasklist_name")
            if name:
                names.append(str(name))
    return list(dict.fromkeys(names))


def _hard_scope_match(task: dict[str, Any], preferred_scopes: list[str] | None = None) -> bool:
    scopes = configured_preferred_scopes(preferred_scopes)
    names = [n.lower() for n in tasklist_names(task)]
    return any(scope.lower() in names for scope in scopes)


def match_scope(task: dict[str, Any], preferred_scopes: list[str] | None = None) -> dict[str, Any]:
    scopes = configured_preferred_scopes(preferred_scopes)
    aliases = list(dict.fromkeys(scopes + SCOPE_ALIASES))
    haystack = _scope_haystack(task)
    haystack_lower = haystack.lower()
    for scope in aliases:
        if scope and scope.lower() in haystack_lower:
            canonical = scopes[0] if scope in SCOPE_ALIASES and scopes else scope
            return {"matched": True, "scope": canonical, "matched_text": scope}
    return {"matched": False, "scope": "", "matched_text": ""}


def prioritize_tasks(tasks: list[dict[str, Any]], preferred_scopes: list[str] | None = None, scope_mode: str | None = None) -> list[dict[str, Any]]:
    mode = configured_scope_mode(scope_mode)
    annotated: list[dict[str, Any]] = []
    for task in tasks:
        copied = dict(task)
        m = match_scope(copied, preferred_scopes)
        copied["_lark_task_scope"] = m["scope"]
        copied["_lark_task_scope_match"] = m
        annotated.append(copied)
    if mode == "off":
        return annotated
    if mode == "only":
        # Hard scope mode is used to prove tasklist membership. Do not let title,
        # description, or comments containing "新版开发" masquerade as membership.
        return [t for t in annotated if _hard_scope_match(t, preferred_scopes)]
    scoped = [t for t in annotated if t.get("_lark_task_scope_match", {}).get("matched")]
    return scoped if scoped else annotated


def _custom_field_value_text(cf: dict[str, Any]) -> str:
    values: list[str] = []
    for key in ("value", "text_value", "single_select_value", "multi_select_value", "number_value", "datetime_value"):
        if key in cf:
            values.append(_stringify(cf.get(key)))
    return " ".join(v for v in values if v).strip()


def should_include_unprocessed(task: dict[str, Any]) -> bool:
    completed_at = task.get("completed_at", "0")
    if completed_at not in (None, "", 0, "0") and str(completed_at) != "0":
        return False
    if task.get("completed") is True:
        return False
    skip_status_values = {"已派发", "处理中", "进行中", "已处理", "已完成", "done", "closed", "complete", "completed"}
    pending_status_values = {"", "未开始", "待处理", "todo", "open", "pending", "new", "待办"}
    for cf in task.get("custom_fields", []) or []:
        if isinstance(cf, dict) and cf.get("name") == "状态":
            value = _custom_field_value_text(cf).strip()
            normalized = value.lower()
            if normalized in pending_status_values or value in pending_status_values:
                continue
            if normalized in skip_status_values or value in skip_status_values:
                return False
            # Preserve old dispatch safety for unknown non-empty 状态 values:
            # unknown status likely means already in a workflow lane.
            if value:
                return False
    return True


@dataclass
class LarkClient:
    api_base: str = LARK_API
    timeout: int = 20

    def get(self, path: str, token: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self.api_base + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


def get_token() -> str:
    env = os.environ.get("LARK_USER_ACCESS_TOKEN") or os.environ.get("FEISHU_USER_ACCESS_TOKEN")
    if env:
        return env.strip()
    root = Path(os.environ.get("LARK_MCP_ROOT", "/Users/charles/.nvm/versions/node/v24.14.0/lib/node_modules/@larksuiteoapi/lark-mcp"))
    script = f"""
const {{ authStore }} = require({json.dumps(str(root / 'dist/auth/store.js'))});
authStore.initialize().then(() => {{
  const tokens = authStore.storageDataCache.tokens || {{}};
  const keys = Object.keys(tokens);
  if (!keys.length) {{ process.stderr.write('NO_TOKEN\\n'); process.exit(1); }}
  const valid = keys.find(k => !tokens[k].expiresAt || Date.now() / 1000 <= tokens[k].expiresAt);
  if (!valid) {{ process.stderr.write('TOKEN_EXPIRED\\n'); process.exit(1); }}
  process.stdout.write(valid);
  process.exit(0);
}}).catch(e => {{ process.stderr.write(String(e)); process.exit(1); }});
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=20)
    if result.returncode != 0:
        raise RuntimeError(f"Lark token unavailable: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def fetch_tasks(token: str, page_size: int = 100, client: LarkClient | Any | None = None) -> list[dict[str, Any]]:
    client = client or LarkClient()
    items: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        query: dict[str, Any] = {"page_size": page_size, "completed": "false"}
        if page_token:
            query["page_token"] = page_token
        data = client.get("/task/v2/tasks", token, query=query)
        if data.get("code") != 0:
            raise RuntimeError(f"Lark API error {data.get('code')}: {data.get('msg')}")
        body = data.get("data") or {}
        items.extend(body.get("items") or [])
        if not body.get("has_more"):
            break
        page_token = body.get("page_token")
        if not page_token:
            raise RuntimeError("Lark API pagination reported has_more=true without page_token")
    return items


def fetch_tasklists(token: str, page_size: int = 100, client: LarkClient | Any | None = None) -> dict[str, dict[str, Any]]:
    """Return tasklist_guid -> tasklist metadata for lists visible to caller."""
    client = client or LarkClient()
    mapping: dict[str, dict[str, Any]] = {}
    page_token: str | None = None
    while True:
        query: dict[str, Any] = {"page_size": page_size}
        if page_token:
            query["page_token"] = page_token
        data = client.get("/task/v2/tasklists", token, query=query)
        if data.get("code") != 0:
            raise RuntimeError(f"Lark tasklist API error {data.get('code')}: {data.get('msg')}")
        body = data.get("data") or {}
        for item in body.get("items") or []:
            guid = item.get("guid") or item.get("tasklist_guid")
            if guid:
                mapping[guid] = item
        if not body.get("has_more"):
            break
        page_token = body.get("page_token")
        if not page_token:
            raise RuntimeError("Lark tasklist pagination reported has_more=true without page_token")
    return mapping


def enrich_tasks_with_tasklists(tasks: list[dict[str, Any]], token: str, client: LarkClient | Any | None = None) -> list[dict[str, Any]]:
    """Attach tasklist names/urls to task.tasklists so scope can match real list names.

    If the tasklist endpoint is unavailable, keep the raw task payload but annotate
    each task with a warning. This is intentionally visible: hard-scope reads must
    not be certified from title/body keywords when tasklist names were unavailable.
    """
    enrichment_warning = ""
    try:
        by_guid = fetch_tasklists(token, client=client)
    except Exception as exc:
        by_guid = {}
        enrichment_warning = f"tasklist_enrichment_failed: {type(exc).__name__}: {exc}"
    enriched: list[dict[str, Any]] = []
    for task in tasks:
        copied = dict(task)
        new_tasklists = []
        for tl in copied.get("tasklists", []) or []:
            if not isinstance(tl, dict):
                continue
            merged = dict(tl)
            meta = by_guid.get(tl.get("tasklist_guid") or tl.get("guid"))
            if meta:
                merged.setdefault("name", meta.get("name"))
                merged.setdefault("url", meta.get("url"))
                merged.setdefault("guid", meta.get("guid"))
            new_tasklists.append(merged)
        copied["tasklists"] = new_tasklists
        copied["tasklist_names"] = tasklist_names(copied)
        if enrichment_warning:
            copied["tasklist_scope_enrichment_warning"] = enrichment_warning
        enriched.append(copied)
    return enriched


def fetch_comments(token: str, task_guid: str, page_size: int = 50, client: LarkClient | Any | None = None) -> list[dict[str, Any]]:
    client = client or LarkClient()
    endpoints = [
        (f"/task/v2/tasks/{task_guid}/comments", lambda pt: {"page_size": page_size, **({"page_token": pt} if pt else {})}),
        ("/task/v2/comments", lambda pt: {"resource_id": task_guid, "resource_type": "task", "page_size": page_size, **({"page_token": pt} if pt else {})}),
    ]
    best_empty: list[dict[str, Any]] = []
    for path, make_query in endpoints:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        try:
            while True:
                data = client.get(path, token, query=make_query(page_token))
                if data.get("code") != 0:
                    raise RuntimeError(f"Lark comments API error {data.get('code')}: {data.get('msg')}")
                body = data.get("data") or {}
                items.extend(body.get("items") or [])
                if not body.get("has_more"):
                    if items:
                        return items
                    best_empty = items
                    break
                page_token = body.get("page_token")
                if not page_token:
                    raise RuntimeError("Lark comments pagination reported has_more=true without page_token")
        except Exception:
            continue
    return best_empty


def _extract_text_and_images_from_content(content: Any) -> tuple[str, list[str], list[str]]:
    try:
        obj = json.loads(content) if isinstance(content, str) else content
    except (json.JSONDecodeError, TypeError):
        text = str(content).strip()
        return text, [], _URL_RE.findall(text)
    parts: list[str] = []
    image_keys: list[str] = []
    links: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            parts.append(node)
            links.extend(_URL_RE.findall(node))
            return
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return
        if node.get("text_run"):
            text = node["text_run"].get("content", "")
            parts.append(text)
            links.extend(_URL_RE.findall(text))
        if node.get("link"):
            url = node["link"].get("url", "")
            if url:
                parts.append(url)
                links.append(url)
        if node.get("image"):
            img = node["image"]
            key = img.get("image_key") or img.get("file_token") or ""
            if key:
                image_keys.append(key)
            parts.append(f"[图片{(':' + key[:16]) if key else ''}]")
        if node.get("file"):
            f = node["file"]
            name = f.get("name") or f.get("file_name") or "file"
            parts.append(f"[附件:{name}]")
        if node.get("mention_doc"):
            md = node["mention_doc"]
            title = md.get("title") or md.get("name") or "doc"
            url = md.get("url") or ""
            token = md.get("token") or md.get("obj_token") or md.get("wiki_token") or ""
            parts.append(f"[文档:{title}]" + (f" {url}" if url else (f" {token}" if token else "")))
            if url:
                links.append(url)
        for key in ("elements", "children"):
            if node.get(key):
                walk(node[key])

    walk(obj)
    return " ".join(p for p in parts if p).strip(), list(dict.fromkeys(image_keys)), list(dict.fromkeys(links))


def extract_comment_text(comments: list[dict[str, Any]], limit: int = 20) -> str:
    lines: list[str] = []
    all_links: list[str] = []
    for c in comments[:limit]:
        text, _keys, links = _extract_text_and_images_from_content(c.get("content", ""))
        all_links.extend(links)
        if text:
            creator = ((c.get("creator") or {}).get("name") or (c.get("operator") or {}).get("name") or "unknown")
            lines.append(f"[{creator}] {text[:600]}")
    unique_links = list(dict.fromkeys(all_links))
    if unique_links:
        lines.append("\n## 提取的链接\n" + "\n".join(unique_links[:20]))
    return "\n".join(lines)


def extract_comment_image_keys(comments: list[dict[str, Any]], limit: int = 20) -> list[str]:
    seen: set[str] = set()
    keys: list[str] = []
    for c in comments[:limit]:
        _text, image_keys, _links = _extract_text_and_images_from_content(c.get("content", ""))
        for key in image_keys:
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


def _extract_lark_links(text: str) -> tuple[list[str], list[str]]:
    return list(dict.fromkeys(_DOCX_RE.findall(text or ""))), list(dict.fromkeys(_WIKI_RE.findall(text or "")))


def _wiki_to_docx_id(token: str, node_token: str, client: LarkClient | Any | None = None) -> str | None:
    client = client or LarkClient()
    try:
        data = client.get("/wiki/v2/spaces/get_node", token, query={"token": node_token})
        if data.get("code") == 0:
            node = (data.get("data") or {}).get("node") or {}
            if node.get("obj_type") in ("doc", "docx"):
                return node.get("obj_token")
    except Exception:
        return None
    return None


def _fetch_docx_content(token: str, doc_id: str, max_chars: int = 3000, client: LarkClient | Any | None = None) -> str:
    client = client or LarkClient()
    try:
        data = client.get(f"/docx/v1/documents/{doc_id}/raw_content", token)
        if data.get("code") == 0:
            return ((data.get("data") or {}).get("content") or "")[:max_chars]
    except Exception:
        return ""
    return ""


def fetch_linked_docs(token: str, text: str, max_docs: int = 3, max_chars: int = 3000, client: LarkClient | Any | None = None) -> str:
    client = client or LarkClient()
    docx_ids, wiki_tokens = _extract_lark_links(text)
    for wt in wiki_tokens:
        doc_id = _wiki_to_docx_id(token, wt, client=client)
        if doc_id and doc_id not in docx_ids:
            docx_ids.append(doc_id)
    parts: list[str] = []
    for doc_id in docx_ids[:max_docs]:
        content = _fetch_docx_content(token, doc_id, max_chars=max_chars, client=client)
        if content:
            parts.append(f"[文档内容 {doc_id}]\n{content}")
    return "\n\n".join(parts)


def payload_from_task(token: str, task: dict[str, Any], client: LarkClient | Any | None = None, include_comments: bool = True, include_docs: bool = True) -> dict[str, Any]:
    client = client or LarkClient()
    comments_raw = fetch_comments(token, task["guid"], client=client) if include_comments else []
    comments_text = extract_comment_text(comments_raw)
    comment_image_keys = extract_comment_image_keys(comments_raw)
    raw_description = task.get("description", "") or ""
    description, description_image_keys, _description_links = _extract_text_and_images_from_content(raw_description)
    combined = f"{description}\n\n{comments_text}"
    docs_content = fetch_linked_docs(token, combined, client=client) if include_docs else ""
    body_parts = []
    if description:
        body_parts.append(description)
    if comments_text:
        body_parts.append("## 评论补充\n" + comments_text)
    if docs_content:
        body_parts.append("## 关联文档内容\n" + docs_content)
    issue_body = "\n\n".join(body_parts)
    image_keys = list(dict.fromkeys(description_image_keys + comment_image_keys))
    return {
        "lark_task_guid": task["guid"],
        "issue_number": task["guid"],
        "issue_title": task.get("summary") or task.get("title") or "",
        "issue_body": issue_body,
        "summary": task.get("summary") or task.get("title") or "",
        "description": description,
        "comments": comments_text,
        "comment_image_keys": image_keys,
        "linked_docs": docs_content,
        "docs_content": docs_content,
        "custom_fields": task.get("custom_fields", []),
        "members": task.get("members", []),
        "tasklists": task.get("tasklists", []),
        "tasklist_names": task.get("tasklist_names", []),
        "tasklist_scope_enrichment_warning": task.get("tasklist_scope_enrichment_warning", ""),
        "lark_url": task.get("url", ""),
        "lark_task_scope": task.get("_lark_task_scope", ""),
        "lark_task_scope_match": task.get("_lark_task_scope_match", {}),
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "labels": [],
    }


def collect_tasks(token: str | None = None, client: LarkClient | Any | None = None, preferred_scopes: list[str] | None = None, scope_mode: str | None = None, include_comments: bool = True, include_docs: bool = True) -> list[dict[str, Any]]:
    token = token or get_token()
    client = client or LarkClient()
    raw = enrich_tasks_with_tasklists(fetch_tasks(token, client=client), token, client=client)
    selected = prioritize_tasks(raw, preferred_scopes=preferred_scopes, scope_mode=scope_mode)
    candidates = [t for t in selected if should_include_unprocessed(t)]
    seen: set[str] = set()
    payloads: list[dict[str, Any]] = []
    for task in candidates:
        guid = task.get("guid")
        if not guid or guid in seen:
            continue
        seen.add(guid)
        payloads.append(payload_from_task(token, task, client=client, include_comments=include_comments, include_docs=include_docs))
    return payloads


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read incomplete Lark tasks as JSON; read-only, no enqueue/writeback.")
    parser.add_argument("--preferred-scope", action="append", dest="preferred_scopes", help="Preferred Lark task scope/tasklist; default UVISA-2.0新版开发")
    parser.add_argument("--scope-mode", choices=sorted(VALID_SCOPE_MODES), default=None, help="prefer=default scoped tasks first; only=hard filter; off=disable scope preference")
    parser.add_argument("--no-comments", action="store_true")
    parser.add_argument("--no-docs", action="store_true")
    parser.add_argument("--summary", action="store_true", help="Print compact human-readable summary instead of JSON")
    args = parser.parse_args(argv)
    payloads = collect_tasks(preferred_scopes=args.preferred_scopes, scope_mode=args.scope_mode, include_comments=not args.no_comments, include_docs=not args.no_docs)
    if args.summary:
        print(f"tasks={len(payloads)}")
        for i, p in enumerate(payloads, 1):
            desc = (p.get("description") or p.get("comments") or "").replace("\n", " ")[:180]
            print(f"{i}. {p.get('summary')} | guid={p.get('lark_task_guid')} | scope={p.get('lark_task_scope')} | desc={desc}")
    else:
        print(json.dumps(payloads, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
