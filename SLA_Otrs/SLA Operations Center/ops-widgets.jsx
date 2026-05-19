// All major widgets for the SLA Operations Center.
// Globals expected: React, Ico, MiniSpark, HealthRing, GaugeRing, KpiTile, opsFmt, OPSDATA, Delta
const { useState, useMemo, useEffect } = React;

// =====================================================
// INCIDENT BANNER (top alerts)
// =====================================================
function IncidentBanner({ incidents, onClick }) {
  if (!incidents || incidents.length === 0) return null;
  const top = incidents[0];
  return (
    <div className="incident-banner" onClick={() => onClick && onClick(top)} style={{ cursor: "pointer" }}>
      <div className="ico"><Ico name="risk" size={18}/></div>
      <div className="body">
        <div className="ttl">
          <span style={{ color: "var(--crit)", marginRight: 6 }}>● {top.id}</span>
          {top.title}
        </div>
        <div className="meta" style={{ display: "flex", gap: 12, marginTop: 4, fontSize: 11.5 }}>
          <span><b style={{ color: "var(--text-2)" }}>{top.affected_queues.length}</b> очередей затронуто</span>
          <span><b style={{ color: "var(--crit)" }}>{top.breach_count}</b> нарушений за инцидент</span>
          <span>Открыт <b style={{ color: "var(--text-2)" }}>{opsFmt.fmtMin(top.started_min_ago)}</b> назад</span>
          <span>Координатор · <b style={{ color: "var(--text-2)" }}>{top.coordinator}</b></span>
        </div>
      </div>
      <div className="actions">
        {incidents.length > 1 && (
          <span className="badge crit">+{incidents.length - 1} ещё</span>
        )}
        <button className="btn sm">Открыть инцидент-центр</button>
      </div>
    </div>
  );
}
window.IncidentBanner = IncidentBanner;

// =====================================================
// GLOBAL STATUS STRIP (KPI tiles)
// =====================================================
function StatusStrip({ kpi }) {
  const accentForHealth = (h) => h >= 92 ? "ok" : h >= 85 ? "warn" : h >= 75 ? "high" : "crit";
  return (
    <div className="status-strip">
      <KpiTile
        label="SLA Health"
        value={kpi.health}
        unit="%"
        accent={accentForHealth(kpi.health)}
        delta={-1.4}
        spark={kpi.spark.health}
        sparkColor="var(--accent)"
        icon={<Ico name="target" size={11}/>}
      />
      <KpiTile
        label="Активные нарушения"
        value={kpi.active_breaches}
        accent="crit"
        delta={12} deltaInvert={false}
        hint={`-${Math.round(kpi.active_breaches*0.05)} за час`}
        spark={kpi.spark.breaches}
        sparkColor="var(--crit)"
        icon={<Ico name="risk" size={11}/>}
      />
      <KpiTile
        label="Критичных очередей"
        value={kpi.critical_queues}
        accent="crit"
        hint={`из 12`}
        icon={<Ico name="fire" size={11}/>}
      />
      <KpiTile
        label="⌀ Реакция"
        value={kpi.avg_response_min}
        unit="мин"
        accent="react"
        delta={8} deltaInvert
        spark={kpi.spark.response}
        sparkColor="var(--reaction)"
        icon={<Ico name="clock" size={11}/>}
      />
      <KpiTile
        label="⌀ Решение"
        value={kpi.avg_resolution_h}
        unit="ч"
        accent="resolve"
        delta={-3} deltaInvert
        spark={kpi.spark.resolution}
        sparkColor="var(--resolution)"
        icon={<Ico name="bolt" size={11}/>}
      />
      <KpiTile
        label="Тикеты в зоне риска"
        value={kpi.tickets_at_risk}
        accent="warn"
        delta={6}
        spark={kpi.spark.at_risk}
        sparkColor="var(--warn)"
        icon={<Ico name="risk" size={11}/>}
      />
      <KpiTile
        label="Без владельца"
        value={kpi.unassigned}
        accent="warn"
        spark={kpi.spark.unassigned}
        sparkColor="var(--warn)"
        icon={<Ico name="user" size={11}/>}
      />
      <KpiTile
        label="Активные инциденты"
        value={kpi.active_incidents}
        accent="crit"
        hint="требуют внимания"
        icon={<Ico name="bell" size={11}/>}
      />
    </div>
  );
}
window.StatusStrip = StatusStrip;

