# 07 命令行工具规格（数据校验 `validate`、无头模拟与回放 `simrun`、性能基准 `bench`）

> 本文件定义 `tools/validate` 与 `tools/simrun`（含回放校验 `--verify-replay`、批量平衡统计 `--seeds`、性能基准 `--bench`）的命令行契约、静态检查规则、输出 JSON 结构、确定性统计算法与验收测试。
> **修订（D2b，2026-10-17）**：依据 `review/C_coverage.md`（`C-T1-10`、`C-T1-11`、`C-T1-12`、`C-T1-15`、`C-T1-16`、`C-T2-02`、`C-T2-04`、`C-T2-08`、`C-T2-09`）、`review/B_decisions.md`（`B-T2-24`、`B-T2-122`、`B-T3-04`、`B-T3-07`、`B-T3-10`）与 `review/DECISIONS.md` 新建。

---

## 0. 范围与依据

### 0.1 覆盖范围

| 工具 / 模式 | 本文件章节 | 对应 WBS | 阶段 |
|---|---|---|---|
| 数据校验 CLI：`tools/validate` | 1.1、2.1、3.1 | WS06-004 | M1 |
| 无头单夜运行与回放录制：`tools/simrun` | 1.2.1、2.2、3.2 | WS06-006、WS06-008 | M2 |
| 回放确定性校验：`tools/simrun --verify-replay` | 1.2.2、2.2、3.3 | WS01-020、WS06-008 | M2 |
| 批量模拟与平衡统计：`tools/simrun --seeds` | 1.2.3、2.3、3.4 | WS06-007、WS09-002 | M2 |
| 单步耗时与内存性能基准：`tools/simrun --bench` | 1.2.4、2.4、3.5 | WS01-028、WS06-007 | M2–M3 |

- **项目结构**：
  - `tools/validate/Validate.csproj`（程序集 `Nightwatch.Tools.Validate`，命名空间 `Nightwatch.Tools.Validate`）：仅引用 `../../sim/Sim.csproj`。
  - `tools/simrun/SimRun.csproj`（程序集 `Nightwatch.Tools.SimRun`，命名空间 `Nightwatch.Tools.SimRun`）：仅引用 `../../sim/Sim.csproj`（及复用 `Nightwatch.Sim.Data`、`Nightwatch.Sim.Replay`）。
  - 测试位于 `sim.tests/Tools/`（`ValidateToolTests.cs`、`SimRunToolTests.cs`、`BenchStatsTests.cs`），直接调用两个工具公开的 `ValidateRunner` 与 `SimRunRunner` 纯入口函数（注入 `IDataSource` 与 `TextWriter`，不启动外部子进程即可单测）。

### 0.2 依据

- [AGENTS.md](../../AGENTS.md) 第 3、5 节（模拟层独立、确定性、常用命令）
- [WBS](../开发任务分解_WBS_v1.md) WS01-020、WS01-028、WS06-004、WS06-006、WS06-007、WS06-008、WS09-002
- [00_core.md](00_core.md) §1（`DataLoader` 与 `DataError`）、§3.1.5（`--seed` 约定）、§3.3.1（单步性能预算与空闲步早退）、§3.5（`NightResult`）、§3.7（`StateHasher`）、§3.9（`.nwreplay.json` 回放格式）
- [01_spawn_movement_terrain.md](01_spawn_movement_terrain.md) §1.2–1.3（`firstSeen`、`storyEventOnly`、弹道/滑翔 `waypointsM`）
- [02_sensing_tracks_ew_emission.md](02_sensing_tracks_ew_emission.md) §1.8、§3.5–3.6（辐射策略 `exposureMult` 目标平均暴露系数）
- [03_engagement_impact_scoring.md](03_engagement_impact_scoring.md) §3.8（`NightResult` 详细结构）
- [04_enemy_ai_commands.md](04_enemy_ai_commands.md) §3.3、§3.5（`DeploymentValidator`、波次 AI 标签警告）
- [05_campaign_economy.md](05_campaign_economy.md) §1.4、§3.10、§3.16（`CampaignDataLoader`、`W_E_NO_SUPPLY_WINDOWS`、跨关引用、策略机器人）

### 0.3 依赖

依赖 `00_core.md` – `05_campaign_economy.md`（不依赖 `06_client_graybox.md`、不引用任何 Godot 程序集）。

### 0.4 全局约束与免责声明

1. **文档同步免责声明（C-T1-12）**：本规格已将 GDD、塔防数值表、WBS 及 D2 审查（`DECISIONS.md`、`A_interfaces.md`、`B_decisions.md`、`C_coverage.md`）中关于命令行工具、静态校验、批量统计与性能基准的全部要求同步收口。编码代理按本规格实现时**无需再次停下询问文档差异**。
2. **跨平台确定性与禁用 `Math.Hypot`（C-T1-04）**：工具层涉及的所有几何距离（如弹道飞行窗口检查、压力场景生成）与统计标准差开方，一律使用 `Math.Sqrt(dx * dx + dy * dy)`，**严禁使用或自写 `Math.Hypot`**。统计聚合（均值、方差、分位数）严格按升序排序后的数组顺序累加，杜绝浮点加法的顺序不确定性。
3. **Stopwatch 隔离（00 §6.2）**：`System.Diagnostics.Stopwatch` 只允许在 `tools/simrun` 的 `--bench` 模式与运行耗时报告中使用，严禁流入 `sim/` 或影响任何模拟结果。

---

## 1. 数据输入与命令行契约

### 1.1 `tools/validate` 命令行契约（WS06-004，`C-T1-11`）

**调用格式**：

```bash
dotnet run --project tools/validate -- [--data <dir>] [--level <id>] [--format text|json] [--strict-warnings] [--strict]
```

| 参数 | 类型 / 缺省 | 说明 |
|---|---|---|
| `--data <dir>` | `string?`，缺省 `null` | `data/` 目录路径；未指定时按 `DataRootLocator` 从当前工作目录或可执行文件目录向上查找含 `AGENTS.md` 的仓库根下的 `data/`（与 06 §1.7 同源） |
| `--level <id>` | `string?`，缺省 `null` | 仅校验指定关卡 `<id>`（含全局目录）；可重复传入多次（`--level test_01 --level l01`）；未指定时校验 `data/levels/` 下除 `_templates` 外的**全部关卡目录**（按目录名序数升序）以及 `data/campaign/` |
| `--format <fmt>` | `text \| json`，缺省 `text` | 输出格式：`text` 按行打印 `[Code] File JsonPath: Detail`；`json` 输出序列化的 `ValidateReport`（§2.1） |
| `--strict-warnings`（别名 `--strict`） | `bool` 开关，缺省 `false` | 开启后，若存在任何警告（`W_*`），退出码也返回 `1` |

**退出码（Exit Codes）**：

| 退出码 | 含义 | 条件 |
|---|---|---|
| `0` | 校验通过 | `Errors.Count == 0` 且（`!StrictWarnings \|\| Warnings.Count == 0`） |
| `1` | 数据校验失败 | `Errors.Count > 0`（含 `DataError` 或关卡初始部署 `DeploymentError`），或 `StrictWarnings && Warnings.Count > 0` |
| `2` | CLI 参数或 IO 错误 | 未知命令行参数、参数缺值、`--data` 目录不存在或无法读取 |

### 1.2 `tools/simrun` 四种运行模式与命令行契约（WS06-006、WS06-007、WS06-008，`C-T1-10`、`C-T1-15`）

`tools/simrun` 根据主模式标志分为**单夜模式**（默认）、**回放校验模式**（`--verify-replay`）、**批量统计模式**（`--seeds`）和**性能基准模式**（`--bench`）。这四种主模式互斥（同时传入多于一种主模式标志时返回退出码 `2`）。

#### 1.2.1 模式一：单夜运行模式（默认）

```bash
dotnet run --project tools/simrun -- --level <id> [--night <1..N>] [--seed <ulong|0x...>] \
  [--deploy <plan.json|default>] [--commands <cmds.json>] [--auto-resolve] [--hardcore] \
  [--hash-every <K>] [--out <report.json>] [--record <replay.nwreplay.json>] [--data <dir>]
```

