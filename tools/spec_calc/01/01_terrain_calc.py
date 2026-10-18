# Reference calculation for 01_spawn_movement_terrain.md (terrain + LOS + HorizonProfile)
import math

class Heightmap:
    def __init__(self, w, h, mpp, elev):
        self.w = w
        self.h = h
        self.mpp = mpp
        self.elev = elev  # row-major, row 0 = north
        self.min_e = min(elev)
        self.max_e = max(elev)

    def elevation_at(self, x: float, y: float) -> float:
        m = self.mpp
        extent_y = self.h * m
        fx = x / m - 0.5
        fy = (extent_y - y) / m - 0.5
        fx = min(max(fx, 0.0), self.w - 1.0)
        fy = min(max(fy, 0.0), self.h - 1.0)
        c0 = int(math.floor(fx))
        r0 = int(math.floor(fy))
        if c0 > self.w - 2: c0 = max(self.w - 2, 0)
        if r0 > self.h - 2: r0 = max(self.h - 2, 0)
        c1 = min(c0 + 1, self.w - 1)
        r1 = min(r0 + 1, self.h - 1)
        tx = fx - c0
        ty = fy - r0
        e00 = self.elev[r0 * self.w + c0]
        e01 = self.elev[r0 * self.w + c1]
        e10 = self.elev[r1 * self.w + c0]
        e11 = self.elev[r1 * self.w + c1]
        top = e00 + (e01 - e00) * tx
        bot = e10 + (e11 - e10) * tx
        return top + (bot - top) * ty

def has_los(hm: Heightmap, a, a_msl: float, b, b_msl: float, step_m: float, r_eff_m):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    d = math.sqrt(dx * dx + dy * dy)
    if d <= step_m:
        return True
    n = int(math.ceil(d / step_m))
    for i in range(1, n):
        f = i / n
        px = a[0] + dx * f
        py = a[1] + dy * f
        ray = a_msl + (b_msl - a_msl) * f
        s = d * f
        drop = 0.0 if r_eff_m is None else (s * (d - s)) / (2.0 * r_eff_m)
        terr = hm.elevation_at(px, py) + drop
        if terr > ray:
            return False
    return True

class HorizonProfile:
    def __init__(self, hm: Heightmap, obs, obs_agl_m: float, max_range_m: float, step_m: float, r_eff_m, bins: int = 720):
        self.obs = obs
        self.obs_msl = hm.elevation_at(obs[0], obs[1]) + obs_agl_m
        self.max_range_m = max_range_m
        self.step_m = step_m
        self.r_eff_m = r_eff_m
        self.bins = bins
        self.radial_steps = max(1, int(math.ceil(max_range_m / step_m)))
        self.max_slope = []
        for b in range(bins):
            theta = 2.0 * math.pi * b / bins
            ux = math.cos(theta)
            uy = math.sin(theta)
            row = [-math.inf]
            for j in range(1, self.radial_steps + 1):
                s = j * step_m
                px = obs[0] + ux * s
                py = obs[1] + uy * s
                elev = hm.elevation_at(px, py)
                curv = 0.0 if r_eff_m is None else s / (2.0 * r_eff_m)
                slope = (elev - self.obs_msl) / s - curv
                row.append(max(row[-1], slope))
            self.max_slope.append(row)

    def has_los(self, target, target_msl_m: float) -> bool:
        dx = target[0] - self.obs[0]
        dy = target[1] - self.obs[1]
        d = math.sqrt(dx * dx + dy * dy)
        if d <= self.step_m:
            return True
        ang = math.atan2(dy, dx)
        if ang < 0.0:
            ang += 2.0 * math.pi
        b = int(math.floor(ang * self.bins / (2.0 * math.pi) + 0.5)) % self.bins
        j = min(max(int(math.ceil(d / self.step_m)) - 1, 1), self.radial_steps)
        curv = 0.0 if self.r_eff_m is None else d / (2.0 * self.r_eff_m)
        target_slope = (target_msl_m - self.obs_msl) / d - curv
        return target_slope >= self.max_slope[b][j]

# ---------- 4x4 test heightmap (mpp = 100 m -> 400 x 400 m) ----------
# row 0 (north, y_c = 350):  10,  20,  30,  40
# row 1 (       y_c = 250):  10, 120, 120,  40   <-- ridge at y around 200..250
# row 2 (       y_c = 150):  10, 120, 120,  40
# row 3 (south, y_c =  50):  10,  20,  30,  40
elev = [
    10.0,  20.0,  30.0,  40.0,
    10.0, 120.0, 120.0,  40.0,
    10.0, 120.0, 120.0,  40.0,
    10.0,  20.0,  30.0,  40.0,
]
hm = Heightmap(4, 4, 100.0, elev)

print("=== Bilinear elevation samples (4x4, mpp=100) ===")
test_pts = [
    (50.0, 350.0),   # center of (r=0, c=0) -> 10
    (150.0, 250.0),  # center of (r=1, c=1) -> 120
    (200.0, 200.0),  # center of 4 ridge pixels (r=1..2, c=1..2) -> 120
    (100.0, 300.0),  # average of (0,0)=10, (0,1)=20, (1,0)=10, (1,1)=120 -> 40
    (125.0, 275.0),  # tx=0.75, ty=0.75 in cell (0..1, 0..1)
    (0.0, 400.0),    # NW corner (clamped to r=0, c=0) -> 10
    (-500.0, 200.0), # outside west: clamped fx=0, fy=1.5 -> avg(10,10)=10
    (500.0, 50.0),   # outside east at y=50: clamped fx=3, fy=3 -> 40
]
for x, y in test_pts:
    print(f"  E({x:6.1f}, {y:6.1f}) = {hm.elevation_at(x, y):.12f}")

