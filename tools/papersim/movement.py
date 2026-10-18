"""Wave spawning, enemy movement, kinematics, routing, and AI hook interfaces (01_spawn_movement_terrain.md)."""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from .core import Geo, SimError, SimRandom, SimTime, Vec2
from .entities import (
    AiTag,
    MotionProfile,
    PathEndAction,
    PendingRelease,
    PendingSpawn,
    SimEventType,
    SimState,
    TargetTag,
    Threat,
    ThreatExitReason,
    ThreatKind,
    ThreatPhase,
    ThreatTargetKind,
    WaveInjection,
)


@dataclass(frozen=True)
class TargetChoice:
    kind: ThreatTargetKind
    pos: Vec2
    structure_id: int = 0
    unit_id: int = 0


@dataclass(frozen=True)
class TargetRequest:
    enemy_id: str
    kind: ThreatKind
    wave_id: str
    wave_index: int
    group_index: int
    ordinal: int
    entry_pos: Vec2


@dataclass(frozen=True)
class AvoidanceRequest:
    enemy_id: str
    tag: TargetTag
    wave_id: str
    a50_active: bool
    bypass_tagged: bool


class IEnemyAiHooks:
    def select_known_target(self, state: SimState, level: Any, req: TargetRequest, rng: SimRandom) -> Optional[TargetChoice]:
        return None

    def select_air_defense_target(self, state: SimState, level: Any, req: TargetRequest, rng: SimRandom) -> Optional[TargetChoice]:
        return None

    def select_weighted_random_override(self, state: SimState, level: Any, req: TargetRequest, rng: SimRandom) -> Optional[TargetChoice]:
        return None

    def adjust_avoidance(self, state: SimState, level: Any, req: AvoidanceRequest, path: Sequence[Vec2]) -> List[Vec2]:
        return list(path)

    def defer_group(self, level: Any, night: Dict[str, Any], wave_index: int, group_index: int) -> bool:
        return False

    def saturation_spawn_times(
        self, state: SimState, level: Any, night: Dict[str, Any], wave_index: int, group_indices: Sequence[int], base_sec: float
    ) -> Optional[List[float]]:
        return None


class DefaultEnemyAiHooks(IEnemyAiHooks):
    pass


class EnemyAiQueries:
    @staticmethod
    def avoidance_active(state: SimState, catalog: Any) -> bool:
        for i in range(state.threats.count):
            th = state.threats[i]
            if not th.alive or th.kind != ThreatKind.Platform or th.phase == ThreatPhase.Arrived:
                continue
            pdef = catalog.platforms.get(th.def_id or "")
            if pdef and pdef.get("whileAlive", {}) and pdef["whileAlive"].get("cruiseMissilesAvoidAirDefense"):
                return True
        return False


class ThreatPath:
    @staticmethod
    def compute_cum_m(pts: Sequence[Vec2]) -> List[float]:
        cum = [0.0]
        for i in range(len(pts) - 1):
            dx = pts[i + 1].x - pts[i].x
            dy = pts[i + 1].y - pts[i].y
            cum.append(cum[-1] + math.sqrt(dx * dx + dy * dy))
        return cum

    @staticmethod
    def set_path(th: Threat, pts: Sequence[Vec2], bump_version: bool = False) -> None:
        th.path = list(pts)
        th.path_cum_m = ThreatPath.compute_cum_m(th.path)
        th.path_length_m = th.path_cum_m[-1] if th.path_cum_m else 0.0
        if bump_version:
            th.path_version += 1

    @staticmethod
    def pos_on_polyline(pts: Sequence[Vec2], cum: Sequence[float], s: float) -> Vec2:
        if len(pts) == 1:
            return pts[0]
        l_tot = cum[-1]
        sc = min(max(s, 0.0), l_tot)
        lo, hi = 0, len(pts) - 2
        idx = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if cum[mid] <= sc:
                idx = mid
                lo = mid + 1
            else:
                hi = mid - 1
        seg = cum[idx + 1] - cum[idx]
        if seg <= 0.0:
            return pts[idx]
        f = (sc - cum[idx]) / seg
        return Vec2(
            pts[idx].x + (pts[idx + 1].x - pts[idx].x) * f,
            pts[idx].y + (pts[idx + 1].y - pts[idx].y) * f,
        )

    @staticmethod
    def dir_on_polyline(pts: Sequence[Vec2], cum: Sequence[float], s: float) -> Vec2:
        if len(pts) <= 1:
            return Vec2(0.0, 0.0)
        l_tot = cum[-1]
        sc = min(max(s, 0.0), l_tot)
        lo, hi = 0, len(pts) - 2
        idx = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if cum[mid] <= sc:
                idx = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if s < l_tot:
            for k in range(idx, len(pts) - 1):
                seg = cum[k + 1] - cum[k]
                if seg > 0.0:
                    return (pts[k + 1] - pts[k]) / seg
        for k in range(len(pts) - 2, -1, -1):
            if k <= idx or s >= l_tot:
                seg = cum[k + 1] - cum[k]
                if seg > 0.0:
                    return (pts[k + 1] - pts[k]) / seg
        return Vec2(0.0, 0.0)

    @staticmethod
    def truncate_at(pts: Sequence[Vec2], cum: Sequence[float], s_turn: float) -> List[Vec2]:
        if s_turn <= 0.0:
            return [pts[0]]
        out: List[Vec2] = [pts[0]]
        for k in range(1, len(pts)):
            if cum[k] < s_turn:
                out.append(pts[k])
            else:
                end_pt = ThreatPath.pos_on_polyline(pts, cum, s_turn)
                if end_pt != out[-1]:
                    out.append(end_pt)
                break
        return out


@dataclass(frozen=True)
class ThreatPose:
    pos: Vec2
    alt_m: float
    vel_mps: Vec2
    vert_speed_mps: float
    path_arc_m: float
    at_path_end: bool


@dataclass(frozen=True)
class MotionLeg:
    start_sec: float
    end_sec: float
    start_pos: Vec2
    vel_mps: Vec2
    start_alt_m: float
    vert_speed_mps: float
    vert_accel_mps2: float


