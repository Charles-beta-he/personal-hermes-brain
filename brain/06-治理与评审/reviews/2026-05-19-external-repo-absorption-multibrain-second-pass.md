# 2026-05-19 外部仓库吸收 Second-pass 多脑榨干报告

## 结论
- dev 脑原先承接了过多“外源吸收”职责；二刷后按能力域拆成 design/research/media/mlops/workflow 五个专业脑，hermes-core 承接 agent-control 类。
- dev 保留通用工程交付、本地静态 App、未知外源吸收入口；专业领域由对应脑 owning，必要时回委托 dev 做实现。
- “榨干”的标准：每个外源必须落到 owner brain、profile、stop condition、verification slice；无来源验证或无 capability_delta 的内容不进入能力层。

## 分类盘点（任务文件 116 个）
### design (5)
- - / - / Task - 用户端-点击我的，点击安全中心，在手机号这一行右侧缺少"未绑定"的初始化状态标识，请设计一个“未绑定”的初始化标识
- done / P1 / Task - 用 12Factor Agents 生产化范式审计 Hermes Agent 控制平面与任务池架构缺口
- done / P2 / Task - Skill学习路线：UI UX Pro Max 风格/配色库与 Hermes UI 审美基线评估
- done / P2 / Task - 分析 fireworks-tech-graph 仓库并提炼 Hermes 在自然语言技术图表生成SVGPNG导出与 AI 工作流图模板上的可吸收增量
- pending / P2 / Task - 吸收 awesome-design-md 的 DESIGN.md 代理设计规范机制到 Hermes 设计/项目画像工作流 / github.com/VoltAgent/awesome-design-md

### dev / external-absorption-general (7)
- - / - / 10. 2026-05-18 P3-P5 全盘落地记录
- active / - / 2026-05-07 Resumable Multi-Model Certification Landing Log
- done / P1 / Task - 沉淀系统提示词五大核心规则并治理 Hermes prompt 模块化与 truthfulness 约束
- pending / P1 / 采纳 GenericAgent 三大模式 / github.com/lsdefine/GenericAgent
- pending / P1 / 铁板架构: 32→5 Cron Jobs 整合
- done / P2 / Task - 分析 Meta-Meta-Prompting 文章并提炼 Hermes 可吸收的 skillify eval retrieval 架构增量
- done / P2 / Task - 分析 agentmemory 仓库并提炼 Hermes 在 hybrid retrieval shared memory server 与 hook-driven consolidation 上的可吸收增量 / github.com/rohitg00/agentmemory

