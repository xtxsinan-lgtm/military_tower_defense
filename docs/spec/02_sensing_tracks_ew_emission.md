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
    // 已在圆内（含边界）→ 0；永不进入 → null
    public static double? TimeToEnterRadius(Vec2 p, Vec2 v, Vec2 c, double r)
    {
        Vec2 d = p - c;
        double cc = d.LengthSquared() - r * r;
        if (cc <= 0) return 0.0;
        double a = v.LengthSquared();
        if (a == 0) return null;
        double b = 2 * d.Dot(v);
        double disc = b * b - 4 * a * cc;
        if (disc < 0) return null;
        double t = (-b - Math.Sqrt(disc)) / (2 * a);
        return t >= 0 ? t : null;
    }
}
```

- `Geo.PointInPolygon(Vec2 p, IReadOnlyList<Vec2> poly)`：交叉数法（射线向 +x），顶点按数据顺序，`(yi > p.Y) != (yj > p.Y)` 且 `p.X < (xj − xi) × (p.Y − yi) / (yj − yi) + xi` 时翻转。点恰在边上的结果未定义，测试不得依赖（建议登记到 00 的 `Geo`，03 也要用）。
- `InUrban(p)` = 任一 `Level.Layers.Urban[i].Polygon` 包含 `p`（按数据顺序检查，找到即停）。
- **事件游标读取**（6 号、11 号系统共用）：系统需要消费"可能由更晚系统产生"的事件时，按 `Seq` 升序遍历 `ctx.Events.PreviousStep` 再遍历 `ctx.Events.CurrentStep`，只处理 `Seq > cursor` 的事件，处理完把 cursor 设为已处理的最大 `Seq`。这样每个事件恰好被处理一次，与产生它的系统序号无关。
- **辐射源状态的时序**：3 号（探测）与 5 号（电子战）读取的 `Emitter.On` 是**上一步** 6 号系统（或 `Initialize`）的结果；11 号（暴露度）读取的是**本步** 6 号系统的结果。这是 01.B 固定顺序的直接后果，不做补偿。
- 遍历顺序：实体按 ID 升序；跨实体类型时按 `EntityKind` 值升序（`FireUnit` → `SensorUnit` → `EwUnit` → `DeceptionUnit`）。

### 3.2 `SensorSystem`（Order 3，子流 `sensor`）

#### 3.2.1 `Initialize`

1. **自动探测单位**：对 `Catalog.Sensors` 按数据顺序，`Automatic == true` 且（`Meta.Number == null` 或 `FirstAvailable?.Level == null` 或 `FirstAvailable.Level ≤ Meta.Number`）的每个定义，`Sensors.Add` 一个实体：`DefId = Id`、`Pos = (WidthM / 2, HeightM / 2)`、`AltM = 0`、`DeployState = Deployed`、`Exposure = 0`、`Automatic = true`、`Placement = null`、`Emitter = null`（自动单位都是被动的；若数据中出现 `Automatic && Emission == Active`，加载器报 `E_RANGE`）。（Q25）
2. **所有我方单位的本文件字段**（按 `EntityKind` 再按 ID 升序）：按 2.1–2.4 的初值填写；`Emitter` 的 `PolicyId` 若设置值不是已知策略 ID，抛 `SimSetupException`（04 的校验应已拦截）。
3. **预警时间表** `WarningSchedule`：对本夜 `night.Waves` 按数据顺序，每个波次内按 `Groups` 数据顺序收集**首次出现**的 `EntryId`；对每个 `(wave, entryId)`：
   - `entry = Waves.EntryPoints` 中该 ID；`entry.WarningSec == null` → 跳过。
   - `ExpectedAtSec = wave.AtSec`；`Tick = max(1, SecToTicksFloor(max(0, wave.AtSec − entry.WarningSec), StepSec))`。
   - `BearingRad = Geo.BearingRad(mapCenter, entry.Pos)`，`mapCenter = (WidthM / 2, HeightM / 2)`。
   - `Ballistic` = 该波次中 `EntryId == entry.Id` 的任一组，其敌方定义的 `Tag ∈ { BM, HBM }`。
   - 结果列表按 `(Tick, 波次数据下标, 入口首次出现顺序)` 排序（稳定）。

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

`SensorActive(s)`：`s.DeployState == Deployed` 且（`s.Emitter == null` 或 `s.Emitter.On`）。

对某个目标 `t` 的**有效探测距离**（仅 `DetectionRangeM != null` 的单位）：

```
R = s.Def.DetectionRangeM
if s.Def.NightRangeMult != null:                                   # 光学传感器
    nightMult = (s.NightAids ∩ s.Def.NightPenaltyNegatedBy 非空) ? 1.0 : s.Def.NightRangeMult
    weatherMult = night.Weather == null ? 1.0 : Detection.OpticalWeatherRangeMult[night.Weather]
    R = R × nightMult × weatherMult
if s.Emitter != null and not s.Powered:  R = R × Detection.UnpoweredActiveRangeMult
if s.NewPositionPenalty:                 R = R × Positions.NewUnsurveyed.FirstNightEfficiencyMult
if t.AltM < Detection.LowAltitudeBelowM:
    R = R × Detection.LowAltitudeRangeMult[s.Def.LowAltitude]
    if s.Def.LargeLowAltitudeBlindZone == true: R = R × Detection.LargeBlindZoneLowAltitudeRangeMult
```

- 乘法按上面书写顺序逐个执行（保证二进制可复现）。
- 夜晚：本文件把每个 `NightDef` 都视为夜间（Q26）；白天关卡由 WS01-026 引入后改为读取昼夜标记。

#### 3.2.4 `RangeDetect(s)`（有探测距离的单位）

对每个 `Threat t`（ID 升序，Alive）：

1. `s.Def.OnlyDetects == RadioLinkedDrones` 且 `t` 的定义 `RadioLinked != true` → 跳过。
2. `R` = 3.2.3；`!WithinRange(s.Pos, t.Pos, R)` → 跳过。
3. 视线：`s.Def.LineOfSight != false` 且 `s.Def.Layer != National` 时，要求 `TerrainQuery.HasLineOfSight(s.Pos, h, t.Pos, t.AltM)`，`h = s.Def.AntennaHeightM ?? Detection.SensorHeightM`；不通 → 跳过。
4. 质量 `q = s.Def.TrackQuality`；对 `TrackQualityUpgrades` 每一项（数据顺序）：
   - `CloseRange`：`WithinRange(s.Pos, t.Pos, R × Detection.CloseRangeFraction)` → `q = max(q, To)`；
   - `LinkedDroneTypes`：`EnemyIds` 包含 `t.DefId` → `q = max(q, To)`。
5. 上限：`q = min(q, Approximate)`（探测单位不产生"精确"，D2；现有数据中也没有输出"精确"的探测单位，Q3）；再若 `BLineApplies(s)`（3.2.7）→ `q = min(q, BLine.MaxTrackQuality)`。
6. 误差圈 `err = Detection.ErrorRadiusM[q] × (s.Def.FastUpdate == true ? Detection.FastUpdateErrorRadiusMult : 1.0)`。
7. `Route(new Detection(s.Id, Sensor, s.Def.Layer, t.Id, 0, t.Pos, t.AltM, t.VelMps, q, err, ctx.TimeSec), delay)`，`delay = max(s.Def.ReportDelay == true ? Detection.ReportDelaySec : 0, BLineApplies(s) ? BLine.RelayDelaySec : 0)`。

#### 3.2.5 火控雷达与自主捕获（`FireControlDetect(f)`）

- **火控雷达**：`f.Def.FireControlRadar != null` 且 `f.DeployState == Deployed` 且 `f.Emitter.On`。有效距离 `R = FireControlRadar.RangeM`，再按 3.2.3 依次乘断电倍率（`!f.Powered`）、新阵地倍率、低空倍率（用 `FireControlRadar.LowAltitude`；火控雷达没有"低空盲区大"标记）。视线必需，天线高度 `FireControlRadar.AntennaHeightM ?? Detection.SensorHeightM`。范围内、视线通的每个目标产生 `Detection(f.Id, FireControl, Local, t.Id, 0, …, Quality = Precise, err = Detection.ErrorRadiusM[Precise], ObservedAtSec = TimeSec)`，不延迟（B 线也不延迟：数值表 1.3"配属的车载雷达"）。
- **自主捕获**（无火控雷达的单位，如单兵导弹、高炮；Q4）：`f.Def.SelfAcquisitionRangeM != null` 且（`f.DeployState == Deployed`，或 `f.DeployState == Moving` 且 `f.Def.FireOnMove != No`）。有效距离 `R = SelfAcquisitionRangeM`（不乘任何倍率），视线必需，不受低空、夜间修正。产生 `Source = SelfAcquisition`、`Quality = Precise` 的探测。被动，不是辐射源。
- 同一火力单元两者都满足时只走火控雷达分支。

#### 3.2.6 覆盖型单位（`CoverageDetect(s)`）

对每个目标 `t`（ID 升序）：

1. 低空：`t.AltM < LowAltitudeBelowM` 且 `s.Def.LowAltitude < Detection.CoverageLowAltitudeMinCapability`（按 enum 整数值比较）→ 跳过。
2. `FullMap`：不检查位置（含地图外）。`UrbanAreas`：要求 `InUrban(t.Pos)`。
3. `OnlyDetects`、升级规则与质量上限同 3.2.4 第 1、4、5 步（`CloseRange` 对覆盖型单位不适用，跳过）；不检查视线。
4. 产生探测：`Layer = s.Def.Layer`，延迟规则同 3.2.4 第 7 步（民众上报 `ReportDelay == true` → 延迟 `ReportDelaySec`）。

#### 3.2.7 B 线空情转发

`BLineApplies(s)` = `Meta.Protagonist == B` 且 `s.Def.Layer == Regional`。（`AB` 视为 A：终章 A 直接控制区域雷达网。）
- 效果：该单位的探测延迟 `BLine.RelayDelaySec` 送达、质量不超过 `BLine.MaxTrackQuality`。
- `BLine.RegionalRadarDirectControl == false` 时，对这些单位的 `SetEmissionPolicy` 拒绝（`NotAvailable`，3.5.8）；它们按部署时的设置运行（关卡设计者预置）。（Q28）

`DeliverDelayed()`：取出 `Delayed` 中全部 `DeliverTick ≤ Tick` 的条目（列表已按 `(DeliverTick, Seq)` 有序），按此顺序追加到 `Detections`。延迟探测**保留观测时的位置与时刻**（`ObservedAtSec`），不外推。来源单位此后被摧毁、或目标已被移除，延迟探测照常送达（目标已移除的会在 3.3.2 被丢弃）。

#### 3.2.8 国家预警 `EmitEarlyWarnings()`

1. 对 `WarningSchedule` 中 `Tick ≤ ctx.Tick` 且键 `"<WaveId>|<EntryId>"` 不在 `WarnedKeys` 中的条目（按表顺序）：发出 `EarlyWarning { WaveId, EntryId, ExpectedAtSec, BearingRad, Ballistic }`，加入 `WarnedKeys`。
2. 剧情追加的波次（不在本夜 `night.Waves` 中、由 01 运行时生成）：在 `CurrentStep` 中看到 `WaveStarted { WaveId }` 且该波次的任一 `(WaveId, EntryId)` 键未预警时，立即按第 1 步发出（`ExpectedAtSec = TimeSec`），即零提前量。（01 需在 `WaveStarted` 之后能查到该波次的 `WaveDef`；见 8.3。）
3. 预警**不创建航迹**：模糊航迹只来自探测（国家预警网自动单位会在目标进入其覆盖后提供模糊探测）。

#### 3.2.9 误报 `FalseAlarms()`

对每个 `SensorActive` 且 `Def.FalseAlarms != null` 的探测单位（ID 升序）：

1. `p = Detection.FalseAlarmsPerSec[Def.FalseAlarms] × StepSec`；`if (!rng.Chance(p)) continue;`（每个单位每步恰好消耗 1 次 `NextDouble`）。
2. 位置：
   - 有探测距离：`u1 = rng.NextDouble(); u2 = rng.NextDouble()`；`r = R0 × Math.Sqrt(u1)`（`R0` = 3.2.3 中**不含低空项**的有效距离），`b = 2π × u2`；`pos = s.Pos + (r × Math.Sin(b), r × Math.Cos(b))`。
   - `UrbanAreas`：`i = rng.NextInt(0, Urban.Count)`（`Urban.Count == 0` → 不产生误报，但第 1 步的 `Chance` 已消耗）；在该多边形的轴对齐包围盒内最多尝试 8 次：`x = minX + (maxX − minX) × rng.NextDouble()`，`y = minY + (maxY − minY) × rng.NextDouble()`，`PointInPolygon` 为真即采用；8 次都失败 → 采用顶点算术平均值。
   - `FullMap`：（现有数据无此组合）`pos = (WidthM × rng.NextDouble(), HeightM × rng.NextDouble())`。
3. `key = NextPhantomKey++`；`Route(new Detection(s.Id, Sensor, s.Def.Layer, 0, key, pos, AltM: 0, VelMps: (0,0), Quality: q = 3.2.4 第 5 步的上限作用于 s.Def.TrackQuality（不做升级）, err = ErrorRadiusM[q], TimeSec), delay)`（延迟规则同 3.2.4）。

误报航迹只有这一次探测，之后按 3.3.2 超时丢失。

### 3.3 `TrackFusionSystem`（Order 4，子流 `fusion`）

#### 3.3.1 关联方式

按**真实目标**关联：真实探测的键 = `ThreatId`，误报探测的键 = `PhantomKey`。每个键至多一条 Alive 航迹。查找表 `trackByThreat`、`trackByPhantom` 每步由 `Tracks` 重建（`Dictionary` 只查找，不遍历）。

理由：见 0.4 D1。代价是"同一目标被两个相距很远的传感器看到时，界面只显示一条航迹"——这本来就是理想的融合结果。

#### 3.3.2 每步流程

```
# 1. 目标已消失的航迹立即删除
for each Track k (ID 升序): if k.ThreatId != 0 and !Threats.TryGet(k.ThreatId): Remove(k); emit TrackLost{k.Id, ThreatGone}
# 2. 分组：把 Detections 按键分组（丢弃 ThreatId 指向已不存在目标的探测）
#    组的处理顺序：真实键按 ThreatId 升序，然后误报键按 PhantomKey 升序
# 3. 对每组：已有航迹 → Update；没有 → Create
# 4. 本步没有任何探测的航迹 → Coast（3.3.7）
# 5. 诱饵甄别（3.3.8）：对本步 Create / Update 过的航迹，按航迹 ID 升序
```

#### 3.3.3 融合质量

对一组探测 `G`（同一键）：

```
sensorDets  = G 中 Source == Sensor 的探测
preciseDets = G 中 Source ∈ {FireControl, SelfAcquisition} 的探测
localCount  = sensorDets 中 Layer == Local 的不同 SourceId 个数
netQ = sensorDets 为空 ? null : max(sensorDets.Quality)
if netQ == Vague and localCount ≥ ApproximateFromLocalSensorCount: netQ = Approximate     # 交叉升级
Quality = max(netQ ?? Vague, preciseDets 非空 ? Precise : Vague)
NetworkQuality = netQ
LocalSensorCount = localCount
PreciseHolderIds = preciseDets 的 SourceId 去重升序
```

- 交叉升级只把"模糊"升到"大致"，不会到"精确"。国家层、区域层探测单位不计入 `localCount`；火控 / 自主捕获探测不计入。
- 民众上报（一个自动单位）只算 1 个本地传感器。误报探测各自独立成组，永远不会交叉升级。
- 延迟送达的探测与当步新探测一样参与。

#### 3.3.4 "精确"的含义（D2）

- `Quality == Precise` ⇔ 本步至少一个火力单元的火控雷达 / 自主捕获锁定了目标。
- **03 的约定**：火力单元 `f` 用导弹（`MissilesAllowed` 由 `Qualities[Precise]` 给出）交战航迹 `k` 的前提是 `f.Id ∈ k.PreciseHolderIds`；其他单位只能看到"这条航迹是精确的"，不能借用。（需 03 确认，Q3。）

#### 3.3.5 位置、速度、误差圈

- 选中探测 `best`：先 `preciseDets` 中 `SourceId` 最小者；没有则 `sensorDets` 中按（`Quality` 降序，`ObservedAtSec` 降序，`SourceId` 升序）的第一个。
- `Pos = best.Pos`，`AltM = best.AltM`，`VelMps = best.VelMps`，`LastObservedAtSec = best.ObservedAtSec`。
- `ErrorRadiusM`：若 `G` 中存在 `Quality == 航迹 Quality` 的探测 → 其中 `ErrorRadiusM` 的最小值；否则（质量来自交叉升级）→ `Detection.ErrorRadiusM[Quality]`。
- `LastDetectedTick = Tick`。

#### 3.3.6 对外显示的标签

`Tag = Quality ≥ Approximate 且 ThreatId != 0 ? DisplayTag(threat) : null`，其中 `DisplayTag = (threat.Tag == DECOY && !DecoyIdentified) ? Intercept.DecoyUsesColumn : threat.Tag`（未识别的诱饵与无人机外观相同）。甄别成功后同步更新 `Tag`。

#### 3.3.7 创建、更新、外推、丢失

- **Create**：`Tracks.Add`，填 3.3.3–3.3.6 的全部字段，`DefId = ""`；发出 `TrackCreated { TrackId, Quality }`。
- **Update**：重算 3.3.3–3.3.6；`Quality` 变化 → `TrackQualityChanged { TrackId, From, To }`。
- **Coast**（本步无探测）：
  1. `Pos += VelMps × StepSec`；`AltM`、`ErrorRadiusM` 不变；`NetworkQuality = null`；`LocalSensorCount = 0`；`PreciseHolderIds` 清空。
  2. 若 `Quality == Precise` → 改为 `Approximate`（精确需要持续锁定），发 `TrackQualityChanged`；`Tag` 按 3.3.6 重算（仍 ≥ Approximate，标签保留）。
  3. 若 `(Tick − LastDetectedTick) × StepSec > Detection.TrackLostSec`（严格大于）→ `Remove`，发 `TrackLost { TrackId, Timeout }`（误报航迹同样走此路径）。
- 质量**升降都立即生效**（有探测的步）：例如本地交叉的两个传感器之一失去目标，当步即从"大致"降为"模糊"。
- 航迹丢失后目标再次被探测 → 新建航迹（新 ID，甄别状态重置）。

#### 3.3.8 诱饵甄别

只对 `ThreatId != 0`、`!DecoyIdentified` 且目标 `Tag == DECOY` 的航迹（ID 升序）：

```
q = k.Quality
if k.DecoyCheckedQuality != null and q <= k.DecoyCheckedQuality: 跳过         # 每个质量等级最多掷一次；降级不重掷
pNew  = Qualities[q].DecoyDiscrimination
pPrev = k.DecoyCheckedQuality == null ? 0 : Qualities[k.DecoyCheckedQuality].DecoyDiscrimination
k.DecoyCheckedQuality = q
if pNew <= pPrev: 跳过（不消耗随机数）
p = (pNew - pPrev) / (1 - pPrev)                 # 条件概率：累计识别率恰为 pNew（Q33）
if rng.Chance(p): k.DecoyIdentified = true; 重算 Tag; emit DecoyIdentified{k.Id}
```

- 模糊航迹 `pNew = 0` → 不掷（数值表：模糊不能甄别）。
- 只掷"真诱饵"：对非诱饵目标不掷，也不会出现"把真目标误判为诱饵"。
- 在 3.3.2 第 5 步执行，即同一步内先确定质量再甄别。

### 3.4 `ElectronicWarfareSystem`（Order 5，子流 `ew`）

#### 3.4.1 覆盖

电子战单位 `u` 本步**生效**：`u.DeployState == Deployed` 且 `u.Emitter.On`（上一步结果）。
`Covers(u, t)` = `u` 生效 且 `WithinRange(u.Pos, t.Pos, u.Def.RadiusM)`（水平距离，不看高度）且 `u.Def.EffectiveAgainst` 包含 `t.DefId` 且 `!(t 的 MunitionDef?.EwImmune == true)`。

#### 3.4.2 每步流程

```
for each Threat t (ID 升序), Alive:
    HoverTimeout(t)            # 3.4.6：悬停到时 → 坠落移除，continue
    NavEffect(t)               # 3.4.4
    SpoofPull(t)               # 3.4.5
    NationalSpoof(t)           # 3.4.6
    LinkCut(t)                 # 3.4.6（可能移除 t）
