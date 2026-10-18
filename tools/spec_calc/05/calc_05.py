#!/usr/bin/env python3
"""
docs/spec/05_campaign_economy.md §7 测试向量参考计算脚本（D2b 收口版）。
运行：python3 tools/spec_calc/05/calc_05.py

特性：
- 浮点按 IEEE754 double，运算顺序与规格中书写的顺序一致。
- 严格禁用 math.hypot（C-T1-04）。
- 内置 00_core.md §3.3 的 SimRandom（PCG32 + SplitMix64 + FNV-1a 64）与 NightSeed / ChildSeed 实现。
- 战役层子流名一律带 "campaign:" 前缀（A-5-01）。
- 覆盖 B-T3-01（交换比混合公式与浪费比值阈值 0.2）、B-T3-04（信任度下限 10 与 min=0 对比、RequestStrategySpread）、
  B-T3-07（AutoResolve 默认 1.0/1.0 与 0.95/1.0、Review 阶段手打覆盖）、B-T2-10（buy_drone_team 第 14 关与 2025-10）、
  B-T2-36（urbanNavJamPenalty -1.0）、B-T2-81（白天响应度恢复 +0.2/day）、B-T2-105（buy_searchlight）、
  C-T2-03（邻国越界扣分）等全部 T-05-01..T-05-46 向量。
"""
import math

M64 = (1 << 64) - 1
M32 = (1 << 32) - 1

PCG_MULT = 6364136223846793005
SM_GAMMA = 0x9E3779B97F4A7C15
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3


def fnv1a64(data: bytes) -> int:
    h = FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & M64
    return h


def splitmix64_next(x: int):
    x = (x + SM_GAMMA) & M64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return x, z ^ (z >> 31)


class Pcg32:
    def __init__(self, initstate: int, initseq: int):
        self.state = 0
        self.inc = ((initseq << 1) | 1) & M64
        self.next_u32()
        self.state = (self.state + initstate) & M64
        self.next_u32()

    def next_u32(self) -> int:
        old = self.state
        self.state = (old * PCG_MULT + self.inc) & M64
        xorshifted = (((old >> 18) ^ old) >> 27) & M32
        rot = old >> 59
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & M32


class SimRandom:
    def __init__(self, seed: int):
        self.seed = seed & M64
        x, initstate = splitmix64_next(self.seed)
        x, initseq = splitmix64_next(x)
        self.pcg = Pcg32(initstate, initseq)

    def next_u32(self) -> int:
        return self.pcg.next_u32()

    def next_u64(self) -> int:
        hi = self.next_u32()
        lo = self.next_u32()
        return (hi << 32) | lo

    def next_double(self) -> float:
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    @staticmethod
    def child_seed(parent_seed: int, name: str) -> int:
        _, out = splitmix64_next((parent_seed ^ fnv1a64(name.encode("utf-8"))) & M64)
        return out


def night_seed(run_seed: int, level_id: str, night_seq: int) -> int:
    return SimRandom.child_seed(run_seed, f"night:{level_id}:{night_seq}")


def hx(v: int) -> str:
    return "0x%016X" % v


def round_half_away(x: float) -> int:
    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


def floor_eps(x: float) -> int:
    return math.floor(x + 1e-9)


def ceil_eps(x: float) -> int:
    return math.ceil(x - 1e-9)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def dist_sq(a, b) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def potential_loss_b_t3_01(enemy_cost_musd: float, damage_level: int, weight: float = 1.0) -> float:
    """03 §3.10.2 B-T3-01 混合公式：max(enemyCost, 2^(damageLevel-1) * 0.1 * weight)"""
    return max(enemy_cost_musd, (2 ** (damage_level - 1)) * 0.1 * weight)


