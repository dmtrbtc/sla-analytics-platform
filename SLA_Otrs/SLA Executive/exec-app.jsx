// SLA Executive — light enterprise dashboard. All widgets inline for clarity.

const NAV_GROUPS = [
  {
    head: "Аналитика",
    items: [
      { key: "overview", icon: "dashboard", label: "Обзор" },
      { key: "trends",   icon: "target",    label: "Тренды SLA" },
      { key: "queues",   icon: "queues",    label: "Очереди", count: 12 },
    ],
  },
  {
    head: "Операционная работа",
    items: [
      { key: "breaches", icon: "risk",     label: "Пробития", count: 23, danger: true },
      { key: "tickets",  icon: "tickets",  label: "Тикеты" },
      { key: "incidents",icon: "incident", label: "Инциденты", count: 2, danger: true },
      { key: "agents",   icon: "team",     label: "Команда" },
    ],
  },
  {
    head: "Конфигурация",
    items: [
      { key: "config",   icon: "config",   label: "Настройки SLA" },
      { key: "reports",  icon: "reports",  label: "Отчёты" },
      { key: "settings", icon: "settings", label: "Параметры" },
    ],
  },
];

function ExecApp() {
  const D = window.OPSDATA;
  const [t, setTweak] = useTweaks({
    show_chart: true,
    show_simulator: true,
    chart_overlay: "split",
    zebra_table: false,
  });

  const [active, setActive] = useState("overview");
  const [period, setPeriod] = useState("30d");
  const [filter, setFilter] = useState("all"); // all / critical / near / breached
  const [drawer, setDrawer] = useState({ open: false, kind: null, payload: null });

  useEffect(() => {
    const onEsc = (e) => { if (e.key === "Escape") setDrawer((d) => ({ ...d, open: false })); };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, []);

  // Build trend series: response & resolution breaches per day, last 30 (or N)
  const N = period === "7d" ? 7 : period === "90d" ? 90 : 30;
  const trend = useMemo(() => {
    const days = [];
    const total = D.QUEUES.reduce((s, q) => s + q.tickets, 0);
    for (let i = 0; i < N; i++) {
      const seed = Math.sin(i * 0.43) * 0.5 + Math.cos(i * 0.17) * 0.3;
      const baseR = Math.round((D.KPI.total_reaction_breach / N) * (1 + seed * 0.35));
      const baseS = Math.round((D.KPI.total_resolution_breach / N) * (1 - seed * 0.25));
      const totalDay = Math.round(total / N);
      days.push({
        day: i,
        date: new Date(Date.now() - (N - 1 - i) * 86400000),
        reaction: Math.max(0, baseR + Math.round((Math.sin(i * 0.7)) * 4)),
        resolution: Math.max(0, baseS + Math.round((Math.cos(i * 0.5)) * 3)),
        total: totalDay,
      });
    }
    return days;
  }, [N, D]);

  const breaches = useMemo(() => {
    let arr = D.AT_RISK;
    if (filter === "breached") arr = arr.filter((t) => t.r_over || t.s_over);
    else if (filter === "critical") arr = arr.filter((t) => t.tier === "crit");
    else if (filter === "near") arr = arr.filter((t) => t.tier !== "crit" && (t.r_used > 80 || t.s_used > 80));
    return arr;
  }, [filter, D.AT_RISK]);

  return (
    <div className="app">
      {/* SIDEBAR */}
      <aside className="side">
        <div className="brand">
          <div className="mark">SP</div>
          <div className="name">SLA Platform <span className="sub">enterprise</span></div>
        </div>
        {NAV_GROUPS.map((g) => (
          <div className="group" key={g.head}>
            <div className="head">{g.head}</div>
            {g.items.map((it) => (
              <div
                key={it.key}
                className={`nav-item ${active === it.key ? "active" : ""} ${it.danger ? "danger-flag" : ""}`}
                onClick={() => setActive(it.key)}
              >
                <span className="ico"><I n={it.icon} s={15}/></span>
                <span>{it.label}</span>
                {it.count != null && <span className="count">{it.count}</span>}
              </div>
            ))}
          </div>
        ))}
        <div className="spacer"/>
        <div className="footer">
          <div className="ava">АИ</div>
          <div className="meta">
            <div className="nm">Анна Иванова</div>
            <div className="role">SLA-менеджер</div>
          </div>
        </div>
      </aside>

      {/* MAIN */}
      <div className="main">
        <div className="topbar">
          <div className="crumb">
            <I n="dashboard" s={14}/>
            <span>Аналитика</span>
            <span className="sep">/</span>
            <b>Обзор SLA</b>
          </div>
          <div className="right">
            <input className="search" placeholder="Поиск тикета, очереди, агента..."/>
            <button className="btn ghost icon-only"><I n="bell" s={15}/></button>
            <button className="btn ghost icon-only"><I n="help" s={15}/></button>
          </div>
        </div>

        <div className="canvas">
          <div className="wrap">
            {/* Page header */}
            <div className="page-hdr">
              <div>
                <h1>Обзор SLA</h1>
                <div className="sub">Соблюдение реакции и решения по всем очередям за выбранный период.</div>
              </div>
              <div className="actions">
                <div className="seg">
                  <button className={period === "7d" ? "active" : ""} onClick={() => setPeriod("7d")}>7 дн</button>
                  <button className={period === "30d" ? "active" : ""} onClick={() => setPeriod("30d")}>30 дн</button>
                  <button className={period === "90d" ? "active" : ""} onClick={() => setPeriod("90d")}>90 дн</button>
                </div>
                <button className="btn"><I n="download" s={13}/>Выгрузка</button>
                <button className="btn primary"><I n="plus" s={13}/>Создать отчёт</button>
              </div>
            </div>

            {/* KPI row */}
            <KpiRow kpi={D.KPI}/>

            {/* SLA Trends */}
            {t.show_chart && <SlaTrendsChart trend={trend} overlay={t.chart_overlay} setOverlay={(v) => setTweak("chart_overlay", v)}/>}

            {/* Two column: Breaches table + Queue health */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 460px", gap: 20 }}>
              <BreachesTable tickets={breaches} filter={filter} setFilter={setFilter} onPick={(tk) => setDrawer({ open: true, kind: "ticket", payload: tk })}/>
              <QueueHealth queues={D.QUEUES} onPick={(q) => setDrawer({ open: true, kind: "queue", payload: q })}/>
            </div>

            {/* Simulator */}
            {t.show_simulator && <SlaSimulator queues={D.QUEUES}/>}

            <div style={{ fontSize: 11.5, color: "var(--text-3)", textAlign: "center", paddingTop: 8 }}>
              SLA Platform · обновлено только что · период {period}
            </div>
          </div>
        </div>
      </div>

      {/* Drawer */}
      <ExecDrawer drawer={drawer} onClose={() => setDrawer((d) => ({ ...d, open: false }))}/>

      {/* Tweaks */}
      <TweaksPanel title="Tweaks · Executive">
        <TweakSection label="Виджеты">
          <TweakToggle label="График трендов" value={t.show_chart} onChange={(v) => setTweak("show_chart", v)}/>
          <TweakToggle label="SLA-симулятор" value={t.show_simulator} onChange={(v) => setTweak("show_simulator", v)}/>
          <TweakToggle label="Чередование строк" value={t.zebra_table} onChange={(v) => setTweak("zebra_table", v)}/>
        </TweakSection>
        <TweakSection label="График">
          <TweakRadio
            label="Отображение"
            value={t.chart_overlay}
            options={[
              { value: "split", label: "Раздельно" },
              { value: "stack", label: "Стек" },
              { value: "pct",   label: "% SLA" },
            ]}
            onChange={(v) => setTweak("chart_overlay", v)}
          />
        </TweakSection>
      </TweaksPanel>

      <style>{`
        ${t.zebra_table ? `.table tbody tr:nth-child(2n) td { background: var(--surface-2); }` : ""}
      `}</style>
    </div>
  );
}

// ==================== KPI ROW ====================
function KpiRow({ kpi }) {
  const items = [
    { label: "SLA · Реакция",     value: `${kpi.reaction_pct}%`,   accent: kpi.reaction_pct >= 95 ? "ok" : kpi.reaction_pct >= 90 ? "warn" : "alert",
      delta: 1.2,  goodIsDown: false, foot: `${execFmt.fmtNum(kpi.total_reaction_breach)} нарушений`, spark: kpi.spark.health, sparkColor: "#16a34a", icon: "target" },
    { label: "SLA · Решение",     value: `${kpi.resolution_pct}%`, accent: kpi.resolution_pct >= 95 ? "ok" : kpi.resolution_pct >= 90 ? "warn" : "alert",
      delta: -2.1, goodIsDown: false, foot: `${execFmt.fmtNum(kpi.total_resolution_breach)} нарушений`, spark: kpi.spark.health.map((v)=>v-2), sparkColor: "#7c3aed", icon: "clock" },
    { label: "Тикеты в зоне риска", value: execFmt.fmtNum(kpi.tickets_at_risk), accent: "warn",
      delta: 6, goodIsDown: true, foot: "близко к пробитию SLA", spark: kpi.spark.at_risk, sparkColor: "#d97706", icon: "risk" },
    { label: "Активные нарушения", value: execFmt.fmtNum(kpi.active_breaches), accent: "alert",
      delta: 12, goodIsDown: true, foot: "за выбранный период", spark: kpi.spark.breaches, sparkColor: "#dc2626", icon: "fire" },
    { label: "⌀ Время реакции",    value: kpi.avg_response_min, unit: "мин", accent: "",
      delta: 8, goodIsDown: true, foot: `цель ⌀ 30 мин`, spark: kpi.spark.response, sparkColor: "#2563eb", icon: "clock" },
    { label: "⌀ Время решения",    value: kpi.avg_resolution_h, unit: "ч", accent: "",
      delta: -3, goodIsDown: true, foot: `цель ⌀ 8 ч`, spark: kpi.spark.resolution, sparkColor: "#2563eb", icon: "target" },
  ];
  return (
    <div className="kpis">
      {items.map((it) => (
        <div key={it.label} className={`kpi ${it.accent || ""}`}>
          <div className="label"><I n={it.icon} s={12}/>{it.label}</div>
          <div className="value-row">
            <span className="value">{it.value}</span>
            {it.unit && <span className="unit">{it.unit}</span>}
            <Delta value={it.delta} goodIsDown={it.goodIsDown}/>
          </div>
          <div className="foot">{it.foot}</div>
          {it.spark && <div className="spark"><Spark data={it.spark} color={it.sparkColor} w={56} h={20}/></div>}
        </div>
      ))}
    </div>
  );
}

// ==================== SLA TRENDS CHART ====================
function SlaTrendsChart({ trend, overlay, setOverlay }) {
  const w = 1180, h = 280, pad = { l: 48, r: 24, t: 24, b: 36 };
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const maxR = Math.max(...trend.map((d) => d.reaction), 1);
  const maxS = Math.max(...trend.map((d) => d.resolution), 1);
  const maxStack = Math.max(...trend.map((d) => d.reaction + d.resolution), 1);
  const maxV = overlay === "stack" ? maxStack : Math.max(maxR, maxS, 1);
  const stepX = iw / (trend.length - 1 || 1);
  const yScale = (v, max) => pad.t + ih - (v / max) * ih;

  const linePts = (key, max) => trend.map((d, i) => `${pad.l + i * stepX},${yScale(d[key], max)}`).join(" ");
  const areaPts = (key, max) => `${pad.l},${pad.t + ih} ${linePts(key, max)} ${pad.l + (trend.length-1)*stepX},${pad.t + ih}`;

  const ticks = 5;
  const xTickEvery = Math.max(1, Math.floor(trend.length / 8));

  // for "pct" mode: SLA % per day
  const pctData = trend.map((d) => ({
    ...d,
    r_pct: Math.max(70, +(((d.total - d.reaction) / Math.max(d.total, 1)) * 100).toFixed(1)),
    s_pct: Math.max(70, +(((d.total - d.resolution) / Math.max(d.total, 1)) * 100).toFixed(1)),
  }));
  const maxPct = 100, minPct = 80;
  const yPct = (v) => pad.t + ih - ((v - minPct) / (maxPct - minPct)) * ih;
  const linePtsPct = (key) => pctData.map((d, i) => `${pad.l + i * stepX},${yPct(d[key])}`).join(" ");

  return (
    <div className="panel">
      <div className="panel-h">
        <div>
          <div className="t">Тренд нарушений SLA</div>
          <div className="sub">Реакция и решение · {trend.length} дней</div>
        </div>
        <div className="right">
          <div className="seg">
            <button className={overlay === "split" ? "active" : ""} onClick={() => setOverlay("split")}>Раздельно</button>
            <button className={overlay === "stack" ? "active" : ""} onClick={() => setOverlay("stack")}>Стек</button>
            <button className={overlay === "pct" ? "active" : ""} onClick={() => setOverlay("pct")}>% SLA</button>
          </div>
        </div>
      </div>
      <div className="panel-b tight">
        <div className="chart-wrap">
          <div className="chart-legend">
            <span className="item"><span className="sw" style={{ background: "#d97706" }}/>Реакция</span>
            <span className="item"><span className="sw" style={{ background: "#7c3aed" }}/>Решение</span>
          </div>
          <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet" style={{ display: "block", maxHeight: 320 }}>
            {/* gridlines */}
            {Array.from({ length: ticks }).map((_, i) => {
              const yv = (overlay === "pct" ? minPct + (i/(ticks-1)) * (maxPct - minPct) : (maxV * (1 - i/(ticks-1))));
              const yy = overlay === "pct" ? yPct(yv) : yScale(yv, maxV);
              return (
                <g key={i}>
                  <line x1={pad.l} x2={w - pad.r} y1={yy} y2={yy} stroke="#f3f4f6"/>
                  <text x={pad.l - 8} y={yy + 3} textAnchor="end" fontSize="10.5" fill="#9ca3af" fontFamily="JetBrains Mono">{overlay === "pct" ? `${Math.round(yv)}%` : Math.round(yv)}</text>
                </g>
              );
            })}
            {/* x ticks */}
            {trend.map((d, i) => {
              if (i % xTickEvery !== 0 && i !== trend.length - 1) return null;
              const xx = pad.l + i * stepX;
              const lbl = `${String(d.date.getDate()).padStart(2,"0")}.${String(d.date.getMonth()+1).padStart(2,"0")}`;
              return (
                <text key={i} x={xx} y={h - pad.b + 18} textAnchor="middle" fontSize="10.5" fill="#9ca3af" fontFamily="JetBrains Mono">{lbl}</text>
              );
            })}
            {/* axis bottom */}
            <line x1={pad.l} x2={w - pad.r} y1={pad.t + ih} y2={pad.t + ih} stroke="#e5e7eb"/>

            {overlay === "pct" ? (
              <>
                <polyline points={linePtsPct("r_pct")} fill="none" stroke="#d97706" strokeWidth="2"/>
                <polyline points={linePtsPct("s_pct")} fill="none" stroke="#7c3aed" strokeWidth="2"/>
                {/* 95% target line */}
                <line x1={pad.l} x2={w - pad.r} y1={yPct(95)} y2={yPct(95)} stroke="#2563eb" strokeDasharray="4 4" strokeWidth="1"/>
                <text x={w - pad.r - 4} y={yPct(95) - 4} textAnchor="end" fontSize="10.5" fill="#2563eb" fontFamily="JetBrains Mono">цель 95%</text>
              </>
            ) : overlay === "stack" ? (
              <>
                <polygon points={`${pad.l},${pad.t + ih} ${trend.map((d, i) => `${pad.l + i*stepX},${yScale(d.reaction + d.resolution, maxStack)}`).join(" ")} ${pad.l + (trend.length-1)*stepX},${pad.t + ih}`} fill="#7c3aed" fillOpacity="0.14"/>
                <polygon points={areaPts("reaction", maxStack)} fill="#d97706" fillOpacity="0.18"/>
                <polyline points={trend.map((d, i) => `${pad.l + i*stepX},${yScale(d.reaction + d.resolution, maxStack)}`).join(" ")} fill="none" stroke="#7c3aed" strokeWidth="2"/>
                <polyline points={linePts("reaction", maxStack)} fill="none" stroke="#d97706" strokeWidth="2"/>
              </>
            ) : (
              <>
                <polygon points={areaPts("reaction", maxV)} fill="#d97706" fillOpacity="0.1"/>
                <polygon points={areaPts("resolution", maxV)} fill="#7c3aed" fillOpacity="0.08"/>
                <polyline points={linePts("reaction", maxV)} fill="none" stroke="#d97706" strokeWidth="2"/>
                <polyline points={linePts("resolution", maxV)} fill="none" stroke="#7c3aed" strokeWidth="2"/>
                {trend.map((d, i) => (
                  <React.Fragment key={i}>
                    {i === trend.length - 1 && <>
                      <circle cx={pad.l + i*stepX} cy={yScale(d.reaction, maxV)} r="3" fill="#d97706"/>
                      <circle cx={pad.l + i*stepX} cy={yScale(d.resolution, maxV)} r="3" fill="#7c3aed"/>
                    </>}
                  </React.Fragment>
                ))}
              </>
            )}
          </svg>
        </div>
      </div>
    </div>
  );
}

// ==================== BREACHES TABLE ====================
function BreachesTable({ tickets, filter, setFilter, onPick }) {
  return (
    <div className="panel">
      <div className="panel-h">
        <div>
          <div className="t">Пробития SLA</div>
          <div className="sub">{tickets.length} тикетов с превышением или близкими к нему</div>
        </div>
        <div className="right">
          <div className="seg">
            <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>Все</button>
            <button className={filter === "breached" ? "active" : ""} onClick={() => setFilter("breached")}>Нарушено</button>
            <button className={filter === "near" ? "active" : ""} onClick={() => setFilter("near")}>Близко</button>
            <button className={filter === "critical" ? "active" : ""} onClick={() => setFilter("critical")}>Критично</button>
          </div>
          <button className="btn sm"><I n="filter" s={12}/>Фильтры</button>
          <button className="btn sm"><I n="download" s={12}/></button>
        </div>
      </div>
      <div style={{ maxHeight: 480, overflow: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th style={{ width: 110 }}>Тикет</th>
              <th>Тема и очередь</th>
              <th>Владелец</th>
              <th style={{ minWidth: 160 }}>SLA реакц. / реш.</th>
              <th className="num">До пробития</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {tickets.slice(0, 12).map((t) => <BreachRow key={t.id} t={t} onClick={() => onPick(t)}/>)}
          </tbody>
        </table>
      </div>
      <div style={{ padding: "10px 20px", color: "var(--text-3)", fontSize: 12, textAlign: "center", borderTop: "1px solid var(--border)" }}>
        Показано {Math.min(12, tickets.length)} из {tickets.length}. <a style={{ color: "var(--brand)", cursor: "pointer" }}>Открыть все →</a>
      </div>
    </div>
  );
}

function BreachRow({ t, onClick }) {
  const remain = t.breach_eta_min;
  const remainLabel = remain < 0 ? `пробит +${execFmt.fmtMin(Math.abs(remain))}`
                     : remain < 10 ? execFmt.fmtMin(remain)
                     : execFmt.fmtMin(remain);
  const cls = remain < 0 ? "danger" : remain < 30 ? "warning" : "ok";
  return (
    <tr onClick={onClick}>
      <td><span className="tno">{t.ticket_number}</span></td>
      <td>
        <div className="t-title" style={{ maxWidth: 360, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.title}</div>
        <div className="t-meta"><span className="q-chip"><span className="dot"/>{t.queue}</span></div>
      </td>
      <td className="muted mono" style={{ fontSize: 12 }}>{t.owner}</td>
      <td>
        <div className="cell-progress">
          <div className="row">
            <span className="lab">Р</span>
            <div className="bar r"><i className={t.r_over ? "over" : ""} style={{ width: `${Math.min(t.r_used, 100)}%` }}/><div className="mark"/></div>
            <span className={`val ${t.r_over ? "danger" : ""}`}>{t.r_used}%</span>
          </div>
          <div className="row">
            <span className="lab">Реш</span>
            <div className="bar s"><i className={t.s_over ? "over" : ""} style={{ width: `${Math.min(t.s_used, 100)}%` }}/><div className="mark"/></div>
            <span className={`val ${t.s_over ? "danger" : ""}`}>{t.s_used}%</span>
          </div>
        </div>
      </td>
      <td className="num">
        <span className="mono" style={{ fontWeight: 600, color: cls === "danger" ? "var(--danger)" : cls === "warning" ? "var(--warning)" : "var(--success)" }}>
          {remainLabel}
        </span>
      </td>
      <td>
        {t.r_over && t.s_over ? <span className="badge danger"><span className="dot"/>Оба пробиты</span>
          : t.r_over ? <span className="badge warn"><span className="dot"/>Реакция пробита</span>
          : t.s_over ? <span className="badge warn"><span className="dot"/>Решение пробито</span>
          : t.tier === "crit" ? <span className="badge danger"><span className="dot"/>Критично</span>
          : t.tier === "high" ? <span className="badge warn"><span className="dot"/>Высокий риск</span>
          : <span className="badge info"><span className="dot"/>В зоне риска</span>}
      </td>
    </tr>
  );
}

// ==================== QUEUE HEALTH BARS ====================
function QueueHealth({ queues, onPick }) {
  const sorted = [...queues].sort((a, b) => a.health - b.health);
  return (
    <div className="panel">
      <div className="panel-h">
        <div>
          <div className="t">Здоровье очередей</div>
          <div className="sub">отсортировано по приоритету внимания</div>
        </div>
        <div className="right">
          <button className="btn sm"><I n="download" s={12}/></button>
        </div>
      </div>
      <div className="panel-b tight" style={{ maxHeight: 480, overflow: "auto" }}>
        <div className="qh-head">
          <span>Очередь</span>
          <span>SLA реакция / решение</span>
          <span style={{ textAlign: "right" }}>В риске</span>
          <span style={{ textAlign: "right" }}>Health</span>
        </div>
        {sorted.map((q) => {
          const tierCls = q.health >= 92 ? "ok" : q.health >= 85 ? "warn" : "crit";
          return (
            <div key={q.id} className="qh-row" onClick={() => onPick(q)}>
              <div className="qn">
                {q.name}
                <div className="meta">P{q.priority} · {q.calendar}</div>
              </div>
              <div className="stack">
                <div className="row">
                  <span className="lab">Реакц.</span>
                  <div className="bar r"><i style={{ width: `${100 - q.reaction.pct_ok}%` }}/></div>
                  <span className="val">{q.reaction.pct_ok}%</span>
                </div>
                <div className="row">
                  <span className="lab">Реш.</span>
                  <div className="bar s"><i style={{ width: `${100 - q.resolution.pct_ok}%` }}/></div>
                  <span className="val">{q.resolution.pct_ok}%</span>
                </div>
              </div>
              <div className="figure" style={{ color: q.at_risk > 30 ? "var(--danger)" : q.at_risk > 12 ? "var(--warning)" : "var(--text)" }}>
                {q.at_risk}
              </div>
              <div className={`health-pip ${tierCls}`}>{q.health}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ==================== SIMULATOR ====================
function SlaSimulator({ queues }) {
  const [queueId, setQueueId] = useState(queues[0].id);
  const [respMin, setRespMin] = useState(30);
  const [resHr, setResHr] = useState(8);
  const [calendar, setCalendar] = useState("9-18");
  const [elapsedMin, setElapsedMin] = useState(45);

  // Working hours impact
  const hoursMul = calendar === "9-18" ? 0.55 : 1;

  const q = queues.find((qq) => qq.id === queueId) || queues[0];

  const respWindow = respMin;
  const resWindow = resHr * 60;
  const effectiveElapsed = elapsedMin * hoursMul;
  const respUsedPct = Math.round((effectiveElapsed / respWindow) * 100);
  const resUsedPct  = Math.round((effectiveElapsed / resWindow) * 100);
  const willBreachResp = respUsedPct >= 100;
  const willBreachRes  = resUsedPct >= 100;

  const risk = Math.max(respUsedPct, resUsedPct);
  const riskLabel = risk >= 100 ? "пробит" : risk >= 90 ? "критич." : risk >= 70 ? "высокий" : risk >= 40 ? "средний" : "низкий";
  const riskCls = risk >= 100 ? "danger" : risk >= 90 ? "danger" : risk >= 70 ? "warn" : risk >= 40 ? "warn" : "ok";

  return (
    <div className="panel">
      <div className="panel-h">
        <div>
          <div className="t">SLA-симулятор</div>
          <div className="sub">прогноз пробития до создания правила</div>
        </div>
        <div className="right">
          <button className="btn sm ghost">Сбросить</button>
          <button className="btn primary sm"><I n="bolt" s={12}/>Сохранить как правило</button>
        </div>
      </div>
      <div className="sim-grid">
        <div className="sim-form">
          <div className="field">
            <label>Очередь</label>
            <select className="select" value={queueId} onChange={(e) => setQueueId(e.target.value)}>
              {queues.map((qq) => <option key={qq.id} value={qq.id}>{qq.name}</option>)}
            </select>
            <span className="hint">Применяется к шаблону имени очереди (поддерживает wildcard)</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div className="field">
              <label>Время реакции</label>
              <div className="row">
                <input type="number" className="input" style={{ flex: 1 }} value={respMin} onChange={(e) => setRespMin(+e.target.value)}/>
                <span className="dim">мин</span>
              </div>
            </div>
            <div className="field">
              <label>Время решения</label>
              <div className="row">
                <input type="number" className="input" style={{ flex: 1 }} value={resHr} onChange={(e) => setResHr(+e.target.value)}/>
                <span className="dim">ч</span>
              </div>
            </div>
          </div>
          <div className="field">
            <label>Календарь работы</label>
            <select className="select" value={calendar} onChange={(e) => setCalendar(e.target.value)}>
              <option value="9-18">RU 9:00–18:00 (рабочие часы)</option>
              <option value="24x7">24×7 (круглосуточно)</option>
            </select>
            <span className="hint">Влияет на эффективное использование SLA</span>
          </div>
          <div className="field">
            <label>Прошло с момента создания: {execFmt.fmtMin(elapsedMin)}</label>
            <input type="range" min="5" max="600" step="5" value={elapsedMin} onChange={(e) => setElapsedMin(+e.target.value)} style={{ width: "100%" }}/>
          </div>
        </div>

        <div className="sim-out">
          <div className="head">
            <h3>Прогноз для очереди <span className="mono" style={{ color: "var(--brand)" }}>{q.name}</span></h3>
            <span className={`badge ${riskCls === "danger" ? "danger" : riskCls === "warn" ? "warn" : "ok"}`}>
              <span className="dot"/>Риск: {riskLabel}
            </span>
          </div>

          {/* Reaction timeline */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#d97706" }}/>
              <span style={{ fontSize: 13, fontWeight: 600 }}>Реакция</span>
              <span className="dim" style={{ fontSize: 12, marginLeft: "auto" }}>цель {respMin} мин · использовано {respUsedPct}%</span>
            </div>
            <div className="timeline-axis">
              <div className="track">
                <i style={{
                  width: `${Math.min(respUsedPct, 100)}%`,
                  background: willBreachResp ? "var(--danger)" : "linear-gradient(90deg, #fbbf24, #d97706)",
                }}/>
              </div>
              <div className="marker now" style={{ left: `${Math.min(respUsedPct, 100)}%` }}><span className="lbl">сейчас</span></div>
              <div className="marker target" style={{ left: "100%" }}><span className="lbl">цель</span></div>
              {willBreachResp && <div className="marker breach" style={{ left: `${Math.min(respUsedPct, 100)}%` }}><span className="lbl below">пробит</span></div>}
              <div className="scale">
                <span>0</span><span>25%</span><span>50%</span><span>75%</span><span>цель</span>
              </div>
            </div>
          </div>

          {/* Resolution timeline */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#7c3aed" }}/>
              <span style={{ fontSize: 13, fontWeight: 600 }}>Решение</span>
              <span className="dim" style={{ fontSize: 12, marginLeft: "auto" }}>цель {resHr} ч · использовано {resUsedPct}%</span>
            </div>
            <div className="timeline-axis">
              <div className="track">
                <i style={{
                  width: `${Math.min(resUsedPct, 100)}%`,
                  background: willBreachRes ? "var(--danger)" : "linear-gradient(90deg, #a78bfa, #7c3aed)",
                }}/>
              </div>
              <div className="marker now" style={{ left: `${Math.min(resUsedPct, 100)}%` }}><span className="lbl">сейчас</span></div>
              <div className="marker target" style={{ left: "100%" }}><span className="lbl">цель</span></div>
              {willBreachRes && <div className="marker breach" style={{ left: `${Math.min(resUsedPct, 100)}%` }}><span className="lbl below">пробит</span></div>}
              <div className="scale">
                <span>0</span><span>25%</span><span>50%</span><span>75%</span><span>цель</span>
              </div>
            </div>
          </div>

          {/* Outcomes */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
            <div className="gauge">
              <div className="vmajor" style={{ color: riskCls === "danger" ? "var(--danger)" : riskCls === "warn" ? "var(--warning)" : "var(--success)" }}>{risk}%</div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>Risk score</div>
                <div className="vminor">от текущего использования</div>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: "var(--text-3)" }}>Реакция</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: willBreachResp ? "var(--danger)" : "var(--success)", marginTop: 4 }}>
                {willBreachResp ? "пробит" : "в срок"}
              </div>
              <div className="vminor" style={{ marginTop: 2 }}>
                {willBreachResp ? `просрочка ${execFmt.fmtMin(elapsedMin - respWindow / hoursMul)}` : `осталось ${execFmt.fmtMin(Math.round((respWindow / hoursMul) - elapsedMin))}`}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: "var(--text-3)" }}>Решение</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: willBreachRes ? "var(--danger)" : "var(--success)", marginTop: 4 }}>
                {willBreachRes ? "пробит" : "в срок"}
              </div>
              <div className="vminor" style={{ marginTop: 2 }}>
                {willBreachRes ? `просрочка ${execFmt.fmtMin(elapsedMin - resWindow / hoursMul)}` : `осталось ${execFmt.fmtMin(Math.round((resWindow / hoursMul) - elapsedMin))}`}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== DRAWER ====================
function ExecDrawer({ drawer, onClose }) {
  return (
    <>
      <div className={`scrim ${drawer.open ? "open" : ""}`} onClick={onClose}/>
      <aside className={`drawer ${drawer.open ? "open" : ""}`}>
        {drawer.kind === "ticket" && drawer.payload && <TicketDrawerBody t={drawer.payload} onClose={onClose}/>}
        {drawer.kind === "queue" && drawer.payload && <QueueDrawerBody q={drawer.payload} onClose={onClose}/>}
      </aside>
    </>
  );
}

function TicketDrawerBody({ t, onClose }) {
  return (
    <>
      <div className="drawer-h">
        <div>
          <div className="row" style={{ gap: 8, marginBottom: 4 }}>
            <span className="tno">{t.ticket_number}</span>
            {t.r_over && t.s_over ? <span className="badge danger"><span className="dot"/>Оба пробиты</span>
              : t.r_over ? <span className="badge warn"><span className="dot"/>Реакция пробита</span>
              : t.s_over ? <span className="badge warn"><span className="dot"/>Решение пробито</span>
              : <span className="badge info"><span className="dot"/>В зоне риска</span>}
          </div>
          <div style={{ fontSize: 15, fontWeight: 500 }}>{t.title}</div>
        </div>
        <button className="close" onClick={onClose}><I n="close" s={14}/></button>
      </div>
      <div className="drawer-b">
        <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", rowGap: 8, columnGap: 12, fontSize: 13, marginBottom: 18 }}>
          <div className="dim">Очередь</div><div><span className="q-chip"><span className="dot"/>{t.queue}</span></div>
          <div className="dim">Владелец</div><div className="mono">{t.owner}</div>
          <div className="dim">Приоритет</div><div><span className={`tag-priority ${t.priority === "Высокий" ? "p20" : t.priority === "Средний" ? "p10" : "p5"}`}>{t.priority}</span></div>
          <div className="dim">Создан</div><div className="mono">{t.created_at}</div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 8 }}>SLA · Реакция</div>
          <div style={{ position: "relative", height: 14, background: "var(--surface-3)", borderRadius: 4, overflow: "hidden", marginBottom: 6 }}>
            <div style={{ width: `${Math.min(t.r_used, 100)}%`, height: "100%", background: t.r_over ? "var(--danger)" : "var(--warning)", borderRadius: 4 }}/>
            <div style={{ position: "absolute", top: -2, bottom: -2, left: "100%", width: 1, background: "var(--text-4)" }}/>
          </div>
          <div className="row" style={{ justifyContent: "space-between", fontSize: 12 }}>
            <span className="dim">Использовано <b className="mono" style={{ color: t.r_over ? "var(--danger)" : "var(--text)" }}>{t.r_used}%</b></span>
            <span className="dim mono">цель {execFmt.fmtSec(t.target_response)}</span>
          </div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 8 }}>SLA · Решение</div>
          <div style={{ position: "relative", height: 14, background: "var(--surface-3)", borderRadius: 4, overflow: "hidden", marginBottom: 6 }}>
            <div style={{ width: `${Math.min(t.s_used, 100)}%`, height: "100%", background: t.s_over ? "var(--danger)" : "#7c3aed", borderRadius: 4 }}/>
            <div style={{ position: "absolute", top: -2, bottom: -2, left: "100%", width: 1, background: "var(--text-4)" }}/>
          </div>
          <div className="row" style={{ justifyContent: "space-between", fontSize: 12 }}>
            <span className="dim">Использовано <b className="mono" style={{ color: t.s_over ? "var(--danger)" : "var(--text)" }}>{t.s_used}%</b></span>
            <span className="dim mono">цель {execFmt.fmtSec(t.target_resolution)}</span>
          </div>
        </div>

        <div className="divider"/>

        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn primary">Открыть в OTRS</button>
          <button className="btn">Переназначить</button>
          <button className="btn">Эскалация</button>
        </div>
      </div>
    </>
  );
}

function QueueDrawerBody({ q, onClose }) {
  return (
    <>
      <div className="drawer-h">
        <div>
          <div className="mono" style={{ fontSize: 15, fontWeight: 600 }}>{q.name}</div>
          <div className="dim" style={{ fontSize: 12, marginTop: 2 }}>P{q.priority} · {q.calendar} · {q.agents_on} агент.</div>
        </div>
        <button className="close" onClick={onClose}><I n="close" s={14}/></button>
      </div>
      <div className="drawer-b">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 20 }}>
          <div style={{ background: "var(--surface-2)", border: "1px solid var(--border)", padding: 12, borderRadius: 8 }}>
            <div className="dim" style={{ fontSize: 11.5 }}>Health</div>
            <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: q.health >= 92 ? "var(--success)" : q.health >= 85 ? "var(--warning)" : "var(--danger)" }}>{q.health}</div>
          </div>
          <div style={{ background: "var(--surface-2)", border: "1px solid var(--border)", padding: 12, borderRadius: 8 }}>
            <div className="dim" style={{ fontSize: 11.5 }}>Тикетов</div>
            <div className="mono" style={{ fontSize: 22, fontWeight: 700 }}>{q.tickets}</div>
          </div>
          <div style={{ background: "var(--surface-2)", border: "1px solid var(--border)", padding: 12, borderRadius: 8 }}>
            <div className="dim" style={{ fontSize: 11.5 }}>В риске</div>
            <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--warning)" }}>{q.at_risk}</div>
          </div>
        </div>

        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 10 }}>SLA · Реакция</div>
        <DrawerSlaRow color="#d97706" pct={q.reaction.pct_ok} inTime={q.reaction.in_time} breached={q.reaction.breached} avg={execFmt.fmtSec(q.reaction.avg_sec)} target={execFmt.fmtSec(q.target_response)}/>

        <div style={{ height: 18 }}/>

        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 10 }}>SLA · Решение</div>
        <DrawerSlaRow color="#7c3aed" pct={q.resolution.pct_ok} inTime={q.resolution.in_time} breached={q.resolution.breached} avg={execFmt.fmtSec(q.resolution.avg_sec)} target={execFmt.fmtSec(q.target_resolution)}/>

        <div className="divider"/>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn primary">Открыть все тикеты</button>
          <button className="btn">Правило SLA</button>
        </div>
      </div>
    </>
  );
}

