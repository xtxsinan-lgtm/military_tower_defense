# 00 核心约定与模拟框架

> 本文件是 `docs/spec/` 的地基：其余 6 份规格引用这里定义的**术语、类型、子流名、实体类型、事件 / 命令名称和接口**。
> 本文件中的名字就是最终代码中的名字；其他规格不得为同一概念另起名字（需要新名字时先补进本文件）。
> **修订（D2b，2026-10-17）**：已应用 `review/A_interfaces.md` 第 1 节登记补丁 P01–P50、A / B / C 报告中指向 00 的 T1 / T2 条目与 `review/DECISIONS.md`；逐条去向见 `review/APPLY_LOG.md` 的"00_core.md"小节。01–06 的登记内容（实体字段、单例组件、子流用途、事件 / 命令字段、规则文件加载序）**以本文件为准**；各规格第 2 / 4 节细化字段时不得改变本文件给出的名字与顺序。

---

## 0. 范围与依据

### 0.1 覆盖范围

| 主题 | 本文件章节 | 对应 WBS |
|---|---|---|
| 术语表、单位与换算、角度约定 | 0.3、0.4 | 01.A |
| 项目结构（`sim/`、`sim.tests/`） | 0.5 | WS01-001 |
| `SimRandom`、子流 | 2.1、3.1 | WS01-002 |
| 实体存储与 ID、`SimState` | 2.2 – 2.5 | 01.A、WS01-003 |
| `SimWorld`、`Step()` 框架、命令队列、事件流、快照、夜晚结束 | 2.6、3.2 – 3.6 | 01.B、01.C、WS01-003 |
| 事件与命令的公共格式和总表 | 4 | 01.C |
| 数据加载契约（JSON → C#） | 1 | WS01-004 |
| 确定性、状态哈希、回放文件 | 3.7 – 3.9、6.2 | WS01-020 |

本文件**不**定义任何玩法规则（探测、交战、伤害、AI……），只定义它们共用的框架。

### 0.2 依据

- [AGENTS.md](../../AGENTS.md) 第 3、4 节（全局约束、目录与模拟层约定）
- [WBS](../开发任务分解_WBS_v1.md) 0.3、01.A、01.B、01.C、01.D（WS01-001 – 004、020）、02.A
- [GDD](../游戏设计文档_GDD_v1.md) 第 5 章（核心循环、指挥点操作、二选一）、第 6 章（单位体系、目标标签）、第 7 章（敌方体系）、第 8 章（核心系统）、第 11 章（时间结构、时间比例）、16.4（技术架构）、附录术语表
- [data/README.md](../../data/README.md)（单位后缀、区间取值、合并行、暂定值）
- `data/schema/*.json`（全部 14 个 Schema）、`data/rules/conventions.json`

依赖：无（00 是根）。其余规格都依赖本文件。

### 0.3 术语表

> 规则：中文用于文档与注释，英文名用于代码标识符。**同一个概念全目录只用这一个英文名。**
> 数据定义（JSON 中的条目）的 C# 类型一律以 `Def` 结尾；运行时实例（实体）不带后缀。例如 `WeaponDef`（武器定义）vs `Interceptor`（飞行中的拦截弹）。

#### 0.3.1 时间与框架

| 中文 | 英文（代码） | 含义 |
|---|---|---|
| 世界秒 | world second（`Sec` 后缀） | 模拟内部的时间单位，真实世界的 1 秒 |
| 游戏秒 | game second（`GameSec` 后缀，仅数据中出现） | 数值表的时间单位；1 游戏秒 = `conventions.gameSecToWorldSec` 世界秒（= 60） |
| 步 | `Tick`（整数） | 一次 `SimWorld.Step()`；步长 `StepSec` = `conventions.worldStepSec`（= 1 世界秒） |
| 夜晚 | `Night` | 一次 `SimWorld` 的生命周期：从 `Create` 到 `NightEnded` |
| 夜晚序号 | `NightIndex` | 关卡内第几夜，**从 1 开始**（与 `waves.json` 的 `night` 一致） |
| 模拟世界 | `SimWorld` | 对外门面：创建、推进、命令、事件、快照 |
| 模拟状态 | `SimState` | `SimWorld` 内部的全部可变状态（参与哈希） |
| 系统 | `ISimSystem` | `Step()` 中按固定顺序执行的 14 个系统之一 |
| 系统上下文 | `SimContext` | 传给系统的参数包（状态、数据、本系统子流、事件出口） |
| 命令 | `SimCommand` | 外部（玩家 / 回放）输入，带生效步 |
| 事件 | `SimEvent` | 模拟输出的事实记录 |
| 快照 | `SimSnapshot` | 某一步结束时的只读状态副本，供渲染 / 界面 |
| 状态哈希（快照哈希） | `StateHash` | 对 `SimState` 规范序列化后计算的 64 位哈希，用于确定性校验 |
| 回放 | `Replay` | 种子 + 关卡 + 数据哈希 + 配置 + 命令列表 |
| 种子 | `Seed`（`ulong`） | 一夜模拟的根随机种子 |
| 子流 | stream（`IRandom`） | 由根种子 + 子流名派生的独立随机序列 |
| 一夜结算 | `NightResult` | 夜晚结束时产出的结算数据 |
| 阶段 0 | Stage 0（代码：`CommandStage`） | `Step()` 开头、系统 1 之前的命令应用 / 部署计时 / 二选一 / 剧情阶段（3.4，04 3.1）；是对 WBS 01.B 的补充，不改变 1–14 的顺序（B-T2-15） |

#### 0.3.2 我方

| 中文 | 英文（代码） | 含义 |
|---|---|---|
| 我方单位 | player unit（公共字段块 `PlayerUnitCommon`） | 可部署单位的统称：枪 / 眼 / 盾 / 假 |
| 火力单元（枪） | `FireUnit` / `AirDefenseUnitDef` | 一个防空单元实例（数据：`units/air_defense.json` 的 `units[]`，"一个火力单元 / 连"） |
| 发射架 | `Launcher`（`FireUnit` 内的组件，非独立实体） | 火力单元下的一个发射架；弹仓按发射架计（`weapons[].launchers`、`magazine`） |
| 武器 | `WeaponDef` | 火力单元可用的一种弹药 / 身管武器（`weapons[]`）；相同武器 ID = 共享弹药池 |
| 拦截类别 | `InterceptClass` | 拦截概率矩阵的行（`rules/intercept.json` 的 `classes`） |
| 探测单位（眼） | `SensorUnit` / `SensorDef` | 雷达、声学哨、观察哨等（`units/sensors.json`） |
| 电子战单位（盾） | `EwUnit` / `EwUnitDef` | `units/ew.json` |
| 欺骗单位（假） | `DeceptionUnit` / `DeceptionUnitDef` | 诱饵辐射源、牺牲雷达、假发射车（`units/deception.json`） |
| 诱饵辐射源 | decoy emitter（`DeceptionUnit` 的一种） | **我方**欺骗装置；不要与敌方"诱饵 `DECOY`"混淆 |
| 辐射源 | `Emitter`（能力，不是实体类型） | 会主动辐射、可被反辐射导弹追踪的单位（雷达、电子战站、诱饵辐射源） |
| 辐射策略 | `EmissionPolicy` | 雷达开关机的预设规则（GDD 8.2） |
| 触发规则 | `EmissionTrigger` | 反辐射来袭处置、开火后转移、主雷达被毁接替（GDD 8.2） |
| 暴露度 | `Exposure`（0–100，`double`） | 单位被敌方定位的程度 |
| 交战规则 | `EngagementRule` | 目标优先级、开火纪律、弹药保留（GDD 5.2、WS01-009） |
| 交战 | engagement | 火力单元决定对某航迹开火的一次决策 |
| 发射 | shot / launch | 发出一枚拦截弹（或一次身管射击） |
| 拦截弹 | `Interceptor` | 飞行中的拦截导弹或拦截无人机（实体） |
| 拦截点 | intercept point（`InterceptAtSec`、`InterceptPos`） | 解析求出的拦截时刻与位置 |
| 拦截判定 | intercept resolution | 到达拦截点时按"拦截概率 × 修正"掷骰 |
| 展开 / 撤收 / 转移 | deploy / pack / relocate | 我方单位的部署状态变化（`UnitDeployState`） |
| 备用阵地 | alternate position（`AlternatePositionDef`） | `map/deploy.json` 的 `alternatePositions`；`surveyed` = 预先勘察 |
| 保护目标 | `Structure` / `StructureDef` | `map/structures.json` |
| 电网节点 / 连线 | `GridNode` / `GridLinkDef` | `map/grid.json` |
| 外部支援 | support（`SupportDef`、实体 `SupportAsset`） | 战斗机、国家级电子战、邻州火力组等 |
| 战斗机 | `FighterDef` | `support/fighters.json` |
| 架次 | sortie | 一次战斗机出动 |
| 空袭警报 | `AirRaidAlert` | GDD 8.6 |
| 指挥点 | `CommandPoints` | 每夜可用于关键操作的点数 |
| 二选一请求 | `ChoiceRequest` | 慢放 + 二选一（GDD 5.2），超时按默认 |
| 碎片 | `Debris` | 城区上空拦截产生的地面伤害（GDD 8.4）；在 `ImpactSystem` 当步结算，**不是**持续实体（B-T2-16） |
| 交换比 | `ExchangeRatio` | 被拦截目标的潜在损失 ÷ 拦截弹价格（潜在损失公式 → 03，B-T3-01） |
| 部署方案 | `DeploymentPlan` | 夜晚开始前已就位的我方单位与设置（`SimConfig` 的一部分） |
| 部署条目 | `Placement`（类型 `PlacedUnit`） | 部署方案中的一项；实体字段 `Placement` 保存它（不哈希） |
| 花名册编号 | `RosterId` | 战役花名册中单位的编号（05）；`CarryIn` / `CarryOut` 按它匹配实体；0 = 非战役单位 |
| 辐射控制 | `EmitterControl` | 辐射源单位的开关机状态组件（02 2.2） |
| 精确持有者 | `PreciseHolderIds` | 对某航迹给出"精确"的火力单元集合（02 2.5）；导弹 / 火箭只能对自己持有精确的航迹发射 |
| 弹药池 | `AmmoPool`（夜内）/ `Depot`（战役层，05） | 关卡配额中尚未分配到发射架的弹药；夜内一律称 `AmmoPool` |
| 部署档 | `DeployTier` | 单位展开 / 撤收时间的档位（`instant` / `minutes` / `hours_short` / `hours` / `fixed`，04） |

#### 0.3.3 敌方与探测

| 中文 | 英文（代码） | 含义 |
|---|---|---|
| 敌方目标 | `Threat` | 地图上任何一个敌方空中物体的**真实**状态（弹药或平台） |
| 敌方弹药 | munition（`MunitionDef`，`ThreatKind.Munition`） | 导弹、无人机、诱饵、滑翔炸弹等（`enemies/munitions.json`） |
| 敌方平台 | platform（`PlatformDef`，`ThreatKind.Platform`） | 飞机、直升机、平台型无人机（`enemies/platforms.json`） |
| 诱饵（敌方） | decoy（目标标签 `DECOY`） | Gerbera 等敌方诱饵无人机 |
| 目标标签 | `TargetTag` | `UAV` `JET_UAV` `DECOY` `CM` `SCM` `BM` `HBM` `GB` `HELI` `AC_LOW` `AC_HIGH` |
| 精度档 | `AccuracyTier` | `A` `B` `C` `D` |
| 伤害等级 | `DamageLevel`（0–10） | 数值表 3.2 |
| 波次 | `WaveDef` | `waves.json` 的一波 |
| 组 | `WaveGroupDef` | 一波中的一组同型目标 |
| 进入点 | `EntryPointDef` | 敌方目标进入地图的位置 |
| 航线 / 航点 | route / waypoint（`RouteDef`） | 进入点 → 航点 → 目标 |
| 敌方 AI 标签 | `AiTag` | `probe` `suppress` `hunt` `bypass` `saturate`（GDD 7.4） |
| 已知目标清单 | `KnownTargetList` | 敌方 AI 掌握的我方目标（GDD 7.4"猎杀"） |
| 探测 | `Detection` | 某传感器在某一步对某敌方目标的一次原始探测（**每步临时数据，不是实体**） |
| 航迹 | `Track` | 由探测融合而成、玩家和交战系统可见的目标估计（实体） |
| 航迹质量 | `TrackQuality` | `Vague` 模糊 / `Approximate` 大致 / `Precise` 精确 |
| 预警 | early warning | 国家层给出的"模糊"预警（`entryPoints[].warningGameSec`） |
| 火控指示 | cueing | 大致以上航迹覆盖下火控雷达只在最后时刻开机（`rules/tracks.json` 的 `cueing`） |
| 诱饵甄别 | decoy discrimination | 按航迹质量的概率识别敌方诱饵 |
| 反辐射导弹 | ARM（`tracksEmittingRadarOnly = true` 的弹药） | 只追踪开机雷达 |
| 落地 / 命中地面 | impact | 敌方弹药（或碎片）到达地面并结算伤害 |
| 已知目标带出记录 | `KnownTargetCarry` | 夜末带出、次夜带入的敌方已知目标记录（04 定义类型，05 搬运） |
| 推迟的波次组 | `HeldWave` | 敌方 AI 压制行为暂缓生成的组（04 2.3） |
| 覆盖查询 | `CoverageQuery` | 供客户端绘制探测覆盖的只读查询（02 定义；与模拟使用同一可见性函数） |
| 空间索引 | `ThreatGrid` / `TrackGrid` | 每步重建的派生网格索引，加速"圆内目标 / 航迹"查询（3.3.1）；不参与哈希 |

### 0.4 单位、坐标与角度约定

#### 0.4.1 模拟内部单位（全部 `double`，除注明外）

| 量 | 内部单位 | C# 字段后缀 | 说明 |
|---|---|---|---|
| 时间 | 世界秒 | `Sec`（时刻用 `AtSec`） | `TimeSec = Tick × StepSec` |
| 步 | 步 | `Tick`（`int`） | 计数，`Tick` 从 0 开始 |
| 水平距离 / 坐标 | 米 | `M`；坐标用 `Vec2 Pos` | |
| 高度 | 米，**相对地面**（AGL） | `AltM` | WBS 01.A："高度单独存储（米，相对地面）"；海拔 = 地形高程 + `AltM`（地形采样见 01） |
| 海拔 | 米 | `ElevationM` / `MslM` | 仅地形与视线计算使用 |
| 速度 | 米 / 秒 | `Mps` | |
| 加速度 | 米 / 秒² | `Mps2` | 例：01 `MotionLeg.VertAccelMps2` |
| 速率（每时间） | 每世界秒 | `PerSec` | |
| 角度 | 弧度 | `Rad` | 见 0.4.3 |
| 价格 | 百万美元 | `Musd` | 不换算 |
| 概率 | 0–1 | 无后缀 | |
| 比例 / 份额 | 0–1 | `Frac` | `…Pct` 的换算结果（0.4.2）及其他份额量（如 `ShelteredFrac`、`WeightedLossFrac`）；倍率类量用 `…Mult`，不用 `Frac` |
| 暴露度 | 0–100 | 无后缀 | |
| 每战役日（战役层） | 每天 | `PerDay` | 不换算；例：`cityResourcePerDay`、05 `dayExposureDecayPerDay`、`structureHpFracPerDay` |
| 战役日 / 夜计数（战役层） | 天 / 夜（整数） | `Days` / `Nights` | 不换算；例：05 `startDays`、`arrivalDays`、`woundedNights`、`durationNights`。`…Day`（单数）表示"第几天"（如 `returnAfterDay`） |

#### 0.4.2 加载时换算（只在数据加载层完成，系统代码里不出现换算系数）

换算系数一律读自 `data/rules/conventions.json`（以下记为 `C`）；`1000` 与 `3.6` 是 SI 定义，不是游戏数值。

| JSON 字段后缀 / 名称 | 数据单位 | 换算公式（结果为内部单位） | C# 字段名改写 |
|---|---|---|---|
| `…Km` | 游戏 km | `v × 1000` | `…M` |
| `…M` | 米 | `v` | `…M` |
| `…GameSec`，或字段名恰为 `gameSec` | 游戏秒 | `v × C.gameSecToWorldSec` | `…Sec`（`gameSec` → `Sec`） |
| `…Kmh` | km/h | `v ÷ 3.6` | `…Mps` |
| `…Cells` | 格 | `v × C.cellKm × 1000` | `…M` |
| `…PerGameSec` | 每游戏秒 | `v ÷ C.gameSecToWorldSec` | `…PerSec` |
| `…Musd` | 百万美元 | `v` | `…Musd` |
| `…Mach`（目前数据中没有） | 马赫 | `v × C.machKmh ÷ 3.6` | `…Mps` |
| `…Pct`（`gridDamagePct`） | 百分比 | `v ÷ 100` | `…Frac`（B-T1-01；data/README 第 2 节同步补一行） |
| `…PerDay`、`…Days`、`…Nights`、`…Day`（战役层） | 每天 / 天 / 夜 / 第几天 | `v`（不换算） | 不改名 |

规则：

1. 后缀匹配按**最长后缀优先**：先判 `PerGameSec`，再 `GameSec`、`Kmh`、`Km`、`Cells`、`Musd`、`Mach`、`Pct`，最后 `M`。字段名为 `M` 结尾但不是单位的（目前没有）须在加载器中列为例外。
2. 后缀作用于该字段下的**所有数值叶子**：`altitudeM`（`{min,max}`）、`offsetCells`（`{min,max}`）、`ratesPerGameSec`（对象，每个值都换算）、`rangeByTagKm`（对象，每个值都换算）都按此处理。
3. `null` 保持 `null`（C# 中为 `double?`）。
4. **公式中的乘除顺序固定**为上表所写（先乘后除，单次运算），保证结果的二进制可复现。例：`180 Kmh → 180 / 3.6 = 50.0`；`2 Mach → 2 × 1200 / 3.6 = 666.6666666666666`（先算 `2 × 1200 = 2400`，再 `÷ 3.6`）。
5. 数值表的"Mach"在数据中已换算成 `…Kmh`（data/README 第 2 节），原始写法在 `_source`，加载器不读 `_source`。
6. `conventions.worldStepSec` 必须等于 `1`（WBS 01.A 固定 1 世界秒一步）；否则加载报 `E_RANGE`。
7. **加载器特例**（现有数据字段名违反后缀约定，02 H1–H3）：
   - (a) `units/ew.json` 的 `offsetCellsAdd`：`Cells` 不在末尾，仍按 `Cells` 换算（`× C.cellKm × 1000`），C# 名 `OffsetAddM`（B-T3-08 之后仅供界面显示）；
   - (b) `configurableOnOffGameSec` 是布尔值，不换算，C# 名 `ConfigurableOnOff`；
   - (c) `sensorExposureLevelRates`、`ewExposureLevelRates`：每个值按每游戏秒 `÷ C.gameSecToWorldSec`，C# 名 `SensorExposureLevelRatesPerSec`、`EwExposureLevelRatesPerSec`。

   三者都应在 data 中改名（`offsetAddCells`、`configurableOnOff`、`sensorExposureLevelRatesPerGameSec`、`ewExposureLevelRatesPerGameSec`，A-3-04 / B-T1-09）；**data 改名完成后删除本条**，加载器回到纯机械规则。

#### 0.4.3 时间 ↔ 步的取整

```csharp
public static class SimTime
{
    public const double TickEpsilon = 1e-9;
    // 持续时间 → 需要的步数（向上取整，容忍浮点误差）
    public static int SecToTicksCeil(double sec, double stepSec)
        => (int)Math.Ceiling(sec / stepSec - TickEpsilon);
    // 时刻 → 所在步（向下取整，容忍浮点误差）
    public static int SecToTicksFloor(double sec, double stepSec)
        => (int)Math.Floor(sec / stepSec + TickEpsilon);
}
```

`sec < 0` 时抛 `ArgumentOutOfRangeException`。其他规格中"持续 X 秒 → 多少步"一律用 `SecToTicksCeil`，"在 X 秒时发生 → 第几步"一律用 `SecToTicksFloor`，除非该规格明确写了别的取整。

#### 0.4.4 坐标

- 二维平面，单位米；**原点在地图西南角**，x 向东、y 向北（WBS 01.A、data/README）。
- 地图范围 `[0, WidthM] × [0, HeightM]`；地图外的点（进入点、航点）可以为负或超出范围，模拟不裁剪。
- 类型：`public readonly record struct Vec2(double X, double Y)`，提供 `+ - * /`（标量）、`Dot`、`LengthSquared`、`Length`（`Math.Sqrt`）、`DistanceTo`、`Normalized()`（零向量返回零向量）。不提供三维向量类型；需要三维距离时显式写 `Math.Sqrt(dx*dx + dy*dy + dz*dz)`。**距离一律写成 `Math.Sqrt(dx*dx + dy*dy[ + dz*dz])`**，不得使用或自写 `hypot` 类函数（与 `Math.Sqrt` 形式可差 1 ulp，C-T1-04；见 6.2）。公共几何函数见 0.4.6。
- 高程图像素 `(0,0)` 为**西北角**（与世界坐标 y 方向相反）；像素 ↔ 世界坐标的映射与插值由 01 规定。

#### 0.4.5 角度（写死）

- **方位角（Bearing）**：从**正北顺时针**，弧度，取值范围 `[0, 2π)`。字段名 `BearingRad`。
- 计算：`BearingRad(from, to) = Normalize(Math.Atan2(dx, dy))`，其中 `dx = to.X − from.X`，`dy = to.Y − from.Y`（**注意参数顺序是 `(dx, dy)`**）。
- 方位角 → 单位向量：`(Math.Sin(b), Math.Cos(b))`。
- 规范化：`b < 0 → b += 2π`；之后若 `b >= 2π → b −= 2π`。`dx = dy = 0` 时方位角定义为 `0`。
- **俯仰角**：从水平面向上为正，弧度，`[−π/2, π/2]`，字段名 `ElevationRad`。
- 数据中若出现角度字段，一律用度并以 `Deg` 结尾，加载时 `× π / 180` 换成弧度、字段名改为 `…Rad`。
- 内部运算优先用向量，避免不必要的三角函数（见 6.2）。

#### 0.4.6 公共几何函数 `Geo`（全目录唯一实现，P48 / A-2-23 / A-3-09）

```csharp
namespace Nightwatch.Sim.Core;
public static class Geo                      // 只在本文件定义；其他规格需要新几何函数时先登记到这里
{
    public static double Normalize(double rad);                   // 0.4.5 规范化到 [0, 2π)
    public static double BearingRad(Vec2 from, Vec2 to);           // 0.4.5

    // 点在多边形内（交叉数法，射线向 +x，半开规则）。多边形不必闭合（首尾自动相连）；
    // 点恰在边上 / 顶点上的结果由下式唯一决定，不另做特判（各规格测试可依赖 T-00-38 的边界向量）。
    public static bool PointInPolygon(Vec2 p, IReadOnlyList<Vec2> poly)
    {
        bool inside = false;
        for (int i = 0, j = poly.Count - 1; i < poly.Count; j = i++)
        {
            var a = poly[i]; var b = poly[j];
            if ((a.Y > p.Y) != (b.Y > p.Y) &&
                p.X < (b.X - a.X) * (p.Y - a.Y) / (b.Y - a.Y) + a.X)
                inside = !inside;
        }
        return inside;
    }

    // 点在城区：level.Layers.Urban 中任一多边形（任意密度，数据顺序，找到即停）PointInPolygon 为真
    public static bool InUrban(LevelData level, Vec2 p);

    // 从 p 出发沿向量 d（速度或线段向量）的直线 p + u·d（u ≥ 0），第一次进入以 c 为圆心、半径 r 的圆（含边界）时的参数 u。
    // 已在圆内（含边界）→ 0；永不进入（含 d 为零向量）→ null。调用方自行判断 u ≤ 1（线段，01）或把 u 当作秒（速度，02）。
    public static double? FirstEntryIntoCircle(Vec2 p, Vec2 d, Vec2 c, double r)
    {
        Vec2 w = p - c;
        double cc = w.Dot(w) - r * r;
        if (cc <= 0) return 0.0;
        double a = d.Dot(d);
        if (a <= 0) return null;
        double b = 2.0 * d.Dot(w);
        double disc = b * b - 4.0 * a * cc;
        if (disc < 0) return null;
        double u = (-b - Math.Sqrt(disc)) / (2.0 * a);
        return u >= 0 ? u : null;
    }
}
```

- 03 3.0 原有的 `Geo.PointInPolygon` 代码移至此处（03 改为引用）；02 3.1 的文字描述、04 3.5.2 的引用一律改为引用本节；"点在边上未定义"的说法作废。
- 02 `SensingMath.TimeToEnterRadius(p, v, c, r)` 与 01 `ReleaseS` 的内层二次方程改为调用 `FirstEntryIntoCircle`（逐位相同：同一公式、同一运算顺序）。
- `InUrban` 取代 02 3.1 与 03 3.0 的两份 `InUrban`。

### 0.5 项目结构

