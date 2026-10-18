# D3 纸面模拟器实现与规格自洽性审查报告（`D3_GAP_LOG.md`）

> **日期**：2026-10-18
> **任务**：D3 — 基于 `docs/spec/00_core.md` ~ `04_enemy_ai_commands.md`、`07_tools.md` 与 `data/` 实现纯 Python 3 标准库纸面模拟器 `tools/papersim/`，跑通 `test_01` 第 1 夜与第 2 夜并验证全部规格契约。

---

## 1. 实现概览（`tools/papersim/`）

| 模块 | 对应规格 | 核心内容 |
|---|---|---|
| `core.py` | `00_core.md` §0.4, §2, §3.1, §3.3.1, §3.7 | `SimTime`、`Vec2`、`Geo`（全 `math.sqrt`，零 `math.hypot`）、`SimRandom`（PCG32 + SplitMix64 + FNV-1a 64 UTF-8）、`ScriptedRandom`、`StateHasher`（FNV-1a 64 LE）、`SpatialGrid` |
| `entities.py` | `00_core.md` §2, §4; `01`–`04` §2, §4 | `EntityStore`、10 类实体、10 个单例状态组件、`SimState`（含 `write_hash` 与 `rebind_stores`）、全 34 种 `SimEvent`、全 12 种 `SimCommand`、`NightResult` / `CarryIn` |
| `terrain.py` | `00_core.md` §1.5; `01_spawn_movement_terrain.md` §3.4 | 纯标准库 16-bit 大端灰度 PNG 解码器（`zlib` + Paeth 滤波还原）、`HeightmapData` 双线性插值、地球曲率修正 `TerrainModel.has_los`、`HorizonProfile`（720 方位角天际线斜率预计算） |
| `loader.py` | `00_core.md` §1; `07_tools.md` §2.1 | `DataLoader`（加载并按关卡日期解析 `data/` 全部 35 个 JSON + PNG 文件，计算规范 `DataHash`）、`DataValidator`（引用完整性、时期升序、反导窗口、占空比漂移等静态检查） |
| `movement.py` | `01_spawn_movement_terrain.md` §3.1–3.3 | 系统 1 `WaveSpawnSystem`（波次时刻表、平台挂载展开、注入波次、权重随机与 AI 选目标钩子）、系统 2 `EnemyMovementSystem`（直线/航点/绕行、线性俯冲/抛物线/高空俯冲、防区外投弹返航、悬停与退出射线） |
| `sensing.py` | `02_sensing_tracks_ew_emission.md` §3.1–3.6 | 系统 3 `SensorSystem`、系统 4 `TrackFusionSystem`、系统 5 `ElectronicWarfareSystem`、系统 6 `EmissionSystem`、系统 11 `ExposureSystem` |
| `engagement.py` | `03_engagement_impact_scoring.md` §3.1–3.8 | 系统 7 `EngagementSystem`（便宜优先弹药分配 + 提前量二次方程求解）、系统 8 `InterceptorSystem`（8 项乘法修正链 + 城市上空判定 + 碎片生成）、系统 9 `ExternalSupportSystem`、系统 10 `ImpactSystem`（CEP 偏移 + 溅射 + 电网 BFS 连锁 + 欺骗假目标）、系统 13 `ScoringSystem` |
| `enemy_ai.py` | `04_enemy_ai_commands.md` §3.1–3.7 | `DeploymentValidator`、阶段 0 `CommandStage`（部署/拆除/移位、防空警报、交战学说、战果二选一、剧情触发器）、系统 12 `EnemyIntelSystem`、`EnemyAiHooks`（`avoid_ad` 64×64 A* 绕行规划、`suppress` 压制波推迟与放行、`known_targets` 评分选目标） |
| `world.py` | `00_core.md` §3.2–3.9 | `SimWorld`（14 系统固定顺序步进、空闲步早退、命令入队规范化、状态哈希、终局提取）、`SimSnapshot`（深拷贝捕获与恢复）、`ReplayRunner`（`.nwreplay.json` 录制与逐检查点回放校验） |
| `bots.py` | `05_campaign_economy.md` §3.16; `07_tools.md` §2.3 | 8 种自动化策略机器人（`passive`、`default`、`always_emit`、`never_emit`、`smart_blink`、`hoarder`、`wasteful`、`relocator`）与 `BatchAnalyzer`（Type-7 分位数统计 + 7 条平衡异常检测规则） |
| `__main__.py` | `07_tools.md` §1 | CLI 子命令：`validate`、`run`、`batch`、`test` |

---

## 2. 发现的规格/脚本缺口与回填记录

### D3-GAP-01：`tools/spec_calc/01/` 验算脚本残留 `math.hypot` 与旧版 `xoshiro256**`
- **现象**：`tools/spec_calc/01/01_terrain_calc.py` 与 `tools/spec_calc/01/01_movement_calc.py` 在 `C-T1-02`（切换至 PCG32）与 `C-T1-04`（禁用 `Math.Hypot`）决议后未同步更新脚本内部的辅助函数，仍使用 `math.hypot` 和 `xoshiro256**`。
- **影响**：违反 `C-T1-04` 与 `00_core.md` §3.1.2。`01_spawn_movement_terrain.md` 正文测试用例（`T-01-01` ~ `T-01-58`）使用的是 `ScriptedRandom` 与整数勾股三元组（如 `3-4-5`、`600-800-1000`），因此正文数值未受影响。
- **修复**：已将 `tools/spec_calc/01/01_terrain_calc.py` 与 `tools/spec_calc/01/01_movement_calc.py` 中的 `math.hypot(dx, dy)` 全部替换为 `math.sqrt(dx * dx + dy * dy)`，并将 `01_movement_calc.py` 顶部的 `SimRandom` 更新为标准 PCG32。全部 8 个 `tools/spec_calc/` 脚本均验证通过。

