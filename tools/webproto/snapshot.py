"""Compact frame snapshot serializer for tools.webproto."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from tools.papersim.enemy_ai import CommandStage
from tools.papersim.entities import SimEvent
from tools.papersim.world import SimWorld

from .helpers import downsample_elevation, format_clock, tr
from .telemetry import compute_battle_report, format_sim_event


def serialize_level_meta(session: Any, presets: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize full static level, terrain, intel, and unit catalog payload for /api/init."""
    cat = session.level.catalog
    night_def = next(
        (n for n in session.level.waves.get("nights", []) if int(n.get("night", 1)) == session.night_index),
        session.level.waves["nights"][0],
    )
    intel_night = next(
        (n for n in session.level.intel.get("nights", []) if int(n.get("night", 1)) == session.night_index),
        {"items": []},
    )
    intel_items = [
        {
            "textKey": it.get("textKey", ""),
            "text": tr(it.get("textKey", ""), it.get("textKey", "")),
            "accurate": bool(it.get("accurate", True)),
            "confidence": it.get("confidence", "confirmed"),
            "relatedWave": it.get("relatedWave", ""),
        }
        for it in (intel_night.get("items") or [])
    ]

    unit_catalog: List[Dict[str, Any]] = []
    for au in session.level.meta.get("availableUnits") or []:
        uid = str(au["unit"])
        udef = cat.get_player_unit_def(uid)
        ucategory = cat.get_player_unit_category(uid).name.lower()
        weapons_info = []
        for wid in udef.get("weaponIds", []):
            wdef = cat.weapons.get(wid, {})
            weapons_info.append({
                "id": wid,
                "name": tr(wdef.get("nameKey", f"weapon.{wid}.name"), wid),
                "kind": wdef.get("kind", "missile"),
                "rangeM": float(wdef.get("rangeM", 0.0)),
                "ceilingM": float(wdef.get("ceilingM", 0.0)),
                "magazine": wdef.get("magazine"),
                "shotCostMusd": float(wdef.get("shotCostMusd", 0.0) or 0.0),
                "targets": wdef.get("targets", []),
            })
        fcr = udef.get("fireControlRadar")
        unit_catalog.append({
            "unitDefId": uid,
            "name": tr(udef.get("nameKey", uid), uid),
            "category": ucategory,
            "count": int(au.get("count", 1)),
            "source": au.get("source", "city"),
            "mobility": udef.get("mobility", "mobile"),
            "hasRadar": fcr is not None or udef.get("emission") == "active",
            "radarRangeM": float(fcr.get("rangeM", 0.0)) if fcr else 0.0,
            "detectionRangeM": float(udef.get("detectionRangeM") or 0.0),
            "selfAcquisitionRangeM": float(udef.get("selfAcquisitionRangeM") or 0.0),
            "weapons": weapons_info,
        })

    ly = session.level.layers
    kts = []
    for kt in session.carry_in.known_targets or []:
        uid = str(kt.get("unitDefId", ""))
        udef = cat.get_player_unit_def(uid) if uid else {}
        kts.append({
            "rosterId": kt.get("rosterId", 0),
            "unitId": kt.get("unitId", 0),
            "unitDefId": uid,
            "name": tr(udef.get("nameKey", uid), uid or "暴露阵地"),
            "pos": kt.get("pos", [0.0, 0.0]),
            "exposure": round(float(kt.get("exposure", 70.0)), 1),
        })

    return {
        "levelId": session.level.id,
        "nightIndex": session.night_index,
        "totalNights": int(session.level.meta.get("nights", 2)),
        "seed": session.seed,
        "levelName": tr(session.level.meta.get("nameKey", "level.test_01.name"), "测试地图 01"),
        "briefing": tr(session.level.meta.get("briefingKey", "level.test_01.briefing"), ""),
        "date": night_def.get("date", session.level.date),
        "weather": night_def.get("weather", "clear"),
        "season": night_def.get("season", "autumn"),
        "durationWorldSec": float(night_def.get("durationSec", 28800.0)),
        "gameSecToWorldSec": float(cat.conventions.get("gameSecToWorldSec", 60.0)),
        "commandPointsPerNight": int(session.level.meta.get("commandPointsPerNight", 4)),
        "trustScore": round(session.trust_score, 1),
        "map": {
            "widthM": float(session.level.meta.get("map", {}).get("widthM", 20000.0)),
            "heightM": float(session.level.meta.get("map", {}).get("heightM", 20000.0)),
            "minElevationM": session.terrain.min_elevation_m,
            "maxElevationM": session.terrain.max_elevation_m,
            "gridSize": 100,
            "elevationGrid": downsample_elevation(session.terrain, 100),
        },
        "layers": {
            "rivers": [{"id": r.get("id"), "widthM": float(r.get("widthM", 300.0)), "path": [[p.x, p.y] for p in r.get("path", [])]} for r in (ly.get("rivers") or [])],
            "roads": [{"id": r.get("id"), "class": r.get("class", "main"), "path": [[p.x, p.y] for p in r.get("path", [])]} for r in (ly.get("roads") or [])],
            "urban": [{"id": u.get("id"), "density": u.get("density", "core"), "polygon": [[p.x, p.y] for p in u.get("polygon", [])]} for u in (ly.get("urban") or [])],
            "forests": [{"id": f.get("id"), "polygon": [[p.x, p.y] for p in f.get("polygon", [])]} for f in (ly.get("forests") or [])],
        },
        "deploy": {
            "zones": [{"id": z.get("id"), "polygon": [[p.x, p.y] for p in z.get("polygon", [])]} for z in (session.level.deploy.get("zones") or [])],
            "forbidden": [{"id": f.get("id"), "reason": f.get("reason"), "polygon": [[p.x, p.y] for p in f.get("polygon", [])]} for f in (session.level.deploy.get("forbidden") or [])],
            "alternatePositions": [
                {"id": ap.get("id"), "pos": [ap["pos"].x, ap["pos"].y], "surveyed": bool(ap.get("surveyed", True))}
                for ap in (session.level.deploy.get("alternatePositions") or [])
                if ap.get("pos") is not None
            ],
            "minSpacingM": float(cat.rules.get("positions", {}).get("minSpacingM", 100.0)),
        },
        "structures": [
            {
                "id": s["id"],
                "name": tr(s.get("nameKey", f"map.{session.level.id}.{s['id']}"), s["id"]),
                "type": s.get("type", "structure"),
                "pos": [s["pos"].x, s["pos"].y],
                "radiusM": float(s.get("radiusM", 150.0)),
                "hp": int(s.get("hp", 15)),
                "maxHp": int(s.get("maxHp", s.get("hp", 15))),
                "weight": float(s.get("weight", 1.0)),
                "gridNode": s.get("gridNode", ""),
            }
            for s in session.level.structures
        ],
        "grid": {
            "nodes": [{"id": n["id"], "type": n.get("type", "consumer"), "pos": [n["pos"].x, n["pos"].y]} for n in (session.level.grid.get("nodes") or []) if n.get("pos")],
            "links": list(session.level.grid.get("links") or []),
        },
        "entryPoints": [
            {
                "id": ep["id"],
                "name": tr(ep.get("nameKey", ep["id"]), ep["id"]),
                "pos": [ep["pos"].x, ep["pos"].y],
                "warningSec": float(ep.get("warningSec") or 0.0),
            }
            for ep in session.level.entry_points_by_id.values()
        ],
        "intel": intel_items,
        "unitCatalog": unit_catalog,
        "presets": presets,
        "currentPlacements": session.placements,
        "carryIn": {
            "hasCarryIn": session.night_index > 1 and bool(session.carry_in.units or kts),
            "knownTargets": kts,
            "ammoPool": session.carry_in.ammo_pool or {},
            "structures": session.carry_in.structures or [],
            "alertResponsiveness": session.carry_in.alert_responsiveness or 1.0,
            "trustScore": round(session.trust_score, 1),
        },
        "availableBots": ["manual", "smart_blink", "default", "relocator", "wasteful", "hoarder", "passive"],
    }