```
sim/
├─ Sim.csproj                 程序集 Nightwatch.Sim，命名空间根 Nightwatch.Sim
├─ BannedSymbols.txt          禁用 API 清单（6.2）
├─ Core/                      Nightwatch.Sim.Core
│  ├─ SimRandom.cs  IRandom.cs  SplitMix64.cs  Fnv1a64.cs  StreamNames.cs
│  ├─ SimWorld.cs  SimState.cs  SimContext.cs  ISimSystem.cs  SimConfig.cs  SimTime.cs
│  ├─ EntityStore.cs  Entity.cs  EntityKind.cs  IdAllocator.cs  Vec2.cs  Geo.cs  SpatialGrid.cs
│  ├─ StateHasher.cs  SimSnapshot.cs  NightResult.cs  SimJson.cs
│  ├─ Events/                 Nightwatch.Sim.Core.Events：SimEvent.cs、SimEventType.cs、EventSink.cs、核心事件
│  └─ Commands/               Nightwatch.Sim.Core.Commands：SimCommand.cs、SimCommandType.cs、CommandQueue.cs、ICommandHandler.cs
├─ Data/                      Nightwatch.Sim.Data：DataLoader.cs、IDataSource.cs、JsonCursor.cs、DataLoadException.cs、Png16Decoder.cs、DataHash.cs
│  └─ Models/                 Nightwatch.Sim.Data.Models：全部 *Def / LevelData 类型（1.6）
├─ Systems/                   Nightwatch.Sim.Systems：14 个 ISimSystem 实现（每个一个文件，名字见 3.3）
├─ Movement/ Terrain/ Sensing/ Engagement/ Deception/ Infrastructure/ Civil/ Commands/ EnemyAi/ Crew/ Environment/ Rules/
│                             各规格的领域代码（与 WBS 01.D 的输出路径一致；命名空间 = Nightwatch.Sim.<目录名>）
│                             Movement/、Terrain/：01；EnemyAi/：04（EnemyAiHooks、EnemyBelief、EnemyIntelRules、BypassPlanner）与 01 的 EnemyAiQueries；
│                             Commands/：04（CommandStage、DeploymentStage、ChoiceStage、StoryStage、CommandPointRules、DeploymentValidator、DeploymentRules、StoryRules）；
│                             Rules/：跨规格共用的规则取值函数（WeaponParams，见 0.5.1）
├─ Campaign/ Economy/ Save/ Production/ Research/
│                             05 战役层（Campaign/Data 含 CampaignDataLoader）；不被 14 个系统引用
└─ Replay/                    Nightwatch.Sim.Replay：ReplayFile.cs、ReplayRunner.cs

sim.tests/
├─ Sim.Tests.csproj           程序集 Nightwatch.Sim.Tests，命名空间根 Nightwatch.Sim.Tests
├─ Core/                      SimRandomTests、SimTimeTests、GeoTests、EntityStoreTests、SimWorldTests、CommandQueueTests、StateHasherTests
├─ Data/                      DataLoaderTests、PeriodResolveTests、Png16DecoderTests、SampleDataTests
├─ Determinism/               DeterminismTests、ReplayTests（WBS WS01-020：sim.tests/Determinism*）
├─ Architecture/              NoGodotReferenceTests
├─ TestKit/                   ScriptedRandom、MiniLevelBuilder、InMemoryDataSource、RecordingSystem
└─ TestData/                  手写的小型 JSON / PNG 夹具（不依赖正式数值）
```

`sim/Sim.csproj` 必须包含：

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <AssemblyName>Nightwatch.Sim</AssemblyName>
    <RootNamespace>Nightwatch.Sim</RootNamespace>
    <LangVersion>12.0</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>disable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <Deterministic>true</Deterministic>
    <InvariantGlobalization>true</InvariantGlobalization>
    <CheckForOverflowUnderflow>false</CheckForOverflowUnderflow>  <!-- PCG32 / FNV 依赖无符号回绕 -->
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.BannedApiAnalyzers" Version="3.3.4" PrivateAssets="all" />
    <AdditionalFiles Include="BannedSymbols.txt" />
    <InternalsVisibleTo Include="Nightwatch.Sim.Tests" />
  </ItemGroup>
</Project>
```

- 除 `BannedApiAnalyzers`（仅编译期分析器）外，`sim/` **不得有任何 `PackageReference` 或 `ProjectReference`**。只用 .NET 8 基础类库（含 `System.Text.Json`、`System.IO.Compression`、`System.Security.Cryptography`）。
- `sim.tests/Sim.Tests.csproj`：`net8.0`、`IsPackable=false`；包 `Microsoft.NET.Test.Sdk`、`xunit`（2.x）、`xunit.runner.visualstudio`；`<ProjectReference Include="../sim/Sim.csproj" />`；`TestData/**` 设为 `CopyToOutputDirectory=PreserveNewest`。
- 读取正式数据的集成测试通过"从测试程序集目录向上查找含 `AGENTS.md` 的目录"定位仓库根，再读 `data/`。
- **禁止引用 Godot 的检查**（三道）：
  1. `NoGodotReferenceTests`：`typeof(SimWorld).Assembly.GetReferencedAssemblies()` 中没有任何名字以 `Godot` 开头的程序集（`GodotSharp`、`GodotSharpEditor`、`Godot.SourceGenerators`……）。
  2. 同一测试扫描 `sim/**/*.cs` 源文件文本：不得出现正则 `^\s*using\s+Godot\b` 或 `\bGodot\.`。
  3. 同一测试解析 `sim/Sim.csproj`（XML）：`PackageReference` 只允许 `Microsoft.CodeAnalysis.BannedApiAnalyzers`，`ProjectReference` 数量为 0。
- 测试命令：`dotnet test sim.tests`（AGENTS.md 第 5 节）。
- 规格测试向量的参考计算脚本放在仓库 `tools/spec_calc/<规格编号>/`（C-T1-01）；本文件的脚本见第 8 节之后的"附：参考脚本"。

#### 0.5.1 跨规格公共工具登记（全目录唯一实现）

> 下表中的函数 / 类型被多个规格调用；**只能在"拥有者"处实现一次**，其他规格只调用（3.8"同一公式只写一处"）。签名与语义以拥有者规格为准；新增跨规格工具须先在此登记。

| 工具 | 命名空间 / 位置 | 拥有者（规则说明） | 主要调用者 | 来源 |
|---|---|---|---|---|
| `Geo.Normalize` / `BearingRad` / `PointInPolygon` / `InUrban` / `FirstEntryIntoCircle` | `Nightwatch.Sim.Core.Geo` | 00（0.4.6） | 01、02、03、04、06 | P48、A-2-23、A-3-09 |
| `SimTime.SecToTicksCeil` / `SecToTicksFloor` | `Nightwatch.Sim.Core` | 00（0.4.3） | 全部 | — |
| `ThreatGrid` / `TrackGrid`（派生空间索引） | `Nightwatch.Sim.Core.SpatialGrid`；经 `SimContext` 取得 | 00（3.3.1） | 02、03、04 | C-T1-08 |
| `WeaponParams.ReactionSec` / `ShotIntervalSec` / `InterceptorSpeedMps` / `RangeFor` / `LauncherCount` | `Nightwatch.Sim.Rules.WeaponParams`（由 `Nightwatch.Sim.Engagement` 移出） | 03（1.1） | 02（火控开机窗口）、03、04（单位级 `MaxRangeAgainst` 内部调用 `RangeFor`） | A-2-30、A-3-09 |
| `TerrainModel`（高程、视线） | `Nightwatch.Sim.Terrain`；经 `SimContext.Terrain` 取得 | 01（2.5、3.3） | 02、04、06 | P30 |
| `ThreatKinematics.Predict` / `MaxSpeed3DMps` | `Nightwatch.Sim.Movement` | 01（3.2.9） | 03、04 | A-2-02、C-T1-03 |
| `ThreatRouting.Retarget` / `BeginEgress` / `Hover` | `Nightwatch.Sim.Movement` | 01（3.2.8） | 02（电子战后果）、04 | A-2-27 |
| `EnemyAiQueries.AvoidanceActive(SimState, GameCatalog)` | `Nightwatch.Sim.EnemyAi` | 01 | 04 | A-2-10 |
| `IEnemyAiHooks` / `DefaultEnemyAiHooks`（接口 01，正式实现 `EnemyAiHooks` 04） | `Nightwatch.Sim.EnemyAi`；经 `SimContext.EnemyAiHooks` 取得 | 01（接口）/ 04（实现） | 01 | P30、A-2-10 |
| `FireControlQueries.Cued` / `HasFireControlRadar` / `ReactionMult` / `SilentHold` | `Nightwatch.Sim.Sensing` | 02 | 03 | A-2-08 |
| `EmitterQueries.ListActive` | `Nightwatch.Sim.Sensing` | 02 | 04 | A-2-31 |
| `EmissionChoiceEffects.ApplyArmChoice(SimState, int unitId, bool silence)` | `Nightwatch.Sim.Sensing` | 02 | 04（`AnswerChoice`） | A-2-11 |
| `EmissionPolicyRules.CheckAvailable(string unitDefId, EmissionStrategyDef, LevelData)` | `Nightwatch.Sim.Sensing` | 02 | 04（部署校验）、02（命令） | A-2-25 |
| `CoverageQuery`（覆盖查询，线程安全、不读 `SimState`） | `Nightwatch.Sim.Sensing` | 02 | 06 | A-2-16、C-T1-12 |
| `CivilRules.SetAlert(ctx, on, cause)` | `Nightwatch.Sim.Civil` | 03（3.7.2） | 03（命令）、04（剧情 `set_alert`） | A-2-31 |
| `FireUnitFactory.Init` | `Nightwatch.Sim.Engagement` | 03 | 00（`Create` 第 7 步） | P36 |
| `CommandPointRules.CanSpend` / `Spend` / `Refund` / `CostOf` | `Nightwatch.Sim.Commands` | 04（3.6） | 02、03、04 的命令处理者；03 系统 9（退还） | A-2-17 |
| `DeploymentValidator.Validate` / `CheckPlacement`；`DeploymentRules.CheckPosition` | `Nightwatch.Sim.Commands` | 04（3.5） | 00（`Create` 第 7 步）、05、06 | A-2-15 |
| `StoryRules.HasPendingScheduledSpawn(ctx)` | `Nightwatch.Sim.Commands` | 04（3.9） | 00（`AllClear`） | P41 |
| `EnemyIntelRules.BuildCarryOut` | `Nightwatch.Sim.EnemyAi` | 04（3.2.7） | 03（`BuildResult`） | P42 |
| `KnownTargetCarryOps.IsScouted` / `OnUnitRemoved` | `Nightwatch.Sim.Campaign` | 05 | 05 | A-2-18 |

---

## 1. 数据输入

### 1.1 加载入口

```csharp
namespace Nightwatch.Sim.Data;

public interface IDataSource                       // 抽象文件系统，测试用内存实现
{
    bool Exists(string relativePath);              // 相对 data/ 根，正斜杠
    byte[] ReadAllBytes(string relativePath);
}
public sealed class FileSystemDataSource : IDataSource { public FileSystemDataSource(string dataRoot); }
// 测试：sim.tests/TestKit/InMemoryDataSource（Dictionary<string, byte[]>，只做查找）

public static class DataLoader
{
    // 读 level.json 得到关卡日期 → 加载全局目录（按该日期解析随时期变化的数值）→ 加载关卡其余文件 → 交叉引用校验
    // nightIndex：null = 按整关日期 dateRange.from 解析；给定且 waves.json 中该夜有 date 时按该夜日期解析（1.4，B-T2-17）
    public static LevelData LoadLevel(IDataSource source, string levelId, int? nightIndex = null);
    // 只加载全局目录（units / enemies / support / rules），供校验工具使用
    public static GameCatalog LoadCatalog(IDataSource source, GameDate date);
}
```

全局目录的文件**按下表固定顺序**读取（不做目录枚举，避免文件系统顺序差异）。`conventions.json` 最先读取，其后所有文件的换算都使用它。

| 顺序 | 文件 | 顶层数组 / kind | 对应 C# | 细化字段的规格 |
|---|---|---|---|---|
| 1 | `rules/conventions.json` | `kind: conventions` | `ConventionsDef` | 00 |
| 2 | `units/air_defense.json` | `units` | `AirDefenseUnitDef`、`WeaponDef` | 03 |
| 3 | `units/sensors.json` | `sensors` | `SensorDef` | 02 |
| 4 | `units/ew.json` | `ewUnits` | `EwUnitDef` | 02 |
| 5 | `units/deception.json` | `deceptionUnits` | `DeceptionUnitDef` | 02 |
| 6 | `enemies/munitions.json` | `munitions` | `MunitionDef` | 01（移动）、03（伤害） |
| 7 | `enemies/platforms.json` | `platforms` | `PlatformDef` | 01 |
| 8 | `support/fighters.json` | `fighters` | `FighterDef` | 03 |
| 9 | `support/support.json` | `support` | `SupportDef` | 03 |
| 10–20 | `rules/accuracy.json` `damage.json` `intercept.json` `exposure.json` `emission.json` `debris.json` `tracks.json` `ew.json` `positions.json` `support.json` `economy.json` | `kind` 与文件名一致 | 见 1.6 `RulesSet` | 见 1.6 |
| 21 | `rules/movement.json` | `kind: movement` | `MovementRulesDef` | 01 |
| 22 | `rules/terrain.json` | `kind: terrain` | `TerrainRulesDef` | 01 |
| 23 | `rules/engagement.json` | `kind: engagement` | `EngagementRulesDef` | 03 |
| 24 | `rules/civil.json` | `kind: civil` | `CivilRulesDef` | 03 |
| 25 | `rules/enemy_ai.json` | `kind: enemy_ai` | `EnemyAiRulesDef` | 04 |
| 26 | `rules/commands.json` | `kind: commands` | `CommandRulesDef` | 04 |

（21–26 按规格编号、同规格按文中顺序合并编号，A 1.1；`rules.schema.json` 的 `kind` 枚举需追加这 6 个值，见 1.2 第 3 条。新增全局文件只能追加到 26 之后。）

关卡文件（`data/levels/<levelId>/`）：

| 顺序 | 文件 | Schema | 对应 C# |
|---|---|---|---|
| 1 | `level.json` | `level.schema.json` | `LevelMetaDef` |
| 2 | `waves.json` | `waves.schema.json` | `WavesDef` |
| 3 | `intel.json` | `level_content.schema.json`（`kind: intel`） | `IntelDef` |
| 4 | `events.json` | `level_content.schema.json`（`kind: events`） | `StoryEventsDef` |
| 5 | `map/layers.json` | `map.schema.json`（`kind: layers`） | `MapLayersDef` |
| 6 | `map/structures.json` | `map.schema.json`（`kind: structures`） | `IReadOnlyList<StructureDef>` |
| 7 | `map/grid.json` | `map.schema.json`（`kind: grid`） | `GridDef` |
| 8 | `map/deploy.json` | `map.schema.json`（`kind: deploy`） | `DeployDef` |
| 9 | `level.json` 的 `map.heightmap.file`（如 `map/heightmap.png`） | — | `Heightmap` |

- `loc/`、`narrative/`、`schema/` 不由模拟层读取。
- `campaign/`、`rules/campaign.json`（`kind: campaign_rules`）、`levels/<id>/flow.json`（`kind: level_flow`）**不由** `DataLoader.LoadLevel` 读取，由 05 的 `CampaignDataLoader`（`sim/Campaign/Data`）读取，**不计入** `LevelData.LoadedFiles` 与 `DataHash`（P02，05 R-00-6）。`CampaignDataLoader` 复用本节的 `JsonCursor`、1.2 的映射规则与 1.3 的错误格式。
- 日期预读（B-T2-17）：`LoadLevel` 在加载全局目录之前，需要确定解析日期（1.4）。`nightIndex != null` 时，加载器在读完 `level.json` 后**预读** `waves.json` 中 `nights[]` 的 `night` 与 `date` 两个字段以确定日期；`waves.json` 的正式解析与 `LoadedFiles` 记录仍在关卡文件第 2 位（预读不产生错误；`waves.json` 不存在或语法错误时按 `dateRange.from` 解析，错误在正式解析处报告）。

### 1.2 JSON → C# 映射规则

1. **解析器**：`System.Text.Json` 的 `JsonDocument`（`JsonDocumentOptions { AllowTrailingCommas = false, CommentHandling = JsonCommentHandling.Disallow, MaxDepth = 64 }`），由手写映射代码逐字段读取（`JsonCursor` 辅助类跟踪 JSON 路径）。**不使用** `JsonSerializer` 反序列化数据模型（无法给出精确路径、无法在加载时换算单位）。`JsonSerializer` 只用于 `SimConfig`、命令、`NightResult`、回放文件（3.9）。
2. **忽略的字段**（任何层级）：`$schema`、`_source`、`provisional`。`provisional` 的键（字段路径）收集进 `LevelData.ProvisionalPaths`（格式 `<文件>#<provisional 的键>`，供工具提示），模拟不读。
3. **`kind` 字段**：Schema 要求 `kind` 的文件（`rules/*`、`intel.json` / `events.json`（`level_content`）、`map/*`、05 的 `campaign/*` 与 `flow.json`）读取并校验等于该文件期望的值，否则 `E_KIND`；`level.json`、`waves.json`、`units/*`、`enemies/*`、`support/*` 没有 `kind` 字段，不校验（出现即 `E_UNKNOWN_FIELD`）（P03，A-2-24）。`rules.schema.json` 的 `kind` 枚举须含 `movement`、`terrain`、`engagement`、`civil`、`enemy_ai`、`commands`、`campaign_rules`；`level_flow` 用独立的 `level_flow.schema.json`。
4. **未知字段** → `E_UNKNOWN_FIELD`（Schema 均为 `additionalProperties: false`，加载器同样严格，以便尽早发现拼写错误）。
5. **必填字段**以对应 Schema 的 `required` 为准；缺失 → `E_MISSING_FIELD`。
6. **可选字段缺失** → C# 中为 `null`（值类型用 `T?`，集合用 `null` 而不是空集合）。**加载器不填默认值**；默认值由使用该字段的规格在第 1 节写明，并在系统代码中通过具名常量之外的方式（即读数据或写明"缺省 = 不生效"）处理。
7. **数值**：JSON number → `double`（`JsonElement.GetDouble()`，与区域设置无关）。Schema 为 `integer` 的字段用 `TryGetInt32`，失败（小数或越界）→ `E_TYPE`。
8. **字符串枚举 → C# enum**：JSON 值全为大写（如 `UAV`、`JET_UAV`、`A`、`AB`）时 C# 成员名与 JSON 完全相同；否则 `snake_case` → `PascalCase`（按 `_` 拆分、每段首字母大写、其余小写：`power_plant` → `PowerPlant`，`offmap_call` → `OffmapCall`，`very_low` → `VeryLow`）。enum 的整数值按 Schema `enum` 数组顺序从 0 开始**显式写出**（参与哈希，不得重排；新增值只能追加）。未知字符串 → `E_ENUM`。
9. **数据 ID**（`common.id`）保持 `string`，字段名 `…Id`（JSON `enemy` → `EnemyId`，`entry` → `EntryId`，`structure` → `StructureId`，`gridNode` → `GridNodeId`，`unit` → `UnitId`，`weapon` → `WeaponId`，`wave` → `WaveId`，`ref` → `RefId`）。
10. **坐标**：`pointM` → `Vec2`；`polylineM` / `polygonM` → `IReadOnlyList<Vec2>`；字段名 `positionM` → `Pos`，`pathM` → `Path`，`polygonM` → `Polygon`，`waypointsM` → `Waypoints`。
11. **`minMax`** → `MinMax`（`readonly record struct MinMax(double Min, double Max)`），按后缀换算两个值；`Min > Max` → `E_RANGE`。
12. **日期**：`date`（`YYYY-MM-DD`）→ `GameDate`；`yearMonth`（`YYYY-MM`）→ `YearMonth`。格式不符 → `E_FORMAT`。
13. **ID 唯一性**：同一文件同一数组内 ID 重复 → `E_DUPLICATE_ID`。**单位 ID 在 `units/*.json` 四个文件之间也必须唯一**（部署方案只给单位 ID，需据此判断实体类型）。敌方 ID 在 `munitions` 与 `platforms` 之间必须唯一。战斗机武器 ID（`fighters[].weapons[].id`）与防空武器 ID 不得重复（P04）。
14. **共享武器**：同一 `weapons[].id` 出现在多个单位中时，各处的 JSON 子树必须逐字段相等（忽略键顺序，数值按 `double` 比较），否则 `E_SHARED_WEAPON_MISMATCH`。`GameCatalog.Weapons` 中每个武器 ID 只保留一个 `WeaponDef`。
15. **交叉引用校验**（加载器负责，全部 → `E_UNKNOWN_REF`）：`availableUnits[].unit` ∈ 单位 ID；`ammoQuota[].weapon` ∈ 武器 ID；`waves` 的 `groups[].enemy` ∈ 敌方 ID、`groups[].entry` ∈ `entryPoints[].id`、`target.structure` ∈ 保护目标 ID；`structures[].gridNode` ∈ 电网节点 ID；`links[].from/to` ∈ 电网节点 ID；`weapons[].interceptClass` ∈ `intercept.classes` 的键；`restrictToEnemies[]` ∈ 敌方 ID；`victory/defeat[].structure` ∈ 保护目标 ID；`events` 中 `ref`、`wave` 指向存在的对象；`intel` 的 `relatedWave` ∈ 波次 ID。追加（P05）：`platforms[].loadout[].options[]` ∈ 弹药 ID（`敌方单位`）；`ewUnits[].effectiveAgainst[]` / `ineffectiveAgainst[]`、`sensors[].trackQualityUpgrades[].enemies[]` ∈ 敌方 ID（`敌方单位`）；`support[].affectsSameAsEwUnit` ∈ 电子战单位 ID（`单位`）；`support[].fighterRef` ∈ 战斗机 ID（`战斗机`）；`support[].fighterWeaponRef` ∈ 该战斗机的武器 ID（`武器`）；`support[].reinforcementUnit`、`coverageUnits[]` ∈ 防空单位 ID（`单位`）；`fighters[].weapons[].interceptClass` ∈ `intercept.classes`（`拦截类别`）；`emission.defaultStrategy` ∈ `strategies[].id`（`辐射策略`）；`events.json` 的 `unit_destroyed.ref` ∈ 单位 ID（`单位`）、`structure_destroyed.ref` ∈ 保护目标 ID（`保护目标`）、`wave_spawned.ref` / `spawn_wave.wave` ∈ 任一夜的波次 ID（`波次`）。其他规格可在本表追加（括号内为 1.3 的 `{类别}`）。
16. **所有错误收集后一次性抛出**（不在第一个错误处停止），按"文件读取顺序 → 文件内出现顺序"排列。
17. **规格追加校验**（索引；正文与错误码在各规格，均在 `LoadLevel` 中执行，按本条顺序、在第 15 条之后进行）（P06）：
    - 01：V1（`movement` / `terrain` 规则范围）、V2（波次不得直接使用 `carrier` 弹药；非 carrier 弹药速度 > 0）、V3（平台高度带与速度）（01 8.2）；
    - 02：H5、H7（02 8.2）；`tracks.cueing.uncued.firstShotReactionTimeMult` 与 `intercept.modifiers.noCueSelfSearch.firstShotReactionTimeMult` 相等（A-2-08）；
    - 03：`damage.bands` 覆盖伤害等级 1–10 且不重叠；`victory` / `defeat` 条件类型限制；`intercept.modifiers.restrictedEngagement` 为限制交战反应倍率的唯一来源（B-T1-11 删除 `support.airspace…reactionTimeMult` 之前，两处必须相等）；
    - 04：1.1.1 的范围检查、`commandPointCosts` 键规则、`commandPointsPerNight ∈ economy` 范围、`events.json` 动作 / 触发器必填字段（04 1.4）。
    - 只产生警告、不阻止加载的检查不在加载器中，统一由 `tools/validate` 列出（07 §2，C-T1-11）。
18. **00 自身的跨文件检查**：
    - 胜利条件 `survive_game_sec` 的 `gameSec` ≤ `waves.json` 各夜 `durationGameSec` 之和，否则 `E_RANGE`（`取值 {gameSec} 超出范围 各夜时长之和 {和}`）；夜内时长只以 `durationGameSec` 为准，`survive_game_sec` 由关卡层（05）判定（B-T2-19）。
    - `waves.json` 的 `nights[].date`（可选）必须落在 `level.json` 的 `[dateRange.from, dateRange.to]` 内，否则 `E_RANGE`（B-T2-17）。

### 1.3 错误信息格式

```csharp
public sealed class DataLoadException : Exception
{
    public IReadOnlyList<DataError> Errors { get; }   // Message = 全部 Errors.ToString() 以 '\n' 连接
}
public sealed record DataError(string Code, string File, string JsonPath, string Detail)
{
    public override string ToString() => $"[{Code}] {File} {JsonPath}: {Detail}";
}
```

- `File`：相对 `data/` 的路径，正斜杠，例如 `units/air_defense.json`、`levels/test_01/map/grid.json`。
- `JsonPath`：从 `$` 开始，属性用 `.name`，数组下标用 `[i]`（从 0 开始）。例：`$.units[3].weapons[0].rangeKm`。文件级错误用 `$`。
- `Detail`：中文说明，格式固定如下表（`{}` 为占位）：

