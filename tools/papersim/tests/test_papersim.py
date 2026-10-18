"""Comprehensive unit, spec vector, and integration test suite for tools.papersim (D3)."""

from __future__ import annotations

import copy
import math
import struct
import subprocess
import sys
import unittest
import zlib

from tools.papersim.bots import BatchAnalyzer, create_bot
from tools.papersim.core import (
    FNV_OFFSET_BASIS,
    Geo,
    ScriptedRandom,
    SimError,
    SimRandom,
    SimTime,
    SpatialGrid,
    StateHasher,
    Vec2,
    fnv1a64,
    splitmix64_next,
)
from tools.papersim.enemy_ai import AvoidanceAStar, CommandStage, DeploymentStage
from tools.papersim.engagement import ImpactSystem, InterceptSolver, ScoringSystem
from tools.papersim.entities import (
    CarryIn,
    CommandRejectReason,
    DeploymentPlan,
    Entity,
    EntityKind,
    EntityStore,
    FireUnit,
    GridNode,
    IdAllocator,
    LauncherState,
    NightEndReason,
    NightOutcome,
    PathEndAction,
    PlacedUnit,
    SimCommand,
    SimCommandType,
    SimConfig,
    SimEventType,
    SimState,
    Structure,
    TargetTag,
    Threat,
    ThreatKind,
    ThreatPhase,
    TrackQuality,
    UnitDeployState,
    WeaponSlotState,
)
from tools.papersim.loader import (
    DataLoadException,
    DataLoader,
    FileSystemDataSource,
    InMemoryDataSource,
    Png16Decoder,
)
from tools.papersim.movement import ThreatKinematics, ThreatPath
from tools.papersim.sensing import SensingMath
from tools.papersim.terrain import Heightmap, TerrainModel, TerrainRules
from tools.papersim.world import ReplayRunner, SimSnapshot, SimWorld


