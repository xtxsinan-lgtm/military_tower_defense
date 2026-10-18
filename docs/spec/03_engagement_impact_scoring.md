# 03 交战、拦截、外部支援、伤害、电网、空袭警报与评分

> 本文件把 GDD / 数值表中"枪打得着吗、打不打、打中没有、落地炸了什么、断了谁的电、警报有什么用、这一夜算得怎样"写成可直接实现的规格。
> 术语、类型、子流名、事件 / 命令名、实体类型、`SimWorld` 流程以 [00_core.md](00_core.md) 为准；本文件新增的名字在第 8.2 节"需登记到 00_core"中列出。

---

## 0. 范围与依据

### 0.1 覆盖范围

| 主题 | 本文件章节 | `Step()` 位置（00 3.3） | 对应 WBS |
|---|---|---|---|
| 可交战判定、交战规则（ROE）、便宜优先火力分配、反应时间、弹仓 / 发射架 / 身管耗弹、换枪管冷却、交战约束区与越界计数 | 3.2、3.8 | 7 `EngagementSystem`、13 `ScoringSystem` | WS01-009、WS01-027（禁止区内不交战 + 邻国越界计数，C-T2-03） |
| 解析拦截点、追不上不发射、到点掷骰、目标机动失效、拦截概率修正链、身管射击判定 | 3.1、3.3 | 8 `InterceptorSystem` | WS01-010 |
| 外部支援：战斗机三种呼叫、额度、拒绝、风险区、空域协调；国家级导航欺骗的呼叫流程；邻近扇区覆盖 | 3.4 | 9 `ExternalSupportSystem` | WS01-022 |
| 落地：精度档落点偏移、伤害等级效果、溅射衰减、子弹头、对车辆加成、车载防护罩、反辐射导弹、碎片（所在 1 km 格） | 3.5 | 10 `ImpactSystem` | WS01-011、WS01-017 |
| 电网拓扑与断电传播 | 3.6 | 10 `ImpactSystem`（00 Q5 / B-T2-15） | WS01-018 |
| 空袭警报：第 6 关闸门、避难、生产 / 城市资源暂停记录、警报疲劳 | 3.7 | 阶段 0（命令）+ 13 `ScoringSystem`（00 Q5 / B-T2-15） | WS01-024 |
| 评分、指数潜在损失与交换比、突防原因、胜负条件、`NightResult` 与 `CarryOut` | 3.8 | 13 `ScoringSystem` + `CheckNightEnd` 调用的 `BuildResult` | WS01-023 |

不在本文件范围：敌方移动与 `ThreatKinematics.Predict`（01）；传感器、航迹质量、诱饵甄别、电子战效果、辐射策略、暴露度（02）；部署状态机、指挥点扣除、二选一、剧情事件（04）；信任度增减、配额补给、跨夜结算（05）；命令行校验与压测工具（[07_tools.md](07_tools.md)）。本文件只**读取**这些规格写出的字段或调用其公开查询，接口在 0.3 列出。

### 0.2 依据与全局同步声明

- GDD v1.3：5.2（指挥点操作）、6.2、8.1（航迹质量）、8.4（碎片）、8.5（电网）、8.6（空袭警报）、8.9（战斗机）、8.10（交战规则约束与边境越界）、9.3（交换比）、15.5（复盘与突防原因）、17（敏感内容）
- 数值表 v1.2：1.1、1.2（射程 / 射高 / 弹仓 / 可拦截目标）、1.3"航迹质量规则"与"火控指示"、1.6（外部支援）、2.1–2.3（HP、伤害、溅射、精度、敌方成本）、3.1、3.2、3.3（拦截概率与修正）、3.5（辐射策略反应时间）、3.6（碎片）、第 4 节（交换比）、5.1–5.3
- WBS：01.A、01.B、WS01-009、010、011、017、018、022、023、024、027
- data：`units/air_defense.json`、`support/fighters.json`、`support/support.json`、`enemies/munitions.json`、`enemies/platforms.json`、`rules/intercept.json`、`rules/accuracy.json`、`rules/damage.json`、`rules/debris.json`、`rules/support.json`、`rules/tracks.json`（只读 `qualities`、`cueing`）、`rules/economy.json`、`rules/engagement.json`、`rules/civil.json`、`levels/<id>/level.json`、`map/layers.json`、`map/structures.json`、`map/grid.json`
- 依赖规格：[00_core.md](00_core.md)、[01_spawn_movement_terrain.md](01_spawn_movement_terrain.md)、[02_sensing_tracks_ew_emission.md](02_sensing_tracks_ew_emission.md)。
- **文档同步免责声明（C-T1-12）**：本规格已根据 D2 审查结论（`DECISIONS.md`、`A_interfaces.md`、`B_decisions.md`、`C_coverage.md`）与 GDD v1.3、数值表 v1.2、WBS v1 同步收口，进入实现前无需因本文已裁决的差异再次停下询问；本文涉及的 JSON 数据与 Schema 新增字段汇总于 §8.2，由后续数据任务（D3）统一落盘。
- **浮点距离约定（C-T1-04）**：所有二维 / 三维欧氏距离计算统一使用 `Math.Sqrt(dx * dx + dy * dy)` 或 `Math.Sqrt(dx * dx + dy * dy + dz * dz)`，禁止调用或自写 `Math.Hypot`（与 `00_core.md` §0.4.4 / §6.2 一致）。

### 0.3 依赖接口（由 01 / 02 / 04 / 05 提供，本文件只读或只调用）

| 编号 | 提供者 | 接口 / 字段 | 类型与语义（已与 00 / 01 / 02 / 04 / 05 定稿对齐） |
|---|---|---|---|
| D1 | 01 | `ThreatKinematics.Predict(Threat th, double atSec)`、`PredictArrivalSec(Threat th)`、`MaxSpeed3DMps(Threat th)`（`Nightwatch.Sim.Movement`） | `Predict` 返回 `ThreatPose(Vec2 Pos, double AltM, Vec2 VelMps, double VertSpeedMps, double PathArcM, bool AtPathEnd)`；本文件通过适配器 `dt => { var p = ThreatKinematics.Predict(t, ctx.TimeSec + dt); return new PredictedState(p.Pos, p.AltM, Arrived: p.AtPathEnd && t.PathEnd == PathEndAction.Arrive); }` 供 `InterceptSolver.Solve` 调用（保留 `IThreatPredictor` 桩接口供单元测试替换，A-2-02）。`PredictArrivalSec(t)` 返回 `PathEnd == Arrive` 目标的预计到达时刻（否则 `null`，供 B-T3-02 让位判定）；`MaxSpeed3DMps(t)` 返回目标三维速度上界（供 C-T1-03 粗筛与 C-T1-05 下界加速）。 |
| D2 | 01 | 事件 `ThreatArrived { ThreatId, DefId, Pos, TargetKind, TargetStructureId, TargetUnitId }` | **只由弹药（`Kind == Munition`）**在到达路径终点时由 `EnemyMovementSystem`（系统 2）发出（平台永不产生 `ThreatArrived`，A-2-03）；**01 不删除该目标**，将其置为 `Phase = Arrived`、`ArrivedAtSec = tEnd`；由本文件的 `ImpactSystem`（系统 10）在同一步结算并删除（若同一步系统 8 在飞拦截弹在 `InterceptAtSec <= t.ArrivedAtSec + Eps` 命中并删除该目标，系统 10 自动跳过，A-4-02）。 |
| D3 | 01 | `Threat.TargetStructureId`（`int`，0 = 不以保护目标为目标） | 用于评分中的"潜在损失"权重（B-T3-01） |
| D4 | 01 / 02 | `PlatformDef.Behavior == PlatformBehavior.Spotter`（兼容旧字段 `WhileAlive?.EnemyAccuracyTierBoost != null`） | Orlan 类侦察平台存活判定；升档数值只从 `Rules.Accuracy.SpotterTierBoost` 读取（B-T2-14） |
| D5 | 02 | `Track.Tag`（`TargetTag?`，A-2-01 / B-T1-23） | 融合航迹对外标签：未甄别的敌方诱饵为 `UAV`；已甄别的诱饵为 `DECOY`；`Vague` 航迹或无标签目标为 `null`。在候选筛选（3.2.3 C）中，若 `track.Tag == null && track.Quality == TrackQuality.Vague`，外观标签取 `pt = Rules.Intercept.DecoyUsesColumn`（`UAV`），使身管武器可对模糊航迹交战并触发 `TrackVague.GunProbMult = 0.5`（A-2-01）。 |
| D6 | 02 | `FireControlQueries.Cued(Track k, TrackRulesDef rules)`（`Nightwatch.Sim.Sensing`，A-2-08） | 等价于 `k.NetworkQuality != null && k.NetworkQuality >= rules.Cueing.Cued.MinTrackQuality`，表示该航迹有来自探测网络的"大致"或更高质量指示 |
| D7 | 02 | `Track.DecoyIdentified`（`bool`） | 诱饵甄别成功（`DecoyIdentified` 事件之后为 `true`） |
| D8 | 02 | `Track.PreciseHolderIds`（`List<int>`，A-2-08） | 当前对该航迹拥有"精确"锁定（火控雷达锁定或自主捕获）的 `FireUnit.Id` 升序列表；发射 `Missile` / `Rocket` 要求 `track.PreciseHolderIds.Contains(unit.Id)` |
| D9 | 02 | `FireControlQueries.HasFireControlRadar(FireUnit f)`（A-2-08） | `f.Def.FireControlRadar != null`，用于"摧毁雷达或发射车其一"（3.5.6） |
| D10 | 02 | `FireControlQueries.ReactionMult(FireUnit f, EmissionRulesDef rules)`（A-2-08） | 当前辐射策略的反应时间倍率（无 `Emitter` 时返回 `1.0`） |
| D11 | 02 | `EwQueries.IsInFriendlyEwZone(SimState s, GameCatalog c, Vec2 pos)` 与 `EwQueries.ShieldHitProbMult(SimState s, GameCatalog c, int targetUnitId, string threatDefId)`（`Nightwatch.Sim.Sensing`，A-2-08、B-T2-52） | 前者判断拦截点是否处于己方生效电子战干扰区内（3.3.2 `m5`）；后者返回车载防护罩对冲向该车无人机的命中概率倍率（3.5.6） |
| D12 | 02 | `Threat.AccuracyTierDrop`（`int`，≥ 0）、`Threat.EwExtraOffsetM`（`double`，≥ 0）、`Threat.EwEverCovered`（`bool`）、`Threat.EwDivertPos`（`Vec2?`）（A-2-07、B-T3-08） | 02 的 `ReconcileNavAccuracy` 已保证国家级导航欺骗降档（`AccuracyTierDrop`）与单位电子战附加偏移（`EwExtraOffsetM`）取期望偏移较大者、不叠加；`EwEverCovered` 表示本夜曾进入开启的导航电子战区（用于突防原因"电子战失效"與 `PlayStats.ThreatsEverEwCovered`） |
| D13 | 01 / 02 | `Threat.TargetUnitId`（`int`）、`Threat.ArmHitProbMult`（`double?`，默认 `null` 按 `1.0` 计，A-2-07） | 反辐射导弹追踪的我方辐射源单位 ID（由 01 / 04 写入）；雷达关机时机造成的命中倍率（由 02 在辐射源关机时按距离比写入） |
| D14 | 02 | `FireControlQueries.SilentHold(FireUnit f, double timeSec)`（A-2-08） | `f.Emitter != null && !f.Emitter.On && f.DeployState == Deployed && !f.RadarDestroyed && f.SuspendedUntilSec <= timeSec + 1e-9`，用于区分 `HoldReason.EmissionSilent` 与 `HoldReason.FireControlOff` |
| D15 | 04 | `CommandPointRules.CostOf(LevelData level, SimCommandType type)`、`CanSpend(ctx, int n)`、`Spend(ctx, int n, SimCommandType cause)`、`Refund(ctx, int n, SimCommandType cause)`（A-2-17） | 指挥点消耗查询、检查、扣除与退还（会发出 `CommandPointsChanged`） |
| D16 | 04 | `UnitDeployState`（00 2.3.2） | 部署状态（`Deployed`、`Moving`、`Packing` 等） |
| D17 | 05 | `CarryIn` 中本文件读取的字段（见 8.2 R-CI 及 00 2.5） | 跨夜带入的保护目标 HP、单位受损、班组、弹药池与逐架余弹、警报响应度、自动结算修正、外部支援等 |

---

## 1. 数据输入

> 换算规则见 00 0.4.2。下表"C# 名"即加载后的字段名（遵循 00 §1.2 与 A-3-02 的机械转换规则；常用简写属性见 1.13）。`?` 表示可空（JSON 可选或可为 null）。标注 **★** 的字段为 D2 裁决新增字段（详见 8.2）。

### 1.1 `units/air_defense.json` → `AirDefenseUnitDef` / `WeaponDef`

| JSON 字段 | 单位 | C# 名 | 类型 | 本文件用途 |
|---|---|---|---|---|
| `units[].id` | — | `Id` | `string` | 部署方案引用 |
| `mobility` | enum | `Mobility` | `Mobility` | 对车辆伤害加成（3.5.5） |
| `fireOnMove` | enum | `FireOnMove` | `FireOnMove { Yes = 0, Partial = 1, No = 2 }` | 行进间射击（3.2.2） |
| `systemPriceMusd` | M$ | `SystemPriceMusd` | `double?` | `NightResult` 损失统计 |
| `weapons[]` | — | `WeaponIds` | `IReadOnlyList<string>` | 数据顺序 = `FireUnit.Weapons` 顺序 |
| `weapons[].id` | — | `WeaponDef.Id` | `string` | 共享弹药池键 |
| `kind` | enum | `Kind` | `WeaponKind { Gun = 0, Missile = 1, Rocket = 2, InterceptorDrone = 3 }` | 航迹门槛、射击方式 |
| `interceptClass` | id | `InterceptClass` | `string` | 拦截概率矩阵的行与反应时间分档 |
| `rangeKm` | km | `RangeM` | `double` | 射程（水平） |
| `rangeByTagKm` | km | `RangeByTagM` | `IReadOnlyDictionary<TargetTag,double>?` | 对特定标签的射程，覆盖 `RangeM` |
| `ceilingKm` | km | `CeilingM` | `double` | 射高（AGL） |
| `shotCostMusd` | M$ | `ShotCostMusd` | `double?` | 交换比分母与便宜优先分配；`null` → 按 0 计并在 `AmmoSummary` 中标 `CostUnknown = true` |
| `magazine` | 发 / 架 | `Magazine` | `int?` | 每架弹仓；`null` = 不计数 |
| `magazineRounds` | 发 | `MagazineRounds` | `int?` | 身管武器备弹 |
| `launchers` | 架 | `Launchers` | `int?` | `null` → 查关卡 `launcherOverrides` 后回退 `engagement.defaultLaunchers`（B-T2-57） |
| `perLevelLimit` | 发 | `PerLevelLimit` | `int?` | 每关上限 |
| `targets` + `targetsFrom` | — | `Targets` | `IReadOnlyList<TargetTag>` | 已并入生效的 `targetsFrom`（00 1.4） |
| `lowEfficiencyTargets` | — | `LowEfficiencyTargets` | 同上 `?` | **不参与模拟**（已体现在矩阵中，`intercept._source.lowEfficiency`），只供界面 |
| `restrictToEnemies` | id[] | `RestrictToEnemies` | `IReadOnlyList<string>?` | 只打这些敌方 ID |
| `barrelCooldown` | — | `BarrelCooldown` | `bool?` | `null` = false |
| ★ `reactionGameSec` | 游戏秒 | `ReactionSec` | `double?` | 缺省 → 查 `engagement.reactionGameSecByClass[interceptClass]` 后回退 `engagement.byWeaponKind.<kind>.reactionGameSec`（B-T2-01、P15） |
| ★ `shotIntervalGameSec` | 游戏秒 | `ShotIntervalSec` | `double?` | 缺省 → 同上 `shotIntervalGameSec`（B-T2-01） |
| ★ `interceptorSpeedKmh` | km/h | `InterceptorSpeedMps` | `double?` | 缺省 → 同上 `interceptorSpeedKmh`；`Gun` 不允许填写（填则报 `E_RANGE`，P15、B-T2-55） |

`ammoSupply`、`deployTier`、`deployGameSec`、`packGameSec`、`moveSpeedKmh`、`stockOnly` 本文件不读（05 / 04）。

**取值函数**（全目录只此一处实现，放在 `Nightwatch.Sim.Rules.WeaponParams`，供 02 / 03 / 04 / 05 共用，A-2-30、A-3-09、B-T2-01、B-T2-57）：

```csharp
namespace Nightwatch.Sim.Rules;
public static class WeaponParams
{
    public static double ReactionSec(WeaponDef w, EngagementRulesDef r)
        => w.ReactionSec
           ?? (r.ReactionSecByClass != null && r.ReactionSecByClass.TryGetValue(w.InterceptClass, out var rc) ? rc : r.ByWeaponKind[w.Kind].ReactionSec);

    public static double ShotIntervalSec(WeaponDef w, EngagementRulesDef r)
        => w.ShotIntervalSec ?? r.ByWeaponKind[w.Kind].ShotIntervalSec;

    public static double InterceptorSpeedMps(WeaponDef w, EngagementRulesDef r)
        => w.InterceptorSpeedMps ?? r.ByWeaponKind[w.Kind].InterceptorSpeedMps!.Value; // Gun 调用 → InvalidOperationException

    public static double RangeFor(WeaponDef w, TargetTag tag)
        => w.RangeByTagM != null && w.RangeByTagM.TryGetValue(tag, out var r) ? r : w.RangeM;

    public static int LauncherCount(WeaponDef w, EngagementRulesDef r, LevelMetaDef? meta = null, string? unitDefId = null)
    {
        if (meta?.LauncherOverrides != null && unitDefId != null)
            foreach (var ov in meta.LauncherOverrides)
                if (ov.Unit == unitDefId && ov.Weapon == w.Id) return ov.Launchers;
        return w.Launchers ?? r.DefaultLaunchers;
    }
}
```

### 1.2 `support/fighters.json` → `FighterDef`

| JSON | C# | 类型 | 用途 |
|---|---|---|---|
| `id` | `Id` | `string` | |
| `ceilingKm` | `CeilingM` | `double` | 战斗机交战射高 |
| `takeoffGameSec` / `rearmGameSec` | `TakeoffSec` / `RearmSec` | `double` | 本文件**不使用**（延迟以 `support.delay` 为准，见 8.1 Q-S4 / B-T2-86） |
| `patrolSpeedKmh` | `PatrolSpeedMps` | `double` | 不使用（战斗机到位后定点巡逻，3.4.4） |
| `priceMusd` | `PriceMusd` | `double` | 不使用 |
| `weapons[].id` | `FighterWeaponDef.Id` | `string` | `support.fighterWeaponRef` 引用 |
| ★ `weapons[].kind`（必填） | `Kind` | `WeaponKind`（只允许 `Missile` / `Rocket`） | 取 `byWeaponKind` 默认值（P16） |
| `weapons[].interceptClass` | `InterceptClass` | `string` | |
| `weapons[].rangeKm` | `RangeM` | `double` | |
| `weapons[].shotCostMusd` | `ShotCostMusd` | `double` | |
| `weapons[].loadout` | `Loadout` | `int` | 每架次携弹 |
| `weapons[].targets` | `Targets` | `IReadOnlyList<TargetTag>` | |

### 1.3 `support/support.json` → `SupportDef`

| JSON | C# | 类型 | 用途 |
|---|---|---|---|
| `id`、`provider` | `Id`、`Provider` | `string`、`SupportProvider { AirForce, HigherEw, NeighborOblast, RegionalAdCommand }` | |
| `effect` | `Effect` | `SupportEffect { AreaPatrol = 0, DirectedIntercept = 1, UavHunt = 2, AccuracyDrop = 3, Reinforcement = 4, SectorCoverage = 5 }` | |
| `fighterRef` / `fighterWeaponRef` | `FighterId` / `FighterWeaponId` | `string?` | 加载器校验存在（`E_UNKNOWN_REF`，类别名 `战斗机` / `武器`） |
| `targets` | `Targets` | `IReadOnlyList<TargetTag>?` | 与武器 `Targets` 取交集；`null` = 用武器全部 |
| `killsPerSortie` | `KillsPerSortie` | `int?` | `UavHunt` 架次击落上限 |
| ★ `radiusKm` | `RadiusM` | `double?` | 作用半径（`national_gnss_spoof` 填 `30` km = `30000` m；`null` 时回退 `AffectsSameAsEwUnitId` 的半径，B-T2-04、A-2-21） |
| `accuracyTierDrop` / `affectsSameAsEwUnit` | `AccuracyTierDrop` / `AffectsSameAsEwUnitId` | `int?` / `string?` | 交给 02（3.4.5） |
| `delay.kind` | `Delay.Kind` | `DelayKind { GameSec = 0, NextDay = 1, Instant = 2 }` | |
| `delay.offMapGameSec` / `onMapAirbaseGameSec` / `gameSec` | `OffMapSec` / `OnMapAirbaseSec` / `Sec` | `double?` | 延迟 |
| `duration.kind` | `Duration.Kind` | `DurationKind { GameSec = 0, UntilAmmoOut = 1, Nights = 2, SameAsEwUnit = 3 }` | |
| `duration.gameSec` / `nights` | `Sec` / `Nights` | `double?` / `int?` | |
| `cost.commandPoints` / `trust` | `CommandPoints` / `Trust` | `int?` / `TrustCost?` | 指挥点由 04 扣；信任度 05 |
| `firstAvailable.level` | `FirstAvailableLevel` | `int?` | 关卡编号闸门（3.4.2） |

### 1.4 `enemies/munitions.json` → `MunitionDef`（本文件读取的部分）

| JSON | C# | 用途 |
|---|---|---|
| `tag` | `Tag`（`TargetTag?`） | 拦截概率列 |
| `interceptable` | `Interceptable` | `false` 的弹药不进入任何交战（即使存在航迹） |
| `hp` | `Hp`（`int?`） | **本文件不用于拦截判定**（命中即击毁，见 3.3.4 与 B-T3-03）；保留字段供将来扩展 |
| `interceptProbMult` | `InterceptProbMult`（`double?`，缺省 1.0） | 修正链第 8 项 |
| `damageLevel` | `DamageLevel`（`int`） | 伤害等级与潜在损失指数项（B-T3-01） |
| `vehicleDamageMult` | `VehicleDamageMult`（`double?`，缺省 1.0） | 对车辆加成 |
| `splashCells` | `SplashM` | 溅射半径 |
| `submunitions{count, damageLevel, splashCells}` | `Submunitions{Count, DamageLevel, SplashM}` | 子弹头 |
| `accuracy` / `accuracyByPeriod` | `Accuracy`（已解析） | 落点偏移 |
| `ewImmune` | `EwImmune`（`bool?`） | 忽略 D12 |
| `tracksEmittingRadarOnly` | `TracksEmittingRadarOnly`（`bool?`） | 反辐射导弹落地判定（3.5.7） |
| `costMusd` | `CostMusd`（`double?`） | 交换比潜在损失下界 `max(costMusd, 伤害价值)`（3.8.2、B-T3-01） |

`PlatformDef` 读取：`Tag`、`Hp`、`Behavior`（及兼容字段 `WhileAlive?.EnemyAccuracyTierBoost`，D4 / B-T2-14）。

### 1.5 `rules/intercept.json` → `InterceptRulesDef`

| JSON 路径 | C# 路径（A-3-02 机械转换） | 便捷只读属性（1.13） | 说明 |
|---|---|---|---|
| `decoyUsesColumn` | `DecoyUsesColumn`（`TargetTag`） | — | 真实标签为 `DECOY` 或模糊无标签航迹时查的列（A-2-01） |
| `classes.<class>.<tag>` | `InterceptClassDef { string Id; IReadOnlyDictionary<TargetTag,double> ProbByTag }`，`Classes` 按 `Id` 序数排序 | — | 已按关卡日期解析成 `double`（00 1.4 形态 A）；缺列 = 该类不能打该标签 |
| `modifiers.trackVague` | `Modifiers.TrackVague { bool MissilesAllowed; double GunProbMult; bool Active }` | `TrackVague` | |
| `modifiers.trackApproximateCued.probMult` | `Modifiers.TrackApproximateCued.ProbMult` | `TrackApproximateCuedProbMult` | |
| `modifiers.noCueSelfSearch.firstShotReactionTimeMult` | `Modifiers.NoCueSelfSearch.FirstShotReactionTimeMult` | `NoCueFirstShotReactionMult` | 加载器校验与 `tracks.cueing.uncued.firstShotReactionTimeMult` 相等（不等报 `E_RANGE`，A-2-08） |
| `modifiers.newPositionFirstNight.probMult` | `Modifiers.NewPositionFirstNight.ProbMult` | `NewPositionFirstNightProbMult` | |
| `modifiers.crewFatigue{minConsecutiveNights, probMult}` | `Modifiers.CrewFatigue{MinConsecutiveNights, ProbMult}` | `CrewFatigue` | |
| `modifiers.aceCrew.probMult` | `Modifiers.AceCrew.ProbMult` | `AceCrewProbMult` | |
| `modifiers.restrictedEngagement.reactionTimeMult` | `Modifiers.RestrictedEngagement.ReactionTimeMult` | `RestrictedEngagementReactionMult` | 限制交战反应时间倍率的唯一权威来源（B-T1-11） |
| `modifiers.interceptorDroneInFriendlyEw.probMult` | `Modifiers.InterceptorDroneInFriendlyEw.ProbMult` | `DroneInFriendlyEwProbMult` | 友军干扰倍率的唯一权威来源（B-T1-08） |
| `modifiers.evasiveTargetVsInterceptorDrone{probMult, from, enemies}` | `Modifiers.EvasiveTargetVsInterceptorDrone{ProbMult, Active, Enemies}` | `EvasiveVsDrone` | `Active` 按 `from` 解析（00 1.4 形态 C） |

