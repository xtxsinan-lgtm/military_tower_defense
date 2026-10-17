# 01 波次生成、敌方移动、地形与视线

> 覆盖 `SimWorld.Step()` 的第 1 步 `WaveSpawnSystem`、第 2 步 `EnemyMovementSystem`，以及供其他系统调用的地形服务 `TerrainModel`（高程采样、视线、多山脊遮挡包络）和敌方运动学接口 `ThreatKinematics`（解析位置预测，供 03 的解析拦截使用）。
> 术语、类型、子流、事件 / 命令名称以 [00_core.md](00_core.md) 为准；本文件登记到 `00_core.md` 的名字与规则已全部并入 `00_core.md`（见第 8.2 节登记清单）。

---

## 0. 范围与依据

### 0.1 覆盖范围

| 主题 | 本文件章节 | 对应 WBS |
|---|---|---|
| 波次时间表、组内间隔、注入波次（剧情 `spawn_wave` 与 04 压制波放行） | 3.1 | WS01-005（生成部分）、WS01-019 的接口 |
| 进入点、航线（`direct` / `waypointsM` / `template`）、目标选择（`structure` / `weighted_random` / `known_targets` / `air_defense` / `decoy_flight`） | 3.1.4 – 3.1.7 | 同上 |
| 平台（`platforms.json`）生成、挂载选择、投放时机（`releaseRangeKm`、`standoffFrom`）、返航；不进入地图的波次源（`strategic_bomber`） | 3.1.8、3.2.6 | WS01-005 |
| 航点跟随、高度剖面（12 种 `altitudeBand`）、末段下降、俯冲加速、弹道 / 准弹道 / 末端机动、滑翔、无制导投弹 | 3.2 | WS01-005 |
| 到达目标（`ThreatArrived`）、离开地图（`ThreatExited`）、悬停、改航 / 返航 / 悬停接口、反辐射导弹归航接口 | 3.2.5、3.2.8 | WS01-005 |
| 解析位置预测 `ThreatKinematics.Predict` / `Legs` / `MaxSpeed3DMps` | 3.2.9 | WS01-005（供 WS01-010） |
| 高程采样（双线性、像素中心、地图外）、视线（采样步长、地球曲率）、多山脊遮挡包络 `HorizonProfile`、缓存与性能 | 3.3 | WS01-006 |

**不**在本文件：探测概率与传感器参数（02）、电子战决定是否改航（02，本文件只提供改航 / 返航 / 悬停接口）、反辐射导弹何时归航（02）、拦截解算与命中（03）、落地伤害（03）、敌方 AI 选择已知目标 / 绕开防空圈 / 压制 / 饱和的算法（04，本文件只定义调用点和接口 `IEnemyAiHooks`）。

### 0.2 依据

- [AGENTS.md](../../AGENTS.md) 第 3、4、8 节（确定性、坐标与高度约定、"快速目标解析计算拦截时刻"）
- [WBS](../开发任务分解_WBS_v1.md) 01.A（世界秒、1 秒一步、米制坐标、高度相对地面）、01.B（系统顺序）、WS01-005、WS01-006、WS01-019、WS01-028、WS02-004
- [GDD](../游戏设计文档_GDD_v1.md) 7.1、7.3、7.4（试探 / 压制 / 猎杀 / 绕行 / 饱和）、8.1（"地形和地平线形成低空盲区"）、8.3（电子战"把打向电厂的 Shahed 引到空地上"）、8.8（天气与昼夜）、11.2（时间比例）
- [数值表](../塔防数值表_v1.md) 2.1（速度、飞行高度）、2.2（滑翔炸弹投放距离）、2.3（平台行为、携带）、5.1（"飞行高度剖面保留区间"）、5.2（滑翔炸弹 600 km/h）
- `data/schema/waves.schema.json`、`enemy_munition.schema.json`、`enemy_platform.schema.json`、`map.schema.json`、`level.schema.json`
- `data/levels/test_01/`（地图 20 × 20 km、东北山脊，生成脚本 `tools/testmap/gen_test01_heightmap.py`）

### 0.3 依赖

- 只依赖 [00_core.md](00_core.md)（实体存储、`SimRandom`、子流 `spawn` / `movement`、事件 100–104、`LevelData`、`Heightmap`、`SimTime`、`Vec2`、`Geo`）。
- 本文件**向后**提供接口（被 02 / 03 / 04 调用），并**向后**声明由 04 实现的 `IEnemyAiHooks` 钩子（3.1.2、3.1.6、3.1.9）；钩子在 04 未注入自定义实现时使用本文件给出的 `DefaultEnemyAiHooks`。

### 0.4 天气与昼夜

天气（`NightDef.Weather`）、季节、昼夜**不影响**任何敌方目标的生成与移动（速度、高度、航线都不变）；它们只影响探测（02）与交战（03）。

---

## 1. 数据输入

### 1.1 `waves.json`（00 已定义类型，本节补充用法）

| JSON 字段 | 单位 | 加载后（C#） | 本文件用法 |
|---|---|---|---|
| `entryPoints[].id` | — | `EntryPointDef.Id` | `Threat.EntryId` |
| `entryPoints[].positionM` | m | `EntryPointDef.Pos`（`Vec2`） | 生成位置；平台返航终点。可在地图外 |
| `entryPoints[].warningGameSec` | 游戏秒 | `EntryPointDef.WarningSec`（×60） | 不用（02 的国家预警） |
| `nights[].night` | — | `NightDef.Night` | 按 `SimConfig.NightIndex` 选夜（00 3.2） |
| `nights[].weather` / `season` | — | `NightDef.Weather` / `Season` | 不用（0.4） |
| `waves[].id` | — | `WaveDef.Id` | `WaveStarted.WaveId`、`Threat.WaveId` |
| `waves[].atGameSec` | 游戏秒 | `WaveDef.AtSec`（×60） | 本波第一个目标的生成时刻（相对夜晚开始，即 `TimeSec`） |
| `waves[].aiTags` | — | `WaveDef.AiTags`（`AiTag[]?`） | 原样写入 `WaveStarted.AiTags`；`suppress`、`saturate`、`bypass` 经 3.1.2 / 3.1.5 / 3.1.9 的 `IEnemyAiHooks` 与 04 配合（A-2-10，见 8.1 Q11） |
| `groups[].enemy` | — | `WaveGroupDef.EnemyId` | 弹药 ID 或平台 ID（二者 ID 互不重复，00 1.2 第 13 条） |
| `groups[].count` | 个 | `WaveGroupDef.Count`（`int ≥ 1`） | 本组生成次数（平台为架数） |
| `groups[].entry` | — | `WaveGroupDef.EntryId` | 进入点 |
| `groups[].spacingGameSec` | 游戏秒 | `WaveGroupDef.SpacingSec`（×60，`double?`） | 组内相邻两次生成的间隔；**缺省 = 0**（同一时刻全部生成） |
| `groups[].route` | — | `RouteDef(Kind, TemplateId, Waypoints)` | 3.1.5 |
| `groups[].target` | — | `TargetSpecDef(StructureId, Mode)` | 3.1.6 |

### 1.2 `enemies/munitions.json` → `MunitionDef`（移动相关字段，全字段由 01、02、03 共同定义，完整声明见 `00_core.md` 1.6）

| JSON 字段 | 单位 | C# 字段 | 类型 | 本文件用法 |
|---|---|---|---|---|
| `id` | — | `Id` | `string` | `Threat.DefId` |
| `category` | — | `Category` | `MunitionCategory` | 只用于 3.2.2 的 `Carrier` 判定之外的说明；移动规则只看 `AltitudeBand` |
| `tag` | — | `Tag` | `TargetTag?` | 复制到 `Threat.Tag`；用于 3.1.5 / 3.1.9 绕行钩子 |
| `firstSeen` | 年月 | `FirstSeen` | `YearMonth?` | 不用（00 1.4 形态 A，供 `tools/validate` 与历史模式校验，C-T2-08） |
| `speedKmh` | km/h | `SpeedMps` | `double?`（÷3.6） | 水平速度；`null` 只允许 `altitudeBand = carrier`（8.2 校验 V2） |
| `diveFaster` | — | `DiveFaster` | `bool?`（缺省 = false） | 末段速度 × `rules.movement.diveSpeedMult` |
| `altitudeBand` | — | `AltitudeBand` | `AltitudeBand` | 选择运动剖面（3.2.2） |
| `altitudeM` | m | `AltitudeM` | `MinMax?` | 巡航 / 起始高度区间；缺省用 `rules.movement.altitudeBandsM[band]` |
| `releaseRangeKm` | 游戏 km | `ReleaseRangeM` | `double?`（×1000） | 平台投放距离（3.1.8）；`0` = 必须飞到目标正上方；`null` = 回退使用平台的 `ReleaseRangeM`（若平台也为 `null` 则生成即投放，B-T3-09） |
| `storyEventOnly` | — | `StoryEventOnly` | `bool?` | 不用（`tools/validate` 校验） |

```csharp
public enum MunitionCategory { Decoy = 0, Drone = 1, JetDrone = 2, Loitering = 3, Fpv = 4, CruiseMissile = 5, SupersonicMissile = 6,
                               AntiRadiation = 7, Ballistic = 8, Hypersonic = 9, GlideBomb = 10, UnguidedBomb = 11 }
public enum AltitudeBand { VeryLow = 0, Low = 1, LowMid = 2, Mid = 3, MidHigh = 4, High = 5, HighDive = 6,
                           Ballistic = 7, QuasiBallistic = 8, TerminalManeuver = 9, Glide = 10, Carrier = 11 }
```

（整数值 = Schema `enum` 数组顺序，00 1.2 第 8 条。）

### 1.3 `enemies/platforms.json` → `PlatformDef`（全字段，完整声明见 `00_core.md` 1.6）

| JSON 字段 | 单位 | C# 字段 | 类型 | 本文件用法 |
|---|---|---|---|---|
| `id` | — | `Id` | `string` | `Threat.DefId` |
| `nameKey` | — | `NameKey` | `string` | 不用 |
| `tag` | — | `Tag` | `TargetTag?` | 复制到 `Threat.Tag` |
| `firstSeen` | 年月 | `FirstSeen` | `YearMonth?` | 不用（00 1.4 形态 A，供 `tools/validate` 与历史模式校验，C-T2-08） |
| `cruiseSpeedKmh` | km/h | `CruiseSpeedMps` | `double` | 平台水平速度（进入、返航都用它） |
| `maxSpeedKmh` | km/h | `MaxSpeedMps` | `double?` | **不用**（8.1 Q8，B-T2-26） |
| `altitudeBand` | — | `AltitudeBand` | `AltitudeBand` | 只允许 `VeryLow … High`（8.2 校验 V3） |
| `hp` | — | `Hp` | `int?` | 不用（03） |
| `entersMap` | — | `EntersMap` | `bool` | `false` = 不生成平台实体，只生成挂载弹药（3.1.8） |
| `loadout[].options` | — | `Loadout[i].OptionIds` | `IReadOnlyList<string>` | 每次出击从中选一种（`spawn` 子流） |
| `loadout[].count` | 枚 | `Loadout[i].Count` | `int?` | 该挂载位投放枚数；`null` → 按 1 枚（8.1 Q7，B-T2-25） |
| `otherArmament` | — | `OtherArmament` | `IReadOnlyList<OtherArmament>?` | 不用（未建模为弹药） |
| `behavior` | — | `Behavior` | `PlatformBehavior` | 3.1.8 |
| `standoffFrom` | 年月 | `StandoffActive` | `bool`（00 1.4 形态 C） | 只对 `StandoffReleaseAndReturn` 有意义 |
| ★ `releaseRangeKm` | 游戏 km | `ReleaseRangeM` | `double?`（×1000） | 平台默认防区外投放距离（`≥ 0`，如 `tu22m3` 默认 `60` km，B-T3-09）；挂载弹药的 `ReleaseRangeM` 为 `null` 时使用此值，两者皆为 `null` 时退化为 0 秒停留（生成即投放并离开） |
| `whileAlive.enemyAccuracyTierBoost` | 档 | `WhileAlive.EnemyAccuracyTierBoost` | `int?` | 不用（03） |
| `whileAlive.cruiseMissilesAvoidAirDefense` | — | `WhileAlive.CruiseMissilesAvoidAirDefense` | `bool?` | 3.1.9 绕行钩子的开关 |
| ★ `radioLinked` / `reconQuality` | — | `RadioLinked` / `ReconQuality` | `bool?` / `TrackQuality?` | 不用（02 使用，P02） |

```csharp
public sealed record LoadoutEntryDef(IReadOnlyList<string> OptionIds, int? Count);
public sealed record PlatformWhileAliveDef(int? EnemyAccuracyTierBoost, bool? CruiseMissilesAvoidAirDefense);
public enum OtherArmament { Atgm = 0, Rockets = 1, UnguidedBombs = 2, LongRangeAam = 3, SmallGuidedBombs = 4 }
public enum PlatformBehavior { FrontlineAttack = 0, MustEnterShorad = 1, LowStrike = 2, StandoffReleaseAndReturn = 3,
                               HuntFightersAndRadars = 4, LaunchFromMapEdge = 5, GlobalAlertOnTakeoff = 6, WaveSourceOnly = 7,
                               ArmedRecon = 8, Spotter = 9, Awacs = 10 }
public sealed record PlatformDef
{
    public string Id { get; init; }  public string NameKey { get; init; }  public TargetTag? Tag { get; init; }
    public YearMonth? FirstSeen { get; init; }
    public double CruiseSpeedMps { get; init; }  public double? MaxSpeedMps { get; init; }
    public AltitudeBand AltitudeBand { get; init; }  public int? Hp { get; init; }  public bool EntersMap { get; init; }
    public IReadOnlyList<LoadoutEntryDef>? Loadout { get; init; }  public IReadOnlyList<OtherArmament>? OtherArmament { get; init; }
    public PlatformBehavior Behavior { get; init; }  public bool StandoffActive { get; init; }
    public double? ReleaseRangeM { get; init; }                    // releaseRangeKm × 1000（B-T3-09）
    public PlatformWhileAliveDef? WhileAlive { get; init; }
    public bool? RadioLinked { get; init; }  public TrackQuality? ReconQuality { get; init; }   // 02（P02）
}
```

### 1.4 其他关卡数据与跨夜带入说明

| 来源 | 字段 | 用法 |
|---|---|---|
| `level.json` `map.widthM` / `heightM` | `MapInfoDef.WidthM` / `HeightM` | 地图矩形 `[0, WidthM] × [0, HeightM]`：诱饵飞出点（3.1.7） |
| `level.json` `map.heightmap` | `HeightmapInfoDef`、`Heightmap` | 地形（3.3） |
| `map/structures.json` | `StructureDef.Pos`、`Weight` | 目标点、`weighted_random` 的权重 |
| `events.json` | `StoryActionDef { Type = SpawnWave, WaveId }` | 被引用的波次不进入自动时间表（3.1.1、3.1.9 `IsStoryOnlyWave`，A-2-28） |
| `CarryIn.Adaptation` | `IReadOnlyList<EnemyAdaptationCarry>?` | M1/M2 不实现，`SimWorld.Create` 第 8 步非空且 `Count > 0` 时抛 `E_NOT_IMPLEMENTED`（00 3.2，A-2-22） |

### 1.5 新增规则文件 `rules/movement.json`（`kind: "movement"`，顺序 21）→ `MovementRulesDef`

> 建议默认值已由 B-T2-02 / B-T2-22 确认（8.1 Q1、Q2）。测试一律使用第 7 节的手写数值。

| JSON 字段 | 单位 | C# 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|---|---|
| `altitudeBandsM` | m（AGL） | `AltitudeBandsM` | `IReadOnlyDictionary<AltitudeBand, MinMax>` | 必须**恰好**含 8 个键：`very_low` `low` `low_mid` `mid` `mid_high` `high` `high_dive` `glide`；`Min ≥ 0` | 定义中没有 `altitudeM` 时使用的巡航 / 起始高度区间 |
| `cruiseDescentAngleDeg` | 度 | `CruiseDescentAngleRad` | `double` | `0 < v < 90` | 巡航剖面弹药末段直线下降的下滑角 |
| `highDiveAngleDeg` | 度 | `HighDiveAngleRad` | `double` | `0 < v < 90` | `high_dive` 俯冲角 |
| `ballisticTerminalAngleDeg` | 度 | `BallisticTerminalAngleRad` | `double` | `0 < v < 90` | `ballistic` 落地时的弹道倾角 |
| `quasiBallisticTerminalAngleDeg` | 度 | `QuasiBallisticTerminalAngleRad` | `double` | `0 < v < 90` | `quasi_ballistic` 与 `terminal_maneuver` 的落地倾角 |
| `diveSpeedMult` | — | `DiveSpeedMult` | `double` | `≥ 1` | `diveFaster = true` 的弹药在末段的速度倍率 |