def serialize_world_snapshot(
    session: Any,
    raw_events: Sequence[SimEvent],
    hard_pause: bool = False,
    pause_reason: Optional[str] = None,
    command_ok: bool = True,
) -> Dict[str, Any]:
    """Serialize current SimWorld state into a compact JSON frame snapshot."""
    w: SimWorld = session.world
    st = w.state
    cat = w.level.catalog
    now_sec = st.tick * w.step_sec

    logs: List[Dict[str, Any]] = list(session.extra_logs)
    session.extra_logs.clear()
    for ev in raw_events:
        item = format_sim_event(w, ev)
        if item is not None:
            logs.append(item)
            if item.get("radio"):
                session.radio_banner = item["radio"]

    kt_positions = [kt.pos for kt in st.enemy_intel.known_targets]
    units_out: List[Dict[str, Any]] = []
    rule_names = {0: "any", 1: "ballistic_only", 2: "hold_fire", 3: "high_value_only"}
    for store, cat_name in (
        (st.fire_units, "fire"),
        (st.sensors, "sensor"),
        (st.ew_units, "ew"),
        (st.deception_units, "deception"),
    ):
        for u in store.alive_list():
            if getattr(u, "automatic", False) or u.pos is None:
                continue
            udef = cat.get_player_unit_def(u.def_id or "")
            is_kt = any(u.pos.distance_to(kp) <= 500.0 for kp in kt_positions)
            weapons_out = []
            if cat_name == "fire":
                for ws in getattr(u, "weapons", []):
                    wdef = cat.weapons.get(ws.weapon_id, {})
                    rounds = sum(ln.rounds for ln in ws.launchers if not ln.destroyed)
                    max_rounds = sum(ln.max_rounds for ln in ws.launchers if not ln.destroyed)
                    reload_rem = max(
                        0.0,
                        max((ln.reload_until_sec - now_sec for ln in ws.launchers if ln.reload_until_sec > now_sec), default=0.0),
                    )
                    wl_set = getattr(ws, "whitelist", None)
                    weapons_out.append({
                        "weaponId": ws.weapon_id,
                        "name": tr(wdef.get("nameKey", f"weapon.{ws.weapon_id}.name"), ws.weapon_id),
                        "kind": wdef.get("kind", "missile"),
                        "rangeM": float(wdef.get("rangeM", 0.0)),
                        "rule": rule_names.get(ws.rule, "any"),
                        "ammoReserve": int(getattr(ws, "ammo_reserve", 0) or 0),
                        "whitelist": [t.name for t in sorted(wl_set, key=lambda x: int(x))] if wl_set else ["UAV", "CM", "BM", "AC_LOW"],
                        "shootLookShoot": bool(getattr(ws, "shoot_look_shoot", True)),
                        "rounds": rounds if rounds < 900000 else -1,
                        "maxRounds": max_rounds if max_rounds < 900000 else -1,
                        "reloadRemSec": round(reload_rem, 1),
                    })
            fcr = udef.get("fireControlRadar")
            det_r = float(fcr.get("rangeM", 0.0)) if fcr else float(udef.get("detectionRangeM") or udef.get("selfAcquisitionRangeM") or 0.0)
            units_out.append({
                "id": u.id,
                "rosterId": u.roster_id,
                "unitDefId": u.def_id,
                "name": tr(udef.get("nameKey", u.def_id or ""), u.def_id or ""),
                "category": cat_name,
                "mobility": udef.get("mobility", "mobile"),
                "pos": [round(u.pos.x, 1), round(u.pos.y, 1)],
                "deployState": u.deploy_state.name,
                "exposure": round(u.exposure, 1),
                "exposurePeak": round(u.exposure_peak, 1),
                "powered": u.powered,
                "lightDamaged": u.light_damaged,
                "radarDestroyed": getattr(u, "radar_destroyed", False),
                "killsTonight": getattr(u, "kills_tonight", 0),
                "isKnownTarget": is_kt,
                "detectionRangeM": round(det_r, 1),
                "emitter": {
                    "hasEmitter": u.emitter is not None,
                    "on": bool(u.emitter.on) if u.emitter else False,
                    "policyId": u.emitter.policy_id if u.emitter else "none",
                },
                "weapons": weapons_out,
                "relocation": {
                    "dest": [u.relocation.dest.x, u.relocation.dest.y],
                    "altId": u.relocation.alternate_position_id,
                } if u.relocation else None,
            })

    tracks_out = []
    for trk in st.tracks.alive_list():
        if trk.pos is None:
            continue
        spd = math.hypot(trk.vel_mps.x, trk.vel_mps.y)
        hdg = math.atan2(trk.vel_mps.y, trk.vel_mps.x)
        tracks_out.append({
            "id": trk.id,
            "threatId": trk.threat_id,
            "quality": int(trk.quality),
            "qualityName": trk.quality.name,
            "pos": [round(trk.pos.x, 1), round(trk.pos.y, 1)],
            "velMps": [round(trk.vel_mps.x, 2), round(trk.vel_mps.y, 2)],
            "speedMps": round(spd, 1),
            "headingRad": round(hdg, 3),
            "tag": trk.tag.name if trk.tag is not None else "UNKNOWN",
            "uncertaintyRadiusM": round(trk.uncertainty_radius_m, 1),
            "cued": trk.cued,
            "classified": trk.classified,
            "identifiedAsDecoy": trk.identified_as_decoy,
        })

    threats_out = []
    for th in st.threats.alive_list():
        if th.pos is None:
            continue
        edef = cat.munitions.get(th.def_id or "") or cat.platforms.get(th.def_id or "") or {}
        threats_out.append({
            "id": th.id,
            "defId": th.def_id,
            "name": tr(edef.get("nameKey", th.def_id or ""), th.def_id or ""),
            "tag": th.tag.name if th.tag is not None else "",
            "pos": [round(th.pos.x, 1), round(th.pos.y, 1)],
            "altM": round(th.alt_m or 0.0, 1),
            "velMps": [round(th.vel_mps.x, 2), round(th.vel_mps.y, 2)],
            "targetPos": [round(th.target_pos.x, 1), round(th.target_pos.y, 1)],
            "isDecoy": th.def_id == "gerbera",
            "ewJammed": th.ew_nav == 2 or th.national_spoof == 2 or th.ew_pull == 2,
        })

    interceptors_out = []
    for ic in st.interceptors.alive_list():
        dur = max(1.0, ic.intercept_sec - ic.launch_sec)
        frac = max(0.0, min(1.0, (now_sec - ic.launch_sec) / dur))
        cx = ic.launch_pos.x + (ic.intercept_pos.x - ic.launch_pos.x) * frac
        cy = ic.launch_pos.y + (ic.intercept_pos.y - ic.launch_pos.y) * frac
        interceptors_out.append({
            "id": ic.id,
            "fireUnitId": ic.fire_unit_id,
            "weaponId": ic.weapon_id,
            "threatId": ic.threat_id,
            "launchPos": [round(ic.launch_pos.x, 1), round(ic.launch_pos.y, 1)],
            "interceptPos": [round(ic.intercept_pos.x, 1), round(ic.intercept_pos.y, 1)],
            "curPos": [round(cx, 1), round(cy, 1)],
            "progress": round(frac, 3),
        })

    active_choice = None
    if st.choices.count_alive() > 0:
        ch = st.choices.alive_list()[0]
        subj = CommandStage._find_unit(w.ctx, ch.subject_unit_id)
        subj_name = f"雷达阵地 #{ch.subject_unit_id}"
        if subj is not None:
            udef = cat.get_player_unit_def(subj.def_id or "")
            subj_name = f"{tr(udef.get('nameKey', subj.def_id or ''), subj.def_id)} #{subj.roster_id or subj.id}"
        active_choice = {
            "choiceId": ch.id,
            "choiceKey": ch.choice_key,
            "title": tr(ch.choice_key, "反辐射导弹与巡航导弹同时逼近，是否立即关机规避？"),
            "optionA": tr(f"{ch.choice_key}.opt_a", "立即关机规避反辐射导弹（保住雷达，巡航导弹可能突防）"),
            "optionB": tr(f"{ch.choice_key}.opt_b", "坚持开机引导拦截（拦截巡航导弹，雷达承担被毁风险）"),
            "defaultOption": ch.default_option,
            "timeoutRealSec": 8.0,
            "subjectUnitId": ch.subject_unit_id,
            "subjectUnitName": subj_name,
        }

    battle_report = None
    carry_out = None
    if w.is_ended:
        res = w.build_result()
        session.last_carry_out = res.carry_out
        battle_report = compute_battle_report(w, res)
        session.last_battle_report = battle_report
        carry_out = res.carry_out

    return {
        "ok": command_ok,
        "nightIndex": session.night_index,
        "tick": st.tick,
        "timeWorldSec": now_sec,
        "clockStr": format_clock(now_sec),
        "durationWorldSec": w.ctx.duration_ticks * w.step_sec,
        "isEnded": w.is_ended,
        "hardPause": hard_pause or (active_choice is not None and session.bot is None),
        "pauseReason": pause_reason or ("choice_requested" if active_choice else None),
        "activeChoice": active_choice,
        "cp": {
            "current": st.commands.command_points,
            "initial": st.commands.command_points_initial,
            "spent": st.commands.command_points_spent,
        },
        "alert": {
            "on": st.civil.alert_on,
            "shelteredFrac": round(st.civil.sheltered_frac, 3),
            "responsiveness": round(st.civil.responsiveness, 3),
            "fatigueSec": round(st.civil.false_alarm_sec, 1),
        },
        "nationalSpoofActive": any(sa.support_kind == 1 and sa.state == 1 for sa in st.support_assets.alive_list()),
        "grid": {
            "collapsed": st.grid.collapsed,
            "unpoweredFrac": round(st.grid.unpowered_consumer_frac, 3),
            "nodes": [
                {"id": gn.def_id, "powered": gn.powered, "destroyed": gn.destroyed, "pos": [gn.pos.x, gn.pos.y]}
                for gn in st.grid_nodes.alive_list() if gn.pos
            ],
        },
        "structures": [
            {
                "id": s.def_id,
                "name": tr(f"map.{w.level.id}.{s.def_id}", s.def_id or ""),
                "pos": [s.pos.x, s.pos.y] if s.pos else [0.0, 0.0],
                "hp": s.hp,
                "maxHp": s.max_hp,
                "powered": s.powered,
                "destroyed": s.destroyed,
                "weight": s.weight,
            }
            for s in st.structures.alive_list()
        ],
        "ammoPool": dict(st.engagement.ammo_pool),
        "units": units_out,
        "tracks": tracks_out,
        "threats": threats_out,
        "interceptors": interceptors_out,
        "events": logs,
        "radioBanner": session.radio_banner,
        "battleReport": battle_report,
        "carryOut": carry_out,
    }