每个修正项都有 `Active`（无 `from` 的恒为 `true`）。`Active == false` 时该项乘数视为 `1.0`。

### 1.6 `rules/tracks.json`（只读两项）

- `qualities[].missilesAllowed`（按 `id` 映射到 `TrackQuality`）→ `TrackRulesDef.MissilesAllowed(TrackQuality)`：`Missile` 与 `Rocket` 的航迹门槛。
- `qualities[].actions` 是否含 `vector_interceptor_drones` / `vector_fighters` → `TrackRulesDef.Allows(TrackQuality, TrackAction)`：拦截无人机与战斗机的航迹门槛。

### 1.7 `rules/accuracy.json` → `AccuracyRulesDef`

| JSON | C# | 说明 |
|---|---|---|
| `tierOrder` | `TierOrder`（`IReadOnlyList<AccuracyTier>`，从差到好） | 升 / 降档按此顺序的下标 ±1 |
| `tiers.<T>.offsetCells{min,max}` | `Tiers[T].OffsetM`（`MinMax`） | 落点偏移距离范围 |
| `tiers.<T>.ewExtraCells` | `Tiers[T].EwExtraM` | 02 计算 `Threat.EwExtraOffsetM` 使用（03 直接读 `t.EwExtraOffsetM`，A-2-07） |
| `spotterTierBoost` | `SpotterTierBoost`（`int`） | 侦察平台存活时的升档数（3.5.3、B-T2-14） |

### 1.8 `rules/damage.json` → `DamageRulesDef`

| JSON 路径 | C# 路径（A-3-02） | 便捷属性（1.13） | 说明 |
|---|---|---|---|
| `bands[]{minLevel,maxLevel}` | `Bands[i].MinLevel/MaxLevel` | — | 按等级查表 |
| `bands[].airDefense.effect` | `Bands[i].AirDefense.Effect`：`UnitDamageEffect { None = 0, LightDamage = 1, HeavyDamage = 2, DestroyComponent = 3, DestroyFireUnit = 4, DestroyFireUnitAndAdjacent = 5 }` | `UnitEffect` | |
| `bands[].airDefense.efficiencyMult` | `Bands[i].AirDefense.EfficiencyMult`（`double?`） | `EfficiencyMult` | 轻伤效能 |
| `bands[].airDefense.suspendGameSec` | `Bands[i].AirDefense.SuspendSec`（`double?`） | `SuspendSec` | 重伤暂停 |
| `bands[].civilBuildings.effect` | `Bands[i].CivilBuildings.Effect`：`CivilDamageEffect { Minor = 0, Buildings = 1, Block = 2 }` | `CivilEffect` | |
| `bands[].civilBuildings.destroyed{min,max}` | `Bands[i].CivilBuildings.Destroyed`（`MinMax?`，整数） | `CivilDestroyed` | 掷骰 HP 损失 |
| `bands[].gridDamagePct` | `Bands[i].GridDamageFrac`（00 Q6 / P10 / A-3-03：`÷ 100`） | — | 电网设施 HP 损失比例 |
| `splashFalloff{center, edge}` | `SplashFalloff.{Center, Edge}` | `SplashCenterMult`、`SplashEdgeMult` | 线性衰减 |
| ★ `unitFootprintCells` | `UnitFootprintM` | — | 我方单位的受击半径（默认 `0.05` 格 = `50` m，B-T2-76） |
| ★ `componentRadarChance` | `ComponentRadarChance` | — | "摧毁雷达或发射车其一"时毁雷达的概率（默认 `0.5`，B-T2-71） |

等级 0（`damageLevel: 0` 或衰减后取整为 0）不在任何 band 中 → 无效果。等级 > 10 截断为 10。

### 1.9 `rules/debris.json` → `DebrisRulesDef`

| JSON 路径 | C# 路径（A-3-02） | 便捷属性（1.13） | 说明 |
|---|---|---|---|
| `urbanInterceptDamageFraction` | `UrbanInterceptDamageFraction` | `UrbanFrac` | 城区拦截碎片伤害系数（默认 `0.3`） |
| `urbanInterceptRadiusCells` | `UrbanInterceptRadiusM` | `UrbanRadiusM` | `0` = 按"拦截点所在 1 km 格"判定受影响目标（3.5.2 A，C-T2-05）；`> 0` = 按半径衰减 |
| `ruralInterceptDamageFraction` | `RuralInterceptDamageFraction` | `RuralFrac` | 城外拦截碎片伤害系数（默认 `0.0`） |
| `divertedImpactFullDamageInUrban` | `DivertedImpactFullDamageInUrban` | `DivertedFullDamageInUrban` | 本文件对被诱偏的弹药**不做任何减伤**；值为 `false` 时 `SimWorld.Create` 抛 `SimSetupException("debris.divertedImpactFullDamageInUrban=false 未定义")` |
| `scoreUrbanInterceptRatio` | `ScoreUrbanInterceptRatio` | — | `false` 时 `DebrisSummary.UrbanInterceptRatio` 恒为 `null` |

### 1.10 `rules/support.json` → `SupportRulesDef`

| JSON 路径 | C# 路径（A-3-02） | 便捷属性（1.13） | 说明 |
|---|---|---|---|
| `fighterSortiesPerNight{min,max}` | `FighterSortiesPerNight`（`MinMax`） | — | `level.fighterSortiesPerNight` 缺省时取 `Min`；超出范围不报错（关卡可配置，见 `_source`） |
| `bigRaidRefusalChance` | `BigRaidRefusalChance` | — | |
| `frontlineRiskZoneBlocksCalls` | `FrontlineRiskZoneBlocksCalls` | — | |
| `airspace.restrictedEngagement{isDefault, confirmedHostileOnly, reactionTimeMult?}` | `Airspace.RestrictedEngagement.{IsDefault, ConfirmedHostileOnly, ReactionTimeMult}` | `Airspace.Restricted` | `ReactionTimeMult` 可选保留；若非空则加载器校验与 `intercept.modifiers.restrictedEngagement.reactionTimeMult` 相等（不等报 `E_RANGE`）；运行时统一只读 `intercept` 中的值（B-T1-11） |
| `airspace.fighterExclusiveZone{isDefault, groundHoldFire}` | `Airspace.FighterExclusiveZone.{IsDefault, GroundHoldFire}` | `Airspace.Exclusive` | |

### 1.11 关卡数据

| 文件 → 字段 | C# | 用途 |
|---|---|---|
| `level.json` `number` | `Meta.Number` | 支援 `firstAvailable` 与警报 `availableFromLevel` 闸门；`null`（测试关卡）= 不设闸门 |
| `fighterMode`、`fighterSortiesPerNight` | `Meta.FighterMode`、`Meta.FighterSortiesPerNight` | 3.4 |
| `ammoQuota[]` | `Meta.AmmoQuota` | 开局弹药池（3.2.1） |
| ★ `launcherOverrides[]`（可选） | `Meta.LauncherOverrides`（`IReadOnlyList<LauncherOverrideDef>?`：`Unit`、`Weapon`、`Launchers`） | 覆盖 `launchers: null` 武器的每单位发射架数（B-T2-57） |
| ★ `sectorCoverageAnchors[]`（可选） | `Meta.SectorCoverageAnchors`（`IReadOnlyList<SectorCoverageAnchorDef>?`：`Pos`、`UnitDefId`） | 邻近扇区覆盖（`adjacent_sector_coverage`）的场外虚拟火力单元锚点（B-T2-89） |
| `victory[]` / `defeat[]` | `Meta.Victory` / `Meta.Defeat`（`grid_collapse` 支持可选 `double? Fraction`，缺省 `1.0`，B-T2-79） | 3.8.5 |
| ★ `waves.json` `nights[].bigRaid`（可选） | `NightDef.BigRaid`（`bool?`，缺省 `false`） | 战斗机拒绝概率（3.4.3，B-T2-88） |
| `map/layers.json` `urban[]` | `Layers.Urban` | 碎片、城区上空拦截 |
| `restrictedZones[]` | `Layers.RestrictedZones`（`rule` 支持 `no_engagement`、`restricted_engagement`、`frontline_risk`、★ `neighbor_country`，C-T2-03） | 3.0、3.2.4.2、3.8.1 |
| `map/structures.json` | `StructureDef(Id, NameKey, Type, Pos, RadiusM, Weight, Hp, GridNodeId)` | 3.5、3.6、3.8 |
| `map/grid.json` | `GridDef` | 3.6 |

### 1.12 新增规则文件 ★

本文件引入的两个全局规则文件位于 `00_core.md` §1.1.3 全局加载顺序的第 23、24 位（`23 rules/engagement.json`、`24 rules/civil.json`，P01 / P49）。数值已按 `DECISIONS.md` / `B_decisions.md` / `C_coverage.md` 裁决锁定。

`rules/engagement.json`（`kind: "engagement"`）→ `EngagementRulesDef`：

```json
{
  "kind": "engagement",
  "byWeaponKind": {
    "gun":               { "reactionGameSec": 0.05, "shotIntervalGameSec": 0.5,  "roundsPerBurst": 34 },
    "missile":           { "reactionGameSec": 0.2,  "shotIntervalGameSec": 0.25, "interceptorSpeedKmh": 3600 },
    "rocket":            { "reactionGameSec": 0.1,  "shotIntervalGameSec": 0.25, "interceptorSpeedKmh": 2400 },
    "interceptor_drone": { "reactionGameSec": 0.5,  "shotIntervalGameSec": 0.5,  "interceptorSpeedKmh": 300 }
  },
  "reactionGameSecByClass": {
    "gun": 0.05, "gun_radar": 0.05, "manpads": 0.05,
    "shorad": 0.1, "medium": 0.15,
    "s300": 0.2, "samp_t": 0.2, "pac2": 0.2, "pac3": 0.2, "s200": 0.2,
    "jet_interceptor_drone": 0.3, "interceptor_drone": 0.5
  },
  "barrelCooldown": { "burstsBeforeCooldown": 5, "cooldownGameSec": 1 },
  "defaultLaunchers": 1,
  "maxSalvoSize": 4,
  "allocation": "cheapest_expected",
  "defaultRule": { "salvoSize": 1, "shootLookShoot": true, "ammoReserve": 0, "priorityMode": "soonest_intercept", "engageIdentifiedDecoys": false },
  "defaultRuleByTag": {
    "pac2":   { "BM": { "salvoSize": 2, "shootLookShoot": false }, "HBM": { "salvoSize": 2, "shootLookShoot": false } },
    "pac3":   { "BM": { "salvoSize": 2, "shootLookShoot": false }, "HBM": { "salvoSize": 2, "shootLookShoot": false } },
    "samp_t": { "BM": { "salvoSize": 2, "shootLookShoot": false }, "HBM": { "salvoSize": 2, "shootLookShoot": false } },
    "s300":   { "BM": { "salvoSize": 2, "shootLookShoot": false }, "HBM": { "salvoSize": 2, "shootLookShoot": false } }
  },
  "fighterRule": { "salvoSize": 1, "shootLookShoot": true }
}
```

| JSON | C# | 单位换算 / 说明 |
|---|---|---|
| `byWeaponKind.<kind>.reactionGameSec` | `ByWeaponKind[kind].ReactionSec` | × 60 |
| `…shotIntervalGameSec` | `…ShotIntervalSec` | × 60 |
| `…interceptorSpeedKmh` | `…InterceptorSpeedMps`（`double?`；`gun` 不得填写） | ÷ 3.6（B-T2-55） |
| `…roundsPerBurst`（只 `gun`） | `…RoundsPerBurst`（`int?`） | —（B-T2-59） |
| ★ `reactionGameSecByClass`（可选） | `ReactionSecByClass`（`IReadOnlyDictionary<string, double>?`） | × 60；按武器 `interceptClass` 细分默认反应时间，未命中时回退 `ByWeaponKind[w.Kind].ReactionSec`（B-T2-01） |
| `barrelCooldown.burstsBeforeCooldown` / `cooldownGameSec` | `BarrelBurstsBeforeCooldown` / `BarrelCooldownSec` | — / × 60（B-T2-61） |
| `defaultLaunchers` | `DefaultLaunchers` | —（B-T2-57） |
| `maxSalvoSize` | `MaxSalvoSize` | — |
| ★ `allocation`（可选，缺省 `"cheapest_expected"`） | `Allocation`（`EngagementAllocationMode { CheapestExpected = 0, UnitIdOrder = 1 }`） | 多火力单元同目标分配策略（3.2.4、B-T3-02） |
| `defaultRule` | `DefaultRule`（`EngagementRule`，见 2.3） | — |
| ★ `defaultRuleByTag`（可选） | `DefaultRuleByTag`（`IReadOnlyDictionary<string, IReadOnlyDictionary<TargetTag, SalvoRuleOverrideDef>>?`） | 反导类对 `BM` / `HBM` 的默认齐射覆盖（3.2.4、C-T2-09） |
| `fighterRule{salvoSize, shootLookShoot}` | `FighterSalvoSize`、`FighterShootLookShoot` | — |

`ByWeaponKind` 是按 `WeaponKind` 下标的定长数组（4 项，缺一项 → `E_MISSING_FIELD`）。

`rules/civil.json`（`kind: "civil"`）→ `CivilRulesDef`：

```json
{
  "kind": "civil",
  "grid": {
    "unitConnectRadiusCells": 1,
    "unitCategoriesOnGrid": ["sensor", "ew"],
    "unpoweredShelterProtectionMult": 0.5
  },
  "alert": {
    "availableFromLevel": 6,
    "shelterGameSec": 2,
    "protectionFrac": 0.8,
    "populationStructureTypes": ["residential"],
    "freeRaisesPerNight": 2,
    "fatiguePerExtraRaise": 0.1,
    "minResponsiveness": 0.3
  },
  "scoring": {
    "lossMusdBase": 0.1,
    "platformPotentialLossMusd": 10,
    "highThreatDamageLevel": 7
  }
}
```

| JSON | C# | 换算 / 说明 |
|---|---|---|
| `grid.unitConnectRadiusCells` | `Grid.UnitConnectRadiusM` | × cellKm × 1000（B-T2-05） |
| `grid.unitCategoriesOnGrid` | `Grid.UnitCategoriesOnGrid`（`IReadOnlyList<PlayerUnitCategory>`；JSON 值 `fire`/`sensor`/`ew`/`deception`） | —（B-T2-05） |
| `grid.unpoweredShelterProtectionMult` | `Grid.UnpoweredShelterProtectionMult` | —（B-T2-82） |
| ★ `alert.availableFromLevel`（可选，缺省 `6`） | `Alert.AvailableFromLevel`（`int`） | 空袭警报命令的关卡编号闸门（3.7.1、C-T2-04） |
| `alert.shelterGameSec` | `Alert.ShelterSec` | × 60（B-T2-80） |
| `alert.protectionFrac` | `Alert.ProtectionFrac` | —（B-T2-80） |
| `alert.populationStructureTypes` | `Alert.PopulationStructureTypes`（`IReadOnlyList<StructureType>`） | — |
| `alert.freeRaisesPerNight` | `Alert.FreeRaisesPerNight` | —（B-T2-80） |
| `alert.fatiguePerExtraRaise` | `Alert.FatiguePerExtraRaise` | —（B-T2-80） |
| `alert.minResponsiveness` | `Alert.MinResponsiveness` | —（B-T2-80） |
| ★ `scoring.lossMusdBase`（兼容旧名 `lossMusdPerDamageLevel`，若仅给旧名则缺省取 `0.1`） | `Scoring.LossMusdBase`（`double`） | 指数潜在损失基数 `0.1` M$（3.8.2、B-T3-01） |
| `scoring.platformPotentialLossMusd` | `Scoring.PlatformPotentialLossMusd` | —（B-T3-01） |
| `scoring.highThreatDamageLevel` | `Scoring.HighThreatDamageLevel` | —（B-T2-90） |

### 1.13 本文件中的固定实现常数与派生便捷属性

| 常数 | 值 | 说明 |
|---|---|---|
| `InterceptSolver.SampleSec` | `= ctx.StepSec`（1） | 解析拦截的扫描步长 |
| `InterceptSolver.BisectionIterations` | `32` | 二分次数（区间 1 s → 分辨率 2.3e-10 s，1 km/s 下约 0.2 µm；C-T2-10） |
| `Eps` | `1e-9` | 时间 / 距离比较容差（与 `SimTime.TickEpsilon` 相同） |

**派生便捷只读属性（A-3-02）**：数据模型 `*Def` 类保留与 JSON 机械对应的嵌套路径（见 1.5、1.8、1.9、1.10），同时提供以下无参只读转发属性供算法伪代码与单测直接访问：
- `InterceptRulesDef`：`TrackVague => Modifiers.TrackVague`、`TrackApproximateCuedProbMult => Modifiers.TrackApproximateCued.ProbMult`、`NoCueFirstShotReactionMult => Modifiers.NoCueSelfSearch.FirstShotReactionTimeMult`、`NewPositionFirstNightProbMult => Modifiers.NewPositionFirstNight.ProbMult`、`CrewFatigue => Modifiers.CrewFatigue`、`AceCrewProbMult => Modifiers.AceCrew.ProbMult`、`RestrictedEngagementReactionMult => Modifiers.RestrictedEngagement.ReactionTimeMult`、`DroneInFriendlyEwProbMult => Modifiers.InterceptorDroneInFriendlyEw.ProbMult`、`EvasiveVsDrone => Modifiers.EvasiveTargetVsInterceptorDrone`。
- `DamageBandDef`：`UnitEffect => AirDefense.Effect`、`EfficiencyMult => AirDefense.EfficiencyMult`、`SuspendSec => AirDefense.SuspendSec`、`CivilEffect => CivilBuildings.Effect`、`CivilDestroyed => CivilBuildings.Destroyed`；`DamageRulesDef`：`SplashCenterMult => SplashFalloff.Center`、`SplashEdgeMult => SplashFalloff.Edge`。
- `DebrisRulesDef`：`UrbanFrac => UrbanInterceptDamageFraction`、`UrbanRadiusM => UrbanInterceptRadiusM`、`RuralFrac => RuralInterceptDamageFraction`、`DivertedFullDamageInUrban => DivertedImpactFullDamageInUrban`。
- `AirspaceRulesDef`：`Restricted => RestrictedEngagement`、`Exclusive => FighterExclusiveZone`。

---

## 2. 状态

> "写 / 读"列：系统序号（00 3.3）或规格号。表中行顺序 = `WriteHash` 顺序（00 3.7.2）。"快照"列标 ✔ 的字段进入对应 `…View`。

### 2.1 `PlayerUnitCommon` 字段（四类我方单位共用，已合入 00 2.3.2）

| 字段 | C# 类型 | 单位 | 初值 | 写 | 读 | 快照 |
|---|---|---|---|---|---|---|
| `NewPositionPenalty` | `bool` | — | `PlacedUnit.FirstNightAtNewPosition`（P24、A-2-13、B-T2-06） | — | 7、02 | ✔ |
| `DamageEfficiencyMult` | `double` | — | `CarryIn` 给定，否则 1.0 | 10 | 7、02 | ✔ |
| `SuspendedUntilSec` | `double` | 世界秒（时刻） | 0.0 | 10 | 7、02 | ✔ |
| `LightDamaged` | `bool` | — | `CarryIn`，否则 false | 10 | 05（维修） | ✔ |

`Suspended(now) ⇔ SuspendedUntilSec > now + Eps`。02 把被暂停的传感器 / 电子战 / 火控雷达视为强制关机（A-2-12）。

### 2.2 `FireUnit` 专有字段（03 部分，与 00 2.2.2 对齐）

| 字段 | C# 类型 | 初值 | 写 | 读 | 快照 |
|---|---|---|---|---|---|
| `Weapons` | `List<WeaponState>` | 按 `AirDefenseUnitDef.WeaponIds` 顺序建立（3.2.1） | 7、8、10 | 7、13 | ✔（每项的 `WeaponId`、总余弹、`TargetTrackId`） |
| `RadarDestroyed` | `bool` | false | 10 | 02（A-2-12 强制关机）、13 | ✔ |
| `LaunchersLost` | `int` | 0（每次 `DestroyComponent(Launcher)` 时 `+1`，A-2-20） | 10 | 13（导出 `UnitCarryOut`） | ✔ |
| `CrewConsecutiveNights` | `int` | `CarryIn`（含今晚在内的连续作战夜数，由 05 计算传入，03 不自增，A-2-19），否则 0 | — | 7 | |
| `AceCrew` | `bool` | `CarryIn`，否则 false | — | 7 | |
| `Engagement` | `UnitEngagementSettings` | `PlacedUnit.Settings.Engagement` ?? 默认（2.3） | 阶段 0（`SetEngagementRule`） | 7 | ✔ |
| `IsVirtualSectorCoverage`（不参与哈希，派生自创建来源） | `bool` | 邻近扇区覆盖生成的场外虚拟火力单元为 `true`（不累积暴露度、不受地面伤害，B-T2-89），其余为 `false` | — | 02、10 | |

> 兼容说明：`FireUnit.NewPositionFirstNight` 已统一合入基类 `PlayerUnitCommon.NewPositionPenalty`（A-2-13、B-T2-06）；`FireUnit` 上可保留同名转发属性 `bool NewPositionFirstNight { get => NewPositionPenalty; set => NewPositionPenalty = value; }` 供单测便捷设置，不重复写入哈希。

`WeaponState`（类，非实体；列表顺序 = 数据顺序）：

| 字段 | C# 类型 | 初值 | 说明 |
|---|---|---|---|
| `WeaponId` | `string` | | |
| `Launchers` | `List<LauncherState>` | 3.2.1 | `Gun` 恒为 1 项 |
| `TargetTrackId` | `int` | 0 | 当前锁定的航迹（0 = 无） |
| `ReadyAtSec` | `double` | 0.0 | 对 `TargetTrackId` 的反应完成时刻 |
| `NextShotAtSec` | `double` | 0.0 | 下一次可发射 / 射击的最早时刻（射击间隔） |
| `BurstsSinceCooldown` | `int` | 0 | 换枪管计数 |
| `CooldownUntilSec` | `double` | 0.0 | 换枪管冷却结束时刻 |
| `ShotsFired` | `int` | 0 | 本夜发射数（导弹按枚，身管按次） |
| `PerLevelUsedBefore` | `int` | `CarryIn`，否则 0 | 本关此前各夜已用（`perLevelLimit`） |
| `DecoyShots` | `int` | 0 | 本夜射向**真实**诱饵的发射数（突防原因"诱饵消耗"） |
| `DepletedAnnounced` | `bool` | false | 是否已发过 `AmmoDepleted` |

`LauncherState`：`int RoundsLeft`（`-1` = 不计数）。

派生量（不存储）：`TotalRounds(w) = -1`（任一发射架为 -1）否则 `Σ RoundsLeft`。

### 2.3 交战规则（`EngagementRule`，值类型记录，参与哈希）

```csharp
public enum TargetPriorityMode { SoonestIntercept = 0, Nearest = 1 }
public enum EngagementAllocationMode { CheapestExpected = 0, UnitIdOrder = 1 }

public sealed record EngagementRule
{
    public bool HoldFire { get; init; }                         // 停火
    public IReadOnlyList<TargetTag>? AllowedTags { get; init; } // 标签白名单；null = 武器 Targets 全部。"PAC-3 只打弹道" = [BM, HBM]
    public IReadOnlyList<TargetTag>? TagPriority { get; init; } // 优先顺序；未列出的排在后面；null = 不按标签排序
    public TargetPriorityMode PriorityMode { get; init; }       // 同一标签优先级内的排序键
    public int SalvoSize { get; init; }                         // 每次交战决策发射数（1 … MaxSalvoSize）
    public bool ShootLookShoot { get; init; }                   // 射击-观察-射击
    public int AmmoReserve { get; init; }                       // 弹药保留：总余弹 ≤ 此值时只对 ReserveForTags 开火
    public IReadOnlyList<TargetTag>? ReserveForTags { get; init; } // 可动用保留弹药的标签；null = 无
    public bool EngageIdentifiedDecoys { get; init; }           // 是否射击已甄别的诱饵
}
public sealed record SalvoRuleOverrideDef(int SalvoSize, bool ShootLookShoot);
public sealed record WeaponRuleOverride(string WeaponId, EngagementRule Rule);
public sealed record UnitEngagementSettings(EngagementRule Default, IReadOnlyList<WeaponRuleOverride>? PerWeapon);
```

- 有效规则：`RuleFor(unit, weaponId) = PerWeapon 中 WeaponId 相等的第一项 ?? Default`。
- 对特定目标标签 `pt` 的有效齐射参数（C-T2-09）：若该武器未在 `UnitSettings.Engagement` 中显式设置规则（即使用系统默认规则），且 `engagement.DefaultRuleByTag` 中存在 `(def.InterceptClass, pt)` 的条目 `ov`，则对该目标交战时 `SalvoSize = ov.SalvoSize`、`ShootLookShoot = ov.ShootLookShoot`；若玩家通过初始部署设置或夜间 `SetEngagementRule` 命令显式指定了规则，则以玩家规则为准。
- 未给设置时：`Default = engagement.defaultRule`（`HoldFire = false`、三个列表为 `null`），`PerWeapon = null`。
- 哈希写入顺序 = 上面属性声明顺序；列表按存储顺序写；`PerWeapon` 按存储顺序写。
- `UnitSettings`（00 2.5）包含属性 `UnitEngagementSettings? Engagement`。

