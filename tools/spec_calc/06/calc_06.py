#!/usr/bin/env python3
"""
tools/spec_calc/06/calc_06.py
《守夜》Nightwatch — 06_client_graybox.md §7 测试向量与审阅决议计算验证脚本
注意：按 C-T1-04，距离计算一律使用 math.sqrt(dx*dx + dy*dy)，不使用 math.hypot。
"""
import math

# === 3.1 MapProjection ===
k = 4.0
H = 2000.0


def to_world_px(x: float, y: float):
    return (x * k, (H - y) * k)


def from_world_px(wx: float, wy: float):
    return (wx / k, H - wy / k)


def bearing_to_rot(b: float) -> float:
    return b - math.pi / 2.0


def interceptor_rot(px: float, py: float, ix: float, iy: float) -> float:
    dx, dy = ix - px, iy - py
    if dx * dx + dy * dy < 1.0:
        return 0.0
    return math.atan2(dx, dy)


def rot_pt(x: float, y: float, th: float):
    c, s = math.cos(th), math.sin(th)
    return (x * c - y * s, x * s + y * c)


# === 3.2 MapCamera ===
W, Hv = 1000.0, 500.0
C = (1500.0, 1000.0)
S = 3000.0
s = W / S


def world_to_screen(px: float, py: float, c=C, span=S, w=W, h=Hv):
    sc = w / span
    return ((px - c[0]) * sc + w / 2.0, (c[1] - py) * sc + h / 2.0)


def screen_to_world(qx: float, qy: float, c=C, span=S, w=W, h=Hv):
    sc = w / span
    return (c[0] + (qx - w / 2.0) / sc, c[1] - (qy - h / 2.0) / sc)


def zoom_at(qx: float, qy: float, steps: int, c=C, span=S, min_s=1000.0, max_s=4400.0, f=1.25):
    pw = screen_to_world(qx, qy, c, span)
    s_new = max(min_s, min(max_s, span * (f ** (-steps))))
    sc_new = W / s_new
    cx = pw[0] - (qx - W / 2.0) / sc_new
    cy = pw[1] + (qy - Hv / 2.0) / sc_new
    cx = max(0.0, min(3000.0, cx))
    cy = max(0.0, min(2000.0, cy))
    return (cx, cy), s_new, pw


def log_t(span: float, mn=1000.0, mx=400000.0) -> float:
    return (math.log(span) - math.log(mn)) / (math.log(mx) - math.log(mn))


# === 3.4 StepAccumulator ===
class Acc:
    def __init__(self, max_dt=0.25):
        self.acc = 0.0
        self.dropped = 0
        self.max_dt = max_dt

    def plan(self, dt: float, spr: float, max_steps=32) -> int:
        dt = max(0.0, min(self.max_dt, dt))
        self.acc += dt * spr
        n = int(math.floor(self.acc + 1e-9))
        return min(n, max_steps)

    def commit(self, k_exec: int, dropped_rate=False):
        self.acc -= k_exec
        if dropped_rate:
            self.acc = 0.0
            return
        if self.acc >= 1.0 - 1e-9:
            w = int(math.floor(self.acc + 1e-9))
            self.dropped += w
            self.acc -= w
        if self.acc < 0.0:
            self.acc = 0.0

    @property
    def alpha(self) -> float:
        return max(0.0, min(1.0, self.acc))


# === 3.5 TimeController (C-T3-01) ===
GAME_SEC_TO_WORLD_SEC = 60.0
BALLISTIC_MIN_REAL_WINDOW_SEC = 6.0
BALLISTIC_SLOW_RATE = 0.5
CHOICE_SLOW_RATE = 1.0 / 60.0
CHOICE_TIMEOUT_REAL_SEC = 8.0


def effective_ballistic_slow_rate(min_rem_world_sec):
    if min_rem_world_sec is None:
        return BALLISTIC_SLOW_RATE
    raw = min_rem_world_sec / (GAME_SEC_TO_WORLD_SEC * BALLISTIC_MIN_REAL_WINDOW_SEC)
    return max(1.0 / GAME_SEC_TO_WORLD_SEC, min(BALLISTIC_SLOW_RATE, raw))


def dashed_circle(cx: float, cy: float, r: float, dash: float, gap: float):
    m = max(8, int(math.ceil(2.0 * math.pi * r / (dash + gap))))
    segs = []
    for i in range(m):
        th0 = 2.0 * math.pi * i / m
        th1 = th0 + 2.0 * math.pi * (dash / (dash + gap)) / m
        p0 = (cx + r * math.cos(th0), cy + r * math.sin(th0))
        p1 = (cx + r * math.cos(th1), cy + r * math.sin(th1))
        segs.append((p0, p1))
    return m, segs


