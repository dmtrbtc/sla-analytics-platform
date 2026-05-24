// SLA Portal — analytical portal main app
const { useState, useEffect, useMemo, useRef } = React;

// ---------- formatters ----------
const fmtMin = (m) => {
  if (m == null) return "—";
  const abs = Math.abs(m);
  let s;
  if (abs === 0) s = "0 мин";
  else if (abs < 60) s = `${Math.round(abs)} мин`;
  else if (abs < 24 * 60) {
    const h = Math.floor(abs / 60), mn = Math.round(abs % 60);
    s = mn === 0 ? `${h} ч` : `${h} ч ${mn} мин`;
  } else {
    const d = Math.floor(abs / (24 * 60)), h = Math.round((abs % (24 * 60)) / 60);
    s = h === 0 ? `${d} д` : `${d} д ${h} ч`;
  }
  return m < 0 ? `−${s}` : s;
};
const fmtSec = (s) => {
  if (!s) return "0 сек";
  if (s < 60) return `${Math.round(s)} сек`;
  return fmtMin(Math.round(s / 60));
};

// ---------- icons ----------
function Icon({ n, s = 16 }) {
  const map = {
    dashboard: "M3 3h7v9H3V3zm0 11h7v7H3v-7zm9-11h9v7h-9V3zm0 9h9v9h-9v-9z",
    queues:    "M3 6h4v4H3V6zm6 0h12v2H9V6zm0 4h9v2H9v-2zM3 13h4v4H3v-4zm6 1h12v2H9v-2zm0 4h9v2H9v-2z",
    tickets:   "M22 10V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v4a2 2 0 0 1 0 4v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4a2 2 0 0 1 0-4z",
    risk:      "M12 2 1 21h22L12 2zm0 14h-2v-2h2v2zm0-4h-2V8h2v4z",
    chart:     "M3 21h18v-2H3v2zm3-4h2v-7H6v7zm5 0h2V3h-2v14zm5 0h2v-4h-2v4z",
    reports:   "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z",
    settings:  "M19.4 13c0-.3.1-.7.1-1s0-.7-.1-1l2.1-1.6L19.5 6l-2.4 1a7 7 0 0 0-1.7-1L14.6 3h-4l-.3 2.5a7 7 0 0 0-1.7 1L6.2 6.5 4.2 9.9l2.1 1.6c0 .3-.1.7-.1 1s0 .7.1 1L4.2 15.1l2 3.4 2.4-1a7 7 0 0 0 1.7 1l.3 2.5h4l.3-2.5a7 7 0 0 0 1.7-1l2.4 1 2-3.4-2.1-1.6zM12 15a3 3 0 1 1 0-6 3 3 0 0 1 0 6z",
    team:      "M16 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3zM8 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-2.7 0-8 1.3-8 4v2h10v-2c0-1 .3-1.8.7-2.5A11 11 0 0 0 8 13zm8 0c-.4 0-.8 0-1.3.1A5.4 5.4 0 0 1 16 17v2h8v-2c0-2.7-5.3-4-8-4z",
    incident:  "M12 2 1 21h22L12 2zm1 14h-2v-2h2zm0-4h-2V8h2z",
    download:  "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
    plus:      "M19 11h-6V5h-2v6H5v2h6v6h2v-6h6z",
    refresh:   "M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.74 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
    close:     "M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    fire:      "M12 23a8 8 0 0 0 8-8c0-2.5-1-4.83-2.39-6.5C16.5 11 13 12 13 12s2-7-5-11c1 5-5 8-5 14a8 8 0 0 0 9 8z",
    bell:      "M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6V11c0-3.07-1.63-5.64-4.5-6.32V4a1.5 1.5 0 0 0-3 0v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
    clock:     "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm.5-13H11v6l5.2 3.2.8-1.3-4.5-2.7z",
    target:    "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm0-13a5 5 0 1 0 5 5 5 5 0 0 0-5-5zm0 8a3 3 0 1 1 3-3 3 3 0 0 1-3 3z",
    heat:      "M5 21h14v-2H5v2zm0-4h6v-2H5v2zm8 0h6v-2h-6v2zM5 13h6v-2H5v2zm8 0h6v-2h-6v2zM5 9h14V3H5v6z",
    up:        "M7 14l5-5 5 5z",
    down:      "M7 10l5 5 5-5z",
    open:      "M14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z",
  };
  const p = map[n];
  if (!p) return null;
  return <svg width={s} height={s} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d={p}/></svg>;
}
window.PIcon = Icon;