`altitudeBandsM` 的键是 `AltitudeBand` 的 JSON 名（snake_case），加载后为 enum 键；字典只查找、不遍历（00 6.2）。

### 1.6 新增规则文件 `rules/terrain.json`（`kind: "terrain"`，顺序 22）→ `TerrainRulesDef`

| JSON 字段 | 单位 | C# 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|---|---|
| `losSampleStepPx` | 像素 | `LosSampleStepPx` | `double` | `> 0` | 视线采样步长（以高程图像素为单位，跟随地图分辨率，建议 `0.5`） |
| `earthRadiusM` | m | `EarthRadiusM` | `double?` | `null` 或 `> 0` | 地球半径（建议 `6371000`）；`null` = 不计地球曲率 |
| `refractionK` | — | `RefractionK` | `double` | `> 0` | 有效地球半径系数（大气折射，建议 `1.3333333333333333`）；有效半径 `ReffM = RefractionK × EarthRadiusM` |
| `defaultAntennaHeightM` | m（AGL） | `DefaultAntennaHeightM` | `double` | `≥ 0` | 传感器 / 火控雷达的天线离地高度（建议 `10`，02 / 04 使用，8.1 Q3 / B-T2-03） |
| `horizonAzimuthBins` | 桶数 | `HorizonAzimuthBins` | `int` | `> 0`（JSON 省略时默认 `720`） | 预计算多山脊地平线遮挡包络 `HorizonProfile` 的方位角分桶数（建议 `720` = 每 `0.5°` 一桶，B-T2-31 / C-T2-01） |

`RulesSet` 包含 `MovementRulesDef Movement`（顺序 21）、`TerrainRulesDef Terrain`（顺序 22）（已在 `00_core.md` 1.1、1.6 登记，P11）。

---

## 2. 状态

### 2.1 枚举

```csharp
namespace Nightwatch.Sim.Movement;
public enum ThreatPhase { Ingress = 0, Egress = 1, Holding = 2, Arrived = 3 }        // 已离开地图的目标直接 Remove，没有对应阶段
public enum PathEndAction { Arrive = 0, Exit = 1, Hold = 2 }                          // 走完路径后：到达（落地结算）/ 离开地图 / 悬停
public enum MotionProfile { Linear = 0, Parabolic = 1 }                                // 高度随弧长：分段线性 / 抛物线
public enum ThreatTargetKind { None = 0, Structure = 1, PlayerUnit = 2, AimPoint = 3 } // AimPoint = 诱饵的假目标点
public enum ThreatExitReason { EgressComplete = 0, DecoyPathEnd = 1 }
```

### 2.2 `Threat`（`EntityKind.Threat`）

公共字段 `Id / Alive / CreatedTick / RemovedTick / DefId / Pos / AltM` 见 00 2.2、2.4。下表为 `Threat.WriteHash` 中 01 负责的前 32 个字段的**写入顺序**（00 2.4、3.7.2；后接 02 的 4 个字段与 03 的 3 个字段）。弧长字段统一以 `…ArcM` 结尾（A-3-08）。"快照"列 = 是否进入 `ThreatView`。

| # | 字段 | C# 类型 | 单位 | 初值 | 写 | 读 | 快照 |
|---|---|---|---|---|---|---|---|
| 1 | `Kind` | `ThreatKind` | — | 定义类型 | 01 | 全部 | ✔ |
| 2 | `Tag` | `TargetTag?` | — | 定义 `Tag` | 01 | 02、03 | ✔ |
| 3 | `VelMps` | `Vec2` | m/s | `(0,0)` | 01 | 02、03 | ✔ |
| 4 | `VertSpeedMps` | `double` | m/s，`d(AltM)/dt` | `0` | 01 | 03 | ✔ |
| 5 | `Phase` | `ThreatPhase` | — | `Ingress` | 01（02 / 04 经 3.2.8 接口） | 02、03、04 | ✔ |
| 6 | `WaveId` | `string?` | — | 生成它的波次；子弹药继承父平台 | 01 | 03、04 | ✔ |
| 7 | `EntryId` | `string?` | — | 进入点；子弹药继承父平台 | 01 | 01（返航）、04 | — |
| 8 | `ParentThreatId` | `int` | 实体 ID | `0`；平台投放的子弹药 = 平台 ID | 01 | 03 | ✔ |
| 9 | `SpawnAtSec` | `double` | 世界秒 | 精确生成 / 投放时刻 | 01 | 03 | — |
| 10 | `TargetKind` | `ThreatTargetKind` | — | 3.1.6 | 01 | 03、04 | — |
| 11 | `TargetPos` | `Vec2` | m | 目标点（= 路径中"到达"的那一点；诱饵为假目标点） | 01 | 03、04 | — |
| 12 | `TargetStructureId` | `int` | 实体 ID | `0` | 01 | 03 | — |
| 13 | `TargetUnitId` | `int` | 实体 ID | `0` | **01 唯一写入**（3.1.3、3.2.6、3.2.8，A-2-04） | 02、03、04 | — |
| 14 | `HomingUnitId` | `int` | 实体 ID | `0` | **02**（第 6 步 `EmissionSystem` 维护，A-2-06） | 01（第 2 步 `ApplyHoming`） | — |
| 15 | `ProfileReady` | `bool` | — | 由 01 生成：`false`；平台投放：`true` | 01 | 01 | — |
| 16 | `Profile` | `MotionProfile` | — | 3.2.2 | 01 | 01、03 | — |
| 17 | `Path` | `List<Vec2>` | m | 3.1.5 / 3.1.8；`Count ≥ 1` | 01 | 01、03 | — |
| 18 | `PathVersion` | `int` | — | `1`；每次改写 `Path` 加一 | 01 | 03（在飞拦截弹比对 `TargetPathVersion`，不一致按 `TargetLost` 自毁，A-2-09） | — |
| 19 | `PathEnd` | `PathEndAction` | — | 3.1 | 01 | 01、03 | — |
| 20 | `AnchorSec` | `double` | 世界秒 | `SpawnAtSec` | 01 | 01 | — |
| 21 | `AnchorArcM` | `double` | m（沿路径弧长） | `0` | 01 | 01 | — |
| 22 | `PathArcM` | `double` | m（沿路径弧长） | `0` | 01 | 02、03 | — |
| 23 | `SpeedMps` | `double` | m/s | 3.2.2 | 01 | 03 | — |
| 24 | `TerminalSpeedMps` | `double` | m/s | 3.2.2 | 01 | 03 | — |
| 25 | `TerminalStartArcM` | `double` | m（沿路径弧长） | 3.2.2（记作 `sD`） | 01 | 01 | — |
| 26 | `StartAltM` | `double` | m（AGL） | 3.2.2（记作 `A0`） | 01 | 01 | — |
| 27 | `EndAltM` | `double` | m（AGL） | 3.2.2（记作 `AEnd`） | 01 | 01 | — |
| 28 | `LastUpdateSec` | `double` | 世界秒 | `SpawnAtSec` | 01 | 03 | — |
| 29 | `ArrivedAtSec` | `double` | 世界秒 | `-1`；到达时 = 精确到达时刻 | 01 | 03 | — |
| 30 | `TurnArcM` | `double` | m（沿路径弧长） | `-1`；有挂载的平台 = 返航起点弧长 | 01 | 01 | — |
| 31 | `Releases` | `List<PendingRelease>` | — | 空；有挂载的平台见 3.1.8 | 01 | 01 | — |
| 32 | `IngressPath` | `List<Vec2>` | m | 空；平台 = 进场折线 `I`（3.1.8），用于构造子弹药路径 | 01 | 01 | — |
| — | `PathCumM` | `double[]` | m | 由 `Path` 派生：`PathCumM[0] = 0`，`PathCumM[i] = PathCumM[i−1] + |Path[i] − Path[i−1]|` | 01 | 01、03 | 不参与哈希 |
| — | `PathLengthM` | `double` | m | `= PathCumM[^1]`（记作 `L`） | 01 | 01、03 | 不参与哈希 |

```csharp
public sealed class PendingRelease            // 平台的一次投放（一个挂载位）
{
    public int LoadoutIndex;                  // PlatformDef.Loadout 下标
    public string MunitionId;                 // 已选定的弹药 ID
    public int Count;                         // 枚数（Count ?? 1）
    public double AtArcM;                     // 投放点弧长（m，A-3-08）
    public bool Done;                         // 已投放或已取消
    // 哈希顺序：LoadoutIndex, MunitionId, Count, AtArcM, Done
}
```

规则：

- `Path`、`PathCumM` 只能经 `ThreatPath.SetPath(threat, points)` 改写（同时重算 `PathCumM`、`PathLengthM`、`PathVersion += 1`；首次设置后 `PathVersion = 1`）。
- 高度 `AltM` 一律**相对地面**（AGL，00 0.4.1）。海拔 = `terrain.ElevationAt(Pos) + AltM`。高度剖面全部用 AGL 定义 ⇒ 低空目标**自动贴地飞行**（越过山脊时海拔随地形抬升），不会与地形相撞。

### 2.3 单例组件 `WaveState`（`SimState.Waves`，哈希序 1）

| # | 字段 | C# 类型 | 初值 | 写 | 读 |
|---|---|---|---|---|---|
| 1 | `Pending` | `List<PendingSpawn>` | `Initialize` 建立（3.1.2） | 01 | 01 |
| 2 | `NextSpawnSeq` | `long` | `1` | 01 | 01 |
| 3 | `Injections` | `List<WaveInjection>` | 空 | **04**（阶段 0 剧情事件 / 第 12 步压制波放行）追加；01 消费后清空 | 01 |
| 4 | `SpawnedThreatCount` | `int` | `0` | 01（每产生一个 `ThreatSpawned` 或 `MunitionReleased` 加一） | 快照 |
| 5 | `AllWavesSpawned` | `bool` | `Initialize` 末尾计算 | 01 | 00（`AllClear`） |

```csharp
public sealed record PendingSpawn(long Seq, int WaveIndex, int GroupIndex, int Ordinal,
                                  double SpawnAtSec, int SpawnTick, bool StartsWave, bool Injected);
    // 哈希顺序 = 参数顺序。Pending 始终按 (SpawnTick, SpawnAtSec, Seq) 升序（Seq 唯一 ⇒ 全序）
public sealed record WaveInjection(string WaveId, double StartAtSec, IReadOnlyList<int>? GroupIndices = null);
    // 哈希顺序：WaveId, StartAtSec, GroupIndices（null 写 false；否则写 true、Count、逐项 int，A-2-10）
```

`AllWavesSpawned = (Pending.Count == 0) && (Injections.Count == 0)`，每次 `WaveSpawnSystem.Execute` 末尾重算。注意：`AllWavesSpawned` 只反映 01 的待生成队列与注入队列是否已空；`00_core.md` 3.5 的 `AllClear` 在此基础上还会同时检查 `State.EnemyIntel.HeldWaves.Count == 0` 与 `!StoryRules.HasPendingScheduledSpawn(ctx)`（A-4-02）。

### 2.4 快照

```csharp
public readonly record struct ThreatView(int Id, string DefId, ThreatKind Kind, TargetTag? Tag, Vec2 Pos, double AltM,
    Vec2 VelMps, double VertSpeedMps, ThreatPhase Phase, string? WaveId, int ParentThreatId);
// GlobalView 追加：int PendingSpawnCount（= Waves.Pending.Count）, int SpawnedThreatCount, bool AllWavesSpawned
```

### 2.5 地形服务（不可变，不属于 `SimState`，不参与哈希）

```csharp
namespace Nightwatch.Sim.Terrain;
public sealed class TerrainModel
{
    public TerrainModel(Heightmap heightmap, TerrainRulesDef rules);
    public int WidthPx { get; }  public int HeightPx { get; }  public double MetersPerPixel { get; }
    public double ExtentXM { get; }            // = WidthPx × MetersPerPixel
    public double ExtentYM { get; }            // = HeightPx × MetersPerPixel
    public double MaxElevationM { get; }       // 高程数组的实际最大值（构造时遍历一次）
    public double LosStepM { get; }            // = LosSampleStepPx × MetersPerPixel
    public double? ReffM { get; }              // = RefractionK × EarthRadiusM；EarthRadiusM 为 null 时为 null
    public int HorizonAzimuthBins { get; }     // = rules.HorizonAzimuthBins（默认 720）
    public double ElevationAt(double x, double y);
    public double ElevationAt(Vec2 p);
    public bool HasLineOfSight(Vec2 a, double aMslM, Vec2 b, double bMslM);
    public bool HasLineOfSightAgl(Vec2 a, double aAglM, Vec2 b, double bAglM);   // = HasLineOfSight(a, ElevationAt(a) + aAglM, b, ElevationAt(b) + bAglM)
    public double CurvatureDropM(double s, double d);                              // 3.3.3
    public HorizonProfile BuildHorizonProfile(Vec2 observer, double observerAglM, double maxRangeM, int? azimuthBins = null);   // 3.3.4（B-T2-31 / C-T2-01）
    internal bool HasLineOfSightReference(Vec2 a, double aMslM, Vec2 b, double bMslM);   // 参考实现（测试对照）
}

public sealed class HorizonProfile             // 单个观察者的多山脊累积最大遮挡斜率包络（B-T2-31 / C-T2-01）
{
    public Vec2 ObserverPos { get; }
    public double ObserverMslM { get; }
    public double MaxRangeM { get; }
    public int AzimuthBins { get; }
    public double StepM { get; }
    public int RadialSteps { get; }
    public bool HasLineOfSight(Vec2 target, double targetMslM);
    public bool HasLineOfSightAgl(Vec2 target, double targetAglM);
}
```

- `SimWorld.Create` 在 00 3.2 第 3 步之后、第 4 步之前构造一次：`terrain = new TerrainModel(level.Heightmap, level.Catalog.Rules.Terrain)`；`SimContext.Terrain` 返回它（P30）。
- `TerrainModel` 直接引用 `Heightmap` 的高程数组，**不复制**（大地图 4000 × 4000 像素 = 128 MB）。`Heightmap` 内部以 `double[]` 存储并提供 `internal double[] ElevationArray`（P14）。
- 调用约定（A-2-26）：`HasLineOfSight` 参数为海拔（MSL），`HasLineOfSightAgl` 参数为离地高度（AGL）；02、04 按各自手头已有的高度形式选择调用或使用 `BuildHorizonProfile` 预计算包络（3.3.4）。

---

## 3. 每步算法

### 3.1 `WaveSpawnSystem`（Order 1，子流 `spawn`）

#### 3.1.1 `Initialize(ctx)`（`ctx.Rng` = `setup`，本系统不使用）

```
night        = 00 3.2 选出的 NightDef
storyOnly    = { a.WaveId | e ∈ level.StoryEvents.Events, a ∈ e.Actions, a.Type == SpawnWave }      # 字符串集合，只做成员判断
for wi in 0 .. night.Waves.Count−1:                     # 数据顺序
    w = night.Waves[wi]
    for gi, g in w.Groups:                              # 校验：模板航线尚未实现
        if g.Route.Kind == Template: 记录错误 E_NOT_IMPLEMENTED（格式见 4.3）
if 有错误: throw SimSetupException（列出全部错误）
for wi in 0 .. night.Waves.Count−1:
    w = night.Waves[wi]
    if w.Id ∈ storyOnly: continue                       # 只能由剧情注入（8.1 Q10）
    ExpandWave(wi, baseSec = w.AtSec, injected = false)
State.Waves.AllWavesSpawned = (Pending.Count == 0 && Injections.Count == 0)
```

#### 3.1.2 `ExpandWave(wi, baseSec, injected)`

```
w = night.Waves[wi]
for gi in 0 .. w.Groups.Count−1:
    g = w.Groups[gi]
    spacing = g.SpacingSec ?? 0.0
    for k in 0 .. g.Count−1:
        t    = baseSec + k * spacing                          # 乘法，不累加（避免误差累积）
        tick = Math.Max(1, SimTime.SecToTicksCeil(t, StepSec))
        at   = Math.Min(t, tick * StepSec)                    # 容差吸收：保证 at ≤ tick·StepSec
        Pending.Add(new PendingSpawn(NextSpawnSeq++, wi, gi, k, at, tick,
                                     StartsWave: gi == 0 && k == 0, Injected: injected))
Pending 按 (SpawnTick, SpawnAtSec, Seq) 稳定排序
```