def clock_fmt(sec: float) -> str:
    t = int(math.floor(sec + 1e-9))
    return f"{t // 3600:02d}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def bearing_dir(rad: float):
    deg = int(math.floor(rad * 180.0 / math.pi + 0.5)) % 360
    dirs = ["n", "ne", "e", "se", "s", "sw", "w", "nw"]
    idx = ((deg + 22) // 45) % 8
    return deg, dirs[idx]


def verify_all():
    # T-06-01
    for p, expected in [
        ((0.0, 0.0), (0.0, 8000.0)),
        ((3000.0, 2000.0), (12000.0, 0.0)),
        ((1250.5, 100.25), (5002.0, 7599.0)),
        ((-500.0, 2500.0), (-2000.0, -2000.0)),
    ]:
        w = to_world_px(*p)
        assert w == expected, f"T-06-01 {w} != {expected}"
        assert from_world_px(*w) == p

    # T-06-02
    assert abs(bearing_to_rot(0.0) - (-1.5707963267948966)) < 1e-15
    assert abs(bearing_to_rot(math.pi / 2.0) - 0.0) < 1e-15
    th_e = interceptor_rot(0.0, 0.0, 10.0, 0.0)
    assert abs(th_e - 1.5707963267948966) < 1e-15
    tip_e = rot_pt(0.0, -4.0, th_e)
    assert abs(tip_e[0] - 4.0) < 1e-12 and abs(tip_e[1]) < 1e-12
    assert abs(interceptor_rot(0.0, 0.0, -3.0, -3.0) - (-2.356194490192345)) < 1e-15
    assert interceptor_rot(0.0, 0.0, 0.5, 0.0) == 0.0

    # T-06-03 & T-06-04
    assert world_to_screen(1500.0, 1000.0) == (500.0, 250.0)
    c1, s1, pw1 = zoom_at(750.0, 125.0, +1)
    assert s1 == 2400.0 and c1 == (1650.0, 1075.0)
    assert world_to_screen(pw1[0], pw1[1], c1, s1) == (750.0, 125.0)
    c2, s2, _ = zoom_at(750.0, 125.0, -1)
    assert s2 == 3750.0 and c2 == (1312.5, 906.25)

    # T-06-06 & T-06-07
    assert abs(log_t(20000.0) - 0.49999999999999983) < 1e-15
    assert abs(log_t(3000.0) - 0.1833628956710422) < 1e-15
    dt = 1.0 / 60.0
    tau = 0.08
    a_smooth = 1.0 - math.exp(-dt / tau)
    assert abs(a_smooth - 0.18806365384936496) < 1e-15
    ln_s = math.log(3000.0)
    ln_t = math.log(2400.0)
    snap_frame = None
    for frame in range(1, 60):
        ln_s = ln_s + (ln_t - ln_s) * a_smooth
        if abs(ln_t - ln_s) < 1e-4:
            snap_frame = frame
            break
    assert snap_frame == 38

    # T-06-08
    inv = 1.0 / math.sqrt(2.0)
    assert abs((1500.0 + inv * 1125.0) - 2295.4951288348657) < 1e-12
    assert abs((1000.0 + inv * 1125.0) - 1795.495128834866) < 1e-12

    # T-06-11 .. T-06-15
    ac = Acc()
    res = []
    for _ in range(5):
        n = ac.plan(0.01, 60.0)
        ac.commit(n)
        res.append((n, ac.acc))
    assert [r[0] for r in res] == [0, 1, 0, 1, 1]
    assert abs(res[4][1] - 0.0) < 1e-12

    # T-06-18 & T-06-19: C-T3-01 Adaptive Ballistic Slow-Mo
    assert effective_ballistic_slow_rate(None) == 0.5
    assert abs(effective_ballistic_slow_rate(12.0) - (1.0 / 30.0)) < 1e-15      # 锆石 12s -> 1/30x
    assert abs(effective_ballistic_slow_rate(22.0) - (11.0 / 180.0)) < 1e-15    # 匕首 22s -> 11/180x
    assert abs(effective_ballistic_slow_rate(35.0) - (7.0 / 72.0)) < 1e-15      # 伊斯坎德尔 35s -> 7/72x
    assert abs(effective_ballistic_slow_rate(3.0) - (1.0 / 60.0)) < 1e-15       # 下限夹取 1/60x
    assert abs(effective_ballistic_slow_rate(240.0) - 0.5) < 1e-15              # 上限夹取 0.5x

    # T-06-20 & T-06-21: C-T3-01 ChoiceSlow (normal hard pause vs hardcore 1/60x + 8.0s timer)
    normal_choice_rate = 0.0
    hardcore_choice_rate = CHOICE_SLOW_RATE
    assert normal_choice_rate == 0.0
    assert abs(hardcore_choice_rate - (1.0 / 60.0)) < 1e-15
    assert CHOICE_TIMEOUT_REAL_SEC == 8.0

    # T-06-28
    m_dc, segs_dc = dashed_circle(100.0, 50.0, 20.0, 6.0, 4.0)
    assert m_dc == 13
    assert segs_dc[0][0] == (120.0, 50.0)
    assert abs(segs_dc[0][1][0] - 119.16491658218332) < 1e-12
    assert abs(segs_dc[0][1][1] - 55.718913567973786) < 1e-12

    # T-06-30: distance using math.sqrt(dx*dx + dy*dy), no math.hypot (C-T1-04)
    d_a = math.sqrt((520.0 - 500.0) ** 2 + (510.0 - 500.0) ** 2)
    d_b = math.sqrt((520.0 - 540.0) ** 2 + (510.0 - 500.0) ** 2)
    assert d_a == d_b and abs(d_a - 22.360679774997898) < 1e-12

    # T-06-38
    assert clock_fmt(0) == "00:00:00"
    assert clock_fmt(12345) == "03:25:45"
    assert clock_fmt(28800) == "08:00:00"
    assert bearing_dir(0.0) == (0, "n")
    assert bearing_dir(math.pi / 2.0) == (90, "e")
    assert bearing_dir(3.9) == (223, "sw")
    assert bearing_dir(6.2) == (355, "n")

    # T-06-41 & T-06-46
    fit_01 = max(32000.0, 20000.0 * 1920.0 / 1080.0) * 1.1
    assert abs(fit_01 - 39111.11111111112) < 1e-9
    z4 = fit_01 / (1.25 ** 4)
    assert abs(z4 - 16019.911111111114) < 1e-9

    print("ALL 06_client_graybox SPEC_CALC CHECKS PASSED")


if __name__ == "__main__":
    verify_all()
