# 05 战役、经济与关卡流程

> 系统规格层（M3 起实现；生产 / 研发 / 日历为 M5）。详细度比 01–04 低一档，但**状态、公式、流程完整**，每条经济公式至少一条测试。
> 本文件定义的数值参数已按 D2/D2b 人工裁决（`DECISIONS.md`、`A_interfaces.md`、`B_decisions.md`、`C_coverage.md`）统一收口，所有新增数值带 `provisional` 标记供 D4/WS09 平衡微调。
> **文档同步声明（`C-T1-12`）**：本规格已与 GDD / 数值表 / WBS 同步收口，进入实现前无需再次停下询问。
> 术语、类型、子流、`SimWorld` 接口以 [00_core.md](00_core.md) 为准。

---

## 0. 范围与依据

### 0.1 覆盖范围

| 系统 | 本文件章节 | 对应 WBS / 00 待决 |
|---|---|---|
| 战役状态模型（两条主角线、苏制库存、信任度、王牌班组、敌情档案、人情、城市记忆、条令） | 2.1–2.3 | WS05-001 |
| 经济规则：配额、信任度增减、城市资源、保底、紧急支援、历史事件强制配额 | 3.3–3.6 | WS05-002、WS05-005（后半） |
| 关卡内多夜流程（夜晚 → 复盘 → 白天）、时间结构 A–E | 3.2、3.7、3.8 | WS05-003 |
| 跨关影响（GDD 13.5 全部节点）与"战役影响"清单 | 3.10 | WS05-004 |
| 奖励卡（3 选 1） | 3.11 | WS05-005（前半） |
| 敌人适应（GDD 13.4） | 3.12 | WS05-006 |
| 存档 / 读档（含夜间中途） | 3.15 | WS05-007 |
| 战役流程（两线交替、解锁、重试） | 3.1、3.9 | WS05-008 |
| 生产、飞手、产出去向、研发、电力分配（状态 + 公式层） | 3.13、3.14 | WS05-009、010 |
| 日历与自动结算（GDD 11.5） | 3.8 | WS05-011；00 Q11 |
| 死亡螺旋 / 滚雪球防护的批量模拟指标 | 3.16 | WS05-013、WS09 |
| `runSeed`、战役子流（`campaign:` 前缀，`A-5-01`） | 3.1.2 | 00 Q10 |
| `CarryIn` / `CarryOut`（`NightResult` 的战役侧字段）与 `KnownTargetCarryOps` | 2.4、3.7.4 | 00 2.6、3.5；`A-2-18`、`A-2-20` |
| 班组疲劳与王牌班组的跨夜 / 跨关部分 | 3.7.5 | WS01-025（夜内修正由 03 实现） |
| 天气与昼夜的关卡级配置（数据侧） | 1.4、3.7.6 | WS01-026（夜内效果由 02 / 03 实现） |

**不在本文件**：一夜之内的任何规则（探测、交战、伤害、敌方 AI、指挥点扣除）。本文件只**准备** `SimConfig`（部署方案 + `CarryIn`）、**消费** `NightResult`。

### 0.2 依据

- [GDD](../游戏设计文档_GDD_v1.md) v1.3：3.2（指挥权限、归还期限）、4.3（两线互动、人情）、5.1 / 5.3（关卡内循环、战役循环）、8.6（警报暂停城市资源）、8.7（班组疲劳、王牌班组）、8.8（天气昼夜）、8.9（战斗机额度）、8.10（边境越界）、第 9 章（经济）、第 10 章（生产研发）、11.3–11.5（部署时间、时间结构、自动结算）、12.1 / 12.3（关卡表、系统解锁）、第 13 章（跨关影响）、第 14 章（难度模式）、16.4（存档为 JSON）、第 17 章
- [数值表](../塔防数值表_v1.md) v1.2：1.5（备用阵地 / 新阵地）、1.6（邻州火力组、邻近扇区覆盖的信任度代价）、3.3 修正项（班组疲劳、王牌班组、新阵地）、3.4（转移暴露度）、第 4 节（交换比压力、弹药稀缺分级）、5.3（伊朗战争 PAC‑3 减半暂定 2026‑01 起）
- [WBS](../开发任务分解_WBS_v1.md) WS05 全部、WS01-025、WS01-026、WS04-010、WS06-007、WS09
- `data/rules/economy.json`、`data/rules/positions.json`、`data/rules/intercept.json`（`modifiers`）、`data/rules/exposure.json`（`onRelocate`）、`data/support/support.json`（`cost.trust`、`delay.next_day`、`duration.nights`）、`data/units/*.json`（`firstAvailable`、`stockOnly`、`ammoSupply`、`perLevelLimit`、`deployGameSec`、`packGameSec`、`duration` / `durationNights`）、`data/schema/level.schema.json`（`protagonist`、`timeStructure`、`nights`、`availableUnits[].source`、`ammoQuota`、`commandPointsPerNight`、`cityResourcePerDay`、`victory`）

### 0.3 依赖

| # | 规格 | 本文件使用的接口 |
|---|---|---|
| D1 | 00 | `SimWorld.Create / Step / Enqueue / Result`、`SimConfig`、`DeploymentPlan`、`PlacedUnit`、`CarryIn`、`NightResult`、`SimRandom`（`ChildSeed`、`NightSeed`）、`StateHasher`、`DataLoader.LoadLevel(source, levelId, nightIndex)`（`B-T2-17`）、`WeaponParams.LauncherCount`（00 §0.5.1、`A-2-30`）、`JsonCursor` 与错误格式（1.3）、回放（3.9） |
| D2 | 01 | 波次数据（`WavesDef.Nights`）；敌人适应的波次开关与替换（3.12、8.3 R-01） |
| D3 | 02 | `PlacedUnit.FirstNightAtNewPosition` → `PlayerUnitCommon.NewPositionPenalty`（`A-2-13`、`B-T2-06`）、`ExposureRules.Relocated`（02 3.6.3，同一函数在白天转移中复用）、`DeceptionUnit.SeenThrough`、`DeceptionUnitDef.Duration / DurationNights`；敌情档案与自动结算的 `CarryIn` 读取（8.3 R-02） |
| D4 | 03 | `NightResult` 的 `Losses`（含 `BorderViolations`，`C-T2-03`）、`Ammo`、`Exchange`、`Debris`、`Exposure`、`Civil`、`Support`、`Commands`（03 3.8.6）；`PlayerUnitCommon` 的 `NewPositionPenalty`、`DamageEfficiencyMult`、`LightDamaged`；`FireUnit` 的 `CrewConsecutiveNights`、`AceCrew`、`PerLevelUsedBefore`；`Structure.Hp / LossHp`；`Civil.Responsiveness`（均由 `CarryIn` 初始化，03 2.1、2.2、2.7）；空袭警报闸门 `civil.alert.availableFromLevel = 6`（`C-T2-04`） |
| D5 | 04 | `DeploymentValidator.Validate(level, plan)`、`DeploymentRules.CheckPosition(level, unitDefId, pos)`（`A-2-15`）；已知目标清单的跨夜载体 `IReadOnlyList<KnownTargetCarry>?`（00 §2.6、04 §3.2.7 定义记录类型，本文件提供 `KnownTargetCarryOps.IsScouted` / `OnUnitRemoved`，`A-2-18`）；`CommandState` 的每夜指挥点 = `level.commandPointsPerNight + CarryIn.CommandPointsBonus` |

### 0.4 架构要点（写死）

1. **战役层在 `SimWorld` 之外**。它是一个独立的确定性状态机：`CampaignState`（可 JSON 序列化）+ 一组纯函数操作（`CampaignOps`、`LevelFlow`、`EconomyRules`、`TrustRules`、`LinkResolver`、`CardDraw`、`Adaptation`、`ProductionRules`、`ResearchRules`）。不参与 `SimWorld.Step()` 的系统顺序。
2. 代码位置：`sim/Campaign/`（状态、流程、日历 `Calendar`、跨关 `Links`、奖励卡 `Cards`、适应 `Adaptation`、`KnownTargetCarryOps`、数据加载 `CampaignDataLoader`）、`sim/Economy/`（配额、信任度、城市资源、补给、紧急支援）、`sim/Crew/CampaignCrew.cs`（跨夜 / 跨关班组；夜内修正在 03）、`sim/Environment/EnvironmentResolver.cs`（关卡级天气 / 昼夜解析）、`sim/Production/`、`sim/Research/`、`sim/Save/`。命名空间 = `Nightwatch.Sim.<目录名>`。全部遵守 00 第 6 节（无 Godot、无熵源、无 `Dictionary` 遍历依赖；**禁用 `Math.Hypot`**，欧氏距离一律写 `Math.Sqrt(dx*dx + dy*dy)` 或平方距离比较 `dx*dx + dy*dy <= r*r`，`C-T1-04`）。
3. **一夜的边界**：战役层 → `LevelFlow.PrepareNight()` 产出 `(LevelData, SimConfig, ulong seed)` → 宿主（客户端或无画面运行器）创建 `SimWorld` 并推进 → `LevelFlow.ApplyNightResult(NightResult)`。自动结算夜由 `LevelFlow.AutoResolveNight()` 在内部完成同样的三步（3.8.3）。
4. **战役层的随机数（`A-5-01`）**：每次使用时用 `new SimRandom(SimRandom.ChildSeed(RunSeed, <名字>))` 新建，用完即弃，**不保存随机状态**（存档因此不含随机状态；同名永远得到同一序列）。所有战役子流名一律以 `"campaign:"` 开头（`"campaign:cards:…"`、`"campaign:crew:…"`、`"campaign:production:…"`，见 3.1.2），**严禁以 `"night:"` 开头**，从而在结构上与 `SimRandom.NightSeed`（`ChildSeed(runSeed, $"night:{levelId}:{nightSeq}")`）永不碰撞。测试通过 `CampaignOptions.RandomOverride: Func<string, ulong, IRandom>?`（同 00 3.1.4 第 5 条）注入 `ScriptedRandom`。
5. **文件 I/O**：`sim/Save/` 只做"`CampaignState` ↔ UTF-8 字节"，不读写文件（00 6.2 第 7 条）；写文件、原子替换、云存档由 `game/save/` 负责。`CampaignDataLoader` 属于数据加载层，通过 `IDataSource` 读 `data/campaign/` 与关卡的 `flow.json`。
6. **文档同步声明（`C-T1-12`）**：本规格已与 GDD / 数值表 / WBS 同步收口（D2/D2b 全部裁决已合入），进入实现前无需再次停下询问。

---

## 1. 数据输入

> 换算规则见 00 0.4.2。标 **【新】** 的文件 / 字段数据已纳入 D2b 数据规格（8.3）。`CampaignDataLoader` 使用与 `DataLoader` 相同的 `JsonCursor`、错误码与 `Detail` 格式（00 1.3），文件按下表固定顺序读取。

### 1.1 已有数据（本文件读取的字段）

| 文件 → 字段 | C# 名 | 本文件用途 |
|---|---|---|
| `level.json` `number` | `Meta.Number` (`int?`) | 解锁、跨关节点、`firstAvailable` 闸门；`null` = 测试关卡（经济全开，3.3.6） |
| `protagonist` | `Meta.Protagonist` | 信任度归属线（3.4.6）、苏制库存是否适用（A / AB） |
| `dateRange.from` | `Meta.DateFrom` | 历史事件闸门（00 1.4 形态 C，已解析为 `HistoricalEventDef.Active`）、季节缺省（3.7.6）、奖励卡 / 城市商店的日期闸门；多夜关卡单夜存在 `nights[].date` 时，`PrepareNight` 传 `nightIndex: n.WavesNight` 交由 `DataLoader.LoadLevel` 按该夜日期解析（`B-T2-17`） |
| `timeStructure` | `Meta.TimeStructure` | 流程（3.2） |
| `nights` | `Meta.Nights` | = 需要亲自指挥的关键夜数量（`flow.json` 校验） |
| `availableUnits[]{unit,count,source}` | `Meta.AvailableUnits` | 开局花名册（3.3.2）；`source = city` 的 `count` = 本关该单位**可购买上限**（3.5.2，`B-T2-105`） |
| `ammoQuota[]` | `Meta.AmmoQuota` | 开局弹药基数（3.3.3） |
| `commandPointsPerNight` | `Meta.CommandPointsPerNight` | 由 04 使用；本文件只追加 `CarryIn.CommandPointsBonus` |
| `cityResourcePerDay` | `Meta.CityResourcePerDay` (`double?`) | 城市资源速率；`null` = 本关无城市资源（第 1 关"无经济系统"） |
| `victory[]` | `Meta.Victory` | `survive_nights` / `survive_game_sec` 由本文件判定（00 Q4、03 3.8.5） |
| `rules/economy.json` `ammoTiers[]` | `Economy.AmmoTiers` | `replenish = false` + `sharedBy = line_a` 的武器 = 全国共享库存（3.3.4）；`hasFloor` |
| `economy.historicalEvents[]` | `Economy.HistoricalEvents`（`Active` 已解析） | `unit_unavailable`、`resupply_mult`（3.3.5） |
| `economy.commandPointsPerNight{min,max}` | | 校验 `Meta.CommandPointsPerNight + CommandPointsBonus` 截断到 `max`（3.7.3） |
| `rules/positions.json` `preparedAlternate.deployTimeMult`、`availableFromLevel`；`newUnsurveyed` | `Positions` | 白天转移的时间槽（3.7.2）、勘察（3.7.2） |
| `rules/exposure.json` `onRelocate` | `Exposure.OnRelocate` | 白天转移暴露度（复用 02 `ExposureRules.Relocated`） |
| `rules/intercept.json` `modifiers.crewFatigue.minConsecutiveNights` | | 仅用于界面提示；判定在 03 |
| `rules/civil.json` `alert.availableFromLevel` | `Civil.Alert.AvailableFromLevel` | 空袭警报命令自第 6 关起启用（03 §1.12 / §3.7.1，`C-T2-04`） |
| `support/support.json` `cost.trust`、`delay.kind = next_day / instant`、`duration.nights`、`reinforcementUnit`、`reinforcementCount`、`firstAvailable.level` | `SupportDef` | 信任度申请（3.4.5） |
| `units/*.json` `firstAvailable.level`、`stockOnly`、`deployGameSec` / `packGameSec`、`mobility` | | 解锁闸门、库存制单位、转移时间槽 |
| `units/air_defense.json` `weapons[].magazine`、`launchers`、`magazineRounds`、`ammoSupply`、`perLevelLimit`、`interceptClass`、`targets` | `WeaponDef` | 装填（3.3.3，调用 `WeaponParams.LauncherCount`，`A-2-30`）、补给运力（3.7.2）、敌人适应统计（3.12） |
| `units/deception.json` `duration`、`durationNights` | `DeceptionUnitDef` | 假发射车跨夜寿命（3.7.4） |
| `waves.json` `nights[]{night, date?, durationGameSec, weather, season, timeOfDay?}` | `NightDef` | 夜晚模板、单夜日期覆盖（`B-T2-17`）、天气与昼夜（3.7.6） |

**从 `NightResult` 读取的 03 / 04 字段**（00 §3.5、03 §3.8.6 已定义，`A-2-20`）：`Outcome`、`EndReason`、`EndTimeSec`；`Losses.WeightedLossFrac`、`Losses.Structures[]`（`StructureId, MaxHp, HpEnd, LossHp, Destroyed, PoweredAtEnd, PausedSec`）、`Losses.UnitLosses[]`、`Losses.ThreatsImpacted`、`Losses.ThreatsEwDowned`、`Losses.ThreatsArmMissed`、`Losses.HighThreatLeaksWithReserve`、`Losses.BorderViolations[]`（`C-T2-03`）；`Ammo.Weapons[]`（`WeaponId, Shots, Hits, PerLevelUsedTotal`）、`Ammo.PoolRemaining`；`Exchange.TotalPotentialLossMusd / TotalShotCostMusd / ExchangeRatio / ByWeapon[]`；`Debris.UrbanInterceptRatio`；`Exposure.Units[]`；`Civil.AlertActiveSec / ResponsivenessEnd`；`Commands.RelocationsCompleted`。另加 `CarryOut`（2.4.2，含 `UrbanNavJamTriggered` 与 `StoryChoiceResults`）。

### 1.2 新增：`rules/economy.json` 追加块【新】

> 全部带 `provisional` 标记（data/README 第 5 节，`B-T3-01`、`B-T3-04`、`B-T2-10`、`B-T2-36`、`B-T2-103`–`B-T2-110`、`C-T2-03`）。下列 JSON 即默认生效值；C# 名按 00 1.2 规则（`camelCase` → `PascalCase`）。

```json
"trust": {
  "availableFromLevel": 6,
  "initial": 50, "min": 10, "max": 100, "neutral": 50,
  "exchangeBands": [
    { "minRatio": 0,   "delta": -3 },
    { "minRatio": 0.4, "delta": -1 },
    { "minRatio": 1.5, "delta": 0 },
    { "minRatio": 4.0, "delta": 1 },
    { "minRatio": 10,  "delta": 3 }
  ],
  "minShotCostForExchangeMusd": 0.5,
  "wastefulWeapon": { "minAvgShotCostMusd": 2.0, "maxRatio": 0.2, "minKills": 1, "penaltyPerShot": 3, "maxPenaltyPerNight": 9 },
  "inquiry": { "minWastefulShots": 2, "penalty": 3 },
  "hoardedLeak": { "penaltyPerLeak": 2, "maxPenaltyPerNight": 6 },
  "borderViolation": { "penaltyPerViolation": 2, "maxPenaltyPerNight": 6 },
  "nightDeltaClamp": { "min": -12, "max": 8 },
  "levelVictoryBonus": 5, "levelDefeatPenalty": 8,
  "quotaModMaxFrac": 0.10,
  "requestCost": { "small": 8, "large": 20 }
},
"crossLevelModClamp": { "min": -0.2, "max": 0.2 },
"cityResource": {
  "startDays": 1, "cap": 30, "alertPauseWeight": 0.5, "urbanNavJamPenalty": 1.0,
  "shop": [
    { "id": "buy_fire_team",   "kind": "unit", "unit": "mobile_fire_team", "cost": 2 },
    { "id": "buy_acoustic",    "kind": "unit", "unit": "acoustic_post", "cost": 0.5 },
    { "id": "buy_observer",    "kind": "unit", "unit": "visual_observer", "cost": 0.5 },
    { "id": "buy_drone_team",  "kind": "unit", "unit": "interceptor_drone_team", "cost": 3, "availableFromLevel": 14, "until": "2025-10" },
    { "id": "buy_searchlight", "kind": "night_aid", "aid": "searchlight", "cost": 0.5 },
    { "id": "buy_repair_team", "kind": "repair_team", "cost": 2, "logisticsAdd": 2, "perLevelCap": 2 }
  ]
},
"supply": {
  "logisticsPerWindow": 10,
  "roundCostByAmmoSupply": { "ample": 0, "medium": 0.05, "limited": 0.5, "scarce": 1, "none": 1 },
  "roundCostByWeapon": { "pac2": 2, "pac3_mse": 2, "aster_30": 1.5 }
},
"repair": { "lightLogistics": 2, "lightDays": 1, "crippledLogistics": 5, "crippledDays": 3, "structureHpFracPerDay": 0.1 },
"relocation": { "timeSlotsPerDay": 3, "slotGameSec": 30, "surveyTimeSlots": 1, "dayExposureDecayPerDay": 20 },
"emergencySupport": {
  "triggerSetbacks": 2, "setbackWeightedLossFrac": 0.3,
  "grants": [
    { "kind": "command_points_delta", "delta": 1 },
    { "kind": "ammo_frac_immediate", "frac": 0.2 },
    { "kind": "trust_raise_to", "value": 30 }
  ]
},
"requests": [
  { "id": "req_nasams_loan", "kind": "unit", "unit": "nasams", "count": 1, "trustCost": "large", "arrivalDays": 3, "durationNights": 2, "line": "A", "firstAvailableLevel": 6 },
  { "id": "req_pac3_rush",   "kind": "ammo", "weapon": "pac3_mse", "count": 8, "trustCost": "small", "arrivalDays": 1, "line": "A", "firstAvailableLevel": 7 }
]
```

| 新增参数 | 说明 | 用于 |
|---|---|---|
| `trust.*` | 信任度量表（0–100 标度，保底下限 `min = 10`，`B-T3-04` / `B-T2-103`）与增减规则；`wastefulWeapon.maxRatio = 0.2` 按 `B-T3-01` 混合潜在损失公式标定（PAC‑3 打 Shahed 为 `0.4 / 4 = 0.1 < 0.2`）；`borderViolation` 为邻国越界信任度扣分（`C-T2-03`） | 3.4 |
| `crossLevelModClamp` | GDD 13.2"±10–20%"：所有比例型修正之和的夹紧区间 | 3.3.1 |
| `cityResource.*` | 城市资源积累、上限、城区导航干扰误伤惩罚 `urbanNavJamPenalty = 1.0`（`B-T2-36`）、商店（`buy_drone_team` 自第 14 关起可买、`until = "2025-10"`，`B-T2-10`；`buy_searchlight` 为 `night_aid` 商品，`B-T2-105`；`unit` 类每关上限由 `availableUnits[source=city].count` 给出） | 3.5 |
| `supply.*` | 补给运力（"运力点"，无单位）：每个补给窗口的总量、每发弹药的运力成本 | 3.7.2 |
| `repair.*` | 维修（与补给共用运力，GDD 9.4"先修雷达还是先补弹药"） | 3.7.2 |
| `relocation.*` | 白天转移时间槽、勘察、白天暴露度衰减 | 3.7.2 |
| `emergencySupport.*` | GDD 9.5"连续失败触发上级紧急支援" | 3.6 |
| `requests[]` | GDD 9.2"申请增援（临时调来一套 NASAMS、加急补 PAC‑3……）"的目录；`support.json` 中 `cost.trust` 非空的条目自动并入（3.4.5） | 3.4.5 |

### 1.3 新增：`rules/campaign.json`（`kind: campaign_rules`）【新】

```json
{
  "kind": "campaign_rules",
  "crew": { "aceDeathChanceOnUnitDestroyed": 0.5, "woundedNights": 2, "xpPerHit": 1 },
  "alert": { "dayRecovery": 0.2 },
  "autoResolve": { "interceptProbMult": 1.0, "exposureGainMult": 1.0, "watchTrustBonus": 1 },
  "adaptation": {
    "alpha": 0.5, "hysteresis": 0.1, "positionRadiusM": 500,
    "rules": [
      { "id": "uav_fly_higher",       "stat": "gun_kill_share",   "threshold": 0.5, "notBefore": "2024-01", "effect": { "kind": "uav_altitude_add", "valueM": 1000 } },
      { "id": "evasive_uav_early",    "stat": "drone_kill_share", "threshold": 0.5, "notBefore": "2024-09", "effect": { "kind": "force_evasive_uav" } },
      { "id": "position_priority",    "stat": "position_nights",  "threshold": 3,                          "effect": { "kind": "priority_position" } },
      { "id": "suppress_then_strike", "stat": "arm_shutdown_rate","threshold": 0.7,                        "effect": { "kind": "enable_trigger", "trigger": "silence_heavy" } },
      { "id": "anti_ew_mix",          "stat": "ew_coverage_frac", "threshold": 0.5,                        "effect": { "kind": "enable_trigger", "trigger": "ew_heavy" } }
    ]
  },
  "dossier": {
    "pointsPerKill": 1, "maxPoints": 50,
    "levels": [ { "minPoints": 5, "discriminationAdd": 0.05, "classifyTimeMult": 0.9 },
                { "minPoints": 20, "discriminationAdd": 0.10, "classifyTimeMult": 0.75 } ],
    "families": [ { "id": "geran_jet", "members": ["geran_3", "geran_4", "geran_5"] },
                  { "id": "shahed", "members": ["shahed_136", "geran_2_heavy"] } ]
  },
  "cityMemory": { "bonusFracPerVictory": 0.1, "maxBonusFrac": 0.2 },
  "rewardCards": { "offerCount": 3 },
  "balanceTargets": { "trustFloorDwellMax": 0.15, "trustFloorMargin": 5, "recoveryRateMin": 0.6,
                      "resourceSpreadMax": 1.5, "requestStrategySpreadMax": 0.15, "winGapSlopeMax": 0.02,
                      "autoResolveGapMin": 0.03, "autoResolveGapMax": 0.10, "floorLevelWinRateMin": 0.4 }
}
```

- `alert.dayRecovery = 0.2`：白天每流逝 1 天，民众警报响应度恢复 `+0.2`（上限 `1.0`，`B-T2-81`）。
- `autoResolve.interceptProbMult = 1.0`：默认只靠"不使用指挥点"拉开自动结算与手打差距（字段与管线保留；若 D4/WS09 实测 `AutoResolveGap < 0.03`，则在数据中调为 `0.95`，`B-T3-07`）。
- `adaptation.rules[].effect`：单位后缀写在数值字段名 `valueM` 上，枚举值为 `uav_altitude_add`（`A-3-04`）。
- `balanceTargets` 只由 `tools/balance` 读取（3.16），模拟层不读（含 `requestStrategySpreadMax = 0.15` 检查"一直申请"与"从不申请"总资源差 ≤ 15%，`B-T3-04`；`autoResolveGapMin = 0.03, autoResolveGapMax = 0.10`，`B-T3-07`）。

### 1.4 新增：关卡流程 `levels/<id>/flow.json`（`kind: level_flow`，可选）【新】

```json
{
  "kind": "level_flow",
  "city": "kyiv",
  "days": 21,
  "dayPhase": "full",
  "nights": [
    { "day": 3,  "kind": "auto",  "wavesNight": 1 },
    { "day": 5,  "kind": "key",   "wavesNight": 2, "warnDaysBefore": 3 },
    { "day": 6,  "kind": "quiet" }
  ],
  "supplyWindows": [ { "day": 4, "logistics": 12 } ],
  "resupplyLimits": [ { "weapon": "pac3_mse", "count": 8 } ],
  "reinforcements": [ { "day": 4, "unit": "gepard", "count": 1, "returnAfterDay": 10 } ],
  "rosterTags": [ { "unit": "mobile_fire_team", "index": 0, "tag": "volunteer_fire_team" } ],
  "objectives": [
    { "id": "obj_grid", "scope": "night", "type": "weighted_loss_at_most", "fraction": 0.2, "trustOnSuccess": 2, "trustOnFail": -2 },
    { "id": "obj_tpp",  "scope": "level", "type": "structure_intact", "structure": "tpp", "trustOnSuccess": 3, "trustOnFail": -3 }
  ],
  "levelMetrics": [ { "key": "escort_survival_frac", "source": "custom" } ],
  "production": null,
  "research": null
}
```