UrbanNavJam()                  # 3.4.8
```

每个函数内部的随机数消耗只发生在"满足条件、需要掷骰"时，且每次掷骰恰好 1 次 `Chance`（链路中断成功后再加 1 次 `NextDouble`）。

#### 3.4.3 效能概率

单位 `u` 对目标 `t` 的效果概率：

```
base  = (u.Def.Effect ∈ {NavJam, NavSpoof}) ? Ew.Effectiveness.Nav : Ew.Effectiveness.CounterUas
weak  = (u.Def.FirstAvailable?.FullStrengthLevel != null and Meta.Number != null
         and Meta.Number < u.Def.FirstAvailable.FullStrengthLevel) ? Ew.BelowFullStrengthMult : 1.0
newp  = u.NewPositionPenalty ? Positions.NewUnsurveyed.FirstNightEfficiencyMult : 1.0
ai    = AiVisionMult(u, t)            # 3.4.5；非导航效果恒为 1.0
P(u, t) = base × weak × newp × ai     # 按此顺序相乘
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
    t.EwExtraOffsetM = Accuracy.Tiers[t 的 MunitionDef.Accuracy].EwExtraM    # 数值表 3.1（Q8）
    t.AccuracyTierDrop += u*.Def.AccuracyTierDrop ?? 0
    emit EwDiverted{ t.Id, u*.Id, NavJam }
else:
    t.EwNav = Resisted
```

- 平台（`PlatformDef`）没有精度档：若平台出现在 `EffectiveAgainst` 中，`Applied` 时 `EwExtraOffsetM = 0`（只记录状态）。
- `EwExtraOffsetM` 与 `AccuracyTierDrop` 如何作用于落点由 03 规定（3.1 偏移表 + 降档）。

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
pu = u.Def.PullChance × weak(u) × newp(u) × (t 是 AI 视觉 ? (u.Def.AiVisionEffectMult ?? 1.0) : 1.0)
(u*, p) = argmax pu（并列取 ID 最小）
if p <= 0: return
if rng.Chance(p): t.EwPull = Applied; t.EwDivertPos = u*.LurePoint; emit EwDiverted{ t.Id, u*.Id, NavSpoofPull }
else: t.EwPull = Resisted
```

- 诱导以"导航已被干扰"为前提（同一步内先 `NavEffect` 后 `SpoofPull`，两次掷骰）。`PullChance` 不再乘时期效能（已在 `NavEffect` 中计入，避免重复）。
- **01 的要求**：`EwDivertPos != null` 的目标改为飞向该点，并在该点落地（`ThreatArrived` 的 `Pos` 为该点）；03 在该点结算伤害（数值表 3.6：落入城区仍全额伤害）。

#### 3.4.6 国家级导航欺骗、链路中断、悬停

**国家级导航欺骗**（外部支援的效果；呼叫、延迟、持续时间由 03 的 `ExternalSupportSystem` 管理）：

```
if t.NationalSpoof != None or (t 的 MunitionDef?.EwImmune == true): return
for each SupportAsset a (ID 升序), Alive, a.Active, a 的 SupportDef.Effect == AccuracyDrop:
    ref = Catalog.GetEwUnit(def.AffectsSameAsEwUnitId)
    if ref.EffectiveAgainst 不含 t.DefId or !WithinRange(a.CenterPos, t.Pos, def.RadiusM): continue
    p = Ew.Effectiveness.Nav × ((t 是 AI 视觉 且 NavTerminalIneffectiveVsAiVision) ? 0 : 1)
    if p <= 0: return
    if rng.Chance(p): t.NationalSpoof = Applied; t.AccuracyTierDrop += def.AccuracyTierDrop ?? 0; emit EwDiverted{ t.Id, a.Id, NationalSpoof }
    else: t.NationalSpoof = Resisted
    return                     # 只取第一个覆盖它的支援实体
```

（`SupportAsset.Active`、`CenterPos` 由 03 定义，见 8.3。）

**链路中断** `LinkCut(t)`：

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
    Crash:  emit EwLinkCut{ t.Id, u*.Id, Crash }; Threats.Remove(t.Id)          # 坠毁，不造成伤害（Q10）
    Hover:  t.LinkCutState = Hover; t.LinkCutAtTick = Tick; emit EwLinkCut{…, Hover}
    Return: t.LinkCutState = Return; emit EwLinkCut{…, Return}