| 参数 | 缺省值 | 说明 |
|---|---|---|
| `--level <id>` | 必填 | 关卡 ID（如 `test_01`） |
| `--night <1..N>` | `1` | 夜晚序号 `NightIndex`（从 1 开始） |
| `--seed <ulong>` | 见右 | 支持十进制或 `0x` 十六进制无符号 64 位整数；**直接**作为 `SimWorld.Create` 的 `seed` 传入（00 §3.1.5）；未指定时取 `SimRandom.NightSeed(1UL, levelId, nightIndex)`（与 06 §1.5 一致，如 `test_01` 第 1 夜为 `0x6DD180096484586D`） |
| `--deploy <arg>`（别名 `--plan`） | `default` | 部署方案文件路径（JSON 格式同 00 §3.9.1 `config.deployment`），或字面量 `"default"`（使用关卡 `deploy.json` 中的 `initialDeployment` 预设部署，无预设则用 `DeploymentPlan.Empty`） |
| `--commands <path>` | `null` | 预置玩家命令列表 JSON 文件路径（数组元素格式同 00 §3.9.1 `commands[]`），在 `Tick = 0` 按序调用 `world.Enqueue` |
| `--auto-resolve` | `false` | 开启时注入 `CarryIn.AutoResolve = new(InterceptProbMult: 1.0, ExposureGainMult: 1.0)`（或从 `rules/campaign.json` 读取自动结算参数，05 §3.8.2），且不注入任何耗点命令 |
| `--hardcore` | `false` | 开启时设置 `SimConfig.AutoChoicePrompts = false`（关闭自动二选一，B-T2-11） |
| `--hash-every <K>` | `0` | `K > 0` 时，每当 `Tick % K == 0` 记录检查点 `{ tick, hash }` 写入报告的 `tickHashes` 与回放的 `checkpoints`（00 §3.9.1 中录制回放缺省 `checkpointInterval = 60`） |
| `--out <path>` | `null`（写 stdout） | 输出 `SimRunNightReport` JSON（§2.2）到指定文件；未指定时输出到标准输出 `stdout` |
| `--record <path>` | `null` | 夜晚结束后将完整回放（00 §3.9.1 `.nwreplay.json` 格式）写入 `<path>` |
| `--data <dir>` | `null` | 同 `tools/validate --data` |

#### 1.2.2 模式二：回放校验模式（`--verify-replay`）

```bash
dotnet run --project tools/simrun -- --verify-replay <replay.nwreplay.json> [--data <dir>] [--force-data-hash] [--out <verify_report.json>]
```

- 按 00 §3.9.3 `ReplayRunner` 执行：加载关卡数据（校验 `DataHash`，不匹配且未传 `--force-data-hash` 时返回退出码 `1`），创建 `SimWorld`，入队全部命令，逐步推进并在每个 `checkpoints` 与末尾 `final` 核对 `ComputeStateHash()`。
- 若发现任一检查点或最终哈希/步数不一致，立即停止，向 `stderr` 打印首个分歧点 `[E_REPLAY_DIVERGED] tick={tick} expected={expectedHash} actual={actualHash}` 并返回**退出码 `3`**。

#### 1.2.3 模式三：批量统计模式（`--seeds`）

```bash
dotnet run --project tools/simrun -- --level <id> [--night <1..N>] --seeds <start..end|count> \
  [--strategy <passive|default|always_emit|never_emit|hoarder|wasteful>] \
  [--deploy <plan.json|default>] [--out <batch_summary.json>] [--data <dir>]
```

| 参数 | 缺省值 | 说明 |
|---|---|---|
| `--seeds <spec>` | 必填 | 种子规格：①闭区间 `"<start>..<end>"`（如 `"1..100"`，要求 `1 ≤ start ≤ end`），生成种子序列 `s = start, start+1, ..., end`；②正整数 `"<count>"`（如 `"50"`），等同于 `"1..<count>"`。每个种子 `s` 直接作为 `SimWorld.Create` 的 `seed` |
| `--strategy <name>` | `default` | 批量运行的预设策略覆写器（§3.4.1）：`passive`（全单位 `HoldFire = true`）、`default`（保持部署方案原设置）、`always_emit`（所有辐射源设为 `always_on`）、`never_emit`（所有辐射源扇区强制静默 `Silence`）、`hoarder`（所有导弹武器 `AmmoReserve = 50%`）、`wasteful`（所有武器 `PriorityMode = SoonestIntercept`、`AmmoReserve = 0`、关闭目标标签保留） |
| `--out <path>` | `null`（写 stdout） | 输出 `SimRunBatchSummary` JSON（§2.3），供 D3/D4 与 WS09 量化可玩性检验直接调用 |

#### 1.2.4 模式四：性能基准模式（`--bench`，WS01-028、`C-T1-15`、`C-T2-02`）

```bash
dotnet run --project tools/simrun -- --bench [--scenario idle|test_01|stress_50x15x20|finale_600] \
  [--warmup-nights <int>] [--measure-nights <int>] [--strict-budget] [--out <bench_report.json>] [--data <dir>]
```

| 参数 | 缺省值 | 说明 |
|---|---|---|
| `--scenario <id>` | `stress_50x15x20` | 基准场景（§3.5.1）：`idle`（全空场空闲步早退基准）、`test_01`（正式灰盒关卡第 1 夜）、`stress_50x15x20`（`C-T2-02` 标准高压验收场：同屏 50 `Threat` × 15 我方单位 × 20 `Interceptor`，600 步测量窗口）、`finale_600`（`C-T1-15` 终章极限场：600 UAV + 90 CM/BM + 60 火力单元 + 70 传感器） |
| `--warmup-nights <W>` | `2` | 预热运行次数（消除 JIT 编译与首次页分配抖动，不计入统计） |
| `--measure-nights <M>` | `10` | 正式测量运行次数（每次 600 步，共采样 `600 × M` 步） |
| `--strict-budget` | `true` | 是否按 `C-T2-02` 性能阈值判败（可通过 `--no-strict-budget` 在慢速 CI 容器中仅输出报告不报错） |

**`tools/simrun` 统一退出码表**：

| 退出码 | 名称 | 触发条件 |
|---|---|---|
| `0` | `Success` | 运行、回放校验或性能基准全部通过 |
| `1` | `DataOrDeployError` | 数据加载失败（`DataLoadException`）、部署校验失败（`SimSetupException`）或回放 `DataHash` 不匹配 |
| `2` | `CliOrIoError` | 命令行参数非法、文件不存在、JSON 格式无法解析或运行期未捕获异常 |
| `3` | `ReplayDiverged` | `--verify-replay` 模式下任一检查点或最终状态哈希 / 步数不一致 |
| `4` | `BenchBudgetExceeded` | `--bench` 模式下（且 `StrictBudget == true`）耗时超出 `C-T2-02` 阈值（高压场均值 `≥ 2.0 ms/step`、P99 `≥ 4.0 ms/step`、单步最坏 `≥ 50.0 ms`，或空闲步均值 `> 20.0 µs`） |

---

## 2. 状态与输出数据结构（C# Records 与 JSON 契约）

所有输出报告统一使用 `00_core.md` §3.5 规定的 `SimJson.DefaultOptions`（`PropertyNamingPolicy = JsonNamingPolicy.CamelCase`、`JsonStringEnumConverter`、`NumberHandling = JsonNumberHandling.Strict`）。

### 2.1 数据校验报告 `ValidateReport`

```csharp
namespace Nightwatch.Tools.Validate;

public sealed record ValidateWarning(string Code, string File, string JsonPath, string Detail)
{
    public override string ToString() => $"[{Code}] {File} {JsonPath}: {Detail}";
}

public sealed record ValidateReport
{
    public bool Passed { get; init; }                                      // ExitCode == 0
    public int CheckedFilesCount { get; init; }                            // 校验的 JSON/PNG 文件总数
    public IReadOnlyList<string> CheckedLevels { get; init; } = [];        // 校验的关卡 ID 列表（升序）
    public IReadOnlyList<DataError> Errors { get; init; } = [];            // 00 §1.3 错误列表
    public IReadOnlyList<ValidateWarning> Warnings { get; init; } = [];    // §3.1 扩展静态检查警告列表
    public IReadOnlyList<string> ProvisionalPaths { get; init; } = [];     // 汇总全部 LevelData.ProvisionalPaths（去重升序）
}
```

### 2.2 单夜运行与回放校验报告 `SimRunNightReport`、`ReplayVerifyReport`

