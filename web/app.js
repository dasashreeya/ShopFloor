// ShopFloor UI: Google Stitch design (design/stitch/) driven by the real API.
// Every interpolated value goes through html`` which escapes it: headlines and drafts are LLM-written.

// ---------- tiny helpers ----------
class Raw { constructor(s) { this.s = s; } }
const raw = (s) => new Raw(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v) => (v instanceof Raw ? v.s : Array.isArray(v) ? v.map(fmt).join("") : esc(v));
const html = (strs, ...vals) => raw(strs.reduce((a, s, i) => a + s + (i < vals.length ? fmt(vals[i]) : ""), ""));
const $ = (s, root = document) => root.querySelector(s);
const usd = (n) => "$" + Math.round(n).toLocaleString();
const pct = (x) => Math.round(x * 100) + "%";
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const icon = (name, cls = "") => html`<span class="material-symbols-outlined ${cls}">${name}</span>`;

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

const JOBS = {
  missed_calls: { icon: "phone_in_talk", color: "#ff8a00", tag: "Voice & orders" },
  review_replies: { icon: "reviews", color: "#0ea5e9", tag: "Reputation" },
  invoice_chasing: { icon: "receipt_long", color: "#10b981", tag: "Cash flow" },
  email_triage: { icon: "mail", color: "#8b5cf6", tag: "Inbox" },
  other: { icon: "smart_toy", color: "#64748b", tag: "Other" },
};
const job = (j) => JOBS[j] || JOBS.other;
const CONNECTORS = {
  square: ["Square", "point_of_sale", "Orders, payments, customers"],
  toast: ["Toast", "restaurant", "Orders, guests"],
  quickbooks: ["QuickBooks", "account_balance", "Invoices, accounting"],
  gmail: ["Gmail", "mail", "Inbound email"],
  phone: ["Phone line", "call", "Call log, SMS"],
  google_business: ["Google Business Profile", "storefront", "Reviews"],
};
const connName = (c) => (CONNECTORS[c] || [c])[0];
const SOURCES = {
  square_app_marketplace: "Square App Marketplace",
  toast_partner_connect: "Toast Partner Connect",
  quickbooks_app_store: "QuickBooks App Store",
};

// ---------- state ----------
const S = { biz: null, deck: [], tools: {}, roster: [], accuracy: [] };

async function boot() {
  $("#view").innerHTML = html`
    <div class="h-full flex flex-col items-center justify-center gap-3 text-on-surface-variant">
      ${icon("autorenew", "text-[32px] animate-spin text-secondary")}
      <p class="text-[13px]">Replaying your last 90 days against every tool…</p>
    </div>`.s;
  const saved = localStorage.getItem("sf.biz");
  if (saved) S.biz = await api(`/api/businesses/${saved}`).catch(() => null);
  if (!S.biz) await newBusiness();
  await refreshAll();
  window.addEventListener("hashchange", render);
  $("#btn-reset").onclick = async () => { await newBusiness(); await refreshAll(); location.hash = "#deck"; render(); toast("New demo business connected", "restart_alt", "DEMO"); };
  render();
}

async function newBusiness() {
  S.biz = await api("/api/businesses", { method: "POST", body: JSON.stringify({ name: "Joe's Pizza & Grill" }) });
  localStorage.setItem("sf.biz", S.biz.id);
}

async function refreshAll() {
  const [tools, deck, roster, accuracy] = await Promise.all([
    api("/api/tools"), api(`/api/businesses/${S.biz.id}/deck`), api(`/api/businesses/${S.biz.id}/roster`), api("/api/accuracy"),
  ]);
  S.tools = Object.fromEntries(tools.map((t) => [t.id, t]));
  S.deck = deck; S.roster = roster; S.accuracy = accuracy;
  renderHeader();
}

function renderHeader() {
  const conns = S.biz.connectors.map(connName);
  $("#biz-line").textContent = `${S.biz.name} · ${conns.slice(0, 2).join(" + ")}${conns.length > 2 ? ` +${conns.length - 2}` : ""}`;
  const n = S.accuracy.reduce((a, r) => a + r.verified_hires, 0);
  const cov = n ? S.accuracy.reduce((a, r) => a + r.interval_coverage * r.verified_hires, 0) / n : null;
  const badge = $("#calib-badge");
  badge.textContent = cov == null ? "UNCALIBRATED" : `${pct(cov)} IN RANGE`;
  badge.title = cov == null ? "No verified outcomes yet" : `${plural(n, "verified hire")} landed inside our predicted range ${pct(cov)} of the time`;
  const left = S.deck.length;
  $("#counter-badge").textContent = left ? `${left} left` : "Deck done";
}

function render() {
  const view = (location.hash || "#deck").slice(1);
  document.querySelectorAll(".nav-link").forEach((a) => {
    const on = a.dataset.view === view;
    a.classList.toggle("active", on);
    on ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current");
  });
  $("#counter-wrap").style.visibility = view === "deck" ? "visible" : "hidden";
  ({ deck: renderDeck, roster: renderRoster, outcomes: renderOutcomes, integrations: renderIntegrations }[view] || renderDeck)();
}

// ---------- toast & modal ----------
function toast(msg, iconName = "check_circle", tag = "", color = "text-[#6ffbbe]") {
  const t = $("#toast");
  $("#toast-msg").textContent = msg; $("#toast-icon").textContent = iconName;
  $("#toast-tag").textContent = tag; $("#toast-tag").className = `font-label-badge text-[10px] uppercase tracking-wider font-bold ${color}`;
  t.classList.remove("-translate-y-24", "opacity-0");
  clearTimeout(t.timer);
  t.timer = setTimeout(() => t.classList.add("-translate-y-24", "opacity-0"), 2600);
}
const fail = (e) => toast(e.message, "error", "ERROR", "text-red-400");