```

- `LinkCutDirectional`（单兵反无人机枪）按全向处理（Q35）。
- **01 的要求**：`LinkCutState == Hover` 的目标原地不动（`VelMps = (0,0)`，高度不变）；`Return` 的目标飞回其进入点并在到达后按"离开地图"处理（`ThreatExited`）。两者都仍可被拦截。

`HoverTimeout(t)`：`t.LinkCutState == Hover` 且 `Tick ≥ t.LinkCutAtTick + SecToTicksCeil(Ew.HoverBeforeCrashSec, StepSec)` → `Threats.Remove(t.Id)`（不再发事件），`continue`。

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
- `IsInFriendlyEwZone`：存在生效的 `EwUnit u`（3.4.1，不检查目标），`u.Def.Effect ∈ {NavJam, NavSpoof, LinkCut, LinkCutDirectional}` 且 `WithinRange(u.Pos, pos, u.Def.RadiusM)`。倍率本身由 03 从 `rules/intercept.json` 的 `interceptorDroneInFriendlyEw` 读取（与 `rules/ew.json` 的 `friendlyInterceptorDroneMult` 重复，Q15）。
- `sideEffects.ownDroneLinkCut`：数值表未给概率，本版本不实现（Q15）。

#### 3.4.8 城区导航干扰

`UrbanNavJam()`：若存在生效的 `EwUnit u`，`u.Def.Effect ∈ {NavJam, NavSpoof}` 且 `InUrban(u.Pos)` → `Ew.UrbanNavJamSec += StepSec`（每步至多加一次，与单位个数无关）。
夜晚结束时由 03 / 05 判定：`UrbanNavJamSec ≥ Ew.UrbanNavJamMinSec` → 城市韧性变化 `SideEffects.UrbanNavJamCityResiliencePerNight`（Q14）。

### 3.5 `EmissionSystem`（Order 6，子流 `emission`——本文件规则不消耗随机数）

#### 3.5.1 每步流程

```
ProcessEvents()                    # 3.5.6：游标读取 PlayerUnitDestroyed、InterceptorLaunched、GunFired
ArmScan()                          # 3.5.5 第 1–3 步：初始距离、来袭识别、ArmSilenced
DeceptionAttractScan()             # 3.7.1
for each 辐射源 e（FireUnit → SensorUnit → EwUnit → DeceptionUnit，各自 ID 升序）:
    (on, cause) = Desired(e)       # 3.5.3
    if e.FireUnit: e.Emitter.FcMode = on ? (CueAvailable(e) ? Cued : SelfSearch) : Off     # 3.5.4
    if on != e.Emitter.On: Switch(e, on, cause)
AfterFiringScan()                  # 3.5.6
```

`Switch(e, on, cause)`：`e.Emitter.On = on`；`on` → `OnSinceTick = Tick`，否则 `OnSinceTick = −1`；发出 `EmitterSwitched { UnitId, On, Cause }`；若 `on == false` → `ArmShutdownEffect(e)`（3.5.5 第 4 步）；若 `on == true` → `ArmReacquire(e)`。

#### 3.5.2 策略可用性 `EmissionPolicyRules.CheckAvailable(unit, strategy, level) : CommandRejectReason?`

按顺序检查，第一个不满足的返回：

1. `strategy.Activation == LastMoment`（静默待机）：单位必须是带火控雷达的 `FireUnit` → 否则 `WrongEntityKind`。
2. `strategy.WesternSystemsOnly == true`：`FireControlRadar.Origin == Western`（非火力单元视为不满足）→ 否则 `NotAvailable`。
3. `strategy.AvailableFromLevel != null` 且 `Meta.Number != null` 且 `Meta.Number < AvailableFromLevel` → `NotAvailable`。（`Meta.Number == null` 的测试关卡不受限。）
4. `Requires` 中的 `ApproximateTrack`、`Network`、`Decoy` 是**运行时条件**（3.5.3），不在此检查。

#### 3.5.3 期望状态 `Desired(e)`

按顺序，第一个命中的决定结果：

| # | 条件 | 结果 | `Cause` |
|---|---|---|---|
| 1 | `e.DeployState != Deployed` | 关 | `NotDeployed` |
| 2 | `Forced == Silence` | 关 | `SectorSilence` |
| 3 | `Forced == ForceOn` | 开 | `SectorForceOn` |
| 4 | `ArmSilenced` | 关 | `ArmShutdown` |
| 5 | `TakeoverActive` | 开 | `Takeover` |
| 6 | 按策略 `Activation`（下表） | 开 / 关 | `Policy` |

| `Activation` | 开机条件 |
|---|---|
| `Always` | 恒开 |
| `ApproximateWarning` | `WarnTrack(e)`：存在航迹 `k`，`k.Quality ≥ Approximate` 且 `WithinRange(e.Pos, k.Pos, RefRange(e))` |
| `DutyCycle` | `onT = SecToTicksCeil(DutyOnSec)`，`offT = SecToTicksCeil(DutyOffSec)`（两者 ≥ 1，见 3.5.8），`phase = (Tick − DutyPhaseStartTick) mod (onT + offT)`；`phase < onT` 为开 |
| `LastMoment` | `CueWindow(e)`（3.5.4）；非火力单元恒关 |
| `AfterDecoy` | 若场上**不存在**任何存活的 `FakeEmitter` / `SacrificialEmitter` 欺骗单位 → 等同 `ApproximateWarning`；否则 `WarnTrack(e)` 且存在这样的欺骗单位 `d`：`d.Emitter.On` 且 `d.Emitter.OnSinceTick ≥ 0` 且 `(Tick − d.Emitter.OnSinceTick) × StepSec ≥ DecoyLeadSec` |

`RefRange(e)`：`SensorUnit` → `DetectionRangeM`（覆盖型自动单位不是辐射源，不会出现）；`FireUnit` → `FireControlRadar.RangeM`；`EwUnit` → `RadiusM`；`DeceptionUnit` → `Emission.DefaultReferenceRangeM`。

- 遍历顺序使诱饵（`DeceptionUnit`）在本步晚于其他辐射源被评估："诱饵配合"读取的是诱饵**上一步**的开关状态。这是有意的（诱饵"先"开机）。
- `WarnTrack` 使用的航迹包含本单位自己的贡献（雷达开机后自己维持"大致"，目标离开范围或航迹丢失才关机）。

#### 3.5.4 火控指示联动（WS01-014）

对带火控雷达的火力单元 `f`：

```
CueAvailable(f) = 存在航迹 k：k.NetworkQuality != null 且 k.NetworkQuality ≥ Cueing.Cued.MinTrackQuality
                  且 WithinRange(f.Pos, k.Pos, f.Def.FireControlRadar.RangeM)

CueWindow(f) = Cueing.Cued.FireControlOnlyLastReactionTime 且 存在航迹 k：
      k.NetworkQuality != null 且 k.NetworkQuality ≥ Cueing.Cued.MinTrackQuality
      且 k.Tag != null 且 存在武器 w ∈ f 的武器：w.Targets 含 k.Tag 且 k.AltM ≤ w.CeilingM
      且 τ = TimeToEnterRadius(k.Pos, k.VelMps, f.Pos, Rw) != null 且 τ ≤ ReactionEff(f)
  其中 Rw = w.RangeByTagM?[k.Tag] ?? w.RangeM，对每个满足条件的 w 分别计算，任一满足即可
  ReactionEff(f) = (f.Def.ReactionSec ?? 0) × 当前策略的 ReactionTimeMult
```

- `NetworkQuality` 只统计探测单位（"网络"），**不含**火力单元自己的精确探测，因此火控雷达开机后不会因为自己的锁定而"自我指示"。
- 静默待机的"需'大致'航迹 + 网络"即：没有网络提供的"大致"航迹时，`CueWindow` 恒为假，雷达保持关机（因而无法发射导弹）。
- `FcMode`：开机时 `CueAvailable` 为真 → `Cued`（暴露速率 `FireControlCued`），否则 `SelfSearch`（暴露速率 `FireControlSelfSearch`，03 据此把首发反应时间乘 `Cueing.Uncued.FirstShotReactionTimeMult`）。`FcMode` 与策略无关：常开的火控雷达在有网络覆盖时也按 `Cued` 计（Q6）。
- 反应时间字段 `reactionGameSec` 目前数据中**没有**，需新增（8.2、Q5）。

#### 3.5.5 反辐射导弹与关机时机

反辐射导弹 = `MunitionDef.TracksEmittingRadarOnly == true` 的目标。

1. **初始距离**：对每个存活的反辐射导弹 `m`（ID 升序），若 `m.ArmInitialDistM == 0` 且 `m.TargetUnitId != 0` 且目标单位存活 → `m.ArmInitialDistM = |m.Pos − target.Pos|`（水平），若结果为 0 则取 `1e-9`（避免再次进入此分支）。（"射程"的解释见 Q16。）
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
6. 反辐射导弹的**目标选择**（包括被诱饵吸引、暴露度 ≥ 40 优先）不在本文件，由 01 / 04 写 `TargetUnitId`；命中判定时由 03 乘 `ArmHitProbMult`（`null` 视为 1.0）。

#### 3.5.6 事件消费：开火后转移、主雷达被毁

`ProcessEvents()`（游标 `EmissionEventCursor`，3.1）：

- `InterceptorLaunched { FireUnitId }` / `GunFired { FireUnitId }`：若该火力单元存活且有 `Emitter`（无火控雷达的火力单元没有 `Emitter`，见下注）→ `FiredSinceRelocation = true`，`LastShotTick = 事件.Tick`。
- `PlayerUnitDestroyed { UnitId, Kind, Pos }`：若被毁单位是辐射源型探测单位（`SensorUnit` 且 `Emission == Active`）或带火控雷达的火力单元（依据 `DefId` 查定义判断）→ 对每个存活的辐射源 `U`（ID 升序），`U.Emitter.NeighborTakeover && !U.Emitter.TakeoverActive && WithinRange(U.Pos, 事件.Pos, RefRange(U))` → `U.Emitter.TakeoverActive = true`（本夜一直保持；玩家可用 `SetEmissionPolicy` 清除，3.5.8）。

> 注："开火后转移"设置只对拥有 `Emitter` 的火力单元有效。无火控雷达的火力单元（单兵导弹等）的开火后转移若需要，属于 04 的机动规则（Q19）。

`AfterFiringScan()`：对每个有 `Emitter` 的火力单元 `f`（ID 升序）：
`AfterFiring == RelocateToAlternate` 且 `FiredSinceRelocation` 且 `LastShotTick ≤ Tick − 2`（至少一个整步未开火）且没有存活的自家拦截弹 且 `f.Placement?.AlternatePositionId != null` 且 `f.PendingRelocationAltId == null` → `f.PendingRelocationAltId = f.Placement.AlternatePositionId`，`FiredSinceRelocation = false`。由 04 的部署状态机执行转移并清空该字段。

#### 3.5.7 `Initialize`

对每个辐射源（3.5.1 的顺序）：按 3.5.3 求初值，但此时没有航迹、没有反辐射导弹：`Always` → 开；`DutyCycle` → `phase = 0` → 开；其他 → 关。`DeployState != Deployed` → 关。**不发事件**（`NightStarted` 必须是 `Seq 1`）。开 → `OnSinceTick = 0`；`FcMode`：开 → `SelfSearch`（无航迹），关 → `Off`。

#### 3.5.8 命令

`EmissionSystem` 实现 `ICommandHandler`，处理 `SetEmissionPolicy`、`SectorEmissionOverride`（字段见 4.2）。

**`SetEmissionPolicy` 校验**（按顺序，第一个失败的返回）：

1. `UnitId` 不存在（四类我方存储中都 `TryGet` 失败）→ `UnknownEntity`。
2. 单位没有 `Emitter` → `WrongEntityKind`。
3. `PolicyId` 不是已知策略 → `InvalidArgument`。
4. `CheckAvailable`（3.5.2）失败 → 其返回值。
5. `DutyOnSec` / `DutyOffSec` 给出但 `≤ 0`、非有限值、或 `SecToTicksCeil` 结果 < 1 → `InvalidArgument`。
6. 单位是 `SensorUnit` 且 `BLineApplies` 且 `!BLine.RegionalRadarDirectControl` → `NotAvailable`。

**应用**：`PolicyId` 赋值；可空字段非 null 时覆盖对应 `Emitter` 字段；若新策略 `Activation == DutyCycle` → `DutyPhaseStartTick = ctx.Tick`；`TakeoverActive = false`（玩家重新接管）。开关机在本步 6 号系统中按新策略生效。

**`SectorEmissionOverride` 校验**：`RadiusM` 非有限值或 `≤ 0` → `InvalidArgument`；`Center` 分量非有限值 → `InvalidArgument`。扇区内没有任何辐射源也接受（无操作）。

**应用**：对全部存活辐射源（3.5.1 顺序），`WithinRange(Center, e.Pos, RadiusM)` → `Forced = Mode 对应值`（`Silence` / `ForceOn` / `Cancel → None`）。生效对象在命令应用时确定，单位之后移动出扇区仍保持。指挥点扣除由 04 规定。

### 3.6 `ExposureSystem`（Order 11，子流 `exposure`）

#### 3.6.1 每步流程

```
ProcessEvents()          # 游标 ExposureEventCursor：收集本步要处理的发射次数、转移完成
for each 我方单位 u（FireUnit → SensorUnit → EwUnit → DeceptionUnit，各自 ID 升序），Alive:
    if u 是 SensorUnit 且 u.Automatic: continue          # 自动单位不累积暴露度
    old = u.Exposure
    e = old
    if u 本步完成转移: e = Relocated(e, 事件)            # 3.6.3
    emit  = EmitRate(u)                                  # 3.6.2，每秒
    recon = ReconNearby(u) ? Exposure.RatesPerSec.EnemyReconNearby : 0
    n     = u 本步的导弹发射次数
    rate  = emit + recon
    if emit == 0 and recon == 0 and n == 0: rate = Exposure.RatesPerSec.Silent
    e = Clamp(e + rate × StepSec + n × Exposure.PerMissileLaunched, Exposure.Min, Exposure.Max)
    u.Exposure = e
    u.ExposurePeak = max(u.ExposurePeak, e)
    Thresholds(u, old, e)                                # 3.6.4