```csharp
namespace Nightwatch.Tools.SimRun;

public readonly record struct TickHashEntry(int Tick, string Hash);        // Hash 格式 "0x" + 16 位大写十六进制

public sealed record SimRunNightReport
{
    public string LevelId { get; init; } = "";
    public int NightIndex { get; init; }
    public string Seed { get; init; } = "";                                // "0x" + X16
    public string DataHash { get; init; } = "";                            // "sha256:..."
    public string FinalStateHash { get; init; } = "";                      // = Result.FinalStateHash
    public double ElapsedWallMs { get; init; }                             // 实际运行耗时（毫秒，仅供参考）
    public NightResult Result { get; init; } = new();                      // 00 §3.5 / 03 §3.8.6 完整结算结构
    public IReadOnlyList<TickHashEntry> TickHashes { get; init; } = [];    // --hash-every K > 0 时输出
    public string? RecordedReplayPath { get; init; }                       // --record 时输出路径
}

public sealed record ReplayVerifyReport
{
    public string ReplayFile { get; init; } = "";
    public string LevelId { get; init; } = "";
    public int NightIndex { get; init; }
    public string Seed { get; init; } = "";
    public bool Passed { get; init; }
    public int TotalTicks { get; init; }
    public int CheckpointsVerified { get; init; }
    public int? DivergedTick { get; init; }                               // Passed == true 时为 null
    public string? ExpectedHash { get; init; }
    public string? ActualHash { get; init; }
    public string? RuntimeWarning { get; init; }                           // runtime 字符串不同时提示（B-T2-20）
}
```

### 2.3 批量统计汇总报告 `SimRunBatchSummary`

```csharp
namespace Nightwatch.Tools.SimRun;

public sealed record MetricDistribution
{
    public int Count { get; init; }
    public double Min { get; init; }
    public double Max { get; init; }
    public double Mean { get; init; }
    public double StdDev { get; init; }                                    // 总体标准差 sqrt(Σ(x_i - mean)^2 / N)
    public double P10 { get; init; }
    public double P50 { get; init; }
    public double P90 { get; init; }
    public double P99 { get; init; }
}

public sealed record StructureSurvivalStat(
    string StructureId, double SurvivalRate, double MeanHpEndFrac, double MeanUnpoweredSec);

public sealed record UnitContributionStat(
    string UnitDefId, PlayerUnitCategory Category,
    double MeanKills, double MeanShots, double MeanShotCostMusd,
    double MeanExposureEnd, double MeanExposurePeak, double DestroyedRate);

public sealed record StrategyExposureStat(
    string UnitDefId, string PolicyId,
    double TargetExposureMult, double MeasuredMeanExposureRatio, double Drift); // B-T3-10 核对

public sealed record SimRunBatchSummary
{
    public string LevelId { get; init; } = "";
    public int NightIndex { get; init; }
    public string Strategy { get; init; } = "default";
    public int RunCount { get; init; }
    public IReadOnlyList<string> Seeds { get; init; } = [];                // 全部运行的种子（"0x" + X16）
    public double SurvivalRate { get; init; }                              // Outcome == Survived 的比例 [0, 1]
    public double GridCollapseRate { get; init; }                          // GridCollapsed == true 的比例
    public double Exposure100TriggerRate { get; init; }                    // 任一我方单位 ExposurePeak >= 100.0 的运行比例（B-T3-05）
    public double UrbanNavJamTriggerRate { get; init; }                    // CarryOut.UrbanNavJamTriggered 比例（B-T2-36）
    public MetricDistribution InterceptRate { get; init; } = new();        // ThreatsIntercepted / max(1, ThreatsSpawned - DecoysSpawned)
    public MetricDistribution AllTargetInterceptRate { get; init; } = new();// ThreatsIntercepted / max(1, ThreatsSpawned)
    public MetricDistribution? ExchangeRatio { get; init; }                // 仅对 TotalShotCostMusd > 0 的运行统计；全为 0 时为 null
    public MetricDistribution WeightedLossFrac { get; init; } = new();
    public MetricDistribution TotalShotCostMusd { get; init; } = new();
    public IReadOnlyDictionary<LeakReason, double> MeanLeaksByReason { get; init; } = new SortedDictionary<LeakReason, double>();
    public IReadOnlyList<StructureSurvivalStat> Structures { get; init; } = [];
    public IReadOnlyList<UnitContributionStat> Units { get; init; } = [];
    public IReadOnlyList<StrategyExposureStat> ExposureCalibration { get; init; } = []; // 供 D3 校验 B-T3-10
}
```

### 2.4 性能基准报告 `BenchReport`（WS01-028、`C-T1-15`、`C-T2-02`）

```csharp
namespace Nightwatch.Tools.SimRun;

public sealed record SystemTimingStat(
    int Order, string SystemName, double MeanMs, double P99Ms, double MaxMs);

public sealed record BenchBudgetThresholds(
    double MaxMeanStepMs, double MaxP99StepMs, double MaxSingleStepMs);

public sealed record BenchReport
{
    public string Scenario { get; init; } = "";
    public string Runtime { get; init; } = "";                             // RuntimeInformation.RuntimeIdentifier + FrameworkDescription
    public int WarmupNights { get; init; }
    public int MeasureNights { get; init; }
    public int TotalMeasuredSteps { get; init; }
    public bool Passed { get; init; }
    public BenchBudgetThresholds Thresholds { get; init; } = new(2.0, 4.0, 50.0);
    public MetricDistribution StepWallMs { get; init; } = new();           // 单步总耗时分布（毫秒）
    public double EngagementAllocationMeanMs { get; init; }                // 03 便宜优先分配子步骤均值（预算 <= 0.3 ms，C-T1-14）
    public long AllocatedBytesPerStepMean { get; init; }                   // GC.GetAllocatedBytesForCurrentThread() 差值均值
    public IReadOnlyList<SystemTimingStat> SystemTimings { get; init; } = []; // Order 0 (Stage0) .. 14 分项耗时
    public IReadOnlyList<string> Violations { get; init; } = [];           // 超标项说明列表
}
```
---

## 3. 每步与各模式算法

### 3.1 数据校验器算法 `ValidateRunner`（WS06-004、`C-T1-11`、`C-T2-04`、`C-T2-08`、`C-T2-09`）

`ValidateRunner.Run(options)` 按确定性顺序执行以下 6 个阶段，收集全部 `errors` 与 `warnings`（不在首个错误处短路）：

#### 阶段 1：全局目录与跨文件引用校验（复用 `00 §4.2` 与 `05 §2`）
1. 调用 `DataLoader.LoadCatalog(dataRoot)` 加载 `units/*.json`、`enemies/*.json`、`support/*.json`、`loc/*.json`；捕获所有 `DataError` 并映射为 `ValidateIssue(Severity: Error)`。
2. 调用 `CampaignDataLoader.LoadAll(dataRoot)` 加载 `campaign/campaign.json`、`cross_level_links.json`、`reward_cards.json`、`historical_events.json`、`commander_trait.json`、`narrative/*.json`：
   - 校验 `campaign.json` 中所有 `levelId` 对应目录 `levels/<levelId>/` 存在。
   - 校验 `reward_cards.json` 的 `unlockCondition`、`grantUnitId`、`grantSupportId` 引用合法。

#### 阶段 2：逐关基础加载与初始部署合法性校验
对目标关卡集合（默认按 `campaign.json` 关卡序号升序 + 其余 `levels/*` 字典序；`--level` 时仅指定关卡）：
1. 调用 `DataLoader.LoadLevel(dataRoot, levelId, catalog)` 执行 `00 §4.2` 规则 1–10（JSON 语法、Schema、唯一 ID、外键引用、本地化键、地图尺寸与多边形几何、数值区间、波次时间窗口、阶段解锁、枚举值）。
2. 若关卡含 `deploy.json` 的 `initialDeployment`（预设/教程初始部署），构造对应的 `DeploymentPlan` 并调用 `DeploymentValidator.Validate(level, plan)`（`00 §3.2`）：任何返回的 `DeploymentError`（`D_*`）均转为 `ValidateIssue(Severity: Error)`。
3. 校验 `cross_level_links.json` 中引用该关的 `sourceLevelId` / `sourceStructureId` / `targetLevelId` 存在且类型匹配（`C-T2-04` / `B-T2-124`）。

