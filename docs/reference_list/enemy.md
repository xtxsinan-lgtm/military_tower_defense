# 装备外观参考清单 · 敌方单位（WS10-003）

> 资料截至 2026-10-15。覆盖 `data/enemies/munitions.json`（34 条）与 `data/enemies/platforms.json`（11 条），顺序与 ID 同数据文件，显示名取自 `data/loc/zh.json`。
> 状态：🟡 AI 初稿，**需人工审核**（见文末“需要人工确认的事项”）。

## 用途说明

- **给谁用**：做精灵 / 尾迹粒子的人（WS03-003 / 008）、校正 AI 生成模型的人（WS03-007）、收集参考图的人（WS03-006）、做音效的人（WS08，参考“声音特征”）。
- **只写可见外形**：按 GDD 第 17 章第 5 条与 AGENTS.md 第 3 节第 8 条，本清单**不写**射程、战斗部、精度、制导方式、速度等技术参数；“尺度等级”只用于决定精灵像素尺寸（03.A：4 像素/米，例如 3.5 m 的 Shahed ≈ 14 像素）。
- **画面表现**：按 GDD 16.2 与 WBS 03.A，导弹、无人机在实景层主要表现为“小精灵 + 尾迹 / 光点”，拉远后切到指挥层符号；因此每个弹药条目都有“画面表现建议”（俯视轮廓、尾迹类型、声音特征）。飞机 / 直升机进入地图，需要 16 方向精灵。
- **可靠性标注**：每条事实后的 [n] 指向文末来源；带 ≈ 的是推断、来源不足或只有单方面说法，**做美术前需要对照照片确认**。声音特征一律是给音效设计的**艺术化描述**，不作为史实。
- **参考图**：Wikimedia Commons 分类链接均已用 Commons API（`action=query&titles=Category:…`）确认存在；不存在的明确写出。维基条目链接已用 en.wikipedia API 确认存在。参考图仅作内部参考，使用前逐张确认授权（WS03-006）。

### 尺度等级与画面表现方式图例

| 尺度等级 | 长度范围 | 4 px/m 下的精灵长度 |
|---|---|---|
| S0 | < 1 m | < 4 px（只用光点 / 图标） |
| S1 | 1–5 m | 4–20 px |
| S2 | 5–10 m | 20–40 px |
| S3 | 10–15 m | 40–60 px |
| S4 | > 15 m | > 60 px |

（S0 是在模板的 4 档基础上为 FPV 增加的细分；其余对应模板的 < 5 m / 5–10 m / 10–15 m / > 15 m。）

画面表现方式：**光点**（几乎只看灯光 / 尾迹）、**小精灵 + 尾迹**、**下落条纹**（从画面外高速落下的亮线，GDD 16.1）、**完整精灵**（16 方向）、**不入图**（只在简报 / 插画中出现）。

## 总表

| # | ID | 显示名 | 类别（数据 `category` / 平台） | 尺度 | 画面表现方式 |
|---|---|---|---|---|---|
| 1 | `gerbera` | Gerbera 诱饵 | decoy | S1 | 小精灵（无尾迹） |
| 2 | `shahed_136` | Shahed‑136 / Geran‑2 | drone | S1 | 小精灵（无尾迹） |
| 3 | `geran_2_heavy` | Geran‑2 大战斗部型 | drone | S1 | 小精灵（无尾迹） |
| 4 | `geran_3` | Geran‑3 | jet_drone | S1 | 小精灵 + 弱喷气尾迹 |
| 5 | `geran_4` | Geran‑4 | jet_drone | S1 | 小精灵 + 弱喷气尾迹 |
| 6 | `geran_5` | Geran‑5 | jet_drone | S1 ≈ | 小精灵 + 弱喷气尾迹 |
| 7 | `lancet` | Lancet | loitering | S1 | 小精灵（无尾迹） |
| 8 | `fpv_fiber` | 光纤 FPV | fpv | S0 | 光点 + 可选光纤细线 |
| 9 | `fpv_radio` | 无线电 FPV | fpv | S0 | 光点 |
| 10 | `molniya` | Molniya | loitering | S1 | 小精灵（无尾迹） |
| 11 | `kh101` | Kh‑101 / Kh‑555 | cruise_missile | S2 | 小精灵 + 弱喷气尾迹 |
| 12 | `kalibr` | 口径 Kalibr | cruise_missile | S2 | 小精灵 + 弱喷气尾迹（发射段亮尾焰） |
| 13 | `iskander_k` | 伊斯坎德尔‑K | cruise_missile | S2 | 小精灵 + 弱喷气尾迹 |
| 14 | `kh59` | Kh‑59 / Kh‑69 | cruise_missile | S2 | 小精灵 + 弱喷气尾迹 |
| 15 | `banderol` | S8000 Banderol | cruise_missile | S1 ≈ | 小精灵 + 弱喷气尾迹 |
| 16 | `oniks` | Oniks | supersonic_missile | S2 | 小精灵 + 喷气尾迹（快速） |
| 17 | `kh22` | Kh‑22 | supersonic_missile | S3 | 下落条纹 + 火箭亮尾焰 |
| 18 | `kh32` | Kh‑32 | supersonic_missile | S3 | 下落条纹 + 火箭亮尾焰 |
| 19 | `kh31p` | Kh‑31P 反辐射导弹 | anti_radiation | S1–S2 边界 | 小精灵 + 短亮尾焰转弱尾迹 |
| 20 | `s300_ground` | S‑300 对地 | ballistic | S2 | 下落条纹 |
| 21 | `kn23` | KN‑23 | ballistic | S2 | 下落条纹 |
| 22 | `iskander_m` | 伊斯坎德尔‑M | ballistic | S2 | 下落条纹 |
| 23 | `iskander_m_mod` | 伊斯坎德尔‑M 改 | ballistic | S2 | 下落条纹（末段摆动） |
| 24 | `kinzhal` | 匕首 Kinzhal | hypersonic | S2 | 下落条纹 |
| 25 | `zircon` | 锆石 Zircon | hypersonic | S2 ≈ | 下落条纹 |
| 26 | `oreshnik` | Oreshnik | hypersonic | —（不做实体精灵） | 多组发光再入体光点（剧情事件） |
| 27 | `fab250` | FAB‑250 无制导炸弹 | unguided_bomb | S1 | 小精灵（随载机投下，无尾迹） |
| 28 | `fab500` | FAB‑500 无制导炸弹 | unguided_bomb | S1 | 小精灵（无尾迹） |
| 29 | `fab250_umpk` | FAB‑250 UMPK | glide_bomb | S1 | 小精灵（无动力滑翔） |
| 30 | `fab500_umpk` | FAB‑500 UMPK | glide_bomb | S1 | 小精灵（无动力滑翔） |
| 31 | `fab1500_umpk` | FAB‑1500 UMPK | glide_bomb | S1 | 小精灵（无动力滑翔） |
| 32 | `fab3000_umpk` | FAB‑3000 UMPK | glide_bomb | S1（接近 S2）≈ | 小精灵（无动力滑翔） |
| 33 | `umpb_d30` | UMPB D‑30 | glide_bomb | S1 | 小精灵（无动力滑翔） |
| 34 | `umpb_5r` | UMPB‑5R 喷气滑翔弹 | glide_bomb | S1 | 小精灵 + 弱喷气尾迹 |
| 35 | `attack_helicopter` | 武装直升机（Ka‑52 / Mi‑28 / Mi‑24） | 直升机 | S4（含旋翼） | 完整精灵 + 旋翼动画 |
| 36 | `su25` | Su‑25 | 固定翼（强击机） | S4（接近 S3） | 完整精灵 |
| 37 | `su24m` | Su‑24M | 固定翼（前线轰炸机） | S4 | 完整精灵 |
| 38 | `su34` | Su‑34 | 固定翼（战斗轰炸机） | S4 | 完整精灵 |
| 39 | `su35s` | Su‑35S / Su‑30SM | 固定翼（战斗机） | S4 | 完整精灵（两型外形不同） |
| 40 | `tu22m3` | Tu‑22M3 | 固定翼（远程轰炸机） | S4 | 完整精灵（地图边缘） |
| 41 | `mig31k` | MiG‑31K | 固定翼（截击机 + 机腹挂弹） | S4 | 完整精灵 |
| 42 | `strategic_bomber` | 战略轰炸机（Tu‑95MS / Tu‑160） | 固定翼（战略轰炸机） | S4 | 不入图（`entersMap: false`） |
| 43 | `orion` | Orion 无人机 | 无人机平台（察打一体） | S2（翼展 S4） | 完整精灵 |
| 44 | `orlan_10` | Orlan‑10 / Zala | 无人机平台（侦察） | S1 | 小精灵 / 光点 |
| 45 | `a50u` | A‑50U 预警机 | 固定翼（预警机） | S4 | 完整精灵 |

---

## 一、弹药（`munitions.json`）

### 1.1 无人机类

### Gerbera 诱饵（`gerbera`）
- **类别**：一次性固定翼无人机（诱饵 / 侦察），空中目标，无地面底盘。
- **关键外形特征**：
  1. 截梢三角翼，整体轮廓与 Shahed‑136 相似但更小 [3]。
  2. 机体为胶合板骨架 + 聚苯乙烯泡沫外壳 [3]；公开残骸照片多为白色 / 浅色泡沫，表面可见胶带与拼缝 [44]。
  3. 尾部推进式螺旋桨，活塞发动机 [3]。
  4. 翼尖有垂直安定面 [44]。
