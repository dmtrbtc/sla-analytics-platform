// Right-side drilldown drawer for the SLA Operations Center
function OpsDrawer({ open, kind, payload, onClose }) {
  return (
    <React.Fragment>
      <div className={`scrim ${open ? "open" : ""}`} onClick={onClose}/>
      <aside className={`drawer ${open ? "open" : ""}`}>
        {kind === "queue" && payload && <QueueDrillPanel q={payload} onClose={onClose}/>}
        {kind === "ticket" && payload && <TicketDrillPanel t={payload} onClose={onClose}/>}
      </aside>
    </React.Fragment>
  );
}
window.OpsDrawer = OpsDrawer;

function QueueDrillPanel({ q, onClose }) {
  return (
    <React.Fragment>
      <div className="drawer-head">
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 700 }}>{q.name}</div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Очередь · приоритет {q.priority} · {q.calendar} · {q.agents_on} агент.
          </div>
        </div>
        <button className="drawer-close" onClick={onClose}><Ico name="close" size={16}/></button>
      </div>
      <div className="drawer-body">
        {/* Header KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
          <MiniKpi label="Health" value={q.health} unit="%" tone={q.tier}/>
          <MiniKpi label="Тикетов" value={q.tickets}/>
          <MiniKpi label="Открыто" value={q.open}/>
          <MiniKpi label="В риске" value={q.at_risk} tone={q.at_risk > 30 ? "crit" : q.at_risk > 12 ? "warn" : "ok"}/>
        </div>

        {/* Reaction block */}
        <SectionHead color="var(--reaction)" label="Реакция" target={opsFmt.fmtSec(q.target_response)}/>
        <DualBarBlock kind="reaction" pct={q.reaction.pct_ok} inTime={q.reaction.in_time} breached={q.reaction.breached} avgSec={q.reaction.avg_sec} target={q.target_response}/>
        <MiniSpark data={q.reaction.trend} color="var(--reaction)" w={520} h={56} fill={true}/>

        <div style={{ height: 18 }}/>

        {/* Resolution block */}
        <SectionHead color="var(--resolution)" label="Решение" target={opsFmt.fmtSec(q.target_resolution)}/>
        <DualBarBlock kind="resolution" pct={q.resolution.pct_ok} inTime={q.resolution.in_time} breached={q.resolution.breached} avgSec={q.resolution.avg_sec} target={q.target_resolution}/>
        <MiniSpark data={q.resolution.trend} color="var(--resolution)" w={520} h={56} fill={true}/>

        <div style={{ height: 16 }}/>
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.6px", color: "var(--text-3)", marginBottom: 10 }}>Связанные тикеты с нарушением</div>
          <RelatedTickets queueId={q.id}/>
        </div>

        <div style={{ marginTop: 18, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn primary"><Ico name="open" size={12}/>Открыть все тикеты</button>
          <button className="btn"><Ico name="settings" size={12}/>Правило SLA</button>
          <button className="btn"><Ico name="clock" size={12}/>Календарь</button>
          <button className="btn"><Ico name="bell" size={12}/>Эскалации</button>
        </div>
      </div>
    </React.Fragment>
  );
}