class TestSpec00Core(unittest.TestCase):
    """Tests for 00_core.md: SimRandom PCG32, StateHasher, SimTime, Geo, SpatialGrid, EntityStore, DataLoader."""

    def test_simrandom_pcg32_vectors(self) -> None:
        # Exact vectors from tools/spec_calc/00/simrandom_vectors.py & 00_core.md §3.1
        self.assertEqual(fnv1a64(""), 0xCBF29CE484222325)
        self.assertEqual(fnv1a64("spawn"), 0x4328F78AB20E1F98)
        self.assertEqual(fnv1a64("intercept"), 0x708A838B1F6CE3B5)
        _, sm0 = splitmix64_next(0)
        self.assertEqual(sm0, 0xE220A8397B1DCDAF)

        rng = SimRandom(1)
        u32_5 = [rng.next_u32() for _ in range(5)]
        self.assertEqual(
            u32_5,
            [0x5249C5DC, 0x01959430, 0xE7976769, 0x57D21847, 0xEC099420],
        )

        rng_d = SimRandom(1)
        self.assertAlmostEqual(rng_d.next_double(), 0.3214381849407657, places=15)
        self.assertAlmostEqual(rng_d.next_double(), 0.9046539909539394, places=15)
        self.assertAlmostEqual(rng_d.next_double(), 0.922021158155058, places=15)

        rng42 = SimRandom(42)
        ints = [rng42.next_int(0, 10) for _ in range(10)]
        self.assertEqual(ints, [7, 5, 9, 6, 5, 9, 1, 8, 1, 7])

        self.assertEqual(SimRandom.child_seed(1, "spawn"), 0x247FD80E4FD86BD1)
        self.assertEqual(SimRandom.night_seed(1, "test_01", 1), 0x6DD180096484586D)
        self.assertEqual(SimRandom.parse_seed("42"), 42)
        self.assertEqual(SimRandom.parse_seed("0x2a"), 42)
        self.assertEqual(SimRandom.parse_seed("hello"), fnv1a64("hello"))

    def test_state_hasher_vectors(self) -> None:
        # Exact vectors from tools/spec_calc/00/hasher_vectors.py & 00_core.md §3.7.1
        h = StateHasher()
        self.assertEqual(h.value, 0xCBF29CE484222325)

        h_i32 = StateHasher()
        h_i32.write_i32(7)
        self.assertEqual(h_i32.value, 0x6D3572669B2CDE42)

        h_f64 = StateHasher()
        h_f64.write_f64(1.5)
        self.assertEqual(h_f64.value, 0xAA95E93229A27C80)

        h_neg0 = StateHasher()
        h_neg0.write_f64(-0.0)
        self.assertEqual(h_neg0.value, 0xA8C7F832281A39C5)
        h_pos0 = StateHasher()
        h_pos0.write_f64(0.0)
        self.assertEqual(h_neg0.value, h_pos0.value)

        h_null = StateHasher()
        h_null.write_str(None)
        self.assertEqual(h_null.value, 0x994F76653E2A3951)

        h_seq = StateHasher()
        h_seq.write_i32(7)
        h_seq.write_f64(1.5)
        h_seq.write_str("ab")
        h_seq.write_bool(True)
        h_seq.write_u64(0xDEADBEEF)
        self.assertEqual(h_seq.value, 0x461DC66E88FEC47B)

        with self.assertRaises(ValueError):
            h.write_f64(float("nan"))

    def test_simtime_and_geo(self) -> None:
        self.assertEqual(SimTime.to_world_seconds(2.5), 150.0)
        self.assertEqual(SimTime.sec_to_ticks_ceil(0.0), 0)
        self.assertEqual(SimTime.sec_to_ticks_ceil(0.1), 1)
        self.assertEqual(SimTime.sec_to_ticks_floor(2.9), 2)
        self.assertEqual(SimTime.parse_year_month("2022-11-15"), (2022, 11, 15))
        self.assertEqual(SimTime.parse_year_month("2025-08"), (2025, 8, 1))

        # Geo.first_entry_into_circle (00_core.md §0.4.6 & T-00-38)
        t_enter = Geo.first_entry_into_circle(Vec2(0.0, 0.0), Vec2(100.0, 0.0), Vec2(500.0, 0.0), 100.0)
        self.assertIsNotNone(t_enter)
        self.assertAlmostEqual(t_enter if t_enter is not None else -1.0, 4.0, places=9)
        t_inside = Geo.first_entry_into_circle(Vec2(450.0, 0.0), Vec2(100.0, 0.0), Vec2(500.0, 0.0), 100.0)
        self.assertIsNotNone(t_inside)
        self.assertAlmostEqual(t_inside if t_inside is not None else -1.0, 0.0, places=9)
        t_miss = Geo.first_entry_into_circle(Vec2(0.0, 200.0), Vec2(100.0, 0.0), Vec2(500.0, 0.0), 100.0)
        self.assertIsNone(t_miss)

        # Polygon & polyline
        poly = [Vec2(0.0, 0.0), Vec2(10.0, 0.0), Vec2(10.0, 10.0), Vec2(0.0, 10.0)]
        self.assertTrue(Geo.point_in_polygon(Vec2(5.0, 5.0), poly))
        self.assertFalse(Geo.point_in_polygon(Vec2(15.0, 5.0), poly))
        self.assertAlmostEqual(Geo.polyline_length([Vec2(0.0, 0.0), Vec2(3.0, 4.0)]), 5.0, places=9)
        pt, hdg = Geo.point_at_distance([Vec2(0.0, 0.0), Vec2(0.0, 10.0)], 4.0)
        self.assertAlmostEqual(pt.y, 4.0, places=9)
        self.assertAlmostEqual(hdg, 0.0, places=9)

        # Piecewise linear & initial stock
        pts = [(0.0, 10.0), (10.0, 20.0)]
        self.assertAlmostEqual(Geo.piecewise_linear(pts, 5.0), 15.0, places=9)
        self.assertEqual(Geo.compute_initial_stock(10, 12, "tight", {"tight": 0.75}), 7)

    def test_entity_store_and_spatial_grid(self) -> None:
        ids = IdAllocator(1)
        tick = 0
        store: EntityStore[Entity] = EntityStore(EntityKind.Threat, ids, lambda: tick)
        e1 = store.add(Entity(def_id="a", pos=Vec2(100.0, 100.0)))
        e2 = store.add(Entity(def_id="b", pos=Vec2(200.0, 200.0)))
        self.assertEqual(e1.id, 1)
        self.assertEqual(e2.id, 2)
        store.remove(1)
        self.assertIsNone(store.try_get(1))
        self.assertIsNotNone(store.try_get_including_removed(1))
        store.compact()
        self.assertEqual(len(store), 1)

        grid = SpatialGrid(10000.0, 10000.0)
        grid.rebuild([(1, Vec2(1000.0, 1000.0)), (2, Vec2(8000.0, 8000.0))])
        self.assertEqual(grid.query_circle(Vec2(1100.0, 1100.0), 500.0), [1])

    def test_png16_decoder_and_dataloader(self) -> None:
        # Build a 2x2 16-bit grayscale PNG in memory and decode
        raw_rows = b"\x00\x00\x00\xff\xff" + b"\x00\x80\x00\x40\x00"
        idat = zlib.compress(raw_rows)

        def chunk(ctype: bytes, data: bytes) -> bytes:
            crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
            return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)

        ihdr = struct.pack(">IIBBBBB", 2, 2, 16, 0, 0, 0, 0)
        png_bytes = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
        hm = Png16Decoder.decode(png_bytes, 100.0, 0.0, 65535.0, "test.png")
        self.assertEqual((hm.width_px, hm.height_px), (2, 2))
        self.assertAlmostEqual(hm.elevation_m[0], 0.0, places=5)
        self.assertAlmostEqual(hm.elevation_m[1], 65535.0, places=5)

        # Load real catalog and test_01
        src = FileSystemDataSource("data")
        lvl = DataLoader.load_level(src, "test_01", night_index=1)
        self.assertEqual(lvl.id, "test_01")
        self.assertTrue(lvl.data_hash.startswith("sha256:"))
        # Verify Gap 1: interceptor_drone.JET_UAV is absent before 2025-11
        ic_drone = lvl.catalog.rules["intercept"]["classes"]["interceptor_drone"]
        self.assertNotIn("JET_UAV", ic_drone)
        cat_2026 = DataLoader.load_catalog(src, "2026-01-01")
        self.assertAlmostEqual(cat_2026.rules["intercept"]["classes"]["interceptor_drone"]["JET_UAV"], 0.10)


