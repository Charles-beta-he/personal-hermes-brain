#!/usr/bin/env python3
"""
Hermes post-update self-check: detect if vendor-code patches have been
overwritten by `hermes update`, re-apply if needed, report fixed-by-upstream.

Usage:
    python3 ~/.hermes/scripts/post-update-check.py [--fix]

Without --fix: dry-run mode — only report what needs fixing.
With    --fix: apply patches when needed.
"""

import re
import json
import os
import sys
import subprocess
import pathlib

LEGACY_HERMES_HOME = pathlib.Path(__file__).resolve().parent.parent
HERMES_ROOT = str(LEGACY_HERMES_HOME / "hermes-agent")
OVERLAY_REGISTRY = str(LEGACY_HERMES_HOME / "overlays" / "hermes-local-enhancements.json")
CHECKS = []

def register(name, file_rel, pattern_needle, fix_desc, fix_func=None):
    """Register a check. fix_func(path) applies the fix, returns bool."""
    CHECKS.append({
        "name": name,
        "path": os.path.join(HERMES_ROOT, file_rel),
        "needle": pattern_needle,
        "fix_desc": fix_desc,
        "fix_func": fix_func,
    })


# ── Check 1: chat_completions.py truthiness bug ─────────────────
def _fix_chat_completions_truthiness(path):
    with open(path, "r") as f:
        content = f.read()
    old = "if reasoning_content:\n            provider_data[\"reasoning_content\"] = reasoning_content"
    new = "if reasoning_content is not None:\n            provider_data[\"reasoning_content\"] = reasoning_content"
    if old in content:
        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        return True
    return False

register(
    "chat_completions_truthiness",
    "agent/transports/chat_completions.py",
    r'if reasoning_content:\s+provider_data\["reasoning_content"\]',
    "if reasoning_content: → if reasoning_content is not None: (empty string not stored)",
    _fix_chat_completions_truthiness,
)


# ── Check 2: _copy_reasoning_content_for_api step ordering ──────
def _fix_step_ordering(path):
    """Reorder _copy_reasoning_content_for_api so reasoning promotion
    happens BEFORE the DeepSeek/Kimi empty-string fallback.

    Strategy: swap two adjacent blocks in the method body using
    direct text replacement. Each block is identified by its comment header.
    """
    with open(path, "r") as f:
        content = f.read()

    # Detect order via comment markers
    has_promote_as_step2 = "# 2. Healthy session: promote 'reasoning'" in content
    has_deepseek_as_step3 = "# 3. DeepSeek / Kimi thinking mode: tool-call" in content
    has_deepseek_as_step2 = "# 2. DeepSeek / Kimi thinking mode: tool-call" in content
    has_promote_as_step3 = "# 3. Healthy session: promote 'reasoning'" in content

    if has_promote_as_step2 and has_deepseek_as_step3:
        return False  # Already correct order

    if has_deepseek_as_step2 and has_promote_as_step3:
        # Swap: move the promote block before the needs_empty_reasoning block
        # Use the exact text replacement
        old_order_block = """        # 2. DeepSeek / Kimi thinking mode: tool-call turns that lack
        # reasoning_content are "poisoned history" — a prior provider (MiniMax,
        # etc.) left them empty. DeepSeek returns HTTP 400 if reasoning_content
        # is absent on replay; inject "" to satisfy the provider's requirement
        # without forwarding any cross-provider reasoning content.
        needs_empty_reasoning = (
            source_msg.get("tool_calls")
            and (
                self._needs_kimi_tool_reasoning()
                or self._needs_deepseek_tool_reasoning()
            )
        )
        if needs_empty_reasoning:
            api_msg["reasoning_content"] = ""
            return

        # 3. Healthy session: promote 'reasoning' field to 'reasoning_content'
        # for providers that use the internal 'reasoning' key.
        normalized_reasoning = source_msg.get("reasoning")
        if isinstance(normalized_reasoning, str) and normalized_reasoning:
            api_msg["reasoning_content"] = normalized_reasoning
            return"""

        new_order_block = """        # 2. Healthy session: promote 'reasoning' field to 'reasoning_content'
        # for providers that use the internal 'reasoning' key.
        normalized_reasoning = source_msg.get("reasoning")
        if isinstance(normalized_reasoning, str) and normalized_reasoning:
            api_msg["reasoning_content"] = normalized_reasoning
            return

        # 3. DeepSeek / Kimi thinking mode: tool-call turns that lack
        # reasoning_content are "poisoned history" — a prior provider (MiniMax,
        # etc.) left them empty. DeepSeek returns HTTP 400 if reasoning_content
        # is absent on replay; inject "" to satisfy the provider's requirement
        # without forwarding any cross-provider reasoning content.
        needs_empty_reasoning = (
            source_msg.get("tool_calls")
            and (
                self._needs_kimi_tool_reasoning()
                or self._needs_deepseek_tool_reasoning()
            )
        )
        if needs_empty_reasoning:
            api_msg["reasoning_content"] = ""
            return"""

        if old_order_block in content:
            content = content.replace(old_order_block, new_order_block)
            with open(path, "w") as f:
                f.write(content)
            return True

    return False