class ThreatKinematics:
    """Analytical threat kinematics and trajectory predictor (01 §3.2.3 & §3.2.9)."""

    @staticmethod
    def s_at(th: Threat, t: float) -> float:
        tau = t - th.anchor_sec
        sa = th.anchor_arc_m
        sd = th.terminal_start_arc_m
        v1 = th.speed_mps
        v2 = th.terminal_speed_mps
        l_tot = th.path_length_m
        if tau <= 0.0 or v1 <= 0.0:
            return min(sa, l_tot)
        if sa >= sd:
            s = sa + v2 * tau
        else:
            tau1 = (sd - sa) / v1
            if tau <= tau1:
                s = sa + v1 * tau
            else:
                s = sd + v2 * (tau - tau1)
        return min(s, l_tot)

    @staticmethod
    def time_at_s(th: Threat, x: float) -> float:
        ta = th.anchor_sec
        sa = th.anchor_arc_m
        sd = th.terminal_start_arc_m
        v1 = th.speed_mps
        v2 = th.terminal_speed_mps
        if x <= sa:
            return ta
        if sa >= sd:
            return ta + (x - sa) / v2 if v2 > 0.0 else ta
        if x <= sd:
            return ta + (x - sa) / v1 if v1 > 0.0 else ta
        return ta + (sd - sa) / v1 + (x - sd) / v2

    @staticmethod
    def pos_at_s(th: Threat, s: float) -> Vec2:
        return ThreatPath.pos_on_polyline(th.path, th.path_cum_m, s)

    @staticmethod
    def dir_at_s(th: Threat, s: float) -> Vec2:
        return ThreatPath.dir_on_polyline(th.path, th.path_cum_m, s)

    @staticmethod
    def speed_at_s(th: Threat, s: float) -> float:
        return th.speed_mps if s < th.terminal_start_arc_m else th.terminal_speed_mps

    @staticmethod
    def alt_at_s(th: Threat, s: float) -> float:
        l_tot = th.path_length_m
        a0 = th.start_alt_m
        a_end = th.end_alt_m
        sd = th.terminal_start_arc_m
        if th.profile == MotionProfile.Parabolic:
            if l_tot <= 0.0:
                return 0.0
            return a0 * ((l_tot - s) * (l_tot + s)) / (l_tot * l_tot)
        if s <= sd or l_tot <= sd:
            return a0
        return a_end + (a0 - a_end) * (l_tot - s) / (l_tot - sd)

    @staticmethod
    def vert_at_s(th: Threat, s: float) -> float:
        l_tot = th.path_length_m
        if s >= l_tot or l_tot <= 0.0:
            return 0.0
        spd = ThreatKinematics.speed_at_s(th, s)
        a0 = th.start_alt_m
        a_end = th.end_alt_m
        sd = th.terminal_start_arc_m
        if th.profile == MotionProfile.Parabolic:
            return -2.0 * a0 * s / (l_tot * l_tot) * spd
        if s < sd or l_tot <= sd:
            return 0.0
        return -(a0 - a_end) / (l_tot - sd) * spd

    @staticmethod
    def predict(th: Threat, at_sec: float) -> ThreatPose:
        if at_sec < th.last_update_sec - 1e-9:
            raise ValueError(f"at_sec ({at_sec}) < th.last_update_sec ({th.last_update_sec})")
        if th.phase in (ThreatPhase.Arrived, ThreatPhase.Holding):
            return ThreatPose(th.pos, th.alt_m, Vec2(0.0, 0.0), 0.0, th.path_arc_m, True)
        s = ThreatKinematics.s_at(th, at_sec)
        l_tot = th.path_length_m
        pos = ThreatKinematics.pos_at_s(th, s)
        at_end = s >= l_tot
        alt = th.end_alt_m if (at_end and th.path_end == PathEndAction.Arrive) else ThreatKinematics.alt_at_s(th, s)
        vel = Vec2(0.0, 0.0) if at_end else ThreatKinematics.dir_at_s(th, s) * ThreatKinematics.speed_at_s(th, s)
        vz = ThreatKinematics.vert_at_s(th, s)
        return ThreatPose(pos, alt, vel, vz, s, at_end)

    @staticmethod
    def predict_arrival_sec(th: Threat) -> Optional[float]:
        if th.path_end != PathEndAction.Arrive:
            return None
        if th.phase == ThreatPhase.Arrived:
            return th.arrived_at_sec
        return ThreatKinematics.time_at_s(th, th.path_length_m)

    @staticmethod
    def max_speed_3d_mps(th: Threat) -> float:
        if th.phase in (ThreatPhase.Arrived, ThreatPhase.Holding) or th.path_length_m <= 0.0:
            return 0.0
        vh_max = max(th.speed_mps, th.terminal_speed_mps)
        l_tot = th.path_length_m
        sd = th.terminal_start_arc_m
        if th.profile == MotionProfile.Parabolic:
            max_slope = 2.0 * th.start_alt_m / l_tot
        else:
            max_slope = abs(th.start_alt_m - th.end_alt_m) / (l_tot - sd) if l_tot > sd else 0.0
        return vh_max * math.sqrt(1.0 + max_slope * max_slope)

    @staticmethod
    def legs(th: Threat, from_sec: float) -> List[MotionLeg]:
        if th.phase in (ThreatPhase.Arrived, ThreatPhase.Holding):
            return [MotionLeg(from_sec, math.inf, th.pos, Vec2(0.0, 0.0), th.alt_m, 0.0, 0.0)]
        s_from = ThreatKinematics.s_at(th, from_sec)
        l_tot = th.path_length_m
        breaks = [from_sec, ThreatKinematics.time_at_s(th, l_tot)]
        for c_arc in th.path_cum_m:
            if s_from < c_arc < l_tot:
                breaks.append(ThreatKinematics.time_at_s(th, c_arc))
        sd = th.terminal_start_arc_m
        if s_from < sd < l_tot:
            breaks.append(ThreatKinematics.time_at_s(th, sd))
        breaks = sorted(set(breaks))
        out: List[MotionLeg] = []
        for i in range(len(breaks) - 1):
            t0, t1 = breaks[i], breaks[i + 1]
            if t1 <= t0:
                continue
            s0 = ThreatKinematics.s_at(th, t0)
            smid = ThreatKinematics.s_at(th, 0.5 * (t0 + t1))
            start_pos = ThreatKinematics.pos_at_s(th, s0)
            v = ThreatKinematics.speed_at_s(th, smid)
            vel = ThreatKinematics.dir_at_s(th, smid) * v
            start_alt = ThreatKinematics.alt_at_s(th, s0)
            if th.profile == MotionProfile.Parabolic and l_tot > 0.0:
                vz = -2.0 * th.start_alt_m * s0 / (l_tot * l_tot) * v
                az = -2.0 * th.start_alt_m * v * v / (l_tot * l_tot)
            else:
                vz = ThreatKinematics.vert_at_s(th, smid)
                az = 0.0
            out.append(MotionLeg(t0, t1, start_pos, vel, start_alt, vz, az))
        if th.path_end == PathEndAction.Hold:
            t_end = ThreatKinematics.time_at_s(th, l_tot)
            out.append(MotionLeg(t_end, math.inf, th.path[-1], Vec2(0.0, 0.0), th.start_alt_m, 0.0, 0.0))
        return out