print("\n=== LOS across ridge (no earth curvature, step = 50 m) ===")
# Sensor at (200, 50), ground = 25 m, antenna = 10 m -> a_msl = 35 m
# Target at (200, 350), ground = 25 m
a = (200.0, 50.0)
b = (200.0, 350.0)
print(f"  ground(a)={hm.elevation_at(*a)}, ground(b)={hm.elevation_at(*b)}")
# Along (200, 50) -> (200, 350), d = 300, step = 50 -> n = 6, i=1..5:
# i=3 -> f=0.5 -> (200, 200) where terrain = 120 m!
# For ray at f=0.5 to be >= 120: 35 + (b_msl - 35)*0.5 >= 120 -> b_msl >= 205 m (target alt AGL >= 180 m)
for b_msl in [100.0, 204.9, 205.0, 205.1, 250.0]:
    los = has_los(hm, a, 35.0, b, b_msl, 50.0, None)
    print(f"  b_msl={b_msl:6.1f} -> LOS={los}")

print("\n=== LOS with earth curvature (flat terrain 0 m, R_eff = 4/3 * 6371000 = 8494666.6667 m) ===")
hm_flat = Heightmap(2, 2, 100000.0, [0.0, 0.0, 0.0, 0.0])
R_eff = (4.0 / 3.0) * 6371000.0
# Radar at (0, 0), a_msl = 25 m; target at d = 100000 m (100 km)
# At midpoint s = 50 km, drop = 50000 * 50000 / (2 * R_eff) = 147.151157 m
# Ray at midpoint = (25 + b_msl) / 2. Blocked if (25 + b_msl)/2 < 147.151157 -> b_msl < 269.3023 m
# Wait: tangent horizon distance from h1=25 m is sqrt(2*R_eff*25) = 20,609 m; remaining 79,391 m requires h2 = 79391^2 / (2*R_eff) = 371.0 m!
# Let's check exact threshold for n = ceil(100000 / 500) = 200 steps:
step = 500.0
d = 100000.0
n = int(math.ceil(d / step))
req_b = 0.0
worst_i = 0
for i in range(1, n):
    f = i / n
    s = d * f
    drop = s * (d - s) / (2.0 * R_eff)
    # need 25 + (b_msl - 25)*f >= drop -> b_msl >= 25 + (drop - 25) / f
    need = 25.0 + (drop - 25.0) / f
    if need > req_b:
        req_b = need
        worst_i = i
print(f"  R_eff = {R_eff:.6f}, critical i = {worst_i}/{n} (s={d*worst_i/n:.1f} m), min b_msl = {req_b:.6f} m")
for b_msl in [200.0, 370.0, 371.0, 372.0, 400.0]:
    print(f"  b_msl={b_msl:6.1f} -> LOS={has_los(hm_flat, (0.0,0.0), 25.0, (100000.0,0.0), b_msl, step, R_eff)}")

print("\n=== T-01-58 Dual-ridge terrain occlusion & HorizonProfile (B-T2-31, C-T2-01) ===")
# 10x1 heightmap (WidthPx=10, HeightPx=1, MetersPerPixel=100 m -> 1000 x 100 m)
# Pixel centers at x_c = 50, 150, 250, 350, 450, 550, 650, 750, 850, 950; y_c = 50
# Elevations:
#   c=0 (x=50):   0 m (observer at (50, 50), ground=0, antenna=10 -> a_msl=10)
#   c=1 (x=150):  0 m
#   c=2 (x=250): 30 m <-- Ridge 1 at x=250 (d=200 m from observer): slope = (30 - 10)/200 = 0.10
#   c=3 (x=350):  0 m (valley between ridges)
#   c=4 (x=450):  0 m (valley at x=450, d=400 m from observer)
#   c=5 (x=550):  0 m
#   c=6 (x=650): 130 m <-- Ridge 2 at x=650 (d=600 m from observer): slope = (130 - 10)/600 = 0.20 > 0.10
#   c=7 (x=750):  0 m
#   c=8 (x=850):  0 m (behind Ridge 2 at x=850, d=800 m from observer)
#   c=9 (x=950):  0 m
elev_dual = [0.0, 0.0, 30.0, 0.0, 0.0, 0.0, 130.0, 0.0, 0.0, 0.0]
hm_dual = Heightmap(10, 1, 100.0, elev_dual)
obs = (50.0, 50.0)
obs_agl = 10.0
obs_msl = 10.0
step_dual = 50.0
hp = HorizonProfile(hm_dual, obs, obs_agl, 900.0, step_dual, None, bins=720)

dual_cases = [
    ("Target A (between R1 & R2, slope 0.15 > R1 0.10, < R2 0.20)", (450.0, 50.0), 70.0),
    ("Target B (between R1 & R2, low in valley, slope 0.05 < R1 0.10)", (450.0, 50.0), 30.0),
    ("Target C (behind R2, clears R1 slope 0.15 > 0.10, blocked by R2 0.20)", (850.0, 50.0), 130.0),
    ("Target D (behind R2, grazing R2 slope 0.20 == 0.20)", (850.0, 50.0), 170.0),
]
for label, tgt, tgt_msl in dual_cases:
    los_exact = has_los(hm_dual, obs, obs_msl, tgt, tgt_msl, step_dual, None)
    los_prof = hp.has_los(tgt, tgt_msl)
    assert los_exact == los_prof, f"Mismatch on {label}: {los_exact} != {los_prof}"
    print(f"  {label}: exact={los_exact}, profile={los_prof}")