### hermes-core / agent-control (73)
- completed / - / 2026-05-06 Cybernetic Multi-model Intervention Log
- - / - / Evolution Lane 认证死循环 — 根因分析与预防方案
- current / - / Iteration Budget PUA-loop 落地 Proof
- completed / - / Local Brain Backlog-zero Loop Log
- - / - / Task - 用户端-底部导航栏第一个资产菜单内，“法币钱包”列表下的“人民币”修改为“CNY”
- - / - / Task - 用户端-底部导航栏第一个资产菜单内，点击“U-Visa 卡可用额度”板块，跳转到“U-VISA”页面，该页面文案和显示内容需要修改，当没有任何U-VISA卡片时候，顶部的“待激活”应显示“待开卡”，当卡片被注销之后，同样也是该页面显示“待开
- - / - / Task - 用户端-底部导航栏第一个资产菜单内，点击转入，选择境内转账，输入金额，点击下一步，收款信息页面点击下一步去app转账后到达挂单页面，底部显示挂单已创建的时间未按照当前挂单创建时间显示
- - / - / Task - 用户端-点击我的，点击安全中心，在邮箱这一行右侧缺少"未绑定"的初始化状态标识，请设计一个“未绑定”的初始化标识
- - / - / Task - 用户端-点击我的，点击客服后与原型图中的不一致，请查看评论区中原型图的文案进行1:1复刻；其中红框中在没有联系客服之前的状态文案显示的是“联系顾问·开始对话”，已经联系过客服之后的状态文案显示的是“继续对话”
- - / - / Task - 用户端-点击我的，点击退出登录时缺少确认退出登录弹框的功能，请设计一个确认退出登录弹框
- - / - / Task - 用户端-登录时输入账号和输入邮箱验证码点击登录后，跳转至请输入支付密码页面，输入错误支付密码后提示语为英文，未跟随当前 APP 的系统语言设置进行适配，输入错误支付密码后提示语应根据当前 APP 语言自动显示为对应语言。
- done / P0 / 2026-05-08 Symphony-inspired Task Orchestrator Landing Log
- done / P0 / Local-brain Taskflow Closure Proof
- done / P1 / Task - Mission方法论P1：Mission DAG 分解、路由与 Dashboard 进度视图
- done / P1 / Task - Mission方法论P1：local-first Mission artifacts 与知识图谱沉淀
- done / P1 / Task - OpenAI openai-cli 沙箱评估与 Hermes/API 自动化集成决策
- done / P1 / Task - Skill学习路线：Code Review 多 Agent 并行审查与置信度过滤评估
- done / P1 / Task - Skill学习路线：Ralph Loop Hook 防提前收工与 Hermes PUA/Loop 边界评估
- done / P1 / Task - 为 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略 细化 fallback threshold 收敛前置任务
- done / P1 / Task - 为 Hermes 设计 grace call 输出结构化 continuation packet 机制
- done / P1 / Task - 为 taskpool 设计前置固定多模型优先级分析与入池分层机制
- done / P1 / Task - 为每日日报建立自动生成任务的受治理入池机制
- done / P1 / Task - 为每日日报补充 GitHub 官方 Trending 排名数据源并纳入证据化汇总
- done / P1 / Task - 从 hermes-hudui 提炼 Hermes-native Replay 证据闭环与 HUD 安全门 / github.com/joeynyc/hermes-hudui
- done / P1 / Task - 分析 jcode 仓库并优化 Hermes 自身多会话代理编排与边界闭环能力 / github.com/1jehuang/jcode
- done / P1 / Task - 多模型分析 Agent Development Kit 图片并将 Hermes 优化方案落地
- done / P1 / Task - 多模型分析 Panniantong/Agent-Reach 并给出 Hermes 优化方案 / github.com/Panniantong/Agent-Reach
- done / P1 / Task - 对预算耗尽后的 grace-call continuation / new-session resume 机制做多模型分析并完善方案
- done / P1 / Task - 将 Dreaming 长期经验沉淀与 Outcomes 裁判分离机制映射为 Hermes 技能复盘/独立质检闭环
- done / P1 / Task - 建设 Hermes 长期可维护的 execution-quality 评估反馈基座以承接 EvoAgentX 演化闭环建议
- done / P1 / Task - 建设 Hermes 长期可维护的自动 skill 演化与 prompt 治理闭环以落地 EvoAgentX Agent Evolver 建议
- done / P1 / Task - 本地大脑迁移残留闭环清理与 repair-plan/apply 验证
- done / P1 / Task - 落地 Iteration Budget PUA-loop 有界执行与 handoff 闭环
- done / P1 / Task - 补齐 brain_task_orchestrator add 流程并在创建时强制写入优先级分层依赖顺序与多模型 triage 结果
- done / P2 / Task - Mission方法论P2：proof-gated auto-claim-and-handoff Mission runner 集成
- done / P2 / Task - Second-pass 分析 openai/symphony 仓库并提炼 Hermes 在工单监听隔离工作区工作证明链与安全落 PR 闭环上的可吸收增量
- done / P2 / Task - Skill学习路线：PPTX 直接生成 pptx 文件与 Hermes productivity 流程评估
- archived / P2 / Task - Task - P2 Mission proof-gated autorun handoff 与权限暂停状态
- done / P2 / Task - 为 2026-05-14-分析-evoagentx-仓库并优化-hermes-自身进化式代理与自动改进机制 细化 fallback threshold 收敛前置任务 / github.com/evoagentx/EvoAgentX
- done / P2 / Task - 为 2026-05-14-分析-evoagentx-仓库并优化-hermes-自身进化式代理与自动改进机制 细化 quota observability 收敛前置任务 / github.com/evoagentx/EvoAgentX
- done / P2 / Task - 为 2026-05-14-分析-evoagentx-仓库并优化-hermes-自身进化式代理与自动改进机制 细化 relay ordering 收敛前置任务 / github.com/evoagentx/EvoAgentX
- done / P2 / Task - 修正 taskpool 默认任务模板对 smallest-slice framing 的系统性偏置并对齐长期可维护主链治理
- done / P2 / Task - 分析 CUA 仓库并优化 Hermes 自身计算机使用与代理执行能力 / github.com/trycua/cua
- done / P2 / Task - 分析 EvoAgentX 仓库并优化 Hermes 自身进化式代理与自动改进机制 / github.com/evoagentx/EvoAgentX
- done / P2 / Task - 分析 Hindsight 仓库并优化 Hermes 自身回溯记忆与知识工作流 / github.com/vectorize-io/hindsight
- ... plus 28 more

