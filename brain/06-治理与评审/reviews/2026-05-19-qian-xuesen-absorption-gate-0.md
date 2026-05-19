# 钱学森核心著作系统吸收级评审 — Gate 0

> 评审模型：Hermes 多脑架构评审
> 日期：2026-05-19
> 状态：Gate 0 理论基础完整性评审 — PASS（可进入 Gate 1 实现阶段）
> 基于：Engineering Cybernetics (1954) / 论系统工程 (1982) / 系统科学思想文选 (2011) / 创建系统学 (2007, 待补齐)

---

## 一、缺失部分

### 1.1 综合集成研讨厅体系 (HWME) 三级结构工程映射

| HWME 层 | 理论原意 | 已有映射 | 缺失 | capability_delta |
|---------|---------|---------|------|-----------------|
| 专家体系 | 人的经验、直觉、领域判断 | main脑路由/仲裁 + human-in-the-loop | 多脑多模型仲裁回路未工程化 | quorum_voter.py + 分歧仲裁协议 |
| 知识体系 | 历史数据、文献、案例库 | brain/04-知识原子/atoms | atom→taskpool自动入栈机制缺失 | 知识原子碰撞→task生成管道 |
| 机器体系 | 计算机算力、数据处理、模型推理 | dev/mlops/media脑 | quorum vote可审计链路缺失 | vote参数→workflow脑全量记录 |

### 1.2 从定性到定量综合集成法 (Meta-synthesis)

- **已有**：research脑来源验证 + 综合集成方法论.md 定义了定性→定量循环
- **缺失**：闭环链路缺少自动化——research的定性发现不能自动生成定量验证task入dev池
- **capability_delta**：qual_to_quant.py 管道（research置信度+可证伪条件 → dev验证task自动生成）

### 1.3 大成智慧工程 (Meta-synthetic Wisdom Engineering)

- **已有**：brain/04-知识原子/atoms 目录 + atom沉淀机制
- **缺失**：钱老"集大成得智慧"的三阶段只有沉淀，无碰撞和涌现
  - 碰撞：atom间跨域关联度矩阵
  - 涌现：跨域推理自动生成新atom候选
  - 沉淀：人工评审后写入（已有）
- **capability_delta**：collision_engine.py（维护关联度矩阵 + 阈值触发候选atom生成）

### 1.4 开放复杂巨系统四特征操作化

| 特征 | 已有 | 缺失 | capability_delta |
|------|-----|------|-----------------|
| 开放性 | external-repo吸收管道 | 论文/新闻/法规等知识源的持续吸收 | 外部知识流入速率监控 + 多源吸收管道 |
| 复杂性 | atom→task→project→lane 层级 | 层级间"涌现"监控（何时升级） | 层级涌现事件计数 + 升级阈值 |
| 层次性 | 多脑层次结构 | 层次间信息压缩/解压缩协议 | 跨层压缩比监控 |
| 巨量性 | 当前规模尚小 | scale-out预设协议 | atom总数阈值触发聚类/归并 |

### 1.5 工程控制论核心概念未映射

| 概念 | 工程控制论原意 | Hermes已有 | 缺失 | capability_delta |
|------|-------------|-----------|------|-----------------|
| 前馈控制 | 扰动进入前的预补偿 | 无 | task dispatch前的风险预建模 | dispatch_gate.py precheck_model |
| 反馈控制 | 误差修正闭环 | auto-done / self-check | 反馈仅覆盖完成态，不覆盖过程态 | 已有，标记为已吸收 |
| 系统辨识 | 在线估计系统参数 | 无 | 脑运行状态持续辨识 | brain_health向量 [latency, error_rate, drift] |
| 可靠性 | 故障容错 | 无 | 脑offline时的降级/接管 | brain_degradation.py |

---

## 二、核心著作吸收矩阵

| 著作 | 吸收目标脑 | Capability Delta | Evidence |
|------|-----------|-----------------|----------|
| Engineering Cybernetics (1954) | hermes-core | +前馈：dispatch_gate.py precheck_model<br>+辨识：brain_health向量写入state.db<br>+可靠性：brain_degradation.py降级协议 | dispatch_gate单测通过<br>brain_health有24h连续数据<br>故障注入测试通过 |
| 论系统工程 (1982) | main | +RDADIV六态task状态机 | 20+ task平滑迁移<br>状态转换图dashboard可见 |
| 论系统工程 (1982) | workflow | +Meta-synthesis协议沉淀：quorum vote全参记录 | 可查询30天内所有综合集成决策 |
| 论系统工程 (1982) | research | +定性→定量转换：验证结论→置信度+可证伪条件 | research评估后dev池自动出现验证task |
| 系统科学思想文选 (2011) | brain/04-atom | +大成智慧涌现引擎：跨域关联度矩阵+碰撞阈值 | 5+atom创建后引擎自动建议≥2涌现候选 |
| 系统科学思想文选 (2011) | dev | +开放复杂巨系统四特征监控器 | dashboard四维雷达图48h无缺失 |
| 创建系统学 (2007) | brain/04-atom | +系统学分类体系注入知识原子分类框架 | atom type扩展为系统学分类（待补齐） |

