// Shared widgets and utilities for the SLA Operations Center
const { useState, useEffect, useMemo, useRef } = React;

// ===================== Format helpers =====================
function fmtNum(n)  { return (n == null ? "—" : n.toLocaleString("ru-RU")); }
function fmtMin(m, opts={}) {
  if (m == null) return "—";
  if (m === 0) return "0м";
  const abs = Math.abs(m);
  let s = "";
  if (abs < 60) s = `${Math.round(abs)}м`;
  else if (abs < 24*60) {
    const h = Math.floor(abs/60), mn = Math.round(abs%60);
    s = mn === 0 ? `${h}ч` : `${h}ч ${mn}м`;
  } else {
    const d = Math.floor(abs/(24*60)), h = Math.round((abs%(24*60))/60);
    s = h === 0 ? `${d}д` : `${d}д ${h}ч`;
  }
  return m < 0 ? `-${s}` : s;
}
function fmtSec(s) {
  if (!s) return "0с";
  if (s < 60) return `${Math.round(s)}с`;
  return fmtMin(Math.round(s/60));
}
function fmtTimeShort() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
window.opsFmt = { fmtNum, fmtMin, fmtSec, fmtTimeShort };

// ===================== Inline icons =====================
function Ico({ name, size = 14, color = "currentColor" }) {
  const paths = {
    dashboard: "M3 3h8v8H3V3zm0 10h8v8H3v-8zm10 0h8v8h-8v-8zm0-10h8v8h-8V3z",
    fund:      "M3 17h2v-7H3zm4 0h2V8H7zm4 0h2V5h-2zm4 0h2V8h-2zm4-9v9h2V8z",
    ticket:    "M4 4h16v6a2 2 0 0 0 0 4v6H4v-6a2 2 0 0 0 0-4V4z",
    queues:    "M4 5h4v4H4V5zm0 10h4v4H4v-4zm6-10h10v4H10V5zm0 10h10v4H10v-4z",
    risk:      "M1 21h22L12 2 1 21zm12-3h-2v-2h2zm0-4h-2v-4h2z",
    fire:      "M12 23a8 8 0 0 0 8-8c0-2.5-1-4.83-2.39-6.5C16.5 11 13 12 13 12s2-7-5-11c1 5-5 8-5 14a8 8 0 0 0 9 8z",
    settings:  "M19.4 13c.04-.3.06-.6.06-1s-.02-.7-.06-1l2.1-1.6L19.5 6l-2.4 1a7 7 0 0 0-1.7-1L14.6 3h-4l-.3 2.5a7 7 0 0 0-1.7 1L6.2 6.5 4.2 9.9 6.3 11.5c-.04.3-.06.6-.06 1s.02.7.06 1L4.2 15.1l2 3.4 2.4-1a7 7 0 0 0 1.7 1l.3 2.5h4l.3-2.5a7 7 0 0 0 1.7-1l2.4 1 2-3.4-2.1-1.6zM12 15a3 3 0 1 1 0-6 3 3 0 0 1 0 6z",
    bell:      "M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6V11c0-3.07-1.63-5.64-4.5-6.32V4a1.5 1.5 0 0 0-3 0v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
    refresh:   "M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.74 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
    download:  "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
    close:     "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    target:    "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm0-13a5 5 0 1 0 5 5 5 5 0 0 0-5-5zm0 8a3 3 0 1 1 3-3 3 3 0 0 1-3 3z",
    clock:     "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm.5-13H11v6l5.2 3.2.8-1.3-4.5-2.7z",
    bolt:      "M11 21h-1l1-7H7.5C7 14 7 13.7 7.07 13.5L13 3h1l-1 7h3.5c.5 0 .6.3.5.5L11 21z",
    bug:       "M9 1v2h6V1H9zm1 4h4v2h2.4l1.1-1.8 1.7 1L18 8h2v2h-3v1h3v2h-3v1h3v2h-2l1 1.6-1.7 1.1L16.4 17H13v-2h-2v2H7.6l-1.1 1.7-1.7-1L6 16H4v-2h3v-1H4v-2h3v-1H4V8h2L4.8 6.2 6.5 5.2 7.6 7H10V5z",
    swap:      "M6 4l-4 4h3v7h2V8h3L6 4zm9 5v7h-3l4 4 4-4h-3V9h-2z",
    user:      "M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0 2c-3.3 0-10 1.7-10 5v3h20v-3c0-3.3-6.7-5-10-5z",
    team:      "M16 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-2.67 0-8 1.34-8 4v3h16v-3c0-2.66-5.33-4-8-4zm8 0c-.29 0-.62.02-.97.05A5.5 5.5 0 0 1 18 17v3h6v-3c0-2.66-5.33-4-8-4z",
    search:    "M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z",
    chev:      "M9 6l6 6-6 6",
    chev_down: "M6 9l6 6 6-6",
    arrow_up:  "M7 14l5-5 5 5z",
    arrow_dn:  "M7 10l5 5 5-5z",
    flat:      "M5 11h14v2H5z",
    file:      "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z",
    pause:     "M6 4h4v16H6zm8 0h4v16h-4z",
    play:      "M8 5v14l11-7z",
    open:      "M14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3z",
  };
  const p = paths[name];
  if (!p) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d={p}/>
    </svg>
  );
}
window.Ico = Ico;

