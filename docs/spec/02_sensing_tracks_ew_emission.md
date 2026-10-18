# 02 探测、航迹、电子战、辐射与暴露度

> 本文件覆盖"眼 / 盾 / 假"三类我方单位的全部模拟规则，以及防空单位自带火控雷达的探测与开关机。
> 术语、类型、子流名、实体类型、事件 / 命令名称以 [00_core.md](00_core.md) 为准；本文件在 D2b 审查中提出的登记项已全部合入 [00_core.md](00_core.md)（历史汇总保留在第 8.2 节备查）。

---

## 0. 范围与依据

### 0.1 覆盖范围

| 主题 | 系统（Step 序号，WBS 01.B） | 对应 WBS | 本文件章节 |
|---|---|---|---|
| 传感器探测、国家预警、误报、上报延迟、B 线空情转发、火控雷达 / 自主捕获作为传感器 | 3 `SensorSystem` | WS01-007 | 3.2 |
| 航迹关联、三级质量、交叉升级、超时丢失、精确持有者、诱饵甄别 | 4 `TrackFusionSystem` | WS01-008 | 3.3 |
| 导航干扰 / 欺骗、链路中断、效能随时期衰减、友军干扰、城区影响、车载防护罩、国家级导航欺骗的效果 | 5 `ElectronicWarfareSystem` | WS01-015 | 3.4 |
| 辐射策略状态机、触发规则、火控指示联动、关机时机 | 6 `EmissionSystem` | WS01-013、014 | 3.5 |
| 暴露度累积、开火增量、侦察、静默、转移、阈值事件 | 11 `ExposureSystem` | WS01-012 | 3.6 |
| 欺骗单位（诱饵辐射源、牺牲雷达、假发射车）、备用阵地 / 新阵地效能 | 分散在 3、6、11（见 3.7） | WS01-016 | 3.7 |
| 部署覆盖预计算查询（`CoverageQuery.ComputeGrid`，只读供客户端） | 灰盒客户端查询 | WS04-002 | 3.8 |

**不在本文件**：敌方目标的生成与移动（01，本文件通过 01 的 `ThreatRouting` 接口触发诱导改航、悬停与返航）、交战与拦截判定（03）、反辐射导弹 / 定点打击的**目标选择**（04 / 01，本文件只提供查询并维护 `HomingUnitId`）、外部支援的**呼叫流程**（03，本文件只实现国家级导航欺骗的**效果**）、部署状态机与转移执行（04）、天气 / 昼夜的战役层推进（05，本文件只实现昼夜、天气与冬季对探测和电子战的夜内修正）。

### 0.2 依据

- [GDD v1.3](../游戏设计文档_GDD_v1.md)：3.2–3.3（指挥权限、信息来源）、4.1（B 线空情"有延迟，精度最高为大致"）、5.2（指挥点操作、二选一）、7.4（敌方 AI）、8.1（探测与航迹质量）、8.2（辐射策略与反防空压制）、8.3（电子战）、8.5（雷达断电）、8.8（天气与昼夜）、11.3（新阵地首夜）、12.3（解锁节奏）、15.1–15.2（航迹显示、覆盖层）、17（敏感内容）。
- [数值表 v1.2](../塔防数值表_v1.md)：1.3（探测单位、航迹质量规则、火控指示、B 线限制）、1.4（电子战、效能衰减、副作用）、1.5（欺骗单位、备用阵地）、1.6（国家级导航欺骗）、3.1（精度档与电子战偏移）、3.3（拦截概率修正，仅引用）、3.4（暴露度）、3.5（辐射策略、触发规则、关机时机）、5.3（规则补充）。
- [WBS](../开发任务分解_WBS_v1.md)：01.A、01.B、WS01-007、008、012 – 016。
- 数据：`units/sensors.json`、`units/ew.json`、`units/deception.json`、`units/air_defense.json`（仅火控与自主捕获字段）、`units/weapons.json`（`reactionGameSec`）、`enemies/munitions.json`、`enemies/platforms.json`（仅本文件用到的标记）、`rules/tracks.json`、`rules/emission.json`、`rules/exposure.json`、`rules/ew.json`、`rules/positions.json`、`rules/terrain.json`（`defaultAntennaHeightM`）、`rules/engagement.json`（武器类别默认反应时间）、`rules/accuracy.json`（仅 `ewExtraCells`）、`support/support.json`（仅 `national_gnss_spoof`）、`levels/<id>/waves.json`（`entryPoints[].warningGameSec`、`weather`、`timeOfDay`、`season`）、`levels/<id>/map/layers.json`（`urban`）、`levels/<id>/map/deploy.json`（`alternatePositions`）。

### 0.3 依赖

- **00_core**：全部框架（`SimWorld`、`EntityStore`、`SimRandom`、`SpatialGrid`、事件 / 命令、数据加载契约、`SimTime`、`Vec2`、方位角约定、`Geo` 公共几何工具、`WeaponParams` 公共武器参数查询、`EnvironmentResolver.SeasonFor`）。
- **01**（[01_spawn_movement_terrain.md](01_spawn_movement_terrain.md)）：
  - 地形视线与地平线包络：`ctx.Terrain.BuildHorizonProfile(Vec2 pos, double antennaAglM, double maxRangeM) : HorizonProfile` 与 `HorizonProfile.HasLineOfSightAgl(Vec2 targetPos, double targetAglM) : bool`（高度均为 AGL；含等效地球曲率 $R_{\text{eff}} = k R_e$，见 01 §2.5、§3.3.4；A-2-26、B-T2-31、C-T2-01）。
  - 波次过滤：`WaveSpawnRules.IsStoryOnlyWave(LevelData level, string waveId) : bool`（01 §3.1.1，用于排除仅剧情注入的波次；A-2-28）。
  - 目标路径改写：`ThreatRouting.Retarget(SimContext ctx, Threat t, Vec2 newAim)`、`ThreatRouting.Hover(SimContext ctx, Threat t)`、`ThreatRouting.BeginEgress(SimContext ctx, Threat t)`（01 §3.2.8；A-2-27）。
  - `Threat` 的 `Pos`、`AltM`、`VelMps`、`Phase`（`ThreatPhase`）、`TargetUnitId`（由 01 唯一写入，本文件只读；A-2-04）与 `HomingUnitId`（01 拥有，本文件第 6 步写入、01 第 2 步 `ApplyHoming` 读取；A-2-06）。
- **03 / 04 / 05 跨规格交互**：本文件不依赖 03 / 04 的系统实现，只读取它们维护的实体字段（`FireUnit.RadarDestroyed`、`PlayerUnitCommon.SuspendedUntilSec`、`SupportAsset` 的 `State / CenterPos / RadiusM`、`SimConfig.CarryIn`）与事件，并在命令处理中调用 04 的 `CommandPointRules`（A-2-12、A-2-17、A-2-21、A-2-22）。

### 0.4 已作的关键选择（理由见各节）

| # | 选择 | 理由 | 章节 |
|---|---|---|---|
| D1 | **航迹按真实 `ThreatId` 关联**（不做空间关联，已决 B-T1-07） | 确定性强、实现简单、不会出现"错配"带来的不可复现 bug；战争迷雾通过质量、延迟、误差圈、误报航迹体现，而不是通过关联错误体现 | 3.3.1 |
| D2 | **"精确"是火力单元私有的**：航迹的 `PreciseHolderIds` 记录"哪些火力单元的自带火控雷达 / 自主捕获此刻锁定了它"（已决 B-T2-33） | 数值表 1.3：精确 = 防空系统**自带**火控雷达；若精确在网络中共享，一部雷达开机即可让全网发射导弹，火控指示联动就失去意义 | 3.3.4 |
| D3 | 探测是**确定性**的（在范围内且视线通就探测到），随机只用于误报、诱饵甄别、电子战判定 | 避免航迹逐步闪烁；数值表没有给出探测概率 | 3.2 |
| D4 | 电子战效能解释为**每个目标、每类效果只掷一次**的概率，结果锁存到当夜结束（已决 B-T3-08） | 每步重掷会让效果随停留时间无限累积，数值表的百分比失去意义 | 3.4 |
| D5 | 辐射策略的 `exposureMult` **不在模拟中相乘**，暴露度只在雷达实际开机时按基础速率累积（已决 B-T3-10：作为平衡验证的目标平均暴露系数） | 开关机状态机已经产生了时间占比上的差异，再乘系数会重复计算；`cueing.cued.exposureMult = 0.3` 恰好等于 `fireControlCued / fireControlSelfSearch = 0.6 / 2.0`，说明这些系数是"目标平均比值" | 3.5、3.6 |

---

## 1. 数据输入

> 换算规则见 00 的 0.4.2；下表"C# 字段"已是换算后的名字与单位。**标 ★ 的是本文件提出并已在 D2b 批准新增到 `data/` 与 Schema 的字段**（同时列在 8.2，裁决见第 8.1 节）。可选字段缺失时的处理写在"缺省"列，加载器不填默认值（00 的 1.2 第 6 条）。

### 1.1 `units/sensors.json` → `SensorDef`

| JSON 字段 | C# 字段 | 类型 / 单位 | 缺省 |
|---|---|---|---|
| `id` / `nameKey` | `Id` / `NameKey` | `string` | 必填 |
| `layer` | `Layer` | `SensorLayer { National = 0, Regional = 1, Local = 2 }` | 必填 |
| `detectionRangeKm` | `DetectionRangeM` | `double?`，米 | `null` = 覆盖由 `Coverage` 决定 |
| `coverage` | `Coverage` | `SensorCoverage? { FullMap = 0, UrbanAreas = 1 }` | `null` |
| `lowAltitude` | `LowAltitude` | `LowAltitudeCapability { Poor = 0, Medium = 1, Good = 2, VeryGood = 3 }` | 必填 |
| `largeLowAltitudeBlindZone` | `LargeLowAltitudeBlindZone` | `bool?` | `null` = false |
| `trackQuality` | `TrackQuality` | `TrackQuality` | 必填 |
| `trackQualityUpgrades[]` | `TrackQualityUpgrades` | `IReadOnlyList<TrackQualityUpgradeDef>?`；`TrackQualityUpgradeDef(TrackQuality To, UpgradeCondition Condition, IReadOnlyList<string>? EnemyIds)`，`UpgradeCondition { CloseRange = 0, LinkedDroneTypes = 1 }` | `null` = 无 |
| `fastUpdate` | `FastUpdate` | `bool?` | false |
| `onlyDetects` | `OnlyDetects` | `OnlyDetectsKind? { RadioLinkedDrones = 0 }` | `null` = 不限 |
| `falseAlarms` | `FalseAlarms` | `FalseAlarmLevel? { Some = 0, High = 1 }` | `null` = 无误报 |
| `reportDelay` | `ReportDelay` | `bool?` | false |
| `nightRangeMult` | `NightRangeMult` | `double?` | `null` = 不受夜间影响，也不受天气影响（视为非光学） |
| `nightPenaltyNegatedBy[]` | `NightPenaltyNegatedBy` | `IReadOnlyList<NightAid>?`，`NightAid { Searchlight = 0, Thermal = 1 }` | `null` = 不可抵消 |
| `emission` | `Emission` | `EmissionKind { Active = 0, Passive = 1, None = 2 }` | 必填 |
| `exposureLevel` | `ExposureLevel` | `SensorExposureLevel { High = 0, Medium = 1, Zero = 2, None = 3 }` | 必填 |
| `deployGameSec` / `packGameSec` | `DeploySec` / `PackSec` | `double?`，秒 | 由 04 使用 |
| `priceMusd` / `stockOnly` | `PriceMusd` / `StockOnly` | | 本文件不用 |
| `automatic` | `Automatic` | `bool?` | false |
| `firstAvailable` | `FirstAvailable` | `FirstAvailableDef?`（`int? Level, int? FullStrengthLevel, bool? Optional, bool? InfoSourceOnly`） | `null` |
| ★ `lineOfSight` | `LineOfSight` | `bool?` | `null` = true（需要地形视线）；`acoustic_post` 填 `false`（B-T2-50） |
| ★ `antennaHeightM` | `AntennaHeightM` | `double?`，米 AGL | `null` = `Rules.Terrain.DefaultAntennaHeightM`（`10` m，B-T2-03 / A-2-26；`tethered_balloon` 填 `300`） |

### 1.2 `units/ew.json` → `EwUnitDef`

| JSON 字段 | C# 字段 | 类型 / 单位 | 缺省 |
|---|---|---|---|
| `id` / `nameKey` | `Id` / `NameKey` | `string` | 必填 |
| `radiusKm` | `RadiusM` | `double`，米 | 必填 |
| `effect` | `Effect` | `EwEffect { NavJam = 0, NavSpoof = 1, LinkCut = 2, LinkCutDirectional = 3, SelfProtection = 4 }` | 必填 |
| `offsetCellsAdd`（将改名 `offsetAddCells`） | `OffsetAddM` | `double?`，米（00 0.4.2 #7 临时特例，A-3-04） | **仅界面显示**，模拟不读（单位电子战统一按 `Accuracy.Tiers[tier].EwExtraM`，已决 B-T3-08） |
| `accuracyTierDrop` | `AccuracyTierDrop` | `int?` | 单位电子战不降精度档（模拟忽略此字段，国家级欺骗用 `SupportDef.AccuracyTierDrop`，已决 B-T3-08） |
| `pullChance` | `PullChance` | `double?`，概率 | `null` = 不能诱导 |
| `aiVisionEffectMult` | `AiVisionEffectMult` | `double?` | `null` = 1.0 |
| `linkCutOutcomes[]` | `LinkCutOutcomes` | `IReadOnlyList<LinkCutOutcome>?`，`LinkCutOutcome { Crash = 0, Hover = 1, Return = 2 }` | `LinkCut*` 效果必填（加载器校验，缺失 → `E_MISSING_FIELD`） |
| `hitProbMult` | `HitProbMult` | `double?` | `SelfProtection` 必填（同上） |
| `protectsSelfOnly` / `equipmentSlot` | `ProtectsSelfOnly` / `EquipmentSlot` | `bool?` | false |
| `effectiveAgainst[]` | `EffectiveAgainst` | `IReadOnlyList<string>`，敌方 ID（交叉引用校验，类别"敌方单位"） | 必填 |
| `ineffectiveAgainst[]` | `IneffectiveAgainst` | `IReadOnlyList<string>?` | 仅界面提示，模拟不读 |
| `emissionExposure` | `EmissionExposure` | `EwExposureLevel { High = 0, Medium = 1, Low = 2 }` | 必填 |
| `deployGameSec` / `packGameSec` / `priceMusd` | `DeploySec` / `PackSec` / `PriceMusd` | | 04 / 05 使用 |
| `firstAvailable` | `FirstAvailable` | `FirstAvailableDef?` | `FullStrengthLevel` 用于 3.4.3 |

"有效对象"判定：**只看 `EffectiveAgainst` 是否包含 `Threat.DefId`**；此外 `MunitionDef.EwImmune == true` 的目标对**所有**电子战效果免疫（即使误列在 `EffectiveAgainst` 中）。

### 1.3 `units/deception.json` → `DeceptionUnitDef`

| JSON 字段 | C# 字段 | 类型 | 缺省 |
|---|---|---|---|
| `id` / `nameKey` | `Id` / `NameKey` | `string` | 必填 |
| `effect` | `Effect` | `DeceptionEffect { FakeEmitter = 0, SacrificialEmitter = 1, FakeLauncher = 2 }` | 必填 |
| `attracts[]` | `Attracts` | `IReadOnlyList<DeceptionAttract>?`，`{ AntiRadiation = 0, Recon = 1, Iskander = 2, Lancet = 3 }` | 本文件不读（供 04 选目标） |
| `seeThroughByReconQuality` | `SeeThroughByReconQuality` | `bool?` | false |
| `duration` / `durationNights` | `Duration` / `DurationNights` | `DeceptionDuration { OneShot = 0, UntilDestroyed = 1, Nights = 2 }` / `int?` | 05 使用 |
| `priceMusd` / `stockOnly` / `firstAvailable` | | | 本文件不用 |

### 1.4 `units/air_defense.json` → `AirDefenseUnitDef` 与 `units/weapons.json` → `WeaponDef`（本文件只用下列字段，全字段见 03）

| 来源 → JSON 字段 | C# 字段 | 类型 / 单位 | 缺省 |
|---|---|---|---|
| `air_defense.json` → `weapons[]` | `WeaponIds` → `WeaponDef`（`Kind`、`RangeM`、`RangeByTagM`、`CeilingM`、`Targets`、`ReactionSec`） | | 03 定义；有效射程通过 `Nightwatch.Sim.Rules.WeaponParams.RangeFor(w, tag)` 读取（A-3-09） |
| `air_defense.json` → `fireOnMove` | `FireOnMove` | `FireOnMove { Yes = 0, Partial = 1, No = 2 }` | 必填 |
| ★ `air_defense.json` → `fireControlRadar` | `FireControlRadar` | `FireControlRadarDef?`：`RangeM`（`rangeKm`）、`LowAltitude`（`LowAltitudeCapability`）、`Origin`（`SystemOrigin { Soviet = 0, Western = 1 }`）、`AntennaHeightM`（`double?`，`null` = `Rules.Terrain.DefaultAntennaHeightM`） | `null` = 无火控雷达（不是辐射源；B-T2-34） |
| ★ `air_defense.json` → `selfAcquisitionRangeKm` | `SelfAcquisitionRangeM` | `double?`，米 | `null` = 无自主捕获（见 3.2.5、B-T2-09） |
| ★ `air_defense.json` → `selfAcquisition` | `SelfAcquisition` | `SelfAcquisitionKind? { Optical = 0 }` | `null` = 非光学自主捕获；`Optical` 受夜间 `0.3` 倍率与光学天气倍率影响（`mobile_fire_team`、`zu23_2`、`stinger`、`igla`、`piorun`、`starstreak`、`martlet`、`rbs70`、`mistral`、`interceptor_drone_team` 填 `"optical"`；`gepard`、`avenger`、`strela_10`、`osa` 填 `null`；B-T2-09、C-T2-07） |
| ★ `weapons.json` → `reactionGameSec` | `WeaponDef.ReactionSec` | `double?`，秒 | `null` = 按 `Rules.Engagement.ByWeaponKind[w.Kind].ReactionSec` 取类别默认（`Gun 0`、`InterceptorDrone 0`、`ShortRangeSam 0.05` 游戏秒 = 3 s、`MediumRangeSam 0.1` = 6 s、`LongRangeSam 0.2` = 12 s）；统一通过 `WeaponParams.ReactionSec(w, Rules.Engagement)` 读取（已决 B-T2-01、P15、A-2-30） |

### 1.5 `enemies/*.json`（只列本文件读取的字段）

| 文件 → 字段 | C# 字段 | 用途 | 缺省 |
|---|---|---|---|
| munitions / platforms → `id`、`tag` | `Id`、`Tag` | `Threat.DefId`、`Threat.Tag`（00 已登记） | |
| munitions → `ewImmune` | `MunitionDef.EwImmune` | 3.4 | `null` = false |
| munitions → `tracksEmittingRadarOnly` | `MunitionDef.TracksEmittingRadarOnly` | 识别反辐射导弹（3.5.5） | `null` = false |
| munitions → `accuracy`（已按时期解析） | `MunitionDef.Accuracy` | 3.4.4 取 `ewExtraCells` | |
| platforms → `behavior` | `PlatformDef.Behavior`（`PlatformBehavior`，snake → Pascal，顺序同 Schema） | 侦察平台判定：`Spotter`、`ArmedRecon`（B-T2-41） | |
| ★ munitions / platforms → `radioLinked` | `RadioLinked` | `bool?` | `null` = false（无线电侦测器只探测 `true` 的目标；B-T2-43） |
| ★ munitions → `aiVisionFrom` | 解析为 `bool AiVisionActive`（00 的 1.4 形态 C 闸门） | 3.4.5 | 缺省 = `false`（B-T3-08） |
| ★ platforms → `reconQuality` | `ReconQuality? { Low = 0, Medium = 1, High = 2 }` | 3.7.3 假发射车识破 | `null` = 该平台不会识破（B-T2-41） |

"无标签目标"（`Tag == null`，如无制导炸弹）同样可以被探测和形成航迹；是否交战由 03 决定。

### 1.6 `rules/tracks.json` → `TrackRulesDef`

| JSON 字段 | C# 字段 | 说明 |
|---|---|---|
| `qualities[]` | `Qualities`：`IReadOnlyList<TrackQualityRuleDef>`，**按 `TrackQuality` 值排序**（下标 0/1/2 = Vague/Approximate/Precise）；三个 `id` 必须各出现一次，否则 `E_RANGE` | `TrackQualityRuleDef(TrackQuality Id, double DecoyDiscrimination, bool MissilesAllowed, TrackDisplay Display, IReadOnlyList<TrackAction> Actions)`；`Display`、`Actions` 只供 03 / 06 |
| `approximateFromLocalSensorCount` | `ApproximateFromLocalSensorCount`（`int`） | 3.3.3 |
| `cueing.cued` | `Cueing.Cued`：`MinTrackQuality`（`TrackQuality`）、`FireControlOnlyLastReactionTime`（`bool`）、`ExposureMult`（仅平衡目标与界面显示，模拟不乘，D5 / B-T3-10） | 3.5.4 |
| `cueing.uncued` | `Cueing.Uncued`：`ExposureMult`（不乘）、`FirstShotReactionTimeMult`（**仅界面显示**；`DataLoader` 校验其值与 `intercept.modifiers.noCueSelfSearch.firstShotReactionTimeMult` 相等，不等报 `E_RANGE`，03 运行时只读后者；A-2-08） | |
| `warningRadarEnemyAiWeightAs` | `WarningRadarEnemyAiWeightAs`（`string`） | 04 使用 |
| `bLine` | `BLine`：`RegionalRadarDirectControl`（`bool`）、`RelayDelaySec`（`relayDelayGameSec` × 60）、`MaxTrackQuality` | 3.2.7 |
| ★ `detectionRules` | `DetectionRules`：`DetectionRulesDef`，字段见下表（命名为 `DetectionRules` 以免与 `Detection` 结构体撞名；A-3-06、P17） | 3.2 |

★ `detectionRules` 对象（全部必填，除另有注明外；已决 B-T2-32、B-T2-45～B-T2-50、B-T2-05、B-T2-09、C-T2-07）：

| JSON 字段 | C# 字段 | 单位 / 类型 | 默认值 |
|---|---|---|---|
| `lowAltitudeBelowM` | `LowAltitudeBelowM` | 米 AGL；`AltM <` 此值即"低空" | 1000 |
| `lowAltitudeRangeMult` | `LowAltitudeRangeMult` | 按 `LowAltitudeCapability` 的对象（键 `poor` `medium` `good` `very_good`，四个必填） | 0.3 / 0.6 / 0.9 / 1.0 |
| `largeBlindZoneLowAltitudeRangeMult` | `LargeBlindZoneLowAltitudeRangeMult` | 倍率 | 0.5 |
| `coverageLowAltitudeMinCapability` | `CoverageLowAltitudeMinCapability` | `LowAltitudeCapability` | `good` |
| `closeRangeFraction` | `CloseRangeFraction` | 0–1 | 0.5 |
| `errorRadiusM` | `ErrorRadiusM` | 按 `TrackQuality` 的对象（键 `vague` `approximate` `precise`） | 5000 / 1000 / 0 |
| `fastUpdateErrorRadiusMult` | `FastUpdateErrorRadiusMult` | 倍率 | 0.5 |
| `trackLostGameSec` | `TrackLostSec` | 秒 | 1（= 60 s） |
| `falseAlarmsPerGameSec` | `FalseAlarmsPerSec` | 按 `FalseAlarmLevel` 的对象（键 `some` `high`），每秒 | 0.02 / 0.1（每游戏秒） |
| `reportDelayGameSec` | `ReportDelaySec` | 秒 | 0.5（= 30 s） |
| `opticalWeatherRangeMult` | `OpticalWeatherRangeMult` | 按 `Weather` 的对象（键 `clear` `moonlit` `low_cloud` `fog`） | 1.0 / 1.3 / 0.6 / 0.3 |
| `opticalNightRangeMult` | `OpticalNightRangeMult` | 倍率（`SelfAcquisition == Optical` 的火力单元在夜间的自主捕获距离倍率；缺省 `0.3`） | 0.3（B-T2-09） |
| `unpoweredActiveRangeMult` | `UnpoweredActiveRangeMult` | 倍率（主动辐射源断电时的探测距离倍率） | 0.5（B-T2-05） |
| `winterActiveRangeMult` | `WinterActiveRangeMult` | 倍率（冬季 `Season.Winter` 下主动雷达探测 / 火控距离倍率；缺省 `0.9`） | 0.9（C-T2-07） |

> 默认天线高度统一放在 `rules/terrain.json` 的 `defaultAntennaHeightM`（`10` m），不在 `detectionRules` 中重复定义（已决 B-T2-03、P17、A-2-26）。

### 1.7 `rules/emission.json` → `EmissionRulesDef`

| JSON 字段 | C# 字段 | 说明 |
|---|---|---|
| `strategies[]` | `Strategies`：`IReadOnlyList<EmissionStrategyDef>`（数据顺序） | `EmissionStrategyDef(string Id, string NameKey, EmissionActivation Activation, double ExposureMult, double ReactionTimeMult, bool? TrackInterrupted, bool? ConfigurableOnOff, bool? CanRelocate, IReadOnlyList<StrategyRequirement>? Requires, int? AvailableFromLevel, bool? WesternSystemsOnly)`；`EmissionActivation { Always = 0, ApproximateWarning = 1, DutyCycle = 2, LastMoment = 3, AfterDecoy = 4 }`；`StrategyRequirement { ApproximateTrack = 0, Network = 1, Decoy = 2 }`。`ExposureMult` 为平衡验证的目标平均暴露系数（运行时不乘，B-T3-10）。`configurableOnOffGameSec`（将改名 `configurableOnOff`）是**布尔**字段，加载器特例不做时间换算（00 0.4.2 #7、A-3-04） |
| `triggers.onAntiRadiationIncoming[]` | `Triggers.OnAntiRadiationIncoming`：`IReadOnlyList<ArmResponse>`，`ArmResponse { ShutdownImmediately = 0, ShutdownAfterCurrentIntercept = 1, KeepEngaging = 2 }` | Schema 允许任意字符串；加载器按此 enum 解析，未知值 → `E_ENUM`。**第 0 项为默认值** |
| `triggers.afterFiring[]` | `Triggers.AfterFiring`：`IReadOnlyList<AfterFiringAction>`，`{ Stay = 0, RelocateToAlternate = 1 }` | 第 0 项为默认值 |
| `triggers.onMainRadarDestroyed[]` | `Triggers.OnMainRadarDestroyed`：`IReadOnlyList<RadarDestroyedResponse>`，`{ NeighborRadarTakesOver = 0 }` | 列出可选项；是否启用由单位设置 `NeighborTakeover` 决定（缺省 false） |
| `shutdownTiming[]` | `ShutdownTiming`：`IReadOnlyList<ShutdownTimingTierDef(double ArmDistanceFractionAbove, double ArmHitProbMult)>`（**数据顺序**，按顺序取第一个满足条件者） | 3.5.5 |
| ★ `defaultStrategy` | `DefaultStrategyId`（`string`，须 ∈ `strategies[].id`，否则 `E_UNKNOWN_REF`） | 单位未设置策略时使用；默认 `always_on`（B-T2-38） |
| ★ `dutyCycleDefaultOnGameSec` / `dutyCycleDefaultOffGameSec` | `DutyCycleDefaultOnSec` / `DutyCycleDefaultOffSec` | 间歇开机未设置周期时使用；默认 1 / 1（B-T2-39） |
| ★ `decoyLeadGameSec` | `DecoyLeadSec` | 诱饵配合：诱饵须先开机的时长；默认 0.25（B-T2-39） |
| ★ `defaultReferenceRangeKm` | `DefaultReferenceRangeM` | 没有自身距离的辐射源（诱饵）用于"按预警开机"的参考距离；默认 30（B-T2-39） |

### 1.8 `rules/exposure.json` → `ExposureRulesDef`