### media (4)
- active / - / 任务池-排序
- done / P2 / Task - 分析 DramaDirector 仓库并提炼 Hermes 在 schema-first 媒体编排、stateful CLI 与 drop-in skill 集成上的可吸收增量 / github.com/Dramalf/DramaDirector
- done / P2 / Task - 分析 Voice Pro 仓库并提炼 Hermes 在本地免费语音转写配音翻译人声分离与 YouTube 音视频处理上的可吸收增量
- pending / P3 / Task - 验证 OmniVoiceStudio 本地语音克隆/视频配音项目真实性并评估是否纳入 Hermes 媒体工作流 / github.com/depalash/OmniVoiceStudio

### mlops (10)
- active / - / 2026-05-07 - Agent COS Landing Log
- accepted / - / Quota Observability Policy Brief
- done / P1 / Task - Advisory - tokenusage clean-room provider-quota observability upgrade / github.com/hanbu97/tokenusage
- done / P1 / Task - 为空闲时间自动推进增加 idle-runner 检测与风险路由
- done / P2 / Task - 分析 TencentDB-Agent-Memory 仓库并提炼 Hermes 在 symbolic short-term memory、4-tier progressive layering 与 Hermes 插件记忆运行时上的可吸收增量 / github.com/Tencent/TencentDB-Agent-Memory
- done / P2 / Task - 分析 keycompute 仓库并优化 Hermes 自身模型路由/算力治理与观测能力 / github.com/keycompute/keycompute
- done / P2 / Task - 分析 openhuman 仓库并提炼 Hermes 在 memory tree autofetch token compression 上的可吸收增量
- done / P2 / Task - 分析 rtk-hermes 仓库并提炼 Hermes 在 pre-tool command rewrite、RTK 过滤输出与插件化 token 降耗上的可吸收增量 / github.com/ogallotti/rtk-hermes
- done / P2 / Task - 精读 Perplexity《Designing, Refining, and Maintaining Agent Skills at Perplexity》②并把 progressive loading 与路由回归门落成 Hermes 技能治理增量
- done / P3 / Task - 分析 MiniMind 仓库并提炼 Hermes 在轻量 LLM 教学链路、可解释训练实验与入门型模型实践上的参考价值 / github.com/jingyaogong/minimind

### research (4)
- done / P2 / Task - 分析 CocoIndex 仓库并提炼 Hermes 在增量索引、多源实时同步与 fresh-context 数据面上的可吸收增量 / github.com/cocoindex-io/cocoindex
- done / P2 / Task - 分析 Context7 平台并提炼 Hermes 在最新代码文档检索、版本化上下文注入与编码提示去幻觉上的可吸收增量 / github.com/upstash/context7
- done / P2 / Task - 分析 web-access 仓库并提炼 Hermes 在跨平台信息检索、浏览器自动化与联网策略编排上的可吸收增量 / github.com/eze-is/web-access
- done / P3 / Task - 分析 public-apis 仓库并提炼 Hermes 在公共数据源发现、免密 API 选路与外部实时信息接入上的可吸收增量 / github.com/public-apis/public-apis