class ThreatRouting:
    """Retarget, BeginEgress, and Hover interfaces for EW/AI systems (01 §3.2.8)."""

    @staticmethod
    def _recompute_profile_on_retarget(th: Threat, catalog: Any) -> None:
        m_rules = catalog.rules["movement"]
        m_def = catalog.munitions[th.def_id or ""]
        band = m_def["altitudeBand"]
        l_tot = th.path_length_m
        a0 = th.start_alt_m
        if band in ("ballistic", "quasi_ballistic", "terminal_maneuver"):
            th.profile = MotionProfile.Parabolic
            th.terminal_start_arc_m = 0.0
            th.end_alt_m = 0.0
        elif band in ("glide", "carrier"):
            th.profile = MotionProfile.Linear
            th.terminal_start_arc_m = 0.0
            th.end_alt_m = 0.0
        elif band == "high_dive":
            th.profile = MotionProfile.Linear
            angle_rad = float(m_rules.get("highDiveAngleRad", math.radians(45.0)))
            th.terminal_start_arc_m = max(0.0, l_tot - a0 / math.tan(angle_rad))
            th.end_alt_m = 0.0
        else:
            th.profile = MotionProfile.Linear
            angle_rad = float(m_rules.get("cruiseDescentAngleRad", math.radians(45.0)))
            th.terminal_start_arc_m = max(0.0, l_tot - a0 / math.tan(angle_rad))
            th.end_alt_m = 0.0

    @staticmethod
    def retarget(ctx: Any, th: Threat, new_target_pos: Vec2) -> bool:
        if th.last_update_sec != ctx.time_sec:
            raise RuntimeError("Retarget called before EnemyMovementSystem update")
        if th.kind != ThreatKind.Munition or th.phase != ThreatPhase.Ingress:
            return False
        cur = th.pos
        alt = th.alt_m
        ThreatPath.set_path(th, [cur, new_target_pos], bump_version=True)
        th.path_end = PathEndAction.Arrive
        th.target_pos = new_target_pos
        th.anchor_sec = ctx.time_sec
        th.anchor_arc_m = 0.0
        th.path_arc_m = 0.0
        th.start_alt_m = alt
        ThreatRouting._recompute_profile_on_retarget(th, ctx.level.catalog)
        return True

    @staticmethod
    def begin_egress(ctx: Any, th: Threat) -> bool:
        if th.last_update_sec != ctx.time_sec:
            raise RuntimeError("BeginEgress called before EnemyMovementSystem update")
        if th.phase == ThreatPhase.Arrived:
            return False
        cur = th.pos
        alt = th.alt_m
        ep = ctx.level.entry_points_by_id.get(th.entry_id) if th.entry_id else None
        dest = ep["pos"] if ep is not None else cur
        for r in th.releases:
            if not r.done:
                r.done = True
        ThreatPath.set_path(th, [cur, dest], bump_version=True)
        th.path_end = PathEndAction.Exit
        th.phase = ThreatPhase.Egress
        th.turn_arc_m = 0.0
        th.anchor_sec = ctx.time_sec
        th.anchor_arc_m = 0.0
        th.path_arc_m = 0.0
        th.start_alt_m = alt
        th.end_alt_m = alt
        th.terminal_start_arc_m = th.path_length_m
        th.profile = MotionProfile.Linear
        th.terminal_speed_mps = th.speed_mps
        return True

    @staticmethod
    def hover(ctx: Any, th: Threat) -> bool:
        if th.last_update_sec != ctx.time_sec:
            raise RuntimeError("Hover called before EnemyMovementSystem update")
        if th.phase == ThreatPhase.Arrived:
            return False
        cur = th.pos
        alt = th.alt_m
        for r in th.releases:
            if not r.done:
                r.done = True
        ThreatPath.set_path(th, [cur, cur], bump_version=True)
        th.path_end = PathEndAction.Hold
        th.phase = ThreatPhase.Holding
        th.turn_arc_m = -1.0
        th.anchor_sec = ctx.time_sec
        th.anchor_arc_m = 0.0
        th.path_arc_m = 0.0
        th.start_alt_m = alt
        th.end_alt_m = alt
        th.terminal_start_arc_m = 0.0
        th.profile = MotionProfile.Linear
        th.vel_mps = Vec2(0.0, 0.0)
        th.vert_speed_mps = 0.0
        return True


_TAG_MAP: Dict[str, TargetTag] = {t.name: t for t in TargetTag}
_AI_TAG_MAP: Dict[str, AiTag] = {
    "probe": AiTag.Probe,
    "suppress": AiTag.Suppress,
    "hunt": AiTag.Hunt,
    "bypass": AiTag.Bypass,
    "saturate": AiTag.Saturate,
}


def parse_target_tag(tag_str: Optional[str]) -> Optional[TargetTag]:
    if not tag_str:
        return None
    return _TAG_MAP.get(tag_str)


def parse_ai_tags(raw_tags: Optional[Sequence[str]]) -> Optional[List[AiTag]]:
    if raw_tags is None:
        return None
    return [_AI_TAG_MAP[t] for t in raw_tags if t in _AI_TAG_MAP]