| JSON 字段 | C# 字段 | 说明 |
|---|---|---|
| `min` / `max` | `Min` / `Max` | 夹取范围 |
| `ratesPerGameSec.*` | `RatesPerSec`：`FireControlSelfSearch`、`FireControlCued`、`Silent`、`EnemyReconNearby`（全部 ÷ 60，每秒） | `WarningRadarSoviet`、`WarningRadarWestern`、`HighPowerEw` 与下面两张"等级速率表"重复，已决删除（B-T1-10），模拟只读等级速率表 |
| `perMissileLaunched` | `PerMissileLaunched` | 一次性增量，不换算 |
| `enemyReconRadiusKm` | `EnemyReconRadiusM` | 米 |
| `onRelocate` | `OnRelocate`：`ResetTo`、`ToScoutedPositionMult` | 3.6.3 |
| `sensorExposureLevelRates`（将改名 `sensorExposureLevelRatesPerGameSec`） | `SensorExposureLevelRatesPerSec`（按 `SensorExposureLevel`） | 00 0.4.2 #7 临时特例：改名前加载时亦 ÷ 60（B-T1-09、A-3-04） |
| `ewExposureLevelRates`（将改名 `ewExposureLevelRatesPerGameSec`） | `EwExposureLevelRatesPerSec`（按 `EwExposureLevel`） | 同上 |
| `thresholds[]` | `Thresholds`：`IReadOnlyList<ExposureThresholdDef(double AtLeast, ExposureConsequence Consequence)>`，加载后**按 `AtLeast` 升序稳定排序**；`ExposureConsequence { AntiRadiationPriorityTonight = 0, KnownTargetListNextNight = 1, PrecisionStrikeTonight = 2 }` | 3.6.4 |

### 1.9 `rules/ew.json` → `EwRulesDef`

| JSON 字段 | C# 字段 | 说明 |
|---|---|---|
| `effectivenessByPeriod`（已按关卡日期解析为单行） | `Effectiveness`：`EwEffectivenessDef(double Nav, double CounterUas, bool NavTerminalIneffectiveVsAiVision)`（JSON 缺省 → false） | 3.4.3 |
| `sideEffects` | `SideEffects`：`FriendlyInterceptorDroneMult`（仅界面显示或删除，03 只读 `intercept.json`，B-T1-08）、`OwnDroneLinkCut`（本版不实现，B-T1-08）、`UrbanNavJamCityResiliencePerNight` | 3.4.7、3.4.8 |
| ★ `linkCutOutcomeWeights` | `LinkCutOutcomeWeights`（按 `LinkCutOutcome`，键 `crash` `hover` `return`，非负，三者之和 > 0） | 默认 0.5 / 0.25 / 0.25（B-T2-35） |
| ★ `hoverBeforeCrashGameSec` | `HoverBeforeCrashSec` | 悬停后坠落的时长；默认 2（B-T2-35） |
| ★ `belowFullStrengthMult` | `BelowFullStrengthMult` | 关卡序号 < `fullStrengthLevel` 时的效能倍率；默认 0.5（B-T2-35） |
| ★ `unpoweredEffectMult` | `UnpoweredEffectMult` | 电子战单位断电（`!Powered`）时的效能概率倍率；缺省 `0.5`（B-T2-05、A-2-12） |
| ★ `winterEffectMult` | `WinterEffectMult` | 冬季（`Season.Winter`）下电子战单位效能概率倍率；缺省 `0.9`（C-T2-07） |
| ★ `urbanNavJamMinGameSec` | `UrbanNavJamMinSec` | 当夜城区内导航干扰累计开启达到此值才算"长时间"；默认 60（B-T2-36） |

### 1.10 其他规则与关卡数据

| 来源 | C# | 用途 |
|---|---|---|
| `rules/terrain.json` → `defaultAntennaHeightM`、`earthRadiusM`、`refractionK` | `TerrainRulesDef.DefaultAntennaHeightM`（`10` m）、`EarthRadiusM`（`6371000`）、`RefractionK`（`4.0 / 3.0`） | 3.2.4、3.2.5 默认天线高度与地平线视线模型（B-T2-02、B-T2-03） |
| `rules/accuracy.json` → `tiers.<档>.ewExtraCells` | `AccuracyRulesDef.Tiers[tier].EwExtraM`（米） | 3.4.4 单位电子战的额外落点偏移 |
| `rules/intercept.json` → `decoyUsesColumn` | `InterceptRulesDef.DecoyUsesColumn`（`TargetTag`） | 3.3.6 未识别的诱饵对外显示的标签 |
| `rules/positions.json` → `newUnsurveyed.firstNightEfficiencyMult` | `PositionRulesDef.NewUnsurveyed.FirstNightEfficiencyMult` | 3.7.4 |
| ★ `rules/positions.json` → `deception.fakeLauncherSeeThroughChance` | `PositionRulesDef.Deception.FakeLauncherSeeThroughChance`（按 `ReconQuality`，键 `low` `medium` `high`） | 3.7.3；默认 0.1 / 0.3 / 0.6（B-T2-41） |
| ★ `rules/positions.json` → `deception.decoyEmitterExposureLevel` | `PositionRulesDef.Deception.DecoyEmitterExposureLevel`（`SensorExposureLevel`） | 3.6.2；默认 `high`（B-T2-42） |
| `support/support.json` → `national_gnss_spoof`：`accuracyTierDrop`、`affectsSameAsEwUnit` | `SupportDef.AccuracyTierDrop`、`SupportDef.AffectsSameAsEwUnitId` | 3.4.6 |
| ★ `support/support.json` → `national_gnss_spoof.radiusKm` | `SupportDef.RadiusM` | "某区域"的半径；默认 30 km（B-T2-04；由 03 写入 `SupportAsset.RadiusM`，A-2-21） |
| `level.json` → `protagonist`、`number`、`dateRange.from` | `Meta.Protagonist`、`Meta.Number`、`Meta.DateRange.From` | B 线（3.2.7）、关卡闸门、季节解析 |
| `waves.json` → `entryPoints[].warningGameSec` | `EntryPointDef.WarningSec` | 3.2.8 国家预警 |
| `waves.json` → `nights[].weather` / ★ `timeOfDay` / ★ `season` | `NightDef.Weather`（`null` = 倍率 1.0）、`NightDef.TimeOfDay`（`TimeOfDay { Night = 0, Day = 1 }`，缺省 `Night`）、`NightDef.Season`（经 `EnvironmentResolver.SeasonFor(night, Meta.DateRange.From)` 解析为 `Season`） | 3.2.3、3.2.5、3.4.3（B-T2-45、C-T2-07） |
| `layers.json` → `urban[].polygonM` | `UrbanAreaDef.Polygon` | 民众上报覆盖（3.2.6）、城区导航干扰（3.4.8） |
| `deploy.json` → `alternatePositions[]` | `AlternatePositionDef(Id, Pos, Surveyed)` | 3.7.4 |

### 1.11 单位设置（`SimConfig` → `PlacedUnit.Settings`，00 的 2.6）

`UnitSettings` 中由本文件定义的字段（全部可空；在 `SimConfig` JSON 中出现，**单位为世界秒 / 米**）：

| 字段 | 类型 | 适用 | 缺省（为 null 时） |
|---|---|---|---|
| `EmissionPolicyId` | `string?` | 辐射源 | `Rules.Emission.DefaultStrategyId` |
| `DutyOnSec` / `DutyOffSec` | `double?` | 间歇开机 | `DutyCycleDefaultOnSec` / `OffSec` |
| `OnArmIncoming` | `ArmResponse?` | 辐射源 | `Triggers.OnAntiRadiationIncoming[0]` |
| `AfterFiring` | `AfterFiringAction?` | 火力单元 | `Triggers.AfterFiring[0]` |
| `NeighborTakeover` | `bool?` | 辐射源 | false |
| `LurePoint` | `Vec2?` | `NavSpoof` 电子战单位 | 无诱导点（只偏移、不诱导） |
| `NightAids` | `IReadOnlyList<NightAid>?` | 探测单位、带光学自主捕获的火力单元 | 无 |
| `EquipmentEwIds` | `IReadOnlyList<string>?` | 车辆类我方单位；元素为 `EquipmentSlot == true` 的 `EwUnitDef.Id` | 无 |

合法性（策略可用性、装备能否安装、夜视器材是否可用）由 04 的 `DeploymentValidator` 校验；本文件在 3.5.2 规定策略约束的判定函数 `EmissionPolicyRules.CheckAvailable`，供 04 与命令处理共用。

---

## 2. 状态

> "写 / 读"列中的数字是 Step 序号（3 = `SensorSystem` …），"0" = 阶段 0（命令），"I" = `Initialize`。所有字段**按表中行顺序**写入状态哈希，标"不哈希"的除外。

### 2.1 我方单位公共字段（`PlayerUnitCommon`，适用 `FireUnit` `SensorUnit` `EwUnit` `DeceptionUnit`）

完整 14 个参与哈希的公共字段与 2 个不哈希字段已合入 [00_core.md §2.4](00_core.md)（P22）；下表列出本文件拥有或直接读写的字段及其在 `PlayerUnitCommon` 中的哈希序号：

| 哈希序号 | 字段 | C# 类型 | 单位 | 初值 | 写 | 读 | 拥有者 |
|---|---|---|---|---|---|---|---|
| 1–3 | `DeployState` / `DeployTimerSec` / `DeployTargetPos` | — | — | 见 00 2.4 | 0、1 | 3、5、6、11、03、04 | 00 / 04 |
| 4 | `Exposure` | `double` | 0–100 | `CarryIn.Units` 或 `0.0` | Create 第 8 步、11 | 11、03、04 | 00 / 02 |
| 5 | `ExposurePeak` | `double` | 0–100 | = 初始 `Exposure` | I、11 | 03（`NightResult.Exposure` 结算，A-3-10）、04 | 02 |
| 6–7 | `GridNodeId` / `Powered` | `int` / `bool` | — | `0` / `true` | 10 | 3、5（断电倍率，B-T2-05）、03 | 00 / 03 |
| 8 | `Emitter` | `EmitterControl?` | — | 辐射源 = 新实例（2.2）；否则 `null` | I（3 号系统）、0、6 | 3、5、6、7、11、04 | 02 |
| 9 | `NewPositionPenalty` | `bool` | — | `Placement?.FirstNightAtNewPosition ?? false` | I、11 | 3、5、7（03 统一读此字段，A-2-13 / B-T2-06） | 02 |
| 10 | `PendingRelocationAltId` | `string?` | — | `null` | 6（写入）、0（04 执行后清空） | 04 | 02 |
| 11 | `EquipmentEwIds` | `List<string>` | — | `Placement?.Settings.EquipmentEwIds` 副本（数据顺序），无则空 | I | 11、10（经 `EwQueries`） | 02 |
| 12 | `DamageEfficiencyMult` | `double` | — | `CarryIn` 或 `1.0` | 10 | 7、02 | 03 |
| 13 | `SuspendedUntilSec` | `double` | 秒 | `0.0` | 10 | 3、5、6、7（`Suspended(u)` 判定，A-2-12） | 03 |
| 14 | `LightDamaged` | `bool` | — | `CarryIn` 或 `false` | 10 | 05 | 03 |
| — | `Placement` | `PlacedUnit?` | — | 部署条目；运行时创建 / 自动单位为 `null` | Create 第 7 步 | 全部（**不哈希**） | 02 |
| — | `RosterId` | `int` | — | `Placement?.RosterId ?? 0` | Create 第 7 步 | 05、03、02（**不哈希**） | 05 |

暂停辅助谓词（全文件通用，A-2-12）：
`Suspended(u) = u.SuspendedUntilSec > ctx.TimeSec + 1e-9`。

辐射源（拥有 `Emitter`）判定，**创建时确定、之后不变**：

| 实体 | 是辐射源的条件 |
|---|---|
| `SensorUnit` | `Def.Emission == Active` |
| `FireUnit` | `Def.FireControlRadar != null` |
| `EwUnit` | 全部（`EquipmentSlot == true` 的定义不会成为 `EwUnit` 实体，见 3.4.7） |
| `DeceptionUnit` | `Def.Effect ∈ { FakeEmitter, SacrificialEmitter }` |

### 2.2 `EmitterControl`（组件类，非实体；字段按行序哈希，前置 `Write(bool 非 null)`）

| 字段 | C# 类型 | 单位 | 初值（I） | 写 | 读 |
|---|---|---|---|---|---|
| `On` | `bool` | — | 3.5.7 的初始评估 | 6 | 3、5、11、03、04 |
| `PolicyId` | `string` | — | 设置值或 `DefaultStrategyId` | I、0 | 6 |
| `DutyOnSec` / `DutyOffSec` | `double` | 秒 | 设置值或默认 | I、0 | 6 |
| `DutyPhaseStartTick` | `int` | 步 | 0 | 0（策略改为间歇时 = 当前 Tick） | 6 |
| `OnArmIncoming` | `ArmResponse` | — | 设置值或默认 | I、0 | 6 |
| `AfterFiring` | `AfterFiringAction` | — | 设置值或默认（非火力单元也存，但不生效） | I、0 | 6 |
| `NeighborTakeover` | `bool` | — | 设置值或 false | I、0 | 6 |
| `Forced` | `SectorForce { None = 0, Silence = 1, ForceOn = 2 }` | — | `None` | 0 | 6 |
| `ArmSilenced` | `bool` | — | false | 0（经 `ApplyArmChoice`，A-2-11）、6 | 6 |
| `ArmPending` | `bool` | — | false（"完成当前拦截后关机"的等待标记） | 0（经 `ApplyArmChoice`，A-2-11）、6 | 6 |
| `TakeoverActive` | `bool` | — | false | 6 | 6 |
| `OnSinceTick` | `int` | 步 | 初始为开 → 0；否则 −1（曾开机后关机置为 −2） | 6 | 6（诱饵配合）、11（条令 `forward_ambush`） |
| `FcMode` | `FireControlMode { Off = 0, Cued = 1, SelfSearch = 2 }` | — | `Off`（仅火力单元有意义；其他实体恒为 `Off`） | 6 | 11（暴露速率；03 改读 `FireControlQueries.Cued(track)`，A-2-08） |
| `FiredSinceRelocation` | `bool` | — | false | 6 | 6 |
| `LastShotTick` | `int` | 步 | −1 | 6 | 6 |

### 2.3 `SensorUnit` 专有字段

| 字段 | C# 类型 | 初值 | 写 | 读 |
|---|---|---|---|---|
| `Automatic` | `bool` | 部署来的 = false；3.2.1 自动创建的 = true | I | 3、11、04 |
| `NightAids` | `List<NightAid>` | `Placement?.Settings.NightAids` 副本（数据顺序），无则空 | I | 3 |

### 2.4 `EwUnit` / `DeceptionUnit` / `FireUnit` 专有字段（本文件部分）

| 实体 | 字段 | C# 类型 | 初值 | 写 | 读 |
|---|---|---|---|---|---|
| `EwUnit` | `LurePoint` | `Vec2?` | `Placement?.Settings.LurePoint` | I | 5 |
| `DeceptionUnit` | `SeenThrough` | `bool` | `CarryIn.Units[RosterId].SeenThrough`（有匹配时）否则 `false`（R-02-2） | I、11 | 04、03（`BuildResult`） |
| `DeceptionUnit` | `ReconCheckedThreatIds` | `List<int>`（升序、无重复） | 空 | 11 | 11 |
| `DeceptionUnit` | `AttractedThreatIds` | `List<int>`（升序、无重复） | 空 | 6 | 6 |
| `FireUnit` | （本文件无专有字段；火控状态在 `Emitter` 中，03 定义 `RadarDestroyed` 等专有字段） | | | | |

### 2.5 `Track`（实体，`EntityKind.Track`；本文件拥有全部字段）

公共字段：`DefId = ""`（航迹没有数据定义，恒为空串）；`Pos`、`AltM` = 航迹估计位置 / 高度（AGL）。

| 字段 | C# 类型 | 单位 | 初值 | 写 | 读 |
|---|---|---|---|---|---|
| `ThreatId` | `int` | 实体 ID | 关联的目标；误报航迹 = 0 | 4 | 03、6（**界面不得显示**） |
| `Quality` | `TrackQuality` | — | 创建时的融合质量 | 4 | 03、04、6、06 |
| `PhantomKey` | `int` | — | 真实航迹 = 0；误报航迹 = 其误报编号（≥ 1） | 4 | 4 |
| `NetworkQuality` | `TrackQuality?` | — | 本步来自**探测单位**（`SensorUnit`）的融合质量；本步无此类探测 = `null` | 4 | 6、03（经 `FireControlQueries.Cued`） |
| `Tag` | `TargetTag?` | — | 3.3.6（全目录统一名 `Track.Tag`，A-2-01 / B-T1-23） | 4 | 03、06 |
| `VelMps` | `Vec2` | m/s | 来自选中探测 | 4 | 6、03 |
| `ErrorRadiusM` | `double` | m | 3.3.5 | 4 | 03、06 |
| `LastDetectedTick` | `int` | 步 | 创建步 | 4 | 4 |
| `LastObservedAtSec` | `double` | 秒 | 选中探测的观测时刻 | 4 | 06（显示"数据陈旧"） |
| `LocalSensorCount` | `int` | — | 本步贡献探测的不同本地层探测单位数 | 4 | 06 |
| `PreciseHolderIds` | `List<int>` | 实体 ID，升序无重复 | 本步以精确质量探测到此目标的火力单元 | 4 | 03、6 |
| `DecoyCheckedQuality` | `TrackQuality?` | — | `null` | 4 | 4 |
| `DecoyIdentified` | `bool` | — | false | 4 | 03、06 |
| `ArmWarned` | `bool` | — | false | 6 | 6 |

### 2.6 `Threat` 追加字段（01 拥有实体；以下 11 项字段由本文件拥有并写入，对应 00 2.4 `Threat` 第 33–43 项）

| 字段 | C# 类型 | 单位 | 初值 | 写 | 读 |
|---|---|---|---|---|---|
| `EwNav` | `EwRollState { None = 0, Applied = 1, Resisted = 2 }` | — | `None` | 5 | 03 |
| `EwExtraOffsetM` | `double` | m | 0 | 5 | 03（落点额外偏移唯一来源，A-2-07） |
| `AccuracyTierDrop` | `int` | 档 | 0 | 5 | 03（国家级欺骗精度降档，A-2-07 / B-T3-08） |
| `EwPull` | `EwRollState` | — | `None` | 5 | 5 |
| `EwDivertPos` | `Vec2?` | m | `null` | 5 | 03 / 复盘记录（移动由 5 调用 `ThreatRouting.Retarget` 完成，A-2-27） |
| `NationalSpoof` | `EwRollState` | — | `None` | 5 | 5 |
| `LinkCutState` | `LinkCutState { None = 0, Resisted = 1, Hover = 2, Return = 3 }`（坠落直接移除，无状态） | — | `None` | 5 | 5（移动由 5 调用 `ThreatRouting.Hover / BeginEgress` 完成，A-2-27） |
| `LinkCutAtTick` | `int` | 步 | −1 | 5 | 5 |
| `ArmInitialDistM` | `double` | m | 0（= 未设置） | 6 | 6 |
| `ArmHitProbMult` | `double?` | — | `null`（= 不修正，03 按 `ArmHitProbMult ?? 1.0` 读取） | 6 | 03（反辐射导弹对单位伤害修正，A-2-07） |
| `EwEverCovered` | `bool` | — | `false` | 5 | 03（突防原因 `EwCovered` 与 `ScoringState.ThreatsEverEwCovered`）、05（`PlayStats.ThreatsEverEwCovered`；A-2-07、R-02-1） |

由 01 拥有、与本文件交互的 `Threat` 字段：
- `TargetUnitId`（`int`，01 2.2 #13）：**由 01 唯一写入**（生成时取钩子返回值，`ApplyHoming` 时改写；A-2-04），本文件在第 3、6、11 步只读。
- `HomingUnitId`（`int`，01 2.2 #14）：**由本文件第 6 步写入**（3.5.5 第 0 步：若 `TargetUnitId` 指向的存活辐射源当前 `Emitter.On == true` 则写其 `Id`，否则写 `0`；A-2-06），01 在下一步第 2 步 `ApplyHoming` 读取。

### 2.7 单例组件 `SensingState`（00 的 3.7.2 第 2 项）

| 字段 | C# 类型 | 初值 | 写 | 读 | 哈希 |
|---|---|---|---|---|---|
| `Detections` | `List<Detection>` | 空 | 3（每步开头清空） | 4 | **不哈希**（每步临时缓冲） |
| `Delayed` | `List<DelayedDetection>`（按 `(DeliverTick, Seq)` 升序） | 空 | 3 | 3 | 哈希 |
| `NextDelaySeq` | `long` | 1 | 3 | 3 | 哈希 |
| `NextPhantomKey` | `int` | 1 | 3 | 3 | 哈希 |
| `WarningSchedule` | `List<ScheduledWarning>` | I 计算 | I | 3 | **不哈希**（由数据推出，不变） |
| `WarnedKeys` | `SortedSet<string>`（序数比较；元素 `"<WaveId>|<EntryId>"`） | 空 | 3 | 3 | 哈希（按序写） |
| `EmissionEventCursor` | `long` | 0 | 6 | 6 | 哈希 |
| `ExposureEventCursor` | `long` | 0 | 11 | 11 | 哈希 |
| `HorizonProfiles` | `Dictionary<int, HorizonProfile>` | 空 | I（3.2.1）、11（转移完成时重算，3.6.3） | 3（3.2.4、3.2.5） | **不哈希**（由地形与单位位置派生的只读缓存，C-T2-01 / B-T2-31） |

```csharp
public readonly record struct Detection(
    int SourceId,             // 产生探测的实体 ID（SensorUnit 或 FireUnit）
    DetectionSource Source,   // Sensor = 0, FireControl = 1, SelfAcquisition = 2
    SensorLayer Layer,        // 来源为 FireUnit 时记为 Local（不参与交叉计数，见 3.3.3）
    int ThreatId,             // 误报 = 0
    int PhantomKey,           // 真实 = 0
    Vec2 Pos, double AltM, Vec2 VelMps,
    TrackQuality Quality,
    double ErrorRadiusM,
    double ObservedAtSec);
public readonly record struct DelayedDetection(int DeliverTick, long Seq, Detection D);
public readonly record struct ScheduledWarning(int Tick, string WaveId, string EntryId, double ExpectedAtSec, double BearingRad, bool Ballistic);
```

`DelayedDetection` 的哈希写入顺序：`DeliverTick, Seq`，然后 `Detection` 的字段按声明顺序。

### 2.8 单例组件 `EwState`（00 的 3.7.2 第 3 项）

| 字段 | C# 类型 | 初值 | 写 | 读 |
|---|---|---|---|---|
| `UrbanNavJamSec` | `double` | 0 | 5 | 03 / 05（结算时判断 `UrbanNavJamSec >= Rules.Ew.UrbanNavJamMinSec` → 城市资源 −1，每夜最多触发一次；B-T2-36） |

### 2.9 快照字段（00 的 2.7）

- `TrackView`：`Id, Pos, AltM, Quality, Tag, VelMps, ErrorRadiusM, LastObservedAtSec, DecoyIdentified, IsPrecise`（`IsPrecise = PreciseHolderIds.Count > 0`）。**不含** `ThreatId`、`PhantomKey`（真值仅调试视图可见，经 `ThreatView`）。
- `SensorUnitView` / `FireUnitView` / `EwUnitView` / `DeceptionUnitView` 追加：`EmitterOn`（无辐射源 = false）、`PolicyId`（无 = null）、`FcMode`、`Exposure`、`ExposurePeak`、`NewPositionPenalty`。
- `GlobalView` 追加：无。

---

## 3. 每步算法

### 3.1 公共函数与约定

```csharp
namespace Nightwatch.Sim.Sensing;

static class SensingMath
{
    // 水平距离平方比较（全部"在范围内"判定都用 ≤，且比较平方，不开方）
    public static bool WithinRange(Vec2 a, Vec2 b, double rangeM)
        => (b - a).LengthSquared() <= rangeM * rangeM;

    // 从 p 出发、速度 v 的直线运动，第一次进入以 c 为圆心、半径 r 的圆所需时间（秒）
    // 已在圆内（含边界）→ 0；永不进入 → null。直接委托 00_core 3.8 的公共实现（A-2-23）
    public static double? TimeToEnterRadius(Vec2 p, Vec2 v, Vec2 c, double r)
        => Nightwatch.Sim.Core.Geo.FirstEntryIntoCircle(p, v, c, r);
}
```

- **多边形与城区判定**（A-2-23）：统一调用 `Nightwatch.Sim.Core.Geo.PointInPolygon(p, poly)` 与 `Geo.InUrban(ctx.Level, p)`（唯一实现见 [00_core.md §3.8](00_core.md)，半开交叉数法，边界点由公式确定性决定）。
- **欧氏距离约定**（C-T1-04）：需要开方的距离计算一律写 `Math.Sqrt(dx * dx + dy * dy)`，禁止使用 `Math.Hypot`。
- **空间网格加速**（`SpatialGrid`，C-T1-08）：3.2.4 `RangeDetect`、3.2.5 `FireControlDetect`、3.6.3 `ReconNearby`、3.7.3 `FakeLauncherRecon` 对 `Threats` 的圆形范围查询统一调用 `ctx.ThreatGrid.QueryCircle(center, r)`；3.5.3 `WarnTrack`、3.5.4 `CueAvailable` / `CueWindow` 对 `Tracks` 的圆形范围查询统一调用 `ctx.TrackGrid.QueryCircle(center, r)`。`QueryCircle` 保证返回距离 `≤ r`（比较平方）的全部存活实体且按 `Id` 严格升序排列，与全表扫描逐位等价。
- **空步快速返回**（C-T1-16）：当 `Threats.CountAlive() == 0`、`Tracks.CountAlive() == 0`、`Sensing.Delayed.Count == 0` 且本步无到期 `WarningSchedule` 条目时，3 号系统跳过 `RangeDetect` / `CoverageDetect` / `FireControlDetect`，只执行 `FalseAlarms()`（保持 `sensor` 子流消耗对齐）；4 号系统直接返回；5 号系统跳过 `Threats` 循环，只执行 `UrbanNavJam()`。
- **事件游标读取**（6 号、11 号系统共用）：系统需要消费"可能由更晚系统产生"的事件时，按 `Seq` 升序遍历 `ctx.Events.PreviousStep` 再遍历 `ctx.Events.CurrentStep`，只处理 `Seq > cursor` 的事件，处理完把 cursor 设为已处理的最大 `Seq`。这样每个事件恰好被处理一次，与产生它的系统序号无关。
- **辐射源状态的时序**：3 号（探测）与 5 号（电子战）读取的 `Emitter.On` 是**上一步** 6 号系统（或 `Initialize`）的结果；11 号（暴露度）读取的是**本步** 6 号系统的结果。这是 01.B 固定顺序的直接后果，不做补偿。但 10 号系统写入的 `FireUnit.RadarDestroyed` 与 `SuspendedUntilSec` 在下一步第 3、5 步中由探测 / 电子战直接检查（A-2-12），不再多延迟一步。
- 遍历顺序：实体按 ID 升序；跨实体类型时按 `EntityKind` 值升序（`FireUnit` → `SensorUnit` → `EwUnit` → `DeceptionUnit`）。

### 3.2 `SensorSystem`（Order 3，子流 `sensor`）

#### 3.2.1 `Initialize`