- 组内**没有随机抖动**、同组目标**没有横向散开**（数据没有对应参数）。同组目标沿同一条路径、按时间间隔先后飞行。
- `t ≤ 0` 的生成（`atGameSec = 0`）在第 1 步处理（`tick = 1`），运动学上仍从 `SpawnAtSec = t` 开始推进（第 1 步结束时已飞 `1 − t` 秒）。

#### 3.1.3 `Execute(ctx)`

```
# 1. 消费注入（04 在阶段 0 或上一步写入）
for inj in State.Waves.Injections (列表顺序):
    wi = night.Waves 中 Id == inj.WaveId 的下标（序数比较）；找不到 → throw InvalidOperationException（04 负责只注入存在的波次）
    ExpandWave(wi, baseSec = Math.Max(inj.StartAtSec, ctx.TimeSec), injected = true)
State.Waves.Injections.Clear()

# 2. 处理到期的生成
while Pending.Count > 0 and Pending[0].SpawnTick <= ctx.Tick:
    e = Pending[0]; Pending.RemoveAt(0)
    ProcessSpawn(e)

State.Waves.AllWavesSpawned = (Pending.Count == 0 && Injections.Count == 0)
```

`ProcessSpawn(e)`：

```
w = night.Waves[e.WaveIndex]; g = w.Groups[e.GroupIndex]
entry = waves.EntryPoints 中 Id == g.EntryId 的一项
if e.StartsWave: Emit WaveStarted { WaveId = w.Id, AiTags = w.AiTags, Injected = e.Injected }，AtSec = EvAt(e.SpawnAtSec)

if g.EnemyId 是弹药 m:
    target = ResolveTarget(g.Target, entry.Pos)                       # 3.1.6，可能消耗 spawn 子流
    CreateWaveMunition(m, entry, g, w, target, e.SpawnAtSec, parentId = 0)
elif g.EnemyId 是平台 p:
    picks = ChooseLoadout(p)                                           # 3.1.8：每个挂载位一次 NextInt
    if p.EntersMap:
        target = ResolveTarget(g.Target, entry.Pos)
        CreatePlatform(p, entry, g, w, target, picks, e.SpawnAtSec)
    else:                                                              # 不进入地图的波次源（strategic_bomber）
        for (j, munitionId, count) in picks（挂载位顺序）:
            for c in 0 .. count−1:
                target = ResolveTarget(g.Target, entry.Pos)            # 每枚弹药各自选目标
                CreateWaveMunition(munitions[munitionId], entry, g, w, target, e.SpawnAtSec, parentId = 0)
```

`EvAt(x)` = `x > (ctx.Tick − 1) × StepSec ? x : null`（事件 `AtSec` 必须落在 `(Tick−1, Tick]`，00 4.2）。

`CreateWaveMunition(m, entry, g, w, target, at, parentId)`：

```
(path, endAction) = BuildMunitionPath(m, entry.Pos, g.Route, target)   # 3.1.5、3.1.7
th = new Threat { Kind = Munition, DefId = m.Id, Tag = m.Tag, Pos = entry.Pos, AltM = 0,
                  Phase = Ingress, WaveId = w.Id, EntryId = entry.Id, ParentThreatId = parentId,
                  SpawnAtSec = at, AnchorSec = at, AnchorS = 0, PathS = 0, LastUpdateSec = at,
                  ArrivedAtSec = −1, TurnS = −1, ProfileReady = false, PathEnd = endAction,
                  TargetKind / TargetPos / TargetStructureId / TargetUnitId = target 的对应值 }
ThreatPath.SetPath(th, path)
State.Threats.Add(th)
Emit ThreatSpawned { ThreatId = th.Id, DefId, Kind = Munition, EntryId = entry.Id, WaveId = w.Id }，AtSec = EvAt(at)
State.Waves.SpawnedThreatCount += 1
```

（`AltM = 0` 只是占位：同一步内第 2 步 `EnemyMovementSystem` 会初始化剖面并推进，快照不会看到 0。）

#### 3.1.4 进入点

所有目标都在进入点 `entry.Pos` 生成（可以在地图外；模拟不裁剪坐标，00 0.4.4）。生成时**不判断**进入点是否在地图内。

#### 3.1.5 航线 → 路径 `BuildMunitionPath`

记 `E = entry.Pos`，`T = target.Pos`，`W = g.Route.Waypoints`。

| 情况（按顺序判断） | 路径 | `PathEnd` |
|---|---|---|
| `target.Kind == AimPoint`（诱饵，3.1.7） | 见 3.1.7 | `Exit` |
| `m.AltitudeBand ∈ {Ballistic, QuasiBallistic, TerminalManeuver, Glide}` | `[E, T]`（**忽略** `waypointsM`；8.1 Q6） | `Arrive` |
| `Route.Kind == Direct` | `[E, T]` | `Arrive` |
| `Route.Kind == Waypoints` | `[E, W[0], …, W[n−1], T]` | `Arrive` |
| `Route.Kind == Template` | 不会出现（`Initialize` 已拒绝；WS02-004 实现后由模板解析器给出中间航点，再按 `Waypoints` 处理） | — |

之后：若 `m.Tag == CM` 且 `AvoidanceActive(state)`（3.1.9），`path = AirDefenseAvoidance.Adjust(state, level, path)`（04 钩子）。

相邻重复点（`Path[i] == Path[i+1]`，逐位相等）**保留**，形成长度为 0 的段，运动学按 3.2.3 规则处理。

#### 3.1.6 目标选择 `ResolveTarget(spec, entryPos)` → `TargetChoice`

```csharp
public readonly record struct TargetChoice(ThreatTargetKind Kind, Vec2 Pos, int StructureId, int UnitId);
```

| `spec` | 算法 | 随机消耗（`spawn` 子流） |
|---|---|---|
| `StructureId = s` | `id = State.StructureIdByDefId[s]`；`Kind = Structure, Pos = 该结构的 Pos, StructureId = id`。**即使该保护目标已被摧毁也照常打**（敌方不知道） | 0 |
| `Mode = WeightedRandom` | `WeightedStructure()`（下） | 1 次 `NextDouble` |
| `Mode = KnownTargets` | `c = EnemyTargeting.SelectKnownTarget(state, level, ctx.Rng)`（04 钩子）；`c == null` → `WeightedStructure()` | 钩子自定 + 回退时 1 次 |
| `Mode = AirDefense` | `c = EnemyTargeting.SelectAirDefenseTarget(state, level, ctx.Rng)`（04 钩子）；`c == null` → `WeightedStructure()` | 同上 |
| `Mode = DecoyFlight` | `w = WeightedStructure()`；返回 `w with { Kind = AimPoint, StructureId = 0 }` | 1 次 |

`WeightedStructure()`：

```
cands = State.Structures 中 Alive 的实体，按 ID 升序，且 StructureRules.IsDestroyed(s) == false（03 提供的只读判定；8.3 边界 B1）
if cands 为空: cands = State.Structures 中全部 Alive 实体（按 ID 升序）
total = Σ def(c).Weight（按 ID 升序从左到右累加）
r = ctx.Rng.NextDouble() * total                               # 无论 cands 是否为空都恰好消耗一次（cands 为空时 total = 0）
if cands 为空 或 total <= 0: return NoTarget()                  # 见下"无目标"
cum = 0
for c in cands: cum += def(c).Weight; if r < cum: return TargetChoice(Structure, c.Pos, c.Id, 0)
return cands 的最后一个                                          # 浮点兜底（r 理论上 < total）
```

**无目标** `NoTarget()`（关卡没有保护目标，或全部权重为 0）：返回 `TargetChoice(AimPoint, Pos = (WidthM / 2, HeightM / 2), 0, 0)`；调用方因 `Kind == AimPoint` 把该目标按诱饵处理（3.1.7，穿过地图中心后飞出）。

04 钩子的默认实现（04 实现前）：`SelectKnownTarget` 与 `SelectAirDefenseTarget` 都返回 `null`，不消耗随机数。04 实现的约定见 3.1.9。

#### 3.1.7 诱饵（`decoy_flight`）：只飞航线、不攻击

```
A   = target.Pos（假目标点）
pts = [E] + (Route.Kind == Waypoints ? W : []) + [A]
P   = pts 中 A 之前的最后一个与 A 不逐位相等的点；若不存在，dir = (0, 1)（正北）
dir = (A − P).Normalized()
X   = RayExitPoint(A, dir, WidthM, HeightM)
path = pts + [X]（若 X == A 则不追加）；PathEnd = Exit
```

`RayExitPoint(A, u, W, H)`（A 在地图矩形内时求射线离开矩形的点；A 在矩形外或边上时返回 A）：

```
if A.X <= 0 or A.X >= W or A.Y <= 0 or A.Y >= H: return A
tx = u.X > 0 ? (W − A.X) / u.X : (u.X < 0 ? (0 − A.X) / u.X : +∞)
ty = u.Y > 0 ? (H − A.Y) / u.Y : (u.Y < 0 ? (0 − A.Y) / u.Y : +∞)
t  = Math.Min(tx, ty)
return A + u * t
```

诱饵走完路径 → `ThreatExited { Reason = DecoyPathEnd }` 并删除；**不会**产生 `ThreatArrived`（不落地、不造成伤害）。

#### 3.1.8 平台

`ChooseLoadout(p)`：

```
picks = []
for j in 0 .. (p.Loadout?.Count ?? 0) − 1:                 # 挂载位顺序
    opts = p.Loadout[j].OptionIds
    idx  = ctx.Rng.NextInt(0, opts.Count)                  # 只有 1 个选项时也调用（恰好消耗 1 次 NextUInt32，返回 0）
    picks.Add((j, opts[idx], p.Loadout[j].Count ?? 1))
```

`CreatePlatform(p, entry, g, w, target, picks, at)`：

```
I = 进场折线：Route.Kind == Waypoints ? [E] + W + [T] : [E, T]      # 平台不受 Ballistic/Glide 规则影响
if AvoidanceActive 且 p.Tag == CM: 不适用（平台没有 CM 标签）
cumI = I 的累计弧长；LI = cumI[^1]
if picks 为空:
    path = I; PathEnd = Hold; TurnS = −1; Releases = []
else:
    for (j, mid, cnt) in picks:
        m = munitions[mid]
        R = (p.Behavior == StandoffReleaseAndReturn && !p.StandoffActive) ? 0.0 : (m.ReleaseRangeM ?? +∞)
        sj = ReleaseS(I, cumI, T, R)
        Releases.Add(new PendingRelease { LoadoutIndex = j, MunitionId = mid, Count = cnt, AtS = sj, Done = false })
    Releases 按 (AtS, LoadoutIndex) 升序
    sTurn = Releases 中最大的 AtS
    out   = TruncateAt(I, cumI, sTurn)                       # I 从起点到弧长 sTurn 的部分（末点 = PosOnPolyline(I, sTurn)）
    path  = out + Reverse(out) 去掉重复的折返点               # 原路返回进入点
    PathEnd = Exit; TurnS = sTurn
th = new Threat { Kind = Platform, DefId = p.Id, Tag = p.Tag, Pos = E, AltM = 0, Phase = Ingress, WaveId, EntryId,
                  ParentThreatId = 0, SpawnAtSec = at, AnchorSec = at, AnchorS = 0, LastUpdateSec = at,
                  ArrivedAtSec = −1, ProfileReady = false, target 各字段, TurnS, Releases, PathEnd, IngressPath = I }
ThreatPath.SetPath(th, path); State.Threats.Add(th)
Emit ThreatSpawned { ThreatId, DefId, Kind = Platform, EntryId, WaveId }，AtSec = EvAt(at)；SpawnedThreatCount += 1
```

`ReleaseS(I, cum, T, R)`：沿折线第一次进入以 `T` 为圆心、`R` 为半径的圆（含边界）时的弧长。

```
if R == +∞: return 0
for i in 0 .. I.Count−2:
    P0 = I[i]; w = P0 − T
    c = w.Dot(w) − R*R
    if c <= 0: return cum[i]                         # 段起点已在圈内
    d = I[i+1] − P0; a = d.Dot(d)
    if a <= 0: continue
    b = 2.0 * d.Dot(w)
    disc = b*b − 4.0*a*c
    if disc < 0: continue
    u = (−b − Math.Sqrt(disc)) / (2.0*a)
    if 0 <= u && u <= 1: return cum[i] + u * (cum[i+1] − cum[i])
return cum[^1]                                       # 折线终点 = T，必在圈内（兜底）
```

投放与返航规则汇总（R 为投放距离）：

| 行为 / 条件 | R | 投放后 |
|---|---|---|
| `StandoffReleaseAndReturn` 且 `StandoffActive` | `ReleaseRangeM ?? ∞` | 原路返航，回到进入点后离开 |
| `StandoffReleaseAndReturn` 且 `!StandoffActive` | `0`（飞到目标正上方投弹） | 同上 |
| 其他行为（`LowStrike`、`MustEnterShorad`、`LaunchFromMapEdge`、`GlobalAlertOnTakeoff`、`HuntFightersAndRadars`、`ArmedRecon`、`FrontlineAttack`……） | `ReleaseRangeM ?? ∞` | 同上 |
| 没有挂载（`loadout` 缺省或为空：`spotter`、`awacs`、直升机……） | — | 走完进场路径后**悬停**在终点（`Holding`），直到夜晚结束或被击落（8.1 Q5） |

- `ReleaseRangeM == null` ⇒ R = ∞ ⇒ 平台**一生成就投放**（如 Tu‑22M3 的 Kh‑22、MiG‑31K 的匕首、Su‑24M 的 Kh‑59）。此时 `sTurn = 0`，路径长度为 0，平台在同一步内生成、投放、离开（8.1 Q4）。
- `ReleaseRangeM == 0`（无制导炸弹）⇒ 投放点 = 目标点。
- 不进入地图的波次源（`EntersMap == false`）：不创建平台实体；挂载弹药在进入点生成，沿**本组航线**飞向各自的目标，发 `ThreatSpawned`（`ParentThreatId = 0`），不发 `MunitionReleased`。
- 平台的 `behavior` 中与移动无关的含义（`global_alert_on_takeoff` 的全图警报、`hunt_fighters_and_radars` 的猎杀、`awacs` / `spotter` 的存活效果）不在本文件：02 / 03 / 04 读取 `ThreatSpawned` 与 `PlatformDef` 自行处理。

#### 3.1.9 04 钩子（接口，经 `SimContext.EnemyAiHooks` 取得）

```csharp
namespace Nightwatch.Sim.EnemyAi;
public interface IEnemyAiHooks
{
    // 返回 null = 无可用目标（调用方回退到 weighted_random）。只读 state；随机数只能用传入的 rng（即 spawn 子流）
    TargetChoice? SelectKnownTarget(SimState state, LevelData level, IRandom rng);
    TargetChoice? SelectAirDefenseTarget(SimState state, LevelData level, IRandom rng);
    // 输入完整路径（首点 = 进入点或投放点，末点 = 目标点），返回修正后的路径：首末点必须保持不变。不得使用随机数；只读 state
    IReadOnlyList<Vec2> AdjustAvoidance(SimState state, LevelData level, IReadOnlyList<Vec2> path);
}
public sealed class DefaultEnemyAiHooks : IEnemyAiHooks { /* 前两个返回 null（不消耗随机数），AdjustAvoidance 原样返回 */ }
```

- `SimWorld.Create` 选择实现：`config.EnemyAiHooksOverride ?? 04 的正式实现（04 完成前为 DefaultEnemyAiHooks）`，存入世界（不属于 `SimState`，必须无状态）。`SimConfig.EnemyAiHooksOverride` 仅测试使用，`[JsonIgnore]`，回放中禁止（同 `RandomOverride`，8.2）。
- 本文件伪代码中的 `EnemyTargeting.SelectKnownTarget(...)`、`EnemyTargeting.SelectAirDefenseTarget(...)`、`AirDefenseAvoidance.Adjust(...)` 分别指 `ctx.EnemyAiHooks` 的三个方法。
- `TargetChoice.Kind == PlayerUnit` 时，`Pos` 是**敌方掌握的位置**（例如已知目标清单中记录的位置），不是单位当前位置；目标单位转移后，弹药仍飞向旧位置（GDD 7.4"猎杀"与 11.3"转移"的意义所在）。
- `AvoidanceActive(state)` = 存在 `Alive` 的 `Threat`，其 `Kind == Platform`、`Phase != Arrived`，且 `PlatformDef.WhileAlive?.CruiseMissilesAvoidAirDefense == true`。只在**生成 / 投放时**判定一次；A‑50 之后被击落不影响已在飞的导弹。
- `AiTag.Bypass` 的效果（沿河谷、低空盲区）由数据作者用 `waypointsM` 或模板表达；04 若需要按标签生成航线，在 `Adjust` 之外另行定义（8.1 Q11）。