register(
    "reasoning_content_step_ordering",
    "run_agent.py",
    r'# 2\. DeepSeek / Kimi thinking mode.*?needs_empty_reasoning',
    "Reposition 'reasoning' promotion before DeepSeek empty-string fallback",
    _fix_step_ordering,
)



# ── Check 3a: MemoryManager provider registration rollback ─────────────
def _fix_memory_manager_provider_rollback(path):
    with open(path, "r") as f:
        content = f.read()

    old = """        self._providers.append(provider)

        # Index tool names → provider for routing
        for schema in provider.get_tool_schemas():
            tool_name = schema.get(\"name\", \"\")
            if tool_name and tool_name not in self._tool_to_provider:
                self._tool_to_provider[tool_name] = provider
            elif tool_name in self._tool_to_provider:
                logger.warning(
                    \"Memory tool name conflict: '%s' already registered by %s, \"
                    \"ignoring from %s\",
                    tool_name,
                    self._tool_to_provider[tool_name].name,
                    provider.name,
                )

        logger.info(
            \"Memory provider '%s' registered (%d tools)\",
            provider.name,
            len(provider.get_tool_schemas()),
        )"""

    new = """        self._providers.append(provider)

        # Index tool names → provider for routing
        # If get_tool_schemas() fails (dirty/uninitialized provider),
        # roll back the registration to prevent global state pollution.
        try:
            schemas = list(provider.get_tool_schemas())
            for schema in schemas:
                tool_name = schema.get(\"name\", \"\")
                if tool_name and tool_name not in self._tool_to_provider:
                    self._tool_to_provider[tool_name] = provider
                elif tool_name in self._tool_to_provider:
                    logger.warning(
                        \"Memory tool name conflict: '%s' already registered by %s, \"
                        \"ignoring from %s\",
                        tool_name,
                        self._tool_to_provider[tool_name].name,
                        provider.name,
                    )
        except Exception:
            logger.error(
                \"Memory provider '%s' failed get_tool_schemas(), rolling back registration\",
                provider.name,
            )
            self._providers.remove(provider)
            if not is_builtin:
                self._has_external = False
            return

        logger.info(
            \"Memory provider '%s' registered (%d tools)\",
            provider.name,
            len(schemas),
        )"""

    if old in content:
        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        return True
    return False

register(
    "memory_manager_provider_rollback",
    "agent/memory_manager.py",
    r'self\._providers\.append\(provider\)\s+# Index tool names → provider for routing\s+for schema in provider\.get_tool_schemas\(\):',
    "Wrap provider.get_tool_schemas() with rollback so failed memory providers do not pollute global state",
    _fix_memory_manager_provider_rollback,
)


# ── Check 3b: prompt_builder memory ghost prevention ───────────────────
def _fix_prompt_builder_ghost_prevention(path):
    with open(path, "r") as f:
        content = f.read()
    if "GHOST PREVENTION: Never save WIP status" in content:
        return False
    old = """    \"Imperative phrasing gets re-read as a directive in later sessions and can \"
    \"cause repeated work or override the user's current request. Procedures and \"
    \"workflows belong in skills, not memory.\"
)"""
    new = """    \"Imperative phrasing gets re-read as a directive in later sessions and can \"
    \"cause repeated work or override the user's current request. Procedures and \"
    \"workflows belong in skills, not memory.\\n\"
    \"GHOST PREVENTION: Never save WIP status, session-local state, or \\\"this session\\\" \"
    \"context to memory. These become stale ghosts after context compression — \"
    \"they survive as past-tense entries that future sessions treat as current. \"
    \"Before memory.write, ask: \\\"Will this fact still be true in 10 sessions?\\\" \"
    \"If no, don't save it.\"
)"""
    if old in content:
        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        return True
    return False

register(
    "prompt_builder_ghost_prevention",
    "agent/prompt_builder.py",
    r'workflows belong in skills, not memory\."\s*\)',
    "Add durable-memory ghost prevention guidance to MEMORY_GUIDANCE",
    _fix_prompt_builder_ghost_prevention,
)


# ── Check 3c: context compressor anti-ghost compaction rules ────────────
def _fix_context_compressor_anti_ghost(path):
    with open(path, "r") as f:
        content = f.read()
    if "CRITICAL — ANTI-GHOST RULES:" in content:
        return False
    old = '''Update the summary using this exact structure. PRESERVE all existing information that is still relevant. ADD new completed actions to the numbered list (continue numbering). Move items from "In Progress" to "Completed Actions" when done. Move answered questions to "Resolved Questions". Update "Active State" to reflect current state. Remove information only if it is clearly obsolete. CRITICAL: Update "## Active Task" to reflect the user's most recent unfulfilled request — this is the most important field for task continuity.

{_template_sections}"""'''
    new = '''Update the summary using this exact structure. PRESERVE all existing information that is still relevant. ADD new completed actions to the numbered list (continue numbering). Move items from "In Progress" to "Completed Actions" when done. Move answered questions to "Resolved Questions". Update "Active State" to reflect current state. Remove information only if it is clearly obsolete. CRITICAL: Update "## Active Task" to reflect the user's most recent unfulfilled request — this is the most important field for task continuity.

CRITICAL — ANTI-GHOST RULES:
1. REMOVE any numeric counters or stats that refer to memory usage, token counts, or session-local state — these are ALWAYS stale
2. REMOVE any sentence that says "This session..." or "Currently working on..." — rewrite to describe what was DONE, not what "is" happening
3. TIMESTAMPS from the previous summary are ALWAYS outdated — drop them unless they refer to permanent external events
4. If the PREVIOUS SUMMARY describes work now COMPLETE (confirmed by new turns), move it to "Completed Actions"
5. NEVER carry forward "Memory at" or system metrics — they are now misleading

{_template_sections}"""'''
    if old in content:
        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        return True
    return False

