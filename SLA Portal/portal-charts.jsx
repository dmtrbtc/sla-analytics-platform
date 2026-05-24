// Inline SVG chart components for SLA Portal
const { useState: useStateC, useMemo: useMemoC, useRef: useRefC, useEffect: useEffectC } = React;

// ============================================================
// Utility — format
// ============================================================
const fmtDate = (d) => {
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}`;
};
const fmtDateFull = (d) => {
  const p = (n) => String(n).padStart(2, "0");
  const wd = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"][d.getDay()];
  return `${p(d.getDate())}.${p(d.getMonth() + 1)} · ${wd}`;
};
const fmtNum = (n) => n == null ? "—" : n.toLocaleString("ru-RU");

window.fmtDate = fmtDate;
window.fmtDateFull = fmtDateFull;
window.fmtNum = fmtNum;

// ============================================================
// StackedAreaChart — daily breach trend, two layers
// ============================================================
function StackedAreaChart({ data, height = 280, showLegend = true, mode = "stack" }) {
  const wrapRef = useRefC(null);
  const [hover, setHover] = useStateC(null);
  const [w, setW] = useStateC(900);

  useEffectC(() => {
    if (!wrapRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const cr = entries[0].contentRect;
      setW(cr.width);
    });
    obs.observe(wrapRef.current);
    return () => obs.disconnect();
  }, []);

  const pad = { l: 44, r: 16, t: 16, b: 28 };
  const iw = Math.max(100, w - pad.l - pad.r);
  const ih = height - pad.t - pad.b;

  const maxStack = Math.max(...data.map((d) => d.reaction + d.resolution), 1);
  const maxSplit = Math.max(...data.map((d) => Math.max(d.reaction, d.resolution)), 1);
  const max = mode === "stack" ? maxStack : maxSplit;

  const stepX = iw / (data.length - 1 || 1);
  const yScale = (v) => pad.t + ih - (v / max) * ih;

  // Build series paths
  const ptsReact = data.map((d, i) => [pad.l + i * stepX, yScale(d.reaction)]);
  const ptsResolve = data.map((d, i) => [pad.l + i * stepX, yScale(d.resolution)]);
  const ptsStack = data.map((d, i) => [pad.l + i * stepX, yScale(d.reaction + d.resolution)]);

  const pathFromPts = (pts) => pts.map(p => p.join(",")).join(" ");
  const areaFromPts = (pts) => `${pts[0][0]},${pad.t + ih} ${pathFromPts(pts)} ${pts[pts.length-1][0]},${pad.t + ih}`;

  // Y ticks
  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => Math.round((max * i) / ticks));

  // X ticks
  const xEvery = Math.max(1, Math.ceil(data.length / 8));

  // Hover handler
  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * w;
    const idx = Math.round((x - pad.l) / stepX);
    if (idx >= 0 && idx < data.length) {
      setHover({ idx, x: pad.l + idx * stepX });
    }
  };
  const onLeave = () => setHover(null);

  return (
    <div className="chart-frame" ref={wrapRef} onMouseMove={onMove} onMouseLeave={onLeave}>
      <svg width="100%" height={height} viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" style={{ display: "block" }}>
        {/* Grid */}
        {yTicks.map((v, i) => {
          const y = yScale(v);
          return (
            <g key={i}>
              <line x1={pad.l} x2={w - pad.r} y1={y} y2={y} stroke="#eef0f3" strokeWidth="1"/>
              <text x={pad.l - 8} y={y + 4} textAnchor="end" fontSize="10.5" fill="#98a2b3" fontFamily="JetBrains Mono">{v}</text>
            </g>
          );
        })}
        {/* X axis */}
        <line x1={pad.l} x2={w - pad.r} y1={pad.t + ih} y2={pad.t + ih} stroke="#e4e7ec" strokeWidth="1"/>
        {data.map((d, i) => {
          if (i % xEvery !== 0 && i !== data.length - 1) return null;
          const x = pad.l + i * stepX;
          return (
            <text key={i} x={x} y={height - pad.b + 18} textAnchor="middle" fontSize="10.5" fill="#98a2b3" fontFamily="JetBrains Mono">
              {fmtDate(d.date)}
            </text>
          );
        })}

        {/* Series */}
        {mode === "stack" ? (
          <>
            {/* Resolution baseline (full stack) */}
            <polygon points={areaFromPts(ptsStack)} fill="#8b5cf6" fillOpacity="0.18"/>
            {/* Reaction on top of zero (below stack curve) */}
            <polygon points={areaFromPts(ptsReact)} fill="#f59e0b" fillOpacity="0.32"/>
            <polyline points={pathFromPts(ptsStack)} fill="none" stroke="#8b5cf6" strokeWidth="2"/>
            <polyline points={pathFromPts(ptsReact)} fill="none" stroke="#f59e0b" strokeWidth="2"/>
          </>
        ) : (
          <>
            <polygon points={areaFromPts(ptsReact)} fill="#f59e0b" fillOpacity="0.14"/>
            <polygon points={areaFromPts(ptsResolve)} fill="#8b5cf6" fillOpacity="0.14"/>
            <polyline points={pathFromPts(ptsReact)} fill="none" stroke="#f59e0b" strokeWidth="2"/>
            <polyline points={pathFromPts(ptsResolve)} fill="none" stroke="#8b5cf6" strokeWidth="2"/>
          </>
        )}

        {/* Hover overlay */}
        {hover && (() => {
          const d = data[hover.idx];
          return (
            <g>
              <line x1={hover.x} x2={hover.x} y1={pad.t} y2={pad.t + ih} stroke="#101828" strokeWidth="1" strokeDasharray="3 3" opacity="0.4"/>
              <circle cx={hover.x} cy={yScale(d.reaction)} r="4" fill="#fff" stroke="#f59e0b" strokeWidth="2"/>
              <circle cx={hover.x} cy={mode === "stack" ? yScale(d.reaction + d.resolution) : yScale(d.resolution)} r="4" fill="#fff" stroke="#8b5cf6" strokeWidth="2"/>
            </g>
          );
        })()}
      </svg>

      {/* Tooltip */}
      {hover && (() => {
        const d = data[hover.idx];
        const left = (hover.x / w) * 100;
        return (
          <div className="chart-tooltip show" style={{ left: `${left}%`, top: pad.t + 30 }}>
            <div className="ttd">{fmtDateFull(d.date)}</div>
            <div className="tr"><span className="sw" style={{ background: "#f59e0b" }}/><span className="ll">Реакция</span><span className="vv">{d.reaction}</span></div>
            <div className="tr"><span className="sw" style={{ background: "#8b5cf6" }}/><span className="ll">Решение</span><span className="vv">{d.resolution}</span></div>
            <div className="tr" style={{ borderTop: "1px solid rgba(255,255,255,0.12)", paddingTop: 4, marginTop: 4 }}>
              <span className="ll">Всего тикетов</span><span className="vv">{d.total}</span>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
window.StackedAreaChart = StackedAreaChart;

// ============================================================
// HorizontalBarsChart — top queues by breaches (two segments)
// ============================================================
function HorizontalBarsChart({ data, max, height = 30 }) {
  const total = Math.max(...data.map((d) => d.reaction + d.resolution), 1);
  const M = max || total;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {data.map((d) => {
        const rW = (d.reaction / M) * 100;
        const sW = (d.resolution / M) * 100;
        const totalDay = d.reaction + d.resolution;
        return (
          <div key={d.id} className="hbar-row" style={{ display: "grid", gridTemplateColumns: "160px 1fr 60px", gap: 12, alignItems: "center", cursor: "pointer" }}
            onClick={() => d.onClick && d.onClick()}>
            <div style={{ fontSize: 12.5, color: "var(--ink-2)", fontFamily: "var(--font-mono)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={d.name}>{d.name}</div>
            <div style={{ position: "relative", height: 18, background: "var(--surface-3)", borderRadius: 5, display: "flex", overflow: "hidden" }}>
              <div style={{ width: `${rW}%`, background: "var(--reaction)", borderRadius: "5px 0 0 5px", transition: "width 0.4s" }} title={`Реакция: ${d.reaction}`}/>
              <div style={{ width: `${sW}%`, background: "var(--resolution)", transition: "width 0.4s" }} title={`Решение: ${d.resolution}`}/>
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, fontVariantNumeric: "tabular-nums", textAlign: "right" }}>{totalDay}</div>
          </div>
        );
      })}
    </div>
  );
}
window.HorizontalBarsChart = HorizontalBarsChart;

// ============================================================
// Heatmap — queue × hour
// ============================================================
function Heatmap({ rows, max, onCellClick }) {
  const M = max || Math.max(...rows.flatMap((r) => r.hours), 1);
  const colorFor = (v) => {
    if (v === 0) return "#f3f4f6";
    const t = v / M;
    // Light → deep crimson
    if (t < 0.15) return "#fff7ed";
    if (t < 0.30) return "#ffedd5";
    if (t < 0.50) return "#fed7aa";
    if (t < 0.70) return "#fdba74";
    if (t < 0.85) return "#fb923c";
    return "#ea580c";
  };
  return (
    <div className="hm-grid">
      {/* Header — hours */}
      <div className="hm-row head">
        <div className="qn"></div>
        {Array.from({ length: 24 }, (_, h) => (
          <div key={h} className="hm-cell" style={{ background: "transparent" }}>{h % 3 === 0 ? h : ""}</div>
        ))}
      </div>
      {rows.map((r) => (
        <div className="hm-row" key={r.queue_id}>
          <div className="qn" title={r.name}>{r.name}</div>
          {r.hours.map((v, h) => (
            <div
              key={h}
              className="hm-cell"
              style={{ background: colorFor(v) }}
              title={`${r.name} · ${String(h).padStart(2,"0")}:00 — ${v} нарушений`}
              onClick={() => onCellClick && onCellClick(r, h, v)}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
window.Heatmap = Heatmap;

// ============================================================
// HourBarChart — bar chart by hour-of-day
// ============================================================
function HourBarChart({ data, height = 140 }) {
  const wrapRef = useRefC(null);
  const [w, setW] = useStateC(360);
  useEffectC(() => {
    if (!wrapRef.current) return;
    const obs = new ResizeObserver((e) => setW(e[0].contentRect.width));
    obs.observe(wrapRef.current);
    return () => obs.disconnect();
  }, []);
  const pad = { l: 28, r: 4, t: 8, b: 18 };
  const iw = Math.max(60, w - pad.l - pad.r);
  const ih = height - pad.t - pad.b;
  const max = Math.max(...data, 1);
  const bw = iw / 24 - 1.5;
  return (
    <div ref={wrapRef}>
      <svg width="100%" height={height} viewBox={`0 0 ${w} ${height}`} style={{ display: "block" }}>
        {[0, 0.5, 1].map((t) => {
          const y = pad.t + ih * (1 - t);
          return <line key={t} x1={pad.l} x2={w - pad.r} y1={y} y2={y} stroke="#eef0f3"/>;
        })}
        <text x={pad.l - 4} y={pad.t + 8} textAnchor="end" fontSize="10" fill="#98a2b3" fontFamily="JetBrains Mono">{max}</text>
        <text x={pad.l - 4} y={pad.t + ih + 2} textAnchor="end" fontSize="10" fill="#98a2b3" fontFamily="JetBrains Mono">0</text>
        {data.map((v, h) => {
          const x = pad.l + h * (iw / 24);
          const bh = (v / max) * ih;
          return (
            <g key={h}>
              <rect x={x} y={pad.t + ih - bh} width={bw} height={bh} fill="var(--reaction)" opacity="0.8" rx="1.5"/>
              {h % 4 === 0 && (
                <text x={x + bw / 2} y={height - 4} textAnchor="middle" fontSize="9.5" fill="#98a2b3" fontFamily="JetBrains Mono">{h}</text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
window.HourBarChart = HourBarChart;

// ============================================================
// Inline sparkline
// ============================================================
function Spark({ data, color = "currentColor", w = 80, h = 22 }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = Math.max(max - min, 1);
  const stepX = w / (data.length - 1 || 1);
  const pts = data.map((d, i) => `${i * stepX},${h - ((d - min) / range) * (h - 4) - 2}`).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
    </svg>
  );
}
window.Spark = Spark;
