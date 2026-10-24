// 《守夜》Nightwatch 战术画布双视图渲染引擎 (指挥台平面图 + 2.5D 25° 实况斜视角)
// 说明：所有绘制使用"逻辑像素"坐标（CSS 像素），通过 devicePixelRatio 变换保证高分屏清晰。
(function () {
  const MAP_SIZE_M = 20000;
  const PAD = 26; // 平面图四周留白（逻辑像素），用于坐标格标注

  // 我方单位统一用北约军标"友军蓝"系，按类别细分明度/色相
  const CAT_COLORS = { fire: "#5fb6ff", sensor: "#7fe0e0", ew: "#a9a4ff", deception: "#66778a" };
  // 航迹质量：灰(刚发现) → 黄(未知) → 橙 → 红(敌对·已识别)，对应北约军标未知/敌对色
  const Q_COLORS = ["#66778a", "#f5cf47", "#ff9a3c", "#ff5b4f"];

  const cache = {
    terrainKey: "", terrain: { command: null, live25d: null },
    covRef: null, covKey: "", covLayer: null,
    lights: null, lightsKey: "",
    hatchRed: null, hatchRedSoft: null,
    trails: new Map(), lastTick: -1,
  };

  // ───────────────────────── 坐标投影与镜头缩放 ─────────────────────────
  const MIN_ZOOM = 1.0;
  const MAX_ZOOM = 4.0;

  function getView(canvas) {
    return canvas._view || { width: canvas.width, height: canvas.height, dpr: 1, zoom: 1, panX: 0, panY: 0 };
  }

  // 全屏画布（地图铺满整个视口，界面以浮层叠加其上，参照 DEFCON）：
  // view.safe = 被 HUD 浮层占用的四边留白 {l,t,r,b}（逻辑像素）；
  // lb = 画布内标注（比例尺、射程标签）的底部留白，额外避开无线电字幕条。
  // 作战区（AO）正方形在安全区内居中，未缩放时完整可见；安全区之外照常绘制“区外地形”。
  function safeOf(view) {
    const s = view.safe || {};
    return { l: s.l || 0, t: s.t || 0, r: s.r || 0, b: s.b || 0, lb: Math.max(s.lb || 0, s.b || 0) };
  }

  // 基准（缩放=1）地图外框：含 PAD 坐标标注带的正方形 {x, y, s}
  function mapFrame(view) {
    const sa = safeOf(view);
    const aw = Math.max(120, view.width - sa.l - sa.r);
    const ah = Math.max(120, view.height - sa.t - sa.b);
    const s = Math.min(aw, ah);
    return { x: sa.l + (aw - s) / 2, y: sa.t + (ah - s) / 2, s };
  }

  // 基准比例尺：每米对应的逻辑像素（缩放=1）
  function basePxPerM(view) {
    return (mapFrame(view).s - PAD * 2) / MAP_SIZE_M;
  }

  function clampCamera(view) {
    const z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, view.zoom || 1));
    view.zoom = z;
    if (z <= 1.001) {
      view.zoom = 1.0;
      view.panX = 0;
      view.panY = 0;
      return;
    }
    // 允许把 AO 任一边缘拖到安全区边缘（再多留一点余量），但不允许整张图被拖出视野
    const f = mapFrame(view);
    const sa = safeOf(view);
    const cx = view.width * 0.5, cy = view.height * 0.5;
    const slack = 48;
    const axis = (lo0, hi0, c, safeLo, safeHi) => {
      const L = c + (lo0 - c) * z, R = c + (hi0 - c) * z;
      const lo = safeHi - slack - R; // 右（下）缘不得离开安全区
      const hi = safeLo + slack - L; // 左（上）缘不得离开安全区
      return lo > hi ? [(lo + hi) / 2, (lo + hi) / 2] : [lo, hi];
    };
    const [x0, x1] = axis(f.x + PAD, f.x + f.s - PAD, cx, sa.l, view.width - sa.r);
    const [y0, y1] = axis(f.y + PAD, f.y + f.s - PAD, cy, sa.t, view.height - sa.b);
    view.panX = Math.max(x0, Math.min(x1, view.panX || 0));
    view.panY = Math.max(y0, Math.min(y1, view.panY || 0));
  }

  function zoomAt(canvas, newZoom, anchorX, anchorY, newAnchorX, newAnchorY) {
    const view = getView(canvas);
    const oldZ = view.zoom || 1;
    const targetZ = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom));
    // 未指定锚点（按钮 / 键盘缩放）时以 HUD 安全区中心为锚，而非画布中心
    const sa = safeOf(view);
    const ax0 = anchorX !== undefined ? anchorX : sa.l + (view.width - sa.l - sa.r) * 0.5;
    const ay0 = anchorY !== undefined ? anchorY : sa.t + (view.height - sa.t - sa.b) * 0.5;
    const ax1 = newAnchorX !== undefined ? newAnchorX : ax0;
    const ay1 = newAnchorY !== undefined ? newAnchorY : ay0;
    const cx = view.width * 0.5;
    const cy = view.height * 0.5;
    const bx = cx + (ax0 - cx - (view.panX || 0)) / oldZ;
    const by = cy + (ay0 - cy - (view.panY || 0)) / oldZ;
    view.zoom = targetZ;
    view.panX = ax1 - cx - (bx - cx) * targetZ;
    view.panY = ay1 - cy - (by - cy) * targetZ;
    clampCamera(view);
    return view.zoom;
  }

  function panBy(canvas, dx, dy) {
    const view = getView(canvas);
    view.panX = (view.panX || 0) + dx;
    view.panY = (view.panY || 0) + dy;
    clampCamera(view);
  }

  function resetCamera(canvas) {
    const view = getView(canvas);
    view.zoom = 1.0;
    view.panX = 0;
    view.panY = 0;
  }

  function baseWorldToScreen(wx, wy, altM, view, viewMode, elevM) {
    const f = mapFrame(view);
    const S = f.s;
    const nx = wx / MAP_SIZE_M;
    const ny = 1.0 - wy / MAP_SIZE_M;
    if (viewMode !== "live25d") {
      return { x: f.x + PAD + nx * (S - PAD * 2), y: f.y + PAD + ny * (S - PAD * 2), scale: 1.0 };
    }
    // 25° 俯角 2.5D 透视投影：北端略收窄，地形海拔与目标高度向上抬升
    const persp = 0.72 + 0.28 * ny;
    const sx = f.x + S * 0.5 + (nx - 0.5) * (S * 0.86) * persp;
    const baseSy = f.y + S * 0.13 + Math.pow(Math.max(0, ny), 0.92) * (S * 0.79);
    const groundZ = (elevM || 0) * 0.08 * (S / 920);
    const totalZ = groundZ + (altM || 0) * 0.055 * (S / 920);
    return { x: sx, y: baseSy - totalZ, groundY: baseSy - groundZ, scale: persp };
  }

  function worldToScreen(wx, wy, altM, view, viewMode, elevM) {
    const b = baseWorldToScreen(wx, wy, altM, view, viewMode, elevM);
    const z = view.zoom || 1;
    const px = view.panX || 0;
    const py = view.panY || 0;
    if (z === 1 && px === 0 && py === 0) return b;
    const cx = view.width * 0.5;
    const cy = view.height * 0.5;
    const sx = cx + (b.x - cx) * z + px;
    const sy = cy + (b.y - cy) * z + py;
    const groundY = b.groundY !== undefined ? cy + (b.groundY - cy) * z + py : undefined;
    return { x: sx, y: sy, groundY, scale: b.scale };
  }

  function screenToWorld(px, py, view, viewMode) {
    const W = view.width;
    const H = view.height;
    const z = view.zoom || 1;
    const panX = view.panX || 0;
    const panY = view.panY || 0;
    const cx = W * 0.5;
    const cy = H * 0.5;
    const bx = cx + (px - cx - panX) / z;
    const by = cy + (py - cy - panY) / z;
    const f = mapFrame(view);
    const S = f.s;
    if (viewMode !== "live25d") {
      const nx = (bx - f.x - PAD) / (S - PAD * 2);
      const ny = (by - f.y - PAD) / (S - PAD * 2);
      return [
        Math.max(0, Math.min(MAP_SIZE_M, nx * MAP_SIZE_M)),
        Math.max(0, Math.min(MAP_SIZE_M, (1.0 - ny) * MAP_SIZE_M)),
      ];
    }
    const rawNy = Math.max(0, Math.min(1, (by - f.y - S * 0.13) / (S * 0.79)));
    const ny = Math.pow(rawNy, 1 / 0.92);
    const persp = 0.72 + 0.28 * ny;
    const nx = 0.5 + (bx - f.x - S * 0.5) / ((S * 0.86) * persp);
    return [
      Math.max(0, Math.min(MAP_SIZE_M, nx * MAP_SIZE_M)),
      Math.max(0, Math.min(MAP_SIZE_M, (1.0 - ny) * MAP_SIZE_M)),
    ];
  }

  function sampleElevation(meta, wx, wy) {
    if (!meta || !meta.map || !meta.map.elevationGrid) return 110;
    const g = meta.map.elevationGrid;
    const N = g.length;
    const ix = Math.max(0, Math.min(N - 1, Math.floor((wx / MAP_SIZE_M) * N)));
    const iy = Math.max(0, Math.min(N - 1, Math.floor((wy / MAP_SIZE_M) * N)));
    return g[iy][ix];
  }

  // 双线性插值高程（仅用于渲染平滑，不参与模拟）
  function sampleElevSmooth(g, N, wx, wy) {
    const step = MAP_SIZE_M / N;
    const fx = Math.max(0, Math.min(N - 1.001, wx / step - 0.5));
    const fy = Math.max(0, Math.min(N - 1.001, wy / step - 0.5));
    const x0 = Math.floor(fx), y0 = Math.floor(fy);
    const tx = fx - x0, ty = fy - y0;
    const x1 = Math.min(N - 1, x0 + 1), y1 = Math.min(N - 1, y0 + 1);
    const a = g[y0][x0] * (1 - tx) + g[y0][x1] * tx;
    const b = g[y1][x0] * (1 - tx) + g[y1][x1] * tx;
    return a * (1 - ty) + b * ty;
  }

  const P = (pt, view, mode, meta, alt) =>
    worldToScreen(pt[0], pt[1], alt || 0, view, mode, sampleElevation(meta, pt[0], pt[1]));

  // ───────────────────────── 配色工具 ─────────────────────────
  const RAMP = [
    [0.0, [13, 18, 24]], [0.3, [17, 23, 30]], [0.55, [22, 30, 39]],
    [0.78, [31, 41, 52]], [1.0, [48, 60, 73]],
  ];
  function rampColor(t) {
    for (let i = 1; i < RAMP.length; i++) {
      if (t <= RAMP[i][0]) {
        const [t0, c0] = RAMP[i - 1], [t1, c1] = RAMP[i];
        const k = (t - t0) / (t1 - t0);
        return [c0[0] + (c1[0] - c0[0]) * k, c0[1] + (c1[1] - c0[1]) * k, c0[2] + (c1[2] - c0[2]) * k];
      }
    }
    return RAMP[RAMP.length - 1][1];
  }

  function makeHatch(color, bg, spacing, lw) {
    const c = document.createElement("canvas");
    c.width = c.height = spacing;
    const x = c.getContext("2d");
    if (bg) { x.fillStyle = bg; x.fillRect(0, 0, spacing, spacing); }
    x.strokeStyle = color; x.lineWidth = lw;
    x.beginPath();
    x.moveTo(-1, spacing + 1); x.lineTo(spacing + 1, -1);
    x.moveTo(-1, 1); x.lineTo(1, -1);
    x.moveTo(spacing - 1, spacing + 1); x.lineTo(spacing + 1, spacing - 1);
    x.stroke();
    return c;
  }

  function hash01(n) {
    const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return s - Math.floor(s);
  }

  function pointInPoly(x, y, pts) {
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  // ───────────────────────── 静态地形缓存 ─────────────────────────
  // 渲染用值噪声（确定性哈希，仅用于区外地形外观，不参与模拟）
  function valueNoise(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y);
    const xf = x - xi, yf = y - yi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    const h = (a, b) => hash01(a * 157.31 + b * 311.17);
    const a = h(xi, yi), b = h(xi + 1, yi), c = h(xi, yi + 1), d = h(xi + 1, yi + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  function fbm(x, y) {
    let s = 0, amp = 0.5, f = 1;
    for (let o = 0; o < 4; o++) { s += amp * valueNoise(x * f, y * f); f *= 2.03; amp *= 0.5; }
    return s / 0.9375;
  }
  // 作战区外的渲染高程：AO 边缘高程按距离指数衰减到程序噪声地形
  function surroundElev(g, N, wx, wy, minE, maxE) {
    const cxm = Math.max(0, Math.min(MAP_SIZE_M, wx)), cym = Math.max(0, Math.min(MAP_SIZE_M, wy));
    const d = Math.hypot(wx - cxm, wy - cym);
    const edge = sampleElevSmooth(g, N, cxm, cym);
    const n = minE + (maxE - minE) * (0.15 + 0.7 * fbm(wx / 5200 + 17.3, wy / 5200 - 4.1));
    const b = Math.exp(-d / 3500);
    return edge * b + n * (1 - b);
  }

  // 区外地形：作战区之外延伸的低对比晕渲（AO 边缘高程平滑过渡到程序噪声），让地图铺满全屏
  function drawSurroundTerrain(ctx, meta, view) {
    const { width: W, height: H, dpr } = view;
    const f = mapFrame(view);
    const g = meta.map.elevationGrid || [];
    const N = g.length;
    if (!N) return;
    const minE = meta.map.minElevationM || 80;
    const maxE = Math.max(minE + 10, meta.map.maxElevationM || 320);
    const inner = f.s - PAD * 2;
    const mPerCss = MAP_SIZE_M / inner;
    const k = Math.max(1, Math.round(2 / Math.min(1.5, dpr))); // 每纹素约 2 个逻辑像素
    const TW = Math.ceil(W / k) + 2, TH = Math.ceil(H / k) + 2;
    const E = new Float32Array(TW * TH);
    const mPerTex = mPerCss * k;
    for (let ty = 0; ty < TH; ty++) {
      const wy = (1 - ((ty * k) - f.y - PAD) / inner) * MAP_SIZE_M;
      for (let tx = 0; tx < TW; tx++) {
        const wx = (((tx * k) - f.x - PAD) / inner) * MAP_SIZE_M;
        E[ty * TW + tx] = surroundElev(g, N, wx, wy, minE, maxE);
      }
    }
    const img = ctx.createImageData(TW, TH);
    const dd = img.data;
    const L = [-0.5, 0.5, 0.707];
    const zx = 3.2;
    for (let ty = 0; ty < TH; ty++) {
      for (let tx = 0; tx < TW; tx++) {
        const i = ty * TW + tx;
        const e = E[i];
        const eL = E[ty * TW + Math.max(0, tx - 1)], eR = E[ty * TW + Math.min(TW - 1, tx + 1)];
        const eU = E[Math.max(0, ty - 1) * TW + tx], eD = E[Math.min(TH - 1, ty + 1) * TW + tx];
        const dzdx = ((eR - eL) / (2 * mPerTex)) * zx;
        const dzdy = ((eU - eD) / (2 * mPerTex)) * zx;
        const nl = Math.hypot(dzdx, dzdy, 1);
        const shade = Math.max(0, (-dzdx * L[0] - dzdy * L[1] + L[2]) / nl);
        const t = Math.max(0, Math.min(1, (e - minE) / (maxE - minE)));
        const c = rampColor(t);
        const kk = (0.5 + 0.75 * shade) * 0.8; // 区外略压暗，突出作战区
        let r = c[0] * kk, gg = c[1] * kk, bb = c[2] * kk;
        const band = Math.floor(e / 20);
        if (band !== Math.floor(eR / 20) || band !== Math.floor(eD / 20)) {
          r = r * 0.93 + 90 * 0.07; gg = gg * 0.93 + 112 * 0.07; bb = bb * 0.93 + 135 * 0.07;
        }
        dd[i * 4] = r; dd[i * 4 + 1] = gg; dd[i * 4 + 2] = bb; dd[i * 4 + 3] = 255;
      }
    }
    const tex = document.createElement("canvas");
    tex.width = TW; tex.height = TH;
    tex.getContext("2d").putImageData(img, 0, 0);
    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(tex, 0, 0, TW * k, TH * k);
    // 区外 2.5 km 参考网格（与作战区方格对齐，营造“标图桌”的延伸感）
    ctx.strokeStyle = "rgba(120, 150, 180, 0.1)";
    ctx.lineWidth = 1;
    const cell = 2500 / mPerCss;
    const ox = f.x + PAD, oy = f.y + PAD;
    ctx.beginPath();
    for (let x = ox - Math.ceil(ox / cell) * cell; x <= W; x += cell) { ctx.moveTo(Math.round(x) + 0.5, 0); ctx.lineTo(Math.round(x) + 0.5, H); }
    for (let y = oy - Math.ceil(oy / cell) * cell; y <= H; y += cell) { ctx.moveTo(0, Math.round(y) + 0.5); ctx.lineTo(W, Math.round(y) + 0.5); }
    ctx.stroke();
    ctx.restore();
  }

  function buildTerrainCommand(meta, view) {
    const { width: W, height: H, dpr } = view;
    const fr = mapFrame(view);
    const inner = fr.s - PAD * 2;
    const off = document.createElement("canvas");
    off.width = Math.round(W * dpr); off.height = Math.round(H * dpr);
    const ctx = off.getContext("2d");
    ctx.fillStyle = "#080b0f";
    ctx.fillRect(0, 0, off.width, off.height);
    if (!meta || !meta.map) return off;

    drawSurroundTerrain(ctx, meta, view);

    const g = meta.map.elevationGrid || [];
    const N = g.length;
    const minE = meta.map.minElevationM || 80;
    const maxE = Math.max(minE + 10, meta.map.maxElevationM || 320);

    // 1) 生成高分辨率晕渲 + 等高线纹理
    const S = Math.max(64, Math.min(1400, Math.round(inner * dpr)));
    const mPerPx = MAP_SIZE_M / S;
    const E = new Float32Array(S * S);
    for (let py = 0; py < S; py++) {
      const wy = (1 - (py + 0.5) / S) * MAP_SIZE_M;
      for (let px = 0; px < S; px++) {
        E[py * S + px] = sampleElevSmooth(g, N, ((px + 0.5) / S) * MAP_SIZE_M, wy);
      }
    }
    const img = ctx.createImageData(S, S);
    const d = img.data;
    const L = [-0.5, 0.5, 0.707]; // 西北方向斜照
    const zx = 3.2;
    for (let py = 0; py < S; py++) {
      for (let px = 0; px < S; px++) {
        const i = py * S + px;
        const e = E[i];
        const eL = E[py * S + Math.max(0, px - 1)], eR = E[py * S + Math.min(S - 1, px + 1)];
        const eU = E[Math.max(0, py - 1) * S + px], eD = E[Math.min(S - 1, py + 1) * S + px];
        const dzdx = ((eR - eL) / (2 * mPerPx)) * zx;
        const dzdy = ((eU - eD) / (2 * mPerPx)) * zx;
        const nl = Math.hypot(dzdx, dzdy, 1);
        const shade = Math.max(0, (-dzdx * L[0] - dzdy * L[1] + L[2]) / nl);
        const t = Math.max(0, Math.min(1, (e - minE) / (maxE - minE)));
        const c = rampColor(t);
        const k = 0.5 + 0.75 * shade;
        let r = c[0] * k, gg = c[1] * k, b = c[2] * k;
        // 等高线：20m 细线、100m 粗线
        const band = Math.floor(e / 20);
        if (band !== Math.floor(eR / 20) || band !== Math.floor(eD / 20)) {
          const major = Math.floor(e / 100) !== Math.floor(eR / 100) || Math.floor(e / 100) !== Math.floor(eD / 100);
          const a = major ? 0.32 : 0.13;
          const cc = major ? [120, 165, 200] : [90, 112, 135];
          r = r * (1 - a) + cc[0] * a; gg = gg * (1 - a) + cc[1] * a; b = b * (1 - a) + cc[2] * a;
        }
        d[i * 4] = r; d[i * 4 + 1] = gg; d[i * 4 + 2] = b; d[i * 4 + 3] = 255;
      }
    }
    const tex = document.createElement("canvas");
    tex.width = tex.height = S;
    tex.getContext("2d").putImageData(img, 0, 0);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(tex, fr.x + PAD, fr.y + PAD, inner, inner);
    return off;
  }

  function buildTerrain25D(meta, view) {
    const { width: W, height: H, dpr } = view;
    const fr = mapFrame(view);
    const off = document.createElement("canvas");
    off.width = Math.round(W * dpr); off.height = Math.round(H * dpr);
    const ctx = off.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const horizonY = fr.y + fr.s * 0.13;
    const sky = ctx.createLinearGradient(0, 0, 0, Math.max(40, horizonY + 20));
    sky.addColorStop(0, "#06080c"); sky.addColorStop(1, "#111821");
    ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H);
    if (!meta || !meta.map) return off;

    const g = meta.map.elevationGrid || [];
    const N = g.length;
    const minE = meta.map.minElevationM || 80;
    const maxE = Math.max(minE + 10, meta.map.maxElevationM || 320);
    const step = MAP_SIZE_M / N;
    const inAO = (wx, wy) => wx >= 0 && wx <= MAP_SIZE_M && wy >= 0 && wy <= MAP_SIZE_M;
    const elevAt = (wx, wy) => (inAO(wx, wy) ? sampleElevSmooth(g, N, wx, wy) : surroundElev(g, N, wx, wy, minE, maxE));

    // 区外延伸：横向铺满视口、向南（近景）铺到画面底部；北侧收于地平线
    const halfW = Math.max(fr.x + fr.s * 0.5, W - fr.x - fr.s * 0.5);
    const extraX = Math.max(0, Math.ceil(N * (halfW / (fr.s * 0.86 * 0.72) - 0.5)) + 1);
    const nyMax = Math.pow(Math.max(1, (H - fr.y - fr.s * 0.13) / (fr.s * 0.79)), 1 / 0.92);
    const extraS = Math.max(0, Math.ceil(N * (nyMax - 1)) + 1);

    // 由远（北）至近（南）绘制网格面片
    for (let iy = N - 1; iy >= -extraS; iy--) {
      for (let ix = -extraX; ix < N + extraX; ix++) {
        const x0 = ix * step, x1 = (ix + 1) * step, y0 = iy * step, y1 = (iy + 1) * step;
        const out = !(ix >= 0 && ix < N && iy >= 0);
        const e00 = elevAt(x0, y0), e10 = elevAt(x1, y0), e11 = elevAt(x1, y1), e01 = elevAt(x0, y1);
        const p00 = worldToScreen(x0, y0, 0, view, "live25d", e00);
        const p10 = worldToScreen(x1, y0, 0, view, "live25d", e10);
        const p11 = worldToScreen(x1, y1, 0, view, "live25d", e11);
        const p01 = worldToScreen(x0, y1, 0, view, "live25d", e01);
        if (out && (Math.max(p00.x, p10.x, p11.x, p01.x) < -4 || Math.min(p00.x, p10.x, p11.x, p01.x) > W + 4)) continue;
        const e = out ? (e00 + e10 + e11 + e01) / 4 : g[iy][ix];
        const dzdx = ((e10 + e11) - (e00 + e01)) / (2 * step) * 3.2;
        const dzdy = ((e01 + e11) - (e00 + e10)) / (2 * step) * 3.2;
        const nl = Math.hypot(dzdx, dzdy, 1);
        const shade = Math.max(0, (dzdx * 0.5 - dzdy * 0.5 + 0.707) / nl);
        const t = Math.max(0, Math.min(1, (e - minE) / (maxE - minE)));
        const c = rampColor(t);
        const fog = 0.62 + 0.38 * Math.min(1, 1 - iy / N); // 远处更暗
        const k = (0.5 + 0.75 * Math.min(1, shade)) * fog * (out ? 0.62 : 1);
        const col = `rgb(${(c[0] * k) | 0},${(c[1] * k) | 0},${(c[2] * k) | 0})`;
        ctx.fillStyle = col; ctx.strokeStyle = col; ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(p00.x, p00.y); ctx.lineTo(p10.x, p10.y); ctx.lineTo(p11.x, p11.y); ctx.lineTo(p01.x, p01.y);
        ctx.closePath(); ctx.fill(); ctx.stroke();
        // 每 100m 高程带勾一条细亮线
        if (!out && Math.floor(e / 40) !== Math.floor(g[iy][Math.min(N - 1, ix + 1)] / 40)) {
          ctx.strokeStyle = "rgba(95, 182, 255, 0.10)";
          ctx.beginPath(); ctx.moveTo(p10.x, p10.y); ctx.lineTo(p11.x, p11.y); ctx.stroke();
        }
      }
    }
    // 作战区边界（贴地虚线）
    ctx.save();
    ctx.strokeStyle = "rgba(140, 170, 200, 0.35)"; ctx.lineWidth = 1; ctx.setLineDash([6, 5]);
    ctx.beginPath();
    const edge = [[0, 0], [MAP_SIZE_M, 0], [MAP_SIZE_M, MAP_SIZE_M], [0, MAP_SIZE_M], [0, 0]];
    for (let i = 0; i < edge.length - 1; i++) {
      const a = edge[i], b = edge[i + 1];
      for (let s = 0; s <= 20; s++) {
        const wx = a[0] + (b[0] - a[0]) * s / 20, wy = a[1] + (b[1] - a[1]) * s / 20;
        const p = worldToScreen(wx, wy, 0, view, "live25d", sampleElevSmooth(g, N, Math.min(MAP_SIZE_M - 1, wx), Math.min(MAP_SIZE_M - 1, wy)));
        if (i === 0 && s === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
      }
    }
    ctx.stroke();
    ctx.restore();
    drawVectorLayers(ctx, meta, view, "live25d");
    // 远景雾化
    const fogG = ctx.createLinearGradient(0, horizonY - fr.s * 0.03, 0, horizonY + fr.s * 0.32);
    fogG.addColorStop(0, "rgba(9, 13, 18, 0.7)"); fogG.addColorStop(1, "rgba(9, 13, 18, 0)");
    ctx.fillStyle = fogG; ctx.fillRect(0, 0, W, horizonY + fr.s * 0.32);
    return off;
  }

  function drawVectorLayers(ctx, meta, view, mode) {
    const ly = meta.layers || {};
    const z = view.zoom || 1;
    const pxPerM = basePxPerM(view) * z;
    (ly.forests || []).forEach((f) => {
      polyPath(ctx, f.polygon, view, mode, meta);
      ctx.fillStyle = "rgba(26, 42, 38, 0.32)"; ctx.fill();
      ctx.strokeStyle = "rgba(126, 217, 154, 0.16)"; ctx.lineWidth = 1; ctx.stroke();
      // 树冠点阵
      const bb = bbox(f.polygon);
      ctx.fillStyle = "rgba(100, 150, 130, 0.14)";
      for (let i = 0; i < 260; i++) {
        const wx = bb[0] + hash01(i * 3.1 + bb[0]) * (bb[2] - bb[0]);
        const wy = bb[1] + hash01(i * 7.7 + bb[1]) * (bb[3] - bb[1]);
        if (!pointInPoly(wx, wy, f.polygon)) continue;
        const p = P([wx, wy], view, mode, meta);
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.3 * (p.scale || 1), 0, Math.PI * 2); ctx.fill();
      }
    });
    (ly.urban || []).forEach((u) => {
      polyPath(ctx, u.polygon, view, mode, meta);
      ctx.fillStyle = u.density === "core" ? "rgba(238, 243, 247, 0.05)" : "rgba(112, 128, 146, 0.05)";
      ctx.fill();
      ctx.setLineDash([4, 3]);
      ctx.strokeStyle = u.density === "core" ? "rgba(238, 243, 247, 0.22)" : "rgba(112, 128, 146, 0.2)";
      ctx.lineWidth = 1; ctx.stroke(); ctx.setLineDash([]);
    });
    (ly.rivers || []).forEach((rv) => {
      const w = Math.max(3, (rv.widthM || 300) * pxPerM);
      linePath(ctx, rv.path, view, mode, meta);
      ctx.lineCap = "round"; ctx.lineJoin = "round";
      ctx.strokeStyle = "rgba(6, 9, 12, 0.9)"; ctx.lineWidth = w + 3; ctx.stroke();
      ctx.strokeStyle = "rgba(38, 70, 96, 0.85)"; ctx.lineWidth = w; ctx.stroke();
      ctx.strokeStyle = "rgba(220, 228, 236, 0.22)"; ctx.lineWidth = 1; ctx.stroke();
    });
    (ly.roads || []).forEach((rd) => {
      const main = rd.class === "main";
      linePath(ctx, rd.path, view, mode, meta);
      ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(0, 0, 0, 0.45)"; ctx.lineWidth = main ? 4 : 2.6; ctx.stroke();
      ctx.strokeStyle = main ? "rgba(170, 185, 200, 0.34)" : "rgba(140, 152, 165, 0.2)";
      ctx.lineWidth = main ? 1.8 : 1.1; ctx.stroke();
    });

    // 战术方格网 2.5km
    ctx.strokeStyle = "rgba(140, 154, 170, 0.07)";
    ctx.lineWidth = 1;
    for (let m = 2500; m < MAP_SIZE_M; m += 2500) {
      const a = worldToScreen(m, 0, 0, view, mode, 0), b = worldToScreen(m, MAP_SIZE_M, 0, view, mode, 0);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      const c = worldToScreen(0, m, 0, view, mode, 0), d = worldToScreen(MAP_SIZE_M, m, 0, view, mode, 0);
      ctx.beginPath(); ctx.moveTo(c.x, c.y); ctx.lineTo(d.x, d.y); ctx.stroke();
    }

    // 北山脊标注
    const rp = worldToScreen(10000, 14500, 0, view, mode, sampleElevation(meta, 10000, 14500));
    pillLabel(ctx, "▲ 北山脊 ≈280m · 低空遮挡", rp.x, rp.y - 10, {
      fg: "#f5cf47", bg: "rgba(13, 18, 24, 0.8)", border: "rgba(245, 207, 71, 0.45)", size: 10.5,
    });
  }

  function drawCommandFrame(ctx, view) {
    const { width: W, height: H } = view;
    const sa = safeOf(view);
    // 作战区边界随缩放 / 平移实时变换（全屏画布下不再是固定外框）
    const tl = worldToScreen(0, MAP_SIZE_M, 0, view, "command", 0);
    const br = worldToScreen(MAP_SIZE_M, 0, 0, view, "command", 0);
    const x0 = tl.x, y0 = tl.y, x1 = br.x, y1 = br.y;
    // 外侧压暗一圈，作战区内外层次分明
    ctx.save();
    ctx.fillStyle = "rgba(4, 6, 9, 0.2)";
    ctx.beginPath();
    ctx.rect(0, 0, W, H);
    ctx.rect(x0, y0, x1 - x0, y1 - y0);
    ctx.fill("evenodd");
    ctx.restore();
    ctx.strokeStyle = "rgba(140, 170, 200, 0.5)";
    ctx.lineWidth = 1;
    ctx.strokeRect(Math.round(x0) + 0.5, Math.round(y0) + 0.5, Math.round(x1 - x0) - 1, Math.round(y1 - y0) - 1);
    // 四角括弧
    ctx.strokeStyle = "rgba(170, 200, 230, 0.75)";
    ctx.lineWidth = 2;
    const cl = 14;
    [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]].forEach(([x, y, dx, dy]) => {
      ctx.beginPath(); ctx.moveTo(x + dx * cl, y); ctx.lineTo(x, y); ctx.lineTo(x, y + dy * cl); ctx.stroke();
    });
    // 坐标标注带：AO 边缘在视野内时贴边，否则钉在安全区边缘
    const lblTop = Math.max(sa.t + 12, Math.min(y1 - 12, y0 - 16));
    const lblLeft = Math.max(sa.l + 12, Math.min(x1 - 12, x0 - 17));
    // 1km 刻度
    ctx.strokeStyle = "rgba(140, 170, 200, 0.4)";
    ctx.lineWidth = 1;
    for (let m = 0; m <= MAP_SIZE_M; m += 1000) {
      const p = worldToScreen(m, MAP_SIZE_M - m, 0, view, "command", 0);
      const len = m % 5000 === 0 ? 7 : 3.5;
      ctx.beginPath();
      if (p.x >= x0 - 0.5 && p.x <= x1 + 0.5) {
        ctx.moveTo(p.x, y0); ctx.lineTo(p.x, y0 - len);
        ctx.moveTo(p.x, y1); ctx.lineTo(p.x, y1 + len);
      }
      if (p.y >= y0 - 0.5 && p.y <= y1 + 0.5) {
        ctx.moveTo(x0, p.y); ctx.lineTo(x0 - len, p.y);
        ctx.moveTo(x1, p.y); ctx.lineTo(x1 + len, p.y);
      }
      ctx.stroke();
    }
    // 方格编号 A–H / 1–8
    const font = "600 10px 'JetBrains Mono', 'SF Mono', Menlo, monospace";
    const cells = MAP_SIZE_M / 2500;
    for (let i = 0; i < cells; i++) {
      const wm = (i + 0.5) * 2500;
      const p = worldToScreen(wm, MAP_SIZE_M - wm, 0, view, "command", 0);
      if (p.x >= Math.max(x0, sa.l) + 8 && p.x <= Math.min(x1, W - sa.r) - 8) {
        haloText(ctx, String.fromCharCode(65 + i), p.x, lblTop + 4, "rgba(150, 170, 192, 0.8)", font);
      }
      if (p.y >= Math.max(y0, sa.t) + 8 && p.y <= Math.min(y1, H - sa.b) - 8) {
        haloText(ctx, String(i + 1), lblLeft, p.y + 4, "rgba(150, 170, 192, 0.8)", font);
      }
    }
    ctx.textBaseline = "alphabetic";
  }

  function bbox(pts) {
    let a = Infinity, b = Infinity, c = -Infinity, d = -Infinity;
    pts.forEach((p) => { a = Math.min(a, p[0]); b = Math.min(b, p[1]); c = Math.max(c, p[0]); d = Math.max(d, p[1]); });
    return [a, b, c, d];
  }

  function polyPath(ctx, pts, view, mode, meta) {
    ctx.beginPath();
    if (!pts || pts.length < 3) return;
    pts.forEach((pt, i) => {
      const p = P(pt, view, mode, meta);
      if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
    });
    ctx.closePath();
  }

  function linePath(ctx, pts, view, mode, meta) {
    ctx.beginPath();
    if (!pts || pts.length < 2) return;
    // 细分折线以贴合 2.5D 地形起伏
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i], b = pts[i + 1];
      const segs = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 400));
      for (let s = 0; s <= segs; s++) {
        if (i > 0 && s === 0) continue;
        const t = s / segs;
        const p = P([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], view, mode, meta);
        if (i === 0 && s === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
      }
    }
  }

  function centroid(pts) {
    let x = 0, y = 0;
    pts.forEach((p) => { x += p[0]; y += p[1]; });
    return [x / pts.length, y / pts.length];
  }

  // 地图注记标签（细边小方框，类似印刷地图的注记）
  function pillLabel(ctx, text, x, y, o) {
    o = o || {};
    const size = o.size || 10.5;
    ctx.font = `${o.weight || 500} ${size}px -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif`;
    const w = ctx.measureText(text).width + 12;
    const h = size + 7;
    const lx = x - w / 2, ly = y - h / 2;
    ctx.fillStyle = o.bg || "rgba(9, 13, 18, 0.8)";
    roundRect(ctx, lx, ly, w, h, 2);
    ctx.fill();
    if (o.border) { ctx.strokeStyle = o.border; ctx.lineWidth = 1; ctx.stroke(); }
    ctx.fillStyle = o.fg || "#dce4ec";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(text, x, y + 0.5);
    ctx.textBaseline = "alphabetic";
    return { x: lx, y: ly, w, h };
  }

  function roundRect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function haloText(ctx, text, x, y, fill, font, align) {
    ctx.font = font;
    ctx.textAlign = align || "center";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "rgba(6, 8, 11, 0.85)";
    ctx.lineWidth = 3;
    ctx.strokeText(text, x, y);
    ctx.fillStyle = fill;
    ctx.fillText(text, x, y);
  }

  // ───────────────────────── 覆盖层缓存 ─────────────────────────
  function buildCoverageLayer(cov, meta, view, mode) {
    const { width: W, height: H, dpr } = view;
    const fr = mapFrame(view);
    const off = document.createElement("canvas");
    off.width = Math.round(W * dpr); off.height = Math.round(H * dpr);
    const ctx = off.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const g = cov.grid;
    const R = g.length;
    if (!R) return off;

    if (mode !== "live25d") {
      const vis = document.createElement("canvas"); vis.width = vis.height = R;
      const bl = document.createElement("canvas"); bl.width = bl.height = R;
      const vctx = vis.getContext("2d"), bctx = bl.getContext("2d");
      const vi = vctx.createImageData(R, R), bi = bctx.createImageData(R, R);
      for (let iy = 0; iy < R; iy++) {
        for (let ix = 0; ix < R; ix++) {
          const st = g[iy][ix];
          const o = ((R - 1 - iy) * R + ix) * 4; // 图像第 0 行 = 北
          if (st === 2) { vi.data[o] = 236; vi.data[o + 1] = 232; vi.data[o + 2] = 223; vi.data[o + 3] = 255; }
          if (st === 1) { bi.data[o] = 255; bi.data[o + 1] = 255; bi.data[o + 2] = 255; bi.data[o + 3] = 255; }
        }
      }
      vctx.putImageData(vi, 0, 0); bctx.putImageData(bi, 0, 0);
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
      ctx.globalAlpha = 0.05;
      ctx.drawImage(vis, fr.x + PAD, fr.y + PAD, fr.s - PAD * 2, fr.s - PAD * 2);
      ctx.globalAlpha = 1;
      // 盲区：平滑遮罩 + 红色斜线填充
      const tmp = document.createElement("canvas"); tmp.width = off.width; tmp.height = off.height;
      const tctx = tmp.getContext("2d");
      tctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      tctx.imageSmoothingEnabled = true; tctx.imageSmoothingQuality = "high";
      tctx.drawImage(bl, fr.x + PAD, fr.y + PAD, fr.s - PAD * 2, fr.s - PAD * 2);
      tctx.globalCompositeOperation = "source-in";
      tctx.setTransform(1, 0, 0, 1, 0, 0);
      tctx.fillStyle = tctx.createPattern(cache.hatchRed, "repeat");
      tctx.fillRect(0, 0, tmp.width, tmp.height);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(tmp, 0, 0);
      return off;
    }

    const step = MAP_SIZE_M / R;
    for (let iy = R - 1; iy >= 0; iy--) {
      for (let ix = 0; ix < R; ix++) {
        const st = g[iy][ix];
        if (st === 0) continue;
        const x0 = ix * step, x1 = x0 + step, y0 = iy * step, y1 = y0 + step;
        const q = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map((c) => P(c, view, "live25d", meta));
        ctx.beginPath();
        ctx.moveTo(q[0].x, q[0].y); q.slice(1).forEach((p) => ctx.lineTo(p.x, p.y)); ctx.closePath();
        ctx.fillStyle = st === 2 ? "rgba(220, 228, 236, 0.045)" : "rgba(255, 91, 79, 0.26)";
        ctx.fill();
      }
    }
    return off;
  }

  // 城市灯火点（随断电比例变暗）
  function getCityLights(meta) {
    const key = `${meta.levelId}`;
    if (cache.lightsKey === key && cache.lights) return cache.lights;
    const pts = [];
    ((meta.layers && meta.layers.urban) || []).forEach((u, ui) => {
      const bb = bbox(u.polygon);
      const n = u.density === "core" ? 520 : 220;
      for (let i = 0; i < n; i++) {
        const wx = bb[0] + hash01(i * 1.37 + ui * 91) * (bb[2] - bb[0]);
        const wy = bb[1] + hash01(i * 2.71 + ui * 57) * (bb[3] - bb[1]);
        if (!pointInPoly(wx, wy, u.polygon)) continue;
        pts.push({ x: wx, y: wy, b: 0.25 + hash01(i * 9.1 + ui) * 0.75, core: u.density === "core" });
      }
    });
    cache.lights = pts; cache.lightsKey = key;
    return pts;
  }

  function drawCachedLayer(ctx, img, view) {
    const { width: W, height: H, dpr } = view;
    const z = view.zoom || 1;
    const px = view.panX || 0;
    const py = view.panY || 0;
    ctx.save();
    ctx.setTransform(
      dpr * z, 0, 0, dpr * z,
      (W * 0.5 + px - W * 0.5 * z) * dpr,
      (H * 0.5 + py - H * 0.5 * z) * dpr
    );
    ctx.drawImage(img, 0, 0, W, H);
    ctx.restore();
  }

  // ───────────────────────── 主渲染 ─────────────────────────
  function renderFrame(canvas, state) {
    const ctx = canvas.getContext("2d");
    const meta = state.meta;
    const view = getView(canvas);
    const dpr = view.dpr;
    if (!meta) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "#080b0f"; ctx.fillRect(0, 0, canvas.width, canvas.height);
      return;
    }
    if (!cache.hatchRed) {
      cache.hatchRed = makeHatch("rgba(255, 91, 79, 0.55)", "rgba(255, 91, 79, 0.10)", Math.round(7 * dpr), 1.2 * dpr);
      cache.hatchRedSoft = makeHatch("rgba(255, 91, 79, 0.35)", "rgba(255, 91, 79, 0.05)", Math.round(9 * dpr), 1 * dpr);
    }
    const viewMode = state.viewMode || "command";
    const baseView = { width: view.width, height: view.height, dpr: view.dpr, safe: view.safe, zoom: 1, panX: 0, panY: 0 };
    const fk = mapFrame(view);
    const key = `${meta.levelId}_${meta.nightIndex}_${view.width}x${view.height}@${dpr}_${fk.x | 0},${fk.y | 0},${fk.s | 0}`;
    if (cache.terrainKey !== key) {
      cache.terrain.command = null; cache.terrain.live25d = null;
      cache.terrainKey = key; cache.covKey = "";
    }
    if (!cache.terrain[viewMode]) {
      cache.terrain[viewMode] = viewMode === "live25d" ? buildTerrain25D(meta, baseView) : buildTerrainCommand(meta, baseView);
    }
    const nowMs = performance.now();
    cache.frameRects = [];

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#080b0f";
    ctx.fillRect(0, 0, view.width, view.height);

    // 全屏画布：地形铺满视口，不再裁剪到固定外框（区外地形与射程圈自然延伸到浮层之下）
    ctx.save();

    drawCachedLayer(ctx, cache.terrain[viewMode], view);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    if (viewMode !== "live25d") {
      drawVectorLayers(ctx, meta, view, "command");
    }

    // 城市灯火
    drawCityLights(ctx, view, viewMode, meta, state);

    // 1. 雷达通视与北山脊盲区覆盖网格
    if (state.losAltM > 0 && state.coverage && state.coverage.grid) {
      const ck = `${key}_${viewMode}`;
      if (cache.covRef !== state.coverage || cache.covKey !== ck) {
        cache.covLayer = buildCoverageLayer(state.coverage, meta, baseView, viewMode);
        cache.covRef = state.coverage; cache.covKey = ck;
      }
      drawCachedLayer(ctx, cache.covLayer, view);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // 2. 战前禁区与预备阵地
    if (state.phase === "deploy" && meta.deploy) {
      (meta.deploy.forbidden || []).forEach((fb) => {
        polyPath(ctx, fb.polygon, view, viewMode, meta);
        const pat = ctx.createPattern(cache.hatchRedSoft, "repeat");
        if (pat && pat.setTransform && typeof DOMMatrix === "function") pat.setTransform(new DOMMatrix([1 / dpr, 0, 0, 1 / dpr, 0, 0]));
        ctx.fillStyle = pat || "rgba(255, 91, 79, 0.08)";
        ctx.fill();
        ctx.setLineDash([5, 4]);
        ctx.strokeStyle = "rgba(255, 91, 79, 0.6)"; ctx.lineWidth = 1.2; ctx.stroke();
        ctx.setLineDash([]);
      });
    }
    ((meta.deploy && meta.deploy.alternatePositions) || []).forEach((ap) => {
      const p = P(ap.pos, view, viewMode, meta);
      ctx.save();
      ctx.translate(p.x, p.y); ctx.rotate(Math.PI / 4);
      ctx.strokeStyle = state.phase === "deploy" ? "rgba(220, 228, 236, 0.7)" : "rgba(220, 228, 236, 0.35)";
      ctx.lineWidth = 1; ctx.setLineDash([2, 2]);
      ctx.strokeRect(-4.5, -4.5, 9, 9);
      ctx.setLineDash([]);
      ctx.restore();
      if (state.phase === "deploy") {
        haloText(ctx, ap.id.replace("alt_", "预备·"), p.x, p.y + 15, "rgba(220, 228, 236, 0.75)", "500 9px -apple-system, sans-serif");
      }
    });

    // 3. 敌军进袭方向
    drawEntryPoints(ctx, view, viewMode, meta, state, nowMs);

    // 4. 电网连线与保卫建筑
    drawGridAndStructures(ctx, view, state, viewMode, meta, nowMs);

    // 5. 第 2 夜暴露阵地猎杀红圈预警
    const kts = (meta.carryIn && meta.carryIn.knownTargets) || [];
    kts.forEach((kt) => {
      const p = P(kt.pos, view, viewMode, meta);
      const pulse = 0.5 + 0.5 * Math.sin(nowMs * 0.005);
      ctx.strokeStyle = `rgba(255, 91, 79, ${0.55 + 0.4 * pulse})`;
      ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.arc(p.x, p.y, 18 + pulse * 3, 0, Math.PI * 2); ctx.stroke();
      ctx.beginPath();
      [[0, -1], [1, 0], [0, 1], [-1, 0]].forEach(([dx, dy]) => {
        ctx.moveTo(p.x + dx * 14, p.y + dy * 14); ctx.lineTo(p.x + dx * 25, p.y + dy * 25);
      });
      ctx.stroke();
      pillLabel(ctx, "已被敌标定", p.x, p.y - 32, { fg: "#ffc9c3", bg: "rgba(32, 10, 10, 0.8)", border: "rgba(255, 91, 79, 0.6)", size: 9.5 });
    });

    // 6. 我方防空单位与射程环
    drawUnits(ctx, view, state, viewMode, meta, nowMs);

    // 7. 战场航迹、真值透视、拦截弹与爆炸特效
    if (state.snapshot) drawTracksAndCombat(ctx, view, state, viewMode, meta, nowMs);

    ctx.restore();

    if (viewMode !== "live25d") {
      drawCommandFrame(ctx, view);
    }

    // 8. HUD：暗角、指北针、比例尺
    drawHud(ctx, view, viewMode, state);
  }

  function drawCityLights(ctx, view, mode, meta, state) {
    const pts = getCityLights(meta);
    if (!pts.length) return;
    const unp = (state.snapshot && state.snapshot.grid && state.snapshot.grid.unpoweredFrac) || 0;
    const dim = 1 - Math.min(1, unp) * 0.85;
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    pts.forEach((pt, i) => {
      // 断电时按确定性顺序熄灭部分灯火
      if (hash01(i * 4.2) < unp) return;
      const p = P([pt.x, pt.y], view, mode, meta);
      const a = pt.b * (pt.core ? 0.55 : 0.35) * dim;
      // 城市灯火用偏暖的白，避免与敌对红/橙混淆
      ctx.fillStyle = `rgba(240, 228, 200, ${a})`;
      const s = (pt.core ? 1.4 : 1.1) * (p.scale || 1);
      ctx.fillRect(p.x - s / 2, p.y - s / 2, s, s);
    });
    ctx.restore();
  }

  const SHORT_UNIT_LABELS = {
    mobile_fire_team: "皮卡机枪",
    iris_t_sls: "IRIS‑T 近程导弹",
    nasams: "NASAMS 中程导弹",
    soviet_mid_range_radar: "警戒雷达",
    acoustic_post: "听音哨",
    visual_observer: "目视哨",
  };

  function isPassivePost(u) {
    return u.unitDefId === "acoustic_post" || u.unitDefId === "visual_observer";
  }

  function drawAttackCorridor(ctx, waypoints, label, view, mode, meta, nowMs, alphaMul, labelWorldPos) {
    if (!waypoints || waypoints.length < 2) return;
    const pts = waypoints.map((pt) => P(pt, view, mode, meta));
    ctx.save();
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    // 底层宽光带
    ctx.strokeStyle = `rgba(255, 91, 79, ${0.11 * alphaMul})`;
    ctx.lineWidth = 10;
    ctx.beginPath();
    pts.forEach((p, i) => { if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y); });
    ctx.stroke();
    // 动态行进虚线
    ctx.strokeStyle = `rgba(255, 91, 79, ${0.62 * alphaMul})`;
    ctx.lineWidth = 1.8;
    ctx.setLineDash([7, 6]);
    ctx.lineDashOffset = -(nowMs * 0.022);
    ctx.beginPath();
    pts.forEach((p, i) => { if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y); });
    ctx.stroke();
    ctx.setLineDash([]); ctx.lineDashOffset = 0;

    // 末端箭头指向保护设施
    const last = pts[pts.length - 1], prev = pts[pts.length - 2];
    const ang = Math.atan2(last.y - prev.y, last.x - prev.x);
    ctx.fillStyle = `rgba(255, 91, 79, ${0.82 * alphaMul})`;
    ctx.beginPath();
    ctx.moveTo(last.x, last.y);
    ctx.lineTo(last.x - Math.cos(ang - 0.42) * 11, last.y - Math.sin(ang - 0.42) * 11);
    ctx.lineTo(last.x - Math.cos(ang + 0.42) * 11, last.y - Math.sin(ang + 0.42) * 11);
    ctx.closePath();
    ctx.fill();

    if (label && alphaMul > 0.5) {
      const mid = labelWorldPos ? P(labelWorldPos, view, mode, meta) : (pts[1] || pts[0]);
      pillLabel(ctx, label, mid.x, mid.y - 12, {
        fg: "#ffc9c3", bg: "rgba(32, 10, 10, 0.85)", border: "rgba(255, 91, 79, 0.55)", size: 9.5,
      });
    }
    ctx.restore();
  }

  function drawEntryPoints(ctx, view, mode, meta, state, nowMs) {
    // 战前部署（或战中尚无敌情时）画出敌军预计攻击走廊，直接连向保卫设施
    const hasActiveTracks = state.snapshot && (state.snapshot.tracks || []).length > 0;
    const corridorAlpha = state.phase === "deploy" ? 1.0 : (hasActiveTracks ? 0.22 : 0.45);
    drawAttackCorridor(
      ctx,
      [[19100, 13200], [16600, 10700], [14000, 7550]],
      "AXIS-E  无人机群 → ★热电厂",
      view, mode, meta, nowMs, corridorAlpha,
      [15600, 13300]
    );
    drawAttackCorridor(
      ctx,
      [[1100, 18100], [4500, 15200], [7400, 12750], [10400, 10750]],
      "AXIS-NW  巡航导弹·低空 → ★水厂/变电站",
      view, mode, meta, nowMs, corridorAlpha,
      [4800, 15500]
    );

    (meta.entryPoints || []).forEach((ep, idx) => {
      const cx = Math.max(500, Math.min(MAP_SIZE_M - 500, ep.pos[0]));
      const cy = Math.max(500, Math.min(MAP_SIZE_M - 500, ep.pos[1]));
      const ang = Math.atan2(MAP_SIZE_M / 2 - ep.pos[1], MAP_SIZE_M / 2 - ep.pos[0]);
      const p = P([cx, cy], view, mode, meta);
      const q = P([cx + Math.cos(ang) * 1000, cy + Math.sin(ang) * 1000], view, mode, meta);
      const sa = Math.atan2(q.y - p.y, q.x - p.x);
      const t = state.phase === "battle" ? (nowMs * 0.0012 + idx) % 1 : 0.35;
      ctx.save();
      ctx.translate(p.x, p.y); ctx.rotate(sa);
      for (let k = 0; k < 3; k++) {
        const ph = (k / 3 + t) % 1;
        ctx.strokeStyle = `rgba(255, 91, 79, ${0.3 + 0.65 * (1 - Math.abs(ph - 0.5) * 2)})`;
        ctx.lineWidth = 2.2; ctx.lineCap = "round"; ctx.lineJoin = "round";
        const x = -6 + k * 8;
        ctx.beginPath(); ctx.moveTo(x - 4, -6); ctx.lineTo(x + 2, 0); ctx.lineTo(x - 4, 6); ctx.stroke();
      }
      ctx.restore();
      const lx = p.x - Math.cos(sa) * 4, ly = p.y - Math.sin(sa) * 4 + (Math.sin(sa) > 0.3 ? -16 : 18);
      pillLabel(ctx, `${ep.name}来袭口`, lx, ly, { fg: "#ffc9c3", bg: "rgba(32, 10, 10, 0.85)", border: "rgba(255, 91, 79, 0.6)", size: 9.5 });
    });
  }

  function drawStructureIcon(ctx, x, y, sid, color) {
    ctx.save();
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 1.6; ctx.lineCap = "round"; ctx.lineJoin = "round";
    if (sid === "tpp" || sid === "power_plant") {
      // 闪电符号（代表核心供电热电厂）
      ctx.beginPath();
      ctx.moveTo(x + 1.5, y - 7);
      ctx.lineTo(x - 4.5, y + 0.5);
      ctx.lineTo(x + 0.5, y + 0.5);
      ctx.lineTo(x - 1.5, y + 7);
      ctx.lineTo(x + 4.5, y - 0.5);
      ctx.lineTo(x - 0.5, y - 0.5);
      ctx.closePath();
      ctx.fill();
    } else if (sid === "substation_central" || sid === "substation") {
      // 变电枢纽符号（菱形核心 + 节点）
      ctx.beginPath();
      ctx.moveTo(x, y - 5.5); ctx.lineTo(x + 5.5, y); ctx.lineTo(x, y + 5.5); ctx.lineTo(x - 5.5, y); ctx.closePath();
      ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();
    } else {
      // 水厂符号（水滴）
      ctx.beginPath();
      ctx.moveTo(x, y - 6.5);
      ctx.bezierCurveTo(x + 5.5, y - 1, x + 5.5, y + 6, x, y + 6);
      ctx.bezierCurveTo(x - 5.5, y + 6, x - 5.5, y - 1, x, y - 6.5);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  function drawGridAndStructures(ctx, view, state, mode, meta, nowMs) {
    const snap = state.snapshot;
    const nodeMap = {};
    ((meta.grid && meta.grid.nodes) || []).forEach((n) => { nodeMap[n.id] = { pos: n.pos, powered: true }; });
    if (snap && snap.grid && snap.grid.nodes) {
      snap.grid.nodes.forEach((gn) => { if (nodeMap[gn.id]) nodeMap[gn.id].powered = gn.powered; });
    }
    ((meta.grid && meta.grid.links) || []).forEach((lk) => {
      const a = nodeMap[lk[0]], b = nodeMap[lk[1]];
      if (!a || !b) return;
      const pa = P(a.pos, view, mode, meta), pb = P(b.pos, view, mode, meta);
      const ok = a.powered && b.powered;
      ctx.strokeStyle = ok ? "rgba(220, 228, 236, 0.16)" : "rgba(255, 91, 79, 0.22)";
      ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
      ctx.strokeStyle = ok ? "rgba(220, 228, 236, 0.65)" : "rgba(255, 91, 79, 0.65)";
      ctx.lineWidth = 1.2;
      ctx.setLineDash([4, 6]);
      ctx.lineDashOffset = ok ? -nowMs * 0.012 : 0;
      ctx.stroke();
      ctx.setLineDash([]); ctx.lineDashOffset = 0;
    });

    const structs = (snap && snap.structures) || meta.structures || [];
    const pxPerM = basePxPerM(view);
    structs.forEach((s) => {
      const p = P(s.pos, view, mode, meta);
      const hpFrac = Math.max(0, s.hp / Math.max(1, s.maxHp));
      const sc = p.scale || 1;
      const isFocused = state.focusStructId === s.id;
      const isPrimary = s.id === "tpp" || (s.weight && s.weight >= 4);

      // 1. 醒目的重点保卫区光环 + 白色防区虚线环
      const ringR = Math.max(isPrimary ? 34 : 26, (s.radiusM || 200) * pxPerM * 2.2) * Math.max(0.85, sc);
      ctx.save();
      const rg = ctx.createRadialGradient(p.x, p.y, 4, p.x, p.y, ringR);
      if (s.destroyed) {
        rg.addColorStop(0, "rgba(255, 91, 79, 0.25)");
        rg.addColorStop(1, "rgba(255, 91, 79, 0.0)");
      } else {
        rg.addColorStop(0, isPrimary ? "rgba(238, 243, 247, 0.24)" : "rgba(238, 243, 247, 0.16)");
        rg.addColorStop(0.65, "rgba(238, 243, 247, 0.05)");
        rg.addColorStop(1, "rgba(238, 243, 247, 0.0)");
      }
      ctx.fillStyle = rg;
      ctx.beginPath();
      if (mode === "live25d") ctx.ellipse(p.x, p.y, ringR, ringR * 0.68, 0, 0, Math.PI * 2);
      else ctx.arc(p.x, p.y, ringR, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = s.destroyed ? "rgba(255, 91, 79, 0.65)" : (isFocused ? "#fff" : "rgba(238, 243, 247, 0.68)");
      ctx.lineWidth = isPrimary || isFocused ? 1.6 : 1.2;
      ctx.setLineDash([5, 4]);
      ctx.beginPath();
      if (mode === "live25d") ctx.ellipse(p.x, p.y, ringR, ringR * 0.68, 0, 0, Math.PI * 2);
      else ctx.arc(p.x, p.y, ringR, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      if (isFocused) {
        const pulse = 0.5 + 0.5 * Math.sin(nowMs * 0.008);
        ctx.strokeStyle = `rgba(238, 243, 247, ${0.4 + 0.5 * pulse})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, ringR + 6 + pulse * 6, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();

      // 2. 保卫目标地标主体（双层纯白护盾方章，尺寸远大于普通单位）
      const sz = (isPrimary ? 26 : 23) * Math.max(0.88, sc);
      ctx.save();
      ctx.fillStyle = s.destroyed ? "#3a1210" : (s.powered === false ? "#2a3644" : "#eef3f7");
      roundRect(ctx, p.x - sz / 2, p.y - sz / 2, sz, sz, 4);
      ctx.fill();
      ctx.strokeStyle = s.destroyed ? "#ff5b4f" : "#ffffff";
      ctx.lineWidth = isPrimary ? 1.8 : 1.3;
      roundRect(ctx, p.x - sz / 2, p.y - sz / 2, sz, sz, 4);
      ctx.stroke();

      // 内层深色核 + 专属建筑符号
      const inSz = sz - 6;
      ctx.fillStyle = s.destroyed ? "#240a08" : "#0b0f14";
      roundRect(ctx, p.x - inSz / 2, p.y - inSz / 2, inSz, inSz, 2.5);
      ctx.fill();
      drawStructureIcon(ctx, p.x, p.y, s.id, s.destroyed ? "#ff5b4f" : "#eef3f7");
      ctx.restore();

      // 3. 顶部高优先级保卫目标铭牌（绝不被普通单位遮挡）
      const tagPrefix = "★ ";
      const sr = pillLabel(ctx, `${tagPrefix}${s.name}  ${s.hp}/${s.maxHp}`, p.x, p.y - sz / 2 - 13, {
        fg: s.destroyed ? "#ff9d94" : "#eef3f7",
        bg: s.destroyed ? "rgba(40, 12, 10, 0.92)" : "rgba(11, 16, 22, 0.92)",
        border: s.destroyed ? "rgba(255, 91, 79, 0.85)" : "rgba(238, 243, 247, 0.85)",
        size: isPrimary ? 11 : 10.5,
        weight: 600,
      });
      cache.frameRects.push(sr, { x: p.x - sz / 2 - 4, y: p.y - sz / 2 - 4, w: sz + 8, h: sz + 18 });

      // 4. 底部醒目血条
      const bw = isPrimary ? 44 : 36;
      ctx.fillStyle = "rgba(6, 8, 11, 0.92)";
      roundRect(ctx, p.x - bw / 2 - 1, p.y + sz / 2 + 4, bw + 2, 6, 3); ctx.fill();
      ctx.strokeStyle = "rgba(238, 243, 247, 0.4)"; ctx.lineWidth = 0.8;
      roundRect(ctx, p.x - bw / 2 - 1, p.y + sz / 2 + 4, bw + 2, 6, 3); ctx.stroke();
      ctx.fillStyle = hpFrac > 0.5 ? "#7ed99a" : (hpFrac > 0.2 ? "#f5cf47" : "#ff5b4f");
      roundRect(ctx, p.x - bw / 2, p.y + sz / 2 + 5, Math.max(1, bw * hpFrac), 4, 2); ctx.fill();
    });
  }

  // 投影圆（2.5D 下自动变为透视椭圆）
  function ringPath(ctx, wx, wy, r, view, mode, meta) {
    ctx.beginPath();
    const n = 72;
    for (let i = 0; i <= n; i++) {
      const a = (i / n) * Math.PI * 2;
      const x = wx + Math.cos(a) * r, y = wy + Math.sin(a) * r;
      const p = worldToScreen(x, y, 0, view, mode, mode === "live25d" ? sampleElevation(meta, Math.max(0, Math.min(MAP_SIZE_M, x)), Math.max(0, Math.min(MAP_SIZE_M, y))) : 0);
      if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
    }
    ctx.closePath();
  }

  function unitList(state) {
    return state.phase === "deploy" ? state.placements : ((state.snapshot && state.snapshot.units) || []);
  }

  function unitScreenPos(u, canvas, state) {
    const view = getView(canvas);
    return P(u.pos, view, state.viewMode || "command", state.meta);
  }

  function drawUnitGlyph(ctx, x, y, u, color) {
    const defId = u.unitDefId || "";
    const cat = u.category || "fire";
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 1.5; ctx.lineCap = "round"; ctx.lineJoin = "round";
    if (defId === "mobile_fire_team") {
      // 皮卡高射机枪：车底座 + 双联高射枪管斜指天空
      ctx.beginPath();
      ctx.moveTo(x - 6.5, y + 4.5); ctx.lineTo(x + 5.5, y + 4.5);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(x - 3.5, y + 5.5, 1.3, 0, Math.PI * 2);
      ctx.arc(x + 3.0, y + 5.5, 1.3, 0, Math.PI * 2);
      ctx.fill();
      // 双枪管向右上斜指
      ctx.beginPath();
      ctx.moveTo(x - 2, y + 3.5); ctx.lineTo(x + 6, y - 4.5);
      ctx.moveTo(x - 3.5, y + 2); ctx.lineTo(x + 4.5, y - 6);
      ctx.stroke();
    } else if (defId === "nasams" || defId === "iris_t_sls" || cat === "fire") {
      // 防空导弹发射架：底座 + 两枚倾斜待发导弹
      ctx.beginPath();
      ctx.moveTo(x - 7, y + 5); ctx.lineTo(x + 7, y + 5);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x - 4.5, y + 3.5); ctx.lineTo(x + 2.5, y - 4.5);
      ctx.moveTo(x - 0.5, y + 3.5); ctx.lineTo(x + 6.5, y - 4.5);
      ctx.stroke();
      // 导弹尖端
      ctx.beginPath();
      ctx.arc(x + 2.5, y - 4.5, 1.1, 0, Math.PI * 2);
      ctx.arc(x + 6.5, y - 4.5, 1.1, 0, Math.PI * 2);
      ctx.fill();
    } else if (cat === "sensor") {
      ctx.beginPath(); ctx.arc(x + 2.5, y + 3, 6, Math.PI * 1.0, Math.PI * 1.5); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x + 2.5, y + 3); ctx.lineTo(x - 1.5, y - 1); ctx.stroke();
      ctx.beginPath(); ctx.arc(x + 2.5, y + 3, 1.2, 0, Math.PI * 2); ctx.fill();
    } else if (cat === "ew") {
      ctx.beginPath(); ctx.moveTo(x - 3.5, y - 4); ctx.lineTo(x + 1, y - 0.5); ctx.lineTo(x - 1, y + 0.5); ctx.lineTo(x + 3.5, y + 4); ctx.stroke();
    } else {
      ctx.font = "700 9px -apple-system, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("?", x, y + 0.5); ctx.textBaseline = "alphabetic";
    }
  }

  function drawUnits(ctx, view, state, mode, meta, nowMs) {
    const list = unitList(state);
    const labelRects = cache.frameRects || [];
    list.forEach((u) => {
      if (isPassivePost(u)) return;
      const q = P(u.pos, view, mode, meta);
      labelRects.push({ x: q.x - 13, y: q.y - 9, w: 26, h: 18 });
    });
    const hit = (r) => labelRects.some((o) => r.x < o.x + o.w && r.x + r.w > o.x && r.y < o.y + o.h && r.y + r.h > o.y);

    // 1. 战前部署阶段：常驻画出全部 6 部防空武器的轻量化射程圈（皮卡机枪 2.5km 圈 + 导弹虚线圈），一眼看懂火力网
    if (state.phase === "deploy") {
      list.forEach((u) => {
        if ((u.category || "fire") !== "fire") return;
        const idKey = u.id || u.rosterId;
        if (idKey === state.selectedUnitKey) return;
        const w0 = (u.weapons || [])[0];
        if (!w0 || !(w0.rangeM > 0)) return;
        const isGun = u.unitDefId === "mobile_fire_team";
        ringPath(ctx, u.pos[0], u.pos[1], w0.rangeM, view, mode, meta);
        ctx.fillStyle = isGun ? "rgba(95, 182, 255, 0.04)" : "rgba(95, 182, 255, 0.015)";
        ctx.fill();
        ctx.strokeStyle = isGun ? "rgba(95, 182, 255, 0.36)" : "rgba(95, 182, 255, 0.18)";
        ctx.lineWidth = isGun ? 1.1 : 0.9;
        ctx.setLineDash(isGun ? [3, 4] : [5, 5]);
        ctx.stroke();
        ctx.setLineDash([]);
      });
    }

    // 2. 选中（或悬停）单位的高亮射程环与探测环
    const focusU = list.find((u) => (u.id || u.rosterId) === state.selectedUnitKey)
      || list.find((u) => (u.id || u.rosterId) === state.hoverUnitKey);
    if (focusU) {
      const detR = focusU.detectionRangeM || 0;
      if (detR > 0 && (focusU.category === "sensor" || !(focusU.weapons || []).length)) {
        ringPath(ctx, focusU.pos[0], focusU.pos[1], detR, view, mode, meta);
        ctx.fillStyle = "rgba(126, 217, 154, 0.04)"; ctx.fill();
        ctx.strokeStyle = "rgba(126, 217, 154, 0.6)"; ctx.lineWidth = 1.2;
        ctx.setLineDash([6, 5]); ctx.stroke(); ctx.setLineDash([]);
        const tp = worldToScreen(focusU.pos[0], focusU.pos[1] + detR, 0, view, mode, 0);
        // 全屏画布：射程 / 探测环可能超出视野，标注钉在 HUD 安全区内
        haloText(ctx, `探测范围 ${(detR / 1000).toFixed(1)}km`, tp.x, Math.max(safeOf(view).t + 14, tp.y - 4), "rgba(127, 224, 224, 0.92)", "600 9.5px 'JetBrains Mono', 'SF Mono', Menlo, monospace");
      }
      (focusU.weapons || []).forEach((w, wi) => {
        if (!(w.rangeM > 0)) return;
        const isGun = focusU.unitDefId === "mobile_fire_team";
        ringPath(ctx, focusU.pos[0], focusU.pos[1], w.rangeM, view, mode, meta);
        ctx.fillStyle = isGun ? "rgba(95, 182, 255, 0.08)" : "rgba(95, 182, 255, 0.06)";
        ctx.fill();
        ctx.strokeStyle = isGun ? "rgba(127, 224, 224, 0.9)" : "rgba(95, 182, 255, 0.88)";
        ctx.lineWidth = 1.5; ctx.stroke();
        const tp = worldToScreen(focusU.pos[0], focusU.pos[1] - w.rangeM, 0, view, mode, 0);
        const maxY = view.height - safeOf(view).lb - 8 - ((focusU.weapons || []).length - 1 - wi) * 12;
        haloText(ctx, `${w.name || w.weaponId} · 射程 ${(w.rangeM / 1000).toFixed(1)}km`, tp.x, Math.min(maxY, tp.y + 13 + wi * 12), isGun ? "#7fe0e0" : "#c4e0ff", "600 10px 'JetBrains Mono', 'SF Mono', Menlo, monospace");
      });
    }

    // 排序：被动哨所最底层 → 普通单位 → 选中/悬停最顶层
    const order = list.slice().sort((a, b) => {
      const ka = (a.id || a.rosterId), kb = (b.id || b.rosterId);
      const pa = isPassivePost(a) ? -2 : 0, pb = isPassivePost(b) ? -2 : 0;
      const wa = pa + (ka === state.selectedUnitKey ? 4 : 0) + (ka === state.hoverUnitKey ? 2 : 0);
      const wb = pb + (kb === state.selectedUnitKey ? 4 : 0) + (kb === state.hoverUnitKey ? 2 : 0);
      return wa - wb;
    });

    const labelQueue = [];

    order.forEach((u) => {
      const idKey = u.id || u.rosterId;
      const isSel = state.selectedUnitKey === idKey;
      const isHover = state.hoverUnitKey === idKey;
      const p = P(u.pos, view, mode, meta);
      const cat = u.category || "fire";
      const inactive = u.deployState && !["ACTIVE", "Deployed"].includes(u.deployState);

      // 机动转移路线
      if (u.relocation && u.relocation.dest) {
        const dp = P(u.relocation.dest, view, mode, meta);
        ctx.strokeStyle = "rgba(220, 228, 236, 0.85)"; ctx.lineWidth = 1.4;
        ctx.setLineDash([4, 4]); ctx.lineDashOffset = -nowMs * 0.02;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(dp.x, dp.y); ctx.stroke();
        ctx.setLineDash([]); ctx.lineDashOffset = 0;
        const a = Math.atan2(dp.y - p.y, dp.x - p.x);
        ctx.fillStyle = "#dce4ec";
        ctx.beginPath(); ctx.moveTo(dp.x, dp.y);
        ctx.lineTo(dp.x - Math.cos(a - 0.4) * 8, dp.y - Math.sin(a - 0.4) * 8);
        ctx.lineTo(dp.x - Math.cos(a + 0.4) * 8, dp.y - Math.sin(a + 0.4) * 8);
        ctx.closePath(); ctx.fill();
      }

      // ── 分支 A：被动暗哨（声学听音哨 / 目视哨）画成低调的小圆点图钉，不抢防空武器视觉 ──
      if (isPassivePost(u)) {
        const r = isSel || isHover ? 6.5 : 4.5;
        ctx.save();
        if (inactive) ctx.globalAlpha = 0.45;
        ctx.fillStyle = "rgba(9, 13, 18, 0.92)";
        ctx.strokeStyle = isSel || isHover ? "#7fe0e0" : "rgba(127, 224, 224, 0.62)";
        ctx.lineWidth = isSel || isHover ? 1.8 : 1.2;
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.fillStyle = isSel || isHover ? "#ffffff" : "rgba(127, 224, 224, 0.85)";
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.6, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
        if (isSel || isHover) {
          labelQueue.push({ u, p, isSel, isHover, inactive, shortName: SHORT_UNIT_LABELS[u.unitDefId] || u.name });
        }
        return;
      }

      // ── 分支 B：主力防空武器（皮卡机枪、IRIS-T、NASAMS）与主力警戒雷达 ──
      const isGun = u.unitDefId === "mobile_fire_team";
      const isMissile = cat === "fire" && !isGun;
      const color = CAT_COLORS[cat] || CAT_COLORS.fire;

      // 皮卡高射机枪：在平面图与 2.5D 下都画出探照灯光锥，直观体现“探照灯+高射机枪”
      if (isGun && !inactive) {
        const ang = -Math.PI * 0.15 + Math.sin(nowMs * 0.0014 + idKey * 1.3) * 0.42;
        const coneLen = mode === "live25d" ? 64 : 42;
        ctx.save();
        ctx.translate(p.x, p.y); ctx.rotate(ang);
        const grad = ctx.createLinearGradient(0, 0, coneLen, 0);
        grad.addColorStop(0, "rgba(127, 224, 224, 0.28)");
        grad.addColorStop(1, "rgba(127, 224, 224, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(coneLen, -9); ctx.lineTo(coneLen, 9); ctx.closePath(); ctx.fill();
        ctx.restore();
      }

      // 雷达开机：旋转扫描扇
      const emOn = u.emitter ? u.emitter.on : (u.emissionPolicy !== "silent" && (cat === "sensor" || u.unitDefId === "nasams" || u.unitDefId === "soviet_mid_range_radar"));
      if (emOn) {
        const a = (nowMs * 0.0025 + idKey * 1.7) % (Math.PI * 2);
        const R = 25;
        if (ctx.createConicGradient) {
          const cg = ctx.createConicGradient(a, p.x, p.y);
          cg.addColorStop(0, "rgba(126, 217, 154, 0)");
          cg.addColorStop(0.82, "rgba(126, 217, 154, 0)");
          cg.addColorStop(1, "rgba(126, 217, 154, 0.42)");
          ctx.fillStyle = cg;
          ctx.beginPath(); ctx.arc(p.x, p.y, R, 0, Math.PI * 2); ctx.fill();
        }
        ctx.strokeStyle = "rgba(127, 224, 224, 0.75)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + Math.cos(a) * R, p.y + Math.sin(a) * R); ctx.stroke();
        ctx.strokeStyle = "rgba(126, 217, 154, 0.2)";
        ctx.beginPath(); ctx.arc(p.x, p.y, R, 0, Math.PI * 2); ctx.stroke();
      }

      // 暴露度外环
      const exp = u.exposure !== undefined ? u.exposure : (u.carryExposure || 0);
      if (exp > 5) {
        ctx.strokeStyle = "rgba(112, 128, 146, 0.2)"; ctx.lineWidth = 2.4;
        ctx.beginPath(); ctx.arc(p.x, p.y, 16, 0, Math.PI * 2); ctx.stroke();
        ctx.strokeStyle = exp >= 70 ? "#ff5b4f" : "#f5cf47";
        ctx.beginPath();
        ctx.arc(p.x, p.y, 16, -Math.PI * 0.5, -Math.PI * 0.5 + Math.min(1, exp / 100) * Math.PI * 2);
        ctx.stroke();
      }

      // 悬停/选中高亮框
      const fw = isMissile ? 26 : 22, fh = isMissile ? 17 : 15;
      if (isSel || isHover) {
        ctx.strokeStyle = isSel ? "rgba(255, 255, 255, 0.95)" : "rgba(255, 255, 255, 0.5)";
        ctx.lineWidth = 1.2;
        const sx0 = fw / 2 + 4, sy0 = fh / 2 + 4, c = 5;
        ctx.beginPath();
        [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([sx, sy]) => {
          ctx.moveTo(p.x + sx * sx0, p.y + sy * (sy0 - c));
          ctx.lineTo(p.x + sx * sx0, p.y + sy * sy0);
          ctx.lineTo(p.x + sx * (sx0 - c), p.y + sy * sy0);
        });
        ctx.stroke();
      }

      // 武器/雷达主体框
      ctx.save();
      if (inactive) ctx.globalAlpha = 0.5;
      if (isSel) { ctx.shadowColor = color; ctx.shadowBlur = 5; }
      ctx.fillStyle = "rgba(9, 13, 18, 0.94)";
      roundRect(ctx, p.x - fw / 2, p.y - fh / 2, fw, fh, 3); ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = color; ctx.lineWidth = isSel ? 2.1 : 1.5;
      roundRect(ctx, p.x - fw / 2, p.y - fh / 2, fw, fh, 3); ctx.stroke();
      drawUnitGlyph(ctx, p.x, p.y, u, color);

      // 导弹车右上角显示当前装填弹药数角标
      if (isMissile && u.weapons && u.weapons[0]) {
        const w0 = u.weapons[0];
        const rds = w0.rounds !== undefined ? w0.rounds : w0.magazine;
        if (typeof rds === "number" && rds >= 0 && rds < 9000) {
          const bx = p.x + fw / 2 + 2, by = p.y - fh / 2 - 2;
          ctx.fillStyle = rds === 0 ? "#ff5b4f" : "#111820";
          ctx.strokeStyle = rds === 0 ? "#ff9d94" : color;
          ctx.lineWidth = 1;
          roundRect(ctx, bx - 7, by - 5, 14, 10, 2); ctx.fill(); ctx.stroke();
          ctx.fillStyle = "#dce4ec";
          ctx.font = "600 8.5px 'JetBrains Mono', monospace";
          ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.fillText(String(rds), bx, by + 0.5);
          ctx.textBaseline = "alphabetic";
        }
      }

      // 规避静默标记
      if (u.emitter && u.emitter.armSilenced) {
        ctx.fillStyle = "#f5cf47";
        ctx.beginPath(); ctx.arc(p.x - fw / 2, p.y - fh / 2, 3.2, 0, Math.PI * 2); ctx.fill();
      }
      ctx.restore();

      labelQueue.push({
        u, p, isSel, isHover, inactive,
        shortName: SHORT_UNIT_LABELS[u.unitDefId] || u.name,
      });
    });

    // 标签：选中 > 悬停 > 防空武器/主力雷达
    labelQueue.sort((a, b) => (b.isSel * 2 + b.isHover) - (a.isSel * 2 + a.isHover));
    labelQueue.forEach(({ u, p, isSel, isHover, inactive, shortName }) => {
      const text = `#${u.rosterId} ${shortName}`;
      const font = isSel ? "700 11px -apple-system, 'PingFang SC', sans-serif" : "600 10px -apple-system, 'PingFang SC', sans-serif";
      ctx.font = font;
      const w = ctx.measureText(text).width + 4;
      const cands = [[p.x, p.y + 21], [p.x, p.y - 14], [p.x + w / 2 + 15, p.y + 4], [p.x - w / 2 - 15, p.y + 4]];
      for (const [lx, ly] of cands) {
        const r = { x: lx - w / 2, y: ly - 10, w, h: 13 };
        if (!isSel && !isHover && hit(r)) continue;
        labelRects.push(r);
        const fill = isSel ? "#ffffff" : (inactive ? "rgba(112, 128, 146, 0.7)" : "rgba(196, 224, 255, 0.94)");
        haloText(ctx, text, lx, ly, fill, font);
        break;
      }
    });
  }

  function updateTrails(snap) {
    if (!snap || snap.tick === cache.lastTick) return;
    if (snap.tick < cache.lastTick) cache.trails.clear();
    cache.lastTick = snap.tick;
    const alive = new Set();
    (snap.tracks || []).forEach((t) => {
      alive.add(t.id);
      const arr = cache.trails.get(t.id) || [];
      const last = arr[arr.length - 1];
      if (!last || Math.hypot(last[0] - t.pos[0], last[1] - t.pos[1]) > 60) arr.push([t.pos[0], t.pos[1]]);
      while (arr.length > 16) arr.shift();
      cache.trails.set(t.id, arr);
    });
    Array.from(cache.trails.keys()).forEach((k) => { if (!alive.has(k)) cache.trails.delete(k); });
  }

  function drawTracksAndCombat(ctx, view, state, mode, meta, nowMs) {
    const snap = state.snapshot;
    updateTrails(snap);

    // 真值透视层
    if (state.godView && snap.threats) {
      snap.threats.forEach((th) => {
        const elev = sampleElevation(meta, th.pos[0], th.pos[1]);
        const p = worldToScreen(th.pos[0], th.pos[1], th.altM, view, mode, elev);
        if (mode === "live25d" && p.groundY) {
          ctx.strokeStyle = "rgba(255, 91, 79, 0.3)"; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(p.x, p.groundY); ctx.lineTo(p.x, p.y); ctx.stroke();
        }
        ctx.strokeStyle = "rgba(255, 140, 130, 0.75)"; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(p.x, p.y - 5); ctx.lineTo(p.x + 5, p.y); ctx.lineTo(p.x, p.y + 5); ctx.lineTo(p.x - 5, p.y); ctx.closePath(); ctx.stroke();
      });
    }

    // 航迹尾迹
    const tracks = snap.tracks || [];
    tracks.forEach((trk) => {
      const tr = cache.trails.get(trk.id);
      if (!tr || tr.length < 2) return;
      const col = Q_COLORS[trk.quality] || "#ff5b4f";
      for (let i = 1; i < tr.length; i++) {
        const a = worldToScreen(tr[i - 1][0], tr[i - 1][1], 140, view, mode, sampleElevation(meta, tr[i - 1][0], tr[i - 1][1]));
        const b = worldToScreen(tr[i][0], tr[i][1], 140, view, mode, sampleElevation(meta, tr[i][0], tr[i][1]));
        ctx.strokeStyle = col; ctx.globalAlpha = (i / tr.length) * 0.55; ctx.lineWidth = 1.4;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      ctx.globalAlpha = 1;
    });

    // T0-T3 航迹符号
    tracks.forEach((trk) => {
      const elev = sampleElevation(meta, trk.pos[0], trk.pos[1]);
      const p = worldToScreen(trk.pos[0], trk.pos[1], 140, view, mode, elev);
      const col = Q_COLORS[trk.quality] || "#ff5b4f";
      if (mode === "live25d" && p.groundY) {
        ctx.strokeStyle = "rgba(112, 128, 146, 0.25)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(p.x, p.groundY); ctx.lineTo(p.x, p.y); ctx.stroke();
        ctx.fillStyle = "rgba(0, 0, 0, 0.45)";
        ctx.beginPath(); ctx.ellipse(p.x, p.groundY, 4, 1.6, 0, 0, Math.PI * 2); ctx.fill();
      }
      if (trk.quality === 0) {
        ctx.strokeStyle = "rgba(112, 128, 146, 0.5)"; ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.arc(p.x, p.y, Math.max(10, (trk.uncertaintyRadiusM || 600) * basePxPerM(view)), 0, Math.PI * 2); ctx.stroke();
        ctx.setLineDash([]);
      }
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(-trk.headingRad);
      ctx.shadowColor = col; ctx.shadowBlur = 4;
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.moveTo(8, 0); ctx.lineTo(-5, -5); ctx.lineTo(-2.5, 0); ctx.lineTo(-5, 5); ctx.closePath();
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = "rgba(6, 8, 11, 0.9)"; ctx.lineWidth = 0.8; ctx.stroke();
      ctx.restore();

      const TAGS = { UAV: "无人机", CM: "巡航弹", BM: "弹道弹", AC_LOW: "飞机", ARM: "反辐射", DECOY: "诱饵", UNKNOWN: "?" };
      const tagStr = trk.identifiedAsDecoy ? "诱饵" : (trk.quality >= 3 || trk.classified ? (TAGS[trk.tag] || trk.tag) : "?");
      haloText(ctx, tagStr, p.x + 10, p.y + 3.5, col, "600 9.5px 'JetBrains Mono', 'SF Mono', Menlo, monospace", "left");
    });

    // 飞行中的拦截弹与高炮曳光弹链
    (snap.interceptors || []).forEach((ic) => {
      const p0 = worldToScreen(ic.launchPos[0], ic.launchPos[1], 0, view, mode, sampleElevation(meta, ic.launchPos[0], ic.launchPos[1]));
      const pc = worldToScreen(ic.curPos[0], ic.curPos[1], 120, view, mode, sampleElevation(meta, ic.curPos[0], ic.curPos[1]));
      const isGun = ic.weaponId === "gepard_35mm" || ic.weaponId === "mdf_hmg" || ic.weaponId === "zu23_2";
      const grad = ctx.createLinearGradient(p0.x, p0.y, pc.x, pc.y);
      const c = isGun ? "242, 183, 102" : "205, 230, 255";
      grad.addColorStop(0, `rgba(${c}, 0)`); grad.addColorStop(1, `rgba(${c}, 0.95)`);
      ctx.strokeStyle = grad; ctx.lineWidth = isGun ? 1.3 : 1.8;
      if (isGun) { ctx.setLineDash([3, 4]); ctx.lineDashOffset = -nowMs * 0.08; }
      ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(pc.x, pc.y); ctx.stroke();
      ctx.setLineDash([]); ctx.lineDashOffset = 0;
      ctx.save();
      ctx.shadowColor = `rgb(${c})`; ctx.shadowBlur = 5;
      ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(pc.x, pc.y, 2.3, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    });

    // 瞬态特效：hit=空中拦截成功；impact_hit=突防落地命中；其余为脱靶/点射
    const DUR = 1500;
    state.fxList = (state.fxList || []).filter((fx) => nowMs - fx.t0 < DUR);
    state.fxList.forEach((fx) => {
      const age = (nowMs - fx.t0) / DUR;
      const kind = fx.kind;
      const isKill = kind === "hit";
      const isImpact = kind === "impact_hit";
      const minor = !isKill && !isImpact;
      const p = worldToScreen(fx.pos[0], fx.pos[1], isImpact ? 0 : 100, view, mode, sampleElevation(meta, fx.pos[0], fx.pos[1]));
      const R = isImpact ? 30 : (isKill ? 20 : 8);
      if (age < 0.35 && !minor) {
        const fa = 1 - age / 0.35;
        const rg = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, R);
        rg.addColorStop(0, isImpact ? `rgba(242, 214, 170, ${fa})` : `rgba(220, 228, 236, ${fa})`);
        rg.addColorStop(0.4, isImpact ? `rgba(255, 130, 70, ${fa * 0.75})` : `rgba(126, 217, 154, ${fa * 0.55})`);
        rg.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = rg;
        ctx.beginPath(); ctx.arc(p.x, p.y, R, 0, Math.PI * 2); ctx.fill();
      }
      ctx.strokeStyle = isImpact ? `rgba(255, 91, 79, ${1 - age})` : (isKill ? `rgba(126, 217, 154, ${1 - age})` : `rgba(140, 154, 170, ${(1 - age) * 0.5})`);
      ctx.lineWidth = isImpact ? 2.2 : (isKill ? 1.6 : 1);
      ctx.beginPath(); ctx.arc(p.x, p.y, 3 + age * (isImpact ? 38 : (isKill ? 24 : 8)), 0, Math.PI * 2); ctx.stroke();
      if (isImpact) {
        ctx.strokeStyle = `rgba(255, 150, 80, ${(1 - age) * 0.6})`;
        ctx.beginPath(); ctx.arc(p.x, p.y, 2 + age * 20, 0, Math.PI * 2); ctx.stroke();
      }
    });

    // 关注脉冲（新手提示用）
    state.pulses = (state.pulses || []).filter((pl) => nowMs - pl.t0 < 3000);
    state.pulses.forEach((pl) => {
      const age = ((nowMs - pl.t0) % 1000) / 1000;
      const p = worldToScreen(pl.pos[0], pl.pos[1], 0, view, mode, sampleElevation(meta, pl.pos[0], pl.pos[1]));
      ctx.strokeStyle = `rgba(255, 91, 79, ${1 - age})`;
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(p.x, p.y, 10 + age * 30, 0, Math.PI * 2); ctx.stroke();
    });
  }

  function drawHud(ctx, view, mode, state) {
    const { width: W, height: H } = view;
    const sa = safeOf(view);
    const fr = mapFrame(view);
    // 暗角（以作战区中心为焦点，四周浮层下方逐渐压暗，提升 HUD 可读性）
    const fcx = fr.x + fr.s / 2, fcy = fr.y + fr.s / 2;
    const vg = ctx.createRadialGradient(fcx, fcy, fr.s * 0.42, fcx, fcy, Math.max(W, H) * 0.85);
    vg.addColorStop(0, "rgba(0, 0, 0, 0)"); vg.addColorStop(1, "rgba(0, 0, 0, 0.55)");
    ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
    // 顶 / 底边缘渐暗，给浮动 HUD 一个“托底”
    const tg = ctx.createLinearGradient(0, 0, 0, 90);
    tg.addColorStop(0, "rgba(4, 6, 9, 0.55)"); tg.addColorStop(1, "rgba(4, 6, 9, 0)");
    ctx.fillStyle = tg; ctx.fillRect(0, 0, W, 90);
    const bg = ctx.createLinearGradient(0, H - 110, 0, H);
    bg.addColorStop(0, "rgba(4, 6, 9, 0)"); bg.addColorStop(1, "rgba(4, 6, 9, 0.6)");
    ctx.fillStyle = bg; ctx.fillRect(0, H - 110, W, 110);

    // AO 内角（随缩放平移），钉在安全区内
    const tl = worldToScreen(0, MAP_SIZE_M, 0, view, "command", 0);
    const brp = worldToScreen(MAP_SIZE_M, 0, 0, view, "command", 0);
    const isFlat = mode !== "live25d";
    const aoR = isFlat ? Math.min(brp.x, W - sa.r) : Math.min(fr.x + fr.s, W - sa.r);
    const aoT = isFlat ? Math.max(tl.y, sa.t) : Math.max(fr.y, sa.t);
    const aoL = isFlat ? Math.max(tl.x, sa.l) : Math.max(fr.x, sa.l);
    const aoB = isFlat ? Math.min(brp.y, H - sa.lb) : Math.min(fr.y + fr.s, H - sa.lb);

    // 指北针（AO 右下内角：右上角留给事件浮窗）
    const cx = aoR - 26, cy = aoB - 30;
    ctx.fillStyle = "rgba(9, 13, 18, 0.72)";
    ctx.strokeStyle = "rgba(140, 154, 170, 0.35)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(cx, cy, 16, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#ff5b4f";
    ctx.beginPath(); ctx.moveTo(cx, cy - 12); ctx.lineTo(cx + 4.5, cy); ctx.lineTo(cx - 4.5, cy); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "rgba(156, 170, 184, 0.65)";
    ctx.beginPath(); ctx.moveTo(cx, cy + 12); ctx.lineTo(cx + 4.5, cy); ctx.lineTo(cx - 4.5, cy); ctx.closePath(); ctx.fill();
    haloText(ctx, "N", cx, cy - 19, "#ffc9c3", "700 9.5px 'JetBrains Mono', 'SF Mono', Menlo, monospace");

    // 比例尺（平面图，随缩放倍率自动切换量程）
    if (isFlat) {
      const z = view.zoom || 1;
      const pxPerM = basePxPerM(view) * z;
      // 量程自适应：取使比例尺长度落在约 70–170 px 的最小整数量程
      const refKm = [0.5, 1, 2, 5, 10].find((k) => k * 1000 * pxPerM >= 70) || 10;
      const len = refKm * 1000 * pxPerM;
      const x0 = aoL + 16, y0 = aoB - 14;
      ctx.fillStyle = "rgba(9, 13, 18, 0.72)";
      roundRect(ctx, x0 - 8, y0 - 18, len + 16, 26, 2); ctx.fill();
      ctx.fillStyle = "rgba(220, 228, 236, 0.85)";
      ctx.fillRect(x0, y0, len / 2, 3);
      ctx.fillStyle = "rgba(86, 100, 116, 0.85)";
      ctx.fillRect(x0 + len / 2, y0, len / 2, 3);
      ctx.font = "600 9px 'JetBrains Mono', 'SF Mono', Menlo, monospace"; ctx.fillStyle = "rgba(156, 170, 184, 0.8)";
      ctx.textAlign = "left"; ctx.fillText("0", x0 - 2, y0 - 5);
      ctx.textAlign = "center"; ctx.fillText(String(refKm / 2), x0 + len / 2, y0 - 5);
      ctx.textAlign = "right"; ctx.fillText(`${refKm} km`, x0 + len + 4, y0 - 5);
    } else {
      pillLabel(ctx, "2.5D 实况斜视角 · 25°", aoL + 80, aoT + 14, { fg: "#dce4ec", bg: "rgba(9, 13, 18, 0.72)", border: "rgba(220, 228, 236, 0.35)", size: 10 });
    }
  }

  function sameSafe(a, b) {
    a = a || {}; b = b || {};
    return ["l", "t", "r", "b", "lb"].every((k) => Math.round(a[k] || 0) === Math.round(b[k] || 0));
  }

  // cssW / cssH：画布逻辑尺寸（全屏）；safe：HUD 浮层占用的四边留白
  function resize(canvas, cssW, cssH, safe) {
    const dpr = Math.min(2.5, window.devicePixelRatio || 1);
    const w = Math.max(200, Math.floor(cssW)), h = Math.max(200, Math.floor(cssH));
    const prev = canvas._view;
    const sf = safe
      ? { l: Math.round(safe.l || 0), t: Math.round(safe.t || 0), r: Math.round(safe.r || 0), b: Math.round(safe.b || 0), lb: Math.round(safe.lb || 0) }
      : { l: 0, t: 0, r: 0, b: 0, lb: 0 };
    if (prev && prev.width === w && prev.height === h && prev.dpr === dpr && sameSafe(prev.safe, sf)) return false;
    if (!prev || prev.width !== w || prev.height !== h || prev.dpr !== dpr) {
      canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    }
    canvas._view = {
      width: w,
      height: h,
      dpr,
      safe: sf,
      zoom: prev ? prev.zoom || 1 : 1,
      panX: prev && prev.width ? (prev.panX || 0) * (w / prev.width) : 0,
      panY: prev && prev.height ? (prev.panY || 0) * (h / prev.height) : 0,
    };
    clampCamera(canvas._view);
    return true;
  }

  window.TacticalRenderer = {
    renderFrame, worldToScreen, screenToWorld, sampleElevation,
    resize, getView, unitScreenPos, zoomAt, panBy, resetCamera, mapFrame,
  };
})();
