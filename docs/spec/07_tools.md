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