### 3.2 `EnemyMovementSystem`（Order 2，子流 `movement`）

#### 3.2.1 `Execute(ctx)`

```
n = State.Threats.Count
for i in 0 .. n−1:                                  # ID 升序；本循环中新建的子弹药不被循环访问（00 2.2.3），在创建处立即推进
    th = State.Threats[i]
    if !th.Alive: continue
    if th.Phase == Arrived: continue                 # 等待 03 删除；不再移动、不再发事件
    if th.Phase == Holding: th.LastUpdateSec = ctx.TimeSec; continue
    if !th.ProfileReady: InitProfile(th, parentAltM: null, parentSpeedMps: null)
    ApplyHoming(th)                                  # 3.2.8
    Advance(th, ctx.TimeSec)
```

`Initialize(ctx)`：无操作。

#### 3.2.2 剖面初始化 `InitProfile(th, double? parentAltM, double? parentSpeedMps)`

`parentAltM` / `parentSpeedMps` 只在平台投放子弹药时给出（= 投放点处平台的高度、平台的 `SpeedMps`），其余情况为 `null`。记 `M = rules.Movement`，`def` = 弹药或平台定义，`L = th.PathLengthM`，`band = def.AltitudeBand`。`Roll(r) = ctx.Rng.Range(r.Min, r.Max)`（恰好 1 次 `NextDouble`，`Min == Max` 也消耗）。

| `band`（弹药） | `Profile` | `A0 = StartAltM` | `sD = TerminalStartS` | `AEnd = EndAltM` | `v1 = SpeedMps` | `v2 = TerminalSpeedMps` |
|---|---|---|---|---|---|---|
| `VeryLow`…`High` | `Linear` | `Roll(def.AltitudeM ?? M.AltitudeBandsM[band])` | `PathEnd == Arrive` ? `Max(0, L − A0 / Math.Tan(M.CruiseDescentAngleRad))` : `L` | `PathEnd == Arrive` ? `0` : `A0` | `def.SpeedMps` | `DiveFaster == true` ? `v1 * M.DiveSpeedMult` : `v1` |
| `HighDive` | `Linear` | `Roll(def.AltitudeM ?? M.AltitudeBandsM[HighDive])` | 同上，但用 `M.HighDiveAngleRad` | 同上 | 同上 | 同上 |
| `Ballistic` | `Parabolic` | `L * Math.Tan(M.BallisticTerminalAngleRad) / 2.0` | `0` | `0` | 同上 | `v1`（`DiveFaster` 规则同上，数据中没有） |
| `QuasiBallistic`、`TerminalManeuver` | `Parabolic` | `L * Math.Tan(M.QuasiBallisticTerminalAngleRad) / 2.0` | `0` | `0` | 同上 | 同上 |
| `Glide` | `Linear` | `parentAltM ?? Roll(def.AltitudeM ?? M.AltitudeBandsM[Glide])` | `0` | `0` | 同上 | 同上 |
| `Carrier`（无制导炸弹） | `Linear` | `parentAltM.Value` | `0` | `0` | `parentSpeedMps.Value` | `v1` |

| 平台（`Kind == Platform`，`band ∈ VeryLow…High`） | `Linear` | `Roll(M.AltitudeBandsM[band])` | `L` | `A0` | `def.CruiseSpeedMps` | `v1` |
|---|---|---|---|---|---|---|

说明：

- `PathEnd != Arrive` 的弹药（诱饵 `Exit`）不下降：`sD = L`，`AEnd = A0`。
- 巡航剖面的末段：从弧长 `sD` 起以下滑角直线降到地面，`L − sD = A0 / tan(γ)`；路径比这短时从起点就开始下降（`sD = 0`）。
- 弹道 / 准弹道：把地图内这一段建模为**以进入点为顶点的下降抛物线** `alt(s) = A0 · (1 − (s/L)²)`，落地倾角 `γ` 满足 `tan γ = 2·A0 / L` ⇒ `A0 = L·tan γ / 2`。水平速度恒为 `def.SpeedMps`（数据中的速度按水平速度使用，8.1 Q2）。`terminal_maneuver` 的轨迹与 `quasi_ballistic` 相同，"末端机动"只体现为 03 读取的 `interceptProbMult`（8.1 Q2）。
- 滑翔：从起始高度沿直线匀速下滑到目标（`sD = 0`），下滑比由几何决定。
- 无制导炸弹：投放点 = 目标点 ⇒ `L = 0` ⇒ 创建即到达（3.2.5）。
- `Math.Tan` 在每个目标初始化时调用一次（00 3.8：允许使用，结果不参与阈值判断）。
- 之后 `th.ProfileReady = true`；`AnchorSec`、`AnchorS` 不变（`SpawnAtSec`、`0`）。

#### 3.2.3 运动学公式（全部以"锚点 + 解析式"计算，不逐步累加）

记 `ta = AnchorSec`，`sa = AnchorS`，`v1`、`v2`、`sD`、`A0`、`AEnd`、`L` 如上。

**弧长随时间** `SAt(t)`（`t ≥ ta`）：

```
tau = t − ta
if sa >= sD:          s = sa + v2 * tau
else:
    tau1 = (sD − sa) / v1
    if tau <= tau1:   s = sa + v1 * tau
    else:             s = sD + v2 * (tau − tau1)
return Math.Min(s, L)
```

**到达某弧长的时刻** `TimeAtS(x)`（`x ≥ sa`；`x ≤ sa` 返回 `ta`）：

```
if x <= sa:           return ta
if sa >= sD:          return ta + (x − sa) / v2
if x <= sD:           return ta + (x − sa) / v1
return ta + (sD − sa) / v1 + (x − sD) / v2
```

**位置** `PosAtS(s)`：`Path.Count == 1` → `Path[0]`。否则二分查找最大的 `i ∈ [0, Count−2]` 使 `PathCumM[i] <= s`；`seg = PathCumM[i+1] − PathCumM[i]`；`seg <= 0` → `Path[i]`；否则 `f = (s − PathCumM[i]) / seg`，`pos = (Path[i].X + (Path[i+1].X − Path[i].X) * f, Path[i].Y + (Path[i+1].Y − Path[i].Y) * f)`。

**方向** `DirAtS(s)`：从上一步的 `i` 开始向后找第一个 `seg > 0` 的段 `k`，返回 `(Path[k+1] − Path[k]) / seg_k`；若 `s >= L` 或找不到，用最后一个 `seg > 0` 的段；全部段长为 0 → `(0,0)`。

**高度** `AltAtS(s)`：

```
Parabolic:  L <= 0 ? 0 : A0 * ((L − s) * (L + s)) / (L * L)
Linear:     s <= sD ? A0 : AEnd + (A0 − AEnd) * (L − s) / (L − sD)
```

**当前速度** `SpeedAtS(s)` = `s < sD ? v1 : v2`。

**速度向量**：`VelMps = DirAtS(s) * SpeedAtS(s)`；`s >= L` 时为 `(0,0)`。

**垂直速度** `VertAtS(s)`（`s >= L` → `0`）：

```
Parabolic:  −2.0 * A0 * s / (L * L) * SpeedAtS(s)
Linear:     s < sD ? 0 : −(A0 − AEnd) / (L − sD) * SpeedAtS(s)
```

（弧长恰在 `sD` 时取末段的值：速度 `v2`、垂直速度为下降值；高度仍为 `A0`。）

#### 3.2.4 推进 `Advance(th, T)`

```
sNew = SAt(th, T)

# 1. 平台投放（只有平台有 Releases），按 (AtS, LoadoutIndex) 顺序
for r in th.Releases:
    if r.Done or r.AtS > sNew: continue
    tr = TimeAtS(th, r.AtS); r.Done = true
    for c in 0 .. r.Count−1: ReleaseChild(th, r, tr, T)          # 3.2.6

# 2. 写状态
th.PathS = sNew
th.Pos = PosAtS(sNew); th.AltM = AltAtS(sNew)
th.VelMps = (sNew >= L) ? (0,0) : DirAtS(sNew) * SpeedAtS(sNew)
th.VertSpeedMps = VertAtS(sNew)
if th.TurnS >= 0 and th.Phase == Ingress and sNew >= th.TurnS: th.Phase = Egress
th.LastUpdateSec = T

# 3. 路径终点
if sNew >= L:
    tEnd = TimeAtS(th, L)
    switch th.PathEnd:
        Arrive: th.Phase = Arrived; th.ArrivedAtSec = tEnd; th.AltM = th.EndAltM; th.VelMps = (0,0); th.VertSpeedMps = 0
                Emit ThreatArrived { ThreatId, DefId, Pos = th.Pos, TargetKind, TargetStructureId, TargetUnitId }，AtSec = EvAt(tEnd)
        Exit:   Emit ThreatExited { ThreatId, DefId, Reason = (th.Phase == Egress ? EgressComplete : DecoyPathEnd) }，AtSec = EvAt(tEnd)
                State.Threats.Remove(th.Id)
        Hold:   th.Phase = Holding; th.VelMps = (0,0); th.VertSpeedMps = 0
```

- `EvAt` 同 3.1.3。
- 由于全部量都由锚点解析计算，`Predict(th, t)`（3.2.9）在路径不变时与实际推进到 `t` 的结果**逐位相同**。

#### 3.2.5 到达与删除

- 到达后 `Phase = Arrived`，目标停在 `Path[^1]`、`AltM = EndAltM`（= 0），不再移动。
- **由 03 的 `ImpactSystem`（Order 10）在同一步消费 `ThreatArrived` 并 `Remove` 该目标**（落地结算）。在 WS01-011 实现之前，占位 `ImpactSystem` 只做删除。
- 同一步中较晚的系统（7、8）看到 `Phase == Arrived` 的目标：03 决定是否允许在 `ArrivedAtSec` 之前完成的拦截生效（8.3 边界 B3）。

#### 3.2.6 平台投放子弹药 `ReleaseChild(p, r, tr, T)`

```
m  = munitions[r.MunitionId]
ps = r.AtS
pPos = PosAtS(p, ps); pAlt = AltAtS(p, ps)            # ps ≤ TurnS，位于平台路径的进场段
I = p.IngressPath；cumI = I 的累计弧长
rest = [pPos] + [I[k] | cumI[k] > ps]（按 k 升序；跳过与前一点逐位相等的点）     # I 的末点 = 平台目标点
path = (m.AltitudeBand ∈ {Ballistic, QuasiBallistic, TerminalManeuver, Glide, Carrier}) ? [pPos, p.TargetPos] : rest
endAction = Arrive
if p.TargetKind == AimPoint:                           # 数据中不会出现；为完整性规定
    X = RayExitPoint(p.TargetPos, 末段方向, WidthM, HeightM)；若 X != 末点则追加 X；endAction = Exit
if m.Tag == CM and AvoidanceActive(state) and endAction == Arrive: path = AirDefenseAvoidance.Adjust(state, level, path)
c = new Threat { Kind = Munition, DefId = m.Id, Tag = m.Tag, Pos = pPos, AltM = pAlt, Phase = Ingress,
                 WaveId = p.WaveId, EntryId = p.EntryId, ParentThreatId = p.Id, SpawnAtSec = tr,
                 AnchorSec = tr, AnchorS = 0, PathS = 0, LastUpdateSec = tr, ArrivedAtSec = −1, TurnS = −1,
                 TargetKind / TargetPos / TargetStructureId / TargetUnitId = 平台的对应值, PathEnd = endAction }
ThreatPath.SetPath(c, path); State.Threats.Add(c)
InitProfile(c, parentAltM: pAlt, parentSpeedMps: p.SpeedMps)
c.ProfileReady = true
Emit MunitionReleased { ParentThreatId = p.Id, ThreatId = c.Id, DefId = m.Id }，AtSec = EvAt(tr)
State.Waves.SpawnedThreatCount += 1
Advance(c, T)                                   # 立即推进到本步时刻；子弹药没有 Releases，不会递归
```

- 子弹药的路径 = 平台进场航线的剩余部分（例如不进入地图的波次源 / 一生成就投放的平台：`ps = 0`，子弹药沿整条航线飞）；弹道、滑翔、无制导类直飞目标。
- 同一挂载位的 `Count` 枚弹药在同一时刻、同一位置投放，路径相同（落点差异由 03 的精度档决定）。随机消耗：每枚子弹药在 `InitProfile` 中按 3.2.2 可能消耗 1 次 `movement` 子流（`Glide` / `Carrier` 子弹药不消耗）。

#### 3.2.7 平台的阶段

| 时刻 | `Phase` |
|---|---|
| 生成 | `Ingress` |
| `PathS >= TurnS`（有挂载） | `Egress` |
| 走完返航路径 | 发 `ThreatExited { EgressComplete }` 并删除 |
| 无挂载、走完进场路径 | `Holding` |

#### 3.2.8 改航 / 返航 / 归航接口（`Nightwatch.Sim.Movement.ThreatRouting`，供 02 / 03 / 04 调用）

```csharp
public static class ThreatRouting
{
    // 弹药改飞新目标点（电子战诱导 / 链路中断后坠落点等）。返回 false = 不适用（非弹药、Phase != Ingress）
    public static bool Retarget(SimContext ctx, Threat th, Vec2 newTargetPos);
    // 立即返航（平台或弹药）：飞回进入点后离开。返回 false = 不适用（Phase == Arrived）
    public static bool BeginEgress(SimContext ctx, Threat th);
}
```

两者都只在 `th.LastUpdateSec == ctx.TimeSec`（本步第 2 步之后）调用，否则抛 `InvalidOperationException`。设 `t0 = ctx.TimeSec`，`cur = th.Pos`，`alt = th.AltM`。

`Retarget`：

```
ThreatPath.SetPath(th, [cur, newTargetPos]); th.PathEnd = Arrive
th.TargetPos = newTargetPos; th.TargetKind = 原值（不改）; TargetStructureId / TargetUnitId 不改
th.AnchorSec = t0; th.AnchorS = 0; th.PathS = 0
th.StartAltM = alt
按 3.2.2 同一行的规则、用新的 L 与 A0 = alt 重算 sD、AEnd（Parabolic：A0 = alt，即以当前点为新抛物线顶点）；v1、v2 不变
```

`BeginEgress`：

```
dest = 进入点 Pos（waves.EntryPoints 中 Id == th.EntryId；th.EntryId 为 null 时 dest = cur）
所有 Releases 中 Done == false 的项置 Done = true（取消投放，挂载随平台返回）
ThreatPath.SetPath(th, [cur, dest]); th.PathEnd = Exit; th.Phase = Egress; th.TurnS = 0
th.AnchorSec = t0; th.AnchorS = 0; th.PathS = 0
th.StartAltM = alt; th.EndAltM = alt; th.TerminalStartS = PathLengthM; th.Profile = Linear
v1 不变；v2 = v1
```

`ApplyHoming(th)`（`EnemyMovementSystem` 内部，在 `Advance` 之前）：

```
if th.HomingUnitId == 0 or th.Kind != Munition or th.Phase != Ingress or th.PathEnd != Arrive: return
if 在 FireUnits / Sensors / EwUnits / DeceptionUnits 中依次 TryGet(th.HomingUnitId) 都失败: return     # 目标已毁：继续飞向最后的目标点
u = 找到的实体
if u.Pos == th.Path[^1]（逐位相等）: return
以 t0 = th.LastUpdateSec 执行与 Retarget 相同的改写（cur / alt 用 SAt(t0) 处的值，即当前 Pos / AltM），并令 th.TargetUnitId = u.Id、th.TargetKind = PlayerUnit
```

- 02 负责设置 / 清除 `HomingUnitId`（例如反辐射导弹只在目标雷达开机时归航，关机后清零 → 飞向最后记录的位置）。
- `PathVersion` 的增加通知 03：之前基于旧路径算出的拦截点可能失效（03 自行决定处理方式，8.3 边界 B2）。

#### 3.2.9 解析位置预测（供 03 解析拦截）

