"""Sensing, track fusion, electronic warfare, emission control, and exposure systems (02_sensing_tracks_ew_emission.md)."""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from .core import Geo, SimTime, Vec2
from .entities import (
    CommandRejectReason,
    DeceptionUnit,
    DelayedDetection,
    EmitterControl,
    EntityKind,
    EwUnit,
    FireUnit,
    PlayerUnitCategory,
    PlayerUnitEntity,
    RawDetection,
    SensorUnit,
    SimCommand,
    SimCommandType,
    SimEventType,
    SimState,
    TargetTag,
    Threat,
    ThreatKind,
    ThreatPhase,
    Track,
    TrackQuality,
    UnitDeployState,
)
from .movement import ThreatRouting, parse_target_tag

_QUALITY_MAP = {
    "vague": TrackQuality.Vague,
    "approximate": TrackQuality.Approximate,
    "precise": TrackQuality.Precise,
}

_LOW_ALT_CAP_ORDER = {"none": 0, "poor": 1, "medium": 2, "good": 3}


class EnvironmentResolver:
    @staticmethod
    def season_for(night: Dict[str, Any], date_str: str) -> str:
        if night.get("season"):
            return str(night["season"])
        parts = date_str.split("-")
        month = int(parts[1]) if len(parts) >= 2 else 11
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "autumn"


class SensingMath:
    @staticmethod
    def time_to_enter_radius(p: Vec2, v: Vec2, c: Vec2, r: float) -> Optional[float]:
        return Geo.first_entry_into_circle(p, v, c, r)


class FireControlQueries:
    @staticmethod
    def cued(track: Track, track_rules: Dict[str, Any]) -> bool:
        min_q_str = track_rules.get("cueing", {}).get("cued", {}).get("minTrackQuality", "approximate")
        min_q = _QUALITY_MAP.get(min_q_str, TrackQuality.Approximate)
        net_q = getattr(track, "network_quality", None)
        return net_q is not None and net_q >= min_q

    @staticmethod
    def has_fire_control_radar(f: FireUnit, catalog: Any) -> bool:
        udef = catalog.air_defense_units.get(f.def_id or "", {})
        return udef.get("fireControlRadar") is not None

    @staticmethod
    def reaction_mult(f: FireUnit, emission_rules: Dict[str, Any]) -> float:
        if f.emitter is None:
            return 1.0
        for st in emission_rules.get("strategies", []):
            if st["id"] == f.emitter.policy_id:
                return float(st.get("reactionTimeMult", 1.0))
        return 1.0

    @staticmethod
    def silent_hold(f: FireUnit, time_sec: float) -> bool:
        return (
            f.emitter is not None
            and not f.emitter.on
            and f.deploy_state == UnitDeployState.Deployed
            and not f.radar_destroyed
            and f.suspended_until_sec <= time_sec + 1e-9
        )


@dataclass(frozen=True)
class ActiveEmitter:
    unit_id: int
    entity_kind: EntityKind
    pos: Vec2
    exposure: float
    is_decoy: bool


class EmitterQueries:
    @staticmethod
    def list_active(state: SimState) -> List[ActiveEmitter]:
        out: List[ActiveEmitter] = []
        for store, kind, is_dec in (
            (state.fire_units, EntityKind.FireUnit, False),
            (state.sensors, EntityKind.SensorUnit, False),
            (state.ew_units, EntityKind.EwUnit, False),
            (state.deception_units, EntityKind.DeceptionUnit, True),
        ):
            for u in store.alive_list():
                if u.emitter is not None and u.emitter.on and u.pos is not None:
                    out.append(ActiveEmitter(u.id, kind, u.pos, u.exposure, is_dec))
        return out


class EwQueries:
    @staticmethod
    def shield_hit_prob_mult(state: SimState, catalog: Any, target_unit_id: int, threat_def_id: str) -> float:
        m_def = catalog.munitions.get(threat_def_id, {})
        if m_def.get("ewImmune"):
            return 1.0
        u = (
            state.fire_units.try_get(target_unit_id)
            or state.sensors.try_get(target_unit_id)
            or state.ew_units.try_get(target_unit_id)
            or state.deception_units.try_get(target_unit_id)
        )
        if u is None or u.deploy_state == UnitDeployState.Packed:
            return 1.0
        for eq_id in u.equipment_ew_ids:
            eq_def = catalog.ew_units.get(eq_id, {})
            if eq_def.get("effect") == "self_protection" and threat_def_id in (eq_def.get("effectiveAgainst") or []):
                hit_mult = float(eq_def.get("hitProbMult", 0.5))
                eff = float(catalog.rules.get("ew", {}).get("effectiveness", {}).get("counterUas", 1.0))
                return 1.0 - (1.0 - hit_mult) * eff
        return 1.0

    @staticmethod
    def is_in_friendly_ew_zone(state: SimState, catalog: Any, pos: Vec2, time_sec: float = 0.0) -> bool:
        for u in state.ew_units.alive_list():
            if u.deploy_state != UnitDeployState.Deployed or u.suspended_until_sec > time_sec + 1e-9:
                continue
            if u.emitter is None or not u.emitter.on or u.pos is None:
                continue
            edef = catalog.ew_units.get(u.def_id or "", {})
            if edef.get("effect") in ("nav_jam", "nav_spoof", "link_cut", "link_cut_directional"):
                rad_m = float(edef.get("radiusM", 0.0) or 0.0)
                if u.pos.distance_to(pos) <= rad_m + 1e-9:
                    return True
        return False


class EmissionChoiceEffects:
    @staticmethod
    def apply_arm_choice(state: SimState, unit_id: int, silence: bool) -> None:
        u = (
            state.fire_units.try_get(unit_id)
            or state.sensors.try_get(unit_id)
            or state.ew_units.try_get(unit_id)
            or state.deception_units.try_get(unit_id)
        )
        if u is None or u.emitter is None:
            return
        setattr(u.emitter, "arm_silenced", silence)
        setattr(u.emitter, "arm_pending", False)


class EmissionPolicyRules:
    @staticmethod
    def check_available(unit_def_id: str, strategy: Dict[str, Any], level: Any) -> Optional[CommandRejectReason]:
        cat = level.catalog
        act = strategy.get("activation", "")
        if act == "last_moment":
            ad = cat.air_defense_units.get(unit_def_id)
            if ad is None or ad.get("fireControlRadar") is None:
                return CommandRejectReason.WrongEntityKind
        if strategy.get("westernSystemsOnly"):
            ad = cat.air_defense_units.get(unit_def_id)
            if ad is None or (ad.get("fireControlRadar") or {}).get("origin") != "western":
                return CommandRejectReason.NotAvailable
        avail_lvl = strategy.get("availableFromLevel")
        meta_num = level.meta.get("number")
        if avail_lvl is not None and meta_num is not None and int(meta_num) < int(avail_lvl):
            return CommandRejectReason.NotAvailable
        return None