| 字段 | C# | 规则 |
|---|---|---|
| `city` | `CityId` (`string?`) | 城市记忆键（3.10.4）；同一城市的关卡用同一值（`kyiv`、`kharkiv`、`zaporizhzhia`） |
| `days` | `Days` (`int`) | 日历天数（1 起）；A / B 必须为 1 |
| `dayPhase` | `DayPhaseKind { Full = 0, Interlude = 1, None = 2 }?` | 夜与夜之间的白天类型；缺省：A / B → `None`，C / E → `Full`，D → `Interlude`（`B-T2-121`） |
| `nights[]` | `FlowNightDef(int Day, NightKind Kind, int? WavesNight, int? WarnDaysBefore)` | `NightKind { Key = 0, Auto = 1, Quiet = 2 }`。昼间战斗（第 18 关白天消耗段）= 引用一个 `timeOfDay: day` 的波次夜（3.7.6）。`day` 严格升序且 ≤ `days`；`Key` / `Auto` 必须有 `wavesNight`（∈ `waves.json` 的 `night`），`Quiet` 不得有。"大空袭夜"沿用 03 登记的 `waves.json nights[].bigRaid`（03 Q-S8），本文件只读 `NightDef.BigRaid` 发预警（3.8.4）。同一 `wavesNight` 可被多个条目复用（E 的普通夜） |
| `supplyWindows[]` | `SupplyWindowDef(int Day, double Logistics, int? AfterNight)` | 有此数组时只有列出的窗口提供补给运力（3.2.4 第 10 步；`afterNight` = `flow.nights` 下标，窗口只在该夜之后的白天开放）；无此数组时每个 `Full` 白天都有 `supply.logisticsPerWindow`，`Interlude` 白天没有。结构 E 关卡必须显式配置 `supplyWindows`，缺失时数据校验报警告 `W_E_NO_SUPPLY_WINDOWS`（`B-T2-122`） |
| `resupplyLimits[]` | `ResupplyLimitDef(string WeaponId, int Count)` | 本关白天补给该武器的总上限（不含开局装填）；未列出的配额级武器上限 = 开局基数（3.3.3 的 `base`） |
| `reinforcements[]` | `ScriptedReinforcementDef(int Day, string UnitId, int Count, int? ReturnAfterDay)` | 剧本安排的配属（作战控制，GDD 3.2"有归还期限"） |
| `rosterTags[]` | `RosterTagDef(string UnitId, int Index, string Tag)` | 给开局花名册中该单位的第 `index` 个（0 起）打标签，供跨关节点统计 |
| `objectives[]` | `ObjectiveDef(string Id, ObjectiveScope Scope, ObjectiveType Type, double? Fraction, string? StructureId, int? Count, double TrustOnSuccess, double TrustOnFail)` | `ObjectiveScope { Night = 0, Level = 1 }`；`ObjectiveType { WeightedLossAtMost = 0, StructureIntact = 1, UrbanInterceptRatioAtMost = 2, LeaksAtMost = 3 }`（上级目标，3.4.3） |
| `levelMetrics[]` | `LevelMetricDef(string Key, string Source)` | 关卡结束时写入 `LevelRecord.Metrics` 的自定义指标；`source = custom` 取自 `CarryOut.CustomMetrics`（由关卡专用规则提供，例如护送 / 撤离 / 补给车，WS02） |
| `production` / `research` | 3.13 / 3.14 | M5 |

**缺省流程**（无 `flow.json`）：`days = waves.json` 的夜数；`nights[i] = { day = i+1, kind = key, wavesNight = waves.nights[i].night }`；`dayPhase` 按结构缺省；无目标、无补给窗口数组。

**校验**（`CampaignDataLoader`，错误码沿用 00 1.3）：`Key` 夜数 ≠ `Meta.Nights` → `E_RANGE`；结构 A / B：恰 1 个 `Key` 夜、无 `Auto`；C：3–5 个 `Key`、无 `Auto`；D：≥ 2 个 `Key`、无 `Auto`；E：≥ 1 个 `Key`。违反 → `E_RANGE`（`Detail` 写明结构与计数）。`victory` 中 `survive_nights.nights` ≠ `Meta.Nights` → `E_RANGE`。结构 E 关卡若 `supplyWindows == null || supplyWindows.Count == 0`，由 `tools/validate` 输出警告 `W_E_NO_SUPPLY_WINDOWS`（`B-T2-122`）。

### 1.5 新增：`data/campaign/` 文件【新】

| 文件 | `kind` | 内容 | 章节 |
|---|---|---|---|
| `campaign.json` | `campaign` | 关卡顺序（编号 → 关卡 ID、主角线）、初始苏制库存与保底、王牌班组名单引用、两线插曲选择（`interludes`）、人情定义（`favors`） | 3.1、3.9、3.10.5 |
| `links.json` | `links` | 跨关节点（GDD 13.5） | 3.10 |
| `cards.json` | `cards` | 奖励卡 | 3.11 |
| `crews.json` | `crews` | 王牌班组（`id`、`nameKey`、`line`、`eligibleUnits[]`、`joinLevel`） | 3.7.5 |
| `doctrines.json` | `doctrines` | 条令（`id`、`nameKey`、`line`、`effectKey`；效果由所属规格实现） | 3.10.6 |
| `production.json` | `production` | 设施类型、零部件、飞手（M5） | 3.13 |
| `research.json` | `research` | 研发项目（M5） | 3.14 |

`campaign.json` 示例：

```json
{
  "kind": "campaign",
  "id": "main",
  "levels": [ { "number": 1, "level": "l01", "line": "AB" }, { "number": 2, "level": "l02", "line": "B" }, { "number": 3, "level": "l03", "line": "A" } ],
  "nationalStock": [ { "weapon": "s300_missile", "rounds": 40, "floor": 6 }, { "weapon": "buk_m1_missile", "rounds": 24, "floor": 4 } ],
  "favors": [ { "id": "favor_b_drone_team", "grantUnit": "interceptor_drone_team", "count": 1, "nights": 1 } ],
  "interludes": [
    { "id": "lend_gepard", "afterLevel": 7, "promptKey": "interlude.lend_gepard", "options": [
        { "textKey": "interlude.lend_gepard.yes", "effects": [
            { "kind": "unit_count_delta", "unit": "gepard", "delta": -1, "at": { "nextLevelOfLine": "A" } },
            { "kind": "grant_unit", "unit": "gepard", "count": 1, "at": { "nextLevelOfLine": "B" } },
            { "kind": "favor", "favor": "favor_b_drone_team", "holder": "A", "uses": 1, "at": "immediate" } ] },
        { "textKey": "interlude.lend_gepard.no", "effects": [] } ] }
  ]
}
```

### 1.6 效果（`EffectDef`）——跨关节点、奖励卡、插曲、紧急支援共用

```csharp
public enum EffectKind
{
    AmmoFrac = 0,                  // weapon, frac：计入该武器开局弹药的比例修正（3.3.1）
    CityResourceFrac = 1,          // frac：计入城市资源比例修正
    LogisticsFrac = 2,             // frac：计入补给运力比例修正
    GrantUnit = 3,                 // unit, count, condition?, ammoFrac?, tag?, nights?：开局加入花名册（绝对数量，不受夹紧）
    UnitCountDelta = 4,            // unit, delta：修改 availableUnits 中该单位的 count（下限见 3.3.2）
    FighterSortiesDelta = 5,       // delta：本关每夜战斗机额度（CarryIn.FighterSortiesDelta）
    CommandPointsDelta = 6,        // delta：下一夜（紧急支援）或本关每夜（其余来源）的指挥点
    SurveyedPositions = 7,         // count：开局把前 count 个未勘察备用阵地（数据顺序）标为已勘察
    ReturnDeadlineExtend = 8,      // unit, nights：延长作战控制单位的归还期限
    UnlockDoctrine = 9,            // doctrine
    AceCrewsJoin = 10,             // count：本线前 count 个未加入的王牌班组加入（crews.json 顺序）
    ProductionLineStart = 11,      // facilityType, outputStock：开局即有一个运转中的设施与成品库存
    Favor = 12,                    // favor, holder, uses
    TrustDelta = 13,               // line, delta
    SetFlag = 14,                  // key, value
    AmmoFracImmediate = 15,        // frac：立即把每种配额级武器"开局基数 × frac"（四舍五入）放入弹药库（紧急支援）
    TrustRaiseTo = 16              // value：Trust = max(Trust, value)
}
public sealed record EffectDef(EffectKind Kind, string? UnitId, string? WeaponId, double? Frac, int? Count, int? Delta,
    UnitCondition? Condition, double? AmmoFrac, string? Tag, int? Nights, string? DoctrineId, string? FacilityType,
    int? OutputStock, string? FavorId, Line? Holder, int? Uses, Line? TargetLine, string? Key, double? Value, EffectTarget At);
public sealed record EffectTarget(int? Level, Line? NextLevelOfLine, bool Immediate);   // JSON: {level:n} | {nextLevelOfLine:"A"} | "immediate"
```

JSON 键：`kind`（snake_case → 上面的 enum）、`unit`、`weapon`、`frac`、`count`、`delta`、`condition`（`intact` / `light_damaged` / `crippled`）、`ammoFrac`、`tag`、`nights`、`doctrine`、`facilityType`、`outputStock`、`favor`、`holder`、`uses`、`line`、`key`、`value`、`at`。各 `kind` 的必填键如注释；缺失 → `E_MISSING_FIELD`。`at` 缺省：跨关节点必须写 `level`；奖励卡缺省 `nextLevelOfLine = 卡的 line`；紧急支援固定 `Immediate`。

---

## 2. 状态

> 全部类型可被 `System.Text.Json` 往返（3.15）。集合一律有序：`List<T>`（顺序在表中写明）或 `SortedDictionary<string, T>` / `SortedSet<string>`（`StringComparer.Ordinal`）。不出现 `Dictionary` / `HashSet`。"写 / 读"列：本文件小节号或规格号。

### 2.1 `CampaignState`（`Nightwatch.Sim.Campaign`）

| 字段 | C# 类型 | 初值 | 写 | 读 |
|---|---|---|---|---|
| `FormatVersion` | `int` | `1` | 3.15 | 3.15 |
| `CampaignId` | `string` | `campaign.json` 的 `id` | 3.1 | 全部 |
| `RunSeed` | `ulong`（JSON：`"0x" + X16` 字符串） | 新战役参数 | 3.1 | 3.1.2 |
| `Difficulty` | `Difficulty { Narrative = 0, Normal = 1, Hardcore = 2 }` | 新战役参数 | 3.1 | 3.3.1、3.7.5、3.10、3.12 |
| `Lines` | `List<LineState>`（恰 2 项：下标 0 = A，1 = B） | 2.2 | 3.4、3.6、3.7.5、3.10 | 全部 |
| `NationalStock` | `SortedDictionary<string, StockEntry>`（键 = 武器 ID） | `campaign.json` `nationalStock` | 3.3.4 | 3.3.4 |
| `Dossier` | `SortedDictionary<string, int>`（键 = 家族 ID，值 = 点数） | 空 | 3.10.3 | 3.10.3 |
| `Adaptation` | `AdaptationState` | 空 | 3.12 | 3.12 |
| `CityMemory` | `SortedDictionary<string, CityMemoryEntry>` | 空 | 3.10.4 | 3.5 |
| `LinkOutcomes` | `SortedDictionary<string, LinkOutcome>`（键 = 节点 ID） | 空 | 3.10.1 | 3.10.2 |
| `PendingEffects` | `List<PendingEffect>`（追加顺序） | 空 | 3.10、3.11、插曲 | 3.3.1 |
| `Flags` | `SortedDictionary<string, double>` | 空 | `SetFlag` | 跨关度量 |
| `ResearchCompleted` | `SortedSet<string>` | 空 | 3.14 | 3.14、3.10 |
| `CompletedLevels` | `List<LevelRecord>`（完成顺序） | 空 | 3.9 | 3.9、3.10、3.16 |
| `CurrentLevel` | `LevelRunState?` | `null` | 3.2 | 全部 |
| `LevelStartSnapshot` | `string?` | `null` | 3.2.1 | 3.9（重试） |
| `PendingCardOffer` | `CardOffer?` | `null` | 3.11 | 3.11 |
| `PendingInterlude` | `string?`（插曲 ID） | `null` | 3.9 | 3.9 |

```csharp
public enum Line { A = 0, B = 1 }
public sealed record StockEntry(int Rounds, int Floor);                          // 可变：用 with 更新
public sealed record CityMemoryEntry(int Visits, int Victories);
public sealed record LinkOutcome(int OutcomeIndex, double MetricValue, string SourceLevelId);
public sealed record PendingEffect(string SourceKey, EffectDef Effect, int? TargetLevel, Line? TargetLine);   // 已把 At 解析为具体关卡号或"某线下一关"
public sealed record LevelRecord(string LevelId, int? Number, int Attempts, LevelOutcome Outcome,
    SortedDictionary<string, double> Metrics, double TrustAtStartA, double TrustAtStartB);
public enum LevelOutcome { Completed = 0, Failed = 1 }
public sealed record CardOffer(string LevelId, Line Line, IReadOnlyList<string> CardIds);
```

### 2.2 `LineState`

| 字段 | C# 类型 | 初值 | 说明 |
|---|---|---|---|
| `Line` | `Line` | | |
| `Trust` | `double` | `trust.initial` | `[trust.min, trust.max]`（0–100 标度，保底 `trust.min = 10`，`B-T3-04` / `B-T2-103`） |
| `Setbacks` | `int` | 0 | 连续挫折计数（3.6）；跨关、跨重试保留 |
| `EmergencyGrantedThisLevel` | `bool` | false | 每次开始关卡（含重试）时清零 |
| `Doctrines` | `SortedSet<string>` | 空 | 已解锁条令 |
| `AceCrews` | `List<AceCrewState>`（`crews.json` 中本线顺序） | 每个 `crews.json` 条目一项，`Status = NotJoined` | |
| `Favors` | `List<FavorToken>`（获得顺序） | 空 | 本线**持有**的人情 |
| `Cards` | `List<string>`（选择顺序） | 空 | 已选奖励卡 ID（记录用，效果在 `PendingEffects`） |

```csharp
public enum AceStatus { NotJoined = 0, Available = 1, Wounded = 2, Dead = 3 }
public sealed class AceCrewState { public string AceId; public AceStatus Status; public int WoundedNightsLeft; public int Xp; public int ConsecutiveNights; public int LastFoughtDay; }
public sealed record FavorToken(string FavorId, Line OwedBy, int UsesLeft);
```

### 2.3 `LevelRunState`（关卡进行中）

| 字段 | C# 类型 | 初值（3.3） | 说明 |
|---|---|---|---|
| `LevelId` / `Number` | `string` / `int?` | | |
| `Attempt` | `int` | 1 起 | 第几次尝试 |
| `Phase` | `LevelPhase { Briefing = 0, Deployment = 1, Night = 2, Review = 3, Day = 4, Completed = 5, Failed = 6 }` | `Briefing` | 3.2 |
| `Day` | `int` | 3.2.3 | 当前日历日（1 起；E 开局为 0） |
| `NextNightIndex` | `int` | 0 | 下一个要处理的 `flow.nights[]` 下标 |
| `Roster` | `List<RosterUnit>`（`RosterId` 升序） | 3.3.2 | 花名册 |
| `NextRosterId` | `int` | 1 | 只增不减 |
| `Depot` | `SortedDictionary<string, int>` | 3.3.3 | 关卡弹药库（未装填的弹药；即 03 的 `AmmoPool`） |
| `ResupplyDelivered` | `SortedDictionary<string, int>` | 空 | 本关白天已补给数（对照 `resupplyLimits`） |
| `PerLevelUsed` | `SortedDictionary<string, int>` | 空 | `perLevelLimit` 已用（= 上一夜 `Ammo.Weapons[].PerLevelUsedTotal`） |
| `CityResource` | `double` | 3.5.1 | `[0, cap]` |
| `CityPurchases` | `SortedDictionary<string, int>` | 空 | 商店条目 ID → 本关已买数量 |
| `RepairTeams` | `int` | 0 | 已购维修队数（3.5.2） |
| `NightAidStock` | `SortedDictionary<NightAid, int>` | 空 | 城市商店购买的未消耗夜间辅助装备库存（如 `searchlight`，`B-T2-105`） |
| `Tallies` | `PlayTallies` | 全 0 | 本关累计的打法统计（3.12.1） |
| `TimeSlotsLeft` | `int` | 0 | 当前白天剩余时间槽 |
| `LogisticsLeft` | `double` | 0 | 当前白天剩余运力 |
| `Structures` | `SortedDictionary<string, StructureCarry>` | 空（= 满血） | `StructureCarry(int Hp, double LossHp, bool Destroyed)` |
| `KnownTargets` | `IReadOnlyList<KnownTargetCarry>?`（00 §2.6 / 04 §3.2.7，`A-2-18`） | `null` | 跨夜已知目标列表（经 `KnownTargetCarryOps` 查询与移除已毁单位） |
| `AlertResponsiveness` | `double` | 1.0 | 03 `Civil.Responsiveness` 跨夜（3.7.4，白天每流逝 1 天恢复 `+0.2` 至上限 `1.0`，`B-T2-81`） |
| `SurveyedPositions` | `SortedSet<string>` | 3.3.7 | 本关已勘察的备用阵地 ID（含数据中 `surveyed = true` 的） |
| `PendingArrivals` | `List<PendingArrival>`（申请顺序） | 空 | 3.4.5 |
| `ActiveSupports` | `List<ActiveSupport>`（获得顺序） | 空 | 夜间生效的外部支援（如 `adjacent_sector_coverage`，`B-T2-89`） |
| `ResourceMods` | `SortedDictionary<string, double>` | 3.3.1 | 已夹紧的比例修正：键 `ammo:<weaponId>`、`city`、`logistics` |
| `ResourceBase` | `SortedDictionary<string, int>` | 3.3.3 | 配额级武器的开局基数（紧急支援、补给上限使用） |
| `CommandPointsBonusLevel` | `int` | 3.3.1 | 本关每夜的指挥点加成（来自效果） |
| `CommandPointsBonusNext` | `int` | 0 | 仅下一夜（紧急支援、亲自观看奖励之外的一次性加成） |
| `FighterSortiesDelta` | `int` | 3.3.1 | |
| `Nights` | `List<NightRecord>`（处理顺序） | 空 | 3.7.4 |
| `Metrics` | `SortedDictionary<string, double>` | 空 | 关卡度量（跨关节点用，3.10.1） |
| `HandedOver` / `HandoverTrust` | `int` / `double` | 0 / 0 | 3.13.4 |
| `Production` | `ProductionState?` | 3.13 | M5 |
| `Research` | `ResearchProgress?` | 3.14 | M5 |
| `Power` | `PowerAllocation?` | `null` | 3.14.3 |
| `RaidWarnings` | `SortedSet<int>` | 空 | 已发出预警的关键夜 `day` |
| `ConsumedWindows` | `SortedSet<int>` | 空 | 已领取的 `supplyWindows` 下标 |
| `NightInProgress` | `NightInProgressSave?` | `null` | 夜间中途存档（3.15.3） |
| `PreAutoNightSnapshot` | `string?` | `null` | 最近一次 `AutoResolveNight` 前的状态快照，供 `Review` 阶段消耗重打次数手打覆盖（3.8.2，`B-T3-07`） |
| `WatchNext` | `bool` | false | 下一个普通夜改为亲自观看（3.2.2） |
| `InitialPlacement` | `bool` | false | 结构 E 开局的放置阶段（3.2.2） |
| `DeadlineExtensions` | `SortedDictionary<string, int>` | 3.3.7 | 单位 ID → 归还期限延长的夜数 |
| `NextArrivalId` | `int` | 1 | `PendingArrival.ArrivalId` 计数 |
| `LastAlertFrac` | `double` | 0 | 上一夜 `AlertActiveSec / DurationSec`（3.2.4 的 `a`） |
| `LastUnpoweredStructures` | `SortedSet<string>` | 空 | 上一夜 `PoweredAtEnd == false` 的保护目标 ID（3.13.2、3.14.3）；空 = 全部有电 |
| `StockAtLevelStart` | `SortedDictionary<string, int>` | 开局时的 `NationalStock[*].Rounds` | 跨关度量 `StockUsed`、影响清单 |

```csharp
public enum UnitSource { Quota = 0, City = 1, Stock = 2, Request = 3, Effect = 4, Scripted = 5, Emergency = 6, Production = 7, Favor = 8 }
public enum UnitCondition { Intact = 0, LightDamaged = 1, Crippled = 2 }
public enum PositionKind { Initial = 0, Surveyed = 1, New = 2 }

public sealed class RosterUnit
{
    public int RosterId;                     // 关卡内唯一，从 1 起
    public string UnitDefId;
    public PlayerUnitCategory Category;      // 00 1.6
    public UnitSource Source;
    public string? Tag;                      // rosterTags / grant_unit 的 tag
    public Vec2? Pos;                        // null = 尚未放置
    public string? AlternatePositionId;      // 当前所在备用阵地（若是）
    public PositionKind PositionKind;
    public bool FirstNightAtNewPosition;     // → PlacedUnit.FirstNightAtNewPosition → PlayerUnitCommon.NewPositionPenalty（00 / 02 / 03，A-2-13、B-T2-06）
    public double Exposure;                  // 0–100
    public UnitCondition Condition;
    public int RepairDaysLeft;               // 0 = 未在维修
    public double DamageEfficiencyMult;      // 1.0 或 03 给出的值（轻伤 0.8）
    public List<RosterWeapon> Weapons;       // 火力单元：按 AirDefenseUnitDef.WeaponIds 顺序；其他类别为空
    public int CrewNights;                   // 普通班组的连续作战夜数（3.7.5）
    public int LastFoughtDay;                // 0 = 本关未作战
    public string? AceId;                    // 当前配属的王牌班组
    public int AvailableFromDay;             // 申请 / 剧本增援的可用起始日；开局单位 = 0
    public int? ReturnAfterNightIndex;       // 作战控制：flow.nights 下标为此值的夜晚结束后归还（移出花名册）；剧本的 returnAfterDay 在加入时换算为"day ≤ returnAfterDay 的最后一个 Key/Auto 夜的下标"
    public int? NightsLeft;                  // 有期限的单位（申请增援 durationNights、假发射车 durationNights）；null = 不限
    public bool SeenThrough;                 // 假发射车被识破（3.7.4）
    public int NightsAtPosition;             // 在当前阵地连续部署的夜数（敌人适应，3.12）
    public bool Deployed;                    // 当前部署方案是否包含本单位
    public UnitSettings? Settings;           // 玩家上次设定（00 PlacedUnit.Settings），白天保留
    public int LevelHits;                    // 本关累计命中（王牌经验）
}
public sealed class RosterWeapon { public string WeaponId; public List<int> LauncherRounds; }   // −1 = 不计数（身管 / 无限）
public sealed record PendingArrival(int ArrivalId, string RequestId, string? UnitId, string? WeaponId, int Count, int AvailableFromDay, int? DurationNights, Line PaidBy);
public sealed record ActiveSupport(string SupportDefId, int NightsLeft);
public sealed record NightRecord(int Index, int Day, NightKind Kind, int WavesNight, string Seed, NightOutcome Outcome,
    bool AutoResolved, bool Watched, double TrustDelta, TrustBreakdown Breakdown, double WeightedLossFrac, bool Setback);
public sealed record TrustBreakdown(double Exchange, double Wasteful, double Inquiry, double Hoarded, double Objectives, double Border, double Raw, double Applied);
public sealed class PlayTallies { public int HitsTotal; public int HitsGun; public int HitsDrone; public int ArmDetections; public int ArmShutdowns; public int ThreatsSpawned; public int ThreatsEverEwCovered; }
```

### 2.4 `CarryIn` / `CarryOut`（与 00 §2.6 / §3.5、03 §3.8.6、04 §3.2.7 对齐）

#### 2.4.1 `CarryIn`（`SimConfig.CarryIn`，`Create` 第 8–9a 步应用，`P34` / `A-2-18` / `A-2-22`）

| 字段 | C# 类型 | 缺省（`CarryIn.Empty`） | 读者 | 应用 |
|---|---|---|---|---|
| `Units` | `IReadOnlyList<UnitCarryIn>`（`RosterId` 升序） | 空 | 00 Create 第 8 步、02、03 | 按 `PlacedUnit.RosterId` 匹配实体（`A-4-05`） |
| `Structures` | `IReadOnlyList<StructureCarryIn>`（`StructureId` 序数升序） | 空 | 03 | `Structure.Hp`、`LossHp` |
| `AmmoPool` | `IReadOnlyList<PoolEntry>?`（`WeaponId` 序数升序） | `null` | 03 3.2.1 | 非 null 时**代替** `Meta.AmmoQuota` 作为弹药池（`A-2-14`） |
| `PerLevelUsed` | `IReadOnlyList<PoolEntry>` | 空 | 03 | 各单位该武器 `PerLevelUsedBefore` = 此值 |
| `AlertResponsiveness` | `double?` | `null` | 03 | `Civil.Responsiveness` 初值 |
| `KnownTargets` | `IReadOnlyList<KnownTargetCarry>?` | `null` | 04 | 已知目标清单初值（00 §2.6 / 04 §3.2.7，`A-2-18`） |
| `CommandPointsBonus` | `int` | 0 | 04 | 每夜指挥点 = `Meta.CommandPointsPerNight + CommandPointsBonus`，截断到 `[0, economy.commandPointsPerNight.max]`（`A-2-18`） |
| `FighterSortiesDelta` | `int` | 0 | 03 | 每夜战斗机额度 = `max(0, (Meta.FighterSortiesPerNight ?? min) + delta)`（`A-2-22`） |
| `ActiveSupports` | `IReadOnlyList<string>` | 空 | 03 | 本夜生效的信任度支援（如 `adjacent_sector_coverage`，由 03 在 `Level.Meta.SectorCoverageAnchors` 生成场外虚拟火力单元，`B-T2-89`） |
| `Doctrines` | `IReadOnlyList<string>` | 空 | 02 / 03 / 04 | 已解锁条令 ID（效果由所属规格实现，`B-T2-126`） |
| `Dossier` | `IReadOnlyList<DossierCarryIn>`（`EnemyDefId` 序数升序） | 空 | 02 | 诱饵甄别加成、分类时间倍率 |
| `Adaptation` | `AdaptationCarryIn?` | `null`（全部关闭） | 01、03、04 | 3.12.3 |
| `AutoResolve` | `AutoResolveCarryIn?` | `null` | 03、02 | 自动结算修正（3.8.2，`B-T3-07`） |
| `ResearchEffects` | `IReadOnlyList<ResearchEffectCarryIn>`（`EffectId` 序数升序） | 空 | 02 / 03 | 3.14.2 |

```csharp
public sealed record UnitCarryIn(
    int RosterId, double Exposure, IReadOnlyList<WeaponCarryIn> Weapons,   // Weapons：逐架余弹，覆盖 03 的 RoundsLeft（03 3.2.1，A-4-05）
    bool LightDamaged, double DamageEfficiencyMult, int CrewConsecutiveNights, bool AceCrew,
    int? DeceptionNightsLeft, bool SeenThrough);
public sealed record WeaponCarryIn(string WeaponId, IReadOnlyList<int> LauncherRounds);
public sealed record StructureCarryIn(string StructureId, int Hp, double LossHp);
public sealed record PoolEntry(string WeaponId, int Rounds);
public sealed record KnownTargetCarry(string UnitDefId, Vec2 Pos, double Exposure, int RosterId = 0, bool Priority = false); // 00 §2.6 / 04 §3.2.7（A-2-18、B-T3-05）
public sealed record DossierCarryIn(string EnemyDefId, double DiscriminationAdd, double ClassifyTimeMult);
public sealed record AdaptationCarryIn(double UavAltitudeAddM, bool ForceEvasiveUav,
    IReadOnlyList<Vec2> PriorityPositions, IReadOnlyList<string> ActiveTriggers);   // ActiveTriggers 序数升序
public sealed record AutoResolveCarryIn(double InterceptProbMult, double ExposureGainMult);
public sealed record ResearchEffectCarryIn(string EffectId, double Value);
```