class WaveSpawnRules:
    @staticmethod
    def is_story_only_wave(level: Any, wave_id: str) -> bool:
        for ev in level.story_events.get("events", []):
            for act in ev.get("actions", []):
                if act.get("type") == "spawn_wave" and act.get("wave") == wave_id:
                    return True
        return False

    @staticmethod
    def ray_exit_point(a: Vec2, u: Vec2, w_m: float, h_m: float) -> Vec2:
        if a.x <= 0.0 or a.x >= w_m or a.y <= 0.0 or a.y >= h_m:
            return a
        tx = (w_m - a.x) / u.x if u.x > 0.0 else ((0.0 - a.x) / u.x if u.x < 0.0 else math.inf)
        ty = (h_m - a.y) / u.y if u.y > 0.0 else ((0.0 - a.y) / u.y if u.y < 0.0 else math.inf)
        t = min(tx, ty)
        return a + u * t

    @staticmethod
    def release_s(ingress_pts: Sequence[Vec2], cum: Sequence[float], target_pos: Vec2, r_m: float) -> float:
        if math.isinf(r_m):
            return 0.0
        for i in range(len(ingress_pts) - 1):
            p0 = ingress_pts[i]
            d = ingress_pts[i + 1] - p0
            u = Geo.first_entry_into_circle(p0, d, target_pos, r_m)
            if u is not None and u <= 1.0:
                return cum[i] + u * (cum[i + 1] - cum[i])
        return cum[-1]


