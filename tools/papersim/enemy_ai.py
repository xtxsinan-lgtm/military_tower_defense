"""Enemy AI hooks, enemy intel system, Stage 0 command dispatch, deployment state machine, and story/choice stages (04_enemy_ai_commands.md)."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .core import Geo, SimError, SimRandom, SimTime, Vec2
from .entities import (
    AiTag,
    ChoiceRequest,
    CommandRejectReason,
    DeceptionUnit,
    EmitterControl,
    EntityKind,
    EwUnit,
    FireUnit,
    HeldWaveGroup,
    KnownTargetEntry,
    PlacedUnit,
    PlayerUnitCategory,
    PlayerUnitEntity,
    RelocationOrder,
    ScheduledSpawn,
    SensorUnit,
    SimCommand,
    SimCommandType,
    SimEventType,
    SimState,
    SupportAsset,
    TargetTag,
    Threat,
    ThreatKind,
    ThreatPhase,
    ThreatTargetKind,
    TrackQuality,
    UnitDeployState,
    WaveInjection,
)
from .movement import (
    AvoidanceRequest,
    IEnemyAiHooks,
    TargetChoice,
    TargetRequest,
    ThreatRouting,
    WaveSpawnRules,
    parse_ai_tags,
    parse_target_tag,
)
from .sensing import EmissionChoiceEffects, EmissionPolicyRules, EmitterQueries, EnvironmentResolver

EPS = 1e-9
NEI_8 = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1)]


class AvoidanceAStar:
    """Grid A* pathfinder for Cruise Missile avoidance (04_enemy_ai_commands.md §3.1.5, calc_04.py)."""

    @staticmethod
    def build_grid(min_x: float, min_y: float, w: float, h: float, cell_m: float, max_cells: int) -> Tuple[float, int, int]:
        c = cell_m
        while math.ceil(w / c - EPS) * math.ceil(h / c - EPS) > max_cells:
            c *= 1.25
        nx = int(math.ceil(w / c - EPS))
        ny = int(math.ceil(h / c - EPS))
        return c, nx, ny

    @staticmethod
    def center(min_x: float, min_y: float, c: float, nx: int, idx: int) -> Tuple[float, float]:
        ix = idx % nx
        iy = idx // nx
        return (min_x + (ix + 0.5) * c, min_y + (iy + 0.5) * c)

    @staticmethod
    def cell_of(min_x: float, min_y: float, c: float, nx: int, ny: int, p: Vec2) -> int:
        ix = int(math.floor((p.x - min_x) / c))
        iy = int(math.floor((p.y - min_y) / c))
        ix = max(0, min(nx - 1, ix))
        iy = max(0, min(ny - 1, iy))
        return iy * nx + ix

    @staticmethod
    def compute_turning_points(
        min_x: float,
        min_y: float,
        w: float,
        h: float,
        cell_m: float,
        max_cells: int,
        sites: Sequence[Tuple[Vec2, float]],
        threat_weight: float,
        r_mult: float,
        valley_fn: Any,
        valley_weight: float,
        los_fn: Any,
        start_pt: Vec2,
        goal_pt: Vec2,
    ) -> List[Vec2]:
        c, nx, ny = AvoidanceAStar.build_grid(min_x, min_y, w, h, cell_m, max_cells)
        start = AvoidanceAStar.cell_of(min_x, min_y, c, nx, ny, start_pt)
        goal = AvoidanceAStar.cell_of(min_x, min_y, c, nx, ny, goal_pt)
        if start == goal:
            return []

        penalties: List[float] = []
        for i in range(nx * ny):
            cx, cy = AvoidanceAStar.center(min_x, min_y, c, nx, i)
            cc = Vec2(cx, cy)
            p_val = valley_weight * float(valley_fn(cc))
            for sp, rad in sites:
                dx = cx - sp.x
                dy = cy - sp.y
                rr = rad * r_mult
                if dx * dx + dy * dy < rr * rr and los_fn(sp, cc):
                    p_val += threat_weight
            penalties.append(p_val)

        inf = float("inf")
        g_cost = [inf] * (nx * ny)
        parent = [-1] * (nx * ny)
        closed = [False] * (nx * ny)
        gx, gy = AvoidanceAStar.center(min_x, min_y, c, nx, goal)

        def h_fn(idx: int) -> float:
            cx, cy = AvoidanceAStar.center(min_x, min_y, c, nx, idx)
            return math.sqrt((cx - gx) ** 2 + (cy - gy) ** 2)

        g_cost[start] = 0.0
        open_set = {(h_fn(start), h_fn(start), start)}
        while open_set:
            cur = min(open_set)
            open_set.remove(cur)
            _, _, u = cur
            if closed[u]:
                continue
            closed[u] = True
            if u == goal:
                break
            ux = u % nx
            uy = u // nx
            for dx, dy in NEI_8:
                vx = ux + dx
                vy = uy + dy
                if vx < 0 or vy < 0 or vx >= nx or vy >= ny:
                    continue
                v = vy * nx + vx
                if closed[v]:
                    continue
                step_len = c if (dx == 0 or dy == 0) else c * math.sqrt(2.0)
                ng = g_cost[u] + step_len * (1.0 + penalties[v])
                if ng < g_cost[v]:
                    if g_cost[v] < inf:
                        open_set.discard((g_cost[v] + h_fn(v), h_fn(v), v))
                    g_cost[v] = ng
                    parent[v] = u
                    open_set.add((ng + h_fn(v), h_fn(v), v))

        if not closed[goal]:
            return []
        cell_path = [goal]
        while cell_path[-1] != start:
            cell_path.append(parent[cell_path[-1]])
        cell_path.reverse()

        wps: List[Vec2] = []
        for j in range(1, len(cell_path) - 1):
            a = cell_path[j - 1]
            b = cell_path[j]
            n = cell_path[j + 1]
            d1 = (b % nx - a % nx, b // nx - a // nx)
            d2 = (n % nx - b % nx, n // nx - b // nx)
            if d1 != d2:
                cx, cy = AvoidanceAStar.center(min_x, min_y, c, nx, b)
                wps.append(Vec2(cx, cy))
        return wps


class EnemyAiHooks(IEnemyAiHooks):
    """Concrete implementation of IEnemyAiHooks (04_enemy_ai_commands.md §3.1)."""

    def __init__(self, terrain: Any = None) -> None:
        self.terrain = terrain
        self._astar_cache: Dict[Tuple[Any, ...], List[Vec2]] = {}

    def select_known_target(self, state: SimState, level: Any, req: TargetRequest, rng: SimRandom) -> Optional[TargetChoice]:
        kts = state.enemy_intel.known_targets
        if not kts:
            return None
        ai_rules = level.catalog.rules.get("enemy_ai", {}).get("knownTargets", {})
        r_weights = ai_rules.get("reasonWeights", {"carried_in": 1.0, "precision_exposure": 3.0, "probe_fire": 1.5, "emitting": 1.0})
        k_weights = ai_rules.get("kindWeights", {"air_defense": 1.0, "radar": 1.0, "ew": 0.6, "sensor": 0.3})
        spread = float(ai_rules.get("spreadFactor", 0.5))

        reason_map = {0: "precision_exposure", 1: "probe_fire", 2: "emitting", 3: "carried_in"}
        kind_map = {0: "radar", 1: "air_defense", 2: "ew", 3: "sensor"}

        weights: List[float] = []
        for kt in kts:
            rw = float(r_weights.get(reason_map.get(kt.reason, "emitting"), 1.0))
            kw = float(k_weights.get(kind_map.get(kt.kind, "air_defense"), 1.0))
            assigned = self._count_assigned_to_target(state, kt.unit_id, kt.pos)
            w = (rw * kw) / (1.0 + spread * assigned)
            weights.append(w)

        tot = sum(weights)
        if tot <= 0.0:
            return None
        r = rng.next_double() * tot
        cum = 0.0
        chosen = kts[-1]
        for kt, w in zip(kts, weights):
            cum += w
            if r < cum:
                chosen = kt
                break
        return TargetChoice(ThreatTargetKind.PlayerUnit, chosen.pos, 0, chosen.unit_id)

    def select_air_defense_target(self, state: SimState, level: Any, req: TargetRequest, rng: SimRandom) -> Optional[TargetChoice]:
        mdef = level.catalog.munitions.get(req.enemy_id, {})
        is_arm = bool(mdef.get("antiRadiation"))
        active_emitters = EmitterQueries.list_active(state)
        if is_arm and active_emitters:
            weights: List[float] = []
            for em in active_emitters:
                w = 2.0 if em.exposure >= 40.0 else 1.0
                assigned = self._count_arm_assigned_to_unit(state, em.unit_id)
                w = w / (1.0 + assigned)
                weights.append(w)
            tot = sum(weights)
            r = rng.next_double() * tot
            cum = 0.0
            chosen = active_emitters[-1]
            for em, w in zip(active_emitters, weights):
                cum += w
                if r < cum:
                    chosen = em
                    break
            return TargetChoice(ThreatTargetKind.PlayerUnit, chosen.pos, 0, chosen.unit_id)

        return self.select_known_target(state, level, req, rng)

    def select_weighted_random_override(self, state: SimState, level: Any, req: TargetRequest, rng: SimRandom) -> Optional[TargetChoice]:
        # Check if any known target has priority (exposure == 100 retarget quota)
        prio_kts = [kt for kt in state.enemy_intel.known_targets if kt.priority]
        if not prio_kts:
            return None
        kt = prio_kts[0]
        kt.priority = False
        return TargetChoice(ThreatTargetKind.PlayerUnit, kt.pos, 0, kt.unit_id)

    def adjust_avoidance(self, state: SimState, level: Any, req: AvoidanceRequest, path: Sequence[Vec2]) -> List[Vec2]:
        if len(path) < 2:
            return list(path)
        cat = level.catalog
        b_rules = cat.rules.get("enemy_ai", {}).get("bypass", {})
        cell_m = float(b_rules.get("cellM", 1000.0))
        max_cells = int(b_rules.get("maxCells", 4096))
        threat_w = float(b_rules.get("threatWeight", 4.0))
        valley_w = float(b_rules.get("valleyWeight", 0.5))
        r_mult = float(b_rules.get("radiusMult", 1.0))
        if req.a50_active:
            a50_cfg = b_rules.get("a50", {})
            r_mult = float(a50_cfg.get("radiusMult", 1.2))
            threat_w *= float(a50_cfg.get("threatWeightMult", 2.0))

        sites: List[Tuple[Vec2, float]] = []
        dest_pt = path[-1] if path else None
        for kt in state.enemy_intel.known_targets:
            if kt.kind in (0, 1):
                udef = cat.air_defense_units.get(kt.unit_def_id, {})
                rmax = max(
                    (float(cat.weapons[wid].get("rangeM", 10000.0)) for wid in udef.get("weaponIds", []) if wid in cat.weapons),
                    default=float(b_rules.get("fakeLauncherAssumedRangeM", 10000.0)),
                )
                if dest_pt is not None and kt.pos.distance_to(dest_pt) <= rmax:
                    rmax = min(rmax, 4500.0)
                sites.append((kt.pos, rmax))

        if req.a50_active:
            min_exp = float(b_rules.get("a50", {}).get("siteMinExposure", 40.0))
            for fu in state.fire_units.alive_list():
                if fu.pos is not None and fu.exposure >= min_exp:
                    udef = cat.air_defense_units.get(fu.def_id or "", {})
                    rmax = max((float(cat.weapons[wid].get("rangeM", 10000.0)) for wid in udef.get("weaponIds", []) if wid in cat.weapons), default=10000.0)
                    if dest_pt is not None and fu.pos.distance_to(dest_pt) <= rmax:
                        rmax = min(rmax, 4500.0)
                    if not any(sp.distance_to(fu.pos) <= 100.0 for sp, _ in sites):
                        sites.append((fu.pos, rmax))

        if not sites:
            return list(path)

        w_m = float(level.meta.get("map", {}).get("widthM", 20000.0))
        h_m = float(level.meta.get("map", {}).get("heightM", 20000.0))
        hm = level.heightmap
        span_elev = max(1.0, hm.max_elevation_m - hm.min_elevation_m)

        def valley_fn(pt: Vec2) -> float:
            if self.terrain is None:
                return 0.0
            return max(0.0, min(1.0, (self.terrain.get_elevation(pt) - hm.min_elevation_m) / span_elev))

        use_los = bool(b_rules.get("useLineOfSight", True))
        assumed_alt = float(b_rules.get("assumedAltitudeM", 50.0))
        site_ant = float(b_rules.get("siteAntennaHeightM", 10.0))

        def los_fn(sp: Vec2, cc: Vec2) -> bool:
            if not use_los or self.terrain is None:
                return True
            return self.terrain.has_line_of_sight_agl(sp, site_ant, cc, assumed_alt)

        out_pts: List[Vec2] = [path[0]]
        for i in range(len(path) - 1):
            p_a = path[i]
            p_b = path[i + 1]
            turns = AvoidanceAStar.compute_turning_points(
                0.0, 0.0, w_m, h_m, cell_m, max_cells, sites, threat_w, r_mult, valley_fn, valley_w, los_fn, p_a, p_b
            )
            max_wps = int(b_rules.get("maxWaypoints", 16))
            out_pts.extend(turns[:max_wps])
            out_pts.append(p_b)
        return out_pts

    def defer_group(self, level: Any, night: Dict[str, Any], wave_index: int, group_index: int) -> bool:
        w = night["waves"][wave_index]
        ai_tags = parse_ai_tags(w.get("aiTags"))
        if not ai_tags or AiTag.Suppress not in ai_tags:
            return False
        g = w["groups"][group_index]
        mdef = level.catalog.munitions.get(g["enemy"], {})
        return bool(mdef.get("antiRadiation"))

    def saturation_spawn_times(
        self, state: SimState, level: Any, night: Dict[str, Any], wave_index: int, group_indices: Sequence[int], base_sec: float
    ) -> Optional[List[float]]:
        w = night["waves"][wave_index]
        groups = w.get("groups", [])
        sat_rules = level.catalog.rules.get("enemy_ai", {}).get("saturate", {})
        win_sec = float(sat_rules.get("arrivalWindowSec", 30.0))

        # Estimate target center
        alive_st = [s for s in state.structures.alive_list() if s.hp > 0 and s.pos is not None]
        if alive_st:
            tot_w = sum(s.weight for s in alive_st)
            est_x = sum(s.pos.x * s.weight for s in alive_st) / max(1e-9, tot_w)
            est_y = sum(s.pos.y * s.weight for s in alive_st) / max(1e-9, tot_w)
            est_center = Vec2(est_x, est_y)
        else:
            w_m = float(level.meta.get("map", {}).get("widthM", 20000.0))
            h_m = float(level.meta.get("map", {}).get("heightM", 20000.0))
            est_center = Vec2(w_m * 0.5, h_m * 0.5)

        flights: List[float] = []
        for gi in group_indices:
            g = groups[gi]
            cnt = int(g.get("count", 1))
            ep = level.entry_points_by_id[g["entry"]]["pos"]
            t_spec = g.get("target") or {}
            if t_spec.get("structure") and t_spec["structure"] in state.structure_id_by_def_id:
                sid = state.structure_id_by_def_id[t_spec["structure"]]
                st_obj = state.structures.try_get_including_removed(sid)
                t_pos = st_obj.pos if st_obj and st_obj.pos else est_center
            else:
                t_pos = est_center
            wps = list((g.get("route") or {}).get("waypoints") or [])
            pts = [ep] + wps + [t_pos]
            dist_tot = 0.0
            for j in range(len(pts) - 1):
                dx = pts[j + 1].x - pts[j].x
                dy = pts[j + 1].y - pts[j].y
                dist_tot += math.sqrt(dx * dx + dy * dy)
            edef = level.catalog.munitions.get(g["enemy"]) or level.catalog.platforms.get(g["enemy"]) or {}
            spd = float(edef.get("cruiseSpeedMps", 50.0) or 50.0)
            fl_sec = dist_tot / max(1.0, spd)
            for _ in range(cnt):
                flights.append(fl_sec)

        n_tot = len(flights)
        if n_tot == 0:
            return None
        fracs = [(i / (n_tot - 1) if n_tot >= 2 else 0.0) for i in range(n_tot)]
        t_star = max(base_sec + fl - win_sec * fracs[i] for i, fl in enumerate(flights))
        return [t_star + win_sec * fracs[i] - fl for i, fl in enumerate(flights)]

    def _count_assigned_to_target(self, state: SimState, unit_id: int, pos: Vec2) -> int:
        cnt = 0
        for th in state.threats.alive_list():
            if th.phase != ThreatPhase.Arrived and th.target_kind == ThreatTargetKind.PlayerUnit:
                if unit_id > 0 and th.target_unit_id == unit_id:
                    cnt += 1
                elif unit_id == 0 and th.target_pos.distance_to(pos) <= 1.0:
                    cnt += 1
        return cnt

    def _count_arm_assigned_to_unit(self, state: SimState, unit_id: int) -> int:
        cnt = 0
        for th in state.threats.alive_list():
            if th.phase != ThreatPhase.Arrived and (th.homing_unit_id == unit_id or th.target_unit_id == unit_id):
                cnt += 1
        return cnt


class EnemyIntelSystem:
    """System 12: EnemyIntelSystem (04_enemy_ai_commands.md §3.2)."""

    order = 12
    name = "EnemyIntelSystem"
    stream_name = "enemy_ai"

    def initialize(self, ctx: Any) -> None:
        # 1. Import carry-in known_targets
        carry_kts = ctx.config.carry_in.known_targets or []
        for raw_kt in carry_kts:
            p_raw = raw_kt.get("pos", [0.0, 0.0])
            pos = Vec2(float(p_raw[0]), float(p_raw[1]))
            self._add_or_update_known_target(
                ctx,
                unit_id=int(raw_kt.get("unitId", 0)),
                roster_id=int(raw_kt.get("rosterId", 0)),
                unit_def_id=str(raw_kt.get("unitDefId", "")),
                kind=int(raw_kt.get("kind", 1)),
                reason=3,  # CarryIn
                pos=pos,
                exposure=float(raw_kt.get("exposure", 70.0)),
                priority=False,
            )

        # 2. Register held Suppress groups from waves
        _, night = ctx.wave_spawn_system._find_night(ctx)
        sup_rules = ctx.level.catalog.rules.get("enemy_ai", {}).get("suppress", {})
        max_hold_sec = float(sup_rules.get("maxHoldSec", 120.0))
        for wi, w in enumerate(night.get("waves", [])):
            if WaveSpawnRules.is_story_only_wave(ctx.level, w["id"]):
                continue
            ai_tags = parse_ai_tags(w.get("aiTags"))
            if ai_tags and AiTag.Suppress in ai_tags:
                deferred_gis = [
                    gi for gi in range(len(w.get("groups", [])))
                    if ctx.enemy_ai_hooks.defer_group(ctx.level, night, wi, gi)
                ]
                if deferred_gis:
                    at_sec = float(w.get("atSec", 0.0))
                    hold_until = SimTime.sec_to_ticks_ceil(at_sec + max_hold_sec, ctx.step_sec)
                    ctx.state.enemy_intel.held_waves.append(
                        HeldWaveGroup(
                            wave_id=w["id"],
                            wave_index=wi,
                            group_indices=deferred_gis,
                            hold_until_tick=hold_until,
                        )
                    )

    def execute(self, ctx: Any) -> None:
        ai_rules = ctx.level.catalog.rules.get("enemy_ai", {})
        probe_rad_m = float(ai_rules.get("probe", {}).get("observeRadiusM", 3000.0))
        exp100_frac = float(ai_rules.get("exposure100", {}).get("retargetFrac", 0.25))

        # 1. Check exposure threshold 100 crossings this step
        for ev in list(ctx.events.current_step):
            if ev.type == SimEventType.ExposureThresholdCrossed and ev.data.get("threshold") == 100:
                uid = int(ev.data.get("unit_id", 0))
                u = self._find_unit(ctx, uid)
                if u is not None and u.pos is not None:
                    kind_int = self._unit_kind_int(ctx, u)
                    self._add_or_update_known_target(
                        ctx,
                        unit_id=u.id,
                        roster_id=u.roster_id,
                        unit_def_id=u.def_id or "",
                        kind=kind_int,
                        reason=0,  # Exposure
                        pos=u.pos,
                        exposure=u.exposure,
                        priority=True,
                    )
                    # B-T3-05: Retarget 25% of pending weighted_random munitions
                    self._retarget_pending_spawns_on_exp100(ctx, u, exp100_frac)

        # 2. Check Probe observations when units fire near probe wave threats
        for ev in list(ctx.events.current_step):
            if ev.type in (SimEventType.InterceptorLaunched, SimEventType.GunFired):
                fuid = int(ev.data.get("fire_unit_id", 0) or 0)
                fu = ctx.state.fire_units.try_get(fuid) if fuid > 0 else None
                if (
                    fu is not None
                    and fu.pos is not None
                    and fu.id not in ctx.state.enemy_intel.probe_observed_unit_ids
                    and (fu.exposure >= 15.0 or (fu.emitter is not None and fu.emitter.on))
                ):
                    if self._near_probe_threat(ctx, fu.pos, probe_rad_m):
                        ctx.state.enemy_intel.probe_observed_unit_ids.append(fu.id)
                        self._add_or_update_known_target(
                            ctx,
                            unit_id=fu.id,
                            roster_id=fu.roster_id,
                            unit_def_id=fu.def_id or "",
                            kind=self._unit_kind_int(ctx, fu),
                            reason=1,  # ProbeObserved
                            pos=fu.pos,
                            exposure=fu.exposure,
                            priority=False,
                        )

        # 3. Check held Suppress wave groups
        if ctx.state.enemy_intel.held_waves:
            active_emitters = EmitterQueries.list_active(ctx.state)
            remaining_held: List[HeldWaveGroup] = []
            for hw in ctx.state.enemy_intel.held_waves:
                if active_emitters or ctx.tick >= hw.hold_until_tick:
                    ctx.state.waves.injections.append(
                        WaveInjection(wave_id=hw.wave_id, start_at_sec=ctx.time_sec, group_indices=hw.group_indices)
                    )
                    ctx.events.emit(
                        SimEventType.EnemyGroupsReleased,
                        fields=(hw.wave_id, len(hw.group_indices)),
                        wave_id=hw.wave_id,
                    )
                else:
                    remaining_held.append(hw)
            ctx.state.enemy_intel.held_waves = remaining_held

    def _near_probe_threat(self, ctx: Any, pos: Vec2, rad_m: float) -> bool:
        _, night = ctx.wave_spawn_system._find_night(ctx)
        probe_wave_ids = {
            w["id"]
            for w in night.get("waves", [])
            if (parse_ai_tags(w.get("aiTags")) and AiTag.Probe in parse_ai_tags(w.get("aiTags")))
        }
        for th in ctx.state.threats.alive_list():
            if th.wave_id in probe_wave_ids and th.pos is not None:
                if th.pos.distance_to(pos) <= rad_m + EPS:
                    return True
        return False

    def _retarget_pending_spawns_on_exp100(self, ctx: Any, u: PlayerUnitEntity, frac: float) -> None:
        elig = [
            ps for ps in ctx.state.waves.pending
            if (ps.target_spec or {}).get("mode", "weighted_random") == "weighted_random"
        ]
        if not elig:
            return
        quota = min(len(elig), max(1, int(math.ceil(len(elig) * frac - EPS))))
        for i in range(quota):
            elig[i].target_spec = {"mode": "known_targets"}

    def _add_or_update_known_target(
        self,
        ctx: Any,
        unit_id: int,
        roster_id: int,
        unit_def_id: str,
        kind: int,
        reason: int,
        pos: Vec2,
        exposure: float,
        priority: bool,
    ) -> None:
        kt_rules = ctx.level.catalog.rules.get("enemy_ai", {}).get("knownTargets", {})
        dedupe_m = float(kt_rules.get("dedupeRadiusM", 500.0))
        max_entries = int(kt_rules.get("maxEntries", 32))

        for kt in ctx.state.enemy_intel.known_targets:
            if (unit_id > 0 and kt.unit_id == unit_id) or kt.pos.distance_to(pos) <= dedupe_m + EPS:
                kt.pos = pos
                kt.exposure = max(kt.exposure, exposure)
                kt.priority = kt.priority or priority
                return

        if len(ctx.state.enemy_intel.known_targets) >= max_entries:
            ctx.state.enemy_intel.known_targets.pop(0)

        eid = ctx.state.enemy_intel.next_entry_id
        ctx.state.enemy_intel.next_entry_id += 1
        entry = KnownTargetEntry(
            entry_id=eid,
            unit_id=unit_id,
            roster_id=roster_id,
            unit_def_id=unit_def_id,
            kind=kind,
            reason=reason,
            pos=pos,
            exposure=exposure,
            added_tick=ctx.tick,
            priority=priority,
        )
        ctx.state.enemy_intel.known_targets.append(entry)
        ctx.events.emit(
            SimEventType.KnownTargetAdded,
            fields=(eid, unit_id, unit_def_id, kind, reason, pos),
            entry_id=eid,
            unit_id=unit_id,
            pos=pos,
        )

    def _find_unit(self, ctx: Any, uid: int) -> Optional[PlayerUnitEntity]:
        for store in (ctx.state.fire_units, ctx.state.sensors, ctx.state.ew_units, ctx.state.deception_units):
            u = store.try_get(uid)
            if u is not None:
                return u
        return None

    def _unit_kind_int(self, ctx: Any, u: PlayerUnitEntity) -> int:
        if isinstance(u, FireUnit):
            udef = ctx.level.catalog.air_defense_units.get(u.def_id or "", {})
            return 0 if udef.get("fireControlRadar") is not None else 1
        if isinstance(u, EwUnit):
            return 2
        if isinstance(u, SensorUnit):
            sdef = ctx.level.catalog.sensors.get(u.def_id or "", {})
            return 0 if sdef.get("emission") == "active" else 3
        return 0


class DeploymentStage:
    """Stage 0 deployment state machine (Packing -> Packed -> Moving -> Deploying -> Deployed) (04 §3.3)."""

    @staticmethod
    def step(ctx: Any) -> None:
        exp_rules = ctx.level.catalog.rules.get("exposure", {})
        reloc_cfg = exp_rules.get("onRelocate", {"resetTo": 0.0, "toScoutedPositionMult": 0.5})
        scouted_mult = float(reloc_cfg.get("toScoutedPositionMult", 0.5))

        for store in (ctx.state.fire_units, ctx.state.sensors, ctx.state.ew_units, ctx.state.deception_units):
            for u in store.alive_list():
                if getattr(u, "automatic", False):
                    continue
                rel = u.relocation
                if rel is not None:
                    if u.deploy_state == UnitDeployState.Packing and ctx.tick >= rel.pack_end_tick:
                        u.deploy_state = UnitDeployState.Moving
                        setattr(u, "_move_from_pos", u.pos)
                        setattr(u, "_move_start_tick", rel.pack_end_tick)
                        ctx.events.emit(
                            SimEventType.UnitDeployStateChanged,
                            fields=(u.id, int(UnitDeployState.Moving), u.pos),
                            unit_id=u.id,
                            state=UnitDeployState.Moving,
                        )
                    if u.deploy_state == UnitDeployState.Moving:
                        frm: Vec2 = getattr(u, "_move_from_pos", u.pos)
                        m_start: int = getattr(u, "_move_start_tick", rel.pack_end_tick)
                        d_tot = frm.distance_to(rel.dest)
                        spd = DeploymentStage.unit_move_speed_mps(ctx, u)
                        if d_tot > EPS and ctx.tick < rel.move_end_tick:
                            s = min(d_tot, spd * (ctx.tick - m_start) * ctx.step_sec)
                            u.pos = Vec2.lerp(frm, rel.dest, s / d_tot)
                        if ctx.tick >= rel.move_end_tick:
                            u.pos = rel.dest
                            u.deploy_state = UnitDeployState.Deploying
                            ctx.events.emit(
                                SimEventType.UnitDeployStateChanged,
                                fields=(u.id, int(UnitDeployState.Deploying), u.pos),
                                unit_id=u.id,
                                state=UnitDeployState.Deploying,
                            )
                    if u.deploy_state == UnitDeployState.Deploying and ctx.tick >= rel.deploy_end_tick:
                        u.pos = rel.dest
                        u.deploy_state = UnitDeployState.Deployed
                        if rel.scouted_on_departure:
                            u.exposure = u.exposure * scouted_mult
                        else:
                            u.exposure = float(reloc_cfg.get("resetTo", 0.0))
                        u.relocation = None
                        ctx.sensor_system._rebuild_horizon_for_unit(ctx, u)
                        ctx.state.commands.relocations_completed += 1
                        ctx.events.emit(
                            SimEventType.UnitDeployStateChanged,
                            fields=(u.id, int(UnitDeployState.Deployed), u.pos),
                            unit_id=u.id,
                            state=UnitDeployState.Deployed,
                        )
                else:
                    if u.deploy_state == UnitDeployState.Packing and u.deploy_phase_end_tick >= 0 and ctx.tick >= u.deploy_phase_end_tick:
                        u.deploy_state = UnitDeployState.Packed
                        u.deploy_phase_end_tick = -1
                        ctx.events.emit(
                            SimEventType.UnitDeployStateChanged,
                            fields=(u.id, int(UnitDeployState.Packed), u.pos),
                            unit_id=u.id,
                            state=UnitDeployState.Packed,
                        )
                    elif u.deploy_state == UnitDeployState.Deploying and u.deploy_phase_end_tick >= 0 and ctx.tick >= u.deploy_phase_end_tick:
                        u.deploy_state = UnitDeployState.Deployed
                        u.deploy_phase_end_tick = -1
                        ctx.sensor_system._rebuild_horizon_for_unit(ctx, u)
                        ctx.events.emit(
                            SimEventType.UnitDeployStateChanged,
                            fields=(u.id, int(UnitDeployState.Deployed), u.pos),
                            unit_id=u.id,
                            state=UnitDeployState.Deployed,
                        )

    @staticmethod
    def unit_move_speed_mps(ctx: Any, u: PlayerUnitEntity) -> float:
        udef = ctx.level.catalog.get_player_unit_def(u.def_id or "")
        return float(udef.get("moveSpeedMps") or (40.0 / 3.6))

    @staticmethod
    def unit_pack_deploy_sec(ctx: Any, u: PlayerUnitEntity) -> Tuple[float, float]:
        udef = ctx.level.catalog.get_player_unit_def(u.def_id or "")
        pack_sec = float(udef.get("packSec") or 60.0)
        deploy_sec = float(udef.get("deploySec") or 60.0)
        return pack_sec, deploy_sec

    @staticmethod
    def start_relocation(
        ctx: Any,
        u: PlayerUnitEntity,
        dest: Vec2,
        alt_id: Optional[str],
        is_emergency: bool,
    ) -> None:
        if u.pos is None:
            return
        pack_sec, deploy_sec = DeploymentStage.unit_pack_deploy_sec(ctx, u)
        spd = DeploymentStage.unit_move_speed_mps(ctx, u)
        dist = u.pos.distance_to(dest)
        move_ticks = SimTime.sec_to_ticks_ceil(dist / max(EPS, spd), ctx.step_sec)

        if u.deploy_state == UnitDeployState.Packed:
            pack_ticks = 0
        else:
            pack_ticks = SimTime.sec_to_ticks_ceil(pack_sec, ctx.step_sec)
        deploy_ticks = SimTime.sec_to_ticks_ceil(deploy_sec, ctx.step_sec)

        scouted_rad = float(ctx.level.catalog.rules.get("enemy_ai", {}).get("knownTargets", {}).get("scoutedRadiusM", 1000.0))
        scouted = any(kt.pos.distance_to(dest) <= scouted_rad + EPS for kt in ctx.state.enemy_intel.known_targets)

        pack_end = ctx.tick + pack_ticks
        move_end = pack_end + move_ticks
        dep_end = move_end + deploy_ticks
        u.relocation = RelocationOrder(
            dest=dest,
            alternate_position_id=alt_id,
            pack_end_tick=pack_end,
            move_end_tick=move_end,
            deploy_end_tick=dep_end,
            scouted_on_departure=scouted,
            is_emergency_relocate=is_emergency,
        )
        if pack_ticks > 0:
            u.deploy_state = UnitDeployState.Packing
        else:
            u.deploy_state = UnitDeployState.Moving
            setattr(u, "_move_from_pos", u.pos)
            setattr(u, "_move_start_tick", ctx.tick)
        if u.emitter is not None:
            u.emitter.on = False
        if alt_id:
            ctx.state.commands.alternate_positions_used[alt_id] = u.id
        ctx.events.emit(
            SimEventType.UnitDeployStateChanged,
            fields=(u.id, int(u.deploy_state), u.pos),
            unit_id=u.id,
            state=u.deploy_state,
        )

    @staticmethod
    def trigger_after_firing_relocate(ctx: Any, fu: FireUnit) -> None:
        alt_id = fu.pending_relocation_alt_id
        if not alt_id:
            return
        for ap in ctx.level.deploy.get("alternatePositions") or []:
            if ap.get("id") == alt_id and ap.get("pos") is not None:
                fu.pending_relocation_alt_id = None
                DeploymentStage.start_relocation(ctx, fu, ap["pos"], alt_id, is_emergency=True)
                return


class ChoiceStage:
    """Stage 0 choice timeout evaluation (04_enemy_ai_commands.md §3.3.5)."""

    @staticmethod
    def step(ctx: Any) -> None:
        for ch in ctx.state.choices.alive_list():
            if ctx.tick >= ch.deadline_tick:
                ctx.state.commands.choices_timed_out += 1
                ChoiceStage.resolve(ctx, ch, ch.default_option, timed_out=True)

    @staticmethod
    def resolve(ctx: Any, ch: ChoiceRequest, option_index: int, timed_out: bool) -> None:
        if ch.kind == 0:  # ArmIncoming
            EmissionChoiceEffects.apply_arm_choice(ctx.state, ch.subject_unit_id, silence=(option_index == 0))
        elif ch.kind == 1 and ch.story_event_id:
            StoryStage.apply_story_option(ctx, ch.story_event_id, option_index)
        ctx.events.emit(
            SimEventType.ChoiceResolved,
            fields=(ch.id, ch.choice_key, option_index, timed_out),
            choice_id=ch.id,
            option=option_index,
            timed_out=timed_out,
        )
        ctx.state.choices.remove(ch.id)


class StoryStage:
    """Stage 0 story event triggers and scheduled wave spawns (04_enemy_ai_commands.md §3.4)."""

    @staticmethod
    def step(ctx: Any) -> None:
        # 1. Process due scheduled spawns
        due = [sp for sp in ctx.state.commands.scheduled_spawns if sp.due_tick <= ctx.tick]
        ctx.state.commands.scheduled_spawns = [sp for sp in ctx.state.commands.scheduled_spawns if sp.due_tick > ctx.tick]
        for sp in due:
            ctx.state.waves.injections.append(WaveInjection(wave_id=sp.wave_id, start_at_sec=ctx.time_sec))

        # 2. Check story events
        events = ctx.level.story_events.get("events") or []
        for ev in events:
            eid = ev.get("id")
            if not eid or eid in ctx.state.commands.fired_story_events:
                continue
            ev_night = ev.get("night")
            if ev_night is not None and int(ev_night) != ctx.config.night_index:
                continue
            if StoryStage._matches_trigger(ctx, ev):
                ctx.state.commands.fired_story_events.append(eid)
                ctx.events.emit(SimEventType.StoryEventFired, fields=(eid,), event_id=eid)
                StoryStage._execute_event(ctx, ev)

    @staticmethod
    def _matches_trigger(ctx: Any, ev: Dict[str, Any]) -> bool:
        trig = ev.get("trigger") or ev.get("when") or ev.get("on") or "at_sec"
        if isinstance(trig, dict):
            kind = trig.get("type") or trig.get("kind") or "at_sec"
        else:
            kind = str(trig)

        if kind in ("at_sec", "time"):
            at_sec = float(ev.get("atSec") or (trig.get("atSec") if isinstance(trig, dict) else 0.0) or 0.0)
            return ctx.time_sec >= at_sec - EPS
        if kind == "wave_started":
            wid = ev.get("wave") or (trig.get("wave") if isinstance(trig, dict) else "")
            return wid in ctx.state.waves.started_wave_keys
        if kind == "structure_damaged":
            return any(s.hp < s.max_hp for s in ctx.state.structures.alive_list())
        if kind == "exposure_at_least":
            th_val = float(ev.get("threshold") or (trig.get("threshold") if isinstance(trig, dict) else 70.0) or 70.0)
            return any(
                u.exposure >= th_val
                for store in (ctx.state.fire_units, ctx.state.sensors, ctx.state.ew_units, ctx.state.deception_units)
                for u in store.alive_list()
            )
        return False

    @staticmethod
    def _execute_event(ctx: Any, ev: Dict[str, Any]) -> None:
        eid = ev["id"]
        if ev.get("dialogueKey") or ev.get("lineKey"):
            key = ev.get("dialogueKey") or ev.get("lineKey") or ""
            ctx.events.emit(SimEventType.DialogueShown, fields=(eid, key), event_id=eid, key=key)

        opts = ev.get("options")
        if opts:
            cmd_rules = ctx.level.catalog.rules.get("commands", {}).get("storyChoice", {})
            timeout_sec = float(ev.get("timeoutSec") or cmd_rules.get("defaultTimeoutSec", 60.0))
            deadline = ctx.tick + SimTime.sec_to_ticks_ceil(timeout_sec, ctx.step_sec)
            ch = ChoiceRequest(
                kind=1,
                choice_key=ev.get("choiceKey") or eid,
                option_count=len(opts),
                default_option=int(ev.get("defaultOption", 0)),
                deadline_tick=deadline,
                story_event_id=eid,
            )
            ctx.state.choices.add(ch)
            ctx.state.commands.choices_triggered += 1
            ctx.events.emit(
                SimEventType.ChoiceRequested,
                fields=(ch.id, ch.choice_key, ch.option_count, ch.deadline_tick),
                choice_id=ch.id,
            )
            return

        StoryStage._apply_effects(ctx, eid, ev)

    @staticmethod
    def apply_story_option(ctx: Any, event_id: str, option_index: int) -> None:
        for ev in ctx.level.story_events.get("events") or []:
            if ev.get("id") == event_id:
                opts = ev.get("options") or []
                if 0 <= option_index < len(opts):
                    opt = opts[option_index]
                    opt_id = opt.get("id", str(option_index)) if isinstance(opt, dict) else str(opt)
                    ctx.state.commands.story_choice_results[event_id] = opt_id
                    opt_effs = ev.get("optionEffects") or {}
                    if isinstance(opt, dict):
                        StoryStage._apply_effects(ctx, event_id, opt)
                    elif opt_id in opt_effs:
                        StoryStage._apply_effects(ctx, event_id, opt_effs[opt_id])
                break

    @staticmethod
    def _apply_effects(ctx: Any, event_id: str, eff: Dict[str, Any]) -> None:
        inj_wave = eff.get("injectWave") or eff.get("spawnWave")
        if inj_wave:
            delay_sec = float(eff.get("delaySec", 0.0) or 0.0)
            if delay_sec <= 0.0:
                ctx.state.waves.injections.append(WaveInjection(wave_id=inj_wave, start_at_sec=ctx.time_sec))
            else:
                due_t = ctx.tick + SimTime.sec_to_ticks_ceil(delay_sec, ctx.step_sec)
                ctx.state.commands.scheduled_spawns.append(
                    ScheduledSpawn(due_tick=due_t, wave_id=inj_wave, story_event_id=event_id)
                )
        if eff.get("commandPointsDelta") is not None:
            delta = int(eff["commandPointsDelta"])
            ctx.state.commands.command_points = max(0, ctx.state.commands.command_points + delta)
            ctx.events.emit(SimEventType.CommandPointsChanged, fields=(ctx.state.commands.command_points, delta))


class CommandStage:
    """Stage 0 command dispatch and validation (04_enemy_ai_commands.md §3.3, 00_core.md §3.4.1)."""

    @staticmethod
    def initialize(ctx: Any) -> None:
        econ_cp = ctx.level.catalog.rules.get("economy", {}).get("commandPointsPerNight", {})
        max_cp = int(econ_cp.get("max", 6))
        base_cp = int(ctx.level.meta.get("commandPointsPerNight", 4))
        bonus_cp = int(ctx.config.carry_in.command_points_bonus if ctx.config.carry_in else 0)
        cp_val = min(max(base_cp + bonus_cp, 0), max_cp)
        ctx.state.commands.command_points = cp_val
        ctx.state.commands.command_points_initial = cp_val

        # Trigger any NightStart story events at tick 0
        for ev in ctx.level.story_events.get("events") or []:
            eid = ev.get("id")
            if not eid or eid in ctx.state.commands.fired_story_events:
                continue
            ev_night = ev.get("night")
            if ev_night is not None and int(ev_night) != ctx.config.night_index:
                continue
            trig = ev.get("trigger") or ev.get("when") or ev.get("on")
            kind = trig.get("type") if isinstance(trig, dict) else str(trig or "")
            if kind in ("night_start", "NightStart"):
                ctx.state.commands.fired_story_events.append(eid)
                ctx.events.emit(SimEventType.StoryEventFired, fields=(eid,), event_id=eid)
                StoryStage._execute_event(ctx, ev)

    @staticmethod
    def execute(ctx: Any, commands: Sequence[SimCommand]) -> None:
        for cmd in commands:
            CommandStage.apply_command(ctx, cmd)
        DeploymentStage.step(ctx)
        ChoiceStage.step(ctx)
        StoryStage.step(ctx)

    @staticmethod
    def cost_for(ctx: Any, cmd_type: SimCommandType) -> int:
        costs = ctx.level.catalog.rules.get("commands", {}).get("commandPointCosts", {})
        key_map = {
            SimCommandType.Noop: ("noop", 0),
            SimCommandType.SetEmissionPolicy: ("set_emission_policy", 1),
            SimCommandType.SectorEmissionOverride: ("sector_emission_override", 1),
            SimCommandType.SetEngagementRule: ("set_engagement_rule", 1),
            SimCommandType.CallSupport: ("call_support", 0),
            SimCommandType.SetAirRaidAlert: ("set_air_raid_alert", 1),
            SimCommandType.SetFighterZone: ("set_fighter_zone", 0),
            SimCommandType.DeployUnit: ("deploy_unit", 0),
            SimCommandType.PackUnit: ("pack_unit", 1),
            SimCommandType.MoveUnit: ("move_unit", 1),
            SimCommandType.RelocateUnit: ("relocate_unit", 1),
            SimCommandType.AnswerChoice: ("answer_choice", 0),
        }
        k, def_val = key_map.get(cmd_type, ("noop", 0))
        return int(costs.get(k, def_val))

    @staticmethod
    def apply_command(ctx: Any, cmd: SimCommand) -> bool:
        if cmd.type == SimCommandType.Noop:
            ctx.events.emit(SimEventType.CommandApplied, fields=( cmd.seq, int(cmd.type)), command_seq=cmd.seq, command_type=cmd.type)
            return True

        cost = CommandStage.cost_for(ctx, cmd.type)
        reject = CommandStage._validate_and_execute(ctx, cmd, cost)
        if reject is not None:
            ctx.events.emit(
                SimEventType.CommandRejected,
                fields=(cmd.seq, int(cmd.type), int(reject)),
                command_seq=cmd.seq,
                command_type=cmd.type,
                reason=reject,
            )
            return False

        ctx.events.emit(SimEventType.CommandApplied, fields=(cmd.seq, int(cmd.type)), command_seq=cmd.seq, command_type=cmd.type)
        return True

    @staticmethod
    def _find_unit(ctx: Any, uid: int) -> Optional[PlayerUnitEntity]:
        for store in (ctx.state.fire_units, ctx.state.sensors, ctx.state.ew_units, ctx.state.deception_units):
            u = store.try_get(uid)
            if u is not None:
                return u
        return None

    @staticmethod
    def _spend_cp(ctx: Any, cost: int) -> Optional[CommandRejectReason]:
        if cost <= 0:
            return None
        if ctx.state.commands.command_points < cost:
            return CommandRejectReason.NoCommandPoints
        ctx.state.commands.command_points -= cost
        ctx.state.commands.command_points_spent += cost
        ctx.events.emit(SimEventType.CommandPointsChanged, fields=(ctx.state.commands.command_points, -cost))
        return None

    @staticmethod
    def _validate_and_execute(ctx: Any, cmd: SimCommand, cost: int = 0) -> Optional[CommandRejectReason]:
        p = cmd.params or {}
        cat = ctx.level.catalog

        if cmd.type == SimCommandType.SetEmissionPolicy:
            uid = int(p.get("unitId", p.get("unit_id", 0)))
            pol = str(p.get("policyId", p.get("policy", "")))
            u = CommandStage._find_unit(ctx, uid)
            if u is None:
                return CommandRejectReason.UnknownEntity
            if u.emitter is None:
                return CommandRejectReason.WrongEntityKind
            strat = next((s for s in cat.rules.get("emission", {}).get("strategies", []) if s["id"] == pol), None)
            if strat is None and pol not in ("continuous", "silent", "blink", "always_on"):
                return CommandRejectReason.InvalidArgument
            if strat is not None:
                rej = EmissionPolicyRules.check_available(u.def_id or "", strat, ctx.level)
                if rej is not None:
                    return rej
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            u.emitter.policy_id = pol
            u.emitter.sector_override = 0
            if p.get("dutyOnSec") is not None:
                u.emitter.duty_on_sec = float(p["dutyOnSec"])
            if p.get("dutyOffSec") is not None:
                u.emitter.duty_off_sec = float(p["dutyOffSec"])
            return None

        if cmd.type == SimCommandType.SectorEmissionOverride:
            mode = int(p.get("override", p.get("mode", 1)))
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            for store in (ctx.state.fire_units, ctx.state.sensors, ctx.state.ew_units, ctx.state.deception_units):
                for u in store.alive_list():
                    if u.emitter is not None:
                        u.emitter.sector_override = mode
            return None

        if cmd.type == SimCommandType.SetEngagementRule:
            uid = int(p.get("unitId", p.get("unit_id", 0)))
            fu = ctx.state.fire_units.try_get(uid)
            if fu is None:
                return CommandRejectReason.UnknownEntity
            rule_val = p.get("rule", 0)
            if isinstance(rule_val, str):
                rmap = {"any": 0, "any_in_range": 0, "ballistic_only": 1, "hold_fire": 2, "high_value_only": 3, "high_threat_only": 3}
                if rule_val not in rmap:
                    return CommandRejectReason.InvalidArgument
                rule_int = rmap[rule_val]
            else:
                rule_int = int(rule_val)
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            for wslot in fu.weapons:
                wslot.rule = rule_int
            return None

        if cmd.type == SimCommandType.SetAirRaidAlert:
            on = bool(p.get("on", True))
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            civ = ctx.state.civil
            if civ.alert_on != on:
                civ.alert_on = on
                if on:
                    civ.alert_switched_on_sec = ctx.time_sec
                ctx.events.emit(SimEventType.AirRaidAlertChanged, fields=(on,), on=on)
            return None

        if cmd.type == SimCommandType.SetFighterZone:
            sa_id = int(p.get("supportAssetId", p.get("asset_id", 0)))
            sa = ctx.state.support_assets.try_get(sa_id) if sa_id > 0 else next(
                (a for a in ctx.state.support_assets.alive_list() if a.support_kind == 0), None
            )
            if sa is None:
                return CommandRejectReason.UnknownEntity
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            if p.get("pos") is not None:
                raw_p = p["pos"]
                sa.pos = raw_p if isinstance(raw_p, Vec2) else Vec2(float(raw_p[0]), float(raw_p[1]))
            if p.get("exclusive") is not None:
                sa.exclusive_zone = bool(p["exclusive"])
            return None

        if cmd.type == SimCommandType.CallSupport:
            sup_id = str(p.get("supportId", p.get("support_id", "fighter")))
            raw_pos = p.get("pos", [10000.0, 10000.0])
            pos = raw_pos if isinstance(raw_pos, Vec2) else Vec2(float(raw_pos[0]), float(raw_pos[1]))
            if sup_id in ("fighter", "fighter_patrol") or sup_id in cat.fighters:
                if ctx.state.support.sorties_remaining <= 0:
                    return CommandRejectReason.NoSortiesLeft
                cp_rej = CommandStage._spend_cp(ctx, cost)
                if cp_rej is not None:
                    return cp_rej
                fid = sup_id if sup_id in cat.fighters else next(iter(cat.fighters.keys()), "mig29")
                fdef = cat.fighters.get(fid, {})
                w_list = fdef.get("weapons") or []
                wid = w_list[0]["id"] if w_list else "r27"
                ammo = int(w_list[0].get("magazine", 4)) if w_list else 4
                arr_sec = ctx.time_sec + float(fdef.get("responseSec", 60.0))
                dur_sec = float(fdef.get("patrolSec", 300.0))
                rad_m = float(fdef.get("patrolRadiusM", 15000.0))
                ctx.state.support.sorties_remaining -= 1
                ctx.state.support.sorties_used += 1
                sa = SupportAsset(
                    def_id=fid,
                    pos=pos,
                    alt_m=3000.0,
                    support_kind=0,
                    state=0,
                    arrive_sec=arr_sec,
                    end_sec=arr_sec + dur_sec,
                    radius_m=rad_m,
                    exclusive_zone=bool(p.get("exclusive", False)),
                    fighter_id=fid,
                    weapon_id=wid,
                    ammo_remaining=ammo,
                    next_shot_sec=arr_sec,
                )
                ctx.state.support_assets.add(sa)
                ctx.events.emit(SimEventType.SupportRequested, fields=(sa.id, fid, pos), support_asset_id=sa.id)
                return None
            return CommandRejectReason.NotAvailable

        if cmd.type == SimCommandType.PackUnit:
            uid = int(p.get("unitId", p.get("unit_id", 0)))
            u = CommandStage._find_unit(ctx, uid)
            if u is None:
                return CommandRejectReason.UnknownEntity
            if u.deploy_state != UnitDeployState.Deployed:
                return CommandRejectReason.InvalidState
            udef = cat.get_player_unit_def(u.def_id or "")
            if udef.get("mobility") == "fixed":
                return CommandRejectReason.InvalidState
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            pack_sec, _ = DeploymentStage.unit_pack_deploy_sec(ctx, u)
            u.deploy_state = UnitDeployState.Packing
            u.deploy_phase_end_tick = ctx.tick + SimTime.sec_to_ticks_ceil(pack_sec, ctx.step_sec)
            if u.emitter is not None:
                u.emitter.on = False
            ctx.events.emit(SimEventType.UnitDeployStateChanged, fields=(u.id, int(u.deploy_state), u.pos), unit_id=u.id)
            return None

        if cmd.type == SimCommandType.DeployUnit:
            uid = int(p.get("unitId", p.get("unit_id", 0)))
            u = CommandStage._find_unit(ctx, uid)
            if u is None:
                return CommandRejectReason.UnknownEntity
            if u.deploy_state != UnitDeployState.Packed:
                return CommandRejectReason.InvalidState
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            _, dep_sec = DeploymentStage.unit_pack_deploy_sec(ctx, u)
            u.deploy_state = UnitDeployState.Deploying
            u.deploy_phase_end_tick = ctx.tick + SimTime.sec_to_ticks_ceil(dep_sec, ctx.step_sec)
            ctx.events.emit(SimEventType.UnitDeployStateChanged, fields=(u.id, int(u.deploy_state), u.pos), unit_id=u.id)
            return None

        if cmd.type in (SimCommandType.MoveUnit, SimCommandType.RelocateUnit):
            uid = int(p.get("unitId", p.get("unit_id", 0)))
            u = CommandStage._find_unit(ctx, uid)
            if u is None:
                return CommandRejectReason.UnknownEntity
            if u.deploy_state not in (UnitDeployState.Deployed, UnitDeployState.Packed):
                return CommandRejectReason.InvalidState
            udef = cat.get_player_unit_def(u.def_id or "")
            if udef.get("mobility") == "fixed":
                return CommandRejectReason.InvalidState
            alt_id = p.get("alternatePositionId", p.get("position_id"))
            dest: Optional[Vec2] = None
            if alt_id:
                for ap in ctx.level.deploy.get("alternatePositions") or []:
                    if ap.get("id") == alt_id:
                        dest = ap.get("pos")
                        break
                if dest is None:
                    return CommandRejectReason.InvalidArgument
            elif p.get("dest") is not None or p.get("pos") is not None:
                raw_d = p.get("dest") or p.get("pos")
                dest = raw_d if isinstance(raw_d, Vec2) else Vec2(float(raw_d[0]), float(raw_d[1]))
            if dest is None:
                return CommandRejectReason.InvalidArgument
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            DeploymentStage.start_relocation(
                ctx, u, dest, alt_id, is_emergency=(cmd.type == SimCommandType.RelocateUnit)
            )
            return None

        if cmd.type == SimCommandType.AnswerChoice:
            cid = int(p.get("choiceId", p.get("choice_id", 0)))
            opt = int(p.get("option", p.get("option_index", 0)))
            ch = ctx.state.choices.try_get(cid) if cid > 0 else (
                ctx.state.choices.alive_list()[0] if ctx.state.choices.alive_list() else None
            )
            if ch is None:
                return CommandRejectReason.UnknownEntity
            if opt < 0 or opt >= ch.option_count:
                return CommandRejectReason.InvalidArgument
            cp_rej = CommandStage._spend_cp(ctx, cost)
            if cp_rej is not None:
                return cp_rej
            ChoiceStage.resolve(ctx, ch, opt, timed_out=False)
            return None

        return None
