// Main app for the SLA Operations Center
const { useState, useEffect, useMemo, useRef } = React;

const NAV_OPS = [
  { key: "dashboard", icon: "dashboard", label: "Дашборд" },
  { key: "ops",       icon: "fund",      label: "Аналитика" },
  { key: "queues",    icon: "queues",    label: "Очереди",   badge: true },
  { key: "tickets",   icon: "ticket",    label: "Тикеты" },
  { key: "incidents", icon: "fire",      label: "Инциденты", badge: true },
  { key: "agents",    icon: "team",      label: "Агенты" },
  { key: "reports",   icon: "file",      label: "Отчёты" },
  { key: "config",    icon: "settings",  label: "SLA" },
];

function OpsApp() {
  // Tweaks
  const [t, setTweak] = useTweaks({
    reaction_color: "#ff8a3d",
    resolution_color: "#a78bfa",
    blink_critical: true,
    show_agent_matrix: true,
    show_bottleneck: true,
  });

  const D = window.OPSDATA;

  // State
  const [active, setActive] = useState("dashboard");
  const [sortQueues, setSortQueues] = useState("health");
  const [search, setSearch] = useState("");
  const [period, setPeriod] = useState("24h");
  const [scope, setScope] = useState("all");
  const [drawer, setDrawer] = useState({ open: false, kind: null, payload: null });
  const [clock, setClock] = useState(opsFmt.fmtTimeShort());

  // Live clock
  useEffect(() => {
    const id = setInterval(() => setClock(opsFmt.fmtTimeShort()), 1000);
    return () => clearInterval(id);
  }, []);

  // Esc to close drawer
  useEffect(() => {
    const fn = (e) => { if (e.key === "Escape") setDrawer((d) => ({ ...d, open: false })); };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, []);

  // Filter queues by search + scope
  const filteredQueues = useMemo(() => {
    let arr = D.QUEUES;
    if (scope === "support") arr = arr.filter((q) => q.name.startsWith("Support"));
    else if (scope === "infra") arr = arr.filter((q) => q.name.startsWith("Infrastructure"));
    else if (scope === "biz") arr = arr.filter((q) => ["Billing","Finance","HR","Development","Security"].includes(q.name));
    if (search) arr = arr.filter((q) => q.name.toLowerCase().includes(search.toLowerCase()));
    return arr;
  }, [D.QUEUES, scope, search]);

  const onPickQueue = (q) => setDrawer({ open: true, kind: "queue", payload: q });
  const onPickTicket = (tk) => setDrawer({ open: true, kind: "ticket", payload: tk });

  return (
    <div className="ops-app">
      {/* SIDE RAIL */}
      <nav className="rail">
        <div className="brand">SLA</div>
        {NAV_OPS.map((n) => (
          <button key={n.key} className={`nav-btn ${n.key === active ? "active" : ""}`} title={n.label} onClick={() => setActive(n.key)}>
            <Ico name={n.icon} size={16}/>
            {n.badge && <span className="badge-dot"/>}
          </button>
        ))}
        <div className="sp"/>
        <button className="nav-btn" title="Настройки"><Ico name="settings" size={16}/></button>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: "linear-gradient(135deg, #00d4ff, #4361ee)", display: "grid", placeItems: "center", fontSize: 10.5, fontWeight: 700, color: "#001218", marginTop: 4 }}>АИ</div>
      </nav>

      {/* WORKSPACE */}
      <div className="workspace">
        {/* HEADER */}
        <div className="hdr">
          <div className="title-block">
            <div className="crumb">SLA → MONITORING</div>
            <h1>
              SLA Operations Center
              <span className="live">Live · {D.QUEUES.length} очередей</span>
            </h1>
          </div>
          <div className="hdr-spacer"/>
          <input className="input" placeholder="Поиск очереди, тикета..." value={search} onChange={(e) => setSearch(e.target.value)}/>
          <div className="seg">
            <button className={scope === "all" ? "active" : ""} onClick={() => setScope("all")}>Все</button>
            <button className={scope === "support" ? "active" : ""} onClick={() => setScope("support")}>Support</button>
            <button className={scope === "infra" ? "active" : ""} onClick={() => setScope("infra")}>Infra</button>
            <button className={scope === "biz" ? "active" : ""} onClick={() => setScope("biz")}>Бизнес</button>
          </div>
          <select className="select" value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="1h">Последний час</option>
            <option value="24h">24 часа</option>
            <option value="7d">7 дней</option>
            <option value="30d">30 дней</option>
          </select>
          <button className="btn icon-only"><Ico name="refresh" size={13}/></button>
          <button className="btn icon-only"><Ico name="bell" size={13}/></button>
          <div className="hdr-time">
            <div className="label">UTC+3 · Moscow</div>
            <div>{clock}</div>
          </div>
        </div>

        {/* CANVAS */}
        <div className="canvas">
          {/* Incident banner — spans full width */}
          {D.INCIDENTS.length > 0 && (
            <div className="row-fullw">
              <IncidentBanner incidents={D.INCIDENTS}/>
            </div>
          )}

          {/* Global status strip */}
          <div className="row-fullw">
            <StatusStrip kpi={D.KPI}/>
          </div>

          {/* Main column: dual response/resolution + queue map + at-risk + bottleneck */}
          <div className="row-main col" style={{ gap: 14 }}>
            <DualMetric kpi={D.KPI} queues={filteredQueues} onPickQueue={onPickQueue}/>
            <QueueHealthMap queues={filteredQueues} onPickQueue={onPickQueue} sortBy={sortQueues} setSortBy={setSortQueues}/>
            <AtRiskTable tickets={D.AT_RISK} onPickTicket={onPickTicket}/>
            {t.show_bottleneck && <Bottleneck items={D.BOTTLENECKS} onPickQueue={(it) => {
              const q = D.QUEUES.find((qq) => qq.id === it.queue_id);
              if (q) onPickQueue(q);
            }}/>}
          </div>

          {/* Right rail */}
          <div className="row-rail col" style={{ gap: 14 }}>
            <EventStream events={D.EVENTS}/>
            {t.show_agent_matrix && <AgentMatrix agents={D.AGENTS}/>}
          </div>
        </div>
      </div>

      {/* Drawer */}
      <OpsDrawer
        open={drawer.open}
        kind={drawer.kind}
        payload={drawer.payload}
        onClose={() => setDrawer((d) => ({ ...d, open: false }))}
      />

      {/* Tweaks panel */}
      <TweaksPanel title="Tweaks · Operations Center">
        <TweakSection label="Визуальная сигнализация">
          <TweakToggle
            label="Мигание критических индикаторов"
            value={t.blink_critical}
            onChange={(v) => setTweak("blink_critical", v)}
          />
        </TweakSection>
        <TweakSection label="Цветовая идентичность метрик">
          <TweakColor
            label="Цвет Реакции"
            value={t.reaction_color}
            options={["#ff8a3d", "#ff5470", "#ffb340", "#00d4ff"]}
            onChange={(v) => setTweak("reaction_color", v)}
          />
          <TweakColor
            label="Цвет Решения"
            value={t.resolution_color}
            options={["#a78bfa", "#7c3aed", "#00d4ff", "#2dd482"]}
            onChange={(v) => setTweak("resolution_color", v)}
          />
        </TweakSection>
        <TweakSection label="Виджеты">
          <TweakToggle label="Нагрузка на агентов" value={t.show_agent_matrix} onChange={(v) => setTweak("show_agent_matrix", v)}/>
          <TweakToggle label="Bottleneck-блок" value={t.show_bottleneck} onChange={(v) => setTweak("show_bottleneck", v)}/>
        </TweakSection>
      </TweaksPanel>

      <style>{`
        ${!t.blink_critical ? `
          .kpi-tile.crit::before, .badge.crit.blink, .incident-banner .ico, .q-tile.tier-crit::before {
            animation: none !important;
          }
        ` : ""}
        :root {
          --reaction: ${t.reaction_color};
          --reaction-dim: ${hexA(t.reaction_color, 0.16)};
          --reaction-glow: ${hexA(t.reaction_color, 0.35)};
          --resolution: ${t.resolution_color};
          --resolution-dim: ${hexA(t.resolution_color, 0.18)};
          --resolution-glow: ${hexA(t.resolution_color, 0.35)};
        }
      `}</style>
    </div>
  );
}

// helper for tweak color → rgba
function hexA(hex, a) {
  const m = hex.replace("#", "").match(/^([a-f0-9]{6})$/i);
  if (!m) return hex;
  const r = parseInt(m[1].substring(0,2), 16);
  const g = parseInt(m[1].substring(2,4), 16);
  const b = parseInt(m[1].substring(4,6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

ReactDOM.createRoot(document.getElementById("root")).render(<OpsApp/>);