function confirmFire(row) {
  return new Promise((resolve) => {
    const m = $("#modal");
    const conns = [...new Set((row.tool?.integrations || []).map(connName))].join(" and ") || "connected apps";
    const price = row.hire.billing?.plan_usd_month;
    m.innerHTML = html`
      <div class="w-full max-w-md bg-surface-container-lowest rounded-3xl p-5 shadow-2xl">
        <div class="flex items-center gap-2 text-error">${icon("warning")}<h3 class="font-headline-sm text-[18px] font-bold">Fire ${row.tool?.name}?</h3></div>
        <p class="text-[13px] text-on-surface-variant mt-1">This happens immediately, in one tap:</p>
        <ul class="mt-3 space-y-2 text-[13px]">
          <li class="flex gap-2">${icon("check", "text-[18px] text-[#059669]")} Revoke its access to ${conns} (${plural(row.hire.granted_scopes.length, "scope")})</li>
          <li class="flex gap-2">${icon("check", "text-[18px] text-[#059669]")} Export everything it did to you (JSON download)</li>
          <li class="flex gap-2">${icon("check", "text-[18px] text-[#059669]")} ${price ? `Stop billing (${usd(price)}/mo)` : "No billing to cancel (shadow shifts are free)"}</li>
        </ul>
        <div class="mt-5 flex flex-col gap-2">
          <button data-ok class="w-full py-3 rounded-full bg-error text-white font-label-button">Yes, fire &amp; revoke access</button>
          <button data-no class="w-full py-3 rounded-full bg-surface-container font-label-button">Keep it</button>
        </div>
      </div>`.s;
    m.classList.remove("hidden");
    const done = (v) => { m.classList.add("hidden"); m.innerHTML = ""; resolve(v); };
    $("[data-ok]", m).onclick = () => done(true);
    $("[data-no]", m).onclick = () => done(false);
    $("[data-no]", m).focus();
  });
}

function download(name, data) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  a.download = name; a.click(); URL.revokeObjectURL(a.href);
}

