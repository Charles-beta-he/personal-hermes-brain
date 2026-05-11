#!/usr/bin/env python3
"""
agent_protocol.py — 多Agent 结构化通信协议 v2.0.0 (L2)

OpenTelemetry-compatible correlation (chain_id/span_id/parent_span_id),
typed substructures, envelope metadata, version negotiation, SQLite persistence.

用法:
  python3 agent_protocol.py validate <json_file>
  python3 agent_protocol.py wrap --agent-id X --task-id Y --verdict pass [--chain-id Z]
  python3 agent_protocol.py extract <stdin>
  python3 agent_protocol.py extract-strict <stdin>    # old behavior: schema-required
  python3 agent_protocol.py version                    # print SCHEMA_VERSION
"""

import json
import sys
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, TypedDict

# ── 常量 ──
SCHEMA_VERSION = "2.0.0"
SUPPORTED_VERSIONS = {"1.0.0", "2.0.0"}

# ── 自定义异常 ──
class ProtocolError(ValueError):
    """协议验证失败 — 调用方应据此返回错误码"""

# ── TypedDict 子结构 ──
class Artifact(TypedDict, total=False):
    path: str
    sha256: str
    size_bytes: int
    kind: str          # file | url | blob | log | trace

class Suggestion(TypedDict, total=False):
    action: str        # edit | run | review | retry | escalate | skip
    target: str
    rationale: str
    confidence: float

class ErrorDetail(TypedDict, total=False):
    code: str          # machine-readable, e.g. 'TIMEOUT', 'PARSE_FAIL'
    category: str      # transient | permanent | budget | validation | upstream
    message: str
    retryable: bool

class Envelope(TypedDict, total=False):
    chain_id: str           # uuid4 — top-level task correlation
    span_id: str            # uuid4 — this message
    parent_span_id: str     # uuid4 | null — direct producer
    ts_ns: int              # UTC nanoseconds since epoch
    seq: int                # per-(chain_id, agent_id) monotonic counter
    priority: int           # 0-9, default 5
    deadline_ts_ns: int     # hard deadline, 0 = none
    idempotency_key: str    # dedup key
    retry_count: int        # default 0
    content_type: str       # default 'application/vnd.hermes.agent+json'

# ── Schema定义 ──
REQUIRED_FIELDS = ["agent_id", "task_id", "verdict"]
OPTIONAL_FIELDS = [
    "version", "chain_id", "parent_span_id", "model", "summary",
    "cost_usd", "duration_s", "artifacts", "error", "confidence",
    "suggestions", "verification_pattern", "extensions",
    "envelope",          # v2: envelope block
    "ts", "ts_ns",       # ts = second (v1 compat), ts_ns = nanosecond (v2)
    "seq",               # v2: per-chain monotonic seq
]
VALID_VERDICTS = {
    "pass", "fail", "partial", "unknown",
    "pending", "skipped", "timeout"
}
VALID_ARTIFACT_KINDS = {"file", "url", "blob", "log", "trace"}
VALID_SUGGESTION_ACTIONS = {"edit", "run", "review", "retry", "escalate", "skip"}
VALID_ERROR_CATEGORIES = {"transient", "permanent", "budget", "validation", "upstream"}

# ── Per-agent seq counter (thread-safe via threading.local) ──
import threading as _threading
_seq_state = _threading.local()

def _get_seq_counter(chain_id: str) -> int:
    """返回 per-chain_id 的单调递增序号"""
    key = chain_id
    if not hasattr(_seq_state, 'counters'):
        _seq_state.counters = {}
    _seq_state.counters[key] = _seq_state.counters.get(key, 0) + 1
    return _seq_state.counters[key]


def _utc_ns() -> int:
    """UTC 纳秒时间戳"""
    return int(datetime.now(timezone.utc).timestamp() * 1e9)


# ═══════════════════════════════════════════════════════════════
#  validate(msg) — 检测是否为有效协议消息
# ═══════════════════════════════════════════════════════════════