1. **自动探测单位**：对 `Catalog.Sensors` 按数据顺序，`Automatic == true` 且（`Meta.Number == null` 或 `FirstAvailable?.Level == null` 或 `FirstAvailable.Level ≤ Meta.Number`）的每个定义，`Sensors.Add` 一个实体：`DefId = Id`、`Pos = (WidthM / 2, HeightM / 2)`、`AltM = 0`、`DeployState = Deployed`、`Exposure = 0`、`Automatic = true`、`Placement = null`、`Emitter = null`（自动单位都是被动的；若数据中出现 `Automatic && Emission == Active`，加载器报 `E_RANGE`）。（B-T2-44）
2. **所有我方单位的本文件字段**（按 `EntityKind` 再按 ID 升序）：按 2.1–2.4 的初值填写（其中 `DeceptionUnit.SeenThrough` 若 `RosterId != 0` 在 `CarryIn.Units` 中有对应项则取其 `SeenThrough`，R-02-2）；`Emitter` 的 `PolicyId` 若设置值不是已知策略 ID，抛 `SimSetupException`（04 的校验应已拦截）。
3. **预警时间表** `WarningSchedule`：对本夜 `night.Waves` 按数据顺序，**跳过 `WaveSpawnRules.IsStoryOnlyWave(ctx.Level, wave.Id) == true` 的仅剧情注入波次**（01 §3.1.1、A-2-28）；其余每个波次内按 `Groups` 数据顺序收集**首次出现**的 `EntryId`；对每个 `(wave, entryId)`：
   - `entry = Waves.EntryPoints` 中该 ID；`entry.WarningSec == null` → 跳过。
   - `ExpectedAtSec = wave.AtSec`；`Tick = max(1, SecToTicksFloor(max(0, wave.AtSec − entry.WarningSec), StepSec))`。
   - `BearingRad = Geo.BearingRad(mapCenter, entry.Pos)`，`mapCenter = (WidthM / 2, HeightM / 2)`。
   - `Ballistic` = 该波次中 `EntryId == entry.Id` 的任一组，其敌方定义的 `Tag ∈ { BM, HBM }`。
   - 结果列表按 `(Tick, 波次数据下标, 入口首次出现顺序)` 排序（稳定）。
4. **地平线视线包络预计算**（`Sensing.HorizonProfiles`，B-T2-31、C-T2-01、A-2-26）：
   - 对每个 `SensorUnit s`（`s.Def.DetectionRangeM != null && s.Def.LineOfSight != false && s.Def.Layer != SensorLayer.National`）：`h = s.Def.AntennaHeightM ?? Rules.Terrain.DefaultAntennaHeightM`，`maxR = MaxPossibleRangeM(s.Def)`（含晴朗 / 月夜最大天气倍率），写入 `Sensing.HorizonProfiles[s.Id] = ctx.Terrain.BuildHorizonProfile(s.Pos, h, maxR)`。
   - 对每个 `FireUnit f`：若 `f.Def.FireControlRadar != null`，取 `h = f.Def.FireControlRadar.AntennaHeightM ?? Rules.Terrain.DefaultAntennaHeightM`、`maxR = f.Def.FireControlRadar.RangeM`；否则若 `f.Def.SelfAcquisitionRangeM != null`，取 `h = Rules.Terrain.DefaultAntennaHeightM`、`maxR = MaxPossibleSelfAcqRangeM(f.Def)`；写入 `Sensing.HorizonProfiles[f.Id] = ctx.Terrain.BuildHorizonProfile(f.Pos, h, maxR)`。

#### 3.2.2 `Execute` 总流程

```
Sensing.Detections.Clear()
EmitEarlyWarnings()            # 3.2.8
for each SensorUnit s (ID 升序), Alive:
    if not SensorActive(s): continue                       # 3.2.3
    if s.Def.Coverage != null: CoverageDetect(s)           # 3.2.6
    else: RangeDetect(s)                                   # 3.2.4
for each FireUnit f (ID 升序), Alive:
    FireControlDetect(f)                                   # 3.2.5
FalseAlarms()                                              # 3.2.9（按探测单位 ID 升序，唯一消耗 sensor 子流的地方）
DeliverDelayed()                                           # 3.2.7：把 DeliverTick ≤ Tick 的延迟探测移入 Detections
```

每条"新产生"的探测经过 `Route(d, delaySec)`：`delaySec == 0` → 直接加入 `Detections`；否则加入 `Delayed`（`DeliverTick = Tick + SecToTicksCeil(delaySec, StepSec)`，`Seq = NextDelaySeq++`）。同一条探测既有民众上报延迟又有 B 线转发延迟时**取较大者**（不相加；两者不会同时出现在现有数据中）。

#### 3.2.3 探测单位是否工作、有效距离

`SensorActive(s)`：`s.DeployState == Deployed` 且 `!Suspended(s)`（A-2-12）且（`s.Emitter == null` 或 `s.Emitter.On`）。

本夜季节 `season = EnvironmentResolver.SeasonFor(night, ctx.Level.Meta.DateRange.From)`（05 §3.7.6、C-T2-07）。

对某个目标 `t` 的**有效探测距离**（仅 `DetectionRangeM != null` 的单位）：

```
R = s.Def.DetectionRangeM
if s.Def.NightRangeMult != null:                                   # 光学传感器
    nightMult = (night.TimeOfDay == TimeOfDay.Day or (s.NightAids ∩ s.Def.NightPenaltyNegatedBy 非空)) ? 1.0 : s.Def.NightRangeMult
    weatherMult = night.Weather == null ? 1.0 : DetectionRules.OpticalWeatherRangeMult[night.Weather]
    R = R × nightMult × weatherMult
if s.Emitter != null and not s.Powered:         R = R × DetectionRules.UnpoweredActiveRangeMult
if s.Emitter != null and season == Season.Winter: R = R × DetectionRules.WinterActiveRangeMult
if s.NewPositionPenalty:                        R = R × Positions.NewUnsurveyed.FirstNightEfficiencyMult
if t.AltM < DetectionRules.LowAltitudeBelowM:
    R = R × DetectionRules.LowAltitudeRangeMult[s.Def.LowAltitude]
    if s.Def.LargeLowAltitudeBlindZone == true: R = R × DetectionRules.LargeBlindZoneLowAltitudeRangeMult
```

- 乘法按上面书写顺序逐个执行（当某项条件不满足时不执行该次乘法，保证二进制可复现）。
- 昼夜与季节：`night.TimeOfDay` 缺省为 `TimeOfDay.Night`；白天（`TimeOfDay.Day`）光学传感器不乘 `NightRangeMult`，但仍乘 `weatherMult`（C-T2-07、B-T2-45）。

#### 3.2.4 `RangeDetect(s)`（有探测距离的单位）

通过 `ctx.ThreatGrid.QueryCircle(s.Pos, R0)`（`R0` 为 3.2.3 中不含低空项的有效距离，按 `t.Id` 升序，C-T1-08）遍历候选存活 `Threat t`：

1. `s.Def.OnlyDetects == RadioLinkedDrones` 且 `t` 的定义 `RadioLinked != true` → 跳过。
2. `R` = 3.2.3；`!WithinRange(s.Pos, t.Pos, R)` → 跳过。
3. 视线（A-2-26、B-T2-31、C-T2-01）：`s.Def.LineOfSight != false` 且 `s.Def.Layer != National` 时，要求 `Sensing.HorizonProfiles[s.Id].HasLineOfSightAgl(t.Pos, t.AltM)`（天线高度 `h = s.Def.AntennaHeightM ?? Rules.Terrain.DefaultAntennaHeightM`，含等效地球曲率与地形遮挡斜率包络，见 [01 §3.3.4](01_spawn_movement_terrain.md)）；不通 → 跳过。
4. 质量 `q = s.Def.TrackQuality`；对 `TrackQualityUpgrades` 每一项（数据顺序）：
   - `CloseRange`：`WithinRange(s.Pos, t.Pos, R × DetectionRules.CloseRangeFraction)` → `q = max(q, To)`；
   - `LinkedDroneTypes`：`EnemyIds` 包含 `t.DefId` → `q = max(q, To)`。
5. 上限：`q = min(q, Approximate)`（探测单位不产生"精确"，D2 / B-T2-33）；再若 `BLineApplies(s)`（3.2.7）→ `q = min(q, BLine.MaxTrackQuality)`。
6. 误差圈 `err = DetectionRules.ErrorRadiusM[q] × (s.Def.FastUpdate == true ? DetectionRules.FastUpdateErrorRadiusMult : 1.0)`。
7. `Route(new Detection(s.Id, Sensor, s.Def.Layer, t.Id, 0, t.Pos, t.AltM, t.VelMps, q, err, ctx.TimeSec), delay)`，`delay = max(s.Def.ReportDelay == true ? DetectionRules.ReportDelaySec : 0, BLineApplies(s) ? BLine.RelayDelaySec : 0)`。

#### 3.2.5 火控雷达与自主捕获（`FireControlDetect(f)`）

- **火控雷达**：`f.Def.FireControlRadar != null` 且 `f.DeployState == Deployed` 且 `!f.RadarDestroyed` 且 `!Suspended(f)`（A-2-12）且 `f.Emitter.On`。有效距离 `R = FireControlRadar.RangeM`，再按 3.2.3 依次乘断电倍率（`!f.Powered`）、冬季倍率（`season == Season.Winter` → `× DetectionRules.WinterActiveRangeMult`）、新阵地倍率、低空倍率（用 `FireControlRadar.LowAltitude`；火控雷达没有"低空盲区大"标记）。视线必需，调用 `Sensing.HorizonProfiles[f.Id].HasLineOfSightAgl(t.Pos, t.AltM)`（天线高度 `FireControlRadar.AntennaHeightM ?? Rules.Terrain.DefaultAntennaHeightM`）。通过 `ctx.ThreatGrid.QueryCircle` 遍历范围内、视线通的每个目标（ID 升序），产生 `Detection(f.Id, FireControl, Local, t.Id, 0, …, Quality = Precise, err = DetectionRules.ErrorRadiusM[Precise], ObservedAtSec = TimeSec)`，不延迟（B 线也不延迟：数值表 1.3"配属的车载雷达"）。
- **自主捕获**（无火控雷达的单位，如单兵导弹、高炮、火力组；B-T2-09、C-T2-07）：`f.Def.SelfAcquisitionRangeM != null` 且 `!Suspended(f)`（A-2-12）且（`f.DeployState == Deployed`，或 `f.DeployState == Moving` 且 `f.Def.FireOnMove != No`）。有效距离：
  ```
  R = f.Def.SelfAcquisitionRangeM
  if f.Def.SelfAcquisition == SelfAcquisitionKind.Optical:
      hasNightAid = f.Placement?.Settings.NightAids != null && f.Placement.Settings.NightAids.Count > 0
      nightMult   = (night.TimeOfDay == TimeOfDay.Day or hasNightAid) ? 1.0 : DetectionRules.OpticalNightRangeMult
      weatherMult = night.Weather == null ? 1.0 : DetectionRules.OpticalWeatherRangeMult[night.Weather]
      R = R × nightMult × weatherMult
  ```
  视线必需，调用 `Sensing.HorizonProfiles[f.Id].HasLineOfSightAgl(t.Pos, t.AltM)`（天线高度 `Rules.Terrain.DefaultAntennaHeightM`），不受低空倍率修正。产生 `Source = SelfAcquisition`、`Quality = Precise` 的探测。被动，不是辐射源。
- 同一火力单元两者都满足时只走火控雷达分支。

#### 3.2.6 覆盖型单位（`CoverageDetect(s)`）

对每个目标 `t`（ID 升序）：

1. 低空：`t.AltM < DetectionRules.LowAltitudeBelowM` 且 `s.Def.LowAltitude < DetectionRules.CoverageLowAltitudeMinCapability`（按 enum 整数值比较）→ 跳过。
2. `FullMap`：不检查位置（含地图外）。`UrbanAreas`：要求 `Geo.InUrban(ctx.Level, t.Pos)`。
3. `OnlyDetects`、升级规则与质量上限同 3.2.4 第 1、4、5 步（`CloseRange` 对覆盖型单位不适用，跳过）；不检查视线。
4. 产生探测：`Layer = s.Def.Layer`，延迟规则同 3.2.4 第 7 步（民众上报 `ReportDelay == true` → 延迟 `DetectionRules.ReportDelaySec`）。

#### 3.2.7 B 线空情转发

`BLineApplies(s)` = `Meta.Protagonist == B` 且 `s.Def.Layer == Regional`。（`AB` 视为 A：终章 A 直接控制区域雷达网。）
- 效果：该单位的探测延迟 `BLine.RelayDelaySec` 送达、质量不超过 `BLine.MaxTrackQuality`。
- `BLine.RegionalRadarDirectControl == false` 时，对这些单位的 `SetEmissionPolicy` 拒绝（`NotAvailable`，3.5.8）；它们按部署时的设置运行（关卡设计者预置）。（B-T2-47）

`DeliverDelayed()`：取出 `Delayed` 中全部 `DeliverTick ≤ Tick` 的条目（列表已按 `(DeliverTick, Seq)` 有序），按此顺序追加到 `Detections`。延迟探测**保留观测时的位置与时刻**（`ObservedAtSec`），不外推。来源单位此后被摧毁、或目标已被移除，延迟探测照常送达（目标已移除的会在 3.3.2 被丢弃）。

#### 3.2.8 国家预警 `EmitEarlyWarnings()`

1. 对 `WarningSchedule` 中 `Tick ≤ ctx.Tick` 且键 `"<WaveId>|<EntryId>"` 不在 `WarnedKeys` 中的条目（按表顺序）：发出 `EarlyWarning { WaveId, EntryId, ExpectedAtSec, BearingRad, Ballistic }`，加入 `WarnedKeys`。
2. 剧情或敌方 AI 注入的波次（在 3.2.1 第 3 步被跳过或延后触发）：在 `CurrentStep` 中看到 `WaveStarted { WaveId }` 时，在本夜 `night.Waves` 中按 `Id == WaveId` 查得该 `WaveDef`（所有注入波次均定义于本夜 `night.Waves` 中，A-2-28）；若该波次的任一 `(WaveId, EntryId)` 键（`entry.WarningSec != null`）不在 `WarnedKeys` 中，立即按第 1 步发出（`ExpectedAtSec = TimeSec`），即零提前量。
3. 预警**不创建航迹**：模糊航迹只来自探测（国家预警网自动单位会在目标进入其覆盖后提供模糊探测）。

#### 3.2.9 误报 `FalseAlarms()`

对每个 `SensorActive` 且 `Def.FalseAlarms != null` 的探测单位（ID 升序）：

1. `p = DetectionRules.FalseAlarmsPerSec[Def.FalseAlarms] × StepSec`；`if (!rng.Chance(p)) continue;`（每个单位每步恰好消耗 1 次 `NextDouble`）。
2. 位置：
   - 有探测距离：`u1 = rng.NextDouble(); u2 = rng.NextDouble()`；`r = R0 × Math.Sqrt(u1)`（`R0` = 3.2.3 中**不含低空项**的有效距离），`b = 2π × u2`；`pos = s.Pos + (r × Math.Sin(b), r × Math.Cos(b))`。
   - `UrbanAreas`：`i = rng.NextInt(0, Urban.Count)`（`Urban.Count == 0` → 不产生误报，但第 1 步的 `Chance` 已消耗）；在该多边形的轴对齐包围盒内最多尝试 8 次：`x = minX + (maxX − minX) × rng.NextDouble()`，`y = minY + (maxY − minY) × rng.NextDouble()`，`Geo.PointInPolygon` 为真即采用；8 次都失败 → 采用顶点算术平均值。
   - `FullMap`：（现有数据无此组合）`pos = (WidthM × rng.NextDouble(), HeightM × rng.NextDouble())`。
3. `key = NextPhantomKey++`；`Route(new Detection(s.Id, Sensor, s.Def.Layer, 0, key, pos, AltM: 0, VelMps: (0,0), Quality: q = 3.2.4 第 5 步的上限作用于 s.Def.TrackQuality（不做升级）, err = DetectionRules.ErrorRadiusM[q], TimeSec), delay)`（延迟规则同 3.2.4）。

误报航迹只有这一次探测，之后按 3.3.2 超时丢失。

### 3.3 `TrackFusionSystem`（Order 4，子流 `fusion`）

#### 3.3.1 关联方式

按**真实目标**关联：真实探测的键 = `ThreatId`，误报探测的键 = `PhantomKey`。每个键至多一条 Alive 航迹。查找表 `trackByThreat`、`trackByPhantom` 每步由 `Tracks` 重建（`Dictionary` 只查找，不遍历）。

理由：见 0.4 D1。代价是"同一目标被两个相距很远的传感器看到时，界面只显示一条航迹"——这本来就是理想的融合结果。

#### 3.3.2 每步流程与无分配桶分组（C-T1-17）

```
# 1. 目标已消失的航迹立即删除
for each Track k (ID 升序): if k.ThreatId != 0 and !Threats.TryGet(k.ThreatId): Remove(k); emit TrackLost{k.Id, ThreatGone}
# 2. 分组：把 Detections 按键分组（丢弃 ThreatId 指向已不存在目标的探测）
#    组的处理顺序：真实键按 ThreatId 升序，然后误报键按 PhantomKey 升序
# 3. 对每组：已有航迹 → Update；没有 → Create
# 4. 本步没有任何探测的航迹 → Coast（3.3.7）
# 5. 诱饵甄别（3.3.8）：对本步 Create / Update 过的航迹，按航迹 ID 升序
```

- **确定性 $O(N)$ 桶分组实现约定**（C-T1-17）：`Detection` 为值类型 `readonly record struct`，存储在 `Sensing.Detections` 复用列表中。第 2 步不得使用 `Dictionary` 遍历或每步堆分配 `List<Detection>`：对真实探测（`d.ThreatId != 0 && Threats.TryGet(d.ThreatId)`），以 `d.ThreatId - minThreatId` 为桶下标，用系统内复用的整数数组 `head[]` / `next[]` 建立链式桶，按桶下标从 `0` 到 `maxThreatId - minThreatId` 顺序遍历非空桶（桶内保持 `Detections` 原始产生顺序）；对误报探测（`d.PhantomKey != 0`）同理按 `PhantomKey` 升序遍历。

#### 3.3.3 融合质量

对一组探测 `G`（同一键）：

```
sensorDets  = G 中 Source == Sensor 的探测
preciseDets = G 中 Source ∈ {FireControl, SelfAcquisition} 的探测
localCount  = sensorDets 中 Layer == Local 的不同 SourceId 个数
netQ = sensorDets 为空 ? null : max(sensorDets.Quality)
if netQ == Vague and localCount ≥ ApproximateFromLocalSensorCount: netQ = Approximate     # 交叉升级
if "fire_team_network" ∈ CarryIn.Doctrines:                                               # 条令：火力组联网（B-T2-126）
    optCount = preciseDets 中 Source == SelfAcquisition 且 FireUnit.Def.SelfAcquisition == Optical 的不同 SourceId 个数
    if optCount ≥ 2: netQ = max(netQ ?? Vague, Approximate)
Quality = max(netQ ?? Vague, preciseDets 非空 ? Precise : Vague)
NetworkQuality = netQ
LocalSensorCount = localCount
PreciseHolderIds = preciseDets 的 SourceId 去重升序
```

- 交叉升级只把"模糊"升到"大致"，不会到"精确"。国家层、区域层探测单位不计入 `localCount`；火控 / 自主捕获探测不计入 `localCount`（但解锁 `fire_team_network` 条令后，≥ 2 个光学自主捕获火力单元同时看到目标时可将 `NetworkQuality` 升为 `Approximate`）。
- 民众上报（一个自动单位）只算 1 个本地传感器。误报探测各自独立成组，永远不会交叉升级。
- 延迟送达的探测与当步新探测一样参与。

#### 3.3.4 "精确"的含义（D2）

- `Quality == Precise` ⇔ 本步至少一个火力单元的火控雷达 / 自主捕获锁定了目标。
- **03 的约定**（已决 B-T2-33、A-2-08）：火力单元 `f` 用导弹或制导火箭（`Kind ∈ {Missile, Rocket}`）交战航迹 `k` 的前提是 `f.Id ∈ k.PreciseHolderIds`；其他单位只能看到"这条航迹是精确的"，不能借用。

#### 3.3.5 位置、速度、误差圈

- 选中探测 `best`：先 `preciseDets` 中 `SourceId` 最小者；没有则 `sensorDets` 中按（`Quality` 降序，`ObservedAtSec` 降序，`SourceId` 升序）的第一个。
- `Pos = best.Pos`，`AltM = best.AltM`，`VelMps = best.VelMps`，`LastObservedAtSec = best.ObservedAtSec`。
- `ErrorRadiusM`：若 `G` 中存在 `Quality == 航迹 Quality` 的探测 → 其中 `ErrorRadiusM` 的最小值；否则（质量来自交叉升级）→ `DetectionRules.ErrorRadiusM[Quality]`。
- `LastDetectedTick = Tick`。

#### 3.3.6 对外显示的标签

`Tag = Quality ≥ Approximate 且 ThreatId != 0 ? DisplayTag(threat) : null`，其中 `DisplayTag = (threat.Tag == DECOY && !DecoyIdentified) ? Intercept.DecoyUsesColumn : threat.Tag`（未识别的诱饵与无人机外观相同）。甄别成功后同步更新 `Tag`。
- 全目录统一使用 `Track.Tag`（A-2-01 / B-T1-23）；03 对 `Quality == Vague`（`Tag == null`）的航迹进行高炮交战时，按 `Intercept.DecoyUsesColumn`（无人机外观）处理。

#### 3.3.7 创建、更新、外推、丢失

- **Create**：`Tracks.Add`，填 3.3.3–3.3.6 的全部字段，`DefId = ""`；发出 `TrackCreated { TrackId, Quality }`。
- **Update**：重算 3.3.3–3.3.6；`Quality` 变化 → `TrackQualityChanged { TrackId, From, To }`。
- **Coast**（本步无探测）：
  1. `Pos += VelMps × StepSec`；`AltM`、`ErrorRadiusM` 不变；`NetworkQuality = null`；`LocalSensorCount = 0`；`PreciseHolderIds` 清空。
  2. 若 `Quality == Precise` → 改为 `Approximate`（精确需要持续锁定），发 `TrackQualityChanged`；`Tag` 按 3.3.6 重算（仍 ≥ Approximate，标签保留）。
  3. 若 `(Tick − LastDetectedTick) × StepSec > DetectionRules.TrackLostSec`（严格大于）→ `Remove`，发 `TrackLost { TrackId, Timeout }`（误报航迹同样走此路径）。
- 质量**升降都立即生效**（有探测的步）：例如本地交叉的两个传感器之一失去目标，当步即从"大致"降为"模糊"。
- 航迹丢失后目标再次被探测 → 新建航迹（新 ID，甄别状态重置）。

#### 3.3.8 诱饵甄别（含敌情档案加成，A-2-22 / R-02-1）

只对 `ThreatId != 0`、`!DecoyIdentified` 且目标 `Tag == DECOY` 的航迹（ID 升序）：

```
q = k.Quality
if k.DecoyCheckedQuality != null and q <= k.DecoyCheckedQuality: 跳过         # 每个质量等级最多掷一次；降级不重掷
add   = DossierDiscriminationAdd(ctx, threat.DefId)                           # CarryIn.Dossier 中匹配项的 DiscriminationAdd，无则 0.0
pNew  = Qualities[q].DecoyDiscrimination <= 0 ? 0.0 : Math.Min(1.0, Qualities[q].DecoyDiscrimination + add)
pPrev = (k.DecoyCheckedQuality == null or Qualities[k.DecoyCheckedQuality].DecoyDiscrimination <= 0)
        ? 0.0 : Math.Min(1.0, Qualities[k.DecoyCheckedQuality].DecoyDiscrimination + add)
k.DecoyCheckedQuality = q
if pNew <= pPrev or pPrev >= 1.0: 跳过（不消耗随机数）
p = (pNew - pPrev) / (1 - pPrev)                 # 条件概率：累计识别率恰为 pNew（B-T2-51）
if rng.Chance(p): k.DecoyIdentified = true; 重算 Tag; emit DecoyIdentified{k.Id}
```

- 模糊航迹 `Qualities[Vague].DecoyDiscrimination == 0` → `pNew = 0`，不掷（数值表：模糊不能甄别，即使有敌情档案加成也不在模糊阶段甄别）。`DossierCarryIn.ClassifyTimeMult` 在本版本即时分类模型中保留未用。
- 只掷"真诱饵"：对非诱饵目标不掷，也不会出现"把真目标误判为诱饵"。
- 在 3.3.2 第 5 步执行，即同一步内先确定质量再甄别。

### 3.4 `ElectronicWarfareSystem`（Order 5，子流 `ew`）

#### 3.4.1 覆盖

电子战单位 `u` 本步**生效**：`u.DeployState == Deployed` 且 `!Suspended(u)`（A-2-12）且 `u.Emitter.On`（上一步结果）。
`Covers(u, t)` = `u` 生效 且 `WithinRange(u.Pos, t.Pos, u.Def.RadiusM)`（水平距离，不看高度）且 `u.Def.EffectiveAgainst` 包含 `t.DefId` 且 `!(t 的 MunitionDef?.EwImmune == true)`。

#### 3.4.2 每步流程

```
for each Threat t (ID 升序), Alive:
    if t.Phase == ThreatPhase.Arrived: continue     # 本步第 2 步已到达、待第 10 步结算落点的目标不再受电子战影响（A-4-06）
    HoverTimeout(t)                                 # 3.4.6：悬停到时 → 发 EwLinkCut{Crash} 并移除，continue
    if 存在 u 满足 Covers(u, t) 且 u.Def.Effect ∈ {NavJam, NavSpoof}:
        t.EwEverCovered = true                      # 粘性覆盖标记，不掷骰、不耗随机数（A-2-07）
    NavEffect(t)                                    # 3.4.4
    SpoofPull(t)                                    # 3.4.5
    NationalSpoof(t)                                # 3.4.6
    LinkCut(t)                                      # 3.4.6（可能移除 t）
UrbanNavJam()                                       # 3.4.8
```

每个函数内部的随机数消耗只发生在"满足条件、需要掷骰"时，且每次掷骰恰好 1 次 `Chance`（链路中断成功后再加 1 次 `NextDouble`）。

#### 3.4.3 效能概率

单位 `u` 对目标 `t` 的效果概率（含断电倍率 B-T2-05、冬季倍率 C-T2-07、研发加成 R-02-1）：

```
base   = (u.Def.Effect ∈ {NavJam, NavSpoof}) ? Ew.Effectiveness.Nav : Ew.Effectiveness.CounterUas
if CarryIn.ResearchEffects 含 "ew_effectiveness_add": base = Math.Clamp(base + value, 0.0, 1.0)
weak   = (u.Def.FirstAvailable?.FullStrengthLevel != null and Meta.Number != null
          and Meta.Number < u.Def.FirstAvailable.FullStrengthLevel) ? Ew.BelowFullStrengthMult : 1.0
power  = u.Powered ? 1.0 : Ew.UnpoweredEffectMult
winter = (SeasonFor(night) == Season.Winter) ? Ew.WinterEffectMult : 1.0
newp   = u.NewPositionPenalty ? Positions.NewUnsurveyed.FirstNightEfficiencyMult : 1.0
ai     = AiVisionMult(u, t)                                  # 3.4.5；非导航效果恒为 1.0
P(u, t) = base × weak × power × winter × newp × ai           # 按此顺序从左到右相乘
```

多个单位同时覆盖时取 `P` 最大者（并列取 ID 最小者）作为"生效单位"，只掷一次。

#### 3.4.4 导航干扰 / 欺骗的落点效果 `NavEffect(t)`

```
if t.EwNav != None: return
cands = { u : Covers(u, t) 且 u.Def.Effect ∈ {NavJam, NavSpoof} }
if cands 为空: return
(u*, p) = argmax P
if p <= 0: return                                   # 状态保持 None，不掷，以后仍可能被其他单位影响
if rng.Chance(p):
    t.EwNav = Applied
    ReconcileNavAccuracy(t)                         # B-T3-08 / A-2-07：按原精度档写 EwExtraOffsetM，不降档；若国家级欺骗也已生效则取较大者
    emit EwDiverted { ThreatId = t.Id, SourceId = u*.Id, Kind = EwDivertKind.NavJam }
else:
    t.EwNav = Resisted
```

`ReconcileNavAccuracy(t)`（统一维护 `t.EwExtraOffsetM` 与 `t.AccuracyTierDrop`，在 `NavEffect` 或 `NationalSpoof` 置 `Applied` 时调用；B-T3-08、A-2-07）：