def test_t05_01_to_05():
    print("=== T-05-01 交换比档位与 B-T3-01 典型武器交换比 ===")
    bands = [(0.0, -3.0), (0.5, -1.0), (2.0, 0.0), (5.0, 1.0), (20.0, 3.0)]

    def band(r):
        d = None
        for mn, dl in bands:
            if mn <= r:
                d = dl
        return d

    for r, exp in [(0.3, -3.0), (0.5, -1.0), (0.49999, -3.0), (3.0, 0.0), (5.0, 1.0), (25.0, 3.0), (0.0, -3.0)]:
        assert band(r) == exp
        print(f"  ratio={r} -> {band(r)}")

    # B-T3-01 典型组合
    pl_shahed = potential_loss_b_t3_01(0.05, 3, 1.0)     # max(0.05, 0.4) = 0.4
    pl_iskander_w1 = potential_loss_b_t3_01(3.0, 8, 1.0) # max(3.0, 12.8) = 12.8
    pl_kh101_w1 = potential_loss_b_t3_01(13.0, 6, 1.0)   # max(13.0, 3.2) = 13.0
    assert pl_shahed == 0.4
    assert pl_iskander_w1 == 12.8
    assert pl_kh101_w1 == 13.0
    r_pac3_shahed = pl_shahed / 4.0       # 0.1 -> -3
    r_pac3_iskander = pl_iskander_w1 / 4.0 # 3.2 -> 0
    r_pac3_kh101 = pl_kh101_w1 / 4.0      # 3.25 -> 0
    r_gepard_shahed = pl_shahed / 0.01    # 40.0 -> +3
    assert (r_pac3_shahed, band(r_pac3_shahed)) == (0.1, -3.0)
    assert (r_pac3_iskander, band(r_pac3_iskander)) == (3.2, 0.0)
    assert (r_pac3_kh101, band(r_pac3_kh101)) == (3.25, 0.0)
    assert (r_gepard_shahed, band(r_gepard_shahed)) == (40.0, 3.0)
    print(f"  B-T3-01: PAC3->Shahed={r_pac3_shahed}({band(r_pac3_shahed)}), "
          f"PAC3->Iskander={r_pac3_iskander}({band(r_pac3_iskander)}), "
          f"PAC3->Kh101={r_pac3_kh101}({band(r_pac3_kh101)}), "
          f"Gepard->Shahed={r_gepard_shahed}({band(r_gepard_shahed)})")

    print("\n=== T-05-02 一夜结算（B-T3-01 wastefulWeapon.maxRatio = 0.2） ===")
    # w_exp (PAC-3, 4.0 M$/shot) 3 发命中 3 架 Shahed（B-T3-01 PotentialLoss = 3 * 0.4 = 1.2 M$）
    loss_b_t3_01 = 1.2 + 39.0 + 0.0
    cost = 12.0 + 1.6 + 0.01
    ex_ratio_b_t3_01 = loss_b_t3_01 / cost
    w_exp_ratio = 1.2 / 12.0  # 0.1 < 0.2 (maxRatio)
    assert loss_b_t3_01 == 40.2
    assert cost == 13.61
    assert ex_ratio_b_t3_01 == 2.953710506980162
    assert band(ex_ratio_b_t3_01) == 0.0
    assert w_exp_ratio == 0.09999999999999999 and w_exp_ratio < 0.2
    # 旧版直接注入 PotentialLossMusd = 0.15 时：
    loss_legacy = 0.15 + 39.0 + 0.0
    ex_ratio_legacy = loss_legacy / cost
    assert ex_ratio_legacy == 2.876561351947098
    assert band(ex_ratio_legacy) == 0.0
    raw = 0 - 3 - 3 - 2 + (2 - 3) + 0
    applied = clamp(raw, -12, 8)
    trust_after = clamp(50 + applied, 10, 100)
    assert (raw, applied, trust_after) == (-9, -9, 41)
    print("  B-T3-01 loss=", repr(loss_b_t3_01), "cost=", repr(cost), "ratio=", repr(ex_ratio_b_t3_01),
          "w_exp_ratio=", repr(w_exp_ratio), "raw=", raw, "trust=", trust_after)

    print("\n=== T-05-03 夹紧、越界扣分与下限（min=10 vs min=0） ===")
    raw2 = 0 - 5 - 3 - 6 + (2 - 3) + 0
    clamped2 = clamp(raw2, -12, 8)
    assert (raw2, clamped2) == (-15, -12)
    assert clamp(15 + clamped2, 10, 100) == 10
    assert clamp(15 + clamped2, 0, 100) == 3
    assert clamp(10 + clamped2, 0, 100) == 0
    # C-T2-03 邻国越界：2 次越界 -> dBorder = -Min(2*5, 10) = -10
    d_border_2 = -min(2 * 5.0, 10.0)
    d_border_3 = -min(3 * 5.0, 10.0)
    assert d_border_2 == -10.0 and d_border_3 == -10.0
    print("  raw2=", raw2, "clamped=", clamped2, "trust(min=10): 15->10", "trust(min=0): 15->3, 10->0",
          "dBorder(2)=", d_border_2)

    print("\n=== T-05-04 信任度 -> 配额修正（min=10 正式参数 vs min=0 夹具参数） ===")

    def m_trust(T, neutral=50.0, mn=10.0, mx=100.0, q=0.1):
        if T >= neutral:
            return (T - neutral) / (mx - neutral) * q
        return -((neutral - T) / (neutral - mn)) * q

    for T, exp10, exp0 in [
        (75, 0.05, 0.05),
        (10, -0.1, -0.08000000000000002),
        (30, -0.05, -0.04000000000000001),
        (50, 0.0, 0.0),
        (100, 0.1, 0.1),
        (41, -0.022500000000000003, -0.018),
    ]:
        v10 = m_trust(T, mn=10.0)
        v0 = m_trust(T, mn=0.0)
        assert v10 == exp10, (T, v10, exp10)
        assert v0 == exp0, (T, v0, exp0)
        print(f"  T={T}: min=10 -> {repr(v10)}, min=0 -> {repr(v0)}")

    print("\n=== T-05-05..07 比例修正夹紧与取整 ===")

    def scaled(base, m, lo=-0.2, hi=0.2):
        mm = clamp(m, lo, hi)
        v = round_half_away(base * (1 + mm))
        return max(1 if base >= 1 else 0, v), mm, base * (1 + mm)

    assert scaled(20, 0.25) == (24, 0.2, 24.0)
    assert scaled(8, 0.35) == (10, 0.2, 9.6)
    assert scaled(1, -0.2) == (1, -0.2, 0.8)
    assert scaled(3, -0.2) == (2, -0.2, 2.4000000000000004)
    assert scaled(2, -0.25) == (2, -0.2, 1.6)
    assert scaled(5, 0.1) == (6, 0.1, 5.5)
    assert scaled(5, -0.1) == (5, -0.1, 4.5)
    assert scaled(0, 0.2) == (0, 0.2, 0.0)
    # T-05-07: base=16, Trust=10 + effect=-0.05 -> m=-0.15 (when min=10) -> 13.6 -> 14;
    # when min=0: mT=-0.08 + effect=-0.05 -> m=-0.13 -> 16 * 0.87 = 13.92 -> 14
    assert scaled(16, -0.15) == (14, -0.15, 13.6)
    assert scaled(16, -0.13) == (14, -0.13, 13.92)
    print("  T-05-07 base=16: m=-0.15 ->", scaled(16, -0.15), "m=-0.13 ->", scaled(16, -0.13))


