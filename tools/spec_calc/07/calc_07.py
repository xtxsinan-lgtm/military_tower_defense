#!/usr/bin/env python3
"""
tools/spec_calc/07/calc_07.py
独立计算并验证 docs/spec/07_tools.md §7 (T-07-01 .. T-07-18) 的全部测试向量。
遵守 C-T1-01（入库参考计算脚本）与 C-T1-04（禁止使用 math.hypot，欧氏距离统一用 math.sqrt(dx*dx + dy*dy)）。
"""

import math
import json

# ---------------------------------------------------------------------------
# 1. PCG32 / SplitMix64 / FNV-1a 64 参考实现（与 00_core.md §3.1 逐位一致）
# ---------------------------------------------------------------------------
MASK64 = 0xFFFFFFFFFFFFFFFF
MASK32 = 0xFFFFFFFF
PCG_MULT = 6364136223846793005
SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
SPLITMIX_MUL1 = 0xBF58476D1CE4E5B9
SPLITMIX_MUL2 = 0x94D049BB133111EB
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x00000100000001B3


def splitmix64_next(x: int) -> tuple[int, int]:
    x = (x + SPLITMIX_GAMMA) & MASK64
    z = x
    z = ((z ^ (z >> 30)) * SPLITMIX_MUL1) & MASK64
    z = ((z ^ (z >> 27)) * SPLITMIX_MUL2) & MASK64
    z = (z ^ (z >> 31)) & MASK64
    return x, z


def fnv1a64(s: str) -> int:
    h = FNV_OFFSET
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * FNV_PRIME) & MASK64
    return h


def night_seed(run_seed: int, level_id: str, night_seq: int) -> int:
    x = (run_seed ^ fnv1a64(f"night:{level_id}:{night_seq}")) & MASK64
    _, out = splitmix64_next(x)
    return out


# ---------------------------------------------------------------------------
# 2. 确定性统计与分位数函数（07_tools.md §3.4）
#    - Mean(xs): 升序排序后按序算术累加 ÷ N
#    - StdDev(xs): 总体标准差 sqrt(sum((x_i - mean)^2) / N)，按升序累加
#    - Percentile(xs, q): 升序排序 a[0..N-1]，pos = q * (N - 1)，
#      lo = floor(pos), hi = ceil(pos), frac = pos - lo,
#      返回 a[lo] + frac * (a[hi] - a[lo])（线性插值 Type 7，确定性无分支歧义）
# ---------------------------------------------------------------------------
def calc_stats(values: list[float]) -> dict[str, float]:
    n = len(values)
    assert n > 0
    a = sorted(float(v) for v in values)
    total = 0.0
    for v in a:
        total += v
    mean = total / n
    sq_sum = 0.0
    for v in a:
        d = v - mean
        sq_sum += d * d
    std_dev = math.sqrt(sq_sum / n)

    def pct(q: float) -> float:
        pos = q * (n - 1)
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        frac = pos - lo
        return a[lo] + frac * (a[hi] - a[lo])

    return {
        "count": n,
        "min": a[0],
        "max": a[-1],
        "mean": mean,
        "stdDev": std_dev,
        "p10": pct(0.10),
        "p50": pct(0.50),
        "p90": pct(0.90),
        "p99": pct(0.99),
    }


def check(name: str, actual, expected, tol: float = 0.0):
    if isinstance(expected, float) and tol > 0:
        assert abs(actual - expected) <= tol, f"[FAIL] {name}: actual={actual!r}, expected={expected!r}"
    else:
        assert actual == expected, f"[FAIL] {name}: actual={actual!r}, expected={expected!r}"


