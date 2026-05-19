// Shared utilities, icons, sparkline for the Executive view
const { useState, useEffect, useMemo, useRef } = React;

// --------- format helpers ---------
function fmtNum(n) { return n == null ? "—" : n.toLocaleString("ru-RU"); }
function fmtMin(m) {
  if (m == null) return "—";
  const abs = Math.abs(m);
  if (abs === 0) return "0 мин";
  let s;
  if (abs < 60) s = `${Math.round(abs)} мин`;
  else if (abs < 24*60) {
    const h = Math.floor(abs/60), mn = Math.round(abs % 60);
    s = mn === 0 ? `${h} ч` : `${h} ч ${mn} мин`;
  } else {
    const d = Math.floor(abs/(24*60)), h = Math.round((abs % (24*60))/60);
    s = h === 0 ? `${d} д` : `${d} д ${h} ч`;
  }
  return m < 0 ? `−${s}` : s;
}
function fmtSec(s) {
  if (!s) return "0 сек";
  if (s < 60) return `${Math.round(s)} сек`;
  return fmtMin(Math.round(s/60));
}
window.execFmt = { fmtNum, fmtMin, fmtSec };

// --------- icons ---------
function I({ n, s = 14 }) {
  const m = {
    dashboard: "M3 3h7v9H3V3zm0 11h7v7H3v-7zm9-11h9v7h-9V3zm0 9h9v9h-9v-9z",
    queues:    "M4 5h16v2H4V5zm0 6h16v2H4v-2zm0 6h16v2H4v-2z",
    tickets:   "M4 5h16a1 1 0 0 1 1 1v4a2 2 0 0 0 0 4v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4a2 2 0 0 0 0-4V6a1 1 0 0 1 1-1z",
    risk:      "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
    reports:   "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z",
    settings:  "M19.4 13c.04-.3.06-.6.06-1s-.02-.7-.06-1l2.1-1.6L19.5 6l-2.4 1a7 7 0 0 0-1.7-1L14.6 3h-4l-.3 2.5a7 7 0 0 0-1.7 1L6.2 6.5 4.2 9.9 6.3 11.5c-.04.3-.06.6-.06 1s.02.7.06 1L4.2 15.1l2 3.4 2.4-1a7 7 0 0 0 1.7 1l.3 2.5h4l.3-2.5a7 7 0 0 0 1.7-1l2.4 1 2-3.4-2.1-1.6zM12 15a3 3 0 1 1 0-6 3 3 0 0 1 0 6z",
    config:    "M22 4h-7v6h2v2H8v-2h2V4H3v6h2v4h6v2H8v6h7v-6h-3v-2h6v-4h2z",
    team:      "M16 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3zM8 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-2.67 0-8 1.34-8 4v2h10v-2c0-1 .27-1.84.74-2.55A11.32 11.32 0 0 0 8 13zm8 0c-.4 0-.83.03-1.27.09A5.45 5.45 0 0 1 16 17v2h8v-2c0-2.66-5.33-4-8-4z",
    incident:  "M12 2L1 21h22L12 2zm1 14h-2v-2h2zm0-4h-2V8h2z",
    clock:     "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm.5-13H11v6l5.2 3.2.8-1.3-4.5-2.7z",
    target:    "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm0-13a5 5 0 1 0 5 5 5 5 0 0 0-5-5zm0 8a3 3 0 1 1 3-3 3 3 0 0 1-3 3z",
    fire:      "M12 23a8 8 0 0 0 8-8c0-2.5-1-4.83-2.39-6.5C16.5 11 13 12 13 12s2-7-5-11c1 5-5 8-5 14a8 8 0 0 0 9 8z",
    download:  "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
    plus:      "M19 11h-6V5h-2v6H5v2h6v6h2v-6h6z",
    refresh:   "M17.65 6.35A8 8 0 0 0 12 4a8 8 0 1 0 7.74 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
    chev_dn:   "M6 9l6 6 6-6",
    chev_rt:   "M9 6l6 6-6 6",
    up:        "M7 14l5-5 5 5z",
    dn:        "M7 10l5 5 5-5z",
    flat:      "M5 11h14v2H5z",
    close:     "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    bell:      "M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6V11c0-3.07-1.63-5.64-4.5-6.32V4a1.5 1.5 0 0 0-3 0v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1z",
    help:      "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm1 17h-2v-2h2zm2.07-7.75l-.9.92A3.4 3.4 0 0 0 13 15h-2v-.5a3.5 3.5 0 0 1 1.04-2.5l1.25-1.27a2 2 0 0 0-3.41-1.4L8 8.43A4 4 0 0 1 15.85 10a3.18 3.18 0 0 1-.93 2.25z",
    play:      "M8 5v14l11-7z",
    bolt:      "M11 21h-1l1-7H7.5C7 14 7 13.7 7.07 13.5L13 3h1l-1 7h3.5c.5 0 .6.3.5.5L11 21z",
    filter:    "M3 4h18l-7 9v6l-4 2v-8z",
  };
  const p = m[n];
  if (!p) return null;
  return <svg width={s} height={s} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d={p}/></svg>;
}
window.I = I;

// --------- sparkline ---------
function Spark({ data, color = "#2563eb", w = 70, h = 22, fill = true }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = Math.max(max - min, 1);
  const stepX = w / (data.length - 1 || 1);
  const pts = data.map((d, i) => [i * stepX, h - ((d - min) / range) * (h - 4) - 2]);
  const polyline = pts.map(p => p.join(",")).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      {fill && <polygon points={`0,${h} ${polyline} ${w},${h}`} fill={color} fillOpacity={0.1}/>}
      <polyline points={polyline} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
    </svg>
  );
}
window.Spark = Spark;

// --------- delta indicator ---------
function Delta({ value, goodIsDown = false }) {
  if (value == null) return null;
  const sign = value > 0 ? "up" : value < 0 ? "dn" : "flat";
  const good = goodIsDown ? value < 0 : value > 0;
  const cls = sign === "flat" ? "flat" : good ? "good" : "bad";
  return (
    <span className={`delta ${cls}`}>
      <I n={sign === "up" ? "up" : sign === "dn" ? "dn" : "flat"} s={11}/>
      {Math.abs(value)}%
    </span>
  );
}
window.Delta = Delta;