**已知目标跨夜辅助操作 `KnownTargetCarryOps`**（全目录唯一实现位于 `Nightwatch.Sim.Campaign`，已登记到 00 §0.5.1，`A-2-18`、`C-T1-04`）：

```csharp
namespace Nightwatch.Sim.Campaign;
public static class KnownTargetCarryOps
{
    // 判断目标坐标 pos 是否落在已知目标列表任一条目的 scoutedRadiusM（来自 rules/enemy_ai.json knownTargets.dedupeRadiusM）内
    public static bool IsScouted(IReadOnlyList<KnownTargetCarry>? list, Vec2 pos, double scoutedRadiusM)
    {
        if (list == null) return false;
        double r2 = scoutedRadiusM * scoutedRadiusM;
        foreach (var kt in list)
        {
            double dx = kt.Pos.X - pos.X, dy = kt.Pos.Y - pos.Y;
            if (dx * dx + dy * dy <= r2) return true;   // 禁用 Math.Hypot（C-T1-04）
        }
        return false;
    }

    // 单位被毁移除时从已知目标列表中移除对应 RosterId 的条目（注意：不提供 OnUnitRelocated——已知目标坐标是侦察快照，不随我方单位转移而自动跟移，04 §3.2 K2 / A-2-18）
    public static IReadOnlyList<KnownTargetCarry>? OnUnitRemoved(IReadOnlyList<KnownTargetCarry>? list, int rosterId)
        => list == null ? null : list.Where(kt => kt.RosterId != rosterId).ToList();
}
```

`FirstNightAtNewPosition` 不在 `UnitCarryIn` 中：统一经 `PlacedUnit.FirstNightAtNewPosition` 传入 `PlayerUnitCommon.NewPositionPenalty`（00 / 02 / 03 共用，`A-2-13`、`B-T2-06`）。

#### 2.4.2 `CarryOut`（`NightResult.CarryOut`，由 03 `ScoringSystem.BuildResult` 与 04 `EnemyIntelRules.BuildCarryOut` 填写，`P42` / `A-2-20` / `B-T2-36`）

| 字段 | C# 类型 | 来源 |
|---|---|---|
| `Units` | `IReadOnlyList<UnitCarryOut>`（`RosterId` 升序；只含 `RosterId != 0 && !IsVirtualSectorCoverage` 的单位，含已毁快照） | 03 实体状态与 `ScoringState.DestroyedUnitSnapshots` |
| `KnownTargets` | `IReadOnlyList<KnownTargetCarry>?` | 04 `EnemyIntelRules.BuildCarryOut` 导出 |
| `PlayStats` | `PlayStats` | 03 `ScoringState` 按事件累计（`A-2-20`） |
| `KillsByEnemy` | `IReadOnlyList<EnemyCount>`（`EnemyDefId` 序数升序，只含 `Count > 0`） | 03 `ScoringState.KillsByEnemy`（`InterceptResolved{Hit}` 与电子战致坠，按真实目标 `DefId` 计数，3.10.3） |
| `CustomMetrics` | `IReadOnlyList<MetricEntry>`（`Key` 序数升序） | 关卡专用规则与里程碑指标（含 `"urban_nav_jam_triggered"`，`B-T2-36`）；无则空 |
| `StoryChoiceResults` | `IReadOnlyDictionary<string, string>`（`choiceId → optionId`） | 04 剧情二选一结果（`B-T1-16` / `B-T2-102`） |
| `UrbanNavJamTriggered` | `bool` | 02 本夜是否曾在城区开启导航干扰达阈值时长（`B-T2-36`） |

```csharp
public sealed record UnitCarryOut(int RosterId, string UnitDefId, bool Alive, double Exposure, Vec2 Pos,
    IReadOnlyList<WeaponCarryIn> Weapons, bool LightDamaged, double DamageEfficiencyMult, bool RadarDestroyed, int LaunchersLost,
    int Hits, bool SeenThrough);
public sealed record PlayStats(int ArmDetections, int ArmShutdowns, int ThreatsSpawned, int ThreatsEverEwCovered);
public sealed record MetricEntry(string Key, double Value);
public sealed record EnemyCount(string EnemyDefId, int Count);
```

- 已毁单位：`Alive = false`，`Weapons` 为被毁前一刻的余弹（由 03 `ScoringState.DestroyedUnitSnapshots` 保存，用于"随单位损失的库存弹药"，3.3.4，`A-2-20`）。
- `Pos`：夜间转移后的最终位置（白天以此为准；00 §3.5 `UnitCarryOut.FinalPos` 为其同义别名）。
- `RadarDestroyed` / `LaunchersLost`：03 的部件损毁（伤害 5–6 档"摧毁雷达或发射车其一"）；任一非零 → 本文件记为 `Crippled`（3.7.4）。

---

## 3. 算法

> 战役层不在 `SimWorld.Step()` 内，没有 WBS 01.B 序号；"时机"写在每个操作上。所有操作是**同步、确定**的函数：输入 `CampaignState` + 数据 + 动作，输出新状态（原地修改）+ `CampaignEvent` 列表（按产生顺序）。遍历顺序：花名册按 `RosterId` 升序，有序字典按键的序数顺序，数据数组按数据顺序。
> 公共取整函数（`Nightwatch.Sim.Economy.Num`，全目录只此一处）：
> `RoundHalfAway(x) = Math.Round(x, MidpointRounding.AwayFromZero)`；`FloorEps(x) = (int)Math.Floor(x + 1e-9)`；`CeilEps(x) = (int)Math.Ceiling(x − 1e-9)`；`Clamp(v, lo, hi) = Math.Min(hi, Math.Max(lo, v))`。

### 3.1 新战役与随机数

#### 3.1.1 `CampaignOps.NewCampaign(CampaignData data, ulong runSeed, Difficulty difficulty)`

1. `RunSeed = runSeed`（00 Q10：由 `game/` 在"新战役"时用系统随机源生成 8 字节；**模拟层不得自行生成**；测试传固定值）。
2. `Lines = [A, B]`：`Trust = trust.initial`，`Setbacks = 0`，`AceCrews` = `crews.json` 中 `line` 相同的条目（数据顺序）各一项，`Status = NotJoined`、其余 0。
3. `NationalStock[w] = StockEntry(rounds, floor)`（`campaign.json` `nationalStock`；校验 `rounds ≥ floor ≥ 0`，否则 `E_RANGE`；`w` 必须在 `economy.ammoTiers` 中 `replenish = false` 的层，否则 `E_UNKNOWN_REF`）。
4. 其余集合为空，`CurrentLevel = null`。

#### 3.1.2 种子与子流名

| 用途 | 种子 | 消耗 |
|---|---|---|
| 一夜模拟（关键夜、自动结算夜） | `SimRandom.NightSeed(RunSeed, LevelId, index + 1)`，`index` = 该夜在 `flow.nights[]` 中的下标（`Quiet` 也占下标） | 交给 `SimWorld.Create` |
| 奖励卡抽取 | `ChildSeed(RunSeed, $"cards:{LevelId}")` | 每抽一张 1 次 `NextDouble` |
| 王牌阵亡判定 | `ChildSeed(RunSeed, $"crew:{LevelId}:{index + 1}")` | 每个需判定的王牌 1 次 `NextDouble`（王牌 ID 序数顺序） |
| 生产随机事件（M5） | `ChildSeed(RunSeed, $"production:{LevelId}:{day}")` | 每个事件定义 1 次 `NextDouble`（数据顺序） |

- 字符串内的整数用 `CultureInfo.InvariantCulture` 格式化。
- 同一关重试（3.9.3）**使用相同的种子**（关卡同名、下标同号）。
- 00 3.1.5 推荐 `NightSeed(runSeed, level.Id, config.NightIndex)`；本文件改为按 `flow.nights[]` 下标取序号（E 结构多个普通夜复用同一个 `wavesNight`，若用 `NightIndex` 会得到相同种子）。无 `flow.json` 的关卡两者相等（8.3 R-00-3）。

### 3.2 关卡流程状态机（`LevelFlow`）

#### 3.2.1 `StartLevel(levelId)`

前置：`CurrentLevel == null`、`PendingCardOffer == null`、`PendingInterlude == null`、关卡已解锁（3.9.1），否则拒绝 `WrongPhase` / `LevelLocked`。

1. `LevelStartSnapshot = SaveCodec.SerializeState(state with { CurrentLevel = null, LevelStartSnapshot = null })`（3.15.1 的规范序列化）。
2. 加载 `LevelData`（00 `DataLoader.LoadLevel`）与 `LevelFlowDef`（1.4，含缺省流程）。
3. 本关涉及的线（A / B / AB → 两条）：`EmergencyGrantedThisLevel = false`；`crews.json` 中 `joinLevel ≤ Number` 且 `Status == NotJoined` 的王牌 → `Available`（`AceCrewJoined`）；所有王牌 `ConsecutiveNights = 0`、`LastFoughtDay = 0`。
4. `CurrentLevel = new LevelRunState { Attempt = 1（重试时由 3.9.3 设置）, Phase = Briefing, Day = 3.2.3 的初值, NextNightIndex = 0 }`。
5. 开局资源（3.3）。
6. 发出 `LevelStarted { LevelId, Attempt }`。

#### 3.2.2 阶段转移与 `Advance()`

| 当前阶段 | 动作 / 触发 | 结果 |
|---|---|---|
| `Briefing` | `AcknowledgeBriefing` | 结构 E：`Phase = Deployment`，`InitialPlacement = true`（只放置单位、不开始夜晚）；其他结构：`Advance(FromStart)` |
| `Deployment`（`InitialPlacement`） | `ConfirmDeployment(plan)` | 应用 3.7.1 的放置部分（不装填、不准备夜晚），`InitialPlacement = false`，`Advance(FromStart)` |
| `Deployment` | `ConfirmDeployment(plan)` | 3.7.1 → `Phase = Night`，宿主取 `PrepareNight()` 创建 `SimWorld` |
| `Night` | `ApplyNightResult(r)` | 3.7.4 → `Phase = Review` |
| `Review` | `AcknowledgeReview` | 关卡结束（3.2.5）→ `Completed` / `Failed`；否则 `Advance(FromReview)` |
| `Day` | `EndDay` | `Advance(FromDay)` |

```
Advance(from):
    n = flow.nights[NextNightIndex]
    if Day < n.Day:
        if dayPhase == None:            Day = n.Day; Dispatch(n); return            # A / B 实际不会走到
        g = (TimeStructure == E) ? 1 : n.Day − Day                                   # E 逐日，C / D 一次跨过整个间隔
        DayStep(g); OpenDay(); return
    if from ∈ {FromReview, FromQuiet} and dayPhase != None and 上一个已处理条目的 Day == Day:
        OpenDay(); return                                                            # 同日两段之间（第 18 关黄昏补给）：不流逝时间，只开白天
    Dispatch(n)

Dispatch(n):
    switch n.Kind:
        Key:                     Phase = Deployment
        Auto and WatchNext:      WatchNext = false; Phase = Deployment                # 亲自观看
        Auto:                    AutoResolveNight()  → Phase = Review                 # 3.8.2
        Quiet:                   3.7.4 第 11、12 步；NextNightIndex += 1；
                                 if NextNightIndex == flow.nights.Count: 关卡结束判定（3.2.5）
                                 else: Advance(FromQuiet)

OpenDay(): 3.2.4 第 9–10 步（时间槽、运力）；检查紧急支援（3.6）；Phase = Day
```

- 结构 A / B：`Briefing → Deployment → Night → Review → Completed / Failed`。
- 结构 C / D：每个间隔一次 `DayStep(g)`、一个 `Day` 阶段（GDD 11.2"白天单一管理界面，跳过的天数用文字交代"）；D 的白天缺省为 `Interlude`（只有时间槽，补给窗口按 `supplyWindows`）。
- 结构 E：日历逐日推进，每天一个 `Day` 阶段（GDD 11.4"每天简短经营回合"）；没有夜晚条目的日子只有白天。
- `WatchNext`：由 `WatchAutoNight(bool)` 设置。`InitialPlacement`（`bool`，`LevelRunState` 字段）。
- 进入 `Deployment`（非 `InitialPlacement`）时同样检查紧急支援（3.6）。

#### 3.2.3 日历起点

`Day` 初值：结构 E 为 0（第一次 `DayStep(1)` 进入第 1 天）；其他结构为 `flow.nights[0].Day`（第一夜所在日）。之前的日子不模拟：开局资源（3.3）已把"开局前的积累"折算进 `cityResource.startDays`。剧本增援 `day ≤ 初值` 的在开局加入。

#### 3.2.4 `DayStep(g)`（`g ≥ 1` 天流逝；固定顺序。第 1–8 步属于 `DayStep`，第 9–10 步为 `OpenDay()`，由 `Advance` 紧接着调用）

设 `prev = Day`，`a = LastAlertFrac`（本关尚无已结算夜晚时为 0）；`a` 只作用于 `g` 天中的第一天。

1. `Day = prev + g`。
2. 城市资源积累（3.5.1）。
3. 白天暴露度衰减：每个花名册单位 `Exposure = Max(0, Exposure − relocation.dayExposureDecayPerDay × g)`。
4. 保护目标修复：对 `Structures` 中 `!Destroyed` 的每项：`add = FloorEps(MaxHp × repair.structureHpFracPerDay × g)`；`Hp = Min(MaxHp, Hp + add)`；`LossHp = Max(0, LossHp − add)`；`Hp == MaxHp` 时移除该项（= 满血）。`MaxHp` 取自关卡数据。被毁者本关不修复。
5. 单位维修：`RepairDaysLeft > 0` 的单位 `RepairDaysLeft = Max(0, RepairDaysLeft − g)`；变为 0 时：`Condition = Intact`、`DamageEfficiencyMult = 1.0`；若原为 `Crippled`：每个武器的发射架数恢复为 `LauncherCount(def)`（新增发射架 `RoundsLeft = 0`）。发出 `UnitRepaired`。
6. 生产、飞手训练、研发：`ProductionRules.Advance(g, a)`、`ResearchRules.Advance(g)`（3.13、3.14；无则跳过）。
7. 到达：`PendingArrivals` 中 `AvailableFromDay ≤ Day` 的项（申请顺序）→ 3.4.5 第 7 步加入；剧本增援 `prev < r.Day ≤ Day` → 加入花名册（`Source = Scripted`、`ReturnAfterNightIndex` 按 2.3 换算）。各发 `ReinforcementArrived`。
8. 大空袭预警（3.8.4）。
9. 归零当日计数：`TimeSlotsLeft = 0`、`LogisticsLeft = 0`（第 10 步重新给）。
10. 开白天（`OpenDay`）：`TimeSlotsLeft = relocation.timeSlotsPerDay`；`LogisticsLeft = 窗口运力 × (1 + ResourceMods["logistics"]) + RepairTeams × logisticsAdd`。"窗口运力"：有 `supplyWindows` 时 = 所有 `w.Day ≤ Day`、`w.AfterNight == null || NextNightIndex > w.AfterNight`、且下标不在 `ConsumedWindows` 中的窗口 `Logistics` 之和，并把这些下标加入 `ConsumedWindows`（C 结构一个白天可一次领到间隔内的多个窗口；第 18 关的黄昏窗口用 `afterNight` 指定在白天战斗段之后）；无该数组时 `dayPhase == Full` → `supply.logisticsPerWindow`，`Interlude` → 0。

#### 3.2.5 关卡结束判定（`Review` 阶段确认时）

1. 本夜 `Kind == Key`（含"观看"的普通夜）且 `Outcome == Defeated` → `Failed`。
2. 否则若 `NextNightIndex == flow.nights.Count` → 判定胜利条件：
   - `survive_nights{n}`：本关 `Kind == Key` 且 `Outcome == Survived` 的夜数 ≥ `n`。
   - `survive_game_sec{sec}`：`Σ_{Key 夜} (Outcome == Survived ? NightDef.DurationSec : EndTimeSec) ≥ Sec`（`AllClear` 提前结束视为撑满）。
   - 全部满足 → `Completed`，否则 `Failed`。
3. 否则未结束。
4. 普通夜（自动结算）以 `Defeated` 结束**不导致关卡失败**，只计为挫折（3.6；待决 Q-F3）。
5. `Completed` / `Failed` 时执行信任度关卡结算（3.4.4），然后 3.9.2 / 3.9.3。

### 3.3 开局资源（`EconomyRules.SetupLevel`）

#### 3.3.1 待生效效果与比例修正

1. 收集 `PendingEffects` 中 `TargetLevel == Number`，或 `TargetLine ∈ 本关线集合 且 TargetLevel == null` 的项（追加顺序）为 `E`，并从 `PendingEffects` 移除。线集合：A → {A}；B → {B}；AB → {A, B}。`Number == null`（测试关卡）不消耗任何待生效效果。
2. 叙事难度（`Difficulty == Narrative`，GDD 14"关闭负面跨关影响"）：从 `E` 中丢弃"负面"效果：`AmmoFrac / CityResourceFrac / LogisticsFrac` 的 `frac < 0`；`UnitCountDelta / FighterSortiesDelta / CommandPointsDelta` 的 `delta < 0`；`TrustDelta` 的 `delta < 0`。
3. 信任度修正（`TrustRules.QuotaMod`）：

   ```
   T = 本关线的 Trust（AB：两条线 Trust 的算术平均）
   if T ≥ neutral: mT = (T − neutral) / (max − neutral) × quotaModMaxFrac
   else:           mT = −((neutral − T) / (neutral − min)) × quotaModMaxFrac
   叙事难度：mT = Max(0, mT)；信任度未启用（3.4.1）：mT = 0
   ```

4. 比例修正键与求和（每个键各自求和后夹紧到 `[crossLevelModClamp.min, crossLevelModClamp.max]`，写入 `ResourceMods`）：

   | 键 | 求和项 |
   |---|---|
   | `ammo:<w>`（每种**配额级**武器，3.3.3） | `mT` + `E` 中 `AmmoFrac(weapon = w)` 的 `frac` |
   | `city` | `mT` + `E` 中 `CityResourceFrac` 的 `frac` + 城市记忆加成（3.10.4） |
   | `logistics` | `mT` + `E` 中 `LogisticsFrac` 的 `frac` |

5. `CommandPointsBonusLevel = Σ CommandPointsDelta`；`FighterSortiesDelta = Σ FighterSortiesDelta`。
6. 其余效果在 3.3.2–3.3.7 的对应步骤中按 `E` 的顺序应用；`UnlockDoctrine / AceCrewsJoin / Favor / TrustDelta / SetFlag` 在第 3.3.7 步应用。

#### 3.3.2 花名册

1. 对 `Meta.AvailableUnits` 每项（数据顺序），`src = Source ?? Quota`：
   - `count' = Count + Σ E.UnitCountDelta(unit)`；`Count ≥ 1` 时 `count' = Max(1, count')`（GDD 12.3"所有武器一周目都能用到"），否则 `Max(0, count')`。
   - 历史事件 `unit_unavailable` 对该单位 `Active` → 跳过，发 `HistoricalRestrictionApplied { EventId, UnitId }`（数据校验工具 WS06-004 应对此报警告）。
   - `src == City`：**不加入**花名册；`count'` 记为该单位的城市商店上限（3.5.2）。
   - `src ∈ {Quota, Stock}`：加入 `count'` 个 `RosterUnit`（`Source = src`，`Condition = Intact`，`DamageEfficiencyMult = 1.0`，`Exposure = 0`，`PositionKind = Initial`，`Pos = null`，`Deployed = false`，武器按 `WeaponIds` 建立、发射架 `RoundsLeft = 0`，待 3.3.3 装填）。
2. `E` 中每个 `GrantUnit`：加入 `count` 个单位（`Source = Effect`，`Condition = condition ?? Intact`，`Tag = tag`，`NightsLeft = nights`，`DamageEfficiencyMult = condition == LightDamaged ? 03 轻伤倍率 : 1.0`），其弹药 = 满弹仓 × `ammoFrac ?? 1.0`（每个发射架 `RoundHalfAway(cap × ammoFrac)`），**不**从配额池扣、不受比例修正。`Crippled` 的单位先需维修（3.7.2）。
3. 剧本增援 `day ≤ Day`（3.2.3）。
4. 每加入一个单位（任何来源，含之后的购买、到达）：`k` = 本关此前加入过的同 `UnitDefId` 单位数（含已移除）；若 `rosterTags` 有 `(UnitDefId, k)` → `Tag = tag`。
5. `RosterId` 依加入顺序从 `NextRosterId` 分配。

#### 3.3.3 弹药（配额级）

"配额级武器" = 花名册中火力单元的武器，且**不是**本关适用的全国库存武器（3.3.4）。对每种配额级武器 `w`（武器 ID 序数顺序）：

```
cap(u, w)  = (def.Kind == Gun ? def.MagazineRounds : def.Magazine)；null → 不计数，跳过该武器
launch(w)  = def.Kind == Gun ? 1 : (def.Launchers ?? engagement.defaultLaunchers)      # 03 的 LauncherCount
base       = Meta.AmmoQuota 含 w ? 其 Count : Σ_{u ∈ 开局花名册中 Source ∈ {Quota, Stock} 且有 w} cap(u,w) × launch(w)
m          = ResourceMods["ammo:" + w]
alloc      = base ≥ 1 ? Max(1, RoundHalfAway(base × (1 + m))) : 0
若历史事件 resupply_mult 对 w Active：alloc = FloorEps(alloc × mult)
ResourceBase[w] = base
装填：按 RosterId 升序、武器顺序、发射架顺序，每个发射架 take = Min(cap, 剩余)；剩余放入 Depot[w]
```

- `GrantUnit` 带来的弹药已在 3.3.2 装好，不计入 `base`，也不参与装填分配。
- `Meta.AmmoQuota` 中出现、但花名册中没有对应武器的条目：`alloc` 照算，全部放入 `Depot`（可能由后到的单位使用）。

#### 3.3.4 全国共享库存（苏制导弹，GDD 9.6"只减不增"、13.3"有保底"）

适用条件：本关 `Protagonist ∈ {A, AB}` 且武器 `w` 属于 `economy.ammoTiers` 中 `replenish = false`、`sharedBy = line_a` 的层，且 `NationalStock` 含 `w`。不适用（B 线关卡）时 `w` 按配额级处理。

```
req   = Meta.AmmoQuota 含 w ? Count : Σ cap × launch（同 3.3.3 的 base 算法）
issue = Min(req, NationalStock[w].Rounds)          # 不受比例修正、不受 resupply_mult
装填同 3.3.3；剩余放入 Depot[w]
```

- **库存只在"使用"时减少**（发放不减）：每夜结束 `Used(w) = Ammo.Weapons[w].Shots + Σ_{本夜被毁单位} 其该武器余弹`；`Rounds = Max(Floor, Rounds − Used(w))`（3.7.4 第 6 步）。
- 本关持有量 `Held(w) = Σ 花名册该武器各发射架余弹（≥ 0 者） + Depot[w]`。不变量：`Held(w) ≤ Rounds`（6.1）。
- 白天从库存补给：可补数 = `Rounds − Held(w)`（3.7.2）。
- 关卡结束时持有的库存弹药不需"归还"（从未扣减）。
- `hasFloor = false` 的层：`Floor` 视为 0。

#### 3.3.5 历史事件强制配额（`economy.historicalEvents`，`Active` 已由加载器按关卡日期解析）

| `effect` | 作用点 | 规则 |
|---|---|---|
| `unit_unavailable`（`unit`） | 开局花名册（3.3.2）、城市商店（3.5.2）、信任度申请（3.4.5）、`GrantUnit` 效果、奖励卡（3.11 资格） | 该单位不得以任何途径进入本关花名册；对应动作拒绝 `HistoricallyUnavailable`；`GrantUnit` 效果被丢弃并发 `HistoricalRestrictionApplied` |
| `resupply_mult`（`weapon`, `mult`） | 开局配额分配（3.3.3）、白天补给（3.7.2）、弹药类申请（3.4.5） | 数量 `FloorEps(n × mult)`；结果为 0 的白天补给 / 申请拒绝 `HistoricallyUnavailable`。不作用于全国库存层、不作用于已持有弹药 |

#### 3.3.6 测试关卡（`Number == null`）

信任度启用；城市资源按 `cityResourcePerDay`；不消耗、不产生待生效效果；不触发奖励卡、插曲、跨关节点、城市记忆；敌人适应只读不写。

#### 3.3.7 其余开局项

1. `CityResource`（3.5.1）。
2. `SurveyedPositions` = 关卡 `deploy.alternatePositions` 中 `surveyed == true` 的 ID ∪ `E.SurveyedPositions` 的合计 `count` 个"未勘察"备用阵地（数据顺序取前 `count` 个）。
3. `UnlockDoctrine` → 目标线 `Doctrines.Add`（`DoctrineUnlocked`）；`AceCrewsJoin(count)` → 目标线前 `count` 个 `NotJoined` 王牌 → `Available`；`Favor` → 3.10.5；`TrustDelta` → `Trust = Clamp(Trust + delta, min, max)`（`TrustChanged{Cause = Effect}`）；`SetFlag` → `Flags[key] = value`；`ProductionLineStart` → 3.13；`ReturnDeadlineExtend(unit, nights)` → 花名册中该单位 `ReturnAfterNightIndex += nights`（对剧本增援在加入时同样生效：记入 `LevelRunState.DeadlineExtensions[unit]`，加入时加上）。
4. `Structures` 空（满血）；`KnownTargets = null`；`AlertResponsiveness = 1.0`。
5. 生产 / 研发初始化（3.13、3.14；`flow.production == null` 时 `Production = null`）。

### 3.4 信任度（`TrustRules`）

#### 3.4.1 启用条件

`TrustEnabled(level) = level.Number == null || level.Number ≥ trust.availableFromLevel`（GDD 12.3：交换比与信任度第 6 关引入）。未启用时 3.4.2–3.4.4 全部跳过（`TrustDelta = 0`），3.4.5 的申请拒绝 `NotYetAvailable`。

#### 3.4.2 一夜结算 `TrustRules.ForNight(NightResult r, IReadOnlyList<ObjectiveDef> objectives, GameCatalog cat)`

