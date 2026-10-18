#!/usr/bin/env python3
"""
docs/spec/04_enemy_ai_commands.md §7 测试向量参考计算脚本（D2b 收口版）。
严格使用 math.sqrt(dx*dx + dy*dy) 计算欧氏距离（禁用 math.hypot，C-T1-04）。
包含 B-T3-05（暴露度 100 改派 25% 待生成 weighted_random 弹药）、C-T1-06（增量计数等价性）、
C-T1-07（A* 缓存等价性）的独立核算与断言。
"""
import math

EPS = 1e-9


def ceil_ticks(sec, step=1.0):
    return int(math.ceil(sec / step - EPS))


def dist(p, q):
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    return math.sqrt(dx * dx + dy * dy)


# ---- 1. T-04-07 / T-04-08 / T-04-25: 已知目标与防空模式加权选择 ----
def test_weighted_selection():
    print("=== T-04-07 / T-04-08 / T-04-25 ===")
    w0 = [1.0, 1.5, 2.0]
    W0 = sum(w0)
    r0 = 0.3 * W0
    assert W0 == 4.5
    assert r0 == 1.3499999999999999
    print("T-04-07 case 1:", w0, "W=", repr(W0), "r(0.3)=", repr(r0))

    w1 = [1.0, 1.5 / (1.0 + 1 * 1.0), 2.0]
    W1 = sum(w1)
    r1_a = 0.3 * W1
    r1_b = 0.5 * W1
    assert W1 == 3.75
    assert r1_a == 1.125
    assert r1_b == 1.875
    print("T-04-07 case 2:", w1, "W=", repr(W1), "r(0.3)=", repr(r1_a), "r(0.5)=", repr(r1_b))

    assert 0.6 * 2.0 == 1.2
    assert 0.4 * 2.0 == 0.8
    print("T-04-08: r(0.6)=", repr(0.6 * 2.0), "r(0.4)=", repr(0.4 * 2.0))

    W25_1 = 1.0 + 1.0 + 1.0
    r25_1 = 0.1 * W25_1
    assert r25_1 == 0.30000000000000004
    W25_2 = 0.5 + 1.0 + 1.0
    r25_2 = 0.9 * W25_2
    assert W25_2 == 2.5 and r25_2 == 2.25
    print("T-04-25: r1=", repr(r25_1), "W2=", repr(W25_2), "r2=", repr(r25_2))


# ---- 2. B-T3-05: 暴露度 100 改派 25% 待生成 weighted_random 组 ----
def calc_exposure100_quota(rem, retarget_frac=0.25):
    return min(rem, max(1, int(math.ceil(rem * retarget_frac - 1e-9))))


def test_b_t3_05():
    print("\n=== B-T3-05 Exposure 100 Retargeting ===")
    assert calc_exposure100_quota(4, 0.25) == 1
    assert calc_exposure100_quota(5, 0.25) == 2
    assert calc_exposure100_quota(8, 0.25) == 2
    assert calc_exposure100_quota(1, 0.25) == 1
    print("Quotas for rem=[1, 4, 5, 8]:", [calc_exposure100_quota(n) for n in (1, 4, 5, 8)])


