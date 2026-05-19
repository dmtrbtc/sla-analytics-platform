// Main app shell
const { useState: useStateA, useEffect: useEffectA, useMemo: useMemoA } = React;

const NAV = [
  { key: "dashboard", label: "Дашборд", icon: "dashboard" },
  { key: "analytics", label: "Аналитика", icon: "fund" },
  { key: "tickets",   label: "Тикеты", icon: "ticket" },
  { key: "sla",       label: "SLA · Мониторинг", icon: "target", active: true },
  { key: "sla-cfg",   label: "Конфигурация SLA", icon: "clock" },
  { key: "imports",   label: "Импорт", icon: "upload" },
  { key: "reports",   label: "Отчёты", icon: "file" },
  { key: "teams",     label: "Команды", icon: "team" },
];

function App() {
  const [t, setTweak] = useTweaks({
    accent_palette: "blue",
    layout_density: "comfortable",
    show_sparklines: true,
    show_priority_col: true,
    color_mode: "heatmap",
  });

  // --- top-level state ---
  const [view, setView]               = useStateA("matrix"); // matrix | split | feed
  const [period, setPeriod]           = useStateA(30);
  const [search, setSearch]           = useStateA("");
  const [groupBy, setGroupBy]         = useStateA("all");    // all | support | infra | biz
  const [kindFilter, setKindFilter]   = useStateA("all");    // all | reaction | resolution | both
  const [queueFilter, setQueueFilter] = useStateA("all");
  const [sevFilter, setSevFilter]     = useStateA("all");

  const [sortMatrix, setSortMatrix]   = useStateA({ key: "r_breached", dir: "desc" });
  const [sortFeed, setSortFeed]       = useStateA({ key: "overdue", dir: "desc" });

  const [drawer, setDrawer]           = useStateA({ open: false, kind: null, payload: null });

  // hot-key escape to close
  useEffectA(() => {
    const fn = (e) => { if (e.key === "Escape") setDrawer((d) => ({ ...d, open: false })); };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, []);

  const D = window.MOCK;
  const queueMetrics = D.QUEUE_METRICS;
  const tickets = D.TICKETS;
  const kpis = D.KPIS;

  const onPickQueue = (q) => setDrawer({ open: true, kind: "queue", payload: q });
  const onPickTicket = (t) => setDrawer({ open: true, kind: "ticket", payload: t });
  const closeDrawer = () => setDrawer((d) => ({ ...d, open: false }));

  return (
    <div className="app">
      {/* Sidebar */}
      <nav className="sider">
        <div className="brand">
          <span className="brand-mark">SLA</span>
          <span>SLA Platform</span>
        </div>
        <div className="menu">
          {NAV.map((n) => (
            <div key={n.key} className={`menu-item ${n.active ? "active" : ""}`}>
              <span className="icon"><Icon name={n.icon} size={14} color="currentColor"/></span>
              <span>{n.label}</span>
            </div>
          ))}
        </div>
      </nav>

      <main className="main">
        {/* Top bar */}
        <div className="topbar">
          <div className="crumbs">
            SLA <span style={{ margin: "0 6px" }}>/</span> <strong>Мониторинг нарушений</strong>
          </div>
          <div className="user">
            <button className="btn icon-only" title="Уведомления"><Icon name="bell" size={14}/></button>
            <button className="btn icon-only" title="Обновить"><Icon name="refresh" size={14}/></button>
            <div className="avatar">АИ</div>
          </div>
        </div>

        {/* Page */}
        <div className="page">
          {/* Header */}
          <div className="page-header">
            <div>
              <h1>
                Мониторинг SLA
                <span className="live-pill"><span className="live-dot"/>Live · обновлено 5 сек назад</span>
              </h1>
              <div className="sub">Нарушения по реакции и решению с разбивкой по очередям. Период — последние {period} дн.</div>
            </div>

            <div className="row" style={{ gap: 8 }}>
              <select className="select" value={period} onChange={(e) => setPeriod(+e.target.value)}>
                <option value={1}>Сегодня</option>
                <option value={7}>Последние 7 дн</option>
                <option value={30}>Последние 30 дн</option>
                <option value={90}>Последние 90 дн</option>
              </select>
              <button className="btn"><Icon name="download" size={13}/>Экспорт CSV</button>
              <button className="btn primary"><Icon name="settings" size={13}/>Настроить SLA</button>
            </div>
          </div>

          {/* KPI strip */}
          <div className="kpi-grid">
            <Kpi
              label={<span>Всего тикетов</span>}
              value={fmt.fmtNum(kpis.total_tickets)}
              hint={`за ${period} дн`}
              accent="blue"
              icon={<Icon name="ticket" size={13}/>}
              delta={-3}
            />
            <Kpi
              label="% SLA по реакции"
              value={`${kpis.overall_reaction_pct}%`}
              icon={<Icon name="clock" size={13}/>}
              accent={kpis.overall_reaction_pct >= 95 ? "green" : kpis.overall_reaction_pct >= 90 ? "orange" : "red"}
              delta={1.2}
            />
            <Kpi
              label="% SLA по решению"
              value={`${kpis.overall_resolution_pct}%`}
              icon={<Icon name="target" size={13}/>}
              accent={kpis.overall_resolution_pct >= 95 ? "green" : kpis.overall_resolution_pct >= 90 ? "orange" : "red"}
              delta={-2.1}
            />
            <Kpi
              label="Нарушений реакции"
              value={fmt.fmtNum(kpis.total_reaction_breach)}
              accent="orange"
              icon={<Icon name="warn" size={13}/>}
              delta={8}
            />
            <Kpi
              label="Нарушений решения"
              value={fmt.fmtNum(kpis.total_resolution_breach)}
              accent="violet"
              icon={<Icon name="warn" size={13}/>}
              delta={4}
            />
            <Kpi
              label="Очередей в риске"
              value={kpis.queues_at_risk}
              hint={`из ${queueMetrics.length}`}
              accent="red"
              icon={<Icon name="fire" size={13}/>}
            />
          </div>

          {/* View tabs + filters */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
            <div className="view-tabs">
              <button className={view === "matrix" ? "active" : ""} onClick={() => setView("matrix")}>
                <Icon name="matrix" size={14}/>Матрица очередей
              </button>
              <button className={view === "split" ? "active" : ""} onClick={() => setView("split")}>
                <Icon name="split" size={14}/>Реакция | Решение
              </button>
              <button className={view === "feed" ? "active" : ""} onClick={() => setView("feed")}>
                <Icon name="list" size={14}/>Лента нарушений
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="filters">
            <input
              className="input search"
              placeholder="Поиск по очереди, тикету, теме..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: 280 }}
            />

            {view === "matrix" && (
              <React.Fragment>
                <div className="sep"/>
                <span className="label">Группа:</span>
                <div className="seg">
                  <button className={groupBy === "all" ? "active" : ""} onClick={() => setGroupBy("all")}>Все ({queueMetrics.length})</button>
                  <button className={groupBy === "support" ? "active" : ""} onClick={() => setGroupBy("support")}>Support</button>
                  <button className={groupBy === "infra" ? "active" : ""} onClick={() => setGroupBy("infra")}>Infra</button>
                  <button className={groupBy === "biz" ? "active" : ""} onClick={() => setGroupBy("biz")}>Бизнес</button>
                </div>
              </React.Fragment>
            )}

            {view === "feed" && (
              <React.Fragment>
                <div className="sep"/>
                <span className="label">Тип нарушения:</span>
                <div className="seg">
                  <button className={kindFilter === "all" ? "active" : ""} onClick={() => setKindFilter("all")}>Все</button>
                  <button className={kindFilter === "reaction" ? "active" : ""} onClick={() => setKindFilter("reaction")}>
                    <span style={{ color: "#fa8c16" }}>●</span> Реакция
                  </button>
                  <button className={kindFilter === "resolution" ? "active" : ""} onClick={() => setKindFilter("resolution")}>
                    <span style={{ color: "#722ed1" }}>●</span> Решение
                  </button>
                  <button className={kindFilter === "both" ? "active" : ""} onClick={() => setKindFilter("both")}>
                    <span style={{ color: "#ff4d4f" }}>●</span> Оба
                  </button>
                </div>
                <div className="sep"/>
                <span className="label">Очередь:</span>
                <select className="select" value={queueFilter} onChange={(e) => setQueueFilter(e.target.value)} style={{ minWidth: 160 }}>
                  <option value="all">Все очереди</option>
                  {queueMetrics.map((q) => <option key={q.id} value={q.id}>{q.name}</option>)}
                </select>
                <div className="sep"/>
                <span className="label">Severity:</span>
                <select className="select" value={sevFilter} onChange={(e) => setSevFilter(e.target.value)}>
                  <option value="all">Любой</option>
                  <option value="warn">Предупр.</option>
                  <option value="high">Высокий</option>
                  <option value="crit">Критич.</option>
                </select>
              </React.Fragment>
            )}

            <div className="spacer"/>
            <button className="btn sm"><Icon name="refresh" size={12}/>Сбросить</button>
          </div>

          {/* Active view */}
          {view === "matrix" && (
            <MatrixView
              queueMetrics={queueMetrics}
              onPickQueue={onPickQueue}
              search={search}
              group={groupBy}
              sort={sortMatrix}
              setSort={setSortMatrix}
            />
          )}
          {view === "split" && (
            <SplitView
              queueMetrics={queueMetrics}
              onPickQueue={onPickQueue}
              search={search}
            />
          )}
          {view === "feed" && (
            <FeedView
              tickets={tickets}
              onPickTicket={onPickTicket}
              search={search}
              kindFilter={kindFilter}
              queueFilter={queueFilter}
              severityFilter={sevFilter}
              sort={sortFeed}
              setSort={setSortFeed}
            />
          )}

          {/* Helper note at bottom */}
          <div style={{ marginTop: 24, padding: "12px 16px", background: "var(--color-primary-bg)", borderLeft: "3px solid var(--color-primary)", borderRadius: 4, fontSize: 13, color: "var(--color-text-secondary)" }}>
            <strong style={{ color: "var(--color-text)" }}>Подсказка.</strong> Кликните по строке очереди — откроется детализация с тиками-нарушителями и трендом. Сортировка работает по любому столбцу — нажмите на заголовок.
          </div>
        </div>
      </main>

      {/* Drawer */}
      <Drawer
        open={drawer.open}
        kind={drawer.kind}
        payload={drawer.payload}
        tickets={tickets}
        onClose={closeDrawer}
        onPickTicket={onPickTicket}
      />

      {/* Tweaks panel */}
      <TweaksPanel title="Tweaks · SLA Monitor">
        <TweakSection label="Внешний вид">
          <TweakRadio
            label="Плотность"
            value={t.layout_density}
            options={[
              { value: "compact", label: "Плотно" },
              { value: "comfortable", label: "Стандарт" },
            ]}
            onChange={(v) => setTweak("layout_density", v)}
          />
          <TweakToggle
            label="Спарклайны трендов"
            value={t.show_sparklines}
            onChange={(v) => setTweak("show_sparklines", v)}
          />
          <TweakToggle
            label="Столбец «Приоритет»"
            value={t.show_priority_col}
            onChange={(v) => setTweak("show_priority_col", v)}
          />
        </TweakSection>
        <TweakSection label="Начальный вид">
          <TweakSelect
            label="Открывать на"
            value={view}
            options={[
              { value: "matrix", label: "Матрица очередей" },
              { value: "split", label: "Реакция | Решение" },
              { value: "feed", label: "Лента нарушений" },
            ]}
            onChange={setView}
          />
          <TweakSelect
            label="Период по умолчанию"
            value={period}
            options={[
              { value: 1, label: "Сегодня" },
              { value: 7, label: "7 дней" },
              { value: 30, label: "30 дней" },
              { value: 90, label: "90 дней" },
            ]}
            onChange={(v) => setPeriod(+v)}
          />
        </TweakSection>
      </TweaksPanel>

      {/* Density override */}
      <style>{`
        ${t.layout_density === "compact" ? `
          table.t tbody td { padding: 6px 10px; }
          table.t thead th { padding: 6px 10px; }
          .queue-row { padding: 8px 14px; }
          .feed-row { padding: 8px 14px; }
          .kpi { padding: 10px 14px; }
          .kpi-value { font-size: 22px; }
        ` : ""}
        ${!t.show_sparklines ? `table.t.matrix thead th:last-child, table.t.matrix tbody td:last-child { display: none; }` : ""}
        ${!t.show_priority_col ? `table.t.matrix thead th:nth-child(2), table.t.matrix tbody td:nth-child(2) { display: none; }` : ""}
      `}</style>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
