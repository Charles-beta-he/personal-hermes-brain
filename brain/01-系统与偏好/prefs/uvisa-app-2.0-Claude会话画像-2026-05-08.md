---
title: uvisa-app-2.0 Claude 会话画像
created: 2026-05-08
status: evidence_grounded_profile
source_project: /Users/charles/Desktop/folder/work/uvisa-app-2.0
source_claude_logs: /Users/charles/.claude/projects/-Users-charles-Desktop-folder-work-uvisa-app-2-0
multi_model_tick: /Users/charles/.hermes/tick-20260508-072835
truth_status: grounded
evidence_coverage: 1.0
verified_claim_count: 5/5
type: profile
---

# uvisa-app-2.0 Claude 会话画像

## 1. 结论摘要

基于 uvisa-app-2.0 的 Claude Code 会话记录、项目文档、git 记录与多模型交叉分析，可以较高置信度得出：

- 用户在该项目上的工作方式不是一次性指令，而是长时间自运行 loop / pua-loop：持续发现缺口、修复、验证、再深挖。
- 用户的质量标准核心是“交互闭环”：不能有 dead UI、缺省逻辑、未闭环状态页、死路由、装饰按钮、动态弹窗漏测。
- 用户偏好 P10/A+ 标准：每轮改动后要自检、UI 实测、边界扩充，直到无 next pass / 无 dead UI / A+。
- 用户强约束：不能通过删除功能解决问题；不能改坏原有功能；要保持字段展示与内部 H5 UI 功能不漂移。
- 项目目标：将 `uvisa-app-2.0` 填充到参考项目 `uvisa-app` 的功能完成度，同时保持原字段展示与 H5 交互体验；后续重点是后端地址/真实接口联调、mock/server 对齐、全流程 UI 验收。

## 2. 证据范围

- Claude Code 会话目录：`/Users/charles/.claude/projects/-Users-charles-Desktop-folder-work-uvisa-app-2-0`
- 会话数量：5 个 jsonl 会话
- 直接用户 prompt：217 条
- 项目路径：`/Users/charles/Desktop/folder/work/uvisa-app-2.0`
- 项目结构：React 19 + Vite + TypeScript + Zustand + Tailwind
- 路由数量：78 routes
- 业务 screen 域：auth、card、exchange、global、home、me、payment、payout、remit、topup、wealth
- 文档证据：`docs/UI_TEST_CASES.md`、`docs/decisions/ADR-001..008`
- Git 证据：`feat/uvisa-2.0` 近期提交集中在 test/docs boundary log、UI primitive contracts、401 refresh、analytics flush、money-moving services、pnpm switch。

## 3. 多模型结论

多模型 tick：`/Users/charles/.hermes/tick-20260508-072835`

- 4/4 模型完成：gpt-5.5、mimo-v2.5-pro、claude-opus-4-7、deepseek-v4-pro
- truth_status: grounded
- evidence_coverage: 1.0
- verified_claim_count: 5/5
- consensus_verdict: weak_consensus
- confidence: 0.6778

说明：weak_consensus 不是事实失败。四个模型对用户习惯、工作流和项目目标判断一致；分歧主要在“下一步应该补哪些 verifier gate / patch”的命名与优先级。

## 4. 工作习惯画像

### 4.1 长时间自运行 loop

置信度：高

证据：

- 用户多次使用 “loop”、“pua-loop”、“继续深挖”、“全盘推进”、“直至无 next pass”。
- 会话中存在大量延续摘要，说明项目连续运行到上下文窗口极限后继续恢复。
- 主题计数中 exhaustive_loop = 247。

画像：

用户倾向把 Agent 当作可长时间自主推进的执行系统，而不是问答工具。用户通常不希望 Agent 停在“建议下一步”，而是要继续找缺口、继续修复、继续验证，直到没有新发现。

### 4.2 交互闭环优先

置信度：高

证据：

- 原话：“避免出现交互流程卡住、页面布局分布不合理，但是截图正常的问题”。
- 原话：“多agent team分析当前项目是否存在，逻辑或状态页面缺失，信息操作展示未闭环情况”。
- 原话：“pua-loop 寻找 dead ui，p10 深挖实现功能，直至无 dead UI”。
- 主题计数 closure_gap = 151。

画像：

用户不是只看静态截图或代码编译，而是关注真实用户路径是否能走完：按钮能不能点、状态能不能到达、失败后能不能恢复、弹窗是否重复、流程是否卡死、详情页是否真的能打开。

### 4.3 实现优先，禁止删除式修复

置信度：高

证据：

- 原话：“注意红线为不能修改原有功能！不能以删除的方案来解决 dead UI，仅能以实现的方案实现！”
- 多次要求“删除代码需要严格检查业务流程是否缺失，有可能是业务有其他端来闭环”。

画像：

用户对“为了让测试通过而删掉功能/入口/按钮”的做法高度敏感。对 dead UI 的期望不是隐藏，而是补齐真实业务闭环；除非证据证明该入口确实不应存在。

### 4.4 P10/A+ 验收标准

置信度：高

证据：

- 原话：“p10检查功能是否完整填充……直至 p10 整体功能填充前端项目功能上线评分为 A+”。
- 原话：“UI pro max 为 A+ 直至新需求完全落地且 UI 自测通过”。
- 原话：“补充 dark 模式下的 UI 测试，要求评分为 A+”。

画像：

用户用 P10 表示高层架构/上线级审查，用 A+ 表示体验、功能、验证都过线。不是“能跑就行”，而是接近上线可交付。

### 4.5 证据优先与真测试

置信度：高

证据：

