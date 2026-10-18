"""Terrain elevation sampling, line-of-sight, and multi-ridge HorizonProfile (01_spawn_movement_terrain.md §3.3)."""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
from .core import Vec2


@dataclass(frozen=True)
class Heightmap:
    width_px: int
    height_px: int
    meters_per_pixel: float
    min_elevation_m: float
    max_elevation_m: float
    elevation_m: Sequence[float]


@dataclass(frozen=True)
class TerrainRules:
    los_sample_step_px: float = 0.5
    earth_radius_m: Optional[float] = 6371000.0
    refraction_k: float = 1.3333333333333333
    default_antenna_height_m: float = 10.0
    horizon_azimuth_bins: int = 720


class HorizonProfile:
    """Precomputed radial cumulative max-slope envelope for O(1) multi-ridge LOS (01 §3.3.4)."""

    def __init__(
        self,
        terrain: TerrainModel,
        observer: Vec2,
        observer_agl_m: float,
        max_range_m: float,
        azimuth_bins: Optional[int] = None,
    ):
        self.terrain = terrain
        self.observer_pos = observer
        self.observer_msl_m = terrain.elevation_at(observer.x, observer.y) + observer_agl_m
        self.step_m = terrain.los_step_m
        self.r_eff_m = terrain.r_eff_m
        self.azimuth_bins = azimuth_bins if azimuth_bins is not None else terrain.horizon_azimuth_bins
        self.radial_steps = max(1, int(math.ceil(max_range_m / self.step_m)))
        self.max_slope: List[List[float]] = []

        twopi = 2.0 * math.pi
        for b in range(self.azimuth_bins):
            theta = twopi * b / self.azimuth_bins
            ux = math.cos(theta)
            uy = math.sin(theta)
            row: List[float] = [-math.inf]
            prev = -math.inf
            for j in range(1, self.radial_steps + 1):
                s = j * self.step_m
                elev = terrain.elevation_at(observer.x + ux * s, observer.y + uy * s)
                curv = 0.0 if self.r_eff_m is None else s / (2.0 * self.r_eff_m)
                slope = (elev - self.observer_msl_m) / s - curv
                if slope > prev:
                    prev = slope
                row.append(prev)
            self.max_slope.append(row)

    def has_line_of_sight(self, target: Vec2, target_msl_m: float) -> bool:
        dx = target.x - self.observer_pos.x
        dy = target.y - self.observer_pos.y
        d = math.sqrt(dx * dx + dy * dy)
        if d <= self.step_m:
            return True
        ang = math.atan2(dy, dx)
        if ang < 0.0:
            ang += 2.0 * math.pi
        b = int(math.floor(ang * self.azimuth_bins / (2.0 * math.pi) + 0.5)) % self.azimuth_bins
        j = min(max(int(math.ceil(d / self.step_m)) - 1, 1), self.radial_steps)
        curv = 0.0 if self.r_eff_m is None else d / (2.0 * self.r_eff_m)
        target_slope = (target_msl_m - self.observer_msl_m) / d - curv
        return target_slope >= self.max_slope[b][j]

    def has_line_of_sight_agl(self, target: Vec2, target_agl_m: float) -> bool:
        return self.has_line_of_sight(
            target, self.terrain.elevation_at(target.x, target.y) + target_agl_m
        )


class TerrainModel:
    """Bilinear terrain elevation and exact/cached line-of-sight model (01 §3.3)."""

    def __init__(self, heightmap: Heightmap, rules: Optional[TerrainRules] = None):
        if rules is None:
            rules = TerrainRules()
        self.heightmap = heightmap
        self.width_px = heightmap.width_px
        self.height_px = heightmap.height_px
        self.meters_per_pixel = heightmap.meters_per_pixel
        self.extent_x_m = self.width_px * self.meters_per_pixel
        self.extent_y_m = self.height_px * self.meters_per_pixel
        self.elev = list(heightmap.elevation_m)
        self.min_elevation_m = min(self.elev) if self.elev else 0.0
        self.max_elevation_m = max(self.elev) if self.elev else 0.0
        self.los_step_m = rules.los_sample_step_px * self.meters_per_pixel
        self.r_eff_m: Optional[float] = (
            None
            if rules.earth_radius_m is None
            else rules.refraction_k * rules.earth_radius_m
        )
        self.default_antenna_height_m = rules.default_antenna_height_m
        self.horizon_azimuth_bins = rules.horizon_azimuth_bins

    def elevation_at(self, x: float, y: float) -> float:
        m = self.meters_per_pixel
        fx = x / m - 0.5
        fy = (self.extent_y_m - y) / m - 0.5
        fx = min(max(fx, 0.0), float(self.width_px - 1))
        fy = min(max(fy, 0.0), float(self.height_px - 1))
        c0 = int(math.floor(fx))
        r0 = int(math.floor(fy))
        if c0 > self.width_px - 2:
            c0 = max(self.width_px - 2, 0)
        if r0 > self.height_px - 2:
            r0 = max(self.height_px - 2, 0)
        c1 = min(c0 + 1, self.width_px - 1)
        r1 = min(r0 + 1, self.height_px - 1)
        tx = fx - c0
        ty = fy - r0
        w = self.width_px
        e00 = self.elev[r0 * w + c0]
        e01 = self.elev[r0 * w + c1]
        e10 = self.elev[r1 * w + c0]
        e11 = self.elev[r1 * w + c1]
        top = e00 + (e01 - e00) * tx
        bot = e10 + (e11 - e10) * tx
        return top + (bot - top) * ty

    def elevation_at_vec(self, pos: Vec2) -> float:
        return self.elevation_at(pos.x, pos.y)

    def has_line_of_sight(self, a: Vec2, a_msl_m: float, b: Vec2, b_msl_m: float) -> bool:
        dx = b.x - a.x
        dy = b.y - a.y
        d = math.sqrt(dx * dx + dy * dy)
        if d <= self.los_step_m:
            return True
        cmax = 0.0 if self.r_eff_m is None else (d * d) / (8.0 * self.r_eff_m)
        if min(a_msl_m, b_msl_m) > self.max_elevation_m + cmax + 1e-6:
            return True
        n = int(math.ceil(d / self.los_step_m))
        for i in range(1, n):
            f = float(i) / float(n)
            px = a.x + dx * f
            py = a.y + dy * f
            ray = a_msl_m + (b_msl_m - a_msl_m) * f
            s = d * f
            drop = 0.0 if self.r_eff_m is None else (s * (d - s)) / (2.0 * self.r_eff_m)
            if self.elevation_at(px, py) + drop > ray:
                return False
        return True

    def has_line_of_sight_agl(self, a: Vec2, a_agl_m: float, b: Vec2, b_agl_m: float) -> bool:
        a_msl = self.elevation_at(a.x, a.y) + a_agl_m
        b_msl = self.elevation_at(b.x, b.y) + b_agl_m
        return self.has_line_of_sight(a, a_msl, b, b_msl)

    def build_horizon_profile(
        self,
        observer: Vec2,
        observer_agl_m: float,
        max_range_m: float,
        azimuth_bins: Optional[int] = None,
    ) -> HorizonProfile:
        return HorizonProfile(self, observer, observer_agl_m, max_range_m, azimuth_bins)