```
# 1) 交换比档位
if r.Exchange.ExchangeRatio == null or r.Exchange.TotalShotCostMusd < minShotCostForExchangeMusd: dEx = 0
else: dEx = bands 中 minRatio ≤ ratio 的最后一项的 delta        # bands 按 minRatio 严格升序，第一项 minRatio 必须为 0（加载校验）

# 2) 浪费型武器（GDD 9.3 "用 PAC-3 打 Shahed"）
W = 0
for x in r.Exchange.ByWeapon（序数顺序）:
    if x.Shots == 0: continue
    avg = x.ShotCostMusd / x.Shots
    ratio = x.Ratio ?? 0
    if avg ≥ wastefulWeapon.minAvgShotCostMusd and ratio < wastefulWeapon.maxRatio: W += x.Shots
dWaste = −Min(W × penaltyPerShot, maxPenaltyPerNight)

# 3) 指挥部质询
inquiry = W ≥ inquiry.minWastefulShots
dInq = inquiry ? −inquiry.penalty : 0

# 4) 囤弹放行（GDD 9.3 "让高威胁目标突防但昂贵弹药仍有剩余"；03 已统计）
dHoard = −Min(r.Losses.HighThreatLeaksWithReserve × hoardedLeak.penaltyPerLeak, hoardedLeak.maxPenaltyPerNight)

# 5) 上级目标（scope == Night 的目标，数据顺序）
dObj = Σ (Holds(o, r) ? o.TrustOnSuccess : o.TrustOnFail)

raw = dEx + dWaste + dInq + dHoard + dObj
applied = Clamp(raw, nightDeltaClamp.min, nightDeltaClamp.max)
```

`Holds(o, r)`：

| `Type` | 成立条件 |
|---|---|
| `WeightedLossAtMost` | `r.Losses.WeightedLossFrac ≤ o.Fraction + 1e-12` |
| `StructureIntact` | `r.Losses.Structures` 中 `StructureId == o.StructureId` 的项 `Destroyed == false` |
| `UrbanInterceptRatioAtMost` | `r.Debris.UrbanInterceptRatio == null` 或 `≤ o.Fraction + 1e-12` |
| `LeaksAtMost` | `r.Losses.ThreatsImpacted ≤ o.Count` |

应用：对本关线集合中的每条线 `L`：`L.Trust = Clamp(L.Trust + applied, min, max)`；发出 `TrustChanged { Line, Before, After, Cause = Night }`；`inquiry` 为真时另发 `InquiryTriggered { NightIndex, WastefulShots = W }`（由叙事层显示质询事件）。

- 自动结算夜照常结算；被"观看"的普通夜在 `applied` 之后另加 `autoResolve.watchTrustBonus`（再夹紧到 `[min, max]`，`Cause = WatchBonus`）。
- `Breakdown = TrustBreakdown(dEx, dWaste, dInq, dHoard, dObj, raw, applied)` 存入 `NightRecord`（复盘界面显示）。

#### 3.4.3 关卡目标（`scope == Level`）

在关卡结束（3.2.5）时用**最后一个已结算夜**的 `NightResult` 求 `Holds`，`Σ` 结果计入 3.4.4。

#### 3.4.4 关卡结算

`dLevel = (Completed ? levelVictoryBonus : −levelDefeatPenalty) + Σ 关卡目标`；对线集合中每条线 `Trust = Clamp(Trust + dLevel, min, max)`（`Cause = Level`），**不**受 `nightDeltaClamp` 约束。重试同一关时，失败时扣的 `levelDefeatPenalty` 不随快照恢复而撤销（3.9.3）。

#### 3.4.5 申请增援 `RequestReinforcement(requestId, Line? paidBy)`

目录 = `economy.requests[]` ∪ `support.json` 中 `cost.trust != null` 的条目（ID 即支援 ID；`kind` 由 `effect` 决定：`reinforcement` → `unit`（`unit = reinforcementUnit`、`count = reinforcementCount`、`durationNights = duration.nights`），`sector_coverage` → `support`；`arrivalDays`：`delay.kind == next_day` → 1，`instant` → 0；`firstAvailableLevel = firstAvailable.level`）。

1. 阶段 ∈ {`Deployment`, `Day`}，否则 `WrongPhase`。
2. 信任度启用（3.4.1），否则 `NotYetAvailable`。
3. `firstAvailableLevel`：`Number != null && Number < firstAvailableLevel` → `NotYetAvailable`。`line` 非空且不在本关线集合 → `NotAvailable`（00 公共原因）。
4. 付款线：本关单线 → 该线（`paidBy` 必须为 null 或相同）；AB → `paidBy` 必填，否则 `InvalidArgument`。
5. 历史事件：`unit` 类且 `unit_unavailable` Active → `HistoricallyUnavailable`；`ammo` 类且 `resupply_mult` Active → `count = FloorEps(count × mult)`，为 0 → `HistoricallyUnavailable`。
6. `cost = trust.requestCost[trustCost]`；`Trust − cost < trust.min − 1e-9` → `InsufficientTrust`。否则 `Trust −= cost`（`TrustChanged{Cause = Request}`），`PendingArrivals.Add(new PendingArrival(id = 关卡内自增, requestId, unit, weapon, count, AvailableFromDay = Day + arrivalDays, durationNights, paidBy))`。
7. **到达**（`arrivalDays == 0` 时立即执行，否则在 `DayStep` 第 7 步）：`unit` → 加入 `count` 个单位（`Source = Request`、满弹仓、`NightsLeft = durationNights`、`AvailableFromDay`）；`ammo` → `Depot[weapon] += count`；`support` → `ActiveSupports.Add(new ActiveSupport(id, durationNights ?? 1))`。从 `PendingArrivals` 移除。
8. 可用性：单位只能在 `n.Day ≥ AvailableFromDay` 的夜晚部署（`Deployment` 阶段当天申请、`arrivalDays = 1` 的单位赶不上当夜）。

### 3.5 城市资源（`CityRules`）

#### 3.5.1 积累

```
p = Meta.CityResourcePerDay；p == null → CityResource 恒为 0，商店动作拒绝 NotAvailable
m = ResourceMods["city"]
开局：CityResource = Min(cap, p × startDays × (1 + m))
DayStep(g)：CityResource = Min(cap, CityResource + p × (1 + m) × Max(0, g − alertPauseWeight × a))
```

`a` 见 3.2.4（上一夜警报时长占比；GDD 8.6"警报暂停积累"——只折减夜晚那一天的一部分，`alertPauseWeight` = 夜晚在一天积累中的权重）。

#### 3.5.2 购买 `BuyCityItem(itemId)`

1. 阶段 ∈ {`Deployment`, `Day`}；`p != null`；否则 `WrongPhase` / `NotAvailable`。
2. 条目 `kind == unit`：本关 `availableUnits` 必须有 `(unit, source = city)` 项，否则 `NotAvailable`；上限 = 该项的 `count'`（3.3.2）；`CityPurchases[itemId] ≥ 上限` → `CapReached`；`until` 非空且关卡年月 ≥ `until` → `HistoricallyUnavailable`；`unit_unavailable` Active → 同。
3. 条目 `kind == repair_team`：`CityPurchases[itemId] ≥ perLevelCap` → `CapReached`。
4. `CityResource + 1e-9 < cost` → `InsufficientCityResource`。
5. 应用：`CityResource −= cost`（结果 < 0 时置 0）；`CityPurchases[itemId] += 1`；`unit` → 加入 1 个单位（`Source = City`、满弹仓、`AvailableFromDay = Day`）；`repair_team` → `RepairTeams += 1`，并立即 `LogisticsLeft += logisticsAdd`（仅 `Day` 阶段）。发出 `CityResourceChanged`。

### 3.6 挫折与紧急支援（GDD 9.5 防死亡螺旋）

每夜结算后（3.7.4 第 10 步），对本关线集合中每条线：

```
setback = (r.Outcome == Defeated) or (r.Losses.WeightedLossFrac ≥ emergencySupport.setbackWeightedLossFrac − 1e-12)
if setback: L.Setbacks += 1 else: L.Setbacks = 0
```

触发（在下一次进入 `Deployment` 或 `Day` 阶段时检查，含重试后的第一次 `Deployment`）：`L.Setbacks ≥ triggerSetbacks` 且 `!L.EmergencyGrantedThisLevel` →

1. 按 `emergencySupport.grants` 顺序应用（`At = Immediate`）：`command_points_delta` → `CommandPointsBonusNext += delta`；`ammo_frac_immediate` → 对每个配额级武器 `w`（序数顺序）`Depot[w] += RoundHalfAway(ResourceBase[w] × frac)`；`trust_raise_to` → `Trust = Max(Trust, value)`；`grant_unit` → 加入单位（`Source = Emergency`）。
2. `L.EmergencyGrantedThisLevel = true`；`L.Setbacks = 0`；发出 `EmergencySupportGranted { Line }`。

AB 关卡两条线各自判定，但同一次检查中只应用一次 `grants`（两线都满足时按 A 处理并把两线都标记为已发放）。

### 3.7 一夜的准备与结算

#### 3.7.1 `ConfirmDeployment(plan)` 与 `PrepareNight()`

`plan`：`IReadOnlyList<DeployEntry(int RosterId, Vec2 Pos, string? AlternatePositionId, UnitSettings Settings)>`。

校验（任一失败 → 拒绝，状态不变）：

1. 阶段 `Deployment`，否则 `WrongPhase`。
2. 每个 `RosterId` 存在，否则 `UnknownRosterUnit`；不重复，否则 `InvalidArgument`。
3. 单位可用：`AvailableFromDay ≤ n.Day`、`RepairDaysLeft == 0`、`Condition != Crippled`；否则 `UnitUnavailable`。
4. 位置：已放置（`Pos != null`）的单位，`plan.Pos` 必须等于 `Pos`（逐分量 `==`），否则 `PositionChangeRequiresRelocation`——**例外**：本关尚未结算过任何夜晚时，可自由改变位置（GDD 11.3"关卡开始前的部署无惩罚"）。
5. 飞手（3.13.3）：部署的拦截无人机班组数 × `pilotsPerTeam` ≤ `Pilots`（仅 `Production != null`），否则 `NoPilots`。
6. 构造 `DeploymentPlan` 后调用 04 `DeploymentValidator.Validate(level, plan)`；有错误 → `InvalidDeployment`（错误列表附在拒绝事件中）。

应用：

1. 列出的单位 `Deployed = true`，其余 `false`；`Settings` 保存。
2. 首次放置（`Pos == null`）：`Pos = plan.Pos`、`AlternatePositionId = plan.AltId`；若本关尚未结算过夜晚 → `PositionKind = Initial`、`FirstNightAtNewPosition = false`；否则：`AltId ∈ SurveyedPositions` → `Surveyed`、false；其他 → `New`、`true`（新到单位进入未勘察阵地同样有首夜惩罚，待决 Q-F6）。
3. 夜前装填：对 `Deployed` 的火力单元（`RosterId` 升序、武器顺序、发射架顺序）：`take = Min(cap − RoundsLeft, Depot[w])`，`RoundsLeft += take`，`Depot[w] −= take`（`cap` 不计数的跳过）。
4. 阶段 → `Night`，并由 `PrepareNight()` 返回 `NightSetup(LevelData, SimConfig, ulong Seed)`：

```
n = flow.nights[NextNightIndex]
Seed = NightSeed(RunSeed, LevelId, NextNightIndex + 1)
Deployment = Deployed 的单位按 RosterId 升序 → PlacedUnit { UnitDefId, Pos, AlternatePositionId, Settings,
             RosterId, FirstNightAtNewPosition }
SimConfig { NightIndex = n.WavesNight, Deployment, CarryIn = BuildCarryIn(n), EndWhenClear = 00 缺省 }
```

`BuildCarryIn(n)`：

| 字段 | 值 |
|---|---|
| `Units[i]` | 每个 `Deployed` 单位：`Exposure`；`Weapons` = 各发射架 `RoundsLeft`；`LightDamaged = Condition == LightDamaged`；`DamageEfficiencyMult`；`CrewConsecutiveNights = TonightCrewNights(u, n.Day)`（3.7.5）；`AceCrew = AceId != null`；`DeceptionNightsLeft = NightsLeft`（仅欺骗单位）；`SeenThrough` |
| `Structures` | `Structures` 中每项 → `(id, Hp, LossHp)`（满血者不列出） |
| `AmmoPool` | `Depot` 的全部条目（含 0） |
| `PerLevelUsed` | `PerLevelUsed` 的全部条目 |
| `AlertResponsiveness` | `AlertResponsiveness` |
| `KnownTargets` | `KnownTargets`（加上 3.12.3 的优先打击位置、3.13.2 的生产设施目标由 04 接口写入的结果） |
| `CommandPointsBonus` | `CommandPointsBonusLevel + CommandPointsBonusNext`（使用后 `CommandPointsBonusNext = 0`） |
| `FighterSortiesDelta` | `FighterSortiesDelta` |
| `ActiveSupports` | `ActiveSupports` 的 ID（获得顺序） |
| `Doctrines` | 线集合中各线 `Doctrines` 的并集（序数升序） |
| `Dossier` | 3.10.3 |
| `Adaptation` | 3.12.3 |
| `AutoResolve` | 关键夜 / 观看的普通夜 → `null`；自动结算 → 3.8.2 |
| `ResearchEffects` | 3.14.2 |

#### 3.7.2 白天动作（阶段 `Day`）

**补给 `Resupply(weaponId, count)`**：

1. `count ≥ 1`，且花名册中至少一个火力单元有该武器，否则 `InvalidArgument`。
2. 全国库存层（3.3.4 适用）：`count > Rounds − Held(w)` → `InsufficientStock`；`d = count`。
3. 配额级：`d = resupply_mult Active ? FloorEps(count × mult) : count`；`d == 0` → `HistoricallyUnavailable`；`L = resupplyLimits[w] ?? ResourceBase.GetValueOrDefault(w, 0)`；`ResupplyDelivered[w] + d > L` → `CapReached`。
4. `cost = d × RoundCost(w)`，`RoundCost(w) = supply.roundCostByWeapon[w] ?? supply.roundCostByAmmoSupply[def.AmmoSupply]`；`LogisticsLeft + 1e-9 < cost` → `InsufficientLogistics`。
5. 应用：`LogisticsLeft −= cost`；`Depot[w] += d`；配额级 `ResupplyDelivered[w] += d`。

**维修 `RepairUnit(rosterId)`**：`Condition == Intact` → `UnitNotDamaged`；`RepairDaysLeft > 0` → `InvalidState`（已在维修）；`cost = LightDamaged ? repair.lightLogistics : repair.crippledLogistics`；运力不足 → `InsufficientLogistics`；应用：`LogisticsLeft −= cost`，`RepairDaysLeft = lightDays / crippledDays`。维修中的单位不能部署（3.7.1 第 3 条），在 `DayStep` 第 5 步完成。

**转移 `RelocateUnit(rosterId, Vec2 pos, string? altId)`**（GDD 11.3"白天转移消耗时间槽"）：

1. 单位已放置（`Pos != null`），否则 `InvalidState`；`def.DeploySec` 与 `def.PackSec` 都非 null 且 `Mobility != Fixed`，否则 `CannotRelocate`。
2. `altId` 非空时必须存在于 `deploy.alternatePositions`，且 `pos` 必须等于其 `Pos`，否则 `InvalidArgument`；位置合法性由 04 `DeploymentValidator.ValidatePosition(level, unitDefId, pos)` 判定，非法 → `InvalidArgument`。
3. 时间槽：

   ```
   surveyed = altId != null && SurveyedPositions.Contains(altId)
   deploy   = def.DeploySec × (surveyed ? positions.preparedAlternate.deployTimeMult : 1.0)
   slots    = Max(1, CeilEps((def.PackSec + deploy) / (relocation.slotGameSec × conventions.gameSecToWorldSec)))
   ```

   `TimeSlotsLeft < slots` → `InsufficientTimeSlots`。
4. 应用：`TimeSlotsLeft −= slots`；`scouted = KnownTargets?.IsScouted(pos) ?? false`；`Exposure = ExposureRules.Relocated(Exposure, scouted)`（02 3.6.3 同一函数：`scouted ? e × onRelocate.toScoutedPositionMult : onRelocate.resetTo`）；`Pos = pos`；`AlternatePositionId = altId`；`PositionKind = surveyed ? Surveyed : New`；`FirstNightAtNewPosition = !surveyed`；`NightsAtPosition = 0`；`KnownTargets?.OnUnitRelocated(rosterId, pos)`；发出 `UnitRelocated { RosterId, Slots }`。

**勘察 `SurveyPosition(altId)`**：`Number != null && Number < positions.preparedAlternate.availableFromLevel` → `NotYetAvailable`；`altId` 不存在 → `InvalidArgument`；已在 `SurveyedPositions` → `AlreadySurveyed`；`TimeSlotsLeft < relocation.surveyTimeSlots` → `InsufficientTimeSlots`；应用：扣槽、`SurveyedPositions.Add(altId)`。勘察对已在该阵地的单位不追溯（其 `FirstNightAtNewPosition` 不变）。

**王牌配属 `AssignAceCrew(aceId, rosterId)`**（阶段 `Deployment` 或 `Day`）：王牌属于本关线集合，`Status == Available`，否则 `AceUnavailable`；`rosterId == 0` → 解除该王牌的配属；否则单位的 `UnitDefId ∈ crews.json eligibleUnits`，否则 `AceNotEligible`；应用：该王牌原单位 `AceId = null`；目标单位原有王牌被解除；目标 `AceId = aceId`。

**观看 `WatchAutoNight(bool)`**：下一夜（`flow.nights[NextNightIndex]`）为 `Auto` 时设置 `WatchNext`，否则 `InvalidState`。

**结束白天 `EndDay`**：无条件（剩余时间槽、运力作废）。

#### 3.7.3 指挥点

本文件只提供 `CarryIn.CommandPointsBonus`；扣除与上限由 04 实现（`economy.commandPointsPerNight.max` 为每夜上限）。

#### 3.7.4 `ApplyNightResult(NightResult r)`（阶段 `Night`，或自动结算内部调用）

固定顺序：

1. 校验 `r.LevelId == LevelId`、`r.NightIndex == n.WavesNight`，否则抛 `InvalidOperationException`（宿主错误，不是玩家动作）。
2. **单位**：对 `r.CarryOut.Units` 每项（`RosterId` 升序），找花名册单位 `u`（找不到 → 抛异常）：
   - `!Alive`：若 `u.AceId != null` → 加入"待判定王牌"列表；`KnownTargets?.OnUnitRemoved(u.RosterId)`；从花名册移除（`RosterUnitLost { RosterId, UnitDefId }`）。
   - `Alive`：`Exposure`；`Pos`（若与夜前不同 → `NightsAtPosition = 1`，`AlternatePositionId` = `Pos` 恰等于某备用阵地坐标时为其 ID，否则 null；相同 → `NightsAtPosition += 1`）；`Weapons` 逐架余弹（发射架数以 `CarryOut` 为准）；`LightDamaged → Condition = LightDamaged`、`DamageEfficiencyMult`；`RadarDestroyed || LaunchersLost > 0 → Condition = Crippled`（优先于轻伤）；`LevelHits += Hits`，王牌 `Xp += Hits × crew.xpPerHit`；`SeenThrough`；`FirstNightAtNewPosition = false`（首夜已过）。
3. **王牌判定**（3.7.5）。
4. **班组夜数**：本夜 `Deployed` 的每个单位（含已毁者，在移除前记下）：班组 `c`（王牌或单位本身）`c.ConsecutiveNights = TonightCrewNights(u, n.Day)`、`c.LastFoughtDay = n.Day`；本关线集合中**未参战**的王牌与花名册中未部署的单位：`ConsecutiveNights = 0`。受伤王牌 `WoundedNightsLeft −= 1`，为 0 → `Available`（`AceCrewRecovered`）。
5. **保护目标**：对 `r.Losses.Structures` 每项：`HpEnd == MaxHp` → 移除；否则 `Structures[id] = (HpEnd, LossHp, Destroyed)`。
6. **弹药**：`PerLevelUsed[w] = r.Ammo.Weapons[w].PerLevelUsedTotal`（`perLevelLimit` 非 null 的武器）；`Depot` = `r.Ammo.PoolRemaining`（逐项覆盖；未出现的武器保持）；全国库存层：`Rounds = Max(Floor, Rounds − Used(w))`（3.3.4），变化时发 `StockChanged`。
7. `AlertResponsiveness = r.Civil.ResponsivenessEnd`；`KnownTargets = r.CarryOut.KnownTargets`。
8. **欺骗单位寿命**：本夜部署、存活、`Duration == Nights` 的欺骗单位 `NightsLeft −= 1`，为 0 → 移除（`RosterUnitExpired`）；`OneShot` 存活者保留（未被命中）；`SeenThrough` 保持为 true（敌方已识破，跨夜保留；02 8.x 对齐项）。
9. **信任度**（3.4.2，启用时）。
10. **挫折**（3.6）。
11. **期限**：本夜可用（`AvailableFromDay ≤ n.Day`）且 `NightsLeft != null` 的申请 / 效果单位 `NightsLeft −= 1`，为 0 → 移除（`ReinforcementExpired`）；`ActiveSupports` 每项 `NightsLeft −= 1`，为 0 → 移除。`Quiet` 夜同样执行本步。
12. **归还**：`ReturnAfterNightIndex == NextNightIndex` 的单位移除（`UnitReturned`）。`Quiet` 夜同样执行。
13. **统计**：`Tallies` 累加（3.12.1）；敌情档案（3.10.3）；生产设施受损 / 断电（3.13）。
14. 记录 `NightRecord`（`Setback`、`TrustDelta`、`Breakdown`、`WeightedLossFrac = r.Losses.WeightedLossFrac`）；更新 `LastAlertFrac = r.Civil.AlertActiveSec / NightDef(n.WavesNight).DurationSec` 与 `LastUnpoweredStructures`；`NightResult` 本身只在内存中保留供复盘，不进存档（3.15）；`NextNightIndex += 1`；阶段 → `Review`；发出 `NightResolved { Index, Outcome, AutoResolved }`。

#### 3.7.5 班组疲劳与王牌班组（跨夜 / 跨关；WS01-025 的战役侧）

```
TonightCrewNights(u, day):
    c = u.AceId != null ? Ace(u.AceId) : u
    return (c.LastFoughtDay == day − 1 or c.LastFoughtDay == day) ? c.ConsecutiveNights + 1 : 1
```

- 含义："包括今晚在内的连续作战夜数"；03 以 `CrewConsecutiveNights ≥ crewFatigue.minConsecutiveNights` 判疲劳（03 3.3），即默认数据下**第 3 个连续夜起** ×0.85（GDD 8.7"连续 3 夜以上"，按含 3 夜解释，待决 Q-C1）。
- C 结构夜与夜相隔一周以上 → 永远是 1（不疲劳）；D / E 的连续日才会累积；同日的白天段与夜间段（第 18 关）算连续。
- 跨关：开始关卡时所有王牌 `ConsecutiveNights = 0`（关卡之间相隔数周）；普通班组随花名册重建。
- **王牌阵亡**：3.7.4 第 3 步，"待判定王牌"按王牌 ID 序数顺序：叙事难度 → 一律 `Wounded`（`WoundedNightsLeft = crew.woundedNights`），不消耗随机数；否则 `rng = Stream("crew:{LevelId}:{index+1}")`，每个王牌 `rng.Chance(crew.aceDeathChanceOnUnitDestroyed)` → `Dead`（`AceCrewKilled`），否则 `Wounded`（`AceCrewWounded`）。
- 王牌倍率本身（`aceCrew.probMult`）由 03 读取；本文件只给 `AceCrew = true`。`Xp` 目前只用于显示（特长解锁待决 Q-C3）。

#### 3.7.6 天气与昼夜（WS01-026 的数据侧）

- 天气：`waves.json nights[].weather`（02 已读取 `NightDef.Weather`）。E 结构的普通夜复用波次夜模板，因此天气随模板；需要不同天气就写不同的波次夜。
- 昼夜：新增 `waves.json nights[].timeOfDay`（`night` / `day`，缺省 `night`）→ `NightDef.TimeOfDay`（02 Q26 的建议，8.3 R-01-2）。第 18 关"白天无人机持续消耗"= 一个 `timeOfDay: day` 的波次夜作为 `Key` 条目，同日后接黄昏补给（`Day` 阶段）与夜间条目。
- 季节：`EnvironmentResolver.SeasonFor(NightDef night, GameDate levelDate) = night.Season ?? FromMonth(levelDate.Month)`，`FromMonth`：12、1、2 → `Winter`；3–5 → `Spring`；6–8 → `Summer`；9–11 → `Autumn`。全目录只此一处实现（`sim/Environment/`），02 / 03 需要季节时调用它。
- 冬季效能、电网压力等夜内效果不在本文件。

### 3.8 日历与自动结算（WS05-011，GDD 11.5）

#### 3.8.1 结构 E 的日程

`flow.nights` 中 `Key` = 亲自指挥；`Auto` = 普通夜，默认自动结算；`Quiet` = 无空袭。日历按 3.2.2 逐日推进；没有夜晚条目的日子只有 `Day` 阶段。

#### 3.8.2 `AutoResolveNight()`

1. 部署方案 = 当前 `Deployed` 的单位（玩家上次的部署；`Pos` 不变）；若没有任何单位部署，照常运行（全部突防）。
2. `setup = PrepareNight()`，其中 `CarryIn.AutoResolve = new AutoResolveCarryIn(autoResolve.interceptProbMult, autoResolve.exposureGainMult)`。
3. `world = SimWorld.Create(setup.Level, setup.Config, setup.Seed)`；**不入队任何命令**；`while (!world.IsFinished) world.Step()`；二选一请求全部按超时默认处理（04）。
4. `ApplyNightResult(world.Result)`，`NightRecord.AutoResolved = true`。
5. 生成战报 `AutoNightReport { Index, Outcome, WeightedLossFrac, AmmoUsed: [(WeaponId, Shots)], UnitsLost: [RosterId], ExposureDelta: [(RosterId, Before, After)], FactoryPausedSec }`（GDD 11.5"产量损失、弹药消耗、暴露度变化"；`FactoryPausedSec = Σ Losses.Structures[Type == Factory].PausedSec`）。

"略逊于亲自指挥"的来源（三项叠加，数值待 WS09 批量验证）：①不使用指挥点、二选一取默认；②`interceptProbMult`（03 作为额外乘子）；③`exposureGainMult`（02 作用于暴露度的**正**增量）。玩家选择观看则无 ②③，并得到 `watchTrustBonus`。

#### 3.8.3 自动结算的确定性

自动结算与"观看"使用同一种子（3.1.2），因此"观看"一个普通夜而不下任何命令时，结果与自动结算只差 ②③ 两项修正。

#### 3.8.4 大空袭预警

`DayStep` 第 8 步：对 `flow.nights` 中 `Kind == Key` 且 `WarnDaysBefore != null` 且 `NightDef(WavesNight).BigRaid == true` 的条目 `k`：若 `Day ≥ k.Day − k.WarnDaysBefore` 且 `Day < k.Day` 且 `k.Day ∉ RaidWarnings` → `RaidWarnings.Add(k.Day)`，发出 `RaidWarningIssued { NightDay = k.Day, DaysAhead = k.Day − Day }`。

### 3.9 战役流程（WS05-008）

#### 3.9.1 解锁

`campaign.json levels[]` 的顺序即游玩顺序（两线交替由数据给出）。第 `i` 项解锁 ⇔ 第 `0 … i−1` 项都在 `CompletedLevels` 中。全部完成 → 战役结束（`CampaignCompleted`）。

#### 3.9.2 关卡完成（`Completed`）

