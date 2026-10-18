"""Dynamic entities, EntityStore, singleton state components, events, commands, and SimState (00-04)."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, Generic, List, Optional, Sequence, Tuple, TypeVar
from .core import FNV_OFFSET_BASIS, SimRandom, StateHasher, Vec2


class EntityKind(IntEnum):
    GridNode = 0
    Structure = 1
    FireUnit = 2
    SensorUnit = 3
    EwUnit = 4
    DeceptionUnit = 5
    Threat = 6
    Track = 7
    Interceptor = 8
    SupportAsset = 9
    Debris = 10
    ChoiceRequest = 11


class PlayerUnitCategory(IntEnum):
    Fire = 0
    Sensor = 1
    Ew = 2
    Deception = 3


class UnitDeployState(IntEnum):
    Deployed = 0
    Packing = 1
    Packed = 2
    Moving = 3
    Deploying = 4


class TargetTag(IntEnum):
    UAV = 0
    JET_UAV = 1
    DECOY = 2
    CM = 3
    SCM = 4
    BM = 5
    HBM = 6
    GB = 7
    HELI = 8
    AC_LOW = 9
    AC_HIGH = 10


class AccuracyTier(IntEnum):
    A = 0
    B = 1
    C = 2
    D = 3


class TrackQuality(IntEnum):
    Vague = 0
    Approximate = 1
    Precise = 2


class ThreatKind(IntEnum):
    Munition = 0
    Platform = 1


class ThreatPhase(IntEnum):
    Ingress = 0
    Egress = 1
    Holding = 2
    Arrived = 3


class MotionProfile(IntEnum):
    Linear = 0
    Parabolic = 1


class PathEndAction(IntEnum):
    Arrive = 0
    Exit = 1
    Hold = 2


class ThreatTargetKind(IntEnum):
    Structure = 0
    PlayerUnit = 1
    AimPoint = 2


class ThreatExitReason(IntEnum):
    DecoyPathEnd = 0
    EgressComplete = 1
    LinkCutReturn = 2


class AiTag(IntEnum):
    Probe = 0
    Suppress = 1
    Hunt = 2
    Bypass = 3
    Saturate = 4


class NightOutcome(IntEnum):
    Survived = 0
    Defeated = 1


class NightEndReason(IntEnum):
    DurationElapsed = 0
    AllClear = 1
    DefeatCondition = 2


class SimCommandType(IntEnum):
    Noop = 0
    SetEmissionPolicy = 200
    SectorEmissionOverride = 201
    SetEngagementRule = 300
    CallSupport = 301
    SetAirRaidAlert = 302
    SetFighterZone = 303
    DeployUnit = 400
    PackUnit = 401
    MoveUnit = 402
    RelocateUnit = 403
    AnswerChoice = 404


class CommandRejectReason(IntEnum):
    UnknownEntity = 0
    WrongEntityKind = 1
    InvalidState = 2
    InvalidArgument = 3
    NotAvailable = 4
    NoCommandPoints = 5
    NotImplemented = 6
    NoSortiesLeft = 300
    InRiskZone = 301
    AirbaseUnavailable = 302


class SimEventType(IntEnum):
    NightStarted = 0
    NightEnded = 1
    CommandApplied = 2
    CommandRejected = 3
    WaveStarted = 100
    ThreatSpawned = 101
    MunitionReleased = 102
    ThreatArrived = 103
    ThreatExited = 104
    EarlyWarning = 200
    TrackCreated = 201
    TrackQualityChanged = 202
    TrackLost = 203
    DecoyIdentified = 204
    EmitterSwitched = 205
    ArmThreatDetected = 206
    EwDiverted = 207
    EwLinkCut = 208
    ExposureThresholdCrossed = 209
    DeceptionTriggered = 210
    InterceptorLaunched = 300
    GunFired = 301
    InterceptResolved = 302
    InterceptorExpired = 303
    EngagementHeld = 304
    AmmoDepleted = 305
    ThreatImpacted = 306
    StructureDamaged = 307
    StructureDestroyed = 308
    PlayerUnitDamaged = 309
    PlayerUnitDestroyed = 310
    DebrisFell = 311
    GridPowerChanged = 312
    AirRaidAlertChanged = 313
    SupportRequested = 314
    SupportRefused = 315
    SupportArrived = 316
    SupportEnded = 317
    KnownTargetAdded = 400
    KnownTargetRemoved = 401
    ChoiceRequested = 402
    ChoiceResolved = 403
    CommandPointsChanged = 404
    UnitDeployStateChanged = 405
    StoryEventFired = 406
    DialogueShown = 407
    EnemyGroupsReleased = 408


class IdAllocator:
    def __init__(self, next_id: int = 1):
        self.next_id = next_id

    def allocate(self) -> int:
        if self.next_id >= 0x7FFFFFFF:
            raise RuntimeError("Entity ID overflow")
        cid = self.next_id
        self.next_id += 1
        return cid


@dataclass
class Entity:
    id: int = 0
    alive: bool = True
    created_tick: int = 0
    removed_tick: int = -1
    def_id: Optional[str] = ""
    pos: Optional[Vec2] = field(default_factory=lambda: Vec2(0.0, 0.0))
    alt_m: Optional[float] = 0.0

    def write_hash(self, h: StateHasher) -> None:
        pass


T = TypeVar("T", bound=Entity)


class EntityStore(Generic[T]):
    """Ordered entity store sorted by monotonically increasing ID (00_core.md §2.2.2)."""

    def __init__(self, kind: EntityKind, ids: IdAllocator, state_ref: Callable[[], int]):
        self.kind = kind
        self._ids = ids
        self._tick_fn = state_ref
        self._items: List[T] = []

    @property
    def count(self) -> int:
        return len(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> T:
        return self._items[index]

    def count_alive(self) -> int:
        return sum(1 for e in self._items if e.alive)

    def alive_list(self) -> List[T]:
        return [e for e in self._items if e.alive]

    def add(self, entity: T) -> T:
        entity.id = self._ids.allocate()
        entity.alive = True
        entity.created_tick = self._tick_fn()
        entity.removed_tick = -1
        self._items.append(entity)
        return entity

    def _find_index(self, entity_id: int) -> int:
        lo, hi = 0, len(self._items) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            mid_id = self._items[mid].id
            if mid_id == entity_id:
                return mid
            if mid_id < entity_id:
                lo = mid + 1
            else:
                hi = mid - 1
        return -1

    def try_get(self, entity_id: int) -> Optional[T]:
        idx = self._find_index(entity_id)
        if idx < 0:
            return None
        e = self._items[idx]
        return e if e.alive else None

    def get(self, entity_id: int) -> T:
        e = self.try_get(entity_id)
        if e is None:
            raise KeyError(f"Entity {entity_id} not found or removed in {self.kind.name}")
        return e

    def try_get_including_removed(self, entity_id: int) -> Optional[T]:
        idx = self._find_index(entity_id)
        return self._items[idx] if idx >= 0 else None

    def remove(self, entity_id: int) -> None:
        idx = self._find_index(entity_id)
        if idx >= 0 and self._items[idx].alive:
            self._items[idx].alive = False
            self._items[idx].removed_tick = self._tick_fn()

    def compact(self) -> None:
        self._items = [e for e in self._items if e.alive]


@dataclass
class RelocationOrder:
    dest: Vec2
    alternate_position_id: Optional[str] = None
    pack_end_tick: int = -1
    move_end_tick: int = -1
    deploy_end_tick: int = -1
    scouted_on_departure: bool = False
    is_emergency_relocate: bool = False


@dataclass
class EmitterControl:
    policy_id: str = "continuous"
    on: bool = True
    duty_on_sec: float = 60.0
    duty_off_sec: float = 60.0
    cycle_anchor_sec: float = 0.0
    on_arm_incoming: int = 0  # ArmResponse enum
    after_firing: int = 0     # AfterFiringAction enum
    neighbor_takeover: bool = False
    fc_mode: int = 0          # FireControlMode: Off=0,Active=1,ForcedSilence=2,ForcedOn=3
    fc_window_until_sec: float = 0.0
    forced_silence_until_sec: float = 0.0
    sector_override: int = 0  # None=0, Silence=1, ForceOn=2
    arm_warned_track_ids: List[int] = field(default_factory=list)


@dataclass
class PlayerUnitEntity(Entity):
    deploy_state: UnitDeployState = UnitDeployState.Deployed
    deploy_phase_end_tick: int = -1
    relocation: Optional[RelocationOrder] = None
    exposure: float = 0.0
    exposure_peak: float = 0.0
    grid_node_id: int = 0
    powered: bool = True
    emitter: Optional[EmitterControl] = None
    new_position_penalty: bool = False
    pending_relocation_alt_id: Optional[str] = None
    equipment_ew_ids: List[str] = field(default_factory=list)
    damage_efficiency_mult: float = 1.0
    suspended_until_sec: float = 0.0
    light_damaged: bool = False
    placement: Any = None
    roster_id: int = 0

    def write_common_hash(self, h: StateHasher) -> None:
        h.write_enum(self.deploy_state)
        h.write_i32(self.deploy_phase_end_tick)
        h.write_bool(self.relocation is not None)
        if self.relocation is not None:
            h.write_vec2(self.relocation.dest)
            h.write_str(self.relocation.alternate_position_id)
            h.write_i32(self.relocation.pack_end_tick)
            h.write_i32(self.relocation.move_end_tick)
            h.write_i32(self.relocation.deploy_end_tick)
            h.write_bool(self.relocation.scouted_on_departure)
            h.write_bool(self.relocation.is_emergency_relocate)
        h.write_f64(self.exposure)
        h.write_f64(self.exposure_peak)
        h.write_i32(self.grid_node_id)
        h.write_bool(self.powered)
        h.write_bool(self.emitter is not None)
        if self.emitter is not None:
            h.write_str(self.emitter.policy_id)
            h.write_bool(self.emitter.on)
            h.write_f64(self.emitter.duty_on_sec)
            h.write_f64(self.emitter.duty_off_sec)
            h.write_f64(self.emitter.cycle_anchor_sec)
            h.write_enum(self.emitter.on_arm_incoming)
            h.write_enum(self.emitter.after_firing)
            h.write_bool(self.emitter.neighbor_takeover)
            h.write_enum(self.emitter.fc_mode)
            h.write_f64(self.emitter.fc_window_until_sec)
            h.write_f64(self.emitter.forced_silence_until_sec)
            h.write_enum(self.emitter.sector_override)
            h.write_i32(len(self.emitter.arm_warned_track_ids))
            for tid in self.emitter.arm_warned_track_ids:
                h.write_i32(tid)
        h.write_bool(self.new_position_penalty)
        h.write_str(self.pending_relocation_alt_id)
        h.write_i32(len(self.equipment_ew_ids))
        for eq in self.equipment_ew_ids:
            h.write_str(eq)
        h.write_f64(self.damage_efficiency_mult)
        h.write_f64(self.suspended_until_sec)
        h.write_bool(self.light_damaged)


@dataclass
class GridNode(Entity):
    node_type: int = 0
    off_map_supply: bool = False
    powered: bool = True
    destroyed: bool = False

    def write_hash(self, h: StateHasher) -> None:
        h.write_enum(self.node_type)
        h.write_bool(self.off_map_supply)
        h.write_bool(self.powered)
        h.write_bool(self.destroyed)


@dataclass
class Structure(Entity):
    hp: int = 100
    max_hp: int = 100
    weight: float = 1.0
    radius_m: float = 50.0
    grid_node_id: int = 0
    powered: bool = True
    destroyed: bool = False

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(self.hp)
        h.write_i32(self.max_hp)
        h.write_f64(self.weight)
        h.write_f64(self.radius_m)
        h.write_i32(self.grid_node_id)
        h.write_bool(self.powered)
        h.write_bool(self.destroyed)


@dataclass
class LauncherState:
    rounds: int = 0
    max_rounds: int = 0
    reload_until_sec: float = 0.0
    destroyed: bool = False


@dataclass
class WeaponSlotState:
    weapon_id: str = ""
    rule: int = 0  # EngagementRule: Any=0, BallisticOnly=1, HoldFire=2, HighValueOnly=3
    next_shot_sec: float = 0.0
    continuous_fire_sec: float = 0.0
    cooldown_until_sec: float = 0.0
    first_shot_ready_sec: Dict[int, float] = field(default_factory=dict)
    launchers: List[LauncherState] = field(default_factory=list)
    depleted_emitted: bool = False


@dataclass
class FireUnit(PlayerUnitEntity):
    weapons: List[WeaponSlotState] = field(default_factory=list)
    radar_destroyed: bool = False
    launchers_lost: int = 0
    crew_consecutive_nights: int = 1
    ace_crew: bool = False
    kills_tonight: int = 0

    def write_hash(self, h: StateHasher) -> None:
        self.write_common_hash(h)
        h.write_i32(len(self.weapons))
        for w in self.weapons:
            h.write_str(w.weapon_id)
            h.write_enum(w.rule)
            h.write_f64(w.next_shot_sec)
            h.write_f64(w.continuous_fire_sec)
            h.write_f64(w.cooldown_until_sec)
            h.write_i32(len(w.first_shot_ready_sec))
            for k in sorted(w.first_shot_ready_sec.keys()):
                h.write_i32(k)
                h.write_f64(w.first_shot_ready_sec[k])
            h.write_i32(len(w.launchers))
            for ln in w.launchers:
                h.write_i32(ln.rounds)
                h.write_i32(ln.max_rounds)
                h.write_f64(ln.reload_until_sec)
                h.write_bool(ln.destroyed)
            h.write_bool(w.depleted_emitted)
        h.write_bool(self.radar_destroyed)
        h.write_i32(self.launchers_lost)
        h.write_i32(self.crew_consecutive_nights)
        h.write_bool(self.ace_crew)
        h.write_i32(self.kills_tonight)


@dataclass
class SensorUnit(PlayerUnitEntity):
    automatic: bool = False
    night_aids: List[int] = field(default_factory=list)
    horizon_profile: Any = None  # cached, not hashed

    def write_hash(self, h: StateHasher) -> None:
        self.write_common_hash(h)
        h.write_bool(self.automatic)
        h.write_i32(len(self.night_aids))
        for na in self.night_aids:
            h.write_enum(na)


@dataclass
class EwUnit(PlayerUnitEntity):
    lure_point: Optional[Vec2] = None

    def write_hash(self, h: StateHasher) -> None:
        self.write_common_hash(h)
        h.write_opt_vec2(self.lure_point)


@dataclass
class DeceptionUnit(PlayerUnitEntity):
    seen_through: bool = False
    nights_at_current_pos: int = 1
    recon_checked_threat_ids: List[int] = field(default_factory=list)
    attracted_threat_ids: List[int] = field(default_factory=list)

    def write_hash(self, h: StateHasher) -> None:
        self.write_common_hash(h)
        h.write_bool(self.seen_through)
        h.write_i32(self.nights_at_current_pos)
        h.write_i32(len(self.recon_checked_threat_ids))
        for tid in sorted(self.recon_checked_threat_ids):
            h.write_i32(tid)
        h.write_i32(len(self.attracted_threat_ids))
        for tid in sorted(self.attracted_threat_ids):
            h.write_i32(tid)


@dataclass
class PendingRelease:
    loadout_index: int
    munition_id: str
    count: int
    at_arc_m: float
    done: bool = False


@dataclass
class Threat(Entity):
    # 01 §2.2 (32 fields)
    kind: ThreatKind = ThreatKind.Munition
    tag: Optional[TargetTag] = None
    vel_mps: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    vert_speed_mps: float = 0.0
    phase: ThreatPhase = ThreatPhase.Ingress
    wave_id: str = ""
    entry_id: str = ""
    parent_threat_id: int = 0
    spawn_at_sec: float = 0.0
    target_kind: ThreatTargetKind = ThreatTargetKind.Structure
    target_pos: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    target_structure_id: int = 0
    target_unit_id: int = 0
    homing_unit_id: int = 0
    profile_ready: bool = False
    profile: MotionProfile = MotionProfile.Linear
    path: List[Vec2] = field(default_factory=list)
    path_cum_m: List[float] = field(default_factory=list)  # derived cache, not hashed
    path_length_m: float = 0.0                             # derived cache, not hashed
    path_version: int = 1
    path_end: PathEndAction = PathEndAction.Arrive
    anchor_sec: float = 0.0
    anchor_arc_m: float = 0.0
    path_arc_m: float = 0.0
    speed_mps: float = 0.0
    terminal_speed_mps: float = 0.0
    terminal_start_arc_m: float = 0.0
    start_alt_m: float = 0.0
    end_alt_m: float = 0.0
    last_update_sec: float = 0.0
    arrived_at_sec: float = -1.0
    turn_arc_m: float = -1.0
    releases: List[PendingRelease] = field(default_factory=list)
    ingress_path: List[Vec2] = field(default_factory=list)
    # 02 §2.6 (11 fields)
    ew_nav: int = 0  # None=0, CheckedNoEffect=1, Jammed=2
    ew_extra_offset_m: float = 0.0
    accuracy_tier_drop: int = 0
    ew_pull: int = 0  # None=0, CheckedNoEffect=1, Pulled=2
    ew_divert_pos: Optional[Vec2] = None
    national_spoof: int = 0  # None=0, CheckedNoEffect=1, Degraded=2, Diverted=3
    link_cut_state: int = 0  # Intact=0, CheckedNoEffect=1, Hovering=2, Resolved=3
    link_cut_at_tick: int = -1
    arm_initial_dist_m: float = 0.0
    arm_hit_prob_mult: float = 1.0
    ew_ever_covered: bool = False
    # 03 §2.4 (4 fields)
    max_track_quality: Optional[TrackQuality] = None
    shots_taken: int = 0
    held_mask: int = 0
    decoy_drained: bool = False

    def write_hash(self, h: StateHasher) -> None:
        h.write_enum(self.kind)
        h.write_opt_i32(int(self.tag) if self.tag is not None else None)
        h.write_vec2(self.vel_mps)
        h.write_f64(self.vert_speed_mps)
        h.write_enum(self.phase)
        h.write_str(self.wave_id)
        h.write_str(self.entry_id)
        h.write_i32(self.parent_threat_id)
        h.write_f64(self.spawn_at_sec)
        h.write_enum(self.target_kind)
        h.write_vec2(self.target_pos)
        h.write_i32(self.target_structure_id)
        h.write_i32(self.target_unit_id)
        h.write_i32(self.homing_unit_id)
        h.write_bool(self.profile_ready)
        h.write_enum(self.profile)
        h.write_i32(len(self.path))
        for pt in self.path:
            h.write_vec2(pt)
        h.write_i32(self.path_version)
        h.write_enum(self.path_end)
        h.write_f64(self.anchor_sec)
        h.write_f64(self.anchor_arc_m)
        h.write_f64(self.path_arc_m)
        h.write_f64(self.speed_mps)
        h.write_f64(self.terminal_speed_mps)
        h.write_f64(self.terminal_start_arc_m)
        h.write_f64(self.start_alt_m)
        h.write_f64(self.end_alt_m)
        h.write_f64(self.last_update_sec)
        h.write_f64(self.arrived_at_sec)
        h.write_f64(self.turn_arc_m)
        h.write_i32(len(self.releases))
        for r in self.releases:
            h.write_i32(r.loadout_index)
            h.write_str(r.munition_id)
            h.write_i32(r.count)
            h.write_f64(r.at_arc_m)
            h.write_bool(r.done)
        h.write_i32(len(self.ingress_path))
        for pt in self.ingress_path:
            h.write_vec2(pt)
        # 02 fields
        h.write_enum(self.ew_nav)
        h.write_f64(self.ew_extra_offset_m)
        h.write_i32(self.accuracy_tier_drop)
        h.write_enum(self.ew_pull)
        h.write_opt_vec2(self.ew_divert_pos)
        h.write_enum(self.national_spoof)
        h.write_enum(self.link_cut_state)
        h.write_i32(self.link_cut_at_tick)
        h.write_f64(self.arm_initial_dist_m)
        h.write_f64(self.arm_hit_prob_mult)
        h.write_bool(self.ew_ever_covered)
        # 03 fields
        h.write_opt_i32(int(self.max_track_quality) if self.max_track_quality is not None else None)
        h.write_i32(self.shots_taken)
        h.write_i32(self.held_mask)
        h.write_bool(self.decoy_drained)


@dataclass
class Track(Entity):
    threat_id: int = 0
    phantom_key: int = 0
    quality: TrackQuality = TrackQuality.Vague
    tag: Optional[TargetTag] = None
    vel_mps: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    uncertainty_radius_m: float = 0.0
    cued: bool = False
    classified: bool = False
    precise_first_tick: int = -1
    decoy_check_done: bool = False
    identified_as_decoy: bool = False
    last_seen_tick: int = 0
    source_mask: int = 0

    def __post_init__(self) -> None:
        self.def_id = ""

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(self.threat_id)
        h.write_i32(self.phantom_key)
        h.write_enum(self.quality)
        h.write_opt_i32(int(self.tag) if self.tag is not None else None)
        h.write_vec2(self.vel_mps)
        h.write_f64(self.uncertainty_radius_m)
        h.write_bool(self.cued)
        h.write_bool(self.classified)
        h.write_i32(self.precise_first_tick)
        h.write_bool(self.decoy_check_done)
        h.write_bool(self.identified_as_decoy)
        h.write_i32(self.last_seen_tick)
        h.write_i32(self.source_mask)


@dataclass
class Interceptor(Entity):
    fire_unit_id: int = 0
    support_asset_id: int = 0
    launcher_index: int = 0
    weapon_id: str = ""
    track_id: int = 0
    threat_id: int = 0
    target_path_version: int = 1
    launch_sec: float = 0.0
    intercept_sec: float = 0.0
    launch_pos: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    intercept_pos: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    intercept_alt_m: float = 0.0
    speed_mps: float = 0.0
    hit_prob: float = 0.0

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(self.fire_unit_id)
        h.write_i32(self.support_asset_id)
        h.write_i32(self.launcher_index)
        h.write_str(self.weapon_id)
        h.write_i32(self.track_id)
        h.write_i32(self.threat_id)
        h.write_i32(self.target_path_version)
        h.write_f64(self.launch_sec)
        h.write_f64(self.intercept_sec)
        h.write_vec2(self.launch_pos)
        h.write_vec2(self.intercept_pos)
        h.write_f64(self.intercept_alt_m)
        h.write_f64(self.speed_mps)
        h.write_f64(self.hit_prob)


@dataclass
class SupportAsset(Entity):
    support_kind: int = 0  # Fighter=0, NationalSpoof=1, AdjacentCoverage=2, ElectronicRecon=3
    state: int = 0         # EnRoute=0, Active=1
    arrive_sec: float = 0.0
    end_sec: float = 0.0
    radius_m: float = 0.0
    exclusive_zone: bool = False
    fighter_id: str = ""
    weapon_id: str = ""
    ammo_remaining: int = 0
    next_shot_sec: float = 0.0

    def write_hash(self, h: StateHasher) -> None:
        h.write_enum(self.support_kind)
        h.write_enum(self.state)
        h.write_f64(self.arrive_sec)
        h.write_f64(self.end_sec)
        h.write_f64(self.radius_m)
        h.write_bool(self.exclusive_zone)
        h.write_str(self.fighter_id)
        h.write_str(self.weapon_id)
        h.write_i32(self.ammo_remaining)
        h.write_f64(self.next_shot_sec)


@dataclass
class Debris(Entity):
    def __post_init__(self) -> None:
        self.def_id = None


@dataclass
class ChoiceRequest(Entity):
    kind: int = 0  # ArmIncoming=0, StoryEvent=1
    choice_key: str = ""
    option_count: int = 2
    default_option: int = 0
    deadline_tick: int = 0
    subject_unit_id: int = 0
    subject_track_id: int = 0
    story_event_id: Optional[str] = None

    def __post_init__(self) -> None:
        self.def_id = None
        self.pos = None
        self.alt_m = None

    def write_hash(self, h: StateHasher) -> None:
        h.write_enum(self.kind)
        h.write_str(self.choice_key)
        h.write_i32(self.option_count)
        h.write_i32(self.default_option)
        h.write_i32(self.deadline_tick)
        h.write_i32(self.subject_unit_id)
        h.write_i32(self.subject_track_id)
        h.write_str(self.story_event_id)


# ---------- Singleton State Components (1-10 in hash order) ----------


@dataclass
class PendingSpawn:
    seq: int
    spawn_tick: int
    spawn_at_sec: float
    wave_id: str
    wave_index: int
    group_index: int
    index_in_group: int
    enemy_id: str
    entry_id: str
    route: Any
    target_spec: Any
    ai_tags: Optional[List[AiTag]]
    injected: bool = False


@dataclass
class WaveInjection:
    wave_id: str
    start_at_sec: float
    group_indices: Optional[List[int]] = None


@dataclass
class WaveState:
    pending: List[PendingSpawn] = field(default_factory=list)
    injections: List[WaveInjection] = field(default_factory=list)
    started_wave_keys: List[str] = field(default_factory=list)
    next_spawn_seq: int = 1
    spawned_threat_count: int = 0
    all_waves_spawned: bool = False

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(len(self.pending))
        for p in self.pending:
            h.write_i32(p.seq)
            h.write_i32(p.spawn_tick)
            h.write_f64(p.spawn_at_sec)
            h.write_str(p.wave_id)
            h.write_i32(p.wave_index)
            h.write_i32(p.group_index)
            h.write_i32(p.index_in_group)
            h.write_str(p.enemy_id)
            h.write_str(p.entry_id)
            h.write_bool(p.injected)
        h.write_i32(len(self.injections))
        for inj in self.injections:
            h.write_str(inj.wave_id)
            h.write_f64(inj.start_at_sec)
            if inj.group_indices is None:
                h.write_bool(False)
            else:
                h.write_bool(True)
                h.write_i32(len(inj.group_indices))
                for gi in inj.group_indices:
                    h.write_i32(gi)
        h.write_i32(len(self.started_wave_keys))
        for k in sorted(self.started_wave_keys):
            h.write_str(k)
        h.write_i32(self.next_spawn_seq)
        h.write_i32(self.spawned_threat_count)
        h.write_bool(self.all_waves_spawned)


@dataclass
class RawDetection:
    source_id: int
    source_kind: int  # 0=Sensor, 1=FireControl, 2=Optical, 3=Fighter
    threat_id: int
    phantom_key: int
    quality: TrackQuality
    pos: Vec2
    vel_mps: Vec2
    tag: Optional[TargetTag]
    can_cue: bool
    uncertainty_radius_m: float = 0.0


@dataclass
class DelayedDetection:
    due_tick: int
    detection: RawDetection


@dataclass
class SensingState:
    detections: List[RawDetection] = field(default_factory=list)  # transient per step, not hashed
    delayed: List[DelayedDetection] = field(default_factory=list)
    emitted_early_warnings: List[str] = field(default_factory=list)
    next_phantom_key: int = 1

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(len(self.delayed))
        for d in self.delayed:
            h.write_i32(d.due_tick)
            h.write_i32(d.detection.source_id)
            h.write_i32(d.detection.threat_id)
            h.write_i32(d.detection.phantom_key)
            h.write_enum(d.detection.quality)
            h.write_vec2(d.detection.pos)
        h.write_i32(len(self.emitted_early_warnings))
        for w in sorted(self.emitted_early_warnings):
            h.write_str(w)
        h.write_i32(self.next_phantom_key)


@dataclass
class EwState:
    urban_nav_jam_sec: float = 0.0
    urban_nav_jam_triggered: bool = False

    def write_hash(self, h: StateHasher) -> None:
        h.write_f64(self.urban_nav_jam_sec)
        h.write_bool(self.urban_nav_jam_triggered)


@dataclass
class ScheduledSpawn:
    due_tick: int
    wave_id: str
    story_event_id: str


@dataclass
class CommandState:
    command_points: int = 0
    command_points_initial: int = 0
    command_points_spent: int = 0
    relocations_completed: int = 0
    choices_triggered: int = 0
    choices_timed_out: int = 0
    fired_story_events: List[str] = field(default_factory=list)
    story_choice_results: Dict[str, str] = field(default_factory=dict)
    scheduled_spawns: List[ScheduledSpawn] = field(default_factory=list)
    alternate_positions_used: Dict[str, int] = field(default_factory=dict)  # altId -> unitId

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(self.command_points)
        h.write_i32(self.command_points_initial)
        h.write_i32(self.command_points_spent)
        h.write_i32(self.relocations_completed)
        h.write_i32(self.choices_triggered)
        h.write_i32(self.choices_timed_out)
        h.write_i32(len(self.fired_story_events))
        for ev in self.fired_story_events:
            h.write_str(ev)
        h.write_i32(len(self.story_choice_results))
        for k in sorted(self.story_choice_results.keys()):
            h.write_str(k)
            h.write_str(self.story_choice_results[k])
        h.write_i32(len(self.scheduled_spawns))
        for sp in self.scheduled_spawns:
            h.write_i32(sp.due_tick)
            h.write_str(sp.wave_id)
            h.write_str(sp.story_event_id)


@dataclass
class KnownTargetEntry:
    entry_id: int
    unit_id: int
    roster_id: int
    unit_def_id: str
    kind: int  # 0=Radar, 1=Launcher, 2=Ew, 3=Sensor
    reason: int  # 0=Exposure, 1=ProbeObserved, 2=SpotterObserved, 3=CarryIn
    pos: Vec2
    exposure: float
    added_tick: int
    priority: bool = False


@dataclass
class HeldWaveGroup:
    wave_id: str
    wave_index: int
    group_indices: List[int]
    hold_until_tick: int
    watched_unit_ids: List[int] = field(default_factory=list)


@dataclass
class EnemyIntelState:
    next_entry_id: int = 1
    known_targets: List[KnownTargetEntry] = field(default_factory=list)
    held_waves: List[HeldWaveGroup] = field(default_factory=list)
    probe_observed_unit_ids: List[int] = field(default_factory=list)

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(self.next_entry_id)
        h.write_i32(len(self.known_targets))
        for kt in self.known_targets:
            h.write_i32(kt.entry_id)
            h.write_i32(kt.unit_id)
            h.write_str(kt.unit_def_id)
            h.write_enum(kt.kind)
            h.write_enum(kt.reason)
            h.write_vec2(kt.pos)
            h.write_f64(kt.exposure)
            h.write_i32(kt.added_tick)
            h.write_bool(kt.priority)
        h.write_i32(len(self.held_waves))
        for hw in self.held_waves:
            h.write_str(hw.wave_id)
            h.write_i32(hw.wave_index)
            h.write_i32(len(hw.group_indices))
            for gi in hw.group_indices:
                h.write_i32(gi)
            h.write_i32(hw.hold_until_tick)


@dataclass
class SupportState:
    sorties_remaining: int = 0
    sorties_used: int = 0
    support_calls_tonight: Dict[str, int] = field(default_factory=dict)
    cooldown_until_sec: Dict[str, float] = field(default_factory=dict)

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(self.sorties_remaining)
        h.write_i32(self.sorties_used)
        h.write_i32(len(self.support_calls_tonight))
        for k in sorted(self.support_calls_tonight.keys()):
            h.write_str(k)
            h.write_i32(self.support_calls_tonight[k])
        h.write_i32(len(self.cooldown_until_sec))
        for k in sorted(self.cooldown_until_sec.keys()):
            h.write_str(k)
            h.write_f64(self.cooldown_until_sec[k])


@dataclass
class GridState:
    collapsed: bool = False
    unpowered_consumer_frac: float = 0.0

    def write_hash(self, h: StateHasher) -> None:
        h.write_bool(self.collapsed)
        h.write_f64(self.unpowered_consumer_frac)


@dataclass
class CivilState:
    alert_on: bool = False
    sheltered_frac: float = 0.0
    responsiveness: float = 1.0
    alert_switched_on_sec: float = -1.0
    total_alert_sec: float = 0.0
    false_alarm_sec: float = 0.0

    def write_hash(self, h: StateHasher) -> None:
        h.write_bool(self.alert_on)
        h.write_f64(self.sheltered_frac)
        h.write_f64(self.responsiveness)
        h.write_f64(self.alert_switched_on_sec)
        h.write_f64(self.total_alert_sec)
        h.write_f64(self.false_alarm_sec)


@dataclass
class ScoringState:
    defense_cost_musd: float = 0.0
    enemy_destroyed_value_musd: float = 0.0
    enemy_total_value_musd: float = 0.0
    shots_fired_by_weapon: Dict[str, int] = field(default_factory=dict)
    hits_by_weapon: Dict[str, int] = field(default_factory=dict)
    raw_enemy_cost_by_weapon: Dict[str, float] = field(default_factory=dict)
    wasteful_shots_by_weapon: Dict[str, int] = field(default_factory=dict)
    kills_by_enemy: Dict[str, int] = field(default_factory=dict)
    leaks_by_enemy: Dict[str, int] = field(default_factory=dict)
    threats_ew_downed: int = 0
    threats_ever_ew_covered: int = 0
    debris_count: int = 0
    debris_urban_hits: int = 0
    civilian_structures_damaged: int = 0
    destroyed_unit_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    weighted_loss_frac: float = 0.0
    neighbor_crossings: int = 0

    def write_hash(self, h: StateHasher) -> None:
        h.write_f64(self.defense_cost_musd)
        h.write_f64(self.enemy_destroyed_value_musd)
        h.write_f64(self.enemy_total_value_musd)
        h.write_i32(len(self.shots_fired_by_weapon))
        for k in sorted(self.shots_fired_by_weapon.keys()):
            h.write_str(k)
            h.write_i32(self.shots_fired_by_weapon[k])
        h.write_i32(len(self.hits_by_weapon))
        for k in sorted(self.hits_by_weapon.keys()):
            h.write_str(k)
            h.write_i32(self.hits_by_weapon[k])
        h.write_i32(len(self.kills_by_enemy))
        for k in sorted(self.kills_by_enemy.keys()):
            h.write_str(k)
            h.write_i32(self.kills_by_enemy[k])
        h.write_i32(self.threats_ew_downed)
        h.write_i32(self.threats_ever_ew_covered)
        h.write_i32(self.debris_count)
        h.write_i32(self.debris_urban_hits)
        h.write_i32(self.civilian_structures_damaged)
        h.write_f64(self.weighted_loss_frac)
        h.write_i32(self.neighbor_crossings)


@dataclass
class EngagementState:
    ammo_pool: Dict[str, int] = field(default_factory=dict)
    per_level_used: Dict[str, int] = field(default_factory=dict)

    def write_hash(self, h: StateHasher) -> None:
        h.write_i32(len(self.ammo_pool))
        for k in sorted(self.ammo_pool.keys()):
            h.write_str(k)
            h.write_i32(self.ammo_pool[k])
        h.write_i32(len(self.per_level_used))
        for k in sorted(self.per_level_used.keys()):
            h.write_str(k)
            h.write_i32(self.per_level_used[k])


# ---------- Events, Commands, Config, SimState ----------


@dataclass
class SimEvent:
    type: SimEventType
    tick: int = 0
    seq: int = 0
    at_sec: Optional[float] = None
    fields: Tuple[Any, ...] = ()
    data: Dict[str, Any] = field(default_factory=dict)

    def write_hash(self, h: StateHasher) -> None:
        for val in self.fields:
            if isinstance(val, bool):
                h.write_bool(val)
            elif isinstance(val, IntEnum):
                h.write_enum(int(val))
            elif isinstance(val, int):
                h.write_i32(val)
            elif isinstance(val, float):
                h.write_f64(val)
            elif isinstance(val, str) or val is None:
                h.write_str(val)
            elif isinstance(val, Vec2):
                h.write_vec2(val)
            elif isinstance(val, tuple) and len(val) == 2 and val[0] in ("opt_i32", "opt_f64", "opt_str", "i64", "list_enum"):
                kind, inner = val
                if kind == "opt_i32":
                    h.write_opt_i32(inner)
                elif kind == "opt_f64":
                    h.write_opt_f64(inner)
                elif kind == "opt_str":
                    h.write_str(inner)
                elif kind == "i64":
                    h.write_i64(inner)
                elif kind == "list_enum":
                    if inner is None:
                        h.write_bool(False)
                    else:
                        h.write_bool(True)
                        h.write_i32(len(inner))
                        for item in inner:
                            h.write_enum(int(item))


class EventSink:
    """Per-step event buffer and event stream hasher (00_core.md §3.4.2)."""

    def __init__(self, state_ref: Callable[[], SimState]):
        self._state_ref = state_ref
        self.current_step: List[SimEvent] = []
        self.previous_step: List[SimEvent] = []
        self._outbox: List[SimEvent] = []

    def emit(
        self,
        ev_type: SimEventType,
        at_sec: Optional[float] = None,
        fields: Tuple[Any, ...] = (),
        **kwargs: Any,
    ) -> SimEvent:
        st = self._state_ref()
        if at_sec is not None:
            left = (st.tick - 1) * 1.0
            right = st.tick * 1.0
            if at_sec <= left or at_sec >= right:
                if abs(at_sec - right) <= 1e-9 or at_sec <= left:
                    at_sec = None
        ev = SimEvent(
            type=ev_type,
            tick=st.tick,
            seq=st.next_event_seq,
            at_sec=at_sec,
            fields=fields,
            data=kwargs,
        )
        st.next_event_seq += 1
        self.current_step.append(ev)
        return ev

    def seal_step(self) -> None:
        st = self._state_ref()
        h = StateHasher(st.event_stream_hash)
        for ev in self.current_step:
            h.write_enum(int(ev.type))
            h.write_i32(ev.tick)
            h.write_i64(ev.seq)
            h.write_opt_f64(ev.at_sec)
            ev.write_hash(h)
        st.event_stream_hash = h.value
        self._outbox.extend(self.current_step)
        self.previous_step = self.current_step
        self.current_step = []

    def drain(self) -> List[SimEvent]:
        res = list(self._outbox)
        self._outbox.clear()
        return res


@dataclass
class SimCommand:
    type: SimCommandType
    effective_tick: int = 0
    seq: int = 0
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlacedUnit:
    unit_def_id: str
    pos: Vec2
    alternate_position_id: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    first_night_at_new_position: bool = False
    roster_id: int = 0


@dataclass
class DeploymentPlan:
    units: List[PlacedUnit] = field(default_factory=list)


@dataclass
class CarryIn:
    units: List[Dict[str, Any]] = field(default_factory=list)
    structures: List[Dict[str, Any]] = field(default_factory=list)
    ammo_pool: Optional[Dict[str, int]] = None
    per_level_used: Dict[str, int] = field(default_factory=dict)
    alert_responsiveness: Optional[float] = None
    known_targets: Optional[List[Dict[str, Any]]] = None
    command_points_bonus: int = 0
    fighter_sorties_delta: int = 0
    active_supports: List[str] = field(default_factory=list)
    adaptation: Optional[Dict[str, Any]] = None
    auto_resolve: Optional[Dict[str, float]] = None


@dataclass
class SimConfig:
    night_index: int = 1
    deployment: DeploymentPlan = field(default_factory=DeploymentPlan)
    carry_in: CarryIn = field(default_factory=CarryIn)
    end_when_clear: bool = True
    auto_choice_prompts: bool = True
    duration_ticks_override: Optional[int] = None
    check_invariants: bool = True
    random_override: Optional[Callable[[str, int], Optional[SimRandom]]] = None
    enemy_ai_hooks_override: Any = None
    capture_debug: bool = False


@dataclass
class EndRequest:
    outcome: NightOutcome
    reason: NightEndReason
    detail: Optional[str] = None


@dataclass
class NightResult:
    level_id: str = ""
    night_index: int = 1
    seed: str = ""
    data_hash: str = ""
    outcome: NightOutcome = NightOutcome.Survived
    end_reason: NightEndReason = NightEndReason.DurationElapsed
    end_tick: int = 0
    end_time_sec: float = 0.0
    final_state_hash: str = ""
    losses: Dict[str, Any] = field(default_factory=dict)
    ammo: Dict[str, Any] = field(default_factory=dict)
    exchange: Dict[str, Any] = field(default_factory=dict)
    debris: Dict[str, Any] = field(default_factory=dict)
    exposure: Dict[str, Any] = field(default_factory=dict)
    civil: Dict[str, Any] = field(default_factory=dict)
    support: Dict[str, Any] = field(default_factory=dict)
    commands: Dict[str, Any] = field(default_factory=dict)
    carry_out: Dict[str, Any] = field(default_factory=dict)


class SimState:
    """Complete mutable simulation state (00_core.md §2.5)."""

    def __init__(self, seed: int, random_override: Optional[Callable[[str, int], Optional[SimRandom]]] = None):
        self.tick: int = 0
        self.ids = IdAllocator(1)
        self.next_event_seq: int = 1
        self.event_stream_hash: int = FNV_OFFSET_BASIS
        self.end_request: Optional[EndRequest] = None

        root = SimRandom(seed)
        self.streams: Dict[str, SimRandom] = {}
        for name in SimRandom.STREAM_NAMES:
            child_seed = SimRandom.child_seed(root.seed, name)
            ovr = random_override(name, child_seed) if random_override else None
            self.streams[name] = ovr if ovr is not None else SimRandom(child_seed)

        tick_fn = lambda: self.tick
        self.grid_nodes: EntityStore[GridNode] = EntityStore(EntityKind.GridNode, self.ids, tick_fn)
        self.structures: EntityStore[Structure] = EntityStore(EntityKind.Structure, self.ids, tick_fn)
        self.fire_units: EntityStore[FireUnit] = EntityStore(EntityKind.FireUnit, self.ids, tick_fn)
        self.sensors: EntityStore[SensorUnit] = EntityStore(EntityKind.SensorUnit, self.ids, tick_fn)
        self.ew_units: EntityStore[EwUnit] = EntityStore(EntityKind.EwUnit, self.ids, tick_fn)
        self.deception_units: EntityStore[DeceptionUnit] = EntityStore(EntityKind.DeceptionUnit, self.ids, tick_fn)
        self.threats: EntityStore[Threat] = EntityStore(EntityKind.Threat, self.ids, tick_fn)
        self.tracks: EntityStore[Track] = EntityStore(EntityKind.Track, self.ids, tick_fn)
        self.interceptors: EntityStore[Interceptor] = EntityStore(EntityKind.Interceptor, self.ids, tick_fn)
        self.support_assets: EntityStore[SupportAsset] = EntityStore(EntityKind.SupportAsset, self.ids, tick_fn)
        self.debris: EntityStore[Debris] = EntityStore(EntityKind.Debris, self.ids, tick_fn)
        self.choices: EntityStore[ChoiceRequest] = EntityStore(EntityKind.ChoiceRequest, self.ids, tick_fn)

        self.all_stores: Tuple[EntityStore[Any], ...] = (
            self.grid_nodes,
            self.structures,
            self.fire_units,
            self.sensors,
            self.ew_units,
            self.deception_units,
            self.threats,
            self.tracks,
            self.interceptors,
            self.support_assets,
            self.debris,
            self.choices,
        )

        # 10 singleton components in hash order
        self.waves = WaveState()
        self.sensing = SensingState()
        self.ew = EwState()
        self.commands = CommandState()
        self.enemy_intel = EnemyIntelState()
        self.support = SupportState()
        self.grid = GridState()
        self.civil = CivilState()
        self.scoring = ScoringState()
        self.engagement = EngagementState()

        self.structure_id_by_def_id: Dict[str, int] = {}
        self.grid_node_id_by_def_id: Dict[str, int] = {}

    def rebind_stores(self) -> None:
        tick_fn = lambda: self.tick
        for store in self.all_stores:
            store._ids = self.ids
            store._tick_fn = tick_fn

    def request_end(self, outcome: NightOutcome, reason: NightEndReason, detail: Optional[str] = None) -> None:
        if self.end_request is None:
            self.end_request = EndRequest(outcome=outcome, reason=reason, detail=detail)

    def compute_hash(self) -> int:
        """Compute canonical FNV-1a 64 state hash (00_core.md §3.7.2)."""
        h = StateHasher()
        h.write_str("NWSH")
        h.write_i32(1)
        h.write_i32(self.tick)
        h.write_i32(self.ids.next_id)
        h.write_i64(self.next_event_seq)
        h.write_u64(self.event_stream_hash)

        if self.end_request is None:
            h.write_bool(False)
        else:
            h.write_bool(True)
            h.write_enum(int(self.end_request.outcome))
            h.write_enum(int(self.end_request.reason))
            h.write_str(self.end_request.detail)

        for name in SimRandom.STREAM_NAMES:
            rng = self.streams[name]
            if getattr(rng, "is_override", False):
                h.write_u64(0)
                h.write_u64(0)
            else:
                st, inc = rng.get_state()
                h.write_u64(st)
                h.write_u64(inc)

        for store in self.all_stores:
            h.write_i32(int(store.kind))
            alive = store.alive_list()
            h.write_i32(len(alive))
            for e in alive:
                h.write_i32(e.id)
                h.write_i32(e.created_tick)
                h.write_str(e.def_id)
                if e.pos is not None:
                    h.write_vec2(e.pos)
                    h.write_f64(e.alt_m if e.alt_m is not None else 0.0)
                e.write_hash(h)

        self.waves.write_hash(h)
        self.sensing.write_hash(h)
        self.ew.write_hash(h)
        self.commands.write_hash(h)
        self.enemy_intel.write_hash(h)
        self.support.write_hash(h)
        self.grid.write_hash(h)
        self.civil.write_hash(h)
        self.scoring.write_hash(h)
        self.engagement.write_hash(h)
        return h.value