### workflow (13)
- complete / - / EvoAgentX 仓库分析 — Hermes 优化建议
- done / P1 / Task - SkillClaw 沙箱评估与 Hermes 技能进化集成决策 / github.com/AMAP-ML/SkillClaw
- done / P1 / Task - Skill学习路线：MCP Builder 四阶段 MCP Server 引导与 Hermes MCP skill 补强评估
- done / P1 / Task - Skill学习路线：Planning with Files 文件化规划与上下文压缩抗丢失评估
- done / P1 / Task - Skill学习路线：Skill Creator 官方元技能与 eval 测试框架适配评估
- done / P1 / Task - Skill学习路线：Superpowers 可组合开发流程与 TDD/brainstorming 适配评估
- done / P1 / Task - Skill学习路线：Webapp Testing Playwright 自动化与截图证据流水线评估
- done / P1 / Task - 多模型分析 simular-ai/Agent-S 并完善 Hermes 技能树 / github.com/simular-ai/Agent-S
- done / P2 / Task - Skill学习路线：Code Simplifier 重复逻辑合并与安全重构评估
- done / P2 / Task - 分析 Perplexity agent skills 文章并优化 Hermes 自身技能体系与维护机制
- done / P2 / Task - 分析 spec-kit 仓库并优化 Hermes 自身规范驱动开发与工作流 / github.com/github/spec-kit
- done / P2 / Task - 分析 vibe-coding-cn 教程中的产品开发组并提炼 Hermes 在技能创造、技能检索、前端生成、界面优化与自动化测试上的可吸收增量 / github.com/tukuaiai/vibe-coding-cn
- done / P2 / Task - 建设 Hermes 长期可维护的 workflow-generator 与 orchestration-plan 编译框架以吸收 EvoAgentX 启发

## 能力强化/新增脑落地矩阵
| 脑 | 吸收来源 | 强化点 | 反漂移/停止条件 |
|---|---|---|---|
| hermes-core | Rowboat/Symphony/EvoAgentX/Orca/JCode/Paperclip/OpenClaw/Dreaming/Outcomes/12Factor | agent-control-plane absorption、默认关闭/证据链/预算/continuation | 不放松 truth/cert gate；不把 runtime/secrets 入 git |
| dev | 通用 repo/source validation/local app | 保留工程交付和未知外源入口；专业类转路由 | 无 capability_delta/来源验证则停止 |
| design | awesome-design-md/UI-UX Pro Max/baseline-ui/fireworks-tech-graph | DESIGN.md、token/component/brand、截图/无障碍证据 | 泛化审美建议、覆盖既有 token 停止 |
| research | public-apis/Context7/CocoIndex/web-access | source registry、fresh context、版本化引用 | 无 provenance、动态页无 DOM/browser 证据停止 |
| media | Voice Pro/DramaDirector/OmniVoiceStudio | 本地音视频/模型权重/隐私/license 验证 | 404/未验证权重/私密媒体上传停止 |
| mlops | keycompute/MiniMind/rtk-hermes/memory repos | provider quota、模型路由、推理/训练/eval 边界 | 非 canonical model id、quota 不可观测停止 |
| workflow | SkillClaw/Perplexity skills/Superpowers/spec-kit/Planning with Files | skill/template/protocol/eval 闭环 | 泛流程总结、触发面扩大无邻例停止 |

## 已落地文件
- `/Users/charles/.hermes/brains/{design,research,media,mlops,workflow}/brain.yaml`
- `/Users/charles/.hermes/brains/main/brain.yaml` 路由协议升级
- `/Users/charles/.hermes/brains/hermes-core/brain.yaml` agent-control absorption profile
- `/Users/charles/.hermes/brains/registry.yaml` v0.4.0 注册新脑
- `/Users/charles/.hermes/scripts/brainctl.py` 多脑路由扩展
- `/Users/charles/.hermes/scripts/test_brainctl.py` 路由回归测试扩展

## 验证命令
- `python3 ~/.hermes/scripts/brainctl.py --json brains validate`
- `~/.hermes/hermes-agent/.venv/bin/python -m pytest ~/.hermes/scripts/test_brainctl.py -q`
- route smoke: design/media/research/mlops/workflow/hermes-core/dev 七类 query