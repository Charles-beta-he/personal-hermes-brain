# UVISA Validation Infrastructure Extraction Pattern

When a Lark task describes a validation issue at one location, check whether the same concern exists elsewhere before implementing a point fix.

## Case Study: Bank Name Emoji Validation (2026-05-11)

**Lark task**: "新增SWIFT银行收款人时，银行名称输入包含表情符号和空格仍能保存成功"

**Agent's initial approach**: Added `BANK_RE` regex locally in `RemitNewSwiftScreen.tsx`. Fixed the one location mentioned in the task.

**User's correction**: "选择其他的银行名称还是可以输入表情符号和空格，似乎并未扩展限制项目中所有的银行名称输入位置。有些对于项目属于基础设施或者常规限制，不能因为任务只说了一个地方就只改这一个地方。"

**Root cause analysis** (6 theoretical frameworks):
- Kahneman System 1 (literal execution) overrode System 2 (pattern recognition)
- Donella Meadows: operated at lowest leverage "parameter tweaking" instead of "system structure"
- Pragmatic Programmer DRY: `cleanText()` duplicated in 2 files, `BANK_RE` local to 1 screen
- Fowler Refactoring: Duplicated Code smell + Feature Envy
- Cross-cutting concerns (AOP): validation is infrastructure, not a per-screen concern

**Correct implementation**:
1. Extract `cleanText()` → `src/lib/utils.ts` (shared utility)
2. Extract `BANK_NAME_RE`, `validateBankName()`, `BANK_ADDRESS_RE`, `validateBankAddress()` → `src/lib/validators.ts` (shared infrastructure, alongside existing `isValidEthAddress`)
3. Update all consumers (`RemitNewSwiftScreen`, `RemitNewWalletScreen`) to import from shared
4. Add bank address validation (previously had none)
5. Add 13 unit tests at infrastructure level
6. Backend should also validate (defense-in-depth, separate task)

**Key insight**: `src/lib/validators.ts` already had `isValidEthAddress` — the infrastructure pattern was established. The agent should have recognized this and extended it, not created a local regex.

## Pre-Execution Checklist for Validation Tasks

Before implementing any input validation fix:
1. `grep` the codebase for similar validation patterns (regex, cleanText, sanitize)
2. Check `src/lib/validators.ts` for existing shared validators
3. Check if backend has matching validation (defense-in-depth)
4. If pattern exists in 2+ locations → extract to shared infrastructure
5. If shared infrastructure exists for same concern → extend it, don't create parallel

## Theoretical Grounding (Why Agents Miss This)

Six frameworks explain why the agent followed the task literally instead of recognizing the cross-cutting concern:

| Framework | Principle | Violation | Correct Behavior |
|-----------|-----------|-----------|------------------|
| Kahneman (Thinking, Fast and Slow) | System 1 vs System 2 | Literal task execution without architectural reflection | Classify problem type before executing |
| Donella Meadows (Thinking in Systems) | Leverage points | Operated at "parameter tweaking" (lowest) instead of "system structure" (high) | Design shared infrastructure |
| Ousterhout (A Philosophy of Software Design) | Tactical vs Strategic | Tactical one-off fix | Strategic extraction to shared module |
| Hunt/Thomas (Pragmatic Programmer) | DRY, Orthogonality | `cleanText` duplicated, `BANK_RE` local | Single source of truth |
| Fowler (Refactoring) | Code smells | Duplicated Code + Feature Envy | Extract Method/Module |
| Evans (DDD) | Ubiquitous language | Validation not a project-level concept | Validators.ts as shared vocabulary |

**Single root cause**: The agent jumped from "receive task" to "execute fix" without passing through problem classification, infrastructure scanning, or leverage analysis. It operated in System 1 when System 2 was needed.

## Pre-Execution Gate (Classify → Scan → Leverage-Test)

Before implementing any task:

1. **Classify**: Is this a point fix, cross-cutting concern, or infrastructure task?
   - Cross-cutting: validation, security, error handling, data transforms, i18n
2. **Scope scan**: Does shared infrastructure exist? Is the pattern duplicated?
3. **Leverage test**: Will this fix recur if done locally? Should it be in `validators.ts`/`utils.ts`?

The user explicitly requires this: "有些对于项目属于基础设施或者常规限制，不能因为任务只说了一个地方就只改这一个地方"

## UVISA Shared Infrastructure Locations

| Concern | Location | Examples |
|---------|----------|----------|
| Input validation | `src/lib/validators.ts` | `isWeakPin`, `isValidAmount`, `isValidEthAddress`, `validateBankName` |
| Text utilities | `src/lib/utils.ts` | `cleanText`, `cn`, `formatAmount` |
| API safety | `src/services/platformConfig.service.ts` | `isPublicReceivingText`, `hasUsableSwiftReceivingConfig` |
| Backend validation | `com.uvisa.platform.core.validation` | (should mirror frontend validators) |