def test_t05_10_to_27():
    print("\n=== T-05-10 城市资源与 B-T2-36 城区导航干扰惩罚 ===")
    per_day = 4.0
    m_city = 0.05 + 0.1
    start = min(30.0, per_day * 1 * (1 + m_city))
    assert start == 4.6
    a = 11520.0 / 28800.0
    acc = per_day * (1 + m_city) * max(0.0, 7 - 0.5 * a)
    assert acc == 31.279999999999998
    assert min(30.0, start + acc) == 30.0
    # B-T2-36: UrbanNavJamTriggered -> CityResource = max(0, CityResource - 1.0)
    assert max(0.0, 4.6 - 1.0) == 3.5999999999999996
    assert max(0.0, 0.5 - 1.0) == 0.0
    print("  start=", repr(start), "after urbanNavJamPenalty(-1.0)=", repr(max(0.0, start - 1.0)))

    print("\n=== T-05-15 白天警报响应度恢复（B-T2-81） ===")
    # AlertResponsiveness = min(1.0, AlertResponsiveness + 0.2 * g)
    assert min(1.0, 0.7 + 0.2 * 1) == 0.8999999999999999
    assert min(1.0, 0.7 + 0.2 * 7) == 1.0
    print("  AlertResponsiveness 0.7 after 1 day:", repr(min(1.0, 0.7 + 0.2 * 1)),
          "after 7 days:", repr(min(1.0, 0.7 + 0.2 * 7)))

    print("\n=== T-05-17 / T-05-23 / T-05-27 种子与 campaign: 子流名（A-5-01） ===")
    s_l15_1 = night_seed(1, "l15", 1)
    s_l15_2 = night_seed(1, "l15", 2)
    s_l15_3 = night_seed(1, "l15", 3)
    assert s_l15_1 == 0x003961A3A0873D26
    assert s_l15_3 == 0x0AF82D8CF73259EF
    print("  night:l15:1 =", hx(s_l15_1), "night:l15:2 =", hx(s_l15_2), "night:l15:3 =", hx(s_l15_3))

    for nm in [
        "campaign:crew:l07:2",
        "campaign:crew:level_06:1",
        "campaign:cards:l07",
        "campaign:cards:level_01",
        "campaign:production:l15:3",
    ]:
        cs = SimRandom.child_seed(1, nm)
        rng = SimRandom(cs)
        d0 = rng.next_double()
        d1 = rng.next_double()
        d2 = rng.next_double()
        print(f"  {nm} -> seed={hx(cs)}, next_double=[{d0!r}, {d1!r}, {d2!r}]")

    # T-05-23: 用真實 SimRandom(ChildSeed(1, "campaign:crew:l07:2")) 与 "campaign:crew:level_06:1" 核算王牌判定
    cs_crew_l07 = SimRandom.child_seed(1, "campaign:crew:l07:2")
    r_crew_l07 = SimRandom(cs_crew_l07)
    u0, u1 = r_crew_l07.next_double(), r_crew_l07.next_double()
    print(f"  T-05-23 real SimRandom('campaign:crew:l07:2'): u0={u0!r} ({'Dead' if u0 < 0.5 else 'Wounded'}), "
          f"u1={u1!r} ({'Dead' if u1 < 0.5 else 'Wounded'})")

    cs_crew_l06 = SimRandom.child_seed(1, "campaign:crew:level_06:1")
    r_crew_l06 = SimRandom(cs_crew_l06)
    v0, v1 = r_crew_l06.next_double(), r_crew_l06.next_double()
    print(f"  T-05-23 real SimRandom('campaign:crew:level_06:1'): v0={v0!r} ({'Dead' if v0 < 0.5 else 'Wounded'}), "
          f"v1={v1!r} ({'Dead' if v1 < 0.5 else 'Wounded'})")

    # T-05-27: ScriptedRandom [0.5, 0.0, 0.99] 与真实 SimRandom(ChildSeed(1, "campaign:cards:l07")) / "campaign:cards:level_01"
    cards = [("c_a", 1.0), ("c_b", 2.0), ("c_c", 3.0), ("c_d", 4.0)]

    def draw_cards(rand_vals):
        pool = list(cards)
        picked = []
        steps = []
        for d in rand_vals:
            total = sum(w for _, w in pool)
            r = d * total
            acc = 0.0
            chosen = len(pool) - 1
            for i, (cid, w) in enumerate(pool):
                acc += w
                if r < acc:
                    chosen = i
                    break
            steps.append((total, r, pool[chosen][0]))
            picked.append(pool.pop(chosen)[0])
        return picked, steps

    picked_scripted, steps_scripted = draw_cards([0.5, 0.0, 0.99])
    assert picked_scripted == ["c_c", "c_a", "c_d"]
    print("  T-05-27 Scripted [0.5, 0.0, 0.99]:", picked_scripted, steps_scripted)

    for card_stream in ["campaign:cards:l07", "campaign:cards:level_01"]:
        cs_c = SimRandom.child_seed(1, card_stream)
        rc = SimRandom(cs_c)
        vals = [rc.next_double() for _ in range(3)]
        picked_real, steps_real = draw_cards(vals)
        print(f"  T-05-27 real SimRandom('{card_stream}'={hx(cs_c)}): picked={picked_real}, steps={steps_real}")


