# GUI / Computer-Use Agent Repository Audit Pattern

Use this reference when evaluating repositories like Agent-S, OpenAI/Anthropic-style computer-use agents, desktop GUI automation agents, visual grounding frameworks, or wrappers that let another agent control a local GUI.

## Default posture

Do **not** adopt the whole runtime by default. Treat GUI control as a high-blast-radius execution surface: screen reading, keyboard/mouse control, clipboard, local files, shell/Python execution, and logs can expose sensitive data or mutate the user environment.

Prefer Hermes-native selective extraction:

- capability doctor / preflight checklist
- typed GUI action contract
- trajectory evidence schema
- reflection/drift reviewer
- behavior best-of-N evaluator
- permission and log-redaction gates

## Evidence-first scan checklist

1. **Fix source identity**
   - Record repo URL, exact commit SHA, package version, entry points, license.
   - Count files and major runtime surfaces.

2. **Read canonical docs and entry points**
   - `README`, install docs, model/provider docs, package metadata, console scripts.
   - CLI app or wrapper that starts the GUI agent.
   - Any integration skill/wrapper for other agents.

3. **Map real execution path**
   - screenshot capture -> prompt assembly -> model call -> action formatting -> grounding -> OS action execution -> observation loop.
   - Distinguish GUI primitives from code/shell primitives.
   - Identify whether actions are typed schema, free-form code, `eval`, `exec`, shell, or pyautogui strings.

4. **Permission and safety boundary**
   - Screen/Accessibility/Input Monitoring permissions.
   - Clipboard use.
   - Shell/Python execution.
   - Auto-install or system package mutation.
   - Log locations and whether commands/API keys/PII/screenshots are persisted.
   - Timeout/step budget/interrupt behavior.

5. **Grounding and model requirements**
   - Required visual grounding model, OCR dependency, screen resolution assumptions, single-monitor constraints.
   - Provider/API-key handling; whether keys are passed via env, CLI flags, config files, or logs.

6. **Verification pattern**
   - Existing tests/CI gates.
   - Benchmark scripts and split/result artifacts if headline SOTA numbers are cited.
   - Trajectory trace, screenshot, fact-caption, and judge artifacts.

7. **Adoption decision**
   - `adopt` only if runtime is sandboxed, permissioned, reversible, and well-tested.
   - `selective` if methodology is valuable but runtime permission/supply-chain blast radius is high.
   - `reject/reference-only` if the repo mainly wraps unsafe shell/GUI automation without evidence artifacts.

## Hermes-native mappings

| External GUI-agent primitive | Hermes-native target |
|---|---|
| Screen/OCR/grounding setup docs | `macos-computer-use` / browser harness capability doctor |
| Reflection agent over recent trajectory | anti-drift / multi-model reviewer packet |
| Typed `@agent_action` GUI primitives | bounded tool contract / action registry |
| pyautogui code renderer | do **not** copy; replace with permissioned tool calls |
| Local code/bash environment | default-off allowlisted terminal/code tool, with proof-gated output |
| Behavior best-of-N over trajectories | multi-run closure evaluator using screenshots/traces/fact captions |
| External skill wrapper | Hermes skill reference only unless sandboxed and redacted |

## Agent-S observations from fixed audit slice

Source: `simular-ai/Agent-S` commit `5caa76cb19c6a6b947a524f74995c45848c2efbc`.

High-value ideas:

- S3 simplifies orchestration to Worker + ACI grounding instead of a deep hierarchy.
- Reflection checks whether the trajectory is looping or off-plan, without directly becoming the planner.
- GUI actions are exposed as primitives such as open/type/click/drag/save-to-knowledge/call-code-agent.
- Behavior best-of-N turns trajectories into fact captions and compares initial/final screenshots before selecting a rollout.

Risks that block direct runtime adoption:

- Real GUI control via pyautogui and screen capture.
- Optional local Bash/Python execution.
- Free-form generated action code is evaluated into pyautogui code in the observed S3 path.
- Some actions can auto-install packages or modify the host environment.
- Wrappers may print full command lines and should not include secret-bearing CLI args.

Minimum safe Hermes extraction: add a GUI capability doctor and trajectory evidence schema first; do not install or invoke Agent-S from Hermes automation until a separate sandbox/permission design is certified.
