"""In-memory game session state and API methods for tools.webproto."""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Optional, Sequence

from tools.papersim.bots import BOT_REGISTRY, TacticalBot, create_bot
from tools.papersim.core import SimRandom, Vec2
from tools.papersim.enemy_ai import ChoiceStage, CommandStage
from tools.papersim.engagement import ScoringSystem
from tools.papersim.entities import (
    CarryIn,
    ChoiceRequest,
    DeploymentPlan,
    PlacedUnit,
    PlayerUnitCategory,
    SimCommand,
    SimCommandType,
    SimConfig,
    SimEvent,
    SimEventType,
    SupportAsset,
    TargetTag,
    TrackQuality,
    UnitDeployState,
)
from tools.papersim.movement import parse_target_tag
from tools.papersim.world import DefaultDeploymentBuilder, DeploymentValidator, SimWorld

from .helpers import (
    build_preset_placements,
    build_terrain_model,
    compute_coverage_and_validation,
    downsample_elevation,
    format_clock,
     get_loc,
    load_level_cached,
    make_placement_dict,
    tr,
)
from .telemetry import compute_battle_report, format_sim_event


class GameSession:
    """Manages a single playthrough across Night 1 and Night 2 for the web prototype."""

    def __init__(self) -> None:
        self.level_id: str = "test_01"
        self.night_index: int = 1
        self.seed: int = 42
        self.trust_score: float = 50.0
        self.trust_applied_for_night: bool = False
        self.carry_in: CarryIn = CarryIn()
        self.last_carry_out: Optional[Dict[str, Any]] = None
        self.last_battle_report: Optional[Dict[str, Any]] = None
        self.level = load_level_cached(self.level_id, self.night_index)
        self.terrain = build_terrain_model(self.level)
        self.placements: List[Dict[str, Any]] = build_preset_placements(self.level, "layered", self.carry_in)
        self.world: Optional[SimWorld] = None
        self.bot_name: str = "manual"
        self.bot: Optional[TacticalBot] = None
        self.arm_choice_fired_tonight: bool = False
        self.radio_banner: str = ""
        self.extra_logs: List[Dict[str, Any]] = []

    def init_level(
        self,
        level_id: str = "test_01",
        night_index: int = 1,
        seed: int = 42,
        reset: bool = False,
    ) -> Dict[str, Any]:
        self.level_id = level_id
        self.seed = int(seed)
        if reset or int(night_index) == 1:
            self.night_index = 1
            self.carry_in = CarryIn()
            self.last_carry_out = None
            self.last_battle_report = None
            self.trust_score = 50.0
            self.trust_applied_for_night = False
        else:
            self.night_index = int(night_index)

        self.level = load_level_cached(self.level_id, self.night_index)
        self.terrain = build_terrain_model(self.level)
        self.world = None

        presets = {
            "default": build_preset_placements(self.level, "default", self.carry_in),
            "layered": build_preset_placements(self.level, "layered", self.carry_in),
            "stacked": build_preset_placements(self.level, "stacked", self.carry_in),
        }
        if self.night_index == 2 and self.carry_in.units:
            self.placements = build_preset_placements(self.level, "carry_in", self.carry_in)
        else:
            self.placements = copy.deepcopy(presets["layered"])

        from .snapshot import serialize_level_meta
        return serialize_level_meta(self, presets)

    def compute_coverage(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        placements = payload.get("placements") or self.placements
        alt_m = float(payload.get("altM", 100.0))
        grid_res = int(payload.get("gridRes", 64))
        return compute_coverage_and_validation(self.level, self.terrain, placements, alt_m=alt_m, grid_res=grid_res)

    def start_night(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload.get("placements"):
            self.placements = payload["placements"]
        if payload.get("seed") is not None:
            self.seed = int(payload["seed"])
        if payload.get("night") is not None and int(payload["night"]) != self.night_index:
            self.night_index = int(payload["night"])
            self.level = load_level_cached(self.level_id, self.night_index)
            self.terrain = build_terrain_model(self.level)

        self.bot_name = str(payload.get("bot", "manual"))
        self.bot = create_bot(self.bot_name) if self.bot_name in BOT_REGISTRY else None
        self.arm_choice_fired_tonight = False
        self.trust_applied_for_night = False
        self.extra_logs.clear()

        pos_rules = self.level.catalog.rules.get("positions", {})
        min_spacing_m = float(pos_rules.get("minSpacingM", 100.0))
        existing_pos: List[Vec2] = []
        placed_units: List[PlacedUnit] = []
        used_alts: set[str] = set()

        for idx, p in enumerate(self.placements):
            uid = str(p.get("unitDefId", ""))
            raw_pos = p.get("pos", [10000.0, 10000.0])
            cand = Vec2(float(raw_pos[0]), float(raw_pos[1]))
            ok, _, _ = DeploymentValidator.is_valid_pos(cand, self.level, existing_pos, min_spacing_m)
            if not ok:
                cand = DefaultDeploymentBuilder._find_pos(cand, idx, self.level, existing_pos, min_spacing_m)
            existing_pos.append(cand)
            alt_id = p.get("alternatePositionId")
            if alt_id in used_alts:
                alt_id = None
            if alt_id:
                used_alts.add(alt_id)
            rid = int(p.get("rosterId", idx + 1))
            st = dict(p.get("settings") or {})
            placed_units.append(
                PlacedUnit(
                    unit_def_id=uid,
                    pos=cand,
                    alternate_position_id=alt_id,
                    settings=st,
                    first_night_at_new_position=bool(p.get("firstNightAtNewPosition", False)),
                    roster_id=rid,
                )
            )

        # If player moved an exposed unit away from its Night 1 KnownTarget position (>600m), remove stale KnownTarget
        # and reset its carry_in initial exposure to 0.0
        ci_copy = copy.deepcopy(self.carry_in)
        pos_by_rid = {pu.roster_id: pu.pos for pu in placed_units}
        relocated_rids: set[int] = set()
        if ci_copy.known_targets:
            kept_kts = []
            for kt in ci_copy.known_targets:
                rid = int(kt.get("rosterId", 0))
                kp = kt.get("pos", [0.0, 0.0])
                if rid in pos_by_rid and math.hypot(pos_by_rid[rid].x - kp[0], pos_by_rid[rid].y - kp[1]) > 600.0:
                    relocated_rids.add(rid)
                    continue
                kept_kts.append(kt)
            ci_copy.known_targets = kept_kts
        if ci_copy.units:
            for cu in ci_copy.units:
                rid = int(cu.get("rosterId", cu.get("roster_id", 0)))
                upos = cu.get("pos", [0.0, 0.0])
                if rid in relocated_rids or (
                    rid in pos_by_rid and math.hypot(pos_by_rid[rid].x - float(upos[0]), pos_by_rid[rid].y - float(upos[1])) > 600.0
                ):
                    cu["exposure"] = 0.0

        cfg = SimConfig(
            night_index=self.night_index,
            deployment=DeploymentPlan(units=placed_units),
            carry_in=ci_copy,
            end_when_clear=True,
            check_invariants=False,
        )
        self.world = SimWorld.create(self.level, seed=self.seed, config=cfg)

        # Apply initial weapon slot rules, ammo reserves, whitelist, SLS
        st_by_rid = {int(p.get("rosterId", i + 1)): (p.get("settings") or {}) for i, p in enumerate(self.placements)}
        rmap = {"any": 0, "ballistic_only": 1, "hold_fire": 2, "high_value_only": 3}
        for fu in self.world.state.fire_units.alive_list():
            ust = st_by_rid.get(fu.roster_id, {})
            r_int = rmap.get(str(ust.get("engagementRule", "any")), 0)
            res_cnt = int(ust.get("ammoReserve", 0) or 0)
            wl_raw = ust.get("whitelist")
            wl_set = {parse_target_tag(t) for t in wl_raw if parse_target_tag(t) is not None} if isinstance(wl_raw, list) else None
            sls = bool(ust.get("shootLookShoot", True))
            for ws in fu.weapons:
                ws.rule = r_int
                setattr(ws, "ammo_reserve", res_cnt)
                if wl_set is not None:
                    setattr(ws, "whitelist", wl_set)
                setattr(ws, "shoot_look_shoot", sls)

        init_evs = self.world.events.drain()
        return self.build_snapshot(init_evs, hard_pause=False, pause_reason=None)

    def step(self, ticks: int = 5) -> Dict[str, Any]:
        if self.world is None:
            self.start_night({})
        assert self.world is not None

        ticks = max(1, min(int(ticks), 28800))
        collected_evs: List[SimEvent] = []
        hard_pause = False
        pause_reason: Optional[str] = None

        for _ in range(ticks):
            if self.world.is_ended:
                break
            if self.bot is not None:
                for cmd in self.bot(self.world):
                    self.world.submit_command(cmd)

            step_evs = self.world.step()
            self._check_tactical_dilemma_trigger(step_evs)
            collected_evs.extend(step_evs)

            # Check if a ChoiceRequest is active or was emitted this step
            if self.world.state.choices.count_alive() > 0:
                if self.bot is None:
                    hard_pause = True
                    pause_reason = "choice_requested"
                    break
            if self.bot is None:
                for ev in step_evs:
                    if ev.type == SimEventType.EarlyWarning and ev.data.get("ballistic"):
                        pause_reason = "ballistic_warning"
                        break
            if pause_reason:
                break

        return self.build_snapshot(collected_evs, hard_pause=hard_pause, pause_reason=pause_reason)

    def _check_tactical_dilemma_trigger(self, step_evs: List[SimEvent]) -> None:
        """Create C-T3-01 ChoiceRequest on ARM lock or cruise-wave radar lock dilemma."""
        assert self.world is not None
        st = self.world.state
        if st.choices.count_alive() > 0 or self.arm_choice_fired_tonight:
            return

        target_unit = None
        for ev in step_evs:
            if ev.type == SimEventType.ArmThreatDetected:
                uid = int(ev.data.get("unit_id", 0))
                target_unit = CommandStage._find_unit(self.world.ctx, uid)
                break

        # Also trigger once per night when cruise wave (kh101 / su24m / kh59) is tracked while radar/SAM emits
        if target_unit is None:
            has_cruise = any(
                th.def_id in ("kh101", "su24m", "kh59", "kh31p")
                for th in st.threats.alive_list()
            )
            if has_cruise and st.tracks.count_alive() > 0:
                for s in st.sensors.alive_list():
                    if not s.automatic and s.emitter is not None and s.emitter.on:
                        target_unit = s
                        break
                if target_unit is None:
                    for fu in st.fire_units.alive_list():
                        if fu.emitter is not None and fu.emitter.on:
                            target_unit = fu
                            break

        if target_unit is not None:
            self.arm_choice_fired_tonight = True
            tr_id = st.tracks.alive_list()[0].id if st.tracks.alive_list() else 0
            ch = ChoiceRequest(
                kind=0,
                choice_key="choice.arm_vs_cruise",
                option_count=2,
                default_option=0,
                deadline_tick=st.tick + 1800,
                subject_unit_id=target_unit.id,
                subject_track_id=tr_id,
            )
            st.choices.add(ch)
            st.commands.choices_triggered += 1
            ev_ch = SimEvent(
                type=SimEventType.ChoiceRequested,
                tick=st.tick,
                seq=st.next_event_seq,
                fields=(ch.id, ch.choice_key, ch.option_count, ch.deadline_tick),
                data={"choice_id": ch.id, "subject_unit_id": target_unit.id},
            )
            st.next_event_seq += 1
            step_evs.append(ev_ch)

    def apply_command(self, cmd_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.world is None:
            return {"ok": False, "error": "Night has not started"}
        st = self.world.state
        ctype_str = str(cmd_data.get("type", ""))
        clk = format_clock(st.tick * self.world.step_sec)

        if ctype_str == "SetEmissionPolicy":
            uid = int(cmd_data.get("unitId", 0))
            pol = str(cmd_data.get("policyId", "continuous"))
            cmd = SimCommand(type=SimCommandType.SetEmissionPolicy, effective_tick=st.tick + 1, params={"unitId": uid, "policyId": pol})
            ok = CommandStage.apply_command(self.world.ctx, cmd)
            u = CommandStage._find_unit(self.world.ctx, uid)
            if ok and u and u.emitter:
                u.emitter.on = pol in ("continuous", "always_on", "blink")
                setattr(u.emitter, "arm_silenced", pol == "silent")
                self.extra_logs.append({"tick": st.tick, "clock": clk, "type": "Command", "level": "command", "text": f"📡 指令下达：单位 #{uid} 切换辐射策略为【{pol}】"})
            return self.build_snapshot([], hard_pause=False, pause_reason=None, command_ok=ok)

        if ctype_str == "BurstScan":
            uid = int(cmd_data.get("unitId", 0))
            u = CommandStage._find_unit(self.world.ctx, uid)
            if u is not None and u.emitter is not None:
                u.emitter.on = True
                u.emitter.policy_id = "continuous"
                u.emitter.fc_mode = 3
                u.emitter.fc_window_until_sec = self.world.ctx.time_sec + 180.0
                setattr(u.emitter, "arm_silenced", False)
                u.exposure = min(100.0, u.exposure + 8.0)
                self.extra_logs.append({"tick": st.tick, "clock": clk, "type": "BurstScan", "level": "alert", "text": f"⚡ 脉冲开机扫描：单位 #{uid} 强制全功率开机刷新高精度航迹（暴露度 +8%）"})
                return self.build_snapshot([], hard_pause=False, pause_reason=None, command_ok=True)
            return {"ok": False, "error": "Unit has no active radar emitter"}

        if ctype_str in ("NationalSpoof", "TriggerNationalSpoof"):
            already = any(sa.support_kind == 1 and sa.state == 1 for sa in st.support_assets.alive_list())
            if not already and st.commands.command_points > 0:
                st.commands.command_points -= 1
                st.commands.command_points_spent += 1
                sa = SupportAsset(
                    def_id="national_gnss_spoof",
                    pos=Vec2(10000.0, 10000.0),
                    alt_m=0.0,
                    support_kind=1,
                    state=1,
                    arrive_sec=self.world.ctx.time_sec,
                    end_sec=self.world.ctx.time_sec + 3600.0,
                    radius_m=30000.0,
                )
                st.support_assets.add(sa)
                self.extra_logs.append({"tick": st.tick, "clock": clk, "type": "NationalSpoof", "level": "command", "text": "🟣 国家级 GNSS 导航欺骗网已激活（消耗 1 CP）！全图卫星制导武器精度大幅降级"})
            return self.build_snapshot([], hard_pause=False, pause_reason=None, command_ok=True)

        if ctype_str in ("RelocateUnit", "Relocate"):
            uid = int(cmd_data.get("unitId", 0))
            alt_id = cmd_data.get("alternatePositionId")
            dest = cmd_data.get("dest")
            params: Dict[str, Any] = {"unitId": uid}
            if alt_id:
                params["alternatePositionId"] = alt_id
            if dest:
                params["dest"] = dest
            cmd = SimCommand(type=SimCommandType.RelocateUnit, effective_tick=st.tick + 1, params=params)
            ok = CommandStage.apply_command(self.world.ctx, cmd)
            if ok:
                self.extra_logs.append({"tick": st.tick, "clock": clk, "type": "RelocateUnit", "level": "command", "text": f"🚚 阵地转移：单位 #{uid} 开始撤收并机动前往备用阵地 {alt_id or ''}（消耗 1 CP）"})
            return self.build_snapshot([], hard_pause=False, pause_reason=None, command_ok=ok)

        if ctype_str in ("SetAirRaidAlert", "ToggleCivilAlert"):
            on = bool(cmd_data.get("on", not st.civil.alert_on))
            cmd = SimCommand(type=SimCommandType.SetAirRaidAlert, effective_tick=st.tick + 1, params={"on": on})
            ok = CommandStage.apply_command(self.world.ctx, cmd)
            if ok:
                self.extra_logs.append({"tick": st.tick, "clock": clk, "type": "AirRaidAlert", "level": "alert" if on else "info", "text": "🚨 全城防空警报拉响，市民进入掩体！" if on else "🔔 全城防空警报解除"})
            return self.build_snapshot([], hard_pause=False, pause_reason=None, command_ok=ok)

        if ctype_str in ("SetEngagementRule", "SetAmmoReserve", "SetTargetWhitelist", "SetShootLookShoot"):
            uid = int(cmd_data.get("unitId", 0))
            fu = st.fire_units.try_get(uid)
            if fu is None:
                return {"ok": False, "error": "FireUnit not found"}
            rmap = {"any": 0, "ballistic_only": 1, "hold_fire": 2, "high_value_only": 3}
            rule_str = cmd_data.get("rule")
            res_cnt = cmd_data.get("ammoReserve", cmd_data.get("reserve"))
            wl_raw = cmd_data.get("whitelist", cmd_data.get("tags"))
            sls = cmd_data.get("shootLookShoot", cmd_data.get("enabled") if ctype_str == "SetShootLookShoot" else None)
            wid = cmd_data.get("weaponId")
            for ws in fu.weapons:
                if wid and ws.weapon_id != wid:
                    continue
                if rule_str is not None:
                    ws.rule = rmap.get(str(rule_str), 0)
                if res_cnt is not None:
                    setattr(ws, "ammo_reserve", int(res_cnt))
                if isinstance(wl_raw, list):
                    setattr(ws, "whitelist", {parse_target_tag(t) for t in wl_raw if parse_target_tag(t) is not None})
                if sls is not None:
                    setattr(ws, "shoot_look_shoot", bool(sls))
            self.extra_logs.append({"tick": st.tick, "clock": clk, "type": "EngagementRule", "level": "command", "text": f"🎯 射击学说更新：单位 #{uid} ({ctype_str})"})
            return self.build_snapshot([], hard_pause=False, pause_reason=None, command_ok=True)

        if ctype_str == "AnswerChoice":
            cid = int(cmd_data.get("choiceId", 0))
            opt = int(cmd_data.get("option", 0))
            ch = st.choices.try_get(cid) if cid > 0 else (st.choices.alive_list()[0] if st.choices.alive_list() else None)
            if ch is not None:
                ChoiceStage.resolve(self.world.ctx, ch, opt, timed_out=False)
                st.choices.compact()
                opt_txt = "选项A：立即关机规避反辐射导弹" if opt == 0 else "选项B：坚持开机引导拦截巡航导弹"
                self.extra_logs.append({"tick": st.tick, "clock": clk, "type": "ChoiceResolved", "level": "choice", "text": f"⚡ 紧急抉择已下达：【{opt_txt}】"})
            return self.build_snapshot([], hard_pause=False, pause_reason=None, command_ok=True)

        if ctype_str in ("TriggerChoice", "TriggerArmChoiceDemo"):
            self.arm_choice_fired_tonight = False
            u = next((s for s in st.sensors.alive_list() if not s.automatic), None) or (st.fire_units.alive_list()[0] if st.fire_units.alive_list() else None)
            if u is not None:
                ch = ChoiceRequest(kind=0, choice_key="choice.arm_vs_cruise", option_count=2, default_option=0, deadline_tick=st.tick + 1800, subject_unit_id=u.id, subject_track_id=0)
                st.choices.add(ch)
                return self.build_snapshot([], hard_pause=True, pause_reason="choice_requested", command_ok=True)

        return {"ok": False, "error": f"Unknown command type: {ctype_str}"}

    def advance_to_next_night(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.world is not None:
            if self.last_carry_out is None or self.last_battle_report is None:
                res = self.world.build_result()
                self.last_carry_out = res.carry_out
                self.last_battle_report = compute_battle_report(self.world, res)
            if not self.trust_applied_for_night and self.last_battle_report is not None:
                self.trust_score = max(0.0, min(100.0, self.trust_score + float(self.last_battle_report["trust"]["applied"])))
                self.trust_applied_for_night = True

        co = self.last_carry_out or {}
        self.carry_in = CarryIn(
            units=copy.deepcopy(co.get("units", [])),
            structures=copy.deepcopy(co.get("structures", [])),
            ammo_pool=dict(co.get("ammoPool", {})) if co.get("ammoPool") else None,
            per_level_used=dict(co.get("perLevelUsed", {})),
            alert_responsiveness=float(co.get("alertResponsiveness", 1.0)),
            known_targets=copy.deepcopy(co.get("knownTargets", [])),
        )
        self.night_index = 2
        self.seed = SimRandom.night_seed(self.seed, self.level_id, 2) & 0x7FFFFFFFFFFFFFFF
        return self.init_level(self.level_id, night_index=2, seed=self.seed, reset=False)

    def build_snapshot(
        self,
        raw_events: Sequence[SimEvent],
        hard_pause: bool = False,
        pause_reason: Optional[str] = None,
        command_ok: bool = True,
    ) -> Dict[str, Any]:
        from .snapshot import serialize_world_snapshot
        return serialize_world_snapshot(self, raw_events, hard_pause=hard_pause, pause_reason=pause_reason, command_ok=command_ok)


SESSION_STORE = GameSession()