class WaveSpawnSystem:
    """System 1: WaveSpawnSystem (01_spawn_movement_terrain.md §3.1)."""

    order = 1
    name = "WaveSpawnSystem"
    stream_name = "spawn"

    def initialize(self, ctx: Any) -> None:
        night_idx, night = self._find_night(ctx)
        for wi, w in enumerate(night.get("waves", [])):
            for gi, g in enumerate(w.get("groups", [])):
                route = g.get("route", {})
                if route.get("template") is not None:
                    raise SimError(
                        "E_NOT_IMPLEMENTED",
                        "航线模板尚未实现（WS02-004）",
                        f"levels/{ctx.level.id}/waves.json",
                        f"$.nights[{night_idx}].waves[{wi}].groups[{gi}].route.template",
                    )

        for wi, w in enumerate(night.get("waves", [])):
            if WaveSpawnRules.is_story_only_wave(ctx.level, w["id"]):
                continue
            self._expand_wave(ctx, night, wi, float(w.get("atSec", 0.0)), injected=False, group_indices=None)
        ctx.state.waves.all_waves_spawned = (
            len(ctx.state.waves.pending) == 0 and len(ctx.state.waves.injections) == 0
        )

    def _find_night(self, ctx: Any) -> Tuple[int, Dict[str, Any]]:
        for idx, n in enumerate(ctx.level.waves.get("nights", [])):
            if n.get("night") == ctx.config.night_index:
                return idx, n
        raise RuntimeError(f"Night {ctx.config.night_index} not found")

    def _expand_wave(
        self,
        ctx: Any,
        night: Dict[str, Any],
        wave_index: int,
        base_sec: float,
        injected: bool,
        group_indices: Optional[Sequence[int]],
    ) -> None:
        w = night["waves"][wave_index]
        groups = w.get("groups", [])
        active_gis: List[int] = []
        for gi in range(len(groups)):
            if group_indices is not None:
                if gi not in group_indices:
                    continue
            else:
                if ctx.enemy_ai_hooks.defer_group(ctx.level, night, wave_index, gi):
                    continue
            active_gis.append(gi)

        if not active_gis:
            return

        ai_tags = parse_ai_tags(w.get("aiTags"))
        sat_times: Optional[List[float]] = None
        if ai_tags and AiTag.Saturate in ai_tags:
            sat_times = ctx.enemy_ai_hooks.saturation_spawn_times(
                ctx.state, ctx.level, night, wave_index, active_gis, base_sec
            )

        flat_idx = 0
        for gi in active_gis:
            g = groups[gi]
            cnt = int(g.get("count", 1))
            spacing = float(g.get("spacingSec", 0.0) or 0.0)
            for k in range(cnt):
                if sat_times is not None and flat_idx < len(sat_times):
                    t_sec = sat_times[flat_idx]
                else:
                    t_sec = base_sec + k * spacing
                flat_idx += 1
                sp_tick = max(1, SimTime.sec_to_ticks_ceil(t_sec, ctx.step_sec))
                seq = ctx.state.waves.next_spawn_seq
                ctx.state.waves.next_spawn_seq += 1
                ctx.state.waves.pending.append(
                    PendingSpawn(
                        seq=seq,
                        spawn_tick=sp_tick,
                        spawn_at_sec=t_sec,
                        wave_id=w["id"],
                        wave_index=wave_index,
                        group_index=gi,
                        index_in_group=k,
                        enemy_id=g["enemy"],
                        entry_id=g["entry"],
                        route=g.get("route", {}),
                        target_spec=g.get("target", {}),
                        ai_tags=ai_tags,
                        injected=injected and group_indices is None,
                    )
                )
        ctx.state.waves.pending.sort(key=lambda p: (p.spawn_tick, p.spawn_at_sec, p.seq))

    def execute(self, ctx: Any) -> None:
        _, night = self._find_night(ctx)
        if ctx.state.waves.injections:
            for inj in list(ctx.state.waves.injections):
                wi = -1
                for idx, w in enumerate(night.get("waves", [])):
                    if w["id"] == inj.wave_id:
                        wi = idx
                        break
                if wi < 0:
                    raise RuntimeError(f"Injected unknown wave '{inj.wave_id}'")
                base_sec = max(inj.start_at_sec, ctx.time_sec)
                if inj.group_indices is None:
                    # Re-injecting a full wave allows WaveStarted to fire for this injection
                    key = f"{inj.wave_id}#inj#{ctx.state.waves.next_spawn_seq}"
                self._expand_wave(ctx, night, wi, base_sec, injected=True, group_indices=inj.group_indices)
            ctx.state.waves.injections.clear()

        pending = ctx.state.waves.pending
        while pending and pending[0].spawn_tick <= ctx.tick:
            item = pending.pop(0)
            self._process_spawn(ctx, night, item)

        ctx.state.waves.all_waves_spawned = (
            len(ctx.state.waves.pending) == 0 and len(ctx.state.waves.injections) == 0
        )

    def _process_spawn(self, ctx: Any, night: Dict[str, Any], e: PendingSpawn) -> None:
        w = night["waves"][e.wave_index]
        g = w["groups"][e.group_index]
        entry = ctx.level.entry_points_by_id[e.entry_id]
        entry_pos: Vec2 = entry["pos"]

        w_key = f"{w['id']}#{'inj' if e.injected else 'sched'}#{e.spawn_at_sec if e.injected and e.index_in_group == 0 and e.group_index == 0 else '0'}"
        base_key = w["id"] if not e.injected else f"{w['id']}@{ctx.tick}"
        if base_key not in ctx.state.waves.started_wave_keys:
            ctx.state.waves.started_wave_keys.append(base_key)
            ctx.events.emit(
                SimEventType.WaveStarted,
                at_sec=e.spawn_at_sec,
                fields=(w["id"], ("list_enum", e.ai_tags), e.injected),
                wave_id=w["id"],
                ai_tags=e.ai_tags,
                injected=e.injected,
            )

        cat = ctx.level.catalog
        if e.enemy_id in cat.munitions:
            m = cat.munitions[e.enemy_id]
            req = TargetRequest(m["id"], ThreatKind.Munition, w["id"], e.wave_index, e.group_index, e.index_in_group, entry_pos)
            target = self._resolve_target(ctx, e.target_spec, req)
            self._create_wave_munition(ctx, m, entry, g, w, target, e.spawn_at_sec, parent_id=0)
        elif e.enemy_id in cat.platforms:
            p = cat.platforms[e.enemy_id]
            picks = self._choose_loadout(ctx, p)
            if p.get("entersMap", True):
                req = TargetRequest(p["id"], ThreatKind.Platform, w["id"], e.wave_index, e.group_index, e.index_in_group, entry_pos)
                target = self._resolve_target(ctx, e.target_spec, req)
                self._create_platform(ctx, p, entry, g, w, target, picks, e.spawn_at_sec)
            else:
                for _j, mid, cnt in picks:
                    for c_idx in range(cnt):
                        req = TargetRequest(mid, ThreatKind.Munition, w["id"], e.wave_index, e.group_index, c_idx, entry_pos)
                        target = self._resolve_target(ctx, e.target_spec, req)
                        self._create_wave_munition(ctx, cat.munitions[mid], entry, g, w, target, e.spawn_at_sec, parent_id=0)

    def _choose_loadout(self, ctx: Any, p: Dict[str, Any]) -> List[Tuple[int, str, int]]:
        picks: List[Tuple[int, str, int]] = []
        for j, slot in enumerate(p.get("loadout") or []):
            opts = slot.get("options", [])
            idx = ctx.rng.next_int(0, len(opts))
            cnt = int(slot.get("count") if slot.get("count") is not None else 1)
            picks.append((j, opts[idx], cnt))
        return picks

    def _weighted_structure(self, ctx: Any) -> TargetChoice:
        alive_intact = [s for s in ctx.state.structures.alive_list() if s.hp > 0]
        cands = alive_intact if alive_intact else ctx.state.structures.alive_list()
        total = sum(s.weight for s in cands)
        r = ctx.rng.next_double() * total
        if not cands or total <= 0.0:
            w_m = float(ctx.level.meta.get("map", {}).get("widthM", 20000.0))
            h_m = float(ctx.level.meta.get("map", {}).get("heightM", 20000.0))
            return TargetChoice(ThreatTargetKind.AimPoint, Vec2(w_m * 0.5, h_m * 0.5), 0, 0)
        cum = 0.0
        for s in cands:
            cum += s.weight
            if r < cum:
                return TargetChoice(ThreatTargetKind.Structure, s.pos, s.id, 0)
        last = cands[-1]
        return TargetChoice(ThreatTargetKind.Structure, last.pos, last.id, 0)

    def _resolve_target(self, ctx: Any, spec: Dict[str, Any], req: TargetRequest) -> TargetChoice:
        if spec.get("structure") is not None:
            sid = ctx.state.structure_id_by_def_id[spec["structure"]]
            st = ctx.state.structures.try_get_including_removed(sid)
            return TargetChoice(ThreatTargetKind.Structure, st.pos if st else Vec2(0.0, 0.0), sid, 0)
        mode = spec.get("mode", "weighted_random")
        if mode == "weighted_random":
            ovr = ctx.enemy_ai_hooks.select_weighted_random_override(ctx.state, ctx.level, req, ctx.rng)
            if ovr is not None:
                return ovr
            return self._weighted_structure(ctx)
        if mode == "known_targets":
            c = ctx.enemy_ai_hooks.select_known_target(ctx.state, ctx.level, req, ctx.rng)
            return c if c is not None else self._weighted_structure(ctx)
        if mode == "air_defense":
            c = ctx.enemy_ai_hooks.select_air_defense_target(ctx.state, ctx.level, req, ctx.rng)
            return c if c is not None else self._weighted_structure(ctx)
        if mode == "decoy_flight":
            w = self._weighted_structure(ctx)
            return TargetChoice(ThreatTargetKind.AimPoint, w.pos, 0, 0)
        return self._weighted_structure(ctx)

    def _build_munition_path(
        self, ctx: Any, m: Dict[str, Any], entry_pos: Vec2, route: Dict[str, Any], target: TargetChoice, w: Optional[Dict[str, Any]]
    ) -> Tuple[List[Vec2], PathEndAction]:
        wps: List[Vec2] = list(route.get("waypoints") or [])
        band = m.get("altitudeBand", "low")
        if target.kind == ThreatTargetKind.AimPoint:
            pts = [entry_pos] + wps + [target.pos]
            prev = entry_pos
            for p in reversed(pts[:-1]):
                if p != target.pos:
                    prev = p
                    break
            d = (target.pos - prev).normalized()
            if d.x == 0.0 and d.y == 0.0:
                d = Vec2(0.0, 1.0)
            w_m = float(ctx.level.meta.get("map", {}).get("widthM", 20000.0))
            h_m = float(ctx.level.meta.get("map", {}).get("heightM", 20000.0))
            exit_pt = WaveSpawnRules.ray_exit_point(target.pos, d, w_m, h_m)
            if exit_pt != target.pos:
                pts.append(exit_pt)
            return pts, PathEndAction.Exit

        if band in ("ballistic", "quasi_ballistic", "terminal_maneuver", "glide"):
            path = [entry_pos, target.pos]
        elif wps:
            path = [entry_pos] + wps + [target.pos]
        else:
            path = [entry_pos, target.pos]

        end_action = PathEndAction.Arrive
        tag = parse_target_tag(m.get("tag"))
        enemy_ai_rules = ctx.level.catalog.rules.get("enemy_ai", {})
        bypass_tag_strs = enemy_ai_rules.get("bypass", {}).get("tags", ["CM"])
        bypass_tags = {parse_target_tag(ts) for ts in bypass_tag_strs}
        a50_active = EnemyAiQueries.avoidance_active(ctx.state, ctx.level.catalog)
        w_ai_tags = parse_ai_tags(w.get("aiTags")) if w else None
        bypass_tagged = bool(w_ai_tags and AiTag.Bypass in w_ai_tags)

        if (
            end_action == PathEndAction.Arrive
            and band not in ("ballistic", "quasi_ballistic", "terminal_maneuver", "glide", "carrier")
            and tag is not None
            and tag in bypass_tags
            and (bypass_tagged or a50_active)
        ):
            av_req = AvoidanceRequest(m["id"], tag, w["id"] if w else "", a50_active, bypass_tagged)
            path = list(ctx.enemy_ai_hooks.adjust_avoidance(ctx.state, ctx.level, av_req, path))

        return path, end_action

    def _create_wave_munition(
        self,
        ctx: Any,
        m: Dict[str, Any],
        entry: Dict[str, Any],
        g: Dict[str, Any],
        w: Dict[str, Any],
        target: TargetChoice,
        at_sec: float,
        parent_id: int,
    ) -> Threat:
        entry_pos: Vec2 = entry["pos"]
        path, end_action = self._build_munition_path(ctx, m, entry_pos, g.get("route", {}), target, w)
        th = Threat(
            def_id=m["id"],
            pos=entry_pos,
            alt_m=0.0,
            kind=ThreatKind.Munition,
            tag=parse_target_tag(m.get("tag")),
            phase=ThreatPhase.Ingress,
            wave_id=w["id"],
            entry_id=entry["id"],
            parent_threat_id=parent_id,
            spawn_at_sec=at_sec,
            target_kind=target.kind,
            target_pos=target.pos,
            target_structure_id=target.structure_id,
            target_unit_id=target.unit_id,
            profile_ready=False,
            path_end=end_action,
            anchor_sec=at_sec,
            anchor_arc_m=0.0,
            path_arc_m=0.0,
            last_update_sec=at_sec,
            arrived_at_sec=-1.0,
            turn_arc_m=-1.0,
        )
        ThreatPath.set_path(th, path, bump_version=False)
        ctx.state.threats.add(th)
        ctx.events.emit(
            SimEventType.ThreatSpawned,
            at_sec=at_sec,
            fields=(th.id, m["id"], ThreatKind.Munition, entry["id"], w["id"]),
            threat_id=th.id,
            def_id=m["id"],
            kind=ThreatKind.Munition,
            entry_id=entry["id"],
            wave_id=w["id"],
        )
        ctx.state.waves.spawned_threat_count += 1
        return th

    def _create_platform(
        self,
        ctx: Any,
        p: Dict[str, Any],
        entry: Dict[str, Any],
        g: Dict[str, Any],
        w: Dict[str, Any],
        target: TargetChoice,
        picks: List[Tuple[int, str, int]],
        at_sec: float,
    ) -> Threat:
        entry_pos: Vec2 = entry["pos"]
        wps: List[Vec2] = list(g.get("route", {}).get("waypoints") or [])
        ingress = [entry_pos] + wps + [target.pos]
        cum_i = ThreatPath.compute_cum_m(ingress)
        releases: List[PendingRelease] = []
        if not picks:
            path = list(ingress)
            end_action = PathEndAction.Hold
            turn_arc_m = -1.0
        else:
            behavior = p.get("behavior", "")
            standoff_active = bool(p.get("standoffActive", True))
            p_rel_m = p.get("releaseRangeM")
            for j, mid, cnt in picks:
                m = ctx.level.catalog.munitions[mid]
                m_rel_m = m.get("releaseRangeM")
                if behavior == "standoff_release_and_return" and not standoff_active:
                    r_m = 0.0
                else:
                    r_m = float(m_rel_m) if m_rel_m is not None else (float(p_rel_m) if p_rel_m is not None else math.inf)
                sj = WaveSpawnRules.release_s(ingress, cum_i, target.pos, r_m)
                releases.append(PendingRelease(loadout_index=j, munition_id=mid, count=cnt, at_arc_m=sj, done=False))
            releases.sort(key=lambda r: (r.at_arc_m, r.loadout_index))
            s_turn = max(r.at_arc_m for r in releases)
            out = ThreatPath.truncate_at(ingress, cum_i, s_turn)
            rev = list(reversed(out[:-1]))
            path = out + rev
            end_action = PathEndAction.Exit
            turn_arc_m = s_turn

        th = Threat(
            def_id=p["id"],
            pos=entry_pos,
            alt_m=0.0,
            kind=ThreatKind.Platform,
            tag=parse_target_tag(p.get("tag")),
            phase=ThreatPhase.Ingress,
            wave_id=w["id"],
            entry_id=entry["id"],
            parent_threat_id=0,
            spawn_at_sec=at_sec,
            target_kind=target.kind,
            target_pos=target.pos,
            target_structure_id=target.structure_id,
            target_unit_id=target.unit_id,
            profile_ready=False,
            path_end=end_action,
            anchor_sec=at_sec,
            anchor_arc_m=0.0,
            path_arc_m=0.0,
            last_update_sec=at_sec,
            arrived_at_sec=-1.0,
            turn_arc_m=turn_arc_m,
            releases=releases,
            ingress_path=ingress,
        )
        ThreatPath.set_path(th, path, bump_version=False)
        ctx.state.threats.add(th)
        ctx.events.emit(
            SimEventType.ThreatSpawned,
            at_sec=at_sec,
            fields=(th.id, p["id"], ThreatKind.Platform, entry["id"], w["id"]),
            threat_id=th.id,
            def_id=p["id"],
            kind=ThreatKind.Platform,
            entry_id=entry["id"],
            wave_id=w["id"],
        )
        ctx.state.waves.spawned_threat_count += 1
        return th


