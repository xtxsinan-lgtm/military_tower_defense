"""World orchestrator, SimContext, DefaultDeploymentBuilder, DeploymentValidator, SimWorld, SimSnapshot, ReplayRunner (00_core.md §3)."""

from __future__ import annotations

import copy
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

from .core import Geo, SimError, SimRandom, SimTime, SpatialGrid, Vec2
from .enemy_ai import (
    ChoiceStage,
    CommandStage,
    DeploymentStage,
    EnemyAiHooks,
    EnemyIntelSystem,
    StoryStage,
)
from .engagement import (
    EngagementSystem,
    ExternalSupportSystem,
    ImpactSystem,
    InterceptorSystem,
    ScoringSystem,
)
from .entities import (
    CarryIn,
    DeceptionUnit,
    DeploymentPlan,
    EventSink,
    EwUnit,
    FireUnit,
    GridNode,
    NightResult,
    PlacedUnit,
    PlayerUnitCategory,
    PlayerUnitEntity,
    SensorUnit,
    SimCommand,
    SimConfig,
    SimEvent,
    SimEventType,
    SimState,
    Structure,
    UnitDeployState,
)
from .loader import LevelData
from .movement import (
    DefaultEnemyAiHooks,
    EnemyMovementSystem,
    IEnemyAiHooks,
    WaveSpawnSystem,
)
from .sensing import (
    ElectronicWarfareSystem,
    EmissionSystem,
    ExposureSystem,
    SensorSystem,
    TrackFusionSystem,
)
from .terrain import TerrainModel, TerrainRules