```csharp
namespace Nightwatch.Sim.Movement;
public readonly record struct ThreatPose(Vec2 Pos, double AltM, Vec2 VelMps, double VertSpeedMps, double PathS, bool AtPathEnd);
public readonly record struct MotionLeg(double StartSec, double EndSec, Vec2 StartPos, Vec2 VelMps,
                                        double StartAltM, double VertSpeedMps, double VertAccelMps2);
public static class ThreatKinematics
{
    public static ThreatPose Predict(Threat th, double atSec);
    public static IReadOnlyList<MotionLeg> Legs(Threat th, double fromSec);
    public static double? PredictArrivalSec(Threat th);        // PathEnd == Arrive 且未到达 → TimeAtS(L)；否则 null（已到达返回 ArrivedAtSec）
    public static double SAt(Threat th, double atSec);
    public static double TimeAtS(Threat th, double s);
    public static Vec2 PosAtS(Threat th, double s);
    public static double AltAtS(Threat th, double s);
}
```

`Predict(th, t)`：

- `t < th.LastUpdateSec − 1e-9` → `ArgumentOutOfRangeException`（只预测未来）。
- `Phase == Arrived` 或 `Holding` → 返回当前 `Pos / AltM`，速度为 0，`AtPathEnd = true`。
- 否则 `s = SAt(t)`，按 3.2.3 求 `Pos / AltM / VelMps / VertSpeedMps`；`AtPathEnd = (s >= L)`；`s >= L` 且 `PathEnd == Arrive` 时 `AltM = EndAltM`。

预测**只基于当前路径**：不包括未来的改航、归航更新、返航指令（`PathVersion` 变化即失效）。平台的返航段已在路径中，所以平台的预测在投放后仍然准确。

`Legs(th, from)`：把 `[from, 路径终点时刻]` 分成水平速度恒定的若干段，供 03 逐段解析求解拦截时刻：

```
断点 = { from } ∪ { TimeAtS(PathCumM[i]) | PathCumM[i] 在 (SAt(from), L) 内 } ∪ { TimeAtS(sD) 若 sD 在 (SAt(from), L) 内 } ∪ { TimeAtS(L) }
按时间升序、去重（逐位相等）；对每对相邻断点 (t0, t1)：
    s0 = SAt(t0)；smid = SAt((t0 + t1) / 2)
    StartPos = PosAtS(s0)；VelMps = DirAtS(smid) * SpeedAtS(smid)
    StartAltM = AltAtS(s0)
    Linear：VertSpeedMps = VertAtS(smid)；VertAccelMps2 = 0
    Parabolic：v = SpeedAtS(smid)；VertSpeedMps = −2.0 * A0 * s0 / (L * L) * v；VertAccelMps2 = −2.0 * A0 * v * v / (L * L)
Hold：最后追加一段 (TimeAtS(L), +∞)，速度 0，高度 A0
Phase == Arrived / Holding：返回单段 (from, +∞)，速度 0
```

段内：`pos(t) = StartPos + VelMps × (t − StartSec)`，`alt(t) = StartAltM + VertSpeedMps × τ + 0.5 × VertAccelMps2 × τ²`（`τ = t − StartSec`）。与 `Predict` 的差异只来自浮点舍入（测试容差 1e-6 m）。

### 3.3 地形与视线（`TerrainModel`）

#### 3.3.1 像素约定

- 像素 `(row, col)`（`row = 0` 为图像最上一行 = 北边，00 1.5）代表一个 `m × m` 的方块（`m = MetersPerPixel`），**高程值位于方块中心**：

  `x_c = (col + 0.5) × m`，`y_c = ExtentYM − (row + 0.5) × m`，其中 `ExtentYM = HeightPx × m`。

  （与 `tools/testmap/gen_test01_heightmap.py` 的采样点一致。图像范围用 `WidthPx × m`、`HeightPx × m`，不用 `map.widthM / heightM`；二者差值 ≤ 1 像素，00 1.5 已校验。）

#### 3.3.2 双线性采样 `ElevationAt(x, y)`

```
fx = x / m − 0.5
fy = (ExtentYM − y) / m − 0.5
fx = Math.Clamp(fx, 0.0, WidthPx − 1.0)          # 地图外 / 边缘半像素：钳到边缘像素中心
fy = Math.Clamp(fy, 0.0, HeightPx − 1.0)
c0 = (int)Math.Floor(fx);  r0 = (int)Math.Floor(fy)
if c0 > WidthPx − 2:  c0 = Math.Max(WidthPx − 2, 0)
if r0 > HeightPx − 2: r0 = Math.Max(HeightPx − 2, 0)
c1 = Math.Min(c0 + 1, WidthPx − 1);  r1 = Math.Min(r0 + 1, HeightPx − 1)
tx = fx − c0;  ty = fy − r0
e00 = E[r0*W + c0]; e01 = E[r0*W + c1]; e10 = E[r1*W + c0]; e11 = E[r1*W + c1]
top = e00 + (e01 − e00) * tx
bot = e10 + (e11 − e10) * tx
return top + (bot − top) * ty
```

- **地图外**：坐标被钳到最近的边缘像素中心带 ⇒ 高程沿边缘向外**常值延伸**（例如地图外的进入点取最近边缘的高程）。不报错。
- 运算顺序必须如上（结果逐位可复现）。`W = WidthPx`，`E` = 高程数组（行主序）。
- `WidthPx == 1` 或 `HeightPx == 1` 时退化为一维插值（`c1 == c0` 或 `r1 == r0`，`tx` 或 `ty` 为 0）。

#### 3.3.3 视线 `HasLineOfSight(a, aMslM, b, bMslM)`（参考算法 = 定义）

输入为两端点的**海拔**（MSL）。观察者（传感器）海拔 = `ElevationAt(pos) + 天线离地高度`（来源由 02 规定，8.1 Q3）；目标海拔 = `ElevationAt(threat.Pos) + threat.AltM`。

```
dx = b.X − a.X; dy = b.Y − a.Y
d  = Math.Sqrt(dx*dx + dy*dy)
if d <= LosStepM: return true                           # 端点之间没有内部采样点
# 快速接受（精确，不改变结果）
cmax = (ReffM == null) ? 0.0 : (d * d) / (8.0 * ReffM)
if Math.Min(aMslM, bMslM) > MaxElevationM + cmax + 1e-6: return true
n = (int)Math.Ceiling(d / LosStepM)
for i in 1 .. n−1:                                       # 不含两端点
    f   = (double)i / n
    px  = a.X + dx * f;  py = a.Y + dy * f
    ray = aMslM + (bMslM − aMslM) * f
    s   = d * f
    drop = (ReffM == null) ? 0.0 : (s * (d − s)) / (2.0 * ReffM)
    if ElevationAt(px, py) + drop > ray: return false    # 严格大于：擦边可见
return true
```

- **地球曲率**：计入。把地形抬高 `drop(s) = s·(d − s) / (2·R_eff)`（等价于两端点之间的地球凸起，抛物线近似），`R_eff = RefractionK × EarthRadiusM`。`EarthRadiusM = null` 时不计。理由：GDD 8.1 明确"地形**和地平线**形成低空盲区"；A 线地图可达 400 km（WBS 01.A），150 km 外地平线遮挡数百米以下的目标。
- **快速接受**的正确性：每个样本 `ray ≥ min(aMsl, bMsl)`，双线性值不超过 4 个像素的最大值（加 1e-6 吸收舍入），`drop ≤ d²/(8R)`；条件成立时不可能有样本被遮挡。
- 结果与方向无关只在样本点对称时成立；**调用方一律以观察者为 `a`、目标为 `b`**。
- `HasLineOfSight` 的任何加速实现（见 3.3.4）都必须与 `HasLineOfSightReference` 对任意输入给出相同结果（T-01-47）。

#### 3.3.4 缓存与加速（必须确定性）

1. 视线结果是输入的纯函数；**任何缓存都只能以精确输入为键**（`double` 按位比较，或 `(观察者实体 ID, 目标实体 ID, Tick)` 且同一步内输入不变），命中与否不得改变结果。缓存不属于 `SimState`，不参与哈希，可随时清空。
2. **禁止**：按网格量化坐标作为缓存键、用近似结果代替定义、跨步复用而不校验输入。
3. 允许的精确加速：
   - 构造时预计算 `MaxElevationM`（已用于快速接受）。
   - 分块最大值金字塔：对 `B × B` 像素块存最大高程；沿射线遇到某段采样点全部落在块覆盖范围内、且该段 `min(ray) > 块最大值 + 该段 max(drop) + 1e-6` 时跳过该段采样。块范围要包含双线性用到的相邻像素（向外扩 1 像素）。
4. 不得使用多线程（00 6.2）。

#### 3.3.5 性能上限提示（WS01-028：600 无人机 + 90 导弹 + 拦截弹，单步 < 2 ms）

| 部分 | 每步成本 | 说明 |
|---|---|---|
| `WaveSpawnSystem` | O(本步生成数) | 每次生成 O(路径点数 + 保护目标数) |
| `EnemyMovementSystem` | O(N)，每个目标常数次运算 + 一次 O(log 路径点数) 二分 | 700 个目标远小于 0.1 ms |
| `HasLineOfSight` | O(d / LosStepM) 次双线性采样（约 20 次浮点运算 / 样本） | 100 m 像素、0.5 像素步长时 150 km 视线 = 3000 样本 |

视线是主要开销：若 5 部远程雷达 × 700 个目标每步都做全长视线，约 1000 万样本 / 步，远超预算。因此 02 必须（在 02 中规定）：先做距离 / 高度筛选再调用视线；同一步内同一（传感器，目标）只算一次；必要时规定"每 K 步重算一次视线"作为**规则**（写入数据，属于定义的一部分，不是缓存）。本文件保证单次调用的复杂度与确定性，见 8.3 边界 B4。

---

## 4. 事件与命令

### 4.1 产生的事件（字段表顺序 = `WriteHash` 顺序）

| 值 | 事件 | 字段 | `AtSec` | 产生者 |
|---|---|---|---|---|
| 100 | `WaveStarted` | `string WaveId, IReadOnlyList<AiTag>? AiTags, bool Injected` | 本波首个生成时刻（`EvAt`） | 1 |
| 101 | `ThreatSpawned` | `int ThreatId, string DefId, ThreatKind Kind, string EntryId, string WaveId` | `EvAt(SpawnAtSec)` | 1 |
| 102 | `MunitionReleased` | `int ParentThreatId, int ThreatId, string DefId` | `EvAt(投放时刻)` | 2 |
| 103 | `ThreatArrived` | `int ThreatId, string DefId, Vec2 Pos, ThreatTargetKind TargetKind, int TargetStructureId, int TargetUnitId` | `EvAt(到达时刻)` | 2 |
| 104 | `ThreatExited` | `int ThreatId, string DefId, ThreatExitReason Reason` | `EvAt(离开时刻)` | 2 |

- 每个新 `Threat` 恰好伴随一个 `ThreatSpawned`（由波次生成，含不进入地图的波次源投放的弹药）**或**一个 `MunitionReleased`（由地图上的平台投放），二者不会同时出现。
- 同一步内事件顺序：`WaveStarted` → 该波的 `ThreatSpawned`（按 `Pending` 顺序）→（第 2 步，按目标 ID 升序处理）`MunitionReleased`（子弹药被立即推进，可能紧接着自己的 `ThreatArrived`）→ 该平台的 `ThreatArrived` / `ThreatExited`。
- `WriteHash` 中 `IReadOnlyList<AiTag>?` 按 00 3.7.1：`null` 写 `Write(false)`；否则 `Write(true)`、`Write(Count)`、逐项 `Write((int)tag)`。

### 4.2 命令

本文件的系统不处理任何命令（不实现 `ICommandHandler`）。改航 / 返航 / 归航经 3.2.8 的静态接口由其他系统调用；波次注入经 `WaveState.Injections` 由 04 写入。

### 4.3 `SimWorld.Create` 时的错误

`WaveSpawnSystem.Initialize` 抛 `SimSetupException`，消息每条一行：

```
[E_NOT_IMPLEMENTED] levels/<levelId>/waves.json $.nights[<i>].waves[<j>].groups[<k>].route.template: 航线模板尚未实现（WS02-004）
```

`<i>` 为该夜在 `nights` 数组中的下标，`<j>`、`<k>` 为数据下标。

---

## 5. 边界情况

| # | 情况 | 处理 |
|---|---|---|
| 1 | `spacingGameSec` 缺省 | 间隔 0：同组目标在同一时刻、同一位置生成，ID 按序号 `k` 递增 |
| 2 | `atGameSec = 0` | 第 1 步生成；`ThreatSpawned.AtSec = null`；运动从 `t = 0` 起算（第 1 步末已飞 1 秒） |
| 3 | 生成时刻为小数（如 60.6 秒） | 在 `ceil` 所在步生成，`AtSec` 精确；第 2 步推进 `T − SpawnAtSec` 秒 |
| 4 | 两个波次 / 组的生成时刻相同 | 按 `Seq`（= 波次数据顺序 → 组顺序 → 序号）决定先后与 ID |
| 5 | 夜晚提前结束时仍有未生成的条目 | 永不生成，不报错 |
| 6 | `DurationTicks` 之后才到期的波次 | 永不生成；`AllWavesSpawned` 一直为 false（`EndWhenClear` 不会提前结束） |
| 7 | 剧情注入不存在的波次 ID | `InvalidOperationException`（04 的错误） |
| 8 | 剧情注入时 `StartAtSec` 早于当前时刻 | 以当前步时刻 `ctx.TimeSec` 为本波起点，不补算过去 |
| 9 | 同一波次被注入两次 | 生成两批，各自发 `WaveStarted { Injected = true }` |
| 10 | 被剧情引用的波次 | 不进入自动时间表，只能被注入 |
| 11 | 指定的保护目标已被摧毁 | 照常飞向该点（敌方不知道） |
| 12 | `weighted_random` 时全部保护目标已被摧毁 | 在全部（含已摧毁）保护目标中按权重选 |
| 13 | 关卡没有保护目标 / 权重和为 0 | 按诱饵处理：穿过地图中心后飞出（3.1.6） |
| 14 | `known_targets` / `air_defense` 钩子返回 null | 回退 `weighted_random`（再消耗 1 次 `NextDouble`） |
| 15 | 已知目标单位已转移 | 弹药飞向钩子给出的（旧）位置 |
| 16 | 路径中有逐位相等的相邻点 | 长度 0 的段：位置取该点，方向取下一个非零段 |
| 17 | 路径长度为 0（进入点 = 目标点；无制导炸弹） | 在推进时立即到达，`ThreatArrived.AtSec = SpawnAtSec` |
| 18 | 弹道类目标的 `waypointsM` | 忽略，直飞目标 |
| 19 | 弹道类路径长度 `L = 0` | `A0 = 0`，立即到达 |
| 20 | 巡航弹药路径短于下降段 `A0 / tan γ` | `sD = 0`：从起点开始线性下降 |
| 21 | 平台挂载 `count = null` | 按 1 枚 |
| 22 | 平台挂载弹药 `releaseRangeKm` 缺省 | 生成即投放；平台路径长度 0，同一步内生成、投放、离开（发 3 个事件） |
| 23 | 平台进场路径从未进入投放圈 | 不可能（终点 = 目标点，距离 0）；`ReleaseS` 兜底返回 `L` |
| 24 | 平台多个挂载位投放距离不同 | 分别在各自投放点投放；在最近的投放点（最大 `AtS`）折返 |
| 25 | 平台在投放前被击落（03 `Remove`） | 未投放的挂载随之消失 |
| 26 | 平台在投放前被 `BeginEgress` | 未投放项取消（`Done = true`），飞回进入点离开 |
| 27 | 无挂载平台 | 走完进场路径后悬停到夜晚结束；`AllClear` 因而不会触发（00 3.5） |
| 28 | `Retarget` 作用于平台或已到达 / 返航中的弹药 | 返回 false，状态不变 |
| 29 | 在第 2 步之前（阶段 0 或第 1 步）调用 `Retarget` / `BeginEgress` | `InvalidOperationException` |
| 30 | `HomingUnitId` 指向已被摧毁的单位 | 不改航，继续飞向最后的目标点；`HomingUnitId` 保留（02 可清零） |
| 31 | `Phase == Arrived` 的目标未被 03 删除 | 不再移动、不再发事件 |
| 32 | 子弹药在投放的同一步就到达 | 同一步先发 `MunitionReleased`，再发其 `ThreatArrived` |
| 33 | A‑50 在导弹生成后被击落 | 已生成导弹的路径不变 |
| 34 | 坐标在地图外的高程查询 | 钳到边缘像素中心，常值延伸 |
| 35 | 视线两端点距离 ≤ 采样步长（含 0） | 可见 |
| 36 | 视线样本恰好与射线等高 | 不遮挡（严格大于才遮挡） |
| 37 | 观察者自身低于地形（天线高度 0 且在坑底） | 按算法计算，不特殊处理 |
| 38 | `earthRadiusM = null` | 不计曲率、`cmax = 0` |
| 39 | 天气、季节、昼夜 | 对生成与移动无影响 |