固定顺序：

1. `CompletedLevels.Add(new LevelRecord(LevelId, Number, Attempt, Completed, Metrics, …))`；`Metrics` = `LevelRunState.Metrics` ∪ `flow.levelMetrics` 中 `source = custom` 的键取最后一夜 `CarryOut.CustomMetrics` 的值。
2. 跨关节点求值（3.10.1）。
3. 城市记忆（3.10.4）。
4. 敌人适应更新（3.12.2）。
5. 奖励卡：本关 `line ∈ {A, B}`（AB 不发）→ 3.11 抽卡；候选为空则不发。
6. 插曲：`campaign.json interludes` 中 `afterLevel == Number` 的第一项 → `PendingInterlude = id`。
7. "战役影响"清单（3.10.7）。
8. `CurrentLevel = null`；`LevelStartSnapshot = null`。

`ChooseCard` 与 `ChooseInterlude(optionIndex)` 必须在开始下一关前完成（`StartLevel` 的前置）。`ChooseInterlude`：把所选选项的效果按 `At` 解析为 `PendingEffect`（`Immediate` 立即应用），`PendingInterlude = null`。

#### 3.9.3 关卡失败与重试（`Failed`）

- 阶段 `Failed` 时只接受 `RetryLevel`。
- `RetryLevel`：记下当前 `Lines[*].Setbacks`、`Lines[*].Trust`（失败已扣的信任度）；`state = Deserialize(LevelStartSnapshot)`；恢复记下的 `Setbacks` 与 `Trust`；再执行 3.2.1（`Attempt = 旧 Attempt + 1`，`LevelStartSnapshot` 重新生成）。
- 失败不写 `CompletedLevels`；跨关节点、适应、奖励卡只在完成时结算。

### 3.10 跨关影响（WS05-004，GDD 13）

#### 3.10.1 节点数据 `links.json` 与求值

```json
{ "kind": "links", "links": [
  { "id": "l04_captured", "sourceLevel": 4, "textKey": "link.l04_captured",
    "metric": { "type": "level_metric", "key": "escort_survival_frac" },
    "outcomes": [
      { "atLeast": 0.7, "textKey": "link.l04_captured.best", "effects": [ { "kind": "grant_unit", "unit": "captured_spaag", "count": 1, "condition": "intact", "ammoFrac": 1.0, "at": { "level": 8 } } ] },
      { "atLeast": 0.4, "textKey": "link.l04_captured.mid",  "effects": [ { "kind": "grant_unit", "unit": "captured_spaag", "count": 1, "condition": "intact", "ammoFrac": 0.5, "at": { "level": 8 } } ] },
      { "atLeast": null, "textKey": "link.l04_captured.low", "effects": [ { "kind": "grant_unit", "unit": "captured_spaag", "count": 1, "condition": "light_damaged", "ammoFrac": 0.5, "at": { "level": 8 } } ] } ] }
] }
```

```csharp
public enum LinkMetricType { Victory = 0, StructureAlive = 1, StructureHpFrac = 2, RosterTagAliveCount = 3,
                             RosterUnitLostCount = 4, LevelMetric = 5, Flag = 6, ResearchCompleted = 7, StockUsed = 8 }
```

| 度量 | 参数 | 值（在 3.9.2 第 2 步、`LevelRunState` 仍可读时计算） |
|---|---|---|
| `Victory` | — | 1（只在完成时求值） |
| `StructureAlive` | `structure` | 最后一夜后 `!Structures[id].Destroyed` → 1，否则 0（不在表中 = 满血 = 1） |
| `StructureHpFrac` | `structure` | `Hp / MaxHp`（不在表中 = 1.0） |
| `RosterTagAliveCount` | `tag` | 花名册中 `Tag == tag` 的单位数 |
| `RosterUnitLostCount` | `unit` | 本关 `RosterUnitLost` 中该 `UnitDefId` 的次数 |
| `LevelMetric` | `key` | `LevelRecord.Metrics[key]`（缺失 = 0） |
| `Flag` | `key` | `Flags[key]`（缺失 = 0） |
| `ResearchCompleted` | `project` | 1 / 0 |
| `StockUsed` | `weapon` | 本关开始时 `Rounds` − 当前 `Rounds` |

求值：`outcomes` 按数据顺序，取第一个 `atLeast == null || v ≥ atLeast − 1e-12` 的项（加载校验：非 null 的 `atLeast` 严格降序，最后一项可为 null）；无匹配 → 无效果。记录 `LinkOutcomes[id] = (index, v, LevelId)`，把该项 `effects` 按 `At` 处理：`Immediate` → 立即应用（只允许 `UnlockDoctrine`、`Favor`、`SetFlag`、`TrustDelta`，其余加载报 `E_RANGE`）；`Level` → `PendingEffect`（必须 > `sourceLevel`，否则 `E_RANGE`）；`NextLevelOfLine` → `PendingEffect(TargetLine)`。发出 `LinkOutcomeRecorded`。

**夹紧规则**：比例型效果（`AmmoFrac`、`CityResourceFrac`、`LogisticsFrac`）在目标关卡开局时与信任度修正一起夹紧到 `crossLevelModClamp`（GDD 13.2"±10–20%，有保底"）；绝对型效果（`GrantUnit`、`UnitCountDelta`、`FighterSortiesDelta`）不受比例夹紧，但 `UnitCountDelta` 有"≥ 1"保底（3.3.2），`FighterSortiesDelta` 有"≥ 0"保底（CarryIn）。

#### 3.10.2 GDD 13.5 全部节点（`links.json` 草案；效果数值全部待决）

| 节点 ID | 来源 | 度量 | 结果 → 效果（目标关卡） |
|---|---|---|---|
| `l03_soviet_stock` | 3 | `StockUsed(s300_missile)`（只用于"战役影响"文本） | 无效果条目——由全国库存本身传递到 6、11（3.3.4） |
| `l04_captured` | 4 | `LevelMetric(escort_survival_frac)` | ≥ 0.7 完好 + 满弹 / ≥ 0.4 完好 + 半弹 / 其他 轻伤 + 半弹 → `GrantUnit(captured_spaag, 1)` @8（GDD 12.3"至少保证 1 套"） |
| `l05_volunteers` | 5 | `RosterTagAliveCount(volunteer_fire_team)` | ≥ 1 → `GrantUnit(mobile_fire_team, 1, tag volunteer_fire_team)` + `CityResourceFrac(+0.1)` @15 与 @18；其他 → 无 |
| `l07_patriot_debut` | 7 | 派生度量 `LevelMetric(patriot_survived)`（3.9.2 第 1 步写 `Metrics["patriot_survived"] = 1 − Min(1, 本关 patriot 损失数)`；`atLeast` 只能表达"≥"，因此先派生） | ≥ 1 → `AmmoFrac(pac3_mse, +0.15)` @9、@11；其他 → `AmmoFrac(pac3_mse, +0.05)` @9、@11（援助信心只增不减） |
| `l09_ambush_doctrine` | 9 | `Victory` | ≥ 1 → `UnlockDoctrine(forward_ambush)`（`at: "immediate"`，立即写入 A 线；第 11 关起经 `CarryIn.Doctrines` 生效） |
| `l09_patriot_loss` | 9 | `RosterUnitLostCount(patriot)` | ≥ 1 → `UnitCountDelta(patriot, −1)` @11、@12、@13、@16、@18（保底 1） |
| `l10_evacuation` | 10 | `LevelMetric(evacuated_frac)` | ≥ 0.8 → `AceCrewsJoin(3)`；≥ 0.5 → 2；其他 → 1 @14（B 线） |
| `l12_hangar` | 12 | `StructureAlive(hangar)` | `atLeast 1` → 无；其他 → `FighterSortiesDelta(−1)` @13、@15、@16（"机库受损则额度永久下降"） |
| `l12_runway` | 12 | `StructureHpFrac(runway)` | ≥ 0.5 → 无；其他 → `FighterSortiesDelta(−1)` @13 |
| `l14_workshop` | 14 | `StructureAlive(field_workshop)` | ≥ 1 → `ProductionLineStart(dispersed, outputStock 10)` + `GrantUnit(interceptor_drone_team, 1)` @15；其他 → 无（"设施被毁则推迟"：第 15 关照常从零建造） |
| `l15_handover` | 15 | `LevelMetric(handed_over)`（3.13.4） | ≥ 40 → `GrantUnit(interceptor_drone_team, 3)`；≥ 20 → 2；≥ 1 → 1 @16（A 线） |
| `l16_underground` | 16 | `ResearchCompleted(high_speed_interceptor)` 且地下车间存活：3.9.2 写 `Metrics["hs_ready"]` = 两者都成立 ? 1 : 0，度量 `LevelMetric(hs_ready)` | ≥ 1 → `GrantUnit(high_speed_interceptor_team, 1)` @17（"最多提前一关、限量原型"） |
| `l16_17_jet` | 17 | `Flag(jet_test_facility_ok)`（第 16 关研发完成时 `SetFlag(jet_research, 1)`；第 17 关结束时 3.9.2 写 `Flags["jet_test_facility_ok"] = jet_research == 1 且 StructureAlive(test_facility) ? 1 : 0`） | ≥ 1 → `GrantUnit(jet_interceptor_drone, 6)`；其他 → `GrantUnit(jet_interceptor_drone, 2)` @18（GDD 12.2：必定出现，6 或 2） |
| `l17_repair_plant` | 17 | `StructureHpFrac(aviation_repair_plant)` | ≥ 1.0 → 无；≥ 0.5 → `FighterSortiesDelta(−1)`；其他 → `FighterSortiesDelta(−2)` @18 |
| （全程）残骸回收 | 每夜 | `KillsByEnemy` | 敌情档案（3.10.3） |

- 第 7、16、17 关所需的组合条件在 3.9.2 第 1 步由**关卡专用的度量写入规则**生成（`flow.levelMetrics` 增加 `source` 取值 `derived:<规则名>`，规则名与实现见 8.2 Q-L3）。上表给出了每个规则的精确定义。
- `captured_spaag`、`high_speed_interceptor_team`、地图保护目标 ID（`hangar`、`runway`、`field_workshop`、`aviation_repair_plant`、`test_facility`）在数据中尚不存在（8.2 Q-L2）。

#### 3.10.3 敌情档案（残骸回收）

每夜（3.7.4 第 13 步）：对 `r.CarryOut.KillsByEnemy` 每项 `(e, c)`：`f = dossier.families` 中第一个 `members` 含 `e` 的家族 ID，没有则 `f = e`；`Dossier[f] = Min(maxPoints, Dossier[f] + c × pointsPerKill)`；若跨过某个 `levels[k].minPoints` → `DossierLevelUp { Family, Level = k + 1 }`。

`CarryIn.Dossier`：对 `Dossier` 每项 `(f, p)`，`k` = `minPoints ≤ p` 的最高档（没有则跳过）；成员集合 = 家族 `members`（`f` 不是家族时为 `{f}`）；每个成员一项 `DossierCarryIn(member, levels[k].discriminationAdd, levels[k].classifyTimeMult)`；按 `EnemyDefId` 序数升序。含义由 02 实现（诱饵甄别概率 `+add`、航迹分类 / 升级所需时间 `× mult`；8.3 R-02-1）。"回收 Geran‑3 → 更快识别 Geran‑5"由同家族共享点数实现。

#### 3.10.4 城市记忆

- 关卡完成时（3.9.2 第 3 步）：`city = flow.CityId`，非空则 `CityMemory[city].Visits += 1`；若本关所有 `Key` 夜都不是挫折（`NightRecord.Setback == false`）→ `Victories += 1`。
- 开局（3.3.1 第 4 步）：`city` 非空 → 城市记忆加成 `Min(cityMemory.maxBonusFrac, Victories × cityMemory.bonusFracPerVictory)` 计入 `city` 比例修正（本关的完成在之后才计入，不影响本关）。

#### 3.10.5 人情

- `Favor` 效果：`Lines[holder].Favors.Add(new FavorToken(favorId, OwedBy = 另一条线, uses))`；发出 `FavorGained`。
- `CallFavor(int tokenIndex)`（阶段 `Deployment` / `Day`，本关线集合含 `holder`）：下标有效且 `UsesLeft > 0`，否则 `NoFavor`；按 `campaign.json favors[favorId]` 加入 `count` 个 `grantUnit`（`Source = Favor`，`NightsLeft = nights`，`AvailableFromDay = Day`）；`UsesLeft −= 1`，为 0 则移除；发出 `FavorCalled`。不消耗信任度。

#### 3.10.6 条令

`doctrines.json` 只登记 ID、名称与 `effectKey`；效果由所属规格读取 `CarryIn.Doctrines` 实现（`forward_ambush` → 04 / 02：伏击相关；`fire_team_network` → 02：火力组共享航迹）。本文件只管解锁（`UnlockDoctrine` 效果）与传递。效果定义待决 Q-L4。

#### 3.10.7 "战役影响"清单

关卡完成时生成 `CampaignImpactReport`（只读视图，不进存档）：按以下顺序列出 `ImpactLine(TextKey, Args, TargetLevels, Sign)`：①本关记录的每个节点结果（`links` 数据顺序；`TextKey` = 结果项的 `textKey`；`TargetLevels` = 该项效果的 `at.level` 去重升序；`Sign` = 效果"正面 / 负面 / 中性"按 3.3.1 第 2 步的规则判定）；②全国库存变化（每个武器：开始 → 结束）；③两线信任度变化（开始 → 结束）；④敌情档案升档；⑤敌人适应的启用 / 停用；⑥待生效的奖励卡与插曲效果。叙事难度下负面项标注"已关闭"。

### 3.11 奖励卡（WS05-005 前半）

`cards.json`：`cards[]{ id, nameKey, line, weight, levelRange{min,max}?, from?, until?, unique?, effects[] }`（`from` / `until` 为年月，按关卡日期判定，00 1.4 形态 C 语义）。

抽卡（3.9.2 第 5 步）：

```
pool = cards 中满足：line == 本关 line；levelRange 包含 Number（缺省不限）；日期闸门 Active；
       !(unique == true && line.Cards.Contains(id))；effects 中 GrantUnit 的单位不受 unit_unavailable（按"目标关卡"日期无法预知 → 按本关日期判定）
       按 id 序数升序
k = Min(rewardCards.offerCount, pool.Count)；pool.Count == 0 → 不发
rng = Stream("cards:{LevelId}")
for i in 1..k:
    total = Σ pool[j].weight（按顺序累加）
    r = rng.NextDouble() × total
    acc = 0; chosen = pool.Count − 1
    for j in 0..pool.Count−1: acc += pool[j].weight; if r < acc: chosen = j; break
    offer.Add(pool[chosen].id); pool.RemoveAt(chosen)
PendingCardOffer = new CardOffer(LevelId, line, offer)          # offer 保持抽取顺序
```

`ChooseCard(cardId)`：`cardId ∈ PendingCardOffer.CardIds`，否则 `InvalidArgument`；`line.Cards.Add`；效果按 `At`（缺省 `nextLevelOfLine = 卡的 line`）转为 `PendingEffect`；`PendingCardOffer = null`；发出 `CardChosen`。`weight ≤ 0` 的卡加载时报 `E_RANGE`。

示例卡（GDD 13.3）：`extra_iris_t_batch`（`AmmoFrac(iris_t_slm_missile, +0.15)`）、`gepard_extension`（`ReturnDeadlineExtend(gepard, 1)`）、`alt_positions_x3`（`SurveyedPositions(3)`）。

### 3.12 敌人适应（WS05-006，GDD 13.4）

#### 3.12.1 统计

每夜（3.7.4 第 13 步）累加到 `Tallies`：

```
for x in r.Ammo.Weapons: cls = Catalog.Weapon(x.WeaponId).InterceptClass
    HitsTotal += x.Hits
    if cls ∈ {"gun", "gun_radar"}: HitsGun += x.Hits                       # 类别名取自 intercept.json
    if cls ∈ {"interceptor_drone", "jet_interceptor_drone"}: HitsDrone += x.Hits
ArmDetections += r.CarryOut.PlayStats.ArmDetections；ArmShutdowns += …ArmShutdowns
ThreatsSpawned += …ThreatsSpawned；ThreatsEverEwCovered += …ThreatsEverEwCovered
```

类别名集合写在 `rules/campaign.json adaptation.statClasses`（缺省即上面两组；8.1 新参数），不在代码中写死。

#### 3.12.2 关卡结束更新（仅 `Completed`、`Number != null`）

```
s["gun_kill_share"]    = HitsTotal > 0 ? HitsGun / HitsTotal : 未定义
s["drone_kill_share"]  = HitsTotal > 0 ? HitsDrone / HitsTotal : 未定义
s["arm_shutdown_rate"] = ArmDetections > 0 ? ArmShutdowns / ArmDetections : 未定义
s["ew_coverage_frac"]  = ThreatsSpawned > 0 ? ThreatsEverEwCovered / ThreatsSpawned : 未定义
for stat in 上述四项（按此顺序）: if 有定义: S[stat] = (1 − alpha) × S.GetValueOrDefault(stat, 0) + alpha × s[stat]
for rule in adaptation.rules（数据顺序，stat ≠ position_nights）:
    if !Active(rule) and S[rule.stat] ≥ rule.threshold − 1e-12: 启用，发 AdaptationActivated
    elif Active(rule) and S[rule.stat] < rule.threshold − hysteresis − 1e-12: 停用，发 AdaptationDeactivated
```

`AdaptationState { SortedDictionary<string,double> Stats; SortedSet<string> ActiveRules; }`。敌人是同一个，统计**跨两线共享**。

#### 3.12.3 应用（`BuildCarryIn`）

叙事难度：`AdaptationCarryIn` 全部关闭（`0, false, [], []`）。否则对每个已启用规则（数据顺序），`notBefore` 非空且关卡年月 < `notBefore` → 跳过：

| `effect.kind` | 写入 | 夜内实现 |
|---|---|---|
| `uav_altitude_add_m` | `UavAltitudeAddM = Max(当前, value)` | 01：`Tag == UAV` 的弹药巡航高度 + 该值（"飞得更高，躲开机枪射程"） |
| `force_evasive_uav` | `ForceEvasiveUav = true` | 03：`evasiveTargetVsInterceptorDrone` 修正视为日期已生效（"提前出现会规避的 Shahed"） |
| `enable_trigger` | `ActiveTriggers.Add(trigger)`（去重、序数升序） | 01：`waves.json` 中带 `adaptiveTrigger` 的波次 / 组只在其触发器启用时生成；`adaptiveSubstitutes` 在启用时替换敌方 ID（"先压制后突击"、"抗干扰型与弹道导弹比例"） |

`position_priority`（关卡内、跨夜，不走 EMA）：`PriorityPositions` = 本夜部署的单位中 `NightsAtPosition ≥ threshold` 者的 `Pos`（`RosterId` 升序）；由 04 在 `Initialize` 时加入已知目标清单（"该位置被列入优先打击"）。

### 3.13 生产（WS05-009，状态 + 公式层，M5）

#### 3.13.1 数据与状态

`production.json`：

```json
{ "kind": "production",
  "outputWeapon": "interceptor_drone", "partsPerUnit": 1, "pilotsPerTeam": 2, "dayExposureDecay": 5, "targetThreshold": 70,
  "facilityTypes": [
    { "id": "dispersed",   "outputPerDay": 2, "exposurePerUnit": 1.0, "buildDays": 1, "buildCost": 3 },
    { "id": "central",     "outputPerDay": 8, "exposurePerUnit": 3.0, "buildDays": 3, "buildCost": 6 },
    { "id": "underground", "outputPerDay": 5, "exposurePerUnit": 0.3, "buildDays": 7, "buildCost": 12, "availableFromLevel": 16 } ],
  "pilotTraining": { "days": 5, "costPerPilot": 1, "schoolCapacity": 4 },
  "handover": { "trustPerUnit": 0.25, "trustCapPerLevel": 10 },
  "partsEvents": [ { "id": "parts_cutoff", "chancePerDay": 0.05, "outputMult": 0.6, "days": 3 } ] }
```

`flow.production`：`{ "sites": [ { "id": "site_a", "structure": "workshop_a" } ], "partsPerDay": 6, "startPilots": 4, "startParts": 0 }`。

```csharp
public sealed class ProductionState { public double Parts; public int Pilots; public List<int> TraineeDaysLeft; public int OutputStock;
    public List<Facility> Facilities; public List<ActivePartsEvent> Events; }
public sealed class Facility { public int FacilityId; public string TypeId; public string SiteId; public string StructureId;
    public FacilityStatus Status; public int BuildDaysLeft; public double Exposure; public double Progress; }
public enum FacilityStatus { Building = 0, Active = 1, Destroyed = 2 }
public sealed record ActivePartsEvent(string EventId, int DaysLeft);
```

#### 3.13.2 每日推进 `ProductionRules.Advance(g, a)`

逐日执行 `g` 次（第 1 天 `a1 = a`，之后 `a1 = 0`），每日：

```
1. 随机事件：rng = Stream("production:{LevelId}:{Day − g + d}")；对 partsEvents（数据顺序）：
       若该事件未激活且 rng.Chance(chancePerDay) → Events.Add(id, days)
   eventMult = Π 激活事件的 outputMult
2. Parts += partsPerDay
3. 对 Facilities（FacilityId 升序）：Building → BuildDaysLeft −= 1，为 0 → Active
4. 产能：对每个 Active 设施 f：
       st = Structures[f.StructureId]（缺失 = 满血）；st.Destroyed → f.Status = Destroyed，cap_f = 0
       hpFrac = st == null ? 1 : Hp / MaxHp
       dayOne = (d == 1) ? (PoweredAtEnd(f) ? 1 : 0) × (1 − cityResource.alertPauseWeight × a1) : 1
       cap_f = outputPerDay(type) × dayOne × hpFrac × eventMult
   D = Σ cap_f；s = D × partsPerUnit ≤ Parts ? 1 : Parts / (D × partsPerUnit)（D == 0 → s = 0）
5. 对每个 Active 设施（ID 升序）：p = cap_f × s；f.Progress += p；whole = FloorEps(f.Progress)；f.Progress −= whole；
       OutputStock += whole；Parts −= p × partsPerUnit
       f.Exposure = Clamp(f.Exposure − dayExposureDecay + exposurePerUnit(type) × p, 0, 100)
       f.Exposure ≥ targetThreshold 且本关未登记 → KnownTargets.AddStructureTarget(f.StructureId)（04 接口），发 FacilityTargeted
6. 飞手训练：TraineeDaysLeft 每项 −1；为 0 的移除并 Pilots += 1
7. 事件 DaysLeft −= 1，为 0 移除
```

`PoweredAtEnd(f)` = `!LastUnpoweredStructures.Contains(f.StructureId)`（3.7.4 第 13 步由 `Losses.Structures[].PoweredAtEnd` 更新）。`Parts` 不足时按比例缩减所有设施（"补给线守不住就停工"）；暴露度随产量上升（GDD 10.3），达到阈值后被列为打击目标（"生产设施本身就是诱饵和弱点"）。

#### 3.13.3 动作

- `BuildFacility(typeId, siteId)`（`Day`）：站点存在且空闲；`availableFromLevel` 闸门；城市资源 ≥ `buildCost`；→ 新设施 `Building`，`BuildDaysLeft = buildDays`。
- `TrainPilots(n)`（`Day`）：`n ≥ 1`；`TraineeDaysLeft.Count + n ≤ schoolCapacity`（`CapReached`）；城市资源 ≥ `n × costPerPilot`；→ 追加 `n` 个 `days`。
- `AllocateOutput(n)`（`Day` / `Deployment`）：`n ≤ OutputStock`；`OutputStock −= n`；`Depot[outputWeapon] += n`（自用：今晚多拦几架）。
- 飞手约束：3.7.1 第 5 条；拦截无人机班组被毁 → `Pilots = Max(0, Pilots − pilotsPerTeam)`（3.7.4 第 2 步，"老飞手阵亡代价很大"）。
- `ProductionLineStart(type, outputStock)` 效果：开局在第一个站点建一个 `Active` 设施，`OutputStock += outputStock`。

#### 3.13.4 上交 `HandOver(n)`（`Day`）

`n ≤ OutputStock`；`gain = Min(n × handover.trustPerUnit, handover.trustCapPerLevel − HandoverTrust)`（< 0 时为 0）；`OutputStock −= n`；`HandedOver += n`；`HandoverTrust += gain`；本关线 `Trust = Clamp(Trust + gain, min, max)`（`Cause = Handover`）；`Metrics["handed_over"] = HandedOver`（第 15 关 → 第 16 关节点）。

### 3.14 研发与电力分配（WS05-010，状态 + 公式层，M5）

#### 3.14.1 研发

`research.json projects[]{ id, nameKey, counters, cost, availableFromLevel?, effect{ id, value }, setFlag? }`；`flow.research = { "pointsPerDay": 3 }`。

- 状态 `ResearchProgress { string? ActiveProject; SortedDictionary<string,double> Progress; }`。
- `SetResearch(projectId)`（`Day`）：未完成、闸门满足 → `ActiveProject = id`（切换不清空已有进度）。
- `Advance(g)`：`ActiveProject != null` → `Progress[p] += pointsPerDay × g`；`Progress[p] ≥ cost − 1e-9` → `ResearchCompleted.Add(p)`（战役级、永久）、`setFlag` 非空则 `Flags[setFlag] = 1`、`ActiveProject = null`、发 `ResearchCompleted`。超出部分丢弃。

#### 3.14.2 研发效果

`CarryIn.ResearchEffects` = 所有已完成项目的 `effect`（`EffectId` 序数升序；同一 `EffectId` 多个项目 → 取 `value` 最大者）。效果 ID 与夜内实现：

| `effect.id` | 实现者 | 规则（建议） |
|---|---|---|
| `evasive_recover` | 03 | 规避修正 `m = base + (1 − base) × value`（`base = evasiveTargetVsInterceptorDrone.probMult`）——"夺回被废掉的最优解" |
| `ew_effectiveness_add` | 02 | 电子战时期效能 `Min(1, eff + value)` |
| `jet_research`（仅 `setFlag`） | — | 第 18 关节点（3.10.2） |

#### 3.14.3 电力分配（第 17 关，公式层）

`PowerAllocation { double ProductionFrac, RadarFrac, HeatingFrac }`，三者 ≥ 0 且和为 1（容差 1e-9），`SetPowerAllocation` 校验。`avail` = 上一夜 `PoweredAtEnd` 的电源 / 变电站保护目标占比（按 `Weight` 加权）。

```
productionPowerMult = Min(1, avail × ProductionFrac / power.productionNeed)    # 乘到 3.13.2 的 cap_f
radarPowerMult      = Min(1, avail × RadarFrac / power.radarNeed)              # → CarryIn（02 读取，雷达效能）
heatingShortfall    = Max(0, power.heatingNeed − avail × HeatingFrac)          # 每日 Trust −= heatingShortfall × power.heatingTrustPenalty
```

`power.*` 为 `flow.json` 新参数（待决 Q-P3）；`radarPowerMult` 需要 `CarryIn` 新字段（8.3 R-02-3，M5 时再登记）。

### 3.15 存档（WS05-007）

#### 3.15.1 格式