class SensorSystem:
    """System 3: SensorSystem (02_sensing_tracks_ew_emission.md §3.2)."""

    order = 3
    name = "SensorSystem"
    stream_name = "sensor"

    def initialize(self, ctx: Any) -> None:
        cat = ctx.level.catalog
        def_policy = cat.rules.get("emission", {}).get("defaultStrategy", "continuous")
        # Create automatic sensors (national warning net, civil reports)
        for s_id, s_def in cat.sensors.items():
            if s_def.get("automatic"):
                su = SensorUnit(
                    def_id=s_id,
                    pos=Vec2(0.0, 0.0),
                    alt_m=0.0,
                    deploy_state=UnitDeployState.Deployed,
                    automatic=True,
                    emitter=None,
                )
                ctx.state.sensors.add(su)

        # Initialize emitters and HorizonProfiles on all placed units
        for store, tbl_name in (
            (ctx.state.fire_units, "air_defense_units"),
            (ctx.state.sensors, "sensors"),
            (ctx.state.ew_units, "ew_units"),
            (ctx.state.deception_units, "deception_units"),
        ):
            tbl = getattr(cat, tbl_name)
            for u in store.alive_list():
                udef = tbl.get(u.def_id or "", {})
                is_emitter = False
                if tbl_name == "air_defense_units":
                    is_emitter = udef.get("fireControlRadar") is not None
                elif tbl_name == "sensors":
                    is_emitter = udef.get("emission") == "active" and not u.automatic
                elif tbl_name == "ew_units":
                    is_emitter = udef.get("effect") != "self_protection"
                elif tbl_name == "deception_units":
                    is_emitter = udef.get("effect") in ("fake_emitter", "sacrificial_emitter")

                if is_emitter and u.emitter is None:
                    settings = (u.placement.settings if u.placement else {}) or {}
                    pol = settings.get("emissionPolicyId") or def_policy
                    u.emitter = EmitterControl(
                        policy_id=pol,
                        on=pol in ("continuous", "blink"),
                        duty_on_sec=float(settings.get("dutyOnSec", 60.0) or 60.0),
                        duty_off_sec=float(settings.get("dutyOffSec", 60.0) or 60.0),
                        on_arm_incoming=int(settings.get("onArmIncoming", 0) or 0),
                        after_firing=int(settings.get("afterFiring", 0) or 0),
                        neighbor_takeover=bool(settings.get("neighborTakeover", False)),
                    )
                    setattr(u.emitter, "on_since_tick", 0 if u.emitter.on else -1)
                    setattr(u.emitter, "arm_silenced", False)
                    setattr(u.emitter, "arm_pending", False)
                    setattr(u.emitter, "takeover_active", False)
                    setattr(u.emitter, "fired_since_relocation", False)
                    setattr(u.emitter, "last_shot_tick", -1)

                self._rebuild_horizon_for_unit(ctx, u)

        # Precompute early warning schedule
        self._warning_schedule: List[Tuple[int, str, str, float, float, bool]] = []
        night = self._get_night(ctx)
        w_cx = float(ctx.level.meta.get("map", {}).get("widthM", 20000.0)) * 0.5
        w_cy = float(ctx.level.meta.get("map", {}).get("heightM", 20000.0)) * 0.5
        center = Vec2(w_cx, w_cy)
        for wi, w in enumerate(night.get("waves", [])):
            # Skip story-only waves in static schedule
            from .movement import WaveSpawnRules
            if WaveSpawnRules.is_story_only_wave(ctx.level, w["id"]):
                continue
            seen_entries: List[str] = []
            for g in w.get("groups", []):
                ep_id = g["entry"]
                if ep_id not in seen_entries:
                    seen_entries.append(ep_id)
            for ep_id in seen_entries:
                ep = ctx.level.entry_points_by_id.get(ep_id, {})
                warn_sec = ep.get("warningSec")
                if warn_sec is None:
                    continue
                at_sec = float(w.get("atSec", 0.0))
                warn_tick = max(1, SimTime.sec_to_ticks_floor(max(0.0, at_sec - float(warn_sec)), ctx.step_sec))
                ep_pos: Vec2 = ep["pos"]
                bearing = Geo.bearing_rad(center, ep_pos)
                is_bm = False
                for g in w.get("groups", []):
                    if g["entry"] == ep_id:
                        en_def = cat.munitions.get(g["enemy"]) or cat.platforms.get(g["enemy"]) or {}
                        if en_def.get("tag") in ("BM", "HBM"):
                            is_bm = True
                self._warning_schedule.append((warn_tick, w["id"], ep_id, at_sec, bearing, is_bm))
        self._warning_schedule.sort(key=lambda item: item[0])

    def _get_night(self, ctx: Any) -> Dict[str, Any]:
        for n in ctx.level.waves.get("nights", []):
            if n.get("night") == ctx.config.night_index:
                return n
        return ctx.level.waves["nights"][0]

    def _rebuild_horizon_for_unit(self, ctx: Any, u: PlayerUnitEntity) -> None:
        if u.pos is None:
            return
        cat = ctx.level.catalog
        def_ant = float(cat.rules.get("terrain", {}).get("defaultAntennaHeightM", 10.0))
        ex = ctx.terrain.extent_x_m
        ey = ctx.terrain.extent_y_m
        max_map_r = math.sqrt(ex * ex + ey * ey) * 1.25
        if isinstance(u, SensorUnit) and not u.automatic:
            sdef = cat.sensors.get(u.def_id or "", {})
            r_m = sdef.get("detectionRangeM")
            if r_m is not None and sdef.get("lineOfSight", True) is not False and sdef.get("layer") != "national":
                ant = float(sdef.get("antennaHeightM") if sdef.get("antennaHeightM") is not None else def_ant)
                u.horizon_profile = ctx.terrain.build_horizon_profile(u.pos, ant, min(float(r_m) * 1.5, max_map_r))
        elif isinstance(u, FireUnit):
            fdef = cat.air_defense_units.get(u.def_id or "", {})
            fcr = fdef.get("fireControlRadar")
            if fcr is not None:
                ant = float(fcr.get("antennaHeightM") if fcr.get("antennaHeightM") is not None else def_ant)
                r_m = float(fcr.get("rangeM", 10000.0))
                setattr(u, "horizon_profile", ctx.terrain.build_horizon_profile(u.pos, ant, min(r_m, max_map_r)))
            elif fdef.get("selfAcquisitionRangeM") is not None:
                r_m = float(fdef["selfAcquisitionRangeM"])
                setattr(u, "horizon_profile", ctx.terrain.build_horizon_profile(u.pos, def_ant, min(r_m * 1.5, max_map_r)))

    def _sensor_active(self, s: SensorUnit, now_sec: float) -> bool:
        if s.deploy_state != UnitDeployState.Deployed:
            return False
        if s.suspended_until_sec > now_sec + 1e-9:
            return False
        return s.emitter is None or s.emitter.on

    def _b_line_applies(self, ctx: Any, sdef: Dict[str, Any]) -> bool:
        return ctx.level.meta.get("protagonist") == "B" and sdef.get("layer") == "regional"

    def _effective_sensor_range(
        self, ctx: Any, s: SensorUnit, sdef: Dict[str, Any], night: Dict[str, Any], season: str, alt_m: Optional[float]
    ) -> float:
        det_rules = ctx.level.catalog.rules.get("tracks", {}).get("detectionRules", {})
        pos_rules = ctx.level.catalog.rules.get("positions", {})
        r = float(sdef.get("detectionRangeM", 0.0))
        if sdef.get("nightRangeMult") is not None:
            tod = night.get("timeOfDay", "night")
            negated = False
            neg_by = set(sdef.get("nightPenaltyNegatedBy") or [])
            settings = (s.placement.settings if s.placement else {}) or {}
            aids = set(settings.get("nightAids") or [])
            if tod == "day" or bool(aids & neg_by):
                night_mult = 1.0
            else:
                night_mult = float(sdef["nightRangeMult"])
            weather = night.get("weather")
            w_map = det_rules.get("opticalWeatherRangeMult", {"clear": 1.0, "moonlit": 1.5, "low_cloud": 0.6, "fog": 0.25})
            w_mult = 1.0 if weather is None else float(w_map.get(weather, 1.0))
            r = r * night_mult * w_mult
        if s.emitter is not None and not s.powered:
            r = r * float(det_rules.get("unpoweredActiveRangeMult", 0.5))
        if s.emitter is not None and season == "winter":
            r = r * float(det_rules.get("winterActiveRangeMult", 0.9))
        if s.new_position_penalty:
            r = r * float(pos_rules.get("newUnsurveyed", {}).get("firstNightEfficiencyMult", 0.7))
        if alt_m is not None:
            low_below = float(det_rules.get("lowAltitudeBelowM", 200.0))
            if alt_m < low_below:
                low_cap = sdef.get("lowAltitude", "medium")
                low_map = det_rules.get("lowAltitudeRangeMult", {"none": 0.0, "poor": 0.25, "medium": 0.5, "good": 0.75})
                r = r * float(low_map.get(low_cap, 0.5))
                if sdef.get("largeLowAltitudeBlindZone"):
                    r = r * float(det_rules.get("largeBlindZoneLowAltitudeRangeMult", 0.5))
        return r

    def execute(self, ctx: Any) -> None:
        ctx.state.sensing.detections.clear()
        night = self._get_night(ctx)
        season = EnvironmentResolver.season_for(night, ctx.level.date)
        det_rules = ctx.level.catalog.rules.get("tracks", {}).get("detectionRules", {})
        b_line_rules = ctx.level.catalog.rules.get("tracks", {}).get("bLine", {})
        err_map = det_rules.get("errorRadiusM", {"vague": 3000.0, "approximate": 800.0, "precise": 50.0})

        # 1. Early warnings
        self._emit_early_warnings(ctx, night)

        # 2. Sensor units
        for s in ctx.state.sensors.alive_list():
            if not self._sensor_active(s, ctx.time_sec):
                continue
            sdef = ctx.level.catalog.sensors.get(s.def_id or "", {})
            if sdef.get("coverage") is not None:
                self._coverage_detect(ctx, s, sdef, det_rules, b_line_rules, err_map)
            elif sdef.get("detectionRangeM") is not None:
                self._range_detect(ctx, s, sdef, night, season, det_rules, b_line_rules, err_map)

        # 3. Fire units (fire control radar or self-acquisition)
        for f in ctx.state.fire_units.alive_list():
            self._fire_control_detect(ctx, f, night, season, det_rules, err_map)

        # 4. False alarms
        self._false_alarms(ctx, night, season, det_rules, b_line_rules, err_map)

        # 5. Deliver delayed detections
        due = [d for d in ctx.state.sensing.delayed if d.due_tick <= ctx.tick]
        ctx.state.sensing.delayed = [d for d in ctx.state.sensing.delayed if d.due_tick > ctx.tick]
        for d in due:
            ctx.state.sensing.detections.append(d.detection)

    def _emit_early_warnings(self, ctx: Any, night: Dict[str, Any]) -> None:
        for tick, wid, eid, exp_sec, brg, is_bm in self._warning_schedule:
            if tick <= ctx.tick:
                key = f"{wid}|{eid}"
                if key not in ctx.state.sensing.emitted_early_warnings:
                    ctx.state.sensing.emitted_early_warnings.append(key)
                    ctx.events.emit(
                        SimEventType.EarlyWarning,
                        fields=(wid, eid, exp_sec, brg, is_bm),
                        wave_id=wid,
                        entry_id=eid,
                        expected_at_sec=exp_sec,
                        bearing_rad=brg,
                        ballistic=is_bm,
                    )
        # Injected waves zero-lead warning
        w_cx = float(ctx.level.meta.get("map", {}).get("widthM", 20000.0)) * 0.5
        w_cy = float(ctx.level.meta.get("map", {}).get("heightM", 20000.0)) * 0.5
        center = Vec2(w_cx, w_cy)
        for ev in list(ctx.events.current_step):
            if ev.type == SimEventType.WaveStarted:
                wid = ev.data.get("wave_id", "")
                for w in night.get("waves", []):
                    if w["id"] == wid:
                        for g in w.get("groups", []):
                            eid = g["entry"]
                            ep = ctx.level.entry_points_by_id.get(eid, {})
                            if ep.get("warningSec") is not None:
                                key = f"{wid}|{eid}"
                                if key not in ctx.state.sensing.emitted_early_warnings:
                                    ctx.state.sensing.emitted_early_warnings.append(key)
                                    brg = Geo.bearing_rad(center, ep["pos"])
                                    en_def = ctx.level.catalog.munitions.get(g["enemy"]) or ctx.level.catalog.platforms.get(g["enemy"]) or {}
                                    is_bm = en_def.get("tag") in ("BM", "HBM")
                                    ctx.events.emit(
                                        SimEventType.EarlyWarning,
                                        fields=(wid, eid, ctx.time_sec, brg, is_bm),
                                        wave_id=wid,
                                        entry_id=eid,
                                        expected_at_sec=ctx.time_sec,
                                        bearing_rad=brg,
                                        ballistic=is_bm,
                                    )

    def _route_detection(self, ctx: Any, det: RawDetection, delay_sec: float) -> None:
        if delay_sec <= 0.0:
            ctx.state.sensing.detections.append(det)
        else:
            deliv_tick = ctx.tick + SimTime.sec_to_ticks_ceil(delay_sec, ctx.step_sec)
            ctx.state.sensing.delayed.append(DelayedDetection(due_tick=deliv_tick, detection=det))

    def _range_detect(
        self,
        ctx: Any,
        s: SensorUnit,
        sdef: Dict[str, Any],
        night: Dict[str, Any],
        season: str,
        det_rules: Dict[str, Any],
        b_line_rules: Dict[str, Any],
        err_map: Dict[str, Any],
    ) -> None:
        if s.pos is None:
            return
        r0 = self._effective_sensor_range(ctx, s, sdef, night, season, alt_m=None)
        cand_ids = ctx.threat_grid.query_circle(s.pos, r0)
        for tid in cand_ids:
            t = ctx.state.threats.try_get(tid)
            if t is None or t.pos is None or t.phase == ThreatPhase.Arrived:
                continue
            t_def = ctx.level.catalog.munitions.get(t.def_id or "") or ctx.level.catalog.platforms.get(t.def_id or "") or {}
            if sdef.get("onlyDetects") == "radio_linked_drones" and not t_def.get("radioLinked"):
                continue
            r = self._effective_sensor_range(ctx, s, sdef, night, season, alt_m=t.alt_m)
            if s.pos.distance_to(t.pos) > r + 1e-9:
                continue
            if sdef.get("lineOfSight", True) is not False and sdef.get("layer") != "national":
                hp = getattr(s, "horizon_profile", None)
                if hp is not None:
                    if not hp.has_line_of_sight_agl(t.pos, t.alt_m or 0.0):
                        continue
                else:
                    ant = float(sdef.get("antennaHeightM") or ctx.terrain.default_antenna_height_m)
                    if not ctx.terrain.has_line_of_sight_agl(s.pos, ant, t.pos, t.alt_m or 0.0):
                        continue
            q = _QUALITY_MAP.get(sdef.get("trackQuality", "vague"), TrackQuality.Vague)
            for upg in sdef.get("trackQualityUpgrades") or []:
                cond = upg.get("when")
                to_q = _QUALITY_MAP.get(upg.get("to", "approximate"), TrackQuality.Approximate)
                if cond == "close_range":
                    cf = float(det_rules.get("closeRangeFraction", 0.5))
                    if s.pos.distance_to(t.pos) <= r * cf + 1e-9:
                        q = max(q, to_q)
                elif cond == "linked_drone_types":
                    if t.def_id in (upg.get("enemies") or []):
                        q = max(q, to_q)
            q = min(q, TrackQuality.Approximate)
            b_applies = self._b_line_applies(ctx, sdef)
            if b_applies:
                b_max_q = _QUALITY_MAP.get(b_line_rules.get("maxTrackQuality", "approximate"), TrackQuality.Approximate)
                q = min(q, b_max_q)
            q_key = q.name.lower()
            err = float(err_map.get(q_key, 800.0)) * (float(det_rules.get("fastUpdateErrorRadiusMult", 0.5)) if sdef.get("fastUpdate") else 1.0)
            delay = max(
                float(det_rules.get("reportDelaySec", 0.0)) if sdef.get("reportDelay") else 0.0,
                float(b_line_rules.get("relayDelaySec", 0.0)) if b_applies else 0.0,
            )
            det = RawDetection(
                source_id=s.id,
                source_kind=0,
                threat_id=t.id,
                phantom_key=0,
                quality=q,
                pos=t.pos,
                vel_mps=t.vel_mps,
                tag=t.tag,
                can_cue=(sdef.get("layer") == "local"),
                uncertainty_radius_m=err,
            )
            self._route_detection(ctx, det, delay)

    def _coverage_detect(
        self,
        ctx: Any,
        s: SensorUnit,
        sdef: Dict[str, Any],
        det_rules: Dict[str, Any],
        b_line_rules: Dict[str, Any],
        err_map: Dict[str, Any],
    ) -> None:
        cov = sdef.get("coverage")
        low_below = float(det_rules.get("lowAltitudeBelowM", 200.0))
        min_cap = _LOW_ALT_CAP_ORDER.get(det_rules.get("coverageLowAltitudeMinCapability", "medium"), 2)
        s_cap = _LOW_ALT_CAP_ORDER.get(sdef.get("lowAltitude", "medium"), 2)
        for t in ctx.state.threats.alive_list():
            if t.pos is None or t.phase == ThreatPhase.Arrived:
                continue
            if (t.alt_m or 0.0) < low_below and s_cap < min_cap:
                continue
            if cov == "urban_areas" and not Geo.in_urban(ctx.level.urban_polygons, t.pos):
                continue
            t_def = ctx.level.catalog.munitions.get(t.def_id or "") or ctx.level.catalog.platforms.get(t.def_id or "") or {}
            if sdef.get("onlyDetects") == "radio_linked_drones" and not t_def.get("radioLinked"):
                continue
            q = _QUALITY_MAP.get(sdef.get("trackQuality", "vague"), TrackQuality.Vague)
            q = min(q, TrackQuality.Approximate)
            q_key = q.name.lower()
            err = float(err_map.get(q_key, 3000.0))
            delay = float(det_rules.get("reportDelaySec", 0.0)) if sdef.get("reportDelay") else 0.0
            det = RawDetection(
                source_id=s.id,
                source_kind=0,
                threat_id=t.id,
                phantom_key=0,
                quality=q,
                pos=t.pos,
                vel_mps=t.vel_mps,
                tag=t.tag,
                can_cue=(sdef.get("layer") == "local"),
                uncertainty_radius_m=err,
            )
            self._route_detection(ctx, det, delay)

    def _fire_control_detect(
        self,
        ctx: Any,
        f: FireUnit,
        night: Dict[str, Any],
        season: str,
        det_rules: Dict[str, Any],
        err_map: Dict[str, Any],
    ) -> None:
        if f.pos is None or f.suspended_until_sec > ctx.time_sec + 1e-9:
            return
        fdef = ctx.level.catalog.air_defense_units.get(f.def_id or "", {})
        pos_rules = ctx.level.catalog.rules.get("positions", {})
        fcr = fdef.get("fireControlRadar")
        if fcr is not None:
            if f.deploy_state != UnitDeployState.Deployed or f.radar_destroyed or f.emitter is None or not f.emitter.on:
                return
            r0 = float(fcr.get("rangeM", 0.0))
            if not f.powered:
                r0 = r0 * float(det_rules.get("unpoweredActiveRangeMult", 0.5))
            if season == "winter":
                r0 = r0 * float(det_rules.get("winterActiveRangeMult", 0.9))
            if f.new_position_penalty:
                r0 = r0 * float(pos_rules.get("newUnsurveyed", {}).get("firstNightEfficiencyMult", 0.7))
            cand_ids = ctx.threat_grid.query_circle(f.pos, r0)
            low_below = float(det_rules.get("lowAltitudeBelowM", 200.0))
            low_map = det_rules.get("lowAltitudeRangeMult", {"none": 0.0, "poor": 0.25, "medium": 0.5, "good": 0.75})
            fcr_low = fcr.get("lowAltitude", "good")
            for tid in cand_ids:
                t = ctx.state.threats.try_get(tid)
                if t is None or t.pos is None or t.phase == ThreatPhase.Arrived:
                    continue
                r = r0
                if (t.alt_m or 0.0) < low_below:
                    r = r * float(low_map.get(fcr_low, 0.75))
                if f.pos.distance_to(t.pos) > r + 1e-9:
                    continue
                hp = getattr(f, "horizon_profile", None)
                if hp is not None:
                    if not hp.has_line_of_sight_agl(t.pos, t.alt_m or 0.0):
                        continue
                else:
                    ant = float(fcr.get("antennaHeightM") or ctx.terrain.default_antenna_height_m)
                    if not ctx.terrain.has_line_of_sight_agl(f.pos, ant, t.pos, t.alt_m or 0.0):
                        continue
                ctx.state.sensing.detections.append(
                    RawDetection(
                        source_id=f.id,
                        source_kind=1,
                        threat_id=t.id,
                        phantom_key=0,
                        quality=TrackQuality.Precise,
                        pos=t.pos,
                        vel_mps=t.vel_mps,
                        tag=t.tag,
                        can_cue=False,
                        uncertainty_radius_m=float(err_map.get("precise", 50.0)),
                    )
                )
            return

        self_acq = fdef.get("selfAcquisitionRangeM")
        if self_acq is not None:
            can_move_acq = f.deploy_state == UnitDeployState.Moving and fdef.get("fireOnMove", "no") != "no"
            if f.deploy_state != UnitDeployState.Deployed and not can_move_acq:
                return
            r = float(self_acq)
            if fdef.get("selfAcquisition") == "optical":
                settings = (f.placement.settings if f.placement else {}) or {}
                has_aid = bool(settings.get("nightAids"))
                tod = night.get("timeOfDay", "night")
                night_mult = 1.0 if (tod == "day" or has_aid) else float(det_rules.get("opticalNightRangeMult", 0.3))
                weather = night.get("weather")
                w_map = det_rules.get("opticalWeatherRangeMult", {"clear": 1.0, "moonlit": 1.5, "low_cloud": 0.6, "fog": 0.25})
                w_mult = 1.0 if weather is None else float(w_map.get(weather, 1.0))
                r = r * night_mult * w_mult
            cand_ids = ctx.threat_grid.query_circle(f.pos, r)
            for tid in cand_ids:
                t = ctx.state.threats.try_get(tid)
                if t is None or t.pos is None or t.phase == ThreatPhase.Arrived:
                    continue
                if f.pos.distance_to(t.pos) > r + 1e-9:
                    continue
                hp = getattr(f, "horizon_profile", None)
                if hp is not None:
                    if not hp.has_line_of_sight_agl(t.pos, t.alt_m or 0.0):
                        continue
                elif not ctx.terrain.has_line_of_sight_agl(f.pos, ctx.terrain.default_antenna_height_m, t.pos, t.alt_m or 0.0):
                    continue
                ctx.state.sensing.detections.append(
                    RawDetection(
                        source_id=f.id,
                        source_kind=2,
                        threat_id=t.id,
                        phantom_key=0,
                        quality=TrackQuality.Precise,
                        pos=t.pos,
                        vel_mps=t.vel_mps,
                        tag=t.tag,
                        can_cue=False,
                        uncertainty_radius_m=float(err_map.get("precise", 50.0)),
                    )
                )

    def _false_alarms(
        self,
        ctx: Any,
        night: Dict[str, Any],
        season: str,
        det_rules: Dict[str, Any],
        b_line_rules: Dict[str, Any],
        err_map: Dict[str, Any],
    ) -> None:
        fa_rates = det_rules.get("falseAlarmsPerSec", {})
        for s in ctx.state.sensors.alive_list():
            if not self._sensor_active(s, ctx.time_sec):
                continue
            sdef = ctx.level.catalog.sensors.get(s.def_id or "", {})
            fa_level = sdef.get("falseAlarms")
            if not fa_level:
                continue
            p = float(fa_rates.get(fa_level, 0.0)) * ctx.step_sec
            if not ctx.rng.chance(p):
                continue
            if sdef.get("detectionRangeM") is not None and s.pos is not None:
                r0 = self._effective_sensor_range(ctx, s, sdef, night, season, alt_m=None)
                u1 = ctx.rng.next_double()
                u2 = ctx.rng.next_double()
                r_fa = r0 * math.sqrt(u1)
                b = 2.0 * math.pi * u2
                pos = Vec2(s.pos.x + r_fa * math.sin(b), s.pos.y + r_fa * math.cos(b))
            elif sdef.get("coverage") == "urban_areas":
                urbans = ctx.level.urban_polygons
                if not urbans:
                    continue
                idx = ctx.rng.next_int(0, len(urbans))
                poly = urbans[idx]
                xs = [pt.x for pt in poly]
                ys = [pt.y for pt in poly]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                chosen_pos: Optional[Vec2] = None
                for _ in range(8):
                    px = min_x + (max_x - min_x) * ctx.rng.next_double()
                    py = min_y + (max_y - min_y) * ctx.rng.next_double()
                    cand = Vec2(px, py)
                    if Geo.point_in_polygon(cand, poly):
                        chosen_pos = cand
                        break
                if chosen_pos is None:
                    chosen_pos = Vec2(sum(xs) / len(xs), sum(ys) / len(ys))
                pos = chosen_pos
            else:
                w_m = float(ctx.level.meta.get("map", {}).get("widthM", 20000.0))
                h_m = float(ctx.level.meta.get("map", {}).get("heightM", 20000.0))
                pos = Vec2(w_m * ctx.rng.next_double(), h_m * ctx.rng.next_double())

            q = min(_QUALITY_MAP.get(sdef.get("trackQuality", "vague"), TrackQuality.Vague), TrackQuality.Approximate)
            b_applies = self._b_line_applies(ctx, sdef)
            if b_applies:
                b_max_q = _QUALITY_MAP.get(b_line_rules.get("maxTrackQuality", "approximate"), TrackQuality.Approximate)
                q = min(q, b_max_q)
            key = ctx.state.sensing.next_phantom_key
            ctx.state.sensing.next_phantom_key += 1
            delay = max(
                float(det_rules.get("reportDelaySec", 0.0)) if sdef.get("reportDelay") else 0.0,
                float(b_line_rules.get("relayDelaySec", 0.0)) if b_applies else 0.0,
            )
            det = RawDetection(
                source_id=s.id,
                source_kind=0,
                threat_id=0,
                phantom_key=key,
                quality=q,
                pos=pos,
                vel_mps=Vec2(0.0, 0.0),
                tag=None,
                can_cue=False,
                uncertainty_radius_m=float(err_map.get(q.name.lower(), 3000.0)),
            )
            self._route_detection(ctx, det, delay)


