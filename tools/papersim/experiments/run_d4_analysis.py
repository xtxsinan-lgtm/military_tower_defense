#!/usr/bin/env python3
"""D4-1 Playability & Balance Quantitative Analysis Runner using tools/papersim.

Executes Monte Carlo simulations (N=20..30 seeds per configuration) across:
  1. Experiment 1: 8 Bots on test_01 (Night 1, Night 2 chained, and 2-Night Combined)
  2. Experiment 2: 4 Deployment Topologies (Series 2A: Standard test_01; Series 2B: Combined-Arms with EW/Decoy/ARM)
  3. Experiment 3: Targeted Mechanism & Hypothesis Verification for H-01..H-15 and B-T3-01..10

Outputs all raw and aggregated statistics to tools/papersim/experiments/d4_results.json.
"""

from __future__ import annotations

import copy
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.papersim.bots import (
    AlwaysEmitBot,
    DefaultBot,
    HoarderBot,
    NeverEmitBot,
    PassiveBot,
    RelocatorBot,
    SmartBlinkBot,
    TacticalBot,
    WastefulBot,
    create_bot,
)
from tools.papersim.core import Geo, SimRandom, Vec2
from tools.papersim.entities import (
    CarryIn,
    DeploymentPlan,
    NightOutcome,
    PlacedUnit,
    SimCommand,
    SimConfig,
    SimEventType,
    SupportAsset,
    TargetTag,
)
from tools.papersim. loader import DataLoader, FileSystemDataSource, LevelData
from tools.papersim.terrain import TerrainModel
from tools.papersim.world import DefaultDeploymentBuilder, SimWorld

# ---------------------------------------------------------------------------
# Worker-level HorizonProfile & LevelData cache for fast Monte Carlo runs
# ---------------------------------------------------------------------------
_HORIZON_CACHE: Dict[Tuple[Any, ...], Any] = {}
_ORIG_BUILD_HORIZON = TerrainModel.build_horizon_profile
_WORKER_SOURCE: Optional[FileSystemDataSource] = None
_WORKER_LEVELS: Dict[Tuple[str, Optional[int]], LevelData] = {}


def _cached_build_horizon_profile(
    self: TerrainModel,
    observer: Vec2,
    observer_agl_m: float,
    max_range_m: float,
    azimuth_bins: Optional[int] = None,
) -> Any:
    key = (
        id(self.heightmap),
        round(observer.x, 2),
        round(observer.y, 2),
        round(observer_agl_m, 2),
        round(max_range_m, 2),
        azimuth_bins,
    )
    prof = _HORIZON_CACHE.get(key)
    if prof is None:
        prof = _ORIG_BUILD_HORIZON(self, observer, observer_agl_m, max_range_m, azimuth_bins)
        _HORIZON_CACHE[key] = prof
    return prof


TerrainModel.build_horizon_profile = _cached_build_horizon_profile  # type: ignore[method-assign]


def get_level(level_id: str = "test_01", night_index: Optional[int] = 1) -> LevelData:
    global _WORKER_SOURCE
    if _WORKER_SOURCE is None:
        _WORKER_SOURCE = FileSystemDataSource(REPO_ROOT / "data")
    key = (level_id, night_index)
    if key not in _WORKER_LEVELS:
        _WORKER_LEVELS[key] = DataLoader.load_level(_WORKER_SOURCE, level_id, night_index=night_index)
    return _WORKER_LEVELS[key]


