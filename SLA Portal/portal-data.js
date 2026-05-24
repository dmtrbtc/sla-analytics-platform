// Extended mock data for the SLA Operations Center
window.OPSDATA = (() => {
  let _seed = 71;
  const rand = () => { _seed = (_seed * 9301 + 49297) % 233280; return _seed / 233280; };
  const pick = (arr) => arr[Math.floor(rand() * arr.length)];
  const int = (mn, mx) => Math.floor(rand() * (mx - mn + 1)) + mn;

  // ---- Queues ----
  const QUEUES = [
    { id:"q-vip", name:"Support::VIP", priority:20, target_response:5*60,    target_resolution:2*3600,  calendar:"24×7",   agents_on:4 },
    { id:"q-db",  name:"Infrastructure::DB", priority:20, target_response:10*60,  target_resolution:4*3600,  calendar:"24×7",   agents_on:3 },
    { id:"q-net", name:"Infrastructure::Network", priority:20, target_response:10*60,  target_resolution:4*3600,  calendar:"24×7",   agents_on:5 },
    { id:"q-srv", name:"Infrastructure::Servers", priority:20, target_response:15*60,  target_resolution:6*3600,  calendar:"24×7",   agents_on:5 },
    { id:"q-sec", name:"Security",              priority:20, target_response:10*60,  target_resolution:6*3600,  calendar:"24×7",   agents_on:3 },
    { id:"q-l1",  name:"Support::L1",           priority:5,  target_response:15*60,  target_resolution:4*3600,  calendar:"RU 9-18", agents_on:12 },
    { id:"q-l2",  name:"Support::L2",           priority:10, target_response:30*60,  target_resolution:8*3600,  calendar:"RU 9-18", agents_on:7 },
    { id:"q-l3",  name:"Support::L3",           priority:20, target_response:60*60,  target_resolution:24*3600, calendar:"RU 9-18", agents_on:4 },
    { id:"q-bill",name:"Billing",               priority:10, target_response:60*60,  target_resolution:12*3600, calendar:"RU 9-18", agents_on:3 },
    { id:"q-dev", name:"Development",           priority:5,  target_response:4*3600, target_resolution:5*24*3600, calendar:"RU 9-18", agents_on:8 },
    { id:"q-hr",  name:"HR",                    priority:0,  target_response:8*3600, target_resolution:3*24*3600, calendar:"RU 9-18", agents_on:2 },
    { id:"q-fin", name:"Finance",               priority:5,  target_response:4*3600, target_resolution:2*24*3600, calendar:"RU 9-18", agents_on:3 },
  ];

  const profile = (name) => {
    if (name === "Support::L1")            return { r:0.07, q:0.05, vol:480, wait:6 };
    if (name === "Support::L2")            return { r:0.14, q:0.18, vol:220, wait:14 };
    if (name === "Support::L3")            return { r:0.22, q:0.31, vol:110, wait:38 };
    if (name === "Support::VIP")           return { r:0.05, q:0.03, vol:38,  wait:2 };
    if (name === "Billing")                return { r:0.06, q:0.21, vol:156, wait:24 };
    if (name === "Infrastructure::Network")return { r:0.18, q:0.12, vol:92,  wait:11 };
    if (name === "Infrastructure::Servers")return { r:0.28, q:0.34, vol:84,  wait:42 };
    if (name === "Infrastructure::DB")     return { r:0.41, q:0.29, vol:41,  wait:18 };
    if (name === "Security")               return { r:0.07, q:0.10, vol:27,  wait:8 };
    if (name === "Development")            return { r:0.04, q:0.27, vol:68,  wait:96 };
    if (name === "HR")                     return { r:0.02, q:0.05, vol:51,  wait:540 };
    if (name === "Finance")                return { r:0.08, q:0.14, vol:35,  wait:120 };
    return { r:0.1, q:0.1, vol:60, wait:15 };
  };

  const QUEUE_METRICS = QUEUES.map((q) => {
    const p = profile(q.name);
    const tickets = p.vol;
    const reactBr = Math.round(tickets * p.r);
    const resBr   = Math.round(tickets * p.q);
    const reactPct = +(((tickets - reactBr) / tickets) * 100).toFixed(1);
    const resPct   = +(((tickets - resBr) / tickets) * 100).toFixed(1);
    // health score: weighted of two metrics + overload penalty
    const health = Math.round(0.55 * reactPct + 0.45 * resPct);
    const atRisk = Math.round(tickets * Math.max(0, (p.r + p.q) / 3));
    const open   = Math.round(tickets * (0.15 + p.r * 1.2));

    // Severity tier
    const tier = health < 75 ? "crit" : health < 85 ? "high" : health < 92 ? "warn" : "ok";

    const points = 16;
    const trendR = Array.from({length:points}, (_,i)=>{
      const b = reactBr/points;
      const drift = (i/points) * (p.r > 0.25 ? 4 : p.r > 0.12 ? 1 : -0.5);
      return Math.max(0, Math.round(b + drift + (rand()-0.5)*1.5));
    });
    const trendS = Array.from({length:points}, (_,i)=>{
      const b = resBr/points;
      const drift = (i/points) * (p.q > 0.25 ? 4 : p.q > 0.12 ? 1 : -0.5);
      return Math.max(0, Math.round(b + drift + (rand()-0.5)*1.5));
    });

    return {
      ...q,
      tickets, open, at_risk: atRisk,
      avg_wait_min: p.wait,
      reaction:   { in_time: tickets - reactBr, breached: reactBr, pct_ok: reactPct, avg_sec: Math.round(q.target_response * (0.5 + p.r * 4)), trend: trendR },
      resolution: { in_time: tickets - resBr,   breached: resBr,   pct_ok: resPct,   avg_sec: Math.round(q.target_resolution * (0.6 + p.q * 3)), trend: trendS },
      health, tier,
    };
  });

  // ---- Tickets at risk (live) ----
  const SUBJECTS = [
    "Падает БД prod-pg-01: connections exhausted",
    "Repl. lag > 60s на db-replica-02",
    "VPN отваливается каждые 5 минут",
    "Сертификат wildcard истекает через 7 дней",
    "Не приходят счета на согласование",
    "Ошибка 502 на api.internal.lan",
    "Сбой синхронизации Active Directory",
    "DNS resolution медленный для *.corp.ru",
    "Подозрение на фишинговую рассылку",
    "Невозможно подключиться к Wi-Fi в офисе СПб",
    "Запрос на восстановление доступа к 1С",
    "Замена SSD на ws-1042 (RAID failure)",
    "Перерасчёт зарплаты за апрель",
    "Не открывается личный кабинет Confluence",
    "Просьба настроить SSO для нового сервиса",
    "Принтер HR-3 не подключается",
    "Аномальный трафик с подсети 10.20.0.0/16",
    "Падение worker-узла k8s-prod-node-3",
    "Замедление работы CRM (>5s на запрос)",
    "Заблокирована учётная запись a.fedorov",
  ];
  const OWNERS = ["a.ivanov","m.petrova","d.kuznetsov","e.smirnova","i.popov","k.vasileva","n.fedorov","s.morozov","—"];

  const fmtTime = (offsetMin) => {
    const d = new Date(Date.now() - offsetMin*60*1000);
    const p = (n) => String(n).padStart(2,"0");
    return `${p(d.getDate())}.${p(d.getMonth()+1)} ${p(d.getHours())}:${p(d.getMinutes())}`;
  };

  const AT_RISK = [];
  let tn = 2024100000;
  for (let i=0;i<32;i++){
    const q = pick(QUEUE_METRICS);
    const reactUsed = 50 + int(20, 95);   // % of reaction SLA window consumed (>100 means already breached)
    const resUsed   = 40 + int(10, 75);
    const breached  = reactUsed > 100 || rand() < 0.35;
    const reactOver = reactUsed > 100;
    const resOver   = resUsed > 100;
    // remaining minutes until next breach
    const r_remain  = reactOver ? -int(2, 240) : Math.round((1 - reactUsed/100) * (q.target_response/60));
    const s_remain  = resOver   ? -int(5, 480) : Math.round((1 - resUsed/100)   * (q.target_resolution/60));
    const minRemain = Math.min(reactOver ? Infinity : r_remain, resOver ? Infinity : s_remain);
    const tier = breached ? "crit" : minRemain < 10 ? "crit" : minRemain < 30 ? "high" : minRemain < 90 ? "warn" : "ok";

    AT_RISK.push({
      id: ++tn,
      ticket_number: `T-${tn}`,
      title: pick(SUBJECTS),
      queue: q.name,
      queue_id: q.id,
      owner: pick(OWNERS),
      priority: q.priority >= 20 ? "Высокий" : q.priority >= 10 ? "Средний" : "Низкий",
      created_at: fmtTime(int(30, 4320)),
      r_used: reactUsed, s_used: resUsed,
      r_over: reactOver, s_over: resOver,
      r_remain_min: r_remain, s_remain_min: s_remain,
      breach_eta_min: minRemain,
      tier,
      target_response: q.target_response,
      target_resolution: q.target_resolution,
    });
  }
  AT_RISK.sort((a,b) => (a.breach_eta_min ?? 9999) - (b.breach_eta_min ?? 9999));

  // ---- Active Incidents ----
  const INCIDENTS = [
    {
      id: "INC-2057",
      severity: "critical",
      title: "Деградация Infrastructure::DB · реакция >2× от нормы",
      affected_queues: ["Infrastructure::DB","Infrastructure::Servers"],
      started_min_ago: 26,
      breach_count: 14,
      coordinator: "d.kuznetsov",
    },
    {
      id: "INC-2056",
      severity: "high",
      title: "Очередь Support::L3 — превышение нагрузки на 180%",
      affected_queues: ["Support::L3"],
      started_min_ago: 102,
      breach_count: 7,
      coordinator: "m.petrova",
    },
  ];

  // ---- Event Stream ----
  const EVENTS = [
    { ts: "2 сек",  type:"breach",     kind:"crit",   title:"SLA реакции пробит",          queue:"Infrastructure::DB",     ticket:"T-2024100214", who:"sla-engine" },
    { ts: "18 сек", type:"escalation", kind:"warn",   title:"Эскалация → L3",              queue:"Support::L2",            ticket:"T-2024100198", who:"auto-escalator" },
    { ts: "42 сек", type:"reassign",   kind:"info",   title:"Переназначение тикета",       queue:"Billing",                 ticket:"T-2024100179", who:"k.vasileva" },
    { ts: "1 мин",  type:"breach",     kind:"react",  title:"Нарушение реакции",           queue:"Infrastructure::Servers", ticket:"T-2024100211", who:"sla-engine" },
    { ts: "2 мин",  type:"overload",   kind:"warn",   title:"Перегрузка очереди (180%)",   queue:"Support::L3",             ticket:"—",            who:"queue-monitor" },
    { ts: "3 мин",  type:"breach",     kind:"resolve",title:"Нарушение решения",           queue:"Development",             ticket:"T-2024100207", who:"sla-engine" },
    { ts: "5 мин",  type:"incident",   kind:"crit",   title:"Открыт инцидент INC-2057",    queue:"Infrastructure::DB",     ticket:"—",            who:"d.kuznetsov" },
    { ts: "8 мин",  type:"breach",     kind:"react",  title:"Нарушение реакции",           queue:"Infrastructure::DB",      ticket:"T-2024100195", who:"sla-engine" },
    { ts: "11 мин", type:"recovery",   kind:"info",   title:"Восстановлено: время отклика", queue:"Support::L1",            ticket:"—",            who:"sla-engine" },
    { ts: "14 мин", type:"reassign",   kind:"info",   title:"Переназначение тикета",       queue:"Support::L2",            ticket:"T-2024100188", who:"n.fedorov" },
    { ts: "17 мин", type:"breach",     kind:"resolve",title:"Нарушение решения",           queue:"Billing",                 ticket:"T-2024100173", who:"sla-engine" },
    { ts: "21 мин", type:"escalation", kind:"warn",   title:"Эскалация → VIP",             queue:"Support::VIP",            ticket:"T-2024100170", who:"auto-escalator" },
    { ts: "26 мин", type:"incident",   kind:"crit",   title:"Открыт инцидент INC-2056",    queue:"Support::L3",             ticket:"—",            who:"m.petrova" },
  ];

  // ---- Agents (workload matrix) ----
  const AGENTS = [
    { name:"a.ivanov",     initials:"АИ", open:14, handled:138, sla_pct:82, avg_min:42, over:false, top:false },
    { name:"m.petrova",    initials:"МП", open:23, handled:104, sla_pct:71, avg_min:68, over:true,  top:false },
    { name:"d.kuznetsov",  initials:"ДК", open:18, handled:122, sla_pct:78, avg_min:55, over:true,  top:false },
    { name:"e.smirnova",   initials:"ЕС", open:9,  handled:156, sla_pct:96, avg_min:24, over:false, top:true  },
    { name:"i.popov",      initials:"ИП", open:11, handled:91,  sla_pct:88, avg_min:33, over:false, top:false },
    { name:"k.vasileva",   initials:"КВ", open:7,  handled:142, sla_pct:97, avg_min:21, over:false, top:true  },
    { name:"n.fedorov",    initials:"НФ", open:16, handled:115, sla_pct:84, avg_min:39, over:false, top:false },
    { name:"s.morozov",    initials:"СМ", open:21, handled:88,  sla_pct:73, avg_min:62, over:true,  top:false },
  ];

  // ---- Bottlenecks ----
  const BOTTLENECKS = [...QUEUE_METRICS]
    .map((q) => ({
      name: q.name, queue_id: q.id,
      avg_wait_min: q.avg_wait_min,
      reassignments: Math.round(q.tickets * (q.tier === "crit" ? 0.4 : q.tier === "high" ? 0.2 : 0.08)),
      stuck: Math.round(q.at_risk * 0.6),
      kind: q.reaction.breached > q.resolution.breached ? "reaction" : "resolution",
    }))
    .sort((a, b) => b.avg_wait_min - a.avg_wait_min)
    .slice(0, 7);

  // ---- KPI for global status strip ----
  const totalTickets = QUEUE_METRICS.reduce((s,q)=>s+q.tickets,0);
  const totalReact = QUEUE_METRICS.reduce((s,q)=>s+q.reaction.breached,0);
  const totalResolve = QUEUE_METRICS.reduce((s,q)=>s+q.resolution.breached,0);
  const totalOpen = QUEUE_METRICS.reduce((s,q)=>s+q.open,0);
  const totalAtRisk = QUEUE_METRICS.reduce((s,q)=>s+q.at_risk,0);
  const reactPct  = +(((totalTickets-totalReact)/totalTickets)*100).toFixed(1);
  const resPct    = +(((totalTickets-totalResolve)/totalTickets)*100).toFixed(1);
  const health    = Math.round(0.5 * reactPct + 0.5 * resPct);
  const criticalQueues = QUEUE_METRICS.filter(q => q.tier === "crit").length;
  const avgResp = Math.round(QUEUE_METRICS.reduce((s,q)=>s+q.reaction.avg_sec,0) / QUEUE_METRICS.length / 60);
  const avgResv = Math.round(QUEUE_METRICS.reduce((s,q)=>s+q.resolution.avg_sec,0) / QUEUE_METRICS.length / 3600);

  const KPI = {
    health,
    active_breaches: totalReact + totalResolve,
    critical_queues: criticalQueues,
    avg_response_min: avgResp,
    avg_resolution_h: avgResv,
    tickets_at_risk: totalAtRisk,
    unassigned: 11,
    active_incidents: INCIDENTS.length,
    reaction_pct: reactPct, resolution_pct: resPct,
    total_tickets: totalTickets,
    total_reaction_breach: totalReact,
    total_resolution_breach: totalResolve,
    total_open: totalOpen,
  };

  // ---- Sparkline data for KPI tiles (24 ticks for last 24h) ----
  const buildSpark = (basePattern) => Array.from({length:24}, (_,i) => Math.max(0, Math.round(basePattern(i) + (rand()-0.5)*2)));
  KPI.spark = {
    health:        buildSpark((i)=> 90 - Math.sin(i/4)*4 - (i>18?5:0)),
    breaches:      buildSpark((i)=> 12 + Math.sin(i/3)*5 + (i>20?10:0)),
    response:      buildSpark((i)=> avgResp + Math.sin(i/3)*3),
    resolution:    buildSpark((i)=> avgResv + Math.cos(i/4)*1.5),
    at_risk:       buildSpark((i)=> totalAtRisk/3 + Math.sin(i/3)*8 + (i>18?12:0)),
    unassigned:    buildSpark((i)=> 8 + Math.sin(i/4)*3 + (i>16?3:0)),
  };

  return { QUEUES: QUEUE_METRICS, AT_RISK, INCIDENTS, EVENTS, AGENTS, BOTTLENECKS, KPI };
})();
