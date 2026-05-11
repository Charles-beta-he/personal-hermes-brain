#!/usr/bin/env python3
"""
MCP Git Server — Structured Git operations via MCP stdio protocol.
Provides: git_status, git_log, git_diff, git_branch, git_commit, git_add

Usage: This file is registered as an MCP server in config.yaml:
  mcp_servers:
    git:
      command: python3
      args:
        - ~/.hermes/scripts/mcp-git-server.py
      timeout: 30
"""

import json, sys, subprocess, os
from pathlib import Path


def json_rpc_error(id, code, message):
    return json.dumps({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})

def json_rpc_result(id, result):
    return json.dumps({"jsonrpc": "2.0", "id": id, "result": result})

def json_rpc_notification(method, params):
    return json.dumps({"jsonrpc": "2.0", "method": method, "params": params})


# ─── Tool Definitions ───

TOOLS = [
    {
        "name": "git_status",
        "description": "Show working tree status (git status --short)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Git repo path (default: cwd)"}
            }
        }
    },
    {
        "name": "git_log",
        "description": "Show commit log",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Git repo path"},
                "count": {"type": "integer", "description": "Number of commits (default: 10)", "default": 10}
            }
        }
    },
    {
        "name": "git_diff",
        "description": "Show unstaged diff (git diff) or staged diff (git diff --cached)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Git repo path"},
                "cached": {"type": "boolean", "description": "Show staged diff instead", "default": False}
            }
        }
    },
    {
        "name": "git_branch",
        "description": "List branches or create/switch branch",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Git repo path"},
                "action": {
                    "type": "string",
                    "enum": ["list", "current", "create", "delete"],
                    "description": "Branch action (default: list)"
                },
                "name": {"type": "string", "description": "Branch name (required for create/delete)"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "git_commit",
        "description": "Stage all and commit with message",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Git repo path"},
                "message": {"type": "string", "description": "Commit message"},
                "files": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Specific files to stage (default: all changes)"
                }
            },
            "required": ["path", "message"]
        }
    },
    {
        "name": "git_add",
        "description": "Stage specific files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Git repo path"},
                "files": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Files to stage"
                },
                "all": {"type": "boolean", "description": "Stage all changes", "default": False}
            },
            "required": ["path"]
        }
    },
]


def run_git(path, *args):
    """Run git command and return stdout"""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=os.path.expanduser(path) if path else None,
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout
        if result.returncode != 0:
            output = output or f"git error (exit={result.returncode}): {result.stderr[:200]}"
        return {
            "success": result.returncode == 0,
            "output": output.strip(),
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "git command timed out", "exit_code": -1}
    except FileNotFoundError:
        return {"success": False, "output": "git not found or path invalid", "exit_code": -1}


def handle_tool_call(name, args):
    """Execute tool and return result"""
    path = args.get("path", os.getcwd())

    if name == "git_status":
        return run_git(path, "status", "--short")
    elif name == "git_log":
        count = min(args.get("count", 10), 50)
        return run_git(path, "log", f"--oneline", f"-{count}")
    elif name == "git_diff":
        cmd = ["diff"]
        if args.get("cached"):
            cmd.append("--cached")
        return run_git(path, *cmd)
    elif name == "git_branch":
        action = args.get("action", "list")
        if action == "list":
            return run_git(path, "branch")
        elif action == "current":
            return run_git(path, "branch", "--show-current")
        elif action == "create":
            name = args.get("name", "")
            if not name:
                return {"success": False, "output": "branch name required", "exit_code": -1}
            return run_git(path, "checkout", "-b", name)
        elif action == "delete":
            name = args.get("name", "")
            if not name:
                return {"success": False, "output": "branch name required", "exit_code": -1}
            return run_git(path, "branch", "-D", name)
        return {"success": False, "output": f"unknown action: {action}", "exit_code": -1}
    elif name == "git_commit":
        files = args.get("files")
        message = args.get("message", "")
        if not message:
            return {"success": False, "output": "commit message required", "exit_code": -1}
        # Stage files
        if files:
            result = run_git(path, "add", *files)
            if not result["success"]:
                return result
        else:
            run_git(path, "add", "-A")
        # Commit
        return run_git(path, "commit", "-m", message)
    elif name == "git_add":
        if args.get("all"):
            return run_git(path, "add", "-A")
        files = args.get("files", [])
        if not files:
            return {"success": False, "output": "no files specified", "exit_code": -1}
        return run_git(path, "add", *files)

    return {"success": False, "output": f"unknown tool: {name}", "exit_code": -1}


def main():
    """MCP server main loop (stdio JSON-RPC)"""
    initialized = False

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize" and not initialized:
            initialized = True
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "git-mcp-server",
                        "version": "0.1.0"
                    }
                }
            }
            print(json.dumps(response), flush=True)

        elif method == "notifications/initialized":
            pass  # Acknowledge

        elif method == "tools/list" and initialized:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS}
            }
            print(json.dumps(response), flush=True)

        elif method == "tools/call" and initialized:
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            result = handle_tool_call(tool_name, tool_args)
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result.get("output", "")
                        }
                    ],
                    "isError": not result.get("success", False)
                }
            }
            print(json.dumps(response), flush=True)

        else:
            if msg_id:
                err = {"jsonrpc": "2.0", "id": msg_id}
                if not initialized:
                    err["error"] = {"code": -32000, "message": "Server not initialized"}
                else:
                    err["error"] = {"code": -32601, "message": f"Method not found: {method}"}
                print(json.dumps(err), flush=True)


if __name__ == "__main__":
    main()
