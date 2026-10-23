"""Build static GitHub Pages bundle (py_bundle.json + prebaked_init.json) for tools.webproto."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Dict

from tools.webproto.server import dispatch_api
from tools.webproto.session import GameSession

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"


def build_py_bundle() -> Dict[str, Dict[str, str]]:
    """Pack tools/papersim/*.py, tools/webproto/*.py, and data/**/* into a JSON bundle for Pyodide FS."""
    files: Dict[str, Dict[str, str]] = {}

    for pkg in ("tools/papersim", "tools/webproto"):
        pkg_dir = REPO_ROOT / pkg
        for p in sorted(pkg_dir.glob("*.py")):
            rel = p.relative_to(REPO_ROOT).as_posix()
            files[rel] = {"encoding": "utf-8", "content": p.read_text(encoding="utf-8")}

    # Ensure tools/__init__.py exists in virtual FS
    files["tools/__init__.py"] = {"encoding": "utf-8", "content": ""}

    data_dir = REPO_ROOT / "data"
    for p in sorted(data_dir.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        if p.suffix.lower() == ".json" or p.suffix.lower() == ".md":
            files[rel] = {"encoding": "utf-8", "content": p.read_text(encoding="utf-8")}
        else:
            files[rel] = {
                "encoding": "base64",
                "content": base64.b64encode(p.read_bytes()).decode("ascii"),
            }

    return {"version": 1, "files": files}


def build_prebaked_init() -> Dict[str, object]:
    """Precompute initial /api/init and /api/coverage for Night 1 so GitHub Pages renders in <100ms."""
    sess = GameSession()
    _, init_n1 = dispatch_api("GET", "/api/init?level=test_01&night=1&reset=1", None, sess)
    _, cov_n1 = dispatch_api(
        "POST",
        "/api/coverage",
        {"placements": init_n1.get("currentPlacements", []), "altM": 100, "gridRes": 56},
        sess,
    )
    return {
        "init_n1": init_n1,
        "cov_n1": cov_n1,
    }


def main() -> None:
    bundle = build_py_bundle()
    bundle_path = STATIC_DIR / "py_bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    prebaked = build_prebaked_init()
    prebaked_path = STATIC_DIR / "prebaked_init.json"
    prebaked_path.write_text(json.dumps(prebaked, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"[OK] Wrote {bundle_path.name} ({bundle_path.stat().st_size / 1024:.1f} KB, {len(bundle['files'])} files)")
    print(f"[OK] Wrote {prebaked_path.name} ({prebaked_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