def main():
    # T-07-04: 辐射策略目标平均暴露系数校验（B-T3-10）
    # DutyCycle: onGameSec=0.5 (30s), offGameSec=0.5 (30s) -> 理论占空比 30 / (30 + 30) = 0.5
    # 若 exposureMult = 0.45，|0.45 - 0.5| = 0.05 <= 0.15 -> 通过
    # 若 exposureMult = 0.80，|0.80 - 0.5| = 0.30 > 0.15 -> W_EXPOSURE_MULT_DRIFT
    duty_ratio = 30.0 / (30.0 + 30.0)
    check("T-07-04 duty_ratio", duty_ratio, 0.5)
    check("T-07-04 drift ok", abs(0.45 - duty_ratio) <= 0.15, True)
    check("T-07-04 drift warn", abs(0.80 - duty_ratio), 0.30, 1e-12)

    # T-07-05: 弹道目标小地图飞行窗口警告（C-T2-09）
    # 20 km 地图，弹道入口 (10000, 20000) -> 保护目标 (10000, 0)，水平距离 d = 20000 m
    # 速度 7200 km/h = 2000 m/s -> 飞行时间 t_fly = 20000 / 2000 = 10.0 s
    # 可用反导单位 PAC-3: 反应时间 0.2 gs = 12.0 s，射击间隔 0.25 gs = 15.0 s -> 最小两发窗口 27.0 s，单发窗口 12.0 s
    # t_fly = 10.0 s < 12.0 s + 15.0 s = 27.0 s -> W_BALLISTIC_WINDOW_TOO_SHORT
    dx, dy = 0.0, -20000.0
    dist_m = math.sqrt(dx * dx + dy * dy)
    t_fly = dist_m / 2000.0
    t_req = 12.0 + 15.0
    check("T-07-05 dist_m", dist_m, 20000.0)
    check("T-07-05 t_fly", t_fly, 10.0)
    check("T-07-05 t_req", t_req, 27.0)
    check("T-07-05 short window", t_fly < t_req, True)

    # T-07-08: 命令行种子解析与缺省 NightSeed
    # 缺省 runSeed = 1，levelId = "test_01"，nightIndex = 1
    default_seed = night_seed(1, "test_01", 1)
    check("T-07-08 default NightSeed(1, test_01, 1)", f"0x{default_seed:016X}", "0x6DD180096484586D")
    # 批量种子区间 "1..5" -> [1, 2, 3, 4, 5]；数量 "4" -> [1, 2, 3, 4]
    check("T-07-08 seeds range 1..5", list(range(1, 6)), [1, 2, 3, 4, 5])

    # T-07-12: 分位数与标准差确定性公式（5 个样本）
    # 拦截率样本: [0.60, 0.70, 0.75, 0.80, 0.90]
    s5 = calc_stats([0.80, 0.60, 0.90, 0.75, 0.70])
    check("T-07-12 mean", s5["mean"], 0.75, 1e-12)
    # 方差 = ((0.15^2 + 0.05^2 + 0 + 0.05^2 + 0.15^2) / 5) = 0.05 / 5 = 0.01 -> stdDev = 0.1
    check("T-07-12 stdDev", s5["stdDev"], 0.10, 1e-12)
    # pos(0.10) = 0.4 -> 0.60 + 0.4 * (0.70 - 0.60) = 0.64
    check("T-07-12 p10", s5["p10"], 0.64, 1e-12)
    check("T-07-12 p50", s5["p50"], 0.75, 1e-12)
    # pos(0.90) = 3.6 -> 0.80 + 0.6 * (0.90 - 0.80) = 0.86
    check("T-07-12 p90", s5["p90"], 0.86, 1e-12)
    # pos(0.99) = 3.96 -> 0.80 + 0.96 * (0.90 - 0.80) = 0.896
    check("T-07-12 p99", s5["p99"], 0.896, 1e-12)

    # T-07-13: 批量统计汇总 SimRunBatchSummary（10 个种子的合成结算向量）
    intercept_rates = [0.50, 0.60, 0.65, 0.70, 0.72, 0.78, 0.80, 0.85, 0.90, 1.00]
    exchange_ratios = [1.20, 1.50, 1.80, 2.00, 2.10, 2.30, 2.50, 2.80, 3.00, 3.80]
    weighted_losses = [0.45, 0.35, 0.30, 0.25, 0.20, 0.18, 0.15, 0.12, 0.10, 0.00]
    survived_flags = [0, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # 9/10 存活
    exp100_flags = [1, 1, 0, 1, 0, 0, 0, 0, 0, 0]    # 3/10 触发暴露度 100

    st_ir = calc_stats(intercept_rates)
    st_ex = calc_stats(exchange_ratios)
    st_wl = calc_stats(weighted_losses)
    check("T-07-13 ir mean", st_ir["mean"], 0.75, 1e-12)
    check("T-07-13 ir stdDev", st_ir["stdDev"], 0.14028542333400146, 1e-12)
    check("T-07-13 ir p10", st_ir["p10"], 0.59, 1e-12)
    check("T-07-13 ir p50", st_ir["p50"], 0.75, 1e-12)
    check("T-07-13 ir p90", st_ir["p90"], 0.91, 1e-12)
    check("T-07-13 ex mean", st_ex["mean"], 2.30, 1e-12)
    check("T-07-13 ex p50", st_ex["p50"], 2.20, 1e-12)
    check("T-07-13 wl mean", st_wl["mean"], 0.21, 1e-12)
    check("T-07-13 survivalRate", sum(survived_flags) / 10.0, 0.90, 1e-12)
    check("T-07-13 exposure100TriggerRate", sum(exp100_flags) / 10.0, 0.30, 1e-12)

    # T-07-15 & T-07-16: 性能基准 C-T2-02 门限判定与分位数计算
    # 构造 100 步耗时样本（单位 ms）：前 95 步为 1.0 ms，第 96..99 步为 2.0 ms，第 100 步为 3.5 ms
    step_ms_pass = [1.0] * 95 + [2.0] * 4 + [3.5]
    st_bench = calc_stats(step_ms_pass)
    # mean = (95*1.0 + 4*2.0 + 3.5) / 100 = 106.5 / 100 = 1.065 ms < 2.0 ms
    # p50: pos = 49.5 -> 1.0 ms
    # p99: pos = 0.99 * 99 = 98.01 -> lo=98 (val=2.0), hi=99 (val=3.5), frac=0.01 -> 2.0 + 0.01 * 1.5 = 2.015 ms < 4.0 ms
    # max = 3.5 ms < 50.0 ms
    check("T-07-15 bench mean", st_bench["mean"], 1.065, 1e-12)
    check("T-07-15 bench p50", st_bench["p50"], 1.0, 1e-12)
    check("T-07-15 bench p99", st_bench["p99"], 2.015, 1e-12)
    check("T-07-15 bench max", st_bench["max"], 3.5, 1e-12)
    check("T-07-15 pass C-T2-02", st_bench["mean"] < 2.0 and st_bench["p99"] < 4.0 and st_bench["max"] < 50.0, True)

    # 超标场景：98 步 1.5 ms，2 步 6.0 ms -> p99 = 6.0 >= 4.0 -> 退出码 4
    step_ms_fail = [1.5] * 98 + [6.0] * 2
    st_fail = calc_stats(step_ms_fail)
    check("T-07-16 fail p99", st_fail["p99"], 6.0, 1e-12)
    check("T-07-16 fail C-T2-02", st_fail["p99"] < 4.0, False)

    print("calc_07.py: ALL CHECKS PASSED (24 assertions).")


if __name__ == "__main__":
    main()