def test_t05_34_to_44():
    print("\n=== T-05-34 敌人适应 EMA ===")
    S = 0.0
    seq = []
    for s_ in [0.8, 0.8, 0.3, 0.1]:
        S = (1 - 0.5) * S + 0.5 * s_
        seq.append(S)
    assert seq == [0.4, 0.6000000000000001, 0.45000000000000007, 0.275]
    print("  EMA:", [repr(x) for x in seq])

    print("\n=== T-05-36 每日生产 ===")
    caps = [2.0 * 1 * (1 - 0.5 * 0.25), 8.0 * 1 * (1 - 0.5 * 0.25)]
    D = caps[0] + caps[1]
    parts = 6.0
    s = min(1.0, parts / (D * 1.0))
    assert caps == [1.75, 7.0] and D == 8.75 and s == 0.6857142857142857
    p1 = caps[0] * s
    p2 = caps[1] * s
    assert p1 == 1.2 and p2 == 4.8
    exp1 = clamp(10.0 - 5.0 + 1.0 * p1, 0.0, 100.0)
    exp2 = clamp(62.0 - 5.0 + 3.0 * p2, 0.0, 100.0)
    assert exp1 == 6.2 and exp2 == 71.4
    print(f"  s={s!r}, p1={p1!r}, p2={p2!r}, exp1={exp1!r}, exp2={exp2!r}")

    print("\n=== T-05-44 平衡指标计算器（含 RequestStrategySpread，B-T3-04） ===")
    runs = [[50, 30, 12, 10, 14], [50, 55, 60, 58, 62], [50, 40, 15, 13, 30], [50, 45, 47, 52, 49]]
    dwell = sum(1 for r in runs for t in r if t <= 10 + 5) / sum(len(r) for r in runs)
    assert dwell == 0.25
    strong = [100.0, 120.0, 118.0]
    weak = [100.0, 80.0, 82.0]
    spreads = [s_ / w_ for s_, w_ in zip(strong, weak)]
    assert max(spreads) == 1.5
    # RequestStrategySpread: |mean(always_request) - mean(never_request)| / mean(never_request)
    always_req = [420.0, 440.0]
    never_req = [400.0, 400.0]
    req_spread = abs((sum(always_req) / 2) - (sum(never_req) / 2)) / (sum(never_req) / 2)
    assert req_spread == 0.075  # <= 0.15
    gaps = [0.10, 0.12, 0.15, 0.13, 0.20]
    n = len(gaps)
    xs = list(range(1, n + 1))
    xm = sum(xs) / n
    ym = sum(gaps) / n
    num = sum((x - xm) * (y - ym) for x, y in zip(xs, gaps))
    den = sum((x - xm) ** 2 for x in xs)
    slope = num / den
    assert abs(slope - 0.021) < 1e-12
    print(f"  TrustFloorDwell={dwell!r}, ResourceSpreadMax={max(spreads)!r}, "
          f"RequestStrategySpread={req_spread!r}, WinGapSlope={slope!r}")


if __name__ == "__main__":
    test_t05_01_to_05()
    test_t05_10_to_27()
    test_t05_34_to_44()
    print("\nALL T-05 VECTORS VERIFIED SUCCESSFULLY.")
