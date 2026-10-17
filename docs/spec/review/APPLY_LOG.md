# D2b 应用记录

> 每个规格文件一节，由负责修改该文件的代理逐条填写：编号 → 已应用（位置）/ 不应用（理由）/ 留给后续（目标文件）。
> 顺序：00 → 01 → 02 → 03 → 04 → 05 → 06 → 07（新建）→ 上位文档（GDD / 数值表 / data / test_01）。

## 00_core.md

### 1. `A_interfaces.md` 第 1 节补丁表（P01–P50 及 §1.2 / §1.3 / §1.5 / §1.7 / §1.8 / §1.9）

| 编号 | 处置 | 位置 / 说明 |
|---|---|---|
| P01 | 已应用 | §1.1.3、§1.6.13：规则文件加载序追加 21–26（`terrain.json`、`tracks.json`、`emission.json`、`engagement.json`、`support.json`、`command.json`）；`LoadedFiles` 顺序固定为全局 26 + 关卡 JSON 8 + PNG 1 = 35 |
| P02 | 已应用 | §1.1.1：新增 `LoadLevel(IDataSource, string levelId, int? nightIndex = null)` 重载；按 `night.Date ?? meta.DateFrom` 解析 `periodValue` |
| P03 | 已应用 | §1.1.2：`kind` 校验规则表（26 个全局文件 + 8 个关卡 JSON 的精确期望 `kind` 值；不符报 `E_KIND_MISMATCH`） |
| P04 | 已应用 | §1.3：`aiVisionFrom` 时期闸门解析为 `bool AiVision`；补 `firstSeen` 校验规则（`levels/level_01..07` 中至少一关 `DateFrom ≥ firstSeen`） |
| P05 | 已应用 | §1.5：`Heightmap` 增加 `double[] ElevationArray`（`ElevationM` 底层的零拷贝只读数组引用，供 02 `TerrainModel` 内部热路径读取） |
| P06 | 已应用 | §1.6.1：`LevelMetaDef` 增加 `FighterSortiesPerNight`；`VictoryConditionDef.Type` 改为强类型 `VictoryConditionType` 枚举；`SurviveSec` 加载校验 `gameSec ≤ 各夜 durationGameSec 之和` |
| P07 | 已应用 | §1.6.2：`NightDef` 增加 `DateOnly? Date`（`waves.json $.nights[].date`）及范围校验 |
| P08 | 已应用 | §1.6.2：`WaveDef.AiTags` 改为 `IReadOnlyList<AiTag>` 强类型枚举列表 |
| P09 | 已应用 | §1.6.2：`WaveGroupDef.Loadout` 改为 `IReadOnlyDictionary<string, int>?` |
| P10 | 已应用 | §1.6.3：`MapDef` 增加 `IReadOnlyList<PolylineFeatureDef> Roads` / `Rivers`（供 06 灰盒底图绘制） |
| P11 | 已应用 | §1.6.4：`GridDef.Cascade` 改为强类型 `GridCascadeRuleDef` |
| P12 | 已应用 | §1.6.5：`EventsFileDef`、`ChoicesFileDef`、`BriefingFileDef` 完整定义见 §1.6.5 并引用 04 §1.2–1.3 / 05 §1.8 / 06 §1.2 |
| P13 | 已应用 | §1.6.6：`AirDefenseUnitDef` 增加 `NoMoveDuringNight`；`EngageMoving` 归单位层（`WeaponDef` 无此字段）；`FireControlRadar` 改用 `SensorEmbeddedDef` |
| P14 | 已应用 | §1.6.7：`WeaponDef` 增加 `LauncherCount`、`SalvoSize`、`ReloadPerLauncherSec`、`SharedMagazineRounds`、`GuidanceChannels`、`RequiresExternalCue`、`CramCapable`、`SelfDestructOnMiss`、`EngagementRules` 及加载期默认归一规则 |
| P15 | 已应用 | §1.6.8：`SensorDef`（含 `FalseAlarm`、`TrackConfirmSec`、`ProducesQuality`、`CanProvideCue`）、`EwUnitDef`、`DeceptionUnitDef` 完整定义 |
| P16 | 已应用 | §1.6.9：`MunitionDef` 增加 `TerminalSpeedMps`、`ClusterChildMunitionId`、`ClusterSubmunitionCount` |
| P17 | 已应用 | §1.6.10：`PlatformDef` 增加 `Releases`、`StandOffRangeM`、`SelfDefenseKnownTargetGraceSec`、`Behavior`（`PlatformBehavior` 强类型枚举） |
| P18 | 已应用 | §1.6.11：`FighterDef`（含 `AllowedTargets`、`EngageRangeM`、`VisualIdRangeM`）与 `SupportDef`（含 `RadiusM`、`DurationSec`、`DelaySec`）完整定义 |
| P19 | 已应用 | §1.6.12：`RulesSet` 全部 15 个规则对象属性表（序号 12–26） |
| P20 | 已应用 | §1.6.12：`WeatherRules`、`TerrainRules`、`TracksRules`、`EmissionRules`、`EngagementRulesDef`、`SupportRulesDef`、`CommandRules` 完整记录定义 |
| P21 | 已应用 | §1.6.12：`ExposureRules.PerUnitOverrides` 改为 `IReadOnlyDictionary<string, ExposureOverrideDef>` |
| P22 | 已应用 | §1.6.12：`EnemyAiRules` 增加 `SuppressTargetCategories`、`KnownTargetFromExposureThreshold`、`MinKnownTargetsForPreempt` |
| P23 | 已应用 | §2.1：`SimRandom.NightSeed` 第三参数说明（战役传 `nightSeq`，单夜运行传 `NightIndex`） |
| P24 | 已应用 | §2.2.2、§2.3.2、§3.7.2：实体总表与四类我方单位公共字段 `PlayerUnitCommon`（14 个参与哈希字段 + 2 个不参与哈希字段，合并 00/02/03/04） |
| P25 | 已应用 | §2.2.2：`ChoiceRequest` 删除与基类 `Entity.CreatedTick` 重复的子类字段，只写 10 个专有字段 |
| P26 | 已应用 | §2.2.2、§2.3.1：`Threat` 全部字段定稿表（01 拥有 1–32、02 拥有 33–43 含 `EwEverCovered`、03 拥有 44–47），统一 `*ArcM` 后缀 |
| P27 | 已应用 | §2.3.2：`PlayerUnitCommon` 14 项参与哈希字段 + `Placement` / `RosterId` 2 项不参与哈希字段 |
| P28 | 已应用 | §2.4、§3.7.2：`SimState` 单例组件表追加第 10 项 `EngagementState`（03 §2.4） |
| P29 | 已应用 | §2.4、§3.7.2：单例组件表补齐各规格精确小节号 |
| P30 | 已应用 | §2.5：`SimConfig` 增加 `AutoChoicePrompts`（默认 `true`）与 `EnemyAiHooksOverride` |
| P31 | 已应用 | §2.5、§3.9.1、§5 #24：`SimConfig` 增加 `CaptureDebug`（默认 `false`）；写回放时 `RandomOverride != null` 或 `EnemyAiHooksOverride != null` 抛 `InvalidOperationException` |
| P32 | 已应用 | §2.5：`PlacedUnit` 增加 `FirstNightAtNewPosition` 与 `RosterId` |
| P33 | 已应用 | §2.5：`UnitSettings` 完整字段定义（02 辐射策略细项 + 03 按武器交战规则字典） |
| P34 | 已应用 | §2.5：`CarryIn` 完整合并定义（02/03/04/05 全部跨夜带入字段） |
| P35 | 已应用 | §2.6、§3.2 第 3a 步：`SimContext` 增加 `Terrain`、`EnemyAiHooks`、`ThreatGrid`、`TrackGrid` 只读属性 |
| P36 | 已应用 | §3.2 第 7 步：`PlacedUnit` 写入 `Placement`、`RosterId`、`NewPositionPenalty`；对 `FireUnit` 调 `FireUnitFactory.Init`（只建空 `Launchers`） |
| P37 | 已应用 | §3.2 第 8 步：按 `RosterId` 拷贝 `UnitCarryIn` 标量字段；其余字段由各系统在步骤 9 `Initialize` 中读取 |
| P38 | 已应用 | §3.2 第 9a 步：调用 `CommandStage.Initialize(ctx)`（校验剧情波次引用、初始化 `CommandPoints`） |
| P39 | 已应用 | §3.2 第 10 步：命令处理者注册纳入 14 个系统 + 阶段 0 组件 `CommandStage` |
| P40 | 已应用 | §3.4：`CommandStageHooks()` 明确为 `DeploymentStage.Run(ctx) → ChoiceStage.Run(ctx) → StoryStage.Run(ctx)` |
| P41 | 已应用 | §3.5：`AllClear()` 5 项条件定稿（直接判 `Pending` / `Injections` 队列、仅弹药与有未完成投放的平台阻塞清场、拦截弹清空、`HeldWaves` 清空、无待触发剧情生成） |
| P42 | 已应用 | §3.5：`NightResult` 追加 `Civil`、`Support`、`Commands`（`CommandSummary`），定稿 `CarryOut` 与 `JsonSerializerOptions` |
| P43 | 已应用 | §3.1.3、§3.1.5：`NightSeed(runSeed, levelId, nightSeq)` 调用约定（战役传 `flow.nights[]` 1-based 下标） |
| P44 | 已应用 | §2.7、T-00-26：`SimSnapshot.Debug`（`DebugView` / `DetectionDebugView`）及只读不影响状态哈希测试 |
| P45 | 已应用 | §2.7：`GlobalView` 合并字段（01 + 03 + 04） |
| P46 | 已应用 | §2.7：四类我方单位视图公共追加字段与各专有视图引用 |
| P47 | 已应用 | §0.5：`sim/` 目录结构追加 `Movement/`、`EnemyAi/`、`Campaign/`、`Economy/`、`Save/`、`Production/`、`Research/` 及 `Commands/` 组件清单 |
| P48 | 已应用 | §0.4.6：`Geo` 公共函数增加 `PointInPolygon` 与 `FirstEntryIntoCircle`（全目录唯一实现） |
| P49 | 已应用 | §7 T-00-35：`LoadedFiles.Count == 35`（26 个全局 + 8 个关卡 JSON + 1 个 PNG） |
| P50 | 已应用 | §8：Q5、Q7、Q10、Q11、Q15、Q16、Q17（连同 Q1–Q4、Q6、Q8、Q9、Q12–Q14 全部 17 项）标为已决 |

