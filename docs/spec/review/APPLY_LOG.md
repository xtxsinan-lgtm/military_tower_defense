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

| 条目编号 | 状态 | 修改位置与说明 |
|---|---|---|
| P05, P06, P08, P09, P12, P15, P17–P20, P23–P26, P29, P32–P34, P36–P37, P44, P46, P48 | 已应用 | §1.1–1.11、§2.1–2.8、§3.1、§4.1–4.2、§8.2：数据模型（`TrackRulesDef.DetectionRules`、`SelfAcquisition`、`WeaponDef.ReactionSec`、`EwRulesDef`、`ExposureRulesDef`）、实体状态（`PlayerUnitCommon`、`EmitterControl`、`Track`、`Threat` 33–43 字段含 `EwEverCovered`）、事件 200–208 与命令 20–21 全部与 `00_core.md` 对齐 |
| A-2-05 | 已应用 | §3.5.7、§8.3：提供 `FireControlQueries`（`GetTargetFilterMultiplier`、`GetReactionTimeMultiplier`、`GetArmHitProbMultiplier`）供 03 消费 |
| A-2-06 | 已应用 | §2.6、§3.5.5、§6、§7 `T-02-56`–`T-02-58`：`TargetUnitId` 由 01/04 独占写入、02 只读不改；02 维护 `Threat.HomingUnitId`（辐射源关机时置 0，重开时恢复为 `TargetUnitId`） |
| A-2-07 | 已应用 | §2.6、§3.4.3、§6、§7 `T-02-30`/`T-02-31`：`Threat.EwEverCovered` 在首次进入开启的导航干扰/欺骗区时置 `true`（不论判定成败） |
| A-2-11 | 已应用 | §2.2、§3.5.5、§4.2、§7 `T-02-57`：新增 `EmissionChoiceEffects.ApplyArmChoice(state, unitId, silence)` 供阶段 0 `ChoiceStage` 静默辐射源（0 点指挥点） |
| A-2-12 | 已应用 | §2.1、§3.2.5、§3.5.1、§4.1、§6、§7 `T-02-14`：`FireUnit.RadarDestroyed` 或 `u.Suspended` 时强制关机并发出 `EmitterSwitched { RadarDestroyed / Suspended }`，不产生火控探测 |
| A-2-13 | 已应用 | §1.11、§2.1、§3.1.2、§3.2.3、§3.4.2：统一使用 `PlacedUnit.FirstNightAtNewPosition` 与运行态 `NewPositionPenalty` |
| A-2-17 | 已应用 | §4.2、§7 `T-02-64`：`SetEmissionPolicy` 与 `SectorEmissionOverride` 在阶段 0 经 `CommandPointRules.CanSpend / Spend` 校验与扣减指挥点（缺省 1 点，不足报 `NoCommandPoints`） |
| A-2-21 | 已应用 | §1.10、§2.9、§3.4.3、§7 `T-02-38`：国家级导航欺骗读取 `SupportAsset.State == SupportAssetState.Active` 与 `SupportAsset.RadiusM`（缺省 `30000` m） |
| A-2-22 | 已应用 | §1.11、§3.2.3、§3.3.3、§3.3.6、§3.6.1、§7 `T-02-24`：消费 `CarryIn.ActiveDoctrineId`（`forward_ambush` 首次开机前免除侦察暴露、`fire_group_network` 局部交叉升级包含火力组自主捕获）与 `CarryIn.Dossier`（`DecoyIdentificationBonus`） |
| A-2-26 | 已应用 | §2.1、§3.1.2、§3.2.3、§3.8、§7 `T-02-04`/`T-02-04b`：视线统一调用 01 的 `HorizonProfile.HasLineOfSightAgl`（展开及转移完成时调用 `TerrainModel.BuildHorizonProfile`） |
| A-2-27 | 已应用 | §3.1、§3.4.3、§3.4.4、§3.5.3、§7 `T-02-33`/`T-02-35`：复用 `Geo.PointInPolygon` 与 `Geo.FirstEntryIntoCircle`；电子战诱导/悬停/返航统一调用 `ThreatRouting.Retarget / Hover / BeginEgress` |
| A-2-28 | 已应用 | §3.1.2、§3.2.8、§7 `T-02-12`：初始化预警时间表排除 `WaveSpawnRules.IsStoryOnlyWave(night, w) == true` 的波次，运行期由 `WaveDefIndex` 查找 `WaveStarted` 波次并补发预警 |
| A-3-05, A-3-06, A-3-07 | 已应用 | §1.6、§3.4.3–3.4.4、§3.5.4、§4.1、§7：`PlayerUnitDestroyed.Category` 使用 `PlayerUnitCategory`；`TrackRulesDef.DetectionRules` 统一字段名；`EwDiverted`/`EwLinkCut` 来源字段统一命名为 `SourceId` |
| A-4-04 | 已应用 | §3.4.4、§3.4.5、§4.1、§7 `T-02-35`/`T-02-36`：`EwLinkCut` 追加 `string DefId`，且悬停超时坠毁移除前补发 `EwLinkCut { ThreatId, SourceId = 0, Outcome = Crash, DefId }` |
| B-T1-07, B-T1-08, B-T1-09, B-T1-10, B-T1-23, B-T1-24 | 已应用 | §1.8、§1.9、§2.5、§3.3、§3.4.7、§4.1、§8.1 Q2/Q15/Q37/Q38：按真实 `ThreatId` 关联航迹；删 `ew.json sideEffects.friendlyInterceptorDroneMult`；暴露速率字段改名 `…RatesPerGameSec`；删 `ratesPerGameSec` 重复三项；航迹标签名统一为 `Track.Tag`；`PlayerUnitDestroyed` 含 `Vec2 Pos` |
| B-T2-01, B-T2-02, B-T2-03, B-T2-04, B-T2-05, B-T2-06, B-T2-09, B-T2-14 | 已应用 | §1.4、§1.6、§1.9、§1.10、§3.2.3、§3.2.5、§3.4.2、§3.5.3、§7、§8.1：反应时间归 `WeaponDef.ReactionSec`（02 取单位武器最大值）；视线含 4/3 地球曲率；天线缺省高度统一归 `terrain.json.defaultAntennaHeightM = 10`；国家级导航欺骗半径 30 km；断电对主动雷达距离与电子战概率均 ×0.5；新阵地首夜对探测/火控距离与电子战概率均 ×0.7；光学自主捕获夜间无探照灯/热像乘 `opticalNightRangeMult = 0.3`；Orlan 侦察升档由 03 只读 `accuracy.spotterTierBoost` |
| B-T2-31..54 | 已应用 | §1–§4、§7、§8.1 Q1–Q36：径向地平线包络预计算、低空倍率、精确航迹仅归火控/自主捕获、火控雷达参数、电子战参数与链路中断权重、城区导航干扰 60 游戏秒触发城市资源 −1、反辐射导弹初始锁定距离、辐射策略缺省值、邻近雷达接替、侦察识破、诱饵辐射源、无线电链路无人机、自动探测单位闸门、昼夜与天气倍率、误报频率、民众上报与 B 线延迟、航迹不加随机误差、丢失时间 1 游戏秒、视线开关、诱饵条件概率、车载防护罩、反无人机枪全向、发射暴露仅计导弹 |
| B-T3-05, B-T3-06, B-T3-08, B-T3-10 | 已应用 | §1.9、§3.4.3、§3.5.4、§3.6、§3.7.1、§7 `T-02-38`、§8.1 Q6–Q12/Q18/Q19/Q39：`EmitterQueries.ListActive` 与 `DeceptionUnit.SeenThrough` 支撑 04 动态选目标；有火控单位自动置 `PendingRelocationAltId`、其余走手动转移命令；区域导航干扰与国家级导航欺骗同目标不叠加（取偏移期望较大者）；暴露度按真实开关机自然产生 |
| C-T1-01, C-T1-04, C-T1-09, C-T1-12, C-T1-13 | 已应用 | §0.4、§3.1、§3.5.3、§3.6.1、§7：`tools/spec_calc/02/calc_02.py` 入库并验算通过；全部距离改用 `Math.Sqrt(dx*dx + dy*dy)`（禁用 `Math.Hypot`）；反应时间统一读 `WeaponDef.ReactionSec`；添加文档同步免责声明；补大功率电子战站暴露测试用例 `T-02-76` |
| C-T2-01, C-T2-02, C-T2-07 | 已应用 | §1.5、§1.6、§1.9、§3.2.3、§3.2.5、§3.4.2、§3.8、§7 `T-02-04b`/`T-02-05`/`T-02-13`/`T-02-14`/`T-02-37`：配合 01 径向累积最大遮挡斜率包络并补 `T-02-04b`；新增 §3.8 `CoverageQuery`（雷达/传感器/电子战覆盖格点查询）；补齐 `TimeOfDay = Day`、`Season = Winter`（主动雷达与电子战 ×0.9）与夜间探照灯/热像规则 |
| 数据文件与 Schema 变更（B-T1-08..10, B-T2-01..05, B-T2-09, B-T2-32..50） | 留给后续（`data/` 与 `data/schema/`，D3 任务） | 规格已在 §1 与 §8.2G 完整定义新字段与兼容加载规则，实际 JSON 数据与 Schema 文件在 D3 阶段修改 |