#### 阶段 3：历史时间线一致性校验（`C-T2-08`、`00 §4.2 #11`、`05 §5 #18`）
对每个拥有战役序号 `level.Meta.Number` 与日期 `level.Meta.Date` 的关卡：
1. **我方单位解锁关卡检查（Error `E_TIMELINE_UNIT_UNAVAILABLE`）**：遍历 `deploy.json` 的 `availableUnits[].unit` 及 `initialDeployment.units[].unitId`，若对应 `UnitDef.FirstAvailable.Level > level.Meta.Number`，报 Error `E_TIMELINE_UNIT_UNAVAILABLE`。
2. **敌方首次出现年月检查（Error `E_TIMELINE_ENEMY_FIRST_SEEN`）**：取关卡年月 `levelYm = level.Meta.Date.ToYearMonth()`（`"YYYY-MM"`）；遍历 `waves.json` 中所有波次组的 `enemyId` 以及 `flow.json` 中可能刷出敌人的事件，若 ` string.CompareOrdinal(enemyDef.FirstSeen, levelYm) > 0`，报 Error `E_TIMELINE_ENEMY_FIRST_SEEN`。
3. **跨全战役从不登场的敌人检查（Warning `W_FIRST_SEEN_NEVER_APPEARS`）**：全量扫描时（未指定 `--level`），取战役最大关卡年月 `maxCampaignYm`；若某 `EnemyDef.FirstSeen > maxCampaignYm`（例如 `P04` 滑翔炸弹在 M5 战役范围外），报 Warning `W_FIRST_SEEN_NEVER_APPEARS`。
4. **历史事件停用单位冲突检查（Warning `W_HISTORICAL_UNIT_UNAVAILABLE`）**：若 `historical_events.json` 在该关激活了 `unit_unavailable(unitId)`，但该关 `deploy.json` 的 `availableUnits` 仍包含 `unitId`（加载时虽按 `05 §5 #18` 自动过滤），报 Warning `W_HISTORICAL_UNIT_UNAVAILABLE` 提醒策划确认。

#### 阶段 4–6：扩展静态分析警告规则表（`C-T1-11`、`C-T2-09`、`B-T3-10`）

除上述错误外，`ValidateRunner` 执行以下静态一致性与可玩性检查，触发时记录 `Severity: Warning`（`--strict` 下阻断 CI）：

| 代码 | 级别 | 触发条件 | 关联规格与依据 |
|---|---|---|---|
| `E_TIMELINE_UNIT_UNAVAILABLE` | Error | 关卡可用/预设单位的 `firstAvailable.level > level.Meta.Number` | `00 §4.2 #11`, `C-T2-08` |
| `E_TIMELINE_ENEMY_FIRST_SEEN` | Error | 关卡波次/事件引用敌人的 `firstSeen > level.Meta.Date[0..7]` | `00 §4.2 #11`, `C-T2-08` |
| `W_FIRST_SEEN_NEVER_APPEARS` | Warning | `EnemyDef.FirstSeen` 晚于 `campaign.json` 中所有关卡日期 | `00 §4.2 #11`, `C-T2-08` |
| `W_HISTORICAL_UNIT_UNAVAILABLE` | Warning | 历史事件在该关停用了某单位，但该单位仍列在关卡 `availableUnits` 中 | `05 §5 #18` |
| `W_IGNORED_WAYPOINTS` | Warning | 弹道/滑翔弹药（`BM` / `HBM` / `GB`）波次组配置了非空 `waypointsM`（模拟层按直线忽略航路点） | `01 §8.1 Q6`, `B-T2-24` |
| `W_HUNT_NO_KNOWN_TARGETS_GROUP` | Warning | 波次含 `AiTag.Hunt`，但组内没有任何 `targetRule` 为 `known_targets` 或 `air_defense` 的组 | `04 §3.3.1`, `C-T1-11` |
| `W_SUPPRESS_NO_ARM_GROUP` | Warning | 波次含 `AiTag.Suppress`，但组内没有任何反辐射弹药（`tracksEmittingRadarOnly == true`）组 | `04 §3.3.3`, `C-T1-11` |
| `W_ARM_STATIC_TARGET` | Warning | 反辐射弹药（`tracksEmittingRadarOnly == true`）波次组的 `targetRule` 设为 `structure` 或 `weighted_random` | `04 §5 #7`, `C-T1-11` |
| `W_STORY_ONLY_ENEMY_IN_NORMAL_WAVE` | Warning | `storyEventOnly == true` 的敌人（如 `A02` 运输机）出现在 `isStoryWave == false` 的普通波次中 | `01 §1.2`, `C-T1-11` |
| `W_E_NO_SUPPLY_WINDOWS` | Warning | 时间结构为 `TimeStructure.E`（持久消耗战）的关卡 `flow.json` 中 `supplyWindows` 为空 | `05 §1.4`, `B-T2-122` |
| `W_EXPOSURE_MULT_DRIFT` | Warning | `DutyCycle` 辐射策略的静态 `exposureMult` 与理论占空比 $\frac{\text{onSec}}{\text{onSec}+\text{offSec}}$ 绝对差 $> 0.15$ | `02 §3.7`, `B-T3-10` |
| `W_BALLISTIC_WINDOW_TOO_SHORT` | Warning | 关卡存在 `BM`/`HBM` 波次组，其地图内水平飞行时间 $t_{\text{fly}} = \frac{\text{dist2D}(\text{spawn}, \text{target})}{\text{speedMps}}$ 小于本关任一可用反导武器（`canEngageBallistic == true`）的 $\text{reactionSec} + \text{shotIntervalSec}$ | `01 §3.6`, `C-T2-09` |

> **`W_BALLISTIC_WINDOW_TOO_SHORT` 精确计算公式（`C-T2-09`）**：
> 对每个 `Category in {BM, HBM}` 的波次组，取出生点 $S = (x_s, y_s)$，目标点 $T$ 遍历该组可能命中的本关设施坐标（若 `targetRule == SpecificStructure` 则取该设施坐标，否则取距离 $S$ 最近的非诱饵设施坐标），水平距离 $d = \sqrt{(x_T - x_s)^2 + (y_T - y_s)^2}$，水平飞行时间 $t_{\text{fly}} = d / v_{\text{enemy}}$。收集本关 `availableUnits` 及 `initialDeployment` 中具备 `canEngageBallistic == true` 的我方单位定义，若存在单位满足 $t_{\text{fly}} < \text{reactionSec} + \text{shotIntervalSec}$，则发出 `W_BALLISTIC_WINDOW_TOO_SHORT`（提示地图尺寸或出生点距离过近，不足以完成“首轮拦截 + 补射”两发窗口）。

---

### 3.2 单夜无头运行与录像生成算法 `SimRunner`（WS06-006、`B-T3-06`）