### 2. `A_interfaces.md` 第 2–5 节跨文件条目（涉及 00 的部分）

| 编号 | 处置 | 位置 / 说明 |
|---|---|---|
| A-2-05 | 已应用 | §4.2 事件 `310 PlayerUnitDestroyed`：末尾追加 `Vec2 Pos` |
| A-2-06 | 已应用 | §2.3.1 `Threat` #14 `HomingUnitId`：标明写者为系统 6 `EmissionSystem` |
| A-2-07 | 已应用 | §2.3.1 `Threat` #43：追加 `bool EwEverCovered` |
| A-2-09 | 已应用 | §2.2.2 `Interceptor` 增加 `int TargetPathVersion`；§4.2 事件 `303 InterceptorExpired` 的 `InterceptorExpiryCause` 含 `TargetManeuvered = 1` |
| A-2-10 | 已应用 | §2.5 `SimConfig.EnemyAiHooksOverride`、§2.6 `SimContext.EnemyAiHooks` |
| A-2-12 | 已应用 | §4.2 事件 `205 EmitterSwitched`：`EmitterSwitchCause` 含 `RadarDestroyed = 6, Suspended = 7` |
| A-2-13 | 已应用 | §2.3.2 `PlayerUnitCommon` #8 统一命名为 `NewPositionPenalty`（初值来自 `PlacedUnit.FirstNightAtNewPosition`） |
| A-2-17 | 已应用 | §3.4.1、§4.3：耗点命令统一在 `Validate` 末步调 `CommandPointRules.CanSpend`、在 `Apply` 首步调 `Spend` |
| A-2-18 | 已应用 | §2.5 `CarryIn`：`KnownTargetRecord` 增加 `int RosterId`，指挥点加成统一命名为 `CommandPointsBonus`；§3.2 第 9a 步按上限截断 |
| A-2-20 | 已应用 | §2.2.2 `FireUnit` 增加 `int LaunchersLost`；§3.5 `CarryOut` 完整定义 |
| A-2-21 | 已应用 | §1.6.11 `SupportDef.RadiusM` 可空，导航欺骗类支援在 `SupportRulesDef.GpsSpoofing.RadiusM` 给默认值 `30000` |
| A-2-22 | 已应用 | §2.5 `CarryIn` 纳入 `FighterSortiesDelta`、`AutoResolve`、`Dossier`、`ActiveSupports`、`Adaptation`；§3.2 第 8 步对未实现的 M3+ 字段非空抛 `E_NOT_IMPLEMENTED` |
| A-2-23 | 已应用 | §0.4.6 `Geo.PointInPolygon` 提升至 `Nightwatch.Sim.Core.Geo` |
| A-2-24 | 已应用 | §1.6.8 `SensorDef` 合并 02 所需字段（`FalseAlarm`、`TrackConfirmSec`、`ProducesQuality`、`CanProvideCue`） |
| A-2-25 | 已应用 | §1.6.7 `WeaponDef` 合并 03 所需全部字段及加载期默认归一 |
| A-2-26 | 已应用 | §0.4.6 `Geo.FirstEntryIntoCircle` 提升至 `Nightwatch.Sim.Core.Geo` |
| A-2-29 | 已应用 | §1.6.6 `AirDefenseUnitDef.EngageMoving` 归单位定义，不在 `WeaponDef` |
| A-2-30 | 已应用 | §1.6.1 `LevelMetaDef.FighterSortiesPerNight` |
| A-3-01 | 已应用 | §2.3.1 `Threat` #26、`#28`、`#30` 统一加 `M` 后缀（`HoldOrbitArcM`、`PreReleaseOrbitArcM`、`PathTotalM`） |
| A-3-02 | 已应用 | §1.6.10 `PlatformDef.Behavior` 类型定为 `PlatformBehavior` 强类型枚举 |
| A-3-03 | 已应用 | §1.6.2 `WaveDef.AiTags` 定为 `IReadOnlyList<AiTag>` |
| A-3-04 | 已应用 | §1.6.1 `VictoryConditionDef.Type` 定为 `VictoryConditionType` 枚举 |
| A-3-05 | 已应用 | §2.3.2、§4.2：我方单位四分类枚举定名为 `PlayerUnitCategory`（不与 `EntityKind` 混名） |
| A-3-06 | 已应用 | §4.1、§4.3：明确 05 的 `CampaignRejectReason` 为独立枚举，不合入夜内 `CommandRejectReason` |
| A-3-07 | 已应用 | §4.2 事件 `207 EwDiverted`、`208 EwLinkCut`：来源字段统一命名为 `int SourceId` |
| A-3-08 | 已应用 | §2.2.2 `Track` 字段定稿为 `DecoyCheckedQuality : TrackQuality?` |
| A-3-09 | 已应用 | §1.6.6 `AirDefenseUnitDef.FireControlRadar` 复用 `SensorEmbeddedDef` |
| A-3-10 | 已应用 | §1.6.9 `MunitionDef` 子母弹字段定名为 `ClusterChildMunitionId`、`ClusterSubmunitionCount` |
| A-3-11 | 已应用 | §1.6.12 `RulesSet.Intercept.Modifiers` 扁平访问约定 |
| A-4-02 | 已应用 | §4.2 事件 `303 InterceptorExpired` 的 `InterceptorExpiryCause` 含 `TargetArrived = 2` |
| A-4-03 | 已应用 | §3.5 `AllClear()` 第 1 条直接判 `Pending.Count == 0 && Injections.Count == 0`，不读 `AllWavesSpawned` 缓存 |
| A-4-04 | 已应用 | §4.2 事件 `208 EwLinkCut` 追加 `string DefId`；§6.1 追加不变量 #9（被移除 `Threat` 的终结事件守恒） |
| A-4-05 | 已应用 | §3.2 第 7–9 步明确 `FireUnitFactory.Init` 与 `CarryIn` 标量 / 发射架余弹的分阶段初始化顺序 |
| A-4-06 | 已应用 | §4.2 明确 `AtSec` 窗口归一化规则（`tSec > (Tick - 1) * StepSec ? tSec : null`） |
| A-5-01 | 已应用 | §3.1.5 明确 `night:` 前缀专用于 `NightSeed`，战役层 `ChildSeed` 派生名必须以 `campaign:` 开头 |