```
if t.Kind != EntityThreatKind.Munition:
    t.EwExtraOffsetM = 0.0; t.AccuracyTierDrop = 0; return
T0 = t 的 MunitionDef.Accuracy
unitExtra = (t.EwNav == Applied) ? Accuracy.Tiers[T0].EwExtraM : 0.0
natDrop   = (t.NationalSpoof == Applied) ? t.NationalSpoofDrop : 0          # national_gnss_spoof 为 2
if natDrop == 0:
    t.AccuracyTierDrop = 0; t.EwExtraOffsetM = unitExtra; return
if t.EwNav != Applied:
    t.AccuracyTierDrop = natDrop; t.EwExtraOffsetM = 0.0; return
# 单位电子战与国家级导航欺骗同时 Applied：按期望偏移增量取较大者，不叠加（B-T3-08）
order = Accuracy.TierOrder                                                  # [D, C, B, A]
Tdrop = order[Math.Clamp(order.IndexOf(T0) - natDrop, 0, order.Count - 1)]
natDelta = 0.5 * (Accuracy.Tiers[Tdrop].OffsetM.Min + Accuracy.Tiers[Tdrop].OffsetM.Max)
         - 0.5 * (Accuracy.Tiers[T0].OffsetM.Min    + Accuracy.Tiers[T0].OffsetM.Max)
if natDelta >= unitExtra:
    t.AccuracyTierDrop = natDrop; t.EwExtraOffsetM = 0.0
else:
    t.AccuracyTierDrop = 0; t.EwExtraOffsetM = unitExtra
```

- 单位电子战只增加 `Accuracy.Tiers[T0].EwExtraM`（A/B +1 格、C/D +2 格），**不降精度档**（`EwUnitDef.AccuracyTierDrop` 不参与计算，`offsetCellsAdd` 仅界面显示；已决 B-T3-08）。
- 平台（`PlatformDef`）没有精度档：若平台出现在 `EffectiveAgainst` 中，`Applied` 时 `EwExtraOffsetM = 0`（只记录状态）。
- 03 在落点结算时读取 `t.AccuracyTierDrop` 与 `t.EwExtraOffsetM`（A-2-07）。

#### 3.4.5 导航欺骗：诱导点 `SpoofPull(t)` 与 AI 视觉修正

`AiVisionMult(u, t)`（仅 `NavJam` / `NavSpoof`）：

```
if not (t 的 MunitionDef?.AiVisionActive == true): return 1.0
if u.Def.Effect == NavJam and Ew.Effectiveness.NavTerminalIneffectiveVsAiVision: return 0.0   # 末段无效
return u.Def.AiVisionEffectMult ?? 1.0
```

诱导：

```
if t.EwNav != Applied or t.EwPull != None: return
cands = { u : Covers(u, t) 且 u.Def.Effect == NavSpoof 且 u.LurePoint != null 且 u.Def.PullChance != null }
if cands 为空: return
pu = u.Def.PullChance × weak(u) × power(u) × winter × newp(u) × (t 是 AI 视觉 ? (u.Def.AiVisionEffectMult ?? 1.0) : 1.0)
(u*, p) = argmax pu（并列取 ID 最小）
if p <= 0: return
if rng.Chance(p):
    t.EwPull = Applied
    t.EwDivertPos = u*.LurePoint
    ThreatRouting.Retarget(ctx, t, u*.LurePoint.Value)                      # 01 3.2.8：立即改航向诱导点（A-2-27）
    emit EwDiverted { ThreatId = t.Id, SourceId = u*.Id, Kind = EwDivertKind.NavSpoofPull }
else:
    t.EwPull = Resisted
```

- 诱导以"导航已被干扰"为前提（同一步内先 `NavEffect` 后 `SpoofPull`，两次掷骰）。`PullChance` 不再乘时期效能（已在 `NavEffect` 中计入，避免重复）。
- 改航通过调用 01 的 `ThreatRouting.Retarget(ctx, t, u*.LurePoint.Value)` 立即生效（A-2-27）；`EwDivertPos` 保留在 `Threat` 上供 03 与复盘记录读取。

#### 3.4.6 国家级导航欺骗、链路中断、悬停

**国家级导航欺骗**（外部支援的效果；呼叫、延迟、持续时间由 03 的 `ExternalSupportSystem` 管理；A-2-21、B-T2-04、B-T3-08）：

```
if t.NationalSpoof != None or (t 的 MunitionDef?.EwImmune == true): return
for each SupportAsset a (ID 升序), Alive, a.State == SupportAssetState.Active, a.Effect == SupportEffect.AccuracyDrop:
    def = Catalog.GetSupport(a.DefId)
    ref = Catalog.GetEwUnit(def.AffectsSameAsEwUnitId)
    if ref.EffectiveAgainst 不含 t.DefId or !WithinRange(a.CenterPos, t.Pos, a.RadiusM): continue
    p = Ew.Effectiveness.Nav × ((t 是 AI 视觉 且 NavTerminalIneffectiveVsAiVision) ? 0 : 1)
    if p <= 0: return
    if rng.Chance(p):
        t.NationalSpoof = Applied
        ReconcileNavAccuracy(t)                                             # B-T3-08：降 2 档，与单位电子战取较大者、不叠加
        emit EwDiverted { ThreatId = t.Id, SourceId = a.Id, Kind = EwDivertKind.NationalSpoof }
    else:
        t.NationalSpoof = Resisted
    return                                                                  # 只取第一个覆盖它的支援实体
```

**链路中断** `LinkCut(t)`（A-2-27、A-3-07、A-4-04）：

```
if t.LinkCutState != None: return
cands = { u : Covers(u, t) 且 u.Def.Effect ∈ {LinkCut, LinkCutDirectional} }
if cands 为空: return
(u*, p) = argmax P（3.4.3，ai = 1）
if p <= 0: return
if not rng.Chance(p): t.LinkCutState = Resisted; return
outcomes = u*.Def.LinkCutOutcomes（数据顺序）；w_i = Ew.LinkCutOutcomeWeights[outcome_i]；W = Σ w_i
if W <= 0: t.LinkCutState = Resisted; return            # 数据错误兜底；加载器应保证 W > 0
x = rng.NextDouble() × W；依次累加 w_i，取第一个满足 x < 累计和 的 outcome（全部不满足时取最后一个）
switch outcome:
    Crash:
        emit EwLinkCut { ThreatId = t.Id, SourceId = u*.Id, Outcome = LinkCutOutcome.Crash, DefId = t.DefId }
        Threats.Remove(t.Id)                            # 坠毁，不造成地面伤害（B-T3-08）
    Hover:
        t.LinkCutState = Hover; t.LinkCutAtTick = Tick
        ThreatRouting.Hover(ctx, t)                     # 01 3.2.8：原地悬停（A-2-27）
        emit EwLinkCut { ThreatId = t.Id, SourceId = u*.Id, Outcome = LinkCutOutcome.Hover, DefId = t.DefId }
    Return:
        t.LinkCutState = Return
        ThreatRouting.BeginEgress(ctx, t)               # 01 3.2.8：掉头飞向最近地图边离开（A-2-27）
        emit EwLinkCut { ThreatId = t.Id, SourceId = u*.Id, Outcome = LinkCutOutcome.Return, DefId = t.DefId }
```

- `LinkCutDirectional`（单兵反无人机枪）按全向处理（B-T2-53）。
- 悬停与返航通过调用 01 的 `ThreatRouting.Hover(ctx, t)` 与 `ThreatRouting.BeginEgress(ctx, t)` 落地（A-2-27），两者在移除前仍可被拦截。

`HoverTimeout(t)`（A-4-04）：`t.LinkCutState == Hover` 且 `Tick ≥ t.LinkCutAtTick + SecToTicksCeil(Ew.HoverBeforeCrashSec, StepSec)` → 先发出终止事件 `EwLinkCut { ThreatId = t.Id, SourceId = 0, Outcome = LinkCutOutcome.Crash, DefId = t.DefId }`（`SourceId = 0` 表示悬停超时坠毁，满足 00 6.1 #9"每个被移除的 `Threat` 都有终止事件"，并供 03 `ScoringSystem` 计入 `KillsByEnemy`），再 `Threats.Remove(t.Id)`，`continue`。

#### 3.4.7 车载防护罩与友军干扰（查询函数，不改状态）

```csharp
public static class EwQueries
{
    // 03 在敌方无人机命中我方车辆时调用：返回命中概率倍率
    public static double ShieldHitProbMult(SimState s, GameCatalog c, int targetUnitId, string threatDefId);
    // 03 在拦截无人机判定时调用：pos 是否处于己方电子战干扰区
    public static bool IsInFriendlyEwZone(SimState s, GameCatalog c, Vec2 pos);
}
```

- `ShieldHitProbMult`：目标单位存在且 `EquipmentEwIds` 中有 `Effect == SelfProtection` 且 `EffectiveAgainst` 含 `threatDefId` 的定义 `d`（多个取第一个）、且目标单位 `DeployState != Packed`、且威胁不是 `EwImmune` → 返回 `1 − (1 − d.HitProbMult) × Ew.Effectiveness.CounterUas`；否则 `1.0`。
- `IsInFriendlyEwZone`：存在生效的 `EwUnit u`（3.4.1，不检查目标），`u.Def.Effect ∈ {NavJam, NavSpoof, LinkCut, LinkCutDirectional}` 且 `WithinRange(u.Pos, pos, u.Def.RadiusM)`。倍率本身由 03 从 `rules/intercept.json` 的 `interceptorDroneInFriendlyEw` 读取（`rules/ew.json` 的 `friendlyInterceptorDroneMult` 仅界面显示或删除，B-T1-08）。
- `sideEffects.ownDroneLinkCut`：数值表未给概率，本版本不实现（B-T1-08）。

#### 3.4.8 城区导航干扰

`UrbanNavJam()`：若存在生效的 `EwUnit u`，`u.Def.Effect ∈ {NavJam, NavSpoof}` 且 `Geo.InUrban(ctx.Level, u.Pos)` → `Ew.UrbanNavJamSec += StepSec`（每步至多加一次，与单位个数无关）。
夜晚结束时由 03 / 05 判定：`UrbanNavJamSec ≥ Ew.UrbanNavJamMinSec` → 本夜触发一次（05 将城市资源 `CityResource −= 1`，B-T2-36）。

### 3.5 `EmissionSystem`（Order 6，子流 `emission`——本文件规则不消耗随机数）

#### 3.5.1 每步流程

```
ProcessEvents()                    # 3.5.6：游标读取 PlayerUnitDestroyed、InterceptorLaunched、GunFired
ArmScan()                          # 3.5.5 第 0–3 步：HomingUnitId 维护、初始距离、来袭识别、ArmSilenced
DeceptionAttractScan()             # 3.7.1
for each 辐射源 e（FireUnit → SensorUnit → EwUnit → DeceptionUnit，各自 ID 升序）:
    (on, cause) = Desired(e)       # 3.5.3
    if e.FireUnit: e.Emitter.FcMode = on ? (CueAvailable(e) ? Cued : SelfSearch) : Off     # 3.5.4
    if on != e.Emitter.On: Switch(e, on, cause)
AfterFiringScan()                  # 3.5.6
```

`Switch(e, on, cause)`：`e.Emitter.On = on`；`on` → `OnSinceTick = Tick`，否则 `OnSinceTick = −2`（表示当前关机但本夜曾开机；从未开机过的单位保持初值 `−1`）；发出 `EmitterSwitched { UnitId, On, Cause }`；若 `on == false` → `ArmShutdownEffect(e)`（3.5.5 第 4 步）；若 `on == true` → `ArmReacquire(e)`。

#### 3.5.2 策略可用性 `EmissionPolicyRules.CheckAvailable(string unitDefId, EmissionStrategyDef strategy, LevelData level) : CommandRejectReason?`

参数为定义 ID `unitDefId`（供 04 `DeploymentValidator` 在实体创建前直接调用，命令处理时传入 `unit.DefId`；A-2-25）。按顺序检查，第一个不满足的返回：

1. `strategy.Activation == LastMoment`（静默待机）：`unitDefId` 必须是 `level.Catalog.AirDefenseUnits` 中 `FireControlRadar != null` 的定义 → 否则 `WrongEntityKind`。
2. `strategy.WesternSystemsOnly == true`：`unitDefId` 是 `AirDefenseUnitDef` 且 `FireControlRadar?.Origin == SystemOrigin.Western`（其他定义视为不满足）→ 否则 `NotAvailable`。
3. `strategy.AvailableFromLevel != null` 且 `level.Meta.Number != null` 且 `level.Meta.Number < AvailableFromLevel` → `NotAvailable`。（`Meta.Number == null` 的测试关卡不受限。）
4. `Requires` 中的 `ApproximateTrack`、`Network`、`Decoy` 是**运行时条件**（3.5.3），不在此检查。

#### 3.5.3 期望状态 `Desired(e)`

按顺序，第一个命中的决定结果（含雷达被毁与重伤暂停，A-2-12）：

| # | 条件 | 结果 | `Cause` |
|---|---|---|---|
| 1 | `e.DeployState != Deployed` | 关 | `NotDeployed` |
| 1a | `e is FireUnit f && f.RadarDestroyed` | 关 | `RadarDestroyed` |
| 1b | `Suspended(e)`（`e.SuspendedUntilSec > ctx.TimeSec + 1e-9`） | 关 | `Suspended` |
| 2 | `Forced == Silence` | 关 | `SectorSilence` |
| 3 | `Forced == ForceOn` | 开 | `SectorForceOn` |
| 4 | `ArmSilenced` | 关 | `ArmShutdown` |
| 5 | `TakeoverActive` | 开 | `Takeover` |
| 6 | 按策略 `Activation`（下表） | 开 / 关 | `Policy` |

| `Activation` | 开机条件 |
|---|---|
| `Always` | 恒开 |
| `ApproximateWarning` | `WarnTrack(e)`：通过 `ctx.TrackGrid.QueryCircle(e.Pos, RefRange(e))` 检查存在航迹 `k`，`k.Quality ≥ Approximate` 且 `WithinRange(e.Pos, k.Pos, RefRange(e))` |
| `DutyCycle` | `onT = SecToTicksCeil(DutyOnSec)`，`offT = SecToTicksCeil(DutyOffSec)`（两者 ≥ 1，见 3.5.8），`phase = (Tick − DutyPhaseStartTick) mod (onT + offT)`；`phase < onT` 为开 |
| `LastMoment` | `CueWindow(e)`（3.5.4）；非火力单元恒关 |
| `AfterDecoy` | 若场上**不存在**任何存活的 `FakeEmitter` / `SacrificialEmitter` 欺骗单位 → 等同 `ApproximateWarning`；否则 `WarnTrack(e)` 且存在这样的欺骗单位 `d`：`d.Emitter.On` 且 `d.Emitter.OnSinceTick ≥ 0` 且 `(Tick − d.Emitter.OnSinceTick) × StepSec ≥ DecoyLeadSec` |

`RefRange(e)`：`SensorUnit` → `DetectionRangeM`（覆盖型自动单位不是辐射源，不会出现）；`FireUnit` → `FireControlRadar.RangeM`；`EwUnit` → `RadiusM`；`DeceptionUnit` → `Emission.DefaultReferenceRangeM`。

- 遍历顺序使诱饵（`DeceptionUnit`）在本步晚于其他辐射源被评估："诱饵配合"读取的是诱饵**上一步**的开关状态。这是有意的（诱饵"先"开机）。
- `WarnTrack` 使用的航迹包含本单位自己的贡献（雷达开机后自己维持"大致"，目标离开范围或航迹丢失才关机）。

#### 3.5.4 火控指示联动与查询接口（WS01-014，A-2-08、A-2-30、B-T2-01）

对带火控雷达的火力单元 `f`：

```
CueAvailable(f) = 存在航迹 k（经 ctx.TrackGrid.QueryCircle(f.Pos, f.Def.FireControlRadar.RangeM)）：
                  FireControlQueries.Cued(k, Rules.Tracks)
                  且 WithinRange(f.Pos, k.Pos, f.Def.FireControlRadar.RangeM)

CueWindow(f) = Cueing.Cued.FireControlOnlyLastReactionTime 且 存在航迹 k：
      FireControlQueries.Cued(k, Rules.Tracks)
      且 k.Tag != null 且 存在武器 w ∈ f 的武器：w.Targets 含 k.Tag.Value 且 k.AltM ≤ w.CeilingM
      且 τ = SensingMath.TimeToEnterRadius(k.Pos, k.VelMps, f.Pos, Rw) != null 且 τ ≤ ReactionEff(f, w)
  其中 Rw = WeaponParams.RangeFor(w, k.Tag.Value)
       ReactionEff(f, w) = WeaponParams.ReactionSec(w, Rules.Engagement) × FireControlQueries.ReactionMult(f, Rules.Emission)
  （对每个满足条件的武器 w 分别计算 Rw 与 ReactionEff(f, w)，任一满足即可）
```

供 03 与本文件共用的只读火控查询工具（`Nightwatch.Sim.Sensing.FireControlQueries`，A-2-08）：

```csharp
public static class FireControlQueries
{
    public static bool Cued(Track k, TrackRulesDef rules)
        => k.NetworkQuality != null && k.NetworkQuality >= rules.Cueing.Cued.MinTrackQuality;

    public static bool HasFireControlRadar(FireUnit f)
        => f.Def.FireControlRadar != null;

    public static double ReactionMult(FireUnit f, EmissionRulesDef rules)
        => f.Emitter == null ? 1.0 : rules.GetStrategy(f.Emitter.PolicyId).ReactionTimeMult;

    public static bool SilentHold(FireUnit f, double timeSec)
        => f.Emitter != null && !f.Emitter.On && f.DeployState == UnitDeployState.Deployed
           && !f.RadarDestroyed && f.SuspendedUntilSec <= timeSec + 1e-9;
}
```

- `NetworkQuality` 只统计探测单位（"网络"），**不含**火力单元自己的精确探测，因此火控雷达开机后不会因为自己的锁定而"自我指示"。
- 静默待机的"需'大致'航迹 + 网络"即：没有网络提供的"大致"航迹时，`CueWindow` 恒为假，雷达保持关机（因而无法发射导弹）。
- `FcMode`：开机时 `CueAvailable` 为真 → `Cued`（暴露速率 `FireControlCued`），否则 `SelfSearch`（暴露速率 `FireControlSelfSearch`）。`FcMode` 只用于本文件的暴露速率计算；03 的"无指示自搜首发反应时间 ×1.5"按逐条航迹的 `FireControlQueries.Cued(track, Rules.Tracks)` 判定并读取 `intercept.modifiers.noCueSelfSearch.firstShotReactionTimeMult`（A-2-08）。

#### 3.5.5 反辐射导弹与关机时机

反辐射导弹 = `MunitionDef.TracksEmittingRadarOnly == true` 的目标。

0. **归航目标维护**（`HomingUnitId`，A-2-06）：对每个存活的反辐射导弹 `m`（ID 升序），令 `U` 为 `Id == m.TargetUnitId` 的存活辐射源单位；置 `m.HomingUnitId = (U != null && U.Emitter != null && U.Emitter.On) ? U.Id : 0`（本步第 6 步写入，下一步第 2 步由 01 `ApplyHoming` 读取：雷达关机后 `HomingUnitId == 0`，导弹飞向关机前最后记录的位置）。
1. **初始距离**：对每个存活的反辐射导弹 `m`（ID 升序），若 `m.ArmInitialDistM == 0` 且 `m.TargetUnitId != 0` 且目标单位存活 → `m.ArmInitialDistM = |m.Pos − target.Pos|`（水平），若结果为 0 则取 `1e-9`（避免再次进入此分支）。（已决 B-T2-37。）
2. **来袭识别**：对每条航迹 `k`（ID 升序）：`k.ThreatId` 对应反辐射导弹 `m`、`k.Quality ≥ Approximate`、`m.TargetUnitId` 是存活的辐射源单位 `U`、`!k.ArmWarned` → `k.ArmWarned = true`，发出 `ArmThreatDetected { TrackId = k.Id, TargetUnitId = U.Id }`，并按 `U.Emitter.OnArmIncoming` 处理：
   - `ShutdownImmediately` → `U.Emitter.ArmSilenced = true`。
   - `ShutdownAfterCurrentIntercept` → 若 `U` 是火力单元且存在存活的 `Interceptor` 其 `FireUnitId == U.Id` → `U.Emitter.ArmPending = true`；否则同上立即 `ArmSilenced = true`。
   - `KeepEngaging` → 不处理。
3. **待关机 / 解除**（对每个辐射源单位 `U`，ID 升序；`armAlive(U)` = 存在存活的反辐射导弹且 `TargetUnitId == U.Id`）：
   - `ArmPending` 且 `!armAlive(U)` → `ArmPending = false`。
   - `ArmPending` 且 `U` 已没有存活的自家拦截弹 → `ArmPending = false`，`ArmSilenced = true`。
   - `ArmSilenced` 且 `!armAlive(U)` → `ArmSilenced = false`（导弹被拦截 / 落地 / 移除后恢复策略）。
4. **关机时机效果** `ArmShutdownEffect(U)`（`U` 由开转关时调用，无论原因）：对每个存活的反辐射导弹 `m`（ID 升序），`m.TargetUnitId == U.Id` 且 `m.ArmInitialDistM > 0`：
   ```
   f = |m.Pos − U.Pos| / m.ArmInitialDistM
   m.ArmHitProbMult = Emission.ShutdownTiming 中按数据顺序第一个满足 f > ArmDistanceFractionAbove 的档位的 ArmHitProbMult；都不满足 → 1.0
   ```
5. `ArmReacquire(U)`（`U` 由关转开时）：对 `TargetUnitId == U.Id` 的存活反辐射导弹，`ArmHitProbMult = null`（重新锁定，之前的关机效果作废）。
6. 反辐射导弹的**目标选择**（包括被诱饵吸引、暴露度 ≥ 40 优先）不在本文件，由 01（调 04 钩子）唯一写 `TargetUnitId`（A-2-04）；对单位伤害判定时由 03 乘 `ArmHitProbMult ?? 1.0`（A-2-07）。
7. **二选一落地接口**（供 04 `ChoiceStage` 在玩家回答或超时默认时调用，A-2-11）：
   ```csharp
   namespace Nightwatch.Sim.Sensing;
   public static class EmissionChoiceEffects
   {
       public static void ApplyArmChoice(SimState s, int unitId, bool silence)
       {
           if (!s.FireUnits.TryGet(unitId, out var u) || u.Emitter == null) return;
           u.Emitter.ArmSilenced = silence;
           u.Emitter.ArmPending = false;
       }
   }
   ```

#### 3.5.6 事件消费：开火后转移、主雷达被毁

`ProcessEvents()`（游标 `EmissionEventCursor`，3.1）：

- `InterceptorLaunched { FireUnitId }` / `GunFired { FireUnitId }`：若该火力单元存活且有 `Emitter`（无火控雷达的火力单元没有 `Emitter`，见下注）→ `FiredSinceRelocation = true`，`LastShotTick = 事件.Tick`。
- `PlayerUnitDestroyed { UnitId, DefId, Category, SourceThreatId, Pos }`（A-2-05、A-3-05）：若被毁单位是辐射源型探测单位（`Category == SensorUnit` 且 `Emission == Active`）或带火控雷达的火力单元（依据 `DefId` 查定义判断）→ 对每个存活的辐射源 `U`（ID 升序），`U.Emitter.NeighborTakeover && !U.Emitter.TakeoverActive && WithinRange(U.Pos, 事件.Pos, RefRange(U))` → `U.Emitter.TakeoverActive = true`（本夜一直保持；玩家可用 `SetEmissionPolicy` 清除，3.5.8）。

> 注："开火后转移"触发规则只对拥有 `Emitter` 的火力单元有效，**不受展开时间档位（`DeployTier`）限制且不消耗指挥点**（若小时档单位配置了"开火后转移"，夜间触发后会撤收并在当夜剩余时间失去战斗力；已决 B-T3-06）。

`AfterFiringScan()`：对每个有 `Emitter` 的火力单元 `f`（ID 升序）：
`AfterFiring == RelocateToAlternate` 且 `FiredSinceRelocation` 且 `LastShotTick ≤ Tick − 2`（至少一个整步未开火）且没有存活的自家拦截弹 且 `f.Placement?.AlternatePositionId != null` 且 `f.PendingRelocationAltId == null` → `f.PendingRelocationAltId = f.Placement.AlternatePositionId`，`FiredSinceRelocation = false`。由 04 的部署状态机执行转移并清空该字段。

#### 3.5.7 `Initialize`

对每个辐射源（3.5.1 的顺序）：按 3.5.3 求初值，但此时没有航迹、没有反辐射导弹：`Always` → 开；`DutyCycle` → `phase = 0` → 开；其他 → 关。`DeployState != Deployed`、`RadarDestroyed` 或 `Suspended` → 关。**不发事件**（`NightStarted` 必须是 `Seq 1`）。开 → `OnSinceTick = 0`，关 → `OnSinceTick = −1`；`FcMode`：开 → `SelfSearch`（无航迹），关 → `Off`。

#### 3.5.8 命令

`EmissionSystem` 实现 `ICommandHandler`，处理 `SetEmissionPolicy`、`SectorEmissionOverride`（字段见 4.2）。

**`SetEmissionPolicy` 校验**（按顺序，第一个失败的返回）：

1. `UnitId` 不存在（四类我方存储中都 `TryGet` 失败）→ `UnknownEntity`。
2. 单位没有 `Emitter` → `WrongEntityKind`。
3. `PolicyId` 不是已知策略 → `InvalidArgument`。
4. `EmissionPolicyRules.CheckAvailable(unit.DefId, strategy, ctx.Level)`（3.5.2）失败 → 其返回值。
5. `DutyOnSec` / `DutyOffSec` 给出但 `≤ 0`、非有限值、或 `SecToTicksCeil` 结果 < 1 → `InvalidArgument`。
6. 单位是 `SensorUnit` 且 `BLineApplies` 且 `!BLine.RegionalRadarDirectControl` → `NotAvailable`。
7. `!CommandPointRules.CanSpend(ctx, CommandPointRules.CostOf(ctx.Level, cmd.Type))` → `NoCommandPoints`（A-2-17）。

**应用**：第一步调用 `CommandPointRules.Spend(ctx, CommandPointRules.CostOf(ctx.Level, cmd.Type), cmd.Type)`（A-2-17）；`PolicyId` 赋值；可空字段非 null 时覆盖对应 `Emitter` 字段；若新策略 `Activation == DutyCycle` → `DutyPhaseStartTick = ctx.Tick`；`TakeoverActive = false`（玩家重新接管）。开关机在本步 6 号系统中按新策略生效。

**`SectorEmissionOverride` 校验**（按顺序，第一个失败的返回）：

1. `RadiusM` 非有限值或 `≤ 0` → `InvalidArgument`。
2. `Center` 分量非有限值 → `InvalidArgument`。
3. `!CommandPointRules.CanSpend(ctx, CommandPointRules.CostOf(ctx.Level, cmd.Type))` → `NoCommandPoints`（A-2-17）。

扇区内没有任何辐射源也接受（无操作）。

**应用**：第一步调用 `CommandPointRules.Spend(ctx, CommandPointRules.CostOf(ctx.Level, cmd.Type), cmd.Type)`（A-2-17）；对全部存活辐射源（3.5.1 顺序），`WithinRange(Center, e.Pos, RadiusM)` → `Forced = Mode 对应值`（`Silence` / `ForceOn` / `Cancel → None`）。生效对象在命令应用时确定，单位之后移动出扇区仍保持。

### 3.6 `ExposureSystem`（Order 11，子流 `exposure`）

#### 3.6.1 每步流程