FakeLauncherRecon()                                       # 3.7.3（唯一消耗 exposure 子流的地方）
```

加法顺序固定为：`e + rate × StepSec`，再 `+ n × PerMissileLaunched`，最后夹取一次。

#### 3.6.2 辐射速率 `EmitRate(u)`

| 单位 | 条件 | 每秒速率 |
|---|---|---|
| `SensorUnit`（辐射源） | `Emitter.On` | `SensorExposureLevelRatesPerSec[Def.ExposureLevel]` |
| `FireUnit`（有火控） | `Emitter.On` | `FcMode == Cued` → `RatesPerSec.FireControlCued`；`SelfSearch` → `RatesPerSec.FireControlSelfSearch` |
| `EwUnit` | `Emitter.On` | `EwExposureLevelRatesPerSec[Def.EmissionExposure]` |
| `DeceptionUnit`（诱饵辐射源 / 牺牲雷达） | `Emitter.On` | `SensorExposureLevelRatesPerSec[Positions.Deception.DecoyEmitterExposureLevel]` |
| 任意单位（追加项） | `EquipmentEwIds` 中每个装备定义 `d`，且单位 `DeployState != Packed` | `+ EwExposureLevelRatesPerSec[d.EmissionExposure]`（防护罩常开，Q34） |
| 其他 | | 0 |

策略的 `ExposureMult` 与 `cueing.*.exposureMult` **不相乘**（D5、Q6）。

#### 3.6.3 侦察、发射、转移

- `ReconNearby(u)`：存在存活的 `Threat t`，`t.Kind == Platform` 且其 `PlatformDef.Behavior ∈ { Spotter, ArmedRecon }`（Q21），`WithinRange(u.Pos, t.Pos, Exposure.EnemyReconRadiusM)`。多架侦察机只计一次。
- 发射次数 `n`：本步处理的 `InterceptorLaunched { FireUnitId == u.Id }` 中，`WeaponDef.Kind == Missile` 的个数（`Rocket`、`InterceptorDrone`、`GunFired` 不计，Q36）。
- 转移完成：`UnitDeployStateChanged { UnitId == u.Id, To == Deployed, CompletedRelocation == true }`（字段见 8.3）：
  ```
  Relocated(e, ev) = ev.DestinationScouted ? e × OnRelocate.ToScoutedPositionMult : OnRelocate.ResetTo
  u.NewPositionPenalty = !(ev.DestinationAlternatePositionId != null 且 该备用阵地 Surveyed == true)
  ```
- 本步事件只处理一次（游标）；一个单位一步内多次转移完成（不应发生）按事件顺序依次应用。

#### 3.6.4 阈值事件

`Thresholds`（已按 `AtLeast` 升序）：
- 上穿：`old < th.AtLeast ≤ e` 的每个 `th`，**按升序**发出 `ExposureThresholdCrossed { UnitId, Threshold = th.AtLeast, Consequence, Rising = true }`。
- 下穿：`e < th.AtLeast ≤ old` 的每个 `th`，**按降序**发出 `Rising = false`。
- 只比较本步开始与结束的值（转移归零造成的下穿也在此产生）。`Initialize` / `CarryIn` 带入的高暴露度**不**发事件（04 直接读 `Exposure`）。
- 阈值的后果（反辐射导弹优先、次夜已知目标清单、当夜定点打击）由 04 消费；本文件只产生事件并维护 `ExposurePeak`。

### 3.7 欺骗单位与阵地（WS01-016）

#### 3.7.1 诱饵辐射源、牺牲雷达

- 二者都是辐射源（2.1），按辐射策略开关机（缺省 `DefaultStrategyId`），开机时按 3.6.2 累积暴露度——高暴露度让它们成为反辐射导弹 / 侦察的优先目标（目标选择在 04 / 01）。
- 它们**不产生探测**（牺牲雷达不作为真实传感器，Q22）。
- `DeceptionAttractScan()`（6 号系统）：对每个存活的 `Threat t`（ID 升序），`t.TargetUnitId` 指向存活的 `DeceptionUnit d` 且 `t.Id ∉ d.AttractedThreatIds` → 插入（保持升序），发出 `DeceptionTriggered { UnitId = d.Id, ThreatId = t.Id, Outcome = Attracted }`。假发射车同样适用。
- 被命中即销毁（一次性）由 03 的伤害规则处理；`Duration` 的跨夜含义由 05 处理。

#### 3.7.2 查询：当前可被反辐射导弹追踪的辐射源

```csharp
public static class EmitterQueries
{
    // 当前开机的辐射源（FireUnit → SensorUnit → EwUnit → DeceptionUnit，各自 ID 升序）
    public static IReadOnlyList<ActiveEmitter> ListActive(SimState s);
}
public readonly record struct ActiveEmitter(int UnitId, EntityKind Kind, Vec2 Pos, double Exposure, bool IsDecoy);
```

供 04 / 01 实现"只追踪开机雷达"与"诱饵吸引"。`IsDecoy` 对 04 的选择逻辑**不可见**（敌方不知道哪个是诱饵）——仅用于复盘统计；04 必须只依据 `Pos`、`Exposure` 选择。

#### 3.7.3 假发射车 `FakeLauncherRecon()`

对每个存活的 `DeceptionUnit d`（ID 升序），`d.Def.Effect == FakeLauncher` 且 `d.Def.SeeThroughByReconQuality == true` 且 `!d.SeenThrough`：
对每个存活的侦察平台 `t`（3.6.3 的判定，ID 升序），`WithinRange(d.Pos, t.Pos, Exposure.EnemyReconRadiusM)` 且 `t.Id ∉ d.ReconCheckedThreatIds`：

```
插入 t.Id 到 ReconCheckedThreatIds（保持升序）
rq = t 的 PlatformDef.ReconQuality；rq == null → continue（不掷）
if rng.Chance(Positions.Deception.FakeLauncherSeeThroughChance[rq]):
    d.SeenThrough = true; emit DeceptionTriggered{ d.Id, t.Id, SeenThrough }; break
