# OpenWolf Analysis

Source: https://github.com/cytostack/openwolf (TypeScript/Node.js)

## What It Actually Is
NOT a file reading layer. It's a Claude Code hooks system that injects intelligence via 6 lifecycle hooks.

## Three Mechanisms

### 1. Anatomy-based Read Avoidance
- anatomy.md: project file index with descriptions + token estimates
- pre-read hook prints summary to stderr before Claude reads file
- Claude sees summary, can skip full read
- Savings: ~200 tokens per anatomy hit

### 2. Repeated Read Blocking
- Session tracker (_session.json) records every file read + token count
- Re-read attempt → hook warns "already read this session (~380 tok)"
- Savings: full file token × (repeat count - 1)

### 3. Cerebrum/Buglog Guidance
- cerebrum.md: Do-Not-Repeat list
- buglog.json: known bug/fix matching
- pre-write hook checks before code generation
- Savings: prevents repeated mistakes → fewer debug rounds

## Key Files
- src/hooks/pre-read.ts — core token saver
- src/hooks/post-write.ts — anatomy update, memory logging
- src/hooks/shared.ts — token estimation (chars/3.5 code, chars/4.0 prose)
- src/scanner/anatomy-scanner.ts — project tree walker
- src/templates/OPENWOLF.md — protocol Claude follows

## Token Estimation
- Code: text.length / 3.5
- Prose: text.length / 4.0

## Hermes Port
- Anatomy Scanner: agent/anatomy_scanner.py
- Cerebrum: ~/.hermes/cerebrum.md
- Session tracking: _session_files_read set (planned)