// ===================== Sparkline =====================
function MiniSpark({ data, color = "currentColor", w = 60, h = 22, fill = true, mode = "line" }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = Math.max(max - min, 1);
  const stepX = w / (data.length - 1 || 1);
  const ptsArr = data.map((d, i) => [i * stepX, h - ((d - min) / range) * (h - 4) - 2]);
  const points = ptsArr.map(p => p.join(",")).join(" ");
  const area = `0,${h} ${points} ${w},${h}`;
  if (mode === "bar") {
    const bw = (w / data.length) - 1;
    return (
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
        {data.map((d, i) => {
          const bh = ((d - min) / range) * (h - 2);
          return <rect key={i} x={i * (bw + 1)} y={h - bh} width={bw} height={bh} fill={color} opacity={0.65}/>;
        })}
      </svg>
    );
  }
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      {fill && <polygon points={area} fill={color} fillOpacity={0.18}/>}
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
      <circle cx={ptsArr[ptsArr.length-1][0]} cy={ptsArr[ptsArr.length-1][1]} r="2" fill={color}/>
    </svg>
  );
}
window.MiniSpark = MiniSpark;

// ===================== Health ring (donut SVG) =====================
function HealthRing({ pct, size = 48, stroke = 4, color, trackColor = "rgba(255,255,255,0.08)", showLabel = false, fontSize = 13 }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const auto = pct >= 92 ? "var(--ok)" : pct >= 85 ? "var(--warn)" : pct >= 75 ? "var(--high)" : "var(--crit)";
  const col = color || auto;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} stroke={trackColor} strokeWidth={stroke} fill="none"/>
        <circle cx={size/2} cy={size/2} r={r} stroke={col} strokeWidth={stroke} strokeLinecap="round" fill="none"
                strokeDasharray={c} strokeDashoffset={offset}
                style={{ transition: "stroke-dashoffset 0.5s ease, stroke 0.3s" }}/>
      </svg>
      {showLabel && (
        <div style={{
          position: "absolute", inset: 0, display: "grid", placeItems: "center",
          fontFamily: "var(--font-mono)", fontWeight: 700, fontSize, color: col,
          letterSpacing: "-0.3px",
        }}>{Math.round(pct)}</div>
      )}
    </div>
  );
}
window.HealthRing = HealthRing;

// ===================== Big circular gauge with two arcs =====================
function GaugeRing({ pct, size = 138, stroke = 12, color, trackColor = "rgba(255,255,255,0.06)" }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size/2} cy={size/2} r={r} stroke={trackColor} strokeWidth={stroke} fill="none"/>
      <circle cx={size/2} cy={size/2} r={r} stroke={color} strokeWidth={stroke} strokeLinecap="round" fill="none"
              strokeDasharray={c} strokeDashoffset={offset}
              style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: "stroke-dashoffset 0.5s" }}/>
    </svg>
  );
}
window.GaugeRing = GaugeRing;

// ===================== Delta indicator =====================
function Delta({ value, suffix = "%", invertGood = false }) {
  if (value == null) return null;
  const sign = value > 0 ? "up" : value < 0 ? "down" : "flat";
  const good = invertGood ? value < 0 : value > 0;
  const cls = sign === "flat" ? "flat" : good ? "down" : "up";
  return (
    <span className={`delta ${cls}`}>
      {sign === "up" ? <Ico name="arrow_up" size={11}/> : sign === "down" ? <Ico name="arrow_dn" size={11}/> : <Ico name="flat" size={11}/>}
      {Math.abs(value)}{suffix}
    </span>
  );
}
window.Delta = Delta;

// ===================== KPI Tile =====================
function KpiTile({ label, value, unit, hint, accent, delta, deltaInvert = false, spark, sparkColor, icon }) {
  return (
    <div className={`kpi-tile ${accent || ""}`}>
      <div className="head">
        {icon && <span className="ico">{icon}</span>}
        <span>{label}</span>
      </div>
      <div className="val">
        {value}{unit && <span className="unit"> {unit}</span>}
      </div>
      <div className="foot">
        <Delta value={delta} invertGood={deltaInvert}/>
        {hint && <span style={{ marginLeft: 2 }}>{hint}</span>}
      </div>
      {spark && (
        <div className="spark-mini">
          <MiniSpark data={spark} color={sparkColor || "rgba(255,255,255,0.35)"} w={60} h={20}/>
        </div>
      )}
    </div>
  );
}
window.KpiTile = KpiTile;