```csharp
public static (SimRunNightReport Report, NightReplay? Replay) RunSingleNight(
    SimRunOptions opts, LevelDataPackage pkg, ulong seed,
    DeploymentPlan plan, IReadOnlyList<SimCommand> scheduledCommands, ISimStrategyBot? bot)
{
    var world = new SimWorld(pkg, seed);
    world.ApplyDeployment(plan);

    // 按 (TimeSec 升序, OriginalIndex 升序) 归并排定命令
    var cmdQueue = scheduledCommands
        .Select((cmd, idx) => (cmd, idx))
        .OrderBy(x => x.cmd.TimeSec).ThenBy(x => x.idx)
        .ToList();
    int cmdCursor = 0;

    var recordedCommands = new List<SimCommand>();
    var hourlyChecksums = new List<ReplayHourlyChecksum>();
    var eventCounts = new SortedDictionary<string, int>(StringComparer.Ordinal);
    var leaksByReason = new SortedDictionary<LeakReason, int>();
    foreach (LeakReason r in Enum.GetValues<LeakReason>()) leaksByReason[r] = 0;

    int totalSteps = pkg.Level.Flow.NightDurationSec;
    for (int step = 0; step < totalSteps; step++)
    {
        int nowSec = world.NowSec; // 步初世界秒 [0 .. totalSteps-1]
        // 1. 注入本步排定的外部命令
        while (cmdCursor < cmdQueue.Count && cmdQueue[cmdCursor].cmd.TimeSec <= nowSec)
        {
            var c = cmdQueue[cmdCursor++].cmd with { TimeSec = nowSec };
            world.EnqueueCommand(c);
            recordedCommands.Add(c);
        }
        // 2. 若启用了内置策略 Bot，生成本步策略命令并入队
        if (bot is not null)
        {
            foreach (var bc in bot.DecideCommands(world, nowSec))
            {
                var c = bc with { TimeSec = nowSec };
                world.EnqueueCommand(c);
                recordedCommands.Add(c);
            }
        }
        // 3. 推进 1 世界秒（严格按 00 §1.4 的 Stage 0..14 顺序）
        world.Step();

        // 4. 排空并统计本步事件（B-T3-06：防止 _pendingEvents 无界增长）
        foreach (var ev in world.DrainEvents())
        {
            string typeName = ev.GetType().Name;
            eventCounts[typeName] = eventCounts.GetValueOrDefault(typeName) + 1;
            if (ev is EnemyLeakedEvent leakEv)
                leaksByReason[leakEv.Reason] = leaksByReason[leakEv.Reason] + 1;
        }

        // 5. 整点摘要记录（每 3600 步或夜晚结束步）
        if (world.NowSec % 3600 == 0 || world.NowSec == totalSteps)
        {
            hourlyChecksums.Add(new ReplayHourlyChecksum(world.NowSec, world.ComputeStateChecksum()));
        }

        if (world.IsNightOver) break;
    }

    ulong finalChecksum = world.ComputeStateChecksum();
    var report = BuildNightReport(world, pkg, seed, leaksByReason, eventCounts, finalChecksum);
    NightReplay? replay = opts.ReplayOutPath is not null
        ? new NightReplay
        {
            FormatVersion = 1,
            LevelId = pkg.Level.Meta.Id,
            NightIndex = opts.NightIndex,
            Seed = seed,
            NightDurationSec = world.NowSec,
            InitialDeployment = plan,
            Commands = recordedCommands,
            HourlyChecksums = hourlyChecksums,
            FinalStateChecksum = finalChecksum
        }
        : null;
    return (report, replay);
}
```

---

### 3.3 回放确定性校验算法 `ReplayVerifier`（WS01-027、`A-2-11`）

`ReplayVerifier.Verify(replay, pkg)` 独立构造全新的 `SimWorld(pkg, replay.Seed)`，应用 `replay.InitialDeployment`，将 `replay.Commands` 按记录顺序注入，逐步运行至 `replay.NightDurationSec`：

1. 每当 `world.NowSec` 匹配 `replay.HourlyChecksums` 中的某一项 `check.TimeSec` 时，计算 `actual = world.ComputeStateChecksum()`。若 `actual != check.StateChecksum`：
   - 立即返回 `ReplayVerifyReport(Matched: false, FirstMismatchTimeSec: world.NowSec, ExpectedChecksum: ..., ActualChecksum: ...)`，进程以退出码 **`3`** 终止。
2. 跑完最后一秒后，校验 `world.ComputeStateChecksum() == replay.FinalStateChecksum`。若不等，同样返回 `Matched: false` 并以退出码 **`3`** 终止。
3. 全部一致时返回 `Matched: true, FirstMismatchTimeSec: null`，退出码为 **`0`**。

---

### 3.4 批量统计、内置策略与校准算法 `BatchRunner`（WS06-007、`B-T3-10`）

#### 3.4.1 内置自动策略接口与 6 种标准实现

```csharp
public interface ISimStrategyBot
{
    string Name { get; }
    DeploymentPlan ModifyInitialDeployment(LevelDataPackage pkg, DeploymentPlan basePlan);
    IReadOnlyList<SimCommand> DecideCommands(SimWorld world, int nowSec);
}
```

| 策略名 (`--strategy`) | 部署期行为 (`ModifyInitialDeployment`) | 夜战期每步行为 (`DecideCommands`) | 用途 |
|---|---|---|---|
| `passive` | 保持输入 `basePlan` 不变 | 不产生任何命令（返回空列表） | 检验纯静态部署与默认交战规则基线 |
| `default` | 保持输入 `basePlan` 不变 | ① 当某我方地面单位 `Exposure >= 75.0` 且存在空闲备用阵地且冷却就绪时，下达 `MoveUnitCommand` 转移至按 `SiteId` 升序首个空闲阵地；② 当补给窗口开启（`NowSec == window.StartSec`）且某存活单位弹药比例 $\le 0.50$ 时，按单位 `Id` 升序下达 `SupplyOrderCommand` 直至配额用尽；③ 若支援就绪且场上活跃敌数 $\ge 5$，触发首个就绪支援 | 标准回归基线（模拟理性中等水平玩家） |
| `always_emit` | 将所有我方雷达单位的 `EmissionStrategy` 覆写为 `AlwaysOn` | 不产生命令 | 检验最大探测覆盖与最快暴露上界（`B-T3-10`） |
| `never_emit` | 将所有我方雷达单位的 `EmissionStrategy` 覆写为 `Silent` | 不产生命令 | 检验纯被动传感器（声学/哨所）保底能力 |
| `hoarder` | 将所有防空火力的交战准则 `EngagementDoctrine` 覆写为 `ConserveAmmo`（仅打高价值/非诱饵确认目标） | 仅在单位弹药 $= 0$ 时请求补给 | 检验省弹策略在饱和波次下的漏防风险 |
| `wasteful` | 将所有防空火力的交战准则覆写为 `MaxIntercept`，所有雷达设为 `AlwaysOn` | 不转移阵地；有支援即刻释放 | 检验弹药耗尽时间与费效比下界 |

#### 3.4.2 确定性分布统计 `StatsCalculator`（`C-T1-15`）

给定长度 $N \ge 1$ 的样本序列 $X = [x_0, x_1, \dots, x_{N-1}]$：
1. **排序副本**：先构造升序排列副本 $S = [s_0 \le s_1 \le \dots \le s_{N-1}]$（消除输入顺序影响，且升序累加减小浮点舍入误差）。
2. **均值与总体标准差**：
   $$\mu = \frac{1}{N} \sum_{i=0}^{N-1} s_i, \qquad \sigma = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (s_i - \mu)^2}$$
3. **连续线性插值分位数（Type-7 / NumPy `linear` / Excel `PERCENTILE.INC`）**：
   对分位点 $p \in [0, 1]$（如 $p \in \{0.10, 0.50, 0.90, 0.99\}$）：
   - 当 $N = 1$ 时，$\text{Percentile}(S, p) = s_0$。
   - 当 $N \ge 2$ 时，令连续下标 $h = p \cdot (N - 1)$，下取整 $k = \lfloor h \rfloor$，小数部分 $f = h - k$：
     $$\text{Percentile}(S, p) = \begin{cases} s_{N-1}, & k \ge N - 1 \\ s_k + f \cdot (s_{k+1} - s_k), & 0 \le k < N - 1 \end{cases}$$

#### 3.4.3 辐射暴露乘数校准统计 `ExposureCalibration`（`B-T3-10`）

为验证 `02 §3.7` 中各辐射策略的静态 `exposureMult` 与实际交战触发下的有效暴露速率一致，当 `simrun` 在批量模式下附加 `--calibrate-exposure`（或由回归测试调用 `BatchRunner.ComputeExposureCalibration`）时：
1. 以相同种子集合分别在 `always_emit`、关卡默认 `DutyCycle`、`BurstSweep`、`WaitForCue` 四种辐射配置下运行；
2. 对每个雷达单位统计全夜累积暴露增量 $\Delta E_{\text{strat}}$，计算其相对于 `always_emit` 的实测暴露比：
   $$r_{\text{empirical}} = \frac{\text{Mean}(\Delta E_{\text{strat}})}{\max(10^{-9},\; \text{Mean}(\Delta E_{\text{always\_emit}}))}$$
3. 输出 `StrategyExposureStat(StrategyType,ConfiguredExposureMult, EmpiricalExposureRatio, AbsoluteDrift: |Configured - Empirical|)` 列表，供 D3 平衡验收核对 $|r_{\text{empirical}} - \text{ConfiguredExposureMult}| \le 0.15$。

---

### 3.5 性能基准测试算法 `BenchRunner`（WS01-028、`C-T2-02`、`C-T1-14`、`C-T1-16`）

#### 3.5.1 内置基准场景定义