```

- 每架侦察机对每个假发射车最多掷一次；识破后不再掷。
- 未识破时，假发射车与真单位一样累积侦察暴露度（3.6.3），从而进入 04 的已知目标清单、吸引伊斯坎德尔 / Lancet；识破后 04 应将其排除（`SeenThrough`）。

#### 3.7.4 备用阵地 / 新阵地

- `NewPositionPenalty` 的来源：开局 `Placement.FirstNightAtNewPosition`（05 在白天转移到未勘察阵地后置 true）；夜间转移完成时按 3.6.3 重算。
- 效果：本文件中——探测单位与火控雷达的有效距离（3.2.3、3.2.5）、电子战效能概率（3.4.3）乘 `NewUnsurveyed.FirstNightEfficiencyMult`；火力单元的拦截概率由 03 乘 `intercept.modifiers.newPositionFirstNight`（Q23）。
- `preparedAlternate.deployTimeMult`（展开时间 −50%）由 04 的部署状态机使用。

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
| 205 | `EmitterSwitched` | `int UnitId, bool On, EmitterSwitchCause Cause`；`EmitterSwitchCause { Policy = 0, SectorSilence = 1, SectorForceOn = 2, ArmShutdown = 3, Takeover = 4, NotDeployed = 5 }` | 6 | 3.5.1（`Initialize` 不发） |
| 206 | `ArmThreatDetected` | `int TrackId, int TargetUnitId` | 6 | 3.5.5 第 2 步，每条航迹一次 |
| 207 | `EwDiverted` | `int ThreatId, int EwUnitId, EwDivertKind Kind`；`EwDivertKind { NavJam = 0, NavSpoofPull = 1, NationalSpoof = 2 }`；`NationalSpoof` 时 `EwUnitId` 为 `SupportAsset` 的实体 ID | 5 | 3.4.4–3.4.6，只在成功时 |
| 208 | `EwLinkCut` | `int ThreatId, int EwUnitId, LinkCutOutcome Outcome` | 5 | 3.4.6，只在成功时 |
| 209 | `ExposureThresholdCrossed` | `int UnitId, double Threshold, ExposureConsequence Consequence, bool Rising` | 11 | 3.6.4 |
| 210 | `DeceptionTriggered` | `int UnitId, int ThreatId, DeceptionOutcome Outcome`；`DeceptionOutcome { Attracted = 0, SeenThrough = 1 }` | 6（Attracted）、11（SeenThrough） | 3.7.1、3.7.3 |

同一系统一步内的事件顺序 = 伪代码中的执行顺序（实体按 ID 升序）。全部事件 `AtSec = null`（发生在步末时刻）。

### 4.2 本文件处理的命令

| 值 | 命令 | 字段 | 校验 / 应用 | 生效时刻 |
|---|---|---|---|---|
| 200 | `SetEmissionPolicy` | `int UnitId, string PolicyId, double? DutyOnSec, double? DutyOffSec, ArmResponse? OnArmIncoming, AfterFiringAction? AfterFiring, bool? NeighborTakeover` | 3.5.8 | `EffectiveTick` 的阶段 0；当步 6 号系统按新策略决定开关 |
| 201 | `SectorEmissionOverride` | `Vec2 Center, double RadiusM, SectorOverrideMode Mode`；`SectorOverrideMode { Silence = 0, ForceOn = 1, Cancel = 2 }` | 3.5.8 | 同上 |

拒绝原因只使用 00 的公共原因（`UnknownEntity`、`WrongEntityKind`、`InvalidArgument`、`NotAvailable`）。是否消耗指挥点、消耗多少由 04 规定（处理者在 `Apply` 前调用 04 提供的扣点接口；本文件不定义）。

### 4.3 本文件消费的其他事件 / 字段

| 来源 | 事件 / 字段 | 用途 |
|---|---|---|
| 01 | `WaveStarted { WaveId }` | 剧情追加波次的零提前量预警（3.2.8） |
| 03 | `InterceptorLaunched { FireUnitId, WeaponId }`、`GunFired { FireUnitId }` | 开火后转移（3.5.6）、发射暴露（3.6.3） |
| 03 | `PlayerUnitDestroyed { UnitId, DefId, Kind, Pos }`（`Pos` 需追加，8.3） | 邻近雷达接替（3.5.6） |
| 04 | `UnitDeployStateChanged { UnitId, From, To, CompletedRelocation, DestinationScouted, DestinationAlternatePositionId }`（后三个字段需追加，8.3） | 转移归零 / 减半、新阵地标记（3.6.3） |
| 03 | `Interceptor.FireUnitId`（字段） | "完成当前拦截后关机"、开火后转移 |
| 03 | `SupportAsset.Active`、`SupportAsset.CenterPos`（字段） | 国家级导航欺骗（3.4.6） |
| 01 / 04 | `Threat.TargetUnitId`（字段） | 反辐射导弹来袭、诱饵吸引 |

---

## 5. 边界情况

| # | 情况 | 处理 |
|---|---|---|
| 1 | 目标恰在探测距离上（`d == R`） | 探测到（`≤`）。电子战半径、侦察半径、扇区半径、参考距离同样含边界 |
| 2 | 目标高度恰等于 `LowAltitudeBelowM` | 不算低空（`AltM <` 才算） |
| 3 | 雷达本步刚关机 | 本步 3 号系统仍按上一步"开"产生探测；下一步起不再探测（3.1 时序） |
| 4 | 探测单位处于展开 / 撤收 / 移动中 | 不探测；辐射源强制关机（`NotDeployed`）；暴露度照常结算（静默衰减、侦察、转移） |
| 5 | 延迟探测送达时来源单位已被摧毁 | 照常送达 |
| 6 | 延迟探测送达时目标已被移除 | 在融合第 2 步丢弃，不创建航迹 |
| 7 | 目标被拦截 / 落地 / 离开 / 坠毁 | 下一步融合第 1 步删除航迹（`ThreatGone`）。同一步内 03 仍可能看到该航迹，须用 `TryGet(ThreatId)` 判断 |
| 8 | 误报航迹（`ThreatId == 0`） | 质量恒为来源单位的输出质量（实际数据中为模糊），不交叉升级、不甄别、按超时丢失；03 必须把 `ThreatId == 0` 的航迹视为"无可拦截目标"（不得发射；Q27） |
| 9 | 同一目标同时被火控雷达和网络看到 | `Quality = Precise`，`NetworkQuality` = 网络部分；位置取火控探测 |
| 10 | 航迹外推期间目标又被探测到 | 正常 Update；外推期间降级的"精确"在重新锁定时恢复 |
| 11 | 诱饵航迹被甄别后丢失、再次出现 | 新航迹重新从未甄别开始 |
| 12 | 诱饵航迹从"精确"降为"大致"再升回"精确" | 不重掷（`DecoyCheckedQuality` 只增不减） |
| 13 | 目标同时位于多个干扰站覆盖内 | 每类效果只掷一次，取概率最大的单位（并列取 ID 最小） |
| 14 | 目标导航干扰判定失败后飞入另一个干扰站 | 不再掷（`Resisted` 锁存，D4） |
| 15 | AI 视觉目标只被区域导航干扰站覆盖（末段无效时期） | 概率 0，不掷，状态保持 `None`；之后被导航欺骗站覆盖时仍可判定 |
| 16 | 导航欺骗站未设诱导点 | 只有落点偏移，无诱导 |
| 17 | `EwImmune` 目标误列在 `EffectiveAgainst` 中 | 免疫优先，不掷 |
| 18 | 链路中断结果为坠落 | 同一步内移除目标；本步后续系统 `TryGet` 失败；不造成地面伤害 |
| 19 | 悬停目标被拦截 | 由 03 正常结算；悬停计时随之失效 |
| 20 | 电子战单位本步关机 | 本步 5 号系统仍按上一步"开"生效（时序） |
| 21 | `SetEmissionPolicy` 指向已被摧毁的单位 | `UnknownEntity` |
| 22 | `SetEmissionPolicy` 指向非辐射源（声学哨、单兵导弹、假发射车） | `WrongEntityKind` |
| 23 | 静默待机设给苏制火控 / 第 5 关 | `NotAvailable`（3.5.2）；部署方案中出现时由 04 的校验报错 |
| 24 | 静默待机但没有网络"大致"航迹 | 雷达一直关机；单位无法获得精确航迹，不能发射导弹 |
| 25 | 扇区强制开机覆盖了"反辐射来袭立即关机" | 强制开机优先（玩家明确命令，3.5.3 第 3 行先于第 4 行） |
| 26 | 扇区命令之后单位移出扇区 | 保持强制状态，直到 `Cancel` 或新的扇区命令覆盖 |
| 27 | 反辐射导弹没有 `TargetUnitId`，或目标不是辐射源 | 不触发来袭处置；不设初始距离 |
| 28 | 反辐射导弹在雷达关机后、雷达重新开机 | `ArmHitProbMult` 清空（3.5.5 第 5 步），下次关机重新计算 |
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

---

## 6. 不变量

`SimConfig.CheckInvariants = true` 时每步末尾检查（追加到 00 的 6.1）：

1. 对所有我方单位：`Min ≤ Exposure ≤ Max`；`ExposurePeak ≥ Exposure`；`ExposurePeak ≤ Max`。
2. 辐射源的 `Emitter.On == true` ⇒ `DeployState == Deployed`。
3. `Emitter.On == true` ⇔ `Emitter.OnSinceTick ≥ 0`；`OnSinceTick ≤ Tick`。
4. `FcMode != Off` ⇔（实体是 `FireUnit` 且 `Emitter.On`）。
5. 每个存活 `Track`：`(ThreatId == 0) != (PhantomKey == 0)`；`ThreatId != 0` ⇒ 不存在另一条存活航迹具有相同 `ThreatId`；`PhantomKey` 同理。
6. 每个存活 `Track`：`Quality == Precise` ⇔ `PreciseHolderIds.Count > 0`；`PreciseHolderIds` 严格升序；`NetworkQuality == null || NetworkQuality ≤ Quality`；`NetworkQuality != Precise`。
7. `DecoyIdentified` ⇒ `DecoyCheckedQuality != null`；`Tag != null` ⇒ `Quality ≥ Approximate`。
8. `ErrorRadiusM ≥ 0`；`LastDetectedTick ≤ Tick`；`(Tick − LastDetectedTick) × StepSec ≤ TrackLostSec`。
9. `Sensing.Delayed` 按 `(DeliverTick, Seq)` 严格升序且全部 `DeliverTick > Tick`（已到期的已送达）。
10. `Threat.EwPull == Applied` ⇒ `EwNav == Applied` 且 `EwDivertPos != null`；`EwDivertPos != null` ⇒ `EwPull == Applied`。
11. `Threat.AccuracyTierDrop ≥ 0`；`EwExtraOffsetM ≥ 0`；`ArmHitProbMult == null || ArmHitProbMult ≥ 0`。
12. `DeceptionUnit.ReconCheckedThreatIds`、`AttractedThreatIds` 严格升序。
13. `Ew.UrbanNavJamSec` 非递减、`≤ Tick × StepSec`。
14. `Sensing.WarnedKeys` 中的键数 ≤ 预警时间表条目数 + 剧情追加波次键数。

---

## 7. 测试用例

> 全部数值由 `/Users/xtxsinan/.gemini/antigravity/brain/efb38ab3-800b-4b7a-9a46-b48259632fd8/scratch/calc_02.py` 计算核对。浮点比较：标"精确"的用 `==`；其余容差 `1e-9`。

### 7.0 夹具与测试替身

**关卡 `mini02`**（`MiniLevelBuilder`）：
- 地图 `20000 × 20000` m；高程图 2×2 像素全 0，`metersPerPixel = 10000`，`minElevationM = 0`，`maxElevationM = 1`（平地，视线恒通）。
- `level.json`：`protagonist = A`，`number = null`，`dateRange.from = 2022-11-15`，部署区覆盖全图，无禁区；`alternatePositions = [{ id: alt_s, positionM: [5000, 5000], surveyed: true }, { id: alt_u, positionM: [6000, 6000], surveyed: false }]`。
- `layers.json`：`urban = [{ id: u1, polygonM: [[8000,8000],[12000,8000],[12000,12000],[8000,12000]], density: dense }]`，其余图层为空。
- `waves.json`：无进入点、一个夜晚 `durationGameSec = 10`，`weather = clear`，无波次（T-02-12 另给）。
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

**防空单位**（省略字段任意合法；`interceptClass: "k"`，`rules/intercept.json` 夹具含类别 `k`）：

| ID | 火控 / 自主捕获 | 反应 | 武器 |
|---|---|---|---|
| `f_sam` | `fireControlRadar: { rangeKm: 8, lowAltitude: "good", origin: "western" }` | `reactionGameSec: 0.1`（6 s） | `w_sam`：`kind missile, rangeKm 6, ceilingKm 5, targets [UAV, CM, SCM]` |
| `f_sov` | `fireControlRadar: { rangeKm: 8, lowAltitude: "good", origin: "soviet" }` | 0.1 | `w_sov`：同 `w_sam` |
| `f_gun` | `selfAcquisitionRangeKm: 2`，无火控 | — | `w_gun`：`kind gun, rangeKm 2, ceilingKm 2, targets [UAV, DECOY]` |

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
 "detection":{"lowAltitudeBelowM":100,"lowAltitudeRangeMult":{"poor":0.25,"medium":0.5,"good":0.75,"very_good":1.0},
   "largeBlindZoneLowAltitudeRangeMult":0.5,"coverageLowAltitudeMinCapability":"good","sensorHeightM":10,
   "closeRangeFraction":0.5,"errorRadiusM":{"vague":2000,"approximate":500,"precise":0},"fastUpdateErrorRadiusMult":0.5,
   "trackLostGameSec":0.05,"falseAlarmsPerGameSec":{"some":0.6,"high":6},"reportDelayGameSec":0.1,
   "opticalWeatherRangeMult":{"clear":1.0,"moonlit":1.5,"low_cloud":0.5,"fog":0.25},"unpoweredActiveRangeMult":0.5}}
// emission.json：strategies 与正式数据相同（5 条），triggers 与正式数据相同，shutdownTiming 与正式数据相同（0.5→0.2，0.25→0.5，0→0.8），
//   另加 "defaultStrategy":"always_on","dutyCycleDefaultOnGameSec":0.05,"dutyCycleDefaultOffGameSec":0.05,"decoyLeadGameSec":0.05,"defaultReferenceRangeKm":10
// exposure.json
{"kind":"exposure","min":0,"max":100,
 "ratesPerGameSec":{"warningRadarSoviet":60,"warningRadarWestern":36,"fireControlSelfSearch":120,"fireControlCued":36,"highPowerEw":60,"silent":-30,"enemyReconNearby":30},
 "perMissileLaunched":5,"enemyReconRadiusKm":5,"onRelocate":{"resetTo":0,"toScoutedPositionMult":0.5},
 "sensorExposureLevelRates":{"high":60,"medium":36,"zero":0,"none":0},"ewExposureLevelRates":{"high":60,"medium":36,"low":18},
 "thresholds":[{"atLeast":70,"consequence":"known_target_list_next_night"},{"atLeast":40,"consequence":"anti_radiation_priority_tonight"},{"atLeast":100,"consequence":"precision_strike_tonight"}]}
// ew.json
{"kind":"ew",
 "effectivenessByPeriod":[{"from":"2022-02","nav":0.5,"counterUas":0.8},{"from":"2025-03","nav":0.5,"counterUas":0.8,"navTerminalIneffectiveVsAiVision":true}],
 "sideEffects":{"friendlyInterceptorDroneMult":0.6,"ownDroneLinkCut":true,"urbanNavJamCityResiliencePerNight":-1},
 "linkCutOutcomeWeights":{"crash":1,"hover":1,"return":2},"hoverBeforeCrashGameSec":0.05,"belowFullStrengthMult":0.5,"urbanNavJamMinGameSec":1}
// positions.json：preparedAlternate 同正式数据；"newUnsurveyed":{"firstNightEfficiencyMult":0.7}；
//   "deception":{"fakeLauncherSeeThroughChance":{"low":0.1,"medium":0.3,"high":0.6},"decoyEmitterExposureLevel":"high"}
// accuracy.json：tiers 的 ewExtraCells：A 0.5，B 1，C 1.5，D 2（offsetCells 任意合法）
// support.json：含 {"id":"s_nspoof","effect":"accuracy_drop","accuracyTierDrop":2,"affectsSameAsEwUnit":"ew_jam","radiusKm":10,…}
```

注意 `thresholds` 故意乱序，用于验证加载后按 `AtLeast` 升序排列。换算后：`RelayDelaySec = 3`，`TrackLostSec = 3`，`ReportDelaySec = 6`，`FalseAlarmsPerSec = { Some: 0.01, High: 0.1 }`，`DutyCycleDefault* = 3`，`DecoyLeadSec = 3`，`HoverBeforeCrashSec = 3`，`UrbanNavJamMinSec = 60`；暴露速率（每秒）：高 1.0、中 0.6、低 0.3、自行搜索 2.0、指示 0.6、静默 −0.5、侦察 0.5。

**测试替身**（`sim.tests/TestKit`，用 `SimWorld.CreateForTest` 替换）：
- `ScriptedThreats`（替换 Order 1）：按脚本在指定步创建目标（`DefId`、`Kind`、`Pos`、`AltM`、`VelMps`、`Tag` 来自定义、`TargetUnitId`），或移除指定目标，或执行任意状态修改（设置 `DeployState`、`Powered`，创建 / 移除 `Interceptor`、`SupportAsset`）。创建当步的 `Pos` 即脚本给定值。
- `LinearMover`（替换 Order 2）：对 `CreatedTick < Tick` 的目标执行 `Pos += VelMps × StepSec`（不处理悬停 / 返航，悬停测试中速度为 0）。
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

**T-02-04 地形遮挡**
另建地图 `3000 × 3000`，高程图 3×3、`metersPerPixel 1000`、`min 0 / max 1000`，三行像素均为 `[0, 65535, 0]`（中间一列为 1000 m 高的山脊）。部署 `r_reg@(500,1500)`、`s_ac@(1000,1500)`。
- 目标 `AltM 50` 于 `(2500,1500)`：`r_reg` 无探测（视线被挡）；`s_ac`（`lineOfSight: false`，距离 1500）探测到 → 航迹 `Quality == Vague`，`LocalSensorCount == 1`。
- 目标 `AltM 3000` 于同一点、不部署 `s_ac`：`r_reg` 探测到 → `Quality == Approximate`。
（任何合理的 01 视线采样都应得到此结果：山脊处视线高度约 30 m / 1505 m，地形 1000 m。）

**T-02-05 夜间与天气（光学）**
部署 `s_obs@(5000,5000)`，目标 `AltM 500`。

| 情形 | `night.Weather` | `NightAids` | 有效距离 | 探测到 | 探测不到 |
|---|---|---|---|---|---|
| a | `moonlit` | — | 3000 | `(8000,5000)` | `(8000.001,5000)` |
| b | `moonlit` | `[thermal]` | 6000 | `(11000,5000)` | `(11000.001,5000)` |
| c | `fog` | — | 500 | `(5500,5000)` | `(5500.001,5000)` |
| d | `null` | — | 2000 | `(7000,5000)` | `(7000.001,5000)` |
| e | `moonlit` | `[searchlight]`（不在可抵消列表中） | 3000 | `(8000,5000)` | `(8000.001,5000)` |

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
`waves.json`：`entryPoints = [ e1@(30000,10000) warningGameSec 0.5, e2@(10000,30000) warningGameSec 2, e3@(-5000,10000) 无 warningGameSec ]`；第 1 夜 `waves = [ w1 atGameSec 1：groups [m_uav from e1, m_bm from e2, m_uav from e3]；w2 atGameSec 2：groups [m_uav from e1, m_uav from e1] ]`（Order 1 为不生成任何目标的空替身）。运行 120 步，`EarlyWarning` 事件恰为：