```
ProcessEvents()          # 游标 ExposureEventCursor：收集本步要处理的发射次数、转移完成
for each 我方单位 u（FireUnit → SensorUnit → EwUnit → DeceptionUnit，各自 ID 升序），Alive:
    if u 是 SensorUnit 且 u.Automatic: continue          # 自动单位不累积暴露度
    old = u.Exposure
    e = old
    if u 本步完成转移: e = Relocated(u, e, 事件)         # 3.6.3（含重算 HorizonProfile）
    emit  = EmitRate(u)                                  # 3.6.2，每秒
    recon = ReconNearby(u) ? Exposure.RatesPerSec.EnemyReconNearby : 0
    if "forward_ambush" ∈ CarryIn.Doctrines and u.Emitter != null and not u.Emitter.On and u.Emitter.OnSinceTick == -1:
        recon = 0                                        # 条令：前推伏击——首次开机前不累积侦察暴露（B-T2-126）
    n     = u 本步的导弹发射次数
    rate  = emit + recon
    if emit == 0 and recon == 0 and n == 0:
        delta = Exposure.RatesPerSec.Silent × StepSec
    else:
        delta = rate × StepSec + n × Exposure.PerMissileLaunched
        if CarryIn.AutoResolve != null: delta = delta × CarryIn.AutoResolve.ExposureGainMult   # 自动结算正增量乘子（A-2-22）
    e = Clamp(e + delta, Exposure.Min, Exposure.Max)
    u.Exposure = e
    u.ExposurePeak = max(u.ExposurePeak, e)
    Thresholds(u, old, e)                                # 3.6.4
FakeLauncherRecon()                                      # 3.7.3（唯一消耗 exposure 子流的地方）
```

当 `CarryIn.AutoResolve == null` 时，加法顺序固定为：`e + (rate × StepSec + n × PerMissileLaunched)`（与 `e + rate × StepSec + n × PerMissileLaunched` 在 `delta` 处计算后加到 `e`），最后夹取一次。

#### 3.6.2 辐射速率 `EmitRate(u)`

| 单位 | 条件 | 每秒速率 |
|---|---|---|
| `SensorUnit`（辐射源） | `Emitter.On` | `SensorExposureLevelRatesPerSec[Def.ExposureLevel]` |
| `FireUnit`（有火控） | `Emitter.On` | `FcMode == Cued` → `RatesPerSec.FireControlCued`；`SelfSearch` → `RatesPerSec.FireControlSelfSearch` |
| `EwUnit` | `Emitter.On` | `EwExposureLevelRatesPerSec[Def.EmissionExposure]` |
| `DeceptionUnit`（诱饵辐射源 / 牺牲雷达） | `Emitter.On` | `SensorExposureLevelRatesPerSec[Positions.Deception.DecoyEmitterExposureLevel]` |
| 任意单位（追加项） | `EquipmentEwIds` 中每个装备定义 `d`，且单位 `DeployState != Packed` | `+ EwExposureLevelRatesPerSec[d.EmissionExposure]`（防护罩常开，B-T2-52） |
| 其他 | | 0 |

策略的 `ExposureMult` 与 `cueing.*.exposureMult` **不在运行时相乘**（它们作为平衡验证的目标平均暴露系数，实测偏差容忍 ±0.15；已决 B-T3-10）。

#### 3.6.3 侦察、发射、转移

- `ReconNearby(u)`：通过 `ctx.ThreatGrid.QueryCircle(u.Pos, Exposure.EnemyReconRadiusM)` 检查存在存活的 `Threat t`，`t.Kind == Platform` 且其 `PlatformDef.Behavior ∈ { Spotter, ArmedRecon }`（B-T2-41），`WithinRange(u.Pos, t.Pos, Exposure.EnemyReconRadiusM)`。多架侦察机只计一次。
- 发射次数 `n`：本步处理的 `InterceptorLaunched { FireUnitId == u.Id }` 中，`WeaponDef.Kind == Missile` 的个数（`Rocket`、`InterceptorDrone`、`GunFired` 不计，B-T2-54）。
- 转移完成：`UnitDeployStateChanged { UnitId == u.Id, To == Deployed, CompletedRelocation == true }`：
  ```
  Relocated(u, e, ev):
      u.NewPositionPenalty = !(ev.DestinationAlternatePositionId != null 且 该备用阵地 Surveyed == true)
      if Sensing.HorizonProfiles.ContainsKey(u.Id):
          按 3.2.1 第 4 步在新位置 u.Pos 重新计算 Sensing.HorizonProfiles[u.Id]      # B-T2-31 / C-T2-01
      return ev.DestinationScouted ? e × OnRelocate.ToScoutedPositionMult : OnRelocate.ResetTo
  ```
- 本步事件只处理一次（游标）；一个单位一步内多次转移完成（不应发生）按事件顺序依次应用。

#### 3.6.4 阈值事件

`Thresholds`（已按 `AtLeast` 升序）：
- 上穿：`old < th.AtLeast ≤ e` 的每个 `th`，**按升序**发出 `ExposureThresholdCrossed { UnitId, Threshold = th.AtLeast, Consequence, Rising = true }`。
- 下穿：`e < th.AtLeast ≤ old` 的每个 `th`，**按降序**发出 `Rising = false`。
- 只比较本步开始与结束的值（转移归零造成的下穿也在此产生）。`Initialize` / `CarryIn` 带入的高暴露度**不**发事件（04 直接读 `Exposure`）。
- 阈值的后果（≥ 40 反辐射导弹优先、≥ 70 次夜已知目标清单、100 当夜改派 25% 未生成 `weighted_random` 打击或次夜标优先；已决 B-T3-05）由 04 / 01 消费；本文件只产生事件并维护 `ExposurePeak`（同时供 03 `NightResult.Exposure` 汇总读取，A-3-10）。

### 3.7 欺骗单位与阵地（WS01-016）

#### 3.7.1 诱饵辐射源、牺牲雷达

- 二者都是辐射源（2.1），按辐射策略开关机（缺省 `DefaultStrategyId`），开机时按 3.6.2 累积暴露度——高暴露度让它们成为反辐射导弹 / 侦察的优先目标（目标选择在 04 / 01）。
- 它们**不产生探测**（牺牲雷达不作为真实传感器，B-T2-42）。
- `DeceptionAttractScan()`（6 号系统）：对每个存活的 `Threat t`（ID 升序），`t.TargetUnitId` 指向存活的 `DeceptionUnit d` 且 `t.Id ∉ d.AttractedThreatIds` → 插入（保持升序），发出 `DeceptionTriggered { UnitId = d.Id, ThreatId = t.Id, Outcome = Attracted }`。假发射车同样适用。
- 被命中即销毁（一次性）由 03 的伤害规则处理；`Duration` 的跨夜含义由 05 处理。

#### 3.7.2 查询：当前可被反辐射导弹追踪的辐射源

```csharp
public static class EmitterQueries
{
    // 当前开机的辐射源（FireUnit → SensorUnit → EwUnit → DeceptionUnit，各自 ID 升序）
    public static IReadOnlyList<ActiveEmitter> ListActive(SimState s);
}
public readonly record struct ActiveEmitter(int UnitId, EntityKind EntityKind, Vec2 Pos, double Exposure, bool IsDecoy);
```

（字段名由 `Kind` 改为 `EntityKind`，以免与 `PlayerUnitCategory` 混淆；A-3-05。）
供 04 / 01 实现"只追踪开机雷达"与"诱饵吸引"。`IsDecoy` 对 04 的选择逻辑**不可见**（敌方不知道哪个是诱饵，见 B-T3-05）——仅用于复盘统计；04 必须只依据 `Pos`、`Exposure` 选择。

#### 3.7.3 假发射车 `FakeLauncherRecon()`

对每个存活的 `DeceptionUnit d`（ID 升序），`d.Def.Effect == FakeLauncher` 且 `d.Def.SeeThroughByReconQuality == true` 且 `!d.SeenThrough`：
通过 `ctx.ThreatGrid.QueryCircle(d.Pos, Exposure.EnemyReconRadiusM)` 遍历每个存活的侦察平台 `t`（3.6.3 的判定，ID 升序），`WithinRange(d.Pos, t.Pos, Exposure.EnemyReconRadiusM)` 且 `t.Id ∉ d.ReconCheckedThreatIds`：

```
插入 t.Id 到 ReconCheckedThreatIds（保持升序）
rq = t 的 PlatformDef.ReconQuality；rq == null → continue（不掷）
if rng.Chance(Positions.Deception.FakeLauncherSeeThroughChance[rq]):
    d.SeenThrough = true; emit DeceptionTriggered{ d.Id, t.Id, SeenThrough }; break
```

- 每架侦察机对每个假发射车最多掷一次；识破后不再掷。
- 未识破时，假发射车与真单位一样累积侦察暴露度（3.6.3），从而进入 04 的已知目标清单、吸引伊斯坎德尔 / Lancet（敌方绕行估计其威胁半径按 `fakeLauncherAssumedRangeKm = 10`，B-T3-05）；识破后 04 将其排除（`SeenThrough`）。

#### 3.7.4 备用阵地 / 新阵地

- `NewPositionPenalty` 的来源：开局 `Placement.FirstNightAtNewPosition`（05 在白天转移到未勘察阵地或中途增援放到未勘察阵地后置 true，A-2-13 / B-T2-06）；夜间转移完成时按 3.6.3 重算。
- 效果：本文件中——探测单位与火控雷达的有效距离（3.2.3、3.2.5）、电子战效能概率（3.4.3）乘 `NewUnsurveyed.FirstNightEfficiencyMult`；火力单元的拦截概率由 03 读取同一个 `unit.NewPositionPenalty` 字段并乘 `intercept.modifiers.newPositionFirstNight`（A-2-13、B-T2-06）。
- `preparedAlternate.deployTimeMult`（展开时间 −50%）由 04 的部署状态机使用。

### 3.8 覆盖预计算查询（`CoverageQuery`，只读供客户端，A-2-16 / C-T1-12）

供客户端部署阶段与夜间覆盖层（06 §3.9.6、§8.3 D-02-1）在后台或主线程计算单个单位的探测 / 火控 / 自主捕获覆盖与盲区网格；**不读 `SimState`、无副作用、线程安全**：

```csharp
namespace Nightwatch.Sim.Sensing;

public readonly record struct CoverageGridSpec(double MinX, double MaxY, double CellM, int Cols, int Rows);

public static class CoverageQuery
{
    // 返回 Rows × Cols（行主序，r = 0 对应北侧 MaxY）的 byte[]（三态，A-2-16 / 06 §3.9.6）：
    //   0 = 名义距离 R_nom 之外；
    //   1 = 名义距离 R_nom 之内，但在 targetAglM 高度不可探测（超出有效距离 R 或视线被地形遮挡 = 盲区）；
    //   2 = 可探测（在有效距离 R 内且视线无遮挡）。
    // 该单位无探测能力（如电子战单位、欺骗单位、覆盖型自动单位、无火控且无自主捕获的火力单元）返回 null。
    public static byte[]? ComputeGrid(
        LevelData level, TerrainModel terrain, int nightIndex, PlacedUnit unit,
        double targetAglM, CoverageGridSpec grid);
}
```

计算规则（与 3.2.3–3.2.5 完全同源，禁止另写一套公式，C-T1-12 / C-T2-01）：

1. 取 `night = level.Waves.Nights` 中 `Night == nightIndex` 的项（无则取 `Nights[0]`），`season = EnvironmentResolver.SeasonFor(night, level.Meta.DateRange.From)`。
2. 按 `unit.UnitDefId` 在 `level.Catalog` 中查找定义，确定名义探测距离 `R_nom`、在目标高度 `AltM = targetAglM` 下的有效探测距离 `R`、以及是否需要视线检查与對應的 `HorizonProfile`（预计算一次 720 方位桶径向最大遮挡斜率包络，耗时约 1.2 ms）：
   - **`SensorUnit`**（`DetectionRangeM != null`）：`R_nom = s.Def.DetectionRangeM`；按 3.2.3 计算 `AltM = targetAglM` 下的有效探测距离 `R`（其中 `Powered = true`、`NewPositionPenalty = unit.FirstNightAtNewPosition`、`NightAids = unit.Settings?.NightAids`）；若 `LineOfSight != false && Layer != National`，用 `profile = terrain.BuildHorizonProfile(unit.Pos, AntennaHeightM ?? Rules.Terrain.DefaultAntennaHeightM, R)` 检查视线，否则不需要视线检查（`profile = null`）。
   - **`FireUnit`**：
     - 若 `FireControlRadar != null`：`R_nom = FireControlRadar.RangeM`；按 3.2.5 火控雷达分支计算 `R`（`Powered = true`、`NewPositionPenalty = unit.FirstNightAtNewPosition`、含冬季与 `targetAglM` 低空倍率），并用 `profile = terrain.BuildHorizonProfile(unit.Pos, FireControlRadar.AntennaHeightM ?? Rules.Terrain.DefaultAntennaHeightM, R)` 检查视线；
     - 否则若 `SelfAcquisitionRangeM != null`：`R_nom = SelfAcquisitionRangeM`；按 3.2.5 自主捕获分支计算 `R`（含 `SelfAcquisition == Optical` 的昼夜与天气倍率），并用 `profile = terrain.BuildHorizonProfile(unit.Pos, Rules.Terrain.DefaultAntennaHeightM, R)` 检查视线。
   - 其他定义（含 `EwUnit`、`DeceptionUnit`、`DetectionRangeM == null` 的覆盖型单位、无火控且无自主捕获的 `FireUnit`）：返回 `null`（电子战圈与武器射程圈由 06 §3.8.7 `RangeRings` 直接按半径绘制）。
3. 对每个格子 `(r, c)`（`0 ≤ r < grid.Rows`、`0 ≤ c < grid.Cols`），格心 `p = (grid.MinX + (c + 0.5) * grid.CellM, grid.MaxY - (r + 0.5) * grid.CellM)`：
   - 若 `!WithinRange(unit.Pos, p, R_nom)` → `result[r * grid.Cols + c] = 0`（名义距离外）；
   - 否则若 `WithinRange(unit.Pos, p, R)` 且（`profile == null || profile.HasLineOfSightAgl(p, targetAglM)`）→ `result[r * grid.Cols + c] = 2`（可探测）；
   - 否则 → `result[r * grid.Cols + c] = 1`（名义距离内盲区）。

---

## 4. 事件与命令

### 4.1 本文件产生的事件（字段顺序 = 哈希顺序）

| 值 | 事件 | 字段 | 产生者 | 何时 |
|---|---|---|---|---|
| 200 | `EarlyWarning` | `string WaveId, string EntryId, double ExpectedAtSec, double BearingRad, bool Ballistic` | 3 | 3.2.8 |
| 201 | `TrackCreated` | `int TrackId, TrackQuality Quality` | 4 | 3.3.7 |
| 202 | `TrackQualityChanged` | `int TrackId, TrackQuality From, TrackQuality To` | 4 | 3.3.7（含外推时精确降为大致） |
| 203 | `TrackLost` | `int TrackId, TrackLostCause Cause`；`TrackLostCause { Timeout = 0, ThreatGone = 1 }` | 4 | 3.3.2、3.3.7 |
| 204 | `DecoyIdentified` | `int TrackId` | 4 | 3.3.8 |
| 205 | `EmitterSwitched` | `int UnitId, bool On, EmitterSwitchCause Cause`；`EmitterSwitchCause { Policy = 0, SectorSilence = 1, SectorForceOn = 2, ArmShutdown = 3, Takeover = 4, NotDeployed = 5, RadarDestroyed = 6, Suspended = 7 }`（A-2-12） | 6 | 3.5.1（`Initialize` 不发） |
| 206 | `ArmThreatDetected` | `int TrackId, int TargetUnitId` | 6 | 3.5.5 第 2 步，每条航迹一次 |
| 207 | `EwDiverted` | `int ThreatId, int SourceId, EwDivertKind Kind`；`EwDivertKind { NavJam = 0, NavSpoofPull = 1, NationalSpoof = 2 }`；`NationalSpoof` 时 `SourceId` 为 `SupportAsset` 的实体 ID，其余为 `EwUnit` 的实体 ID（A-3-07） | 5 | 3.4.4–3.4.6，只在成功时 |
| 208 | `EwLinkCut` | `int ThreatId, int SourceId, LinkCutOutcome Outcome, string DefId`；悬停超时坠毁时 `SourceId = 0, Outcome = Crash`（A-3-07、A-4-04） | 5 | 3.4.6，成功时及悬停超时移除前 |
| 209 | `ExposureThresholdCrossed` | `int UnitId, double Threshold, ExposureConsequence Consequence, bool Rising` | 11 | 3.6.4 |
| 210 | `DeceptionTriggered` | `int UnitId, int ThreatId, DeceptionOutcome Outcome`；`DeceptionOutcome { Attracted = 0, SeenThrough = 1 }` | 6（Attracted）、11（SeenThrough） | 3.7.1、3.7.3 |

同一系统一步内的事件顺序 = 伪代码中的执行顺序（实体按 ID 升序）。全部事件 `AtSec = null`（发生在步末时刻）。

### 4.2 本文件处理的命令

| 值 | 命令 | 字段 | 校验 / 应用 | 生效时刻 |
|---|---|---|---|---|
| 200 | `SetEmissionPolicy` | `int UnitId, string PolicyId, double? DutyOnSec, double? DutyOffSec, ArmResponse? OnArmIncoming, AfterFiringAction? AfterFiring, bool? NeighborTakeover` | 3.5.8 | `EffectiveTick` 的阶段 0；当步 6 号系统按新策略决定开关 |
| 201 | `SectorEmissionOverride` | `Vec2 Center, double RadiusM, SectorOverrideMode Mode`；`SectorOverrideMode { Silence = 0, ForceOn = 1, Cancel = 2 }` | 3.5.8 | 同上 |

拒绝原因使用 00 的公共原因：`UnknownEntity`、`WrongEntityKind`、`InvalidArgument`、`NotAvailable`、`NoCommandPoints`。两条命令在 `Validate` 最后一步检查 `CommandPointRules.CanSpend(ctx, CommandPointRules.CostOf(ctx.Level, cmd.Type))`，在 `Apply` 第一步调用 `CommandPointRules.Spend`（A-2-17）。

### 4.3 本文件消费的其他事件 / 字段

| 来源 | 事件 / 字段 | 用途 |
|---|---|---|
| 01 | `WaveStarted { WaveId }` | 注入波次的零提前量预警（3.2.8，在 `night.Waves` 中按 `Id` 查找，A-2-28） |
| 03 | `InterceptorLaunched { FireUnitId, WeaponId }`、`GunFired { FireUnitId }` | 开火后转移（3.5.6）、发射暴露（3.6.3） |
| 03 | `PlayerUnitDestroyed { UnitId, DefId, Category, SourceThreatId, Pos }` | 邻近雷达接替（3.5.6，A-2-05 / A-3-05） |
| 04 | `UnitDeployStateChanged { UnitId, From, To, CompletedRelocation, DestinationScouted, DestinationAlternatePositionId }` | 转移归零 / 减半、新阵地标记与重算地平线包络（3.6.3） |
| 03 | `Interceptor.FireUnitId`（字段） | "完成当前拦截后关机"、开火后转移 |
| 03 | `FireUnit.RadarDestroyed`、`PlayerUnitCommon.SuspendedUntilSec`（字段） | 雷达被毁与重伤暂停时停止探测 / 电子战并关机（3.2.3、3.2.5、3.4.1、3.5.3，A-2-12） |
| 03 | `SupportAsset.State`（`SupportAssetState.Active`）、`CenterPos`、`RadiusM`（字段） | 国家级导航欺骗（3.4.6，A-2-21） |
| 01 | `Threat.TargetUnitId`（字段，01 唯一写入，A-2-04） | 反辐射导弹来袭与归航目标维护、诱饵吸引 |

---

## 5. 边界情况

| # | 情况 | 处理 |
|---|---|---|
| 1 | 目标恰在探测距离上（`d == R`） | 探测到（`≤`）。电子战半径、侦察半径、扇区半径、参考距离同样含边界 |
| 2 | 目标高度恰等于 `LowAltitudeBelowM` | 不算低空（`AltM <` 才算） |
| 3 | 雷达本步刚关机 | 本步 3 号系统仍按上一步"开"产生探测；下一步起不再探测（3.1 时序）。但 10 号系统造成的 `RadarDestroyed` / `SuspendedUntilSec` 在下一步第 3、5 步直接拦截，无额外 1 步滞后（A-2-12） |
| 4 | 探测单位处于展开 / 撤收 / 移动中或重伤暂停中 | 不探测；辐射源强制关机（`NotDeployed` / `Suspended`）；暴露度照常结算（静默衰减、侦察、转移） |
| 5 | 延迟探测送达时来源单位已被摧毁 | 照常送达 |
| 6 | 延迟探测送达时目标已被移除 | 在融合第 2 步丢弃，不创建航迹 |
| 7 | 目标被拦截 / 落地 / 离开 / 坠毁 | 下一步融合第 1 步删除航迹（`ThreatGone`）。同一步内 03 仍可能看到该航迹，须用 `TryGet(ThreatId)` 判断 |
| 8 | 误报航迹（`ThreatId == 0`） | 质量恒为来源单位的输出质量（实际数据中为模糊），不交叉升级、不甄别、按超时丢失；03 必须把 `ThreatId == 0` 的航迹视为"无可拦截目标"（不得发射；B-T2-46） |
| 9 | 同一目标同时被火控雷达和网络看到 | `Quality = Precise`，`NetworkQuality` = 网络部分；位置取火控探测 |
| 10 | 航迹外推期间目标又被探测到 | 正常 Update；外推期间降级的"精确"在重新锁定时恢复 |
| 11 | 诱饵航迹被甄别后丢失、再次出现 | 新航迹重新从未甄别开始 |
| 12 | 诱饵航迹从"精确"降为"大致"再升回"精确" | 不重掷（`DecoyCheckedQuality` 只增不减） |
| 13 | 目标同时位于多个干扰站覆盖内 | 每类效果只掷一次，取概率最大的单位（并列取 ID 最小） |
| 14 | 目标导航干扰判定失败后飞入另一个干扰站 | 不再掷（`Resisted` 锁存，D4） |
| 15 | AI 视觉目标只被区域导航干扰站覆盖（末段无效时期） | 概率 0，不掷，状态保持 `None`；之后被导航欺骗站覆盖时仍可判定 |
| 16 | 导航欺骗站未设诱导点 | 只有落点偏移，无诱导 |
| 17 | `EwImmune` 目标误列在 `EffectiveAgainst` 中 | 免疫优先，不掷 |
| 18 | 链路中断结果为坠落，或悬停超时坠落 | 同一步内发出 `EwLinkCut { ..., Outcome = Crash, DefId }`（悬停超时 `SourceId = 0`）并移除目标；本步后续系统 `TryGet` 失败；不造成地面伤害（A-4-04、B-T3-08） |
| 19 | 悬停目标被拦截 | 由 03 正常结算；悬停计时随之失效 |
| 20 | 电子战单位本步关机 | 本步 5 号系统仍按上一步"开"生效（时序） |
| 21 | `SetEmissionPolicy` 指向已被摧毁的单位 | `UnknownEntity` |
| 22 | `SetEmissionPolicy` 指向非辐射源（声学哨、单兵导弹、假发射车） | `WrongEntityKind` |
| 23 | 静默待机设给苏制火控 / 第 5 关 | `NotAvailable`（3.5.2）；部署方案中出现时由 04 的校验报错 |
| 24 | 静默待机但没有网络"大致"航迹 | 雷达一直关机；单位无法获得精确航迹，不能发射导弹 |
| 25 | 扇区强制开机覆盖了"反辐射来袭立即关机" | 强制开机优先（玩家明确命令，3.5.3 第 3 行先于第 4 行）；但 `NotDeployed`、`RadarDestroyed`、`Suspended` 仍高于强制开机 |
| 26 | 扇区命令之后单位移出扇区 | 保持强制状态，直到 `Cancel` 或新的扇区命令覆盖 |
| 27 | 反辐射导弹没有 `TargetUnitId`，或目标不是辐射源 | 不触发来袭处置；不设初始距离；`HomingUnitId = 0` |
| 28 | 反辐射导弹在雷达关机后、雷达重新开机 | `ArmHitProbMult` 清空（3.5.5 第 5 步），`HomingUnitId` 在下一步恢复为目标单位 ID，下次关机重新计算 |
| 29 | 反辐射导弹距离比 `f` 恰等于 0.5 / 0.25 | 不满足"> 0.5"，取下一档（0.25 档 → 0.5；0 档 → 0.8） |
| 30 | `f == 0`（导弹已在雷达正上方） | 三档都不满足，倍率 1.0 |
| 31 | 主雷达被毁时邻近单位处于强制静默 | `TakeoverActive` 置 true，但强制静默优先（第 2 行），保持关机 |
| 32 | 开火后转移但没有备用阵地 | 不设 `PendingRelocationAltId`，`FiredSinceRelocation` 保持 true |
| 33 | 暴露度已为 0 时静默 | 夹取在 `Min`，不产生下穿事件 |
| 34 | 一步内跨越多个阈值 | 上穿按升序、下穿按降序逐个发事件 |
| 35 | 自动探测单位（国家预警、民众上报） | 不累积暴露度、不是辐射源、不接受命令（`WrongEntityKind`） |
| 36 | 关卡没有城区 | 民众上报永远探测不到；其误报 `Chance` 仍消耗但不产生航迹 |
| 37 | 波次 `atSec − warningSec ≤ 0` | 第 1 步发出预警 |
| 38 | 两个波次同一步预警 | 按波次数据顺序 |
| 39 | 同一辐射源一步内多个原因 | 只按 3.5.3 第一个命中的原因发一个事件；状态未变不发事件 |
| 40 | 假发射车被识破后仍有侦察机经过 | 不再掷；暴露度照常累积（04 依据 `SeenThrough` 排除） |
| 41 | 目标在本步第 2 步已到达（`Phase == Arrived`） | 第 5 步电子战直接跳过，不在落地结算前改写或坠毁该目标（A-4-06） |
| 42 | 同一目标同时使单位电子战与国家级导航欺骗 `Applied` | `ReconcileNavAccuracy` 比较期望偏移增量，取较大者，不叠加（B-T3-08） |

---

## 6. 不变量

`SimConfig.CheckInvariants = true` 时每步末尾检查（追加到 00 的 6.1）：

1. 对所有我方单位：`Min ≤ Exposure ≤ Max`；`ExposurePeak ≥ Exposure`；`ExposurePeak ≤ Max`。
2. 辐射源的 `Emitter.On == true` ⇒ `DeployState == Deployed && !Suspended(u) && !(u is FireUnit f && f.RadarDestroyed)`。
3. `Emitter.On == true` ⇔ `Emitter.OnSinceTick ≥ 0`；`OnSinceTick ≤ Tick`。
4. `FcMode != Off` ⇔（实体是 `FireUnit` 且 `Emitter.On`）。
5. 每个存活 `Track`：`(ThreatId == 0) != (PhantomKey == 0)`；`ThreatId != 0` ⇒ 不存在另一条存活航迹具有相同 `ThreatId`；`PhantomKey` 同理。
6. 每个存活 `Track`：`Quality == Precise` ⇔ `PreciseHolderIds.Count > 0`；`PreciseHolderIds` 严格升序；`NetworkQuality == null || NetworkQuality ≤ Quality`；`NetworkQuality != Precise`。
7. `DecoyIdentified` ⇒ `DecoyCheckedQuality != null`；`Tag != null` ⇒ `Quality ≥ Approximate`。
8. `ErrorRadiusM ≥ 0`；`LastDetectedTick ≤ Tick`；`(Tick − LastDetectedTick) × StepSec ≤ TrackLostSec`。
9. `Sensing.Delayed` 按 `(DeliverTick, Seq)` 严格升序且全部 `DeliverTick > Tick`（已到期的已送达）。
10. `Threat.EwPull == Applied` ⇒ `EwNav == Applied` 且 `EwDivertPos != null`；`EwDivertPos != null` ⇒ `EwPull == Applied`。
11. `Threat.AccuracyTierDrop ≥ 0`；`EwExtraOffsetM ≥ 0`；`!(Threat.AccuracyTierDrop > 0 && Threat.EwExtraOffsetM > 0)`（国家级降档与单位电子战额外偏移不叠加，B-T3-08）；`ArmHitProbMult == null || ArmHitProbMult ≥ 0`。
12. `DeceptionUnit.ReconCheckedThreatIds`、`AttractedThreatIds` 严格升序。
13. `Ew.UrbanNavJamSec` 非递减、`≤ Tick × StepSec`。
14. `Sensing.WarnedKeys` 中的键数 ≤ 预警时间表条目数 + 注入波次键数。

