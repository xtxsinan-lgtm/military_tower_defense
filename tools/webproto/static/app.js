// 《守夜》Nightwatch 网页纸上原型前端状态机与 API 交互逻辑
// 设计目标：第一次打开的人不看文档也能玩——任务简报 → 聚光灯教程 → 参谋建议 → 拂晓复盘。
(function () {
  const state = {
    phase: "deploy", meta: null, placements: [], coverage: null, snapshot: null,
    selectedUnitKey: null, hoverUnitKey: null, draggingUnit: null, viewMode: "command", godView: false,
    losAltM: 100, speed: 0, stepBusy: false, skipping: false, fxList: [], pulses: [],
    choiceDeadlineMs: 0, choiceTimerId: null,
    ammoInitial: {}, lastRadio: "", activePreset: "layered",
    tally: { kills: 0, leaks: 0 }, lastThreatTick: 0, advSig: "", advActions: [],
  };
  const canvas = document.getElementById("tactical-canvas");
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s === undefined || s === null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const { Coach, Toast } = window.NWGuide;
  const LS = {
    get: (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (_) { /* 隐私模式 */ } },
  };

  // ───────────── 玩家可读的说明文字（仅用于界面，不参与模拟） ─────────────
  const UNIT_INFO = {
    mobile_fire_team: { role: "近程火力", desc: "皮卡载机枪/高炮。专打<b>低慢的无人机</b>，弹药几乎用不完。自己<b>没有雷达</b>，要靠别人发现目标。" },
    iris_t_sls: { role: "近程导弹", desc: "命中率高的防空导弹。<b>导弹数量有限</b>（见右侧库存），尽量别浪费在廉价无人机上。" },
    nasams: { role: "主力防空", desc: "自带雷达的中远程系统，是你的主力。<b>雷达开机会暴露位置</b>，小心反辐射导弹。" },
    soviet_mid_range_radar: { role: "警戒雷达", desc: "负责<b>远距离发现敌人</b>，自己不能开火。山脊会挡住它看低空；开机也会暴露位置。" },
    acoustic_post: { role: "声学哨", desc: "靠<b>听声音</b>发现附近的低空无人机，<b>不会暴露</b>。适合填补雷达盲区。" },
    visual_observer: { role: "目视哨", desc: "用眼睛发现附近目标，<b>不会暴露</b>。适合放进山脊后的盲区。" },
  };
  const CAT_ROLE = { fire: "火力单元", sensor: "侦察单元", ew: "电子战", deception: "诱饵" };
  const STRUCT_INFO = {
    power_plant: "城市供电的核心，<b>最重要</b>。被毁会让大片城区断电。",
    substation: "电网枢纽。被毁会切断下游供电，部分防空阵地也会转入备用电池。",
    water_plant: "城市供水设施。",
  };
  const TAG_CN = { UAV: "无人机", CM: "巡航导弹", BM: "弹道导弹", AC_LOW: "低空飞机", ARM: "反辐射导弹", DECOY: "诱饵", UNKNOWN: "未识别目标" };
  const Q_CN = ["刚发现，位置模糊", "粗略跟踪中", "已锁定，可以开火", "已识别型号"];
  const POLICY = [
    ["continuous", "常开", "看得最远，最易暴露"],
    ["blink", "闪烁", "间歇开机，折中"],
    ["silent", "静默", "不暴露，看不见"],
  ];
  const AMMO_LABELS = { iris_t_slm_missile: "IRIS-T 导弹", amraam_nasams: "NASAMS 导弹", igla_manpads: "便携防空导弹", heavy_mg_12_7: "机枪弹药" };
  const AMMO_UNIT = { iris_t_slm_missile: "iris_t_sls", amraam_nasams: "nasams" };
  const STATE_NAMES = {
    ACTIVE: "就绪", Deployed: "就绪", Moving: "机动中", Packing: "撤收中", Packed: "已撤收",
    Deploying: "展开中", Destroyed: "被毁", Suppressed: "压制",
  };
  const isActiveState = (s) => !s || s === "ACTIVE" || s === "Deployed" || s === "PRE-NIGHT";

  // ───────────── API ─────────────
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

  // ───────────── 关卡与阶段 ─────────────
  async function initGame(night = 1, reset = false) {
    setSpeed(0);
    applyLevelMeta(await apiGet(`/api/init?level=test_01&night=${night}&reset=${reset ? 1 : 0}`, "正在载入关卡与模拟核心…"));
    await refreshCoverage();
  }

  function setPhase(phase) {
    state.phase = phase;
    document.body.classList.toggle("phase-deploy", phase === "deploy");
    document.body.classList.toggle("phase-battle", phase === "battle");
    const el = $("phase-badge");
    if (phase === "battle") { el.textContent = "夜间实战"; el.className = "chip chip-red"; }
    else { el.textContent = "战前部署"; el.className = "chip chip-amber"; }
    setStep(phase);
  }

  function setStep(which) {
    const order = ["deploy", "battle", "report"];
    const idx = order.indexOf(which);
    document.querySelectorAll("#stepper .step").forEach((s) => {
      const i = order.indexOf(s.dataset.step);
      s.classList.toggle("active", i === idx);
      s.classList.toggle("done", i < idx);
    });
  }

  function applyLevelMeta(meta) {
    state.meta = meta; state.snapshot = null; state.fxList = []; state.pulses = [];
    state.tally = { kills: 0, leaks: 0 }; state.lastThreatTick = 0; state.advSig = "";
    setPhase("deploy");
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
    $("date-weather-badge").textContent = `${meta.date} · ${meta.weather === "clear" ? "晴" : meta.weather}`;
    $("trust-badge").textContent = `${meta.trustScore}`;
    $("world-clock").textContent = "22:00:00";
    $("tick-readout").textContent = "战前准备";
    $("clock-progress").style.width = "0%";
    const nStruct = (meta.structures || []).length;
    $("step-goal").textContent = `目标：守住 ${nStruct} 处设施，撑到 06:00`;
    setCp(meta.commandPointsPerNight, meta.commandPointsPerNight);
    $("deploy-controls-section").classList.remove("hidden");
    $("report-modal").classList.add("hidden");
    $("choice-modal").classList.add("hidden");
    $("btn-alert-toggle").textContent = "防空警报：关";
    $("btn-alert-toggle").className = "btn btn-sm battle-only";
    setRadio(meta.nightIndex > 1
      ? "第 2 夜：昨晚暴露的阵地已被敌人记住，开战前先转移它们。"
      : "战前部署：拖动单位调整阵地，尽量消除北山脊后的红色盲区。");
    $("event-log-list").innerHTML = '<div class="log-empty">开战后，发现敌机、拦截、命中等事件会在这里滚动。</div>';
    Toast.clear();
    updateHud();

    const kts = (meta.carryIn && meta.carryIn.knownTargets) || [];
    const warnBox = $("exposed-warning-box");
    if (kts.length > 0) {
      warnBox.classList.remove("hidden");
      $("exposed-warning-desc").textContent =
        `昨晚暴露过高的阵地：${kts.map((k) => `${k.name}(#${k.rosterId})`).join("、")}。今夜敌人会专门用巡航导弹打这些坐标——开战前把它们挪走。`;
    } else warnBox.classList.add("hidden");
    renderIntelList(); renderStructuresAndAmmo(); renderRosterAndInspector(); renderAdvisor(true);
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
    const cov = await apiPost("/api/coverage", { placements: list, altM: state.losAltM || 100, gridRes: 56 }, "正在计算雷达覆盖…");
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
    renderAdvisor();
  }

  // ───────────── 面板渲染 ─────────────
  function renderIntelList() {
    const items = (state.meta && state.meta.intel) || [];
    $("intel-count-badge").textContent = `${items.length} 条`;
    $("intel-list").innerHTML = items.map((it) => `
      <div class="intel-item ${it.accurate ? "" : "inaccurate"}">
        <div class="intel-meta">
          <span>${esc(it.relatedWave || "全夜")}</span>
          <span class="${it.confidence === "confirmed" ? "intel-conf-ok" : "intel-conf-rumor"}">${it.confidence === "confirmed" ? "高可信通报" : "研判估计"}</span>
        </div><div>${esc(it.text)}</div>
      </div>`).join("");
  }

  function renderStructuresAndAmmo() {
    const snap = state.snapshot;
    const structs = (snap && snap.structures) || (state.meta && state.meta.structures) || [];
    $("structures-list").innerHTML = structs.map((s) => {
      const frac = Math.max(0, Math.min(1, s.hp / Math.max(1, s.maxHp)));
      const col = frac > 0.5 ? "var(--ok)" : (frac > 0.2 ? "var(--accent)" : "var(--danger)");
      const pwr = s.destroyed ? '<span class="badge badge-err">已摧毁</span>'
        : (s.powered === false ? '<span class="badge badge-err">断电</span>' : '<span class="badge badge-ok">正常</span>');
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
    const pool = getAmmoPool();
    $("ammo-pool-list").innerHTML = Object.entries(pool).map(([k, v]) => {
      const inf = typeof v !== "number" || v > 90000;
      if (!inf && (state.ammoInitial[k] === undefined || v > state.ammoInitial[k])) state.ammoInitial[k] = v;
      const init = state.ammoInitial[k] || 1;
      const frac = inf ? 1 : Math.max(0, Math.min(1, v / init));
      return `<div class="ammo-cell">
        <div class="ammo-top"><span>${esc(AMMO_LABELS[k] || k)}</span><strong class="${!inf && frac < 0.25 ? "low" : ""}">${inf ? "充足" : v}</strong></div>
        <div class="ammo-meter"><i style="width:${frac * 100}%"></i></div></div>`;
    }).join("");
  }

  function getAmmoPool() {
    const snap = state.snapshot;
    const pool = (snap && snap.ammoPool) || (state.meta && state.meta.carryIn && state.meta.carryIn.ammoPool) || {};
    return Object.keys(pool).length ? pool : { iris_t_slm_missile: 16, amraam_nasams: 18, igla_manpads: 16, heavy_mg_12_7: 99999 };
  }

  const getActiveUnits = () => state.phase === "deploy" ? state.placements : ((state.snapshot && state.snapshot.units) || []);
  const unitKey = (u) => u.id || u.rosterId;
  const CAT_ORDER = ["fire", "sensor", "ew", "deception"];
  const CAT_NAMES = { fire: "火力单元 · 负责开火", sensor: "侦察单元 · 负责发现", ew: "电子战", deception: "诱饵" };

  function renderRosterAndInspector() {
    const units = getActiveUnits();
    $("roster-count-badge").textContent = `${units.length} 单位`;
    const rBox = $("unit-roster-list");
    const scrollTop = rBox.scrollTop;
    const groups = {};
    units.forEach((u) => { const c = u.category || "fire"; (groups[c] = groups[c] || []).push(u); });
    const cats = CAT_ORDER.filter((c) => groups[c]).concat(Object.keys(groups).filter((c) => !CAT_ORDER.includes(c)));
    rBox.innerHTML = cats.map((cat) => `<div class="roster-group">${CAT_NAMES[cat] || cat} · ${groups[cat].length}</div>` + groups[cat].map((u) => {
      const key = unitKey(u), sel = key === state.selectedUnitKey ? "selected" : "";
      const expV = u.exposure !== undefined ? u.exposure : (u.carryExposure || 0);
      const expFlag = u.isExposed || u.isKnownTarget || expV >= 70 ? "exposed" : "";
      const isArmSilenced = Boolean(u.emitter && u.emitter.armSilenced);
      const em = isArmSilenced ? '<span class="em-arm">规避静默</span>'
        : (u.emitter && u.emitter.hasEmitter ? (u.emitter.on ? '<span class="em-on">雷达开</span>' : '<span>雷达关</span>') : "");
      const w0 = (u.weapons && u.weapons[0] && u.weapons[0].rounds !== undefined) ? (u.weapons[0].rounds >= 0 ? `弹${u.weapons[0].rounds}` : "") : "";
      const expTxt = expV > 0 ? `<span class="${expV >= 70 ? "exp-hi" : (expV >= 35 ? "exp-mid" : "")}">暴露${Math.round(expV)}%</span>` : "";
      const st = u.deployState ? (STATE_NAMES[u.deployState] || u.deployState) : "";
      const inactive = !isActiveState(u.deployState);
      return `<div class="roster-item ${sel} ${expFlag}" data-ukey="${key}">
        <i class="roster-pip cat-${esc(u.category || "fire")} ${inactive ? "inactive" : ""}"></i>
        <div class="roster-name"><span class="rid">#${u.rosterId}</span><strong>${esc(u.name)}</strong>${st && st !== "就绪" ? `<span class="rstate">${esc(st)}</span>` : ""}</div>
        <div class="roster-meta">${em}${w0 ? `<span>${w0}</span>` : ""}${expTxt}</div></div>`;
    }).join("")).join("");
    rBox.scrollTop = scrollTop;
    rBox.querySelectorAll(".roster-item").forEach((el) => {
      el.addEventListener("click", () => { state.selectedUnitKey = Number(el.dataset.ukey); renderRosterAndInspector(); });
    });
    renderInspector(units.find((u) => unitKey(u) === state.selectedUnitKey));
  }

  function rangeOf(u) {
    const w = (u.weapons || []).find((x) => x.rangeM > 0);
    return w ? w.rangeM : 0;
  }

  function renderInspector(u) {
    const body = $("insp-body");
    if (body.contains(document.activeElement) && document.activeElement.tagName !== "BUTTON" && body.dataset.ukey === String(u && unitKey(u))) return;
    body.dataset.ukey = String(u ? unitKey(u) : "");
    if (!u) {
      $("insp-unit-title").textContent = "选中单位";
      $("insp-unit-state").textContent = "—";
      body.innerHTML = '<div class="empty-hint">点击地图上的单位，看看它能做什么。</div>';
      return;
    }
    const info = UNIT_INFO[u.unitDefId] || { role: CAT_ROLE[u.category] || "单位", desc: "" };
    $("insp-unit-title").textContent = `${u.name}`;
    const st = u.deployState || "PRE-NIGHT";
    const stEl = $("insp-unit-state");
    stEl.textContent = st === "PRE-NIGHT" ? info.role : (STATE_NAMES[st] || st);
    stEl.className = `badge ${isActiveState(st) ? "badge-ok" : (st === "Destroyed" ? "badge-err" : "badge-info")}`;
    const exp = Math.round(u.exposure !== undefined ? u.exposure : (u.carryExposure || 0));
    const alts = ((state.meta && state.meta.deploy && state.meta.deploy.alternatePositions) || []);
    const altOpts = alts.map((a) => `<option value="${esc(a.id)}">${esc(a.id.replace("alt_", "预备阵地 · "))}</option>`).join("");
    const curPol = u.emitter ? u.emitter.policyId : (u.emissionPolicy || "blink");
    const isArmSilenced = Boolean(u.emitter && u.emitter.armSilenced);
    const hasEmitter = (u.emitter && u.emitter.hasEmitter) || u.hasRadar || u.unitDefId === "soviet_mid_range_radar" || u.unitDefId === "nasams";
    const expCol = exp >= 70 ? "var(--danger)" : (exp >= 35 ? "var(--accent)" : "var(--text)");
    const rng = rangeOf(u), det = u.detectionRangeM || 0;

    let html = `<div class="insp-desc"><b>${esc(info.role)}</b>　${info.desc}</div>
      <div class="insp-stats">
        <div class="insp-stat"><span class="k">${rng ? "射程" : "探测范围"}</span><span class="v">${((rng || det) / 1000).toFixed(1)} km</span></div>
        <div class="insp-stat"><span class="k">今夜击落</span><span class="v">${u.killsTonight || 0}</span></div>
        <div class="insp-stat"><span class="k">暴露度</span><span class="v" style="color:${expCol}">${exp}%</span></div>
      </div>
      <div class="exp-bar-wrap" data-tip="暴露度：雷达开机越久越高。超过 70% 敌人会记住这个位置，下一夜专门来打。"><div class="exp-bar-fill" style="width:${Math.min(100, exp)}%"></div></div>`;

    if (isArmSilenced) html += `<div class="insp-alert">正在关机躲避反辐射导弹，这段时间看不见敌人。危险过去后点下方“闪烁”或“常开”恢复。</div>`;

    if (hasEmitter) {
      html += `<div class="insp-section-lbl">雷达开关</div>
        <div class="policy-seg">${POLICY.map(([id, nm, tip]) =>
          `<button class="policy-btn ${curPol === id || (id === "continuous" && curPol === "always_on") ? "active" : ""}" data-pol="${id}"><b>${nm}</b><small>${tip}</small></button>`).join("")}</div>`;
    }

    if (u.mobility !== "fixed" && alts.length > 0) {
      html += `<div class="insp-section-lbl">${state.phase === "deploy" ? "移到预备阵地（也可以直接在地图上拖动）" : "转移阵地：撤收→机动→展开，期间不能开火"}</div>
        <div class="insp-row">
          <select id="insp-sel-alt" class="select-sm flex-1">${altOpts}</select>
          <button id="insp-btn-reloc" class="btn btn-xs ${state.phase === "deploy" ? "" : "btn-warn"}">${state.phase === "deploy" ? "移过去" : "转移 · 1 CP"}</button>
        </div>`;
    }

    if ((u.weapons || []).length) {
      const carryUsedMap = (state.meta && state.meta.carryIn && state.meta.carryIn.perLevelUsed) || {};
      html += `<details class="adv-weapons" ${state.openWeapons ? "open" : ""}><summary>射击规则（高级，一般不用改）</summary>`;
      (u.weapons || []).forEach((w) => {
        const wid = w.weaponId || w.id;
        const wl = w.whitelist || ["UAV", "CM", "BM", "AC_LOW"];
        const rds = w.rounds !== undefined ? (w.rounds < 0 ? "充足" : `${w.rounds}/${w.maxRounds}`) : (w.magazine || "充足");
        const plLim = w.perLevelLimit !== undefined && w.perLevelLimit !== null ? Number(w.perLevelLimit) : null;
        let quotaHtml = "";
        if (plLim !== null) {
          const remQ = w.remainingQuota !== undefined && w.remainingQuota !== null ? Number(w.remainingQuota) : Math.max(0, plLim - Number(carryUsedMap[wid] || 0));
          quotaHtml = `<div class="insp-row" style="font-size:11px;color:${remQ <= 0 ? "var(--danger)" : "var(--text-2)"};"><span>本关剩余配额 <strong>${remQ}/${plLim}</strong>${remQ <= 0 ? " · 已用完" : ""}</span></div>`;
        }
        html += `<div class="weapon-box">
          <div class="insp-row"><span class="weapon-name">${esc(w.name)}</span><span class="weapon-ammo">弹 ${rds}${w.reloadRemSec > 0 ? ` · 装填 ${w.reloadRemSec}s` : ""}</span></div>
          ${quotaHtml}
          <div class="insp-row"><span class="insp-label">什么时候开火</span>
            <select class="select-sm insp-w-rule" data-wid="${esc(wid)}">
              <option value="any" ${w.rule === "any" ? "selected" : ""}>见到就打</option>
              <option value="high_value_only" ${w.rule === "high_value_only" ? "selected" : ""}>只打高价值目标</option>
              <option value="ballistic_only" ${w.rule === "ballistic_only" ? "selected" : ""}>只打弹道导弹</option>
              <option value="hold_fire" ${w.rule === "hold_fire" ? "selected" : ""}>停火</option>
            </select>
          </div>
          <div class="insp-row"><span class="insp-label" data-tip="至少留几发不打，以备更危险的目标">保留弹数 <strong id="lbl-res-${esc(wid)}" style="color:var(--text);font-family:var(--font-mono);font-weight:400">${w.ammoReserve || 0}</strong></span>
            <input type="range" min="0" max="4" value="${w.ammoReserve || 0}" class="insp-w-res" data-wid="${esc(wid)}" />
          </div>
          <div class="insp-label">可以打哪些目标</div>
          <div class="tag-checks">
            ${["UAV", "CM", "BM", "AC_LOW"].map((tg) => `<label><input type="checkbox" class="insp-w-tag" data-wid="${esc(wid)}" value="${tg}" ${wl.includes(tg) ? "checked" : ""}/>${TAG_CN[tg]}</label>`).join("")}
            <label data-tip="先打一发，看结果再决定是否补射，更省弹"><input type="checkbox" class="insp-w-sls" data-wid="${esc(wid)}" ${w.shootLookShoot !== false ? "checked" : ""}/>打一发看一眼</label>
          </div>
          ${state.phase === "battle" && hasEmitter ? `<button id="insp-btn-burst" class="btn btn-xs" data-tip="强制全功率开机 15 秒刷新航迹，暴露度 +8%">短促扫描</button>` : ""}
        </div>`;
      });
      html += `</details>`;
    }
    if (state.phase === "deploy" && u.mobility !== "fixed") html += `<div class="card-note">提示：在地图上按住它拖动即可换位置。</div>`;
    body.innerHTML = html;
    bindInspectorEvents(u);
  }

  function bindInspectorEvents(u) {
    const det = document.querySelector("#insp-body .adv-weapons");
    if (det) det.addEventListener("toggle", () => { state.openWeapons = det.open; });
    document.querySelectorAll("#insp-body .policy-btn").forEach((b) => b.addEventListener("click", () => setPolicy(u, b.dataset.pol)));
    const burstBtn = $("insp-btn-burst");
    if (burstBtn) burstBtn.addEventListener("click", () => sendCommand({ type: "BurstScan", unitId: u.id, durationSec: 15 }));
    const relocBtn = $("insp-btn-reloc");
    if (relocBtn) relocBtn.addEventListener("click", () => relocateUnit(u, $("insp-sel-alt").value));
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

  async function setPolicy(u, pol) {
    if (state.phase === "deploy") { u.emissionPolicy = pol; await refreshCoverage(); renderRosterAndInspector(); }
    else await sendCommand({ type: "SetEmissionPolicy", unitId: u.id, policyId: pol });
  }

  async function relocateUnit(u, altId) {
    const ap = ((state.meta.deploy && state.meta.deploy.alternatePositions) || []).find((a) => a.id === altId);
    if (!ap) return;
    if (state.phase === "deploy") {
      u.pos = [ap.pos[0], ap.pos[1]];
      u.isExposed = false; u.carryExposure = 0;
      await refreshCoverage();
      renderRosterAndInspector();
    } else {
      await sendCommand({ type: "Relocate", unitId: u.id, alternatePositionId: altId });
      Toast.show({ kind: "warn", icon: "→", title: `${u.name} 开始转移`, text: "撤收、机动、展开期间不能开火" });
    }
  }

  function bestAltFor(u) {
    const alts = (state.meta.deploy && state.meta.deploy.alternatePositions) || [];
    const far = alts.filter((a) => Math.hypot(a.pos[0] - u.pos[0], a.pos[1] - u.pos[1]) > 1500);
    far.sort((a, b) => Math.hypot(a.pos[0] - u.pos[0], a.pos[1] - u.pos[1]) - Math.hypot(b.pos[0] - u.pos[0], b.pos[1] - u.pos[1]));
    return far[0];
  }

  // ───────────── 参谋建议 ─────────────
  function computeAdvice() {
    const out = [];
    const meta = state.meta;
    if (!meta) return out;
    if (state.phase === "deploy") {
      const kts = (meta.carryIn && meta.carryIn.knownTargets) || [];
      const unmoved = kts.filter((kt) => {
        const pu = state.placements.find((p) => Number(p.rosterId) === Number(kt.rosterId));
        return pu && Math.hypot(pu.pos[0] - kt.pos[0], pu.pos[1] - kt.pos[1]) <= 600;
      });
      if (unmoved.length) {
        out.push({ lv: "danger", text: `<b>${unmoved.map((k) => esc(k.name)).join("、")}</b> 还在昨晚暴露的位置，今夜会被巡航导弹专门攻击。`, actions: [["一键转移", () => $("btn-auto-relocate-exposed").click()]] });
      }
      const cov = state.coverage;
      if (cov && !cov.valid) out.push({ lv: "danger", text: `部署有冲突：${esc(cov.errors[0] || "")}`, actions: [] });
      if (cov && cov.stats) {
        const blind = cov.stats.blindFrac * 100;
        if (blind > 2.5) {
          const acts = state.activePreset !== "layered" ? [["换成推荐阵型", () => applyPreset("layered")]] : [];
          out.push({ lv: "warn", text: `还有 <b>${blind.toFixed(1)}%</b> 的低空盲区（地图上的红色斜线）。巡航导弹会沿西北河谷低飞，从盲区钻进来。把雷达、观察哨拖到山脊北侧可以消除它。`, actions: acts });
        }
      }
      if (!out.some((a) => a.lv === "danger" || a.lv === "warn")) {
        out.push({ lv: "ok", text: "部署看起来不错。准备好就开始守夜——开战后武器会<b>自动开火</b>，你只需要应对突发情况。", actions: [["开始守夜", () => startNightBattle(false)]] });
      }
      return out;
    }
    const snap = state.snapshot;
    if (!snap) return out;
    if (snap.isEnded) return [{ lv: "ok", text: "天亮了，本夜结束。", actions: [["查看战报", () => snap.battleReport && showReportModal(snap.battleReport)]] }];
    const tracks = snap.tracks || [];
    const structs = snap.structures || [];
    const near = tracks.filter((t) => structs.some((s) => !s.destroyed && Math.hypot(t.pos[0] - s.pos[0], t.pos[1] - s.pos[1]) < 8000));
    if (near.length && !snap.alert.on) {
      out.push({ lv: "danger", text: `<b>${near.length}</b> 个敌方目标正在逼近城区。<b>拉响防空警报</b>，让市民进入掩体。`, actions: [["拉响警报", () => sendCommand({ type: "ToggleCivilAlert", on: true })]] });
    }
    if (snap.alert.on && !tracks.length && snap.tick - state.lastThreatTick > 900) {
      out.push({ lv: "info", text: "空中暂时安全了。可以<b>解除警报</b>——一直拉响会让市民疲惫，下次就不那么配合了。", actions: [["解除警报", () => sendCommand({ type: "ToggleCivilAlert", on: false })]] });
    }
    (snap.units || []).forEach((u) => {
      if (u.emitter && u.emitter.armSilenced && !tracks.some((t) => t.tag === "ARM")) {
        out.push({ lv: "warn", text: `<b>${esc(u.name)}</b> 还在关机躲避，现在<b>看不见敌人</b>。危险已经过去，可以恢复。`, actions: [["恢复闪烁", () => setPolicy(u, "blink")], ["选中它", () => selectUnit(u)]] });
      }
    });
    const hot = (snap.units || []).filter((u) => u.exposure >= 55 && u.emitter && u.emitter.on && !u.relocation && isActiveState(u.deployState))
      .sort((a, b) => b.exposure - a.exposure).slice(0, 2);
    hot.forEach((u) => {
      const acts = [];
      if (u.emitter.policyId !== "blink") acts.push(["改为闪烁", () => setPolicy(u, "blink")]);
      acts.push(["关机隐蔽", () => setPolicy(u, "silent")]);
      const alt = u.mobility !== "fixed" ? bestAltFor(u) : null;
      if (alt && snap.cp.current > 0) acts.push(["转移阵地 · 1CP", () => relocateUnit(u, alt.id)]);
      out.push({ lv: u.exposure >= 70 ? "danger" : "warn", text: `<b>${esc(u.name)}</b> 暴露度 <b>${Math.round(u.exposure)}%</b>，敌人快定位到它了。超过 70% 会被记住，下一夜专门来打。`, actions: acts });
    });
    const pool = snap.ammoPool || {};
    Object.entries(pool).forEach(([k, v]) => {
      const init = state.ammoInitial[k];
      if (typeof v === "number" && v < 90000 && init && v / init < 0.3 && AMMO_UNIT[k]) {
        const defId = AMMO_UNIT[k];
        out.push({ lv: "warn", text: `<b>${AMMO_LABELS[k] || k}</b> 只剩 <b>${v}</b> 发。让它们只打导弹，无人机交给机枪。`, actions: [["只打导弹", () => {
          (snap.units || []).filter((u) => u.unitDefId === defId).forEach((u) => (u.weapons || []).forEach((w) =>
            sendCommand({ type: "SetTargetWhitelist", unitId: u.id, weaponId: w.weaponId || w.id, tags: ["CM", "BM", "AC_LOW"] })));
          Toast.show({ kind: "good", icon: "✓", title: "已设置：只打导弹和飞机" });
        }]] });
      }
    });
    if (!tracks.length && !out.length) {
      out.push({ lv: "info", text: "暂时没有敌情。可以<b>跳到下一波</b>节省时间。", actions: [["跳到下一波", () => skipToNextContact()]] });
    } else if (!out.length) {
      out.push({ lv: "ok", text: "武器正在自动迎击。留意暴露度和防空警报即可。", actions: [] });
    }
    const order = { danger: 0, warn: 1, info: 2, ok: 3 };
    return out.sort((a, b) => order[a.lv] - order[b.lv]).slice(0, 4);
  }

  function renderAdvisor(force) {
    const adv = computeAdvice();
    const sig = adv.map((a) => a.lv + a.text + a.actions.map((x) => x[0]).join()).join("|");
    if (!force && sig === state.advSig) return;
    state.advSig = sig;
    state.advActions = [];
    $("advisor-count").textContent = adv.filter((a) => a.lv === "danger" || a.lv === "warn").length ? `${adv.length} 条` : "";
    $("advisor-list").innerHTML = adv.map((a) => {
      const btns = a.actions.map(([label, fn]) => {
        state.advActions.push(fn);
        return `<button class="btn btn-xs ${a.lv === "danger" ? "btn-warn" : ""}" data-act="${state.advActions.length - 1}">${esc(label)}</button>`;
      }).join("");
      return `<div class="adv-item lv-${a.lv}"><div class="adv-text">${a.text}</div>${btns ? `<div class="adv-actions">${btns}</div>` : ""}</div>`;
    }).join("");
    $("advisor-list").querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", () => {
      const fn = state.advActions[Number(b.dataset.act)];
      if (fn) fn();
    }));
  }

  // ───────────── 战斗中 ─────────────
  async function sendCommand(payload) {
    if (state.phase !== "battle") return;
    const snap = await rawPost("/api/command", payload);
    if (snap && snap.tick !== undefined) applySnapshot(snap);
  }

  function selectUnit(u) { state.selectedUnitKey = unitKey(u); renderRosterAndInspector(); }

  function updateHud() {
    const snap = state.snapshot;
    const structs = (snap && snap.structures) || (state.meta && state.meta.structures) || [];
    const ok = structs.filter((s) => !s.destroyed).length;
    const set = (id, v) => {
      const b = $(id).querySelector("b");
      if (b.textContent !== String(v)) {
        b.textContent = v;
        $(id).classList.remove("bump"); void $(id).offsetWidth; $(id).classList.add("bump");
      }
    };
    set("hud-structs", `${ok}/${structs.length}`);
    set("hud-kills", state.tally.kills);
    set("hud-leaks", state.tally.leaks);
    set("hud-threats", snap ? (snap.tracks || []).length : 0);
  }

  function handleEventFeedback(ev) {
    const fx = ev.fx || {};
    if (fx.kind === "hit") {
      state.tally.kills++;
      Toast.show({ kind: "good", icon: "✓", title: "拦截成功", key: "kill", ttl: 2400 });
      hint("firstKill");
    } else if (fx.kind === "impact_hit") {
      state.tally.leaks++;
      Toast.show({ kind: "bad", icon: "!", title: ev.text, ttl: 4200 });
      if (fx.pos) state.pulses.push({ pos: fx.pos, t0: performance.now(), color: "danger" });
      hint("firstLeak", fx.pos);
    } else if (ev.type === "StructureDestroyed") {
      Toast.show({ kind: "bad", icon: "!", title: ev.text, ttl: 5000 });
    } else if (ev.type === "EarlyWarning") {
      Toast.show({ kind: "warn", icon: "›", title: "空袭预警", text: ev.text.replace(/^.*?：/, ""), ttl: 4500 });
    } else if (ev.type === "ArmThreatDetected" || ev.type === "KnownTargetAdded") {
      Toast.show({ kind: "bad", icon: "!", title: ev.text, ttl: 4500 });
    } else if (ev.type === "AmmoDepleted") {
      Toast.show({ kind: "warn", icon: "!", title: ev.text, ttl: 4000 });
    } else if (ev.type === "DecoyIdentified") {
      Toast.show({ kind: "good", icon: "✓", title: "识破诱饵，自动停火省弹", key: "decoy" });
    }
  }

  function applySnapshot(snap) {
    const firstTracks = state.snapshot && !(state.snapshot.tracks || []).length && (snap.tracks || []).length;
    state.snapshot = snap;
    if ((snap.tracks || []).length) state.lastThreatTick = snap.tick;
    $("world-clock").textContent = snap.clockStr;
    const pct = Math.min(100, (snap.timeWorldSec / Math.max(1, snap.durationWorldSec)) * 100);
    $("clock-progress").style.width = `${pct.toFixed(1)}%`;
    const remMin = Math.max(0, Math.round((snap.durationWorldSec - snap.timeWorldSec) / 60));
    $("tick-readout").textContent = `距拂晓 ${Math.floor(remMin / 60)}h${String(remMin % 60).padStart(2, "0")}m`;
    setCp(snap.cp.current, snap.cp.initial);

    const alBtn = $("btn-alert-toggle");
    const shPct = Math.round((snap.alert.shelteredFrac || 0) * 100);
    alBtn.textContent = snap.alert.on ? `防空警报：开 · 已掩蔽 ${shPct}%` : "防空警报：关";
    alBtn.className = `btn btn-sm battle-only ${snap.alert.on ? "btn-alert-on" : ""}`;
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
      handleEventFeedback(ev);
    });
    while (logBox.children.length > 90) logBox.removeChild(logBox.lastChild);

    renderStructuresAndAmmo();
    renderRosterAndInspector();
    updateHud();
    renderAdvisor();

    if (firstTracks) hint("firstTrack");
    if ((snap.units || []).some((u) => u.exposure >= 55)) hint("firstExposure");

    if (snap.activeChoice) { setSpeed(0); showChoiceModal(snap.activeChoice); }
    else hideChoiceModal();

    if (snap.isEnded && snap.battleReport) { setSpeed(0); setStep("report"); showReportModal(snap.battleReport); }
  }

  function showChoiceModal(ch) {
    const modal = $("choice-modal");
    if (!modal.classList.contains("hidden")) return;
    Coach.stop(false);
    modal.classList.remove("hidden");
    $("choice-title").textContent = ch.title;
    $("choice-unit-subtitle").textContent = `被锁定的雷达：${ch.subjectUnitName}`;
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

  // 战报字段适配：后端 compute_battle_report 返回 perEnemy / weightedLossFrac / defenseCostMusd 等
  function normReport(rep) {
    const per = (rep.perEnemy || []).map((r) => ({
      name: r.name, isDecoy: Boolean(r.isDecoy), spawned: r.spawned || 0, intercepted: r.killed || 0,
      penetrated: r.leaked || 0, interceptRate: Math.round((r.interceptRate || 0) * 100),
    }));
    const real = per.filter((r) => !r.isDecoy);
    const spawned = real.reduce((n, r) => n + r.spawned, 0);
    const killed = real.reduce((n, r) => n + r.intercepted, 0);
    return {
      per, spawned, killed,
      lossPct: Math.round((rep.weightedLossFrac || 0) * 1000) / 10,
      ratePct: Math.round((rep.nonDecoyInterceptRate !== undefined ? rep.nonDecoyInterceptRate : (spawned ? killed / spawned : 1)) * 100),
      wasted: (rep.trust && rep.trust.wastedWeapons) || [],
      trust: (rep.trust && rep.trust.applied) || 0,
      cost: rep.defenseCostMusd || 0, saved: rep.potentialLossAvoidedMusd || 0,
    };
  }

  function buildLessons(rep, n) {
    const L = [];
    if (rep.survived === false) L.push(`<b>防线失守</b>（${esc(rep.endReasonText || "")}）。下一次先保证热电厂周围有足够的火力和探测。`);
    const types = n.per.filter((r) => r.penetrated > 0 && !r.isDecoy).sort((a, b) => b.penetrated - a.penetrated);
    if (!types.length && n.lossPct === 0) L.push("设施<b>毫发无损</b>，干得漂亮。");
    types.slice(0, 2).forEach((r) => {
      let tip = "";
      if (/巡航|CM|Kh|口径|kh/.test(r.name)) tip = "巡航导弹贴着河谷低飞——用观察哨、声学哨填补山脊和河谷里的雷达盲区。";
      else if (/无人|Shahed|沙赫德|Geran|天竺葵|shahed/.test(r.name)) tip = "无人机数量多但速度慢，在它们的来路上多放几组机动火力。";
      else tip = "看看它们是从哪个方向进来的，在那条路上加强探测和火力。";
      L.push(`<b>${esc(r.name)}</b> 突防了 ${r.penetrated} 次。${tip}`);
    });
    if (n.wasted.length) L.push(`<b>${n.wasted.map(esc).join("、")}</b> 把昂贵导弹打在了廉价目标上。在“射击规则”里让它们只打导弹，可以省弹也保住公信力。`);
    const exposed = rep.exposedPositions || [];
    if (exposed.length) L.push(`<b>${exposed.map((k) => esc(k.name)).join("、")}</b> 暴露过高，敌人已经记住了位置。下一夜开战前记得转移。`);
    if (!L.length) L.push("整体表现稳定。下一夜敌人会更多，留意弹药库存。");
    return L;
  }

  function showReportModal(rep) {
    const n = normReport(rep);
    $("report-modal").classList.remove("hidden");
    $("report-title").textContent = `第 ${rep.nightIndex} 夜 · ${rep.survived === false ? "防线失守" : "守住了"}`;
    const rEl = $("report-rating");
    rEl.textContent = rep.rating;
    rEl.className = `rating-letter grade-${String(rep.rating).charAt(0)}`;
    $("report-score").textContent = `${rep.compositeScore} 分`;
    const isLast = rep.nightIndex >= ((state.meta && state.meta.totalNights) || 2);
    $("btn-next-night").classList.toggle("hidden", isLast || rep.canAdvanceToNight2 === false);
    const rows = n.per.map((r) =>
      `<tr><td>${esc(r.name)}${r.isDecoy ? ' <span style="color:var(--text-muted)">(诱饵)</span>' : ""}</td><td>${r.spawned}</td><td>${r.intercepted} <span style="color:var(--text-muted)">(${r.interceptRate}%)</span><span class="rate-bar"><i style="width:${Math.min(100, r.interceptRate)}%"></i></span></td><td style="color:${r.penetrated > 0 && !r.isDecoy ? "var(--danger)" : "inherit"}">${r.penetrated}</td></tr>`).join("");
    const exposed = rep.exposedPositions || [];
    const kts = exposed.map((k) => `${esc(k.name)}(#${k.rosterId}, 暴露 ${k.exposure}%)`).join("、") || "无，全员隐蔽良好";
    $("report-body").innerHTML = `
      <div>
        <div class="report-sec-title">复盘要点</div>
        <div class="lesson-list">${buildLessons(rep, n).map((l) => `<div class="lesson">${l}</div>`).join("")}</div>
      </div>
      <div class="report-grid">
        <div class="stat-card"><div class="lbl">设施损失率（越低越好）</div><div class="val">${n.lossPct}%</div></div>
        <div class="stat-card"><div class="lbl">拦截率（不含诱饵）</div><div class="val">${n.ratePct}% <span style="font-size:11px;color:var(--text-muted)">${n.killed}/${n.spawned}</span></div></div>
        <div class="stat-card"><div class="lbl">花掉的弹药 / 避免的损失</div><div class="val">$${n.cost.toFixed(1)}M / $${n.saved.toFixed(1)}M</div></div>
        <div class="stat-card"><div class="lbl">公信力变化</div><div class="val" style="color:${n.trust >= 0 ? "var(--ok)" : "var(--danger)"}">${n.trust >= 0 ? "+" : ""}${n.trust}</div></div>
      </div>
      <table class="report-table">
        <thead><tr><th>来袭目标</th><th>数量</th><th>拦截</th><th>突防命中</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="warning-card">
        <div class="warning-title">带到下一夜：暴露的阵地 (${exposed.length} 处)</div>
        <div class="warning-desc">${kts}${exposed.length && !isLast ? "。下一夜敌人会专门攻击这些坐标。" : ""}</div>
      </div>`;
  }

  function setSpeed(spd) {
    state.speed = Number(spd);
    document.querySelectorAll("#speed-btn-group .seg-btn[data-speed]").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.speed) === state.speed);
    });
  }

  async function skipToNextContact() {
    if (state.phase !== "battle" || state.skipping || !state.snapshot || state.snapshot.isEnded) return;
    state.skipping = true; state.stepBusy = true;
    setSpeed(0);
    try {
      await withBusy("快进到下一波…", async () => {
        for (let i = 0; i < 120; i++) {
          const snap = await rawPost("/api/step", { ticks: 90 });
          if (!snap || snap.tick === undefined) break;
          applySnapshot(snap);
          if (snap.isEnded || snap.activeChoice || (snap.tracks || []).length || (snap.events || []).some((e) => e.level === "danger")) break;
        }
      });
    } finally { state.skipping = false; state.stepBusy = false; }
    if (state.snapshot && !state.snapshot.isEnded && !state.snapshot.activeChoice && !Coach.active) setSpeed(1);
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

  function fitCanvas() {
    const wrap = $("canvas-wrapper");
    const size = Math.max(240, Math.min(wrap.clientWidth, wrap.clientHeight) - 12);
    const v = canvas._view;
    if (v && v.width === Math.floor(size) && v.dpr === Math.min(2.5, window.devicePixelRatio || 1)) return;
    window.TacticalRenderer.resize(canvas, size, size);
  }

  // ───────────── 地图拾取与悬停说明 ─────────────
  function canvasXY(e) {
    const rect = canvas.getBoundingClientRect();
    return [e.clientX - rect.left, e.clientY - rect.top];
  }
  function worldToCanvas(pos, alt) {
    const view = window.TacticalRenderer.getView(canvas);
    const elev = window.TacticalRenderer.sampleElevation(state.meta, pos[0], pos[1]);
    return window.TacticalRenderer.worldToScreen(pos[0], pos[1], alt || 0, view, state.viewMode, elev);
  }
  function pickNearest(list, posOf, px, py, radius) {
    let best = null, bestD = radius;
    list.forEach((it) => {
      const p = posOf(it);
      const d = Math.hypot(p.x - px, p.y - py);
      if (d < bestD) { bestD = d; best = it; }
    });
    return best;
  }
  function pickUnitAt(e, r) {
    const [px, py] = canvasXY(e);
    return pickNearest(getActiveUnits(), (u) => worldToCanvas(u.pos), px, py, r);
  }

  function showMapTip(e) {
    const tip = $("map-tip");
    if (!state.meta || state.draggingUnit) { tip.classList.add("hidden"); return; }
    const [px, py] = canvasXY(e);
    let html = "";
    const u = pickUnitAt(e, 18);
    if (u) {
      const info = UNIT_INFO[u.unitDefId] || { role: CAT_ROLE[u.category] || "", desc: "" };
      const rng = rangeOf(u), det = u.detectionRangeM || 0;
      const exp = Math.round(u.exposure !== undefined ? u.exposure : (u.carryExposure || 0));
      html = `<div class="mt-title">${esc(u.name)}<span class="mt-kind">${esc(info.role)}</span></div>
        <div>${info.desc}</div>
        <div class="mt-row">${rng ? `射程 ${(rng / 1000).toFixed(1)} km` : ""}${rng && det ? " · " : ""}${det ? `探测 ${(det / 1000).toFixed(1)} km` : ""}${exp ? ` · 暴露 ${exp}%` : ""}</div>
        <div class="mt-hint">${state.phase === "deploy" && u.mobility !== "fixed" ? "按住拖动换位置 · 点击查看射程" : "点击选中，在左侧调整"}</div>`;
    } else {
      const structs = (state.snapshot && state.snapshot.structures) || state.meta.structures || [];
      const s = pickNearest(structs, (x) => worldToCanvas(x.pos), px, py, 18);
      if (s) {
        const typ = (state.meta.structures.find((m) => m.id === s.id) || {}).type;
        html = `<div class="mt-title">${esc(s.name)}<span class="mt-kind">要保护的设施</span></div>
          <div>${STRUCT_INFO[typ] || "需要保护的城市设施。"}</div>
          <div class="mt-row">耐久 ${s.hp}/${s.maxHp}${s.destroyed ? " · 已摧毁" : ""}</div>`;
      } else if (state.snapshot) {
        const t = pickNearest(state.snapshot.tracks || [], (x) => worldToCanvas(x.pos, 140), px, py, 16);
        if (t) {
          const kind = t.identifiedAsDecoy ? "诱饵（不用管）" : (t.quality >= 3 || t.classified ? (TAG_CN[t.tag] || t.tag) : "类型未知");
          html = `<div class="mt-title">敌方目标 T-${t.id}<span class="mt-kind">${esc(kind)}</span></div>
            <div>${Q_CN[t.quality] || ""}${t.quality < 2 ? "——还不能开火，需要更近或更好的探测。" : "——射程内的武器会自动开火。"}</div>
            <div class="mt-row">速度 ${Math.round((t.speedMps || 0) * 3.6)} km/h</div>`;
        }
      }
    }
    if (!html) { tip.classList.add("hidden"); return; }
    tip.innerHTML = html;
    tip.classList.remove("hidden");
    const wrap = $("canvas-wrapper").getBoundingClientRect();
    const cr = canvas.getBoundingClientRect();
    let x = cr.left - wrap.left + px + 16, y = cr.top - wrap.top + py + 14;
    if (x + tip.offsetWidth > wrap.width - 8) x = cr.left - wrap.left + px - tip.offsetWidth - 16;
    if (y + tip.offsetHeight > wrap.height - 8) y = wrap.height - tip.offsetHeight - 8;
    tip.style.left = `${x}px`; tip.style.top = `${y}px`;
  }

  // ───────────── 预设 / 开战 ─────────────
  async function applyPreset(name) {
    state.activePreset = name;
    document.querySelectorAll(".btn-preset").forEach((x) => x.classList.toggle("active", x.dataset.preset === name));
    state.meta.currentPlacements = JSON.parse(JSON.stringify((state.meta.presets && state.meta.presets[name]) || []));
    applyLevelMeta(state.meta);
    await refreshCoverage();
  }

  async function startNightBattle(skipConfirm = false) {
    if (state.phase !== "deploy") return;
    const kts = (state.meta && state.meta.carryIn && state.meta.carryIn.knownTargets) || [];
    if (!skipConfirm && state.meta && state.meta.nightIndex > 1 && kts.length > 0) {
      const unmoved = kts.filter((kt) => {
        const pu = state.placements.find((p) => Number(p.rosterId) === Number(kt.rosterId));
        if (!pu || !pu.pos || !kt.pos) return false;
        return Math.hypot(pu.pos[0] - kt.pos[0], pu.pos[1] - kt.pos[1]) <= 600.0;
      });
      if (unmoved.length > 0 && typeof window.confirm === "function") {
        const names = unmoved.map((k) => `${k.name}#${k.rosterId}`).join("、");
        if (!window.confirm(`${names} 还在昨晚暴露的位置（未移动超过 600 米），今夜会被专门攻击。仍然开始吗？`)) return;
      }
    }
    Coach.stop(false);
    const snap = await apiPost("/api/start_night", { placements: state.placements, bot: $("sel-bot-mode").value }, "正在初始化夜间战场…");
    setPhase("battle");
    $("deploy-controls-section").classList.add("hidden");
    applySnapshot(snap);
    state.selectedUnitKey = snap.units.length ? snap.units[0].id : null;
    renderRosterAndInspector();
    setSpeed(1);
    hint("battleStart");
  }

  // ───────────── 新手引导：简报、部署教程、战斗提示 ─────────────
  function showBriefing() {
    const meta = state.meta;
    if (meta) {
      $("brief-title").textContent = `第 ${meta.nightIndex} 夜 · ${meta.levelName}`;
      $("brief-story").textContent = meta.briefing || "";
      const names = (meta.structures || []).map((s) => s.name).join("、");
      $("brief-goal").innerHTML = `保护<b>${esc(names)}</b>，从 22:00 撑到 <b>06:00 拂晓</b>。设施受损越少，评级越高。`;
    }
    $("briefing-modal").classList.remove("hidden");
  }
  function closeBriefing() { $("briefing-modal").classList.add("hidden"); LS.set("nw_seen_brief", "1"); }

  function rectFromWorld(points, padPx) {
    if (!state.meta) return null;
    const cr = canvas.getBoundingClientRect();
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    points.forEach((pt) => {
      const p = worldToCanvas(pt);
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x); y1 = Math.max(y1, p.y);
    });
    const pad = padPx || 20;
    return { left: cr.left + x0 - pad, top: cr.top + y0 - pad, width: x1 - x0 + pad * 2, height: y1 - y0 + pad * 2 };
  }

  function runDeployTutorial() {
    LS.set("nw_hints_off", "");
    state.hintsSeen = {};
    const meta = state.meta;
    const sel = () => state.placements.find((p) => p.rosterId === state.selectedUnitKey) || state.placements[0];
    Coach.run([
      {
        title: "这三个金色方块是你要保护的设施",
        text: "热电厂、变电站和水厂。敌人的无人机和导弹会冲着它们来。<b>热电厂最重要</b>——它一倒，城市就断电。",
        target: () => rectFromWorld((meta.structures || []).map((s) => s.pos), 34),
      },
      {
        title: "敌人从这两个方向来",
        text: "<b>东面</b>是成群的无人机，<b>西北</b>是沿河谷低飞的巡航导弹。注意地图北边的<b>山脊</b>：它会挡住雷达看低空。",
        target: () => rectFromWorld([[600, 13600], [19400, 18600]], 10),
      },
      {
        title: "这些方框是你的防空单位",
        text: "带<b>半圆</b>的是火力单元（负责开火），带<b>雷达弧线</b>的是侦察单元（负责发现）。<b>按住拖动</b>就能换位置；点一下会显示它的射程圈。",
        target: () => { const u = sel(); return u ? rectFromWorld([u.pos], 34) : null; },
        onEnter: () => { const u = sel(); if (u) { state.selectedUnitKey = u.rosterId; renderRosterAndInspector(); } },
      },
      {
        title: "红色斜线 = 雷达盲区",
        text: "山脊后面、河谷里，雷达看不到低空。这两个数字告诉你覆盖得怎么样：<b>雷达覆盖</b>越高越好，<b>低空盲区</b>越低越好。",
        target: "#coverage-summary",
      },
      {
        title: "懒得摆？选一个阵型",
        text: "<b>推荐</b>阵型已经把雷达推过山脊，盲区很少。也可以试试<b>抱团</b>，看看盲区会变得多大。",
        target: ".preset-row",
      },
      {
        title: "右边的参谋会给你建议",
        text: "不知道该干什么时，看这里。每条建议都带按钮，<b>点一下就执行</b>。",
        target: "#advisor-card",
      },
      {
        title: "准备好了就开战",
        text: "开战后时间会自动走，武器会<b>自动开火</b>。你只需要在关键时刻做决定。",
        target: "#btn-start-night",
        nextLabel: "知道了",
      },
    ], { onDone: (done) => { if (!done) LS.set("nw_hints_off", "1"); } });
  }

  // 战斗中的一次性提示：首次出现时暂停并聚焦
  function hint(key, pos) {
    if (LS.get("nw_hints_off") === "1") return;
    state.hintsSeen = state.hintsSeen || {};
    if (state.hintsSeen[key] || Coach.active || state.skipping && key !== "firstTrack") return;
    const H = {
      battleStart: {
        title: "时间开始走了",
        text: "敌机要飞一会儿才到。<b>空格</b>暂停，<b>1 / 2 / 3</b> 调速；没有敌情时点<b>跳到下一波</b>。",
        target: "#time-ctrl", pause: false,
      },
      firstTrack: {
        title: "发现敌机",
        text: "箭头就是敌机，颜色表示我们<b>锁定它的程度</b>：灰 → 黄 → 橙 → 红。到<b>橙色</b>时，射程内的武器会<b>自动开火</b>。鼠标放在箭头上可以看它是什么。",
        target: () => {
          const t = (state.snapshot.tracks || [])[0];
          if (!t) return null;
          const cr = canvas.getBoundingClientRect(); const p = worldToCanvas(t.pos, 140);
          return { left: cr.left + p.x - 40, top: cr.top + p.y - 40, width: 80, height: 80 };
        },
        pause: true,
      },
      firstLeak: {
        title: "有敌机突防了",
        text: "看看右边的<b>参谋建议</b>：拉响防空警报能减少伤亡。如果它是从盲区钻进来的，下一夜要调整部署。",
        target: "#advisor-card", pause: true,
      },
      firstExposure: {
        title: "雷达快暴露了",
        text: "雷达开机越久，敌人越容易定位它。参谋建议你<b>改为闪烁、关机或转移</b>——点建议里的按钮即可。",
        target: "#advisor-card", pause: true,
      },
    };
    const h = H[key];
    if (!h) return;
    if (typeof h.target === "function" && !h.target()) return;
    state.hintsSeen[key] = true;
    const prev = state.speed || 1;
    if (h.pause) setSpeed(0);
    Coach.run([{ title: h.title, text: h.text, target: h.target, nextLabel: h.pause ? "继续" : "知道了" }], {
      onDone: () => { if (h.pause && state.phase === "battle" && !(state.snapshot && state.snapshot.activeChoice)) setSpeed(prev); },
    });
  }

  // ───────────── 事件绑定 ─────────────
  function setViewMode(mode) {
    state.viewMode = mode;
    document.querySelectorAll("#view-seg .seg-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === mode));
  }
  function toggleViewMode() { setViewMode(state.viewMode === "command" ? "live25d" : "command"); }

  function bindGlobalEvents() {
    document.querySelectorAll("#speed-btn-group .seg-btn[data-speed]").forEach((b) =>
      b.addEventListener("click", () => setSpeed(Number(b.dataset.speed) === 0 && state.speed === 0 ? 1 : Number(b.dataset.speed))));
    $("btn-skip").addEventListener("click", skipToNextContact);
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
      closeMore();
      if (state.phase === "deploy") await startNightBattle(true);
      await sendCommand({ type: "TriggerArmChoiceDemo" });
    });
    $("btn-reset-game").addEventListener("click", () => { closeMore(); initGame(1, true); });
    $("btn-restart-tutorial").addEventListener("click", async () => {
      closeMore();
      if (state.phase !== "deploy") await initGame(1, true);
      runDeployTutorial();
    });
    $("btn-help").addEventListener("click", showBriefing);
    $("btn-more").addEventListener("click", (e) => { e.stopPropagation(); $("more-dd").classList.toggle("open"); });
    document.addEventListener("click", (e) => { if (!$("more-dd").contains(e.target)) closeMore(); });
    $("btn-clear-log").addEventListener("click", () => { $("event-log-list").innerHTML = ""; });
    $("map-hint-x").addEventListener("click", () => $("map-hint").classList.add("hidden"));

    $("btn-brief-skip").addEventListener("click", () => { closeBriefing(); LS.set("nw_hints_off", ""); });
    $("btn-brief-tutorial").addEventListener("click", async () => {
      closeBriefing();
      if (state.phase !== "deploy") await initGame(1, true);
      runDeployTutorial();
    });

    document.querySelectorAll(".btn-preset").forEach((b) => b.addEventListener("click", () => applyPreset(b.dataset.preset)));

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
      applyLevelMeta(await apiPost("/api/next_night", {}, "正在结转到下一夜…")); await refreshCoverage();
    });

    canvas.addEventListener("mousedown", (e) => {
      const best = pickUnitAt(e, 18);
      if (best) {
        state.selectedUnitKey = unitKey(best);
        if (state.phase === "deploy" && best.mobility !== "fixed") {
          state.draggingUnit = best;
          canvas.classList.add("grabbing");
          $("map-tip").classList.add("hidden");
        }
        renderRosterAndInspector();
      }
    });
    canvas.addEventListener("mousemove", (e) => {
      if (!state.meta) return;
      const [px, py] = canvasXY(e);
      const view = window.TacticalRenderer.getView(canvas);
      const pt = window.TacticalRenderer.screenToWorld(px, py, view, state.viewMode);
      const elev = Math.round(window.TacticalRenderer.sampleElevation(state.meta, pt[0], pt[1]));
      const col = String.fromCharCode(65 + Math.min(7, Math.floor(pt[0] / 2500)));
      const row = 8 - Math.min(7, Math.floor(pt[1] / 2500));
      $("hover-telemetry").textContent = `方格 ${col}${row} · X ${(pt[0] / 1000).toFixed(2)} km · Y ${(pt[1] / 1000).toFixed(2)} km · 海拔 ${elev} m`;
      if (state.draggingUnit && state.phase === "deploy") {
        state.draggingUnit.pos = [Math.round(pt[0]), Math.round(pt[1])];
        return;
      }
      const hov = pickUnitAt(e, 18);
      state.hoverUnitKey = hov ? unitKey(hov) : null;
      canvas.classList.toggle("can-grab", Boolean(hov && state.phase === "deploy" && hov.mobility !== "fixed"));
      canvas.classList.toggle("can-select", Boolean(hov) && !(state.phase === "deploy" && hov.mobility !== "fixed"));
      showMapTip(e);
    });
    canvas.addEventListener("mouseleave", () => { state.hoverUnitKey = null; $("map-tip").classList.add("hidden"); });
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
        state.activePreset = "custom";
        document.querySelectorAll(".btn-preset").forEach((x) => x.classList.remove("active"));
        await refreshCoverage();
        renderRosterAndInspector();
      }
    });
    window.addEventListener("keydown", (e) => {
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (e.code === "Escape") { if (Coach.active) Coach.stop(false); closeMore(); if (!$("briefing-modal").classList.contains("hidden")) closeBriefing(); return; }
      if (e.code === "Space" && state.phase === "battle") { e.preventDefault(); setSpeed(state.speed > 0 ? 0 : 1); }
      else if (e.code === "Tab") { e.preventDefault(); toggleViewMode(); }
      else if (e.code === "KeyN") skipToNextContact();
      else if (state.phase === "battle" && ["Digit1", "Digit2", "Digit3"].includes(e.code)) {
        setSpeed({ Digit1: 1, Digit2: 4, Digit3: 8 }[e.code]);
      }
    });
    if (window.ResizeObserver) new ResizeObserver(fitCanvas).observe($("canvas-wrapper"));
    window.addEventListener("resize", fitCanvas);
  }
  function closeMore() { $("more-dd").classList.remove("open"); }

  // 调试/截图辅助：?demo=battle&ticks=600&view=live25d&god=1&bot=smart_blink&tutorial=0
  async function runDemoFromUrl() {
    const q = new URLSearchParams(location.search);
    if (q.get("view") === "live25d") setViewMode("live25d");
    if (q.get("god") === "1") { state.godView = true; $("chk-god-view").checked = true; }
    if (q.get("demo") === "battle") {
      LS.set("nw_seen_brief", "1"); LS.set("nw_hints_off", "1");
      if (q.get("bot")) $("sel-bot-mode").value = q.get("bot");
      await startNightBattle(true);
      setSpeed(0);
      // 后端单次 step 有上限，分批推进直到目标 tick 或夜晚结束
      let left = Number(q.get("ticks") || 600);
      while (left > 0) {
        const n = Math.min(left, 7200);
        const snap = await rawPost("/api/step", { ticks: n });
        applySnapshot(snap);
        left -= n;
        if (!snap || snap.isEnded || snap.activeChoice) break;
      }
      return;
    }
    if (q.get("tutorial") === "1") { runDeployTutorial(); return; }
    if (q.get("brief") === "1" || !LS.get("nw_seen_brief")) showBriefing();
  }

  bindGlobalEvents();
  fitCanvas();
  setPhase("deploy");
  requestAnimationFrame(animLoop);
  initGame(1, true).then(runDemoFromUrl);
})();