---

## 6. 不变量（`SimConfig.CheckInvariants = true` 时，每步末尾检查）

1. 每个 `Alive` 的 `Threat`：`Path.Count ≥ 1`；`PathCumM` 与 `Path` 一致（重新计算后逐位相等）；`0 ≤ PathS ≤ PathLengthM`；`PathS == SAt(LastUpdateSec)`（逐位）。
2. `Phase ∈ {Ingress, Egress}` 的目标：`LastUpdateSec == TimeSec`（第 2 步推进了所有在飞目标，包括本步投放的子弹药）。
3. `AltM ≥ 0`；`SpeedMps > 0`（`PathLengthM > 0` 时）；`TerminalSpeedMps ≥ SpeedMps`；`0 ≤ TerminalStartS ≤ PathLengthM`。
4. `Phase == Arrived` ⇔ `ArrivedAtSec ≥ 0`；此时 `ArrivedAtSec ≤ TimeSec`、`VelMps == (0,0)`、`Pos == Path[^1]`。
5. `Phase == Holding` ⇒ `PathEnd == Hold` 且 `PathS == PathLengthM`。
6. `ParentThreatId != 0` ⇒ `ParentThreatId < Id`；`Kind == Platform` ⇒ `ParentThreatId == 0`。
7. `Releases` 按 `(AtS, LoadoutIndex)` 升序；`Kind == Munition` ⇒ `Releases.Count == 0` 且 `TurnS == −1`。
8. `ProfileReady == true`（第 2 步之后所有 `Alive` 目标都已初始化）。
9. `WaveState.Pending` 按 `(SpawnTick, SpawnAtSec, Seq)` 严格升序；第 1 步之后所有 `SpawnTick > Tick`；`AllWavesSpawned == (Pending.Count == 0 && Injections.Count == 0)`；第 1 步之后 `Injections.Count == 0`。
10. `SpawnedThreatCount` = 本夜已发出的 `ThreatSpawned` + `MunitionReleased` 事件数。
11. 地形：`ElevationAt` 对任意有限输入返回有限值，且落在 `[min(E), MaxElevationM + 1e-6]` 内。


---

## 7. 测试用例

> 预期值由 `/Users/xtxsinan/.gemini/antigravity/brain/a6d360e5-4c81-4530-9448-7555c8e757a0/scratch/spec_calc/01_movement_calc.py` 与 `01_terrain_calc.py` 计算（与 3.2.3、3.3 的运算顺序一致）。浮点比较：标"=="的逐位相等；其余容差 `1e-9`（绝对值，除非另注）。
> 测试文件：`sim.tests/Spawn/WaveSpawnTests.cs`、`sim.tests/Movement/EnemyMovementTests.cs`、`sim.tests/Movement/ThreatKinematicsTests.cs`、`sim.tests/Terrain/TerrainModelTests.cs`、`sim.tests/Data/MovementRulesLoadTests.cs`。

### 7.0 公共夹具 `Mini01`（`MiniLevelBuilder`，手写，不依赖正式数值）

- `conventions`：`gameSecToWorldSec 60, worldStepSec 1, cellKm 1, machKmh 1200`；关卡日期 `2023-06-01`；`levelId = "mini"`；只有第 1 夜，`durationGameSec 100`（6000 步），`EndWhenClear = false`。
- 地图 `20000 × 20000` m；高程图 `2 × 2` 像素、`metersPerPixel 10000`、全部为 0（移动测试不涉及地形）。个别测试注明更大的地图时，高程图同样按 `10000 m/像素` 全 0 生成。
- 电网为空；保护目标（ID 依次为 1、2、3）：`s1 (10000, 10000) weight 5`、`s2 (15000, 5000) weight 3`、`s3 (5000, 15000) weight 2`。个别测试另行给出保护目标列表时替换这三项。
- 进入点：`eE (25000, 10000)`、`eW (−5000, 10000)`、`e0 (0, 0)`。
- `rules/movement.json`（测试值）：`altitudeBandsM = { very_low {50,50}, low {300,300}, low_mid {1000,1000}, mid {3000,3000}, mid_high {6000,6000}, high {8000,8000}, high_dive {10000,10000}, glide {9000,9000} }`，`cruiseDescentAngleDeg 45`，`highDiveAngleDeg 45`，`ballisticTerminalAngleDeg 45`，`quasiBallisticTerminalAngleDeg 30`，`diveSpeedMult 2`。（`tan(45°)` 在 double 中为 `0.9999999999999999`。）
- `rules/terrain.json`（测试值）：`losSampleStepPx 0.5, earthRadiusM null, refractionK 1, defaultAntennaHeightM 10`。
- 弹药（只列移动相关字段，其余必填字段任意合法值）：

| id | tag | speedKmh（→ m/s） | altitudeBand | altitudeM | 其他 |
|---|---|---|---|---|---|
| `d1` | DECOY | 180（50） | low | — | |
| `u1` | UAV | 180（50） | low | {500, 2000} | |
| `m100` | CM | 180（50） | very_low | {100, 100} | |
| `l1` | UAV | 180（50） | very_low | {100, 100} | `diveFaster: true` |
| `c1` | CM | 720（200） | very_low | {30, 70} | |
| `a1` | CM | 720（200） | very_low | {30, 70} | 无 `releaseRangeKm` |
| `b1` | BM | 7200（2000） | ballistic | — | |
| `q1` | BM | 7200（2000） | quasi_ballistic | — | |
| `h1` | SCM | 3600（1000） | high_dive | — | |
| `g1` | GB | 720（200） | glide | — | `releaseRangeKm 20` |
| `f1` | null | null | carrier | — | `releaseRangeKm 0`，`interceptable false`，`hp null` |

- 平台：

| id | tag | cruiseSpeedKmh（→ m/s） | altitudeBand | entersMap | loadout | behavior | 其他 |
|---|---|---|---|---|---|---|---|
| `p_bomb` | null | 720（200） | high | false | `[{options:[c1], count:3}]` | wave_source_only | |
| `p_glide` | AC_HIGH | 252（70） | high | true | `[{options:[g1], count:2}]` | standoff_release_and_return | 无 `standoffFrom`（⇒ `StandoffActive = true`） |
| `p_glide_old` | AC_HIGH | 252（70） | high | true | 同上 | standoff_release_and_return | `standoffFrom "2099-01"`（⇒ false） |
| `p_edge` | AC_HIGH | 252（70） | high | true | `[{options:[a1], count:1}]` | launch_from_map_edge | |
| `p_low` | AC_LOW | 252（70） | low | true | `[{options:[f1], count:1}]` | low_strike | |
| `p_multi` | AC_LOW | 252（70） | low | true | `[{options:[c1, a1, u1], count:1}]` | low_strike | |
| `p_spot` | UAV | 108（30） | low_mid | true | — | spotter | |
| `p_awacs` | AC_HIGH | 252（70） | high | true | — | awacs | `whileAlive.cruiseMissilesAvoidAirDefense: true` |

- 除注明外系统 3–14 使用 M1 占位实现：不产生事件；占位 `ImpactSystem` 在收到 `ThreatArrived` 的同一步 `Remove` 该目标。
- "用脚本随机"指 `SimConfig.RandomOverride = (name, seed) => name == "<子流>" ? new ScriptedRandom(...) : null`。`ScriptedRandom.NextInt` / `Range` 必须与 `SimRandom` 同样实现（`NextInt` = `Bounded` 作用于脚本给出的 `NextUInt32` 序列；`Range` = `min + (max − min) × 脚本的 NextDouble`）。

### 7.1 波次生成（WS01-005 生成部分）

**T-01-01 时间表与组内间隔**
波次 `w1 { atGameSec 2, groups: [{ enemy u1, count 3, entry eE, spacingGameSec 0.5, route {direct}, target {structure s1} }] }`。`movement` 用脚本随机 `NextDouble = [0.5, 0.0, 0.25]`。
- 第 119 步后：`Threats.Count == 0`，`AllWavesSpawned == false`。
- 第 120 步事件依次：`WaveStarted { WaveId "w1", AiTags null, Injected false, AtSec 120.0 }`、`ThreatSpawned { ThreatId 4, DefId "u1", Kind Munition, EntryId "eE", WaveId "w1", AtSec 120.0 }`。第 150、180 步各一个 `ThreatSpawned`（ID 5、6，`AtSec` 150.0、180.0）。
- 第 120 步后威胁 4：`Pos == (25000, 10000)`，`AltM == 1250.0`，`VelMps == (−50, 0)`；第 121 步后 `Pos == (24950, 10000)`、`PathS == 50.0`。威胁 5 的 `AltM == 500.0`，威胁 6 的 `AltM == 875.0`。
- 第 179 步后 `AllWavesSpawned == false`；第 180 步后 `true`；`SpawnedThreatCount == 3`。

**T-01-02 小数生成时刻**
`w1 { atGameSec 1, groups: [{ enemy u1, count 3, entry eW, spacingGameSec 0.01, route {direct}, target {structure s1} }] }`（间隔 0.6 秒）。
- 生成步与 `AtSec`：第 60 步 `60.0`，第 61 步 `60.6`，第 62 步 `61.2`（`SpawnAtSec` 逐位等于 `60.0 + k * 0.6`）。
- 第 61 步后威胁 5：`PathS = 19.99999999999993`。第 62 步后 `PathS` 依次为 `100.0`、`69.99999999999993`、`39.99999999999986`；`Pos.X` ≈ `−4900, −4930, −4960`。

**T-01-03 atGameSec 0**
`w1 { atGameSec 0, …, count 1, entry eW }`：第 1 步生成；`ThreatSpawned.AtSec == null`、`WaveStarted.AtSec == null`；第 1 步后 `PathS == 50.0`。

**T-01-04 同时刻多波的顺序**
`wA { atGameSec 1, groups: [{u1, count 2, entry eE, 无 spacing, direct, structure s1}] }`、`wB { atGameSec 1, groups: [{d1, count 1, entry eW, direct, structure s2}] }`（数据顺序 wA、wB）。第 60 步事件顺序：`WaveStarted(wA)`、`ThreatSpawned(4)`、`ThreatSpawned(5)`、`WaveStarted(wB)`、`ThreatSpawned(6)`。威胁 4、5 位置相同。

**T-01-05 weighted_random**
`w1 { atGameSec 1, groups: [{u1, count 4, entry eE, direct, target {mode weighted_random}}] }`；`spawn` 用脚本随机 `NextDouble = [0.55, 0.0, 0.5, 0.95]`（总权重 10）。
预期 `TargetStructureId` 依次 `2, 1, 2, 3`（`r = 5.5, 0, 5.0, 9.5`；`r = 5.0` 不满足 `r < 5` ⇒ 选 s2）；`TargetPos` 为对应结构位置；`TargetKind == Structure`。脚本序列恰好用完（再多取一次会抛异常）。

**T-01-06 weighted_random 排除已摧毁目标**
同 T-01-05 但 `count 2`，在第 1 步前经 03 的接口把 s1 标为已摧毁（03 实现前用测试替身 `StructureRules.IsDestroyed`）。脚本 `[0.0, 0.9]`：总权重 5 ⇒ `r = 0` → s2，`r = 4.5` → s3。再把 s1、s2、s3 全部标为已摧毁，脚本 `[0.0]` ⇒ 回退到全部保护目标，选 s1。

**T-01-07 known_targets / air_defense**
- 默认钩子：`target {mode known_targets}`，脚本 `[0.0]` ⇒ 回退 `weighted_random` ⇒ s1。`air_defense` 同理。
- `EnemyAiHooksOverride` 的 `SelectKnownTarget` 返回 `TargetChoice(PlayerUnit, (12000, 8000), 0, 77)`，不消耗随机数；`spawn` 脚本序列为空。预期：`TargetKind == PlayerUnit`、`TargetUnitId == 77`、`Path == [(25000,10000), (12000,8000)]`，无异常（未消耗随机数）。

**T-01-08 诱饵 decoy_flight**
`w1 { atGameSec 2, groups: [{d1, count 1, entry eE, direct, target {mode decoy_flight}}] }`，`spawn` 脚本 `[0.0]`（假目标 s1）。
- `Path == [(25000,10000), (10000,10000), (0,10000)]`，`PathEnd == Exit`，`TargetKind == AimPoint`，`TargetStructureId == 0`。
- `AltM == 300.0` 全程不变（不下降）。第 400 步后 `Pos == (11000, 10000)`。
- 第 620 步：`ThreatExited { Reason DecoyPathEnd, AtSec 620.0 }`，威胁被删除；全程没有 `ThreatArrived`。
- 变体：`route {waypointsM: [[15000, 15000]]}`：`Path == [(25000,10000), (15000,15000), (10000,10000), X]`，`X ≈ (0, 0)`（容差 1e-9）。

**T-01-09 不进入地图的波次源**
`w1 { atGameSec 1, groups: [{p_bomb, count 2, entry eE, spacingGameSec 0, route {waypointsM [[20000,15000]]}, target {structure s1}}] }`。
预期第 60 步：6 个 `ThreatSpawned`（ID 4–9，`DefId "c1"`，`Kind Munition`，`EntryId "eE"`，`WaveId "w1"`），没有 `Kind == Platform` 的实体，没有 `MunitionReleased`；每个 `ParentThreatId == 0`，`Path == [(25000,10000), (20000,15000), (10000,10000)]`。`spawn` 子流共消耗 2 次 `NextUInt32`（每架一次 `NextInt(0,1)`）。

**T-01-10 挂载选择**
`p_multi`，`target {structure s1}`，`spawn` 脚本 `NextUInt32 = [7]`：`Bounded(3)` 阈值 1，7 % 3 = 1 ⇒ 选 `a1`（第 60 步出现 `MunitionReleased`，子弹药 `DefId "a1"`）。脚本 `[0, 5]`：0 被拒，5 % 3 = 2 ⇒ `u1`。

**T-01-11 剧情注入波次**
`waves` 含 `w_story { atGameSec 1, groups: [{u1, count 2, entry eE, spacingGameSec 0.5, direct, structure s1}] }`；`events.json` 有一个事件，其动作 `{ type spawn_wave, wave "w_story" }`（触发器任意，测试中不由 04 执行）。
- `Create` 后 `Pending.Count == 0`；第 1 步后 `AllWavesSpawned == true`；第 60 步无生成。
- 第 49 步后测试代码直接执行 `State.Waves.Injections.Add(new WaveInjection("w_story", 49.0))`；第 50 步：`WaveStarted { Injected true, AtSec 50.0 }`、`ThreatSpawned(AtSec 50.0)`；第 50 步后 `AllWavesSpawned == false`、`Injections.Count == 0`；第 80 步生成第二个，之后 `AllWavesSpawned == true`。
- 注入不存在的 `"nope"` → 下一次 `Step()` 抛 `InvalidOperationException`。

**T-01-12 模板航线被拒绝**
`groups[0].route = { template: "river" }`（夜晚下标 0、波次下标 0、组下标 0）。`SimWorld.Create` 抛 `SimSetupException`，消息恰为：
`[E_NOT_IMPLEMENTED] levels/mini/waves.json $.nights[0].waves[0].groups[0].route.template: 航线模板尚未实现（WS02-004）`

### 7.2 移动与剖面（WS01-005）

**T-01-20 折线跟随、转弯、悬停**
保护目标改为 `t0 (100, 100) weight 1`；`w1 { atGameSec 1, groups: [{p_spot, count 1, entry e0, route {waypointsM [[100,0]]}, target {structure t0}}] }`。
- `Path == [(0,0), (100,0), (100,100)]`，`PathEnd == Hold`，`AltM == 1000.0`（全程）。
- 第 63 步后：`Pos == (90, 0)`，`VelMps == (30, 0)`；第 64 步后：`Pos == (100, 20)`，`VelMps == (0, 30)`；第 66 步后：`(100, 80)`。
- 第 67 步后：`Pos == (100, 100)`，`Phase == Holding`，`VelMps == (0, 0)`，`PathS == 200.0`；之后不再变化，没有任何 `ThreatArrived` / `ThreatExited`。