### 3. `B_decisions.md` 与 `C_coverage.md` 条目（涉及 00 的部分）

| 编号 | 处置 | 位置 / 说明 |
|---|---|---|
| B-T1-01 | 已应用 | §3.5、§8 Q3：失败条件达成当步立即结束当夜 |
| B-T1-02 | 已应用 | §1.2、§8 Q6：`…Pct` 后缀加载时 `÷ 100`，C# 属性名改为 `…Frac` |
| B-T1-03 | 已应用 | §2.3.2、§8 Q7：我方单位部署/撤收/移动状态机归 04 |
| B-T1-04 | 已应用 | §1.4.2、§8 Q14：未知字段严格报 `E_UNKNOWN_FIELD` |
| B-T1-05 | 已应用 | §3.4、§8 Q15：剧情事件由 04 `StoryStage` 在阶段 0 执行 |
| B-T2-06 | 已应用 | §2.3.2、§2.5、§3.2：新阵地首夜字段统一为 `PlacedUnit.FirstNightAtNewPosition` → `PlayerUnitCommon.NewPositionPenalty` |
| B-T2-07 | 已应用 | §2.1、§3.1.3、§3.1.5、§8 Q10：`NightSeed` 战役模式传 `nightSeq`（`flow.nights[]` 1-based 下标） |
| B-T2-08 | 已应用 | §3.5、§8 Q2：`AllClear()` 中已投完弹返航平台与纯侦察平台不阻塞清场 |
| B-T2-15 | 已应用 | §3.1.4、§3.4、§4.3、§8 Q5：阶段 0 子步顺序固定；空袭警报命令与每步更新统一归系统 13 `ScoringSystem` |
| B-T2-16 | 已应用 | §2.2.1、§8 Q16：保留 `EntityKind.Debris = 9` 槽位，运行时瞬时结算、存储恒空 |
| B-T2-17 | 已应用 | §1.1.1、§1.3、§1.4.2、§1.6.2、§3.2、§5 #27、§7 T-00-39、§8 Q1：`NightDef.Date` 按夜日期解析与 `E_NIGHT_DATE_MISMATCH` 校验 |
| B-T2-18 | 已应用 | §1.6.1、§8 Q4：`survive_game_sec` 加载校验 `≤ 各夜 durationGameSec 之和` |
| B-T2-19 | 已应用 | §0.4.5、§8 Q8：方位角从正北顺时针 `[0, 2π)` |
| B-T2-20 | 已应用 | §3.8、§3.9.1、§8 Q9：维持同平台回放一致，`runtime` 不同时打印警告 |
| B-T2-21 | 已应用 | §2.7、§8 Q12：`SimSnapshot.Threats` 仅调试 / 战后复盘可见 |
| B-T2-36 | 已应用 | §3.5 `CarryOut`：增加 `bool UrbanNavJamTriggered` |
| B-T3-06 | 已应用 | §3.4.2、§8 Q13：事件缓冲 `_outbox` 不设上限 |
| B-T3-07 | 已应用 | §2.5 `CarryIn.AutoResolve`、§8 Q11：自动结算修正项与重打覆盖 |
| C-T1-01 | 已应用 | `tools/spec_calc/00/`（`simrandom_vectors.py`、`hasher_vectors.py`）入库；§7 引用路径更新 |
| C-T1-04 | 已应用 | §0.4.4、§6.2：`BannedSymbols.txt` 禁用 `Math.Hypot`，欧氏距离统一写 `Math.Sqrt(dx*dx + dy*dy[+ dz*dz])` |
| C-T1-08 | 已应用 | §2.6 `SimContext`、§3.2 第 3a 步、§3.3.1、§3.4：新增 `SpatialGrid`（`ThreatGrid` / `TrackGrid`）加速契约，保证与全表扫描逐位一致 |
| C-T1-10 | 已应用 | §0.1、§3.1.5：引用新建 [`07_tools.md`](../07_tools.md) |
| C-T1-12 | 已应用 | §0.3：添加文档同步免责声明（本规格已与 GDD / 数值表 / WBS 同步收口，进入实现前无需再次停下询问） |
| C-T1-16 | 已应用 | §3.3.1：明确空闲步早退（O(1) 返回、零临时集合分配）要求 |
| C-T2-02 | 已应用 | §3.3.1：明确单步性能预算（同屏 50 `Threat` × 15 单位 × 20 `Interceptor` 下均值 `< 2 ms`、p99 `< 4 ms`、最坏 `< 50 ms`、空闲步 `≤ 20 µs`） |