| Code | 何时 | Detail 格式 |
|---|---|---|
| `E_FILE_NOT_FOUND` | 文件不存在 | `文件不存在` |
| `E_JSON_SYNTAX` | JSON 语法错误 | `JSON 语法错误（第 {行} 行，第 {列} 列）：{JsonException.Message}`（行列从 1 开始） |
| `E_MISSING_FIELD` | 缺少必填字段 | `缺少必填字段` |
| `E_UNKNOWN_FIELD` | 多余字段 | `未知字段` |
| `E_TYPE` | 类型不符 | `期望 {类型}，实际 {类型}`；`{类型}` ∈ number / integer / string / boolean / object / array / null |
| `E_ENUM` | 枚举值不合法 | `非法取值 "{值}"，允许：{逗号分隔的允许值}` |
| `E_FORMAT` | 日期 / ID / 本地化键格式不符 | `格式错误 "{值}"，期望 {格式}`；`{格式}` ∈ YYYY-MM / YYYY-MM-DD / id / locKey |
| `E_RANGE` | 超出 Schema 的 minimum / maximum，或 `Min > Max` | `取值 {值} 超出范围 {说明}` |
| `E_KIND` | `kind` 不符 | `kind 应为 "{期望}"，实际 "{值}"` |
| `E_DUPLICATE_ID` | ID 重复 | `ID "{id}" 重复（首次出现于 {文件} {路径}）` |
| `E_UNKNOWN_REF` | 引用不存在 | `引用的 {类别} "{id}" 不存在` |
| `E_SHARED_WEAPON_MISMATCH` | 共享武器定义不一致 | `共享武器 "{id}" 与 {文件} {路径} 的定义不一致` |
| `E_PERIOD_ORDER` | 时期数组 `from` 未严格升序 | `时期数组的 from 必须严格升序` |
| `E_PERIOD_BEFORE_FIRST` | 关卡日期早于时期数组第一项且无基准值 | `关卡日期 {YYYY-MM-DD} 早于第一个时期 {YYYY-MM}` |
| `E_PNG_FORMAT` | 高程图格式不支持 | `高程图必须是 16 位灰度、非隔行 PNG：{原因}` |
| `E_NIGHT_NOT_FOUND` | （`SimWorld.Create` 时）夜晚序号不存在 | `waves.json 中没有第 {n} 夜` |
| `E_NIGHT_DATE_MISMATCH` | （`SimWorld.Create` 时）`LevelData` 的解析日期不是该夜应使用的日期（1.4） | `第 {n} 夜应按 {YYYY-MM-DD} 解析，LevelData 按 {YYYY-MM-DD} 加载` |
| `E_NOT_IMPLEMENTED` | （`SimWorld.Create` 时）数据或 `CarryIn` 用到了尚未实现的功能 | `{功能}尚未实现（{任务号}）`（01 4.3 的格式为其实例；P07） |

例（精确字符串，测试会逐字比较）：

```
[E_MISSING_FIELD] units/air_defense.json $.units[0].weapons[0].rangeKm: 缺少必填字段
[E_TYPE] units/air_defense.json $.units[0].weapons[0].rangeKm: 期望 number，实际 string
[E_UNKNOWN_REF] levels/mini/waves.json $.nights[0].waves[0].groups[0].enemy: 引用的 敌方单位 "nope" 不存在
```

`E_UNKNOWN_REF` 的 `{类别}` 取值：`单位`、`武器`、`敌方单位`、`进入点`、`保护目标`、`电网节点`、`拦截类别`、`波次`、`战斗机`、`辐射策略`（P08）。

`SimSetupException`（`SimWorld.Create` 阶段的错误）的消息使用同一 `[Code] File JsonPath: Detail` 格式；没有对应文件位置时 `File` 写 `levels/<id>/level.json`、`JsonPath` 写 `$`。

### 1.4 随时期变化的数值（按关卡日期解析）

**关卡日期** `LevelData.Date`：`LoadLevel(source, levelId, nightIndex)` 中，若 `nightIndex != null` 且 `waves.json` 中 `night == nightIndex` 的一项给出了可选字段 `date`，则 = 该 `date`；否则 = `level.json` 的 `dateRange.from`（`GameDate`）。比较时只取其年月 `Date.ToYearMonth()`。`LevelData.ResolvedNightIndex` 记录按哪一夜加载（`null` = 整关）。多夜关卡缺省整关使用 `dateRange.from`；需要某夜不同时，由关卡作者给该夜写 `date`（B-T2-17，原待决问题 Q1；`waves.schema.json` 的 `nights[]` 追加可选 `date`）。`SimWorld.Create` 检查日期一致性（3.2 第 2 步）。

解析**在加载时完成**：`LevelData` / `GameCatalog` 中只有解析后的普通值，系统代码看不到时期数组。三种形态：

| 形态 | 出现位置 | 解析规则 | 关卡日期早于第一项时 |
|---|---|---|---|
| A. `periodValue`（数字，或 `[{from, value}]`） | `rules/intercept.json` 的 `classes.<类>.<标签>` | 数字 → 原值；数组 → 取 `from ≤ 关卡年月` 的**最后一项**的 `value` | `E_PERIOD_BEFORE_FIRST` |
| B. 时期表（`[{from, …}]`，每项是一组字段） | `rules/ew.json` 的 `effectivenessByPeriod`；`munitions[].accuracyByPeriod` | 同上，取整行 | `ew`：`E_PERIOD_BEFORE_FIRST`；`accuracyByPeriod`：使用基准字段 `accuracy` |
| C. 生效闸门（单个 `from` / `until`） | `weapons[].targetsFrom[]`；`intercept.modifiers.<名>.from`；`platforms[].standoffFrom`；`munitions[].aiVisionFrom`；`economy.historicalEvents[].from/until` | `Active = (from 缺省 或 关卡年月 ≥ from) 且 (until 缺省 或 关卡年月 < until)` | 不适用（`Active = false`） |

- 数组必须按 `from` **严格升序**，否则 `E_PERIOD_ORDER`。
- `YearMonth` 比较：先年后月，整数比较。`"2025-08"` 表示 2025 年 8 月 1 日起生效：关卡日期 `2025-07-31` → 不生效，`2025-08-01` → 生效。
- 形态 C 的解析结果：`targetsFrom` 中 `Active` 的标签**并入** `WeaponDef.Targets`（并去重，顺序 = 原 `targets` 后接按数据顺序追加的新标签）；`modifiers` 解析为 `InterceptModifierDef.Active`；`standoffFrom` 解析为 `PlatformDef.StandoffActive`；`aiVisionFrom` 解析为 `MunitionDef.AiVisionActive`（缺省字段 = `false`，02 B-T3-08）；`historicalEvents` 解析为 `HistoricalEventDef.Active`。
- 敌方定义的可选字段 `firstSeen`（年月，C-T2-08）**不是**闸门：加载器原样保留为 `YearMonth? FirstSeen`，只供 `tools/validate` 的时间线检查使用，模拟不读。
- `until` 取"不含该月"语义，依据是 `economy.json` `_source`："2023.04 之前申请不到 Patriot"。
- `firstAvailable.level` 是战役层闸门（05），不是日期，加载时原样保留。

### 1.5 `LevelData` 的组成

`LevelData` 是 `SimWorld.Create` 需要的**全部**数据：全局目录（已按关卡日期解析）+ 关卡 8 个文件 + 高程图 + 数据哈希。加载后**不可变**（全部属性只读、集合为 `IReadOnlyList`），可在多个 `SimWorld` 之间共享。

高程图：

- 必须是 PNG、颜色类型 0（灰度）、位深 16、非隔行；否则 `E_PNG_FORMAT`。解码用自带的最小 PNG 解码器 `Png16Decoder`（`System.IO.Compression.ZLibStream` 解压 `IDAT`，支持 5 种行过滤器 None/Sub/Up/Average/Paeth，忽略辅助块，校验 `IHDR`，不校验 CRC）。
- 像素值大端 16 位 `g ∈ [0, 65535]`；海拔 `ElevationM = minElevationM + (g / 65535.0) × (maxElevationM − minElevationM)`（按此顺序计算）。
- 存储：`double[] ElevationM`，**行主序，第 0 行 = 图像最上一行 = 北边**，索引 `row × WidthPx + col`。世界坐标映射、双线性插值、视线由 01 规定。
- 校验：`WidthPx × metersPerPixel` 与 `map.widthM`、`HeightPx × metersPerPixel` 与 `map.heightM` 之差的绝对值 ≤ `metersPerPixel`，否则 `E_RANGE`。

### 1.6 C# 数据模型清单（签名，不含实现）

> 所有类型为 `sealed record`（或 `readonly record struct`），属性 `{ get; init; }`。下表只列到"其他规格需要知道的层级"；标注"→ 0x"的类型由该规格第 1 节列全字段，命名必须遵守 1.2 与 0.4.2。

```csharp
namespace Nightwatch.Sim.Data.Models;

// ---- 公共 ----
public readonly record struct YearMonth(int Year, int Month) : IComparable<YearMonth>;
public readonly record struct GameDate(int Year, int Month, int Day) : IComparable<GameDate>
{ public YearMonth ToYearMonth(); }
public readonly record struct MinMax(double Min, double Max);
public enum TargetTag { UAV = 0, JET_UAV = 1, DECOY = 2, CM = 3, SCM = 4, BM = 5, HBM = 6, GB = 7, HELI = 8, AC_LOW = 9, AC_HIGH = 10 }
public enum AccuracyTier { A = 0, B = 1, C = 2, D = 3 }
public enum TrackQuality { Vague = 0, Approximate = 1, Precise = 2 }   // 数值越大质量越高（JSON: vague / approximate / precise）

// ---- 顶层 ----
public sealed record GameCatalog
{
    public ConventionsDef Conventions { get; init; }
    public IReadOnlyList<AirDefenseUnitDef> AirDefenseUnits { get; init; }   // 数据顺序
    public IReadOnlyList<WeaponDef> Weapons { get; init; }                   // 去重后，按首次出现顺序
    public IReadOnlyList<SensorDef> Sensors { get; init; }
    public IReadOnlyList<EwUnitDef> EwUnits { get; init; }
    public IReadOnlyList<DeceptionUnitDef> DeceptionUnits { get; init; }
    public IReadOnlyList<MunitionDef> Munitions { get; init; }
    public IReadOnlyList<PlatformDef> Platforms { get; init; }
    public IReadOnlyList<FighterDef> Fighters { get; init; }
    public IReadOnlyList<SupportDef> Support { get; init; }
    public RulesSet Rules { get; init; }
    public GameDate ResolvedForDate { get; init; }
    // 按 ID 查找（内部用有序数组 + 二分，或 Dictionary 仅作查找；不得遍历 Dictionary）
    public AirDefenseUnitDef GetAirDefenseUnit(string id);  /* 其余 Get… 同理；找不到抛 KeyNotFoundException */
    public PlayerUnitCategory GetPlayerUnitCategory(string unitId);   // Fire / Sensor / Ew / Deception
}
public enum PlayerUnitCategory { Fire = 0, Sensor = 1, Ew = 2, Deception = 3 }
// 凡类型为 PlayerUnitCategory 的字段（事件、记录、视图）一律命名 Category，不叫 Kind（A-3-05）

public sealed record LevelData
{
    public string Id { get; init; }
    public GameDate Date { get; init; }                      // 解析日期（1.4）：该夜 date ?? Meta.DateFrom
    public int? ResolvedNightIndex { get; init; }            // LoadLevel 的 nightIndex 参数（null = 整关，1.4）
    public LevelMetaDef Meta { get; init; }
    public WavesDef Waves { get; init; }
    public IntelDef Intel { get; init; }
    public StoryEventsDef StoryEvents { get; init; }
    public MapLayersDef Layers { get; init; }
    public IReadOnlyList<StructureDef> Structures { get; init; }
    public GridDef Grid { get; init; }
    public DeployDef Deploy { get; init; }
    public Heightmap Heightmap { get; init; }
    public GameCatalog Catalog { get; init; }
    public string DataHash { get; init; }                    // "sha256:<64 位小写十六进制>"（3.9.2）
    public IReadOnlyList<string> LoadedFiles { get; init; }  // 相对 data/ 的路径，按读取顺序
    public IReadOnlyList<string> ProvisionalPaths { get; init; }
}

// ---- conventions（00）----
public sealed record ConventionsDef(double GameSecToWorldSec, double WorldStepSec, double CellKm, double MachKmh, string Currency);

// ---- level.json ----
public enum Protagonist { A = 0, B = 1, AB = 2 }
public enum TimeStructure { A = 0, B = 1, C = 2, D = 3, E = 4 }
public enum FighterMode { None = 0, OffmapAuto = 1, OffmapCall = 2, OnmapAirbase = 3, OnmapSupportFacility = 4 }
public enum UnitSource { Quota = 0, City = 1, Stock = 2 }
public enum ConditionType { SurviveNights = 0, SurviveGameSec = 1, StructureDestroyed = 2, WeightedDamageAtLeast = 3, GridCollapse = 4 }
public sealed record LevelMetaDef
{
    public string Id; public int? Number; public string NameKey; public string? BriefingKey;
    public Protagonist Protagonist; public GameDate DateFrom; public GameDate DateTo;
    public TimeStructure TimeStructure; public FighterMode FighterMode; public int? FighterSortiesPerNight;
    public int Nights; public MapInfoDef Map;
    public IReadOnlyList<AvailableUnitDef> AvailableUnits; public IReadOnlyList<AmmoQuotaDef>? AmmoQuota;
    public int CommandPointsPerNight; public double? CityResourcePerDay;
    public IReadOnlyList<ConditionDef> Victory; public IReadOnlyList<ConditionDef> Defeat;
    // 追加（字段结构由所属规格第 1 节给出）：LauncherOverrides（→ 03，B-T2-57）；SectorCoverageAnchors（→ 05 / 03，B-T2-89）
}   // （示意：实际为 init 属性）
public sealed record MapInfoDef(double WidthM, double HeightM, HeightmapInfoDef Heightmap, IReadOnlyList<string>? Attribution);
public sealed record HeightmapInfoDef(string File, double MetersPerPixel, double MinElevationM, double MaxElevationM);
public sealed record AvailableUnitDef(string UnitId, int Count, UnitSource? Source);
public sealed record AmmoQuotaDef(string WeaponId, int Count);
public sealed record ConditionDef(ConditionType Type, int? Nights, double? Sec, string? StructureId, double? Fraction);  // JSON gameSec → Sec；grid_collapse 的 Fraction 缺省 1.0（03，B-T2-79）

// ---- waves.json（→ 01）----
public enum AiTag { Probe = 0, Suppress = 1, Hunt = 2, Bypass = 3, Saturate = 4 }
public enum Weather { Clear = 0, Moonlit = 1, LowCloud = 2, Fog = 3 }
public enum Season { Spring = 0, Summer = 1, Autumn = 2, Winter = 3 }
public enum TimeOfDay { Night = 0, Day = 1 }                       // 05 R-01-2；缺省 Night（B-T2-45）
public enum RouteKind { Template = 0, Waypoints = 1, Direct = 2 }
public enum TargetMode { WeightedRandom = 0, KnownTargets = 1, AirDefense = 2, DecoyFlight = 3 }
public sealed record WavesDef(IReadOnlyList<EntryPointDef> EntryPoints, IReadOnlyList<NightDef> Nights);
public sealed record EntryPointDef(string Id, string? NameKey, Vec2 Pos, double? WarningSec);
public sealed record NightDef(int Night, double DurationSec, Weather? Weather, Season? Season, IReadOnlyList<WaveDef> Waves,
    GameDate? Date,                 // 可选：该夜的解析日期（1.4，B-T2-17）
    bool? BigRaid,                  // 可选：大空袭夜（03 Q-S8，B-T2-88）
    TimeOfDay? TimeOfDay);          // 可选：缺省 Night（05 R-01-2）
public sealed record WaveDef(string Id, double AtSec, IReadOnlyList<AiTag>? AiTags, IReadOnlyList<WaveGroupDef> Groups,
    string? AdaptiveTrigger);       // 可选：敌人适应（05 3.12，B-T2-112；WS05-006）
public sealed record WaveGroupDef(string EnemyId, int Count, string EntryId, double? SpacingSec, RouteDef Route, TargetSpecDef Target,
    string? AdaptiveTrigger, IReadOnlyList<AdaptiveSubstituteDef>? AdaptiveSubstitutes);   // 可选，字段 → 05（WS05-006）
public sealed record RouteDef(RouteKind Kind, string? TemplateId, IReadOnlyList<Vec2>? Waypoints);
public sealed record TargetSpecDef(string? StructureId, TargetMode? Mode);   // 二者恰有一个非 null

// ---- intel.json / events.json（→ 04）----
public sealed record IntelDef(IReadOnlyList<IntelNightDef> Nights);
public sealed record IntelNightDef(int Night, IReadOnlyList<IntelItemDef> Items);
public sealed record IntelItemDef(string TextKey, bool Accurate, string? RelatedWaveId);
public enum StoryTriggerType { NightStart = 0, AtGameSec = 1, StructureDestroyed = 2, UnitDestroyed = 3, WaveSpawned = 4 }
public enum StoryActionType { Dialogue = 0, SpawnWave = 1, Choice = 2, SetAlert = 3 }
public sealed record StoryEventsDef(IReadOnlyList<StoryEventDef> Events);
public sealed record StoryEventDef(string Id, StoryTriggerDef Trigger, IReadOnlyList<StoryActionDef> Actions);
public sealed record StoryTriggerDef(StoryTriggerType Type, int? Night, double? Sec, string? RefId);
public sealed record StoryActionDef(StoryActionType Type, string? DialogueKey, string? WaveId, string? ChoiceKey, double? TimeoutSec, int? DefaultOption);

// ---- map/*.json ----
public sealed record MapLayersDef(IReadOnlyList<RiverDef> Rivers, IReadOnlyList<RoadDef> Roads, IReadOnlyList<BridgeDef> Bridges,
    IReadOnlyList<UrbanAreaDef> Urban, IReadOnlyList<ForestDef> Forests, IReadOnlyList<BorderDef> Borders,
    IReadOnlyList<RestrictedZoneDef> RestrictedZones);                                   // 字段 → 01（地形）/ 03（碎片、约束区）
public sealed record RiverDef(string Id, string? NameKey, IReadOnlyList<Vec2> Path, double WidthM);
public sealed record RoadDef(string Id, IReadOnlyList<Vec2> Path, RoadClass Class);      // enum RoadClass { Highway, Main, Local }
public sealed record BridgeDef(string Id, IReadOnlyList<Vec2> Path, string? RoadId, bool? Destructible);
public sealed record UrbanAreaDef(string Id, IReadOnlyList<Vec2> Polygon, UrbanDensity Density);  // enum UrbanDensity { Core, Dense, Suburban }
public sealed record ForestDef(string Id, IReadOnlyList<Vec2> Polygon);
public sealed record BorderDef(string Id, IReadOnlyList<Vec2> Path, BorderKind Kind);    // enum BorderKind { Oblast, National, Frontline }
public sealed record RestrictedZoneDef(string Id, IReadOnlyList<Vec2> Polygon, ZoneRule Rule, ZoneReason? Reason);
    // enum ZoneRule { NoEngagement = 0, RestrictedEngagement = 1, FrontlineRisk = 2, NeighborCountry = 3 }; enum ZoneReason { Border, NuclearPlant, CivilCorridor, Frontline }
    // NeighborCountry（JSON neighbor_country）：多边形 = 邻国领土，用于越界计数（03，C-T2-03）；Schema 枚举追加
public sealed record StructureDef(string Id, string NameKey, StructureType Type, Vec2 Pos, double RadiusM, double Weight, int Hp, string? GridNodeId);
    // enum StructureType { PowerPlant, Substation, CommandPost, Factory, Residential, Port, Shipyard, WaterPlant, Hospital, Shelter, AirbaseRunway, AirbaseHangar, RepairPlant, Bridge }
public sealed record GridDef(IReadOnlyList<GridNodeDef> Nodes, IReadOnlyList<GridLinkDef> Links);   // → 03
public sealed record GridNodeDef(string Id, GridNodeType Type, Vec2 Pos, bool? OffMapSupply);       // enum GridNodeType { Source, Substation, Consumer }
public sealed record GridLinkDef(string FromId, string ToId);
public sealed record DeployDef(IReadOnlyList<DeployZoneDef> Zones, IReadOnlyList<ForbiddenZoneDef> Forbidden, IReadOnlyList<AlternatePositionDef> AlternatePositions);  // → 04
public sealed record DeployZoneDef(string Id, IReadOnlyList<Vec2> Polygon, IReadOnlyList<Mobility>? AllowedMobility);
public sealed record ForbiddenZoneDef(string Id, IReadOnlyList<Vec2> Polygon, ForbiddenReason Reason); // enum ForbiddenReason { Water, UrbanCore, Frontline, Other }
public sealed record AlternatePositionDef(string Id, Vec2 Pos, bool Surveyed);
public sealed record Heightmap(int WidthPx, int HeightPx, double MetersPerPixel, double MinElevationM, double MaxElevationM, IReadOnlyList<double> ElevationM)
{
    internal double[] ElevationArray { get; }   // 内部存储（1.5）；ElevationM 是它的只读包装。01 的 TerrainModel 零复制引用它（P14）
}

// ---- 我方单位（全字段见 03 1.1、02 1.1–1.4）----
public enum Mobility { Vehicle = 0, Towed = 1, Portable = 2, Fixed = 3 }
public enum DeployTier { Instant = 0, Minutes = 1, HoursShort = 2, Hours = 3, Fixed = 4 }          // 04（P15）
public enum FireOnMove { Yes = 0, Partial = 1, No = 2 }                                            // 02 / 03（B-T2-62）
public enum SelfAcquisitionKind { Optical = 0 }                                                    // 02（B-T2-09：光学自主捕获受夜间 / 天气倍率）
public sealed record FirstAvailableDef(int? Level, int? FullStrengthLevel, bool? Optional, bool? InfoSourceOnly);   // P17
public sealed record AirDefenseUnitDef        // → 03（交战）、02（火控 / 自主捕获）、04（部署状态机）；不含单位级 ReactionSec（反应时间挂武器，B-T2-01）
{
    public string Id; public string NameKey; public DeployTier DeployTier;
    public double? DeploySec; public double? PackSec;            // deployGameSec / packGameSec × 60
    public Mobility Mobility; public double? MoveSpeedMps; public FireOnMove FireOnMove;
    public double? SystemPriceMusd; public bool? StockOnly; public IReadOnlyList<string> WeaponIds;
    public FireControlRadarDef? FireControlRadar;                // → 02 1.4（RangeM, LowAltitude, Origin, AntennaHeightM）
    public double? SelfAcquisitionRangeM;                        // → 02 1.4（selfAcquisitionRangeKm）
    public SelfAcquisitionKind? SelfAcquisition;                 // → 02（selfAcquisition，B-T2-09）
    public FirstAvailableDef? FirstAvailable;
}
public sealed record WeaponDef                // → 03 1.1（WeaponKind / AmmoSupply 枚举值按 03 R-DATA）
{
    public string Id; public string NameKey; public WeaponKind Kind; public string InterceptClass;
    public double RangeM; public IReadOnlyDictionary<TargetTag, double>? RangeByTagM;   // 只查找，不遍历；需要遍历时按 TargetTag 升序
    public double CeilingM; public double? ShotCostMusd; public int? Magazine; public int? MagazineRounds;
    public int? Launchers; public int? PerLevelLimit; public AmmoSupply AmmoSupply;
    public IReadOnlyList<TargetTag> Targets;   // 已并入 Active 的 targetsFrom（1.4）
    public IReadOnlyList<TargetTag>? LowEfficiencyTargets; public IReadOnlyList<string>? RestrictToEnemies; public bool? BarrelCooldown;
    public double? ReactionSec;                // reactionGameSec × 60（可选，缺省按 InterceptClass 查 EngagementRulesDef，B-T2-01 / P16）
    public double? ShotIntervalSec;            // shotIntervalGameSec × 60（可选，P16）
    public double? InterceptorSpeedMps;        // interceptorSpeedKmh ÷ 3.6（可选，Gun 不得填写，B-T2-55 / P16）
}
public sealed record SensorDef { /* 全字段见 02 1.1；含 bool? LineOfSight（缺省 true，acoustic_post 为 false，B-T2-50）、double? AntennaHeightM（缺省取 Terrain.DefaultAntennaHeightM，B-T2-03）、FirstAvailableDef? FirstAvailable（P17） */ }
public sealed record EwUnitDef { /* 全字段见 02 1.2；radiusKm → RadiusM，offsetCellsAdd → OffsetAddM（0.4.2 第 7 条，仅界面显示，B-T3-08）、FirstAvailableDef? FirstAvailable（P17） */ }
public sealed record DeceptionUnitDef { /* 全字段见 02 1.3；含 FirstAvailableDef? FirstAvailable（P17） */ }

// ---- 敌方与外部支援（→ 01 / 02 / 03）----
public sealed record MunitionDef              // MunitionCategory / AltitudeBand 枚举定义见 01 1.2（P18）
{
    public string Id; public string NameKey; public MunitionCategory Category; public TargetTag? Tag;
    public double? SpeedMps; public bool? DiveFaster; public AltitudeBand AltitudeBand; public MinMax? AltitudeM;
    public bool Interceptable; public int? Hp; // Hp 当前版本不参与拦截判定（命中即毁，B-T3-03），只保留字段
    public double? InterceptProbMult; public int DamageLevel;
    public double? VehicleDamageMult; public double SplashM; public SubmunitionsDef? Submunitions;
    public AccuracyTier Accuracy;              // 已按 accuracyByPeriod 解析（1.4 形态 B）
    public bool? EwImmune; public bool? TracksEmittingRadarOnly; public double? ReleaseRangeM;
    public double? CostMusd;
    public bool? RadioLinked;                  // 02 1.5（无线电链路，B-T2-43）
    public bool AiVisionActive;                // 02 1.5（1.4 形态 C 闸门 aiVisionFrom，缺省 false，B-T3-08 / B-T2-35）
    public bool? StoryEventOnly;               // 01 1.2（仅剧情生成）
    public YearMonth? FirstSeen;               // C-T2-08（仅 tools/validate 时间线检查使用）
}
public sealed record LoadoutEntryDef(IReadOnlyList<string> OptionIds, int? Count);                 // Count 为 null 时按 1 枚（01，B-T2-25）
public sealed record PlatformWhileAliveDef(int? EnemyAccuracyTierBoost, bool? CruiseMissilesAvoidAirDefense); // B-T2-14：升档数只读 accuracy.spotterTierBoost
public enum OtherArmament { Atgm = 0, Rockets = 1, UnguidedBombs = 2, LongRangeAam = 3, SmallGuidedBombs = 4 }
public enum PlatformBehavior { FrontlineAttack = 0, MustEnterShorad = 1, LowStrike = 2, StandoffReleaseAndReturn = 3,
                               HuntFightersAndRadars = 4, LaunchFromMapEdge = 5, GlobalAlertOnTakeoff = 6, WaveSourceOnly = 7,
                               ArmedRecon = 8, Spotter = 9, Awacs = 10 }
public enum ReconQuality { Low = 0, Medium = 1, High = 2 }                                         // 02 1.5（B-T2-41）
public sealed record PlatformDef              // 01 1.3 + 02 1.5（P19）
{
    public string Id; public string NameKey; public TargetTag? Tag;
    public double CruiseSpeedMps; public double? MaxSpeedMps;                                      // MaxSpeedMps 保留不用（B-T2-26）
    public AltitudeBand AltitudeBand; public int? Hp; public bool EntersMap;
    public IReadOnlyList<LoadoutEntryDef>? Loadout; public IReadOnlyList<OtherArmament>? OtherArmament;
    public PlatformBehavior Behavior; public bool StandoffActive;                                  // standoffFrom 形态 C
    public PlatformWhileAliveDef? WhileAlive;
    public double? ReleaseRangeM;              // releaseRangeKm × 1000（可选，飞到距目标此距离再投放并返航；null = 停留 0 秒，01 B-T3-09）
    public bool? RadioLinked;                  // 02 1.5（B-T2-43）
    public ReconQuality? ReconQuality;         // 02 1.5（假发射车识破，B-T2-41）
    public YearMonth? FirstSeen;               // C-T2-08
}
public sealed record FighterDef { /* 全字段见 03 1.2；FighterWeaponDef.Kind 必填（Missile / Rocket）（P20） */ }
public sealed record SupportDef { /* 全字段见 03 1.3；含 double? RadiusM（radiusKm，02 B-T2-04）、int? AccuracyTierDrop、string? AffectsSameAsEwUnitId（P20） */ }

// ---- rules/*.json（属性名严格遵守 1.2 与 0.4.2 的机械映射，A-3-02）----
public sealed record RulesSet
{
    public ConventionsDef Conventions;         // 00（rules/conventions.json）
    public AccuracyRulesDef Accuracy;          // → 03
    public DamageRulesDef Damage;              // → 03
    public InterceptRulesDef Intercept;        // → 03（classes 已解析为 double；modifiers 带 Active）
    public ExposureRulesDef Exposure;          // → 02
    public EmissionRulesDef Emission;          // → 02
    public DebrisRulesDef Debris;              // → 03
    public TrackRulesDef Tracks;               // → 02（detectionRules 块见 A-3-06）
    public EwRulesDef Ew;                      // → 02（effectivenessByPeriod 已解析为单行 EwEffectivenessDef）
    public PositionRulesDef Positions;         // → 04（02 读 newUnsurveyed 与新增 deception 块，P12）
    public SupportRulesDef Support;            // → 03
    public EconomyRulesDef Economy;            // → 05（historicalEvents 带 Active；追加 Trust、Exchange、CrossLevelModClamp、CityResource、Supply、Repair、Relocation、EmergencySupport、Requests，P13 / B-T3-01 / B-T3-04）
    public MovementRulesDef Movement;          // → 01（rules/movement.json，P11）
    public TerrainRulesDef Terrain;            // → 01（rules/terrain.json，P11）
    public EngagementRulesDef Engagement;      // → 03（rules/engagement.json，P11）
    public CivilRulesDef Civil;                // → 03（rules/civil.json，P11）
    public EnemyAiRulesDef EnemyAi;            // → 04（rules/enemy_ai.json，P11）
    public CommandRulesDef Commands;           // → 04（rules/commands.json，P11）
}
```

