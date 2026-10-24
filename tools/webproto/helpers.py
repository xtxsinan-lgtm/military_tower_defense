"""Terrain coverage, preset deployments, event formatting, and battle report helpers for tools.webproto."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tools.papersim.core import SimRandom, Vec2
from tools.papersim.entities import (
    CarryIn,
    DeploymentPlan,
    NightOutcome,
    PlacedUnit,
    PlayerUnitCategory,
    SimEvent,
    SimEventType,
    TargetTag,
)
from tools.papersim.loader import DataLoader, FileSystemDataSource, LevelData
from tools.papersim.terrain import TerrainModel, TerrainRules
from tools.papersim.world import DefaultDeploymentBuilder, DeploymentValidator, SimWorld

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data"

_SOURCE: Optional[FileSystemDataSource] = None
_LEVEL_CACHE: Dict[Tuple[str, int], LevelData] = {}
_LOC_CACHE: Optional[Dict[str, str]] = None
_HORIZON_CACHE: Dict[Tuple[Any, ...], Any] = {}
_ORIG_BUILD_HORIZON = TerrainModel.build_horizon_profile


def _cached_build_horizon(
    self: TerrainModel,
    observer: Vec2,
    observer_agl_m: float,
    max_range_m: float,
    azimuth_bins: Optional[int] = None,
) -> Any:
    key = (
        id(self.heightmap),
        round(observer.x, 1),
        round(observer.y, 1),
        round(observer_agl_m, 1),
        round(max_range_m, 1),
        azimuth_bins,
    )
    prof = _HORIZON_CACHE.get(key)
    if prof is None:
        prof = _ORIG_BUILD_HORIZON(self, observer, observer_agl_m, max_range_m, azimuth_bins)
        _HORIZON_CACHE[key] = prof
    return prof


TerrainModel.build_horizon_profile = _cached_build_horizon  # type: ignore[method-assign]


_WEBPROTO_LOC_OVERRIDES: Dict[str, str] = {
    "unit.mobile_fire_team.name": "皮卡高射机枪组",
    "unit.iris_t_sls.name": "IRIS‑T 近程导弹车",
    "unit.nasams.name": "NASAMS 中程防空导弹",
    "sensor.soviet_mid_range_radar.name": "苏制警戒雷达站",
    "sensor.acoustic_post.name": "声学听音哨",
    "sensor.visual_observer.name": "目视观察哨",
    "weapon.mobile_fire_team_gun.name": "双联12.7mm高射机枪",
    "weapon.iris_t_sls_missile.name": "IRIS‑T 近程导弹",
    "weapon.nasams_missile.name": "AIM‑120 中程导弹",
}


def get_loc() -> Dict[str, str]:
    global _LOC_CACHE
    if _LOC_CACHE is None:
        loc_path = DATA_ROOT / "loc" / "zh.json"
        with open(loc_path, "r", encoding="utf-8") as f:
            _LOC_CACHE = json.load(f)
    return _LOC_CACHE


def tr(key: str, default: Optional[str] = None) -> str:
    if key in _WEBPROTO_LOC_OVERRIDES:
        return _WEBPROTO_LOC_OVERRIDES[key]
    loc = get_loc()
    if key in loc:
        return loc[key]
    return default if default is not None else key


def load_level_cached(level_id: str = "test_01", night_index: int = 1) -> LevelData:
    global _SOURCE
    if _SOURCE is None:
        _SOURCE = FileSystemDataSource(str(DATA_ROOT))
    key = (level_id, int(night_index))
    if key not in _LEVEL_CACHE:
        _LEVEL_CACHE[key] = DataLoader.load_level(_SOURCE, level_id, night_index=int(night_index))
    return _LEVEL_CACHE[key]


def build_terrain_model(level: LevelData) -> TerrainModel:
    tr_cfg = level.catalog.rules.get("terrain", {})
    tr_rules = TerrainRules(
        los_sample_step_px=float(tr_cfg.get("losSampleStepPx", 0.5)),
        earth_radius_m=float(tr_cfg["earthRadiusM"]) if tr_cfg.get("earthRadiusM") is not None else 6371000.0,
        refraction_k=float(tr_cfg.get("refractionK", 1.3333333333333333)),
        default_antenna_height_m=float(tr_cfg.get("defaultAntennaHeightM", 10.0)),
        horizon_azimuth_bins=int(tr_cfg.get("horizonAzimuthBins", 720)),
    )
    return TerrainModel(level.heightmap, tr_rules)


def format_clock(world_sec: float) -> str:
    """Format world_sec as 24h clock starting from 22:00:00."""
    total_sec = int(round(22 * 3600 + world_sec))
    hh = (total_sec // 3600) % 24
    mm = (total_sec % 3600) // 60
    ss = total_sec % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def downsample_elevation(terrain: TerrainModel, grid_size: int = 100) -> List[List[float]]:
    """Return grid_size x grid_size elevation grid (row iy=0 is South y=0, col ix=0 is West x=0)."""
    w_m = terrain.extent_x_m
    h_m = terrain.extent_y_m
    rows: List[List[float]] = []
    for iy in range(grid_size):
        y = (iy + 0.5) * (h_m / grid_size)
        row: List[float] = []
        for ix in range(grid_size):
            x = (ix + 0.5) * (w_m / grid_size)
            row.append(round(terrain.elevation_at(x, y), 1))
        rows.append(row)
    return rows


def build_preset_placements(
    level: LevelData,
    preset_name: str,
    carry_in: Optional[CarryIn] = None,
) -> List[Dict[str, Any]]:
    """Build preset deployment ('default', 'layered', 'stacked') adapted to CarryIn if present."""
    pos_rules = level.catalog.rules.get("positions", {})
    min_spacing_m = float(pos_rules.get("minSpacingM", 100.0))

    if preset_name == "layered":
        raw_coords = [
            (1, "mobile_fire_team", Vec2(16200.0, 12200.0)),
            (2, "mobile_fire_team", Vec2(16500.0, 11000.0)),
            (3, "mobile_fire_team", Vec2(16200.0, 9600.0)),
            (4, "mobile_fire_team", Vec2(15000.0, 8800.0)),
            (5, "iris_t_sls", Vec2(12800.0, 10200.0)),
            (6, "nasams", Vec2(10800.0, 9600.0)),
            (7, "soviet_mid_range_radar", Vec2(11500.0, 10600.0)),
            (8, "acoustic_post", Vec2(18200.0, 12200.0)),
            (9, "acoustic_post", Vec2(18400.0, 11200.0)),
            (10, "acoustic_post", Vec2(18400.0, 10200.0)),
            (11, "acoustic_post", Vec2(18000.0, 8600.0)),
            (12, "acoustic_post", Vec2(12500.0, 13600.0)),
            (13, "acoustic_post", Vec2(15500.0, 7800.0)),
            (14, "visual_observer", Vec2(17200.0, 12000.0)),
            (15, "visual_observer", Vec2(17200.0, 10600.0)),
            (16, "visual_observer", Vec2(17000.0, 9000.0)),
        ]
    elif preset_name == "stacked":
        base_units = [
            (1, "mobile_fire_team"), (2, "mobile_fire_team"), (3, "mobile_fire_team"), (4, "mobile_fire_team"),
            (5, "iris_t_sls"), (6, "nasams"), (7, "soviet_mid_range_radar"),
            (8, "acoustic_post"), (9, "acoustic_post"), (10, "acoustic_post"),
            (11, "acoustic_post"), (12, "acoustic_post"), (13, "acoustic_post"),
            (14, "visual_observer"), (15, "visual_observer"), (16, "visual_observer"),
        ]
        raw_coords = []
        for idx, (rid, udef) in enumerate(base_units):
            ring = idx // 6
            slot = idx % 6
            r = 140.0 + ring * 130.0
            angle = slot * (2.0 * math.pi / 6.0) + ring * 0.3
            raw_coords.append(
                (rid, udef, Vec2(round(11000.0 + r * math.cos(angle), 1), round(9800.0 + r * math.sin(angle), 1)))
            )
    else:
        plan = DefaultDeploymentBuilder.build(level, carry_in if preset_name == "carry_in" else None)
        raw_coords = [(pu.roster_id or (i + 1), pu.unit_def_id, pu.pos) for i, pu in enumerate(plan.units)]

    alive_by_rid: Dict[int, Dict[str, Any]] = {}
    if carry_in and carry_in.units:
        for cu in carry_in.units:
            if not cu.get("destroyed", False):
                alive_by_rid[int(cu.get("rosterId", 0))] = cu

    existing: List[Vec2] = []
    out: List[Dict[str, Any]] = []
    for idx, (rid, uid, pos) in enumerate(raw_coords):
        if alive_by_rid and rid not in alive_by_rid:
            continue
        ok, _, _ = DeploymentValidator.is_valid_pos(pos, level, existing, min_spacing_m)
        cand = pos if ok else DefaultDeploymentBuilder._find_pos(pos, idx, level, existing, min_spacing_m)
        existing.append(cand)
        out.append(make_placement_dict(level, rid, uid, cand, carry_in=carry_in))
    return out


def make_placement_dict(
    level: LevelData,
    roster_id: int,
    unit_def_id: str,
    pos: Vec2,
    alt_id: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
    carry_in: Optional[CarryIn] = None,
) -> Dict[str, Any]:
    cat = level.catalog
    udef = cat.get_player_unit_def(unit_def_id)
    ucategory = cat.get_player_unit_category(unit_def_id).name.lower()
    st = dict(settings or {})
    st.setdefault("emissionPolicyId", "continuous")
    st.setdefault("ammoReserve", 2 if unit_def_id in ("nasams", "iris_t_sls") else 0)
    st.setdefault("engagementRule", "any")
    st.setdefault("whitelist", ["UAV", "JET_UAV", "CM", "SCM", "BM", "HBM", "GB", "HELI", "AC_LOW", "AC_HIGH"])
    st.setdefault("shootLookShoot", True)
    st.setdefault("nightAids", ["searchlight"] if unit_def_id == "mobile_fire_team" else [])

    exposed = False
    exp_val = 0.0
    if carry_in:
        for cu in carry_in.units or []:
            if int(cu.get("rosterId", 0)) == roster_id:
                exp_val = float(cu.get("exposure", 0.0))
        for kt in carry_in.known_targets or []:
            kp = kt.get("pos", [0.0, 0.0])
            if int(kt.get("rosterId", 0)) == roster_id or math.hypot(pos.x - kp[0], pos.y - kp[1]) <= 600.0:
                exposed = True
                exp_val = max(exp_val, float(kt.get("exposure", 70.0)))

    return {
        "rosterId": roster_id,
        "unitDefId": unit_def_id,
        "name": tr(udef.get("nameKey", unit_def_id), unit_def_id),
        "category": ucategory,
        "pos": [round(pos.x, 1), round(pos.y, 1)],
        "alternatePositionId": alt_id,
        "settings": st,
        "isExposed": exposed,
        "carryExposure": round(exp_val, 1),
    }


def compute_coverage_and_validation(
    level: LevelData,
    terrain: TerrainModel,
    placements: Sequence[Dict[str, Any]],
    alt_m: float = 100.0,
    grid_res: int = 64,
) -> Dict[str, Any]:
    """Compute 3-state terrain occlusion grid (0=out of range, 1=ridge blind spot, 2=visible) and validate deployment."""
    cat = level.catalog
    pos_rules = cat.rules.get("positions", {})
    min_spacing_m = float(pos_rules.get("minSpacingM", 100.0))
    def_ant = float(cat.rules.get("terrain", {}).get("defaultAntennaHeightM", 10.0))
    det_rules = cat.rules.get("tracks", {}).get("detectionRules", {})
    low_below = float(det_rules.get("lowAltitudeBelowM", 200.0))
    low_map = det_rules.get("lowAltitudeRangeMult", {"none": 0.0, "poor": 0.25, "medium": 0.5, "good": 0.75})

    errors: List[Dict[str, Any]] = []
    existing_pos: List[Vec2] = []
    sensor_sources: List[Tuple[Vec2, float, Optional[Any]]] = []
    unit_rings: List[Dict[str, Any]] = []

    for idx, p in enumerate(placements):
        uid = str(p.get("unitDefId", ""))
        raw_pos = p.get("pos", [0.0, 0.0])
        pos = Vec2(float(raw_pos[0]), float(raw_pos[1]))
        rid = int(p.get("rosterId", idx + 1))
        ok, code, msg = DeploymentValidator.is_valid_pos(pos, level, existing_pos, min_spacing_m)
        if not ok:
            errors.append({"index": idx, "rosterId": rid, "unitDefId": uid, "code": code, "message": msg})
        existing_pos.append(pos)

        st = p.get("settings") or {}
        pol = st.get("emissionPolicyId", "continuous")
        cat_enum = cat.get_player_unit_category(uid)
        udef = cat.get_player_unit_def(uid)
        w_ranges: List[float] = []
        det_r = 0.0

        if cat_enum == PlayerUnitCategory.Sensor:
            r_base = float(udef.get("detectionRangeM") or 0.0)
            if r_base > 0.0 and pol != "silent":
                r_eff = r_base
                if udef.get("nightRangeMult") is not None:
                    r_eff *= float(udef["nightRangeMult"])
                if alt_m < low_below:
                    low_cap = udef.get("lowAltitude", "medium")
                    r_eff *= float(low_map.get(low_cap, 0.5))
                    if udef.get("largeLowAltitudeBlindZone"):
                        r_eff *= float(det_rules.get("largeBlindZoneLowAltitudeRangeMult", 0.5))
                det_r = r_eff
                los = udef.get("lineOfSight", True) is not False
                ant = float(udef.get("antennaHeightM") or def_ant)
                hp = terrain.build_horizon_profile(pos, ant, min(r_eff * 1.1, 28000.0), azimuth_bins=360) if los else None
                sensor_sources.append((pos, r_eff, hp))
        elif cat_enum == PlayerUnitCategory.Fire:
            for wid in udef.get("weaponIds", []):
                wdef = cat.weapons.get(wid, {})
                w_ranges.append(float(wdef.get("rangeM", 0.0)))
            fcr = udef.get("fireControlRadar")
            if fcr is not None and pol != "silent":
                r_eff = float(fcr.get("rangeM", 0.0))
                if alt_m < low_below:
                    r_eff *= float(low_map.get(fcr.get("lowAltitude", "good"), 0.75))
                det_r = r_eff
                ant = float(fcr.get("antennaHeightM") or def_ant)
                hp = terrain.build_horizon_profile(pos, ant, min(r_eff * 1.1, 28000.0), azimuth_bins=360)
                sensor_sources.append((pos, r_eff, hp))
            elif udef.get("selfAcquisitionRangeM") is not None:
                r_eff = float(udef["selfAcquisitionRangeM"]) * 0.7
                det_r = r_eff
                hp = terrain.build_horizon_profile(pos, def_ant, min(r_eff * 1.1, 28000.0), azimuth_bins=360)
                sensor_sources.append((pos, r_eff, hp))

        unit_rings.append({
            "rosterId": rid,
            "unitDefId": uid,
            "pos": [pos.x, pos.y],
            "detectionRangeM": round(det_r, 1),
            "weaponRangesM": w_ranges,
            "valid": ok,
        })

    w_m = terrain.extent_x_m
    h_m = terrain.extent_y_m
    grid: List[List[int]] = []
    vis_cells = 0
    blind_cells = 0
    for iy in range(grid_res):
        cy = (iy + 0.5) * (h_m / grid_res)
        row: List[int] = []
        for ix in range(grid_res):
            cx = (ix + 0.5) * (w_m / grid_res)
            pt = Vec2(cx, cy)
            pt_msl = terrain.elevation_at(cx, cy) + alt_m
            state = 0
            for spos, r_eff, hp in sensor_sources:
                dx = cx - spos.x
                dy = cy - spos.y
                if dx * dx + dy * dy <= r_eff * r_eff:
                    if hp is None or hp.has_line_of_sight(pt, pt_msl):
                        state = 2
                        break
                    else:
                        state = max(state, 1)
            if state == 2:
                vis_cells += 1
            elif state == 1:
                blind_cells += 1
            row.append(state)
        grid.append(row)

    tot_cells = max(1, grid_res * grid_res)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "altM": alt_m,
        "gridRes": grid_res,
        "grid": grid,
        "stats": {
            "visibleFrac": round(vis_cells / tot_cells, 4),
            "blindFrac": round(blind_cells / tot_cells, 4),
        },
        "unitRings": unit_rings,
    }