class TestSpec01MovementAndTerrain(unittest.TestCase):
    """Tests for 01_spawn_movement_terrain.md: TerrainModel, HorizonProfile, ThreatKinematics."""

    def test_terrain_bilinear_los_and_horizon(self) -> None:
        elev = [
            10.0, 20.0, 30.0, 40.0,
            10.0, 120.0, 120.0, 40.0,
            10.0, 120.0, 120.0, 40.0,
            10.0, 20.0, 30.0, 40.0,
        ]
        hm = Heightmap(4, 4, 100.0, 10.0, 120.0, elev)
        tm = TerrainModel(hm, TerrainRules(los_sample_step_px=0.5, earth_radius_m=None))
        self.assertAlmostEqual(tm.elevation_at(50.0, 350.0), 10.0, places=9)
        self.assertAlmostEqual(tm.elevation_at(150.0, 250.0), 120.0, places=9)
        self.assertAlmostEqual(tm.elevation_at(100.0, 300.0), 40.0, places=9)
        self.assertAlmostEqual(tm.elevation_at(125.0, 275.0), 73.75, places=9)

        # Blocked by 120m ridge at (200, 200) when observer is at 35m MSL and target is at 50m MSL
        self.assertFalse(tm.has_line_of_sight(Vec2(200.0, 50.0), 35.0, Vec2(200.0, 350.0), 50.0))
        # Clear when observer and target are at 150m MSL above the 120m ridge
        self.assertTrue(tm.has_line_of_sight(Vec2(200.0, 50.0), 150.0, Vec2(200.0, 350.0), 150.0))

        hp = tm.build_horizon_profile(Vec2(200.0, 50.0), 10.0, 400.0)
        self.assertFalse(hp.has_line_of_sight(Vec2(200.0, 350.0), 50.0))
        self.assertTrue(hp.has_line_of_sight(Vec2(200.0, 350.0), 350.0))

    def test_threat_kinematics_profiles(self) -> None:
        th = Threat(
            pos=Vec2(0.0, 0.0),
            alt_m=1000.0,
            kind=ThreatKind.Munition,
            tag=TargetTag.CM,
            phase=ThreatPhase.Ingress,
            path_end=PathEndAction.Arrive,
            start_alt_m=1000.0,
            end_alt_m=0.0,
            terminal_start_arc_m=8000.0,
            speed_mps=200.0,
            terminal_speed_mps=400.0,
            anchor_sec=0.0,
            anchor_arc_m=0.0,
            last_update_sec=0.0,
            profile_ready=True,
        )
        ThreatPath.set_path(th, [Vec2(0.0, 0.0), Vec2(10000.0, 0.0)], bump_version=False)
        # 8000m @ 200m/s = 40s; 2000m @ 400m/s = 5s -> total 45s
        self.assertAlmostEqual(ThreatKinematics.predict_arrival_sec(th) or 0.0, 45.0, places=9)
        pose_mid = ThreatKinematics.predict(th, 42.5)
        self.assertAlmostEqual(pose_mid.pos.x, 9000.0, places=9)
        self.assertAlmostEqual(pose_mid.alt_m, 500.0, places=9)


