// 《守夜》Nightwatch 战术画布双视图渲染引擎 (指挥台平面图 + 2.5D 25° 实况斜视角)
(function () {
  const MAP_SIZE_M = 20000;
  let terrainCacheCmd = null;
  let terrainCache25D = null;
  let cachedNightKey = "";

  function worldToScreen(wx, wy, altM, canvas, viewMode, elevM) {
    const W = canvas.width;
    const H = canvas.height;
    const nx = wx / MAP_SIZE_M;
    const ny = 1.0 - wy / MAP_SIZE_M;
    if (viewMode !== "live25d") {
      const pad = 28;
      return {
        x: pad + nx * (W - pad * 2),
        y: pad + ny * (H - pad * 2),
        scale: 1.0,
      };
    }
    // 25° 俯角 2.5D 透视投影：北端略收窄，地形海拔与目标高度向上抬升
    const persp = 0.72 + 0.28 * ny;
    const sx = W * 0.5 + (nx - 0.5) * (W * 0.86) * persp;
    const baseSy = H * 0.13 + Math.pow(ny, 0.92) * (H * 0.79);
    const totalZ = (elevM || 0) * 0.08 + (altM || 0) * 0.055;
    return { x: sx, y: baseSy - totalZ, groundY: baseSy, scale: persp };
  }

  function screenToWorld(px, py, canvas, viewMode) {
    const W = canvas.width;
    const H = canvas.height;
    if (viewMode !== "live25d") {
      const pad = 28;
      const nx = (px - pad) / (W - pad * 2);
      const ny = (py - pad) / (H - pad * 2);
      return [
        Math.max(0, Math.min(MAP_SIZE_M, nx * MAP_SIZE_M)),
        Math.max(0, Math.min(MAP_SIZE_M, (1.0 - ny) * MAP_SIZE_M)),
      ];
    }
    const rawNy = Math.max(0, Math.min(1, (py - H * 0.13) / (H * 0.79)));
    const ny = Math.pow(rawNy, 1 / 0.92);
    const persp = 0.72 + 0.28 * ny;
    const nx = 0.5 + (px - W * 0.5) / ((W * 0.86) * persp);
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

  function buildStaticTerrainCanvas(meta, width, height, viewMode) {
    const off = document.createElement("canvas");
    off.width = width;
    off.height = height;
    const ctx = off.getContext("2d");
    ctx.fillStyle = viewMode === "live25d" ? "#05090e" : "#081018";
    ctx.fillRect(0, 0, width, height);
    if (!meta || !meta.map) return off;

    const g = meta.map.elevationGrid || [];
    const N = g.length;
    const minE = meta.map.minElevationM || 80;
    const maxE = Math.max(minE + 10, meta.map.maxElevationM || 320);
    const stepM = MAP_SIZE_M / N;

    for (let iy = 0; iy < N; iy++) {
      const wy = (iy + 0.5) * stepM;
      for (let ix = 0; ix < N; ix++) {
        const wx = (ix + 0.5) * stepM;
        const elev = g[iy][ix];
        const t = Math.max(0, Math.min(1, (elev - minE) / (maxE - minE)));
        const p = worldToScreen(wx, wy, 0, off, viewMode, elev);
        const r = Math.round(11 + t * 46);
        const gr = Math.round(22 + t * 52);
        const b = Math.round(30 + t * 34);
        ctx.fillStyle = `rgb(${r},${gr},${b})`;
        const cw = (width / N) * 1.25;
        ctx.fillRect(p.x - cw * 0.5, p.y - cw * 0.5, cw, cw);
        // 50m 等高线高光
        if (ix > 0 && iy > 0) {
          const b0 = Math.floor(elev / 35);
          if (b0 !== Math.floor(g[iy][ix - 1] / 35) || b0 !== Math.floor(g[iy - 1][ix] / 35)) {
            ctx.fillStyle = t > 0.55 ? "rgba(245, 158, 11, 0.26)" : "rgba(125, 211, 252, 0.14)";
            ctx.fillRect(p.x, p.y, 1.6, 1.6);
          }
        }
      }
    }

    // 绘制森林、城区、河流、道路
    const ly = meta.layers || {};
    (ly.forests || []).forEach((f) => {
      drawPolygon(ctx, f.polygon, off, viewMode, meta, "rgba(20, 83, 45, 0.28)", "rgba(34, 197, 94, 0.2)");
    });
    (ly.urban || []).forEach((u) => {
      const fill = u.density === "core" ? "rgba(245, 158, 11, 0.16)" : "rgba(148, 163, 184, 0.12)";
      drawPolygon(ctx, u.polygon, off, viewMode, meta, fill, "rgba(251, 191, 36, 0.3)");
    });
    (ly.rivers || []).forEach((rv) => {
      drawPath(ctx, rv.path, off, viewMode, meta, "rgba(14, 116, 144, 0.55)", 6);
    });
    (ly.roads || []).forEach((rd) => {
      drawPath(ctx, rd.path, off, viewMode, meta, "rgba(148, 163, 184, 0.28)", rd.class === "main" ? 2.2 : 1.2);
    });

    // 战术方格网与北山脊标注
    ctx.strokeStyle = "rgba(56, 189, 248, 0.08)";
    ctx.lineWidth = 1;
    for (let m = 0; m <= MAP_SIZE_M; m += 2500) {
      const p1 = worldToScreen(m, 0, 0, off, viewMode, 110);
      const p2 = worldToScreen(m, MAP_SIZE_M, 0, off, viewMode, 110);
      ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
      const q1 = worldToScreen(0, m, 0, off, viewMode, 110);
      const q2 = worldToScreen(MAP_SIZE_M, m, 0, off, viewMode, 110);
      ctx.beginPath(); ctx.moveTo(q1.x, q1.y); ctx.lineTo(q2.x, q2.y); ctx.stroke();
    }
    const ridgePt = worldToScreen(10000, 14500, 0, off, viewMode, sampleElevation(meta, 10000, 14500));
    ctx.fillStyle = "rgba(253, 224, 71, 0.65)";
    ctx.font = "bold 11px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("▲ 北山脊棱线 (海拔 ~280m · 低空雷达遮挡带)", ridgePt.x, ridgePt.y - 4);
    return off;
  }

  function drawPolygon(ctx, pts, canvas, viewMode, meta, fill, stroke) {
    if (!pts || pts.length < 3) return;
    ctx.beginPath();
    pts.forEach((pt, idx) => {
      const p = worldToScreen(pt[0], pt[1], 0, canvas, viewMode, sampleElevation(meta, pt[0], pt[1]));
      if (idx === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.stroke(); }
  }

  function drawPath(ctx, pts, canvas, viewMode, meta, stroke, width) {
    if (!pts || pts.length < 2) return;
    ctx.beginPath();
    pts.forEach((pt, idx) => {
      const p = worldToScreen(pt[0], pt[1], 0, canvas, viewMode, sampleElevation(meta, pt[0], pt[1]));
      if (idx === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.strokeStyle = stroke;
    ctx.lineWidth = width;
    ctx.stroke();
  }

  function renderFrame(canvas, state) {
    const ctx = canvas.getContext("2d");
    const meta = state.meta;
    if (!meta) return;
    const viewMode = state.viewMode || "command";
    const key = `${meta.levelId}_${meta.nightIndex}_${canvas.width}`;
    if (cachedNightKey !== key) {
      terrainCacheCmd = buildStaticTerrainCanvas(meta, canvas.width, canvas.height, "command");
      terrainCache25D = buildStaticTerrainCanvas(meta, canvas.width, canvas.height, "live25d");
      cachedNightKey = key;
    }
    ctx.drawImage(viewMode === "live25d" ? terrainCache25D : terrainCacheCmd, 0, 0);

    // 1. 雷达通视与北山脊盲区覆盖网格
    if (state.losAltM > 0 && state.coverage && state.coverage.grid) {
      const g = state.coverage.grid;
      const R = g.length;
      const stepM = MAP_SIZE_M / R;
      const cellPx = (canvas.width / R) * 1.1;
      for (let iy = 0; iy < R; iy++) {
        const wy = (iy + 0.5) * stepM;
        for (let ix = 0; ix < R; ix++) {
          const st = g[iy][ix];
          if (st === 0) continue;
          const wx = (ix + 0.5) * stepM;
          const p = worldToScreen(wx, wy, 0, canvas, viewMode, sampleElevation(meta, wx, wy));
          ctx.fillStyle = st === 2 ? "rgba(34, 197, 94, 0.13)" : "rgba(239, 68, 68, 0.24)";
          ctx.fillRect(p.x - cellPx * 0.5, p.y - cellPx * 0.5, cellPx, cellPx);
        }
      }
    }

    // 2. 战前禁区与预备阵地
    if (state.phase === "deploy" && meta.deploy) {
      (meta.deploy.forbidden || []).forEach((fb) => {
        drawPolygon(ctx, fb.polygon, canvas, viewMode, meta, "rgba(239, 68, 68, 0.16)", "rgba(239, 68, 68, 0.5)");
      });
    }
    ((meta.deploy && meta.deploy.alternatePositions) || []).forEach((ap) => {
      const p = worldToScreen(ap.pos[0], ap.pos[1], 0, canvas, viewMode, sampleElevation(meta, ap.pos[0], ap.pos[1]));
      ctx.strokeStyle = "rgba(125, 211, 252, 0.45)";
      ctx.setLineDash([2, 2]);
      ctx.strokeRect(p.x - 5, p.y - 5, 10, 10);
      ctx.setLineDash([]);
    });

    // 3. 敌军进袭方向入口标记
    (meta.entryPoints || []).forEach((ep) => {
      const p = worldToScreen(ep.pos[0], ep.pos[1], 0, canvas, viewMode, sampleElevation(meta, ep.pos[0], ep.pos[1]));
      ctx.fillStyle = "rgba(248, 113, 113, 0.85)";
      ctx.font = "bold 10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`▼ ${ep.name}`, p.x, Math.max(14, Math.min(canvas.height - 8, p.y)));
    });

    // 4. 电网连线与保卫建筑
    drawGridAndStructures(ctx, canvas, state, viewMode, meta);

    // 5. 第 2 夜暴露阵地猎杀红圈预警
    const kts = (meta.carryIn && meta.carryIn.knownTargets) || [];
    kts.forEach((kt) => {
      const p = worldToScreen(kt.pos[0], kt.pos[1], 0, canvas, viewMode, sampleElevation(meta, kt.pos[0], kt.pos[1]));
      ctx.strokeStyle = "rgba(239, 68, 68, 0.85)";
      ctx.lineWidth = 1.8;
      ctx.setLineDash([4, 3]);
      ctx.beginPath(); ctx.arc(p.x, p.y, 18, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "#fca5a5";
      ctx.font = "10px sans-serif";
      ctx.fillText("⚠ 敌已标定", p.x, p.y - 21);
    });

    // 6. 我方防空单位与射程环
    drawUnits(ctx, canvas, state, viewMode, meta);

    // 7. 战场航迹、真值透视、拦截弹与爆炸特效
    if (state.snapshot) {
      drawTracksAndCombat(ctx, canvas, state, viewMode, meta);
    }
  }

  function drawGridAndStructures(ctx, canvas, state, viewMode, meta) {
    const snap = state.snapshot;
    const nodeMap = {};
    ((meta.grid && meta.grid.nodes) || []).forEach((n) => { nodeMap[n.id] = { pos: n.pos, powered: true }; });
    if (snap && snap.grid && snap.grid.nodes) {
      snap.grid.nodes.forEach((gn) => { if (nodeMap[gn.id]) nodeMap[gn.id].powered = gn.powered; });
    }
    ((meta.grid && meta.grid.links) || []).forEach((lk) => {
      const a = nodeMap[lk[0]], b = nodeMap[lk[1]];
      if (!a || !b) return;
      const pa = worldToScreen(a.pos[0], a.pos[1], 0, canvas, viewMode, sampleElevation(meta, a.pos[0], a.pos[1]));
      const pb = worldToScreen(b.pos[0], b.pos[1], 0, canvas, viewMode, sampleElevation(meta, b.pos[0], b.pos[1]));
      ctx.strokeStyle = a.powered && b.powered ? "rgba(56, 189, 248, 0.35)" : "rgba(239, 68, 68, 0.45)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
      ctx.setLineDash([]);
    });

    const structs = (snap && snap.structures) || meta.structures || [];
    structs.forEach((s) => {
      const elev = sampleElevation(meta, s.pos[0], s.pos[1]);
      const p = worldToScreen(s.pos[0], s.pos[1], 0, canvas, viewMode, elev);
      const hpFrac = Math.max(0, s.hp / Math.max(1, s.maxHp));
      ctx.fillStyle = s.destroyed ? "#7f1d1d" : (s.powered === false ? "#475569" : "#eab308");
      ctx.strokeStyle = "#fef08a";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.rect(p.x - 8, p.y - 8, 16, 16);
      ctx.fill(); ctx.stroke();
      // 血条与名称
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(p.x - 16, p.y + 11, 32, 4);
      ctx.fillStyle = hpFrac > 0.5 ? "#22c55e" : (hpFrac > 0.2 ? "#f59e0b" : "#ef4444");
      ctx.fillRect(p.x - 16, p.y + 11, 32 * hpFrac, 4);
      ctx.fillStyle = "#fef9c3";
      ctx.font = "bold 11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`${s.name} (${s.hp}/${s.maxHp})`, p.x, p.y - 12);
    });
  }

  function drawUnits(ctx, canvas, state, viewMode, meta) {
    const list = state.phase === "deploy" ? state.placements : (state.snapshot ? state.snapshot.units : []);
    const nowMs = performance.now();
    list.forEach((u) => {
      const idKey = u.id || u.rosterId;
      const isSel = state.selectedUnitKey === idKey;
      const elev = sampleElevation(meta, u.pos[0], u.pos[1]);
      const p = worldToScreen(u.pos[0], u.pos[1], 0, canvas, viewMode, elev);

      // 选中单位显示射程环与探测环
      if (isSel) {
        const pxPerM = (canvas.width - 56) / MAP_SIZE_M;
        const detR = u.detectionRangeM || 0;
        if (detR > 0) {
          ctx.strokeStyle = "rgba(45, 212, 191, 0.45)";
          ctx.lineWidth = 1.2;
          ctx.setLineDash([5, 4]);
          ctx.beginPath(); ctx.arc(p.x, p.y, detR * pxPerM, 0, Math.PI * 2); ctx.stroke();
          ctx.setLineDash([]);
        }
        (u.weapons || []).forEach((w) => {
          if (w.rangeM > 0) {
            ctx.strokeStyle = "rgba(56, 189, 248, 0.55)";
            ctx.lineWidth = 1.4;
            ctx.beginPath(); ctx.arc(p.x, p.y, w.rangeM * pxPerM, 0, Math.PI * 2); ctx.stroke();
          }
        });
      }

      // 2.5D 视图下绘制机动防空组探照灯光锥
      if (viewMode === "live25d" && u.unitDefId === "mobile_fire_team" && state.phase === "battle") {
        const ang = -Math.PI * 0.5 + Math.sin(nowMs * 0.0015 + idKey) * 0.45;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(ang);
        const grad = ctx.createLinearGradient(0, 0, 75, 0);
        grad.addColorStop(0, "rgba(254, 249, 195, 0.32)");
        grad.addColorStop(1, "rgba(254, 249, 195, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(75, -14); ctx.lineTo(75, 14); ctx.closePath(); ctx.fill();
        ctx.restore();
      }

      // 机动转移路线
      if (u.relocation && u.relocation.dest) {
        const dp = worldToScreen(u.relocation.dest[0], u.relocation.dest[1], 0, canvas, viewMode, elev);
        ctx.strokeStyle = "#38bdf8";
        ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(dp.x, dp.y); ctx.stroke();
        ctx.setLineDash([]);
      }

      // 暴露度外环
      const exp = u.exposure || 0;
      if (exp > 5) {
        ctx.strokeStyle = exp >= 70 ? "#ef4444" : "#f59e0b";
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 11, -Math.PI * 0.5, -Math.PI * 0.5 + Math.min(1, exp / 100) * Math.PI * 2);
        ctx.stroke();
      }

      // 单位主体符号
      const cat = u.category || "fire";
      ctx.fillStyle = cat === "sensor" ? "#2dd4bf" : (cat === "ew" ? "#a855f7" : (cat === "deception" ? "#94a3b8" : "#38bdf8"));
      if (u.deployState && u.deployState !== "ACTIVE") ctx.fillStyle = "#64748b";
      ctx.strokeStyle = isSel ? "#ffffff" : "#0f172a";
      ctx.lineWidth = isSel ? 2.5 : 1.5;
      ctx.beginPath();
      ctx.arc(p.x, p.y, isSel ? 7.5 : 6, 0, Math.PI * 2);
      ctx.fill(); ctx.stroke();

      // 雷达开机旋转扫描线
      const emOn = u.emitter ? u.emitter.on : (u.emissionPolicy !== "silent" && (cat === "sensor" || u.unitDefId === "nasams" || u.unitDefId === "soviet_mid_range_radar"));
      if (emOn) {
        const a = (nowMs * 0.004 + idKey) % (Math.PI * 2);
        ctx.strokeStyle = "rgba(45, 212, 191, 0.85)";
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + Math.cos(a) * 13, p.y + Math.sin(a) * 13); ctx.stroke();
      }

      ctx.fillStyle = isSel ? "#fff" : "#cbd5e1";
      ctx.font = isSel ? "bold 10.5px sans-serif" : "10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(u.name.replace("防空系统", "").replace("火控雷达", ""), p.x, p.y + 17);
    });
  }

  function drawTracksAndCombat(ctx, canvas, state, viewMode, meta) {
    const snap = state.snapshot;
    // 真值透视层
    if (state.godView && snap.threats) {
      snap.threats.forEach((th) => {
        const elev = sampleElevation(meta, th.pos[0], th.pos[1]);
        const p = worldToScreen(th.pos[0], th.pos[1], th.altM, canvas, viewMode, elev);
        if (viewMode === "live25d" && p.groundY) {
          ctx.strokeStyle = "rgba(244, 63, 94, 0.3)";
          ctx.beginPath(); ctx.moveTo(p.x, p.groundY); ctx.lineTo(p.x, p.y); ctx.stroke();
        }
        ctx.fillStyle = "rgba(244, 63, 94, 0.45)";
        ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, Math.PI * 2); ctx.fill();
      });
    }

    // T0-T3 航迹符号
    const qColors = ["#94a3b8", "#facc15", "#f97316", "#ef4444"];
    (snap.tracks || []).forEach((trk) => {
      const elev = sampleElevation(meta, trk.pos[0], trk.pos[1]);
      const p = worldToScreen(trk.pos[0], trk.pos[1], 140, canvas, viewMode, elev);
      const col = qColors[trk.quality] || "#ef4444";
      if (trk.quality === 0) {
        ctx.strokeStyle = "rgba(148, 163, 184, 0.55)";
        ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.arc(p.x, p.y, Math.max(10, trk.uncertaintyRadiusM * 0.018), 0, Math.PI * 2); ctx.stroke();
        ctx.setLineDash([]);
      }
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(-trk.headingRad);
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.moveTo(7, 0); ctx.lineTo(-5, -4.5); ctx.lineTo(-3, 0); ctx.lineTo(-5, 4.5); ctx.closePath();
      ctx.fill();
      ctx.restore();

      ctx.fillStyle = col;
      ctx.font = "10px monospace";
      ctx.textAlign = "left";
      const tagStr = trk.identifiedAsDecoy ? "诱饵" : (trk.quality >= 3 ? trk.tag : `T${trk.quality}`);
      ctx.fillText(tagStr, p.x + 8, p.y + 3);
    });

    // 飞行中的拦截弹与高炮曳光弹链
    (snap.interceptors || []).forEach((ic) => {
      const p0 = worldToScreen(ic.launchPos[0], ic.launchPos[1], 0, canvas, viewMode, 140);
      const pc = worldToScreen(ic.curPos[0], ic.curPos[1], 120, canvas, viewMode, 140);
      const isGun = ic.weaponId === "gepard_35mm" || ic.weaponId === "mdf_hmg";
      ctx.strokeStyle = isGun ? "#fde047" : "#38bdf8";
      ctx.lineWidth = isGun ? 1.4 : 2.0;
      if (isGun) ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(pc.x, pc.y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(pc.x, pc.y, 2.5, 0, Math.PI * 2); ctx.fill();
    });

    // 瞬态爆炸与拦截光环
    const now = performance.now();
    state.fxList = (state.fxList || []).filter((fx) => now - fx.t0 < 1400);
    state.fxList.forEach((fx) => {
      const age = (now - fx.t0) / 1400;
      const p = worldToScreen(fx.pos[0], fx.pos[1], 100, canvas, viewMode, 140);
      ctx.strokeStyle = fx.kind === "hit" ? `rgba(239, 68, 68, ${1 - age})` : `rgba(34, 197, 94, ${1 - age})`;
      ctx.lineWidth = fx.kind === "hit" ? 3 : 2;
      ctx.beginPath(); ctx.arc(p.x, p.y, 4 + age * (fx.kind === "hit" ? 28 : 18), 0, Math.PI * 2); ctx.stroke();
    });
  }

  window.TacticalRenderer = { renderFrame, worldToScreen, screenToWorld, sampleElevation };
})();
