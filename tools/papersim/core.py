"""Core math, geometry, time conversion, deterministic PCG32 RNG, and FNV-1a 64 StateHasher (00_core.md)."""

from __future__ import annotations
import math
import struct
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1

PCG_MULTIPLIER = 6364136223846793005
SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
SPLITMIX_MUL1 = 0xBF58476D1CE4E5B9
SPLITMIX_MUL2 = 0x94D049BB133111EB
FNV_OFFSET_BASIS = 0xCBF29CE484222325
FNV_PRIME = 0x00000100000001B3
DOUBLE_UNIT = 1.0 / 9007199254740992.0  # 2^-53


def u64(x: int) -> int:
    return x & MASK64


def u32(x: int) -> int:
    return x & MASK32


def i64_to_u64(x: int) -> int:
    return struct.unpack("<Q", struct.pack("<q", x))[0]


def splitmix64_next(x: int) -> Tuple[int, int]:
    """Advance SplitMix64 state x and return (new_x, output) (00_core.md §3.1.2)."""
    x = (x + SPLITMIX_GAMMA) & MASK64
    z = x
    z = ((z ^ (z >> 30)) * SPLITMIX_MUL1) & MASK64
    z = ((z ^ (z >> 27)) * SPLITMIX_MUL2) & MASK64
    return x, (z ^ (z >> 31)) & MASK64


def fnv1a64_bytes(data: bytes, h: int = FNV_OFFSET_BASIS) -> int:
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & MASK64
    return h


def fnv1a64(s: str) -> int:
    return fnv1a64_bytes(s.encode("utf-8"))


class SimError(Exception):
    """Structured error raised during data loading, validation, or setup."""

    def __init__(self, code: str, message: str, file_path: str = "", json_path: str = ""):
        loc = f"{file_path} {json_path}".strip()
        prefix = f"[{code}] {loc}: " if loc else f"[{code}] "
        super().__init__(f"{prefix}{message}")
        self.code = code
        self.message = message
        self.file_path = file_path
        self.json_path = json_path


class SimTime:
    """Unit and time conversions (00_core.md §0.4)."""

    WORLD_SECONDS_PER_GAME_SECOND: float = 60.0
    WORLD_STEP_SECONDS: float = 1.0
    TICK_EPSILON: float = 1e-9

    @staticmethod
    def to_world_seconds(game_seconds: float, game_sec_to_world_sec: float = 60.0) -> float:
        return game_seconds * game_sec_to_world_sec

    @staticmethod
    def per_game_sec_to_per_world_sec(rate_per_game_sec: float, game_sec_to_world_sec: float = 60.0) -> float:
        return rate_per_game_sec / game_sec_to_world_sec

    @staticmethod
    def km_to_m(km: float) -> float:
        return km * 1000.0

    @staticmethod
    def kmh_to_mps(kmh: float) -> float:
        return kmh / 3.6

    @staticmethod
    def mach_to_mps(mach: float, mach_kmh: float = 1200.0) -> float:
        return (mach * mach_kmh) / 3.6

    @staticmethod
    def cells_to_m(cells: float, cell_km: float = 1.0) -> float:
        return cells * cell_km * 1000.0

    @staticmethod
    def pct_to_frac(pct: float) -> float:
        return pct / 100.0

    @staticmethod
    def deg_to_rad(deg: float) -> float:
        return deg * (math.pi / 180.0)

    @staticmethod
    def rad_to_deg(rad: float) -> float:
        return rad * (180.0 / math.pi)

    @staticmethod
    def sec_to_ticks_ceil(sec: float, step_sec: float = 1.0) -> int:
        if sec < 0.0:
            raise ValueError(f"sec must be >= 0, got {sec}")
        return int(math.ceil(sec / step_sec - SimTime.TICK_EPSILON))

    @staticmethod
    def sec_to_ticks_floor(sec: float, step_sec: float = 1.0) -> int:
        if sec < 0.0:
            raise ValueError(f"sec must be >= 0, got {sec}")
        return int(math.floor(sec / step_sec + SimTime.TICK_EPSILON))

    @staticmethod
    def parse_year_month(s: str, file_path: str = "", json_path: str = "") -> Tuple[int, int, int]:
        parts = s.split("-")
        if len(parts) not in (2, 3):
            raise SimError("E_SCHEMA_INVALID", f"Invalid date '{s}'", file_path, json_path)
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2]) if len(parts) == 3 else 1
        except ValueError as exc:
            raise SimError("E_SCHEMA_INVALID", f"Invalid date '{s}'", file_path, json_path) from exc
        if not (1 <= month <= 12 and 1 <= day <= 31):
            raise SimError("E_RANGE", f"Date out of range '{s}'", file_path, json_path)
        return (year, month, day)


