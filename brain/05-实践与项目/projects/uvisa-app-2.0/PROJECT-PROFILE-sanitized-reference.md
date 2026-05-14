# UVISA 2.0 Sanitized Project Profile Reference

Source: `/Users/charles/Downloads/PROJECT-PROFILE.md`
Source sha256: `9dc2b1ecf9167f248307e445369a246e777921b99f486c29b40eeda1cd002ac2`
Generated: `2026-05-13T03:45:47.575803+00:00`
Status: `truth_grounded_advisory`, not full PRD/code certification.

Purpose: make the useful PROJECT-PROFILE content available during future UVISA task execution without leaking credentials or overwriting the canonical Hermes operational profile.

Hard rules for use:
- This reference is advisory/navigation unless a specific claim is verified against current PRD PDF, code, Lark task body/comments, PM screenshot, or explicit user instruction.
- Do not treat this file as a replacement for `/Users/charles/.hermes/project-profiles/uvisa-app-2.0.json`.
- Do not copy credentials, OTPs, test accounts, cookies, tokens, `.env` values, or private runtime identifiers into project profile/global memory/public docs.
- Canonical local repos for this Hermes setup remain:
  - Frontend: `/Users/charles/Desktop/folder/work/uvisa-app-2.0`
  - Backend: `/Users/charles/Desktop/folder/work/uvisa-backend`

## Evidence tiers

- `verified_prd`: independently checked against current PRD/PDF section/page.
- `verified_code`: independently checked against current repo source with file/line.
- `lark_primary`: current Lark task body/comment/PM screenshot/prototype for this delivery.
- `secondary_source`: markdown/dev-guide/product-manual/team note, useful but not authoritative by itself.
- `team_claim`: human/team assignment/process context; may be stale.
- `tbd`: explicitly TBD / pending Roy / pending owner confirmation.
- `advisory`: useful navigation or execution hint only.

## Product positioning

## 0. 一句话产品定位

> **UVISA 2.0 是面向中国境内身份证用户的跨境综合金融服务移动应用（iOS/Android）**，由 Dena Trust Limited 运营，整合多币种钱包、跨境汇款、外汇兑换、U-Visa 卡消费、理财投资 5 大能力。**禁止 C 端自主注册**，所有新用户必须由**理财顾问通过 PAD 端现场开户**，客户在 UVISA APP 上完成转账/换汇/申购/卡管理，**Admin 后台**做账务确认、KYC 审核、双段出金审批与全栈监控。卡片服务由**吉薪（Gsalary）**提供 BIN 与卡管理。

**证据**：✅ C 端 PRD §2.1 产品定位（page 3）+ ✅ §2.3 业务原则"❌ 不开放 C 端自主注册"

**核心承诺四词**：安全 · 私密 · 增值 · 无界 ⚠️（来源 product-manual.md，未在 PRD 验证）

## Three-terminal architecture and global state

## 2. 三端架构与职责矩阵

> ✅ 来源：PAD PRD v2.0 §2 三端职责矩阵（page 7）

| 维度 | **PAD 端**（理财师工作台）| **C 端 UVISA APP**（客户）| **Admin 后台**（运营）|
|---|---|---|---|
| 用户角色 | 理财师（账号+密码登录）| 客户本人（手机号+短信验证码 / 密码登录）| 总部 / 网点负责人 / 业务管理员 |
| 端 viewport | 800×1280 锁竖屏 | 390×844 手机 | ≥1280×800 桌面 Web |
| 部署形态 | Pad 独立 APK（WebView 套壳）| App 原生 | Admin 桌面 Web |
| 工程仓 | `uvisa-pad-ui/` | `uvisa-app/` | `uvisa-admin-new/uvisa-admin/` |
| 核心操作 | 为新客户开户 + 办卡（17 步）| 转账 / 换汇 / 申购 / 卡管理 | 管控理财师 / Pad / 客户 / 产品 / 系统 |
| 数据写入 | 创建 OnboardingSession + 提交激活 | 创建交易订单 | 创建理财师 / 分配 Pad / 审核 KYC / 配置产品 |
| 数据读取 | 仅理财师下属客户的持仓概要 | 客户本人全部数据 | 全量数据 |
| 是否能看资产金额 | ❌ 不能（仅看持仓产品名）| ✅ 自有数据 | ✅ 全部 |
| 是否能看出入金 | ❌ | ✅ | ✅ |
| 配置能力 | ❌ | ❌ | ✅ Pad 下载二维码 / 产品 / 限额 / i18n |

### 2.1 全局状态机（三个核心状态）

> ✅ 来源：PAD PRD v2.0 §1.3（page 6）

```
Onboarding Session              Customer.kycStatus           UvisaCard.activationStatus
─────────────────              ──────────────────           ─────────────────────────
DRAFT (Pad 端进行中)            AUTO_PASSED                  INACTIVE (待激活)
   │ 17 步走完                   MANUAL_PASSED                  │ 提交激活
   ▼                             SUBMITTED                     ▼
ARCHIVED                        REJECTED                     PENDING (激活中)
   │ 后端创建 Customer            EXPIRED                       │ 查询接口返回
   ▼                                                          ▼
                                                            ACTIVE / FROZEN / FAILED
```

## C端 module navigation

## 3. C 端业务模块（PRD §6.1-6.11，11 个模块）

> ✅ **所有 11 个模块直接对应 C 端 PRD §6 子章节**。每个模块给：① PRD 锚点 ② 核心规则 ③ Backend Controller ④ 主责。

### 3.1 ⭐ AUTH 启动与身份（§6.1）

✅ PRD §6.1 page 16-17