class TrackFusionSystem:
    """System 4: TrackFusionSystem (02_sensing_tracks_ew_emission.md §3.3)."""

    order = 4
    name = "TrackFusionSystem"
    stream_name = "fusion"

    def initialize(self, ctx: Any) -> None:
        pass

    def execute(self, ctx: Any) -> None:
        tr_rules = ctx.level.catalog.rules.get("tracks", {})
        det_rules = tr_rules.get("detectionRules", {})
        err_map = det_rules.get("errorRadiusM", {"vague": 5000.0, "approximate": 1000.0, "precise": 0.0})
        fusion_req = int(tr_rules.get("approximateFromLocalSensorCount", 2))
        lost_sec = float(det_rules.get("trackLostSec", 60.0))
        lost_ticks = SimTime.sec_to_ticks_ceil(lost_sec, ctx.step_sec)

        groups: Dict[Tuple[int, int], List[RawDetection]] = {}
        for d in ctx.state.sensing.detections:
            key = (d.threat_id, d.phantom_key)
            groups.setdefault(key, []).append(d)

        track_by_key: Dict[Tuple[int, int], Track] = {}
        for tr in ctx.state.tracks.alive_list():
            track_by_key[(tr.threat_id, tr.phantom_key)] = tr

        updated_ids: Set[int] = set()
        for key in sorted(groups.keys()):
            dets = sorted(groups[key], key=lambda item: (item.source_kind, item.source_id))
            q, net_q, best_det = self._fuse_quality(ctx, dets, fusion_req, err_map)
            src_mask = 0
            for d in dets:
                src_mask |= (1 << d.source_kind)

            tr = track_by_key.get(key)
            is_new = False
            prev_q = TrackQuality.Vague
            if tr is None:
                tr = Track(
                    pos=best_det.pos,
                    alt_m=self._threat_alt(ctx, key[0]),
                    threat_id=key[0],
                    phantom_key=key[1],
                    quality=q,
                    tag=best_det.tag if q >= TrackQuality.Approximate else None,
                    vel_mps=best_det.vel_mps,
                    uncertainty_radius_m=best_det.uncertainty_radius_m,
                    cued=False,
                    classified=(q >= TrackQuality.Approximate and best_det.tag is not None),
                    precise_first_tick=ctx.tick if q == TrackQuality.Precise else -1,
                    decoy_check_done=False,
                    identified_as_decoy=False,
                    last_seen_tick=ctx.tick,
                    source_mask=src_mask,
                )
                ctx.state.tracks.add(tr)
                track_by_key[key] = tr
                is_new = True
            else:
                prev_q = tr.quality
                tr.quality = q
                tr.pos = best_det.pos
                tr.alt_m = self._threat_alt(ctx, key[0])
                tr.vel_mps = best_det.vel_mps
                tr.uncertainty_radius_m = best_det.uncertainty_radius_m
                tr.last_seen_tick = ctx.tick
                tr.source_mask = src_mask
                if q >= TrackQuality.Approximate and best_det.tag is not None:
                    tr.tag = best_det.tag
                    tr.classified = True
                if q == TrackQuality.Precise and tr.precise_first_tick < 0:
                    tr.precise_first_tick = ctx.tick

            setattr(tr, "network_quality", net_q)
            tr.cued = FireControlQueries.cued(tr, tr_rules)
            self._check_decoy_discrimination(ctx, tr, prev_q, is_new, tr_rules)

            if key[0] > 0:
                th = ctx.state.threats.try_get(key[0])
                if th is not None:
                    if th.max_track_quality is None or q > th.max_track_quality:
                        th.max_track_quality = q

            updated_ids.add(tr.id)
            if is_new:
                ctx.events.emit(
                    SimEventType.TrackCreated,
                    fields=(tr.id, tr.threat_id, int(tr.quality), tr.pos),
                    track_id=tr.id,
                    threat_id=tr.threat_id,
                    quality=tr.quality,
                    pos=tr.pos,
                )
            elif tr.quality != prev_q:
                ctx.events.emit(
                    SimEventType.TrackQualityChanged,
                    fields=(tr.id, int(prev_q), int(tr.quality)),
                    track_id=tr.id,
                    old_quality=prev_q,
                    new_quality=tr.quality,
                )

        # Coasting and expiration
        for tr in ctx.state.tracks.alive_list():
            if tr.id in updated_ids:
                continue
            if tr.threat_id > 0:
                th = ctx.state.threats.try_get(tr.threat_id)
                if th is None or th.phase == ThreatPhase.Arrived:
                    ctx.events.emit(SimEventType.TrackLost, fields=(tr.id, tr.threat_id), track_id=tr.id)
                    ctx.state.tracks.remove(tr.id)
                    continue
            if ctx.tick - tr.last_seen_tick >= lost_ticks:
                ctx.events.emit(SimEventType.TrackLost, fields=(tr.id, tr.threat_id), track_id=tr.id)
                ctx.state.tracks.remove(tr.id)
                continue
            if tr.pos is not None:
                tr.pos = tr.pos + tr.vel_mps * ctx.step_sec

    def _threat_alt(self, ctx: Any, threat_id: int) -> float:
        if threat_id > 0:
            th = ctx.state.threats.try_get(threat_id)
            if th is not None and th.alt_m is not None:
                return th.alt_m
        return 0.0

    def _fuse_quality(
        self, ctx: Any, dets: List[RawDetection], fusion_req: int, err_map: Dict[str, Any]
    ) -> Tuple[TrackQuality, Optional[TrackQuality], RawDetection]:
        best_q = max(d.quality for d in dets)
        cands = [d for d in dets if d.quality == best_q]
        cands.sort(key=lambda d: (d.uncertainty_radius_m, d.source_kind, d.source_id))
        best_det = cands[0]

        net_dets = [d for d in dets if d.source_kind in (0, 3)]
        net_q: Optional[TrackQuality] = max((d.quality for d in net_dets), default=None)

        if best_q == TrackQuality.Vague and best_det.threat_id > 0:
            local_sensor_ids = {d.source_id for d in dets if d.source_kind == 0 and d.can_cue}
            if len(local_sensor_ids) >= fusion_req:
                best_q = TrackQuality.Approximate
                net_q = TrackQuality.Approximate
                best_det = RawDetection(
                    source_id=best_det.source_id,
                    source_kind=best_det.source_kind,
                    threat_id=best_det.threat_id,
                    phantom_key=best_det.phantom_key,
                    quality=TrackQuality.Approximate,
                    pos=best_det.pos,
                    vel_mps=best_det.vel_mps,
                    tag=best_det.tag,
                    can_cue=best_det.can_cue,
                    uncertainty_radius_m=float(err_map.get("approximate", 1000.0)),
                )
        return best_q, net_q, best_det

    def _check_decoy_discrimination(
        self, ctx: Any, tr: Track, prev_q: TrackQuality, is_new: bool, tr_rules: Dict[str, Any]
    ) -> None:
        if tr.threat_id <= 0 or tr.identified_as_decoy or tr.quality < TrackQuality.Approximate:
            return
        th = ctx.state.threats.try_get(tr.threat_id)
        if th is None or th.tag != TargetTag.DECOY:
            return
        q_table = {q["id"]: float(q.get("decoyDiscrimination", 0.0)) for q in tr_rules.get("qualities", [])}
        p_approx = q_table.get("approximate", 0.7)
        p_prec = q_table.get("precise", 0.95)
        bonus = float(getattr(ctx.config, "dossier_decoy_bonus", 0.0))
        p_approx = min(1.0, p_approx + bonus)
        p_prec = min(1.0, p_prec + bonus)

        if tr.quality == TrackQuality.Approximate and not tr.decoy_check_done:
            tr.decoy_check_done = True
            if ctx.rng.chance(p_approx):
                tr.identified_as_decoy = True
                ctx.events.emit(SimEventType.DecoyIdentified, fields=(tr.id, tr.threat_id), track_id=tr.id, threat_id=tr.threat_id)
        elif tr.quality == TrackQuality.Precise and (is_new or prev_q < TrackQuality.Precise):
            if not tr.decoy_check_done:
                tr.decoy_check_done = True
                p_roll = p_prec
            else:
                p_roll = (p_prec - p_approx) / max(1e-9, 1.0 - p_approx) if p_approx < 1.0 else 1.0
            if ctx.rng.chance(p_roll):
                tr.identified_as_decoy = True
                ctx.events.emit(SimEventType.DecoyIdentified, fields=(tr.id, tr.threat_id), track_id=tr.id, threat_id=tr.threat_id)


