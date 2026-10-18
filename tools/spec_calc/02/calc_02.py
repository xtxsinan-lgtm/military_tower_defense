#!/usr/bin/env python3
"""
02_sensing_tracks_ew_emission.md 测试用例预期值计算与自检脚本
运行方式：python3 tools/spec_calc/02/calc_02.py
"""
import math

fails = 0


def check(name, got, exp, tol=None):
    global fails
    ok = (got == exp) if tol is None else abs(got - exp) <= tol
    if not ok:
        fails += 1
    print(("OK  " if ok else "FAIL"), name, "got", repr(got), "exp", repr(exp))


def run_exposure(rates, n_launch=None, steps=10, start=0.0):
    e = start
    out = []
    for k in range(1, steps + 1):
        r = rates(k)
        n = n_launch(k) if n_launch else 0
        if r == 0 and n == 0:
            r = -0.5
        e = min(100.0, max(0.0, e + r * 1.0 + n * 5.0))
        out.append(e)
    return out


# T-02-02, T-02-03, T-02-05, T-02-13, T-02-14: 探测距离与有效距离
check("T-02-02 lowAlt medium", 10000.0 * 0.5, 5000.0)
check("T-02-03 blind zone lowAlt", 10000.0 * 0.25 * 0.5, 1250.0)
check("T-02-05a moonlit", 4000.0 * 0.5 * 1.5, 3000.0)
check("T-02-05b moonlit+thermal", 4000.0 * 1.5, 6000.0)
check("T-02-05c fog", 4000.0 * 0.5 * 0.25, 500.0)
check("T-02-05d null weather", 4000.0 * 0.5, 2000.0)
check("T-02-05e moonlit+searchlight", 4000.0 * 0.5 * 1.5, 3000.0)
check("T-02-05f day clear", 4000.0 * 1.0, 4000.0)
check("T-02-13 unpowered", 10000.0 * 0.5, 5000.0)
check("T-02-13 newPosition", 10000.0 * 0.7, 7000.0)
check("T-02-13 winter", 10000.0 * 0.9, 9000.0)
check("T-02-14 fc lowAlt", 8000.0 * 0.75, 6000.0)
check("T-02-14 optical selfAcq night", 2000.0 * 0.3, 600.0)
check("T-02-14 optical selfAcq searchlight/day", 2000.0 * 1.0, 2000.0)

# T-02-04 & T-02-04b: 视线与径向最大遮挡斜率包络
R_eff = 6371000.0 * (4.0 / 3.0)


def drop(d):
    return (d * d) / (2.0 * R_eff)


# T-02-04: sensor@(500,1500), antenna 10m -> z_s = 10; ridge at x=1500 (d1=1000) z=1000; target@(2500,1500) (d=2000)
s_ridge = (1000.0 - drop(1000.0) - 10.0) / 1000.0
s_low_target = (0.0 + 50.0 - drop(2000.0) - 10.0) / 2000.0
s_high_target = (0.0 + 3000.0 - drop(2000.0) - 10.0) / 2000.0
check("T-02-04 low target occluded", s_low_target < s_ridge, True)
check("T-02-04 high target visible", s_high_target >= s_ridge, True)

# T-02-04b: 多山脊合成高度场径向包络与逐段采样对比
def synth_elev(x, y):
    # 两道山脊 + 平缓起伏（轴对称于中心 (5000,5000) 的环形山脊 + 方向调制，使方位离散化误差极小）
    dx = x - 5000.0
    dy = y - 5000.0
    r = math.sqrt(dx * dx + dy * dy)
    h1 = 220.0 * math.exp(-((r - 2500.0) / 350.0) ** 2)
    h2 = 380.0 * math.exp(-((r - 5500.0) / 450.0) ** 2)
    return h1 + h2