def validate(msg: dict) -> Tuple[bool, str]:
    """
    验证消息是否符合协议。

    返回 (ok, reason)。
    注意：不抛异常——调用方自己决定严格程度。
    """
    if not isinstance(msg, dict):
        return False, "message must be a JSON object"

    version = msg.get("version", "1.0.0")

    # ── 必填字段检查 ──
    for field in REQUIRED_FIELDS:
        if field not in msg:
            return False, f"missing required field: {field}"

    # ── verdict 枚举检查 ──
    verdict = msg.get("verdict", "")
    if verdict not in VALID_VERDICTS:
        return False, f"invalid verdict '{verdict}' — valid: {', '.join(sorted(VALID_VERDICTS))}"

    # ── confidence 范围 ──
    if "confidence" in msg:
        c = msg["confidence"]
        if not isinstance(c, (int, float)) or c < 0 or c > 1:
            return False, f"confidence must be 0-1, got {c}"

    # ── v2: typed substructures ──
    if "artifacts" in msg:
        arts = msg["artifacts"]
        if not isinstance(arts, list):
            return False, "artifacts must be a list"
        for i, a in enumerate(arts):
            if not isinstance(a, dict):
                return False, f"artifacts[{i}] must be an object"
            if "kind" in a and a["kind"] not in VALID_ARTIFACT_KINDS:
                return False, f"artifacts[{i}].kind invalid: {a['kind']}"

    if "suggestions" in msg:
        sugs = msg["suggestions"]
        if not isinstance(sugs, list):
            return False, "suggestions must be a list"
        for i, s in enumerate(sugs):
            if not isinstance(s, dict):
                return False, f"suggestions[{i}] must be an object"
            if "action" in s and s["action"] not in VALID_SUGGESTION_ACTIONS:
                return False, f"suggestions[{i}].action invalid: {s['action']}"

    if "error" in msg:
        err = msg["error"]
        if isinstance(err, dict) and "category" in err:
            if err["category"] not in VALID_ERROR_CATEGORIES:
                return False, f"error.category invalid: {err['category']}"

    return True, "ok"


# ═══════════════════════════════════════════════════════════════
#  try_wrap(msg) — 安全包装，返回 (msg, error)|None
# ═══════════════════════════════════════════════════════════════

def try_wrap(
    agent_id: str,
    task_id: str,
    verdict: str = "unknown",
    **kwargs
) -> Tuple[Optional[dict], Optional[str]]:
    """
    安全包装——验证失败返回 (None, error_msg)，成功返回 (msg, None)。
    不会抛异常。
    """
    try:
        msg = wrap(agent_id=agent_id, task_id=task_id, verdict=verdict, **kwargs)
        return msg, None
    except ProtocolError as e:
        return None, str(e)


# ═══════════════════════════════════════════════════════════════
#  wrap(agent_id, task_id, ...) — 构建协议消息
# ═══════════════════════════════════════════════════════════════