# ---- 3. C-T1-06: 1000 个存活目标下增量计数与全表扫描逐位一致 ----
def test_c_t1_06_incremental_counts():
    print("\n=== C-T1-06 Incremental Assigned Counts ===")
    state = 0x853C49E6748FEA9B
    inc = 0xDA3E39CB94B95BDB

    def next_u32():
        nonlocal state
        old = state
        state = (old * 6364136223846793005 + inc) & ((1 << 64) - 1)
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = (old >> 59) & 0x1F
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF

    threats = {}
    assigned_by_unit = {}
    assigned_by_pos = {}
    arm_by_unit = {}

    positions = [(1000.0, 1000.0), (2000.0, 2000.0), (8000.0, 8000.0)]
    for tid in range(1, 1001):
        u_id = next_u32() % 6
        pos = positions[next_u32() % len(positions)]
        is_arm = (next_u32() % 4) == 0
        is_arrived = (next_u32() % 10) == 0
        kind_player = (next_u32() % 5) != 0
        th = {
            "alive": True,
            "phase": "Arrived" if is_arrived else "Ingress",
            "target_kind": "PlayerUnit" if kind_player else "Structure",
            "unit_id": u_id if kind_player else 0,
            "pos": pos,
            "is_arm": is_arm,
        }
        threats[tid] = th
        if th["alive"] and th["phase"] != "Arrived" and th["target_kind"] == "PlayerUnit":
            if th["unit_id"] != 0:
                assigned_by_unit[th["unit_id"]] = assigned_by_unit.get(th["unit_id"], 0) + 1
                if th["is_arm"]:
                    arm_by_unit[th["unit_id"]] = arm_by_unit.get(th["unit_id"], 0) + 1
            else:
                assigned_by_pos[th["pos"]] = assigned_by_pos.get(th["pos"], 0) + 1

    for tid in range(1, 1001):
        th = threats[tid]
        if tid % 3 == 0 or tid % 7 == 0:
            if th["alive"] and th["phase"] != "Arrived" and th["target_kind"] == "PlayerUnit":
                if th["unit_id"] != 0:
                    assigned_by_unit[th["unit_id"]] -= 1
                    if th["is_arm"]:
                        arm_by_unit[th["unit_id"]] -= 1
                else:
                    assigned_by_pos[th["pos"]] -= 1
            if tid % 3 == 0:
                th["alive"] = False
            else:
                th["phase"] = "Arrived"

    for u in range(1, 6):
        scan_assigned = sum(
            1 for th in threats.values()
            if th["alive"] and th["phase"] != "Arrived"
            and th["target_kind"] == "PlayerUnit" and th["unit_id"] == u
        )
        scan_arm = sum(
            1 for th in threats.values()
            if th["alive"] and th["phase"] != "Arrived"
            and th["target_kind"] == "PlayerUnit" and th["unit_id"] == u and th["is_arm"]
        )
        assert assigned_by_unit.get(u, 0) == scan_assigned
        assert arm_by_unit.get(u, 0) == scan_arm
    for p in positions:
        scan_pos = sum(
            1 for th in threats.values()
            if th["alive"] and th["phase"] != "Arrived"
            and th["target_kind"] == "PlayerUnit" and th["unit_id"] == 0 and th["pos"] == p
        )
        assert assigned_by_pos.get(p, 0) == scan_pos
    print("C-T1-06 1000-threat incremental vs full-scan verified: 0 mismatches.")


# ---- 4. T-04-14..16: 饱和攻击时间计算 ----
def saturate(base, threats, W):
    N = len(threats)
    f = [(i / (N - 1) if N >= 2 else 0.0) for i in range(N)]
    tstar = max(base + fl - W * f[i] for i, (_, fl) in enumerate(threats))
    out = []
    for i, (n, fl) in enumerate(threats):
        sp = tstar + W * f[i] - fl
        out.append((n, fl, sp, sp + fl))
    return tstar, out


def test_saturation():
    print("\n=== T-04-14..16 Saturation ===")
    eA = (0.0, 0.0)
    eB = (10000.0, 0.0)
    s3 = (0.0, 6000.0)
    dA = dist(eA, s3)
    dB = dist(eB, s3)
    fA = dA / 50.0
    fB = dB / 200.0
    assert dA == 6000.0 and fA == 120.0
    assert dB == 11661.903789690601
    assert fB == 58.309518948453004
    ts14, out14 = saturate(600.0, [("A0", fA), ("A1", fA), ("B0", fB)], 30.0)
    t14 = [o[2] for o in out14]
    assert ts14 == 720.0
    assert t14 == [600.0, 615.0, 691.690481051547]
    print("T-04-14:", [repr(x) for x in t14])

    wp = (3000.0, 3000.0)
    L15 = dist(eA, wp) + dist(wp, s3)
    f15 = L15 / 50.0
    assert L15 == 8485.28137423857
    assert f15 == 169.70562748477138
    _, out15 = saturate(600.0, [("A0", f15), ("A1", f15), ("B0", fB)], 30.0)
    t15 = [o[2] for o in out15]
    assert t15 == [600.0, 615.0, 741.3961085363184]
    print("T-04-15:", [repr(x) for x in t15])

    est = ((2000.0 * 3 + 8000.0 * 1) / 4.0, (6000.0 * 3 + 6000.0 * 1) / 4.0)
    L16 = dist(eA, est)
    f16 = L16 / 50.0
    assert est == (3500.0, 6000.0)
    assert L16 == 6946.221994724902
    assert f16 == 138.92443989449805
    print("T-04-16: est=", est, "L=", repr(L16), "flight=", repr(f16))


# ---- 5. T-04-17..23 & C-T1-07: 绕行网格与 A* ----
NEI = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1)]