// ---------- Decision Deck ----------
function cardHTML(c, posFromTop) {
  const t = S.tools[c.tool_id] || {}, j = job(c.job);
  const roi = c.monthly_cost_usd > 0 ? Math.round(c.monthly_value_usd / c.monthly_cost_usd) : null;
  return html`
    <div class="h-2 w-full" style="background-color:${j.color}"></div>
    <div class="p-4 sm:p-5 flex flex-col flex-1 justify-between gap-3 relative">
      ${posFromTop === 0 ? html`
        <div class="stamp stamp-hire absolute top-6 left-6 z-50 px-4 py-1.5 rounded-xl font-headline-sm text-[22px] font-black tracking-widest uppercase rotate-[-18deg]" data-stamp="right">HIRE</div>
        <div class="stamp stamp-pass absolute top-6 right-6 z-50 px-4 py-1.5 rounded-xl font-headline-sm text-[22px] font-black tracking-widest uppercase rotate-[18deg]" data-stamp="left">PASS</div>
        <div class="stamp stamp-shadow absolute bottom-24 inset-x-8 text-center z-50 px-4 py-2 rounded-xl font-headline-sm text-[20px] font-black tracking-widest uppercase rotate-[-6deg]" data-stamp="up">14-DAY SHADOW</div>` : ""}
      <div class="flex items-start justify-between gap-2.5">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-12 h-12 rounded-2xl bg-surface-container flex items-center justify-center shrink-0 shadow-inner border border-outline-variant/30">${icon(j.icon, "text-[26px] text-on-surface")}</div>
          <div class="min-w-0">
            <h2 class="font-headline-sm text-[18px] text-on-surface font-bold truncate leading-tight">${c.tool_name}</h2>
            <p class="font-body-sm text-[12px] text-on-surface-variant truncate mt-0.5">${t.vendor || "Unknown vendor"} · ${t.summary || ""}</p>
          </div>
        </div>
        <div class="text-right shrink-0 bg-surface-container-low px-3 py-1.5 rounded-xl border border-surface-container">
          <div class="font-headline-sm text-[17px] font-bold text-on-surface">${usd(c.monthly_cost_usd)}<span class="text-[11px] font-normal text-on-surface-variant">/mo</span></div>
        </div>
      </div>
      <div class="bg-surface-container-low rounded-2xl p-3.5 flex flex-col gap-2.5 border border-surface-container">
        <div class="text-[10px] font-label-badge text-on-surface-variant uppercase tracking-wider font-bold flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full" style="background-color:${j.color}"></span> Replay findings · ${j.tag} · last 90 days
        </div>
        <div class="grid grid-cols-2 gap-2">
          ${c.stats.map((s) => html`
            <div class="bg-surface-container-lowest p-2.5 rounded-xl border border-outline-variant/20">
              <div class="font-body-sm text-[11px] text-on-surface-variant truncate">${s.label}</div>
              <div class="font-headline-sm text-[16px] font-bold mt-0.5 ${s.accent ? "text-[#059669]" : "text-on-surface"}">${s.value}</div>
            </div>`)}
        </div>
        <p class="font-body-md text-[12.5px] text-on-surface-variant leading-snug">${c.headline}</p>
      </div>
      <div class="bg-secondary-fixed/35 border border-secondary-fixed-dim/40 rounded-2xl p-3 flex items-center justify-between gap-2">
        <div class="flex flex-col min-w-0">
          <span class="font-body-sm text-[10px] text-on-secondary-fixed-variant uppercase tracking-wider font-bold">Estimated value</span>
          <div class="font-headline-sm text-[22px] font-bold text-secondary flex items-baseline gap-1">+${usd(c.monthly_value_usd)}<span class="text-[11px] font-normal text-on-secondary-fixed-variant">/mo</span></div>
          <span class="text-[10px] text-on-secondary-fixed-variant">90% range ${usd(c.monthly_value_low)}–${usd(c.monthly_value_high)}</span>
        </div>
        <div class="text-right shrink-0">
          ${roi ? html`<span class="font-label-badge text-[11px] font-bold px-2.5 py-1 rounded-full bg-secondary-container text-white">${roi}× its cost</span>` : ""}
          <div class="text-[10px] text-on-secondary-fixed-variant font-medium mt-1 truncate max-w-[140px]">${(t.integrations || []).map(connName).join(" & ")}</div>
        </div>
      </div>
      <div class="flex items-center justify-between text-[11px] text-on-surface-variant px-1 pt-0.5 gap-2">
        ${c.lab_accuracy == null
          ? html`<span class="flex items-center gap-1 font-medium truncate">${icon("science", "text-[15px]")} Not lab-tested yet</span>`
          : html`<span class="flex items-center gap-1 font-medium truncate">${icon("verified", "text-[15px] text-[#059669]")} Lab tested · ${pct(c.lab_accuracy)} accuracy</span>`}
        <span class="font-medium text-secondary shrink-0">Free shadow · 1-tap fire</span>
      </div>
    </div>`;
}

function renderDeck() {
  const v = $("#view");
  v.innerHTML = html`
    <div class="h-full w-full max-w-md mx-auto flex flex-col justify-between px-3 py-2">
      <div class="relative w-full flex-1 min-h-[440px] max-h-[600px] my-auto" id="card-stack"></div>
      <div class="w-full shrink-0 pt-2 pb-1 px-4 flex items-center justify-center gap-3.5 z-30" id="action-controls">
        <button class="w-14 h-14 rounded-full bg-surface-container-lowest border-2 border-red-500/20 shadow-lg text-red-500 hover:bg-red-50 flex items-center justify-center active:scale-90 transition-transform" data-dir="left" title="Pass (←)" aria-label="Pass">${icon("close", "text-[28px]")}</button>
        <button class="w-12 h-12 rounded-full bg-amber-500 text-white shadow-lg shadow-amber-500/30 hover:bg-amber-600 flex items-center justify-center active:scale-90 transition-transform" data-dir="up" title="14-day shadow shift (↑)" aria-label="Start 14-day shadow shift">${icon("bolt", "text-[24px]")}</button>
        <button class="w-14 h-14 rounded-full bg-surface-container-lowest border-2 border-emerald-500/20 shadow-lg text-emerald-500 hover:bg-emerald-50 flex items-center justify-center active:scale-90 transition-transform" data-dir="right" title="Hire (→)" aria-label="Hire">${icon("favorite", "text-[28px]")}</button>
        <button class="w-11 h-11 rounded-full bg-surface-container-lowest border border-outline-variant/40 shadow-md text-blue-500 flex items-center justify-center active:scale-90 transition-transform" id="btn-info" title="Tool dossier" aria-label="Open tool dossier">${icon("info", "text-[20px]")}</button>
      </div>
    </div>`.s;
  const stack = $("#card-stack");
  $("#action-controls").style.visibility = S.deck.length ? "visible" : "hidden";
  if (!S.deck.length) {
    stack.innerHTML = html`
      <div class="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-surface-container-lowest/90 rounded-3xl border border-dashed border-outline-variant/60">
        <div class="w-16 h-16 rounded-full bg-secondary-fixed flex items-center justify-center text-secondary mb-3">${icon("done_all", "text-[32px]")}</div>
        <h3 class="font-headline-sm text-[20px] font-bold">Deck cleared</h3>
        <p class="text-[13px] text-on-surface-variant max-w-[260px] mt-1">That's every job we found in your last 90 days. Your hires and shadow shifts are on the roster.</p>
        <a href="#roster" class="mt-4 px-5 py-2.5 rounded-full bg-primary-container text-white font-label-button text-[13px] flex items-center gap-1.5">${icon("group_work", "text-[18px]")} Open Active Roster</a>
      </div>`.s;
    return;
  }
  const visible = S.deck.slice(0, 3);
  visible.slice().reverse().forEach((c) => {
    const pos = visible.indexOf(c);
    const el = document.createElement("article");
    el.className = `absolute inset-0 rounded-[28px] bg-surface-container-lowest shadow-2xl flex flex-col overflow-hidden border border-outline-variant/30 ${pos === 0 ? "card-drag cursor-grab" : "pointer-events-none"}`;
    el.style.transform = `translate3d(0, ${pos * 9}px, 0) scale(${1 - pos * 0.045})`;
    el.style.opacity = 1 - pos * 0.16;
    el.style.zIndex = 30 - pos * 5;
    el.style.transition = "transform .3s cubic-bezier(.2,.9,.3,1), opacity .3s ease";
    el.innerHTML = cardHTML(c, pos).s;
    if (pos === 0) { el.id = "top-card"; attachGestures(el); }
    stack.appendChild(el);
  });
  document.querySelectorAll("#action-controls [data-dir]").forEach((b) => (b.onclick = () => swipe(b.dataset.dir)));
  $("#btn-info").onclick = () => openDossier(S.deck[0].tool_id);
}

function attachGestures(card) {
  let x0 = null, y0 = 0, dx = 0, dy = 0;
  const stamps = Object.fromEntries([...card.querySelectorAll("[data-stamp]")].map((s) => [s.dataset.stamp, s]));
  const dirOf = (x, y) => (x > 85 ? "right" : x < -85 ? "left" : y < -85 && Math.abs(x) < 70 ? "up" : null);
  card.addEventListener("pointerdown", (e) => { x0 = e.clientX; y0 = e.clientY; dx = dy = 0; card.setPointerCapture(e.pointerId); card.style.transition = "none"; });
  card.addEventListener("pointermove", (e) => {
    if (x0 == null) return;
    dx = e.clientX - x0; dy = e.clientY - y0;
    card.style.transform = `translate3d(${dx}px, ${dy}px, 0) rotate(${dx * 0.07}deg)`;
    stamps.right.style.opacity = dx > 25 ? Math.min((dx - 25) / 80, 1) : 0;
    stamps.left.style.opacity = dx < -25 ? Math.min((-dx - 25) / 80, 1) : 0;
    stamps.up.style.opacity = dy < -35 && Math.abs(dx) < 70 ? Math.min((-dy - 35) / 75, 1) : 0;
  });
  const end = () => {
    if (x0 == null) return;
    x0 = null;
    const dir = dirOf(dx, dy);
    if (dir) return swipe(dir);
    card.style.transition = "transform .35s cubic-bezier(.175,.885,.32,1.25)";
    card.style.transform = "translate3d(0,0,0)";
    Object.values(stamps).forEach((s) => (s.style.opacity = 0));
  };
  card.addEventListener("pointerup", end);
  card.addEventListener("pointercancel", end);
}

let swiping = false;
async function swipe(dir, cardId) {
  if (swiping) return;
  const card = cardId ? S.deck.find((c) => c.id === cardId) : S.deck[0];
  if (!card) return;
  swiping = true;
  const top = card === S.deck[0] ? $("#top-card") : null;
  if (top) {
    const stamp = top.querySelector(`[data-stamp="${dir}"]`); if (stamp) stamp.style.opacity = 1;
    top.style.transition = "transform .4s ease-out, opacity .4s ease-out";
    top.style.transform = { right: "translate3d(140%,40px,0) rotate(25deg)", left: "translate3d(-140%,40px,0) rotate(-25deg)", up: "translate3d(0,-150%,0) scale(.9)" }[dir];
    top.style.opacity = 0;
  }
  try {
    await api(`/api/cards/${card.id}/swipe`, { method: "POST", body: JSON.stringify({ direction: dir }) });
    ({
      right: () => toast(`Hired ${card.tool_name}`, "verified", "HIRED", "text-emerald-400"),
      left: () => toast(`Passed on ${card.tool_name}`, "archive", "PASSED", "text-red-400"),
      up: () => toast(`14-day shadow shift started for ${card.tool_name}`, "bolt", "SHADOWING", "text-amber-400"),
    })[dir]();
  } catch (e) { fail(e); }
  await refreshAll();
  swiping = false;
  setTimeout(render, top ? 250 : 0);
}
document.addEventListener("keydown", (e) => {
  if ((location.hash || "#deck") !== "#deck" || !$("#sheet").classList.contains("hidden") || !$("#modal").classList.contains("hidden")) return;
  const dir = { ArrowLeft: "left", ArrowUp: "up", ArrowRight: "right" }[e.key];
  if (dir) { e.preventDefault(); swipe(dir); }
});

// ---------- Active Roster ----------
const STATUS = {
  hired: ["Active", "bg-[#10b981]/15 text-[#059669]"],
  shadow: ["Shadow shift", "bg-amber-500/15 text-amber-700"],
  fired: ["Fired", "bg-surface-container text-on-surface-variant"],
};
const shadowDay = (h) => Math.min(14, Math.floor((Date.now() - new Date(h.started_at)) / 864e5) + 1);

function renderRoster() {
  const active = S.roster.filter((r) => r.hire.status === "hired");
  const shadows = S.roster.filter((r) => r.hire.status === "shadow");
  const value = active.reduce((a, r) => a + (r.prediction?.monthly_value_usd || 0), 0);
  const cost = active.reduce((a, r) => a + (r.hire.billing?.plan_usd_month || 0), 0);
  $("#view").innerHTML = html`
    <div class="max-w-md mx-auto px-4 py-4 flex flex-col gap-4 pb-10">
      <div>
        <h1 class="font-headline-lg-mobile text-headline-lg-mobile">Floor Roster</h1>
        <p class="text-[13px] text-on-surface-variant">${active.length} active · ${shadows.length} on a free shadow shift</p>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div class="bg-surface-container-lowest rounded-2xl p-3 border border-outline-variant/30"><div class="text-[11px] text-on-surface-variant">Predicted value added</div><div class="font-label-data-lg text-label-data-lg text-[#059669]">+${usd(value)}<span class="text-[12px] font-normal">/mo</span></div></div>
        <div class="bg-surface-container-lowest rounded-2xl p-3 border border-outline-variant/30"><div class="text-[11px] text-on-surface-variant">Total cost</div><div class="font-label-data-lg text-label-data-lg">${usd(cost)}<span class="text-[12px] font-normal">/mo</span></div></div>
      </div>
      ${S.roster.length ? "" : html`<div class="text-center text-on-surface-variant text-[13px] py-10 border border-dashed border-outline-variant/60 rounded-2xl">No AI workers yet. Swipe right or up on the <a class="underline" href="#deck">Decision Deck</a>.</div>`}
      <div class="flex flex-col gap-3">${S.roster.map(rosterRow)}</div>
      ${active.length ? html`
        <div class="bg-surface-container-low rounded-2xl p-4 border border-surface-container">
          <div class="flex items-center gap-2 font-headline-sm text-[15px]">${icon("receipt", "text-[20px]")} Monthly billing</div>
          ${active.map((r) => html`<div class="flex justify-between text-[13px] mt-2"><span>${r.tool?.name}</span><span>${usd(r.hire.billing.plan_usd_month)}.00</span></div>`)}
          <div class="flex justify-between font-bold text-[14px] mt-3 pt-2 border-t border-outline-variant/40"><span>Total</span><span>${usd(cost)}.00/mo</span></div>
          <p class="text-[11px] text-on-surface-variant mt-2">Fire any tool anytime: access revoked, data exported, billing stopped.</p>
        </div>` : ""}
    </div>`.s;
  document.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => rosterAction(b.dataset.act, b.dataset.hire)));
}

