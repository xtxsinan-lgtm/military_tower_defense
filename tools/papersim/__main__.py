"""CLI entry point for tools.papersim (validate, run, batch, test) (07_tools.md §§3.2-3.4)."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
import sys
import unittest
from typing import Any, Dict, List

from .bots import BOT_REGISTRY, BatchAnalyzer, create_bot
from .entities import CarryIn, SimConfig
from .loader import DataLoadException, DataLoader, FileSystemDataSource
from .world import SimWorld


def _parse_seed_spec(spec: str) -> List[int]:
    """Parse seed count/range specification (e.g. '5', '1..5', '1,2,3')."""
    if ".." in spec:
        lo_s, hi_s = spec.split("..", 1)
        return list(range(int(lo_s), int(hi_s) + 1))
    if "-" in spec and not spec.startswith("-"):
        lo_s, hi_s = spec.split("-", 1)
        return list(range(int(lo_s), int(hi_s) + 1))
    if "," in spec:
        return [int(x.strip()) for x in spec.split(",") if x.strip()]
    n = int(spec)
    return list(range(1, n + 1))


def cmd_validate(args: argparse.Namespace) -> int:
    source = FileSystemDataSource(args.data)
    levels_dir = os.path.join(args.data, "levels")
    level_ids: List[str] = []
    if args.level:
        level_ids = [args.level]
    elif os.path.isdir(levels_dir):
        level_ids = sorted(
            d
            for d in os.listdir(levels_dir)
            if os.path.isdir(os.path.join(levels_dir, d))
            and os.path.isfile(os.path.join(levels_dir, d, "level.json"))
        )

    all_errors: List[Dict[str, str]] = []
    validated_levels: List[Dict[str, Any]] = []

    try:
        cat = DataLoader.load_catalog(source, "2022-11-15")
    except DataLoadException as exc:
        for e in exc.errors:
            all_errors.append(
                {"code": e.code, "file": e.file_path, "jsonPath": e.json_path, "message": e.message}
            )
        cat = None

    for lid in level_ids:
        try:
            lvl = DataLoader.load_level(source, lid)
            validated_levels.append(
                {
                    "id": lvl.id,
                    "dataHash": lvl.data_hash,
                    "files": len(lvl.loaded_files),
                    "provisionalCount": len(lvl.provisional_paths),
                }
            )
        except DataLoadException as exc:
            for e in exc.errors:
                all_errors.append(
                    {"code": e.code, "file": e.file_path, "jsonPath": e.json_path, "message": e.message}
                )

    report = {
        "ok": len(all_errors) == 0,
        "levels": validated_levels,
        "provisionalPaths": cat.provisional_paths if cat else [],
        "errors": all_errors,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if report["ok"]:
            print(f"[OK] Validated {len(validated_levels)} level(s): {[l['id'] for l in validated_levels]}")
            for l in validated_levels:
                print(f"  - {l['id']}: {l['dataHash']} ({l['files']} files, {l['provisionalCount']} provisional)")
        else:
            for e in all_errors:
                print(f"[{e['code']}] {e['file']} {e['jsonPath']}: {e['message']}", file=sys.stderr)
    return 0 if report["ok"] else 2


def cmd_run(args: argparse.Namespace) -> int:
    source = FileSystemDataSource(args.data)
    try:
        lvl = DataLoader.load_level(source, args.level, night_index=args.night)
    except DataLoadException as exc:
        for e in exc.errors:
            print(f"[{e.code}] {e.file_path} {e.json_path}: {e.message}", file=sys.stderr)
        return 2

    carry_in = CarryIn()
    if args.carry_in:
        with open(args.carry_in, "r", encoding="utf-8") as f:
            ci_doc = json.load(f)
        co = ci_doc.get("carry_out", ci_doc)
        carry_in = CarryIn(
            units=co.get("units", []),
            structures=co.get("structures", []),
            ammo_pool=co.get("ammoPool"),
            per_level_used=co.get("perLevelUsed", {}),
            alert_responsiveness=co.get("alertResponsiveness"),
            known_targets=co.get("knownTargets"),
        )

    cfg = SimConfig(
        night_index=args.night,
        carry_in=carry_in,
        check_invariants=not args.no_invariants,
    )
    world = SimWorld.create(lvl, seed=args.seed, config=cfg)
    bot = create_bot(args.bot)

    trace_f = open(args.trace, "w", encoding="utf-8") if args.trace else None
    try:
        if trace_f is not None:
            for ev in world.events.drain():
                trace_f.write(
                    json.dumps(
                        {"tick": ev.tick, "seq": ev.seq, "type": ev.type.name, "atSec": ev.at_sec, "data": _json_safe(ev.data)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        while not world.is_ended:
            for c in bot(world):
                world.submit_command(c)
            step_evs = world.step()
            if trace_f is not None:
                for ev in step_evs:
                    trace_f.write(
                        json.dumps(
                            {"tick": ev.tick, "seq": ev.seq, "type": ev.type.name, "atSec": ev.at_sec, "data": _json_safe(ev.data)},
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
    finally:
        if trace_f is not None:
            trace_f.close()

    res = world.build_result()
    out_dict = asdict(res)
    out_dict["outcome"] = res.outcome.name.lower()
    out_dict["end_reason"] = res.end_reason.name.lower()

    payload = json.dumps(out_dict, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
    else:
        print(payload)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    source = FileSystemDataSource(args.data)
    try:
        lvl = DataLoader.load_level(source, args.level, night_index=args.night)
    except DataLoadException as exc:
        for e in exc.errors:
            print(f"[{e.code}] {e.file_path} {e.json_path}: {e.message}", file=sys.stderr)
        return 2

    seeds = _parse_seed_spec(args.seeds)
    bot_names = [b.strip() for b in args.bots.split(",") if b.strip()]

    summaries: Dict[str, Dict[str, Any]] = {}
    for bname in bot_names:
        results = []
        for s in seeds:
            cfg = SimConfig(night_index=args.night, check_invariants=False)
            world = SimWorld.create(lvl, seed=s, config=cfg)
            bot = create_bot(bname)
            res = world.run_to_end(bot)
            results.append(res)
        summaries[bname] = BatchAnalyzer.summarize_bot(bname, results)

    anomalies = BatchAnalyzer.detect_anomalies(summaries)
    report = {
        "levelId": lvl.id,
        "nightIndex": args.night,
        "dataHash": lvl.data_hash,
        "seeds": seeds,
        "bots": summaries,
        "anomalies": anomalies,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
    else:
        print(payload)
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    tests_dir = os.path.join(os.path.dirname(__file__), "tests")
    suite = unittest.defaultTestLoader.discover(start_dir=tests_dir, pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def _json_safe(val: Any) -> Any:
    if hasattr(val, "x") and hasattr(val, "y"):
        return [val.x, val.y]
    if isinstance(val, dict):
        return {str(k): _json_safe(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_json_safe(x) for x in val]
    return val


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m tools.papersim", description="Nightwatch Paper Simulator (D3)")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_val = sub.add_parser("validate", help="Validate data/ catalog and levels")
    p_val.add_argument("--data", default="data", help="Path to data directory")
    p_val.add_argument("--level", default=None, help="Specific level ID to validate")
    p_val.add_argument("--json", action="store_true", help="Output JSON report")

    p_run = sub.add_parser("run", help="Run a single night headless")
    p_run.add_argument("--data", default="data", help="Path to data directory")
    p_run.add_argument("--level", required=True, help="Level ID (e.g. test_01)")
    p_run.add_argument("--night", type=int, default=1, help="Night index (1-based)")
    p_run.add_argument("--seed", default="1", help="RNG seed (int or string)")
    p_run.add_argument("--bot", default="passive", choices=sorted(BOT_REGISTRY.keys()), help="Tactical bot name")
    p_run.add_argument("--carry-in", default=None, help="Path to previous night JSON result or carry_out")
    p_run.add_argument("--trace", default=None, help="Path to write JSONL event trace")
    p_run.add_argument("--out", default=None, help="Path to write NightResult JSON")
    p_run.add_argument("--no-invariants", action="store_true", help="Disable per-tick invariant checks")

    p_bat = sub.add_parser("batch", help="Run batch balance simulations across seeds and bots")
    p_bat.add_argument("--data", default="data", help="Path to data directory")
    p_bat.add_argument("--level", required=True, help="Level ID (e.g. test_01)")
    p_bat.add_argument("--night", type=int, default=1, help="Night index (1-based)")
    p_bat.add_argument("--seeds", default="1..5", help="Seed count or range (e.g. '10' or '1..10')")
    p_bat.add_argument("--bots", default="passive,default", help="Comma-separated bot names")
    p_bat.add_argument("--out", default=None, help="Path to write batch JSON report")

    p_tst = sub.add_parser("test", help="Run papersim unit and integration test suite")
    p_tst.add_argument("-v", "--verbose", action="store_true", help="Verbose test output")

    args = parser.parse_args(argv)
    if args.subcommand == "validate":
        return cmd_validate(args)
    if args.subcommand == "run":
        return cmd_run(args)
    if args.subcommand == "batch":
        return cmd_batch(args)
    if args.subcommand == "test":
        return cmd_test(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
