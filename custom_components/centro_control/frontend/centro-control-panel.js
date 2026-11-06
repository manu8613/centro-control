/*
 * Centro de Control — panel propio para Home Assistant.
 * Creado por manu8613 · https://github.com/manu8613/centro-control
 * Licencia Apache 2.0 (ver LICENSE y NOTICE).
 *
 * Panel independiente: no necesita tarjetas de HACS. Lee los estados de
 * Home Assistant, pide el historial por websocket y dibuja todo en SVG.
 */

const C = {
  cyan: "#00e5ff", amber: "#ffc400", green: "#00e676", pink: "#ff4fd8", violet: "#b388ff",
  blue: "#40c4ff", orange: "#ff9100", red: "#ff1744", lime: "#c6ff00", gold: "#ffd740",
  text: "#e6f7ff", muted: "#8fb3c9", line: "#1b2a44", dim: "#1d2d4a",
};
const PALETTE = [C.pink, C.violet, C.orange, C.blue, C.cyan, C.lime, C.gold, C.amber, C.green, C.red, "#ff8a80", "#82b1ff"];
const PERIODS = { hoy: "Hoy", ayer: "Ayer", mes: "Este mes", factura: "Factura", ano: "Este año", total: "Total" };
const TABS = [
  ["resumen", "Puente de mando", "mdi:view-dashboard-variant", C.cyan],
  ["red", "Red", "mdi:transmission-tower", C.cyan],
  ["solar", "Solar", "mdi:solar-power-variant", C.amber],
  ["bateria", "Batería", "mdi:home-battery", C.green],
  ["consumos", "Consumos", "mdi:home-lightning-bolt", C.pink],
  ["problemas", "Problemas", "mdi:alert-decagram", C.red],
  ["coste", "Coste", "mdi:cash-multiple", C.gold],
  ["co2", "CO₂", "mdi:leaf-circle", C.lime],
  ["gas", "Gas", "mdi:fire", C.violet],
  ["luces", "Luces", "mdi:lightbulb-group", C.gold],
  ["clima", "Temperaturas", "mdi:thermometer", C.orange],
  ["riego", "Riego", "mdi:sprinkler-variant", C.blue],
];

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const n = (x, d = 1) => {
  const v = Number(x);
  if (x === null || x === undefined || x === "" || Number.isNaN(v)) return "—";
  return v.toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });
};
const w = (x) => {
  const v = Number(x);
  if (x === null || x === undefined || Number.isNaN(v)) return "—";
  return Math.abs(v) >= 1000 ? `${n(v / 1000, 2)} kW` : `${n(v, 0)} W`;
};
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const niceStep = (span) => {
  const raw = span / 4 || 1, mag = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || 10 * mag;
};

class CentroControlPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "resumen";
    try { this._tab = localStorage.getItem("centro-control-tab") || "resumen"; } catch (e) { /* storage blocked */ }
    this._hist = {};
    this._busy = false;
    this._timer = null;
    this._last = 0;
    this._built = false;
  }

  set panel(panel) { this._panel = panel; this._ctx = (panel && panel.config && panel.config.ctx) || {}; this._schedule(true); }
  set narrow(v) { this._narrow = v; this.toggleAttribute("narrow", !!v); if (this._menu) this._menu.narrow = v; this._schedule(); }
  set route(v) { this._route = v; }
  set hass(hass) {
    this._hass = hass;
    if (this._menu) { this._menu.hass = hass; this._menu.narrow = this._narrow; }
    this._schedule();
  }

  connectedCallback() { this._schedule(true); }

  // ------------------------------------------------------------------ data
  id(key) { return (this._ctx.ids || {})[key]; }
  st(id) { return id && this._hass ? this._hass.states[id] : undefined; }
  val(id) { const s = this.st(id); return s ? s.state : undefined; }
  num(id) { const s = this.st(id); if (!s) return null; const v = parseFloat(s.state); return Number.isNaN(v) ? null : v; }
  attr(id, a) { const s = this.st(id); return s ? s.attributes[a] : undefined; }
  k(key) { return this.num(this.id(key)); }
  ka(key, a) { return this.attr(this.id(key), a); }
  name(id) { return this.attr(id, "friendly_name") || (id || "").split(".").pop().replace(/_/g, " "); }
  setting(key) { const v = (this._ctx.settings || {})[key]; return v === "" || v === null || v === undefined ? undefined : v; }
  period() { return this.val(this.id("periodo")) || "hoy"; }

  // ------------------------------------------------------------------ render loop
  _schedule(now = false) {
    if (!this._hass || !this._ctx) return;
    if (!this._built) { this._build(); }
    const wait = now ? 0 : Math.max(0, 1500 - (Date.now() - this._last));
    if (this._timer) return;
    this._timer = setTimeout(() => { this._timer = null; this._render(); }, wait);
  }

  _build() {
    this._built = true;
    const root = this.shadowRoot;
    root.innerHTML = `<style>${STYLE}</style>
      <div class="app">
        <header>
          <div class="brand"><span class="menu"></span><ha-icon icon="mdi:atom-variant"></ha-icon><span class="title"></span><span class="clock"></span></div>
          <nav></nav>
        </header>
        <main></main>
        <footer></footer>
      </div>`;
    this._menu = document.createElement("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;
    root.querySelector(".menu").appendChild(this._menu);
    root.addEventListener("click", (ev) => this._click(ev));
    root.addEventListener("change", (ev) => this._change(ev));
    root.addEventListener("pointerdown", (ev) => { if (ev.target.matches("input")) this._busy = true; });
    root.addEventListener("pointerup", () => { setTimeout(() => { this._busy = false; }, 300); });
  }

  _render() {
    if (this._busy) { this._schedule(); return; }
    this._last = Date.now();
    const root = this.shadowRoot;
    const ctx = this._ctx;
    root.querySelector(".title").textContent = (ctx.title || "Centro de Control").toUpperCase();
    root.querySelector(".clock").textContent = new Date().toLocaleString("es-ES", { weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    const problems = this.ka("problemas", "lista") || [];
    const crit = problems.filter((p) => p.nivel === "critico" && !p.reconocido).length;
    root.querySelector("nav").innerHTML = TABS.map(([key, label, icon, color]) => {
      const badge = key === "problemas" && problems.filter((p) => !p.reconocido).length
        ? `<b class="badge" style="background:${crit ? C.red : C.amber}">${problems.filter((p) => !p.reconocido).length}</b>` : "";
      return `<button class="tab ${key === this._tab ? "on" : ""}" data-action="tab" data-tab="${key}" style="--c:${color}"><ha-icon icon="${icon}"></ha-icon><span>${label}</span>${badge}</button>`;
    }).join("");
    const view = this[`v_${this._tab}`] ? this._tab : "resumen";
    let html = "";
    try { html = this[`v_${view}`](); } catch (e) { html = `<div class="card" style="--c:${C.red}">Error dibujando la pestaña: ${esc(e.message)}</div>`; console.error(e); }
    const main = root.querySelector("main");
    const scroll = main.scrollTop;
    main.innerHTML = html;
    main.scrollTop = scroll;
    root.querySelector("footer").innerHTML = `<ha-icon icon="mdi:atom-variant"></ha-icon> Centro de Control v${esc(ctx.version || "")} · creado por <a href="${esc(ctx.author_url || "https://github.com/manu8613")}" target="_blank" rel="noopener">${esc(ctx.author || "manu8613")}</a> · <a href="${esc(ctx.repo_url || "")}" target="_blank" rel="noopener">código</a>`;
  }

  // ------------------------------------------------------------------ events
  _fire(type, detail) { this.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true })); }
  _call(domain, service, data) { return this._hass.callService(domain, service, data).catch((e) => alert(`No se pudo: ${e.message || e}`)); }

  _click(ev) {
    const el = ev.target.closest("[data-action]");
    if (!el || el.matches("input")) return;
    const a = el.dataset.action;
    const entity = el.dataset.entity;
    if (a === "tab") {
      this._tab = el.dataset.tab;
      try { localStorage.setItem("centro-control-tab", this._tab); } catch (e) { /* ignore */ }
      this.shadowRoot.querySelector("main").scrollTop = 0;
      this._render();
    } else if (a === "more") {
      if (entity) this._fire("hass-more-info", { entityId: entity });
    } else if (a === "press") {
      if (el.dataset.confirm && !confirm(el.dataset.confirm)) return;
      this._call("button", "press", { entity_id: entity });
    } else if (a === "toggle") {
      const domain = entity.split(".")[0];
      if (domain === "valve") this._call("valve", "toggle", { entity_id: entity });
      else this._call("homeassistant", "toggle", { entity_id: entity });
    } else if (a === "select") {
      this._call("select", "select_option", { entity_id: entity, option: el.dataset.option });
    } else if (a === "temp") {
      const s = this.st(entity);
      const cur = Number(s?.attributes?.temperature ?? 20);
      const step = Number(s?.attributes?.target_temp_step || 0.5) * Number(el.dataset.step);
      this._call("climate", "set_temperature", { entity_id: entity, temperature: cur + step });
    }
    ev.stopPropagation();
  }

  _change(ev) {
    const el = ev.target;
    const a = el.dataset.action;
    this._busy = false;
    if (a === "number") this._call("number", "set_value", { entity_id: el.dataset.entity, value: Number(el.value) });
    if (a === "bright") this._call("light", "turn_on", { entity_id: el.dataset.entity, brightness_pct: Number(el.value) });
  }

  // ------------------------------------------------------------------ history
  history(ids, hours = 24) {
    ids = ids.filter(Boolean);
    const key = `${hours}|${ids.join(",")}`;
    const cached = this._hist[key];
    const fresh = cached && Date.now() - cached.at < 5 * 60 * 1000;
    if (!fresh && !(cached && cached.loading)) {
      this._hist[key] = { ...(cached || {}), loading: true, at: cached ? cached.at : 0 };
      const start = new Date(Date.now() - hours * 3600 * 1000).toISOString();
      this._hass.callWS({ type: "history/history_during_period", start_time: start, entity_ids: ids, minimal_response: true, no_attributes: true, significant_changes_only: false })
        .then((res) => {
          const data = {};
          for (const id of ids) {
            data[id] = (res[id] || []).map((p) => [1000 * (p.lu || p.lc || 0), parseFloat(p.s)]).filter((p) => !Number.isNaN(p[1]) && p[0] > 0);
          }
          this._hist[key] = { at: Date.now(), data, loading: false };
          this._render();
        })
        .catch(() => { this._hist[key] = { at: Date.now(), data: {}, loading: false }; });
    }
    return (this._hist[key] && this._hist[key].data) || null;
  }

  // ------------------------------------------------------------------ building blocks
  card(body, color = C.cyan, span = 1, cls = "") { return `<section class="card ${cls}" style="--c:${color};--span:${span}">${body}</section>`; }
  head(text, icon, color = C.cyan, sub = "") {
    return `<div class="head" style="--c:${color}"><ha-icon icon="${icon}"></ha-icon><div><h2>${esc(text)}</h2>${sub ? `<p>${esc(sub)}</p>` : ""}</div></div>`;
  }
  kpi(entity, value, label, icon, color, tab) {
    const action = tab ? `data-action="tab" data-tab="${tab}"` : entity ? `data-action="more" data-entity="${entity}"` : "";
    return `<div class="kpi" ${action} style="--c:${color}"><div class="ic"><ha-icon icon="${icon}"></ha-icon></div><div><div class="v">${value}</div><div class="l">${label}</div></div></div>`;
  }
  gauge(value, min, max, color, label, unit = "", entity) {
    const f = clamp(((Number(value) || 0) - min) / ((max - min) || 1), 0, 1);
    const a = Math.PI * (1 - f);
    const x = 60 + 46 * Math.cos(a), y = 62 - 46 * Math.sin(a);
    const v = value === null || value === undefined ? "—" : `${n(value, unit === "%" ? 0 : unit === "W" ? 0 : 1)}${unit ? " " + unit : ""}`;
    return `<div class="gauge" ${entity ? `data-action="more" data-entity="${entity}"` : ""}><svg viewBox="0 0 120 84">
      <path d="M14 62 A46 46 0 0 1 106 62" class="track"/>
      <path d="M14 62 A46 46 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}" stroke="${color}" class="arc"/>
      <text x="60" y="57" class="gv">${v}</text><text x="60" y="78" class="gl">${esc(label)}</text></svg></div>`;
  }
  bar(v, max, color, width = 100) {
    const p = max > 0 ? clamp((Number(v) || 0) / max, 0, 1) * 100 : 0;
    return `<span class="bar" style="width:${width}%"><i style="width:${p}%;background:${color}"></i></span>`;
  }
  table(rows, head) {
    const th = head ? `<tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr>` : "";
    return `<table>${th}${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</table>`;
  }
  alert(p) {
    const color = p.nivel === "critico" ? C.red : p.nivel === "aviso" ? C.amber : C.blue;
    const since = p.desde ? new Date(p.desde).toLocaleString("es-ES", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "";
    return `<div class="alert" style="--c:${color}" ${p.entidad ? `data-action="more" data-entity="${p.entidad}"` : ""}>
      <b>${esc(p.titulo)}${p.reconocido ? " ✓" : ""}</b><span>${esc(p.detalle)}</span><small>${esc(p.area)} · desde ${since}</small></div>`;
  }
  btn(entity, label, icon, color, confirmText) {
    if (!entity) return "";
    return `<button class="btn" style="--c:${color}" data-action="press" data-entity="${entity}" ${confirmText ? `data-confirm="${esc(confirmText)}"` : ""}><ha-icon icon="${icon}"></ha-icon>${esc(label)}</button>`;
  }
  slider(entity, label, color) {
    const s = this.st(entity);
    if (!s) return "";
    const a = s.attributes;
    return `<label class="slider" style="--c:${color}"><span>${esc(label)}</span>
      <input type="range" min="${a.min}" max="${a.max}" step="${a.step}" value="${s.state}" data-action="number" data-entity="${entity}">
      <b>${n(s.state, a.step < 1 ? 2 : 0)} ${esc(a.unit_of_measurement || "")}</b></label>`;
  }
  periodChips(color = C.cyan) {
    const cur = this.period();
    const ent = this.id("periodo");
    return `<div class="chips" style="--c:${color}">${Object.entries(PERIODS).map(([k, l]) => `<button class="chip ${k === cur ? "on" : ""}" data-action="select" data-entity="${ent}" data-option="${k}">${l}</button>`).join("")}</div>`;
  }
  empty(text) { return `<div class="empty"><ha-icon icon="mdi:information-outline"></ha-icon>${esc(text)}</div>`; }

  // ------------------------------------------------------------------ charts
  lineChart(series, { hours = 24, height = 220, stacked = false, unit = "", width = 700 } = {}) {
    const W = window.innerWidth < 760 ? 380 : width, H = height, pad = 34;
    const end = Date.now(), start = end - hours * 3600 * 1000;
    const step = hours <= 48 ? 5 * 60 * 1000 : 60 * 60 * 1000;
    const buckets = Math.ceil((end - start) / step);
    const resampled = series.map((s) => {
      const out = new Array(buckets).fill(null);
      const pts = s.points || [];
      let j = 0, last = null;
      for (let b = 0; b < buckets; b++) {
        const t1 = start + (b + 1) * step;
        let sum = 0, cnt = 0;
        while (j < pts.length && pts[j][0] < t1) { if (pts[j][0] >= start + b * step) { sum += pts[j][1]; cnt++; } last = pts[j][1]; j++; }
        out[b] = cnt ? sum / cnt : last;
      }
      return { ...s, values: out };
    });
    let lo = 0, hi = 0;
    const stack = new Array(buckets).fill(0);
    for (const s of resampled) {
      s.values.forEach((v, i) => {
        if (v === null) return;
        const top = stacked ? (stack[i] += Math.max(v, 0)) : v;
        hi = Math.max(hi, top); lo = Math.min(lo, v);
      });
    }
    if (hi === lo) hi = lo + 1;
    const stepY = niceStep(hi - lo);
    lo = Math.floor(lo / stepY) * stepY; hi = Math.ceil(hi / stepY) * stepY;
    const span = hi - lo;
    const X = (i) => pad + (i / (buckets - 1)) * (W - pad - 6);
    const Y = (v) => 8 + (1 - (v - lo) / span) * (H - 30);
    let svg = `<svg viewBox="0 0 ${W} ${H}" class="chart">`;
    for (let v = lo; v <= hi + stepY / 2; v += stepY) {
      const y = Y(v);
      svg += `<line x1="${pad}" x2="${W}" y1="${y}" y2="${y}" class="grid"/><text x="${pad - 4}" y="${y + 3}" class="ax" text-anchor="end">${Math.abs(v) >= 1000 ? n(v / 1000, 1) + "k" : n(v, span < 10 ? 1 : 0)}</text>`;
    }
    const ticks = hours <= 48 ? 6 : 7;
    for (let t = 0; t <= ticks; t++) {
      const time = new Date(start + (t / ticks) * (end - start));
      const label = hours <= 48 ? time.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }) : time.toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" });
      svg += `<text x="${X((t / ticks) * (buckets - 1))}" y="${H - 6}" class="ax" text-anchor="middle">${label}</text>`;
    }
    if (lo < 0) svg += `<line x1="${pad}" x2="${W}" y1="${Y(0)}" y2="${Y(0)}" class="zero"/>`;
    const base = new Array(buckets).fill(0);
    for (const s of resampled) {
      let path = "", area = "", started = false, first = 0, lastI = 0;
      s.values.forEach((v, i) => {
        if (v === null) return;
        const yv = stacked ? base[i] + Math.max(v, 0) : v;
        const pt = `${X(i).toFixed(1)},${Y(yv).toFixed(1)}`;
        if (!started) { first = i; path += `M${pt}`; started = true; } else path += `L${pt}`;
        lastI = i;
      });
      if (!started) continue;
      if (s.type === "area" || stacked) {
        let back = "";
        for (let i = lastI; i >= first; i--) back += `L${X(i).toFixed(1)},${Y(stacked ? base[i] : Math.max(lo, 0)).toFixed(1)}`;
        area = `<path d="${path}${back}Z" fill="${s.color}" opacity="${stacked ? 0.35 : 0.18}"/>`;
      }
      if (stacked) s.values.forEach((v, i) => { if (v !== null) base[i] += Math.max(v, 0); });
      svg += `${area}<path d="${path}" fill="none" stroke="${s.color}" stroke-width="2" class="glow"/>`;
    }
    svg += `</svg>`;
    const legend = resampled.map((s) => {
      const lastV = [...s.values].reverse().find((v) => v !== null);
      return `<span><i style="background:${s.color}"></i>${esc(s.name)} <b>${lastV === undefined ? "—" : n(lastV, Math.abs(lastV) < 10 ? 1 : 0)}${unit}</b></span>`;
    }).join("");
    return svg + `<div class="legend">${legend}</div>`;
  }

  barChart(labels, series, { height = 200, unit = "", width = 700 } = {}) {
    const W = window.innerWidth < 760 ? 380 : width, H = height, pad = 34;
    const count = labels.length || 1;
    let hi = 0;
    for (const s of series) for (const v of s.values) hi = Math.max(hi, Number(v) || 0);
    if (!hi) hi = 1;
    const stepB = niceStep(hi);
    hi = Math.ceil(hi / stepB) * stepB;
    const slot = (W - pad - 6) / count, bw = (slot * 0.8) / series.length;
    const Y = (v) => 8 + (1 - v / hi) * (H - 30);
    let svg = `<svg viewBox="0 0 ${W} ${H}" class="chart">`;
    for (let v = 0; v <= hi + stepB / 2; v += stepB) { svg += `<line x1="${pad}" x2="${W}" y1="${Y(v)}" y2="${Y(v)}" class="grid"/><text x="${pad - 4}" y="${Y(v) + 3}" class="ax" text-anchor="end">${n(v, hi < 10 ? 1 : 0)}</text>`; }
    series.forEach((s, si) => {
      s.values.forEach((v, i) => {
        const x = pad + i * slot + slot * 0.1 + si * bw;
        const y = Y(Number(v) || 0);
        svg += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(bw - 1, 1).toFixed(1)}" height="${(H - 22 - y).toFixed(1)}" rx="2" fill="${s.color}" opacity=".88"><title>${esc(labels[i])} · ${esc(s.name)}: ${n(v, 2)}${unit}</title></rect>`;
      });
    });
    const every = Math.ceil(count / 8);
    labels.forEach((l, i) => { if (i % every === 0) svg += `<text x="${(pad + i * slot + slot / 2).toFixed(1)}" y="${H - 6}" class="ax" text-anchor="middle">${esc(l)}</text>`; });
    svg += `</svg>`;
    const legend = series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)} <b>${n(s.values.reduce((a, b) => a + (Number(b) || 0), 0), 1)}${unit}</b></span>`).join("");
    return svg + `<div class="legend">${legend}</div>`;
  }

  live(title, defs, opts = {}) {
    const ids = defs.map((d) => d.entity).filter(Boolean);
    const data = this.history(ids, opts.hours || 24);
    const body = data
      ? this.lineChart(defs.map((d) => ({ ...d, points: (data[d.entity] || []).map(([t, v]) => [t, (d.scale || 1) * v]) })), opts)
      : `<div class="loading">Cargando historial…</div>`;
    return `<h3>${esc(title)}</h3>${body}`;
  }

  daily(title, fields, days = 30, width = 700) {
    const rows = (this.ka("historico", "dias") || []).slice(-days);
    if (!rows.length) return `<h3>${esc(title)}</h3>${this.empty("El histórico diario aparece a partir de mañana (o importando el de Home Assistant).")}`;
    const labels = rows.map((r) => r.fecha.slice(8, 10) + "/" + r.fecha.slice(5, 7));
    return `<h3>${esc(title)}</h3>${this.barChart(labels, fields.map(([k, name, color]) => ({ name, color, values: rows.map((r) => r[k] || 0) })), { unit: fields[0][3] || "", width })}`;
  }

  monthly(title, fields, months = 12, width = 700) {
    const rows = (this.ka("historico", "meses") || []).slice(-months);
    if (!rows.length) return "";
    const names = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
    const labels = rows.map((r) => names[Number(r.mes.slice(5, 7)) - 1] + " " + r.mes.slice(2, 4));
    return `<h3>${esc(title)}</h3>${this.barChart(labels, fields.map(([k, name, color]) => ({ name, color, values: rows.map((r) => r[k] || 0) })), { unit: fields[0][3] || "", width })}`;
  }

  // ------------------------------------------------------------------ flow diagram
  flow() {
    const pv = Math.max(this.k("potencia_solar") || 0, 0);
    const grid = this.k("potencia_red") || 0;
    const bat = this.k("potencia_bateria") || 0;
    const load = Math.max(this.k("potencia_consumo") || 0, 0);
    const hasPv = (this._ctx.strings || []).length || this.setting("solar_potencia");
    const hasBat = (this._ctx.batteries || []).length;
    const imp = Math.max(grid, 0), exp = Math.max(-grid, 0), dis = Math.max(bat, 0), chg = Math.max(-bat, 0);
    const s2g = Math.min(pv, exp), s2b = Math.min(pv - s2g, chg), s2h = Math.max(pv - s2g - s2b, 0);
    const g2b = Math.max(chg - s2b, 0), g2h = Math.max(imp - g2b, 0);
    const P = { s: [300, 64], g: [96, 200], b: [504, 200], h: [300, 312] };
    const line = (a, b, v, color, id) => {
      const [x1, y1] = P[a], [x2, y2] = P[b];
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      const d = `M${x1},${y1} Q${mx + (y2 - y1) * 0.12},${my - (x2 - x1) * 0.12} ${x2},${y2}`;
      const on = v > 5;
      const dur = on ? clamp(6 - Math.log10(v + 1) * 1.4, 0.8, 5).toFixed(2) : 0;
      return `<path id="${id}" d="${d}" class="fl ${on ? "on" : ""}" stroke="${color}"/>` +
        (on ? [0, 0.33, 0.66].map((o) => `<circle r="4" fill="${color}" class="dot"><animateMotion dur="${dur}s" begin="-${(o * dur).toFixed(2)}s" repeatCount="indefinite"><mpath href="#${id}"/></animateMotion></circle>`).join("") : "");
    };
    const node = (key, color, icon, label, value, sub, entity) => {
      const [x, y] = P[key];
      return `<g class="node" data-action="more" data-entity="${entity || ""}" style="--c:${color}">
        <circle cx="${x}" cy="${y}" r="44" class="ring"/><circle cx="${x}" cy="${y}" r="38" class="core"/>
        <foreignObject x="${x - 14}" y="${y - 30}" width="28" height="28"><ha-icon icon="${icon}" style="color:${color};--mdc-icon-size:26px"></ha-icon></foreignObject>
        <text x="${x}" y="${y + 10}" class="nv">${value}</text><text x="${x}" y="${y + 25}" class="ns">${sub}</text>
        <text x="${x}" y="${y + 62}" class="nl">${label}</text></g>`;
    };
    let svg = `<svg viewBox="0 0 600 390" class="flow">`;
    if (hasPv) { svg += line("s", "h", s2h, C.amber, "f1"); svg += line("s", "g", s2g, C.amber, "f2"); }
    if (hasPv && hasBat) svg += line("s", "b", s2b, C.amber, "f3");
    svg += line("g", "h", g2h, C.cyan, "f4");
    if (hasBat) { svg += line("b", "h", dis, C.green, "f5"); svg += line("g", "b", g2b, C.cyan, "f6"); }
    if (hasPv) svg += node("s", C.amber, "mdi:solar-power-variant", "Solar", w(pv), `${n(this.k("energia_solar"), 1)} kWh hoy`, this.id("potencia_solar"));
    svg += node("g", C.cyan, "mdi:transmission-tower", grid > 5 ? "Red · importando" : grid < -5 ? "Red · vertiendo" : "Red", w(Math.abs(grid)), `${n(this.k("precio_actual"), 3)} €/kWh`, this.id("potencia_red"));
    if (hasBat) svg += node("b", C.green, "mdi:home-battery", bat < -5 ? "Batería · cargando" : bat > 5 ? "Batería · descargando" : "Batería", w(Math.abs(bat)), `${n(this.k("soc_bateria"), 0)} %`, this.id("potencia_bateria"));
    svg += node("h", C.pink, "mdi:home-lightning-bolt", "Casa", w(load), `${n(this.k("autosuficiencia_ahora"), 0)} % propio`, this.id("potencia_consumo"));
    svg += `</svg>`;
    const circuits = (this.ka("potencia_consumo", "circuitos") || []).filter((c) => c.en_total !== false).slice(0, 6);
    const chips = circuits.map((c, i) => `<span class="pill" style="--c:${PALETTE[i % PALETTE.length]}" data-action="tab" data-tab="consumos"><ha-icon icon="${esc(c.icono)}"></ha-icon>${esc(c.nombre)} <b>${w(c.w)}</b></span>`).join("");
    return svg + (chips ? `<div class="pills">${chips}</div>` : "");
  }

  // ================================================================== views
  v_resumen() {
    const per = this.period();
    const problems = this.ka("problemas", "lista") || [];
    const open = problems.filter((p) => !p.reconocido);
    const crit = open.filter((p) => p.nivel === "critico").length;
    const status = crit ? `<span style="color:${C.red}">◉ ${crit} crítico${crit > 1 ? "s" : ""}</span>` : open.length ? `<span style="color:${C.amber}">◉ ${open.length} aviso${open.length > 1 ? "s" : ""}</span>` : `<span style="color:${C.green}">◉ Todo en orden</span>`;
    const grid = this.k("potencia_red") || 0, bat = this.k("potencia_bateria") || 0;
    const kpis = [
      this.kpi(this.id("potencia_solar"), w(this.k("potencia_solar")), `Solar · ${n(this.k("energia_solar"), 1)} kWh hoy`, "mdi:solar-power-variant", C.amber, "solar"),
      this.kpi(this.id("potencia_consumo"), w(this.k("potencia_consumo")), `Consumo · ${n(this.k("energia_consumo"), 1)} kWh hoy`, "mdi:home-lightning-bolt", C.pink, "consumos"),
      this.kpi(this.id("potencia_red"), `${w(Math.abs(grid))} ${grid > 5 ? "↓" : grid < -5 ? "↑" : ""}`, grid > 5 ? "Importando de la red" : grid < -5 ? "Vertiendo a la red" : "Red en reposo", "mdi:transmission-tower", C.cyan, "red"),
      (this._ctx.batteries || []).length ? this.kpi(this.id("soc_bateria"), `${n(this.k("soc_bateria"), 0)} %`, `Batería · ${bat > 30 ? "descarga " + w(bat) : bat < -30 ? "carga " + w(-bat) : "en reposo"}`, "mdi:battery-charging-high", C.green, "bateria") : "",
      this.kpi(this.id("autosuficiencia_ahora"), `${n(this.k("autosuficiencia_ahora"), 0)} %`, `Autosuficiencia · hoy ${n(this.k("autosuficiencia"), 0)} %`, "mdi:shield-sun", C.lime, "co2"),
      this.kpi(this.id("coste_energia"), `${n(this.k("coste_energia"), 2)} €`, `Coste hoy · ahorro solar ${n(this.ka("ahorro_solar", "hoy"), 2)} €`, "mdi:currency-eur", C.gold, "coste"),
    ].join("");
    const at = (key) => this.ka(key, per);
    const co2 = (this.ka("co2_evitado", per) || {}).evitado_kg;
    const summary = this.table([
      [`<span style="color:${C.amber}">☀ Producción</span>`, `<b>${n(at("energia_solar"), 2)} kWh</b>`],
      [`<span style="color:${C.pink}">⌂ Consumo</span>`, `<b>${n(at("energia_consumo"), 2)} kWh</b>`],
      [`<span style="color:${C.cyan}">↓ Importado</span>`, `${n(at("energia_importada"), 2)} kWh`],
      [`<span style="color:${C.cyan}">↑ Vertido</span>`, `${n(at("energia_exportada"), 2)} kWh`],
      [`<span style="color:${C.gold}">€ Coste energía</span>`, `${n(at("coste_energia"), 2)} €`],
      [`<span style="color:${C.gold}">€ Ahorro solar</span>`, `${n(at("ahorro_solar"), 2)} €`],
      [`<span style="color:${C.lime}">♻ CO₂ evitado</span>`, `${n(co2, 1)} kg`],
    ]);
    const chart = [
      { entity: this.id("potencia_solar"), name: "Solar", color: C.amber, type: "area" },
      { entity: this.id("potencia_consumo"), name: "Consumo", color: C.pink },
      { entity: this.id("potencia_red"), name: "Red", color: C.cyan },
    ];
    if ((this._ctx.batteries || []).length) chart.push({ entity: this.id("potencia_bateria"), name: "Batería", color: C.green });
    return `<div class="grid">
      ${this.card(`<div class="hero"><div><h1>${esc((this._ctx.title || "").toUpperCase())}</h1><p>Periodo ${esc(this.val(this.id("periodo_tarifario")) || "—")} · ${n(this.k("precio_actual"), 4)} €/kWh · ${status}</p></div></div>${this.flow()}`, C.cyan, 2, "tall")}
      <div class="stack" style="--span:1"><div class="kpis">${kpis}</div>
        ${this.card(`<h3>${PERIODS[per]}</h3>${this.periodChips()}${summary}`, C.cyan)}</div>
      ${this.card(`<h3 data-action="tab" data-tab="problemas" class="link">Alertas</h3>${open.length ? open.slice(0, 4).map((p) => this.alert(p)).join("") + (open.length > 4 ? `<p class="muted">… y ${open.length - 4} más</p>` : "") : `<div class="ok"><ha-icon icon="mdi:check-circle-outline"></ha-icon>Sin problemas detectados</div>`}`, open.length ? (crit ? C.red : C.amber) : C.green)}
      ${this.card(this.live("Últimas 24 h (W)", chart, { unit: " W" }), C.cyan, 2)}
      ${this.card(this.daily("Últimos 30 días (kWh)", [["solar", "Solar", C.amber, " kWh"], ["consumo", "Consumo", C.pink], ["importada", "De la red", C.cyan]]), C.cyan, 2)}
      </div>`;
  }

  v_red() {
    const per = this.period();
    const price = this.setting("precio_modo") === "sensor" ? this.setting("precio_sensor") : null;
    let priceChart = "";
    if (price) {
      const a = (this.st(price) || {}).attributes || {};
      const labels = [], today = [], tomorrow = [];
      for (let h = 0; h < 24; h++) {
        const k = String(h).padStart(2, "0");
        labels.push(`${k}h`); today.push(a[`price_${k}h`] ?? null); tomorrow.push(a[`price_next_day_${k}h`] ?? null);
      }
      if (today.some((v) => v !== null)) {
        const series = [{ name: "Hoy", color: C.gold, values: today.map((v) => v || 0) }];
        if (tomorrow.some((v) => v !== null)) series.push({ name: "Mañana", color: C.orange, values: tomorrow.map((v) => v || 0) });
        priceChart = this.card(`<h3>Precio por horas (€/kWh)</h3>${this.barChart(labels, series, { unit: " €" })}`, C.gold, 2);
      }
    }
    const extra = [["red_tension", "Tensión", "mdi:sine-wave", "V", 1], ["red_frecuencia", "Frecuencia", "mdi:waveform", "Hz", 2]]
      .filter(([k]) => this.setting(k)).map(([k, l, i, u, d]) => this.kpi(this.setting(k), `${n(this.num(this.setting(k)), d)} ${u}`, l, i, C.cyan)).join("");
    return `<div class="grid">
      ${this.card(`${this.head("Red eléctrica", "mdi:transmission-tower", C.cyan, "Importación, vertido y potencia contratada")}
        <div class="row">${this.gauge(this.k("uso_potencia_contratada"), 0, 110, C.cyan, `de ${n(this.ka("uso_potencia_contratada", "contratada_kw"), 2)} kW contratados`, "%", this.id("uso_potencia_contratada"))}</div>
        <div class="kpis">${this.kpi(this.id("potencia_importada"), w(this.k("potencia_importada")), "Importando", "mdi:transmission-tower-import", C.cyan)}
        ${this.kpi(this.id("potencia_exportada"), w(this.k("potencia_exportada")), "Vertiendo", "mdi:transmission-tower-export", C.lime)}
        ${this.kpi(this.id("precio_actual"), `${n(this.k("precio_actual"), 4)} €`, `Precio · periodo ${esc(this.val(this.id("periodo_tarifario")) || "—")}`, "mdi:cash-clock", C.gold)}
        ${this.kpi(this.id("precio_excedentes"), `${n(this.k("precio_excedentes"), 4)} €`, "Precio excedentes", "mdi:cash-plus", C.lime)}${extra}</div>`, C.cyan)}
      ${this.card(`<h3>${PERIODS[per]}</h3>${this.periodChips()}${this.table([
        ["Energía", `<b>${n(this.ka("energia_importada", per), 2)} kWh</b>`, `<b>${n(this.ka("energia_exportada", per), 2)} kWh</b>`],
        ["Importe", `${n(this.ka("coste_energia", per), 2)} €`, `${n(this.ka("compensacion_excedentes", per), 2)} €`]], ["", "Importado", "Vertido"])}`, C.cyan)}
      ${this.card(this.live("Red 24 h (W)", [{ entity: this.id("potencia_importada"), name: "Importado", color: C.cyan, type: "area" }, { entity: this.id("potencia_exportada"), name: "Vertido", color: C.lime, type: "area" }], { unit: " W" }), C.cyan, 2)}
      ${priceChart}
      ${this.card(this.daily("Últimos 30 días (kWh)", [["importada", "Importado", C.cyan, " kWh"], ["exportada", "Vertido", C.lime]]), C.cyan, 2)}
    </div>`;
  }

  v_solar() {
    const strings = this._ctx.strings || [];
    if (!strings.length && !this.setting("solar_potencia")) return `<div class="grid">${this.card(this.empty("Añade la potencia solar en Configurar → Solar, o cada string con «Añadir string»."), C.amber, 4)}</div>`;
    const peak = Number(this.setting("solar_pico_wp")) || strings.reduce((a, s) => a + (Number(s.peak_wp) || 0), 0) || 5000;
    const fc = this.setting("solar_prevision_hoy");
    const live = this.ka("potencia_solar", "strings") || [];
    const maxY = Math.max(1, ...live.map((s) => (s.wp && s.w ? (1000 * s.w) / s.wp : 0)));
    const stringCards = strings.map((s, i) => {
      const l = live.find((x) => x.id === s.id) || {};
      const yieldKw = l.wp ? (1000 * (l.w || 0)) / l.wp : null;
      return `<div class="string" data-action="more" data-entity="${s.power}" style="--c:${[C.amber, C.orange, C.gold, C.lime][i % 4]}">
        <div class="sn"><ha-icon icon="mdi:solar-panel"></ha-icon><b>${esc(s.name)}</b><small>${esc(l.grupo || "")}</small></div>
        <div class="sv">${w(l.w)}</div>
        <div class="muted">${l.v !== null && l.v !== undefined ? n(l.v, 0) + " V · " : ""}${l.a !== null && l.a !== undefined ? n(l.a, 1) + " A · " : ""}${n(l.kwh_hoy, 2)} kWh hoy</div>
        ${l.wp ? `${this.bar(l.w, l.wp, "var(--c)")}<div class="muted">${n(l.pct, 0)} % de ${n(l.wp, 0)} Wp · ${n(yieldKw, 0)} W/kWp</div>` : ""}
        ${strings.length > 1 && yieldKw !== null ? `<div class="cmp">${this.bar(yieldKw, maxY, "var(--c)")}</div>` : ""}</div>`;
    }).join("");
    const inv = [["inversor_temperatura", "Inversor", "mdi:thermometer"], ["inversor_temperatura_dc", "Inversor DC", "mdi:thermometer-high"]]
      .filter(([k]) => this.setting(k)).map(([k, l, i]) => this.kpi(this.setting(k), `${n(this.num(this.setting(k)), 1)} °C`, l, i, C.orange)).join("")
      + [["inversor_estado", "Estado"], ["inversor_fallo", "Fallo"], ["inversor_alarma", "Alarma"]]
        .filter(([k]) => this.setting(k)).map(([k, l]) => this.kpi(this.setting(k), esc(this.val(this.setting(k)) ?? "—"), l, "mdi:information-outline", C.orange)).join("");
    return `<div class="grid">
      ${this.card(`${this.head("Paneles solares", "mdi:solar-power-variant", C.amber, `${n(peak, 0)} Wp instalados`)}
        <div class="row">${this.gauge(this.k("potencia_solar"), 0, peak, C.amber, "Producción ahora", "W", this.id("potencia_solar"))}</div>
        <div class="kpis">${this.kpi(this.id("energia_solar"), `${n(this.k("energia_solar"), 2)} kWh`, `Hoy · mes ${n(this.ka("energia_solar", "mes"), 0)} kWh`, "mdi:solar-power-variant-outline", C.amber)}
        ${this.kpi(this.id("potencia_solar"), `${n(this.ka("potencia_solar", "rendimiento_pct"), 0)} %`, "Rendimiento sobre el pico", "mdi:speedometer", C.amber)}
        ${this.kpi(this.id("autoconsumo"), `${n(this.k("autoconsumo"), 0)} %`, `Autoconsumo hoy · mes ${n(this.ka("autoconsumo", "mes"), 0)} %`, "mdi:home-import-outline", C.lime)}
        ${fc ? this.kpi(fc, `${n(this.num(fc), 1)} kWh`, `Previsión hoy · llevas ${n((100 * (this.k("energia_solar") || 0)) / Math.max(this.num(fc) || 0.01, 0.01), 0)} %`, "mdi:weather-sunny-alert", C.amber) : ""}</div>`, C.amber)}
      ${this.card(`<h3>Strings</h3>${stringCards ? `<div class="strings">${stringCards}</div>` : this.empty("Sin strings: añádelos con «Añadir string».")}${inv ? `<h3>Inversor</h3><div class="kpis">${inv}</div>` : ""}`, C.amber)}
      ${strings.length ? this.card(this.live("Strings 24 h (W)", strings.map((s, i) => ({ entity: s.power, name: s.name, color: [C.amber, C.orange, C.gold, C.lime, C.pink, C.cyan][i % 6] })), { unit: " W" }), C.amber, 2) : ""}
      ${this.card(this.daily("Producción 30 días (kWh)", [["solar", "Solar", C.amber, " kWh"]]), C.amber, 2)}
      ${this.card(this.monthly("Producción por meses (kWh)", [["solar", "Solar", C.amber, " kWh"]]), C.amber, 2)}
    </div>`;
  }

  v_bateria() {
    const bats = this._ctx.batteries || [];
    if (!bats.length) return `<div class="grid">${this.card(this.empty("Añade tus baterías en la integración → «Añadir batería»."), C.green, 4)}</div>`;
    const b = this.k("potencia_bateria") || 0;
    const h = this.k("autonomia_bateria");
    const per = bats.map((bt) => {
      const sign = bt.positive_charge ? -1 : 1;
      const pw = sign * (this.num(bt.power) || 0);
      const cells = (bt.cells || []).map((c) => this.num(c)).filter((v) => v !== null && v > 1);
      let cellHtml = "";
      if (cells.length) {
        const lo = Math.min(...cells), hi = Math.max(...cells);
        const span = Math.max(hi - lo, 0.005) + 0.02;
        cellHtml = `<h3>Celdas · Δ ${n((hi - lo) * 1000, 0)} mV</h3><div class="cells">${cells.map((v, i) => {
          const color = v < 3.0 || v > 3.6 ? C.red : v < 3.2 || v > 3.45 ? C.amber : C.green;
          const mark = v === lo ? " ▼" : v === hi ? " ▲" : "";
          return `<div class="cell" data-action="more" data-entity="${bt.cells[i]}"><span>${String(i + 1).padStart(2, "0")}</span>${this.bar(v - lo + 0.01, span, color)}<b style="color:${color}">${n(v, 3)} V${mark}</b></div>`;
        }).join("")}</div>`;
      }
      const extra = [["voltage", "Tensión", "mdi:sine-wave", "V", 2], ["current", "Corriente", "mdi:current-dc", "A", 1], ["cycles", "Ciclos", "mdi:autorenew", "", 0]]
        .filter(([k]) => bt[k]).map(([k, l, i, u, d]) => this.kpi(bt[k], `${n(this.num(bt[k]), d)} ${u}`, l, i, C.green)).join("")
        + (bt.temperatures || []).map((t) => this.kpi(t, `${n(this.num(t), 1)} °C`, esc(this.name(t)), "mdi:thermometer", C.orange)).join("");
      return this.card(`${this.head(bt.name, "mdi:battery-outline", C.green)}<div class="row">${this.gauge(this.num(bt.soc), 0, 100, C.green, "SOC", "%", bt.soc)}</div>
        <div class="kpis">${this.kpi(bt.power, w(Math.abs(pw)), pw > 30 ? "Descargando" : pw < -30 ? "Cargando" : "En reposo", "mdi:flash", C.green)}${extra}</div>${cellHtml}`, C.green);
    }).join("");
    return `<div class="grid">
      ${this.card(`${this.head("Baterías", "mdi:home-battery", C.green, `${n(this.ka("potencia_bateria", "capacidad_kwh"), 0)} kWh en total`)}
        <div class="row">${this.gauge(this.k("soc_bateria"), 0, 100, C.green, "Carga total", "%", this.id("soc_bateria"))}</div>
        <div class="kpis">${this.kpi(this.id("potencia_bateria"), w(Math.abs(b)), b > 30 ? "Descargando" : b < -30 ? "Cargando" : "En reposo", "mdi:battery-sync", C.green)}
        ${this.kpi(this.id("energia_almacenada"), `${n(this.k("energia_almacenada"), 1)} kWh`, "Almacenado", "mdi:battery-high", C.green)}
        ${this.kpi(this.id("autonomia_bateria"), h === null ? "—" : `${n(h, 1)} h`, "Autonomía con el consumo actual", "mdi:timer-sand", C.green)}
        ${this.kpi(this.id("energia_bateria_carga"), `↓${n(this.k("energia_bateria_carga"), 1)} ↑${n(this.k("energia_bateria_descarga"), 1)}`, "kWh cargados · descargados hoy", "mdi:swap-vertical-bold", C.green)}</div>`, C.green)}
      ${per}
      ${this.card(this.live("Batería 24 h", [{ entity: this.id("soc_bateria"), name: "SOC", color: C.green }], { unit: " %" }), C.green, 2)}
      ${this.card(this.live("Potencia de batería 24 h (W, + descarga)", [{ entity: this.id("potencia_bateria"), name: "Potencia", color: C.lime, type: "area" }], { unit: " W" }), C.green, 2)}
    </div>`;
  }

  v_consumos() {
    const per = this.period();
    const cs = this.ka("potencia_consumo", "circuitos") || [];
    const top = Math.max(1, ...cs.map((c) => c.w || 0));
    const rank = cs.map((c) => `<div class="rank" data-action="more" data-entity="${esc((this._ctx.circuits || []).find((x) => x.id === c.id)?.power || "")}">
      <ha-icon icon="${esc(c.icono)}"></ha-icon><div><b>${esc(c.nombre)}</b>${c.padre ? ` <small>⤷ ${esc(c.padre)}</small>` : ""}${this.bar(c.w, top, C.pink)}</div>
      <span><b>${w(c.w)}</b><small>${n(c.pct, 0)} % · ${n(c.periodo_kwh, 2)} kWh</small></span></div>`).join("");
    const groups = {};
    for (const c of this._ctx.circuits || []) (groups[c.group] = groups[c.group] || []).push(c);
    const groupCards = Object.entries(groups).map(([g, items]) => this.card(`<h3>${esc(g)}</h3><div class="kpis">${items.map((c) => {
      const e = this.id(`${c.id}:energia_circuito`);
      return this.kpi(c.power, w(this.num(c.power)), `${esc(c.name)} · ${n(this.num(e), 2)} kWh hoy · ${n(this.attr(e, per), 1)} kWh ${PERIODS[per].toLowerCase()}`, c.icon, C.pink);
    }).join("")}</div>`, C.pink)).join("");
    const circ = (this._ctx.circuits || []).filter((c) => c.in_total);
    return `<div class="grid">
      ${this.card(`${this.head("Consumos", "mdi:home-lightning-bolt", C.pink, "Total y cada circuito por separado")}
        <div class="kpis">${this.kpi(this.id("potencia_consumo"), w(this.k("potencia_consumo")), `Consumo total · ${n(this.k("energia_consumo"), 2)} kWh hoy`, "mdi:home-lightning-bolt", C.pink)}
        ${this.kpi(this.id("potencia_no_medida"), w(this.k("potencia_no_medida")), "Sin medir por ningún circuito", "mdi:help-circle-outline", C.violet)}</div>
        <h3>${PERIODS[per]}</h3>${this.periodChips(C.pink)}${this.table([["Consumido", `<b>${n(this.ka("energia_consumo", per), 2)} kWh</b>`], ["De la red", `${n(this.ka("energia_importada", per), 2)} kWh`], ["Autosuficiencia", `${n((this.ka("autosuficiencia", per)), 0)} %`]])}`, C.pink)}
      ${this.card(`<h3>Ahora mismo</h3>${rank || this.empty("Añade cada circuito o aparato con «Añadir circuito».")}${cs.length ? `<p class="muted">◌ Sin medir: ${w(this.ka("potencia_consumo", "no_medido_w"))}</p>` : ""}`, C.pink)}
      ${circ.length ? this.card(this.live("Circuitos 24 h (W, apilado)", circ.map((c, i) => ({ entity: c.power, name: c.name, color: PALETTE[i % PALETTE.length] })), { stacked: true, unit: " W", height: 260 }), C.pink, 2) : ""}
      ${groupCards}
      ${this.card(this.daily("Consumo 30 días (kWh)", [["consumo", "Consumo", C.pink, " kWh"], ["importada", "De la red", C.cyan]]), C.pink, 2)}
    </div>`;
  }

  v_problemas() {
    const ps = this.ka("problemas", "lista") || [];
    const count = (lv) => ps.filter((p) => p.nivel === lv).length;
    const byArea = {};
    for (const p of ps) (byArea[p.area] = byArea[p.area] || []).push(p);
    const order = { critico: 0, aviso: 1, info: 2 };
    const list = Object.entries(byArea).sort((a, b) => Math.min(...a[1].map((p) => order[p.nivel])) - Math.min(...b[1].map((p) => order[p.nivel])))
      .map(([area, items]) => `<h3>${esc(area)}</h3>${items.sort((a, b) => order[a.nivel] - order[b.nivel]).map((p) => this.alert(p)).join("")}`).join("");
    const sources = this._sources().map(([label, e]) => {
      const s = this.val(e);
      const bad = s === undefined || s === "unavailable" || s === "unknown";
      return [esc(label), `<span data-action="more" data-entity="${e}" style="color:${bad ? C.red : C.green}">●</span> ${bad ? `<span style="color:${C.red}">${esc(s ?? "no existe")}</span>` : `${esc(s)} ${esc(this.attr(e, "unit_of_measurement") || "")}`}`];
    });
    return `<div class="grid">
      ${this.card(`${this.head("Diagnóstico", "mdi:alert-decagram", C.red, "Se revisa cada 30 s; un problema solo aparece si dura lo bastante")}
        <div class="counts"><div style="--c:${C.red}"><b>${count("critico")}</b>Críticos</div><div style="--c:${C.amber}"><b>${count("aviso")}</b>Avisos</div><div style="--c:${C.blue}"><b>${count("info")}</b>Info</div></div>
        <div class="btns">${this.btn(this.id("reconocer_problemas"), "Reconocer todo", "mdi:check-all", C.green)}${this.btn(this.id("importar_historico"), "Importar histórico", "mdi:database-import", C.cyan, "¿Rellenar el histórico con las estadísticas de Home Assistant?")}</div>`, C.red)}
      ${this.card(list || `<div class="ok"><ha-icon icon="mdi:check-circle-outline"></ha-icon>Todo en orden: no se ha detectado ningún problema.</div>`, ps.length ? C.red : C.green, 2)}
      ${this.card(`<h3>Estado de las fuentes</h3>${sources.length ? this.table(sources) : this.empty("Sin fuentes configuradas.")}`, C.cyan)}
    </div>`;
  }

  _sources() {
    const out = [];
    for (const [k, l] of [["red_potencia", "Red"], ["consumo_potencia", "Consumo total"], ["solar_potencia", "Solar"], ["red_tension", "Tensión de red"], ["inversor_temperatura", "Temp. inversor"], ["precio_sensor", "Precio"]]) if (this.setting(k)) out.push([l, this.setting(k)]);
    for (const s of this._ctx.strings || []) out.push([s.name, s.power]);
    for (const b of this._ctx.batteries || []) { out.push([`${b.name} · SOC`, b.soc]); out.push([`${b.name} · potencia`, b.power]); }
    for (const c of this._ctx.circuits || []) out.push([c.name, c.power]);
    for (const z of this._ctx.zones || []) out.push([z.name, z.valve]);
    return out;
  }

  bill(key, title, icon) {
    const f = this.st(this.id(key));
    const a = (f && f.attributes) || {};
    if (!a.lineas) return `<h3>${title}</h3><p class="muted">Calculando…</p>`;
    const d = (s) => (s ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : "—");
    return `<h3><ha-icon icon="${icon}"></ha-icon> ${title}</h3><p class="muted">${d(a.desde)} – ${d(a.hasta)} · ${a.dias} días · ${n(a.importada_kwh, 1)} kWh</p>
      ${this.table([...a.lineas.map((l) => [esc(l.concepto), `<small>${esc(l.calculo)}</small>`, `${n(l.importe, 2)} €`]),
        ["<b>Base imponible</b>", "", `<b>${n(a.base_imponible, 2)} €</b>`], ["IVA", `${n(a.iva_porcentaje, 0)} %`, `${n(a.iva, 2)} €`],
        [`<b style="color:${C.gold}">TOTAL</b>`, "", `<b class="big" style="color:${C.gold}">${n(a.total, 2)} €</b>`]])}
      ${Number(a.compensacion_perdida) > 0 ? `<p style="color:${C.amber}">⚠ ${n(a.compensacion_perdida, 2)} € de excedentes no se compensan (superan la energía del periodo).</p>` : ""}`;
  }

  v_coste() {
    const nx = this.ka("prevision_factura", "proximas") || [];
    const months = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
    const sim = this.st(this.id("simulacion_factura"));
    const sa = (sim && sim.attributes) || {};
    const s = sa.simulada || {}, b = sa.base || {}, diff = Number(sa.diferencia) || 0;
    const sliders = [["sim_potencia_p1", "Potencia punta (−1 = la actual)"], ["sim_potencia_p2", "Potencia valle (−1 = la actual)"], ["sim_consumo", "Cambio de consumo"], ["sim_precio", "Cambio del precio"], ["sim_paneles", "Paneles extra"], ["sim_bateria", "Batería extra"], ["sim_excedentes", "Precio excedentes (−1 = el actual)"]]
      .map(([k, l]) => this.slider(this.id(k), l, C.violet)).join("");
    const sav = (k) => n(this.ka("ahorro_solar", k), 2);
    return `<div class="grid">
      ${this.card(this.bill("factura_actual", "Factura en curso (hasta hoy)", "mdi:receipt-text-clock"), C.gold)}
      ${this.card(this.bill("prevision_factura", "Previsión al cierre del periodo", "mdi:crystal-ball"), C.gold)}
      ${this.card(`<h3><ha-icon icon="mdi:calendar-arrow-right"></ha-icon> Próximas facturas</h3>${nx.length ? this.table(nx.map((m) => [`${months[Number(m.mes.slice(5, 7)) - 1]} ${m.mes.slice(0, 4)} <small>${m.fuente === "año_anterior" ? "año pasado" : "modelo"}</small>`, `${n(m.consumo_kwh, 0)} kWh`, `${n(m.importada_kwh, 0)} kWh`, `<b style="color:${C.gold}">${n(m.total, 2)} €</b>`]), ["Mes", "Consumo", "De la red", "Total"]) + this.barChart(nx.map((m) => months[Number(m.mes.slice(5, 7)) - 1]), [{ name: "Factura", color: C.gold, values: nx.map((m) => m.total) }], { unit: " €", height: 150, width: 340 }) : `<p class="muted">Calculando…</p>`}
        <p class="muted">«modelo»: tu media de los últimos 30 días con la estacionalidad solar · «año pasado»: el mismo periodo del año anterior.</p>`, C.gold)}
      ${this.card(`<h3><ha-icon icon="mdi:flask-outline"></ha-icon> Simulador «¿y si…?»</h3>${sliders}
        ${this.table([["Potencia", `${n(b.potencia, 2)} €`, `${n(s.potencia, 2)} €`], ["Energía", `${n(b.energia, 2)} €`, `${n(s.energia, 2)} €`], ["Compensación", `−${n(b.compensacion, 2)} €`, `−${n(s.compensacion, 2)} €`], ["<b>Total</b>", `<b>${n(b.total, 2)} €</b>`, `<b>${n(s.total, 2)} €</b>`]], [`Próxima factura`, "Actual", "Simulada"])}
        <p class="big" style="color:${diff < 0 ? C.green : diff > 0 ? C.red : C.muted}">${diff < 0 ? "▼ Ahorras" : diff > 0 ? "▲ Pagas" : "="} ${n(Math.abs(diff), 2)} €/mes · ${n(Math.abs(Number(sa.diferencia_anual) || 0), 0)} €/año</p>`, C.violet)}
      ${this.card(`<h3><ha-icon icon="mdi:piggy-bank-outline"></ha-icon> Lo que te ahorra el sol</h3>${this.table([[`${sav("hoy")} €`, `${sav("mes")} €`, `<b>${sav("ano")} €</b>`, `${sav("total")} €`]], ["Hoy", "Mes", "Año", "Total"])}`, C.lime, 2)}
      ${this.card(this.daily("Coste diario 30 días (€)", [["coste", "Energía", C.gold, " €"], ["compensacion", "Compensación", C.lime]]), C.gold, 2)}
      ${this.card(this.monthly("Por meses (€)", [["coste_energia", "Energía", C.gold, " €"], ["compensacion", "Compensación", C.lime]], 12, 1400), C.gold, 4)}
    </div>`;
  }

  v_co2() {
    const t = this.ka("co2_evitado", "total") || {};
    const kg = Number(t.evitado_kg) || 0;
    const big = kg >= 1000 ? `${n(kg / 1000, 2)} t` : `${n(kg, 1)} kg`;
    const row = (k, label, color) => [`<span style="color:${color}">${label}</span>`, ...["hoy", "mes", "ano", "total"].map((p) => n((this.ka("co2_evitado", p) || {})[k], p === "hoy" || p === "mes" ? 1 : 0))];
    const aut = (p) => Number(this.ka("autosuficiencia", p)) || 0;
    return `<div class="grid">
      ${this.card(`<div class="co2hero"><p>CO₂ EVITADO DESDE QUE MIDES</p><h1>${big}</h1>
        <div class="eq"><span><ha-icon icon="mdi:tree"></ha-icon><b>${n(t.arboles, 1)}</b> árboles absorbiendo un año</span><span><ha-icon icon="mdi:car"></ha-icon><b>${n(t.km_coche, 0)}</b> km en coche</span></div></div>`, C.lime, 2)}
      ${this.card(`<h3>Independencia energética</h3><div class="row">${this.gauge(aut("hoy"), 0, 100, C.lime, "Autosuficiencia hoy", "%", this.id("autosuficiencia"))}${this.gauge(this.k("autoconsumo"), 0, 100, C.lime, "Autoconsumo hoy", "%", this.id("autoconsumo"))}</div>
        <div class="bars"><span>Este mes</span>${this.bar(aut("mes"), 100, C.lime)}<b>${n(aut("mes"), 0)} %</b><span>Este año</span>${this.bar(aut("ano"), 100, C.lime)}<b>${n(aut("ano"), 0)} %</b></div>`, C.lime, 2)}
      ${this.card(`<h3>Balance de carbono (kg CO₂)</h3>${this.table([row("evitado_kg", "Evitado (solar)", C.lime), row("red_kg", "Red eléctrica", C.cyan), row("gas_kg", "Gas", C.violet), row("neto_kg", "<b>Huella neta</b>", C.text)], ["", "Hoy", "Mes", "Año", "Total"])}
        <p class="muted">Red: ${n(this.ka("co2_evitado", "factor_red_kg_kwh"), 3)} kg CO₂/kWh. Se cambia en Configurar → CO₂.</p>`, C.lime, 2)}
      ${this.card(this.monthly("CO₂ por meses (kg)", [["co2_evitado", "Evitado", C.lime, " kg"], ["co2_red", "Red", C.cyan], ["co2_gas", "Gas", C.violet]]) || this.empty("Aparecerá con el histórico."), C.lime, 2)}
    </div>`;
  }

  v_gas() {
    const g = this._ctx.gas || {};
    if (!Object.keys(g).length) return `<div class="grid">${this.card(this.empty("Instala Gas TUR (se detecta solo) o indica tus sensores en Configurar → Gas."), C.violet, 4)}</div>`;
    const k = (key, fmt, label, icon, span = "") => (g[key] ? this.kpi(g[key], fmt(this.num(g[key])), label, icon, C.violet) : "");
    const gk = this.ka("consumo_gas", "kwh") || {};
    return `<div class="grid">
      ${this.card(`${this.head("Gas", "mdi:fire", C.violet, "Consumo y coste")}<div class="kpis">
        ${k("coste_hoy", (v) => `${n(v, 2)} €`, "Gasto de hoy", "mdi:fire")}
        ${k("coste_mes", (v) => `${n(v, 2)} €`, "Este mes", "mdi:calendar-month")}
        ${this.kpi(this.id("consumo_gas"), `${n(this.k("consumo_gas"), 2)} m³`, `Hoy · ${n(gk.hoy, 1)} kWh`, "mdi:meter-gas", C.violet)}
        ${k("caudal", (v) => `${n(v, 3)} m³/h`, "Caudal ahora", "mdi:gauge")}
        ${k("precio_kwh", (v) => `${n(v, 5)} €`, "Precio por kWh", "mdi:cash")}
        ${k("factura", (v) => `${n(v, 2)} €`, "Factura en curso", "mdi:receipt-text")}
        ${k("prevision_factura", (v) => `${n(v, 2)} €`, "Previsión de la factura", "mdi:crystal-ball")}</div>
        ${g.lectura && g.factor_conversion ? `<p><a class="link" href="/gas-tur">Abrir el panel de Gas TUR →</a></p>` : ""}`, C.violet)}
      ${g.caudal ? this.card(this.live("Caudal 24 h (m³/h)", [{ entity: g.caudal, name: "Caudal", color: C.violet, type: "area" }], { unit: " m³/h", width: 340, height: 260 }), C.violet) : ""}
      ${this.card(this.daily("Gas 30 días (m³)", [["gas_m3", "Gas", C.violet, " m³"]]), C.violet, 2)}
      ${this.card(this.monthly("Gas por meses (m³)", [["gas_m3", "Gas", C.violet, " m³"]]), C.violet, 2)}
    </div>`;
  }

  v_luces() {
    const lights = this._ctx.lights || [];
    const tile = (l) => {
      const s = this.st(l.entity);
      const on = s && s.state === "on";
      const off = !s || s.state === "unavailable";
      const pct = on && s.attributes.brightness ? Math.round((s.attributes.brightness / 255) * 100) : 0;
      return `<div class="light ${on ? "on" : ""} ${off ? "off" : ""}" style="--c:${C.gold}">
        <button class="lamp" data-action="toggle" data-entity="${l.entity}"><ha-icon icon="${on ? "mdi:lightbulb-on" : "mdi:lightbulb-outline"}"></ha-icon></button>
        <div data-action="more" data-entity="${l.entity}"><b>${esc(l.name)}</b><small>${off ? "Sin conexión" : on ? (pct ? `${pct} %` : "Encendida") : "Apagada"}</small></div>
        ${l.dimmable && !off ? `<input type="range" min="1" max="100" value="${pct || 50}" data-action="bright" data-entity="${l.entity}">` : ""}</div>`;
    };
    const inside = lights.filter((l) => !l.outdoor), outside = lights.filter((l) => l.outdoor);
    const onList = this.ka("luces_encendidas", "encendidas") || [];
    return `<div class="grid">
      ${this.card(`${this.head("Iluminación", "mdi:lightbulb-group", C.gold, "Todas las luces de la casa")}
        <div class="kpis">${this.kpi(this.id("luces_encendidas"), `${this.k("luces_encendidas") ?? 0} / ${this.ka("luces_encendidas", "total") ?? lights.length}`, `Encendidas · ${this.ka("luces_encendidas", "interior") ?? 0} dentro · ${this.ka("luces_encendidas", "exterior") ?? 0} fuera`, "mdi:lightbulb-group", C.gold)}
        ${this.kpi(this.id("luces_encendidas"), `${this.ka("luces_encendidas", "sin_conexion") ?? 0}`, "Sin conexión", "mdi:lan-disconnect", C.red)}</div>
        <div class="btns">${this.btn(this.id("apagar_luces"), "Apagar todas", "mdi:lightbulb-group-off", C.gold, "¿Apagar todas las luces?")}</div>
        <h3>Encendidas ahora</h3>${onList.length ? onList.map((l) => `<span class="pill" style="--c:${C.gold}">${esc(l.nombre)}</span>`).join("") : `<p class="muted">Todas apagadas</p>`}`, C.gold)}
      ${inside.length ? this.card(`<h3>Interior</h3><div class="lights">${inside.map(tile).join("")}</div>`, C.gold, outside.length ? 2 : 3) : ""}
      ${outside.length ? this.card(`<h3>Exterior</h3><div class="lights">${outside.map(tile).join("")}</div>`, C.gold) : ""}
      ${lights.length ? "" : this.card(this.empty("No hay luces. Si las añades a Home Assistant, pulsa «Regenerar panel»."), C.gold, 3)}
    </div>`;
  }

  v_clima() {
    const temps = this._ctx.temperatures || [];
    const out = this.setting("temperatura_exterior");
    const outT = out ? (out.startsWith("weather.") ? this.attr(out, "temperature") : this.num(out)) : null;
    const vals = temps.map((e) => [e, this.num(e)]).filter(([, v]) => v !== null).sort((a, b) => b[1] - a[1]);
    const color = (v) => (v >= 28 ? C.red : v >= 24 ? C.orange : v >= 19 ? C.green : v >= 14 ? C.blue : C.violet);
    const heat = vals.map(([e, v]) => `<div class="heat" data-action="more" data-entity="${e}">${this.bar(v - 5, 30, color(v))}<b style="color:${color(v)}">${n(v, 1)} °C</b><span>${esc(this.name(e))}</span></div>`).join("");
    const climates = (this._ctx.climates || []).map((e) => {
      const s = this.st(e);
      if (!s) return "";
      const a = s.attributes;
      const action = a.hvac_action || s.state;
      const col = action === "heating" ? C.orange : action === "cooling" ? C.blue : s.state === "off" ? C.muted : C.green;
      return `<div class="thermo" style="--c:${col}">
        <div data-action="more" data-entity="${e}"><b>${esc(a.friendly_name || e)}</b><small>${esc({ heating: "calentando", cooling: "enfriando", idle: "en espera", off: "apagado" }[action] || action || "")}</small></div>
        <div class="tt"><button data-action="temp" data-entity="${e}" data-step="-1">−</button><span><b>${a.temperature !== undefined && a.temperature !== null ? n(a.temperature, 1) : "—"}°</b><small>actual ${n(a.current_temperature, 1)}°</small></span><button data-action="temp" data-entity="${e}" data-step="1">+</button></div></div>`;
    }).join("");
    return `<div class="grid">
      ${this.card(`${this.head("Temperaturas", "mdi:thermometer", C.orange, "Clima de cada estancia")}
        <div class="kpis">${this.kpi(this.id("temperatura_interior"), `${n(this.k("temperatura_interior"), 1)} °C`, `Media interior · ▲ ${n(this.ka("temperatura_interior", "maxima"), 1)} ${esc(this.ka("temperatura_interior", "maxima_nombre") || "")} · ▼ ${n(this.ka("temperatura_interior", "minima"), 1)} ${esc(this.ka("temperatura_interior", "minima_nombre") || "")}`, "mdi:home-thermometer", C.orange)}
        ${this.kpi(this.id("humedad_interior"), `${n(this.k("humedad_interior"), 0)} %`, "Humedad media", "mdi:water-percent", C.blue)}
        ${out ? this.kpi(out, `${n(outT, 1)} °C`, "Exterior", "mdi:thermometer", C.blue) : ""}</div>
        <h3>Mapa de calor</h3>${heat || this.empty("Sin sensores de temperatura.")}`, C.orange)}
      ${climates ? this.card(`<h3>Calefacción y climatización</h3><div class="thermos">${climates}</div>`, C.orange) : ""}
      ${temps.length ? this.card(this.live("Temperaturas 24 h (°C)", temps.slice(0, 12).map((e, i) => ({ entity: e, name: this.name(e), color: PALETTE[i % PALETTE.length] })), { unit: " °C", height: 260 }), C.orange, 2) : ""}
      ${(this._ctx.humidities || []).length ? this.card(this.live("Humedad 24 h (%)", this._ctx.humidities.slice(0, 8).map((e, i) => ({ entity: e, name: this.name(e), color: [C.blue, C.cyan, C.violet, C.green, C.lime, C.pink, C.gold, C.orange][i % 8] })), { unit: " %" }), C.blue, 2) : ""}
    </div>`;
  }

  v_riego() {
    const zones = this._ctx.zones || [];
    if (!zones.length) return `<div class="grid">${this.card(this.empty("Añade cada zona en la integración → «Añadir zona de riego»."), C.blue, 4)}</div>`;
    const rain = this.setting("lluvia_sensor");
    const skip = this.id("omitir_si_llueve");
    const cards = zones.map((z) => {
      const v = this.st(z.valve);
      const open = v && ["on", "open", "opening"].includes(v.state);
      const rem = this.id(`${z.id}:riego_restante`);
      const r = this.num(rem) || 0;
      const last = this.attr(rem, "ultimo_riego");
      const soil = z.soil ? this.num(z.soil) : null;
      return this.card(`<div class="zone ${open ? "on" : ""}">
        ${this.head(z.name, "mdi:sprinkler", C.blue, open ? (r > 0 ? `Regando · quedan ${Math.round(r)} min` : "Válvula abierta") : `Parada · último riego ${last ? new Date(last).toLocaleString("es-ES", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"}`)}
        <div class="btns"><button class="btn ${open ? "active" : ""}" style="--c:${C.blue}" data-action="toggle" data-entity="${z.valve}"><ha-icon icon="mdi:valve"></ha-icon>${open ? "Cerrar" : "Abrir"}</button>${this.btn(this.id(`${z.id}:regar`), "Regar", "mdi:sprinkler", C.blue)}</div>
        ${this.slider(this.id(`${z.id}:minutos_riego`), "Minutos", C.blue)}
        ${soil !== null ? `<div class="row">${this.gauge(soil, 0, 100, C.blue, "Humedad del suelo", "%", z.soil)}</div>` : ""}</div>`, C.blue);
    }).join("");
    const soils = zones.filter((z) => z.soil);
    return `<div class="grid">
      ${this.card(`${this.head("Riego", "mdi:sprinkler-variant", C.blue, "Zonas, humedad del suelo y lluvia")}
        <div class="kpis">${this.kpi(this.id("riego_activo"), this.val(this.id("riego_activo")) === "on" ? "Regando" : "Parado", "Riego", "mdi:sprinkler-variant", C.blue)}
        ${rain ? this.kpi(rain, ["on", "rain", "rainy", "pouring"].includes(this.val(rain)) ? "Lloviendo" : "Seco", "Lluvia", "mdi:weather-rainy", C.blue) : ""}</div>
        <div class="btns"><button class="btn ${this.val(skip) === "on" ? "active" : ""}" style="--c:${C.blue}" data-action="toggle" data-entity="${skip}"><ha-icon icon="mdi:weather-pouring"></ha-icon>Omitir si llueve: ${this.val(skip) === "on" ? "sí" : "no"}</button>
        ${this.btn(this.id("parar_riego"), "Parar todo", "mdi:water-off", C.red, "¿Cerrar todas las válvulas?")}</div>`, C.blue)}
      ${cards}
      ${soils.length ? this.card(this.live("Humedad del suelo 7 días (%)", soils.map((z, i) => ({ entity: z.soil, name: z.name, color: [C.blue, C.cyan, C.green, C.lime, C.violet, C.pink][i % 6] })), { hours: 168, unit: " %" }), C.blue, 2) : ""}
    </div>`;
  }
}

const STYLE = `
:host{display:block;height:100%;--c:${C.cyan};color:${C.text};font-family:var(--ha-font-family-body, Roboto, "Segoe UI", sans-serif);
  background:radial-gradient(1200px 600px at 8% -10%, rgba(0,229,255,.16), transparent 60%),radial-gradient(900px 500px at 110% 0%, rgba(255,79,216,.10), transparent 60%),
  repeating-linear-gradient(0deg, rgba(0,229,255,.035) 0 1px, transparent 1px 44px),repeating-linear-gradient(90deg, rgba(0,229,255,.035) 0 1px, transparent 1px 44px),linear-gradient(180deg,#030712,#060d20);}
*{box-sizing:border-box}
.app{display:flex;flex-direction:column;height:100%}
header{position:sticky;top:0;z-index:2;background:rgba(3,8,20,.86);backdrop-filter:blur(8px);border-bottom:1px solid #0e2a44}
.brand{display:flex;align-items:center;gap:10px;padding:8px 16px 0;color:${C.cyan}}
.brand .title{font-weight:700;letter-spacing:4px;text-shadow:0 0 10px ${C.cyan}aa}
.brand .clock{margin-left:auto;color:${C.muted};font-size:12px;font-variant-numeric:tabular-nums}
.menu{display:none}:host([narrow]) .menu{display:block}
nav{display:flex;gap:2px;padding:6px 10px;overflow-x:auto;scrollbar-width:none}
.tab{all:unset;cursor:pointer;display:flex;align-items:center;gap:6px;padding:7px 11px;border-radius:10px;color:${C.muted};font-size:13px;white-space:nowrap;position:relative}
.tab ha-icon{--mdc-icon-size:18px}.tab:hover{color:${C.text};background:#ffffff0d}
.tab.on{color:var(--c);background:color-mix(in srgb,var(--c) 12%,transparent);box-shadow:inset 0 -2px var(--c);text-shadow:0 0 8px var(--c)}
.badge{font-size:10px;color:#000;border-radius:9px;padding:0 5px;margin-left:2px}
main{flex:1;overflow-y:auto;padding:14px}
footer{padding:10px;text-align:center;color:${C.muted};font-size:12px}footer a{color:${C.cyan}}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;align-items:start}
.stack{display:flex;flex-direction:column;gap:14px;grid-column:span var(--span,1)}
@media (max-width:1300px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.card[style*="--span:4"],.card[style*="--span:3"]{grid-column:span 2}}
@media (max-width:760px){.grid{grid-template-columns:1fr}.card,.stack{grid-column:span 1 !important}main{padding:8px}}
.card{grid-column:span var(--span,1);position:relative;background:linear-gradient(150deg,rgba(10,20,44,.92),rgba(3,8,20,.94));border:1px solid color-mix(in srgb,var(--c) 35%,transparent);
  border-radius:16px;padding:14px;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--c) 8%,transparent),0 0 22px color-mix(in srgb,var(--c) 16%,transparent),0 8px 24px rgba(0,0,0,.45);overflow:hidden;min-width:0}
.card::before{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,transparent,var(--c),transparent)}
.card::after{content:"";position:absolute;top:8px;right:10px;width:14px;height:14px;border-top:2px solid var(--c);border-right:2px solid var(--c);opacity:.6;border-radius:0 4px 0 0}
h1{margin:0;font-size:22px;letter-spacing:5px;color:${C.cyan};text-shadow:0 0 12px ${C.cyan}aa}
h2{margin:0;font-size:16px;letter-spacing:3px;text-transform:uppercase;color:var(--c);text-shadow:0 0 10px var(--c)}
h3{margin:10px 0 8px;font-size:13px;letter-spacing:1.5px;text-transform:uppercase;color:var(--c);display:flex;align-items:center;gap:6px}h3:first-child{margin-top:0}
h3 ha-icon{--mdc-icon-size:18px}
p{margin:6px 0}.muted{color:${C.muted};font-size:12px}small{color:${C.muted};font-size:11px}.big{font-size:18px;font-weight:700;white-space:nowrap}td:last-child{white-space:nowrap}
.link{cursor:pointer;color:${C.cyan}}
.head{display:flex;gap:10px;align-items:center;margin-bottom:12px}.head ha-icon{color:var(--c);--mdc-icon-size:28px;filter:drop-shadow(0 0 6px var(--c))}.head p{margin:2px 0 0;color:${C.muted};font-size:12px}
.hero{display:flex;justify-content:space-between;align-items:flex-start}.hero p{color:${C.muted};font-size:13px}
.kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}
.kpi{display:flex;gap:10px;align-items:center;padding:10px;border-radius:12px;background:#0a1630;border:1px solid color-mix(in srgb,var(--c) 22%,transparent);cursor:pointer;transition:.2s}
.kpi:hover{background:color-mix(in srgb,var(--c) 10%,#0a1630);box-shadow:0 0 14px color-mix(in srgb,var(--c) 30%,transparent)}
.ic{width:38px;height:38px;flex:none;border-radius:50%;display:grid;place-items:center;color:var(--c);background:color-mix(in srgb,var(--c) 15%,transparent);box-shadow:0 0 12px color-mix(in srgb,var(--c) 30%,transparent)}
.kpi .v{font-size:17px;font-weight:700;font-variant-numeric:tabular-nums}.kpi .l{color:${C.muted};font-size:11.5px;line-height:1.3}
.row{display:flex;justify-content:center;gap:10px;flex-wrap:wrap}
.gauge{width:180px;max-width:100%;cursor:pointer}.gauge svg{width:100%}
.track{stroke:${C.dim};stroke-width:10;fill:none;stroke-linecap:round}.arc{stroke-width:10;fill:none;stroke-linecap:round;filter:drop-shadow(0 0 5px currentColor)}
.gv{fill:${C.text};font-size:15px;font-weight:700;text-anchor:middle}.gl{fill:${C.muted};font-size:8px;text-anchor:middle}
table{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}td,th{padding:5px 4px;border-bottom:1px solid #12223a;text-align:right}
td:first-child,th:first-child{text-align:left}th{color:${C.muted};font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:1px}
.bar{display:inline-block;height:8px;background:${C.dim};border-radius:5px;overflow:hidden;vertical-align:middle}.bar i{display:block;height:100%;border-radius:5px;box-shadow:0 0 8px currentColor}
.chips{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px}.chip{all:unset;cursor:pointer;padding:4px 10px;border-radius:14px;background:#0d1c33;color:${C.muted};font-size:12px}
.chip.on{background:var(--c);color:#02101c;font-weight:700;box-shadow:0 0 10px var(--c)}
.alert{border-left:3px solid var(--c);background:color-mix(in srgb,var(--c) 10%,transparent);border-radius:8px;padding:8px 10px;margin:6px 0;display:flex;flex-direction:column;gap:2px;font-size:12.5px;cursor:pointer}
.alert b{color:var(--c)}
.ok{display:flex;gap:8px;align-items:center;color:${C.green};padding:10px;border-radius:10px;background:${C.green}14}
.empty{display:flex;gap:8px;align-items:center;color:${C.muted};padding:10px}
.loading{color:${C.muted};padding:30px;text-align:center}
.chart{width:100%;height:auto;display:block}.chart line.grid{stroke:${C.line};stroke-dasharray:3}.chart .zero{stroke:${C.muted};stroke-width:1}
.chart .ax{fill:${C.muted};font-size:10px}.glow{filter:drop-shadow(0 0 3px currentColor)}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:11.5px;color:${C.muted};margin-top:4px}.legend i{display:inline-block;width:10px;height:3px;margin-right:5px;vertical-align:middle;border-radius:2px}.legend b{color:${C.text}}
.flow{width:100%;max-height:420px;display:block}
.fl{fill:none;stroke-width:2;opacity:.18;stroke-dasharray:4 6}.fl.on{opacity:.75;stroke-width:3}.dot{filter:drop-shadow(0 0 4px currentColor)}
.node{cursor:pointer}.ring{fill:none;stroke:var(--c);stroke-width:3;filter:drop-shadow(0 0 8px var(--c))}.core{fill:#06112a}
.nv{fill:${C.text};font-size:15px;font-weight:700;text-anchor:middle}.ns{fill:${C.muted};font-size:10px;text-anchor:middle}.nl{fill:var(--c);font-size:12px;text-anchor:middle;letter-spacing:1px}
.pills{display:flex;gap:6px;flex-wrap:wrap;justify-content:center}
.pill{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--c);color:var(--c);border-radius:20px;padding:3px 10px;font-size:12px;margin:2px;cursor:pointer}.pill ha-icon{--mdc-icon-size:15px}.pill b{color:${C.text}}
.strings{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}
.string{padding:10px;border-radius:12px;background:#0a1630;border:1px solid color-mix(in srgb,var(--c) 25%,transparent);cursor:pointer;display:flex;flex-direction:column;gap:4px}
.string .sn{display:flex;gap:6px;align-items:center;color:var(--c)}.string .sv{font-size:20px;font-weight:700}.string .bar{width:100%}
.cells{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:3px 12px}
.cell{display:grid;grid-template-columns:22px 1fr 78px;gap:6px;align-items:center;font-size:12px;cursor:pointer}.cell .bar{width:100%}.cell span{color:${C.muted}}
.rank{display:grid;grid-template-columns:24px 1fr auto;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid #12223a;cursor:pointer}
.rank ha-icon{color:${C.pink}}.rank .bar{width:100%;margin-top:4px}.rank span{text-align:right;display:flex;flex-direction:column}
.counts{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center}.counts div{padding:10px;border-radius:12px;background:color-mix(in srgb,var(--c) 10%,transparent);color:var(--c);font-size:12px}
.counts b{display:block;font-size:30px;text-shadow:0 0 12px var(--c)}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.btn{all:unset;cursor:pointer;display:inline-flex;align-items:center;gap:6px;padding:9px 14px;border-radius:12px;border:1px solid var(--c);color:var(--c);font-size:13px;transition:.2s}
.btn:hover,.btn.active{background:var(--c);color:#02101c;box-shadow:0 0 14px var(--c)}
.slider{display:grid;grid-template-columns:1fr 1.2fr 80px;gap:8px;align-items:center;font-size:12px;margin:6px 0}.slider b{text-align:right}
input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:6px;border-radius:4px;background:${C.dim};outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:var(--c);box-shadow:0 0 10px var(--c);cursor:pointer}
input[type=range]::-moz-range-thumb{width:16px;height:16px;border-radius:50%;background:var(--c);box-shadow:0 0 10px var(--c);cursor:pointer;border:none}
.co2hero{text-align:center;padding:10px}.co2hero p{color:${C.muted};letter-spacing:3px;font-size:12px}.co2hero h1{font-size:54px;color:${C.lime};text-shadow:0 0 20px ${C.lime}}
.eq{display:flex;justify-content:center;gap:24px;flex-wrap:wrap;margin-top:8px}.eq span{display:flex;gap:6px;align-items:center}.eq ha-icon{color:${C.lime}}
.bars{display:grid;grid-template-columns:80px 1fr 50px;gap:8px;align-items:center;font-size:12px;margin-top:8px}.bars .bar{width:100%}
.lights{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px}
.light{padding:10px;border-radius:12px;background:#0a1630;border:1px solid #1d2d4a;display:grid;grid-template-columns:40px 1fr;gap:4px 8px;align-items:center}
.light div{cursor:pointer;display:flex;flex-direction:column}.light input{grid-column:1/3}
.light.on{border-color:var(--c);box-shadow:0 0 14px color-mix(in srgb,var(--c) 35%,transparent)}.light.off{opacity:.45}
.lamp{all:unset;cursor:pointer;width:38px;height:38px;border-radius:50%;display:grid;place-items:center;background:#0d1c33;color:${C.muted}}
.light.on .lamp{background:var(--c);color:#201600;box-shadow:0 0 16px var(--c)}
.heat{display:grid;grid-template-columns:1fr 70px 1.2fr;gap:8px;align-items:center;font-size:12.5px;padding:3px 0;cursor:pointer}.heat .bar{width:100%}
.thermos{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px}
.thermo{padding:10px;border-radius:12px;background:#0a1630;border:1px solid color-mix(in srgb,var(--c) 40%,transparent);display:flex;flex-direction:column;gap:6px}
.thermo > div:first-child{cursor:pointer;display:flex;flex-direction:column}
.tt{display:flex;align-items:center;justify-content:space-between}.tt span{text-align:center;display:flex;flex-direction:column}.tt b{font-size:24px;color:var(--c);text-shadow:0 0 10px var(--c)}
.tt button{all:unset;cursor:pointer;width:34px;height:34px;border-radius:50%;border:1px solid var(--c);color:var(--c);display:grid;place-items:center;font-size:18px}.tt button:hover{background:var(--c);color:#000}
.zone.on .head ha-icon{animation:pulse 1.2s infinite}
@keyframes pulse{50%{opacity:.4}}
`;

if (!customElements.get("centro-control-panel")) customElements.define("centro-control-panel", CentroControlPanel);