function rosterRow(r) {
  const h = r.hire, t = r.tool || {}, j = job(t.job);
  const [label, cls] = STATUS[h.status];
  const o = r.outcome;
  const btn = (act, text, style) => html`<button data-act="${act}" data-hire="${h.id}" class="px-3 py-2 rounded-full text-[12px] font-label-button ${style}">${text}</button>`;
  return html`
    <div class="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/30 ${h.status === "fired" ? "opacity-60" : ""}">
      <div class="flex items-start gap-3">
        <div class="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center shrink-0">${icon(j.icon, "text-[22px]")}</div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap"><span class="font-headline-sm text-[15px] font-bold">${t.name}</span><span class="px-2 py-0.5 rounded-full text-[10px] font-label-badge ${cls}">${label}</span></div>
          <p class="text-[12px] text-on-surface-variant truncate">${t.summary}</p>
        </div>
        <div class="text-right shrink-0 font-headline-sm text-[14px]">${h.status === "shadow" ? "$0" : usd(t.price_usd_month)}<span class="text-[11px] font-normal text-on-surface-variant">${h.status === "shadow" ? " trial" : "/mo"}</span></div>
      </div>
      ${h.status === "shadow" ? html`
        <div class="mt-3">
          <div class="flex justify-between text-[11px] text-on-surface-variant"><span>Day ${shadowDay(h)} of 14</span><span>${14 - shadowDay(h)} days left</span></div>
          <div class="h-1.5 rounded-full bg-surface-container mt-1 overflow-hidden"><div class="h-full bg-amber-500" style="width:${(shadowDay(h) / 14) * 100}%"></div></div>
          <p class="text-[12px] mt-2">${h.shadow_actions} actions it would have taken · nothing was sent</p>
        </div>` : ""}
      ${h.status === "hired" && r.prediction ? html`<p class="text-[12px] mt-2 text-on-surface-variant">Predicted <b class="text-on-surface">+${usd(r.prediction.monthly_value_usd)}/mo</b>${o ? html` · Verified actual <b class="${o.within_interval ? "text-[#059669]" : "text-error"}">+${usd(o.actual_monthly_usd)}/mo</b> ${o.within_interval ? "(inside our range)" : "(outside our range)"}` : ""}</p>` : ""}
      ${h.status === "fired" ? html`<p class="text-[12px] mt-2 text-on-surface-variant">Access revoked · data exported · billing cancelled</p>` : ""}
      ${h.status !== "fired" ? html`
        <div class="flex gap-2 mt-3 flex-wrap">
          ${btn("dossier", "Manage", "bg-surface-container")}
          ${h.status === "shadow" ? btn("promote", "Keep & hire", "bg-[#10b981] text-white") : ""}
          ${h.status === "hired" && !o ? btn("measure", "Run day-30 audit (demo)", "bg-primary-container text-white") : ""}
          ${btn("fire", h.status === "shadow" ? "Stop trial" : "Fire", "bg-error-container text-on-error-container")}
        </div>` : ""}
    </div>`;
}

