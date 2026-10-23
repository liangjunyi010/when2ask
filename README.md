# When2Ask — Clarification Timing for Robotic Task Execution

真实 PyBullet / Franka Panda 的 Pack and Cover MVP。机器人先执行已知的蓝杯装箱，再决定询问偏好或按公开默认策略继续。全项目不调用 LLM / Jev API，不训练模型。

![真实 PyBullet 初始场景](outputs/ask_demo/scene.png)

## 在本机观看

```bash
cd ~/Desktop/CS4278/when2ask
bash scripts/setup_env.sh
source .venv/bin/activate
python demo.py --mode ask --gui
```

GUI 中能看到机械臂接近、抓取、抬升、运输、放置、释放与等待稳定。每次执行结束自动关闭连接。第一次安装 PyBullet 需要源码编译，可能花几分钟。

```bash
python demo.py --mode noask --gui
python demo.py --mode ask --record
python demo.py --mode noask --record
# 也可同时打开 GUI 并录制，或指定独立输出目录
python demo.py --mode ask --gui --record --output-dir outputs/my_demo
```

`--record` 默认使用 DIRECT 和 CPU TinyRenderer，无需 GUI、显示器或 ffmpeg。GIF 帧取自执行中的 Bullet 世界，字幕仅标注当前动作、问题、回答和仿真步数。ASK 的停顿通过真实静止帧延长显示时间，不推进仿真。

可用 `--seed 3`、`--fast`（仅取消 GUI 的主动时钟节流）和 `--require-success`。正常完成但不符合偏好的 NoAsk 默认退出码为 0；加 `--require-success` 时评分失败退出 2，执行或产物错误退出 1。

## 环境与安装

实际验证平台：macOS 26.6.2 / Apple Silicon arm64，CPython **3.11.16**，uv **0.12.21**，Apple clang 21，Git **2.47.1**，GitHub CLI **2.98.0**。

| 运行依赖 | 已验证版本 |
|---|---:|
| pybullet | 3.2.7 |
| numpy | 2.4.6 |
| pillow | 13.0.0 |
| pytest | 9.1.1 |

`pyproject.toml` 声明依赖，`requirements-lock.txt` 固定测试环境的传递依赖。无需 pyyaml。推荐使用已安装的 uv；其他 macOS 机器可以先 `brew install uv`。缺少编译器时先安装 Apple Command Line Tools。已有 Python 3.11 时，安装脚本也支持普通 venv/pip。

安装脚本只创建/使用本项目 `.venv`。此机器的默认 macOS 27 SDK 与当前链接器不兼容，因此构建 PyBullet 时使用已安装的 **MacOSX26.5.sdk**，并传入 `CFLAGS=-Dfdopen=fdopen` 修复其旧 zlib 宏冲突。这些设置仅影响构建进程。需要其他 SDK 时：

```bash
WHEN2ASK_SDKROOT=/path/to/MacOSX.sdk bash scripts/setup_env.sh
```

