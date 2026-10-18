# data/ 数据约定

`data/` 是游戏**唯一的数值来源**。代码中不写死数值；调平衡只改这里。
来源文档：[塔防数值表 v1.2](../docs/塔防数值表_v1.md)（下称"数值表"）。

## 1. 目录

| 路径 | 内容 | Schema |
|---|---|---|
| `units/air_defense.json` | 防空单位（"枪"）及其武器 / 弹药 | `schema/air_defense.schema.json` |
| `units/sensors.json` | 探测单位（"眼"） | `schema/sensor.schema.json` |
| `units/ew.json` | 电子战单位（"盾"） | `schema/ew.schema.json` |
| `units/deception.json` | 欺骗单位（"假"） | `schema/deception.schema.json` |
| `support/support.json` | 呼叫型外部支援 | `schema/support.schema.json` |
| `support/fighters.json` | 战斗机性能（外部支援所用的机型） | `schema/fighter.schema.json` |
| `enemies/munitions.json` | 敌方导弹、无人机、滑翔炸弹 | `schema/enemy_munition.schema.json` |
| `enemies/platforms.json` | 敌方飞机、直升机、侦察 / 打击无人机平台 | `schema/enemy_platform.schema.json` |
| `rules/*.json` | 19 个规则参数文件：拦截概率、精度、伤害、暴露度、辐射策略、碎片、航迹质量、电子战、阵地与欺骗、支援、经济、敌方运动、地形与地平线、交战与火控、民防与电网、敌方 AI、战中指令、战役跨夜与适应（含单位/支援/敌方/本地化共 28 个全局数据文件） | `schema/rules.schema.json` |
| `loc/zh.json` | 本地化文本（中文为源语言） | — |
| `levels/<id>/level.json` | 关卡元数据：主角线、日期、时间结构、战斗机模式、地图尺寸与高程图、可用单位、配额、胜负条件 | `schema/level.schema.json` |
| `levels/<id>/waves.json` | 进入点与每夜的波次 | `schema/waves.schema.json` |
| `levels/<id>/intel.json`、`events.json`、`flow.json`（可选） | 每夜情报（可能不准确）、剧情事件、多夜/时间流转片段 | `schema/level_content.schema.json` |
| `levels/<id>/map/layers.json`、`structures.json`、`grid.json`、`deploy.json` | 矢量图层、保护目标、电网拓扑、部署区域 | `schema/map.schema.json` |
| `levels/<id>/map/heightmap.png` | 16 位灰度高程图；像素 (0,0) 为西北角，比例和海拔范围写在 `level.json` | — |

> `rules/` 是 WBS 0.5 节之外新增的目录：数值表第 3 节的规则参数不属于任何单位，单独存放。
>
> **地图坐标**：单位米，原点在地图西南角，x 向东、y 向北（与模拟层一致，WBS 01.A）。地图外的点（进入点、航点）可以是负数或超出地图尺寸。

## 2. 单位与字段命名

**JSON 沿用数值表的单位，字段名带单位后缀**；模拟层加载时统一换算成米和世界秒。

| 后缀 | 单位 | 加载时换算 |
|---|---|---|
| `Km` | 游戏 km（1 格 ≈ 1 km） | × 1000 → 米 |
| `M` | 米 | — |
| `GameSec` | 游戏秒 | × 60 → 世界秒（见 `rules/conventions.json`） |
| `Kmh` | km/h | ÷ 3.6 → 米/秒 |
| `Musd` | 百万美元 | — |
| `Cells` | 格（1 格 ≈ 1 km） | × 1000 → 米 |
| `PerGameSec` | 每游戏秒 | ÷ 60 → 每世界秒 |
| `Pct` | 百分比（0–100） | ÷ 100 → `…Frac`（0–1 比例） |
| `Deg` | 度（角度） | × π / 180 → `…Rad`（弧度） |
| `PerDay` / `Days` / `Nights` / `Day` | 战役时间单位（天 / 夜） | —（战役层直接使用，不换算为世界秒） |