function DrawerSlaRow({ color, pct, inTime, breached, avg, target }) {
  return (
    <div>
      <div style={{ position: "relative", height: 10, background: "var(--surface-3)", borderRadius: 5, overflow: "hidden", marginBottom: 8 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 5 }}/>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, fontSize: 12 }}>
        <div><div className="dim">В срок</div><div className="mono" style={{ fontWeight: 600, color: "var(--success)", marginTop: 2 }}>{execFmt.fmtNum(inTime)} <span style={{ color: "var(--text-3)", fontWeight: 400 }}>({pct}%)</span></div></div>
        <div><div className="dim">Нарушено</div><div className="mono" style={{ fontWeight: 600, color: "var(--danger)", marginTop: 2 }}>{execFmt.fmtNum(breached)}</div></div>
        <div><div className="dim">⌀ время</div><div className="mono" style={{ fontWeight: 600, marginTop: 2 }}>{avg}</div></div>
        <div><div className="dim">Цель</div><div className="mono" style={{ fontWeight: 600, marginTop: 2 }}>{target}</div></div>
      </div>
    </div>
  );
}

// custom delta CSS (defined here so it doesn't pollute global stylesheet)
const dx = document.createElement("style");
dx.textContent = `
.delta { display: inline-flex; align-items: center; gap: 2px; font-size: 11.5px; font-weight: 500; padding: 1px 6px; border-radius: 4px; line-height: 1; height: 18px; }
.delta.good { color: var(--success); background: var(--success-bg); }
.delta.bad  { color: var(--danger);  background: var(--danger-bg); }
.delta.flat { color: var(--text-3);  background: var(--surface-3); }
`;
document.head.appendChild(dx);

ReactDOM.createRoot(document.getElementById("root")).render(<ExecApp/>);