不使用 uv 的等价安装方式（已具备 Python 3.11 和兼容 SDK）：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install pip==26.2.2 setuptools==84.2.1 wheel==0.48.0 numpy==2.4.6
SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk \
  CFLAGS=-Dfdopen=fdopen python -m pip install --no-build-isolation pybullet==3.2.7
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps .
python scripts/verify_direct.py
```

入口脚本直接使用 checkout 的 `src/`，测试也使用源文件，因此编辑源码后可直接重新运行 demo/pytest。若在其他 Python 程序中导入安装的包，编辑后重新运行 `python -m pip install --no-deps .`。

## 任务与两种模式

公开指令：

> Put one cup and one block in the box, then cover it. Use the blue cup. Leave all unselected objects outside the box.

默认隐藏偏好为 `blue_cup / green_block / black_lid`。场景固定物体 ID 为 `box`、`red_cup`、`blue_cup`、`green_block`、`yellow_block`、`black_lid`、`white_lid`。

- **scripted_ask**：蓝杯入盒 → 同轮询问 `block_choice` 和 `lid_choice` → 用户仅回答这两个 slot → 绿块入盒 → 黑盖盖盒 → evaluator。一次问题请求两个 slot，burden 为 2。
- **scripted_noask**：蓝杯入盒 → 对未知类别，按当前公开 observation 中到盒子的 XY 距离选择最近对象，距离相同时按稳定 ID 排序 → 装块 → 盖盒。默认 seed 0 选择黄块和黑盖。它没有 UserSimulator 实例，也不读取隐藏偏好。

默认 seed 0 的实际结果：

| 模式 | 物理技能成功 | 最终 task_success | burden | 原因 |
|---|---:|---|---:|---|
| Ask | 3/3 | true | 2 | 满足所有物理条件与偏好 |
| NoAsk | 3/3 | false | 0 | 黄块入盒，隐藏偏好要求绿块 |

NoAsk 没有被强制判失败：自动测试将隐藏方块偏好改为黄块后，完全相同的公开 observation、决策与物理动作得到成功评分。另已真实测试 Ask 遵循黄块/白盖的替代隐藏偏好。

固定 seeds **0、1、2、3、4**：Ask 物理完成 **5/5**、任务成功 **5/5**；NoAsk 物理完成 **5/5**、当前隐藏偏好下任务成功 **0/5**。这是对小幅位置扰动的工程回归，不能作为正式 LLM/Jev 实验成功率。逐次结果在 `outputs/verification/seed_summary.json`。

## 物理实现与评分

场景使用 1/240 秒固定步长、150 次 solver iterations 和固定 RNG seed。桌面、固定基座 Panda、盒底/四面墙、两只带杯底与薄壁的开放杯、两个块和两个盖子都是真实 collision shapes / rigid bodies。源物体 XY 有 ±4 mm 的种子控制扰动；盒子固定，初始物体之间无超过 1 mm 的穿透。

`RobotSkills.pick_place(object_id, target_id, relation="inside")` 与 `cover(lid_id, box_id)` 通过 IK 和 POSITION_CONTROL 移动 Panda。辅助抓取仅在末端到抓取点距离不超过 25 mm、且手部 collision geometry 到物体不超过 40 mm 时建立固定 constraint。物体跟随机械臂运动，释放后自然落下并稳定。所有日志明确记录 `grasp_mode=constraint`。仅对被抓物体暂时关闭手部碰撞，世界碰撞与其余机械臂碰撞继续生效，退出后恢复。每个技能最多 15,000 个物理步，每段移动也有收敛上限。

Evaluator 在执行结束后独立读取 Bullet 状态：

- 选中杯/块的**完整 collision AABB** 都在盒内，垂直范围正确、与盒子有向上的实际承重接触、速度已稳定。
- 正确盖子的实际旋转坐标系覆盖全部四个盒口角点，高度与倾角合适，在跨越盒沿的接触点上得到支撑且稳定。
- 未选物体的完整水平包围范围与盒子分离，且已稳定。
- 机器人没有保留物体约束，也未接触目标物体。
- 盖盒开始时，物理传感记录已经确认必要杯/块在盒内，之前对应装箱技能已完成并释放。

评分不会只看物体中心或 agent 报出的 ID。日志保存每项 boolean 条件和几何/接触细节、终止原因、burden、动作次数、成功动作次数、仿真步数。失败 episode 同样保存。

## 公开/私有边界

`PrivateTaskSpec` 只由 runner、结构化 UserSimulator 和最终 Evaluator 持有。Environment 完全不接受隐藏偏好。策略唯一输入为 `PublicState(instruction, observation, history)`，包含公开指令、实际物理状态，以及公开动作/问答。UserSimulator 只返回所请求的 slot。ASK 不调用 `stepSimulation()`，运行时对比前后全状态与 step count。

这是可信程序中的接口边界，并非针对恶意 Python 插件的进程隔离。未来传给模型的 payload 必须仅从 PublicState 构造，不能把最终评分或 episode 的 evaluator 部分反馈给当前 episode 的策略。

## 输出与复现证据

```text
outputs/ask_demo/              outputs/noask_demo/
  scene.png                     scene.png
  action_01_pick_place.png       action_01_pick_place.png
  action_02_pick_place.png       action_02_pick_place.png
  action_03_cover.png            action_03_cover.png
  final.png                     final.png
  demo.gif                      demo.gif
  episode.json                  episode.json
  evaluation.json               evaluation.json
```

`episode.json` 含公开决策/问答、带步数的技能阶段日志、每 120 步的真实物理轨迹、ASK 冻结检查、最终评分，录制时还包含帧对应的仿真步数。PNG、示例 JSON、测试证据进入 Git；约 7 MB 的 GIF 保存在本地并被 `.gitignore` 排除，可用上面的命令重新生成。每次运行覆盖选定输出目录；保留旧运行时请使用 `--output-dir`。

```bash
python scripts/verify_direct.py
python scripts/verify_block.py
python scripts/verify_pack.py
python -m pytest -q --junitxml=outputs/verification/pytest.xml
python scripts/verify_seeds.py --seeds 0 1 2 3 4
python scripts/verify_artifacts.py
```

最终 pytest：**26 passed**。自动测试覆盖物理渲染/退出、真实方块运输、完整两种策略、替代偏好、ASK 冻结、不泄露未询问偏好、伪造动作标签、远距离抓取拒绝、技能步数上限、失败结果落盘、跨墙物体、旋转/悬空盖子、动作顺序和未释放约束。负面几何测试会刻意重设测试物体位姿制造反例；实际技能和成功轨迹不重设物体位置。

## 范围与后续

这是 scripted baseline 的工程 MVP。LLM-NoAsk、LLM-Gate、Jev-Gate 均未接入；没有模型推理成本或正式 benchmark 结论。夹爪使用 constraint 辅助，不是经力闭合验证的摩擦抓取；当前 IK 路线只验证了这个桌面布局与小幅扰动，尚无通用碰撞路径规划、任意形状处理或硬件验证。GIF 已实现，MP4 未实现。

下一阶段在 `scripted_agent.py` 的 `decide(PublicState) -> Decision` 接口替换策略，由 gate 先选择 ASK/CONTINUE，再由规划器产生结构化输出。继续共用 runner、UserSimulator、skills 与 Evaluator，校验 slot/物体 ID/动作预算；另行记录模型 token 和 latency。Jev 阈值应在单独的开发集上确定，正式比较需要新的任务集及种子划分。

实现与验证细节见 [implementation_status.md](docs/implementation_status.md)，引用与资产许可见 [sources.md](docs/sources.md)。

## GitHub 发布

目标仓库为 **Private**。虚拟环境、`.env`、密钥、缓存、GIF/MP4 和批量回归轨迹不会提交。复现发布检查：

```bash
git status --short
gh repo view --json url,isPrivate,defaultBranchRef
git rev-parse HEAD
git ls-remote origin refs/heads/main
```