| 场景名 (`--bench`) | 世界规模与参数 | 每夜步数 | 用途 |
|---|---|---|---|
| `idle` | 20 km × 20 km 空旷地图，0 我方单位，0 敌方波次 | 3600 步 | 测量 `SimWorld.Step()` 框架空转开销基线 |
| `test_01` | 标准测试关 `test_01`（默认部署与波次） | `flow.NightDurationSec` | 测量常规关卡单步耗时 |
| `stress_50x15x20` | 合成高压场景（**无需外部磁盘文件**，由 `SyntheticScenarioBuilder.BuildStress50x15x20()` 在内存中构造）：<br/>• 50 个活跃敌方威胁（含 `Shahed`、`CM`、`BM`、`AD` 混合编队，全夜持续巡航/补充以维持 50 个在场目标）<br/>• 15 个我方防空火力单位（涵盖高射机枪、高炮、近程/中程/远程防空导弹，均开启自动交战）<br/>• 20 个我方传感器（含全天候搜索雷达、周期开关雷达、声学阵列、机动观察哨、火控雷达） | 3600 步 | **核心架构性能门禁场景**（`00 §1.4`、`C-T2-02`） |
| `finale_600` | M5 终局饱和夜压力场景（由 `SyntheticScenarioBuilder.BuildFinale600()` 构造：全夜累计 600 个敌方飞行物分多波次复合突防，20 个火力单位 + 24 个传感器 + 5 个电子战器） | 10800 步 | 测量大波次终局夜长时运行与内存分配稳定性（`C-T1-16`） |

#### 3.5.2 预热、采样与合格判定规则

1. **JIT 预热**：先完整运行 `WarmupNights` 夜（默认 1 夜），丢弃计时数据，并调用一次 `GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect();`。
2. **正式采样**：运行 `MeasureNights` 夜（默认 5 夜；如 `stress_50x15x20` 共采样 $5 \times 3600 = 18000$ 步）：
   - 每步外部用 `Stopwatch.GetTimestamp()` 测量单步总耗时 $t_{\text{step}}$（换算为毫秒 `elapsedTicks * 1000.0 / Stopwatch.Frequency`）。
   - 通过注入 `SimWorld.StepInstrumentation` 回调记录 Stage 0..14 各子系统的分项耗时，以及 `03 §3.4` 便宜优先分配子步骤耗时 $t_{\text{alloc}}$。
   - 每步前后读取 `GC.GetAllocatedBytesForCurrentThread()` 差值，统计单步平均托管堆分配字节数。
3. **合格阈值判定（`Passed`）**：
   当且仅当以下 4 项全部满足时，`BenchReport.Passed = true`（退出码 `0`），否则 `Passed = false`（记录 `Violations` 并返回退出码 `4`）：
   - `StepWallMs.Mean < Thresholds.MaxMeanStepMs`（默认 `< 2.0 ms`，保障 60× 快进时每秒 60 步总耗时 $< 120\text{ ms}$）；
   - `StepWallMs.P99 < Thresholds.MaxP99StepMs`（默认 `< 4.0 ms`）；
   - `StepWallMs.Max < Thresholds.MaxSingleStepMs`（默认 `< 50.0 ms`，杜绝渲染卡顿尖峰）；
   - `EngagementAllocationMeanMs <= 0.3`（`03 §3.4` / `C-T1-14` 贪心指派预算 $\le 0.3\text{ ms}$）。

---

## 4. 事件与命令

1. **`tools/validate`**：纯静态数据读取与分析，不创建 `SimWorld`，不产生或消费任何 `SimCommand` / `SimEvent`。
2. **`tools/simrun` 对命令的注入**：
   - 仅使用 `00_core.md` §1.5 定义的 6 种标准夜战命令（`ChangeEmissionModeCommand`、`ChangeDoctrineCommand`、`ManualEngageCommand`、`MoveUnitCommand`、`TriggerSupportCommand`、`SupplyOrderCommand`），通过 `world.EnqueueCommand(cmd)` 入队。
   - **禁止**绕过 `EnqueueCommand` 直接修改 `SimWorld` 内部实体状态。
3. **`tools/simrun` 对事件的消费（`B-T3-06`）**：
   - 单夜运行、回放校验、批量模拟的每一步 `world.Step()` 之后，**必须**立即调用 `world.DrainEvents()` 清空本步事件队列（`--bench` 模式下同样每步调用 `DrainEvents()` 以包含事件生成的真实开销并防止列表膨胀）。

---

## 5. 边界情况

| # | 场景 | 规定行为 |
|---|---|---|
| 1 | `tools/validate` 目标目录不存在或缺少 `units/`、`enemies/` | 捕获异常并输出包含 `E_DATA_DIR_NOT_FOUND` 的 `ValidateReport`，退出码为 `2`（不抛未处理异常崩溃）。 |
| 2 | JSON 文件存在语法错误（如末尾多余逗号） | 记录 `E_JSON_SYNTAX`（含文件路径与行号），继续扫描其余文件，最终退出码 `2`。 |
| 3 | `tools/validate` 无错误但有 1 条 Warning | 默认模式退出码为 `0`；加 `--strict` 时退出码为 `2`。 |
| 4 | `DutyCycle` 的 `onSec + offSec == 0` | `00 §4.2 #7` 已拦为 `E_INVALID_RANGE` Error；`ValidateRunner` 计算 `W_EXPOSURE_MULT_DRIFT` 时先检查分母 $> 0$，避免除零。 |
| 5 | 关卡无任何 `canEngageBallistic == true` 的可用单位，但有 `BM` 波次 | 不触发 `W_BALLISTIC_WINDOW_TOO_SHORT`（因为不存在反导单位可比较反应窗口，此类关卡属于硬抗或特定剧情关）。 |
| 6 | `--seed` 传入十进制或 `0x` 十六进制 | `0x`/`0X` 前缀按 Base-16 无符号 64 位整数解析；纯数字按 Base-10 `ulong.Parse(..., CultureInfo.InvariantCulture)` 解析；非法字符串报退出码 `1`。 |
| 7 | `--seed` 与 `--seeds` 同时传入 | 命令行参数冲突，向 `stderr` 打印错误说明并返回退出码 `1`。 |
| 8 | `--seeds 0` 或负数 | 参数非法，返回退出码 `1`（`--seeds` 必须 $\ge 1$）。 |
| 9 | 单夜或某次运行中我方未发射任何拦截弹（`TotalShotCostMusd == 0.0`） | 单夜 `SimRunNightReport.ExchangeRatio` 为 `null`（JSON 序列化为 `null`，避免 `NaN`/`Infinity`）；批量汇总 `SimRunBatchSummary.ExchangeRatio` 仅对 `TotalShotCostMusd > 0` 的运行子集计算分布，若全部运行均为 `0` 则汇总项也为 `null`。 |
| 10 | 全夜刷出敌人数 `ThreatsSpawned == 0` 或全部为诱饵（`ThreatsSpawned == DecoysSpawned`） | `InterceptRate` 与 `AllTargetInterceptRate` 分母未达 1 时 convention 约定值为 `1.0`（100% 拦截/无漏防）。 |
| 11 | 外部 `--commands` JSON 中的 `TimeSec < 0` | 在步初 `nowSec == 0` 时一并夹紧为 `TimeSec = 0` 入队执行。 |
| 12 | 外部 `--commands` JSON 中的 `TimeSec >= NightDurationSec` | 夜晚在 `NightDurationSec` 结束，超出时长上限的命令不会被执行，也不会写入 `NightReplay.Commands`。 |
| 13 | 关键设施在 `t < NightDurationSec` 时全毁导致 `world.IsNightOver == true` | 循环在当前步完成后提前终止，`Report.DurationSimulatedSec = world.NowSec`，记录 `Outcome = Defeat`。 |
| 14 | `--replay-in` 文件损坏、JSON 格式错误或 `FormatVersion != 1` | 报参数/输入错误，退出码 `1`。 |
| 15 | `--replay-in` 文件中的 `LevelId` 与当前命令行 `--level` 不一致 | 若未显式传 `--level` 则自动采用 `replay.LevelId`；若显式传了不同的 `--level` 则报参数冲突，退出码 `1`。 |
| 16 | `StatsCalculator` 输入样本数 $N = 1$ | `Mean = Min = Max = P10 = P50 = P90 = P99 = x[0]`，`StdDev = 0.0`。 |
| 17 | `--out` 指定的输出文件父目录不存在 | 工具自动调用 `Directory.CreateDirectory` 创建父目录后再写入 UTF-8（无 BOM）JSON 文件。 |
| 18 | 不同操作系统的区域设置（如德语/法语小数点为逗号 `,`） | 所有工具在 `Main` 入口首行强制设置 `CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture`，确保数值解析与格式化完全一致。 |

