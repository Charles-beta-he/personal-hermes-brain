---
title: Workpad - uvisa-app-2.0
created: 2026-05-08
updated: 2026-05-10 11:59 CST
type: project_workpad
project: uvisa-app-2.0
repo_path: /Users/charles/Desktop/folder/work/uvisa-app-2.0
branch: feat/uvisa-2.0
head: 9256626
status: active_project_working_memory
multi_model_tick: /Users/charles/.hermes/tick-20260509-040423
truth_status: grounded
verified_claim_count: 5/5
---

# Workpad - uvisa-app-2.0

> 规则：这是项目工作记忆，不是全局 memory。跨项目规则进 playbook/skill；项目目标、红线、业务流、验收矩阵留在本文件。

## 0. 元信息

- Project: uvisa-app-2.0
- Path: `/Users/charles/Desktop/folder/work/uvisa-app-2.0`
- Branch: `feat/uvisa-2.0`
- HEAD: `9256626`
- Product type: 移动 H5 金融/银行卡/加密资产前端
- Stack: React 19 + Vite + TypeScript + Zustand + Tailwind + mock-server + Vitest + Playwright
- Current route count: 78
- Current screen count: 72
- Service files: 22
- Last verified: 2026-05-09 16:07 CST
- Current scope: Lark PRD 已读并已补入本 Workpad；用户端 Railway 测换环境、测试账号、验证码临时读取方式均已登记为真实联调 anchor；PRD-derived 产品用户逻辑测试用例已扩展并执行 deterministic Playwright 产品逻辑 smoke：`tests/product-logic-prd.spec.ts` chromium + mobile-chrome 16/16 PASS，覆盖无 C 端自助注册、KYC 只读 + 顾问关系、USDT 转出与 USDT/USDC 充值 EVM-only、USDC ERC20 不显示 token contract 作为充值地址、TRON 地址拦截、USDT/CNY 转出 T2 PIN→邮箱验证码分页、CNY 金额 guard、核心页 + 汇款处理中 i18n 后端供应商/通道术语不外露、单实体卡、稳健理财范围。UI guards：`ui:regression` 22 captures/0 issues，`ui:mobile-h5` 6/6 buckets to new-email-code、0 blockers；`pnpm test` 与 `pnpm run build` PASS。`pnpm lint` 仍是既有 baseline FAIL（139 errors/8 warnings），touched-file ESLint 0 errors。repo 最新提交 `eb3b91a docs: add agent bootstrap handoff` 是本轮修改前基线。官方 OpenAPI 路线从 tenant/app 身份改为 user OAuth 身份优先。`lark_docx_reader.py` 已支持 `--auth user` / `LARK_USER_ACCESS_TOKEN` / OAuth code exchange；Lark 后台已添加 redirect URL 与 user scopes `offline_access`、`docx:document`，OAuth 仍 `20027`，因权限状态 `待发布`，发布/审批需用户显式确认。上一轮 P10 mobile-H5 gate commit 为 `a75a222`。

## 1. North Star

让 `uvisa-app-2.0` 在不丢功能、不降精度、不破坏原字段展示与 H5 交互的前提下，持续对齐参考 `uvisa-app` 的功能完成度，达到 P10/A+ 前端上线级：功能完整、交互闭环、移动端可用、i18n/dark/PWA/观测/后端联调可验证。

决策更新（2026-05-08）：用户已确认直接以 `uvisa-app-2.0` 当前状态为主，不再等待旧 `uvisa-app` reference anchor。因此后续 loop 的基线是当前 repo 的代码、路由、screens、UI_TEST_CASES、ADR 与真实浏览器验收结果；旧 reference 仅作为历史候选材料，不能阻塞当前闭环推进。

## 2. Non-goals

- 本 Workpad 落地不修改 `/Users/charles/Desktop/folder/work/uvisa-app-2.0` 代码。
- 不把项目临时状态写入全局 persistent memory。
- 不用删除按钮、删除路由、隐藏字段、吞错来制造“无 dead UI”。
- 不在缺少 browser/Playwright 证据时宣称 UI 已 A+。
- 不把 README 模板文字当作产品事实；以代码、UI_TEST_CASES、ADR、会话画像和实测证据为准。

## 3. Anchors

| Anchor | Path/URL | Type | Immutable? | Verification |
|---|---|---|---|---|
| Product PRD (Lark) | `https://uaecprod.sg.larksuite.com/docx/GaGLdayTSosobYx6kWylgS7PgMg` | product baseline | Yes for product semantics | extracted via Chrome logged-in fallback; evidence `/tmp/uvisa-lark-product-doc-evidence.json`; tick 20260509-040423 |
| User test environment | `https://uvisa-app-trnn-production.up.railway.app/login` | real user-end environment | Yes for backend/UI联调 | user-provided test account below; must verify via browser/Playwright before claiming real-backend PASS |
| Railway project/services | project `uvisa-test`; frontend service `uvisa-app-tRnN`; backend service `uvisa-backend` | remote package/deploy monitor | Yes for Lark closeout | select the `uvisa-test` project in Railway dashboard; inspect services/deployments with screenshots from the already-open/logged-in browser; do not record cookies/tokens/session data |
| Backend OTP log source | Browser-open Railway `uvisa-backend` service → Deploy Logs | temporary verification-code channel | Yes for current test environment only | read latest `LOGIN` OTP from deploy logs; never persist one-time code values |
| Current project | `/Users/charles/Desktop/folder/work/uvisa-app-2.0` | code repo | No | `git status`, package scripts, routes/screens |
| Current-state baseline | `/Users/charles/Desktop/folder/work/uvisa-app-2.0` | canonical baseline | Yes for next loop | 以当前 routes/screens/docs/tests 为主；本轮记录 78 routes / 72 screens |
| Product user logic cases | `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` | PRD-derived test ledger | Append-only preferred | separates product/user/business logic from page function cases in `docs/UI_TEST_CASES.md` |
| Historical reference candidate | `/Users/charles/Downloads/uvisa-app` | optional historical material | No | 仅作参考，不作为阻塞 gate |
| UI test ledger | `docs/UI_TEST_CASES.md` | project evidence | Append-only preferred | PASS/TODO/FAIL/BLOCK/SKIP 状态与证据 |
| ADR index | `docs/decisions/INDEX.md` | architecture evidence | Append-only preferred | ADR-001..008 |
| Project Claude profile | `/Users/charles/Documents/brain/01-系统与偏好/prefs/uvisa-app-2.0-Claude会话画像-2026-05-08.md` | work-habit evidence | Stable snapshot | multi-model tick 20260508-072835 |
| Frontend closure playbook | `/Users/charles/Documents/brain/05-实践与项目/实践方案/前端闭环验收标准.md` | cross-project standard | Stable evolving | browser/Playwright/evidence ledger |

## 4. Red Lines

- 不能通过删除功能、入口、展示字段、路由或按钮来修 dead UI；除非有证据证明该入口不属于当前业务范围，并写入 ADR/decision。
- 不能改坏原字段展示、原 H5 UI 行为、原业务语义。
- 不能只看截图正常就判定完成；必须验证入口、点击、反馈、状态、错误恢复、完成态。
- 不能用 mock 成功掩盖真实后端路径不一致；mock/real backend alignment 必须有证据。
- 不能跳过 i18n/dark/mobile/PWA/console/network 检查宣称 A+。
- 不能把本项目临时 TODO、当前进度、未验证猜测写进全局 memory。

## 5. Skill Route

