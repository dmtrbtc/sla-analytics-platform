// Mock data — realistic OTRS-style SLA breach metrics, RU locale

window.MOCK = (() => {
  // Deterministic RNG so layout is stable
  let _seed = 42;
  const rand = () => {
    _seed = (_seed * 9301 + 49297) % 233280;
    return _seed / 233280;
  };
  const pick = (arr) => arr[Math.floor(rand() * arr.length)];
  const int = (min, max) => Math.floor(rand() * (max - min + 1)) + min;

  // ---- Queue rules taken from your SLA Config shape ----
  // Each queue has its own response/resolution target (seconds), priority, calendar.
  const QUEUES = [
    { id: "q-l1", name: "Support::L1",            priority: 5,  target_response: 15 * 60,      target_resolution: 4 * 3600,   calendar: "RU 9-18" },
    { id: "q-l2", name: "Support::L2",            priority: 10, target_response: 30 * 60,      target_resolution: 8 * 3600,   calendar: "RU 9-18" },
    { id: "q-l3", name: "Support::L3",            priority: 20, target_response: 60 * 60,      target_resolution: 24 * 3600,  calendar: "RU 9-18" },
    { id: "q-vip", name: "Support::VIP",          priority: 20, target_response: 5 * 60,       target_resolution: 2 * 3600,   calendar: "24x7" },
    { id: "q-bill", name: "Billing",              priority: 10, target_response: 60 * 60,      target_resolution: 12 * 3600,  calendar: "RU 9-18" },
    { id: "q-net", name: "Infrastructure::Network", priority: 20, target_response: 10 * 60,    target_resolution: 4 * 3600,   calendar: "24x7" },
    { id: "q-srv", name: "Infrastructure::Servers", priority: 20, target_response: 15 * 60,    target_resolution: 6 * 3600,   calendar: "24x7" },
    { id: "q-db",  name: "Infrastructure::DB",    priority: 20, target_response: 10 * 60,      target_resolution: 4 * 3600,   calendar: "24x7" },
    { id: "q-sec", name: "Security",              priority: 20, target_response: 10 * 60,      target_resolution: 6 * 3600,   calendar: "24x7" },
    { id: "q-dev", name: "Development",           priority: 5,  target_response: 4 * 3600,     target_resolution: 5 * 24 * 3600, calendar: "RU 9-18" },
    { id: "q-hr",  name: "HR",                    priority: 0,  target_response: 8 * 3600,     target_resolution: 3 * 24 * 3600, calendar: "RU 9-18" },
    { id: "q-fin", name: "Finance",               priority: 5,  target_response: 4 * 3600,     target_resolution: 2 * 24 * 3600, calendar: "RU 9-18" },
  ];

  // Generate per-queue metrics for chosen period
  const buildQueueMetrics = (queue, days = 30) => {
    // total volume scales with queue type
    const baseVolume = queue.name.includes("L1") ? 480 :
                       queue.name.includes("L2") ? 220 :
                       queue.name.includes("L3") ? 110 :
                       queue.name.includes("VIP") ? 38 :
                       queue.name === "Billing" ? 156 :
                       queue.name.includes("Network") ? 92 :
                       queue.name.includes("Servers") ? 84 :
                       queue.name.includes("DB") ? 41 :
                       queue.name === "Security" ? 27 :
                       queue.name === "Development" ? 68 :
                       queue.name === "HR" ? 51 :
                       queue.name === "Finance" ? 35 : 60;
    const tickets = Math.round(baseVolume * (days / 30));

    // Different breach profiles per queue (hand-tuned for visual variety)
    const profile = (() => {
      if (queue.name === "Support::L1")            return { r: 0.09, q: 0.06 };   // ok / ok
      if (queue.name === "Support::L2")            return { r: 0.14, q: 0.18 };   // warn
      if (queue.name === "Support::L3")            return { r: 0.22, q: 0.31 };   // bad
      if (queue.name === "Support::VIP")           return { r: 0.05, q: 0.03 };   // good
      if (queue.name === "Billing")                return { r: 0.06, q: 0.21 };   // resolution-heavy
      if (queue.name.includes("Network"))          return { r: 0.18, q: 0.12 };
      if (queue.name.includes("Servers"))          return { r: 0.28, q: 0.34 };   // critical
      if (queue.name.includes("DB"))               return { r: 0.41, q: 0.29 };   // reaction-heavy
      if (queue.name === "Security")               return { r: 0.07, q: 0.10 };
      if (queue.name === "Development")            return { r: 0.04, q: 0.27 };
      if (queue.name === "HR")                     return { r: 0.02, q: 0.05 };
      if (queue.name === "Finance")                return { r: 0.08, q: 0.14 };
      return { r: 0.1, q: 0.1 };
    })();

    const reactionBreaches   = Math.round(tickets * profile.r);
    const resolutionBreaches = Math.round(tickets * profile.q);
    const reactionInTime     = tickets - reactionBreaches;
    const resolutionInTime   = tickets - resolutionBreaches;
    const reactionPct        = +((reactionInTime / tickets) * 100).toFixed(1);
    const resolutionPct      = +((resolutionInTime / tickets) * 100).toFixed(1);

    // Mean times (in seconds) — for table secondary info
    const avgReactionSec    = Math.round(queue.target_response * (0.5 + profile.r * 4));
    const avgResolutionSec  = Math.round(queue.target_resolution * (0.6 + profile.q * 3));

    // Trend sparkline: 14 points for last N days
    const points = 14;
    const trendReact = Array.from({ length: points }, (_, i) => {
      const base = reactionBreaches / points;
      // last few bars darker on degrading queues
      const trend = (i / points) * (profile.r > 0.2 ? 3 : profile.r > 0.1 ? 1 : -0.5);
      return Math.max(0, Math.round(base + trend + (rand() - 0.5) * 2));
    });
    const trendResolve = Array.from({ length: points }, (_, i) => {
      const base = resolutionBreaches / points;
      const trend = (i / points) * (profile.q > 0.2 ? 3 : profile.q > 0.1 ? 1 : -0.5);
      return Math.max(0, Math.round(base + trend + (rand() - 0.5) * 2));
    });

    return {
      ...queue,
      tickets,
      reaction: {
        in_time: reactionInTime,
        breached: reactionBreaches,
        pct_ok: reactionPct,
        avg_sec: avgReactionSec,
        trend: trendReact,
      },
      resolution: {
        in_time: resolutionInTime,
        breached: resolutionBreaches,
        pct_ok: resolutionPct,
        avg_sec: avgResolutionSec,
        trend: trendResolve,
      },
    };
  };

  // ---- Individual breached tickets (for drilldown + feed view) ----
  const SUBJECTS = [
    "Не открывается личный кабинет Confluence",
    "VPN отваливается каждые 5 минут",
    "Принтер HR-3 печатает с задержкой",
    "Запрос на восстановление доступа к 1С",
    "Падает БД prod-pg-01: connections exhausted",
    "Ошибка 502 на api.internal.lan",
    "Перерасчёт зарплаты за апрель",
    "Заказать MacBook Pro 16 для нового сотрудника",
    "Подозрение на фишинговую рассылку",
    "Не приходят push-уведомления в мобильном приложении",
    "Запрос отпуска не уходит руководителю",
    "Сертификат wildcard истекает через 7 дней",
    "Невозможно подключиться к Wi-Fi в офисе СПб",
    "Replication lag > 30s на db-replica-02",
    "Не приходят счета на согласование",
    "Сбой синхронизации Active Directory",
    "DNS resolution медленный для *.corp.ru",
    "Не отображается отчёт по продажам за квартал",
    "Замена SSD на ws-1042 (RAID failure)",
    "Просьба настроить SSO для нового сервиса",
  ];
  const OWNERS = ["a.ivanov", "m.petrova", "d.kuznetsov", "e.smirnova", "i.popov", "k.vasileva", "n.fedorov", "s.morozov", "—"];
  const PRIORITY = ["Низкий", "Средний", "Высокий", "Критичный"];

  const fmtTime = (offsetMin) => {
    const d = new Date(Date.now() - offsetMin * 60 * 1000);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const breachKind = () => {
    const r = rand();
    if (r < 0.45) return "reaction";
    if (r < 0.85) return "resolution";
    return "both";
  };

  // Build a pool of breached tickets across queues
  const TICKETS = [];
  let tn = 2024100000;
  for (const q of QUEUES) {
    const m = buildQueueMetrics(q, 30);
    const count = Math.max(m.reaction.breached, m.resolution.breached);
    const generate = Math.min(count, 14); // cap for UI
    for (let i = 0; i < generate; i++) {
      const kind = i < m.reaction.breached && i < m.resolution.breached
        ? breachKind()
        : (i < m.reaction.breached ? (rand() < 0.6 ? "reaction" : "both") : "resolution");

      // Severity is "how far past SLA"
      const overReact = kind === "resolution" ? 0 : Math.round(q.target_response / 60 * (0.2 + rand() * 4)); // in minutes
      const overResolve = kind === "reaction" ? 0 : Math.round(q.target_resolution / 60 * (0.1 + rand() * 1.8));
      const overMax = Math.max(overReact, overResolve / 60); // normalize roughly to "hours equiv" for severity
      const severity = overMax > 180 ? "crit" : overMax > 60 ? "high" : "warn";

      TICKETS.push({
        id: ++tn,
        ticket_number: `T-${tn}`,
        title: pick(SUBJECTS),
        queue_id: q.id,
        queue: q.name,
        priority: q.priority >= 20 ? "Высокий" : q.priority >= 10 ? "Средний" : "Низкий",
        owner: pick(OWNERS),
        kind, // 'reaction' | 'resolution' | 'both'
        over_reaction_min: overReact,
        over_resolution_min: overResolve,
        target_response_sec: q.target_response,
        target_resolution_sec: q.target_resolution,
        severity,
        created_at: fmtTime(int(60, 3 * 24 * 60)),
        opened_min_ago: int(30, 4320),
        sla_response_used_pct: kind === "resolution" ? int(60, 95) : 100 + int(20, 400),
        sla_resolution_used_pct: kind === "reaction" ? int(70, 99) : 100 + int(10, 220),
      });
    }
  }

  // Pre-aggregate per-queue metrics for default 30d period
  const QUEUE_METRICS = QUEUES.map((q) => buildQueueMetrics(q, 30));

  // ---- Global KPIs ----
  const totalTickets = QUEUE_METRICS.reduce((s, q) => s + q.tickets, 0);
  const totalReactBreach = QUEUE_METRICS.reduce((s, q) => s + q.reaction.breached, 0);
  const totalResolveBreach = QUEUE_METRICS.reduce((s, q) => s + q.resolution.breached, 0);
  const overallReactPct = +(((totalTickets - totalReactBreach) / totalTickets) * 100).toFixed(1);
  const overallResolvePct = +(((totalTickets - totalResolveBreach) / totalTickets) * 100).toFixed(1);
  const queuesAtRisk = QUEUE_METRICS.filter((q) => q.reaction.pct_ok < 90 || q.resolution.pct_ok < 90).length;

  const KPIS = {
    total_tickets: totalTickets,
    total_reaction_breach: totalReactBreach,
    total_resolution_breach: totalResolveBreach,
    overall_reaction_pct: overallReactPct,
    overall_resolution_pct: overallResolvePct,
    queues_at_risk: queuesAtRisk,
    most_breached_queue: [...QUEUE_METRICS].sort((a, b) =>
      (b.reaction.breached + b.resolution.breached) - (a.reaction.breached + a.resolution.breached)
    )[0].name,
  };

  return { QUEUES, QUEUE_METRICS, TICKETS, KPIS };
})();
