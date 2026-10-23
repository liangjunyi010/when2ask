# When2Ask Phase 2 Engineering Pilot

代码与脱敏证据已 push 到 Private 仓库的 `feat/benchmark-apis`，
[PR #1](https://github.com/liangjunyi010/when2ask/pull/1) 指向 `main`，保持 OPEN，未合并。
已核对仓库 `isPrivate=true` 与远端 commit。

本报告只陈述真实 API 与真实 PyBullet 执行结果。离线 adapter 测试使用显式 test doubles，未计入下列表格。样本量很小，不作统计显著性或泛化结论。

## 实验范围与版本

- 当前数据：5 个 handcrafted validation cases、20 个 pilot samples，覆盖 0/1/2/3 个未知偏好。全部 25/25 通过当前场景版本的真实物理 oracle。
- 最终 cohort v2：`validation_002`（2 未知）、`pilot_000`（0 未知）、`pilot_007`（3 未知），每个样本三种方法，共 9 episodes。两个 pilot 的隐藏真值包含不同方块和盖子颜色。
- 前置诊断 cohort v1：同一 validation 样本的三种方法，共 3 episodes。三者都完成物理技能但猜错偏好，均为 0/1 success、burden 0。原始结果完整保留，没有与 v2 混合。
- v1 中模型把未指定的对象当作可任意选择。v2 向所有 Gate/Planner 统一加入公开任务定义：每类对象始终有一个固定用户偏好，未披露是未知，物理放置成功不代表用户确认。没有提供任何正确选择，也没有修改阈值。
- 在已记录的公开状态上额外做了 2 次 gate-only 诊断；DeepSeek 返回 ASK，Jev 返回 ASK / p=0.71。这些调用只属于诊断成本，不是新的完整 episode。
- 最终 cohort 计划见 `experiment_plan_v2.json`。为遵守总上限，v2 的 C 实验只选两个 pilot；1 未知条件本轮仅做数据、oracle 和离线测试，没有在线配对结果。

## 最终真实比较（v2，按每种方法的三个 episodes 求和）

| Method | Task Success | Burden 总数 | DeepSeek tokens | Jev tokens | API latency 秒 |
|---|---:|---:|---:|---:|---:|
| llm_noask | 1/3 | 0 | 16,842 | — | 10.409 |
| llm_gate | 3/3 | 5 | 38,359 | — | 22.129 |
| jev_gate | 3/3 | 5 | 20,267 | 27,455 | 17.641 |

Tokens 为各后端实际 input + output 的和，不能互相等同为美元成本。逐次 input/output、wall time、终止原因在 `episodes.csv`。

| Method | DeepSeek input | DeepSeek output | Jev input | Jev output |
|---|---:|---:|---:|---:|
| llm_noask | 16,586 | 256 | — | — |
| llm_gate | 37,906 | 453 | — | — |
| jev_gate | 19,908 | 359 | 27,119 | 336 |

## 逐样本结果

| Sample | Method | Success | Burden | Termination |
|---|---|---|---:|---|
| pilot_000 | jev_gate | True | 0 | done |
| pilot_000 | llm_gate | True | 0 | done |
| pilot_000 | llm_noask | True | 0 | done |
| pilot_007 | jev_gate | True | 3 | done |
| pilot_007 | llm_gate | True | 3 | done |
| pilot_007 | llm_noask | False | 0 | done |
| validation_002 | jev_gate | True | 2 | done |
| validation_002 | llm_gate | True | 2 | done |
| validation_002 | llm_noask | False | 0 | done |

最终 cohort 全部 27 个机器人技能成功，所有 episodes 均由 Planner 返回 DONE。NoAsk 的两次失败来自真实偏好不匹配，不是人为标注。三个样本的初始公开 payload、Planner 配置与提示哈希均已自动验证在方法之间相同。

## API 连通性与成本审计

本地 `.env` 已安全合并并设置为 0600，未提交。DeepSeek 与 TypeSafe 均完成真实模型发现与实际推理。
- deepseek: configured `deepseek-flash`，returned `deepseek-flash`，schema valid；smoke input/output=49/5，latency=828.360 ms。
- jev: configured `jev-latest`，returned `jev-1.14.0`，schema valid；smoke input/output=320/24，latency=263.312 ms。
- 全部认证 HTTP attempts = **95/200**，完整在线 episodes = **12/12**。95 个 attempt 的 session ID 从 1 到 95 连续且唯一，已与 ledger 核对。
- 95 包括：3 次模型发现 GET、2 次 smoke 推理、2 次 gate-only 诊断、v1 的 20 次 episode 推理、v2 的 68 次 episode 推理。
- 所有实际推理请求都返回了真实 usage。模型发现没有 token usage，保持 null。在线未出现重试、schema error 或 HTTP/API error。
- DeepSeek 实际返回的模型字段是 `deepseek-flash` 别名，不能据此声称锁定了底层精确 build；Jev 返回 `jev-1.14.0`。
- 首个 DeepSeek discovery 日志在 ledger 写入模式调试后从实际终端输出恢复，保留 recovery note 和真实 latency；高水位计数始终保留，没有把该次请求遗漏到预算之外。
- 本地结构化用户模拟器不调用 API，其耗时单独写入 episode。离线生成耗时及哈希在 `data/generation_manifest.json`；oracle 耗时逐条保留。

## 物理验证和测试

- 开始开发前原测试：26 passed。最终：**66 passed in 34.61 s**；离线 pytest 全局禁止 urllib 网络请求。
- 最初 oracle：validation 3/5、pilot 4/20；红杯抓取会碰盒沿。失败证据位于 `outputs/phase2/oracle_initial_red_cup_collision/`。
- 当前 benchmark 场景仅把红杯安全源位置改为 (0.38, -0.12)，其余沿用原几何和 ±4 mm 扰动。原 Scripted Demo 默认布局保持原样。修复后 validation 5/5、pilot 20/20。
- 从盒内重抓时提高末端安全间隙，仍检查原有 25 mm tracking / 40 mm hand proximity。真实早盖盒、取盖、装错块、取回、换块和重新盖盒的恢复测试通过。没有通过重设最终位姿完成动作。
- Evaluator 保留完整 AABB、支撑接触、盖口角点和释放检查，使用最后相关盖盒事件允许恢复；task_success 与 termination_reason 独立。预算结束时真实完成的状态可成功。

## 文件和复现

- 最终原始 episodes / request responses / PNG / GIF：`outputs/phase2_live/paired_v2/`。每个 episode 都含逐轮公开 payload、模型响应、实际动作、稠密物理轨迹、ASK 冻结检查、评分与 usage。
- 最终 CSV 与报告：`outputs/phase2_live/paired_v2/{episodes.csv,summary.csv,summary.json,report.md}`。
- v1 诊断：`outputs/phase2_live/paired/`，独立 CSV 与报告。
- API smoke：`outputs/phase2_live/api_smoke.json`、`api_smoke_attempts.jsonl`；额外诊断：`public_context_probe.*`。
- 预算和全局证据：`outputs/phase2_live/session_budget.json`、`outputs/phase2/evidence.json`；pytest：`outputs/phase2/pytest.xml`。
- 大型 GIF 仅保留本地，截图、原始脱敏 JSON/JSONL、CSV、数据与代码进入 Git。

```bash
python -m when2ask doctor
python -m when2ask doctor --live
python -m when2ask generate --split validation --count 5 --seed 42
python -m when2ask generate --split pilot --count 20 --seed 42
python -m when2ask validate --split validation --oracle
python -m when2ask validate --split pilot --oracle
python -m when2ask run --sample validation_002 --method llm_noask --live
python -m when2ask run --sample validation_002 --method llm_gate --live
python -m when2ask run --sample validation_002 --method jev_gate --live
python scripts/run_pilot.py --live
python -m when2ask report --run-dir outputs/phase2_live/paired_v2
python scripts/verify_phase2.py
python -m pytest -q --junitxml=outputs/phase2/pytest.xml
python scripts/secret_scan.py
```

本轮已经耗尽完整 episode 配额；上述 run_pilot 重跑只保留匹配的已完成结果，不会新增调用。重现新在线运行应另行规划新 session 与预算。离线 report/verify 不发送网络请求。

## 限制与下一阶段

这三个最终样本只用于工程验收。v2 提示是在 validation 诊断后明确的；没有对 held-out test 调参，也没有用这些数字做统计检验。pilot 在线样本属于 dev 偏好家族。本轮不构成正式 Dev/Test 实验。
下一阶段先冻结公开任务契约、提示、模型版本和恢复规则。在新的 Dev groups 上选择 Jev threshold，再锁定配置。Test groups 必须与 Dev 在归一化任务家族层面隔离，并增加布局/任务模板家族；覆盖 0/1/2/3 未知偏好、不同先可执行子目标及冲突修复。
预先规定新的调用预算与失败处理规则，逐样本三方法配对并报告不确定性。保留 backend 分别的 token、真实 latency、usage 缺失计数和控制器失败。需要时按供应商实际账单口径另算货币成本。当前 constraint 辅助抓取、固定几何和未校准 Noul 阈值仍是限制。