---

## 7. 测试用例

> 全部数值由 `tools/spec_calc/02/calc_02.py` 计算核对（C-T1-01）。浮点比较：标"精确"的用 `==`；其余容差 `1e-9`。

### 7.0 夹具与测试替身

**关卡 `mini02`**（`MiniLevelBuilder`）：
- 地图 `20000 × 20000` m；高程图 2×2 像素全 0，`metersPerPixel = 10000`，`minElevationM = 0`，`maxElevationM = 1`（平地，视线恒通）。
- `level.json`：`protagonist = A`，`number = null`，`dateRange.from = 2022-11-15`，部署区覆盖全图，无禁区；`alternatePositions = [{ id: alt_s, positionM: [5000, 5000], surveyed: true }, { id: alt_u, positionM: [6000, 6000], surveyed: false }]`。
- `layers.json`：`urban = [{ id: u1, polygonM: [[8000,8000],[12000,8000],[12000,12000],[8000,12000]], density: dense }]`，其余图层为空。
- `waves.json`：无进入点、一个夜晚 `durationGameSec = 10`，`weather = clear`，`timeOfDay = night`，`season = autumn`，无波次（T-02-12 另给）。
- `SimConfig.DurationTicksOverride = 120`，`EndWhenClear = false`，seed = 1。
- 部署方案中单位按列出顺序创建，ID 从 1 开始（无电网节点、无保护目标）；**基础目录不含自动探测单位**（需要时测试会声明"目录加入 `s_civ` / `s_nat`"，它们在部署单位之后获得 ID）。

**`conventions`**：`gameSecToWorldSec 60, worldStepSec 1, cellKm 1, machKmh 1200`。

**探测单位**（省略的必填字段取任意合法值：`deployGameSec 1, packGameSec 1, priceMusd 1`）：

```json
[
 {"id":"r_reg","nameKey":"t.a","layer":"regional","detectionRangeKm":10,"lowAltitude":"medium","trackQuality":"approximate","emission":"active","exposureLevel":"high"},
 {"id":"r_fast","nameKey":"t.a","layer":"regional","detectionRangeKm":10,"lowAltitude":"medium","trackQuality":"approximate","fastUpdate":true,"emission":"active","exposureLevel":"medium"},
 {"id":"r_blind","nameKey":"t.a","layer":"regional","detectionRangeKm":10,"lowAltitude":"poor","largeLowAltitudeBlindZone":true,"trackQuality":"approximate","emission":"active","exposureLevel":"high"},
 {"id":"s_ac","nameKey":"t.a","layer":"local","detectionRangeKm":2,"lowAltitude":"very_good","trackQuality":"vague","emission":"passive","exposureLevel":"zero","lineOfSight":false},
 {"id":"s_ac_fa","nameKey":"t.a","layer":"local","detectionRangeKm":2,"lowAltitude":"very_good","trackQuality":"vague","falseAlarms":"some","emission":"passive","exposureLevel":"zero","lineOfSight":false},
 {"id":"s_obs","nameKey":"t.a","layer":"local","detectionRangeKm":4,"nightRangeMult":0.5,"nightPenaltyNegatedBy":["thermal"],"lowAltitude":"very_good","trackQuality":"vague","trackQualityUpgrades":[{"to":"approximate","condition":"close_range"}],"emission":"passive","exposureLevel":"zero"},
 {"id":"s_radio","nameKey":"t.a","layer":"local","detectionRangeKm":5,"lowAltitude":"good","onlyDetects":"radio_linked_drones","trackQuality":"vague","trackQualityUpgrades":[{"to":"approximate","condition":"linked_drone_types","enemies":["m_fpv"]}],"emission":"passive","exposureLevel":"zero"},
 {"id":"s_civ","nameKey":"t.a","layer":"local","detectionRangeKm":null,"coverage":"urban_areas","lowAltitude":"good","trackQuality":"vague","reportDelay":true,"emission":"passive","exposureLevel":"zero","deployGameSec":null,"packGameSec":null,"automatic":true,"firstAvailable":{"level":3}},
 {"id":"s_nat","nameKey":"t.a","layer":"national","detectionRangeKm":null,"coverage":"full_map","lowAltitude":"poor","trackQuality":"vague","emission":"none","exposureLevel":"none","deployGameSec":null,"packGameSec":null,"automatic":true,"firstAvailable":{"level":1}}
]
```

**防空单位**（省略字段任意合法；`interceptClass: "k"`，`rules/intercept.json` 与 `rules/engagement.json` 夹具含类别 `k` 缺省反应 `0.1` 游戏秒 = 6 s，且武器可逐个覆盖 `reactionGameSec`；B-T2-01 / P15）：

| ID | 火控 / 自主捕获 | 武器（含反应时间） |
|---|---|---|
| `f_sam` | `fireControlRadar: { rangeKm: 8, lowAltitude: "good", origin: "western" }` | `w_sam`：`kind missile, rangeKm 6, ceilingKm 5, reactionGameSec 0.1（6 s）, targets [UAV, CM, SCM]` |
| `f_sov` | `fireControlRadar: { rangeKm: 8, lowAltitude: "good", origin: "soviet" }` | `w_sov`：同 `w_sam` |
| `f_gun` | `selfAcquisitionRangeKm: 2, selfAcquisition: "passive"`，无火控 | `w_gun`：`kind gun, rangeKm 2, ceilingKm 2, reactionGameSec 0.05（3 s）, targets [UAV, DECOY]` |
| `f_opt` | `selfAcquisitionRangeKm: 2, selfAcquisition: "optical"`，无火控 | `w_gun`：同 `f_gun` |

`fireOnMove` 均为 `no`。

**敌方**（省略字段任意合法；高度由测试直接给 `AltM`）：

| ID | 类型 | 标签 | 本文件相关字段 |
|---|---|---|---|
| `m_uav` | 弹药 | UAV | `accuracy C` |
| `m_fpv` | 弹药 | UAV | `accuracy A, radioLinked true` |
| `m_decoy` | 弹药 | DECOY | `accuracy D` |
| `m_cm` | 弹药 | CM | `accuracy C` |
| `m_fiber` | 弹药 | UAV | `accuracy A, ewImmune true` |
| `m_arm` | 弹药 | SCM | `accuracy A, tracksEmittingRadarOnly true` |
| `m_bm` | 弹药 | BM | `accuracy A` |
| `m_ai` | 弹药 | UAV | `accuracy B, aiVisionFrom "2025-03"` |
| `p_recon` | 平台 | UAV | `behavior spotter, reconQuality medium, radioLinked true` |
| `p_recon_nq` | 平台 | UAV | `behavior spotter`（无 `reconQuality`） |

**电子战单位**（省略字段任意合法）：

| ID | effect | radiusKm | 其他 | effectiveAgainst |
|---|---|---|---|---|
| `ew_jam` | nav_jam | 5 | `emissionExposure high` | `m_cm, m_uav, m_fiber, m_ai` |
| `ew_spoof` | nav_spoof | 5 | `pullChance 0.3, aiVisionEffectMult 0.5` | `m_cm, m_uav, m_ai` |
| `ew_cuas` | link_cut | 2 | `linkCutOutcomes [crash, hover, return]` | `m_fpv, p_recon` |
| `ew_weak` | nav_jam | 5 | `firstAvailable { level 3, fullStrengthLevel 6 }` | `m_cm` |
| `ew_shield` | self_protection | 0.3 | `hitProbMult 0.5, equipmentSlot true, emissionExposure low` | `m_fpv` |

**欺骗单位**：`d_decoy`（`fake_emitter`，`duration one_shot`）；`d_fake`（`fake_launcher`，`seeThroughByReconQuality true`，`duration nights`，`durationNights 2`）。

**规则夹具**（与正式数值不同）：

```json
// terrain.json：含 "defaultAntennaHeightM":10,"earthRadiusM":6371000,"refractionK":1.3333333333333333,"losSampleStepPx":0.5,"horizonAzimuthBins":720,"horizonRangeStepM":50
// tracks.json
{"kind":"tracks",
 "qualities":[{"id":"vague","decoyDiscrimination":0,"missilesAllowed":false,"display":"area_and_arrow","actions":[]},
              {"id":"approximate","decoyDiscrimination":0.5,"missilesAllowed":false,"display":"icon_and_error_circle","actions":[]},
              {"id":"precise","decoyDiscrimination":0.8,"missilesAllowed":true,"display":"precise_icon","actions":[]}],
 "approximateFromLocalSensorCount":2,
 "cueing":{"cued":{"minTrackQuality":"approximate","fireControlOnlyLastReactionTime":true,"exposureMult":0.3},
           "uncued":{"exposureMult":1.0,"firstShotReactionTimeMult":1.5}},
 "warningRadarEnemyAiWeightAs":"medium_sam",
 "bLine":{"regionalRadarDirectControl":false,"relayDelayGameSec":0.05,"maxTrackQuality":"approximate"},
 "detectionRules":{"lowAltitudeBelowM":100,"lowAltitudeRangeMult":{"poor":0.25,"medium":0.5,"good":0.75,"very_good":1.0},
   "largeBlindZoneLowAltitudeRangeMult":0.5,"coverageLowAltitudeMinCapability":"good",
   "closeRangeFraction":0.5,"errorRadiusM":{"vague":2000,"approximate":500,"precise":0},"fastUpdateErrorRadiusMult":0.5,
   "trackLostGameSec":0.05,"falseAlarmsPerGameSec":{"some":0.6,"high":6},"reportDelayGameSec":0.1,
   "opticalWeatherRangeMult":{"clear":1.0,"moonlit":1.5,"low_cloud":0.5,"fog":0.25},"opticalNightRangeMult":0.3,
   "unpoweredActiveRangeMult":0.5,"winterActiveRangeMult":0.9}}
// emission.json：strategies 与正式数据相同（5 条），triggers 与正式数据相同，shutdownTiming 与正式数据相同（0.5→0.2，0.25→0.5，0→0.8），
//   另加 "defaultStrategy":"always_on","dutyCycleDefaultOnGameSec":0.05,"dutyCycleDefaultOffGameSec":0.05,"decoyLeadGameSec":0.05,"defaultReferenceRangeKm":10
// exposure.json
{"kind":"exposure","min":0,"max":100,
 "ratesPerGameSec":{"fireControlSelfSearch":120,"fireControlCued":36,"silent":-30,"enemyReconNearby":30},
 "perMissileLaunched":5,"enemyReconRadiusKm":5,"onRelocate":{"resetTo":0,"toScoutedPositionMult":0.5},
 "sensorExposureLevelRates":{"high":60,"medium":36,"zero":0,"none":0},"ewExposureLevelRates":{"high":60,"medium":36,"low":18},
 "thresholds":[{"atLeast":70,"consequence":"known_target_list_next_night"},{"atLeast":40,"consequence":"anti_radiation_priority_tonight"},{"atLeast":100,"consequence":"precision_strike_tonight"}]}
// ew.json
{"kind":"ew",
 "effectivenessByPeriod":[{"from":"2022-02","nav":0.5,"counterUas":0.8},{"from":"2025-03","nav":0.5,"counterUas":0.8,"navTerminalIneffectiveVsAiVision":true}],
 "sideEffects":{"ownDroneLinkCut":true,"urbanNavJamCityResiliencePerNight":-1},
 "linkCutOutcomeWeights":{"crash":1,"hover":1,"return":2},"hoverBeforeCrashGameSec":0.05,"belowFullStrengthMult":0.5,
 "unpoweredEffectMult":0.5,"winterEffectMult":0.9,"urbanNavJamMinGameSec":1}
// positions.json：preparedAlternate 同正式数据；"newUnsurveyed":{"firstNightEfficiencyMult":0.7}；
//   "deception":{"fakeLauncherSeeThroughChance":{"low":0.1,"medium":0.3,"high":0.6},"decoyEmitterExposureLevel":"high"}
// accuracy.json：tiers 的 ewExtraCells：A 0.5，B 1，C 1.5，D 2（offsetCells：A 0..0，B 0..1，C 1..2，D 2..4）
// support.json：含 {"id":"s_nspoof","effect":"accuracy_drop","accuracyTierDrop":2,"affectsSameAsEwUnit":"ew_jam","radiusKm":10,…}
```

注意 `thresholds` 故意乱序，用于验证加载后按 `AtLeast` 升序排列。换算后：`RelayDelaySec = 3`，`TrackLostSec = 3`，`ReportDelaySec = 6`，`FalseAlarmsPerSec = { Some: 0.01, High: 0.1 }`，`DutyCycleDefault* = 3`，`DecoyLeadSec = 3`，`HoverBeforeCrashSec = 3`，`UrbanNavJamMinSec = 60`；暴露速率（每秒）：高 1.0、中 0.6、低 0.3、自行搜索 2.0、指示 0.6、静默 −0.5、侦察 0.5。

**测试替身**（`sim.tests/TestKit`，用 `SimWorld.CreateForTest` 替换）：
- `ScriptedThreats`（替换 Order 1）：按脚本在指定步创建目标（`DefId`、`Kind`、`Pos`、`AltM`、`VelMps`、`Tag` 来自定义、`TargetUnitId`），或移除指定目标，或执行任意状态修改（设置 `DeployState`、`Powered`、`RadarDestroyed`、`SuspendedUntilSec`，创建 / 移除 `Interceptor`、`SupportAsset`）。创建当步的 `Pos` 即脚本给定值。
- `LinearMover`（替换 Order 2）：对 `CreatedTick < Tick` 的目标执行 `Pos += VelMps × StepSec`（记录 `ThreatRouting.Retarget / Hover / BeginEgress` 调用供断言，悬停测试中速度置为 0）。
- `ScriptedEvents`（替换 Order 7）：在指定步发出给定事件（`InterceptorLaunched`、`GunFired`、`UnitDeployStateChanged`、`PlayerUnitDestroyed`），并可同时移除我方单位。
- Order 8、9、10、12、13 替换为空系统。
- 随机：`RandomOverride` 对测试指定的子流返回 `ScriptedRandom`（按序返回给定的 `NextDouble` 值，耗尽即抛异常——用于证明"没有多余消耗"），其他子流返回正常 `SimRandom`。
- 记号："t 在第 k 步"指脚本在第 k 步创建；"第 k 步事件"指 `Tick == k` 的事件；状态断言均为该步 `Step()` 返回后的值。

### 7.1 探测（WS01-007）

**T-02-01 探测距离边界**
部署 `r_reg@(5000,5000)`（缺省策略 `always_on`）。`m_uav` 目标 `AltM 500`，第 1 步创建于 `(15000,5000)`（距离恰 10000）。
ID：`r_reg = 1`，目标 = 2，航迹 = 3。预期第 1 步：事件 `TrackCreated{3, Approximate}`；航迹 `ThreatId == 2`，航迹 `Pos == (15000,5000)`，`Tag == UAV`，`ErrorRadiusM == 500`，`NetworkQuality == Approximate`，`LocalSensorCount == 0`，`PreciseHolderIds` 为空。
另一世界目标在 `(15000.001,5000)`：120 步内无航迹、无 `TrackCreated`。

**T-02-02 低空能力**
`r_reg@(5000,5000)`（`medium` → 低空倍率 0.5，有效 5000）。
- `AltM 50` 于 `(10000,5000)` → 有航迹；于 `(10000.001,5000)` → 无。
- `AltM 100`（恰等于阈值，不算低空）于 `(14000,5000)` → 有航迹。

**T-02-03 低空盲区大**
`r_blind@(5000,5000)`：低空有效距离 `10000 × 0.25 × 0.5 = 1250`。`AltM 50` 于 `(6250,5000)` → 有；`(6251,5000)` → 无。`AltM 500` 于 `(15000,5000)` → 有。

**T-02-04 地形遮挡（径向地平线包络）**
另建地图 `3000 × 3000`，高程图 3×3、`metersPerPixel 1000`、`min 0 / max 1000`，三行像素均为 `[0, 65535, 0]`（中间一列为 1000 m 高的山脊）。部署 `r_reg@(500,1500)`（展开时调用 `TerrainModel.BuildHorizonProfile`，`defaultAntennaHeightM = 10`）、`s_ac@(1000,1500)`。
- 目标 `AltM 50` 于 `(2500,1500)`：`r_reg` 的 `HorizonProfile.HasLineOfSightAgl` 返回 `false`（山脊处斜率 `s_ridge ≈ 0.990 > s_target ≈ 0.020`，视线被挡）；`s_ac`（`lineOfSight: false`，距离 1500）探测到 → 航迹 `Quality == Vague`，`LocalSensorCount == 1`。
- 目标 `AltM 3000` 于同一点、不部署 `s_ac`：`r_reg` 探测到（`s_target ≈ 1.495 ≥ s_ridge`）→ `Quality == Approximate`。

**T-02-04b 径向最大遮挡斜率包络 vs 逐段采样参考函数（B-T2-31 / C-T2-01）**
在含两道山脊（`r = 2500 m` 高 220 m、`r = 5500 m` 高 380 m）的测试高度场上，传感器位于 `(5000,5000)`、`antennaHeightM = 10`：
- 山前谷底低空目标（`r = 4000 m, AltM = 50`）：第一道山脊遮挡，`HorizonProfile.HasLineOfSightAgl == false`，与 `TerrainModel.HasLineOfSightReference` 一致；同一距离 `AltM = 600` 高空目标越过第一道山脊但未到第二道山脊，`HasLineOfSightAgl == true`（若只存整条射线终点的单一仰角则会误判为被第二道山脊遮挡）。
- 固定随机种子生成 2000 个 `(targetPos, targetAltM)` 点对，`HorizonProfile.HasLineOfSightAgl` 与 `TerrainModel.HasLineOfSightReference` 的不一致率 `< 1%`。
- 当传感器完成转移发出 `UnitDeployStateChanged { To = Deployed, CompletedRelocation = true }` 时，`Horizon` 按新位置重算。

**T-02-05 夜间、白天与天气（光学，C-T2-07）**
部署 `s_obs@(5000,5000)`，目标 `AltM 500`。

| 情形 | `night.TimeOfDay` | `night.Weather` | `NightAids` | 有效距离 | 探测到 | 探测不到 |
|---|---|---|---|---|---|---|
| a | `Night` | `moonlit` | — | 3000 | `(8000,5000)` | `(8000.001,5000)` |
| b | `Night` | `moonlit` | `[thermal]` | 6000 | `(11000,5000)` | `(11000.001,5000)` |
| c | `Night` | `fog` | — | 500 | `(5500,5000)` | `(5500.001,5000)` |
| d | `Night` | `null` | — | 2000 | `(7000,5000)` | `(7000.001,5000)` |
| e | `Night` | `moonlit` | `[searchlight]`（不在可抵消列表中） | 3000 | `(8000,5000)` | `(8000.001,5000)` |
| f | `Day` | `clear` | — | 4000（白天不乘 `nightRangeMult`） | `(9000,5000)` | `(9000.001,5000)` |

`r_reg` 在情形 c 中有效距离仍为 10000（非光学不受天气影响）。

**T-02-06 无线电侦测器**
`s_radio@(5000,5000)`，目标都在 `(6000,5000)`、`AltM 50`：`m_uav` → 无航迹；`m_fpv` → `Quality == Approximate`（链路型号升级）；`p_recon` → `Quality == Vague`。

**T-02-07 近距离升级**
`s_obs@(5000,5000)`，`weather clear`（有效 2000，近距离 1000）：目标于 `(6000,5000)` → `Approximate`；于 `(6500,5000)` → `Vague`。

**T-02-08 覆盖型自动单位**
目录加入 `s_civ`、`s_nat`（自动创建，ID 1、2，`Automatic == true`，`Pos == (10000,10000)`），无部署。
- 目标 A：`AltM 50` 于 `(100000,100000)` → 无航迹（国家层 `poor` < `good`，不在城区）。
- 目标 B：`AltM 500` 于 `(100000,100000)`（地图外）→ 第 1 步 `Vague` 航迹。
- 目标 C：`AltM 50` 于 `(10000,10000)`（城区内）→ 第 1–6 步无航迹，第 7 步 `TrackCreated{…, Vague}`（民众上报延迟 6 s）。

**T-02-09 民众上报延迟与陈旧位置**
目录加入 `s_civ`。`m_uav`，`AltM 500`，第 1 步于 `(9000,10000)`，`VelMps (10,0)`。
- 第 1–6 步：无航迹。
- 第 7 步：航迹 `Pos == (9000,10000)`，`LastObservedAtSec == 1.0`，`VelMps == (10,0)`，`Quality == Vague`，`ErrorRadiusM == 2000`。
- 第 8 步：`Pos == (9010,10000)`，`LastObservedAtSec == 2.0`。
- 第 k 步末 `Sensing.Delayed.Count == min(k, 6)`（每步进 1 条；第 7 步起每步同时送达 1 条）。

**T-02-10 误报**
`s_ac_fa@(5000,5000)`；`sensor` 子流脚本 `[0.005, 0.25, 0.25, 0.5, 0.5, 0.5, 0.5]`，运行 5 步。
- 第 1 步：`0.005 < 0.01` → 误报于 `(6000.0, 5000.0)`（容差 1e-9）；`TrackCreated{…, Vague}`；航迹 `ThreatId == 0`、`PhantomKey == 1`、`Tag == null`、`VelMps == (0,0)`。
- 第 2–4 步：航迹仍在（外推不动）。
- 第 5 步：`TrackLost{…, Timeout}`（`5 − 1 = 4 > 3`）。
- 恰好消耗 7 个值（第 6 步若继续运行则抛"脚本耗尽"）。

**T-02-11 B 线空情转发**
`level.protagonist = B`。部署 `r_reg@(5000,5000)`、`s_ac@(5500,5000)`；目标 `AltM 500` 静止于 `(6000,5000)`。
- 第 1 步：航迹 `Vague`（只有 `s_ac`），`LocalSensorCount == 1`。
- 第 2、3 步：仍 `Vague`。
- 第 4 步：`TrackQualityChanged{…, Vague, Approximate}`（`r_reg` 第 1 步的探测延迟 3 s 送达），选中探测按质量优先为 `r_reg` 第 1 步的探测 → `LastObservedAtSec == 1.0`，`Pos == (6000,5000)`，`LocalSensorCount == 1`。此后每步送达一条 `r_reg` 探测（第 k 步送达第 k − 3 步的观测）。
- 同一场景 `protagonist = A`：第 1 步即 `Approximate`。

**T-02-12 国家预警**
`waves.json`：`entryPoints = [ e1@(30000,10000) warningGameSec 0.5, e2@(10000,30000) warningGameSec 2, e3@(-5000,10000) 无 warningGameSec ]`；第 1 夜 `waves = [ w1 atGameSec 1：groups [m_uav from e1, m_bm from e2, m_uav from e3]；w2 atGameSec 2：groups [m_uav from e1, m_uav from e1] ]`（Order 1 为不生成任何目标的空替身，`WaveSpawnRules.IsStoryOnlyWave` 对 `w1, w2` 返回 `false`）。运行 120 步，`EarlyWarning` 事件恰为：

| Tick | WaveId | EntryId | ExpectedAtSec | BearingRad | Ballistic |
|---|---|---|---|---|---|
| 1 | w1 | e2 | 60.0 | 0.0 | true |
| 30 | w1 | e1 | 60.0 | 1.5707963267948966 | false |
| 90 | w2 | e1 | 120.0 | 1.5707963267948966 | false |

无航迹产生。若另一波次 `w_story` 被 `WaveSpawnRules.IsStoryOnlyWave` 标为 `true`，则初始化时不排入时间表，仅在收到 `WaveStarted { WaveId = "w_story" }` 的下一步由 3.2.8 发出 `EarlyWarning`（A-2-28）。

**T-02-13 断电、新阵地与冬季（B-T2-05、B-T2-06、C-T2-07）**
- `r_reg@(5000,5000)`，脚本在第 1 步开头设 `Powered = false`：目标 `AltM 500` 于 `(10000,5000)` → 有航迹；`(10000.001,5000)` → 无。
- `r_reg` 的 `PlacedUnit.FirstNightAtNewPosition = true`（`Powered = true`）：于 `(12000,5000)` → 有；`(12000.001,5000)` → 无。
- `r_reg` 在 `night.Season = Winter`（`Powered = true`，非新阵地）：有效距离 `10000 × 0.9 = 9000` m，于 `(14000,5000)` → 有；`(14000.001,5000)` → 无。

**T-02-14 火控雷达、自主捕获与部件损毁 / 暂停（B-T2-09、A-2-12、C-T2-07）**
- `f_sam@(5000,5000)`（`always_on`）；目标 `AltM 500` 于 `(13000,5000)`：第 1 步航迹 `Quality == Precise`、`PreciseHolderIds == [1]`、`NetworkQuality == null`、`ErrorRadiusM == 0`。
- 同上，目标 `AltM 50`：于 `(11000,5000)`（低空倍率 0.75 → 6000）→ 有；`(11000.001,5000)` → 无。
- 同上，脚本在第 1 步开头设 `f_sam.RadarDestroyed = true`（或设 `f_sam.SuspendedUntilSec = 10`）：第 1 步无探测、无航迹（A-2-12）。
- `f_gun@(5000,5000)`（`selfAcquisition: "passive"`）：目标 `AltM 50` 于 `(7000,5000)` → `Precise`、`PreciseHolderIds == [1]`；`f_gun.Emitter == null`；于 `(7000.001,5000)` → 无航迹。
- `f_opt@(5000,5000)`（`selfAcquisition: "optical"`，B-T2-09）：
  - 夜间（`TimeOfDay = Night, Weather = clear`，无 `NightAids`）：有效距离 `2000 × 0.3 = 600` m，目标于 `(5600,5000)` → `Precise`；`(5600.001,5000)` → 无航迹。
  - 夜间配 `NightAids = [Searchlight]`（或 `TimeOfDay = Day`）：不乘 `0.3`，有效距离 `2000` m，于 `(7000,5000)` → `Precise`。

**T-02-15 自动单位的关卡闸门**
目录加入 `s_civ`（`firstAvailable.level 3`）、`s_nat`（`level 1`）。`level.number = 2` → 只创建 `s_nat`；`number = 3` → 两者都创建（`s_civ` ID 较小，按目录顺序）；`number = null` → 两者都创建。

### 7.2 航迹融合（WS01-008）

**T-02-20 本地交叉升级**
- `s_ac@(5000,5000)`、`s_ac@(6000,5000)`；目标 `AltM 50` 于 `(5500,5500)`（两者距离均为 707.1…）→ `Quality == Approximate`、`LocalSensorCount == 2`、`NetworkQuality == Approximate`、`ErrorRadiusM == 500`（交叉升级，无同质量探测 → 取表值）、`Tag == UAV`。
- 第二个 `s_ac` 改在 `(9000,5000)`（距离 3535.5…）→ `Vague`、`LocalSensorCount == 1`、`ErrorRadiusM == 2000`、`Tag == null`。
- 一个 `s_ac@(5000,5000)` + 目录加入 `s_nat`，目标 `AltM 500` 于 `(5500,5500)` → `Vague`、`LocalSensorCount == 1`（国家层不计）。

**T-02-21 外推与超时丢失**
`r_reg@(5000,5000)`；目标 `AltM 500`，第 1 步于 `(14990,5000)`，`VelMps (10,0)`。

| Tick | 目标 x | 探测 | 航迹 `Pos.X` | 事件 |
|---|---|---|---|---|
| 1 | 14990 | 有 | 14990 | `TrackCreated` |
| 2 | 15000 | 有 | 15000 | — |
| 3 | 15010 | 无 | 15010 | — |
| 4 | 15020 | 无 | 15020 | — |
| 5 | 15030 | 无 | 15030 | — |
| 6 | 15040 | 无 | （已删除） | `TrackLost{…, Timeout}` |

第 3–5 步 `Quality == Approximate`、`NetworkQuality == null`。

**T-02-22 目标消失**
`r_reg@(5000,5000)`，目标静止于 `(8000,5000)`；脚本在第 3 步移除目标。第 3 步事件含 `TrackLost{…, ThreatGone}`，第 3 步末无航迹。

