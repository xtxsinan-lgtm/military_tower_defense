# Reference calculation for 01_spawn_movement_terrain.md (spawn + movement)
import math, struct

# ---------- SimRandom (PCG32 from 00_core.md 3.1.2, C-T1-02) ----------
MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1
PCG_MULT = 6364136223846793005
def u64(x): return x & MASK64

def splitmix64_next(state):
    state = u64(state + 0x9E3779B97F4A7C15)
    z = state
    z = u64((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9)
    z = u64((z ^ (z >> 27)) * 0x94D049BB133111EB)
    return state, u64(z ^ (z >> 31))

def fnv1a64(s: str) -> int:
    h = 0xCBF29CE484222325
    for b in s.encode("utf-8"):
        h ^= b
        h = u64(h * 0x00000100000001B3)
    return h

class SimRandom:
    def __init__(self, seed_u64: int):
        self.seed = u64(seed_u64)
        sm, s0 = splitmix64_next(self.seed)
        _, s1 = splitmix64_next(sm)
        self._state = 0
        self._inc = u64((s1 << 1) | 1)
        self.next_u32()
        self._state = u64(self._state + s0)
        self.next_u32()

    def next_u32(self) -> int:
        old = self._state
        self._state = u64(old * PCG_MULT + self._inc)
        xorshifted = (((old >> 18) ^ old) >> 27) & MASK32
        rot = old >> 59
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & MASK32

    def next_u64(self) -> int:
        hi = self.next_u32()
        lo = self.next_u32()
        return u64((hi << 32) | lo)

    def next_double(self) -> float:
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    def derive(self, name: str) -> "SimRandom":
        _, child_seed = splitmix64_next(self.seed ^ fnv1a64(name))
        return SimRandom(child_seed)

# ---------- Seed 42 spawn stream ----------
root = SimRandom(struct.unpack("<Q", struct.pack("<q", 42))[0])
spawn_rng = root.derive("spawn")
print("=== Seed 42 -> derive('spawn') first 8 NextDouble() ===")
vals = [spawn_rng.next_double() for _ in range(8)]
for i, v in enumerate(vals):
    print(f"  [{i}] = {v:.17g}")

# Weighted structure selection: S1 weight 1.0, S2 weight 2.0, S3 weight 1.0 -> W = 4.0
# Destroyed S2 -> S1 weight 1.0, S3 weight 1.0 -> W = 2.0
print("\n=== T-01-06 weighted_random (S1 w=1, S2 w=2, S3 w=1, total=4) ===")
for i in range(4):
    r = vals[i] * 4.0
    pick = "s1" if r < 1.0 else ("s2" if r < 3.0 else "s3")
    print(f"  draw {i}: u={vals[i]:.12f}, r={r:.12f} -> {pick}")

# ---------- Movement math ----------
def poly_cum(pts):
    cum = [0.0]
    for i in range(len(pts) - 1):
        dx = pts[i+1][0] - pts[i][0]
        dy = pts[i+1][1] - pts[i][1]
        cum.append(cum[-1] + math.sqrt(dx * dx + dy * dy))
    return cum

def pos_dir_at_s(pts, cum, s):
    L = cum[-1]
    if L == 0.0:
        return pts[0], (0.0, 0.0)
    sc = min(max(s, 0.0), L)
    # largest i with cum[i] <= sc and i < len-1
    i = 0
    for k in range(len(pts) - 1):
        if cum[k] <= sc:
            i = k
    seg = cum[i+1] - cum[i]
    u = 0.0 if seg == 0.0 else (sc - cum[i]) / seg
    px = pts[i][0] + (pts[i+1][0] - pts[i][0]) * u
    py = pts[i][1] + (pts[i+1][1] - pts[i][1]) * u
    # direction: first non-zero segment from i, else backward
    dx = dy = 0.0
    dlen = 0.0
    for k in range(i, len(pts) - 1):
        sl = cum[k+1] - cum[k]
        if sl > 0:
            dx = (pts[k+1][0] - pts[k][0]) / sl
            dy = (pts[k+1][1] - pts[k][1]) / sl
            dlen = sl
            break
    if dlen == 0.0:
        for k in range(i - 1, -1, -1):
            sl = cum[k+1] - cum[k]
            if sl > 0:
                dx = (pts[k+1][0] - pts[k][0]) / sl
                dy = (pts[k+1][1] - pts[k][1]) / sl
                break
    return (px, py), (dx, dy)

def s_at(t, t0, s0, sD, L, v1, v2):
    dt = t - t0
    if dt <= 0.0:
        return s0
    if v1 == v2 or s0 >= sD:
        v = v1 if s0 < sD else v2
        return min(L, s0 + v * dt)
    t_to_d = (sD - s0) / v1
    if dt <= t_to_d:
        return s0 + v1 * dt
    return min(L, sD + v2 * (dt - t_to_d))

def time_at_s(s, t0, s0, sD, v1, v2):
    if s <= s0:
        return t0
    if v1 == v2 or s0 >= sD or s <= sD:
        v = v1 if s0 < sD else v2
        return t0 + (s - s0) / v
    return t0 + (sD - s0) / v1 + (s - sD) / v2

def alt_linear(s, sD, L, A0, Aend):
    if s <= sD or L <= sD:
        return A0
    u = min(1.0, (s - sD) / (L - sD))
    return A0 + (Aend - A0) * u

def alt_parabolic(s, L, A0):
    if L <= 0.0:
        return 0.0
    u = min(1.0, max(0.0, s / L))
    return A0 * (1.0 - u * u)

def vert_speed(s, sD, L, A0, Aend, vh, parabolic=False):
    if s >= L or vh == 0.0:
        return 0.0
    if parabolic:
        return vh * (-2.0 * A0 * s / (L * L))
    if s < sD or L <= sD:
        return 0.0
    return vh * ((Aend - A0) / (L - sD))

# ---------- Case A: Shahed direct with terminal dive ----------
# Entry (1000, 0) -> Target (0, 0), L = 1000 m
# speedKmh = 180 -> v1 = 50 m/s, v2 = 50 m/s (no dive speed mult)
# alt = 200 m, diveAngleDeg = 45 -> tan(45°) = 1.0 -> D = 200 / 1 = 200 m -> sD = 800 m
print("\n=== T-01-20 Shahed (L=1000, v=50, A0=200, dive 45 deg -> sD=800) ===")
pts = [(1000.0, 0.0), (0.0, 0.0)]
cum = poly_cum(pts)
L = cum[-1]
sD = L - 200.0 / math.tan(math.radians(45.0))
print(f"  sD = {sD:.12f}, arrival t = {time_at_s(L, 0, 0, sD, 50, 50):.12f}")
for t in [1, 16, 17, 18, 20]:
    s = s_at(t, 0.0, 0.0, sD, L, 50.0, 50.0)
    pos, d = pos_dir_at_s(pts, cum, s)
    alt = alt_linear(s, sD, L, 200.0, 0.0)
    vh = 0.0 if s >= L else 50.0
    vz = vert_speed(s, sD, L, 200.0, 0.0, vh)
    print(f"  t={t:2d}: s={s:6.1f}, pos=({pos[0]:6.1f},{pos[1]:4.1f}), alt={alt:6.2f}, vel=({d[0]*vh:6.1f},{d[1]*vh:4.1f}), vz={vz:6.2f}")

# ---------- Case B: Lancet with terminalSpeedMultiplier = 2.5 ----------
# Entry (900, 0) -> Target (0, 0), L = 900 m
# speedKmh = 108 -> v1 = 30 m/s, mult = 2.5 -> v2 = 75 m/s
# alt = 150 m, diveAngleDeg = 45 -> D = 150 m -> sD = 750 m
# t to sD = 750 / 30 = 25 s; remaining 150 m at 75 m/s = 2 s -> arrival at t = 27 s
# Test mid-step transition: if L = 915 -> sD = 765 -> t_to_d = 765/30 = 25.5 s, rem 150/75 = 2.0 s -> t_arr = 27.5 s!
print("\n=== T-01-21 Lancet (L=915, v1=30, v2=75, A0=150, dive 45 deg -> sD=765) ===")
pts = [(915.0, 0.0), (0.0, 0.0)]
cum = poly_cum(pts)
L = cum[-1]
sD = L - 150.0 / math.tan(math.radians(45.0))
t_arr = time_at_s(L, 0.0, 0.0, sD, 30.0, 75.0)
print(f"  sD = {sD:.12f}, t_to_D = {sD/30.0:.12f}, t_arr = {t_arr:.12f}")
for t in [25, 26, 27, 28]:
    s = s_at(t, 0.0, 0.0, sD, L, 30.0, 75.0)
    pos, d = pos_dir_at_s(pts, cum, s)
    alt = alt_linear(s, sD, L, 150.0, 0.0)
    vh = 0.0 if s >= L else (30.0 if s < sD else 75.0)
    vz = vert_speed(s, sD, L, 150.0, 0.0, vh)
    print(f"  t={t:2d}: s={s:6.2f}, pos=({pos[0]:6.2f},{pos[1]:4.1f}), alt={alt:6.2f}, vh={vh:5.1f}, vz={vz:6.2f}")

# ---------- Case C: Waypoints + Cruise ----------
# Entry (1000, 0) -> W1 (1000, 600) -> Target (200, 600)
# seg0 = 600 (north), seg1 = 800 (west), total L = 1400 m
# v = 250 m/s (900 km/h), A0 = 50 m, diveAngleDeg = 45 -> D = 50 m -> sD = 1350 m
print("\n=== T-01-22 Cruise waypoints (1000,0)->(1000,600)->(200,600), L=1400, v=250, A0=50 ===")
pts = [(1000.0, 0.0), (1000.0, 600.0), (200.0, 600.0)]
cum = poly_cum(pts)
L = cum[-1]
sD = L - 50.0
t_arr = time_at_s(L, 0.0, 0.0, sD, 250.0, 250.0)
print(f"  cum = {cum}, sD = {sD}, t_arr = {t_arr:.12f}")
for t in [1, 2, 3, 5, 6]:
    s = s_at(t, 0.0, 0.0, sD, L, 250.0, 250.0)
    pos, d = pos_dir_at_s(pts, cum, s)
    alt = alt_linear(s, sD, L, 50.0, 0.0)
    vh = 0.0 if s >= L else 250.0
    vz = vert_speed(s, sD, L, 50.0, 0.0, vh)
    print(f"  t={t:2d}: s={s:6.1f}, pos=({pos[0]:6.1f},{pos[1]:6.1f}), alt={alt:6.2f}, vel=({d[0]*vh:6.1f},{d[1]*vh:6.1f}), vz={vz:6.2f}")

# ---------- Case D: Ballistic parabolic ----------
# Entry (6000, 0) -> Target (0, 0), L = 6000 m, v = 2000 m/s (7200 km/h), A0 = 50000 m
print("\n=== T-01-23 Ballistic (L=6000, v=2000, A0=50000, parabolic) ===")
pts = [(6000.0, 0.0), (0.0, 0.0)]
cum = poly_cum(pts)
L = cum[-1]
for t in [1, 2, 3]:
    s = s_at(t, 0.0, 0.0, L, L, 2000.0, 2000.0)
    pos, d = pos_dir_at_s(pts, cum, s)
    alt = alt_parabolic(s, L, 50000.0)
    vh = 0.0 if s >= L else 2000.0
    vz = vert_speed(s, L, L, 50000.0, 0.0, vh, parabolic=True)
    print(f"  t={t:2d}: s={s:6.1f}, pos=({pos[0]:6.1f},{pos[1]:4.1f}), alt={alt:9.4f}, vz={vz:10.4f}")

# ---------- Case E: Decoy exitRay ----------
# Entry (1000, 200), center = (500, 500), map 1000x1000, margin = 200 -> box [-200, 1200] x [-200, 1200]
print("\n=== T-01-25 Decoy exit ray from (1000, 200) through center (500, 500) ===")
E = (1000.0, 200.0)
C = (500.0, 500.0)
dx, dy = C[0] - E[0], C[1] - E[1]
norm = math.sqrt(dx * dx + dy * dy)
ux, uy = dx / norm, dy / norm
# box [-200, 1200] x [-200, 1200]: ux < 0 -> x = -200; uy > 0 -> y = 1200
tx = (-200.0 - E[0]) / ux
ty = (1200.0 - E[1]) / uy
t_exit = min(tx, ty)
P_exit = (E[0] + ux * t_exit, E[1] + uy * t_exit)
print(f"  u = ({ux:.12f}, {uy:.12f}), tx = {tx:.12f}, ty = {ty:.12f}, t_exit = {t_exit:.12f}")
print(f"  P_exit = ({P_exit[0]:.12f}, {P_exit[1]:.12f})")

# ---------- Case F: Platform release circle intersection ----------
# Platform at Entry (2000, 0) -> Target (0, 0), v = 200 m/s, alt = 8000 m
# Carries munition with releaseRange = 1000 m -> release at s = 1000 m, pos = (1000, 0), t = 5.0 s
# Platform path: (2000, 0) -> (1000, 0) -> (2000, 0), L = 2000 m, exits at t = 10.0 s
print("\n=== T-01-26 Platform standoff release (Entry (2000,0), Target (0,0), R=1000, v_p=200) ===")
print("  Release at s=1000, t=5.0, pos=(1000,0); platform exits at s=2000, t=10.0, pos=(2000,0)")

# Oblique release circle test: Entry (2000, 600) -> Target (0, 0), R = 1000 m
P0 = (2000.0, 600.0); P1 = (0.0, 0.0); T = (0.0, 0.0); R = 1000.0
dx, dy = P1[0] - P0[0], P1[1] - P0[1]
fx, fy = P0[0] - T[0], P0[1] - T[1]
a = dx*dx + dy*dy
b = 2.0 * (fx*dx + fy*dy)
c = fx*fx + fy*fy - R*R
disc = b*b - 4*a*c
u = max(0.0, (-b - math.sqrt(disc)) / (2*a))
seg_len = math.sqrt(a)
s_rel = u * seg_len
prel = (P0[0] + u*dx, P0[1] + u*dy)
print(f"  Oblique Entry (2000,600)->(0,0), R=1000: seg={seg_len:.6f}, u={u:.12f}, s_rel={s_rel:.6f}, pos=({prel[0]:.6f},{prel[1]:.6f}), dist_to_T={math.sqrt(prel[0]*prel[0] + prel[1]*prel[1]):.6f}")

# ---------- Case G: T-01-28b Platform p_edge_r with releaseRangeKm=13.6 (ReleaseRangeM=13600, Mini01) ----------
# Entry eE=(25000,10000) -> Target s1=(10000,10000), dist = 15000 m, p_edge_r: v=70 m/s, alt=8000, ReleaseRangeM=13600
# Carries 1x a1 (ReleaseRangeM=null, v=200 m/s, alt roll 0.5 in [30,70] -> 50 m)
# R = m.ReleaseRangeM ?? p.ReleaseRangeM ?? +inf = 13600 -> s_rel = 15000 - 13600 = 1400 m, pos = (23600, 10000)
# Platform path: [(25000,10000), (23600,10000), (25000,10000)], L = 2800 m, TurnArcM = 1400 m
# SpawnAtSec = 60.0 (Step 60); Release at t = 60 + 1400 / 70 = 80.0 s (Step 80); Platform exits at t = 60 + 2800 / 70 = 100.0 s (Step 100)
# Released a1: SpawnAtSec = 80.0, Entry = (23600,10000) -> (10000,10000), L_m = 13600, v_m = 200 m/s, arrives at t = 80 + 13600/200 = 148.0 s (Step 148)
print("\n=== T-01-28b Platform p_edge_r with releaseRangeKm=13.6 (ReleaseRangeM=13600, Mini01) ===")
print("  s_rel = 1400 m, release pos = (23600, 10000), t_rel = 80.0 s (Step 80)")
print("  Platform exits at s = 2800 m, pos = (25000, 10000), t_exit = 100.0 s (Step 100)")
print("  a1 (v=200 m/s, L=13600 m): SpawnAtSec=80.0, arrives Step 148 (t=148.0)")

# ---------- Case H: T-01-43 MaxSpeed3DMps (Mini01) ----------
def max_speed_3d(profile, phase, L, sD, v1, v2, A0, Aend):
    if phase in ("Arrived", "Holding") or L <= 0.0:
        return 0.0
    vh_max = max(v1, v2)
    if profile == "Parabolic":
        slope = 2.0 * A0 / L
    else:
        slope = abs(A0 - Aend) / (L - sD) if L > sD else 0.0
    return vh_max * math.sqrt(1.0 + slope * slope)

print("\n=== T-01-43 MaxSpeed3DMps (Mini01) ===")
# 1. m100 (Linear, L=1000, sD=900, v1=v2=50, A0=100, Aend=0): slope = 100/100 = 1.0 -> 50 * sqrt(2)
v3d_m100 = max_speed_3d("Linear", "Ingress", 1000.0, 900.0, 50.0, 50.0, 100.0, 0.0)
# 2. l1 (Linear, L=1025, sD=925, v1=50, v2=100, A0=100, Aend=0): slope = 100/100 = 1.0 -> 100 * sqrt(2)
v3d_l1 = max_speed_3d("Linear", "Ingress", 1025.0, 925.0, 50.0, 100.0, 100.0, 0.0)
# 3. b1 (Parabolic, L=10000, sD=0, v1=v2=2000, A0=10000*tan(45)/2, Aend=0): slope = tan(45) -> 2000 * sqrt(2)
v3d_b1 = max_speed_3d("Parabolic", "Ingress", 10000.0, 0.0, 2000.0, 2000.0, 10000.0 * math.tan(math.radians(45.0)) / 2.0, 0.0)
# 4. Holding / Arrived -> 0.0
v3d_hold = max_speed_3d("Linear", "Holding", 200.0, 200.0, 30.0, 30.0, 1000.0, 1000.0)
print(f"  m100:    {v3d_m100:.16f} (= 50 * sqrt(2))")
print(f"  l1:      {v3d_l1:.16f} (= 100 * sqrt(2))")
print(f"  b1:      {v3d_b1:.16f} (= 2000 * sqrt(2))")
print(f"  holding: {v3d_hold:.16f}")