class EnemyMovementSystem:
    """System 2: EnemyMovementSystem (01_spawn_movement_terrain.md §3.2)."""

    order = 2
    name = "EnemyMovementSystem"
    stream_name = "movement"

    def initialize(self, ctx: Any) -> None:
        pass

    def execute(self, ctx: Any) -> None:
        n = ctx.state.threats.count
        for i in range(n):
            th = ctx.state.threats[i]
            if not th.alive:
                continue
            if th.phase == ThreatPhase.Arrived:
                continue
            if th.phase == ThreatPhase.Holding:
                th.vel_mps = Vec2(0.0, 0.0)
                th.vert_speed_mps = 0.0
                th.last_update_sec = ctx.time_sec
                continue
            if not th.profile_ready:
                self._init_profile(ctx, th, parent_alt_m=None, parent_speed_mps=None)
            self._apply_homing(ctx, th)
            self._advance(ctx, th, ctx.time_sec)

    def _roll_minmax(self, rng: SimRandom, mm: Dict[str, Any]) -> float:
        return rng.range(float(mm["min"]), float(mm["max"]))

    def _init_profile(
        self,
        ctx: Any,
        th: Threat,
        parent_alt_m: Optional[float],
        parent_speed_mps: Optional[float],
    ) -> None:
        cat = ctx.level.catalog
        m_rules = cat.rules["movement"]
        bands = m_rules["altitudeBandsM"]
        l_tot = th.path_length_m

        if th.kind == ThreatKind.Platform:
            p_def = cat.platforms[th.def_id or ""]
            band = p_def["altitudeBand"]
            a0 = self._roll_minmax(ctx.rng, bands[band])
            v1 = float(p_def["cruiseSpeedMps"])
            th.profile = MotionProfile.Linear
            th.start_alt_m = a0
            th.end_alt_m = a0
            th.terminal_start_arc_m = l_tot
            th.speed_mps = v1
            th.terminal_speed_mps = v1
            th.profile_ready = True
            return

        m_def = cat.munitions[th.def_id or ""]
        band = m_def["altitudeBand"]
        dive_mult = float(m_rules.get("diveSpeedMult", 2.0))

        if band == "carrier":
            v1 = float(parent_speed_mps if parent_speed_mps is not None else 0.0)
            a0 = float(parent_alt_m if parent_alt_m is not None else 0.0)
            th.profile = MotionProfile.Linear
            th.start_alt_m = a0
            th.end_alt_m = 0.0
            th.terminal_start_arc_m = 0.0
            th.speed_mps = v1
            th.terminal_speed_mps = v1
            th.profile_ready = True
            return

        v1 = float(m_def["speedMps"])
        v2 = v1 * dive_mult if m_def.get("diveFaster") else v1
        th.speed_mps = v1
        th.terminal_speed_mps = v2

        if band == "ballistic":
            th.profile = MotionProfile.Parabolic
            angle_rad = float(m_rules["ballisticTerminalAngleRad"])
            th.start_alt_m = l_tot * math.tan(angle_rad) / 2.0
            th.end_alt_m = 0.0
            th.terminal_start_arc_m = 0.0
        elif band in ("quasi_ballistic", "terminal_maneuver"):
            th.profile = MotionProfile.Parabolic
            angle_rad = float(m_rules["quasiBallisticTerminalAngleRad"])
            th.start_alt_m = l_tot * math.tan(angle_rad) / 2.0
            th.end_alt_m = 0.0
            th.terminal_start_arc_m = 0.0
        elif band == "glide":
            th.profile = MotionProfile.Linear
            a0 = parent_alt_m if parent_alt_m is not None else self._roll_minmax(ctx.rng, m_def.get("altitudeM") or bands["glide"])
            th.start_alt_m = float(a0)
            th.end_alt_m = 0.0
            th.terminal_start_arc_m = 0.0
        elif band == "high_dive":
            th.profile = MotionProfile.Linear
            a0 = self._roll_minmax(ctx.rng, m_def.get("altitudeM") or bands["high_dive"])
            angle_rad = float(m_rules["highDiveAngleRad"])
            th.start_alt_m = a0
            if th.path_end == PathEndAction.Arrive:
                th.terminal_start_arc_m = max(0.0, l_tot - a0 / math.tan(angle_rad))
                th.end_alt_m = 0.0
            else:
                th.terminal_start_arc_m = l_tot
                th.end_alt_m = a0
        else:
            th.profile = MotionProfile.Linear
            a0 = self._roll_minmax(ctx.rng, m_def.get("altitudeM") or bands[band])
            angle_rad = float(m_rules["cruiseDescentAngleRad"])
            th.start_alt_m = a0
            if th.path_end == PathEndAction.Arrive:
                th.terminal_start_arc_m = max(0.0, l_tot - a0 / math.tan(angle_rad))
                th.end_alt_m = 0.0
            else:
                th.terminal_start_arc_m = l_tot
                th.end_alt_m = a0
        th.profile_ready = True

    def _apply_homing(self, ctx: Any, th: Threat) -> None:
        if th.homing_unit_id == 0 or th.kind != ThreatKind.Munition or th.phase != ThreatPhase.Ingress or th.path_end != PathEndAction.Arrive:
            return
        u = (
            ctx.state.fire_units.try_get(th.homing_unit_id)
            or ctx.state.sensors.try_get(th.homing_unit_id)
            or ctx.state.ew_units.try_get(th.homing_unit_id)
            or ctx.state.deception_units.try_get(th.homing_unit_id)
        )
        if u is None or u.pos is None:
            return
        if th.path and u.pos == th.path[-1]:
            return
        t0 = th.last_update_sec
        cur = ThreatKinematics.pos_at_s(th, ThreatKinematics.s_at(th, t0))
        alt = ThreatKinematics.alt_at_s(th, ThreatKinematics.s_at(th, t0))
        ThreatPath.set_path(th, [cur, u.pos], bump_version=True)
        th.path_end = PathEndAction.Arrive
        th.target_pos = u.pos
        th.target_unit_id = u.id
        th.target_kind = ThreatTargetKind.PlayerUnit
        th.anchor_sec = t0
        th.anchor_arc_m = 0.0
        th.path_arc_m = 0.0
        th.start_alt_m = alt
        ThreatRouting._recompute_profile_on_retarget(th, ctx.level.catalog)

    def _advance(self, ctx: Any, th: Threat, t_sec: float) -> None:
        s_new = ThreatKinematics.s_at(th, t_sec)
        l_tot = th.path_length_m

        for r in th.releases:
            if r.done or r.at_arc_m > s_new:
                continue
            tr = ThreatKinematics.time_at_s(th, r.at_arc_m)
            r.done = True
            for _c in range(r.count):
                self._release_child(ctx, th, r, tr, t_sec)

        th.path_arc_m = s_new
        th.pos = ThreatKinematics.pos_at_s(th, s_new)
        th.alt_m = ThreatKinematics.alt_at_s(th, s_new)
        th.vel_mps = (
            Vec2(0.0, 0.0)
            if s_new >= l_tot
            else ThreatKinematics.dir_at_s(th, s_new) * ThreatKinematics.speed_at_s(th, s_new)
        )
        th.vert_speed_mps = ThreatKinematics.vert_at_s(th, s_new)
        if th.turn_arc_m >= 0.0 and th.phase == ThreatPhase.Ingress and s_new >= th.turn_arc_m:
            th.phase = ThreatPhase.Egress
        th.last_update_sec = t_sec

        if s_new >= l_tot:
            t_end = ThreatKinematics.time_at_s(th, l_tot)
            if th.path_end == PathEndAction.Arrive:
                th.phase = ThreatPhase.Arrived
                th.arrived_at_sec = t_end
                th.alt_m = th.end_alt_m
                th.vel_mps = Vec2(0.0, 0.0)
                th.vert_speed_mps = 0.0
                ctx.events.emit(
                    SimEventType.ThreatArrived,
                    at_sec=t_end,
                    fields=(th.id, th.def_id, th.pos, th.target_kind, th.target_structure_id, th.target_unit_id),
                    threat_id=th.id,
                    def_id=th.def_id,
                    pos=th.pos,
                    target_kind=th.target_kind,
                    target_structure_id=th.target_structure_id,
                    target_unit_id=th.target_unit_id,
                )
            elif th.path_end == PathEndAction.Exit:
                reason = ThreatExitReason.EgressComplete if th.phase == ThreatPhase.Egress else ThreatExitReason.DecoyPathEnd
                ctx.events.emit(
                    SimEventType.ThreatExited,
                    at_sec=t_end,
                    fields=(th.id, th.def_id, reason),
                    threat_id=th.id,
                    def_id=th.def_id,
                    reason=reason,
                )
                ctx.state.threats.remove(th.id)
            elif th.path_end == PathEndAction.Hold:
                th.phase = ThreatPhase.Holding
                th.vel_mps = Vec2(0.0, 0.0)
                th.vert_speed_mps = 0.0

    def _release_child(self, ctx: Any, p: Threat, r: PendingRelease, tr: float, t_sec: float) -> None:
        m = ctx.level.catalog.munitions[r.munition_id]
        ps = r.at_arc_m
        p_pos = ThreatKinematics.pos_at_s(p, ps)
        p_alt = ThreatKinematics.alt_at_s(p, ps)
        ingress = p.ingress_path
        cum_i = ThreatPath.compute_cum_m(ingress)
        rest: List[Vec2] = [p_pos]
        for k in range(len(ingress)):
            if cum_i[k] > ps and ingress[k] != rest[-1]:
                rest.append(ingress[k])
        band = m.get("altitudeBand", "low")
        if band in ("ballistic", "quasi_ballistic", "terminal_maneuver", "glide", "carrier"):
            path = [p_pos, p.target_pos]
        else:
            path = rest

        end_action = PathEndAction.Arrive
        tag = parse_target_tag(m.get("tag"))
        enemy_ai_rules = ctx.level.catalog.rules.get("enemy_ai", {})
        bypass_tag_strs = enemy_ai_rules.get("bypass", {}).get("tags", ["CM"])
        bypass_tags = {parse_target_tag(ts) for ts in bypass_tag_strs}
        a50_active = EnemyAiQueries.avoidance_active(ctx.state, ctx.level.catalog)
        if (
            end_action == PathEndAction.Arrive
            and band not in ("ballistic", "quasi_ballistic", "terminal_maneuver", "glide", "carrier")
            and tag is not None
            and tag in bypass_tags
            and a50_active
        ):
            av_req = AvoidanceRequest(m["id"], tag, p.wave_id, a50_active, False)
            path = list(ctx.enemy_ai_hooks.adjust_avoidance(ctx.state, ctx.level, av_req, path))

        c = Threat(
            def_id=m["id"],
            pos=p_pos,
            alt_m=p_alt,
            kind=ThreatKind.Munition,
            tag=tag,
            phase=ThreatPhase.Ingress,
            wave_id=p.wave_id,
            entry_id=p.entry_id,
            parent_threat_id=p.id,
            spawn_at_sec=tr,
            target_kind=p.target_kind,
            target_pos=p.target_pos,
            target_structure_id=p.target_structure_id,
            target_unit_id=p.target_unit_id,
            profile_ready=False,
            path_end=end_action,
            anchor_sec=tr,
            anchor_arc_m=0.0,
            path_arc_m=0.0,
            last_update_sec=tr,
            arrived_at_sec=-1.0,
            turn_arc_m=-1.0,
        )
        ThreatPath.set_path(c, path, bump_version=False)
        ctx.state.threats.add(c)
        self._init_profile(ctx, c, parent_alt_m=p_alt, parent_speed_mps=p.speed_mps)
        ctx.events.emit(
            SimEventType.MunitionReleased,
            at_sec=tr,
            fields=(p.id, c.id, m["id"]),
            parent_threat_id=p.id,
            threat_id=c.id,
            def_id=m["id"],
        )
        ctx.state.waves.spawned_threat_count += 1
        self._advance(ctx, c, t_sec)
