#!/usr/bin/env python3
"""Read Lark/Larksuite Docx documents via OpenAPI.

Auth modes:
  tenant (default): app/tenant identity via LARK_APP_ID + LARK_APP_SECRET
  user: user identity via either:
    - LARK_USER_ACCESS_TOKEN
    - --oauth-code plus LARK_APP_ID + LARK_APP_SECRET (+ --redirect-uri if used when obtaining code)

Usage:
  LARK_APP_ID=... LARK_APP_SECRET=... python3 lark_docx_reader.py <docx_url_or_token> --out /tmp/doc.json
  LARK_USER_ACCESS_TOKEN=... python3 lark_docx_reader.py <docx_url_or_token> --auth user --out /tmp/doc.json
  LARK_APP_ID=... LARK_APP_SECRET=... python3 lark_docx_reader.py --make-auth-url --redirect-uri http://localhost:8765/callback --scope docx:document offline_access
  LARK_APP_ID=... LARK_APP_SECRET=... python3 lark_docx_reader.py <docx_url_or_token> --auth user --oauth-code CODE --redirect-uri http://localhost:8765/callback --out /tmp/doc.json

Security:
  - Never prints access tokens or app secrets.
  - Redacts common credential-like fields in document text previews.
  - Output files include extracted document content, but not access tokens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

OPENAPI = os.environ.get("LARK_OPENAPI_BASE", "https://open.larksuite.com")
AUTH_BASE = os.environ.get("LARK_AUTH_BASE", "https://accounts.larksuite.com")

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|pwd|authorization|bearer)\s*[:：=]\s*([^\s,;，；]+)"),
    re.compile(r"(?i)(refresh[_-]?token|access[_-]?token)\s*[:：=]\s*([^\s,;，；]+)"),
]


def redact(s: str) -> str:
    out = s
    for pat in SECRET_PATTERNS:
        out = pat.sub(lambda m: f"{m.group(1)}=[REDACTED]", out)
    return out


def safe_error(e: Exception) -> str:
    return redact(str(e))


def request_json(method: str, path: str, *, token: str | None = None, body: dict[str, Any] | None = None, query: dict[str, Any] | None = None) -> dict[str, Any]:
    url = OPENAPI.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": redact(raw[:1000])}
        raise RuntimeError(json.dumps({"http_status": e.code, "url": url.split("?")[0], "payload": payload}, ensure_ascii=False))


def post_json_url(url: str, body: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": redact(raw[:1000])}
        raise RuntimeError(json.dumps({"http_status": e.code, "url": url, "payload": payload}, ensure_ascii=False))


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    payload = request_json("POST", "/open-apis/auth/v3/tenant_access_token/internal", body={"app_id": app_id, "app_secret": app_secret})
    if payload.get("code") != 0:
        raise RuntimeError(json.dumps({"stage": "tenant_access_token", "payload": payload}, ensure_ascii=False))
    token = payload.get("tenant_access_token")
    if not token:
        raise RuntimeError("tenant_access_token missing")
    return token


def exchange_user_access_token(app_id: str, app_secret: str, code: str, redirect_uri: str | None = None, code_verifier: str | None = None, scope: str | None = None) -> tuple[str, dict[str, Any]]:
    body: dict[str, Any] = {
        "grant_type": "authorization_code",
        "client_id": app_id,
        "client_secret": app_secret,
        "code": code,
    }
    if redirect_uri:
        body["redirect_uri"] = redirect_uri
    if code_verifier:
        body["code_verifier"] = code_verifier
    if scope:
        body["scope"] = scope
    payload = post_json_url(OPENAPI.rstrip("/") + "/open-apis/authen/v2/oauth/token", body)
    # Lark v2 OAuth may return either {code:0,data:{access_token}} or OAuth-like top-level fields.
    if payload.get("code") not in (None, 0):
        raise RuntimeError(json.dumps({"stage": "user_access_token", "payload": payload}, ensure_ascii=False))
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    token = data.get("access_token") or data.get("user_access_token")
    if not token:
        raise RuntimeError(json.dumps({"stage": "user_access_token", "payload_keys": sorted(payload.keys()), "data_keys": sorted(data.keys())}, ensure_ascii=False))
    return token, data


def make_authorize_url(app_id: str, redirect_uri: str, scope: str = "docx:document", state: str | None = None) -> str:
    state = state or secrets.token_urlsafe(18)
    query = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
    }
    return AUTH_BASE.rstrip("/") + "/open-apis/authen/v1/authorize?" + urllib.parse.urlencode(query)


def extract_doc_token(s: str) -> str:
    s = s.strip()
    m = re.search(r"/docx/([A-Za-z0-9]+)", s)
    if m:
        return m.group(1)
    return s


def get_document_meta(token: str, access_token: str) -> dict[str, Any]:
    return request_json("GET", f"/open-apis/docx/v1/documents/{token}", token=access_token)


def list_blocks(token: str, access_token: str, page_size: int = 500) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    page_token = None
    while True:
        query = {"document_revision_id": -1, "page_size": page_size}
        if page_token:
            query["page_token"] = page_token
        payload = request_json("GET", f"/open-apis/docx/v1/documents/{token}/blocks", token=access_token, query=query)
        if payload.get("code") != 0:
            raise RuntimeError(json.dumps({"stage": "list_blocks", "payload": payload}, ensure_ascii=False))
        data = payload.get("data") or {}
        blocks.extend(data.get("items") or [])
        page_token = data.get("page_token")
        if not data.get("has_more"):
            break
        time.sleep(0.15)
    return blocks


def text_from_elements(elements: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for el in elements or []:
        text_run = el.get("text_run") or {}
        if "content" in text_run:
            parts.append(text_run.get("content") or "")
        mention = el.get("mention_user") or el.get("mention_doc") or el.get("mention_sheet") or el.get("mention_bitable")
        if mention:
            parts.append(mention.get("name") or mention.get("title") or "")
        equation = el.get("equation")
        if equation:
            parts.append(equation.get("content") or "")
    return redact("".join(parts)).strip()


def block_to_text(block: dict[str, Any]) -> str | None:
    btype = block.get("block_type")
    candidates = [
        "text", "heading1", "heading2", "heading3", "heading4", "heading5", "heading6", "heading7", "heading8", "heading9",
        "bullet", "ordered", "code", "quote", "todo", "callout", "table_cell",
    ]
    for key in candidates:
        val = block.get(key)
        if isinstance(val, dict):
            txt = text_from_elements(val.get("elements"))
            if txt:
                prefix = ""
                if key.startswith("heading"):
                    level = key.replace("heading", "")
                    prefix = "#" * max(1, int(level or 1)) + " "
                elif key == "bullet":
                    prefix = "- "
                elif key == "ordered":
                    prefix = "1. "
                elif key == "todo":
                    prefix = "[ ] "
                elif key == "quote":
                    prefix = "> "
                return prefix + txt
    marker_map = {
        "table": "[TABLE]",
        "grid": "[GRID]",
        "image": "[IMAGE]",
        "file": "[FILE]",
        "divider": "---",
    }
    if isinstance(btype, int):
        return None
    return marker_map.get(str(btype))


def resolve_access_token(args: argparse.Namespace) -> tuple[str, str, dict[str, Any]]:
    if args.auth == "user":
        env_token = os.environ.get("LARK_USER_ACCESS_TOKEN") or os.environ.get("FEISHU_USER_ACCESS_TOKEN")
        if env_token:
            return env_token.removeprefix("Bearer ").strip(), "user_access_token_env", {}
        if args.oauth_code:
            app_id = os.environ.get("LARK_APP_ID") or os.environ.get("FEISHU_APP_ID")
            app_secret = os.environ.get("LARK_APP_SECRET") or os.environ.get("FEISHU_APP_SECRET")
            if not app_id or not app_secret:
                raise SystemExit("Missing LARK_APP_ID/LARK_APP_SECRET env for OAuth code exchange")
            token, token_data = exchange_user_access_token(app_id, app_secret, args.oauth_code, args.redirect_uri, args.code_verifier, args.scope)
            safe_token_data = {k: v for k, v in token_data.items() if "token" not in k.lower()}
            return token, "user_access_token_oauth_code", safe_token_data
        raise SystemExit("--auth user requires LARK_USER_ACCESS_TOKEN or --oauth-code")

    app_id = os.environ.get("LARK_APP_ID") or os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("LARK_APP_SECRET") or os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("Missing LARK_APP_ID/LARK_APP_SECRET env")
    return get_tenant_access_token(app_id, app_secret), "tenant_access_token", {}


def build_output(url_or_token: str, args: argparse.Namespace) -> dict[str, Any]:
    token = extract_doc_token(url_or_token)
    access_token, auth_source, auth_meta = resolve_access_token(args)
    meta_payload = get_document_meta(token, access_token)
    blocks = list_blocks(token, access_token)
    lines: list[str] = []
    for b in blocks:
        t = block_to_text(b)
        if t:
            lines.append(t)
    title = None
    if meta_payload.get("code") == 0:
        doc = meta_payload.get("data", {}).get("document", {})
        title = redact(doc.get("title") or "") or None
    text = "\n".join(lines)
    return {
        "source": "lark_docx_openapi",
        "auth_source": auth_source,
        "auth_meta_no_tokens": auth_meta,
        "document_token": token,
        "meta_code": meta_payload.get("code"),
        "meta_msg": meta_payload.get("msg"),
        "title": title,
        "block_count": len(blocks),
        "text_line_count": len(lines),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "preview_lines": lines[:80],
        "text": text,
        "raw_block_sample": blocks[:3],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc", nargs="?", help="docx URL or token")
    ap.add_argument("--out", default="")
    ap.add_argument("--auth", choices=["tenant", "user"], default="tenant")
    ap.add_argument("--oauth-code", default="")
    ap.add_argument("--redirect-uri", default="")
    ap.add_argument("--scope", default="docx:document")
    ap.add_argument("--code-verifier", default="")
    ap.add_argument("--make-auth-url", action="store_true")
    args = ap.parse_args()

    if args.make_auth_url:
        app_id = os.environ.get("LARK_APP_ID") or os.environ.get("FEISHU_APP_ID")
        if not app_id:
            raise SystemExit("Missing LARK_APP_ID env")
        if not args.redirect_uri:
            raise SystemExit("--make-auth-url requires --redirect-uri")
        print(json.dumps({"authorize_url": make_authorize_url(app_id, args.redirect_uri, args.scope), "scope": args.scope, "redirect_uri": args.redirect_uri}, ensure_ascii=False, indent=2))
        return 0

    if not args.doc:
        raise SystemExit("doc is required unless --make-auth-url is used")
    try:
        out = build_output(args.doc, args)
    except Exception as e:
        print(json.dumps({"ok": False, "error": safe_error(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "source": out["source"],
        "auth_source": out["auth_source"],
        "document_token": out["document_token"],
        "title": out.get("title"),
        "block_count": out["block_count"],
        "text_line_count": out["text_line_count"],
        "sha256": out.get("sha256"),
        "preview_lines": out["preview_lines"][:20],
        "out": args.out or None,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