class ElectronicWarfareSystem:
    """System 5: ElectronicWarfareSystem (02_sensing_tracks_ew_emission.md §3.4)."""

    order = 5
    name = "ElectronicWarfareSystem"
    stream_name = "ew"

    def initialize(self, ctx: Any) -> None:
        pass

    def execute(self, ctx: Any) -> None:
        cat = ctx.level.catalog
        ew_rules = cat.rules.get("ew", {})
        pos_rules = cat.rules.get("positions", {})
        night = ctx.sensor_system._get_night(ctx)
        season = EnvironmentResolver.season_for(night, ctx.level.date)

        eff_row = ew_rules.get("effectiveness", {"nav": 1.0, "counterUas": 1.0})
        eff_nav = float(eff_row.get("nav", 1.0))
        eff_cuas = float(eff_row.get("counterUas", 1.0))
        below_full_mult = float(ew_rules.get("belowFullStrengthMult", 0.5))
        unpow_mult = float(ew_rules.get("unpoweredEffectMult", 0.5))
        win_mult = float(ew_rules.get("winterEffectMult", 0.9))
        new_pos_mult = float(pos_rules.get("newUnsurveyed", {}).get("firstNightEfficiencyMult", 0.7))
        hover_sec = float(ew_rules.get("hoverBeforeCrashSec", 120.0))
        hover_ticks = SimTime.sec_to_ticks_ceil(hover_sec, ctx.step_sec)

        active_ew: List[Tuple[EwUnit, Dict[str, Any], float]] = []
        urban_nav_active = False
        for u in ctx.state.ew_units.alive_list():
            if u.deploy_state != UnitDeployState.Deployed or u.suspended_until_sec > ctx.time_sec + 1e-9:
                continue
            if u.emitter is None or not u.emitter.on or u.pos is None:
                continue
            edef = cat.ew_units.get(u.def_id or "", {})
            eff_type = edef.get("effect", "")
            if eff_type == "self_protection":
                continue
            base_eff = eff_nav if eff_type in ("nav_jam", "nav_spoof") else eff_cuas
            m_u = base_eff
            if u.light_damaged:
                m_u *= below_full_mult
            if u.new_position_penalty:
                m_u *= new_pos_mult
            if not u.powered:
                m_u *= unpow_mult
            if season == "winter":
                m_u *= win_mult
            active_ew.append((u, edef, m_u))
            if eff_type in ("nav_jam", "nav_spoof") and Geo.in_urban(ctx.level.urban_polygons, u.pos):
                urban_nav_active = True

        if urban_nav_active:
            ctx.state.ew.urban_nav_jam_sec += ctx.step_sec
            min_urban_sec = float(ew_rules.get("urbanNavJamMinSec", 3600.0))
            if ctx.state.ew.urban_nav_jam_sec >= min_urban_sec - 1e-9:
                ctx.state.ew.urban_nav_jam_triggered = True

        for th in ctx.state.threats.alive_list():
            if th.phase == ThreatPhase.Arrived or th.pos is None:
                continue
            # Check hovering link-cut timeout
            if th.link_cut_state == 2 and th.link_cut_at_tick >= 0:
                if ctx.tick - th.link_cut_at_tick >= hover_ticks:
                    th.link_cut_state = 3
                    ctx.state.scoring.threats_ew_downed += 1
                    ctx.events.emit(SimEventType.EwLinkCut, fields=(0, th.id, "crash"), threat_id=th.id, outcome="crash")
                    self._cleanup_threat(ctx, th.id)
                    ctx.state.threats.remove(th.id)
                    continue

            if th.kind != ThreatKind.Munition:
                continue
            mdef = cat.munitions.get(th.def_id or "", {})
            if mdef.get("ewImmune"):
                continue

            covering: List[Tuple[EwUnit, Dict[str, Any], float]] = []
            for u, edef, m_u in active_ew:
                r_m = float(edef.get("radiusM", 0.0) or 0.0)
                if u.pos.distance_to(th.pos) <= r_m + 1e-9:
                    eff_against = edef.get("effectiveAgainst") or []
                    tag_str = th.tag.name if th.tag is not None else ""
                    if not eff_against or tag_str in eff_against or (th.def_id or "") in eff_against:
                        covering.append((u, edef, m_u))

            if not covering:
                continue

            if not th.ew_ever_covered:
                th.ew_ever_covered = True
                ctx.state.scoring.threats_ever_ew_covered += 1

            ai_vis_mult = 0.5 if mdef.get("aiVisionActive") else 1.0

            # 1. Link cut
            if th.link_cut_state == 0:
                link_units = [(u, edef, m_u) for u, edef, m_u in covering if edef.get("effect") in ("link_cut", "link_cut_directional")]
                if link_units:
                    u0, edef0, m0 = link_units[0]
                    p_cut = float(edef0.get("linkCutProb", 0.5)) * m0
                    if ctx.rng.chance(p_cut):
                        weights = ew_rules.get("linkCutOutcomeWeights", {"crash": 0.5, "hover": 0.25, "return": 0.25})
                        w_c = float(weights.get("crash", 0.5))
                        w_h = float(weights.get("hover", 0.25))
                        w_r = float(weights.get("return", 0.25))
                        tot_w = w_c + w_h + w_r
                        roll = ctx.rng.next_double() * tot_w
                        if roll < w_c:
                            th.link_cut_state = 3
                            ctx.state.scoring.threats_ew_downed += 1
                            ctx.events.emit(SimEventType.EwLinkCut, fields=(u0.id, th.id, "crash"), unit_id=u0.id, threat_id=th.id, outcome="crash")
                            self._cleanup_threat(ctx, th.id)
                            ctx.state.threats.remove(th.id)
                            continue
                        elif roll < w_c + w_h:
                            th.link_cut_state = 2
                            th.link_cut_at_tick = ctx.tick
                            ThreatRouting.hover(th, ctx.time_sec)
                            ctx.events.emit(SimEventType.EwLinkCut, fields=(u0.id, th.id, "hover"), unit_id=u0.id, threat_id=th.id, outcome="hover")
                        else:
                            th.link_cut_state = 3
                            w_m = float(ctx.level.meta.get("map", {}).get("widthM", 20000.0))
                            h_m = float(ctx.level.meta.get("map", {}).get("heightM", 20000.0))
                            ThreatRouting.begin_egress(th, ctx.time_sec, w_m, h_m)
                            ctx.events.emit(SimEventType.EwLinkCut, fields=(u0.id, th.id, "return"), unit_id=u0.id, threat_id=th.id, outcome="return")
                    else:
                        th.link_cut_state = 1

            # 2. Nav jam / spoof
            if th.ew_nav == 0:
                nav_units = [(u, edef, m_u) for u, edef, m_u in covering if edef.get("effect") in ("nav_jam", "nav_spoof")]
                if nav_units:
                    u0, edef0, m0 = nav_units[0]
                    p_nav = float(edef0.get("degradeProb", 1.0)) * m0 * ai_vis_mult
                    if ctx.rng.chance(p_nav):
                        th.ew_nav = 2
                        th.accuracy_tier_drop = max(th.accuracy_tier_drop, int(edef0.get("accuracyTierDrop", 1)))
                        th.ew_extra_offset_m = max(th.ew_extra_offset_m, float(edef0.get("extraOffsetM", 500.0)))
                    else:
                        th.ew_nav = 1

            if th.ew_pull == 0:
                spoof_units = [(u, edef, m_u) for u, edef, m_u in covering if edef.get("effect") == "nav_spoof"]
                if spoof_units:
                    u0, edef0, m0 = spoof_units[0]
                    p_pull = float(edef0.get("pullToEmptyProb", 0.3)) * m0 * ai_vis_mult
                    if ctx.rng.chance(p_pull):
                        th.ew_pull = 2
                        lure = u0.lure_point or (u0.pos + Vec2(1500.0, 0.0))
                        th.ew_divert_pos = lure
                        ThreatRouting.retarget(th, ctx.time_sec, lure, 0, 0)
                        ctx.events.emit(SimEventType.EwDiverted, fields=(u0.id, th.id, lure), unit_id=u0.id, threat_id=th.id, pos=lure)
                    else:
                        th.ew_pull = 1

    def _cleanup_threat(self, ctx: Any, threat_id: int) -> None:
        for tr in ctx.state.tracks.alive_list():
            if tr.threat_id == threat_id:
                ctx.events.emit(SimEventType.TrackLost, fields=(tr.id, threat_id), track_id=tr.id)
                ctx.state.tracks.remove(tr.id)
        for ic in ctx.state.interceptors.alive_list():
            if ic.threat_id == threat_id:
                ctx.state.interceptors.remove(ic.id)