| 项 | 内容 |
|---|---|
| **页面** | AUTH-01 启动页 / AUTH-02 强制更新 / AUTH-03 可选更新 / AUTH-04+04B 登录（短信 OR 密码）/ AUTH-05/05B/05C 重置密码 / AUTH-06/07/07B/10 首次引导 / AUTH-11 会话过期 |
| **关键规则** | 登录默认"手机号+短信验证码"，密码登录次选；密码登录连错 5 次 → 账户锁定 30 分钟；短信 60s 倒计时 / 日内上限 10 次 |
| **首次引导** | ❌ AUTH-08/09 二次验证绑定已永久删除（PAD 端开户已完成，C 端不引导）|
| **Backend** | `AuthController` ✅ + `MfaController` ✅ + `AppVersionController` ✅ |
| **主责** | 刘（后端 JWT + 短信 stub）+ 郭（C 端登录页）|

### 3.2 ⭐ HOME 资产首页（§6.2）

✅ PRD §6.2 page 18-20

| 项 | 内容 |
|---|---|
| **页面** | HOME-01 资产页 / HOME-02 "更多"抽屉 / HOME-03 通知中心 / HOME-04 通知详情 |
| **总资产** | 默认计价 CNY，副数字显示 USD 等值；🙈 控制资产可见性记忆用户选择 |
| **4 主操作** | [+ 转入] [⇄ 兑换] [✈ 转出] [… 更多]，等宽不可横滑 |
| **钱包列表** | 法币区（Onshore CNY / Offshore CNH / USD / HKD）+ 加密区（USDT / USDC）|
| **下拉刷新** | 全页刷新（总资产 + 余额 + 最近交易）；30-60s 后台静默轮询 |
| **通知中心** | 3 Tab：系统 / 交易 / 理财（交易 Tab 带未读红点）|
| **Backend** | `WalletController` ✅ + `TransactionController` ✅ + `NotificationController` ✅ |
| **主责** | 刘 + 郭 |

### 3.3 ⭐ ACCT 账户详情（§6.3）

✅ PRD §6.3 page 20-22

| 项 | 内容 |
|---|---|
| **统一模板** | 所有 6 个钱包详情页采用统一"三按钮"结构，第三按钮文案随账户类型变化 |
| **6 钱包路由表** | Onshore CNY → PAY-CNY-01 / Offshore CNH/USD/HKD → REMIT-01 / USDT/USDC → PAY-USDT-01 |
| **统一文案** | ACCT_CONFIGS sendLabel **全部统一为"转出"**（不再使用"提现/汇款"区分文案）|
| **账户信息 Bottom Sheet** | 右上角三点 menu — 加密：资产类型 / 支持网络 / 单笔最低 / 到账时间；Onshore CNY：充值方式 / 入金限额 / 订单过期 1 天；SWIFT 系：充值方式 SWIFT 国际电汇 / 入金限额视银行政策 |
| **交易记录列表** | 顶部 4 等分 Tab：全部 / 转入 / 转出 / 兑换；行布局采用 DesignRule-01（三列：图标 / 主信息 / 金额）|
| **交易详情** | data-action="tx-detail" 携 (txType, ccy) 分发到 TOPUP-CNY-04 / TOPUP-SWIFT-03 / TOPUP-USDT-03 / PAY-CNY-05 / REMIT-10 / PAY-USDT-06 / EX-06 等具体详情页 |
| **5 种交易状态** | ✅ 已完成 / ⏳ 进行中 / ❌ 交易失败 / ⏰ 已过期（仅 Onshore CNY 充值订单 1 天未支付时触发）|
| **Backend** | `WalletController` + `TransactionController` ✅ |

### 3.4 ⭐ TOPUP 转入（§6.4）

✅ PRD §6.4 page 22 + §4.2 关键决策 page 5

| 通路 | 关键规则 |
|---|---|
| **Onshore CNY** | 付款卡仅一张（**开户时绑定，不可改**）；点"我已转账"创建虚拟订单等待入账确认；订单 **1 天**有效期 |
| **Offshore CNH / USD / HKD** | 走 SWIFT 国际电汇，**4 页流程**（金额 → 须知 → 银行详情 → 处理中）|
| **USDT / USDC** | 链上充值；**地址前 6 后 6 高亮**（金色 #D4AF7A）；选错链不可逆 |
| **链上确认对外** | 使用第三方加密资产托管，**不暴露具体区块确认数**；对外文案统一为"通常 5-15 分钟到账" |
| **HOME-02 抽屉** | v1.0 极简化为只有"我的链上充值地址" |

**Backend**：`TopupController` ✅ + `CoboWebhookController` ✅（Cobo HMAC BIZ-SAFE-SIGN）

**主责**：刘（TopupController + 法币人工 / Cobo 自动 / Debit 自动 三入金）+ 郭（C 端 3 通路表单）+ hotlei（Cobo webhook 配置）

### 3.5 ⭐ EX 兑换（§6.5）

✅ PRD §6.5 page 23 + §4.3 关键决策

| 项 | 内容 |
|---|---|
| **币种切换** | 走 Bottom Sheet（**不跳二级页**）|
| **汇率刷新中间态** | 切币时金额置灰 + spinner + CTA 置灰 1.5s |
| **大额二次确认** | **>10 万 USD 等值**需二次确认 + 强制勾选 |
| **倒计时** | 汇率锁定 30 秒倒计时（≤5 秒进入 warning 黄）|

**Backend**：`ExchangeController` ✅（4 分录双分录平衡）+ `FxRateController` ✅

**主责**：刘 + 郭 + Roy（汇率口径）

### 3.6 ⭐ REMIT 汇款 + PAYEE 收款人（§6.6）

✅ PRD §6.6 page 24-25 + §4.4 关键决策

> **关键纠正（v1.0 偏差）**：REMIT **不是独立业务线**，而是**内嵌 FX 的跨币种汇款**！

