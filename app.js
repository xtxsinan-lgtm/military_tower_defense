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
    openDrawerIndex: 0, inspectorOpen: true,
  };
  const DRAWER_META = {
    1: { code: "D1", title: "战前部署与阵型沙盘" },
    2: { code: "D2", title: "防空武器与雷达编制" },
    3: { code: "D3", title: "火控纪律与电磁条令" },
    4: { code: "D4", title: "空袭情报与来袭走廊" },
    5: { code: "D5", title: "城市电网与保卫目标" },
    6: { code: "D6", title: "导弹库存与战备补给" },
    7: { code: "D7", title: "值班作战室与战况日志" },
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
  const FRIENDLY_NAMES = {
    mobile_fire_team: "皮卡高射机枪组",
    iris_t_sls: "IRIS‑T 近程导弹车",
    nasams: "NASAMS 中程防空导弹",
    soviet_mid_range_radar: "苏制警戒雷达站",
    acoustic_post: "声学听音哨",
    visual_observer: "目视观察哨",
  };
  const WEAPON_NAMES = {
    mobile_fire_team_gun: "双联 12.7mm 高射机枪",
    iris_t_sls_missile: "IRIS‑T 红外近程导弹",
    nasams_missile: "AIM‑120 中程防空导弹",
  };
  const UNIT_INFO = {
    mobile_fire_team: {
      role: "皮卡高射机枪",
      weaponSpec: "双联 12.7mm 高射机枪 + 探照灯",
      targetRole: "专打低慢无人机 · 机枪弹药无限",
      desc: "四驱皮卡架设双联重机枪与大功率探照灯。<b>子弹无限</b>，专门前推堵截东面成群的廉价无人机，替导弹省弹药。自己<b>没有雷达</b>，靠雷达或暗哨发现目标后开灯扫射。",
    },
    iris_t_sls: {
      role: "近程防空导弹",
      weaponSpec: "IRIS‑T 红外近程防空导弹（12 km）",
      targetRole: "专拦巡航导弹 · 红外被动不暴露",
      desc: "高命中率防空导弹，不发射雷达波（<b>不会暴露位置</b>）。<b>全关导弹数量有限</b>，强烈建议设为<b>“省弹：只打导弹”</b>，别浪费在廉价无人机上。",
    },
    nasams: {
      role: "主力中程防空",
      weaponSpec: "AIM‑120 中程防空导弹（25 km）+ 火控雷达",
      targetRole: "防空网核心主力 · 覆盖全城",
      desc: "你的头号主力防空武器，射程覆盖大半个战区。<b>自带火控雷达，开机越久越容易暴露</b>（满 70% 会招来反辐射导弹猎杀），注意用闪烁/静默规避。",
    },
    soviet_mid_range_radar: {
      role: "远程警戒雷达",
      weaponSpec: "150 km 区域搜索雷达（无武装）",
      targetRole: "远距搜捕敌机 · 引导全场防空武器开火",
      desc: "自己不能开火，但能远距离发现敌机并替防空武器指示目标。<b>北山脊会挡住它看低空</b>；开机也会积累暴露度。",
    },
    acoustic_post: {
      role: "被动听音暗哨",
      weaponSpec: "电线杆麦克风阵列（无武装 · 自动工作）",
      targetRole: "5 km 听声辨位 · 零暴露 · 无视山脊遮挡",
      desc: "靠<b>听发动机声音</b>发现附近低空无人机，<b>绝对不会暴露</b>。战前摆在盲区即可，<b>开战后全自动报信，无需手动操作</b>。",
    },
    visual_observer: {
      role: "被动目视暗哨",
      weaponSpec: "光学 / 热像观察哨（无武装 · 自动工作）",
      targetRole: "5 km 目视盯梢 · 零暴露 · 填补河谷盲区",
      desc: "靠<b>眼睛与热像仪</b>发现低空目标，<b>绝对不会暴露</b>。适合塞进北山脊后的河谷盲区，<b>开战后全自动报信，无需手动操作</b>。",
    },
  };
  const CAT_ROLE = { fire: "防空武器", sensor: "雷达/暗哨", ew: "电子战", deception: "诱饵" };
  const STRUCT_INFO = {
    power_plant: "全城供电核心（<b>权重×5 · 头号保卫目标</b>）。一旦被炸毁，全城立即断电瘫痪。",
    substation: "电网输电枢纽（<b>权重×3 · 重点保卫目标</b>）。被毁会切断下游供电，防空阵地转入备用电池。",
    water_plant: "城市民生供水设施（<b>权重×2 · 保卫目标</b>）。西北河谷低飞的巡航导弹常偷袭这里。",
  };
  const STRUCT_ROLE = {
    power_plant: "供电核心",
    substation: "电网枢纽",
    water_plant: "城市供水",
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
      const weapons = (c.weapons || []).map((w) => Object.assign({}, w, {
        name: WEAPON_NAMES[w.id || w.weaponId] || w.name || w.id,
        rule: w.rule || "any",
        whitelist: (w.whitelist || ["UAV", "CM", "BM", "AC_LOW"]).slice(),
        ammoReserve: w.ammoReserve || 0,
        shootLookShoot: w.shootLookShoot !== false,
      }));
      return Object.assign({}, p, {
        name: FRIENDLY_NAMES[p.unitDefId] || p.name || c.name || p.unitDefId,
        category: p.category || c.category || "fire",
        hasRadar: Boolean(c.hasRadar), mobility: p.mobility || c.mobility,
        detectionRangeM: c.radarRangeM || c.detectionRangeM || c.selfAcquisitionRangeM || 0,
        weapons,
      });
    });
    const defaultUnit = state.placements.find((p) => p.unitDefId === "nasams")
      || state.placements.find((p) => p.category === "fire")
      || state.placements[0];
    state.selectedUnitKey = defaultUnit ? defaultUnit.rosterId : null;
    state.ammoInitial = Object.assign({}, (meta.carryIn && meta.carryIn.ammoPool) || {});
    $("level-title").textContent = meta.levelName;
    $("level-title").title = meta.briefing || "";
    $("night-badge").textContent = `第 ${meta.nightIndex} 夜 / 共 ${meta.totalNights} 夜`;
    $("date-weather-badge").textContent = `${meta.date} · ${meta.weather === "clear" ? "晴" : meta.weather}`;
    $("trust-badge").textContent = `${meta.trustScore}`;
    $("world-clock").textContent = "22:00:00";
    $("tick-readout").textContent = "战前准备";
    $("clock-progress").style.width = "0%";
    $("step-goal").textContent = `保卫目标：★ 热电厂 · 中心变电站 · 水厂（撑到 06:00）`;
    setCp(meta.commandPointsPerNight, meta.commandPointsPerNight);
    $("deploy-controls-section").classList.remove("hidden");
    $("report-modal").classList.add("hidden");
    $("choice-modal").classList.add("hidden");
    $("btn-alert-toggle").textContent = "防空警报：关";
    $("btn-alert-toggle").className = "btn btn-sm battle-only";
    setRadio(meta.nightIndex > 1
      ? "第 2 夜：昨晚暴露的防空阵地已被敌人记住，开战前先把它们挪走。"
      : "战前部署：把【皮卡机枪】摆在无人机来路上，把【IRIS-T / NASAMS 导弹】护在 ★ 热电厂周围。");
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
    const qInit = new URLSearchParams(location.search);
    if (qInit.get("inspect") === "0") state.inspectorOpen = false;
    if (qInit.get("drawer")) openDrawer(Number(qInit.get("drawer")));
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
    if ($("tb-cov-vis")) $("tb-cov-vis").textContent = `${vis.toFixed(1)}%`;
    if ($("tb-cov-blind")) $("tb-cov-blind").textContent = `${blind.toFixed(1)}%`;
    const vBadge = $("validation-badge"), errBox = $("validation-errors");
    if (cov.valid) {
      vBadge.textContent = "部署合法"; vBadge.className = "badge badge-ok"; errBox.classList.add("hidden");
    } else {
      vBadge.textContent = `${cov.errors.length} 处冲突`; vBadge.className = "badge badge-err";
      errBox.classList.remove("hidden"); errBox.textContent = cov.errors.slice(0, 2).join("；");
    }
    renderAdvisor();
    refreshOpenDrawer();
  }

  // ───────────── D1–D7 指挥所抽屉管理（参照 israel_political_simulation DrawerContainer） ─────────────
  function syncDrawerButtons() {
    const idx = state.openDrawerIndex || 0;
    document.querySelectorAll(".desk-prop-btn[data-drawer]").forEach((b) => {
      b.classList.toggle("open", Number(b.dataset.drawer) === idx);
    });
    document.querySelectorAll(".drawer-tab-btn[data-drawer-tab]").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.drawerTab) === idx);
    });
    document.querySelectorAll(".tb-kpi-slot[data-open-drawer]").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.openDrawer) === idx);
    });
    const inspCard = $("unit-inspector");
    const showInsp = idx === 0 && Boolean(state.inspectorOpen && state.selectedUnitKey);
    if (inspCard) {
      inspCard.classList.toggle("collapsed", !showInsp);
    }
    if ($("canvas-wrapper")) {
      $("canvas-wrapper").classList.toggle("inspector-docked", showInsp);
    }
    setTimeout(fitCanvas, 10);
  }

  function openDrawer(index) {
    const target = Math.max(0, Math.min(7, Number(index) || 0));
    if (target === 0) return closeDrawer();
    state.openDrawerIndex = target;
    const container = $("DrawerContainer");
    if (container) container.classList.remove("hidden");
    const m = DRAWER_META[target] || { code: `D${target}`, title: "" };
    if ($("drawer-code-badge")) $("drawer-code-badge").textContent = m.code;
    if ($("drawer-title")) $("drawer-title").textContent = m.title;
    document.querySelectorAll("#drawer-content .drawer-slot").forEach((slot) => {
      slot.classList.toggle("hidden", Number(slot.dataset.slot) !== target);
    });
    syncDrawerButtons();
    refreshOpenDrawer();
  }

  function closeDrawer() {
    state.openDrawerIndex = 0;
    const container = $("DrawerContainer");
    if (container) container.classList.add("hidden");
    syncDrawerButtons();
  }

  function toggleDrawer(index) {
    const target = Number(index) || 0;
    if (state.openDrawerIndex === target) closeDrawer();
    else openDrawer(target);
  }

  function kpiCardHtml(title, val, sub, tone) {
    return `<div class="d-metric-card ${tone ? `tone-${tone}` : ""}">
      <div class="d-metric-top"><span class="d-metric-name">${esc(title)}</span><span class="d-metric-val">${esc(val)}</span></div>
      ${sub ? `<div class="d-metric-sub">${esc(sub)}</div>` : ""}
    </div>`;
  }

  function renderD1() {
    const kpiBox = $("d1-kpi-row");
    if (!kpiBox) return;
    const cov = state.coverage;
    const vis = cov && cov.stats ? (cov.stats.visibleFrac * 100).toFixed(1) + "%" : "--%";
    const blind = cov && cov.stats ? (cov.stats.blindFrac * 100).toFixed(1) + "%" : "--%";
    const validStr = !cov || cov.valid ? "合法就绪" : `${(cov.errors || []).length} 处冲突`;
    const presetMap = { layered: "推荐（前推）", default: "均衡（环形）", stacked: "抱团（反例）", custom: "自定义布防" };
    kpiBox.innerHTML = [
      kpiCardHtml("100m 雷达覆盖率", vis, "越高越能提早拦截", cov && cov.stats && cov.stats.visibleFrac >= 0.9 ? "good" : "warn"),
      kpiCardHtml("山脊低空盲区", blind, "巡航导弹易在此贴地渗透", cov && cov.stats && cov.stats.blindFrac <= 0.05 ? "good" : "bad"),
      kpiCardHtml("部署校验状态", validStr, "检查禁放区与最小间距", !cov || cov.valid ? "good" : "bad"),
      kpiCardHtml("当前布防方案", presetMap[state.activePreset] || "自定义", `盲区参考高度 ${state.losAltM || 100}m`, ""),
    ].join("");
    document.querySelectorAll("#d1-preset-cards .d-preset-card").forEach((b) => {
      b.classList.toggle("active", b.dataset.preset === state.activePreset);
    });
    document.querySelectorAll("#d1-alt-seg .seg-btn").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.alt) === Number(state.losAltM));
    });
  }

  function renderD3() {
    const kpiBox = $("d3-kpi-row");
    if (!kpiBox) return;
    const units = getActiveUnits();
    const fireUnits = units.filter((u) => (u.category || "fire") === "fire");
    const radarUnits = units.filter((u) => (u.emitter && u.emitter.hasEmitter) || u.hasRadar || u.unitDefId === "soviet_mid_range_radar" || u.unitDefId === "nasams");
    const activeRadars = radarUnits.filter((u) => u.emitter ? u.emitter.on : (u.emissionPolicy !== "silent")).length;
    const maxExp = Math.round(units.reduce((m, u) => Math.max(m, u.exposure !== undefined ? u.exposure : (u.carryExposure || 0)), 0));
    const cpCur = state.snapshot && state.snapshot.cp ? state.snapshot.cp.current : (state.meta ? state.meta.commandPointsPerNight : 4);
    const cpMax = state.snapshot && state.snapshot.cp ? state.snapshot.cp.initial : (state.meta ? state.meta.commandPointsPerNight : 4);
    kpiBox.innerHTML = [
      kpiCardHtml("防空火力单元", `${fireUnits.filter((u) => isActiveState(u.deployState)).length} / ${fireUnits.length}`, "NASAMS + IRIS-T + 皮卡×4", "good"),
      kpiCardHtml("电磁辐射源开机", `${activeRadars} / ${radarUnits.length}`, "警戒雷达 + NASAMS 火控雷达", activeRadars > 0 ? "good" : "warn"),
      kpiCardHtml("全军最高暴露度", `${maxExp}%`, "达 70% 将引来反辐射导弹", maxExp >= 70 ? "bad" : (maxExp >= 40 ? "warn" : "good")),
      kpiCardHtml("剩余指挥点 CP", `${cpCur} / ${cpMax}`, "用于阵地转移与导航诱偏", cpCur > 0 ? "" : "warn"),
    ].join("");

    const wWrap = $("d3-weapons-table-wrap");
    if (wWrap) {
      const rows = fireUnits.map((u) => {
        const w = (u.weapons && u.weapons[0]) || {};
        const wid = w.weaponId || w.id || "";
        const wl = w.whitelist || ["UAV", "CM", "BM", "AC_LOW"];
        const isMissile = u.unitDefId === "nasams" || u.unitDefId === "iris_t_sls";
        const isHold = w.rule === "hold_fire";
        const isMissileOnly = !isHold && !wl.includes("UAV") && wl.includes("CM");
        const isAllOpen = !isHold && wl.includes("UAV");
        const rds = !isMissile ? "无限弹链" : (w.rounds !== undefined ? (w.rounds < 0 ? "无限" : `${w.rounds}发`) : (w.magazine > 100 ? "无限" : `${w.magazine || 8}发`));
        const ctrlHtml = isMissile
          ? `<div class="d-batch-row">
              <button type="button" class="btn btn-xs ${isMissileOnly ? "btn-primary" : ""}" data-d3-doc="missile_only" data-ukey="${unitKey(u)}" data-wid="${esc(wid)}">只打导弹</button>
              <button type="button" class="btn btn-xs ${isAllOpen ? "btn-primary" : ""}" data-d3-doc="all_open" data-ukey="${unitKey(u)}" data-wid="${esc(wid)}">全开</button>
              <button type="button" class="btn btn-xs ${isHold ? "btn-warn" : ""}" data-d3-doc="hold" data-ukey="${unitKey(u)}" data-wid="${esc(wid)}">停火</button>
            </div>`
          : `<span class="badge badge-ok">机枪自动自由扫射无人机</span>`;
        return `<tr>
          <td class="td-bold">#${u.rosterId} ${esc(FRIENDLY_NAMES[u.unitDefId] || u.name)}</td>
          <td class="td-num">${esc(rds)}</td>
          <td>${ctrlHtml}</td>
        </tr>`;
      }).join("");
      wWrap.innerHTML = `<table class="d-table"><thead><tr><th>防空武器单元</th><th>备弹</th><th>开火纪律（点击立即下达）</th></tr></thead><tbody>${rows}</tbody></table>`;
      wWrap.querySelectorAll("[data-d3-doc]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const u = units.find((x) => String(unitKey(x)) === String(btn.dataset.ukey));
          if (!u) return;
          await applyUnitDoctrine(u, btn.dataset.wid, btn.dataset.d3Doc);
          renderRosterAndInspector();
        });
      });
    }

    const rWrap = $("d3-radars-table-wrap");
    if (rWrap) {
      const rRows = radarUnits.map((u) => {
        const curPol = u.emitter ? u.emitter.policyId : (u.emissionPolicy || "blink");
        const exp = Math.round(u.exposure !== undefined ? u.exposure : (u.carryExposure || 0));
        return `<tr>
          <td class="td-bold">#${u.rosterId} ${esc(FRIENDLY_NAMES[u.unitDefId] || u.name)}</td>
          <td class="td-num" style="color:${exp >= 70 ? "var(--hostile)" : (exp >= 40 ? "var(--unknown)" : "var(--text)")}">${exp}%</td>
          <td>
            <div class="d-batch-row">
              ${POLICY.map(([id, nm]) => `<button type="button" class="btn btn-xs ${curPol === id || (id === "continuous" && curPol === "always_on") ? "btn-primary" : ""}" data-d3-pol="${id}" data-ukey="${unitKey(u)}">${nm}</button>`).join("")}
            </div>
          </td>
        </tr>`;
      }).join("");
      rWrap.innerHTML = `<table class="d-table"><thead><tr><th>雷达单元</th><th>暴露度</th><th>辐射模式</th></tr></thead><tbody>${rRows}</tbody></table>`;
      rWrap.querySelectorAll("[data-d3-pol]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const u = units.find((x) => String(unitKey(x)) === String(btn.dataset.ukey));
          if (u) await setPolicy(u, btn.dataset.d3Pol);
        });
      });
    }
  }

  function renderD5() {
    const kpiBox = $("d5-kpi-row");
    const detailBox = $("d5-structures-detail");
    if (!kpiBox || !detailBox) return;
    const snap = state.snapshot;
    const structs = (snap && snap.structures) || (state.meta && state.meta.structures) || [];
    const okCount = structs.filter((s) => !s.destroyed).length;
    const unp = snap && snap.grid ? Math.round((snap.grid.unpoweredFrac || 0) * 100) : 0;
    const alertOn = Boolean(snap && snap.alert && snap.alert.on);
    const shPct = snap && snap.alert ? Math.round((snap.alert.shelteredFrac || 0) * 100) : 0;
    kpiBox.innerHTML = [
      kpiCardHtml("完好保卫设施", `${okCount} / ${structs.length}`, "热电厂 · 变电站 · 水厂", okCount === structs.length ? "good" : "bad"),
      kpiCardHtml("城市电网状态", unp > 0 ? `断电 ${unp}%` : "100% 正常供电", "热电厂为全城总电源", unp === 0 ? "good" : "bad"),
      kpiCardHtml("市政防空警报", alertOn ? "已拉响" : "关闭待命", "空袭逼近城区时应拉响", alertOn ? "warn" : ""),
      kpiCardHtml("市民掩蔽率", `${shPct}%`, "越高越能减少平民伤亡", shPct >= 60 ? "good" : ""),
    ].join("");
    detailBox.innerHTML = structs.map((s) => {
      const metaStruct = (state.meta && (state.meta.structures || []).find((m) => m.id === s.id)) || s;
      const typ = metaStruct.type || s.type;
      const roleTag = STRUCT_ROLE[typ] || "保卫设施";
      const desc = STRUCT_INFO[typ] || "";
      const frac = Math.max(0, Math.min(1, s.hp / Math.max(1, s.maxHp)));
      const col = frac > 0.5 ? "var(--ok)" : (frac > 0.2 ? "var(--warn)" : "var(--danger)");
      return `<div class="struct-item ${s.destroyed ? "destroyed" : ""}" data-sid="${esc(s.id)}">
        <div class="struct-row">
          <span class="struct-name"><span class="struct-glyph">★</span>${esc(s.name)} <span class="struct-role-tag">${esc(roleTag)}</span></span>
          <span class="struct-hp">耐久 ${s.hp}/${s.maxHp}</span>
        </div>
        <div class="d-subnote">${desc}</div>
        <div class="hp-bar-wrap"><div class="hp-bar-fill" style="width:${frac * 100}%;background:${col}"></div></div>
      </div>`;
    }).join("");
    detailBox.querySelectorAll(".struct-item").forEach((el) => {
      el.addEventListener("click", () => {
        const stObj = structs.find((x) => String(x.id) === String(el.dataset.sid));
        if (stObj && stObj.pos) {
          state.focusStructId = stObj.id;
          state.pulses.push({ pos: stObj.pos, t0: performance.now(), color: "ok" });
          closeDrawer();
        }
      });
    });
  }

  function refreshOpenDrawer() {
    if (state.openDrawerIndex === 1) renderD1();
    else if (state.openDrawerIndex === 3) renderD3();
    else if (state.openDrawerIndex === 5) renderD5();
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
    const okCount = structs.filter((s) => !s.destroyed).length;
    if ($("tb-struct-kpi")) {
      $("tb-struct-kpi").textContent = `${okCount}/${structs.length} 完好`;
      $("tb-struct-kpi").className = `tb-kpi-val ${okCount < structs.length ? "tb-val-warn" : ""}`;
    }
    $("structures-list").innerHTML = structs.map((s) => {
      const metaStruct = (state.meta && (state.meta.structures || []).find((m) => m.id === s.id)) || s;
      const typ = metaStruct.type || s.type;
      const roleTag = STRUCT_ROLE[typ] || "保卫设施";
      const desc = STRUCT_INFO[typ] || "";
      const frac = Math.max(0, Math.min(1, s.hp / Math.max(1, s.maxHp)));
      const col = frac > 0.5 ? "var(--ok)" : (frac > 0.2 ? "var(--warn)" : "var(--danger)");
      const pwr = s.destroyed ? '<span class="badge badge-err">已摧毁</span>'
        : (s.powered === false ? '<span class="badge badge-err">断电</span>' : '<span class="badge badge-ok">正常</span>');
      return `<div class="struct-item ${s.destroyed ? "destroyed" : ""}" data-sid="${esc(s.id)}" data-tip="${esc(desc)}（点击在地图上定位）">
        <div class="struct-row">
          <span class="struct-name"><span class="struct-glyph">★</span>${esc(s.name)} <span class="struct-role-tag">${esc(roleTag)}</span></span>
          <span class="struct-hp">${s.hp}/${s.maxHp} ${pwr}</span>
        </div>
        <div class="hp-bar-wrap"><div class="hp-bar-fill" style="width:${frac * 100}%;background:${col}"></div></div></div>`;
    }).join("");
    $("structures-list").querySelectorAll(".struct-item").forEach((el) => {
      const sid = el.dataset.sid;
      const stObj = structs.find((x) => String(x.id) === String(sid));
      el.addEventListener("mouseenter", () => { state.focusStructId = sid; });
      el.addEventListener("mouseleave", () => { state.focusStructId = null; });
      el.addEventListener("click", () => {
        if (stObj && stObj.pos) {
          state.focusStructId = sid;
          state.pulses.push({ pos: stObj.pos, t0: performance.now(), color: "ok" });
        }
      });
    });
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
    if (state.openDrawerIndex === 5) renderD5();
  }

  function getAmmoPool() {
    const snap = state.snapshot;
    const pool = (snap && snap.ammoPool) || (state.meta && state.meta.carryIn && state.meta.carryIn.ammoPool) || {};
    return Object.keys(pool).length ? pool : { iris_t_slm_missile: 16, amraam_nasams: 18, igla_manpads: 16, heavy_mg_12_7: 99999 };
  }

  const getActiveUnits = () => state.phase === "deploy" ? state.placements : ((state.snapshot && state.snapshot.units) || []);
  const unitKey = (u) => u.id || u.rosterId;
  const isPassiveSensor = (u) => u && (u.unitDefId === "acoustic_post" || u.unitDefId === "visual_observer");

  function renderRosterItem(u) {
    const key = unitKey(u), sel = key === state.selectedUnitKey ? "selected" : "";
    const expV = u.exposure !== undefined ? u.exposure : (u.carryExposure || 0);
    const expFlag = u.isExposed || u.isKnownTarget || expV >= 70 ? "exposed" : "";
    const isArmSilenced = Boolean(u.emitter && u.emitter.armSilenced);
    const em = isArmSilenced ? '<span class="em-arm">规避静默</span>'
      : (u.emitter && u.emitter.hasEmitter ? (u.emitter.on ? '<span class="em-on">雷达开</span>' : '<span>雷达关</span>') : "");
    const w0Obj = u.weapons && u.weapons[0];
    let w0 = "";
    if (w0Obj) {
      if (u.unitDefId === "mobile_fire_team") w0 = "无限弹";
      else if (w0Obj.rounds !== undefined) w0 = w0Obj.rounds >= 0 ? `弹${w0Obj.rounds}` : "无限弹";
      else if (w0Obj.magazine) w0 = w0Obj.magazine > 100 ? "无限弹" : `弹${w0Obj.magazine}`;
    }
    const expTxt = expV > 0 ? `<span class="${expV >= 70 ? "exp-hi" : (expV >= 35 ? "exp-mid" : "")}">暴露${Math.round(expV)}%</span>` : "";
    const st = u.deployState ? (STATE_NAMES[u.deployState] || u.deployState) : "";
    const inactive = !isActiveState(u.deployState);
    const info = UNIT_INFO[u.unitDefId] || {};
    const subSpec = !isPassiveSensor(u) && info.weaponSpec ? `<div class="roster-sub">${esc(info.weaponSpec)}</div>` : "";
    return `<div class="roster-item ${sel} ${expFlag}" data-ukey="${key}">
      <i class="roster-pip cat-${esc(u.category || "fire")} ${inactive ? "inactive" : ""}"></i>
      <div class="roster-name"><div><span class="rid">#${u.rosterId}</span><strong>${esc(FRIENDLY_NAMES[u.unitDefId] || u.name)}</strong>${st && st !== "就绪" ? `<span class="rstate">${esc(st)}</span>` : ""}</div>${subSpec}</div>
      <div class="roster-meta">${em}${w0 ? `<span>${w0}</span>` : ""}${expTxt}</div></div>`;
  }

  function renderRosterAndInspector() {
    const units = getActiveUnits();
    const fireOrder = { nasams: 0, iris_t_sls: 1, mobile_fire_team: 2 };
    const fireUnits = units.filter((u) => (u.category || "fire") === "fire")
      .sort((a, b) => (fireOrder[a.unitDefId] ?? 9) - (fireOrder[b.unitDefId] ?? 9) || (a.rosterId - b.rosterId));
    const radarUnits = units.filter((u) => u.category === "sensor" && !isPassiveSensor(u));
    const passiveUnits = units.filter((u) => isPassiveSensor(u));

    $("roster-count-badge").textContent = `${fireUnits.length} 部武器 · ${radarUnits.length} 座雷达`;
    if ($("tb-roster-kpi")) $("tb-roster-kpi").textContent = `${fireUnits.length}火力·${radarUnits.length}雷达`;
    const rBox = $("unit-roster-list");
    const scrollTop = rBox.scrollTop;
    let html = "";
    if (fireUnits.length) {
      html += `<div class="roster-group">主力防空武器 · ${fireUnits.length}</div>` + fireUnits.map(renderRosterItem).join("");
    }
    if (radarUnits.length) {
      html += `<div class="roster-group">远程警戒雷达 · ${radarUnits.length}</div>` + radarUnits.map(renderRosterItem).join("");
    }
    if (passiveUnits.length) {
      const selInPassive = passiveUnits.some((u) => unitKey(u) === state.selectedUnitKey);
      const openAttr = (state.openPassiveRoster || selInPassive) ? "open" : "";
      html += `<details class="passive-roster-fold" ${openAttr}>
        <summary class="roster-group passive-summary">辅助暗哨（听音×6 / 目视×3）· 自动补盲，战中免操作</summary>
        <div class="passive-roster-body">${passiveUnits.map(renderRosterItem).join("")}</div>
      </details>`;
    }
    rBox.innerHTML = html;
    rBox.scrollTop = scrollTop;
    const pFold = rBox.querySelector(".passive-roster-fold");
    if (pFold) pFold.addEventListener("toggle", () => { state.openPassiveRoster = pFold.open; });
    rBox.querySelectorAll(".roster-item").forEach((el) => {
      el.addEventListener("click", () => {
        state.selectedUnitKey = Number(el.dataset.ukey);
        state.inspectorOpen = true;
        const targetUnit = units.find((u) => unitKey(u) === state.selectedUnitKey);
        if (targetUnit && targetUnit.pos) state.pulses.push({ pos: targetUnit.pos, t0: performance.now(), color: "ok" });
        renderRosterAndInspector();
      });
    });
    renderInspector(units.find((u) => unitKey(u) === state.selectedUnitKey));
    if (state.openDrawerIndex === 3) renderD3();
  }

  function rangeOf(u) {
    const w = (u.weapons || []).find((x) => x.rangeM > 0);
    return w ? w.rangeM : 0;
  }

  function renderInspector(u) {
    const inspCard = $("unit-inspector");
    const showInsp = state.openDrawerIndex === 0 && Boolean(state.inspectorOpen && u);
    if (inspCard) {
      inspCard.classList.toggle("collapsed", !showInsp);
    }
    if ($("canvas-wrapper")) {
      $("canvas-wrapper").classList.toggle("inspector-docked", showInsp);
    }
    setTimeout(fitCanvas, 10);
    const body = $("insp-body");
    if (body.contains(document.activeElement) && document.activeElement.tagName !== "BUTTON" && body.dataset.ukey === String(u && unitKey(u))) return;
    body.dataset.ukey = String(u ? unitKey(u) : "");
    if (!u) {
      $("insp-unit-title").textContent = "选中防空武器";
      $("insp-unit-state").textContent = "—";
      body.innerHTML = '<div class="empty-hint">点击地图上的防空武器（皮卡机枪、IRIS‑T、NASAMS），查看它的射程与开火设置。</div>';
      return;
    }
    const info = UNIT_INFO[u.unitDefId] || { role: CAT_ROLE[u.category] || "单位", weaponSpec: "", targetRole: "", desc: "" };
    const dispName = FRIENDLY_NAMES[u.unitDefId] || u.name;
    $("insp-unit-title").textContent = `#${u.rosterId} ${dispName}`;
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
    const expCol = exp >= 70 ? "var(--danger)" : (exp >= 35 ? "var(--warn)" : "var(--text)");
    const rng = rangeOf(u), det = u.detectionRangeM || 0;

    let html = "";
    if (info.weaponSpec) {
      html += `<div class="insp-weapon-banner">
        <div class="iwb-top"><span class="iwb-lbl">武器装备</span><strong class="iwb-spec">${esc(info.weaponSpec)}</strong></div>
        ${info.targetRole ? `<div class="iwb-sub">作战分工：<b>${esc(info.targetRole)}</b></div>` : ""}
      </div>`;
    }
    html += `<div class="insp-desc">${info.desc}</div>
      <div class="insp-stats">
        <div class="insp-stat"><span class="k">${rng ? "有效射程" : "探测范围"}</span><span class="v">${((rng || det) / 1000).toFixed(1)} km</span></div>
        <div class="insp-stat"><span class="k">今夜击落</span><span class="v">${u.killsTonight || 0}</span></div>
        <div class="insp-stat"><span class="k">暴露度</span><span class="v" style="color:${expCol}">${exp}%</span></div>
      </div>
      <div class="exp-bar-wrap" data-tip="暴露度：雷达开机越久越高。超过 70% 敌人会记住这个位置，下一夜专门来打。"><div class="exp-bar-fill" style="width:${Math.min(100, exp)}%"></div></div>`;

    if (isPassiveSensor(u)) {
      html += `<div class="passive-notice-box">
        <div><b>被动辅助暗哨（战中 100% 全自动）</b>：只负责帮防空武器照亮山脊背面的低空盲区，战斗中<b>无需手动操作</b>。</div>
        <button id="btn-jump-main-weapon" class="btn btn-xs" style="margin-top:6px">→ 切回主力防空武器</button>
      </div>`;
    }

    if (isArmSilenced) html += `<div class="insp-alert">正在关机躲避反辐射导弹，这段时间看不见敌人。危险过去后点下方“闪烁”或“常开”恢复。</div>`;

    if (hasEmitter) {
      html += `<div class="insp-section-lbl">雷达开关（影响探测与暴露度）</div>
        <div class="policy-seg">${POLICY.map(([id, nm, tip]) =>
          `<button class="policy-btn ${curPol === id || (id === "continuous" && curPol === "always_on") ? "active" : ""}" data-pol="${id}"><b>${nm}</b><small>${tip}</small></button>`).join("")}</div>`;
    }

    if ((u.weapons || []).length) {
      const carryUsedMap = (state.meta && state.meta.carryIn && state.meta.carryIn.perLevelUsed) || {};
      (u.weapons || []).forEach((w) => {
        const wid = w.weaponId || w.id;
        const wName = WEAPON_NAMES[wid] || w.name || wid;
        const wl = w.whitelist || ["UAV", "CM", "BM", "AC_LOW"];
        const isMissile = u.unitDefId === "nasams" || u.unitDefId === "iris_t_sls";
        const rds = !isMissile ? "无限（机枪弹链充足）" : (w.rounds !== undefined ? (w.rounds < 0 ? "无限（机枪弹链充足）" : `${w.rounds}/${w.maxRounds} 发`) : (w.magazine > 100 ? "无限（机枪弹链充足）" : `${w.magazine || 8} 发`));
        const isHold = w.rule === "hold_fire";
        const isMissileOnly = !isHold && !wl.includes("UAV") && wl.includes("CM");
        const isAllOpen = !isHold && wl.includes("UAV");
        const plLim = w.perLevelLimit !== undefined && w.perLevelLimit !== null ? Number(w.perLevelLimit) : null;
        let quotaHtml = "";
        if (plLim !== null) {
          const remQ = w.remainingQuota !== undefined && w.remainingQuota !== null ? Number(w.remainingQuota) : Math.max(0, plLim - Number(carryUsedMap[wid] || 0));
          quotaHtml = `<div class="insp-row" style="font-size:11px;color:${remQ <= 0 ? "var(--danger)" : "var(--text-2)"};"><span>本关剩余导弹配额 <strong>${remQ}/${plLim}</strong>${remQ <= 0 ? " · 已用完" : ""}</span></div>`;
        }
        html += `<div class="weapon-box">
          <div class="insp-row"><span class="weapon-name">${esc(wName)}</span><span class="weapon-ammo">备弹 ${rds}${w.reloadRemSec > 0 ? ` · 装填 ${w.reloadRemSec}s` : ""}</span></div>
          ${quotaHtml}`;
        if (isMissile) {
          html += `<div class="insp-section-lbl" style="margin-top:2px">开火纪律（打什么目标）</div>
            <div class="doctrine-seg">
              <button class="doctrine-btn ${isMissileOnly ? "active" : ""}" data-doc="missile_only" data-wid="${esc(wid)}"><b>只打导弹</b><small>省弹 · 无人机留给机枪</small></button>
              <button class="doctrine-btn ${isAllOpen ? "active" : ""}" data-doc="all_open" data-wid="${esc(wid)}"><b>无人机也打</b><small>全开 · 危急时帮忙清场</small></button>
              <button class="doctrine-btn ${isHold ? "active" : ""}" data-doc="hold" data-wid="${esc(wid)}"><b>停火待命</b><small>保留弹药暂不开火</small></button>
            </div>`;
        }
        html += `<details class="adv-weapons" ${state.openWeapons ? "open" : ""}><summary>细分目标与保留弹数</summary>
          <div class="insp-row" style="margin-top:6px"><span class="insp-label">开火原则</span>
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
          <div class="insp-label">允许拦截的目标类型</div>
          <div class="tag-checks">
            ${["UAV", "CM", "BM", "AC_LOW"].map((tg) => `<label><input type="checkbox" class="insp-w-tag" data-wid="${esc(wid)}" value="${tg}" ${wl.includes(tg) ? "checked" : ""}/>${TAG_CN[tg]}</label>`).join("")}
            <label data-tip="先打一发，看结果再决定是否补射，更省弹"><input type="checkbox" class="insp-w-sls" data-wid="${esc(wid)}" ${w.shootLookShoot !== false ? "checked" : ""}/>打一发看一眼</label>
          </div>
        </details>
        ${state.phase === "battle" && hasEmitter ? `<button id="insp-btn-burst" class="btn btn-xs" data-tip="强制全功率开机 15 秒刷新航迹，暴露度 +8%">短促扫描</button>` : ""}
        </div>`;
      });
    }

    if (u.mobility !== "fixed" && alts.length > 0) {
      html += `<div class="insp-section-lbl">${state.phase === "deploy" ? "移到预备阵地（也可以直接在地图上拖动）" : "转移阵地：撤收→机动→展开，期间不能开火"}</div>
        <div class="insp-row">
          <select id="insp-sel-alt" class="select-sm flex-1">${altOpts}</select>
          <button id="insp-btn-reloc" class="btn btn-xs ${state.phase === "deploy" ? "" : "btn-warn"}">${state.phase === "deploy" ? "移过去" : "转移 · 1 CP"}</button>
        </div>`;
    }

    if (state.phase === "deploy" && u.mobility !== "fixed") html += `<div class="card-note">提示：在地图上按住该防空武器拖动即可换位置。</div>`;
    body.innerHTML = html;
    bindInspectorEvents(u);
  }

  async function applyUnitDoctrine(u, wid, doc) {
    const wObj = (u.weapons || []).find((x) => (x.weaponId || x.id) === wid) || (u.weapons && u.weapons[0]);
    const targetWid = wid || (wObj && (wObj.weaponId || wObj.id));
    if (doc === "missile_only") {
      if (wObj) { wObj.rule = "any"; wObj.whitelist = ["CM", "BM", "AC_LOW"]; }
      if (state.phase === "battle" && targetWid) {
        await sendCommand({ type: "SetEngagementRule", unitId: u.id, weaponId: targetWid, rule: "any" });
        await sendCommand({ type: "SetTargetWhitelist", unitId: u.id, weaponId: targetWid, tags: ["CM", "BM", "AC_LOW"] });
      }
    } else if (doc === "all_open") {
      if (wObj) { wObj.rule = "any"; wObj.whitelist = ["UAV", "CM", "BM", "AC_LOW"]; }
      if (state.phase === "battle" && targetWid) {
        await sendCommand({ type: "SetEngagementRule", unitId: u.id, weaponId: targetWid, rule: "any" });
        await sendCommand({ type: "SetTargetWhitelist", unitId: u.id, weaponId: targetWid, tags: ["UAV", "CM", "BM", "AC_LOW"] });
      }
    } else if (doc === "hold") {
      if (wObj) { wObj.rule = "hold_fire"; }
      if (state.phase === "battle" && targetWid) {
        await sendCommand({ type: "SetEngagementRule", unitId: u.id, weaponId: targetWid, rule: "hold_fire" });
      }
    }
  }

  function bindInspectorEvents(u) {
    const det = document.querySelector("#insp-body .adv-weapons");
    if (det) det.addEventListener("toggle", () => { state.openWeapons = det.open; });
    const jumpBtn = $("btn-jump-main-weapon");
    if (jumpBtn) {
      jumpBtn.addEventListener("click", () => {
        const units = getActiveUnits();
        const mainW = units.find((x) => x.unitDefId === "nasams") || units.find((x) => (x.category || "fire") === "fire");
        if (mainW) { state.selectedUnitKey = unitKey(mainW); state.inspectorOpen = true; renderRosterAndInspector(); }
      });
    }
    document.querySelectorAll("#insp-body .policy-btn").forEach((b) => b.addEventListener("click", () => setPolicy(u, b.dataset.pol)));
    document.querySelectorAll("#insp-body .doctrine-btn").forEach((b) => b.addEventListener("click", async () => {
      await applyUnitDoctrine(u, b.dataset.wid, b.dataset.doc);
      renderRosterAndInspector();
    }));
    const burstBtn = $("insp-btn-burst");
    if (burstBtn) burstBtn.addEventListener("click", () => sendCommand({ type: "BurstScan", unitId: u.id, durationSec: 15 }));
    const relocBtn = $("insp-btn-reloc");
    if (relocBtn) relocBtn.addEventListener("click", () => relocateUnit(u, $("insp-sel-alt").value));
    document.querySelectorAll(".insp-w-rule").forEach((el) => {
      el.addEventListener("change", () => {
        const wObj = (u.weapons || []).find((x) => (x.weaponId || x.id) === el.dataset.wid);
        if (wObj) wObj.rule = el.value;
        sendCommand({ type: "SetEngagementRule", unitId: u.id, weaponId: el.dataset.wid, rule: el.value });
        el.blur();
        if (state.phase === "deploy") renderRosterAndInspector();
      });
    });
    document.querySelectorAll(".insp-w-res").forEach((el) => {
      el.addEventListener("input", () => {
        $(`lbl-res-${el.dataset.wid}`).textContent = el.value;
        const wObj = (u.weapons || []).find((x) => (x.weaponId || x.id) === el.dataset.wid);
        if (wObj) wObj.ammoReserve = Number(el.value);
        sendCommand({ type: "SetAmmoReserve", unitId: u.id, weaponId: el.dataset.wid, reserve: Number(el.value) });
      });
      el.addEventListener("change", () => el.blur());
    });
    document.querySelectorAll(".insp-w-tag").forEach((el) => {
      el.addEventListener("change", () => {
        const wid = el.dataset.wid;
        const tags = Array.from(document.querySelectorAll(`.insp-w-tag[data-wid="${wid}"]:checked`)).map((c) => c.value);
        const wObj = (u.weapons || []).find((x) => (x.weaponId || x.id) === wid);
        if (wObj) wObj.whitelist = tags;
        sendCommand({ type: "SetTargetWhitelist", unitId: u.id, weaponId: wid, tags });
        el.blur();
        if (state.phase === "deploy") renderRosterAndInspector();
      });
    });
    document.querySelectorAll(".insp-w-sls").forEach((el) => {
      el.addEventListener("change", () => {
        const wObj = (u.weapons || []).find((x) => (x.weaponId || x.id) === el.dataset.wid);
        if (wObj) wObj.shootLookShoot = el.checked;
        sendCommand({ type: "SetShootLookShoot", unitId: u.id, weaponId: el.dataset.wid, enabled: el.checked });
        el.blur();
      });
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

  function selectUnit(u) { state.selectedUnitKey = unitKey(u); state.inspectorOpen = true; renderRosterAndInspector(); }

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
    if (snap && snap.units) {
      snap.units.forEach((u) => {
        if (FRIENDLY_NAMES[u.unitDefId]) u.name = FRIENDLY_NAMES[u.unitDefId];
        (u.weapons || []).forEach((w) => {
          const wid = w.weaponId || w.id;
          if (WEAPON_NAMES[wid]) w.name = WEAPON_NAMES[wid];
        });
      });
    }
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
    const showInsp = state.openDrawerIndex === 0 && Boolean(state.inspectorOpen && state.selectedUnitKey);
    const availW = wrap.clientWidth - (showInsp ? 304 : 12);
    const availH = wrap.clientHeight - 12;
    const size = Math.max(240, Math.min(availW, availH));
    const v = canvas._view;
    if (v && v.width === Math.floor(size) && v.dpr === Math.min(2.5, window.devicePixelRatio || 1)) return;
    window.TacticalRenderer.resize(canvas, size, size);
  }

  // ───────────── 地图拾取、缩放与悬停说明 ─────────────
  function canvasXY(e) {
    const rect = canvas.getBoundingClientRect();
    const view = window.TacticalRenderer.getView(canvas);
    const sx = rect.width ? view.width / rect.width : 1;
    const sy = rect.height ? view.height / rect.height : 1;
    return [(e.clientX - rect.left) * sx, (e.clientY - rect.top) * sy];
  }

  function updateZoomReadout() {
    const view = window.TacticalRenderer.getView(canvas);
    const pct = `${Math.round((view.zoom || 1) * 100)}%`;
    if ($("btn-zoom-reset")) $("btn-zoom-reset").textContent = pct;
    if ($("btn-tb-zoom-reset")) $("btn-tb-zoom-reset").textContent = pct;
  }

  function stepMapZoom(factor, ax, ay) {
    const view = window.TacticalRenderer.getView(canvas);
    const cur = view.zoom || 1;
    window.TacticalRenderer.zoomAt(canvas, cur * factor, ax, ay);
    updateZoomReadout();
  }

  function resetMapZoom() {
    window.TacticalRenderer.resetCamera(canvas);
    updateZoomReadout();
  }

  function applyUiScale(scale) {
    const s = Math.max(0.8, Math.min(1.3, Math.round(scale * 20) / 20));
    state.uiScale = s;
    document.body.style.zoom = s === 1 ? "" : String(s);
    if ($("btn-ui-zoom-reset")) $("btn-ui-zoom-reset").textContent = `${Math.round(s * 100)}%`;
    LS.set("nw_ui_scale", String(s));
    setTimeout(fitCanvas, 30);
  }

  async function finishUnitDrag() {
    canvas.classList.remove("grabbing");
    if (!state.draggingUnit) return;
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
      const info = UNIT_INFO[u.unitDefId] || { role: CAT_ROLE[u.category] || "", weaponSpec: "", desc: "" };
      const rng = rangeOf(u), det = u.detectionRangeM || 0;
      const exp = Math.round(u.exposure !== undefined ? u.exposure : (u.carryExposure || 0));
      const dispName = FRIENDLY_NAMES[u.unitDefId] || u.name;
      html = `<div class="mt-title">#${u.rosterId} ${esc(dispName)}<span class="mt-kind">${esc(info.role)}</span></div>
        ${info.weaponSpec ? `<div style="color:var(--friend);font-size:11.5px;font-weight:600;margin:2px 0">${esc(info.weaponSpec)}</div>` : ""}
        <div>${info.desc}</div>
        <div class="mt-row">${rng ? `有效射程 ${(rng / 1000).toFixed(1)} km` : ""}${rng && det ? " · " : ""}${det ? `探测 ${(det / 1000).toFixed(1)} km` : ""}${exp ? ` · 暴露 ${exp}%` : ""}</div>
        <div class="mt-hint">${state.phase === "deploy" && u.mobility !== "fixed" ? "按住拖动换位置 · 点击查看射程与开火设置" : "点击选中，在左侧调整开火纪律"}</div>`;
    } else {
      const structs = (state.snapshot && state.snapshot.structures) || state.meta.structures || [];
      const s = pickNearest(structs, (x) => worldToCanvas(x.pos), px, py, 24);
      if (s) {
        const typ = (state.meta.structures.find((m) => m.id === s.id) || {}).type;
        const roleTag = STRUCT_ROLE[typ] || "保卫目标";
        html = `<div class="mt-title">★ ${esc(s.name)}<span class="mt-kind">${esc(roleTag)}</span></div>
          <div>${STRUCT_INFO[typ] || "需要保护的城市关键设施。"}</div>
          <div class="mt-row">耐久 ${s.hp}/${s.maxHp}${s.destroyed ? " · 已摧毁" : " · 敌方空袭走廊终点"}</div>`;
      } else if (state.snapshot) {
        const t = pickNearest(state.snapshot.tracks || [], (x) => worldToCanvas(x.pos, 140), px, py, 16);
        if (t) {
          const kind = t.identifiedAsDecoy ? "诱饵（不用管）" : (t.quality >= 3 || t.classified ? (TAG_CN[t.tag] || t.tag) : "类型未知");
          html = `<div class="mt-title">敌方目标 T-${t.id}<span class="mt-kind">${esc(kind)}</span></div>
            <div>${Q_CN[t.quality] || ""}${t.quality < 2 ? "——还不能开火，需要更近或更好的探测。" : "——射程内的防空武器会自动开火。"}</div>
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
    const mainBattleUnit = snap.units.find((u) => u.unitDefId === "nasams")
      || snap.units.find((u) => u.category === "fire")
      || snap.units[0];
    state.selectedUnitKey = mainBattleUnit ? mainBattleUnit.id : null;
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
      const names = (meta.structures || []).map((s) => `★ ${s.name}`).join("、");
      $("brief-goal").innerHTML = `核心目标：死守<b>${esc(names)}</b>，用<b>皮卡高射机枪</b>拦截廉价无人机、用<b>IRIS‑T / NASAMS 防空导弹</b>拦截巡航导弹，撑到 <b>06:00 拂晓</b>。`;
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
    const sel = () => state.placements.find((p) => p.unitDefId === "nasams")
      || state.placements.find((p) => p.rosterId === state.selectedUnitKey)
      || state.placements[0];
    Coach.run([
      {
        title: "这三个 ★ 白色地标是你要保卫的城市命脉",
        text: "<b>★ 热电厂、★ 中心变电站、★ 水厂</b>。地图上的红色虚线箭头标出了敌机冲向它们的攻击走廊。<b>热电厂最重要</b>——它一倒，全城断电。",
        target: () => rectFromWorld((meta.structures || []).map((s) => s.pos), 38),
      },
      {
        title: "敌人从两条走廊袭来",
        text: "<b>东面走廊</b>是成群的廉价自杀式无人机（冲向热电厂），<b>西北河谷走廊</b>是贴地低飞的巡航导弹（冲向水厂与变电站）。",
        target: () => rectFromWorld([[600, 13600], [19400, 18600]], 10),
      },
      {
        title: "你指挥的 3 种防空武器（6 部火力 + 1 座雷达）",
        text: "<b>皮卡高射机枪组 ×4</b>（双联12.7mm机枪+探照灯，无限子弹专打无人机）、<b>IRIS‑T 近程导弹</b>与<b>NASAMS 中程导弹</b>（宝贵导弹专打巡航导弹）。小圆点是自动工作的听音哨，战中不用管。",
        target: () => { const u = sel(); return u ? rectFromWorld([u.pos], 36) : null; },
        onEnter: () => { const u = sel(); if (u) { state.selectedUnitKey = u.rosterId; renderRosterAndInspector(); } },
      },
      {
        title: "红色斜线 = 雷达低空盲区",
        text: "山脊背面雷达照不到低空。把<b>警戒雷达</b>或辅助小圆点（听音哨/观察哨）拖过山脊，就能为防空武器照亮盲区。",
        target: "#coverage-summary",
      },
      {
        title: "懒得摆？一键切换预设阵型",
        text: "<b>推荐</b>阵型已经把皮卡机枪顶在无人机来路上、把导弹护在热电厂旁。也可以试试<b>抱团</b>对比效果。",
        target: ".preset-row",
      },
      {
        title: "右栏顶部看保卫目标，参谋随时给建议",
        text: "右侧第一张卡实时显示三座保卫设施的血量；下方的<b>参谋建议</b>每条都带一键执行按钮。",
        target: "#structures-card",
      },
      {
        title: "准备好了就开战",
        text: "开战后防空武器会<b>自动瞄准开火</b>。你主要负责管理<b>雷达开关、导弹省弹纪律（只打导弹）与防空警报</b>。",
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
    document.querySelectorAll("#d1-preset-cards .d-preset-card").forEach((b) => b.addEventListener("click", () => applyPreset(b.dataset.preset)));
    document.querySelectorAll("#d1-alt-seg .seg-btn").forEach((b) => b.addEventListener("click", async () => {
      state.losAltM = Number(b.dataset.alt);
      if ($("sel-los-alt")) $("sel-los-alt").value = String(state.losAltM);
      if (state.losAltM > 0) await refreshCoverage();
      else renderD1();
    }));

    // 底部 D1–D7 指挥台器械栏、顶部标签与 KPI 槽点击绑定
    document.querySelectorAll(".desk-prop-btn[data-drawer]").forEach((b) => {
      b.addEventListener("click", () => toggleDrawer(Number(b.dataset.drawer)));
    });
    document.querySelectorAll(".drawer-tab-btn[data-drawer-tab]").forEach((b) => {
      b.addEventListener("click", () => toggleDrawer(Number(b.dataset.drawerTab)));
    });
    document.querySelectorAll("[data-open-drawer]").forEach((b) => {
      b.addEventListener("click", () => toggleDrawer(Number(b.dataset.openDrawer)));
    });
    if ($("drawer-close-btn")) $("drawer-close-btn").addEventListener("click", closeDrawer);
    if ($("btn-close-inspector")) $("btn-close-inspector").addEventListener("click", () => {
      state.inspectorOpen = false;
      renderRosterAndInspector();
    });

    // D3 批量火控与电磁条令按钮
    if ($("btn-d3-all-missile-only")) {
      $("btn-d3-all-missile-only").addEventListener("click", async () => {
        for (const u of getActiveUnits().filter((x) => x.unitDefId === "nasams" || x.unitDefId === "iris_t_sls")) {
          const w0 = u.weapons && u.weapons[0];
          if (w0) await applyUnitDoctrine(u, w0.weaponId || w0.id, "missile_only");
        }
        Toast.show({ kind: "good", icon: "✓", title: "全军防空导弹已设为「只打导弹（省弹）」" });
        renderRosterAndInspector();
      });
    }
    if ($("btn-d3-all-open")) {
      $("btn-d3-all-open").addEventListener("click", async () => {
        for (const u of getActiveUnits().filter((x) => x.unitDefId === "nasams" || x.unitDefId === "iris_t_sls")) {
          const w0 = u.weapons && u.weapons[0];
          if (w0) await applyUnitDoctrine(u, w0.weaponId || w0.id, "all_open");
        }
        Toast.show({ kind: "info", icon: "✓", title: "全军防空导弹已设为「无人机也打（全开）」" });
        renderRosterAndInspector();
      });
    }
    document.querySelectorAll("[data-batch-pol]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const pol = btn.dataset.batchPol;
        const radars = getActiveUnits().filter((u) => (u.emitter && u.emitter.hasEmitter) || u.hasRadar || u.unitDefId === "soviet_mid_range_radar" || u.unitDefId === "nasams");
        for (const u of radars) await setPolicy(u, pol);
        Toast.show({ kind: "info", icon: "✓", title: `全军雷达已切为「${pol === "continuous" ? "常开" : (pol === "blink" ? "闪烁" : "静默")}」` });
      });
    });

    // D5 / D7 快捷按钮
    if ($("btn-d5-alert-toggle")) $("btn-d5-alert-toggle").addEventListener("click", () => $("btn-alert-toggle").click());
    if ($("btn-d5-spoof")) $("btn-d5-spoof").addEventListener("click", () => $("btn-national-spoof").click());
    if ($("btn-d7-briefing")) $("btn-d7-briefing").addEventListener("click", () => { closeDrawer(); showBriefing(); });
    if ($("btn-d7-tutorial")) $("btn-d7-tutorial").addEventListener("click", () => { closeDrawer(); $("btn-restart-tutorial").click(); });
    if ($("btn-d7-choice-demo")) $("btn-d7-choice-demo").addEventListener("click", () => { closeDrawer(); $("btn-trigger-choice-demo").click(); });
    if ($("btn-d7-reset")) $("btn-d7-reset").addEventListener("click", () => { closeDrawer(); $("btn-reset-game").click(); });

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

    // 地图缩放与主界面缩放按钮
    if ($("btn-zoom-in")) $("btn-zoom-in").addEventListener("click", () => stepMapZoom(1.28));
    if ($("btn-zoom-out")) $("btn-zoom-out").addEventListener("click", () => stepMapZoom(1 / 1.28));
    if ($("btn-zoom-reset")) $("btn-zoom-reset").addEventListener("click", resetMapZoom);
    if ($("btn-tb-zoom-in")) $("btn-tb-zoom-in").addEventListener("click", () => stepMapZoom(1.28));
    if ($("btn-tb-zoom-out")) $("btn-tb-zoom-out").addEventListener("click", () => stepMapZoom(1 / 1.28));
    if ($("btn-tb-zoom-reset")) $("btn-tb-zoom-reset").addEventListener("click", resetMapZoom);

    if ($("btn-ui-zoom-in")) $("btn-ui-zoom-in").addEventListener("click", () => applyUiScale((state.uiScale || 1) + 0.1));
    if ($("btn-ui-zoom-out")) $("btn-ui-zoom-out").addEventListener("click", () => applyUiScale((state.uiScale || 1) - 0.1));
    if ($("btn-ui-zoom-reset")) $("btn-ui-zoom-reset").addEventListener("click", () => applyUiScale(1.0));
    const savedUiScale = Number(LS.get("nw_ui_scale"));
    if (savedUiScale >= 0.8 && savedUiScale <= 1.3 && savedUiScale !== 1) applyUiScale(savedUiScale);

    // 鼠标滚轮 / 触控板双指缩放（以光标为中心）
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const [px, py] = canvasXY(e);
      const factor = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0022));
      stepMapZoom(factor, px, py);
    }, { passive: false });

    // 双击地图空白处快速放大 / 复位
    canvas.addEventListener("dblclick", (e) => {
      if (pickUnitAt(e, 18)) return;
      const [px, py] = canvasXY(e);
      const view = window.TacticalRenderer.getView(canvas);
      if ((view.zoom || 1) >= 2.2) resetMapZoom();
      else {
        window.TacticalRenderer.zoomAt(canvas, Math.min(4.0, (view.zoom || 1) * 1.75), px, py);
        updateZoomReadout();
      }
    });

    canvas.addEventListener("mousedown", (e) => {
      const best = pickUnitAt(e, 18);
      if (best && e.button === 0) {
        state.selectedUnitKey = unitKey(best);
        state.inspectorOpen = true;
        if (state.phase === "deploy" && best.mobility !== "fixed") {
          state.draggingUnit = best;
          canvas.classList.add("grabbing");
          $("map-tip").classList.add("hidden");
          renderRosterAndInspector();
          return;
        }
        renderRosterAndInspector();
        return;
      }
      // 点击地图空白处时：若抽屉打开则收起抽屉
      if (state.openDrawerIndex !== 0 && e.button === 0) {
        closeDrawer();
      }
      // 放大状态下（或按住中键/右键）拖曳空白处平移地图
      const view = window.TacticalRenderer.getView(canvas);
      if ((view.zoom || 1) > 1.01 || e.button === 1 || e.button === 2) {
        const [px, py] = canvasXY(e);
        state.panningMap = { lastX: px, lastY: py };
        canvas.classList.add("panning");
        $("map-tip").classList.add("hidden");
      }
    });
    canvas.addEventListener("mousemove", (e) => {
      if (!state.meta) return;
      const [px, py] = canvasXY(e);
      const view = window.TacticalRenderer.getView(canvas);
      if (state.panningMap) {
        const dx = px - state.panningMap.lastX;
        const dy = py - state.panningMap.lastY;
        state.panningMap.lastX = px;
        state.panningMap.lastY = py;
        window.TacticalRenderer.panBy(canvas, dx, dy);
        return;
      }
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
      if (state.panningMap) {
        state.panningMap = null;
        canvas.classList.remove("panning");
      }
      await finishUnitDrag();
    });

    // ───────────── iPad / 触屏手势：双指捏合缩放 + 双指平移 + 单指拖拽部署 + 双击缩放 ─────────────
    let touchPinch = null;
    let lastTapInfo = { t: 0, x: 0, y: 0 };

    canvas.addEventListener("touchstart", (e) => {
      if (!state.meta) return;
      if (e.touches.length >= 2) {
        e.preventDefault();
        state.draggingUnit = null;
        state.panningMap = null;
        canvas.classList.remove("grabbing", "panning");
        $("map-tip").classList.add("hidden");
        const [x0, y0] = canvasXY(e.touches[0]);
        const [x1, y1] = canvasXY(e.touches[1]);
        touchPinch = {
          lastDist: Math.max(10, Math.hypot(x1 - x0, y1 - y0)),
          lastMidX: (x0 + x1) * 0.5,
          lastMidY: (y0 + y1) * 0.5,
        };
        return;
      }
      if (e.touches.length === 1) {
        e.preventDefault();
        touchPinch = null;
        const t = e.touches[0];
        const [px, py] = canvasXY(t);
        const best = pickUnitAt(t, 26); // iPad 触控拾取半径放宽到 26px，方便手指点选
        if (best) {
          state.selectedUnitKey = unitKey(best);
          state.inspectorOpen = true;
          renderRosterAndInspector();
          if (state.phase === "deploy" && best.mobility !== "fixed") {
            state.draggingUnit = best;
            canvas.classList.add("grabbing");
            $("map-tip").classList.add("hidden");
          } else {
            showMapTip(t);
            state.panningMap = { lastX: px, lastY: py };
          }
          return;
        }
        // 双击空白处快速放大或复位
        const now = performance.now();
        if (now - lastTapInfo.t < 300 && Math.hypot(px - lastTapInfo.x, py - lastTapInfo.y) < 30) {
          const view = window.TacticalRenderer.getView(canvas);
          if ((view.zoom || 1) >= 1.8) resetMapZoom();
          else {
            window.TacticalRenderer.zoomAt(canvas, Math.min(4.0, (view.zoom || 1) * 1.9), px, py);
            updateZoomReadout();
          }
          lastTapInfo.t = 0;
          return;
        }
        lastTapInfo = { t: now, x: px, y: py };
        showMapTip(t);
        state.panningMap = { lastX: px, lastY: py };
      }
    }, { passive: false });

    canvas.addEventListener("touchmove", (e) => {
      if (!state.meta) return;
      if (e.touches.length >= 2) {
        e.preventDefault();
        const [x0, y0] = canvasXY(e.touches[0]);
        const [x1, y1] = canvasXY(e.touches[1]);
        const dist = Math.max(10, Math.hypot(x1 - x0, y1 - y0));
        const midX = (x0 + x1) * 0.5;
        const midY = (y0 + y1) * 0.5;
        if (!touchPinch) {
          touchPinch = { lastDist: dist, lastMidX: midX, lastMidY: midY };
          return;
        }
        const view = window.TacticalRenderer.getView(canvas);
        const newZ = (view.zoom || 1) * (dist / touchPinch.lastDist);
        window.TacticalRenderer.zoomAt(canvas, newZ, touchPinch.lastMidX, touchPinch.lastMidY, midX, midY);
        touchPinch.lastDist = dist;
        touchPinch.lastMidX = midX;
        touchPinch.lastMidY = midY;
        updateZoomReadout();
        return;
      }
      if (e.touches.length === 1 && !touchPinch) {
        e.preventDefault();
        const t = e.touches[0];
        const [px, py] = canvasXY(t);
        const view = window.TacticalRenderer.getView(canvas);
        if (state.draggingUnit && state.phase === "deploy") {
          const pt = window.TacticalRenderer.screenToWorld(px, py, view, state.viewMode);
          state.draggingUnit.pos = [Math.round(pt[0]), Math.round(pt[1])];
          const col = String.fromCharCode(65 + Math.min(7, Math.floor(pt[0] / 2500)));
          const row = 8 - Math.min(7, Math.floor(pt[1] / 2500));
          $("hover-telemetry").textContent = `移动 #${state.draggingUnit.rosterId} → 方格 ${col}${row} · X ${(pt[0] / 1000).toFixed(2)} km · Y ${(pt[1] / 1000).toFixed(2)} km`;
          return;
        }
        if (state.panningMap) {
          const dx = px - state.panningMap.lastX;
          const dy = py - state.panningMap.lastY;
          state.panningMap.lastX = px;
          state.panningMap.lastY = py;
          window.TacticalRenderer.panBy(canvas, dx, dy);
        }
      }
    }, { passive: false });

    const onTouchEnd = async (e) => {
      if (e.touches.length < 2) touchPinch = null;
      if (e.touches.length === 0) {
        state.panningMap = null;
        canvas.classList.remove("panning");
        await finishUnitDrag();
      }
    };
    canvas.addEventListener("touchend", onTouchEnd);
    canvas.addEventListener("touchcancel", onTouchEnd);
    // 阻止 iPadOS Safari 在画布上触发系统级页面捏合抖动
    canvas.addEventListener("gesturestart", (e) => e.preventDefault(), { passive: false });
    canvas.addEventListener("gesturechange", (e) => e.preventDefault(), { passive: false });

    window.addEventListener("keydown", (e) => {
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (e.code === "Escape") {
        if (Coach.active) { Coach.stop(false); return; }
        if (state.openDrawerIndex !== 0) { closeDrawer(); return; }
        if (state.inspectorOpen) { state.inspectorOpen = false; renderRosterAndInspector(); return; }
        closeMore();
        if (!$("briefing-modal").classList.contains("hidden")) closeBriefing();
        return;
      }
      if (/^F[1-7]$/.test(e.code)) {
        e.preventDefault();
        toggleDrawer(Number(e.code.slice(1)));
        return;
      }
      if (e.code === "Space" && state.phase === "battle") { e.preventDefault(); setSpeed(state.speed > 0 ? 0 : 1); }
      else if (e.code === "Tab") { e.preventDefault(); toggleViewMode(); }
      else if (e.code === "KeyN") skipToNextContact();
      else if (e.code === "Equal" || e.code === "NumpadAdd") { e.preventDefault(); stepMapZoom(1.28); }
      else if (e.code === "Minus" || e.code === "NumpadSubtract") { e.preventDefault(); stepMapZoom(1 / 1.28); }
      else if (e.code === "Digit0" || e.code === "Numpad0") { e.preventDefault(); resetMapZoom(); }
      else if (state.phase === "battle" && ["Digit1", "Digit2", "Digit3"].includes(e.code)) {
        setSpeed({ Digit1: 1, Digit2: 4, Digit3: 8 }[e.code]);
      }
    });
    if (window.ResizeObserver) new ResizeObserver(fitCanvas).observe($("canvas-wrapper"));
    window.addEventListener("resize", fitCanvas);
  }
  function closeMore() { $("more-dd").classList.remove("open"); }

  // 调试/截图辅助：?demo=battle&ticks=600&view=live25d&god=1&bot=smart_blink&tutorial=0&drawer=3&inspect=1
  async function runDemoFromUrl() {
    const q = new URLSearchParams(location.search);
    if (q.get("view") === "live25d") setViewMode("live25d");
    if (q.get("god") === "1") { state.godView = true; $("chk-god-view").checked = true; }
    if (q.get("inspect") === "1") { state.inspectorOpen = true; renderRosterAndInspector(); }
    if (q.get("drawer")) { openDrawer(Number(q.get("drawer"))); }
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
      if (q.get("drawer")) openDrawer(Number(q.get("drawer")));
      return;
    }
    if (q.get("tutorial") === "1") { runDeployTutorial(); return; }
    if (q.get("drawer") || q.get("inspect") === "1") return;
    if (q.get("brief") === "1" || !LS.get("nw_seen_brief")) showBriefing();
  }

  bindGlobalEvents();
  fitCanvas();
  setPhase("deploy");
  requestAnimationFrame(animLoop);
  initGame(1, true).then(runDemoFromUrl);
})();