| Task Type | Required Skills/Tools | Verification Gate |
|---|---|---|
| Read repo / restore context | source-driven-development, codebase-intelligence, project `.claude/skills/read-repo` | README/package/UI_TEST_CASES/ADR/routes/screens/services 摘要 |
| Architecture / goal shaping | p10, p9, multi-model-thinking | claims/evidence bundle；T2/T3 只在高风险/跨模块时启用 |
| Code edit | project `.claude/skills/modify-code`, test-driven-development, incremental-implementation | caller scan + lint/tsc/test/build |
| Frontend flow closure | react-architecture-migration, browser-harness-integration, visual-regression, uimax-audit | Playwright/browser-harness + console/network/storage |
| UI quality | ui-ux-pro-max, baseline-ui, fixing-accessibility, fixing-motion-performance | mobile 375/390, dark, i18n overflow, interaction feedback |
| Backend/mock alignment | react-architecture-migration Round 9.5, source-driven-development | service path ↔ mock server ↔ real API evidence |
| Product PRD reading | lark-docx-reading, multi-model-thinking | user OAuth preferred when human user can read doc; OpenAPI tenant/app fallback documented; browser copy/screenshot evidence; redacted text/hash/summary; T2/T3 certification |
| Documentation deposition | obsidian, documentation-and-adrs | UI_TEST_CASES / ADR / Workpad Evidence Ledger updated |
| Control-plane check | this self-check script | `python3 ~/.hermes/scripts/uvisa_app_2_workpad_selfcheck.py` PASS |

## 6. Business Flow Matrix