@dataclass(frozen=True)
class Vec2:
    """2D vector in world meters (East=x, North=y). Never uses math.hypot (C-T1-04)."""

    x: float
    y: float

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Vec2:
        return Vec2(self.x / scalar, self.y / scalar)

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vec2) -> float:
        return self.x * other.y - self.y * other.x

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalized(self) -> Vec2:
        ln = self.length()
        if ln == 0.0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / ln, self.y / ln)

    def distance_sq_to(self, other: Vec2) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    def distance_to(self, other: Vec2) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def lerp(a: Vec2, b: Vec2, t: float) -> Vec2:
        return Vec2(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)


class Geo:
    """Cross-spec geometry and interpolation functions (00_core.md §0.4.6)."""

    @staticmethod
    def normalize(rad: float) -> float:
        twopi = 2.0 * math.pi
        if rad < 0.0:
            rad += twopi
        if rad >= twopi:
            rad -= twopi
        if rad == 0.0:
            return 0.0
        return rad

    @staticmethod
    def bearing_rad(from_pt: Vec2, to_pt: Vec2) -> float:
        dx = to_pt.x - from_pt.x
        dy = to_pt.y - from_pt.y
        if dx == 0.0 and dy == 0.0:
            return 0.0
        return Geo.normalize(math.atan2(dx, dy))

    @staticmethod
    def point_in_polygon(p: Vec2, poly: Sequence[Vec2]) -> bool:
        if len(poly) < 3:
            return False
        inside = False
        j = len(poly) - 1
        for i in range(len(poly)):
            a = poly[i]
            b = poly[j]
            if ((a.y > p.y) != (b.y > p.y)) and (
                p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x
            ):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def in_urban(urban_polygons: Sequence[Sequence[Vec2]], p: Vec2) -> bool:
        for poly in urban_polygons:
            if Geo.point_in_polygon(p, poly):
                return True
        return False

    @staticmethod
    def first_entry_into_circle(p: Vec2, d: Vec2, c: Vec2, r: float) -> Optional[float]:
        """Ray p + u*d (u >= 0) first entry parameter u into circle (c, r) (00_core.md §0.4.6)."""
        w = p - c
        cc = w.dot(w) - r * r
        if cc <= 0.0:
            return 0.0
        a = d.dot(d)
        if a <= 0.0:
            return None
        b = 2.0 * d.dot(w)
        disc = b * b - 4.0 * a * cc
        if disc < 0.0:
            return None
        u = (-b - math.sqrt(disc)) / (2.0 * a)
        return u if u >= 0.0 else None

    @staticmethod
    def polyline_length(pts: Sequence[Vec2]) -> float:
        total = 0.0
        for i in range(len(pts) - 1):
            total += pts[i].distance_to(pts[i + 1])
        return total

    @staticmethod
    def point_at_distance(pts: Sequence[Vec2], dist_m: float) -> Tuple[Vec2, float]:
        if not pts:
            return (Vec2.zero(), 0.0)
        if len(pts) == 1 or dist_m <= 0.0:
            if len(pts) >= 2:
                d = pts[1] - pts[0]
                return (pts[0], math.atan2(d.x, d.y))
            return (pts[0], 0.0)
        rem = dist_m
        for i in range(len(pts) - 1):
            a = pts[i]
            b = pts[i + 1]
            seg = a.distance_to(b)
            if seg <= 0.0:
                continue
            if rem <= seg or i == len(pts) - 2:
                u = min(1.0, max(0.0, rem / seg))
                pos = Vec2(a.x + (b.x - a.x) * u, a.y + (b.y - a.y) * u)
                d = b - a
                return (pos, math.atan2(d.x, d.y))
            rem -= seg
        return (pts[-1], 0.0)

    @staticmethod
    def sample_piecewise_linear(pts: Sequence[Tuple[float, float]], x: float) -> float:
        if not pts:
            return 0.0
        if x <= pts[0][0]:
            return pts[0][1]
        if x >= pts[-1][0]:
            return pts[-1][1]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            if x0 <= x <= x1:
                if x1 == x0:
                    return y1
                t = (x - x0) / (x1 - x0)
                return y0 + (y1 - y0) * t
        return pts[-1][1]

    piecewise_linear = sample_piecewise_linear

    @staticmethod
    def lower_bound(arr: Sequence[float], x: float) -> int:
        lo = 0
        hi = len(arr)
        while lo < hi:
            mid = (lo + hi) // 2
            if arr[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    @staticmethod
    def compute_initial_stock(
        initial_stock: int,
        max_stock: int,
        supply_level: str,
        initial_stock_multiplier: Mapping[str, float],
    ) -> int:
        mult = initial_stock_multiplier[supply_level]
        return int(math.floor(min(float(max_stock), float(initial_stock) * mult) + 1e-9))


class SpatialGrid:
    """2D uniform grid spatial index (00_core.md §3.3.1)."""

    def __init__(self, width_m: float = 50000.0, height_m: float = 50000.0):
        self.width_m = width_m
        self.height_m = height_m
        self.cell_size_m = max(5000.0, max(width_m, height_m) / 64.0)
        self.cols = max(1, int(math.ceil(width_m / self.cell_size_m)))
        self.rows = max(1, int(math.ceil(height_m / self.cell_size_m)))
        self._cells: Dict[Tuple[int, int], List[Tuple[int, Vec2]]] = {}

    def _cell_coords(self, p: Vec2) -> Tuple[int, int]:
        cx = int(math.floor(p.x / self.cell_size_m))
        cy = int(math.floor(p.y / self.cell_size_m))
        cx = min(max(cx, 0), self.cols - 1)
        cy = min(max(cy, 0), self.rows - 1)
        return (cx, cy)

    def rebuild(self, items: Iterable[Tuple[int, Vec2]]) -> None:
        self._cells.clear()
        for item_id, pos in sorted(items, key=lambda kv: kv[0]):
            cell = self._cell_coords(pos)
            self._cells.setdefault(cell, []).append((item_id, pos))

    def query_circle(self, center: Vec2, radius_m: float) -> List[int]:
        if not self._cells:
            return []
        min_pt = Vec2(center.x - radius_m, center.y - radius_m)
        max_pt = Vec2(center.x + radius_m, center.y + radius_m)
        cx0, cy0 = self._cell_coords(min_pt)
        cx1, cy1 = self._cell_coords(max_pt)
        r_sq = radius_m * radius_m
        out: List[int] = []
        if (cx1 - cx0 + 1) * (cy1 - cy0 + 1) > len(self._cells):
            for (cx, cy), bucket in self._cells.items():
                if cx0 <= cx <= cx1 and cy0 <= cy <= cy1:
                    for item_id, pos in bucket:
                        if center.distance_sq_to(pos) <= r_sq:
                            out.append(item_id)
        else:
            for cx in range(cx0, cx1 + 1):
                for cy in range(cy0, cy1 + 1):
                    for item_id, pos in self._cells.get((cx, cy), ()):
                        if center.distance_sq_to(pos) <= r_sq:
                            out.append(item_id)
        out.sort()
        return out


class SimRandom:
    """PCG32 (PCG-XSH-RR 64/32) + SplitMix64 seeding + FNV-1a 64 substreams (00_core.md §3.1)."""

    STREAM_NAMES: Tuple[str, ...] = (
        "setup",
        "command",
        "spawn",
        "movement",
        "sensor",
        "fusion",
        "ew",
        "emission",
        "engagement",
        "intercept",
        "support",
        "impact",
        "exposure",
        "enemy_ai",
        "scoring",
        "civil",
        "environment",
        "crew",
    )

    def __init__(self, seed: int):
        self.seed = seed & MASK64
        x, init_state = splitmix64_next(self.seed)
        x, init_seq = splitmix64_next(x)
        self._state = 0
        self._inc = ((init_seq << 1) | 1) & MASK64
        self.next_u32()
        self._state = (self._state + init_state) & MASK64
        self.next_u32()

    @classmethod
    def from_pcg_seed(cls, init_state: int, init_seq: int) -> SimRandom:
        inst = cls.__new__(cls)
        inst.seed = 0
        inst._state = 0
        inst._inc = ((init_seq << 1) | 1) & MASK64
        inst.next_u32()
        inst._state = (inst._state + (init_state & MASK64)) & MASK64
        inst.next_u32()
        return inst

    def get_state(self) -> Tuple[int, int]:
        return (self._state, self._inc)

    def set_state(self, state_inc: Tuple[int, int]) -> None:
        self._state = state_inc[0] & MASK64
        self._inc = state_inc[1] & MASK64

    def next_u32(self) -> int:
        old = self._state
        self._state = (old * PCG_MULTIPLIER + self._inc) & MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & MASK32
        rot = old >> 59
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & MASK32

    def next_u64(self) -> int:
        hi = self.next_u32()
        lo = self.next_u32()
        return ((hi << 32) | lo) & MASK64

    def next_double(self) -> float:
        return (self.next_u64() >> 11) * DOUBLE_UNIT

    @staticmethod
    def bounded(rng_range: int, next_u32_fn: Callable[[], int]) -> int:
        rng = rng_range & MASK32
        threshold = ((1 << 32) - rng) % rng
        while True:
            r = next_u32_fn() & MASK32
            if r >= threshold:
                return r % rng

    def next_int(self, min_inclusive: int, max_exclusive: int) -> int:
        if max_exclusive <= min_inclusive:
            raise ValueError(f"max_exclusive ({max_exclusive}) must be > min_inclusive ({min_inclusive})")
        rng = max_exclusive - min_inclusive
        return min_inclusive + SimRandom.bounded(rng, self.next_u32)

    def roll_inclusive(self, min_val: int, max_val: int) -> int:
        return self.next_int(min_val, max_val + 1)

    def chance(self, p: float) -> bool:
        u = self.next_double()
        if math.isnan(p) or p <= 0.0:
            return False
        if p >= 1.0:
            return True
        return u < p

    def range(self, min_val: float, max_val: float) -> float:
        if max_val < min_val:
            raise ValueError(f"max_val ({max_val}) < min_val ({min_val})")
        return min_val + (max_val - min_val) * self.next_double()

    next_float = range

    @staticmethod
    def child_seed(parent_seed: int, name: str) -> int:
        _, out = splitmix64_next((parent_seed & MASK64) ^ fnv1a64(name))
        return out

    def derive(self, name: str) -> SimRandom:
        return SimRandom(SimRandom.child_seed(self.seed, name))

    @staticmethod
    def night_seed(run_seed: int, level_id: str, night_index: int) -> int:
        _, out = splitmix64_next((run_seed & MASK64) ^ fnv1a64(f"night:{level_id}:{night_index}"))
        return out

    @staticmethod
    def parse_seed(seed_str: str) -> int:
        if not seed_str:
            raise ValueError("seed_str must be non-empty")
        s = seed_str.strip()
        try:
            if s.startswith(("0x", "0X")):
                val = int(s, 16)
                if 0 <= val <= MASK64:
                    return val
            elif s.isdigit():
                val = int(s, 10)
                if 0 <= val <= MASK64:
                    return val
        except ValueError:
            pass
        return fnv1a64(s)


class ScriptedRandom(SimRandom):
    """Test double providing scripted NextDouble / NextUInt32 values (00_core.md §3.1.4)."""

    def __init__(
        self,
        doubles: Sequence[float] = (),
        u32s: Sequence[int] = (),
        seed: int = 0,
    ):
        self.seed = seed & MASK64
        self._state = 0
        self._inc = 1
        self._doubles = list(doubles)
        self._u32s = list(u32s)
        self.is_override = True

    def next_u32(self) -> int:
        if not self._u32s:
            raise RuntimeError("ScriptedRandom u32 sequence exhausted")
        return self._u32s.pop(0) & MASK32

    def next_double(self) -> float:
        if not self._doubles:
            raise RuntimeError("ScriptedRandom double sequence exhausted")
        return float(self._doubles.pop(0))


class StateHasher:
    """FNV-1a 64-bit little-endian canonical state hasher (00_core.md §3.7.1)."""

    def __init__(self, initial: int = FNV_OFFSET_BASIS):
        self.value: int = initial & MASK64

    def write_bytes(self, data: bytes) -> None:
        h = self.value
        for b in data:
            h ^= b
            h = (h * FNV_PRIME) & MASK64
        self.value = h

    def write_bool(self, v: bool) -> None:
        self.write_bytes(b"\x01" if v else b"\x00")

    def write_i32(self, v: int) -> None:
        self.write_bytes(struct.pack("<i", int(v)))

    def write_i64(self, v: int) -> None:
        self.write_bytes(struct.pack("<q", int(v)))

    def write_u64(self, v: int) -> None:
        self.write_bytes(struct.pack("<Q", int(v) & MASK64))

    def write_f64(self, v: float) -> None:
        fv = float(v)
        if math.isnan(fv):
            raise ValueError("StateHasher.write_f64: NaN is prohibited in canonical state hash")
        if fv == 0.0:
            fv = 0.0
        self.write_bytes(struct.pack("<d", fv))

    def write_str(self, s: Optional[str]) -> None:
        if s is None:
            self.write_i32(-1)
        else:
            raw = s.encode("utf-8")
            self.write_i32(len(raw))
            self.write_bytes(raw)

    def write_enum(self, v: int) -> None:
        self.write_i32(int(v))

    def write_vec2(self, v: Vec2) -> None:
        self.write_f64(v.x)
        self.write_f64(v.y)

    def write_opt_i32(self, v: Optional[int]) -> None:
        if v is None:
            self.write_bool(False)
        else:
            self.write_bool(True)
            self.write_i32(v)

    def write_opt_f64(self, v: Optional[float]) -> None:
        if v is None:
            self.write_bool(False)
        else:
            self.write_bool(True)
            self.write_f64(v)

    def write_opt_vec2(self, v: Optional[Vec2]) -> None:
        if v is None:
            self.write_bool(False)
        else:
            self.write_bool(True)
            self.write_vec2(v)

    def hex_str(self) -> str:
        return f"0x{self.value:016X}"