```json
{
  "format": "nightwatch-save",
  "version": 1,
  "simVersion": "0.1.0",
  "dataHash": "sha256:…",
  "savedAt": { "phase": "Day", "levelId": "l06", "day": 8 },
  "campaign": { … CampaignState … }
}
```

- 序列化：`System.Text.Json`，`JsonSerializerOptions { PropertyNamingPolicy = CamelCase, WriteIndented = false, NumberHandling = Strict }` + `JsonStringEnumConverter`；`ulong` 种子写 `"0x" + X16`；`Vec2` 写 `{"x":…,"y":…}`；`SortedDictionary` 按键序输出；`double` 必须有限。同一状态两次序列化**逐字节相同**；反序列化后再序列化与原文逐字节相同。
- `dataHash` = 战役数据哈希：00 3.9.2 的算法作用于 `data/campaign/*.json` + `rules/economy.json` + `rules/campaign.json`。读档时不一致 → 警告但继续（数值调整不应让存档作废）。
- `simVersion` 仅供参考。
- 不保存：`NightResult`（只保存派生值 `LastAlertFrac`、`LastUnpoweredStructures`——3.2.4 与 3.13.2 需要的信息）、`CampaignImpactReport`、随机状态（3.1.2）。

#### 3.15.2 存档时机

`Briefing`、`Deployment`、`Review`、`Day`、`Completed` / `Failed` 阶段、以及待选奖励卡 / 插曲时，状态即完整，直接序列化。

#### 3.15.3 夜间中途存档（"任意时刻存读一致"）

`NightInProgressSave { SimConfigJson（00 回放的 config 格式）, string Seed, IReadOnlyList<SimCommand> Commands（00 回放格式）, int Tick, string StateHashAtTick, string DataHash }`：

- 存：宿主从 `SimWorld` 取命令日志与当前 `Tick`、`ComputeStateHash()`。
- 读：`SimWorld.Create(level, config, seed)` → 按序 `Enqueue` 全部命令 → `Step()` 直到 `Tick` → 比较 `ComputeStateHash()`：相等 → 继续；不等（跨平台或数据已变，00 Q9）→ 丢弃中途进度，从该夜开头重新开始，并给出 `NightRestartedOnLoad` 提示。
- 本质上是 00 3.9 回放的复用；`RandomOverride` 不得存在。

#### 3.15.4 版本迁移

`version < 当前` → 依次调用 `SaveMigrations.Migrate_vN_to_vN+1(JsonNode)`；`version > 当前` → 抛 `SaveVersionException`（不尝试读取）。`format` 不符 → 抛 `SaveFormatException`。

### 3.16 死亡螺旋 / 滚雪球防护的批量验证指标（WS05-013、WS09）

防护机制（本文件已实现的部分）：信任度下限与每夜变化夹紧（3.4）、比例修正夹紧 ±20% 与"≥ 1"保底（3.3.1–3.3.2）、全国库存保底（3.3.4）、紧急支援（3.6）、城市资源上限与商店上限（3.5）、生产暴露度自然上限（3.13.2）。

**验证方法**：`tools/balance --campaign` 以固定的**策略机器人**（`baseline`：推荐部署；`wasteful`：总用最贵武器；`hoarder`：弹药保留 50%；`strong`：人工调优部署）从第 1 关跑到第 18 关，每个策略 N 个 `runSeed`。`CampaignMetrics`（`sim/Campaign/Metrics.cs`，纯函数，可单测）计算：

| 指标 | 定义（精确） | 目标（`balanceTargets`） |
|---|---|---|
| `TrustFloorDwell` | 全部运行、全部关卡中，"开局时本关线 `Trust ≤ trust.min + trustFloorMargin`"的关卡数 ÷ 总关卡数（AB 关卡按两线平均） | `baseline ≤ trustFloorDwellMax` |
| `RecoveryRate` | 所有"首次尝试失败"的关卡中，在第 2 或第 3 次尝试内完成的比例 | `baseline ≥ recoveryRateMin` |
| `ResourceSpread` | 对每个关卡号 `k`：`strong` 与 `wasteful` 的"开局配额级弹药总价值 `Σ alloc(w) × shotCostMusd(w)`"均值之比；取所有 `k` 的最大值 | `≤ resourceSpreadMax`（理论上限 1.2 / 0.8 = 1.5，超出说明夹紧有漏洞） |
| `WinGapSlope` | `gap_k` = 关卡 `k` 首次尝试完成率（`strong` − `baseline`）；对 `(k, gap_k)` 做最小二乘斜率 `Σ(k − k̄)(gap − ḡ) / Σ(k − k̄)²` | `≤ winGapSlopeMax`（差距不随战役推进而扩大 = 没有滚雪球） |
| `AutoResolveGap` | 同一部署、同一种子：自动结算夜 `WeightedLossFrac` 均值 − 观看且由 `strong` 指挥的均值 | `∈ [autoResolveGapMin, autoResolveGapMax]`（"略逊于"） |
| `FloorLevelWinRate` | `wasteful` 策略在全国库存已到保底的 A 线关卡上的首次尝试完成率 | `≥ floorLevelWinRateMin` |

计算细节：均值为算术平均（按运行顺序累加）；分母为 0 的指标输出 `null` 并在报告中标"无样本"。

---

## 4. 事件与动作

> 战役层不使用 `SimEvent` / `SimCommand`（它们只存在于一夜之内）。本文件定义三个独立的 enum，整数值取 00 4.1 分配给 05 的段 **500–599**，避免与夜内编号混淆；只追加、不重排（8.3 R-00-4）。

### 4.1 战役动作 `CampaignActionType`

```csharp
public abstract record CampaignAction { public abstract CampaignActionType Type { get; } }
```

| 值 | 动作 | 字段 | 阶段 | 章节 |
|---|---|---|---|---|
| 500 | `StartLevel` | `string LevelId` | 无进行中关卡 | 3.2.1 |
| 501 | `AcknowledgeBriefing` | — | `Briefing` | 3.2.2 |
| 502 | `ConfirmDeployment` | `IReadOnlyList<DeployEntry> Plan` | `Deployment` | 3.7.1 |
| 503 | `AcknowledgeReview` | — | `Review` | 3.2.2 |
| 504 | `Resupply` | `string WeaponId, int Count` | `Day` | 3.7.2 |
| 505 | `RepairUnit` | `int RosterId` | `Day` | 3.7.2 |
| 506 | `RelocateUnit` | `int RosterId, Vec2 Pos, string? AlternatePositionId` | `Day` | 3.7.2 |
| 507 | `SurveyPosition` | `string AlternatePositionId` | `Day` | 3.7.2 |
| 508 | `RequestReinforcement` | `string RequestId, Line? PaidBy` | `Deployment` / `Day` | 3.4.5 |
| 509 | `BuyCityItem` | `string ItemId` | `Deployment` / `Day` | 3.5.2 |
| 510 | `AssignAceCrew` | `string AceId, int RosterId` | `Deployment` / `Day` | 3.7.2 |
| 511 | `WatchAutoNight` | `bool Watch` | `Day` | 3.7.2 |
| 512 | `EndDay` | — | `Day` | 3.2.2 |
| 513 | `ChooseCard` | `string CardId` | 有待选卡 | 3.11 |
| 514 | `ChooseInterlude` | `int OptionIndex` | 有待选插曲 | 3.9.2 |
| 515 | `CallFavor` | `int TokenIndex` | `Deployment` / `Day` | 3.10.5 |
| 516 | `RetryLevel` | — | `Failed` | 3.9.3 |
| 517 | `BuildFacility` | `string TypeId, string SiteId` | `Day` | 3.13.3 |
| 518 | `TrainPilots` | `int Count` | `Day` | 3.13.3 |
| 519 | `AllocateOutput` | `int Count` | `Day` / `Deployment` | 3.13.3 |
| 520 | `HandOver` | `int Count` | `Day` | 3.13.4 |
| 521 | `SetResearch` | `string ProjectId` | `Day` | 3.14.1 |
| 522 | `SetPowerAllocation` | `double ProductionFrac, double RadarFrac, double HeatingFrac` | `Day` | 3.14.3 |

`ApplyNightResult` 与 `AutoResolveNight` 是宿主调用的方法，不是玩家动作。入口：`CampaignResult CampaignOps.Apply(CampaignState s, CampaignData d, CampaignAction a)` → `CampaignResult(bool Accepted, CampaignRejectReason? Reason, IReadOnlyList<CampaignEvent> Events, IReadOnlyList<DataError>? Details)`。被拒绝时状态**完全不变**（实现：先校验全部条件，再修改）。

### 4.2 拒绝原因 `CampaignRejectReason`

| 值 | 原因 | 值 | 原因 |
|---|---|---|---|
| 500 | `WrongPhase` | 513 | `InsufficientStock` |
| 501 | `LevelLocked` | 514 | `CannotRelocate` |
| 502 | `UnknownRosterUnit` | 515 | `AlreadySurveyed` |
| 503 | `InvalidArgument` | 516 | `UnitNotDamaged` |
| 504 | `InvalidState` | 517 | `UnitUnavailable` |
| 505 | `NotAvailable` | 518 | `PositionChangeRequiresRelocation` |
| 506 | `NotYetAvailable` | 519 | `InvalidDeployment` |
| 507 | `HistoricallyUnavailable` | 520 | `AceUnavailable` |
| 508 | `InsufficientTrust` | 521 | `AceNotEligible` |
| 509 | `InsufficientLogistics` | 522 | `NoFavor` |
| 510 | `InsufficientTimeSlots` | 523 | `NoPilots` |
| 511 | `InsufficientCityResource` | 524 | `PendingChoice`（有待选卡 / 插曲） |
| 512 | `CapReached` | | |

### 4.3 战役事件 `CampaignEventType`

`public abstract record CampaignEvent { public abstract CampaignEventType Type { get; } }`；`CampaignResult.Events` 按产生顺序。

| 值 | 事件 | 字段 |
|---|---|---|
| 500 | `LevelStarted` | `string LevelId, int Attempt` |
| 501 | `LevelCompleted` | `string LevelId` |
| 502 | `LevelFailed` | `string LevelId, int Attempt` |
| 503 | `NightResolved` | `int Index, NightOutcome Outcome, bool AutoResolved` |
| 504 | `TrustChanged` | `Line Line, double Before, double After, TrustChangeCause Cause`；`TrustChangeCause { Night = 0, Level = 1, Request = 2, Effect = 3, WatchBonus = 4, Handover = 5, Emergency = 6, Heating = 7 }` |
| 505 | `InquiryTriggered` | `int NightIndex, int WastefulShots` |
| 506 | `EmergencySupportGranted` | `Line Line` |
| 507 | `StockChanged` | `string WeaponId, int Before, int After` |
| 508 | `CityResourceChanged` | `double Before, double After` |
| 509 | `ReinforcementArrived` | `string Source, string? UnitId, string? WeaponId, int Count` |
| 510 | `ReinforcementExpired` | `int RosterId` |
| 511 | `UnitReturned` | `int RosterId` |
| 512 | `RosterUnitLost` | `int RosterId, string UnitDefId` |
| 513 | `RosterUnitExpired` | `int RosterId` |
| 514 | `UnitRelocated` | `int RosterId, int Slots` |
| 515 | `UnitRepaired` | `int RosterId` |
| 516 | `AceCrewJoined` / 517 `AceCrewWounded` / 518 `AceCrewKilled` / 519 `AceCrewRecovered` | `string AceId` |
| 520 | `RaidWarningIssued` | `int NightDay, int DaysAhead` |
| 521 | `CardOffered` | `IReadOnlyList<string> CardIds` |
| 522 | `CardChosen` | `string CardId` |
| 523 | `LinkOutcomeRecorded` | `string LinkId, int OutcomeIndex, double Value` |
| 524 | `PendingEffectApplied` | `string SourceKey, EffectKind Kind` |
| 525 | `HistoricalRestrictionApplied` | `string EventId, string? UnitId, string? WeaponId` |
| 526 | `AdaptationActivated` / 527 `AdaptationDeactivated` | `string RuleId, double Value` |
| 528 | `DossierLevelUp` | `string Family, int Level` |
| 529 | `DoctrineUnlocked` | `Line Line, string DoctrineId` |
| 530 | `FavorGained` / 531 `FavorCalled` | `Line Holder, string FavorId` |
| 532 | `FacilityTargeted` | `string StructureId` |
| 533 | `ResearchCompleted` | `string ProjectId` |
| 534 | `NightRestartedOnLoad` | `int Index` |
| 535 | `CampaignCompleted` | — |

---

## 5. 边界情况

| # | 情况 | 处理 |
|---|---|---|
| 1 | 一夜零发射 | `ExchangeRatio == null` → `dEx = 0`；`ByWeapon` 为空 → `W = 0` |
| 2 | 总发射成本低于 `minShotCostForExchangeMusd`（只用机枪） | `dEx = 0`（样本太少不评价） |
| 3 | 交换比恰等于档位下限（如 0.5） | 归入该档（`minRatio ≤ ratio`） |
| 4 | `WeaponExchange.Ratio == null`（`ShotCostMusd == 0`） | 按 0 处理；但 `avg = 0 < minAvgShotCostMusd`，不会计为浪费 |
| 5 | 信任度已在下限时又被扣分 | 夹紧到 `min`；`TrustChanged.Before == After` 时**不发**事件 |
| 6 | 申请后信任度恰好等于 `min` | 允许（`Trust − cost ≥ min − 1e-9`） |
| 7 | AB 关卡（第 1、18 关） | 夜间信任度变化对两条线都生效；申请必须指定 `PaidBy`；不发奖励卡 |
| 8 | 信任度未启用的关卡（第 2–5 关） | 无夜间 / 关卡信任度变化；`mT = 0`；申请拒绝 `NotYetAvailable` |
| 9 | 比例修正之和超出 ±20% | 夹紧（3.3.1）；超出部分丢弃，不顺延 |
| 10 | `base × (1 + m)` 恰为 x.5 | `MidpointRounding.AwayFromZero`（2.5 → 3） |
| 11 | 单位数 `UnitCountDelta` 后 < 1 | 原 `Count ≥ 1` 时保底 1 |
| 12 | `ammoQuota` 中的武器没有任何单位使用 | 照算，全部进弹药库 |
| 13 | 武器 `magazine == null`（身管、不计数） | 不分配、不补给（补给动作拒绝 `InvalidArgument`） |
| 14 | 全国库存已为保底值时继续使用 | `Rounds` 保持保底值（`Max(Floor, …)`），下一关仍能领到保底数量 |
| 15 | B 线关卡使用苏制武器 | 按配额级处理，不读写全国库存 |
| 16 | 库存弹药随单位被毁 | 计入当夜 `Used`（3.3.4） |
| 17 | `resupply_mult` 使补给数为 0 | 拒绝 `HistoricallyUnavailable`，不扣运力 |
| 18 | `unit_unavailable` 的单位出现在 `availableUnits` | 跳过并发 `HistoricalRestrictionApplied`；校验工具报警告 |
| 19 | 同一天申请、`arrivalDays = 0` | 立即到达，当夜可部署 |
| 20 | 申请的单位在期限内被毁 | 移除；剩余期限作废；不退信任度 |
| 21 | 作战控制单位到期时正在维修 | 照常归还（移除） |
| 22 | 白天转移到当前所在位置 | 允许，照常扣时间槽并重算暴露度（玩家自担） |
| 23 | 白天转移到已被敌方侦察过的阵地 | 暴露度 × `toScoutedPositionMult`（与 02 夜间转移同一函数） |
| 24 | 维修中的单位出现在部署方案中 | 拒绝 `UnitUnavailable` |
| 25 | 轻伤单位不维修直接部署 | 允许；03 按 `DamageEfficiencyMult` 降效 |
| 26 | `Crippled` 单位 | 必须先维修才能部署 |
| 27 | 城市资源不足 1e-9 以内 | 视为足够（`CityResource + 1e-9 ≥ cost`），扣后若为负置 0 |
| 28 | `cityResourcePerDay == null` 的关卡 | `CityResource = 0`；商店拒绝 `NotAvailable` |
| 29 | 城市商店单位上限由 `UnitCountDelta` 改变 | 上限 = 修改后的 `count'` |
| 30 | 自动结算夜以 `Defeated` 结束 | 计挫折，不使关卡失败（Q-F3） |
| 31 | 关键夜 `AllClear` 提前结束 | `survive_game_sec` 按整夜时长计 |
| 32 | 最后一个条目是 `Quiet` | 处理后直接做关卡结束判定 |
| 33 | 同日两个战斗条目（第 18 关白天段 + 夜间段） | 中间开白天但不 `DayStep`；班组夜数按连续计 |
| 34 | 王牌所在单位被毁且难度为叙事 | 王牌受伤，不阵亡，不消耗随机数 |
| 35 | 同一夜两名王牌需判定 | 按王牌 ID 序数顺序各消耗 1 个 `NextDouble` |
| 36 | 奖励卡候选少于 3 张 | 只发候选数；0 张不发、不阻塞流程 |
| 37 | 跨关节点的度量在数据中不存在（如关卡未提供自定义指标） | 按 0 求值 |
| 38 | 跨关节点的目标关卡是另一条线 | 照常（按关卡号匹配），如第 12 关 → 第 15 关 |
| 39 | 叙事难度下负面效果 | 丢弃；"战役影响"清单标"已关闭" |
| 40 | 敌人适应统计分母为 0 | 该统计本关不更新 |
| 41 | 适应规则的 `notBefore` 晚于关卡日期 | 已启用但本关不生效 |
| 42 | 生产时零部件为 0 | `s = 0`，无产出，暴露度仍按衰减变化 |
| 43 | 设施所在保护目标被毁 | 设施 `Destroyed`，不再产出；不可在该站点重建（本关） |
| 44 | 被拒绝的动作 | 状态逐字节不变（可用序列化比较） |
| 45 | 读档时 `version` 更高 | `SaveVersionException` |
| 46 | 夜间中途读档哈希不一致 | 从该夜开头重来，`NightRestartedOnLoad` |
| 47 | 重试关卡 | 恢复开局快照，但保留 `Setbacks` 与失败扣除后的 `Trust`；种子不变 |
| 48 | 有待选奖励卡 / 插曲时 `StartLevel` | 拒绝 `PendingChoice` |

---

## 6. 不变量

### 6.1 运行时断言（`CampaignOptions.CheckInvariants = true` 时每个动作之后检查）

1. 每条线 `trust.min ≤ Trust ≤ trust.max`；所有 `double` 有限。
2. `NationalStock[w]`：`Floor ≤ Rounds`；**任一关卡开始后 `Rounds` 只减不增**（与 `StockAtLevelStart` 比较，跨关卡亦然：新关开始时的 `Rounds` ≤ 上一关结束时的值）。
3. 本关适用库存层的每个武器：`Held(w) ≤ NationalStock[w].Rounds`。
4. `ResourceMods` 每个值 ∈ `[crossLevelModClamp.min, crossLevelModClamp.max]`。
5. `0 ≤ CityResource ≤ cityResource.cap`；`CityPurchases[item] ≤ 上限`。
6. `TimeSlotsLeft ≥ 0`；`LogisticsLeft ≥ −1e-9`；`Depot[w] ≥ 0`；每个发射架 `RoundsLeft ≥ −1`。
7. 花名册 `RosterId` 严格升序、唯一，且 `< NextRosterId`；`0 ≤ Exposure ≤ 100`；`0 < DamageEfficiencyMult ≤ 1`；`Condition == Intact ⇔ DamageEfficiencyMult == 1.0`（`Crippled` 时取 03 给出的值）。
8. 每个王牌至多配属一个单位；配属单位的 `AceId` 与王牌一致；`Dead` 的王牌不配属。
9. `Phase == Night` ⇔ 宿主持有未结算的夜晚；`Completed / Failed` 时 `NextNightIndex == flow.nights.Count` 或最后结算的夜为 `Defeated`。
10. 序列化往返：`Serialize(Deserialize(Serialize(s))) == Serialize(s)`（逐字节）。
11. 被拒绝的动作前后 `Serialize(s)` 相同。

### 6.2 代码约束

- 遵守 00 第 6.2 节全部禁用项；`sim/Campaign`、`sim/Economy`、`sim/Save`、`sim/Production`、`sim/Research` 中不得出现 `Dictionary<`、`HashSet<`（`NoUnorderedCollectionsTests` 扫描源码）。
- 战役层不得调用 `SimWorld` 的内部成员；只通过 00 2.6 的公开接口。
- 所有数值来自 `data/`；代码中只允许 0、1、`1e-9` / `1e-12` 容差这类非玩法常数。

---

## 7. 测试用例

> 预期值由 `/Users/xtxsinan/.gemini/antigravity/brain/1ae01fc5-32fa-40fc-8760-b956bb95db3c/scratch/spec05_calc.py` 计算（种子用 00 的 `simrandom_vectors.py` 参考实现）。浮点断言：标"=="的逐位相等；其余容差 `1e-12`。所有测试在 `sim.tests/Campaign/`、`sim.tests/Economy/`、`sim.tests/Save/` 下。

### 7.0 公共夹具

- **`TE5` 经济规则**：1.2 节的 JSON **原样**（`trust`、`crossLevelModClamp`、`cityResource`、`supply`、`repair`、`relocation`、`emergencySupport`），但替换：
  - `cityResource.shop = [ {id "buy_ft", unit "u_ft", cost 2}, {id "buy_rt", kind repair_team, cost 2, logisticsAdd 2, perLevelCap 2}, {id "buy_drone", unit "u_drone", cost 3, until "2025-01"} ]`；
  - `supply.roundCostByWeapon = { "w_exp": 2 }`；
  - `requests = [ {id "req_loan", kind unit, unit "u_sam", count 1, trustCost large, arrivalDays 1, durationNights 2}, {id "req_rush", kind ammo, weapon "w_exp", count 6, trustCost small, arrivalDays 0} ]`；
  - `historicalEvents = [ {id "h_nopat", until "2023-04", effect unit_unavailable, unit "u_pat"}, {id "h_half", from "2026-01", effect resupply_mult, weapon "w_exp", mult 0.5} ]`；
  - `ammoTiers = [ {id "sov", weapons ["w_sov"], replenish false, sharedBy line_a, hasFloor true}, {id "west", replenish "supply_window"} ]`；`commandPointsPerNight {min 3, max 6}`。
  - `conventions.gameSecToWorldSec = 60`；`engagement.defaultLaunchers = 1`（03）。
- **单位**（`units/*.json` 手写）：`u_sam`（火力，`vehicle`，`deployGameSec 10`、`packGameSec 10`，武器 `w_sam`：missile、`magazine 4`、`launchers 2`、`ammoSupply limited`、`shotCostMusd 0.4`、`interceptClass "medium"`）；`u_exp`（`deploy 45`、`pack 30`，`w_exp`：`magazine 4`、`launchers 1`、`limited`、`4.0`、`"pac3"`）；`u_sov`（`deploy 5`、`pack 5`，`w_sov`：`magazine 4`、`launchers 1`、`none`、`1.0`、`"s300"`）；`u_ft`（`w_gun`：gun、`magazineRounds null`、`ample`、`0.001`、`"gun"`）；`u_fixed`（`mobility fixed`，`deploy / pack null`）；`u_pat`（任意火力）；`u_drone`（`w_drone`：interceptor_drone、`magazine 10`、`"interceptor_drone"`）；欺骗单位 `d_fake`（`duration nights`、`durationNights 2`）。
- **关卡 `L5`**：`id "l08"`、`number 8`、`protagonist A`、`dateRange.from 2022-11-15`、`timeStructure C`、`nights 3`、`availableUnits [ {u_sam,2,quota}, {u_exp,1,quota}, {u_sov,1,stock}, {u_ft,4,city} ]`、`ammoQuota [ {w_sam,20}, {w_sov,12} ]`、`cityResourcePerDay 4`、`victory [ {survive_nights, 3} ]`；`waves.json` 三夜，`durationGameSec 480`（28800 s）；保护目标 `s1`（`hp 10`）；备用阵地 `a1 (1000,1000) surveyed false`、`a2 (2000,2000) surveyed true`；`flow.json`：`city "c1"`、`days 15`、`nights [ {1,key,1}, {8,key,2}, {15,key,3} ]`。
- **`NR(...)`**：构造 `NightResult` 的测试辅助，未写明的字段取"空 / 0 / null / Survived"。
- **`ScriptedRandom`**：00 TestKit；经 `CampaignOptions.RandomOverride` 注入。
- 战役：`NewCampaign(data, runSeed: 1, Normal)`，`nationalStock [ {w_sov, 20, floor 4} ]`，两线 `Trust = 50`（各测试可改）。

### 7.1 信任度（WS05-002）

**T-05-01 交换比档位**
`TrustRules.ExchangeDelta(ratio, totalCost)`：`(0.3, 13.6) → −3`；`(0.5, 13.6) → −1`；`(0.49999, 13.6) → −3`；`(3, 13.6) → 0`；`(5, 13.6) → 1`；`(25, 13.6) → 3`；`(0.0, 13.6) → −3`；`(30, 0.4) → 0`（成本低于 0.5）；`(null, 13.6) → 0`。另：`bands` 第一项 `minRatio 0.1` → 加载 `E_RANGE`。

**T-05-02 一夜结算（组合）**
`NR`：`Exchange { TotalPotentialLossMusd 39.15, TotalShotCostMusd 13.61, ExchangeRatio 2.876561351947098, ByWeapon [ w_exp{Shots 3, Kills 3, ShotCostMusd 12, PotentialLossMusd 0.15, Ratio 0.012499999999999999}, w_gun{Shots 10, Kills 0, 0.01, 0, 0.0}, w_sam{Shots 4, Kills 3, 1.6, 39.0, 24.375} ] }`；`Losses { WeightedLossFrac 0.1, HighThreatLeaksWithReserve 1, Structures [ s1{Destroyed true} ] }`；目标 `[ obj_a{Night, WeightedLossAtMost, 0.2, +2, −2}, obj_b{Night, StructureIntact, s1, +3, −3} ]`。
预期 `Breakdown == (0, −3, −3, −2, −1, −9, −9)`；A 线 `Trust 50 → 41`；事件 `TrustChanged{A, 50, 41, Night}`、`InquiryTriggered{0, 3}`。

**T-05-03 夹紧与边界**
- 同 T-05-02 但 `w_exp.Shots 7`、`HighThreatLeaksWithReserve 3`：`dWaste = −5`（上限）、`dInq = −3`、`dHoard = −6`、`dObj = −1` → `raw = −15`、`applied = −12`；`Trust 15 → 10`（下限）。
- `ratio 25`（`TotalShotCostMusd 13.6`）、无浪费、无囤弹、`s1` 存活、`WeightedLossFrac 0.1` → `raw = 3 + 5 = 8`、`applied = 8`；`Trust 95 → 100`（上限）。
- `w_exp.Shots 1`：`W = 1 < 2` → 无质询，`dWaste = −1`。
- `Trust 10` 再扣：`After == 10`，**不发** `TrustChanged`。

**T-05-04 信任度 → 配额修正**
`QuotaMod(T)`：`75 → 0.05`；`10 → −0.1`；`30 → −0.05`；`50 → 0.0`；`100 → 0.1`；`41 → −0.022500000000000003`（==）。叙事难度 `30 → 0.0`；`Number 5`（未启用）`→ 0.0`；AB 关卡 A `70`、B `30` → 平均 50 → `0.0`。