| Flow | Entry | Happy Path | Error Path | Finish State | Evidence |
|---|---|---|---|---|---|
| Auth / 启动 | /login, /verify, /pin-setup | 手机号/验证码/PIN -> /home | 错码、refresh 失败、退出登录 | 登录态明确；失败回 login；无 token 残留 | docs/UI_TEST_CASES.md AUTH-* |
| Home / Wallet / Tx | /home, /account/:ccy, /tx, /tx/:id | 资产、钱包、交易列表/详情可达 | 空交易、长地址、筛选无结果 | 列表/详情/通知回写一致 | HOME-*, TX-* |
| Card | /card, /card/cvv, /card/freeze, /card/topup, /card/withdraw, /card/limits, /card/pin | 卡详情、CVV、冻结、充值提现、限额/PIN | 弱 PIN、冻结后入口、防重复提交 | finish 或状态更新可见 | CARD-* |
| Topup | /topup, /topup/swift/*, /topup/usdt, /topup/cny/* | SWIFT/USDT/CNY 充值路径 | 轮询超时、hidden tab、网络失败 | progress/finish 可达，订单状态一致 | TOPUP-* |
| Exchange | /exchange, /exchange/confirm, /exchange/finish, /order/:id | quote -> confirm -> execute -> order | 报价过期、不支持币对、刷新失败 | 订单详情/timeline 可达 | EX-* |
| Remit | /remit, /remit/payees/*, /remit/:payeeId/* | 收款人 -> 金额 -> preview -> PIN/2FA -> finish | 删除收款人、2FA 错误、返回中断 | finish/timeline/收款人列表一致 | RMT-* |
| Payout | /payout, /payout/crypto/:asset, /payout/usdt, /payout/cny | 地址/收款账户 -> 提交 -> finish | 地址格式、网络选择、余额不足 | finish + tx 回写 | PAYOUT-* |
| Wealth | /wealth, /wealth/product/:id, /wealth/buy/*, /wealth/holdings, /wealth/holding/:id | 产品 -> 购买 -> PIN/2FA -> finish；持仓/赎回 | 金额边界、协议未勾选、赎回失败 | 持仓/收益/详情回写 | WLT-* |
| Me / Security / Customer / Legal | /me, /me/security/*, /me/customer, /legal/:slug | 安全中心、客服、语言/主题、about/legal | 换绑三段、2FA、支付/登录密码错误 | 保护页/设置页状态明确 | SMK-03..08, ME-* |
| Cross-cutting | i18n, dark, mobile, PWA, Sentry/web-vitals, mock/real API | 主题/语言/移动视口/更新提示/API 对齐 | 长英文溢出、dark 跟随失败、SW 旧缓存、API 404 | console/network 清洁，证据入账 | 前端闭环验收标准 + UI_TEST_CASES |

## 6.1 Test Environment / Test Account

> 仅限 `uvisa-app-2.0` 本地项目 Workpad 与联调使用；不要复制到全局 memory、公开 README、PR 描述或 issue。若后续确认该账号不是测试账号，立即从 Workpad 删除并提醒轮换凭据。

- 前端原型地址：`https://napp.denatrust.com`（2026-05-11 用户提供；用于 UI/交互原型对照，非真实联调环境）。

| Environment | Login URL | Login ID | Phone | UID | KYC | Payment PIN | Source / Rule |
|---|---|---|---|---|---|---|---|
| 用户端 Railway 测换环境 | `https://uvisa-app-trnn-production.up.railway.app/login` | `charles.he@uaec.net` | `+8613800000000` | `UV1380000` | `L3` | `123456` | 2026-05-09 用户提供；当前线上入口为邮箱 OTP 登录；仅用于 browser/Playwright 真实联调，结果需写回 Evidence Ledger/UI_TEST_CASES |

### Verification Code Retrieval / 当前临时验证码来源

- 当前测试环境登录验证码暂时不以真实邮件/短信为准，而是在浏览器已打开的 Railway `uvisa-backend` 服务日志中读取。
- 操作入口：Railway 控制台 → project 中选择 `uvisa-backend` 服务 → `Deploy Logs` 标签页。
- 识别方式：查看最新登录相关日志，优先搜索/过滤 `OTP-CODE`、`SMS-DEV`、`purpose=LOGIN`、登录邮箱或账号标识；日志形态通常包含 `OtpService` / `LogSmsSender`、`ttlSeconds=300` 或 `5 分钟内有效`。
- 使用规则：只读取最新一条与本次登录请求匹配的 `LOGIN` 验证码；发送验证码后，后端日志出现 OTP 可能有一段时间间隔，不要立刻判定失败，应等待/刷新/按关键词过滤后再读取；验证码 5 分钟内有效，过期/多次请求后必须重新发送并重新读日志。
- 安全规则：Workpad 只记录“从日志读取验证码”的方法，不保存任何一次性验证码值；截图/日志如包含验证码，应视为敏感调试证据，不进入公开文档、PR、issue 或全局 memory。

## 7. Acceptance Matrix

| Gate | Command/Tool | Pass Criteria | Last Result / Rule |
|---|---|---|---|
| Scope / no app-code change | `git status --short -- /Users/charles/Desktop/folder/work/uvisa-app-2.0` | 本轮仅 brain/scripts 变更，app repo 不被修改 | 本次 Workpad 落地不改 app 代码 |
| Lint | `eslint .` | eslint 无新增错误 | 下次代码 loop 必跑 |
| Build / TypeScript | `tsc -b && vite build` | tsc -b && vite build 通过；若已有 tsc 历史错误需记录隔离 | 下次代码 loop 必跑 |
| Unit | `vitest run` | vitest run 通过；新增逻辑需补回归 | 下次代码 loop 必跑 |
| E2E | `npx playwright test` | 关键 money-moving/auth/security 流程通过 | 下次 UI loop 必跑 |
| Browser-harness / Playwright manual | `browser-harness` 浏览器真实打开，按 `docs/UI_TEST_CASES.md` 真走业务流；必要时 Playwright 辅助记录 console/network | 移动端 390/375 视口、dark/i18n、toast/dialog/返回中断、触摸目标、TabBar/safe-area、console/network 有证据；不能只依赖脚本截图或静态报告 | 下次 UI loop 必跑；使用 `ui-ux-pro-max`、`uimax-audit`、`baseline-ui`、a11y/motion 约束 |
| Full-stack local UI regression | local backend + local frontend + browser-harness/Playwright | 若改动范围同时包含前端代码与后端代码，UI 回测必须改为本地前端连接本地真实后端，由 agent 亲自操作浏览器回归测试并评分；先验证后端 health/exact service path，再记录 browser console/network/storage、截图、UI 评分与缺陷分级 | Mock-server/Railway 只能作对照或回归参考，不能替代本地 full-stack acceptance；证据写回 UI ledger/Workpad |
| Mock / real backend alignment | `服务路径扫描 + mock-server route check + network panel` | service path 与 mock/真实 API 无未解释 404；真实后端切换不破坏 demo | 下次后端联调必跑 |
| Lark task closeout gate | `docs/workflows/lark-task-closeout.md` + Railway/package/deploy monitor | 每个 Lark 任务完成前必须记录本地检查通过，并监听 `uvisa-test` 项目内相关远端 Railway/package/deploy 打包到 success/healthy：前端服务 `uvisa-app-tRnN`，后端服务 `uvisa-backend`；若 failed/cancelled/timeout/pending，必须作为显式 closeout blocker 记录，不得当作 fully closed；Railway/staging 只作远端监控/对照，不替代本地确定性检查与本地 FE→BE 回归；dashboard 可通过已登录浏览器截图读取状态但不得记录 session/cookie/token | 每个 Lark 任务完成必跑 |
| Docs deposition | `更新 docs/UI_TEST_CASES.md / ADR / Workpad Evidence Ledger` | bug fix/架构选择/验收结果有证据路径 | 每轮结束必做 |
| Control-plane self-check | `python3 ~/.hermes/scripts/uvisa_app_2_workpad_selfcheck.py` | Workpad 可检索、结构完整、无明显 secret | 本次 PASS 后登记 |

## 8. Evidence Ledger

| Date | Claim | Evidence Path | Status | Expiry / Next Check |
|---|---|---|---|---|
| 2026-05-11 | Lark cd2b1022 forgot-payment-password / payment PIN reset loading copy + backend route closeout | `/tmp/uvisa-lark-cd2b1022-forgot-payment-pwd-send-status-evidence.md`; `/tmp/uvisa-lark-cd2b1022-forgot-payment-pwd-closeout-evidence.md`; FE `src/screens/me/ForgotPaymentPwdScreen.tsx`, `src/screens/me/__tests__/ForgotPaymentPwdScreen.test.tsx`, `docs/UI_TEST_CASES.md` ME-05; BE `LegacyApiController`, `LegacyApiControllerPaymentPinForgotTest`; multi-model tick `/Users/charles/.hermes/tick-20260511-142315`, certification manifest `final/certification_manifest.json`; FE commits `faba44e` (task-loop), `4570821` + `a07bc11` on deploy branch; BE commit `5b4f602` local | PASS/closed for scoped implementation: FE pending state shows `auth.sendingCode` instead of premature failure; backend provides authenticated `POST /api/auth/pin/forgot/send-code` and `/reset` using bound-email OTP, masked email, no PIN/PII leakage, audit `USER_PAYMENT_PIN_RESET`; BE api-public tests PASS; FE targeted test PASS; FE `pnpm test` PASS 67 files / 519 passed / 1 skipped after restoring upstream feat-branch regressions; FE build PASS with existing chunk warning; Railway frontend `uvisa-app-tRnN` deployment `396a1118-398b-44ca-bc09-df3583834967` SUCCESS for commit `a07bc11`, `/login` HTTP 200. Local FE→local real-BE browser walkthrough explicitly blocked by unrelated backend app compile error `GsalaryWebhookController.findByGsalaryCardId` before app startup. | If final product acceptance requires live PIN-reset E2E, deploy backend commit to the watched backend branch first; backend deployment was not required for this closeout unless explicitly requested |
| 2026-05-11 | Lark 04548d8d SWIFT/IBAN account validation enforces uppercase A-Z + digits only, max 34, no spaces/slash/hyphen | `/tmp/uvisa-lark-04548d8d-swift-iban-validation-evidence.md`; FE `src/lib/validators.ts`, `src/screens/remit/RemitNewSwiftScreen.tsx`, `src/i18n/{zh,en}.json`, `src/lib/__tests__/validators.test.ts`, `src/screens/remit/__tests__/RemitRecipientValidation.test.tsx`; BE `PayeeDetailsValidator`, `RemitController`, `PayeeController`, `PayeeDetailsValidatorTest`; docs `docs/UI_TEST_CASES.md` RMT-01 | PASS local deterministic scope: FE targeted Vitest 2 files / 30 tests PASS; FE `pnpm build` PASS with existing chunk-size warning; BE reactor targeted test 15 modules SUCCESS, `PayeeDetailsValidatorTest` 3/3 PASS; BE reactor package compile SUCCESS. Best landing point was FE immediate form guard + BE contract guard for direct API calls. | Browser full-stack smoke not completed in this slice because local Vite dev returned 403 before walkthrough; run local FE→BE browser acceptance if this task needs final visual closeout/remote deployment evidence. |
| 2026-05-10 | Lark task closeout workflow now requires local checks + remote Railway/package/deploy monitor | `/tmp/uvisa-lark-closeout-workflow-20260510.md`; repo `AGENTS.md`, `docs/workflows/lark-task-closeout.md`, `docs/P10_LOOP_WORKFLOW_STRATEGY.md`, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md`; Workpad verification matrix + boot capsule; Railway project selector screenshot `/Users/charles/.hermes/images/clip_20260510_114905_1.png` confirms project `uvisa-test`; T2 advisory `/tmp/uvisa-lark-closeout-workflow-state.json`, `/Users/charles/.hermes/tick-20260510-033556` | landed as project workflow; exact Railway scope recorded: project `uvisa-test`, frontend service `uvisa-app-tRnN`, backend service `uvisa-backend`; T2 discussion itself not certified because merge left unresolved implementation-required patches, but useful direction adopted with one canonical workflow doc + pointers; public Railway app smoke `/login` HTTP 200, dashboard package terminal status to be read via logged-in browser screenshots without recording secrets | Apply for every future Lark task closeout; local checks must pass and remote status must be success/healthy or an explicit blocker |
| 2026-05-10 | Lark 0fb33d02 auth OTP error i18n closeout | `/tmp/uvisa-auth-code-i18n-20260510.md`, repo `docs/UI_TEST_CASES.md` AUTH-03 + execution ledger row, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` PUL-CON-07/PUL-UX-04; commands `pnpm vitest run src/lib/__tests__/api.envelope.test.ts src/stores/__tests__/auth.store.test.ts --reporter=dot`, `pnpm exec playwright test tests/auth-login.spec.ts --grep AUTH-OTP-I18N --reporter=line`, `pnpm exec playwright test tests/auth-login.spec.ts --reporter=line`, `OUT_DIR=/tmp/uvisa-ui-regression-auth-otp-i18n-20260510 pnpm run ui:regression`, touched-file `eslint`, `pnpm test`, `pnpm run build`, `git diff --check` | PASS: targeted Vitest 32/32; targeted Playwright auth OTP i18n 4/4 across chromium + mobile-chrome; full auth Playwright spec 16/16; UI regression 21 captures / 0 issues; full unit 55 files / 477 passed / 1 skipped; build PASS with existing chunk warning; backend `code` preserved for auth-domain mapping; invalid/expired/rate-limit OTP errors normalize to i18n keys while unknown/non-OTP business messages remain raw or use the correct send-code fallback; no live OTP/test account copied into repo docs or tmp evidence | Next: real Railway login smoke remains separate with Workpad OTP-log workflow |
| 2026-05-10 | Lark 8ebab4cd login send-code rate-limit prompt follows active language | `/tmp/uvisa-lark-8ebab4cd-login-rate-limit-i18n-evidence.md`, repo `docs/UI_TEST_CASES.md` D135, `src/stores/__tests__/auth.store.test.ts`, `tests/auth-login.spec.ts`; final multi-model state `/tmp/uvisa-lark-8ebab4cd-mm-state-final2.json`, tick `/Users/charles/.hermes/tick-20260510-083228` | PASS for scoped task: production `auth.store` already normalizes rate-limit code/message to `auth.requestTooFrequent`; added store guards for code+message and message-only `Too many requests`; Playwright `AUTH-SEND-CODE-I18N-01` verifies zh toast `请求次数过多，请稍后再试`, no raw English, remains `/login`; targeted Vitest 28/28, targeted Playwright 2/2, touched-file ESLint + `git diff --check` PASS, build PASS. Full `pnpm test` remains baseline FAIL outside touched files (54 files passed / 6 failed, 472 passed / 17 failed / 1 skipped). Multi-model truth gate grounded 6/6; Claude/GPT-5.5/DeepSeek approve; final status not clean four-model certified because MiMo discussion adapter failed (`Not supported model xiaomi`) despite seed planner artifact. | Next: commit/push shared task-loop branch, monitor frontend Railway/package/deploy, TG notify; live Lark API read/write still blocked by user-token/app credentials |
| 2026-05-10 | Lark 3cc6f26d transaction times use backend timestamp + local timezone | `/tmp/uvisa-lark-3cc6f26d-transaction-time-evidence.md`, repo `docs/UI_TEST_CASES.md` D136/TX-01/TX-02/CARD-08, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` PUL-MONEY-01 + execution ledger, `src/services/transaction.service.ts`, `src/services/card.service.ts`, `src/types/index.ts`, `src/services/__tests__/money-services.test.ts`, `src/services/__tests__/card.service.test.ts`; final multi-model state `/tmp/uvisa-lark-3cc6f26d-mm-state-final.json`, tick `/Users/charles/.hermes/tick-20260510-090432` | PASS in touched scope: backend `/api/transactions*` already supplies `postedAt`; frontend now centralizes `normalizeTransaction`, prioritizes backend timestamp fields, supports ISO + seconds/milliseconds Unix timestamp, renders `date` via local-time `formatDate(...,{time:true})`, preserves `occurredAt`, and reuses the same logic for card transaction lists. Targeted service Vitest 38/38 PASS; touched-file ESLint + `git diff --check` PASS; build PASS with existing chunk warning; full `pnpm test` remains baseline FAIL outside touched files (54 files passed / 6 failed, 475 passed / 17 failed / 1 skipped). Multi-model truth gate grounded 7/7 and GPT/DeepSeek discussion votes approved; not clean four-model certified because Claude discussion call was unparseable and MiMo adapter failed/hung (`Not supported model xiaomi`). | Next: scoped commit/push, remote frontend package/deploy monitor, TG notify; PUL-MONEY-01 notification-side `occurredAt` backend follow-up remains separate from this task |
| 2026-05-10 | Lark 43e7f9bb exchange quote countdown uses backend quoteId/expiresAt and links input→confirm→PIN finish | `/tmp/uvisa-lark-43e7f9bb-exchange-quote-countdown-evidence.md`, repo `src/screens/exchange/__tests__/ExchangeQuoteCountdown.test.tsx`, `src/screens/exchange/ExchangeScreen.tsx`, `src/screens/exchange/ExchangeConfirmScreen.tsx`, `src/screens/payment/PaymentFinishScreens.tsx`, `src/services/exchange.service.ts`, `docs/UI_TEST_CASES.md` D137/EX-01/EX-02, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` PUL-FLOW-06/PUL-MONEY-06; multi-model state `/tmp/uvisa-lark-43e7f9bb-mm-state.json`, tick `/Users/charles/.hermes/tick-20260510-095612`; commit `855293d` pushed to `origin/lark/uvisa-2-task-loop-20260510-144147` | PASS in touched scope: input page calls backend quote and displays quote converted/rate/countdown; confirm reuses same expiresAt and writes quoteId/expiresAt to PIN next URL; finish rejects missing/expired quote and calls execute with same quoteId, so no post-PIN re-quote. Targeted Vitest 32/32 PASS, touched-file ESLint PASS, tsc PASS, `git diff --check` PASS, build PASS with existing chunk warning, browser smoke observed `/api/exchange/quote` and expired confirm disabled. Full `pnpm test` remains baseline FAIL outside touched files (55 files passed / 6 failed, 480 passed / 17 failed / 1 skipped). Multi-model truth gate grounded 6/6 with GPT-5.5 + DeepSeek approve and empty issue ledger; not clean four-model certified because Claude discussion hit API 403 and MiMo provider reports `Not supported model xiaomi`. Railway frontend `uvisa-app-tRnN` current deployment `63d7bed8-4c37-4947-8770-198f320f9d2d` is `NEEDS_APPROVAL`, stopped=true; public `/login` smoke HTTP 200 from prior successful deployment. | `closed_with_remote_blocker`: implementation pushed and local gates pass; current remote FE package/deploy requires approval before fully healthy/latest. Real backend SUCCESS/FAIL polling + wallet balance reconciliation remain separate PUL follow-up |
| 2026-05-11 | Lark b8920d15 password-login wrong-password lock copy | `/tmp/uvisa-lark-b8920d15-password-login-lock-copy-evidence.md`; FE `src/i18n/zh.json`, `src/i18n/en.json`, `src/i18n/__tests__/auth-password-rate-limit-copy.test.ts`, docs `docs/UI_TEST_CASES.md` D135A, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` PUL-UX-04; BE `AuthService`, `AuthServicePasswordLoginTest`; commands: BE targeted 3/3 PASS, BE api-public package PASS, FE targeted i18n guard 2/2 PASS, FE full test 72 files / 554 passed / 1 skipped, FE build PASS, both repos `git diff --check` PASS | PASS local deterministic: password-login rate-limit now counts only backend-confirmed `PASSWORD_INVALID`, success/frozen/no-user paths do not consume wrong-password attempts, UI shows “密码错误次数过多，账户已锁定 30 分钟” instead of generic request throttling, and forgot-password RATE_LIMITED remains generic. Frontend commit `d5950c4` pushed; backend local commit `69f511b`; Railway frontend service `uvisa-app-tRnN` latest deployment `ccc7f82b-5c60-408f-914b-18b0d00acf69` is SUCCESS on branch `feat/uvisa-2.0` commit `bc9f6316793f`, public `/login` smoke HTTP 200; pushed task-loop commit is not currently deployed, so closeout is `closed_with_remote_blocker` for latest-task deployment until branch is merged/deployed. TG notification sent. | Next: merge/deploy task-loop branch if production/staging latest-task verification is required |
| 2026-05-11 | Lark 95b2a5d5 trusted-device state persists refresh/relogin with backend source-of-truth | `/tmp/uvisa-lark-95b2a5d5-trusted-device-evidence.md`; FE `src/lib/deviceTrust.ts`, `src/data/securityStore.ts`, `src/screens/me/security/DevicesScreen.tsx`, `src/stores/auth.store.ts`, `src/services/auth.service.ts`; BE `DeviceController`, `AuthController`, `AuthService`, `DeviceFingerprintService`, migration `V727__identity_user_device_trusted.sql`; docs `docs/UI_TEST_CASES.md` ME-07/ME-10 + ledger, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` PUL-SEC-05/06; tests/build: FE targeted 14 pass/1 skip, FE full 71 files/552 pass/1 skip, FE build PASS, BE targeted 5/5 PASS including password-login token contract, BE package PASS after generated duplicate target class cleanup, both repos `git diff --check` PASS | PASS local deterministic: trusted-device state persists through backend source of truth, and both frontend token paths (`/auth/login`, `/auth/login-with-password`) receive backend-sourced `currentDeviceTrusted`; backend local commit `8405bc3`, frontend commit `25dd3e9` pushed to `origin/lark/uvisa-2-task-loop-20260510-144147`; remote frontend monitor frontend Railway service `uvisa-app-tRnN`: status SUCCESS/stopped=false, deployment `ccc7f82b-5c60-408f-914b-18b0d00acf69`, branch `feat/uvisa-2.0`, commit `bc9f6316793fc85ff27faf267d1f3160fe972527`; public `/login` HTTP 200 at 2026-05-11 20:43 CST. Task-loop frontend commit `25dd3e9` is pushed to `origin/lark/uvisa-2-task-loop-20260510-144147`; Railway tracks `feat/uvisa-2.0`, so monitored deployment is healthy comparison evidence, not proof that task-loop commit is deployed.; TG通知 sent telegram message_id 840 |
| 2026-05-10 | Lark 57da3f4f large-amount typography avoids 375px overflow without losing precision | `/tmp/uvisa-lark-57da3f4f-large-amount-typography-evidence.md`, `/tmp/uvisa-lark-57da3f4f-visual-evidence.json`, screenshots `/tmp/uvisa-lark-57da3f4f-home-large-amount-375.png` and `/tmp/uvisa-lark-57da3f4f-account-usd-large-amount-375.png`; repo `src/screens/home/HomeScreen.tsx`, `src/screens/home/AccountDetailScreen.tsx`, `src/screens/home/__tests__/HomeScreen.amount-fit.test.tsx`, `docs/UI_TEST_CASES.md` D139/BND-VIS-02; multi-model state `/tmp/uvisa-lark-57da3f4f-mm-state.json`, tick `/Users/charles/.hermes/tick-20260510-115329`; commit `7bf5a97` pushed to `origin/lark/uvisa-2-task-loop-20260510-144147` | CLOSED: Home total, wallet rows, and account detail balance now use adaptive typography tiers while keeping thousands separators and decimal precision; account detail 20+ character amount tier reduced to `text-24` after visual proof found `text-26` clipped. Targeted Vitest 3/3 PASS, touched-file ESLint PASS, 375px Playwright visual PASS (`docScrollWidth=375`, wallet/account amount not clipped), full `pnpm test` PASS 63 files / 505 passed / 1 skipped, `pnpm run build` PASS with existing chunk warning, `git diff --check` PASS. Multi-model truth gate grounded 4/4; GPT-5.5/Claude/DeepSeek approve; not clean four-model certified because MiMo/xiaomi discussion adapter returns `Not supported model xiaomi`. Railway frontend `uvisa-app-tRnN` service monitor at 2026-05-10 20:07 CST: deployment `63d7bed8-4c37-4947-8770-198f320f9d2d` `SUCCESS`, `stopped=false`; public `/login` smoke HTTP 200. Note: healthy watched FE deployment is branch `feat/uvisa-2.0` commit `35a6eec`, while task-loop commit is pushed to shared branch rather than asserted as the current deployed commit. | Closed for Lark task-reporting purposes; continue next UVISA assigned task. |
| 2026-05-08 | Project has enough evidence for Workpad | `/tmp/uvisa_workpad_next/uvisa_workpad_mm_state.json`, `/Users/charles/.hermes/tick-20260508-080122` | grounded 5/5 | Refresh when routes/screens/scripts materially change |
| 2026-05-08 | Project has 78 routes and 72 screens | `/tmp/uvisa_workpad_next/evidence_requests_fulfilled.json` | verified | Re-run before parity diff |
| 2026-05-08 | UI test ledger exists and contains mixed status evidence | `docs/UI_TEST_CASES.md` | keyword_counts PASS=108, TODO=35, FAIL=7, BLOCK=1, SKIP=3 | Do not treat keyword counts as unique-test pass rate |
| 2026-05-08 | Red lines and workflow habits are grounded | `uvisa-app-2.0-Claude会话画像-2026-05-08.md` | grounded | Re-evaluate if user changes project goal |
| 2026-05-08 | Cross-project closure standard exists | `前端闭环验收标准.md` | verified | Reuse across frontend projects |
| 2026-05-08 | User decision: current-state baseline wins | current conversation decision | verified by user instruction | 后续以当前 uvisa-app-2.0 状态推进 |
| 2026-05-08 | Historical reference candidate exists | `/Users/charles/Downloads/uvisa-app` | non-blocking reference | 仅作历史对照，不作为当前验收 gate |
| 2026-05-08 | Login -> email-code browser walkthrough | `/tmp/uvisa-login-email-evidence-default-railway/evidence.json`, `/tmp/uvisa-login-email-evidence-mock/evidence.json`, `/Users/charles/.hermes/tick-20260508-084049` | default dev FAIL; forced mock PASS to new-email-code stage; truth grounded 5/5 | Superseded by UI regression guard fix row below |
| 2026-05-08 | UI regression guard + P0/P1/P2 fixes | `/tmp/uvisa-ui-regression-final-crypto-v2-20260508/report.md`, `/tmp/uvisa-money-contract-mm-state.json`, `/Users/charles/.hermes/tick-20260508-091940` | default `npm run dev` + local mock PASS; 22 captures; 0 issues; AI vision复检 home crypto light/dark-en PASS; unit 52 files/451 pass/1 skipped; build PASS with existing warnings | Remaining: Playwright `flow-closure.spec.ts` stale selectors and real-backend log dependency; build CSS/chunk warnings are next backlog |
| 2026-05-09 | P10 mobile-H5 PUA-loop gate certified | `/tmp/uvisa-mobile-h5-loop-gate-pua-final/report.md`, `/tmp/uvisa-mobile-h5-loop-gate-pua-final/issue-ledger.json`, `/tmp/uvisa-ui-regression-pua-final/report.md`, `/Users/charles/.hermes/tick-20260509-031134`, commit `a75a222` | grounded 4/4; T3 discussion certified 4/4 approve; `ui:mobile-h5` 6/6 buckets to new-email-code, 60 captures, 53 INFO scrollable_below_fold, 0 blocker/P0 true_clip/unclassified HIGH/console error/pageerror/API failure; `ui:regression` 22 captures/0 issues; test 52 files/451 pass/1 skipped; build PASS | Remaining: Vite chunk-size warning classified P2 performance backlog; not severity>=3 mobile-H5 blocker while runtime gates pass |
| 2026-05-09 | Product PRD from Lark read and certified | `/tmp/uvisa-lark-product-doc-redacted.txt`, `/tmp/uvisa-lark-product-doc-evidence.json`, `/tmp/uvisa-lark-product-doc-summary.md`, `/tmp/uvisa-lark-window-screenshot-proof/summary.json`, `/tmp/uvisa-lark-window-screenshot-proof/manifest.json`, `/Users/charles/.hermes/tick-20260509-040423`, skill `lark-docx-reading` | grounded 5/5; T2 discussion certified 4/4 approve; extracted `U-VISA2.0 C 端产品需求文档（PRD v1.0）`, 27069 chars / 967 lines / sha256 `3b1eb4cce25572dd2049ae42e70482851be48f6de6d7a44a84d70ea5481e74a9`; 11 modules / 13 flows summarized; OpenAPI path recorded as 403/1770032; Chrome logged-in fallback succeeded; screenshot sweep 129 window-only captures / 110 unique hashes, vision samples confirm sections 1/4/5/6 and late Appendix D | For official OpenAPI read, request Lark permission `查看新版文档`, optionally `创建及编辑新版文档` for edit/history, optionally `获取用户 user ID` only if user fields needed; app/bot or user token must also have document-level read access. Preserve `暂时无法在Lark文档外展示此内容` placeholders as unknown, not inferred |
| 2026-05-09 | Lark Docx official API route changed to user OAuth-first | `/tmp/uvisa-lark-user-oauth-permission-state.json`, `/tmp/lark-permission-after-apply.png`, `/tmp/lark-oauth-after-permission.png`, `~/.hermes/scripts/lark_docx_reader.py`, skill reference `lark-user-oauth-docx.md` | redirect URL added; user scopes `offline_access` + `docx:document` imported/applied; script supports `--auth user`; OAuth still `20027` because permissions are `待发布`; no user_access_token / OpenAPI read yet | Needs explicit user confirmation before version creation/release/admin approval; then retry OAuth and read PRD with `user_access_token` |
| 2026-05-09 | 用户端 Railway 测换环境测试账号已登记 | current user instruction; Workpad section 6.1 | verified as user-provided; 2026-05-09 updated login identifier to email; browser opened live login page and confirmed filled email enables `下一步`; OTP not sent in this update | Next real-backend loop must authenticate with this account, inspect console/network/storage, then update UI_TEST_CASES + Evidence Ledger |
| 2026-05-09 | 当前测试环境验证码需从浏览器打开的 Railway `uvisa-backend` Deploy Logs 读取 | current user instruction + attached screenshots; Workpad section 6.1 | verified as user-provided workflow; screenshot examples show `OTP-CODE` / `SMS-DEV` / `purpose=LOGIN` log pattern; OTP values intentionally not persisted; user clarified OTP log may appear after a delay; current login challenge is email OTP | During login smoke tests, send code once, then wait/refresh/filter for the latest matching log entry from `uvisa-backend` deploy logs; do not store OTP values in docs |
| 2026-05-09 | PRD-derived 产品用户逻辑测试用例已补充 | `docs/PRODUCT_USER_LOGIC_TEST_CASES.md`, `docs/UI_TEST_CASES.md` section 0.3, PRD summary `/tmp/uvisa-lark-product-doc-summary.md`, PRD redacted lines 737-858 | created test layer for product/user logic distinct from page function tests; covers PRD constraints, 13 core user flows, funds/state closure, risk/security/device logic, backend transparency, product limits, and real-env execution protocol | Next loop should execute P0: real login baseline, T2 outflow coverage, backend-transparency checks; update statuses with evidence |
| 2026-05-09 | PRD deterministic product-logic smoke started | repo `tests/product-logic-prd.spec.ts`, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` §9, `docs/UI_TEST_CASES.md` §0.3, multi-model tick `/Users/charles/.hermes/tick-20260509-070819`, command `npx playwright test tests/product-logic-prd.spec.ts --reporter=line` | PASS 8/8 chromium + mobile-chrome: no C-side self-registration, KYC readonly + advisor, USDT payout EVM-only + TRON-format address blocked + T2 PIN→email-code paging, single physical card + stable-only wealth/fund-quant empty states | Next: real Railway login smoke with delayed OTP-log workflow, topup/USDC EVM, full outflow T2 matrix, card注销/72h/限流专项 |
| 2026-05-09 | PRD deterministic product-logic smoke expanded + UI guards rerun | repo `tests/product-logic-prd.spec.ts`, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` §9, `docs/UI_TEST_CASES.md` §0.3, `test-results/ui-regression-2026-05-09T08-06-20-061Z/report.md`, `/tmp/uvisa-mobile-h5-loop-gate-1778314001330/report.md`; commands: `pnpm exec playwright test tests/product-logic-prd.spec.ts --reporter=line`, `BASE_URL=http://localhost:5173 pnpm run ui:regression`, `BASE_URL=http://localhost:5173 pnpm run ui:mobile-h5`, `pnpm test`, `pnpm run build`, touched-file `eslint` | PASS: product logic 16/16 chromium + mobile-chrome, including USDC ERC20 deposit-address guard against token contract display; UI regression 22 captures/0 issues; mobile-H5 6/6 buckets to new-email-code, 60 captures, 53 INFO, 0 blockers/P0 true clip/unclassified HIGH/console error/pageerror/API failure; unit 52 files/451 pass/1 skipped; build PASS; touched-file ESLint 0 errors. Full `pnpm lint` remains baseline FAIL 139 errors/8 warnings unrelated to touched files | Next: real Railway login smoke with delayed OTP-log workflow, full outflow T2 matrix (汇款/赎回/卡注销), card注销/72h/限流专项, real webhook/到账闭环, full failure-state backend-transparency scan |
| 2026-05-09 | 新会话 handoff capsule 已补齐 | Workpad section 12, repo `AGENTS.md`, commit `eb3b91a`, global memory updated with repo + Workpad pointer | another Hermes session can restore project context by reading `AGENTS.md`, this Workpad, `docs/UI_TEST_CASES.md`, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md`, ADR index, and latest git status; sensitive OTP/test-account details stay project-scoped | On new session, do not rely on compressed chat alone; load `AGENTS.md` + section 12 first, then verify repo HEAD/status |
| 2026-05-09 | P0 card no-card + topup receiving safety hardening verified | frontend repo `src/services/card.service.ts`, `src/screens/card/RequireCard.tsx`, `src/screens/topup/SwiftDetailsScreen.tsx`, `src/screens/topup/CnyBankScreen.tsx`, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md`, `docs/UI_TEST_CASES.md`; backend repo `PlatformPublicConfigController.java`, `LegacyApiController.java`, `FrontendCompatibilityApiContractTest.java`; evidence `/tmp/uvisa-ui-regression-p0-card-topup-20260509-v4`, `/tmp/uvisa-mobile-h5-p0-card-topup-20260509-v4` | PASS deterministic slice after independent reviewer blocker fix: backend contract 10/10 + package PASS; frontend Vitest 55 files/468 pass/1 skip + build PASS; UI regression 21 captures/0 issues; mobile-H5 6/6 buckets/0 blockers; frontend/backend `git diff --check` + added-line static scan PASS. Topup receiving details now fail-closed unless backend section is explicitly `publicVisible=true` and all fields are safe/masked; reviewer blocker fix added numeric/split-digit account-number bypass tests, validates displayed CNY hints, and removes synthetic CNY reference generation. Initial local real-backend smoke caveat was resolved by the later JDBC timing proxy exception-unwrapping fix recorded below. Four-model T3 ratification certified this deterministic slice at `/Users/charles/.hermes/tick-20260509-145115`; scoped local commits landed as frontend `7f63a78` and backend `cb80f2a`, with both repo worktrees clean; keep sensitive account/PIN/OTP only in section 6.1. | Next: real Railway login smoke with Workpad OTP-log workflow, card cancel semantics decision, and full backend architecture-gate cleanup as separate task. |
| 2026-05-09 | Local full Spring Boot real-backend smoke unblocked | backend repo `app/uvisa-app/src/main/java/com/uvisa/app/jdbc/JdbcTimingDataSource.java`, `app/uvisa-app/src/test/java/com/uvisa/app/jdbc/JdbcTimingDataSourceTest.java`; frontend repo `docs/REAL_BACKEND_REBASE_AND_GAP_REPORT_2026-05-09.md`; process `proc_e9e31c3c5c1b` | Root cause: dev `JdbcTimingDataSource` reflection proxy wrapped MySQL/Flyway `SQLException` as `InvocationTargetException`/`UndeclaredThrowableException`, preventing Flyway's MySQL user-variable permission probe from degrading gracefully. Fix unwraps reflective invocation causes and preserves original checked `SQLException`. Verification: RED test reproduced UTE; GREEN targeted Maven test PASS; `mvn -pl app/uvisa-app -am -DskipTests package` PASS; `FLYWAY_ENABLED=true` + production-like RocketMQ `spring-boot:run` stayed running on 8080; Flyway applied 89 migrations to v940; `/actuator/health` 200/UP with DB/Redis UP; `/api/platform-config/topup` and `/api/platform-config/customer-service` 200. | Next: commit backend fix separately; keep RocketMQ-excluded harness marked invalid because `CoboWebhookController` requires `RocketMQTemplate`; do not claim full backend test-suite green until existing ArchUnit/M1 gates are separately fixed. |
| 2026-05-09 | Real-backend login contract switched to email OTP | repo `tests/real-backend-login.spec.ts`, `playwright.real-backend.config.ts`, `tests/auth-login.spec.ts`, `tests/payment-pin-gate.spec.ts`, `scripts/ui-regression.mjs`, `scripts/mobile-h5-loop-gate.mjs`, `docs/UI_TEST_CASES.md`, `docs/PRODUCT_USER_LOGIC_TEST_CASES.md`; live browser page `https://uvisa-app-trnn-production.up.railway.app/login`; commands `pnpm exec playwright test tests/auth-login.spec.ts tests/payment-pin-gate.spec.ts --reporter=line`, `pnpm exec playwright test -c playwright.real-backend.config.ts tests/real-backend-login.spec.ts --reporter=line`, `pnpm test`, `pnpm run build` | PASS for mock/local guards: auth+PIN gate 18/18, unit 52 files/452 pass/1 skipped, build PASS with existing chunk warning; real-backend spec skips unless `UVISA_TEST_LOGIN_EMAIL` is provided from Workpad; live browser confirmed email input and enabled next CTA without sending OTP | Next: run real login with OTP from Railway Deploy Logs, then finish login→logout→login→pin-setup gate and security review |

| 2026-05-09 | Backend repo write permission granted for full local-stack workflow | current user instruction; backend repo `/Users/charles/Desktop/folder/work/uvisa-backend`; Workpad section 12.2 | verified as user-provided workflow change; backend branch `feat/frontend-api-gap-analysis` clean at `0805d09`; frontend branch has pending email-OTP migration diff awaiting scoped commit | Next: run multi-model evidence-first planning across PRD + frontend + backend, then TDD-gated backend/frontend changes, local full-stack UI scoring, and separate local commits per repo |

## 8.1 Claim / Evidence IDs

- Claims: C-001, C-002, C-003, C-004, C-005
- Evidence: E-001, E-002, E-003, E-004, E-005
- Source state: `/tmp/uvisa-lark-doc-reading-mm-state.json`
- Multi-model tick: `/Users/charles/.hermes/tick-20260509-040423`

## 9. Known Debts / Open Risks

| ID | Risk | Severity | Owner | Next Check |
|---|---|---|---|---|
| R-001 | 当前状态基线可能仍含历史 TODO/FAIL/BLOCK，不能因为不等旧参考就降低闭环标准 | 4 | next loop | 从 UI_TEST_CASES 和真实浏览器结果生成 P0/P1 队列 |
| R-002 | UI_TEST_CASES includes TODO/FAIL/BLOCK keyword counts; cannot claim A+ until actual current run evidence updates ledger | 4 | next loop | Run Playwright/browser-harness and update statuses |
| R-003 | Real backend vs mock alignment can drift as APIs change | 4 | next backend loop | service path scan + network check |
| R-004 | i18n/dark/mobile/PWA issues often pass build but fail real UI | 3 | UI loop | 375/390 viewport + system dark + language switch |
| R-005 | Long-running loop may drift from red lines if Workpad is not read at session start | 3 | agent | Load this Workpad before code changes |

## 10. Next Loop Queue

- [ ] Freeze current-state baseline: record current routes/screens/services/docs snapshot as next loop starting point.
- [ ] Build current-state closure backlog: derive P0/P1/P2 from UI_TEST_CASES TODO/FAIL/BLOCK + live browser evidence.
- [ ] Build product-user-logic closure backlog from `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` P0/P1/P2, not only page functional TODOs.
- [ ] Convert UI_TEST_CASES TODO/FAIL/BLOCK into prioritized P0/P1/P2 loop queue.
- [ ] Run deterministic gates: lint, build/tsc, vitest.
- [ ] Run Playwright/browser-harness mobile dark/i18n closure sweep.
- [ ] For UI tasks, prefer browser-harness real browser walkthrough: open the app, follow `docs/UI_TEST_CASES.md` step-by-step, test interactions, inspect console/network, capture screenshots, and grade with ui-ux-pro-max/UIMax/baseline-ui/a11y/motion constraints; `npm run ui:regression` is a guard, not the sole acceptance proof.
- [ ] Run mock/real backend path alignment check and record unresolved API mismatches.
- [ ] Use the registered Railway test account (current login identifier: email) for a real user-end login smoke test; after sending verification code, wait for delayed backend log emission if needed, then read the latest matching `LOGIN` OTP from browser-open Railway `uvisa-backend` Deploy Logs, then record console/network/storage evidence before marking real-backend login PASS. Do not persist the OTP value itself.
- [ ] Update docs/UI_TEST_CASES.md, ADR if needed, and this Evidence Ledger after each loop.

## 11. Deposition Rules

- Stable project convention → this Workpad or project `.claude/skills`.
- Cross-project workflow → `前端闭环验收标准.md` / skill.
- User durable preference → global memory only if still true across projects.
- Completed task status → session transcript/task log, not memory.
- Secrets/tokens/passwords/API keys → never copy into global memory or public docs; project test credentials may live only in this local Workpad when explicitly provided by the user, and must be removed if they are not disposable test credentials.

## 12. New Session Handoff / Boot Capsule

另开 Hermes 会话或交给子 Agent 前，先读这一节，避免只靠压缩会话或全局 memory 造成上下文漂移。

### 12.1 Minimum boot sequence

1. `cd /Users/charles/Desktop/folder/work/uvisa-app-2.0`
2. `git status --short && git log -3 --oneline`
3. 读取 repo agent bootstrap：`AGENTS.md`。
4. 读取本 Workpad：`/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/Workpad - uvisa-app-2.0.md`
5. 读取 repo 关键文档：
   - `docs/UI_TEST_CASES.md`：页面功能、UI、边界、自动守卫与执行日志。
   - `docs/PRODUCT_USER_LOGIC_TEST_CASES.md`：PRD-derived 产品用户逻辑，不可用页面 PASS 代替。
   - `docs/decisions/INDEX.md`：ADR 约束。
   - `docs/P10_LOOP_WORKFLOW_STRATEGY.md`：P10 loop 策略。
6. 若任务涉及 PRD 语义，优先使用 Lark PRD 读取证据：`/tmp/uvisa-lark-product-doc-summary.md`、`/tmp/uvisa-lark-product-doc-redacted.txt`、tick `/Users/charles/.hermes/tick-20260509-040423`；不要根据记忆猜 PRD。

### 12.2 Current project facts to preserve

- 当前基线：以 `uvisa-app-2.0` 当前 repo 状态为主；旧 `uvisa-app`/`/Users/charles/Downloads/uvisa-app` 仅历史参考，不是阻塞 gate。
- 最新 repo commit：`9256626 docs: pin Railway services for Lark closeout`。
- 上一轮 mobile-H5 gate commit：`a75a222 [verified] certify mobile H5 loop gate`。
- 栈：React 19 + Vite + TypeScript + Zustand + Tailwind + mock-server + Vitest + Playwright。
- 规模快照：78 routes / 72 screens / 22 service files。
- PRD：`U-VISA2.0 C 端产品需求文档（PRD v1.0）` 已读，27069 chars / 967 lines；产品逻辑必须按 PRD-derived 用例补证据。
- 页面功能测试与产品用户逻辑测试分层：`UI_TEST_CASES.md` ≠ `PRODUCT_USER_LOGIC_TEST_CASES.md`。
- 异常处理边界：先区分前端修改还是后端修改；后端代码在 `/Users/charles/Desktop/folder/work/uvisa-backend`。截至 2026-05-09，用户已明确授予后端写权限；若 evidence-first / 多模型业务逻辑分析判定“改后端”是最佳方案，可直接在后端仓库按 TDD 修改、验证并单独本地 commit。若未来权限不明确，则回退为只查看后端并在前端项目新增文档记录问题、证据与推荐后端改动。
- 前后端同时变更时，UI 回测的权威路径是本地前端连接本地真实后端；必须由 agent 操作浏览器完成回归与评分，记录 console/network/storage、截图、UI quality score、后端 health 与 exact service-path curl 证据。Mock 与 Railway/staging 仅作对照，不替代本地 full-stack 验收。

### 12.3 Test environment facts

- 用户端测换环境 URL、测试账号、登录邮箱、支付 PIN 只保存在本 Workpad section 6.1；不要复制到全局 memory、README、PR、issue。
- 当前线上登录入口为邮箱 OTP；验证码来源：浏览器打开的 Railway `uvisa-backend` → `Deploy Logs`，读取最新 `LOGIN` OTP；发送验证码后日志可能有延迟，要等待/刷新/过滤，不能立刻判失败。
- 本地浏览器/Railway 控制台预计有可复用登录态；Railway 项目是 `uvisa-test`，前端服务 `uvisa-app-tRnN`，后端服务 `uvisa-backend`。优先使用现有登录态通过截图查看 `uvisa-backend` Deploy Logs、相关服务 Deployments/package/build 状态。若登录态失效或需重新认证，只记录为访问 blocker；不要把账号凭据、cookies、session token 或一次性 OTP 写入 repo docs、Lark 评论、PR/issue 或全局 memory。
- 不保存一次性 OTP 值；含 OTP 的截图/日志视为敏感调试证据。

### 12.4 Verification status

- `pnpm test` latest run PASS（2026-05-10 19:50）：63 files passed / 505 passed / 1 skipped。
- `pnpm run build` PASS（2026-05-10 19:50）：`tsc -b && vite build` completed; existing Vite chunk-size warning remains (`index-tzjS8gWs.js` 546.63 kB > 500 kB), classified as P2 performance backlog.
- `pnpm exec playwright test tests/product-logic-prd.spec.ts --reporter=line` PASS：16/16（chromium + mobile-chrome，2026-05-09 16:07），含 USDC ERC20 充值地址不是 token contract 的防资金损失 guard。
- `BASE_URL=http://localhost:5173 pnpm run ui:regression` PASS：22 captures / 0 issues；最新报告 `test-results/ui-regression-2026-05-09T08-06-20-061Z/report.md`。注意：当前 Vite 只监听 `localhost/[::1]`，脚本默认 `127.0.0.1` 会 `ERR_CONNECTION_REFUSED`，需显式传 `BASE_URL=http://localhost:5173` 或调整脚本默认值。
- `BASE_URL=http://localhost:5173 pnpm run ui:mobile-h5` PASS：6/6 buckets to new-email-code，0 blockers，53 INFO；最新报告 `/tmp/uvisa-mobile-h5-loop-gate-1778314001330/report.md`。
- `pnpm lint` 当前 FAIL：139 errors / 8 warnings，集中在既有 React compiler lint、no-explicit-any、hook/purity 等；本轮 touched-file ESLint 0 errors（仅 i18n JSON ignored warnings）。代码 loop 若触碰相关文件，必须按 TDD/小步修复。
- Backend local full Spring Boot smoke PASS（2026-05-09 23:05）：backend fix `JdbcTimingDataSource` unwraps reflective `InvocationTargetException` so Flyway can degrade MySQL user-variable permission probe correctly; `FLYWAY_ENABLED=true` + production-like RocketMQ stayed running on 8080; Flyway applied 89 migrations to v940; `/actuator/health` 200/UP with DB/Redis UP; `/api/platform-config/topup` and `/api/platform-config/customer-service` 200. Targeted regression `JdbcTimingDataSourceTest` PASS; backend package PASS. Full backend test suite still not claimed green because existing ArchUnit/M1 gates remain separate cleanup.
- Workpad 自检脚本：`python3 ~/.hermes/scripts/uvisa_app_2_workpad_selfcheck.py` 应 PASS。

### 12.5 Red-line reminders for new sessions

- 不删功能/入口/字段/路由/按钮来修 dead UI。
- 不用 mock 成功掩盖真实后端路径不一致。
- 不在缺少 browser/Playwright 证据时宣称 UI A+。
- 前后端同时改动时，不用 mock/Railway 代替本地前端→本地后端的 browser 回测与 UI 评分。
- 每个 Lark 任务 closeout 必须同时满足本地检查通过、证据写回；若有前端代码修改，必须 push 并监控远端前端 Railway/package/build 到 success/healthy 或记录显式 blocker。后端部署状态当前无需关注，除非用户明确要求后端部署验证；后端代码变更仍必须有本地 backend test/compile 证据。
- 每轮修改后必须跑 test + build；删除文件前必须全项目引用扫描。
- 产品判断 evidence-first：PRD / 代码 / browser evidence / UI_TEST_CASES / PRODUCT_USER_LOGIC_TEST_CASES / ADR。
- Lark 任务验收前必须自动查询与任务相关的最新 PRD/产品文档、UI_TEST_CASES、PRODUCT_USER_LOGIC_TEST_CASES；不能只按任务标题或前端实现做 closeout。
- 若产品文档与 Lark 任务明确分歧，以 Lark 任务为本次验收优先级，但必须在 evidence/closeout 中记录分歧、按任务走的理由，以及是否需要产品文档回写。

### 12.6 Returned-for-improvement items

- 2026-05-10：Lark `6906ef6e` / `d0655d71`（通知交易类型区分 + 通知时间本地化）已从“前端 closeout”打回后端完善。多模型/红队复核结论：前端 `notification.service` 已能解析 `occurredAt/createdAt/updatedAt/timestamp/eventTime/timeAt` 并 fallback `time`，但后端 `/api/notifications` 当前只返回 `time = identity_user_notification.created_at`；该值来自 `NotificationDispatcher.notifyUser()` 的 `Instant.now()` 通知落库时刻，不等于业务事件时间/交易时间。产品逻辑 `PUL-MONEY-01` 要求 Home/Account/Tx/通知金额、币种、订单号、时间、状态一致；交易流水使用 `ledger_journal.posted_at`，通知使用独立 `created_at`，因此只能算 `partially_compliant_display_only`，不满足 `business_time_consistency`。后端需保留兼容 `time`，新增明确 `createdAt`（通知创建时间）、`occurredAt`（业务事件/账本 posted_at/到账确认时间）、原始 `type`，资金类通知按业务事件时间排序/展示策略需产品确认；完成前 Lark closeout 状态应为 `returned_for_backend_completion` / `not_fully_closed`。


### 12.7 前后端同步实施方案 (多模型认证 2026-05-11)

**3 模型审查**: Architecture/Correctness + Red-Team/Security + Practical/Simplicity
**认证状态**: certified_with_amendments
**方案文件**: /tmp/uvisa-fe-be-sync-plan.md

#### 实施顺序

| # | 任务 | Lark GUID | 风险 | 预估 | 前端 | 后端 |
|---|------|-----------|------|------|------|------|
| 1 | 通知子类型+时间 | 6906ef6e+d0655d71 | LOW | 4h | notification.service.ts: 保留inferTransactionType作fallback, 优先用subType | NotificationController.toItem(): 添加subType映射 |
| 2 | 收款信息脱敏 | ee902251+c1ec1131 | MED | 8h | SwiftDetailsScreen/CnyBankScreen: 已有完整安全检查, 最小改动 | **CRITICAL**: TopupController返回未脱敏数据! 修复+AES-256-GCM加密 |
| 3 | 单点登录 | ed1cb905 | HIGH | 12h | auth.store.ts: SESSION_EXPIRED→特定toast+重定向 | Redis active-session方案: auth:session:{userId}, sid claim, 校验 |

#### 关键决策

- **SSO 方案**: Redis Active-Session (方案B), 非 session_version (方案A)
  - 理由: 无DB migration, 原子SET, 已有Redis依赖, TTL自然过期
- **通知 fallback**: inferTransactionType() 保留作 fallback, 不删除
  - 理由: 缓存的旧通知没有 subType 字段
- **收款信息**: 发现 ACTIVE DATA LEAK (TopupController未脱敏)
  - 优先级提升: 必须在加密之前先修复 masking

#### 红队发现的 CRITICAL 问题

1. **TopupController 数据泄露**: getSwiftDetails()/getCnyBankDetails() 返回原始 config_json, 未脱敏
2. **SSO refresh token 漏洞**: rotate() 未校验 session, 被踢设备的 refresh token 仍可刷新
3. **旧 access token 未 blacklist**: 新登录时必须 blacklist 旧 access token
4. **CnyBankScreen 校验弱于 SwiftDetailsScreen**: 缺少 looksLikeInternalPayload/hasLongDigitRun

### 12.8 Project profile update — backend-aware regression gate (2026-05-11)

已新增项目画像：`/Users/charles/.hermes/project-profiles/uvisa-app-2.0.json`。

结论：当前前端回归测试只能覆盖前端逻辑、mock/fixture 契约、页面渲染和构建类型问题；不能自动证明真实后端 API 已填充、字段语义正确、权限/状态机安全、资金/通知/时间口径一致。任务 closeout 必须按风险分层标注：

- `frontend_unit_build`: Vitest / pnpm test / pnpm build，证明前端代码不回归。
- `mock_contract`: 仅证明前端预期契约，不代表真实后端。
- `real_backend_contract`: 需要读 backend controller/service/entity/repository；必要时本地真实后端或 live/test backend Playwright/curl 证明。
- `backend_tdd`: 若 backend 是正确修复点，直接在 `/Users/charles/Desktop/folder/work/uvisa-backend` 按 TDD 修改，单独 commit；使用 openjdk@21 跑 targeted test + compile/package。
- `task_focused_verification`: 测试目标优先服务 Lark 任务验收；在满足最佳安全方案与项目红线前提下贴合任务要求，不把 backend-aware gate 扩成无边界后端审计。后端相关任务由多模型先分类最佳落点（frontend/backend/contract/shared infrastructure）再 PUA-loop 落地。
- `remote_frontend_build`: 前端修改后按用户要求 push 并监控远端前端打包；后端部署状态当前不纳入 closeout gate，除非用户另行要求。

触发 backend-aware gate 的任务类型：auth/OTP/PIN/payment password/2FA/device/session/KYC/card/wallet/topup/exchange/remittance/notification/account/profile/money/status/time/order 字段，或任何 PRD source-of-truth 语义。多模型方案必须覆盖这些后端完善点，不能只给前端兼容 shim。

