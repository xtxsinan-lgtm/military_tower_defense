"""End-to-end unit and HTTP integration tests for tools.webproto."""

from __future__ import annotations

import json
import threading
import unittest
from urllib.request import Request, urlopen

from tools.webproto.server import WebProtoServer, dispatch_api
from tools.webproto.session import GameSession


class WebProtoApiTests(unittest.TestCase):
    """Verify the full Night 1 -> Night 2 interactive API lifecycle."""

    def test_init_and_ridge_los_coverage_comparison(self) -> None:
        sess = GameSession()
        code, meta = dispatch_api("GET", "/api/init?level=test_01&night=1&seed=42&reset=1", session=sess)
        self.assertEqual(code, 200)
        self.assertEqual(meta["levelId"], "test_01")
        self.assertEqual(meta["nightIndex"], 1)
        self.assertEqual(len(meta["structures"]), 3)
        self.assertEqual(len(meta["currentPlacements"]), 16)
        self.assertEqual(len(meta["map"]["elevationGrid"]), 100)

        # Compare layered (radar north of ridge) vs stacked (radar behind ridge)
        _, cov_layered = dispatch_api(
            "POST",
            "/api/coverage",
            {"placements": meta["presets"]["layered"], "altM": 100.0, "gridRes": 48},
            session=sess,
        )
        _, cov_stacked = dispatch_api(
            "POST",
            "/api/coverage",
            {"placements": meta["presets"]["stacked"], "altM": 100.0, "gridRes": 48},
            session=sess,
        )
        self.assertGreater(cov_layered["stats"]["visibleFrac"], cov_stacked["stats"]["visibleFrac"])
        self.assertLess(cov_layered["stats"]["blindFrac"], cov_stacked["stats"]["blindFrac"])

    def test_live_commands_and_binary_choice_hard_pause(self) -> None:
        sess = GameSession()
        sess.init_level("test_01", night_index=1, seed=42, reset=True)
        _, snap = dispatch_api("POST", "/api/start_night", {"bot": "manual"}, session=sess)
        self.assertEqual(snap["tick"], 0)
        self.assertEqual(snap["cp"]["current"], 4)

        # Find a NASAMS unit (with fire control radar) and an IRIS-T SLS unit
        nasams = next(u for u in snap["units"] if u["unitDefId"] == "nasams")
        iris = next(u for u in snap["units"] if u["unitDefId"] == "iris_t_sls")
        wid = iris["weapons"][0]["weaponId"]

        # 1. Emission policy & BurstScan
        _, snap = dispatch_api(
            "POST",
            "/api/command",
            {"type": "SetEmissionPolicy", "unitId": nasams["id"], "policyId": "continuous"},
            session=sess,
        )
        self.assertTrue(snap["ok"])

        # 2. Weapon doctrine commands (rule, reserve, whitelist, shoot-look-shoot)
        _, snap = dispatch_api(
            "POST",
            "/api/command",
            {"type": "SetEngagementRule", "unitId": iris["id"], "weaponId": wid, "rule": "high_value_only"},
            session=sess,
        )
        self.assertTrue(snap["ok"])
        _, snap = dispatch_api(
            "POST",
            "/api/command",
            {"type": "SetAmmoReserve", "unitId": iris["id"], "weaponId": wid, "reserve": 2},
            session=sess,
        )
        self.assertTrue(snap["ok"])
        _, snap = dispatch_api(
            "POST",
            "/api/command",
            {"type": "SetTargetWhitelist", "unitId": iris["id"], "weaponId": wid, "tags": ["CM", "BM"]},
            session=sess,
        )
        self.assertTrue(snap["ok"])
        _, snap = dispatch_api(
            "POST",
            "/api/command",
            {"type": "SetShootLookShoot", "unitId": iris["id"], "weaponId": wid, "enabled": True},
            session=sess,
        )
        self.assertTrue(snap["ok"])

        # 3. Civil Alert (1 CP) & National Spoof (1 CP) -> 4 - 1(Emission) - 1(Alert) - 1(Spoof) = 1 CP
        _, snap = dispatch_api("POST", "/api/command", {"type": "ToggleCivilAlert", "on": True}, session=sess)
        self.assertTrue(snap["alert"]["on"])
        _, snap = dispatch_api("POST", "/api/command", {"type": "TriggerNationalSpoof"}, session=sess)
        self.assertEqual(snap["cp"]["current"], 1)

        # 4. Trigger C-T3-01 binary choice hard pause and answer Option A (shut down radar)
        _, snap = dispatch_api("POST", "/api/command", {"type": "TriggerArmChoiceDemo"}, session=sess)
        self.assertTrue(snap["hardPause"])
        self.assertIsNotNone(snap["activeChoice"])
        self.assertIsNotNone(snap["activeChoice"]["subjectUnitPos"])
        subj_id = snap["activeChoice"]["subjectUnitId"]
        cid = snap["activeChoice"]["choiceId"]
        _, snap = dispatch_api(
            "POST",
            "/api/command",
            {"type": "AnswerChoice", "choiceId": cid, "option": 0},
            session=sess,
        )
        self.assertIsNone(snap["activeChoice"])
        subj_unit = next(u for u in snap["units"] if u["id"] == subj_id)
        self.assertTrue(subj_unit["emitter"]["armSilenced"])

    def test_night1_to_night2_carryover_and_pre_night_relocation(self) -> None:
        sess = GameSession()
        meta1 = sess.init_level("test_01", night_index=1, seed=42, reset=True)
        dispatch_api(
            "POST",
            "/api/start_night",
            {"placements": meta1["presets"]["stacked"], "bot": "default"},
            session=sess,
        )
        assert sess.world is not None
        sess.world.ctx.duration_ticks = 2400
        _, snap_end = dispatch_api("POST", "/api/step", {"ticks": 2400}, session=sess)
        self.assertTrue(snap_end["isEnded"])
        self.assertIsNotNone(snap_end["battleReport"])
        self.assertIn(snap_end["battleReport"]["rating"], ("S", "A", "B", "C", "D", "F"))
        self.assertGreater(len(snap_end["carryOut"]["knownTargets"]), 0)
        expected_trust = max(0.0, min(100.0, 50.0 + float(snap_end["battleReport"]["trust"]["applied"])))

        # Advance to Night 2 and verify trustScore accumulated Night 1 trust delta
        _, meta2 = dispatch_api("POST", "/api/next_night", {}, session=sess)
        self.assertEqual(meta2["nightIndex"], 2)
        self.assertAlmostEqual(meta2["trustScore"], round(expected_trust, 1), places=1)
        self.assertTrue(meta2["carryIn"]["hasCarryIn"])
        kts = meta2["carryIn"]["knownTargets"]
        self.assertGreater(len(kts), 0)

        # Relocate all exposed units in Night 2 pre-night deployment to alternate positions >600m away
        alts = meta2["deploy"]["alternatePositions"]
        new_placements = meta2["currentPlacements"]
        relocated_roster_ids = set()
        for idx, u in enumerate(new_placements):
            if u.get("isExposed"):
                ap = alts[idx % len(alts)]
                u["pos"] = [ap["pos"][0], ap["pos"][1]]
                relocated_roster_ids.add(u["rosterId"])

        wdef_nasams = sess.level.catalog.weapons["nasams_missile"]
        orig_limit = wdef_nasams.get("perLevelLimit")
        try:
            wdef_nasams["perLevelLimit"] = 24
            _, snap_n2 = dispatch_api(
                "POST",
                "/api/start_night",
                {"placements": new_placements, "bot": "smart_blink"},
                session=sess,
            )
            # Verify that relocated units are no longer marked as knownTargets and their initial exposure is reset to 0.0!
            still_marked = [u for u in snap_n2["units"] if u["isKnownTarget"]]
            self.assertEqual(len(still_marked), 0)
            for u in snap_n2["units"]:
                if u["rosterId"] in relocated_roster_ids:
                    self.assertEqual(u["exposure"], 0.0)
            nasams_n2 = next(u for u in snap_n2["units"] if u["unitDefId"] == "nasams")
            self.assertEqual(nasams_n2["weapons"][0]["perLevelLimit"], 24)
            self.assertGreater(nasams_n2["weapons"][0]["perLevelUsed"], 0)
            self.assertEqual(
                nasams_n2["weapons"][0]["remainingQuota"],
                24 - nasams_n2["weapons"][0]["perLevelUsed"],
            )
        finally:
            if orig_limit is None:
                wdef_nasams.pop("perLevelLimit", None)
            else:
                wdef_nasams["perLevelLimit"] = orig_limit

    def test_http_server_endpoints(self) -> None:
        srv = WebProtoServer(("127.0.0.1", 0))
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            with urlopen(f"http://127.0.0.1:{port}/") as resp:
                html = resp.read().decode("utf-8")
                self.assertIn("《守夜》Nightwatch", html)
            with urlopen(f"http://127.0.0.1:{port}/api/init?level=test_01&night=1&reset=1") as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["levelId"], "test_01")
            req = Request(
                f"http://127.0.0.1:{port}/api/start_night",
                data=json.dumps({"bot": "smart_blink"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req) as resp:
                snap = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(snap["tick"], 0)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
