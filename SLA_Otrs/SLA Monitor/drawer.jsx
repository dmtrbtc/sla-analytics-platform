// Right-side drawer — queue or ticket drilldown
function Drawer({ open, kind, payload, tickets, onClose, onPickTicket }) {
  return (
    <React.Fragment>
      <div className={`scrim ${open ? "open" : ""}`} onClick={onClose}/>
      <aside className={`drawer ${open ? "open" : ""}`}>
        {kind === "queue" && payload && <QueuePanel queue={payload} tickets={tickets} onClose={onClose} onPickTicket={onPickTicket}/>}
        {kind === "ticket" && payload && <TicketPanel ticket={payload} onClose={onClose}/>}
      </aside>
    </React.Fragment>
  );
}

function QueuePanel({ queue, tickets, onClose, onPickTicket }) {
  const q = queue;
  const breachedTickets = tickets.filter((t) => t.queue_id === q.id);

  return (
    <React.Fragment>
      <div className="drawer-head">
        <div>
          <div className="title">{q.name}</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>Очередь · Приоритет {q.priority} · {q.calendar}</div>
        </div>
        <button className="close" onClick={onClose}><Icon name="close" size={16}/></button>
      </div>
      <div className="drawer-body">
        {/* SLA targets vs actual */}
        <div className="card" style={{ background: "var(--color-bg-spotlight)", border: "none", boxShadow: "none" }}>
          <div className="card-body" style={{ padding: 12 }}>
            <div className="dual-bar">
              <div>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong style={{ fontSize: 13 }}>⏱ Реакция</strong>
                  <span className="muted" style={{ fontSize: 12 }}>Цель: {fmt.fmtDuration(q.target_response)}</span>
                </div>
                <div className="row">
                  <span className="lab" style={{ width: 80, color: "var(--color-text-secondary)", fontSize: 12 }}>В срок</span>
                  <div className="bar reaction" style={{ flex: 1 }}><i style={{ width: `${q.reaction.pct_ok}%` }}/></div>
                  <span className="num" style={{ width: 56, textAlign: "right", fontWeight: 600 }}>{q.reaction.pct_ok}%</span>
                </div>
                <div className="row" style={{ marginTop: 4 }}>
                  <span className="lab" style={{ width: 80, color: "var(--color-text-secondary)", fontSize: 12 }}>Нарушено</span>
                  <div className="bar over" style={{ flex: 1 }}><i style={{ width: `${100 - q.reaction.pct_ok}%` }}/></div>
                  <span className="num" style={{ width: 56, textAlign: "right", color: "var(--color-error)" }}>{q.reaction.breached}</span>
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong style={{ fontSize: 13 }}>✓ Решение</strong>
                  <span className="muted" style={{ fontSize: 12 }}>Цель: {fmt.fmtDuration(q.target_resolution)}</span>
                </div>
                <div className="row">
                  <span className="lab" style={{ width: 80, color: "var(--color-text-secondary)", fontSize: 12 }}>В срок</span>
                  <div className="bar resolution" style={{ flex: 1 }}><i style={{ width: `${q.resolution.pct_ok}%` }}/></div>
                  <span className="num" style={{ width: 56, textAlign: "right", fontWeight: 600 }}>{q.resolution.pct_ok}%</span>
                </div>
                <div className="row" style={{ marginTop: 4 }}>
                  <span className="lab" style={{ width: 80, color: "var(--color-text-secondary)", fontSize: 12 }}>Нарушено</span>
                  <div className="bar over" style={{ flex: 1 }}><i style={{ width: `${100 - q.resolution.pct_ok}%` }}/></div>
                  <span className="num" style={{ width: 56, textAlign: "right", color: "var(--color-error)" }}>{q.resolution.breached}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Trend */}
        <div style={{ marginTop: 16 }}>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
            <strong style={{ fontSize: 13 }}>Тренд нарушений за 14 дней</strong>
            <span className="legend">
              <span className="swatch" style={{ background: "#fa8c16" }}/>Реакция
              <span className="swatch" style={{ background: "#722ed1" }}/>Решение
            </span>
          </div>
          <DualTrend a={q.reaction.trend} b={q.resolution.trend}/>
        </div>

        {/* Breached tickets list */}
        <div style={{ marginTop: 20 }}>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
            <strong style={{ fontSize: 13 }}>Тикеты с нарушением ({breachedTickets.length})</strong>
            <button className="btn sm">Все тикеты очереди →</button>
          </div>
          <div style={{ border: "1px solid var(--color-border-secondary)", borderRadius: 6, overflow: "hidden" }}>
            {breachedTickets.slice(0, 10).map((t) => (
              <div
                key={t.id}
                onClick={() => onPickTicket(t)}
                style={{
                  padding: "10px 12px",
                  borderBottom: "1px solid var(--color-border-secondary)",
                  cursor: "pointer",
                  display: "grid",
                  gridTemplateColumns: "100px 1fr auto",
                  gap: 10,
                  alignItems: "center",
                  fontSize: 13,
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--color-bg-spotlight)"}
                onMouseLeave={(e) => e.currentTarget.style.background = ""}
              >
                <span style={{ fontFamily: "SF Mono, Menlo, monospace", color: "var(--color-primary)", fontWeight: 600 }}>{t.ticket_number}</span>
                <div>
                  <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.title}</div>
                  <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                    {t.owner} · {t.created_at}
                  </div>
                </div>
                <div className="col" style={{ alignItems: "flex-end", gap: 2 }}>
                  <span className={`tag ${t.kind === "reaction" ? "orange" : t.kind === "resolution" ? "violet" : "red"}`}>
                    {t.kind === "reaction" ? "Реакция" : t.kind === "resolution" ? "Решение" : "Оба"}
                  </span>
                </div>
              </div>
            ))}
            {breachedTickets.length === 0 && <div className="empty" style={{ padding: 20 }}>Нет нарушений в этой очереди</div>}
          </div>
        </div>

        {/* Quick actions */}
        <div style={{ marginTop: 20, padding: 12, background: "var(--color-bg-spotlight)", borderRadius: 6 }}>
          <strong style={{ fontSize: 13 }}>Быстрые действия</strong>
          <div className="row" style={{ marginTop: 8, flexWrap: "wrap", gap: 6 }}>
            <button className="btn sm">Правило SLA</button>
            <button className="btn sm">Календарь</button>
            <button className="btn sm">Эскалации</button>
            <button className="btn sm">Экспорт CSV</button>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

function TicketPanel({ ticket, onClose }) {
  const t = ticket;
  const events = [
    { when: t.created_at, what: "Создан тикет", who: "system" },
    { when: t.created_at, what: `Назначен на очередь ${t.queue}`, who: "auto-routing" },
    { when: t.created_at, what: t.kind === "resolution" ? "Первый ответ дан" : "Просрочена реакция", who: t.owner },
    ...(t.kind !== "reaction" ? [{ when: t.created_at, what: "Просрочено решение SLA", who: "sla-engine" }] : []),
  ];
  return (
    <React.Fragment>
      <div className="drawer-head">
        <div>
          <div className="row" style={{ gap: 8 }}>
            <span style={{ fontFamily: "SF Mono, Menlo, monospace", color: "var(--color-primary)" }}>{t.ticket_number}</span>
            <span className={`tag ${t.kind === "reaction" ? "orange" : t.kind === "resolution" ? "violet" : "red"}`}>
              {t.kind === "reaction" ? "Нарушение реакции" : t.kind === "resolution" ? "Нарушение решения" : "Нарушение реакции и решения"}
            </span>
          </div>
          <div className="title" style={{ marginTop: 4, fontSize: 14 }}>{t.title}</div>
        </div>
        <button className="close" onClick={onClose}><Icon name="close" size={16}/></button>
      </div>
      <div className="drawer-body">
        <dl className="dl">
          <dt>Очередь</dt><dd><span className="q-chip"><span className="dot"/>{t.queue}</span></dd>
          <dt>Владелец</dt><dd>{t.owner}</dd>
          <dt>Приоритет</dt><dd><span className={`tag ${t.priority === "Высокий" ? "red" : t.priority === "Средний" ? "orange" : "gray"}`}>{t.priority}</span></dd>
          <dt>Создан</dt><dd>{t.created_at}</dd>
          <dt>Открыт</dt><dd>{fmt.fmtMinutes(t.opened_min_ago)}</dd>
        </dl>

        <div className="divider-h"/>

        <strong style={{ fontSize: 13 }}>SLA против цели</strong>
        <div className="dual-bar" style={{ marginTop: 8 }}>
          <div className="row" style={{ marginBottom: 4 }}>
            <span className="lab" style={{ width: 100, color: "var(--color-text-secondary)" }}>Реакция</span>
            <div className="bar reaction" style={{ flex: 1, position: "relative" }}>
              <i style={{ width: `${Math.min(t.sla_response_used_pct, 100)}%` }}/>
              {t.sla_response_used_pct > 100 && (
                <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "100%", background: "repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(255,77,79,0.25) 4px, rgba(255,77,79,0.25) 8px)", borderRadius: 4 }}/>
              )}
            </div>
            <span className="num" style={{ width: 72, textAlign: "right", color: t.sla_response_used_pct > 100 ? "var(--color-error)" : "var(--color-text)" }}>{t.sla_response_used_pct}%</span>
          </div>
          <div className="muted" style={{ fontSize: 12, marginLeft: 100, marginBottom: 8 }}>
            Цель: {fmt.fmtDuration(t.target_response_sec)}
            {t.over_reaction_min > 0 && <span style={{ color: "var(--color-error)", marginLeft: 8 }}>· просрочено на {fmt.fmtMinutes(t.over_reaction_min)}</span>}
          </div>

          <div className="row" style={{ marginBottom: 4 }}>
            <span className="lab" style={{ width: 100, color: "var(--color-text-secondary)" }}>Решение</span>
            <div className="bar resolution" style={{ flex: 1, position: "relative" }}>
              <i style={{ width: `${Math.min(t.sla_resolution_used_pct, 100)}%` }}/>
              {t.sla_resolution_used_pct > 100 && (
                <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "100%", background: "repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(255,77,79,0.25) 4px, rgba(255,77,79,0.25) 8px)", borderRadius: 4 }}/>
              )}
            </div>
            <span className="num" style={{ width: 72, textAlign: "right", color: t.sla_resolution_used_pct > 100 ? "var(--color-error)" : "var(--color-text)" }}>{t.sla_resolution_used_pct}%</span>
          </div>
          <div className="muted" style={{ fontSize: 12, marginLeft: 100 }}>
            Цель: {fmt.fmtDuration(t.target_resolution_sec)}
            {t.over_resolution_min > 0 && <span style={{ color: "var(--color-error)", marginLeft: 8 }}>· просрочено на {fmt.fmtMinutes(t.over_resolution_min)}</span>}
          </div>
        </div>

        <div className="divider-h"/>

        <strong style={{ fontSize: 13 }}>Хронология</strong>
        <div className="timeline" style={{ marginTop: 8 }}>
          {events.map((e, i) => (
            <div className="t-row" key={i}>
              <div className="when">{e.when}</div>
              <div className="what">{e.what} <span className="who">· {e.who}</span></div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
          <button className="btn primary">Открыть тикет в OTRS</button>
          <button className="btn">Переназначить</button>
          <button className="btn">Эскалация</button>
        </div>
      </div>
    </React.Fragment>
  );
}

function DualTrend({ a, b }) {
  const w = 520, h = 90, pad = 8;
  const max = Math.max(...a, ...b, 1);
  const stepX = (w - pad * 2) / (a.length - 1);
  const toPts = (arr) => arr.map((v, i) => `${pad + i * stepX},${h - pad - (v / max) * (h - pad * 2)}`).join(" ");
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ background: "var(--color-bg-spotlight)", borderRadius: 6, border: "1px solid var(--color-border-secondary)" }}>
      {/* gridlines */}
      {[0.25, 0.5, 0.75].map((y) => (
        <line key={y} x1={pad} y1={h - pad - y * (h - pad * 2)} x2={w - pad} y2={h - pad - y * (h - pad * 2)} stroke="#eee"/>
      ))}
      <polyline points={toPts(a)} fill="none" stroke="#fa8c16" strokeWidth="2"/>
      <polyline points={toPts(b)} fill="none" stroke="#722ed1" strokeWidth="2"/>
      {a.map((v, i) => (
        <circle key={"a" + i} cx={pad + i * stepX} cy={h - pad - (v / max) * (h - pad * 2)} r="2.5" fill="#fa8c16"/>
      ))}
      {b.map((v, i) => (
        <circle key={"b" + i} cx={pad + i * stepX} cy={h - pad - (v / max) * (h - pad * 2)} r="2.5" fill="#722ed1"/>
      ))}
    </svg>
  );
}

window.Drawer = Drawer;
