# D2-A 规格接口与命名一致性审查

> 审查对象：docs/spec/00_core.md … 06_client_graybox.md（只审查，不修改规格）
> 参照：AGENTS.md、docs/spec/README.md、data/schema、data/rules、[B_decisions.md](B_decisions.md)（下文引用其编号 `B-T2-xx` / `B-T3-xx`，不重复裁决）
> 分级：**T1** 技术 / 接口（按建议直接改）· **T2** 设计细节 / 默认值（批量批准）· **T3** 重要设计选择（逐条决定）
> 问题编号：`A-<节>-<序>`。行号均指审查时的版本。

## 目录

1. [00_core 登记补丁表](#1-00_core-登记补丁表)（可直接应用）
2. [跨文件接口对齐](#2-跨文件接口对齐)
3. [术语与字段名](#3-术语与字段名)
4. [Step 顺序与数据流](#4-step-顺序与数据流)
5. [随机数子流](#5-随机数子流)
6. [汇总](#6-汇总)

---

## 1. 00_core 登记补丁表

> 本节把 01–06 各自第 8 节"需登记到 00_core"逐条核对后合并，冲突处给出**唯一**合并结果。格式：`位置（00 的节 / 行）｜操作｜内容｜来源`。
> 应用顺序：先应用第 2–4 节中被标为"改变登记内容"的 T1 结论（已在下表中直接体现，表内注"见 A-x-y"）。
> 本节整体分级 **T1**（登记本身是技术动作；其中依赖 T2 / T3 裁决的行已注明）。

### 1.1 编号冲突的合并结果（先读）

| 冲突 | 各规格的写法 | 合并结果 |
|---|---|---|
| 全局目录新增规则文件的加载序 | 01：movement 21、terrain 22；03：engagement 21、civil 22；04：enemy_ai 23、commands 24（"01 已登记 21、22"） | **21 movement、22 terrain、23 engagement、24 civil、25 enemy_ai、26 commands**（按规格编号、同规格按文中顺序） |
| T-00-35 `LoadedFiles.Count` | 00：29；01：31；03：31；04："再加 2" | **35** = 26 个全局 + 8 个关卡 JSON + 1 个 PNG（05 的 `rules/campaign.json`、`flow.json` 不计入，05 R-00-6） |
| 单例组件哈希序 | 03：`EngagementState`"插在 `SupportState` 之前，或追加为序 10" | **追加为序 10**（00 2.3 / 3.7.2 "只追加、不重排"原则） |
| 拒绝原因 | 03：300–302；其余无新增 | 03 段 `300 NoSortiesLeft`、`301 InRiskZone`、`302 AirbaseUnavailable`；05 的 `CampaignRejectReason` 是**独立 enum**（05 R-00-4），不占 `CommandRejectReason` 的 500 段 |
| 事件值 | 04：新增 408 `EnemyGroupsReleased`；02 建议的终结事件见 A-4-03 | 408 `EnemyGroupsReleased`；**209–210 之后不新增**（A-4-03 复用 208 `EwLinkCut`） |
| `PlayerUnitCommon` 字段的哈希顺序 | 00（4 个）、02（6 个）、03（3 个）、04（2 个，"位于 `DeployState` 之后"）、05（`RosterId`，不哈希） | 见 1.4 合并表 |
| `Threat` 字段的哈希顺序 | 01（32 个）、02（10 个）、03（4 个） | 01 → 02 → 03，另加 A-2-07 的 `EwEverCovered`（02 段末） |
| `CarryIn.KnownTargets` 类型 | 04：`IReadOnlyList<KnownTargetCarry>?`；05：`KnownTargetCarry?`（不透明单对象） | 04 的列表（见 A-2-19） |
| 指挥点奖励字段名 | 04：`CarryIn.BonusCommandPoints`（`int?`）；05：`CommandPointsBonus`（`int`） | `CommandPointsBonus`（`int`，缺省 0；05 拥有 `CarryIn`） |

### 1.2 数据加载（00 第 1 节）

| # | 位置 | 操作 | 内容 | 来源 |
|---|---|---|---|---|
| P01 | 1.1 全局目录表，L304 之后 | 追加 6 行 | `21 rules/movement.json kind movement → MovementRulesDef（01）`；`22 rules/terrain.json kind terrain → TerrainRulesDef（01）`；`23 rules/engagement.json kind engagement → EngagementRulesDef（03）`；`24 rules/civil.json kind civil → CivilRulesDef（03）`；`25 rules/enemy_ai.json kind enemy_ai → EnemyAiRulesDef（04）`；`26 rules/commands.json kind commands → CommandRulesDef（04）` | 01 8.2、03 R-DATA、04 G |
| P02 | 1.1，L320 | 改写 | "`loc/`、`narrative/`、`schema/` 不由模拟层读取；`campaign/`、`rules/campaign.json`、`levels/<id>/flow.json` 不由 `DataLoader.LoadLevel` 读取，由 `CampaignDataLoader`（`sim/Campaign/Data`）读取，不计入 `LevelData.LoadedFiles`" | 05 R-00-6 |
| P03 | 1.2 第 3 条，L326 | 改写 | "`kind` 字段：Schema 要求 `kind` 的文件（`rules/*`、`level_content`、`map/*`、05 的 `campaign/*`）读取并校验；`level.json`、`waves.json`、`units/*`、`enemies/*`、`support/*` 没有 `kind` 字段，不校验"（见 A-2-25） | 审查 |
| P04 | 1.2 第 13 条，L336 末尾 | 追加 | "战斗机武器 ID（`fighters[].weapons[].id`）与防空武器 ID 不得重复" | 03 R-DATA |
| P05 | 1.2 第 15 条，L338 末尾"其他规格可在本表追加"之前 | 追加 | `platforms[].loadout[].options[]` ∈ 弹药 ID（敌方单位）；`ewUnits[].effectiveAgainst[]` / `ineffectiveAgainst[]`、`sensors[].trackQualityUpgrades[].enemies[]` ∈ 敌方 ID；`support[].affectsSameAsEwUnit` ∈ 电子战单位 ID（单位）；`support[].fighterRef` ∈ 战斗机 ID（战斗机）；`support[].fighterWeaponRef` ∈ 该战斗机武器 ID（武器）；`support[].reinforcementUnit`、`coverageUnits[]` ∈ 防空单位 ID（单位）；`fighters[].weapons[].interceptClass` ∈ `intercept.classes`（拦截类别）；`emission.defaultStrategy` ∈ `strategies[].id`（辐射策略）；`events.json` 的 `unit_destroyed.ref` ∈ 单位 ID、`structure_destroyed.ref` ∈ 保护目标 ID、`wave_spawned.ref` / `spawn_wave.wave` ∈ 任一夜波次 ID | 01 V-、02 H6、03 R-DATA、04 H |
| P06 | 1.2，第 16 条之后 | 新增第 17 条"规格追加校验" | 列出：01 V1–V3；02 H5、H7；03（`damage.bands` 覆盖 1–10 不重叠；`defeat`/`victory` 条件类型限制；`restrictedEngagement.reactionTimeMult` 两处相等）；04（1.1.1 范围、`commandPointCosts` 键规则、`commandPointsPerNight ∈ economy 范围`、`events.json` 必填项）。正文仍在各规格，00 只列索引 | 01/02/03/04 |
| P07 | 1.3 错误码表，L375 之后 | 追加 1 行 | `E_NOT_IMPLEMENTED`｜`SimWorld.Create` 时数据用到尚未实现的功能｜`{功能}尚未实现（{任务号}）`（01 4.3 的格式为其实例） | 01 8.2 |
| P08 | 1.3，L385 | 改写 | `E_UNKNOWN_REF` 的 `{类别}` 追加 `战斗机`、`辐射策略` | 02 H6、03 R-DATA |
| P09 | 0.4.2 规则，L166 之后 | 新增第 7 条"加载器特例" | (a) `offsetCellsAdd` → `OffsetAddM`（`Cells` 不在末尾，按 `Cells` 换算）；(b) `configurableOnOffGameSec` 是布尔，不换算，C# 名 `ConfigurableOnOff`；(c) `sensorExposureLevelRates`、`ewExposureLevelRates` 每个值 ÷ `gameSecToWorldSec`，C# 名加 `PerSec`。三者都建议在 data 中改名（见 A-3-04），改名后删除本条 | 02 H1–H3 |
| P10 | 0.4.1 单位表，L141 之后 | 追加 3 行 | `加速度`｜m/s²｜`Mps2`（01 `MotionLeg.VertAccelMps2`）；`比例`｜0–1｜`Frac`（`…Pct` 换算结果、`DamageEfficiencyMult` 之外的份额量）；`每日`（战役层）｜每战役日｜`PerDay`（不换算；`cityResourcePerDay`、05 `dayExposureDecayPerDay`、`structureHpFracPerDay`） | 审查（A-3-03） |

### 1.3 数据模型（00 1.6）

| # | 位置 | 操作 | 内容 | 来源 |
|---|---|---|---|---|
| P11 | `RulesSet`，L596 之后 | 追加 6 个属性 | `MovementRulesDef Movement; // → 01`、`TerrainRulesDef Terrain; // → 01`、`EngagementRulesDef Engagement; // → 03`、`CivilRulesDef Civil; // → 03`、`EnemyAiRulesDef EnemyAi; // → 04`、`CommandRulesDef Commands; // → 04` | 01/03/04 |
| P12 | `RulesSet`，L594 注释 | 改写 | `PositionRulesDef Positions; // → 04（02 读 newUnsurveyed 与新增 deception 块）` | 02 F |
| P13 | `RulesSet`，L596 注释 | 改写 | `EconomyRulesDef Economy; // → 05（historicalEvents 带 Active；追加 Trust、CrossLevelModClamp、CityResource、Supply、Repair、Relocation、EmergencySupport、Requests）` | 05 R-00-7 |
| P14 | `Heightmap`，L543 | 改写 | 存储改为 `double[]`，追加 `internal double[] ElevationArray`（`TerrainModel` 零复制引用） | 01 8.2 |
| P15 | `AirDefenseUnitDef`，L549 | 补注 | `DeployTier`：`enum DeployTier { Instant = 0, Minutes = 1, HoursShort = 2, Hours = 3, Fixed = 4 }`（04）；追加 `FireControlRadarDef? FireControlRadar`、`double? SelfAcquisitionRangeM`（02）；**不**追加单位级 `ReactionSec`（反应时间挂武器，B-T2-01） | 02 F、04 G、B-T2-01 |
| P16 | `WeaponDef`，L561 之后 | 追加 | `double? ReactionSec; double? ShotIntervalSec; double? InterceptorSpeedMps;`（03；`Gun` 不得有 `InterceptorSpeedMps`）；`WeaponKind` 等 enum 的整数值按 03 R-DATA | 03 R-DATA |
| P17 | `SensorDef` / `EwUnitDef` / `DeceptionUnitDef`，L563–565 | 指向 | "全字段见 02 1.1–1.3"；`SensorDef` 含 `bool? LineOfSight`、`double? AntennaHeightM`；公共 `FirstAvailableDef(int? Level, int? FullStrengthLevel, bool? Optional, bool? InfoSourceOnly)` | 02 F |
| P18 | `MunitionDef`，L576 | 追加 | `MunitionCategory Category`、`AltitudeBand AltitudeBand` 的 enum 定义见 01 1.2；追加 `bool? RadioLinked`、`bool AiVisionActive`（02，形态 C 闸门 `aiVisionFrom`）、`bool? StoryEventOnly`（01） | 01、02 |
| P19 | `PlatformDef`，L578 | 替换为 01 1.3 的全字段 record | 另追加 `bool? RadioLinked`、`ReconQuality? ReconQuality`（02）；`LoadoutEntryDef`、`PlatformWhileAliveDef`、`OtherArmament`、`PlatformBehavior` 按 01 | 01、02 |
| P20 | `FighterDef` / `SupportDef`，L579–580 | 指向 | "全字段见 03 1.2、1.3"；`FighterWeaponDef.Kind`（必填）；`SupportDef` 追加 `double? RadiusM`（02，B-T2-04）、`AccuracyTierDrop`、`AffectsSameAsEwUnitId` | 02、03 |
| P21 | `NightDef`，L505 | 追加可选字段 | `bool? BigRaid`（03 Q-S8）、`TimeOfDay? TimeOfDay`（05 R-01-2，`enum TimeOfDay { Night = 0, Day = 1 }`，缺省 `Night`） | 03、05 |
| P22 | `WaveDef` / `WaveGroupDef`，L506–507 | 追加可选字段（**仅在 05 的适应功能批准后**） | `string? AdaptiveTrigger`；`WaveGroupDef` 追加 `string? AdaptiveTrigger`、`IReadOnlyList<AdaptiveSubstituteDef>? AdaptiveSubstitutes` | 05 R-01-1（T2，依赖 WS05-006） |

### 1.4 实体字段（00 2.3 / 2.4）

**`PlayerUnitCommon` 合并后的完整字段表**（替换 00 2.4 中"我方单位"三行；顺序 = 哈希顺序；"不哈希"者不写）：

| 序 | 字段 | C# 类型 | 初值 | 写 | 读 | 来源 |
|---|---|---|---|---|---|---|
| 1 | `DeployState` | `UnitDeployState` | `Deployed` | 0 | 全部 | 00 |
| 2 | `DeployPhaseEndTick` | `int` | −1 | 0 | 0、快照 | 04 |
| 3 | `Relocation` | `RelocationOrder?` | `null` | 0 | 0、快照 | 04 |
| 4 | `Exposure` | `double` | `CarryIn` 或 0 | Create 第 8 步、11 | 02、04、03 | 00 |
| 5 | `ExposurePeak` | `double` | = 初始 `Exposure` | 11 | 03、04 | 02 |
| 6 | `GridNodeId` | `int` | 0 | 10（Initialize） | 02、03 | 00 |
| 7 | `Powered` | `bool` | true | 10 | 02、03 | 00 |
| 8 | `Emitter` | `EmitterControl?` | 02 2.2 | 0、6 | 3、5、6、7、11、04 | 02 |
| 9 | `NewPositionPenalty` | `bool` | `Placement?.FirstNightAtNewPosition ?? false` | 11 | 3、5、7 | 02（A-2-13） |
| 10 | `PendingRelocationAltId` | `string?` | `null` | 6、0 | 0 | 02 |
| 11 | `EquipmentEwIds` | `List<string>` | `Placement?.Settings.EquipmentEwIds` | I | 11、10 | 02 |
| 12 | `DamageEfficiencyMult` | `double` | `CarryIn` 或 1.0 | 10 | 7、02 | 03 |
| 13 | `SuspendedUntilSec` | `double` | 0.0 | 10 | 7、02 | 03 |
| 14 | `LightDamaged` | `bool` | `CarryIn` 或 false | 10 | 05 | 03 |
| — | `Placement` | `PlacedUnit?` | 部署条目；运行时创建 = null | Create 第 7 步 | 全部 | 02（不哈希） |
| — | `RosterId` | `int` | `Placement?.RosterId ?? 0` | Create 第 7 步 | 05、03（`BuildResult`） | 05（不哈希） |

| # | 位置 | 操作 | 内容 | 来源 |
|---|---|---|---|---|
| P23 | 2.4 表，`Threat` 行（L732–735） | 指向 | "`Threat` 全字段：01 2.2（32 项，含 `PendingRelease`）→ 02 2.6（10 项 + `EwEverCovered`）→ 03 2.4（4 项），按此顺序哈希"；`VertSpeedMps` 含义 = `d(AltM)/dt` | 01、02、03、A-2-07 |
| P24 | 2.4 表，`Track` 行（L736–737） | 指向 | "`Track` 全字段见 02 2.5；`DefId` 恒为 `""`" | 02 |
| P25 | 2.3 表 `FireUnit` 行 | 补注 | 03 专有字段 `Weapons`、`RadarDestroyed`、`CrewConsecutiveNights`、`AceCrew`、`Engagement`（**删去** 03 的 `NewPositionFirstNight`，A-2-13） | 03、A-2-13 |
| P26 | 2.3 表其余行 | 补注 | `SensorUnit`：`Automatic`、`NightAids`（02）；`EwUnit`：`LurePoint`（02）；`DeceptionUnit`：`SeenThrough`、`ReconCheckedThreatIds`、`AttractedThreatIds`（02）；`Interceptor` / `SupportAsset` / `Structure` / `GridNode`：03 2.5–2.7（`Interceptor` 追加 `TargetPathVersion`，A-2-09）；`ChoiceRequest`：04 2.2 **去掉 `CreatedTick` 行**（A-3-01） | 02、03、04 |

### 1.5 单例组件与哈希顺序（00 2.5 / 3.7.2）

| # | 位置 | 操作 | 内容 | 来源 |
|---|---|---|---|---|
| P27 | `SimState` 单例块，L781 之后 | 追加 | `public EngagementState Engagement;  // 03：弹药池剩余、已记录的保留原因` | 03 2.8 |
| P28 | 3.7.2 表，L1259 之后 | 追加 | `| 10 | EngagementState | 03 |` | 03 2.8 |
| P29 | 3.7.2 表 1–9 行 | 补注字段来源 | `WaveState` → 01 2.3（`WaveInjection` 追加 `GroupIndices`，04 3.3.0）；`SensingState` / `EwState` → 02 2.7 / 2.8；`CommandState` / `EnemyIntelState` → 04 2.3 / 2.4；`SupportState` / `GridState` / `CivilState` / `ScoringState` → 03 2.8（`ScoringState` 追加 A-4-03、A-2-21 的计数） | 01–04 |

### 1.6 `SimWorld` 流程、`SimContext`、`SimConfig`（00 2.6 / 3.2 / 3.4 / 3.5）

| # | 位置 | 操作 | 内容 | 来源 |
|---|---|---|---|---|
| P30 | `SimContext`，L852 之后 | 追加 | `public TerrainModel Terrain { get; }`、`public IEnemyAiHooks EnemyAiHooks { get; }` | 01 |
| P31 | `SimConfig`，L830 之后 | 追加 | `public bool AutoChoicePrompts { get; init; } = true;`（参与回放）；`[JsonIgnore] public IEnemyAiHooks? EnemyAiHooksOverride { get; init; }`（仅测试，写回放时非 null 抛异常）；`[JsonIgnore] public bool CaptureDebug { get; init; } = false;`（不影响任何系统，06） | 04、01、06 |
| P32 | `PlacedUnit`，L839 之后 | 追加 | `public bool FirstNightAtNewPosition { get; init; }`（05 填）；`public int RosterId { get; init; }`（0 = 非战役单位） | 02 I、05 R-00-1 |
| P33 | `UnitSettings`（L839 注释所指） | 定义 | 字段：02 1.11 全部（`EmissionPolicyId`、`DutyOnSec`、`DutyOffSec`、`OnArmIncoming`、`AfterFiring`、`NeighborTakeover`、`LurePoint`、`NightAids`、`EquipmentEwIds`）+ 03 `UnitEngagementSettings? Engagement` | 02、03 |
| P34 | `CarryIn`，L841 | 替换 | 05 2.4.1 的全集；`KnownTargets` 类型为 `IReadOnlyList<KnownTargetCarry>?`，`KnownTargetCarry(string UnitDefId, Vec2 Pos, double Exposure, int RosterId)`（04 定义，`RosterId` 见 A-2-19）；`CommandPointsBonus int` | 05、04 |
| P35 | 3.2 第 3 步之后，L1059 | 新增第 3a 步 | "构造 `TerrainModel(level.Heightmap, level.Catalog.Rules.Terrain)`；选定 `IEnemyAiHooks`（`config.EnemyAiHooksOverride ?? EnemyAiHooks`）" | 01 |
| P36 | 3.2 第 7 步，L1065 | 追加 | "创建每个实体时写 `Placement`、`RosterId`；`FireUnit` 创建后立即调用 03 的 `FireUnitFactory.Init`（建立 `Weapons` 列表，不分配弹药）"（A-4-05） | 02、05、03 |
| P37 | 3.2 第 8 步，L1066 | 改写 | "按 `RosterId` 把 `CarryIn.Units[i]` 中的 `Exposure`、`DamageEfficiencyMult`、`LightDamaged`、`CrewConsecutiveNights`、`AceCrew` 写入对应实体；其余 `CarryIn` 字段（弹药、保护目标 HP、已知目标、警报响应度、欺骗单位寿命……）由所属系统在第 9 步 `Initialize` 中读取"（A-4-05） | 05、03 |
| P38 | 3.2 第 9 步之后，L1067 | 新增第 9a 步 | "调用阶段 0 组件 `CommandStage.Initialize(ctx)`（`ctx.Rng = setup`；剧情校验、指挥点初值）" | 04 B |
| P39 | 3.2 第 10 步，L1068 | 改写 | "收集所有实现 `ICommandHandler` 的系统**以及阶段 0 组件 `CommandStage`**" | 04 B |
| P40 | 3.4 `CommandStageHooks()`，L1103 | 改写注释 | `// 04：DeploymentStage.Run → ChoiceStage.Run → StoryStage.Run（04 3.1）` | 04 B、B-T2-15 |
| P41 | 3.5 `AllClear()`，L1178 | 改写 | 按 B-T2-08：`AllWavesSpawned` 且 "仍可造成伤害的目标"（`Kind == Munition`，或 `Kind == Platform` 且仍有未完成的 `Releases`）为 0 且 `Interceptors.CountAlive() == 0` 且 `EnemyIntel.HeldWaves.Count == 0` 且 `!StoryRules.HasPendingScheduledSpawn(ctx)` | 04 C、B-T2-08 |
| P42 | 3.5 `NightResult`，L1207 之后 | 追加 | `CivilSummary Civil`、`SupportSummary Support`（03）、`CommandSummary Commands`（04）；`CarryOut` 定义见 05 2.4.2，追加 `IReadOnlyList<StoryChoiceResult> StoryChoiceResults`（04）；序列化选项（camelCase、`JsonStringEnumConverter`、无 NaN）写入本节 | 03 R-NR、04 I、05 R-00-5 |
| P43 | 3.1.5，L1049 | 改写 | 按 B-T2-07：第三参数由调用方给出（战役 = flow 序号 + 1，非战役 = `NightIndex`） | 05 R-00-3、B-T2-07 |

### 1.7 子流（00 3.1.4，用途列，L1018–1037）

| 子流 | 改后的用途 | 来源 |
|---|---|---|
| `command` | 预留（本版本 0 消耗） | 04 D |
| `spawn` | 组目标选择（`weighted_random` / 回退）、挂载选择（`NextInt`）、**04 钩子 `SelectKnownTarget` / `SelectAirDefenseTarget` 的加权选择**（代码在 04，宿主为系统 1） | 01、04 |
| `movement` | `altitudeM` 区间掷骰（每个目标初始化一次） | 01 |
| `sensor` | 误报（每个有误报能力的工作中探测单位每步 1 次 `Chance` + 位置） | 02 |
| `fusion` | 诱饵甄别 | 02 |
| `ew` | 导航干扰 / 诱导 / 国家级欺骗 / 链路中断判定与结果 | 02 |
| `emission` | 预留（本版本 0 消耗）——删去"反辐射导弹规避判定" | 02 C |
| `engagement` | 预留（0 消耗） | 03 |
| `intercept` | 拦截弹与身管射击判定 | 03 |
| `support` | 大空袭夜拒绝 | 03 |
| `impact` | 落点偏移、民用损毁数、部件选择、反辐射导弹失锁 | 03 |
| `exposure` | 假发射车识破（不再是"预留"） | 02 C |
| `enemy_ai` | 预留（0 消耗） | 04 D |
| `civil` | 预留（0 消耗）；宿主 `ScoringSystem` | 03 R-RNG |

### 1.8 事件（00 4.2 总表，L1356–1403"关键字段"列整列替换）

| 值 | 事件 | 定稿字段（顺序 = 哈希顺序） | 来源 |
|---|---|---|---|
| 100 | `WaveStarted` | `string WaveId, IReadOnlyList<AiTag>? AiTags, bool Injected` | 01 |
| 101 | `ThreatSpawned` | `int ThreatId, string DefId, ThreatKind Kind, string EntryId, string WaveId` | 01 |
| 102 | `MunitionReleased` | `int ParentThreatId, int ThreatId, string DefId` | 01 |
| 103 | `ThreatArrived` | `int ThreatId, string DefId, Vec2 Pos, ThreatTargetKind TargetKind, int TargetStructureId, int TargetUnitId` | 01 |
| 104 | `ThreatExited` | `int ThreatId, string DefId, ThreatExitReason Reason` | 01 |
| 200 | `EarlyWarning` | `string WaveId, string EntryId, double ExpectedAtSec, double BearingRad, bool Ballistic` | 02 |
| 201 | `TrackCreated` | `int TrackId, TrackQuality Quality` | 02 |
| 202 | `TrackQualityChanged` | `int TrackId, TrackQuality From, TrackQuality To` | 02 |
| 203 | `TrackLost` | `int TrackId, TrackLostCause Cause` | 02 |
| 204 | `DecoyIdentified` | `int TrackId` | 02 |
| 205 | `EmitterSwitched` | `int UnitId, bool On, EmitterSwitchCause Cause`（`Cause` 追加 `RadarDestroyed = 6`、`Suspended = 7`，A-2-12） | 02、A-2-12 |
| 206 | `ArmThreatDetected` | `int TrackId, int TargetUnitId` | 02 |
| 207 | `EwDiverted` | `int ThreatId, int EwUnitId, EwDivertKind Kind` | 02 |
| 208 | `EwLinkCut` | `int ThreatId, int EwUnitId, LinkCutOutcome Outcome, string DefId`（`DefId` 追加；悬停超时坠落也发本事件，A-4-03） | 02、A-4-03 |
| 209 | `ExposureThresholdCrossed` | `int UnitId, double Threshold, ExposureConsequence Consequence, bool Rising` | 02 |
| 210 | `DeceptionTriggered` | `int UnitId, int ThreatId, DeceptionOutcome Outcome` | 02 |
| 300 | `InterceptorLaunched` | `int FireUnitId, int LauncherIndex, string WeaponId, int InterceptorId, int TrackId, int ThreatId, int SupportAssetId` | 03 |
| 301 | `GunFired` | `int FireUnitId, string WeaponId, int TrackId, int ThreatId, double Probability, int RoundsUsed` | 03 |
| 302 | `InterceptResolved` | `int? InterceptorId, int ThreatId, bool Hit, double Probability, Vec2 Pos, double AltM, bool OverUrban, string WeaponId, int FireUnitId, int SupportAssetId` | 03 |
| 303 | `InterceptorExpired` | `int InterceptorId, InterceptorExpiryCause Cause`（`Cause` 追加 `TargetManeuvered = 1`、`TargetArrived = 2`，A-2-09、A-4-02） | 03 |
| 304 | `EngagementHeld` | `int FireUnitId, string WeaponId, int TrackId, int ThreatId, HoldReason Reason` | 03 |
| 305 | `AmmoDepleted` | `int FireUnitId, string WeaponId` | 03 |
| 306 | `ThreatImpacted` | `int ThreatId, string DefId, Vec2 Pos, Vec2 AimPos, int DamageLevel, AccuracyTier Tier, ImpactOutcome Outcome, int SubIndex, LeakReason? LeakReason, int LeakMask` | 03 |
| 307 | `StructureDamaged` | `int StructureId, int HpBefore, int HpAfter, int SourceThreatId, DamageCause Cause` | 03 |
| 308 | `StructureDestroyed` | `int StructureId` | 03 |
| 309 | `PlayerUnitDamaged` | `int UnitId, string DefId, PlayerUnitCategory Kind, UnitDamageEffect Effect, DamagedComponent Component, int SourceThreatId` | 03 |
| 310 | `PlayerUnitDestroyed` | `int UnitId, string DefId, PlayerUnitCategory Kind, int SourceThreatId, Vec2 Pos`（**追加 `Pos`**，A-2-05） | 03、02、06 |
| 311 | `DebrisFell` | `Vec2 Pos, int StructureId, int DamageLevel, int SourceThreatId`（`StructureId` 0 = 无） | 03 |
| 312 | `GridPowerChanged` | `int GridNodeId, bool Powered` | 03 |
| 313 | `AirRaidAlertChanged` | `bool On, AlertCause Cause` | 03 |
| 314 | `SupportRequested` | `string SupportDefId, int SupportAssetId` | 03 |
| 315 | `SupportRefused` | `string SupportDefId, SupportRefusalReason Reason` | 03 |
| 316 | `SupportArrived` | `int SupportAssetId` | 03 |
| 317 | `SupportEnded` | `int SupportAssetId, SupportEndReason Reason` | 03 |
| 400 | `KnownTargetAdded` | `int EntryId, int UnitId, string UnitDefId, KnownTargetKind Kind, KnownTargetReason Reason, Vec2 Pos` | 04 |
| 401 | `KnownTargetRemoved` | `int EntryId, int UnitId, KnownTargetRemovedReason Reason` | 04 |
| 402 | `ChoiceRequested` | `int ChoiceId, ChoiceKind Kind, string ChoiceKey, int OptionCount, int DefaultOption, int DeadlineTick, int SubjectUnitId, int SubjectTrackId, string? StoryEventId` | 04 |
| 403 | `ChoiceResolved` | `int ChoiceId, int Option, bool TimedOut, bool Cancelled` | 04 |
| 404 | `CommandPointsChanged` | `int Before, int After, SimCommandType Cause` | 04 |
| 405 | `UnitDeployStateChanged` | `int UnitId, UnitDeployState From, UnitDeployState To, bool CompletedRelocation, bool DestinationScouted, string? DestinationAlternatePositionId` | 04、02 |
| 406 | `StoryEventFired` | `string StoryEventId` | 04 |
| 407 | `DialogueShown` | `string DialogueKey, string StoryEventId` | 04 |
| 408 | `EnemyGroupsReleased`（新增） | `string WaveId, int HeldGroupCount, ReleaseCause Cause` | 04 |

### 1.9 命令与拒绝原因（00 4.3，L1418–1443）

| 值 | 命令 | 定稿字段 | 处理者 | 来源 |
|---|---|---|---|---|
| 200 | `SetEmissionPolicy` | `int UnitId, string PolicyId, double? DutyOnSec, double? DutyOffSec, ArmResponse? OnArmIncoming, AfterFiringAction? AfterFiring, bool? NeighborTakeover` | `EmissionSystem` | 02 |
| 201 | `SectorEmissionOverride` | `Vec2 Center, double RadiusM, SectorOverrideMode Mode` | `EmissionSystem` | 02 |
| 300 | `SetEngagementRule` | `int FireUnitId, string? WeaponId, EngagementRule Rule` | `EngagementSystem` | 03 |
| 301 | `CallSupport` | `string SupportDefId, Vec2? TargetPos` | `ExternalSupportSystem` | 03 |
| 302 | `SetAirRaidAlert` | `bool On` | **`ScoringSystem`**（L1425 的"宿主见 Q5"改为此） | 03、04 |
| 303 | `SetFighterZone` | `int SupportAssetId, bool Exclusive` | `ExternalSupportSystem` | 03 |
| 400 | `DeployUnit` | `int UnitId, string? UnitDefId, Vec2? Pos` | `CommandStage` | 04 |
| 401 | `PackUnit` | `int UnitId` | `CommandStage` | 04 |
| 402 | `MoveUnit` | `int UnitId, Vec2 Dest` | `CommandStage` | 04 |
| 403 | `RelocateUnit` | `int UnitId, Vec2? Dest, string? AlternatePositionId` | `CommandStage` | 04 |
| 404 | `AnswerChoice` | `int ChoiceId, int Option` | `CommandStage` | 04 |

拒绝原因：L1443 之后追加"03 段"小表：`300 NoSortiesLeft`、`301 InRiskZone`、`302 AirbaseUnavailable`。L1416 的"是否消耗指挥点由 04 统一规定"补一句："所有处理者的 `Validate` 最后一条检查为 `!CommandPointRules.CanSpend(ctx, cost)` → `NoCommandPoints`（04 3.6）"。

### 1.10 快照、项目结构、公共工具

| # | 位置 | 操作 | 内容 | 来源 |
|---|---|---|---|---|
| P44 | 2.7 `SimSnapshot`，L892 之后 | 追加 | `public DebugView? Debug { get; }`（`CaptureDebug == false` 时 null；`DetectionDebugView` 按 06 8.2 A） | 06 |
| P45 | 2.7 注释，L892 | 改写 | `GlobalView` 字段：01（`PendingSpawnCount`、`SpawnedThreatCount`、`AllWavesSpawned`）、03（`AlertOn`、`ShelteredFrac`、`Responsiveness`、`SortiesRemaining`、`GridCollapsed`、`WeightedLossFrac`）、04（`CommandPoints`、`CommandPointsInitial`、`EnemyKnownTargets`、`HeldWaveCount`） | 01/03/04 |
| P46 | 2.7 各单位视图 | 补注 | 我方单位视图公共追加：`DeployState`、`DeployPhaseEndTick`、`RelocationDest`（04）、`EmitterOn`、`PolicyId`、`FcMode`、`Exposure`、`ExposurePeak`、`NewPositionPenalty`（02）、`DamageEfficiencyMult`、`SuspendedUntilSec`、`LightDamaged`（03）；`TrackView` 按 02 2.9；`ThreatView` 按 01 2.4 | 02/03/04/06 |
| P47 | 0.5 项目结构，L218 | 改写目录列表 | 追加 `Movement/`、`EnemyAi/`（01、04）、`Campaign/`、`Economy/`、`Save/`、`Production/`、`Research/`（05）；`Commands/` 含 `CommandStage`、`DeploymentStage`、`ChoiceStage`、`StoryStage`、`CommandPointRules`、`DeploymentValidator`、`DeploymentRules`、`StoryRules`（04） | 01、04、05 |
| P48 | 0.4.4，L189 之后 | 追加 | `Geo` 公共函数（全目录唯一实现）：`BearingRad`、`Normalize`（0.4.5）、`PointInPolygon(Vec2 p, IReadOnlyList<Vec2> poly)`——代码取 03 3.0（半开规则，边界结果由公式决定）；02 3.1、04 3.5.2 改为引用此处（A-2-24） | 02 J、03 B16 |
| P49 | T-00-35，L1756 | 改写 | `LoadedFiles.Count == 35`（26 个全局 + 8 个关卡 JSON + 1 个 PNG） | 合并 |
| P50 | 8 Q5、Q7、Q10、Q11、Q15、Q16、Q17 | 关闭 | Q5 → 04 3.1 + 03 3.7.1；Q7 → 04；Q10 → 05 / B-T2-07；Q11 → 05 R-00-9；Q15 → 04 3.8；Q16 → B-T2-16；Q17 → 04 3.4.5 | 各规格 |

---

## 2. 跨文件接口对齐

> 每条：依赖方写的签名 / 字段 vs 被依赖方实际定义。推荐方案已在第 1 节补丁表中体现的，注"→ Pxx"。

### A-2-01 航迹标签：03 的 `Track.PerceivedTag` 不存在；且模糊航迹被 03 整体排除
- 位置：03 0.3 D5、3.2.3 C（`if track.PerceivedTag == null: continue`）、3.2.4、5 #17；02 2.5 `Tag`、3.3.6（`Tag = Quality ≥ Approximate 且 ThreatId != 0 ? DisplayTag : null`）；06 8.4 B1。
- 问题：(1) 字段名不一致（02 `Track.Tag`，03 `PerceivedTag`，06 已按 02）。(2) 语义冲突：02 对**模糊**航迹给 `Tag = null`，03 把 `null` 解释为"类型未知、不可交战"并在候选阶段跳过，于是模糊航迹永远进不了交战，03 3.3.2 的 `TrackVague.GunProbMult`（数值表"模糊航迹：高炮 / 火力组 ×0.5"）成为死代码。
- 建议：(1) 把 03 全文 `PerceivedTag` 改为 `Tag`（0.3 D5、3.2.3、3.2.4、5 #17、8.3 B3）。(2) 03 3.2.3 C 改为：`pt = track.Tag ?? (track.Quality == Vague ? Intercept.DecoyUsesColumn : null)`；`pt == null` 才跳过。即模糊航迹按"像无人机"进入候选，再由 3.2.4.1 d 的质量门槛只放行 `Gun`（及 `tracks.Allows(Vague, vector_interceptor_drones)` 为真时的拦截无人机）。拦截概率仍按真实标签列（3.3.2 不变）。
- 分级：(1) T1；(2) **T2**（"模糊航迹按 UAV 外观处理"是默认值选择）。

### A-2-02 `Predict` 签名、"已到达"语义与悬停平台
- 位置：03 0.3 D1（`ThreatPredictor.Predict(SimContext ctx, Threat t, double dtSec)` → `PredictedState(Pos, AltM, bool Arrived)`）、3.1 `Solve`；01 3.2.9（`ThreatKinematics.Predict(Threat th, double atSec)` → `ThreatPose(…, bool AtPathEnd)`，绝对时刻）。
- 问题：(1) 类名、参数（相对 / 绝对时间）、返回类型均不同。(2) `AtPathEnd` 对 `Holding`（无挂载平台悬停）、`Exit`（离开地图前的终点）也为 true。若 03 直接把 `AtPathEnd` 当 `Arrived`，`Solve` 第一采样点即返回 `null`，**悬停的 Orlan / A‑50 / 直升机永远打不到**。
- 建议：03 删除 `ThreatPredictor` / `PredictedState`，改为在 03 内部适配：`predict = dt => { var p = ThreatKinematics.Predict(t, ctx.TimeSec + dt); return (p.Pos, p.AltM, Arrived: p.AtPathEnd && t.PathEnd == PathEndAction.Arrive); }`。`PredictedState` 作为 03 私有 `readonly record struct` 保留给测试桩。01 3.2.9 补一句"`AtPathEnd` 对 `Hold` / `Exit` 也为 true，调用方需结合 `PathEnd` 判断是否落地"。
- 分级：T1。

### A-2-03 `ThreatArrived` 的删除责任与平台
- 位置：03 0.3 D2（"平台的 `ThreatArrived`（到达投放点）本文件忽略"）；01 3.2.4（只有 `PathEnd == Arrive` 发 `ThreatArrived`；平台的路径终点是 `Exit` 或 `Hold`，**从不**发）、3.2.5、B10。
- 问题：删除责任两边一致（03 系统 10 删除）；但 03 D2 的平台从句与 01 不符，会诱导实现者为平台写无用分支。
- 建议：删去 03 D2 的平台从句，改为"`ThreatArrived` 只由弹药产生"；01 4.1 表注明同一点。
- 分级：T1。

### A-2-04 `Threat.TargetUnitId` 由谁写
- 位置：02 2.6 末行、8.2 A（"01 / 04 写"）、4.3；04 3.3.2 末条（"本文件从不直接写 `Threat`……01 依据钩子返回值写"）；01 3.1.3（生成时）、3.2.8 `ApplyHoming`（归航时改写）。
- 问题：02 的"01 / 04"与 04 的声明不一致。
- 建议：唯一写者 = 01（生成时取钩子返回值；`ApplyHoming` 时改写）。02 2.6、8.2 A、4.3 三处改为"01 写"。
- 分级：T1。

### A-2-05 `PlayerUnitDestroyed` 缺 `Pos`
- 位置：02 3.5.6、8.2 D（要求追加）；03 3.5.6 `Destroy`、4.2（字段 `UnitId, DefId, Kind, SourceThreatId`，无 `Pos`）；06 8.2 C、8.4 B3（有回退）。
- 问题：02 的"邻近雷达接替"在被毁单位压缩后无法再取位置。
- 建议：03 4.2 字段改为 `int UnitId, string DefId, PlayerUnitCategory Kind, int SourceThreatId, Vec2 Pos`（`Pos` 追加在末尾，保持现有字段哈希顺序），`Destroy` 中填 `u.Pos`。→ 1.8 表。
- 分级：T1。

### A-2-06 反辐射导弹的 `HomingUnitId` 无人写入
- 位置：01 2.2 #14（写者"**02**（反辐射归航）"）、3.2.8 `ApplyHoming`、B6；04 3.3.2（"之后的归航由 02 设置 `HomingUnitId`"）、5 #8；02 全文**没有** `HomingUnitId`。
- 问题：01 / 04 都假设 02 写，02 未定义 ⇒ `ApplyHoming` 永不生效，"雷达关机后反辐射导弹飞向最后记录位置"的分工落空（命中率由 `ArmHitProbMult` 体现，位置跟踪缺失）。
- 建议：02 3.5.5 增加第 0 步（在 `ArmScan` 开头）：对每个存活的反辐射导弹 `m`（ID 升序），`U = m.TargetUnitId` 指向的存活辐射源；`m.HomingUnitId = (U 存在 且 U.Emitter.On) ? U.Id : 0`。2.6 表追加一行"`HomingUnitId`（01 拥有）｜写 6｜读 01"。生效时刻：本步第 6 步写，下一步第 2 步 `ApplyHoming` 读（1 步延迟，可接受）。
- 分级：T1。

### A-2-07 03 假设的电子战字段名与 02 定义不符；"降档"与"额外偏移"的消费方
- 位置：03 0.3 D12（`EwTierDrop`、`EwAffected`、`EwCovered`）、D13（`ArmTargetUnitId`、`ArmHitProbMult` 默认 1.0）、3.5.3、3.5.4、3.5.7、3.8.4；02 2.6（`AccuracyTierDrop`、`EwNav`、`EwExtraOffsetM`、`ArmHitProbMult : double?`）、3.4.4；05 R-02-1（"曾处于电子战覆盖"粘性标记）；B-T3-08。
- 问题：(1) 名字不同；(2) 02 没有 `EwCovered`（03 突防原因"电子战失效"、05 `PlayStats.ThreatsEverEwCovered` 都要）；(3) 额外偏移由两处计算：02 写 `EwExtraOffsetM = EwExtraM[原精度档]`，03 又按**有效**精度档自己取 `tierDef.EwExtraM`，值可能不同；(4) `ArmHitProbMult` 可空性不同。
- 建议：
  - 03 改读：`EwTierDrop` → `t.AccuracyTierDrop`；`EwAffected` → `t.EwNav == EwRollState.Applied`；`ArmTargetUnitId` → `t.TargetUnitId`；`ArmHitProbMult` → `t.ArmHitProbMult ?? 1.0`（3.5.7）。
  - 额外偏移唯一由 02 计算：03 3.5.4 的 `extra` 改为 `def.EwImmune == true ? 0 : t.EwExtraOffsetM`（数值口径按 B-T3-08 的裁决，02 写入时使用）。
  - 02 2.6 追加 `EwEverCovered : bool`（初值 false；第 5 步：任一 `Covers(u, t)` 成立且 `u.Def.Effect ∈ {NavJam, NavSpoof}` 时置 true，不掷骰、不耗随机数）；03 的 `EwCovered` 读它；05 的 `ThreatsEverEwCovered` 由 03 `ScoringSystem` 在目标被移除时累计。
- 分级：T1。

### A-2-08 03 假设的火控 / 指示字段在 02 中不存在；导弹发射资格与 02 D2 冲突
- 位置：03 0.3 D6 `Track.Cued`、D8 `FireUnit.FireControlActive`、D9 `HasFireControlRadar`、D10 `EmissionReactionMult`、D14 `EmissionSilentHold`、3.2.4.1 e、3.2.5、3.3.2 m1；02 0.4 D2、2.2、2.5、3.3.4（"03 用导弹交战航迹 k 的前提是 `f.Id ∈ k.PreciseHolderIds`"）、3.5.4、8.3。
- 问题：(1) 5 个字段 02 均未定义；(2) 03 的门槛 e 只检查本单位雷达开机，不检查 `PreciseHolderIds`——单位 A 的雷达把航迹变成"精确"后，单位 B（雷达开机但被山挡住、或没有雷达的单兵导弹，D8 规定其 `FireControlActive` 恒 true）也能对它发射导弹，与 02 D2、数值表 1.3"精确 = 防空系统**自带**火控雷达"相反；(3) "无指示首发 +50%"两处数据源：`intercept.modifiers.noCueSelfSearch.firstShotReactionTimeMult`（03 用）与 `tracks.cueing.uncued.firstShotReactionTimeMult`（02 8.3 要求 03 用），且判定粒度不同（03 按航迹 `Cued`，02 按单位 `FcMode`）。
- 建议：
  - 02 新增只读工具 `Nightwatch.Sim.Sensing.FireControlQueries`（3.5.4 之后）：`Cued(Track k) = k.NetworkQuality != null && k.NetworkQuality >= Cueing.Cued.MinTrackQuality`；`HasFireControlRadar(FireUnit f) = f.Def.FireControlRadar != null`；`ReactionMult(FireUnit f) = f.Emitter == null ? 1.0 : Strategy(f.Emitter.PolicyId).ReactionTimeMult`；`SilentHold(FireUnit f) = f.Emitter != null && !f.Emitter.On && f.DeployState == Deployed && !f.RadarDestroyed && !Suspended(f)`。
  - 03 3.2.4.1 门槛 e 改为：`Missile` / `Rocket` 要求 `unit.Id ∈ track.PreciseHolderIds`；不满足时原因 = `FireControlQueries.SilentHold(unit) ? EmissionSilent : FireControlOff`。删除 D8 `FireControlActive`。
  - 首发反应倍率按 03 的**逐航迹** `Cued(track)`、数据取 `intercept.modifiers.noCueSelfSearch`；02 8.3 对应句删除；`tracks.cueing.uncued.firstShotReactionTimeMult` 改为"仅界面"，加载器校验两值相等（与 03 1.10 对 `restrictedEngagement` 的做法一致）。02 的 `FcMode` 只用于暴露度速率。
- 分级：T1（`PreciseHolderIds` 门槛是 02 Q3 已提出、数值表已写明的规则落地，不是新设计）。

### A-2-09 路径改写后在飞拦截弹的处理（01 B2 未被 03 回应）
- 位置：01 2.2 #18 `PathVersion`、3.2.8、B2；03 2.5（发射后拦截点固定）、3.3.1、5 #3。
- 问题：电子战诱导 / 链路中断悬停 / 返航、反辐射归航都会改写路径。03 只处理"目标已消失"和"提前落地"，目标仍在但已偏离拦截点时照常按原概率掷骰，等于拦截弹"瞬移"到目标身边。
- 建议：`Interceptor` 追加 `TargetPathVersion : int`（发射时 = `t.PathVersion`）；3.3.1 结算前若 `t.PathVersion != ic.TargetPathVersion` 且 `|t.Pos − ic.InterceptPos| > ic.InterceptorSpeedMps × StepSec`（拦截弹一步内可修正的距离）→ `InterceptorExpired { Cause = TargetManeuvered }`，不掷骰；否则照常结算。系统 7 在下一步可重新交战。
- 分级：**T2**（"机动目标使在飞拦截弹失效"影响电子战与拦截的配合效果，默认值需批准）。

### A-2-10 `IEnemyAiHooks` 签名扩展（04 → 01）
- 位置：04 3.3.0（`TargetRequest`、`AvoidanceRequest`、`DeferGroup`、`SaturationSpawnTimes`、`WaveInjection.GroupIndices`、`StartsWave` 规则、绕行条件）、8.3 B-01；01 2.3、3.1.2、3.1.3、3.1.5、3.1.6、3.1.9、3.2.6。
- 问题：01 仍是旧签名（无请求上下文、无推迟 / 饱和入口），04 已按新签名实现；04 还引用 01 的 `AvoidanceActive(state)`，但 01 只把它写成伪代码谓词。
- 建议：以 04 3.3.0 为准修改 01：3.1.9 接口整体替换为 04 的 5 个方法与 2 个请求类型；3.1.2 `ExpandWave(wi, baseSec, injected, groupIndices)` 按 04 第 3、4 条；2.3 `WaveInjection(string WaveId, double StartAtSec, IReadOnlyList<int>? GroupIndices)`，哈希追加 `GroupIndices`；3.1.5 / 3.2.6 绕行条件按 04 第 2 条；`DefaultEnemyAiHooks` 的两个新方法返回 `false` / `null`。`AvoidanceActive` 提升为 `public static bool EnemyAiQueries.AvoidanceActive(SimState, GameCatalog)`（放 `Nightwatch.Sim.EnemyAi`，01 定义），04 调用它。
- 分级：T1。

### A-2-11 二选一结果的落地方式：命令（02）vs 直接设置（04）
- 位置：02 8.3 末第二行（"回答通过 `SetEmissionPolicy` / `SectorEmissionOverride` 落地……建议走命令"）；04 3.7.3（`EmissionChoiceEffects.ApplyArmChoice(SimState, int unitId, bool silence)`，并给出 3 条理由）、8.3 B-02。
- 问题：两种方案互斥，02 未定义 `ApplyArmChoice`。
- 建议：采用 04 方案。理由补充：`AnswerChoice` 本身已是记录在回放中的命令，效果在其 `Apply` 中同步执行，与"命令是唯一输入"不冲突；内部再造命令会污染 `_commandLog`。02 3.5.5 末尾追加 `EmissionChoiceEffects.ApplyArmChoice` 的定义（语义照抄 04 3.7.3），2.2 表 `ArmSilenced` / `ArmPending` 的"写"列加"0（经 `ApplyArmChoice`）"；删除 02 8.3 的"建议走命令"。
- 分级：T1。

### A-2-12 02 未读取 03 的 `RadarDestroyed` / `SuspendedUntilSec`
- 位置：03 2.1、2.2 `RadarDestroyed`（"02（D8 应据此置 …）"）、8.3 B7；02 3.2.3 `SensorActive`、3.2.5、3.4.1、3.5.3 `Desired`（均无这两项）。
- 问题：雷达被毁的火力单元仍开机、仍产生精确探测、仍累积暴露度；重伤暂停的探测 / 电子战单位照常工作。
- 建议：02 3.5.3 `Desired` 表在第 1 行之后插入：`1a｜FireUnit 且 RadarDestroyed｜关｜RadarDestroyed`、`1b｜Suspended(e)（SuspendedUntilSec > TimeSec + 1e-9）｜关｜Suspended`；`EmitterSwitchCause` 追加 `RadarDestroyed = 6, Suspended = 7`（→ 1.8）。`SensorActive` 追加 `!Suspended(s)`；3.2.5 自主捕获追加 `!Suspended(f)`；3.4.1 电子战生效追加 `!Suspended(u)`；电子战断电按 B-T2-05（效果概率 ×0.5，在 3.4.3 乘入）。
- 分级：T1。

### A-2-13 新阵地首夜：三个名字
- 位置：02 2.1 `NewPositionPenalty`；03 2.2 `NewPositionFirstNight`（初值"`CarryIn`"）、3.3.2 m2；05 2.4.1 末段、8.4 B3；04 B-02e；B-T2-06。
- 建议：按 B-T2-06：删除 03 2.2 的 `NewPositionFirstNight` 行与 R-CI 中的同名项；3.3.2 `m2 = unit.NewPositionPenalty ? …`。数据流：`PlacedUnit.FirstNightAtNewPosition`（05 填）→ 02 `Initialize` 写 `NewPositionPenalty` → 02 第 11 步在夜间转移完成时重算 → 03 第 7 步只读。
- 分级：T1（字段统一部分）。

### A-2-14 弹药池：`Meta.AmmoQuota`（03）vs `CarryIn.AmmoPool` / `Depot`（05）
- 位置：03 3.2.1（`pool = Meta.AmmoQuota`）、2.8 `AmmoPoolRemaining`；05 2.4.1 `AmmoPool`（"非 null 时代替 `Meta.AmmoQuota`"）、8.3 R-03-2、8.4 B5。
- 建议：03 3.2.1 第一行改为 `pool = (Config.CarryIn.AmmoPool ?? Meta.AmmoQuota 转换) 的副本`；`AmmoSummary.PoolRemaining` 即 05 的取回来源。术语：夜内一律称"弹药池"（`AmmoPool`），`Depot` 只在 05 战役层使用（3.3 节表格注明对应关系）。逐架余弹的覆盖时序见 A-4-05。
- 分级：T1。

### A-2-15 部署校验：`DeploymentValidator` / `CheckPlacement` / `CheckPosition` / `ValidatePosition`
- 位置：00 3.2 第 7 步（`DeploymentValidator.Validate(level, plan)`）；04 3.5.1（`Validate`，`DeploymentError(string Code, int Index, string UnitDefId, string Detail)`，码 `D_*`）、3.5.2（`DeploymentRules.CheckPosition(level, defId, p) : (string Code, string Detail)?`）；06 8.3 D-04-1（`CheckPlacement(level, plan, replaceIndex, candidate)`，`DeploymentError(string Code, int UnitIndex, string Detail)`，码 `E_DEPLOY_*`）、8.2 E `ui.deploy.error.<Code>`；05 R-04-1（`DeploymentValidator.ValidatePosition(level, unitDefId, pos)`）。
- 建议：以 04 为准：`DeploymentError(Code, Index, UnitDefId, Detail)`，码 `D_*`。04 3.5.1 追加 06 需要的 `public static DeploymentError? CheckPlacement(LevelData level, DeploymentPlan plan, int replaceIndex, PlacedUnit candidate)`（= 构造候选方案后调用 `Validate`，返回第一条 `Index == 候选下标` 的错误）。05 R-04-1 改为调用 `DeploymentRules.CheckPosition`（不新增 `ValidatePosition`）。06 8.3 改用 `Index`，本地化键 `ui.deploy.error.D_*`。
- 分级：T1。

### A-2-16 `CoverageQuery`（06 需要，02 未定义）
- 位置：06 8.3 D-02-1、8.4 B2；02 全文无。
- 建议：02 新增 3.8"覆盖查询（只读，供客户端）"，签名照抄 06 D-02-1；语义按 06 所列（有效距离公式复用 3.2.3–3.2.6 的同一实现，天线高度按 B-T2-03，天气取 `Waves.Nights` 中 `Night == nightIndex` 的 `Weather`，`NightAids` 取 `unit.Settings.NightAids`）。同时声明"线程安全、不读 `SimState`"。
- 分级：T1。

### A-2-17 指挥点：02 / 03 的处理者缺 `NoCommandPoints` 检查
- 位置：04 3.6（"所有耗点命令，含 02 / 03 的处理者：`Validate` 最后一条为 `!CanSpend` → `NoCommandPoints`；`Apply` 第一件事 `Spend`"）；02 3.5.8（`SetEmissionPolicy` 6 条、`SectorEmissionOverride` 2 条，均无）、4.2（"拒绝原因只使用 … 不定义"）；03 4.3 `SetEngagementRule`、`SetAirRaidAlert`、`SetFighterZone`（无）；03 3.4.1 `CallSupport` 第 9 条（已有）。
- 问题：03 D15 与 04 签名一致（`CanSpend(ctx, n)`、`Spend(ctx, n, cause)`、`Refund(ctx, n, cause)`），但 02 / 03 的其他处理者未落实约定，实现时会漏扣点。
- 建议：02 3.5.8 两条命令各追加最后一条校验 `!CommandPointRules.CanSpend(ctx, CommandPointRules.CostOf(Level, cmd.Type))` → `NoCommandPoints`，应用第一步 `Spend`；4.2 拒绝原因补 `NoCommandPoints`。03 4.3 三条命令同样追加。`CallSupport` 的退还在系统 9 调 `Refund`（04 2.4 已注明这是 `CommandState` 唯一的阶段 0 外写入，保留）。
- 分级：T1。

### A-2-18 `CarryIn.KnownTargets` 与指挥点奖励：04 / 05 类型冲突
- 位置：04 3.2.1、3.2.7、8.2 I（`IReadOnlyList<KnownTargetCarry>?`，`KnownTargetCarry(string UnitDefId, Vec2 Pos, double Exposure)`；`BonusCommandPoints int?`）；05 0.3 D5、2.4.1（`KnownTargetCarry?` 不透明单对象，带 `IsScouted`、`OnUnitRelocated(int rosterId, …)`、`OnUnitRemoved(int rosterId)`、`AddStructureTarget(string)`；`CommandPointsBonus int`，截断到 `[0, economy.commandPointsPerNight.max]`）、8.3 R-04-1。
- 问题：类型形态不同；05 的方法需要 `RosterId`，04 的记录没有；05 的 `OnUnitRelocated` 若改写记录位置，将违反 04 K2（"记录不随单位移动"，04 B-05 已说明白天转移不更新清单）；`AddStructureTarget` 在 04 中没有对应（04 的清单只记我方单位）。
- 建议：类型以 04 为准（04 拥有敌方情报的语义），追加 `int RosterId`（0 = 未知；`BuildCarryOut` 从实体 `RosterId` 填，04 匹配时忽略它）。05 的 4 个方法改为 05 战役层静态函数 `KnownTargetCarryOps`：`IsScouted(list, pos)`（同 04 `ScoutedRadiusM` 口径）；`OnUnitRemoved(list, rosterId)` 删除该花名册单位的记录；`OnUnitRelocated` **删除**（K2）；`AddStructureTarget` 删除（敌方对保护目标的掌握已由 I1 表达）。字段名统一为 `CommandPointsBonus`（`int`，缺省 0），截断由 04 在 `CommandState` 初值处执行（04 2.4 初值改为 `Clamp(Meta.CommandPointsPerNight + CarryIn.CommandPointsBonus, 0, Economy.CommandPointsPerNight.Max)`）。→ P34。
- 分级：T1。

### A-2-19 `CrewConsecutiveNights` 语义
- 位置：03 2.2（`CarryIn`，否则 0）、3.3.2 m3（`>= CrewFatigue.MinConsecutiveNights`）；05 3.7.5、8.4 B4（"含今晚的连续作战夜数"）、2.4.1 `UnitCarryIn.CrewConsecutiveNights`。
- 建议：03 2.2 该行说明改为"含今晚的连续作战夜数（05 在夜前计算并经 `CarryIn.Units[].CrewConsecutiveNights` 带入；非战役 = 0）"；03 不自增。
- 分级：T1。

### A-2-20 03 的 `BuildResult` 需要但 `ScoringState` 没有的数据（05 `CarryOut`）
- 位置：05 2.4.2（`UnitCarryOut.Weapons`"被毁单位取被毁前一刻"、`RadarDestroyed`、`LaunchersLost`、`Hits`；`PlayStats`；`KillsByEnemy`）、8.3 R-03-1；03 2.8 `ScoringState`、3.5.6 `Destroy`（直接 `Remove`，`WeaponState` 随实体消失）。
- 问题：被毁单位的余弹、每单位命中数、按敌方定义的击落数、ARM 统计在 03 中都无处可取。
- 建议：03 2.8 `ScoringState` 追加：`UnitHits : SortedDictionary<int,int>`（`InterceptResolved{Hit}` 按 `FireUnitId`）、`DestroyedUnitSnapshots : List<UnitCarryOut>`（`Destroy` 时由系统 10 先构造快照再 `Remove`——这是系统 10 写 `ScoringState` 的唯一例外，或改为在 `Destroy` 内发事件后由 13 从事件中重建：推荐前者，简单）、`KillsByEnemy : SortedDictionary<string,int>`（`InterceptResolved{Hit}` 与 `EwLinkCut{Crash}` 按真实 `DefId`）、`ArmDetections`、`ArmShutdowns`、`ThreatsEverEwCovered`。`FireUnit` 追加 `LaunchersLost : int`（`DestroyComponent` 时 +1）。
- 分级：T1。

### A-2-21 外部支援实体字段：02 `a.Active` / `def.RadiusM` vs 03 `a.State` / `a.RadiusM`
- 位置：02 3.4.6（`a.Active`、`a.CenterPos`、`WithinRange(a.CenterPos, t.Pos, def.RadiusM)`）、4.3、8.3；03 2.6（`State : SupportAssetState { EnRoute, Active }`、`RadiusM`）、3.4.3 `AssetRadius`（导航欺骗取所引用电子战单位半径）；B-T2-04。
- 建议：02 3.4.6 改为 `a.State == SupportAssetState.Active` 与 `WithinRange(a.CenterPos, t.Pos, a.RadiusM)`；03 `AssetRadius` 的 `AccuracyDrop` 分支改为 `def.RadiusM ?? EwUnit(def.AffectsSameAsEwUnitId).RadiusM`（B-T2-04 默认给 `radiusKm = 30`）。
- 分级：T1。

### A-2-22 战斗机额度、自动结算、敌情档案：05 的 `CarryIn` 字段无人读取
- 位置：05 2.4.1 `FighterSortiesDelta`（读者 03）、`AutoResolve`（03、02）、`Dossier`（02）、`ActiveSupports`（03）、`Adaptation`（01、03、04）；03 2.8 `SortiesRemaining` 初值、3.3.2 修正链；02 3.3.8；01、04 全文无。
- 建议：03 2.8 `SortiesRemaining` 初值改为 `Max(0, (level.fighterSortiesPerNight ?? support.fighterSortiesPerNight.Min) + CarryIn.FighterSortiesDelta)`；03 3.3.2 追加 `m9 = CarryIn.AutoResolve?.InterceptProbMult ?? 1.0`（口径按 B-T3-07）；02 3.3.8 诱饵甄别 `pNew += Dossier[t.DefId].DiscriminationAdd`（截断到 1）；`ActiveSupports` / `Adaptation` 在 01 / 03 / 04 中标为"M3 之后实现，当前忽略并在 `SimWorld.Create` 遇到非空时抛 `E_NOT_IMPLEMENTED`"，避免静默无效。
- 分级：T1。

### A-2-23 `Geo.PointInPolygon` 两处定义
- 位置：02 3.1（文字描述，"点在边上结果未定义"）、8.2 J；03 3.0（代码，"半开规则，边界结果由公式决定"）、B16；04 3.5.2（引用 02 3.1，"未定义"）。
- 建议：唯一实现放 00（→ P48），代码取 03 3.0；02 3.1、04 3.5.2 删除描述改为引用；边界语义统一为 03 的"由公式决定、测试可依赖 03 T 用例"。
- 分级：T1。

### A-2-24 `waves.json` / `level.json` 没有 `kind` 字段
- 位置：00 1.2 第 3 条（"`kind` 字段：读取并校验"）、1.1 关卡文件表；data/schema 中只有 `rules.schema.json`（及 `level_content`、`map`）要求 `kind`；`data/levels/test_01/waves.json`、`level.json` 无 `kind`。另：03 / 04 / 01 新增的 6 个 `kind` 与 05 的 `campaign_rules`、`level_flow` 需要进入 Schema 枚举。
- 建议：→ P03；`rules.schema.json` 的 `kind` 枚举追加 `movement`、`terrain`、`engagement`、`civil`、`enemy_ai`、`commands`、`campaign_rules`；`level_flow` 用新 Schema `level_flow.schema.json`。
- 分级：T1。

### A-2-25 `EmissionPolicyRules.CheckAvailable` 需要接受定义 ID
- 位置：02 3.5.2（`CheckAvailable(unit, strategy, level)`，实体）；04 3.5.3 第 9 行、8.3 B-02b（部署前没有实体）。
- 建议：02 改为 `CheckAvailable(string unitDefId, EmissionStrategyDef strategy, LevelData level) : CommandRejectReason?`（规则只依赖定义：是否带火控、`Origin`、关卡号）；命令处理时传 `unit.DefId`。
- 分级：T1。

### A-2-26 地形视线接口与天线高度来源
- 位置：02 0.3、3.2.4 第 3 步、3.2.5、8.3（`TerrainQuery.HasLineOfSight(fromPos, fromAltM, toPos, toAltM)`，AGL；天线缺省 `Detection.SensorHeightM`）；01 2.5（`ctx.Terrain.HasLineOfSightAgl(a, aAglM, b, bAglM)`，缺省 `Rules.Terrain.DefaultAntennaHeightM`）；04 1.1.1 `bypass.siteAntennaHeightM`（又一个 10 m）；B-T2-03。
- 建议：02 全文 `TerrainQuery.HasLineOfSight` → `ctx.Terrain.HasLineOfSightAgl`；天线缺省按 B-T2-03 改为 `Rules.Terrain.DefaultAntennaHeightM`，删除 `detection.sensorHeightM`。04 的 `siteAntennaHeightM` 保留（敌方估计值，语义不同），但说明"与 `terrain.defaultAntennaHeightM` 独立"。
- 分级：T1。

### A-2-27 电子战对移动的后果：02 要求 01 读字段，01 要求 02 调接口
- 位置：02 0.3（"01 的移动必须读取 `EwDivertPos`、`LinkCutState`"）、3.4.5 末、3.4.6 末、8.3；01 3.2.8 `ThreatRouting.Retarget / BeginEgress`（"只在第 2 步之后调用"）、B7；01 无"悬停"接口。
- 问题：两边都等对方实现，结果谁都不做；01 也没有让弹药"原地悬停"的入口。
- 建议：采用 01 的接口方式（移动逻辑集中在 01，02 第 5 步满足"第 2 步之后"的前提）：02 3.4.5 诱导成功后调用 `ThreatRouting.Retarget(ctx, t, u*.LurePoint)`；3.4.6 `Return` 调 `ThreatRouting.BeginEgress(ctx, t)`；`Hover` 调**新增**的 `ThreatRouting.Hover(ctx, t)`（01 3.2.8 追加：`SetPath(th, [cur]); PathEnd = Hold; Phase = Holding; VelMps = (0,0)`；返回 false = 非弹药或已到达）。`EwDivertPos` 保留为记录字段（03 / 复盘读）。删除 02 0.3 与 8.3 中"01 读取"的要求。
- 分级：T1。

### A-2-28 02 会为"仅剧情注入"的波次发出国家预警
- 位置：02 3.2.1 第 3 步（对 `night.Waves` **全部**波次建预警表）；01 3.1.1（被 `spawn_wave` 引用的波次不进入自动时间表）。
- 问题：剧情波次不会在 `atGameSec` 出现，但 02 仍会在该时刻前发 `EarlyWarning`，客户端据此报警 / 弹道慢放，属于错误信息。02 3.2.8 第 2 步已处理注入时的零提前量预警，所以只需排除。
- 建议：02 3.2.1 第 3 步开头追加"跳过 `w.Id ∈ storyOnly` 的波次（集合定义同 01 3.1.1）"。02 8.3 第 3 行"01 需提供查找"关闭：注入只来自今晚的 `night.Waves`（01 3.1.3、04 3.8.4），02 按 `Id` 在其中查找即可。
- 分级：T1。

### A-2-29 01 依赖的 `StructureRules.IsDestroyed` 在 03 中不存在
- 位置：01 3.1.6 `WeightedStructure`、B1；03 2.7（只有 `Hp`）。
- 建议：01 改为 `s.Hp > 0`（03 的"被毁"定义 = `Hp == 0`，3.5.6、3.8.5）；删除 B1。
- 分级：T1。

### A-2-30 反应时间的取值函数：02 不能依赖 03
- 位置：03 1.1 `WeaponParams.ReactionSec(w, r)`（`Nightwatch.Sim.Engagement`）；02 3.5.4 `ReactionEff(f) = (f.Def.ReactionSec ?? 0) × …`；B-T2-01（挂在武器上，缺省按拦截类别）；README"只依赖编号更小的文件"。
- 问题：B-T2-01 之后 02 的"火控最后时刻开机"需要武器级反应时间，但取值函数在 03。
- 建议：`WeaponParams` 整体移到 `Nightwatch.Sim.Rules`（00 0.5 已有 `Rules/` 目录），由 00 登记为公共工具、03 拥有其规则说明；02 3.5.4 改为 `ReactionEff(f, w) = WeaponParams.ReactionSec(w, Rules.Engagement) × FireControlQueries.ReactionMult(f)`，按每个满足条件的武器分别计算（与 `Rw` 同一循环）。
- 分级：T1。

### A-2-31 已一致、仅需 00 登记的接口（不计问题数）
- `SetAirRaidAlert` 处理者：03 3.7.1 / 4.3 与 04 3.6、3.8.3 一致为 `ScoringSystem`，剧情调用 `CivilRules.SetAlert(ctx, on, AlertCause.Story)` → 1.9。
- `CommandPointRules` 签名：03 D15 与 04 3.6 一致。
- `EmitterQueries.ListActive`、`DeceptionUnit.SeenThrough`、`PendingRelocationAltId`、`UnitDeployStateChanged` 三个追加字段：02 与 04 一致。
- `WaveInjection` 的写入方：04（阶段 0d、系统 12），与 01 2.3 一致（但需 A-2-10 追加 `GroupIndices`）。