def build_grid(minx, miny, w, h, cell, maxcells):
    c = cell
    while math.ceil(w / c - EPS) * math.ceil(h / c - EPS) > maxcells:
        c *= 1.25
    nx = int(math.ceil(w / c - EPS))
    ny = int(math.ceil(h / c - EPS))
    return c, nx, ny


def center(minx, miny, c, nx, i):
    ix = i % nx
    iy = i // nx
    return (minx + (ix + 0.5) * c, miny + (iy + 0.5) * c)


def cell_of(minx, miny, c, nx, ny, p):
    ix = int(math.floor((p[0] - minx) / c))
    iy = int(math.floor((p[1] - miny) / c))
    ix = max(0, min(nx - 1, ix))
    iy = max(0, min(ny - 1, iy))
    return iy * nx + ix


def penalties(minx, miny, c, nx, ny, sites, weight, rmult, valley_fn, valley_w, los_fn):
    P = []
    for i in range(nx * ny):
        cc = center(minx, miny, c, nx, i)
        p = valley_w * valley_fn(cc)
        for (sp, R) in sites:
            dx = cc[0] - sp[0]
            dy = cc[1] - sp[1]
            rr = R * rmult
            if dx * dx + dy * dy < rr * rr and los_fn(sp, cc):
                p += weight
        P.append(p)
    return P


def astar(minx, miny, c, nx, ny, P, start, goal):
    INF = float("inf")
    g = [INF] * (nx * ny)
    parent = [-1] * (nx * ny)
    closed = [False] * (nx * ny)
    gc = center(minx, miny, c, nx, goal)

    def hfun(i):
        cc = center(minx, miny, c, nx, i)
        return math.sqrt((cc[0] - gc[0]) ** 2 + (cc[1] - gc[1]) ** 2)

    g[start] = 0.0
    openset = {(hfun(start), hfun(start), start)}
    expansions = 0
    while openset:
        cur = min(openset)
        openset.remove(cur)
        _, _, u = cur
        if closed[u]:
            continue
        closed[u] = True
        expansions += 1
        if u == goal:
            break
        ux = u % nx
        uy = u // nx
        for (dx, dy) in NEI:
            vx = ux + dx
            vy = uy + dy
            if vx < 0 or vy < 0 or vx >= nx or vy >= ny:
                continue
            v = vy * nx + vx
            if closed[v]:
                continue
            ln = c if (dx == 0 or dy == 0) else c * math.sqrt(2.0)
            ng = g[u] + ln * (1.0 + P[v])
            if ng < g[v]:
                if g[v] < INF:
                    openset.discard((g[v] + hfun(v), hfun(v), v))
                g[v] = ng
                parent[v] = u
                openset.add((ng + hfun(v), hfun(v), v))
    if not closed[goal]:
        return None, None, expansions
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path, g[goal], expansions


