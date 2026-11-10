/*
 * Centro de Control — panel de Home Assistant.
 * Creado por manu8613 · https://github.com/manu8613/centro-control
 * Licencia Apache 2.0 (conservar esta atribución en copias y derivados).
 *
 * Panel autónomo (sin dependencias): HTML + CSS + SVG generados aquí.
 * Las gráficas leen el historial de tus sensores originales, así que se
 * conservan desde el primer día.
 */

const C = {
  cyan: "#00e5ff", amber: "#ffc400", green: "#00e676", pink: "#ff4fd8", violet: "#b388ff",
  blue: "#40c4ff", orange: "#ff9100", red: "#ff1744", lime: "#c6ff00", gold: "#ffd740",
  text: "#e6f7ff", muted: "#8fb3c9", line: "#1b2a44",
};
const PALETTE = [C.amber, C.pink, C.cyan, C.green, C.violet, C.orange, C.blue, C.lime, C.gold, C.red, "#ff8a80", "#82b1ff"];
const PERIODS = { hoy: "Hoy", ayer: "Ayer", mes: "Este mes", factura: "Factura", ano: "Este año", total: "Total" };
const TABS = [
  ["resumen", "Puente de mando", "mdi:view-dashboard-variant"],
  ["red", "Red", "mdi:transmission-tower"],
  ["solar", "Solar", "mdi:solar-power-variant"],
  ["bateria", "Batería", "mdi:home-battery"],
  ["consumos", "Consumos", "mdi:home-lightning-bolt"],
  ["problemas", "Problemas", "mdi:alert-decagram"],
  ["coste", "Coste", "mdi:cash-multiple"],
  ["co2", "CO₂", "mdi:leaf-circle"],
  ["gas", "Gas", "mdi:fire"],
  ["luces", "Luces", "mdi:lightbulb-group"],
  ["clima", "Temperaturas", "mdi:thermometer"],
  ["riego", "Riego", "mdi:sprinkler-variant"],
  ["config", "Configuración", "mdi:cog"],
];
// Rotación automática de pestañas (por dispositivo). «config» nunca rota.
const ROT_KEY = "centro_control_ajustes";
const MAN_KEY = "centro_control_carga_manual";
const ROT_SECS = [10, 15, 30, 60, 120, 300];
const ROT_RESUME = [15, 30, 60, 120, 300];
const ROT_DEFAULT = { on: false, secs: 30, resume: 60, off: [] };
const fmtSecs = (s) => (s >= 60 ? `${s / 60} min` : `${s} s`);

// ------------------------------------------------------------------ formatting
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const isNum = (v) => v !== null && v !== undefined && v !== "" && !isNaN(Number(v));
const toNum = (v, d = null) => (isNum(v) ? Number(v) : d);
function fmt(v, dec = 1) {
  if (!isNum(v)) return "—";
  return Number(v).toLocaleString("es-ES", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
function fmtW(w) {
  if (!isNum(w)) return "—";
  const v = Number(w);
  return Math.abs(v) >= 1000 ? `${fmt(v / 1000, 2)} kW` : `${fmt(v, 0)} W`;
}
const eur = (v, d = 2) => (isNum(v) ? `${fmt(v, d)} €` : "—");
const kwh = (v, d = 1) => (isNum(v) ? `${fmt(v, d)} kWh` : "—");
function fmtDate(iso, withTime = false) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  const p = (n) => String(n).padStart(2, "0");
  return withTime ? `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}` : `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`;
}
const icon = (i, cls = "") => `<ha-icon class="${cls}" icon="${esc(i)}"></ha-icon>`;

// ------------------------------------------------------------------ styles
const CSS = `
:host{display:block;min-height:100vh;color:${C.text};font-family:var(--paper-font-body1_-_font-family, "Segoe UI", Roboto, sans-serif);
 background:radial-gradient(1200px 600px at 8% -10%, rgba(0,229,255,.16), transparent 60%),radial-gradient(900px 500px at 110% 0%, rgba(255,79,216,.10), transparent 60%),
 repeating-linear-gradient(0deg, rgba(0,229,255,.035) 0 1px, transparent 1px 44px),repeating-linear-gradient(90deg, rgba(0,229,255,.035) 0 1px, transparent 1px 44px),
 linear-gradient(180deg,#030712,#060d20)}
*{box-sizing:border-box}
header{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:6px;padding:6px 10px;background:rgba(3,8,20,.88);backdrop-filter:blur(8px);border-bottom:1px solid #0e2a44}
.menu{display:none}.menu.show{display:block}
.brand{display:flex;align-items:center;gap:8px;color:${C.cyan};font-weight:700;letter-spacing:3px;text-transform:uppercase;font-size:14px;white-space:nowrap;text-shadow:0 0 10px ${C.cyan}aa;margin-right:6px}
nav{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;flex:1;min-width:0}
nav button{all:unset;cursor:pointer;display:flex;align-items:center;gap:6px;padding:8px 11px;border-radius:10px;color:${C.muted};font-size:13px;white-space:nowrap;position:relative}
nav button ha-icon{--mdc-icon-size:18px}
nav button:hover{color:${C.text};background:#0b1a30}
nav button.on{color:${C.cyan};background:${C.cyan}14;box-shadow:inset 0 -2px ${C.cyan}}
nav .badge{position:absolute;top:2px;right:2px;min-width:16px;height:16px;border-radius:8px;background:${C.red};color:#fff;font-size:10px;display:flex;align-items:center;justify-content:center;padding:0 4px;box-shadow:0 0 8px ${C.red}}
nav .badge.warn{background:${C.amber};color:#221}
main{padding:16px;max-width:1800px;margin:0 auto;container-type:inline-size}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;align-items:start}
.sec{display:grid;grid-template-columns:repeat(12,1fr);gap:10px;align-content:start}
.sec{position:relative}
.sec.w2{grid-column:span 2}.sec.w3{grid-column:span 3}.sec.wall,.sec.charts{grid-column:1/-1}
.sec.charts>.card{grid-column:span 6}
.card.u12{grid-column:span 12!important}.card.u6{grid-column:span 6!important}.card.u4{grid-column:span 4!important}.card.u3{grid-column:span 3!important}
@container (max-width:1040px){.sec.w3{grid-column:span 2}}
@container (max-width:900px){.sec.charts>.card{grid-column:span 12}}
@container (max-width:690px){.sec.w2,.sec.w3{grid-column:span 1}.card.u6,.card.u4,.card.u3{grid-column:span 12!important}}
@media(max-width:720px){.sec.w2,.sec.w3{grid-column:span 1}}
@media(max-width:760px){header{gap:4px;padding:6px}.brand{letter-spacing:0;margin-right:0}.brand .t{display:none}.laybtn span{display:none}.laybtn{padding:7px}nav button{padding:8px 9px}}
.laybtn{all:unset;flex:none;cursor:pointer;display:flex;align-items:center;gap:6px;padding:7px 10px;border-radius:10px;color:${C.muted};font-size:13px;white-space:nowrap;border:1px solid #12304d}
.laybtn:hover,.laybtn.on{color:${C.amber};border-color:${C.amber}88;background:${C.amber}14}
.rotbtn.on{color:${C.cyan};border-color:${C.cyan}88;background:${C.cyan}14}.rotbtn.on:hover{color:${C.cyan};border-color:${C.cyan}88;background:${C.cyan}22}
.layinfo{grid-column:1/-1;display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:10px 14px;border:1px dashed ${C.amber}aa;border-radius:14px;color:${C.amber};background:${C.amber}0d;font-size:13px}
.layinfo button,.lay button{all:unset;cursor:pointer;padding:5px 9px;border-radius:8px;border:1px solid ${C.amber}77;color:${C.amber};font-size:12px;display:inline-flex;align-items:center;gap:4px;background:#0a1222}
.layinfo button:hover,.lay button:hover{background:${C.amber}22}
main.edit .sec{outline:1px dashed ${C.amber}55;outline-offset:4px;border-radius:12px;padding-top:34px}
.lay{position:absolute;top:0;right:0;z-index:3;display:flex;gap:4px;align-items:center}
.lay.sl{left:0;right:auto;top:0;color:${C.amber};font-size:11px;letter-spacing:1px;text-transform:uppercase}
.card .lay{top:6px;right:6px}.card .lay button{padding:3px 7px;background:#060d20ee}
main.edit .card,main.edit .title{cursor:default}main.edit .card{padding-top:34px}
.card{--c:${C.cyan};position:relative;grid-column:span 12;background:linear-gradient(150deg,rgba(10,20,44,.92),rgba(3,8,20,.94));border:1px solid color-mix(in srgb,var(--c) 34%,transparent);
 border-radius:16px;padding:12px 14px;font-size:13px;overflow:hidden;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--c) 8%,transparent),0 0 22px color-mix(in srgb,var(--c) 14%,transparent),0 8px 24px rgba(0,0,0,.45)}
.card::before{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,transparent,var(--c),transparent)}
.card.s6{grid-column:span 6}.card.s4{grid-column:span 4}.card.s3{grid-column:span 3}.card.s8{grid-column:span 8}
.card.click{cursor:pointer;transition:transform .15s, box-shadow .15s}.card.click:hover{transform:translateY(-1px);box-shadow:0 0 30px color-mix(in srgb,var(--c) 30%,transparent)}
.title{grid-column:span 12;color:var(--c,${C.cyan});padding:6px 2px 0}
.title h2{margin:0;font-size:17px;text-transform:uppercase;letter-spacing:3px;font-weight:700;text-shadow:0 0 10px var(--c),0 0 22px color-mix(in srgb,var(--c) 40%,transparent);display:flex;gap:8px;align-items:center}
.title p{margin:3px 0 0;color:${C.muted};font-size:12px}
h3{margin:0 0 8px;font-size:13px;color:var(--c);letter-spacing:.6px;text-transform:uppercase;display:flex;align-items:center;gap:6px}
h3 ha-icon{--mdc-icon-size:16px}
.kpi{display:flex;gap:12px;align-items:center}
.kpi .ic{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none;color:var(--c);background:color-mix(in srgb,var(--c) 15%,transparent);box-shadow:0 0 14px color-mix(in srgb,var(--c) 35%,transparent)}
.kpi .v{font-size:20px;font-weight:700;line-height:1.1}.kpi .l{color:${C.muted};font-size:11.5px;margin-top:3px}
.big{font-size:34px;font-weight:800;color:var(--c);text-shadow:0 0 16px color-mix(in srgb,var(--c) 60%,transparent)}
.muted{color:${C.muted}}.small{font-size:11px}
table{width:100%;border-collapse:collapse;font-size:12.5px}td,th{padding:4px 5px;border-bottom:1px solid #12223a;text-align:left;vertical-align:top}
th{color:${C.muted};font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px}td.r,th.r{text-align:right;white-space:nowrap}tr.tot td{color:${C.gold};font-weight:800;border-bottom:none;font-size:14px}
.alert{padding:8px 10px;border-radius:9px;margin:6px 0;border-left:4px solid var(--a);background:color-mix(in srgb,var(--a) 13%,transparent);font-size:12.5px}
.alert b{color:var(--a)}.alert .when{color:${C.muted};font-size:11px;margin-top:3px}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{all:unset;cursor:pointer;padding:5px 11px;border-radius:14px;background:#0d1c33;color:${C.muted};font-size:12px;border:1px solid #16304f}
.chip.on{background:var(--c);color:#031018;font-weight:700;box-shadow:0 0 12px var(--c)}
.btn{all:unset;box-sizing:border-box;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:9px 14px;border-radius:12px;border:1px solid color-mix(in srgb,var(--c) 50%,transparent);color:var(--c);background:color-mix(in srgb,var(--c) 10%,transparent);font-weight:600;font-size:13px}
.btn:hover{background:color-mix(in srgb,var(--c) 22%,transparent);box-shadow:0 0 14px color-mix(in srgb,var(--c) 40%,transparent)}
.btn.full{display:flex;width:100%}
.bar{height:8px;border-radius:5px;background:#0d1c33;overflow:hidden}.bar>i{display:block;height:100%;border-radius:5px;background:var(--b,var(--c));box-shadow:0 0 8px var(--b,var(--c))}
.row{display:flex;align-items:center;gap:10px;padding:5px 0}.row .n{flex:0 0 38%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.row .bar{flex:1}.row .x{flex:0 0 auto;text-align:right;min-width:72px;font-variant-numeric:tabular-nums}
input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:8px;border-radius:5px;background:#0d1c33;outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;border-radius:50%;background:var(--c);box-shadow:0 0 10px var(--c);cursor:pointer}
input[type=range]::-moz-range-thumb{width:18px;height:18px;border-radius:50%;background:var(--c);box-shadow:0 0 10px var(--c);cursor:pointer;border:none}
.sim{display:grid;grid-template-columns:1fr 64px;gap:4px 10px;align-items:center;margin:6px 0}.sim label{font-size:12px;color:${C.muted};grid-column:1/-1}
.sim b{text-align:right;font-variant-numeric:tabular-nums}
.nrb{grid-column:1/-1;display:flex;align-items:center;gap:12px}.nrb input[type=range]{flex:1;min-width:0}.nrv{display:flex;align-items:center;gap:4px}.nrv input{width:76px;text-align:right;font:inherit;font-variant-numeric:tabular-nums;color:inherit;background:rgba(255,255,255,.06);border:1px solid ${C.muted};border-radius:8px;padding:6px 8px}.nrw{white-space:nowrap;font-variant-numeric:tabular-nums;color:${C.cyan};min-width:84px;text-align:right}.nrv i{font-style:normal;color:${C.muted};min-width:18px}
svg text{font-family:inherit}
.chart{position:relative;min-height:180px}.chart svg{width:100%;display:block}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:11px;color:${C.muted};margin-top:4px}.legend span{display:flex;align-items:center;gap:5px}.legend i{width:10px;height:3px;border-radius:2px;display:inline-block}
.tip{position:absolute;pointer-events:none;background:rgba(3,8,20,.95);border:1px solid #1d3557;border-radius:8px;padding:6px 8px;font-size:11px;white-space:nowrap;display:none;z-index:2}
.loading{color:${C.muted};font-size:12px;padding:20px 0;text-align:center}
.flow .ln{fill:none;stroke-width:2.2;stroke-dasharray:6 10;animation:dash var(--d,1.5s) linear infinite}
@keyframes dash{to{stroke-dashoffset:-32}}
.flow .node circle.ring{filter:drop-shadow(0 0 6px var(--c))}
.pulse{animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{opacity:.45}}
.light{display:flex;align-items:center;gap:10px}.light .ic{cursor:pointer}.light.on .ic{color:${C.gold};background:${C.gold}26;box-shadow:0 0 16px ${C.gold}88}
.light.off .ic{color:#5c7089;background:#0d1c33;box-shadow:none}.light .grow{flex:1;min-width:0}
.thermo{text-align:center}.thermo .ctr{display:flex;align-items:center;justify-content:center;gap:12px}
.cells{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:4px 14px}
.cell{display:flex;align-items:center;gap:6px;font-size:11.5px;font-variant-numeric:tabular-nums}.cell .bar{flex:1;height:7px}
.foot{grid-column:1/-1;text-align:center;color:${C.muted};font-size:12px;padding:14px}.foot a{color:${C.cyan}}
.empty{color:${C.muted};font-size:13px;padding:6px 0}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;background:var(--a);box-shadow:0 0 6px var(--a)}
`;

// ------------------------------------------------------------------ charts
function niceMax(v) {
  if (!(v > 0)) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 2, 2.5, 5, 10]) if (v <= m * p) return m * p;
  return 10 * p;
}
function drawChart(el, series, opt) {
  const W = el.clientWidth || 600, H = opt.height || 220, L = 46, R = 10, T = 10, B = 24;
  const t0 = opt.start, t1 = opt.end;
  const all = series.flatMap((s) => s.points.map((p) => p[1])).filter((v) => isNum(v));
  let lo = Math.min(0, ...all), hi = Math.max(0, ...all);
  if (opt.stacked) {
    const sums = {};
    series.forEach((s) => s.points.forEach(([t, v]) => (sums[t] = (sums[t] || 0) + Math.max(v, 0))));
    hi = Math.max(hi, ...Object.values(sums));
  }
  if (opt.min !== undefined) lo = opt.min;
  if (opt.max !== undefined) hi = opt.max;
  if (hi === lo) hi = lo + 1;
  let step = opt.max !== undefined && opt.min !== undefined ? (hi - lo) / 4 : niceMax((hi - lo) / 4);
  if (opt.min === undefined) lo = Math.floor(lo / step) * step;
  if (opt.max === undefined) hi = Math.ceil(hi / step) * step;
  if (hi === lo) hi = lo + step;
  const x = (t) => L + ((t - t0) / (t1 - t0)) * (W - L - R);
  const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  let s = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" height="${H}">`;
  const nTicks = Math.round((hi - lo) / step);
  for (let i = 0; i <= nTicks; i++) {
    const v = lo + step * i;
    s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="${C.line}" stroke-dasharray="3 4"/>`;
    s += `<text x="${L - 6}" y="${y(v) + 3}" text-anchor="end" fill="${C.muted}" font-size="10">${fmt(v, step < 1 ? (step < 0.1 ? 2 : 1) : 0)}</text>`;
  }
  const span = t1 - t0, day = 86400000;
  const p2 = (n) => String(n).padStart(2, "0");
  const label = (d) => (span <= 2 * day ? `${p2(d.getHours())}:${p2(d.getMinutes())}` : span <= 40 * day ? `${p2(d.getDate())}/${p2(d.getMonth() + 1)}` : d.toLocaleDateString("es-ES", { month: "short" }));
  const slotTimes = opt.slots && opt.slots <= 24 ? (series.find((q) => q.points.length) || { points: [] }).points.map((p) => p[0]) : null;
  const tickTimes = slotTimes && slotTimes.length ? slotTimes : Array.from({ length: 7 }, (_, i) => t0 + (span * i) / 6);
  const every = Math.max(1, Math.ceil(tickTimes.length / 12));
  tickTimes.forEach((t, i) => {
    if (i % every) return;
    s += `<text x="${x(t)}" y="${H - 6}" text-anchor="middle" fill="${C.muted}" font-size="10">${label(new Date(t))}</text>`;
  });
  if (lo < 0) s += `<line x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}" stroke="#2d4a70"/>`;
  const bars = series.filter((q) => q.type === "bar");
  const base = {};
  series.forEach((q) => {
    const pts = q.points.filter((p) => isNum(p[1]) && p[0] >= t0 - 1 && p[0] <= t1 + 1);
    if (!pts.length) return;
    if (q.type === "bar") {
      const n = bars.length, i = bars.indexOf(q);
      const slot = (W - L - R) / Math.max(opt.slots || pts.length, 1);
      const bw = Math.max(2, (slot * 0.8) / (opt.stacked ? 1 : n));
      pts.forEach(([t, v]) => {
        const b0 = opt.stacked ? base[t] || 0 : 0;
        const x0 = x(t) - (slot * 0.8) / 2 + (opt.stacked ? 0 : i * bw);
        const y0 = y(Math.max(v, 0) + b0), y1 = y(Math.min(v, 0) + b0);
        s += `<rect x="${x0}" y="${Math.min(y0, y1)}" width="${bw}" height="${Math.max(Math.abs(y1 - y0), 1)}" rx="2" fill="${q.color}" opacity=".88"/>`;
        if (opt.stacked) base[t] = b0 + Math.max(v, 0);
      });
      return;
    }
    let d = "";
    pts.forEach(([t, v], k) => {
      const yy = y(v);
      d += k === 0 ? `M${x(t)},${yy}` : q.step ? `H${x(t)}V${yy}` : `L${x(t)},${yy}`;
    });
    if (q.type === "area") s += `<path d="${d}L${x(pts[pts.length - 1][0])},${y(Math.max(lo, 0))}L${x(pts[0][0])},${y(Math.max(lo, 0))}Z" fill="${q.color}" opacity=".16"/>`;
    s += `<path d="${d}" fill="none" stroke="${q.color}" stroke-width="2" style="filter:drop-shadow(0 0 3px ${q.color})"/>`;
  });
  s += `<line class="cur" x1="0" x2="0" y1="${T}" y2="${H - B}" stroke="${C.muted}" stroke-dasharray="2 3" style="display:none"/></svg>`;
  const legend = series.map((q) => `<span><i style="background:${q.color}"></i>${esc(q.name)}</span>`).join("");
  el.innerHTML = s + `<div class="legend">${legend}</div><div class="tip"></div>`;
  const svg = el.querySelector("svg"), tip = el.querySelector(".tip"), cur = el.querySelector(".cur");
  const unit = opt.unit || "";
  svg.addEventListener("mousemove", (ev) => {
    const r = svg.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * W;
    const t = t0 + ((px - L) / (W - L - R)) * (t1 - t0);
    if (t < t0 || t > t1) return;
    const rows = series.map((q) => {
      let best = null;
      for (const p of q.points) if (p[0] <= t + (opt.slots ? span / opt.slots / 2 : 0)) best = p;
      return best && isNum(best[1]) ? `<div><span class="dot" style="--a:${q.color}"></span>${esc(q.name)}: <b>${fmt(best[1], opt.decimals ?? (Math.abs(best[1]) < 10 ? 2 : 0))} ${unit}</b></div>` : "";
    });
    const d = new Date(t);
    tip.innerHTML = `<div class="muted">${span <= 2 * day ? d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }) : d.toLocaleDateString("es-ES")}</div>${rows.join("")}`;
    tip.style.display = "block";
    const left = Math.min(ev.clientX - r.left + 12, r.width - tip.offsetWidth - 4);
    tip.style.left = `${left}px`;
    tip.style.top = `8px`;
    cur.setAttribute("x1", px);
    cur.setAttribute("x2", px);
    cur.style.display = "";
  });
  svg.addEventListener("mouseleave", () => {
    tip.style.display = "none";
    cur.style.display = "none";
  });
}