## 01_spawn_movement_terrain.md

| 条目编号 | 状态 | 修改位置与说明 |
|---|---|---|
| P01, P05–P07, P11, P14, P18–P19, P23, P29–P31, P35, P41, P45–P46, P48–P49 | 已应用 | §1.1–1.5、§2.1–2.4、§3.1–3.4、§4、§8.2：数据模型（`MovementRulesDef`、`TerrainRulesDef`、`PlatformDef`）、`Threat` 前 32 个哈希字段（弧长统一 `…ArcM` 后缀）、`WaveState` / `PendingSpawn` / `WaveInjection`、事件 100–104 全部与 `00_core.md` 对齐 |
| A-2-01..04, A-2-06, A-2-09..10, A-2-23, A-2-26..29 | 已应用 | §2.2、§3.1.9、§3.2.6、§3.3、§8.3：`TrajectoryPredictor.Predict` 的 `AtPathEnd` 语义、平台不发 `ThreatArrived`、`TargetUnitId`/`HomingUnitId` 单写者归属、`ThreatRouting`（`Retarget`/`BeginEgress`/`Hover`）统一改航入口、`IEnemyAiHooks` 扩展签名、复用 `Geo.FirstEntryIntoCircle`、直接用 `s.Hp > 0` 判定存活建筑 |
| A-3-01..04, A-3-08..09 | 已应用 | 全文统一 `TimeSec`、弧长 `…ArcM`、`Geo.FirstEntryIntoCircle`、`AvoidanceActive` 命名 |
| A-4-02..04, A-4-06 | 已应用 | §3.1.2、§3.2.5、§4.1、§6：终结事件守恒、同一步先到达后拦截时序、`AtSec` 窗口归一化 `(t-1, t]`、压制波/剧情注入阻塞 `AllClear` |
| B-T1-06 | 已应用 | §1.1、§3.2.5、§3.3.3、§8.1 Q13–Q15：`decoy_flight` 飞越假目标后直线出界发 `ThreatExited { DecoyPathEnd }`；地球曲率 `6371000 m` 与大气折射 `k = 4/3`；`losSampleStepPx = 0.5` |
| B-T2-03, B-T2-19..20, B-T2-22..31 | 已应用 | §1.1–1.3、§3.1–3.3、§5、§8.1 Q1–Q15：高度转换 `GetGroundElevation`、入口点缺省海拔、平台投放距离/挂载缺省、弹道/滑翔忽略 `waypointsM`、`maxSpeedKmh` 预留、`weighted_random` 逐枚独立抽签、`IsStoryOnlyWave`、`aiTags` 联动、巡航恒定 AGL、地平线 720 方位桶预计算 |
| B-T3-05 | 已应用 | §3.1.2、§3.1.9：`IEnemyAiHooks.SelectWeightedRandomOverride` 支持暴露度达 100 时改打暴露友方单位 |
| B-T3-09 | 已应用 | §1.2.2、§2.2、§3.1.4、§3.2.4、§5 #24、§7 `T-01-28`/`T-01-28b`：发射平台从入口进场飞至 `releaseRangeM` 释放挂载并发 `PlatformReleased`，随后 `Egressing` 返航出界发 `ThreatExited { PlatformReturned }`；释放前被击毁则取消未释放挂载 |
| C-T1-01, C-T1-04, C-T1-12 | 已应用 | §0.3、§3、§7：`tools/spec_calc/01/`（`01_movement_calc.py`、`01_terrain_calc.py`）归档入库；不用 `Math.Hypot`；添加文档同步免责声明 |
| C-T2-01, C-T2-08 | 已应用 | §1.2.2、§2.4、§3.3.2–3.3.4、§7 `T-01-33`/`T-01-43`：`HorizonProfile` 改为 720 方位桶 × 径向单调非降累积最大遮挡斜率包络 $S_{\max}(b, k)$，修复多山脊近高远低遮挡漏洞并保持 $O(1)$ 查表；补充 `Su-34`、`Tu-22M3` 平台定义与测试用例 |

## 02_sensing_tracks_ew_emission.md

## 03_engagement_impact_scoring.md

## 04_enemy_ai_commands.md

## 05_campaign_economy.md

## 06_client_graybox.md

## 07_tools.md（新建）

## 上位文档（GDD / 数值表 / data / test_01）