| 项 | 内容 |
|---|---|
| **流程倒置** | HOME → REMIT-02 选收款人 → REMIT-01 输入金额 → REMIT-07 预览 |
| **内嵌 FX** | 用户"汇出 A 币种 → 收款人收到 B 币种"，**无需先去 EX 兑换再来汇款** |
| **双输入双绑定** | 汇出金额 ↔ 收到金额 |
| **汇率展示** | 两区块分隔条上（`1 A = X.XXXX B`）+ 锁定 30 秒倒计时 |
| **付款方式不可切换** | 按收款人方式自动展示：SWIFT 国际汇款 / 电子钱包（加密资产收款人走"链上转账"不属代付）|
| **收款人 3 种独立流程** | ① SWIFT 国际电汇（国家=中国时强制省/市/详细地址/邮编）② 电子钱包（合作方接口下拉：Alipay/WeChat Pay/PayPal/Wise 等）③ 加密资产（EVM 地址正则 `/^0x[a-fA-F0-9]{40}$/`）|
| **REMIT-10 时间轴** | 处理中 / 审核拒绝 / 已完成 |
| **汇款目的（Purpose）** | 默认 FAMILY_SUPPORT，UI 上不展示 |

**Backend**：`RemitController` ✅ + `PayeeController` ✅

**主责**：刘 + 郭 + Roy

### 3.7 ⭐ PAYOUT 转出（§6.7）

✅ PRD §6.7 page 25-26 + §4.1 资金外流双因子

| 项 | 内容 |
|---|---|
| **入口** | HOME 主页"转出"按钮 → PAYOUT-01 转出币种选择器 |
| **资金外流双因子验证** | **基于用户 2FA 策略**（在 MY-16 配置的"支付密码 / 手机 / 邮箱"3 项中按优先级选取 2 个因子）；**两个因子分两页执行** |
| **默认组合** | 第 1 步 支付密码 → 第 2 步 邮箱验证码 |
| **第 2 步切换** | 当用户开启手机验证时，可点击"切换到手机验证码" |
| **PAY-USDT 链路** | 03 → 04（因子 1）→ 04B（因子 2）→ 05 |
| **REMIT 链路** | 07 → 08（因子 1）→ 08B（因子 2）→ 09 |
| **PAY-CNY 链路** | 02 → 03（因子 1）→ 03B（因子 2）→ 04 |

**Backend**：`PayoutController` ✅

**主责**：刘（FundProtectionService + 24h 资金保护期）+ 郭 + Sec

### 3.8 ⭐ CARD U-Visa 卡（§6.8）

✅ PRD §6.8 page 26

> **关键纠正（v1.0 偏差）**：v1.0 **仅实体卡**，**5 种卡状态**（不是 9 种）

| 项 | 内容 |
|---|---|
| **v1.0 范围** | **仅实体卡**（由技术助理上门交付，不走自助申请）|
| **单用户单卡** | 多卡管理与虚拟卡归档至 v2.0 |
| **卡面深色风格** | 品牌区 / 非接触图标 / Balance / Status / Physical Card / VISA / 卡号尾号 9055（脱敏展示）|
| **5 种卡状态** | 正常 / 冻结中 / 已冻结 / 解冻中 / 已解冻 |
| **卡详情交互** | 底部弹窗菜单：卡片信息 / 重置 ATM 取现密码 / 限额管理 |
| **冻解限流** | 1 小时内 3 次限流 |
| **注销冷静期** | 72h 内可撤销 |

**Backend**：`CardController` ✅ + `GsalaryWebhookController` ✅（吉薪 RSA 验签）

**主责**：刘（卡 + 吉薪集成）+ 郭（卡管理 UI）+ Sec

> ⚠️ **Admin 端卡管理**与 C 端不同：Admin PRD §1.1 说"**9 态卡片状态机**"（待与 C 端 5 态对齐 — Admin 多看到了 INACTIVE/PENDING/FAILED 等开户中状态）

### 3.9 ⭐ INV 理财（§6.9）

✅ PRD §6.9 page 27

> **关键纠正（v1.0 偏差）**：v1.0 **仅"稳健"产品**，基金/量化整体归档至 v2.0

| 项 | 内容 |
|---|---|
| **v1.0 范围** | **仅"稳健"产品**（含活期、双币稳健、固定收益、Onshore CNY 大额存单等）|
| **INV-01 保留 3 Tab** | "基金"/"量化"显示空状态卡（v1 暂无此类型，引导回稳健）|
| **量化与基金类** | 整体归档至 v2.0 |
| **提前赎回** | INV-21 红色警示 + 强制 checkbox + danger CTA + **提前赎回管理费明示** |
| **数字** | 保留两位小数 |

**Backend**：`WealthController` ✅

**主责**：刘（WealthController + InterestAccrualJob）+ 郭 + Roy（产品要素表 / 风险揭示文案）

> ⚠️ **派息真账本（M4 缺口）**：当前只累 `accrued_interest`，**未真出 ledger interest_expense 分录**。Admin PRD §1.1 说"双账本派息"是 admin 后台职责之一。

### 3.10 ⭐ MY 个人中心（§6.10）

✅ PRD §6.10 page 27

| 项 | 内容 |
|---|---|
| **KYC 信息（MY-17）** | **全部只读**，修改通过理财顾问 + PAD 端 |
| **MY-06 修改手机号** | 自助二步验证（默认 支付密码 + 邮箱验证码，可切 SMS）→ 输入新手机号 + 新号验证码 |
| **支付密码修改双路径** | 知道原密码 vs 忘记重置，汇聚到 MY-12 成功页 |
| **MY-16 双重验证策略配置** | 用户自助配置"支付密码 / 手机 / 邮箱" 3 种验证方式，至少启用 2 项才能完成 T2 验证 |
| **MY-27 登录设备管理** | 查看所有登录设备，支持"信任 / 删除"|

**Backend**：`MeController` ✅ + `DeviceController` ✅ + `MfaController` ✅

**主责**：刘 + 郭 + Sec

### 3.11 ⭐ GLOBAL 全局与异常（§6.11）

✅ PRD §6.11（未深读，仅目录确认存在 — ❌ 完整章节待 Roy 补充）

| 项 | 内容（来自 PRD §1.6 异常登录文案） |
|---|---|
| **手机号未注册** | "该手机号未注册，请联系平台客服开通账户" |
| **密码错误** | "密码不正确，剩余尝试次数：N 次" |
| **密码错误超限** | "密码错误次数过多，账户已锁定 30 分钟" |
| **账户已冻结** | "账户已冻结，请联系客服处理" |
| **账户已注销** | "该账户已注销，无法登录" |
| **短信/验证码超限** | "今日获取次数已达上限，请明日再试" |

