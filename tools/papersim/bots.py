"""Built-in tactical bots and batch statistical/anomaly analyzer (07_tools.md §§3.3-3.4)."""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Sequence

from .entities import (
    NightOutcome,
    NightResult,
    PlayerUnitEntity,
    SimCommand,
    SimCommandType,
    UnitDeployState,
)
from .world import SimWorld


class TacticalBot:
    """Base tactical bot interface invoked once per tick before SimWorld.step()."""

    name: str = "passive"

    def __init__(self) -> None:
        self._initialized: bool = False
        self._last_clear_tick: int = 0
        self._relocated_units: set[int] = set()

    def __call__(self, world: SimWorld) -> List[SimCommand]:
        return self.decide(world)

    def decide(self, world: SimWorld) -> List[SimCommand]:
        return []


class PassiveBot(TacticalBot):
    name = "passive"


class DefaultBot(TacticalBot):
    """Balanced baseline bot: manages civil air-raid alert, answers choices, reserves expensive SAMs for CM/BM, and calls fighter support."""

    name = "default"

    def decide(self, world: SimWorld) -> List[SimCommand]:
        cmds: List[SimCommand] = []
        st = world.state
        tick = st.tick + 1

        if not self._initialized:
            self._initialized = True
            cat = world.level.catalog
            for fu in st.fire_units.alive_list():
                for wslot in fu.weapons:
                    wdef = cat.weapons.get(wslot.weapon_id, {})
                    if float(wdef.get("shotCostMusd", 0.0) or 0.0) >= 0.80:
                        wslot.ammo_reserve = 3

        # 1. Answer any pending choices immediately with default option
        for ch in st.choices.alive_list():
            cmds.append(
                SimCommand(
                    type=SimCommandType.AnswerChoice,
                    effective_tick=tick,
                    params={"choiceId": ch.id, "option": ch.default_option},
                )
            )

        # 2. Civil air-raid alert management
        has_threat = st.threats.count_alive() > 0 or len(st.sensing.emitted_early_warnings) > 0
        if st.threats.count_alive() > 0:
            self._last_clear_tick = tick
        if not st.civil.alert_on and has_threat and st.threats.count_alive() > 0 and st.commands.command_points >= 2:
            cmds.append(
                SimCommand(
                    type=SimCommandType.SetAirRaidAlert,
                    effective_tick=tick,
                    params={"on": True},
                )
            )
        elif st.civil.alert_on and st.threats.count_alive() == 0 and (tick - self._last_clear_tick) >= 120 and st.commands.command_points >= 2:
            cmds.append(
                SimCommand(
                    type=SimCommandType.SetAirRaidAlert,
                    effective_tick=tick,
                    params={"on": False},
                )
            )

        # 3. Call fighter support if available and >= 3 threats active
        if (
            st.support.sorties_remaining > 0
            and st.support_assets.count_alive() == 0
            and st.threats.count_alive() >= 3
        ):
            cmds.append(
                SimCommand(
                    type=SimCommandType.CallSupport,
                    effective_tick=tick,
                    params={"supportId": "fighter", "pos": [10000.0, 10000.0]},
                )
            )

        return cmds


class AlwaysEmitBot(TacticalBot):
    """Forces all emitters to continuous and refuses to shut down on ARM."""

    name = "always_emit"

    def decide(self, world: SimWorld) -> List[SimCommand]:
        cmds: List[SimCommand] = []
        st = world.state
        tick = st.tick + 1
        if not self._initialized:
            self._initialized = True
            for store in (st.fire_units, st.sensors, st.ew_units, st.deception_units):
                for u in store.alive_list():
                    if u.emitter is not None:
                        u.emitter.policy_id = "continuous"
                        u.emitter.on = True
                        u.emitter.on_arm_incoming = 1  # keep emitting
        for ch in st.choices.alive_list():
            opt = 1 if ch.kind == 0 and ch.option_count > 1 else ch.default_option
            cmds.append(
                SimCommand(
                    type=SimCommandType.AnswerChoice,
                    effective_tick=tick,
                    params={"choiceId": ch.id, "option": opt},
                )
            )
        return cmds


