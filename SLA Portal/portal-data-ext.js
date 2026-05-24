// Extend OPSDATA with daily series + heatmap for the analytical portal
(function() {
  if (!window.OPSDATA) return;
  const D = window.OPSDATA;

  let seed = 137;
  const rand = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
  const rnd = (mn, mx) => mn + rand() * (mx - mn);

  // Daily series per queue (last 90 days max). Each day has reaction_breach, resolution_breach, total.
  const DAILY_DAYS = 90;
  const today = new Date(); today.setHours(0, 0, 0, 0);

  D.DAILY = D.QUEUES.map((q) => {
    const series = [];
    const dailyVolume = q.tickets / 30;            // base tickets per day
    const dailyReaction = q.reaction.breached / 30;
    const dailyResolve  = q.resolution.breached / 30;
    for (let i = 0; i < DAILY_DAYS; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() - (DAILY_DAYS - 1 - i));
      const dow = date.getDay();                   // 0=Sun..6=Sat
      const isWeekend = dow === 0 || dow === 6;
      const volFactor = isWeekend ? 0.4 : 1.0 + Math.sin(i * 0.2) * 0.15;
      // Add a "spike" in last 7 days for visual interest
      const trendFactor = i >= DAILY_DAYS - 7 ? 1.0 + ((i - (DAILY_DAYS - 7)) / 7) * 0.5 : 1.0;
      const total       = Math.max(0, Math.round(dailyVolume * volFactor + (rand() - 0.5) * 3));
      const reaction    = Math.max(0, Math.round(dailyReaction * volFactor * trendFactor + (rand() - 0.5) * 1.5));
      const resolution  = Math.max(0, Math.round(dailyResolve  * volFactor * trendFactor + (rand() - 0.5) * 1.5));
      series.push({ date, total, reaction, resolution, dow });
    }
    return { queue_id: q.id, name: q.name, series };
  });

  // Aggregate daily across all queues for the headline chart
  D.DAILY_TOTAL = (function() {
    const arr = [];
    for (let i = 0; i < DAILY_DAYS; i++) {
      let total = 0, reaction = 0, resolution = 0;
      const date = D.DAILY[0].series[i].date;
      for (const q of D.DAILY) {
        total      += q.series[i].total;
        reaction   += q.series[i].reaction;
        resolution += q.series[i].resolution;
      }
      arr.push({ date, total, reaction, resolution });
    }
    return arr;
  })();

  // Heatmap: queue × hour-of-day, breach intensity (sum reaction + resolution).
  // Patterns: business hours peaks, weekend lulls, queue-specific spikes.
  D.HEATMAP = D.QUEUES.map((q) => {
    const hours = [];
    for (let h = 0; h < 24; h++) {
      let base;
      if (q.calendar === "24×7") {
        base = 2 + Math.sin((h - 6) * Math.PI / 12) * 1.5 + Math.cos(h * 0.3) * 0.8;
      } else {
        // business hours: high 9-18, low elsewhere
        base = (h >= 9 && h <= 18) ? 3 + Math.sin((h - 9) * Math.PI / 9) * 2 : 0.4;
      }
      const tierMul = q.tier === "crit" ? 3.0 : q.tier === "high" ? 2.0 : q.tier === "warn" ? 1.2 : 0.7;
      const value = Math.max(0, Math.round(base * tierMul + (rand() - 0.5) * 2));
      hours.push(value);
    }
    return { queue_id: q.id, name: q.name, tier: q.tier, hours };
  });

  // Hour-of-day distribution across all queues (for small subchart in detail)
  D.HOUR_TOTAL = (function() {
    const arr = new Array(24).fill(0);
    for (const q of D.HEATMAP) for (let h = 0; h < 24; h++) arr[h] += q.hours[h];
    return arr;
  })();

  // Pre-compute owner workload per queue (for detail panel)
  D.OWNER_BY_QUEUE = {};
  const allOwners = D.AGENTS.map((a) => a.name);
  for (const q of D.QUEUES) {
    const pickN = Math.min(5, 3 + Math.floor(rand() * 3));
    const owners = [];
    for (let i = 0; i < pickN; i++) {
      const ag = allOwners[Math.floor(rand() * allOwners.length)];
      owners.push({
        name: ag,
        open: Math.round(q.open * (0.1 + rand() * 0.3)),
        sla_pct: Math.round(80 + rand() * 18),
      });
    }
    D.OWNER_BY_QUEUE[q.id] = owners.sort((a, b) => b.open - a.open);
  }

  // Total per scope
  D.SCOPE_TOTALS = (function() {
    const all = { name: "Все", tickets: 0, reaction_breach: 0, resolution_breach: 0, queues: D.QUEUES.length };
    const sup = { name: "Support", tickets: 0, reaction_breach: 0, resolution_breach: 0, queues: 0 };
    const inf = { name: "Infrastructure", tickets: 0, reaction_breach: 0, resolution_breach: 0, queues: 0 };
    const biz = { name: "Бизнес", tickets: 0, reaction_breach: 0, resolution_breach: 0, queues: 0 };
    for (const q of D.QUEUES) {
      all.tickets += q.tickets; all.reaction_breach += q.reaction.breached; all.resolution_breach += q.resolution.breached;
      if (q.name.startsWith("Support")) {
        sup.tickets += q.tickets; sup.reaction_breach += q.reaction.breached; sup.resolution_breach += q.resolution.breached; sup.queues++;
      } else if (q.name.startsWith("Infrastructure")) {
        inf.tickets += q.tickets; inf.reaction_breach += q.reaction.breached; inf.resolution_breach += q.resolution.breached; inf.queues++;
      } else {
        biz.tickets += q.tickets; biz.reaction_breach += q.reaction.breached; biz.resolution_breach += q.resolution.breached; biz.queues++;
      }
    }
    return { all, sup, inf, biz };
  })();
})();
