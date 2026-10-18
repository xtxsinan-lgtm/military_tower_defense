#!/usr/bin/env python3
"""
03 规格（交战、拦截、落地、支援、电网、警报与评分）测试用例预期值计算与等价性校验脚本（D2b-03）。
运行：python3 tools/spec_calc/03/calc_03.py
"""
import math

EPS = 1e-9
BISECTION_ITERS = 32  # C-T2-10: 由 48 改为 32


def solve(origin, speed, R, C, predict, sample=1.0, iters=BISECTION_ITERS, max_speed_3d=None):
    """
    InterceptSolver.Solve:
    - max_speed_3d is None: 朴素实现（从 k = 1 开始采样）
    - max_speed_3d is not None: 加速实现（C-T1-05，从 k0 = max(1, floor(d3D_0 / (speed + max_speed_3d))) 开始采样）
    """
    def reach(t):
        pos, alt, arrived = predict(t)
        dx = pos[0] - origin[0]
        dy = pos[1] - origin[1]
        h2 = dx * dx + dy * dy
        d = math.sqrt(h2 + alt * alt)
        return speed * t + EPS >= d

    tmax = math.sqrt(R * R + C * C) / speed
    K = math.ceil(tmax / sample - 1e-9)
    if K < 1:
        K = 1

    if max_speed_3d is not None:
        pos0, alt0, arr0 = predict(0.0)
        if arr0:
            return None
        dx0 = pos0[0] - origin[0]
        dy0 = pos0[1] - origin[1]
        d3d_0 = math.sqrt(dx0 * dx0 + dy0 * dy0 + alt0 * alt0)
        k0 = max(1, int(math.floor(d3d_0 / ((speed + max(0.0, max_speed_3d)) * sample))))
    else:
        k0 = 1

    if k0 > K:
        return None

    lo = (k0 - 1) * sample
    hi = None
    for k in range(k0, K + 1):
        t = k * sample
        if predict(t)[2]:
            return None
        if reach(t):
            hi = t
            break
        lo = t
    if hi is None:
        return None
    for _ in range(iters):
        mid = lo + (hi - lo) * 0.5
        if reach(mid):
            hi = mid
        else:
            lo = mid
    pos, alt, arrived = predict(hi)
    if arrived:
        return None
    dx = pos[0] - origin[0]
    dy = pos[1] - origin[1]
    h = math.sqrt(dx * dx + dy * dy)
    if h > R + EPS or alt > C + EPS or alt < 0:
        return None
    return hi, pos, alt


def lin(p0, v, alt, arrive_at=None):
    def f(t):
        if arrive_at is not None and t > arrive_at:
            return ((p0[0] + v[0] * arrive_at, p0[1] + v[1] * arrive_at), alt, True)
        return ((p0[0] + v[0] * t, p0[1] + v[1] * t), alt, False)
    return f


def pcg32_step(state, inc):
    old = state
    state = (old * 6364136223846793005 + inc) & 0xFFFFFFFFFFFFFFFF
    xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
    rot = (old >> 59) & 0x1F
    out = ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF
    return state, out