async function rosterAction(act, hireId) {
  const row = S.roster.find((r) => r.hire.id === hireId);
  try {
    if (act === "dossier") return openDossier(row.tool.id);
    if (act === "promote") { await api(`/api/hires/${hireId}/promote`, { method: "POST" }); toast(`Hired ${row.tool.name}`, "verified", "HIRED"); }
    if (act === "measure") {
      const o = await api(`/api/hires/${hireId}/measure`, { method: "POST" });
      toast(`Audit: predicted ${usd(o.predicted_monthly_usd)}, actual ${usd(o.actual_monthly_usd)}`, "fact_check", o.within_interval ? "IN RANGE" : "MISSED", o.within_interval ? "text-[#6ffbbe]" : "text-red-400");
    }
    if (act === "fire") {
      if (!(await confirmFire(row))) return;
      const bundle = await api(`/api/hires/${hireId}/fire`, { method: "POST" });
      download(`shopfloor-export-${row.tool.id}-${hireId}.json`, bundle);
      toast(`Fired ${row.tool.name}. Data exported`, "power_settings_new", "REVOKED", "text-red-400");
    }
  } catch (e) { fail(e); }
  await refreshAll();
  render();
}

// ---------- Outcomes & Lab ----------
function renderOutcomes() {
  const n = S.accuracy.reduce((a, r) => a + r.verified_hires, 0);
  const cov = n ? S.accuracy.reduce((a, r) => a + r.interval_coverage * r.verified_hires, 0) / n : null;
  const audits = S.roster.filter((r) => r.outcome);
  const tools = Object.values(S.tools).sort((a, b) => (b.lab?.accuracy ?? -1) - (a.lab?.accuracy ?? -1));
  const filter = S.labFilter || "all";
  const jobsPresent = [...new Set(tools.map((t) => t.job))];
  $("#view").innerHTML = html`
    <div class="max-w-md mx-auto px-4 py-4 flex flex-col gap-5 pb-10">
      <section class="rounded-3xl bg-[#0b192c] text-white p-5 shadow-xl">
        <div class="flex items-center justify-between text-[10px] font-label-badge tracking-wider">
          <span class="flex items-center gap-1.5 text-[#6ffbbe]"><span class="w-2 h-2 rounded-full bg-[#4edea3]"></span> VERIFICATION LOOP</span>
          <span class="px-2 py-1 rounded-md bg-white/10">${plural(n, "VERIFIED HIRE")}</span>
        </div>
        <h1 class="font-headline-lg-mobile text-headline-lg-mobile mt-3">Closed-loop verification</h1>
        <p class="text-[13px] text-white/70 mt-1">We predict before you buy, then measure what actually happened 30 days later and publish it, including when we were wrong.</p>
        <div class="mt-4 rounded-2xl bg-white/5 border border-white/10 p-4">
          ${cov == null
            ? html`<div class="text-[14px] text-white/80">No verified outcomes yet. Hire a tool, then run its day-30 audit from the roster.</div>`
            : html`<div class="flex items-baseline gap-2"><span class="font-headline-xl text-[40px] font-bold">${pct(cov)}</span><span class="text-[#ff8a00] font-headline-sm">landed in our range</span></div>
                   <div class="text-[12px] text-white/60">Across ${plural(n, "verified hire")}, all businesses</div>`}
        </div>
      </section>

      ${S.accuracy.length ? html`
      <section>
        <h2 class="font-headline-sm text-[17px] flex items-center gap-2">${icon("public", "text-[20px]")} Published accuracy</h2>
        <div class="mt-2 bg-surface-container-lowest rounded-2xl border border-outline-variant/30 overflow-hidden">
          <table class="w-full text-[12px]">
            <thead class="bg-surface-container-low text-on-surface-variant"><tr><th class="text-left p-2.5">Job</th><th class="p-2.5">Hires</th><th class="p-2.5">Avg error</th><th class="p-2.5">In range</th><th class="p-2.5">Correction</th></tr></thead>
            <tbody>${S.accuracy.map((r) => html`<tr class="border-t border-outline-variant/20"><td class="p-2.5">${job(r.job).tag}</td><td class="p-2.5 text-center">${r.verified_hires}</td><td class="p-2.5 text-center">${r.mape == null ? "–" : pct(r.mape)}</td><td class="p-2.5 text-center">${pct(r.interval_coverage)}</td><td class="p-2.5 text-center">×${r.current_correction_factor}</td></tr>`)}</tbody>
          </table>
        </div>
        <p class="text-[11px] text-on-surface-variant mt-1.5">Correction is learned from verified outcomes and applied to every new prediction for that job.</p>
      </section>` : ""}

      <section>
        <h2 class="font-headline-sm text-[17px] flex items-center gap-2">${icon("fact_check", "text-[20px]")} 30-day post-hire audits <span class="ml-auto text-[10px] font-label-badge px-2 py-1 rounded-md bg-surface-container">${S.biz.name.toUpperCase()}</span></h2>
        ${audits.length ? "" : html`<p class="text-[13px] text-on-surface-variant mt-2">No audits for this business yet.</p>`}
        <div class="flex flex-col gap-3 mt-2">${audits.map(auditCard)}</div>
      </section>

      <section>
        <div class="flex items-center justify-between">
          <h2 class="font-headline-sm text-[17px] flex items-center gap-2">${icon("science", "text-[20px]")} Golden-set lab leaderboard</h2>
          <button id="btn-run-lab" class="px-3 py-2 rounded-full bg-secondary-container text-white text-[12px] font-label-button flex items-center gap-1">${icon("play_arrow", "text-[18px]")} Run lab</button>
        </div>
        <p class="text-[12px] text-on-surface-variant mt-1">Every tool runs the same golden-set tasks; a judge from a different model family grades each answer. Tools were found by crawling marketplaces; vendors don't submit themselves.</p>
        <div class="flex gap-2 overflow-x-auto mt-3 pb-1">
          ${["all", ...jobsPresent].map((jb) => html`<button data-filter="${jb}" class="shrink-0 px-3 py-1.5 rounded-full text-[12px] font-label-button ${filter === jb ? "bg-primary-container text-white" : "bg-surface-container"}">${jb === "all" ? "All categories" : job(jb).tag}</button>`)}
        </div>
        <div class="flex flex-col gap-2 mt-3">
          ${tools.filter((t) => filter === "all" || t.job === filter).map((t, i) => html`
            <button data-tool="${t.id}" class="text-left bg-surface-container-lowest rounded-2xl p-3 border border-outline-variant/30 hover:border-outline-variant">
              <div class="flex items-center gap-3">
                <span class="font-headline-sm text-[15px] ${t.lab ? "text-secondary" : "text-on-surface-variant"} w-7">${t.lab ? `#${i + 1}` : "–"}</span>
                <div class="flex-1 min-w-0"><div class="font-headline-sm text-[14px] font-bold truncate">${t.name}</div><div class="text-[11px] text-on-surface-variant truncate">${(t.integrations || []).map(connName).join(" + ") || "No integrations listed"}</div></div>
                <div class="text-right"><div class="font-label-data-md text-label-data-md">${t.lab ? pct(t.lab.accuracy) : "untested"}</div><div class="text-[10px] text-on-surface-variant">ACCURACY</div></div>
              </div>
              ${t.lab ? html`<div class="grid grid-cols-3 gap-2 mt-2 text-center bg-surface-container-low rounded-xl p-2 text-[11px]">
                <div><div class="text-on-surface-variant text-[10px]">LATENCY p50</div><b>${t.lab.p50_latency_s.toFixed(2)}s</b></div>
                <div><div class="text-on-surface-variant text-[10px]">COST / RESOLVED</div><b>${Number.isFinite(t.lab.cost_per_resolved_usd) ? "$" + t.lab.cost_per_resolved_usd.toFixed(5) : "n/a"}</b></div>
                <div><div class="text-on-surface-variant text-[10px]">TASKS</div><b>${t.lab.n_tasks}</b></div></div>` : ""}
            </button>`)}
        </div>
      </section>
    </div>`.s;
  document.querySelectorAll("[data-filter]").forEach((b) => (b.onclick = () => { S.labFilter = b.dataset.filter; renderOutcomes(); }));
  document.querySelectorAll("[data-tool]").forEach((b) => (b.onclick = () => openDossier(b.dataset.tool)));
  $("#btn-run-lab").onclick = runLab;
}