---

## 2. 状态

### 2.1 `SimRandom` 状态

| 字段 | C# 类型 | 说明 |
|---|---|---|
| `Seed` | `ulong` | 创建本流的种子（派生子流时使用，**创建后不变**） |
| `_state` | `ulong` | PCG32 状态 |
| `_inc` | `ulong` | PCG32 增量（恒为奇数） |

```csharp
namespace Nightwatch.Sim.Core;

public interface IRandom
{
    ulong Seed { get; }
    uint NextUInt32();
    ulong NextUInt64();                              // 两次 NextUInt32：高 32 位在先
    double NextDouble();                             // [0, 1)
    int NextInt(int minInclusive, int maxExclusive); // 无偏差
    int RollInclusive(int min, int max);             // = NextInt(min, max + 1)；用于数据中的整数 minMax
    double Range(double min, double max);            // min + (max − min) × NextDouble()；max < min 抛异常
    bool Chance(double p);                           // NextDouble() < p；无论 p 为何值都恰好消耗一次 NextDouble
    IRandom Derive(string name);                     // 由 Seed + name 派生，不消耗本流
}
public sealed class SimRandom : IRandom
{
    public SimRandom(ulong seed);
    public RandomState GetState();                   // (State, Inc)，用于哈希与检查点
    public void SetState(RandomState s);
    public static ulong ChildSeed(ulong parentSeed, string name);
    public static ulong NightSeed(ulong runSeed, string levelId, int nightSeq);  // nightSeq：战役 = flow.nights 下标 + 1，非战役 = NightIndex（3.1.5，P43 / B-T2-07）
    internal static uint Bounded(uint range, Func<uint> next);  // 无偏差取整的核心，返回 [0, range)，供测试注入原始序列
    internal static SimRandom FromPcgSeed(ulong initState, ulong initSeq);   // 仅测试：跳过 SplitMix64，直接 pcg32_srandom_r（T-00-01）
}
public readonly record struct RandomState(ulong State, ulong Inc);
```

### 2.2 实体存储

#### 2.2.1 ID

- 实体 ID 为 `int`，**全局唯一**（跨所有实体类型共用一个计数器）、**单调递增**、**从 1 开始**、**永不重用**。`0` 表示"无"（字段名 `…Id` 的空值）。
- `IdAllocator { int NextId; int Allocate(); }`：`Allocate()` 返回 `NextId` 后加一；`NextId == int.MaxValue` 时抛 `InvalidOperationException`。`NextId` 属于 `SimState`，参与哈希。
- 数据中的字符串 ID（如保护目标 `tpp`）与实体 ID 是两回事：实体的 `DefId` 字段保存字符串 ID；`SimState` 为静态对象提供"数据 ID → 实体 ID"查找表（只查找，不遍历）。

#### 2.2.2 `Entity` 基类与 `EntityStore<T>`

只有一层继承：所有实体类继承 `Entity`，**不得**再派生。

```csharp
public abstract class Entity
{
    public int Id;            // 分配后不变
    public bool Alive;        // false = 已标记删除，步末压缩时移出
    public int CreatedTick;   // 创建时的 State.Tick
    public int RemovedTick;   // 标记删除时的 State.Tick；未删除为 -1
    public abstract void WriteHash(StateHasher h);   // 只写子类字段（公共字段 Id / CreatedTick / DefId / Pos / AltM 由存储写）
}

public sealed class EntityStore<T> where T : Entity
{
    public EntityKind Kind { get; }
    public int Count { get; }                       // 含本步已标记删除的条目
    public T this[int index] { get; }               // 按存储下标访问（= ID 升序）
    public T Add(T entity);                         // 分配 ID、设 Alive = true、CreatedTick = Tick、RemovedTick = -1，追加到末尾
    public bool TryGet(int id, out T entity);       // 只返回 Alive 的实体；二分查找
    public T Get(int id);                           // 不存在或已删除 → KeyNotFoundException
    public bool TryGetIncludingRemoved(int id, out T entity);   // 本步内仍可读到已标记删除的实体（用于写事件）
    public void Remove(int id);                     // 标记删除：Alive = false、RemovedTick = Tick；重复删除无操作
    public void Compact();                          // 移出 Alive == false 的条目，保持相对顺序
    public int CountAlive();
}
```

存储结构：每种实体一个 `List<T>`（类实例列表），按 ID 升序（ID 单调递增 + 只追加 ⇒ 天然有序）；按 ID 查找用二分。**不使用 `Dictionary` 存放实体**。

#### 2.2.3 遍历与删除规则

1. **遍历顺序 = ID 升序**（即存储下标顺序）。所有"对每个实体……"的伪代码都按此顺序执行。
2. 遍历写法固定为：

   ```csharp
   for (int i = 0, n = store.Count; i < n; i++)
   {
       var e = store[i];
       if (!e.Alive) continue;
       ...
   }
   ```

   循环开始时记下 `n`：**本循环中新增的实体不会被本循环访问**；本步中由第 k 号系统创建的实体，第 k+1 … 14 号系统可以看到（除非该规格另行规定"创建当步不行动"）。
3. **删除 = 标记删除**：`Remove` 后实体仍留在列表中直到本步末尾 `Compact()`；本步内 `TryGet` 返回 false，遍历跳过它。
4. 引用失效：其他实体中保存的 `…Id` 指向已删除实体时，`TryGet` 返回 false；使用方必须处理（各规格第 5 节写明）。压缩后不清理悬空 ID（ID 不重用，因此不会误指）。
5. 状态哈希在压缩之后计算，因此不包含已删除实体。

### 2.3 实体类型

`EntityKind` 的整数值即**哈希顺序**和**快照中的顺序**，不得重排；新增类型只能追加。

| `EntityKind` | 值 | C# 类型 | 中文 | 来源 | 专有字段与细化规格（P25、P26） |
|---|---|---|---|---|---|
| `GridNode` | 0 | `GridNode` | 电网节点 | `map/grid.json` | 03 2.7 |
| `Structure` | 1 | `Structure` | 保护目标 | `map/structures.json` | 03 2.7 |
| `FireUnit` | 2 | `FireUnit` | 火力单元（含 `Launcher[]`） | 部署 | `PlayerUnitCommon`（2.4）+ 03 2.2：`Weapons`、`RadarDestroyed`、`LaunchersLost`（A-2-20）、`CrewConsecutiveNights`（含今晚，A-2-19）、`AceCrew`、`Engagement`（**删去** 03 的 `NewPositionFirstNight`，统一用 `PlayerUnitCommon.NewPositionPenalty`，A-2-13 / B-T2-06） |
| `SensorUnit` | 3 | `SensorUnit` | 探测单位 | 部署；`automatic` 传感器由 02 在 `Initialize` 中创建 | `PlayerUnitCommon`（2.4）+ 02 2.3：`Automatic`、`NightAids` |
| `EwUnit` | 4 | `EwUnit` | 电子战单位 | 部署 | `PlayerUnitCommon`（2.4）+ 02 2.4：`LurePoint` |
| `DeceptionUnit` | 5 | `DeceptionUnit` | 欺骗单位 | 部署 | `PlayerUnitCommon`（2.4）+ 02 2.4：`SeenThrough`、`ReconCheckedThreatIds`、`AttractedThreatIds` |
| `Threat` | 6 | `Threat` | 敌方目标（弹药 / 平台） | 波次生成、平台投放 | 01 2.2（32 项）→ 02 2.6（10 项 + `EwEverCovered`）→ 03 2.4（4 项）（见 2.4，P23） |
| `Track` | 7 | `Track` | 航迹 | 航迹融合 | 02 2.5（`DefId` 恒为 `""`，P24） |
| `Interceptor` | 8 | `Interceptor` | 拦截弹 / 拦截无人机 | 交战发射 | 03 2.5（追加 `TargetPathVersion : int`，发射时 = `t.PathVersion`，A-2-09） |
| `SupportAsset` | 9 | `SupportAsset` | 外部支援（战斗机编队等） | 呼叫支援 | 03 2.6（`State`、`RadiusM` 等，A-2-21） |
| `Debris` | 10 | `Debris` | 碎片（槽位保留） | 拦截 | 碎片在 `ImpactSystem` 当步结算，**不建持续实体**，存储恒为空（B-T2-16 / P50） |
| `ChoiceRequest` | 11 | `ChoiceRequest` | 二选一请求 | 触发 | 04 2.2（`Kind, ChoiceKey, OptionCount, DefaultOption, DeadlineTick, SubjectUnitId, SubjectTrackId, StoryEventId`；**去掉子类 `CreatedTick` 行**，直接使用基类 `Entity.CreatedTick`，A-3-01） |

**不是实体**的东西：`Detection`（每步临时缓冲，02）、`Launcher`（`FireUnit` 的组件数组，03）、进入点 / 航点 / 图层 / 部署区（静态数据，直接读 `LevelData`）、已知目标清单（`EnemyIntelState` 的组件，04）。

### 2.4 公共字段与合并字段序

每个实体除 2.2.2 的 `Id / Alive / CreatedTick / RemovedTick` 外，由存储统一写入哈希的头部字段与跨规格共用的核心字段如下：

| 字段块 | 适用类型 | 字段 | C# 类型 | 单位 | 初值 | 写 | 读 |
|---|---|---|---|---|---|---|---|
| 定义引用 | 除 `ChoiceRequest`、`Debris` 外全部 | `DefId` | `string` | — | 创建时给定（`Track` 恒为 `""`，P24） | 创建者 | 全部 |
| 空间 | 除 `ChoiceRequest` 外全部 | `Pos` | `Vec2` | m | 创建时给定 | 移动 / 部署相关系统 | 全部 |
| 空间 | 同上 | `AltM` | `double` | m（AGL） | 地面实体 0 | 01（敌方）、03（拦截弹 / 支援） | 全部 |
| 敌方目标（全字段哈希序见下注，P23） | `Threat` | `Kind` | `ThreatKind`（`Munition = 0, Platform = 1`） | — | 创建时 | 01 | 全部 |
| 同上 | `Threat` | `Tag` | `TargetTag?` | — | 来自定义（`null` = 无标签、不可拦截） | 01 | 02、03 |
| 同上 | `Threat` | `VelMps` | `Vec2` | m/s（水平） | `(0,0)` | 01 | 02、03 |
| 同上 | `Threat` | `VertSpeedMps` | `double` | m/s，`d(AltM)/dt`（向上为正） | `0` | 01 | 03 |
| 航迹（全字段见 02 2.5，P24） | `Track` | `ThreatId` | `int` | 实体 ID（真值关联，误报 = 0；界面不得显示） | 02 | 02（4） | 03、02（6） |
| 同上 | `Track` | `Quality` | `TrackQuality` | — | 创建时的融合质量 | 02（4） | 03、04、02（6）、06 |
| 同上 | `Track` | `Tag` | `TargetTag?` | — | 02 3.3.6（统一用 `Tag`，不用 `PerceivedTag`，A-2-01） | 02（4） | 03、06 |

- **`Threat` 全字段与哈希顺序**（P23、A-2-04、A-2-06、A-2-07、A-3-08）：
  1. **01 2.2 段（32 项）**：`Kind`, `Tag`, `VelMps`, `VertSpeedMps`, `Phase`, `WaveId`, `EntryId`, `ParentThreatId`, `SpawnAtSec`, `TargetKind`, `TargetPos`, `TargetStructureId`, `TargetUnitId`（唯一写者 = 01，A-2-04）, `HomingUnitId`（写者 = 02 第 6 步，读者 = 01 第 2 步，A-2-06）, `ProfileReady`, `Profile`, `Path`, `PathVersion`, `PathEnd`, `AnchorSec`, `AnchorArcM`, `PathArcM`, `SpeedMps`, `TerminalSpeedMps`, `TerminalStartArcM`, `StartAltM`, `EndAltM`, `LastUpdateSec`, `ArrivedAtSec`, `TurnArcM`, `Releases`（元素 `PendingRelease` 的 `AtArcM`）, `IngressPath`（弧长字段后缀统一为 `ArcM`，A-3-08；`PathCumM`、`PathLengthM` 不哈希）；
  2. **02 2.6 段（11 项）**：`EwNav`, `EwExtraOffsetM`（落点额外偏移唯一来源，A-2-07 / B-T3-08）, `AccuracyTierDrop`（只来自国家级欺骗，B-T3-08）, `EwPull`, `EwDivertPos`, `NationalSpoof`, `LinkCutState`, `LinkCutAtTick`, `ArmInitialDistM`, `ArmHitProbMult`, **`EwEverCovered`**（`bool`，初值 `false`，第 5 步任一 `NavJam` / `NavSpoof` 单位覆盖即置 `true`，A-2-07）；
  3. **03 2.4 段（4 项）**：`MaxTrackQuality`, `ShotsTaken`, `HeldMask`, `DecoyDrained`。

**我方单位公共字段 `PlayerUnitCommon` 合并表**（适用 `FireUnit`、`SensorUnit`、`EwUnit`、`DeceptionUnit`；`entity.WriteHash(h)` 先按序 1–14 写本表，再写 2.3 所列的子类专有字段；标"—"的不参与哈希，A 1.4）：

| 序 | 字段 | C# 类型 | 初值 | 写（Step 序号） | 读 | 来源 |
|---|---|---|---|---|---|---|
| 1 | `DeployState` | `UnitDeployState` | `Deployed` | 0 | 全部 | 00 / 04 |
| 2 | `DeployPhaseEndTick` | `int` | `-1` | 0 | 0、快照 | 04 |
| 3 | `Relocation` | `RelocationOrder?` | `null` | 0 | 0、快照 | 04 |
| 4 | `Exposure` | `double` | `CarryIn` 或 `0.0` | Create 第 8 步、11 | 02、04、03 | 00 / 02 |
| 5 | `ExposurePeak` | `double` | = 初始 `Exposure` | Create 第 8 步、11 | 03（结算，A-3-10）、04、快照 | 02 |
| 6 | `GridNodeId` | `int` | `0` | 10（`Initialize`） | 02、03 | 00 / 03 |
| 7 | `Powered` | `bool` | `true` | 10 | 02、03 | 00 / 03 |
| 8 | `Emitter` | `EmitterControl?` | 辐射源 = 新实例（02 2.2），否则 `null` | 3（`Initialize`）、0、6 | 3、5、6、7、11、04、快照 | 02 |
| 9 | `NewPositionPenalty` | `bool` | `Placement?.FirstNightAtNewPosition ?? false` | 3（`Initialize`）、11 | 3、5、7、快照 | 02（A-2-13 / B-T2-06） |
| 10 | `PendingRelocationAltId` | `string?` | `null` | 6、0 | 0 | 02 / 04 |
| 11 | `EquipmentEwIds` | `List<string>` | `Placement?.Settings.EquipmentEwIds` 副本，无则空 | 3（`Initialize`） | 11、10 | 02 |
| 12 | `DamageEfficiencyMult` | `double` | `CarryIn` 或 `1.0` | Create 第 8 步、10 | 7、02、快照 | 03 |
| 13 | `SuspendedUntilSec` | `double` | `0.0` | 10 | 3、5、6、7（A-2-12）、快照 | 03 |
| 14 | `LightDamaged` | `bool` | `CarryIn` 或 `false` | Create 第 8 步、10 | 05、快照 | 03 |
| — | `Placement` | `PlacedUnit?` | 部署条目；运行时 / 自动创建 = `null` | Create 第 7 步 | 全部 | 02（**不哈希**） |
| — | `RosterId` | `int` | `Placement?.RosterId ?? 0` | Create 第 7 步 | Create 第 8 步、03（`BuildResult`）、05 | 05（**不哈希**） |

```csharp
public enum UnitDeployState { Deployed = 0, Packing = 1, Packed = 2, Moving = 3, Deploying = 4 }   // 状态机细节 → 04 2.1（B-T1-02）
```

我方单位被摧毁 = `Remove`（不设"已摧毁"状态），同时发出 `PlayerUnitDestroyed`（含 `Vec2 Pos`，A-2-05）；被毁前一刻的 `UnitCarryOut` 快照由 03 系统 10 在 `Remove` 前记入 `ScoringState.DestroyedUnitSnapshots`（A-2-20）。

### 2.5 `SimState`

```csharp
public sealed class SimState
{
    // ---- 00 拥有 ----
    public int Tick;                       // 已完成的步数；Create 后为 0
    public IdAllocator Ids;                // NextId 从 1 开始
    public long NextEventSeq;              // 下一个事件序号，从 1 开始
    public ulong EventStreamHash;          // 全部已产生事件的滚动哈希（3.7.3），初值 = FNV 偏移基 0xCBF29CE484222325
    public EndRequest? EndRequest;         // 系统请求结束夜晚（3.5）
    public RandomStreams Streams;          // 全部子流（3.1.4）

    // ---- 实体存储（声明顺序 = EntityKind 顺序）----
    public EntityStore<GridNode> GridNodes;
    public EntityStore<Structure> Structures;
    public EntityStore<FireUnit> FireUnits;
    public EntityStore<SensorUnit> Sensors;
    public EntityStore<EwUnit> EwUnits;
    public EntityStore<DeceptionUnit> DeceptionUnits;
    public EntityStore<Threat> Threats;
    public EntityStore<Track> Tracks;
    public EntityStore<Interceptor> Interceptors;
    public EntityStore<SupportAsset> SupportAssets;
    public EntityStore<Debris> Debris;
    public EntityStore<ChoiceRequest> Choices;

    // ---- 单例组件（各规格定义字段；声明顺序 = 哈希顺序 1–10，见 3.7.2，P27–P29）----
    public WaveState Waves;                // 1 → 01 2.3：波次进度、Injections（含 GroupIndices，A-2-10）、AllWavesSpawned
    public SensingState Sensing;           // 2 → 02 2.7：本步 Detection 缓冲（不哈希）、延迟探测、已发预警
    public EwState Ew;                     // 3 → 02 2.8：城区导航干扰累计时长
    public CommandState Commands;          // 4 → 04 2.4：指挥点、已触发剧情、剧情二选一结果
    public EnemyIntelState EnemyIntel;     // 5 → 04 2.3：已知目标清单、推迟波次、绕行站点与网格（网格与增量计数不哈希，C-T1-06）
    public SupportState Support;           // 6 → 03 2.8：剩余架次、待处理呼叫
    public GridState Grid;                 // 7 → 03 2.8：电网崩溃状态
    public CivilState Civil;               // 8 → 03 2.8：空袭警报、避难比例、响应度
    public ScoringState Scoring;           // 9 → 03 2.8：结算累加器（含 UnitHits、DestroyedUnitSnapshots、KillsByEnemy、ThreatsEwDowned、ThreatsEverEwCovered，A-2-20 / A-4-04）
    public EngagementState Engagement;     // 10 → 03 2.8：弹药池剩余、已记录的保留原因（P27、P28）

    // ---- 查找表（只查找，不遍历，不参与哈希）----
    public IReadOnlyDictionary<string, int> StructureIdByDefId;
    public IReadOnlyDictionary<string, int> GridNodeIdByDefId;
}

public sealed record EndRequest(NightOutcome Outcome, NightEndReason Reason, string? Detail);
```

各规格可以新增单例组件，但必须在本文件 3.7.2 的哈希顺序表中追加登记。

### 2.6 `SimWorld`、`SimConfig`、`SimContext`