### 2.4 `Threat` 追加字段（03 写，对应 00 2.3.1 #44–47）

| 字段 | C# 类型 | 初值 | 写 | 读 |
|---|---|---|---|---|
| `MaxTrackQuality` | `int` | -1（从未被航迹覆盖），否则 `(int)TrackQuality` 的本夜最大值 | 7 | 10 |
| `ShotsTaken` | `int` | 0 | 7、9 | 10 |
| `HeldMask` | `int` | 0（按 `HoldReason` 的位：`1 << (int)reason`） | 7 | 10 |
| `DecoyDrained` | `bool` | false | 7 | 10 |

### 2.5 `Interceptor` 实体（03 拥有；公共字段 `DefId` = 武器 ID，`Pos/AltM` 为显示位置）

| 字段 | C# 类型 | 单位 | 说明 | 快照 |
|---|---|---|---|---|
| `FireUnitId` | `int` | | 发射的火力单元；支援发射为 0 | ✔ |
| `SupportAssetId` | `int` | | 支援发射的 `SupportAsset`；地面发射为 0 | ✔ |
| `WeaponKind` | `WeaponKind` | | | ✔ |
| `LauncherIndex` | `int` | | 支援发射为 0 | |
| `TargetTrackId` | `int` | | 发射时的航迹 | ✔ |
| `TargetThreatId` | `int` | | 发射时航迹关联的真实目标 | |
| ★ `TargetPathVersion` | `int` | | 发射时 `t.PathVersion`（目标中途改航 / 悬停 / 返航时用于在系统 8 判定失锁自毁，A-2-09） | |
| `OriginPos` | `Vec2` | m | 发射点 | |
| `LaunchAtSec` | `double` | 世界秒 | | |
| `InterceptAtSec` | `double` | 世界秒 | 解析拦截时刻 | ✔ |
| `InterceptPos` | `Vec2` | m | | ✔ |
| `InterceptAltM` | `double` | m | | ✔ |
| `HitProbability` | `double` | 0–1 | 发射时计算的最终概率（3.3.2） | |
| `ShotCostMusd` | `double` | M$ | | |

### 2.6 `SupportAsset` 实体（03 拥有；`DefId` = 支援 ID）

| 字段 | C# 类型 | 单位 | 初值 / 说明 | 快照 |
|---|---|---|---|---|
| `Effect` | `SupportEffect` | | | ✔ |
| `State` | `SupportAssetState { EnRoute = 0, Active = 1 }` | | `EnRoute` | ✔ |
| `CenterPos` | `Vec2` | m | 呼叫点 | ✔ |
| `ArriveAtSec` | `double` | 世界秒 | | ✔ |
| `EndAtSec` | `double` | 世界秒 | 到位时计算；`-1` = 无时限（至弹药耗尽） | ✔ |
| `RadiusM` | `double` | m | 战斗机 = 武器 `RangeM`；导航欺骗 = 3.4.5（A-2-21 / B-T2-04） | ✔ |
| `Exclusive` | `bool` | | 战斗机专区；初值 `airspace.fighterExclusiveZone.isDefault` | ✔ |
| `RoundsLeft` | `int` | | 战斗机 = 武器 `Loadout`；其他 = 0 | ✔ |
| `KillsLeft` | `int` | | `UavHunt` = `KillsPerSortie`；其他 = -1（不限） | ✔ |
| `TargetTrackId` | `int` | | 0 | |
| `ReadyAtSec` | `double` | | 0.0 | |
| `NextShotAtSec` | `double` | | 0.0 | |
| `CommandPointsSpent` | `int` | | 结算用 | |

公共字段：`Pos` = 到位前为 `CenterPos`（不参与逻辑），`AltM` = 0。

### 2.7 静态实体字段

`Structure`（00 3.2 第 6 步创建；其余字段由 03 在 `ImpactSystem.Initialize` 中填写）：

| 字段 | C# 类型 | 初值 | 写 | 读 | 快照 |
|---|---|---|---|---|---|
| `Type` | `StructureType` | 数据 | — | 10、13 | ✔ |
| `RadiusM` | `double` | 数据 | — | 10 | ✔ |
| `Weight` | `double` | 数据 | — | 13 | ✔ |
| `MaxHp` | `int` | 数据 `hp` | — | 10、13 | ✔ |
| `Hp` | `int` | `CarryIn` 给定，否则 `MaxHp` | 10 | 10、13 | ✔ |
| `HpAtNightStart` | `int` | = 初始 `Hp` | — | 13 | |
| `LossHp` | `double` | `CarryIn` 给定，否则 `MaxHp − Hp` | 10 | 13 | |
| `GridNodeId` | `int` | 00 3.2 | — | 10 | |
| `Powered` | `bool` | 3.6 初次计算 | 10 | 13、05 | ✔ |
| `UnpoweredSec` | `double` | 0.0 | 13 | 13 | |
| `PausedSec` | `double` | 0.0 | 13 | 13 | |

`PausedSec` = 警报拉响**或**断电的累计时长（05 据此计算工厂停产）。

`LossHp` 是"计入加权损失的 HP"，≤ `MaxHp − Hp`（空袭警报的避难效果只减少它，不减少物理 HP，3.7.4）。

`GridNode`：

| 字段 | C# 类型 | 初值 | 写 | 读 | 快照 |
|---|---|---|---|---|---|
| `Type` | `GridNodeType` | 数据 | — | 10 | ✔ |
| `OffMapSupply` | `bool` | 数据 `?? false` | — | 10 | |
| `FacilityStructureId` | `int` | 该节点的电网设施保护目标（`Type ∈ {PowerPlant, Substation}` 且 `GridNodeId` 指向本节点，取 ID 最小者），无则 0 | — | 10 | |
| `Operational` | `bool` | 3.6 | 10 | 10 | ✔ |
| `Powered` | `bool` | 3.6 | 10 | 10、13 | ✔ |

### 2.8 单例组件

`EngagementState`（已登记到 00 2.4 与 3.7.2 单例哈希表第 10 项，P28）：

| 字段 | C# 类型 | 说明 |
|---|---|---|
| `AmmoPoolRemaining` | `SortedDictionary<string,int>`（序数比较） | `CarryIn.AmmoPool ?? Meta.AmmoQuota` 分配后剩余的关卡弹药（本夜不用于装填，供 05，A-2-14） |
| `HeldLogged` | `SortedSet<HeldKey>` | 已发过 `EngagementHeld` 的 `(FireUnitId, WeaponIndex, TrackId, Reason)`；`HeldKey` 为 `readonly record struct`，比较器按四个字段依次升序 |

`SupportState`（单例哈希表第 6 项）：

| 字段 | C# 类型 | 初值 | 说明 |
|---|---|---|---|
| `SortiesRemaining` | `int` | `Math.Max(0, (level.Meta.FighterSortiesPerNight ?? rules.Support.FighterSortiesPerNight.Min) + (config.CarryIn?.FighterSortiesDelta ?? 0))`（A-2-22） | |
| `PendingCalls` | `List<PendingCall>` | 空 | 本步阶段 0 接受、待系统 9 处理的呼叫；系统 9 处理后清空 |
| `CallsAccepted` / `CallsRefused` | `int` / `int` | 0 / 0 | |

`PendingCall`（`readonly record struct`）：`long CommandSeq, string SupportDefId, Vec2 TargetPos, int CommandPointsSpent, bool UsesSortie`。

`GridState`（单例哈希表第 7 项）：

| 字段 | C# 类型 | 初值 | 说明 |
|---|---|---|---|
| `Dirty` | `bool` | false | 本步有电网设施 HP 变化，需要重算 |
| `Collapsed` | `bool` | 3.6 | 电网崩溃（3.6.4） |
| `CollapsedAtSec` | `double` | -1 | 首次崩溃时刻 |

`CivilState`（单例哈希表第 8 项）：

| 字段 | C# 类型 | 初值 | 说明 |
|---|---|---|---|
| `AlertOn` | `bool` | false | |
| `AlertChangedAtSec` | `double` | 0.0 | 最近一次切换时刻 |
| `RaisesTonight` | `int` | 0 | 本夜拉响次数 |
| `Responsiveness` | `double` | `CarryIn.AlertResponsiveness ?? 1.0` | 民众响应度 0–1 |
| `ResponsivenessAtStart` | `double` | = 初值 | |
| `ShelteredFrac` | `double` | 0.0 | 当前避难比例 0–1 |
| `ShelterQuality` | `double` | 1.0 | 3.7.3 |
| `AlertActiveSec` | `double` | 0.0 | 本夜警报累计时长 |
| `ShelteredPeakFrac` | `double` | 0.0 | |

`ScoringState`（单例哈希表第 9 项，只由 13 写；全部从事件与实体状态累计，3.8.1，A-2-20、A-3-10、A-4-04、C-T2-03）：

| 字段 | C# 类型 | 说明 |
|---|---|---|
| `ThreatsSpawned` / `ThreatsIntercepted` / `ThreatsImpacted` / `ThreatsExited` / ★ `ThreatsEwDowned` | `int` | `ThreatsSpawned` 计 `ThreatSpawned` + `MunitionReleased`；`ThreatsEwDowned` 计 `EwLinkCut { Outcome == Crash }`（含悬停超时坠毁，A-4-04） |
| `InterceptsOverUrban` | `int` | |
| `Weapons` | `SortedDictionary<string, WeaponTally>`（序数） | 按武器 ID：`Shots`、`Hits`、`ShotCostMusd`、`PotentialLossMusd`、`DecoyShots`、`DecoyCostMusd`、`GunRoundsUsed` |
| `TotalShotCostMusd` / `TotalPotentialLossMusd` | `double` | |
| `Leaks` | `List<LeakRecord>` | 按事件顺序 |
| `UnitLosses` | `List<UnitLossRecord>` | 按事件顺序（含受损） |
| `DebrisEvents` / `DebrisHpLost` | `int` / `int` | |
| `ExposureStart` | `SortedDictionary<int,double>` | 我方单位 ID → 开局暴露度（`Initialize` 填写；峰值与终值直接从存活单位 `u.ExposurePeak` / `u.Exposure` 及已毁单位快照读取，不再冗余存储 `ExposureMax` / `ExposureLast`，A-3-10） |
| `HighThreatLeaksWithReserve` | `int` | 3.8.3 |
| `SupportKills` | `int` | 支援发射的命中数 |
| ★ `UnitHits` | `SortedDictionary<int,int>` | 我方 `FireUnit.Id` → 本夜命中次数（供 `UnitCarryOut.Hits` 导出，A-2-20） |
| ★ `DestroyedUnitSnapshots` | `List<UnitCarryOut>` | 被毁且 `RosterId != 0` 的我方单位在被删除前一刻的 `UnitCarryOut` 快照（含被毁前暴露度与余弹，A-2-20、A-3-10） |
| ★ `KillsByEnemy` | `SortedDictionary<string,int>`（序数） | 敌方定义 ID → 本夜被防空命中或电子战致坠的数量（供 `CarryOut.KillsByEnemy`，A-2-20） |
| ★ `ArmDetections` / `ArmShutdowns` / `ThreatsEverEwCovered` | `int` | 累计 `ArmThreatDetected`、`EmitterSwitched { On == false, Cause == ArmShutdown }`、终结时 `t.EwEverCovered == true` 的目标数（供 `CarryOut.PlayStats`，A-2-20） |
| ★ `BorderViolations` | `List<BorderViolationRecord>` | 邻国越界记录（按发生顺序，3.8.1、C-T2-03） |

`WeaponTally`、`LeakRecord`、`UnitLossRecord`、`BorderViolationRecord` 的字段见 3.8.6（与 `NightResult` 的对应记录相同）。

---

## 3. 每步算法

### 3.0 公共工具（全目录只此一处实现）

```csharp
namespace Nightwatch.Sim.Core;
public static partial class Geo
{
    // 点在多边形内（交叉数法，半开规则）。多边形不必闭合；边界上的点结果由下式决定，不另做特判。
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
}
```

- `InUrban(p)` = `Layers.Urban` 中任一多边形（任意密度）`PointInPolygon(p, Polygon)`。
- `ZoneRuleAt(p)`：遍历 `Layers.RestrictedZones`（数据顺序），收集包含 `p` 的区域规则集合；返回 `(bool NoEngagement, bool Restricted, bool FrontlineRisk)`。
- 若 01 也需要点在多边形判断，必须调用同一个 `Geo.PointInPolygon`（00 3.8：同一公式只写一处）。
- 本文件所有“时刻比较”使用 `Eps = 1e-9`：`a ≥ b` 写作 `a + Eps >= b`；`a > b` 写作 `a > b + Eps`。

### 3.1 解析拦截点（`InterceptSolver`，WS01-010）

```csharp
namespace Nightwatch.Sim.Engagement;
public readonly record struct InterceptSolution(double TimeSec, Vec2 Pos, double AltM);

public static class InterceptSolver
{
    // origin：发射点（高度按 0 AGL）；speedMps：拦截弹速度；rangeM：对该目标的射程（水平）；ceilingM：射高；
    // predict：dt → 目标预测状态（正式代码传入 dt => ThreatPredictor.Predict(ctx, threat, dt)，测试传入桩函数）
    public static InterceptSolution? Solve(Vec2 origin, double speedMps, double rangeM, double ceilingM,
                                           Func<double, PredictedState> predict, double sampleSec);
}
```

算法（逐行实现）：

```
Reach(t):                                             # 等速直线飞行 t 秒能否到达目标在 t 时刻的位置
    s = predict(t)
    dx = s.Pos.X − origin.X; dy = s.Pos.Y − origin.Y
    d = Math.Sqrt(dx*dx + dy*dy + s.AltM*s.AltM)      # 三维直线距离
    return speedMps * t + Eps >= d

Solve:
    tMax = Math.Sqrt(rangeM*rangeM + ceilingM*ceilingM) / speedMps   # 超过此时长的解必然在包络外
    K = SimTime.SecToTicksCeil(tMax, sampleSec); if K < 1: K = 1
    lo = 0.0
    for k = 1 .. K:
        t = k * sampleSec
        if predict(t).Arrived: return null            # 目标在可达之前已落地 / 到达
        if Reach(t): hi = t; goto Refine
        lo = t
    return null                                       # 追不上
Refine:
    repeat 48 times:
        mid = lo + (hi − lo) * 0.5
        if Reach(mid): hi = mid else lo = mid
    s = predict(hi)
    if s.Arrived: return null
    h = Math.Sqrt((s.Pos.X − origin.X)² + (s.Pos.Y − origin.Y)²)
    if h > rangeM + Eps or s.AltM > ceilingM + Eps or s.AltM < 0: return null   # 拦截点在射程 / 射高包络外：本步不发射
    return InterceptSolution(hi, s.Pos, s.AltM)
```

- 结果是“最早可达时刻” `t*`（拦截弹恰好在 `t*` 到达，不会提前飞到某处等待）。若 `t*` 的拦截点在包络外，本步返回 `null`；目标继续接近后，后续某一步的 `t*` 落入包络时才发射——即“在最大射程处发射”的自然结果。
- 在 `sampleSec` 网格上首次可达的区间内二分；可达窗口短于 `sampleSec` 而恰好落在两个采样点之间时会被漏掉，属已知近似（8.1 Q-I5）。
- 拦截弹不做逐帧碰撞（WBS 01.A），也不做中途修正：发射后拦截点固定（2.5）。
- 地形：拦截弹和目标高度都用 AGL，不考虑发射点与拦截点的地形高差（8.1 Q-I5）。
- 对 `Gun` 不调用本函数（3.2.4.2）。


### 3.2 `EngagementSystem`（Order 7，子流 `engagement`，WS01-009）

本系统**不消耗随机数**（所有选择都有确定的全序）；`engagement` 子流保留未用。

#### 3.2.1 `Initialize`（火力单元的武器状态、弹药池）

`SimWorld.Create` 第 7 步创建 `FireUnit` 后、第 8 步应用 `CarryIn` 之前，由 `FireUnitFactory.Init(unit, def, level)` 填写 2.2 的字段（00 3.2“其余字段由所属规格初始化”）。本系统 `Initialize` 只做弹药池分配：

```
pool = 对 Meta.AmmoQuota 中每项：pool[WeaponId] = Count          # 无 ammoQuota → pool 为空
for unit in FireUnits (ID 升序):
  for w in unit.Weapons (数据顺序):
    def = Weapon(w.WeaponId)
    n = (def.Kind == Gun) ? 1 : LauncherCount(def)
    for i in 0..n−1:
      if def.Kind == Gun:              cap = def.MagazineRounds ?? −1
      else:                            cap = def.Magazine ?? −1
      if cap ≥ 0 and pool 含 def.Id:   take = min(cap, pool[def.Id]); pool[def.Id] −= take; rounds = take
      else:                            rounds = cap
      w.Launchers.Add(new LauncherState { RoundsLeft = rounds })
EngagementState.AmmoPoolRemaining = pool（只保留 ammoQuota 中出现的武器）
```

- 共享弹药池按武器 ID（00 1.2 第 14 条）：同一武器出现在多个单位中时，按单位 ID、武器顺序、发射架顺序依次取弹。
- 夜间**不从弹药池装填**（8.1 Q-E3）。
- `CarryIn` 若给出某单位某武器的逐架余弹，则在第 8 步覆盖 `RoundsLeft`（05 定义字段），覆盖时不再从池中扣。

#### 3.2.2 单位能否开火

```
CanAct(unit, def):
    switch unit.DeployState:
        Deployed: return true
        Moving:   return unitDef.FireOnMove == Yes
                         or (unitDef.FireOnMove == Partial and def.Kind == Gun)
        其他（Packing / Packed / Deploying）: return false
```

`CanAct == false` 时本步跳过该武器：不开火、不标记任何保留原因、`TargetTrackId = 0`。

#### 3.2.3 候选航迹

每步开头（单位循环之前）：

```
now = ctx.TimeSec
# A. 航迹覆盖记录（突防原因用）
for track in Tracks (ID 升序):
    if Threats.TryGet(track.ThreatId, out t): t.MaxTrackQuality = max(t.MaxTrackQuality, (int)track.Quality)
# B. 已占用数（按真实目标计，避免同一目标多条航迹时重复射击）
claims = new Dictionary<int,int>()          # 只查找，不遍历
for ic in Interceptors (ID 升序): claims[ic.TargetThreatId] += 1
# C. 候选列表（按航迹 ID 升序）
candidates = []
for track in Tracks (ID 升序):
    if !Threats.TryGet(track.ThreatId, out t): continue
    if t.Tag == null: continue
    if t.Kind == Munition and MunitionDef(t).Interceptable == false: continue
    if track.PerceivedTag == null: continue
    candidates.Add((track, t))
```

#### 3.2.4 逐武器的交战决策

```
for unit in FireUnits (ID 升序):
  for wi, w in unit.Weapons (列表顺序):
    EngageWeapon(unit, wi, w)
```

`EngageWeapon`：

```
def  = Weapon(w.WeaponId); rule = RuleFor(unit, w.WeaponId)
if !CanAct(unit, def): w.TargetTrackId = 0; return

# —— 第 1 步：逐候选筛选 ——
eligible = []; reachable = []
for (track, t) in candidates:
    pt = track.PerceivedTag
    if pt ∉ def.Targets: continue                                     # 武器本身打不了，不算“有目标”
    if !ClassHasColumn(def.InterceptClass, Column(pt)): continue        # Column：DECOY → decoyUsesColumn
    if def.RestrictToEnemies != null and !(track.Quality == Precise and t.DefId ∈ def.RestrictToEnemies): continue
    R = RangeFor(def, pt)
    dNow = |t.Pos − unit.Pos|
    inReach = dNow <= R + Eps and t.AltM <= def.CeilingM + Eps        # 当前就在射程、射高内
    if def.Kind == Gun: coarse = inReach
    else:               coarse = dNow <= R + |t.VelMps| * TMax(def, R) + Eps   # TMax = √(R²+Ceiling²)/速度
    if !coarse: continue
    if inReach: reachable.Add((track, t))
    reason = FirstGateFailure(unit, w, def, rule, track, t, pt)        # 3.2.4.1
    if reason != null:
        if inReach: MarkHeld(unit, wi, track, t, reason)               # 3.2.7
        continue
    if Covered(rule, def, claims, t): continue                         # 已有足够拦截弹 / 射击指向该目标；不标记
    eligible.Add((track, t, pt, dNow, inReach))

# 单位 / 武器级状态（在筛选之后判断，使 reachable 可用于标记）
if unit.Suspended(now):                  mark Suspended on all reachable; w.TargetTrackId = 0; return
if def.BarrelCooldown == true and w.CooldownUntilSec > now + Eps:
                                         mark BarrelCooling on all reachable; return

# —— 第 2 步：排序 ——
for e in eligible: e.Key1 = TagPriorityIndex(rule, e.pt)               # rule.TagPriority == null → 0；否则 IndexOf，未列出 = Count
                   e.Key2 = (rule.PriorityMode == Nearest or def.Kind == Gun) ? e.dNow : SolveFor(unit, def, e).TimeSec（无解 = +∞）
order eligible by (Key1 asc, Key2 asc, track.Id asc)

# —— 第 3 步：选目标（粘滞：已锁定且仍合格的目标优先）——
chosen = null
if w.TargetTrackId != 0 and eligible 中存在 track.Id == w.TargetTrackId:
    把它移到 order 的最前面
for e in order:
    r = PostCheck(unit, wi, def, rule, e)                              # 3.2.4.2；失败时内部已 MarkHeld（若 inReach）
    if r.Ok: chosen = e; restricted = r.Restricted; sol = r.Solution; break
if chosen == null: w.TargetTrackId = 0; return
for e in reachable where e.track.Id != chosen.track.Id: MarkHeld(unit, wi, e.track, e.t, ChannelBusy)

# —— 第 4 步：反应时间 ——
if chosen.track.Id != w.TargetTrackId:
    w.TargetTrackId = chosen.track.Id
    w.ReadyAtSec = now + ReactionSecFor(unit, def, chosen.track, restricted)   # 3.2.5
if w.ReadyAtSec > now + Eps: return                                    # 反应中
if w.NextShotAtSec > now + Eps: return                                 # 射击间隔未到（选目标与反应计时不受影响，可与间隔重叠）

# —— 第 5 步：开火 ——
if def.Kind == Gun: FireGun(unit, w, def, chosen) else: FireInterceptors(unit, w, def, rule, chosen, sol)
```

##### 3.2.4.1 `FirstGateFailure`（按此顺序，返回第一个不满足的原因；全部满足返回 `null`）

| 序 | 条件（不满足即返回右列原因） | `HoldReason` |
|---|---|---|
| a | `!rule.HoldFire` | `HoldFire` |
| b | `!(track.DecoyIdentified && !rule.EngageIdentifiedDecoys)` | `IdentifiedDecoy` |
| c | `rule.AllowedTags == null \|\| rule.AllowedTags.Contains(pt)` | `TagNotAllowedByRule` |
| d | `QualityAllows(def.Kind, track.Quality)`：`Gun` → 任意质量；`InterceptorDrone` → `tracks.Allows(q, vector_interceptor_drones)`；`Missile` / `Rocket` → `tracks.MissilesAllowed(q)` | `TrackQualityTooLow` |
| e | `Missile`/`Rocket`：`unit.FireControlActive`。不满足时：`unit.EmissionSilentHold ? EmissionSilent : FireControlOff` | `EmissionSilent` / `FireControlOff` |
| f | `TotalRounds(w) != 0`（不满足时若 `w.DecoyShots > 0` 则置 `t.DecoyDrained = true`） | `AmmoDepleted` |
| g | `def.PerLevelLimit == null \|\| w.PerLevelUsedBefore + w.ShotsFired < def.PerLevelLimit` | `PerLevelLimitReached` |
| h | `rule.AmmoReserve == 0 \|\| TotalRounds(w) == −1 \|\| TotalRounds(w) > rule.AmmoReserve \|\| (rule.ReserveForTags != null && rule.ReserveForTags.Contains(pt))` | `AmmoReserve` |

`Covered(rule, def, claims, t)`：`c = claims.GetValueOrDefault(t.Id)`；`Gun` 或 `!rule.ShootLookShoot` → `c >= rule.SalvoSize`；否则（射击-观察-射击）→ `c > 0`。

##### 3.2.4.2 `PostCheck`（需要拦截点的检查）

```
if def.Kind == Gun:
    if !e.inReach: fail（不标记）
    point = e.t.Pos; sol = null
else:
    sol = SolveFor(unit, def, e)       # InterceptSolver.Solve(unit.Pos, InterceptorSpeedMps(def), RangeFor(def, pt), def.CeilingM, dt => Predict(t, dt), StepSec)
    if sol == null: if e.inReach: MarkHeld(CannotIntercept); fail
    point = sol.Pos
z = ZoneRuleAt(point)
if z.NoEngagement: MarkHeld(NoEngagementZone); fail
restricted = z.Restricted
for a in SupportAssets (ID 升序) where a.State == Active and IsFighter(a.Effect):
    if |point − a.Pos| <= a.RadiusM + Eps:
        if a.Exclusive and support.Airspace.Exclusive.GroundHoldFire: MarkHeld(FighterExclusiveZone); fail
        restricted = true
if restricted and support.Airspace.Restricted.ConfirmedHostileOnly and e.track.Quality != Precise:
    MarkHeld(NotConfirmedHostile); fail
ok(restricted, sol)
```