function gauge(value, min, max, color, label, unit, size = 150) {
  const v = toNum(value);
  const f = v === null ? 0 : Math.max(0, Math.min(1, (v - min) / (max - min || 1)));
  const R = 52, cx = 70, cy = 66, a0 = Math.PI * 0.85, a1 = Math.PI * 2.15;
  const a = a0 + (a1 - a0) * f;
  const pt = (ang) => [cx + R * Math.cos(ang), cy + R * Math.sin(ang)];
  const [x0, y0] = pt(a0), [x1, y1] = pt(a1), [xa, ya] = pt(a);
  const large = (a - a0) > Math.PI ? 1 : 0;
  const ticks = Array.from({ length: 11 }, (_, i) => {
    const t = a0 + ((a1 - a0) * i) / 10, [p, q] = [cx + (R + 9) * Math.cos(t), cy + (R + 9) * Math.sin(t)], [r, s] = [cx + (R + 5) * Math.cos(t), cy + (R + 5) * Math.sin(t)];
    return `<line x1="${p}" y1="${q}" x2="${r}" y2="${s}" stroke="${i / 10 <= f ? color : "#1d2d4a"}" stroke-width="1.5"/>`;
  }).join("");
  return `<svg viewBox="0 0 140 120" style="width:100%;max-width:${size}px;display:block;margin:auto">
  ${ticks}
  <path d="M${x0},${y0} A${R},${R} 0 1 1 ${x1},${y1}" stroke="#14233b" stroke-width="10" fill="none" stroke-linecap="round"/>
  ${f > 0.001 ? `<path d="M${x0},${y0} A${R},${R} 0 ${large} 1 ${xa},${ya}" stroke="${color}" stroke-width="10" fill="none" stroke-linecap="round" style="filter:drop-shadow(0 0 6px ${color})"/>` : ""}
  <text x="70" y="70" text-anchor="middle" fill="${C.text}" font-size="21" font-weight="800">${v === null ? "—" : fmt(v, Math.abs(v) >= 100 ? 0 : 1)}</text>
  <text x="70" y="86" text-anchor="middle" fill="${C.muted}" font-size="10">${esc(unit)}</text>
  <text x="70" y="114" text-anchor="middle" fill="${C.muted}" font-size="11">${esc(label)}</text></svg>`;
}

