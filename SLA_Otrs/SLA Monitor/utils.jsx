// Shared helpers + small presentational components
const { useState, useMemo, useEffect, useRef } = React;

// ---------- formatters ----------
function fmtDuration(sec) {
  if (!sec || sec <= 0) return "0 сек";
  if (sec < 60) return `${Math.round(sec)} сек`;
  if (sec < 3600) return `${Math.round(sec / 60)} мин`;
  const h = Math.floor(sec / 3600);
  const m = Math.round((sec % 3600) / 60);
  if (h < 24) return m === 0 ? `${h} ч` : `${h} ч ${m} мин`;
  const d = Math.floor(h / 24);
  const hr = h % 24;
  return hr === 0 ? `${d} д` : `${d} д ${hr} ч`;
}
function fmtNum(n) {
  return n.toLocaleString("ru-RU");
}
function fmtMinutes(m) {
  if (!m || m <= 0) return "0 мин";
  if (m < 60) return `${m} мин`;
  const h = Math.floor(m / 60);
  const mn = m % 60;
  if (h < 24) return mn === 0 ? `${h} ч` : `${h} ч ${mn} мин`;
  const d = Math.floor(h / 24);
  return `${d} д ${h % 24} ч`;
}
function pctClass(p) {
  if (p >= 95) return "ok";
  if (p >= 90) return "warn";
  if (p >= 80) return "bad";
  return "crit";
}
function countClass(n, total) {
  if (n === 0) return "zero";
  const r = n / Math.max(total, 1);
  if (r >= 0.2) return "crit";
  if (r >= 0.1) return "bad";
  return "warn";
}
window.fmt = { fmtDuration, fmtNum, fmtMinutes, pctClass, countClass };

// ---------- tiny icons (inline svg) ----------
function Icon({ name, size = 14, color = "currentColor" }) {
  const map = {
    dashboard: "M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z",
    fund: "M4 19h16v2H4zM2 17h2v-7H2zm5 0h2V8H7zm5 0h2V5h-2zm5 0h2v-9h-2z",
    ticket: "M6 2h12a2 2 0 0 1 2 2v16a1 1 0 0 1-1.6.8L17 19l-2.4 1.8a1 1 0 0 1-1.2 0L11 19l-2.4 1.8a1 1 0 0 1-1.2 0L5 19l-2.4 1.8A1 1 0 0 1 1 20V4a2 2 0 0 1 2-2zm1 6h10v2H7V8zm0 4h10v2H7v-2z",
    team: "M16 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-2.67 0-8 1.34-8 4v3h16v-3c0-2.66-5.33-4-8-4zm8 0c-.29 0-.62.02-.97.05A5.5 5.5 0 0 1 18 17v3h6v-3c0-2.66-5.33-4-8-4z",
    clock: "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm.5-13H11v6l5.2 3.2.8-1.3-4.5-2.7z",
    settings: "M19.4 13c.04-.3.06-.6.06-1s-.02-.7-.06-1l2.1-1.6a.5.5 0 0 0 .1-.6l-2-3.4a.5.5 0 0 0-.6-.2l-2.4 1a7 7 0 0 0-1.7-1L14.6 3a.5.5 0 0 0-.5-.4h-4a.5.5 0 0 0-.5.4l-.3 2.5a7 7 0 0 0-1.7 1l-2.4-1a.5.5 0 0 0-.6.2l-2 3.4a.5.5 0 0 0 .1.6L4.7 11c-.04.3-.06.6-.06 1s.02.7.06 1l-2.1 1.6a.5.5 0 0 0-.1.6l2 3.4c.1.2.4.3.6.2l2.4-1a7 7 0 0 0 1.7 1l.3 2.5c.04.3.3.5.5.5h4c.3 0 .5-.2.5-.4l.3-2.5a7 7 0 0 0 1.7-1l2.4 1c.2.1.5 0 .6-.2l2-3.4a.5.5 0 0 0-.1-.6L19.4 13zM12 15a3 3 0 1 1 0-6 3 3 0 0 1 0 6z",
    bug: "M9 1v2h6V1H9zm1 4h4v2h2.4l1.1-1.8 1.7 1L18 8h2v2h-3v1h3v2h-3v1h3v2h-2l1 1.6-1.7 1.1L16.4 17H13v-2h-2v2H7.6l-1.1 1.7-1.7-1L6 16H4v-2h3v-1H4v-2h3v-1H4V8h2L4.8 6.2 6.5 5.2 7.6 7H10V5z",
    file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z",
    upload: "M12 4l-1.4 1.4L13.6 8H4v2h9.6l-3 2.6L12 14l6-5-6-5zM4 16h16v4H4z",
    warn: "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
    chev: "M6 9l6 6 6-6",
    close: "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    search: "M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z",
    download: "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
    filter: "M10 18h4v-2h-4v2zM3 6v2h18V6H3zm3 7h12v-2H6v2z",
    refresh: "M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.74 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
    arrow_up: "M7 14l5-5 5 5z",
    arrow_down: "M7 10l5 5 5-5z",
    bell: "M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6V11c0-3.07-1.63-5.64-4.5-6.32V4a1.5 1.5 0 0 0-3 0v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
    bolt: "M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.96 17.55 11 21 11 21z",
    queues: "M3 5h2v14H3V5zm4 0h2v14H7V5zm4 0h10v4H11V5zm0 6h10v4H11v-4zm0 6h10v4H11v-4z",
    list: "M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z",
    split: "M11 4H4v7h7V4zm0 9H4v7h7v-7zm9 0h-7v7h7v-7zm0-9h-7v7h7V4z",
    matrix: "M4 4h6v6H4V4zm0 10h6v6H4v-6zm10-10h6v6h-6V4zm0 10h6v6h-6v-6z",
    fire: "M12 23a8 8 0 0 0 8-8c0-2.5-1-4.83-2.39-6.5C16.5 11 13 12 13 12s2-7-5-11c1 5-5 8-5 14a8 8 0 0 0 9 8z",
    target: "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm0-13a5 5 0 1 0 5 5 5 5 0 0 0-5-5zm0 8a3 3 0 1 1 3-3 3 3 0 0 1-3 3z",
  };
  const path = map[name];
  if (!path) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden="true">
      <path d={path}/>
    </svg>
  );
}
window.Icon = Icon;