**主责**：郭（统一错误处理组件）+ Roy（异常文案规范）

## Admin module navigation

## 4. Admin 业务模块（PRD §1.1，11 个职责领域）

> ✅ 来源：Admin PRD §1.1 业务定位（page 6）+ §2.1 路由表（page 9-10）

### 4.1 Admin 11 个职责领域

| # | 职责 | 核心场景 | 路由 |
|---|---|---|---|
| 1 | **用户管理** | KYC 复核 / 过期用户冻结 / 用户详情聚合查看 / **PII 安全访问审计** | `/users` `/users/:id` `/kyc` |
| 2 | **U-Visa 卡管理** | **9 态卡片状态机** / 激活流水台 / 卡交易订单（DCC / 退款 / 预授权）| `/cards` `/cards/activation` `/cards/transactions` `/cards/:id` |
| 3 | **入金审核** | **Dena HSBC 公户法币入金**（人工 + GA 拨款）/ Cobo 链上自动入金 / Debit 自动入金 / HSBC 退款 | `/inflows/hsbc` `/inflows/cobo` `/inflows/debit` `/inflows/refunds` |
| 4 | **出金审核** | **双段审核**（OPS 初审 + 财务终审 GA）/ 跨币种代付 / 链上失败重发 | `/outflows` `/outflows/gsalary` `/outflows/refunds` `/outflows/limits` |
| 5 | **通道配置** | 吉薪 BANK 通道 / 吉薪 WALLET 通道（按 payment_method）/ Cobo CHAIN 网络-路由 | `/routes/bank` `/routes/wallet` `/routes/chain` |
| 6 | **钱包总览** | 三大类（资金/理财/平台）的双账本视图 / 7 大类型手续费透视 / 派息池注资 | `/wallets` `/wallets/currencies` `/transactions` |
| 7 | **换汇** | 多源汇率比对（去极值平均）/ 换汇通道配置（固定+百分比双轨）/ 换汇记录三栏拆分 | `/wallets/fx` `/wallets/fx/sources` `/wallets/fx/records` |
| 8 | **理财** | **平台 / U-VISA 双类产品** / 活期 + 定期 + 封闭期 / 提前赎回管理费 / 双账本派息 | `/products` `/holdings` |
| 9 | **理财师/网点** | **三维分润**（网点 × 理财师 × 产品）/ Pad 状态机 / 业绩统计与下钻 | `/advisors` `/payees` `/payers` |
| 10 | **客服** | 自营会话 / 工单状态机 / 第三方 IM 内嵌（Intercom/Zendesk/Freshchat/Tidio）| `/cs/conversations` `/cs/tickets` `/cs/external` |
| 11 | **系统设置** | 角色与权限矩阵 / admin 用户 / **多语言 5 种** / 验证码服务商 / 维护/发版/APK | `/system/{roles,admins,i18n,verification,maintenance,ga}` |

### 4.2 Admin 53 条权限码（按 13 个域）

✅ 来源：Admin PRD §3.2（page 13-18）

| 域 | 权限码示例 |
|---|---|
| **kyc** | `kyc.review` `kyc.expire_freeze` |
| **card** | `card.activate` `card.activate_review` `card.limit_change` `card.close` |
| **inflow** | `inflow.hsbc.review` `inflow.hsbc.treasury_credit`(GA) `inflow.hsbc.refund_record` `inflow.hsbc.refund_review`(GA) `inflow.cobo.read` `inflow.cobo.held_unlock`(GA) `inflow.debit.read` |
| **outflow** | `outflow.review_op` `outflow.review_treasury`(GA) `outflow.refund_record` |
| **route** | `route.bank.config` `route.bank.toggle`(GA) `route.wallet.config` `route.wallet.toggle`(GA) `route.chain.config` |
| **fx** | `fx.config` `fx.source_config` `fx.pause`(GA) |
| **invest** | `product.draft` `product.list`(GA) `product.rate_change`(GA) `product.delist` `advisor.unbind` `advisor.assign` `revenue.manual_settle` |
| **system** | `i18n.edit` `system.role_manage` `system.user_manage` `system.reset_ga`(GA) `system.reset_password`(GA) |
| **cs** | `cs.conversation` `cs.ticket` |
| **approval** | `approval.approve` |
| **ops** | `ops.maintenance_toggle`(GA) `ops.release_force`(GA) `ops.release_hot` |
| **users** | `users.read` `users.contact` `users.freeze`(GA) `users.security_read` `users.kyc_read`(PII) `users.card_read` |
| **payees** | `payees.read` `payees.crud` `payers.read` `payers.crud` |
| **pii** | `pii.kyc_photo`(PII) `pii.full_card_no`(PII) |

> (GA) = 需要 GA 二次验证；(PII) = 触碰敏感数据，写访问审计

### 4.3 Admin 7 个内置角色（ROLES）

✅ 来源：Admin PRD §3.3（page 18-19）

| 角色 ID | 名称 | 描述 | 成员数 |
|---|---|---|---|
| `R-SUPER` | 超级管理员 | 全部 53 条权限 | 1 |
| `R-OPS-REV` | 中台复核员 | KYC 复核 + 卡激活复核 | 2 |
| `R-FIN-OP` | 财务（初审）| HSBC 初审 + 出款初审 + 退款录入 | 1 |
| `R-FIN-TR` | 财务（终审 GA）| HSBC 终审拨款 + 出款终审 + 退款复核（必 GA）| 1 |
| `R-BIZ` | 业务管理员 | 通道 / 产品 / FX / 多语言 / 理财师管理 | 1 |
| `R-CS` | 客服 | 客服会话 + 工单 | 2 |
| `R-TECH` | 技术 | 维护开关 + 版本发布 + FX 源配置 + 审计读 | 1 |

### 4.4 Admin 38 个路由全清单