```csharp
public sealed class SimWorld
{
    public static SimWorld Create(LevelData level, SimConfig config, ulong seed);

    public LevelData Level { get; }
    public SimConfig Config { get; }
    public ulong Seed { get; }
    public int Tick { get; }                       // = State.Tick
    public double TimeSec { get; }                 // = Tick × StepSec
    public double StepSec { get; }                 // = Level.Catalog.Conventions.WorldStepSec（= 1）
    public int DurationTicks { get; }              // 本夜长度（步）
    public bool IsFinished { get; }
    public NightResult? Result { get; }            // IsFinished 之后非 null

    public SimCommand Enqueue(SimCommand command); // 返回带 Seq、EffectiveTick 的规范化命令
    public void Step();
    public IReadOnlyList<SimEvent> DrainEvents();
    public SimSnapshot Snapshot { get; }           // 惰性生成、缓存到下一次 Step
    public ulong ComputeStateHash();

    internal SimState State { get; }               // 测试可读

    // 仅测试：按 Order 替换系统实现（返回 null = 使用正式实现）。替身的 Order 必须等于被替换者，StreamName 被忽略（仍使用 3.3 表的子流）
    internal static SimWorld CreateForTest(LevelData level, SimConfig config, ulong seed, Func<int, ISimSystem?> systemOverride);
}

public sealed record SimConfig
{
    public int NightIndex { get; init; } = 1;                  // 从 1 开始
    public DeploymentPlan Deployment { get; init; } = DeploymentPlan.Empty;
    public CarryIn CarryIn { get; init; } = CarryIn.Empty;     // 跨夜 / 跨关带入的数据（下表，P34）
    public bool EndWhenClear { get; init; } = true;            // B-T2-08（原 Q2）
    public bool AutoChoicePrompts { get; init; } = true;       // 04：叙事 / 普通 true，硬核 false（B-T2-11 / P31；参与回放配置）
    public int? DurationTicksOverride { get; init; }           // 仅测试：覆盖夜晚长度
    public bool CheckInvariants { get; init; } = false;        // 每步执行第 6 节断言（测试 / 调试打开）
    [JsonIgnore] public Func<string, ulong, IRandom>? RandomOverride { get; init; }   // 仅测试：按子流名替换随机源；写回放时非 null 抛异常
    [JsonIgnore] public IEnemyAiHooks? EnemyAiHooksOverride { get; init; }            // 仅测试（01 / 04）：写回放时非 null 抛异常（P31）
    [JsonIgnore] public bool CaptureDebug { get; init; } = false;                     // 06：只决定 Snapshot.Debug 是否构建，不参与哈希、不影响任何系统（P31）
}

public sealed record DeploymentPlan(IReadOnlyList<PlacedUnit> Units) { public static readonly DeploymentPlan Empty = new([]); }
public sealed record PlacedUnit
{
    public string UnitDefId { get; init; }          // units/*.json 中的 ID；类别由 GameCatalog.GetPlayerUnitCategory 决定
    public Vec2 Pos { get; init; }
    public string? AlternatePositionId { get; init; }
    public UnitSettings Settings { get; init; } = new();        // 辐射策略 / 触发规则（02 1.11）+ 交战规则（03 2.3）（P33）
    public bool FirstNightAtNewPosition { get; init; }          // 02 / 05：新阵地首夜惩罚来源（P32 / B-T2-06）
    public int RosterId { get; init; }                          // 05：战役花名册编号；0 = 非战役单位（P32）
}

public sealed record UnitSettings                   // 全部字段可空；JSON 单位为内部单位（世界秒 / 米）（P33）
{
    // ---- 02 1.11 ----
    public string? EmissionPolicyId { get; init; }
    public double? DutyOnSec { get; init; }
    public double? DutyOffSec { get; init; }
    public ArmResponse? OnArmIncoming { get; init; }
    public AfterFiringAction? AfterFiring { get; init; }
    public bool? NeighborTakeover { get; init; }
    public Vec2? LurePoint { get; init; }
    public IReadOnlyList<NightAid>? NightAids { get; init; }
    public IReadOnlyList<string>? EquipmentEwIds { get; init; }
    // ---- 03 2.3 ----
    public UnitEngagementSettings? Engagement { get; init; }
}

// ---- CarryIn（05 2.4.1 全集 + 04 KnownTargetCarry，P34 / A-2-18）----
public sealed record CarryIn
{
    public static readonly CarryIn Empty = new();
    public IReadOnlyList<UnitCarryIn> Units { get; init; } = [];              // RosterId 升序
    public IReadOnlyList<StructureCarryIn> Structures { get; init; } = [];    // StructureId 序数升序
    public IReadOnlyList<PoolEntry>? AmmoPool { get; init; }                  // WeaponId 序数升序；非 null 时代替 Meta.AmmoQuota（A-2-14）
    public IReadOnlyList<PoolEntry> PerLevelUsed { get; init; } = [];
    public double? AlertResponsiveness { get; init; }
    public IReadOnlyList<KnownTargetCarry>? KnownTargets { get; init; }       // 04 定义列表类型（A-2-18）
    public int CommandPointsBonus { get; init; }                              // 04 / 05 统一字段名（缺省 0，A-2-18）
    public int FighterSortiesDelta { get; init; }                             // 03 读取（A-2-22）
    public IReadOnlyList<string> ActiveSupports { get; init; } = [];          // 如 adjacent_sector_coverage（B-T2-89 / A-2-22）
    public IReadOnlyList<string> Doctrines { get; init; } = [];
    public IReadOnlyList<DossierCarryIn> Dossier { get; init; } = [];         // EnemyDefId 序数升序（A-2-22）
    public AdaptationCarryIn? Adaptation { get; init; }                       // null = 全部关闭（A-2-22）
    public AutoResolveCarryIn? AutoResolve { get; init; }                     // 03 / 02 读取（B-T3-07 / A-2-22）
    public IReadOnlyList<ResearchEffectCarryIn> ResearchEffects { get; init; } = [];
}
public sealed record UnitCarryIn(
    int RosterId, double Exposure, IReadOnlyList<WeaponCarryIn> Weapons,
    bool LightDamaged, double DamageEfficiencyMult, int CrewConsecutiveNights, bool AceCrew,
    int? DeceptionNightsLeft, bool SeenThrough);
public sealed record WeaponCarryIn(string WeaponId, IReadOnlyList<int> LauncherRounds);
public sealed record StructureCarryIn(string StructureId, int Hp, double LossHp);
public sealed record PoolEntry(string WeaponId, int Rounds);
public sealed record KnownTargetCarry(string UnitDefId, Vec2 Pos, double Exposure, int RosterId = 0, bool Priority = false);  // 04 定义；RosterId 供 05 维护（A-2-18），Priority 供暴露 100 次夜优先打击（B-T3-05）
public sealed record DossierCarryIn(string EnemyDefId, double DiscriminationAdd, double ClassifyTimeMult);
public sealed record AdaptationCarryIn(double UavAltitudeAddM, bool ForceEvasiveUav,
    IReadOnlyList<Vec2> PriorityPositions, IReadOnlyList<string> ActiveTriggers);
public sealed record AutoResolveCarryIn(double InterceptProbMult, double ExposureGainMult);
public sealed record ResearchEffectCarryIn(string EffectId, double Value);

public sealed class SimContext
{
    public SimState State { get; }
    public LevelData Level { get; }
    public SimConfig Config { get; }
    public int Tick { get; }                       // 正在计算的步（= State.Tick，Step 开头已加一）
    public double TimeSec { get; }                 // = Tick × StepSec：本步计算的是这一时刻的状态
    public double StepSec { get; }
    public IRandom Rng { get; }                    // 本系统的子流（3.1.4）；EventLog 为 null
    public EventSink Events { get; }               // Emit + 读本步 / 上一步事件
    public TerrainModel Terrain { get; }           // 01 地形与视线模型（P30）
    public IEnemyAiHooks EnemyAiHooks { get; }     // 01 接口 / 04 实现（P30）
    public SpatialGrid ThreatGrid { get; }         // 3.3.1：系统 2 后重建的敌方目标空间索引（C-T1-08）
    public SpatialGrid TrackGrid { get; }          // 3.3.1：系统 4 后重建的航迹空间索引（C-T1-08）
}

public interface ISimSystem
{
    int Order { get; }                             // 1–14（3.3）
    string Name { get; }                           // 类名
    string? StreamName { get; }                    // 子流名（3.1.4），不用随机数也必须登记
    void Initialize(SimContext ctx);               // Create 时按 Order 调用一次（Tick = 0）
    void Execute(SimContext ctx);                  // 每步调用一次
}

public interface ICommandHandler                   // 由拥有该命令的系统或阶段 0 组件 CommandStage 实现（4.3 表"处理者"列，P39）
{
    IReadOnlyList<SimCommandType> Handles { get; }
    CommandRejectReason? Validate(SimContext ctx, SimCommand cmd);   // null = 接受
    void Apply(SimContext ctx, SimCommand cmd);
}
```

### 2.7 `SimSnapshot`

```csharp
public sealed class SimSnapshot
{
    public int Tick { get; }  public double TimeSec { get; }  public int NightIndex { get; }
    public int DurationTicks { get; }  public bool IsFinished { get; }
    // 每种实体一个数组，按 ID 升序，只含 Alive 实体；视图类型为 readonly record struct，字段由各规格第 2 节标注"快照"列
    public IReadOnlyList<GridNodeView> GridNodes { get; }
    public IReadOnlyList<StructureView> Structures { get; }
    public IReadOnlyList<FireUnitView> FireUnits { get; }
    public IReadOnlyList<SensorUnitView> Sensors { get; }
    public IReadOnlyList<EwUnitView> EwUnits { get; }
    public IReadOnlyList<DeceptionUnitView> DeceptionUnits { get; }
    public IReadOnlyList<ThreatView> Threats { get; }        // 真值：仅调试 / 复盘；正常界面只显示 Tracks（B-T2-21，原 Q12）
    public IReadOnlyList<TrackView> Tracks { get; }
    public IReadOnlyList<InterceptorView> Interceptors { get; }
    public IReadOnlyList<SupportAssetView> SupportAssets { get; }
    public IReadOnlyList<DebrisView> Debris { get; }
    public IReadOnlyList<ChoiceRequestView> Choices { get; }
    public GlobalView Global { get; }                        // 见下（P45）
    public DebugView? Debug { get; }                         // Config.CaptureDebug == false 时为 null（06 8.2 A，P44）
}

public sealed class DebugView
{
    public IReadOnlyList<DetectionDebugView> Detections { get; init; } = [];
}
public readonly record struct DetectionDebugView(
    int SourceId, DetectionSource Source, int ThreatId, int PhantomKey, TrackQuality Quality);
```

- 每个实体视图至少包含：`int Id`、`string DefId`（若有）、`Vec2 Pos`、`double AltM`（若有）。
- **四类我方单位视图**（`FireUnitView` / `SensorUnitView` / `EwUnitView` / `DeceptionUnitView`）公共追加（P46）：
  - 04：`UnitDeployState DeployState`、`int DeployPhaseEndTick`、`Vec2? RelocationDest`（`= Relocation?.Dest`）；
  - 02：`bool EmitterOn`（`= Emitter?.On ?? false`）、`string? PolicyId`（`= Emitter?.PolicyId`）、`FireControlMode FcMode`（`= Emitter?.FcMode ?? FireControlMode.Off`）、`double Exposure`、`double ExposurePeak`、`bool NewPositionPenalty`；
  - 03：`double DamageEfficiencyMult`、`double SuspendedUntilSec`、`bool LightDamaged`；
  - 其余专有视图字段见 03 2.2（`FireUnitView`）与 02 2.9（`TrackView` 等）；`ThreatView` 按 01 2.4；`ChoiceRequestView` 按 04 2.5（`CreatedTick` 取自基类 `Entity.CreatedTick`）。
- **`GlobalView` 合并字段**（P45）：
  - 01：`int PendingSpawnCount`、`int SpawnedThreatCount`、`bool AllWavesSpawned`；
  - 03：`bool AlertOn`、`double ShelteredFrac`、`double Responsiveness`、`int SortiesRemaining`、`bool GridCollapsed`、`double WeightedLossFrac`；
  - 04：`int CommandPoints`、`int CommandPointsInitial`、`IReadOnlyList<KnownTargetView> EnemyKnownTargets`（仅调试 / 复盘显示）、`int HeldWaveCount`。
- 快照是**深拷贝**（视图为值类型，数组新建），之后对 `SimState` 的修改不影响已取得的快照。

---

## 3. 每步算法

### 3.1 `SimRandom` 算法（WS01-002）

选定 **PCG32**（PCG-XSH-RR 64/32，O'Neill 2014 参考实现 `pcg32_random_r` / `pcg32_srandom_r`），**SplitMix64** 用于播种和派生，**FNV‑1a 64** 用于哈希子流名。全部运算为 `ulong` / `uint` 无符号回绕（`unchecked`）。

#### 3.1.1 常数

| 名称 | 值 |
|---|---|
| `PcgMultiplier` | `6364136223846793005UL`（`0x5851F42D4C957F2D`） |
| `SplitMixGamma` | `0x9E3779B97F4A7C15UL` |
| `SplitMixMul1` | `0xBF58476D1CE4E5B9UL` |
| `SplitMixMul2` | `0x94D049BB133111EBUL` |
| `FnvOffsetBasis` | `0xCBF29CE484222325UL` |
| `FnvPrime` | `0x00000100000001B3UL` |
| `DoubleUnit` | `1.0 / 9007199254740992.0`（= 2⁻⁵³） |

#### 3.1.2 基础函数

```csharp
// SplitMix64：x 为状态（按引用推进），返回输出
static ulong SplitMix64Next(ref ulong x)
{
    x += SplitMixGamma;
    ulong z = x;
    z = (z ^ (z >> 30)) * SplitMixMul1;
    z = (z ^ (z >> 27)) * SplitMixMul2;
    return z ^ (z >> 31);
}

// FNV-1a 64，对 UTF-8 字节
static ulong Fnv1a64(ReadOnlySpan<byte> data)
{
    ulong h = FnvOffsetBasis;
    foreach (byte b in data) { h ^= b; h *= FnvPrime; }
    return h;
}
static ulong Fnv1a64(string s) => Fnv1a64(Encoding.UTF8.GetBytes(s));
```

#### 3.1.3 PCG32 与 `SimRandom`

```csharp
public SimRandom(ulong seed)
{
    Seed = seed;
    ulong x = seed;
    ulong initState = SplitMix64Next(ref x);
    ulong initSeq   = SplitMix64Next(ref x);
    // == pcg32_srandom_r(initState, initSeq)
    _state = 0;
    _inc = (initSeq << 1) | 1UL;
    NextUInt32();
    _state += initState;
    NextUInt32();
}

public uint NextUInt32()
{
    ulong old = _state;
    _state = old * PcgMultiplier + _inc;
    uint xorshifted = (uint)(((old >> 18) ^ old) >> 27);
    int rot = (int)(old >> 59);
    return (xorshifted >> rot) | (xorshifted << ((-rot) & 31));
}

public ulong NextUInt64() { ulong hi = NextUInt32(); ulong lo = NextUInt32(); return (hi << 32) | lo; }

public double NextDouble() => (NextUInt64() >> 11) * DoubleUnit;          // 53 位精度，[0, 1)

public int NextInt(int minInclusive, int maxExclusive)
{
    if (maxExclusive <= minInclusive) throw new ArgumentOutOfRangeException(nameof(maxExclusive));
    uint range = (uint)((long)maxExclusive - minInclusive);              // 1 … 2³²−1
    return (int)((long)minInclusive + Bounded(range, NextUInt32));      // long 运算，结果必在 [min, max) 内
}

// 无偏差取整（PCG 参考实现 pcg32_boundedrand_r 的拒绝采样）
internal static uint Bounded(uint range, Func<uint> next)  // 返回 [0, range)；实际实现可避免委托分配
{
    uint threshold = unchecked(0u - range) % range;          // = (2³² − range) mod range
    while (true)
    {
        uint r = next();
        if (r >= threshold) return r % range;
    }
}

public bool Chance(double p) => NextDouble() < p;           // p ≤ 0 恒 false，p ≥ 1 恒 true，但都消耗一次
public double Range(double min, double max) { if (max < min) throw ...; return min + (max - min) * NextDouble(); }
public int RollInclusive(int min, int max) => NextInt(min, max + 1);   // max == int.MaxValue 时抛异常

public static ulong ChildSeed(ulong parentSeed, string name)
{
    ulong x = parentSeed ^ Fnv1a64(name);
    return SplitMix64Next(ref x);
}
public IRandom Derive(string name) => new SimRandom(ChildSeed(Seed, name));   // 只依赖 Seed，不读写 _state

public static ulong NightSeed(ulong runSeed, string levelId, int nightIndex) // 第三参数在战役中传 nightSeq（flow.nights[] 1-based 下标），单夜运行传 NightIndex（P43，B-T2-07）
{
    ulong x = runSeed ^ Fnv1a64($"night:{levelId}:{nightIndex.ToString(CultureInfo.InvariantCulture)}");
    return SplitMix64Next(ref x);
}
```

要点：

- **派生只依赖 `Seed` 与名字**，与父流已消耗多少无关；因此新增 / 删除一个子流、或某系统多用了几个随机数，**都不影响其他子流**（WBS 01.A"改动一处不影响全局"）。
- `Chance` 与 `Range` 无论参数如何都消耗固定次数，保证调整概率数值不改变后续随机序列的对齐。
- `NextInt` 的拒绝采样可能多消耗 `NextUInt32`（概率 `threshold / 2³²`）。

#### 3.1.4 子流名单（P32–P34、A-1.7）

根流：`root = new SimRandom(seed)`（`seed` 为 `SimWorld.Create` 参数）。子流：`root.Derive(<子流名>)`。`RandomStreams` 在 `Create` 中按下表顺序创建全部子流（顺序不影响结果，只影响哈希中的写入顺序）。

| 序 | 子流名 | 使用者（唯一） | 规格 | 用途举例 |
|---|---|---|---|---|
| 0 | `setup` | `SimWorld.Create` 及各系统 `Initialize` | 00 | 开局需要的随机（本版本 0 消耗，预留） |
| 1 | `command` | 阶段 0（命令应用、二选一超时、剧情事件） | 04 | 预留（本版本 0 消耗） |
| 2 | `spawn` | 1 `WaveSpawnSystem` | 01 | 组目标选择（`weighted_random` / 回退）、挂载选择（`NextInt`）、04 钩子 `SelectKnownTarget` / `SelectAirDefenseTarget` 的加权选择（宿主为系统 1） |
| 3 | `movement` | 2 `EnemyMovementSystem` | 01 | `altitudeM` 区间掷骰（每个目标初始化一次） |
| 4 | `sensor` | 3 `SensorSystem` | 02 | 误报（每个有误报能力的工作中探测单位每步 1 次 `Chance` + 位置；探测本身确定性） |
| 5 | `fusion` | 4 `TrackFusionSystem` | 02 | 诱饵甄别（精确航迹首次出现每诱饵 1 次 `Chance`） |
| 6 | `ew` | 5 `ElectronicWarfareSystem` | 02 | 导航干扰 / 诱导 / 国家级欺骗 / 链路中断判定与结果 |
| 7 | `emission` | 6 `EmissionSystem` | 02 | 预留（本版本 0 消耗；诱骗偏转在系统 10 使用 `impact`） |
| 8 | `engagement` | 7 `EngagementSystem` | 03 | 预留（本版本确定性优先级，0 消耗） |
| 9 | `intercept` | 8 `InterceptorSystem` | 03 | 拦截弹与身管射击命中判定 |
| 10 | `support` | 9 `ExternalSupportSystem` | 03 | 大空袭夜战斗机支援拒绝概率 |
| 11 | `impact` | 10 `ImpactSystem` | 03 | 落点偏移、民用损毁数、部件选择、反辐射导弹失锁（欺骗诱偏 + 关机规避） |
| 12 | `exposure` | 11 `ExposureSystem` | 02 | 假发射车被识破判定（每步对暴露度达到阈值的假单位 1 次 `Chance`） |
| 13 | `enemy_ai` | 12 `EnemyIntelSystem` | 04 | 预留（本版本 0 消耗；选目标在系统 1 内走 `spawn`） |
| 14 | `scoring` | 13 `ScoringSystem` | 03 | 预留（0 消耗） |
| 15 | `civil` | 空袭警报相关代码（宿主为系统 13 `ScoringSystem`） | 03 | 预留（本版本警报公式确定性，0 消耗） |
| 16 | `environment` | 天气 / 昼夜（WS01-026） | 01/02 | 预留 |
| 17 | `crew` | 班组（WS01-025） | 03 | 预留 |

规则：

1. **一个系统只能使用 `ctx.Rng`（自己的子流）**。宿主在某系统内的子功能（如碎片在 `ImpactSystem` 内、欺骗单位效果在 `SensorSystem` / `ImpactSystem` 内、敌方 AI 选目标钩子在 `WaveSpawnSystem` 内）使用宿主的子流，除非上表单列。
2. 新增子流：在表末追加一行，并在 3.7.2 中追加（只影响哈希写入，不影响已有子流的序列）。
3. **按实体派生的子流**（`ctx.Rng.Derive($"e{id}")`）只能在实体创建时派生一次并保存在实体字段中（参与哈希）；不得每步重新派生（每次派生都会从头开始，产生重复序列）。默认不使用。
4. `EventLog`（14）不使用随机数，`StreamName = null`。
5. **测试钩子**：`SimConfig.RandomOverride != null` 时，`RandomStreams` 对每个子流调用 `RandomOverride(name, childSeed)`，返回 `null` 则使用正常 `SimRandom`。测试工具 `ScriptedRandom`（`sim.tests/TestKit`）按给定序列返回 `NextDouble` / `NextUInt32`，序列耗尽时抛异常。回放文件不允许携带覆盖。

#### 3.1.5 种子来源（P43、A-5-01、B-T2-07、C-T1-10）

- `SimWorld.Create(level, config, seed)` 的 `seed` 由调用方提供；调用方使用 `SimRandom.NightSeed(runSeed, level.Id, nightSeq)`（WBS 01.A："种子来自关卡 + 夜晚序号"）。其中第三参数 `nightSeq` 由调用方决定：**战役模式**传入该夜在 `flow.nights[]` 中的 1-based 下标（保证插播夜 `nightIndex == 0` 多次出现或同关重打时各夜种子唯一）；**非战役单夜运行**直接传入 `config.NightIndex`（P43，B-T2-07，原 Q11）。
- **命名空间隔离（A-5-01）**：`night:` 前缀专用于 `NightSeed`；战役层（05）通过 `SimRandom.ChildSeed(runSeed, name)` 派生的战役子种子名字一律以 `campaign:` 开头（如 `campaign:card:{seq}`、`campaign:intel:{seq}`），保证两个命名空间互不碰撞。
- `runSeed`（`ulong`）是一局战役的随机种子，由战役层（05）在新战役开始时生成并写入存档；生成方式不在模拟层（模拟层不得调用任何熵源）。
- 无画面工具（`tools/simrun`，命令行规范见 [`07_tools.md` 第 1 节](07_tools.md)）的 `--seed N` 直接作为 `seed` 传入（不经过 `NightSeed`），便于复现（C-T1-10）。

### 3.2 `SimWorld.Create(LevelData, SimConfig, seed)`

按顺序执行；任何一步失败都抛异常，不返回半初始化的世界。

1. **参数校验**：`level`、`config` 非 `null`，否则 `ArgumentNullException`。`config.RandomOverride`、`config.EnemyAiHooksOverride` 可为 `null`。
2. **夜晚数据与时期校验**：`night = level.Waves.Nights` 中 `Night == config.NightIndex` 的唯一一项；找不到 → `SimSetupException`，消息使用 `E_NIGHT_NOT_FOUND` 格式（`[E_NIGHT_NOT_FOUND] levels/<id>/waves.json $.nights: waves.json 中没有第 {n} 夜`）。随后校验 `LevelData` 的加载时期与该夜一致：`DateOnly expectedDate = night.Date ?? level.Meta.DateFrom; if (level.Date != expectedDate)` → 抛 `SimSetupException`（`[E_NIGHT_DATE_MISMATCH] levels/<id>/waves.json $.nights[{i}].date: LevelData 以日期 {level.Date} 加载，但第 {n} 夜要求日期 {expectedDate}；请用 LoadLevel(source, id, nightIndex: {n}) 加载`，B-T2-17，原 Q1）。
3. **时钟**：`StepSec = level.Catalog.Conventions.WorldStepSec`；`DurationTicks = config.DurationTicksOverride ?? SimTime.SecToTicksCeil(night.DurationSec, StepSec)`；`DurationTicks < 1` → `SimSetupException`。
3a. **地形、AI 钩子与空间网格（P35、C-T1-08）**：构造 `Terrain = new TerrainModel(level.Heightmap, level.Catalog.Rules.Terrain)`（02 3.1）；选择 `EnemyAiHooks = config.EnemyAiHooksOverride ?? new EnemyAiHooks()`（04 3.4）；初始化空间索引 `ThreatGrid` 与 `TrackGrid`（3.3.1）。
4. **状态**：新建 `SimState`：`Tick = 0`，`Ids.NextId = 1`，`NextEventSeq = 1`，`EventStreamHash = 0xCBF29CE484222325`，`EndRequest = null`，全部实体存储与 10 个单例组件为空 / 初值。
5. **随机**：`root = new SimRandom(seed)`；按 3.1.4 表顺序创建全部子流（考虑 `RandomOverride`）。
6. **静态实体**（ID 分配顺序固定）：
   1. 电网节点：按 `level.Grid.Nodes` 数据顺序 `Add`，填 `DefId`、`Pos`；同时填 `GridNodeIdByDefId`。
   2. 保护目标：按 `level.Structures` 数据顺序 `Add`，填 `DefId`、`Pos`、`GridNodeId`（按查找表解析，无则 0）；填 `StructureIdByDefId`。其余字段初值由 03 规定。
