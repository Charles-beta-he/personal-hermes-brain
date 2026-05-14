---
type: project-report
project: agent-skill-learning
topic: webapp-testing-playwright-evidence-chain
created: 2026-05-13T15:58:00+08:00
status: deterministic-slice-complete
---

# Webapp Testing / Playwright 自动化与截图证据流水线评估

## 结论

- 决策：BORROW pattern，不导入/不安装/不宣称采用外部 `webapp-testing` skill。
- 采用对象：将“Playwright 自动化 + 截图 + 日志”能力映射为现有 `browser-harness-integration` 的 deterministic evidence chain，并与 `visual-regression` 的截图留存规则兼容。
- 本轮证据：已用本机已有的 `/Users/charles/Desktop/folder/work/uvisa-app-2.0` 项目内 `@playwright/test@1.59.1` 跑通本地 fixture；没有执行 npm/pnpm install。

## 1. 来源与许可确认

已确认的事实：

- 候选项来自截图 OCR 任务状态，不是一个已拉取的源码包或仓库。
- 截图来源：`/Users/charles/.hermes/images/clip_20260510_170708_1.png`，记录在 `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json`。
- OCR 对第 6 个候选项的描述：`Webapp Testing`，`Playwright 自动化，写脚本跑测试截屏一条龙`。
- 本地搜索未发现可验证的 `webapp-testing` skill 源码、README、LICENSE 或仓库路径。

许可判断：

- License：UNKNOWN / NOT VERIFIED。
- 处理原则：不能导入、复制或宣称采用该外部 skill；只能借鉴截图描述中抽象出来的工作流模式。
- 安全决策：BORROW pattern only，即把“脚本 + 截图 + 日志 + 可复跑命令”纳入本地 browser-harness 证据规范。

## 2. 映射到现有 browser-harness

现有能力对应关系：

| 截图候选能力 | Hermes 现有落点 | 本轮标准化要求 |
|---|---|---|
| Playwright 自动化 | `browser-harness-integration` 的自动化 guard / real browser walkthrough 后置 guard | 命令必须可复跑，记录 URL、viewport、环境、依赖来源 |
| 写脚本跑测试 | 项目内 Playwright 或本地已有依赖；禁止临时安装 | 脚本必须输出机器可读 summary 与人类可读 run-log |
| 截屏一条龙 | `visual-regression` 截图目录和稳定 evidence path 规则 | 截图路径稳定；避免只存在于会被覆盖的 test-results |
| console/network/storage 证据 | `browser-harness-integration` UI evidence closeout | 至少采集 console/pageerror/requestfailed；storage 只记录必要 keys/断言 |

纳入标准流程的位置：

1. 先确认来源/license，外部未知时只 borrow pattern。
2. 真实项目 UI 任务仍以 browser-harness/real-browser walkthrough 为主证据。
3. Playwright 脚本作为 deterministic guard：访问 URL、交互、断言、截屏、日志。
4. 输出 stable evidence bundle：`scriptPath`、`commandLine`、`url`、`viewport`、`screenshot`、`browserEvents`、`summary`。
5. 报告必须明确：当前截图/脚本 guard 证明页面渲染与指定交互，不等价于完整产品/后端业务闭环。

## 3. 本轮创建的证据链 artifacts

Artifact 根目录：

- `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/`

创建文件：

- 脚本：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/scripts/playwright-evidence-chain.mjs`
- 本地示例页：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/fixtures/local-example.html`
- dry-run plan：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/evidence/dry-run-plan/dry-run-plan.json`
- dry-run log：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/evidence/dry-run-plan/run-log.md`
- 实跑 summary：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/evidence/local-example-pass/evidence-summary.json`
- 浏览器事件：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/evidence/local-example-pass/browser-events.json`
- 实跑日志：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/evidence/local-example-pass/run-log.md`
- 截图：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/evidence/local-example-pass/local-example-1280x720.png`

截图校验：

- size：45273 bytes
- sha256：`87bcb1d05a7cea8af21c9e02b34cad4196ccb2e1d5bbcbfe26ce76cf0db0e8e0`

## 4. Dry-run 方案

命令：

```bash
node /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/scripts/playwright-evidence-chain.mjs \
  --dry-run \
  --project-dir /Users/charles/Desktop/folder/work/uvisa-app-2.0 \
  --url file:///Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/fixtures/local-example.html \
  --out /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/evidence/dry-run-plan
```

Dry-run 输出状态：`DRY_RUN_ONLY`。

计划检查项：

- resolve `@playwright/test` from `--project-dir` without installing packages
- open URL in Chromium 1280x720
- record console/pageerror/requestfailed events
- assert title contains Playwright Evidence Chain
- click `#increment` and assert `#count` becomes `1`
- capture screenshot and write machine-readable summary

## 5. 实跑验证结果

命令：

```bash
node /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/scripts/playwright-evidence-chain.mjs \
  --project-dir /Users/charles/Desktop/folder/work/uvisa-app-2.0 \
  --url file:///Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/fixtures/local-example.html \
  --out /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/webapp-testing-playwright-evaluation-2026-05-13/evidence/local-example-pass
```

结果：PASS。

关键断言：

```json
{
  "responseStatus": 200,
  "titleContainsEvidenceChain": true,
  "countAfterClick": "1",
  "countAfterClickIsOne": true,
  "storageClickCount": "1",
  "storageClickCountIsOne": true,
  "consoleErrorCount": 0,
  "pageErrorCount": 0,
  "requestFailedCount": 0
}
```

浏览器事件：2 条 console info；0 pageerror；0 requestfailed。

已使用的现有依赖：

- Node：`v24.14.0`
- Playwright：`/Users/charles/Desktop/folder/work/uvisa-app-2.0/node_modules/.pnpm/@playwright+test@1.59.1/node_modules/@playwright/test/index.js`

## 6. 验收覆盖

| Acceptance | Status | Evidence |
|---|---|---|
| 确认来源与许可 | PASS | 本报告第 1 节；只找到截图/OCR 来源，license unknown，不导入 |
| 映射到现有 browser-harness | PASS | 本报告第 2 节；已映射到 `browser-harness-integration` + `visual-regression` |
| 设计脚本+截图+日志证据链 | PASS | `scripts/playwright-evidence-chain.mjs` + `local-example-1280x720.png` + `run-log.md` + `browser-events.json` |
| 给出 dry-run 方案 | PASS | `evidence/dry-run-plan/dry-run-plan.json` 和本报告第 4 节 |
| 本地示例页验证 | PASS | `fixtures/local-example.html` 实跑 status PASS |

## 7. 残余风险

- 未验证外部 `webapp-testing` 的真实源码与 license；因此只能 borrow workflow pattern。
- 本轮 fixture 证明的是最小 evidence chain，不证明复杂真实业务流、后端 API 合约、支付/认证等产品语义。
- 脚本依赖一个已存在项目的 `@playwright/test`；若搬到新机器，需要指向另一个已有 Playwright 项目，或在项目本身声明依赖后再运行。
