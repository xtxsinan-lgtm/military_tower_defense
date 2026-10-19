#!/usr/bin/env python3
"""D4-③ AI Playtester: Three-Persona Two-Night Playtest on test_01 via GameSession.

Runs 3 complete two-night playtest games (Night 1 -> Post-Night Review & Adjustments -> Night 2)
strictly from a player's perspective (using only briefing, intel, map layers/structures/deploy zones,
and runtime sensor tracks/events; never reading waves.json):
  - Game 1: 初见直觉型玩家 (Blind First-Timer)
  - Game 2: 激进贪婪型玩家 (Aggressive Radar-On / Fire-At-Will)
  - Game 3: 老练复盘型指挥官 (Veteran Tactical Commander)

Outputs complete step-by-step observation-judgment-decision logs, key timestamps, raw vs UI event
comparisons, and battle reports to tools/papersim/experiments/d4_3_playtest_logs.json.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.papersim.entities import SimEvent, SimEventType
from tools.webproto.session import GameSession
from tools.webproto.telemetry import format_clock, format_sim_event


INTERESTING_RAW_EVENTS = {
    SimEventType.WaveStarted,
    SimEventType.EarlyWarning,
    SimEventType.ExposureThresholdCrossed,
    SimEventType.InterceptorLaunched,
    SimEventType.GunFired,
    SimEventType.InterceptResolved,
    SimEventType.ThreatImpacted,
    SimEventType.StructureDamaged,
    SimEventType.StructureDestroyed,
    SimEventType.GridPowerChanged,
    SimEventType.KnownTargetAdded,
    SimEventType.ArmThreatDetected,
    SimEventType.ChoiceRequested,
    SimEventType.ChoiceResolved,
    SimEventType.AmmoDepleted,
    SimEventType.DebrisFell,
    SimEventType.PlayerUnitDamaged,
    SimEventType.PlayerUnitDestroyed,
    SimEventType.SupportArrived,
    SimEventType.SupportEnded,
    SimEventType.NightEnded,
}


def _summarize_raw_event(world: Any, ev: SimEvent) -> Dict[str, Any]:
    ui_ev = format_sim_event(world, ev)
    return {
        "tick": int(ev.tick),
        "clock": format_clock(ev.tick * world.step_sec),
        "type": ev.type.name,
        "fields": [str(f) for f in (ev.fields or [])],
        "data": dict(ev.data) if ev.data else {},
        "shownInWebprotoLog": ui_ev is not None,
        "webprotoText": ui_ev["text"] if ui_ev else None,
    }


def _collect_structure_status(world: Any) -> List[Dict[str, Any]]:
    out = []
    for st in world.state.structures.alive_list():
        out.append({
            "id": st.def_id,
            "hp": int(st.hp),
            "maxHp": int(st.max_hp),
            "weight": float(st.weight),
            "destroyed": bool(st.destroyed),
            "powered": bool(st.powered),
        })
    return out


def _collect_unit_status(world: Any) -> List[Dict[str, Any]]:
    out = []
    for store in (world.state.fire_units, world.state.sensors):
        for u in store.alive_list():
            if getattr(u, "automatic", False):
                continue
            weapons_info = []
            for ws in getattr(u, "weapons", []):
                weapons_info.append({
                    "weaponId": ws.weapon_id,
                    "rule": int(ws.rule),
                    "ammoReserve": int(getattr(ws, "ammo_reserve", 0) or 0),
                    "roundsOnLaunchers": sum(ln.rounds for ln in ws.launchers if not ln.destroyed),
                })
            out.append({
                "unitId": int(u.id),
                "rosterId": int(u.roster_id),
                "unitDefId": str(u.def_id),
                "pos": [round(u.pos.x, 1), round(u.pos.y, 1)],
                "exposure": round(float(u.exposure), 1),
                "exposurePeak": round(float(u.exposure_peak), 1),
                "lightDamaged": bool(u.light_damaged),
                "damageEfficiencyMult": float(u.damage_efficiency_mult),
                "offlineUntilSec": float(getattr(u, "offline_until_sec", 0.0) or 0.0),
                "radarDestroyed": bool(getattr(u, "radar_destroyed", False)),
                "launchersLost": int(getattr(u, "launchers_lost", 0)),
                "emitterOn": bool(u.emitter.on) if u.emitter else None,
                "emissionPolicy": str(u.emitter.policy_id) if u.emitter else None,
                "weapons": weapons_info,
            })
    return out


def _run_night_loop(
    session: GameSession,
    decision_log: List[Dict[str, Any]],
    tick_hook: Callable[[GameSession, int, List[Dict[str, Any]]], None],
    choice_hook: Callable[[GameSession, int, Dict[str, Any], List[Dict[str, Any]]], None],
    step_ticks: int = 180,
) -> Dict[str, Any]:
    assert session.world is not None
    raw_timeline: List[Dict[str, Any]] = []
    ui_timeline: List[Dict[str, Any]] = []
    silent_critical_events: List[Dict[str, Any]] = []

    while not session.world.is_ended:
        t = session.world.state.tick
        tick_hook(session, t, decision_log)

        # Step tick-by-tick inside a batch to capture raw SimEvents alongside GameSession's snapshot
        collected_raw: List[SimEvent] = []
        hard_pause = False
        pause_reason: Optional[str] = None
        for _ in range(step_ticks):
            if session.world.is_ended:
                break
            step_evs = session.world.step()
            session._check_tactical_dilemma_trigger(step_evs)
            collected_raw.extend(step_evs)
            if session.world.state.choices.count_alive() > 0:
                hard_pause = True
                pause_reason = "choice_requested"
                break
            for ev in step_evs:
                if ev.type == SimEventType.EarlyWarning and ev.data.get("ballistic"):
                    pause_reason = "ballistic_warning"
                    break
            if pause_reason:
                break

        snap = session.build_snapshot(collected_raw, hard_pause=hard_pause, pause_reason=pause_reason)
        for uev in snap.get("events", []):
            ui_timeline.append(uev)

        for ev in collected_raw:
            if ev.type in INTERESTING_RAW_EVENTS:
                item = _summarize_raw_event(session.world, ev)
                raw_timeline.append(item)
                if ev.type in (
                    SimEventType.AmmoDepleted,
                    SimEventType.DebrisFell,
                    SimEventType.PlayerUnitDamaged,
                    SimEventType.PlayerUnitDestroyed,
                    SimEventType.KnownTargetAdded,
                ) and not item["shownInWebprotoLog"]:
                    silent_critical_events.append(item)

        if pause_reason == "choice_requested":
            choice_hook(session, session.world.state.tick, snap, decision_log)

    final_snap = session.build_snapshot([], hard_pause=False, pause_reason=None)
    report = final_snap["battleReport"]
    seen_exp_thresholds: set[tuple[int, int]] = set()
    dedup_key_events: List[Dict[str, Any]] = []
    repeated_exp_alerts = 0
    for e in raw_timeline:
        if e["type"] == "ExposureThresholdCrossed":
            key = (int(e["data"].get("unit_id", 0)), int(e["data"].get("threshold", 0)))
            if key in seen_exp_thresholds:
                repeated_exp_alerts += 1
                continue
            seen_exp_thresholds.add(key)
        if e["type"] in (
            "WaveStarted",
            "EarlyWarning",
            "ExposureThresholdCrossed",
            "KnownTargetAdded",
            "ChoiceRequested",
            "ChoiceResolved",
            "AmmoDepleted",
            "StructureDamaged",
            "StructureDestroyed",
            "GridPowerChanged",
            "PlayerUnitDamaged",
            "PlayerUnitDestroyed",
            "DebrisFell",
            "NightEnded",
        ):
            dedup_key_events.append(e)

    return {
        "nightIndex": int(session.night_index),
        "seed": int(session.seed),
        "trustScoreSessionRaw": float(session.trust_score),
        "decisionLog": decision_log,
        "battleReport": report,
        "structuresEnd": _collect_structure_status(session.world),
        "unitsEnd": _collect_unit_status(session.world),
        "carryOut": copy.deepcopy(session.last_carry_out),
        "silentCriticalEventsCount": len(silent_critical_events),
        "silentCriticalEvents": silent_critical_events,
        "repeatedExposureAlertsCount": repeated_exp_alerts,
        "keyRawEvents": dedup_key_events,
    }


def run_game_1_blind_first_timer() -> Dict[str, Any]:
    """Game 1: 初见直觉型玩家 (Blind First-Timer)."""
    session = GameSession()
    meta_n1 = session.init_level("test_01", night_index=1, seed=42, reset=True)

    # Night 1 Pre-deployment: First-timer picks "default" preset around city center
    placements_n1 = copy.deepcopy(meta_n1["presets"]["default"])
    decisions_n1: List[Dict[str, Any]] = [
        {
            "phase": "Pre-Night 1 Deployment",
            "clock": "22:00:00",
            "tick": 0,
            "observation": (
                "阅读简报与城市地图：中心城区有热电厂(tpp, 权重5)、中心变电站(substation_central, 权重3)、"
                "水厂(water_plant, 权重2)。情报提示主要威胁来自东/东北方向，分夜间四波。"
            ),
            "judgment": (
                "作为初见玩家，直觉认为把所有防空单位围在城区三座保护设施周围最安全；"
                "看到预设方案里有 default（默认环城部署），直接采用默认方案，保留系统默认的"
                " continuous（常开）雷达策略与 any（自由开火）规则，未修改白名单。"
            ),
            "action": "Select preset='default', keep emissionPolicyId='continuous', engagementRule='any', ammoReserve=2 on SAMs.",
        }
    ]

    session.start_night({"placements": placements_n1, "seed": 42, "night": 1, "bot": "manual"})

    alert_raised_n1 = False

    def tick_hook_n1(s: GameSession, tick: int, dlog: List[Dict[str, Any]]) -> None:
        nonlocal alert_raised_n1
        if tick >= 1800 and not alert_raised_n1:
            alert_raised_n1 = True
            s.apply_command({"type": "SetAirRaidAlert", "on": True})
            dlog.append({
                "phase": "Night 1 Mid-Battle",
                "clock": format_clock(tick),
                "tick": tick,
                "observation": "22:30 第一波接触！东北方向出现慢速无人机航迹，NASAMS 立即发射 AIM-120 迎击。",
                "judgment": "赶紧拉响全城防空警报降低民用伤亡风险；看 NASAMS 一发入魂觉得很爽，没意识到这是敌方试探波(w1_probe)正在记录我方防空阵地坐标，也没心疼 85 万美元一发的 AIM-120。",
                "action": "SetAirRaidAlert(on=True)",
            })

    def choice_hook_n1(s: GameSession, tick: int, snap: Dict[str, Any], dlog: List[Dict[str, Any]]) -> None:
        s.apply_command({"type": "AnswerChoice", "option": 0})
        dlog.append({
            "phase": "Night 1 Tactical Dilemma",
            "clock": format_clock(tick),
            "tick": tick,
            "observation": "02:00 河谷方向涌入高速巡航导弹(Kh-101)，同时弹出紧急抉择：反辐射导弹风险下是否立即关机规避？此时 NASAMS 只剩最后 2 发保留弹，苏制雷达与 NASAMS 暴露度均已 100%。",
            "judgment": "初见玩家害怕雷达被反辐射导弹炸毁，慌乱中选择【选项A：立即关机规避】，而且关机后忘了手动重新开机！",
            "action": "AnswerChoice(option=0: 立即关机规避反辐射导弹)",
        })

    n1_res = _run_night_loop(session, decisions_n1, tick_hook_n1, choice_hook_n1)

    # Advance to Night 2 & Post-Night 1 Review
    session.advance_to_next_night()
    placements_n2 = copy.deepcopy(session.placements)
    for u in placements_n2:
        rid = u["rosterId"]
        st = u.setdefault("settings", {})
        if rid == 6:  # NASAMS moved to alt_south, set to high_value_only
            u["pos"] = [11000.0, 5000.0]
            u["alternatePositionId"] = "alt_south"
            st["engagementRule"] = "high_value_only"
            st["ammoReserve"] = 2
            st["whitelist"] = ["JET_UAV", "CM", "SCM", "BM", "HBM", "GB", "HELI", "AC_LOW", "AC_HIGH"]
        elif rid == 5:  # IRIS-T set to ammoReserve=2
            st["ammoReserve"] = 2
        # Crucial First-Timer Mistake: forgets to move Soviet Mid-Range Radar (rosterId=7)!

    decisions_n2: List[Dict[str, Any]] = [
        {
            "phase": "Post-Night 1 Review & Night 2 Adjustment",
            "clock": "22:00:00",
            "tick": 0,
            "observation": (
                "复盘第 1 夜战报：评级 C (56.7分)，加权设施损失 37.5%（水厂被第4波无人机彻底摧毁，热电厂受损 13/20），"
                "NASAMS 把 18 发 AIM-120 全打光了（绝大部分打在廉价 Shahed 上），且 NASAMS(#6) 与苏制中程雷达(#7) 均被标为 100% 暴露！"
                "此外城区内击落无人机还造成了 9 次残骸落入城区(debrisUrbanHits=9)。"
            ),
            "judgment": (
                "吸取教训：① 把 NASAMS 的交战规则改为 high_value_only 并从白名单剔除 UAV，专打巡航导弹和战机；"
                "② 把暴露的 NASAMS(#6) 转移到南侧已勘察备用阵地 alt_south [11000, 5000]；"
                "③ 【典型新手疏漏】只顾着搬最贵的 NASAMS 导弹连，完全忘了同样 100% 暴露的苏制中程警戒雷达(#7) 还在原坐标 [11694.0, 8839.3]！"
            ),
            "action": "Relocate NASAMS(#6) -> alt_south [11000, 5000] with high_value_only; forget to relocate exposed Soviet Radar(#7).",
        }
    ]

    session.start_night({"placements": placements_n2, "night": 2, "bot": "manual"})
    session.apply_command({"type": "SetAirRaidAlert", "on": True})

    unlocked_w6 = False

    def tick_hook_n2(s: GameSession, tick: int, dlog: List[Dict[str, Any]]) -> None:
        nonlocal unlocked_w6
        if tick >= 18000 and not unlocked_w6:
            unlocked_w6 = True
            s.apply_command({
                "type": "SetEngagementRule",
                "unitId": 14,
                "rule": "any",
                "ammoReserve": 0,
                "whitelist": ["UAV", "JET_UAV", "CM", "SCM", "BM", "HBM", "GB", "HELI", "AC_LOW", "AC_HIGH"],
            })
            dlog.append({
                "phase": "Night 2 Final Wave Emergency",
                "clock": format_clock(tick),
                "tick": tick,
                "observation": "03:00 拂晓前最后一波饱和攻击来袭！未转移的苏制中程警戒雷达(#7)正遭敌方猎杀无人机围攻，中心变电站告急！",
                "judgment": "紧急解除 NASAMS 的 high_value_only 限制与保留弹限制，允许其用剩余的 AIM-120 拦截突防的 Shahed 救场！",
                "action": "SetEngagementRule(unitId=14, rule='any', ammoReserve=0, whitelist=ALL)",
            })

    def choice_hook_n2(s: GameSession, tick: int, snap: Dict[str, Any], dlog: List[Dict[str, Any]]) -> None:
        s.apply_command({"type": "AnswerChoice", "option": 1})
        dlog.append({
            "phase": "Night 2 Tactical Dilemma",
            "clock": format_clock(tick),
            "tick": tick,
            "observation": "第 2 夜 00:00 敌方 Su-24M 战斗轰炸机与巡航导弹来袭，再次触发反辐射/巡航导弹抉择。",
            "judgment": "昨晚关机导致漏防，今晚决定选择【选项B：坚持开机引导拦截】，优先保住热电厂和变电站。",
            "action": "AnswerChoice(option=1: 坚持开机引导拦截巡航导弹)",
        })

    n2_res = _run_night_loop(session, decisions_n2, tick_hook_n2, choice_hook_n2)

    return {
        "gameId": "game_1_blind_first_timer",
        "personaName": "初见直觉型玩家 (Blind First-Timer)",
        "personaSummary": (
            "首夜使用默认环城部署，常开雷达+自由开火，在 22:30:09 试探波暴露 NASAMS 并在 02:01:14 将 18 发 AIM-120 打光，"
            "03:36:23 水厂被第 4 波无人机彻底摧毁并引发断电（C级，56.7分，损失 37.5%）；"
            "次夜学会限制 NASAMS 仅打高价值目标并将其南移至 alt_south [11000, 5000]，但漏移了 100% 暴露的苏制警戒雷达，"
            "且因南移过远漏掉西北方向 2 枚 Kh-101（触发囤弹扣分 dHoard=-4.0），03:00 饱和波次又慌乱解禁 NASAMS 狂打 Shahed（触发挥霍质询 dWaste=-9.0, dInq=-3.0），"
            "最终次夜拿到 C 级（53.4分，信任值单夜暴跌 -12.0）。"
        ),
        "night1": n1_res,
        "night2": n2_res,
    }


def run_game_2_aggressive_fire_at_will() -> Dict[str, Any]:
    """Game 2: 激进贪婪型玩家 (Aggressive Radar-On / Fire-At-Will)."""
    session = GameSession()
    meta_n1 = session.init_level("test_01", night_index=1, seed=42, reset=True)

    # Night 1 Pre-deployment: Uses layered preset, forces continuous, any, ammoReserve=0, shootLookShoot=False,
    # and focuses SAM whitelist on UAVs to wipe out every incoming drone wave immediately
    placements_n1 = copy.deepcopy(meta_n1["presets"]["layered"])
    for u in placements_n1:
        st = u.setdefault("settings", {})
        st["emissionPolicyId"] = "continuous"
        st["engagementRule"] = "any"
        st["ammoReserve"] = 0
        st["whitelist"] = ["UAV", "JET_UAV"]
        st["shootLookShoot"] = False

    decisions_n1: List[Dict[str, Any]] = [
        {
            "phase": "Pre-Night 1 Deployment",
            "clock": "22:00:00",
            "tick": 0,
            "observation": "查看可用编制：NASAMS 有 18 发导弹、IRIS-T 有 8 发导弹，雷达探测距离高达 150km。",
            "judgment": (
                "追求极致火力倾泻与视野全开：把所有雷达设为 continuous（全功率常开），"
                "所有防空导弹 ammoReserve 设为 0（不留保留弹），关闭 shootLookShoot（允许双发齐射确保秒杀），"
                "并将白名单锁定在满屏刷新的无人机群(UAV/JET_UAV)上，企图把所有进图的无人机第一时间清零！"
            ),
            "action": "Select preset='layered', set all units to emissionPolicyId='continuous', engagementRule='any', ammoReserve=0, whitelist=['UAV','JET_UAV'], shootLookShoot=False.",
        }
    ]

    session.start_night({"placements": placements_n1, "seed": 42, "night": 1, "bot": "manual"})

    burst_1_done = False
    burst_2_done = False

    def tick_hook_n1(s: GameSession, tick: int, dlog: List[Dict[str, Any]]) -> None:
        nonlocal burst_1_done, burst_2_done
        if tick >= 1800 and not burst_1_done:
            burst_1_done = True
            s.apply_command({"type": "BurstScan", "unitId": 15})
            dlog.append({
                "phase": "Night 1 Mid-Battle",
                "clock": format_clock(tick),
                "tick": tick,
                "observation": "22:30 第一波接触，为了尽快看清所有目标，立刻点击【脉冲开机扫描(BurstScan)】。",
                "judgment": "不在乎 +8% 暴露度惩罚，只想要最高精度航迹让 NASAMS 远距齐射。",
                "action": "BurstScan(unitId=15: 苏制中程警戒雷达)",
            })
        if tick >= 7200 and not burst_2_done:
            burst_2_done = True
            s.apply_command({"type": "BurstScan", "unitId": 15})
            dlog.append({
                "phase": "Night 1 Mid-Battle",
                "clock": format_clock(tick),
                "tick": tick,
                "observation": "00:00 主波次 Shahed 群出现，再次激活脉冲扫描，NASAMS 疯狂齐射，00:14:09 即打光全部 18 发 AIM-120！",
                "judgment": "前半夜无人机几乎被全歼(21/24)，盲目乐观，浑然不知 02:00 还有河谷巡航导弹波次。",
                "action": "BurstScan(unitId=15: 苏制中程警戒雷达)",
            })

    def choice_hook_n1(s: GameSession, tick: int, snap: Dict[str, Any], dlog: List[Dict[str, Any]]) -> None:
        s.apply_command({"type": "AnswerChoice", "option": 1})
        dlog.append({
            "phase": "Night 1 Tactical Dilemma",
            "clock": format_clock(tick),
            "tick": tick,
            "observation": "02:00 弹出反辐射/巡航导弹抉择，此时 NASAMS 弹舱早已在 00:14:09 清零(0/18)！",
            "judgment": "头铁到底，绝不关机，选择【选项B：坚持开机】，但因为 AIM-120 早已在前半夜挥霍殆尽且未勾选巡航导弹，6 枚 Kh-101 如入无人之境（0/6 拦截）！",
            "action": "AnswerChoice(option=1: 坚持开机引导拦截巡航导弹)",
        })

    n1_res = _run_night_loop(session, decisions_n1, tick_hook_n1, choice_hook_n1)

    # Advance to Night 2 & Post-Night 1 Review
    session.advance_to_next_night()
    placements_n2 = copy.deepcopy(session.placements)
    for u in placements_n2:
        st = u.setdefault("settings", {})
        st["emissionPolicyId"] = "continuous"
        st["engagementRule"] = "any"
        st["ammoReserve"] = 0
        st["whitelist"] = ["UAV", "JET_UAV"]
        st["shootLookShoot"] = False

    decisions_n2: List[Dict[str, Any]] = [
        {
            "phase": "Post-Night 1 Review & Night 2 Adjustment",
            "clock": "22:00:00",
            "tick": 0,
            "observation": (
                "第 1 夜战报惨烈：评级 D (42.5分)，设施加权损失已高达 45.5%（中心变电站仅剩 1/15 HP，距 50% 失败线仅差 4.5%）！"
                "更致命的是：因为把 18 发 AIM-120 ($15.30M) 全砸在 Shahed 上（效费比仅 0.78），"
                "触发了【最高统帅部调查委员会质询 (inquiry=True)】，信任值单夜暴跌 -12.0！"
                "而且 NASAMS 整关限额 (perLevelLimit=24) 在首夜已消耗 18 发，次夜实际只剩 6 发配额可用！"
            ),
            "judgment": (
                "激进型玩家嫌弃转移阵地会有新阵地效率惩罚，拒绝挪动已 100% 暴露的 NASAMS(#6) 和苏制雷达(#7)，"
                "且固执己见不改开火原则（仍保留 continuous + any + ammoReserve=0 + shootLookShoot=False），"
                "导致次夜 22:45 敌方猎杀波次(w5_known_hunt) 6 架 Shahed 进场时，NASAMS 连射 7 发 AIM-120 将整关配额彻底打穿！"
            ),
            "action": "Keep exposed positions unchanged; keep emissionPolicyId='continuous', engagementRule='any', ammoReserve=0, shootLookShoot=False.",
        }
    ]

    session.start_night({"placements": placements_n2, "night": 2, "bot": "manual"})

    burst_n2_done = False

    def tick_hook_n2(s: GameSession, tick: int, dlog: List[Dict[str, Any]]) -> None:
        nonlocal burst_n2_done
        if tick >= 1800 and not burst_n2_done:
            burst_n2_done = True
            s.apply_command({"type": "BurstScan", "unitId": 15})
            dlog.append({
                "phase": "Night 2 Mid-Battle",
                "clock": format_clock(tick),
                "tick": tick,
                "observation": "22:30 准备迎敌，激活脉冲扫描；22:45 敌方猎杀波次(w5_known_hunt) 6 架 Shahed 直扑暴露阵地，NASAMS 连射 7 发 AIM-120 将其全部击落，但也把全关 AIM-120 配额彻底打穿！",
                "judgment": "玩家看着发射架上显示还有 11 发弹药，浑然不知已触及全关配额上限(perLevelLimit=24)且未拦截高空投弹战机。",
                "action": "BurstScan(unitId=15: 苏制中程警戒雷达)",
            })

    def choice_hook_n2(s: GameSession, tick: int, snap: Dict[str, Any], dlog: List[Dict[str, Any]]) -> None:
        s.apply_command({"type": "AnswerChoice", "option": 1})
        dlog.append({
            "phase": "Night 2 Tactical Dilemma",
            "clock": format_clock(tick),
            "tick": tick,
            "observation": "01:00:00 敌方复合波次(w6_platform_cruise) Su-24M 突防投掷 FAB-250 航空炸弹，无人拦截！",
            "judgment": "选 B 坚持开机也无济于事，01:01:32 FAB-250 直接命中热电厂(HP 13->9)，加权损失突破 55.5% (>50%)，防线当场崩溃失败！",
            "action": "AnswerChoice(option=1: 坚持开机引导拦截巡航导弹)",
        })

    n2_res = _run_night_loop(session, decisions_n2, tick_hook_n2, choice_hook_n2)

    return {
        "gameId": "game_2_aggressive_fire_at_will",
        "personaName": "激进贪婪型玩家 (Aggressive Radar-On / Fire-At-Will)",
        "personaSummary": (
            "全功率常开雷达+关闭打看打(shootLookShoot=False)+零保留弹+频繁脉冲扫描，首夜 00:14:09 即把 18 发 AIM-120 全部倾泻在 Shahed 上，"
            "导致 02:00 河谷 6 枚 Kh-101 巡航导弹 0 拦截全部漏过，中心变电站被打至 1/15 HP，并触发最高统帅部【调查委员会质询】(信任值 -12.0，D级 42.5分，损失 45.5%)；"
            "次夜拒绝转移暴露阵地且不改开火原则，22:45 猎杀波次耗尽全关 AIM-120 限额，01:01:32 被 Su-24M 投掷 FAB-250 命中热电厂，加权损失达 55.5% 直接战败（F级 0.0分，信任值再扣 -12.0）！"
        ),
        "night1": n1_res,
        "night2": n2_res,
    }


def run_game_3_veteran_commander() -> Dict[str, Any]:
    """Game 3: 老练复盘型指挥官 (Veteran Tactical Commander)."""
    session = GameSession()
    meta_n1 = session.init_level("test_01", night_index=1, seed=42, reset=True)

    # Night 1 Pre-deployment: Layered defense, strict radar blink, NASAMS strictly high_value_only (no UAV)
    placements_n1 = copy.deepcopy(meta_n1["presets"]["layered"])
    for u in placements_n1:
        rid = u["rosterId"]
        st = u.setdefault("settings", {})
        if rid == 6:  # NASAMS: blink emission, high_value_only, remove UAV from whitelist!
            st["emissionPolicyId"] = "blink"
            st["engagementRule"] = "high_value_only"
            st["ammoReserve"] = 0
            st["whitelist"] = ["JET_UAV", "CM", "SCM", "BM", "HBM", "GB", "HELI", "AC_LOW", "AC_HIGH"]
            st["shootLookShoot"] = True
        elif rid == 5:  # IRIS-T: blink emission, shootLookShoot=True
            st["emissionPolicyId"] = "blink"
            st["engagementRule"] = "any"
            st["ammoReserve"] = 0
            st["shootLookShoot"] = True
        elif rid == 7:  # Soviet radar: blink emission
            st["emissionPolicyId"] = "blink"

    decisions_n1: List[Dict[str, Any]] = [
        {
            "phase": "Pre-Night 1 Deployment",
            "clock": "22:00:00",
            "tick": 0,
            "observation": (
                "研读简报、地形与装备参数：① 东北高地(289m)遮挡低空雷达视线，西北-东南河谷(93-110m)是巡航导弹天然走廊；"
                "② NASAMS 单发成本高达 $0.85M，且全关两夜总配额 (perLevelLimit) 仅 24 发！"
                "③ 东侧外围有 6 个声学哨、3 个目视哨与 4 支机动火力组(配探照灯)，足以组成低成本反无人机猎杀带。"
            ),
            "judgment": (
                "制定梯次防空与电磁/弹药严管条令：① 采用 layered 东重纵深布局；"
                "② 将苏制警戒雷达、NASAMS、IRIS-T 全部设为 blink（闪烁开机），减缓暴露度积累并避免试探波过早锁定；"
                "③ 将 NASAMS 设为 high_value_only 并从白名单中剔除 UAV，严禁向 Shahed-136 发射哪怕一发 AIM-120，将廉价无人机全部交给 4 支机动火力组与 IRIS-T 处理；"
                "④ 开局即拉响防空警报。"
            ),
            "action": "Select preset='layered', set radars/SAMs to 'blink', restrict NASAMS to high_value_only (no UAV tag), enable SetAirRaidAlert.",
        }
    ]

    session.start_night({"placements": placements_n1, "seed": 42, "night": 1, "bot": "manual"})
    session.apply_command({"type": "SetAirRaidAlert", "on": True})

    spoofed_n1 = False

    def tick_hook_n1(s: GameSession, tick: int, dlog: List[Dict[str, Any]]) -> None:
        nonlocal spoofed_n1
        if tick >= 14100 and not spoofed_n1:
            spoofed_n1 = True
            s.apply_command({"type": "NationalSpoof"})
            dlog.append({
                "phase": "Night 1 Mid-Battle",
                "clock": format_clock(tick),
                "tick": tick,
                "observation": "01:55 接近简报预警的 02:00 河谷巡航导弹波次窗口，提前激活【国家级 GNSS 导航欺骗网 (NationalSpoof)】。",
                "judgment": "消耗 1 CP 开启全图卫星制导欺骗（持续 3600 秒），不仅能压制接踵而至的 Kh-101 巡航导弹命中精度，还能覆盖到 02:55 的余波。",
                "action": "NationalSpoof()",
            })

    def choice_hook_n1(s: GameSession, tick: int, snap: Dict[str, Any], dlog: List[Dict[str, Any]]) -> None:
        s.apply_command({"type": "AnswerChoice", "option": 0})
        dlog.append({
            "phase": "Night 1 Tactical Dilemma",
            "clock": format_clock(tick),
            "tick": tick,
            "observation": "02:00 河谷出现 6 枚 Kh-101 巡航导弹，苏制雷达触发反辐射预警抉择。",
            "judgment": "选择【选项A：立即关机规避】保护苏制警戒雷达免受锁定，同时依靠 NASAMS 自身的 50km 火控雷达与 IRIS-T 接力，6 枚 Kh-101 巡航导弹在河谷内被 100% 全数击落(6/6)！",
            "action": "AnswerChoice(option=0: 立即关机规避反辐射导弹)",
        })

    n1_res = _run_night_loop(session, decisions_n1, tick_hook_n1, choice_hook_n1)

    # Advance to Night 2 & Post-Night 1 Review
    session.advance_to_next_night()
    placements_n2 = copy.deepcopy(session.placements)
    for u in placements_n2:
        rid = u["rosterId"]
        st = u.setdefault("settings", {})
        if rid == 6:  # Relocate NASAMS >1100m away from [9804.1, 9025.0] -> [10800.0, 9600.0]
            u["pos"] = [10800.0, 9600.0]
            st["emissionPolicyId"] = "continuous"
            st["engagementRule"] = "any"
            st["ammoReserve"] = 2
            st["whitelist"] = ["UAV", "JET_UAV", "CM", "SCM", "BM", "HBM", "GB", "HELI", "AC_LOW", "AC_HIGH"]
            st["shootLookShoot"] = True
        elif rid == 5:  # Relocate IRIS-T >890m away from [12800.0, 10200.0] -> [13600.0, 9800.0]
            u["pos"] = [13600.0, 9800.0]
            st["emissionPolicyId"] = "continuous"
            st["engagementRule"] = "any"
            st["ammoReserve"] = 0
            st["shootLookShoot"] = True
        elif rid == 7:
            st["emissionPolicyId"] = "continuous"

    decisions_n2: List[Dict[str, Any]] = [
        {
            "phase": "Post-Night 1 Review & Night 2 Adjustment",
            "clock": "22:00:00",
            "tick": 0,
            "observation": (
                "复盘第 1 夜战报：斩获 A 级评价 (82.6分)，加权损失仅 6.0%，信任值 +1.0 (51.0)，效费比高达 7.33！"
                "6 枚 Kh-101 巡航导弹 100% 拦截，6 架 Gerbera 诱饵机 100% 识别放过（0 发浪费），机动火力组机枪开火 43 轮！"
                "更重要的是：全夜仅消耗 8 发 AIM-120，为第 2 夜省下了足足 16 发 AIM-120 配额（24 - 8 = 16）！"
                "同时注意到苏制雷达因采用 blink 策略未满暴露，仅有 NASAMS(#6, 100%) 与 IRIS-T(#5, 5% 但被试探波目击) 记录在敌方已知目标列表中。"
            ),
            "judgment": (
                "执行教科书级阵地换防与决战火力配置：① 将 NASAMS(#6) 从 [9804.1, 9025.0] 转移逾 1.1 公里至 [10800.0, 9600.0]，"
                "将 IRIS-T(#5) 从 [12800.0, 10200.0] 转移逾 890 米至 [13600.0, 9800.0]，彻底废除敌方首夜侦察到的 KnownTarget 坐标（使次夜敌方猎杀波次扑空）；"
                "② 鉴于手握 16 发充裕的 AIM-120 剩余配额，次夜解锁 NASAMS 对高危突防无人机的补防权限（设 ammoReserve=2 保底巡航导弹/战机），"
                "确保次夜零新增建筑损伤！"
            ),
            "action": "Relocate NASAMS(#6) -> [10800.0, 9600.0] and IRIS-T(#5) -> [13600.0, 9800.0] (>600m displacement clears KnownTargets); set ammoReserve=2.",
        }
    ]

    session.start_night({"placements": placements_n2, "night": 2, "bot": "manual"})
    session.apply_command({"type": "SetAirRaidAlert", "on": True})

    spoofed_n2 = False

    def tick_hook_n2(s: GameSession, tick: int, dlog: List[Dict[str, Any]]) -> None:
        nonlocal spoofed_n2
        if tick >= 3500 and not spoofed_n2:
            spoofed_n2 = True
            s.apply_command({"type": "NationalSpoof"})
            dlog.append({
                "phase": "Night 2 Mid-Battle",
                "clock": format_clock(tick),
                "tick": tick,
                "observation": "22:58 接近第 2 夜 00:00 战机/巡航导弹复合打击窗口，提前开启【国家级 GNSS 导航欺骗网】。",
                "judgment": "提前压制复合波次制导精度，配合换防后的 NASAMS 与 IRIS-T 形成交叉火力网。",
                "action": "NationalSpoof()",
            })

    def choice_hook_n2(s: GameSession, tick: int, snap: Dict[str, Any], dlog: List[Dict[str, Any]]) -> None:
        s.apply_command({"type": "AnswerChoice", "option": 1})
        dlog.append({
            "phase": "Night 2 Tactical Dilemma",
            "clock": format_clock(tick),
            "tick": tick,
            "observation": "00:00 Su-24M 战机与 Kh-101 巡航导弹进入射界，触发抉择。",
            "judgment": "由于我方防空阵地已在夜前完成换防，敌方猎杀波次掌握的是旧坐标，果断选择【选项B：坚持开机引导拦截】，将 Su-24M 与 3 枚 Kh-101 全部凌空击碎！",
            "action": "AnswerChoice(option=1: 坚持开机引导拦截巡航导弹)",
        })

    n2_res = _run_night_loop(session, decisions_n2, tick_hook_n2, choice_hook_n2)

    return {
        "gameId": "game_3_veteran_commander",
        "personaName": "老练复盘型指挥官 (Veteran Tactical Commander)",
        "personaSummary": (
            "首夜依托东侧声学/目视哨与 4 支探照灯机动火力组构建反无人机外环，将雷达设为闪烁(blink)，"
            "并将 NASAMS 严格限制为 high_value_only（剔除 UAV 白名单），实现 6/6 Kh-101 100% 拦截、6/6 Gerbera 诱饵 100% 放过，"
            "且全夜仅用 8 发 AIM-120（A级，82.6分，损失仅 6%）；"
            "次夜前精准将暴露的 NASAMS 与 IRIS-T 转移逾 800 米使敌方首夜侦察情报作废，凭借省下的 16 发 AIM-120 配额，"
            "在次夜达成 100% 全敌机清零（3/3 Kh-101、14/14 Shahed-136、1/1 Su-24M 全部击落，次夜零新增损伤，A级 89.4分）！"
        ),
        "night1": n1_res,
        "night2": n2_res,
    }


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "x") and hasattr(obj, "y"):
        return [round(float(obj.x), 1), round(float(obj.y), 1)]
    if hasattr(obj, "name"):
        return str(obj.name)
    return str(obj)


def main() -> None:
    print("Running D4-3 AI Playtester (3 games x 2 nights on test_01)...")
    g1 = run_game_1_blind_first_timer()
    print(f"  [Game 1] N1: {g1['night1']['battleReport']['rating']} ({g1['night1']['battleReport']['compositeScore']}) | N2: {g1['night2']['battleReport']['rating']} ({g1['night2']['battleReport']['compositeScore']})")

    g2 = run_game_2_aggressive_fire_at_will()
    print(f"  [Game 2] N1: {g2['night1']['battleReport']['rating']} ({g2['night1']['battleReport']['compositeScore']}) | N2: {g2['night2']['battleReport']['rating']} ({g2['night2']['battleReport']['compositeScore']})")

    g3 = run_game_3_veteran_commander()
    print(f"  [Game 3] N1: {g3['night1']['battleReport']['rating']} ({g3['night1']['battleReport']['compositeScore']}) | N2: {g3['night2']['battleReport']['rating']} ({g3['night2']['battleReport']['compositeScore']})")

    output_data = {
        "taskId": "D4-3",
        "levelId": "test_01",
        "baseSeed": 42,
        "games": [g1, g2, g3],
    }

    out_path = REPO_ROOT / "tools" / "papersim" / "experiments" / "d4_3_playtest_logs.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(f"Saved complete playtest logs to {out_path}")


if __name__ == "__main__":
    main()