class MiniRng:
    def __init__(self, seed=1):
        # Simple deterministic PRNG for T-03-56 verification in Python
        self.state = 0
        self.inc = ((seed << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self.state, _ = pcg32_step(self.state, self.inc)
        self.state = (self.state + seed) & 0xFFFFFFFFFFFFFFFF
        self.state, _ = pcg32_step(self.state, self.inc)

    def next_u32(self):
        self.state, out = pcg32_step(self.state, self.inc)
        return out

    def next_double(self):
        hi = self.next_u32() >> 5
        lo = self.next_u32() >> 6
        return ((hi * 67108864.0) + lo) / 9007199254740992.0

    def uniform(self, a, b):
        return a + (b - a) * self.next_double()


def main():
    print("== T-03-01 迎头 (32 vs 48)")
    r32 = solve((0, 0), 900, 20000, 5000, lin((10000, 0), (-100, 0), 1000), iters=32)
    r48 = solve((0, 0), 900, 20000, 5000, lin((10000, 0), (-100, 0), 1000), iters=48)
    print("32:", repr(r32[0]), repr(r32[1]), r32[2])
    print("48:", repr(r48[0]), repr(r48[1]), r48[2])
    A = 810000 - 10000
    B = 2 * 10000 * 100
    Cc = -(10000**2 + 1000**2)
    t_cf = (-B + math.sqrt(B * B - 4 * A * Cc)) / (2 * A)
    print("closed form:", repr(t_cf), "x:", repr(10000 - 100 * t_cf))

    print("\n== T-03-02 横穿目标 (32 vs 48)")
    r32 = solve((0, 0), 1000, 30000, 10000, lin((-8000, 6000), (250, 0), 2000), iters=32)
    r48 = solve((0, 0), 1000, 30000, 10000, lin((-8000, 6000), (250, 0), 2000), iters=48)
    print("32:", repr(r32[0]), repr(r32[1]))
    print("48:", repr(r48[0]), repr(r48[1]))
    A = 937500
    B = 4e6
    Cc = -104e6
    t_cf = (-B + math.sqrt(B * B - 4 * A * Cc)) / (2 * A)
    print("closed form:", repr(t_cf), "x:", repr(-8000 + 250 * t_cf))

    print("\n== T-03-03 追不上")
    print(solve((0, 0), 200, 20000, 5000, lin((5000, 0), (300, 0), 500)))

    print("\n== T-03-04 射程包络 & 进入包络 (32 vs 48)")
    print("out:", solve((0, 0), 900, 5000, 5000, lin((10000, 0), (-100, 0), 1000)))
    r32 = solve((0, 0), 900, 5000, 5000, lin((5500, 0), (-100, 0), 1000), iters=32)
    r48 = solve((0, 0), 900, 5000, 5000, lin((5500, 0), (-100, 0), 1000), iters=48)
    print("in 32:", repr(r32[0]), repr(r32[1]))
    print("in 48:", repr(r48[0]), repr(r48[1]))

    print("\n== T-03-05 先落地 / 超射高")
    print(solve((0, 0), 100, 20000, 5000, lin((3000, 0), (-50, 0), 100, arrive_at=5.0)))
    print(solve((0, 0), 900, 20000, 5000, lin((10000, 0), (-100, 0), 6000)))

    print("\n== T-03-06 拦截无人机 (32 vs 48)")
    r32 = solve((0, 0), 100, 20000, 3000, lin((5000, 0), (-50, 0), 500), iters=32)
    r48 = solve((0, 0), 100, 20000, 3000, lin((5000, 0), (-50, 0), 500), iters=48)
    print("32:", repr(r32[0]), repr(r32[1]))
    print("48:", repr(r48[0]), repr(r48[1]))
    print("fast escape:", solve((0, 0), 100, 20000, 3000, lin((1000, 0), (120, 0), 500)))

    print("\n== T-03-08 & T-03-09 概率链")
    base = 0.6
    mults = [1.0, 0.7, 0.85, 1.15, 0.6, 0.6, 1.0, 0.8]
    p = base
    for m in mults:
        p = p * m
    print("T-03-08 chain (m9=1.0):", repr(p * 1.0))
    p_no_ev = 0.6
    for m in [1.0, 0.7, 0.85, 1.15, 0.6, 1.0, 1.0, 0.8, 1.0]:
        p_no_ev *= m
    print("T-03-08 no evasive:", repr(p_no_ev))
    print("T-03-09 clamp raw:", repr(0.95 * 1.15))
    print("T-03-09 gun vague:", repr(0.25 * 0.5))
    print("T-03-09 m1 vs e_bm (C-T1-02 fix):", repr(0.5 * 0.7))

    print("\n== T-03-10 反应时间")
    print("3.0 * 1.25 * 1.5 * 1.3 =", repr(3.0 * 1.25 * 1.5 * 1.3))

    print("\n== T-03-11 场景：tick1 求解 / tick4 发射 (32 vs 48)")
    for x0, label in [(9900, "tick1"), (9600, "tick4")]:
        r32 = solve((0, 0), 900, 10000, 5000, lin((x0, 0), (-100, 0), 1000), iters=32)
        r48 = solve((0, 0), 900, 10000, 5000, lin((x0, 0), (-100, 0), 1000), iters=48)
        print(
            label,
            "32: dt=", repr(r32[0]), "x=", repr(r32[1][0]),
            "InterceptAt=", repr(4 + r32[0]) if label == "tick4" else None,
        )
        print(
            label,
            "48: dt=", repr(r48[0]), "x=", repr(r48[1][0]),
            "InterceptAt=", repr(4 + r48[0]) if label == "tick4" else None,
        )

    print("\n== T-03-20 多火力单元分配 (B-T3-02: 便宜优先)")
    # uF (ID=1) at (0,0), AceCrew=false (p=0.8, cost=0.4 -> expectedCost = 0.5)
    # uF' (ID=2) at (2000,0), AceCrew=true (p=0.8*1.15=0.92, cost=0.4 -> expectedCost = 0.4/0.92 = 0.4347826...)
    # At step 1: both lock, ReadyAtSec = 4.
    # At step 4 (x0 = 9600): uF' (ID=2, cheaper expectedCost) fires first!
    r_u2_t4 = solve((2000, 0), 900, 10000, 5000, lin((9600, 0), (-100, 0), 1000), iters=32)
    print(
        "Step 4 uF' (at 2000,0) fires: dt=", repr(r_u2_t4[0]),
        "InterceptAtSec=", repr(4 + r_u2_t4[0]),
        "x=", repr(r_u2_t4[1][0]),
    )
    # InterceptAtSec = 4 + 8.512296228546184 = 12.512296228546184 -> resolves at step 13!
    # At step 13: uF' missile misses (D[0] = 0.99).
    # At step 14: uF' is on cooldown (NextShotAtSec = 19); uF (ID=1, at (0,0)) re-locks, ReadyAtSec = 14 + 3 = 17!
    # At step 17 (x0 = 10000 - 100*17 = 8300): uF (at 0,0) fires!
    r_u1_t17 = solve((0, 0), 900, 10000, 5000, lin((8300, 0), (-100, 0), 1000), iters=32)
    print(
        "Step 17 uF (at 0,0) fires: dt=", repr(r_u1_t17[0]),
        "InterceptAtSec=", repr(17 + r_u1_t17[0]),
        "x=", repr(r_u1_t17[1][0]),
    )
    # Also check step 18 at (2000,0) (when both have AceCrew=false so ID tie-breaker applies):
    r_u2_t18 = solve((2000, 0), 900, 10000, 5000, lin((8200, 0), (-100, 0), 1000), iters=32)
    print(
        "Tie-breaker step 18 uF' (at 2000,0) fires: dt=", repr(r_u2_t18[0]),
        "InterceptAtSec=", repr(18 + r_u2_t18[0]),
        "x=", repr(r_u2_t18[1][0]),
    )

    print("\n== T-03-26 禁止区：拦截点首次 x<8000 的步 (32 vs 48)")
    for k in range(1, 40):
        x0 = 10000 - 100 * k
        s32 = solve((0, 0), 900, 10000, 5000, lin((x0, 0), (-100, 0), 1000), iters=32)
        if s32 and s32[1][0] < 8000:
            s48 = solve((0, 0), 900, 10000, 5000, lin((x0, 0), (-100, 0), 1000), iters=48)
            print("lock tick", k, "32 x=", repr(s32[1][0]), "48 x=", repr(s48[1][0]))
            s2_32 = solve((0, 0), 900, 10000, 5000, lin((10000 - 100 * (k + 3), 0), (-100, 0), 1000), iters=32)
            s2_48 = solve((0, 0), 900, 10000, 5000, lin((10000 - 100 * (k + 3), 0), (-100, 0), 1000), iters=48)
            print(
                "fire tick", k + 3,
                "32: x=", repr(s2_32[1][0]), "InterceptAt=", repr(k + 3 + s2_32[0]),
                "| 48: x=", repr(s2_48[1][0]), "InterceptAt=", repr(k + 3 + s2_48[0]),
            )
            break

    print("\n== T-03-34 战斗机交战 (32 vs 48)")
    for x in [1000, 2000]:
        s32 = solve((0, 0), 900, 5000, 15000, lin((x, 0), (0, 0), 500), iters=32)
        s48 = solve((0, 0), 900, 5000, 15000, lin((x, 0), (0, 0), 500), iters=48)
        print(f"x={x}: 32 dt={s32[0]!r}, 48 dt={s48[0]!r}")

    print("\n== T-03-51 交换比 (B-T3-01 新公式)")
    # B-T3-01: PotentialLoss(t) = max(costMusd ?? 0.0, 2^(damageLevel - 1) * lossMusdBase * weight)
    # where lossMusdBase = 0.1
    # In T-03-51: target is e_uav (damageLevel 3, costMusd 0.05), TargetStructureId = tpp (weight 5)
    # 2^(3 - 1) * 0.1 * 5.0 = 4 * 0.1 * 5.0 = 2.0 M$ > 0.05 M$ -> 2.0 M$
    pot = max(0.05, (2 ** (3 - 1)) * 0.1 * 5.0)
    cost = 0.0
    for c_ in [0.4, 0.4, 0.001, 0.001, 0.001]:
        cost += c_
    print("pot:", repr(pot), "cost:", repr(cost), "ratio:", repr(pot / cost))
    print("m1 ratio:", repr(pot / 0.8), "g1 ratio:", repr(0.0 / 0.003))
    # Also check e_cm (damageLevel 7, costMusd 13, weight 1 vs weight 3):
    pot_cm_w1 = max(13.0, (2 ** (7 - 1)) * 0.1 * 1.0)
    pot_cm_w3 = max(13.0, (2 ** (7 - 1)) * 0.1 * 3.0)
    print("e_cm w=1:", repr(pot_cm_w1), "e_cm w=3:", repr(pot_cm_w3))
    # Oreshnik submunitions (count 6, damageLevel 6, weight 1):
    pot_sub = max(0.0, 6 * (2 ** (6 - 1)) * 0.1 * 1.0)
    print("submunitions (6 x L6, w=1):", repr(pot_sub))

    print("\n== T-03-56 2000 组随机场景朴素与加速实现逐位等价性校验 (C-T1-05)")
    rng = MiniRng(1)
    mismatches = 0
    solved_count = 0
    for _ in range(2000):
        speed = rng.uniform(100.0, 1200.0)
        R = rng.uniform(3000.0, 40000.0)
        C = rng.uniform(1000.0, 12000.0)
        # Generate a random candidate list of 8 targets
        n_cands = 8
        cands = []
        for cid in range(1, n_cands + 1):
            px = rng.uniform(-R * 1.2, R * 1.2)
            py = rng.uniform(-R * 1.2, R * 1.2)
            alt = rng.uniform(50.0, C * 1.1)
            vx = rng.uniform(-300.0, 300.0)
            vy = rng.uniform(-300.0, 300.0)
            vt = math.sqrt(vx * vx + vy * vy)
            arr = rng.uniform(5.0, 120.0) if rng.next_double() < 0.3 else None
            cands.append((cid, (px, py), (vx, vy), alt, vt, arr))

        # Naive: solve all, sort by (TimeSec, cid), pick first non-null
        naive_best = None
        for cid, p0, v, alt, vt, arr in cands:
            s_naive = solve((0.0, 0.0), speed, R, C, lin(p0, v, alt, arr), iters=32, max_speed_3d=None)
            s_accel = solve((0.0, 0.0), speed, R, C, lin(p0, v, alt, arr), iters=32, max_speed_3d=vt)
            if s_naive != s_accel:
                mismatches += 1
            if s_naive is not None:
                cand_key = (s_naive[0], cid, s_naive[1], s_naive[2])
                if naive_best is None or (cand_key[0], cand_key[1]) < (naive_best[0], naive_best[1]):
                    naive_best = cand_key

        # Accelerated lower-bound lazy queue:
        lb_list = []
        for cid, p0, v, alt, vt, arr in cands:
            d3d = math.sqrt(p0[0] * p0[0] + p0[1] * p0[1] + alt * alt)
            lb = max(0.0, d3d / (speed + vt))
            lb_list.append((lb, cid, p0, v, alt, vt, arr))
        lb_list.sort(key=lambda x: (x[0], x[1]))

        accel_best = None
        for lb, cid, p0, v, alt, vt, arr in lb_list:
            if accel_best is not None and (accel_best[0], accel_best[1]) <= (lb, cid):
                break
            s_accel = solve((0.0, 0.0), speed, R, C, lin(p0, v, alt, arr), iters=32, max_speed_3d=vt)
            if s_accel is not None:
                cand_key = (s_accel[0], cid, s_accel[1], s_accel[2])
                if accel_best is None or (cand_key[0], cand_key[1]) < (accel_best[0], accel_best[1]):
                    accel_best = cand_key

        if naive_best != accel_best:
            mismatches += 1
        if naive_best is not None:
            solved_count += 1

    print(f"T-03-56: 2000 scenarios tested, solved={solved_count}, mismatches={mismatches}")
    assert mismatches == 0, f"Expected 0 mismatches, got {mismatches}"


if __name__ == "__main__":
    main()