// ------------------------------------------------------------------ the panel
class CentroControlPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = (location.hash || "").replace("#", "") || "resumen";
    if (!TABS.some((t) => t[0] === this._tab)) this._tab = "resumen";
    this._cards = new Map();
    this._layoutKey = "";
    this._cache = {};
    this._busy = 0;
    this._last = 0;
  }

  set hass(h) {
    this._hass = h;
    if (this._menu) this._menu.hass = h;
    this._schedule();
  }
  set narrow(n) {
    this._narrow = n;
    if (this._menu) {
      this._menu.narrow = n;
      this._menu.classList.toggle("show", !!n);
    }
  }
  set panel(p) {
    this.cfg = p?.config || {};
    this._schedule(true);
  }
  set route(_r) {}

  connectedCallback() {
    if (this._built) return;
    this._built = true;
    const root = this.shadowRoot;
    root.innerHTML = `<style>${CSS}</style><header><span class="menu"></span><div class="brand">${icon("mdi:atom-variant")}<span class="t"></span></div><nav></nav><button class="laybtn rotbtn" data-rot="toggle"></button><button class="laybtn" data-lay="toggle" title="Mover y redimensionar tarjetas y gráficas en este dispositivo">${icon("mdi:view-dashboard-edit-outline")}<span>Diseño</span></button></header><main><div class="grid"></div></main>`;
    const holder = root.querySelector(".menu");
    this._menu = document.createElement("ha-menu-button");
    holder.appendChild(this._menu);
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;
    holder.classList.toggle("show", !!this._narrow);
    this._grid = root.querySelector(".grid");
    root.addEventListener("click", (e) => this._click(e));
    root.addEventListener("change", (e) => this._change(e));
    root.addEventListener("input", (e) => {
      this._busy = Date.now() + 2500;
      const t = e.target;
      if (t.dataset && t.dataset.manin) {
        const b = t.closest(".nrb");
        if (b && t.value !== "") {
          for (const o of b.querySelectorAll("input[data-manin]")) if (o !== t) o.value = t.value;
          const n = (x) => (x === "" || x === undefined ? NaN : Number(x));
          const p = b.parentElement.querySelector(".manp");
          if (p) p.textContent = this._manPreview(Number(t.value), n(b.dataset.s08), n(b.dataset.cap), n(b.dataset.target));
          const ab = b.closest(".card, .sim")?.parentElement?.querySelector('[data-adv="apply"] .advl');
          if (ab) ab.textContent = `Aplicar en el Deye: cargar hasta ${Math.round(Number(t.value))} % (manual)`;
        }
      }
      if (t.dataset && t.dataset.nr) {
        const b = t.closest(".nrb");
        if (b) for (const o of b.querySelectorAll("input[data-nr]")) if (o !== t && t.value !== "") o.value = t.value;
        if (b && b.dataset.volt && t.value !== "") {
          const cap = b.dataset.cap ? Number(b.dataset.cap) : Infinity;
          const val = Number(t.value), w = b.querySelector(".nrw");
          if (w) {
            w.textContent = `≈ ${Math.round(Math.min(val, cap) * Number(b.dataset.volt)).toLocaleString("es-ES")} W${val > cap ? ` (máx. ${cap} A)` : ""}`;
            w.style.color = val > cap ? C.red : "";
          }
        }
      }
    });
    root.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.dataset && (e.target.dataset.nr || e.target.dataset.manin) && e.target.type === "number") e.target.blur();
    });
    window.addEventListener("hashchange", () => {
      const t = location.hash.replace("#", "");
      if (TABS.some((x) => x[0] === t) && t !== this._tab) this._go(t);
    });
    this._timer = setInterval(() => this._refreshCharts(), 60000);
    // Cualquier toque, tecla o rueda del usuario retrasa el siguiente cambio de pestaña.
    const touched = () => this._rotTouched();
    for (const ev of ["pointerdown", "keydown", "wheel"]) root.addEventListener(ev, touched, { passive: true });
    this._rotUi();
    this._rotSchedule();
    this._schedule(true);
  }
  disconnectedCallback() {
    clearInterval(this._timer);
    clearTimeout(this._rotTimer);
    this._rotTimer = null;
    this._built = false;
  }

  // ---------------------------------------------------------------- manual night grid-charge target (per device)
  _manLoad() {
    if (this._man) return this._man;
    let r = {};
    try {
      r = JSON.parse(localStorage.getItem(MAN_KEY) || "{}") || {};
    } catch (e) {
      r = {};
    }
    const soc = Number(r.soc);
    this._man = { on: r.on === true, soc: Number.isFinite(soc) ? Math.max(0, Math.min(100, Math.round(soc))) : null };
    return this._man;
  }
  _manSave() {
    try {
      localStorage.setItem(MAN_KEY, JSON.stringify(this._manLoad()));
    } catch (e) {
      /* modo privado: dura hasta recargar */
    }
  }
  /** What a manual night target means: SOC at 08:00 and the energy the grid has to supply (cap = battery kWh, s08 = SOC at 08:00 without grid, target = advised). */
  _manPreview(v, s08, cap, target) {
    const parts = [`Empezarías el día a las 08:00 con ≈ ${fmt(v, 0)} %`];
    if (Number.isFinite(s08) && Number.isFinite(cap) && cap > 0) {
      const grid = Math.max(0, v - s08) / 100 * cap / 0.9;
      parts.push(grid > 0.05 ? `la red aportaría ≈ ${fmt(grid, 1)} kWh` : `sin red llegarías con ≈ ${fmt(s08, 0)} %: no hace falta cargar`);
    }
    let cmp = "";
    if (Number.isFinite(target)) cmp = v < target ? ` · ${fmt(target - v, 0)} puntos por debajo de lo aconsejado (${fmt(target, 0)} %): la batería podría no llegar a las 00:00` : v > target ? ` · ${fmt(v - target, 0)} puntos por encima de lo aconsejado (${fmt(target, 0)} %)` : " · igual que lo aconsejado";
    return parts.join(" · ") + cmp;
  }

  // ---------------------------------------------------------------- tab rotation (per device)
  _rotLoad() {
    if (this._rot) return this._rot;
    let r = {};
    try {
      r = JSON.parse(localStorage.getItem(ROT_KEY) || "{}") || {};
    } catch (e) {
      r = {};
    }
    this._rot = {
      on: r.on === true,
      secs: ROT_SECS.includes(r.secs) ? r.secs : ROT_DEFAULT.secs,
      resume: ROT_RESUME.includes(r.resume) ? r.resume : ROT_DEFAULT.resume,
      off: Array.isArray(r.off) ? r.off.filter((k) => TABS.some((t) => t[0] === k && k !== "config")) : [],
    };
    return this._rot;
  }
  _rotSave() {
    try {
      localStorage.setItem(ROT_KEY, JSON.stringify(this._rotLoad()));
    } catch (e) {
      /* modo privado: los ajustes duran hasta recargar la página */
    }
  }
  _rotKeys() {
    const off = this._rotLoad().off;
    return TABS.map((t) => t[0]).filter((k) => k !== "config" && !off.includes(k));
  }
  _rotSchedule(ms) {
    clearTimeout(this._rotTimer);
    this._rotTimer = null;
    const r = this._rotLoad();
    if (!r.on || !this._built) return;
    this._rotTimer = setTimeout(() => this._rotTick(), ms ?? r.secs * 1000);
  }
  _rotTouched() {
    const r = this._rotLoad();
    if (r.on) this._rotSchedule(r.resume * 1000);
  }
  _rotTick() {
    this._rotTimer = null;
    const r = this._rotLoad();
    if (!r.on) return;
    const keys = this._rotKeys();
    const idle = !this._edit && this._tab !== "config" && Date.now() >= this._busy;
    if (idle && keys.length > 1) {
      const all = TABS.map((t) => t[0]);
      for (let step = 1; step <= all.length; step++) {
        const k = all[(all.indexOf(this._tab) + step) % all.length];
        if (keys.includes(k)) {
          this._go(k);
          break;
        }
      }
    }
    this._rotSchedule();
  }
  _rotUi() {
    const btn = this.shadowRoot?.querySelector(".rotbtn");
    if (!btn) return;
    const on = this._rotLoad().on;
    btn.classList.toggle("on", on);
    btn.title = on ? "Parar el cambio automático de pestañas" : "Cambiar de pestaña automáticamente (ajustes en Configuración)";
    btn.innerHTML = `${icon(on ? "mdi:pause-circle-outline" : "mdi:play-circle-outline")}<span>Rotar</span>`;
  }
  _rotAction(d) {
    const r = this._rotLoad();
    if (d.rot === "toggle") r.on = !r.on;
    else if (d.rot === "secs" && ROT_SECS.includes(Number(d.v))) r.secs = Number(d.v);
    else if (d.rot === "resume" && ROT_RESUME.includes(Number(d.v))) r.resume = Number(d.v);
    else if (d.rot === "tab" && TABS.some((t) => t[0] === d.v && d.v !== "config")) r.off = r.off.includes(d.v) ? r.off.filter((k) => k !== d.v) : [...r.off, d.v];
    else if (d.rot === "all") r.off = [];
    else if (d.rot === "none") r.off = TABS.map((t) => t[0]).filter((k) => k !== "config");
    this._rotSave();
    this._rotUi();
    this._rotSchedule();
    this._schedule(true);
  }

  // ---------------------------------------------------------------- helpers
  id(key) { return this.cfg.ids?.[key]; }
  st(e) { return e ? this._hass?.states?.[e] : undefined; }
  s(e) { return this.st(e)?.state; }
  n(e, d = null) { return toNum(this.s(e), d); }
  a(e, attr) { return this.st(e)?.attributes?.[attr]; }
  S(key) { return this.s(this.id(key)); }
  N(key, d = null) { return this.n(this.id(key), d); }
  A(key, attr) { return this.a(this.id(key), attr); }
  set_(k) { return this.cfg.settings?.[k]; }
  name(e) { return this.a(e, "friendly_name") || (e || "").split(".").pop(); }
  unit(e) { return this.a(e, "unit_of_measurement") || ""; }
  watts(e) {
    const v = this.n(e);
    if (v === null) return null;
    const u = this.unit(e);
    return u === "kW" ? v * 1000 : u === "MW" ? v * 1e6 : v;
  }
  get period() { return this.S("periodo") || "hoy"; }
  bucket(key, per = this.period) { return this.A(key, per); }

  // ---------------------------------------------------------------- cards
  card(k, html, { c = C.cyan, w = 12, click = null, cls = "" } = {}) {
    const span = w === 12 ? "" : `s${w}`;
    const attrs = click ? ` data-more="${esc(click)}"` : "";
    return { k, html, c, cls: `card ${span} ${click ? "click" : ""} ${cls}`.trim(), attrs };
  }
  title(k, text, sub, ic, c = C.cyan) {
    return { k, html: `<h2>${icon(ic)}${esc(text)}</h2>${sub ? `<p>${esc(sub)}</p>` : ""}`, c, cls: "title", attrs: "" };
  }
  kpi(k, entity, value, label, ic, c, w = 6, nav = null) {
    const html = `<div class="kpi"${nav ? ` data-tab="${nav}"` : ""}><div class="ic">${icon(ic)}</div><div><div class="v">${value}</div><div class="l">${label}</div></div></div>`;
    const card = this.card(k, html, { c, w, click: nav ? null : entity });
    if (nav) card.cls += " click";
    return card;
  }
  chartCard(k, title, c, spec, w = 12) {
    return { k, html: `<h3>${icon("mdi:chart-timeline-variant")}${esc(title)}</h3><div class="chart" data-chart="${esc(k)}"><div class="loading">Cargando historial…</div></div>`, c, cls: `card ${w === 12 ? "" : "s" + w}`, attrs: "", chart: spec };
  }
  empty(k, text) {
    return this.card(k, `<div class="empty">${icon("mdi:information-outline")} ${esc(text)}</div>`, { c: C.muted });
  }
  periodChips(k, c = C.cyan) {
    const per = this.period, sel = this.id("periodo");
    const chips = Object.entries(PERIODS).map(([v, l]) => `<button class="chip ${v === per ? "on" : ""}" data-select="${sel}" data-option="${v}">${l}</button>`).join("");
    return this.card(k, `<h3>${icon("mdi:calendar-range")}Periodo</h3><div class="chips">${chips}</div>`, { c });
  }

  // ---------------------------------------------------------------- render loop
  _schedule(force = false) {
    if (!this._built || !this._hass || !this.cfg) return;
    if (force) this._force = true;
    if (this._raf) return;
    const wait = this._force ? 0 : Math.max(0, 1000 - (Date.now() - this._last));
    this._raf = setTimeout(() => {
      this._raf = null;
      this._render();
    }, wait);
  }

  _render() {
    if (!this._hass || !this.cfg) return;
    if (!this._force && Date.now() < this._busy) {
      this._schedule();
      return;
    }
    this._force = false;
    this._last = Date.now();
    const root = this.shadowRoot;
    root.querySelector(".brand .t").textContent = this.cfg.title || "Centro de Control";
    const probs = this.A("problemas", "lista") || [];
    const crit = probs.filter((p) => p.nivel === "critico" && !p.reconocido).length;
    const warn = probs.filter((p) => p.nivel === "aviso" && !p.reconocido).length;
    root.querySelector("nav").innerHTML = TABS.map(([k, l, ic]) => {
      const badge = k === "problemas" && (crit || warn) ? `<span class="badge ${crit ? "" : "warn"}">${crit || warn}</span>` : "";
      return `<button class="${k === this._tab ? "on" : ""}" data-tab="${k}">${icon(ic)}${l}${badge}</button>`;
    }).join("");
    let sections;
    try {
      sections = this["v_" + this._tab]();
    } catch (err) {
      console.error("Centro de Control", err);
      sections = [{ cards: [this.empty("err", `Error al dibujar esta pestaña: ${err.message}`)] }];
    }
    sections = this._applyLayout(sections);
    if (this._edit)
      sections.unshift({ id: "_lay", cls: "wall", cards: [{ k: "_layinfo", html: `${icon("mdi:gesture-tap-hold")}<span>Modo diseño: mueve las secciones y las gráficas con las flechas y cambia su ancho con ⤢. Se guarda en este dispositivo (la tablet y el PC pueden tener su propio diseño).</span><span style="flex:1"></span><button data-lay="reset">${icon("mdi:restore")}Restablecer pestaña</button><button data-lay="toggle">${icon("mdi:check")}Listo</button>`, cls: "layinfo", attrs: "", c: C.amber }] });
    sections.push({ cls: "wall", cards: [{ k: "foot", html: "", cls: "foot", attrs: "", c: C.muted, foot: true }] });
    const layout = (this._edit ? "E" : "") + this._tab + "|" + sections.map((s) => (s.cls || "") + ":" + s.cards.map((c) => c.k + "/" + c.cls).join(",")).join(";");
    if (layout !== this._layoutKey) {
      this._layoutKey = layout;
      this._cards.clear();
      this._grid.innerHTML = sections
        .map((s) => `<div class="sec ${s.cls || ""}">${s.tools || ""}${s.cards.map((c) => `<div class="${c.cls}" style="--c:${c.c}" data-k="${esc(c.k)}"${c.attrs}></div>`).join("")}</div>`)
        .join("");
      this._grid.querySelectorAll("[data-k]").forEach((el) => this._cards.set(el.dataset.k, { el, html: null }));
    }
    for (const s of sections)
      for (const c of s.cards) {
        const slot = this._cards.get(c.k);
        if (!slot) continue;
        if (c.foot) {
          if (slot.html === null) {
            const cfg = this.cfg;
            slot.el.innerHTML = `${icon("mdi:atom-variant")} Centro de Control v${esc(cfg.version)} · creado por <a href="${esc(cfg.author_url)}" target="_blank">${esc(cfg.author)}</a> · <a href="${esc(cfg.repo_url)}" target="_blank">código</a>`;
            slot.html = "foot";
          }
          continue;
        }
        if (c.chart) {
          slot.spec = c.chart;
          if (slot.html === null) {
            slot.el.innerHTML = c.html;
            slot.html = c.html;
            this._drawChart(c.k, slot);
          }
          continue;
        }
        if (slot.html !== c.html) {
          if (slot.el.contains(this.shadowRoot.activeElement) && Date.now() < this._busy) continue;
          slot.el.innerHTML = c.html;
          slot.html = c.html;
        }
      }
  }

  // ---------------------------------------------------------------- layout (per device)
  _layLoad() {
    if (this._lay) return this._lay;
    try {
      this._lay = JSON.parse(localStorage.getItem("centro_control_diseno") || "{}") || {};
    } catch (e) {
      this._lay = {};
    }
    return this._lay;
  }
  _laySave() {
    try {
      localStorage.setItem("centro_control_diseno", JSON.stringify(this._lay || {}));
    } catch (e) {
      /* private mode: the layout lasts until the page is reloaded */
    }
  }
  _layTab() {
    const all = this._layLoad();
    return (all[this._tab] = all[this._tab] || { order: [], w: {}, cards: {}, cw: {} });
  }
  _applyLayout(sections) {
    const L = this._layTab();
    sections.forEach((s, i) => {
      s.id = s.id || (s.cards[0] && s.cards[0].k) || "s" + i;
      s._i = i;
      if (s.cards.length && s.cards.every((c) => c.chart) && s.cls !== "wall") s.cls = "charts";
    });
    const rank = (s) => (L.order.includes(s.id) ? L.order.indexOf(s.id) : s._i - 0.5);
    sections.sort((a, b) => rank(a) - rank(b) || a._i - b._i);
    const WIDTHS = { "1": "", "2": "w2", "3": "w3", all: "wall" };
    this._secIds = sections.map((s) => s.id);
    this._cardIds = {};
    sections.forEach((s, si) => {
      if (L.w[s.id] !== undefined) s.cls = WIDTHS[L.w[s.id]] ?? s.cls;
      const order = L.cards[s.id] || [];
      const cr = (c, i) => (order.includes(c.k) ? order.indexOf(c.k) : i - 0.5);
      const idx = new Map(s.cards.map((c, i) => [c, i]));
      s.cards.sort((a, b) => cr(a, idx.get(a)) - cr(b, idx.get(b)) || idx.get(a) - idx.get(b));
      this._cardIds[s.id] = s.cards.map((c) => c.k);
      for (const c of s.cards) {
        const w = L.cw[c.k];
        if (w) c.cls = c.cls.replace(/\bu\d+\b/g, "") + " u" + w;
        if (this._edit && !c.foot && c.cls.split(" ").includes("card")) {
          const tools = `<div class="lay"><button data-lay="card-prev" data-sec="${esc(s.id)}" data-id="${esc(c.k)}" title="Antes">◀</button><button data-lay="card-next" data-sec="${esc(s.id)}" data-id="${esc(c.k)}" title="Después">▶</button><button data-lay="card-w" data-id="${esc(c.k)}" title="Ancho">⤢</button></div>`;
          c.html += tools;
        }
      }
      if (this._edit) {
        const wl = { "": "1 col", w2: "2 col", w3: "3 col", wall: "completa", charts: "gráficas" }[s.cls || ""] || "";
        s.tools = `<div class="lay sl">S${si + 1} · ${wl}</div><div class="lay"><button data-lay="sec-prev" data-id="${esc(s.id)}" title="Mover antes">◀</button><button data-lay="sec-next" data-id="${esc(s.id)}" title="Mover después">▶</button><button data-lay="sec-w" data-id="${esc(s.id)}" title="Ancho de la sección">⤢ Ancho</button></div>`;
      }
    });
    return sections;
  }
  _layAction(d) {
    const L = this._layTab();
    const move = (list, id, delta) => {
      const i = list.indexOf(id), j = i + delta;
      if (i < 0 || j < 0 || j >= list.length) return null;
      [list[i], list[j]] = [list[j], list[i]];
      return list;
    };
    if (d.lay === "toggle") {
      this._edit = !this._edit;
      this.shadowRoot.querySelector("main").classList.toggle("edit", this._edit);
      this.shadowRoot.querySelector(".laybtn").classList.toggle("on", this._edit);
    } else if (d.lay === "reset") {
      delete this._layLoad()[this._tab];
    } else if (d.lay === "sec-prev" || d.lay === "sec-next") {
      const list = move([...this._secIds], d.id, d.lay === "sec-prev" ? -1 : 1);
      if (list) L.order = list;
    } else if (d.lay === "card-prev" || d.lay === "card-next") {
      const list = move([...(this._cardIds[d.sec] || [])], d.id, d.lay === "card-prev" ? -1 : 1);
      if (list) L.cards[d.sec] = list;
    } else if (d.lay === "sec-w") {
      const seq = ["1", "2", "3", "all"];
      const el = this._grid.querySelector(`[data-k="${window.CSS.escape(d.id)}"]`)?.parentElement;
      const cur = L.w[d.id] ?? (el?.classList.contains("wall") || el?.classList.contains("charts") ? "all" : el?.classList.contains("w3") ? "3" : el?.classList.contains("w2") ? "2" : "1");
      L.w[d.id] = seq[(seq.indexOf(cur) + 1) % seq.length];
    } else if (d.lay === "card-w") {
      const seq = [12, 6, 4, 3];
      const el = this._grid.querySelector(`[data-k="${window.CSS.escape(d.id)}"]`);
      const span = el ? Math.round(el.getBoundingClientRect().width / Math.max(1, el.parentElement.getBoundingClientRect().width) * 12) : 12;
      const cur = L.cw[d.id] || seq.reduce((a, b) => (Math.abs(b - span) < Math.abs(a - span) ? b : a));
      L.cw[d.id] = seq[(seq.indexOf(cur) + 1) % seq.length];
    }
    this._laySave();
    this._layoutKey = "";
    this._schedule(true);
  }

  _go(tab) {
    this._tab = tab;
    history.replaceState(null, "", "#" + tab);
    this._layoutKey = "";
    this._schedule(true);
    window.scrollTo({ top: 0 });
  }

  // ---------------------------------------------------------------- events
  _fire(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
  }
  _click(e) {
    const lay = e.target.closest("[data-lay]");
    if (lay) {
      e.stopPropagation();
      return this._layAction(lay.dataset);
    }
    const rot = e.target.closest("[data-rot]");
    if (rot) {
      e.stopPropagation();
      return this._rotAction(rot.dataset);
    }
    const mm = e.target.closest("[data-manmode]");
    if (mm) {
      e.stopPropagation();
      const man = this._manLoad();
      man.on = mm.dataset.manmode === "manual";
      if (man.on && man.soc === null) {
        const t = Number(this.A("recomendacion_carga_red", "soc_objetivo"));
        man.soc = Number.isFinite(t) ? Math.round(t) : 60;
      }
      this._manSave();
      return this._schedule(true);
    }
    const adv = e.target.closest("[data-adv]");
    if (adv) {
      e.stopPropagation();
      return this._applyAdvice(adv.dataset.adv);
    }
    if (this._edit && !e.target.closest("nav")) return;
    const t = e.target.closest("[data-set],[data-tab],[data-more],[data-toggle],[data-press],[data-select],[data-service],[data-temp]");
    if (!t) return;
    const d = t.dataset;
    if (d.set !== undefined && d.flag !== undefined) return this._flagSet(d.set, d.flag === "on");
    if (d.set !== undefined && d.val !== undefined) return this._write(d.set, d.val);
    if (d.tab) return this._go(d.tab);
    if (d.select) return this._hass.callService("select", "select_option", { entity_id: d.select, option: d.option });
    if (d.press) {
      if (d.confirm && !confirm(d.confirm)) return;
      return this._hass.callService("button", "press", { entity_id: d.press });
    }
    if (d.toggle) {
      const domain = d.toggle.split(".")[0];
      return this._hass.callService(["light", "switch", "input_boolean", "fan", "valve"].includes(domain) ? domain : "homeassistant", "toggle", { entity_id: d.toggle });
    }
    if (d.temp) {
      const cur = toNum(this.a(d.temp, "temperature"), 20);
      return this._hass.callService("climate", "set_temperature", { entity_id: d.temp, temperature: Math.round((cur + Number(d.delta)) * 2) / 2 });
    }
    if (d.service) {
      const [domain, service] = d.service.split(".");
      return this._hass.callService(domain, service, JSON.parse(d.data || "{}"));
    }
    if (d.more) return this._fire("hass-more-info", { entityId: d.more });
  }
  _change(e) {
    const t = e.target;
    this._busy = Date.now() + 1500;
    if (t.dataset.manin) {
      const man = this._manLoad(), v = Number(t.value);
      if (Number.isFinite(v)) man.soc = Math.max(Number(t.min) || 0, Math.min(Number(t.max) || 100, Math.round(v)));
      this._manSave();
      this._schedule(true);
    } else if (t.dataset.set) {
      this._write(t.dataset.set, t.value);
    } else if (t.dataset.number) {
      this._hass.callService("number", "set_value", { entity_id: t.dataset.number, value: Number(t.value) });
    } else if (t.dataset.bright) {
      this._hass.callService("light", "turn_on", { entity_id: t.dataset.bright, brightness_pct: Number(t.value) });
    }
  }

  // ---------------------------------------------------------------- history
  async _history(ids, hours) {
    const key = ids.join(",") + "|" + hours;
    const hit = this._cache[key];
    if (hit && Date.now() - hit.t < 55000) return hit.data;
    const end = new Date(), start = new Date(end - hours * 3600000);
    const data = await this._hass.callWS({
      type: "history/history_during_period",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      entity_ids: ids,
      minimal_response: true,
      no_attributes: true,
      significant_changes_only: false,
    });
    this._cache[key] = { t: Date.now(), data };
    return data;
  }
  _points(hist, entity, { scale = 1, transform = null, bucketMin = 5 } = {}) {
    const rows = hist?.[entity] || [];
    const unit = this.unit(entity);
    const k = unit === "kW" ? 1000 : 1;
    const out = [];
    let lastBucket = null, acc = 0, cnt = 0;
    for (const r of rows) {
      const v = toNum(r.s);
      const t = (r.lu ?? r.lc ?? 0) * 1000;
      if (v === null || !t) continue;
      let val = v * k * scale;
      if (transform) val = transform(val);
      const b = Math.floor(t / (bucketMin * 60000));
      if (lastBucket !== null && b !== lastBucket) {
        out.push([lastBucket * bucketMin * 60000, acc / cnt]);
        acc = 0;
        cnt = 0;
      }
      lastBucket = b;
      acc += val;
      cnt += 1;
    }
    if (cnt) out.push([lastBucket * bucketMin * 60000, acc / cnt]);
    if (out.length) out.push([Date.now(), out[out.length - 1][1]]);
    return out;
  }
  /** max − min of several entities over time (e.g. the SOC gap between batteries). */
  _spread(hist, ents, bucketMin) {
    const lines = ents.map((e) => this._points(hist, e, { bucketMin }));
    const times = [...new Set(lines.flatMap((l) => l.map((p) => p[0])))].sort((a, b) => a - b);
    const pos = lines.map(() => 0), cur = lines.map(() => null), out = [];
    for (const t of times) {
      lines.forEach((l, i) => {
        while (pos[i] < l.length && l[pos[i]][0] <= t) cur[i] = l[pos[i]++][1];
      });
      if (cur.every((v) => v !== null)) out.push([t, Math.max(...cur) - Math.min(...cur)]);
    }
    return out;
  }
  _refreshCharts() {
    for (const [k, slot] of this._cards) if (slot.spec) this._drawChart(k, slot);
  }
  async _drawChart(k, slot) {
    const spec = slot.spec;
    const el = slot.el.querySelector(".chart");
    if (!el) return;
    try {
      let series, opt;
      if (spec.kind === "history") {
        const ids = [...new Set(spec.series.flatMap((s) => (s.spread ? s.spread : [s.entity])).filter(Boolean))];
        const hist = ids.length ? await this._history(ids, spec.hours || 24) : {};
        series = spec.series.map((s, i) => ({
          name: s.name,
          color: s.color || PALETTE[i % PALETTE.length],
          type: s.type || "line",
          step: s.step,
          points: s.spread ? this._spread(hist, s.spread, spec.bucket || 5) : this._points(hist, s.entity, { scale: s.scale || 1, transform: s.abs ? Math.abs : s.pos ? (v) => Math.max(v, 0) : s.neg ? (v) => Math.max(-v, 0) : null, bucketMin: spec.bucket || 5 }),
        }));
        const end = Date.now();
        opt = { start: end - (spec.hours || 24) * 3600000, end, unit: spec.unit, height: spec.height, min: spec.min, max: spec.max };
      } else if (spec.kind === "days" || spec.kind === "months") {
        const rows = this.A("historico", spec.kind === "days" ? "dias" : "meses") || [];
        const field = spec.kind === "days" ? "fecha" : "mes";
        const pick = rows.slice(-(spec.count || (spec.kind === "days" ? 30 : 12)));
        const tt = (r) => new Date(spec.kind === "days" ? r[field] + "T12:00:00" : r[field] + "-15T12:00:00").getTime();
        series = spec.series.map((s, i) => ({ name: s.name, color: s.color || PALETTE[i], type: "bar", points: pick.map((r) => [tt(r), toNum(r[s.field], 0)]) }));
        const first = pick.length ? tt(pick[0]) : Date.now(), last = pick.length ? tt(pick[pick.length - 1]) : Date.now();
        const half = spec.kind === "days" ? 43200000 : 15 * 86400000;
        opt = { start: first - half, end: last + half, unit: spec.unit, slots: pick.length || 1, height: spec.height, stacked: spec.stacked };
      } else if (spec.kind === "points") {
        series = spec.series;
        opt = spec.opt;
      }
      if (!series.some((s) => s.points.length)) {
        el.innerHTML = `<div class="loading">Todavía no hay datos para esta gráfica.</div>`;
        return;
      }
      drawChart(el, series, opt);
    } catch (err) {
      el.innerHTML = `<div class="loading">No se pudo leer el historial (${esc(err.message || err)}).</div>`;
    }
  }

  // ================================================================ views
  live() {
    return {
      pv: this.N("potencia_solar"),
      grid: this.N("potencia_red"),
      bat: this.N("potencia_bateria"),
      load: this.N("potencia_consumo"),
      soc: this.N("soc_bateria"),
    };
  }

  flowSVG() {
    const { pv, grid, bat, load, soc } = this.live();
    const P = Math.max(pv || 0, 0), G = grid || 0, B = bat || 0, H = Math.max(load || 0, 0);
    const hasPV = (this.cfg.strings || []).length || this.set_("solar_potencia");
    const hasBat = (this.cfg.batteries || []).length > 0;
    const sToH = Math.min(P, H), rest = Math.max(P - sToH, 0);
    const sToB = Math.min(rest, Math.max(-B, 0));
    const sToG = Math.max(-G, 0);
    const gToB = G > 0 ? Math.max(Math.max(-B, 0) - sToB, 0) : 0;
    const bToH = Math.max(B, 0), gToH = Math.max(Math.max(G, 0) - gToB, 0);
    const nodes = { solar: [300, 80], grid: [90, 210], bat: [510, 210], home: [300, 300] };
    const line = (a, b, w, color, rev = false) => {
      if (!(w > 15)) return `<path d="M${a[0]},${a[1]} L${b[0]},${b[1]}" stroke="#14233b" stroke-width="2" fill="none"/>`;
      const dur = Math.max(0.35, 3 - Math.log10(w) * 0.75);
      const [p, q] = rev ? [b, a] : [a, b];
      return `<path d="M${a[0]},${a[1]} L${b[0]},${b[1]}" stroke="#14233b" stroke-width="2" fill="none"/><path class="ln" style="--d:${dur}s;stroke:${color};stroke-width:${1.5 + Math.min(w / 1500, 3)}px;filter:drop-shadow(0 0 4px ${color})" d="M${p[0]},${p[1]} L${q[0]},${q[1]}"/>`;
    };
    const node = (key, [x, y], color, ic, value, label, entity) => `
      <g class="node" data-more="${esc(entity || "")}" style="cursor:pointer;--c:${color}">
        <circle class="ring" cx="${x}" cy="${y}" r="44" fill="#06101f" stroke="${color}" stroke-width="3"/>
        <foreignObject x="${x - 14}" y="${y - 32}" width="28" height="28"><div xmlns="http://www.w3.org/1999/xhtml" style="color:${color};display:flex;justify-content:center">${icon(ic)}</div></foreignObject>
        <text x="${x}" y="${y + 10}" text-anchor="middle" fill="${C.text}" font-size="15" font-weight="800">${value}</text>
        <text x="${x}" y="${key === "solar" ? y - 54 : y + 66}" text-anchor="middle" fill="${C.muted}" font-size="12.5">${label}</text>
      </g>`;
    let svg = `<svg class="flow" viewBox="0 0 600 380" style="width:100%;max-height:420px">`;
    if (hasPV) svg += line(nodes.solar, nodes.home, sToH, C.amber) + line(nodes.solar, nodes.grid, sToG, C.amber) + (hasBat ? line(nodes.solar, nodes.bat, sToB, C.amber) : "");
    svg += line(nodes.grid, nodes.home, gToH, C.cyan);
    if (hasBat) svg += line(nodes.bat, nodes.home, bToH, C.green) + line(nodes.grid, nodes.bat, gToB, C.cyan);
    if (hasPV) svg += node("solar", nodes.solar, C.amber, "mdi:solar-power-variant", fmtW(P), "Solar", this.id("potencia_solar"));
    svg += node("grid", nodes.grid, C.cyan, "mdi:transmission-tower", fmtW(Math.abs(G)), G > 15 ? "Red · importando" : G < -15 ? "Red · vertiendo" : "Red", this.id("potencia_red"));
    if (hasBat) svg += node("bat", nodes.bat, C.green, "mdi:home-battery", fmtW(Math.abs(B)), `Batería ${soc === null ? "" : fmt(soc, 0) + " %"} ${B > 15 ? "↑" : B < -15 ? "↓" : ""}`, this.id("potencia_bateria"));
    svg += node("home", nodes.home, C.pink, "mdi:home-lightning-bolt", fmtW(H), "Casa", this.id("potencia_consumo"));
    svg += `</svg>`;
    const circuits = (this.A("potencia_consumo", "circuitos") || []).filter((c) => c.en_total !== false && isNum(c.w)).slice(0, 6);
    const chips = circuits.map((c, i) => `<span class="chip" data-more="${esc((this.cfg.circuits || []).find((x) => x.id === c.id)?.power || "")}" style="border-color:${PALETTE[(i + 1) % PALETTE.length]};color:${PALETTE[(i + 1) % PALETTE.length]}">${icon(c.icono || "mdi:flash")} ${esc(c.nombre)} · ${fmtW(c.w)}</span>`).join("");
    return svg + (chips ? `<div class="chips" style="justify-content:center;margin-top:4px">${chips}</div>` : "");
  }

  sources24h() {
    const s = (k) => this.set_(k);
    const inv = s("red_signo") === "positivo_exporta";
    const series = [];
    series.push({ name: "Solar", color: C.amber, type: "area", entity: s("solar_potencia") || this.id("potencia_solar") });
    series.push({ name: "Consumo", color: C.pink, entity: s("consumo_potencia") || this.id("potencia_consumo") });
    series.push({ name: "Red", color: C.cyan, entity: s("red_potencia") || this.id("potencia_red"), scale: s("red_potencia") && inv ? -1 : 1 });
    const bats = this.cfg.batteries || [];
    if (bats.length === 1) series.push({ name: "Batería", color: C.green, entity: bats[0].power, scale: bats[0].positive_charge ? -1 : 1 });
    else if (bats.length) series.push({ name: "Batería", color: C.green, entity: this.id("potencia_bateria") });
    return series;
  }

  problemsHTML(list, max = 99) {
    if (!list.length) return `<div class="alert" style="--a:${C.green}"><b>Todo en orden.</b> No se ha detectado ningún problema.</div>`;
    const col = { critico: C.red, aviso: C.amber, info: C.blue };
    const more = list.length > max ? `<div class="muted small">… y ${list.length - max} más</div>` : "";
    return list.slice(0, max).map((p) => `<div class="alert" style="--a:${col[p.nivel] || C.blue}"${p.entidad ? ` data-more="${esc(p.entidad)}"` : ""}><b>${esc(p.titulo)}${p.reconocido ? " ✓" : ""}</b><br>${esc(p.detalle)}<div class="when">${esc(p.area)} · desde ${fmtDate(p.desde, true)}</div></div>`).join("") + more;
  }

  // ---------------------------------------------------------------- 1 resumen
  v_resumen() {
    const { pv, grid, bat, load, soc } = this.live();
    const per = this.period;
    const probs = this.A("problemas", "lista") || [];
    const crit = probs.filter((p) => p.nivel === "critico").length, warn = probs.filter((p) => p.nivel === "aviso").length;
    const status = crit ? `<span class="pulse" style="color:${C.red}">◉ ${crit} crítico${crit > 1 ? "s" : ""}</span>` : warn ? `<span style="color:${C.amber}">◉ ${warn} aviso${warn > 1 ? "s" : ""}</span>` : `<span style="color:${C.green}">◉ Todo en orden</span>`;
    const now = new Date();
    const head = this.card("head", `<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap"><div><div class="muted small">${now.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" })} · periodo ${esc(this.S("periodo_tarifario") || "—")} · ${fmt(this.N("precio_actual"), 4)} €/kWh</div><div style="margin-top:4px;font-size:14px">${status}</div></div><div style="text-align:right"><div class="muted small">Autosuficiencia ahora</div><div class="big" style="--c:${C.lime}">${fmt(this.N("autosuficiencia_ahora"), 0)} %</div></div></div>`, { c: C.cyan });
    const flow = this.card("flow", this.flowSVG(), { c: C.cyan });
    const kp = [
      this.kpi("k1", null, fmtW(pv), `Solar · ${kwh(this.N("energia_solar"))} hoy`, "mdi:solar-power-variant", C.amber, 6, "solar"),
      this.kpi("k2", null, fmtW(load), `Consumo · ${kwh(this.N("energia_consumo"))} hoy`, "mdi:home-lightning-bolt", C.pink, 6, "consumos"),
      this.kpi("k3", null, `${fmtW(Math.abs(grid ?? 0))} ${grid > 15 ? "↓" : grid < -15 ? "↑" : ""}`, grid > 15 ? "Importando de la red" : grid < -15 ? "Vertiendo a la red" : "Red en reposo", "mdi:transmission-tower", C.cyan, 6, "red"),
    ];
    if ((this.cfg.batteries || []).length) {
      const d = (this.cfg.soc_pair || []).length >= 2 ? this.N("diferencia_soc") : null;
      const dTxt = d === null ? "" : ` · <span style="color:${this.socDiffColor(d)}">Δ ${fmt(d, 0)} %</span>`;
      kp.push(this.kpi("k4", null, `${fmt(soc, 0)} %`, `Batería · ${bat > 30 ? "descargando " + fmtW(bat) : bat < -30 ? "cargando " + fmtW(-bat) : "en reposo"}${dTxt}`, "mdi:home-battery", C.green, 6, "bateria"));
    }
    kp.push(this.kpi("k5", null, eur(this.N("coste_energia")), `Luz hoy · ahorro solar ${eur(this.A("ahorro_solar", "hoy"))}`, "mdi:currency-eur", C.gold, 6, "coste"));
    const gasCost = this.cfg.gas?.coste_hoy;
    kp.push(this.kpi("k6", null, gasCost ? eur(this.n(gasCost)) : `${fmt(this.N("co2_evitado"), 1)} kg`, gasCost ? `Gas hoy · ${fmt(this.N("consumo_gas"), 2)} m³` : "CO₂ evitado hoy", gasCost ? "mdi:fire" : "mdi:leaf", gasCost ? C.violet : C.lime, 6, gasCost ? "gas" : "co2"));
    const row = (c, ic, l, v) => `<tr><td style="color:${c}">${icon(ic)} ${l}</td><td class="r"><b>${v}</b></td></tr>`;
    const co2 = this.bucket("co2_evitado") || {};
    const sum = this.card("sum", `<h3>${icon("mdi:chart-donut-variant")}${PERIODS[per]}</h3><table>
      ${row(C.amber, "mdi:solar-power-variant", "Producción", kwh(this.bucket("energia_solar"), 2))}
      ${row(C.pink, "mdi:home-lightning-bolt", "Consumo", kwh(this.bucket("energia_consumo"), 2))}
      ${row(C.cyan, "mdi:transmission-tower-import", "Importado", kwh(this.bucket("energia_importada"), 2))}
      ${row(C.cyan, "mdi:transmission-tower-export", "Vertido", kwh(this.bucket("energia_exportada"), 2))}
      ${row(C.gold, "mdi:currency-eur", "Coste de la luz", eur(this.bucket("coste_energia")))}
      ${row(C.lime, "mdi:piggy-bank-outline", "Ahorro solar", eur(this.bucket("ahorro_solar")))}
      ${row(C.lime, "mdi:leaf", "CO₂ evitado", `${fmt(co2.evitado_kg, 1)} kg`)}</table>`, { c: C.cyan });
    const alerts = this.card("alerts", `<h3>${icon("mdi:alert-decagram")}Alertas</h3>${this.problemsHTML(probs, 3)}`, { c: probs.length ? (crit ? C.red : C.amber) : C.green });
    alerts.cls += " click";
    alerts.attrs = ` data-tab="problemas"`;
    return [
      { cls: "w2", cards: [head, flow] },
      { cards: [...kp, this.periodChips("per"), sum] },
      { cards: [alerts, this.chartCard("c24", "Últimas 24 h (W)", C.cyan, { kind: "history", hours: 24, unit: "W", series: this.sources24h(), height: 240 })] },
    ];
  }

  // ---------------------------------------------------------------- 2 red
  v_red() {
    const imp = this.N("potencia_importada"), exp = this.N("potencia_exportada");
    const use = this.N("uso_potencia_contratada");
    const cards = [
      this.title("t", "Red eléctrica", "Importación, vertido y potencia contratada", "mdi:transmission-tower", C.cyan),
      this.card("g", gauge(use, 0, 100, use > 90 ? C.red : use > 75 ? C.amber : C.cyan, `de ${fmt(this.A("uso_potencia_contratada", "contratada_kw"), 2)} kW contratados`, "% potencia"), { c: C.cyan, w: 6, click: this.id("uso_potencia_contratada") }),
      this.kpi("i", this.id("potencia_importada"), fmtW(imp), "Importando", "mdi:transmission-tower-import", C.cyan, 6),
      this.kpi("e", this.id("potencia_exportada"), fmtW(exp), "Vertiendo", "mdi:transmission-tower-export", C.lime, 6),
      this.kpi("p", this.id("precio_actual"), `${fmt(this.N("precio_actual"), 4)} €/kWh`, `Periodo ${esc(this.S("periodo_tarifario") || "—")} · excedentes ${fmt(this.N("precio_excedentes"), 4)} €/kWh`, "mdi:cash-clock", C.gold, 12),
    ];
    for (const [k, l, ic, u] of [["red_tension", "Tensión", "mdi:sine-wave", "V"], ["red_frecuencia", "Frecuencia", "mdi:waveform", "Hz"]]) {
      const e = this.set_(k);
      if (e) cards.push(this.kpi(k, e, `${fmt(this.n(e), k === "red_tension" ? 1 : 2)} ${u}`, l, ic, C.cyan, 6));
    }
    const per = this.period;
    const energy = this.card("en", `<h3>${icon("mdi:counter")}${PERIODS[per]}</h3><table><tr><th></th><th class="r">Importado</th><th class="r">Vertido</th></tr>
      <tr><td>Energía</td><td class="r"><b>${kwh(this.bucket("energia_importada"), 2)}</b></td><td class="r"><b>${kwh(this.bucket("energia_exportada"), 2)}</b></td></tr>
      <tr><td>Importe</td><td class="r">${eur(this.bucket("coste_energia"))}</td><td class="r">${eur(this.bucket("compensacion_excedentes"))}</td></tr></table>`, { c: C.cyan });
    const charts = [];
    const priceSensor = this.set_("precio_modo") === "sensor" ? this.set_("precio_sensor") : null;
    if (priceSensor && this.a(priceSensor, "price_00h") !== undefined) {
      const d = new Date(); d.setHours(0, 0, 0, 0);
      const pts = [];
      for (let h = 0; h < 48; h++) {
        const key = h < 24 ? `price_${String(h).padStart(2, "0")}h` : `price_next_day_${String(h - 24).padStart(2, "0")}h`;
        const v = this.a(priceSensor, key);
        if (isNum(v)) pts.push([d.getTime() + h * 3600000 + 1800000, Number(v)]);
      }
      charts.push({ k: "price", html: `<h3>${icon("mdi:cash-clock")}Precio hoy y mañana (€/kWh)</h3><div class="chart" data-chart="price"></div>`, c: C.gold, cls: "card", attrs: "", chart: { kind: "points", series: [{ name: "Precio", color: C.gold, type: "bar", points: pts }], opt: { start: d.getTime(), end: d.getTime() + 48 * 3600000, slots: 48, unit: "€/kWh", decimals: 4 } } });
    }
    const inv = this.set_("red_signo") === "positivo_exporta";
    const ge = this.set_("red_potencia") || this.id("potencia_red");
    charts.push(this.chartCard("g24", "Red 24 h (W)", C.cyan, { kind: "history", hours: 24, unit: "W", series: [{ name: "Importado", color: C.cyan, type: "area", entity: ge, scale: inv ? -1 : 1, pos: true }, { name: "Vertido", color: C.lime, type: "area", entity: ge, scale: inv ? -1 : 1, neg: true }] }));
    charts.push(this.chartCard("g30", "Últimos 30 días (kWh)", C.cyan, { kind: "days", unit: "kWh", series: [{ name: "Importado", field: "importada", color: C.cyan }, { name: "Vertido", field: "exportada", color: C.lime }] }));
    return [{ cards }, { cards: [this.periodChips("per"), energy] }, { cls: "w2", cards: charts }];
  }

  // ---------------------------------------------------------------- 3 solar
  v_solar() {
    const strings = this.cfg.strings || [];
    if (!strings.length && !this.set_("solar_potencia")) return [{ cards: [this.title("t", "Solar", "", "mdi:solar-power-variant", C.amber), this.empty("e", "Añade la potencia solar en Configurar → Solar, o cada string con «Añadir string».")] }];
    const peak = Number(this.set_("solar_pico_wp")) || strings.reduce((a, s) => a + (Number(s.peak_wp) || 0), 0) || 5000;
    const pv = this.N("potencia_solar");
    const head = [
      this.title("t", "Paneles solares", "Producción, strings e inversor", "mdi:solar-power-variant", C.amber),
      this.card("g", gauge(pv, 0, peak, C.amber, `de ${fmt(peak, 0)} Wp`, "W"), { c: C.amber, w: 6, click: this.id("potencia_solar") }),
      this.kpi("hoy", this.id("energia_solar"), kwh(this.N("energia_solar"), 2), `Hoy · mes ${kwh(this.A("energia_solar", "mes"), 0)} · año ${kwh(this.A("energia_solar", "ano"), 0)}`, "mdi:solar-power-variant-outline", C.amber, 6),
      this.kpi("ac", this.id("autoconsumo"), `${fmt(this.N("autoconsumo"), 0)} %`, `Autoconsumo hoy · mes ${fmt(this.A("autoconsumo", "mes"), 0)} %`, "mdi:home-import-outline", C.lime, 6),
    ];
    const fc = this.set_("solar_prevision_hoy");
    if (fc) head.push(this.kpi("fc", fc, kwh(this.n(fc)), `Previsión hoy · llevas el ${fmt((100 * (this.N("energia_solar") || 0)) / Math.max(this.n(fc) || 0, 0.01), 0)} %`, "mdi:weather-sunny-alert", C.amber, 6));
    const live = this.A("potencia_solar", "strings") || [];
    const maxY = Math.max(1, ...live.map((s) => (s.wp && s.w ? (1000 * s.w) / s.wp : 0)));
    const st = strings.map((s) => {
      const l = live.find((x) => x.id === s.id) || {};
      const w = this.watts(s.power);
      const extra = [s.voltage ? `${fmt(this.n(s.voltage), 0)} V` : "", s.current ? `${fmt(this.n(s.current), 1)} A` : "", s.peak_wp ? `${fmt((100 * (w || 0)) / s.peak_wp, 0)} % de ${fmt(s.peak_wp, 0)} Wp` : ""].filter(Boolean).join(" · ");
      const spec = s.peak_wp && w !== null ? (1000 * w) / s.peak_wp : null;
      return this.card("s" + s.id, `<div class="kpi"><div class="ic">${icon("mdi:solar-panel")}</div><div style="flex:1"><div class="v">${fmtW(w)}</div><div class="l">${esc(s.name)} · ${kwh(this.N(s.id + ":energia_string"), 2)} hoy${extra ? " · " + extra : ""}</div>${spec !== null ? `<div class="bar" style="margin-top:6px"><i style="width:${Math.min(100, (100 * spec) / maxY)}%"></i></div><div class="small muted" style="margin-top:3px">${fmt(spec, 0)} W/kWp</div>` : ""}</div></div>`, { c: C.amber, w: 6, click: s.power });
    });
    const inv = [];
    for (const [k, l] of [["inversor_temperatura", "Inversor"], ["inversor_temperatura_dc", "Inversor DC"]]) {
      const e = this.set_(k);
      if (e) {
        const t = this.n(e);
        inv.push(this.card(k, gauge(t, 0, 80, t > 60 ? C.red : t > 45 ? C.orange : C.green, l, "°C", 130), { c: C.orange, w: 6, click: e }));
      }
    }
    for (const [k, l] of [["inversor_estado", "Estado"], ["inversor_fallo", "Fallo"], ["inversor_alarma", "Alarma"]]) {
      const e = this.set_(k);
      if (e) inv.push(this.kpi(k, e, esc(this.s(e) ?? "—"), l, "mdi:information-outline", C.orange, 6));
    }
    const charts = [];
    if (strings.length) charts.push(this.chartCard("st24", "Strings 24 h (W)", C.amber, { kind: "history", hours: 24, unit: "W", series: strings.map((s, i) => ({ name: s.name, entity: s.power, color: PALETTE[i % PALETTE.length] })) }));
    charts.push(this.chartCard("p30", "Producción 30 días (kWh)", C.amber, { kind: "days", unit: "kWh", series: [{ name: "Solar", field: "solar", color: C.amber }] }));
    charts.push(this.chartCard("p12", "Producción por meses (kWh)", C.amber, { kind: "months", unit: "kWh", count: 12, series: [{ name: "Solar", field: "solar", color: C.amber }] }));
    const deye = this.deyeCards();
    return [
      { cards: head },
      { cards: [this.title("ts", "Strings", "", "mdi:solar-panel", C.amber), ...st, ...(inv.length ? [this.title("ti", "Inversor", "", "mdi:power-plug-battery", C.orange), ...inv] : [])] },
      { id: "plan", cls: "w2", cards: this.adviceCards() },
      { id: "deye", cls: deye.length > 1 ? "w3" : "", cards: deye },
      { cls: "w2", cards: charts },
    ];
  }

  // ---------------------------------------------------------------- inverter control (Deye) and cloud cover
  _write(entity, value) {
    const st = this.st(entity);
    if (!st) return;
    const d = entity.split(".")[0];
    const call = (domain, service, data) => this._hass.callService(domain, service, { entity_id: entity, ...data });
    this._busy = Date.now() + 1500;
    if (d === "number" || d === "input_number") {
      let v = Number(value);
      if (!Number.isFinite(v)) return;
      const a = st.attributes;
      if (a.min !== undefined) v = Math.max(Number(a.min), v);
      if (a.max !== undefined) v = Math.min(Number(a.max), v);
      if (entity === this.set_("deye_corriente_carga_red")) {
        const cap = this._gridCap();
        if (cap) v = Math.min(cap.amps, v); // never above the contracted power
      }
      return call(d, "set_value", { value: v });
    }
    if (d === "time") return call("time", "set_value", { time: String(value).length === 5 ? value + ":00" : value });
    if (d === "input_datetime") return call("input_datetime", "set_datetime", { time: String(value).length === 5 ? value + ":00" : value });
    if (d === "text") return call("text", "set_value", { value: String(value).slice(0, 5) });
    if (d === "select" || d === "input_select") return call(d, "select_option", { option: String(value) });
    if (d === "switch" || d === "input_boolean") return call(d, value === true || value === "true" || value === "on" ? "turn_on" : "turn_off", {});
  }
  /** Battery voltage (bank first); falls back to a 16S LiFePO4 nominal 51.2 V. */
  _batVolt() {
    const bs = (this.cfg.batteries || []).slice().sort((a, b) => (b.in_total ? 1 : 0) - (a.in_total ? 1 : 0));
    for (const b of bs) {
      const v = b.voltage ? toNum(this.s(b.voltage), NaN) : NaN;
      if (v >= 20 && v <= 120) return { v, nominal: false };
    }
    return { v: 51.2, nominal: true };
  }
  /** Highest grid-charge current (A) that keeps the grid draw within the contracted power: contracted minus what the house consumes right now. */
  _gridCap() {
    const kw = toNum(this.A("uso_potencia_contratada", "contratada_kw"), NaN);
    if (!(kw > 0)) return null;
    const { v, nominal } = this._batVolt();
    const loadEntity = this.set_("consumo_potencia");
    const load = loadEntity ? Math.max(0, this.watts(loadEntity) || 0) : 0;
    const avail = Math.max(0, kw * 1000 - load);
    return { amps: Math.floor(avail / v), watts: avail, load, contracted: kw * 1000, volt: v, nominal, kw };
  }
  _gridOpt(o) { return /(grid|red|both|ambos)/i.test(o) && !/^\s*(no|none|ning|sin|off|disable)/i.test(o); }
  _offOpt(o) { return /^\s*(no|none|ning|sin|off|disable)/i.test(o); }
  /** Is "charge from the grid" on for a program (select with a grid option, or a switch)? */
  _chargeOn(entity) {
    const st = this.s(entity);
    return entity.startsWith("select.") || entity.startsWith("input_select.") ? this._gridOpt(st || "") : st === "on";
  }
  _chargeSet(entity, on) {
    if (entity.startsWith("select.") || entity.startsWith("input_select.")) {
      const opts = this.a(entity, "options") || [];
      const opt = on ? opts.find((o) => /^\s*(grid|red)\s*$/i.test(o)) ?? opts.find((o) => this._gridOpt(o)) : opts.find((o) => this._offOpt(o));
      if (opt) this._write(entity, opt);
    } else this._write(entity, on);
  }
  /** On/off of a flag that can be a switch or a select (Enabled/Disabled...). */
  _flagOn(entity) {
    const st = this.s(entity);
    if (entity.startsWith("select.") || entity.startsWith("input_select.")) return !!st && !/^\s*(unavailable|unknown|disabled?|off|desactiv|no|none)/i.test(st);
    return st === "on";
  }
  _flagSet(entity, on) {
    if (entity.startsWith("select.") || entity.startsWith("input_select.")) {
      const opts = this.a(entity, "options") || [];
      const opt = opts.find((o) => (on ? /^\s*(enabled?|on|activ|s[ií]|yes|true)/i : /^\s*(disabled?|off|desactiv|no|none)/i).test(o));
      if (opt) this._write(entity, opt);
    } else this._write(entity, on);
  }
  _applyAdvice(act = "apply") {
    let est = this.S("recomendacion_carga_red");
    let target = Number(this.A("recomendacion_carga_red", "soc_objetivo"));
    const man = this._manLoad();
    if (act === "off") est = "no_cargar";
    else if (man.on && man.soc !== null) {
      est = "cargar"; // the person chose the target
      target = man.soc;
    }
    const k = (x) => this.set_(x);
    const steps = [];
    let note = "";
    // Night programs: those of 1 and 2 that start before 08:00 (the battery is meant to be used from 08:00 to 00:00).
    const night = [1, 2].filter((n) => {
      const t = k(`deye_p${n}_hora`);
      return t ? String(this.s(t) || "99:99").slice(0, 5) < "08:00" : n === 1;
    });
    if (est === "cargar" && Number.isFinite(target)) {
      if (k("deye_franjas") && !this._flagOn(k("deye_franjas"))) {
        if (/^(select|input_select)\./.test(k("deye_franjas"))) note = "\n\nOjo: la programación por franjas está desactivada. Elige el modo en el desplegable de Solar para que los programas funcionen.";
        else steps.push(["Activar la programación por franjas", () => this._flagSet(k("deye_franjas"), true)]);
      }
      for (const n of night) {
        if (k(`deye_p${n}_soc`)) steps.push([`Programa ${n}: SOC ${target} %`, () => this._write(k(`deye_p${n}_soc`), target)]);
        if (k(`deye_p${n}_carga`)) steps.push([`Programa ${n}: carga desde la red activada`, () => this._chargeSet(k(`deye_p${n}_carga`), true)]);
      }
      // With time-of-use active, grid charging is decided by each program; the general switch is only for the mode without programs.
      const touOn = !!k("deye_franjas") && this._flagOn(k("deye_franjas"));
      if (!touOn && k("deye_carga_red") && this.s(k("deye_carga_red")) !== "on") steps.push(["Activar la carga de la batería por la red", () => this._write(k("deye_carga_red"), true)]);
    } else if (est === "no_cargar") {
      for (const n of night) if (k(`deye_p${n}_carga`)) steps.push([`Programa ${n}: carga desde la red desactivada`, () => this._chargeSet(k(`deye_p${n}_carga`), false)]);
    }
    if (!steps.length) return alert("No hay nada que aplicar: configura los programas del Deye en Configurar → Inversor Deye.");
    if (!confirm("Se va a cambiar en el inversor:\n\n• " + steps.map((s2) => s2[0]).join("\n• ") + note + "\n\n¿Aplicar?")) return;
    steps.forEach((s2) => s2[1]());
  }

  cloudIcon(p) {
    return p === null || p === undefined ? "mdi:weather-cloudy-clock" : p < 20 ? "mdi:weather-sunny" : p < 45 ? "mdi:weather-partly-cloudy" : p < 75 ? "mdi:weather-cloudy" : "mdi:weather-cloudy-alert";
  }
  adviceCards() {
    if (!this.set_("meteo_entidad"))
      return [this.card("adv", `<h3>${icon("mdi:weather-partly-cloudy")}Nubosidad y carga por red</h3><div class="empty">${icon("mdi:information-outline")} Elige la «Entidad del tiempo» en Configurar → Solar e inversor para ver la nubosidad de hoy y de los próximos 5 días, y la recomendación de carga por red.</div>`, { c: C.muted })];
    const est = this.S("recomendacion_carga_red");
    const a = (x) => this.A("recomendacion_carga_red", x);
    const col = est === "cargar" ? C.amber : est === "no_cargar" ? C.green : C.muted;
    const head = est === "cargar" ? "Conviene cargar por la red esta noche" : est === "no_cargar" ? "No hace falta cargar por la red" : "Sin datos suficientes";
    const canApply = est === "cargar" || est === "no_cargar" ? ["deye_p1_carga", "deye_p1_soc", "deye_carga_red"].some((x) => this.set_(x)) : false;
    const target = a("soc_objetivo"), s08 = a("soc_previsto_08h");
    const kpis = target !== null && target !== undefined && est !== "sin_datos" ? `<div class="chips" style="margin:6px 0"><span class="chip on" style="--c:${col}">Objetivo ${fmt(target, 0)} %</span><span class="chip">A las 08:00 sin red: ${fmt(s08, 0)} %</span><span class="chip">Consumo medio ${kwh(a("consumo_diario_kwh"), 1)}/día</span></div>` : "";
    const advTarget = Number(target);
    const man = this._manLoad();
    const socEnt = this.set_("deye_p1_soc");
    const sa = socEnt ? this.st(socEnt)?.attributes || {} : {};
    const lo = Number.isFinite(Number(sa.min)) ? Number(sa.min) : 0, hi = Number.isFinite(Number(sa.max)) ? Number(sa.max) : 100;
    const mv = Math.max(lo, Math.min(hi, man.soc ?? (Number.isFinite(advTarget) ? advTarget : 60)));
    const canApplyAny = ["deye_p1_carga", "deye_p1_soc", "deye_carga_red"].some((x) => this.set_(x));
    const modeChip = (m, label, on) => `<button class="chip ${on ? "on" : ""}" style="--c:${col}" data-manmode="${m}">${label}</button>`;
    const mode = canApplyAny ? `<div class="chips" style="margin:10px 0 4px">${modeChip("auto", "Usar lo aconsejado", !man.on)}${modeChip("manual", "Elegir yo el SOC", man.on)}</div>` : "";
    const s08n = Number(s08), capn = Number(a("capacidad_kwh"));
    const manual = canApplyAny && man.on ? `<div class="sim nr"><label>SOC con el que quiero empezar a las 08:00 (objetivo de carga por red)</label><div class="nrb" data-man="1" data-s08="${Number.isFinite(s08n) ? s08n : ""}" data-cap="${Number.isFinite(capn) ? capn : ""}" data-target="${Number.isFinite(advTarget) ? advTarget : ""}"><input type="range" min="${lo}" max="${hi}" step="1" value="${mv}" data-manin="1" aria-label="SOC objetivo manual"><span class="nrv"><input type="number" inputmode="numeric" min="${lo}" max="${hi}" step="1" value="${mv}" data-manin="1" aria-label="SOC objetivo manual (valor exacto)"><i>%</i></span></div><div class="small muted manp" style="grid-column:1/-1">${esc(this._manPreview(mv, s08n, capn, advTarget))}</div></div>` : "";
    const btn = (act, label) => `<button class="btn full" style="--c:${col};margin-top:8px" data-adv="${act}">${icon("mdi:flash-auto")}<span class="advl">${label}</span></button>`;
    const apply = !canApplyAny ? "" : man.on ? btn("apply", `Aplicar en el Deye: cargar hasta ${fmt(mv, 0)} % (manual)`) + btn("off", "Aplicar en el Deye: no cargar por red esta noche") : canApply ? btn("apply", est === "cargar" ? `Aplicar en el Deye: cargar hasta ${fmt(target, 0)} %` : "Aplicar en el Deye: no cargar por red") : "";
    const adv = this.card("adv", `<h3>${icon("mdi:transmission-tower-import")}Carga por red esta noche</h3><div class="big" style="--c:${col};font-size:20px">${head}</div>${kpis}<div class="small muted">${esc(a("motivo") || "")}</div>${mode}${manual}${apply}<div class="small muted" style="margin-top:8px">Prioriza la batería de 08:00 a 00:00; la red carga de 00:00 a 08:00. Es una estimación con la nubosidad prevista y tu consumo medio.</div>`, { c: col });
    const days = a("dias") || [];
    const tiles = days.map((d, i) => {
      const label = i === 0 ? "Hoy" : i === 1 ? "Mañana" : new Date(d.fecha + "T12:00:00").toLocaleDateString("es-ES", { weekday: "short" });
      const p = d.nubes_pct;
      const c = p === null || p === undefined ? C.muted : p < 30 ? C.amber : p < 70 ? C.cyan : C.violet;
      const solar = d.solar_kwh !== null && d.solar_kwh !== undefined ? `≈ ${fmt(d.solar_kwh, 1)} kWh` : "—";
      const cov = d.cobertura_pct !== null && d.cobertura_pct !== undefined ? `${fmt(d.cobertura_pct, 0)} % del consumo` : "";
      return `<div style="flex:1 1 90px;min-width:90px;text-align:center;padding:8px 4px;border-radius:12px;border:1px solid ${c}55;background:${c}12"><div class="small muted">${esc(label)}</div><div style="color:${c};font-size:22px">${icon(this.cloudIcon(p))}</div><div style="font-weight:700;color:${c}">${p === null || p === undefined ? "—" : fmt(p, 0) + " %"}</div><div class="small">${solar}</div><div class="small muted">${cov}</div>${d.origen_nubes === "estimada" ? `<div class="small muted" title="La previsión no trae porcentaje de nubes: se estima por el estado del cielo">~ por el cielo</div>` : ""}</div>`;
    }).join("");
    const cloud = this.card("cloud", `<h3>${icon("mdi:weather-partly-cloudy")}Nubosidad: hoy y próximos 5 días</h3>${days.length ? `<div style="display:flex;gap:8px;flex-wrap:wrap">${tiles}</div><div class="small muted" style="margin-top:8px">Producción solar estimada con la nubosidad${this.set_("solar_prevision_manana") ? " (hoy y mañana, de tu sensor de previsión)" : ""}.</div>` : `<div class="empty">${icon("mdi:information-outline")} Esperando la previsión de ${esc(this.name(this.set_("meteo_entidad")))}…${a("meteo") && a("meteo").error ? `<div class="small muted" style="margin-top:6px">Motivo: ${esc(a("meteo").error)}</div>` : ""}</div>`}`, { c: C.cyan });
    return [adv, cloud];
  }
  numRow(label, entity, unit, opt = {}) {
    const st = this.st(entity);
    if (!st) return "";
    const a = st.attributes;
    const min = a.min ?? 0, step = a.step ?? 1;
    const v = toNum(st.state, 0);
    const cap = opt.cap ?? null; // extra upper limit (e.g. contracted power)
    const max = cap !== null ? Math.min(a.max ?? 100, cap) : (a.max ?? 100);
    const dec = step < 1 ? 1 : 0;
    const volt = opt.volt || 0;
    const wTxt = (x) => `≈ ${Math.round(x * volt).toLocaleString("es-ES", { useGrouping: true })} W`;
    const over = cap !== null && v > cap;
    const watts = volt ? `<span class="nrw" style="${over ? `color:${C.red}` : ""}">${wTxt(v)}</span>` : "";
    const note = opt.note ? `<div class="small muted" style="grid-column:1/-1">${opt.note}</div>` : "";
    const warn = over ? `<div class="small" style="grid-column:1/-1;color:${C.red}">⚠ ${fmt(v, 0)} ${unit} supera la potencia contratada menos el consumo de la casa; bájala a ${fmt(cap, 0)} ${unit} o menos.</div>` : "";
    // slider + exact box that stay in sync while dragging/typing; the value is written on release / Enter / leaving the box
    return `<div class="sim nr"><label>${esc(label)}</label><div class="nrb" ${volt ? `data-volt="${volt}"` : ""} ${cap !== null ? `data-cap="${cap}"` : ""}><input type="range" min="${min}" max="${max}" step="${step}" value="${Math.min(v, max)}" data-set="${esc(entity)}" data-nr="1" aria-label="${esc(label)}"><span class="nrv"><input type="number" inputmode="decimal" min="${min}" max="${max}" step="${step}" value="${Number(v.toFixed(dec))}" data-set="${esc(entity)}" data-nr="1" aria-label="${esc(label)} (valor exacto)"><i>${unit}</i></span>${watts}</div>${warn}${note}</div>`;
  }
  deyeCards() {
    const k = (x) => this.set_(x);
    if (!["deye_carga_red", "deye_corriente_carga_red", "deye_carga_red_inicio", "deye_franjas", "deye_p1_hora", "deye_p1_soc", "deye_p1_carga", "deye_p2_hora", "deye_p2_soc", "deye_p2_carga"].some(k))
      return [this.card("deye", `<h3>${icon("mdi:power-plug-battery")}Inversor Deye</h3><div class="empty">${icon("mdi:information-outline")} Añade las entidades de tu inversor en Configurar → Inversor Deye para controlar la carga por red y los programas 1 y 2 desde aquí.</div>`, { c: C.muted })];
    const toggle = (label, entity, ic) => {
      const on = this.s(entity) === "on";
      return `<button class="btn full" style="--c:${on ? C.green : C.muted};margin-bottom:8px" data-toggle="${esc(entity)}">${icon(ic)}${esc(label)}: ${on ? "activada" : "desactivada"}</button>`;
    };
    let main = `<h3>${icon("mdi:transmission-tower-import")}Carga de la batería por la red</h3>`;
    if (k("deye_carga_red")) main += toggle("Carga por red", k("deye_carga_red"), "mdi:transmission-tower-import");
    if (k("deye_corriente_carga_red")) {
      const g = this._gridCap();
      const { v: volt, nominal } = this._batVolt();
      const note = `Potencia = intensidad × tensión de la batería (${fmt(volt, 1)} V${nominal ? " nominal" : ""})${g ? `. Máximo ahora ${fmt(g.amps, 0)} A = ${fmt(g.watts, 0)} W: potencia contratada (${fmt(g.contracted, 0)} W) menos lo que consume la casa (${fmt(g.load, 0)} W).` : "."}`;
      main += this.numRow("Intensidad de carga", k("deye_corriente_carga_red"), this.unit(k("deye_corriente_carga_red")) || "A", { cap: g ? g.amps : null, volt, note });
    }
    if (k("deye_carga_red_inicio")) main += this.numRow("Empezar a cargar por red por debajo de", k("deye_carga_red_inicio"), this.unit(k("deye_carga_red_inicio")) || "%");
    if (k("deye_franjas")) {
      const f = k("deye_franjas"), on = this._flagOn(f);
      main += /^(select|input_select)\./.test(f)
        ? `<div class="sim"><label>${icon("mdi:calendar-clock")} Programación por franjas (Time of Use) · ${on ? "activada" : "desactivada"}</label><select data-set="${esc(f)}" style="grid-column:1/-1;background:#0d1c33;color:inherit;border:1px solid ${on ? C.green : "#16304f"};border-radius:8px;padding:6px 8px">${(this.a(f, "options") || []).map((o) => `<option value="${esc(o)}"${o === this.s(f) ? " selected" : ""}>${esc(o)}</option>`).join("")}</select></div>`
        : toggle("Programación por franjas", f, "mdi:calendar-clock");
    }
    main += `<div class="small muted" style="margin-top:6px">Los cambios se envían al inversor al soltar el control. Se respetan los límites que da el propio inversor.</div>`;
    const cards = [this.card("gc", main, { c: C.green })];
    for (const n of [1, 2]) {
      const t = k(`deye_p${n}_hora`), so = k(`deye_p${n}_soc`), ch = k(`deye_p${n}_carga`);
      if (![t, so, ch].some(Boolean)) continue;
      let h = `<h3>${icon("mdi:clock-time-four-outline")}Programa ${n}</h3>`;
      if (t) {
        const v = String(this.s(t) || "").slice(0, 5);
        h += `<div class="sim"><label>Hora de inicio</label><input type="time" value="${esc(v)}" data-set="${esc(t)}" style="background:#0d1c33;color:inherit;border:1px solid #16304f;border-radius:8px;padding:4px 6px"><b>${esc(v || "—")}</b></div>`;
      }
      if (so) h += this.numRow("SOC", so, this.unit(so) || "%");
      if (ch) {
        const sel = ch.startsWith("select.") || ch.startsWith("input_select.");
        h += `<div class="small muted" style="margin:8px 0 4px">Carga</div><div class="chips">` + (sel ? (this.a(ch, "options") || []).map((o) => `<button class="chip ${this.s(ch) === o ? "on" : ""}" data-set="${esc(ch)}" data-val="${esc(o)}">${esc(o)}</button>`).join("") : `<button class="chip ${this.s(ch) === "on" ? "on" : ""}" data-set="${esc(ch)}" data-val="${this.s(ch) === "on" ? "false" : "true"}">${this.s(ch) === "on" ? "Desde la red: sí" : "Desde la red: no"}</button>`) + `</div>`;
      }
      cards.push(this.card(`p${n}`, h, { c: n === 1 ? C.amber : C.violet }));
    }
    return cards;
  }

  socDiffColor(d) {
    const warn = toNum(this.set_("diferencia_soc_aviso"), 5), crit = toNum(this.set_("diferencia_soc_critico"), 15);
    return d === null ? C.muted : d >= crit ? C.red : d >= warn ? C.amber : C.green;
  }

  /** Marker comparing the SOC of the batteries in cfg.soc_pair. */
  socDiffCard(k) {
    const pair = (this.cfg.soc_pair || []).map((id) => (this.cfg.batteries || []).find((b) => b.id === id)).filter(Boolean);
    if (pair.length < 2) return null;
    const warn = toNum(this.set_("diferencia_soc_aviso"), 5), crit = toNum(this.set_("diferencia_soc_critico"), 15);
    const d = this.N("diferencia_soc");
    const c = this.socDiffColor(d);
    const verdict = d === null ? "Sin datos de alguna batería" : d >= crit ? "Desequilibradas" : d >= warn ? "Vigilar" : "Equilibradas";
    const colors = [C.lime, C.cyan, C.violet, C.amber];
    const rows = pair.map((b, i) => {
      const v = this.n(b.soc);
      return `<div class="row" data-more="${esc(b.soc)}" style="cursor:pointer"><div class="n">${esc(b.name)}</div><div class="bar"><i style="--b:${colors[i % colors.length]};width:${v === null ? 0 : Math.max(0, Math.min(100, v))}%"></i></div><div class="x"><b>${fmt(v, 0)} %</b></div></div>`;
    }).join("");
    const top = Math.max(crit * 1.5, (d || 0) * 1.1, 10);
    const pos = (x) => `${Math.min(100, (100 * x) / top)}%`;
    const scale = `<div style="position:relative;height:12px;border-radius:6px;margin:14px 0 4px;background:linear-gradient(90deg,${C.green}55 0 ${pos(warn)},${C.amber}55 ${pos(warn)} ${pos(crit)},${C.red}55 ${pos(crit)} 100%)">
        ${d === null ? "" : `<div style="position:absolute;top:-5px;left:calc(${pos(d)} - 2px);width:4px;height:22px;border-radius:2px;background:${c};box-shadow:0 0 10px ${c}"></div>`}
      </div><div class="small muted" style="display:flex;justify-content:space-between"><span>0</span><span>aviso ${fmt(warn, 0)}</span><span>crítico ${fmt(crit, 0)}</span><span>${fmt(top, 0)} pts</span></div>`;
    return this.card(k, `<h3>${icon("mdi:scale-unbalanced")}Diferencia de SOC entre baterías</h3>
      <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:6px"><div class="big" style="--c:${c}">${d === null ? "—" : `Δ ${fmt(d, 1)}`}</div><div class="muted">puntos · <b style="color:${c}">${verdict}</b></div></div>
      ${rows}${scale}`, { c, click: this.id("diferencia_soc") });
  }

  v_bateria() {
    const bats = this.cfg.batteries || [];
    if (!bats.length) return [{ cards: [this.title("t", "Batería", "", "mdi:home-battery", C.green), this.empty("e", "Añade tus baterías en la integración → «Añadir batería».")] }];
    const b = this.N("potencia_bateria");
    const soc = this.N("soc_bateria");
    const auto = this.N("autonomia_bateria");
    const sections = [{
      cards: [
        this.title("t", "Baterías", "Carga, flujo y celdas", "mdi:home-battery", C.green),
        this.card("g", gauge(soc, 0, 100, soc < 20 ? C.red : soc < 40 ? C.amber : C.green, "Carga total", "%"), { c: C.green, w: 6, click: this.id("soc_bateria") }),
        this.kpi("p", this.id("potencia_bateria"), fmtW(Math.abs(b ?? 0)), b > 30 ? "Descargando" : b < -30 ? "Cargando" : "En reposo", b < -30 ? "mdi:battery-charging-high" : "mdi:battery-arrow-down", C.green, 6),
        this.kpi("e", this.id("energia_almacenada"), kwh(this.N("energia_almacenada")), `Almacenado de ${fmt(this.A("potencia_bateria", "capacidad_kwh"), 0)} kWh`, "mdi:battery-high", C.green, 6),
        this.kpi("a", this.id("autonomia_bateria"), auto === null ? "—" : `${fmt(auto, 1)} h`, "Autonomía con el consumo actual", "mdi:timer-sand", C.green, 6),
        this.kpi("cd", this.id("energia_bateria_carga"), `↓ ${kwh(this.N("energia_bateria_carga"), 2)} · ↑ ${kwh(this.N("energia_bateria_descarga"), 2)}`, "Cargado · descargado hoy", "mdi:swap-vertical-bold", C.green, 12),
      ],
    }];
    const diff = this.socDiffCard("sd");
    if (diff) sections[0].cards.push(diff);
    for (const bt of bats) {
      const detail = bt.in_total === false;
      const link = bt.link ? this.s(bt.link) : null;
      const sub = [detail ? "Detalle del BMS" : "Banco · cuenta para el total", bt.capacity_kwh ? `${fmt(bt.capacity_kwh, 1)} kWh` : ""].filter(Boolean).join(" · ");
      const cards = [this.title("b" + bt.id, bt.name, sub, detail ? "mdi:battery-outline" : "mdi:home-battery-outline", C.green)];
      if (bt.link) {
        const fresh = this.n(bt.soc) !== null;
        const [lv, ll, lc, li] = link === "on" ? ["Comunicando", "BMS · RS485", C.green, "mdi:lan-connect"] : link !== "off" && fresh ? ["Comunicando", "BMS · datos al día", C.green, "mdi:lan-connect"] : link === "off" ? ["Sin comunicación", "BMS · datos congelados", C.red, "mdi:lan-disconnect"] : ["Sin datos", "BMS · ESP32 no disponible", C.amber, "mdi:lan-pending"];
        cards.push(this.kpi("lk" + bt.id, bt.link, lv, ll, li, lc, 12));
      }
      const w = this.watts(bt.power);
      const wv = w === null ? null : bt.positive_charge ? -w : w;
      cards.push(this.card("bs" + bt.id, gauge(this.n(bt.soc), 0, 100, C.green, "SOC", "%", 130), { c: C.green, w: 6, click: bt.soc }));
      cards.push(this.kpi("bp" + bt.id, bt.power, fmtW(Math.abs(wv ?? 0)), wv > 30 ? "Descargando" : wv < -30 ? "Cargando" : "En reposo", "mdi:flash", C.green, 6));
      for (const [k, l, ic, u, d] of [["voltage", "Tensión", "mdi:sine-wave", "V", 2], ["current", "Corriente", "mdi:current-dc", "A", 1], ["cycles", "Ciclos", "mdi:autorenew", "", 0]])
        if (bt[k]) cards.push(this.kpi(k + bt.id, bt[k], `${fmt(this.n(bt[k]), d)} ${u}`, l, ic, C.green, 6));
      if (bt.alarms) {
        const al = this.s(bt.alarms);
        const bad = al !== null && al !== undefined && !["0", "0.0", "off", "ok", "normal", "unknown", "unavailable"].includes(String(al).toLowerCase());
        cards.push(this.kpi("al" + bt.id, bt.alarms, bad ? esc(al) : "Sin alarmas", "Alarmas del BMS", bad ? "mdi:alert-octagon" : "mdi:shield-check", bad ? C.red : C.green, 6));
      }
      for (const e of bt.temperatures || []) cards.push(this.kpi("bt" + e, e, `${fmt(this.n(e), 1)} °C`, esc(this.name(e)), "mdi:thermometer", C.orange, 6));
      if ((bt.cells || []).length) {
        const vals = bt.cells.map((e) => this.n(e));
        const ok = vals.filter((v) => v !== null && v > 1);
        const lo = ok.length ? Math.min(...ok) : 0, hi = ok.length ? Math.max(...ok) : 0;
        const span = Math.max(hi - lo, 0.005) + 0.02;
        const delta = (hi - lo) * 1000;
        const cells = vals.map((v, i) => {
          const c = v === null ? C.muted : v < 3.0 || v > 3.6 ? C.red : v < 3.2 || v > 3.45 ? C.amber : C.green;
          const mark = v === lo ? " ▼" : v === hi ? " ▲" : "";
          return `<div class="cell" data-more="${esc(bt.cells[i])}" style="cursor:pointer"><span class="muted">${String(i + 1).padStart(2, "0")}</span><div class="bar"><i style="--b:${c};width:${v === null ? 0 : Math.min(100, (100 * (v - lo + 0.01)) / span)}%"></i></div><span style="color:${c}">${fmt(v, 3)}${mark}</span></div>`;
        }).join("");
        cards.push(this.card("cells" + bt.id, `<h3>${icon("mdi:view-grid")}Celdas · Δ <span style="color:${delta > 100 ? C.red : delta > 50 ? C.amber : C.green}">${fmt(delta, 0)} mV</span> · media ${fmt(ok.reduce((a, v) => a + v, 0) / (ok.length || 1), 3)} V</h3><div class="cells">${cells}</div>`, { c: C.green }));
      }
      sections.push({ cards });
    }
    const pairIds = this.cfg.soc_pair || [];
    const palette = [C.lime, C.cyan, C.violet, C.amber];
    const series = bats.length === 1
      ? [{ name: "SOC", entity: bats[0].soc, color: C.green }]
      : [{ name: "Banco", entity: this.id("soc_bateria"), color: C.green }, ...bats.filter((b) => pairIds.includes(b.id)).map((b, i) => ({ name: b.name, entity: b.soc, color: palette[i % palette.length] }))];
    const charts = [this.chartCard("soc", "Carga 48 h (%)", C.green, { kind: "history", hours: 48, unit: "%", min: 0, max: 100, series })];
    if (pairIds.length >= 2) charts.push(this.chartCard("sdh", "Diferencia de SOC 48 h (puntos)", C.amber, { kind: "history", hours: 48, unit: "%", min: 0, series: [{ name: "Δ SOC", spread: bats.filter((b) => pairIds.includes(b.id)).map((b) => b.soc), color: C.amber, type: "area" }] }));
    sections.push({ cls: "w2", cards: [
      ...charts,
      this.chartCard("bw", "Potencia 24 h (W, + descarga)", C.green, { kind: "history", hours: 24, unit: "W", series: bats.map((bt, i) => ({ name: bt.name, entity: bt.power, scale: bt.positive_charge ? -1 : 1, type: "area", color: [C.lime, C.green, C.cyan][i % 3] })) }),
    ] });
    return sections;
  }

  // ---------------------------------------------------------------- 5 consumos
  v_consumos() {
    const per = this.period;
    const circuits = this.A("potencia_consumo", "circuitos") || [];
    const top = Math.max(1, ...circuits.map((c) => c.w || 0));
    const rows = circuits.map((c, i) => {
      const src = (this.cfg.circuits || []).find((x) => x.id === c.id);
      return `<div class="row" data-more="${esc(src?.power || "")}" style="cursor:pointer"><div class="n">${icon(c.icono || "mdi:flash")} ${esc(c.nombre)}${c.padre ? ` <span class="muted small">⤷ ${esc(c.padre)}</span>` : ""}</div><div class="bar"><i style="--b:${PALETTE[(i + 1) % PALETTE.length]};width:${(100 * (c.w || 0)) / top}%"></i></div><div class="x"><b>${fmtW(c.w)}</b><div class="small muted">${fmt(c.pct, 0)} % · ${kwh(c.periodo_kwh, 2)}</div></div></div>`;
    }).join("");
    const nm = this.A("potencia_consumo", "no_medido_w");
    const rank = this.card("rank", `<h3>${icon("mdi:podium")}Ahora · kWh ${PERIODS[per].toLowerCase()}</h3>${rows || `<div class="empty">Añade circuitos con «Añadir circuito».</div>`}${isNum(nm) ? `<div class="row"><div class="n" style="color:${C.violet}">${icon("mdi:help-circle-outline")} Sin medir</div><div class="bar"><i style="--b:${C.violet};width:${(100 * nm) / top}%"></i></div><div class="x"><b>${fmtW(nm)}</b></div></div>` : ""}`, { c: C.pink });
    const head = [
      this.title("t", "Consumos", "Total y cada circuito por separado", "mdi:home-lightning-bolt", C.pink),
      this.kpi("tot", this.id("potencia_consumo"), fmtW(this.N("potencia_consumo")), `Consumo total · ${kwh(this.N("energia_consumo"), 2)} hoy · ${kwh(this.bucket("energia_consumo"), 1)} ${PERIODS[per].toLowerCase()}`, "mdi:home-lightning-bolt", C.pink, 12),
      this.periodChips("per", C.pink),
    ];
    const groups = {};
    for (const c of this.cfg.circuits || []) (groups[c.group] = groups[c.group] || []).push(c);
    const groupSecs = Object.entries(groups).map(([g, items]) => ({
      cards: [this.title("g" + g, g, "", "mdi:electric-switch", C.pink), ...items.map((c) => this.kpi("c" + c.id, c.power, fmtW(this.watts(c.power)), `${esc(c.name)} · ${kwh(this.N(c.id + ":energia_circuito"), 2)} hoy · ${kwh(this.a(this.id(c.id + ":energia_circuito"), per), 1)} periodo`, c.icon || "mdi:flash", C.pink, 6))],
    }));
    const charts = [this.chartCard("d30", "Consumo 30 días (kWh)", C.pink, { kind: "days", unit: "kWh", series: [{ name: "Consumo", field: "consumo", color: C.pink }, { name: "Solar", field: "solar", color: C.amber }] })];
    const cs = (this.cfg.circuits || []).filter((c) => c.in_total);
    if (cs.length) charts.unshift(this.chartCard("c24", "Circuitos 24 h (W)", C.pink, { kind: "history", hours: 24, unit: "W", height: 280, series: cs.map((c, i) => ({ name: c.name, entity: c.power, color: PALETTE[(i + 1) % PALETTE.length] })) }));
    return [{ cards: [...head, rank] }, ...groupSecs, { cls: "w2", cards: charts }];
  }

  // ---------------------------------------------------------------- 6 problemas
  v_problemas() {
    const list = this.A("problemas", "lista") || [];
    const count = (l) => list.filter((p) => p.nivel === l).length;
    const big = (n, l, c) => `<div style="text-align:center;flex:1"><div class="big" style="--c:${c}">${n}</div><div class="small muted">${l}</div></div>`;
    const counts = this.card("cnt", `<div style="display:flex">${big(count("critico"), "CRÍTICOS", C.red)}${big(count("aviso"), "AVISOS", C.amber)}${big(count("info"), "INFO", C.blue)}</div><div class="small muted" style="margin-top:8px">Se revisa cada 30 s. Un problema solo aparece si dura lo bastante, para que una lectura suelta no dispare un aviso.</div>`, { c: C.red });
    const btns = this.card("btn", `<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><button class="btn full" style="--c:${C.green}" data-press="${this.id("reconocer_problemas")}">${icon("mdi:check-all")}Reconocer todo</button><button class="btn full" data-press="${this.id("regenerar_panel")}">${icon("mdi:refresh")}Regenerar panel</button></div>`, { c: C.cyan });
    const byArea = {};
    list.forEach((p) => (byArea[p.area] = byArea[p.area] || []).push(p));
    const order = { critico: 0, aviso: 1, info: 2 };
    const listing = Object.keys(byArea).length
      ? Object.entries(byArea).sort((a, b) => Math.min(...a[1].map((p) => order[p.nivel])) - Math.min(...b[1].map((p) => order[p.nivel]))).map(([a, ps]) => `<h3 style="margin-top:8px">${esc(a)}</h3>${this.problemsHTML(ps)}`).join("")
      : this.problemsHTML([]);
    const src = [];
    const add = (l, e) => e && src.push([l, e]);
    add("Red", this.set_("red_potencia")); add("Consumo total", this.set_("consumo_potencia")); add("Solar", this.set_("solar_potencia")); add("Precio", this.set_("precio_sensor"));
    (this.cfg.strings || []).forEach((s) => add(s.name, s.power));
    (this.cfg.batteries || []).forEach((b) => { add(b.name + " · SOC", b.soc); add(b.name + " · potencia", b.power); });
    (this.cfg.circuits || []).forEach((c) => add(c.name, c.power));
    (this.cfg.zones || []).forEach((z) => add(z.name, z.valve));
    const rows = src.map(([l, e]) => {
      const s = this.s(e), bad = s === undefined || s === "unavailable" || s === "unknown";
      return `<tr data-more="${esc(e)}" style="cursor:pointer"><td>${esc(l)}</td><td class="r"><span class="dot" style="--a:${bad ? C.red : C.green}"></span>${bad ? `<span style="color:${C.red}">${s === undefined ? "no existe" : esc(s)}</span>` : `${esc(s)} ${esc(this.unit(e))}`}</td></tr>`;
    }).join("");
    return [
      { cards: [this.title("t", "Diagnóstico", "Problemas detectados en la instalación", "mdi:alert-decagram", C.red), counts, btns] },
      { cls: "w2", cards: [this.card("list", listing, { c: C.red })] },
      { cards: [this.card("src", `<h3>${icon("mdi:heart-pulse")}Estado de las fuentes</h3><table>${rows}</table>`, { c: C.cyan })] },
    ];
  }

  // ---------------------------------------------------------------- 7 coste (luz + gas)
  billTable(attrs, { lines = "lineas", kind = "luz" } = {}) {
    const ls = attrs?.[lines] || [];
    if (!ls.length) return `<div class="loading">Calculando…</div>`;
    const rows = ls.map((l) => {
      const calc = kind === "gas" ? `${fmt(l.cantidad, l.unidad === "días" || l.unidad === "dias" ? 0 : 2)} ${esc(l.unidad || "")} × ${fmt(l.precio, 6)} ${esc(l.unidad_precio || "")}` : esc(l.calculo || "");
      return `<tr><td>${esc(l.concepto)}</td><td class="small muted">${calc}</td><td class="r">${eur(l.importe)}</td></tr>`;
    }).join("");
    return `<table><tr><th>Concepto</th><th>Cálculo</th><th class="r">Importe</th></tr>${rows}
      <tr><td><b>Base imponible</b></td><td></td><td class="r"><b>${eur(attrs.base_imponible)}</b></td></tr>
      <tr><td>IVA</td><td class="small muted">${fmt(attrs.iva_porcentaje, 0)} %</td><td class="r">${eur(attrs.iva)}</td></tr>
      <tr class="tot"><td>TOTAL</td><td></td><td class="r">${eur(attrs.total)}</td></tr></table>`;
  }
  v_coste() {
    const fa = this.st(this.id("factura_actual"))?.attributes || {};
    const pf = this.st(this.id("prevision_factura"))?.attributes || {};
    const sim = this.st(this.id("simulacion_factura"))?.attributes || {};
    const lost = toNum(fa.compensacion_perdida, 0);
    const luzNow = this.card("ln", `<h3>${icon("mdi:receipt-text-clock")}Factura en curso</h3><div class="small muted" style="margin-bottom:6px">${fmtDate(fa.desde)} – ${fmtDate(fa.hasta)} · ${fa.dias ?? "—"} días · ${kwh(fa.importada_kwh)}</div>${this.billTable(fa)}${lost > 0 ? `<div class="small" style="color:${C.amber};margin-top:6px">⚠ ${eur(lost)} de excedentes no se compensan (superan la energía del periodo).</div>` : ""}`, { c: C.gold });
    const luzEnd = this.card("le", `<div style="display:flex;justify-content:space-between;align-items:center"><h3>${icon("mdi:crystal-ball")}Previsión al cierre</h3><div class="big" style="--c:${C.gold};font-size:26px">${eur(pf.total)}</div></div><div class="small muted">${fmtDate(pf.desde)} – ${fmtDate(pf.hasta)} · ${kwh(pf.importada_kwh, 0)} importados</div>`, { c: C.gold });
    const nx = (pf.proximas || []).map((m) => `<tr><td>${esc(m.mes)} <span class="small muted">${m.fuente === "año_anterior" ? "📅" : "∿"}</span></td><td class="r">${kwh(m.consumo_kwh, 0)}</td><td class="r">${kwh(m.importada_kwh, 0)}</td><td class="r">${kwh(m.exportada_kwh, 0)}</td><td class="r" style="color:${C.gold}"><b>${eur(m.total)}</b></td></tr>`).join("");
    const next = this.card("nx", `<h3>${icon("mdi:calendar-arrow-right")}Próximas facturas</h3><table><tr><th>Mes</th><th class="r">Consumo</th><th class="r">Importado</th><th class="r">Vertido</th><th class="r">Total</th></tr>${nx}</table><div class="small muted" style="margin-top:6px">∿ tu media reciente ajustada a la producción solar de cada mes · 📅 mismo periodo del año pasado</div>`, { c: C.gold });
    // gas
    const g = this.cfg.gas || {};
    const gasCards = [];
    if (g.factura || g.prevision_factura || g.coste_hoy) {
      const gf = this.st(g.factura)?.attributes || {};
      if (g.factura) gasCards.push(this.card("gf", `<h3>${icon("mdi:fire")}Factura del gas en curso</h3><div class="small muted" style="margin-bottom:6px">Desde ${fmtDate(gf.fecha_lectura_anterior)} · ${gf.dias ?? "—"} días · ${fmt(gf.m3, 0)} m³ · ${fmt(gf.kwh, 0)} kWh</div>${this.billTable({ ...gf }, { kind: "gas" })}`, { c: C.violet }));
      const prev = g.prevision_factura ? this.n(g.prevision_factura) : toNum(gf.prevision);
      if (isNum(prev)) gasCards.push(this.card("gp", `<div style="display:flex;justify-content:space-between;align-items:center"><h3>${icon("mdi:crystal-ball")}Previsión del gas</h3><div class="big" style="--c:${C.violet};font-size:26px">${eur(prev)}</div></div><div class="small muted">Periodo de ${gf.dias_periodo ?? "—"} días · hoy ${eur(this.n(g.coste_hoy))} · mes ${eur(this.n(g.coste_mes))}</div>`, { c: C.violet }));
    } else gasCards.push(this.empty("ge", "Instala Gas TUR o indica tus sensores de gas en Configurar → Gas."));
    // total
    const totalNow = toNum(fa.total, 0) + toNum(this.st(g.factura)?.attributes?.total, 0);
    const totalCard = this.card("tot", `<div style="display:flex;gap:16px;flex-wrap:wrap;justify-content:space-around;text-align:center">
      <div><div class="small muted">LUZ · PREVISIÓN</div><div class="big" style="--c:${C.gold}">${eur(pf.total)}</div></div>
      <div><div class="small muted">GAS · PREVISIÓN</div><div class="big" style="--c:${C.violet}">${eur(g.prevision_factura ? this.n(g.prevision_factura) : this.st(g.factura)?.attributes?.prevision)}</div></div>
      <div><div class="small muted">GASTADO HASTA HOY</div><div class="big" style="--c:${C.text}">${eur(totalNow)}</div></div>
      <div><div class="small muted">AHORRO SOLAR · AÑO</div><div class="big" style="--c:${C.lime}">${eur(this.A("ahorro_solar", "ano"), 0)}</div></div></div>`, { c: C.gold });
    // simulator
    const simRow = (key, label, min, max, step, unit, neutral) => {
      const e = this.id(key), v = this.N(key, neutral);
      return `<div class="sim"><label>${label}</label><input type="range" min="${min}" max="${max}" step="${step}" value="${v}" data-number="${e}"><b>${v === -1 ? "actual" : fmt(v, step < 1 ? (step < 0.01 ? 3 : 2) : 0) + " " + unit}</b></div>`;
    };
    const s = sim.simulada || {}, b = sim.base || {}, d = toNum(sim.diferencia, 0);
    const simCard = this.card("sim", `<h3>${icon("mdi:flask-outline")}Simulador «¿y si…?»</h3>
      ${simRow("sim_potencia_p1", "Potencia punta (−1 = la actual)", -1, 10, 0.05, "kW", -1)}
      ${simRow("sim_potencia_p2", "Potencia valle (−1 = la actual)", -1, 10, 0.05, "kW", -1)}
      ${simRow("sim_consumo", "Cambio de consumo", -50, 100, 5, "%", 0)}
      ${simRow("sim_precio", "Cambio del precio de la energía", -50, 100, 5, "%", 0)}
      ${simRow("sim_paneles", "Paneles extra", 0, 10000, 100, "Wp", 0)}
      ${simRow("sim_bateria", "Batería extra", 0, 40, 1, "kWh", 0)}
      ${simRow("sim_excedentes", "Precio de excedentes (−1 = el actual)", -1, 0.3, 0.005, "€/kWh", -1)}
      <table style="margin-top:8px"><tr><th>${esc(s.mes || "")}</th><th class="r">Actual</th><th class="r">Simulada</th></tr>
      <tr><td>Potencia</td><td class="r">${eur(b.potencia)}</td><td class="r">${eur(s.potencia)}</td></tr>
      <tr><td>Energía</td><td class="r">${eur(b.energia)}</td><td class="r">${eur(s.energia)}</td></tr>
      <tr><td>Compensación</td><td class="r">−${eur(b.compensacion)}</td><td class="r">−${eur(s.compensacion)}</td></tr>
      <tr class="tot"><td>Total</td><td class="r">${eur(b.total)}</td><td class="r">${eur(s.total)}</td></tr></table>
      <div style="margin-top:8px;font-size:16px;font-weight:700;color:${d < 0 ? C.green : d > 0 ? C.red : C.muted}">${d < 0 ? "▼ Ahorras" : d > 0 ? "▲ Pagas" : "="} ${eur(Math.abs(d))}/mes · ${eur(Math.abs(toNum(sim.diferencia_anual, 0)), 0)}/año</div>`, { c: C.violet });
    const fcPts = (pf.proximas || []).map((m) => [new Date(m.mes + "-15T12:00:00").getTime(), m.total]);
    const fcChart = fcPts.length ? { k: "fc", html: `<h3>${icon("mdi:chart-bar")}Previsión luz (€)</h3><div class="chart" data-chart="fc"></div>`, c: C.gold, cls: "card", attrs: "", chart: { kind: "points", series: [{ name: "Factura", color: C.gold, type: "bar", points: fcPts }], opt: { start: fcPts[0][0] - 15 * 86400000, end: fcPts[fcPts.length - 1][0] + 15 * 86400000, slots: fcPts.length, unit: "€", height: 180, decimals: 2 } } } : null;
    return [
      { cls: "wall", cards: [this.title("t", "Coste energético", "Luz y gas: facturas en curso, previsiones y simulador", "mdi:cash-multiple", C.gold), totalCard] },
      { cards: [this.title("tl", "Luz", "", "mdi:flash", C.gold), luzNow, luzEnd] },
      { cards: [next, ...(fcChart ? [fcChart] : []), this.chartCard("d30", "Coste diario de la luz (€)", C.gold, { kind: "days", unit: "€", series: [{ name: "Energía", field: "coste", color: C.gold }, { name: "Compensación", field: "compensacion", color: C.lime }] })] },
      { cards: [this.title("tg", "Gas", "", "mdi:fire", C.violet), ...gasCards] },
      { cards: [simCard] },
    ];
  }

  // ---------------------------------------------------------------- 8 co2
  v_co2() {
    const tot = this.A("co2_evitado", "total") || {};
    const kg = toNum(tot.evitado_kg, 0);
    const hero = this.card("hero", `<div style="text-align:center"><div class="small muted">CO₂ EVITADO DESDE QUE MIDES</div><div class="big" style="--c:${C.lime};font-size:46px">${kg >= 1000 ? fmt(kg / 1000, 2) + " t" : fmt(kg, 1) + " kg"}</div>
      <div style="display:flex;justify-content:center;gap:28px;margin-top:8px;flex-wrap:wrap"><div>${icon("mdi:pine-tree")} <b>${fmt(tot.arboles, 1)}</b> <span class="muted">árboles absorbiendo un año</span></div><div>${icon("mdi:car")} <b>${fmt(tot.km_coche, 0)}</b> <span class="muted">km en coche</span></div></div></div>`, { c: C.lime });
    const B = ["hoy", "mes", "ano", "total"].map((k) => this.A("co2_evitado", k) || {});
    const r = (l, f, c, d = 1) => `<tr><td style="color:${c}">${l}</td>${B.map((x, i) => `<td class="r">${fmt(x[f], i >= 2 ? 0 : d)}</td>`).join("")}</tr>`;
    const table = this.card("tab", `<h3>${icon("mdi:leaf")}Balance de carbono (kg CO₂)</h3><table><tr><th></th><th class="r">Hoy</th><th class="r">Mes</th><th class="r">Año</th><th class="r">Total</th></tr>${r("Evitado (solar)", "evitado_kg", C.lime)}${r("Red eléctrica", "red_kg", C.cyan)}${r("Gas", "gas_kg", C.violet)}${r("Huella neta", "neto_kg", C.text)}</table><div class="small muted" style="margin-top:6px">Red: ${fmt(this.A("co2_evitado", "factor_red_kg_kwh"), 3)} kg CO₂/kWh. Cámbialo en Configurar → CO₂.</div>`, { c: C.lime });
    const m = toNum(this.A("autosuficiencia", "mes"), 0), y = toNum(this.A("autosuficiencia", "ano"), 0);
    const indep = this.card("ind", `<h3>${icon("mdi:shield-sun")}Independencia energética</h3><div class="row"><div class="n">Este mes</div><div class="bar"><i style="--b:${C.lime};width:${m}%"></i></div><div class="x"><b>${fmt(m, 0)} %</b></div></div><div class="row"><div class="n">Este año</div><div class="bar"><i style="--b:${C.lime};width:${y}%"></i></div><div class="x"><b>${fmt(y, 0)} %</b></div></div>`, { c: C.lime });
    return [
      { cls: "w2", cards: [this.title("t", "Huella de carbono", "Lo que dejas de emitir gracias al sol", "mdi:leaf-circle", C.lime), hero,
        this.card("g1", gauge(this.N("autosuficiencia"), 0, 100, C.lime, "Autosuficiencia hoy", "%"), { c: C.lime, w: 6, click: this.id("autosuficiencia") }),
        this.card("g2", gauge(this.N("autoconsumo"), 0, 100, C.lime, "Autoconsumo hoy", "%"), { c: C.lime, w: 6, click: this.id("autoconsumo") }), indep] },
      { cls: "w2", cards: [table, this.chartCard("m", "CO₂ por meses (kg)", C.lime, { kind: "months", unit: "kg", count: 12, series: [{ name: "Evitado", field: "co2_evitado", color: C.lime }, { name: "Red", field: "co2_red", color: C.cyan }, { name: "Gas", field: "co2_gas", color: C.violet }] })] },
    ];
  }

  // ---------------------------------------------------------------- 9 gas
  v_gas() {
    const g = this.cfg.gas || {};
    if (!Object.keys(g).length) return [{ cards: [this.title("t", "Gas", "", "mdi:fire", C.violet), this.empty("e", "Instala Gas TUR (se detecta solo) o indica tus sensores en Configurar → Gas.")] }];
    const cards = [this.title("t", "Gas", "Consumo y coste", "mdi:fire", C.violet)];
    const kwhG = this.A("consumo_gas", "kwh") || {};
    cards.push(this.kpi("hoy", g.consumo_hoy || this.id("consumo_gas"), `${fmt(g.consumo_hoy ? this.n(g.consumo_hoy) : this.N("consumo_gas"), 2)} m³`, `Hoy · ${fmt(kwhG.hoy, 1)} kWh`, "mdi:meter-gas", C.violet, 6));
    if (g.coste_hoy) cards.push(this.kpi("ch", g.coste_hoy, eur(this.n(g.coste_hoy)), "Gasto de hoy", "mdi:fire", C.violet, 6));
    if (g.coste_mes) cards.push(this.kpi("cm", g.coste_mes, eur(this.n(g.coste_mes)), "Este mes", "mdi:calendar-month", C.violet, 6));
    if (g.caudal) cards.push(this.kpi("cau", g.caudal, `${fmt(this.n(g.caudal), 3)} m³/h`, "Caudal ahora", "mdi:gauge", C.violet, 6));
    if (g.precio_kwh) cards.push(this.kpi("pr", g.precio_kwh, `${fmt(this.n(g.precio_kwh), 5)} €/kWh`, "Precio del gas", "mdi:cash", C.violet, 6));
    if (g.lectura) cards.push(this.kpi("lec", g.lectura, `${fmt(this.n(g.lectura), 2)} m³`, "Lectura del contador", "mdi:counter", C.violet, 6));
    cards.push(this.card("cost", `<button class="btn full" style="--c:${C.gold}" data-tab="coste">${icon("mdi:cash-multiple")}Ver la factura del gas en Coste</button>`, { c: C.gold }));
    const charts = [];
    if (g.caudal) charts.push(this.chartCard("cau24", "Caudal 24 h (m³/h)", C.violet, { kind: "history", hours: 24, unit: "m³/h", bucket: 10, series: [{ name: "Caudal", entity: g.caudal, color: C.violet, type: "area" }] }));
    charts.push(this.chartCard("g30", "Gas 30 días (m³)", C.violet, { kind: "days", unit: "m³", series: [{ name: "Gas", field: "gas_m3", color: C.violet }] }));
    charts.push(this.chartCard("g12", "Gas por meses (m³)", C.violet, { kind: "months", unit: "m³", count: 12, series: [{ name: "Gas", field: "gas_m3", color: C.violet }] }));
    return [{ cards }, { cls: "w2", cards: charts }];
  }

  // ---------------------------------------------------------------- 10 luces
  v_luces() {
    const lights = this.cfg.lights || [];
    const on = lights.filter((l) => this.s(l.entity) === "on");
    const off = lights.filter((l) => ["unavailable", undefined].includes(this.s(l.entity))).length;
    const head = [
      this.title("t", "Iluminación", "Todas las luces de la casa", "mdi:lightbulb-group", C.gold),
      this.kpi("on", null, `${on.length} / ${lights.length}`, `Encendidas · ${on.filter((l) => !l.outdoor).length} dentro · ${on.filter((l) => l.outdoor).length} fuera`, "mdi:lightbulb-group", C.gold, 6),
      this.kpi("na", null, String(off), "Sin conexión", "mdi:lan-disconnect", off ? C.red : C.green, 6),
      this.card("off", `<button class="btn full" style="--c:${C.gold}" data-press="${this.id("apagar_luces")}" data-confirm="¿Apagar todas las luces?">${icon("mdi:lightbulb-group-off")}Apagar todas</button>`, { c: C.gold }),
    ];
    const lightCard = (l) => {
      const s = this.s(l.entity), isOn = s === "on";
      const br = Math.round(((toNum(this.a(l.entity, "brightness"), 0)) / 255) * 100);
      const slider = l.dimmable ? `<input type="range" min="1" max="100" value="${isOn ? br : 0}" data-bright="${esc(l.entity)}" style="margin-top:8px">` : "";
      return this.card("l" + l.entity, `<div class="light ${isOn ? "on" : "off"}"><div class="kpi" style="flex:1"><div class="ic" data-toggle="${esc(l.entity)}">${icon(isOn ? "mdi:lightbulb-on" : "mdi:lightbulb-outline")}</div><div class="grow" data-more="${esc(l.entity)}" style="cursor:pointer"><div style="font-weight:700">${esc(l.name)}</div><div class="l">${s === "unavailable" ? `<span style="color:${C.red}">Sin conexión</span>` : isOn ? (l.dimmable ? `Encendida · ${br} %` : "Encendida") : "Apagada"}</div></div></div></div>${slider}`, { c: isOn ? C.gold : "#2a3b55", w: 6 });
    };
    const inside = lights.filter((l) => !l.outdoor), outside = lights.filter((l) => l.outdoor);
    const secs = [{ cards: head }];
    if (inside.length) secs.push({ cards: [this.title("ti", "Interior", "", "mdi:home-lightbulb", C.gold), ...inside.map(lightCard)] });
    if (outside.length) secs.push({ cards: [this.title("to", "Exterior", "", "mdi:outdoor-lamp", C.gold), ...outside.map(lightCard)] });
    if (!lights.length) secs.push({ cards: [this.empty("e", "No hay luces. Si las añades a Home Assistant, pulsa «Regenerar panel».")] });
    return secs;
  }

  // ---------------------------------------------------------------- 11 clima
  v_clima() {
    const temps = this.cfg.temperatures || [];
    const ext = this.set_("temperatura_exterior");
    const extV = ext ? (ext.startsWith("weather.") ? toNum(this.a(ext, "temperature")) : this.n(ext)) : null;
    const head = [
      this.title("t", "Temperaturas", "Clima de cada estancia", "mdi:thermometer", C.orange),
      this.kpi("avg", this.id("temperatura_interior"), `${fmt(this.N("temperatura_interior"), 1)} °C`, `Media interior · ▲ ${fmt(this.A("temperatura_interior", "maxima"), 1)} ${esc(this.A("temperatura_interior", "maxima_nombre") || "")} · ▼ ${fmt(this.A("temperatura_interior", "minima"), 1)} ${esc(this.A("temperatura_interior", "minima_nombre") || "")}`, "mdi:home-thermometer", C.orange, 12),
      this.kpi("hum", this.id("humedad_interior"), `${fmt(this.N("humedad_interior"), 0)} %`, "Humedad media", "mdi:water-percent", C.blue, 6),
    ];
    if (ext) head.push(this.kpi("ext", ext, `${fmt(extV, 1)} °C`, "Exterior", "mdi:thermometer", C.blue, 6));
    const list = temps.map((e) => ({ e, n: this.name(e), v: this.n(e) })).filter((x) => x.v !== null).sort((a, b) => b.v - a.v);
    const col = (v) => (v >= 28 ? C.red : v >= 24 ? C.orange : v >= 19 ? C.green : v >= 14 ? C.blue : C.violet);
    const heat = list.length ? this.card("heat", `<h3>${icon("mdi:thermometer-lines")}Mapa de calor</h3>${list.map((x) => `<div class="row" data-more="${esc(x.e)}" style="cursor:pointer"><div class="n">${esc(x.n)}</div><div class="bar"><i style="--b:${col(x.v)};width:${Math.max(3, Math.min(100, ((x.v + 5) / 40) * 100))}%"></i></div><div class="x" style="color:${col(x.v)}"><b>${fmt(x.v, 1)} °C</b></div></div>`).join("")}`, { c: C.orange }) : null;
    const climates = (this.cfg.climates || []).map((e) => {
      const st = this.st(e);
      if (!st) return null;
      const a = st.attributes, cur = toNum(a.current_temperature), tgt = toNum(a.temperature), act = a.hvac_action || st.state;
      const heating = ["heating", "heat"].includes(act);
      return this.card("cl" + e, `<div class="thermo"><div style="font-weight:700;cursor:pointer" data-more="${esc(e)}">${esc(this.name(e))}</div>
        ${gauge(cur, 5, 30, heating ? C.orange : C.blue, act === "off" ? "Apagado" : heating ? "Calentando" : act === "idle" ? "En espera" : act, "°C actual", 130)}
        <div class="ctr"><button class="btn" style="--c:${C.blue}" data-temp="${esc(e)}" data-delta="-0.5">−</button><div><div class="small muted">Objetivo</div><div style="font-size:20px;font-weight:800;color:${C.orange}">${tgt === null ? "—" : fmt(tgt, 1) + " °C"}</div></div><button class="btn" style="--c:${C.orange}" data-temp="${esc(e)}" data-delta="0.5">+</button></div>
        ${isNum(a.current_humidity) ? `<div class="small muted" style="margin-top:6px">Humedad ${fmt(a.current_humidity, 0)} %</div>` : ""}</div>`, { c: heating ? C.orange : C.blue, w: 6 });
    }).filter(Boolean);
    const secs = [{ cards: [...head, ...(heat ? [heat] : [])] }];
    if (climates.length) secs.push({ cls: climates.length > 2 ? "w2" : "", cards: [this.title("tc", "Calefacción y climatización", "", "mdi:radiator", C.orange), ...climates] });
    const charts = [];
    if (temps.length) charts.push(this.chartCard("t24", "Temperaturas 24 h (°C)", C.orange, { kind: "history", hours: 24, unit: "°C", bucket: 15, height: 280, series: temps.slice(0, 12).map((e, i) => ({ name: this.name(e), entity: e, color: PALETTE[i % PALETTE.length] })) }));
    if ((this.cfg.humidities || []).length) charts.push(this.chartCard("h24", "Humedad 24 h (%)", C.blue, { kind: "history", hours: 24, unit: "%", bucket: 15, series: this.cfg.humidities.slice(0, 8).map((e, i) => ({ name: this.name(e), entity: e, color: PALETTE[(i + 6) % PALETTE.length] })) }));
    if (charts.length) secs.push({ cls: "w2", cards: charts });
    return secs;
  }

  // ---------------------------------------------------------------- 12 riego
  v_riego() {
    const zones = this.cfg.zones || [];
    if (!zones.length) return [{ cards: [this.title("t", "Riego", "", "mdi:sprinkler-variant", C.blue), this.empty("e", "Añade cada zona en la integración → «Añadir zona de riego».")] }];
    const watering = this.S("riego_activo") === "on";
    const skip = this.S("omitir_si_llueve") === "on";
    const rain = this.set_("lluvia_sensor");
    const head = [
      this.title("t", "Riego", "Zonas, humedad del suelo y lluvia", "mdi:sprinkler-variant", C.blue),
      this.kpi("act", this.id("riego_activo"), watering ? "Regando" : "Parado", watering ? "Hay alguna válvula abierta" : "Todas las válvulas cerradas", watering ? "mdi:sprinkler-variant" : "mdi:water-off-outline", watering ? C.blue : C.muted, 6),
      this.card("skip", `<div class="kpi" data-toggle="${this.id("omitir_si_llueve")}" style="cursor:pointer"><div class="ic">${icon(skip ? "mdi:weather-pouring" : "mdi:weather-sunny")}</div><div><div class="v">${skip ? "Sí" : "No"}</div><div class="l">Omitir si llueve${rain ? ` · ahora ${["on", "rain", "rainy"].includes(this.s(rain)) ? "llueve" : "no llueve"}` : ""}</div></div></div>`, { c: C.blue, w: 6 }),
      this.card("stop", `<button class="btn full" style="--c:${C.red}" data-press="${this.id("parar_riego")}" data-confirm="¿Cerrar todas las válvulas?">${icon("mdi:water-off")}Parar todo</button>`, { c: C.red }),
    ];
    const secs = [{ cards: head }];
    for (const z of zones) {
      const open = ["on", "open", "opening"].includes(this.s(z.valve));
      const rem = this.N(z.id + ":riego_restante", 0);
      const minE = this.id(z.id + ":minutos_riego");
      const mins = this.n(minE, 10);
      const remE = this.id(z.id + ":riego_restante");
      const last = this.a(remE, "ultimo_riego"), lastMin = this.a(remE, "ultimo_riego_minutos");
      const soil = z.soil ? this.n(z.soil) : null;
      const html = `<div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><div class="kpi"><div class="ic ${open ? "pulse" : ""}" data-toggle="${esc(z.valve)}" style="cursor:pointer">${icon(open ? "mdi:sprinkler-variant" : "mdi:sprinkler")}</div><div><div class="v">${esc(z.name)}</div><div class="l">${open ? (rem > 0 ? `Regando · quedan ${fmt(rem, 0)} min` : "Válvula abierta") : "Cerrada"} · último ${last ? fmtDate(last, true) : "—"}${lastMin ? ` (${fmt(lastMin, 0)} min)` : ""}</div></div></div>
        ${soil !== null ? `<div style="width:110px" data-more="${esc(z.soil)}">${gauge(soil, 0, 100, soil < 20 ? C.amber : C.blue, "Suelo", "%", 110)}</div>` : ""}</div>
        <div class="sim"><label>Minutos de riego</label><input type="range" min="1" max="60" step="1" value="${mins}" data-number="${minE}"><b>${fmt(mins, 0)} min</b></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">${open ? `<button class="btn full" style="--c:${C.red}" data-toggle="${esc(z.valve)}">${icon("mdi:stop")}Cerrar</button>` : `<button class="btn full" data-press="${this.id(z.id + ":regar")}">${icon("mdi:play")}Regar ${fmt(mins, 0)} min</button>`}<button class="btn full" style="--c:${C.muted}" data-more="${esc(z.valve)}">${icon("mdi:history")}Historial</button></div>`;
      secs[0].cards.push(this.card("z" + z.id, html, { c: C.blue, cls: open ? "" : "" }));
    }
    const soils = zones.filter((z) => z.soil);
    if (soils.length) secs.push({ cls: "w2", cards: [this.chartCard("soil", "Humedad del suelo 7 días (%)", C.blue, { kind: "history", hours: 168, unit: "%", bucket: 60, min: 0, max: 100, series: soils.map((z, i) => ({ name: z.name, entity: z.soil, color: PALETTE[(i + 6) % PALETTE.length] })) })] });
    secs.push({ cls: "w2", cards: [this.chartCard("valves", "Válvulas 7 días", C.blue, { kind: "history", hours: 168, unit: "", bucket: 5, min: 0, max: zones.length, series: zones.map((z, i) => ({ name: z.name, entity: z.valve, color: PALETTE[(i + 6) % PALETTE.length], step: true })) })] });
    return secs;
  }

  v_config() {
    const r = this._rotLoad();
    const keys = this._rotKeys();
    const chip = (act, v, label, on, extra = "") => `<button class="chip ${on ? "on" : ""}" data-rot="${act}" data-v="${esc(v)}">${extra}${esc(label)}</button>`;
    const power = `<button class="btn full" style="--c:${r.on ? C.green : C.muted}" data-rot="toggle">${icon(r.on ? "mdi:pause-circle-outline" : "mdi:play-circle-outline")}${r.on ? "Rotación activada · pulsa para parar" : "Rotación desactivada · pulsa para activar"}</button>`;
    const warn = r.on && keys.length < 2 ? `<div class="small" style="color:${C.amber};margin-top:8px">⚠ Marca al menos dos pestañas para que haya algo que rotar.</div>` : "";
    const rotCard = this.card(
      "rot",
      `<h3>${icon("mdi:monitor-dashboard")}Cambio automático de pestañas</h3>${power}
      <div class="small muted" style="margin:12px 0 6px">Tiempo en cada pestaña</div><div class="chips">${ROT_SECS.map((s) => chip("secs", s, fmtSecs(s), s === r.secs)).join("")}</div>
      <div class="small muted" style="margin:12px 0 6px">Si tocas la pantalla, seguir pasando pestañas tras</div><div class="chips">${ROT_RESUME.map((s) => chip("resume", s, fmtSecs(s), s === r.resume)).join("")}</div>
      ${warn}
      <div class="small muted" style="margin-top:10px">También puedes activarlo con el botón <b>Rotar</b> de la barra. No cambia de pestaña mientras estás en Configuración ni en el modo Diseño.</div>`,
      { c: C.cyan }
    );
    const tabsCard = this.card(
      "rtabs",
      `<h3>${icon("mdi:tab-search")}Pestañas que se muestran</h3>
      <div class="chips">${TABS.filter((t) => t[0] !== "config").map(([k, l, ic]) => chip("tab", k, l, !r.off.includes(k), icon(ic))).join("")}</div>
      <div class="chips" style="margin-top:12px"><button class="chip" data-rot="all">Todas</button><button class="chip" data-rot="none">Ninguna</button></div>
      <div class="small muted" style="margin-top:10px">${keys.length} de ${TABS.length - 1} pestañas en la rotación. Estos ajustes se guardan solo en este dispositivo: la tablet y el PC pueden tener los suyos.</div>`,
      { c: C.violet }
    );
    return [{ cards: [this.title("t", "Configuración", "Ajustes del panel en este dispositivo", "mdi:cog", C.cyan)] }, { cls: "w2", cards: [rotCard, tabsCard] }];
  }
}

// Valve states are text: map on/open to 1 for the valve chart.
const _origPoints = CentroControlPanel.prototype._points;
CentroControlPanel.prototype._points = function (hist, entity, opts) {
  const rows = hist?.[entity] || [];
  if (rows.length && rows.every((r) => !isNum(r.s))) {
    const idx = (this.cfg.zones || []).findIndex((z) => z.valve === entity);
    const on = (s) => ["on", "open", "opening"].includes(s);
    const pts = rows.map((r) => [(r.lu ?? r.lc ?? 0) * 1000, on(r.s) ? idx + 0.8 : idx]);
    if (pts.length) pts.push([Date.now(), pts[pts.length - 1][1]]);
    return pts;
  }
  return _origPoints.call(this, hist, entity, opts);
};

if (!customElements.get("centro-control-panel")) customElements.define("centro-control-panel", CentroControlPanel);