✅ 来源：Admin PRD §2.1（page 9-10）

完整 38 路由见 PRD §2.1。Backend Controller 数量：35 个 `Admin*Controller` ✅。

## PAD 17-step onboarding navigation

## 5. PAD 17 步开户流程

> ✅ 来源：PAD PRD v2.0 §3.7（page 13-20）

### 5.1 PAD v2.0 关键改动（vs v1.0）

| 维度 | v1.0 | v2.0 |
|---|---|---|
| 流程总步数 | 18 | **17**（旧 11/18 `bind-card-success` 合并到 10/17）|
| Step 6 OCR | 直接展示识别表单 | **6 阶段状态机**（capture-front → preview-front → capture-back → preview-back → ocr-running → ocr-done）|
| Step 7 OTP 通道 | 总是 PHONE+EMAIL 二选一 | 仅展示 Step 1 已验证的通道 |
| Step 9 主 CTA | "客户已收到短信，下一步" | **"客户已确认完成转款"**（理财师当面确认）|
| Step 10 超时 | 5 分钟 | **3 分钟**（旧 5 分钟） |
| 共享 enum 数据 | 无 | `data/banks.ts` / `data/regions.ts` / `data/profile.ts` |
| Mock 跳过按钮 | 无 | 所有异常状态附 `[mock] 模拟正常状态`（仅开发期可见）|

### 5.2 PAD 17 步详细清单

| Step | 名称 | 关键 API / 字段 |
|---|---|---|
| **1/17** | 身份验证（verify）| `POST /onboarding/{sid}/verify/{send-otp,check-otp}`；双通道 OTP，至少一个必须当场验证 |
| **2/17** | 客户信息（basic）| 4 字段姓名 + `<DateField/>` 生日 + 地址拆分省+详细 + 职业枚举 + 行业枚举 + 工作单位 + 收入区间 + 学历 |
| **3/17** | 协议确认（agreements）| 3 份协议（开户/隐私/风险揭示）滚动到底才能勾选 |
| **4/17** | 财富来源声明（sof）| `primarySource` (SALARY/BUSINESS/INHERITANCE/INVESTMENT/OTHER) + `isPep` |
| **5/17** | 实人认证（kyc-liveness）| `POST /kyc/liveness/{start,finish}`；生产 SDK（旷视/百度/腾讯云）；5% 失败概率 |
| **6/17** | 证件信息核对（kyc-result）**v2.0 大改**| 6 阶段状态机 + `POST /kyc/ocr/{upload-shot,run}` |
| **7/17** | 开通账户（bank-open）| `POST /bank/account/open` → `{accountNo (21 位), receiptNo, openedAt, status}`；同步接口 5-15 秒 |
| **8/17** | 绑定储蓄卡（bind-card）| bankName 13 选 1 / cardNo 16-19 位 / **cardHolder 必与开户人一致** / holderReservedPhone 11 位 |
| **9/17** | 储蓄账户绑定（bind-card-sms）**v2.0 大改**| 平台免责声明 3 条 / 主 CTA"客户已确认完成转款" / `POST /bind-card/transfer-confirmed` |
| **10/17** | 转账校验（bind-card-poll）**v2.0 改名+大改**| 三状态视图（waiting/verified/expired）/ 1 秒 1 次轮询 / 超时 3 分钟 |
| **11/17** | 设置登录密码（app-login-pwd）| 8-20 位含字母+数字；`POST /app-login-pwd/set {sid, pwdHash}` |
| **12/17** | 实体卡确认（card-intro）| 7 阶段循环动画 ~11 秒一轮 + Pre-checklist 5 项 |
| **13/17** | 卡片信息采集（card-scan）| 摄像头扫描 (getUserMedia) → OCR 解析 16 位卡号；8% OCR 失败兜底手动 |
| **14/17** | 设置卡密码（card-pin）| 6 位 ATM PIN；二次确认时键盘重新随机洗牌 |
| **15/17** | 提交激活（card-activate）| `POST /card/activate/submit {sid, pinHash, activationCode}` → `{ack:"U", traceId}`；INACTIVE → PENDING |
| **16/17** | 激活进行中（activation-waiting）| `GET /card/status?sid`；每 3 秒查询；软超时 60 秒 |
| **17/17** | 开户完成（complete）| 二维码下载 UVISA APP + 开户交付清单（账户/银行账户/储蓄卡/UVisa 卡）+ `archiveAndClose(sessionId)` |

**Backend**：`PadController` ✅（28 个 endpoint，见 [pad-integration-matrix.md](uvisa-docs/pad-integration-matrix.md)）+ `PadGaController` ✅

**主责**：刘（PadController + 17 步 service）+ 郭（uvisa-pad-ui）+ Roy（17 步流程边界）+ Zhong（17 步 e2e）

## Backend topology and integrations

## 6. 工程拓扑与 Backend Controllers

### 6.1 仓库与服务

✅ 来源：[~/.claude/skills/uvisa/SKILL.md](~/.claude/skills/uvisa/SKILL.md) §3 + Railway 真实部署

| 工程 | 仓库 | Railway service | 端口 | DRI |
|---|---|---|---|---|
| uvisa-backend | cryptolxd/uvisa-backend | uvisa-backend | 8080 | 刘 |
| uvisa-app（C 端 H5）| cryptolxd/uvisa-app | uvisa-app-tRnN | 5173 | 郭 |
| uvisa-admin（管理后台）| cryptolxd/uvisa-admin | uvisa-admin | 5174 | 郭 |
| uvisa-pad-ui（PAD 联调）| cryptolxd/uvisa-pad | uvisa-pad | 5176 | 郭 |
| 文档 | cryptolxd/uvisa-docs | — | — | Roy + 全员 |

### 6.2 Backend 模块拓扑

✅ 来源：[~/.claude/skills/uvisa/SKILL.md](~/.claude/skills/uvisa/SKILL.md) §3