def wrap(
    agent_id: str,
    task_id: str,
    verdict: str = "unknown",
    # ── 元数据 ──
    model: Optional[str] = None,
    summary: Optional[str] = None,
    cost_usd: Optional[float] = None,
    duration_s: Optional[float] = None,
    confidence: Optional[float] = None,
    # ── v2: 关联 ──
    chain_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    # ── v2: 子结构 ──
    artifacts: Optional[List[Dict]] = None,
    suggestions: Optional[List[Dict]] = None,
    error_detail: Optional[Dict] = None,
    # ── v2: 扩展 ──
    verification_pattern: Optional[str] = None,
    extensions: Optional[Dict] = None,
    # ── v2: 信封 ──
    priority: int = 5,
    deadline_ts_ns: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    retry_count: int = 0,
    content_type: str = "application/vnd.hermes.agent+json",
    # ── v1 compat / internal ──
    _parent_id: Optional[str] = None,    # v1 compat alias
    _skip_validate: bool = False,
) -> dict:
    """
    包装一条协议消息。

    Raises:
        ProtocolError: 验证失败时抛出
    """
    # 自动生成/处理 chain_id 和 parent_span_id
    _cid = chain_id or _parent_id or str(uuid.uuid4())
    _psid = parent_span_id or _parent_id or None
    span_id = str(uuid.uuid4())
    ts_ns_val = _utc_ns()
    seq_val = _get_seq_counter(_cid)

    msg = {
        "version": SCHEMA_VERSION,
        "agent_id": agent_id,
        "task_id": task_id,
        "verdict": verdict,
        # ── v2 时间戳 ──
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ts_ns": ts_ns_val,
        "seq": seq_val,
    }

    # ── 关联 ID ──
    if chain_id:
        msg["chain_id"] = chain_id
    elif _parent_id:
        msg["chain_id"] = _parent_id   # v1 compat: parent_id → chain_id
    if parent_span_id:
        msg["parent_span_id"] = parent_span_id
    elif _parent_id:
        msg["parent_span_id"] = _parent_id

    # ── 元数据 (使用 is not None 而非 truthy) ──
    if model is not None and model != "":
        msg["model"] = model
    if summary is not None and summary != "":
        msg["summary"] = summary
    if cost_usd is not None:
        msg["cost_usd"] = cost_usd
    if duration_s is not None:
        msg["duration_s"] = duration_s
    if confidence is not None:
        msg["confidence"] = round(confidence, 4)
    if verification_pattern is not None:
        msg["verification_pattern"] = verification_pattern

    # ── v2: 子结构 ──
    if artifacts:
        msg["artifacts"] = artifacts
    if suggestions:
        msg["suggestions"] = suggestions
    if error_detail:
        # 兼容旧版 error=str
        msg["error"] = error_detail

    # ── v2: 扩展 ──
    if extensions:
        msg["extensions"] = extensions

    # ── v2: envelope block ──
    envelope: Dict[str, Any] = {}
    # 确保 msg 顶层也有 chain_id（auto-gen 或传入的）
    if not msg.get("chain_id"):
        msg["chain_id"] = _cid
    envelope["chain_id"] = _cid
    envelope["span_id"] = span_id
    if _psid:
        envelope["parent_span_id"] = _psid
    envelope["ts_ns"] = ts_ns_val
    envelope["seq"] = seq_val
    if priority != 5:
        envelope["priority"] = priority
    if deadline_ts_ns is not None:
        envelope["deadline_ts_ns"] = deadline_ts_ns
    if idempotency_key is not None:
        envelope["idempotency_key"] = idempotency_key
    if retry_count != 0:
        envelope["retry_count"] = retry_count
    if content_type != "application/vnd.hermes.agent+json":
        envelope["content_type"] = content_type
    msg["envelope"] = envelope

    # ── 验证 ──
    if not _skip_validate:
        ok, reason = validate(msg)
        if not ok:
            raise ProtocolError(f"validation failed: {reason}")

    return msg


# ═══════════════════════════════════════════════════════════════
#  extract(text) — 从文本提取协议消息 (灵活模式)
# ═══════════════════════════════════════════════════════════════

def _find_json_objects(text: str) -> List[dict]:
    """从文本中查找所有 JSON 对象/数组"""
    results = []
    # 尝试直接解析整体
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            results.append(obj)
    except (json.JSONDecodeError, TypeError):
        pass

    # 从 markdown 代码块提取
    for match in re.finditer(r'```(?:json)?\s*\n(.*?)```', text, re.DOTALL):
        try:
            obj = json.loads(match.group(1))
            if isinstance(obj, dict):
                results.append(obj)
        except (json.JSONDecodeError, TypeError):
            continue

    return results


def extract(text: str, strict: bool = False) -> Optional[dict]:
    """
    从子Agent输出中提取协议消息。

    灵活模式 (strict=False, 默认):
      返回任意有效 JSON dict——不要求完整协议字段。
      适用场景：reviewer 输出 {verdict, patches, summary} 等非完全协议格式。

    严格模式 (strict=True):
      只返回通过 validate() 的消息。
      等价于旧版 extract() 行为。
    """
    for obj in _find_json_objects(text):
        if not strict:
            return obj
        ok, _ = validate(obj)
        if ok:
            return obj
    return None


def extract_strict(text: str) -> Optional[dict]:
    """严格模式 extract() — 必须通过 validate()"""
    return extract(text, strict=True)


# ═══════════════════════════════════════════════════════════════
#  v1→v2 迁移
# ═══════════════════════════════════════════════════════════════

def migrate_v1_to_v2(msg: dict) -> dict:
    """将 v1 消息就地升级为 v2"""
    if msg.get("version", "1.0.0") != "1.0.0":
        return msg

    # v1 'parent_id' → v2 'chain_id' + 'parent_span_id'
    if "parent_id" in msg and msg["parent_id"]:
        msg["chain_id"] = msg.pop("parent_id")

    # v1 error=str → v2 error={code, message}
    if "error" in msg and isinstance(msg["error"], str):
        msg["error"] = {
            "code": "UNKNOWN",
            "category": "permanent",
            "message": msg["error"],
            "retryable": False,
        }

    msg["version"] = "2.0.0"
    return msg