class NeverEmitBot(TacticalBot):
    """Silences all emitters at night start."""

    name = "never_emit"

    def decide(self, world: SimWorld) -> List[SimCommand]:
        st = world.state
        if not self._initialized:
            self._initialized = True
            for store in (st.fire_units, st.sensors, st.ew_units, st.deception_units):
                for u in store.alive_list():
                    if u.emitter is not None:
                        u.emitter.policy_id = "silent"
                        u.emitter.on = False
        return []


class SmartBlinkBot(TacticalBot):
    """Uses blink/intermittent emission, reserves expensive SAMs for CM/BM, shuts down on ARM, and relocates at exposure >= 70."""

    name = "smart_blink"

    def decide(self, world: SimWorld) -> List[SimCommand]:
        cmds: List[SimCommand] = []
        st = world.state
        tick = st.tick + 1
        if not self._initialized:
            self._initialized = True
            cat = world.level.catalog
            for fu in st.fire_units.alive_list():
                for wslot in fu.weapons:
                    wdef = cat.weapons.get(wslot.weapon_id, {})
                    if float(wdef.get("shotCostMusd", 0.0) or 0.0) >= 0.80:
                        wslot.ammo_reserve = 3
            for store in (st.fire_units, st.sensors):
                for u in store.alive_list():
                    if u.emitter is not None and not getattr(u, "automatic", False):
                        u.emitter.policy_id = "blink"
                        u.emitter.duty_on_sec = 45.0
                        u.emitter.duty_off_sec = 15.0
                        u.emitter.on_arm_incoming = 0

        for ch in st.choices.alive_list():
            cmds.append(
                SimCommand(
                    type=SimCommandType.AnswerChoice,
                    effective_tick=tick,
                    params={"choiceId": ch.id, "option": 0},
                )
            )

        if st.commands.command_points >= 1:
            cmd = _try_relocate_exposed_unit(world, threshold=70.0, relocated_set=self._relocated_units, tick=tick)
            if cmd is not None:
                cmds.append(cmd)
        return cmds


class HoarderBot(TacticalBot):
    """Conserves medium/long-range missiles by restricting them to high_value_only / ballistic_only."""

    name = "hoarder"

    def decide(self, world: SimWorld) -> List[SimCommand]:
        st = world.state
        if not self._initialized:
            self._initialized = True
            cat = world.level.catalog
            for fu in st.fire_units.alive_list():
                for wslot in fu.weapons:
                    wdef = cat.weapons.get(wslot.weapon_id, {})
                    if float(wdef.get("shotCostMusd", 0.0) or 0.0) >= 0.35:
                        wslot.rule = 1  # BallisticOnly
        return []


class WastefulBot(TacticalBot):
    """Fires all weapons at any target in range and keeps emitters continuously active."""

    name = "wasteful"

    def decide(self, world: SimWorld) -> List[SimCommand]:
        st = world.state
        if not self._initialized:
            self._initialized = True
            for fu in st.fire_units.alive_list():
                for wslot in fu.weapons:
                    wslot.rule = 0  # Any
                    wslot.ammo_reserve = 0
                if fu.emitter is not None:
                    fu.emitter.policy_id = "continuous"
                    fu.emitter.on = True
        return []