```
api/
  api-public        24+ 个 Controller — C 端 + 公共
  api-admin         35+ 个 Admin*Controller + PadController + PadGaController
domain/
  identity / ledger / wallet / topup / payout / fx / wealth / notification / cs / routes
integration/
  adp-cobo          Cobo MPC（USDT/USDC 链上）— HMAC BIZ-SAFE-SIGN
  adp-hsbc          HSBC SWIFT 银行通路
  adp-gsalary       吉薪卡服务 — RSA 验签
  adp-minsheng      民生银行 CNY 通路
platform/
  platform-core / platform-audit / platform-outbox / platform-idempotency
app/uvisa-app       Spring Boot 入口
```

### 6.3 Backend 76 个 Controller 真实清单

✅ 来源：`find uvisa-backend -name "*Controller.java"` 2026-05-12

**C 端公共（24 个）**：AuthController / TopupController / PayoutController / ExchangeController / WealthController / CardController / KycController / CsController / NotificationController / WalletController / DeviceController / FxRateController / MeController / MfaController / QuotaController / RemitController / FeatureFlagController / TransactionController / PayeeController / PadGaController / PushTokenController / AppVersionController / PlatformPublicConfigController / HealthController

**Admin（35 个 `Admin*Controller`）**：AdminAuthController / AdminMeController / AdminUserController / AdminCardsController / AdminKycController / AdminKycApplicationController / AdminKycCaseController / AdminInflowController / AdminInflowCoboController / AdminInflowDebitController / AdminInflowHsbcController / AdminOutflowController / AdminApprovalController / AdminWalletController / AdminWalletQueryController / AdminWalletsController / AdminWealthController / AdminFxRateController / AdminGaController / AdminAdvisorController / AdminBranchController / AdminBranchAdvisorProductShareController / AdminCsConversationController / AdminCsExternalController / AdminCsLookupController / AdminCsTicketController / AdminCurrencyController / AdminDashboardController / AdminFeatureFlagController / AdminGlobalCounterpartyController / AdminGsalaryConfigController / AdminI18nController / AdminMaintenanceController / AdminMembersController / AdminNotifyTestController / AdminOutboxController / AdminPadDeviceController / AdminPlatformPublicConfigController / AdminReconciliationController / AdminRiskLimitController / AdminRolesController / AdminRoutesController / AdminSystemController / AdminTransactionController / AdminVerificationProviderController / AdminWebhookEventController

**PAD（2 个）**：PadController / PadGaController

**Webhook（3 个）**：GsalaryWebhookController（RSA）/ CoboWebhookController（HMAC）/ KycWebhookController

**测试 / Legacy**：GsalaryTestController / LegacyAdminOutflowController / LegacyApiController

### 6.4 集成上游

✅ 来源：Admin PRD §1.1 + SKILL.md §4

| 上游 | 中文 | 用途 | 验签 |
|---|---|---|---|
| **Gsalary** | 吉薪 | U-Visa 卡发行 / 卡管理 / 卡交易 | **RSA**（publicKey 验签）|
| **Cobo** | — | USDT/USDC 链上 MPC 托管 | **HMAC BIZ-SAFE-SIGN** |
| **HSBC** | — | Dena 公户 SWIFT 美金/港币电汇 | （TBD）|
| **民生银行** | — | Onshore CNY 充值通道 | （TBD）|
| **Debit** | — | 借记卡入金 | （TBD）|

## Shared invariants and design anchors

## 7. 共享底层

### 7.1 6 个钱包（v1.0 全量）

✅ 来源：C 端 PRD §3.2（page 4）— **纠正 v1.0 偏差**

| 钱包 | 主标签 | 副标签 | 通道 |
|---|---|---|---|
| 境内 CNY | Onshore CNY | Onshore CNY | 境内合作银行 |
| 境外 CNY | Offshore CNH | Offshore CNH | 境外托管银行 |
| 美元 | USD | US Dollar | 境外托管银行 (SWIFT) |
| 港币 | HKD | Hong Kong Dollar | 境外托管银行 (SWIFT) |
| Tether | USDT | Tether | 链上 EVM |
| USD Coin | USDC | USD Coin | 链上 EVM |

### 7.2 链上网络（仅 EVM）

✅ 来源：C 端 PRD §3.3（page 4）— **纠正 v1.0 偏差："不支持 TRC20、Solana 等非 EVM 链"**

| 网络 | 别名 | 适用币种 |
|---|---|---|
| BSC | BNB Smart Chain (BEP20) | USDT / USDC |
| Arbitrum | Arbitrum One | USDT / USDC |
| Base | Base | USDT / USDC |
| Ethereum | ERC20 | USDT / USDC |

EVM 地址正则：`/^0x[a-fA-F0-9]{40}$/`

### 7.3 Ledger 不变量

⚠️ 来源：[uvisa-docs/20-dev-guide.md](uvisa-docs/20-dev-guide.md) §安全合规速查

| 不变量 | 实现 |
|---|---|
| `ledger_entry` append-only | V1 触发器禁 UPDATE/DELETE |
| `audit_event` append-only | V1 触发器禁 UPDATE/DELETE |
| 双分录平衡 | 业务侧每个 journal `SUM(DEBIT) == SUM(CREDIT)` per currency |
| 资金类 SERIALIZABLE | `@Transactional(SERIALIZABLE)` |
| 幂等 | 所有写路径 `idempotency_key` 唯一索引兜底 |

### 7.4 身份验证强度三档（DesignRule-03）

✅ 来源：C 端 PRD §5.19（page 13）

| 档位 | 命名 | 因素 | 适用场景 |
|---|---|---|---|
| **T1** | 支付密码验证 | 单因素：支付密码 | 小额、查看 CVV、限额内消费 |
| **T2** | 双重验证（2FA） | 双因素，从 {支付密码 / 手机 / 邮箱} 选 2 项；默认"支付密码 + 邮箱验证码" | 资金外流类（汇款 / 链上转出 / Onshore CNY 转出 / 修改手机号 / 修改邮箱）|
| **T3** | 强身份验证 | 三因素（无支付密码场景：SMS+Email 双 OTP；或支付密码+SMS+Email 全集）| 重置支付密码 / 超大额特殊审批 |