function TicketDrillPanel({ t, onClose }) {
  const events = [
    { when: t.created_at, what: `Создан тикет в очереди ${t.queue}`, who: "system" },
    { when: t.created_at, what: "Auto-routing → " + t.queue, who: "router" },
    { when: t.created_at, what: t.r_over ? "Просрочена реакция SLA" : "Подтверждение получателем", who: t.owner },
    ...(t.s_over ? [{ when: t.created_at, what: "Просрочено решение SLA", who: "sla-engine" }] : []),
    { when: "сейчас", what: "Активный тикет — отслеживается", who: "ops-center" },
  ];
  return (
    <React.Fragment>
      <div className="drawer-head">
        <div style={{ flex: 1 }}>
          <div className="row" style={{ gap: 8 }}>
            <span style={{ fontFamily: "var(--font-mono)", color: "var(--accent)", fontWeight: 700, fontSize: 14 }}>{t.ticket_number}</span>
            {t.r_over && t.s_over
              ? <span className="badge crit blink">Оба пробиты</span>
              : t.r_over ? <span className="badge react">Реакция пробита</span>
              : t.s_over ? <span className="badge resolve">Решение пробито</span>
              : <span className="badge warn">Близко к breach</span>}
          </div>
          <div style={{ fontSize: 13, color: "var(--text)", marginTop: 5 }}>{t.title}</div>
        </div>
        <button className="drawer-close" onClick={onClose}><Ico name="close" size={16}/></button>
      </div>
      <div className="drawer-body">
        <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", rowGap: 8, columnGap: 12, fontSize: 13, marginBottom: 16 }}>
          <div className="dim">Очередь</div><div><span className="q-chip"><span className="dot"/>{t.queue}</span></div>
          <div className="dim">Владелец</div><div className="mono">{t.owner}</div>
          <div className="dim">Приоритет</div><div><span className={`badge ${t.priority === "Высокий" ? "crit" : t.priority === "Средний" ? "warn" : "neutral"}`}>{t.priority}</span></div>
          <div className="dim">Создан</div><div className="mono">{t.created_at}</div>
        </div>

        <SectionHead color="var(--reaction)" label="SLA · Реакция" target={opsFmt.fmtSec(t.target_response)}/>
        <ProgressLine kind="reaction" used={t.r_used} over={t.r_over} remain={t.r_remain_min}/>

        <div style={{ height: 14 }}/>
        <SectionHead color="var(--resolution)" label="SLA · Решение" target={opsFmt.fmtSec(t.target_resolution)}/>
        <ProgressLine kind="resolution" used={t.s_used} over={t.s_over} remain={t.s_remain_min}/>

        <div style={{ height: 18 }}/>
        <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.6px", color: "var(--text-3)", marginBottom: 8 }}>Хронология</div>
        <div style={{ borderLeft: "2px solid var(--bg-3)", paddingLeft: 14, marginLeft: 6 }}>
          {events.map((e, i) => (
            <div key={i} style={{ position: "relative", paddingBottom: 12 }}>
              <div style={{ position: "absolute", left: -21, top: 4, width: 10, height: 10, borderRadius: "50%", background: i === events.length - 1 ? "var(--accent)" : "var(--bg-4)", border: "2px solid var(--bg-1)", boxShadow: i === events.length - 1 ? "0 0 8px var(--accent-glow)" : "none" }}/>
              <div style={{ fontSize: 12 }}>{e.what}</div>
              <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>{e.when} · {e.who}</div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 18, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn primary"><Ico name="open" size={12}/>Открыть в OTRS</button>
          <button className="btn"><Ico name="swap" size={12}/>Переназначить</button>
          <button className="btn"><Ico name="bolt" size={12}/>Эскалация</button>
        </div>
      </div>
    </React.Fragment>
  );
}

// --- small reusable bits ---
function MiniKpi({ label, value, unit, tone }) {
  const cls = tone === "crit" ? "crit" : tone === "high" ? "high" : tone === "warn" ? "warn" : tone === "ok" ? "ok" : "";
  return (
    <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", padding: "10px 12px", borderRadius: 8 }}>
      <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.6px", color: "var(--text-3)", fontWeight: 600 }}>{label}</div>
      <div className={`mono ${cls ? "" : ""}`} style={{
        fontSize: 22, fontWeight: 700, marginTop: 4, letterSpacing: "-0.5px",
        color: cls ? `var(--${cls})` : "var(--text)",
      }}>
        {value}{unit && <span style={{ fontSize: 12, opacity: 0.5, marginLeft: 2 }}>{unit}</span>}
      </div>
    </div>
  );
}

function SectionHead({ color, label, target }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, boxShadow: `0 0 8px ${color}` }}/>
      <span style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>{label}</span>
      <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-3)" }}>цель · {target}</span>
    </div>
  );
}