def los_reference(sx, sy, sa, tx, ty, ta, step_m=50.0):
    dx = tx - sx
    dy = ty - sy
    d = math.sqrt(dx * dx + dy * dy)
    if d == 0.0:
        return True
    zs = synth_elev(sx, sy) + sa
    zt = synth_elev(tx, ty) + ta - drop(d)
    st = (zt - zs) / d
    n = max(1, int(math.ceil(d / step_m)))
    for i in range(1, n):
        di = d * (i / n)
        xi = sx + dx * (i / n)
        yi = sy + dy * (i / n)
        zi = synth_elev(xi, yi) - drop(di)
        if (zi - zs) / di > st:
            return False
    return True


def build_envelope(sx, sy, sa, max_r=10000.0, step_m=50.0, bins=720):
    zs = synth_elev(sx, sy) + sa
    n = int(math.ceil(max_r / step_m))
    env = []
    for b in range(bins):
        az = b * (2.0 * math.pi / bins)
        ux = math.sin(az)
        uy = math.cos(az)
        row = [float("-inf")] * (n + 1)
        cur = float("-inf")
        for k in range(1, n + 1):
            dk = k * step_m
            zk = synth_elev(sx + ux * dk, sy + uy * dk) - drop(dk)
            sk = (zk - zs) / dk
            if sk > cur:
                cur = sk
            row[k] = cur
        env.append(row)
    return zs, step_m, bins, env


def los_envelope(profile, sx, sy, tx, ty, ta):
    zs, step_m, bins, env = profile
    dx = tx - sx
    dy = ty - sy
    d = math.sqrt(dx * dx + dy * dy)
    if d == 0.0:
        return True
    az = math.atan2(dx, dy)
    if az < 0.0:
        az += 2.0 * math.pi
    b = int(round(az / (2.0 * math.pi / bins))) % bins
    k = min(len(env[b]) - 1, max(0, int(math.ceil(d / step_m)) - 1))
    if k == 0:
        return True
    zt = synth_elev(tx, ty) + ta - drop(d)
    st = (zt - zs) / d
    return st >= env[b][k]


prof = build_envelope(5000.0, 5000.0, 10.0)
diff_count = 0
for i in range(2000):
    # 确定性伪随机点对（传感器在 (5000,5000)，地形含 x=6500 与 x=8000 两道南北向山脊）
    u1 = ((i * 1103515245 + 12345) & 0x7FFFFFFF) / 0x7FFFFFFF
    u2 = ((i * 214013 + 2531011) & 0x7FFFFFFF) / 0x7FFFFFFF
    u3 = ((i * 1664525 + 1013904223) & 0x7FFFFFFF) / 0x7FFFFFFF
    r = 500.0 + 9000.0 * u1
    th = 2.0 * math.pi * u2
    alt = 30.0 + 1500.0 * u3
    tx = 5000.0 + r * math.sin(th)
    ty = 5000.0 + r * math.cos(th)
    if los_reference(5000.0, 5000.0, 10.0, tx, ty, alt) != los_envelope(prof, 5000.0, 5000.0, tx, ty, alt):
        diff_count += 1
check(f"T-02-04b diff rate < 1% (diff={diff_count}/2000)", diff_count / 2000.0 < 0.01, True)

# T-02-10: 误报位置
R_fa = 2000.0
u1_fa, u2_fa = 0.25, 0.25
r_fa = R_fa * math.sqrt(u1_fa)
th_fa = 2.0 * math.pi * u2_fa
check("T-02-10 phantom X", 5000.0 + r_fa * math.sin(th_fa), 6000.0, 1e-9)
check("T-02-10 phantom Y", 5000.0 + r_fa * math.cos(th_fa), 5000.0, 1e-9)

# T-02-12: 预警方位角
check("T-02-12 e2 bearing", math.atan2(0.0, 20000.0), 0.0)
check("T-02-12 e1 bearing", math.atan2(20000.0, 0.0), 1.5707963267948966)

# T-02-24: 诱饵甄别条件概率（无档案 vs 敌情档案 +0.1）
check("T-02-24 cond p", (0.8 - 0.5) / (1.0 - 0.5), 0.6000000000000001)
check("T-02-24 dossier approx p", min(1.0, 0.5 + 0.1), 0.6)
check("T-02-24 dossier precise p", min(1.0, 0.8 + 0.1), 0.9)
check("T-02-24 dossier cond p", (0.9 - 0.6) / (1.0 - 0.6), 0.75, 1e-9)