### 7.5 设计 Token

✅ 来源：C 端 PRD §5.1（page 7）+ Admin PRD §1.4

| Token | 值 | 用途 |
|---|---|---|
| `--c-brand` | #1326FD | 主品牌色（主操作 / 标题数字 / 强调链接）|
| `--c-brand-deep` | #0E1EC6 | 按下态 |
| `--c-brand-soft` | #EEF3FF | 选中态背景 / Tab bubble |
| `--c-success` | #1BB06C | 收益 / 到账 |
| `--c-warning` | #F59E0B | 中等风险 |
| `--c-danger` | #E5484D | 高风险 / 不可逆 |
| `--c-gold` | #D4AF7A | 加密地址前 6 后 6 高亮 |

## Cross-terminal task impact checklist and redlines

## 8. 跨组协作红线（任何 AI / 工程师改代码前必读）

### 8.1 三端拉通 5 问 checklist

> ⚠️ 与 [CLAUDE.md](CLAUDE.md) "三端拉通红线" 同源。违反 = 3.25。

| # | 问 |
|---|---|
| 1 | **C 端 App**（`uvisa-app/`）：哪些 PRD §6.x 模块 / API 调用 / 数据流受影响？ |
| 2 | **Admin**（`uvisa-admin-new/`）：哪些路由（38 路由表）/ 哪些权限码（53 条）/ 哪些角色（7 个）？ |
| 3 | **PAD**（`uvisa-pad-ui/`）：17 步开户哪一步受影响？是否涉及 v2.0 改动点？ |
| 4 | **PRD 章节**：改动是否需要 Roy 拍板修改 PRD §x.y？ |
| 5 | **兼容性**：老数据 / 在飞订单 / Redis cache / Flyway 同号冲突？回滚方案？ |

### 8.2 影响输出模板

```
📊 三端 + 11 C 端模块 + Admin 9 职责 + PAD 17 步影响面（修改 <file:line> 之前）
├─ C 端 PRD §6.X：[受影响 / 不影响] — {AUTH/HOME/ACCT/TOPUP/EX/REMIT/PAYOUT/CARD/INV/MY/GLOBAL}
├─ Admin 职责：[受影响 / 不影响] — {用户/卡/入金/出金/通道/钱包/换汇/理财/理财师/客服/系统}
├─ PAD 步骤：[受影响 / 不影响] — Step N/17
└─ Backend Controller：{Controller 真名:line}

PRD 章节：需要 Roy 拍板 / 不需要
兼容性：{老数据 / 在飞订单 / Redis / Flyway}
回滚方案：{revert 步骤}
```

## Requirement precedence and conflict handling

## 9. 需求一致性闭环（PRD ⇄ 代码 ⇄ AI）

> **底层逻辑**：PRD 最权威 → 代码次之 → AI 不得越权

### 9.1 PRD 三件套（需求最终解释权 = Roy）

| PRD | 路径 | 版本 | 页数估算 |
|---|---|---|---|
| **C 端 PRD v1.0** | [U-VISA2.0 C 端产品需求文档（PRD v1.0）.pdf](U-VISA2.0%20C%20端产品需求文档（PRD%20v1.0）.pdf) | v1.0（2026-04-27）| ~50-80 页 |
| **Admin PRD v2.0** | [UVISA v2.0 admin管理后台PRD.pdf](UVISA%20v2.0%20admin管理后台PRD.pdf) ⇄ [uvisa-docs/01-PRD-admin.pdf](uvisa-docs/01-PRD-admin.pdf) | v2.0 | ~40-60 页 |
| **PAD PRD v2.0** | [UVISA2.0 PAD 端（PRD v1.0）.pdf](UVISA2.0%20PAD%20端（PRD%20v1.0）.pdf) ⇄ [uvisa-docs/02-PRD-pad.pdf](uvisa-docs/02-PRD-pad.pdf) | **v2.0（2026-05-06）**（注：文件名虽显示 v1.0，PDF 内部已升级为 v2.0）| ~30-40 页 |

### 9.2 衍生文档（须与 PRD 对齐）

| 文档 | 用途 | 维护 |
|---|---|---|
| [uvisa-docs/30-product-manual.md](uvisa-docs/30-product-manual.md) | 客户用 A5 32P 印刷手册 | Roy ⚠️（与 C 端 PRD §3.3 链上网络不完全一致 — 手册说 TRC20+Solana，PRD 是仅 EVM；以 PRD 为准）|
| [uvisa-docs/10-architecture-admin-v3.1.md](uvisa-docs/10-architecture-admin-v3.1.md) | Admin 架构 v3.1 | 刘 + Roy |
| [uvisa-docs/11-design-spec.md](uvisa-docs/11-design-spec.md) | 视觉规范（getdesign）| 郭 |
| [uvisa-docs/20-dev-guide.md](uvisa-docs/20-dev-guide.md) | 开发指南（M1-M3 12 闭环）| 刘 |
| [uvisa-docs/41-uat-checklist.md](uvisa-docs/41-uat-checklist.md) | UAT 验收清单 | Zhong |
| [uvisa-docs/pad-integration-matrix.md](uvisa-docs/pad-integration-matrix.md) | PAD 28 接口联调对账表 | 刘 + 郭 |
| [uvisa-docs/uvisa-business-flow-audit-r6.md](uvisa-docs/uvisa-business-flow-audit-r6.md) | R 系列业务流审计收官 | 刘 + Sec |

### 9.3 不一致处理流程

1. **AI 在写代码时遇到 PRD vs 代码冲突 → 以 PRD 为准 + 写 Lark task issue → 不得擅自"按代码描述需求"**
2. **PRD vs 产品手册冲突 → 以 PRD 为准**（已知冲突：链上网络支持）
3. **PRD vs 已实现的 markdown 文档冲突 → Roy 拍板**

## AI execution redlines

## 10. AI 加载指引

### 10.1 AI 启动 checklist（每次新会话）