---

## 三、多脑职责矩阵（含HWME映射）

| 脑 | 原有职责 | 吸收后新增 | 钱学森理论对应 |
|---|---------|----------|-------------|
| main | 路由/仲裁 | +多模型quorum vote调度<br>+分歧再综合仲裁<br>+六态task状态机维护 | HWME：总体设计部主持 |
| research | 来源验证 | +置信度(0-1)+可证伪条件输出<br>+触发定量验证模型生成→dev<br>+定性假设阶段发起者 | HWME：定性假设阶段 |
| workflow | 协议沉淀 | +quorum vote参数/过程/结果全量记录<br>+成功集成模式沉淀为reusable protocol | HWME：综合集成流程固化 |
| hermes-core | 控制面 | +前馈：dispatch预建模风险<br>+反馈：auto-done/self-check(已有)<br>+辨识：brain-liveness持续监控<br>+可靠性：脑退化检测+降级接管 | 工程控制论：前馈+反馈+辨识 |
| dev | 直接开发+跨脑使能 | +前馈控制环实现<br>+脑liveness探针<br>+quorum vote引擎<br>+知识涌现碰撞引擎<br>+定性→定量转换管道 | 系统工程：实施/集成 |
| design/media/mlops | 保留领域判断 | +综合集成研讨厅"领域专家"角色 | HWME：专家体系 |

---

## 四、DEV工程使能位置

### 4.1 定位

dev脑从"执行者"提升为"工程使能枢纽"——唯一可将其他脑的协议/决策/知识/判断转化为可验证代码实现的脑。

### 4.2 新增使能职责

| 序号 | 使能项 | 服务目标脑 | artifact |
|-----|-------|----------|----------|
| a | 前馈控制环实现 | hermes-core | precheck/dispatch_gate.py |
| b | 脑liveness探针 | hermes-core | brain_health采集器 |
| c | quorum vote引擎 | main | orchestration/quorum_voter.py |
| d | 知识涌现碰撞引擎 | brain/04-atom | emergence/collision_engine.py |
| e | 定性→定量转换管道 | research→dev | pipelines/qual_to_quant.py |

### 4.3 验收交还协议

```
┌──────────┐   spec    ┌──────────┐  impl   ┌──────────┐
│ 源脑     │ ────────→ │ dev脑    │ ──────→ │ 源脑     │
│ (需求方) │           │ (使能方) │         │ (验收方) │
└──────────┘           └──────────┘         └──────────┘
     ↑                      │                    │
     └──── 验收通过/驳回 ────┘────────────────────┘
```

Invariant：dev接收其他脑的spec后，实现、测试、交还，由源脑验收。dev不可自行判定"已完成"。

---

## 五、可落地 Artifact / Backlog

### P0 — 使能基础设施（阻塞所有后续）

```
P0-1  hermes-core前馈控制探针
      目标脑：hermes-core
      路径：hermes-core/precheck/dispatch_gate.py
      内容：task dispatch前预建模，返回风险等级(0-1)+风险因子列表
      验收：单测覆盖3类任务(code/analysis/creative)，预建模耗时<200ms
      挂载项目：agent-systems-engineering-control-plane

P0-2  脑liveness监控向量
      目标脑：hermes-core
      路径：state.db新增brain_health表
      内容：每30s采集[响应延迟, 错误率, 漂移度]，写入state.db
      验收：dashboard可查询，drift>阈值时日志warn级告警

P0-3  多模型quorum vote引擎
      目标脑：main
      路径：hermes-core/orchestration/quorum_voter.py
      内容：可配置投票策略(多数/加权/一致性)，记录vote参数到workflow脑
      验收：单测覆盖3/5/7模型场景，分歧时输出分歧报告
```

### P1 — 核心吸收

