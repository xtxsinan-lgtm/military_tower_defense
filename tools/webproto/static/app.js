// 《守夜》Nightwatch 网页纸上原型前端状态机与 API 交互逻辑
(function () {
  const state = {
    phase: "deploy", meta: null, placements: [], coverage: null, snapshot: null,
    selectedUnitKey: null, draggingUnit: null, viewMode: "command", godView: false,
    losAltM: 100, speed: 0, stepBusy: false, fxList: [], choiceDeadlineMs: 0, choiceTimerId: null,
  };
  const canvas = document.getElementById("tactical-canvas");
  const $ = (id) => document.getElementById(id);
  const apiGet = async (url) => window.nightwatchApi ? window.nightwatchApi("GET", url) : (await fetch(url)).json();
  const apiPost = async (url, data) => window.nightwatchApi ? window.nightwatchApi("POST", url, data) : (await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data || {}),
  })).json();

  async function initGame(night = 1, reset = false) {
    setSpeed(0);
    applyLevelMeta(await apiGet(`/api/init?level=test_01&night=${night}&reset=${reset ? 1 : 0}`));
    await refreshCoverage();
  }

  function applyLevelMeta(meta) {
    state.phase = "deploy"; state.meta = meta; state.snapshot = null;
    const catMap = {};
    (meta.unitCatalog || []).forEach((c) => { catMap[c.unitDefId] = c; });
    state.placements = (meta.currentPlacements || []).map((p) => {
      const c = catMap[p.unitDefId] || {};
      return Object.assign({}, p, {
        name: p.name || c.name || p.unitDefId, category: p.category || c.category || "fire",
        hasRadar: Boolean(c.hasRadar),
        detectionRangeM: c.radarRangeM || c.detectionRangeM || c.selfAcquisitionRangeM || 0,
        weapons: c.weapons || [],
      });
    });
    state.selectedUnitKey = state.placements.length ? state.placements[0].rosterId : null;
    $("level-title").textContent = meta.levelName;
    $("night-badge").textContent = `第 ${meta.nightIndex} 夜 / 共 ${meta.totalNights} 夜`;
    $("phase-badge").textContent = "战前部署";
    $("date-weather-badge").textContent = `${meta.date} · ${meta.weather === "clear" ? "晴" : meta.weather}`;
    $("trust-badge").textContent = `公信力 ${meta.trustScore}`;
    $("world-clock").textContent = "22:00:00";
    $("tick-readout").textContent = "战前准备阶段";
    $("clock-progress").style.width = "0%";
    $("cp-badge").textContent = `指挥点 CP: ${meta.commandPointsPerNight} / ${meta.commandPointsPerNight}`;
    $("deploy-controls-section").classList.remove("hidden");
    $("report-modal").classList.add("hidden");
    $("choice-modal").classList.add("hidden");

    const kts = (meta.carryIn && meta.carryIn.knownTargets) || [];
    const warnBox = $("exposed-warning-box");
    if (kts.length > 0) {
      warnBox.classList.remove("hidden");
      $("exposed-warning-desc").textContent =
        `敌方侦察已标定昨夜暴露阵地：${kts.map((k) => `${k.name}(#${k.rosterId})`).join("、")}。今夜 03:30 (第5波) 将发射巡航导弹猎杀原坐标！请立即移至预备阵地。`;
    } else warnBox.classList.add("hidden");
    renderIntelList(); renderStructuresAndAmmo(); renderRosterAndInspector();
  }

  async function refreshCoverage() {
    if (!state.meta) return;
    const list = state.phase === "deploy" ? state.placements : (state.snapshot ? state.snapshot.units : []);
    const cov = await apiPost("/api/coverage", { placements: list, altM: state.losAltM || 100, gridRes: 56 });
    state.coverage = cov;
    $("cov-vis-pct").textContent = `${(cov.stats.visibleFrac * 100).toFixed(1)}%`;
    $("cov-blind-pct").textContent = `${(cov.stats.blindFrac * 100).toFixed(1)}%`;
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
        <div style="display:flex;justify-content:space-between;font-size:10.5px;color:#93c5fd;margin-bottom:2px;">
          <span>波次: ${it.relatedWave || "全夜"}</span><span>${it.confidence === "confirmed" ? "✓ 高可信通报" : "⚠ 研判估计"}</span>
        </div><div>${it.text}</div>
      </div>`).join("");
  }

  function renderStructuresAndAmmo() {
    const snap = state.snapshot;
    const structs = (snap && snap.structures) || (state.meta && state.meta.structures) || [];
    $("structures-list").innerHTML = structs.map((s) => {
      const pct = Math.max(0, Math.min(100, (s.hp / Math.max(1, s.maxHp)) * 100));
      const pwr = s.powered === false ? '<span class="badge badge-err">断电</span>' : '<span class="badge badge-ok">供电正常</span>';
      return `<div class="struct-item"><div style="display:flex;justify-content:space-between;align-items:center;">
        <strong>${s.name}</strong><span>HP ${s.hp}/${s.maxHp} ${pwr}</span></div>
        <div class="hp-bar-wrap"><div class="hp-bar-fill" style="width:${pct}%"></div></div></div>`;
    }).join("");
    const gBadge = $("grid-status-badge");
    if (snap && snap.grid) {
      const unp = Math.round((snap.grid.unpoweredFrac || 0) * 100);
      gBadge.textContent = snap.grid.collapsed ? `电网崩溃 (断电 ${unp}%)` : `电网正常 (断电 ${unp}%)`;
      gBadge.className = `badge ${snap.grid.collapsed || unp > 0 ? "badge-err" : "badge-ok"}`;
    }
    const pool = (snap && snap.ammoPool) || (state.meta && state.meta.carryIn && state.meta.carryIn.ammoPool) || {};
    const labels = { iris_t_slm_missile: "IRIS-T 导弹", amraam_nasams: "NASAMS 导弹", igla_manpads: "针式便携弹", heavy_mg_12_7: "高机弹药" };
    const entries = Object.keys(pool).length ? Object.entries(pool) : [["iris_t_slm_missile", 16], ["amraam_nasams", 18], ["igla_manpads", 16], ["heavy_mg_12_7", "充足"]];
    $("ammo-pool-list").innerHTML = entries.map(([k, v]) =>
      `<div class="ammo-cell"><span>${labels[k] || k}</span><strong>${v > 90000 ? "充足" : v}</strong></div>`).join("");
  }

  const getActiveUnits = () => state.phase === "deploy" ? state.placements : ((state.snapshot && state.snapshot.units) || []);

  function renderRosterAndInspector() {
    const units = getActiveUnits();
    $("roster-count-badge").textContent = `${units.length} 单位`;
    const rBox = $("unit-roster-list");
    rBox.innerHTML = units.map((u) => {
      const key = u.id || u.rosterId, sel = key === state.selectedUnitKey ? "selected" : "";
      const expFlag = u.isExposed || u.isKnownTarget || (u.exposure || 0) >= 70 ? "exposed" : "";
      const isArmSilenced = Boolean(u.emitter && u.emitter.armSilenced);
      const em = isArmSilenced
        ? '<span style="color:#fbbf24;font-weight:bold;">🔇 规避静默中</span>'
        : (u.emitter ? (u.emitter.on ? "📡开机" : "静默") : (u.emissionPolicy || ""));
      const w0 = (u.weapons && u.weapons[0]) ? (u.weapons[0].rounds >= 0 ? `弹${u.weapons[0].rounds}` : "机枪") : "";
      return `<div class="roster-item ${sel} ${expFlag}" data-ukey="${key}">
        <div><strong>#${u.rosterId} ${u.name}</strong> <span style="color:#94a3b8;">${u.deployState || "就绪"}</span></div>
        <div style="font-family:monospace;color:#7dd3fc;">${em} ${w0} ${(u.exposure || 0) > 0 ? `暴${Math.round(u.exposure)}%` : ""}</div></div>`;
    }).join("");
    rBox.querySelectorAll(".roster-item").forEach((el) => {
      el.addEventListener("click", () => { state.selectedUnitKey = Number(el.dataset.ukey); renderRosterAndInspector(); });
    });
    renderInspector(units.find((u) => (u.id || u.rosterId) === state.selectedUnitKey));
  }

  function renderInspector(u) {
    const body = $("insp-body");
    if (!u) {
      body.innerHTML = '<div class="empty-hint">点击地图或列表中的防空单位进行检视与指挥。</div>';
      return;
    }
    $("insp-unit-title").textContent = `#${u.rosterId} ${u.name}`;
    $("insp-unit-state").textContent = u.deployState || "PRE-NIGHT";
    const exp = Math.round(u.exposure !== undefined ? u.exposure : (u.carryExposure || 0));
    const alts = ((state.meta && state.meta.deploy && state.meta.deploy.alternatePositions) || []);
    const altOpts = alts.map((a) => `<option value="${a.id}">${a.id} (${Math.round(a.pos[0])},${Math.round(a.pos[1])})</option>`).join("");
    const curPol = u.emitter ? u.emitter.policyId : (u.emissionPolicy || "blink");
    const isArmSilenced = Boolean(u.emitter && u.emitter.armSilenced);

    let html = `
      <div class="insp-row"><span>坐标: (${Math.round(u.pos[0])}m, ${Math.round(u.pos[1])}m)</span><span>击落: <strong>${u.killsTonight || 0}</strong></span></div>
      <div class="insp-row"><span>暴露度: <strong style="color:${exp >= 70 ? "#ef4444" : "#2dd4bf"}">${exp}%</strong> (≥70% 跨夜标定)</span></div>
      <div class="exp-bar-wrap"><div class="exp-bar-fill" style="width:${Math.min(100, exp)}%"></div></div>`;

    if (isArmSilenced) {
      html += `<div class="insp-row" style="margin-top:4px;color:#fbbf24;font-weight:bold;">
        <span>状态告警: 🔇 规避静默中（危机解除后请手动切回闪烁/常开）</span>
      </div>`;
    }

    if ((u.emitter && u.emitter.hasEmitter) || u.hasRadar || u.unitDefId === "soviet_mid_range_radar" || u.unitDefId === "nasams") {
      html += `<div class="insp-row" style="margin-top:4px;">
        <span>雷达策略:</span>
        <select id="insp-sel-policy" class="select-sm">
          <option value="silent" ${curPol === "silent" ? "selected" : ""}>静默 (Silent)</option>
          <option value="blink" ${curPol === "blink" ? "selected" : ""}>闪烁周期 (Blink)</option>
          <option value="continuous" ${curPol === "continuous" ? "selected" : ""}>持续开机 (On)</option>
        </select>
        ${state.phase === "battle" ? `<button id="insp-btn-burst" class="btn btn-xs btn-warn">短促扫描</button>` : ""}
      </div>`;
    }

    if (u.mobility !== "fixed" && alts.length > 0) {
      html += `<div class="insp-row" style="margin-top:4px;">
        <select id="insp-sel-alt" class="select-sm flex-1">${altOpts}</select>
        <button id="insp-btn-reloc" class="btn btn-xs btn-primary">${state.phase === "deploy" ? "战前移位" : "机动转移 (1 CP)"}</button>
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
        quotaHtml = `<div class="insp-row" style="font-size:11px;color:${remQ <= 0 ? "#ef4444" : "#93c5fd"};">
          <span>本关剩余配额: <strong>${remQ}/${plLim}</strong> ${remQ <= 0 ? "[配额已尽]" : ""}</span>
        </div>`;
      }
      html += `<div class="weapon-box">
        <div class="insp-row"><strong>${w.name}</strong><span style="font-family:monospace;color:#f59e0b;">弹: ${rds} ${w.reloadRemSec > 0 ? `(${w.reloadRemSec}s)` : ""}</span></div>
        ${quotaHtml}
        <div class="insp-row"><span>射击规则:</span>
          <select class="select-sm insp-w-rule" data-wid="${wid}">
            <option value="any" ${w.rule === "any" ? "selected" : ""}>自由迎击 (Any)</option>
            <option value="high_value_only" ${w.rule === "high_value_only" ? "selected" : ""}>仅限高价值</option>
            <option value="ballistic_only" ${w.rule === "ballistic_only" ? "selected" : ""}>仅限弹道导弹</option>
            <option value="hold_fire" ${w.rule === "hold_fire" ? "selected" : ""}>停火 (Hold)</option>
          </select>
        </div>
        <div class="insp-row"><span>保留弹数: <strong id="lbl-res-${wid}">${w.ammoReserve || 0}</strong></span>
          <input type="range" min="0" max="4" value="${w.ammoReserve || 0}" class="insp-w-res" data-wid="${wid}" />
        </div>
        <div class="tag-checks">
          ${["UAV", "CM", "BM", "AC_LOW"].map((tg) => `<label><input type="checkbox" class="insp-w-tag" data-wid="${wid}" value="${tg}" ${wl.includes(tg) ? "checked" : ""}/> ${tg}</label>`).join("")}
          <label><input type="checkbox" class="insp-w-sls" data-wid="${wid}" ${w.shootLookShoot !== false ? "checked" : ""}/> 1+1教范</label>
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
      el.addEventListener("change", () => sendCommand({ type: "SetEngagementRule", unitId: u.id, weaponId: el.dataset.wid, rule: el.value }));
    });
    document.querySelectorAll(".insp-w-res").forEach((el) => {
      el.addEventListener("input", () => {
        $(`lbl-res-${el.dataset.wid}`).textContent = el.value;
        sendCommand({ type: "SetAmmoReserve", unitId: u.id, weaponId: el.dataset.wid, reserve: Number(el.value) });
      });
    });
    document.querySelectorAll(".insp-w-tag").forEach((el) => {
      el.addEventListener("change", () => {
        const wid = el.dataset.wid;
        const tags = Array.from(document.querySelectorAll(`.insp-w-tag[data-wid="${wid}"]:checked`)).map((c) => c.value);
        sendCommand({ type: "SetTargetWhitelist", unitId: u.id, weaponId: wid, tags });
      });
    });
    document.querySelectorAll(".insp-w-sls").forEach((el) => {
      el.addEventListener("change", () => sendCommand({ type: "SetShootLookShoot", unitId: u.id, weaponId: el.dataset.wid, enabled: el.checked }));
    });
  }

  async function sendCommand(payload) {
    if (state.phase !== "battle") return;
    const snap = await apiPost("/api/command", payload);
    if (snap && snap.tick !== undefined) applySnapshot(snap);
  }

  function applySnapshot(snap) {
    state.snapshot = snap;
    $("world-clock").textContent = snap.clockStr;
    const pct = Math.min(100, (snap.timeWorldSec / Math.max(1, snap.durationWorldSec)) * 100);
    $("clock-progress").style.width = `${pct.toFixed(1)}%`;
    $("tick-readout").textContent = `T+${Math.round(snap.timeWorldSec)}s (${pct.toFixed(0)}%)`;
    $("cp-badge").textContent = `指挥点 CP: ${snap.cp.current} / ${snap.cp.initial}`;

    const alBtn = $("btn-alert-toggle");
    const shPct = Math.round((snap.alert.shelteredFrac || 0) * 100);
    alBtn.textContent = `民防警报：${snap.alert.on ? "拉响中" : "关闭"} (掩蔽 ${shPct}%)`;
    alBtn.className = `btn btn-sm ${snap.alert.on ? "btn-alert-on" : ""}`;
    if (snap.radioBanner) $("radio-text").textContent = snap.radioBanner;

    const logBox = $("event-log-list");
    (snap.events || []).forEach((ev) => {
      const div = document.createElement("div");
      div.className = `log-entry level-${ev.level || "info"}`;
      div.textContent = `[${ev.clock}] ${ev.text}`;
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
    $("choice-unit-subtitle").textContent = `被锁定雷达名称与坐标：${ch.subjectUnitName}${posStr}`;
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
    $("report-rating").textContent = rep.rating;
    $("report-score").textContent = `${rep.compositeScore} 分`;
    const rows = (rep.byEnemyType || []).map((r) =>
      `<tr><td>${r.name}</td><td>${r.spawned}</td><td>${r.intercepted} (${r.interceptRate}%)</td><td>${r.penetrated}</td></tr>`).join("");
    const kts = (rep.exposedPositions || []).map((k) => `${k.name}(#${k.rosterId}, 暴露 ${k.exposure}%)`).join("、") || "无（全员隐蔽良好）";
    $("report-body").innerHTML = `
      <div class="report-grid">
        <div class="stat-card"><div class="lbl">保卫加权损失率</div><div class="val">${rep.weightedLossPercent}%</div></div>
        <div class="stat-card"><div class="lbl">总拦截率</div><div class="val">${rep.summary.interceptRatePercent}% (${rep.summary.totalIntercepted}/${rep.summary.totalSpawned})</div></div>
        <div class="stat-card"><div class="lbl">弹药效费比 (耗弹/毁伤)</div><div class="val">$${rep.exchange.ammoCostMusd}M / $${rep.exchange.interceptedValueMusd}M</div></div>
        <div class="stat-card"><div class="lbl">公信力变动 (浪费${rep.accountability.wastefulShots}发)</div><div class="val">${rep.trust.applied >= 0 ? "+" : ""}${rep.trust.applied}</div></div>
      </div>
      <table class="report-table">
        <thead><tr><th>来袭威胁型号</th><th>来袭总数</th><th>成功拦截</th><th>突防命中</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="warning-card">
        <div class="warning-title">跨夜情报结转：今夜暴露的防空阵地 (${rep.exposedPositions.length} 处)</div>
        <div class="warning-desc">${kts} — 若进入第 2 夜，敌方将在第 5 波对上述坐标发动精准猎杀！</div>
      </div>`;
  }

  function setSpeed(spd) {
    state.speed = Number(spd);
    document.querySelectorAll("#speed-btn-group .btn[data-speed]").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.speed) === state.speed);
    });
  }

  setInterval(async () => {
    if (state.phase !== "battle" || state.speed <= 0 || state.stepBusy) return;
    if (state.snapshot && (state.snapshot.isEnded || state.snapshot.activeChoice)) return;
    state.stepBusy = true;
    try {
      const ticksMap = { 0.25: 2, 1: 8, 4: 32, 8: 64 };
      const snap = await apiPost("/api/step", { ticks: ticksMap[state.speed] || 8 });
      if (snap && snap.tick !== undefined) applySnapshot(snap);
    } finally { state.stepBusy = false; }
  }, 140);

  function animLoop() { window.TacticalRenderer.renderFrame(canvas, state); requestAnimationFrame(animLoop); }

  function bindGlobalEvents() {
    document.querySelectorAll("#speed-btn-group .btn[data-speed]").forEach((b) =>
      b.addEventListener("click", () => setSpeed(Number(b.dataset.speed))));
    $("btn-step-once").addEventListener("click", async () => {
      if (state.phase === "battle") applySnapshot(await apiPost("/api/step", { ticks: 10 }));
    });
    $("btn-view-mode").addEventListener("click", toggleViewMode);
    $("chk-god-view").addEventListener("change", (e) => { state.godView = e.target.checked; });
    $("sel-los-alt").addEventListener("change", async (e) => {
      state.losAltM = Number(e.target.value); if (state.losAltM > 0) await refreshCoverage();
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
      applyLevelMeta(await apiPost("/api/next_night", {})); await refreshCoverage();
    });

    canvas.addEventListener("mousedown", (e) => {
      const pt = getCanvasWorldPos(e);
      let best = null, bestD = 900;
      getActiveUnits().forEach((u) => {
        const d = Math.hypot(u.pos[0] - pt[0], u.pos[1] - pt[1]);
        if (d < bestD) { bestD = d; best = u; }
      });
      if (best) {
        state.selectedUnitKey = best.id || best.rosterId;
        if (state.phase === "deploy" && best.mobility !== "fixed") state.draggingUnit = best;
        renderRosterAndInspector();
      }
    });
    canvas.addEventListener("mousemove", (e) => {
      const pt = getCanvasWorldPos(e);
      const elev = Math.round(window.TacticalRenderer.sampleElevation(state.meta, pt[0], pt[1]));
      $("hover-telemetry").textContent =
        `坐标: X ${Math.round(pt[0])}m, Y ${Math.round(pt[1])}m | 海拔: ${elev}m | 视图: ${state.viewMode === "live25d" ? "2.5D 25°斜视角" : "平面指挥图"}`;
      if (state.draggingUnit && state.phase === "deploy") state.draggingUnit.pos = [Math.round(pt[0]), Math.round(pt[1])];
    });
    window.addEventListener("mouseup", async () => {
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
      if (e.code === "Space" && state.phase === "battle") { e.preventDefault(); setSpeed(state.speed > 0 ? 0 : 1); }
      else if (e.code === "Tab") { e.preventDefault(); toggleViewMode(); }
    });
  }

  function getCanvasWorldPos(e) {
    const rect = canvas.getBoundingClientRect();
    return window.TacticalRenderer.screenToWorld(
      ((e.clientX - rect.left) / rect.width) * canvas.width,
      ((e.clientY - rect.top) / rect.height) * canvas.height,
      canvas, state.viewMode
    );
  }

  function toggleViewMode() {
    state.viewMode = state.viewMode === "command" ? "live25d" : "command";
    $("btn-view-mode").textContent = state.viewMode === "live25d" ? "视图：实况 2.5D 斜视角 [Tab]" : "视图：指挥台平面图 [Tab]";
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
    const snap = await apiPost("/api/start_night", { placements: state.placements, bot: $("sel-bot-mode").value });
    state.phase = "battle";
    $("phase-badge").textContent = "夜间防空实战";
    $("deploy-controls-section").classList.add("hidden");
    applySnapshot(snap);
    state.selectedUnitKey = snap.units.length ? snap.units[0].id : null;
    renderRosterAndInspector();
    setSpeed(1);
  }

  bindGlobalEvents(); initGame(1, true); requestAnimationFrame(animLoop);
})();