7. **部署方案（P36、A-4-05）**：先调用 `DeploymentValidator.Validate(level, config.Deployment)`（规则 → 04 3.1.1：单位存在、数量不超过 `availableUnits`、位置合法……），有错误则抛 `SimSetupException`（列出全部错误）。然后按 `config.Deployment.Units` 顺序为每个 `PlacedUnit` 在对应存储中 `Add`：填 `Placement = placed`、`RosterId = placed.RosterId`、`DeployState = Deployed`、`Pos = placed.Pos`、`AltM = 0`、`Exposure = 0`、`ExposurePeak = 0`、`NewPositionPenalty = placed.FirstNightAtNewPosition`（02 3.6.3）、`Powered = true`、`GridNodeId = 0`、`DamageEfficiencyMult = 1.0`。对 `FireUnit`，创建后立即调用 `FireUnitFactory.Init(fu, def, rules)`（03 3.1.1：按 `def.Weapons` 顺序建立 `fu.Weapons` 列表，`Launchers` 置空，**不在此时扣池装填**——弹药池与发射架在步骤 9 的 `EngagementSystem.Initialize` 中统一建立，A-4-05）；其余类型专有字段初值由所属规格初始化。
8. **带入数据（P37、A-4-05、A-2-22）**：应用 `config.CarryIn`（`CarryIn == null` 时视为默认 `new CarryIn()`）：
   - 若 `CarryIn.ActiveSupports.Count > 0` 或 `CarryIn.Adaptation != null` 且对应 M3+ 特性尚未实现，抛 `SimSetupException`（`[E_NOT_IMPLEMENTED] CarryIn 包含尚未实现的 M3+ 字段`，A-2-22）。
   - 对 `CarryIn.Units` 中每项 `u`：在四类我方单位存储中按 `RosterId == u.RosterId`（`u.RosterId != 0`）查找唯一实体，拷贝标量字段：`Exposure = u.Exposure`、`ExposurePeak = u.Exposure`、`DamageEfficiencyMult = u.DamageEfficiencyMult`、`LightDamaged = u.LightDamaged`、`CrewConsecutiveNights = u.CrewConsecutiveNights`、`AceCrew = u.AceCrew`；若为 `DeceptionUnit` 则置 `SeenThrough = u.SeenThrough`。
   - 其余 `CarryIn` 字段（`AmmoPool` 与 `UnitCarryIn.Weapons[].LauncherRounds`、`Structures`、`KnownTargets`、`AlertResponsiveness`、`DeceptionUnit.NightsAtCurrentPos`、`ActiveSupports`、`Adaptation`）不在此步改写实体，由各系统在步骤 9 `Initialize`（及步骤 9a `CommandStage.Initialize`）中从 `ctx.Config.CarryIn` 读取并初始化各自组件与发射架（其中 03 `EngagementSystem.Initialize` 在 `u.Weapons != null` 时直接按 `LauncherRounds` 构建各发射架、不从 `AmmoPool` 重复扣减，A-4-05）。
9. **系统**：按 3.3 表实例化 14 个系统，按 `Order` 升序调用 `Initialize(ctx)`（`ctx.Tick = 0`，`ctx.Rng` = 子流 `setup`）。`Initialize` 可以创建实体（ID 接着分配）。
9a. **阶段 0 组件初始化（P38、A-2-18）**：调用 `CommandStage.Initialize(ctx)`（04 3.2/3.3，`ctx.Rng = setup`）：执行剧情波次引用开局校验（04 1.3.3），并初始化 `State.Command.CommandPoints = Math.Clamp(level.Meta.CommandPointsPerNight + (config.CarryIn?.CommandPointsBonus ?? 0), 0, level.Catalog.Rules.Economy.CommandPointsPerNight.Max)` 及 `CommandPointsInitial = State.Command.CommandPoints`。
10. **命令处理者注册（P39）**：收集 14 个系统**以及阶段 0 组件 `CommandStage`** 中所有 `ICommandHandler` 实现，建立 `SimCommandType → handler` 表；同一类型有两个处理者 → `InvalidOperationException`；4.3 表中的每个命令类型都必须有处理者（实现阶段未完成的系统用"一律拒绝 `NotImplemented`"的占位处理者）。
11. **开场事件**：发出 `NightStarted { NightIndex, DurationTicks, Seed }`（`Tick = 0`，`Seq = 1`），并立即执行一次 EventLog 的封存逻辑（3.4.2 的步骤 1–3），使其进入事件流哈希并可被 `DrainEvents` 取到。
12. 世界就绪：`Tick = 0`，`IsFinished = false`；`Snapshot` 可读，反映开场状态。

### 3.3 `Step()` 的系统顺序（照抄 WBS 01.B，不得调整）

| Order | 系统（类名） | 子流 | 职责（WBS 01.B 原文） | 规格 |
|---|---|---|---|---|
| 1 | `WaveSpawnSystem` | `spawn` | 按波次脚本生成敌方目标 | 01 |
| 2 | `EnemyMovementSystem` | `movement` | 敌方按航线移动（航点、高度剖面、绕行） | 01 |
| 3 | `SensorSystem` | `sensor` | 各传感器生成原始探测（距离、高度、地形遮挡、天气） | 02 |
| 4 | `TrackFusionSystem` | `fusion` | 合并探测 → 航迹（模糊 / 大致 / 精确），诱饵甄别 | 02 |
| 5 | `ElectronicWarfareSystem` | `ew` | 计算电子战覆盖，修改敌方精度、链路状态 | 02 |
| 6 | `EmissionSystem` | `emission` | 按辐射策略和触发规则决定雷达开关 | 02 |
| 7 | `EngagementSystem` | `engagement` | 按交战规则选目标、分配弹药、发射 | 03 |
| 8 | `InterceptorSystem` | `intercept` | 拦截弹飞行；到达拦截点时判定命中（拦截概率 × 修正） | 03 |
| 9 | `ExternalSupportSystem` | `support` | 战斗机、国家级电子战等 | 03 |
| 10 | `ImpactSystem` | `impact` | 命中地面：伤害、溅射、碎片、电网连锁 | 03 |
| 11 | `ExposureSystem` | `exposure` | 更新暴露度 | 02 |
| 12 | `EnemyIntelSystem` | `enemy_ai` | 敌方 AI 更新已知目标清单（试探结果、暴露度） | 04 |
| 13 | `ScoringSystem` | `scoring` | 交换比、损失、信任度变化 | 03 |
| 14 | `EventLog` | — | 输出本步事件 | 00 |

#### 3.3.1 空间索引与性能预算（C-T1-08、C-T1-16、C-T2-02）

- **`SpatialGrid`**：二维均匀网格加速结构（`ThreatGrid` 与 `TrackGrid`，挂在 `SimContext` 上，**不参与状态哈希**）。
  - 网格划分：覆盖 `[0, Map.WidthM] × [0, Map.HeightM]`，单元边长 `CellSizeM = Math.Max(5000.0, Math.Max(Map.WidthM, Map.HeightM) / 64.0)`（50 km 地图为 5000 m，10×10 格；300 km 地图同样为 5000 m，60×60 格）；越界坐标钳制到边界格。
  - 重建时机：`ThreatGrid` 在系统 2（`EnemyMovementSystem`）结束后由框架重建（写入全部 `Alive` 的 `Threat`）；`TrackGrid` 在系统 4（`TrackFusionSystem`）结束后由框架重建（写入全部 `Alive` 的 `Track`）。系统 8 / 10 中目标死亡仅置 `Alive = false`；`QueryCircle` 自动跳过 `!Alive` 实体。
  - 查询契约：`QueryCircle(Vec2 center, double radiusM)` 枚举圆外接矩形覆盖格内的候选实体，用精确平方距离 `(dx*dx + dy*dy <= radiusM*radiusM)` 过滤后，**按实体 `Id` 升序返回**——与直接遍历 `EntityStore` 全表过滤的返回集合和顺序**逐位完全一致**。
- **空闲步早退（C-T1-16）**：当某一步满足 `Threats.CountAlive == 0 && Tracks.CountAlive == 0 && Interceptors.CountAlive == 0 && Debris.CountAlive == 0` 且本步无到期波次 / 剧情动作 / 移动中单位时，各系统在完成 O(1) 全局检查与必要的每步固定计数 / 随机推进后直接返回，不分配临时集合。
- **单步性能预算（C-T2-02）**：在同屏 50 `Threat` × 15 我方单位 × 20 `Interceptor` 典型高压负载（Release 构建）下，单步 `Step()` 耗时目标：均值 `< 2 ms`（对应 60× 快进 60 Step/s 下 CPU 占用 `< 12%`）、p99 `< 4 ms`、最坏单步 `< 50 ms`；完全空闲步耗时 `≤ 20 µs`。

### 3.4 `Step()` 框架

```csharp
public void Step()
{
    if (IsFinished) throw new InvalidOperationException("夜晚已结束，不能继续 Step()");

    // 1. 推进时钟：本步计算 (Tick−1, Tick] 区间，结束时状态对应时刻 TimeSec = Tick × StepSec
    State.Tick += 1;

    // 2. 阶段 0：命令（不属于 01.B 的 14 个系统，是框架的一部分）
    ApplyDueCommands();                 // 3.4.1
    CommandStageHooks();                // 04：严格按 DeploymentStage.Run(ctx) → ChoiceStage.Run(ctx) → StoryStage.Run(ctx) 顺序执行（P40，B-T2-15，原 Q5/Q15）

    // 3. 系统 1–13（严格按 Order；系统 2 后重建 ThreatGrid，系统 4 后重建 TrackGrid）
    for (int k = 0; k < 13; k++)
    {
        systems[k].Execute(ContextFor(systems[k]));
        if (k == 1) RebuildThreatGrid();
        else if (k == 3) RebuildTrackGrid();
    }

    // 4. 结束判定（3.5）：可能发出 NightEnded、生成 Result
    CheckNightEnd();

    // 5. 系统 14：EventLog
    systems[13].Execute(ContextFor(systems[13]));

    // 6. 压缩全部实体存储（按 EntityKind 顺序逐个 Compact）
    CompactAllStores();

    // 7. 收尾：若本步结束了夜晚，Result.FinalStateHash = ComputeStateHash()；令快照缓存失效
    if (Config.CheckInvariants) AssertInvariants();   // 第 6 节
}
```

#### 3.4.1 命令队列

```csharp
public SimCommand Enqueue(SimCommand command)
{
    if (IsFinished) throw new InvalidOperationException(...);
    int eff = command.EffectiveTick <= State.Tick ? State.Tick + 1 : command.EffectiveTick;   // 最早下一步生效
    var c = command with { EffectiveTick = eff, Seq = _nextCommandSeq++ };                    // Seq 从 1 开始
    _pending.Add(c);                                       // 按 (EffectiveTick, Seq) 有序插入（稳定）
    _commandLog.Add(c);                                    // 回放记录：全部入队命令，含后来被拒绝的
    return c;
}
```

- **生效时刻语义**：`EffectiveTick = T` 表示命令在**使 `Tick` 变为 `T` 的那次 `Step()`** 的阶段 0 被应用，即影响时刻 `(T−1, T]` 的计算。界面在看到 `Tick = k` 的快照后发出的命令，默认 `EffectiveTick = 0`（⇒ 规范化为 `k + 1`）。
- `ApplyDueCommands()`：取出全部 `EffectiveTick ≤ State.Tick` 的命令，按 `(EffectiveTick, Seq)` 升序逐条：
  1. 找处理者 `h`；`r = h.Validate(ctx, cmd)`（`ctx.Rng` = `command` 子流）。
  2. `r == null` → `h.Apply(ctx, cmd)`，发出 `CommandApplied { CommandSeq, CommandType }`。
  3. 否则发出 `CommandRejected { CommandSeq, CommandType, Reason = r }`，状态不变。
  4. 后一条命令的 `Validate` 看到前一条命令 `Apply` 之后的状态。
- **指挥点校验与扣除规则（A-2-17）**：凡消耗指挥点（`cost > 0`）的命令，其处理者在 `Validate` 的**最后一步**（全部业务前置条件通过后）调用 `if (!CommandPointRules.CanSpend(ctx, cost)) return CommandRejectReason.NoCommandPoints;`（04 3.2.1）；在 `Apply` 的**第一步**调用 `CommandPointRules.Spend(ctx, cost)`。免费命令（`cost == 0`）不调用。
- 命令队列与命令日志**不属于 `SimState`**、不参与状态哈希（它们是输入）。
- `_nextCommandSeq` 与事件 `Seq` 是两个独立计数器。

#### 3.4.2 事件流

```csharp
public sealed class EventSink
{
    public void Emit(SimEvent e);                       // 填 Tick = State.Tick、Seq = State.NextEventSeq++，加入 CurrentStep
    public IReadOnlyList<SimEvent> CurrentStep { get; } // 本步已产生的事件（较早系统产生），按 Seq
    public IReadOnlyList<SimEvent> PreviousStep { get; }// 上一步的全部事件，按 Seq
}
```

- 系统 k 可以读 `CurrentStep`（来自阶段 0 和系统 1…k−1 以及自己已发的）和 `PreviousStep`（用于"较晚系统产生、较早系统消费"的情况，例如 `EnemyIntelSystem`(12) 产生、`WaveSpawnSystem`(1) 下一步消费）。**系统之间只通过 `SimState` 与事件交互**，不得互相持有引用调用方法（`ScoringSystem.BuildResult` 由框架调用除外）。
- `EventLog`（14）的 `Execute`：
  1. 对 `CurrentStep` 中每个事件按 `Seq` 顺序更新 `State.EventStreamHash`（3.7.3）；
  2. 追加到输出缓冲 `_outbox`；
  3. `PreviousStep = CurrentStep`，`CurrentStep = 新空列表`。
- `DrainEvents()`：返回 `_outbox` 的副本（按 `Seq` 升序，可能跨多步），然后清空 `_outbox`。从不调用则一直累积（无上限，单夜典型百级事件 ≈ 数十 KB；每步消费的客户端可在每步末调用 `DrainEvents()`，B-T3-06，原 Q13）。
- `DrainEvents()` 与 `Snapshot` 都**不改变** `SimState`（不影响哈希）。

### 3.5 夜晚结束与 `NightResult`

`CheckNightEnd()`（在系统 13 之后、EventLog 之前执行）：

```
if State.EndRequest != null:                          # 由系统设置，典型：ScoringSystem 判定失败条件（03）
    end(State.EndRequest.Outcome, State.EndRequest.Reason)
elif State.Tick >= DurationTicks:
    end(Survived, DurationElapsed)
elif Config.EndWhenClear and AllClear():
    end(Survived, AllClear)
```

- `AllClear()` 同时满足以下 5 项条件（P41、A-4-03、B-T2-08，原 Q2）：
  1. **波次队列清空**：`State.Waves.Pending.Count == 0 && State.Waves.Injections.Count == 0`（直接判底层队列，**不得读取**可能滞后半步的 `State.Waves.AllWavesSpawned` 缓存，A-4-03）；
  2. **场上无仍可造成伤害的敌方目标**：`State.Threats` 中不存在满足 `t.Kind == ThreatKind.Munition || (t.Kind == ThreatKind.Platform && t.Releases.Any(r => !r.Done))` 的存活实体（已投完弹返航的纯平台、以及无剩余投放项的侦察/佯攻平台不阻塞清场，B-T2-08）；
  3. **场上无飞行中拦截弹**：`State.Interceptors.CountAlive == 0`；
  4. **无待释放的推迟波次**：`State.EnemyIntel.HeldWaves.Count == 0`（04）；
  5. **无待触发的剧情生成**：`!StoryRules.HasPendingScheduledSpawn(ctx)`（04 3.3.3）。
- 多个 `EndRequest` 同步设置时，**先设置者胜出**（`EndRequest` 非 null 后不再覆盖）。
- `end(outcome, reason)`：
  1. `Result = ScoringSystem.BuildResult(ctx, outcome, reason)`（字段 → 03 2.9 / 04 2.4 / 05 2.4.2）；框架填写公共字段（下）。
  2. 发出 `NightEnded { Outcome, Reason, EndTick = Tick }`。
  3. `IsFinished = true`。之后 `Step()`、`Enqueue()` 抛 `InvalidOperationException`；`DrainEvents()`、`Snapshot`、`ComputeStateHash()` 仍可用。
  4. 压缩后计算 `FinalStateHash` 写入 `Result`。

```csharp
public enum NightOutcome { Survived = 0, Defeated = 1 }
public enum NightEndReason { DurationElapsed = 0, AllClear = 1, DefeatCondition = 2 }

public sealed record NightResult
{
    // ---- 00 填写 ----
    public string LevelId { get; init; } = "";
    public int NightIndex { get; init; }
    public string Seed { get; init; } = "";                 // "0x" + 16 位大写十六进制
    public string DataHash { get; init; } = "";
    public NightOutcome Outcome { get; init; }
    public NightEndReason EndReason { get; init; }
    public int EndTick { get; init; }
    public double EndTimeSec { get; init; }
    public string FinalStateHash { get; init; } = "";       // "0x" + 16 位大写十六进制
    // ---- 03 定义并填写（03 2.9）：损失、弹药消耗、交换比、碎片、暴露度、民情与信任、支援汇总 ----
    public LossesSummary Losses { get; init; } = new();
    public AmmoSummary Ammo { get; init; } = new();
    public ExchangeSummary Exchange { get; init; } = new();
    public DebrisSummary Debris { get; init; } = new();
    public ExposureSummary Exposure { get; init; } = new();
    public CivilSummary Civil { get; init; } = new();
    public SupportSummary Support { get; init; } = new();
    // ---- 04 定义并填写（04 2.4）：指挥与剧情汇总 ----
    public CommandSummary Commands { get; init; } = new();
    // ---- 05 / 04 / 02 合并定义：跨夜 / 跨关带出的数据 ----
    public CarryOut CarryOut { get; init; } = new();
}

// 04 指挥汇总（P42）
public sealed record CommandSummary
{
    public int CommandPointsInitial { get; init; }
    public int CommandPointsSpent { get; init; }
    public int CommandPointsRemaining { get; init; }
    public int RelocationsCompleted { get; init; }
    public int ChoicesTriggered { get; init; }
    public int ChoicesTimedOut { get; init; }
}

// CarryOut 完整合并定义（05 2.4.2 + 04 StoryChoiceResults + 02 UrbanNavJamTriggered，P42 / B-T2-36）
public sealed record CarryOut
{
    public IReadOnlyList<UnitCarryOut> Units { get; init; } = [];
    public IReadOnlyDictionary<string, int> AmmoPoolRemaining { get; init; } = new Dictionary<string, int>();
    public IReadOnlyList<StructureCarryOut> Structures { get; init; } = [];
    public IReadOnlyList<KnownTargetRecord> KnownTargets { get; init; } = [];
    public double AlertResponsiveness { get; init; }
    public int TrustDelta { get; init; }
    public int MoraleDelta { get; init; }
    public IReadOnlyDictionary<string, string> StoryChoiceResults { get; init; } = new Dictionary<string, string>(); // choiceId → 选中的 optionId（04）
    public bool UrbanNavJamTriggered { get; init; }         // 本夜是否曾在城区开启导航干扰（02 B-T2-36，供 03/05 统计）
}

public sealed record UnitCarryOut
{
    public int RosterId { get; init; }
    public string DefId { get; init; } = "";
    public Vec2 FinalPos { get; init; }
    public bool Destroyed { get; init; }
    public bool LightDamaged { get; init; }
    public double RepairDaysNeeded { get; init; }
    public double Exposure { get; init; }
    public double ExposurePeak { get; init; }
    public int CrewConsecutiveNights { get; init; }
    public bool AceCrew { get; init; }
    public int KillsTonight { get; init; }
    public bool SeenThrough { get; init; }
    public int NightsAtCurrentPos { get; init; }
    public IReadOnlyList<WeaponCarryIn> Weapons { get; init; } = []; // 各武器架上剩余弹药，跨夜原样带入
}

public sealed record StructureCarryOut
{
    public string DefId { get; init; } = "";
    public int Hp { get; init; }
    public bool Destroyed { get; init; }
}
```

`NightResult` 必须可被 `System.Text.Json` 序列化 / 反序列化往返（WS01-023 验收），统一使用以下 `JsonSerializerOptions`（P42）：`PropertyNamingPolicy = JsonNamingPolicy.CamelCase`、`Converters = { new JsonStringEnumConverter() }`、`NumberHandling = JsonNumberHandling.Strict`（禁止 `NaN` / `Infinity`）。

### 3.6 快照生成

- `Snapshot` 属性：若缓存为空，则从 `SimState` 构建 `SimSnapshot`（2.7）并缓存；`Step()` 末尾清空缓存。即：**每步最多构建一次，不访问就不构建**（无画面运行零开销）。
- 构建过程只读 `SimState`，不得调用任何随机数、不得发事件、不得修改状态。
- 线程：`SimWorld` 非线程安全；客户端必须在同一线程调用 `Step()` 与读取 `Snapshot`（或在 `Step()` 之间把快照交给其他线程——快照本身不可变）。

### 3.7 状态哈希

#### 3.7.1 `StateHasher`

FNV‑1a 64（常数同 3.1.1），对以下规范字节流计算。全部为**小端**。

| 写入方法 | 编码 |
|---|---|
| `Write(int v)` | 4 字节补码 |
| `Write(long v)` / `Write(ulong v)` | 8 字节 |
| `Write(double v)` | `v == 0.0` 时先归一为 `+0.0`；写 `BitConverter.DoubleToInt64Bits(v)` 的 8 字节（NaN 由不变量禁止出现） |
| `Write(bool v)` | 1 字节，`0` / `1` |
| `Write(string? v)` | `null` → `Write(-1)`；否则 `Write(UTF-8 字节数)` + UTF-8 字节 |
| `Write<TEnum>(TEnum v)` | `Write((int)v)` |
| `Write(Vec2 v)` | `Write(v.X)`，`Write(v.Y)` |
| `Write(T? v)`（可空值类型） | `Write(bool HasValue)`，有值再写值 |
| 列表 | `Write(Count)`，然后逐项 |

`ulong Value` 返回当前哈希。

#### 3.7.2 写入顺序（`SimWorld.ComputeStateHash()`）

1. 头：`Write("NWSH")`，`Write(1)`（格式版本），`Write(State.Tick)`，`Write(State.Ids.NextId)`，`Write(State.NextEventSeq)`，`Write(State.EventStreamHash)`。
2. `EndRequest`：`Write(bool 非 null)`，非 null 时写 `Outcome`、`Reason`、`Detail`。
3. 随机子流：按 3.1.4 表顺序，每个写 `Write(State)`、`Write(Inc)`（`RandomOverride` 的替身写 `Write(0UL)`、`Write(0UL)`）。
4. 实体存储：按 `EntityKind` 值升序。每个存储：`Write((int)Kind)`，`Write(CountAlive)`，然后对每个 Alive 实体按 ID 升序：`Write(Id)`、`Write(CreatedTick)`、`Write(DefId)`（无此字段的类型写 `null`）、`Write(Pos)`、`Write(AltM)`（无空间字段的类型不写这两项）、再调用 `entity.WriteHash(h)` 写类型专有字段——**顺序 = 2.2.2 及所属规格第 2 节状态表中的行顺序**（其中四类我方单位先按 2.3.2 顺序写 `PlayerUnitCommon` 的 1–14 项，再写子类专有字段，P24）；表中标"不参与哈希"的派生缓存不写。
5. 单例组件：按下表顺序，各自调用 `WriteHash(h)`（字段顺序 = 所属规格状态表顺序，P28、P29）：

| 序 | 组件 | 规格与章节 |
|---|---|---|
| 1 | `WaveState` | 01 §2.3 |
| 2 | `SensingState` | 02 §2.6 |
| 3 | `EwState` | 02 §2.7 |
| 4 | `CommandState` | 04 §2.2 |
| 5 | `EnemyIntelState` | 04 §2.3 |
| 6 | `SupportState` | 03 §2.5 |
| 7 | `GridState` | 03 §2.6 |
| 8 | `CivilState` | 03 §2.7 |
| 9 | `ScoringState` | 03 §2.8 |
| 10 | `EngagementState` | 03 §2.4 |

组件内部的集合必须是有序容器（`List`、按键排序后的数组、`SortedDictionary`）；写入时按其固定顺序遍历。

#### 3.7.3 事件流哈希

`EventLog` 对每个事件计算：在 `State.EventStreamHash` 的基础上继续 FNV‑1a，依次写 `Write((int)e.Type)`、`Write(e.Tick)`、`Write(e.Seq)`、`Write(e.AtSec)`（可空）、再调用 `e.WriteHash(h)`（字段顺序 = 4.2 / 各规格第 4 节的字段表顺序）。结果写回 `State.EventStreamHash`。因此**事件内容的任何差异都会反映在状态哈希中**。

#### 3.7.4 输出格式

对外显示和写文件时：`"0x" + Value.ToString("X16", CultureInfo.InvariantCulture)`。