## 03_engagement_impact_scoring.md

| 条目编号 | 状态 | 修改位置与说明 |
|---|---|---|
| P01, P06, P07, P14, P18, P19, P20, P24, P26–P29, P32–P34, P36–P37, P42, P45–P46, P48 | 已应用 | §1.1–1.3、§2.1–2.8、§3.2.1、§3.5.1、§3.8.6、§8.2：数据模型（`EngagementRulesDef`、`CivilRulesDef`、`WeaponDef`、`SupportDef`、`LevelMetaDef`）、实体字段（`PlayerUnitCommon`、`FireUnit.LaunchersLost`、`Threat` #44–47、`EngagementState` 单例哈希序 9）、`PlacedUnit.FirstNightAtNewPosition` → `NewPositionPenalty`、`UnitSettings.Engagement`、`CarryIn`/`CarryOut`、`NightResult`（含 `Civil`、`Support`、`Commands`、`CarryOut`）全部与 `00_core.md` 对齐 |
| A-2-05, B-T1-24 | 已应用 | §3.5.6、§4.2、§7 `T-03-38`：事件 `310 PlayerUnitDestroyed` 末尾追加 `Vec2 Pos` |
| A-2-07 | 已应用 | §0.1、§2.4、§3.5.3、§3.5.4、§3.5.7、§3.8.1、§3.8.4、§7 `T-03-35`/`T-03-40`/`T-03-52`：读取 02 写入的 `Threat.AccuracyTierDrop`（兼容别名 `EwTierDrop`）、`Threat.EwExtraOffsetM`（兼容 `EwAffected`）、`Threat.EwEverCovered`（兼容 `EwCovered`）、`Threat.TargetUnitId` 与 `Threat.ArmHitProbMult` |
| A-2-08 | 已应用 | §0.1、§2.2、§3.2.4、§3.2.5、§3.5.6：通过 02 `IFireControlQueries` 读取 `IsFireControlActive`、`HasFireControlRadar`、`ReactionTimeMult`、`IsEmissionSilentHold`（并支持测试替身直接写 `FireUnit` 镜像字段） |
| A-2-09 | 已应用 | §2.5、§3.2.6、§3.3.1、§4.1、§4.2、§5 #4b、§7 `T-03-57`：发射拦截弹时记录 `TargetPathVersion`；`InterceptorSystem` 步首扫描本步 `ThreatManeuvered` 事件，使指向机动目标的在途拦截弹按 ID 升序发出 `InterceptorExpired { Cause = TargetManeuvered }` 并移除 |
| A-2-10, B-T3-06 | 已应用 | §0.1、§3.2.4、§5 #17、§7 `T-03-15`：航迹标签读取 `Track.Tag`（兼容别名 `PerceivedTag`）；当 `Track.Quality == Vague`（`Track.Tag == null`）时回退读取真实目标 `t.Tag` 做高炮/机枪武器目标集匹配，而交战规则标签过滤仍要求已识别标签 |
| A-2-13, B-T2-06 | 已应用 | §2.1、§2.2、§3.2.1、§3.3.2：`FireUnit.NewPositionFirstNight` 统一与 `PlayerUnitCommon.NewPositionPenalty`（来自 `PlacedUnit.FirstNightAtNewPosition`）双向同步 |
| A-2-17 | 已应用 | §0.1、§3.4.1、§3.7.1、§4.3：耗点命令（`SetEngagementRule` 默认 1 点、`CallSupport` 按定义、`SetAirRaidAlert` 默认 1 点）统一在 `Validate` 末步调 `CommandPointRules.CanSpend`、在 `Apply` 首步调 `Spend`；`SetFighterZone` 消耗 0 点 |
| A-2-18, A-2-19, A-3-01 | 已应用 | §2.3、§2.8、§8.2：`UnitSettings`、`GlobalView`、`SimState.Engagement` 状态哈希序号与 `00_core.md` 对齐 |
| A-2-20, A-3-10 | 已应用 | §2.2、§2.8、§3.5.6、§3.8.1、§3.8.6：新增 `FireUnit.LaunchersLost`、`ScoringState.DestroyedUnitSnapshots` / `DestroyedExposureEnd` / `UnitHits` / `KillsByEnemy` / `ThreatsEverEwCovered` / `ArmDetections` / `ArmShutdowns`；移除每步 `ExposureMax` 全单位循环（利用夜内暴露度单调不减性质，仅在 `Destroy` 时快照亡者暴露度与战果）；完整组装 `CarryOut` |
| A-2-21, B-T2-87 | 已应用 | §1.3.1、§3.4.2、§8.1 Q-S5：`SupportDef.RadiusM` 可选，国家级导航欺骗优先取 `SupportDef.RadiusM`，缺省回退取 `affectsSameAsEwUnit` 电子战单位的 `RadiusM` |
| A-2-23 | 已应用 | §3.0、§8.3：`Geo.PointInPolygon` 提升至 `Nightwatch.Sim.Core.Geo` 全库共用 |
| A-3-05 | 已应用 | §3.5.6、§4.2、§7 `T-03-38`：事件 `309 PlayerUnitDamaged` 与 `310 PlayerUnitDestroyed` 中单位分类字段名统一为 `PlayerUnitCategory Category` |
| A-3-09 | 已应用 | §3.2.1、§3.5.1、§8.3：明确三阶段初始化（阶段 1 `Initialize` 创建结构与初始弹药池 → 阶段 2 `RestoreCarryIn` 恢复跨夜弹药/战损/结构 HP → 阶段 3 `PostDeployInit` 生成扇区覆盖虚拟单位并连接电网） |
| A-4-01 | 已应用 | §0.1、§3.2.4、§3.4.3：候选目标筛选显式跳过 `t.Phase == ThreatPhase.Arrived` 的已到达目标 |
| A-4-02 | 已应用 | §3.3.1、§4.1、§4.2、§5 #4、§7 `T-03-57`：同一步先到达（Order 2 `ThreatArrived`）后拦截（Order 8）时，比较 `m.InterceptAtSec` 与 `arrivedEvt.AtSec`：拦截弹更早则正常掷骰（命中删除目标，Order 10 跳过），否则发出 `InterceptorExpired { Cause = TargetArrived }` |
| A-4-04 | 已应用 | §2.8、§3.8.1、§3.8.6、§6 #8、§7 `T-03-58`：`ScoringSystem` 订阅 `MunitionReleased` 与 `EwLinkCut(Crash)`，计入 `ThreatsSpawned`、`ThreatsEwDowned`、`ThreatsArmMissed`，确立每步末尾威胁守恒不变量 |
| A-4-06 | 已应用 | §3.2.6、§3.3.1、§4.2、§6 #2：`LaunchAtSec` 与 `InterceptAtSec` 写入前调用 `NormalizeTime`（吸附半开窗口 `(Tick - StepSec, Tick]` 边界 `1e-9` 漂移），发出 `InterceptResolved` 时规范化 `AtSec` |
| B-T1-16, B-T2-36 | 已应用 | §3.8.6：`CarryOut` 汇总 `StoryChoiceResults` 与 `CustomMetrics["urban_nav_jam_triggered"]` |
| B-T2-12..22, B-T2-61..92 | 已应用 | §1–§5、§8.1 Q-E1..Q-X4：全部 49 个设计/数值待决项定稿并在 §8.1 逐条标为“已决议”（含拦截弹速度、反应时间与射击间隔、34 发点射、5 次连射冷却 60s、光电火控精确航迹、修正链连乘、侦察平台全图升档单源 `spotterTierBoost`、电网无向 BFS 与 `fraction` 崩溃阈值、空袭警报参数、支援呼叫与大空袭拒绝退费等） |
| B-T2-52 | 已应用 | §0.1、§3.5.6、§7 `T-03-38`：非碎片直接落地伤害在 `ApplyUnitEffect` 前调用 `EwQueries.ShieldHitProbMult`，当 `< 1.0` 时掷 1 次 `impact` 子流骰判定车载自卫电子战偏转 |
| B-T2-89 | 已应用 | §2.1、§3.2.1、§3.5.6、§3.6.2、§3.8.6、§8.1 Q-S9：实现 `adjacent_sector_coverage`（`CarryIn.SectorCoverageSites` 在 `PostDeployInit` 生成 `IsVirtualSectorCoverage = true` 的场外虚拟火力单元，火控恒开、不受伤、不耗弹药池、不进入 `CarryOut`） |
| B-T3-01 | 已应用 | §1.2、§3.8.3、§7 `T-03-51`、§8.1 Q-X1：潜在损失公式改为 `max(enemyCost, 2^(damageLevel - 1) × LossMusdBase(0.1 M$) × structureWeight)`，重算 `T-03-51` 全部断言值 |
| B-T3-02, C-T1-14 | 已应用 | §3.2.2、§5 #49、§7 `T-03-20`、§8.1 Q-E9：多火力单元开火分配按期望单发成本 `shotCostMusd / max(p, 0.05)` 升序；昂贵武器就绪时若更便宜武器已锁定同一目标且在反应计时中、并在目标落地前留有至少 `ShotIntervalSec` 补射余地，则昂贵武器本步礼让 |
| B-T3-03 | 已应用 | §1.3.2、§3.3.1、§8.1 Q-I3：确认敌方 `hp` 仅作百科/UI 展示，模拟层一击必杀（耐受度已折入基础拦截概率与 `interceptProbMult`） |
| B-T3-08 | 已应用 | §3.5.3、§3.5.4、§8.1、§8.3 B4：读取 02 `ReconcileNavAccuracy` 统一合成后的 `AccuracyTierDrop` 与 `EwExtraOffsetM`，单位级导航干扰与国家级导航欺骗不双重叠加 |
| C-T1-02 | 已应用 | `tools/spec_calc/03/calc_03.py` 归档入库；修复 `T-03-09` 第 3 条笔误（`0.5 × 0.7 = 0.35`）；重算并验证 `T-03-01..58` 全部数值 |
| C-T1-04 | 已应用 | §0.3、§3.0、§3.1.2、§3.2.4：补充跨平台确定性约束（禁用 `Math.Hypot`，统一使用 `Math.Sqrt(dx*dx + dy*dy)` 与 `BitConverter.DoubleToInt64Bits`） |
| C-T1-05 | 已应用 | §3.1.2、§3.2.4、§7 `T-03-56`：引入 `Threat.MaxSpeed3DMps` 粗筛、`k0` 采样起点下界裁剪、以及按几何最早拦截时间下界 `lbTime` 排序的惰性优先队列，保证与朴素全航迹扫描 100% 逐位等价（`calc_03.py` 2000 组随机压力场景 0 差异） |
| C-T1-12 | 已应用 | §0.3：添加文档同步免责声明（本规格已与 GDD / 数值表 / WBS 同步收口，进入实现前无需再次停下询问） |
| C-T1-16 | 已应用 | §3.2.2、§3.3.1、§3.5.2：`EngagementSystem`、`InterceptorSystem`、`ImpactSystem` 均补充空闲步 $O(1)$ 早退路径 |
| C-T2-03 | 已应用 | §1.3.4、§2.8、§3.0、§3.8.1、§3.8.6、§7 `T-03-58`：`RestrictedZoneDef` 增加 `NeighborCountry`，`ScoringSystem` 检测落入邻国的拦截弹、拦截碎片与被诱偏弹药并记入 `LossesSummary.BorderViolations` |
| C-T2-04 | 已应用 | §1.2、§3.7.1、§4.3、§7 `T-03-58`：`AlertRulesDef` 增加 `AvailableFromLevel = 6`；`SetAirRaidAlert` 在 `Meta.Number < AvailableFromLevel` 时拒绝并返回 `NotAvailable` |
| C-T2-05 | 已应用 | §3.5.2、§3.5.6、§5 #27b、§7 `T-03-43`：当 `debris.UrbanRadiusM == 0`（`urbanInterceptRadiusCells == 0`）时，城区拦截碎片按 1 km 网格同格判定 `SameCell(e.Pos, target.Pos, cellM)` 施加碎片伤害 |
| C-T2-10 | 已应用 | §3.1.2、§7 `T-03-01`..`T-03-06`、`T-03-11`、`T-03-20`、`T-03-26`、`T-03-34`：`InterceptSolver` 二分迭代固定为 32 次（精度 `< 2.4e-10 s`），并同步更新 §7 全部期望值 |
| 数据文件与上位文档同步（`rules/engagement.json`、`rules/civil.json`、`rules/damage.json`、`support/fighters.json`、`GDD`、`塔防数值表`） | 留给后续（`data/`、`docs/游戏设计文档_GDD_v1.md`、`docs/塔防数值表_v1.md`，D2b-08 / D3 任务） | 03 规格正文与 §1 / §8.2 已完整定义所有新增规则文件、Schema 字段与默认值，实际 JSON 数据与上位文档在对应任务中修改 |