class RelocatorBot(TacticalBot):
    """Aggressively relocates mobile units as soon as exposure reaches 40 and reserves expensive SAMs."""

    name = "relocator"

    def decide(self, world: SimWorld) -> List[SimCommand]:
        cmds: List[SimCommand] = []
        st = world.state
        tick = st.tick + 1
        if not self._initialized:
            self._initialized = True
            cat = world.level.catalog
            for fu in st.fire_units.alive_list():
                for wslot in fu.weapons:
                    wdef = cat.weapons.get(wslot.weapon_id, {})
                    if float(wdef.get("shotCostMusd", 0.0) or 0.0) >= 0.80:
                        wslot.ammo_reserve = 3
        if st.commands.command_points >= 1:
            cmd = _try_relocate_exposed_unit(world, threshold=40.0, relocated_set=self._relocated_units, tick=tick)
            if cmd is not None:
                cmds.append(cmd)
        return cmds


def _try_relocate_exposed_unit(
    world: SimWorld,
    threshold: float,
    relocated_set: set[int],
    tick: int,
) -> SimCommand | None:
    st = world.state
    cat = world.level.catalog
    alts = world.level.deploy.get("alternatePositions") or []
    avail_alts = [ap for ap in alts if ap.get("id") not in st.commands.alternate_positions_used]
    if not avail_alts:
        return None

    candidates: List[PlayerUnitEntity] = []
    for store in (st.fire_units, st.sensors, st.ew_units):
        for u in store.alive_list():
            if getattr(u, "automatic", False) or u.id in relocated_set:
                continue
            if u.deploy_state != UnitDeployState.Deployed or u.exposure < threshold:
                continue
            udef = cat.get_player_unit_def(u.def_id or "")
            if udef.get("mobility") == "fixed":
                continue
            candidates.append(u)

    if not candidates:
        return None
    candidates.sort(key=lambda u: (-u.exposure, u.id))
    chosen = candidates[0]
    alt = avail_alts[0]
    relocated_set.add(chosen.id)
    return SimCommand(
        type=SimCommandType.RelocateUnit,
        effective_tick=tick,
        params={"unitId": chosen.id, "alternatePositionId": alt["id"]},
    )


BOT_REGISTRY: Dict[str, Callable[[], TacticalBot]] = {
    "passive": PassiveBot,
    "default": DefaultBot,
    "always_emit": AlwaysEmitBot,
    "never_emit": NeverEmitBot,
    "smart_blink": SmartBlinkBot,
    "hoarder": HoarderBot,
    "wasteful": WastefulBot,
    "relocator": RelocatorBot,
}


def create_bot(name: str) -> TacticalBot:
    if name not in BOT_REGISTRY:
        raise ValueError(f"Unknown bot '{name}'. Available: {', '.join(sorted(BOT_REGISTRY.keys()))}")
    return BOT_REGISTRY[name]()