### 3.8 确定性约束（概要；断言见第 6 节）

- 系统执行顺序固定（3.3）；实体遍历按 ID 升序（2.2.3）；事件按 `Seq`；命令按 `(EffectiveTick, Seq)`。
- 需要排序时，比较器必须给出**全序**：主键之后以实体 ID（或数据数组下标）作为最终决胜键。`List<T>.Sort` / `Array.Sort` 是不稳定排序，只能在全序比较器下使用；或使用 LINQ `OrderBy(...).ThenBy(x => x.Id)`（稳定）。
- 浮点运算只用 `double`；同一公式在全目录只写一处实现（放在对应系统或 `Geo` 工具类），不在多处复制。
- WBS 01.A："回放只保证同平台一致"。三角 / 指数函数（`Math.Sin/Cos/Atan2/Exp/Pow/Log`）在不同 CPU / 运行时上可能有末位差异，允许使用，但规格应尽量避免让阈值判断直接依赖它们的末位（优先用平方距离比较、向量点积等）。`Math.Sqrt`、`+ − × ÷` 在 IEEE 754 下逐位确定。

### 3.9 回放

#### 3.9.1 回放文件格式（JSON，UTF-8，扩展名 `.nwreplay.json`）

```json
{
  "format": "nightwatch-replay",
  "version": 1,
  "simVersion": "0.1.0",
  "runtime": "osx-arm64/.NET 8.0.x",
  "levelId": "test_01",
  "nightIndex": 1,
  "seed": "0x6DD180096484586D",
  "dataHash": "sha256:<64 位小写十六进制>",
  "config": { "nightIndex": 1, "deployment": { "units": [ ... ] }, "carryIn": { ... }, "endWhenClear": true },
  "commands": [
    { "type": "SetAirRaidAlert", "seq": 1, "effectiveTick": 120, "on": true }
  ],
  "checkpointInterval": 60,
  "checkpoints": [ { "tick": 60, "hash": "0x0123456789ABCDEF" } ],
  "final": { "tick": 28800, "hash": "0x0123456789ABCDEF", "outcome": "Survived", "reason": "DurationElapsed" }
}
```

- `seed`、哈希用十六进制字符串（JSON number 无法精确表示 64 位整数）。
- `config` 与 `commands` 用 `System.Text.Json` 序列化，属性名 camelCase；命令多态用 `[JsonPolymorphic(TypeDiscriminatorPropertyName = "type")]` + 每个命令类型的 `[JsonDerivedType(typeof(X), "X")]`（判别值 = 4.3 表中的命令名）。enum 序列化为字符串名（`JsonStringEnumConverter`）。
- 写出回放文件时，若 `config.RandomOverride != null` 或 `config.EnemyAiHooksOverride != null`，抛 `InvalidOperationException`（测试替身不可序列化到回放文件，P31）。
- `commands` = 原世界 `_commandLog` 的全部条目（含被拒绝的），按 `seq` 升序，`effectiveTick` 为规范化后的值。
- `simVersion`、`runtime` 仅供参考，不参与校验；`runtime` 不同时回放工具打印警告（同平台保证，WBS 01.A）。
- `checkpoints`：每 `checkpointInterval` 步记录一次状态哈希（`tick % interval == 0`），用于定位分歧点；`checkpointInterval = 0` 表示不记录。

#### 3.9.2 数据哈希

`DataHash` = SHA‑256（`System.Security.Cryptography.SHA256`）对以下字节流：对 `LevelData.LoadedFiles` 按**序数（ordinal）升序**排序后的每个文件，依次写 `UTF-8(相对路径)`、`0x00`、`Int64 小端(内容长度)`、内容字节。`.json` 文件的内容先把 `\r\n` 替换为 `\n` 再计算（长度也按替换后计算）；`.png` 用原始字节。输出 `"sha256:" + 小写十六进制`。

#### 3.9.3 回放流程（`ReplayRunner`）

1. 读文件，校验 `format`、`version`。
2. `level = DataLoader.LoadLevel(source, levelId, nightIndex)`；`level.DataHash != dataHash` → 抛 `ReplayDataMismatchException`（除非调用方传 `force: true`，此时只警告）。
3. `world = SimWorld.Create(level, config, seed)`。
4. 按 `seq` 顺序对每条命令调用 `world.Enqueue(cmd)`（此时 `Tick = 0`，所有 `effectiveTick ≥ 1`，规范化不改变它；新分配的 `Seq` 与记录一致——不一致即抛异常）。
5. 循环 `Step()` 直到 `IsFinished`；在每个检查点比较哈希，第一个不一致的检查点 → 报告 `ReplayDivergedException(tick, expected, actual)`。
6. 结束后比较 `final.tick`、`final.hash`。

---

## 4. 事件与命令

### 4.1 编号规则

事件类型 `SimEventType`、命令类型 `SimCommandType`、拒绝原因 `CommandRejectReason` 都是显式整数值的 enum，按规格分段，**只追加、不重排**：

| 段 | 规格 |
|---|---|
| 0–99 | 00 |
| 100–199 | 01 |
| 200–299 | 02 |
| 300–399 | 03 |
| 400–499 | 04 |
| 500–599 | 05 |

### 4.2 事件

```csharp
public abstract record SimEvent
{
    public int Tick { get; init; }          // 产生事件的步（Emit 时 = State.Tick）
    public long Seq { get; init; }          // 世界内全局单调递增，从 1 开始
    public double? AtSec { get; init; }     // 精确发生时刻（世界秒），用于解析拦截等；须满足 (Tick−1)·StepSec < AtSec ≤ Tick·StepSec；null = Tick·StepSec
    public abstract SimEventType Type { get; }
    public abstract void WriteHash(StateHasher h);   // 只写子类字段，顺序 = 字段表顺序
}
```

- 事件字段只放值（ID、数字、enum、字符串），**不放实体对象引用**。
- 事件命名：过去式 / 名词短语，PascalCase，类名 = enum 成员名。

**事件总表**（字段由"规格"列所指文件第 4 节细化；00 的事件字段在此给全）：

| 值 | 事件 | 规格 | 含义 / 关键字段 |
|---|---|---|---|
| 0 | `NightStarted` | 00 | `int NightIndex, int DurationTicks, string Seed` |
| 1 | `NightEnded` | 00 | `NightOutcome Outcome, NightEndReason Reason, int EndTick` |
| 2 | `CommandApplied` | 00 | `long CommandSeq, SimCommandType CommandType` |
| 3 | `CommandRejected` | 00 | `long CommandSeq, SimCommandType CommandType, CommandRejectReason Reason` |
| 100 | `WaveStarted` | 01 | 一波开始生成（`WaveId`） |
| 101 | `ThreatSpawned` | 01 | 敌方目标进入（`ThreatId, DefId, EntryId, WaveId`） |
| 102 | `MunitionReleased` | 01 | 平台投放弹药 / 母弹释放子弹药（`ParentThreatId, ThreatId`） |
| 103 | `ThreatArrived` | 01 | 到达目标点 / 投放点，移交落地结算（`ThreatId, Pos`） |
| 104 | `ThreatExited` | 01 | 离开地图或返航，不再参与（`ThreatId`） |
| 200 | `EarlyWarning` | 02 | 国家层预警（模糊；含弹道导弹发射预警，界面据此减速报警） |
| 201 | `TrackCreated` | 02 | 新航迹（`TrackId, Quality`） |
| 202 | `TrackQualityChanged` | 02 | 质量升降（`TrackId, From, To`） |
| 203 | `TrackLost` | 02 | 航迹丢失 / 删除（`TrackId`） |
| 204 | `DecoyIdentified` | 02 | 诱饵甄别成功（`TrackId`） |
| 205 | `EmitterSwitched` | 02 | 雷达开 / 关机（`UnitId, On, Cause`） |
| 206 | `ArmThreatDetected` | 02 | 反辐射导弹来袭预警（`TrackId, TargetUnitId`）；04 可据此发二选一 |
| 207 | `EwDiverted` | 02 | 导航干扰 / 欺骗使目标偏离或降档（`ThreatId, EwUnitId`） |
| 208 | `EwLinkCut` | 02 | 反无人机链路中断（`ThreatId, EwUnitId, Outcome`） |
| 209 | `ExposureThresholdCrossed` | 02 | 暴露度跨越阈值（`UnitId, Threshold, Rising`） |
| 210 | `DeceptionTriggered` | 02 | 欺骗单位吸引 / 被识破（`UnitId, ThreatId`） |
| 300 | `InterceptorLaunched` | 03 | 发射（`FireUnitId, LauncherIndex, WeaponId, InterceptorId, TrackId`） |
| 301 | `GunFired` | 03 | 身管武器一次射击（`FireUnitId, WeaponId, TrackId`） |
| 302 | `InterceptResolved` | 03 | 拦截判定（`InterceptorId?, ThreatId, Hit, Probability`；`AtSec` = 拦截时刻） |
| 303 | `InterceptorExpired` | 03 | 拦截弹失效 / 自毁 / 目标已消失（`InterceptorId, Cause`） |
| 304 | `EngagementHeld` | 03 | 有目标但未开火及原因（弹药保留、约束区、射程外……），供复盘 |
| 305 | `AmmoDepleted` | 03 | 某武器弹药耗尽（`FireUnitId, WeaponId`） |
| 306 | `ThreatImpacted` | 03 | 敌方弹药落地（`ThreatId, Pos, DamageLevel`） |
| 307 | `StructureDamaged` | 03 | 保护目标受损（`StructureId, HpBefore, HpAfter, SourceThreatId`） |
| 308 | `StructureDestroyed` | 03 | 保护目标被毁（`StructureId`） |
| 309 | `PlayerUnitDamaged` | 03 | 我方单位受损 |
| 310 | `PlayerUnitDestroyed` | 03 | 我方单位被毁（`UnitId, DefId, Kind`） |
| 311 | `DebrisFell` | 03 | 碎片落地（`Pos, StructureId?`） |
| 312 | `GridPowerChanged` | 03 | 电网节点通断（`GridNodeId, Powered`） |
| 313 | `AirRaidAlertChanged` | 03 | 警报拉响 / 解除（`On, Cause`） |
| 314 | `SupportRequested` | 03 | 呼叫外部支援（`SupportDefId, SupportAssetId`） |
| 315 | `SupportRefused` | 03 | 呼叫被拒绝（`SupportDefId, Reason`） |
| 316 | `SupportArrived` | 03 | 支援到位（`SupportAssetId`） |
| 317 | `SupportEnded` | 03 | 支援结束 / 返航（`SupportAssetId`） |
| 400 | `KnownTargetAdded` | 04 | 我方单位进入已知目标清单（`UnitId, Reason`） |
| 401 | `KnownTargetRemoved` | 04 | 移出清单 |
| 402 | `ChoiceRequested` | 04 | 二选一请求（`ChoiceId, ChoiceKey, DeadlineTick, DefaultOption`） |
| 403 | `ChoiceResolved` | 04 | 已回答或超时（`ChoiceId, Option, TimedOut`） |
| 404 | `CommandPointsChanged` | 04 | 指挥点变化（`Before, After`） |
| 405 | `UnitDeployStateChanged` | 04 | 我方单位部署状态变化（`UnitId, From, To`） |
| 406 | `StoryEventFired` | 04 | 剧情事件触发（`StoryEventId`） |
| 407 | `DialogueShown` | 04 | 剧情台词（`DialogueKey`） |

### 4.3 命令

```csharp
public abstract record SimCommand
{
    public int EffectiveTick { get; init; }   // ≤ 当前 Tick（含默认 0）⇒ 规范化为 Tick + 1（3.4.1）
    public long Seq { get; init; }            // Enqueue 分配；调用方传入的值被忽略
    public abstract SimCommandType Type { get; }
}
```

**命令总表**（字段由"处理者 / 规格"细化；是否消耗指挥点由 04 统一规定）：

| 值 | 命令 | 处理者 / 规格 | 含义（GDD 5.2） |
|---|---|---|---|
| 0 | `Noop` | 框架 / 00 | 无操作，永远接受（测试、回放填充） |
| 200 | `SetEmissionPolicy` | `EmissionSystem` / 02 | 修改单位的辐射策略 |
| 201 | `SectorEmissionOverride` | `EmissionSystem` / 02 | 扇区紧急静默 / 强制开机 / 取消 |
| 300 | `SetEngagementRule` | `EngagementSystem` / 03 | 切换交战规则（如 PAC‑3 只打弹道 / 放开交战） |
| 301 | `CallSupport` | `ExternalSupportSystem` / 03 | 呼叫外部支援（战斗机等） |
| 302 | `SetAirRaidAlert` | 03（宿主见 Q5） | 拉响 / 解除空袭警报（`bool On`） |
| 303 | `SetFighterZone` | `ExternalSupportSystem` / 03 | 划设 / 取消战斗机专区（GDD 8.9；是否可在夜间操作由 03 定） |
| 400 | `DeployUnit` | 04 | 夜间部署预备队单位（有展开时间） |
| 401 | `PackUnit` | 04 | 撤收 |
| 402 | `MoveUnit` | 04 | 调动机动单位（火力组、拦截无人机班组） |
| 403 | `RelocateUnit` | 04 | 紧急转移（仅展开时间按分钟计的系统） |
| 404 | `AnswerChoice` | 04 | 回答二选一（`int ChoiceId, int Option`） |

**拒绝原因**（`CommandRejectReason`，00 段为公共原因，其他规格可在本段之外追加）：

| 值 | 原因 | 含义 |
|---|---|---|
| 0 | `UnknownEntity` | 引用的实体 ID 不存在或已删除 |
| 1 | `WrongEntityKind` | 实体类型不符 |
| 2 | `InvalidState` | 实体当前状态不允许（如撤收中开火） |
| 3 | `InvalidArgument` | 参数非法（越界坐标、非法枚举……） |
| 4 | `NotAvailable` | 本关 / 本时期不可用 |
| 5 | `NoCommandPoints` | 指挥点不足 |
| 6 | `NotImplemented` | 处理者尚未实现（占位） |

---

## 5. 边界情况

| # | 情况 | 处理 |
|---|---|---|
| 1 | `Enqueue` 的 `EffectiveTick` ≤ 当前 `Tick`（含默认 0、负数） | 规范化为 `Tick + 1` |
| 2 | 同一步多条命令 | 按 `(EffectiveTick, Seq)`；后者看到前者的效果 |
| 3 | 命令指向已删除的实体 | `CommandRejected(UnknownEntity)`，状态不变 |
| 4 | `EffectiveTick > DurationTicks` 或夜晚提前结束时仍有未应用命令 | 永不应用，不报错；仍记录在命令日志与回放中 |
| 5 | 夜晚结束后 `Step()` / `Enqueue()` | `InvalidOperationException` |
| 6 | 同一步多个系统设置 `EndRequest` | 先设置者胜出 |
| 7 | 同一步既到时又满足失败条件 | `EndRequest` 优先（`Defeated`） |
| 8 | 同一步内实体被删除后又被后续系统查询 | `TryGet` 返回 false；需要写事件时用 `TryGetIncludingRemoved` |
| 9 | 同一实体在一步内被删除两次 | 第二次无操作，`RemovedTick` 保持第一次的值 |
| 10 | 遍历中创建同类实体 | 本循环不访问（`n` 固定） |
| 11 | ID 计数器溢出 | `InvalidOperationException`（终章规模远小于 2³¹） |
| 12 | `NextInt(min, max)` 中 `max ≤ min` | `ArgumentOutOfRangeException`，不消耗随机数 |
| 13 | `NextInt(5, 6)` | 返回 5，恰好消耗一次 `NextUInt32` |
| 14 | `Chance(p)` 中 `p ≤ 0` / `p ≥ 1` / `p` 为 NaN | 分别恒 false / 恒 true / 恒 false；都消耗一次 `NextDouble` |
| 15 | `Range(min, max)` 中 `min == max` | 返回 `min`，消耗一次 |
| 16 | 子流名为空串 | 合法（FNV 偏移基）；但子流表中不得出现 |
| 17 | 数据文件缺失 | `E_FILE_NOT_FOUND`，继续收集其他文件的错误 |
| 18 | JSON 语法错误 | `E_JSON_SYNTAX`（含行列），跳过该文件的其余校验（其交叉引用错误不报，避免连锁噪音） |
| 19 | 时期数组为空 | Schema 要求 `minItems: 1`；加载器报 `E_RANGE`（`取值 0 超出范围 minItems 1`） |
| 20 | 关卡日期恰为 `from` 所在月的 1 日 | 生效 |
| 21 | 高程图尺寸与地图尺寸不一致 | `E_RANGE`（1.5） |
| 22 | `DrainEvents()` 在 `Create` 之后、第一次 `Step()` 之前调用 | 返回 `[NightStarted]` |
| 23 | 读取 `Snapshot` 两次而中间无 `Step()` | 返回同一实例 |
| 24 | `SimConfig.RandomOverride` 非 null 时写回放 | 回放写入抛 `InvalidOperationException` |
| 25 | 回放数据哈希不一致 | `ReplayDataMismatchException`（`force` 时警告后继续） |
| 26 | `DurationTicks` 计算结果 < 1 | `SimSetupException` |

---

## 6. 不变量

### 6.1 运行时断言（`SimConfig.CheckInvariants = true` 时每步末尾检查）

1. 每个存储中实体 ID 严格升序；全部存储的 ID 互不相同；所有 ID `< State.Ids.NextId`。
2. 压缩后所有实体 `Alive == true` 且 `RemovedTick == -1`。
3. 所有实体 `CreatedTick ≤ State.Tick`。
4. 状态中所有 `double` 字段（含 `Vec2` 分量）为有限值（非 NaN、非 ±∞）。各规格的状态表在"不变量"中补充其字段的范围（如 `0 ≤ Exposure ≤ 100`）。
5. `State.Tick ≤ DurationTicks`；`IsFinished` ⇔ `Result != null`。
6. 事件 `Seq` 严格递增且连续（`DrainEvents` 拼接后无缺号）；每个事件 `Tick` 非递减。
7. `SimRandom._inc` 为奇数。
8. 读取 `Snapshot`、`DrainEvents()`、`ComputeStateHash()` 前后，`ComputeStateHash()` 结果不变。

### 6.2 代码约束（编译期 / 测试期）

`sim/BannedSymbols.txt`（`BannedApiAnalyzers` 格式；违者编译失败）：