**T-01-21 巡航末段直线下降与到达**
保护目标 `t0 (1000, 0)`；`m100`、`entry e0`、`direct`、`atGameSec 1`。
- `TerminalStartS == 900.0`（`1000 − 100 / 0.9999999999999999`）。
- 第 61 步后：`PathS 50`、`AltM 100`、`VertSpeedMps 0`；第 78 步后：`PathS 900`、`AltM 100`、`VertSpeedMps −50`；第 79 步后：`PathS 950`、`AltM 50`、`VertSpeedMps −50`。
- 第 80 步：`ThreatArrived { ThreatId 2, DefId "m100", Pos (1000, 0), TargetKind Structure, TargetStructureId 1, TargetUnitId 0, AtSec 80.0 }`；该步 `EnemyMovementSystem` 之后 `Phase == Arrived`、`AltM == 0`、`ArrivedAtSec == 80.0`（用 Order 3 的记录替身读取）；第 80 步结束后已被占位 `ImpactSystem` 删除。

**T-01-22 高度掷骰与子流消耗**
`w1 { atGameSec 1, groups: [{u1, count 1, entry eE, direct, structure s1}, {d1, count 1, entry eE, direct, structure s1}] }`；`movement` 脚本 `NextDouble = [0.25, 0.9]`。
预期：u1 `AltM == 875.0`（`500 + 1500 × 0.25`），d1 `AltM == 300.0`（规则带 `low {300,300}`，仍消耗 1 次）。序列恰好用完。

**T-01-23 俯冲加速（diveFaster）**
保护目标 `t0 (1025, 0)`；`l1`、`entry e0`、`direct`、`atGameSec 1`。
- `TerminalStartS == 925.0`，`SpeedMps == 50`，`TerminalSpeedMps == 100`。
- 第 78 步后：`PathS 900`、`AltM 100`；第 79 步后：`PathS 975`、`AltM 50`、`VertSpeedMps −100`。
- 第 80 步：`ThreatArrived.AtSec == 79.5`。

**T-01-24 弹道抛物线（忽略航点）**
保护目标 `t0 (10000, 0)`；`b1`、`entry e0`、`route {waypointsM [[5000, 5000]]}`、`atGameSec 1`。
- `Path == [(0,0), (10000,0)]`，`Profile == Parabolic`，`StartAltM == 4999.999999999999`（`10000 × tan45 / 2`）。
- 第 61 步后：`PathS 2000`、`AltM 4799.999999999999`、`VertSpeedMps −399.9999999999999`；第 62 步后：`AltM 4199.999999999999`、`VertSpeedMps −799.9999999999998`；第 64 步后：`AltM 1799.9999999999998`。
- 第 65 步：`ThreatArrived.AtSec == 65.0`。
- 换成 `q1`：`StartAltM == 2886.751345948128`；`movement` 子流不消耗（`b1`、`q1` 都不掷骰）。

**T-01-25 高空俯冲**
地图 `40000 × 20000`；保护目标 `t0 (30000, 0)`；`h1`、`entry e0`、`direct`、`atGameSec 0`。
- `StartAltM == 10000`，`TerminalStartS == 20000.0`。
- 第 19 步后 `AltM 10000`、`VertSpeedMps 0`；第 21 步后 `AltM 9000`、`VertSpeedMps −1000`；第 25 步后 `AltM 5000`。
- 第 30 步：`ThreatArrived.AtSec == 30.0`。

**T-01-26 平台远程投放滑翔炸弹并返航**
地图 `60000 × 20000`；保护目标 `t0 (50000, 0)`；`w1 { atGameSec 1, groups: [{p_glide, count 1, entry e0, direct, structure t0}] }`。
- 平台（ID 2）：`Releases == [{LoadoutIndex 0, MunitionId "g1", Count 2, AtS 30000.0, Done false}]`，`TurnS == 30000.0`，`Path == [(0,0), (30000,0), (0,0)]`，`PathEnd == Exit`，`AltM == 8000`。
- 第 489 步：两个 `MunitionReleased { ParentThreatId 2, ThreatId 3 / 4, DefId "g1", AtSec 488.57142857142856 }`；平台 `Phase == Egress`。子弹药第 489 步后：`PathS ≈ 85.71428571428896`（容差 1e-6），`Pos ≈ (30085.71428571429, 0)`，`AltM ≈ 7965.7142857142835`，`VertSpeedMps ≈ −80.0`，`WaveId == "w1"`。第 539 步后子弹药 `AltM ≈ 3965.7142857142844`。
- 第 589 步：两个 `ThreatArrived`（ID 3、4 顺序），`AtSec ≈ 588.5714285714286`。
- 第 700 步后平台 `Pos == (15200, 0)`；第 918 步：`ThreatExited { ThreatId 2, Reason EgressComplete, AtSec ≈ 917.1428571428571 }`。
- `movement` 子流：只有平台消耗 1 次（滑翔子弹药用平台高度）。

**T-01-27 standoff 未生效 ⇒ 飞到目标上空投弹**
同 T-01-26，平台换成 `p_glide_old`。投放 `AtS == 50000`；第 775 步：`MunitionReleased`（`AtSec ≈ 774.2857142857143`），子弹药路径长度 0，同一步紧接着 `ThreatArrived`（同 `AtSec`、`Pos (50000, 0)`）；平台第 1489 步离开（`AtSec ≈ 1488.5714285714287`）。

**T-01-28 一生成就投放（无 releaseRangeKm）**
`p_edge`、`entry eE`、`route {waypointsM [[20000, 15000]]}`、`structure s1`、`atGameSec 1`；`movement` 脚本 `[0.0, 0.5]`。
第 60 步事件顺序：`ThreatSpawned { ThreatId 4, Kind Platform }`、`MunitionReleased { 4 → 5, DefId "a1" }`、`ThreatExited { 4, EgressComplete }`，`AtSec` 都是 `60.0`；平台被删除。子弹药 5：`Path == [(25000,10000), (20000,15000), (10000,10000)]`，`AltM == 50.0`，`ParentThreatId == 4`。

**T-01-29 无制导炸弹（carrier）**
地图 `20000 × 20000`；保护目标 `t0 (7000, 0)`；`p_low`、`entry e0`、`direct`、`atGameSec 1`。
第 160 步：`MunitionReleased { DefId "f1", AtSec 160.0 }`，紧接 `ThreatArrived { Pos (7000, 0), AtSec 160.0 }`。平台第 260 步离开（`AtSec 260.0`）。子弹药 `Tag == null`。

**T-01-30 改航接口 `Retarget`**
保护目标 `t0 (1000, 0)`；`m100`、`entry e0`、`direct`、`atGameSec 0`。用 Order 5 的测试替身在第 10 步调用 `ThreatRouting.Retarget(ctx, th, (500, 400))`。
- 调用时 `th.Pos == (500, 0)`；返回 `true`；之后 `PathVersion == 2`、`Path == [(500,0), (500,400)]`、`TerminalStartS == 300.0`、`StartAltM == 100`、`AnchorSec == 10`。
- 第 12 步后 `Pos == (500, 100)`；第 18 步：`ThreatArrived { Pos (500, 400), AtSec 18.0, TargetStructureId 1 }`。
- 对平台调用返回 `false`；在 Order 1 替身中调用抛 `InvalidOperationException`（`LastUpdateSec != TimeSec`）。

**T-01-31 返航接口 `BeginEgress`**
地图 `60000 × 20000`；保护目标 `t0 (50000, 0)`；`p_glide`、`entry e0`、`direct`、`atGameSec 0`。Order 12 替身在第 30 步调用 `BeginEgress`。
- 调用时 `Pos == (2100, 0)`；之后 `Phase == Egress`、`Path == [(2100,0), (0,0)]`、`Releases[0].Done == true`。
- 第 60 步：`ThreatExited { Reason EgressComplete, AtSec 60.0 }`；全程没有 `MunitionReleased`。

**T-01-32 反辐射归航（`HomingUnitId`）**
保护目标 `t0 (1000, 0)`；部署方案含一个探测单位（任意 `sensors` 定义）于 `(800, 300)`，其实体 ID 记为 `R`（= 2）；`m100`、`entry e0`、`direct`、`atGameSec 0`（威胁 ID 3）。
- 第 4 步后测试代码设 `th.HomingUnitId = R`。第 5 步后：`PathVersion == 2`、`Path == [(200,0), (800,300)]`、`TargetUnitId == R`、`TargetKind == PlayerUnit`、`Pos ≈ (244.72135954999578, 22.360679774997894)`；`ThreatArrived.AtSec ≈ 17.41640786499874`（第 18 步）。
- 变体：第 4 步后同时 `Remove(R)`：不改航，第 20 步到达 `(1000, 0)`。

**T-01-33 已到达目标不再移动**
同 T-01-21，但 Order 10 替身为空操作（不删除）。第 80 步之后每步：威胁仍 `Alive`、`Phase == Arrived`、`Pos == (1000, 0)`，不再产生任何事件。

**T-01-34 绕行钩子（A‑50）**
`EnemyAiHooksOverride.AdjustAvoidance` = 在首末点之间插入 `(12345, 6789)`。波次：`wA { atGameSec 1: [{c1, count 1, eE, direct, s1}] }`、`wB { atGameSec 2: [{p_awacs, count 1, eE, direct, s2}] }`、`wC { atGameSec 3: [{c1, count 1, eE, direct, s1}, {u1, count 1, eE, direct, s1}] }`。
预期：wA 的 c1 `Path == [eE, s1]`（A‑50 尚未出现）；wC 的 c1 `Path == [eE, (12345,6789), s1]`；wC 的 u1（UAV）不修正。

### 7.3 解析预测（WS01-005，供 WS01-010）

**T-01-40 `Predict` 公式**
直接构造威胁（`ThreatTestFactory`）：`Path [(0,0),(100,0),(100,100)]`、`AnchorSec 0.5`、`AnchorS 0`、`SpeedMps = TerminalSpeedMps = 7`、`TerminalStartS = 200`、`StartAltM = EndAltM = 50`、`Profile Linear`、`PathEnd Hold`、`LastUpdateSec 0.5`。
`Predict(th, 10)` → `Pos (66.5, 0)`、`VelMps (7, 0)`、`AltM 50`；`Predict(th, 20)` → `(100, 36.5)`、`VelMps (0, 7)`；`Predict(th, 37.25)` → `(100, 100)`、`AtPathEnd true`、`VelMps (0,0)`。`Predict(th, 0.0)` → `ArgumentOutOfRangeException`。

**T-01-41 预测 == 实际（逐位）**
T-01-20 的世界：第 61 步后取 `p = Predict(th, 66.0)`；推进到第 66 步，`th.Pos == p.Pos`、`th.AltM == p.AltM`、`th.VelMps == p.VelMps`（`==` 比较）。T-01-24 的世界：第 61 步后 `Predict(th, 64.0)` 与第 64 步后状态逐位相等。

**T-01-42 `Legs`**
- T-01-20 的世界，第 60 步后 `Legs(th, 60.0)`：3 段：`[60, 63.333333333333336]` `VelMps (30,0)`、`StartPos (0,0)`；`[63.333333333333336, 66.66666666666667]` `VelMps (0,30)`、`StartPos (100,0)`；`[66.66666666666667, +∞]` `VelMps (0,0)`、`StartPos (100,100)`。各段 `StartAltM 1000`、`VertSpeedMps 0`、`VertAccelMps2 0`。在 `t = 61, 64.5` 用段公式算出的位置与 `Predict` 相差 ≤ 1e-6 m。
- T-01-24 的世界，第 60 步后 `Legs(th, 60.0)`：1 段 `[60, 65]`，`StartAltM 4999.999999999999`、`VertSpeedMps 0`、`VertAccelMps2 −399.99999999999994`；段公式在 `t = 62` 给出 `AltM 4199.999999999999`（与 `Predict` 差 ≤ 1e-6）。
- `PredictArrivalSec`：T-01-21 的世界第 61 步后返回 `80.0`；T-01-20（Hold）返回 `null`。

### 7.4 地形与视线（WS01-006）

**T-01-50 双线性采样**
`Heightmap(WidthPx 3, HeightPx 2, MetersPerPixel 10, ElevationM [0, 10, 20, 30, 40, 50])`（第 0 行为北）。

| (x, y) | 预期 `ElevationAt` |
|---|---|
| (5, 15) | `0.0`（像素 (0,0) 中心） |
| (15, 10) | `25.0` |
| (10, 10) | `20.0` |
| (12, 7) | `31.0` |
| (25, 5) | `50.0` |
| (15, 20) | `10.0`（北边缘，钳到第 0 行） |
| (0, 0) | `30.0`（西南角，钳到像素 (1,0)） |

**T-01-51 地图外**
同上网格：`(−100, 100) → 0.0`；`(30, 0) → 50.0`；`(1000, 12) → 29.0`（x 钳到最右列，y 插值）。

**T-01-52 山脊遮挡与临界高度（无曲率）**
`11 × 3` 像素、`MetersPerPixel 100`，每行 `[0,0,0,0,0,100,0,0,0,0,0]`；规则 `losSampleStepPx 0.5, earthRadiusM null`。观察者 `a = (50, 150)`、`aMsl = 10`；目标 `b = (1050, 150)`。

| `bMsl` | 预期 | 说明 |
|---|---|---|
| 200 | 可见 | |
| 190 | 可见 | 第 10 个样本（x = 550）射线高 100 = 地形 100，严格大于才遮挡 |
| 189.99 | 遮挡 | |
| 189 | 遮挡 | |

另：观察者 `a = (80, 150)`、`bMsl = 150` → 遮挡；`bMsl = 200` → 可见。步长改为 `2.0` 像素（样本 x = 250, 450, 650, 850，跨过了山脊中心）时 `bMsl = 150` → 可见（证明步长来自数据）。`a = (450,150)`、`b = (490,150)`（距离 40 ≤ 步长 50）→ 可见。

**T-01-53 地球曲率**
`201 × 1` 像素、`MetersPerPixel 100`、全 0；`earthRadiusM 1000000, refractionK 1`（`ReffM = 1e6`）。`a = (50, 50)`、`b = (20050, 50)`（d = 20000，中点凸起 50 m）。

| 两端海拔 | 预期 |
|---|---|
| 60 / 60 | 可见 |
| 50 / 50 | 可见（中点恰好擦边） |
| 49.99 / 49.99 | 遮挡（首个遮挡样本 i = 198） |
| 40 / 40 | 遮挡 |

`earthRadiusM null` 时 10 / 10 → 可见。`CurvatureDropM(10000, 20000) == 50.0`。

**T-01-54 快速接受**
T-01-52 的网格（`MaxElevationM == 100`）：`aMsl = bMsl = 100.000002`（> 100 + 1e-6）→ 可见，且不调用采样（用计数替身验证 `ElevationAt` 调用次数为 0）。`aMsl = 100.0000005` → 进入逐样本计算（结果可见）。

**T-01-55 test_01 东北山脊（正式高程图，集成测试）**
读取 `data/levels/test_01/map/heightmap.png`（200 × 200、100 m/像素、80–330 m）；**测试自带** `TerrainRulesDef { LosSampleStepPx 0.5, EarthRadiusM 6371000, RefractionK 4/3（= 4.0 / 3.0）, DefaultAntennaHeightM 10 }`（不依赖正式规则文件）。
- `MaxElevationM ≈ 290.6202792401007`；`ElevationAt(15500, 11500) ≈ 133.64309147783626`；`ElevationAt(11500, 15500) ≈ 139.62462806134127`；`ElevationAt(13500, 13500) ≈ 247.85782406347752`（山脊上）；`ElevationAt(26000, 14000) == ElevationAt(19950, 14000)`（地图外常值延伸）。
- 观察者：备用阵地 `alt_east (15500, 11500)`，天线 10 m（`aMsl = E + 10`）。目标 `(11500, 15500)`（山脊西北侧）：AGL `50 / 100 / 150 / 200` → **遮挡**；AGL `300 / 500` → 可见。最低可见 AGL ≈ 223.97 m：AGL 220 → 遮挡，AGL 228 → 可见。
- 对照（不越山脊）：目标 `(11500, 7500)`，AGL 50 → 可见。
- 这验证 WS01-006 验收"山后低空目标不可见"：Kh‑101 型巡航导弹（30–70 m）在山脊背后对该阵地的雷达不可见。