class DeploymentValidator:
    """Validates pre-night DeploymentPlan against level rules (00_core.md §3.2 Step 3, 04 §3.3.1)."""

    @staticmethod
    def is_valid_pos(
        pos: Vec2,
        level: LevelData,
        existing_positions: Sequence[Vec2],
        min_spacing_m: float,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        map_w = float(level.meta.get("map", {}).get("widthM", 20000.0))
        map_h = float(level.meta.get("map", {}).get("heightM", 20000.0))
        if not (0.0 <= pos.x <= map_w and 0.0 <= pos.y <= map_h):
            return False, "E_DEPLOY_OUT_OF_ZONE", f"Position ({pos.x}, {pos.y}) outside map bounds"

        zones = level.deploy.get("zones") or []
        if zones:
            in_any_zone = any(
                Geo.point_in_polygon(pos, z.get("polygon") or [])
                for z in zones
                if z.get("polygon")
            )
            if not in_any_zone:
                return False, "E_DEPLOY_OUT_OF_ZONE", f"Position ({pos.x}, {pos.y}) outside deploy zones"

        for fb in level.deploy.get("forbidden") or []:
            poly = fb.get("polygon") or []
            if poly and Geo.point_in_polygon(pos, poly):
                return False, "E_DEPLOY_FORBIDDEN", f"Position ({pos.x}, {pos.y}) inside forbidden zone {fb.get('id')}"

        for other in existing_positions:
            if pos.distance_to(other) < min_spacing_m - 1e-6:
                return False, "E_DEPLOY_SPACING", f"Position ({pos.x}, {pos.y}) closer than {min_spacing_m}m to another unit"

        return True, None, None

    @staticmethod
    def validate(
        deployment: DeploymentPlan,
        level: LevelData,
        carry_in: Optional[CarryIn] = None,
    ) -> None:
        cat = level.catalog
        pos_rules = cat.rules.get("positions", {})
        min_spacing_m = float(pos_rules.get("minSpacingM", 100.0))

        # Check unit counts against availableUnits unless carry_in overrides roster
        avail_map: Dict[str, int] = {}
        for au in level.meta.get("availableUnits") or []:
            uid = str(au["unit"])
            avail_map[uid] = avail_map.get(uid, 0) + int(au.get("count", 1))

        has_carry_units = bool(carry_in and carry_in.units)
        counts: Dict[str, int] = {}
        existing_pos: List[Vec2] = []
        used_alt_ids: Set[str] = set()
        alt_by_id = {ap["id"]: ap for ap in (level.deploy.get("alternatePositions") or []) if "id" in ap}

        for idx, pu in enumerate(deployment.units):
            uid = pu.unit_def_id
            try:
                cat.get_player_unit_def(uid)
            except KeyError:
                raise SimError("E_UNKNOWN_REF", f"Unknown unit '{uid}'", f"levels/{level.id}/level.json", f"$.deployment.units[{idx}]")

            counts[uid] = counts.get(uid, 0) + 1
            if not has_carry_units and avail_map and counts[uid] > avail_map.get(uid, 0):
                raise SimError(
                    "E_DEPLOY_QUOTA",
                    f"Unit '{uid}' count {counts[uid]} exceeds available quota {avail_map.get(uid, 0)}",
                    f"levels/{level.id}/level.json",
                    f"$.deployment.units[{idx}]",
                )

            if pu.alternate_position_id is not None:
                if pu.alternate_position_id not in alt_by_id:
                    raise SimError(
                        "E_UNKNOWN_REF",
                        f"Unknown alternatePositionId '{pu.alternate_position_id}'",
                        f"levels/{level.id}/map/deploy.json",
                        f"$.deployment.units[{idx}].alternatePositionId",
                    )
                if pu.alternate_position_id in used_alt_ids:
                    raise SimError(
                        "E_DEPLOY_ALT_OCCUPIED",
                        f"Alternate position '{pu.alternate_position_id}' occupied by multiple units",
                        f"levels/{level.id}/map/deploy.json",
                        f"$.deployment.units[{idx}].alternatePositionId",
                    )
                used_alt_ids.add(pu.alternate_position_id)

            ok, code, msg = DeploymentValidator.is_valid_pos(pu.pos, level, existing_pos, min_spacing_m)
            if not ok:
                raise SimError(code or "E_DEPLOY_INVALID", msg or "Invalid deployment", f"levels/{level.id}/map/deploy.json", f"$.deployment.units[{idx}]")
            existing_pos.append(pu.pos)


class DefaultDeploymentBuilder:
    """Deterministic spiral-ring deployment generator for headless runs and tests."""

    @staticmethod
    def build(level: LevelData, carry_in: Optional[CarryIn] = None) -> DeploymentPlan:
        pos_rules = level.catalog.rules.get("positions", {})
        min_spacing_m = float(pos_rules.get("minSpacingM", 100.0))

        if carry_in is not None and carry_in.units:
            placed: List[PlacedUnit] = []
            existing_pos: List[Vec2] = []
            for idx, cu in enumerate(carry_in.units):
                if cu.get("destroyed", False):
                    continue
                uid = str(cu.get("unitDefId", cu.get("def_id", "")))
                p_raw = cu.get("pos", [10000.0, 10000.0])
                cand = p_raw if isinstance(p_raw, Vec2) else Vec2(float(p_raw[0]), float(p_raw[1]))
                ok, _, _ = DeploymentValidator.is_valid_pos(cand, level, existing_pos, min_spacing_m)
                if not ok:
                    cand = DefaultDeploymentBuilder._find_pos(cand, idx, level, existing_pos, min_spacing_m)
                existing_pos.append(cand)
                placed.append(
                    PlacedUnit(
                        unit_def_id=uid,
                        pos=cand,
                        roster_id=int(cu.get("rosterId", cu.get("roster_id", idx + 1))),
                    )
                )
            return DeploymentPlan(units=placed)

        map_w = float(level.meta.get("map", {}).get("widthM", 20000.0))
        map_h = float(level.meta.get("map", {}).get("heightM", 20000.0))
        center = Vec2(map_w * 0.5, map_h * 0.5)
        if level.structures:
            sx = sum(s["pos"].x for s in level.structures if "pos" in s)
            sy = sum(s["pos"].y for s in level.structures if "pos" in s)
            cnt = sum(1 for s in level.structures if "pos" in s)
            if cnt > 0:
                center = Vec2(sx / cnt, sy / cnt)

        placed_units: List[PlacedUnit] = []
        existing_positions: List[Vec2] = []
        roster_seq = 1
        for au in level.meta.get("availableUnits") or []:
            uid = str(au["unit"])
            count = int(au.get("count", 1))
            for _ in range(count):
                pos = DefaultDeploymentBuilder._find_pos(
                    center, roster_seq - 1, level, existing_positions, min_spacing_m
                )
                existing_positions.append(pos)
                placed_units.append(
                    PlacedUnit(
                        unit_def_id=uid,
                        pos=pos,
                        roster_id=roster_seq,
                    )
                )
                roster_seq += 1
        return DeploymentPlan(units=placed_units)

    @staticmethod
    def _find_pos(
        center: Vec2,
        index: int,
        level: LevelData,
        existing: Sequence[Vec2],
        min_spacing_m: float,
    ) -> Vec2:
        for ring in range(1, 80):
            radius = 800.0 + ring * 350.0
            steps = max(12, ring * 8)
            for s in range(steps):
                angle = 2.0 * math.pi * ((s + index * 5) % steps) / steps
                cand = Vec2(
                    round(center.x + radius * math.cos(angle), 2),
                    round(center.y + radius * math.sin(angle), 2),
                )
                ok, _, _ = DeploymentValidator.is_valid_pos(cand, level, existing, min_spacing_m)
                if ok:
                    return cand
        return center


class SimContext:
    """Mutable execution context shared across all 14 systems in SimWorld."""

    def __init__(
        self,
        level: LevelData,
        config: SimConfig,
        state: SimState,
        events: EventSink,
        terrain: TerrainModel,
        step_sec: float,
        duration_ticks: int,
        enemy_ai_hooks: IEnemyAiHooks,
        wave_spawn_system: WaveSpawnSystem,
        sensor_system: SensorSystem,
    ) -> None:
        self.level = level
        self.config = config
        self.state = state
        self.events = events
        self.terrain = terrain
        self.step_sec = step_sec
        self.duration_ticks = duration_ticks
        self.enemy_ai_hooks = enemy_ai_hooks
        self.wave_spawn_system = wave_spawn_system
        self.sensor_system = sensor_system
        self.rng: SimRandom = state.streams["setup"]

        map_w = float(level.meta.get("map", {}).get("widthM", 20000.0))
        map_h = float(level.meta.get("map", {}).get("heightM", 20000.0))
        self.threat_grid = SpatialGrid(map_w, map_h)
        self.track_grid = SpatialGrid(map_w, map_h)

    @property
    def tick(self) -> int:
        return self.state.tick

    @property
    def time_sec(self) -> float:
        return self.state.tick * self.step_sec

    def rebuild_threat_grid(self) -> None:
        self.threat_grid.rebuild(
            (t.id, t.pos) for t in self.state.threats.alive_list() if t.pos is not None
        )

    def rebuild_track_grid(self) -> None:
        self.track_grid.rebuild(
            (tr.id, tr.pos) for tr in self.state.tracks.alive_list() if tr.pos is not None
        )


class SimWorld:
    """Main simulation orchestrator implementing 00_core.md §§3.2-3.8."""

    def __init__(
        self,
        level: LevelData,
        seed: Union[int, str] = 1,
        config: Optional[SimConfig] = None,
    ) -> None:
        if config is None:
            config = SimConfig()
        self.level = level
        self.config = config
        self.step_sec: float = float(level.catalog.conventions.get("simStepWorldSec", 1.0))

        # Step 1: Locate night definition
        night_obj: Optional[Dict[str, Any]] = None
        for n in level.waves.get("nights", []):
            if int(n.get("night", 0)) == config.night_index:
                night_obj = n
                break
        if night_obj is None:
            raise SimError(
                "E_RANGE",
                f"Night index {config.night_index} not found in level '{level.id}'",
                f"levels/{level.id}/waves.json",
                "$.nights",
            )
        self.night_def = night_obj

        # Step 2: Verify period resolution if night has a distinct date
        night_date = night_obj.get("date")
        if night_date and night_date != level.date and level.resolved_night_index not in (None, config.night_index):
            raise SimError(
                "E_NIGHT_NOT_RESOLVED",
                f"Level '{level.id}' was resolved for date {level.date} (night {level.resolved_night_index}), not night {config.night_index} ({night_date})",
                f"levels/{level.id}/waves.json",
                "$.nights",
            )

        # Step 3: Build default deployment if empty, then validate
        if not config.deployment.units:
            config.deployment = DefaultDeploymentBuilder.build(level, config.carry_in)
        DeploymentValidator.validate(config.deployment, level, config.carry_in)

        # Step 4-5: Parse seed & create SimState with 18 named RNG streams
        if isinstance(seed, str):
            self.seed_int = SimRandom.parse_seed(seed)
            self.seed_str = seed
        else:
            self.seed_int = int(seed)
            self.seed_str = str(seed)

        self.state = SimState(self.seed_int, config.random_override)
        self.events = EventSink(lambda: self.state)

        # Step 6: Build TerrainModel and EnemyAiHooks
        tr_cfg = level.catalog.rules.get("terrain", {})
        tr_rules = TerrainRules(
            los_sample_step_px=float(tr_cfg.get("losSampleStepPx", 0.5)),
            earth_radius_m=(
                float(tr_cfg["earthRadiusM"])
                if tr_cfg.get("earthRadiusM") is not None
                else 6371000.0
            ),
            refraction_k=float(tr_cfg.get("refractionK", 1.3333333333333333)),
            default_antenna_height_m=float(tr_cfg.get("defaultAntennaHeightM", 10.0)),
            horizon_azimuth_bins=int(tr_cfg.get("horizonAzimuthBins", 720)),
        )
        self.terrain = TerrainModel(level.heightmap, tr_rules)

        hooks: IEnemyAiHooks = (
            config.enemy_ai_hooks_override
            if config.enemy_ai_hooks_override is not None
            else EnemyAiHooks()
        )

        dur_sec = float(night_obj.get("durationSec", 3600.0))
        dur_ticks = config.duration_ticks_override or SimTime.sec_to_ticks_ceil(dur_sec, self.step_sec)

        self.wave_spawn_system = WaveSpawnSystem()
        self.enemy_movement_system = EnemyMovementSystem()
        self.sensor_system = SensorSystem()
        self.track_fusion_system = TrackFusionSystem()
        self.ew_system = ElectronicWarfareSystem()
        self.emission_system = EmissionSystem()
        self.engagement_system = EngagementSystem()
        self.interceptor_system = InterceptorSystem()
        self.support_system = ExternalSupportSystem()
        self.impact_system = ImpactSystem()
        self.exposure_system = ExposureSystem()
        self.enemy_intel_system = EnemyIntelSystem()
        self.scoring_system = ScoringSystem()

        self.systems = [
            self.wave_spawn_system,
            self.enemy_movement_system,
            self.sensor_system,
            self.track_fusion_system,
            self.ew_system,
            self.emission_system,
            self.engagement_system,
            self.interceptor_system,
            self.support_system,
            self.impact_system,
            self.exposure_system,
            self.enemy_intel_system,
            self.scoring_system,
        ]

        self.ctx = SimContext(
            level=level,
            config=config,
            state=self.state,
            events=self.events,
            terrain=self.terrain,
            step_sec=self.step_sec,
            duration_ticks=dur_ticks,
            enemy_ai_hooks=hooks,
            wave_spawn_system=self.wave_spawn_system,
            sensor_system=self.sensor_system,
        )

        # Step 7: Instantiate static entities and apply CarryIn
        self._init_static_entities()

        # Step 8-9: Initialize all 13 systems in order using "setup" stream, then CommandStage
        self.ctx.rng = self.state.streams["setup"]
        for sys in self.systems:
            sys.initialize(self.ctx)
        CommandStage.initialize(self.ctx)

        # Step 10: Build spatial grids
        self.ctx.rebuild_threat_grid()
        self.ctx.rebuild_track_grid()

        # Command queue & threat conservation tracking
        self._command_queue: List[SimCommand] = []
        self._next_cmd_seq: int = 1
        self._spawned_threat_ids: Set[int] = set()
        self._terminal_threat_events: Dict[int, List[SimEventType]] = {}

        # Step 11-12: Emit NightStarted at tick = 0 and seal step 0
        self.events.emit(
            SimEventType.NightStarted,
            fields=(config.night_index, dur_ticks, ("i64", self.seed_int)),
            night_index=config.night_index,
            duration_ticks=dur_ticks,
            seed=self.seed_int,
        )
        self._record_threat_events(self.events.current_step)
        self.events.seal_step()

        if self.config.check_invariants:
            self.assert_invariants()

    @classmethod
    def create(
        cls,
        level: LevelData,
        seed: Union[int, str] = 1,
        config: Optional[SimConfig] = None,
    ) -> "SimWorld":
        return cls(level=level, seed=seed, config=config)

    def _init_static_entities(self) -> None:
        cat = self.level.catalog
        carry = self.config.carry_in

        # 1. GridNodes
        type_map = {"source": 0, "substation": 1, "consumer": 2}
        for n_raw in self.level.grid.get("nodes") or []:
            nid_str = str(n_raw["id"])
            pos = n_raw.get("pos") or Vec2(0.0, 0.0)
            gn = GridNode(
                def_id=nid_str,
                pos=pos,
                alt_m=0.0,
                node_type=type_map.get(str(n_raw.get("type", "consumer")), 2),
                off_map_supply=bool(n_raw.get("offMapSupply", False)),
                powered=True,
                destroyed=False,
            )
            self.state.grid_nodes.add(gn)
            self.state.grid_node_id_by_def_id[nid_str] = gn.id

        # 2. Structures
        carry_structs = {str(s.get("id", "")): s for s in (carry.structures if carry else [])}
        for s_raw in self.level.structures:
            sid_str = str(s_raw["id"])
            pos = s_raw.get("pos") or Vec2(0.0, 0.0)
            max_hp = int(s_raw.get("maxHp", s_raw.get("hp", 10)))
            hp = int(s_raw.get("hp", max_hp))
            destroyed = False
            if sid_str in carry_structs:
                cs = carry_structs[sid_str]
                hp = int(cs.get("hp", hp))
                destroyed = bool(cs.get("destroyed", hp <= 0))
                if destroyed:
                    hp = 0
            gn_id = self.state.grid_node_id_by_def_id.get(str(s_raw.get("gridNode", "")), 0)
            st = Structure(
                def_id=sid_str,
                pos=pos,
                alt_m=0.0,
                hp=hp,
                max_hp=max_hp,
                weight=float(s_raw.get("weight", 1.0)),
                radius_m=float(s_raw.get("radiusM", 100.0)),
                grid_node_id=gn_id,
                powered=True,
                destroyed=destroyed,
            )
            self.state.structures.add(st)
            self.state.structure_id_by_def_id[sid_str] = st.id
            if destroyed and gn_id > 0:
                gn_obj = self.state.grid_nodes.try_get(gn_id)
                if gn_obj is not None:
                    gn_obj.destroyed = True

        # 3. Placed player units
        carry_units_by_roster: Dict[int, Dict[str, Any]] = {}
        if carry and carry.units:
            for idx, cu in enumerate(carry.units):
                rid = int(cu.get("rosterId", cu.get("roster_id", idx + 1)))
                carry_units_by_roster[rid] = cu

        conn_rad = float(
            cat.rules.get("civil", {}).get("grid", {}).get("unitConnectRadiusM", 1000.0)
        )
        alt_by_id = {
            ap["id"]: ap
            for ap in (self.level.deploy.get("alternatePositions") or [])
            if "id" in ap
        }

        for idx, pu in enumerate(self.config.deployment.units):
            roster_id = pu.roster_id if pu.roster_id > 0 else (idx + 1)
            cu = carry_units_by_roster.get(roster_id, {})
            if cu.get("destroyed", False):
                continue

            uid = pu.unit_def_id
            ucategory = cat.get_player_unit_category(uid)
            udef = cat.get_player_unit_def(uid)
            gn_id = self._find_nearest_grid_node(pu.pos, conn_rad)

            unsurveyed_alt = False
            if pu.alternate_position_id and pu.alternate_position_id in alt_by_id:
                unsurveyed_alt = not bool(alt_by_id[pu.alternate_position_id].get("surveyed", True))
                self.state.commands.alternate_positions_used[pu.alternate_position_id] = roster_id

            new_pos_pen = bool(pu.first_night_at_new_position or unsurveyed_alt)
            exp_init = float(cu.get("exposure", 0.0))
            light_dmg = bool(cu.get("lightDamaged", False))
            dmg_mult = 0.8 if light_dmg else 1.0
            eq_ew = list((pu.settings or {}).get("equipmentEwIds") or [])

            if ucategory == PlayerUnitCategory.Fire:
                consec = int(cu.get("crewConsecutiveNights", 1))
                fu = FireUnit(
                    def_id=uid,
                    pos=pu.pos,
                    alt_m=0.0,
                    deploy_state=UnitDeployState.Deployed,
                    exposure=exp_init,
                    exposure_peak=exp_init,
                    grid_node_id=gn_id,
                    powered=True,
                    new_position_penalty=new_pos_pen,
                    equipment_ew_ids=eq_ew,
                    damage_efficiency_mult=dmg_mult,
                    light_damaged=light_dmg,
                    placement=pu,
                    roster_id=roster_id,
                    radar_destroyed=bool(cu.get("radarDestroyed", False)),
                    launchers_lost=int(cu.get("launchersLost", 0)),
                    crew_consecutive_nights=consec,
                    ace_crew=bool(cu.get("aceCrew", consec >= 3)),
                )
                self.state.fire_units.add(fu)
            elif ucategory == PlayerUnitCategory.Sensor:
                su = SensorUnit(
                    def_id=uid,
                    pos=pu.pos,
                    alt_m=0.0,
                    deploy_state=UnitDeployState.Deployed,
                    exposure=exp_init,
                    exposure_peak=exp_init,
                    grid_node_id=gn_id,
                    powered=True,
                    new_position_penalty=new_pos_pen,
                    equipment_ew_ids=eq_ew,
                    damage_efficiency_mult=dmg_mult,
                    light_damaged=light_dmg,
                    placement=pu,
                    roster_id=roster_id,
                    automatic=False,
                )
                self.state.sensors.add(su)
            elif ucategory == PlayerUnitCategory.Ew:
                lure_raw = (pu.settings or {}).get("lurePoint")
                lure = (
                    Vec2(float(lure_raw[0]), float(lure_raw[1]))
                    if isinstance(lure_raw, list) and len(lure_raw) == 2
                    else None
                )
                eu = EwUnit(
                    def_id=uid,
                    pos=pu.pos,
                    alt_m=0.0,
                    deploy_state=UnitDeployState.Deployed,
                    exposure=exp_init,
                    exposure_peak=exp_init,
                    grid_node_id=gn_id,
                    powered=True,
                    new_position_penalty=new_pos_pen,
                    equipment_ew_ids=eq_ew,
                    damage_efficiency_mult=dmg_mult,
                    light_damaged=light_dmg,
                    placement=pu,
                    roster_id=roster_id,
                    lure_point=lure,
                )
                self.state.ew_units.add(eu)
            elif ucategory == PlayerUnitCategory.Deception:
                du = DeceptionUnit(
                    def_id=uid,
                    pos=pu.pos,
                    alt_m=0.0,
                    deploy_state=UnitDeployState.Deployed,
                    exposure=exp_init,
                    exposure_peak=exp_init,
                    grid_node_id=gn_id,
                    powered=True,
                    new_position_penalty=new_pos_pen,
                    equipment_ew_ids=eq_ew,
                    damage_efficiency_mult=dmg_mult,
                    light_damaged=light_dmg,
                    placement=pu,
                    roster_id=roster_id,
                )
                self.state.deception_units.add(du)

        # 4. Initialize ammo_pool, per_level_used, civil responsiveness from level / carry_in
        if carry and carry.ammo_pool is not None:
            self.state.engagement.ammo_pool = dict(carry.ammo_pool)
        else:
            for aq in self.level.meta.get("ammoQuota") or []:
                wid = str(aq["weapon"])
                self.state.engagement.ammo_pool[wid] = int(aq.get("Initial", aq.get("initial", aq.get("quota", 0))))

        if carry and carry.per_level_used:
            self.state.engagement.per_level_used = dict(carry.per_level_used)

        if carry and carry.alert_responsiveness is not None:
            self.state.civil.responsiveness = float(carry.alert_responsiveness)

    def _find_nearest_grid_node(self, pos: Vec2, max_radius: float) -> int:
        best_id = 0
        best_d = max_radius + 1e-9
        for gn in self.state.grid_nodes.alive_list():
            if gn.pos is None:
                continue
            d = pos.distance_to(gn.pos)
            if d <= best_d:
                best_d = d
                best_id = gn.id
        return best_id

    def submit_command(self, cmd: SimCommand) -> None:
        """Enqueue a player/bot command for execution at cmd.effective_tick (or tick + 1)."""
        if cmd.effective_tick <= self.state.tick:
            cmd.effective_tick = self.state.tick + 1
        if cmd.seq <= 0:
            cmd.seq = self._next_cmd_seq
            self._next_cmd_seq += 1
        else:
            self._next_cmd_seq = max(self._next_cmd_seq, cmd.seq + 1)
        self._command_queue.append(cmd)
        self._command_queue.sort(key=lambda c: (c.effective_tick, c.seq))

    enqueue_command = submit_command

    @property
    def is_ended(self) -> bool:
        return self.state.end_request is not None

    @property
    def is_finished(self) -> bool:
        return self.state.end_request is not None

    def step(self) -> List[SimEvent]:
        """Execute 1 world-second tick across Stage 0 + Systems 1..14 (00_core.md §3.3)."""
        if self.is_ended:
            raise SimError("E_ALREADY_ENDED", "Cannot step SimWorld after night has ended")

        # 1. Advance tick
        self.state.tick += 1
        tick = self.state.tick

        # 2. Stage 0: Command dispatch + DeploymentStage + ChoiceStage + StoryStage
        due_cmds: List[SimCommand] = []
        rem_cmds: List[SimCommand] = []
        for c in self._command_queue:
            if c.effective_tick <= tick:
                due_cmds.append(c)
            else:
                rem_cmds.append(c)
        self._command_queue = rem_cmds

        self.ctx.rng = self.state.streams["command"]
        CommandStage.execute(self.ctx, due_cmds)

        # 3. Systems 1..13 in strict order
        for sys in self.systems:
            self.ctx.rng = self.state.streams[sys.stream_name]
            sys.execute(self.ctx)
            if sys.order == 2:
                self.ctx.rebuild_threat_grid()
            elif sys.order == 4:
                self.ctx.rebuild_track_grid()

        # 4. Emit NightEnded if end_request was triggered this tick
        if self.state.end_request is not None:
            er = self.state.end_request
            self.events.emit(
                SimEventType.NightEnded,
                fields=(int(er.outcome), int(er.reason), er.detail),
                outcome=er.outcome,
                reason=er.reason,
                detail=er.detail,
            )

        # 5. System 14: EventLog seal_step()
        self._record_threat_events(self.events.current_step)
        self.events.seal_step()
        step_events = list(self.events.previous_step)

        # 6. Compact all entity stores
        for store in self.state.all_stores:
            store.compact()

        # 7. Check runtime invariants if enabled
        if self.config.check_invariants:
            self.assert_invariants()

        return step_events

    def _record_threat_events(self, events: Sequence[SimEvent]) -> None:
        for ev in events:
            if ev.type == SimEventType.ThreatSpawned:
                tid = int(ev.data.get("threat_id", ev.fields[0] if ev.fields else 0))
                self._spawned_threat_ids.add(tid)
            elif ev.type == SimEventType.MunitionReleased:
                tid = int(ev.data.get("threat_id", ev.fields[1] if len(ev.fields) > 1 else 0))
                self._spawned_threat_ids.add(tid)
            elif ev.type == SimEventType.ThreatExited:
                tid = int(ev.data.get("threat_id", ev.fields[0] if ev.fields else 0))
                self._terminal_threat_events.setdefault(tid, []).append(ev.type)
            elif ev.type == SimEventType.EwLinkCut and ev.data.get("outcome") == "crash":
                tid = int(ev.data.get("threat_id", ev.fields[1] if len(ev.fields) > 1 else 0))
                self._terminal_threat_events.setdefault(tid, []).append(ev.type)
            elif ev.type == SimEventType.InterceptResolved and ev.data.get("hit") is True:
                tid = int(ev.data.get("threat_id", ev.fields[3] if len(ev.fields) > 3 else 0))
                self._terminal_threat_events.setdefault(tid, []).append(ev.type)
            elif ev.type == SimEventType.ThreatImpacted:
                tid = int(ev.data.get("threat_id", ev.fields[0] if ev.fields else 0))
                self._terminal_threat_events.setdefault(tid, []).append(ev.type)

    def run_to_end(
        self,
        bot_fn: Optional[Callable[["SimWorld"], Sequence[SimCommand]]] = None,
    ) -> NightResult:
        while not self.is_ended:
            if bot_fn is not None:
                cmds = bot_fn(self)
                for c in cmds:
                    self.submit_command(c)
            self.step()
        return self.build_result()

    def build_result(self) -> NightResult:
        return ScoringSystem.build_result(self.ctx, self.seed_str)

    def assert_invariants(self) -> None:
        """Verify all 10 runtime invariants (00_core.md §3.8)."""
        # 1. Tick non-negative
        if self.state.tick < 0:
            raise AssertionError(f"Invariant 1 failed: tick={self.state.tick}")

        # 2. All EntityStores strictly ordered by ascending ID and no dead items after compact
        for store in self.state.all_stores:
            ids = [e.id for e in store]
            if ids != sorted(ids) or len(ids) != len(set(ids)):
                raise AssertionError(f"Invariant 2 failed: {store.kind.name} IDs not strictly increasing")
            if any(not e.alive for e in store):
                raise AssertionError(f"Invariant 2 failed: {store.kind.name} contains uncompacted dead entities")

        # 3. Finite coordinates and non-negative altitudes on all Threats
        for th in self.state.threats.alive_list():
            if th.pos is None or not (math.isfinite(th.pos.x) and math.isfinite(th.pos.y)):
                raise AssertionError(f"Invariant 3 failed: non-finite pos on threat {th.id}")
            if th.alt_m is None or not math.isfinite(th.alt_m) or th.alt_m < -1e-6:
                raise AssertionError(f"Invariant 3 failed: invalid alt_m={th.alt_m} on threat {th.id}")

        # 4. Alive threats outside ImpactSystem must not remain in Arrived phase after step
        for th in self.state.threats.alive_list():
            if th.phase.name == "Arrived":
                raise AssertionError(f"Invariant 4 failed: threat {th.id} still in Arrived phase after step")

        # 5. Alive tracks have valid quality and reference either a live threat or phantom_key > 0
        for tr in self.state.tracks.alive_list():
            if tr.threat_id <= 0 and tr.phantom_key <= 0:
                raise AssertionError(f"Invariant 5 failed: track {tr.id} has neither threat_id nor phantom_key")

        # 6. Weapon launcher rounds in [0, max_rounds]
        for fu in self.state.fire_units.alive_list():
            for wslot in fu.weapons:
                for ln in wslot.launchers:
                    if not (0 <= ln.rounds <= ln.max_rounds):
                        raise AssertionError(
                            f"Invariant 6 failed: unit {fu.id} weapon {wslot.weapon_id} rounds={ln.rounds}/{ln.max_rounds}"
                        )

        # 7. Exposure in [0, 100] and CP >= 0
        for store in (self.state.fire_units, self.state.sensors, self.state.ew_units, self.state.deception_units):
            for u in store.alive_list():
                if not (-1e-9 <= u.exposure <= 100.0 + 1e-9):
                    raise AssertionError(f"Invariant 7 failed: unit {u.id} exposure={u.exposure}")
        if self.state.commands.command_points < 0:
            raise AssertionError(f"Invariant 7 failed: negative CP={self.state.commands.command_points}")

        # 8. Structure HP in [0, max_hp]
        for st in self.state.structures.alive_list():
            if not (0 <= st.hp <= st.max_hp):
                raise AssertionError(f"Invariant 8 failed: structure {st.id} hp={st.hp}/{st.max_hp}")

        # 9. Threat terminal event conservation:
        #    Every spawned threat that is still alive has 0 terminal events;
        #    every spawned threat that was removed has AT LEAST 1 and AT MOST 1 terminal event.
        alive_ids = {t.id for t in self.state.threats.alive_list()}
        for tid in self._spawned_threat_ids:
            terms = self._terminal_threat_events.get(tid, [])
            if tid in alive_ids:
                if len(terms) != 0:
                    raise AssertionError(
                        f"Invariant 9 failed: alive threat {tid} has terminal events {terms}"
                    )
            else:
                if len(terms) != 1:
                    raise AssertionError(
                        f"Invariant 9 failed: removed threat {tid} has {len(terms)} terminal events {terms}"
                    )

        # 10. State hash determinism (at init and end of night)
        if self.state.tick == 0 or self.is_ended:
            if self.state.compute_hash() != self.state.compute_hash():
                raise AssertionError("Invariant 10 failed: compute_hash() is non-deterministic")


class SimSnapshot:
    """In-memory deep copy snapshot of SimWorld for branching/testing (00_core.md §3.6)."""

    @staticmethod
    def capture(world: SimWorld) -> Dict[str, Any]:
        st_copy = copy.deepcopy(world.state)
        st_copy.rebind_stores()
        return {
            "state": st_copy,
            "events_outbox": copy.deepcopy(world.events._outbox),
            "events_prev": copy.deepcopy(world.events.previous_step),
            "command_queue": copy.deepcopy(world._command_queue),
            "next_cmd_seq": world._next_cmd_seq,
            "spawned_threat_ids": copy.deepcopy(world._spawned_threat_ids),
            "terminal_threat_events": copy.deepcopy(world._terminal_threat_events),
        }

    @staticmethod
    def restore(world: SimWorld, snap: Dict[str, Any]) -> None:
        world.state = copy.deepcopy(snap["state"])
        world.state.rebind_stores()
        world.events = EventSink(lambda: world.state)
        world.events._outbox = copy.deepcopy(snap["events_outbox"])
        world.events.previous_step = copy.deepcopy(snap["events_prev"])
        world.ctx.state = world.state
        world.ctx.events = world.events
        world._command_queue = copy.deepcopy(snap["command_queue"])
        world._next_cmd_seq = int(snap["next_cmd_seq"])
        world._spawned_threat_ids = copy.deepcopy(snap["spawned_threat_ids"])
        world._terminal_threat_events = copy.deepcopy(snap["terminal_threat_events"])
        world.ctx.rebuild_threat_grid()
        world.ctx.rebuild_track_grid()


class ReplayRunner:
    """Re-executes a recorded command stream and verifies bit-identical hashes."""

    @staticmethod
    def run_replay(
        level: LevelData,
        seed: Union[int, str],
        config: SimConfig,
        commands: Sequence[SimCommand],
    ) -> NightResult:
        cfg_copy = copy.deepcopy(config)
        world = SimWorld.create(level, seed=seed, config=cfg_copy)
        for c in commands:
            world.submit_command(copy.deepcopy(c))
        return world.run_to_end()