---

## 6. 不变量

1. **模拟层零污染不变量**：`sim/` 不因工具需求引入任何 I/O、`Stopwatch` 或命令行解析依赖；所有计时、文件读写、JSON 报告组装均位于 `tools/` 工程中。
2. **输出确定性不变量**：给定相同的 `data/` 目录与相同的命令行参数，`tools/validate` 与 `tools/simrun`（除 `--bench` 墙钟耗时外）生成的 JSON 报告在跨平台（macOS ARM64 / Windows x64 / Linux x64）上**字节级完全一致**（字典键一律按 `StringComparer.Ordinal` 或枚举值升序排列，浮点数格式化在 `InvariantCulture` 下进行）。
3. **单夜与批量同源不变量**：`simrun --level L --seeds N --seed-start S` 中第 $k$ 次运行（$0 \le k < N$）产生的结果，必须与单独执行 `simrun --level L --seed <NightSeed(1, L, S+k)>` 产生的 `FinalStateChecksum`、`Outcome`、`InterceptRate` 完全相等。
4. **录像重放等价不变量（`A-2-11`）**：任何通过 `simrun --replay-out R.json` 录制的夜晚（无论使用了 `--strategy` 还是 `--commands`），立即执行 `simrun --replay-in R.json` 必须 100% 通过逐小时与终态 `StateChecksum` 校验（退出码 `0`）。
5. **事件队列有界不变量（`B-T3-06`）**：在 `simrun` 的所有运行模式中，`SimWorld` 内部未排空事件数在任意步末均 $= 0$。
6. **统计边界不变量**：对任意非空样本集，`MetricDistribution` 必满足 `Min <= P10 <= P50 <= P90 <= P99 <= Max` 且 `Min <= Mean <= Max`、`StdDev >= 0.0`。
7. **无 `Math.Hypot` 约束（`B-T3-08`）**：`tools/` 与 `sim/` 代码均面向 `.NET 8`（`net8.0`），计算二维欧氏距离时一律使用 `Math.Sqrt(dx * dx + dy * dy)`，禁止调用 `.NET 9+` 才引入的 `Math.Hypot`。
---

## 7. 测试用例（`sim.tests/ToolsSpecTests.cs`）

> 所有涉及算术、哈希与分布分位数的测试向量均由 [`tools/spec_calc/07/calc_07.py`](../../tools/spec_calc/07/calc_07.py) 验算通过。

| 编号 | 被测模块 / 规则 | 给定输入 | 预期输出（精确断言） |
|---|---|---|---|
| `T-07-01` | `ValidateRunner` 全量干净数据与 `--strict` | 标准无错无警告小型数据集 | `IsValid == true`，`Errors.Count == 0`，`Warnings.Count == 0`，默认与 `--strict` 退出码均为 `0` |
| `T-07-02` | `ValidateRunner` 时间线校验（`C-T2-08`） | 关卡 1（`2022-02-24`）可用单位含 `U08`（`firstAvailable.level == 4`），波次含 `M04`（`firstSeen == "2022-10"`）；全局目录含 `P04`（`firstSeen == "2023-03"`，晚于战役末关 `2023-01`） | 报 Error `E_TIMELINE_UNIT_UNAVAILABLE`、Error `E_TIMELINE_ENEMY_FIRST_SEEN`、Warning `W_FIRST_SEEN_NEVER_APPEARS`；`IsValid == false`，退出码 `2` |
| `T-07-03` | `ValidateRunner` 扩展静态警告（`C-T1-11`） | ① `BM` 组含非空 `waypointsM`；② `AiTag.Hunt` 波次无 `known_targets`/`air_defense` 组；③ `AiTag.Suppress` 波次无反辐射组；④ 反辐射组 `targetRule == Structure`；⑤ `storyEventOnly == true` 的 `A02` 在普通波次；⑥ `TimeStructure.E` 关卡 `supplyWindows` 为空 | 依次报 `W_IGNORED_WAYPOINTS`、`W_HUNT_NO_KNOWN_TARGETS_GROUP`、`W_SUPPRESS_NO_ARM_GROUP`、`W_ARM_STATIC_TARGET`、`W_STORY_ONLY_ENEMY_IN_NORMAL_WAVE`、`W_E_NO_SUPPLY_WINDOWS`；默认退出码 `0`，`--strict` 退出码 `2` |
| `T-07-04` | `ValidateRunner` 占空比暴露乘数漂移（`B-T3-10`） | `DutyCycle(onSec: 30, offSec: 30)`（理论占空比 $0.50$）：<br/>Case A: `exposureMult = 0.45`<br/>Case B: `exposureMult = 0.80` | Case A 漂移 $|0.45 - 0.50| = 0.05 \le 0.15$，无警告；<br/>Case B 漂移 $|0.80 - 0.50| = 0.30 > 0.15$，报 `W_EXPOSURE_MULT_DRIFT` |
| `T-07-05` | `ValidateRunner` 反导窗口过短警告（`C-T2-09`） | 关卡含可用反导单位 `U07`（`canEngageBallistic: true, reactionSec: 12.0, shotIntervalSec: 15.0`，两发最低窗口 $27.0\text{ s}$）：<br/>Case A: `BM` 从 $(10000, 20000)$ 飞向 $(10000, 0)$，$d = 20000\text{ m}, v = 2000\text{ m/s} \implies t_{\text{fly}} = 10.0\text{ s}$<br/>Case B: `BM` 从 $(30000, 60000)$ 飞向 $(30000, 0)$，$d = 60000\text{ m}, v = 2000\text{ m/s} \implies t_{\text{fly}} = 30.0\text{ s}$ | Case A 因 $10.0 < 27.0$ 报 `W_BALLISTIC_WINDOW_TOO_SHORT`；<br/>Case B 因 $30.0 \ge 27.0$ 无警告 |
| `T-07-06` | `ValidateRunner` 跨关引用与初始部署（`C-T2-04`） | `cross_level_links.json` 引用不存在的 `sourceStructureId: "S99"`；`deploy.json` 的 `initialDeployment` 将防空单位放在 `forbiddenZones` 内 | 报 `E_UNKNOWN_REF` 与 `D_FORBIDDEN_ZONE`（Severity 均为 `Error`），退出码 `2` |
| `T-07-07` | `SimRunner` 单夜运行与指标计算 | 小型关卡：刷出 `10` 个敌方目标（含 `2` 个诱饵，真实威胁 `8` 个），拦截 `6` 个真实威胁，漏防 `2` 个（`NoDetector` 1, `RollFailed` 1），被击落敌机价值 $0.30\text{ M\$}$，消耗弹药成本 $0.12\text{ M\$}$，初期总权重 $10.0$、战损权重 $2.5$ | `InterceptRate == 6.0 / 8.0 == 0.75`，`AllTargetInterceptRate == 6.0 / 10.0 == 0.60`，`ExchangeRatio == 0.30 / 0.12 == 2.50`，`WeightedLossFrac == 2.5 / 10.0 == 0.25`，退出码 `0` |
| `T-07-08` | `SimRunner` 默认种子确定性生成 | `simrun --level test_01 --night 1`（未显式传 `--seed`，默认 `campaignSeed = 1`） | `NightSeed(1, "test_01", 1) == 0x6DD180096484586DUL`（`Report.Seed == "0x6DD180096484586D"`） |
| `T-07-09` | `SimRunner` 事件队列每步排空（`B-T3-06`） | 运行 3600 步的 `test_01` 关卡，每步后检查 `world.PendingEventCount` | 全程 3600 步每步末 `PendingEventCount == 0`，且 `Report.EventCounts` 准确累计全部事件数 |
| `T-07-10` | `ReplayVerifier` 录制与重放 100% 通过（`A-2-11`） | 用 `simrun --level test_01 --seed 42 --strategy default --replay-out r.json` 录制含自动策略命令的 10800 秒单夜，再执行 `simrun --replay-in r.json` | `ReplayVerifyReport.Matched == true`，`FirstMismatchTimeSec == null`，`HourlyChecksums.Count == 3`（3600, 7200, 10800），退出码 `0` |
| `T-07-11` | `ReplayVerifier` 篡改检测与退出码 `3` | 将 `T-07-10` 生成的 `r.json` 中 `t = 7200` 处的 `StateChecksum` 异或 `0x1UL` 后传入 `simrun --replay-in` | `Matched == false`，`FirstMismatchTimeSec == 7200`，输出期望与实际摘要对比，进程返回退出码 `3` |
| `T-07-12` | `StatsCalculator` 分位数与标准差公式 | 样本 $X = [0.80, 0.60, 0.90, 0.75, 0.70]$（$N = 5$，排序后 $[0.60, 0.70, 0.75, 0.80, 0.90]$） | `Mean == 0.75`，`StdDev == 0.10`，`Min == 0.60`，`P10 == 0.64`，`P50 == 0.75`，`P90 == 0.86`，`P99 == 0.896`，`Max == 0.90` |
| `T-07-13` | `BatchRunner` 10 种子汇总统计 | 10 次运行：`InterceptRate` 为 $[0.50, 0.60, 0.65, 0.70, 0.72, 0.78, 0.80, 0.85, 0.90, 1.00]$；其中 2 次未开火（`ShotCost == 0`），其余 8 次 `ExchangeRatio` 为 $[1.2, 1.5, 1.8, 2.0, 2.4, 2.8, 3.2, 3.5]$；`WeightedLossFrac` 为 $[0.0, 0.05, 0.10, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.55]$；存活 9 次，触发暴露满值 3 次 | `InterceptRate`: `Mean = 0.75, StdDev = 0.14028542333400146, P10 = 0.59, P50 = 0.75, P90 = 0.91`；<br/>`ExchangeRatio`（$N=8$）: `Mean = 2.30, P50 = 2.20, P10 = 1.41, P90 = 3.29`；<br/>`WeightedLossFrac`: `Mean = 0.21, P50 = 0.175`；<br/>`SurvivalRate = 0.90`，`Exposure100TriggerRate = 0.30` |
| `T-07-14` | `BatchRunner` 辐射暴露校准比（`B-T3-10`） | 雷达单位在 `always_emit` 下平均全夜累积暴露 `120.0`，在 `DutyCycle(exposureMult: 0.45)` 下实测平均累积暴露 `56.4` | `EmpiricalExposureRatio == 56.4 / 120.0 == 0.47`，`AbsoluteDrift == |0.45 - 0.47| == 0.02 <= 0.15` |
| `T-07-15` | `BenchRunner` 合格判定（`C-T2-02`, `C-T1-14`） | 100 步采样：95 步 `1.0 ms`、4 步 `2.0 ms`、1 步 `3.5 ms`；交战分配子步骤均值 `0.18 ms` | `StepWallMs`: `Mean == 1.065 ms < 2.0`，`P50 == 1.0 ms`，`P99 == 2.015 ms < 4.0`，`Max == 3.5 ms < 50.0`；`EngagementAllocationMeanMs == 0.18 <= 0.30` $\implies$ `Passed == true`，退出码 `0` |
| `T-07-16` | `BenchRunner` P99 超标门禁（退出码 `4`） | 100 步采样：98 步 `1.5 ms`、2 步 `6.0 ms`（阈值 `MaxP99 = 4.0 ms`） | `StepWallMs.P99 == 6.0 ms >= 4.0 ms` $\implies$ `Passed == false`，`Violations` 非空，进程返回退出码 `4` |
| `T-07-17` | 单夜与批量种子一致性不变量 | 执行 `simrun --level test_01 --seeds 5 --seed-start 10`，并与逐个执行 `--seed <NightSeed(1, "test_01", 10..14)>` 对比 | 5 个种子的 `FinalStateChecksum`、`InterceptRate`、`Outcome` 与单夜独立运行 100% 相等 |
| `T-07-18` | CLI 参数校验与错误退出码 `1` | ① 同时传 `--seed 1 --seeds 10`；② 传未知策略 `--strategy magic`；③ 传 `--seeds 0` | 均向 `stderr` 输出明确错误提示，进程退出码均为 `1` |