# ═══════════════════════════════════════════════════════════════
#  emit(msg) — 持久化到 protocol_messages 表
# ═══════════════════════════════════════════════════════════════

def emit(msg: dict, db_path: Optional[str] = None) -> bool:
    """
    将协议消息写入 protocol_messages 持久化表。

    db_path 默认 ~/.hermes/route_outcomes.db (与 L0 共享)。
    返回 True 表示写入成功。
    """
    import sqlite3
    # Honor explicit db_path arg, then test-injection env, then default.
    db = (
        db_path
        or os.environ.get("HERMES_PROTOCOL_DB_PATH")
        or os.environ.get("HERMES_ROUTE_DB_PATH")
        or os.path.expanduser("~/.hermes/route_outcomes.db")
    )
    db = os.path.expanduser(db)

    try:
        conn = sqlite3.connect(db)
        # 确保表存在
        conn.execute("""
            CREATE TABLE IF NOT EXISTS protocol_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id TEXT NOT NULL,
                span_id TEXT UNIQUE,
                parent_span_id TEXT,
                agent_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                verdict TEXT NOT NULL,
                model TEXT,
                ts_ns INTEGER NOT NULL,
                seq INTEGER DEFAULT 0,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (chain_id) REFERENCES protocol_messages(chain_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pm_chain_ts
            ON protocol_messages(chain_id, ts_ns)
        """)

        envelope = msg.get("envelope", {})
        payload = json.dumps(msg, ensure_ascii=False)

        conn.execute(
            """INSERT OR REPLACE INTO protocol_messages
               (chain_id, span_id, parent_span_id, agent_id, task_id,
                verdict, model, ts_ns, seq, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                envelope.get("chain_id", msg.get("chain_id", "unknown")),
                envelope.get("span_id", "unknown"),
                envelope.get("parent_span_id"),
                msg.get("agent_id", "unknown"),
                msg.get("task_id", "unknown"),
                msg.get("verdict", "unknown"),
                msg.get("model"),
                msg.get("ts_ns", 0),
                msg.get("seq", 0),
                payload,
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[agent_protocol] emit failed: {e}", file=sys.stderr)
        return False


# ═══════════════════════════════════════════════════════════════
#  query(chain_id) — 查询链上所有消息
# ═══════════════════════════════════════════════════════════════

def query_messages(chain_id: str, db_path: Optional[str] = None,
                   limit: int = 100) -> List[dict]:
    """查询指定 chain 的所有协议消息（按 ts_ns 排序）"""
    import sqlite3
    db = (
        db_path
        or os.environ.get("HERMES_PROTOCOL_DB_PATH")
        or os.environ.get("HERMES_ROUTE_DB_PATH")
        or os.path.expanduser("~/.hermes/route_outcomes.db")
    )
    db = os.path.expanduser(db)
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM protocol_messages WHERE chain_id = ? "
            "ORDER BY ts_ns ASC LIMIT ?",
            (chain_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

def cli():
    import argparse
    parser = argparse.ArgumentParser(
        description=f"Agent Protocol v{SCHEMA_VERSION} — 多Agent通信协议"
    )
    sub = parser.add_subparsers(dest="cmd")

    # ── validate ──
    val = sub.add_parser("validate", help="验证协议消息")
    val.add_argument("file", help="JSON 文件路径")

    # ── wrap ──
    wr = sub.add_parser("wrap", help="包装协议消息")
    wr.add_argument("--agent-id", required=True)
    wr.add_argument("--task-id", required=True)
    wr.add_argument("--verdict", default="unknown")
    wr.add_argument("--model", default=None)
    wr.add_argument("--summary", default=None)
    wr.add_argument("--cost-usd", type=float, default=None)
    wr.add_argument("--duration-s", type=float, default=None)
    wr.add_argument("--confidence", type=float, default=None)
    wr.add_argument("--chain-id", default=None)
    wr.add_argument("--parent-span-id", default=None)
    wr.add_argument("--verification-pattern", default=None)
    wr.add_argument("--artifacts", default="[]", help="JSON array of artifact objects")
    wr.add_argument("--suggestions", default="[]", help="JSON array of suggestion objects")
    wr.add_argument("--error-detail", default=None, help="JSON error object")
    wr.add_argument("--extensions", default=None, help="JSON extensions object")
    wr.add_argument("--priority", type=int, default=5)
    wr.add_argument("--deadline-ts-ns", type=int, default=None)
    wr.add_argument("--idempotency-key", default=None)
    wr.add_argument("--retry-count", type=int, default=0)
    wr.add_argument("--emit", action="store_true", help="Emit to persistence after wrap")

    # ── extract (灵活) ──
    ex = sub.add_parser("extract", help="从 stdin 提取协议消息 (灵活)")
    ex.add_argument("--strict", action="store_true", help="严格模式：必须通过 validate()")

    # ── extract-strict (兼容旧版) ──
    exs = sub.add_parser("extract-strict", help="从 stdin 提取协议消息 (严格)")

    # ── version ──
    sub.add_parser("version", help="打印协议版本")

    # ── query ──
    q = sub.add_parser("query", help="查询 chain 消息")
    q.add_argument("chain_id", help="Chain ID")
    q.add_argument("--limit", type=int, default=100)

    # ── migrate ──
    mig = sub.add_parser("migrate", help="v1→v2 迁移")
    mig.add_argument("file", help="v1 JSON 文件")

    args = parser.parse_args()

    try:
        if args.cmd == "validate":
            with open(args.file) as f:
                msg = json.load(f)
            ok, reason = validate(msg)
            if ok:
                print(f"✓ Valid v{msg.get('version', '?')}: "
                      f"agent={msg['agent_id']} task={msg['task_id']} "
                      f"verdict={msg['verdict']}")
            else:
                print(f"✗ Invalid: {reason}", file=sys.stderr)
                sys.exit(1)

        elif args.cmd == "wrap":
            artifacts = json.loads(args.artifacts) if args.artifacts else []
            suggestions = json.loads(args.suggestions) if args.suggestions else []
            error_detail = json.loads(args.error_detail) if args.error_detail else None
            extensions = json.loads(args.extensions) if args.extensions else None

            msg = wrap(
                agent_id=args.agent_id,
                task_id=args.task_id,
                verdict=args.verdict,
                model=args.model,
                summary=args.summary,
                cost_usd=args.cost_usd,
                duration_s=args.duration_s,
                confidence=args.confidence,
                chain_id=args.chain_id,
                parent_span_id=args.parent_span_id,
                artifacts=artifacts or None,
                suggestions=suggestions or None,
                error_detail=error_detail or None,
                verification_pattern=args.verification_pattern,
                extensions=extensions or None,
                priority=args.priority,
                deadline_ts_ns=args.deadline_ts_ns,
                idempotency_key=args.idempotency_key,
                retry_count=args.retry_count,
            )
            print(json.dumps(msg, indent=2, ensure_ascii=False))
            if args.emit:
                emit(msg)

        elif args.cmd == "extract":
            text = sys.stdin.read()
            msg = extract(text, strict=args.strict)
            if msg:
                print(json.dumps(msg, indent=2, ensure_ascii=False))
            else:
                print("No valid JSON found in input", file=sys.stderr)
                sys.exit(1)

        elif args.cmd == "extract-strict":
            text = sys.stdin.read()
            msg = extract_strict(text)
            if msg:
                print(json.dumps(msg, indent=2, ensure_ascii=False))
            else:
                print("No valid protocol message found", file=sys.stderr)
                sys.exit(1)

        elif args.cmd == "version":
            print(SCHEMA_VERSION)

        elif args.cmd == "query":
            rows = query_messages(args.chain_id, limit=args.limit)
            if rows:
                print(json.dumps(rows, indent=2, ensure_ascii=False))
                print(f"  ({len(rows)} messages)", file=sys.stderr)
            else:
                print(f"No messages for chain {args.chain_id}", file=sys.stderr)

        elif args.cmd == "migrate":
            with open(args.file) as f:
                msg = json.load(f)
            v2_msg = migrate_v1_to_v2(msg)
            print(json.dumps(v2_msg, indent=2, ensure_ascii=False))

        else:
            parser.print_help()

    except ProtocolError as e:
        print(f"✗ Protocol error: {e}", file=sys.stderr)
        sys.exit(2)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    cli()