function auditCard(r) {
  const o = r.outcome, t = r.tool || {};
  const delta = (o.actual_monthly_usd - o.predicted_monthly_usd) / o.predicted_monthly_usd;
  const [tag, tagCls, tagIcon] = o.actual_monthly_usd < o.predicted_low ? ["NEEDS TUNING", "bg-secondary-fixed text-on-secondary-fixed-variant", "tune"]
    : o.actual_monthly_usd >= o.predicted_monthly_usd ? ["WIN", "bg-tertiary-fixed text-on-tertiary-fixed-variant", "trending_up"] : ["IN RANGE", "bg-surface-container text-on-surface", "check"];
  const fill = Math.max(0, Math.min(1, o.actual_monthly_usd / (o.predicted_high || 1)));
  return html`
    <div class="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/30">
      <div class="flex items-start justify-between gap-2">
        <div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center">${icon(job(t.job).icon, "text-[22px]")}</div>
          <div><div class="font-headline-sm text-[15px] font-bold">${t.name}</div><div class="text-[11px] text-on-surface-variant">Measured over ${o.days_measured} days · ${(t.integrations || []).map(connName).join(" + ")}</div></div></div>
        <span class="px-2 py-1 rounded-md text-[10px] font-label-badge flex items-center gap-1 ${tagCls}">${icon(tagIcon, "text-[14px]")} ${tag}</span>
      </div>
      <div class="grid grid-cols-2 gap-2 mt-3 bg-surface-container-low rounded-xl p-3">
        <div><div class="text-[11px] text-on-surface-variant">Model prediction</div><div class="font-headline-sm text-[16px]">+${usd(o.predicted_monthly_usd)}/mo</div><div class="text-[10px] text-on-surface-variant">range ${usd(o.predicted_low)}–${usd(o.predicted_high)}</div></div>
        <div class="text-right"><div class="text-[11px] text-on-surface-variant">Verified actual <b class="${delta >= 0 ? "text-[#059669]" : "text-error"}">${delta >= 0 ? "+" : ""}${pct(delta)}</b></div><div class="font-label-data-lg text-label-data-lg">+${usd(o.actual_monthly_usd)}<span class="text-[12px] font-normal">/mo</span></div></div>
      </div>
      <div class="h-2 rounded-full bg-surface-container mt-3 overflow-hidden"><div class="h-full ${o.within_interval ? "bg-[#10b981]" : "bg-[#ff8a00]"}" style="width:${fill * 100}%"></div></div>
      <p class="text-[11px] text-on-surface-variant mt-2">${o.within_interval ? "Inside our predicted range. This outcome now sharpens every future prediction for this job." : "Outside our predicted range. Logged publicly and fed back into calibration."}</p>
    </div>`;
}

async function runLab() {
  const btn = $("#btn-run-lab");
  btn.disabled = true; btn.classList.add("opacity-60");
  const ids = Object.values(S.tools).filter((t) => t.job !== "other").map((t) => t.id);
  for (const [i, id] of ids.entries()) {
    toast(`Running lab ${i + 1}/${ids.length}: ${S.tools[id].name}`, "science", "LAB");
    try { await api(`/api/lab/${id}`, { method: "POST" }); } catch (e) { fail(e); }
  }
  await refreshAll();
  toast("Lab complete. New cards use these scores", "verified", "DONE");
  renderOutcomes();
}