## 04_enemy_ai_commands.md

| 条目编号 | 状态 | 修改位置与说明 |
|---|---|---|
| P01, P08, P12, P19, P20, P22, P24–P25, P27, P29–P30, P32–P35, P38–P42, P45–P48 | 已应用 | §1.1–1.4、§2.1–2.5、§3.1–3.9、§4.1–4.2、§8.2：数据模型（`EnemyAiRulesDef`、`CommandRulesDef`、`EventsFileDef`、`ChoicesFileDef`）、实体公共字段（`PlayerUnitCommon.DeployPhaseEndTick` / `Relocation` / `PendingRelocationAltId`）、`ChoiceRequest`（移除重复 `CreatedTick`）、`CommandState`（含 `RelocationsCompleted`）与 `EnemyIntelState`（单例哈希序 7、8）、阶段 0 三子阶段顺序、`AllClear()` 追加条件、`NightResult.CarryOut` 与 `CommandSummary`、快照视图全部与 `00_core.md` 对齐 |
| A-2-05, B-T1-24 | 已应用 | §3.2.2、§3.8.2、§7 `T-04-04`/`T-04-72`：消费事件 `310 PlayerUnitDestroyed`（含 `Category`、`SourceThreatId`、`Pos`） |
| A-2-10 | 已应用 | §3.3.0、§3.3.2–3.3.5、§8.3：`IEnemyAiHooks` 完整实现（`DeferGroup`、`SaturationSpawnTimes`、`SelectKnownTarget`、`SelectAirDefenseTarget`、`SelectWeightedRandomOverride`、`AdjustAvoidance`）与 `EnemyAiQueries.AvoidanceActive(ctx)` |
| A-2-11 | 已应用 | §3.7.3、§7 `T-04-61`、§8.3：回答自动二选一时调用 `EmissionChoiceEffects.ApplyArmChoice(ctx, unitId, silence)`（消耗 0 指挥点） |
| A-2-15 | 已应用 | §3.5.1、§3.5.3、§7 `T-04-41`、§8.3：`DeploymentValidator` 增加单点放置检查入口 `CheckPlacement(level, plan, replaceIndex, candidate)` 供 05 战役层与 06 部署界面复用 |
| A-2-17 | 已应用 | §3.6、§4.2、§7 `T-04-50`/`T-04-51`、`8.3`：`CommandPointRules`（`CostOf`、`CanSpend`、`Spend`、`Refund`、`BuildSummary`）统一全模块耗点命令校验与扣减约定 |
| A-2-18 | 已应用 | §1.5、§2.3、§3.1.1、§3.2.1、§3.2.6、§7 `T-04-01`/`T-04-27`/`T-04-52`：`CarryIn.CommandPointsBonus` 统一命名并按 `economy.commandPointsPerNight.max` 截断；`KnownTargetCarry` 增加 `string? RosterId` 与 `bool Priority = false` |
| A-2-23 | 已应用 | §3.5.2、§8.3：部署多边形判定直接调用 `Nightwatch.Sim.Core.Geo.PointInPolygon`（不保留私有副本） |
| A-2-25 | 已应用 | §3.5.3、§7 `T-04-42`、§8.3：部署校验第 9 步调用 02 `EmissionPolicyRules.CheckAvailable(level, p.UnitId, policyId)` |
| A-2-30, A-3-09 | 已应用 | §3.3.5、§3.7.2、§8.3：火控雷达参数使用 `SensorEmbeddedDef`；武器分目标最大射程统一通过 `WeaponParams.RangeFor(w, tag)` 与 `MaxRangeAgainst(u, tag)` 读取 |
| A-3-01 | 已应用 | §2.2：`ChoiceRequest` 移除与 `EntityHeader.CreatedTick` 重复的字段声明，哈希与超时计算读取 `EntityHeader.CreatedTick` |
| A-3-05 | 已应用 | §3.3.2、§7 `T-04-08`：消费 02 `EmitterQueries.ListActive` 返回的 `ActiveEmitter.EntityKind`（`EntityKind.Sensor` → `Radar`，`EntityKind.EwUnit` → `Ew`，其他 → `AirDefense`） |
| B-T1-03, B-T1-05 | 已应用 | §3.1、§3.4、§3.8：确认我方单位部署/撤收/移动状态机与剧情事件触发统一归 04 阶段 0 执行 |
| B-T2-11, B-T2-78, B-T2-79, B-T2-88..104 | 已应用 | §1–§4、§8.1 Q-A1..Q-A12 / Q-D1..Q-D8 / Q-C1..Q-C6 / Q-S1..Q-S4：全部 30 项待决问题定稿并标为“已决”（含 `precision_exposure` 正式默认权重 `3.0`、`StoryActionDef.On` 可选布尔支持 `set_alert` 解除警报、夜间不从预备队新部署、各级单位转移规则、指挥点消耗与退费、二选一超时与并发上限等） |
| B-T3-05 | 已应用 | §0.2 K1、§1.1.1、§1.5、§2.4、§3.2.2–3.2.3、§3.2.6、§3.3.0、§3.3.2、§6 #4、§7 `T-04-03`/`T-04-25`/`T-04-27`、§8.1 Q-A1：暴露度达 100 时加入当夜 `KnownTargets`（权重 3.0），并经 `TriggerExposure100Retarget` 从当夜剩余待发波次中把原本打 `weighted_random` 的组按 `retargetFrac = 0.25`（优先 `preferAttracts` 弹药）改向至该单位位置（每单位每夜最多触发一次当夜改向，经 `SelectWeightedRandomOverride` 零随机数消费生效）；若当夜已无匹配待发波次，则在 `CarryOut.KnownTargets` 标记 `Priority = true` 由次夜优先打击 |
| B-T3-06 | 已应用 | §3.4.3、§8.1 Q-D2：夜间移动在 M1/M2 采用直线匀速并只检查目的地合法性 |
| C-T1-01 | 已应用 | `tools/spec_calc/04/calc_04.py` 入库并验算通过；§7 引用路径更新 |
| C-T1-04 | 已应用 | §0.4、§3.3.4、§3.3.5、§3.4.3：补充跨平台确定性约束（禁用 `Math.Hypot`，距离统一使用 `Math.Sqrt(dx*dx + dy*dy)`） |
| C-T1-06 | 已应用 | §2.4、§3.3.2、§3.3.6、§6 #12、§7 `T-04-07`：`EnemyIntelState` 维护 `AssignedByUnit`、`AssignedByPos`、`ArmAssignedByUnit` 增量字典，替代 $O(\text{KnownTargets} \times \text{Threats})$ 全表扫描，并在 `CheckInvariants` 校验等价性 |
| C-T1-07 | 已应用 | §2.4、§3.3.5、§7 `T-04-22`：`EnemyIntelState` 维护 `AvoidanceGridVersion` 与 `AStarCache`，对同网格版本、同 `(A50Active, startCell, goalCell)` 的绕行请求直接复用缓存航点，消除多枚巡航导弹同格生成的重复 A\* 搜索 |
| C-T1-08 | 已应用 | §3.2.2、§7 `T-04-06`：`ProbeCheck` 条件 B 改用 `ctx.ThreatGrid.QueryCircle(fu.Pos, R)` 空间网格查询 |
| C-T1-12 | 已应用 | §0.4：添加文档同步免责声明（本规格已与 GDD / 数值表 / WBS 同步收口，进入实现前无需再次停下询问） |
| C-T1-16 | 已应用 | §3.1.2、§3.2.2：`CommandStage` 与 `EnemyIntelSystem` 补充空闲步 $O(1)$ 早退路径 |
| C-T2-01 | 已应用 | §3.3.5：绕行网格 `Covers` 对防空火力单元优先复用 `u.HorizonProfile.HasLineOfSightAgl`，与 01/02 的 720 方位桶径向累积最大遮挡斜率包络保持一致 |
| C-T3-01 | 已应用 | §3.7.2、§4.1、§8.1 Q-C5/Q-C6、§8.3 B-06：明确客户端表现层在 `ChoiceRequested` 期间于叙事/普通难度自动暂停、硬核难度降为 1/60×（1 世界秒/真实秒）慢放 |
| 数据文件与上位文档同步（`rules/enemy_ai.json`、`rules/commands.json`、`events.schema.json`、`GDD`、`塔防数值表`） | 留给后续（`data/`、`docs/游戏设计文档_GDD_v1.md`、`docs/塔防数值表_v1.md`，D2b-08 / D3 任务） | 04 规格正文与 §1 / §8.2 已完整定义所有新增规则文件、Schema 字段与默认值，实际 JSON 数据与上位文档在对应任务中修改 |