- 原话：“真测试，当前系统与浏览器主题都为黑色，但是并未同步变化”。
- 原话：“手动验收内容你来验收”。
- 原话：“使用 browser-harness 完成缺失补充”。
- `docs/UI_TEST_CASES.md` 记录 iPhone 13 390×844 + Chrome Playwright MCP 执行环境。

画像：

用户希望 Agent 替代人工做真实交互验收，而不是只生成测试方案。用户会用实际浏览器/系统状态纠偏，例如 dark mode 的真实触发。

## 5. 工作流画像

### 5.1 标准 loop 工作流

1. P10 定义目标与红线
2. 读取参考项目/原型/现有功能，建立 parity anchor
3. 多 agent / 多模型拆分领域：auth、card、wealth、topup、exchange、remit、payout、me/security 等
4. 每个 agent 深挖 dead UI / 缺省逻辑 / 未闭环状态
5. 实现功能，而不是删除入口
6. 运行 lint / tsc / unit / e2e / browser-harness / Playwright
7. 将测试用例和 issue 写入 `docs/UI_TEST_CASES.md`
8. 每轮 git commit / push 或本地 checkpoint
9. 下一轮继续深挖边界，直到无 next pass / A+

### 5.2 项目内已固化的工程规则

`.claude/skills/read-repo/SKILL.md`：

- 会话开始先 L0/L1 progressive loading
- 读取 README、package.json、UI_TEST_CASES、git log、src/screens/stores/services
- 避免全仓乱读，减少上下文浪费

`.claude/skills/modify-code/SKILL.md`：

- 修改前 parse intent
- 读取目标和 1-hop deps
- shared code 必须 caller scan
- 关键路径无测试要先写回归测试
- 修改后 lint、tsc、test、e2e verify gate
- bug fix 写入 UI_TEST_CASES，架构选择写 ADR

这说明项目中已经把用户偏好的“防漂移、可验证、少破坏”固化成局部技能。

## 6. 项目目标画像

### 6.1 主目标

置信度：高

`uvisa-app-2.0` 的目标是：

- 参考 `/Users/charles/Desktop/folder/work/uvisa-app`
- 在不改变字段展示与内部 H5 界面功能的前提下，填充当前项目
- 最终达到 P10/A+ 上线级前端完成度
- 后续只需要填充/切换后端地址即可

### 6.2 产品形态

置信度：高

这是一个移动 H5 金融/银行卡/加密资产应用，覆盖：

- 鉴权：登录、voice code、PIN、2FA、refresh token
- 首页资产：钱包、交易、通知
- 卡：U-Card、CVV、冻结/解冻、充值/提现、限额、PIN
- 充值：SWIFT、USDT、CNY
- 提现/转出：USDT、CNY
- 换汇：quote、confirm、order/timeline
- 汇款：收款人、SWIFT/wallet/crypto、pay、finish
- 理财：产品、持仓、购买、赎回、今日收益/累计收益
- 我的/安全中心：设备、换绑、支付密码、登录密码、客服、语言、主题、about/legal
- 全局能力：i18n、dark mode、PWA、Sentry/web-vitals、mock server、真实后端联调、错误/网络中断处理

### 6.3 验收目标

置信度：高

验收不是只看 build pass，而是：

- 全模块 UI 测试用例覆盖
- 动态场景覆盖：重复弹窗、toast、StrictMode 重入、返回中断、网络中断、Service Worker 更新、清缓存/Unregister SW
- 多端/移动端适配：不同屏幕宽度、iPhone 13 视口等
- i18n 切换后布局不炸
- dark mode 真跟随系统
- mock 和 service 路由一致，无 404
- 真实后端可联调
- 功能不能以删除方式绕过

## 7. 多模型给出的后续风险点

置信度：中高

多模型一致认为事实画像已经成立，但项目长期 loop 还需要强化 verifier：

1. Parity drift gate
   - 防止 `uvisa-app-2.0` 相对参考 `uvisa-app` 功能/字段/流程漂移。

2. Dynamic closure verifier
   - 专门覆盖动态弹窗、toast、自动跳转、StrictMode 重入、网络中断、返回中断。

3. No-delete drift guard
   - 对删除入口、删除按钮、删除路由、删除字段加硬闸门，要求证明不是业务缺口。

4. UI_TEST_CASES coverage tracker
   - 把 TODO / PASS / BLOCK / D-section issue 做成可量化覆盖指标。

5. Multi-model drift check
   - 对架构填充和原型一致性，用硬规则 + LLM 互检双轨防盲点。

## 8. 不确定性边界

- 该画像高度适用于 `uvisa-app-2.0` 项目，不应无条件推广到所有生活/非工程任务。
- 会话记录来自 Claude Code，可能偏向记录“执行中出现的问题”，不能完全代表用户所有偏好。
- 多模型结论证明 claims 被证据支持，但不能证明项目已经完全无缺陷。
- `docs/UI_TEST_CASES.md` 中仍有 TODO 与 D-section 历史 issue，说明项目目标是持续逼近 A+，不是宣称已绝对完成。

## 9. 可写入长期画像的稳定事实

- 用户在前端项目中偏好长时间自运行 loop / pua-loop，要求 Agent 自主找缺口、修复、验证并继续推进。
- 用户质量标准偏向 P10/A+：功能完整、交互闭环、UI 实测、边界覆盖、文档化验收。
- 用户明确反对通过删除功能/入口/展示来修复 dead UI；优先补齐真实业务闭环。
- uvisa-app-2.0 的核心目标是对齐参考 uvisa-app 的功能完成度，并保持字段展示与 H5 UI 行为不漂移。
- uvisa-app-2.0 的验收重点包括 browser-harness/Playwright 真交互、移动端适配、i18n、dark、mock/真实后端、PWA/可观测性。