class BatchAnalyzer:
    """Aggregates batch simulation metrics and checks the 7 balance anomaly rules (07_tools.md §3.4)."""

    @staticmethod
    def percentile(sorted_vals: Sequence[float], p: float) -> float:
        if not sorted_vals:
            return 0.0
        n = len(sorted_vals)
        if n == 1:
            return sorted_vals[0]
        idx = (p / 100.0) * (n - 1)
        lo = int(math.floor(idx))
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac

    @staticmethod
    def summarize_bot(bot_name: str, results: Sequence[NightResult]) -> Dict[str, Any]:
        n = len(results)
        if n == 0:
            return {"bot": bot_name, "runs": 0}
        wins = sum(1 for r in results if r.outcome == NightOutcome.Survived)
        losses = sorted(float(r.losses.get("weightedStructureLossFrac", 0.0)) for r in results)
        costs = [float(r.ammo.get("defenseCostMusd", 0.0)) for r in results]
        ratios = [
            float(r.exchange["exchangeRatio"])
            for r in results
            if r.exchange.get("exchangeRatio") is not None
        ]
        grid_collapses = sum(1 for r in results if r.civil.get("gridCollapsed", False))
        units_lost = sum(len(r.losses.get("unitsDestroyed", [])) for r in results)

        return {
            "bot": bot_name,
            "runs": n,
            "winRate": wins / n,
            "avgWeightedLossFrac": sum(losses) / n,
            "lossFracP10": BatchAnalyzer.percentile(losses, 10.0),
            "lossFracP50": BatchAnalyzer.percentile(losses, 50.0),
            "lossFracP90": BatchAnalyzer.percentile(losses, 90.0),
            "avgDefenseCostMusd": sum(costs) / n,
            "avgExchangeRatio": (sum(ratios) / len(ratios)) if ratios else None,
            "gridCollapseRate": grid_collapses / n,
            "avgUnitsDestroyed": units_lost / n,
        }

    @staticmethod
    def detect_anomalies(summaries_by_bot: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
        """Evaluate the 7 balance anomaly rules defined in 07_tools.md §3.4."""
        anomalies: List[Dict[str, str]] = []
        default_s = summaries_by_bot.get("default")
        passive_s = summaries_by_bot.get("passive")
        always_s = summaries_by_bot.get("always_emit")
        never_s = summaries_by_bot.get("never_emit")
        blink_s = summaries_by_bot.get("smart_blink")
        hoarder_s = summaries_by_bot.get("hoarder")
        wasteful_s = summaries_by_bot.get("wasteful")

        if default_s and default_s.get("runs", 0) > 0:
            wr = float(default_s["winRate"])
            # 1. Trivial / Impossible baseline
            if wr < 0.20:
                anomalies.append({"code": "ANOM_TOO_HARD", "message": f"default bot winRate={wr:.2f} < 0.20"})
            if wr > 0.98 and float(default_s["avgWeightedLossFrac"]) < 0.02:
                anomalies.append({"code": "ANOM_TRIVIAL", "message": f"default bot winRate={wr:.2f} with <2% structure loss"})
            # 2. High variance / RNG cliff
            if float(default_s["lossFracP90"]) - float(default_s["lossFracP10"]) > 0.60:
                anomalies.append({"code": "ANOM_RNG_CLIFF", "message": "P90 - P10 weighted loss spread exceeds 0.60"})
            # 3. Grid collapse dominance
            if float(default_s["gridCollapseRate"]) > 0.80 and wr < 0.50:
                anomalies.append({"code": "ANOM_GRID_FRAGILE", "message": "Grid collapse occurs in >80% of runs"})

        # 4. Passive dominates active default
        if passive_s and default_s and passive_s.get("runs", 0) > 0 and default_s.get("runs", 0) > 0:
            if float(passive_s["winRate"]) > float(default_s["winRate"]) + 0.15:
                anomalies.append({"code": "ANOM_PASSIVE_DOMINATES", "message": "passive bot outperforms default bot by >15%"})

        # 5. Always-emit has no survival penalty vs smart_blink when ARM/Hunt present
        if always_s and blink_s and always_s.get("runs", 0) > 0 and blink_s.get("runs", 0) > 0:
            if float(always_s["avgUnitsDestroyed"]) < float(blink_s["avgUnitsDestroyed"]) - 0.5:
                anomalies.append({"code": "ANOM_EMCON_USELESS", "message": "always_emit loses fewer units than smart_blink"})

        # 6. Never-emit outperforms default
        if never_s and default_s and never_s.get("runs", 0) > 0 and default_s.get("runs", 0) > 0:
            if float(never_s["winRate"]) > float(default_s["winRate"]) + 0.10:
                anomalies.append({"code": "ANOM_RADAR_REDUNDANT", "message": "never_emit outperforms default bot"})

        # 7. Hoarder vs Wasteful exchange ratio inversion
        if hoarder_s and wasteful_s and hoarder_s.get("avgExchangeRatio") and wasteful_s.get("avgExchangeRatio"):
            if float(wasteful_s["avgExchangeRatio"]) > float(hoarder_s["avgExchangeRatio"]) * 1.5:
                anomalies.append({"code": "ANOM_ECONOMY_INVERTED", "message": "wasteful bot achieves >1.5x exchange ratio of hoarder"})

        return anomalies