- `SolveFor` 的结果在同一步同一武器内缓存（第 2 步排序算过的直接复用），不得重复计算产生不同结果（纯函数，结果必然相同，缓存只为性能）。
- `IsFighter(effect)` = `effect ∈ {AreaPatrol, DirectedIntercept, UavHunt}`。
- “已确认的敌方目标”= 航迹质量 `Precise`（8.1 Q-E7）。地图上的“限制交战区”与“战斗机所在区域”使用同一套效果（`ConfirmedHostileOnly` + 反应时间倍率）。

#### 3.2.5 反应时间

```
ReactionSecFor(unit, def, track, restricted) =
      ReactionSec(def)                                         # 1.1 取值函数
    × unit.EmissionReactionMult                                # D10，辐射策略
    × (track.Cued ? 1.0 : intercept.NoCueFirstShotReactionMult) # 无外部指示，首发 +50%
    × (restricted ? intercept.RestrictedEngagementReactionMult : 1.0)
```

按上式从左到右相乘。“首发”解释为**对每个新锁定目标的第一次发射**（8.1 Q-E5）：同一目标的后续齐射只受射击间隔约束。反应期间若目标失去资格或被别的目标取代，计时作废，新目标重新计时。

#### 3.2.6 开火

**导弹 / 火箭 / 拦截无人机**（`FireInterceptors`）：

```
c = claims.GetValueOrDefault(t.Id)
n = rule.ShootLookShoot ? rule.SalvoSize : rule.SalvoSize − c
if TotalRounds(w) != −1: n = min(n, TotalRounds(w))
if def.PerLevelLimit != null: n = min(n, def.PerLevelLimit − w.PerLevelUsedBefore − w.ShotsFired)
p = HitProbability(unit, def, track, t, sol.Pos)               # 3.3.2；同一齐射共用
for k in 0 .. n−1:
    li = 第一个 RoundsLeft != 0 的发射架下标
    if w.Launchers[li].RoundsLeft > 0: w.Launchers[li].RoundsLeft −= 1
    ic = Interceptors.Add(new Interceptor {
        DefId = def.Id, Pos = unit.Pos, AltM = 0, FireUnitId = unit.Id, SupportAssetId = 0, WeaponKind = def.Kind,
        LauncherIndex = li, TargetTrackId = track.Id, TargetThreatId = t.Id, OriginPos = unit.Pos,
        LaunchAtSec = now, InterceptAtSec = now + sol.TimeSec, InterceptPos = sol.Pos, InterceptAltM = sol.AltM,
        HitProbability = p, ShotCostMusd = def.ShotCostMusd ?? 0 })
    emit InterceptorLaunched { FireUnitId = unit.Id, LauncherIndex = li, WeaponId = def.Id, InterceptorId = ic.Id,
                               TrackId = track.Id, ThreatId = t.Id, SupportAssetId = 0 }
    w.ShotsFired += 1; t.ShotsTaken += 1
    if t.Tag == DECOY: w.DecoyShots += 1
claims[t.Id] = c + n
w.NextShotAtSec = now + ShotIntervalSec(def)
AnnounceDepletion(unit, w)
```

**身管武器**（`FireGun`）：

```
L = w.Launchers[0]
per = engagement.ByWeaponKind[Gun].RoundsPerBurst
if L.RoundsLeft == −1: used = per
else:                  used = min(per, L.RoundsLeft); L.RoundsLeft −= used     # 不足一次的余弹也能打出最后一次
p = HitProbability(unit, def, track, t, t.Pos)
emit GunFired { FireUnitId = unit.Id, WeaponId = def.Id, TrackId = track.Id, ThreatId = t.Id, Probability = p, RoundsUsed = used }
w.ShotsFired += 1; t.ShotsTaken += 1; if t.Tag == DECOY: w.DecoyShots += 1
claims[t.Id] += 1
w.NextShotAtSec = now + ShotIntervalSec(def)
if def.BarrelCooldown == true:
    w.BurstsSinceCooldown += 1
    if w.BurstsSinceCooldown >= engagement.BarrelBurstsBeforeCooldown:
        w.CooldownUntilSec = now + engagement.BarrelCooldownSec; w.BurstsSinceCooldown = 0
AnnounceDepletion(unit, w)
```

`AnnounceDepletion`：`TotalRounds(w) == 0 && !w.DepletedAnnounced` → 发出 `AmmoDepleted { FireUnitId, WeaponId }`，`DepletedAnnounced = true`。

#### 3.2.7 `MarkHeld(unit, wi, track, t, reason)`

```
t.HeldMask |= 1 << (int)reason
if reason ∈ {ChannelBusy}: return                       # 太频繁，只记位、不发事件
key = HeldKey(unit.Id, wi, track.Id, reason)
if EngagementState.HeldLogged.Add(key):                # 首次
    emit EngagementHeld { FireUnitId = unit.Id, WeaponId = w.WeaponId, TrackId = track.Id, ThreatId = t.Id, Reason = reason }
```

同一 `(单位, 武器, 航迹, 原因)` 一夜只发一次事件。

### 3.3 `InterceptorSystem`（Order 8，子流 `intercept`，WS01-010）

#### 3.3.1 每步流程

```
now = ctx.TimeSec
due = []
for ic in Interceptors (ID 升序):
    if ic.InterceptAtSec <= now + Eps: due.Add(ic)
    else:                                                   # 显示位置（不参与逻辑）
        f = (now − ic.LaunchAtSec) / (ic.InterceptAtSec − ic.LaunchAtSec)
        ic.Pos  = ic.OriginPos + (ic.InterceptPos − ic.OriginPos) * f
        ic.AltM = ic.InterceptAltM * f
due 按 (InterceptAtSec 升序, Id 升序) 排序
for ic in due:
    if !Threats.TryGet(ic.TargetThreatId, out t):
        emit InterceptorExpired { InterceptorId = ic.Id, Cause = TargetGone }      # 不掷骰
        Interceptors.Remove(ic.Id); continue
    hit = Rng.NextDouble() < ic.HitProbability                                     # 恰好 1 次 NextDouble
    emit InterceptResolved { AtSec = min(ic.InterceptAtSec, now), InterceptorId = ic.Id, ThreatId = t.Id, Hit = hit,
                             Probability = ic.HitProbability, Pos = ic.InterceptPos, AltM = ic.InterceptAltM,
                             OverUrban = InUrban(ic.InterceptPos), WeaponId = ic.DefId,
                             FireUnitId = ic.FireUnitId, SupportAssetId = ic.SupportAssetId }
    if hit:
        Threats.Remove(t.Id)
        if ic.SupportAssetId != 0 and SupportAssets.TryGet(ic.SupportAssetId, out a) and a.KillsLeft > 0: a.KillsLeft −= 1
    Interceptors.Remove(ic.Id)
for e in ctx.Events.CurrentStep where e is GunFired (Seq 升序):
    if !Threats.TryGet(e.ThreatId, out t): continue                               # 本步已被拦截弹击落：不掷骰、不发事件
    hit = Rng.NextDouble() < e.Probability
    emit InterceptResolved { AtSec = null, InterceptorId = null, ThreatId = t.Id, Hit = hit, Probability = e.Probability,
                             Pos = t.Pos, AltM = t.AltM, OverUrban = InUrban(t.Pos), WeaponId = e.WeaponId,
                             FireUnitId = e.FireUnitId, SupportAssetId = 0 }
    if hit: Threats.Remove(t.Id)
```

- 拦截弹先于身管射击结算（拦截弹的拦截时刻 ≤ 本步时刻，身管射击视为发生在本步时刻）。
- 发射它的火力单元在拦截弹飞行中被毁：拦截弹照常结算（概率已在发射时确定，8.1 Q-I6）。

#### 3.3.2 拦截概率（`HitProbability`，修正链的乘法顺序固定）

```
col  = (t.Tag == DECOY) ? intercept.DecoyUsesColumn : t.Tag          # 真实标签（不是 PerceivedTag）
base = Class(def.InterceptClass).ProbByTag.TryGetValue(col, out v) ? v : 0.0
m1 = QualityMult(def.Kind, track)
       Vague       → (def.Kind == Gun && TrackVague.Active) ? TrackVague.GunProbMult : 1.0
       Approximate → (track.Cued && 该修正 Active) ? TrackApproximateCuedProbMult : 1.0
       Precise     → 1.0
m2 = unit.NewPositionFirstNight ? NewPositionFirstNightProbMult : 1.0
m3 = unit.CrewConsecutiveNights >= CrewFatigue.MinConsecutiveNights ? CrewFatigue.ProbMult : 1.0
m4 = unit.AceCrew ? AceCrewProbMult : 1.0
m5 = (def.Kind == InterceptorDrone && EwQueries.FriendlyJammingAt(ctx, point)) ? DroneInFriendlyEwProbMult : 1.0
m6 = (def.Kind == InterceptorDrone && EvasiveVsDrone.Active && t.DefId ∈ EvasiveVsDrone.EnemyIds) ? EvasiveVsDrone.ProbMult : 1.0
m7 = (t.Kind == Munition) ? (MunitionDef(t).InterceptProbMult ?? 1.0) : 1.0
m8 = unit.DamageEfficiencyMult
p  = base * m1 * m2 * m3 * m4 * m5 * m6 * m7 * m8                     # 严格从左到右
p  = Math.Clamp(p, 0.0, 1.0)
```

- 任何 `Active == false` 的修正项按 1.0。
- `point`：导弹类为拦截点 `sol.Pos`，身管为目标当前位置。
- 数值表“目标只有模糊航迹：不可用导弹交战”由 3.2.4.1 d 保证，因此 `m1` 中导弹不会遇到 `Vague`。
- 战斗机发射的拦截弹（3.4.4）只用 `base × m1 × m7`，其余项为 1.0（战斗机不是“单位”，没有阵地、班组、受损状态）。
- 断电不影响火力单元的拦截概率（火力单元自带电源，8.1 Q-G3）。

#### 3.3.3 “追不上则不发射”

由 3.1 的 `Solve` 返回 `null` 体现（3.2.4.2 标记 `CannotIntercept`）。追得上但拦截点在射程 / 射高之外同样返回 `null`。

#### 3.3.4 HP 模型

数值表 3.3 是“单发拦截概率”，因此**拦截判定命中 = 目标被摧毁**，与目标 HP 无关；HP 字段本文件不用于拦截（8.1 Q-I3 记录了备选方案）。

### 3.4 `ExternalSupportSystem`（Order 9，子流 `support`，WS01-022）

#### 3.4.1 命令 `CallSupport`（处理者：本系统）

`Validate`（按顺序，返回第一个失败）：

| 序 | 条件 | 拒绝原因 |
|---|---|---|
| 1 | `SupportDefId` 不存在 | `InvalidArgument` |
| 2 | `Effect ∈ {Reinforcement, SectorCoverage}`（`delay = next_day` 或代价为信任度，属于夜间之外的申请，由 05 处理） | `NotAvailable` |
| 3 | `Meta.Number != null && def.FirstAvailableLevel != null && Meta.Number < def.FirstAvailableLevel` | `NotAvailable` |
| 4 | `TargetPos == null`，或不在 `[0, WidthM] × [0, HeightM]` 内 | `InvalidArgument` |
| 5 | 战斗机类（`IsFighter(Effect)`）且 `Meta.FighterMode == None` | `NotAvailable` |
| 6 | 战斗机类且 `FighterMode == OnmapAirbase` 且不存在 `Type == AirbaseRunway && Hp > 0` 的保护目标 | `AirbaseUnavailable` |
| 7 | 战斗机类且 `Support.SortiesRemaining <= 0` | `NoSortiesLeft` |
| 8 | 战斗机类且 `support.FrontlineRiskZoneBlocksCalls` 且 `ZoneRuleAt(TargetPos).FrontlineRisk` | `InRiskZone` |
| 9 | `cp = def.CommandPoints ?? 0`，`cp > 0 && !CommandPointRules.CanSpend(ctx, cp)` | `NoCommandPoints` |

`Apply`：`cp > 0` 时 `CommandPointRules.Spend(ctx, cp, CallSupport)`；战斗机类：`SortiesRemaining −= 1`；`PendingCalls.Add(new PendingCall(cmd.Seq, def.Id, TargetPos, cp, UsesSortie: IsFighter))`。

`FighterMode == OffmapAuto` 与 `OnmapSupportFacility` 在夜间按 `OffmapCall` 处理（8.1 Q-S2）。

#### 3.4.2 命令 `SetFighterZone`（处理者：本系统）

`Validate`：`SupportAssets.TryGet(id)` 失败 → 若该 ID 属于其他存储则 `WrongEntityKind`，否则 `UnknownEntity`；`!IsFighter(a.Effect)` → `WrongEntityKind`。`Apply`：`a.Exclusive = cmd.Exclusive`。夜间任何时刻可用；是否扣指挥点由 04 决定（默认不扣，8.1 Q-S7）。

#### 3.4.3 每步流程

```
now = ctx.TimeSec
# A. 处理本步接受的呼叫（PendingCalls 已按 CommandSeq 升序）
for pc in Support.PendingCalls:
    def = Support(pc.SupportDefId)
    refused = pc.UsesSortie and Night.BigRaid == true and Rng.Chance(support.BigRaidRefusalChance)   # 只在大空袭夜掷骰，恰好 1 次 NextDouble
    if refused:
        Support.SortiesRemaining += 1
        if pc.CommandPointsSpent > 0: CommandPointRules.Refund(ctx, pc.CommandPointsSpent, CallSupport)
        Support.CallsRefused += 1
        emit SupportRefused { SupportDefId = def.Id, Reason = BigRaidDiverted }
        continue
    a = SupportAssets.Add(new SupportAsset { DefId = def.Id, Effect = def.Effect, State = EnRoute, CenterPos = pc.TargetPos,
            Pos = pc.TargetPos, AltM = 0, ArriveAtSec = now + DelaySec(def), EndAtSec = −1,
            RadiusM = AssetRadius(def), Exclusive = support.Airspace.Exclusive.IsDefault,
            RoundsLeft = IsFighter ? FighterWeapon(def).Loadout : 0,
            KillsLeft  = def.Effect == UavHunt ? def.KillsPerSortie!.Value : −1,
            CommandPointsSpent = pc.CommandPointsSpent })
    Support.CallsAccepted += 1
    emit SupportRequested { SupportDefId = def.Id, SupportAssetId = a.Id }
Support.PendingCalls.Clear()

# B. 支援实体状态机（ID 升序，含 A 中刚创建的）
claims = 按 3.2.3 B 重新统计（包含系统 7 本步刚发射的拦截弹）
for a in SupportAssets (ID 升序):
    if a.State == EnRoute:
        if a.ArriveAtSec > now + Eps: continue
        a.State = Active; a.Pos = a.CenterPos
        a.EndAtSec = (def.Duration.Kind == GameSec) ? a.ArriveAtSec + def.Duration.Sec : −1
        emit SupportArrived { SupportAssetId = a.Id }
    endReason = null
    if a.EndAtSec >= 0 and now + Eps >= a.EndAtSec: endReason = Duration
    elif IsFighter(a.Effect) and a.RoundsLeft == 0: endReason = AmmoOut
    elif a.KillsLeft == 0: endReason = KillsReached
    if endReason != null:
        emit SupportEnded { SupportAssetId = a.Id, Reason = endReason }; SupportAssets.Remove(a.Id); continue
    if IsFighter(a.Effect): FighterEngage(a, claims)                     # 3.4.4
```

```
DelaySec(def):
    switch def.Delay.Kind:
        Instant: 0
        GameSec:
            if IsFighter(def.Effect): (Meta.FighterMode == OnmapAirbase ? def.Delay.OnMapAirbaseSec : def.Delay.OffMapSec) ?? def.Delay.Sec ?? 0
            else: def.Delay.Sec ?? 0
        NextDay: 不可达（Validate 第 2 条已拒绝）
AssetRadius(def):
    IsFighter → FighterWeapon(def).RangeM
    AccuracyDrop → EwUnit(def.AffectsSameAsEwUnitId).RadiusM（缺省引用 → 0；8.1 Q-S5）
    其他 → 0
```

`Duration.Kind ∈ {Nights, SameAsEwUnit}` 在夜间实体上按 `EndAtSec = −1` 处理（当前数据中只有夜间不可呼叫的条目使用 `Nights`）。

#### 3.4.4 战斗机交战（`FighterEngage`）

与 3.2.4 相同的结构，差异如下（未列出的步骤与地面火力单元一致）：

| 项 | 战斗机的取值 |
|---|---|
| 武器 | `FighterWeapon(def)`；可打标签 = `def.Targets == null ? weapon.Targets : weapon.Targets ∩ def.Targets`（保持 `weapon.Targets` 的顺序） |
| 位置 / 射程 / 射高 | 发射点 `a.Pos`（高度按 0）；射程 `weapon.RangeM`（无 `rangeByTag`）；射高 `Fighter(def.FighterId).CeilingM` |
| 航迹门槛 | `tracks.Allows(track.Quality, vector_fighters)`；`DecoyIdentified` 的航迹不打 |
| 规则 | `SalvoSize = engagement.FighterSalvoSize`，`ShootLookShoot = engagement.FighterShootLookShoot`，无 `HoldFire` / 白名单 / 保留弹药；排序 `SoonestIntercept` |
| 弹药 | `a.RoundsLeft`（每发 −1）；`n = min(n, a.RoundsLeft)` |
| 约束区 | 拦截点在 `NoEngagement` 区内 → 不打；不受其他战斗机空域规则影响 |
| 反应时间 | `ReactionSec` 取 `engagement.ByWeaponKind[weapon.Kind]`，不乘辐射 / 指示 / 限制交战倍率 |
| 射击间隔 | `ShotIntervalSec` 同上 |
| 概率 | `base × m1 × m7`（3.3.2） |
| 拦截弹 | `FireUnitId = 0`、`SupportAssetId = a.Id`、`LauncherIndex = 0`、`ShotCostMusd = weapon.ShotCostMusd` |
| 状态字段 | `a.TargetTrackId`、`a.ReadyAtSec`、`a.NextShotAtSec` |
| 保留原因 | 不调用 `MarkHeld`（支援不参与突防原因分析） |
| 目标计数 | 每发 `t.ShotsTaken += 1` |

`UavHunt` 的击落数在 3.3.1 中扣减（命中时 `KillsLeft −= 1`），本步发射前若 `KillsLeft == 0` 已在 3.4.3 结束。

#### 3.4.5 国家级导航欺骗（`AccuracyDrop`）

本系统只负责呼叫、延迟、到位、持续与结束（3.4.3）。**效果由 02 实现**：02 每步读取 `State == Active && Effect == AccuracyDrop` 的 `SupportAsset`，对 `|threat.Pos − a.CenterPos| ≤ a.RadiusM` 且受 `def.AffectsSameAsEwUnitId` 所指电子战单位影响的目标施加 `def.AccuracyTierDrop` 的降档（计入 D12 的 `EwTierDrop`）。

### 3.5 `ImpactSystem`（Order 10，子流 `impact`，WS01-011、017）

#### 3.5.1 `Initialize`

1. 保护目标：填 2.7 字段；`CarryIn` 给出 HP / `LossHp` 时使用之。
2. 电网节点：填 `Type`、`OffMapSupply`、`FacilityStructureId`；建立邻接表（3.6.1）。
3. 我方单位接入电网（3.6.2）。
4. 计算一次电网（3.6.3），**不发事件**；`GridState.Collapsed` 按结果设置，若为 true 则 `CollapsedAtSec = 0`。

#### 3.5.2 每步流程

```
now = ctx.TimeSec
# A. 碎片（本步命中的拦截判定）
for e in CurrentStep where e is InterceptResolved && e.Hit (Seq 升序):
    if !Threats.TryGetIncludingRemoved(e.ThreatId, out t) or t.Kind != Munition: continue
    frac = e.OverUrban ? debris.UrbanFrac : debris.RuralFrac
    if frac <= 0: continue
    L = RoundLevel(MunitionDef(t).DamageLevel * frac)
    if L < 1: continue
    S = e.OverUrban ? debris.UrbanRadiusM : 0
    first = ApplyDamageAt(e.Pos, L, S, vehicleMult: 1.0, sourceThreatId: t.Id, cause: Debris)   # 返回第一个受损保护目标的实体 ID，无则 0
    emit DebrisFell { Pos = e.Pos, StructureId = first, DamageLevel = L, SourceThreatId = t.Id }
    # 注意：DebrisFell 在其造成的 StructureDamaged 之后发出（ApplyDamageAt 内部先发）
# B. 落地
for e in CurrentStep where e is ThreatArrived (Seq 升序):
    if !Threats.TryGet(e.ThreatId, out t) or t.Kind != Munition: continue
    ResolveImpact(t, e.Pos)
    Threats.Remove(t.Id)
# C. 电网
if Grid.Dirty: RecomputeGrid(emitEvents: true); Grid.Dirty = false
```

> 碎片的 `DebrisFell` 顺序约定：为让事件流读起来是“碎片落下 → 造成损伤”，实现时先计算受损目标再发事件会更直观，但为了只遍历一次，**本规格规定 `DebrisFell` 在 `ApplyDamageAt` 之后发出**。测试按此顺序断言。

#### 3.5.3 有效精度档

```
EffectiveTier(def, t):
    order = accuracy.TierOrder                     # [D, C, B, A]
    idx   = order.IndexOf(def.Accuracy)
    boost = SpotterAlive() ? accuracy.SpotterTierBoost : 0
    drop  = (def.EwImmune == true) ? 0 : t.EwTierDrop
    idx   = Math.Clamp(idx + boost − drop, 0, order.Count − 1)
    return order[idx]
SpotterAlive() = 存在 Alive 的 Threat：Kind == Platform 且 PlatformDef(t).WhileAlive?.EnemyAccuracyTierBoost > 0
```

升档对地图上全部敌方弹药生效（“存活期间”），不要求侦察平台靠近目标（8.1 Q-D6）。

#### 3.5.4 落点偏移

```
Offset(aim, tier, t, def):
    tierDef = accuracy.Tiers[tier]
    extra   = (t.EwAffected && def.EwImmune != true) ? tierDef.EwExtraM : 0
    d  = Rng.Range(tierDef.OffsetM.Min, tierDef.OffsetM.Max) + extra     # 第 1 次 NextDouble
    th = Rng.Range(0.0, 2.0 * Math.PI)                                    # 第 2 次 NextDouble（方位角，正北顺时针）
    return aim + new Vec2(Math.Sin(th), Math.Cos(th)) * d
```

无论 `Min == Max == 0` 与否，都恰好消耗 2 次 `NextDouble`（保持序列对齐）。

#### 3.5.5 伤害衰减与等级取整

```
LevelRaw(L, r, S):                                  # r：到目标边缘的距离（m），S：溅射半径（m）
    if S <= 0: return (r <= Eps) ? L : 0.0
    if r > S + Eps: return 0.0
    f = damage.SplashCenterMult + (damage.SplashEdgeMult − damage.SplashCenterMult) * Math.Min(r / S, 1.0)
    return L * f
RoundLevel(x) = Math.Clamp((int)Math.Round(x, MidpointRounding.AwayFromZero), 0, 10)
BandFor(lv)   = damage.Bands 中 MinLevel ≤ lv ≤ MaxLevel 的一项（lv ≥ 1 时必然存在；加载器校验 1–10 被完整覆盖、不重叠）
```

取整方式见 8.1 Q-D2。

#### 3.5.6 `ApplyDamageAt(P, L, S, vehicleMult, sourceThreatId, cause)`

```
firstStructure = 0
# 保护目标（ID 升序；Hp == 0 的跳过）
for s in Structures:
    if s.Hp == 0: continue
    r  = Math.Max(0, |P − s.Pos| − s.RadiusM)
    lv = RoundLevel(LevelRaw(L, r, S))
    if lv >= 1 and ApplyStructureEffect(s, lv, sourceThreatId, cause) and firstStructure == 0: firstStructure = s.Id
# 我方单位（按 EntityKind 顺序：FireUnits、Sensors、EwUnits、DeceptionUnits；各自 ID 升序）
for u in 四类存储:
    r   = Math.Max(0, |P − u.Pos| − damage.UnitFootprintM)
    raw = LevelRaw(L, r, S)
    if u is FireUnit and UnitDef(u).Mobility ∈ {Vehicle, Towed}: raw *= vehicleMult
    lv  = RoundLevel(raw)
    if lv >= 1: ApplyUnitEffect(u, lv, sourceThreatId)
return firstStructure
```

`ApplyStructureEffect(s, lv, src, cause)`（返回是否造成了 HP 损失）：

```
band   = BandFor(lv)
isGrid = s.Type ∈ {PowerPlant, Substation}
if isGrid:
    loss = band.GridDamageFrac > 0 ? (int)Math.Ceiling(band.GridDamageFrac * s.MaxHp − Eps) : 0
else switch band.CivilEffect:
    Minor, Buildings: loss = band.CivilDestroyed != null ? Rng.RollInclusive((int)Min, (int)Max) : 0   # 有区间就掷，0–0 也掷（对齐）
    Block:            loss = s.Hp
loss = Math.Min(loss, s.Hp)
if loss == 0: return false
before = s.Hp; s.Hp −= loss
s.LossHp += loss * CivilFactor(s)                                       # 3.7.4
emit StructureDamaged { StructureId = s.Id, HpBefore = before, HpAfter = s.Hp, SourceThreatId = src, Cause = cause }
if s.Hp == 0: emit StructureDestroyed { StructureId = s.Id }
if isGrid and s.GridNodeId != 0: Grid.Dirty = true
return true
```