- **Mach 换算**：1 Mach = 1200 km/h（游戏约定，不区分高度）。原始写法保留在 `_source` 中。
- **保留但未消费字段**：`enemies/munitions.json` 与 `enemies/platforms.json` 中的 `hp` 为数值表原始归档字段，模拟层按单发命中概率（`rules/intercept.json`）一次判定击毁，不读取敌方 `hp`（见 `B-T3-03`）。
- 日期：`"YYYY-MM"`，表示该月起生效。
- 显示文本一律通过 `nameKey` 等本地化键引用 `loc/zh.json`，数据里不直接写中文名。

## 3. 区间取值规则

数值表中的区间（如 `4.5–6.5`）在 JSON 中**只存一个游戏值**，原始写法放在 `_source` 中供参考。调平衡时只改游戏值。

| 字段类型 | 取值 | 例子 |
|---|---|---|
| 能力类：射程、射高、探测距离、作用半径、速度、伤害、投放距离 | **上限** | 射程 4.5–6.5 → 6.5 |
| 成本类：系统价格、单发成本 | **中值** | 15–30 → 22.5 |
| 数量类：弹仓、携弹量、额度、架次、持续夜数 | **下限** | 弹仓 2–4 → 2 |
| 时间类：响应延迟、持续时间 | **中值** | 6–10 → 8 |
| 概率 | **中值** | 30–60% → 0.45 |

例外：本身就是**随机范围**的规则（精度档的落点偏移、伤害造成的建筑损毁数）和**飞行高度剖面**（`altitudeM`，如 Kh‑101 的 30–70 m）保留 `min` / `max`，由模拟层用 `SimRandom` 掷骰或按剖面使用。

## 4. 合并行的拆分

- 数值不同 → 拆成独立条目（如 Strela‑10 / Osa‑AKM → `strela_10`、`osa_akm`）。
- 数值完全相同 → 合并为一个条目（如 Igla / Stinger / Piorun → `manpads`）。
- Patriot → 一个发射单元 `patriot` + 两种武器 `pac2`、`pac3_mse`。
- **相同的武器 ID 出现在多个单位中 = 共享弹药池**（如 `s300ps` 与 `s300pt` 都用 `s300_missile`，对应 A 线全国共享库存）。共享武器的定义必须完全一致。

## 5. 暂定值（provisional）

数值表没有给出、由 AI 起草的数值，在条目中用字段级标记：

```json
"provisional": { "weapons[0].interceptClass": "数值表 3.3 未给 Gepard 归类，暂定新类 gun_spaag" }
```

**带 `provisional` 的数值需要人审核**；确认后补进数值表（v1.2），并删除标记。

## 6. 数值表条目 → 数据 ID 对照

### 1.1 / 1.2 防空单位 → `units/air_defense.json`

| 数值表 | ID |
|---|---|
| 单兵防空（Igla / Stinger / Piorun） | `manpads` |
| Starstreak / Martlet | `starstreak_martlet` |
| 机动火力组 | `mobile_fire_team` |
| ZU‑23‑2 / S‑60 牵引高炮 | `zu23_2`、`s60` |
| Sky Sentinel | `sky_sentinel` |
| Gepard | `gepard` |
| Skynex / Skyranger 35 | `skynex`、`skyranger_35` |
| Strela‑10 / Osa‑AKM | `strela_10`、`osa_akm` |
| Avenger / Stormer HVM | `avenger`、`stormer_hvm` |
| VAMPIRE | `vampire` |
| Raven / Gravehawk | `raven`、`gravehawk` |
| Crotale NG | `crotale_ng` |
| RBS 70 | `rbs_70` |
| IRIS‑T SLS | `iris_t_sls` |
| FrankenSAM | `frankensam` |
| Buk‑M1 | `buk_m1` |
| Hawk Phase III / Aspide | `hawk`、`aspide` |
| NASAMS | `nasams` |
| IRIS‑T SLM | `iris_t_slm` |
| S‑300PS / PT | `s300ps`、`s300pt` |
| SAMP/T | `samp_t` |
| Patriot PAC‑2 / PAC‑3 | `patriot`（武器 `pac2`、`pac3_mse`） |
| S‑200 | `s200` |
| 拦截无人机班组 | `interceptor_drone_team` |
| 喷气式拦截无人机 | `jet_interceptor_drone` |
| 电子战 / GNSS 欺骗站（1.1 行） | 见 `units/ew.json`：`area_nav_jammer`、`nav_spoofer` |
| 声学探测网（1.1 行） | 见 `units/sensors.json`：`acoustic_post` |
| F‑16 / Mirage 2000 / MiG‑29（1.1、1.2 行） | 见 `support/fighters.json`：`fighter` |