| Tick | WaveId | EntryId | ExpectedAtSec | BearingRad | Ballistic |
|---|---|---|---|---|---|
| 1 | w1 | e2 | 60.0 | 0.0 | true |
| 30 | w1 | e1 | 60.0 | 1.5707963267948966 | false |
| 90 | w2 | e1 | 120.0 | 1.5707963267948966 | false |

无航迹产生。

**T-02-13 断电与新阵地**
- `r_reg@(5000,5000)`，脚本在第 1 步开头设 `Powered = false`：目标 `AltM 500` 于 `(10000,5000)` → 有航迹；`(10000.001,5000)` → 无。
- `r_reg` 的 `PlacedUnit.FirstNightAtNewPosition = true`（`Powered = true`）：于 `(12000,5000)` → 有；`(12000.001,5000)` → 无。

**T-02-14 火控雷达与自主捕获**
- `f_sam@(5000,5000)`（`always_on`）；目标 `AltM 500` 于 `(13000,5000)`：第 1 步航迹 `Quality == Precise`、`PreciseHolderIds == [1]`、`NetworkQuality == null`、`ErrorRadiusM == 0`。
- 同上，目标 `AltM 50`：于 `(11000,5000)`（低空倍率 0.75 → 6000）→ 有；`(11000.001,5000)` → 无。
- `f_gun@(5000,5000)`：目标 `AltM 50` 于 `(7000,5000)` → `Precise`、`PreciseHolderIds == [1]`；`f_gun.Emitter == null`；于 `(7000.001,5000)` → 无航迹。

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

**T-02-24 诱饵甄别（两次掷骰）**
部署 `r_reg@(5000,5000)`、`f_sam@(5000,5000)`（策略 `silent_standby`）；`m_decoy` 目标 `AltM 500` 静止于 `(12000,5000)`（距 `f_sam` 7000，在火控距离内、武器射程外，静止 → 不会打开指示窗口）；第 3 步生效 `SectorEmissionOverride{(5000,5000), 100, ForceOn}`。`fusion` 子流脚本 `[0.61, 0.59]`。
- 第 1 步：`Approximate`；掷 `p = 0.5`，`0.61` 失败；`DecoyCheckedQuality == Approximate`；`Tag == UAV`（诱饵显示为无人机）。
- 第 2、3 步：不掷。第 3 步 `f_sam` 开机（`SectorForceOn`）。
- 第 4 步：`Precise`；掷 `p = 0.6000000000000001`，`0.59` 成功 → 事件 `DecoyIdentified{TrackId}`；`Tag == DECOY`；`DecoyCheckedQuality == Precise`。
- 第 5–10 步：不再消耗（脚本已耗尽，不抛异常即通过）。
- 变体：脚本 `[0.49]` → 第 1 步即识别，第 4 步不掷。

**T-02-25 模糊航迹不甄别**
`s_ac@(5000,5000)`，`m_decoy` 于 `(6000,5000)`、`AltM 50`；`fusion` 子流脚本为空。运行 10 步不抛异常；`DecoyIdentified == false`；`Tag == null`。

**T-02-26 位置选择与误差圈**
`r_fast@(5000,5000)`（ID 1）、`r_reg@(5000,6000)`（ID 2）；目标 `AltM 500` 于 `(8000,5000)`：`Quality == Approximate`、`ErrorRadiusM == 250`（取同质量探测的最小值）、`Pos == (8000,5000)`。

**T-02-27 精确 + 网络**
`f_sam@(5000,5000)`、`r_reg@(5000,5000)`；目标 `AltM 500` 于 `(9000,5000)`：`Quality == Precise`、`NetworkQuality == Approximate`、`PreciseHolderIds == [1]`、`ErrorRadiusM == 0`。

### 7.3 电子战（WS01-015）

除注明外：`ew_*@(5000,5000)`（缺省 `always_on`），目标 `AltM 50`、静止，`ew` 子流用 `ScriptedRandom`。

**T-02-30 导航干扰成功**
`ew_jam`；`m_cm` 第 1 步于 `(8000,5000)`；脚本 `[0.4]`。第 1 步：`EwNav == Applied`、`EwExtraOffsetM == 1500.0`（C 档）、`AccuracyTierDrop == 0`；事件 `EwDiverted{ThreatId, 1, NavJam}`。运行到第 6 步不再消耗。

**T-02-31 导航干扰失败后锁存**
同上，脚本 `[0.5]`（不小于 0.5）→ `EwNav == Resisted`、`EwExtraOffsetM == 0`，无事件；第 2–6 步不消耗。

**T-02-32 免疫与无效对象**
`ew_jam`；`m_fiber`（误列在有效对象中但 `ewImmune`）于 `(8000,5000)`、`m_bm` 于 `(8000,5000)`、`m_cm` 于 `(10000.001,5000)`；脚本为空，运行 5 步不抛异常；三者 `EwNav == None`。

**T-02-33 导航欺骗诱导**
`ew_spoof`，`LurePoint (6000,1000)`；`m_cm` 于 `(8000,5000)`。
- 脚本 `[0.1, 0.2]` → `EwNav == Applied`、`EwPull == Applied`、`EwDivertPos == (6000,1000)`；第 1 步事件依次为 `EwDiverted{t, 1, NavJam}`、`EwDiverted{t, 1, NavSpoofPull}`。
- 脚本 `[0.1, 0.3]` → `EwPull == Resisted`、`EwDivertPos == null`，只有 `NavJam` 事件。
- 无 `LurePoint`，脚本 `[0.1]` → 只掷一次。

**T-02-34 AI 视觉目标（2025 年后）**
`level.dateRange.from = 2025-06-01`（解析到第二行：`NavTerminalIneffectiveVsAiVision = true`）。`m_ai` 于 `(8000,5000)`。
- 只部署 `ew_jam`：脚本为空，运行 5 步不抛异常，`EwNav == None`。
- 部署 `ew_jam`（ID 1）与 `ew_spoof`（ID 2，`LurePoint (6000,1000)`）：导航概率 `max(0, 0.25) = 0.25`，生效单位 ID 2；脚本 `[0.24, 0.15]` → `EwNav == Applied`（事件 `EwUnitId == 2`）；诱导概率 `0.3 × 0.5 = 0.15`，`0.15` 不小于 → `EwPull == Resisted`。

**T-02-35 链路中断结果**
`ew_cuas`；`m_fpv` 于 `(6000,5000)`（权重 crash 1 / hover 1 / return 2，总 4）。

| 脚本 | `x = u × 4` | 结果 |
|---|---|---|
| `[0.7, 0.6]` | 2.4 | `LinkCutState == Return`，事件 `EwLinkCut{t, 1, Return}` |
| `[0.7, 0.1]` | 0.4 | 事件 `EwLinkCut{t, 1, Crash}`，同一步目标被移除；第 2 步不再有该目标 |
| `[0.7, 0.3]` | 1.2 | `LinkCutState == Hover`，`LinkCutAtTick == 1` |
| `[0.8]` | — | `0.8` 不小于 `0.8` → `Resisted`，只消耗 1 个值 |

**T-02-36 悬停后坠落**
接 T-02-35 第三行：第 2、3 步目标仍存活；第 4 步（`4 ≥ 1 + 3`）目标被移除，无新事件。加部署 `r_reg@(5000,6000)`：第 5 步事件含 `TrackLost{…, ThreatGone}`。

**T-02-37 时期前弱化与新阵地**
`m_cm` 于 `(8000,5000)`：

| 设置 | 概率 | 脚本 | 结果 |
|---|---|---|---|
| `ew_weak`，`level.number = 4` | 0.25 | `[0.3]` | `Resisted` |
| `ew_weak`，`number = null` | 0.5 | `[0.3]` | `Applied` |
| `ew_weak`，`number = 6` | 0.5 | `[0.3]` | `Applied` |
| `ew_jam`，`FirstNightAtNewPosition = true` | 0.35 | `[0.34]` | `Applied` |
| 同上 | 0.35 | `[0.35]` | `Resisted` |

**T-02-38 国家级导航欺骗（效果）**
脚本第 1 步创建 `SupportAsset{DefId s_nspoof, Active true, CenterPos (5000,5000)}`（ID 记为 a），并创建 `m_cm` 于 `(14000,5000)`；无电子战单位；`ew` 脚本 `[0.3]`。第 1 步：`NationalSpoof == Applied`、`AccuracyTierDrop == 2`、事件 `EwDiverted{t, a, NationalSpoof}`。
- `m_bm`（不在 `ew_jam` 有效对象中）→ 不掷。`Active = false` → 不掷。目标于 `(15000.001,5000)` → 不掷。

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

**T-02-56 反辐射来袭：立即关机与关机时机**
`r = r_reg@(0,10000)`（缺省：`OnArmIncoming = ShutdownImmediately`，ID 1）；`m_arm` 目标 `AltM 5000`，第 1 步于 `(20000,10000)`，`VelMps (−1000,0)`，`TargetUnitId = 1`。
- 第 1 步：`ArmInitialDistM == 20000`。
- 第 11 步（距离恰 10000，首次被探测）：事件依次含 `TrackCreated{k, Approximate}`、`ArmThreatDetected{k, 1}`、`EmitterSwitched{1, false, ArmShutdown}`；`ArmHitProbMult == 0.5`（`f = 0.5`，不满足 > 0.5，取第二档）。
- 第 12 步：`r.On == false`，航迹外推。
- 脚本第 13 步移除导弹：第 13 步事件含 `TrackLost{k, ThreatGone}`、`EmitterSwitched{1, true, Policy}`。
- 变体：导弹第 1 步于 `(16000,10000)` → 第 7 步首次探测并关机，`f = 0.625`，`ArmHitProbMult == 0.2`。

**T-02-57 完成当前拦截后关机**
`f = f_sam@(0,10000)`（`OnArmIncoming = ShutdownAfterCurrentIntercept`，ID 1）；`m_arm` 第 1 步于 `(12000,10000)`，`VelMps (−500,0)`，`TargetUnitId 1`；脚本第 5 步创建 `Interceptor{FireUnitId 1}`，第 12 步移除。
- 第 9 步（距离 8000，火控首次探测）：`ArmThreatDetected`；`ArmPending == true`；`f.On == true`。
- 第 10、11 步：仍开机。
- 第 12 步：`EmitterSwitched{1, false, ArmShutdown}`；`f = 6500 / 12000 = 0.5416…` → `ArmHitProbMult == 0.2`。
- 变体（不创建拦截弹）：第 9 步即关机，`f = 0.6666…` → 0.2。

**T-02-58 继续交战、扇区静默、重新开机**
同 T-02-56，但 `OnArmIncoming = KeepEngaging`；第 19 步生效扇区静默 `{(0,10000), 100, Silence}`，第 20 步生效同扇区 `Cancel`。
- 第 11 步：`ArmThreatDetected{k, 1}`，**无** `EmitterSwitched`。
- 第 19 步：`EmitterSwitched{1, false, SectorSilence}`；距离 2000，`f = 0.1` → `ArmHitProbMult == 0.8`。
- 第 20 步：`EmitterSwitched{1, true, Policy}`；`ArmHitProbMult == null`。
- 第 11–20 步只有一个 `ArmThreatDetected`。

**T-02-60 扇区命令**
`A = r_reg@(5000,5000)`（ID 1）、`B = r_reg@(10000,5000)`（ID 2）、`C = r_reg@(10001,5000)`（ID 3，`on_warning`）。
- 第 5 步 `{(5000,5000), 5000, Silence}`：第 5 步 `EmitterSwitched{1, false, SectorSilence}`、`{2, false, SectorSilence}`；`C` 不受影响（距离 5001）。
- 第 8 步 `{(10001,5000), 1, ForceOn}`：`B`（距离 1，含边界）与 `C` 都在扇区内 → 第 8 步事件依次为 `EmitterSwitched{2, true, SectorForceOn}`、`{3, true, SectorForceOn}`。
- 第 10 步 `{(5000,5000), 6000, Cancel}`（三者都在扇区内）：事件依次为 `{1, true, Policy}`、`{3, false, Policy}`；`B` 由强制开机回到策略 `always_on`，状态未变，无事件。
- `RadiusM = 0` 或 `NaN` → `CommandRejected(InvalidArgument)`。

**T-02-61 主雷达被毁，邻近雷达接替**
`A = r_reg@(0,10000)`（ID 1）、`B = r_reg@(5000,10000)`（ID 2，`on_warning`，`NeighborTakeover true`）；`ScriptedEvents` 在第 5 步移除 `A` 并发出 `PlayerUnitDestroyed{UnitId 1, DefId r_reg, Kind SensorUnit, Pos (0,10000)}`。
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

**T-02-64 `SetEmissionPolicy` 校验与应用**
部署 `r = r_reg`（ID 1）、`s = s_ac`（ID 2）。

