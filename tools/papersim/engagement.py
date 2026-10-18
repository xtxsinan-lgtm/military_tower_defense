"""Engagement, interceptor, external support, impact, grid, civil, and scoring systems (03_engagement_impact_scoring.md)."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .core import Geo, SimTime, Vec2
from .entities import (
    AccuracyTier,
    Debris,
    DeceptionUnit,
    EndRequest,
    EntityKind,
    EwUnit,
    FireUnit,
    GridNode,
    Interceptor,
    LauncherState,
    NightEndReason,
    NightOutcome,
    NightResult,
    PlayerUnitCategory,
    PlayerUnitEntity,
    SensorUnit,
    SimEventType,
    Structure,
    SupportAsset,
    TargetTag,
    Threat,
    ThreatKind,
    ThreatPhase,
    ThreatTargetKind,
    Track,
    TrackQuality,
    UnitDeployState,
    WeaponSlotState,
)
from .movement import ThreatKinematics, ThreatRouting, parse_target_tag
from .sensing import EnvironmentResolver, EwQueries, FireControlQueries

EPS = 1e-9
BISECTION_ITERS = 32


@dataclass(frozen=True)
class InterceptSolution:
    dt_sec: float
    pos: Vec2
    alt_m: float


class InterceptSolver:
    """3D bracket + 32-step bisection intercept solver (03_engagement_impact_scoring.md §3.0.2, C-T1-05, C-T2-10)."""

    @staticmethod
    def solve(
        origin: Vec2,
        speed_mps: float,
        range_m: float,
        ceiling_m: float,
        predict_fn: Callable[[float], Tuple[Vec2, float, bool]],
        sample_sec: float = 1.0,
        iters: int = BISECTION_ITERS,
        max_speed_3d: Optional[float] = None,
    ) -> Optional[InterceptSolution]:
        if speed_mps <= 0.0:
            return None

        def reach(dt: float) -> bool:
            pos, alt, arrived = predict_fn(dt)
            dx = pos.x - origin.x
            dy = pos.y - origin.y
            d3 = math.sqrt(dx * dx + dy * dy + alt * alt)
            return speed_mps * dt + EPS >= d3

        tmax = math.sqrt(range_m * range_m + ceiling_m * ceiling_m) / speed_mps
        k_max = max(1, int(math.ceil(tmax / sample_sec - EPS)))

        if max_speed_3d is not None:
            pos0, alt0, arr0 = predict_fn(0.0)
            if arr0:
                return None
            dx0 = pos0.x - origin.x
            dy0 = pos0.y - origin.y
            d3d_0 = math.sqrt(dx0 * dx0 + dy0 * dy0 + alt0 * alt0)
            k0 = max(1, int(math.floor(d3d_0 / ((speed_mps + max(0.0, max_speed_3d)) * sample_sec))))
        else:
            k0 = 1

        if k0 > k_max:
            return None

        lo = (k0 - 1) * sample_sec
        hi: Optional[float] = None
        for k in range(k0, k_max + 1):
            t = k * sample_sec
            if predict_fn(t)[2]:
                return None
            if reach(t):
                hi = t
                break
            lo = t

        if hi is None:
            return None

        for _ in range(iters):
            mid = lo + (hi - lo) * 0.5
            if reach(mid):
                hi = mid
            else:
                lo = mid

        pos_f, alt_f, arrived_f = predict_fn(hi)
        if arrived_f:
            return None
        dx_f = pos_f.x - origin.x
        dy_f = pos_f.y - origin.y
        h_dist = math.sqrt(dx_f * dx_f + dy_f * dy_f)
        if h_dist > range_m + EPS or alt_f > ceiling_m + EPS or alt_f < -EPS:
            return None
        return InterceptSolution(dt_sec=hi, pos=pos_f, alt_m=max(0.0, alt_f))

    @staticmethod
    def solve_threat(
        origin: Vec2,
        speed_mps: float,
        range_m: float,
        ceiling_m: float,
        th: Threat,
        now_sec: float,
        use_accel: bool = True,
    ) -> Optional[InterceptSolution]:
        arr_sec = ThreatKinematics.predict_arrival_sec(th)

        def pred(dt: float) -> Tuple[Vec2, float, bool]:
            t_abs = now_sec + dt
            if arr_sec is not None and t_abs > arr_sec + EPS:
                pose = ThreatKinematics.predict(th, arr_sec)
                return pose.pos, pose.alt_m, True
            pose = ThreatKinematics.predict(th, t_abs)
            return pose.pos, pose.alt_m, pose.at_path_end

        vmax = ThreatKinematics.max_speed_3d_mps(th) if use_accel else None
        return InterceptSolver.solve(origin, speed_mps, range_m, ceiling_m, pred, max_speed_3d=vmax)


class WeaponParams:
    """Helper for resolving weapon parameters and intercept probabilities (03_engagement_impact_scoring.md §3.0.1)."""

    @staticmethod
    def resolve_weapon_def(ctx: Any, fu: FireUnit, wslot: WeaponSlotState) -> Dict[str, Any]:
        cat = ctx.level.catalog
        wdef = dict(cat.weapons.get(wslot.weapon_id, {}))
        eng_rules = cat.rules.get("engagement", {})
        by_kind = eng_rules.get("byWeaponKind", {})
        w_kind = wdef.get("kind", "missile")
        kind_defaults = by_kind.get(w_kind, {})
        ic_class = wdef.get("interceptClass", w_kind)
        reac_by_cls = eng_rules.get("reactionSecByClass", {})

        reaction_sec = float(wdef.get("reactionSec") or reac_by_cls.get(ic_class) or kind_defaults.get("reactionSec", 3.0))
        shot_interval_sec = float(wdef.get("shotIntervalSec") or kind_defaults.get("shotIntervalSec", 15.0))
        speed_mps = float(wdef.get("interceptorSpeedMps") or kind_defaults.get("interceptorSpeedMps", 900.0))
        range_m = float(wdef.get("rangeM", 5000.0))
        ceiling_m = float(wdef.get("ceilingM", 3000.0))
        shot_cost_musd = float(wdef.get("shotCostMusd", 0.0) or 0.0)

        return {
            "id": wslot.weapon_id,
            "kind": w_kind,
            "intercept_class": ic_class,
            "range_m": range_m,
            "ceiling_m": ceiling_m,
            "speed_mps": speed_mps,
            "reaction_sec": reaction_sec,
            "shot_interval_sec": shot_interval_sec,
            "shot_cost_musd": shot_cost_musd,
            "magazine": wdef.get("magazine"),
            "reload_sec": float(wdef.get("reloadSec") or 0.0),
            "targets": [parse_target_tag(t) for t in (wdef.get("targets") or [])],
            "barrel_cooldown": bool(wdef.get("barrelCooldown", False)),
            "guidance": wdef.get("guidance", "active"),
        }

    @staticmethod
    def base_prob(ctx: Any, ic_class: str, tag: Optional[TargetTag]) -> float:
        if tag is None:
            return 0.0
        int_rules = ctx.level.catalog.rules.get("intercept", {})
        cls_map = int_rules.get("classes", {}).get(ic_class, {})
        col = int_rules.get("decoyUsesColumn", "UAV") if tag == TargetTag.DECOY else tag.name
        return float(cls_map.get(col, 0.0))

    @staticmethod
    def compute_hit_prob(
        ctx: Any,
        fu: Optional[FireUnit],
        ic_class: str,
        w_kind: str,
        th: Threat,
        tr: Optional[Track],
        intercept_pos: Vec2,
    ) -> float:
        int_rules = ctx.level.catalog.rules.get("intercept", {})
        mods = int_rules.get("modifiers", {})
        p = WeaponParams.base_prob(ctx, ic_class, th.tag)
        if p <= 0.0:
            return 0.0

        # Track quality modifier
        if tr is not None and tr.quality == TrackQuality.Vague:
            if w_kind != "gun":
                return 0.0
            p *= float(mods.get("trackVague", {}).get("gunProbMult", 0.5))

        if fu is not None:
            if fu.new_position_penalty:
                p *= float(mods.get("newPositionFirstNight", {}).get("probMult", 0.7))
            min_fat = int(mods.get("crewFatigue", {}).get("minConsecutiveNights", 3))
            if fu.crew_consecutive_nights >= min_fat:
                p *= float(mods.get("crewFatigue", {}).get("probMult", 0.85))
            if fu.ace_crew:
                p *= float(mods.get("aceCrew", {}).get("probMult", 1.15))
            p *= float(fu.damage_efficiency_mult)
            if fu.deploy_state == UnitDeployState.Moving:
                udef = ctx.level.catalog.air_defense_units.get(fu.def_id or "", {})
                if udef.get("fireOnMove") == "partial":
                    p *= 0.5

        if ic_class in ("interceptor_drone", "jet_interceptor_drone"):
            if EwQueries.is_in_friendly_ew_zone(ctx.state, ctx.level.catalog, intercept_pos, ctx.time_sec):
                p *= float(mods.get("interceptorDroneInFriendlyEw", {}).get("probMult", 0.6))
            ev_mod = mods.get("evasiveTargetVsInterceptorDrone", {})
            if ev_mod.get("active") and (th.def_id or "") in (ev_mod.get("enemies") or []):
                p *= float(ev_mod.get("probMult", 0.6))

        return min(0.95, max(0.0, p))


class EngagementSystem:
    """System 7: EngagementSystem (03_engagement_impact_scoring.md §3.1)."""

    order = 7
    name = "EngagementSystem"
    stream_name = "engagement"

    def initialize(self, ctx: Any) -> None:
        cat = ctx.level.catalog
        def_launchers = int(cat.rules.get("engagement", {}).get("defaultLaunchers", 1))
        for fu in ctx.state.fire_units.alive_list():
            udef = cat.air_defense_units.get(fu.def_id or "", {})
            if not fu.weapons:
                for wid in udef.get("weaponIds", []):
                    wdef = cat.weapons.get(wid, {})
                    mag = wdef.get("magazine")
                    raw_ln = wdef.get("launchers") or udef.get("launchers") or def_launchers
                    n_launchers = max(1, int(raw_ln) - fu.launchers_lost)
                    rounds = int(mag) if mag is not None else 999999
                    launchers = [LauncherState(rounds=rounds, max_rounds=rounds) for _ in range(n_launchers)]
                    fu.weapons.append(WeaponSlotState(weapon_id=wid, rule=0, launchers=launchers))

    def execute(self, ctx: Any) -> None:
        cat = ctx.level.catalog
        tr_rules = cat.rules.get("tracks", {})
        em_rules = cat.rules.get("emission", {})
        eng_rules = cat.rules.get("engagement", {})
        sup_rules = cat.rules.get("support", {})
        barrel_cfg = eng_rules.get("barrelCooldown", {"burstsBeforeCooldown": 5, "cooldownSec": 60.0})
        bursts_limit = int(barrel_cfg.get("burstsBeforeCooldown", 5))
        cooldown_sec = float(barrel_cfg.get("cooldownSec", 60.0))

        # 1. Process launcher reloads
        for fu in ctx.state.fire_units.alive_list():
            for wslot in fu.weapons:
                wp = WeaponParams.resolve_weapon_def(ctx, fu, wslot)
                for ln in wslot.launchers:
                    if not ln.destroyed and ln.rounds == 0 and ln.reload_until_sec > 0.0 and ctx.time_sec >= ln.reload_until_sec - EPS:
                        ln.reload_until_sec = 0.0
                        pool_rem = ctx.state.engagement.ammo_pool.get(wslot.weapon_id)
                        take = int(wp["magazine"] or 1)
                        if pool_rem is not None:
                            take = min(take, pool_rem)
                            ctx.state.engagement.ammo_pool[wslot.weapon_id] = pool_rem - take
                        ln.rounds = take

        # 2. Evaluate engagements across tracks
        # Build active fighter zones
        fighter_zones: List[Tuple[Vec2, float, bool]] = []
        for sa in ctx.state.support_assets.alive_list():
            if sa.support_kind == 0 and sa.state == 1 and sa.pos is not None:
                fighter_zones.append((sa.pos, sa.radius_m, sa.exclusive_zone))

        # For each alive track, find eligible (FireUnit, WeaponSlot) pairs
        for tr in ctx.state.tracks.alive_list():
            if tr.threat_id <= 0:
                continue
            th = ctx.state.threats.try_get(tr.threat_id)
            if th is None or th.phase == ThreatPhase.Arrived or th.pos is None:
                continue
            if tr.identified_as_decoy:
                continue

            # Check if an interceptor is already in flight for this threat (shoot-look-shoot default)
            in_flight_for_th = [ic for ic in ctx.state.interceptors.alive_list() if ic.threat_id == th.id]
            if in_flight_for_th:
                continue

            cands: List[Tuple[float, int, FireUnit, WeaponSlotState, Dict[str, Any], InterceptSolution, float]] = []
            for fu in ctx.state.fire_units.alive_list():
                if not self._unit_can_engage(ctx, fu):
                    continue
                for wslot in fu.weapons:
                    if wslot.rule == 2:  # HoldFire
                        continue
                    if wslot.rule == 1 and th.tag not in (TargetTag.BM, TargetTag.HBM):
                        continue
                    if wslot.rule == 3 and th.tag not in (
                        TargetTag.CM,
                        TargetTag.SCM,
                        TargetTag.BM,
                        TargetTag.HBM,
                        TargetTag.AC_HIGH,
                        TargetTag.AC_LOW,
                    ):
                        continue
                    wlist = getattr(wslot, "whitelist", None)
                    if wlist is not None and th.tag not in wlist:
                        continue
                    ammo_res = int(getattr(wslot, "ammo_reserve", 0) or 0)
                    if ammo_res > 0 and th.tag not in (
                        TargetTag.CM,
                        TargetTag.SCM,
                        TargetTag.BM,
                        TargetTag.HBM,
                        TargetTag.AC_HIGH,
                    ):
                        tot_rounds = sum(ln.rounds for ln in wslot.launchers if not ln.destroyed)
                        if tot_rounds <= ammo_res:
                            continue
                    wp = WeaponParams.resolve_weapon_def(ctx, fu, wslot)
                    if th.tag not in wp["targets"]:
                        continue
                    if tr.quality == TrackQuality.Vague and wp["kind"] != "gun":
                        continue
                    if ctx.time_sec < wslot.next_shot_sec - EPS or ctx.time_sec < wslot.cooldown_until_sec - EPS:
                        continue
                    avail_ln = self._pick_launcher(wslot)
                    if avail_ln is None:
                        continue

                    # Check fighter airspace restriction
                    in_excl = False
                    in_restr = False
                    if fu.pos is not None:
                        for fpos, frad, fexcl in fighter_zones:
                            if th.pos.distance_to(fpos) <= frad + EPS:
                                if fexcl:
                                    in_excl = True
                                else:
                                    in_restr = True
                    if in_excl:
                        continue
                    if in_restr and not tr.classified:
                        continue

                    sol = InterceptSolver.solve_threat(
                        fu.pos, wp["speed_mps"], wp["range_m"], wp["ceiling_m"], th, ctx.time_sec
                    )
                    if sol is None:
                        continue

                    # Check forbidden zones on intercept point
                    if self._in_forbidden_fire_zone(ctx, sol.pos):
                        continue

                    # Reaction time gate
                    ready_sec = wslot.first_shot_ready_sec.get(tr.id)
                    if ready_sec is None:
                        reac = wp["reaction_sec"] * FireControlQueries.reaction_mult(fu, em_rules)
                        if not tr.cued:
                            reac *= float(tr_rules.get("cueing", {}).get("uncued", {}).get("firstShotReactionTimeMult", 1.5))
                        if in_restr:
                            reac *= float(sup_rules.get("airspace", {}).get("restrictedEngagement", {}).get("reactionTimeMult", 1.3))
                        ready_sec = ctx.time_sec + reac
                        wslot.first_shot_ready_sec[tr.id] = ready_sec
                    if ctx.time_sec < ready_sec - EPS:
                        continue

                    p_hit = WeaponParams.compute_hit_prob(ctx, fu, wp["intercept_class"], wp["kind"], th, tr, sol.pos)
                    if p_hit <= 0.0:
                        continue
                    exp_cost = wp["shot_cost_musd"] / p_hit
                    cands.append((exp_cost, fu.id, fu, wslot, wp, sol, p_hit))

            if not cands:
                continue
            cands.sort(key=lambda item: (item[0], item[1]))
            _, _, best_fu, best_wslot, best_wp, best_sol, best_p = cands[0]
            self._fire_weapon(ctx, best_fu, best_wslot, best_wp, tr, th, best_sol, best_p, bursts_limit, cooldown_sec)

    def _unit_can_engage(self, ctx: Any, fu: FireUnit) -> bool:
        if fu.pos is None or fu.suspended_until_sec > ctx.time_sec + EPS:
            return False
        udef = ctx.level.catalog.air_defense_units.get(fu.def_id or "", {})
        if udef.get("fireControlRadar") is not None:
            if fu.radar_destroyed or fu.emitter is None or not fu.emitter.on:
                return False
        if fu.deploy_state == UnitDeployState.Moving:
            return udef.get("fireOnMove", "no") in ("yes", "partial")
        return fu.deploy_state == UnitDeployState.Deployed

    def _pick_launcher(self, wslot: WeaponSlotState) -> Optional[int]:
        for idx, ln in enumerate(wslot.launchers):
            if not ln.destroyed and ln.rounds > 0:
                return idx
        return None

    def _in_forbidden_fire_zone(self, ctx: Any, pt: Vec2) -> bool:
        for fz in ctx.level.deploy.get("forbiddenFireZones") or []:
            poly = fz.get("polygon") or []
            if poly and Geo.point_in_polygon(pt, poly):
                return True
        return False

    def _fire_weapon(
        self,
        ctx: Any,
        fu: FireUnit,
        wslot: WeaponSlotState,
        wp: Dict[str, Any],
        tr: Track,
        th: Threat,
        sol: InterceptSolution,
        p_hit: float,
        bursts_limit: int,
        cooldown_sec: float,
    ) -> None:
        eng_rules = ctx.level.catalog.rules.get("engagement", {})
        tag_name = th.tag.name if th.tag is not None else ""
        tag_rule = eng_rules.get("defaultRuleByTag", {}).get(wp["intercept_class"], {}).get(tag_name, {})
        salvo_size = int(tag_rule.get("salvoSize", 1)) if not bool(tag_rule.get("shootLookShoot", True)) else 1

        for _ in range(max(1, salvo_size)):
            ln_idx = self._pick_launcher(wslot)
            if ln_idx is None:
                break
            ln = wslot.launchers[ln_idx]
            if wp["magazine"] is not None:
                ln.rounds -= 1
                if ln.rounds == 0 and wp["reload_sec"] > 0.0:
                    pool_rem = ctx.state.engagement.ammo_pool.get(wslot.weapon_id)
                    if pool_rem is None or pool_rem > 0:
                        ln.reload_until_sec = ctx.time_sec + wp["reload_sec"]

            wslot.next_shot_sec = ctx.time_sec + wp["shot_interval_sec"]
            if wp["barrel_cooldown"]:
                wslot.continuous_fire_sec += 1.0
                if wslot.continuous_fire_sec >= bursts_limit - EPS:
                    wslot.continuous_fire_sec = 0.0
                    wslot.cooldown_until_sec = ctx.time_sec + cooldown_sec

            wid = wslot.weapon_id
            cost = wp["shot_cost_musd"]
            ctx.state.scoring.defense_cost_musd += cost
            ctx.state.scoring.shots_fired_by_weapon[wid] = ctx.state.scoring.shots_fired_by_weapon.get(wid, 0) + 1
            ctx.state.engagement.per_level_used[wid] = ctx.state.engagement.per_level_used.get(wid, 0) + 1
            th.shots_taken += 1

            if wp["kind"] == "gun":
                ctx.events.emit(
                    SimEventType.GunFired,
                    fields=(fu.id, wid, tr.id, th.id, sol.pos, p_hit),
                    fire_unit_id=fu.id,
                    weapon_id=wid,
                    track_id=tr.id,
                    threat_id=th.id,
                )

            ic = Interceptor(
                pos=fu.pos,
                alt_m=0.0,
                fire_unit_id=fu.id,
                support_asset_id=0,
                launcher_index=ln_idx,
                weapon_id=wid,
                track_id=tr.id,
                threat_id=th.id,
                target_path_version=th.path_version,
                launch_sec=ctx.time_sec,
                intercept_sec=ctx.time_sec + sol.dt_sec,
                launch_pos=fu.pos,
                intercept_pos=sol.pos,
                intercept_alt_m=sol.alt_m,
                speed_mps=wp["speed_mps"],
                hit_prob=p_hit,
            )
            ctx.state.interceptors.add(ic)
            ctx.events.emit(
                SimEventType.InterceptorLaunched,
                fields=(ic.id, fu.id, wid, tr.id, th.id, ic.intercept_sec, sol.pos),
                interceptor_id=ic.id,
                fire_unit_id=fu.id,
                weapon_id=wid,
                track_id=tr.id,
                threat_id=th.id,
                intercept_sec=ic.intercept_sec,
                pos=sol.pos,
            )

            # Check ammo depletion across all launchers of wslot
            if wp["magazine"] is not None and not wslot.depleted_emitted:
                if all(l.destroyed or (l.rounds == 0 and l.reload_until_sec <= 0.0) for l in wslot.launchers):
                    wslot.depleted_emitted = True
                    ctx.events.emit(SimEventType.AmmoDepleted, fields=(fu.id, wid), unit_id=fu.id, weapon_id=wid)


class InterceptorSystem:
    """System 8: InterceptorSystem (03_engagement_impact_scoring.md §3.2)."""

    order = 8
    name = "InterceptorSystem"
    stream_name = "intercept"

    def initialize(self, ctx: Any) -> None:
        pass

    def execute(self, ctx: Any) -> None:
        alive = ctx.state.interceptors.alive_list()
        due: List[Interceptor] = []
        for ic in alive:
            th = ctx.state.threats.try_get(ic.threat_id)
            if th is None or th.phase == ThreatPhase.Arrived:
                ctx.events.emit(SimEventType.InterceptorExpired, fields=(ic.id, ic.threat_id), interceptor_id=ic.id)
                ctx.state.interceptors.remove(ic.id)
                continue
            if ic.intercept_sec <= ctx.time_sec + EPS:
                due.append(ic)
            else:
                # Interpolate position for visualization/state hash
                dt_tot = max(EPS, ic.intercept_sec - ic.launch_sec)
                frac = min(max((ctx.time_sec - ic.launch_sec) / dt_tot, 0.0), 1.0)
                ic.pos = Vec2.lerp(ic.launch_pos, ic.intercept_pos, frac)
                ic.alt_m = ic.intercept_alt_m * frac

        due.sort(key=lambda item: (item.intercept_sec, item.id))
        for ic in due:
            th = ctx.state.threats.try_get(ic.threat_id)
            if th is None or th.phase == ThreatPhase.Arrived:
                ctx.events.emit(SimEventType.InterceptorExpired, fields=(ic.id, ic.threat_id), interceptor_id=ic.id)
                ctx.state.interceptors.remove(ic.id)
                continue

            # Check mid-flight guidance loss if semi-active / fire-control radar turned off or destroyed
            fu = ctx.state.fire_units.try_get(ic.fire_unit_id) if ic.fire_unit_id > 0 else None
            lost_lock = False
            if fu is not None:
                udef = ctx.level.catalog.air_defense_units.get(fu.def_id or "", {})
                wdef = ctx.level.catalog.weapons.get(ic.weapon_id, {})
                if udef.get("fireControlRadar") is not None and wdef.get("kind") != "gun":
                    if fu.radar_destroyed or fu.emitter is None or not fu.emitter.on:
                        lost_lock = True

            hit = False if lost_lock else ctx.rng.chance(ic.hit_prob)
            ctx.state.interceptors.remove(ic.id)
            ctx.events.emit(
                SimEventType.InterceptResolved,
                at_sec=ic.intercept_sec,
                fields=(ic.id, ic.fire_unit_id, ic.weapon_id, th.id, hit, ic.intercept_pos),
                interceptor_id=ic.id,
                fire_unit_id=ic.fire_unit_id,
                weapon_id=ic.weapon_id,
                threat_id=th.id,
                hit=hit,
                pos=ic.intercept_pos,
            )
            if hit:
                ctx.state.scoring.hits_by_weapon[ic.weapon_id] = ctx.state.scoring.hits_by_weapon.get(ic.weapon_id, 0) + 1
                if fu is not None:
                    fu.kills_tonight += 1
                    if fu.emitter is not None and fu.emitter.after_firing == 1 and fu.pending_relocation_alt_id:
                        from .enemy_ai import DeploymentStage
                        DeploymentStage.trigger_after_firing_relocate(ctx, fu)
                self._on_threat_killed(ctx, th, ic.intercept_pos)

    @staticmethod
    def _on_threat_killed(ctx: Any, th: Threat, pos: Vec2) -> None:
        cat = ctx.level.catalog
        eid = th.def_id or ""
        ctx.state.scoring.kills_by_enemy[eid] = ctx.state.scoring.kills_by_enemy.get(eid, 0) + 1
        pot_loss = ScoringSystem.potential_loss_musd(ctx, th)
        ctx.state.scoring.enemy_destroyed_value_musd += pot_loss

        # Remove tracks targeting th.id
        for tr in ctx.state.tracks.alive_list():
            if tr.threat_id == th.id:
                ctx.events.emit(SimEventType.TrackLost, fields=(tr.id, th.id), track_id=tr.id)
                ctx.state.tracks.remove(tr.id)

        # Expire any remaining interceptors targeting th.id
        for other in ctx.state.interceptors.alive_list():
            if other.threat_id == th.id:
                ctx.events.emit(SimEventType.InterceptorExpired, fields=(other.id, th.id), interceptor_id=other.id)
                ctx.state.interceptors.remove(other.id)

        # Debris check if intercept_pos is inside urban polygon
        deb_rules = cat.rules.get("debris", {})
        if Geo.in_urban(ctx.level.urban_polygons, pos):
            dmg_frac = float(deb_rules.get("urbanInterceptDamageFraction", 0.3))
            if dmg_frac > 0.0:
                deb = Debris(pos=pos, alt_m=0.0)
                ctx.state.debris.add(deb)
                ctx.state.scoring.debris_count += 1
                ctx.state.scoring.debris_urban_hits += 1
                ctx.events.emit(SimEventType.DebrisFell, fields=(deb.id, th.id, pos, True), debris_id=deb.id, threat_id=th.id, pos=pos)

        ctx.state.threats.remove(th.id)


class ExternalSupportSystem:
    """System 9: ExternalSupportSystem (03_engagement_impact_scoring.md §3.3)."""

    order = 9
    name = "ExternalSupportSystem"
    stream_name = "support"

    def initialize(self, ctx: Any) -> None:
        sup = ctx.state.support
        base_sorties = int(ctx.level.meta.get("fighterSortiesPerNight", 0) or 0)
        sup.sorties_remaining = max(0, base_sorties + int(ctx.config.carry_in.fighter_sorties_delta))

    def execute(self, ctx: Any) -> None:
        cat = ctx.level.catalog
        for sa in ctx.state.support_assets.alive_list():
            if sa.state == 0 and ctx.time_sec >= sa.arrive_sec - EPS:
                sa.state = 1
                ctx.events.emit(SimEventType.SupportArrived, fields=(sa.id, sa.support_kind), support_asset_id=sa.id)
            if ctx.time_sec >= sa.end_sec - EPS:
                ctx.events.emit(SimEventType.SupportEnded, fields=(sa.id, sa.support_kind), support_asset_id=sa.id)
                ctx.state.support_assets.remove(sa.id)
                continue

            if sa.state == 1 and sa.support_kind == 0:  # Fighter patrol
                self._step_fighter(ctx, sa, cat)

    def _step_fighter(self, ctx: Any, sa: SupportAsset, cat: Any) -> None:
        if sa.pos is None or sa.ammo_remaining <= 0 or ctx.time_sec < sa.next_shot_sec - EPS:
            return
        wdef = cat.fighter_weapons.get(sa.weapon_id, {})
        range_m = float(wdef.get("rangeM", 15000.0))
        ceiling_m = float(wdef.get("ceilingM", 15000.0))
        speed_mps = float(wdef.get("interceptorSpeedMps", 900.0))
        ic_class = wdef.get("interceptClass", "fighter_aam")
        shot_interval = float(wdef.get("shotIntervalSec", 15.0))
        shot_cost = float(wdef.get("shotCostMusd", 0.4) or 0.0)
        allowed_tags = {parse_target_tag(t) for t in (wdef.get("targets") or [])}

        for tr in ctx.state.tracks.alive_list():
            if tr.threat_id <= 0 or tr.quality < TrackQuality.Approximate:
                continue
            th = ctx.state.threats.try_get(tr.threat_id)
            if th is None or th.phase == ThreatPhase.Arrived or th.pos is None:
                continue
            if th.tag not in allowed_tags:
                continue
            if sa.pos.distance_to(th.pos) > sa.radius_m + EPS:
                continue
            if any(ic.threat_id == th.id for ic in ctx.state.interceptors.alive_list()):
                continue
            sol = InterceptSolver.solve_threat(sa.pos, speed_mps, range_m, ceiling_m, th, ctx.time_sec)
            if sol is None:
                continue
            p_hit = WeaponParams.compute_hit_prob(ctx, None, ic_class, "missile", th, tr, sol.pos)
            if p_hit <= 0.0:
                continue

            sa.ammo_remaining -= 1
            sa.next_shot_sec = ctx.time_sec + shot_interval
            ctx.state.scoring.defense_cost_musd += shot_cost
            ctx.state.scoring.shots_fired_by_weapon[sa.weapon_id] = ctx.state.scoring.shots_fired_by_weapon.get(sa.weapon_id, 0) + 1
            ic = Interceptor(
                pos=sa.pos,
                alt_m=3000.0,
                fire_unit_id=0,
                support_asset_id=sa.id,
                launcher_index=0,
                weapon_id=sa.weapon_id,
                track_id=tr.id,
                threat_id=th.id,
                target_path_version=th.path_version,
                launch_sec=ctx.time_sec,
                intercept_sec=ctx.time_sec + sol.dt_sec,
                launch_pos=sa.pos,
                intercept_pos=sol.pos,
                intercept_alt_m=sol.alt_m,
                speed_mps=speed_mps,
                hit_prob=p_hit,
            )
            ctx.state.interceptors.add(ic)
            ctx.events.emit(
                SimEventType.InterceptorLaunched,
                fields=(ic.id, 0, sa.weapon_id, tr.id, th.id, ic.intercept_sec, sol.pos),
                interceptor_id=ic.id,
                support_asset_id=sa.id,
                weapon_id=sa.weapon_id,
                track_id=tr.id,
                threat_id=th.id,
                intercept_sec=ic.intercept_sec,
                pos=sol.pos,
            )
            break


class ImpactSystem:
    """System 10: ImpactSystem and Grid power propagation (03_engagement_impact_scoring.md §3.4)."""

    order = 10
    name = "ImpactSystem"
    stream_name = "impact"

    def initialize(self, ctx: Any) -> None:
        self.recompute_grid(ctx, emit_events=False)

    def execute(self, ctx: Any) -> None:
        arrived = [th for th in ctx.state.threats.alive_list() if th.phase == ThreatPhase.Arrived]
        arrived.sort(key=lambda t: t.id)
        for th in arrived:
            self._resolve_impact(ctx, th)
        if arrived:
            self.recompute_grid(ctx, emit_events=True)

    def _resolve_impact(self, ctx: Any, th: Threat) -> None:
        cat = ctx.level.catalog
        mdef = cat.munitions.get(th.def_id or "", {})
        acc_rules = cat.rules.get("accuracy", {})
        dmg_rules = cat.rules.get("damage", {})
        eid = th.def_id or ""
        ctx.state.scoring.leaks_by_enemy[eid] = ctx.state.scoring.leaks_by_enemy.get(eid, 0) + 1

        # Remove tracks & interceptors for th.id
        for tr in ctx.state.tracks.alive_list():
            if tr.threat_id == th.id:
                ctx.events.emit(SimEventType.TrackLost, fields=(tr.id, th.id), track_id=tr.id)
                ctx.state.tracks.remove(tr.id)
        for ic in ctx.state.interceptors.alive_list():
            if ic.threat_id == th.id:
                ctx.events.emit(SimEventType.InterceptorExpired, fields=(ic.id, th.id), interceptor_id=ic.id)
                ctx.state.interceptors.remove(ic.id)

        aim = th.target_pos
        tier_str = mdef.get("accuracy", "C")
        tiers_order = ["A", "B", "C", "D"]
        t_idx = tiers_order.index(tier_str) if tier_str in tiers_order else 2
        t_idx = min(3, t_idx + th.accuracy_tier_drop)
        eff_tier = tiers_order[t_idx]

        tiers_map = acc_rules.get("tiers", {})
        tier_obj = tiers_map.get(eff_tier, {"hitProb": 0.5, "missOffsetM": {"min": 100.0, "max": 500.0}})
        p_hit = float(tier_obj.get("hitProb", 0.5)) * th.arm_hit_prob_mult
        if th.accuracy_tier_drop > 0:
            p_hit *= 0.5 ** th.accuracy_tier_drop
        if th.ew_extra_offset_m > 0.0:
            p_hit *= 1000.0 / (1000.0 + th.ew_extra_offset_m)
        if th.target_unit_id > 0:
            p_hit *= EwQueries.shield_hit_prob_mult(ctx.state, cat, th.target_unit_id, eid)

        is_hit = ctx.rng.chance(p_hit)
        impact_pos = aim
        if not is_hit:
            off_cfg = tier_obj.get("missOffsetM", {"min": 100.0, "max": 500.0})
            if isinstance(off_cfg, dict):
                r_off = ctx.rng.next_float(float(off_cfg.get("min", 100.0)), float(off_cfg.get("max", 500.0)))
            else:
                r_off = float(off_cfg)
            r_off += th.ew_extra_offset_m
            angle = 2.0 * math.pi * ctx.rng.next_double()
            impact_pos = Vec2(aim.x + r_off * math.sin(angle), aim.y + r_off * math.cos(angle))

        dmg_level = int(mdef.get("damageLevel", 3) or 3)
        ctx.events.emit(
            SimEventType.ThreatImpacted,
            at_sec=th.arrived_at_sec if th.arrived_at_sec >= 0.0 else None,
            fields=(th.id, eid, is_hit, impact_pos, dmg_level),
            threat_id=th.id,
            def_id=eid,
            hit=is_hit,
            pos=impact_pos,
            damage_level=dmg_level,
        )

        if is_hit and dmg_level > 0:
            if th.target_kind == ThreatTargetKind.Structure and th.target_structure_id > 0:
                st = ctx.state.structures.try_get(th.target_structure_id)
                if st is not None and not st.destroyed:
                    self._damage_structure(ctx, st, dmg_level)
            elif (th.target_kind == ThreatTargetKind.PlayerUnit and th.target_unit_id > 0) or th.homing_unit_id > 0:
                uid = th.homing_unit_id if th.homing_unit_id > 0 else th.target_unit_id
                self._damage_player_unit(ctx, uid, dmg_level, dmg_rules)

        ctx.state.threats.remove(th.id)

    def _damage_structure(self, ctx: Any, st: Structure, dmg_level: int) -> None:
        if st.destroyed:
            return
        st.hp = max(0, st.hp - dmg_level)
        ctx.events.emit(SimEventType.StructureDamaged, fields=(st.id, st.def_id or "", st.hp, st.max_hp), structure_id=st.id, hp=st.hp)
        if st.hp <= 0:
            st.destroyed = True
            ctx.events.emit(SimEventType.StructureDestroyed, fields=(st.id, st.def_id or ""), structure_id=st.id)
            if st.grid_node_id > 0:
                gn = ctx.state.grid_nodes.try_get(st.grid_node_id)
                if gn is not None:
                    gn.destroyed = True

    def _damage_player_unit(self, ctx: Any, uid: int, dmg_level: int, dmg_rules: Dict[str, Any]) -> None:
        u: Optional[PlayerUnitEntity] = (
            ctx.state.fire_units.try_get(uid)
            or ctx.state.sensors.try_get(uid)
            or ctx.state.ew_units.try_get(uid)
            or ctx.state.deception_units.try_get(uid)
        )
        if u is None or u.pos is None:
            return
        # Prepared position survival bonus
        pos_rules = ctx.level.catalog.rules.get("positions", {})
        if getattr(u, "alternate_position_id", None) is None and not u.new_position_penalty:
            pass

        if dmg_level <= 2:
            u.light_damaged = True
            u.damage_efficiency_mult = 0.8
            ctx.events.emit(SimEventType.PlayerUnitDamaged, fields=(u.id, u.def_id or "", "light_damage"), unit_id=u.id)
        elif dmg_level <= 4:
            u.suspended_until_sec = max(u.suspended_until_sec, ctx.time_sec + 1800.0)
            ctx.events.emit(SimEventType.PlayerUnitDamaged, fields=(u.id, u.def_id or "", "heavy_damage"), unit_id=u.id)
        elif dmg_level <= 6 and isinstance(u, FireUnit):
            if ctx.rng.chance(float(dmg_rules.get("componentRadarChance", 0.5))):
                u.radar_destroyed = True
                if u.emitter is not None:
                    u.emitter.on = False
                ctx.events.emit(SimEventType.PlayerUnitDamaged, fields=(u.id, u.def_id or "", "radar_destroyed"), unit_id=u.id)
            else:
                u.launchers_lost += 1
                for wslot in u.weapons:
                    for ln in wslot.launchers:
                        if not ln.destroyed:
                            ln.destroyed = True
                            break
                ctx.events.emit(SimEventType.PlayerUnitDamaged, fields=(u.id, u.def_id or "", "launcher_destroyed"), unit_id=u.id)
        else:
            ctx.state.scoring.destroyed_unit_snapshots.append({"id": u.id, "def_id": u.def_id})
            ctx.events.emit(SimEventType.PlayerUnitDestroyed, fields=(u.id, u.def_id or ""), unit_id=u.id)
            for store in (ctx.state.fire_units, ctx.state.sensors, ctx.state.ew_units, ctx.state.deception_units):
                if store.try_get(u.id) is not None:
                    store.remove(u.id)

    @staticmethod
    def recompute_grid(ctx: Any, emit_events: bool = True) -> None:
        links = ctx.level.grid.get("links") or []
        adj: Dict[int, List[int]] = {}
        for gn in ctx.state.grid_nodes.alive_list():
            adj[gn.id] = []
        for lk in links:
            u_id = ctx.state.grid_node_id_by_def_id.get(lk.get("from", ""), 0)
            v_id = ctx.state.grid_node_id_by_def_id.get(lk.get("to", ""), 0)
            if u_id > 0 and v_id > 0:
                adj.setdefault(u_id, []).append(v_id)
                adj.setdefault(v_id, []).append(u_id)

        visited: set = set()
        queue: List[int] = []
        for gn in ctx.state.grid_nodes.alive_list():
            if not gn.destroyed and (gn.node_type == 0 or gn.off_map_supply):
                visited.add(gn.id)
                queue.append(gn.id)

        while queue:
            curr = queue.pop(0)
            for nb in adj.get(curr, []):
                gn_nb = ctx.state.grid_nodes.try_get(nb)
                if gn_nb is not None and not gn_nb.destroyed and nb not in visited:
                    visited.add(nb)
                    queue.append(nb)

        consumers = 0
        unpowered_consumers = 0
        for gn in ctx.state.grid_nodes.alive_list():
            was_pow = gn.powered
            gn.powered = (not gn.destroyed) and (gn.id in visited)
            if gn.node_type == 2:  # consumer
                consumers += 1
                if not gn.powered:
                    unpowered_consumers += 1
            if emit_events and gn.powered != was_pow:
                ctx.events.emit(SimEventType.GridPowerChanged, fields=(gn.id, gn.powered), grid_node_id=gn.id, powered=gn.powered)

        for st in ctx.state.structures.alive_list():
            if st.grid_node_id > 0:
                gn = ctx.state.grid_nodes.try_get(st.grid_node_id)
                st.powered = gn.powered if gn is not None else True

        for store in (ctx.state.fire_units, ctx.state.sensors, ctx.state.ew_units, ctx.state.deception_units):
            for u in store.alive_list():
                if u.grid_node_id > 0:
                    gn = ctx.state.grid_nodes.try_get(u.grid_node_id)
                    u.powered = gn.powered if gn is not None else True

        ctx.state.grid.unpowered_consumer_frac = (unpowered_consumers / consumers) if consumers > 0 else 0.0
        ctx.state.grid.collapsed = consumers > 0 and unpowered_consumers == consumers


class ScoringSystem:
    """System 13: ScoringSystem and night termination check (03_engagement_impact_scoring.md §3.5)."""

    order = 13
    name = "ScoringSystem"
    stream_name = "scoring"

    def initialize(self, ctx: Any) -> None:
        pass

    @staticmethod
    def potential_loss_musd(ctx: Any, th: Threat) -> float:
        cat = ctx.level.catalog
        civ_rules = cat.rules.get("civil", {}).get("scoring", {})
        loss_base = float(civ_rules.get("lossMusdBase", 0.1))
        if th.kind == ThreatKind.Platform:
            pdef = cat.platforms.get(th.def_id or "", {})
            return float(pdef.get("costMusd") or civ_rules.get("platformPotentialLossMusd", 10.0))
        mdef = cat.munitions.get(th.def_id or "", {})
        cost = float(mdef.get("costMusd") or 0.0)
        dmg_lvl = int(mdef.get("damageLevel") or 0)
        if dmg_lvl <= 0:
            return cost
        w = 1.0
        if th.target_structure_id > 0:
            st = ctx.state.structures.try_get_including_removed(th.target_structure_id)
            if st is not None:
                w = st.weight
        sub_cnt = int((mdef.get("submunitions") or {}).get("count", 1) or 1)
        struct_loss = sub_cnt * (2 ** (dmg_lvl - 1)) * loss_base * w
        return max(cost, struct_loss)

    def execute(self, ctx: Any) -> None:
        # 1. Step civil alert state
        civ = ctx.state.civil
        if civ.alert_on:
            civ.total_alert_sec += ctx.step_sec
            shelter_sec = float(ctx.level.catalog.rules.get("civil", {}).get("alert", {}).get("shelterSec", 120.0))
            if shelter_sec > 0.0:
                civ.sheltered_frac = min(1.0, civ.sheltered_frac + ctx.step_sec / shelter_sec)
            if ctx.state.threats. count_alive() == 0:
                civ.false_alarm_sec += ctx.step_sec
        else:
            civ.sheltered_frac = max(0.0, civ.sheltered_frac - ctx.step_sec / 120.0)

        # 2. Compute weighted structure loss fraction
        tot_w = 0.0
        lost_w = 0.0
        for st in ctx.state.structures.alive_list():
            tot_w += st.weight
            if st.max_hp > 0:
                lost_w += st.weight * ((st.max_hp - st.hp) / st.max_hp)
        ctx.state.scoring.weighted_loss_frac = (lost_w / tot_w) if tot_w > 0.0 else 0.0

        # 3. Check defeat conditions
        for df in ctx.level.meta.get("defeat") or []:
            dtype = df.get("type")
            if dtype == "weighted_damage_at_least":
                frac = float(df.get("fraction", 0.5))
                if ctx.state.scoring.weighted_loss_frac >= frac - EPS:
                    ctx.state.request_end(NightOutcome.Defeated, NightEndReason.DefeatCondition, "weighted_damage_at_least")
                    return
            elif dtype == "grid_collapse":
                if ctx.state.grid.collapsed:
                    ctx.state.request_end(NightOutcome.Defeated, NightEndReason.DefeatCondition, "grid_collapse")
                    return
            elif dtype == "structure_destroyed":
                sid = ctx.state.structure_id_by_def_id.get(df.get("structure", ""), 0)
                st_obj = ctx.state.structures.try_get_including_removed(sid) if sid > 0 else None
                if st_obj is not None and st_obj.destroyed:
                    ctx.state.request_end(NightOutcome.Defeated, NightEndReason.DefeatCondition, f"structure_destroyed:{df.get('structure')}")
                    return

        # 4. Check normal end conditions
        if (
            ctx.config.end_when_clear
            and ctx.state.waves.all_waves_spawned
            and len(ctx.state.enemy_intel.held_waves) == 0
            and len(ctx.state.commands.scheduled_spawns) == 0
            and ctx.state.threats.count_alive() == 0
            and ctx.state.interceptors.count_alive() == 0
        ):
            ctx.state.request_end(NightOutcome.Survived, NightEndReason.AllClear, "all_clear")
            return

        dur_ticks = ctx.config.duration_ticks_override or ctx.duration_ticks
        if ctx.tick >= dur_ticks:
            ctx.state.request_end(NightOutcome.Survived, NightEndReason.DurationElapsed, "duration_elapsed")

    @staticmethod
    def build_result(ctx: Any, seed_str: str) -> NightResult:
        st = ctx.state
        end_req = st.end_request or EndRequest(NightOutcome.Survived, NightEndReason.DurationElapsed)
        h_val = st.compute_hash()
        ratio = (
            st.scoring.enemy_destroyed_value_musd / st.scoring.defense_cost_musd
            if st.scoring.defense_cost_musd > EPS
            else None
        )
        return NightResult(
            level_id=ctx.level.id,
            night_index=ctx.config.night_index,
            seed=seed_str,
            data_hash=ctx.level.data_hash,
            outcome=end_req.outcome,
            end_reason=end_req.reason,
            end_tick=st.tick,
            end_time_sec=st.tick * ctx.step_sec,
            final_state_hash=f"{h_val:016x}",
            losses={
                "weightedStructureLossFrac": st.scoring.weighted_loss_frac,
                "structures": [
                    {"id": s.def_id, "hp": s.hp, "maxHp": s.max_hp, "destroyed": s.destroyed}
                    for s in st.structures.alive_list()
                ],
                "unitsDestroyed": list(st.scoring.destroyed_unit_snapshots),
            },
            ammo={
                "shotsFiredByWeapon": dict(sorted(st.scoring.shots_fired_by_weapon.items())),
                "hitsByWeapon": dict(sorted(st.scoring.hits_by_weapon.items())),
                "defenseCostMusd": st.scoring.defense_cost_musd,
            },
            exchange={
                "enemyDestroyedValueMusd": st.scoring.enemy_destroyed_value_musd,
                "defenseCostMusd": st.scoring.defense_cost_musd,
                "exchangeRatio": ratio,
                "killsByEnemy": dict(sorted(st.scoring.kills_by_enemy.items())),
                "leaksByEnemy": dict(sorted(st.scoring.leaks_by_enemy.items())),
                "threatsEwDowned": st.scoring.threats_ew_downed,
            },
            debris={
                "debrisCount": st.scoring.debris_count,
                "debrisUrbanHits": st.scoring.debris_urban_hits,
            },
            exposure={
                "units": [
                    {"id": u.id, "defId": u.def_id, "exposure": u.exposure, "peak": u.exposure_peak}
                    for store in (st.fire_units, st.sensors, st.ew_units, st.deception_units)
                    for u in store.alive_list()
                    if not getattr(u, "automatic", False)
                ]
            },
            civil={
                "totalAlertSec": st.civil.total_alert_sec,
                "falseAlarmSec": st.civil.false_alarm_sec,
                "responsiveness": st.civil.responsiveness,
                "gridCollapsed": st.grid.collapsed,
                "unpoweredConsumerFrac": st.grid.unpowered_consumer_frac,
            },
            support={
                "sortiesUsed": st.support.sorties_used,
                "sortiesRemaining": st.support.sorties_remaining,
                "supportCallsTonight": dict(sorted(st.support.support_calls_tonight.items())),
            },
            commands={
                "commandPointsInitial": st.commands.command_points_initial,
                "commandPointsRemaining": st.commands.command_points,
                "commandPointsSpent": st.commands.command_points_spent,
                "relocationsCompleted": st.commands.relocations_completed,
                "choicesTriggered": st.commands.choices_triggered,
                "choicesTimedOut": st.commands.choices_timed_out,
            },
            carry_out=ScoringSystem.build_carry_out_dict(ctx),
        )

    @staticmethod
    def build_carry_out_dict(ctx: Any) -> Dict[str, Any]:
        st = ctx.state
        units_out: List[Dict[str, Any]] = []
        for store in (st.fire_units, st.sensors, st.ew_units, st.deception_units):
            for u in store.alive_list():
                if getattr(u, "automatic", False):
                    continue
                u_entry: Dict[str, Any] = {
                    "rosterId": u.roster_id,
                    "unitDefId": u.def_id,
                    "pos": [u.pos.x, u.pos.y] if u.pos else [0.0, 0.0],
                    "exposure": u.exposure,
                    "lightDamaged": u.light_damaged,
                    "radarDestroyed": getattr(u, "radar_destroyed", False),
                    "launchersLost": getattr(u, "launchers_lost", 0),
                    "crewConsecutiveNights": getattr(u, "crew_consecutive_nights", 1) + 1,
                }
                units_out.append(u_entry)

        known_out: List[Dict[str, Any]] = []
        for kt in st.enemy_intel.known_targets:
            known_out.append(
                {
                    "unitId": kt.unit_id,
                    "rosterId": kt.roster_id,
                    "unitDefId": kt.unit_def_id,
                    "kind": kt.kind,
                    "reason": kt.reason,
                    "pos": [kt.pos.x, kt.pos.y],
                    "exposure": kt.exposure,
                }
            )
        # Also add units whose peak exposure >= 70 tonight
        existing_pos = [(kt.pos, kt.unit_def_id) for kt in st.enemy_intel.known_targets]
        for store, kind_int in (
            (st.fire_units, 1),
            (st.sensors, 3),
            (st.ew_units, 2),
            (st.deception_units, 0),
        ):
            for u in store.alive_list():
                if getattr(u, "automatic", False) or u.pos is None:
                    continue
                if u.exposure >= 70.0 or u.exposure_peak >= 70.0:
                    if not any(p.distance_to(u.pos) <= 500.0 for p, _ in existing_pos):
                        known_out.append(
                            {
                                "unitId": u.id,
                                "rosterId": u.roster_id,
                                "unitDefId": u.def_id or "",
                                "kind": kind_int,
                                "reason": 3,  # CarryIn
                                "pos": [u.pos.x, u.pos.y],
                                "exposure": u.exposure,
                            }
                        )

        return {
            "units": units_out,
            "structures": [
                {"id": s.def_id, "hp": s.hp, "destroyed": s.destroyed}
                for s in st.structures.alive_list()
            ],
            "ammoPool": dict(sorted(st.engagement.ammo_pool.items())),
            "perLevelUsed": dict(sorted(st.engagement.per_level_used.items())),
            "alertResponsiveness": st.civil.responsiveness,
            "knownTargets": known_out,
        }
