// 《守夜》Nightwatch 新手引导组件：聚光灯教程 (Coach)、事件浮窗 (Toast)、悬停说明 (Tips)
(function () {
  const $ = (id) => document.getElementById(id);

  // ───────────── 聚光灯教程 ─────────────
  // step: { title, text, target: () => DOMRect | null | string(selector), pad, onEnter, nextLabel, hideNav }
  const Coach = {
    steps: [], idx: 0, active: false, onDone: null, raf: 0,
    run(steps, opts) {
      this.steps = steps; this.idx = 0; this.active = true;
      this.onDone = (opts && opts.onDone) || null;
      $("coach-layer").classList.remove("hidden");
      this.show();
      const loop = () => { if (!this.active) return; this.position(); this.raf = requestAnimationFrame(loop); };
      cancelAnimationFrame(this.raf); this.raf = requestAnimationFrame(loop);
    },
    stop(completed) {
      if (!this.active) return;
      this.active = false;
      cancelAnimationFrame(this.raf);
      $("coach-layer").classList.add("hidden");
      const cb = this.onDone; this.onDone = null;
      if (cb) cb(Boolean(completed));
    },
    show() {
      const s = this.steps[this.idx];
      if (!s) return this.stop(true);
      if (s.onEnter) s.onEnter();
      $("coach-step").textContent = this.steps.length > 1 ? `${this.idx + 1} / ${this.steps.length}` : "提示";
      $("coach-title").innerHTML = s.title || "";
      $("coach-text").innerHTML = s.text || "";
      $("coach-prev").style.display = this.idx > 0 ? "" : "none";
      $("coach-skip").style.display = this.steps.length > 1 && this.idx < this.steps.length - 1 ? "" : "none";
      $("coach-next").textContent = s.nextLabel || (this.idx === this.steps.length - 1 ? "知道了" : "下一步");
      const b = $("coach-bubble");
      b.classList.remove("pop"); void b.offsetWidth; b.classList.add("pop");
      this.position();
    },
    rectOf(s) {
      if (!s.target) return null;
      if (typeof s.target === "string") {
        const el = document.querySelector(s.target);
        if (!el || el.offsetParent === null) return null;
        return el.getBoundingClientRect();
      }
      return s.target();
    },
    position() {
      const s = this.steps[this.idx];
      if (!s) return;
      const spot = $("coach-spot"), b = $("coach-bubble");
      const r = this.rectOf(s);
      const vw = window.innerWidth, vh = window.innerHeight;
      const bw = b.offsetWidth || 320, bh = b.offsetHeight || 160;
      if (!r) {
        spot.style.cssText = `left:${vw / 2}px;top:${vh / 2}px;width:0;height:0;`;
        b.style.left = `${(vw - bw) / 2}px`; b.style.top = `${(vh - bh) / 2}px`;
        return;
      }
      const pad = s.pad === undefined ? 6 : s.pad;
      const x = r.left - pad, y = r.top - pad, w = r.width + pad * 2, h = r.height + pad * 2;
      spot.style.cssText = `left:${x}px;top:${y}px;width:${w}px;height:${h}px;`;
      // 气泡：优先右侧 → 左侧 → 下方 → 上方
      const gap = 14;
      const cands = [
        [x + w + gap, y + h / 2 - bh / 2],
        [x - bw - gap, y + h / 2 - bh / 2],
        [x + w / 2 - bw / 2, y + h + gap],
        [x + w / 2 - bw / 2, y - bh - gap],
      ];
      if (s.placement === "bottom") cands.unshift(cands[2]);
      if (s.placement === "top") cands.unshift(cands[3]);
      if (s.placement === "left") cands.unshift(cands[1]);
      let pos = cands.find(([bx, by]) => bx >= 8 && by >= 8 && bx + bw <= vw - 8 && by + bh <= vh - 8);
      if (!pos) pos = [Math.min(vw - bw - 8, Math.max(8, x + w + gap)), Math.min(vh - bh - 8, Math.max(8, y))];
      b.style.left = `${Math.max(8, Math.min(vw - bw - 8, pos[0]))}px`;
      b.style.top = `${Math.max(8, Math.min(vh - bh - 8, pos[1]))}px`;
    },
  };
  $("coach-next").addEventListener("click", () => { Coach.idx++; Coach.show(); });
  $("coach-prev").addEventListener("click", () => { Coach.idx = Math.max(0, Coach.idx - 1); Coach.show(); });
  $("coach-skip").addEventListener("click", () => Coach.stop(false));

  // ───────────── 事件浮窗 ─────────────
  const Toast = {
    show(o) {
      const stack = $("toast-stack");
      if (o.key) {
        const ex = stack.querySelector(`[data-key="${o.key}"]`);
        if (ex) {
          const n = Number(ex.dataset.n || 1) + 1;
          ex.dataset.n = n;
          ex.querySelector(".toast-title").textContent = o.title + (n > 1 ? ` ×${n}` : "");
          clearTimeout(ex._t);
          ex._t = setTimeout(() => this.remove(ex), o.ttl || 2600);
          return;
        }
      }
      const el = document.createElement("div");
      el.className = `toast toast-${o.kind || "info"}`;
      if (o.key) el.dataset.key = o.key;
      el.innerHTML = `<span class="toast-ico">${o.icon || "•"}</span><div><div class="toast-title"></div>${o.text ? '<div class="toast-text"></div>' : ""}</div>`;
      el.querySelector(".toast-title").textContent = o.title;
      if (o.text) el.querySelector(".toast-text").textContent = o.text;
      stack.prepend(el);
      while (stack.children.length > 4) stack.removeChild(stack.lastChild);
      el._t = setTimeout(() => this.remove(el), o.ttl || 3200);
    },
    remove(el) {
      el.classList.add("out");
      setTimeout(() => el.remove(), 300);
    },
    clear() { $("toast-stack").innerHTML = ""; },
  };

  // ───────────── 悬停说明 ─────────────
  function bindTips() {
    const tip = $("ui-tip");
    let cur = null;
    document.addEventListener("mouseover", (e) => {
      const el = e.target.closest && e.target.closest("[data-tip]");
      if (el === cur) return;
      cur = el;
      if (!el || Coach.active) { tip.classList.add("hidden"); return; }
      tip.textContent = el.dataset.tip;
      tip.classList.remove("hidden");
      const r = el.getBoundingClientRect();
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      let x = r.left + r.width / 2 - tw / 2, y = r.bottom + 8;
      if (y + th > window.innerHeight - 6) y = r.top - th - 8;
      x = Math.max(6, Math.min(window.innerWidth - tw - 6, x));
      tip.style.left = `${x}px`; tip.style.top = `${y}px`;
    });
    document.addEventListener("mousedown", () => { tip.classList.add("hidden"); cur = null; });
  }
  bindTips();

  window.NWGuide = { Coach, Toast };
})();