**T-05-05 比例修正夹紧与取整**
`ScaleAlloc(base, mSum)`（夹紧 ±0.2 后 `Max(1, RoundHalfAway(base × (1 + m)))`）：

| base | mSum | m | base × (1 + m) | alloc |
|---|---|---|---|---|
| 20 | 0.25 | 0.2 | 24.0 | 24 |
| 8 | 0.35 | 0.2 | 9.6 | 10 |
| 1 | −0.2 | −0.2 | 0.8 | 1（保底） |
| 3 | −0.2 | −0.2 | 2.4000000000000004 | 2 |
| 2 | −0.25 | −0.2 | 1.6 | 2 |
| 5 | 0.1 | 0.1 | 5.5 | 6（远离零） |
| 5 | −0.1 | −0.1 | 4.5 | 5 |
| 0 | 0.2 | 0.2 | 0.0 | 0 |

`UnitCountDelta`：`Count 1, delta −1 → 1`；`Count 2, delta −1 → 1`；`Count 2, delta −3 → 1`；`Count 3, delta +2 → 5`。

**T-05-06 开局资源（L5）**
A 线 `Trust 75`；`PendingEffects = [ link:AmmoFrac(w_sam,+0.1)@8, card:AmmoFrac(w_sam,+0.1)@nextLevelOfLine A, link:CityResourceFrac(+0.1)@9 ]`。`StartLevel("l08")` 后：
- `ResourceMods == { "ammo:w_exp": 0.05, "ammo:w_sam": 0.2, "city": 0.05, "logistics": 0.05 }`；`PendingEffects` 只剩 `@9` 一项。
- 花名册：`1 u_sam`、`2 u_sam`、`3 u_exp`、`4 u_sov`（`u_ft` 不在花名册，商店上限 4）。
- `w_sam`：`alloc 24` → `1:[4,4]`、`2:[4,4]`、`Depot["w_sam"] = 8`；`ResourceBase["w_sam"] = 20`。
- `w_exp`：无 `ammoQuota` → `base = 4`，`4 × 1.05 = 4.2` → `4` → `3:[4]`、`Depot["w_exp"] = 0`。
- `w_sov`（库存）：`issue = Min(12, 20) = 12` → `4:[4]`、`Depot["w_sov"] = 8`；`NationalStock["w_sov"].Rounds` 仍为 20。
- `CityResource == 4.2`（==）。

**T-05-07 无 ammoQuota 的缩减装填**
L5 去掉 `ammoQuota`，A 线 `Trust 10`（`mT = −0.1`），`PendingEffects = [AmmoFrac(w_sam, −0.05)@8]`：`m = −0.15`，`base = 16`，`16 × 0.85 = 13.6` → `14` → `1:[4,4]`、`2:[4,2]`、`Depot["w_sam"] = 0`。

**T-05-08 历史事件**
- L5 改日期 `2026-02-01`，`ammoQuota` 加 `{w_exp, 6}`：`alloc = FloorEps(6 × 0.5) = 3` → `3:[3]`；白天 `Resupply("w_exp", 5)` → 交付 2（`FloorEps(2.5)`）、运力 −4.0；`Resupply("w_exp", 1)` → 拒绝 `HistoricallyUnavailable`，运力不变。`req_rush` → `Depot["w_exp"] += 3`。
- L5 加 `{u_pat, 1, quota}`：日期 `2023-03-15` → 花名册无 `u_pat`，事件 `HistoricalRestrictionApplied{"h_nopat", "u_pat", null}`；日期 `2023-04-01` → 有 `u_pat`。

### 7.2 库存、城市资源、申请、紧急支援

**T-05-09 全国库存只减不增（有保底）**
L5 改 `{u_sov, 3, stock}`：开局 `issue 12` → `4:[4]`、`5:[4]`、`6:[4]`、`Depot 0`。
- 第 1 夜 `Ammo.Weapons w_sov{Shots 10}`，`CarryOut` 余弹 `4:[0]、5:[0]、6:[2]` → `Rounds = Max(4, 20 − 10) = 10`（`StockChanged{w_sov,20,10}`），`Held = 2`。
- 白天 `Resupply("w_sov", 9)` → `InsufficientStock`（可补 8）；`Resupply("w_sov", 8)` → `Depot 8`，运力 `10 − 8 × 1 = 2.0`（`ammoSupply none` → 每发 1）。
- 第 2 夜前装填 → `4:[4]、5:[4]、6:[2]`，`Depot 0`；第 2 夜 `Shots 9`，余弹 `[0,0,1]` → `Rounds = Max(4, 10 − 9) = 4`，`Held = 1`。
- 下一个 A 线关卡（`req 12`）→ `issue 4`；该关用掉 4 → `Rounds = 4`（保底）。
- 随单位损失：某夜 `Shots 2`，单位 `5` 被毁时余弹 3 → `Used = 5`。
- B 线关卡（`protagonist B`）用 `w_sov`：按配额级分配，`NationalStock` 不变。

**T-05-10 城市资源积累**
- 城市记忆 `c1 { Visits 1, Victories 1 }`、`Trust 75`：`m = 0.05 + 0.1 = 0.15000000000000002`；开局 `CityResource == 4.6`（==）。
- 第 1 夜 `Civil.AlertActiveSec 11520`（`a = 0.4`）→ `DayStep(7)`：积累 `4 × 1.15… × (7 − 0.2) = 31.279999999999998` → `Min(30, 35.88) = 30.0`。
- `CityResource 5.0`、`g = 1`、`a = 1.0`：积累 `2.3` → `7.3`。
- `cityResourcePerDay` 删除 → `CityResource == 0`，`BuyCityItem` → `NotAvailable`。

**T-05-11 城市商店**
`CityResource = 10`（测试直接设置），阶段 `Day`、`LogisticsLeft 0`：`buy_ft` × 4 → `CityResource 2.0`、花名册 +4 个 `u_ft`（`Source City`）；第 5 次 → `CapReached`。`buy_rt` → `CityResource 0.0`、`RepairTeams 1`、`LogisticsLeft 2.0`；再设 `CityResource 10`：`buy_rt` → `RepairTeams 2`；第 3 次 → `CapReached`。`buy_drone`：`availableUnits` 加 `{u_drone,1,city}`，日期 `2025-02-01` → `HistoricallyUnavailable`；`2024-12-01` → 成功（`CityResource 7`）。

**T-05-12 申请增援**
A 线 `Trust 30`，阶段 `Deployment`（第 1 夜，`Day 1`）：
- `RequestReinforcement("req_loan")` → `Trust 10`（`TrustChanged{…,Request}`），`PendingArrival{AvailableFromDay 2}`；当夜部署方案不能包含它（尚不在花名册）。
- `RequestReinforcement("req_rush")` → `InsufficientTrust`（`10 − 8 < 10`）。
- 第 1 夜后 `DayStep(7)` → `Day 8`，到达（`ReinforcementArrived`，`NightsLeft 2`）；第 2、3 夜各递减 → 第 3 夜结算后 `ReinforcementExpired`。
- `Trust 50` 时 `req_rush`（`arrivalDays 0`）→ 立即 `Depot["w_exp"] += 6`、`Trust 42`。
- `Number 5` 的关卡 → `NotYetAvailable`；AB 关卡不给 `PaidBy` → `InvalidArgument`。
- 支援目录合并：`support.json` 的 `neighbor_fire_teams`（`trust small`、`next_day`、`nights 1`、`mobile_fire_team × 2`）→ 申请成功后 `Day + 1` 起有 2 个单位、`NightsLeft 1`。

**T-05-13 挫折与紧急支援**
D 结构关卡（4 个 `Key` 夜，日 1–4，`dayPhase Interlude`），A 线 `Trust 25`，`ResourceBase["w_sam"] = 20`：
- `WeightedLossFrac` 依次 `0.35 → Setbacks 1`；`0.29 → 0`；`0.3 → 1`（边界含）；`0.4 → 2`。
- 第 4 夜后若还有夜（加第 5 夜）：进入 `Day` 阶段时 `EmergencySupportGranted{A}`：`CommandPointsBonusNext = 1`、`Depot["w_sam"] += 4`、`Trust 25 → 30`、`Setbacks 0`、`EmergencyGrantedThisLevel true`；下一夜 `CarryIn.CommandPointsBonus == 1`，再下一夜回到 0。
- 同关再出现 2 次挫折 → 不再发放。
- 关卡失败时 `Setbacks 2` → `RetryLevel` 后第一次进入 `Deployment` 即发放。

### 7.3 关卡流程（WS05-003）

**T-05-14 结构 B**
`timeStructure B`、1 夜：`StartLevel → Briefing →(Ack) Deployment →(Confirm) Night →(Apply Survived) Review →(Ack) Completed`；`LevelCompleted`；`CompletedLevels.Count 1`；无 `Day` 阶段。`Apply Defeated` → `Failed`。

**T-05-15 结构 C（L5，A 线 `Trust 75` → `ResourceMods["logistics"] = 0.05`）**
- 第 1 夜后 `AcknowledgeReview` → `DayStep(7)`：`Day 8`；`TimeSlotsLeft 3`；`LogisticsLeft == 10.5`（`10 × 1.05`，==）。
- 单位 `Exposure 80` → `0`（`80 − 140` 截 0）；`Exposure 15.5`、`g = 1` → `0`；`Exposure 80`、`g = 1` → `60`。
- `s1 { Hp 4, LossHp 6.0 }` → `add = FloorEps(10 × 0.1 × 7) = 7` → 满血，从 `Structures` 移除。
- 第 2 夜 `CrewConsecutiveNights == 1`（距上次 7 天）。
- 三夜全部 `Survived` → `Completed`。

**T-05-16 结构 D：疲劳与轮换**
D 关卡（`Key` 夜在日 1–5，`Interlude`），`supplyWindows [ {day 3, logistics 6} ]`，`Trust 50`（`m = 0`）：
- 单位 `1` 连续部署第 1–3 夜 → `CarryIn.Units[1].CrewConsecutiveNights` 依次 `1, 2, 3`；第 4 夜不部署、第 5 夜（日 5）部署 → `1`。
- 第 2 夜前的白天 `LogisticsLeft 0`；第 3 夜前 `6.0`；第 4 夜前 `0`。
- 第 2 夜把王牌 `ace1`（此前未参战）配给单位 `1` → `CrewConsecutiveNights 1`（王牌自己的计数），`AceCrew true`。

**T-05-17 结构 E：日历、普通夜、预警、种子**
关卡 `id "l15"`，`days 6`，`nights [ {2,auto,1}, {3,quiet}, {5,key,2,warnDaysBefore 2} ]`，波次夜 2 `bigRaid true`，`runSeed 1`：
- 阶段序列：`Briefing → Deployment(InitialPlacement) → Day(Day 1) → Day(Day 2) →`（自动结算）`Review → Day(Day 3) →`（Quiet）`Day(Day 4) → Day(Day 5) → Deployment → Night → Review → Completed`。
- `Day 3` 时发出 `RaidWarningIssued{NightDay 5, DaysAhead 2}`，之后不再重复。
- 自动结算夜的种子 `NightSeed(1, "l15", 1) == 0x003961A3A0873D26`；关键夜 `NightSeed(1, "l15", 3) == 0x0AF82D8CF73259EF`；`SimConfig.NightIndex` 分别为 1、2。
- 另：`WatchAutoNight(true)` 于 `Day 2` → 进入 `Deployment`，`CarryIn.AutoResolve == null`；该夜结算后 `Trust += 1`（`Cause WatchBonus`）。

**T-05-18 补给与维修共用运力**
`Day` 阶段 `LogisticsLeft 10`：`Resupply("w_sam", 4)` → 成本 `4 × 0.5 = 2.0` → `8.0`；`Resupply("w_exp", 3)` → `3 × 2 = 6.0` → `2.0`；轻伤单位 `RepairUnit` → `0.0`、`RepairDaysLeft 1`；`Crippled` 单位 `RepairUnit` → `InsufficientLogistics`。`resupplyLimits [ {w_sam, 5} ]`：交付 4 后 `Resupply("w_sam", 2)` → `CapReached`。维修中的单位出现在部署方案中 → `UnitUnavailable`；`DayStep(1)` 后 `Intact`、`DamageEfficiencyMult 1.0`。

**T-05-19 白天转移**
`TimeSlotsLeft 3`：
- `u_exp`（`pack 30`、`deploy 45`）转移到新阵地 `(5000,5000)`：`(1800 + 2700) / 1800 = 2.5` → `3` 槽；`PositionKind New`、`FirstNightAtNewPosition true`、`Exposure 64 → 0`。
- 同上转移到 `a2`（已勘察）：`(1800 + 1350) / 1800 = 1.75` → `2` 槽；`Surveyed`、`false`。
- `u_sam`（`10 + 10`）：`1200 / 1800 = 0.667` → `1` 槽。
- `KnownTargets.IsScouted(pos) == true`（04 测试替身）→ `Exposure 64 → 32.0`。
- `u_fixed` → `CannotRelocate`；`u_exp` 用掉 3 槽后再转移 `u_sam` → `InsufficientTimeSlots`。

**T-05-20 勘察**
L5（第 8 关）`SurveyPosition("a1")` → `TimeSlotsLeft 3 → 2`、`SurveyedPositions = {a1, a2}`；再次 → `AlreadySurveyed`；`a9` → `InvalidArgument`；关卡 `number 2` → `NotYetAvailable`。

**T-05-21 部署确认**
- 第 1 夜前：已放置单位改位置 → 允许（关卡开始前的部署无惩罚），`FirstNightAtNewPosition false`。
- 第 2 夜前：已放置单位在方案中改位置 → `PositionChangeRequiresRelocation`。
- 第 2 夜前新到的单位放在 `(3000,3000)` → `New`、`true`；放在 `a2` → `Surveyed`、`false`。
- `Crippled` 单位 → `UnitUnavailable`；同一 `RosterId` 两次 → `InvalidArgument`；不存在 → `UnknownRosterUnit`。
- 夜前装填：`Depot["w_sam"] = 8`，单位 `1:[1,4]`、`2:[0,0]` → 装填后 `1:[4,4]`、`2:[4,1]`、`Depot 0`。

**T-05-22 夜晚结算写回**
`CarryOut.Units`：`1 { Alive false }`（配属 `ace1`）；`2 { Alive true, Exposure 72.5, Pos (1000,1000), LightDamaged true, DamageEfficiencyMult 0.8, Hits 3 }`；`3 { RadarDestroyed true }`；`7 { d_fake, Alive true, SeenThrough true }`（`NightsLeft 2`）；`Losses.Structures [ s1{MaxHp 10, HpEnd 6, LossHp 4.0} ]`；`Ammo.PoolRemaining [ w_sam 5 ]`；`Civil.ResponsivenessEnd 0.7`；花名册另有单位 `5`（`ReturnAfterNightIndex 0`）。
预期：单位 1 移除（`RosterUnitLost`）、进入王牌判定；单位 2 `Condition LightDamaged`、`Exposure 72.5`、`Pos (1000,1000)`、`AlternatePositionId "a1"`、`NightsAtPosition 1`、`LevelHits 3`、`FirstNightAtNewPosition false`；单位 3 `Crippled`；单位 7 `NightsLeft 1`、`SeenThrough true`，下一夜后移除（`RosterUnitExpired`）；`Structures["s1"] == (6, 4.0, false)`；`Depot["w_sam"] == 5`；`AlertResponsiveness 0.7`；单位 5 被移除（`UnitReturned{5}`）。

**T-05-23 王牌阵亡判定**
关卡 `l07`，第 2 个条目（下标 1）的夜晚中，配属 `ace_a`、`ace_b` 的两个单位被毁：种子名 `"crew:l07:2"`（`ChildSeed(1, …) == 0x093C87C51BAE1D39`）。`ScriptedRandom [0.3, 0.7]`：`ace_a` → `Dead`（`0.3 < 0.5`），`ace_b` → `Wounded`、`WoundedNightsLeft 2`；之后两夜各 −1 → `Available`（`AceCrewRecovered`）。叙事难度：两者 `Wounded`，`ScriptedRandom []`（空序列）也通过。

**T-05-24 班组夜数函数**
`TonightCrewNights`：`LastFoughtDay 4, ConsecutiveNights 2, day 5 → 3`；`LastFoughtDay 5, 3, day 5 → 4`（同日两段）；`LastFoughtDay 3, 2, day 5 → 1`；`LastFoughtDay 0 → 1`。开始新关卡后王牌 `ConsecutiveNights == 0`。

**T-05-25 自动结算**
使用 T-05-17 的关卡与 00 的迷你波次：`AutoResolveNight()` 后 `NightRecord.AutoResolved true`；传给 `SimWorld` 的 `CarryIn.AutoResolve == (0.95, 1.0)`；世界的命令日志为空；`AutoNightReport.AmmoUsed` 与 `NightResult.Ammo.Weapons[].Shots` 一致。同一关、同一 `runSeed` 运行两次 → 两个 `CampaignState` 序列化逐字节相同。

**T-05-26 关卡结束判定**
- `survive_game_sec 1000`：三个关键夜 `Survived/DurationElapsed`（各 `DurationSec 480`）→ 1440 ≥ 1000 → 完成；第 2 夜 `Survived/AllClear, EndTimeSec 100` → 仍按 480 计。
- E 关卡 `nights [ {1,key}, {2,auto}, {3,key} ]`、`victory survive_nights 2`、`Meta.Nights 2`：普通夜 `Defeated` → 关卡继续（`Setbacks +1`），两个关键夜 `Survived` → `Completed`；第 3 天关键夜 `Defeated` → `Failed`。
- 最后一个条目为 `Quiet` → 处理后直接判定。

### 7.4 跨关、奖励卡、适应（WS05-004 – 006）

**T-05-27 奖励卡加权抽取**
卡池（序数顺序）`c_a w1, c_b w2, c_c w3, c_d w4`（全部 `line A`），`ScriptedRandom [0.5, 0.0, 0.99]`：
第 1 抽 `total 10, r 5.0 → c_c`；第 2 抽 `total 7, r 0.0 → c_a`；第 3 抽 `total 6, r 5.9399999999999995 → c_d`；`PendingCardOffer.CardIds == [c_c, c_a, c_d]`。
- 只有 2 张合格 → 只抽 2 次（脚本 2 个值）；0 张 → `PendingCardOffer == null`，无事件。
- `c_b` 设 `unique true` 且 `Lines[A].Cards` 已含 → 不在池中；`c_d` 设 `from "2023-01"`、关卡日期 2022-11 → 不在池中。
- `ChooseCard("c_c")` → `PendingEffects` 增加 `c_c` 的效果（`TargetLine A`）；`ChooseCard("c_b")`（不在报价中）→ `InvalidArgument`；有待选卡时 `StartLevel` → `PendingChoice`。
- 种子名 `"cards:l07"`：`ChildSeed(1, "cards:l07") == 0xB4CF970168F6C211`。

**T-05-28 跨关节点求值（通用）**
节点 `l04_captured`（3.10.1 的 JSON），`Metrics["escort_survival_frac"]`：`0.75 → 结果 0`、`0.7 → 0`（边界含）、`0.5 → 1`、`0.1 → 2`。结果 0 时 `PendingEffects` 增加 `GrantUnit(captured_spaag, 1, intact, ammoFrac 1.0) @8`；`StartLevel` 第 8 关后花名册含 1 个 `captured_spaag`（`Source Effect`），`PendingEffects` 中该项被移除。`atLeast` 非降序（`[0.4, 0.7, null]`）→ 加载 `E_RANGE`。

**T-05-29 GDD 13.5 每个节点**（`[Theory]`，每行一个用例；度量值直接注入，断言目标关卡开局后的结果）

| 节点 | 注入 | 断言 |
|---|---|---|
| `l03_soviet_stock` | 第 3 关用掉 30 枚（`Rounds 40 → 10`） | 第 6 关 `issue = Min(req, 10)`；影响清单含 `w_sov 40 → 10` |
| `l04_captured` | `escort_survival_frac 0.3` | 第 8 关 1 个 `captured_spaag`，`LightDamaged`，每架余弹 `RoundHalfAway(cap × 0.5)` |
| `l05_volunteers` | 第 5 关结束时花名册有 1 个 `Tag volunteer_fire_team` | 第 15、18 关各 +1 `mobile_fire_team`（带同一标签），`ResourceMods["city"]` 含 +0.1 |
| `l07_patriot_debut` | `patriot_survived 1` / `0` | 第 9、11 关 `ammo:pac3_mse` 含 +0.15 / +0.05 |
| `l09_ambush_doctrine` | 第 9 关完成 | `Lines[A].Doctrines` 含 `forward_ambush`；第 11 关 `CarryIn.Doctrines` 含之 |
| `l09_patriot_loss` | `patriot` 损失 1 | 第 11 关 `patriot` 数 `Max(1, 1 − 1) = 1`（保底）；`Count 2` 时为 1 |
| `l10_evacuation` | `evacuated_frac 0.85 / 0.6 / 0.2` | 第 14 关 B 线新加入王牌 3 / 2 / 1 名 |
| `l12_hangar` | `hangar` 被毁 | 第 13、15、16 关 `FighterSortiesDelta −1`；`FighterSortiesPerNight 0` 的关卡 `CarryIn` 额度计算为 `Max(0, −1) = 0` |
| `l12_runway` | `runway` HP 3/10 | 第 13 关 `FighterSortiesDelta` 再 −1（与机库叠加 = −2） |
| `l14_workshop` | `field_workshop` 存活 | 第 15 关 `Production.Facilities` 有 1 个 `Active` 的 `dispersed`、`OutputStock 10`、+1 `interceptor_drone_team` |
| `l15_handover` | `handed_over 25` | 第 16 关 +2 `interceptor_drone_team`（A 线） |
| `l16_underground` | `hs_ready 1` | 第 17 关 +1 `high_speed_interceptor_team` |
| `l16_17_jet` | `jet_test_facility_ok 1 / 0` | 第 18 关 `jet_interceptor_drone` 6 / 2 个（绝对数，不受 ±20% 夹紧） |
| `l17_repair_plant` | HP 比 1.0 / 0.6 / 0.0 | 第 18 关 `FighterSortiesDelta` 0 / −1 / −2 |

**T-05-30 叙事难度**
`Difficulty Narrative`：`PendingEffects = [AmmoFrac(w_sam, −0.2)@8, UnitCountDelta(u_sam, −1)@8, AmmoFrac(w_sam, +0.1)@8]`、`Trust 10` → `mT = 0`，`ResourceMods["ammo:w_sam"] == 0.1`，`u_sam` 数 2；敌人适应已启用的规则 → `CarryIn.Adaptation == (0, false, [], [])`；王牌不阵亡（见 T-05-23）。

**T-05-31 敌情档案**
`families [geran_jet: geran_3, geran_4, geran_5]`；第 16 关某夜 `KillsByEnemy [ (geran_3, 4), (shahed_136, 2) ]`，又一夜 `(geran_3, 2)`：`Dossier["geran_jet"] = 6`（第二夜跨过 5 → `DossierLevelUp{geran_jet, 1}`）、`Dossier["shahed_136"] = 2`（`shahed_136` 在本夹具中不属于任何家族）。下一夜 `CarryIn.Dossier == [ (geran_3, 0.05, 0.9), (geran_4, 0.05, 0.9), (geran_5, 0.05, 0.9) ]`（`shahed_136` 点数不足 5，不列）。点数上限：`(geran_3, 100)` → `50`。

**T-05-32 城市记忆**
L5（`city c1`）完成且三夜都非挫折 → `CityMemory["c1"] == (1, 1)`；有一夜挫折 → `(1, 0)`。之后另一关（`city c1`）开局 `ResourceMods["city"]` 含 `Min(0.2, 1 × 0.1) = 0.1`；`Victories 3` → 加成 `0.2`。测试关卡（`number null`）不写城市记忆。

**T-05-33 人情**
插曲 `lend_gepard` 选项 0：A 线下一关 `gepard` 数 −1（保底 1）、B 线下一关 +1 `gepard`、`Lines[A].Favors == [ (favor_b_drone_team, OwedBy B, 1) ]`。A 线关卡 `CallFavor(0)` → +1 `interceptor_drone_team`（`Source Favor`、`NightsLeft 1`），`Favors` 为空；再次 → `NoFavor`。

**T-05-34 敌人适应：EMA 与滞回**
`alpha 0.5`、规则 `uav_fly_higher { threshold 0.5 }`、`hysteresis 0.1`；连续四关的 `gun_kill_share` = `0.8, 0.8, 0.3, 0.1`：
`S = 0.4`（未启用）→ `0.6000000000000001`（启用，`AdaptationActivated`）→ `0.45000000000000007`（≥ 0.4，保持）→ `0.275`（< 0.4，停用，`AdaptationDeactivated`）。`HitsTotal == 0` 的关卡 → `S` 不变。

**T-05-35 敌人适应：应用**
已启用 `uav_fly_higher (notBefore 2024-01, 1000)`、`evasive_uav_early (notBefore 2024-09)`、`anti_ew_mix (trigger ew_heavy)`、`suppress_then_strike (trigger silence_heavy)`：
- 关卡日期 2024-05：`CarryIn.Adaptation == (1000, false, [], ["ew_heavy", "silence_heavy"])`。
- 关卡日期 2024-10：`(1000, true, [], ["ew_heavy", "silence_heavy"])`。
- `position_priority (threshold 3)`：单位 `2` 已在 `(1000,1000)` 连续 3 夜，单位 `1` 2 夜 → `PriorityPositions == [(1000,1000)]`；单位 2 白天转移后 → 空。

### 7.5 生产与研发（WS05-009 / 010）

**T-05-36 每日生产**
`production.json` 同 3.13.1，但 `partsEvents [ {parts_cutoff, 0.05, 0.6, 3} ]`；`flow.production { partsPerDay 6, startParts 0 }`；设施 `f1 dispersed (Progress 0.3, Exposure 10)`、`f2 central (Progress 0, Exposure 62)`，均 `Active`、有电、满血；上一夜 `a = 0.25`；`ScriptedRandom [0.9]`（事件不触发）。`Advance(1, 0.25)`：
- `cap = [1.75, 7.0]`，`D = 8.75`，`Parts = 6` → `s = 0.6857142857142857`。
- `f1`：`p = 1.2`，`Progress 1.5` → 产出 1，余 `0.5`；`f2`：`p = 4.8`，产出 4，余 `0.7999999999999998`；`OutputStock += 5`；`Parts == 0.0`。
- 暴露度：`f1 = 10 − 5 + 1.0 × 1.2 = 6.2`；`f2 = 62 − 5 + 3.0 × 4.8 = 71.4` ≥ 70 → `FacilityTargeted{f2.StructureId}`，04 替身收到 `AddStructureTarget`。
- `ScriptedRandom [0.01]` → 事件触发，`eventMult 0.6`，`Events == [(parts_cutoff, 3)]`，日末 −1 → 2。
- `f2` 所在保护目标 `Destroyed` → `f2.Status Destroyed`，`cap_f2 = 0`。