`ApplyUnitEffect(u, lv, src)`：

```
e = BandFor(lv).UnitEffect
if u is not FireUnit and e == DestroyComponent: e = DestroyFireUnit        # 非火力单元没有“部件”
switch e:
  LightDamage:
      m = band.EfficiencyMult ?? 1.0
      if m < u.DamageEfficiencyMult: u.DamageEfficiencyMult = m           # 不叠乘，取最小
      u.LightDamaged = true
      emit PlayerUnitDamaged { UnitId, DefId, Kind = Category(u), Effect = LightDamage, Component = None, SourceThreatId = src }
  HeavyDamage:
      u.SuspendedUntilSec = Math.Max(u.SuspendedUntilSec, now + band.SuspendSec!.Value)
      emit PlayerUnitDamaged { …, Effect = HeavyDamage, Component = None }
  DestroyComponent:                                                        # 只有 FireUnit 会到这里
      roll = Rng.NextDouble()                                              # 恒消耗 1 次
      if u.HasFireControlRadar and !u.RadarDestroyed and roll < damage.ComponentRadarChance:
          u.RadarDestroyed = true
          emit PlayerUnitDamaged { …, Effect = DestroyComponent, Component = Radar }
      else:
          w = u.Weapons 中 Launchers.Count 最大的一项（并列取下标最小）
          if w.Launchers.Count == 0: Destroy(u, src); break
          w.Launchers.RemoveAt(w.Launchers.Count − 1)
          emit PlayerUnitDamaged { …, Effect = DestroyComponent, Component = Launcher }
          if 所有武器的 Launchers.Count 都为 0: Destroy(u, src)
          else AnnounceDepletion(u, w)
  DestroyFireUnit, DestroyFireUnitAndAdjacent:
      Destroy(u, src)
Destroy(u, src): 对应存储 Remove(u.Id)；emit PlayerUnitDestroyed { UnitId = u.Id, DefId = u.DefId, Kind = Category(u), SourceThreatId = src }
```

“波及相邻格”由溅射本身体现，`DestroyFireUnitAndAdjacent` 不追加额外效果（8.1 Q-D4）。

#### 3.5.7 `ResolveImpact(t, aim)`

```
def = MunitionDef(t)
if def.TracksEmittingRadarOnly == true:                                    # 反辐射导弹
    pHit = Math.Clamp(t.ArmHitProbMult, 0, 1)
    if !(Rng.NextDouble() < pHit):                                         # 恒消耗 1 次
        emit ThreatImpacted { ThreatId = t.Id, DefId = def.Id, Pos = aim, AimPos = aim, DamageLevel = 0,
                              Tier = def.Accuracy, Outcome = ArmMissed, SubIndex = 0, LeakReason = null, LeakMask = 0 }
        return                                                             # 失锁：无伤害，不算突防
tier = EffectiveTier(def, t)
(reason, mask) = LeakAnalysis(t)                                            # 3.8.4
if def.Submunitions != null:
    for k in 0 .. Submunitions.Count − 1:
        P = Offset(aim, tier, t, def)
        emit ThreatImpacted { …, Pos = P, AimPos = aim, DamageLevel = Sub.DamageLevel, Tier = tier, Outcome = Submunition,
                              SubIndex = k, LeakReason = (k == 0 ? reason : null), LeakMask = (k == 0 ? mask : 0) }
        ApplyDamageAt(P, Sub.DamageLevel, Sub.SplashM, def.VehicleDamageMult ?? 1.0, t.Id, Impact)
else:
    P = Offset(aim, tier, t, def)
    emit ThreatImpacted { …, Pos = P, AimPos = aim, DamageLevel = def.DamageLevel, Tier = tier, Outcome = Normal,
                          SubIndex = 0, LeakReason = reason, LeakMask = mask }
    ApplyDamageAt(P, def.DamageLevel, def.SplashM, def.VehicleDamageMult ?? 1.0, t.Id, Impact)
```

- 有子弹头的弹药只结算子弹头，母弹的 `damageLevel` 不另行结算（数值表“6 × 6 次命中”）。
- 反辐射导弹命中时与普通弹药相同（落点 = 01 给出的到达点，即目标辐射源位置；精度档偏移照常）。
- 被电子战诱偏的目标：01 / 02 已改变其到达点，本系统不做额外处理（`debris.divertedImpactFullDamageInUrban = true` 即“全额伤害”）。

### 3.6 电网（在 `ImpactSystem` 中，WS01-018）

#### 3.6.1 拓扑

- 连线视为**无向**（8.1 Q-G1）。邻接表 `GridState.Adjacency`（`int[][]`，按节点存储下标，每个邻居列表按实体 ID 升序；`Initialize` 时由 `Grid.Links` 建立，重复连线去重）。**不参与哈希**（由静态数据派生）。

#### 3.6.2 我方单位接入

```
R = civil.Grid.UnitConnectRadiusM
for u in 我方单位（EntityKind 顺序，ID 升序）where Category(u) ∈ civil.Grid.UnitCategoriesOnGrid:
    best = 0; bestD = +∞
    for n in GridNodes (ID 升序) where n.Type ∈ {Consumer, Substation}:
        d = |n.Pos − u.Pos|
        if d <= R + Eps and d < bestD: best = n.Id; bestD = d          # 严格小于 → 并列取 ID 小者
    u.GridNodeId = best
```

`R == 0` 时没有单位接入电网。

#### 3.6.3 断电传播（`RecomputeGrid`）

```
for n in GridNodes: n.OperationalNew = (n.FacilityStructureId == 0) or Structure(n.FacilityStructureId).Hp > 0
visited = bool[GridNodes.Count]
queue = []
for n in GridNodes (ID 升序): if n.OperationalNew and (n.Type == Source or n.OffMapSupply): visited[n] = true; queue.Enqueue(n)
while queue 非空:
    n = queue.Dequeue()
    for m in Adjacency[n]: if !visited[m] and m.OperationalNew: visited[m] = true; queue.Enqueue(m)
for n in GridNodes (ID 升序):
    n.Operational = n.OperationalNew
    newPowered = visited[n]
    if newPowered != n.Powered:
        n.Powered = newPowered
        if emitEvents: emit GridPowerChanged { GridNodeId = n.Id, Powered = newPowered }
for s in Structures: s.Powered = (s.GridNodeId == 0) or GridNode(s.GridNodeId).Powered
for u in 我方单位: if u.GridNodeId != 0: u.Powered = GridNode(u.GridNodeId).Powered
consumers = GridNodes where Type == Consumer
Grid.Collapsed = consumers.Count >= 1 and consumers 全部 !Powered
if Grid.Collapsed and Grid.CollapsedAtSec < 0: Grid.CollapsedAtSec = now
```

- `Initialize` 时所有节点 `Powered` 初值为 false，调用 `RecomputeGrid(emitEvents: false)`。
- 一个节点没有电网设施（如 `node_city`）时不会因攻击失效，只会因上游断开而断电。
- 电网崩溃后又不会恢复（夜间无维修），`Collapsed` 一旦为 true 保持 true（重算结果必然仍为 true）。

#### 3.6.4 断电的效果

| 对象 | 效果 | 实现者 |
|---|---|---|
| 探测单位、电子战单位（`Powered == false`） | 效能下降 / 停机，数值待决 | **02** 读取 `Powered`（8.1 Q-G2） |
| 火力单元 | 无（不接入电网） | — |
| 工厂（`StructureType.Factory`） | 停产：`PausedSec` 累计（3.7.3） | 05 换算产量 |
| 避难所（`StructureType.Shelter`） | 防护打折：`ShelterQuality`（3.7.3） | 本文件 |
| `grid_collapse` 失败条件 | `Grid.Collapsed` | 本文件 3.8.5 |

### 3.7 空袭警报（WS01-024；状态切换在阶段 0，效果在 `ScoringSystem`）

#### 3.7.1 命令 `SetAirRaidAlert`（处理者：`ScoringSystem`，00 Q5）

`Validate`：`cmd.On == Civil.AlertOn` → `InvalidState`。`Apply`：`CivilRules.SetAlert(ctx, cmd.On, AlertCause.Command)`。指挥点由 04 规定（GDD 5.2 列为指挥点操作）。

#### 3.7.2 `CivilRules.SetAlert(ctx, on, cause)`（04 的剧情动作 `set_alert` 也调用此函数，`cause = Story`）

```
if on == Civil.AlertOn: return                 # 剧情动作重复设置时静默忽略
Civil.AlertOn = on; Civil.AlertChangedAtSec = ctx.TimeSec
if on:
    Civil.RaisesTonight += 1
    if Civil.RaisesTonight > civil.Alert.FreeRaisesPerNight:
        Civil.Responsiveness = Math.Max(civil.Alert.MinResponsiveness, Civil.Responsiveness − civil.Alert.FatiguePerExtraRaise)
else:
    Civil.ShelteredFrac = 0
emit AirRaidAlertChanged { On = on, Cause = cause }
```

#### 3.7.3 每步更新（`ScoringSystem.Execute` 的第 1 步）

```
dt = ctx.StepSec
if Civil.AlertOn:
    Civil.AlertActiveSec += dt
    target = Civil.Responsiveness
    rise   = civil.Alert.ShelterSec > 0 ? target * dt / civil.Alert.ShelterSec : target
    Civil.ShelteredFrac = Math.Min(target, Civil.ShelteredFrac + rise)
    Civil.ShelteredPeakFrac = Math.Max(Civil.ShelteredPeakFrac, Civil.ShelteredFrac)
N0 = 夜开始时 Type == Shelter 的保护目标数（Initialize 记录，不参与哈希的派生量）
Civil.ShelterQuality = (N0 == 0) ? 1.0 : Σ_{s: Type==Shelter, Hp>0} (s.Powered ? 1.0 : civil.Grid.UnpoweredShelterProtectionMult) / N0
for s in Structures:
    if !s.Powered: s.UnpoweredSec += dt
    if !s.Powered or Civil.AlertOn: s.PausedSec += dt
```

#### 3.7.4 避难对损失的影响

```
CivilFactor(s) = s.Type ∈ civil.Alert.PopulationStructureTypes
                 ? 1 − Civil.ShelteredFrac * civil.Alert.ProtectionFrac * Civil.ShelterQuality
                 : 1.0
```

- 在 `ImpactSystem`（10）中使用，读取的是上一步 `ScoringSystem` 更新后的 `ShelteredFrac` / `ShelterQuality`。
- 只影响 `LossHp`（计入加权损失与失败条件），不影响物理 `Hp`（建筑照样被毁）。即：拉响警报让“失败条件风险下降”（GDD 8.6）。
- 城市资源停止积累：本文件只输出 `CivilSummary.AlertActiveSec`，由 05 换算。

### 3.8 `ScoringSystem`（Order 13，子流 `scoring`，0 消耗，WS01-023）

#### 3.8.1 每步流程

```
1. 空袭警报更新（3.7.3）
2. for e in CurrentStep (Seq 升序):
     ThreatSpawned       → ThreatsSpawned += 1
     ThreatExited        → ThreatsExited  += 1
     InterceptorLaunched → Tally(e.WeaponId).Shots += 1; c = ShotCost(e.WeaponId); Tally.ShotCostMusd += c; TotalShotCostMusd += c
                           if TrueTag(e.ThreatId) == DECOY: Tally.DecoyShots += 1; Tally.DecoyCostMusd += c
     GunFired            → 同上，另 Tally.GunRoundsUsed += e.RoundsUsed
     InterceptResolved   → if e.Hit: ThreatsIntercepted += 1; Tally(e.WeaponId).Hits += 1
                                     v = PotentialLoss(e.ThreatId); Tally.PotentialLossMusd += v; TotalPotentialLossMusd += v
                                     if e.OverUrban: InterceptsOverUrban += 1
                                     if e.SupportAssetId != 0: SupportKills += 1
     ThreatImpacted      → if e.Outcome != ArmMissed and e.SubIndex == 0:
                               ThreatsImpacted += 1; Leaks.Add(LeakRecord(e))
                               if e.DamageLevel(母弹定义的 damageLevel；子弹头取 Submunitions.Count × Sub.DamageLevel) >= civil.Scoring.HighThreatDamageLevel
                                  and (e.LeakMask 含 HeldByRule): HighThreatLeaksWithReserve += 1
     StructureDamaged    → if e.Cause == Debris: DebrisHpLost += e.HpBefore − e.HpAfter
     DebrisFell          → DebrisEvents += 1
     PlayerUnitDamaged / PlayerUnitDestroyed → UnitLosses.Add(UnitLossRecord(e))
3. for u in 我方单位（EntityKind 顺序，ID 升序）: ExposureMax[u.Id] = max(ExposureMax.GetValueOrDefault(u.Id, u.Exposure), u.Exposure)
4. if State.EndRequest == null:
     for c in Meta.Defeat（数据顺序）:
        if Holds(c): State.EndRequest = new EndRequest(Defeated, DefeatCondition, Detail(c)); break
```

- `TrueTag(threatId)`：`Threats.TryGetIncludingRemoved` 取 `Tag`；本步已压缩掉的旧目标（不可能出现：事件与删除同步）按 `null`。
- `ShotCost(weaponId)`：先查 `GameCatalog.Weapons`（`ShotCostMusd ?? 0`），再查战斗机武器（`ShotCostMusd`）。加载器校验战斗机武器 ID 与防空武器 ID 不重复（8.2）。
- `Initialize`：`ExposureStart[u.Id] = u.Exposure`（全部我方单位）。

#### 3.8.2 加权损失

```
WeightedLossFrac() = Σw == 0 ? 0 : Σ_s ( s.Weight * s.LossHp / s.MaxHp ) / Σ_s s.Weight          # 全部保护目标，按 ID 升序累加
WeightedLossFracAtNightStart 用 Initialize 时的 LossHp 计算
```

#### 3.8.3 交换比（GDD 9.3、数值表第 4 节）

```
PotentialLoss(threatId):
    t = Threats.TryGetIncludingRemoved(threatId)
    if t.Tag == DECOY: return 0                                              # 诱饵没有潜在损失：打诱饵 = 纯消耗
    if t.Kind == Platform: return civil.Scoring.PlatformPotentialLossMusd
    def = MunitionDef(t)
    L = def.Submunitions != null ? def.Submunitions.Count * def.Submunitions.DamageLevel : def.DamageLevel
    w = (t.TargetStructureId != 0) ? Structure(t.TargetStructureId).Weight : 1.0
    return L * civil.Scoring.LossMusdPerDamageLevel * w
ExchangeRatio = TotalShotCostMusd > 0 ? TotalPotentialLossMusd / TotalShotCostMusd : null
每种武器：Ratio = ShotCostMusd > 0 ? PotentialLossMusd / ShotCostMusd : null
```

- 分母是**全部发射**（含未命中、射向诱饵、夜晚结束时仍在飞行的拦截弹）的价格；支援发射也计入（按其武器价格）。
- 敌方成本 `costMusd` 不进入交换比，只在 `LeakRecord` / 复盘中显示（8.1 Q-X1）。
- 信任度的增减由 05 依据 `ExchangeSummary` 与 `HighThreatLeaksWithReserve`（GDD 9.3 第 3 条“让高威胁目标突防，但昂贵弹药仍有剩余”）计算。

#### 3.8.4 突防原因（`LeakAnalysis`，GDD 15.5）

在 `ImpactSystem` 结算落地时调用（目标仍在），结果写入 `ThreatImpacted`。

```csharp
public enum LeakReason { Undetected = 0, DecoyDrain = 1, AmmoDepleted = 2, EmissionSilent = 3, InterceptMissed = 4,
                         HeldByRule = 5, PoorTrack = 6, Saturated = 7, DefenseDamaged = 8, EwIneffective = 9, OutOfCoverage = 10 }
```

| 原因（= 优先级，值小者优先） | 条件 | GDD 15.5 对应 |
|---|---|---|
| `Undetected` | `t.MaxTrackQuality < 0` | 未探测 |
| `DecoyDrain` | `t.DecoyDrained` | 诱饵消耗 |
| `AmmoDepleted` | `HeldMask` 含 `AmmoDepleted` 或 `PerLevelLimitReached` | 弹药耗尽 |
| `EmissionSilent` | `HeldMask` 含 `EmissionSilent` | 静默中 |
| `InterceptMissed` | `t.ShotsTaken > 0` | （补充）拦截未命中 |
| `HeldByRule` | `HeldMask` 含 `HoldFire`、`IdentifiedDecoy`、`TagNotAllowedByRule`、`AmmoReserve`、`NoEngagementZone`、`FighterExclusiveZone`、`NotConfirmedHostile` 之一 | （补充）交战规则限制 |
| `PoorTrack` | `HeldMask` 含 `TrackQualityTooLow` | （补充）航迹质量不足 |
| `Saturated` | `HeldMask` 含 `ChannelBusy`、`CannotIntercept`、`BarrelCooling` 之一 | （补充）火力饱和 / 追不上 |
| `DefenseDamaged` | `HeldMask` 含 `Suspended` 或 `FireControlOff` | （补充）防空受损 |
| `EwIneffective` | `t.EwCovered` | 电子战失效 |
| `OutOfCoverage` | 以上都不满足 | （补充）不在任何火力覆盖内 |

`LeakMask = Σ (1 << (int)r)`，对所有条件成立的 `r`（`OutOfCoverage` 只在其余全不成立时置位）；`LeakReason` = 成立者中值最小的一个。

#### 3.8.5 胜负条件

```
Holds(c):
    StructureDestroyed:     Structure(StructureIdByDefId[c.StructureId]).Hp == 0
    WeightedDamageAtLeast:  WeightedLossFrac() >= c.Fraction
    GridCollapse:           Grid.Collapsed
    SurviveNights, SurviveGameSec: false             # 出现在 defeat 中无意义：加载器报 E_RANGE（8.2）
Detail(c):
    StructureDestroyed    → "structure_destroyed:" + c.StructureId
    WeightedDamageAtLeast → "weighted_damage_at_least:" + c.Fraction.ToString("R", InvariantCulture)
    GridCollapse          → "grid_collapse"
```

- 失败条件满足时立即结束当夜（00 Q3）。
- 胜利条件（`victory[]`）不在夜内判定：`survive_nights` / `survive_game_sec` 由 05 用多夜结果判定（00 Q4）；夜晚以 `Survived` 结束即本夜“守住”。`victory` 中出现 `structure_destroyed` / `weighted_damage_at_least` / `grid_collapse` → 加载器报 `E_RANGE`（8.2）。

#### 3.8.6 `NightResult`（`BuildResult`）

`ScoringSystem.BuildResult(ctx, outcome, reason)` 由 `CheckNightEnd` 调用（00 3.5），只读状态，不发事件、不用随机数。03 负责的部分：

```csharp
public sealed record LossesSummary
{
    public double WeightedLossFrac { get; init; }
    public double WeightedLossFracAtNightStart { get; init; }
    public IReadOnlyList<StructureResult> Structures { get; init; }        // 实体 ID 升序（= 数据顺序）
    public IReadOnlyList<UnitLossRecord> UnitLosses { get; init; }         // 事件顺序
    public IReadOnlyList<LeakRecord> Leaks { get; init; }                  // 事件顺序
    public IReadOnlyList<LeakReasonCount> LeakReasonCounts { get; init; }  // LeakReason 全部 11 个值，按枚举值升序，含 0
    public int ThreatsSpawned { get; init; } public int ThreatsIntercepted { get; init; }
    public int ThreatsImpacted { get; init; } public int ThreatsExited { get; init; }
    public int HighThreatLeaksWithReserve { get; init; }
    public bool GridCollapsed { get; init; } public double? GridCollapsedAtSec { get; init; }
    public IReadOnlyList<string> UnpoweredGridNodeIds { get; init; }        // 数据 ID，按实体 ID 升序
}
public sealed record StructureResult(string StructureId, StructureType Type, double Weight, int MaxHp, int HpStart, int HpEnd,
                                     double LossHp, bool Destroyed, bool PoweredAtEnd, double UnpoweredSec, double PausedSec);
public enum UnitLossKind { Damaged = 0, Destroyed = 1 }
public enum DamagedComponent { None = 0, Radar = 1, Launcher = 2 }
public sealed record UnitLossRecord(int Tick, int UnitId, string UnitDefId, PlayerUnitCategory Category, UnitLossKind Kind,
                                    UnitDamageEffect Effect, DamagedComponent Component, int SourceThreatId, string? SourceThreatDefId);
public sealed record LeakRecord(int Tick, int ThreatId, string ThreatDefId, TargetTag? Tag, Vec2 Pos, int DamageLevel,
                                LeakReason Reason, int ReasonMask, string? TargetStructureId, double? EnemyCostMusd);
public sealed record LeakReasonCount(LeakReason Reason, int Count);

public sealed record AmmoSummary
{
    public IReadOnlyList<WeaponAmmoResult> Weapons { get; init; }          // 本夜出现过（部署了或发射过）的武器，WeaponId 序数升序
    public IReadOnlyList<PoolRemainingResult> PoolRemaining { get; init; }  // EngagementState.AmmoPoolRemaining 的副本，序数升序
}
public sealed record WeaponAmmoResult(string WeaponId, int Shots, int Hits, int GunRoundsUsed, double ShotCostMusd, bool CostUnknown,
                                      int RoundsRemaining /* 全部存活单位该武器余弹之和；任一为 −1 则 −1 */, int PerLevelUsedTotal);
public sealed record PoolRemainingResult(string WeaponId, int Rounds);

public sealed record ExchangeSummary
{
    public double TotalPotentialLossMusd { get; init; } public double TotalShotCostMusd { get; init; }
    public double? ExchangeRatio { get; init; }
    public int DecoyShots { get; init; } public double DecoyCostMusd { get; init; }
    public IReadOnlyList<WeaponExchange> ByWeapon { get; init; }           // 有发射的武器，序数升序
}
public sealed record WeaponExchange(string WeaponId, int Shots, int Kills, double ShotCostMusd, double PotentialLossMusd, double? Ratio);

public sealed record DebrisSummary
{
    public int InterceptsTotal { get; init; } public int InterceptsOverUrban { get; init; }
    public double? UrbanInterceptRatio { get; init; }                      // InterceptsTotal == 0 或 !ScoreUrbanInterceptRatio → null
    public int DebrisEvents { get; init; } public int DebrisHpLost { get; init; }
}
public sealed record ExposureSummary { public IReadOnlyList<UnitExposure> Units { get; init; } }  // ExposureStart 的键序（单位 ID 升序）
public sealed record UnitExposure(int UnitId, string UnitDefId, PlayerUnitCategory Category, double Start, double End, double Max, bool Alive);
                                     // 已被毁的单位：End = 被毁前最后一步的值（取 ExposureMax 记录时同步保存的最近值），Alive = false

public sealed record CivilSummary      // 【新】NightResult.Civil
{
    public int AlertRaises { get; init; } public double AlertActiveSec { get; init; } public bool AlertOnAtEnd { get; init; }
    public double ResponsivenessStart { get; init; } public double ResponsivenessEnd { get; init; } public double ShelteredPeakFrac { get; init; }
}
public sealed record SupportSummary    // 【新】NightResult.Support
{
    public int CallsAccepted { get; init; } public int CallsRefused { get; init; } public int SortiesRemaining { get; init; } public int Kills { get; init; }
}
```

- `InterceptsTotal = ThreatsIntercepted`。
- `UnitExposure.End`：为得到被毁单位的最后暴露度，`ScoringState` 另存 `ExposureLast: SortedDictionary<int,double>`（第 3 步与 `ExposureMax` 同时写当前值）。
- **序列化**：`System.Text.Json`，`JsonSerializerOptions { PropertyNamingPolicy = CamelCase, WriteIndented = false, NumberHandling = Strict }` + `JsonStringEnumConverter`；`Vec2` 序列化为 `{"x":…,"y":…}`；所有 `double` 有限（比值无定义时为 `null`，不得写 `NaN` / `Infinity`）；集合顺序如上注明，保证同一夜两次序列化逐字节相同。反序列化后与原对象逐字段相等（集合按序比较）。

---

## 4. 事件与命令

### 4.1 本文件使用的枚举

```csharp
public enum HoldReason { HoldFire = 0, IdentifiedDecoy = 1, TagNotAllowedByRule = 2, TrackQualityTooLow = 3, EmissionSilent = 4,
                         FireControlOff = 5, AmmoDepleted = 6, PerLevelLimitReached = 7, AmmoReserve = 8, NoEngagementZone = 9,
                         FighterExclusiveZone = 10, NotConfirmedHostile = 11, CannotIntercept = 12, ChannelBusy = 13,
                         Suspended = 14, BarrelCooling = 15 }
public enum InterceptorExpiryCause { TargetGone = 0 }
public enum ImpactOutcome { Normal = 0, Submunition = 1, ArmMissed = 2 }
public enum DamageCause { Impact = 0, Debris = 1 }
public enum AlertCause { Command = 0, Story = 1 }
public enum SupportRefusalReason { BigRaidDiverted = 0 }
public enum SupportEndReason { Duration = 0, AmmoOut = 1, KillsReached = 2 }
```

### 4.2 事件字段（00 4.2 总表 300–317 的细化；字段顺序 = `WriteHash` 顺序）