---

## 8. 已决问题与跨规格契约

### 8.1 已决设计问题

| # | 问题 | 决议 |
|---|---|---|
| Q1 | 是否单独设立 `tools/balance` 可执行工程？ | **否**。遵循 WBS 06.A WS06-007 与 `C-T1-15` 决议，批量模拟与统计直接作为 `tools/simrun` 的 `--seeds <N>` 模式实现，避免维护两套重复的 `SimWorld` 驱动壳。 |
| Q2 | 分位数（`P10` / `P50` / `P90` / `P99`）采用离散最近邻还是连续线性插值？ | 采用 **Type-7 连续线性插值**（$h = p(N-1)$，与 NumPy `np.percentile(..., method='linear')` 及 Excel `PERCENTILE.INC` 完全一致），在小样本（如 $N=5, 10$）与大样本（$N=100, 18000$）下均连续且无跳变。 |
| Q3 | 单夜或批量某局未发射任何拦截弹（`TotalShotCostMusd == 0`）时费效比如何表示？ | JSON 不支持 `NaN` / `Infinity`；单夜报告 `ExchangeRatio` 设为 `null`，批量报告仅对 `TotalShotCostMusd > 0` 的有效开火局统计 `ExchangeRatio` 分布（若全部未开火则为 `null`）。 |
| Q4 | `stress_50x15x20` 性能基准场景是否依赖 `data/levels/` 下的正式关卡文件？ | **不依赖**。由 `SyntheticScenarioBuilder` 在内存中用最小合成定义构造 50 威胁 + 15 火力 + 20 传感器的确定性高压世界，使 WS01-028 在 M1 阶段（正式关卡数据尚未制作前）即可独立执行并作为 CI 门禁。 |

### 8.2 跨规格契约核对表

| 对接文件 | 契约点 | 状态 |
|---|---|---|
| [`00_core.md`](00_core.md) | `DataLoader` 错误码 `E_*`、`DeploymentValidator` 错误码 `D_*`、`SimRng.NightSeed`、`SimWorld.ComputeStateChecksum`、`NightReplay` 格式、单步 `< 2.0 ms / P99 < 4.0 ms` 预算 | 已对齐 |
| [`01_time_map_movement_waves.md`](01_time_map_movement_waves.md) | `BM`/`HBM`/`GB` 忽略 `waypointsM`（`W_IGNORED_WAYPOINTS`）、`storyEventOnly`（`W_STORY_ONLY_ENEMY_IN_NORMAL_WAVE`）、地图尺寸与弹道飞行窗口（`W_BALLISTIC_WINDOW_TOO_SHORT`） | 已对齐 |
| [`02_sensing_tracks_ew_emission.md`](02_sensing_tracks_ew_emission.md) | `DutyCycle` 占空比与 `exposureMult` 漂移检查（`W_EXPOSURE_MULT_DRIFT`）、实测暴露比校准（`ExposureCalibration`）、`CoverageQuery.ComputeGrid` 三态（`0 / 1 / 2`）契约 | 已对齐 |
| [`03_engagement_weapons_collateral.md`](03_engagement_weapons_collateral.md) | 便宜优先交战分配子步骤耗时监控 `EngagementAllocationMeanMs <= 0.3 ms`、`EnemyLeakedEvent(LeakReason)` 分类统计 | 已对齐 |
| [`04_layered_defense_decoys_saturation_ai.md`](04_layered_defense_decoys_saturation_ai.md) | `AiTag.Hunt` / `AiTag.Suppress` 与反辐射目标规则静态检查（`W_HUNT_NO_KNOWN_TARGETS_GROUP`、`W_SUPPRESS_NO_ARM_GROUP`、`W_ARM_STATIC_TARGET`）、单位暴露满 100 触发率统计 | 已对齐 |
| [`05_campaign_economy.md`](05_campaign_economy.md) | `CampaignDataLoader`、`cross_level_links.json` 校验、`TimeStructure.E` 补给窗口检查（`W_E_NO_SUPPLY_WINDOWS`）、历史事件停用单位警告（`W_HISTORICAL_UNIT_UNAVAILABLE`）、单夜战果与战损权重 | 已对齐 |
| [`06_client_graybox.md`](06_client_graybox.md) | `SimWorld.DrainEvents()` 每步排空契约、`CoverageQuery.ComputeGrid` 三态返回码（`0 / 1 / 2`） | 已对齐 |
