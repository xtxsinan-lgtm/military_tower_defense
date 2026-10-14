# AGENTS.md — AI 协作说明

> 本文件面向 AI 编码助手。开始任何任务前先读完本文件。
> 详细任务清单与完整约束见 [docs/开发任务分解_WBS_v1.md](docs/开发任务分解_WBS_v1.md)（第 0 章为必读）。

## 1. 项目一句话

《守夜》Nightwatch：以俄乌战争为背景的硬核防空塔防 / 策略游戏。玩家提前部署防空网，迎接一夜又一夜的空袭。
Godot 4（.NET）+ C#，Steam（Windows + macOS），个人开发 + AI 辅助。

## 2. 文档优先级

| 文档 | 用途 | 冲突时 |
|---|---|---|
| [GDD](docs/游戏设计文档_GDD_v1.md) | 做什么、为什么 | 设计层面以 GDD 为准 |
| [WBS](docs/开发任务分解_WBS_v1.md) | 怎么做、验收标准、依赖 | 执行层面以 WBS 为准 |
| [数值表](docs/塔防数值表_v1.md) | 所有数值与规则参数 | 数值以数值表为准 |
| [武器投入时间表](docs/俄乌战争塔防_武器投入时间表.md) | 历史依据 | — |
| [战役关卡设计](docs/战役关卡设计_v1.md) | 关卡历史背景 | 与 GDD 冲突时以 GDD 为准 |

## 3. 全局约束（硬性）

1. **只用 Godot 4 API**。禁止 Godot 3 写法：`KinematicBody2D`、`yield`、`export var`、`onready var`、`connect("signal", obj, "method")` 等。C# 中使用 `[Export]`、`await ToSignal(...)`、`CharacterBody2D`。
2. **模拟层独立**：`sim/` 下的代码**禁止** `using Godot;` 或引用任何 Godot 程序集。必须能用 `dotnet test` 在命令行独立运行。
3. **确定性**：模拟层只用 `SimRandom`（以种子初始化、可派生子流）。禁止 `System.Random`、`DateTime.Now`、`Guid.NewGuid()`、并行时的不确定顺序；**不得以 `Dictionary` / `HashSet` 的遍历顺序作为逻辑依据**（需要遍历时按 ID 排序或使用有序容器）。
4. **数据驱动**：单位、武器、敌人、关卡、波次的参数一律放在 `data/` 的 JSON 中，代码中不写死数值。测试使用小型手写数据，不依赖正式数值。
5. **测试**：`sim/` 中的每条规则都要有单元测试；提交前 `dotnet test` 必须全部通过。
6. **命名**：代码标识符用英文；注释和文档用中文；数据中的显示文本用本地化键引用（`loc.xxx`），不直接写中文。
7. **文档同步**：实现与 GDD / 数值表不一致时，**先停下来说明差异**，由人决定改代码还是改文档。不要悄悄"修正"设计。
8. **敏感内容**（GDD 第 17 章）：玩法目标是保护；伤亡不做成画面奖励；人物、部队番号、生产设施一律虚构；数值是游戏化抽象，电子战只描述效果，不整理真实武器的技术参数。

## 4. 目录说明

```
/
├─ AGENTS.md            本文件
├─ docs/                设计文档
├─ data/                JSON 数据（唯一的数值来源）
│  ├─ schema/           JSON Schema
│  ├─ units/            玩家单位（枪、眼、盾、假）
│  ├─ enemies/          敌方单位
│  ├─ support/          外部支援
│  ├─ levels/           关卡：<level_id>/level.json、waves.json、map/
│  ├─ campaign/         战役、跨关影响、奖励卡
│  ├─ narrative/        剧本、简报、台词
│  └─ loc/              本地化文本（中文为源语言）
├─ sim/                 纯 C# 模拟核心（类库，无 Godot 依赖）
├─ sim.tests/           单元测试（xUnit）
├─ tools/               命令行工具（doctor、validate、simrun、balance、mapimport、render）
├─ game/                Godot 4 .NET 项目（渲染、输入、UI、音频）
└─ art_src/             美术源文件（Git LFS）
```

模拟层内部约定（WBS 01.A / 01.B）：
- 时间单位为**世界秒**，固定 1 世界秒一步；坐标单位为米，x 向东、y 向北，高度单独存储。
- 浮点用 `double`；实体按类型分组存储、用整数 ID 引用，不使用深继承。
- `SimWorld.Step()` 中各系统的执行顺序固定，见 WBS 01.B，**不得随意调整**。

## 5. 常用命令

> 部分工具尚未实现，标注了对应任务编号。

```bash
# 开发环境检查（WS06-005）
./tools/doctor/doctor.sh

# 运行模拟层测试（WS01-001 之后可用）
dotnet test sim.tests

# 数据校验（WS06-004 之后可用）
dotnet run --project tools/validate

# 无画面跑一夜（WS06-006 之后可用）
dotnet run --project tools/simrun -- --level test_01 --seed 1
```

版本要求：.NET SDK 8 或更高（`sim/` 目标框架 `net8.0`，与 Godot 4 .NET 保持兼容）；Godot 4.x **.NET 版**（不是标准版）；Blender 4.x（M2 起需要）。

## 6. 执行任务的标准流程

1. 读取任务条目（WBS）及其引用的 GDD 章节、数值表段落。
2. 检查依赖任务是否完成（看 `git log` 中的 `[WSxx-nnn]` 提交）。
3. 有不明确之处：**列出问题并等待回答**，不要自行假设重大设计。
4. 实现 → 编写 / 更新测试 → 运行 `dotnet test`（或 Godot 无头运行）。
5. 按"验收"逐条自查。
6. 🟡 / 🔴 任务：输出"需要人工确认的事项"清单，等待确认后才算完成。
7. 提交。

人工参与标记：🟢 AI 主导 · 🟡 AI + 人工审核 · 🔴 人工主导（AI 只做准备工作，不替人做最终决定）。

## 7. 提交规范

- **一个任务一个提交**，信息格式：`[WSxx-nnn] 简短说明`（中文）。
- 非任务性的修改：`docs: …`、`chore: …`、`fix: …`。
- 不提交构建产物（`bin/`、`obj/`、`.godot/`）；美术与音频大文件走 Git LFS（见 `.gitattributes`）。

## 8. 常见陷阱

- AI 生成的军事装备模型 / 图片常有结构错误：**不要直接使用**，标注"待人工校正"。
- 数值表中的"游戏秒" × 60 = 世界秒。
- 快速目标（导弹、拦截弹）不做逐帧碰撞，而是**解析计算拦截时刻**，到点后掷骰。
- 历史考据只使用公开来源，不确定的标注 ≈ 并说明。
