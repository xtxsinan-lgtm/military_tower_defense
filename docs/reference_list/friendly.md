# 装备外观参考清单 · 我方单位（WS10-003）

> 资料截至 2026-10-15。单位清单按 `data/units/air_defense.json`、`data/units/sensors.json`、`data/units/ew.json`、`data/units/deception.json`、`data/support/fighters.json` 中的顺序和 ID 排列，显示名取自 `data/loc/zh.json`。

## 用途说明

- 本清单是 **3D 建模 / 预渲染精灵** 和 **校正 AI 生成模型** 时的外观对照表（WS03-006 参考图收集、WS03-007 首批底模的前置）。
- **只写可见外形**：车辆组成、发射筒 / 天线的形状和排列、底盘、涂装、画面尺度。**不写**射程、探测距离、频段、功率、制导方式等技术参数（GDD 第 17 章第 5 条）。电子战设备只写外观。
- "画面尺度提示"只是长度等级，用于确定精灵尺寸，不是数据。
- 带 ≈ 的条目表示公开资料不足或版本差异大，**建模前必须对照参考照片人工确认**。AI 生成的军事装备图像 / 模型常有结构错误，一律标注"待人工校正"后再使用（AGENTS.md 第 8 节）。
- Commons 分类链接均已用 Commons API 确认存在（2026-10-15）；找不到对应分类的写"未找到"。维基条目链接同样已确认存在。
- 首批建模对象（WS03-007）：S‑300、Buk、Gepard、Patriot、IRIS‑T、火力组皮卡。下文对应 6 节写得更详细。

## 总表

| # | ID | 显示名 | 类别 | 尺度等级 | WS03-007 首批 |
|---|---|---|---|---|---|
| 1 | `manpads` | 单兵防空（Igla / Stinger / Piorun） | 便携 | < 5 m | |
| 2 | `starstreak_martlet` | Starstreak / Martlet | 便携（三联装架） | < 5 m | |
| 3 | `mobile_fire_team` | 机动火力组 | 自行（民用皮卡） | 5–10 m | ✔（火力组皮卡） |
| 4 | `zu23_2` | ZU‑23‑2 牵引高炮 | 牵引 | < 5 m | |
| 5 | `s60` | S‑60 牵引高炮 | 牵引 | 5–10 m | |
| 6 | `sky_sentinel` | Sky Sentinel AI 机枪塔 | 固定 | < 5 m | |
| 7 | `gepard` | Gepard 猎豹 | 自行（履带） | 5–10 m | ✔ |
| 8 | `skynex` | Skynex | 牵引 / 卡车载 | 5–10 m（单门炮） | |
| 9 | `skyranger_35` | Skyranger 35 | 自行（履带） | 5–10 m | |
| 10 | `strela_10` | Strela‑10 | 自行（履带） | 5–10 m | |
| 11 | `osa_akm` | Osa‑AKM | 自行（轮式 6×6） | 5–10 m | |
| 12 | `avenger` | Avenger | 自行（轮式 4×4） | < 5 m ≈（约 5 m） | |
| 13 | `stormer_hvm` | Stormer HVM | 自行（履带） | 5–10 m | |
| 14 | `vampire` | VAMPIRE | 自行（皮卡） | 5–10 m | |
| 15 | `raven` | Raven | 自行（轮式） | 5–10 m | |
| 16 | `gravehawk` | Gravehawk | 集装箱 / 卡车载 | 5–10 m（集装箱）/ 10–15 m（含卡车） | |
| 17 | `crotale_ng` | Crotale NG | 自行 / 方舱 ≈ | 5–10 m | |
| 18 | `rbs_70` | RBS 70 | 便携（三脚架） | < 5 m | |
| 19 | `iris_t_sls` | IRIS‑T SLS | 自行（轻型车） | 5–10 m | ✔（IRIS‑T 系列） |
| 20 | `frankensam` | FrankenSAM | 自行（视组合而定） | 5–10 m | |
| 21 | `buk_m1` | Buk‑M1 | 自行（履带） | 5–10 m | ✔ |
| 22 | `hawk` | Hawk Phase III | 牵引 | 5–10 m | |
| 23 | `aspide` | Aspide / Spada | 牵引 / 方舱 | 5–10 m | |
| 24 | `nasams` | NASAMS | 牵引 / 卡车载 | 5–10 m | |
| 25 | `iris_t_slm` | IRIS‑T SLM | 卡车载（8×8） | 10–15 m | ✔（IRIS‑T 系列） |
| 26 | `s300ps` | S‑300PS | 自行（轮式 8×8） | 10–15 m | ✔ |
| 27 | `s300pt` | S‑300PT | 牵引（半挂） | > 15 m | ✔ |
| 28 | `samp_t` | SAMP/T | 卡车载（8×8） | 10–15 m | |
| 29 | `patriot` | Patriot | 牵引（半挂）/ 卡车载 | > 15 m | ✔ |
| 30 | `s200` | S‑200 | 固定阵地 | 10–15 m | |
| 31 | `interceptor_drone_team` | 拦截无人机班组 | 自行（皮卡）+ 小型无人机 | 5–10 m | |
| 32 | `jet_interceptor_drone` | 喷气式拦截无人机 | 自行（皮卡 / 发射架） | 5–10 m ≈ | |
| 33 | `national_early_warning` | 国家预警网 | 无实体 | 图标 | |
| 34 | `soviet_long_range_radar` | 苏制远程警戒雷达 | 卡车载 | 5–10 m | |
| 35 | `soviet_mid_range_radar` | 苏制中程警戒雷达 | 卡车 / 拖车 | 5–10 m | |
| 36 | `western_3d_radar` | 西方 3D 警戒雷达 | 卡车载 | 10–15 m ≈ | |
| 37 | `gap_filler_radar` | 低空补盲雷达 | 拖车 / 塔架 | < 5 m（雷达）/ 5–10 m（含拖车） | |
| 38 | `acoustic_post` | 声学哨 | 固定（杆） | < 5 m | |
| 39 | `visual_observer` | 目视观察哨 | 人员 | < 5 m | |
| 40 | `radio_detector` | 无线电侦测器 | 便携 / 固定 | < 5 m | |
| 41 | `civilian_reports` | 民众上报 | 无实体 | 图标 | |
| 42 | `tethered_balloon` | 系留气球传感器 | 系留 + 卡车 | > 15 m（气囊） | |
| 43 | `area_nav_jammer` | 区域导航干扰站 | 卡车 / 方舱 / 固定 | 5–10 m | |
| 44 | `nav_spoofer` | 导航欺骗站 | 固定 / 方舱 | 5–10 m ≈ | |
| 45 | `counter_uas_jammer` | 反无人机干扰站 | 车载 / 三脚架 | < 5 m（设备）/ 5–10 m（含车） | |
| 46 | `handheld_counter_uas` | 单兵反无人机枪 | 便携 | < 5 m | |
| 47 | `vehicle_shield` | 车载防护罩 | 装备槽（附加在车上） | 无独立精灵 | |
| 48 | `decoy_emitter` | 诱饵辐射源 | 便携 / 小型拖车 | < 5 m | |
| 49 | `sacrificial_radar` | 旧雷达牺牲开机 | 卡车 / 拖车 | 5–10 m | |
| 50 | `fake_launcher` | 假发射车 | 充气 / 木制 | 随仿制对象 | |
| 51a | `fighter`（F‑16） | F‑16 / Mirage 2000 / MiG‑29 | 战斗机 | ≈ 15 m（10–15 上限） | |
| 51b | `fighter`（Mirage 2000） | 同上 | 战斗机 | 10–15 m | |
| 51c | `fighter`（MiG‑29） | 同上 | 战斗机 | > 15 m | |

---

## 一、防空单位（`data/units/air_defense.json`）

### 单兵防空（Igla / Stinger / Piorun）（`manpads`）
- **类别**：便携；士兵肩扛。画面上可配一辆皮卡作为机动载具（数据中移动速度按"步兵 / 皮卡"）。
- **关键外形特征**：
  1. 一根细长发射管扛在右肩，前端有握把和瞄准具；射手单膝跪地或站立。
  2. Igla：发射管前端下方有一个圆柱形电池 / 冷却单元，管口前方带细长"针状"探针（导弹头部的整流针）[1]。
  3. Stinger：发射管前部有一块向上折起的方形 IFF 天线框架（像一个小网格），握把组件比较大 [2]。
  4. Piorun：外形接近 Igla 系（波兰在 Grom / Igla 基础上发展），细节差异在瞄准具和握把 [3]。
  5. 一般 2 人一组：射手 + 携带备用发射管的副手。
