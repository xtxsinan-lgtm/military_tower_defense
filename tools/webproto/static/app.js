// 《守夜》Nightwatch 网页纸上原型前端状态机与 API 交互逻辑
(function () {
  const state = {
    phase: "deploy", meta: null, placements: [], coverage: null, snapshot: null,
    selectedUnitKey: null, hoverUnitKey: null, draggingUnit: null, viewMode: "command", godView: false,
    losAltM: 100, speed: 0, stepBusy: false, fxList: [], choiceDeadlineMs: 0, choiceTimerId: null,
    ammoInitial: {}, lastRadio: "",
  };
  const canvas = document.getElementById("tactical-canvas");
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s === undefined || s === null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // 慢请求（如首次加载 WASM 引擎）时显示忙碌提示
  let busyCount = 0;
  async function withBusy(label, fn) {
    busyCount++;
    const t = setTimeout(() => { $("busy-text").textContent = label; $("busy-indicator").classList.remove("hidden"); }, 350);
    try { return await fn(); } finally {
      clearTimeout(t);
      if (--busyCount <= 0) { busyCount = 0; $("busy-indicator").classList.add("hidden"); }
    }
  }
  const rawGet = async (url) => window.nightwatchApi ? window.nightwatchApi("GET", url) : (await fetch(url)).json();
  const rawPost = async (url, data) => window.nightwatchApi ? window.nightwatchApi("POST", url, data) : (await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data || {}),
  })).json();
  const apiGet = (url, label) => withBusy(label || "正在载入模拟核心…", () => rawGet(url));
  const apiPost = (url, data, label) => withBusy(label || "正在计算…", () => rawPost(url, data));

  async function initGame(night = 1, reset = false) {
    setSpeed(0);
    applyLevelMeta(await apiGet(`/api/init?level=test_01&night=${night}&reset=${reset ? 1 : 0}`, "正在载入关卡与模拟核心…"));
    await refreshCoverage();
  }

  function applyLevelMeta(meta) {
    state.phase = "deploy"; state.meta = meta; state.snapshot = null; state.fxList = [];
    const catMap = {};
    (meta.unitCatalog || []).forEach((c) => { catMap[c.unitDefId] = c; });
    state.placements = (meta.currentPlacements || []).map((p) => {
      const c = catMap[p.unitDefId] || {};
      return Object.assign({}, p, {
        name: p.name || c.name || p.unitDefId, category: p.category || c.category || "fire",
        hasRadar: Boolean(c.hasRadar), mobility: p.mobility || c.mobility,
        detectionRangeM: c.radarRangeM || c.detectionRangeM || c.selfAcquisitionRangeM || 0,
        weapons: c.weapons || [],
      });
    });
    state.selectedUnitKey = state.placements.length ? state.placements[0].rosterId : null;
    state.ammoInitial = Object.assign({}, (meta.carryIn && meta.carryIn.ammoPool) || {});
    $("level-title").textContent = meta.levelName;
    $("level-title").title = meta.briefing || "";
    $("night-badge").textContent = `第 ${meta.nightIndex} 夜 / 共 ${meta.totalNights} 夜`;
    setPhaseBadge("deploy");
    $("date-weather-badge").textContent = `${meta.date} · ${meta.weather === "clear" ? "晴" : meta.weather}`;
    $("trust-badge").textContent = `${meta.trustScore}`;
    $("world-clock").textContent = "22:00:00";
    $("tick-readout").textContent = "战前准备阶段";
    $("clock-progress").style.width = "0%";
    setCp(meta.commandPointsPerNight, meta.commandPointsPerNight);
    $("deploy-controls-section").classList.remove("hidden");
    $("report-modal").classList.add("hidden");
    $("choice-modal").classList.add("hidden");
    setRadio(meta.nightIndex > 1
      ? "第 2 夜战前部署：昨夜高暴露阵地已被敌方标定，建议转移后再开战。"
      : "战前部署阶段：拖拽地图上的防空单位调整阵地，观察北山脊对 100m 低空雷达通视扇面的遮挡。");
    const logBox = $("event-log-list");
    logBox.innerHTML = '<div class="log-empty">开战后，雷达接触、拦截与命中事件将在此滚动显示。</div>';

    const kts = (meta.carryIn && meta.carryIn.knownTargets) || [];
    const warnBox = $("exposed-warning-box");
    if (kts.length > 0) {
      warnBox.classList.remove("hidden");
      $("exposed-warning-desc").textContent =
        `敌方侦察已标定昨夜暴露阵地：${kts.map((k) => `${k.name}(#${k.rosterId})`).join("、")}。今夜 03:30 (第5波) 将发射巡航导弹猎杀原坐标！请立即移至预备阵地。`;
    } else warnBox.classList.add("hidden");
    renderIntelList(); renderStructuresAndAmmo(); renderRosterAndInspector();
  }

  function setPhaseBadge(phase) {
    const el = $("phase-badge");
    if (phase === "battle") { el.textContent = "夜间防空实战"; el.className = "chip chip-red"; }
    else { el.textContent = "战前部署"; el.className = "chip chip-amber"; }
  }

  function setCp(cur, init) {
    $("cp-badge").textContent = `${cur} / ${init}`;
    $("cp-pips").innerHTML = Array.from({ length: init }, (_, i) => `<i class="${i < cur ? "on" : ""}"></i>`).join("");
  }

  function setRadio(text) {
    if (!text || text === state.lastRadio) return;
    state.lastRadio = text;
    $("radio-text").textContent = text;
    const b = $("radio-banner");
    b.classList.remove("flash"); void b.offsetWidth; b.classList.add("flash");
  }

  async function refreshCoverage() {
    if (!state.meta) return;
    const list = state.phase === "deploy" ? state.placements : (state.snapshot ? state.snapshot.units : []);
    const cov = await apiPost("/api/coverage", { placements: list, altM: state.losAltM || 100, gridRes: 56 }, "正在计算雷达通视…");
    state.coverage = cov;
    const vis = cov.stats.visibleFrac * 100, blind = cov.stats.blindFrac * 100;
    $("cov-vis-pct").textContent = `${vis.toFixed(1)}%`;
    $("cov-blind-pct").textContent = `${blind.toFixed(1)}%`;
    $("cov-vis-meter").style.width = `${Math.min(100, vis)}%`;
    $("cov-blind-meter").style.width = `${Math.min(100, blind * 4)}%`;
    const vBadge = $("validation-badge"), errBox = $("validation-errors");
    if (cov.valid) {
      vBadge.textContent = "部署合法"; vBadge.className = "badge badge-ok"; errBox.classList.add("hidden");
    } else {
      vBadge.textContent = `${cov.errors.length} 处冲突`; vBadge.className = "badge badge-err";
      errBox.classList.remove("hidden"); errBox.textContent = cov.errors.slice(0, 2).join("；");
    }
  }

  function renderIntelList() {
    const items = (state.meta && state.meta.intel) || [];
    $("intel-count-badge").textContent = `${items.length} 条`;
    $("intel-list").innerHTML = items.map((it) => `
      <div class="intel-item ${it.accurate ? "" : "inaccurate"}">
        <div class="intel-meta">
          <span>${esc(it.relatedWave || "全夜")}</span>
          <span class="${it.confidence === "confirmed" ? "intel-conf-ok" : "intel-conf-rumor"}">${it.confidence === "confirmed" ? "✓ 高可信通报" : "⚠ 研判估计"}</span>
        </div><div>${esc(it.text)}</div>
      </div>`).join("");
  }

  const AMMO_LABELS = { iris_t_slm_missile: "IRIS-T 导弹", amraam_nasams: "NASAMS 导弹", igla_manpads: "针式便携弹", heavy_mg_12_7: "高机弹药" };

  function renderStructuresAndAmmo() {
    const snap = state.snapshot;
    const structs = (snap && snap.structures) || (state.meta && state.meta.structures) || [];
    $("structures-list").innerHTML = structs.map((s) => {
      const frac = Math.max(0, Math.min(1, s.hp / Math.max(1, s.maxHp)));
      const col = frac > 0.5 ? "var(--green)" : (frac > 0.2 ? "var(--amber)" : "var(--red)");
      const pwr = s.destroyed ? '<span class="badge badge-err">已摧毁</span>'
        : (s.powered === false ? '<span class="badge badge-err">断电</span>' : '<span class="badge badge-ok">供电</span>');
      return `<div class="struct-item ${s.destroyed ? "destroyed" : ""}">
        <div class="struct-row">
          <span class="struct-name"><span class="struct-glyph">${esc((s.name || "?").slice(0, 1))}</span>${esc(s.name)}</span>
          <span class="struct-hp">${s.hp}/${s.maxHp} ${pwr}</span>
        </div>
        <div class="hp-bar-wrap"><div class="hp-bar-fill" style="width:${frac * 100}%;background:${col}"></div></div></div>`;
    }).join("");
    const gBadge = $("grid-status-badge");
    if (snap && snap.grid) {
      const unp = Math.round((snap.grid.unpoweredFrac || 0) * 100);
      gBadge.textContent = snap.grid.collapsed ? `电网崩溃 · 断电 ${unp}%` : (unp > 0 ? `局部断电 ${unp}%` : "电网正常");
      gBadge.className = `badge ${snap.grid.collapsed ? "badge-err" : (unp > 0 ? "badge-warn" : "badge-ok")}`;
    } else { gBadge.textContent = "电网正常"; gBadge.className = "badge badge-ok"; }
    const pool = (snap && snap.ammoPool) || (state.meta && state.meta.carryIn && state.meta.carryIn.ammoPool) || {};
    const entries = Object.keys(pool).length ? Object.entries(pool) : [["iris_t_slm_missile", 16], ["amraam_nasams", 18], ["igla_manpads", 16], ["heavy_mg_12_7", 99999]];
    $("ammo-pool-list").innerHTML = entries.map(([k, v]) => {
      const inf = typeof v !== "number" || v > 90000;
      if (!inf && (state.ammoInitial[k] === undefined || v > state.ammoInitial[k])) state.ammoInitial[k] = v;
      const init = state.ammoInitial[k] || 1;
      const frac = inf ? 1 : Math.max(0, Math.min(1, v / init));
      return `<div class="ammo-cell">
        <div class="ammo-top"><span>${esc(AMMO_LABELS[k] || k)}</span><strong class="${!inf && frac < 0.25 ? "low" : ""}">${inf ? "充足" : v}</strong></div>
        <div class="ammo-meter"><i style="width:${frac * 100}%"></i></div></div>`;
    }).join("");
  }

  const getActiveUnits = () => state.phase === "deploy" ? state.placements : ((state.snapshot && state.snapshot.units) || []);
  const CAT_ORDER = ["fire", "sensor", "ew", "deception"];
  const CAT_NAMES = { fire: "火力单元", sensor: "探测 / 观察", ew: "电子战", deception: "欺骗 / 诱饵" };
  const STATE_NAMES = {
    ACTIVE: "就绪", Deployed: "就绪", Moving: "机动中", Packing: "撤收中", Packed: "已撤收",
    Deploying: "展开中", Destroyed: "被毁", Suppressed: "压制",
  };
  const isActiveState = (s) => !s || s === "ACTIVE" || s === "Deployed" || s === "PRE-NIGHT";

  function renderRosterAndInspector() {
    const units = getActiveUnits();
    $("roster-count-badge").textContent = `${units.length} 单位`;
    const rBox = $("unit-roster-list");
    const scrollTop = rBox.scrollTop;
    const groups = {};
    units.forEach((u) => { const c = u.category || "fire"; (groups[c] = groups[c] || []).push(u); });
    const cats = CAT_ORDER.filter((c) => groups[c]).concat(Object.keys(groups).filter((c) => !CAT_ORDER.includes(c)));
    rBox.innerHTML = cats.map((cat) => `<div class="roster-group">${CAT_NAMES[cat] || cat} · ${groups[cat].length}</div>` + groups[cat].map((u) => {
      const key = u.id || u.rosterId, sel = key === state.selectedUnitKey ? "selected" : "";
      const expV = u.exposure !== undefined ? u.exposure : (u.carryExposure || 0);
      const expFlag = u.isExposed || u.isKnownTarget || expV >= 70 ? "exposed" : "";
      const isArmSilenced = Boolean(u.emitter && u.emitter.armSilenced);
      const em = isArmSilenced ? '<span class="em-arm">🔇 静默规避</span>'
        : (u.emitter ? (u.emitter.on ? '<span class="em-on">◉ 开机</span>' : '<span>○ 静默</span>') : "");
      const w0 = (u.weapons && u.weapons[0] && u.weapons[0].rounds !== undefined) ? (u.weapons[0].rounds >= 0 ? `弹${u.weapons[0].rounds}` : "") : "";
      const expTxt = expV > 0 ? `<span class="${expV >= 70 ? "exp-hi" : (expV >= 35 ? "exp-mid" : "")}">暴${Math.round(expV)}%</span>` : "";
      const st = u.deployState ? (STATE_NAMES[u.deployState] || u.deployState) : "";
      const inactive = u.deployState && !["ACTIVE", "Deployed"].includes(u.deployState);
      return `<div class="roster-item ${sel} ${expFlag}" data-ukey="${key}">
        <i class="roster-pip cat-${esc(u.category || "fire")} ${inactive ? "inactive" : ""}"></i>
        <div class="roster-name"><span class="rid">#${u.rosterId}</span><strong>${esc(u.name)}</strong>${st && st !== "就绪" ? `<span class="rstate">${esc(st)}</span>` : ""}</div>
        <div class="roster-meta">${em}${w0 ? `<span>${w0}</span>` : ""}${expTxt}</div></div>`;
    }).join("")).join("");
    rBox.scrollTop = scrollTop;
    rBox.querySelectorAll(".roster-item").forEach((el) => {
      el.addEventListener("click", () => { state.selectedUnitKey = Number(el.dataset.ukey); renderRosterAndInspector(); });
    });
    renderInspector(units.find((u) => (u.id || u.rosterId) === state.selectedUnitKey));
  }

  function renderInspector(u) {
    const body = $("insp-body");
    // 若焦点在检视器内的控件上（如正在拖动滑条），跳过重建以免打断操作
    if (body.contains(document.activeElement) && document.activeElement.tagName !== "BUTTON" && body.dataset.ukey === String(u && (u.id || u.rosterId))) return;
    body.dataset.ukey = String(u ? (u.id || u.rosterId) : "");
    if (!u) {
      $("insp-unit-title").textContent = "选中单位检视";
      $("insp-unit-state").textContent = "—";
      body.innerHTML = '<div class="empty-hint">点击地图或列表中的防空单位进行检视与指挥。</div>';
      return;
    }
    $("insp-unit-title").textContent = `#${u.rosterId} ${u.name}`;
    const st = u.deployState || "PRE-NIGHT";
    const stEl = $("insp-unit-state");
    stEl.textContent = STATE_NAMES[st] || (st === "PRE-NIGHT" ? "战前" : st);
    stEl.className = `badge ${isActiveState(st) ? "badge-ok" : (st === "Destroyed" ? "badge-err" : "badge-info")}`;
    const exp = Math.round(u.exposure !== undefined ? u.exposure : (u.carryExposure || 0));
    const alts = ((state.meta && state.meta.deploy && state.meta.deploy.alternatePositions) || []);
    const altOpts = alts.map((a) => `<option value="${esc(a.id)}">${esc(a.id)} (${Math.round(a.pos[0])}, ${Math.round(a.pos[1])})</option>`).join("");
    const curPol = u.emitter ? u.emitter.policyId : (u.emissionPolicy || "blink");
    const isArmSilenced = Boolean(u.emitter && u.emitter.armSilenced);
    const expCol = exp >= 70 ? "#f87171" : (exp >= 35 ? "#fcd38a" : "#5eead4");

    let html = `
      <div class="insp-stats">
        <div class="insp-stat"><span class="k">坐标 km</span><span class="v">${(u.pos[0] / 1000).toFixed(1)}, ${(u.pos[1] / 1000).toFixed(1)}</span></div>
        <div class="insp-stat"><span class="k">今夜击落</span><span class="v">${u.killsTonight || 0}</span></div>
        <div class="insp-stat"><span class="k">暴露度</span><span class="v" style="color:${expCol}">${exp}%</span></div>
      </div>
      <div class="exp-bar-wrap" title="≥70% 将被敌方跨夜标定"><div class="exp-bar-fill" style="width:${Math.min(100, exp)}%"></div></div>`;

    if (isArmSilenced) html += `<div class="insp-alert">🔇 规避静默中 — 危机解除后请手动切回闪烁 / 常开</div>`;

    if ((u.emitter && u.emitter.hasEmitter) || u.hasRadar || u.unitDefId === "soviet_mid_range_radar" || u.unitDefId === "nasams") {
      html += `<div class="insp-row">
        <span class="insp-label">雷达策略</span>
        <div style="display:flex;gap:6px;align-items:center;">
          <select id="insp-sel-policy" class="select-sm">
            <option value="silent" ${curPol === "silent" ? "selected" : ""}>静默 Silent</option>
            <option value="blink" ${curPol === "blink" ? "selected" : ""}>闪烁 Blink</option>
            <option value="continuous" ${curPol === "continuous" ? "selected" : ""}>常开 On</option>
          </select>
          ${state.phase === "battle" ? `<button id="insp-btn-burst" class="btn btn-xs btn-warn">短促扫描</button>` : ""}
        </div>
      </div>`;
    }

    if (u.mobility !== "fixed" && alts.length > 0) {
      html += `<div class="insp-row">
        <select id="insp-sel-alt" class="select-sm flex-1">${altOpts}</select>
        <button id="insp-btn-reloc" class="btn btn-xs btn-primary">${state.phase === "deploy" ? "战前移位" : "机动转移 · 1 CP"}</button>
      </div>`;
    }

    const carryUsedMap = (state.meta && state.meta.carryIn && state.meta.carryIn.perLevelUsed) || {};
    (u.weapons || []).forEach((w) => {
      const wid = w.weaponId || w.id;
      const wl = w.whitelist || ["UAV", "CM", "BM", "AC_LOW"];
      const rds = w.rounds !== undefined ? (w.rounds < 0 ? "充足" : `${w.rounds}/${w.maxRounds}`) : (w.magazine || "充足");
      const plLim = w.perLevelLimit !== undefined && w.perLevelLimit !== null ? Number(w.perLevelLimit) : null;
      let quotaHtml = "";
      if (plLim !== null) {
        const remQ = w.remainingQuota !== undefined && w.remainingQuota !== null
          ? Number(w.remainingQuota)
          : Math.max(0, plLim - Number(carryUsedMap[wid] || 0));
        quotaHtml = `<div class="insp-row" style="font-size:11px;color:${remQ <= 0 ? "#f87171" : "#93c5fd"};">
          <span>本关剩余配额 <strong>${remQ}/${plLim}</strong> ${remQ <= 0 ? "· 配额已尽" : ""}</span>
        </div>`;
      }
      html += `<div class="weapon-box">
        <div class="insp-row"><span class="weapon-name">${esc(w.name)}</span><span class="weapon-ammo">弹 ${rds}${w.reloadRemSec > 0 ? ` · 装填 ${w.reloadRemSec}s` : ""}${w.rangeM ? ` · ${(w.rangeM / 1000).toFixed(1)}km` : ""}</span></div>
        ${quotaHtml}
        <div class="insp-row"><span class="insp-label">射击规则</span>
          <select class="select-sm insp-w-rule" data-wid="${esc(wid)}">
            <option value="any" ${w.rule === "any" ? "selected" : ""}>自由迎击</option>
            <option value="high_value_only" ${w.rule === "high_value_only" ? "selected" : ""}>仅限高价值</option>
            <option value="ballistic_only" ${w.rule === "ballistic_only" ? "selected" : ""}>仅限弹道导弹</option>
            <option value="hold_fire" ${w.rule === "hold_fire" ? "selected" : ""}>停火</option>
          </select>
        </div>
        <div class="insp-row"><span class="insp-label">保留弹数 <strong id="lbl-res-${esc(wid)}" style="color:#e2e8f0;font-family:var(--font-mono)">${w.ammoReserve || 0}</strong></span>
          <input type="range" min="0" max="4" value="${w.ammoReserve || 0}" class="insp-w-res" data-wid="${esc(wid)}" />
        </div>
        <div class="tag-checks">
          ${["UAV", "CM", "BM", "AC_LOW"].map((tg) => `<label><input type="checkbox" class="insp-w-tag" data-wid="${esc(wid)}" value="${tg}" ${wl.includes(tg) ? "checked" : ""}/>${tg}</label>`).join("")}
          <label><input type="checkbox" class="insp-w-sls" data-wid="${esc(wid)}" ${w.shootLookShoot !== false ? "checked" : ""}/>1+1 教范</label>
        </div>
      </div>`;
    });
    body.innerHTML = html;
    bindInspectorEvents(u);
  }

  function bindInspectorEvents(u) {
    const polEl = $("insp-sel-policy");
    if (polEl) {
      polEl.addEventListener("change", async () => {
        if (state.phase === "deploy") { u.emissionPolicy = polEl.value; await refreshCoverage(); }
        else await sendCommand({ type: "SetEmissionPolicy", unitId: u.id, policyId: polEl.value });
        polEl.blur();
      });
    }
    const burstBtn = $("insp-btn-burst");
    if (burstBtn) burstBtn.addEventListener("click", () => sendCommand({ type: "BurstScan", unitId: u.id, durationSec: 15 }));
    const relocBtn = $("insp-btn-reloc");
    if (relocBtn) {
      relocBtn.addEventListener("click", async () => {
        const altId = $("insp-sel-alt").value;
        const ap = (state.meta.deploy.alternatePositions || []).find((a) => a.id === altId);
        if (!ap) return;
        if (state.phase === "deploy") {
          u.pos = [ap.pos[0], ap.pos[1]];
          u.isExposed = false;
          u.carryExposure = 0;
          await refreshCoverage();
          renderRosterAndInspector();
        } else await sendCommand({ type: "Relocate", unitId: u.id, alternatePositionId: altId });
      });
    }
    document.querySelectorAll(".insp-w-rule").forEach((el) => {
      el.addEventListener("change", () => { sendCommand({ type: "SetEngagementRule", unitId: u.id, weaponId: el.dataset.wid, rule: el.value }); el.blur(); });
    });
    document.querySelectorAll(".insp-w-res").forEach((el) => {
      el.addEventListener("input", () => {
        $(`lbl-res-${el.dataset.wid}`).textContent = el.value;
        sendCommand({ type: "SetAmmoReserve", unitId: u.id, weaponId: el.dataset.wid, reserve: Number(el.value) });
      });
      el.addEventListener("change", () => el.blur());
    });
    document.querySelectorAll(".insp-w-tag").forEach((el) => {
      el.addEventListener("change", () => {
        const wid = el.dataset.wid;
        const tags = Array.from(document.querySelectorAll(`.insp-w-tag[data-wid="${wid}"]:checked`)).map((c) => c.value);
        sendCommand({ type: "SetTargetWhitelist", unitId: u.id, weaponId: wid, tags });
        el.blur();
      });
    });
    document.querySelectorAll(".insp-w-sls").forEach((el) => {
      el.addEventListener("change", () => { sendCommand({ type: "SetShootLookShoot", unitId: u.id, weaponId: el.dataset.wid, enabled: el.checked }); el.blur(); });
    });
  }

  async function sendCommand(payload) {
    if (state.phase !== "battle") return;
    const snap = await rawPost("/api/command", payload);
    if (snap && snap.tick !== undefined) applySnapshot(snap);
  }

  function applySnapshot(snap) {
    state.snapshot = snap;
    $("world-clock").textContent = snap.clockStr;
    const pct = Math.min(100, (snap.timeWorldSec / Math.max(1, snap.durationWorldSec)) * 100);
    $("clock-progress").style.width = `${pct.toFixed(1)}%`;
    $("tick-readout").textContent = `T+${Math.round(snap.timeWorldSec)}s · ${pct.toFixed(0)}%`;
    setCp(snap.cp.current, snap.cp.initial);

    const alBtn = $("btn-alert-toggle");
    const shPct = Math.round((snap.alert.shelteredFrac || 0) * 100);
    alBtn.textContent = `民防警报：${snap.alert.on ? "拉响中" : "关闭"} (掩蔽 ${shPct}%)`;
    alBtn.className = `btn btn-sm ${snap.alert.on ? "btn-alert-on" : ""}`;
    if (snap.radioBanner) setRadio(snap.radioBanner);

    const logBox = $("event-log-list");
    if ((snap.events || []).length) {
      const empty = logBox.querySelector(".log-empty");
      if (empty) empty.remove();
    }
    (snap.events || []).forEach((ev) => {
      const div = document.createElement("div");
      div.className = `log-entry level-${ev.level || "info"}`;
      const t = document.createElement("span"); t.className = "log-time"; t.textContent = ev.clock || "";
      const x = document.createElement("span"); x.className = "log-text"; x.textContent = ev.text;
      div.appendChild(t); div.appendChild(x);
      logBox.prepend(div);
      if (ev.fx && ev.fx.pos) state.fxList.push({ kind: ev.fx.kind, pos: ev.fx.pos, t0: performance.now() });
    });
    while (logBox.children.length > 90) logBox.removeChild(logBox.lastChild);

    renderStructuresAndAmmo();
    renderRosterAndInspector();

    if (snap.activeChoice) { setSpeed(0); showChoiceModal(snap.activeChoice); }
    else hideChoiceModal();

    if (snap.isEnded && snap.battleReport) { setSpeed(0); showReportModal(snap.battleReport); }
  }

  function showChoiceModal(ch) {
    const modal = $("choice-modal");
    if (!modal.classList.contains("hidden")) return;
    modal.classList.remove("hidden");
    $("choice-title").textContent = ch.title;
    const posStr = ch.subjectUnitPos ? ` (坐标: ${Math.round(ch.subjectUnitPos[0])}m, ${Math.round(ch.subjectUnitPos[1])}m)` : "";
    $("choice-unit-subtitle").textContent = `被锁定雷达：${ch.subjectUnitName}${posStr}`;
    $("choice-opt-a-text").textContent = ch.optionA;
    $("choice-opt-b-text").textContent = ch.optionB;
    const durMs = (ch.timeoutRealSec || 8.0) * 1000;
    state.choiceDeadlineMs = performance.now() + durMs;

    const tickTimer = async () => {
      if (modal.classList.contains("hidden")) return;
      const rem = Math.max(0, state.choiceDeadlineMs - performance.now());
      $("choice-timer-text").textContent = `剩余 ${(rem / 1000).toFixed(1)} 秒`;
      $("choice-timer-bar").style.width = `${(rem / durMs) * 100}%`;
      if (rem <= 0) await answerChoice(ch.choiceId, ch.defaultOption || 0);
      else state.choiceTimerId = requestAnimationFrame(tickTimer);
    };
    state.choiceTimerId = requestAnimationFrame(tickTimer);
    $("btn-choice-a").onclick = () => answerChoice(ch.choiceId, 0);
    $("btn-choice-b").onclick = () => answerChoice(ch.choiceId, 1);
  }

  function hideChoiceModal() {
    $("choice-modal").classList.add("hidden");
    if (state.choiceTimerId) cancelAnimationFrame(state.choiceTimerId);
  }

  async function answerChoice(choiceId, option) {
    hideChoiceModal();
    await sendCommand({ type: "AnswerChoice", choiceId, option });
    setSpeed(1);
  }

  function showReportModal(rep) {
    $("report-modal").classList.remove("hidden");
    $("report-title").textContent = `第 ${rep.nightIndex} 夜 防空作战总结`;
    const rEl = $("report-rating");
    rEl.textContent = rep.rating;
    rEl.className = `rating-letter grade-${String(rep.rating).charAt(0)}`;
    $("report-score").textContent = `${rep.compositeScore} 分`;
    const isLast = rep.nightIndex >= ((state.meta && state.meta.totalNights) || 2);
    $("btn-next-night").classList.toggle("hidden", isLast);
    const rows = (rep.byEnemyType || []).map((r) =>
      `<tr><td>${esc(r.name)}</td><td>${r.spawned}</td><td>${r.intercepted} <span style="color:var(--text-muted)">(${r.interceptRate}%)</span><span class="rate-bar"><i style="width:${Math.min(100, r.interceptRate)}%"></i></span></td><td style="color:${r.penetrated > 0 ? "#fca5a5" : "inherit"}">${r.penetrated}</td></tr>`).join("");
    const exposed = rep.exposedPositions || [];
    const kts = exposed.map((k) => `${esc(k.name)}(#${k.rosterId}, 暴露 ${k.exposure}%)`).join("、") || "无（全员隐蔽良好）";
    $("report-body").innerHTML = `
      <div class="report-grid">
        <div class="stat-card"><div class="lbl">保卫加权损失率</div><div class="val">${rep.weightedLossPercent}%</div></div>
        <div class="stat-card"><div class="lbl">总拦截率</div><div class="val">${rep.summary.interceptRatePercent}% <span style="font-size:11px;color:var(--text-muted)">${rep.summary.totalIntercepted}/${rep.summary.totalSpawned}</span></div></div>
        <div class="stat-card"><div class="lbl">弹药效费比 (耗弹 / 毁伤)</div><div class="val">$${rep.exchange.ammoCostMusd}M / $${rep.exchange.interceptedValueMusd}M</div></div>
        <div class="stat-card"><div class="lbl">公信力变动 (浪费 ${rep.accountability.wastefulShots} 发)</div><div class="val" style="color:${rep.trust.applied >= 0 ? "#6ee7b7" : "#fca5a5"}">${rep.trust.applied >= 0 ? "+" : ""}${rep.trust.applied}</div></div>
      </div>
      <table class="report-table">
        <thead><tr><th>来袭威胁型号</th><th>来袭总数</th><th>成功拦截</th><th>突防命中</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="warning-card">
        <div class="warning-title">跨夜情报结转：今夜暴露的防空阵地 (${exposed.length} 处)</div>
        <div class="warning-desc">${kts}${exposed.length && !isLast ? " — 若进入第 2 夜，敌方将在第 5 波对上述坐标发动精准猎杀！" : ""}</div>
      </div>`;
  }

  function setSpeed(spd) {
    state.speed = Number(spd);
    document.querySelectorAll("#speed-btn-group .seg-btn[data-speed]").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.speed) === state.speed);
    });
  }

  setInterval(async () => {
    if (state.phase !== "battle" || state.speed <= 0 || state.stepBusy) return;
    if (state.snapshot && (state.snapshot.isEnded || state.snapshot.activeChoice)) return;
    state.stepBusy = true;
    try {
      const ticksMap = { 0.25: 2, 1: 8, 4: 32, 8: 64 };
      const snap = await rawPost("/api/step", { ticks: ticksMap[state.speed] || 8 });
      if (snap && snap.tick !== undefined) applySnapshot(snap);
    } finally { state.stepBusy = false; }
  }, 140);

  function animLoop() { window.TacticalRenderer.renderFrame(canvas, state); requestAnimationFrame(animLoop); }

  // 画布自适应：保持正方形并按 devicePixelRatio 渲染
  function fitCanvas() {
    const wrap = $("canvas-wrapper");
    const size = Math.max(240, Math.min(wrap.clientWidth, wrap.clientHeight) - 12);
    const v = canvas._view;
    if (v && v.width === Math.floor(size) && v.dpr === Math.min(2.5, window.devicePixelRatio || 1)) return;
    window.TacticalRenderer.resize(canvas, size, size);
  }

  function pickUnitAt(e, radiusPx) {
    const rect = canvas.getBoundingClientRect();
    const px = e.clientX - rect.left, py = e.clientY - rect.top;
    let best = null, bestD = radiusPx;
    getActiveUnits().forEach((u) => {
      const p = window.TacticalRenderer.unitScreenPos(u, canvas, state);
      const d = Math.hypot(p.x - px, p.y - py);
      if (d < bestD) { bestD = d; best = u; }
    });
    return best;
  }

  function setViewMode(mode) {
    state.viewMode = mode;
    document.querySelectorAll("#view-seg .seg-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === mode));
  }
  function toggleViewMode() { setViewMode(state.viewMode === "command" ? "live25d" : "command"); }

  function bindGlobalEvents() {
    document.querySelectorAll("#speed-btn-group .seg-btn[data-speed]").forEach((b) =>
      b.addEventListener("click", () => setSpeed(Number(b.dataset.speed))));
    $("btn-step-once").addEventListener("click", async () => {
      if (state.phase === "battle") applySnapshot(await rawPost("/api/step", { ticks: 10 }));
    });
    document.querySelectorAll("#view-seg .seg-btn").forEach((b) => b.addEventListener("click", () => setViewMode(b.dataset.view)));
    $("btn-view-mode").addEventListener("click", toggleViewMode);
    $("chk-god-view").addEventListener("change", (e) => { state.godView = e.target.checked; });
    $("sel-los-alt").addEventListener("change", async (e) => {
      state.losAltM = Number(e.target.value); if (state.losAltM > 0) await refreshCoverage();
      e.target.blur();
    });
    $("btn-alert-toggle").addEventListener("click", () => {
      if (state.phase === "battle" && state.snapshot) sendCommand({ type: "ToggleCivilAlert", on: !state.snapshot.alert.on });
    });
    $("btn-national-spoof").addEventListener("click", () => sendCommand({ type: "TriggerNationalSpoof" }));
    $("btn-trigger-choice-demo").addEventListener("click", async () => {
      if (state.phase === "deploy") await startNightBattle(true);
      await sendCommand({ type: "TriggerArmChoiceDemo" });
    });
    $("btn-reset-game").addEventListener("click", () => initGame(1, true));
    $("btn-clear-log").addEventListener("click", () => { $("event-log-list").innerHTML = ""; });

    document.querySelectorAll(".btn-preset").forEach((b) => b.addEventListener("click", async () => {
      document.querySelectorAll(".btn-preset").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      state.meta.currentPlacements = JSON.parse(JSON.stringify((state.meta.presets && state.meta.presets[b.dataset.preset]) || []));
      applyLevelMeta(state.meta); await refreshCoverage();
    }));

    $("btn-auto-relocate-exposed").addEventListener("click", async () => {
      const alts = (state.meta.deploy && state.meta.deploy.alternatePositions) || [];
      let idx = 0;
      state.placements.forEach((u) => {
        if (u.isExposed && alts[idx]) { u.pos = [alts[idx].pos[0], alts[idx].pos[1]]; u.isExposed = false; u.carryExposure = 0; idx = (idx + 1) % alts.length; }
      });
      $("exposed-warning-box").classList.add("hidden");
      await refreshCoverage(); renderRosterAndInspector();
    });

    $("btn-start-night").addEventListener("click", () => startNightBattle(false));
    $("btn-replay-night").addEventListener("click", () => initGame(state.meta.nightIndex, false));
    $("btn-next-night").addEventListener("click", async () => {
      applyLevelMeta(await apiPost("/api/next_night", {}, "正在结转跨夜状态…")); await refreshCoverage();
    });

    canvas.addEventListener("mousedown", (e) => {
      const best = pickUnitAt(e, 18);
      if (best) {
        state.selectedUnitKey = best.id || best.rosterId;
        if (state.phase === "deploy" && best.mobility !== "fixed") {
          state.draggingUnit = best;
          canvas.classList.add("grabbing");
        }
        renderRosterAndInspector();
      }
    });
    canvas.addEventListener("mousemove", (e) => {
      const rect = canvas.getBoundingClientRect();
      const view = window.TacticalRenderer.getView(canvas);
      const pt = window.TacticalRenderer.screenToWorld(e.clientX - rect.left, e.clientY - rect.top, view, state.viewMode);
      const elev = Math.round(window.TacticalRenderer.sampleElevation(state.meta, pt[0], pt[1]));
      const col = String.fromCharCode(65 + Math.min(7, Math.floor(pt[0] / 2500)));
      const row = 8 - Math.min(7, Math.floor(pt[1] / 2500));
      $("hover-telemetry").textContent =
        `格 ${col}${row} · X ${(pt[0] / 1000).toFixed(2)}km · Y ${(pt[1] / 1000).toFixed(2)}km · 海拔 ${elev}m`;
      if (state.draggingUnit && state.phase === "deploy") {
        state.draggingUnit.pos = [Math.round(pt[0]), Math.round(pt[1])];
        return;
      }
      const hov = pickUnitAt(e, 18);
      state.hoverUnitKey = hov ? (hov.id || hov.rosterId) : null;
      canvas.classList.toggle("can-grab", Boolean(hov && state.phase === "deploy" && hov.mobility !== "fixed"));
      canvas.classList.toggle("can-select", Boolean(hov) && !(state.phase === "deploy" && hov.mobility !== "fixed"));
    });
    canvas.addEventListener("mouseleave", () => { state.hoverUnitKey = null; });
    window.addEventListener("mouseup", async () => {
      canvas.classList.remove("grabbing");
      if (state.draggingUnit) {
        const u = state.draggingUnit;
        state.draggingUnit = null;
        const kts = (state.meta && state.meta.carryIn && state.meta.carryIn.knownTargets) || [];
        const kt = kts.find((k) => Number(k.rosterId) === Number(u.rosterId));
        if (kt && kt.pos && Math.hypot(u.pos[0] - kt.pos[0], u.pos[1] - kt.pos[1]) > 600.0) {
          u.isExposed = false;
          u.carryExposure = 0;
        }
        await refreshCoverage();
        renderRosterAndInspector();
      }
    });
    window.addEventListener("keydown", (e) => {
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (e.code === "Space" && state.phase === "battle") { e.preventDefault(); setSpeed(state.speed > 0 ? 0 : 1); }
      else if (e.code === "Tab") { e.preventDefault(); toggleViewMode(); }
      else if (state.phase === "battle" && ["Digit1", "Digit2", "Digit3"].includes(e.code)) {
        setSpeed({ Digit1: 1, Digit2: 4, Digit3: 8 }[e.code]);
      }
    });
    if (window.ResizeObserver) new ResizeObserver(fitCanvas).observe($("canvas-wrapper"));
    window.addEventListener("resize", fitCanvas);
  }

  async function startNightBattle(skipConfirm = false) {
    const kts = (state.meta && state.meta.carryIn && state.meta.carryIn.knownTargets) || [];
    if (!skipConfirm && state.meta && state.meta.nightIndex > 1 && kts.length > 0) {
      const unmoved = kts.filter((kt) => {
        const pu = state.placements.find((p) => Number(p.rosterId) === Number(kt.rosterId));
        if (!pu || !pu.pos || !kt.pos) return false;
        return Math.hypot(pu.pos[0] - kt.pos[0], pu.pos[1] - kt.pos[1]) <= 600.0;
      });
      if (unmoved.length > 0 && typeof window.confirm === "function") {
        const names = unmoved.map((k) => `${k.name}#${k.rosterId}`).join("、");
        if (!window.confirm(`⚠️ 警告：${names} 在首夜已被敌军标定坐标（未移位超过 600m），今夜将遭敌方专门猎杀！是否仍直接开始第 2 夜？`)) {
          return;
        }
      }
    }
    const snap = await apiPost("/api/start_night", { placements: state.placements, bot: $("sel-bot-mode").value }, "正在初始化夜间战场…");
    state.phase = "battle";
    setPhaseBadge("battle");
    $("deploy-controls-section").classList.add("hidden");
    applySnapshot(snap);
    state.selectedUnitKey = snap.units.length ? snap.units[0].id : null;
    renderRosterAndInspector();
    setSpeed(1);
  }

  // 调试/截图辅助：?demo=battle&ticks=600&view=live25d 自动开战并推进
  async function runDemoFromUrl() {
    const q = new URLSearchParams(location.search);
    if (q.get("view") === "live25d") setViewMode("live25d");
    if (q.get("god") === "1") { state.godView = true; $("chk-god-view").checked = true; }
    if (q.get("demo") !== "battle") return;
    if (q.get("bot")) $("sel-bot-mode").value = q.get("bot");
    await startNightBattle(true);
    setSpeed(0);
    const ticks = Number(q.get("ticks") || 600);
    applySnapshot(await rawPost("/api/step", { ticks }));
  }

  bindGlobalEvents();
  fitCanvas();
  requestAnimationFrame(animLoop);
  initGame(1, true).then(runDemoFromUrl);
})();