register(
    "context_compressor_anti_ghost",
    "agent/context_compressor.py",
    r'(?s)^(?!.*CRITICAL — ANTI-GHOST RULES:).*Update the summary using this exact structure\..*?\{_template_sections\}"""',
    "Add anti-ghost rules to incremental context compression prompt",
    _fix_context_compressor_anti_ghost,
)


# ── Check 3d: MCP RPC timeout guard (all operations) ─────────────────
def _check_mcp_rpc_timeout_guard(path):
    with open(path, "r") as f:
        content = f.read()
    if "async def _mcp_rpc_call(" in content and "_MCP_SAFETY_NET_SEC" in content:
        return False  # No issue — helper exists
    # Can't auto-fix a 6-location patch via regex. Report and suggest manual re-apply.
    return False

register(
    "mcp_rpc_timeout_guard",
    "tools/mcp_tool.py",
    r'(?s)async def _call\(\):\s+async with server\._rpc_lock:\s+result = await server\.session\.call_tool',
    "Centralize MCP RPC lock+timeout in _mcp_rpc_call helper (all 5 operations). "
    "If missing after upgrade, re-apply from backup or run apply-mcp-timeout-patch.py",
    _check_mcp_rpc_timeout_guard,
)


# ── Check 3e: macOS launchd gateway nofile limit ────────────────────────
def _fix_launchd_gateway_nofile_limit(path):
    with open(path, "r") as f:
        content = f.read()
    if "<key>SoftResourceLimits</key>" in content and "<key>NumberOfFiles</key>" in content:
        return False

    old = """    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>"""
    new = """    <key>RunAtLoad</key>
    <true/>

    <key>SoftResourceLimits</key>
    <dict>
        <key>NumberOfFiles</key>
        <integer>4096</integer>
    </dict>

    <key>HardResourceLimits</key>
    <dict>
        <key>NumberOfFiles</key>
        <integer>8192</integer>
    </dict>
    
    <key>KeepAlive</key>"""
    if old in content:
        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        return True
    return False

register(
    "launchd_gateway_nofile_limit",
    "hermes_cli/gateway.py",
    r'(?s)<key>RunAtLoad</key>\s*<true/>\s*<key>KeepAlive</key>',
    "Add launchd SoftResourceLimits/HardResourceLimits NumberOfFiles so gateway does not inherit macOS soft nofile=256",
    _fix_launchd_gateway_nofile_limit,
)


# ── Check 3f: gateway FD watchdog governance ─────────────────────────
WATCHDOG_FILE = os.path.expanduser("~/.hermes/scripts/gateway_fd_watchdog.py")