“新增字段”列为相对 00 总表新增、需登记的字段（8.2 R-EV）。所有 ID 为实体 ID（`int`，0 = 无），`…DefId` / `WeaponId` 为数据 ID。

| 值 | 事件 | 字段（顺序） | 新增字段 | `AtSec` | 产生者 |
|---|---|---|---|---|---|
| 300 | `InterceptorLaunched` | `int FireUnitId, int LauncherIndex, string WeaponId, int InterceptorId, int TrackId, int ThreatId, int SupportAssetId` | `ThreatId`、`SupportAssetId` | null | 7、9 |
| 301 | `GunFired` | `int FireUnitId, string WeaponId, int TrackId, int ThreatId, double Probability, int RoundsUsed` | `ThreatId`、`Probability`、`RoundsUsed` | null | 7 |
| 302 | `InterceptResolved` | `int? InterceptorId, int ThreatId, bool Hit, double Probability, Vec2 Pos, double AltM, bool OverUrban, string WeaponId, int FireUnitId, int SupportAssetId` | `Pos`、`AltM`、`OverUrban`、`WeaponId`、`FireUnitId`、`SupportAssetId` | 拦截弹 = 拦截时刻；身管 = null | 8 |
| 303 | `InterceptorExpired` | `int InterceptorId, InterceptorExpiryCause Cause` | — | null | 8 |
| 304 | `EngagementHeld` | `int FireUnitId, string WeaponId, int TrackId, int ThreatId, HoldReason Reason` | 全部字段（00 只写了含义） | null | 7 |
| 305 | `AmmoDepleted` | `int FireUnitId, string WeaponId` | — | null | 7、10 |
| 306 | `ThreatImpacted` | `int ThreatId, string DefId, Vec2 Pos, Vec2 AimPos, int DamageLevel, AccuracyTier Tier, ImpactOutcome Outcome, int SubIndex, LeakReason? LeakReason, int LeakMask` | `DefId`、`AimPos`、`Tier`、`Outcome`、`SubIndex`、`LeakReason`、`LeakMask` | null | 10 |
| 307 | `StructureDamaged` | `int StructureId, int HpBefore, int HpAfter, int SourceThreatId, DamageCause Cause` | `Cause` | null | 10 |
| 308 | `StructureDestroyed` | `int StructureId` | — | null | 10 |
| 309 | `PlayerUnitDamaged` | `int UnitId, string DefId, PlayerUnitCategory Kind, UnitDamageEffect Effect, DamagedComponent Component, int SourceThreatId` | 全部字段 | null | 10 |
| 310 | `PlayerUnitDestroyed` | `int UnitId, string DefId, PlayerUnitCategory Kind, int SourceThreatId` | `SourceThreatId` | null | 10 |
| 311 | `DebrisFell` | `Vec2 Pos, int StructureId, int DamageLevel, int SourceThreatId` | `DamageLevel`、`SourceThreatId`；`StructureId` 由 `int?` 改为 `int`（0 = 无） | null | 10 |
| 312 | `GridPowerChanged` | `int GridNodeId, bool Powered` | — | null | 10 |
| 313 | `AirRaidAlertChanged` | `bool On, AlertCause Cause` | — | null | 阶段 0 |
| 314 | `SupportRequested` | `string SupportDefId, int SupportAssetId` | — | null | 9 |
| 315 | `SupportRefused` | `string SupportDefId, SupportRefusalReason Reason` | — | null | 9 |
| 316 | `SupportArrived` | `int SupportAssetId` | — | null | 9 |
| 317 | `SupportEnded` | `int SupportAssetId, SupportEndReason Reason` | `Reason` | null | 9 |

`PlayerUnitCategory` 即 00 1.6 的枚举（`Fire / Sensor / Ew / Deception`），事件中字段名沿用 00 的 `Kind`。

**本文件读取的其他规格事件**：`ThreatSpawned`（101）、`ThreatArrived`（103）、`ThreatExited`（104）——只读，用于 3.5.2 与 3.8.1。

### 4.3 命令（00 4.3 总表 300–303 的细化）

| 值 | 命令 | 字段 | 处理者 | 生效 | 拒绝原因（按检查顺序） |
|---|---|---|---|---|---|
| 300 | `SetEngagementRule` | `int FireUnitId, string? WeaponId, EngagementRule Rule` | `EngagementSystem` | 阶段 0；同一步系统 7 即按新规则决策 | `UnknownEntity` / `WrongEntityKind`（ID 不在 `FireUnits`）；`InvalidArgument`（`WeaponId` 非 null 且不属于该单位；`Rule.SalvoSize ∉ [1, MaxSalvoSize]`；`Rule.AmmoReserve < 0`） |
| 301 | `CallSupport` | `string SupportDefId, Vec2? TargetPos` | `ExternalSupportSystem` | 阶段 0 接受；同一步系统 9 掷拒绝骰、创建支援 | 见 3.4.1 |
| 302 | `SetAirRaidAlert` | `bool On` | `ScoringSystem` | 阶段 0 立即切换 | `InvalidState`（与当前相同） |
| 303 | `SetFighterZone` | `int SupportAssetId, bool Exclusive` | `ExternalSupportSystem` | 阶段 0 | `UnknownEntity` / `WrongEntityKind` |

`SetEngagementRule.Apply`：`WeaponId == null` → 替换 `Default`；否则替换（或追加）`PerWeapon` 中该武器的项。**不重置**已锁定目标与反应计时：新规则下目标不再合格时，系统 7 自然放弃它。

**新增拒绝原因**（03 段，从 300 起）：`NoSortiesLeft = 300`、`InRiskZone = 301`、`AirbaseUnavailable = 302`。

---

## 5. 边界情况

| # | 情况 | 处理 |
|---|---|---|
| 1 | 拦截弹飞行途中目标已被别的拦截弹 / 身管击落 | 到点时 `TryGet` 失败 → `InterceptorExpired(TargetGone)`，不掷骰 |
| 2 | 同一齐射两枚拦截弹同一时刻到达 | 按 ID 顺序结算；第一枚命中后第二枚 `TargetGone` |
| 3 | 目标在拦截时刻之前落地（预测失准，如被电子战诱偏后提前到达） | 落地在系统 10 结算并删除目标；拦截弹下一步 `TargetGone` |
| 4 | 拦截时刻与落地在同一步 | 系统 8 先于 10：拦截判定在先；命中则不再落地 |
| 5 | 航迹被删除（`TrackLost`）但目标仍在 | 已发射的拦截弹照常飞向 `TargetThreatId` 并结算；系统 7 不再以该航迹为候选，`TargetTrackId` 失效后下一步置 0 |
| 6 | 同一目标有两条航迹 | 占用数按 `ThreatId` 统计，不会重复射击；两条航迹各自可被 `MarkHeld` |
| 7 | 弹药为 0 | `AmmoDepleted` 保留原因；`AmmoDepleted` 事件每武器一夜只发一次 |
| 8 | `TotalRounds = −1`（不计数） | 永不耗尽；`AmmoReserve` 不生效 |
| 9 | 身管余弹少于一次射击耗弹 | 打出最后一次，`RoundsUsed` = 余弹数，之后耗尽 |
| 10 | 单位在撤收 / 展开中 | `CanAct == false`：不开火，不记保留原因 |
| 11 | 单位被暂停（重伤）期间被命令改规则 | 命令照常接受；暂停结束后按新规则 |
| 12 | 火力单元被毁时它锁定的目标 | 单位从存储删除，其 `WeaponState` 随之消失；已发射的拦截弹照常结算 |
| 13 | 反应计时中目标离开射程 | 第 3 步选不中它 → 换目标或 `TargetTrackId = 0`；回到射程后重新计时 |
| 14 | `rule.SalvoSize` 大于余弹 | `n` 截断为余弹数 |
| 15 | `perLevelLimit` 已用完（`CarryIn` 带入） | `PerLevelLimitReached`，夜内一发不发 |
| 16 | 武器 `targets` 中有标签但拦截类别矩阵缺该列 | 不视为可交战（3.2.4 第 1 步跳过） |
| 17 | 未甄别诱饵（`PerceivedTag = UAV`），武器 `targets` 含 `UAV` 不含 `DECOY` | 照常交战（玩家看不出是诱饵）；概率按 `decoyUsesColumn`；计入 `DecoyShots` |
| 18 | `restrictToEnemies` 武器面对非精确航迹 | 跳过（需要精确航迹才能识别型号） |
| 19 | 敌方平台被击落时仍携带弹药 | 弹药随平台消失（01 负责不再投放） |
| 20 | 精度档升档到 A 以上 / 降档到 D 以下 | 截断在 `TierOrder` 两端 |
| 21 | 溅射为 0 的弹药偏离目标 | 只有距离 ≤ 目标半径（保护目标）/ ≤ `UnitFootprintM`（我方单位）才受损 |
| 22 | 同一次落地同时伤及多个保护目标和单位 | 全部结算；随机数按“保护目标 ID 升序 → 单位 EntityKind、ID 升序”消耗 |
| 23 | 已被毁（`Hp == 0`）的保护目标再次被命中 | 跳过，不发事件 |
| 24 | 子弹头命中已在前一个子弹头中被毁的单位 | 该单位已删除，遍历跳过 |
| 25 | 反辐射导弹追踪的雷达在落地前已被毁 | 照常结算落点（01 给出的到达点）；`ArmHitProbMult` 由 02 维持 |
| 26 | 碎片源目标是平台 | 平台没有伤害等级，不产生碎片 |
| 27 | 拦截点在城区边界上 | 由 `Geo.PointInPolygon` 的半开规则决定，不另做特判 |
| 28 | 电网中某节点无连线 | 若为电源 → 自身供电；否则永远断电 |
| 29 | 电网没有任何 `consumer` 节点 | `Collapsed` 恒为 false |
| 30 | 电源节点的电厂被毁后同一步又有碎片命中下游变电站 | 本步末一次重算，事件按节点 ID 升序 |
| 31 | 警报已开再次拉响 | 命令 `InvalidState`；剧情动作静默忽略 |
| 32 | 警报响应度降到下限 | 截断在 `MinResponsiveness` |
| 33 | 呼叫战斗机时额度为 0 / 风险区 / 无战斗机模式 | 见 3.4.1 拒绝原因 |
| 34 | 呼叫被拒绝（大空袭夜） | 架次、指挥点退还；`SupportRefused`；不创建实体 |
| 35 | 同一步两次呼叫，额度只剩 1 | 第二条 `Validate` 看到第一条 `Apply` 后的额度 → `NoSortiesLeft` |
| 36 | 战斗机到位时间超过夜晚长度 | 夜晚结束时仍为 `EnRoute`；`SupportSummary` 中计为已接受 |
| 37 | 定向拦截（`until_ammo_out`）一直没有目标 | 持续到夜晚结束（8.1 Q-S3） |
| 38 | 战斗机拦截弹在战斗机返航后到达 | 照常结算；`KillsLeft` 只在实体仍存在时扣减 |
| 39 | `SetFighterZone` 指向已结束的支援 | `UnknownEntity` |
| 40 | `ShotCostMusd == null` 的武器 | 成本按 0；`CostUnknown = true`；交换比分母不含它 |
| 41 | 本夜一次都没开火 | `ExchangeRatio = null` |
| 42 | 本夜零拦截 | `UrbanInterceptRatio = null` |
| 43 | 同一步满足多个失败条件 | 按 `defeat[]` 数据顺序取第一个写 `Detail` |
| 44 | 失败条件与夜晚到时同一步 | `EndRequest` 优先（00 5 第 7 条） |
| 45 | 拦截点恰在禁止交战区边界 | 由 `PointInPolygon` 决定 |
| 46 | `level.number = null` 的测试关卡 | 支援不设首次可用关卡闸门 |
| 47 | 解析拦截时目标正在远离且速度大于拦截弹 | `Solve` 无可行采样点 → `null` → `CannotIntercept` |
| 48 | 目标已在发射点正上方 | 第 1 个采样点通常即可行，二分得到很小的 `t`；拦截可能在本步系统 8 即结算（`AtSec ≤ Tick`） |

---

## 6. 不变量（`CheckInvariants` 时每步末尾检查）

1. 每个 `LauncherState.RoundsLeft ≥ −1`；`WeaponState.ShotsFired ≥ 0`；`PerLevelLimit` 非空时 `PerLevelUsedBefore + ShotsFired ≤ PerLevelLimit`。
2. 每个 `Interceptor`：`LaunchAtSec ≤ InterceptAtSec`；`InterceptAtSec > TimeSec − StepSec`（未结算的拦截弹不会“过期未处理”）；`0 ≤ HitProbability ≤ 1`；`FireUnitId` 与 `SupportAssetId` 恰有一个非 0。
3. 每个 `Structure`：`0 ≤ Hp ≤ MaxHp`；`0 ≤ LossHp ≤ MaxHp − Hp + 1e-9`。
4. 每个我方单位：`0 < DamageEfficiencyMult ≤ 1`；`SuspendedUntilSec ≥ 0`。
5. `0 ≤ Civil.ShelteredFrac ≤ Civil.Responsiveness ≤ 1`；`Civil.Responsiveness ≥ MinResponsiveness`（若开局值已低于下限则 `≥` 开局值）；`AlertOn == false ⇒ ShelteredFrac == 0`。
6. `Support.SortiesRemaining ≥ 0`；步末 `Support.PendingCalls` 为空。
7. 电网：`Powered ⇒ Operational`；每个 `Powered` 节点可从某个 `Operational` 的电源 / 场外供电节点经 `Operational` 节点到达（重算结果自洽）；`Collapsed` 与 3.6.3 的定义一致。
8. `ScoringState`：`ThreatsIntercepted ≤` 本夜 `InterceptResolved(Hit)` 事件数（相等）；`InterceptsOverUrban ≤ ThreatsIntercepted`；`TotalShotCostMusd ≥ 0`；`TotalPotentialLossMusd ≥ 0`。
9. 每个 `SupportAsset`：`State == Active ⇒ ArriveAtSec ≤ TimeSec + Eps`；`RoundsLeft ≥ 0`；`KillsLeft ≥ −1`。
10. `EngagementSystem`、`ScoringSystem` 子流的状态在整夜中不变（0 消耗；`engagement` 子流保留）。
11. 每个 `Threat` 的 `HeldMask` 只含 `HoldReason` 定义的位（`< 1 << 16`）。

---

## 7. 测试用例

> 预期值由 `/Users/xtxsinan/.gemini/antigravity/brain/5a8f59a4-9bf6-4338-93e4-2e1d1a05cb62/scratch/spec03_calc.py` 计算。浮点断言：标“==”的逐位相等；其余容差 `1e-9`（时间、坐标）或 `1e-12`（概率、比例）。

### 7.0 测试约定（`sim.tests/Engagement*`、`Impact*`、`Support*`、`Civil*`、`Scoring*`）

- **TC（约定）**：`conventions = { gameSecToWorldSec: 60, worldStepSec: 1, cellKm: 1, machKmh: 1200 }`。
- **TE（`rules/engagement.json` 夹具）**：`gun { reactionGameSec 0.05, shotIntervalGameSec 0.25, roundsPerBurst 10 }`、`missile { 0.05, 0.25, interceptorSpeedKmh 3240 }`、`rocket { 0.05, 0.25, 3240 }`、`interceptor_drone { 0.05, 0.25, 360 }`；`barrelCooldown { burstsBeforeCooldown 3, cooldownGameSec 0.5 }`；`defaultLaunchers 1`；`maxSalvoSize 4`；`defaultRule { salvoSize 1, shootLookShoot true, ammoReserve 0, priorityMode soonest_intercept, engageIdentifiedDecoys false }`；`fighterRule { 1, true }`。换算后：反应 3.0 s、射击间隔 15.0 s、导弹 900.0 m/s、拦截无人机 100.0 m/s、冷却 30.0 s。
- **TI（`rules/intercept.json` 夹具）**：`decoyUsesColumn: UAV`；`classes: { k: { UAV 0.8, CM 0.7, BM 0.5 }, g: { UAV 0.25, GB 0.05 }, d: { UAV 0.6 }, f: { UAV 0.7, CM 0.7 } }`；修正项取正式数据的值（`trackVague.gunProbMult 0.5`、`trackApproximateCued 1.0`、`noCueSelfSearch 1.5`、`newPositionFirstNight 0.7`、`crewFatigue {3, 0.85}`、`aceCrew 1.15`、`restrictedEngagement 1.3`、`interceptorDroneInFriendlyEw 0.6`、`evasiveTargetVsInterceptorDrone { 0.6, from "2025-09", enemies ["e_uav"] }`）。
- **TD（`rules/damage.json` 夹具）**：正式数据的 5 个 band 与 `splashFalloff`，另加 `unitFootprintCells 0.05`（→ 50 m）、`componentRadarChance 0.5`。
- **TA（`rules/accuracy.json`）**：正式数据（A 0/0+1，B 0–1/+1，C 0–2/+2，D 1–3/+2，`spotterTierBoost 1`）。**TDb**：正式 `debris.json`。**TS**：正式 `support.json`。
- **TCv（`rules/civil.json` 夹具）**：`grid { unitConnectRadiusCells 1, unitCategoriesOnGrid ["sensor","ew"], unpoweredShelterProtectionMult 0.5 }`、`alert { shelterGameSec 2, protectionFrac 0.8, populationStructureTypes ["residential"], freeRaisesPerNight 2, fatiguePerExtraRaise 0.1, minResponsiveness 0.3 }`、`scoring { lossMusdPerDamageLevel 1, platformPotentialLossMusd 10, highThreatDamageLevel 7 }`。
- **武器夹具**：`m1 { kind missile, interceptClass k, rangeKm 10, ceilingKm 5, shotCostMusd 0.4, magazine 2, launchers 1, targets [UAV, CM, BM] }`；`g1 { kind gun, interceptClass g, rangeKm 2, ceilingKm 2, shotCostMusd 0.001, magazine null, magazineRounds 25, targets [UAV, DECOY, GB], barrelCooldown true }`；`d1 { kind interceptor_drone, interceptClass d, rangeKm 20, ceilingKm 3, shotCostMusd 0.003, magazine 3, targets [UAV, DECOY] }`。单位 `uF { mobility vehicle, fireOnMove no, weapons [m1] }`、`uG { mobility vehicle, fireOnMove partial, weapons [g1] }`、`uD { mobility vehicle, fireOnMove no, weapons [d1] }`。
- **敌方夹具**：`e_uav { tag UAV, interceptable true, hp 2, damageLevel 3, splashCells 1, accuracy C, costMusd 0.05 }`、`e_cm { tag CM, hp 5, damageLevel 7, splashCells 2, accuracy A, costMusd 13 }`、`e_bm { tag BM, hp 8, damageLevel 8, splashCells 2, accuracy A, interceptProbMult 0.7 }`、`e_decoy { tag DECOY, hp 1, damageLevel 1, splashCells 0, accuracy D }`、`e_arm { tag SCM, damageLevel 4, splashCells 1, accuracy A, tracksEmittingRadarOnly true }`、`e_sub { tag HBM, interceptable false, hp null, damageLevel 6, splashCells 1, submunitions { count 3, damageLevel 6, splashCells 1 }, accuracy C }`、`e_lancet { tag UAV, damageLevel 2, vehicleDamageMult 3, splashCells 0, accuracy A }`；平台 `p_spot { tag UAV, hp 1, whileAlive { enemyAccuracyTierBoost 1 } }`。
- **替身系统**（经 `SimWorld.CreateForTest` 按 Order 替换）：
  - `ScriptedMover`（Order 2）：每个目标按脚本 `(p0, v, alt)` 在第 `k` 步置 `Pos = p0 + v·k`、`AltM = alt`、`VelMps = v`；脚本可指定“第 `k` 步发出 `ThreatArrived{Pos}`”。
  - `ScriptedTracks`（Order 4）：每步为脚本中的目标维护航迹，字段 `Quality`、`PerceivedTag`、`Cued`、`DecoyIdentified` 由脚本给定。
  - `ScriptedEmission`（Order 6）：每步按脚本写 `FireControlActive`、`EmissionSilentHold`、`EmissionReactionMult`。
  - Order 3、5、11、12 用空替身。
- **桩接口**：`EngagementSystem`、`ExternalSupportSystem` 提供 `internal` 构造函数注入 `IThreatPredictor`（测试用 `LinearPredictor`：`Predict(t, dt) = (t.Pos + t.VelMps·dt, t.AltM, Arrived = 脚本到达步 ≤ now + dt)`）与 `IEwQueries`（测试用 `FixedEwQueries(bool)`）。
- **随机数**：`SimConfig.RandomOverride` 对 `intercept` / `impact` / `support` 子流返回 `ScriptedRandom`（`NextDouble` 序列记为 `D[...]`，`NextUInt32` 序列记为 `U[...]`）；序列多余或不足都使测试失败（用以断言消耗次数）。
- 关卡日期默认 `2022-11-15`；`EndWhenClear = false`；除注明外部署方案中的单位 `DeployState = Deployed`。

### 7.1 解析拦截（`InterceptSolver`，WS01-010）

**T-03-01 迎头目标**
`Solve(origin (0,0), speed 900, range 20000, ceiling 5000, predict = 线性 (10000,0) + (−100,0)·dt，alt 1000，不到达, sampleSec 1)`。
预期：非 null；`TimeSec = 10.055419054594015`（闭式解 10.055419054595014，容差 1e-9）；`Pos = (8994.458094540598, 0)`（容差 1e-6）；`AltM = 1000`。

**T-03-02 横穿目标**
`origin (0,0), speed 1000, range 30000, ceiling 10000`，目标 `(−8000, 6000) + (250, 0)·dt`，alt 2000。
预期：`TimeSec = 8.61303556245775`（闭式 8.613035562458604，容差 1e-9），`Pos.X = −5846.741109385563`（容差 1e-6），`Pos.Y = 6000`。

**T-03-03 追不上 → null**
`speed 200`，目标 `(5000,0) + (300,0)·dt`，alt 500，`range 20000, ceiling 5000` → `null`。

**T-03-04 最早可达点在射程外 → null；进入包络后有解**
- 目标 `(10000,0) + (−100,0)·dt`，alt 1000，`speed 900, range 5000, ceiling 5000` → `null`（`t* ≈ 10.06`，拦截点 x ≈ 8994 > 5000）。
- 同参数，目标起点改为 `(5500, 0)` → `TimeSec = 5.600198804013072`，`Pos.X = 4939.980119598693`（容差 1e-6）。

**T-03-05 目标先落地 / 超射高 → null**
- 目标 `(3000,0) + (−50,0)·dt`，alt 100，脚本 5.0 s 后到达；`speed 100, range 20000, ceiling 5000` → `null`（第 1–5 个采样点不可达，第 6 个采样点 `Arrived`）。
- 目标同 T-03-01 但 alt 6000、`ceiling 5000` → `null`。

**T-03-06 拦截无人机（慢速）**
`speed 100, range 20000, ceiling 3000`：目标 `(5000,0) + (−50,0)·dt`，alt 500 → `TimeSec = 33.582866332942416`，`Pos.X = 3320.8566833528794`；目标 `(1000,0) + (120,0)·dt`（远离、比拦截无人机快）→ `null`。

### 7.2 拦截概率与反应时间（WS01-010）

**T-03-07 基础概率与诱饵列**
`HitProbability`（TI、全部修正不触发、`DamageEfficiencyMult 1`）：武器类 `k` 打真实 `e_uav` → `0.8`；类 `g` 打真实 `e_decoy`（`decoyUsesColumn = UAV`）→ `0.25`；类 `d` 打真实 `e_cm`（无 CM 列）→ `0.0`。

**T-03-08 修正链顺序与乘积**
类 `d`（`UAV 0.6`），武器 `d1`（`InterceptorDrone`），真实目标 `e_uav`，航迹 `Precise`；单位 `NewPositionFirstNight = true`、`CrewConsecutiveNights = 3`、`AceCrew = true`、`DamageEfficiencyMult = 0.8`；`FixedEwQueries(true)`；关卡日期 `2025-09-01`（规避修正生效，`e_uav ∈ enemies`）。
预期：`0.6 × 1.0 × 0.7 × 0.85 × 1.15 × 0.6 × 0.6 × 1.0 × 0.8` 从左到右 = `0.1182384`（==）。关卡日期改为 `2025-08-31` → 规避项为 1.0，结果 `0.197064`（= 上式去掉一个 0.6，容差 1e-12）。

**T-03-09 截断与航迹质量**
- 类 `k`，自定义 `classes.k.UAV = 0.95`，`AceCrew = true` → 原始 `1.0924999999999998`，返回 `1.0`。
- 武器 `g1` 打 `e_uav`，航迹 `Vague` → `0.25 × 0.5 = 0.125`；航迹 `Approximate` 且 `Cued` → `0.25`。
- 武器 `m1` 打 `e_bm`（`interceptProbMult 0.7`）→ `0.5 × 0.7 = 0.5249999999999999`（==）。

**T-03-10 反应时间**
`ReactionSecFor`，武器 `m1`（基准 3.0 s）：
- `EmissionReactionMult 1.0`、`Cued`、非限制 → `3.0`；
- 不 `Cued` → `4.5`；
- `EmissionReactionMult 1.25`、不 `Cued`、`restricted` → `3.0 × 1.25 × 1.5 × 1.3 = 7.3125`（==）。

### 7.3 交战判定与交战规则（WS01-009）