**T-02-23 精确外推降级**
`f_sam@(5000,5000)`，目标 `AltM 500` 静止于 `(10000,5000)`；第 3 步生效 `SectorEmissionOverride{Center (5000,5000), RadiusM 100, Silence}`。
- 第 1–3 步：`Quality == Precise`。第 3 步事件含 `EmitterSwitched{1, false, SectorSilence}`。
- 第 4 步：`TrackQualityChanged{…, Precise, Approximate}`，`PreciseHolderIds` 为空，`Tag == UAV`。
- 第 7 步：`TrackLost{…, Timeout}`。

**T-02-24 诱饵甄别（两次掷骰与敌情档案加成，A-2-22）**
部署 `r_reg@(5000,5000)`、`f_sam@(5000,5000)`（策略 `silent_standby`）；`m_decoy` 目标 `AltM 500` 静止于 `(12000,5000)`（距 `f_sam` 7000，在火控距离内、武器射程外，静止 → 不会打开指示窗口）；第 3 步生效 `SectorEmissionOverride{(5000,5000), 100, ForceOn}`。`fusion` 子流脚本 `[0.61, 0.59]`。
- 第 1 步：`Approximate`；掷 `p = 0.5`，`0.61` 失败；`DecoyCheckedQuality == Approximate`；`Tag == UAV`（诱饵显示为无人机）。
- 第 2、3 步：不掷。第 3 步 `f_sam` 开机（`SectorForceOn`）。
- 第 4 步：`Precise`；掷 `p = 0.6000000000000001`，`0.59` 成功 → 事件 `DecoyIdentified{TrackId}`；`Tag == DECOY`；`DecoyCheckedQuality == Precise`。
- 第 5–10 步：不再消耗（脚本已耗尽，不抛异常即通过）。
- 变体 1：脚本 `[0.49]` → 第 1 步即识别，第 4 步不掷。
- 变体 2：`SimConfig.CarryIn.Dossier = [DossierCarryIn("m_decoy", DecoyIdentificationBonus: 0.1, InterceptProbMult: 1.0)]`，脚本 `[0.61, 0.74]` → 第 1 步 `pNew = 0.6`（`0.61` 失败），第 4 步 `pNew = 0.9`、条件概率 `p = (0.9 − 0.6) / (1 − 0.6) = 0.75`（容差 1e-9，`0.74` 成功识别）。

**T-02-25 模糊航迹不甄别**
`s_ac@(5000,5000)`，`m_decoy` 于 `(6000,5000)`、`AltM 50`；`fusion` 子流脚本为空。运行 10 步不抛异常；`DecoyIdentified == false`；`Tag == null`。

**T-02-26 位置选择与误差圈**
`r_fast@(5000,5000)`（ID 1）、`r_reg@(5000,6000)`（ID 2）；目标 `AltM 500` 于 `(8000,5000)`：`Quality == Approximate`、`ErrorRadiusM == 250`（取同质量探测的最小值）、`Pos == (8000,5000)`。

**T-02-27 精确 + 网络**
`f_sam@(5000,5000)`、`r_reg@(5000,5000)`；目标 `AltM 500` 于 `(9000,5000)`：`Quality == Precise`、`NetworkQuality == Approximate`、`PreciseHolderIds == [1]`、`ErrorRadiusM == 0`。

### 7.3 电子战（WS01-015）

除注明外：`ew_*@(5000,5000)`（缺省 `always_on`），目标 `AltM 50`、静止，`ew` 子流用 `ScriptedRandom`。

**T-02-30 导航干扰成功**
`ew_jam`；`m_cm` 第 1 步于 `(8000,5000)`；脚本 `[0.4]`。第 1 步：`EwEverCovered == true`、`EwNav == Applied`、`EwExtraOffsetM == 1500.0`（C 档）、`AccuracyTierDrop == 0`；事件 `EwDiverted{ThreatId, SourceId: 1, NavJam}`。运行到第 6 步不再消耗。

**T-02-31 导航干扰失败后锁存**
同上，脚本 `[0.5]`（不小于 0.5）→ `EwEverCovered == true`、`EwNav == Resisted`、`EwExtraOffsetM == 0`，无事件；第 2–6 步不消耗（A-2-07）。

**T-02-32 免疫与无效对象**
`ew_jam`；`m_fiber`（误列在有效对象中但 `ewImmune`）于 `(8000,5000)`、`m_bm` 于 `(8000,5000)`、`m_cm` 于 `(10000.001,5000)`；脚本为空，运行 5 步不抛异常；三者 `EwNav == None`、`EwEverCovered == false`。

**T-02-33 导航欺骗诱导**
`ew_spoof`，`LurePoint (6000,1000)`；`m_cm` 于 `(8000,5000)`。
- 脚本 `[0.1, 0.2]` → `EwNav == Applied`、`EwPull == Applied`、`EwDivertPos == (6000,1000)`，且调用 `ThreatRouting.Retarget(t, (6000,1000))`（A-2-27）；第 1 步事件依次为 `EwDiverted{t, SourceId: 1, NavJam}`、`EwDiverted{t, SourceId: 1, NavSpoofPull}`。
- 脚本 `[0.1, 0.3]` → `EwPull == Resisted`、`EwDivertPos == null`，只有 `NavJam` 事件。
- 无 `LurePoint`，脚本 `[0.1]` → 只掷一次。

**T-02-34 AI 视觉目标（2025 年后）**
`level.dateRange.from = 2025-06-01`（解析到第二行：`NavTerminalIneffectiveVsAiVision = true`）。`m_ai` 于 `(8000,5000)`。
- 只部署 `ew_jam`：脚本为空，运行 5 步不抛异常，`EwNav == None`。
- 部署 `ew_jam`（ID 1）与 `ew_spoof`（ID 2，`LurePoint (6000,1000)`）：导航概率 `max(0, 0.25) = 0.25`，生效单位 ID 2；脚本 `[0.24, 0.15]` → `EwNav == Applied`（事件 `SourceId == 2`）；诱导概率 `0.3 × 0.5 = 0.15`，`0.15` 不小于 → `EwPull == Resisted`。

**T-02-35 链路中断结果**
`ew_cuas`；`m_fpv` 于 `(6000,5000)`（权重 crash 1 / hover 1 / return 2，总 4）。

| 脚本 | `x = u × 4` | 结果 |
|---|---|---|
| `[0.7, 0.6]` | 2.4 | `LinkCutState == Return`，调用 `ThreatRouting.BeginEgress(t)`，事件 `EwLinkCut{t, SourceId: 1, Return, "m_fpv"}` |
| `[0.7, 0.1]` | 0.4 | 事件 `EwLinkCut{t, SourceId: 1, Crash, "m_fpv"}`，同一步目标被移除；第 2 步不再有该目标 |
| `[0.7, 0.3]` | 1.2 | `LinkCutState == Hover`，`LinkCutAtTick == 1`，调用 `ThreatRouting.Hover(t)`，事件 `EwLinkCut{t, SourceId: 1, Hover, "m_fpv"}` |
| `[0.8]` | — | `0.8` 不小于 `0.8` → `Resisted`，只消耗 1 个值 |

**T-02-36 悬停后坠落（A-4-04）**
接 T-02-35 第三行：第 2、3 步目标仍存活；第 4 步（`4 ≥ 1 + 3`）发出事件 `EwLinkCut{t, SourceId: 0, Crash, "m_fpv"}` 并在同一步移除目标。加部署 `r_reg@(5000,6000)`：第 5 步事件含 `TrackLost{…, ThreatGone}`。

**T-02-37 时期前弱化、新阵地、断电与冬季（B-T2-05、B-T2-06、C-T2-07）**
`m_cm` 于 `(8000,5000)`：

| 设置 | 概率 | 脚本 | 结果 |
|---|---|---|---|
| `ew_weak`，`level.number = 4` | 0.25 | `[0.3]` | `Resisted` |
| `ew_weak`，`number = null` | 0.5 | `[0.3]` | `Applied` |
| `ew_weak`，`number = 6` | 0.5 | `[0.3]` | `Applied` |
| `ew_jam`，`FirstNightAtNewPosition = true` | 0.35 | `[0.34]` | `Applied` |
| 同上 | 0.35 | `[0.35]` | `Resisted` |
| `ew_jam`，`Powered = false` | 0.25 | `[0.24]` | `Applied` |
| `ew_jam`，`night.Season = Winter` | 0.45 | `[0.44]` | `Applied` |

**T-02-38 国家级导航欺骗与不叠加裁决（A-2-21、B-T3-08）**
- 脚本第 1 步创建 `SupportAsset{DefId: "s_nspoof", State: Active, CenterPos: (5000,5000), RadiusM: 10000}`（ID 记为 a），并创建 `m_cm` 于 `(14000,5000)`；无电子战单位；`ew` 脚本 `[0.3]`。第 1 步：`NationalSpoof == Applied`、`AccuracyTierDrop == 2`、`EwExtraOffsetM == 0.0`、事件 `EwDiverted{t, SourceId: a, NationalSpoof}`。
- 同时部署 `ew_jam@(5000,5000)`（ID 1），`m_cm`（C 档：`offsetCells 1..2` 中点 1500 m，`ewExtraM = 1500` → 3000 m；降到 D 档：`offsetCells 2..4` 中点 3000 m）于 `(8000,5000)`，`ew` 脚本 `[0.3, 0.3]`：两者均 `Applied`，按 §3.4.3 取偏移期望较大者且**不叠加**，满足不变量 `!(AccuracyTierDrop > 0 && EwExtraOffsetM > 0)`。
- `m_bm`（不在 `ew_jam` 有效对象中）→ 不掷。`State = Arriving` 或 `Expired` → 不掷。目标于 `(15000.001,5000)` → 不掷。

**T-02-39 城区导航干扰计时**
- `ew_jam@(10000,10000)`（城区内）运行 10 步 → `Ew.UrbanNavJamSec == 10.0`；再加 `ew_spoof@(9000,9000)` → 仍为 10.0。
- `ew_jam@(5000,5000)` → 0.0。
- `ew_jam@(10000,10000)`，第 6 步生效扇区静默 → 10 步后为 6.0（第 6 步电子战仍按第 5 步的"开"计）。

**T-02-40 查询函数**
部署 `ew_jam@(5000,5000)`（ID 1）、`f_gun@(0,0)`（ID 2，`EquipmentEwIds ["ew_shield"]`）、`f_gun@(1000,0)`（ID 3）。
- `IsInFriendlyEwZone((10000,5000)) == true`；`((10000.001,5000)) == false`；扇区静默 `ew_jam` 一步后（`On == false`）→ `((5000,5000)) == false`。
- `ShieldHitProbMult(2, "m_fpv") == 0.6`；`(2, "m_cm") == 1.0`；`(3, "m_fpv") == 1.0`；`(2, "m_fiber") == 1.0`（`ew_shield` 有效对象中无 `m_fiber`）。

### 7.4 辐射策略与触发规则（WS01-013、014）

**T-02-50 初始状态**
部署 `r_reg`（缺省）、`r_reg`（`on_warning`）、`r_reg`（`intermittent`）、`f_sam`（`silent_standby`），位置任意。`Create` 后：`On == [true, false, true, false]`，`OnSinceTick == [0, −1, 0, −1]`，`f_sam.FcMode == Off`；`DrainEvents()` 只有 `NightStarted`。

**T-02-51 间歇开机**
- `r_reg@(5000,5000)`，`intermittent`，`DutyOnSec 3, DutyOffSec 3`（周期 6）：`EmitterSwitched` 为 `(3, false)`、`(6, true)`、`(9, false)`，`Cause` 均为 `Policy`。目标 `AltM 500` 静止于 `(8000,5000)`：探测发生在第 1、2、3、7、8、9 步；第 4–6 步外推（`6 − 3 = 3`，不丢失）；整个过程只有一条航迹。
- 改 `DutyOffSec 4`（周期 7）：关机 `(3, false)`，开机 `(7, true)`；探测在第 1–3、8–10 步；第 7 步 `TrackLost{…, Timeout}`；第 8 步新 `TrackCreated`（航迹 ID 与第一条不同）。

**T-02-52 按预警开机**
`U = r_reg@(5000,5000)`（`on_warning`，ID 1），`r2 = r_reg@(5000,15000)`（缺省，ID 2）；目标 `AltM 500` 第 5 步于 `(5000,10000)`，脚本第 10 步移除。
- 第 1–4 步：`U.On == false`，无 `U` 的事件。
- 第 5 步：`EmitterSwitched{1, true, Policy}`。
- 第 10 步：`TrackLost{…, ThreatGone}`，之后 `EmitterSwitched{1, false, Policy}`。

**T-02-53 静默待机：火控指示窗口**
`f = f_sam@(2000,10000)`（`silent_standby`，ID 1）、`r = r_reg@(2000,11000)`（ID 2）；`m_uav` 目标 `AltM 500`，第 1 步于 `(9400,10000)`，`VelMps (−100,0)`。
相对 `f` 的距离第 k 步为 `7400 − 100(k − 1)`；进入射程 6000 所需时间 `τ`：第 8 步 7.0、第 9 步 6.0。
- 第 1–8 步：`f.On == false`。
- 第 9 步：`EmitterSwitched{1, true, Policy}`；`f.FcMode == Cued`。
- 第 10 步：航迹 `Quality == Precise`、`PreciseHolderIds == [1]`、`NetworkQuality == Approximate`。
- 不部署 `r`：120 步内 `f.On` 恒为 false，无航迹。

**T-02-54 静默待机的可用性**
`SetEmissionPolicy{UnitId, "silent_standby"}`：对 `f_sov` → `CommandRejected(NotAvailable)`；对 `f_sam` 且 `level.number = 5` → `NotAvailable`；`number = 6` → 接受；`number = null` → 接受；对 `r_reg` → `WrongEntityKind`。

**T-02-55 火控指示的暴露系数（WS01-014 验收）**
- 有网络：`f_sam@(5000,5000)`（缺省 `always_on`）、`r_reg@(5000,5000)`；目标 `AltM 500` 静止于 `(9000,5000)`，第 1 步创建。第 1–10 步 `f_sam.FcMode == Cued`；10 步后 `f_sam.Exposure == 5.999999999999999`（容差 1e-9），`r_reg.Exposure == 10.0`。
- 无网络：只部署 `f_sam` → `FcMode == SelfSearch`，10 步后 `Exposure == 20.0`。
- 两者之比 `0.3`（容差 1e-9），等于 `Cueing.Cued.ExposureMult`。

**T-02-56 反辐射来袭：立即关机、关机时机与 `HomingUnitId`（A-2-06）**
`r = r_reg@(0,10000)`（缺省：`OnArmIncoming = ShutdownImmediately`，ID 1）；`m_arm` 目标 `AltM 5000`，第 1 步于 `(20000,10000)`，`VelMps (−1000,0)`，`TargetUnitId = 1`。
- 第 1–10 步：`ArmInitialDistM == 20000`，`HomingUnitId == 1`。
- 第 11 步（距离恰 10000，首次被探测）：事件依次含 `TrackCreated{k, Approximate}`、`ArmThreatDetected{k, 1}`、`EmitterSwitched{1, false, ArmShutdown}`；`ArmHitProbMult == 0.5`（`f = 0.5`，不满足 > 0.5，取第二档）；关机当步末 `HomingUnitId == 0`、`TargetUnitId == 1`（`TargetUnitId` 不被 02 清零）。
- 第 12 步：`r.On == false`，航迹外推，`HomingUnitId == 0`。
- 脚本第 13 步移除导弹：第 13 步事件含 `TrackLost{k, ThreatGone}`、`EmitterSwitched{1, true, Policy}`。
- 变体：导弹第 1 步于 `(16000,10000)` → 第 7 步首次探测并关机，`f = 0.625`，`ArmHitProbMult == 0.2`。

**T-02-57 完成当前拦截后关机与二选一静默钩子（A-2-11）**
`f = f_sam@(0,10000)`（`OnArmIncoming = ShutdownAfterCurrentIntercept`，ID 1）；`m_arm` 第 1 步于 `(12000,10000)`，`VelMps (−500,0)`，`TargetUnitId 1`；脚本第 5 步创建 `Interceptor{FireUnitId 1}`，第 12 步移除。
- 第 9 步（距离 8000，火控首次探测）：`ArmThreatDetected`；`ArmPending == true`；`f.On == true`；`HomingUnitId == 1`。
- 第 10、11 步：仍开机。
- 第 12 步：`EmitterSwitched{1, false, ArmShutdown}`；`f = 6500 / 12000 = 0.5416…` → `ArmHitProbMult == 0.2`；`HomingUnitId == 0`。
- 变体 1（不创建拦截弹）：第 9 步即关机，`f = 0.6666…` → 0.2。
- 变体 2（第 10 步阶段 0 调用 `EmissionChoiceEffects.ApplyArmChoice(state, 1, silence: true)`）：`ArmSilenced == true`、`ArmPending == false`，第 10 步系统 5 立即发出 `EmitterSwitched{1, false, ArmShutdown}` 并锁存 `ArmHitProbMult`。

**T-02-58 继续交战、扇区静默、重新开机**
同 T-02-56，但 `OnArmIncoming = KeepEngaging`；第 19 步生效扇区静默 `{(0,10000), 100, Silence}`，第 20 步生效同扇区 `Cancel`。
- 第 11 步：`ArmThreatDetected{k, 1}`，**无** `EmitterSwitched`。
- 第 19 步：`EmitterSwitched{1, false, SectorSilence}`；距离 2000，`f = 0.1` → `ArmHitProbMult == 0.8`。
- 第 20 步：`EmitterSwitched{1, true, Policy}`；`ArmHitProbMult == null`；`HomingUnitId == 1`。
- 第 11–20 步只有一个 `ArmThreatDetected`。

**T-02-60 扇区命令**
`A = r_reg@(5000,5000)`（ID 1）、`B = r_reg@(10000,5000)`（ID 2）、`C = r_reg@(10001,5000)`（ID 3，`on_warning`）。
- 第 5 步 `{(5000,5000), 5000, Silence}`：第 5 步 `EmitterSwitched{1, false, SectorSilence}`、`{2, false, SectorSilence}`；`C` 不受影响（距离 5001）。
- 第 8 步 `{(10001,5000), 1, ForceOn}`：`B`（距离 1，含边界）与 `C` 都在扇区内 → 第 8 步事件依次为 `EmitterSwitched{2, true, SectorForceOn}`、`{3, true, SectorForceOn}`。
- 第 10 步 `{(5000,5000), 6000, Cancel}`（三者都在扇区内）：事件依次为 `{1, true, Policy}`、`{3, false, Policy}`；`B` 由强制开机回到策略 `always_on`，状态未变，无事件。
- `RadiusM = 0` 或 `NaN` → `CommandRejected(InvalidArgument)`。

**T-02-61 主雷达被毁，邻近雷达接替**
`A = r_reg@(0,10000)`（ID 1）、`B = r_reg@(5000,10000)`（ID 2，`on_warning`，`NeighborTakeover true`）；`ScriptedEvents` 在第 5 步移除 `A` 并发出 `PlayerUnitDestroyed{UnitId 1, DefId r_reg, Category PlayerUnitCategory.Sensor, Pos (0,10000)}`（A-3-05）。
- 第 6 步：`EmitterSwitched{2, true, Takeover}`；`B.TakeoverActive == true`。
- 变体：`B@(15000,10000)`（距离 15000 > 10000）→ 不接替。被毁的是 `s_ac` → 不接替。`B.NeighborTakeover = false` → 不接替。
- 接替后第 8 步对 `B` 生效 `SetEmissionPolicy{2, "on_warning"}` → `TakeoverActive == false`，第 8 步 `EmitterSwitched{2, false, Policy}`。

**T-02-62 开火后转移**
`f = f_sam@(5000,5000)`（`AfterFiring = RelocateToAlternate`，`AlternatePositionId = "alt_s"`，ID 1）；`ScriptedEvents` 第 3 步发 `InterceptorLaunched{FireUnitId 1, WeaponId w_sam}`。
- 第 3、4 步末：`PendingRelocationAltId == null`；第 5 步末：`== "alt_s"`，`FiredSinceRelocation == false`。
- 变体：`AlternatePositionId = null` → 始终 null，`FiredSinceRelocation == true`。
- 变体：脚本第 3 步同时创建 `Interceptor{FireUnitId 1}`、第 8 步移除 → 第 8 步末才设置。

**T-02-63 诱饵配合**
`U = r_reg@(5000,5000)`（`decoy_coordinated`，ID 1）、`r2 = r_reg@(5000,7000)`（ID 2）、`D = d_decoy@(6000,6000)`（ID 3，缺省 `always_on`）；目标 `AltM 500` 静止于 `(5000,9000)`，第 1 步创建。
- 第 1、2 步：`U.On == false`；第 3 步：`EmitterSwitched{1, true, Policy}`。
- 变体（不部署 `D`）：第 1 步即开机。

**T-02-64 `SetEmissionPolicy` 校验与应用（含指挥点检查，A-2-17）**
部署 `r = r_reg`（ID 1）、`s = s_ac`（ID 2）。

| 命令 | 结果 |
|---|---|
| `{999, "always_on"}` | `UnknownEntity` |
| `{2, "always_on"}` | `WrongEntityKind` |
| `{1, "nope"}` | `InvalidArgument` |
| `{1, "intermittent", DutyOnSec 0}` | `InvalidArgument` |
| `{1, "intermittent", DutyOnSec 0.5, DutyOffSec 0.5}` | 接受（各为 1 步） |
| `level.protagonist = B` 时 `{1, "always_on"}` | `NotAvailable` |
| `CommandPoints == 0` 且命令耗点 1 时 `{1, "on_warning"}` | `NoCommandPoints` |

另：第 5 步生效 `{1, "intermittent", DutyOnSec 2, DutyOffSec 2}` → `DutyPhaseStartTick == 5`；第 5、6 步开（第 5 步无事件：状态未变），第 7 步 `EmitterSwitched{1, false, Policy}`，第 9 步 `{1, true, Policy}`。

**T-02-65 未展开强制关机**
`r_reg@(5000,5000)`（ID 1），目标 `AltM 500` 静止于 `(8000,5000)`；脚本第 4 步设 `DeployState = Packing`，第 6 步设回 `Deployed`。
- 第 4 步：`EmitterSwitched{1, false, NotDeployed}`（第 4 步本身仍有探测：用第 3 步的开机状态）。
- 第 5、6 步：无探测（第 5 步未展开；第 6 步沿用第 5 步的关机状态），航迹外推。
- 第 6 步：`EmitterSwitched{1, true, Policy}`；第 7 步恢复探测，航迹未丢失（`7 − 4 = 3`，第 6 步 `6 − 4 = 2`）。

### 7.5 暴露度（WS01-012）

**T-02-70 累积、静默、夹取**
`r = r_reg`（ID 1）、`s = s_ac`（ID 2）；第 31 步生效扇区静默覆盖 `r`。
- 第 30 步末：`r.Exposure == 30.0`；第 40 步末：`25.0`；`ExposurePeak == 30.0`。
- `s.Exposure` 始终 `0.0`，无阈值事件。
- 40 步内无 `ExposureThresholdCrossed`（峰值 30 < 40）。

**T-02-71 发射增量**
`f = f_sam`（`silent_standby`，无航迹 → 关机，ID 1）、`g = f_gun`（ID 2）；`ScriptedEvents` 第 2 步发 2 个 `InterceptorLaunched{1, w_sam}`、1 个 `GunFired{2, w_gun}`。
- `f.Exposure`：第 1 步 `0.0`，第 2 步 `10.0`（有发射，不扣静默），第 3 步 `9.5`；`ExposurePeak == 10.0`。
- `g.Exposure` 始终 `0.0`。

**T-02-72 侦察无人机**
`g = f_gun@(5000,5000)`；`p_recon` 第 1 步于 `(10000,5000)`（恰 5000）。10 步后 `g.Exposure == 5.0`。再加一架 `p_recon@(5000,10000)` → 仍 `5.0`。侦察机改在 `(10000.001,5000)` → `0.0`。

**T-02-73 阈值事件**
- 加载：夹具 `thresholds` 乱序 → `Rules.Exposure.Thresholds` 的 `AtLeast` 依次为 `40, 70, 100`。
- `f = f_sam`（缺省 `always_on`、无网络 → `SelfSearch` 2.0/s）：第 20 步 `ExposureThresholdCrossed{1, 40, AntiRadiationPriorityTonight, true}`；第 35 步 `{1, 70, KnownTargetListNextNight, true}`；第 50 步 `{1, 100, PrecisionStrikeTonight, true}`；第 51–60 步无暴露事件，`Exposure == 100.0`。
- `f = f_sam`（`silent_standby`）；`ScriptedEvents` 第 1 步发 15 个 `InterceptorLaunched{1, w_sam}` → 第 1 步 `Exposure == 75.0`，事件依次 `{1, 40, …, true}`、`{1, 70, …, true}`；第 2 步发 `UnitDeployStateChanged{UnitId 1, From Deploying, To Deployed, CompletedRelocation true, DestinationScouted false, DestinationAlternatePositionId "alt_u"}` → `Exposure == 0.0`，事件依次 `{1, 70, …, false}`、`{1, 40, …, false}`；`NewPositionPenalty == true`；`ExposurePeak == 75.0`。

**T-02-74 转移到已被侦察的阵地**
同 T-02-73 第二组，但第 2 步事件 `DestinationScouted true, DestinationAlternatePositionId "alt_s"` → `Exposure == 37.0`（`75 × 0.5 = 37.5`，再静默 −0.5）；事件 `{1, 70, …, false}`、`{1, 40, …, false}`；`NewPositionPenalty == false`。`DestinationAlternatePositionId = null` → `NewPositionPenalty == true`。

**T-02-75 诱饵辐射源与防护罩的暴露**
- `d_decoy`（缺省 `always_on`）10 步后 `Exposure == 10.0`。
- `f_gun`（`EquipmentEwIds ["ew_shield"]`，展开）10 步后 `Exposure == 2.9999999999999996`（容差 1e-9）；同一单位 `DeployState = Packed`（脚本第 1 步开头设置）→ `0.0`。

**T-02-76 大功率电子战站的辐射暴露（C-T1-13）**
- 部署 `ew_jam`（`emissionExposure: high`，缺省 `always_on`）：运行 10 步后 `Exposure == 10.0`（每秒 `+1.0`）。
- 若第 1 步生效扇区静默（`On == false`）：10 步后 `Exposure == 0.0`。

### 7.6 欺骗单位（WS01-016）

**T-02-80 假发射车被识破**
`d = d_fake@(5000,5000)`（ID 1）；`exposure` 子流脚本 `[0.5, 0.2]`。目标：`r1 = p_recon` 第 2 步于 `(8000,5000)`；`nq = p_recon_nq` 第 3 步于 `(6000,5000)`；`r2 = p_recon` 第 6 步于 `(5000,9000)`；`r3 = p_recon` 第 8 步于 `(5000,1000)`。
- 第 2 步：掷 `0.5`（≥ 0.3）未识破。第 3 步：`nq` 无侦察质量，不掷。
- 第 6 步：掷 `0.2` → `SeenThrough == true`，事件 `DeceptionTriggered{1, r2, SeenThrough}`。
- 第 8 步：不掷（脚本耗尽也不抛异常）。
- `ReconCheckedThreatIds == [r1, nq, r2]`（ID 升序）。
- `d.Exposure`：第 10 步末 `4.5`（第 2–10 步侦察 +0.5/s）。

**T-02-81 诱饵吸引**
`d = d_decoy`（ID 1）、`r = r_reg`（ID 2）；`m_arm` 第 2 步创建，`TargetUnitId 1`；另一枚 `m_arm` 第 2 步创建，`TargetUnitId 2`。第 2 步恰有一个 `DeceptionTriggered{1, <第一枚>, Attracted}`；第 3 步没有。

### 7.7 确定性