def turning(minx, miny, c, nx, path):
    wps = []
    for j in range(1, len(path) - 1):
        a = path[j - 1]
        b = path[j]
        n = path[j + 1]
        d1 = (b % nx - a % nx, b // nx - a // nx)
        d2 = (n % nx - b % nx, n // nx - b // nx)
        if d1 != d2:
            wps.append(center(minx, miny, c, nx, b))
    return wps


def test_bypass():
    print("\n=== T-04-17..23 & C-T1-07 Bypass / A* ===")
    minx, miny = 0.0, 0.0
    c, nx, ny = build_grid(minx, miny, 10000.0, 10000.0, 1000.0, 4096)
    s = cell_of(minx, miny, c, nx, ny, (500.0, 4500.0))
    g = cell_of(minx, miny, c, nx, ny, (9500.0, 4500.0))
    assert s == 40 and g == 49

    flat = lambda p: 0.0
    los_true = lambda sp, cc: True
    los_false = lambda sp, cc: False

    # T-04-17
    P17 = penalties(minx, miny, c, nx, ny, [((5000.0, 5000.0), 2500.0)], 4.0, 1.0, flat, 0.5, los_true)
    path17, g17, closed17 = astar(minx, miny, c, nx, ny, P17, s, g)
    tp17 = turning(minx, miny, c, nx, path17)
    assert g17 == 10656.85424949238
    assert closed17 == 18
    assert tp17 == [(1500.0, 4500.0), (3500.0, 2500.0), (6500.0, 2500.0), (8500.0, 4500.0)]
    print("T-04-17: G=", repr(g17), "closed=", closed17, "turns=", tp17)

    # T-04-18
    P18 = penalties(minx, miny, c, nx, ny, [], 4.0, 1.0, flat, 0.5, los_true)
    path18, g18, _ = astar(minx, miny, c, nx, ny, P18, s, g)
    assert g18 == 9000.0 and turning(minx, miny, c, nx, path18) == []
    P18b = penalties(minx, miny, c, nx, ny, [((5000.0, 5000.0), 2500.0)], 4.0, 1.0, flat, 0.5, los_false)
    path18b, g18b, _ = astar(minx, miny, c, nx, ny, P18b, s, g)
    assert g18b == 9000.0 and turning(minx, miny, c, nx, path18b) == []
    print("T-04-18: G=", repr(g18))

    # T-04-19 (A-50)
    P19 = penalties(minx, miny, c, nx, ny, [((5000.0, 5000.0), 2500.0)], 8.0, 1.2, flat, 0.5, los_true)
    path19, g19, _ = astar(minx, miny, c, nx, ny, P19, s, g)
    tp19 = turning(minx, miny, c, nx, path19)
    assert g19 == 11485.281374238572
    assert tp19 == [(3500.0, 1500.0), (6500.0, 1500.0)]
    print("T-04-19: G=", repr(g19), "turns=", tp19)

    # T-04-20 (Valley)
    P20 = penalties(
        minx, miny, c, nx, ny, [], 4.0, 1.0,
        lambda p: 0.0 if 1000.0 <= p[1] <= 2000.0 else 1.0,
        0.5, los_true
    )
    path20, g20, _ = astar(minx, miny, c, nx, ny, P20, cell_of(minx, miny, c, nx, ny, (500.0, 1500.0)), g)
    tp20 = turning(minx, miny, c, nx, path20)
    assert g20 == 12363.961030678927
    assert tp20 == [(6500.0, 1500.0)]
    print("T-04-20: G=", repr(g20), "turns=", tp20)

    # T-04-21 (Grid scaling)
    c21, nx21, ny21 = build_grid(0, 0, 100000.0, 100000.0, 1000.0, 400)
    assert c21 == 5960.4644775390625 and nx21 == 17 and ny21 == 17
    print("T-04-21: cell_m=", repr(c21), "nx=ny=", nx21)

    # C-T1-07 A* cache equivalence check (30 missiles with same (ti, a50, s, g, version))
    cache = {}
    ver = 1
    for _ in range(30):
        key = (0, False, s, g, ver)
        if key not in cache:
            cache[key] = turning(minx, miny, c, nx, astar(minx, miny, c, nx, ny, P17, s, g)[0])
        assert cache[key] == tp17
    print("C-T1-07 A* cache equivalence verified.")


# ---- 6. T-04-30 / T-04-31: 部署状态机移动插值 ----
def pos_at(frm, dest, v, d, move_start, t):
    s = min(d, v * (t - move_start))
    f = s / d
    return (frm[0] + (dest[0] - frm[0]) * f, frm[1] + (dest[1] - frm[1]) * f)


def test_relocation():
    print("\n=== T-04-30 / T-04-31 Relocation ===")
    v = 60.0 / 3.6
    d_s = dist((1000.0, 1000.0), (2000.0, 1000.0))
    raw_s = d_s / v
    assert raw_s == 59.99999999999999
    p95 = pos_at((1000.0, 1000.0), (2000.0, 1000.0), v, d_s, 65, 95)
    p124 = pos_at((1000.0, 1000.0), (2000.0, 1000.0), v, d_s, 65, 124)
    assert p95 == (1500.0, 1000.0)
    assert p124 == (1983.3333333333335, 1000.0)
    print("T-04-31 alt_s: d/v=", repr(raw_s), "p95=", p95, "p124=", p124)

    d_n = dist((1000.0, 1000.0), (1600.0, 1800.0))
    p100 = pos_at((1000.0, 1000.0), (1600.0, 1800.0), v, d_n, 65, 100)
    assert p100 == (1350.0, 1466.6666666666667)
    print("T-04-31 alt_n: p100=", p100)


if __name__ == "__main__":
    test_weighted_selection()
    test_b_t3_05()
    test_c_t1_06_incremental_counts()
    test_saturation()
    test_bypass()
    test_relocation()
    print("\nALL 04 SPEC VECTORS VERIFIED SUCCESSFULLY.")