> 本节场景：部署 `uF` 于 `(0,0)`（`FireControlActive = true`、`EmissionReactionMult = 1`），目标脚本 `(10000, 0) + (−100, 0)·k`、alt 1000；航迹 `Precise`、`Cued`，`PerceivedTag` = 真实标签（另有说明除外）。`intercept` 子流 `ScriptedRandom`。

**T-03-11 完整交战时间线（反应 → 发射 → 命中）**
目标 `e_uav`。`D[0.5]`。
- 第 1 步：无 `InterceptorLaunched`；`Weapons[0].TargetTrackId` = 该航迹，`ReadyAtSec = 4.0`。
- 第 2、3 步：不发射。
- 第 4 步：恰好 1 个 `InterceptorLaunched{FireUnitId = uF, LauncherIndex 0, WeaponId "m1", ThreatId, SupportAssetId 0}`；新拦截弹 `InterceptAtSec = 13.657716150276645`（容差 1e-9）、`InterceptPos.X = 8634.228384972335`（容差 1e-6）、`HitProbability = 0.8`；`Launchers[0].RoundsLeft = 1`；`NextShotAtSec = 19.0`。
- 第 5–13 步：无新的发射（射击-观察-射击：目标已被占用）。
- 第 14 步：`InterceptResolved{Hit = true, Probability 0.8, AtSec = 13.657716150276645, InterceptorId = 该拦截弹, FireUnitId = uF, WeaponId "m1"}`；目标被删除；拦截弹被删除；`D` 恰好用尽。

**T-03-12 未命中后再射（射击间隔约束）**
同 T-03-11，`D[0.9, 0.1]`。第 14 步 `Hit = false`；第 15–18 步不发射（`NextShotAtSec = 19`）；第 19 步发射第 2 枚（不重新计反应时间，`TargetTrackId` 未变）；之后 `RoundsLeft = 0` 并在同一步发出 `AmmoDepleted{uF, "m1"}`（全夜仅 1 次）。

**T-03-13 “PAC‑3 只打弹道”标签白名单**
两个目标：`e_cm`（航迹 ID 较小）与 `e_bm`，同轨迹参数（`e_bm` 起点 `(9000,0)`）。`uF` 的 `PerWeapon = [("m1", Rule{ AllowedTags = [BM, HBM] , 其余默认 })]`。
预期：只对 `e_bm` 发射（第 4 步）；对 `e_cm` 的航迹在第 1 步（已在射程内）发出 `EngagementHeld{Reason = TagNotAllowedByRule}`，整夜只 1 次；`e_cm` 的 `HeldMask` 含 `1 << 2`。`D[0.1]`（`e_bm` 被击落）。第 5 步发出 `SetEngagementRule{uF, "m1", 默认规则}` → 第 5 步锁定 `e_cm`（`e_bm` 已被占用），`ReadyAtSec = 8`，受射击间隔约束于第 19 步对 `e_cm` 发射。

**T-03-14 武器不能打的标签不算“有目标”**
武器 `m1`（targets 不含 `GB`），目标标签 `GB`（自定义 `e_gb`）。整夜无发射、无 `EngagementHeld`，`HeldMask == 0`。

**T-03-15 航迹质量门槛**
- `m1` 对 `Approximate` 航迹 → `EngagementHeld{TrackQualityTooLow}`，不发射。
- `uG` 于 `(0,0)`，目标 `e_uav` 起点 `(1900, 0)`、速度 0，航迹 `Vague`：第 1 步选定，`ReadyAtSec = 1 + 3.0 × 1.5 = 5.5`（未 `Cued`）；第 6 步（`now = 6 ≥ 5.5`）发出 `GunFired{Probability = 0.125, RoundsUsed = 10}`，同一步 `InterceptResolved{InterceptorId = null, AtSec = null}`。

**T-03-16 火控未开：静默 vs 火控失效**
`FireControlActive = false`：`EmissionSilentHold = true` → `EngagementHeld{EmissionSilent}`；`EmissionSilentHold = false` → `EngagementHeld{FireControlOff}`。两种情况都不发射。

**T-03-17 弹药保留**
`m1` 改 `magazine 3`；规则 `AmmoReserve = 2, ReserveForTags = [BM]`。目标依次为 `e_uav`（先到）与 `e_bm`（后到，起点 `(14000,0)`）。`D` 全部给 0.9（不命中）。
预期：对 `e_uav` 只发射 1 枚（发射后余弹 2 ≤ 保留 2）；此后对 `e_uav` 发出 `EngagementHeld{AmmoReserve}`；`e_bm` 进入后照常发射直到余弹 0。

**T-03-18 每关限额**
武器 `m1` 加 `perLevelLimit 1`，`CarryIn` 给 `PerLevelUsedBefore = 1` → 整夜不发射，`EngagementHeld{PerLevelLimitReached}`。`PerLevelUsedBefore = 0` → 只发射 1 枚，之后 `PerLevelLimitReached`。

**T-03-19 限定敌方型号**
`m1` 加 `restrictToEnemies ["e_cm"]`。目标 `e_uav`（精确航迹）→ 不发射、无 `EngagementHeld`；目标 `e_cm` 航迹 `Approximate` → 不发射；`Precise` → 发射。

**T-03-20 多火力单元分配（不重复射击）**
`uF`（ID 小）在 `(0,0)`，第二个 `uF'` 在 `(2000,0)`，一个目标 `e_uav`。`D[0.9, …]`。
- 第 1 步两者都锁定，`ReadyAtSec = 4`。
- 第 4 步：ID 小者发射；ID 大者处理时该目标已被占用（`Covered`）→ 无合格目标 → `TargetTrackId = 0`，不标记。
- 第 14 步该拦截弹未命中。第 15 步：ID 小者仍锁定该目标但 `NextShotAtSec = 19` 未到；ID 大者重新锁定，`ReadyAtSec = 18`。
- 第 18 步：ID 大者发射（拦截点 x = 7571.096255672538，`InterceptAtSec = 18 + 6.289037443274623`）。第 19 步：ID 小者因目标被占用不发射。

**T-03-21 齐射与“射射”**
规则 `SalvoSize = 2, ShootLookShoot = false`；`m1` 改 `magazine 1, launchers 2`。第 4 步一次发出 2 个 `InterceptorLaunched`（`LauncherIndex` 依次为 0、1），二者 `InterceptAtSec` 相同；`D[0.5]`：第 14 步第一枚（ID 小）命中，第二枚 `InterceptorExpired{TargetGone}`（只消耗 1 个 `NextDouble`）。

**T-03-22 目标排序**
`uF`、规则 `TagPriority = [CM]`、`PriorityMode = Nearest`。三个静止目标（alt 1000）：A `e_uav` 于 `(6000,0)`，B `e_cm` 于 `(9000,0)`，C `e_uav` 于 `(5000,0)`。第 1 步锁定 B（标签优先）；`D[0.1]`：B 被击落后的下一步锁定 C（同为非优先标签，距离更近）。改为 `TagPriority = null, PriorityMode = SoonestIntercept` → 第 1 步锁定 C（拦截时刻最早）。

**T-03-23 粘滞目标**
规则 `TagPriority = [CM]`。第 1 步只有 A（`e_uav`，`(6000,0)` 静止）→ 锁定 A，`ReadyAtSec = 4`；第 2 步出现 D（`e_cm`，`(7000,0)` 静止，按标签优先级更优）→ 仍保持 A，`ReadyAtSec` 仍为 4；第 4 步对 A 发射。

### 7.4 身管武器、行进间射击、约束区（WS01-009）

**T-03-24 身管耗弹与换枪管**
`uG` 于 `(0,0)`，`g1`（`magazineRounds 25, roundsPerBurst 10, barrelCooldown true`），目标 `e_uav` 起点 `(1500,0)` 静止，航迹 `Precise`、`Cued`；`D` 全部 0.99（不命中）。
预期：射击发生在第 4、19、34 步（间隔 15 s），`RoundsUsed` 依次 `10, 10, 5`；第 34 步后 `AmmoDepleted`。另一组 `magazineRounds = null`：射击在第 4、19、34 步；第 34 步后 `BurstsSinceCooldown` 归 0、`CooldownUntilSec = 64.0`；第 35–63 步 `HeldMask` 含 `BarrelCooling` 且不射击；第 64 步恢复射击。

**T-03-25 行进间射击**
`DeployState = Moving`：`uG`（`partial`，身管）照常射击；`uF`（`no`）不射击、不发 `EngagementHeld`、`TargetTrackId = 0`。`DeployState = Packing` 的 `uG` 不射击。

**T-03-26 禁止交战区与限制交战区**
`layers.restrictedZones = [{ id z1, polygonM [[8000,-1000],[9500,-1000],[9500,1000],[8000,1000]], rule no_engagement }]`，T-03-11 场景：第 1–11 步的最早可达拦截点 x 都在 `[8000, 9500]` 内 → 不锁定、不发射，第 1 步发出 `EngagementHeld{NoEngagementZone}`（整夜 1 次）；第 12 步拦截点 x = 7913.7068704443445 离开 z1 → 锁定，`ReadyAtSec = 15`；第 15 步发射，`InterceptPos.X = 7643.486237439419`，`InterceptAtSec = 23.565137625605814`（容差 1e-9）。
把 `rule` 改为 `restricted_engagement`：航迹 `Precise` → 反应 `3.0 × 1.3 = 3.9000000000000004`，`ReadyAtSec = 4.9`（容差 1e-12），第 5 步发射；`uG` 近距场景（T-03-15 第二条，但航迹 `Approximate`，目标在限制区内）→ `EngagementHeld{NotConfirmedHostile}`。

**T-03-27 战斗机专区**
在 T-03-11 场景中预置一个 `Active` 的 `fighter_area_patrol` 支援实体（`Pos (8000,0)`, `RadiusM 5000`）：
- `Exclusive = false` → 视为限制交战，`ReadyAtSec = 1 + 3.9000000000000004`，第 5 步发射。
- 第 1 步阶段 0 发出 `SetFighterZone{该实体, Exclusive = true}` → 整夜不发射，`EngagementHeld{FighterExclusiveZone}`（只要拦截点在半径内）。

### 7.5 拦截判定（WS01-010）

**T-03-28 结算顺序：拦截弹先于身管**
同一步有 1 枚到点拦截弹（目标 X）与 1 次 `GunFired`（同一目标 X）。`D[0.1]`：拦截弹命中；身管射击不掷骰、不发 `InterceptResolved`（`D` 用尽即证明）。`D[0.9, 0.1]`：拦截弹未命中，身管命中；两个 `InterceptResolved` 按此顺序。

**T-03-29 同一步多枚拦截弹按时刻排序**
两枚拦截弹 `I1(ID 小, InterceptAtSec 9.7)`、`I2(ID 大, InterceptAtSec 9.2)` 指向不同目标，第 10 步结算：事件顺序 `I2` 再 `I1`；`D[0.2, 0.3]` 分别用于 `I2`、`I1`。

**T-03-30 显示位置插值**
拦截弹 `OriginPos (0,0)`、`LaunchAtSec 4`、`InterceptAtSec 14`、`InterceptPos (9000,0)`、`InterceptAltM 1000`：第 9 步后 `Pos = (4500, 0)`、`AltM = 500`。

### 7.6 外部支援（WS01-022）

> 关卡 `number 10`、`fighterMode offmap_call`、`fighterSortiesPerNight 1`；指挥点替身 `CanSpend` 恒 true 并记录 `Spend/Refund` 调用。支援数据为正式 `support.json` 与 `fighters.json`（只读结构；测试断言用到的数值在此列出：区域巡逻延迟 8 / 3 gs、持续 20 gs、2 指挥点；`fighter_aam` 射程 80 km、携弹 4）。

**T-03-31 呼叫校验**
| 命令 | 预期 |
|---|---|
| `CallSupport{"nope", (1000,1000)}` | `InvalidArgument` |
| `CallSupport{"neighbor_fire_teams", (1000,1000)}` | `NotAvailable` |
| `CallSupport{"fighter_apkws_hunter", (1000,1000)}`（首次可用第 15 关） | `NotAvailable` |
| `CallSupport{"fighter_area_patrol", null}` | `InvalidArgument` |
| `fighterMode none` 时呼叫区域巡逻 | `NotAvailable` |
| `fighterMode onmap_airbase` 且关卡无 `airbase_runway` 保护目标 | `AirbaseUnavailable` |
| 目标点在 `frontline_risk` 区内 | `InRiskZone` |
| 同一步两条区域巡逻呼叫（额度 1） | 第 1 条接受，第 2 条 `NoSortiesLeft` |
| `CanSpend` 返回 false | `NoCommandPoints` |

**T-03-32 大空袭夜拒绝**
`waves.json` 本夜 `bigRaid: true`；第 1 步呼叫区域巡逻。`support` 子流 `D[0.3]`（< 0.45）→ 第 1 步 `SupportRefused{"fighter_area_patrol", BigRaidDiverted}`；`SortiesRemaining` 回到 1；`Refund(2)` 被调用 1 次；无 `SupportAsset`。`D[0.6]` → `SupportRequested`；`bigRaid` 缺省时不消耗随机数（`D[]` 为空也通过）。

**T-03-33 延迟、到位、持续**
第 1 步呼叫区域巡逻（场外）→ `ArriveAtSec = 1 + 480 = 481`；第 481 步 `SupportArrived`，`EndAtSec = 1681`；第 1681 步 `SupportEnded{Reason = Duration}`。`fighterMode onmap_airbase`（关卡有 `airbase_runway`，`Hp > 0`）→ 第 181 步到位。

**T-03-34 战斗机交战与架次击落上限**
自定义支援 `s_hunt { effect uav_hunt, fighterRef fighter, fighterWeaponRef fw, targets [UAV], killsPerSortie 2, delay { kind instant }, duration { kind game_sec, gameSec 20 }, cost { commandPoints 1 } }`，战斗机武器 `fw { kind rocket, interceptClass f, rangeKm 5, shotCostMusd 0.025, loadout 14, targets [UAV] }`，`fighter.ceilingKm 15`。呼叫点 `(0,0)`；三个静止 `e_uav` 位于 `(1000,0)`、`(2000,0)`、`(3000,0)`，alt 500，航迹 `Approximate`。`intercept` 子流 `D[0.1, 0.1]`。
预期：第 1 步到位（`instant`）并锁定 `(1000,0)` 的目标，`ReadyAtSec = 4`；第 4 步发射第 1 发（`FireUnitId 0`、`SupportAssetId` = 实体，`InterceptAtSec = 4 + 1.2422599874987732`）；第 6 步命中，`KillsLeft = 1`；第 6 步系统 9 锁定 `(2000,0)`，`ReadyAtSec = 9`，但 `NextShotAtSec = 19`；第 19 步发射（`InterceptAtSec = 19 + 2.2906142364531448`）；第 22 步命中 → `KillsLeft = 0`，**同一步**系统 9 发出 `SupportEnded{KillsReached}`；`NightResult.Support.Kills = 2`；`(3000,0)` 的目标未被射击。

### 7.7 落地伤害（WS01-011、017）

**T-03-35 落点偏移**
`Offset(aim (5000,5000), tier C)`，`EwAffected = false`，`D[0.5, 0.25]` → `d = 1000`、方位 `π/2` → `P = (6000, 5000)`（容差 1e-9）。`EwAffected = true`，`D[0.5, 0.5]` → `d = 3000`、方位 `π` → `P = (5000, 2000)`（容差 1e-9）。tier D、`D[0.0, 0.0]` → `P = (5000, 6000)`。tier A、`D[0.7, 0.3]` → `P == aim`，仍消耗 2 个值。

**T-03-36 溅射衰减与取整**
`LevelRaw(7, r, 2000)` / `RoundLevel`：

| r | 原始 | 等级 |
|---|---|---|
| 0 | 7.0 | 7 |
| 500 | 5.7749999999999995 | 6 |
| 1000 | 4.55 | 5 |
| 1500 | 3.3250000000000006 | 3 |
| 2000 | 2.1000000000000005 | 2 |
| 2000.5 | 0.0 | 0 |

`LevelRaw(2, 0, 0) = 2`；`LevelRaw(2, 1e-6, 0) = 0`。

**T-03-37 保护目标效果**
保护目标 `s_res { type residential, radiusM 100, hp 10, weight 1 }`、`s_pp { type power_plant, radiusM 100, hp 20, weight 5, gridNode n1 }`。
- 等级 3 落在 `s_res` 上，`impact` 子流 `U[0]`：`RollInclusive(1,1)` → 损失 1，`StructureDamaged{HpBefore 10, HpAfter 9, Cause Impact}`。
- 等级 7（band 7–8，`destroyed 2–3`），`U[1]` → `NextInt(2,4)`：`range 2, threshold 0` → `2 + 1 = 3`，`Hp 9 → 6`。
- 等级 1（`destroyed 0–0`），`U[5]` → 损失 0，**不发事件**但消耗 1 个 `NextUInt32`。
- 等级 9（`block`）→ `Hp → 0`，`StructureDamaged` + `StructureDestroyed`，不消耗随机数。
- `s_pp`：等级 7 → `ceil(0.35 × 20 − 1e-9) = 7`，`Hp 20 → 13`，`Grid.Dirty = true`；等级 3 → `2`；等级 1 → 0（无事件、无随机数）。

**T-03-38 我方单位效果**
单位 `uF`（`HasFireControlRadar = true`，`launchers 2`）在 `(0,0)`。
- 等级 2 → `DamageEfficiencyMult = 0.8`、`LightDamaged`、`PlayerUnitDamaged{LightDamage}`；再次等级 1 → 仍 0.8（不叠乘）。
- 等级 4（`now = 100`）→ `SuspendedUntilSec = 1900`（`100 + 30 × 60`）。
- 等级 5，`D[0.3]` → `RadarDestroyed = true`、`Component = Radar`；再次等级 5，`D[0.3]` → 雷达已毁，改毁发射架：`Launchers.Count 2 → 1`、`Component = Launcher`；再次等级 5、`D[0.9]` → 最后一个发射架被毁 → `PlayerUnitDestroyed`。
- 探测单位受等级 5 → 直接 `PlayerUnitDestroyed`，不消耗随机数。
- 等级 7 → 火力单元 `PlayerUnitDestroyed{SourceThreatId}`，从存储删除。

**T-03-39 对车辆加成与受击半径**
`e_lancet`（等级 2、溅射 0、加成 3）落在 `(30, 0)`：车载 `uF` 于 `(0,0)`（距离 30 ≤ 受击半径 50）→ 原始 `2 × 3 = 6` → 等级 6 → 毁部件；落在 `(60, 0)` → `r = 10 > 0` → 无效果。`e_uav`（等级 3、溅射 1000）落在 `(750,0)`（`r = 700`）：车载单位 `RoundLevel(1.53 × 1) = 2`；`vehicleDamageMult` 缺省 → 不加成。

**T-03-40 有效精度档**
`e_uav`（C）：无侦察平台、`EwTierDrop 0` → C；地图上有存活 `p_spot` → B；`p_spot` + `EwTierDrop 2` → D；`e_cm`（A）+ 侦察平台 → A（截断）。`EwImmune` 的自定义弹药 + `EwTierDrop 2` → 不降档。

**T-03-41 反辐射导弹**
`e_arm` 到达 `(100,100)`，`ArmHitProbMult 0.2`：`D[0.5]` → `ThreatImpacted{Outcome ArmMissed, DamageLevel 0, LeakReason null}`，无伤害事件，目标删除，`ThreatsImpacted` 不增加；`D[0.1, 0.0, 0.0]` → 命中，A 档偏移 0 → 正常落地（`D` 的后两个值用于偏移）。

**T-03-42 子弹头**
`e_sub` 到达 `(5000,5000)`，`D` 共 6 个值（每个子弹头 2 个）：`[0.5,0.25, 0.5,0.5, 0.0,0.0]` → 3 个 `ThreatImpacted{Outcome Submunition, SubIndex 0/1/2, Pos (6000,5000) / (5000,4000) / (5000,5000), DamageLevel 6}`；只有 `SubIndex 0` 带 `LeakReason`。

**T-03-43 碎片**
城区多边形 `[[0,0],[4000,0],[4000,4000],[0,4000]]`；保护目标 `s_res` 位于 `(2000,2000)`、`radiusM 100`、`hp 10`。
- 拦截点 `(2050, 2000)`（城区内、在 `s_res` 半径内）命中 `e_cm`（等级 7）→ 碎片等级 `RoundLevel(7 × 0.3 = 2.1) = 2`，band 1–2 `destroyed 0–0`（消耗 `U[0]`，损失 0）→ 无 `StructureDamaged`；`DebrisFell{Pos (2050,2000), StructureId 0, DamageLevel 2}`；`InterceptResolved.OverUrban = true`。
- 等级换算表：`RoundLevel(L × 0.3)` 对 `L = 1…10` 为 `0,1,1,1,2,2,2,2,3,3`（`3 × 0.3 = 0.8999999999999999 → 1`，`5 × 0.3 = 1.5 → 2`）。
- 等级 1（`e_decoy`）→ 碎片等级 0：不发 `DebrisFell`。
- 拦截点 `(5000, 2000)`（城外）→ `ruralFrac = 0`：无碎片，`OverUrban = false`。

### 7.8 电网（WS01-018）

**T-03-44 断电传播（正式 test_01 拓扑的手写副本）**
节点 `node_tpp(source)`、`node_sub(substation)`、`node_water`、`node_city`、`node_radar_site`（consumer），连线同 `test_01/map/grid.json`；保护目标 `tpp(power_plant, hp 20, gridNode node_tpp)`、`sub(substation, hp 10, gridNode node_sub)`、`water(water_plant, hp 12, gridNode node_water)`。
- 开局：5 个节点全部 `Powered`，无 `GridPowerChanged` 事件，`Collapsed = false`。
- `sub` 被打到 `Hp 0`：同一步末事件 `GridPowerChanged` × 4，按节点 ID 升序：`node_sub, node_water, node_city, node_radar_site` 全为 `false`；`water.Powered = false`；`Collapsed = true`、`CollapsedAtSec = now`。
- 只把 `water` 打坏（非电网设施）→ 无电网事件。

**T-03-45 无向连线与场外供电**
节点 `a(source)`、`b(substation)`、`c(consumer, offMapSupply true)`，连线 `a→b`、`c→b`（方向与供电方向相反）。`a` 的电厂被毁：`b` 仍由 `c` 经无向连线供电（`Powered = true`）；`a` 断电。

**T-03-46 单位接入电网**
探测单位 `r1` 位于 `(6500,16000)`（距 `node_radar_site` 500 m ≤ 1000）→ `GridNodeId = node_radar_site`；火力单元同位置 → `GridNodeId = 0`（类别不在 `unitCategoriesOnGrid`）；探测单位位于 `(6000,17500)`（1500 m）→ 0。两个节点等距 → 取 ID 小者。`sub` 被毁后 `r1.Powered = false`。

### 7.9 空袭警报（WS01-024）

**T-03-47 拉响 / 解除与疲劳**
连续 10 次“拉响 → 解除”（每次间隔 1 步）：每次拉响后 `Responsiveness` 依次为 `1.0, 1.0, 0.9, 0.8, 0.7000000000000001, 0.6000000000000001, 0.5000000000000001, 0.40000000000000013, 0.30000000000000016, 0.3`（==；第 10 次被下限截断）。`SetAirRaidAlert{On = true}` 在已拉响时 → `InvalidState`。解除时 `ShelteredFrac` 立即为 0。

**T-03-48 避难进度与损失折减**
第 1 步拉响（`Responsiveness 1.0`，`ShelterSec 120`）。第 60 步 `ScoringSystem` 后 `ShelteredFrac = 0.5000000000000007`；第 120 步后 `0.9999999999999989`；第 121 步后 `1.0`。第 61 步（读第 60 步的值）落地使住宅 `s_res` 损失 2 HP：`Hp` 减 2，`LossHp` 增加 `2 × (1 − 0.5000000000000007 × 0.8 × 1.0) = 1.1999999999999988`（容差 1e-12）。两个避难所中一个断电 → `ShelterQuality = 0.75`；完全避难时住宅损失 3 HP → `LossHp += 1.1999999999999997`。非住宅类型不折减。`AlertActiveSec` 每步 +1；工厂 `PausedSec` 在警报期间每步 +1。

### 7.10 评分与 `NightResult`（WS01-023）

**T-03-49 加权损失与失败条件**
保护目标 `tpp(weight 5, hp 20)`、`sub(3, 10)`、`water(2, 12)`；`LossHp = 10, 10, 0` → `WeightedLossFrac = 0.55`（==）；`defeat = [weighted_damage_at_least 0.5]` → 同一步 `EndRequest(Defeated, DefeatCondition, "weighted_damage_at_least:0.5")`，`NightEnded` 在本步。`LossHp = 9, 10, 0` → `0.525`，同样失败；`LossHp = 0, 10, 0` → `0.3`，不失败。

**T-03-50 失败条件顺序与明细**
`defeat = [grid_collapse, structure_destroyed sub]`，同一步 `sub` 被毁且电网崩溃 → `Detail = "grid_collapse"`。顺序反过来 → `"structure_destroyed:sub"`。