function DualBarBlock({ kind, pct, inTime, breached, avgSec, target }) {
  const c = kind === "reaction" ? "var(--reaction)" : "var(--resolution)";
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, padding: "8px 0 12px" }}>
      <div>
        <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.6px", color: "var(--text-3)" }}>В срок</div>
        <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--ok)", marginTop: 2 }}>{opsFmt.fmtNum(inTime)}</div>
        <div style={{ height: 5, background: "var(--bg-3)", borderRadius: 3, overflow: "hidden", marginTop: 6 }}>
          <div style={{ width: `${pct}%`, height: "100%", background: c, boxShadow: `0 0 6px ${c}` }}/>
        </div>
        <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>{pct}% от общего · ⌀ {opsFmt.fmtSec(avgSec)} (цель {opsFmt.fmtSec(target)})</div>
      </div>
      <div>
        <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.6px", color: "var(--text-3)" }}>Нарушено</div>
        <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--crit)", marginTop: 2 }}>{opsFmt.fmtNum(breached)}</div>
        <div style={{ height: 5, background: "var(--bg-3)", borderRadius: 3, overflow: "hidden", marginTop: 6 }}>
          <div style={{ width: `${100 - pct}%`, height: "100%", background: "var(--crit)", boxShadow: "0 0 6px rgba(255,59,88,0.5)" }}/>
        </div>
        <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>{(100 - pct).toFixed(1)}% от общего</div>
      </div>
    </div>
  );
}

function ProgressLine({ kind, used, over, remain }) {
  const c = kind === "reaction" ? "var(--reaction)" : "var(--resolution)";
  return (
    <div>
      <div style={{ position: "relative", height: 14, background: "var(--bg-3)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(used, 100)}%`, height: "100%", background: c, boxShadow: `0 0 6px ${c}` }}/>
        {over && (
          <div style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0,
            background: "repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(255,59,88,0.3) 4px, rgba(255,59,88,0.3) 8px)" }}/>
        )}
        <div style={{ position: "absolute", top: -2, bottom: -2, left: "100%", width: 1, background: "rgba(255,255,255,0.6)" }}/>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 11.5 }}>
        <span style={{ color: "var(--text-3)" }}>Использовано <b className="mono" style={{ color: over ? "var(--crit)" : "var(--text)" }}>{used}%</b></span>
        <span style={{ color: over ? "var(--crit)" : "var(--text-2)" }} className="mono">
          {over ? `Просрочка ${opsFmt.fmtMin(Math.abs(remain))}` : `Осталось ${opsFmt.fmtMin(remain)}`}
        </span>
      </div>
    </div>
  );
}

function RelatedTickets({ queueId }) {
  const items = (window.OPSDATA.AT_RISK || []).filter((t) => t.queue_id === queueId).slice(0, 6);
  if (items.length === 0) return <div style={{ color: "var(--text-3)", fontSize: 12, padding: "10px 0" }}>Нет связанных нарушений</div>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {items.map((t) => (
        <div key={t.id} style={{ display: "grid", gridTemplateColumns: "100px 1fr auto", gap: 10, padding: "8px 10px", background: "var(--bg-2)", borderRadius: 6, fontSize: 12, alignItems: "center" }}>
          <span className="mono" style={{ color: "var(--accent)", fontWeight: 600 }}>{t.ticket_number}</span>
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.title}</span>
          <span className={`badge ${t.tier === "crit" ? "crit" : t.tier === "high" ? "high" : "warn"}`}>
            {t.r_over && t.s_over ? "Оба" : t.r_over ? "Реакц." : t.s_over ? "Решен." : "Риск"}
          </span>
        </div>
      ))}
    </div>
  );
}