### 1.3 探测 → `units/sensors.json`

`national_early_warning`、`soviet_long_range_radar`、`soviet_mid_range_radar`、`western_3d_radar`、`gap_filler_radar`、`acoustic_post`、`visual_observer`、`radio_detector`、`civilian_reports`、`tethered_balloon`；航迹质量规则 → `rules/tracks.json`

### 1.4 电子战 → `units/ew.json`

`area_nav_jammer`、`nav_spoofer`、`counter_uas_jammer`、`handheld_counter_uas`、`vehicle_shield`；国家级导航欺骗 → `support/support.json` 的 `national_gnss_spoof`；效能衰减与副作用 → `rules/ew.json`

### 1.5 欺骗 → `units/deception.json` + `rules/positions.json`

`decoy_emitter`、`sacrificial_radar`、`fake_launcher`；备用阵地 / 新阵地 → `rules/positions.json`

### 1.6 外部支援 → `support/support.json`

`fighter_area_patrol`、`fighter_directed_intercept`、`fighter_apkws_hunter`、`national_gnss_spoof`、`neighbor_fire_teams`、`adjacent_sector_coverage`；战斗机可用性与空域协调 → `rules/support.json`

### 2.1 / 2.2 敌方弹药 → `enemies/munitions.json`

`gerbera`、`shahed_136`、`geran_2_heavy`、`geran_3`、`geran_4`、`geran_5`、`lancet`、`fpv_fiber`、`kh101`、`kalibr`、`iskander_k`、`kh59`、`banderol`、`oniks`、`kh22`、`kh32`、`kh31p`、`s300_ground`、`kn23`、`iskander_m`、`iskander_m_mod`、`kinzhal`、`zircon`、`oreshnik`；`fab250`、`fab500`、`fab250_umpk`、`fab500_umpk`、`fab1500_umpk`、`fab3000_umpk`、`umpb_d30`、`umpb_5r`

### 2.3 敌方平台 → `enemies/platforms.json`

`attack_helicopter`、`su25`、`su24m`、`su34`、`su35s`、`tu22m3`、`mig31k`、`strategic_bomber`、`orion`、`orlan_10`、`a50u`

### 第 3 节与全局规则 → `rules/`（共 15 个规则文件；连同 4 个 `units/`、2 个 `support/`、2 个 `enemies/`、`campaign/campaign.json`、`campaign/cards.json`、`loc/zh.json` 共 26 个全局数据文件）

| 数值表 / 规格 | 文件 |
|---|---|
| 0 通用约定（时间、格、价格） | `conventions.json` |
| 3.1 精度档 | `accuracy.json` |
| 3.2 伤害等级 | `damage.json` |
| 3.3 拦截概率与修正 | `intercept.json` |
| 3.4 暴露度 | `exposure.json` |
| 3.5 辐射策略 | `emission.json` |
| 3.6 碎片 | `debris.json` |
| 1.3 航迹质量与探测修正 | `tracks.json` |
| 1.4 电子战抗干扰演进与副作用 | `ew.json` |
| 1.5 备用阵地、新阵地与欺骗识破 | `positions.json` |
| 1.6 战斗机可用性与空域协调 | `support.json` |
| 4 经济、信任度、城市资源与补给维修 | `economy.json` |
| 01 高度带与俯冲运动学 | `movement.json` |
| 01 地形视线与地球曲率参数 | `terrain.json` |
| 03 交战时序与发射分配规则 | `engagement.json` |
| 03 电网、空袭警报与结算评分 | `civil.json` |
| 04 敌方战术 AI 与绕行参数 | `enemy_ai.json` |
| 04 指挥点消耗与二选一参数 | `commands.json` |
| 05 战役推进、适应规则与平衡目标 | `campaign.json` |