| 命令 | 结果 |
|---|---|
| `{999, "always_on"}` | `UnknownEntity` |
| `{2, "always_on"}` | `WrongEntityKind` |
| `{1, "nope"}` | `InvalidArgument` |
| `{1, "intermittent", DutyOnSec 0}` | `InvalidArgument` |
| `{1, "intermittent", DutyOnSec 0.5, DutyOffSec 0.5}` | 接受（各为 1 步） |
| `level.protagonist = B` 时 `{1, "always_on"}` | `NotAvailable` |

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

### 8.1 需要人决定的规则问题

| # | 问题 | 背景 | 建议默认值（理由） |
|---|---|---|---|
| Q1 | 低空能力 `poor / medium / good / very_good` 如何数值化 | Schema 注明"数值化由 WS01-007 决定"；数值表只有定性描述 | 新增 `rules/tracks.json` 的 `detection` 块：`lowAltitudeBelowM = 1000`（Shahed 500–2000 m 部分处于低空，巡航导弹 30–70 m 全程低空）；`lowAltitudeRangeMult = 0.3 / 0.6 / 0.9 / 1.0`；`largeBlindZoneLowAltitudeRangeMult = 0.5`；覆盖型单位低空探测要求 `good` 以上。不模拟地球曲率（地平线效果由倍率概括；若需要再引入雷达地平线公式） |
| Q2 | 航迹关联方式 | 任务要求选一个 | **已定**：按真实 `ThreatId`（D1）。列在此处只为让人知情 |
| Q3 | "精确"是否只对自带火控的火力单元有效（`PreciseHolderIds`），探测单位输出质量是否封顶为"大致" | 数值表 1.3：精确 = 防空系统自带火控雷达；GDD 8.1 火控指示联动 | 是（D2）。03 发射导弹须 `f.Id ∈ PreciseHolderIds`。Schema 允许探测单位输出 `precise`，但模拟中封顶为"大致"；建议 Schema 去掉该取值 |
| Q4 | 无火控雷达的单位（单兵导弹、高炮、火力组、拦截无人机班组）如何获得发射所需的精确航迹 | 质量表：大致航迹 `missilesAllowed = false`；单兵导弹没有雷达却必须能发射 | 新增 `air_defense.json` 可选字段 `selfAcquisitionRangeKm`（被动、需视线、产生精确探测）。建议值 = 该单位最大武器射程；高炮 / 火力组也填（使"模糊航迹 ×0.5"只在射程外的预瞄阶段起作用）；夜间对光学瞄准的影响留给 WS01-026（火力组依赖探照灯） |
| Q5 | 火控雷达参数与系统反应时间从哪里来 | 数据中**没有**火控雷达距离、低空能力、苏 / 西制式、反应时间 | 新增 `fireControlRadar { rangeKm, lowAltitude, origin, antennaHeightM? }` 与 `reactionGameSec`。建议：`rangeKm` = 最大武器射程 × 1.25；`lowAltitude` 近程 `good`、中远程 `medium`；`reactionGameSec` 近程 0.05（3 s）、中程 0.1（6 s）、远程 0.2（12 s）（游戏化，非真实参数）。`reactionGameSec` 03 也使用 |
| Q6 | 辐射策略的 `exposureMult`、`cueing.*.exposureMult` 是否在模拟中相乘 | 状态机已经通过开关机时间体现差异；`0.3 = 0.6 / 2.0` 说明是概括值 | **不相乘**（D5）：暴露度只在开机时按基础速率累积；这些系数供界面提示和自动结算估算。若人决定相乘，需同时决定是否保留真实开关机，否则会重复计算 |
| Q7 | "静默 −0.5"在侦察无人机附近 / 刚发射时是否同时生效 | 若同时生效，"侦察 +0.5（不论是否开机）"与静默正好抵消 | 静默只在本步**没有任何正向来源**（辐射、侦察、发射）时生效 |
| Q8 | 导航干扰的落点偏移按 1.4（单位的 `offsetCellsAdd`，+1～+2 格）还是 3.1（按精度档 `ewExtraCells`：A/B +1、C/D +2）？是否同时"精度档下降" | 数值表 5.3 明确留待 WS01-015 确认 | 按 **3.1**：`EwExtraOffsetM = ewExtraCells[目标原精度档]`；不降档（`accuracyTierDrop` 缺省 0）；`offsetCellsAdd` 仅供界面显示。理由：3.1 已按精度档细分且在 `accuracy.json` 中；两者同时生效会重复计算 |
| Q9 | 电子战效能百分比的含义 | 数值表"效能 70%" | 每个目标、每类效果（导航 / 诱导 / 国家级 / 链路）**只掷一次**，概率 = 效能 × 修正，结果锁存到当夜结束（D4）。替代方案：每步重掷（不推荐） |
| Q10 | 链路中断后坠落 / 悬停 / 返航的权重；悬停多久；坠落是否造成伤害 | Schema 注明"权重由 WS01-015 决定" | 新增 `rules/ew.json`：`linkCutOutcomeWeights = { crash 0.5, hover 0.25, return 0.25 }`，`hoverBeforeCrashGameSec = 2`；坠落不造成地面伤害（小型无人机，且避免"电子战制造伤亡"） |
| Q11 | 哪些敌方弹药属于"AI 视觉制导"；"末段无效"的含义 | 数值表 1.4：2025 春起导航干扰 50%（末段无效）；导航欺骗站对 AI 视觉型效果减半 | 新增弹药字段 `aiVisionFrom`（形态 C 闸门）：建议 `shahed_136` 填 `2025-06`（数值表 C→B 的 AI 升级）、`geran_2_heavy` 填 `2025-03`。末段无效 = 区域导航干扰站对其概率为 0；导航欺骗站 × `aiVisionEffectMult` |
| Q12 | 区域导航干扰站"第 3 关（弱）/ 第 6 关"的"弱"是多少 | `firstAvailable.fullStrengthLevel = 6`，无数值 | 新增 `rules/ew.json` 的 `belowFullStrengthMult = 0.5`，乘在效果概率上 |
| Q13 | 国家级导航欺骗的"某区域"多大、由谁指定 | `support.json` 无半径字段 | 新增 `national_gnss_spoof.radiusKm = 30`；中心点由 `CallSupport` 命令给出（03） |
| Q14 | "城区内长时间开启导航干扰"的"长时间"阈值 | 数值表 1.4 副作用 | 新增 `rules/ew.json` 的 `urbanNavJamMinGameSec = 60`（约为一夜的 1/8）；判定以**干扰站所在位置**在城区多边形内为准 |
| Q15 | 友军干扰倍率在 `intercept.json`（0.6）和 `ew.json`（0.6）重复；"己方无人机链路有概率中断"无概率 | 两处数据 | 03 只读 `intercept.json` 的修正项；`ew.json.sideEffects.friendlyInterceptorDroneMult` 改为仅供界面或删除；己方链路中断本版本不实现，待给出概率 |
| Q16 | 关机时机中"反辐射导弹距离 > 50% 射程"的"射程"是什么 | Kh‑31P 数据没有射程字段 | 取导弹**首次锁定目标时**与目标的水平距离（`ArmInitialDistM`）；分子为关机瞬间的水平距离 |
| Q17 | 各辐射源未设置时的缺省策略与触发规则 | 数据没有缺省 | 新增 `emission.json` 的 `defaultStrategy = "always_on"`；`onAntiRadiationIncoming` 与 `afterFiring` 取各数组第 0 项（`shutdown_immediately`、`stay`）；`NeighborTakeover` 缺省关闭 |
| Q18 | 间歇开机的缺省开 / 关时长；按预警开机的参考距离；诱饵配合的提前量 | 数值表"开 N 秒 / 关 N 秒" | `dutyCycleDefaultOn/OffGameSec = 1 / 1`；参考距离 = 单位自身探测 / 火控 / 作用距离（诱饵用 `defaultReferenceRangeKm = 30`）；`decoyLeadGameSec = 0.25`；场上没有诱饵时"诱饵配合"退化为"按预警开机" |
| Q19 | "开火后转移"的触发时机；无火控雷达单位和间歇开机的"可设置转移"（`canRelocate`）是否也支持 | 数值表 3.5 只给选项 | 有火控的火力单元：开火后至少一整步未再开火、且没有在飞的自家拦截弹时请求转移到其备用阵地；执行由 04 负责。无火控单位与间歇转移本版本不实现，由 04 决定是否作为机动规则加入 |
| Q20 | "主雷达被毁时邻近雷达接替"的含义 | 数值表只有一句 | 设置了 `NeighborTakeover` 的辐射源，在其参考距离内有主动雷达（探测雷达或火控雷达）被毁后，**当夜保持开机**，直到玩家重新设置策略 |
| Q21 | 哪些敌方平台算"侦察无人机（Orlan 等）"；假发射车的"侦察质量" | 数值表 3.4、1.5 | 平台 `behavior ∈ { spotter, armed_recon }` 算侦察；新增平台字段 `reconQuality`（建议 `orlan_10 = medium`、`orion = high`），识破概率 `positions.json` 的 `deception.fakeLauncherSeeThroughChance = { low 0.1, medium 0.3, high 0.6 }` |
| Q22 | 诱饵辐射源 / 牺牲雷达开机时的暴露速率；牺牲雷达是否同时提供探测 | 数值表 1.5 只说"模拟雷达开机" | 暴露速率按 `sensorExposureLevelRates.high`（新增 `positions.json` 的 `deception.decoyEmitterExposureLevel = "high"`）；牺牲雷达不提供探测（它是"吸引火力"的单位）；若需要探测，应改为部署一部真实库存雷达 |
| Q23 | 新阵地首夜 −30% 是否也作用于探测单位和电子战单位 | 数值表 1.5"未完全融入防空网"；3.3 只写拦截概率 | 是：探测 / 火控距离和电子战效果概率 × 0.7；火力单元拦截概率由 03 乘 `newPositionFirstNight` |
| Q24 | 无线电侦测器"只对有链路的无人机"——哪些算有链路 | 数据没有标记 | 新增弹药 / 平台字段 `radioLinked`：建议 `fpv_radio`、`lancet`、`molniya`、`orlan_10`、`orion` 为 true；Shahed 系列、光纤 FPV 为 false |
| Q25 | 自动探测单位（国家预警网、民众上报）何时出现 | 两者 `automatic: true`，`firstAvailable` 分别为第 1、3 关；`test_01` 没有关卡序号 | `level.number == null` 或 `firstAvailable.level ≤ number` 时自动创建；不需要写在 `availableUnits` 里 |
| Q26 | 白天关卡与天气倍率 | 数据没有昼夜标记；GDD 8.8 只有定性描述 | 本版本每夜都按夜间处理（白天由 WS01-026 加 `NightDef` 的昼夜字段）；光学天气倍率 `clear 1.0 / moonlit 1.3 / low_cloud 0.6 / fog 0.3`，只作用于有 `nightRangeMult` 的传感器；探照灯 / 热像来自单位设置 `NightAids`，可用性由 04 校验 |
| Q27 | 误报频率；误报航迹能否被交战 | 数值表"有误报 / 误报率高" | `falseAlarmsPerGameSec = { some 0.02, high 0.1 }`（每个单位）；误报航迹为模糊质量，03 不得对 `ThreatId == 0` 的航迹发射（模糊航迹本来就不能用导弹；高炮浪费弹药的效果不模拟） |
| Q28 | 民众上报的延迟；B 线"空军空情"在模拟中的来源 | 数值表只说"延迟"；B 线没有区域雷达实体的控制权 | `reportDelayGameSec = 0.5`。B 线关卡由关卡设计者在部署方案中预置区域层雷达（代表空军雷达网），其探测延迟 `relayDelayGameSec`、质量上限"大致"，玩家不能改其辐射策略 |
| Q29 | 航迹位置是否加随机误差 | 战争迷雾 | 不加：航迹位置 = 观测时的真实位置（可能因延迟而陈旧）；误差圈只用于显示和 03 的引导判断。理由：确定性好、航迹不抖动 |
| Q30 | 航迹超时丢失时间；精确航迹失锁后的处理 | 数值表没有 | `trackLostGameSec = 1`（60 s）；外推期间精确立即降为大致（精确需要持续锁定） |
| Q31 | 雷达断电后"效能下降"多少 | GDD 8.5 | `unpoweredActiveRangeMult = 0.5`（主动辐射源的探测距离）；断电不强制关机 |
| Q32 | 哪些传感器需要地形视线；天线高度 | 声学探测不受山体遮挡；系留气球很高 | 新增探测单位字段 `lineOfSight`（缺省 true，`acoustic_post` 填 false）与 `antennaHeightM`（缺省 `detection.sensorHeightM = 10`；`tethered_balloon` 建议 300） |
| Q33 | 诱饵甄别在质量升级时如何再掷 | "大致 70% / 精确 95%"是累计识别率还是每次概率 | 每个质量等级最多掷一次，升级时用条件概率 `(p新 − p旧) / (1 − p旧)`，使累计识别率恰为表中数值 |
| Q34 | 车载防护罩如何安装、何时生效、是否累积暴露度 | `equipmentSlot: true`，"不单独占位" | 作为宿主单位的装备（`UnitSettings.EquipmentEwIds`），宿主未撤收时常开，按"低"辐射暴露累积到宿主；命中概率倍率随反无人机效能衰减：`1 − (1 − hitProbMult) × counterUas` |
| Q35 | 单兵反无人机枪的"定向" | 需要朝向 | 本版本按半径内全向处理（半径仅 1 km，差别很小） |
| Q36 | "发射导弹（每发）+5"是否包括火箭（VAMPIRE 的 APKWS）与拦截无人机 | 数值表只说导弹 | 只计 `kind == missile`；火箭、拦截无人机、身管射击不计 |
| Q37 | `sensorExposureLevelRates`、`ewExposureLevelRates` 字段名没有单位后缀，但值是每游戏秒 | 违反 data/README 的后缀约定 | 改名为 `sensorExposureLevelRatesPerGameSec`、`ewExposureLevelRatesPerGameSec`；改名前加载器按特例 ÷ 60 |
| Q38 | `ratesPerGameSec` 中的 `warningRadarSoviet / warningRadarWestern / highPowerEw` 与两张等级速率表重复 | 数值表 3.4 与 5.3 两种写法 | 模拟只用等级速率表（按单位的 `exposureLevel` / `emissionExposure`）；三项保留作文档或删除 |
| Q39 | 敌方反辐射导弹 / 定点打击如何选择目标（诱饵吸引、暴露度 ≥ 40 优先、假发射车吸引伊斯坎德尔 / Lancet） | 欺骗的"效果"取决于敌方选目标 | 不在 02：由 04（敌方 AI）/ 01（`target.mode = air_defense`）实现并写 `Threat.TargetUnitId`；02 提供 `EmitterQueries.ListActive` 与 `DeceptionUnit.SeenThrough` |