// ---------- Integrations ----------
function renderIntegrations() {
  const holders = {};
  S.roster.filter((r) => r.hire.status !== "fired").forEach((r) => (r.tool?.integrations || []).forEach((c) => (holders[c] ||= []).push(r)));
  $("#view").innerHTML = html`
    <div class="max-w-md mx-auto px-4 py-4 flex flex-col gap-4 pb-10">
      <div><h1 class="font-headline-lg-mobile text-headline-lg-mobile">Integrations</h1>
        <p class="text-[13px] text-on-surface-variant">What ${S.biz.name} has connected, and which AI workers can touch it. Shadow shifts get read-only scopes.</p></div>
      ${S.biz.connectors.map((c) => {
        const [name, ic, what] = CONNECTORS[c] || [c, "link", ""];
        const hs = holders[c] || [];
        return html`
          <div class="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/30">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-primary-container text-white flex items-center justify-center">${icon(ic, "text-[20px]")}</div>
              <div class="flex-1"><div class="font-headline-sm text-[15px] font-bold">${name}</div><div class="text-[12px] text-on-surface-variant">${what} · 90 days replayed</div></div>
              <span class="flex items-center gap-1 text-[11px] text-[#059669] font-label-badge">${icon("check_circle", "text-[16px]")} CONNECTED</span>
            </div>
            ${hs.length ? html`<div class="mt-3 flex flex-col gap-1.5">${hs.map((r) => html`
              <div class="flex items-center justify-between text-[12px] bg-surface-container-low rounded-lg px-2.5 py-1.5">
                <span>${r.tool.name}</span>
                <span class="font-label-badge text-[10px] ${r.hire.status === "shadow" ? "text-amber-700" : "text-[#059669]"}">${r.hire.granted_scopes.filter((s) => s.startsWith(c + ":")).map((s) => s.split(":").slice(1).join(":")).join(", ") || "no scopes"}</span>
              </div>`)}</div>` : html`<p class="text-[12px] text-on-surface-variant mt-2">No AI worker has access.</p>`}
          </div>`;
      })}
      <p class="text-[11px] text-on-surface-variant">Demo businesses use synthetic history. Real OAuth connectors plug in behind <code>shopfloor/connectors/</code>.</p>
    </div>`.s;
}

// ---------- Tool dossier (sheet) ----------
async function openDossier(toolId) {
  const t = S.tools[toolId];
  if (!t) return;
  const sheet = $("#sheet");
  const card = S.deck.find((c) => c.tool_id === toolId);
  const row = S.roster.filter((r) => r.tool?.id === toolId && r.hire.status !== "fired").pop();
  const draft = row?.hire.shadow_preview?.find((e) => e.draft);
  const j = job(t.job);
  let replay = null;
  try { replay = await api(`/api/businesses/${S.biz.id}/tools/${toolId}/replay`); } catch { /* tool has no replay for this business */ }
  sheet.innerHTML = html`
    <header class="sticky top-0 z-10 bg-surface/90 backdrop-blur-xl border-b border-surface-container-high/60">
      <div class="h-14 px-4 flex items-center gap-3 max-w-md mx-auto">
        <button id="sheet-close" aria-label="Close" class="w-9 h-9 rounded-full hover:bg-surface-container flex items-center justify-center">${icon("arrow_back")}</button>
        <span class="font-headline-sm text-[15px] uppercase tracking-tight font-bold">Tool dossier &amp; shadow test</span>
      </div>
    </header>
    <div class="max-w-md mx-auto px-4 py-4 flex flex-col gap-5 pb-32">
      <div class="flex items-center gap-2 flex-wrap">
        ${t.lab ? html`<span class="px-2 py-1 rounded-md bg-primary-container text-[#6ffbbe] text-[10px] font-label-badge flex items-center gap-1">${icon("verified", "text-[14px]")} SHOPFLOOR LAB TESTED</span>` : html`<span class="px-2 py-1 rounded-md bg-surface-container text-[10px] font-label-badge">NOT LAB-TESTED YET</span>`}
        ${row ? html`<span class="px-2 py-1 rounded-md text-[10px] font-label-badge ${STATUS[row.hire.status][1]}">${STATUS[row.hire.status][0].toUpperCase()}</span>` : card ? html`<span class="px-2 py-1 rounded-md bg-surface-container-low text-[10px] font-label-badge text-blue-600">READY FOR SHADOWING</span>` : ""}
      </div>
      <div>
        <div class="text-[11px] font-label-badge tracking-wider text-secondary uppercase">${j.tag} · ${t.vendor}</div>
        <h1 class="font-headline-lg-mobile text-headline-lg-mobile mt-1">${t.name}</h1>
        <p class="text-[14px] text-on-surface-variant mt-1">${t.summary}</p>
        <p class="text-[11px] text-on-surface-variant mt-2 flex items-center gap-1">${icon("travel_explore", "text-[14px]")} Discovered on ${SOURCES[t.source] || t.source}. Vendors don't submit themselves.</p>
      </div>

      <section class="rounded-3xl bg-[#0b192c] text-white p-5">
        <div class="flex items-center justify-between"><h2 class="font-headline-sm text-[17px] flex items-center gap-2">${icon("visibility", "text-[20px]")} 14-day shadow shift</h2><span class="px-2 py-1 rounded-md bg-[#ff8a00] text-[10px] font-label-badge">FREE</span></div>
        <p class="text-[13px] text-white/80 mt-2">${t.name} reads your live data with read-only access and drafts what it would do, but sends <u>nothing</u> to customers. You review its decisions here before it ever touches the floor.</p>
        ${draft ? html`
          <div class="mt-3 bg-white rounded-2xl p-3 text-on-surface">
            <div class="flex justify-between text-[10px] font-label-badge text-on-surface-variant"><span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-[#10b981]"></span> SIMULATED ACTION</span><span>${new Date(draft.ts).toLocaleString()}</span></div>
            <div class="text-[12px] mt-2 text-on-surface-variant">${draft.event} event</div>
            <div class="mt-1 bg-secondary-fixed/40 rounded-xl p-2.5 text-[13px]"><div class="text-[10px] font-label-badge text-secondary mb-1">DRAFTED, NOT SENT</div>${draft.draft}</div>
            <div class="flex justify-between text-[11px] mt-2"><span class="px-2 py-0.5 rounded bg-[#10b981]/15 text-[#059669] font-label-badge">HELD (SHADOW MODE)</span><span class="text-on-surface-variant">${row.hire.shadow_actions} actions logged · 0 sent</span></div>
          </div>` : ""}
        ${card ? html`<button data-dossier-dir="up" class="mt-4 w-full py-3 rounded-full bg-[#ff8a00] text-white font-label-button flex items-center justify-center gap-2">${icon("play_circle", "text-[20px]")} Start 14-day shadow shift</button>` : ""}
      </section>

      ${replay ? html`
      <section class="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/30">
        <div class="flex items-center justify-between"><h2 class="font-headline-sm text-[17px]">90-day backtest replay</h2><span class="text-[10px] font-label-badge px-2 py-1 rounded-md bg-surface-container">YOUR DATA</span></div>
        <div class="grid grid-cols-2 gap-2 mt-3">
          <div><div class="text-[11px] text-on-surface-variant">Times it would have acted</div><div class="font-label-data-lg text-label-data-lg">${replay.actions.toLocaleString()}</div></div>
          ${card ? html`<div class="text-right"><div class="text-[11px] text-on-surface-variant">Estimated value</div><div class="font-label-data-lg text-label-data-lg text-secondary">+${usd(card.monthly_value_usd)}/mo</div></div>` : ""}
        </div>
        ${hourlyChart(replay)}
        ${card ? html`<p class="text-[12px] text-on-surface-variant mt-3">${card.body}</p>` : ""}
      </section>` : ""}

      <section>
        <h2 class="font-headline-sm text-[17px] flex items-center gap-2">${icon("science", "text-[20px]")} Golden-set benchmark</h2>
        ${t.lab ? html`
          <div class="grid grid-cols-3 gap-2 mt-2">
            ${[["Accuracy", pct(t.lab.accuracy)], ["Latency p50", t.lab.p50_latency_s.toFixed(2) + "s"], ["Cost / resolved", Number.isFinite(t.lab.cost_per_resolved_usd) ? "$" + t.lab.cost_per_resolved_usd.toFixed(5) : "n/a"]].map(([k, v]) => html`
              <div class="bg-surface-container-lowest rounded-xl p-3 border border-outline-variant/30"><div class="font-label-data-md text-label-data-md">${v}</div><div class="text-[11px] text-on-surface-variant">${k}</div></div>`)}
          </div>
          <p class="text-[11px] text-on-surface-variant mt-1.5">${t.lab.n_tasks} tasks · graded by ${t.lab.model ? "an independent judge model" : "judge"}</p>
          ${t.lab.failures.length ? html`<div class="mt-2 flex flex-col gap-1.5">${t.lab.failures.map((f) => html`<div class="text-[12px] bg-error-container/50 rounded-lg px-2.5 py-1.5"><b>${f.task}</b>: ${f.reason}</div>`)}</div>` : ""}`
        : html`<p class="text-[13px] text-on-surface-variant mt-2">Not tested yet. Run the lab from <b>Outcomes &amp; Lab</b>.</p>`}
      </section>

      <section>
        <h2 class="font-headline-sm text-[17px] flex items-center gap-2">${icon("hub", "text-[20px]")} Integration mesh <span class="text-[11px] font-normal text-on-surface-variant">${t.integrations.length} connections</span></h2>
        <div class="flex flex-col gap-2 mt-2">
          ${t.integrations.map((c) => html`
            <div class="flex items-center gap-3 bg-surface-container-lowest rounded-xl p-3 border border-outline-variant/30">
              <div class="w-9 h-9 rounded-lg bg-primary-container text-white flex items-center justify-center">${icon((CONNECTORS[c] || [])[1] || "link", "text-[18px]")}</div>
              <div class="flex-1"><div class="text-[13px] font-bold">${connName(c)}</div><div class="text-[11px] text-on-surface-variant">${(CONNECTORS[c] || [])[2] || ""}</div></div>
              <span class="text-[10px] font-label-badge px-2 py-1 rounded bg-surface-container">${row?.hire.status === "hired" ? "READ + WRITE" : "READ-ONLY IN SHADOW"}</span>
            </div>`)}
        </div>
      </section>

      <section class="bg-surface-container-low rounded-2xl p-4 border border-surface-container">
        <div class="flex justify-between items-center"><h2 class="font-headline-sm text-[17px]">Transparent billing</h2><span class="text-[10px] font-label-badge text-on-surface-variant">NO HIDDEN FEES</span></div>
        <div class="flex justify-between text-[13px] mt-3"><span>${t.name} license</span><b>${usd(t.price_usd_month)}/mo</b></div>
        <div class="flex justify-between text-[13px] mt-1"><span>14-day shadow shift</span><b>Free</b></div>
        <div class="mt-3 bg-surface-container-lowest rounded-xl p-3 flex items-center gap-3">${icon("power_settings_new", "text-error")}<div><div class="text-[13px] font-bold">One-tap fire</div><div class="text-[11px] text-on-surface-variant">Revokes access, exports your data and cancels billing at once.</div></div></div>
      </section>
    </div>
    ${card ? html`
    <div class="fixed bottom-0 inset-x-0 bg-surface/95 backdrop-blur border-t border-surface-container-high p-3 pb-safe">
      <div class="max-w-md mx-auto grid grid-cols-3 gap-2">
        <button data-dossier-dir="left" class="py-3 rounded-full bg-surface-container text-red-600 font-label-button">Pass</button>
        <button data-dossier-dir="up" class="py-3 rounded-full bg-amber-500 text-white font-label-button">Shadow</button>
        <button data-dossier-dir="right" class="py-3 rounded-full bg-[#10b981] text-white font-label-button">Hire</button>
      </div>
    </div>` : ""}`.s;
  sheet.classList.remove("hidden");
  sheet.scrollTop = 0;
  const close = () => { sheet.classList.add("hidden"); sheet.innerHTML = ""; };
  $("#sheet-close").onclick = close;
  $("#sheet-close").focus();
  sheet.onkeydown = (e) => e.key === "Escape" && close();
  sheet.querySelectorAll("[data-dossier-dir]").forEach((b) => (b.onclick = async () => { close(); await swipe(b.dataset.dossierDir, card.id); }));
}

function hourlyChart(replay) {
  const hours = [...Array(14).keys()].map((i) => i + 9); // 9am-10pm
  const vals = hours.map((h) => replay.hourly[h]);
  const max = Math.max(1, ...vals);
  const W = 300, H = 110, bw = W / hours.length;
  const label = (h) => (h % 12 || 12) + (h < 12 ? "a" : "p");
  return html`
    <div class="mt-3">
      <div class="flex justify-between text-[10px] font-label-badge text-on-surface-variant"><span>WHEN IT WOULD HAVE ACTED (BY HOUR)</span>${replay.peak_hour != null ? html`<span class="text-secondary">PEAK ${label(replay.peak_hour)}</span>` : ""}</div>
      <svg viewBox="0 0 ${W} ${H + 16}" class="w-full mt-1" role="img" aria-label="Hourly distribution, peak at ${replay.peak_hour}:00">
        ${hours.map((h, i) => {
          const bh = (vals[i] / max) * H;
          return raw(`<rect x="${i * bw + 2}" y="${H - bh}" width="${bw - 4}" height="${bh}" rx="3" fill="${h === replay.peak_hour ? "#ff8a00" : "#bac7e1"}"><title>${label(h)}: ${vals[i]}</title></rect>`
            + (i % 3 === 0 ? `<text x="${i * bw + bw / 2}" y="${H + 12}" font-size="9" text-anchor="middle" fill="#44474c">${label(h)}</text>` : ""));
        })}
      </svg>
    </div>`;
}

boot().catch(fail);