// ============================================================
// MAIN APP
// ============================================================
function App() {
  const D = window.OPSDATA;
  const K = D.KPI;

  const [t, setTweak] = useTweaks({
    chart_mode: "stack",
    tab_default: "queues",
  });

  // ----- Global filters -----
  const [period, setPeriod] = useState(30);
  const [scope, setScope] = useState("all"); // all | support | infra | biz
  const [calendar, setCalendar] = useState("all"); // all | 24x7 | bh
  const [search, setSearch] = useState("");

  // ----- Tabs -----
  const [tab, setTab] = useState(t.tab_default || "queues");

  // ----- Sort -----
  const [sort, setSort] = useState({ k: "health", d: "asc" });

  // ----- Selection / drawer -----
  const [drawer, setDrawer] = useState({ open: false, kind: null, payload: null });

  useEffect(() => {
    const onEsc = (e) => { if (e.key === "Escape") setDrawer((d) => ({ ...d, open: false })); };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, []);

  // ----- Filter queues by scope, calendar, search -----
  const filteredQueues = useMemo(() => {
    let arr = D.QUEUES;
    if (scope === "support") arr = arr.filter((q) => q.name.startsWith("Support"));
    else if (scope === "infra") arr = arr.filter((q) => q.name.startsWith("Infrastructure"));
    else if (scope === "biz") arr = arr.filter((q) => !q.name.startsWith("Support") && !q.name.startsWith("Infrastructure"));
    if (calendar === "24x7") arr = arr.filter((q) => q.calendar === "24×7");
    else if (calendar === "bh") arr = arr.filter((q) => q.calendar !== "24×7");
    if (search) arr = arr.filter((q) => q.name.toLowerCase().includes(search.toLowerCase()));
    return arr;
  }, [scope, calendar, search]);

  const filteredIds = useMemo(() => new Set(filteredQueues.map((q) => q.id)), [filteredQueues]);

  // ----- Sort queues -----
  const sortedQueues = useMemo(() => {
    const dir = sort.d === "asc" ? 1 : -1;
    const get = (q) => {
      switch (sort.k) {
        case "name":       return q.name;
        case "priority":   return q.priority;
        case "tickets":    return q.tickets;
        case "reaction":   return q.reaction.pct_ok;
        case "resolution": return q.resolution.pct_ok;
        case "rbreach":    return q.reaction.breached;
        case "sbreach":    return q.resolution.breached;
        case "at_risk":    return q.at_risk;
        case "wait":       return q.avg_wait_min;
        case "health":     return q.health;
        default:           return 0;
      }
    };
    return [...filteredQueues].sort((a, b) => {
      const va = get(a), vb = get(b);
      if (typeof va === "string") return va.localeCompare(vb) * dir;
      return (va - vb) * dir;
    });
  }, [filteredQueues, sort]);

  // ----- Aggregated daily data by current scope/period -----
  const dailyTotal = useMemo(() => {
    const days = period;
    const start = D.DAILY_TOTAL.length - days;
    const slice = D.DAILY_TOTAL.slice(start);
    // If scope filtered, recompute from per-queue daily
    if (scope === "all" && calendar === "all" && !search) return slice;
    const filtered = D.DAILY.filter((q) => filteredIds.has(q.queue_id));
    const arr = slice.map((d, i) => {
      let total = 0, reaction = 0, resolution = 0;
      for (const q of filtered) {
        const dd = q.series[start + i];
        total += dd.total; reaction += dd.reaction; resolution += dd.resolution;
      }
      return { date: d.date, total, reaction, resolution };
    });
    return arr;
  }, [period, scope, calendar, search, filteredIds]);

  // ----- Top queues by breaches (for horizontal bar chart) -----
  const topByBreaches = useMemo(() => {
    return [...filteredQueues]
      .map((q) => ({
        id: q.id, name: q.name,
        reaction: q.reaction.breached,
        resolution: q.resolution.breached,
        onClick: () => setDrawer({ open: true, kind: "queue", payload: q }),
      }))
      .sort((a, b) => (b.reaction + b.resolution) - (a.reaction + a.resolution))
      .slice(0, 8);
  }, [filteredQueues]);

  // ----- Heatmap rows -----
  const heatmapRows = useMemo(() => D.HEATMAP.filter((r) => filteredIds.has(r.queue_id)), [filteredIds]);

  // ----- At-risk tickets in scope -----
  const atRiskTickets = useMemo(() => D.AT_RISK.filter((tk) => filteredIds.has(tk.queue_id)), [filteredIds]);

  // ----- Scoped KPIs -----
  const scopedKpi = useMemo(() => {
    const total = filteredQueues.reduce((s, q) => s + q.tickets, 0) || 1;
    const rB = filteredQueues.reduce((s, q) => s + q.reaction.breached, 0);
    const sB = filteredQueues.reduce((s, q) => s + q.resolution.breached, 0);
    const atRisk = filteredQueues.reduce((s, q) => s + q.at_risk, 0);
    const rPct = +(((total - rB) / total) * 100).toFixed(1);
    const sPct = +(((total - sB) / total) * 100).toFixed(1);
    const avgWait = Math.round(filteredQueues.reduce((s, q) => s + q.avg_wait_min, 0) / Math.max(filteredQueues.length, 1));
    return { rPct, sPct, rB, sB, atRisk, total, avgWait, qCount: filteredQueues.length };
  }, [filteredQueues]);

  return (
    <div className="app">
      {/* SIDEBAR */}
      <aside className="side">
        <div className="brand">
          <div className="mark">SP</div>
          <div><div className="nm">SLA Portal</div><div className="sub">enterprise</div></div>
        </div>
        <div className="group">
          <div className="group-h">Аналитика</div>
          <div className="nav-item active"><span className="ic"><Icon n="dashboard" s={15}/></span><span>Обзор</span></div>
          <div className="nav-item"><span className="ic"><Icon n="queues" s={15}/></span><span>Очереди</span><span className="count">{D.QUEUES.length}</span></div>
          <div className="nav-item"><span className="ic"><Icon n="chart" s={15}/></span><span>Тренды</span></div>
          <div className="nav-item"><span className="ic"><Icon n="heat" s={15}/></span><span>Тепловые карты</span></div>
        </div>
        <div className="group">
          <div className="group-h">Работа</div>
          <div className="nav-item flag"><span className="ic"><Icon n="risk" s={15}/></span><span>Пробития</span><span className="count">{K.active_breaches}</span></div>
          <div className="nav-item"><span className="ic"><Icon n="tickets" s={15}/></span><span>Тикеты</span></div>
          <div className="nav-item flag"><span className="ic"><Icon n="incident" s={15}/></span><span>Инциденты</span><span className="count">{D.INCIDENTS.length}</span></div>
          <div className="nav-item"><span className="ic"><Icon n="team" s={15}/></span><span>Команда</span></div>
        </div>
        <div className="group">
          <div className="group-h">Управление</div>
          <div className="nav-item"><span className="ic"><Icon n="reports" s={15}/></span><span>Отчёты</span></div>
          <div className="nav-item"><span className="ic"><Icon n="settings" s={15}/></span><span>Настройки SLA</span></div>
        </div>
        <div className="spacer"/>
        <div className="acct">
          <div className="ava">АИ</div>
          <div><div className="nm">Анна Иванова</div><div className="role">SLA-менеджер</div></div>
        </div>
      </aside>

      {/* MAIN */}
      <main className="main">
        {/* TOPBAR */}
        <div className="topbar">
          <div className="row1">
            <div className="ttl-block">
              <div className="crumb">Аналитика · SLA</div>
              <h1>Обзор SLA<span className="live-pill">live · обновлено только что</span></h1>
            </div>
            <div className="spacer"/>
            <div className="actions">
              <input className="search" placeholder="Поиск очереди или тикета..." value={search} onChange={(e) => setSearch(e.target.value)}/>
              <button className="btn"><Icon n="download" s={13}/>Выгрузка</button>
              <button className="btn primary"><Icon n="plus" s={13}/>Создать правило</button>
            </div>
          </div>
          <div className="row2">
            <span className="lab">Период</span>
            <select className="select sm" value={period} onChange={(e) => setPeriod(+e.target.value)}>
              <option value={7}>Последние 7 дней</option>
              <option value={14}>14 дней</option>
              <option value={30}>30 дней</option>
              <option value={60}>60 дней</option>
              <option value={90}>90 дней</option>
            </select>
            <div className="sep"/>
            <span className="lab">Сегмент</span>
            <div className="chips">
              <button className={`chip ${scope === "all" ? "active" : ""}`} onClick={() => setScope("all")}>Все<span className="count">{D.QUEUES.length}</span></button>
              <button className={`chip ${scope === "support" ? "active" : ""}`} onClick={() => setScope("support")}>Support<span className="count">{D.SCOPE_TOTALS.sup.queues}</span></button>
              <button className={`chip ${scope === "infra" ? "active" : ""}`} onClick={() => setScope("infra")}>Infrastructure<span className="count">{D.SCOPE_TOTALS.inf.queues}</span></button>
              <button className={`chip ${scope === "biz" ? "active" : ""}`} onClick={() => setScope("biz")}>Бизнес<span className="count">{D.SCOPE_TOTALS.biz.queues}</span></button>
            </div>
            <div className="sep"/>
            <span className="lab">Календарь</span>
            <select className="select sm" value={calendar} onChange={(e) => setCalendar(e.target.value)}>
              <option value="all">Все</option>
              <option value="24x7">24×7</option>
              <option value="bh">Рабочие часы</option>
            </select>
            <div className="spacer" style={{ flex: 1 }}/>
            <button className="btn sm ghost"><Icon n="refresh" s={12}/>Сбросить</button>
          </div>
        </div>

        {/* CANVAS */}
        <div className="canvas">
          <div className="wrap">

            {/* ====== KPI ROW ====== */}
            <div className="kpis">
              <Kpi
                lab="SLA по реакции"
                val={`${scopedKpi.rPct}%`}
                ic={<Icon n="clock" s={15}/>}
                accent="react"
                foot={`${fmtNum(scopedKpi.rB)} нарушений / ${fmtNum(scopedKpi.total)} тикетов`}
                delta={0.4}
              />
              <Kpi
                lab="SLA по решению"
                val={`${scopedKpi.sPct}%`}
                ic={<Icon n="target" s={15}/>}
                accent="resolve"
                foot={`${fmtNum(scopedKpi.sB)} нарушений`}
                delta={-1.2}
              />
              <Kpi
                lab="Тикеты в зоне риска"
                val={fmtNum(scopedKpi.atRisk)}
                ic={<Icon n="risk" s={15}/>}
                accent={scopedKpi.atRisk > 50 ? "crit" : ""}
                foot="близко к пробитию SLA"
                delta={6}
                deltaBad
              />
              <Kpi
                lab="Среднее время ожидания"
                val={fmtMin(scopedKpi.avgWait)}
                ic={<Icon n="clock" s={15}/>}
                accent="brand"
                foot={`${scopedKpi.qCount} очередей в выборке`}
                delta={-3}
              />
            </div>

            {/* ====== MAIN CHART + TOP QUEUES ====== */}
            <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.65fr) minmax(0, 1fr)", gap: 16 }}>
              <div className="card">
                <div className="card-h">
                  <div>
                    <div className="t">Тренд нарушений SLA</div>
                    <div className="sub">{period} дней · реакция и решение</div>
                  </div>
                  <div className="right">
                    <div style={{ display: "inline-flex", background: "var(--surface-3)", borderRadius: 7, padding: 2 }}>
                      <button className="btn ghost sm" style={t.chart_mode === "stack" ? { background: "var(--surface)", color: "var(--ink)", fontWeight: 600 } : {}} onClick={() => setTweak("chart_mode", "stack")}>Стек</button>
                      <button className="btn ghost sm" style={t.chart_mode === "split" ? { background: "var(--surface)", color: "var(--ink)", fontWeight: 600 } : {}} onClick={() => setTweak("chart_mode", "split")}>Раздельно</button>
                    </div>
                    <div className="legend" style={{ marginLeft: 12 }}>
                      <span className="item"><span className="sw" style={{ background: "var(--reaction)" }}/>Реакция</span>
                      <span className="item"><span className="sw" style={{ background: "var(--resolution)" }}/>Решение</span>
                    </div>
                  </div>
                </div>
                <div className="card-b">
                  <StackedAreaChart data={dailyTotal} height={280} mode={t.chart_mode}/>
                </div>
              </div>

              <div className="card">
                <div className="card-h">
                  <div>
                    <div className="t">Топ очередей по нарушениям</div>
                    <div className="sub">за выбранный период</div>
                  </div>
                </div>
                <div className="card-b">
                  <HorizontalBarsChart data={topByBreaches}/>
                </div>
                <div style={{ padding: "10px 20px 16px", borderTop: "1px solid var(--line-2)" }}>
                  <div className="legend">
                    <span className="item"><span className="sw" style={{ background: "var(--reaction)" }}/>Реакция</span>
                    <span className="item"><span className="sw" style={{ background: "var(--resolution)" }}/>Решение</span>
                  </div>
                </div>
              </div>
            </div>

            {/* ====== TABS / ANALYSIS ====== */}
            <div className="card">
              <div className="tabs">
                <button className={tab === "queues" ? "active" : ""} onClick={() => setTab("queues")}>
                  <Icon n="queues" s={14}/>Очереди<span className="count">{filteredQueues.length}</span>
                </button>
                <button className={tab === "tickets" ? "active" : ""} onClick={() => setTab("tickets")}>
                  <Icon n="risk" s={14}/>Тикеты в риске<span className="count">{atRiskTickets.length}</span>
                </button>
                <button className={tab === "heat" ? "active" : ""} onClick={() => setTab("heat")}>
                  <Icon n="heat" s={14}/>Тепловая карта
                </button>
                <button className={tab === "team" ? "active" : ""} onClick={() => setTab("team")}>
                  <Icon n="team" s={14}/>Команда<span className="count">{D.AGENTS.length}</span>
                </button>

                <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, paddingRight: 8 }}>
                  {tab === "queues" && (
                    <select className="select sm" value={`${sort.k}-${sort.d}`} onChange={(e) => { const [k, d] = e.target.value.split("-"); setSort({ k, d }); }}>
                      <option value="health-asc">Сначала с худшим health</option>
                      <option value="rbreach-desc">По нарушениям реакции ↓</option>
                      <option value="sbreach-desc">По нарушениям решения ↓</option>
                      <option value="at_risk-desc">По тикетам в риске ↓</option>
                      <option value="tickets-desc">По объёму ↓</option>
                      <option value="name-asc">По имени A→Я</option>
                    </select>
                  )}
                </div>
              </div>

              {tab === "queues" && (
                <QueueTable
                  queues={sortedQueues}
                  sort={sort}
                  setSort={setSort}
                  onPick={(q) => setDrawer({ open: true, kind: "queue", payload: q })}
                />
              )}
              {tab === "tickets" && (
                <TicketTable tickets={atRiskTickets} onPick={(tk) => setDrawer({ open: true, kind: "ticket", payload: tk })}/>
              )}
              {tab === "heat" && (
                <div style={{ padding: 20 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                    <div>
                      <div style={{ fontSize: 13, color: "var(--ink-3)" }}>Интенсивность нарушений · очередь × час суток</div>
                    </div>
                    <div className="legend">
                      <span className="item">
                        низко
                        <span className="sw dot" style={{ background: "#fff7ed" }}/>
                        <span className="sw dot" style={{ background: "#fed7aa" }}/>
                        <span className="sw dot" style={{ background: "#fb923c" }}/>
                        <span className="sw dot" style={{ background: "#ea580c" }}/>
                        высоко
                      </span>
                    </div>
                  </div>
                  <Heatmap rows={heatmapRows} onCellClick={(r, h) => {
                    const q = D.QUEUES.find((qq) => qq.id === r.queue_id);
                    if (q) setDrawer({ open: true, kind: "queue", payload: q });
                  }}/>
                  <div style={{ marginTop: 16, fontSize: 12, color: "var(--ink-3)" }}>
                    Наведите курсор для деталей · клик по ячейке открывает очередь.
                  </div>
                </div>
              )}
              {tab === "team" && <TeamTable agents={D.AGENTS}/>}
            </div>

            <div style={{ fontSize: 12, color: "var(--ink-4)", textAlign: "center", padding: 12 }}>
              SLA Portal · период {period} дней · сегмент: {scope === "all" ? "все" : scope === "support" ? "Support" : scope === "infra" ? "Infrastructure" : "Бизнес"} · обновлено только что
            </div>
          </div>
        </div>
      </main>

      {/* DRAWER */}
      <PortalDrawer drawer={drawer} onClose={() => setDrawer((d) => ({ ...d, open: false }))}/>

      {/* Tweaks */}
      <TweaksPanel title="SLA Portal · настройки">
        <TweakSection label="Графики">
          <TweakRadio label="Режим тренда" value={t.chart_mode} options={[
            { value: "stack", label: "Стек" },
            { value: "split", label: "Раздельно" },
          ]} onChange={(v) => setTweak("chart_mode", v)}/>
        </TweakSection>
        <TweakSection label="Стартовая вкладка">
          <TweakSelect label="По умолчанию" value={t.tab_default} options={[
            { value: "queues", label: "Очереди" },
            { value: "tickets", label: "Тикеты" },
            { value: "heat", label: "Тепловая карта" },
            { value: "team", label: "Команда" },
          ]} onChange={(v) => setTweak("tab_default", v)}/>
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

// ============================================================
// KPI tile
// ============================================================
function Kpi({ lab, val, ic, accent, foot, delta, deltaBad }) {
  const cls = delta == null ? "flat" : (deltaBad ? (delta > 0 ? "bad" : "good") : (delta > 0 ? "good" : "bad"));
  return (
    <div className={`kpi ${accent || ""}`}>
      <div className="head">
        <span className="lab">{lab}</span>
        {ic && <span className="ic">{ic}</span>}
      </div>
      <div className="val">{val}</div>
      <div className="foot">
        {delta != null && (
          <span className={`delta ${cls}`}>
            <PIcon n={delta > 0 ? "up" : delta < 0 ? "down" : ""} s={10}/>
            {Math.abs(delta)}%
          </span>
        )}
        <span>{foot}</span>
      </div>
    </div>
  );
}

// ============================================================
// Queue table
// ============================================================
function QueueTable({ queues, sort, setSort, onPick }) {
  const SortHead = ({ k, num, children }) => {
    const active = sort.k === k;
    return (
      <th className={`sortable ${num ? "num" : ""} ${active ? "sorted" : ""}`}
        onClick={() => setSort((s) => ({ k, d: s.k === k && s.d === "asc" ? "desc" : "asc" }))}>
        {children}
        <span className="arr">{active ? (sort.d === "desc" ? "↓" : "↑") : "↕"}</span>
      </th>
    );
  };
  return (
    <div className="table-wrap" style={{ maxHeight: 560 }}>
      <table className="qtbl">
        <thead>
          <tr>
            <SortHead k="name">Очередь</SortHead>
            <SortHead k="priority">Приоритет</SortHead>
            <SortHead k="tickets" num>Тикетов</SortHead>
            <SortHead k="reaction" num>SLA реакц.</SortHead>
            <SortHead k="resolution" num>SLA реш.</SortHead>
            <SortHead k="rbreach" num>Наруш. реакц.</SortHead>
            <SortHead k="sbreach" num>Наруш. реш.</SortHead>
            <SortHead k="at_risk" num>В риске</SortHead>
            <SortHead k="wait" num>⌀ Ожидание</SortHead>
            <th>Тренд</th>
            <SortHead k="health" num>Health</SortHead>
          </tr>
        </thead>
        <tbody>
          {queues.map((q) => {
            const rCls = q.reaction.pct_ok >= 92 ? "" : q.reaction.pct_ok >= 85 ? "warn" : "crit";
            const sCls = q.resolution.pct_ok >= 92 ? "" : q.resolution.pct_ok >= 85 ? "warn" : "crit";
            const hCls = q.health >= 92 ? "ok" : q.health >= 85 ? "warn" : q.health >= 75 ? "high" : "crit";
            return (
              <tr key={q.id} onClick={() => onPick(q)}>
                <td>
                  <div className="q-name">{q.name}</div>
                  <div className="q-meta">{q.calendar} · {q.agents_on} агент.</div>
                </td>
                <td>
                  <span className={`prio-tag ${q.priority >= 20 ? "p20" : q.priority >= 10 ? "p10" : "p5"}`}>P{q.priority}</span>
                </td>
                <td className="num"><span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{fmtNum(q.tickets)}</span></td>
                <td className="num">
                  <div className={`bar-cell r ${rCls}`}>
                    <span className={`v ${rCls}`}>{q.reaction.pct_ok}%</span>
                    <div className="bar"><i style={{ width: `${q.reaction.pct_ok}%` }}/></div>
                  </div>
                </td>
                <td className="num">
                  <div className={`bar-cell s ${sCls}`}>
                    <span className={`v ${sCls}`}>{q.resolution.pct_ok}%</span>
                    <div className="bar"><i style={{ width: `${q.resolution.pct_ok}%` }}/></div>
                  </div>
                </td>
                <td className="num"><span className="mono" style={{ fontSize: 13, fontWeight: 600, color: q.reaction.breached > 30 ? "var(--crit)" : q.reaction.breached > 10 ? "var(--warn)" : "var(--ink)" }}>{q.reaction.breached}</span></td>
                <td className="num"><span className="mono" style={{ fontSize: 13, fontWeight: 600, color: q.resolution.breached > 30 ? "var(--crit)" : q.resolution.breached > 10 ? "var(--warn)" : "var(--ink)" }}>{q.resolution.breached}</span></td>
                <td className="num"><span className="mono" style={{ fontSize: 13, fontWeight: 600, color: q.at_risk > 30 ? "var(--crit)" : q.at_risk > 12 ? "var(--warn)" : "var(--ink)" }}>{q.at_risk}</span></td>
                <td className="num"><span className="mono" style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{fmtMin(q.avg_wait_min)}</span></td>
                <td>
                  <div className="row-spark">
                    <Spark data={q.reaction.trend} color="var(--reaction)" w={56} h={20}/>
                    <Spark data={q.resolution.trend} color="var(--resolution)" w={56} h={20}/>
                  </div>
                </td>
                <td className="num"><span className={`hp ${hCls}`}>{q.health}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {queues.length === 0 && (
        <div className="empty">
          <div className="ttl">Очереди не найдены</div>
          <div className="sub">Уточните фильтры или поисковый запрос.</div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Ticket table (at-risk)
// ============================================================
function TicketTable({ tickets, onPick }) {
  return (
    <div className="table-wrap" style={{ maxHeight: 560 }}>
      <table className="qtbl">
        <thead>
          <tr>
            <th>Тикет</th>
            <th>Тема</th>
            <th>Очередь · владелец</th>
            <th className="num">Реакция</th>
            <th className="num">Решение</th>
            <th className="num">До пробития</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          {tickets.slice(0, 30).map((tk) => {
            const eta = tk.breach_eta_min;
            const etaCls = eta < 0 ? "crit" : eta < 30 ? "warn" : "ok";
            const etaLabel = eta < 0 ? `пробит +${fmtMin(Math.abs(eta))}` : fmtMin(eta);
            return (
              <tr key={tk.id} onClick={() => onPick(tk)}>
                <td><span className="mono" style={{ color: "var(--brand)", fontSize: 12.5, fontWeight: 600 }}>{tk.ticket_number}</span></td>
                <td><div style={{ maxWidth: 380, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 500 }}>{tk.title}</div></td>
                <td>
                  <div style={{ fontSize: 12.5, fontFamily: "var(--font-mono)", color: "var(--ink-2)" }}>{tk.queue}</div>
                  <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 2, fontFamily: "var(--font-mono)" }}>{tk.owner}</div>
                </td>
                <td className="num">
                  <div className={`bar-cell r ${tk.r_over ? "crit" : tk.r_used > 80 ? "warn" : ""}`}>
                    <span className={`v ${tk.r_over ? "crit" : tk.r_used > 80 ? "warn" : ""}`}>{tk.r_used}%</span>
                    <div className="bar"><i style={{ width: `${Math.min(tk.r_used, 100)}%` }}/></div>
                  </div>
                </td>
                <td className="num">
                  <div className={`bar-cell s ${tk.s_over ? "crit" : tk.s_used > 80 ? "warn" : ""}`}>
                    <span className={`v ${tk.s_over ? "crit" : tk.s_used > 80 ? "warn" : ""}`}>{tk.s_used}%</span>
                    <div className="bar"><i style={{ width: `${Math.min(tk.s_used, 100)}%` }}/></div>
                  </div>
                </td>
                <td className="num">
                  <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: etaCls === "crit" ? "var(--crit)" : etaCls === "warn" ? "var(--warn)" : "var(--ok)" }}>
                    {etaLabel}
                  </span>
                </td>
                <td>
                  {tk.r_over && tk.s_over ? <span className="badge crit"><span className="dot"/>Оба пробиты</span>
                    : tk.r_over ? <span className="badge react"><span className="dot"/>Реакция пробита</span>
                    : tk.s_over ? <span className="badge resolve"><span className="dot"/>Решение пробито</span>
                    : tk.tier === "crit" ? <span className="badge crit"><span className="dot"/>Критич. риск</span>
                    : <span className="badge warn"><span className="dot"/>В зоне риска</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {tickets.length === 0 && (
        <div className="empty">
          <div className="ttl">Тикетов в риске нет</div>
          <div className="sub">Все SLA в пределах нормы по выбранным фильтрам.</div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Team table
// ============================================================
function TeamTable({ agents }) {
  return (
    <div className="table-wrap" style={{ maxHeight: 560 }}>
      <table className="qtbl">
        <thead>
          <tr>
            <th>Агент</th>
            <th className="num">Открыто</th>
            <th className="num">Обработано</th>
            <th className="num">SLA %</th>
            <th className="num">⌀ время</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          {[...agents].sort((a, b) => b.open - a.open).map((a) => {
            const slaCls = a.sla_pct >= 92 ? "ok" : a.sla_pct >= 85 ? "warn" : "crit";
            return (
              <tr key={a.name}>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 30, height: 30, borderRadius: "50%", background: "linear-gradient(135deg, #6366f1, #4f46e5)", color: "#fff", fontSize: 11, fontWeight: 700, display: "grid", placeItems: "center" }}>{a.initials}</div>
                    <div>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 600 }}>{a.name}</div>
                      <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 2 }}>{a.over ? "перегружен" : a.top ? "топ-исполнитель" : "в норме"}</div>
                    </div>
                  </div>
                </td>
                <td className="num"><span className="mono" style={{ fontSize: 14, fontWeight: 700, color: a.open > 20 ? "var(--crit)" : a.open > 15 ? "var(--warn)" : "var(--ink)" }}>{a.open}</span></td>
                <td className="num"><span className="mono" style={{ fontSize: 13, color: "var(--ink-2)" }}>{a.handled}</span></td>
                <td className="num"><span className={`hp ${slaCls}`} style={{ width: 36, height: 36, fontSize: 12 }}>{a.sla_pct}</span></td>
                <td className="num"><span className="mono" style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{fmtMin(a.avg_min)}</span></td>
                <td>
                  {a.over ? <span className="badge crit"><span className="dot"/>Перегружен</span>
                    : a.top ? <span className="badge ok"><span className="dot"/>Топ-исполнитель</span>
                    : <span className="badge"><span className="dot"/>Норма</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// DRAWER
// ============================================================
function PortalDrawer({ drawer, onClose }) {
  return (
    <>
      <div className={`scrim ${drawer.open ? "open" : ""}`} onClick={onClose}/>
      <aside className={`drawer ${drawer.open ? "open" : ""}`}>
        {drawer.kind === "queue" && drawer.payload && <QueueDrawerBody q={drawer.payload} onClose={onClose}/>}
        {drawer.kind === "ticket" && drawer.payload && <TicketDrawerBody t={drawer.payload} onClose={onClose}/>}
      </aside>
    </>
  );
}

function QueueDrawerBody({ q, onClose }) {
  const D = window.OPSDATA;
  const daily = D.DAILY.find((d) => d.queue_id === q.id);
  const series = daily ? daily.series.slice(-30) : [];
  const heat = D.HEATMAP.find((h) => h.queue_id === q.id);
  const owners = D.OWNER_BY_QUEUE[q.id] || [];
  const hCls = q.health >= 92 ? "ok" : q.health >= 85 ? "warn" : q.health >= 75 ? "high" : "crit";
  return (
    <>
      <div className="drawer-h">
        <div>
          <div style={{ fontSize: 11, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: 0.4, fontWeight: 500, marginBottom: 4 }}>Очередь · {q.calendar}</div>
          <h3>{q.name}</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
            <span className={`prio-tag ${q.priority >= 20 ? "p20" : q.priority >= 10 ? "p10" : "p5"}`}>P{q.priority}</span>
            <span style={{ fontSize: 12, color: "var(--ink-3)" }}>{q.agents_on} агентов · ⌀ ожидание {fmtMin(q.avg_wait_min)}</span>
          </div>
        </div>
        <button className="close" onClick={onClose}><PIcon n="close" s={14}/></button>
      </div>
      <div className="drawer-b">
        {/* Top metrics */}
        <div className="metric-row">
          <div className={`metric-tile ${hCls === "ok" ? "ok" : hCls === "warn" ? "warn" : "crit"}`}>
            <div className="lab">Health</div>
            <div className="val">{q.health}</div>
            <div className="sub">из 100</div>
          </div>
          <div className="metric-tile">
            <div className="lab">Тикетов</div>
            <div className="val">{fmtNum(q.tickets)}</div>
            <div className="sub">за период</div>
          </div>
          <div className={`metric-tile ${q.at_risk > 30 ? "crit" : q.at_risk > 12 ? "warn" : ""}`}>
            <div className="lab">В риске</div>
            <div className="val">{q.at_risk}</div>
            <div className="sub">близко к breach</div>
          </div>
        </div>

        {/* Reaction / Resolution side-by-side */}
        <div className="card">
          <div className="card-h">
            <div className="t">Соблюдение SLA</div>
            <div className="right">
              <div className="legend">
                <span className="item"><span className="sw" style={{ background: "var(--reaction)" }}/>Реакция</span>
                <span className="item"><span className="sw" style={{ background: "var(--resolution)" }}/>Решение</span>
              </div>
            </div>
          </div>
          <div className="card-b" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4, color: "var(--reaction)", fontWeight: 700, marginBottom: 8 }}>Реакция</div>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
                <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.5, fontVariantNumeric: "tabular-nums", color: q.reaction.pct_ok >= 92 ? "var(--ink)" : q.reaction.pct_ok >= 85 ? "var(--warn)" : "var(--crit)" }}>
                  {q.reaction.pct_ok}<span style={{ fontSize: 14, color: "var(--ink-3)" }}>%</span>
                </div>
                <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>цель {fmtSec(q.target_response)}</span>
              </div>
              <div style={{ height: 6, background: "var(--surface-3)", borderRadius: 3, marginTop: 10, overflow: "hidden" }}>
                <div style={{ width: `${q.reaction.pct_ok}%`, height: "100%", background: "var(--reaction)", borderRadius: 3 }}/>
              </div>
              <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 8 }}>
                {q.reaction.breached} нарушений · ⌀ {fmtSec(q.reaction.avg_sec)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4, color: "var(--resolution)", fontWeight: 700, marginBottom: 8 }}>Решение</div>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
                <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.5, fontVariantNumeric: "tabular-nums", color: q.resolution.pct_ok >= 92 ? "var(--ink)" : q.resolution.pct_ok >= 85 ? "var(--warn)" : "var(--crit)" }}>
                  {q.resolution.pct_ok}<span style={{ fontSize: 14, color: "var(--ink-3)" }}>%</span>
                </div>
                <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>цель {fmtSec(q.target_resolution)}</span>
              </div>
              <div style={{ height: 6, background: "var(--surface-3)", borderRadius: 3, marginTop: 10, overflow: "hidden" }}>
                <div style={{ width: `${q.resolution.pct_ok}%`, height: "100%", background: "var(--resolution)", borderRadius: 3 }}/>
              </div>
              <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 8 }}>
                {q.resolution.breached} нарушений · ⌀ {fmtSec(q.resolution.avg_sec)}
              </div>
            </div>
          </div>
        </div>

        {/* 30-day daily trend for this queue */}
        <div className="card">
          <div className="card-h">
            <div className="t">Нарушения за 30 дней</div>
          </div>
          <div className="card-b">
            <StackedAreaChart data={series} height={180} mode="stack"/>
          </div>
        </div>

        {/* Hourly distribution */}
        {heat && (
          <div className="card">
            <div className="card-h">
              <div className="t">Распределение по часам суток</div>
            </div>
            <div className="card-b">
              <HourBarChart data={heat.hours} height={140}/>
            </div>
          </div>
        )}

        {/* Owners */}
        {owners.length > 0 && (
          <div className="card">
            <div className="card-h">
              <div className="t">Владельцы в очереди</div>
            </div>
            <div className="card-b" style={{ padding: "8px 20px 16px" }}>
              <div className="own-list">
                {owners.slice(0, 5).map((o) => (
                  <div className="own-row" key={o.name}>
                    <div className="nm">{o.name}</div>
                    <div className="figure" style={{ color: o.open > 12 ? "var(--crit)" : o.open > 6 ? "var(--warn)" : "var(--ink)" }}>{o.open} откр.</div>
                    <div className="figure"><span className={`hp ${o.sla_pct >= 92 ? "ok" : o.sla_pct >= 85 ? "warn" : "crit"}`} style={{ width: 32, height: 32, fontSize: 11 }}>{o.sla_pct}</span></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn primary"><PIcon n="open" s={13}/>Открыть тикеты</button>
          <button className="btn"><PIcon n="settings" s={13}/>Правило SLA</button>
          <button className="btn"><PIcon n="download" s={13}/>Выгрузить</button>
        </div>
      </div>
    </>
  );
}

function TicketDrawerBody({ t, onClose }) {
  return (
    <>
      <div className="drawer-h">
        <div>
          <div style={{ fontSize: 11, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: 0.4, fontWeight: 500, marginBottom: 4 }}>Тикет</div>
          <h3>{t.title}</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
            <span className="mono" style={{ fontSize: 12, color: "var(--brand)", fontWeight: 600 }}>{t.ticket_number}</span>
            <span style={{ fontSize: 12, color: "var(--ink-3)" }}>{t.queue} · {t.owner}</span>
          </div>
        </div>
        <button className="close" onClick={onClose}><PIcon n="close" s={14}/></button>
      </div>
      <div className="drawer-b">
        <div className="metric-row">
          <div className={`metric-tile ${t.r_over ? "crit" : t.r_used > 80 ? "warn" : ""}`}>
            <div className="lab">Реакция</div>
            <div className="val">{t.r_used}%</div>
            <div className="sub">{t.r_over ? `просрочка ${fmtMin(Math.abs(t.r_remain_min))}` : `осталось ${fmtMin(t.r_remain_min)}`}</div>
          </div>
          <div className={`metric-tile ${t.s_over ? "crit" : t.s_used > 80 ? "warn" : ""}`}>
            <div className="lab">Решение</div>
            <div className="val">{t.s_used}%</div>
            <div className="sub">{t.s_over ? `просрочка ${fmtMin(Math.abs(t.s_remain_min))}` : `осталось ${fmtMin(t.s_remain_min)}`}</div>
          </div>
          <div className="metric-tile">
            <div className="lab">Приоритет</div>
            <div className="val" style={{ fontSize: 18 }}>{t.priority}</div>
            <div className="sub">создан {t.created_at}</div>
          </div>
        </div>

        <div className="card">
          <div className="card-h"><div className="t">SLA · Реакция</div><div className="right"><span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>цель {fmtSec(t.target_response)}</span></div></div>
          <div className="card-b">
            <div style={{ position: "relative", height: 14, background: "var(--surface-3)", borderRadius: 6, overflow: "hidden" }}>
              <div style={{ width: `${Math.min(t.r_used, 100)}%`, height: "100%", background: t.r_over ? "var(--crit)" : "var(--reaction)" }}/>
              <div style={{ position: "absolute", top: -2, bottom: -2, left: "100%", width: 1, background: "var(--ink-4)" }}/>
            </div>
            <div style={{ marginTop: 6, fontSize: 12, color: "var(--ink-3)", display: "flex", justifyContent: "space-between" }}>
              <span>Использовано <b style={{ color: t.r_over ? "var(--crit)" : "var(--ink)" }}>{t.r_used}%</b></span>
              <span>{t.r_over ? <b style={{ color: "var(--crit)" }}>просрочка {fmtMin(Math.abs(t.r_remain_min))}</b> : `осталось ${fmtMin(t.r_remain_min)}`}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-h"><div className="t">SLA · Решение</div><div className="right"><span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>цель {fmtSec(t.target_resolution)}</span></div></div>
          <div className="card-b">
            <div style={{ position: "relative", height: 14, background: "var(--surface-3)", borderRadius: 6, overflow: "hidden" }}>
              <div style={{ width: `${Math.min(t.s_used, 100)}%`, height: "100%", background: t.s_over ? "var(--crit)" : "var(--resolution)" }}/>
              <div style={{ position: "absolute", top: -2, bottom: -2, left: "100%", width: 1, background: "var(--ink-4)" }}/>
            </div>
            <div style={{ marginTop: 6, fontSize: 12, color: "var(--ink-3)", display: "flex", justifyContent: "space-between" }}>
              <span>Использовано <b style={{ color: t.s_over ? "var(--crit)" : "var(--ink)" }}>{t.s_used}%</b></span>
              <span>{t.s_over ? <b style={{ color: "var(--crit)" }}>просрочка {fmtMin(Math.abs(t.s_remain_min))}</b> : `осталось ${fmtMin(t.s_remain_min)}`}</span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn primary"><PIcon n="open" s={13}/>Открыть в OTRS</button>
          <button className="btn">Переназначить</button>
          <button className="btn">Эскалация</button>
        </div>
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