### D3-GAP-02：`SimSnapshot.Capture` / `Restore` 深拷贝时的 `EntityStore` 时钟委托重绑定
- **现象**：`EntityStore<T>.Add` 在分配新实体时记录 `CreatedTick = State.Tick`（参与 `StateHasher` 状态哈希，`00_core.md` §3.7.2）。若实现层通过深拷贝 `SimState` 实现 `SimSnapshot.Capture` / `Restore`，且 `EntityStore` 内部通过闭包/委托（如 `() => state.Tick`）读取当前步号，默认深拷贝不会更新闭包绑定的旧 `SimState` 引用，导致从快照恢复后新生成的实体（如拦截弹、敌机）写入旧世界的 `CreatedTick`，进而引发状态哈希分歧。
- **修复**：在 `tools/papersim/entities.py` 中新增 `SimState.rebind_stores()` 并在 `SimSnapshot.capture` / `restore` 中调用；同时在 `docs/spec/00_core.md` §2.2.2 补充实现提示，提醒 C# 实现者要么将 `currentTick` 作为参数传入 `EntityStore.Add(entity, State.Tick)`，要么在克隆 `SimState` 时重绑定 `State` 引用。

### D3-GAP-03：`WeaponParams.LauncherCount` 在 `WeaponDef` 与 `UnitDef` 间的回退层级
- **现象**：`data/units/air_defense.json` 中，`launchers` 定义在武器条目 `units[].weapons[].launchers` 上（如 `nasams_missile` 的 `"launchers": 3`），与 `03_engagement_impact_scoring.md` §1.1 `WeaponParams.LauncherCount` 一致。若工具或加载器同时兼容单位级缺省 `unit.launchers`，取值优先级应明确为：`level.launcherOverrides` → `weapon.launchers` → `unit.launchers` → `rules.engagement.defaultLaunchers`。
- **修复**：在 `tools/papersim/engagement.py` 中按上述优先级实现，并在 `test_01` 中验证 `nasams` 正确初始化 3 架发射架 × 6 发 = 18 发待发弹。

### D3-GAP-04：`07_tools.md` §8.2 跨规格核对表中的旧版文件名引用
- **现象**：`docs/spec/07_tools.md` §8.2 表格中仍保留了早期草稿文件名（`01_time_map_movement_waves.md`、`03_engagement_weapons_collateral.md`、`04_layered_defense_decoys_saturation_ai.md`）。
- **修复**：已更新为定稿文件名（`01_spawn_movement_terrain.md`、`03_engagement_impact_scoring.md`、`04_enemy_ai_commands.md`），并在 `07_tools.md` §0.1 中登记 `tools/papersim/` 作为 D3 纯 Python 参考实现。

### D3-GAP-05：`SpatialGrid.QueryCircle` 在大半径稀疏场景下的遍历优化
- **现象**：当雷达射程较大（如 `s300_radar` 150 km，覆盖 30×30 = 900 个 5 km 网格单元）而场上存活目标较少（`len(_cells) <= 10`）时，逐格遍历外接矩形在解释型语言（Python）中有不必要开销。
- **修复**：当外接矩形覆盖格数大于非空桶数 `len(_cells)` 时，直接遍历非空桶并筛选落在 `[cx0, cx1] × [cy0, cy1]` 内的桶，最后按实体 `Id` 升序排序返回。该优化与全网格遍历在数学上严格等价（逐位确定性不变），使全夜模拟提速约 3 倍。

---

## 3. `test_01` 第 1 夜与第 2 夜基准运行结果（Golden Reference）

使用 `seed = 42`（第 1 夜种子 `42`，第 2 夜种子 `SimRandom.night_seed(42, "test_01", 2)`）及预设初始部署（含第 2 夜跨夜 `CarryIn` 结转）：

| 指标 | 第 1 夜（`nightIndex = 1`） | 第 2 夜（`nightIndex = 2`，带入第 1 夜 `CarryOut`） |
|---|---|---|
| 结局（`Outcome` / `Reason`） | `Survived` / `AllClear` | `Survived` / `AllClear` |
| 结束步号（`EndTick`） | `20183` | `18164` |
| 终态哈希（`FinalStateHash`） | `0x49028360658a7edc` | `0xfa196588838032f3` |
| 击落统计（`KillsByType`） | `kh101`: 4, `shahed_136`: 16（共 20） | `kh101`: 1, `kh59`: 1, `shahed_136`: 14（共 16） |
| 漏防统计（`LeaksByType`） | `kh101`: 2, `shahed_136`: 8 | `kh101`: 2 |
| 跨夜敌方已知目标数 | 结转输出 `2` 个（`s300_radar`、`nasams` 暴露 >= 50） | 带入 `2` 个，终局 `2` 个 |
| 回放校验（`ReplayRunner`） | 每 3600 步检查点 + 终态哈希 `0x49028360658a7edc` 100% 匹配 | 100% 匹配 |
| 快照恢复（`SimSnapshot`） | 第 3600 步捕获并恢复运行至终局，哈希 `0x49028360658a7edc` 100% 匹配 | — |