// ---------- Sparkline ----------
function Sparkline({ data, color = "#fa8c16", height = 22, width = 84, fillOpacity = 0.15 }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data, 1);
  const stepX = width / (data.length - 1 || 1);
  const points = data.map((d, i) => `${i * stepX},${height - (d / max) * (height - 2) - 1}`).join(" ");
  const area = `0,${height} ${points} ${width},${height}`;
  // Highlight the last point
  const last = data[data.length - 1];
  const lx = (data.length - 1) * stepX;
  const ly = height - (last / max) * (height - 2) - 1;
  return (
    <svg width={width} height={height} className="spark" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <polygon points={area} fill={color} fillOpacity={fillOpacity} />
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
      <circle cx={lx} cy={ly} r="2" fill={color}/>
    </svg>
  );
}
window.Sparkline = Sparkline;

// ---------- Sortable table head ----------
function SortHead({ children, k, sort, setSort, align = "left", className = "" }) {
  const active = sort.key === k;
  return (
    <th
      className={`sortable ${align === "right" ? "num" : ""} ${active ? "sorted" : ""} ${className}`}
      onClick={() => setSort((s) => ({ key: k, dir: s.key === k && s.dir === "desc" ? "asc" : "desc" }))}
    >
      {children}
      <span className="sort-arrow">
        {active ? (sort.dir === "desc" ? "↓" : "↑") : "↕"}
      </span>
    </th>
  );
}
window.SortHead = SortHead;

// ---------- KPI card ----------
function Kpi({ label, value, icon, accent, hint, delta }) {
  return (
    <div className={`kpi ${accent ? "accent-" + accent : ""}`}>
      <div className="kpi-label">
        {icon}
        <span>{label}</span>
      </div>
      <div className="kpi-value">{value}</div>
      {(hint || delta) && (
        <div className={`kpi-delta ${delta && delta > 0 ? "up" : delta && delta < 0 ? "down" : ""}`}>
          {delta != null && (delta > 0 ? "▲" : delta < 0 ? "▼" : "—")}
          <span>{delta != null ? `${Math.abs(delta)}%` : ""}</span>
          {hint && <span style={{ color: "var(--color-text-tertiary)", marginLeft: delta != null ? 4 : 0 }}>{hint}</span>}
        </div>
      )}
    </div>
  );
}
window.Kpi = Kpi;

// ---------- Pct cell ----------
function PctCell({ pct, breached, total }) {
  const cls = pctClass(pct);
  return (
    <div className={`pct-cell ${cls}`}>
      <div className="num">{pct}%</div>
      <div className="bar"><i style={{ width: `${Math.max(2, pct)}%` }}/></div>
    </div>
  );
}
window.PctCell = PctCell;

// ---------- Count pill ----------
function CountPill({ value, total, kind = "auto" }) {
  const cls = value === 0 ? "zero" : kind === "auto" ? countClass(value, total) : kind;
  return <span className={`count-pill ${cls}`}>{value === 0 ? "0" : fmtNum(value)}</span>;
}
window.CountPill = CountPill;
