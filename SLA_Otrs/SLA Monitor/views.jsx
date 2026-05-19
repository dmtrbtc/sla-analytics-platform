// Three view modes for the SLA monitor.
const { useState: useStateV, useMemo: useMemoV } = React;

// =====================================================
// View 1: Queue matrix — pivot table of Реакция / Решение per queue
// =====================================================
function MatrixView({ queueMetrics, onPickQueue, search, group, sort, setSort }) {
  const filtered = useMemoV(() => {
    let arr = queueMetrics.filter((q) =>
      !search || q.name.toLowerCase().includes(search.toLowerCase())
    );
    if (group !== "all") {
      arr = arr.filter((q) => {
        if (group === "support") return q.name.startsWith("Support");
        if (group === "infra")   return q.name.startsWith("Infrastructure");
        if (group === "biz")     return ["Billing", "Finance", "HR", "Development", "Security"].includes(q.name);
        return true;
      });
    }
    // sort
    const dir = sort.dir === "desc" ? -1 : 1;
    const get = (q) => {
      switch (sort.key) {
        case "name": return q.name;
        case "priority": return q.priority;
        case "tickets": return q.tickets;
        case "r_in": return q.reaction.in_time;
        case "r_breached": return q.reaction.breached;
        case "r_pct": return q.reaction.pct_ok;
        case "r_avg": return q.reaction.avg_sec;
        case "q_in": return q.resolution.in_time;
        case "q_breached": return q.resolution.breached;
        case "q_pct": return q.resolution.pct_ok;
        case "q_avg": return q.resolution.avg_sec;
        default: return 0;
      }
    };
    arr = [...arr].sort((a, b) => {
      const va = get(a), vb = get(b);
      if (typeof va === "string") return va.localeCompare(vb) * dir;
      return (va - vb) * dir;
    });
    return arr;
  }, [queueMetrics, search, group, sort]);

  const totals = useMemoV(() => filtered.reduce((s, q) => ({
    tickets: s.tickets + q.tickets,
    r_in: s.r_in + q.reaction.in_time,
    r_breached: s.r_breached + q.reaction.breached,
    q_in: s.q_in + q.resolution.in_time,
    q_breached: s.q_breached + q.resolution.breached,
  }), { tickets: 0, r_in: 0, r_breached: 0, q_in: 0, q_breached: 0 }), [filtered]);

  const totalReactPct = +(((totals.r_in) / Math.max(totals.tickets, 1)) * 100).toFixed(1);
  const totalResolvePct = +(((totals.q_in) / Math.max(totals.tickets, 1)) * 100).toFixed(1);

  return (
    <div className="card">
      <div className="card-head">
        <div className="title">Матрица очередей · нарушения SLA</div>
        <div className="extra">
          <span className="legend">
            <span className="swatch" style={{ background: "#52c41a" }}/>≥95%
            <span className="swatch" style={{ background: "#faad14" }}/>90–95%
            <span className="swatch" style={{ background: "#ff4d4f" }}/>80–90%
            <span className="swatch" style={{ background: "#a8071a" }}/>&lt;80%
          </span>
        </div>
      </div>
      <div className="card-body tight" style={{ overflow: "auto" }}>
        <table className="t matrix">
          <thead>
            <tr>
              <th rowSpan="2" className="sortable" onClick={() => setSort((s) => ({ key: "name", dir: s.key === "name" && s.dir === "desc" ? "asc" : "desc" }))}>
                Очередь {sort.key === "name" && <span className="sort-arrow">{sort.dir === "desc" ? "↓" : "↑"}</span>}
              </th>
              <th rowSpan="2" className="num">Приоритет</th>
              <SortHead k="tickets" sort={sort} setSort={setSort} align="right">Тикетов</SortHead>
              <th colSpan="4" className="group reaction">⏱ Реакция</th>
              <th colSpan="4" className="group resolution">✓ Решение</th>
              <th rowSpan="2">Тренд 14д</th>
            </tr>
            <tr>
              <SortHead k="r_in" sort={sort} setSort={setSort} align="right" className="subhead divider-l">В срок</SortHead>
              <SortHead k="r_breached" sort={sort} setSort={setSort} align="right" className="subhead">Нарушено</SortHead>
              <SortHead k="r_pct" sort={sort} setSort={setSort} align="right" className="subhead">% SLA</SortHead>
              <SortHead k="r_avg" sort={sort} setSort={setSort} align="right" className="subhead">⌀ время</SortHead>
              <SortHead k="q_in" sort={sort} setSort={setSort} align="right" className="subhead divider-l">В срок</SortHead>
              <SortHead k="q_breached" sort={sort} setSort={setSort} align="right" className="subhead">Нарушено</SortHead>
              <SortHead k="q_pct" sort={sort} setSort={setSort} align="right" className="subhead">% SLA</SortHead>
              <SortHead k="q_avg" sort={sort} setSort={setSort} align="right" className="subhead">⌀ время</SortHead>
            </tr>
          </thead>
          <tbody>
            {filtered.map((q) => (
              <tr key={q.id} onClick={() => onPickQueue(q)}>
                <td>
                  <div className="queue-cell">
                    <span className="name">{q.name}</span>
                    <span className="meta">Цель: {fmt.fmtDuration(q.target_response)} / {fmt.fmtDuration(q.target_resolution)} · {q.calendar}</span>
                  </div>
                </td>
                <td className="num">
                  <span className={`tag ${q.priority >= 20 ? "red" : q.priority >= 10 ? "orange" : q.priority >= 5 ? "blue" : "gray"}`}>{q.priority}</span>
                </td>
                <td className="num"><strong>{fmt.fmtNum(q.tickets)}</strong></td>
                {/* Reaction */}
                <td className="num divider-l muted">{fmt.fmtNum(q.reaction.in_time)}</td>
                <td className="num"><CountPill value={q.reaction.breached} total={q.tickets}/></td>
                <td><PctCell pct={q.reaction.pct_ok}/></td>
                <td className="num muted">{fmt.fmtDuration(q.reaction.avg_sec)}</td>
                {/* Resolution */}
                <td className="num divider-l muted">{fmt.fmtNum(q.resolution.in_time)}</td>
                <td className="num"><CountPill value={q.resolution.breached} total={q.tickets}/></td>
                <td><PctCell pct={q.resolution.pct_ok}/></td>
                <td className="num muted">{fmt.fmtDuration(q.resolution.avg_sec)}</td>
                <td>
                  <div className="row" style={{ gap: 6 }}>
                    <Sparkline data={q.reaction.trend} color="#fa8c16" width={56} height={20}/>
                    <Sparkline data={q.resolution.trend} color="#722ed1" width={56} height={20}/>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ background: "var(--color-bg-spotlight)", fontWeight: 600 }}>
              <td style={{ padding: "10px 12px", borderTop: "1px solid var(--color-border-secondary)" }}>Итого ({filtered.length})</td>
              <td/>
              <td className="num" style={{ borderTop: "1px solid var(--color-border-secondary)" }}>{fmt.fmtNum(totals.tickets)}</td>
              <td className="num divider-l muted" style={{ borderTop: "1px solid var(--color-border-secondary)" }}>{fmt.fmtNum(totals.r_in)}</td>
              <td className="num" style={{ borderTop: "1px solid var(--color-border-secondary)" }}><CountPill value={totals.r_breached} total={totals.tickets}/></td>
              <td style={{ borderTop: "1px solid var(--color-border-secondary)" }}><PctCell pct={totalReactPct}/></td>
              <td style={{ borderTop: "1px solid var(--color-border-secondary)" }}/>
              <td className="num divider-l muted" style={{ borderTop: "1px solid var(--color-border-secondary)" }}>{fmt.fmtNum(totals.q_in)}</td>
              <td className="num" style={{ borderTop: "1px solid var(--color-border-secondary)" }}><CountPill value={totals.q_breached} total={totals.tickets}/></td>
              <td style={{ borderTop: "1px solid var(--color-border-secondary)" }}><PctCell pct={totalResolvePct}/></td>
              <td style={{ borderTop: "1px solid var(--color-border-secondary)" }}/>
              <td style={{ borderTop: "1px solid var(--color-border-secondary)" }}/>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
window.MatrixView = MatrixView;

// =====================================================
// View 2: Split — Реакция | Решение side by side, queues sorted by their own breach count
// =====================================================
function SplitView({ queueMetrics, onPickQueue, search }) {
  const filter = (arr) => arr.filter((q) => !search || q.name.toLowerCase().includes(search.toLowerCase()));

  const byReaction = useMemoV(() => [...filter(queueMetrics)].sort((a, b) => b.reaction.breached - a.reaction.breached), [queueMetrics, search]);
  const byResolution = useMemoV(() => [...filter(queueMetrics)].sort((a, b) => b.resolution.breached - a.resolution.breached), [queueMetrics, search]);

  const totalReact = byReaction.reduce((s, q) => s + q.reaction.breached, 0);
  const totalResolve = byResolution.reduce((s, q) => s + q.resolution.breached, 0);
  const maxR = Math.max(...byReaction.map((q) => q.reaction.breached), 1);
  const maxQ = Math.max(...byResolution.map((q) => q.resolution.breached), 1);

  const Col = ({ data, total, max, accent, label, sub, kind }) => (
    <div className="card">
      <div className={`split-col-head ${kind}`}>
        <span className="pip"/>
        <h3>{label}</h3>
        <span className="sub">{sub}</span>
      </div>
      <div className="card-body tight">
        <div style={{ padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--color-bg-spotlight)" }}>
          <span className="muted" style={{ fontSize: 12 }}>Очередь</span>
          <span className="row" style={{ gap: 28 }}>
            <span className="muted" style={{ fontSize: 12 }}>Нарушений</span>
            <span className="muted" style={{ fontSize: 12 }}>Доля</span>
            <span className="muted" style={{ fontSize: 12 }}>% SLA</span>
          </span>
        </div>
        {data.map((q) => {
          const breach = kind === "reaction" ? q.reaction.breached : q.resolution.breached;
          const pct = kind === "reaction" ? q.reaction.pct_ok : q.resolution.pct_ok;
          const share = (breach / max) * 100;
          const pctCls = fmt.pctClass(pct);
          return (
            <div className="queue-row" key={q.id} onClick={() => onPickQueue(q)} style={{ gridTemplateColumns: "1fr 70px 110px 80px" }}>
              <div className="col">
                <span className="name">{q.name}</span>
                <span className="meta">{fmt.fmtNum(q.tickets)} тикетов · цель {kind === "reaction" ? fmt.fmtDuration(q.target_response) : fmt.fmtDuration(q.target_resolution)}</span>
              </div>
              <div className="figure" style={{ textAlign: "right" }}>
                <CountPill value={breach} total={q.tickets}/>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ flex: 1, height: 8, background: "#f5f5f5", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{ width: `${share}%`, height: "100%", background: accent, borderRadius: 4 }}/>
                </div>
              </div>
              <div className={`figure ${pctCls === "ok" ? "" : "muted"}`} style={{ textAlign: "right", color: `var(--color-${pctCls === "ok" ? "success" : pctCls === "warn" ? "warning" : pctCls === "bad" ? "error" : "critical"})` }}>
                {pct}%
              </div>
            </div>
          );
        })}
        {data.length === 0 && <div className="empty">Нет нарушений</div>}
      </div>
      <div style={{ padding: "10px 16px", borderTop: "1px solid var(--color-border-secondary)", display: "flex", justifyContent: "space-between", background: "var(--color-bg-spotlight)", fontSize: 13 }}>
        <span className="muted">Всего по столбцу</span>
        <strong style={{ color: accent }}>{fmt.fmtNum(total)} нарушений</strong>
      </div>
    </div>
  );

  return (
    <div className="split">
      <Col data={byReaction} total={totalReact} max={maxR} accent="#fa8c16" label="⏱ Нарушения реакции" sub="по убыванию количества" kind="reaction"/>
      <Col data={byResolution} total={totalResolve} max={maxQ} accent="#722ed1" label="✓ Нарушения решения" sub="по убыванию количества" kind="resolution"/>
    </div>
  );
}
window.SplitView = SplitView;

// =====================================================
// View 3: Breach feed — list of breached tickets
// =====================================================
function FeedView({ tickets, onPickTicket, search, kindFilter, queueFilter, severityFilter, sort, setSort }) {
  const filtered = useMemoV(() => {
    let arr = tickets;
    if (kindFilter !== "all") {
      arr = arr.filter((t) => kindFilter === "both" ? t.kind === "both" : (t.kind === kindFilter || t.kind === "both"));
    }
    if (queueFilter !== "all") arr = arr.filter((t) => t.queue_id === queueFilter);
    if (severityFilter !== "all") arr = arr.filter((t) => t.severity === severityFilter);
    if (search) {
      const s = search.toLowerCase();
      arr = arr.filter((t) =>
        t.title.toLowerCase().includes(s) ||
        t.queue.toLowerCase().includes(s) ||
        t.ticket_number.toLowerCase().includes(s) ||
        (t.owner || "").toLowerCase().includes(s)
      );
    }
    const dir = sort.dir === "desc" ? -1 : 1;
    const get = (t) => {
      switch (sort.key) {
        case "ticket": return t.id;
        case "queue": return t.queue;
        case "owner": return t.owner;
        case "overdue": return Math.max(t.over_reaction_min, t.over_resolution_min / 60);
        case "severity": return t.severity === "crit" ? 3 : t.severity === "high" ? 2 : 1;
        case "kind": return t.kind;
        default: return 0;
      }
    };
    return [...arr].sort((a, b) => {
      const va = get(a), vb = get(b);
      if (typeof va === "string") return va.localeCompare(vb) * dir;
      return (va - vb) * dir;
    });
  }, [tickets, search, kindFilter, queueFilter, severityFilter, sort]);

  // Group by queue if user wants — for now show flat list with queue chip
  const sevLabel = { warn: "Предупр.", high: "Высокий", crit: "Критич." };
  const sevTag   = { warn: "gold", high: "orange", crit: "red" };
  const kindTag  = { reaction: { color: "orange", label: "Реакция" }, resolution: { color: "violet", label: "Решение" }, both: { color: "red", label: "Оба" } };

  return (
    <div className="card">
      <div className="card-head">
        <div className="title">Лента нарушений <span className="muted" style={{ fontWeight: 400, fontSize: 13, marginLeft: 8 }}>{fmt.fmtNum(filtered.length)} тикетов</span></div>
        <div className="extra">
          <span className="muted" style={{ fontSize: 12 }}>Сортировка:</span>
          <select className="select" value={`${sort.key}-${sort.dir}`} onChange={(e) => { const [k, d] = e.target.value.split("-"); setSort({ key: k, dir: d }); }}>
            <option value="overdue-desc">Просрочка (макс)</option>
            <option value="severity-desc">Severity (макс)</option>
            <option value="queue-asc">Очередь (A→Я)</option>
            <option value="ticket-desc">№ тикета (новые)</option>
          </select>
        </div>
      </div>
      <div className="card-body tight">
        <div className="feed-row" style={{ background: "var(--color-bg-spotlight)", cursor: "default", color: "var(--color-text-secondary)", fontSize: 12, fontWeight: 500 }}>
          <div>Тикет</div>
          <div>Тема</div>
          <div>Очередь</div>
          <div>Тип</div>
          <div>Просрочка</div>
          <div style={{ textAlign: "right" }}>Severity</div>
        </div>
        {filtered.slice(0, 60).map((t) => {
          const overReactCls = t.over_reaction_min > 180 ? "crit" : t.over_reaction_min > 30 ? "bad" : t.over_reaction_min > 0 ? "warn" : "";
          const overResCls   = t.over_resolution_min > 480 ? "crit" : t.over_resolution_min > 120 ? "bad" : t.over_resolution_min > 0 ? "warn" : "";
          return (
            <div className="feed-row" key={t.id} onClick={() => onPickTicket(t)}>
              <div className="tno">{t.ticket_number}</div>
              <div className="ttitle">
                <div>{t.title}</div>
                <div className="meta">{t.created_at} · {t.owner}</div>
              </div>
              <div><span className="q-chip"><span className="dot"/>{t.queue}</span></div>
              <div>
                <span className={`tag ${kindTag[t.kind].color} dot`}>{kindTag[t.kind].label}</span>
              </div>
              <div>
                {(t.kind === "reaction" || t.kind === "both") && t.over_reaction_min > 0 && (
                  <div className={`overdue ${overReactCls}`} style={{ fontSize: 12 }}>
                    Реакц.: +{fmt.fmtMinutes(t.over_reaction_min)}
                  </div>
                )}
                {(t.kind === "resolution" || t.kind === "both") && t.over_resolution_min > 0 && (
                  <div className={`overdue ${overResCls}`} style={{ fontSize: 12 }}>
                    Реш.: +{fmt.fmtMinutes(t.over_resolution_min)}
                  </div>
                )}
              </div>
              <div style={{ textAlign: "right" }}>
                <span className={`tag ${sevTag[t.severity]}`}>{sevLabel[t.severity]}</span>
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && <div className="empty">Нарушений не найдено по выбранным фильтрам</div>}
        {filtered.length > 60 && (
          <div style={{ padding: 12, textAlign: "center", color: "var(--color-text-tertiary)", fontSize: 12, borderTop: "1px solid var(--color-border-secondary)" }}>
            Показано 60 из {fmt.fmtNum(filtered.length)}. Уточните фильтры для просмотра остальных.
          </div>
        )}
      </div>
    </div>
  );
}
window.FeedView = FeedView;
