# Hermes 路由/Quota Fail-Closed 治理记录

更新时间：2026-05-07 23:46:04
代码提交：`2f25a10`
仓库：`/Users/charles/.hermes`

## 背景

本次来自 Antigravity-vs-Hermes 多模型路由建议的落地：强化 Hermes model routing、quota gate、provider availability、routing ledger 与 select-pair 多模型角色选择。

## 已落地原则

- quota/router 所有 gate 必须 fail-closed：provider unavailable、quota gate unavailable、all candidates exhausted、config load failed、CLI model=None/unknown 均不得成功返回。
- quota state 与 snapshot 必须显式校验形状：top-level 非 dict、JSON null、exact-key 非 dict、exact-key dict 缺失或错配 model/provider、非法 status 均视为 malformed 并 skip。
- provider metadata 必须保持 source-of-truth 一致：config.yaml `pricing.models`、pricing table、quota snapshot/gate 使用同一 provider mapping，避免 `unknown::<model>` 绕过 exhausted state。
- select-pair 的 reviewer 必须走 provider/quota/capability gates；同 provider reviewer 只允许在 off-peak + high-confidence 且重新通过 select_model gates 时选择。
- routing decision ledger 只记录 secret-safe 字段，不写 credentials/token/password/API key。

## 验证证据

- Full unittest：`python3 -m unittest scripts.test_model_quota scripts.test_model_router_quota scripts.test_consult_models_integration scripts.test_resumable_multimodel_cert_selfcheck -v` -> `Ran 126 tests ... OK`
- Py compile：核心脚本与测试文件编译通过。
- Staged diff check：通过。
- Staged secrets/danger scan：`secret_or_danger_hits=[]`
- Independent staged reviewer：`passed=true`, `security_concerns=[]`, `logic_errors=[]`
- 本地 commit：`2f25a10`

## 后续注意

- reviewer 建议：减少 `_model_available` 对同一 candidate 的重复调用，避免重复 availability logging；非 blocker，可后续优化。
- 未来修改 quota/router/certification 逻辑时，必须继续用 staged-only independent reviewer，并显式覆盖 malformed artifact fail-closed regression tests。

相关：[[Agent认知操作系统互补矩阵]]