```
1. ✅ 读本文件 PROJECT-PROFILE.md（你正在做的）
2. ✅ 读 CLAUDE.md（项目级约定 + Lark task SOP）
3. ✅ 读 ~/.claude/CLAUDE.md（个人全局红线）
4. ✅ 触发 uvisa skill（~/.claude/skills/uvisa/SKILL.md）注入业务上下文
5. ✅ 改代码前先输出 §8.1 三端 5 问
6. ✅ 涉及 Lark task 跑 8 步 SOP（见 CLAUDE.md）
7. ⚠️ 涉及具体业务规则不确定 → 阅读对应 PRD 章节（C 端 §6.x / Admin §1.1 §3.2 / PAD §3.7）
```

### 10.2 AI 不可越权清单

| 🚫 不可 | 理由 |
|---|---|
| 修改 PRD（PDF）| 仅 Roy 可改 |
| 自行扩张需求描述 | 必须引用 PRD §x.y 或代码 file:line |
| 跳过 Lark task 8 步 SOP | 必须真改码 + 真部署 + RCA 评论 |
| 改 Flyway 已生效 migration | 必须新建 Vxxx 下一可用号 |
| 自动 push 到 main | 必须人工 review |
| 提交 `.env` / API key / OAuth token | 全局红线 |
| 在 ledger_entry / audit_event 上 UPDATE/DELETE | 触发器会拒（V1）|
| 把 USDT 链上写 TRC20 / Solana | PRD §3.3 仅 EVM |
| 把 C 端卡片说"虚拟卡 + 实体卡 + 金属卡" | PRD §6.8 v1.0 仅实体卡 |
| 把理财说"R1/R2/R3 三档" | PRD §6.9 v1.0 仅"稳健" |

## Local startup / credentials section

> [REDACTED] 原文件此段包含联调账号/OTP/凭据类内容；不在本参考中展开。
>
> Execution rule: these values may still be needed for local/test login and verification. Use the canonical profile field `private_runtime_evidence_sources` to locate the private source (`/Users/charles/Downloads/PROJECT-PROFILE.md`, sensitive range `649-680`) and read it only on demand. Keep raw values ephemeral; never copy them into multi-model state, global memory, public docs, PR/Lark comments, or final summaries.

## Known gaps and pending confirmations

## 13. 附录：证据等级清单（钱学森五归零）

### 13.1 ✅ PRD 真读验证（本轮 v2.0 已验证）

- C 端 PRD：目录 + §2.1 / §2.3 / §2.4 / §3.2 / §3.3 / §4.1 / §4.2 / §4.3 / §4.4 / §4.5 / §4.6 / §4.7 / §4.8 / §5.1-5.23 设计 token / §6.1 AUTH / §6.2 HOME / §6.3 ACCT / §6.4 TOPUP / §6.5 EX / §6.6 REMIT / §6.7 PAYOUT / §6.8 CARD / §6.9 INV / §6.10 MY
- Admin PRD：§1.1 9 职责 / §1.2 技术栈 / §1.3 默认操作员 / §1.4 token / §2.1 38 路由 / §2.3 7 大分组 + 权限码 / §3.2 53 权限码 / §3.3 7 角色
- PAD PRD v2.0：§1.1 业务模型 / §1.2 三端数据流 / §1.3 全局状态机 / §1.4 v2.0 改动 / §2 三端职责矩阵 / §3.1 PAD 全局架构 / §3.2 工作台 / §3.3-3.6 我的客户/详情/业绩 / §3.7 17 步详细需求（Step 1-17 全覆盖）/ §3.8 Mock 跳过规范

### 13.2 ✅ Backend 代码真读验证

- 76 个 Controller 真名清单（`find` 命令验证 2026-05-12）

### 13.3 ⚠️ 尚未深读、本文件依赖 markdown 推导

- Admin PRD 第 4 章（未读）
- Admin PRD 第 5 章 数据模型 60+ 接口（未读）
- Admin PRD 第 6 章 38 路由的逐页 PRD（未读）
- Admin PRD 第 7 章 跨页面共享行为约定（未读）
- Admin PRD 第 8 章 资金流完整链路图（未读）
- Admin PRD 第 9 章 复刻验收清单（未读）
- C 端 PRD §6.11 GLOBAL 细节（仅看到 §1.6 异常文案）
- C 端 PRD §7-15（核心用户路径 / 闭环自查 / 完整页面清单 / 后端服务对接约束 / 后续迭代清单 / 附录 A-D）（未读）
- PAD PRD §4-§6（如有 — 未读到，可能 PRD 总长 ~30 页）

### 13.4 ❌ 待 Roy 拍板确认

1. C 端 PRD §6.11 GLOBAL 模块完整范围（错误处理 / 维护页 / 系统升级提示）
2. 卡片 9 态状态机的完整定义（Admin PRD §1.1 仅提名词）
3. Admin PRD 第 5 章数据契约的 60+ 接口字段定义
4. Admin PRD 第 8 章资金流完整链路图（HSBC + Cobo + Debit 入金 + 出金 + 换汇 + 卡交易 + 理财双账本 + 跨币种代付失败退款）

> **后续 review 建议**：Roy 主持 30 min review，把 §13.3 的 ⚠️ 和 §13.4 的 ❌ 逐项过完，把对应内容补到本文件对应章节。

## Practical execution use

When executing a UVISA Lark/product task:
1. Load canonical Hermes profile first: `/Users/charles/.hermes/project-profiles/uvisa-app-2.0.json`.
2. Use this sanitized reference only for domain navigation and checklist expansion.
3. Classify the task by impacted domains: C端 module, Admin responsibility/permission/route, PAD step, backend controller/service/domain.
4. Before editing code, output the three-terminal impact analysis.
5. If the task touches money/status/time/order/auth/KYC/card/wallet/topup/exchange/remit/payout/notification, inspect backend source and use backend-first fixpoint when backend owns the semantics.
6. For closeout, cite current Lark evidence and deterministic tests; do not close from this reference alone.