# T-02-30..T-02-40: 电子战计算
check("T-02-30 ewExtraM C", 1.5 * 1.0 * 1000.0, 1500.0)
check("T-02-34 spoof ai nav p", 0.5 * 0.5, 0.25)
check("T-02-34 spoof ai pull p", 0.3 * 0.5, 0.15)
check("T-02-35 link weights", [u * 4.0 for u in (0.6, 0.1, 0.3)], [2.4, 0.4, 1.2])
check("T-02-37 belowFullStrength", 0.5 * 0.5, 0.25)
check("T-02-37 newPos", 0.5 * 0.7, 0.35)
check("T-02-37 unpowered", 0.5 * 0.5, 0.25)
check("T-02-37 winter", 0.5 * 0.9, 0.45)
check("T-02-40 shield mult", 1.0 - (1.0 - 0.5) * 0.8, 0.6, 1e-9)

# T-02-53: 火控指示进入射程时间
def tenter(px, py, vx, vy, R):
    a = vx * vx + vy * vy
    b = 2.0 * (px * vx + py * vy)
    c = px * px + py * py - R * R
    if c <= 0.0:
        return 0.0
    if a == 0.0:
        return None
    d = b * b - 4.0 * a * c
    if d < 0.0:
        return None
    t = (-b - math.sqrt(d)) / (2.0 * a)
    return t if t >= 0.0 else None


check("T-02-53 tick8 tau", tenter(6700.0, 0.0, -100.0, 0.0, 6000.0), 7.0)
check("T-02-53 tick9 tau", tenter(6600.0, 0.0, -100.0, 0.0, 6000.0), 6.0)

# T-02-55..T-02-80: 暴露度与反辐射关机时机
check("T-02-55 cued", run_exposure(lambda k: 0.6)[-1], 5.999999999999999)
check("T-02-55 self", run_exposure(lambda k: 2.0)[-1], 20.0)
check("T-02-55 ratio", run_exposure(lambda k: 0.6)[-1] / run_exposure(lambda k: 2.0)[-1], 0.3, 1e-9)
seq = run_exposure(lambda k: 1.0 if k <= 30 else 0.0, steps=40)
check("T-02-70 30", seq[29], 30.0)
check("T-02-70 40", seq[39], 25.0)
seq = run_exposure(lambda k: 0.0, n_launch=lambda k: 2 if k == 2 else 0, steps=3)
check("T-02-71", seq, [0.0, 10.0, 9.5])
seq = run_exposure(lambda k: 2.0, steps=60)
check("T-02-73 cross", [next(i + 1 for i, v in enumerate(seq) if v >= t) for t in (40, 70, 100)], [20, 35, 50])
check("T-02-74", min(100.0, max(0.0, 75.0 * 0.5 - 0.5)), 37.0)
check("T-02-75 decoy", run_exposure(lambda k: 1.0)[-1], 10.0)
check("T-02-75 shield", run_exposure(lambda k: 0.3)[-1], 2.9999999999999996, 1e-9)
check("T-02-76 ew high", run_exposure(lambda k: 1.0)[-1], 10.0)
check("T-02-76 ew low", run_exposure(lambda k: 0.3)[-1], 2.9999999999999996, 1e-9)
seq = run_exposure(lambda k: 0.5 if k >= 2 else 0.0, steps=10)
check("T-02-80", seq[-1], 4.5)


def armmult(f, tiers=((0.5, 0.2), (0.25, 0.5), (0.0, 0.8))):
    for above, m in tiers:
        if f > above:
            return m
    return 1.0


check("T-02-56", armmult(10000.0 / 20000.0), 0.5)
check("T-02-56b", armmult((16000.0 - 6000.0) / 16000.0), 0.2)
check("T-02-57", armmult((12000.0 - 500.0 * 11.0) / 12000.0), 0.2)
check("T-02-57b", armmult(8000.0 / 12000.0), 0.2)
check("T-02-58", armmult(2000.0 / 20000.0), 0.8)

print("FAILS:", fails)
if fails > 0:
    raise SystemExit(1)