```
T:System.Random;使用 SimRandom
P:System.DateTime.Now;非确定
P:System.DateTime.UtcNow;非确定
P:System.DateTime.Today;非确定
P:System.DateTimeOffset.Now;非确定
P:System.DateTimeOffset.UtcNow;非确定
M:System.Guid.NewGuid;非确定
P:System.Environment.TickCount;非确定
P:System.Environment.TickCount64;非确定
T:System.Diagnostics.Stopwatch;非确定（性能测量放 tools/bench）
T:System.Threading.Tasks.Parallel;禁止并行
T:System.Threading.Thread;禁止多线程
T:System.Threading.ThreadPool;禁止多线程
T:System.Threading.Tasks.Task;模拟层同步执行
T:System.Security.Cryptography.RandomNumberGenerator;使用 SimRandom
M:System.Math.FusedMultiplyAdd(System.Double,System.Double,System.Double);与 a*b+c 结果不同，禁止混用
T:System.MathF;只用 double
T:System.Numerics.Vector2;float 向量，使用 Vec2
T:System.Numerics.Vector3;float 向量
T:System.Numerics.Vector`1;SIMD 宽度依赖平台
T:System.HashCode;每进程随机化
M:System.String.GetHashCode;每进程随机化，使用 Fnv1a64
```

另需遵守（由代码审查与测试保证）：

1. 不以 `Dictionary` / `HashSet` 的遍历顺序作为逻辑依据（只做查找 / 成员判断）；需要遍历时用 `List`、排序数组或 `SortedDictionary` / `SortedSet`（比较器为序数比较）。
2. 字符串比较一律 `StringComparer.Ordinal` / `string.CompareOrdinal`；数字格式化 / 解析一律 `CultureInfo.InvariantCulture`。
3. 状态中不出现 `float`、`decimal`；不使用 `unsafe`。
4. 不手写 FMA 形式的"优化"；不使用 `System.Runtime.Intrinsics`。
5. `Math.Round` 必须显式传 `MidpointRounding`。
6. 系统不得持有静态可变状态；全部可变状态在 `SimState` 中。
7. 模拟层除 `Data/`（读数据）与 `Replay/`（读写回放）外不做文件 I/O，不读环境变量。

---

## 7. 测试用例

> 所有十六进制向量由 `simrandom_vectors.py` / `hasher_vectors.py` 计算（Python 参考实现，见待决问题之后的"附：参考脚本"）。测试数据均为手写小数据。

### RNG（WS01-002）

**T-00-01 PCG32 内核对照官方示例**
输入：直接以 `initState = 42, initSeq = 54` 执行 3.1.3 构造函数中的 `pcg32_srandom_r` 部分（测试用内部构造入口 `SimRandom.FromPcgSeed(42, 54)`）。
预期前 6 个 `NextUInt32`：`0xA15C02B7, 0x7B47F409, 0xBA1D3330, 0x83D2F293, 0xBFA4784B, 0xCBED606E`。

**T-00-02 SplitMix64 与 FNV‑1a 64**
- `SplitMix64Next(ref x)`，`x = 0`：输出 `0xE220A8397B1DCDAF`；再一次：`0x6E789E6AA1B965F4`。
- `Fnv1a64("") = 0xCBF29CE484222325`；`Fnv1a64("a") = 0xAF63DC4C8601EC8C`；`Fnv1a64("spawn") = 0x4328F78AB20E1F98`；`Fnv1a64("intercept") = 0x708A838B1F6CE3B5`。

**T-00-03 种子 → 前 5 个 `NextUInt32`**

| seed | 前 5 个输出 |
|---|---|
| `0` | `0x90644221, 0x4618E85F, 0x8F5BD9CD, 0xAF2C0306, 0xF6CD0B71` |
| `1` | `0x5249C5DC, 0x01959430, 0xE7976769, 0x57D21847, 0xEC099420` |
| `42` | `0xD11DD51F, 0xA9B04C45, 0xB5D97AA9, 0xA9EAB6CE, 0xF63FD201` |
| `0xDEADBEEF` | `0x249C431B, 0xCF8CB18E, 0xAF46EBC6, 0x1CA90B3E, 0x60A23D17` |
| `0xFFFFFFFFFFFFFFFF` | `0x4DF7FDF8, 0x74675B30, 0xA2F72031, 0x21AFFDBD, 0x328CC5C3` |

（中间值核对：seed `1` 的 `initState = 0x910A2DEC89025CC1`、`initSeq = 0xBEEB8DA1658EEC67`。）

**T-00-04 `NextUInt64` 与 `NextDouble`**

| seed | 前 3 个 `NextUInt64` | 前 3 个 `NextDouble`（逐位相等，`==` 比较） |
|---|---|---|
| `0` | `0x906442214618E85F, 0x8F5BD9CDAF2C0306, 0xF6CD0B71A19AB615` | `0.5640298205599695, 0.5599952819022036, 0.964066233865746` |
| `1` | `0x5249C5DC01959430, 0xE797676957D21847, 0xEC0994207EFB0D93` | `0.3214381849407657, 0.9046539909539394, 0.922021158155058` |
| `42` | `0xD11DD51FA9B04C45, 0xB5D97AA9A9EAB6CE, 0xF63FD2019D8FEFEB` | `0.8168614580442305, 0.7103497184961423, 0.9619113210624729` |

（每组 `NextDouble` 用新建的同种子实例。）

**T-00-05 `NextInt` 序列**（每列新建同种子实例，各取 10 个）

| seed | `NextInt(0, 10)` | `NextInt(-5, 5)` | `NextInt(0, 3)` |
|---|---|---|---|
| `0` | `3,1,1,8,5,3,4,5,5,1` | `-2,-4,-4,3,0,-2,-1,0,0,-4` | `1,1,2,0,2,2,2,2,0,1` |
| `1` | `2,6,5,7,0,7,8,3,5,7` | `-3,1,0,2,-5,2,3,-2,0,2` | `2,1,2,2,2,0,2,1,2,2` |
| `42` | `7,5,9,6,5,9,1,8,1,7` | `2,0,4,1,0,4,-4,3,-4,2` | `2,1,2,2,1,0,1,0,0,1` |

**T-00-06 无偏差取整的拒绝分支**
`Bounded(range: 3, next: 依次返回 [0, 1])`：`threshold = (2³² − 3) mod 3 = 1`；第一个值 0 < 1 被拒绝，第二个值 1 接受 → 返回 `1 % 3 = 1`，共调用 `next` 2 次。
`Bounded(range: 10, next: [5, 6])`：`threshold = 6`；5 被拒，6 接受 → 返回 `6`。
`Bounded(range: 1, next: [0xFFFFFFFF])` → 返回 0，调用 1 次。

**T-00-07 参数与消耗**
- `NextInt(5, 5)`、`NextInt(5, 4)` 抛 `ArgumentOutOfRangeException`，之后 `NextUInt32()` 与未调用时相同。
- seed 1：`NextInt(5, 6)` 返回 5；随后 `NextUInt32()` = `0x01959430`（证明恰好消耗一次）。
- seed 1 新实例：`Chance(0)` 返回 false、`Chance(1)` 返回 true；随后 `NextUInt64()` 必须等于 T-00-04 中 seed 1 的**第 3 个**值 `0xEC0994207EFB0D93`（两次 `Chance` 各恰好消耗一次 `NextDouble` = 两个 `NextUInt32`）。
- 任意实例：`Chance(double.NaN)` 返回 false。

**T-00-08 子流派生向量**（根 seed = 1；全部 3.1.4 子流）

| 子流名 | `ChildSeed(1, 名)` | 子流前 3 个 `NextUInt32` |
|---|---|---|
| `setup` | `0x83016B1BF7A6CC04` | `0x75A09F26, 0xF09090BC, 0xA77AF880` |
| `command` | `0xC4D789363E64FADD` | `0xD868D361, 0xFD7B5DEF, 0x7D0F991A` |
| `spawn` | `0x247FD80E4FD86BD1` | `0x3F223FCE, 0x72F5159C, 0xAB0AC575` |
| `movement` | `0x793B80FD5AE18AC6` | `0xCF5A9749, 0x5B539D73, 0x03221EC2` |
| `sensor` | `0xEDA6E1A5EBB04BFC` | `0xEBD79AFA, 0x29F41534, 0xE6FB224E` |
| `fusion` | `0x96BC36F0E16CCB80` | `0xF69CD22D, 0x4BB10F87, 0x6DCC86FA` |
| `ew` | `0xB367DB5DFA5E020B` | `0xAC0F589E, 0x71C7CD73, 0x3B41E853` |
| `emission` | `0xD2942CAECC22C8AA` | `0xC8F4D9F5, 0x9C717F9A, 0x5698AB4E` |
| `engagement` | `0xA32E81D369DE6FE5` | `0x5098CDE5, 0x45DC9F1C, 0xC2ADC3F8` |
| `intercept` | `0x3FCF8184E343749C` | `0xC4B39A4F, 0x0731B85D, 0x8312946F` |
| `support` | `0x2484FDDC722E8093` | `0x97D30FBE, 0xD60CC280, 0x0B187A53` |
| `impact` | `0xD87469420706C63D` | `0xC07EB9FA, 0xFD8437EF, 0x4F5F6421` |
| `exposure` | `0xF88583C05CF5FFCA` | `0x7BC2CD37, 0x1D488B45, 0xFF431DC2` |
| `enemy_ai` | `0xD3DFA39460ABC9A1` | `0x64D978DC, 0x781860D1, 0x55A0C437` |
| `scoring` | `0x75D4D178DA2D89C3` | `0x4258D618, 0x89EDD2A4, 0x4002CDB5` |
| `civil` | `0xCEA91EEB942D54E9` | `0xE5EDFFC0, 0x6ACCAE05, 0xACAA8BE8` |
| `environment` | `0x1E3144E56455EE94` | `0xB7C590F2, 0x8E19A029, 0x08CEEDEA` |
| `crew` | `0x205BA603E1FCB805` | `0x7BE1DBCA, 0xD8835427, 0xA152C83A` |

嵌套：`new SimRandom(1).Derive("intercept").Derive("e42")` 的 `Seed = 0xCB468B9271533E47`，前 3 个输出 `0x0869DFE2, 0x1F3EE24C, 0x3A0BBDB0`。

**T-00-09 子流独立**
根 seed 1。实例 A：派生 `spawn` 并消耗 1000 个 `NextUInt32`，再派生 `intercept` 取第一个值；实例 B：直接派生 `intercept` 取第一个值。两者都等于 `0xC4B39A4F`。另：父流在调用 `Derive` 前后的 `NextUInt32` 序列不变（seed 1：派生 5 个子流后父流第一个输出仍为 `0x5249C5DC`）。

**T-00-10 夜晚种子**
`NightSeed(0, "test_01", 1) = 0x3ED2DE67F24D80CD`；`NightSeed(1, "test_01", 1) = 0x6DD180096484586D`；`NightSeed(1, "test_01", 2) = 0x92C4A19D40D3C63D`；`NightSeed(12345, "l07", 3) = 0x7B78FE8FA9400AAF`。

**T-00-11 状态保存 / 恢复**
seed 42：取 3 个输出后 `s = GetState()`；再取 5 个记为 X；`SetState(s)` 后再取 5 个，必须等于 X。

### 单位与几何

**T-00-12 加载换算**（`conventions`：`gameSecToWorldSec = 60, worldStepSec = 1, cellKm = 1, machKmh = 1200`）

| 输入 | 预期 |
|---|---|
| `rangeKm: 6.5` | `RangeM == 6500.0` |
| `deployGameSec: 2` | `DeploySec == 120.0` |
| `speedKmh: 180` | `SpeedMps == 50.0` |
| `speedKmh: 500` | `SpeedMps == 138.88888888888889` |
| `splashCells: 0.5` | `SplashM == 500.0` |
| `ratesPerGameSec: { "x": 1.5 }` | `RatesPerSec["x"] == 0.025` |
| `altitudeM: { min: 30, max: 70 }` | `AltitudeM == MinMax(30, 70)` |
| `Units.MachToMps(2, conventions)` | `666.6666666666666` |

另一组：`cellKm = 2` 时 `splashCells: 0.5` → `SplashM == 1000.0`（证明系数来自数据）。`worldStepSec = 2` → `[E_RANGE] rules/conventions.json $.worldStepSec: 取值 2 超出范围 必须等于 1`。

**T-00-13 时间取整**
`SecToTicksCeil(6.000000000000001, 1) == 6`；`SecToTicksCeil(6.0000001, 1) == 7`；`SecToTicksCeil(0, 1) == 0`；`SecToTicksCeil(28800, 1) == 28800`；`SecToTicksFloor(5.999999999999999, 1) == 6`；`SecToTicksFloor(5.5, 1) == 5`；`SecToTicksCeil(-1, 1)` 抛 `ArgumentOutOfRangeException`。

**T-00-14 方位角**
从 `(0,0)`：到 `(0,10)` → `0.0`；到 `(10,0)` → `1.5707963267948966`；到 `(0,-10)` → `3.141592653589793`；到 `(-10,0)` → `4.71238898038469`；到 `(10,10)` → `0.7853981633974483`；到 `(0,0)` → `0.0`。`Normalize(-3.141592653589793) == 3.141592653589793`；`Normalize(2π) == 0.0`。

### 实体存储（WS01-003）

**T-00-15 ID 分配顺序**
小关卡：电网节点 `[g1, g2]`、保护目标 `[s1, s2, s3]`、部署方案 2 个单位 `[火力单元 f1, 探测单位 r1]`，所有系统 `Initialize` 不建实体。
预期：`g1=1, g2=2, s1=3, s2=4, s3=5, f1=6, r1=7`；`State.Ids.NextId == 8`；`StructureIdByDefId["s2"] == 4`。

**T-00-16 标记删除与压缩**
在测试系统（Order 1 位置的替身）中第 1 步：向 `Threats` 加 3 个（ID a<b<c），删除 b。同一步内由 Order 2 替身检查：`TryGet(b)` 为 false、`TryGetIncludingRemoved(b)` 为 true 且 `RemovedTick == 1`、`Count == 3`、遍历只访问 a、c。步后：`Count == 2`。第 2 步新加一个，其 ID 为 `c + 1`（不重用 b）。

**T-00-17 遍历中新增**
存储中已有 2 个实体；在遍历循环中对每个实体各 `Add` 一个新实体。预期：循环体执行 2 次；循环结束后 `Count == 4`；后续系统可看到 4 个。

### 命令（WS01-003 / 01.C）

**T-00-18 生效时刻规范化与顺序**
空世界（`Tick = 0`）：
- `Enqueue(Noop{EffectiveTick = 0})` 返回 `EffectiveTick == 1, Seq == 1`。
- `Enqueue(Noop{EffectiveTick = 3})` → `Seq == 2`；`Enqueue(Noop{EffectiveTick = 2})` → `Seq == 3`；`Enqueue(Noop{EffectiveTick = 2})` → `Seq == 4`。
- 连续 `Step()` 3 次，`DrainEvents()` 中 `CommandApplied` 依次为：`(Tick 1, CommandSeq 1)`、`(Tick 2, CommandSeq 3)`、`(Tick 2, CommandSeq 4)`、`(Tick 3, CommandSeq 2)`。
- 在 `Tick = 3` 时 `Enqueue(Noop{EffectiveTick = 2})` → 规范化为 `4`。

**T-00-19 命令拒绝**
注册测试处理者：`TestCommand{ int TargetId }`，`Validate` 在 `TryGet(TargetId)` 失败时返回 `UnknownEntity`。入队 `TargetId = 999`。预期：第 1 步事件含 `CommandRejected{CommandSeq = 1, Reason = UnknownEntity}`，无 `CommandApplied`；第 1 步后状态哈希等于"未入队任何命令、同样 Step 一次"的世界的哈希。

### `SimWorld`（WS01-003）

**T-00-20 空世界推进 N 步**
迷你关卡：无波次、`durationGameSec = 10`（→ 600 步）、`EndWhenClear = false`，空部署。
- `Create` 后：`Tick == 0`、`DurationTicks == 600`、`DrainEvents()` = `[NightStarted{NightIndex 1, DurationTicks 600}]`（`Seq 1, Tick 0`）。
- `Step()` 599 次：`IsFinished == false`、`Tick == 599`。
- 第 600 次：`IsFinished == true`、`Result.EndReason == DurationElapsed`、`Result.Outcome == Survived`、`Result.EndTick == 600`；最后一个事件为 `NightEnded{EndTick 600}`，`Seq == 2`（空世界无其他事件）。
- 再 `Step()` 抛 `InvalidOperationException`。

**T-00-21 系统顺序**
用 `RecordingSystem` 包装（测试构造入口允许替换系统实现但不允许改变 Order 表）。`Create` 后记录 = 14 个 `Initialize`，`Name` 依次为 3.3 表顺序；`Step()` 两次后记录追加 `Execute` × 28，每步顺序同 3.3 表；每个系统收到的 `ctx.Rng.Seed` 等于 `ChildSeed(seed, 该系统子流名)`（EventLog 为 null）。

**T-00-22 `EndWhenClear` 与失败优先**
- 迷你关卡、无波次、`EndWhenClear = true`：第 1 步结束即 `AllClear`（`AllWavesSpawned` 为 true 且无目标），`EndReason == AllClear`、`EndTick == 1`。
- 测试系统在第 5 步设置 `EndRequest(Defeated, DefeatCondition)`，且 `DurationTicksOverride = 5`：结果为 `Defeated / DefeatCondition`。

**T-00-23 事件序号与 `DrainEvents`**
测试系统每步发 2 个事件。`Step()` 3 次后一次 `DrainEvents()`：共 7 个事件（含 `NightStarted`），`Seq` 为 1…7 连续，`Tick` 依次 `0,1,1,2,2,3,3`；再调 `DrainEvents()` 返回空列表。

### 确定性与回放（WS01-020）

**T-00-24 `StateHasher` 编码向量**

| 写入序列 | 字节（十六进制） | 哈希 |
|---|---|---|
| （无） | — | `0xCBF29CE484222325` |
| `Write(7)` | `07000000` | `0x6D3572669B2CDE42` |
| `Write(1.5)` | `000000000000f83f` | `0xAA95E93229A27C80` |
| `Write(-0.0)` | `0000000000000000` | `0xA8C7F832281A39C5`（与 `Write(0.0)` 相同） |
| `Write("ab")` | `020000006162` | `0x9254FD600693E9A0` |
| `Write((string?)null)` | `ffffffff` | `0x994F76653E2A3951` |
| `Write(7); Write(1.5); Write("ab"); Write(true); Write(0xDEADBEEFUL)` | `07000000000000000000f83f02000000616201efbeadde00000000` | `0x461DC66E88FEC47B` |

**T-00-25 同种子同命令 → 1000 步哈希逐步一致**
迷你关卡（含 1 个进入点、1 波 3 个手写敌方目标、1 个火力单元；各系统实现到当时进度即可）、`DurationTicksOverride = 1000`、`EndWhenClear = false`、seed `0x6DD180096484586D`，命令：第 10 步 `Noop`、第 500 步 `Noop`。两个独立世界各 `Step()` 1000 次，每步 `ComputeStateHash()` 相等（1000 对）。另一个世界只把 seed 改为 `0x92C4A19D40D3C63D`：`Tick 0` 的哈希即不同（子流状态参与哈希）。

**T-00-26 只读访问不影响哈希**
同 T-00-25 设置，世界 A 每步读取 `Snapshot` 并 `DrainEvents()`，世界 B 从不读取。1000 步内每步哈希相等。

**T-00-27 快照不可变**
第 1 步后取 `snap1`，记录 `snap1.Threats` 的内容；再 `Step()` 若干步；`snap1` 的 `Tick` 与数组内容不变；`Snapshot` 在两次 `Step()` 之间多次读取返回同一实例（`ReferenceEquals`）。

**T-00-28 回放往返**
运行 T-00-25 的世界并写回放文件（`checkpointInterval = 100`）；用 `ReplayRunner` 重放：通过，`final.hash` 相等。篡改回放中 `dataHash` 的一个字符 → `ReplayDataMismatchException`。把 `commands[0].effectiveTick` 从 10 改为 11 → 在 tick 100 的检查点抛 `ReplayDivergedException(100, …)`（`Noop` 不改变实体状态，但 `CommandApplied` 事件的 `Tick` 改变 ⇒ 事件流哈希改变 ⇒ 状态哈希改变）。

### 数据加载（WS01-004）

**T-00-29 缺字段错误信息**（`InMemoryDataSource`，`units/air_defense.json` 中第 0 个单位的第 0 个武器删去 `rangeKm`，其余文件为最小合法夹具）
`DataLoadException.Errors` 恰好 1 条，`ToString()` 精确等于：
`[E_MISSING_FIELD] units/air_defense.json $.units[0].weapons[0].rangeKm: 缺少必填字段`

**T-00-30 类型、枚举、未知字段、忽略字段**
- `"rangeKm": "6"` → `[E_TYPE] units/air_defense.json $.units[0].weapons[0].rangeKm: 期望 number，实际 string`
- `"mobility": "boat"` → `[E_ENUM] units/air_defense.json $.units[0].mobility: 非法取值 "boat"，允许：vehicle, towed, portable, fixed`
- 多一个字段 `"rangKm": 1` → `[E_UNKNOWN_FIELD] units/air_defense.json $.units[0].weapons[0].rangKm: 未知字段`
- 含 `$schema`、`_source`、`provisional: {"weapons[0].interceptClass": "暂定"}` → 无错误；`ProvisionalPaths` 含 `units/air_defense.json#weapons[0].interceptClass`。
- 三个错误同时存在时，`Errors` 按出现顺序全部列出（3 条）。

**T-00-31 交叉引用与语法错误**
- `waves.json` 的 `groups[0].enemy = "nope"`（关卡 ID `mini`）→ `[E_UNKNOWN_REF] levels/mini/waves.json $.nights[0].waves[0].groups[0].enemy: 引用的 敌方单位 "nope" 不存在`
- `grid.json` 内容为 `{ "kind": "grid", "nodes": [ }` → 1 条 `E_JSON_SYNTAX`，`File == "levels/mini/map/grid.json"`、`JsonPath == "$"`，`Detail` 以 `JSON 语法错误（第 1 行，第 ` 开头；不再报告依赖 grid 的 `E_UNKNOWN_REF`。
- 两个单位共用武器 `w1`，第二处 `rangeKm` 不同 → 1 条 `E_SHARED_WEAPON_MISMATCH`，路径指向第二处武器对象（`$.units[1].weapons[0]`）。

**T-00-32 periodValue 解析**
手写 `rules/intercept.json`：`classes.k.BM = [{from:"2022-02", value:0.75}, {from:"2025-08", value:0.55}]`，`classes.k.CM = 0.9`。

| 关卡日期 | `BM` | `CM` |
|---|---|---|
| `2025-07-31` | `0.75` | `0.9` |
| `2025-08-01` | `0.55` | `0.9` |
| `2030-01-01` | `0.55` | `0.9` |
| `2022-01-15` | 错误：`[E_PERIOD_BEFORE_FIRST] rules/intercept.json $.classes.k.BM: 关卡日期 2022-01-15 早于第一个时期 2022-02` | — |

`from` 顺序为 `2025-08, 2022-02` → `[E_PERIOD_ORDER] rules/intercept.json $.classes.k.BM: 时期数组的 from 必须严格升序`。

**T-00-33 时期表与闸门**
- `ew.effectivenessByPeriod = [{from:"2022-02", nav:1.0, counterUas:1.0}, {from:"2022-10", nav:0.7, counterUas:1.0}]`：日期 `2022-11-15` → `Nav == 0.7`；`2022-09-30` → `Nav == 1.0`。
- 武器 `targets:["UAV"], targetsFrom:[{tag:"JET_UAV", from:"2026-09"}]`：日期 `2026-08-31` → `Targets == [UAV]`；`2026-09-01` → `Targets == [UAV, JET_UAV]`。
- 弹药 `accuracy:"C", accuracyByPeriod:[{from:"2024-01", tier:"B"}]`：`2023-12-31` → `C`；`2024-01-01` → `B`。
- `historicalEvents: [{id:"e", until:"2023-04", ...}]`：`2023-03-31` → `Active == true`；`2023-04-01` → `false`。

**T-00-34 高程图解码**
手写 2×2 16 位灰度 PNG（过滤器：第 0 行 None、第 1 行 Up），像素（行主序，北行在前）`[0, 65535; 32768, 0]`，`minElevationM = 100, maxElevationM = 300`，`metersPerPixel = 10`，地图 `20 × 20` m。
预期 `ElevationM == [100.0, 300.0, 200.00152590218966, 100.0]`。8 位灰度 PNG → `E_PNG_FORMAT`；地图写成 `40 × 20` m → `E_RANGE`。

**T-00-35 正式样例数据可加载**（集成测试，读仓库 `data/`）
`LoadLevel(FileSystemDataSource(<repo>/data), "test_01")` 不抛异常；`Meta.Map.WidthM == 20000`；`Waves.Nights[0].DurationSec == 28800`；`Waves.EntryPoints.Count == 2`；`Heightmap.WidthPx == 200 && HeightPx == 200`；`Date == 2022-11-15`；`LoadedFiles.Count == 29`（20 个全局 + 8 个关卡 JSON + 1 个 PNG）；`DataHash` 以 `sha256:` 开头且长度 71。（只断言结构，不断言具体平衡数值。）

**T-00-36 夜晚不存在**
迷你关卡只有第 1 夜，`SimConfig.NightIndex = 2` → `SimSetupException`，消息为 `[E_NIGHT_NOT_FOUND] levels/mini/waves.json $.nights: waves.json 中没有第 2 夜`。

### 架构

**T-00-37 不引用 Godot**
0.5 节三道检查全部通过；人为在测试夹具字符串中构造 `using Godot;` 的源文件文本，扫描函数能识别（自检扫描器有效）。

---

## 8. 待决问题

| # | 问题 | 背景 | 建议默认值 |
|---|---|---|---|
| Q1 | 多夜关卡（时间结构 C / E，跨 2–10 周）随时期变化的数值按哪个日期解析？ | `level.json` 只有 `dateRange`，`waves.json` 的夜晚没有日期 | 整关使用 `dateRange.from`；若需要每夜不同，给 `waves.json` 的 `nights[]` 增加可选 `date` 字段，加载时按夜解析 |
| Q2 | 所有波次生成完毕、场上无目标时，夜晚是否提前结束？ | GDD 11.2 只说"无来袭目标时自动快进 8×"；WBS 未定义 | `SimConfig.EndWhenClear = true`（提前结束，结局 `Survived / AllClear`）；若希望夜晚总是跑满时长，改默认为 false |
| Q3 | 失败条件（`weighted_damage_at_least`、`grid_collapse`、`structure_destroyed`）达成时是否立即结束当夜？ | `level.json` 只列条件，未说何时判定 | 立即结束，`Defeated / DefeatCondition`（由 03 的 `ScoringSystem` 设置 `EndRequest`） |
| Q4 | 胜利条件 `survive_game_sec` 与 `waves.json` 的 `durationGameSec` 是什么关系？ | 两处都表示时长 | 夜内时长只以 `durationGameSec` 为准；`survive_game_sec` 由关卡层（05）判定；二者同时存在时加载器检查 `gameSec ≤ 各夜 durationGameSec 之和`，否则 `E_RANGE` |
| Q5 | WBS 01.B 的 14 个系统之外的功能放在哪一步？ | 命令应用、二选一超时、剧情事件、空袭警报、电网传播、天气、班组没有槽位 | 命令应用 / 二选一超时 / 剧情事件：阶段 0（本文件 3.4）；电网传播：`ImpactSystem`（10，WBS 原文含"电网连锁"）；空袭警报：状态切换在阶段 0（命令），效果在 `ScoringSystem`（13）累计；天气：每夜静态，`Create` 时读入；班组：每夜静态，经 `CarryIn` 带入。**阶段 0 是对 01.B 的补充（不改变 1–14 的顺序），需确认** |
| Q6 | `…Pct` 后缀（`rules/damage.json` 的 `gridDamagePct`）不在 data/README 的换算表中 | 加载器需要统一规则 | 加载时 `÷ 100`，C# 字段名改为 `…Frac`；同时在 data/README 第 2 节补一行 |
| Q7 | 我方单位的部署 / 撤收 / 移动状态机由哪个规格负责？ | README 的规格分工未列出 | 04（与 `DeployUnit / PackUnit / MoveUnit / RelocateUnit` 命令同处）；展开 / 撤收时长读各单位定义 |
| Q8 | 方位角约定 | 任务要求选一个写死 | 已选"从正北顺时针、弧度 `[0, 2π)`"（贴合军事习惯与指挥层界面）；如需改为数学角请在实现前提出 |
| Q9 | 回放是否需要跨平台（Windows x64 ↔ macOS arm64）一致？ | WBS 01.A："回放只保证同平台一致" | 维持同平台；回放文件记录 `runtime`，不同时警告。若将来需要跨平台，须改为自带确定性三角函数实现（影响 01 / 03） |
| Q10 | `runSeed` 由谁生成、存在哪里？ | WBS 只说"种子来自关卡 + 夜晚序号"，缺少每局战役的变化来源，否则每局都一样 | 05 在新战役时生成（模拟层外，可用系统随机源）并写入存档；每夜 `seed = NightSeed(runSeed, levelId, nightIndex)` |
| Q11 | "自动结算"（GDD 11.5）"略逊于亲自指挥"如何体现？ | 涉及 `SimConfig` 是否需要一个惩罚参数 | 不在 00 中处理；05 规定（建议通过 `CarryIn` 或专门的 `SimConfig.AutoResolve` 修正项，数值进 `rules/`） |
| Q12 | 快照是否包含敌方目标真值？ | 界面应只显示航迹（战争迷雾），但复盘 / 调试需要真值 | 包含（`SimSnapshot.Threats`），06 规定正常界面不得渲染，仅调试开关 / 复盘可见 |
| Q13 | 事件输出缓冲是否设上限？ | 无画面批量运行若不 Drain 会累积 | 不设上限；`tools/simrun` 与客户端每帧 / 每步 Drain |
| Q14 | 加载器对未知字段是否报错？ | Schema 为 `additionalProperties: false`；但严格加载会让"先改数据、后改代码"变难 | 报错（`E_UNKNOWN_FIELD`），与 Schema 一致 |
| Q15 | `events.json` 剧情事件由哪个规格 / 系统执行？ | 触发（结构被毁、波次生成等）与动作（台词、追加波次、二选一、警报）跨多个系统 | 04 负责，在阶段 0 读取 `PreviousStep` 事件判断触发；`spawn_wave` 动作写入 `WaveState` 由 01 下一步生成 |
| Q16 | `Debris` 是否需要成为持续存在的实体？ | GDD 16.4 把碎片列为实体，但数值表 3.6 的规则可能只需瞬时结算 | 保留 `EntityKind.Debris` 槽位；03 决定是否使用（不用则保持空存储） |
| Q17 | 夜间是否允许部署预备队（`DeployUnit`）？ | GDD 5.2 列出"调动机动单位"和"紧急转移"，未列"新部署" | 保留命令；是否允许、是否耗指挥点由 04 决定（默认：不允许，拒绝 `NotAvailable`） |

---

### 附：参考脚本

- `/Users/xtxsinan/.gemini/antigravity/brain/3c71df62-d91b-4de5-a3dc-5b43867948d8/scratch/simrandom_vectors.py`：`SimRandom` 的 Python 参考实现（含 PCG32 官方示例自检、SplitMix64 自检、全部子流种子），T-00-01 – T-00-10 的数值均由它输出。
- `/Users/xtxsinan/.gemini/antigravity/brain/3c71df62-d91b-4de5-a3dc-5b43867948d8/scratch/hasher_vectors.py`：`StateHasher` 编码与 FNV‑1a 向量（T-00-24）。

实现 `SimRandomTests` 时，可以把脚本输出的全部子流种子（含 `setup`、`command`、`civil`……）补进 T-00-08 的表中。