# ---------------------------------------------------------------------------
# Statistical Helpers
# ---------------------------------------------------------------------------
def summarize_metric(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "sd": 0.0, "min": 0.0, "p10": 0.0, "p50": 0.0, "p90": 0.0, "max": 0.0}
    s = sorted(float(v) for v in values)
    n = len(s)

    def pct(p: float) -> float:
        idx = p * (n - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return s[lo]
        return s[lo] + (idx - lo) * (s[hi] - s[lo])

    mean_v = sum(s) / n
    sd_v = statistics.stdev(s) if n > 1 else 0.0
    return {
        "mean": round(mean_v, 4),
        "sd": round(sd_v, 4),
        "min": round(s[0], 4),
        "p10": round(pct(0.10), 4),
        "p50": round(pct(0.50), 4),
        "p90": round(pct(0.90), 4),
        "max": round(s[-1], 4),
    }


# ---------------------------------------------------------------------------
# Trust & Composite Rating Calculation (05_campaign_economy.md §3.4.2)
# ---------------------------------------------------------------------------
def compute_trust_for_night(world: SimWorld, res: Any) -> Dict[str, Any]:
    cat = world.level.catalog
    econ = cat.rules.get("economy", {})
    trust_cfg = econ.get("trust", {})
    bands = trust_cfg.get(
        "exchangeBands",
        [
            {"minRatio": 0.0, "delta": -3},
            {"minRatio": 0.4, "delta": -1},
            {"minRatio": 1.5, "delta": 0},
            {"minRatio": 4.0, "delta": 1},
            {"minRatio": 10.0, "delta": 3},
        ],
    )
    min_shot_cost = float(trust_cfg.get("minShotCostForExchangeMusd", 0.5))
    ex = res.exchange
    ratio = ex.get("exchangeRatio")
    tot_shot_cost = float(ex.get("defenseCostMusd", 0.0) or 0.0)

    if ratio is None or tot_shot_cost < min_shot_cost:
        d_ex = 0.0
    else:
        d_ex = 0.0
        for b in bands:
            if float(ratio) >= float(b["minRatio"]) - 1e-12:
                d_ex = float(b["delta"])

    ww_cfg = trust_cfg.get(
        "wastefulWeapon",
        {
            "minAvgShotCostMusd": 0.8,
            "maxRatio": 0.2,
            "minKills": 1,
            "penaltyPerShot": 3,
            "maxPenaltyPerNight": 9,
        },
    )
    w_shots = 0
    wasted_weapons: List[str] = []
    shots_by_w = res.ammo.get("shotsFiredByWeapon", {})
    hits_by_w = res.ammo.get("hitsByWeapon", {})
    waste_by_w = ex.get("wastefulShotsByWeapon", {})
    raw_cost_by_w = ex.get("rawEnemyCostByWeapon", {})
    for wid, shots in shots_by_w.items():
        kills = int(hits_by_w.get(wid, 0))
        if shots == 0 or kills < int(ww_cfg.get("minKills", 1)):
            continue
        wdef = cat.weapons.get(wid, {})
        avg_cost = float(wdef.get("shotCostMusd", 0.0) or 0.0)
        if avg_cost < float(ww_cfg.get("minAvgShotCostMusd", 0.8)):
            continue
        w_waste_cnt = int(waste_by_w.get(wid, 0))
        raw_val = float(raw_cost_by_w.get(wid, 0.0))
        w_raw_ratio = raw_val / max(1e-9, shots * avg_cost)
        if w_waste_cnt > 0 or w_raw_ratio < float(ww_cfg.get("maxRatio", 0.2)):
            w_shots += max(w_waste_cnt, int(shots))
            wasted_weapons.append(wid)
    d_waste = -min(w_shots * float(ww_cfg.get("penaltyPerShot", 3.0)), float(ww_cfg.get("maxPenaltyPerNight", 9.0)))

    inq_cfg = trust_cfg.get("inquiry", {"minWastefulShots": 2, "penalty": 3})
    inquiry = w_shots >= int(inq_cfg.get("minWastefulShots", 2))
    d_inq = -float(inq_cfg.get("penalty", 3.0)) if inquiry else 0.0

    # High-threat leaks (CM/BM/HBM/SCM, i.e., kh101/kh59/iskander/kinzhal/s300_ground) when expensive SAM rounds remain
    leaks_by_e = ex.get("leaksByEnemy", {})
    high_threat_leaks = sum(
        cnt
        for eid, cnt in leaks_by_e.items()
        if eid in ("kh101", "kh59", "kh22", "iskander_m", "kinzhal", "s300_ground", "kalibr", "fab500")
    )
    expensive_rounds_left = 0
    for fu in world.state.fire_units.alive_list():
        for wslot in fu.weapons:
            wdef = cat.weapons.get(wslot.weapon_id, {})
            if float(wdef.get("shotCostMusd", 0.0) or 0.0) >= 0.35 or wslot.weapon_id in (
                "nasams_missile",
                "iris_t_sls_missile",
                "pac2",
                "pac3_mse",
                "s300_missile",
                "samp_t_missile",
                "s200_missile",
            ):
                expensive_rounds_left += sum(ln.rounds for ln in wslot.launchers if not ln.destroyed)
    hoard_leaks = high_threat_leaks if expensive_rounds_left > 0 else 0
    hl_cfg = trust_cfg.get("hoardedLeak", {"penaltyPerLeak": 2, "maxPenaltyPerNight": 6})
    d_hoard = -min(hoard_leaks * float(hl_cfg.get("penaltyPerLeak", 2.0)), float(hl_cfg.get("maxPenaltyPerNight", 6.0)))

    d_border = 0.0
    raw = d_ex + d_waste + d_inq + d_hoard + d_border
    clamp_cfg = trust_cfg.get("nightDeltaClamp", {"min": -12, "max": 8})
    applied = max(float(clamp_cfg.get("min", -12.0)), min(float(clamp_cfg.get("max", 8.0)), raw))
    return {
        "dEx": d_ex,
        "dWaste": d_waste,
        "dInq": d_inq,
        "dHoard": d_hoard,
        "dBorder": d_border,
        "raw": raw,
        "applied": applied,
        "inquiry": inquiry,
        "wastedWeapons": wasted_weapons,
        "highThreatLeaksWithReserve": hoard_leaks,
        "expensiveRoundsLeft": expensive_rounds_left,
    }


def compute_composite_score_and_rating(
    survived: bool,
    weighted_loss_frac: float,
    non_decoy_intercept_rate: float,
    trust_delta: float,
    units_lost: int,
    total_units: int = 16,
) -> Tuple[float, str]:
    if not survived:
        return 0.0, "F"
    struct_score = 50.0 * max(0.0, 1.0 - weighted_loss_frac / 0.65)
    intercept_score = 25.0 * max(0.0, min(1.0, non_decoy_intercept_rate))
    econ_score = 15.0 * max(0.0, min(1.0, (trust_delta + 12.0) / 20.0))
    force_score = 10.0 * max(0.0, 1.0 - units_lost / max(1, total_units))
    score = round(struct_score + intercept_score + econ_score + force_score, 2)
    if weighted_loss_frac <= 0.05 and units_lost == 0 and score >= 88.0:
        rating = "S"
    elif weighted_loss_frac <= 0.15 and score >= 78.0:
        rating = "A"
    elif weighted_loss_frac <= 0.30 and score >= 65.0:
        rating = "B"
    elif weighted_loss_frac <= 0.45 and score >= 50.0:
        rating = "C"
    else:
        rating = "D"
    return score, rating


# ---------------------------------------------------------------------------
# Detailed Single-Night Telemetry Extraction
# ---------------------------------------------------------------------------
def extract_night_metrics(world: SimWorld, res: Any) -> Dict[str, Any]:
    st = world.state
    sc = st.scoring
    cat = world.level.catalog

    all_events = world.events._outbox
    spawned_by_def: Dict[str, int] = {}
    threat_def_by_id: Dict[int, str] = {}
    urban_L_ge_1_hits = 0
    urban_same_cell_struct_hits = 0
    arm_missed_cnt = 0

    struct_cells = set()
    for s_ent in st.structures.alive_list():
        if s_ent.pos is not None:
            struct_cells.add((int(s_ent.pos.x // 1000.0), int(s_ent.pos.y // 1000.0)))

    for ev in all_events:
        et = ev.type
        if et == SimEventType.ThreatSpawned:
            tid, def_id = int(ev.fields[0]), str(ev.fields[1])
            spawned_by_def[def_id] = spawned_by_def.get(def_id, 0) + 1
            threat_def_by_id[tid] = def_id
        elif et == SimEventType.MunitionReleased:
            cid, cdef = int(ev.fields[1]), str(ev.fields[2])
            spawned_by_def[cdef] = spawned_by_def.get(cdef, 0) + 1
            threat_def_by_id[cid] = cdef
        elif et == SimEventType.ThreatImpacted:
            if len(ev.fields) >= 3 and str(ev.fields[2]) == "arm_missed":
                arm_missed_cnt += 1
        elif et == SimEventType.DebrisFell:
            tid = int(ev.fields[1])
            pos = ev.fields[2]
            tdef = threat_def_by_id.get(tid, "")
            mdef = cat.munitions.get(tdef, {})
            dmg_lvl = int(mdef.get("damageLevel", 0) or 0)
            L = int(math.floor(dmg_lvl * 0.3 + 0.5))
            if L >= 1:
                urban_L_ge_1_hits += 1
                if isinstance(pos, Vec2):
                    cell = (int(pos.x // 1000.0), int(pos.y // 1000.0))
                    if cell in struct_cells:
                        urban_same_cell_struct_hits += 1

    kills_by_enemy = dict(sc.kills_by_enemy)
    leaks_by_enemy = dict(sc.leaks_by_enemy)

    decoy_spawned = spawned_by_def.get("gerbera", 0)
    decoy_killed = kills_by_enemy.get("gerbera", 0)
    total_spawned = sum(spawned_by_def.values())
    non_decoy_spawned = max(0, total_spawned - decoy_spawned)
    total_killed = sum(kills_by_enemy.values())
    non_decoy_killed = max(0, total_killed - decoy_killed)

    non_decoy_intercept_rate = (non_decoy_killed / non_decoy_spawned) if non_decoy_spawned > 0 else 1.0
    decoy_let_through_rate = ((decoy_spawned - decoy_killed) / decoy_spawned) if decoy_spawned > 0 else 1.0

    per_threat_rates: Dict[str, float] = {}
    for k, cnt in spawned_by_def.items():
        if cnt > 0:
            per_threat_rates[k] = round(kills_by_enemy.get(k, 0) / cnt, 4)

    exp_units = res.exposure.get("units", [])
    exp_100_cnt = sum(
        1 for u in exp_units if float(u.get("exposure", 0.0)) >= 100.0 - 1e-6 or float(u.get("peak", 0.0)) >= 100.0 - 1e-6
    )
    max_exp = max((float(u.get("peak", u.get("exposure", 0.0))) for u in exp_units), default=0.0)
    mean_exp = (sum(float(u.get("exposure", 0.0)) for u in exp_units) / len(exp_units)) if exp_units else 0.0

    unit_losses = res.losses.get("unitsDestroyed", [])
    units_lost_cnt = len(unit_losses)
    co_units = res.carry_out.get("units", [])
    light_dmg_cnt = sum(1 for u in co_units if u.get("lightDamaged"))
    crippled_cnt = sum(1 for u in co_units if (u.get("radarDestroyed") or int(u.get("launchersLost", 0)) > 0))

    kt_out = res.carry_out.get("knownTargets") or []
    kt_count = len(kt_out)

    trust_info = compute_trust_for_night(world, res)
    survived = int(res.outcome) == int(NightOutcome.Survived)
    w_loss = float(res.losses.get("weightedStructureLossFrac", 0.0))
    comp_score, rating = compute_composite_score_and_rating(
        survived=survived,
        weighted_loss_frac=w_loss,
        non_decoy_intercept_rate=non_decoy_intercept_rate,
        trust_delta=trust_info["applied"],
        units_lost=units_lost_cnt,
    )

    shots_by_weapon = {k: int(v) for k, v in res.ammo.get("shotsFiredByWeapon", {}).items()}
    hits_by_weapon = {k: int(v) for k, v in res.ammo.get("hitsByWeapon", {}).items()}
    total_intercepts = sum(kills_by_enemy.values())
    urban_hits = int(sc.debris_urban_hits)
    urban_ratio = (urban_hits / total_intercepts) if total_intercepts > 0 else 0.0
    end_detail = st.end_request.detail if st.end_request else "survived"

    return {
        "outcome": int(res.outcome),
        "survived": 1.0 if survived else 0.0,
        "end_reason": int(res.end_reason),
        "end_detail": end_detail,
        "end_time_sec": res.end_time_sec,
        "weighted_loss_frac": round(w_loss, 4),
        "spawned_by_def": spawned_by_def,
        "kills_by_enemy": kills_by_enemy,
        "leaks_by_enemy": leaks_by_enemy,
        "per_threat_intercept_rate": per_threat_rates,
        "non_decoy_spawned": non_decoy_spawned,
        "non_decoy_killed": non_decoy_killed,
        "non_decoy_intercept_rate": round(non_decoy_intercept_rate, 4),
        "decoy_spawned": decoy_spawned,
        "decoy_killed": decoy_killed,
        "decoy_let_through_rate": round(decoy_let_through_rate, 4),
        "threats_impacted": int(sum(leaks_by_enemy.values())),
        "threats_ew_downed": int(sc.threats_ew_downed),
        "threats_arm_missed": arm_missed_cnt,
        "high_threat_leaks_with_reserve": int(trust_info["highThreatLeaksWithReserve"]),
        "expensive_rounds_left": int(trust_info["expensiveRoundsLeft"]),
        "units_lost_count": units_lost_cnt,
        "unit_losses": unit_losses,
        "light_damaged_count": light_dmg_cnt,
        "crippled_count": crippled_cnt,
        "exp_100_count": exp_100_cnt,
        "max_exposure": round(max_exp, 2),
        "mean_exposure": round(mean_exp, 2),
        "known_targets_out_count": kt_count,
        "shot_cost_musd": round(float(res.exchange.get("defenseCostMusd", 0.0) or 0.0), 4),
        "potential_loss_musd": round(float(res.exchange.get("enemyDestroyedValueMusd", 0.0) or 0.0), 4),
        "enemy_destroyed_value_musd": round(float(sc.enemy_destroyed_value_musd), 4),
        "exchange_ratio": round(float(res.exchange.get("exchangeRatio") or 0.0), 4),
        "shots_by_weapon": shots_by_weapon,
        "hits_by_weapon": hits_by_weapon,
        "urban_intercept_count": urban_hits,
        "urban_intercept_ratio": round(urban_ratio, 4),
        "urban_L_ge_1_hits": urban_L_ge_1_hits,
        "urban_same_cell_struct_hits": urban_same_cell_struct_hits,
        "cp_spent": int(res.commands.get("commandPointsSpent", 0)),
        "relocations_completed": int(res.commands.get("relocationsCompleted", 0)),
        "trust": trust_info,
        "composite_score": comp_score,
        "rating": rating,
        "structures_end": res.losses.get("structures", []),
    }


def make_carry_in_from_night1(res1: Any, daytime_exposure_decay: float = 0.0) -> CarryIn:
    co = res1.carry_out
    units_in: List[Dict[str, Any]] = []
    for u in co["units"]:
        u_copy = dict(u)
        u_copy["exposure"] = max(0.0, float(u.get("exposure", 0.0)) - daytime_exposure_decay)
        units_in.append(u_copy)
    return CarryIn(
        units=units_in,
        structures=copy.deepcopy(co["structures"]),
        ammo_pool=dict(co["ammoPool"]),
        per_level_used=dict(co["perLevelUsed"]),
        alert_responsiveness=float(co["alertResponsiveness"]),
        known_targets=copy.deepcopy(co["knownTargets"]),
    )


# ---------------------------------------------------------------------------
# Experiment 1 Worker: 8 Bots on test_01 (Night 1 -> Night 2 chained)
# ---------------------------------------------------------------------------
def _run_exp1_single(args: Tuple[str, int]) -> Dict[str, Any]:
    bot_name, seed = args
    lvl_n1 = get_level("test_01", night_index=1)
    lvl_n2 = get_level("test_01", night_index=2)

    bot1 = create_bot(bot_name)
    cfg1 = SimConfig(night_index=1, end_when_clear=True)
    w1 = SimWorld(lvl_n1, seed, cfg1)
    res1 = w1.run_to_end(bot1)
    m1 = extract_night_metrics(w1, res1)

    ci2 = make_carry_in_from_night1(res1, daytime_exposure_decay=0.0)
    bot2 = create_bot(bot_name)
    cfg2 = SimConfig(night_index=2, carry_in=ci2, end_when_clear=True)
    seed_n2 = SimRandom.night_seed(seed, "test_01", 2) & 0x7FFFFFFFFFFFFFFF
    w2 = SimWorld(lvl_n2, seed_n2, cfg2)
    res2 = w2.run_to_end(bot2)
    m2 = extract_night_metrics(w2, res2)

    both_survived = 1.0 if (m1["survived"] > 0.5 and m2["survived"] > 0.5) else 0.0
    total_shot_cost = m1["shot_cost_musd"] + m2["shot_cost_musd"]
    total_pot_loss = m1["potential_loss_musd"] + m2["potential_loss_musd"]
    combined_ex_ratio = (total_pot_loss / total_shot_cost) if total_shot_cost > 0 else 0.0
    total_non_decoy_spawned = m1["non_decoy_spawned"] + m2["non_decoy_spawned"]
    total_non_decoy_killed = m1["non_decoy_killed"] + m2["non_decoy_killed"]
    combined_intercept_rate = (
        total_non_decoy_killed / total_non_decoy_spawned if total_non_decoy_spawned > 0 else 1.0
    )
    total_units_lost = m1["units_lost_count"] + m2["units_lost_count"]
    total_trust_delta = m1["trust"]["applied"] + m2["trust"]["applied"] + (5.0 if both_survived > 0.5 else -8.0)

    comb_score, comb_rating = compute_composite_score_and_rating(
        survived=(both_survived > 0.5),
        weighted_loss_frac=m2["weighted_loss_frac"],
        non_decoy_intercept_rate=combined_intercept_rate,
        trust_delta=(m1["trust"]["applied"] + m2["trust"]["applied"]) / 2.0,
        units_lost=total_units_lost,
    )

    return {
        "bot": bot_name,
        "seed": seed,
        "n1": m1,
        "n2": m2,
        "combined": {
            "both_survived": both_survived,
            "final_weighted_loss_frac": m2["weighted_loss_frac"],
            "non_decoy_intercept_rate": round(combined_intercept_rate, 4),
            "total_shot_cost_musd": round(total_shot_cost, 4),
            "total_potential_loss_musd": round(total_pot_loss, 4),
            "total_enemy_destroyed_value_musd": round(
                m1["enemy_destroyed_value_musd"] + m2["enemy_destroyed_value_musd"], 4
            ),
            "combined_exchange_ratio": round(combined_ex_ratio, 4),
            "total_units_lost": total_units_lost,
            "total_exp_100_events": m1["exp_100_count"] + m2["exp_100_count"],
            "n1_known_targets_out": m1["known_targets_out_count"],
            "total_trust_delta_with_level": round(total_trust_delta, 2),
            "night_trust_delta_sum": round(m1["trust"]["applied"] + m2["trust"]["applied"], 2),
            "composite_score": comb_score,
            "rating": comb_rating,
        },
    }


def aggregate_bot_runs(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    def agg_phase(phase_key: str) -> Dict[str, Any]:
        items = [r[phase_key] for r in runs]
        ratings: Dict[str, int] = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        end_details: Dict[str, int] = {}
        for it in items:
            rt = it.get("rating", "F")
            ratings[rt] = ratings.get(rt, 0) + 1
            ed = it.get("end_detail") or it.get("end_reason") or "survived"
            if it.get("survived", it.get("both_survived", 0.0)) < 0.5:
                end_details[str(ed)] = end_details.get(str(ed), 0) + 1

        if phase_key in ("n1", "n2"):
            all_threats = set()
            for it in items:
                all_threats.update(it["per_threat_intercept_rate"].keys())
            threat_summary = {}
            for th in sorted(all_threats):
                vals = [
                    it["per_threat_intercept_rate"].get(th, 0.0)
                    for it in items
                    if th in it["per_threat_intercept_rate"]
                ]
                threat_summary[th] = summarize_metric(vals)

            all_weapons = set()
            for it in items:
                all_weapons.update(it["shots_by_weapon"].keys())
            weapon_shots_summary = {
                w: summarize_metric([float(it["shots_by_weapon"].get(w, 0)) for it in items])
                for w in sorted(all_weapons)
            }

            return {
                "survived_rate": round(sum(it["survived"] for it in items) / len(items), 4),
                "defeat_reasons": end_details,
                "weighted_loss_frac": summarize_metric([it["weighted_loss_frac"] for it in items]),
                "non_decoy_intercept_rate": summarize_metric([it["non_decoy_intercept_rate"] for it in items]),
                "decoy_let_through_rate": summarize_metric([it["decoy_let_through_rate"] for it in items]),
                "per_threat_intercept_rate": threat_summary,
                "threats_impacted": summarize_metric([float(it["threats_impacted"]) for it in items]),
                "threats_ew_downed": summarize_metric([float(it["threats_ew_downed"]) for it in items]),
                "threats_arm_missed": summarize_metric([float(it["threats_arm_missed"]) for it in items]),
                "high_threat_leaks_with_reserve": summarize_metric(
                    [float(it["high_threat_leaks_with_reserve"]) for it in items]
                ),
                "expensive_rounds_left": summarize_metric([float(it["expensive_rounds_left"]) for it in items]),
                "units_lost_count": summarize_metric([float(it["units_lost_count"]) for it in items]),
                "light_damaged_count": summarize_metric([float(it["light_damaged_count"]) for it in items]),
                "crippled_count": summarize_metric([float(it["crippled_count"]) for it in items]),
                "exp_100_count": summarize_metric([float(it["exp_100_count"]) for it in items]),
                "max_exposure": summarize_metric([it["max_exposure"] for it in items]),
                "mean_exposure": summarize_metric([it["mean_exposure"] for it in items]),
                "known_targets_out_count": summarize_metric([float(it["known_targets_out_count"]) for it in items]),
                "shot_cost_musd": summarize_metric([it["shot_cost_musd"] for it in items]),
                "potential_loss_musd": summarize_metric([it["potential_loss_musd"] for it in items]),
                "enemy_destroyed_value_musd": summarize_metric([it["enemy_destroyed_value_musd"] for it in items]),
                "exchange_ratio": summarize_metric([it["exchange_ratio"] for it in items]),
                "shots_by_weapon": weapon_shots_summary,
                "urban_intercept_count": summarize_metric([float(it["urban_intercept_count"]) for it in items]),
                "urban_intercept_ratio": summarize_metric([it["urban_intercept_ratio"] for it in items]),
                "urban_L_ge_1_hits": summarize_metric([float(it["urban_L_ge_1_hits"]) for it in items]),
                "urban_same_cell_struct_hits": summarize_metric(
                    [float(it["urban_same_cell_struct_hits"]) for it in items]
                ),
                "cp_spent": summarize_metric([float(it["cp_spent"]) for it in items]),
                "relocations_completed": summarize_metric([float(it["relocations_completed"]) for it in items]),
                "trust_applied": summarize_metric([it["trust"]["applied"] for it in items]),
                "trust_dHoard": summarize_metric([it["trust"]["dHoard"] for it in items]),
                "trust_dEx": summarize_metric([it["trust"]["dEx"] for it in items]),
                "composite_score": summarize_metric([it["composite_score"] for it in items]),
                "ratings": ratings,
            }
        else:
            return {
                "both_survived_rate": round(sum(it["both_survived"] for it in items) / len(items), 4),
                "final_weighted_loss_frac": summarize_metric([it["final_weighted_loss_frac"] for it in items]),
                "non_decoy_intercept_rate": summarize_metric([it["non_decoy_intercept_rate"] for it in items]),
                "total_shot_cost_musd": summarize_metric([it["total_shot_cost_musd"] for it in items]),
                "total_potential_loss_musd": summarize_metric([it["total_potential_loss_musd"] for it in items]),
                "total_enemy_destroyed_value_musd": summarize_metric(
                    [it["total_enemy_destroyed_value_musd"] for it in items]
                ),
                "combined_exchange_ratio": summarize_metric([it["combined_exchange_ratio"] for it in items]),
                "total_units_lost": summarize_metric([float(it["total_units_lost"]) for it in items]),
                "total_exp_100_events": summarize_metric([float(it["total_exp_100_events"]) for it in items]),
                "n1_known_targets_out": summarize_metric([float(it["n1_known_targets_out"]) for it in items]),
                "night_trust_delta_sum": summarize_metric([it["night_trust_delta_sum"] for it in items]),
                "total_trust_delta_with_level": summarize_metric([it["total_trust_delta_with_level"] for it in items]),
                "composite_score": summarize_metric([it["composite_score"] for it in items]),
                "ratings": ratings,
            }

    return {
        "n_seeds": len(runs),
        "night1": agg_phase("n1"),
        "night2": agg_phase("n2"),
        "combined": agg_phase("combined"),
    }


# ---------------------------------------------------------------------------
# Experiment 2: 4 Deployment Topologies (Series 2A & Series 2B)
# ---------------------------------------------------------------------------
def build_validated_plan(lvl: LevelData, raw_units: List[PlacedUnit]) -> DeploymentPlan:
    from tools.papersim.world import DeploymentValidator

    pos_rules = lvl.catalog.rules.get("positions", {})
    min_spacing_m = float(pos_rules.get("minSpacingM", 100.0))
    existing: List[Vec2] = []
    out: List[PlacedUnit] = []
    for idx, pu in enumerate(raw_units):
        ok, _, _ = DeploymentValidator.is_valid_pos(pu.pos, lvl, existing, min_spacing_m)
        cand = pu.pos if ok else DefaultDeploymentBuilder._find_pos(pu.pos, idx, lvl, existing, min_spacing_m)
        existing.append(cand)
        out.append(
            PlacedUnit(
                unit_def_id=pu.unit_def_id,
                pos=cand,
                alternate_position_id=pu.alternate_position_id,
                settings=dict(pu.settings or {}),
                first_night_at_new_position=pu.first_night_at_new_position,
                roster_id=pu.roster_id if pu.roster_id > 0 else (idx + 1),
            )
        )
    return DeploymentPlan(units=out)


def build_series_2a_deployment(topo_name: str, carry_in: Optional[CarryIn] = None) -> DeploymentPlan:
    """Series 2A: Standard test_01 quota (16 units: 4 MFT, 1 IRIS-T SLS, 1 NASAMS, 1 Radar, 6 Acoustic, 3 Observer)."""
    lvl = get_level("test_01", 1)
    if topo_name == "D_default_spiral":
        return DefaultDeploymentBuilder.build(lvl, carry_in)

    if topo_name == "D_layered":
        coords = [
            (1, "mobile_fire_team", Vec2(16200.0, 12200.0), None),
            (2, "mobile_fire_team", Vec2(16500.0, 11000.0), None),
            (3, "mobile_fire_team", Vec2(16200.0, 9600.0), None),
            (4, "mobile_fire_team", Vec2(15000.0, 8800.0), None),
            (5, "iris_t_sls", Vec2(12800.0, 10200.0), None),
            (6, "nasams", Vec2(10800.0, 9600.0), None),
            (7, "soviet_mid_range_radar", Vec2(11500.0, 10600.0), None),
            (8, "acoustic_post", Vec2(18200.0, 12200.0), None),
            (9, "acoustic_post", Vec2(18400.0, 11200.0), None),
            (10, "acoustic_post", Vec2(18400.0, 10200.0), None),
            (11, "acoustic_post", Vec2(18000.0, 8600.0), None),
            (12, "acoustic_post", Vec2(12500.0, 13600.0), None),
            (13, "acoustic_post", Vec2(15500.0, 7800.0), None),
            (14, "visual_observer", Vec2(17200.0, 12000.0), None),
            (15, "visual_observer", Vec2(17200.0, 10600.0), None),
            (16, "visual_observer", Vec2(17000.0, 9000.0), None),
        ]
    elif topo_name == "D_all_stacked":
        # Stacked cluster right next to city core at (11000, 9800) with minSpacingM=100m satisfied
        base_units = [
            (1, "mobile_fire_team"),
            (2, "mobile_fire_team"),
            (3, "mobile_fire_team"),
            (4, "mobile_fire_team"),
            (5, "iris_t_sls"),
            (6, "nasams"),
            (7, "soviet_mid_range_radar"),
            (8, "acoustic_post"),
            (9, "acoustic_post"),
            (10, "acoustic_post"),
            (11, "acoustic_post"),
            (12, "acoustic_post"),
            (13, "acoustic_post"),
            (14, "visual_observer"),
            (15, "visual_observer"),
            (16, "visual_observer"),
        ]
        coords = []
        for idx, (rid, udef) in enumerate(base_units):
            ring = idx // 6
            slot = idx % 6
            r = 140.0 + ring * 130.0
            angle = slot * (2.0 * math.pi / 6.0) + ring * 0.3
            coords.append(
                (
                    rid,
                    udef,
                    Vec2(round(11000.0 + r * math.cos(angle), 1), round(9800.0 + r * math.sin(angle), 1)),
                    None,
                )
            )
    elif topo_name == "D_radar_forward_exposed":
        coords = [
            (1, "mobile_fire_team", Vec2(16200.0, 12200.0), None),
            (2, "mobile_fire_team", Vec2(16500.0, 11000.0), None),
            (3, "mobile_fire_team", Vec2(16200.0, 9600.0), None),
            (4, "mobile_fire_team", Vec2(15000.0, 8800.0), None),
            (5, "iris_t_sls", Vec2(17500.0, 11500.0), None),
            (6, "nasams", Vec2(10800.0, 9600.0), None),
            (7, "soviet_mid_range_radar", Vec2(17800.0, 11800.0), None),
            (8, "acoustic_post", Vec2(18200.0, 12200.0), None),
            (9, "acoustic_post", Vec2(18400.0, 11200.0), None),
            (10, "acoustic_post", Vec2(18400.0, 10200.0), None),
            (11, "acoustic_post", Vec2(18000.0, 8600.0), None),
            (12, "acoustic_post", Vec2(12500.0, 13600.0), None),
            (13, "acoustic_post", Vec2(15500.0, 7800.0), None),
            (14, "visual_observer", Vec2(17200.0, 12000.0), None),
            (15, "visual_observer", Vec2(17200.0, 10600.0), None),
            (16, "visual_observer", Vec2(17000.0, 9000.0), None),
        ]
    else:
        raise ValueError(f"Unknown Series 2A topology: {topo_name}")

    alive_map: Dict[int, Dict[str, Any]] = {}
    if carry_in and carry_in.units:
        for u in carry_in.units:
            alive_map[int(u["rosterId"])] = u

    placed: List[PlacedUnit] = []
    for rid, udef, pos, alt_id in coords:
        if alive_map and rid not in alive_map:
            continue
        use_pos = pos
        if rid in alive_map and "pos" in alive_map[rid]:
            rp = alive_map[rid]["pos"]
            use_pos = rp if isinstance(rp, Vec2) else Vec2(float(rp[0]), float(rp[1]))
        placed.append(
            PlacedUnit(
                unit_def_id=udef,
                pos=use_pos,
                alternate_position_id=alt_id,
                settings={},
                roster_id=rid,
            )
        )
    return build_validated_plan(lvl, placed)


def make_combined_arms_level(night_index: int = 1) -> LevelData:
    """Creates a combined-arms variant of test_01 adding Gepard, EW (area_nav_jammer), Decoy (fake_launcher + decoy_emitter), and 2 Kh-31P ARM threats."""
    base_lvl = get_level("test_01", night_index=night_index)
    lvl = copy.deepcopy(base_lvl)
    lvl.heightmap = base_lvl.heightmap
    lvl.meta = copy.deepcopy(base_lvl.meta)
    avail = list(lvl.meta.get("availableUnits", []))
    avail.extend(
        [
            {"unit": "gepard", "count": 1, "source": "national"},
            {"unit": "area_nav_jammer", "count": 1, "source": "national"},
            {"unit": "fake_launcher", "count": 1, "source": "national"},
            {"unit": "decoy_emitter", "count": 1, "source": "national"},
        ]
    )
    lvl.meta["availableUnits"] = avail
    quota = list(lvl.meta.get("ammoQuota", []))
    quota.append({"weapon": "gepard_35mm", "initial": 640})
    lvl.meta["ammoQuota"] = quota

    lvl.waves = copy.deepcopy(base_lvl.waves)
    for n_obj in lvl.waves.get("nights", []):
        if int(n_obj.get("night", 0)) == night_index:
            n_obj["waves"].append(
                {
                    "id": f"w_arm_sead_n{night_index}",
                    "atSec": 2100.0 if night_index == 1 else 1500.0,
                    "aiTags": ["suppress"],
                    "groups": [
                        {
                            "enemy": "kh31p",
                            "count": 2,
                            "entry": "entry_east",
                            "spacingSec": 30.0,
                            "route": {"direct": True},
                            "target": {"mode": "anti_radiation"},
                        }
                    ],
                }
            )
    return lvl


def build_series_2b_deployment(topo_name: str, carry_in: Optional[CarryIn] = None) -> DeploymentPlan:
    """Series 2B: Combined-Arms 4 Topologies (D_default, D_all_stacked, D_no_decoy_no_ew, D_radar_forward_exposed)."""
    lvl = get_level("test_01", 1)
    if topo_name in ("D_default", "D_no_decoy_no_ew", "D_radar_forward_exposed"):
        radar_pos = Vec2(11500.0, 10600.0) if topo_name != "D_radar_forward_exposed" else Vec2(17800.0, 11800.0)
        iris_pos = Vec2(12800.0, 10200.0) if topo_name != "D_radar_forward_exposed" else Vec2(17500.0, 11500.0)
        coords = [
            (1, "mobile_fire_team", Vec2(16200.0, 12200.0)),
            (2, "mobile_fire_team", Vec2(16500.0, 11000.0)),
            (3, "mobile_fire_team", Vec2(16200.0, 9600.0)),
            (4, "mobile_fire_team", Vec2(15000.0, 8800.0)),
            (5, "iris_t_sls", iris_pos),
            (6, "nasams", Vec2(10800.0, 9600.0)),
            (7, "soviet_mid_range_radar", radar_pos),
            (8, "acoustic_post", Vec2(18200.0, 12200.0)),
            (9, "acoustic_post", Vec2(18400.0, 11200.0)),
            (10, "acoustic_post", Vec2(18400.0, 10200.0)),
            (11, "acoustic_post", Vec2(18000.0, 8600.0)),
            (12, "acoustic_post", Vec2(12500.0, 13600.0)),
            (13, "acoustic_post", Vec2(15500.0, 7800.0)),
            (14, "visual_observer", Vec2(17200.0, 12000.0)),
            (15, "visual_observer", Vec2(17200.0, 10600.0)),
            (16, "visual_observer", Vec2(17000.0, 9000.0)),
            (17, "gepard", Vec2(14200.0, 10800.0)),
        ]
        if topo_name != "D_no_decoy_no_ew":
            coords.extend(
                [
                    (18, "area_nav_jammer", Vec2(11200.0, 9900.0)),
                    (19, "fake_launcher", Vec2(11800.0, 10900.0)),
                    (20, "decoy_emitter", Vec2(12000.0, 11000.0)),
                ]
            )
    elif topo_name == "D_all_stacked":
        base_units = [
            (1, "mobile_fire_team"),
            (2, "mobile_fire_team"),
            (3, "mobile_fire_team"),
            (4, "mobile_fire_team"),
            (5, "iris_t_sls"),
            (6, "nasams"),
            (7, "soviet_mid_range_radar"),
            (8, "acoustic_post"),
            (9, "acoustic_post"),
            (10, "acoustic_post"),
            (11, "acoustic_post"),
            (12, "acoustic_post"),
            (13, "acoustic_post"),
            (14, "visual_observer"),
            (15, "visual_observer"),
            (16, "visual_observer"),
            (17, "gepard"),
            (18, "area_nav_jammer"),
            (19, "fake_launcher"),
            (20, "decoy_emitter"),
        ]
        coords = []
        for idx, (rid, udef) in enumerate(base_units):
            ring = idx // 6
            slot = idx % 6
            r = 140.0 + ring * 130.0
            angle = slot * (2.0 * math.pi / 6.0) + ring * 0.3
            coords.append(
                (rid, udef, Vec2(round(11000.0 + r * math.cos(angle), 1), round(9800.0 + r * math.sin(angle), 1)))
            )
    else:
        raise ValueError(f"Unknown Series 2B topology: {topo_name}")

    alive_map: Dict[int, Dict[str, Any]] = {}
    if carry_in and carry_in.units:
        for u in carry_in.units:
            alive_map[int(u["rosterId"])] = u

    placed: List[PlacedUnit] = []
    for rid, udef, pos in coords:
        if alive_map and rid not in alive_map:
            continue
        use_pos = pos
        if rid in alive_map and "pos" in alive_map[rid]:
            rp = alive_map[rid]["pos"]
            use_pos = rp if isinstance(rp, Vec2) else Vec2(float(rp[0]), float(rp[1]))
        placed.append(
            PlacedUnit(
                unit_def_id=udef,
                pos=use_pos,
                settings={},
                roster_id=rid,
            )
        )
    return build_validated_plan(lvl, placed)


def _run_exp2_single(args: Tuple[str, str, str, int]) -> Dict[str, Any]:
    series, topo_name, bot_name, seed = args
    if series == "2A":
        lvl_n1 = get_level("test_01", 1)
        lvl_n2 = get_level("test_01", 2)
        plan1 = build_series_2a_deployment(topo_name, None)
    else:
        lvl_n1 = make_combined_arms_level(1)
        lvl_n2 = make_combined_arms_level(2)
        plan1 = build_series_2b_deployment(topo_name, None)

    bot1 = create_bot(bot_name)
    cfg1 = SimConfig(night_index=1, deployment=plan1, end_when_clear=True)
    w1 = SimWorld(lvl_n1, seed, cfg1)
    res1 = w1.run_to_end(bot1)
    m1 = extract_night_metrics(w1, res1)

    ci2 = make_carry_in_from_night1(res1, 0.0)
    plan2 = (
        build_series_2a_deployment(topo_name, ci2)
        if series == "2A"
        else build_series_2b_deployment(topo_name, ci2)
    )
    bot2 = create_bot(bot_name)
    cfg2 = SimConfig(night_index=2, deployment=plan2, carry_in=ci2, end_when_clear=True)
    seed_n2 = SimRandom.night_seed(seed, "test_01", 2) & 0x7FFFFFFFFFFFFFFF
    w2 = SimWorld(lvl_n2, seed_n2, cfg2)
    res2 = w2.run_to_end(bot2)
    m2 = extract_night_metrics(w2, res2)

    both_survived = 1.0 if (m1["survived"] > 0.5 and m2["survived"] > 0.5) else 0.0
    tot_sc = m1["shot_cost_musd"] + m2["shot_cost_musd"]
    tot_pl = m1["potential_loss_musd"] + m2["potential_loss_musd"]
    tot_nd_sp = m1["non_decoy_spawned"] + m2["non_decoy_spawned"]
    tot_nd_kl = m1["non_decoy_killed"] + m2["non_decoy_killed"]
    comb_ir = tot_nd_kl / tot_nd_sp if tot_nd_sp > 0 else 1.0
    tot_ul = m1["units_lost_count"] + m2["units_lost_count"]
    comb_score, comb_rating = compute_composite_score_and_rating(
        survived=(both_survived > 0.5),
        weighted_loss_frac=m2["weighted_loss_frac"],
        non_decoy_intercept_rate=comb_ir,
        trust_delta=(m1["trust"]["applied"] + m2["trust"]["applied"]) / 2.0,
        units_lost=tot_ul,
    )

    return {
        "series": series,
        "topology": topo_name,
        "bot": bot_name,
        "seed": seed,
        "n1": m1,
        "n2": m2,
        "combined": {
            "both_survived": both_survived,
            "final_weighted_loss_frac": m2["weighted_loss_frac"],
            "non_decoy_intercept_rate": round(comb_ir, 4),
            "total_shot_cost_musd": round(tot_sc, 4),
            "total_potential_loss_musd": round(tot_pl, 4),
            "total_enemy_destroyed_value_musd": round(
                m1["enemy_destroyed_value_musd"] + m2["enemy_destroyed_value_musd"], 4
            ),
            "combined_exchange_ratio": round((tot_pl / tot_sc) if tot_sc > 0 else 0.0, 4),
            "total_units_lost": tot_ul,
            "total_exp_100_events": m1["exp_100_count"] + m2["exp_100_count"],
            "n1_known_targets_out": m1["known_targets_out_count"],
            "night_trust_delta_sum": round(m1["trust"]["applied"] + m2["trust"]["applied"], 2),
            "total_trust_delta_with_level": round(
                m1["trust"]["applied"] + m2["trust"]["applied"] + (5.0 if both_survived > 0.5 else -8.0), 2
            ),
            "composite_score": comb_score,
            "rating": comb_rating,
        },
    }


# ---------------------------------------------------------------------------
# Experiment 3 Workers: Targeted Verification of H-01..H-15 and B-T3-01..10
# ---------------------------------------------------------------------------
def _run_h01_position(args: Tuple[int, float, float, str]) -> Dict[str, Any]:
    """H-01: NASAMS & SAM position sensitivity across 30 distinct coordinates on test_01."""
    idx, nx, ny, mode = args
    lvl = get_level("test_01", 1)
    base_plan = DefaultDeploymentBuilder.build(lvl, None)
    existing: List[Vec2] = []
    units: List[PlacedUnit] = []
    for u in base_plan.units:
        if u.unit_def_id == "nasams":
            cand = DefaultDeploymentBuilder._find_pos(Vec2(nx, ny), u.roster_id, lvl, existing, 100.0)
            existing.append(cand)
            units.append(PlacedUnit(unit_def_id=u.unit_def_id, pos=cand, settings=dict(u.settings), roster_id=u.roster_id))
        elif mode == "shift_all_sams" and u.unit_def_id in ("iris_t_sls", "mobile_fire_team"):
            dx = nx - 10633.0
            dy = ny - 9900.0
            px = max(1000.0, min(19000.0, u.pos.x + dx))
            py = max(1000.0, min(19000.0, u.pos.y + dy))
            cand = DefaultDeploymentBuilder._find_pos(Vec2(px, py), u.roster_id, lvl, existing, 100.0)
            existing.append(cand)
            units.append(PlacedUnit(unit_def_id=u.unit_def_id, pos=cand, settings=dict(u.settings), roster_id=u.roster_id))
        else:
            cand = DefaultDeploymentBuilder._find_pos(u.pos, u.roster_id, lvl, existing, 100.0)
            existing.append(cand)
            units.append(PlacedUnit(unit_def_id=u.unit_def_id, pos=cand, settings=dict(u.settings), roster_id=u.roster_id))

    plan = DeploymentPlan(units=units)
    surv_list = []
    wloss_list = []
    ir_list = []
    kh101_ir_list = []
    exp100_list = []
    for s in range(1, 3):
        w = SimWorld(lvl, s, SimConfig(night_index=1, deployment=copy.deepcopy(plan), end_when_clear=True))
        res = w.run_to_end(PassiveBot())
        m = extract_night_metrics(w, res)
        surv_list.append(m["survived"])
        wloss_list.append(m["weighted_loss_frac"])
        ir_list.append(m["non_decoy_intercept_rate"])
        kh101_ir_list.append(m["per_threat_intercept_rate"].get("kh101", 0.0))
        exp100_list.append(float(m["exp_100_count"]))
    return {
        "pos_idx": idx,
        "mode": mode,
        "x": nx,
        "y": ny,
        "survived_rate": round(sum(surv_list) / len(surv_list), 4),
        "weighted_loss_frac": round(sum(wloss_list) / len(wloss_list), 4),
        "non_decoy_intercept_rate": round(sum(ir_list) / len(ir_list), 4),
        "kh101_intercept_rate": round(sum(kh101_ir_list) / len(kh101_ir_list), 4),
        "exp_100_count": round(sum(exp100_list) / len(exp100_list), 4),
    }


def _run_h02_sensors(args: Tuple[str, int]) -> Dict[str, Any]:
    """H-02: Sensor network dependency (full vs radar_only vs local_only vs zero_external)."""
    cfg_name, seed = args
    lvl = get_level("test_01", 1)
    base_plan = build_series_2a_deployment("D_layered", None)
    units: List[PlacedUnit] = []
    for u in base_plan.units:
        if cfg_name == "radar_only" and u.unit_def_id in ("acoustic_post", "visual_observer"):
            continue
        if cfg_name == "local_only_no_radar" and u.unit_def_id == "soviet_mid_range_radar":
            continue
        if cfg_name == "zero_external_sensors" and u.unit_def_id in (
            "soviet_mid_range_radar",
            "acoustic_post",
            "visual_observer",
        ):
            continue
        units.append(u)
    plan = DeploymentPlan(units=units)
    w = SimWorld(lvl, seed, SimConfig(night_index=1, deployment=plan, end_when_clear=True))
    res = w.run_to_end(PassiveBot())
    m = extract_night_metrics(w, res)
    return {"config": cfg_name, "seed": seed, "metrics": m}


def _run_h04_ammo_rules(args: Tuple[str, int]) -> Dict[str, Any]:
    """H-04 & B-T3-02: Ammo reservation & engagement rules on test_01."""
    policy_name, seed = args
    lvl = get_level("test_01", 1)

    class PolicyBot(TacticalBot):
        name = policy_name

        def __init__(self) -> None:
            super().__init__()
            self.configured = False
            self.unlocked = False

        def decide(self, world: SimWorld) -> List[SimCommand]:
            if not self.configured:
                self.configured = True
                for fu in world.state.fire_units.alive_list():
                    for wslot in fu.weapons:
                        if policy_name == "wasteful_any":
                            wslot.rule = 0
                            wslot.ammo_reserve = 0
                        elif policy_name == "reserve_4_unlock_cm":
                            if wslot.weapon_id in ("nasams", "nasams_missile"):
                                wslot.ammo_reserve = 4
                            elif wslot.weapon_id in ("iris_t_sls", "iris_t_sls_missile"):
                                wslot.ammo_reserve = 2
                        elif policy_name == "reserve_6_strict":
                            if wslot.weapon_id in ("nasams", "nasams_missile"):
                                wslot.ammo_reserve = 6
                            elif wslot.weapon_id in ("iris_t_sls", "iris_t_sls_missile"):
                                wslot.ammo_reserve = 3
                        elif policy_name == "hoarder_ballistic_only":
                            if wslot.weapon_id in ("nasams", "nasams_missile", "iris_t_sls", "iris_t_sls_missile"):
                                wslot.rule = 1  # BallisticOnly
                        elif policy_name == "whitelist_cm_only":
                            if wslot.weapon_id in ("nasams", "nasams_missile"):
                                wslot.rule = 0
                                setattr(wslot, "whitelist", {TargetTag.CM})
                        elif policy_name == "layered_forward_mft_plus_cm_nasams":
                            if wslot.weapon_id in ("nasams", "nasams_missile"):
                                wslot.rule = 0
                                setattr(wslot, "whitelist", {TargetTag.CM})

            if policy_name in ("reserve_4_unlock_cm", "layered_forward_mft_plus_cm_nasams") and not self.unlocked:
                if world.state.tick >= 14000:
                    self.unlocked = True
                    for fu in world.state.fire_units.alive_list():
                        for wslot in fu.weapons:
                            wslot.ammo_reserve = 0
                            wslot.rule = 0
                            setattr(wslot, "whitelist", None)
            return []

    plan = (
        build_series_2a_deployment("D_layered", None)
        if policy_name == "layered_forward_mft_plus_cm_nasams"
        else DefaultDeploymentBuilder.build(lvl, None)
    )
    w = SimWorld(lvl, seed, SimConfig(night_index=1, deployment=plan, end_when_clear=True))
    res = w.run_to_end(PolicyBot())
    m = extract_night_metrics(w, res)
    return {"policy": policy_name, "seed": seed, "metrics": m}


def _run_h05_night_optical(args: Tuple[str, int]) -> Dict[str, Any]:
    """H-05: Night optical penalty, radar cueing, and searchlight on mobile_fire_team."""
    cond_name, seed = args
    base_lvl = get_level("test_01", 1)
    lvl = copy.deepcopy(base_lvl)
    lvl.heightmap = base_lvl.heightmap
    lvl.waves = copy.deepcopy(base_lvl.waves)

    for n_obj in lvl.waves["nights"]:
        if int(n_obj["night"]) == 1:
            n_obj["timeOfDay"] = "day" if cond_name == "day_clear" else "night"
            n_obj["waves"] = [
                {
                    "id": "w_shahed_optical_test",
                    "atSec": 300.0,
                    "groups": [
                        {
                            "enemy": "shahed_136",
                            "count": 16,
                            "entry": "entry_east",
                            "spacingSec": 90.0,
                            "route": {"direct": True},
                            "target": {"structure": "tpp"},
                        }
                    ],
                }
            ]

    aids = ["searchlight"] if "searchlight" in cond_name else []
    settings = {"nightAids": aids} if aids else {}
    # Entry_east is (26000, 14000) -> TPP is (13500, 7000). Line passes through (18500, 9800), (17250, 9100), (16000, 8400), (14750, 7700)
    units = [
        PlacedUnit("mobile_fire_team", Vec2(18500.0, 9800.0), settings=dict(settings), roster_id=1),
        PlacedUnit("mobile_fire_team", Vec2(17250.0, 9100.0), settings=dict(settings), roster_id=2),
        PlacedUnit("mobile_fire_team", Vec2(16000.0, 8400.0), settings=dict(settings), roster_id=3),
        PlacedUnit("mobile_fire_team", Vec2(14750.0, 7700.0), settings=dict(settings), roster_id=4),
    ]
    if "with_radar" in cond_name:
        units.append(PlacedUnit("soviet_mid_range_radar", Vec2(13500.0, 7500.0), roster_id=7))
    if "with_acoustic" in cond_name:
        units.append(PlacedUnit("acoustic_post", Vec2(19500.0, 10360.0), roster_id=8))
        units.append(PlacedUnit("visual_observer", Vec2(19000.0, 10080.0), settings=dict(settings), roster_id=14))

    w = SimWorld(lvl, seed, SimConfig(night_index=1, deployment=build_validated_plan(lvl, units), end_when_clear=True))
    res = w.run_to_end(PassiveBot())
    m = extract_night_metrics(w, res)
    return {"condition": cond_name, "seed": seed, "metrics": m}


def _run_h07_decoy(args: Tuple[str, int]) -> Dict[str, Any]:
    """H-07: Decoy (gerbera) discrimination and ammo waste under 3D radar (Precise), 2D radar (Approximate), and Visual/Acoustic only (Vague)."""
    cond_name, seed = args
    base_lvl = get_level("test_01", 1)
    lvl = copy.deepcopy(base_lvl)
    lvl.heightmap = base_lvl.heightmap
    lvl.waves = copy.deepcopy(base_lvl.waves)

    for n_obj in lvl.waves["nights"]:
        if int(n_obj["night"]) == 1:
            n_obj["waves"] = [
                {
                    "id": "w_decoy_test",
                    "atSec": 300.0,
                    "aiTags": ["probe"],
                    "groups": [
                        {
                            "enemy": "gerbera",
                            "count": 10,
                            "entry": "entry_east",
                            "spacingSec": 60.0,
                            "route": {"direct": True},
                            "target": {"mode": "decoy_flight"},
                        },
                        {
                            "enemy": "shahed_136",
                            "count": 10,
                            "entry": "entry_east",
                            "spacingSec": 60.0,
                            "route": {"direct": True},
                            "target": {"structure": "tpp"},
                        },
                    ],
                }
            ]

    lvl.meta = copy.deepcopy(base_lvl.meta)
    lvl.meta["availableUnits"].append({"unit": "western_3d_radar", "count": 1, "source": "national"})

    units = [
        PlacedUnit("iris_t_sls", Vec2(14200.0, 7400.0), roster_id=5),
        PlacedUnit("nasams", Vec2(13000.0, 6800.0), roster_id=6),
        PlacedUnit("mobile_fire_team", Vec2(17250.0, 9100.0), roster_id=1),
        PlacedUnit("mobile_fire_team", Vec2(16000.0, 8400.0), roster_id=2),
    ]
    if cond_name == "3d_radar_precise":
        units.append(PlacedUnit("western_3d_radar", Vec2(18000.0, 9500.0), roster_id=20))
    elif cond_name == "2d_radar_approximate":
        units.append(PlacedUnit("soviet_mid_range_radar", Vec2(18000.0, 9500.0), roster_id=7))
    elif cond_name == "no_radar_vague_only":
        units.append(PlacedUnit("acoustic_post", Vec2(19500.0, 10360.0), roster_id=8))
        units.append(PlacedUnit("visual_observer", Vec2(18500.0, 9800.0), roster_id=14))

    w = SimWorld(lvl, seed, SimConfig(night_index=1, deployment=build_validated_plan(lvl, units), end_when_clear=True))
    res = w.run_to_end(PassiveBot())
    m = extract_night_metrics(w, res)
    disc_events = sum(1 for ev in w.events._outbox if ev.type == SimEventType.DecoyIdentified)
    return {
        "condition": cond_name,
        "seed": seed,
        "discriminated_count": disc_events,
        "decoy_spawned": m["decoy_spawned"],
        "decoy_killed": m["decoy_killed"],
        "decoy_let_through_rate": m["decoy_let_through_rate"],
        "shahed_intercept_rate": m["per_threat_intercept_rate"].get("shahed_136", 0.0),
        "shot_cost_musd": m["shot_cost_musd"],
        "exchange_ratio": m["exchange_ratio"],
    }


def _run_h10_probe_avoidance(args: Tuple[str, int]) -> Dict[str, Any]:
    """H-10: Enemy probe -> A* path avoidance closed loop."""
    cond_name, seed = args
    base_lvl = get_level("test_01", 1)
    lvl = copy.deepcopy(base_lvl)
    lvl.heightmap = base_lvl.heightmap
    lvl.waves = copy.deepcopy(base_lvl.waves)

    # Make w3_cruise_valley enter from entry_east with direct route so it flies down the East corridor probed by w1_probe
    for n_obj in lvl.waves["nights"]:
        if int(n_obj["night"]) == 1:
            for w_obj in n_obj["waves"]:
                if w_obj["id"] == "w3_cruise_valley":
                    for g in w_obj["groups"]:
                        g["entry"] = "entry_east"
                        g["route"] = {"direct": True}
            if cond_name == "no_probe_wave":
                n_obj["waves"] = [w_obj for w_obj in n_obj["waves"] if w_obj["id"] != "w1_probe"]

    # Place IRIS-T SLS and Radar right on the direct line from entry_east (26000, 14000) to TPP (13500, 7000)
    plan = build_series_2a_deployment("D_layered", None)
    for u in plan.units:
        if u.unit_def_id == "iris_t_sls":
            u.pos = Vec2(17250.0, 9100.0)
        elif u.unit_def_id == "soviet_mid_range_radar":
            u.pos = Vec2(16500.0, 8680.0)
        elif u.unit_def_id == "nasams":
            u.pos = Vec2(14750.0, 7700.0)
    plan = build_validated_plan(lvl, plan.units)

    class SilentDuringProbeBot(TacticalBot):
        name = "silent_during_probe"

        def decide(self, world: SimWorld) -> List[SimCommand]:
            should_emit = world.state.tick >= 4000
            for s in world.state.sensors.alive_list():
                if s.emitter is not None:
                    s.emitter.on = should_emit
            for fu in world.state.fire_units.alive_list():
                if fu.emitter is not None:
                    fu.emitter.on = should_emit
            return []

    use_bot: TacticalBot = SilentDuringProbeBot() if cond_name == "probe_silent_during_w1" else PassiveBot()
    w = SimWorld(lvl, seed, SimConfig(night_index=1, deployment=plan, end_when_clear=True))

    kh101_waypoints: List[List[Tuple[float, float]]] = []
    orig_step = w.step

    def step_and_record() -> Any:
        ev = orig_step()
        if w.state.tick == 14405:  # w3_cruise_valley spawns at 240 gameSec = 14400 worldSec
            for th in w.state.threats.alive_list():
                if th.def_id == "kh101":
                    kh101_waypoints.append([(round(p.x, 1), round(p.y, 1)) for p in th.path])
        return ev

    w.step = step_and_record  # type: ignore[method-assign]
    res = w.run_to_end(use_bot)
    m = extract_night_metrics(w, res)

    max_dev_m = 0.0
    for wp_list in kh101_waypoints:
        if len(wp_list) >= 2:
            x0, y0 = wp_list[0]
            x1, y1 = wp_list[-1]
            dx, dy = x1 - x0, y1 - y0
            seg_len = math.hypot(dx, dy)
            if seg_len > 1.0:
                for px, py in wp_list[1:-1]:
                    dist = abs(dy * px - dx * py + x1 * y0 - y1 * x0) / seg_len
                    if dist > max_dev_m:
                        max_dev_m = dist

    return {
        "condition": cond_name,
        "seed": seed,
        "known_targets_count": m["known_targets_out_count"],
        "kh101_max_lateral_deviation_m": round(max_dev_m, 1),
        "kh101_waypoint_count": max((len(wp) for wp in kh101_waypoints), default=0),
        "kh101_intercept_rate": m["per_threat_intercept_rate"].get("kh101", 0.0),
        "weighted_loss_frac": m["weighted_loss_frac"],
        "survived": m["survived"],
    }


def _run_h03_bt3_05_10_emission(args: Tuple[str, str, int]) -> Dict[str, Any]:
    """H-03, B-T3-05, B-T3-10: Compare 6 emission strategies on test_01 and ARM scenario."""
    scenario, strategy, seed = args
    lvl = get_level("test_01", 1) if scenario == "test_01" else make_combined_arms_level(1)
    plan = (
        build_series_2a_deployment("D_layered", None)
        if scenario == "test_01"
        else build_series_2b_deployment("D_default", None)
    )

    pol_map = {
        "always_on": "continuous",
        "on_warning": "on_warning",
        "intermittent": "blink",
        "silent_standby": "silent_standby",
        "decoy_coordinated": "decoy_coordinated",
        "silent": "silent",
    }
    pol_id = pol_map[strategy]
    for u in plan.units:
        u.settings["emissionPolicyId"] = pol_id
        if strategy == "intermittent":
            u.settings["dutyOnSec"] = 54.0
            u.settings["dutyOffSec"] = 66.0

    w = SimWorld(lvl, seed, SimConfig(night_index=1, deployment=plan, end_when_clear=True))
    res = w.run_to_end(PassiveBot())
    m = extract_night_metrics(w, res)

    lvl2 = get_level("test_01", 2) if scenario == "test_01" else make_combined_arms_level(2)
    ci2 = make_carry_in_from_night1(res, 0.0)
    plan2 = (
        build_series_2a_deployment("D_layered", ci2)
        if scenario == "test_01"
        else build_series_2b_deployment("D_default", ci2)
    )
    for u in plan2.units:
        u.settings["emissionPolicyId"] = pol_id
        if strategy == "intermittent":
            u.settings["dutyOnSec"] = 54.0
            u.settings["dutyOffSec"] = 66.0

    w2 = SimWorld(
        lvl2,
        SimRandom.night_seed(seed, "test_01", 2) & 0x7FFFFFFFFFFFFFFF,
        SimConfig(night_index=2, deployment=plan2, carry_in=ci2, end_when_clear=True),
    )
    res2 = w2.run_to_end(PassiveBot())
    m2 = extract_night_metrics(w2, res2)

    radar_exp_n1 = 0.0
    for eu in res.exposure.get("units", []):
        if eu.get("defId") == "soviet_mid_range_radar":
            radar_exp_n1 = max(radar_exp_n1, float(eu.get("peak", eu.get("exposure", 0.0))))

    return {
        "scenario": scenario,
        "strategy": strategy,
        "seed": seed,
        "n1_survived": m["survived"],
        "n2_survived": m2["survived"],
        "both_survived": 1.0 if (m["survived"] > 0.5 and m2["survived"] > 0.5) else 0.0,
        "n1_intercept_rate": m["non_decoy_intercept_rate"],
        "n1_weighted_loss": m["weighted_loss_frac"],
        "n2_weighted_loss": m2["weighted_loss_frac"],
        "n1_mean_exposure": m["mean_exposure"],
        "n1_max_exposure": m["max_exposure"],
        "n1_radar_exposure": radar_exp_n1,
        "n1_exp_100_count": m["exp_100_count"],
        "n1_known_targets_out": m["known_targets_out_count"],
        "n1_units_lost": m["units_lost_count"],
        "n2_units_lost": m2["units_lost_count"],
        "n1_arm_missed": m["threats_arm_missed"],
    }


def _run_h11_ballistic(args: Tuple[str, str, bool, int]) -> Dict[str, Any]:
    """H-11: Ballistic missile (iskander_m / s300_ground / kinzhal) intercept rate on 20km vs 60km map, with vs without SLS."""
    missile_id, map_scale, has_sls, seed = args
    base_lvl = get_level("test_01", 1)
    lvl = copy.deepcopy(base_lvl)
    lvl.heightmap = base_lvl.heightmap
    lvl.meta = copy.deepcopy(base_lvl.meta)
    lvl.waves = copy.deepcopy(base_lvl.waves)
    lvl.entry_points_by_id = copy.deepcopy(base_lvl.entry_points_by_id)
    lvl.catalog = copy.deepcopy(base_lvl.catalog)

    # TPP is at (13500, 7000); place entry_east 15km East (28500, 7000) for 20km map, or 45km East (58500, 7000) for 60km map
    if "60km" in map_scale:
        lvl.entry_points_by_id["entry_east"]["pos"] = Vec2(58500.0, 7000.0)
    else:
        lvl.entry_points_by_id["entry_east"]["pos"] = Vec2(28500.0, 7000.0)
    lvl.entry_points_by_id["entry_east"]["warningSec"] = 180.0 if has_sls else 0.0

    lvl.meta["availableUnits"] = [
        {"unit": "patriot", "count": 1, "source": "national"},
        {"unit": "soviet_mid_range_radar", "count": 1, "source": "national"},
    ]
    lvl.meta["ammoQuota"] = [
        {"weapon": "pac3_mse", "initial": 24},
        {"weapon": "pac2", "initial": 24},
    ]
    lvl.meta["defeat"] = []

    if "fast_react_2s" in map_scale:
        reac_cls = lvl.catalog.rules["engagement"].setdefault("reactionSecByClass", {})
        reac_cls["pac3"] = 2.0
        reac_cls["pac2"] = 2.0
        lvl.catalog.rules["engagement"]["byWeaponKind"]["missile"]["reactionSec"] = 2.0

    pac3_rule = lvl.catalog.rules["engagement"]["defaultRuleByTag"]["pac3"]
    pac2_rule = lvl.catalog.rules["engagement"]["defaultRuleByTag"]["pac2"]
    if has_sls:
        pac3_rule["BM"] = {"salvoSize": 1, "shootLookShoot": True}
        pac3_rule["HBM"] = {"salvoSize": 1, "shootLookShoot": True}
        pac2_rule["BM"] = {"salvoSize": 1, "shootLookShoot": True}
    else:
        pac3_rule["BM"] = {"salvoSize": 2, "shootLookShoot": False}
        pac3_rule["HBM"] = {"salvoSize": 2, "shootLookShoot": False}
        pac2_rule["BM"] = {"salvoSize": 2, "shootLookShoot": False}

    for n_obj in lvl.waves["nights"]:
        if int(n_obj["night"]) == 1:
            n_obj["waves"] = [
                {
                    "id": "w_ballistic_test",
                    "atSec": 300.0,
                    "groups": [
                        {
                            "enemy": missile_id,
                            "count": 4,
                            "entry": "entry_east",
                            "spacingSec": 60.0,
                            "route": {"direct": True},
                            "target": {"structure": "tpp"},
                        }
                    ],
                }
            ]

    plan = build_validated_plan(
        lvl,
        [
            PlacedUnit("patriot", Vec2(13500.0, 7300.0), roster_id=1),
            PlacedUnit("soviet_mid_range_radar", Vec2(14000.0, 7000.0), roster_id=2),
        ],
    )
    w = SimWorld(lvl, seed, SimConfig(night_index=1, deployment=plan, end_when_clear=True))
    res = w.run_to_end(PassiveBot())

    spawn_t: List[float] = []
    first_fire_t: Optional[float] = None
    for ev in w.events._outbox:
        if ev.type == SimEventType.ThreatSpawned:
            spawn_t.append(float(ev.tick))
        elif ev.type in (SimEventType.InterceptorLaunched, SimEventType.GunFired) and first_fire_t is None:
            first_fire_t = float(ev.tick) - (min(spawn_t) if spawn_t else 300.0)

    m = extract_night_metrics(w, res)
    tot_shots = m["shots_by_weapon"].get("pac3_mse", 0) + m["shots_by_weapon"].get("pac2", 0)
    tot_hits = m["hits_by_weapon"].get("pac3_mse", 0) + m["hits_by_weapon"].get("pac2", 0)
    return {
        "missile": missile_id,
        "map_scale": map_scale,
        "has_sls": has_sls,
        "seed": seed,
        "intercept_rate": m["per_threat_intercept_rate"].get(missile_id, 0.0),
        "shots_fired": tot_shots,
        "hits": tot_hits,
        "shot_cost_musd": m["shot_cost_musd"],
        "exchange_ratio": m["exchange_ratio"],
        "first_shot_reaction_sec": first_fire_t if first_fire_t is not None else -1.0,
    }


def _run_bt3_08_ew(args: Tuple[str, int]) -> Dict[str, Any]:
    """B-T3-08: Compare unit EW (area_nav_jammer, nav_spoofer, counter_uas_jammer) vs National Spoofing."""
    ew_mode, seed = args
    base_lvl = get_level("test_01", 1)
    lvl = copy.deepcopy(base_lvl)
    lvl.heightmap = base_lvl.heightmap
    lvl.meta = copy.deepcopy(base_lvl.meta)
    lvl.waves = copy.deepcopy(base_lvl.waves)

    lvl.meta["availableUnits"] = [
        {"unit": "soviet_mid_range_radar", "count": 1, "source": "national"},
        {"unit": "area_nav_jammer", "count": 1, "source": "national"},
        {"unit": "nav_spoofer", "count": 1, "source": "national"},
        {"unit": "counter_uas_jammer", "count": 1, "source": "national"},
    ]

    for n_obj in lvl.waves["nights"]:
        if int(n_obj["night"]) == 1:
            n_obj["waves"] = [
                {
                    "id": "w_ew_test",
                    "atSec": 200.0,
                    "groups": [
                        {
                            "enemy": "shahed_136",
                            "count": 12,
                            "entry": "entry_east",
                            "spacingSec": 30.0,
                            "route": {"direct": True},
                            "target": {"structure": "tpp"},
                        },
                        {
                            "enemy": "kh101",
                            "count": 6,
                            "entry": "entry_east",
                            "spacingSec": 30.0,
                            "route": {"direct": True},
                            "target": {"structure": "tpp"},
                        },
                        {
                            "enemy": "lancet",
                            "count": 6,
                            "entry": "entry_east",
                            "spacingSec": 30.0,
                            "route": {"direct": True},
                            "target": {"structure": "tpp"},
                        },
                    ],
                }
            ]
    lvl.meta["defeat"] = []

    units = [PlacedUnit("soviet_mid_range_radar", Vec2(13200.0, 7000.0), roster_id=1)]
    if ew_mode == "area_nav_jammer":
        units.append(PlacedUnit("area_nav_jammer", Vec2(13800.0, 7200.0), roster_id=2))
    elif ew_mode == "nav_spoofer":
        units.append(
            PlacedUnit(
                "nav_spoofer",
                Vec2(13800.0, 7200.0),
                settings={"lurePoint": [16500.0, 4000.0]},
                roster_id=3,
            )
        )
    elif ew_mode == "counter_uas_jammer":
        units.append(PlacedUnit("counter_uas_jammer", Vec2(14750.0, 7700.0), roster_id=4))
    elif ew_mode == "both_national_and_unit_jammer":
        units.append(PlacedUnit("area_nav_jammer", Vec2(13800.0, 7200.0), roster_id=2))

    lvl.structures = copy.deepcopy(base_lvl.structures)
    for st_def in lvl.structures:
        if st_def["id"] == "tpp":
            st_def["hp"] = 100
            st_def["maxHp"] = 100

    class NationalSpoofBot(TacticalBot):
        name = "nat_spoof"

        def __init__(self) -> None:
            super().__init__()
            self.called = False

        def decide(self, world: SimWorld) -> List[SimCommand]:
            if not self.called and world.state.tick >= 180:
                self.called = True
                sa = SupportAsset(
                    def_id="national_gnss_spoof",
                    support_kind=1,
                    state=1,
                    pos=Vec2(13500.0, 7000.0),
                    radius_m=30000.0,
                    arrive_sec=180.0,
                    end_sec=99999.0,
                )
                world.state.support_assets.add(sa)
            return []

    bot: TacticalBot = (
        NationalSpoofBot()
        if ew_mode in ("national_spoofing_only", "both_national_and_unit_jammer")
        else PassiveBot()
    )
    w = SimWorld(lvl, seed, SimConfig(night_index=1, deployment=build_validated_plan(lvl, units), end_when_clear=True))
    res = w.run_to_end(bot)
    m = extract_night_metrics(w, res)
    tpp_st = next((s for s in m["structures_end"] if s["id"] == "tpp"), None)
    tpp_loss_hp = float(tpp_st["maxHp"] - tpp_st["hp"]) if tpp_st else 0.0
    return {
        "ew_mode": ew_mode,
        "seed": seed,
        "threats_impacted": m["threats_impacted"],
        "threats_ew_downed": m["threats_ew_downed"],
        "tpp_loss_hp": tpp_loss_hp,
        "weighted_loss_frac": m["weighted_loss_frac"],
    }


def _run_bt3_09_platform(args: Tuple[str, str, float, int]) -> Dict[str, Any]:
    """B-T3-09: Platform (su24m / su34 / tu22m3) pre-release shootdown vs releaseRangeKm and SAM range."""
    platform_id, sam_unit, release_range_km, seed = args
    base_lvl = get_level("test_01", 2)
    lvl = copy.deepcopy(base_lvl)
    lvl.heightmap = base_lvl.heightmap
    lvl.meta = copy.deepcopy(base_lvl.meta)
    lvl.waves = copy.deepcopy(base_lvl.waves)
    lvl.catalog = copy.deepcopy(base_lvl.catalog)
    lvl.structures = copy.deepcopy(base_lvl.structures)

    lvl.catalog.platforms[platform_id]["releaseRangeM"] = release_range_km * 1000.0

    lvl.meta["availableUnits"] = [
        {"unit": sam_unit, "count": 1, "source": "national"},
        {"unit": "soviet_mid_range_radar", "count": 1, "source": "national"},
    ]
    lvl.meta["ammoQuota"] = [
        {"weapon": "nasams_missile", "initial": 18},
        {"weapon": "pac2", "initial": 16},
        {"weapon": "pac3_mse", "initial": 16},
        {"weapon": "s200_missile", "initial": 6},
    ]
    lvl.meta["defeat"] = []

    for n_obj in lvl.waves["nights"]:
        if int(n_obj["night"]) == 2:
            n_obj["waves"] = [
                {
                    "id": "w_platform_test",
                    "atSec": 300.0,
                    "groups": [
                        {
                            "enemy": platform_id,
                            "count": 2,
                            "entry": "entry_east",
                            "spacingSec": 60.0,
                            "route": {"direct": True},
                            "target": {"structure": "tpp"},
                        }
                    ],
                }
            ]

    # Place TPP at (2500, 10000); entry_east is at (26000, 14000) -> distance 23.8 km!
    for st_def in lvl.structures:
        if st_def["id"] == "tpp":
            st_def["pos"] = Vec2(2500.0, 10000.0)
    if release_range_km >= 60.0 and "entry_east" in lvl.entry_points_by_id:
        lvl.entry_points_by_id["entry_east"]["pos"] = Vec2(75000.0, 14000.0)

    radar_id = "early_warning_radar_p3" if sam_unit == "s200_site" else "soviet_mid_range_radar"
    plan = build_validated_plan(
        lvl,
        [
            PlacedUnit(sam_unit, Vec2(15000.0, 11500.0), roster_id=1),
            PlacedUnit(radar_id, Vec2(15500.0, 11500.0), roster_id=2),
        ],
    )
    w = SimWorld(lvl, seed, SimConfig(night_index=2, deployment=plan, end_when_clear=True))
    res = w.run_to_end(PassiveBot())
    m = extract_night_metrics(w, res)
    released_cnt = sum(1 for ev in w.events._outbox if ev.type == SimEventType.MunitionReleased)
    plat_killed = m["kills_by_enemy"].get(platform_id, 0)
    return {
        "platform": platform_id,
        "sam_unit": sam_unit,
        "release_range_km": release_range_km,
        "seed": seed,
        "platform_spawned": 2,
        "platform_killed": plat_killed,
        "munitions_released": released_cnt,
        "pre_release_kill_rate": round(max(0.0, (2.0 - min(2.0, released_cnt / max(1, int(lvl.catalog.platforms[platform_id].get("payload", {}).get("count", 1)))))) / 2.0, 4),
        "threats_impacted": m["threats_impacted"],
    }


def _run_h13_bt3_07_autoresolve(args: Tuple[float, int]) -> Dict[str, Any]:
    """H-13 & B-T3-07: AutoResolve vs Active Command under interceptProbMult = 1.0 and 0.95."""
    prob_mult, seed = args
    base_lvl = get_level("test_01", 1)
    lvl_auto = copy.deepcopy(base_lvl)
    lvl_auto.heightmap = base_lvl.heightmap

    if abs(prob_mult - 1.0) > 1e-6:
        lvl_auto.catalog = copy.deepcopy(base_lvl.catalog)
        ic_tbl = lvl_auto.catalog.rules["intercept"]["classes"]
        for wc in ic_tbl:
            for tc in ic_tbl[wc]:
                ic_tbl[wc][tc] = round(float(ic_tbl[wc][tc]) * prob_mult, 4)

    # AutoResolve: no commands (PassiveBot)
    w_auto = SimWorld(lvl_auto, seed, SimConfig(night_index=1, end_when_clear=True))
    res_auto = w_auto.run_to_end(PassiveBot())
    m_auto = extract_night_metrics(w_auto, res_auto)

    # Active hand-played command bot on test_01: uses CP to manage emission, ammo reserve unlock for Kh-101, and relocation
    class ActiveCommanderBot(TacticalBot):
        name = "active_commander"

        def __init__(self) -> None:
            super().__init__()
            self.init_done = False
            self.unlocked_cm = False

        def decide(self, world: SimWorld) -> List[SimCommand]:
            if not self.init_done:
                self.init_done = True
                for fu in world.state.fire_units.alive_list():
                    for wslot in fu.weapons:
                        if wslot.weapon_id in ("nasams", "nasams_missile"):
                            wslot.ammo_reserve = 5
                        elif wslot.weapon_id in ("iris_t_sls", "iris_t_sls_missile"):
                            wslot.ammo_reserve = 2
            if not self.unlocked_cm and world.state.tick >= 14200:
                self.unlocked_cm = True
                for fu in world.state.fire_units.alive_list():
                    for wslot in fu.weapons:
                        wslot.ammo_reserve = 0
            return SmartBlinkBot().decide(world) + RelocatorBot().decide(world)

    w_act = SimWorld(base_lvl, seed, SimConfig(night_index=1, end_when_clear=True))
    res_act = w_act.run_to_end(ActiveCommanderBot())
    m_act = extract_night_metrics(w_act, res_act)

    return {
        "prob_mult": prob_mult,
        "seed": seed,
        "auto_weighted_loss": m_auto["weighted_loss_frac"],
        "active_weighted_loss": m_act["weighted_loss_frac"],
        "gap": round(m_auto["weighted_loss_frac"] - m_act["weighted_loss_frac"], 4),
        "auto_survived": m_auto["survived"],
        "active_survived": m_act["survived"],
        "auto_intercept_rate": m_auto["non_decoy_intercept_rate"],
        "active_intercept_rate": m_act["non_decoy_intercept_rate"],
    }


def run_h14_h15_reaction_and_mft_cm() -> Dict[str, Any]:
    """H-14 & H-15: Exact reaction step measurements for high-speed threats and MFT shots against CM."""
    lvl = get_level("test_01", 1)
    results_h14: Dict[str, Any] = {}

    for enemy_id in ["shahed_136", "kh101", "kh59", "iskander_m", "kinzhal"]:
        tlvl = copy.deepcopy(lvl)
        tlvl.heightmap = lvl.heightmap
        tlvl.meta = copy.deepcopy(lvl.meta)
        tlvl.waves = copy.deepcopy(lvl.waves)
        tlvl.meta["availableUnits"] = [
            {"unit": "patriot", "count": 1, "source": "national"},
            {"unit": "nasams", "count": 1, "source": "national"},
            {"unit": "mobile_fire_team", "count": 1, "source": "national"},
            {"unit": "soviet_mid_range_radar", "count": 1, "source": "national"},
        ]
        tlvl.meta["ammoQuota"] = [
            {"weapon": "pac3_mse", "initial": 16},
            {"weapon": "pac2", "initial": 16},
            {"weapon": "nasams_missile", "initial": 18},
        ]
        tlvl.meta["defeat"] = []
        for n_obj in tlvl.waves["nights"]:
            if int(n_obj["night"]) == 1:
                n_obj["waves"] = [
                    {
                        "id": f"w_test_{enemy_id}",
                        "atSec": 100.0,
                        "groups": [
                            {
                                "enemy": enemy_id,
                                "count": 1,
                                "entry": "entry_east",
                                "spacingSec": 10.0,
                                "route": {"direct": True},
                                "target": {"structure": "tpp"},
                            }
                        ],
                    }
                ]
        plan = build_validated_plan(
            tlvl,
            [
                PlacedUnit("patriot", Vec2(13500.0, 7300.0), roster_id=1),
                PlacedUnit("nasams", Vec2(13800.0, 7000.0), roster_id=2),
                PlacedUnit("mobile_fire_team", Vec2(16000.0, 8400.0), roster_id=3),
                PlacedUnit("soviet_mid_range_radar", Vec2(14200.0, 7000.0), roster_id=4),
            ],
        )
        w = SimWorld(tlvl, 1, SimConfig(night_index=1, deployment=plan, end_when_clear=True))
        w.run_to_end(PassiveBot())

        spawn_sec = None
        track_sec = None
        first_fire_sec = None
        end_sec = None
        mft_shots = 0
        sam_shots = 0
        for ev in w.events._outbox:
            if ev.type == SimEventType.ThreatSpawned:
                spawn_sec = float(ev.tick)
            elif ev.type == SimEventType.TrackCreated and track_sec is None:
                track_sec = float(ev.tick)
            elif ev.type in (SimEventType.InterceptorLaunched, SimEventType.GunFired):
                if first_fire_sec is None:
                    first_fire_sec = float(ev.tick)
                wid = str(
                    ev.data.get(
                        "weapon_id",
                        ev.fields[2] if ev.type == SimEventType.InterceptorLaunched else ev.fields[1],
                    )
                )
                if wid in ("mobile_fire_team_gun", "machine_gun", "stinger", "manpads_missile"):
                    mft_shots += 1
                else:
                    sam_shots += 1
            elif ev.type in (SimEventType.ThreatImpacted, SimEventType.DebrisFell) or (
                ev.type == SimEventType.InterceptResolved and bool(ev.fields[3])
            ):
                if end_sec is None:
                    end_sec = float(ev.tick)

        results_h14[enemy_id] = {
            "speed_mps": float(lvl.catalog.munitions[enemy_id].get("speedMps", 0.0)),
            "spawn_sec": spawn_sec,
            "track_created_sec": track_sec,
            "first_shot_sec": first_fire_sec,
            "detect_delay_steps": (track_sec - spawn_sec) if (track_sec is not None and spawn_sec is not None) else None,
            "first_shot_reaction_steps": (
                (first_fire_sec - spawn_sec) if (first_fire_sec is not None and spawn_sec is not None) else None
            ),
            "total_flight_window_steps": (
                (end_sec - spawn_sec) if (end_sec is not None and spawn_sec is not None) else None
            ),
            "mft_shots_fired": mft_shots,
            "sam_shots_fired": sam_shots,
        }

    # H-15: Dedicated test of 1 Mobile Fire Team vs 10 passing Kh-101s
    # Note: In unmodified air_defense.json, mobile_fire_team_gun targets = ["UAV", "DECOY", "GB"] (omits "CM").
    # We test both unmodified (0 shots) and patched (+ "CM" in targets, with and without radar cueing).
    tlvl_mft = copy.deepcopy(lvl)
    tlvl_mft.heightmap = lvl.heightmap
    tlvl_mft.waves = copy.deepcopy(lvl.waves)
    for n_obj in tlvl_mft.waves["nights"]:
        if int(n_obj["night"]) == 1:
            n_obj["waves"] = [
                {
                    "id": "w_mft_vs_cm",
                    "atSec": 100.0,
                    "groups": [
                        {
                            "enemy": "kh101",
                            "count": 10,
                            "entry": "entry_east",
                            "spacingSec": 300.0,
                            "route": {"direct": True},
                            "target": {"structure": "tpp"},
                        }
                    ],
                }
            ]
    tlvl_mft.meta = copy.deepcopy(lvl.meta)
    tlvl_mft.meta["defeat"] = []

    tlvl_mft_patched = copy.deepcopy(tlvl_mft)
    tlvl_mft_patched.heightmap = lvl.heightmap
    tlvl_mft_patched.catalog = copy.deepcopy(lvl.catalog)
    tlvl_mft_patched.catalog.weapons["mobile_fire_team_gun"]["targets"] = ["UAV", "DECOY", "GB", "CM"]

    plan_mft_radar = build_validated_plan(
        tlvl_mft,
        [
            PlacedUnit("mobile_fire_team", Vec2(16000.0, 8400.0), roster_id=1),
            PlacedUnit("soviet_mid_range_radar", Vec2(14200.0, 7000.0), roster_id=7),
        ],
    )
    plan_mft_noradar = build_validated_plan(
        tlvl_mft,
        [
            PlacedUnit("mobile_fire_team", Vec2(16000.0, 8400.0), roster_id=1),
        ],
    )
    unmod_kills = []
    unmod_shots = []
    patched_radar_kills = []
    patched_radar_shots = []
    patched_noradar_kills = []
    patched_noradar_shots = []
    for s in range(1, 21):
        w_u = SimWorld(tlvl_mft, s, SimConfig(night_index=1, deployment=plan_mft_radar, end_when_clear=True))
        res_u = w_u.run_to_end(PassiveBot())
        mu = extract_night_metrics(w_u, res_u)
        unmod_kills.append(mu["per_threat_intercept_rate"].get("kh101", 0.0))
        unmod_shots.append(mu["shots_by_weapon"].get("mobile_fire_team_gun", 0) / 10.0)

        w_r = SimWorld(tlvl_mft_patched, s, SimConfig(night_index=1, deployment=plan_mft_radar, end_when_clear=True))
        res_r = w_r.run_to_end(PassiveBot())
        mr = extract_night_metrics(w_r, res_r)
        patched_radar_kills.append(mr["per_threat_intercept_rate"].get("kh101", 0.0))
        patched_radar_shots.append(mr["shots_by_weapon"].get("mobile_fire_team_gun", 0) / 10.0)

        w_nr = SimWorld(tlvl_mft_patched, s, SimConfig(night_index=1, deployment=plan_mft_noradar, end_when_clear=True))
        res_nr = w_nr.run_to_end(PassiveBot())
        mnr = extract_night_metrics(w_nr, res_nr)
        patched_noradar_kills.append(mnr["per_threat_intercept_rate"].get("kh101", 0.0))
        patched_noradar_shots.append(mnr["shots_by_weapon"].get("mobile_fire_team_gun", 0) / 10.0)

    return {
        "h14_reaction_table": results_h14,
        "h15_mft_vs_kh101": {
            "unmodified_data_with_radar_cue": {
                "note": "mobile_fire_team_gun.targets = ['UAV', 'DECOY', 'GB'] omits 'CM', so gun.CM=0.05 in intercept.json is unreachable",
                "kill_rate": summarize_metric(unmod_kills),
                "mg_shots_per_pass": summarize_metric(unmod_shots),
            },
            "patched_cm_target_with_radar_cue": {
                "kill_rate": summarize_metric(patched_radar_kills),
                "mg_shots_per_pass": summarize_metric(patched_radar_shots),
            },
            "patched_cm_target_without_radar_cue_night": {
                "kill_rate": summarize_metric(patched_noradar_kills),
                "mg_shots_per_pass": summarize_metric(patched_noradar_shots),
            },
        },
    }


def run_h08_bt3_01_exchange_matrix() -> Dict[str, Any]:
    """H-08 & B-T3-01: Analytical & simulated verification of hybrid PotentialLoss, ExchangeRatio, wastefulWeapon, and inquiry."""
    structures = [
        ("tpp", 5.0),
        ("substation_central", 3.0),
        ("water_plant", 2.0),
    ]
    threats = [
        ("gerbera", 0.01, 1, True),
        ("shahed_136", 0.05, 3, False),
        ("banderol", 0.50, 4, False),
        ("kh59", 2.00, 6, False),
        ("kh101", 13.00, 7, False),
        ("iskander_m", 3.00, 8, False),
        ("kinzhal", 10.00, 9, False),
    ]
    weapons = [
        ("machine_gun", 0.001),
        ("gepard_35mm", 0.03),
        ("stinger", 0.04),
        ("iris_t_sls", 0.40),
        ("s300_missile", 0.80),
        ("nasams", 0.85),
        ("aster_30", 2.00),
        ("pac2", 3.00),
        ("pac3_mse", 4.00),
    ]

    matrix: List[Dict[str, Any]] = []
    for tid, e_cost, dmg_lvl, is_decoy in threats:
        for sid, weight in structures:
            if is_decoy:
                struct_loss = 0.0
                pot_loss = 0.0
            else:
                struct_loss = (2 ** (dmg_lvl - 1)) * 0.1 * weight if dmg_lvl > 0 else 0.0
                pot_loss = max(e_cost, struct_loss)
            for wid, w_cost in weapons:
                ratio_hybrid = pot_loss / w_cost if w_cost > 0 else 999.0
                ratio_raw_cost = (0.0 if is_decoy else e_cost) / w_cost if w_cost > 0 else 999.0
                triggers_wasteful_hybrid = (w_cost >= 0.8) and (ratio_hybrid < 0.2)
                triggers_wasteful_raw = (w_cost >= 0.8) and (ratio_raw_cost < 0.2)
                matrix.append(
                    {
                        "threat": tid,
                        "enemy_cost_musd": e_cost,
                        "damage_level": dmg_lvl,
                        "structure": sid,
                        "weight": weight,
                        "struct_loss_term_musd": round(struct_loss, 4),
                        "potential_loss_musd": round(pot_loss, 4),
                        "weapon": wid,
                        "shot_cost_musd": w_cost,
                        "single_hit_exchange_ratio": round(ratio_hybrid, 4),
                        "raw_cost_exchange_ratio": round(ratio_raw_cost, 4),
                        "triggers_wasteful_weapon": triggers_wasteful_hybrid,
                        "triggers_wasteful_if_raw_cost": triggers_wasteful_raw,
                    }
                )
    return {"matrix_sample": matrix}


def run_bt3_04_campaign_trust_simulation() -> Dict[str, Any]:
    """B-T3-04: Simulate 8 Line-A levels (24 nights total) across N=30 seeds comparing Always-Request vs Never-Request vs Adversity Recovery."""
    strategies = ["never_request", "always_request_small", "always_request_large", "adversity_recovery"]
    out: Dict[str, Any] = {}

    for strat in strategies:
        total_resources_list = []
        floor_dwell_fracs = []
        recovered_count = 0
        adversity_trials = 0

        for seed in range(1, 31):
            rng = SimRandom(seed * 1009 + 7)
            trust = 50.0
            setbacks = 0
            total_missile_rounds_received = 0.0
            nights_at_floor = 0
            total_nights = 0
            hit_low_trust = False
            recovered = False

            for lvl_idx in range(6, 14):
                trust_mod = max(-0.10, min(0.10, ((trust - 50.0) / 50.0) * 0.10))
                base_rounds = 36.0
                level_rounds = round(base_rounds * (1.0 + trust_mod))
                total_missile_rounds_received += level_rounds

                if strat == "always_request_small" and trust - 8.0 >= 10.0:
                    trust -= 8.0
                    total_missile_rounds_received += 6.0
                elif strat == "always_request_large" and trust - 20.0 >= 10.0:
                    trust -= 20.0
                    total_missile_rounds_received += 12.0

                for n_idx in range(3):
                    total_nights += 1
                    if strat == "adversity_recovery" and lvl_idx in (6, 7) and n_idx < 2:
                        d_night = -8.0
                        setbacks += 1
                    else:
                        d_night = rng.range(-2.0, 4.0)
                        if d_night < -1.0:
                            setbacks += 1
                        else:
                            setbacks = 0

                    trust = max(10.0, min(100.0, trust + d_night))
                    if trust <= 15.0:
                        nights_at_floor += 1
                        hit_low_trust = True
                    if setbacks >= 2:
                        trust = max(trust, 30.0)
                        total_missile_rounds_received += round(base_rounds * 0.20)
                        setbacks = 0

                trust = max(10.0, min(100.0, trust + 5.0))
                if hit_low_trust and trust >= 45.0:
                    recovered = True

            if hit_low_trust:
                adversity_trials += 1
                if recovered:
                    recovered_count += 1
            total_resources_list.append(total_missile_rounds_received)
            floor_dwell_fracs.append(nights_at_floor / total_nights)

        out[strat] = {
            "total_missile_rounds": summarize_metric(total_resources_list),
            "trust_floor_dwell_frac": summarize_metric(floor_dwell_fracs),
            "recovery_rate": round(recovered_count / max(1, adversity_trials), 4) if adversity_trials > 0 else 1.0,
        }

    never_mean = out["never_request"]["total_missile_rounds"]["mean"]
    small_mean = out["always_request_small"]["total_missile_rounds"]["mean"]
    large_mean = out["always_request_large"]["total_missile_rounds"]["mean"]
    spread_small = abs(small_mean - never_mean) / max(1.0, never_mean)
    spread_large = abs(large_mean - never_mean) / max(1.0, never_mean)
    out["request_strategy_spread_small"] = round(spread_small, 4)
    out["request_strategy_spread_large"] = round(spread_large, 4)
    return out


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------
def main() -> None:
    t0 = time.perf_counter()
    max_workers = min(8, os.cpu_count() or 4)
    n_seeds = 12
    seeds = list(range(1, n_seeds + 1))

    print(f"[D4-1] Starting quantitative playability analysis (N={n_seeds} seeds, workers={max_workers})...")

    results: Dict[str, Any] = {
        "meta": {
            "level": "test_01",
            "n_seeds": n_seeds,
            "workers": max_workers,
        }
    }

    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        # -------------------------------------------------------------------
        # Experiment 1: 8 Bots on test_01 (Night 1 + Night 2 Chained)
        # -------------------------------------------------------------------
        t_exp1 = time.perf_counter()
        bot_names = [
            "passive",
            "default",
            "always_emit",
            "never_emit",
            "smart_blink",
            "hoarder",
            "wasteful",
            "relocator",
        ]
        exp1_tasks = [(b, s) for b in bot_names for s in seeds]
        exp1_raw = list(pool.map(_run_exp1_single, exp1_tasks))
        exp1_by_bot: Dict[str, Any] = {}
        for b in bot_names:
            b_runs = [r for r in exp1_raw if r["bot"] == b]
            exp1_by_bot[b] = aggregate_bot_runs(b_runs)
        results["experiment_1_bots"] = exp1_by_bot
        print(
            f"[D4-1] Experiment 1 (8 bots x 2 nights x {n_seeds} seeds) completed in {time.perf_counter() - t_exp1:.1f}s"
        )

        # -------------------------------------------------------------------
        # Experiment 2: 4 Deployment Topologies (Series 2A & Series 2B)
        # -------------------------------------------------------------------
        t_exp2 = time.perf_counter()
        topos_2a = ["D_default_spiral", "D_layered", "D_all_stacked", "D_radar_forward_exposed"]
        topos_2b = ["D_default", "D_all_stacked", "D_no_decoy_no_ew", "D_radar_forward_exposed"]
        exp2_tasks = [
            ("2A", t, "passive", s) for t in topos_2a for s in seeds
        ] + [
            ("2B", t, "passive", s) for t in topos_2b for s in seeds
        ]
        exp2_raw = list(pool.map(_run_exp2_single, exp2_tasks))
        exp2_summary: Dict[str, Any] = {"series_2a_standard_test01": {}, "series_2b_combined_arms": {}}
        for t in topos_2a:
            t_runs = [r for r in exp2_raw if r["series"] == "2A" and r["topology"] == t]
            exp2_summary["series_2a_standard_test01"][t] = aggregate_bot_runs(t_runs)
        for t in topos_2b:
            t_runs = [r for r in exp2_raw if r["series"] == "2B" and r["topology"] == t]
            exp2_summary["series_2b_combined_arms"][t] = aggregate_bot_runs(t_runs)
        results["experiment_2_deployments"] = exp2_summary
        print(
            f"[D4-1] Experiment 2 (8 topologies x 2 nights x {n_seeds} seeds) completed in {time.perf_counter() - t_exp2:.1f}s"
        )

        # -------------------------------------------------------------------
        # Experiment 3: Targeted Mechanism & Hypothesis Verification
        # -------------------------------------------------------------------
        t_exp3 = time.perf_counter()
        exp3: Dict[str, Any] = {}

        # H-01: 30 random valid positions for NASAMS (and shifted SAM cluster)
        rng_pos = SimRandom(42)
        h01_tasks = []
        for idx in range(30):
            while True:
                px = round(rng_pos.range(2000.0, 18500.0), 1)
                py = round(rng_pos.range(2000.0, 18500.0), 1)
                if not (px >= 13000.0 and py >= 12500.0):
                    break
            h01_tasks.append((idx, px, py, "nasams_only"))
            h01_tasks.append((idx, px, py, "shift_all_sams"))
        h01_raw = list(pool.map(_run_h01_position, h01_tasks))
        nasams_only_runs = [r for r in h01_raw if r["mode"] == "nasams_only"]
        shift_all_runs = [r for r in h01_raw if r["mode"] == "shift_all_sams"]
        exp3["H01_position_sensitivity"] = {
            "nasams_only_30_positions": {
                "survived_rate": summarize_metric([r["survived_rate"] for r in nasams_only_runs]),
                "weighted_loss_frac": summarize_metric([r["weighted_loss_frac"] for r in nasams_only_runs]),
                "non_decoy_intercept_rate": summarize_metric([r["non_decoy_intercept_rate"] for r in nasams_only_runs]),
                "kh101_intercept_rate": summarize_metric([r["kh101_intercept_rate"] for r in nasams_only_runs]),
                "exp_100_count": summarize_metric([r["exp_100_count"] for r in nasams_only_runs]),
                "positions": nasams_only_runs,
            },
            "shift_all_sams_30_positions": {
                "survived_rate": summarize_metric([r["survived_rate"] for r in shift_all_runs]),
                "weighted_loss_frac": summarize_metric([r["weighted_loss_frac"] for r in shift_all_runs]),
                "non_decoy_intercept_rate": summarize_metric([r["non_decoy_intercept_rate"] for r in shift_all_runs]),
                "kh101_intercept_rate": summarize_metric([r["kh101_intercept_rate"] for r in shift_all_runs]),
                "exp_100_count": summarize_metric([r["exp_100_count"] for r in shift_all_runs]),
            },
        }

        # H-02: Sensor network dependency
        h02_cfgs = ["full_sensors", "radar_only", "local_only_no_radar", "zero_external_sensors"]
        h02_raw = list(pool.map(_run_h02_sensors, [(c, s) for c in h02_cfgs for s in seeds]))
        exp3["H02_sensor_dependency"] = {}
        for c in h02_cfgs:
            c_items = [r["metrics"] for r in h02_raw if r["config"] == c]
            exp3["H02_sensor_dependency"][c] = {
                "survived_rate": round(sum(it["survived"] for it in c_items) / len(c_items), 4),
                "weighted_loss_frac": summarize_metric([it["weighted_loss_frac"] for it in c_items]),
                "non_decoy_intercept_rate": summarize_metric([it["non_decoy_intercept_rate"] for it in c_items]),
                "shahed_intercept_rate": summarize_metric(
                    [it["per_threat_intercept_rate"].get("shahed_136", 0.0) for it in c_items]
                ),
                "kh101_intercept_rate": summarize_metric(
                    [it["per_threat_intercept_rate"].get("kh101", 0.0) for it in c_items]
                ),
            }

        # H-03, B-T3-05, B-T3-10: 6 Emission Strategies
        em_strats = ["always_on", "on_warning", "intermittent", "silent_standby", "decoy_coordinated", "silent"]
        h03_tasks = [(scen, st, s) for scen in ("test_01", "arm_sead") for st in em_strats for s in seeds]
        h03_raw = list(pool.map(_run_h03_bt3_05_10_emission, h03_tasks))
        static_exp_mult = {
            "always_on": 1.0,
            "on_warning": 0.7,
            "intermittent": 0.45,
            "silent_standby": 0.15,
            "decoy_coordinated": 0.25,
            "silent": 0.0,
        }
        static_eff_mult = {
            "always_on": 1.0,
            "on_warning": 0.9,
            "intermittent": 0.75,
            "silent_standby": 0.55,
            "decoy_coordinated": 0.85,
            "silent": 0.0,
        }
        exp3["H03_BT3_05_10_emission"] = {}
        for scen in ("test_01", "arm_sead"):
            exp3["H03_BT3_05_10_emission"][scen] = {}
            base_runs = [r for r in h03_raw if r["scenario"] == scen and r["strategy"] == "always_on"]
            base_mean_exp = sum(r["n1_mean_exposure"] for r in base_runs) / len(base_runs)
            base_radar_exp = sum(r["n1_radar_exposure"] for r in base_runs) / len(base_runs)
            base_ir = sum(r["n1_intercept_rate"] for r in base_runs) / len(base_runs)
            for st in em_strats:
                s_runs = [r for r in h03_raw if r["scenario"] == scen and r["strategy"] == st]
                emp_mean_exp = sum(r["n1_mean_exposure"] for r in s_runs) / len(s_runs)
                emp_radar_exp = sum(r["n1_radar_exposure"] for r in s_runs) / len(s_runs)
                emp_ir = sum(r["n1_intercept_rate"] for r in s_runs) / len(s_runs)
                emp_exp_ratio = (emp_mean_exp / base_mean_exp) if base_mean_exp > 0 else 0.0
                emp_radar_ratio = (emp_radar_exp / base_radar_exp) if base_radar_exp > 0 else 0.0
                emp_ir_ratio = (emp_ir / base_ir) if base_ir > 0 else 0.0
                exp3["H03_BT3_05_10_emission"][scen][st] = {
                    "n1_survived_rate": round(sum(r["n1_survived"] for r in s_runs) / len(s_runs), 4),
                    "n2_survived_rate": round(sum(r["n2_survived"] for r in s_runs) / len(s_runs), 4),
                    "both_survived_rate": round(sum(r["both_survived"] for r in s_runs) / len(s_runs), 4),
                    "n1_intercept_rate": summarize_metric([r["n1_intercept_rate"] for r in s_runs]),
                    "n1_weighted_loss": summarize_metric([r["n1_weighted_loss"] for r in s_runs]),
                    "n2_weighted_loss": summarize_metric([r["n2_weighted_loss"] for r in s_runs]),
                    "n1_mean_exposure": summarize_metric([r["n1_mean_exposure"] for r in s_runs]),
                    "n1_radar_exposure": summarize_metric([r["n1_radar_exposure"] for r in s_runs]),
                    "n1_exp_100_count": summarize_metric([float(r["n1_exp_100_count"]) for r in s_runs]),
                    "n1_known_targets_out": summarize_metric([float(r["n1_known_targets_out"]) for r in s_runs]),
                    "n1_units_lost": summarize_metric([float(r["n1_units_lost"]) for r in s_runs]),
                    "n2_units_lost": summarize_metric([float(r["n2_units_lost"]) for r in s_runs]),
                    "n1_arm_missed": summarize_metric([float(r["n1_arm_missed"]) for r in s_runs]),
                    "static_exposure_mult": static_exp_mult[st],
                    "empirical_mean_exposure_ratio": round(emp_exp_ratio, 4),
                    "empirical_radar_exposure_ratio": round(emp_radar_ratio, 4),
                    "exposure_mult_drift_mean": round(emp_exp_ratio - static_exp_mult[st], 4),
                    "exposure_mult_drift_radar": round(emp_radar_ratio - static_exp_mult[st], 4),
                    "static_efficiency_mult": static_eff_mult[st],
                    "empirical_intercept_ratio": round(emp_ir_ratio, 4),
                }

        # H-04 & B-T3-02: Ammo Reservation Policies
        h04_policies = [
            "wasteful_any",
            "reserve_4_unlock_cm",
            "reserve_6_strict",
            "hoarder_ballistic_only",
            "whitelist_cm_only",
            "layered_forward_mft_plus_cm_nasams",
        ]
        h04_raw = list(pool.map(_run_h04_ammo_rules, [(p, s) for p in h04_policies for s in seeds]))
        exp3["H04_BT3_02_ammo_policies"] = {}
        for p in h04_policies:
            p_items = [r["metrics"] for r in h04_raw if r["policy"] == p]
            exp3["H04_BT3_02_ammo_policies"][p] = {
                "survived_rate": round(sum(it["survived"] for it in p_items) / len(p_items), 4),
                "weighted_loss_frac": summarize_metric([it["weighted_loss_frac"] for it in p_items]),
                "non_decoy_intercept_rate": summarize_metric([it["non_decoy_intercept_rate"] for it in p_items]),
                "shahed_intercept_rate": summarize_metric(
                    [it["per_threat_intercept_rate"].get("shahed_136", 0.0) for it in p_items]
                ),
                "kh101_intercept_rate": summarize_metric(
                    [it["per_threat_intercept_rate"].get("kh101", 0.0) for it in p_items]
                ),
                "high_threat_leaks_with_reserve": summarize_metric(
                    [float(it["high_threat_leaks_with_reserve"]) for it in p_items]
                ),
                "shot_cost_musd": summarize_metric([it["shot_cost_musd"] for it in p_items]),
                "exchange_ratio": summarize_metric([it["exchange_ratio"] for it in p_items]),
                "nasams_shots": summarize_metric(
                    [float(it["shots_by_weapon"].get("nasams_missile", it["shots_by_weapon"].get("nasams", 0))) for it in p_items]
                ),
                "iris_t_shots": summarize_metric(
                    [float(it["shots_by_weapon"].get("iris_t_sls_missile", it["shots_by_weapon"].get("iris_t_sls", 0))) for it in p_items]
                ),
                "mft_shots": summarize_metric(
                    [
                        float(
                            it["shots_by_weapon"].get("mobile_fire_team_gun", 0)
                            + it["shots_by_weapon"].get("stinger", 0)
                            + it["shots_by_weapon"].get("machine_gun", 0)
                        )
                        for it in p_items
                    ]
                ),
                "trust_applied": summarize_metric([it["trust"]["applied"] for it in p_items]),
                "trust_dHoard": summarize_metric([it["trust"]["dHoard"] for it in p_items]),
            }

        # H-05: Night Optical Penalty & Searchlight
        h05_conds = [
            "night_no_radar_no_searchlight",
            "night_no_radar_with_searchlight",
            "night_with_acoustic_no_searchlight",
            "night_with_acoustic_with_searchlight",
            "night_with_radar_no_searchlight",
            "day_clear",
        ]
        h05_raw = list(pool.map(_run_h05_night_optical, [(c, s) for c in h05_conds for s in seeds]))
        exp3["H05_night_optical"] = {}
        for c in h05_conds:
            c_items = [r["metrics"] for r in h05_raw if r["condition"] == c]
            exp3["H05_night_optical"][c] = {
                "shahed_intercept_rate": summarize_metric(
                    [it["per_threat_intercept_rate"].get("shahed_136", 0.0) for it in c_items]
                ),
                "mft_gun_shots": summarize_metric(
                    [float(it["shots_by_weapon"].get("mobile_fire_team_gun", 0)) for it in c_items]
                ),
                "weighted_loss_frac": summarize_metric([it["weighted_loss_frac"] for it in c_items]),
            }

        # H-07: Decoy Discrimination
        h07_conds = ["3d_radar_precise", "2d_radar_approximate", "no_radar_vague_only"]
        h07_raw = list(pool.map(_run_h07_decoy, [(c, s) for c in h07_conds for s in seeds]))
        exp3["H07_decoy_discrimination"] = {}
        for c in h07_conds:
            c_runs = [r for r in h07_raw if r["condition"] == c]
            exp3["H07_decoy_discrimination"][c] = {
                "discriminated_count": summarize_metric([float(r["discriminated_count"]) for r in c_runs]),
                "decoy_killed_wasted_shots": summarize_metric([float(r["decoy_killed"]) for r in c_runs]),
                "decoy_let_through_rate": summarize_metric([r["decoy_let_through_rate"] for r in c_runs]),
                "shahed_intercept_rate": summarize_metric([r["shahed_intercept_rate"] for r in c_runs]),
                "shot_cost_musd": summarize_metric([r["shot_cost_musd"] for r in c_runs]),
                "exchange_ratio": summarize_metric([r["exchange_ratio"] for r in c_runs]),
            }

        # H-10: Probe -> Avoidance Closed Loop
        h10_conds = ["with_probe_always_on", "no_probe_wave", "probe_silent_during_w1"]
        h10_raw = list(pool.map(_run_h10_probe_avoidance, [(c, s) for c in h10_conds for s in seeds]))
        exp3["H10_probe_avoidance"] = {}
        for c in h10_conds:
            c_runs = [r for r in h10_raw if r["condition"] == c]
            exp3["H10_probe_avoidance"][c] = {
                "known_targets_count": summarize_metric([float(r["known_targets_count"]) for r in c_runs]),
                "kh101_max_lateral_deviation_m": summarize_metric(
                    [r["kh101_max_lateral_deviation_m"] for r in c_runs]
                ),
                "kh101_waypoint_count": summarize_metric([float(r["kh101_waypoint_count"]) for r in c_runs]),
                "kh101_intercept_rate": summarize_metric([r["kh101_intercept_rate"] for r in c_runs]),
                "weighted_loss_frac": summarize_metric([r["weighted_loss_frac"] for r in c_runs]),
                "survived_rate": round(sum(r["survived"] for r in c_runs) / len(c_runs), 4),
            }

        # H-11: Ballistic Missile Salvo & Map Size
        h11_scales = ("20km", "60km", "20km_fast_react_2s", "60km_fast_react_2s")
        h11_tasks = [
            (m_id, m_scale, sls, s)
            for m_id in ("iskander_m", "s300_ground", "kinzhal")
            for m_scale in h11_scales
            for sls in (True, False)
            for s in seeds
        ]
        h11_raw = list(pool.map(_run_h11_ballistic, h11_tasks))
        exp3["H11_ballistic_salvo"] = {}
        for m_id in ("iskander_m", "s300_ground", "kinzhal"):
            exp3["H11_ballistic_salvo"][m_id] = {}
            for m_scale in h11_scales:
                for sls in (True, False):
                    key = f"{m_scale}_sls_{sls}"
                    sub = [
                        r
                        for r in h11_raw
                        if r["missile"] == m_id and r["map_scale"] == m_scale and r["has_sls"] == sls
                    ]
                    exp3["H11_ballistic_salvo"][m_id][key] = {
                        "intercept_rate": summarize_metric([r["intercept_rate"] for r in sub]),
                        "shots_fired": summarize_metric([float(r["shots_fired"]) for r in sub]),
                        "shot_cost_musd": summarize_metric([r["shot_cost_musd"] for r in sub]),
                        "exchange_ratio": summarize_metric([r["exchange_ratio"] for r in sub]),
                        "first_shot_reaction_sec": summarize_metric([r["first_shot_reaction_sec"] for r in sub]),
                    }

        # H-13 & B-T3-07: AutoResolve vs Active Command
        h13_tasks = [(pm, s) for pm in (1.0, 0.95) for s in seeds]
        h13_raw = list(pool.map(_run_h13_bt3_07_autoresolve, h13_tasks))
        exp3["H13_BT3_07_autoresolve"] = {}
        for pm in (1.0, 0.95):
            sub = [r for r in h13_raw if abs(r["prob_mult"] - pm) < 1e-6]
            exp3["H13_BT3_07_autoresolve"][f"mult_{pm}"] = {
                "auto_weighted_loss": summarize_metric([r["auto_weighted_loss"] for r in sub]),
                "active_weighted_loss": summarize_metric([r["active_weighted_loss"] for r in sub]),
                "auto_resolve_gap": summarize_metric([r["gap"] for r in sub]),
                "auto_survived_rate": round(sum(r["auto_survived"] for r in sub) / len(sub), 4),
                "active_survived_rate": round(sum(r["active_survived"] for r in sub) / len(sub), 4),
                "auto_intercept_rate": summarize_metric([r["auto_intercept_rate"] for r in sub]),
                "active_intercept_rate": summarize_metric([r["active_intercept_rate"] for r in sub]),
            }

        # B-T3-08: EW vs National Spoofing
        bt3_08_modes = [
            "no_ew",
            "national_spoofing_only",
            "area_nav_jammer",
            "nav_spoofer",
            "counter_uas_jammer",
            "both_national_and_unit_jammer",
        ]
        bt3_08_raw = list(pool.map(_run_bt3_08_ew, [(m, s) for m in bt3_08_modes for s in seeds]))
        exp3["BT3_08_ew_differentiation"] = {}
        for m in bt3_08_modes:
            sub = [r for r in bt3_08_raw if r["ew_mode"] == m]
            exp3["BT3_08_ew_differentiation"][m] = {
                "threats_impacted": summarize_metric([float(r["threats_impacted"]) for r in sub]),
                "threats_ew_downed": summarize_metric([float(r["threats_ew_downed"]) for r in sub]),
                "tpp_loss_hp": summarize_metric([r["tpp_loss_hp"] for r in sub]),
                "weighted_loss_frac": summarize_metric([r["weighted_loss_frac"] for r in sub]),
            }

        # B-T3-09: Platform Pre-Release Shootdown
        bt3_09_tasks = [
            (plat, sam, r_km, s)
            for plat in ("su24m", "su34", "tu22m3")
            for sam in ("nasams", "patriot", "s200")
            for r_km in (60.0, 20.0, 10.0)
            for s in seeds
        ]
        bt3_09_raw = list(pool.map(_run_bt3_09_platform, bt3_09_tasks))
        exp3["BT3_09_platform_pre_release"] = {}
        for plat in ("su24m", "su34", "tu22m3"):
            exp3["BT3_09_platform_pre_release"][plat] = {}
            for sam in ("nasams", "patriot", "s200"):
                exp3["BT3_09_platform_pre_release"][plat][sam] = {}
                for r_km in (60.0, 20.0, 10.0):
                    sub = [
                        r
                        for r in bt3_09_raw
                        if r["platform"] == plat and r["sam_unit"] == sam and abs(r["release_range_km"] - r_km) < 1e-6
                    ]
                    exp3["BT3_09_platform_pre_release"][plat][sam][f"release_{int(r_km)}km"] = {
                        "platform_killed": summarize_metric([float(r["platform_killed"]) for r in sub]),
                        "munitions_released": summarize_metric([float(r["munitions_released"]) for r in sub]),
                        "pre_release_kill_rate": summarize_metric([r["pre_release_kill_rate"] for r in sub]),
                        "threats_impacted": summarize_metric([float(r["threats_impacted"]) for r in sub]),
                    }

    # Fast in-process checks for H-08/B-T3-01, H-14/H-15, and B-T3-04
    exp3["H08_BT3_01_exchange_matrix"] = run_h08_bt3_01_exchange_matrix()
    exp3["H14_H15_reaction_and_mft"] = run_h14_h15_reaction_and_mft_cm()
    exp3["BT3_04_campaign_trust"] = run_bt3_04_campaign_trust_simulation()

    results["experiment_3_mechanisms"] = exp3
    elapsed = time.perf_counter() - t0
    results["meta"]["elapsed_sec"] = round(elapsed, 2)
    print(f"[D4-1] Experiment 3 completed in {time.perf_counter() - t_exp3:.1f}s (Total elapsed: {elapsed:.1f}s)")

    out_path = REPO_ROOT / "tools" / "papersim" / "experiments" / "d4_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[D4-1] Wrote results to {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
