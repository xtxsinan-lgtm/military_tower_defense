"""Event formatting, frame snapshot serialization, and battle report calculation for tools.webproto."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from tools.papersim.core import Vec2
from tools.papersim.entities import (
    NightOutcome,
    SimEvent,
    SimEventType,
    TrackQuality,
    UnitDeployState,
)
from tools.papersim.world import SimWorld

from .helpers import format_clock, tr


def format_sim_event(world: SimWorld, ev: SimEvent) -> Optional[Dict[str, Any]]:
    """Convert SimEvent into a rich Chinese battle-log entry and FX descriptor."""
    et = ev.type
    clk = format_clock(ev.tick * world.step_sec)
    cat = world.level.catalog

    def unit_name(uid: int) -> str:
        for store in (world.state.fire_units, world.state.sensors, world.state.ew_units, world.state.deception_units):
            u = store.try_get_including_removed(uid)
            if u is not None:
                udef = cat.get_player_unit_def(u.def_id or "")
                return f"{tr(udef.get('nameKey', u.def_id or ''), u.def_id)}#{u.roster_id or u.id}"
        return f"单位#{uid}"

    def enemy_name(def_id: str) -> str:
        edef = cat.munitions.get(def_id) or cat.platforms.get(def_id) or {}
        return tr(edef.get("nameKey", def_id), def_id)

    def struct_name(sid_or_def: Any) -> str:
        if isinstance(sid_or_def, int):
            s = world.state.structures.try_get_including_removed(sid_or_def)
            def_id = (s.def_id if s else "") or ""
        else:
            def_id = str(sid_or_def)
        return tr(f"map.{world.level.id}.{def_id}", def_id)

    if et == SimEventType.NightStarted:
        n_idx = ev.data.get("night_index", 1)
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "info", "text": f"【第 {n_idx} 夜】防空值班开始，全网进入战备状态。"}
    if et == SimEventType.DialogueShown:
        key = ev.data.get("key") or (ev.fields[1] if len(ev.fields) > 1 else "")
        line = tr(str(key), "各单位注意，空袭警报！按预案进入战斗位置。")
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "radio", "text": f"指挥所：{line}", "radio": line}
    if et == SimEventType.EarlyWarning:
        eid = str(ev.data.get("entry_id", ev.fields[1] if len(ev.fields) > 1 else ""))
        brg = round(math.degrees(float(ev.data.get("bearing_rad", 0.0)))) % 360
        is_bm = bool(ev.data.get("ballistic", False))
        ename = tr(f"map.{world.level.id}.{eid}", eid)
        prefix = "弹道导弹预警" if is_bm else "国家预警网"
        msg = f"{prefix}：{ename}（方位 {brg}°）发现空袭编队接近！"
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger" if is_bm else "warn", "text": msg, "radio": msg}
    if et == SimEventType.WaveStarted:
        wid = str(ev.data.get("wave_id", ev.fields[0] if ev.fields else ""))
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "warn", "text": f"敌方波次 [{wid}] 进入战区边界"}
    if et == SimEventType.TrackCreated:
        tid = int(ev.data.get("track_id", ev.fields[0] if ev.fields else 0))
        q = ev.data.get("quality", TrackQuality.Vague)
        q_str = {0: "模糊扇区", 1: "近似航迹", 2: "精确火控"}.get(int(q), "航迹")
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "info", "text": f"建立新航迹 T-{tid}（质量：{q_str}）"}
    if et == SimEventType.DecoyIdentified:
        tid = int(ev.data.get("track_id", ev.fields[0] if ev.fields else 0))
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "success", "text": f"雷达特征比对：航迹 T-{tid} 识破为【Gerbera 廉价诱饵】，全网自动停火省弹！"}
    if et == SimEventType.InterceptorLaunched:
        fuid = int(ev.data.get("fire_unit_id", ev.fields[1] if len(ev.fields) > 1 else 0))
        wid = str(ev.data.get("weapon_id", ev.fields[2] if len(ev.fields) > 2 else ""))
        wname = tr(f"weapon.{wid}.name", wid)
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "info", "text": f"{unit_name(fuid)} 发射 {wname} 迎击目标"}
    if et == SimEventType.GunFired:
        fuid = int(ev.data.get("fire_unit_id", ev.fields[0] if ev.fields else 0))
        fu = world.state.fire_units.try_get_including_removed(fuid)
        pos = [fu.pos.x, fu.pos.y] if fu and fu.pos else None
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "info", "text": f"{unit_name(fuid)} 高炮/机枪点射拦截", "fx": {"kind": "gun", "pos": pos}}
    if et == SimEventType.InterceptResolved:
        hit = bool(ev.data.get("hit", ev.fields[4] if len(ev.fields) > 4 else False))
        p_raw = ev.data.get("pos") or (ev.fields[5] if len(ev.fields) > 5 else None)
        pos = [p_raw.x, p_raw.y] if hasattr(p_raw, "x") else None
        if hit:
            return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "success", "text": "拦截命中！敌空中目标在空中解体", "fx": {"kind": "hit", "pos": pos}}
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "warn", "text": "拦截弹脱靶，正在重新解算诸元", "fx": {"kind": "miss", "pos": pos}}
    if et == SimEventType.ThreatImpacted:
        def_id = str(ev.data.get("def_id", ev.fields[1] if len(ev.fields) > 1 else ""))
        hit = bool(ev.data.get("hit", False))
        p_raw = ev.data.get("pos") or (ev.fields[3] if len(ev.fields) > 3 else None)
        pos = [p_raw.x, p_raw.y] if hasattr(p_raw, "x") else None
        if hit:
            return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": f"{enemy_name(def_id)} 突防命中地面目标！", "fx": {"kind": "impact_hit", "pos": pos}}
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "info", "text": f"{enemy_name(def_id)} 偏离目标落入空地", "fx": {"kind": "impact_miss", "pos": pos}}
    if et == SimEventType.StructureDamaged:
        sdef = ev.fields[1] if len(ev.fields) > 1 else ""
        hp = ev.data.get("hp", 0)
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": f"保护目标【{struct_name(sdef)}】受损（剩余 HP: {hp}）！"}
    if et == SimEventType.StructureDestroyed:
        sdef = ev.fields[1] if len(ev.fields) > 1 else ""
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": f"保护目标【{struct_name(sdef)}】被彻底摧毁！", "radio": f"报告指挥所，{struct_name(sdef)}失去功能！"}
    if et == SimEventType.GridPowerChanged:
        powered = bool(ev.data.get("powered", False))
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "warn" if powered else "danger", "text": "电网节点恢复供电" if powered else "警告：变电节点断电，下游防空阵地转入备用电池！"}
    if et == SimEventType.ExposureThresholdCrossed:
        uid = int(ev.data.get("unit_id", 0))
        th_v = int(ev.data.get("threshold", 70))
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger" if th_v >= 70 else "warn", "text": f"电子侦察告警：{unit_name(uid)} 暴露度突破 {th_v}%！建议立即关机或转移阵地"}
    if et == SimEventType.KnownTargetAdded:
        uid = int(ev.data.get("unit_id", 0))
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": f"敌军侦察已标定 {unit_name(uid)} 坐标并写入猎杀清单！"}
    if et == SimEventType.ArmThreatDetected:
        uid = int(ev.data.get("unit_id", 0))
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": f"反辐射告警！敌导弹导引头已锁定 {unit_name(uid)}！", "radio": f"告警！反辐射导弹锁定 {unit_name(uid)}！"}
    if et == SimEventType.ChoiceRequested:
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": "紧急战术抉择触发！请在 8.0 秒内下达指令"}
    if et == SimEventType.ChoiceResolved:
        opt = int(ev.data.get("option", 0))
        opt_txt = "立即关机规避" if opt == 0 else "坚持开机拦截"
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "info", "text": f"紧急抉择已执行：【{opt_txt}】"}
    if et == SimEventType.EwLinkCut or et == SimEventType.EwDiverted:
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "success", "text": "电子战压制生效：敌机导航/链路受干扰偏航！"}
    if et == SimEventType.MunitionReleased:
        cdef = str(ev.fields[2] if len(ev.fields) > 2 else "kh59")
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": f"敌空中平台防区外投射【{enemy_name(cdef)}】！"}
    if et == SimEventType.AmmoDepleted:
        uid = int(ev.data.get("unit_id", ev.fields[0] if ev.fields else 0))
        wid = str(ev.data.get("weapon_id", ev.fields[1] if len(ev.fields) > 1 else ""))
        wname = tr(f"weapon.{wid}.name", wid)
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "warn", "text": f"弹药告罄：{unit_name(uid)} 的【{wname}】已打空！"}
    if et == SimEventType.PlayerUnitDamaged:
        uid = int(ev.data.get("unit_id", ev.fields[0] if ev.fields else 0))
        dmg_kind = str(ev.fields[2] if len(ev.fields) > 2 else ev.data.get("damage_kind", "damaged"))
        dmg_desc = {
            "light_damage": "轻伤（作战效能降至 80%）",
            "heavy_damage": "重创（暂停作战 30 分钟抢修）",
            "radar_destroyed": "火控雷达被毁（丧失自主照射能力）",
            "launcher_destroyed": "发射架损毁（减少 1 部发射架）",
        }.get(dmg_kind, "受损")
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": f"阵地受损：{unit_name(uid)} 遭敌方火力打击——{dmg_desc}！"}
    if et == SimEventType.PlayerUnitDestroyed:
        uid = int(ev.data.get("unit_id", ev.fields[0] if ev.fields else 0))
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "danger", "text": f"阵地全毁：{unit_name(uid)} 被敌方火力彻底摧毁！", "radio": f"报告指挥所，{unit_name(uid)} 失去联络！"}
    if et == SimEventType.DebrisFell:
        p_raw = ev.data.get("pos") or (ev.fields[2] if len(ev.fields) > 2 else None)
        pos = [round(p_raw.x), round(p_raw.y)] if hasattr(p_raw, "x") else [0, 0]
        fx_pos = [p_raw.x, p_raw.y] if hasattr(p_raw, "x") else None
        return {"tick": ev.tick, "clock": clk, "type": et.name, "level": "warn", "text": f"拦截残骸坠入城区（[{pos[0]}, {pos[1]}]），造成附带损伤！", "fx": {"kind": "miss", "pos": fx_pos}}
    return None


def compute_battle_report(world: SimWorld, res: Any) -> Dict[str, Any]:
    """Compute comprehensive post-night battle report including rating, exchange ratio, and trust breakdown."""
    cat = world.level.catalog
    st = world.state
    sc = st.scoring

    spawned_by_def: Dict[str, int] = {}
    for ev in world.events._outbox:
        if ev.type == SimEventType.ThreatSpawned and len(ev.fields) >= 2:
            d = str(ev.fields[1])
            spawned_by_def[d] = spawned_by_def.get(d, 0) + 1
        elif ev.type == SimEventType.MunitionReleased and len(ev.fields) >= 3:
            d = str(ev.fields[2])
            spawned_by_def[d] = spawned_by_def.get(d, 0) + 1

    kills_by_e = dict(sc.kills_by_enemy)
    leaks_by_e = dict(sc.leaks_by_enemy)
    per_enemy: List[Dict[str, Any]] = []
    for eid in sorted(set(spawned_by_def.keys()) | set(kills_by_e.keys()) | set(leaks_by_e.keys())):
        sp = spawned_by_def.get(eid, kills_by_e.get(eid, 0) + leaks_by_e.get(eid, 0))
        kl = kills_by_e.get(eid, 0)
        lk = leaks_by_e.get(eid, 0)
        edef = cat.munitions.get(eid) or cat.platforms.get(eid) or {}
        per_enemy.append({
            "enemyId": eid,
            "name": tr(edef.get("nameKey", eid), eid),
            "isDecoy": eid == "gerbera",
            "spawned": sp,
            "killed": kl,
            "leaked": lk,
            "interceptRate": round(kl / sp, 4) if sp > 0 else 1.0,
        })

    decoy_sp = spawned_by_def.get("gerbera", 0)
    decoy_kl = kills_by_e.get("gerbera", 0)
    non_decoy_sp = max(0, sum(spawned_by_def.values()) - decoy_sp)
    non_decoy_kl = max(0, sum(kills_by_e.values()) - decoy_kl)
    nd_rate = (non_decoy_kl / non_decoy_sp) if non_decoy_sp > 0 else 1.0

    # Trust breakdown (05 §3.4.2)
    econ = cat.rules.get("economy", {})
    trust_cfg = econ.get("trust", {})
    bands = trust_cfg.get("exchangeBands", [
        {"minRatio": 0.0, "delta": -3}, {"minRatio": 0.4, "delta": -1},
        {"minRatio": 1.5, "delta": 0}, {"minRatio": 4.0, "delta": 1}, {"minRatio": 10.0, "delta": 3},
    ])
    ex = res.exchange
    ratio = ex.get("exchangeRatio")
    def_cost = float(ex.get("defenseCostMusd", 0.0) or 0.0)
    pot_avoided = float(ex.get("enemyDestroyedValueMusd", 0.0) or 0.0)

    d_ex = 0.0
    if ratio is not None and def_cost >= float(trust_cfg.get("minShotCostForExchangeMusd", 0.5)):
        for b in bands:
            if float(ratio) >= float(b["minRatio"]) - 1e-9:
                d_ex = float(b["delta"])

    shots_by_w = res.ammo.get("shotsFiredByWeapon", {})
    hits_by_w = res.ammo.get("hitsByWeapon", {})
    waste_by_w = ex.get("wastefulShotsByWeapon", {})
    raw_cost_by_w = ex.get("rawEnemyCostByWeapon", {})
    w_shots = 0
    wasted_weapons: List[str] = []
    for wid, shots in shots_by_w.items():
        kills = int(hits_by_w.get(wid, 0))
        wdef = cat.weapons.get(wid, {})
        avg_cost = float(wdef.get("shotCostMusd", 0.0) or 0.0)
        if shots > 0 and kills >= 1 and avg_cost >= 0.8:
            raw_val = float(raw_cost_by_w.get(wid, 0.0))
            if (raw_val / max(1e-9, shots * avg_cost)) < 0.2:
                w_cnt = int(waste_by_w.get(wid, 0)) or int(shots)
                w_shots += w_cnt
                wasted_weapons.append(tr(f"weapon.{wid}.name", wid))

    d_waste = -min(w_shots * 3.0, 9.0)
    inquiry = w_shots >= 2
    d_inq = -3.0 if inquiry else 0.0

    high_leaks = sum(cnt for eid, cnt in leaks_by_e.items() if eid in ("kh101", "kh59", "kh22", "iskander_m", "kinzhal"))
    from tools.papersim.engagement import ScoringSystem
    exp_left = ScoringSystem.compute_expensive_rounds_left(world.ctx)
    hoard_leaks = high_leaks if exp_left > 0 else 0
    d_hoard = -min(hoard_leaks * 2.0, 6.0)
    applied_trust = max(-12.0, min(8.0, d_ex + d_waste + d_inq + d_hoard))

    survived = int(res.outcome) == int(NightOutcome.Survived)
    w_loss = float(res.losses.get("weightedStructureLossFrac", 0.0))
    units_lost = len(res.losses.get("unitsDestroyed", []))
    if not survived:
        comp_score, rating = 0.0, "F"
    else:
        s_part = 50.0 * max(0.0, 1.0 - w_loss / 0.65)
        i_part = 25.0 * max(0.0, min(1.0, nd_rate))
        e_part = 15.0 * max(0.0, min(1.0, (applied_trust + 12.0) / 20.0))
        f_part = 10.0 * max(0.0, 1.0 - units_lost / 16.0)
        comp_score = round(s_part + i_part + e_part + f_part, 1)
        if w_loss <= 0.05 and units_lost == 0 and comp_score >= 88.0:
            rating = "S"
        elif w_loss <= 0.15 and comp_score >= 78.0:
            rating = "A"
        elif w_loss <= 0.30 and comp_score >= 65.0:
            rating = "B"
        elif w_loss <= 0.45 and comp_score >= 50.0:
            rating = "C"
        else:
            rating = "D"

    kt_list = res.carry_out.get("knownTargets") or []
    exposed_summary = []
    for kt in kt_list:
        uid = str(kt.get("unitDefId", ""))
        udef = cat.get_player_unit_def(uid) if uid else {}
        exposed_summary.append({
            "rosterId": kt.get("rosterId", 0),
            "unitId": kt.get("unitId", 0),
            "unitDefId": uid,
            "name": tr(udef.get("nameKey", uid), uid or "防空阵地"),
            "pos": kt.get("pos", [0.0, 0.0]),
            "exposure": round(float(kt.get("exposure", 70.0)), 1),
        })

    return {
        "nightIndex": res.night_index,
        "survived": survived,
        "outcome": res.outcome.name,
        "outcomeText": tr(f"ui.result.outcome.{res.outcome.name}", "守住了" if survived else "防线失守"),
        "endReason": res.end_reason.name,
        "endReasonText": tr(f"ui.result.reason.{res.end_reason.name}", res.end_reason.name),
        "rating": rating,
        "compositeScore": comp_score,
        "weightedLossFrac": round(w_loss, 4),
        "nonDecoyInterceptRate": round(nd_rate, 4),
        "decoyLetThroughRate": round((decoy_sp - decoy_kl) / decoy_sp, 4) if decoy_sp > 0 else 1.0,
        "defenseCostMusd": round(def_cost, 3),
        "potentialLossAvoidedMusd": round(pot_avoided, 3),
        "exchangeRatio": round(float(ratio), 2) if ratio is not None else None,
        "perEnemy": per_enemy,
        "shotsByWeapon": {tr(f"weapon.{k}.name", k): v for k, v in shots_by_w.items()},
        "hitsByWeapon": {tr(f"weapon.{k}.name", k): v for k, v in hits_by_w.items()},
        "trust": {
            "dEx": d_ex,
            "dWaste": d_waste,
            "dInq": d_inq,
            "dHoard": d_hoard,
            "applied": applied_trust,
            "inquiry": inquiry,
            "wastedWeapons": wasted_weapons,
            "hoardLeaks": hoard_leaks,
            "expensiveRoundsLeft": exp_left,
        },
        "exposedPositions": exposed_summary,
        "unitsDestroyed": res.losses.get("unitsDestroyed", []),
        "canAdvanceToNight2": res.night_index < 2,
    }