class EmissionSystem:
    """System 6: EmissionSystem (02_sensing_tracks_ew_emission.md §3.5)."""

    order = 6
    name = "EmissionSystem"
    stream_name = "emission"

    def initialize(self, ctx: Any) -> None:
        pass

    def execute(self, ctx: Any) -> None:
        em_rules = ctx.level.catalog.rules.get("emission", {})
        shutdown_tiers = em_rules.get(
            "shutdownTiming",
            [
                {"armDistanceFractionAbove": 0.5, "armHitProbMult": 0.2},
                {"armDistanceFractionAbove": 0.25, "armHitProbMult": 0.5},
                {"armDistanceFractionAbove": 0.0, "armHitProbMult": 0.8},
            ],
        )

        for store in (ctx.state.fire_units, ctx.state.sensors, ctx.state.ew_units, ctx.state.deception_units):
            for u in store.alive_list():
                em = u.emitter
                if em is None:
                    continue
                was_on = em.on

                if (
                    u.deploy_state != UnitDeployState.Deployed
                    or u.suspended_until_sec > ctx.time_sec + 1e-9
                    or getattr(u, "radar_destroyed", False)
                ):
                    em.on = False
                elif em.forced_silence_until_sec > ctx.time_sec + 1e-9:
                    em.on = False
                elif em.sector_override == 1:
                    em.on = False
                elif em.sector_override == 2:
                    em.on = True
                elif getattr(em, "arm_silenced", False):
                    em.on = False
                else:
                    pol = em.policy_id
                    if pol in ("always_on", "continuous"):
                        em.on = True
                    elif pol == "silent":
                        em.on = False
                    elif pol == "on_warning":
                        em.on = self._has_warning_or_approx_track(ctx)
                    elif pol in ("intermittent", "blink"):
                        period = max(1.0, em.duty_on_sec + em.duty_off_sec)
                        phase = (ctx.time_sec - em.cycle_anchor_sec) % period
                        em.on = phase < em.duty_on_sec - 1e-9
                    elif pol == "silent_standby":
                        em.on = em.fc_mode in (1, 3) or self._should_open_last_moment(ctx, u)
                    elif pol == "decoy_coordinated":
                        em.on = self._decoy_ready(ctx, u)
                    else:
                        em.on = True

                # ARM incoming detection & shutdown timing
                self._check_arm_incoming(ctx, u, em, shutdown_tiers)

                if em.on and not was_on:
                    setattr(em, "on_since_tick", ctx.tick)
                elif not em.on:
                    setattr(em, "on_since_tick", -1)

                if em.on != was_on:
                    ctx.events.emit(
                        SimEventType.EmitterSwitched,
                        fields=(u.id, em.on, em.policy_id),
                        unit_id=u.id,
                        on=em.on,
                        policy_id=em.policy_id,
                    )

    def _has_warning_or_approx_track(self, ctx: Any) -> bool:
        if ctx.state.sensing.emitted_early_warnings:
            return True
        for tr in ctx.state.tracks.alive_list():
            if tr.quality >= TrackQuality.Approximate:
                return True
        return False

    def _should_open_last_moment(self, ctx: Any, u: PlayerUnitEntity) -> bool:
        if not isinstance(u, FireUnit) or u.pos is None:
            return False
        cat = ctx.level.catalog
        udef = cat.air_defense_units.get(u.def_id or "", {})
        rmax = max((float(cat.weapons[wid].get("rangeM", 0.0)) for wid in udef.get("weaponIds", []) if wid in cat.weapons), default=0.0)
        if rmax <= 0.0:
            return False
        for tr in ctx.state.tracks.alive_list():
            if tr.quality >= TrackQuality.Approximate and tr.pos is not None:
                tau = SensingMath.time_to_enter_radius(tr.pos - u.pos, tr.vel_mps, Vec2(0.0, 0.0), rmax)
                if tau is not None and tau <= 15.0:
                    return True
        return False

    def _decoy_ready(self, ctx: Any, u: PlayerUnitEntity) -> bool:
        for d in ctx.state.deception_units.alive_list():
            if d.deploy_state == UnitDeployState.Deployed and d.emitter is not None and d.emitter.on:
                return True
        return True

    def _check_arm_incoming(
        self, ctx: Any, u: PlayerUnitEntity, em: EmitterControl, shutdown_tiers: List[Dict[str, Any]]
    ) -> None:
        if u.pos is None:
            return
        for th in ctx.state.threats.alive_list():
            if th.homing_unit_id != u.id and th.target_unit_id != u.id:
                continue
            mdef = ctx.level.catalog.munitions.get(th.def_id or "", {})
            if not mdef.get("antiRadiation") and th.homing_unit_id != u.id:
                continue
            if th.arm_initial_dist_m <= 0.0 and th.pos is not None:
                th.arm_initial_dist_m = max(1.0, u.pos.distance_to(th.pos))
            if th.id not in em.arm_warned_track_ids:
                em.arm_warned_track_ids.append(th.id)
                ctx.events.emit(SimEventType.ArmThreatDetected, fields=(u.id, th.id), unit_id=u.id, threat_id=th.id)
                if em.on_arm_incoming == 0:  # shutdown_immediately
                    em.on = False
                    setattr(em, "arm_silenced", True)
                    frac = (u.pos.distance_to(th.pos) / max(1.0, th.arm_initial_dist_m)) if th.pos else 0.0
                    for tier in shutdown_tiers:
                        if frac > float(tier.get("armDistanceFractionAbove", 0.0)):
                            th.arm_hit_prob_mult = min(th.arm_hit_prob_mult, float(tier.get("armHitProbMult", 0.8)))
                            break