// =====================================================
// RESPONSE vs RESOLUTION dual card
// =====================================================
function MetricCard({ kind, label, target, queues, totalTickets, totalBreached, pct, trend, onPickQueue }) {
  const ringColor = kind === "reaction" ? "var(--reaction)" : "var(--resolution)";
  const bigCls = pct >= 95 ? "healthy" : pct >= 90 ? "warn" : "crit";
  const worst = [...queues].sort((a, b) =>
    kind === "reaction" ? b.reaction.breached - a.reaction.breached : b.resolution.breached - a.resolution.breached
  ).slice(0, 3);

  return (
    <div className={`metric-card ${kind}`}>
      <div className="top">
        <span className="pip"/>
        <span className="name">{label}</span>
        <span className="target">цель ⌀ {target}</span>
      </div>
      <div className="core">
        <div className="donut-wrap">
          <GaugeRing pct={pct} color={ringColor} size={138} stroke={10}/>
          <div className="donut-center">
            <span className={`big ${bigCls}`}>{pct}<span style={{ fontSize: 16, opacity: 0.5 }}>%</span></span>
            <span className="sml">в срок</span>
          </div>
        </div>
        <div className="breakdown">
          <div className="bd-row">
            <span className="lab">Всего тикетов</span>
            <span className="num">{opsFmt.fmtNum(totalTickets)}</span>
          </div>
          <div className="bd-row">
            <span className="lab" style={{ color: kind === "reaction" ? "var(--reaction)" : "var(--resolution)" }}>В срок</span>
            <span className="num ok">{opsFmt.fmtNum(totalTickets - totalBreached)}</span>
            <div className="bar fill"><i style={{ width: `${pct}%` }}/></div>
          </div>
          <div className="bd-row">
            <span className="lab" style={{ color: "var(--crit)" }}>Нарушено</span>
            <span className="num crit">{opsFmt.fmtNum(totalBreached)}</span>
            <div className="bar over"><i style={{ width: `${100 - pct}%` }}/></div>
          </div>
        </div>
      </div>

      <div className="trend">
        <div className="trend-head">
          <span>Тренд нарушений · 16 интервалов</span>
          <span style={{ color: ringColor }}>● {kind === "reaction" ? "реакция" : "решение"}</span>
        </div>
        <MiniSpark data={trend} color={ringColor} w={420} h={48} fill={true}/>
      </div>

      <div className="trend" style={{ borderTop: "1px solid var(--border)", padding: 0, margin: 0 }}>
        <div className="trend-head" style={{ padding: "10px 16px 6px" }}>
          <span>Топ-3 очереди по нарушениям</span>
          <span>{worst.length === 0 ? "—" : ""}</span>
        </div>
        <div style={{ padding: "0 16px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
          {worst.map((q) => {
            const breach = kind === "reaction" ? q.reaction.breached : q.resolution.breached;
            const maxBreach = Math.max(...queues.map((qq) => kind === "reaction" ? qq.reaction.breached : qq.resolution.breached), 1);
            const w = (breach / maxBreach) * 100;
            return (
              <div key={q.id} onClick={() => onPickQueue && onPickQueue(q)} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 10, cursor: "pointer", alignItems: "center" }}>
                <div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{q.name}</div>
                  <div style={{ height: 5, background: "var(--bg-3)", borderRadius: 3, marginTop: 4, overflow: "hidden" }}>
                    <div style={{ width: `${w}%`, height: "100%", background: ringColor, borderRadius: 3, boxShadow: `0 0 6px ${ringColor}` }}/>
                  </div>
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--crit)", textAlign: "right", minWidth: 38 }}>{breach}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
window.MetricCard = MetricCard;

function DualMetric({ kpi, queues, onPickQueue }) {
  return (
    <div className="dual-metric">
      <MetricCard
        kind="reaction"
        label="SLA · Реакция"
        target={opsFmt.fmtSec(queues.reduce((s,q)=>s+q.target_response,0)/queues.length)}
        queues={queues}
        totalTickets={kpi.total_tickets}
        totalBreached={kpi.total_reaction_breach}
        pct={kpi.reaction_pct}
        trend={Array.from({length: 16}, (_, i) => queues.reduce((s, q) => s + (q.reaction.trend[i] || 0), 0))}
        onPickQueue={onPickQueue}
      />
      <MetricCard
        kind="resolution"
        label="SLA · Решение"
        target={opsFmt.fmtSec(queues.reduce((s,q)=>s+q.target_resolution,0)/queues.length)}
        queues={queues}
        totalTickets={kpi.total_tickets}
        totalBreached={kpi.total_resolution_breach}
        pct={kpi.resolution_pct}
        trend={Array.from({length: 16}, (_, i) => queues.reduce((s, q) => s + (q.resolution.trend[i] || 0), 0))}
        onPickQueue={onPickQueue}
      />
    </div>
  );
}
window.DualMetric = DualMetric;

// =====================================================
// QUEUE HEALTH MAP — tile grid
// =====================================================
function QueueHealthMap({ queues, onPickQueue, sortBy, setSortBy }) {
  const sorted = useMemo(() => {
    return [...queues].sort((a, b) => {
      if (sortBy === "health") return a.health - b.health;
      if (sortBy === "breaches") return (b.reaction.breached + b.resolution.breached) - (a.reaction.breached + a.resolution.breached);
      if (sortBy === "at_risk") return b.at_risk - a.at_risk;
      if (sortBy === "wait") return b.avg_wait_min - a.avg_wait_min;
      return a.name.localeCompare(b.name);
    });
  }, [queues, sortBy]);

  return (
    <div className="panel">
      <div className="panel-head">
        <div className="ttl"><span className="acc-bar"/>Карта здоровья очередей</div>
        <span className="sub">{queues.length} очередей · live</span>
        <div className="right">
          <div className="seg">
            <button className={sortBy === "health" ? "active" : ""} onClick={() => setSortBy("health")}>Health ↓</button>
            <button className={sortBy === "breaches" ? "active" : ""} onClick={() => setSortBy("breaches")}>Нарушений</button>
            <button className={sortBy === "at_risk" ? "active" : ""} onClick={() => setSortBy("at_risk")}>В риске</button>
            <button className={sortBy === "wait" ? "active" : ""} onClick={() => setSortBy("wait")}>Ожидание</button>
            <button className={sortBy === "name" ? "active" : ""} onClick={() => setSortBy("name")}>A→Я</button>
          </div>
        </div>
      </div>
      <div className="q-grid">
        {sorted.map((q) => <QueueTile key={q.id} q={q} onPick={() => onPickQueue(q)}/>)}
      </div>
    </div>
  );
}

function QueueTile({ q, onPick }) {
  return (
    <div className={`q-tile tier-${q.tier}`} onClick={onPick}>
      <div className="qh-top">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="qh-name">{q.name}</div>
          <div className="qh-meta">P{q.priority} · {q.calendar} · {q.agents_on} агент.</div>
        </div>
        <div style={{ position: "relative" }}>
          <HealthRing pct={q.health} size={46} stroke={4} showLabel fontSize={12}/>
        </div>
      </div>
      <div className="qh-stats">
        <div className="qh-stat">
          <div className="lab"><span className="pip r"/>Реакция</div>
          <div className={`v ${q.reaction.pct_ok >= 92 ? "ok" : q.reaction.pct_ok >= 85 ? "warn" : "crit"}`}>
            {q.reaction.pct_ok}<span style={{ fontSize: 10, opacity: 0.6 }}>%</span>
            <span style={{ fontSize: 10, marginLeft: 6, color: "var(--text-3)" }}>×{q.reaction.breached}</span>
          </div>
        </div>
        <div className="qh-stat">
          <div className="lab"><span className="pip s"/>Решение</div>
          <div className={`v ${q.resolution.pct_ok >= 92 ? "ok" : q.resolution.pct_ok >= 85 ? "warn" : "crit"}`}>
            {q.resolution.pct_ok}<span style={{ fontSize: 10, opacity: 0.6 }}>%</span>
            <span style={{ fontSize: 10, marginLeft: 6, color: "var(--text-3)" }}>×{q.resolution.breached}</span>
          </div>
        </div>
        <div className="qh-stat">
          <div className="lab">В риске</div>
          <div className={`v ${q.at_risk > 30 ? "crit" : q.at_risk > 12 ? "warn" : "muted"}`}>{q.at_risk}</div>
        </div>
        <div className="qh-stat">
          <div className="lab">⌀ Ожидание</div>
          <div className="v muted">{opsFmt.fmtMin(q.avg_wait_min)}</div>
        </div>
      </div>
      <div className="qh-bars">
        <div className="seg r"><i style={{ width: `${100 - q.reaction.pct_ok}%` }}/></div>
        <div className="seg s"><i style={{ width: `${100 - q.resolution.pct_ok}%` }}/></div>
      </div>
    </div>
  );
}
window.QueueHealthMap = QueueHealthMap;

// =====================================================
// TICKETS AT RISK — live table
// =====================================================
function AtRiskTable({ tickets, onPickTicket }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="ttl"><span className="acc-bar" style={{ background: "var(--crit)", boxShadow: "0 0 8px var(--crit)" }}/>Тикеты на грани нарушения SLA</div>
        <span className="sub">{tickets.length} тикетов · сортировано по времени до breach</span>
        <div className="right">
          <button className="btn sm"><Ico name="download" size={12}/>CSV</button>
        </div>
      </div>
      <div style={{ overflow: "auto" }}>
        <table className="risk-table">
          <thead>
            <tr>
              <th>Тикет</th>
              <th>Очередь · владелец</th>
              <th>SLA реакции / решения</th>
              <th className="num">До breach</th>
              <th>Прогноз</th>
              <th className="num">Severity</th>
            </tr>
          </thead>
          <tbody>
            {tickets.slice(0, 9).map((t) => (
              <AtRiskRow key={t.id} t={t} onClick={() => onPickTicket(t)}/>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ padding: "10px 14px", borderTop: "1px solid var(--border)", textAlign: "center", color: "var(--text-3)", fontSize: 11.5 }}>
        Показано 9 из {tickets.length}. <a style={{ color: "var(--accent)", cursor: "pointer" }}>Показать все →</a>
      </div>
    </div>
  );
}

function AtRiskRow({ t, onClick }) {
  const eta = t.breach_eta_min;
  const cd = eta < 0 ? { cls: "crit", label: `breach +${opsFmt.fmtMin(Math.abs(eta))}` }
            : eta < 10 ? { cls: "crit", label: `${opsFmt.fmtMin(eta)}` }
            : eta < 30 ? { cls: "high", label: `${opsFmt.fmtMin(eta)}` }
            : eta < 90 ? { cls: "warn", label: `${opsFmt.fmtMin(eta)}` }
            : { cls: "ok", label: `${opsFmt.fmtMin(eta)}` };
  const sevText = t.tier === "crit" ? "Критич." : t.tier === "high" ? "Высокий" : t.tier === "warn" ? "Предупр." : "Норма";
  return (
    <tr className={`tier-${t.tier}`} onClick={onClick}>
      <td>
        <div className="t-no mono">{t.ticket_number}</div>
        <div style={{ color: "var(--text-2)", fontSize: 11.5, marginTop: 3, maxWidth: 260, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {t.title}
        </div>
      </td>
      <td>
        <span className="q-chip"><span className="dot"/>{t.queue}</span>
        <div style={{ color: "var(--text-3)", fontSize: 11, marginTop: 3, fontFamily: "var(--font-mono)" }}>{t.owner}</div>
      </td>
      <td>
        <div className="split-prog">
          <div className="prog r">
            <span className="lab">Р</span>
            <div className="bar">
              <i className={t.r_over ? "over" : ""} style={{ width: `${Math.min(t.r_used, 100)}%` }}/>
              <div className="mark" style={{ left: "100%" }}/>
            </div>
            <span className={`v ${t.r_over ? "crit" : ""}`}>{t.r_used}%</span>
          </div>
          <div className="prog s">
            <span className="lab">Реш</span>
            <div className="bar">
              <i className={t.s_over ? "over" : ""} style={{ width: `${Math.min(t.s_used, 100)}%` }}/>
              <div className="mark" style={{ left: "100%" }}/>
            </div>
            <span className={`v ${t.s_over ? "crit" : ""}`}>{t.s_used}%</span>
          </div>
        </div>
      </td>
      <td className="num">
        <div className={`countdown ${cd.cls}`}>{cd.label}</div>
      </td>
      <td>
        {t.r_over && t.s_over ? <span className="badge crit blink">Оба пробиты</span>
          : t.r_over ? <span className="badge react">Реакция пробита</span>
          : t.s_over ? <span className="badge resolve">Решение пробито</span>
          : <span className="badge warn">Близко к breach</span>}
      </td>
      <td className="num"><span className={`badge ${t.tier === "crit" ? "crit blink" : t.tier === "high" ? "high" : "warn"}`}>{sevText}</span></td>
    </tr>
  );
}
window.AtRiskTable = AtRiskTable;

// =====================================================
// EVENT STREAM (right rail)
// =====================================================
function EventStream({ events }) {
  const [paused, setPaused] = useState(false);
  const iconForType = {
    breach:     <Ico name="risk" size={14}/>,
    escalation: <Ico name="bolt" size={14}/>,
    reassign:   <Ico name="swap" size={14}/>,
    overload:   <Ico name="fire" size={14}/>,
    incident:   <Ico name="bell" size={14}/>,
    recovery:   <Ico name="target" size={14}/>,
  };
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="ttl"><span className="acc-bar"/>Operational stream</div>
        <span className="sub">real-time</span>
        <div className="right">
          <button className="btn icon-only sm" onClick={() => setPaused(!paused)} title={paused ? "Возобновить" : "Пауза"}>
            <Ico name={paused ? "play" : "pause"} size={12}/>
          </button>
        </div>
      </div>
      <div className="stream" style={{ maxHeight: 540, overflow: "auto" }}>
        {events.map((e, i) => (
          <div key={i} className={`stream-item ${e.kind}`}>
            <div className="ic">{iconForType[e.type] || <Ico name="bell" size={14}/>}</div>
            <div className="body">
              <div className="tt">{e.title}</div>
              <div className="meta">
                <span className="ts">{e.ts}</span>
                <span>·</span>
                <span className="q-chip"><span className="dot"/>{e.queue}</span>
                {e.ticket !== "—" && <><span>·</span><span style={{ fontFamily: "var(--font-mono)", color: "var(--accent)" }}>{e.ticket}</span></>}
                <span>·</span>
                <span style={{ fontFamily: "var(--font-mono)" }}>{e.who}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
window.EventStream = EventStream;

// =====================================================
// BOTTLENECK panel
// =====================================================
function Bottleneck({ items, onPickQueue }) {
  const max = Math.max(...items.map((i) => i.avg_wait_min), 1);
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="ttl"><span className="acc-bar" style={{ background: "var(--high)", boxShadow: "0 0 8px var(--high)" }}/>Где застревают тикеты</div>
        <span className="sub">топ по среднему времени ожидания</span>
      </div>
      <div style={{ padding: "4px 0" }}>
        <div className="bn-row" style={{ borderBottom: "1px solid var(--border)", background: "rgba(255,255,255,0.015)", textTransform: "uppercase", letterSpacing: "0.5px", fontSize: 10, color: "var(--text-3)", cursor: "default" }}>
          <span>Очередь</span>
          <span>⌀ Время ожидания (макс {opsFmt.fmtMin(max)})</span>
          <span style={{ textAlign: "right" }}>Реассайн</span>
          <span style={{ textAlign: "right" }}>«Зависших»</span>
        </div>
        {items.map((it) => (
          <div key={it.queue_id} className="bn-row" onClick={() => onPickQueue && onPickQueue(it)}>
            <div className="qn">
              {it.name}
              <div className="sub">{it.kind === "reaction" ? "узкое место: реакция" : "узкое место: решение"}</div>
            </div>
            <div className="bar">
              <i className={it.kind === "resolution" ? "s" : ""} style={{ width: `${(it.avg_wait_min / max) * 100}%` }}/>
              <span className="lbl">{opsFmt.fmtMin(it.avg_wait_min)}</span>
            </div>
            <div className="figure">{it.reassignments}</div>
            <div className="figure" style={{ color: "var(--crit)" }}>{it.stuck}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
window.Bottleneck = Bottleneck;

// =====================================================
// AGENT WORKLOAD MATRIX
// =====================================================
function AgentMatrix({ agents }) {
  const sorted = [...agents].sort((a, b) => b.open - a.open);
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="ttl"><span className="acc-bar" style={{ background: "var(--accent)" }}/>Нагрузка на агентов</div>
        <span className="sub">{agents.length} человек · {agents.filter((a) => a.over).length} перегружено</span>
        <div className="right">
          <span className="badge ok">● на высоте · {agents.filter((a) => a.top).length}</span>
          <span className="badge crit">● перегружены · {agents.filter((a) => a.over).length}</span>
        </div>
      </div>
      <div className="agent-grid">
        {sorted.map((a) => (
          <div key={a.name} className={`agent-cell ${a.over ? "over" : ""} ${a.top ? "top" : ""}`}>
            <div className="name">
              <div className="ava">{a.initials}</div>
              <span style={{ fontFamily: "var(--font-mono)" }}>{a.name}</span>
            </div>
            <div className="stats">
              <div className="stat">
                <div className="lab">Открыто</div>
                <div className={`v ${a.open > 20 ? "crit" : a.open > 15 ? "warn" : "ok"}`}>{a.open}</div>
              </div>
              <div className="stat">
                <div className="lab">% SLA</div>
                <div className={`v ${a.sla_pct >= 92 ? "ok" : a.sla_pct >= 85 ? "warn" : "crit"}`}>{a.sla_pct}</div>
              </div>
              <div className="stat">
                <div className="lab">Закрыто</div>
                <div className="v" style={{ color: "var(--text-2)" }}>{a.handled}</div>
              </div>
              <div className="stat">
                <div className="lab">⌀ время</div>
                <div className="v" style={{ color: "var(--text-2)" }}>{opsFmt.fmtMin(a.avg_min)}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
window.AgentMatrix = AgentMatrix;