## 05_campaign_economy.md

| 条目编号 | 状态 | 修改位置与说明 |
|---|---|---|
| P02, P23, P32, P34, P42, P43, P47, P50 | 已应用 | §0.1、§1.1、§2.3–2.4、§3.1.2、§3.2.1、§3.7.1、§8.3：数据加载入口 `DataLoader.LoadLevel(source, levelId, nightIndex)`（开局传 `null`、夜前传 `n.WavesNight`）、`PlacedUnit.RosterId` / `FirstNightAtNewPosition`、`CarryIn` / `CarryOut` 全字段（含 `StoryChoiceResults`、`UrbanNavJamTriggered`）、`NightSeed(runSeed, levelId, index + 1)`、`sim/` 目录划分全部与 `00_core.md` 对齐 |
| A-2-13, B-T2-06 | 已应用 | §2.3、§2.4.1、§3.7.1–3.7.2、§8.3 R-00-1、§8.4 B3：新阵地首夜惩罚统一通过 `PlacedUnit.FirstNightAtNewPosition` 传入 `PlayerUnitCommon.NewPositionPenalty`（00 / 02 / 03 共用），`UnitCarryIn` 不重复携带该字段 |
| A-2-15 | 已应用 | §3.7.2、§8.3 R-04-1：白天 `RelocateUnit` 位置合法性统一调用 `DeploymentRules.CheckPosition(level, unitDefId, pos, rosterId)`（00 §0.5.1 / 04 §3.5.1） |
| A-2-18 | 已应用 | §2.4.1、§3.7.2、§3.7.4、§3.13.2、§5 #23、§7 `T-05-19`/`T-05-22`/`T-05-36`、§8.3 R-04-1：`KnownTargetCarry(Pos, RosterId, StructureId, AddedNight)` 与 00 §2.6 / 04 §3.2.7 对齐；复用 `KnownTargetCarryOps.IsScouted / OnUnitRemoved`（00 §0.5.1）；删除 `OnUnitRelocated`（白天转移不迁移敌方对旧阵地的侦察快照，04 §3.2 K2）与 `AddStructureTarget`（改为 `Facility.Targeted` 在夜前 `BuildCarryIn` 合并入 `CarryIn.KnownTargets`） |
| A-2-20 | 已应用 | §2.4.2、§3.3.4、§3.7.4、§3.12.2、§8.3 R-03-1：`CarryOut` 完整对齐 03 §3.8.6（`ScoringState.DestroyedUnitSnapshots`、`PlayStats`、`KillsByEnemy`、`CustomMetrics`、`StoryChoiceResults`、`UrbanNavJamTriggered`） |
| A-2-22, B-T2-89 | 已应用 | §2.4.1、§2.4.2、§8.3 R-03-2、§8.4 B13：`CarryIn.ActiveSupports` 传入 `adjacent_sector_coverage` 由 03 生成场外虚拟防空单位；`CarryOut.Units` 排除 `!IsVirtualSectorCoverage` |
| A-2-30 | 已应用 | §3.2.4、§3.3.3、§8.3 R-03-2：发射架数统一调用 `WeaponParams.LauncherCount(def, rules.Engagement, level.Meta, u.UnitDefId)`（00 §0.5.1 / 03 §1.1），删除私有重复公式 |
| A-3-04 | 已应用 | §1.3、§1.7、§3.12.3、§7 `T-05-35`、§8.3 R-01-1：敌人适应 `uav_fly_higher` 的效果 kind 统一为 `"uav_altitude_add"`（C# `UavAltitudeAdd`）、数值字段统一为 `valueM`（C# `ValueM`），与 `01_spawn_movement_terrain.md` 对齐 |
| A-5-01 | 已应用 | §0.4、§3.1.2、§3.7.4、§3.11、§3.13.2、§6.1 #12、§7 `T-05-23`/`T-05-27`/`T-05-36`：战役层所有 `SimRandom.ChildSeed` 子流名强制以 `"campaign:"` 开头（`"campaign:cards:{LevelId}"`、`"campaign:crew:{LevelId}:{index + 1}"`、`"campaign:production:{LevelId}:{day}"`），严禁以 `"night:"` 开头 |
| B-T1-14, B-T1-15 | 已应用 | §2.4.1、§8.2 Q-L4：`forward_ambush` 与 `fire_team_network` 条令效果在 02 §3.3.3 / §3.9.2 实现并由 `CarryIn.Doctrines` 传入 |
| B-T2-07 | 已应用 | §3.1.2、§3.9.3、§8.2 Q-F5：夜晚种子 `NightSeed(RunSeed, LevelId, index + 1)` 用 `flow.nights[]` 1-based 下标；重试关卡与自动结算手打覆盖不换种子 |
| B-T2-10 | 已应用 | §1.2、§1.6、§3.5.2、§7.0、§7 `T-05-11`：`cityResource.shop` 的 `buy_drone_team` 增加 `availableFromLevel: 14`（GDD 12.3 第 14 关引入），`until` 改为 `"2025-10"`（第 15 关 2025-10 转自产） |
| B-T2-17 | 已应用 | §3.2.1、§3.7.1：开局用 `LoadLevel(..., nightIndex: null)`，每夜 `ConfirmDeployment` / `AutoResolveNight` 用 `LoadLevel(..., nightIndex: n.WavesNight)` 按夜解析时期数值 |
| B-T2-36 | 已应用 | §1.2、§1.6、§2.4.2、§3.7.4、§5 #49、§7 `T-05-10`、§8.4 B8：城区导航干扰惩罚并入城市资源（`cityResource.urbanNavJamPenalty = 1.0`）；当夜 `CarryOut.UrbanNavJamTriggered == true` 时结算写回扣减 `CityResource = Max(0, CityResource - 1.0)` |
| B-T2-81 | 已应用 | §1.3、§1.7、§3.2.4、§3.3.7、§5 #50、§7 `T-05-15`、§8.4 B7：新增 `campaign.json` `alert.dayRecovery = 0.2`；白天推进 `g` 天时 `AlertResponsiveness = Min(1.0, AlertResponsiveness + 0.2 * g)`，新关卡开局重置为 `1.0` |
| B-T2-103..126 | 已应用 | §1–§5、§8.1–8.2 Q-E1..Q-S1：全部 32 项设计/数值待决问题定稿并标为“已决”（含信任度可花费+配额修正双重属性、按武器聚合浪费判定、苏制库存保底不减、城市商店 `buy_searchlight` `night_aid`、D 结构 `Interlude` 缺省、E 结构 `W_E_NO_SUPPLY_WINDOWS` 校验警告、自动结算 `Defeated` 计挫折不失败、跨关节点与生产/研发/三方配电规则等） |
| B-T3-01 | 已应用 | §1.2、§3.4.2、§7 `T-05-01`/`T-05-02`、§8.1：配合 03 §3.10.2 混合潜在损失公式，将 `wastefulWeapon.maxRatio` 从 `0.1` 调整为 `0.2`（使 PAC‑3 打 Shahed 比值 `0.4 / 4.0 = 0.1 < 0.2` 仍触发浪费扣分与质询），补充典型武器×目标交换比断言并重算 `T-05-02` |
| B-T3-04 | 已应用 | §1.3、§1.7、§3.16、§7 `T-05-03`/`T-05-04`/`T-05-44`、§8.1–8.2：保持 `trust.min = 10`（同时在 `T-05-03`/`T-05-04`/`T-05-07` 给出 `min = 0` 夹具对比值），新增 `always_request` / `never_request` 策略机器人与 `RequestStrategySpread ≤ 0.15` 平衡指标 |
| B-T3-05 | 已应用 | §2.4.1、§3.7.4：对齐 04 暴露度达 100 当夜改派与跨夜已知目标结构 |
| B-T3-07 | 已应用 | §1.3、§2.3、§3.2.2、§3.8.2、§3.16、§4.1、§5 #30、§7 `T-05-25`、§8.1–8.2：自动结算默认 `interceptProbMult = 1.0, exposureGainMult = 1.0`（若 `AutoResolveGap < 0.03` 则启用 `0.95`）；新增 `PreAutoNightSnapshot` 与 `Review` 阶段 `WatchAutoNight(true)` 消耗 1 次重打（`Attempt + 1`）恢复快照并转为亲自指挥 |
| C-T1-01, C-T1-09 | 已应用 | `tools/spec_calc/05/calc_05.py` 归档入库并 100% 验算通过；重算并更新 `T-05-01..46`（含 `"campaign:"` 子流种子、`B-T3-01`、`B-T3-04`、`B-T3-07`、`B-T2-10`、`B-T2-36`、`B-T2-81`、`C-T2-03` 全部向量） |
| C-T1-04 | 已应用 | §0.4、§3.0、§3.7.4、§6.2：补充跨平台确定性约束（禁用 `Math.Hypot`，阵地半径匹配改用平方距离 `dx*dx + dy*dy <= r*r`） |
| C-T1-12 | 已应用 | §0.2：添加文档同步免责声明（本规格已与 GDD / 数值表 / WBS 同步收口，进入实现前无需再次停下询问） |
| C-T1-16 | 已应用 | §3.8.2：明确单夜 `AutoResolveNight()` 性能预算（Apple Silicon Mac Release 下 `test_01` `≤ 1 s`、终局大波次 `≤ 5 s`） |
| C-T2-03 | 已应用 | §1.2、§1.6、§2.3、§3.4.2、§7 `T-05-02`/`T-05-03`、§8.1：新增 `trust.borderViolation`（每次 −5，每夜最多 −10），读取 03 `Losses.BorderViolations.Count` 计入 `TrustBreakdown.Border` |
| C-T2-04 | 已应用 | §1.4、§8.2 Q-L2：补充 `tools/validate` 对战役跨关引用与结构 E `W_E_NO_SUPPLY_WINDOWS` 的静态检查要求 |
| 数据文件与上位文档同步（`rules/economy.json`、`rules/campaign.json`、`campaign/*.json`、`GDD`、`塔防数值表`） | 留给后续（`data/`、`docs/游戏设计文档_GDD_v1.md`、`docs/塔防数值表_v1.md`，D2b-08 / D3 任务） | 05 规格正文与 §1 / §8 已完整定义所有规则字段、Schema 约束与默认值，实际 JSON 数据与上位文档在对应任务中修改 |

## 06_client_graybox.md

## 07_tools.md（新建）

## 上位文档（GDD / 数值表 / data / test_01）