class ExposureSystem:
    """System 11: ExposureSystem (02_sensing_tracks_ew_emission.md §3.6)."""

    order = 11
    name = "ExposureSystem"
    stream_name = "exposure"

    def initialize(self, ctx: Any) -> None:
        pass

    def execute(self, ctx: Any) -> None:
        exp_rules = ctx.level.catalog.rules.get("exposure", {})
        rates = exp_rules.get("ratesPerSec", {})
        r_self = float(rates.get("fireControlSelfSearch", 2.0 / 60.0))
        r_cued = float(rates.get("fireControlCued", 0.6 / 60.0))
        r_silent = float(rates.get("silent", -0.5 / 60.0))
        r_recon = float(rates.get("enemyReconNearby", 0.5 / 60.0))
        per_missile = float(exp_rules.get("perMissileLaunched", 5.0))
        recon_rad_m = float(exp_rules.get("enemyReconRadiusM", 5000.0))

        sensor_rates = exp_rules.get("sensorExposureLevelRatesPerSec", {"high": 1.0 / 60.0, "medium": 0.6 / 60.0, "zero": 0.0, "none": 0.0})
        ew_rates = exp_rules.get("ewExposureLevelRatesPerSec", {"high": 1.0 / 60.0, "medium": 0.6 / 60.0, "low": 0.3 / 60.0})
        thresholds = [float(t.get("atLeast", 40.0)) for t in exp_rules.get("thresholds", [{"atLeast": 40}, {"atLeast": 70}, {"atLeast": 100}])]

        # Count missiles launched this tick per FireUnit
        launches_by_unit: Dict[int, int] = {}
        for ev in ctx.events.current_step:
            if ev.type == SimEventType.InterceptorLaunched:
                fuid = int(ev.data.get("fire_unit_id", 0) or 0)
                if fuid > 0:
                    launches_by_unit[fuid] = launches_by_unit.get(fuid, 0) + 1

        # Active recon threats
        recon_positions: List[Vec2] = []
        for th in ctx.state.threats.alive_list():
            if th.pos is None or th.phase == ThreatPhase.Arrived:
                continue
            pdef = ctx.level.catalog.platforms.get(th.def_id or "") or ctx.level.catalog.munitions.get(th.def_id or "") or {}
            if pdef.get("behavior") == "recon_loiter" or "orlan" in (th.def_id or "") or "recon" in (th.def_id or ""):
                recon_positions.append(th.pos)

        has_cued_tracks = any(tr.cued for tr in ctx.state.tracks.alive_list())

        for store, kind in (
            (ctx.state.fire_units, EntityKind.FireUnit),
            (ctx.state.sensors, EntityKind.SensorUnit),
            (ctx.state.ew_units, EntityKind.EwUnit),
            (ctx.state.deception_units, EntityKind.DeceptionUnit),
        ):
            for u in store.alive_list():
                if getattr(u, "automatic", False):
                    continue
                prev_exp = u.exposure
                rate = 0.0
                emitting = u.emitter is not None and u.emitter.on and u.deploy_state == UnitDeployState.Deployed
                if kind == EntityKind.FireUnit:
                    if emitting:
                        rate = r_cued if has_cued_tracks else r_self
                elif kind == EntityKind.SensorUnit:
                    sdef = ctx.level.catalog.sensors.get(u.def_id or "", {})
                    lvl = sdef.get("exposureLevel", "zero")
                    if emitting:
                        rate = float(sensor_rates.get(lvl, 0.0))
                elif kind == EntityKind.EwUnit:
                    edef = ctx.level.catalog.ew_units.get(u.def_id or "", {})
                    lvl = edef.get("exposureLevel", "low")
                    if emitting:
                        rate = float(ew_rates.get(lvl, 0.3 / 60.0))
                elif kind == EntityKind.DeceptionUnit:
                    ddef = ctx.level.catalog.deception_units.get(u.def_id or "", {})
                    if emitting:
                        rate = float(sensor_rates.get("high", 1.0 / 60.0))
                    elif ddef.get("effect") == "visual_decoy" and u.deploy_state == UnitDeployState.Deployed:
                        rate = float(ew_rates.get("low", 0.3 / 60.0))

                if u.pos is not None and any(u.pos.distance_to(rp) <= recon_rad_m + 1e-9 for rp in recon_positions):
                    rate += r_recon

                n_launch = launches_by_unit.get(u.id, 0)
                if rate == 0.0 and n_launch == 0:
                    rate = r_silent

                new_exp = min(100.0, max(0.0, prev_exp + rate * ctx.step_sec + n_launch * per_missile))
                u.exposure = new_exp
                if new_exp > u.exposure_peak:
                    u.exposure_peak = new_exp

                for th_val in thresholds:
                    if prev_exp < th_val <= new_exp:
                        ctx.events.emit(
                            SimEventType.ExposureThresholdCrossed,
                            fields=(u.id, int(th_val), new_exp),
                            unit_id=u.id,
                            threshold=int(th_val),
                            exposure=new_exp,
                        )
                        if th_val >= 40.0 and isinstance(u, DeceptionUnit):
                            ctx.events.emit(SimEventType.DeceptionTriggered, fields=(u.id, u.def_id or ""), unit_id=u.id)


class CoverageQuery:
    """Static coverage preview query (02_sensing_tracks_ew_emission.md §3.2.7)."""

    @staticmethod
    def compute_coverage(ctx: Any, alt_m: float, active_only: bool = False) -> List[Tuple[int, Vec2, float]]:
        res: List[Tuple[int, Vec2, float]] = []
        night = ctx.sensor_system._get_night(ctx)
        season = EnvironmentResolver.season_for(night, ctx.level.date)
        for s in ctx.state.sensors.alive_list():
            if s.pos is None or s.deploy_state != UnitDeployState.Deployed or s.automatic:
                continue
            if active_only and (s.emitter is None or not s.emitter.on):
                continue
            sdef = ctx.level.catalog.sensors.get(s.def_id or "", {})
            if sdef.get("detectionRangeM") is not None:
                r = ctx.sensor_system._effective_sensor_range(ctx, s, sdef, night, season, alt_m=alt_m)
                res.append((s.id, s.pos, r))
        return res