- **组成**：1 个双人小组（可选 1 辆民用 / 军用皮卡）。
- **常见涂装**：发射管多为橄榄绿 / 军绿；人员为乌军像素迷彩（MM14）或多地形迷彩，常见黄色 / 蓝色臂章胶带。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons [Category:9K38 Igla](https://commons.wikimedia.org/wiki/Category:9K38_Igla)、[Category:FIM-92 Stinger](https://commons.wikimedia.org/wiki/Category:FIM-92_Stinger)、[Category:PZR Piorun](https://commons.wikimedia.org/wiki/Category:PZR_Piorun)；维基 [9K38 Igla](https://en.wikipedia.org/wiki/9K38_Igla)、[FIM-92 Stinger](https://en.wikipedia.org/wiki/FIM-92_Stinger)、[Piorun (missile)](https://en.wikipedia.org/wiki/Piorun_(missile))。
- **注意**：AI 常把单兵防空画成反坦克导弹（Javelin / NLAW）——Javelin 发射管更粗、带大块方形 CLU 瞄准器，不要混淆。精灵尺寸下三种型号几乎看不出差别，建议做一个通用模型 + 可选 IFF 天线部件。

### Starstreak / Martlet（`starstreak_martlet`）
- **类别**：便携；肩射或"轻型多联装发射架"（LML，三联装，架在三脚架上）[4]。也可从 Stormer 车载发射（见 `stormer_hvm`）[5]。
- **关键外形特征**：
  1. 发射管粗而短，前端有一个较大的方形瞄准单元（肩射型）。
  2. LML 版本：三根发射管并排架在一个低矮三脚基座上，中间是瞄准 / 观测单元，射手坐在后方 [4]。
  3. Martlet（LMM）与 Starstreak 共用同类发射器 [5]，外观上主要差别在弹体，精灵尺寸下可视为同一模型。
- **组成**：2–3 人小组 + 1 个 LML 发射架或若干肩射管。
- **常见涂装**：英制橄榄绿 / 沙色；人员同乌军。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons [Category:Starstreak missiles](https://commons.wikimedia.org/wiki/Category:Starstreak_missiles)、[Category:Martlet missiles](https://commons.wikimedia.org/wiki/Category:Martlet_missiles)；维基 [Starstreak](https://en.wikipedia.org/wiki/Starstreak)、[Lightweight Multirole Missile](https://en.wikipedia.org/wiki/Lightweight_Multirole_Missile)。
- **注意**：Commons 搜索"Starstreak"会混入 Javelin MANPADS 分类，挑图时注意。LML 三联装是本单位最好的辨识特征，建议优先做三联装架版本。

### 机动火力组（`mobile_fire_team`） · 首批
- **类别**：自行；民用 / 准军用皮卡（4×4 双排座皮卡为主），后斗加装武器。**泛指，外观可艺术化。**
- **关键外形特征**：
  1. 底盘：中型双排座皮卡（类似 Toyota Hilux、Mitsubishi L200、Nissan Navara 一类），4 门、短后斗；不必还原具体品牌，避免商标细节 [6]。
  2. 后斗武器：大口径机枪（DShK 类苏式重机枪或 M2 类西式重机枪）装在立柱 / 环形支架上；部分组用多管机枪组合 ≈。
  3. 部分火力组在更大的卡车或皮卡上加装 ZU‑23‑2 双管高炮（见 `zu23_2`）——ZU‑23‑2 装车在技术车辆上很常见 [6][7]。皮卡装 ZU‑23‑2 时后斗明显超载、武器高出驾驶室。
  4. 探照灯：大型圆形探照灯装在后斗或驾驶室顶部，夜间关卡是核心视觉元素（战役关卡设计第 5 关）。
  5. 热像 / 夜视：射手头盔上的夜视仪或架在机枪上的小型热像瞄具（精灵上可省略，只在近景表现）。
  6. 车身常见临时改装：拆掉后挡板、加防滚架、车顶加天线、车身贴识别胶带；部分车辆刷暗绿色哑光漆。
- **组成**：1 辆皮卡 + 2–4 名人员（司机、射手、探照灯手 / 观察员）。
- **常见涂装**：原厂民用颜色（白、银、黑）或手刷橄榄绿 / 暗绿哑光漆；车身常见白色或黄色识别标记 ≈。
- **画面尺度提示**：5–10 m（皮卡约 5 m 出头）。
- **参考图检索**：Commons [Category:Technicals (vehicle)](https://commons.wikimedia.org/wiki/Category:Technicals_(vehicle))、[Category:ZU-23-2 on technicals](https://commons.wikimedia.org/wiki/Category:ZU-23-2_on_technicals)、[Category:Toyota Hilux](https://commons.wikimedia.org/wiki/Category:Toyota_Hilux)、[Category:Searchlights](https://commons.wikimedia.org/wiki/Category:Searchlights)；维基 [Technical (vehicle)](https://en.wikipedia.org/wiki/Technical_(vehicle))。
- **注意**：
  - Commons 的 Technicals 分类多数是中东 / 非洲照片，车辆风格偏沙漠，乌克兰火力组更"干净"、颜色更暗，需人工挑图。
  - 乌克兰俗称这类车为 *tachanka* [6]，可作为检索关键词。
  - 不要画成带装甲的军用车辆；不要出现真实部队番号或可辨认的人员面孔。
  - 建议做"皮卡 + 机枪 + 探照灯"一个基础模型，ZU‑23‑2 版本作为变体。

### ZU‑23‑2 牵引高炮（`zu23_2`）
- **类别**：牵引；两轮炮架，作战时放下支腿、车轮移到一侧 [7]。
- **关键外形特征**：
  1. 两根并排的细长炮管，炮口有消焰器 [7]。
  2. 两侧各一个弹药箱，与炮架成直角伸出（识别要点）[7]。
  3. 中央两个座位（左右各一名炮手），带简单的光学瞄具。
  4. 行军状态：双轮小拖车，炮管向后平放，由卡车或皮卡牵引。
- **组成**：1 门炮 + 1 辆牵引车（Ural / KrAZ 类卡车或皮卡）+ 3–5 名炮手。
- **常见涂装**：苏式暗绿 / 橄榄绿。
- **画面尺度提示**：< 5 m（炮本身）。
- **参考图检索**：Commons [Category:ZU-23-2](https://commons.wikimedia.org/wiki/Category:ZU-23-2)；维基 [ZU-23-2](https://en.wikipedia.org/wiki/ZU-23-2)。
- **注意**：AI 常画成单管或四管（混淆 ZSU‑23‑4）。ZU‑23‑2 是**双管、无装甲、无雷达**。

### S‑60 牵引高炮（`s60`）
- **类别**：牵引；四轮炮架，单管 [8]。
- **关键外形特征**：
  1. 单根长炮管，炮口制退器明显 [8]。
  2. 四轮炮架，作战时放下四个支腿、车轮离地 ≈。
  3. 炮身两侧有护板（防盾较小），炮手座位在两侧。
  4. 体积明显大于 ZU‑23‑2。
- **组成**：1 门炮 + 1 辆牵引卡车（原配套为 Ural‑375 一类卡车 [8]）+ 炮班。
- **常见涂装**：苏式橄榄绿。
- **画面尺度提示**：5–10 m（含炮管）。
- **参考图检索**：Commons [Category:S-60 57 mm gun](https://commons.wikimedia.org/wiki/Category:S-60_57_mm_gun)；维基 [AZP S-60](https://en.wikipedia.org/wiki/AZP_S-60)。
- **注意**：原系统配有火控雷达车，乌克兰实战中是否随炮部署不明 ≈；画面上可不放雷达车。

### Sky Sentinel AI 机枪塔（`sky_sentinel`）
- **类别**：固定（数值表注明"固定 / 卡车"，可整体用卡车转移）。
- **关键外形特征**（≈，公开图像少）：
  1. 一挺大口径机枪装在遥控转塔上（据报道为 M2 类重机枪 ≈）[9]。
  2. 转塔上有光电 / 热像传感器盒。
  3. 底座为固定支架或小型平台，周围可能有沙袋 / 防护网。
- **组成**：1 座转塔 + 电源 / 控制箱；无人值守为主。
- **常见涂装**：橄榄绿 / 灰色 ≈。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons 未找到；维基未找到对应条目（英文维基 "Sky Sentinel" 是**无关的无人飞艇条目**，不要误用）；报道见 Forbes [9]（取自现有时间表文档，未打开核对）。
- **注意**：泛化为"遥控机枪塔 + 传感器"即可，外观可艺术化。不要画成大型 CIWS（如 Phalanx）。

### Gepard 猎豹（`gepard`） · 首批
- **类别**：自行；履带，基于 Leopard 1 主战坦克车体 [10]。
- **关键外形特征**：
  1. 车体为 Leopard 1 车体（略有修改），每侧 7 个负重轮 ≈（与 Leopard 1 相同，建模前对照照片确认）[10]。
  2. 大型可全向旋转的方形炮塔，**两门 35 mm 炮分别装在炮塔左右两侧外部**（不是在炮塔正中），炮管很长 [10]。
  3. 炮塔**后上方**是搜索雷达天线（扁平抛物面 / 条形天线，可向后折叠放倒）≈。
  4. 炮塔**正前方**是跟踪雷达天线（圆盘形）≈。
  5. 炮塔顶部有光学瞄具和舱盖；炮塔两侧炮管下方是弹药供弹舱外壳。
  6. 车体尾部为 Leopard 1 的发动机舱和排气格栅 [10]。
- **组成**：1 辆自行高炮（独立作战，无需其他车辆）；画面上可选配 1 辆弹药补给卡车。
- **常见涂装**：德国三色迷彩（绿 / 棕 / 黑）为主；部分乌军车辆改刷单色橄榄绿，并有白色识别标记 ≈。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:Flakpanzer Gepard](https://commons.wikimedia.org/wiki/Category:Flakpanzer_Gepard)、[Category:Flugabwehrkanonenpanzer Gepard in Ukrainian service](https://commons.wikimedia.org/wiki/Category:Flugabwehrkanonenpanzer_Gepard_in_Ukrainian_service)（含 10 余张乌克兰服役照片）、[Category:Leopard 1 tanks](https://commons.wikimedia.org/wiki/Category:Leopard_1_tanks)；维基 [Flakpanzer Gepard](https://en.wikipedia.org/wiki/Flakpanzer_Gepard)、[Leopard 1](https://en.wikipedia.org/wiki/Leopard_1)。
- **注意**：
  - 荷兰版（CA1 / PRTL）的雷达外观与德国版不同 ≈；乌克兰使用的主要是德国版，以德国版为准。
  - AI 常犯错误：把炮管放在炮塔中央（像普通坦克）、只画一门炮、把雷达画成坦克的机枪塔、负重轮数量错误。
  - Skyranger 35（`skyranger_35`）同样可能用 Leopard 1 车体，两者需在炮塔上区分开。

### Skynex（`skynex`）
- **类别**：牵引 / 卡车载；分布式系统。乌克兰获得的版本由 4 门 35 mm 转膛炮、1 个控制节点和 1 部 X‑TAR3D 雷达组成，全部装在 HX 卡车上 [11]。
- **关键外形特征**：
  1. 单门炮为无人炮塔，炮管长，装在矩形平台上（可放地面或卡车车斗）[11]。
  2. 雷达为独立单元，旋转平板天线 ≈。
  3. 控制节点为方舱（集装箱式）。
  4. 载车为 RMMV HX 系列军用卡车 [11]。
- **组成**：4 门炮 + 1 部雷达 + 1 个控制方舱，各自在一辆 HX 卡车上 [11]。精灵可简化为"1 门炮 + 雷达 + 方舱"组合。
- **常见涂装**：德军橄榄绿 / 灰绿。
- **画面尺度提示**：5–10 m（单门炮）；含卡车 10 m 左右。
- **参考图检索**：Commons [Category:Rheinmetall Air Defence Skynex](https://commons.wikimedia.org/wiki/Category:Rheinmetall_Air_Defence_Skynex)、[Category:MAN HX](https://commons.wikimedia.org/wiki/Category:MAN_HX)；维基 [Skynex](https://en.wikipedia.org/wiki/Skynex)。
- **注意**：数据中 `skynex` 为 `towed`，而乌克兰版本据维基为卡车载 [11]，见"与现有文档的差异"第 3 条。

### Skyranger 35（`skyranger_35`）
- **类别**：自行；无人炮塔装在装甲底盘上。供乌克兰的版本以 Leopard 1 车体为基础（据时间表文档引用的 Rheinmetall 公告 [12]）。
- **关键外形特征**：
  1. 无人炮塔，单门 35 mm 转膛炮居中 [13]。
  2. 炮塔上集成跟踪雷达和光电 / 红外传感器 [13]；2023 年后的新版炮塔带 AESA 搜索雷达面板 [13]。
  3. 底盘为 Leopard 1 车体（乌克兰版）[12]，外形与 Gepard 车体接近。
- **组成**：1 辆自行车（独立作战）。
- **常见涂装**：德军橄榄绿 ≈。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:Oerlikon Skyranger 35](https://commons.wikimedia.org/wiki/Category:Oerlikon_Skyranger_35)（多为样车 / 其他底盘）；维基 [Skyranger 35](https://en.wikipedia.org/wiki/Skyranger_35)。
- **注意**：交付时间和最终外观未公开确认（时间表文档：2025.10 签约）≈。公开照片多为 Piranha / Boxer / Leopard 2 样车 [13]，炮塔可参考，底盘应换为 Leopard 1。与 Gepard 区分：Skyranger 是**单炮、炮塔较小、无外挂双炮**。

### Strela‑10（`strela_10`）
- **类别**：自行；履带，MT‑LB 底盘 ≈ [14]。
- **关键外形特征**：
  1. 低矮的 MT‑LB 履带车体，每侧 6 个负重轮 ≈。
  2. 车顶小型旋转炮塔，两侧各挂 2 个方形发射箱，共 4 个 [14]。
  3. 发射箱之间 / 上方有测距或被动探测天线 ≈。
- **组成**：1 辆发射车（独立作战）。
- **常见涂装**：苏式 / 乌式橄榄绿，部分有乌军迷彩。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:9K35 Strela-10](https://commons.wikimedia.org/wiki/Category:9K35_Strela-10)、[Category:MT-LB](https://commons.wikimedia.org/wiki/Category:MT-LB)；维基 [9K35 Strela-10](https://en.wikipedia.org/wiki/9K35_Strela-10)。
- **注意**：AI 常与 2S6 通古斯卡或 9K31 Strela‑1（BRDM‑2 轮式底盘）混淆。Strela‑10 是**履带 + 4 个方箱**。

### Osa‑AKM（`osa_akm`）
- **类别**：自行；轮式 6×6 两栖车 BAZ‑5937 [15]。
- **关键外形特征**：
  1. 船形车体、6 个大轮（三轴等距），两栖外形 [15]。
  2. 车顶旋转炮塔：顶部有大型搜索雷达天线（可折叠），正面是跟踪雷达和制导天线组合 ≈。
  3. 炮塔两侧各 3 个带肋条的方形发射箱，共 6 个（AK / AKM 版本）[15]。
- **组成**：1 辆 TELAR（独立作战）；可选 1 辆装填车 [15]。
- **常见涂装**：苏式橄榄绿；乌军车辆常有迷彩。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:9K33 Osa](https://commons.wikimedia.org/wiki/Category:9K33_Osa)；维基 [9K33 Osa](https://en.wikipedia.org/wiki/9K33_Osa)。
- **注意**：早期 Osa（9K33）为外露式 4 发导弹，**AKM 为 6 个密封发射箱** [15]，不要混用。

### Avenger（`avenger`）
- **类别**：自行；轮式 HMMWV（M998 / M1097）底盘 [16]。
- **关键外形特征**：
  1. 普通 HMMWV 车体，后部车斗装一个带乘员的炮塔 ≈。
  2. 炮塔两侧各一个导弹吊舱（每侧 4 联装发射筒）≈。
  3. 吊舱下方 / 一侧有一挺机枪 ≈；炮塔前部有光电传感器。
- **组成**：1 辆车（独立作战）。
- **常见涂装**：美军沙色或北约绿；乌克兰车辆多为绿色 ≈。
- **画面尺度提示**：< 5 m ≈（约 5 m）。
- **参考图检索**：Commons [Category:M1097 Avenger](https://commons.wikimedia.org/wiki/Category:M1097_Avenger)、[Category:HMMWV](https://commons.wikimedia.org/wiki/Category:HMMWV)；维基 [AN/TWQ-1 Avenger](https://en.wikipedia.org/wiki/AN/TWQ-1_Avenger)。
- **注意**：吊舱为左右两个，不是车顶单个。

### Stormer HVM（`stormer_hvm`）
- **类别**：自行；履带，Alvis Stormer 装甲车底盘 [5]。
- **关键外形特征**：
  1. 箱形小型履带车体 ≈。
  2. 车顶升降式发射架，两组各 4 个发射筒，共 8 个 ≈。
  3. 车顶有被动探测 / 光电传感器（ADAD 类）≈。
  4. 可发射 Starstreak 或 Martlet [5][4]。
- **组成**：1 辆车（独立作战）。
- **常见涂装**：英军绿色 / 沙色；乌军车辆有改涂 ≈。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:Alvis Stormer](https://commons.wikimedia.org/wiki/Category:Alvis_Stormer)（含乌克兰服役照片 "UA Stormer HVM 01"）；维基 [Alvis Stormer](https://en.wikipedia.org/wiki/Alvis_Stormer)。
- **注意**：发射架在行军时收入车内 / 放平，展开状态和行军状态外形差异大 ≈。

### VAMPIRE（`vampire`）
- **类别**：自行；皮卡车斗加装的模块化套件 [17]。
- **关键外形特征**：
  1. 皮卡车斗中的 4 联装 70 mm 火箭发射器 [17]。
  2. 一根可伸缩桅杆，顶端为光电 / 红外传感器球和激光指示器 [17]。
  3. 车斗里有独立电源和控制设备 [17]。
- **组成**：1 辆皮卡 + 套件（独立作战）。
- **常见涂装**：皮卡原色或手刷绿色 ≈。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons 未找到；维基 [VAMPIRE (weapon)](https://en.wikipedia.org/wiki/VAMPIRE_(weapon))。
- **注意**：与 `mobile_fire_team` 底盘相似，靠**伸缩桅杆 + 4 联装火箭箱**区分。

### Raven（`raven`）
- **类别**：自行；轮式。英国为乌克兰改装的近程防空发射车，使用库存 Supacat 车辆 + ASRAAM 导弹 [18]。
- **关键外形特征**（≈）：
  1. 底盘为 Supacat 高机动车（Jackal 系，敞篷式开放车身）[18]。
  2. 车体后部为导弹发射导轨（2026 年 Raven V 型号为 4 联装 ASRAAM [18]；早期型号数量 ≈）。
  3. 车上有光电传感器转塔 ≈。
- **组成**：1 辆车（独立作战）。
- **常见涂装**：英军沙色 / 绿色 ≈。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons 未找到；维基 [Raven (air defence)](https://en.wikipedia.org/wiki/Raven_(air_defence))。
- **注意**：公开图像少，早期型和 Raven V 外观不同，按游戏时间段选择版本 ≈。

### Gravehawk（`gravehawk`）
- **类别**：集装箱式；装在标准 20 英尺集装箱中，可由各种钩臂卡车装载 [19]。
- **关键外形特征**：
  1. 外观为普通 20 英尺集装箱（伪装目的）[19]。
  2. 展开时箱顶打开，升起导弹发射架（使用乌克兰库存的 R‑73 空空导弹 [19]）≈。
  3. 载车为钩臂式卡车 [19]。
- **组成**：1 个集装箱 + 1 辆钩臂卡车；可选独立传感器 ≈。
- **常见涂装**：集装箱常见颜色（绿 / 灰 / 民用色）≈。
- **画面尺度提示**：5–10 m（集装箱）/ 10–15 m（含卡车）。
- **参考图检索**：Commons 未找到（可用 [Category:Shipping containers](https://commons.wikimedia.org/wiki/Category:Shipping_containers) 做集装箱参考）；维基 [Gravehawk](https://en.wikipedia.org/wiki/Gravehawk)。
- **注意**：收起状态应与普通集装箱几乎无法区分——这是本单位的视觉要点，也可与 `fake_launcher` 的玩法呼应。

### Crotale NG（`crotale_ng`）
- **类别**：自行或方舱式（不同用户底盘差异很大）[20]。乌克兰获得的法国 Crotale NG 具体载车 ≈。
- **关键外形特征**：
  1. 一个集成式发射 / 雷达转塔：中央为雷达和光电组件，两侧各 4 个发射筒，共 8 个 ≈（舰载版为 8 联装 [20]）。
  2. 转塔顶部为搜索雷达天线 ≈。
  3. 底盘：芬兰为 Sisu Pasi 轮式车 [20]；法国空军版为方舱 + 卡车 ≈。
- **组成**：1 个火力单元（转塔 + 载车）。
- **常见涂装**：法军绿色 / 迷彩 ≈。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:Crotale NG](https://commons.wikimedia.org/wiki/Category:Crotale_NG)；维基 [Crotale (missile)](https://en.wikipedia.org/wiki/Crotale_(missile))。
- **注意**：需人工确认乌克兰版本的载车，否则建议做"转塔 + 通用卡车"。

### RBS 70（`rbs_70`）
- **类别**：便携；三脚架 / 座架式，射手坐在发射架后 ≈ [21]。
- **关键外形特征**：
  1. 低矮三脚座架，射手坐姿操作 ≈。
  2. 发射管架在座架上方，后部是瞄准单元 ≈。
  3. 夜视瞄具为可选附加件 [21]。
- **组成**：2–3 人小组 + 发射架 + 备用导弹箱。
- **常见涂装**：瑞典 / 北欧绿色。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons [Category:RBS-70](https://commons.wikimedia.org/wiki/Category:RBS-70)；维基 [RBS 70](https://en.wikipedia.org/wiki/RBS_70)。
- **注意**：与肩射 MANPADS 的区别是**有座架、射手坐着**。

### IRIS‑T SLS（`iris_t_sls`） · 首批（IRIS‑T 系列）
- **类别**：自行；发射器可装在多种车辆上：瑞典为 Bv 410 履带车（4 发）[22]，另有 Mowag Eagle 6×6 版本、Iveco 4×4 版本 [22]。乌克兰版本具体载车 ≈（维基参考文献中有"IRIS‑T SLS for Ukraine integrated on Iveco 4×4 chassis"的报道 [22]）。
- **关键外形特征**：
  1. 车辆后部的小型发射架，挂 4 枚 ≈（Bv 410 版为 4 发 [22]）导弹，导弹为细长红外空空导弹的地面型 [22]。
  2. 发射架在行军时放平、作战时竖起 ≈。
  3. 搭配一部小型雷达（如 Spexer 类或 XENTA‑M 类平板雷达）[22] ≈。
  4. 整体比 SLM 小得多，适合与 SLM 区分。
- **组成**：1 辆发射车 + 1 部雷达 / 指挥车 [22]。精灵可简化为"发射车"单车。
- **常见涂装**：橄榄绿 ≈。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:IRIS-T SLS system](https://commons.wikimedia.org/wiki/Category:IRIS-T_SLS_system)、[Category:IRIS-T SLS in Ukrainian service](https://commons.wikimedia.org/wiki/Category:IRIS-T_SLS_in_Ukrainian_service)（1 张乌克兰发射器照片）、[Category:IRIS-T](https://commons.wikimedia.org/wiki/Category:IRIS-T)；维基 [IRIS-T SL](https://en.wikipedia.org/wiki/IRIS-T_SL)。
- **注意**：WS03-007 只写"IRIS‑T"，未区分 SLS / SLM，见"需要人工确认"第 2 条。

### FrankenSAM（`frankensam`）
- **类别**：自行；FrankenSAM 是一类"苏制平台 + 西方导弹"改装的统称，包括 Buk‑M1 + RIM‑7 Sea Sparrow、苏制雷达 + AIM‑9M 等组合（时间表文档；维基该词重定向到 RIM‑7 地面发射一节 [23]）。
- **关键外形特征**（以 Buk + RIM‑7 组合为例，≈）：
  1. 底盘与 Buk‑M1 发射车相同（履带）。
  2. 发射架上的导弹换成 RIM‑7（弹体更细、弹翼布局不同）≈。
  3. 其他组合（AIM‑9M 版）外观为苏制雷达车 + 小型导轨发射器 ≈。
- **组成**：视组合而定。
- **常见涂装**：同 Buk / 乌军绿色。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons 未找到（可参考 [Category:Skyguard/Sparrow System](https://commons.wikimedia.org/wiki/Category:Skyguard/Sparrow_System) 中 Sparrow 弹体外形）；维基 [RIM-7 Sea Sparrow](https://en.wikipedia.org/wiki/RIM-7_Sea_Sparrow)。
- **注意**：公开照片极少，外观可艺术化；与 `buk_m1` 外观高度重合，需人工决定区分方式（见"需要人工确认"第 3 条）。

### Buk‑M1（`buk_m1`） · 首批
- **类别**：自行；履带，GM 系列底盘（Buk‑M1‑2 发射车为 GM‑569 [24]）。
- **关键外形特征**：
  1. **9A310M1 自行发射制导车（TELAR）**：履带底盘，每侧 6 个负重轮 ≈（维基提到 Buk‑M3 改为"7 负重轮"底盘 [24]，可反推 M1 为 6 个，需对照照片确认）。
  2. 车体中后部是旋转发射台，上方**并列 4 枚导弹**（裸弹挂在导轨上，不是发射箱），行军时导弹向后平放、作战时一起抬起 ≈。
  3. 发射台**前端**装火控雷达（9S35，圆形 / 半圆形天线罩，朝前）[24]，和导弹一起转动。
  4. 驾驶室在车体最前方左侧 ≈，车体前部较低。
  5. **9S18M1 搜索雷达车**（"Kupol"）：同类履带底盘，车顶一面大型椭圆 / 长方形网状天线，行军时向后折叠平放 [24] ≈。
  6. **9A39M1 装填发射车（TEL）**：履带底盘，带 4 枚导弹 + 一台起重机，外观与 TELAR 相似但**没有前端雷达**、多了吊臂 [24] ≈。
  7. **9S470M1 指挥车**：同类履带底盘，车顶为方舱和天线 [24] ≈。
- **组成**：画面上的一个火力单元建议包含 1 辆 TELAR（9A310M1）+ 1 辆 TEL/装填车（9A39M1）；完整营还有 9S18M1 搜索雷达车和 9S470M1 指挥车 [24]。最小可玩单元只做 TELAR 即可（TELAR 可独立作战）。
- **常见涂装**：苏式 / 乌式橄榄绿，部分有三色迷彩；乌军车辆常有白色 / 黄色识别标记 ≈。
- **画面尺度提示**：5–10 m（TELAR 约 9 m 级）。
- **参考图检索**：Commons [Category:9K37 Buk](https://commons.wikimedia.org/wiki/Category:9K37_Buk)、[Category:Buk surface-to-air missile system](https://commons.wikimedia.org/wiki/Category:Buk_surface-to-air_missile_system)、[Category:9A310M1-2](https://commons.wikimedia.org/wiki/Category:9A310M1-2)、[Category:9A39M1](https://commons.wikimedia.org/wiki/Category:9A39M1)、[Category:9S470](https://commons.wikimedia.org/wiki/Category:9S470)；维基 [Buk missile system](https://en.wikipedia.org/wiki/Buk_missile_system)。
- **注意**：
  - 乌克兰装备的是 **Buk‑M1**；Commons 大量照片是 Buk‑M1‑2 / M2 / M3（俄方及出口型）。**M2 / M3 外形不同**（M3 为 6 联装发射箱、7 负重轮 [24]），不要用作参考。
  - 有 MZKT 轮式底盘的 Buk‑M2E 出口型 [24]，与乌克兰无关。
  - AI 常把导弹画成发射箱、把雷达放到车尾、把 4 枚导弹画成 2 枚或 6 枚。
  - 涉及 MH17 的照片（俄方 Buk）不要作为参考来源或在游戏中提及具体事件。

### Hawk Phase III（`hawk`）
- **类别**：牵引；各组件装在轮式拖车上 [25]。
- **关键外形特征**：
  1. M192 牵引式三联装发射架：三枚导弹并排挂在一个可旋转发射架上 [25]。
  2. 脉冲搜索雷达（PAR）：大型椭圆形镂空网格反射面，装在小型双轮拖车上并旋转 [25]。
  3. 高功率照射雷达（HPIR）：两个并排的圆形 / 方形天线（"双眼"外形）在拖车上 ≈ [25]。
  4. 指挥控制方舱 + 发电机拖车 [25]。
- **组成**：若干 M192 发射架 + PAR + HPIR + 控制方舱 [25]。精灵可简化为"1 个发射架 + 1 个 PAR + 1 个 HPIR"。
- **常见涂装**：美 / 西班牙军绿色、沙色。
- **画面尺度提示**：5–10 m（单个发射架 / 拖车）。
- **参考图检索**：Commons [Category:MIM-23 Hawk](https://commons.wikimedia.org/wiki/Category:MIM-23_Hawk)、[Category:AN/MPQ-50 Pulse Acquisition Radar](https://commons.wikimedia.org/wiki/Category:AN/MPQ-50_Pulse_Acquisition_Radar)；维基 [MIM-23 Hawk](https://en.wikipedia.org/wiki/MIM-23_Hawk)。
- **注意**：三联装发射架是识别要点；Phase III 雷达组件与早期型略有不同 ≈。

### Aspide / Spada（`aspide`）
- **类别**：牵引 / 方舱。Aspide 导弹用于 Skyguard（西班牙等）和 Spada（意大利）两种地面系统 [26]。
- **关键外形特征**（≈）：
  1. 牵引式多联装发射架（Skyguard‑Aspide 为 4 联装箱 ≈；Spada 为 6 联装 ≈）。
  2. 火控雷达方舱：拖车上的方舱，顶部为搜索 + 跟踪雷达天线（Skyguard 为典型的双天线方舱）≈。
  3. 整体为拖车阵地风格，与 Hawk 相近。
- **组成**：1–2 个发射架 + 1 个火控方舱。
- **常见涂装**：西班牙 / 意大利军绿色 ≈。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:Aspide missiles](https://commons.wikimedia.org/wiki/Category:Aspide_missiles)、[Category:Skyguard/Sparrow System](https://commons.wikimedia.org/wiki/Category:Skyguard/Sparrow_System)；维基 [Aspide](https://en.wikipedia.org/wiki/Aspide)。
- **注意**：显示名"Aspide / Spada"包含两种外观不同的系统；乌克兰获得的是哪一种需确认（见差异第 4 条）。

### NASAMS（`nasams`）
- **类别**：牵引 / 卡车载；分布式系统 [27]。
- **关键外形特征**：
  1. 发射器：6 个方形发射箱，2 排 × 3 ≈，装在拖车或卡车平台上，可俯仰 [27]。
  2. AN/MPQ‑64 Sentinel 雷达：旋转的长方形平板天线，装在拖车上 [27][28]。
  3. 火力分配中心（FDC）：方舱车 [27]。
  4. 光电传感器车（MSP500）[27]。
- **组成**：每个火力单元 3 个发射器 + 1 部雷达 + 1 个 FDC + 1 辆光电车 [27]。精灵可简化为"发射器 + 雷达 + 方舱"。
- **常见涂装**：挪威 / 美军橄榄绿。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:NASAMS](https://commons.wikimedia.org/wiki/Category:NASAMS)、[Category:AN/MPQ-64 Sentinel](https://commons.wikimedia.org/wiki/Category:AN/MPQ-64_Sentinel)；维基 [NASAMS](https://en.wikipedia.org/wiki/NASAMS)、[AN/MPQ-64 Sentinel](https://en.wikipedia.org/wiki/AN/MPQ-64_Sentinel)。
- **注意**：发射箱数量为 6 [27]；新型 Mk 2 发射器可挂其他导弹，外观有导轨差异 [27]。

### IRIS‑T SLM（`iris_t_slm`） · 首批（IRIS‑T 系列）
- **类别**：卡车载。系统**不绑定底盘**，组件按 20 英尺 ISO 集装箱尺寸设计，可装在各种卡车上 [29]；德军示例为 MAN SX45 8×8 [30]。乌克兰发射车的具体卡车型号随批次不同 ≈（需对照 Commons 乌克兰服役照片）。
- **关键外形特征**：
  1. **发射车**：8×8 重型军用卡车，车后部一个大型箱式发射架，**8 个方形发射箱，2 排 × 4 ≈**，作战时整体竖起接近垂直 ≈。
  2. 发射架行军时平放在车斗上，外形像一个长方形货箱 ≈。
  3. **雷达车**：Hensoldt TRML‑4D，旋转的平板 AESA 天线装在不可伸缩的旋转底座上，底座在方舱 / 卡车顶部 [31]。
  4. 雷达方舱可从卡车上卸下作为独立拖车使用 [31]。
  5. **指挥车**：方舱式指挥所，卡车载 ≈。
  6. 驾驶室为欧式平头 / 长头军用卡车驾驶室 ≈，具体以照片为准。
- **组成**：德军配置为 1 部雷达 + 3 辆发射车 + 指挥所 [30]。画面建议：1 辆雷达车 + 1–3 辆发射车 + 1 辆指挥方舱车。
- **常见涂装**：德军橄榄绿 / 灰绿；乌军车辆可能加伪装网。
- **画面尺度提示**：10–15 m（8×8 卡车）。
- **参考图检索**：Commons [Category:IRIS-T SLM system](https://commons.wikimedia.org/wiki/Category:IRIS-T_SLM_system)、[Category:IRIS-T SLM in Ukrainian service](https://commons.wikimedia.org/wiki/Category:IRIS-T_SLM_in_Ukrainian_service)（10 个文件，含装填照片）、[Category:Hensoldt TRML-4D](https://commons.wikimedia.org/wiki/Category:Hensoldt_TRML-4D)、[Category:MAN SX](https://commons.wikimedia.org/wiki/Category:MAN_SX)；维基 [IRIS-T SL](https://en.wikipedia.org/wiki/IRIS-T_SL)、[TRML](https://en.wikipedia.org/wiki/TRML)。
- **注意**：
  - 发射箱数量和排列（2 × 4）建模前必须对照乌克兰服役照片确认 ≈。
  - 维基 / Commons 中常见的展会照片（ILA）是厂商样车，涂装和底盘可能与乌克兰实物不同。
  - AI 常把发射箱画成圆筒（类似 S‑300），IRIS‑T SLM 是**方箱**。

### S‑300PS（`s300ps`） · 首批
- **类别**：自行；轮式 MAZ‑543 系 8×8 底盘（S‑300PS 开始，发射车、雷达车和指挥车都基于 MAZ‑7910 8×8 底盘 [32]）。
- **关键外形特征**：
  1. **5P85S / 5P85D 发射车**：MAZ‑543 系 8×8 底盘，**4 个大型圆柱形发射筒**并排平放在车背，作战时整体**竖直立起**（垂直发射）[32] ≈。
  2. MAZ‑543 系驾驶室特征：**左右两个分开的驾驶室**，发动机在两室之间 ≈（AI 最常画错的地方）。
  3. 5P85S（"主"）在驾驶室后方多一个设备舱，5P85D（"从"）没有 [32] ≈。
  4. 发射车尾部有液压支腿，竖起时车尾接地 ≈。
  5. **30N6 火控雷达车**（"Flap Lid"）：同类 8×8 底盘，车顶一面**大型方形平板相控阵天线**，作战时竖起，可装在升降桅杆上 [32] ≈。
  6. **搜索雷达**：36D6（"Tin Shield"）/ 76N6（低空，"Clam Shell"）等，可选配 [32]，见 `soviet_mid_range_radar`。
  7. 竖起状态时 4 个筒顶部有防护盖 ≈。
- **组成**：画面上一个火力单元建议：1 辆 30N6 雷达车 + 2–3 辆 5P85S/D 发射车；可选 1 部 36D6 搜索雷达。
- **常见涂装**：苏式橄榄绿 / 乌式迷彩（绿 / 棕 / 黑），部分车辆有白色识别标记 ≈。
- **画面尺度提示**：10–15 m（8×8 底盘）。
- **参考图检索**：Commons [Category:S-300](https://commons.wikimedia.org/wiki/Category:S-300)、[Category:S-300PS](https://commons.wikimedia.org/wiki/Category:S-300PS)、[Category:30N6](https://commons.wikimedia.org/wiki/Category:30N6)、[Category:MAZ-543](https://commons.wikimedia.org/wiki/Category:MAZ-543)、[Category:MAZ-7910](https://commons.wikimedia.org/wiki/Category:MAZ-7910)；维基 [S-300 missile system](https://en.wikipedia.org/wiki/S-300_missile_system)。
- **注意**：
  - 乌克兰装备主要是 S‑300PS / PT（及 V1）；Commons 大量照片是俄方 S‑300PMU / PM / 400（发射车底盘为 MAZ‑543M 后期型或 BAZ 底盘，雷达为 30N6E / 92N6 "Grave Stone"，外形不同）。**S‑400 的发射车和雷达不能用作参考**。
  - AI 常把发射筒画成 2 个或 6 个、把筒画成方箱、把驾驶室画成单一驾驶室。
  - 竖直立起是本系统最有辨识度的姿态，建议精灵同时做"行军"与"竖起"两个状态。

### S‑300PT（`s300pt`） · 首批
- **类别**：牵引；**5P85‑1 / 5P85T 发射车为半挂车** [32]，由牵引车拖带 ≈（牵引车型号 KrAZ 系 ≈）。
- **关键外形特征**：
  1. 半挂车上 4 个大型圆柱形发射筒，作战时竖直立起 [32] ≈。
  2. 前方为独立的牵引卡车（KrAZ 类长头卡车 ≈）。
  3. **30N6 火控雷达**：PT 版本装在拖车 / 半挂上（而不是 8×8 自行车）≈，平板天线外形同 PS。
  4. **36D6 搜索雷达**（"Tin Shield"）为 PT 标准配置之一 [32]。
  5. 可选 76N6 低空雷达，常配 40V6 系高塔 [32] ≈。
- **组成**：1 部 30N6 雷达 + 1 部 36D6 搜索雷达 + 2–3 辆半挂发射车（各自带牵引车）[32]。
- **常见涂装**：苏式橄榄绿；乌军迷彩 ≈。
- **画面尺度提示**：> 15 m（牵引车 + 半挂）。
- **参考图检索**：Commons [Category:S-300PT](https://commons.wikimedia.org/wiki/Category:S-300PT)、[Category:30N6](https://commons.wikimedia.org/wiki/Category:30N6)；维基 [S-300 missile system](https://en.wikipedia.org/wiki/S-300_missile_system)。
- **注意**：
  - 与 PS 的主要区别：**半挂 + 牵引车**（PT）对比**一体式 8×8**（PS）。两者共用发射筒 / 雷达天线部件，建模时可复用。
  - WS03-007 只写"S‑300"，需确认是只做 PS、还是 PS + PT 都做（见"需要人工确认"第 1 条）。

### SAMP/T（`samp_t`）
- **类别**：卡车载；所有组件装在 8×8 卡车上 [33]。
- **关键外形特征**：
  1. 发射车：8×8 卡车，车背 **8 个垂直发射筒**（作战时整体竖起）[33]。
  2. 多功能雷达：Arabel 雷达，旋转的方形 / 立方体式天线罩，装在卡车上 ≈。
  3. 交战指挥模块：方舱车 [33]。
  4. 载车型号随国家而不同（法、意各异）≈。
- **组成**：4–6 辆发射车 + 1 部雷达 + 1 个指挥模块 [33]。画面建议：1 部雷达 + 2 辆发射车 + 1 个方舱。
- **常见涂装**：法 / 意军绿色或沙色 ≈。
- **画面尺度提示**：10–15 m。
- **参考图检索**：Commons [Category:Système sol-air moyenne-portée terrestre](https://commons.wikimedia.org/wiki/Category:Syst%C3%A8me_sol-air_moyenne-port%C3%A9e_terrestre)、[Category:ASTER 30 SAMP/T](https://commons.wikimedia.org/wiki/Category:ASTER_30_SAMP/T)、[Category:Arabel radar](https://commons.wikimedia.org/wiki/Category:Arabel_radar)；维基 [SAMP/T](https://en.wikipedia.org/wiki/SAMP/T)。
- **注意**：与 S‑300PS 同为"8×8 + 竖起发射"，区别在 **8 个较细的筒**（对比 S‑300 的 4 个粗筒）和西式平头驾驶室 ≈。SAMP/T NG 新型号外观不同 [33]，按游戏时间段选择。

### Patriot（`patriot`） · 首批
- **类别**：牵引（半挂）/ 卡车载。雷达和发射器装在 **M860 半挂车**上，由 **M983 HEMTT** 牵引车拖带 [34]。德国提供的系统发射器为卡车载 ≈（德军 MAN 卡车，需对照照片确认）。
- **关键外形特征**：
  1. **发射站（M901 / M902 / M903）**：半挂车上一个**大型箱式发射架**，可装 4 个 PAC‑2 大箱，或 16 个 PAC‑3 小箱（4×4 排列），或混装 [34]；作战时发射架斜向上抬起（约 38° ≈，不是竖直）。
  2. **AN/MPQ‑53 / 65 雷达**：半挂车上一面**大型平板相控阵天线**，前面一个大圆形主阵面 + 周围若干小阵面（IFF 等）≈，作战时斜立 [34]。
  3. **M983 HEMTT 牵引车**：8×8 美式长头 / 平头重型卡车，驾驶室在前 ≈ [34]。
  4. **交战控制站（ECS）**：卡车上的方舱 [34]。
  5. **天线桅杆组（AMG）**：拖车 / 卡车上的伸缩桅杆和天线 [34]。
  6. **电源车（EPP）** [34]；装填用 HEMTT 吊车车（GMT），吊臂收起时外形像"蝎子尾" [34]。
- **组成**：画面上一个火力单元建议：1 部雷达（半挂 + HEMTT）+ 1 个 ECS 方舱车 + 2–4 个发射站 + 1 辆电源车；装填车可选。
- **常见涂装**：美军沙色 / 北约绿；德国 / 荷兰系统为德军橄榄绿；乌军车辆常加伪装网 ≈。
- **画面尺度提示**：> 15 m（HEMTT + 半挂）。
- **参考图检索**：Commons [Category:MIM-104 Patriot](https://commons.wikimedia.org/wiki/Category:MIM-104_Patriot)、[Category:MIM-104 Patriot in Ukrainian service](https://commons.wikimedia.org/wiki/Category:MIM-104_Patriot_in_Ukrainian_service)（5 张乌克兰服役照片）、[Category:M903](https://commons.wikimedia.org/wiki/Category:M903)、[Category:AN/MPQ-65](https://commons.wikimedia.org/wiki/Category:AN/MPQ-65)、[Category:AN/MPQ-53](https://commons.wikimedia.org/wiki/Category:AN/MPQ-53)、[Category:HEMTT M983 Tractor](https://commons.wikimedia.org/wiki/Category:HEMTT_M983_Tractor)；维基 [MIM-104 Patriot](https://en.wikipedia.org/wiki/MIM-104_Patriot)。
- **注意**：
  - 发射架是**斜向抬起**，不是像 S‑300 那样竖直——AI 常混淆。
  - PAC‑2 大箱（4 个）与 PAC‑3 小箱（16 个）外观差别明显，按游戏设定选择；可做两种装填外观。
  - 2017 年后的 AN/MPQ‑65A 雷达为 AESA [34]，外观有细节差异 ≈。
  - 美式（半挂 + HEMTT）和德式（卡车载）两种外观，需人工决定以哪种为主（见"需要人工确认"第 4 条）。

### S‑200（`s200`）
- **类别**：固定阵地；导弹装在大型旋转导轨发射架上 [35]。
- **关键外形特征**（≈）：
  1. 单个发射架上挂 1 枚非常大的导弹（带 4 个助推器捆绑在弹体周围）≈。
  2. 发射架为固定在混凝土基座上的旋转导轨，周围有土堤掩体 ≈；苏联时期每营 6 个发射架 [35]。
  3. 火控雷达 5N62（"Square Pair"）为大型抛物面天线组 + 方舱（K‑1 / K‑2 两个舱）[35]。
  4. 导弹装填车（轨道 / 卡车）≈。
- **组成**：若干发射架 + 1 部火控雷达 + 掩体。画面建议：2 个发射架 + 1 部雷达。
- **常见涂装**：苏式橄榄绿 / 灰色。
- **画面尺度提示**：10–15 m（导弹 + 发射架）。
- **参考图检索**：Commons [Category:S-200](https://commons.wikimedia.org/wiki/Category:S-200)；维基 [S-200 missile system](https://en.wikipedia.org/wiki/S-200_missile_system)。
- **注意**：乌克兰"复活"的 S‑200 改装细节未公开 [35] ≈，外观按原型即可。AI 常把它画成 S‑75（更小、两级、细长）。

### 拦截无人机班组（`interceptor_drone_team`）
- **类别**：自行；皮卡（数值表"皮卡 80"）+ 小型拦截无人机（代表型号 Sting [36]）。
- **关键外形特征**：
  1. Sting：小型"子弹形"四旋翼无人机，机身为圆筒状，常采用竖直起飞 ≈（部分为 3D 打印 [36]）。
  2. 班组在地面或皮卡车斗上起飞，操作员戴 FPV 眼镜 / 持遥控器 ≈。
  3. 皮卡上有天线、地面站箱、小型发射支架 ≈。
- **组成**：1 辆皮卡 + 2–4 名操作员 + 若干拦截无人机。
- **常见涂装**：无人机常见黑色 / 灰色 / 绿色；皮卡同火力组。
- **画面尺度提示**：5–10 m（皮卡）；无人机 < 1 m。
- **参考图检索**：Commons [Category:Sting (drone)](https://commons.wikimedia.org/wiki/Category:Sting_(drone))（4 张）；维基 [Sting (drone)](https://en.wikipedia.org/wiki/Sting_(drone))。
- **注意**：泛指"拦截无人机班组"，外观可艺术化；不必只用 Sting。

### 喷气式拦截无人机（`jet_interceptor_drone`）
- **类别**：自行；皮卡 / 发射架 + 小型喷气无人机（2026 原型）。
- **关键外形特征**（≈，公开图像不足）：
  1. 小型喷气无人机，细长机身、小翼面，尾部涡喷喷口 ≈。
  2. 由车载导轨 / 弹射架发射 ≈。
- **组成**：1 辆皮卡 / 轻卡 + 发射架 + 操作员。
- **常见涂装**：灰色 / 黑色 ≈。
- **画面尺度提示**：5–10 m ≈。
- **参考图检索**：Commons 未找到；维基未找到对应条目。
- **注意**：**泛指，外观可艺术化**；避免照搬任何具体型号的未公开细节。

---

## 二、探测单位（`data/units/sensors.json`）

> 数据只给出了类别，没有指定具体型号。以下"典型外观"是在乌克兰常见的同类装备，仅作外观参考，标 ≈。

### 国家预警网（`national_early_warning`）
- 无实体外观，用图标表示。

### 苏制远程警戒雷达（`soviet_long_range_radar`）
- **类别**：卡车载。典型参考：P‑18 ≈（装在两辆 Ural‑4320 卡车上 [37]）。
- **关键外形特征**：
  1. 卡车上的高桅杆，顶部为 **16 根八木天线，分上下两排各 8 根** [37]，整体像一个大型"鱼骨"框架。
  2. 天线高度和俯仰可调 [37]。
  3. 第二辆卡车装设备方舱 [37]。
- **组成**：天线车 + 设备车（+ 可选发电车）。
- **常见涂装**：苏式橄榄绿。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:P-18](https://commons.wikimedia.org/wiki/Category:P-18)、[Category:Ural-375](https://commons.wikimedia.org/wiki/Category:Ural-375)；维基 [P-18 radar](https://en.wikipedia.org/wiki/P-18_radar)。
- **注意**：其他同类（如更大型的苏制远程雷达）外观差异大，数据未指定型号；建议以 P‑18 为通用外观。

### 苏制中程警戒雷达（`soviet_mid_range_radar`）
- **类别**：卡车 / 拖车。典型参考：36D6 / ST‑68U（"Tin Shield"，S‑300PT 配套 [32]）≈，或 P‑19 ≈。
- **关键外形特征**：
  1. 36D6：拖车上一面大型弧形网状反射面（截断抛物面），旋转 ≈。
  2. P‑19：ZiL‑131 卡车上两个上下排列的开放框架椭圆抛物面天线 [38]，第二辆卡车装电子设备 [38]。
- **组成**：天线车 / 拖车 + 设备车。
- **常见涂装**：苏式橄榄绿。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:ST-68U](https://commons.wikimedia.org/wiki/Category:ST-68U)、[Category:P-19](https://commons.wikimedia.org/wiki/Category:P-19)、[Category:ZIL-131](https://commons.wikimedia.org/wiki/Category:ZIL-131)；维基 [P-19 radar](https://en.wikipedia.org/wiki/P-19_radar)（36D6 / ST‑68U 英文维基无独立条目）。
- **注意**：需人工决定用哪一种作为通用外观。

### 西方 3D 警戒雷达（`western_3d_radar`）
- **类别**：卡车载。典型参考：Thales Ground Master 200 / 400（6×6 或 8×8 卡车载 [39]）、Hensoldt TRML‑4D [31]、Saab Giraffe ≈。
- **关键外形特征**：
  1. 卡车 / 方舱顶部的**长方形平板天线**，旋转 ≈。
  2. 行军时天线放平，作战时竖起 ≈。
  3. 欧式军用卡车底盘 ≈。
- **组成**：1 辆雷达车（+ 可选电源车）。
- **常见涂装**：北约橄榄绿 ≈。
- **画面尺度提示**：10–15 m ≈。
- **参考图检索**：Commons [Category:Ground Master 200](https://commons.wikimedia.org/wiki/Category:Ground_Master_200)、[Category:Ground Master 400](https://commons.wikimedia.org/wiki/Category:Ground_Master_400)、[Category:Hensoldt TRML-4D](https://commons.wikimedia.org/wiki/Category:Hensoldt_TRML-4D)、[Category:Giraffe radar](https://commons.wikimedia.org/wiki/Category:Giraffe_radar)；维基 [Ground Master 400](https://en.wikipedia.org/wiki/Ground_Master_400)、[Ground Master 200 Multi Mission](https://en.wikipedia.org/wiki/Ground_Master_200_Multi_Mission)、[TRML](https://en.wikipedia.org/wiki/TRML)、[Giraffe radar](https://en.wikipedia.org/wiki/Giraffe_radar)。
- **注意**：与 IRIS‑T SLM 的 TRML‑4D 雷达车外观可共用。

### 低空补盲雷达（`gap_filler_radar`）
- **类别**：拖车 / 塔架（数据"车载 / 塔架"）。典型参考：AN/MPQ‑64 Sentinel（拖车载 [28]）≈；或装在塔架 / 楼顶上的小型平板雷达 ≈。
- **关键外形特征**：
  1. 小型旋转平板天线 [28]。
  2. 拖车版：双轮拖车 + 天线 + 发电机，由轻型军车牵引 [28]。
  3. 塔架版：几块小平板天线装在铁塔 / 高杆顶部 ≈。
- **组成**：1 部雷达（拖车或塔架）。
- **常见涂装**：橄榄绿 ≈。
- **画面尺度提示**：< 5 m（雷达）/ 5–10 m（含拖车）。
- **参考图检索**：Commons [Category:AN/MPQ-64 Sentinel](https://commons.wikimedia.org/wiki/Category:AN/MPQ-64_Sentinel)；维基 [AN/MPQ-64 Sentinel](https://en.wikipedia.org/wiki/AN/MPQ-64_Sentinel)。
- **注意**：泛指，外观可艺术化。

### 声学哨（`acoustic_post`）
- **类别**：固定。参考：乌克兰 Sky Fortress 声学网——杆子上安装麦克风和智能手机 [40]。
- **关键外形特征**：
  1. 一根细杆 / 木杆，顶部一个小型麦克风阵列和防雨罩 [40] ≈。
  2. 杆上绑着手机 / 小盒子，可能有小型太阳能板 ≈。
- **组成**：单个传感器杆。
- **常见涂装**：灰色 / 民用色 ≈。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons 未找到；维基 [Sky Fortress (drone defense system)](https://en.wikipedia.org/wiki/Sky_Fortress_(drone_defense_system))。
- **注意**：**泛指，外观可艺术化**。

### 目视观察哨（`visual_observer`）
- **类别**：人员；2–3 人观察小组。**泛指，外观可艺术化。**
- **关键外形特征**：
  1. 人员持望远镜 / 热像仪，位于屋顶、高处或掩体 ≈。
  2. 可配便携探照灯（夜间）和无线电台 ≈。
- **组成**：2–3 名观察员 + 简易掩体。
- **常见涂装**：乌军迷彩 / 民用服装（志愿者）。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons [Category:Military binoculars](https://commons.wikimedia.org/wiki/Category:Military_binoculars)、[Category:Searchlights](https://commons.wikimedia.org/wiki/Category:Searchlights)；维基无专门条目。
- **注意**：不要画出可辨认的真实人物。

### 无线电侦测器（`radio_detector`）
- **类别**：便携 / 固定。**泛指，外观可艺术化。**
- **关键外形特征**：
  1. 小型设备箱 + 几根鞭状 / 板状天线，放在三脚架或杆上 ≈。
  2. 可配一台笔记本 / 平板作为显示终端 ≈。
- **组成**：设备 + 1–2 名操作员。
- **常见涂装**：橄榄绿 / 黑色。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons [Category:Electronic warfare equipment of Ukraine](https://commons.wikimedia.org/wiki/Category:Electronic_warfare_equipment_of_Ukraine)（含各类乌制电子设备子分类，可借鉴外形）；维基未找到对应条目。
- **注意**：只表现外观，不写工作原理。

### 民众上报（`civilian_reports`）
- 无实体外观，用图标表示。

### 系留气球传感器（`tethered_balloon`）
- **类别**：系留气球 + 地面系留车。**数据本身标注 ≈，在乌克兰的使用情况未核实；泛指，外观可艺术化。**
- **关键外形特征**：
  1. 流线型气囊，尾部 3–4 片充气尾翼 ≈。
  2. 气囊下方挂传感器吊舱 ≈。
  3. 地面有绞盘车 / 系留拖车和系留缆 ≈。
- **组成**：气球 + 系留车。
- **常见涂装**：白色 / 浅灰色。
- **画面尺度提示**：> 15 m（气囊）。
- **参考图检索**：Commons [Category:Aerostats](https://commons.wikimedia.org/wiki/Category:Aerostats)、[Category:Tethered balloons](https://commons.wikimedia.org/wiki/Category:Tethered_balloons)；维基 [Aerostat](https://en.wikipedia.org/wiki/Aerostat)。
- **注意**：不要照搬某具体型号。

---

## 三、电子战单位（`data/units/ew.json`）

> 只描述外观（天线阵列的大致样子、载车），不涉及工作原理和技术参数。乌制电子战设备公开图片可在 Commons [Category:Electronic warfare equipment of Ukraine](https://commons.wikimedia.org/wiki/Category:Electronic_warfare_equipment_of_Ukraine) 中查到（含 Bukovel‑AD、Anklav、Nota、Kvertus、EDM4S 等子分类）。

### 区域导航干扰站（`area_nav_jammer`）
- **类别**：卡车 / 方舱 / 固定（数值表"60 / 固定"）。典型参考：Bukovel 类设备 [41]、Anklav 类设备 [41] ≈。
- **关键外形特征**：
  1. 一根桅杆或三脚架，顶部一圈 / 一组板状和鞭状天线 ≈。
  2. 设备箱 / 方舱，可装在轻卡或皮卡上 ≈。
  3. 车顶可能有可伸缩桅杆 ≈。
- **组成**：1 套天线 + 设备箱 + 载车。
- **常见涂装**：橄榄绿 / 灰色。
- **画面尺度提示**：5–10 m（含载车）。
- **参考图检索**：Commons [Category:Bukovel-AD](https://commons.wikimedia.org/wiki/Category:Bukovel-AD)、[Category:Anklav C-UAV](https://commons.wikimedia.org/wiki/Category:Anklav_C-UAV)；维基 [Bukovel (counter unmanned aircraft system)](https://en.wikipedia.org/wiki/Bukovel_(counter_unmanned_aircraft_system))、[Ukraine and electronic warfare](https://en.wikipedia.org/wiki/Ukraine_and_electronic_warfare)。
- **注意**：泛指，外观可艺术化。

### 导航欺骗站（`nav_spoofer`）
- **类别**：固定 / 方舱。公开资料提及乌克兰 Pokrova 系统 2024 年投入使用 [41]，但无可用外观图片。**泛指，外观可艺术化。**
- **关键外形特征**（≈）：
  1. 固定站点：铁塔或楼顶上的天线组 + 设备方舱 ≈。
  2. 可做成"通信塔 + 方舱"外形，便于融入城市地图 ≈。
- **组成**：天线塔 + 方舱。
- **常见涂装**：灰色 / 民用色。
- **画面尺度提示**：5–10 m ≈。
- **参考图检索**：Commons 未找到；维基 [Ukraine and electronic warfare](https://en.wikipedia.org/wiki/Ukraine_and_electronic_warfare)。
- **注意**：只表现外观；与区域导航干扰站要在外形上可区分（建议：干扰站 = 车载，欺骗站 = 固定塔架）。

### 反无人机干扰站（`counter_uas_jammer`）
- **类别**：车载 / 三脚架。典型参考：Nota、Anklav、Polonez 一类 C‑UAV 设备 ≈。
- **关键外形特征**：
  1. 一组朝向不同方向的小型板状天线，装在三脚架或车顶 ≈。
  2. 小型设备箱 + 电池 / 发电机 ≈。
- **组成**：设备 + 载车（可选）。
- **常见涂装**：橄榄绿 / 黑色。
- **画面尺度提示**：< 5 m（设备）/ 5–10 m（含车）。
- **参考图检索**：Commons [Category:Nota C-UAV](https://commons.wikimedia.org/wiki/Category:Nota_C-UAV)、[Category:Anklav C-UAV](https://commons.wikimedia.org/wiki/Category:Anklav_C-UAV)、[Category:Polonez C-UAV](https://commons.wikimedia.org/wiki/Category:Polonez_C-UAV)；维基 [Ukraine and electronic warfare](https://en.wikipedia.org/wiki/Ukraine_and_electronic_warfare)。
- **注意**：泛指，外观可艺术化。

### 单兵反无人机枪（`handheld_counter_uas`）
- **类别**：便携；步枪形外壳 + 前端天线。典型参考：EDM4S、Kvertus 一类 ≈。
- **关键外形特征**：
  1. 枪托 + 握把 + 机匣式外壳，前端为一块 / 多块板状或八木天线 ≈。
  2. 背包电源或枪身电池 ≈。
- **组成**：1 名士兵。
- **常见涂装**：黑 / 沙 / 橄榄绿。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons [Category:EDM4S jammer in Ukrainian service](https://commons.wikimedia.org/wiki/Category:EDM4S_jammer_in_Ukrainian_service)、[Category:Kvertus drone jammers](https://commons.wikimedia.org/wiki/Category:Kvertus_drone_jammers)；维基未找到专门条目。
- **注意**：AI 可能画成真枪；需保证**前端是天线、没有枪管**。

### 车载防护罩（`vehicle_shield`）
- **类别**：装备槽（附加在其他车辆上，数据"只保护本车"）。无独立精灵。
- **关键外形特征**：车顶 / 炮塔上加装的一小簇鞭状 / 蘑菇形天线 + 小设备盒 ≈；可作为任意车辆模型的附加部件（"天线簇"贴件）。
- **常见涂装**：随载车。
- **画面尺度提示**：附加件，< 1 m。
- **参考图检索**：Commons [Category:Electronic warfare equipment of Ukraine](https://commons.wikimedia.org/wiki/Category:Electronic_warfare_equipment_of_Ukraine)；维基 [Ukraine and electronic warfare](https://en.wikipedia.org/wiki/Ukraine_and_electronic_warfare)。
- **注意**：泛指，外观可艺术化；建议做一个通用天线簇部件，装到装备该槽位的单位上。

---

## 四、欺骗单位（`data/units/deception.json`）

### 诱饵辐射源（`decoy_emitter`）
- **类别**：便携 / 小型拖车。**泛指，外观可艺术化。**
- **关键外形特征**：一个小设备箱 + 一面小天线 / 简易雷达外形天线，可放在空地或小拖车上 ≈。
- **组成**：单件设备。
- **常见涂装**：橄榄绿。
- **画面尺度提示**：< 5 m。
- **参考图检索**：Commons 未找到；维基 [Military dummy](https://en.wikipedia.org/wiki/Military_dummy)（通用参考）。
- **注意**：指挥层可显示为"假雷达"图标；实景层可做得像一部小雷达。

### 旧雷达牺牲开机（`sacrificial_radar`）
- **类别**：卡车 / 拖车。外观即库存老式苏制雷达（同 `soviet_long_range_radar` / `soviet_mid_range_radar`，如 P‑18、P‑19 ≈）。
- **关键外形特征**：可复用苏制雷达模型，加旧化效果（锈迹、褪色、缺件）≈。
- **组成**：1 部雷达车。
- **常见涂装**：褪色苏式橄榄绿。
- **画面尺度提示**：5–10 m。
- **参考图检索**：Commons [Category:P-18](https://commons.wikimedia.org/wiki/Category:P-18)、[Category:P-19](https://commons.wikimedia.org/wiki/Category:P-19)；维基 [P-18 radar](https://en.wikipedia.org/wiki/P-18_radar)。
- **注意**：与正常雷达靠旧化程度区分。

### 假发射车（`fake_launcher`）
- **类别**：充气 / 木制假目标。**泛指，外观可艺术化。**
- **关键外形特征**：
  1. 外形仿制某个发射车（如 S‑300 发射车、IRIS‑T 发射车）≈，比例接近但细节简化。
  2. 充气版：表面略鼓、接缝和充气管可见 ≈；木制版：平板拼接、棱角生硬 ≈。
  3. 近距离可见破绽（无车轮细节、无驾驶室玻璃反光等）——可用于"侦察质量越高越容易识破"的表现。
- **组成**：单件假目标（可配伪装网）。
- **常见涂装**：同仿制对象。
- **画面尺度提示**：随仿制对象。
- **参考图检索**：Commons [Category:Mock-ups of tanks](https://commons.wikimedia.org/wiki/Category:Mock-ups_of_tanks)、[Category:Inflatable Su-27 mock-ups](https://commons.wikimedia.org/wiki/Category:Inflatable_Su-27_mock-ups)（质感参考，非乌克兰实物）；维基 [Military dummy](https://en.wikipedia.org/wiki/Military_dummy)。
- **注意**：建议直接复用真实发射车模型，换"充气材质 / 木板材质"着色器。

---

## 五、外部支援 · 战斗机（`data/support/fighters.json`）

> 数据中只有一个条目 `fighter`（显示名"F‑16 / Mirage 2000 / MiG‑29"），但外观上是三种完全不同的飞机，下面分开写。

### F‑16（`fighter`，机型 A）
- **类别**：单发战斗机。乌克兰使用的是欧洲国家转交的 F‑16AM / BM（MLU 升级型）≈。
- **关键外形特征**：
  1. 机腹下方单个"嘴形"进气口（位于座舱下方偏后）≈。
  2. 气泡式单片座舱盖（BM 双座型更长）≈。
  3. 单垂尾，单发，翼身融合，中等后掠的梯形主翼 ≈。
  4. 两翼尖可挂导弹导轨；翼下多个挂架 ≈。
- **组成**：单机（编队可 2 架）。
- **常见涂装**：灰色两色制空迷彩；乌军机徽（蓝黄圆标 / 三叉戟）≈。
- **画面尺度提示**：≈ 15 m（10–15 上限）。
- **参考图检索**：Commons [Category:F-16 in service with Ukraine](https://commons.wikimedia.org/wiki/Category:F-16_in_service_with_Ukraine)（25 个文件）、[Category:General Dynamics F-16 Fighting Falcon](https://commons.wikimedia.org/wiki/Category:General_Dynamics_F-16_Fighting_Falcon)；维基 [General Dynamics F-16 Fighting Falcon](https://en.wikipedia.org/wiki/General_Dynamics_F-16_Fighting_Falcon)。
- **注意**：不同批次（荷兰 / 丹麦 / 挪威 / 比利时）有细节差异 ≈；不要使用美军新型 F‑16V 或带保形油箱的版本作参考。

### Mirage 2000（`fighter`，机型 B）
- **类别**：单发战斗机。乌克兰获得的是法国 Mirage 2000‑5F ≈。
- **关键外形特征**：
  1. **无尾三角翼**（没有水平尾翼），单垂尾 ≈。
  2. 机身两侧半圆形进气口，带锥形中心体 ≈。
  3. 进气口上方小型边条 ≈；机头细长，空中加油管可能在机头右侧 ≈。
- **组成**：单机。
- **常见涂装**：法空军灰色 ≈。
- **画面尺度提示**：10–15 m。
- **参考图检索**：Commons [Category:Dassault Mirage 2000 in service with Ukraine](https://commons.wikimedia.org/wiki/Category:Dassault_Mirage_2000_in_service_with_Ukraine)（14 个文件）、[Category:Mirage 2000-5F](https://commons.wikimedia.org/wiki/Category:Mirage_2000-5F)、[Category:Dassault Mirage 2000](https://commons.wikimedia.org/wiki/Category:Dassault_Mirage_2000)；维基 [Dassault Mirage 2000](https://en.wikipedia.org/wiki/Dassault_Mirage_2000)。
- **注意**：AI 常给三角翼加上平尾，或混淆为 Rafale（Rafale 有前翼、双发）。

### MiG‑29（`fighter`，机型 C）
- **类别**：双发战斗机。
- **关键外形特征**：
  1. 双发，两个分离的发动机舱，**双垂尾**（略外倾）≈。
  2. 机翼下方两个大型矩形进气口，与机身分开 ≈。
  3. 机翼前缘根部有大边条 ≈。
  4. 座舱盖在细长机头上 ≈。
- **组成**：单机。
- **常见涂装**：乌克兰空军**数码像素迷彩**（灰 / 蓝灰）或旧式灰色 ≈。
- **画面尺度提示**：> 15 m。
- **参考图检索**：Commons [Category:Mikoyan-Gurevich MiG-29 in Ukrainian service](https://commons.wikimedia.org/wiki/Category:Mikoyan-Gurevich_MiG-29_in_Ukrainian_service)（150 个文件）、[Category:Mikoyan MiG-29](https://commons.wikimedia.org/wiki/Category:Mikoyan_MiG-29)；维基 [Mikoyan MiG-29](https://en.wikipedia.org/wiki/Mikoyan_MiG-29)。
- **注意**：与 Su‑27 区分：MiG‑29 更小、垂尾在发动机舱上方。MiG‑29 也是俄方装备，涂装需明确是乌军风格以免混淆敌我。

---

## 六、与现有文档的差异

> 不修改现有文档，列在这里由人决定。

1. **输出路径**：WBS WS10-003 的输出写的是 `docs/reference_list.md`（单文件），本次按分派要求写到 `docs/reference_list/friendly.md`。如果确认采用目录结构，需要更新 WBS。
2. **`fighter` 单条目对应三种机型**：数据中 `fighter` 只有一个 ID，但 F‑16 / Mirage 2000 / MiG‑29 外观完全不同（单发 / 无尾三角翼 / 双发双垂尾）。需要决定：拆成三个 ID，还是在同一 ID 下按关卡 / 时间段切换外观。
3. **`skynex` 的 mobility**：数据为 `towed`（数值表"牵引"），但英文维基称乌克兰获得的 Skynex 组件全部装在 HX 卡车上 [11]。外观上应为卡车载；玩法上是否仍按"牵引 / 分钟级展开"处理由人决定。
4. **`aspide` 的显示名 "Aspide / Spada"**：时间表文档写"Aspide 2000 / Spada，西班牙"。按维基，西班牙使用的是 Skyguard‑Aspide，Spada 为意大利空军系统 [26]，两者外观不同 ≈。需确认乌克兰实际接收的是哪种（或两种都有），以决定建模对象。
5. **`frankensam` 是一类组合而非单一装备**：时间表列出至少三种组合，外观各不相同，而数据只有一个单位。且 Buk + RIM‑7 组合与 `buk_m1` 外观几乎相同。
6. **`sky_sentinel` 命名冲突**：英文维基 "Sky Sentinel" 是无关的无人飞艇条目，检索资料时容易误用（不影响数据，仅提示）。
7. **`tethered_balloon`**：数据和数值表均标 ≈，本次也未找到乌克兰使用系留气球传感器的公开资料。
8. **`s300pt` / `s300ps`**：WS03-007 只写"S‑300"，数据中是两个外观不同的单位（PS 为 8×8 自行，PT 为半挂牵引）[32]。

## 七、需要人工确认的事项

1. **S‑300 首批建模范围**：只做 S‑300PS（8×8），还是 PS + PT（半挂）都做？两者可共用发射筒和 30N6 雷达天线部件。
2. **IRIS‑T 首批建模范围**：WS03-007 写"IRIS‑T"，数据中有 SLS 和 SLM 两个单位，外观差异大。建议首批做 SLM（发射车 + TRML‑4D 雷达车）。
3. **FrankenSAM 外观方案**：选一种组合作为代表外观，并决定如何与 Buk‑M1 区分。
4. **Patriot 外观版本**：美式（M860 半挂 + M983 HEMTT）还是德式（卡车载）为主。乌克兰同时有两类来源 ≈。
5. **Buk‑M1 负重轮数、Gepard 负重轮数、IRIS‑T SLM 发射箱排列、Patriot 发射架抬起角度**：以上均标 ≈，建模前需对照 Commons 乌克兰服役照片确认。
6. **探测单位的代表型号**：数据只给类别；本清单建议苏制远程 = P‑18、苏制中程 = 36D6 或 P‑19、西方 3D = GM200/400 或 TRML‑4D、补盲 = Sentinel 类小型雷达。需人工选定。
7. **车辆品牌**：火力组皮卡、拦截无人机班组的民用车辆建议做成"无品牌通用皮卡"，避免商标问题（GDD 17 第 8 条）。
8. **乌军识别标记**：白色十字 / 三角等识别标记在不同时期、不同方向使用不同，是否在模型上表现、用哪种，需人工决定 ≈。

## 来源

> "已打开核对"= 用维基 API 拉取原文并检索了相关段落；"仅核实存在"= 只确认了页面 / 分类存在。所有 Commons 分类均已用 Commons API 确认存在（2026-10-15）。

[1] 9K38 Igla — https://en.wikipedia.org/wiki/9K38_Igla（仅核实存在）
[2] FIM-92 Stinger — https://en.wikipedia.org/wiki/FIM-92_Stinger（仅核实存在）
[3] Piorun (missile) — https://en.wikipedia.org/wiki/Piorun_(missile)（已打开核对）
[4] Starstreak — https://en.wikipedia.org/wiki/Starstreak（已打开核对）
[5] Lightweight Multirole Missile / Alvis Stormer — https://en.wikipedia.org/wiki/Lightweight_Multirole_Missile ；https://en.wikipedia.org/wiki/Alvis_Stormer（已打开核对）
[6] Technical (vehicle) — https://en.wikipedia.org/wiki/Technical_(vehicle)（已打开核对）
[7] ZU-23-2 — https://en.wikipedia.org/wiki/ZU-23-2（已打开核对）
[8] AZP S-60 — https://en.wikipedia.org/wiki/AZP_S-60（已打开核对）
[9] Forbes, "Ukraine Turns To AI-Controlled Guns To Stop Russian Shahed Drones" — https://www.forbes.com/sites/davidhambling/2025/05/27/ukraine-turns-to-ai-controlled-guns-to-stop-russian-shahed-drones/（取自 docs/俄乌战争塔防_武器投入时间表.md，未打开核对）
[10] Flakpanzer Gepard — https://en.wikipedia.org/wiki/Flakpanzer_Gepard（已打开核对）
[11] Skynex — https://en.wikipedia.org/wiki/Skynex（已打开核对）
[12] Rheinmetall 新闻稿（Skyranger 35 乌克兰）— https://www.rheinmetall.com/de/media/news-watch/news/2025/10/2025-10-10-rheinmetall-skyranger-35-ukraine（取自时间表文档，未打开核对）
[13] Skyranger 35 — https://en.wikipedia.org/wiki/Skyranger_35（已打开核对）
[14] 9K35 Strela-10 — https://en.wikipedia.org/wiki/9K35_Strela-10（已打开核对）
[15] 9K33 Osa — https://en.wikipedia.org/wiki/9K33_Osa（已打开核对）
[16] AN/TWQ-1 Avenger — https://en.wikipedia.org/wiki/AN/TWQ-1_Avenger（已打开核对）
[17] VAMPIRE (weapon) — https://en.wikipedia.org/wiki/VAMPIRE_(weapon)（已打开核对）
[18] Raven (air defence) — https://en.wikipedia.org/wiki/Raven_(air_defence)（已打开核对）
[19] Gravehawk — https://en.wikipedia.org/wiki/Gravehawk（已打开核对）
[20] Crotale (missile) — https://en.wikipedia.org/wiki/Crotale_(missile)（已打开核对）
[21] RBS 70 — https://en.wikipedia.org/wiki/RBS_70（已打开核对）
[22] IRIS-T SL — https://en.wikipedia.org/wiki/IRIS-T_SL（已打开核对；其中 Iveco 4×4 报道取自维基参考文献，未逐篇核对）
[23] RIM-7 Sea Sparrow（FrankenSAM 重定向至此）— https://en.wikipedia.org/wiki/RIM-7_Sea_Sparrow（已打开核对）
[24] Buk missile system — https://en.wikipedia.org/wiki/Buk_missile_system（已打开核对）
[25] MIM-23 Hawk — https://en.wikipedia.org/wiki/MIM-23_Hawk（已打开核对）
[26] Aspide — https://en.wikipedia.org/wiki/Aspide（已打开核对）
[27] NASAMS — https://en.wikipedia.org/wiki/NASAMS（已打开核对）
[28] AN/MPQ-64 Sentinel — https://en.wikipedia.org/wiki/AN/MPQ-64_Sentinel（已打开核对）
[29] IRIS-T SLM（乌克兰语维基）— https://uk.wikipedia.org/wiki/IRIS-T_SLM（已打开核对）
[30] IRIS-T SLM（德语维基）— https://de.wikipedia.org/wiki/IRIS-T_SLM（已打开核对）
[31] TRML — https://en.wikipedia.org/wiki/TRML（已打开核对）
[32] S-300 missile system — https://en.wikipedia.org/wiki/S-300_missile_system（已打开核对）
[33] SAMP/T — https://en.wikipedia.org/wiki/SAMP/T（已打开核对）
[34] MIM-104 Patriot — https://en.wikipedia.org/wiki/MIM-104_Patriot（已打开核对）
[35] S-200 missile system — https://en.wikipedia.org/wiki/S-200_missile_system（已打开核对）
[36] Sting (drone) — https://en.wikipedia.org/wiki/Sting_(drone)（已打开核对）
[37] P-18 radar — https://en.wikipedia.org/wiki/P-18_radar（已打开核对）
[38] P-19 radar — https://en.wikipedia.org/wiki/P-19_radar（已打开核对）
[39] Ground Master 400 — https://en.wikipedia.org/wiki/Ground_Master_400（已打开核对）
[40] Sky Fortress (drone defense system) — https://en.wikipedia.org/wiki/Sky_Fortress_(drone_defense_system)（已打开核对）
[41] Ukraine and electronic warfare — https://en.wikipedia.org/wiki/Ukraine_and_electronic_warfare（已打开核对）
[42] General Dynamics F-16 Fighting Falcon / Dassault Mirage 2000 / Mikoyan MiG-29 — https://en.wikipedia.org/wiki/General_Dynamics_F-16_Fighting_Falcon ；https://en.wikipedia.org/wiki/Dassault_Mirage_2000 ；https://en.wikipedia.org/wiki/Mikoyan_MiG-29（仅核实存在 / 拉取原文未逐段核对；战斗机外形描述为通识，标 ≈）