### 8.2 需登记到 00_core

**A. 实体字段（00 的 2.4 / 各实体状态表）**

| 表 / 实体 | 新增字段（顺序即哈希顺序） | 规格 |
|---|---|---|
| `PlayerUnitCommon`（四类我方单位） | `Placement`（`PlacedUnit?`，不哈希）、`Emitter`（`EmitterControl?`）、`ExposurePeak`（`double`）、`NewPositionPenalty`（`bool`）、`PendingRelocationAltId`（`string?`，04 执行后清空）、`EquipmentEwIds`（`List<string>`） | 02 2.1 |
| `EmitterControl`（组件类） | 见 2.2 全表 | 02 |
| `SensorUnit` | `Automatic`、`NightAids` | 02 2.3 |
| `EwUnit` | `LurePoint` | 02 2.4 |
| `DeceptionUnit` | `SeenThrough`、`ReconCheckedThreatIds`、`AttractedThreatIds` | 02 2.4 |
| `Track` | 见 2.5 全表；`DefId` 恒为 `""` | 02 |
| `Threat`（02 写） | `EwNav`、`EwExtraOffsetM`、`AccuracyTierDrop`、`EwPull`、`EwDivertPos`、`NationalSpoof`、`LinkCutState`、`LinkCutAtTick`、`ArmInitialDistM`、`ArmHitProbMult` | 02 2.6 |
| `Threat`（01 / 04 写，02 读） | `TargetUnitId`（`int`，0 = 目标不是我方单位） | 01 / 04 |

**B. 单例组件**：`SensingState`、`EwState` 的字段（2.7、2.8），哈希顺序表第 2、3 项已存在，补字段即可。

**C. 子流**：无新增。`sensor`（误报）、`fusion`（诱饵甄别）、`ew`（电子战判定）、`exposure`（假发射车识破）按 3.1.4 使用；`emission` 本文件不消耗；`setup` 本文件不消耗。00 表中 `exposure` 的"预留"改为"假发射车识破"，`emission` 的"反辐射导弹规避判定"改为"预留（本版本不消耗）"。

**D. 事件字段细化**（00 的 4.2 总表"关键字段"列）：

| 事件 | 定稿字段 |
|---|---|
| `EarlyWarning` | `string WaveId, string EntryId, double ExpectedAtSec, double BearingRad, bool Ballistic` |
| `TrackLost` | 追加 `TrackLostCause Cause` |
| `EwDiverted` | 追加 `EwDivertKind Kind`；`EwUnitId` 在 `NationalSpoof` 时为 `SupportAsset` ID |
| `ExposureThresholdCrossed` | `Threshold` 为 `double`；追加 `ExposureConsequence Consequence` |
| `DeceptionTriggered` | 追加 `DeceptionOutcome Outcome` |
| `EmitterSwitched` | `Cause` 类型为 `EmitterSwitchCause`（4.1） |
| `PlayerUnitDestroyed`（03） | **追加 `Vec2 Pos`**（被毁单位当步被压缩，下一步无法再查位置） |
| `UnitDeployStateChanged`（04） | **追加 `bool CompletedRelocation, bool DestinationScouted, string? DestinationAlternatePositionId`** |

**E. 命令字段**：`SetEmissionPolicy`、`SectorEmissionOverride` 见 4.2；新增 enum `SectorOverrideMode`。**拒绝原因**：无新增。

**F. 数据模型（00 的 1.6）**：`SensorDef`、`EwUnitDef`、`DeceptionUnitDef` 按 1.1–1.3 列全字段；`TrackRulesDef`、`EmissionRulesDef`、`ExposureRulesDef`、`EwRulesDef` 按 1.6–1.9；`AirDefenseUnitDef` 追加 `FireControlRadar`、`ReactionSec`、`SelfAcquisitionRangeM`；`MunitionDef` 追加 `RadioLinked`、`AiVisionActive`；`PlatformDef` 追加 `Behavior`（若 01 未列）、`RadioLinked`、`ReconQuality`；`SupportDef` 追加 `RadiusM`、`AffectsSameAsEwUnitId`、`AccuracyTierDrop`；`PositionRulesDef` 追加 `Deception`；`FirstAvailableDef`（公共）。

**G. 新增数据字段（data/ 与 Schema，需人批准后由 WS06 更新）**：

| 文件 | 字段 |
|---|---|
| `rules/tracks.json` | `detection { … }`（1.6 表） |
| `rules/emission.json` | `defaultStrategy`、`dutyCycleDefaultOnGameSec`、`dutyCycleDefaultOffGameSec`、`decoyLeadGameSec`、`defaultReferenceRangeKm` |
| `rules/ew.json` | `linkCutOutcomeWeights`、`hoverBeforeCrashGameSec`、`belowFullStrengthMult`、`urbanNavJamMinGameSec` |
| `rules/positions.json` | `deception { fakeLauncherSeeThroughChance, decoyEmitterExposureLevel }` |
| `units/air_defense.json` | `fireControlRadar`、`reactionGameSec`、`selfAcquisitionRangeKm` |
| `units/sensors.json` | `lineOfSight`、`antennaHeightM` |
| `enemies/munitions.json` | `radioLinked`、`aiVisionFrom` |
| `enemies/platforms.json` | `radioLinked`、`reconQuality` |
| `support/support.json` | `national_gnss_spoof.radiusKm` |

**H. 加载器特例与校验（00 的 0.4.2 / 1.2）**：
1. `offsetCellsAdd` → `OffsetAddM`（`Cells` 不在末尾，按 `Cells` 换算）。
2. `configurableOnOffGameSec` 是布尔值：不换算，C# 名 `ConfigurableOnOff`。建议改名为 `configurableOnOff`。
3. `sensorExposureLevelRates`、`ewExposureLevelRates`：值 ÷ `gameSecToWorldSec`，C# 名加 `PerSec`（Q37）。
4. `triggers.*` 的字符串按 4 个 enum 解析（`E_ENUM`）。
5. `tracks.qualities` 三个 `id` 各一次（`E_RANGE`）；`exposure.thresholds` 加载后按 `atLeast` 稳定升序。
6. 交叉引用（`E_UNKNOWN_REF`）：`ewUnits[].effectiveAgainst[]`、`ineffectiveAgainst[]`、`sensors[].trackQualityUpgrades[].enemies[]` ∈ 敌方 ID（类别"敌方单位"）；`support[].affectsSameAsEwUnit` ∈ 电子战单位 ID（类别"单位"）；`emission.defaultStrategy` ∈ `strategies[].id`（新类别"辐射策略"）。
7. `Automatic == true && Emission == Active` → `E_RANGE`；`effect ∈ {link_cut, link_cut_directional}` 缺 `linkCutOutcomes`、`self_protection` 缺 `hitProbMult` → `E_MISSING_FIELD`；`linkCutOutcomeWeights` 之和 ≤ 0 → `E_RANGE`。

**I. `SimConfig` / 部署**：`UnitSettings` 追加 1.11 表中的字段；`PlacedUnit` 追加 `bool FirstNightAtNewPosition`（缺省 false，由 05 填写）；创建第 7 步把 `PlacedUnit` 引用写入实体的 `Placement`。

**J. 公共工具**：`Geo.PointInPolygon`（3.1，03 的碎片 / 约束区也要用）。

### 8.3 与其他规格的边界

| 对方 | 事项 | 本文件的假设 |
|---|---|---|
| 01 | 地形视线接口 | `TerrainQuery.HasLineOfSight(fromPos, fromAltM, toPos, toAltM)`，高度 AGL；名称以 01 为准 |
| 01 | 电子战改航 | 移动系统读取 `EwDivertPos`（飞向诱导点并在此落地）、`LinkCutState`（`Hover` 原地不动；`Return` 飞回进入点后 `ThreatExited`） |
| 01 | 剧情追加波次的预警 | `WaveStarted` 之后 02 能查到该波次的 `WaveDef`（若追加波次不在 `waves.json` 的本夜列表中，01 需提供查找） |
| 01 / 04 | `Threat.TargetUnitId` 与反辐射导弹 / 定点打击选目标 | 由 01（`target.mode = air_defense`）或 04（已知目标清单、暴露度 ≥ 40 优先）写入；02 只读 |
| 03 | 导弹发射资格 | 须 `f.Id ∈ Track.PreciseHolderIds`（D2、Q3） |
| 03 | 误报航迹 | `ThreatId == 0` 的航迹不得交战 |
| 03 | 已消失目标的航迹 | 同一步内航迹可能指向已移除的目标，须 `TryGet` |
| 03 | 电子战效果的消费 | 落点：`EwExtraOffsetM`、`AccuracyTierDrop`、`EwDivertPos`；反辐射导弹命中：× `ArmHitProbMult`；车载防护罩：`EwQueries.ShieldHitProbMult`；友军干扰：`EwQueries.IsInFriendlyEwZone` + `intercept.json` 修正项；首发反应时间：`Emitter.FcMode == SelfSearch` 时 × `Cueing.Uncued.FirstShotReactionTimeMult`，策略 `ReactionTimeMult` 也由 03 乘 |
| 03 | 国家级导航欺骗 | 03 的 `SupportAsset` 需提供 `Active`（已到位且未结束）与 `CenterPos`（呼叫时指定）；02 实现效果 |
| 03 | 字段 / 事件 | `Interceptor.FireUnitId`；`PlayerUnitDestroyed.Pos`；`reactionGameSec` 两边共用 |
| 03 / 05 | 结算 | 城市韧性：`Ew.UrbanNavJamSec ≥ UrbanNavJamMinSec` → `UrbanNavJamCityResiliencePerNight`；暴露度汇总读 `Exposure` / `ExposurePeak`；电子战坠毁的目标计入"电子战击落"还是"未落地"由 03 定 |
| 04 | 转移 | 执行 `PendingRelocationAltId`；转移完成时发 `UnitDeployStateChanged` 并填 `CompletedRelocation`、`DestinationScouted`、`DestinationAlternatePositionId` |
| 04 | 二选一 | 收到 `ArmThreatDetected` 可发起二选一；回答通过 `SetEmissionPolicy` / `SectorEmissionOverride` 落地（或 04 直接改 `EmitterControl.ArmSilenced`——不推荐，建议走命令） |
| 04 | 部署校验与指挥点 | `DeploymentValidator` 校验 `UnitSettings`（策略可用性用 `EmissionPolicyRules.CheckAvailable`、装备、夜视器材、诱导点在地图内）；两条辐射命令的指挥点消耗 |
| 04 | 暴露度后果 | 消费 `ExposureThresholdCrossed` / `ExposurePeak`；排除 `SeenThrough` 的假发射车；`PositionRulesDef` 在 00 中归 04，02 只读 `newUnsurveyed` 与新增的 `deception` 块 |
| 05 | 跨夜 | `CarryIn` 的暴露度初值、`FirstNightAtNewPosition`、假发射车的 `durationNights`、`SeenThrough` 是否带到次夜 |
| WS01-026 | 天气 / 昼夜 | 本文件只实现光学传感器的夜间与天气倍率；白天关卡、冬季设备效能等由该任务扩展 |