class TestSpec020304Systems(unittest.TestCase):
    """Tests for 02, 03, 04 systems and reference calculation scripts."""

    def test_sensing_math_and_intercept_solver(self) -> None:
        # SensingMath.time_to_enter_radius
        tau = SensingMath.time_to_enter_radius(Vec2(1000.0, 0.0), Vec2(-50.0, 0.0), Vec2(0.0, 0.0), 500.0)
        self.assertAlmostEqual(tau or -1.0, 10.0, places=9)

        # InterceptSolver 3D bisection (03_engagement_impact_scoring.md §3.0.2)
        def pred(dt: float):
            return Vec2(6000.0 - 200.0 * dt, 0.0), 500.0, dt >= 30.0

        sol = InterceptSolver.solve(Vec2(0.0, 0.0), 800.0, 10000.0, 5000.0, pred, max_speed_3d=200.0)
        self.assertIsNotNone(sol)
        assert sol is not None
        # At dt, sqrt((6000 - 200*dt)^2 + 500^2) == 800 * dt
        dx = sol.pos.x
        dist3d = math.sqrt(dx * dx + sol.alt_m * sol.alt_m)
        self.assertAlmostEqual(dist3d, 800.0 * sol.dt_sec, places=5)

    def test_avoidance_astar(self) -> None:
        start_pt = Vec2(1000.0, 5000.0)
        goal_pt = Vec2(9000.0, 5000.0)
        sites = [(Vec2(5000.0, 5000.0), 1500.0)]
        turns = AvoidanceAStar.compute_turning_points(
            0.0,
            0.0,
            10000.0,
            10000.0,
            500.0,
            1600,
            sites,
            3000.0,
            1.0,
            lambda _p: 0.0,
            0.0,
            lambda _a, _b: True,
            start_pt,
            goal_pt,
        )
        self.assertGreaterEqual(len(turns), 1)

    def test_command_precondition_before_cp_deduction_A_2_17(self) -> None:
        # Verify A-2-17: invalid command rejects WITHOUT deducting Command Points
        src = FileSystemDataSource("data")
        lvl = DataLoader.load_level(src, "test_01", night_index=1)
        world = SimWorld.create(lvl, seed=1, config=SimConfig(night_index=1))
        initial_cp = world.state.commands.command_points
        # Issue RelocateUnit on nonexistent unit 99999
        world.submit_command(
            SimCommand(
                type=SimCommandType.RelocateUnit,
                effective_tick=1,
                params={"unitId": 99999, "alternatePositionId": "alt_north"},
            )
        )
        evs = world.step()
        rej_evs = [e for e in evs if e.type == SimEventType.CommandRejected]
        self.assertEqual(len(rej_evs), 1)
        self.assertEqual(rej_evs[0].data["reason"], CommandRejectReason.UnknownEntity)
        self.assertEqual(world.state.commands.command_points, initial_cp)

    def test_grid_bfs_power_propagation(self) -> None:
        src = FileSystemDataSource("data")
        lvl = DataLoader.load_level(src, "test_01", night_index=1)
        world = SimWorld.create(lvl, seed=1, config=SimConfig(night_index=1))
        self.assertFalse(world.state.grid.collapsed)
        # Destroy source node_tpp -> all downstream consumers lose power and grid collapses
        tpp_gid = world.state.grid_node_id_by_def_id["node_tpp"]
        world.state.grid_nodes.get(tpp_gid).destroyed = True
        ImpactSystem.recompute_grid(world.ctx, emit_events=True)
        self.assertTrue(world.state.grid.collapsed)
        self.assertAlmostEqual(world.state.grid.unpowered_consumer_frac, 1.0, places=9)

    def test_spec_calc_scripts_pass(self) -> None:
        scripts = [
            "tools/spec_calc/00/simrandom_vectors.py",
            "tools/spec_calc/00/hasher_vectors.py",
            "tools/spec_calc/01/01_terrain_calc.py",
            "tools/spec_calc/01/01_movement_calc.py",
            "tools/spec_calc/02/calc_02.py",
            "tools/spec_calc/03/calc_03.py",
            "tools/spec_calc/04/calc_04.py",
            "tools/spec_calc/06/calc_06.py",
            "tools/spec_calc/07/calc_07.py",
        ]
        for sc in scripts:
            proc = subprocess.run([sys.executable, sc], capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, msg=f"{sc} failed:\n{proc.stderr}")