**T-01-56 加速实现 == 参考实现**
在 T-01-55 的地形上，用 `new SimRandom(1)` 依次生成 2000 组 `(ax, ay, bx, by)`（各 `Range(−2000, 22000)`）与 `(aAgl, bAgl)`（各 `Range(0, 400)`）：`HasLineOfSightAgl` 与"参考实现 + `ElevationAt` 计算的海拔"结果完全一致。若实现了分块最大值加速，再用 T-01-52 / T-01-53 的网格各跑 2000 组。

**T-01-57 AGL 包装**
T-01-52 网格：`HasLineOfSightAgl((50,150), 10, (1050,150), 190) == HasLineOfSight((50,150), 10, (1050,150), 190)`（地形 0 ⇒ 相同）。

### 7.5 数据加载与确定性

**T-01-60 `rules/movement.json` 加载**
- 7.0 的测试值：`CruiseDescentAngleRad == 0.7853981633974483`，`QuasiBallisticTerminalAngleRad == 0.5235987755982988`，`AltitudeBandsM[AltitudeBand.High] == MinMax(8000, 8000)`。
- 缺 `glide` 键 → `[E_MISSING_FIELD] rules/movement.json $.altitudeBandsM.glide: 缺少必填字段`。
- 多出 `ballistic` 键 → `[E_UNKNOWN_FIELD] rules/movement.json $.altitudeBandsM.ballistic: 未知字段`。
- `highDiveAngleDeg 90` → `[E_RANGE] rules/movement.json $.highDiveAngleDeg: 取值 90 超出范围 (0, 90)`。
- `diveSpeedMult 0.5` → `[E_RANGE] rules/movement.json $.diveSpeedMult: 取值 0.5 超出范围 ≥ 1`。

**T-01-61 `rules/terrain.json` 加载**
`losSampleStepPx 0` → `[E_RANGE] rules/terrain.json $.losSampleStepPx: 取值 0 超出范围 > 0`；`earthRadiusM null` → `EarthRadiusM == null`，`TerrainModel.ReffM == null`。

**T-01-62 交叉校验**
- 平台 `loadout[0].options[0] = "nope"` → `[E_UNKNOWN_REF] enemies/platforms.json $.platforms[0].loadout[0].options[0]: 引用的 敌方单位 "nope" 不存在`。
- 波次组 `enemy "f1"`（carrier）→ `[E_RANGE] levels/mini/waves.json $.nights[0].waves[0].groups[0].enemy: 取值 f1 超出范围 由载机投放的弹药不能直接出现在波次中`。
- 平台 `altitudeBand "ballistic"` → `[E_RANGE] enemies/platforms.json $.platforms[0].altitudeBand: 取值 ballistic 超出范围 very_low … high`。

**T-01-63 确定性**
`Mini01` + T-01-01、T-01-05、T-01-26、T-01-28 的全部波次合在一夜（真实 `SimRandom`，seed `0x6DD180096484586D`），两个世界各推进 1000 步：每步 `ComputeStateHash()` 相等；`DrainEvents()` 序列逐项相等。把 seed 换成 `0x92C4A19D40D3C63D`：第 60 步后某个 u1 的 `AltM` 不同（`movement` 子流不同）。

---

## 8. 待决问题

### 8.1 需要人决定

| # | 问题 | 背景 | 建议默认值（理由） |
|---|---|---|---|
| Q1 | 高度带 → 米（`rules/movement.json` 的 `altitudeBandsM`） | 数值表只给出 Shahed（500–2000 m）与 Kh‑101（30–70 m）的具体高度，其余只写"极低 / 低 / 中……" | `very_low {30,100}`、`low {100,1000}`、`low_mid {500,3000}`、`mid {3000,6000}`、`mid_high {5000,9000}`、`high {9000,12000}`、`high_dive {12000,20000}`（Kh‑22 / 锆石的巡航段）、`glide {8000,12000}`（地面发射滑翔弹的起始高度）。均为 AGL。定义中有 `altitudeM` 的以定义为准 |
| Q2 | 弹道 / 俯冲几何 | 数值表只写"弹道 / 准弹道 / 末端机动 / 高空俯冲"；WBS 要求"弹道目标按抛物线下落" | 地图内一段为以进入点为顶点的抛物线，用落地倾角参数化：`ballisticTerminalAngleDeg 70`、`quasiBallisticTerminalAngleDeg 40`、`highDiveAngleDeg 45`、`cruiseDescentAngleDeg 30`、`diveSpeedMult 2`；数据中的速度按**水平速度**使用；`terminal_maneuver` 轨迹同准弹道，机动只体现在 `interceptProbMult`。由平台投放的弹道弹（匕首）在投放瞬间高度从平台高度跳到抛物线顶点高度（简化，不影响落点） |
| Q3 | 传感器 / 火控雷达的天线离地高度从哪里来 | 视线需要观察者海拔；`sensors.json` / `air_defense.json` 没有该字段 | 由 02 决定；建议在 `sensors.json` 与 `air_defense.json` 单位上增加可选 `antennaHeightM`，缺省用 `rules/terrain.json` 的 `defaultAntennaHeightM`（建议 10 m）；系留气球可填数百米 |
| Q4 | 一生成就投放的平台（Tu‑22M3、MiG‑31K、Su‑24M 带 Kh‑59）在地图上停留多久 | 数值表说 Tu‑22M3"S‑200/Patriot 可打"，但按本规则平台同一步生成、投放、离开，玩家打不到 | 默认按本规则（停留 0 秒）；若要可打，给 `rules/movement.json` 增加 `launchLingerSec`（平台投放后先原地盘旋该时长再返航），并相应改 3.1.8 |
| Q5 | 无挂载平台（Orlan‑10、A‑50、直升机、Orion 无挂载时）走完航线后做什么 | 数值表只写行为名 | 悬停在航线终点直到夜晚结束（存活效果持续）；后果：有这类平台存活时 `AllClear` 不会触发 |
| Q6 | 弹道 / 滑翔类弹药的 `waypointsM` | 物理上不走折线 | 忽略并直飞（`tools/validate` 给出警告）。备选：加载报错 `E_RANGE` |
| Q7 | 平台挂载 `count: null`（数值表未给数量，如 Su‑25、Su‑35S、Orion） | 必须有个数 | 按 1 枚；建议数值表补数 |
| Q8 | `maxSpeedKmh` 是否使用 | 平台有巡航 / 最大速度两个值 | 不使用（返航、规避都用巡航速度）；保留字段供以后"遭拦截时加速脱离" |
| Q9 | `weighted_random` 按每个目标独立抽签，还是按组抽一次 | GDD 未说明 | 每个目标独立抽签（分散压力，符合"按权重分布"直觉）；需要集中打击时数据用 `structure` 指定 |
| Q10 | 被 `spawn_wave` 引用的波次是否也按 `atGameSec` 自动生成；注入时 `atGameSec` 的含义 | `events.json` 与 `waves.json` 都能决定时间 | 被引用的波次**不**自动生成；注入时以注入时刻为本波起点，`atGameSec` 不使用 |
| Q11 | `aiTags` 在生成 / 移动层的效果 | GDD 7.4 的"饱和 = 同一时刻多方向集中到达"可以在生成层自动调整生成时间；"绕行"可以自动生成航线 | 本文件不解释 `aiTags`（只写入 `WaveStarted`）；饱和、绕行由数据作者通过时间与航点表达，04 若要自动化，在 04 中定义并通过注入 / 钩子实现 |
| Q12 | 巡航剖面的高度按 AGL 恒定（贴地）还是按海拔恒定 | 对 500 m 以上的目标几乎没有区别；对 30–70 m 的巡航导弹，AGL 恒定即"地形跟随" | 全部按 AGL 恒定（实现简单、与"低空突防沿地形"一致） |
| Q13 | 诱饵（`decoy_flight`）的终点 | Schema 只说"只飞航线不攻击" | 以按权重随机选出的保护目标为假目标点，飞越后沿末段方向直线飞出地图（`ThreatExited`），不落地；备选：飞到假目标点后坠毁（`ThreatArrived`、伤害由 03 按 `damageLevel` 结算） |
| Q14 | 地球曲率是否计入视线 | GDD 8.1"地形和地平线形成低空盲区" | 计入：`earthRadiusM 6371000`、`refractionK 4/3`（标准大气折射的有效地球半径，公开的物理约定） |
| Q15 | 视线采样步长 | 精度与性能的取舍 | `losSampleStepPx 0.5`（半个像素，保证不跨过单个像素的山脊顶点） |

### 8.2 需登记到 00_core

| 表 / 位置 | 编号建议 | 内容 |
|---|---|---|
| 1.1 全局目录文件表 | 21、22 | `rules/movement.json`（`kind: movement`，`MovementRulesDef`，细化 01）；`rules/terrain.json`（`kind: terrain`，`TerrainRulesDef`，细化 01）。T-00-35 的 `LoadedFiles.Count` 随之改为 31 |
| 1.6 `RulesSet` | — | 追加 `MovementRulesDef Movement`、`TerrainRulesDef Terrain`（字段见本文件 1.5、1.6） |
| 1.6 敌方模型 | — | `MunitionCategory`、`AltitudeBand` enum（本文件 1.2）；`PlatformDef` 全字段及 `LoadoutEntryDef`、`PlatformWhileAliveDef`、`OtherArmament`、`PlatformBehavior`（本文件 1.3） |
| 1.5 / 1.6 `Heightmap` | — | 内部以 `double[]` 存储，增加 `internal double[] ElevationArray`（`TerrainModel` 零复制引用） |
| 1.2 第 15 条交叉引用 | — | `platforms[].loadout[].options[]` ∈ 弹药 ID（`E_UNKNOWN_REF`，类别 `敌方单位`） |
| 1.2 新增校验 | V1 | `rules/movement.json`：`altitudeBandsM` 恰好 8 个键（缺 → `E_MISSING_FIELD`，多 → `E_UNKNOWN_FIELD`）；角度 `(0, 90)`；`diveSpeedMult ≥ 1`；`rules/terrain.json`：`losSampleStepPx > 0`、`refractionK > 0`、`earthRadiusM` 为 null 或 > 0、`defaultAntennaHeightM ≥ 0`（均 `E_RANGE`，说明文字见 T-01-60、T-01-61） |
| 1.2 新增校验 | V2 | 波次组 `enemy` 为 `altitudeBand = carrier` 的弹药 → `E_RANGE`（`由载机投放的弹药不能直接出现在波次中`）；非 carrier 弹药 `speedKmh` 为 null 或 0 → `E_RANGE` |
| 1.2 新增校验 | V3 | 平台 `altitudeBand` 只允许 `very_low … high` → 否则 `E_RANGE`；平台 `cruiseSpeedKmh > 0`（Schema 已有） |
| 1.3 错误码表 | — | `E_NOT_IMPLEMENTED`：`SimWorld.Create` 时数据用到尚未实现的功能；Detail 格式见本文件 4.3 |
| 0.5 项目结构 | — | 领域目录追加 `Movement/`（`Nightwatch.Sim.Movement`：`ThreatKinematics`、`ThreatRouting`、`ThreatPath`、枚举）与 `EnemyAi/`（`Nightwatch.Sim.EnemyAi`：`IEnemyAiHooks`、`DefaultEnemyAiHooks`、`TargetChoice`；正式实现归 04） |
| 2.4 公共字段 | — | `Threat.VertSpeedMps` 的含义明确为 `d(AltM)/dt`（AGL 高度变化率） |
| 2.6 `SimContext` | — | 追加 `TerrainModel Terrain { get; }`、`IEnemyAiHooks EnemyAiHooks { get; }` |
| 2.6 `SimConfig` | — | 追加 `[JsonIgnore] IEnemyAiHooks? EnemyAiHooksOverride`（仅测试；写回放时非 null → `InvalidOperationException`，同 `RandomOverride`） |
| 3.2 `SimWorld.Create` | 3a | 第 3 步之后构造 `TerrainModel`、选定 `IEnemyAiHooks` |
| 2.5 / 3.7.2 单例组件 | 1 | `WaveState` 字段（本文件 2.3）；`PendingSpawn`、`WaveInjection` 类型 |
| 2.3 实体 | — | `Threat` 的 01 字段（本文件 2.2 表，含 `PendingRelease`）；`ThreatPhase`、`PathEndAction`、`MotionProfile`、`ThreatTargetKind`、`ThreatExitReason` enum |
| 2.7 快照 | — | `ThreatView` 字段；`GlobalView` 追加 `PendingSpawnCount`、`SpawnedThreatCount`、`AllWavesSpawned` |
| 4.2 事件总表 | 100–104 | 字段细化：`WaveStarted { WaveId, AiTags, Injected }`；`ThreatSpawned { ThreatId, DefId, Kind, EntryId, WaveId }`；`MunitionReleased { ParentThreatId, ThreatId, DefId }`；`ThreatArrived { ThreatId, DefId, Pos, TargetKind, TargetStructureId, TargetUnitId }`；`ThreatExited { ThreatId, DefId, Reason }` |
| 3.1.4 子流表 | — | 无新增。`spawn` 用途补充"挂载选择（`NextInt`）、04 钩子的目标选择"；`movement` 用途确认为"高度区间掷骰" |
| Q15（剧情事件） | — | 04 写入 `State.Waves.Injections`（`WaveInjection(WaveId, StartAtSec = ctx.TimeSec)`）；被 `spawn_wave` 引用的波次不进入自动时间表 |

### 8.3 与其他规格的边界

| # | 边界 | 本文件的假设 | 需要谁确认 |
|---|---|---|---|
| B1 | 保护目标"已摧毁"的判定 | 03 提供只读 `StructureRules.IsDestroyed(Structure)`（或等价字段）；`weighted_random` 排除已摧毁目标 | 03 |
| B2 | 路径改写（`PathVersion` 变化）后在飞拦截弹的处理 | 本文件只递增 `PathVersion`；03 决定拦截点重算 / 拦截弹失效 | 03 |
| B3 | 同一步内"先到达、后被拦截"的时间先后 | 第 2 步已发 `ThreatArrived`（`AtSec = 到达时刻`）；若 03 的拦截时刻早于 `ArrivedAtSec`，应由 03 判定拦截优先并阻止 `ImpactSystem` 结算；`Phase == Arrived` 的目标不得再被选为新的交战目标 | 03 |
| B4 | 视线调用频率 | 本文件只保证单次视线的定义与复杂度；"每步对哪些（传感器，目标）对做视线、是否每 K 步一次"是 02 的探测规则（必须写入数据，属于定义） | 02 |
| B5 | 天线高度来源 | 见 Q3 | 02 |
| B6 | 反辐射导弹何时设置 / 清除 `HomingUnitId`、初始目标如何选 | 02（归航随辐射状态）与 04（`air_defense` 选目标钩子）分工；本文件只执行"有归航目标就改航" | 02、04 |
| B7 | 电子战诱导 / 链路中断的移动后果 | 02 调用 `ThreatRouting.Retarget`（诱导点、坠落点）或 `BeginEgress`；坠落 = `Retarget` 到当前位置附近一点（路径极短，下一步到达，03 按落地结算） | 02 |
| B8 | `global_alert_on_takeoff`（MiG‑31K 起飞即全图警报）、弹道导弹发射预警 | 02 读取 `ThreatSpawned` + `PlatformDef.Behavior` / `MunitionDef.Category` 产生 `EarlyWarning` | 02 |
| B9 | Oreshnik 的 6 个子弹头 | 本文件不在飞行中分裂；03 在落地时按 `submunitions` 结算 6 次命中 | 03 |
| B10 | 已到达目标的删除 | 03 的 `ImpactSystem` 在同一步删除；WS01-011 之前由占位实现删除 | 03、00（占位） |
| B11 | `known_targets` / `air_defense` 的选择算法、A‑50 绕开防空圈的航线算法 | 04 实现 `IEnemyAiHooks`；只能用传入的 `spawn` 子流，`AdjustAvoidance` 不得用随机数 | 04 |
| B12 | 剧情注入波次后 `AllClear` 的时机 | `AllWavesSpawned` 只看当前待生成与待注入；若剧情会在之后注入波次，`EndWhenClear` 可能提前结束夜晚 | 04（必要时在剧情事件未全部触发前阻止 `AllClear`） |
| B13 | 地形服务被 02（探测）、03（交战射界）共用 | `TerrainModel` 放在 `SimContext`，接口见 2.5 | 02、03 |
