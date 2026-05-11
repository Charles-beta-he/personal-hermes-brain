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

HERMES_ROOT = os.path.expanduser("~/.hermes/hermes-agent")
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
    warn_count = sum(1 for _, s in statuses if s in ("NEEDS_FIX", "MANUAL", "DORMANT", "GHOSTS", "MISSING"))

    for name, status in statuses:
        icon = {"OK": "✅", "FIXED": "🔧", "NEEDS_FIX": "⚠️", "MANUAL": "👤",
                "DORMANT": "💤", "FIX_FAILED": "❌", "MISSING": "⚠️",
                "INSTALLED_NO_DATA_YET": "📦"}.get(status, "❓")
        print(f"  {icon} {name}: {status}")

    print()
    print(f"  {ok_count} OK  |  {fix_count} fixed  |  {warn_count} need attention")
    print()


if __name__ == "__main__":
    main()