class TestIntegrationTest01(unittest.TestCase):
    """End-to-end integration tests on test_01 Night 1 and Night 2, ReplayRunner, and SimSnapshot."""

    def test_test01_night1_and_night2_carryover_and_replay(self) -> None:
        src = FileSystemDataSource("data")
        lvl1 = DataLoader.load_level(src, "test_01", night_index=1)
        cfg1 = SimConfig(night_index=1, check_invariants=True)
        w1 = SimWorld.create(lvl1, seed=1, config=cfg1)

        # Take a snapshot at tick 1800 and verify snapshot restore determinism
        for _ in range(1800):
            w1.step()
        snap = SimSnapshot.capture(w1)

        res1 = w1.run_to_end()
        self.assertEqual(res1.outcome, NightOutcome.Survived)
        self.assertEqual(res1.end_reason, NightEndReason.AllClear)

        # Restore snapshot and run to end: must match final_state_hash bit-for-bit
        SimSnapshot.restore(w1, snap)
        res1_from_snap = w1.run_to_end()
        self.assertEqual(res1_from_snap.final_state_hash, res1.final_state_hash)

        # ReplayRunner from tick 0: must match final_state_hash bit-for-bit
        rep1 = ReplayRunner.run_replay(lvl1, seed=1, config=SimConfig(night_index=1), commands=[])
        self.assertEqual(rep1.final_state_hash, res1.final_state_hash)

        # Night 2 with CarryIn from Night 1 CarryOut
        co = res1.carry_out
        carry = CarryIn(
            units=co["units"],
            structures=co["structures"],
            ammo_pool=co["ammoPool"],
            per_level_used=co["perLevelUsed"],
            alert_responsiveness=co["alertResponsiveness"],
            known_targets=co["knownTargets"],
        )
        lvl2 = DataLoader.load_level(src, "test_01", night_index=2)
        w2 = SimWorld.create(lvl2, seed=1, config=SimConfig(night_index=2, carry_in=carry, check_invariants=True))
        bot = create_bot("default")
        res2 = w2.run_to_end(bot)
        self.assertIn(res2.outcome, (NightOutcome.Survived, NightOutcome.Defeated))
        # Verify su24m spawned and released kh59 in Night 2
        self.assertGreaterEqual(
            res2.exchange["killsByEnemy"].get("kh59", 0) + res2.exchange["leaksByEnemy"].get("kh59", 0),
            1,
        )

        # Verify BatchAnalyzer summary & anomaly detection
        summary = BatchAnalyzer.summarize_bot("default", [res1, res2])
        self.assertEqual(summary["runs"], 2)
        anomalies = BatchAnalyzer.detect_anomalies({"default": summary})
        self.assertIsInstance(anomalies, list)


if __name__ == "__main__":
    unittest.main()
