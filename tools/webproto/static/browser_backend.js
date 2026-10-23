// 《守夜》Nightwatch 浏览器端离线模拟适配层（支持本地 Python 服务与 GitHub Pages 纯静态部署双模式）
(function () {
  let backendMode = null; // "server" | "pyodide"
  let prebakedPromise = null;
  let pyodideReadyPromise = null;
  let pyodideInstance = null;
  let initialPrebakedUsed = false;

  function setEngineBadge(text, color) {
    let el = document.getElementById("engine-mode-badge");
    if (!el) {
      const brand = document.querySelector(".topbar-brand");
      if (!brand) return;
      el = document.createElement("span");
      el.id = "engine-mode-badge";
      el.className = "badge";
      brand.appendChild(el);
    }
    el.textContent = text;
    if (color) el.style.color = color;
  }

  async function detectBackendMode() {
    if (backendMode) return backendMode;
    if (location.hostname.endsWith("github.io") || location.protocol === "file:") {
      backendMode = "pyodide";
      ensurePyodideLoaded();
      return backendMode;
    }
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 800);
      const res = await fetch("/api/init?level=test_01&night=1&reset=0", { signal: ctrl.signal });
      clearTimeout(timer);
      const ctype = (res.headers.get("content-type") || "").toLowerCase();
      if (res.ok && ctype.includes("application/json")) {
        backendMode = "server";
        setEngineBadge("本地 Python 引擎", "#34d399");
        return backendMode;
      }
    } catch (_) {
      // Fallback to in-browser Pyodide WASM engine
    }
    backendMode = "pyodide";
    ensurePyodideLoaded();
    return backendMode;
  }

  function loadPrebaked() {
    if (!prebakedPromise) {
      prebakedPromise = fetch("prebaked_init.json").then((r) => r.json());
    }
    return prebakedPromise;
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = () => reject(new Error("Failed to load script: " + src));
      document.head.appendChild(s);
    });
  }

  function ensurePyodideLoaded() {
    if (pyodideReadyPromise) return pyodideReadyPromise;
    pyodideReadyPromise = (async () => {
      setEngineBadge("⏳ 正在加载 WASM 模拟核心...", "#fbbf24");
      const [bundle] = await Promise.all([
        fetch("py_bundle.json").then((r) => r.json()),
        typeof window.loadPyodide === "function"
          ? Promise.resolve()
          : loadScript("https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js"),
      ]);
      pyodideInstance = await window.loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/",
      });
      pyodideInstance.globals.set("__nw_bundle_json", JSON.stringify(bundle));
      await pyodideInstance.runPythonAsync(`
import base64, json, os, sys
from pathlib import Path

bundle = json.loads(__nw_bundle_json)
root = Path("/workspace")
for rel_path, item in bundle["files"].items():
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if item.get("encoding") == "base64":
        target.write_bytes(base64.b64decode(item["content"]))
    else:
        target.write_text(item["content"], encoding="utf-8")

if "/workspace" not in sys.path:
    sys.path.insert(0, "/workspace")

from tools.webproto.server import dispatch_api
from tools.webproto.session import SESSION_STORE

SESSION_STORE.init_level(level_id="test_01", night_index=1, seed=42, reset=True)

def __nw_dispatch(method_str, url_str, body_json_str):
    body = json.loads(body_json_str) if body_json_str else {}
    status, resp = dispatch_api(method_str, url_str, body, SESSION_STORE)
    return json.dumps(resp, ensure_ascii=False)
`);
      setEngineBadge("✓ WASM 离线引擎就绪", "#34d399");
      return pyodideInstance;
    })().catch((err) => {
      console.error("Pyodide init error:", err);
      setEngineBadge("⚠ 引擎加载失败", "#f87171");
      throw err;
    });
    return pyodideReadyPromise;
  }

  window.nightwatchApi = async function (method, url, data) {
    const mode = await detectBackendMode();
    if (mode === "server") {
      if (method === "GET") {
        return (await fetch(url)).json();
      }
      return (await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data || {}),
      })).json();
    }

    // Fast path for initial page render on GitHub Pages before Pyodide finishes loading
    if (!pyodideInstance && !initialPrebakedUsed) {
      try {
        const pre = await loadPrebaked();
        if (method === "GET" && url.startsWith("/api/init") && url.includes("night=1") && !url.includes("reset=1")) {
          return pre.init_n1;
        }
        if (method === "POST" && url === "/api/coverage") {
          initialPrebakedUsed = true;
          return pre.cov_n1;
        }
      } catch (_) {
        // Ignore and wait for Pyodide
      }
    }

    const py = await ensurePyodideLoaded();
    const fn = py.globals.get("__nw_dispatch");
    const rawJson = fn(method, url, JSON.stringify(data || {}));
    return JSON.parse(rawJson);
  };
})();