- **组成**：单机；常与 Shahed 混编成群。
- **常见涂装**：未涂装的白 / 浅灰泡沫为主 [44]；是否有深色批次 ≈（未找到可靠来源）。
- **画面尺度提示**：S1（1–5 m）。
- **画面表现建议**：俯视轮廓 **三角翼**；尾迹 **活塞发动机，无明显尾迹**；声音：比 Shahed 更轻、更“塑料”的嗡嗡声，像小排量助动车（艺术化）。
- **参考图检索**：Commons [Category:Gerbera UAV](https://commons.wikimedia.org/wiki/Category:Gerbera_UAV)；维基 [Gerbera (drone)](https://en.wikipedia.org/wiki/Gerbera_(drone))。
- **注意**：AI 容易把它画成与 Shahed 一样的深色复合材料机体——应体现泡沫质感与更小的尺寸；与 Shahed 同屏时要能靠尺寸 / 颜色区分（玩法上它是诱饵）。

### Shahed‑136 / Geran‑2（`shahed_136`）
- **类别**：一次性固定翼攻击无人机。
- **关键外形特征**：
  1. 截梢三角翼，中央机身与机翼融合 [1]。
  2. 翼尖垂直安定面**上下双向延伸**（区别于小型 Shahed‑131 的只向上）[2]。
  3. 机身尾部活塞发动机驱动**双叶推进式螺旋桨** [1]。
  4. 机头圆钝，后期型号在机头加装摄像头 [1]。
  5. 俄方 Geran‑2 有俄式标记与涂装，部分涂黑用于夜间行动 [1]；时间表记为 2023 年下半年起黑色涂装 ≈ [43]。
- **组成**：单机；成群出现（典型夜袭数十至数百架）。
- **常见涂装**：早期浅灰 / 白色；2023 年起常见哑光黑 [1][43]；机身有西里尔字母型号 / 编号喷字（Geran‑4 残骸照片可见黄色“ГЕРАНЬ”喷字 [44]）。
- **画面尺度提示**：S1（1–5 m）。
- **画面表现建议**：俯视轮廓 **三角翼**；尾迹 **活塞发动机，无明显尾迹**（夜间几乎只能靠探照灯照亮或曳光弹勾勒）；声音：摩托车 / 助动车般持续的嗡嗡声，由远及近（媒体常见描述，未逐篇核对）。
- **参考图检索**：Commons [Category:Shahed 136](https://commons.wikimedia.org/wiki/Category:Shahed_136)、[Category:Geran-2](https://commons.wikimedia.org/wiki/Category:Geran-2)；维基 [HESA Shahed 136](https://en.wikipedia.org/wiki/HESA_Shahed_136)。
- **注意**：AI 常把螺旋桨画在机头（拉进式）或画成三叶 / 四叶——应为**尾部双叶推进式**；翼尖安定面上下都有；黑色涂装与早期浅色涂装按关卡年份选择（GDD 7.5）。

### Geran‑2 大战斗部型（`geran_2_heavy`）
- **类别**：同 `shahed_136`，改进型。
- **关键外形特征**：
  1. 总体外形与 Geran‑2 相同 [1]。
  2. 2025 年起部分批次在机头加装摄像头、后视摄像头等（时间表 [43]）；机头 / 机身局部改动肉眼远距离不可辨 ≈。
- **组成**：单机，混在 Geran‑2 群中。
- **常见涂装**：哑光黑为主 ≈ [1]。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **三角翼**；尾迹 **无明显尾迹**；声音：与 Geran‑2 相同的嗡嗡声。
- **参考图检索**：同 `shahed_136`（Commons 无单独分类）。
- **注意**：画面上与普通 Geran‑2 **无法靠外形区分**；建议靠指挥层符号 / 标签区分，或给精灵一个很小的机头摄像头凸起作为“彩蛋”而非识别手段（需人决定）。

### Geran‑3（`geran_3`）
- **类别**：一次性喷气式攻击无人机（伊朗 Shahed‑238 的俄方名称）[2]。
- **关键外形特征**：
  1. 截梢三角翼 + 翼尖安定面，总体轮廓沿用 Shahed‑136 [2][44]。
  2. 尾部为**涡喷发动机**而非螺旋桨 [2]；Shahed‑238 展示品可见尾部 / 机腹下方的发动机进气与喷口 ≈ [44]。
  3. 伊朗公开展示的三种型号均为黑色 [2]。
- **组成**：单机。
- **常见涂装**：黑色 [2][44]。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **三角翼**；尾迹 **喷气（小型涡喷，细短的热尾焰 / 热扭曲，夜间可见暗橙色小光点）**；声音：小型喷气机般的尖啸 / 呼啸，比 Shahed 高调且快速掠过（艺术化）。
- **参考图检索**：Commons [Category:Shahed 238](https://commons.wikimedia.org/wiki/Category:Shahed_238)（Commons 无“Geran-3”分类，API 确认不存在）；维基 [Shahed drones § Shahed 238 (Geran-3)](https://en.wikipedia.org/wiki/Shahed_drones)。
- **注意**：AI 会保留螺旋桨——必须删除；喷口位置以照片为准（≈）。

### Geran‑4（`geran_4`）
- **类别**：一次性喷气式攻击无人机，基于 Geran‑3 改进机体 [2]。
- **关键外形特征**：
  1. 基于 Geran‑3 设计，机体改进 [2]；具体外形差异公开资料有限 ≈。
  2. Commons “Geran-4” 分类中的 2026-10-01 基辅残骸照片：黑色碳纤维板、黄色“ГЕРАНЬ”喷字、圆柱形发动机段 [44]（该照片归类为 Geran‑4 由 Commons 编辑者判断，≈）。
- **组成**：单机。
- **常见涂装**：黑色 ≈ [44]。
- **画面尺度提示**：S1 ≈。
- **画面表现建议**：俯视轮廓 **三角翼 ≈**；尾迹 **喷气**；声音：同 Geran‑3 的喷气尖啸。
- **参考图检索**：Commons [Category:Geran-4](https://commons.wikimedia.org/wiki/Category:Geran-4)（只有残骸照片）；维基 [Shahed drones § Geran-4](https://en.wikipedia.org/wiki/Shahed_drones)。
- **注意**：缺少完整机体照片；建议画面上与 Geran‑3 共用精灵 + 换色 / 标签区分，待出现可靠完整照片后再修。

### Geran‑5（`geran_5`）
- **类别**：一次性喷气式攻击无人机，结构与早期 Geran 不同，**更接近巡航导弹** [2]。
- **关键外形特征**：
  1. 外形“更接近巡航导弹”（细长机身）[2]；具体翼型、尾翼布局、发动机位置 **未找到可核对的公开描述 ≈**。
  2. 不应沿用三角翼轮廓 ≈。
- **组成**：单机。
- **常见涂装**：未找到可靠来源 ≈。
- **画面尺度提示**：S1 ≈（未找到可靠尺寸来源，按“与 Geran 同级”暂定）。
- **画面表现建议**：俯视轮廓 **直翼 ≈（细长弹体 + 小翼，暂按巡航导弹式处理）**；尾迹 **喷气**；声音：更低沉连续的喷气轰鸣，像小号巡航导弹（艺术化）。
- **参考图检索**：Commons **无对应分类**（API 确认 “Category:Geran-5” 不存在）；维基 [Shahed drones § Geran-5](https://en.wikipedia.org/wiki/Shahed_drones)（引用 FT 2026-09-13 报道，付费墙，未打开）。
- **注意**：**本条外形几乎全部待人工核对**，建议 WS03-006 单独检索公开照片后再定精灵。

### Lancet（`lancet`）
- **类别**：巡飞弹（小型固定翼），由弹射架发射。
- **关键外形特征**：
  1. 两组**前后串列的 X 形（十字形）翼**，俯视呈前后两个“×” ≈（取自维基条目与公开照片的一般描述，Commons 分类以视频截图为主，本次未取得清晰静态图核对）[4]。
  2. 细长圆柱形机身，尾部螺旋桨，电动机驱动 [4]。
  3. 机头有光学 / 摄像头窗口 ≈。
- **组成**：单弹；画面上可配一个小型操作组（不入图）。
- **常见涂装**：浅灰 / 灰白 ≈。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **X 形串列翼（介于直翼与无翼之间，俯视像两个叉号）**；尾迹 **电动，无尾迹**；声音：几乎无声，末段俯冲时短促的风啸 / 高频电机声（艺术化）。
- **参考图检索**：Commons [Category:ZALA Lancet](https://commons.wikimedia.org/wiki/Category:ZALA_Lancet)（多为俄方视频）；维基 [ZALA Lancet](https://en.wikipedia.org/wiki/ZALA_Lancet)。
- **注意**：AI 常画成普通直翼小飞机——必须是前后两组 X 形翼；Lancet‑1 / ‑3 及“产品 53”外形有差异，以照片为准。

### 光纤 FPV（`fpv_fiber`）
- **类别**：多旋翼 FPV 攻击无人机（光纤线控）。
- **关键外形特征**：
  1. 四旋翼（少数为更多旋翼）裸露机架，体积小 [5]。
  2. 机身下 / 后方挂一个**光纤线轴（卷筒）**，飞行时身后放出极细光纤 [5]。
  3. 弹药捆扎在机架下方。
- **组成**：单机。
- **常见涂装**：碳纤维黑 / 杂色，无统一涂装。
- **画面尺度提示**：S0（< 1 m）。
- **画面表现建议**：俯视轮廓 **多旋翼（四个圆形桨盘）**；尾迹 **无发动机尾迹**；可选：近距离时画一条闪烁的极细“光纤线”拖在身后（战场上光纤残留在树木、田野中的画面在公开报道中常见 [5]）；声音：蚊子般尖细的高频嗡鸣。
- **参考图检索**：Commons [Category:Combat FPV drones](https://commons.wikimedia.org/wiki/Category:Combat_FPV_drones)（通用；Commons 无“光纤无人机”专门分类，API 确认 “Category:Fiber optic drones” 不存在）；维基 [Fiber optic drone](https://en.wikipedia.org/wiki/Fiber_optic_drone)。
- **注意**：与无线电 FPV 外形几乎一样，**区别只在线轴**；无天线 / 天线很少。

### 无线电 FPV（`fpv_radio`）
- **类别**：多旋翼 FPV 攻击无人机（无线电控制）。
- **关键外形特征**：
  1. 四旋翼裸露机架，相机朝前。
  2. 机尾有 1–2 根短天线 ≈。
  3. 弹药捆扎在机架下方。
- **组成**：单机。
- **常见涂装**：无统一涂装。
- **画面尺度提示**：S0。
- **画面表现建议**：俯视轮廓 **多旋翼**；尾迹 **无**；声音：蚊子般尖细的高频嗡鸣（与光纤 FPV 相同）。
- **参考图检索**：Commons [Category:Combat FPV drones](https://commons.wikimedia.org/wiki/Category:Combat_FPV_drones)；维基 [First-person view (remote control)](https://en.wikipedia.org/wiki/First-person_view_(remote_control))（`FPV drone` 重定向至此）。
- **注意**：在实景层基本只是光点，不值得投入建模精度；重点在指挥层符号。

### Molniya（`molniya`）
- **类别**：廉价固定翼 FPV 攻击 / 侦察无人机 [6]。
- **关键外形特征**：
  1. 胶合板、泡沫、塑料、铝制成 [6]，外观粗糙，可见胶带 [44]。
  2. 博物馆展品（Molniya‑2）：**圆筒形机身 + 上单直翼 + 尾部平尾与小垂尾** [44]。
  3. 弹药直接捆绑或用支架固定在机身 / 机翼挂点上 [6]。
- **组成**：单机。
- **常见涂装**：灰色 / 未涂装 [44]。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **直翼**；尾迹 **无明显尾迹**（动力形式未核实 ≈）；声音：航模般的高频嗡嗡声（艺术化）。
- **参考图检索**：Commons [Category:Molniya-2 (drone)](https://commons.wikimedia.org/wiki/Category:Molniya-2_(drone))、[Category:Molniya-1 (drone)](https://commons.wikimedia.org/wiki/Category:Molniya-1_(drone))；维基 [Molniya (drone)](https://en.wikipedia.org/wiki/Molniya_(drone))。
- **注意**：AI 容易画得太精致——实物是简易手工质感；不同批次布局有差异。

### 1.2 巡航导弹类

### Kh‑101 / Kh‑555（`kh101`）
- **类别**：空射巡航导弹，由 Tu‑95MS 翼下挂架或 Tu‑160 弹舱发射 [7]。
- **关键外形特征**：
  1. **Kh‑101**：放弃 Kh‑55 的圆截面，机头与前机身为能产生升力的扁平 / 多棱面外形 [7]。
  2. 发射后展开的弹翼与尾翼 [7]；发动机位于后机身下方（发射后伸出的短舱）≈ [7][8]。
  3. **Kh‑555**：Kh‑55 系列的常规型，**圆截面细长弹体** [8]，与 Kh‑101 外形明显不同。
- **组成**：单弹；载机 Tu‑95MS 每机可在翼下挂 8 枚 [7]（载机不入图，见 `strategic_bomber`）。
- **常见涂装**：灰 / 白色调 ≈（夜间不可辨）。
- **画面尺度提示**：S2（5–10 m）。
- **画面表现建议**：俯视轮廓 **直翼（弹翼展开后，细长弹体 + 一对小翼）**；尾迹 **喷气（涡扇，暗淡，夜间几乎看不到光，只有极弱热光点）**；声音：低空掠过的喷气轰鸣，像一架远处的小飞机，有明显多普勒变调（艺术化）。
- **参考图检索**：Commons [Category:Raduga Kh-101](https://commons.wikimedia.org/wiki/Category:Raduga_Kh-101)、[Category:Raduga Kh-55](https://commons.wikimedia.org/wiki/Category:Raduga_Kh-55)（Kh‑555 无单独分类，API 确认 “Category:Kh-555” 不存在）；维基 [Kh-101](https://en.wikipedia.org/wiki/Kh-101)、[Kh-55](https://en.wikipedia.org/wiki/Kh-55)。
- **注意**：一个数据条目对应两种外形不同的导弹（见“与现有文档的差异”）；AI 常画成圆截面 + 机头进气道——Kh‑101 无机头进气道。

### 口径 Kalibr（`kalibr`）
- **类别**：海基 / 潜射巡航导弹（舰艇垂直发射）[9]。
- **关键外形特征**：
  1. 圆柱形细长弹体，发射后展开一对小弹翼与十字形尾翼 ≈ [9]。
  2. 发射段从舰艇 / 潜艇垂直升起，带固体助推器的亮尾焰与烟柱 ≈ [9]。
  3. 巡航段机腹进气口伸出 ≈。
- **组成**：单弹；发射平台（舰艇）通常在地图外。
- **常见涂装**：灰 / 白 ≈。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **直翼**；尾迹 **喷气（巡航段暗淡）**，若做发射画面则为**火箭亮尾焰 + 白色烟柱**；声音：同 Kh‑101 的低空喷气轰鸣。
- **参考图检索**：Commons [Category:3M-54 Klub](https://commons.wikimedia.org/wiki/Category:3M-54_Klub)（出口型 Klub，与 Kalibr 同系列；Commons 无 “3M-54 Kalibr” / “Kalibr (missile family)” 分类，API 确认）；维基 [Kalibr (missile family)](https://en.wikipedia.org/wiki/Kalibr_(missile_family))。
- **注意**：Kalibr 家族包括反舰、对地、反潜等多种外形，对地型（3M14）为本条参考；不要用出口展品的涂装直接当实战涂装。

### 伊斯坎德尔‑K（`iskander_k`）
- **类别**：陆基巡航导弹，由伊斯坎德尔系统的轮式发射车发射 [10]。
- **关键外形特征**：
  1. 圆柱形细长弹体 + 发射后展开的小弹翼 ≈ [10]。
  2. 发射车为多轴轮式底盘（与伊斯坎德尔‑M 同系列）[10]，通常不入图。
- **组成**：单弹。
- **常见涂装**：军绿 / 灰 ≈。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **直翼**；尾迹 **喷气（暗淡）**；声音：低空喷气轰鸣。
- **参考图检索**：Commons [Category:9K720 Iskander](https://commons.wikimedia.org/wiki/Category:9K720_Iskander)、[Category:9M728](https://commons.wikimedia.org/wiki/Category:9M728)（9M728 为伊斯坎德尔‑K 所用巡航导弹的型号之一 ≈）；维基 [9K720 Iskander](https://en.wikipedia.org/wiki/9K720_Iskander)。
- **注意**：画面上与 Kalibr / Kh‑101 几乎无差别，建议共用“巡航导弹”精灵族，靠符号区分。

### Kh‑59 / Kh‑69（`kh59`）
- **类别**：空射巡航导弹，由 Su‑24M / Su‑34 等挂载 [11][12]。
- **关键外形特征**：
  1. **Kh‑59**：机头附近有可展开的前翼，尾部有弹翼与舵面；尾部有固体助推器 [11]。
  2. **Kh‑59M 系列**：弹体下方、后翼前方外挂一个涡扇发动机短舱（明显的机腹“吊舱”）[11]。
  3. **Kh‑69**：隐身外形，外观类似“风暴之影 / 金牛座”导弹 [12]；扁平弹体，发射后展开弹翼与尾部四片舵面 [12]。
- **组成**：单弹，由载机发射。
- **常见涂装**：灰 / 白 ≈。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **直翼**（Kh‑59 俯视可见前后两组翼面）；尾迹 **喷气（暗淡）**，Kh‑59 发射后一小段有助推器亮尾焰 [11]；声音：低空喷气轰鸣。
- **参考图检索**：Commons [Category:Raduga Kh-59](https://commons.wikimedia.org/wiki/Category:Raduga_Kh-59)、[Category:Raduga Kh-69](https://commons.wikimedia.org/wiki/Category:Raduga_Kh-69)；维基 [Kh-59](https://en.wikipedia.org/wiki/Kh-59)、[Kh-69](https://en.wikipedia.org/wiki/Kh-69)。
- **注意**：一个条目两种外形（见差异节）；Kh‑59M 的机腹发动机吊舱是最容易漏掉的特征。

### S8000 Banderol（`banderol`）
- **类别**：小型巡航导弹，由 Orion 无人机或 Mi‑28N 挂载发射 [13][43]。
- **关键外形特征**：
  1. 小型喷气推进巡航导弹（小型涡喷）[13]；外形公开资料少 ≈。
  2. 细长弹体 + 展开式弹翼 ≈（参考 TWZ 报道中的缴获残骸照片 [45]，未打开核对）。
- **组成**：单弹，挂在 Orion 翼下。
- **常见涂装**：未找到可靠来源 ≈。
- **画面尺度提示**：S1 ≈。
- **画面表现建议**：俯视轮廓 **直翼 ≈**；尾迹 **喷气（很弱）**；声音：比大型巡航导弹更尖细的小型喷气声（艺术化）。
- **参考图检索**：Commons **无对应分类**（API 确认 “Category:S8000 Banderol” 不存在）；维基 [S8000 Banderol](https://en.wikipedia.org/wiki/S8000_Banderol)；TWZ 报道见来源 [45]。
- **注意**：外形待人工核对；体积应明显小于 Kh‑101。

### 1.3 超音速 / 反辐射导弹类

### Oniks（`oniks`）
- **类别**：超音速反舰 / 对地导弹，由“棱堡”岸防系统发射车（多轴轮式，竖起的发射筒）发射 [14]。
- **关键外形特征**：
  1. 圆柱形弹体，**机头为环形进气口 + 中心锥** ≈ [14]。
  2. 弹体中部一对小梯形弹翼、尾部十字形尾翼 ≈ [14]。
- **组成**：单弹；发射车通常在地图外。
- **常见涂装**：灰 / 白 ≈。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **无翼（小翼，近似细长圆柱）**；尾迹 **喷气（冲压，速度快，尾迹短而直）**，发射段有火箭助推亮尾焰；声音：撕裂空气的音爆声，紧接爆炸（艺术化）。
- **参考图检索**：Commons [Category:P-800 Oniks](https://commons.wikimedia.org/wiki/Category:P-800_Oniks)；维基 [P-800 Oniks](https://en.wikipedia.org/wiki/P-800_Oniks)。
- **注意**：AI 常画出亚音速巡航导弹式的大弹翼——Oniks 的弹翼很小。

### Kh‑22（`kh22`）
- **类别**：大型空射超音速导弹，由 Tu‑22M3 机腹 / 翼下挂载 [15]。
- **关键外形特征**：
  1. 体积很大的细长弹体，尖锐机头 [15]。
  2. 弹体中部一对**小三角翼** ≈ [15]。
  3. 尾部十字形尾翼，其中**腹鳍在挂机时折叠**、发射后展开 ≈ [15]。
- **组成**：单弹，载机 `tu22m3`。
- **常见涂装**：浅灰 / 白 ≈。
- **画面尺度提示**：S3（10–15 m）。
- **画面表现建议**：俯视轮廓 **三角翼（小）**；尾迹 **火箭亮尾焰**（液体火箭发动机）[15]，高空俯冲段可做成从画面外落下的亮条纹；声音：高空传来的雷鸣般轰响 + 音爆（艺术化）。
- **参考图检索**：Commons [Category:Raduga Kh-22](https://commons.wikimedia.org/wiki/Category:Raduga_Kh-22)；维基 [Kh-22](https://en.wikipedia.org/wiki/Kh-22)。
- **注意**：比 Kh‑101 大得多，精灵尺寸要体现；数据中 `altitudeBand: high_dive`，表现上以“高空俯冲”为主。

### Kh‑32（`kh32`）
- **类别**：Kh‑22 的改进型空射超音速导弹，由 Tu‑22M3 挂载 [16]。
- **关键外形特征**：
  1. 外形与 Kh‑22 基本相同 ≈ [16]（公开照片很少）。
- **组成**：单弹。
- **常见涂装**：未找到可靠来源 ≈。
- **画面尺度提示**：S3。
- **画面表现建议**：俯视轮廓 **三角翼（小）**；尾迹 **火箭亮尾焰**；声音：同 Kh‑22。
- **参考图检索**：Commons **无对应分类**（API 确认 “Category:Kh-32” 与 “Category:Raduga Kh-32” 均不存在，可用 Kh‑22 分类代替）；维基 [Kh-32](https://en.wikipedia.org/wiki/Kh-32)。
- **注意**：建议与 Kh‑22 共用精灵。

### Kh‑31P 反辐射导弹（`kh31p`）
- **类别**：空射反辐射导弹，由 Su‑35S / Su‑34 等挂载。
- **关键外形特征**：
  1. 常规布局，**十字形弹翼与舵面** [17]。
  2. 弹体周围有**四个进气道**（冲压发动机），是最显著的识别特征 ≈ [17]。
  3. 发射时尾部固体助推器点火 [17]。
- **组成**：单弹。
- **常见涂装**：灰 ≈。
- **画面尺度提示**：S1–S2 边界（约 5 m 上下，≈）。
- **画面表现建议**：俯视轮廓 **无翼（十字形小翼）**；尾迹 **先短促火箭亮尾焰，后转为细喷气尾迹**；声音：尖锐的呼啸，快速逼近（艺术化）。
- **参考图检索**：Commons [Category:Zvezda Kh-31](https://commons.wikimedia.org/wiki/Category:Zvezda_Kh-31)（无 Kh‑31P 单独分类，API 确认）；维基 [Kh-31](https://en.wikipedia.org/wiki/Kh-31)。
- **注意**：四个进气道常被 AI 画成四片翼；P 型与 A 型 / 加长型（PD）外形长度略有差异 [17]。

### 1.4 弹道 / 高超音速类

> 弹道类在 GDD 16.1 中“从画面外高速落下”；以下“俯视轮廓”只在拉近或发射画面时有意义，实景层主要是**下落条纹**。

### S‑300 对地（`s300_ground`）
- **类别**：S‑300 防空导弹改作对地使用；发射自 S‑300 系统的轮式发射车（竖起的发射筒）[18]。
- **关键外形特征**：
  1. 细长圆柱弹体，尾部四片小舵面 ≈ [18]。
  2. 从发射筒垂直冷发射后点火 ≈ [18]。
- **组成**：单弹（发射车在地图外）。
- **常见涂装**：灰 / 军绿 ≈。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **无翼**；尾迹 **火箭亮尾焰（上升段），下落段为高速亮条纹**；声音：几乎没有预兆，落地前一瞬的尖啸 + 爆炸（艺术化）。
- **参考图检索**：Commons [Category:S-300](https://commons.wikimedia.org/wiki/Category:S-300)（导弹型号 5V55 无单独分类，API 确认）；维基 [S-300 missile system](https://en.wikipedia.org/wiki/S-300_missile_system)。
- **注意**：与我方 S‑300（玩家单位）是同一外形的导弹，敌我区分靠颜色 / 符号（03.A：敌方红橙）。

### KN‑23（`kn23`）
- **类别**：朝鲜短程弹道导弹 [19]。
- **关键外形特征**：
  1. 外形类似伊斯坎德尔‑M，飞行方式也相似 [19]。
  2. 尾部有可动尾翼 [19]。
  3. 弹体涂成军绿色 [19]。
- **组成**：单弹（发射车在地图外）。
- **常见涂装**：军绿 [19]。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **无翼**；尾迹 **下落亮条纹**；声音：同伊斯坎德尔‑M。
- **参考图检索**：Commons [Category:KN-23](https://commons.wikimedia.org/wiki/Category:KN-23)；维基 [Hwasong-11A](https://en.wikipedia.org/wiki/Hwasong-11A)（`KN-23` 重定向至此）。
- **注意**：与伊斯坎德尔‑M 可共用精灵；弹体比伊斯坎德尔略粗 ≈。

### 伊斯坎德尔‑M（`iskander_m`）
- **类别**：短程弹道导弹，发射车为多轴轮式底盘、每车两枚 ≈ [10]。
- **关键外形特征**：
  1. 光滑圆柱弹体、尖锥形头部 ≈ [10]。
  2. 尾部小型尾翼 ≈ [10]。
- **组成**：单弹（发射车在地图外）。
- **常见涂装**：军绿 ≈ [10]。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **无翼**；尾迹 **下落亮条纹（末段几乎垂直）**；声音：往往在警报响起前就已落地——一声尖锐呼啸后爆炸（艺术化）。
- **参考图检索**：Commons [Category:9K720 Iskander](https://commons.wikimedia.org/wiki/Category:9K720_Iskander)、[Category:9M723](https://commons.wikimedia.org/wiki/Category:9M723)；维基 [9K720 Iskander](https://en.wikipedia.org/wiki/9K720_Iskander)。
- **注意**：AI 常画成大尾翼的“二战火箭”——尾翼应很小。

### 伊斯坎德尔‑M 改（`iskander_m_mod`）
- **类别**：同 `iskander_m`，2025 年改进型（时间表 [43]）。
- **关键外形特征**：
  1. 外形与伊斯坎德尔‑M 无公开可辨差异 ≈。
- **组成**：单弹。
- **常见涂装**：同上 ≈。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **无翼**；尾迹 **下落亮条纹，末段可加轻微横向摆动**（对应数据 `terminal_maneuver`，属玩法表现）；声音：同伊斯坎德尔‑M。
- **参考图检索**：同 `iskander_m`。
- **注意**：靠尾迹轨迹而非外形区分。

### 匕首 Kinzhal（`kinzhal`）
- **类别**：空射弹道导弹，挂在 MiG‑31K 机腹中线 [20]。
- **关键外形特征**：
  1. 设计据报基于伊斯坎德尔导弹 [20]，弹体外形相近。
  2. 挂机时尾部装有整流罩（保护尾喷口），发射后脱落 ≈ [20]。
  3. 挂在 MiG‑31K 机腹时非常醒目（大型单枚外挂）≈。
- **组成**：单弹，载机 `mig31k`。
- **常见涂装**：灰 / 白 ≈。
- **画面尺度提示**：S2。
- **画面表现建议**：俯视轮廓 **无翼**；尾迹 **火箭亮尾焰（脱离载机后），终段为高速下落亮条纹**；声音：短促的音爆后立即爆炸（艺术化）。
- **参考图检索**：Commons [Category:Kh-47M2 Kinzhal](https://commons.wikimedia.org/wiki/Category:Kh-47M2_Kinzhal)；维基 [Kh-47M2 Kinzhal](https://en.wikipedia.org/wiki/Kh-47M2_Kinzhal)。
- **注意**：尾部整流罩是 Kinzhal 与伊斯坎德尔的主要可见区别 ≈；建议在 MiG‑31K 精灵上体现挂弹状态。

### 锆石 Zircon（`zircon`）
- **类别**：高超音速导弹，舰射 / 陆基发射 [21]。
- **关键外形特征**：
  1. **未找到可清晰辨认外形的公开实弹照片 ≈** [21]。
- **组成**：单弹。
- **常见涂装**：未找到可靠来源 ≈。
- **画面尺度提示**：S2 ≈。
- **画面表现建议**：俯视轮廓 **无翼 ≈**；尾迹 **高空俯冲的高速亮条纹（艺术化）**；声音：同 Kinzhal 的音爆 + 爆炸（艺术化）。
- **参考图检索**：Commons [Category:Zircon (hypersonic weapon)](https://commons.wikimedia.org/wiki/Category:Zircon_(hypersonic_weapon))（“3M22 Zircon” 分类不存在，API 确认）；维基 [3M22 Zircon](https://en.wikipedia.org/wiki/3M22_Zircon)。
- **注意**：不建议建模，仅做光点 / 条纹，避免“编造外形”。

### Oreshnik（`oreshnik`）
- **类别**：中程弹道导弹，剧情事件（数据中不可拦截）。
- **关键外形特征（只写公开报道中可见的画面）**：
  1. 2024-11-21 第聂伯罗打击的公开夜间视频中，可见**多组发光物体接连从夜空落下**；维基图注描述为“六个弹头之一的六个子弹药落在第聂伯罗” [22]。
  2. 公开报道称其携带多弹头，共六个弹头 [22]。
  3. 后续 2026-01-08 利沃夫、2026-05-24 比拉采尔克瓦的打击见 [22]（未找到更多公开视频画面描述）。
- **组成**：画面上表现为**一组组连续落下的亮点**，而非导弹本体。
- **常见涂装**：不适用。
- **画面尺度提示**：不做实体精灵。
- **画面表现建议**：俯视轮廓 **不适用（无可见本体）**；尾迹 **多个发光再入体：6 组 × 每组数个亮点，几乎垂直、成串地落下，每个亮点带短而亮的白色 / 橙白色拖尾**；声音：落地前几乎无声，随后一连串极快的沉闷撞击声（艺术化）。
- **参考图检索**：Commons [Category:Oreshnik (missile)](https://commons.wikimedia.org/wiki/Category:Oreshnik_(missile))、[Category:Oreshnik](https://commons.wikimedia.org/wiki/Category:Oreshnik)；维基 [Oreshnik (missile)](https://en.wikipedia.org/wiki/Oreshnik_(missile))。
- **注意**：不要建模导弹或再入体外形；这是剧情事件，画面应克制，不做成“奇观奖励”（GDD 17 第 1 条）。

### 1.5 炸弹类

### FAB‑250 无制导炸弹（`fab250`）
- **类别**：无制导航空炸弹，由 Su‑25 / Su‑24M 等投放 [23]。
- **关键外形特征**：
  1. 圆柱形弹体、卵形头部 [23]。
  2. 尾部**箱形 / 环形尾翼** ≈ [23]（M‑54 / M‑62 等型号尾翼形状不同）。
- **组成**：单弹，从载机投下。
- **常见涂装**：灰 / 军绿 ≈。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **无翼（尾部方框）**；尾迹 **无动力，无尾迹**；声音：载机低空呼啸掠过后，炸弹下落的尖哨声（艺术化）。
- **参考图检索**：Commons [Category:FAB-250](https://commons.wikimedia.org/wiki/Category:FAB-250)；维基 [FAB-250](https://en.wikipedia.org/wiki/FAB-250)。
- **注意**：在实景层只在下落的几秒内可见；重点是载机精灵。

### FAB‑500 无制导炸弹（`fab500`）
- **类别**：同上 [24]。
- **关键外形特征**：
  1. 外形同 FAB‑250 系列，尺寸更大 [24]。
  2. 尾部箱形尾翼 ≈ [24]。
- **组成**：单弹。
- **常见涂装**：灰 / 军绿 ≈。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **无翼**；尾迹 **无**；声音：同 FAB‑250，更沉。
- **参考图检索**：Commons [Category:FAB-500](https://commons.wikimedia.org/wiki/Category:FAB-500)；维基 [FAB-500](https://en.wikipedia.org/wiki/FAB-500)。
- **注意**：与 FAB‑250 共用精灵，按比例放大即可。

### FAB‑250 UMPK（`fab250_umpk`）
- **类别**：加装 UMPK 滑翔制导套件的炸弹，由 Su‑34 等投放 [26]。
- **关键外形特征**：
  1. 普通 FAB 炸弹弹体 + **背部加装一对可展开的长直翼**，投弹后由弹簧机构展开 [26]。
  2. 尾部换装**十字形（X 形）控制舵面**的尾段 [26]。
  3. 焊接结构，外观粗犷，可见套件与弹体的分界 [26]。
- **组成**：单弹。
- **常见涂装**：弹体原色（灰 / 军绿）+ 套件原色 ≈。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **直翼（展开后机翼很长，与弹体呈“十”字）**；尾迹 **无动力滑翔，无尾迹**；声音：几乎听不到接近，只有落地前的风哨与巨大爆炸（艺术化）。
- **参考图检索**：Commons [Category:UMPK (bomb kit)](https://commons.wikimedia.org/wiki/Category:UMPK_(bomb_kit))；维基 [UMPK (bomb kit)](https://en.wikipedia.org/wiki/UMPK_(bomb_kit))。
- **注意**：AI 常把机翼画成后掠 / 三角——UMPK 为直翼，位于弹体上方。

### FAB‑500 UMPK（`fab500_umpk`）
- **类别 / 关键外形 / 组成 / 涂装**：同 `fab250_umpk`，弹体为 FAB‑500 [26]。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **直翼**；尾迹 **无动力滑翔**；声音：同上。
- **参考图检索**：同 `fab250_umpk`；另见 Commons [Category:FAB-500](https://commons.wikimedia.org/wiki/Category:FAB-500)。
- **注意**：共用 UMPK 精灵，按弹体比例放大。

### FAB‑1500 UMPK（`fab1500_umpk`）
- **类别 / 关键外形**：FAB‑1500 弹体 + UMPK 套件 [25][26]；弹体明显更粗大；部分老型号 FAB‑1500 头部附近有一圈弹道环 ≈ [25]。
- **组成 / 涂装**：同上。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **直翼**；尾迹 **无动力滑翔**；声音：同上，爆炸更沉重。
- **参考图检索**：Commons [Category:FAB-1500](https://commons.wikimedia.org/wiki/Category:FAB-1500)、[Category:UMPK (bomb kit)](https://commons.wikimedia.org/wiki/Category:UMPK_(bomb_kit))；维基 [General-purpose bomb § Soviet and Russian](https://en.wikipedia.org/wiki/General-purpose_bomb)（`FAB-1500` 重定向至此）。
- **注意**：弹体粗细比例要和 FAB‑250 明显拉开。

### FAB‑3000 UMPK（`fab3000_umpk`）
- **类别 / 关键外形**：FAB‑3000 弹体 + UMPK 套件 [25][26]；本系列最大的弹体。
- **组成 / 涂装**：同上。
- **画面尺度提示**：S1（接近 S2）≈。
- **画面表现建议**：俯视轮廓 **直翼**；尾迹 **无动力滑翔**；声音：同上。
- **参考图检索**：Commons [Category:FAB-3000](https://commons.wikimedia.org/wiki/Category:FAB-3000)；维基 [General-purpose bomb](https://en.wikipedia.org/wiki/General-purpose_bomb)。
- **注意**：数据标记 `rare`，可在精灵上略作夸张以便识别（需人决定）。

### UMPB D‑30（`umpb_d30`）
- **类别**：一体化滑翔炸弹，可空投，也可由火箭炮发射（时间表 [43]）[27]。
- **关键外形特征**：
  1. 流线型弹体，比 UMPK 更“干净” [27]。
  2. **折叠弹翼**，发射前贴合弹体，发射后展开 [27]。
  3. 尾部十字形尾翼 [27]。
- **组成**：单弹。
- **常见涂装**：未找到可靠来源 ≈。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **直翼**；尾迹 **无动力滑翔**（地射型发射段有火箭亮尾焰 ≈）；声音：轻微风哨 + 爆炸（艺术化）。
- **参考图检索**：Commons **无对应分类**（API 确认 “Category:UMPB D-30SN” 不存在）；维基 [UMPB D-30SN](https://en.wikipedia.org/wiki/UMPB_D-30SN)（该条目带“来源不可靠”提示）。
- **注意**：与 UMPK 区分：UMPB 是一体化细长弹体，UMPK 是“普通炸弹 + 外挂套件”。

### UMPB‑5R 喷气滑翔弹（`umpb_5r`）
- **类别**：带喷气发动机的滑翔弹 [26][46]。
- **关键外形特征**：
  1. 基于 FAB‑250 的制导滑翔套件，内部有喷气发动机与燃料箱 [26]。
  2. X 形控制舵面，尾部有发动机喷口 [26]。
- **组成**：单弹。
- **常见涂装**：未找到可靠来源 ≈。
- **画面尺度提示**：S1。
- **画面表现建议**：俯视轮廓 **直翼 ≈**；尾迹 **喷气（细弱）**；声音：轻微喷气嗡鸣，比普通滑翔弹多一点“发动机声”（艺术化）。
- **参考图检索**：Commons 无对应分类（未找到）；维基 [UMPK (bomb kit)](https://en.wikipedia.org/wiki/UMPK_(bomb_kit))（含 UMPB 喷气型残骸描述）。
- **注意**：维基条目中 UMPB 喷气型与“UMPK 增程型”的命名有混用，时间表也注明含“UMPK 增程型” [43]；外形待人工核对。

---

## 二、平台（`platforms.json`）

> 平台进入地图（`strategic_bomber` 除外），需要 16 方向完整精灵。按要求不写航程、速度、载弹量等参数；声音特征一并给出供 WS08 参考。

### 武装直升机（Ka‑52 / Mi‑28 / Mi‑24）（`attack_helicopter`）
- **类别**：武装直升机（三型合并为一个数据条目）。
- **关键外形特征**：
  - **Ka‑52**：**共轴双旋翼**（上下两副旋翼），**无尾桨**；并列双座座舱；短翼挂架；机头有雷达 / 光电球 [28]。
  - **Mi‑28**：**纵列阶梯式双座座舱**；单旋翼 + **X 形（剪刀式）尾桨**；机头下方有机炮；短翼挂架 [29]。
  - **Mi‑24**：纵列双座气泡式座舱；机身后部有运兵舱，机身较粗壮；短翼明显**下反**、带挂架；单旋翼 + 常规尾桨 [30]。
- **组成**：通常 2 机编队 ≈。
- **常见涂装**：深灰、橄榄绿或绿褐迷彩 [28][29][30]；2022 年战争初期俄方飞机 / 直升机常见白色“Z”“V”战术标记 ≈（是否在游戏中出现需人决定，见文末）。
- **画面尺度提示**：S4（含旋翼）。
- **参考图检索**：Commons [Category:Kamov Ka-52](https://commons.wikimedia.org/wiki/Category:Kamov_Ka-52)、[Category:Kamov Ka-52 in Ukraine](https://commons.wikimedia.org/wiki/Category:Kamov_Ka-52_in_Ukraine)、[Category:Mil Mi-28](https://commons.wikimedia.org/wiki/Category:Mil_Mi-28)、[Category:Mil Mi-28N](https://commons.wikimedia.org/wiki/Category:Mil_Mi-28N)、[Category:Mil Mi-24](https://commons.wikimedia.org/wiki/Category:Mil_Mi-24)、[Category:Mil Mi-24 in Ukraine](https://commons.wikimedia.org/wiki/Category:Mil_Mi-24_in_Ukraine)、[Category:Mil Mi-35M](https://commons.wikimedia.org/wiki/Category:Mil_Mi-35M)；维基 [Kamov Ka-52](https://en.wikipedia.org/wiki/Kamov_Ka-52)（重定向至 Ka‑50 条目）、[Mil Mi-28](https://en.wikipedia.org/wiki/Mil_Mi-28)、[Mil Mi-24](https://en.wikipedia.org/wiki/Mil_Mi-24)。
- **画面表现建议**：俯视下最大识别要素是**旋翼盘**：Ka‑52 画成两副叠放的旋翼盘且无尾桨；Mi‑28 / Mi‑24 为单旋翼 + 尾桨。声音：Ka‑52 共轴旋翼特有的双重“拍击”声；Mi‑24 / Mi‑28 为低沉有节奏的旋翼轰鸣（艺术化）。
- **注意**：AI 最常见的错误是给 Ka‑52 加尾桨、给 Mi‑28 画常规尾桨；建议做 3 套精灵或选一型代表（需人决定）。

### Su‑25（`su25`）
- **类别**：强击机（固定翼）。
- **关键外形特征**：
  1. 肩置平直略后掠的梯形机翼，翼下大量挂架 [31]。
  2. 双发，发动机舱紧贴机身两侧 [31]。
  3. **翼尖吊舱**（后端可上下张开的减速板）[31]。
  4. 单垂尾，座舱盖较小、机头较尖 [31]。
- **组成**：通常 2 机编队 ≈。
- **常见涂装**：绿褐迷彩或灰色（如 Su‑25SM 系列）≈ [31]。
- **画面尺度提示**：S4（接近 S3 上限）。
- **参考图检索**：Commons [Category:Sukhoi Su-25](https://commons.wikimedia.org/wiki/Category:Sukhoi_Su-25)、[Category:Sukhoi Su-25SM](https://commons.wikimedia.org/wiki/Category:Sukhoi_Su-25SM)；维基 [Sukhoi Su-25](https://en.wikipedia.org/wiki/Sukhoi_Su-25)。
- **画面表现建议**：低空、大量释放热诱饵弹（亮点散射）是公开视频中的常见画面 ≈；声音：低空掠过的双发轰鸣（艺术化）。
- **注意**：翼尖吊舱常被 AI 省略或画成导弹。

### Su‑24M（`su24m`）
- **类别**：前线轰炸机（固定翼，可变后掠翼）。
- **关键外形特征**：
  1. **可变后掠肩翼**（低速展开、高速后掠）[32]。
  2. **并列双座**座舱，机头宽钝 [32]。
  3. 矩形侧进气道，双发，单个大垂尾 [32]。
- **组成**：通常 2 机编队 ≈。
- **常见涂装**：灰色或迷彩 ≈ [32]。
- **画面尺度提示**：S4。
- **参考图检索**：Commons [Category:Sukhoi Su-24M](https://commons.wikimedia.org/wiki/Category:Sukhoi_Su-24M)、[Category:Sukhoi Su-24](https://commons.wikimedia.org/wiki/Category:Sukhoi_Su-24)；维基 [Sukhoi Su-24](https://en.wikipedia.org/wiki/Sukhoi_Su-24)。
- **画面表现建议**：建议精灵固定为中等后掠角，或做展开 / 后掠两态（需人决定）；声音：双发喷气轰鸣（艺术化）。
- **注意**：AI 易与 Tu‑22M 混淆（同为变后掠翼），Su‑24 体积小得多、单垂尾较短。

### Su‑34（`su34`）
- **类别**：战斗轰炸机（侧卫家族）。
- **关键外形特征**：
  1. **扁平宽大的“鸭嘴”机头**，并列双座 [33]。
  2. 机头两侧小鸭翼 [33]。
  3. 双垂尾、双发、两发之间加长的尾锥 [33]。
- **组成**：通常 2 机编队 ≈。
- **常见涂装**：蓝灰双色海洋式迷彩 ≈ [33]。
- **画面尺度提示**：S4。
- **参考图检索**：Commons [Category:Sukhoi Su-34](https://commons.wikimedia.org/wiki/Category:Sukhoi_Su-34)、[Category:Sukhoi Su-34 in Ukraine](https://commons.wikimedia.org/wiki/Category:Sukhoi_Su-34_in_Ukraine)；维基 [Sukhoi Su-34](https://en.wikipedia.org/wiki/Sukhoi_Su-34)。
- **画面表现建议**：2023 年后在防区外投弹后返航（数据 `standoff_release_and_return`），精灵翼下应可见滑翔炸弹挂载；声音：双发喷气轰鸣（艺术化）。
- **注意**：与 Su‑35 / Su‑30 的区别全在机头——扁平鸭嘴 + 并列座舱。

### Su‑35S / Su‑30SM（`su35s`）
- **类别**：多用途战斗机（侧卫家族，两型合并为一个数据条目）。
- **关键外形特征**：
  - **Su‑35S**：**单座**，**无鸭翼**，座舱前有光电球，加长尾锥，双垂尾 [34]。
  - **Su‑30SM**：**纵列双座**，**有鸭翼** [35]。
- **组成**：通常 2 机编队 ≈。
- **常见涂装**：Su‑35S 多为灰蓝色块迷彩；Su‑30SM 灰蓝 ≈ [34][35]。
- **画面尺度提示**：S4。
- **参考图检索**：Commons [Category:Sukhoi Su-35S](https://commons.wikimedia.org/wiki/Category:Sukhoi_Su-35S)、[Category:Sukhoi Su-30SM](https://commons.wikimedia.org/wiki/Category:Sukhoi_Su-30SM)；维基 [Sukhoi Su-35](https://en.wikipedia.org/wiki/Sukhoi_Su-35)、[Sukhoi Su-30](https://en.wikipedia.org/wiki/Sukhoi_Su-30)。
- **画面表现建议**：俯视下两者差别只在鸭翼；声音：高空喷气轰鸣（艺术化）。
- **注意**：AI 常给 Su‑35 加鸭翼；若只做一套精灵，需人决定以哪型为准。

### Tu‑22M3（`tu22m3`）
- **类别**：远程轰炸机（可变后掠翼）。
- **关键外形特征**：
  1. 可变后掠下单翼 [36]。
  2. 细长尖锐的机头，巨大的楔形侧进气道 [36]。
  3. 双发埋于后机身，单个大垂尾 [36]。
  4. 机腹 / 翼下挂载 Kh‑22 / Kh‑32 [36]。
- **组成**：单机或小编队 ≈。
- **常见涂装**：浅灰上表面、白色下表面 ≈ [36]。
- **画面尺度提示**：S4（远大于战斗机）。
- **参考图检索**：Commons [Category:Tupolev Tu-22M3](https://commons.wikimedia.org/wiki/Category:Tupolev_Tu-22M3)、[Category:Tupolev Tu-22M](https://commons.wikimedia.org/wiki/Category:Tupolev_Tu-22M)；维基 [Tupolev Tu-22M](https://en.wikipedia.org/wiki/Tupolev_Tu-22M)。
- **画面表现建议**：只在地图边缘出现、发射后返回；声音：远处低沉的轰鸣（艺术化）。
- **注意**：与 Su‑24 比例差异巨大，精灵尺寸要严格按 4 px/m。

### MiG‑31K（`mig31k`）
- **类别**：截击机改装的导弹载机。
- **关键外形特征**：
  1. 大型双座（纵列）截击机，矩形大进气道 [37]。
  2. 双垂尾、双发，后掠梯形上单翼 [37]。
  3. **机腹中线挂一枚 Kinzhal**，体积很大、非常醒目 [20][37]。
- **组成**：单机或双机 ≈。
- **常见涂装**：灰色 ≈ [37]。
- **画面尺度提示**：S4。
- **参考图检索**：Commons [Category:Mikoyan MiG-31K](https://commons.wikimedia.org/wiki/Category:Mikoyan_MiG-31K)；维基 [Mikoyan MiG-31](https://en.wikipedia.org/wiki/Mikoyan_MiG-31)。
- **画面表现建议**：做“挂弹 / 已发射”两态；声音：高空强劲的喷气轰鸣（艺术化）。
- **注意**：AI 易与 MiG‑25 / F‑15 混淆；MiG‑31 机身更长、双座。

### 战略轰炸机（Tu‑95MS / Tu‑160）（`strategic_bomber`）
- **类别**：战略轰炸机（两型合并）；数据中 `entersMap: false`，只作为波次来源。
- **关键外形特征**：
  - **Tu‑95MS**：四台发动机驱动**共轴对转螺旋桨**；大后掠机翼；细长机身；Kh‑101 挂在翼下挂架 [38][7]。
  - **Tu‑160**：**白色**，可变后掠翼，四台发动机成对装于翼下两个短舱，Kh‑101 装在弹舱内旋转发射架上 [39][7]。
- **组成**：编队起飞（只在简报 / 指挥层提示中体现）。
- **常见涂装**：Tu‑95MS 银灰 / 金属色 ≈；Tu‑160 白色 ≈ [39]。
- **画面尺度提示**：S4（远大于其他平台）。
- **参考图检索**：Commons [Category:Tupolev Tu-95MS](https://commons.wikimedia.org/wiki/Category:Tupolev_Tu-95MS)、[Category:Tupolev Tu-95](https://commons.wikimedia.org/wiki/Category:Tupolev_Tu-95)、[Category:Tupolev Tu-160](https://commons.wikimedia.org/wiki/Category:Tupolev_Tu-160)；维基 [Tupolev Tu-95](https://en.wikipedia.org/wiki/Tupolev_Tu-95)、[Tupolev Tu-160](https://en.wikipedia.org/wiki/Tupolev_Tu-160)。
- **画面表现建议**：不入实景层；如用于简报插画，Tu‑95 的对转螺旋桨是关键识别点；声音（简报用）：Tu‑95 极响的螺旋桨嗡鸣（艺术化）。
- **注意**：AI 常把 Tu‑95 画成普通四叶螺旋桨——应为前后两副对转螺旋桨。

### Orion 无人机（`orion`）
- **类别**：中空长航时察打一体无人机。
- **关键外形特征**：
  1. 大展弦比细长直翼 ≈ [40]。
  2. 细长机身，尾部推进式螺旋桨 ≈ [40]。
  3. 固定式前三点起落架 [44]（Commons 展会照片）。
  4. 翼下挂载小型制导炸弹 / 导弹（展会照片可见 FAB‑50、UPAB‑50 等模型）[44]；后期挂 Banderol [43]。
  5. 尾翼布局（V 形等）未逐张核对 ≈。
- **组成**：单机。
- **常见涂装**：浅灰 [44]。
- **画面尺度提示**：S2（机身），翼展 S4 ≈。
- **参考图检索**：Commons [Category:Orion UAV](https://commons.wikimedia.org/wiki/Category:Orion_UAV)；维基 [Kronshtadt Orion](https://en.wikipedia.org/wiki/Kronshtadt_Orion)。
- **画面表现建议**：俯视轮廓 **长直翼**；尾迹 **活塞，无尾迹**；声音：缓慢、低沉的螺旋桨嗡鸣，长时间盘旋（艺术化）。
- **注意**：AI 易套用 MQ‑9 / MQ‑1 外形，尾翼与机头需对照照片校正。

### Orlan‑10 / Zala（`orlan_10`）
- **类别**：小型侦察无人机（合并 Orlan‑10 与 ZALA 系列）。
- **关键外形特征**：
  - **Orlan‑10**：上单直翼；**机头拉进式螺旋桨**；浅灰色复合材料机身 [41][44]；由弹射架发射 [44]。
  - **ZALA（421‑16E 等）**：多为飞翼 / 小型固定翼 ≈（未逐张核对）。
- **组成**：单机。
- **常见涂装**：浅灰 [44]。
- **画面尺度提示**：S1。
- **参考图检索**：Commons [Category:Orlan-10](https://commons.wikimedia.org/wiki/Category:Orlan-10)、[Category:ZALA 421-16E](https://commons.wikimedia.org/wiki/Category:ZALA_421-16E)；维基 [STC Orlan-10](https://en.wikipedia.org/wiki/STC_Orlan-10)（ZALA 421‑16E 无英文维基条目，API 确认）。
- **画面表现建议**：俯视轮廓 **直翼**；尾迹 **活塞，无尾迹**；声音：割草机般的小排量发动机声（艺术化）。
- **注意**：Orlan‑10 螺旋桨在机头（拉进式），与 Shahed（推进式）相反，不要混用。

### A‑50U 预警机（`a50u`）
- **类别**：空中预警机（伊尔‑76 运输机改装）。
- **关键外形特征**：
  1. 机身背部架起的**大型圆盘形雷达天线罩** [42]。
  2. 伊尔‑76 机体：高置后掠上单翼、四台翼下吊挂发动机、T 形尾翼 [42]。
- **组成**：单机，远离前线盘旋。
- **常见涂装**：浅灰 / 白 ≈ [42]。
- **画面尺度提示**：S4（远大于战斗机）。
- **参考图检索**：Commons [Category:Beriev A-50U](https://commons.wikimedia.org/wiki/Category:Beriev_A-50U)、[Category:Beriev A-50](https://commons.wikimedia.org/wiki/Category:Beriev_A-50)；维基 [Beriev A-50](https://en.wikipedia.org/wiki/Beriev_A-50)。
- **画面表现建议**：俯视下的圆盘天线罩是唯一必须准确的识别点；声音：远处持续的四发喷气嗡鸣（艺术化）。
- **注意**：AI 常把天线罩画在机腹或画成长条——应为背部圆盘。

---

## 三、与现有文档的差异

（按 brief 第 7 条，只列出，不修改其他文档，由人决定。）

1. **输出路径**：WBS WS10-003 的输出写作 `docs/reference_list.md`（单文件），本任务按指派写为 `docs/reference_list/enemy.md`（按阵营拆分目录）。建议同步更新 WBS 输出列。
2. **合并条目对应多种外形**（数据层面合理，但美术需要决定做几套精灵）：
   - `kh101`：Kh‑101（扁平多棱面）与 Kh‑555（圆截面）外形明显不同 [7][8]；
   - `kh59`：Kh‑59（前后两组翼、M 型有机腹发动机吊舱）与 Kh‑69（类“风暴之影”隐身外形）完全不同 [11][12]；
   - `su35s`：Su‑35S（单座无鸭翼）与 Su‑30SM（双座有鸭翼）[34][35]；
   - `attack_helicopter`：Ka‑52 / Mi‑28 / Mi‑24 三型外形差别很大 [28][29][30]；
   - `orlan_10`：Orlan‑10 与 ZALA 系列外形不同。
3. **时间表“Geran‑2 黑色隐身涂装”**（时间表第 90 行）：维基称部分 Geran‑2“涂黑用于夜间行动” [1]；Shahed‑238 条目称黑色涂装“是否为雷达吸波材料未知” [2]。“隐身”一词缺少公开依据，建议改为“黑色涂装（夜间难以目视）”。
4. **Geran‑5 外形**：时间表与维基都只说“外形接近巡航导弹” [2][43]，没有可核对的翼型 / 尾翼描述；本清单的“直翼”是暂定，需人工核对后再做精灵。
5. **UMPB‑5R 命名**：时间表写“UMPB‑5R 喷气滑翔弹（含报道中的“UMPK 增程型”）” [43]，维基 UMPK 条目中喷气型 UMPB 的描述与“UMPK”命名有混用 [26]；外形依据薄弱。
6. **Commons 分类缺口**（不影响设计，但影响 WS03-006 参考图收集）：Geran‑5、S8000 Banderol、Kh‑32、UMPB D‑30SN、Kh‑555、Kh‑31P、5V55 在 Commons 均无专门分类（API 确认），需从新闻图片（注意授权）或维基条目内图片补充。

## 四、需要人工确认的事项

1. **白色“Z”“V”战术标记**：2022 年俄方飞机 / 直升机上常见 ≈。是否在精灵上出现（真实感 vs. 政治符号的观感），需人决定。
2. **合并条目做几套精灵**（见差异第 2 条）：建议至少 Ka‑52 与 Mi‑24/28 分开、Kh‑101 与 Kh‑555 可共用“巡航导弹”通用精灵，最终由人决定。
3. **外形依据不足的条目**（Geran‑5、Geran‑4、Banderol、Kh‑32、Zircon、UMPB‑5R、Lancet 的具体翼型、Orion 尾翼）：需在 WS03-006 收集到可靠照片后再定，**AI 生成模型不得直接使用**（AGENTS.md 第 8 节）。
4. **S0 尺度档**：为 FPV 新增 “< 1 m” 档，是否接受（或并入 S1）。
5. **声音特征**：全部为艺术化描述，仅 Shahed“摩托车声”有媒体普遍报道依据（本次未逐篇打开核对），供 WS08 参考，需音效设计确认。
6. **Oreshnik 表现**：建议只做多组发光再入体光点，不建模；剧情事件画面的克制程度需人把关（GDD 17 第 1 条）。

## 来源

> 维基条目均通过 `action=raw` 或 API 获取；“已打开核对”= 本次读取了条目原文中与外形相关的句子；“未逐句核对”= 只确认条目存在并取一般描述，未逐句核对外形细节。所有 Commons 分类链接均已用 Commons API 确认存在（另有说明者除外）。

[1] HESA Shahed 136 — https://en.wikipedia.org/wiki/HESA_Shahed_136（已打开核对：截梢三角翼、翼尖安定面、双叶推进螺旋桨、机头摄像头、俄式标记与黑色涂装）
[2] Shahed drones（Shahed 131 / 238 / Geran‑4 / Geran‑5 各节）— https://en.wikipedia.org/wiki/Shahed_drones（已打开核对）
[3] Gerbera (drone) — https://en.wikipedia.org/wiki/Gerbera_(drone)（已打开核对：胶合板 + 泡沫、截梢三角翼、推进式螺旋桨）
[4] ZALA Lancet — https://en.wikipedia.org/wiki/ZALA_Lancet（已打开，仅核对“电动机驱动”；X 形串列翼为一般描述，未逐句核对）
[5] Fiber optic drone — https://en.wikipedia.org/wiki/Fiber_optic_drone（已打开核对：放线、光纤残留）
[6] Molniya (drone) — https://en.wikipedia.org/wiki/Molniya_(drone)（已打开核对：固定翼 FPV、胶合板 / 泡沫 / 塑料 / 铝、弹药捆绑）
[7] Kh-101 — https://en.wikipedia.org/wiki/Kh-101（已打开核对：非圆截面升力机身、Tu‑95MS 翼下 8 枚、Tu‑160 旋转发射架）
[8] Kh-55 — https://en.wikipedia.org/wiki/Kh-55（未逐句核对）
[9] Kalibr (missile family) — https://en.wikipedia.org/wiki/Kalibr_(missile_family)（已获取，外形细节未逐句核对）
[10] 9K720 Iskander — https://en.wikipedia.org/wiki/9K720_Iskander（已获取，外形细节未逐句核对）
[11] Kh-59 — https://en.wikipedia.org/wiki/Kh-59（已打开核对：前部安定面、后部弹翼、尾部助推器、Kh‑59ME 机腹涡扇发动机）
[12] Kh-69 — https://en.wikipedia.org/wiki/Kh-69（已打开核对：外观类似 Storm Shadow / Taurus，展开式弹翼与尾部四片舵面）
[13] S8000 Banderol — https://en.wikipedia.org/wiki/S8000_Banderol（已打开：仅信息框中的小型喷气发动机，外形信息很少）
[14] P-800 Oniks — https://en.wikipedia.org/wiki/P-800_Oniks（已获取，外形细节未逐句核对）
[15] Kh-22 — https://en.wikipedia.org/wiki/Kh-22（已获取，外形细节未逐句核对）
[16] Kh-32 — https://en.wikipedia.org/wiki/Kh-32（已获取，未逐句核对）
[17] Kh-31 — https://en.wikipedia.org/wiki/Kh-31（已打开核对：常规布局、十字形翼面、尾部固体助推器、加长型；四进气道为一般描述）
[18] S-300 missile system — https://en.wikipedia.org/wiki/S-300_missile_system（未逐句核对）
[19] Hwasong-11A（KN‑23）— https://en.wikipedia.org/wiki/Hwasong-11A（已打开核对：类似伊斯坎德尔‑M、尾翼、军绿涂装）
[20] Kh-47M2 Kinzhal — https://en.wikipedia.org/wiki/Kh-47M2_Kinzhal（已打开核对：据报基于伊斯坎德尔；尾部整流罩为一般描述，未逐句核对）
[21] 3M22 Zircon — https://en.wikipedia.org/wiki/3M22_Zircon（已获取；未找到清晰外形描述）
[22] Oreshnik (missile) — https://en.wikipedia.org/wiki/Oreshnik_(missile)（已打开核对：第聂伯罗视频、六弹头、图注“六个子弹药”、利沃夫与比拉采尔克瓦打击）
[23] FAB-250 — https://en.wikipedia.org/wiki/FAB-250（未逐句核对）
[24] FAB-500 — https://en.wikipedia.org/wiki/FAB-500（未逐句核对）
[25] General-purpose bomb § Soviet and Russian（FAB‑1500 / FAB‑3000 重定向目标）— https://en.wikipedia.org/wiki/General-purpose_bomb（未逐句核对）
[26] UMPK (bomb kit) — https://en.wikipedia.org/wiki/UMPK_(bomb_kit)（已打开核对：弹簧展开的双翼、尾部舵面、焊接结构、X 形舵面、UMPB 喷气型残骸描述）
[27] UMPB D-30SN — https://en.wikipedia.org/wiki/UMPB_D-30SN（已打开核对：折叠翼、十字尾翼、比 UMPK 更流线；条目带“来源不可靠”提示）
[28] Kamov Ka-52（重定向至 Kamov Ka-50）— https://en.wikipedia.org/wiki/Kamov_Ka-52（未逐句核对）
[29] Mil Mi-28 — https://en.wikipedia.org/wiki/Mil_Mi-28（未逐句核对）
[30] Mil Mi-24 — https://en.wikipedia.org/wiki/Mil_Mi-24（未逐句核对）
[31] Sukhoi Su-25 — https://en.wikipedia.org/wiki/Sukhoi_Su-25（未逐句核对）
[32] Sukhoi Su-24 — https://en.wikipedia.org/wiki/Sukhoi_Su-24（未逐句核对）
[33] Sukhoi Su-34 — https://en.wikipedia.org/wiki/Sukhoi_Su-34（未逐句核对）
[34] Sukhoi Su-35 — https://en.wikipedia.org/wiki/Sukhoi_Su-35（未逐句核对）
[35] Sukhoi Su-30 — https://en.wikipedia.org/wiki/Sukhoi_Su-30（未逐句核对）
[36] Tupolev Tu-22M — https://en.wikipedia.org/wiki/Tupolev_Tu-22M（未逐句核对）
[37] Mikoyan MiG-31 — https://en.wikipedia.org/wiki/Mikoyan_MiG-31（未逐句核对）
[38] Tupolev Tu-95 — https://en.wikipedia.org/wiki/Tupolev_Tu-95（未逐句核对）
[39] Tupolev Tu-160 — https://en.wikipedia.org/wiki/Tupolev_Tu-160（未逐句核对）
[40] Kronshtadt Orion — https://en.wikipedia.org/wiki/Kronshtadt_Orion（已获取，外形细节未逐句核对）
[41] STC Orlan-10 — https://en.wikipedia.org/wiki/STC_Orlan-10（已打开核对：复合材料机身、弹射架发射图）
[42] Beriev A-50 — https://en.wikipedia.org/wiki/Beriev_A-50（未逐句核对）
[43] 本仓库 docs/俄乌战争塔防_武器投入时间表.md（内部文档，用于时间与平台对照）
[44] Wikimedia Commons 图片（本次已下载缩略图目视查看）：Category:Gerbera UAV（2025-01 乌克兰境内残骸，白色泡沫）、Category:Shahed 238（伊朗国家航空航天公园展品，黑色）、Category:Molniya-2 (drone)（博物馆展品）、Category:Orlan-10（2017 年演习照片）、Category:Orion UAV（Army-2020 展会照片）、Category:Geran-4（2026-10-01 基辅残骸，乌克兰国家警察照片）。分类链接见各条目。
[45] TWZ: New small Russian cruise missile captured by Ukraine intelligence — https://www.twz.com/air/new-small-russian-cruise-missile-captured-by-ukraine-intelligence（取自时间表，未打开核对）
[46] Ukrainska Pravda 2025-10-18（UMPB‑5R 首次袭击洛佐瓦）— https://www.pravda.com.ua/news/2025/10/18/8003354/（取自时间表，未打开核对）