**T-05-37 飞手**
`Pilots 4`、`pilotsPerTeam 2`：部署 2 个 `interceptor_drone_team` → 通过；3 个 → `NoPilots`。`TrainPilots(3)`（`schoolCapacity 4`，城市资源 5）→ `CityResource 2`，`TraineeDaysLeft [5,5,5]`；再 `TrainPilots(2)` → `CapReached`；5 天后 `Pilots 7`。一个班组被毁 → `Pilots 5`。

**T-05-38 研发**
`pointsPerDay 3`，项目 `p1 { cost 20, effect evasive_recover 0.5, setFlag jet_research }`：`SetResearch("p1")`，`DayStep(1)` × 6 → 进度 18；第 7 天 → 21 ≥ 20 → `ResearchCompleted{p1}`、`Flags["jet_research"] == 1`、`ActiveProject null`；之后每夜 `CarryIn.ResearchEffects == [ (evasive_recover, 0.5) ]`。03 按规则得到 `0.6 + 0.4 × 0.5 = 0.8`（03 的测试）。

**T-05-39 上交**
`trustPerUnit 1.5`、`trustCapPerLevel 10`、`HandoverTrust 6`、`OutputStock 10`、`Trust 50`：`HandOver(4)` → `gain = Min(6, 4) = 4` → `Trust 54`、`HandedOver 4`、`Metrics["handed_over"] 4`、`OutputStock 6`；`HandOver(7)` → `InvalidArgument`（`7 > OutputStock 6`）；`HandOver(2)` → `gain 0`、`Trust` 不变。

### 7.6 存档、确定性、天气、指标

**T-05-40 存档往返**
构造覆盖全部字段的 `CampaignState`（两线、库存、档案、适应、待生效效果、进行中的 E 关卡含生产 / 研发、待选卡）。`SaveCodec.Serialize` → `Deserialize` → `Serialize`：两次字节相同；`RunSeed 1` 序列化为 `"0x0000000000000001"`；`SortedDictionary` 键序输出。`version 2`（高于当前）→ `SaveVersionException`；`format "x"` → `SaveFormatException`；`version 0` + 迁移函数（测试注册一个把 `trustA` 改名为 `lines[0].trust` 的 v0 → v1）→ 成功。

**T-05-41 夜间中途存档**
T-00-25 的迷你世界作为关卡第 1 夜：第 300 步存 `NightInProgressSave`（含第 10 步的 `Noop`）；读档重放到 300 → `ComputeStateHash` 相等，继续推进到结束后的 `NightResult` 与未存档的世界逐字段相等。把 `StateHashAtTick` 改一个字符 → 状态回到该夜开头（`Tick 0`），`NightRestartedOnLoad{0}`。

**T-05-42 确定性与拒绝不变**
同一 `CampaignData`、`runSeed 1`、同一动作序列（T-05-17 全流程）跑两遍：每个动作后序列化逐字节相同。任一被拒绝的动作（如 T-05-12 的 `InsufficientTrust`）前后序列化相同、`Events` 为空。

**T-05-43 季节解析**
`SeasonFor(NightDef{Season null}, 2025-12-05) == Winter`；`2026-02-28 → Winter`；`2025-03-01 → Spring`；`2025-08-31 → Summer`；`2025-11-30 → Autumn`；`NightDef{Season Summer}` + 1 月 → `Summer`（数据优先）。

**T-05-44 平衡指标计算器**
- `TrustFloorDwell`：开局信任度 `[[50,30,12,10,14],[50,55,60,58,62],[50,40,15,13,30],[50,45,47,52,49]]`、`min 10`、`margin 5` → `5 / 20 = 0.25`（> 0.15，不达标）。
- `ResourceSpread`：`strong [100,120,118]`、`wasteful [100,80,82]` → 比值 `[1.0, 1.5, 1.4390243902439024]` → 最大 `1.5`（达标，恰为上限）。
- `WinGapSlope`：`gap [0.10,0.12,0.15,0.13,0.20]`（关卡 1–5）→ 斜率 `0.021`（容差 1e-12；> 0.02，不达标）。
- 分母为 0（无失败关卡）→ `RecoveryRate == null`。

### 7.7 战役流程（WS05-008）

**T-05-45 解锁、插曲、完成**
`campaign.json levels [l01(AB), l02(B), l03(A)]`：初始只有 `l01` 解锁；`StartLevel("l02")` → `LevelLocked`。`l01` 完成 → 无奖励卡（AB）；`l02` 完成 → 抽卡；未选卡时 `StartLevel("l03")` → `PendingChoice`。插曲 `afterLevel 2` → `PendingInterlude`，`ChooseInterlude(5)`（越界）→ `InvalidArgument`。全部完成 → `CampaignCompleted`。

**T-05-46 重试**
L5 第 2 夜 `Defeated` → `Failed`，A 线 `Trust 41 → 33`（`levelDefeatPenalty 8`）、`Setbacks 1`。`RetryLevel`：花名册、库存、弹药恢复到开局快照；`Trust == 33`、`Setbacks == 1`（保留）；`Attempt 2`；第 1 夜种子与第一次相同（`NightSeed(1, "l08", 1)`）；阶段 `Briefing`。

---

## 8. 待决问题

### 8.1 新参数（全部待决；默认值即 1.2 / 1.3 / 1.4 / 3.13 / 3.14 中的 JSON）

| 参数 | 建议默认值 | 理由 |
|---|---|---|
| `trust.initial / min / max / neutral` | 50 / 10 / 100 / 50 | 0–100 量表与暴露度一致，便于界面；下限 10 = GDD 9.5"信任度有下限" |
| `trust.availableFromLevel` | 6 | GDD 12.3：交换比与信任度第 6 关引入 |
| `trust.exchangeBands` | `<0.5:−3, 0.5–2:−1, 2–5:0, 5–20:+1, ≥20:+3` | 用分档代替对数，避免超越函数、便于调；中性区 2–5 让"正常打法"不加不减 |
| `trust.minShotCostForExchangeMusd` | 0.5 | 只开几枪机枪不评价 |
| `trust.wastefulWeapon` | 平均单发 ≥ 1 M$ 且该武器比值 < 0.1；每发 −1，每夜最多 −5 | "PAC‑3 打 Shahed"（4 / 0.05）比值 ≈ 0.0125 |
| `trust.inquiry` | ≥ 2 发浪费 → 额外 −3 | 一发误射不至于质询 |
| `trust.hoardedLeak` | 每次 −2，每夜最多 −6 | 03 的 `HighThreatLeaksWithReserve` |
| `trust.nightDeltaClamp` | −12 / +8 | 不对称：一夜崩盘不至于直接跌到底；好表现需要多夜积累 |
| `trust.levelVictoryBonus / levelDefeatPenalty` | +5 / −8 | |
| `trust.quotaModMaxFrac` | 0.10 | GDD 13.2 ±10–20% 中信任度占一半，另一半留给节点 / 奖励卡 |
| `trust.requestCost` | small 8 / large 20 | 数值表 1.6 只写"一般 / 大" |
| `crossLevelModClamp` | ±0.2 | GDD 13.2 上限 |
| `cityResource.startDays / cap / alertPauseWeight` | 1 / 30 / 0.5 | cap ≈ 一周积累，防囤积滚雪球 |
| `cityResource.shop` 价格 | 火力组 2、声学哨 0.5、观察哨 0.5、拦截无人机班组 3（2025-01 前）、维修队 2（+2 运力 / 白天，每关 2 个） | 数值表 1.2 价格比例的抽象；GDD 9.2 列出的"机枪、探照灯"在数据中没有对应单位（Q-E5） |
| `supply.logisticsPerWindow` | 10 | 约等于补 20 枚中程导弹或 5 枚 PAC‑3 |
| `supply.roundCostByAmmoSupply` | ample 0 / medium 0.05 / limited 0.5 / scarce 1 / none 1 | 稀缺度越高越占运力 |
| `supply.roundCostByWeapon` | pac2 2、pac3_mse 2、aster_30 1.5 | 体积 / 稀缺 |
| `repair.*` | 轻伤 2 运力 1 天；部件损毁 5 运力 3 天；保护目标每天修复 10% | "先修雷达还是先补弹药" |
| `relocation.timeSlotsPerDay / slotGameSec / surveyTimeSlots / dayExposureDecayPerDay` | 3 / 30 / 1 / 20 | Patriot（30 + 45）= 3 槽 = 一整天；静默一天 ≈ 夜间静默 40 游戏秒的降幅 |
| `emergencySupport` | 连续 2 次挫折（失败或加权损失 ≥ 30%）；+1 指挥点、+20% 配额弹药、信任度抬到 30；每关一次 | GDD 9.5 |
| `requests[]` | `req_nasams_loan`（大、3 天到、2 夜）、`req_pac3_rush`（小、1 天到、8 枚） | GDD 9.2 的两个例子 |
| `crew.*` | 被毁时王牌阵亡 50%，否则伤 2 夜；每命中 1 经验 | GDD 8.7"可能永久阵亡" |
| `autoResolve.*` | 拦截 ×0.95、暴露 ×1.0、观看奖励信任度 +1 | 自动结算本已不用指挥点；额外惩罚取小值，由 WS09 用 `AutoResolveGap` 校准 |
| `adaptation.*` | `alpha 0.5`、滞回 0.1、五条规则阈值见 1.3 | 两关内对打法变化有反应、不会因一关偶然而摆动 |
| `adaptation.statClasses` | gun：`gun, gun_radar`；drone：`interceptor_drone, jet_interceptor_drone` | 拦截类别名来自 `intercept.json` |
| `dossier.*` | 每击落 1 点、上限 50；5 点：甄别 +0.05、分类时间 ×0.9；20 点：+0.10、×0.75 | |
| `cityMemory.*` | 每次"守好"+10%，上限 20% | GDD 13.3 |
| `rewardCards.offerCount` | 3 | GDD 13.2 |
| `production.*`、`research.*`、`power.*` | 见 3.13.1、3.14 | M5 再调 |
| `balanceTargets` | 见 1.3 | WS09 依据 |

### 8.2 设计待决（需要人决定）

| # | 问题 | 背景 | 建议默认值 |
|---|---|---|---|
| Q-E1 | 信任度是"可花费的货币"还是"只读的评价"？ | GDD 9.2 既说"用于申请增援"，13.3 又说"下一关资源 ±10–20%" | 两者兼有：申请会扣信任度，同时开局按信任度给 ±10% 修正（花掉信任度 = 牺牲下一关的配额，是有意的取舍） |
| Q-E2 | 浪费判定按武器聚合还是逐发？ | 03 的 `NightResult` 只有按武器的汇总（`ByWeapon`） | 按武器聚合（3.4.2）；若试玩发现"PAC‑3 打一枚 Kh‑101 + 三架 Shahed 被平均掉"，再请 03 增加逐发记录 |
| Q-E3 | 伊朗战争 PAC‑3 减半作用于哪些环节？ | GDD 9.6"补给减半" | 开局配额与白天补给、弹药申请都减半；已持有的不减；结束月份待定（数值表 5.3） |
| Q-E4 | 全国库存"保底"的含义 | GDD 13.3 只说"有保底" | 库存降到保底后不再减少（每关至少还能领到保底数量）；另一解释是"每关最少发放 X 枚、但库存仍会耗尽为 0"——若选后者需改 3.3.4 |
| Q-E5 | 城市商店的"机枪、探照灯"在数据中没有单位 | GDD 9.2 | 机枪 = `mobile_fire_team`；探照灯作为单位设置 `NightAids`（02）的可购买项，需要新增 `cityResource.shop` 的 `kind: night_aid` 与库存计数（M3 实现前确定） |
| Q-E6 | `availableUnits[source=city].count` 是"可购买上限"还是"开局免费数量"？ | test_01 写的是 `city` 来源 4 个火力组 | 可购买上限；免费数量由 `cityResource.startDays` 折算的开局资金体现。若希望开局即有，改为"开局给 `count`、之后不能再买" |
| Q-E7 | AB 关卡（第 1、18 关）的信任度归属 | GDD 13.2"两线分开计算" | 夜间变化两线都生效；申请指定付款线 |
| Q-E8 | 比例修正作用于哪些资源？ | GDD 13.3"下一关资源 ±10–20%" | 配额级弹药、城市资源、补给运力；**不**作用于单位数量（1 套 Patriot × 1.2 仍是 1）与全国库存 |
| Q-F1 | 结构 D 与 C 的区别如何体现？ | GDD 11.4 D"不分昼夜、压缩比更高" | D 的白天缺省为 `Interlude`（只有时间槽，补给只在 `supplyWindows` 列出的日子） |
| Q-F2 | 结构 E 普通夜没有 `supplyWindows` 时每天都给 10 运力是否过多？ | | 建议 E 关卡必须写 `supplyWindows`（加载校验 E 无此数组 → 警告） |
| Q-F3 | 自动结算夜以 `Defeated` 结束是否算关卡失败？ | GDD 11.5 只说"生成战报" | 不算失败，只计挫折与损失；否则自动结算的惩罚过重 |
| Q-F4 | 自动结算"略逊于"用哪种方式？ | 00 Q11 | 三项叠加（3.8.2）：不用指挥点 + 拦截 ×0.95 + 暴露 ×1.0；由 `AutoResolveGap` 校准 |
| Q-F5 | 重试关卡是否换种子？ | GDD 未说 | 不换（相同的夜晚，便于玩家针对性调整）；若希望每次不同，种子名改为 `night:{levelId}#{attempt}:{n}` |
| Q-F6 | 关卡中途到达的增援放在未勘察阵地是否有首夜惩罚？ | GDD 11.3 只说"关卡开始前的部署无惩罚"和"转移到新阵地" | 有（视同新阵地） |
| Q-F7 | 失败时扣的信任度在重试时是否恢复？ | | 不恢复（失败有代价），但紧急支援会在重试时发放 |
| Q-F8 | `survive_nights` 只计关键夜？ | schema：`nights` = "需要亲自指挥的夜晚数" | 只计 `Key`（含被观看的普通夜不计入，避免观看改变胜负条件） |
| Q-F9 | `Crippled` 单位能否带伤部署？ | 03：雷达被毁 / 少一个发射架时仍能部分工作 | 不能，必须先维修（简化白天决策）；若希望能带伤上阵，删去 3.7.1 第 3 条的 `Crippled` 限制即可 |
| Q-C1 | "连续 3 夜以上"是否含第 3 夜？ | GDD 8.7；`intercept.json minConsecutiveNights 3`；03 用 `≥` | 含（第 3 个连续夜起疲劳）；若不含，把数据改为 4 |
| Q-C2 | 普通班组的疲劳是否跨"同日白天段 + 夜间段"累积？ | 第 18 关 24 小时 | 累积（算连续） |
| Q-C3 | 王牌经验 `Xp` 的用途（特长、倍率成长 1.1 → 1.2） | GDD 8.7"保留经验和特长"；数值表"×1.1–1.2"；数据只有单值 1.15 | 先只记录；倍率成长需要在 `crews.json` 增加 `probMultByXp` 表，交给 03 读取 |
| Q-C4 | 王牌在两线之间能否流动？ | GDD 只说"每条线 3–5 个" | 不能（各线独立名单） |
| Q-L1 | 跨关节点各效果的具体数值 | GDD 13.5 只给方向 | 3.10.2 表中的数值，全部 `provisional` |
| Q-L2 | 节点需要的单位 / 保护目标 ID（`captured_spaag`、`high_speed_interceptor_team`、`hangar`、`runway`、`field_workshop`、`aviation_repair_plant`、`test_facility`）不存在 | 关卡数据未制作 | 制作第 4、12、14、16、17 关数据时按此 ID 建立；`captured_spaag` 的原型待 WS10 考据 |
| Q-L3 | 组合条件度量（第 7、16、17 关）由谁计算？ | `atLeast` 只能表达单阈值 | 在 `sim/Campaign/Links/DerivedMetrics.cs` 写死 3 条命名规则（`patriot_survived`、`hs_ready`、`jet_test_facility_ok`），`flow.levelMetrics` 用 `source: "derived:<名>"` 引用 |
| Q-L4 | 条令 `forward_ambush`、`fire_team_network` 的具体效果 | GDD 13.3 只有名字 | `forward_ambush`：前推区域（`frontline` 约束区附近）部署的远程系统首次开机前不累积侦察暴露（02）；`fire_team_network`：火力组之间共享航迹，2 个以上火力组同时看到时升为"大致"（02） |
| Q-L5 | 敌情档案按"击落"还是"残骸落在己方区域"计？ | GDD"回收残骸" | 按击落计（简单）；若要区分，需 03 在 `KillsByEnemy` 中只计拦截点在地图内且不在前线风险区的 |
| Q-L6 | 敌人适应是否两线共享？ | GDD 7.4"针对玩家的主要打法" | 共享（敌人是同一个） |
| Q-L7 | 敌人适应的效果是否允许早于史实？ | GDD 13.4 例 1"2024–25 年真实变化" | 用 `notBefore` 限定（默认：飞高 2024-01 起、规避 2024-09 起，即最多提前一年） |
| Q-P1 | 生产随机事件"关键零件断供 −40%"作用于零部件还是产量？ | GDD 10.2 | 作用于产量（`outputMult 0.6`） |
| Q-P2 | 飞手瓶颈的形式 | GDD 10.2"没有飞手，无人机飞不起来" | 每个拦截无人机班组需要 2 名飞手；班组被毁损失飞手 |
| Q-P3 | 电力三方分配的需求参数 | GDD 10.1 第 17 关 | `power.productionNeed / radarNeed / heatingNeed` 由第 17 关数据给出；供暖不足按天扣信任度（市长 / 民意） |
| Q-S1 | 存档的战役数据哈希不一致时 | 平衡补丁会改数据 | 警告后继续 |

### 8.3 需登记到 00

| 编号 | 表 / 位置 | 内容 |
|---|---|---|
| R-00-1 | 00 2.6 `PlacedUnit` | 追加 `int RosterId`（缺省 0 = 非战役单位）；`Create` 第 8 步按 `RosterId` 把 `CarryIn.Units` 应用到实体；实体保存 `RosterId`（**不哈希**，同 `Placement`） |
| R-00-2 | 00 2.6 `CarryIn` | 字段全集见 2.4.1（`Units`、`Structures`、`AmmoPool`、`PerLevelUsed`、`AlertResponsiveness`、`KnownTargets`、`CommandPointsBonus`、`FighterSortiesDelta`、`ActiveSupports`、`Doctrines`、`Dossier`、`Adaptation`、`AutoResolve`、`ResearchEffects`）；须可 JSON 序列化（回放 `config.carryIn`） |
| R-00-3 | 00 3.1.5 | 战役模式的夜晚种子为 `NightSeed(runSeed, levelId, flow 下标 + 1)`（不一定等于 `NightIndex`）；`runSeed` 由 05 保存（关闭 00 Q10） |
| R-00-4 | 00 4.1 | 05 段 500–599 用于三个**战役层** enum：`CampaignActionType`、`CampaignRejectReason`、`CampaignEventType`（4.1–4.3）；`SimEventType` / `SimCommandType` 在 05 段不新增任何值 |
| R-00-5 | 00 3.5 `NightResult.CarryOut` | 类型定义见 2.4.2（`Units`、`KnownTargets`、`PlayStats`、`KillsByEnemy`、`CustomMetrics`），由 `ScoringSystem.BuildResult` 填写 |
| R-00-6 | 00 1.1 | "`campaign/` 不由模拟层读取"改为"不由 `DataLoader.LoadLevel` 读取；由 `CampaignDataLoader`（`sim/Campaign/Data`）读取"；新增文件 `rules/campaign.json`（`kind: campaign_rules`，不进全局目录）与 `levels/<id>/flow.json`（`kind: level_flow`，可选；**不**计入 `LevelData.LoadedFiles`，由战役数据哈希覆盖） |
| R-00-7 | 00 1.6 `RulesSet.Economy` | `EconomyRulesDef` 追加 1.2 的块：`Trust`、`CrossLevelModClamp`、`CityResource`、`Supply`、`Repair`、`Relocation`、`EmergencySupport`、`Requests` |
| R-00-8 | 00 0.5 项目结构 | 新增目录 `sim/Campaign/`、`sim/Economy/`、`sim/Save/`、`sim/Production/`、`sim/Research/`（`sim/Crew/`、`sim/Environment/` 已在列表中）；`sim/Save/` 不做文件 I/O |
| R-00-9 | 00 Q11 | 自动结算的修正项走 `CarryIn.AutoResolve`（不加 `SimConfig.AutoResolve`） |
| R-00-10 | 00 1.4 形态 C | `cards.json` 的 `from` / `until`、`cityResource.shop[].until`、`adaptation.rules[].notBefore` 按同一语义（不含 `until` 当月）由 `CampaignDataLoader` 判定 |

**需要其他规格实现的接口**（不改 00，但请对应规格的作者确认）：

| 编号 | 规格 | 内容 |
|---|---|---|
| R-01-1 | 01 | `waves.json` 的 `waves[]` 与 `groups[]` 增加可选 `adaptiveTrigger: string`（只在 `CarryIn.Adaptation.ActiveTriggers` 含之时生成）与 `adaptiveSubstitutes: [{trigger, enemy}]`（触发时替换 `enemy`）；`CarryIn.Adaptation.UavAltitudeAddM` 加到 `Tag == UAV` 的弹药巡航高度 |
| R-01-2 | 01 / 02 | `waves.json nights[].timeOfDay`（`night` / `day`，缺省 `night`）→ `NightDef.TimeOfDay`（02 Q26 已提出）；`EnvironmentResolver.SeasonFor` 放在 `sim/Environment/`，02 / 03 需要季节时调用 |
| R-02-1 | 02 | 读取 `CarryIn.Dossier`（诱饵甄别 `+DiscriminationAdd`、分类 / 升级时间 `× ClassifyTimeMult`）、`CarryIn.AutoResolve.ExposureGainMult`（只乘正增量）、`ResearchEffects.ew_effectiveness_add`；`Threat` 增加"曾处于电子战覆盖"粘性标记供 `PlayStats.ThreatsEverEwCovered` |
| R-02-2 | 02 | `CarryIn.Units[].Exposure` 作为初始暴露度、`SeenThrough` 与 `DeceptionNightsLeft` 初始化欺骗单位（02 8.x 对齐项）；`FirstNightAtNewPosition` 沿用 `PlacedUnit` 字段 |
| R-03-1 | 03 | `BuildResult` 填写 `CarryOut`（2.4.2）：逐单位余弹（被毁单位取被毁前一刻）、`RadarDestroyed`、`LaunchersLost`、`Hits`；`PlayStats`（`ArmThreatDetected` 计数、`EmitterSwitched{Cause ArmShutdown}` 计数、`ThreatsSpawned`、曾受电子战覆盖的目标数）；`KillsByEnemy` |
| R-03-2 | 03 | `CarryIn.AmmoPool` 非 null 时代替 `Meta.AmmoQuota` 作为弹药池；`CarryIn.PerLevelUsed` → `PerLevelUsedBefore`；`CarryIn.Structures` → `Hp / LossHp`；`CarryIn.FighterSortiesDelta`；`CarryIn.ActiveSupports`（邻近扇区覆盖的夜内效果）；`CarryIn.AutoResolve.InterceptProbMult` 作为额外乘子；`ResearchEffects.evasive_recover`；`Adaptation.ForceEvasiveUav` |
| R-04-1 | 04 | `KnownTargetCarry` 类型及 `IsScouted(Vec2)`、`OnUnitRelocated(int, Vec2)`、`OnUnitRemoved(int)`、`AddStructureTarget(string)`；`Adaptation.PriorityPositions` 加入已知目标清单；`DeploymentValidator.ValidatePosition(level, unitDefId, pos)`；指挥点 = `commandPointsPerNight + CarryIn.CommandPointsBonus`（截断到 `economy.commandPointsPerNight.max`） |

### 8.4 与其他规格的边界问题

| # | 问题 | 涉及 | 建议 |
|---|---|---|---|
| B1 | WBS 01.B 把"信任度变化"写在 `ScoringSystem`（13）里 | 03 / 05 | 夜内不改信任度；03 只产出原始统计，05 的 `TrustRules.ForNight` 结算。03 若想在复盘界面实时预览，可调用同一纯函数（不进状态） |
| B2 | `HighThreatLeaksWithReserve` 的"有储备"由 03 用 `HeldByRule` 判定 | 03 / 05 | 05 直接使用；不另算"夜末余弹" |
| B3 | 新阵地首夜惩罚有两个入口：02 读 `PlacedUnit.FirstNightAtNewPosition`，03 的 `FireUnit.NewPositionFirstNight` 写"由 `CarryIn` 给出" | 02 / 03 / 05 | 统一为 `PlacedUnit.FirstNightAtNewPosition`（05 填），03 改为读同一字段 |
| B4 | 03 的 `CrewConsecutiveNights` 语义 | 03 / 05 | 05 定义为"含今晚的连续作战夜数"（3.7.5），03 的 `≥ minConsecutiveNights` 判定保持不变 |
| B5 | 夜间弹药池（03 `AmmoPoolRemaining`）与 05 的 `Depot` | 03 / 05 | 是同一个东西：05 每夜把 `Depot` 作为 `CarryIn.AmmoPool` 交给 03，夜末从 `PoolRemaining` 取回；03 夜间不从池装填，05 在夜前装填 |
| B6 | 夜间转移（04 部署状态机）后的位置是否算"新阵地"、是否勘察 | 02 / 04 / 05 | 夜内由 02 / 04 重算 `NewPositionPenalty`；05 只在白天转移与夜末读 `CarryOut.Units[].Pos` |
| B7 | 空袭警报"工厂停工、城市资源停止积累" | 03 / 05 | 03 输出 `AlertActiveSec`、工厂 `PausedSec`；05 用 `alertPauseWeight` 折算城市资源与生产 |
| B8 | 城市韧性（02 `UrbanNavJamCityResiliencePerNight`）的去向 | 02 / 03 / 05 | GDD 没有"城市韧性"这一资源；建议并入城市资源：每次触发 `CityResource −= 1`（需要 03 在 `NightResult` 中输出触发标记），待人决定 |
| B9 | 战斗机额度 `fighterSortiesPerNight` 的跨关修正 | 03 / 05 | 05 只给 `FighterSortiesDelta`，03 计算 `Max(0, base + delta)` |
| B10 | 大空袭标记 | 03 / 05 | 沿用 03 新增的 `waves.json nights[].bigRaid`；05 只用于预警 |
| B11 | 关卡专用胜负度量（护送存活率、撤离比例、补给车通过率） | 02 / 03 / 05 / WS02 | 由关卡专用规则写入 `CarryOut.CustomMetrics`；归属规格未定（建议在 03 增加"关卡目标"扩展点） |
| B12 | 天气 / 季节 / 昼夜的夜内效果（冬季设备效能、电网压力） | 02 / 03 | 不在 05；05 只提供 `timeOfDay` 数据字段与 `SeasonFor` |
| B13 | `adjacent_sector_coverage` 的夜内效果 | 03 | 05 只放进 `CarryIn.ActiveSupports`；03 当前把信任度支援一律拒绝（03 3.4 表第 2 行），需要补夜内实现 |