**T-03-51 交换比**
直接向 `ScoringSystem` 投喂事件（替身 Order 7/8 按此顺序发出）：`InterceptorLaunched(m1)`、`InterceptorLaunched(m1)`、`GunFired(g1)` × 3，其后 `InterceptResolved{Hit = true}` 指向第一枚 `m1` 的目标 `e_uav`（`TargetStructureId` = `tpp`，weight 5），`g1` 三次均 `Hit = false`。
预期：`TotalPotentialLossMusd = 3 × 1 × 5 = 15.0`；`TotalShotCostMusd = 0.803`（逐次累加：`0.4 + 0.4 + 0.001 + 0.001 + 0.001`，==）；`ExchangeRatio = 18.679950186799502`；`ByWeapon`：`g1 {Shots 3, Kills 0, Cost 0.003, Loss 0, Ratio 0.0}`、`m1 {Shots 2, Kills 1, Cost 0.8, Loss 15.0, Ratio 18.75}`（序数顺序 `g1` 在前）。命中真实诱饵 → 潜在损失 0；射向诱饵的发射计入 `DecoyShots` / `DecoyCostMusd`。一次都没开火 → `ExchangeRatio == null`。

**T-03-52 突防原因**
逐条构造落地目标的状态并断言 `ThreatImpacted.LeakReason` / `LeakMask`：

| `MaxTrackQuality` | `ShotsTaken` | `HeldMask` 含 | `DecoyDrained` | `EwCovered` | 预期原因 | 预期掩码含 |
|---|---|---|---|---|---|---|
| −1 | 0 | — | false | true | `Undetected` | `Undetected`、`EwIneffective` |
| 2 | 0 | `AmmoDepleted` | true | false | `DecoyDrain` | `DecoyDrain`、`AmmoDepleted` |
| 2 | 0 | `AmmoDepleted` | false | false | `AmmoDepleted` | `AmmoDepleted` |
| 2 | 0 | `EmissionSilent` | false | false | `EmissionSilent` | |
| 2 | 1 | `ChannelBusy` | false | false | `InterceptMissed` | `InterceptMissed`、`Saturated` |
| 1 | 0 | `TagNotAllowedByRule` | false | false | `HeldByRule` | |
| 0 | 0 | `TrackQualityTooLow` | false | false | `PoorTrack` | |
| 2 | 0 | `Suspended` | false | false | `DefenseDamaged` | |
| 2 | 0 | — | false | true | `EwIneffective` | 只有 `EwIneffective` |
| 2 | 0 | — | false | false | `OutOfCoverage` | 只有 `OutOfCoverage` |

`e_cm`（等级 7）以 `HeldByRule` 突防 → `HighThreatLeaksWithReserve = 1`；`e_uav`（等级 3）同样情况 → 0。`LeakReasonCounts` 含全部 11 项。

**T-03-53 城区上空拦截比例**
4 次命中，其中 3 次 `OverUrban` → `UrbanInterceptRatio = 0.75`、`InterceptsOverUrban = 3`；0 次命中 → `null`；`scoreUrbanInterceptRatio = false` → `null`。

**T-03-54 `NightResult` 字段齐全与序列化往返**
迷你关卡（T-03-11 的场景加 `water` 保护目标与 1 个探测单位）跑满 30 步。`Result` 中 `Losses`、`Ammo`、`Exchange`、`Debris`、`Exposure`、`Civil`、`Support` 均非 null；`Ammo.Weapons` 含 `m1`、`RoundsRemaining = 1`；`Exposure.Units` 按单位 ID 升序含 2 项。用 3.8.6 的 `JsonSerializerOptions` 序列化 → 反序列化 → 再序列化：两次 JSON 字符串逐字节相等；反序列化对象与原对象逐字段相等（集合按序）。JSON 中不出现 `NaN`、`Infinity`；`"exchangeRatio"` 在零发射夜为 `null`；枚举为字符串（如 `"reason":"OutOfCoverage"`）；`Vec2` 为 `{"x":…,"y":…}`。

**T-03-55 确定性**
T-03-54 的世界跑两次（相同种子与命令）：每步 `ComputeStateHash()` 相等；`engagement`、`scoring` 子流状态 30 步后与初始相同（0 消耗）。

---

## 8. 待决问题

### 8.1 设计 / 数值待决（每条给出建议默认值；本规格正文按默认值写）

| # | 问题 | 背景 | 建议默认值（理由） |
|---|---|---|---|
| Q-E1 | 拦截弹速度 | 数据中没有拦截弹速度，解析拦截必须有 | 新字段：`rules/engagement.json` 按武器类别给默认（导弹 3600 km/h、火箭 2400 km/h、拦截无人机 300 km/h），武器可用可选字段 `interceptorSpeedKmh` 覆盖。游戏化统一值，不整理真实型号参数（GDD 17.5） |
| Q-E2 | 基准反应时间、射击间隔 | 数值表只有“反应时间 +X%”的倍率，没有基准值；没有射击间隔就无法限制发射速率 | 新字段按武器类别：反应 导弹 / 火箭 0.2、高炮 0.1、拦截无人机 0.5 游戏秒；射击间隔 导弹 / 火箭 0.25、高炮 0.5、拦截无人机 0.5 游戏秒（Shahed 穿越 5 km 高炮圈约 1.6 游戏秒 ≈ 3 次射击、累计约 58% 击落，量级合理）。WS09 批量模拟后调整 |
| Q-E3 | 夜间是否从弹药池装填 / 发射架装填时间 | 数据只有每架弹仓与关卡配额 | 夜间不装填；配额剩余留给 05（白天补给窗口）。若需要，增加 `reloadGameSec` |
| Q-E4 | `launchers: null`（“由关卡配置”）时的发射架数 | `level.json` 没有对应字段（Patriot、S‑300 为 null） | `engagement.defaultLaunchers = 1`；建议后续在 `level.json` 增加 `launcherOverrides[{unit, weapon, launchers}]` |
| Q-E5 | “首发反应时间 +50%”的“首发”含义 | 可理解为每夜第一发或每个目标第一发 | 每个新锁定目标的第一次发射（火控需对每个新目标自行搜索） |
| Q-E6 | 身管武器每次射击耗弹（`magazineRounds`） | Schema 注明“由 WS01-009 决定” | `roundsPerBurst = 34`（Gepard 680 发 ≈ 20 次射击） |
| Q-E7 | “限制交战：只打已确认的敌方目标”中“已确认”的定义 | 模拟中没有民航 / 友机，所有空中目标都是敌方 | 航迹质量 `Precise`。地图“限制交战区”与“战斗机所在区域”用同一套效果 |
| Q-E8 | 换枪管冷却参数 | 数据只有 `barrelCooldown: true` | 连续 5 次射击后冷却 1 游戏秒 |
| Q-E9 | 多个火力单元的分配顺序 | 需要确定性；按单位 ID 会让“先部署的单位”优先 | 按火力单元 ID 升序贪心分配（简单、可预测）。备选：便宜武器优先（更贴合交换比压力），需要人决定 |
| Q-E10 | `fireOnMove: partial` 的含义 | 数值表只写“部分” | 行进间只有身管武器可射击 |
| Q-E11 | 无火控雷达的导弹（单兵防空、Strela、RBS 70 等）的航迹门槛 | 数值表：导弹需精确航迹，精确航迹来自火控雷达 | 仍要求 `Precise`；由 02 把这类单位自身的光学 / 红外瞄准视为短程“精确”来源（见 8.3 B2） |
| Q-I1 | 拦截概率修正项的叠加方式 | 数值表只列各项倍率 | 全部相乘，固定顺序（3.3.2），最后一次截断到 [0, 1] |
| Q-I2 | 受损单位（轻伤 −20% 效能）是否降低拦截概率 | 数值表“效能”含义未定 | 是：作为修正链第 8 项 `DamageEfficiencyMult` |
| Q-I3 | 游戏 HP 与拦截判定的关系 | 数值表给了 HP，但 3.3 是“单发拦截概率” | 命中即击毁，HP 不参与拦截（HP 只记录）。备选：身管 / 碎片按 HP 扣减、导弹直接击毁——需要人决定 |
| Q-I4 | 诱饵（`DECOY`）被打掉是否有潜在损失 | GDD：“打掉诱饵会浪费弹药” | 潜在损失 = 0（交换比惩罚打诱饵） |
| Q-I5 | 解析拦截的近似（1 秒采样、AGL 高度、直线等速、发射后不修正） | WBS 01.A 只要求“解析计算拦截时刻” | 按 3.1；短于 1 秒的可达窗口会被漏掉，地形高差忽略 |
| Q-I6 | 发射单位被毁后，飞行中的拦截弹是否失效 | 半主动制导需要照射雷达 | 照常结算（概率在发射时已定）。备选：雷达类单位被毁时其拦截弹 `InterceptorExpired` |
| Q-D1 | 溅射衰减作用于哪个距离 | “中心 100% → 边缘 30%” | 落点到保护目标**边缘**（扣除 `radiusM`）/ 到单位扣除受击半径后的距离 |
| Q-D2 | 衰减后的伤害等级如何取整 | 等级是整数档 | 四舍五入（`AwayFromZero`）。向下取整会让碎片几乎永远无效（Shahed 碎片 0.9 → 0） |
| Q-D3 | 民用建筑“损毁 N 栋”与保护目标 HP 的关系；“区块损毁”的含义 | 保护目标有 HP（如电厂 20） | 每栋 = 1 HP；区块损毁 = 该保护目标 HP 归零 |
| Q-D4 | 伤害 9–10 “波及相邻格” | 溅射已表达范围伤害 | 不追加额外效果 |
| Q-D5 | “摧毁雷达或发射车其一”如何选 | 未给概率 | 新字段 `componentRadarChance = 0.5`；没有雷达或雷达已毁 → 毁发射架；最后一个发射架被毁 = 单位被毁 |
| Q-D6 | Orlan 升档是全图生效还是只对其附近目标 | 数值表 2.3“存活期间敌方精度档 +1”；`accuracy._source`“标记目标时” | 全图生效，升档数取 `accuracy.spotterTierBoost`（`platforms[].whileAlive.enemyAccuracyTierBoost` 只作“是侦察平台”的标记）。两处数值重复，建议删去其一 |
| Q-D7 | 对车辆加成适用哪些单位 | “对车辆加成 ×3” | `mobility ∈ {vehicle, towed}` 的火力单元；探测 / 电子战 / 欺骗单位数据中没有机动性字段，不加成 |
| Q-D8 | 伤害等级表对非防空单位（探测、电子战、欺骗）的效果 | 3.2 只有“对防空单位” | 同表；“摧毁部件”对它们视为摧毁 |
| Q-D9 | 轻伤是否叠加 | 多次轻伤 | 不叠加，取最小倍率 |
| Q-D10 | 反辐射导弹“未命中”的结果 | 数值表只给命中率修正 | 失锁坠毁：无伤害、不算突防 |
| Q-D11 | 我方单位受击半径 | 溅射 0 的弹药（Lancet、FPV）需要一个可命中的面积 | 新字段 `unitFootprintCells = 0.05`（50 m） |
| Q-G1 | 电网连线是否有方向 | `links` 写的是 from / to | 视为无向（多电源网状拓扑更自然）；电力只经“可用”节点传递 |
| Q-G2 | 断电对探测 / 电子战单位的效果大小 | GDD 8.5 “雷达断电后效能下降” | 由 02 规定；建议探测距离 ×0.5、电子战停机 |
| Q-G3 | 哪些我方单位接入电网、如何接入 | 部署数据没有电网字段 | 探测、电子战单位接入 1 格内最近的 consumer / substation 节点；火力单元与欺骗单位不接入（自带电源） |
| Q-G4 | 电网设施的“−10% / −35%”怎么体现 | 3.2“对电网设施”列 | 按比例扣 HP（向上取整），HP 归零 = 节点失效 |
| Q-G5 | `grid_collapse` 的定义 | 关卡条件只写“电网崩溃” | 全部 consumer 节点断电。备选：断电 consumer 比例 ≥ 阈值（新增 `level` 条件字段 `fraction`） |
| Q-A1 | 警报的避难效果大小、避难进入时间、疲劳规则 | GDD 8.6 只有定性描述 | `protectionFrac 0.8`、`shelterGameSec 2`、每夜前 2 次免费、之后每次 −0.1、下限 0.3；只影响住宅类保护目标的“计入损失 HP” |
| Q-A2 | 警报疲劳是否跨夜恢复 | — | 本文件只带出 `ResponsivenessEnd`；跨夜恢复由 05 决定 |
| Q-A3 | 避难所断电的影响 | WS01-018 列出“避难所” | 断电避难所按 0.5 计入 `ShelterQuality` |
| Q-S1 | 1 次呼叫消耗几个“架次” | 数值表“每夜额度 0–4 架次” | 1 次呼叫 = 1 架次 |
| Q-S2 | `offmap_auto`（场外 AI 自动）与 `onmap_support_facility` 的夜间行为 | GDD 8.9 | 夜间都按“场外呼叫”处理；自动出动的规则另行设计 |
| Q-S3 | “定向拦截：至弹药耗尽”没有目标时何时结束 | — | 持续到夜晚结束 |
| Q-S4 | 战斗机 `takeoffGameSec` / `rearmGameSec` / 巡逻速度 | 与 `support.delay` 重复 | 本文件只用 `support.delay`；战斗机到位后定点巡逻，不模拟航线与返航补给 |
| Q-S5 | 国家级导航欺骗的作用半径 | 数据只有“某区域”与 `affectsSameAsEwUnit` | 取所引用电子战单位（`area_nav_jammer`）的 `radiusKm`；建议给 `support` 增加 `radiusKm` |
| Q-S6 | “限制交战”反应时间倍率在 `intercept.json` 与 `support.json` 中重复 | 两处都是 1.3 | 统一用 `intercept.modifiers.restrictedEngagement`，加载时校验相等；建议删去 `support.airspace.restrictedEngagement.reactionTimeMult` |
| Q-S7 | 空域协调（划设战斗机专区）是否耗指挥点 | GDD 5.2 未列 | 不耗（由 04 最终决定） |
| Q-S8 | 大空袭夜如何标记；被拒绝时是否退还指挥点 | 数据中没有“大空袭”标记 | 新增 `waves.json nights[].bigRaid`；拒绝时退还架次与指挥点 |
| Q-S9 | 邻近扇区覆盖（`sector_coverage`）的夜内效果 | “邻近 Patriot / SAMP/T 扇区覆盖地图边缘” | 本版不实现；建议由 05 在部署方案中加入位于地图边缘外的虚拟火力单元（需要关卡给出位置） |
| Q-X1 | 交换比“潜在损失”的公式 | GDD 只给定义 | `伤害等级 × lossMusdPerDamageLevel(1 M$) × 目标保护目标权重`（不以保护目标为目标时权重 1）；平台按 `platformPotentialLossMusd`（10 M$）；诱饵 0。分母为全部发射的价格。备选：用敌方单价 `costMusd`（数据现成，但滑翔炸弹为 null，且无法体现“目标价值”） |
| Q-X2 | “让高威胁目标突防但昂贵弹药仍有剩余”如何计 | GDD 9.3 第 3 条 | `HighThreatLeaksWithReserve`：伤害等级 ≥ 7 且突防掩码含 `HeldByRule` 的次数；扣分由 05 |
| Q-X3 | 突防原因不止 GDD 列出的 5 种 | 例如“打了没打中”“交战规则不允许” | 增加 6 种补充原因（3.8.4），优先级如表 |
| Q-X4 | 加权损失是否跨夜累计 | 多夜关卡的失败条件 | 是：`LossHp` 与 `Hp` 由 `CarryIn` 带入，失败判定用累计值 |

### 8.2 需登记到 00_core

**R-ENT 实体 / 组件字段**

| 表 | 建议 | 字段 |
|---|---|---|
| 00 2.4 `PlayerUnitCommon` | 追加 3 列 | `DamageEfficiencyMult`、`SuspendedUntilSec`、`LightDamaged`（2.1） |
| 00 2.3 `Interceptor` / `SupportAsset` / `Structure` / `GridNode` / `FireUnit` | 细化规格 = 03 | 字段见 2.2、2.5–2.7 |
| `Threat`（01 主表） | 03 追加 4 个字段 | `MaxTrackQuality`、`ShotsTaken`、`HeldMask`、`DecoyDrained`（2.4） |
| 00 2.5 `SimState` 单例 | 新增 `EngagementState` | 2.8；3.7.2 哈希序号建议插在 `SupportState`（序 6）之前，其后顺延；或追加为序 10（只追加，不重排） |
| 00 2.6 `UnitSettings` | 追加属性 | `UnitEngagementSettings? Engagement`（2.3） |
| 00 2.7 `GlobalView` | 追加 | `AlertOn`、`ShelteredFrac`、`Responsiveness`、`SortiesRemaining`、`GridCollapsed`、`WeightedLossFrac` |

**R-DATA 数据与加载**

| 项 | 内容 |
|---|---|
| 新规则文件 | `rules/engagement.json`（`kind: engagement`）、`rules/civil.json`（`kind: civil`）；00 1.1 全局目录表追加第 21、22 位；`rules.schema.json` 的 `kind` 枚举追加；`RulesSet` 追加 `Engagement`、`Civil`；T-00-35 的 `LoadedFiles.Count` 由 29 变为 31 |
| `units/air_defense.json` 武器可选字段 | `reactionGameSec`、`shotIntervalGameSec`、`interceptorSpeedKmh`（Schema 与 `WeaponDef` 追加，`Gun` 不得有 `interceptorSpeedKmh`） |
| `support/fighters.json` 武器必填字段 | `kind`（`missile` / `rocket`）；`FighterWeaponDef.Kind` |
| `rules/damage.json` 新字段 | `unitFootprintCells`、`componentRadarChance` |
| `waves.json` 可选字段 | `nights[].bigRaid`（`bool`） |
| 交叉引用（00 1.2 第 15 条追加） | `support[].fighterRef` ∈ 战斗机 ID（类别 `战斗机`）；`support[].fighterWeaponRef` ∈ 该战斗机武器 ID（类别 `武器`）；`support[].affectsSameAsEwUnit` ∈ 电子战单位 ID（类别 `单位`）；`support[].reinforcementUnit`、`coverageUnits[]` ∈ 防空单位 ID；`fighters[].weapons[].interceptClass` ∈ `intercept.classes` |
| ID 唯一性（00 1.2 第 13 条追加） | 战斗机武器 ID 与防空武器 ID 不得重复（交换比按武器 ID 查价格） |
| 加载校验 | `damage.bands` 覆盖 1–10 且不重叠；`defeat[]` 中出现 `survive_nights` / `survive_game_sec`、`victory[]` 中出现 `structure_destroyed` / `weighted_damage_at_least` / `grid_collapse` → `E_RANGE`；`support.airspace.restrictedEngagement.reactionTimeMult` 与 `intercept.modifiers.restrictedEngagement.reactionTimeMult` 不等 → `E_RANGE` |
| 新 enum（00 1.2 第 8 条规则下的整数值） | `WeaponKind`、`FireOnMove`、`SupportProvider`、`SupportEffect`、`DelayKind`、`DurationKind`、`TrustCost { Small, Large }`、`UnitDamageEffect`、`CivilDamageEffect`、`TargetPriorityMode`（JSON `soonest_intercept` / `nearest`） |

**R-EV 事件字段细化**（00 4.2 总表“关键字段”列按本文件 4.2 更新）

`InterceptorLaunched` +`ThreatId, SupportAssetId`；`GunFired` +`ThreatId, Probability, RoundsUsed`；`InterceptResolved` +`Pos, AltM, OverUrban, WeaponId, FireUnitId, SupportAssetId`；`EngagementHeld` 字段 `FireUnitId, WeaponId, TrackId, ThreatId, Reason`；`ThreatImpacted` +`DefId, AimPos, Tier, Outcome, SubIndex, LeakReason, LeakMask`；`StructureDamaged` +`Cause`；`PlayerUnitDamaged` 字段 `UnitId, DefId, Kind, Effect, Component, SourceThreatId`；`PlayerUnitDestroyed` +`SourceThreatId`；`DebrisFell` +`DamageLevel, SourceThreatId`，`StructureId` 改为 `int`（0 = 无）；`SupportEnded` +`Reason`。

**R-CMD 命令与拒绝原因**

- 命令字段：`SetEngagementRule { int FireUnitId, string? WeaponId, EngagementRule Rule }`；`CallSupport { string SupportDefId, Vec2? TargetPos }`；`SetAirRaidAlert { bool On }`；`SetFighterZone { int SupportAssetId, bool Exclusive }`。
- `SetAirRaidAlert` 的处理者确定为 `ScoringSystem`（00 Q5）。
- 新拒绝原因：`NoSortiesLeft = 300`、`InRiskZone = 301`、`AirbaseUnavailable = 302`。

**R-NR `NightResult`**

- 03 部分的类型全部按 3.8.6；`NightResult` 追加 `CivilSummary Civil`、`SupportSummary Support` 两个属性（00 3.5 只列了 5 个）。
- 序列化选项（camelCase、枚举字符串、无 NaN）建议写入 00 3.5，供 05 / 工具统一使用。

**R-CI `CarryIn`（字段由 05 定义，本文件读取）**

保护目标 `Hp` 与 `LossHp`；我方单位 `DamageEfficiencyMult`、`LightDamaged`、`Exposure`；火力单元 `NewPositionFirstNight`、`CrewConsecutiveNights`、`AceCrew`、逐武器逐发射架 `RoundsLeft`、`PerLevelUsedBefore`；`AlertResponsiveness`。

**R-RNG 子流**

不新增子流。`civil` 子流（00 3.1.4 序 15）：本文件的警报规则不使用随机数，保持 0 消耗；宿主为 `ScoringSystem`。`engagement` 子流保留未用。

### 8.3 与其他规格的边界问题

| # | 涉及 | 问题 | 本文件的处理 / 建议 |
|---|---|---|---|
| B1 | 01 | `ThreatPredictor.Predict` 的签名与语义（D1）；`ThreatArrived` 后由谁删除目标（D2） | 本文件假设 01 不删除、03 在系统 10 删除；`Predict` 为纯函数、`Arrived` 标志表示提前到达。需要 01 确认 |
| B2 | 02 | 精确航迹的来源：火力单元自身火控（含无雷达的单兵防空）必须能把航迹提升为 `Precise`（D8） | 若 02 不这样实现，本文件的导弹门槛（`MissilesAllowed`）会让无雷达导弹无法开火 |
| B3 | 02 | `Track.PerceivedTag`（未甄别诱饵显示为 UAV）、`Track.Cued`、`Track.DecoyIdentified`、`FireUnit.FireControlActive / HasFireControlRadar / EmissionReactionMult / EmissionSilentHold`、`EwQueries.FriendlyJammingAt`、`Threat.EwTierDrop / EwAffected / EwCovered / ArmTargetUnitId / ArmHitProbMult` 的命名与写入时机 | 全部假设在系统 6 之前写好；需合并到 02 的状态表 |
| B4 | 02 | 电子战造成的精度变化：02 写“降档数”还是直接改精度档；`ewExtraCells` 与降档是否同时生效（数值表 5.3 也写了待 WS01-015 确认） | 本文件同时支持两种钩子：`EwTierDrop`（降档）与 `EwAffected`（追加 `ewExtraCells`）；由 02 决定写哪一个，避免重复惩罚 |
| B5 | 02 | 暴露度“发射导弹每发 +5” | 02 读取 `InterceptorLaunched` 事件；本文件不改暴露度 |
| B6 | 02 | 国家级导航欺骗的效果 | 本文件只管呼叫流程，02 读取 `SupportAsset`（3.4.5） |
| B7 | 02 | 被暂停（重伤）、断电、雷达被毁的探测 / 电子战 / 火力单元的雷达状态 | 02 读取 `SuspendedUntilSec`、`Powered`、`RadarDestroyed`、`DamageEfficiencyMult` 并自行决定效果（建议：暂停 = 关机；断电 = Q-G2） |
| B8 | 02 / 04 | 反辐射导弹“优先锁定暴露度 ≥ 40 的单位”与“雷达关机命中率” | 选目标与 `ArmHitProbMult` 归 02 / 04；落地掷骰归本文件（3.5.7） |
| B9 | 04 | 指挥点扣除 / 退还接口（D15）；`SetEngagementRule`、`SetAirRaidAlert`、`SetFighterZone`、`CallSupport` 是否耗点、耗几点 | 本文件只在 `CallSupport` 中按 `support.cost.commandPoints` 调用 04 的接口；其余命令是否耗点由 04 决定并在其处理逻辑中调用（命令处理者仍是本文件的系统，需要 04 提供可从其他处理者调用的扣点函数） |
| B10 | 04 | 剧情动作 `set_alert` | 04 调用本文件的 `CivilRules.SetAlert(ctx, on, Story)` |
| B11 | 04 | 部署状态（`Moving`、`Packing`……）的定义 | 本文件只读 `DeployState` 判断能否开火（3.2.2） |
| B12 | 05 | `CarryIn` / `CarryOut` 字段 | 见 R-CI；`NightResult` 中本文件给出的计数（弹药余量、保护目标 HP、警报响应度、突防原因）供 05 生成 `CarryOut` |
| B13 | 05 | 邻州火力组（`reinforcement`）、邻近扇区覆盖（`sector_coverage`） | 夜间不可呼叫（`NotAvailable`）；前者由 05 在部署方案中加入单位，后者见 Q-S9 |
| B14 | 01 | 敌方平台被击落后其携带弹药的处理、Orlan 存活判断 | 01 负责；本文件只读 `Threats` 中存活平台 |
| B15 | 00 | 碎片是否做成实体（00 Q16） | 不做：碎片在系统 10 当步结算，`Debris` 存储保持为空 |
| B16 | 00 / 01 | `Geo.PointInPolygon` 的唯一实现 | 本文件 3.0 给出；01 的城区 / 森林判断应共用 |