def check_gateway_fd_watchdog():
    """Verify the update-safe FD watchdog exists and returns a strict sample."""
    if not os.path.exists(WATCHDOG_FILE):
        return f"MISSING: {WATCHDOG_FILE}"
    if not os.access(WATCHDOG_FILE, os.X_OK):
        return f"MISSING_EXECUTABLE_BIT: {WATCHDOG_FILE}"
    compile_result = subprocess.run(
        [sys.executable, "-m", "py_compile", WATCHDOG_FILE],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if compile_result.returncode != 0:
        return f"PY_COMPILE_FAILED: {compile_result.stderr.strip()[:300]}"
    sample_result = subprocess.run(
        [sys.executable, WATCHDOG_FILE, "--json", "--no-record"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if sample_result.returncode not in (0, 2):
        return f"SAMPLE_FAILED rc={sample_result.returncode}: {(sample_result.stderr or sample_result.stdout).strip()[:300]}"
    try:
        sample = json.loads(sample_result.stdout)
    except Exception as exc:
        return f"SAMPLE_JSON_INVALID: {exc}"
    required = {"schema_version", "sampled_at", "status", "actions", "fd", "limits"}
    missing = sorted(required - set(sample))
    if missing:
        return f"SAMPLE_MISSING_KEYS: {missing}"
    actions = sample.get("actions") or {}
    if actions.get("auto_restart") is not False or actions.get("auto_kill") is not False:
        return "UNSAFE_ACTIONS_ENABLED"
    return f"OK ({sample.get('status')} fd={(sample.get('fd') or {}).get('numeric_fd_count')})"

register(
    "gateway_fd_watchdog",
    ".",
    None,
    "Verify update-safe Gateway FD watchdog exists, is executable, returns strict JSON, and does not auto-restart",
)


# ── Check 3: remove_duplicate_project_desc (memory) ─────────────
MEMORY_FILE = os.path.expanduser("~/.hermes/memories/MEMORY.md")
def check_memory_ghosts():
    """Check MEMORY.md for known ghost patterns. Not auto-fixed."""
    if not os.path.exists(MEMORY_FILE):
        return "MISSING"
    with open(MEMORY_FILE) as f:
        content = f.read()
    ghosts = []
    if "v1.4.8" in content:
        ghosts.append("version number (v1.4.8)")
    if "动效系统优化" in content and "无改进" in content:
        ghosts.append("completed animation optimization summary")
    if "Discover 页面" in content and "已上线" in content:
        ghosts.append("past-tense 'Discover page launched'")
    if ghosts:
        return f"GHOSTS DETECTED: {', '.join(ghosts)}"
    return "OK"
register(
    "memory_ghosts",
    ".",  # dummy
    None,
    "Check MEMORY.md for past-tense ghost entries (manual fix)",
)


# ── Check 5: skill tracking (Axis 5) ──────────────────────────
USAGE_FILE = os.path.expanduser("~/.hermes/skills/steward/skill_usage.json")
TRACKER_PLUGIN_DIR = os.path.expanduser("~/.hermes/plugins/skill-tracker")

def check_skill_tracking():
    """Check if skill tracking is operational."""
    plugin_ok = os.path.exists(os.path.join(TRACKER_PLUGIN_DIR, "__init__.py"))
    usage_ok = os.path.exists(USAGE_FILE)
    if not plugin_ok:
        return "NO_PLUGIN"
    if not usage_ok:
        return "INSTALLED_NO_DATA_YET"
    try:
        with open(USAGE_FILE) as f:
            data = json.load(f)
        total_loads = sum(len(v) for v in data.values())
        skills_loaded = len(data)
        return f"OK ({skills_loaded} skills, ~{total_loads} loads)"
    except Exception as e:
        return f"ERROR: {e}"

register(
    "skill_tracking",
    ".",  # dummy
    None,
    "Check skill usage tracking plugin + data",
)
STEWARD_STATE = os.path.expanduser("~/.hermes/skills/steward/state.json")

def check_steward_liveness():
    import json
    if not os.path.exists(STEWARD_STATE):
        return "MISSING"
    try:
        with open(STEWARD_STATE) as f:
            state = json.load(f)
        triggers = state.get("rule_triggers", {})
        active = {k for k, v in triggers.items() if v and v > 0}
        if not active:
            return "DORMANT (0 rules triggered)"
        return f"OK ({len(active)} rules active: {active})"
    except Exception as e:
        return f"ERROR: {e}"
register(
    "steward_liveness",
    ".",  # dummy
    None,
    "Check steward rule_triggers are non-zero (needs cron history)",
)


# ── Check 7: skill quality (test-prompts coverage) ────────────
SKILLS_DIR = os.path.expanduser("~/.hermes/skills")

def check_skill_quality():
    """Check which skills are missing test-prompts.json."""
    if not os.path.exists(SKILLS_DIR):
        return "MISSING"
    total = 0
    missing_tests = []
    for root, dirs, files in os.walk(SKILLS_DIR):
        if "SKILL.md" in files:
            total += 1
            # Check if it's an alias
            sk_path = os.path.join(root, "SKILL.md")
            try:
                with open(sk_path) as f:
                    first_lines = f.read(200)
                if "alias: true" in first_lines:
                    continue  # skip aliases
            except Exception:
                pass
            if "test-prompts.json" not in files:
                rel = os.path.relpath(root, SKILLS_DIR)
                missing_tests.append(rel)
    if not missing_tests:
        return f"OK ({total} skills, all have tests)"
    return f"MISSING ({len(missing_tests)}/{total} no tests: {', '.join(missing_tests[:5])})"

register(
    "skill_quality",
    ".",
    None,
    "Check which skills lack test-prompts.json",
)


# ═══════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════


def _run_cmd(cmd, cwd=None, timeout=120):
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return proc.returncode, (proc.stdout or "").strip()
    except Exception as exc:
        return 99, str(exc)


def _git(args, timeout=30):
    return _run_cmd(["git", *args], cwd=HERMES_ROOT, timeout=timeout)


def check_private_repo_governance():
    """Guard the private Hermes code-repo topology and runtime-state boundary.

    This check makes the first-governance landing durable: future self-checks
    should catch regressions where origin is accidentally pointed back at the
    official repo, upstream disappears, governance docs are lost, or live runtime
    state leaks into the source checkout again.
    """
    if not os.path.isdir(os.path.join(HERMES_ROOT, ".git")):
        return "BROKEN (Hermes root is not a git checkout)"

    issues = []
    rc, branch = _git(["branch", "--show-current"])
    if rc != 0:
        issues.append("cannot read current branch")
    elif branch and not (branch == "private/main" or branch.startswith("integrate/")):
        issues.append(f"unexpected branch {branch!r}; expected private/main or integrate/*")

    rc, origin = _git(["remote", "get-url", "origin"])
    if rc != 0:
        issues.append("missing origin remote")
    elif "Charles-beta-he/hermes-agent-private" not in origin:
        issues.append(f"origin is not private Hermes repo: {origin}")

    rc, upstream = _git(["remote", "get-url", "upstream"])
    if rc != 0:
        issues.append("missing upstream remote")
    elif "NousResearch/hermes-agent" not in upstream:
        issues.append(f"upstream is not official Hermes repo: {upstream}")

    for ref in ("private/main", "backup/landing-20260518-203325"):
        rc, _ = _git(["rev-parse", "--verify", ref])
        if rc != 0:
            issues.append(f"missing local ref {ref}")

    required_docs = [
        "docs/private/overlay-registry.md",
        "docs/private/upgrade-sop.md",
        "docs/private/stable-points.md",
    ]
    missing_docs = [rel for rel in required_docs if not os.path.exists(os.path.join(HERMES_ROOT, rel))]
    if missing_docs:
        issues.append("missing governance docs: " + ", ".join(missing_docs))

    forbidden = ["state.db", ".hermes"]
    leaked = [rel for rel in forbidden if os.path.exists(os.path.join(HERMES_ROOT, rel))]
    if leaked:
        issues.append("runtime state leaked into source checkout: " + ", ".join(leaked))

    gitignore = os.path.join(HERMES_ROOT, ".gitignore")
    try:
        ignore_text = pathlib.Path(gitignore).read_text(encoding="utf-8")
    except Exception as exc:
        issues.append(f"cannot read .gitignore: {exc}")
    else:
        for needle in ("state.db", ".hermes/", "*.db-wal", "*.db-shm"):
            if needle not in ignore_text:
                issues.append(f".gitignore missing {needle}")

    if issues:
        return "BROKEN (" + "; ".join(issues[:8]) + (f"; +{len(issues)-8} more" if len(issues) > 8 else "") + ")"

    return f"OK (branch={branch or '<detached>'}, origin=private, upstream=official, docs=present, runtime-clean)"


def check_overlay_registry():
    if not os.path.exists(OVERLAY_REGISTRY):
        return f"MISSING overlay registry: {OVERLAY_REGISTRY}"
    try:
        data = json.loads(open(OVERLAY_REGISTRY, "r", encoding="utf-8").read())
    except Exception as exc:
        return f"BAD overlay registry JSON: {exc}"

    overlays = data.get("overlays") or []
    if not overlays:
        return "MISSING overlay registry entries"

    required = ["id", "kind", "artifact_paths", "verification", "upstream_absorb_when"]
    schema_issues = []
    missing = []
    for overlay in overlays:
        overlay_id = overlay.get("id") or "<missing-id>"
        for key in required:
            value = overlay.get(key)
            if value in (None, "") or value == []:
                schema_issues.append(f"{overlay_id}:{key}")
        for relpath in overlay.get("artifact_paths") or []:
            abspath = os.path.join(HERMES_ROOT, relpath)
            if not os.path.exists(abspath):
                missing.append(relpath)

    if schema_issues:
        return "BAD overlay schema: " + ", ".join(schema_issues[:12])
    if missing:
        return "MISSING overlay artifacts: " + ", ".join(sorted(set(missing))[:12])

    verified = sum(1 for overlay in overlays if overlay.get("verification"))
    return f"OK ({len(overlays)} overlays registered, {verified} with verification commands)"


def check_conductor_runtime_productization():
    """Regression gate for default-off conductor runtime scaffolding."""
    root = HERMES_ROOT
    required = [
        os.path.join(root, "agent", "conductor_runtime.py"),
        os.path.join(root, "tests", "agent", "test_conductor_runtime.py"),
        os.path.expanduser("~/.hermes/scripts/hermes_conductor_runtime.py"),
        os.path.expanduser("~/.hermes/scripts/hermes_background_task_worker.py"),
        os.path.expanduser("~/.hermes/config/model_profiles.yaml"),
    ]
    missing = [path for path in required if not os.path.exists(path)]
    if missing:
        return "BROKEN (missing conductor runtime files: " + ", ".join(os.path.basename(x) for x in missing) + ")"

    py = os.path.join(root, ".venv", "bin", "python")
    if not os.path.exists(py):
        py = sys.executable

    rc, out = _run_cmd([
        py, "-m", "py_compile",
        "agent/conductor_runtime.py",
        "agent/conversation_loop.py",
        "tests/agent/test_conductor_runtime.py",
        os.path.expanduser("~/.hermes/scripts/hermes_conductor_runtime.py"),
        os.path.expanduser("~/.hermes/scripts/hermes_background_task_worker.py"),
    ], cwd=root)
    if rc != 0:
        return "BROKEN (py_compile failed: " + out[-500:] + ")"

    rc, _ = _run_cmd([py, "-m", "pytest", "--version"], cwd=root, timeout=30)
    if rc == 0:
        rc, out = _run_cmd([py, "-m", "pytest", "tests/agent/test_conductor_runtime.py", "-q"], cwd=root)
        runner = "pytest"
    else:
        manual = """
import sys
sys.path.insert(0,'.')
from tests.agent import test_conductor_runtime as t
for name in sorted(dir(t)):
    if name.startswith('test_'):
        getattr(t, name)()
print('manual-tests-ok')
"""
        rc, out = _run_cmd([sys.executable, "-c", manual], cwd=root)
        runner = "manual"
    if rc != 0:
        return f"BROKEN ({runner} tests failed: {out[-500:]})"

    script = os.path.expanduser("~/.hermes/scripts/hermes_conductor_runtime.py")
    rc, out = _run_cmd([sys.executable, script, "config"], cwd=root)
    if rc != 0:
        return "BROKEN (config command failed: " + out[-400:] + ")"
    try:
        cfg = json.loads(out)
    except Exception as exc:
        return "BROKEN (config JSON parse failed: " + str(exc) + ")"
    if cfg.get("conductor_runtime_enabled") is not True:
        return "BROKEN (conductor runtime must be enabled)"
    if cfg.get("sakana_fugu_enabled") is not False:
        return "BROKEN (sakana_fugu must remain default-off)"
    if cfg.get("router_call_isolated") is not True:
        return "BROKEN (router_call_isolated must remain true)"

    rc, out = _run_cmd([sys.executable, script, "fugu-probe"], cwd=root)
    if rc != 0:
        return "BROKEN (fugu probe command failed: " + out[-400:] + ")"
    try:
        probe = json.loads(out)
    except Exception as exc:
        return "BROKEN (fugu probe JSON parse failed: " + str(exc) + ")"
    if probe.get("status") != "unavailable" or probe.get("fail_soft") is not True:
        return "BROKEN (Fugu adapter must fail-soft when disabled/no key)"

    rc, out = _run_cmd([sys.executable, script, "role-plan"], cwd=root)
    if rc != 0:
        return "BROKEN (role-plan command failed: " + out[-400:] + ")"
    try:
        plan = json.loads(out)
    except Exception as exc:
        return "BROKEN (role-plan JSON parse failed: " + str(exc) + ")"
    if plan.get("conductor_enabled") is not True:
        return "BROKEN (role-plan must show conductor_enabled=true)"
    if plan.get("schema") != "hermes_conductor_role_plan_v1":
        return "BROKEN (role-plan schema mismatch)"

    worker_script = os.path.expanduser("~/.hermes/scripts/hermes_background_task_worker.py")
    rc, out = _run_cmd([sys.executable, worker_script, "probe", "--task-id", "nonexistent"], cwd=root)
    if rc != 0:
        return "BROKEN (background worker probe command failed: " + out[-400:] + ")"
    try:
        probe_w = json.loads(out)
    except Exception as exc:
        return "BROKEN (background worker probe JSON parse failed: " + str(exc) + ")"
    if "error" not in probe_w:
        return "BROKEN (background worker must return error for nonexistent task)"

    return f"OK (tests={runner}, conductor=enabled, fugu=fail-soft, role-plan=enabled, worker=ok)"


def check_openclaw_productization():
    """Regression gate for Hermes-local OpenClaw-informed hardening.

    This is intentionally a behavior check, not a live OpenClaw integration:
    - compile the helper/router/tests
    - run the helper benchmark
    - run pytest if available, otherwise fall back to direct test function calls
    - confirm config stays default-off
    """
    root = HERMES_ROOT
    required = [
        os.path.join(root, "agent", "openclaw_control_plane.py"),
        os.path.join(root, "agent", "task_router.py"),
        os.path.join(root, "tests", "agent", "test_openclaw_control_plane.py"),
        os.path.expanduser("~/.hermes/scripts/hermes_openclaw_control_plane.py"),
    ]
    missing = [path for path in required if not os.path.exists(path)]
    if missing:
        return "BROKEN (missing OpenClaw hardening files: " + ", ".join(os.path.basename(x) for x in missing) + ")"

    rc, out = _run_cmd([
        sys.executable, "-m", "py_compile",
        "agent/openclaw_control_plane.py",
        "agent/task_router.py",
        "tests/agent/test_openclaw_control_plane.py",
    ], cwd=root)
    if rc != 0:
        return "BROKEN (py_compile failed: " + out[-400:] + ")"

    bench_script = os.path.expanduser("~/.hermes/scripts/hermes_openclaw_control_plane.py")
    rc, out = _run_cmd([sys.executable, bench_script, "benchmark"], cwd=root)
    if rc != 0:
        return "BROKEN (benchmark command failed: " + out[-400:] + ")"
    try:
        bench = json.loads(out)
    except Exception as exc:
        return "BROKEN (benchmark JSON parse failed: " + str(exc) + ")"
    if bench.get("verdict") != "pass" or bench.get("passed") != bench.get("total"):
        return f"BROKEN (benchmark {bench.get('passed')}/{bench.get('total')} verdict={bench.get('verdict')})"

    rc, _ = _run_cmd([sys.executable, "-m", "pytest", "--version"], cwd=root, timeout=30)
    if rc == 0:
        rc, out = _run_cmd([sys.executable, "-m", "pytest", "tests/agent/test_openclaw_control_plane.py", "-q"], cwd=root)
        runner = "pytest"
    else:
        manual = """
import sys
sys.path.insert(0,'.')
from tests.agent import test_openclaw_control_plane as t
for name in sorted(dir(t)):
    if name.startswith('test_'):
        getattr(t, name)()
print('manual-tests-ok')
"""
        rc, out = _run_cmd([sys.executable, "-c", manual], cwd=root)
        runner = "manual"
    if rc != 0:
        return f"BROKEN ({runner} tests failed: {out[-500:]})"

    rc, out = _run_cmd([sys.executable, bench_script, "config"], cwd=root)
    if rc != 0:
        return "BROKEN (config check failed: " + out[-400:] + ")"
    try:
        cfg = json.loads(out)
    except Exception as exc:
        return "BROKEN (config JSON parse failed: " + str(exc) + ")"
    if cfg.get("openclaw_activation_hints_enabled") is not True:
        return "BROKEN (activation_hints must be enabled)"
    return f"OK (benchmark {bench.get('passed')}/{bench.get('total')}, tests={runner}, activation_hints=on)"


CONTINUATION_FRAGMENTATION_KEYWORDS = (
    "handoff", "handoffs", "relay", "relays", "resume", "resumes", "retry", "retries", "recovery", "missed",
)
CONTINUATION_FRAGMENTATION_WRITE_MARKERS = (
    ".write_text(", ".write_bytes(", "json.dump(", "open(", "Path(", "mkdir(",
)
CONTINUATION_CANONICAL_MARKERS = (
    "agent.continuation",
    "build_continuation_packet",
    "write_continuation_packet",
    "ContinuationPacket",
    "continuation_status",
)
CONTINUATION_FRAGMENTATION_ALLOWLIST = {
    "tests/",
    "docs/",
    "scripts/post-update-check.py",
}


def _iter_python_files_for_continuation_guard(*roots):
    seen = set()
    for root in roots:
        base = pathlib.Path(root).expanduser()
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def _relative_to_any(path, roots):
    p = pathlib.Path(path).resolve()
    for root in roots:
        try:
            return p.relative_to(pathlib.Path(root).resolve()).as_posix()
        except Exception:
            continue
    return p.as_posix()


def _is_continuation_guard_allowlisted(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    return any(normalized == item.rstrip("/") or normalized.startswith(item) for item in CONTINUATION_FRAGMENTATION_ALLOWLIST)


def _looks_like_ad_hoc_resumable_writer(content: str) -> bool:
    lines = content.splitlines()
    lowered_lines = [line.lower() for line in lines]
    candidate_indexes = [
        idx for idx, line in enumerate(lowered_lines)
        if ".hermes" in line and "state" in line and any(keyword in line for keyword in CONTINUATION_FRAGMENTATION_KEYWORDS)
    ]
    for idx in candidate_indexes:
        start = max(0, idx - 5)
        end = min(len(lines), idx + 6)
        if any(marker in lines[j] for j in range(start, end) for marker in CONTINUATION_FRAGMENTATION_WRITE_MARKERS):
            return True
    return False


def _uses_canonical_continuation(content: str) -> bool:
    return any(marker in content for marker in CONTINUATION_CANONICAL_MARKERS)


def find_continuation_fragmentation_issues(repo_root=None, scripts_root=None):
    """Find ad-hoc resumable-state writers that bypass agent.continuation.

    This is intentionally a conservative governance guard. It does not ban
    legacy relay/handoff compatibility paths; it requires writers of resumable
    state to either use/reference the canonical continuation API or live in a
    test/doc/selfcheck allowlist.
    """
    repo = pathlib.Path(repo_root or HERMES_ROOT).expanduser()
    scripts = pathlib.Path(scripts_root or (LEGACY_HERMES_HOME / "scripts")).expanduser()
    roots = [repo, scripts]
    issues = []
    for path in _iter_python_files_for_continuation_guard(repo, scripts):
        rel = _relative_to_any(path, roots)
        if _is_continuation_guard_allowlisted(rel):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not _looks_like_ad_hoc_resumable_writer(content):
            continue
        if _uses_canonical_continuation(content):
            continue
        evidence = ""
        for line in content.splitlines():
            lowered = line.lower()
            if any(keyword in lowered for keyword in CONTINUATION_FRAGMENTATION_KEYWORDS) and any(marker.strip("(") in line for marker in CONTINUATION_FRAGMENTATION_WRITE_MARKERS):
                evidence = line.strip()[:220]
                break
        if not evidence:
            for line in content.splitlines():
                lowered = line.lower()
                if any(keyword in lowered for keyword in CONTINUATION_FRAGMENTATION_KEYWORDS):
                    evidence = line.strip()[:220]
                    break
        issues.append({"path": rel, "evidence": evidence})
    return issues


def check_continuation_fragmentation_guard() -> str:
    issues = find_continuation_fragmentation_issues(HERMES_ROOT, LEGACY_HERMES_HOME / "scripts")
    if not issues:
        return "OK (no ad-hoc resumable-state writers outside agent.continuation)"
    preview = "; ".join(f"{i['path']}: {i['evidence']}" for i in issues[:5])
    suffix = f"; +{len(issues) - 5} more" if len(issues) > 5 else ""
    return "BROKEN (ad-hoc continuation/handoff writers bypass agent.continuation: " + preview + suffix + ")"


def check_hook_registry_selfcheck() -> str:
    script = str(pathlib.Path(__file__).resolve().parent / "hermes_hook_registry_selfcheck.py")
    if not os.path.exists(script):
        return f"BROKEN (missing selfcheck: {script})"
    rc, out = _run_cmd([sys.executable, script], cwd=HERMES_ROOT)
    text = (out or "").strip()
    if rc == 0:
        return "OK (hook registry selfcheck clean)"
    try:
        payload = json.loads(text)
    except Exception:
        tail = text.splitlines()[-1] if text else f"exit={rc}"
        return f"BROKEN (hook registry selfcheck unreadable: {tail[:300]})"
    issues = payload.get("issues") or []
    if issues:
        return "BROKEN (hook registry selfcheck: " + "; ".join(str(x) for x in issues[:3]) + ")"
    return f"BROKEN (hook registry selfcheck exit={rc})"


register(
    "private_repo_governance",
    ".",
    None,
    "Validate private Hermes repo topology, governance docs, and runtime-state boundary",
)

register(
    "overlay_registry",
    ".",
    None,
    "Validate local overlay registry and artifact presence",
)

register(
    "hook_registry_selfcheck",
    ".",
    None,
    "Validate lifecycle hook registry trust boundaries and fail-closed gates",
)

register(
    "continuation_fragmentation_guard",
    ".",
    None,
    "Detect ad-hoc continuation/handoff/relay/resume/retry writers that bypass agent.continuation",
)

register(
    "conductor_runtime_productization_regression",
    ".",
    None,
    "Run default-off Hermes conductor runtime/Fugu adapter regression gate",
)

register(
    "openclaw_productization_regression",
    ".",
    None,
    "Run OpenClaw-informed Hermes hardening regression gate",
)

def main():
    apply_fixes = "--fix" in sys.argv

    print("═" * 56)
    print("  Hermes Post-Update Self-Check")
    print(f"  Hermes root: {HERMES_ROOT}")
    print(f"  Mode: {'FIX' if apply_fixes else 'DRY RUN'} (pass --fix to apply)")
    print("═" * 56)
    print()

    statuses = []

    for check in CHECKS:
        name = check["name"]
        path = check["path"]
        needle = check["needle"]
        fix_desc = check["fix_desc"]
        fix_func = check["fix_func"]

        print(f"  [{name}]")

            # Memory & steward checks use their own logic
        if needle is None:
            if "gateway_fd_watchdog" in name:
                result = check_gateway_fd_watchdog()
            elif "memory" in name:
                result = check_memory_ghosts()
            elif "steward" in name:
                result = check_steward_liveness()
            elif "skill_tracking" in name:
                result = check_skill_tracking()
            elif "skill_quality" in name:
                result = check_skill_quality()
            elif "private_repo_governance" in name:
                result = check_private_repo_governance()
            elif "overlay_registry" in name:
                result = check_overlay_registry()
            elif "hook_registry_selfcheck" in name:
                result = check_hook_registry_selfcheck()
            elif "continuation_fragmentation_guard" in name:
                result = check_continuation_fragmentation_guard()
            elif "conductor_runtime" in name:
                result = check_conductor_runtime_productization()
            elif "openclaw_productization" in name:
                result = check_openclaw_productization()
            else:
                result = ""
            if result == "OK" or (isinstance(result, str) and result.startswith("OK (")):
                print(f"    ✅ {result}")
                statuses.append((name, "OK"))
            elif result and result.startswith("GHOSTS"):
                print(f"    ⚠️  {result}")
                statuses.append((name, "MANUAL"))
            elif result and result.startswith("DORMANT"):
                print(f"    💤 {result}")
                statuses.append((name, "DORMANT"))
            elif result and result.startswith("INSTALLED"):
                print(f"    📦 {result}")
                statuses.append((name, result))
            else:
                print(f"    ⚠️  {result}")
                statuses.append((name, result))
            continue

        # File-based checks
        if not os.path.exists(path):
            print(f"    ⚠️  FILE MISSING: {path}")
            statuses.append((name, "MISSING"))
            continue

        with open(path) as f:
            content = f.read()

        # Check if the bug pattern is present
        if re.search(needle, content):
            # Bug still present
            if fix_func and apply_fixes:
                if fix_func(path):
                    print(f"    🔧 FIXED: {fix_desc}")
                    statuses.append((name, "FIXED"))
                else:
                    print(f"    ❌ FIX FAILED: {fix_desc}")
                    statuses.append((name, "FIX_FAILED"))
            elif fix_func:
                print(f"    ⚠️  NEEDS FIX: {fix_desc}")
                print(f"       Run with --fix to apply")
                statuses.append((name, "NEEDS_FIX"))
            else:
                print(f"    ⚠️  BUG PRESENT (no auto-fix): {fix_desc}")
                statuses.append((name, "MANUAL"))
        else:
            # Bug not found — already fixed or doesn't apply
            print(f"    ✅ No issue detected (fixed by upstream or not applicable)")
            statuses.append((name, "OK"))

    print()
    print("═" * 56)
    print("  Summary")
    print("═" * 56)

    ok_count = sum(1 for _, s in statuses if s == "OK")
    fix_count = sum(1 for _, s in statuses if s == "FIXED")
    attention_free = {"OK", "FIXED", "INSTALLED_NO_DATA_YET"}
    warn_count = sum(1 for _, s in statuses if s not in attention_free)

    for name, status in statuses:
        if isinstance(status, str) and status.startswith("BROKEN"):
            icon = "❌"
        elif isinstance(status, str) and status.startswith("MISSING"):
            icon = "⚠️"
        else:
            icon = {"OK": "✅", "FIXED": "🔧", "NEEDS_FIX": "⚠️", "MANUAL": "👤",
                    "DORMANT": "💤", "FIX_FAILED": "❌", "MISSING": "⚠️",
                    "INSTALLED_NO_DATA_YET": "📦"}.get(status, "❓")
        print(f"  {icon} {name}: {status}")

    print()
    print(f"  {ok_count} OK  |  {fix_count} fixed  |  {warn_count} need attention")
    print()


if __name__ == "__main__":
    main()