```
P1-1  从定性到定量转换管道
      目标脑：research→dev
      路径：hermes-core/pipelines/qual_to_quant.py
      内容：research置信度+可证伪条件 → 自动生成定量验证task入dev池
      验收：research输出来源评估后，dev池自动出现对应验证task

P1-2  Meta-synthesis协议沉淀
      目标脑：workflow
      路径：workflow脑新增protocol/meta_synthesis/
      内容：记录每次quorum vote的参模/权重/一致度/结论
      验收：可查询"过去30天所有综合集成决策及成功率"

P1-3  知识涌现碰撞引擎
      目标脑：brain/04-atom
      路径：brain/04-知识原子/emergence/collision_engine.py
      内容：atom间跨域关联度矩阵，碰撞度>阈值自动生成候选atom
      验收：创建≥5个atom后，自动建议≥2个涌现候选，人工通过≥1个
```

### P2 — 完整化

```
P2-1  开放复杂巨系统四特征监控器
      目标脑：dev
      路径：hermes-core/monitoring/complex_system_monitor.py
      内容：开放性(流入速率)、复杂性(涌现计数)、层次性(压缩比)、巨量性(atom总数)
      验收：dashboard四维雷达图48h无缺失

P2-2  脑降级/接管协议
      目标脑：hermes-core
      路径：hermes-core/failover/brain_degradation.py
      内容：brain-liveness<阈值 → 自动reassign任务到fallback脑
      验收：模拟某脑offline，task在30s内reassign，无数据丢失

P2-3  系统工程六态task状态机
      目标脑：main
      路径：task状态迁移逻辑
      内容：PDCA四态 → RDADIV六态 (Requirements→Design→Analysis→Development→Integration→Verification)
      验收：20+现有task平滑迁移，状态转换图dashboard可见
```

---

## 六、验收门

### Gate 0：理论基础完整性 ✅ PASS（本报告）

- [x] 三本核心著作+《创建系统学》的概念映射矩阵已产出
- [x] HWME三级结构(专家/知识/机器)在脑架构中有1:1对应
- [x] 工程控制论前馈/反馈/辨识三环在hermes-core中有代码级签名规划
- [x] 每个capability delta有可执行、可测试的验收标准
- [ ] 《创建系统学》(2007)细粒度概念注入待补齐（不阻塞P0）

### Gate 1：基础设施可用性（P0完成后）

- [ ] P0-1：dispatch_gate.py单测通过，3类任务预建模耗时<200ms
- [ ] P0-2：state.db brain_health表有连续24h数据，无drop
- [ ] P0-3：quorum_voter.py在3/5/7模型场景下正确投票
- [ ] 集成验证：dispatch前检查brain health，低健康脑不参与quorum

### Gate 2：核心闭环验证（P1完成后）

- [ ] P1-1：端到端——research识别来源→dev池验证task→执行→结果回写research
- [ ] P1-2：3次真实quorum vote，workflow脑记录完整参数，可查询历史
- [ ] P1-3：5+atom创建后碰撞引擎建议≥2涌现候选，人工通过≥1

### Gate 3：系统级验证（P2完成后）

- [ ] P2-1：dashboard四维雷达图48h无缺失
- [ ] P2-2：故障注入：某脑offline→30s内task reassign，无数据丢失
- [ ] P2-3：20+ task从PDCA→RDADIV迁移，无状态丢失/死锁

### Gate 4：可证伪审查（最终）

- [ ] 每个capability delta有falsifiable condition（在什么条件下判定吸收失败）
- [ ] 系统辨识在线监控：人工注入漂移后30s内告警
- [ ] HWME"人机结合"部分：明确的人类决策介入点（非全自动）

---

## 七、与现有资产的兼容性确认

| 现有资产 | 吸收兼容性 | 变更影响 |
|---------|----------|---------|
| 综合集成方法论.md | ✅ 本报告扩展该atom的工程层 | 无需修改，补充evidence字段 |
| 系统工程四环Agent映射.md | ✅ 四环→六态是兼容扩展 | 新增六态atom，四环atom保留 |
| 社会系统工程三层.md | ✅ 三层架构不变 | 补充宏观反馈自动化协议的capability_delta |
| Agent系统工程控制面 Project | ✅ P0-1直接挂入此项目 | 项目workpad新增前馈探针task |

---

## 八、建议执行顺序

```
Gate 0 (本报告) → P0-1/P0-2/P0-3 并行 → Gate 1
                                       ↓
                                  P1-1/P1-2/P1-3 并行 → Gate 2
                                                         ↓
                                                    P2-1/P2-2/P2-3 并行 → Gate 3 → Gate 4
```