**T-02-90 综合场景可复现**
部署 `r_reg@(5000,5000)`、`s_ac_fa@(6000,5000)`、`f_sam@(5000,5000)`（`silent_standby`）、`ew_jam@(8000,5000)`、`d_decoy@(9000,9000)`；目标：`m_cm` ×3 与 `m_decoy` ×3 在第 1–6 步依次从 `(19000, 2000 + 2000i)` 以 `VelMps (−50,0)` 进入，`m_arm` 第 10 步从 `(19000,9000)` 以 `(−400,0)` 进入、`TargetUnitId` = `d_decoy`。全部子流用正常 `SimRandom`，seed `0x6DD180096484586D`，运行 120 步，两个独立世界每步 `ComputeStateHash()` 相等，且 `DrainEvents()` 的事件序列逐项相等。

---

## 8. 待决问题

### 8.1 需要人决定的规则问题（全部已决）

| # | 问题 | 背景 | 裁决结论 |
|---|---|---|---|
| Q1 | 低空能力 `poor / medium / good / very_good` 如何数值化 | Schema 注明"数值化由 WS01-007 决定"；数值表只有定性描述 | **已决（2026-10-17）**：`rules/tracks.json` 的 `detectionRules` 取 `lowAltitudeBelowM = 1000`、`lowAltitudeRangeMult = 0.3 / 0.6 / 0.9 / 1.0`、`largeBlindZoneLowAltitudeRangeMult = 0.5`、覆盖型低空要求 `good` 以上；视线由 01 计入 4/3 地球等效曲率，本表低空倍率代表地杂波与设备低空探测能力，由 D3 联合复核 —— 依据 B-T2-32、B-T2-02 |
| Q2 | 航迹关联方式 | 任务要求选一个 | **已决（2026-10-17）**：按真实 `ThreatId`（D1） —— 依据 B-T1-07 |
| Q3 | "精确"是否只对自带火控的火力单元有效（`PreciseHolderIds`），探测单位输出质量是否封顶为"大致" | 数值表 1.3：精确 = 防空系统自带火控雷达；GDD 8.1 火控指示联动 | **已决（2026-10-17）**：是（D2）；03 发射导弹须 `f.Id ∈ PreciseHolderIds`；探测单位输出封顶为"大致"，Schema 删除探测单位 `precise` 取值 —— 依据 B-T2-33 |
| Q4 | 无火控雷达的单位如何获得发射所需的精确航迹 | 质量表：大致航迹 `missilesAllowed = false`；单兵导弹没有雷达却必须能发射 | **已决（2026-10-17）**：新增 `selfAcquisitionRangeKm`（基础值 = 最大武器射程）与 `selfAcquisition`（`none \| passive \| optical`）；`optical` 在夜间无探照灯 / 热像时乘 `opticalNightRangeMult = 0.3` —— 依据 B-T2-09 |
| Q5 | 火控雷达参数与系统反应时间从哪里来 | 数据中没有火控雷达距离、低空能力、苏 / 西制式、反应时间 | **已决（2026-10-17）**：`fireControlRadar { rangeKm = 最大射程 × 1.25, lowAltitude (近程 good / 中远程 medium), origin, antennaHeightM? }`；反应时间挂在武器 `WeaponDef.ReactionSec`（缺省回退 `engagement.reactionGameSecByClass`），02 指示窗口取单位武器的 `max(w.ReactionSec)` —— 依据 B-T2-01、B-T2-34、P15 |
| Q6 | 辐射策略的 `exposureMult`、`cueing.*.exposureMult` 是否在模拟中相乘 | 状态机已经通过开关机时间体现差异；`0.3 = 0.6 / 2.0` 说明是概括值 | **已决（2026-10-17）**：不相乘（D5），模拟中暴露度只按开机时间与火控模式（`SelfSearch` 2.0/s vs `Cued` 0.6/s）自然产生；策略缺省参数由 D3 标定使平均暴露比落在数值表 §3.5 标称值的 ±25% 内 —— 依据 B-T3-10 |
| Q7 | "静默 −0.5"在侦察无人机附近 / 刚发射时是否同时生效 | 若同时生效，"侦察 +0.5（不论是否开机）"与静默正好抵消 | **已决（2026-10-17）**：静默只在本步没有任何正向来源（辐射、侦察、发射）时生效 —— 依据 B-T3-10 |
| Q8 | 导航干扰的落点偏移按 1.4 还是 3.1？是否同时与国家级导航欺骗叠加 | 数值表 5.3 明确留待 WS01-015 确认 | **已决（2026-10-17）**：区域导航干扰 / 欺骗按 3.1 `ewExtraCells` 加偏移米数，国家级导航欺骗按 `accuracyTierDrop` 降档；两者同目标同时生效时不叠加，只取偏移期望较大者 —— 依据 B-T3-08 |
| Q9 | 电子战效能百分比的含义 | 数值表"效能 70%" | **已决（2026-10-17）**：每个目标、每类效果（导航 / 诱导 / 国家级 / 链路）在首次受覆盖时只掷一次，结果锁存到当夜结束（D4） —— 依据 B-T3-08 |
| Q10 | 链路中断后坠落 / 悬停 / 返航的权重；悬停多久；坠落是否造成伤害 | Schema 注明"权重由 WS01-015 决定" | **已决（2026-10-17）**：`linkCutOutcomeWeights = { crash 0.5, hover 0.25, return 0.25 }`，`hoverBeforeCrashGameSec = 2`；坠落不造成地面伤害 —— 依据 B-T2-35、B-T3-08 |
| Q11 | 哪些敌方弹药属于"AI 视觉制导"；"末段无效"的含义 | 数值表 1.4：2025 春起导航干扰 50%（末段无效）；导航欺骗站对 AI 视觉型效果减半 | **已决（2026-10-17）**：新增弹药字段 `aiVisionFrom`（`shahed_136 = 2025-06`、`geran_2_heavy = 2025-03`）；末段无效 = 区域导航干扰站对其概率为 0，导航欺骗站 × `aiVisionEffectMult` —— 依据 B-T2-35、B-T3-08 |
| Q12 | 区域导航干扰站"第 3 关（弱）/ 第 6 关"的"弱"是多少 | `firstAvailable.fullStrengthLevel = 6`，无数值 | **已决（2026-10-17）**：`rules/ew.json` 新增 `belowFullStrengthMult = 0.5`，乘在效果概率上 —— 依据 B-T2-35、B-T3-08 |
| Q13 | 国家级导航欺骗的"某区域"多大、由谁指定 | `support.json` 无半径字段 | **已决（2026-10-17）**：`national_gnss_spoof.radiusKm = 30`，中心点由 `CallSupport` 命令给出，运行态存于 `SupportAsset.RadiusM` —— 依据 B-T2-04、A-2-21 |
| Q14 | "城区内长时间开启导航干扰"的"长时间"阈值与后果 | 数值表 1.4 副作用 | **已决（2026-10-17）**：`urbanNavJamMinGameSec = 60`；以干扰站位置在城区多边形内为准；达标时每夜触发一次城市资源 −1（并入 05 城市资源） —— 依据 B-T2-36 |
| Q15 | 友军干扰倍率重复；"己方无人机链路有概率中断"无概率 | 两处数据 | **已决（2026-10-17）**：03 只读 `intercept.json`；删除 `ew.json sideEffects.friendlyInterceptorDroneMult`；己方链路中断本版本不实现 —— 依据 B-T1-08 |
| Q16 | 关机时机中"反辐射导弹距离 > 50% 射程"的"射程"是什么 | Kh‑31P 数据没有射程字段 | **已决（2026-10-17）**：取导弹首次锁定目标时与目标的水平距离（`ArmInitialDistM`），分子为关机瞬间的水平距离 —— 依据 B-T2-37 |
| Q17 | 各辐射源未设置时的缺省策略与触发规则 | 数据没有缺省 | **已决（2026-10-17）**：`defaultStrategy = "always_on"`；触发规则缺省 `shutdown_immediately`、`stay`；`NeighborTakeover` 缺省关闭 —— 依据 B-T2-38 |
| Q18 | 间歇开机的缺省开 / 关时长；按预警开机的参考距离；诱饵配合的提前量 | 数值表"开 N 秒 / 关 N 秒" | **已决（2026-10-17）**：`dutyCycleDefaultOn/OffGameSec = 1 / 1`、`decoyLeadGameSec = 0.25`、`defaultReferenceRangeKm = 30`，由 D3 按 B-T3-10 标定 —— 依据 B-T2-39、B-T3-10 |
| Q19 | "开火后转移"的触发时机；无火控雷达单位和间歇开机的"可设置转移"是否也支持 | 数值表 3.5 只给选项 | **已决（2026-10-17）**：有火控的火力单元开火后至少一整步未再开火且无自家在飞拦截弹时设置 `PendingRelocationAltId`，由 04 执行自动转移；无火控单位与间歇转移走手动 `RelocateUnit` 命令 —— 依据 B-T3-06 |
| Q20 | "主雷达被毁时邻近雷达接替"的含义 | 数值表只有一句 | **已决（2026-10-17）**：设置了 `NeighborTakeover` 的辐射源，在其参考距离内有主动雷达（探测或火控）被毁后当夜保持开机，直到玩家重新设置策略 —— 依据 B-T2-40 |
| Q21 | 哪些敌方平台算"侦察无人机（Orlan 等）"；假发射车的"侦察质量" | 数值表 3.4、1.5 | **已决（2026-10-17）**：`behavior ∈ { spotter, armed_recon }` 算侦察；`reconQuality`（`orlan_10 = medium`、`orion = high`），识破概率 `0.1 / 0.3 / 0.6` —— 依据 B-T2-41、B-T2-14 |
| Q22 | 诱饵辐射源 / 牺牲雷达开机时的暴露速率；牺牲雷达是否同时提供探测 | 数值表 1.5 只说"模拟雷达开机" | **已决（2026-10-17）**：暴露速率按 `sensorExposureLevelRates.high`（`decoyEmitterExposureLevel = "high"`）；牺牲雷达不提供探测 —— 依据 B-T2-42 |
| Q23 | 新阵地首夜 −30% 是否也作用于探测单位和电子战单位 | 数值表 1.5"未完全融入防空网"；3.3 只写拦截概率 | **已决（2026-10-17）**：是，拦截概率 + 探测 / 火控距离 + 电子战概率均 ×0.7，字段统一为 `PlacedUnit.FirstNightAtNewPosition` 与运行态 `NewPositionPenalty` —— 依据 B-T2-06 |
| Q24 | 无线电侦测器"只对有链路的无人机"——哪些算有链路 | 数据没有标记 | **已决（2026-10-17）**：`fpv_radio`、`lancet`、`molniya`、`orlan_10`、`orion` 的 `radioLinked = true`；Shahed 系列与光纤 FPV 为 `false` —— 依据 B-T2-43 |
| Q25 | 自动探测单位（国家预警网、民众上报）何时出现 | 两者 `automatic: true`，`firstAvailable` 分别为第 1、3 关 | **已决（2026-10-17）**：`level.number == null` 或 `firstAvailable.level ≤ number` 时自动创建 —— 依据 B-T2-44 |
| Q26 | 白天关卡与天气倍率 | 数据没有昼夜标记；GDD 8.8 只有定性描述 | **已决（2026-10-17）**：`NightDef` 支持 `TimeOfDay`（缺省 `Night`）与 `Season`（缺省由日期推导）；白天不乘 `nightRangeMult`；光学天气倍率 `clear 1.0 / moonlit 1.3 / low_cloud 0.6 / fog 0.3`；冬季主动雷达距离与电子战概率 ×0.9 —— 依据 B-T2-45、B-T2-09、C-T2-07 |
| Q27 | 误报频率；误报航迹能否被交战 | 数值表"有误报 / 误报率高" | **已决（2026-10-17）**：`falseAlarmsPerGameSec = { some 0.02, high 0.1 }`；03 不得对 `ThreatId == 0` 的误报航迹交战 —— 依据 B-T2-46 |
| Q28 | 民众上报的延迟；B 线"空军空情"在模拟中的来源 | 数值表只说"延迟"；B 线没有区域雷达实体的控制权 | **已决（2026-10-17）**：`reportDelayGameSec = 0.5`；B 线由关卡预置区域雷达，探测延迟 `relayDelayGameSec`、质量封顶 `Approximate`、玩家不可改策略 —— 依据 B-T2-47 |
| Q29 | 航迹位置是否加随机误差 | 战争迷雾 | **已决（2026-10-17）**：不加随机误差，误差圈仅用于界面显示 —— 依据 B-T2-48 |
| Q30 | 航迹超时丢失时间；精确航迹失锁后的处理 | 数值表没有 | **已决（2026-10-17）**：`trackLostGameSec = 1`（60 s）；外推期间精确立即降为大致 —— 依据 B-T2-49 |
| Q31 | 雷达与电子战断电后"效能下降"多少 | GDD 8.5 | **已决（2026-10-17）**：主动雷达距离乘 `unpoweredActiveRangeMult = 0.5`，电子战概率乘 `unpoweredEffectMult = 0.5`；被动传感器、火力、欺骗单位不接入电网 —— 依据 B-T2-05 |
| Q32 | 哪些传感器需要地形视线；天线高度缺省值位置 | 声学探测不受山体遮挡；系留气球很高 | **已决（2026-10-17）**：`lineOfSight` 缺省 `true`（`acoustic_post` 为 `false`）；天线高度缺省值只留 `rules/terrain.json.defaultAntennaHeightM = 10`（气球填 300） —— 依据 B-T2-50、B-T2-03 |
| Q33 | 诱饵甄别在质量升级时如何再掷 | "大致 70% / 精确 95%"是累计识别率还是每次概率 | **已决（2026-10-17）**：每个质量等级最多掷一次，升级时用条件概率 `(p新 − p旧) / (1 − p旧)` 使累计识别率等于表值（含敌情档案加成） —— 依据 B-T2-51 |
| Q34 | 车载防护罩如何安装、何时生效、是否累积暴露度 | `equipmentSlot: true`，"不单独占位" | **已决（2026-10-17）**：作为宿主装备（`UnitSettings.EquipmentEwIds`），宿主展开且未暂停时常开，按 `low` 速率累积到宿主；命中倍率随反无人机效能衰减 —— 依据 B-T2-52 |
| Q35 | 单兵反无人机枪的"定向" | 需要朝向 | **已决（2026-10-17）**：按半径内全向处理 —— 依据 B-T2-53 |
| Q36 | "发射导弹（每发）+5"是否包括火箭与拦截无人机 | 数值表只说导弹 | **已决（2026-10-17）**：只计 `kind == missile` —— 依据 B-T2-54 |
| Q37 | `sensorExposureLevelRates`、`ewExposureLevelRates` 字段名缺单位后缀 | 违反 data/README 的后缀约定 | **已决（2026-10-17）**：改名为 `sensorExposureLevelRatesPerGameSec`、`ewExposureLevelRatesPerGameSec`（加载器兼容旧名并 ÷60） —— 依据 B-T1-09 |
| Q38 | `ratesPerGameSec` 中的 `warningRadarSoviet / warningRadarWestern / highPowerEw` 与等级速率表重复 | 数值表 3.4 与 5.3 两种写法 | **已决（2026-10-17）**：删除三项，统一只用两张等级速率表 —— 依据 B-T1-10 |
| Q39 | 敌方反辐射导弹 / 定点打击如何选择目标 | 欺骗的"效果"取决于敌方选目标 | **已决（2026-10-17）**：由 04（敌方 AI，含动态追加反辐射 / 定点打击与 `known_targets`）和 01（`target.mode = air_defense`）选目标并写 `Threat.TargetUnitId`；02 提供 `EmitterQueries.ListActive` 与 `DeceptionUnit.SeenThrough` —— 依据 B-T3-05 |

### 8.2 已登记到 00_core 的条目清单

> 以下条目均已在 D2a 中合入 `00_core.md`（对应补丁编号 P05、P06、P08、P09、P12、P15、P17–P20、P23–P26、P29、P32–P34、P36–P37、P44、P46、P48），此处保留对齐摘要。

**A. 实体字段（00 的 2.4 / 各实体状态表）**

| 表 / 实体 | 字段（顺序即哈希顺序） | 规格 / 补丁 |
|---|---|---|
| `PlayerUnitCommon`（四类我方单位） | `Placement`（`PlacedUnit?`，不哈希）、`Horizon`（`HorizonProfile?`，不哈希）、`Emitter`（`EmitterControl?`）、`ExposurePeak`（`double`）、`NewPositionPenalty`（`bool`）、`PendingRelocationAltId`（`string?`）、`EquipmentEwIds`（`List<string>`）、`Suspended` / `SuspendedUntilSec` | 02 2.1 / P20、P23、P24 |
| `EmitterControl`（组件类） | 见 2.2 全表 | 02 / P24 |
| `SensorUnit` | `Automatic`、`NightAids` | 02 2.3 / P25 |
| `EwUnit` | `LurePoint` | 02 2.4 / P25 |
| `DeceptionUnit` | `SeenThrough`、`ReconCheckedThreatIds`、`AttractedThreatIds` | 02 2.4 / P25 |
| `Track` | 见 2.5 全表；`DefId` 恒为 `""` | 02 / P26 |
| `Threat`（02 写） | `HomingUnitId`、`EwEverCovered`、`EwNav`、`EwExtraOffsetM`、`AccuracyTierDrop`、`EwPull`、`EwDivertPos`、`NationalSpoof`、`LinkCutState`、`LinkCutAtTick`、`ArmInitialDistM`、`ArmHitProbMult` | 02 2.6 / P18、P19 |
| `Threat`（01 / 04 写，02 只读） | `TargetUnitId`（`int`，0 = 目标不是我方单位） | 01 / 04 / P18 |

**B. 单例组件**：`SensingState`、`EwState` 的字段（2.7、2.8，P29）。

**C. 子流**：`sensor`（误报）、`fusion`（诱饵甄别）、`ew`（电子战判定）、`exposure`（假发射车识破）按 3.1.4 使用；`emission`、`setup` 本文件不消耗（P32）。

**D. 事件字段定稿**（00 的 4.2 总表，P33、P34）：

| 事件 | 定稿字段 |
|---|---|
| `EarlyWarning` | `string WaveId, string EntryId, double ExpectedAtSec, double BearingRad, bool Ballistic` |
| `TrackLost` | 追加 `TrackLostCause Cause` |
| `EwDiverted` | `int ThreatId, int SourceId, EwDivertKind Kind`（`SourceId` 在 `NationalSpoof` 时为 `SupportAsset.Id`） |
| `EwLinkCut` | `int ThreatId, int SourceId, LinkCutOutcome Outcome, string DefId`（悬停超时坠毁时 `SourceId = 0`） |
| `ExposureThresholdCrossed` | `Threshold` 为 `double`；追加 `ExposureConsequence Consequence` |
| `DeceptionTriggered` | 追加 `DeceptionOutcome Outcome` |
| `EmitterSwitched` | `Cause` 类型为 `EmitterSwitchCause`（4.1） |
| `PlayerUnitDestroyed`（03） | `int UnitId, string DefId, PlayerUnitCategory Category, Vec2 Pos` |
| `UnitDeployStateChanged`（04） | 追加 `bool CompletedRelocation, bool DestinationScouted, string? DestinationAlternatePositionId` |

**E. 命令字段**：`SetEmissionPolicy`、`SectorEmissionOverride` 见 4.2；`SectorOverrideMode`（P36、P37）。

**F. 数据模型（00 的 1.6）**：`SensorDef`、`EwUnitDef`、`DeceptionUnitDef` 按 1.1–1.3；`TrackRulesDef.DetectionRules`、`EmissionRulesDef`、`ExposureRulesDef`、`EwRulesDef` 按 1.6–1.9；`AirDefenseUnitDef` 追加 `FireControlRadar`、`SelfAcquisitionRangeM`、`SelfAcquisition`；`WeaponDef` 追加 `ReactionSec`；`MunitionDef` 追加 `RadioLinked`、`AiVisionActive`；`PlatformDef` 追加 `Behavior`、`RadioLinked`、`ReconQuality`；`SupportDef` 追加 `RadiusM`、`AffectsSameAsEwUnitId`、`AccuracyTierDrop`；`PositionRulesDef` 追加 `Deception`（P09、P12、P15、P17）。

**G. 新增数据字段（data/ 与 Schema，由 D3 更新）**：

| 文件 | 字段 |
|---|---|
| `rules/terrain.json` | `defaultAntennaHeightM`、`earthRadiusM`、`refractionK`、`losSampleStepPx`、`horizonAzimuthBins`、`horizonRangeStepM` |
| `rules/tracks.json` | `detectionRules { … }`（1.6 表） |
| `rules/emission.json` | `defaultStrategy`、`dutyCycleDefaultOnGameSec`、`dutyCycleDefaultOffGameSec`、`decoyLeadGameSec`、`defaultReferenceRangeKm` |
| `rules/ew.json` | `linkCutOutcomeWeights`、`hoverBeforeCrashGameSec`、`belowFullStrengthMult`、`unpoweredEffectMult`、`winterEffectMult`、`urbanNavJamMinGameSec`（并删 `sideEffects.friendlyInterceptorDroneMult`） |
| `rules/exposure.json` | `sensorExposureLevelRatesPerGameSec`、`ewExposureLevelRatesPerGameSec`（并删 `ratesPerGameSec` 中三项重复键） |
| `rules/positions.json` | `deception { fakeLauncherSeeThroughChance, decoyEmitterExposureLevel }` |
| `units/air_defense.json` | `fireControlRadar`、`selfAcquisitionRangeKm`、`selfAcquisition`、`weapons[].reactionGameSec` |
| `units/sensors.json` | `lineOfSight`、`antennaHeightM` |
| `enemies/munitions.json` | `radioLinked`、`aiVisionFrom` |
| `enemies/platforms.json` | `radioLinked`、`reconQuality` |
| `support/support.json` | `national_gnss_spoof.radiusKm` |

**H. 加载器特例与校验（00 的 0.4.2 / 1.2，P05、P06）**：
1. `offsetCellsAdd` → `OffsetAddM`（按 `Cells` 换算）。
2. `configurableOnOffGameSec` 是布尔值：不换算，C# 名 `ConfigurableOnOff`。
3. `sensorExposureLevelRates*`、`ewExposureLevelRates*`：值 ÷ `gameSecToWorldSec`，C# 名加 `PerSec`。
4. `triggers.*` 的字符串按 4 个 enum 解析（`E_ENUM`）。
5. `tracks.qualities` 三个 `id` 各一次（`E_RANGE`）；`exposure.thresholds` 加载后按 `atLeast` 稳定升序。
6. 交叉引用（`E_UNKNOWN_REF`）：`ewUnits[].effectiveAgainst[]`、`ineffectiveAgainst[]`、`sensors[].trackQualityUpgrades[].enemies[]` ∈ 敌方 ID（类别"敌方单位"）；`support[].affectsSameAsEwUnit` ∈ 电子战单位 ID（类别"单位"）；`emission.defaultStrategy` ∈ `strategies[].id`（新类别"辐射策略"）。
7. `Automatic == true && Emission == Active` → `E_RANGE`；`effect ∈ {link_cut, link_cut_directional}` 缺 `linkCutOutcomes`、`self_protection` 缺 `hitProbMult` → `E_MISSING_FIELD`；`linkCutOutcomeWeights` 之和 ≤ 0 → `E_RANGE`。

**I. `SimConfig` / 部署**：`UnitSettings` 追加 1.11 表中的字段；`PlacedUnit` 追加 `bool FirstNightAtNewPosition`（P44）；创建第 7 步把 `PlacedUnit` 引用写入实体的 `Placement`，并为需要视线的传感器与火控单元预计算 `HorizonProfile`（P20、P46）。

**J. 公共工具与覆盖查询**：`Geo.PointInPolygon`（3.1，P48）；`CoverageQuery`（3.8，供 06 覆盖层与 04 敌方 AI 共用）。

### 8.3 与其他规格的边界

| 对方 | 事项 | 本文件的接口约定 |
|---|---|---|
| 01 | 地形视线接口 | `HorizonProfile.HasLineOfSightAgl(fromPos, toPos, toAltAglM)`（展开及转移完成时由 `TerrainModel.BuildHorizonProfile` 预计算径向最大遮挡斜率包络，B-T2-31 / A-2-26） |
| 01 | 电子战改航 | 02 在判定成功当步调用 `ThreatRouting.Retarget(t, lurePos)`、`ThreatRouting.Hover(t)`、`ThreatRouting.BeginEgress(t)`（A-2-27 / P48） |
| 01 | 剧情追加波次的预警 | 初始化排除 `WaveSpawnRules.IsStoryOnlyWave(night, w) == true` 的波次；当步通过 `WaveDefIndex` 查找 `WaveStarted` 波次并补发预警（A-2-28） |
| 01 / 04 | `Threat.TargetUnitId` 与 `HomingUnitId` | `TargetUnitId` 由 01 / 04 独占写入，02 只读不改；02 维护 `Threat.HomingUnitId`（辐射源关机时置 0，重开时恢复为 `TargetUnitId`，A-2-06 / P18） |
| 03 | 导弹发射资格与火控查询 | 须 `f.Id ∈ Track.PreciseHolderIds`；02 提供 `FireControlQueries.GetTargetFilterMultiplier / GetReactionTimeMultiplier / GetArmHitProbMultiplier`（A-2-05） |
| 03 | 误报航迹与已消失目标 | `ThreatId == 0` 的航迹不得交战；同一步内航迹可能指向已移除目标，须 `TryGet` |
| 03 | 电子战效果的消费 | 落点：`EwExtraOffsetM`、`AccuracyTierDrop`（两者不叠加，B-T3-08）、`EwDivertPos`；反辐射导弹命中：`GetArmHitProbMultiplier`；车载防护罩：`EwQueries.ShieldHitProbMult`；友军干扰：`EwQueries.IsInFriendlyEwZone` + `intercept.json` 修正项；电子战坠毁统计监听 `EwLinkCut { Outcome = Crash, DefId }`（含悬停超时，A-4-04） |
| 03 | 国家级导航欺骗 | 03 的 `SupportAsset` 提供 `State == SupportAssetState.Active`、`CenterPos`、`RadiusM`（A-2-21）；02 实现效果 |
| 03 | 字段 / 事件 | `Interceptor.FireUnitId`；`PlayerUnitDestroyed { UnitId, DefId, Category, Pos }`；`FireUnit.RadarDestroyed`；`WeaponDef.ReactionSec` 两边共用 |
| 03 / 05 | 结算 | 城市资源：`Ew.UrbanNavJamSec ≥ UrbanNavJamMinSec` → 城市资源 −1（B-T2-36）；暴露度汇总读 `Exposure` / `ExposurePeak` |
| 04 | 转移 | 执行 `PendingRelocationAltId`；转移完成时发 `UnitDeployStateChanged` 并填 `CompletedRelocation`、`DestinationScouted`、`DestinationAlternatePositionId` |
| 04 | 二选一 | 收到 `ArmThreatDetected` 可发起二选一；回答静默时在阶段 0 调用 `EmissionChoiceEffects.ApplyArmChoice(state, unitId, silence: true)`（0 点指挥点，A-2-11） |
| 04 | 部署校验与指挥点 | `DeploymentValidator` 校验 `UnitSettings`（策略可用性用 `EmissionPolicyRules.CheckAvailable`）；运行时辐射命令在阶段 0 经 `CommandPointRules` 校验并扣减指挥点（A-2-17） |
| 04 | 暴露度后果与条令 | 消费 `ExposureThresholdCrossed` / `ExposurePeak`；排除 `SeenThrough` 的假发射车；传入 `CarryIn.ActiveDoctrineId`（`forward_ambush`、`fire_group_network`，A-2-22） |
| 05 | 跨夜与敌情档案 | `CarryIn` 的暴露度初值、`FirstNightAtNewPosition`、`ActiveDoctrineId`、`CarryIn.Dossier`（`DecoyIdentificationBonus`），假发射车的 `durationNights`、`SeenThrough` |
| 06 | 覆盖层预览 | 调用 `CoverageQuery.ComputeGrid(level, terrain, nightIndex, unit, targetAglM, grid)` 返回三态 `byte[]?`（`0 = 名义距离外, 1 = 距离内盲区, 2 = 可探测`；§3.8，A-2-16 / C-T1-12） |

