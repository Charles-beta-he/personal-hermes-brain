# Agent Reach → Hermes selective adoption case

Use this reference when evaluating Agent Reach or similar “internet capability installer + doctor + routing skill” repositories against Hermes.

## Deterministic evidence from Agent Reach audit

Repository audited: `https://github.com/Panniantong/Agent-Reach` at commit `17624268a059ccfb23eba8a2ba50f9f92c8dc0ca`.

Key findings:
- Agent Reach is primarily scaffolding, installer, doctor, and agent-readable routing; it is not a full runtime read/search proxy.
- `agent_reach/core.py` exposes `doctor()` / `doctor_report()` only.
- `agent_reach/integrations/mcp_server.py` exposes only a `get_status` MCP tool.
- `agent_reach/channels/base.py` defines a portable channel contract: `name`, `description`, `backends`, `tier`, `can_handle(url)`, `check(config)`.
- `agent_reach/skill/SKILL.md` contains a useful intent-to-tool routing table for platform access.
- `docs/install.md` documents valuable safety UX: no sudo without approval, no workspace pollution, safe mode, dry-run, and optional-channel opt-in.
- `agent_reach/config.py` writes config with `0600`; `doctor.py` warns on broad permissions.
- Full adoption adds unnecessary overlap and supply-chain/cookie blast radius for Hermes: auto-install logic attempts gh/Node/undici/yt-dlp setup and Linux apt source/keyring writes; optional deps include browser cookie extraction.
- Upstream quality smell: version/platform-count drift appeared across pyproject/CLAUDE/README/skill docs.

## Hermes decision pattern

Default decision: **do not install or vendor Agent Reach into Hermes**. Prefer Hermes-native selective extraction.

Borrowable P0/P1 ideas:
1. Capability doctor / reach doctor: unify tool, MCP, skill, credential, model, and platform status into a capability matrix.
2. Global intent-to-tool routing matrix: map user intents to Hermes-native tools/skills, with fallback, auth tier, risk, and cost notes.
3. Setup/config dry-run and safe mode: preview filesystem/config/tool changes before executing.
4. Secret/permission doctor: audit `~/.hermes/config.yaml`, `.env`, `auth.json`, gateway tokens, and MCP env boundaries.
5. Docs/version/capability drift lint: check README/docs/skills/tool manifests for consistency.

## Existing Hermes note

Hermes already has `chinese-platforms` as a selective Agent-Reach-inspired routing skill. Future work should usually extend that or a broader capability-router, not add a second Agent-Reach skill stack.

## Multi-model certification pitfall observed

When building `consult_models.py state`, do not pass one raw evidence object without claim linkage. If evidence entries have empty `supports`, `evidence_bundle.grounding.*.truth_status` can remain `needs_link_review` with `evidence_coverage=0.0`, causing ratification to correctly end as `not_certified` even when all raw evidence exists.

For repo adoption reviews, link each claim explicitly to file/line evidence or fulfill reviewer evidence requests before claiming certification. Treat fan-out as advisory unless `discussion_result.json` and the certification manifest pass truth + vote + agreement gates.