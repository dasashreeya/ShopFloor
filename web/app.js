// ShopFloor UI. Vanilla JS, no build step. Every interpolated value goes through html`` which escapes it.

// ---------- helpers ----------
class Raw { constructor(s) { this.s = s; } }
const raw = (s) => new Raw(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v) => (v instanceof Raw ? v.s : Array.isArray(v) ? v.map(fmt).join("") : v === false || v == null ? "" : esc(v));
const html = (strs, ...vals) => raw(strs.reduce((a, s, i) => a + s + (i < vals.length ? fmt(vals[i]) : ""), ""));
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const usd = (n) => (n == null ? "–" : "$" + Math.round(n).toLocaleString());
const usd2 = (n) => (n == null ? "–" : "$" + (Number.isInteger(Math.round(n * 100) / 100) ? Math.round(n).toLocaleString() : n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })));
const pct = (x) => Math.round(x * 100) + "%";
const icon = (name, cls = "") => html`<span class="material-symbols-outlined ${cls}" aria-hidden="true">${name}</span>`;
const ext = (url, label, cls = "underline underline-offset-2") => html`<a href="${url}" target="_blank" rel="noopener noreferrer" class="${cls}">${label}${icon("open_in_new", "text-[13px] align-[-2px] ml-0.5")}</a>`;

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json", ...(opts.headers || {}) }, ...opts });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : (body.detail?.[0]?.msg || res.statusText));
  return body;
}
const post = (path, body) => api(path, { method: "POST", body: JSON.stringify(body ?? {}) });

function toast(msg, iconName = "check_circle") {
  const t = $("#toast");
  $("#toast-msg").textContent = msg; $("#toast-icon").textContent = iconName;
  t.classList.remove("-translate-y-24", "opacity-0");
  clearTimeout(t.timer); t.timer = setTimeout(() => t.classList.add("-translate-y-24", "opacity-0"), 3000);
}
const fail = (e) => toast(e.message, "error");
const store = { get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
                set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} } };

// ---------- vocabulary ----------
const JOBS = {
  missed_calls: { icon: "phone_in_talk", color: "#ff8a00", label: "Answer missed calls", short: "Missed calls" },
  review_replies: { icon: "reviews", color: "#0ea5e9", label: "Reply to online reviews", short: "Reviews" },
  invoice_chasing: { icon: "receipt_long", color: "#10b981", label: "Chase late invoices", short: "Invoices" },
  email_triage: { icon: "mail", color: "#8b5cf6", label: "Tame the inbox", short: "Email" },
};
const job = (j) => JOBS[j] || { icon: "smart_toy", color: "#64748b", label: j || "Other", short: j || "Other" };
const INDUSTRIES = [["restaurant", "Restaurant"], ["cafe", "Coffee shop / café"], ["hvac", "HVAC"], ["plumbing", "Plumbing"],
  ["landscaping", "Landscaping"], ["cleaning", "Cleaning"], ["electrical", "Electrical"], ["salon", "Salon / spa"],
  ["auto_repair", "Auto repair"], ["fitness", "Fitness studio"], ["retail", "Retail shop"], ["other", "Something else"]];
const SOFTWARE = [["square", "Square"], ["toast", "Toast"], ["clover", "Clover"], ["quickbooks", "QuickBooks Online"], ["xero", "Xero"],
  ["freshbooks", "FreshBooks"], ["jobber", "Jobber"], ["housecall_pro", "Housecall Pro"], ["servicetitan", "ServiceTitan"],
  ["google_workspace", "Google Workspace"], ["gmail", "Gmail"], ["outlook", "Outlook / Microsoft 365"],
  ["google_business", "Google Business Profile"], ["yelp", "Yelp"], ["opentable", "OpenTable"], ["resy", "Resy"], ["calendly", "Calendly"]];
const swName = (k) => (SOFTWARE.find((s) => s[0] === k) || [k, k.replace(/_/g, " ")])[1];
const KIND = { product: ["Product", "bg-soft2 text-ink"], addon: ["Add-on", "bg-soft2 text-ink"], builtin: ["Free · already yours", "bg-emerald-100 text-emerald-800"],
               candidate: ["Auto-discovered · unverified", "bg-amber-100 text-amber-900"] };
const EVIDENCE = { vendor_page: "Vendor pricing page", vendor_help_center: "Vendor help center", secondary_source: "Third-party listing (vendor page unavailable)",
                   llm_extracted: "Auto-extracted by AI, unverified" };
const ORIGIN = (o) => o === "owner" ? ["Your number", "bg-navy text-white"] : o?.startsWith("file") ? [o.replace("file: ", "From "), "bg-navy text-white"]
  : ["Default", "bg-amber-100 text-amber-900"];
const GRADE = { owner: "", published: "Published source", peer_reviewed: "Peer-reviewed", secondary: "Secondary source", assumption: "ShopFloor assumption" };
// Demo stories: composite personas built from the market study (docs/MARKET_STUDY.md). Numbers are typical, not a real business.
const STORIES = {
  elena: { who: "Elena", emoji: "🌶️", role: "Family Mexican restaurant + catering · Riverdale Park, MD", color: "#ef4444", featured: true,
    quote: "Friday nights the phone rings off the hook, 45 Google reviews a month sit unanswered, catering clients pay late, and my inbox is a mess. Half my customers speak Spanish. I can invest $700 a month if it pays off.",
    data: { name: "Casa Elena (demo story)", industry: "restaurant", stack: ["toast", "opentable", "google_business", "gmail", "quickbooks"],
      budget_usd_month: 700, pains: ["missed_calls", "review_replies", "invoice_chasing", "email_triage"], needs: { spanish: true },
      metrics: { calls_per_week: 250, missed_share: 0.35, avg_ticket: 38, reviews_per_month: 45, reply_share: 0.1, monthly_revenue: 110000,
                 invoices_per_month: 25, avg_invoice: 900, late_share: 0.45, email_hours_per_week: 8, email_users: 2, owner_hourly_value: 40,
                 uses_builtin_reminders: false } } },
  maria: { who: "Maria", emoji: "🌮", role: "Family taqueria · College Park, MD", color: "#ff8a00",
    quote: "I lose lunch-rush calls and never have time for Google reviews. Half my regulars speak Spanish. I can spend about $150 a month.",
    data: { name: "Maria's Taqueria (demo story)", industry: "restaurant", stack: ["square", "google_business", "gmail", "quickbooks"],
      budget_usd_month: 150, pains: ["missed_calls", "review_replies"], needs: { spanish: true },
      metrics: { calls_per_week: 160, avg_ticket: 24, reviews_per_month: 20, reply_share: 0.15, monthly_revenue: 48000,
                 invoices_per_month: 8, avg_invoice: 380, late_share: 0.4, email_hours_per_week: 3, owner_hourly_value: 30 } } },
  dev: { who: "Dev", emoji: "🛠️", role: "Two-truck HVAC company · Silver Spring, MD", color: "#10b981",
    quote: "Every missed call in July is a $350 job going to the next guy on Google. I'm on Jobber and QuickBooks and I'm not adding another login.",
    data: { name: "Dev's Comfort Air HVAC (demo story)", industry: "hvac", stack: ["jobber", "quickbooks", "google_business", "google_workspace", "gmail"],
      budget_usd_month: 300, pains: ["missed_calls", "invoice_chasing"], needs: { human_handoff: true },
      metrics: { calls_per_week: 60, avg_ticket: 350, reviews_per_month: 8, invoices_per_month: 70, avg_invoice: 620, late_share: 0.35,
                 email_hours_per_week: 6, owner_hourly_value: 45, uses_builtin_reminders: false } } },
  keisha: { who: "Keisha", emoji: "💇🏾‍♀️", role: "Two-chair salon · Hyattsville, MD", color: "#8b5cf6",
    quote: "I can't pick up the phone when I'm mid-color. I've got $60 a month, tops. Tell me straight if something isn't worth it.",
    data: { name: "Keisha's Studio (demo story)", industry: "salon", stack: ["square", "google_business", "gmail"],
      budget_usd_month: 60, pains: ["missed_calls", "review_replies"], needs: {},
      metrics: { calls_per_week: 50, missed_share: 0.3, avg_ticket: 85, reviews_per_month: 6, reply_share: 0.5, email_hours_per_week: 2 } } },
};
function startStory(key) {
  store.set("sf.story", key); S.biz = null; S.rec = null; S.picks = [];
  draft = structuredClone(STORIES[key].data); submitIntake();
}
function storyCards(dark = false) {
  return html`<div class="grid gap-2.5 sm:grid-cols-3">${Object.entries(STORIES).map(([k, st]) => html`
    <button type="button" class="text-left rounded-2xl p-3.5 flex flex-col gap-1.5 transition-transform active:scale-[.98] ${st.featured ? "sm:col-span-3 ring-2 ring-[#ff8a00]" : ""} ${dark ? "bg-white/10 hover:bg-white/15" : "bg-white border border-soft2 hover:border-line"}" data-example="${k}">
      ${st.featured ? html`<span class="badge bg-[#ff8a00] text-[#2f1500] self-start">Full demo · all 4 jobs</span>` : ""}
      <div class="flex items-center gap-2.5"><span class="w-10 h-10 rounded-full flex items-center justify-center text-[20px]" style="background:${st.color}33">${st.emoji}</span>
        <div class="min-w-0"><div class="font-head font-bold text-[15px]">${st.who}</div><div class="text-[11.5px] ${dark ? "text-white/70" : "text-muted"} truncate">${st.role}</div></div></div>
      <p class="text-[12.5px] leading-snug ${dark ? "text-white/85" : "text-ink/80"}">“${st.quote}”</p>
      <span class="text-[12px] font-semibold ${dark ? "text-[#ffb77f]" : "text-accent"}">${icon("swipe", "text-[16px] align-[-4px]")} Swipe as ${st.who} →</span>
    </button>`)}</div>`;
}
const currentStory = () => { const k = store.get("sf.story"); return S.biz && k && STORIES[k] && S.biz.name === STORIES[k].data.name ? STORIES[k] : null; };

// ---------- state ----------
const S = { biz: null, rec: null, catalog: [], research: null, picks: [], compare: new Set(), browseJob: "all", q: "" };

async function boot() {
  window.addEventListener("hashchange", render);
  const saved = store.get("sf.biz");
  if (saved) S.biz = await api(`/api/businesses/${saved}`).catch(() => null);
  const [cat, res] = await Promise.all([api("/api/catalog"), api("/api/research")]);
  S.catalog = cat.tools; S.research = res;
  if (S.biz) await refresh();
  if (!S.biz && (!location.hash || location.hash === "#swipe")) {
    // First visit: load the featured demo story so the swipe deck is there immediately.
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
    return startStory("elena");
  }
  if (!S.biz && !["#browse", "#research"].includes(location.hash)) location.hash = "#start";
  render();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}

async function refresh() {
  if (!S.biz) return;
  const [rec, picks] = await Promise.all([api(`/api/businesses/${S.biz.id}/recommendations`), api(`/api/businesses/${S.biz.id}/picks`)]);
  S.rec = rec; S.biz = rec.business; S.picks = picks;
}

function render() {
  let view = (location.hash || "#swipe").slice(1).split("/")[0];
  if (!S.biz && ["foryou", "swipe", "mytools", "profile"].includes(view)) view = "start";
  if (view === "start" || view === "profile") draft = null;
  $$(".nav-link").forEach((a) => { const on = a.dataset.view === view; a.classList.toggle("active", on); on ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"); });
  $("#biz-line").textContent = S.biz ? `${S.biz.name} · ${(INDUSTRIES.find((i) => i[0] === S.biz.industry) || [, ""])[1]}` : "AI tools, scored on your numbers";
  ({ start: renderStart, profile: renderStart, foryou: renderForYou, swipe: renderSwipe, browse: renderBrowse, mytools: renderMyTools, research: renderResearch }[view] || renderForYou)();
  window.scrollTo(0, 0);
}
const view = (h) => { $("#view").innerHTML = h.s; };

// ---------- intake ----------
let draft = null;
function renderStart() {
  const editing = !!S.biz;
  draft = draft || (editing ? structuredClone({ ...S.biz }) : structuredClone(STORIES.elena.data));  // new visitors start from the demo story
  const d = draft, m = d.metrics || (d.metrics = {});
  const chips = (list, sel, attr) => list.map(([k, l]) => html`<button type="button" class="chip" data-${attr}="${k}" aria-pressed="${String(sel(k))}">${l}</button>`);
  const num = (key, label, hint = "", opts = {}) => html`
    <label class="block"><span class="text-[13px] font-semibold">${label}</span>
      <input class="field mt-1" inputmode="decimal" data-m="${key}" data-kind="${opts.kind || "num"}" value="${m[key] == null ? "" : opts.kind === "pct" ? Math.round(m[key] * 100) : m[key]}" placeholder="${opts.ph || "Leave blank if unsure"}"/>
      ${hint ? html`<span class="text-[11.5px] text-muted">${hint}</span>` : ""}</label>`;
  const want = (j) => d.pains.includes(j) || !d.pains.length;
  view(html`
    <section aria-labelledby="start-title">
      ${editing ? "" : html`
        <div class="card p-5 bg-navy text-white border-0 mb-4">
          <p class="badge bg-white/15 text-white">For small business owners</p>
          <h1 id="start-title" class="font-head text-[26px] leading-tight font-bold mt-2">Which AI tools are worth it for <em>your</em> business?</h1>
          <p class="text-[14px] text-white/80 mt-2">Tell us about your shop in 2 minutes. We compare ${S.research?.stats.tools || ""} researched AI tools on <b>your</b> numbers, your budget and the software you already pay for, with real prices and real reviews (good and bad).</p>
          <p class="font-head font-bold text-[15px] mt-5 mb-2">Try it as a real-world owner</p>
          ${storyCards(true)}
          <p class="text-[11px] text-white/60 mt-2">Demo stories are composites built from our market study (typical numbers, not real businesses). The form below is pre-filled with Elena's numbers: change anything, or just tap the orange button.</p>
        </div>`}
      ${editing ? html`<h1 id="start-title" class="font-head text-[22px] font-bold mb-3">Your business profile</h1>` : ""}
      <form id="intake" class="flex flex-col gap-5" novalidate>
        <fieldset class="card p-4 flex flex-col gap-3"><legend class="font-head font-bold text-[16px] px-1">1 · About you</legend>
          <label class="block"><span class="text-[13px] font-semibold">Business name</span><input class="field mt-1" id="f-name" required value="${d.name}" placeholder="e.g. Rosa's Tacos"/></label>
          <div><span class="text-[13px] font-semibold">Industry</span><div class="flex flex-wrap gap-2 mt-1.5" role="group" aria-label="Industry">${chips(INDUSTRIES, (k) => d.industry === k, "ind")}</div></div>
        </fieldset>
        <fieldset class="card p-4 flex flex-col gap-3"><legend class="font-head font-bold text-[16px] px-1">2 · Software you already use</legend>
          <p class="text-[12.5px] text-muted -mt-1">We check compatibility, and we'll tell you when something you already pay for does the job for free.</p>
          <div class="flex flex-wrap gap-2" role="group" aria-label="Software you use">${chips(SOFTWARE, (k) => d.stack.includes(k), "sw")}</div>
        </fieldset>
        <fieldset class="card p-4 flex flex-col gap-3"><legend class="font-head font-bold text-[16px] px-1">3 · What would help most?</legend>
          <div class="flex flex-wrap gap-2" role="group" aria-label="Problems to solve">${chips(Object.entries(JOBS).map(([k, v]) => [k, v.label]), (k) => d.pains.includes(k), "pain")}</div>
          <div class="grid sm:grid-cols-2 gap-3">
            <label class="block"><span class="text-[13px] font-semibold">Monthly budget for new tools ($)</span>
              <input class="field mt-1" id="f-budget" inputmode="decimal" value="${d.budget_usd_month ?? ""}" placeholder="No limit"/></label>
            <div><span class="text-[13px] font-semibold">Must-haves</span>
              <div class="flex flex-wrap gap-2 mt-1">
                <button type="button" class="chip" data-need="spanish" aria-pressed="${String(!!d.needs.spanish)}">Speaks Spanish</button>
                <button type="button" class="chip" data-need="human_handoff" aria-pressed="${String(!!d.needs.human_handoff)}">Hands off to a human</button></div></div>
          </div>
        </fieldset>
        <fieldset class="card p-4 flex flex-col gap-3"><legend class="font-head font-bold text-[16px] px-1">4 · Your numbers</legend>
          <p class="text-[12.5px] text-muted -mt-1">Rough is fine. Blank means "I don't know": we'll use a published average where one exists and tell you we did, or ask. Faster: upload an export below.</p>
          <div class="grid sm:grid-cols-2 gap-3">
            ${want("missed_calls") ? [num("calls_per_week", "Phone calls per week"), num("missed_share", "% of calls nobody answers", "Unsure? We'll use published averages (28-62%).", { kind: "pct" }),
                                       num("avg_ticket", "Average order or job value ($)", d.industry === "hvac" || d.industry === "plumbing" ? "Blank = Angi's typical HVAC repair (~$350)" : "")] : ""}
            ${want("review_replies") ? [num("reviews_per_month", "New online reviews per month"), num("reply_share", "% of reviews you reply to", "", { kind: "pct" }),
                                        num("monthly_revenue", "Monthly revenue ($)", "Used for the rating-to-revenue effect")] : ""}
            ${want("invoice_chasing") ? [num("invoices_per_month", "Invoices sent per month"), num("avg_invoice", "Average invoice ($)"), num("late_share", "% of invoices paid late", "", { kind: "pct" })] : ""}
            ${want("email_triage") ? [num("email_hours_per_week", "Hours a week on email"), num("email_users", "People who'd use an email tool", "", { ph: "1" })] : ""}
            ${num("owner_hourly_value", "What an hour of your time is worth ($)", "Default $30", { ph: "30" })}
            ${num("gross_margin", "Gross margin % (what you keep after direct costs)", "Blank = industry default, shown with its source", { kind: "pct" })}
          </div>
          ${want("invoice_chasing") ? html`<label class="flex items-center gap-2 text-[13px]"><input type="checkbox" id="f-builtin" class="rounded" ${m.uses_builtin_reminders ? "checked" : ""}/> I already use automatic invoice reminders in QuickBooks/Xero</label>` : ""}
        </fieldset>
        ${editing ? importPanel() : ""}
        <div class="sticky bottom-20 z-10"><button class="btn btn-accent w-full shadow-xl" id="f-submit">${icon("auto_awesome", "text-[18px]")} ${editing ? "Save and update my recommendations" : "Show my recommendations"}</button></div>
        ${editing ? html`<button type="button" id="f-reset" class="btn btn-ghost w-full">${icon("restart_alt", "text-[18px]")} Start over as a new business</button>` : ""}
      </form>
    </section>`);
  const toggle = (arr, k) => (arr.includes(k) ? arr.filter((x) => x !== k) : [...arr, k]);
  const sync = () => {
    d.name = $("#f-name").value; const b = $("#f-budget").value.trim(); d.budget_usd_month = b === "" ? null : Number(b.replace(/[$,]/g, ""));
    $$("[data-m]").forEach((i) => { const v = i.value.trim().replace(/[$,%]/g, ""); m[i.dataset.m] = v === "" || isNaN(Number(v)) ? null : i.dataset.kind === "pct" ? Number(v) / 100 : Number(v); });
    if ($("#f-builtin")) m.uses_builtin_reminders = $("#f-builtin").checked;
  };
  $$("[data-ind]").forEach((b) => (b.onclick = () => { sync(); d.industry = b.dataset.ind; renderStart(); }));
  $$("[data-sw]").forEach((b) => (b.onclick = () => { d.stack = toggle(d.stack, b.dataset.sw); b.setAttribute("aria-pressed", d.stack.includes(b.dataset.sw)); }));
  $$("[data-pain]").forEach((b) => (b.onclick = () => { sync(); d.pains = toggle(d.pains, b.dataset.pain); renderStart(); }));
  $$("[data-need]").forEach((b) => (b.onclick = () => { d.needs[b.dataset.need] = !d.needs[b.dataset.need]; b.setAttribute("aria-pressed", !!d.needs[b.dataset.need]); }));
  $$("[data-example]").forEach((b) => (b.onclick = () => startStory(b.dataset.example)));
  if (editing) wireImport();
  $("#f-reset") && ($("#f-reset").onclick = () => { store.set("sf.biz", null); S.biz = null; S.rec = null; draft = null; location.hash = "#start"; render(); });
  $("#intake").onsubmit = (e) => { e.preventDefault(); sync(); if (!editing) store.set("sf.story", d.name === STORIES.elena.data.name ? "elena" : null); submitIntake(); };
}

async function submitIntake() {
  const d = draft;
  if (!d.name?.trim()) { toast("Add your business name", "edit"); $("#f-name")?.focus(); return; }
  if (!d.industry) d.industry = "other";
  const btn = $("#f-submit"); if (btn) btn.disabled = true;
  const editingNow = !!S.biz;
  try {
    const body = { name: d.name, industry: d.industry, stack: d.stack, budget_usd_month: d.budget_usd_month, pains: d.pains, needs: d.needs, metrics: d.metrics };
    S.biz = S.biz ? await api(`/api/businesses/${S.biz.id}`, { method: "PATCH", body: JSON.stringify(body) }) : await post("/api/businesses", body);
    store.set("sf.biz", S.biz.id); draft = null;
    await refresh(); location.hash = "#swipe"; render(); toast("Recommendations ready", "auto_awesome");
  } catch (e) { fail(e); } finally { if (btn) btn.disabled = false; }
}

function importPanel() {
  const kinds = [["calls", "Call log", "From RingCentral, Google Voice, Grasshopper, Dialpad…: needs a date and a status (missed/answered) column", "phone_in_talk"],
                 ["invoices", "Invoice list", "From QuickBooks, Xero or Jobber: amount, due date, paid date or status", "receipt_long"],
                 ["orders", "Sales / orders", "From Square, Toast or Clover: date and total", "point_of_sale"]];
  const src = S.biz?.metric_sources || {};
  const files = [...new Set(Object.values(src).filter((v) => v.startsWith("file")))];
  return html`
    <fieldset class="card p-4 flex flex-col gap-3"><legend class="font-head font-bold text-[16px] px-1">Use your real exports (optional)</legend>
      <p class="text-[12.5px] text-muted -mt-1">We read the file in your browser session, compute a few totals (calls per week, % missed, % late…) and keep only those numbers.</p>
      ${files.length ? html`<p class="text-[12px] text-good font-semibold">${icon("task_alt", "text-[16px] align-[-3px]")} Using numbers from: ${files.map((f) => f.replace("file: ", "")).join(", ")}</p>` : ""}
      ${kinds.map(([k, l, hint, ic]) => html`
        <div class="flex items-center gap-3 border border-soft2 rounded-2xl p-3">
          ${icon(ic, "text-[22px] text-accent")}
          <div class="flex-1 min-w-0"><div class="font-semibold text-[14px]">${l}</div><div class="text-[11.5px] text-muted">${hint} · ${html`<a class="underline" href="/api/templates/${k}.csv">template</a>`}</div></div>
          <label class="btn btn-ghost !min-h-[38px] !px-3 !text-[12.5px] cursor-pointer">${icon("upload", "text-[16px]")} CSV<input type="file" accept=".csv,text/csv" class="sr-only" data-import="${k}"/></label>
        </div>`)}
    </fieldset>`;
}
function wireImport() {
  $$("[data-import]").forEach((inp) => (inp.onchange = async () => {
    const f = inp.files[0]; if (!f) return;
    try {
      const r = await api(`/api/businesses/${S.biz.id}/import/${inp.dataset.import}`, { method: "POST", body: await f.text(), headers: { "Content-Type": "text/csv", "x-filename": f.name } });
      S.biz = r.business; draft = structuredClone(S.biz); await refresh(); toast(r.summary, "upload_file"); renderStart();
    } catch (e) { fail(e); }
  }));
}

// ---------- For you ----------
function statusBadge(st) {
  return { recommend: html`<span class="badge bg-emerald-100 text-emerald-800">Worth it</span>`, use_builtin: html`<span class="badge bg-emerald-100 text-emerald-800">Free option first</span>`,
           no_purchase: html`<span class="badge bg-slate-200 text-slate-800">Don't buy yet</span>`, needs_info: html`<span class="badge bg-amber-100 text-amber-900">Need a number</span>` }[st];
}
function scorePill(score) {
  const c = score >= 75 ? "bg-emerald-600" : score >= 55 ? "bg-navy" : "bg-slate-500";
  return html`<span class="inline-flex flex-col items-center justify-center w-12 h-12 rounded-2xl ${c} text-white shrink-0" title="ShopFloor fit score for your business (out of 100)"><span class="font-head text-[17px] font-bold leading-none">${score}</span><span class="text-[8.5px] uppercase tracking-wide opacity-80">fit</span></span>`;
}
function renderForYou() {
  const r = S.rec; if (!r) return renderStart();
  const st = r.stack;
  const main = r.jobs.filter((j) => j.is_pain || j.status !== "needs_info");
  const later = r.jobs.filter((j) => !main.includes(j));
  view(html`
    <section aria-labelledby="fy-title">
      <h1 id="fy-title" class="font-head text-[22px] font-bold">Recommended for ${S.biz.name}</h1>
      <p class="text-[13px] text-muted mt-0.5">Scored on your numbers, your budget${S.biz.budget_usd_month != null ? ` (${usd(S.biz.budget_usd_month)}/mo)` : ""} and the software you use. <a href="#research" class="underline">How we score</a></p>
      ${deckCards().length ? html`<a href="#swipe" class="btn btn-accent w-full mt-3 shadow-lg">${icon("swipe", "text-[20px]")} Quick decide: swipe through ${deckCards().length} pick${deckCards().length === 1 ? "" : "s"}</a>` : ""}
      <div class="card p-4 mt-3 bg-navy text-white border-0">
        <div class="flex items-center justify-between gap-2"><span class="badge bg-white/15 text-white">Your starter stack</span>
          <span class="text-[12px] text-white/70">${st.tools.length} tool${st.tools.length === 1 ? "" : "s"}</span></div>
        ${st.tools.length ? html`
          <div class="grid grid-cols-3 gap-2 mt-3 text-center">
            <div><div class="font-head text-[20px] font-bold">${usd(st.monthly_cost)}</div><div class="text-[11px] text-white/70">cost / mo</div></div>
            <div><div class="font-head text-[20px] font-bold text-[#6ffbbe]">~${usd(st.monthly_value)}</div><div class="text-[11px] text-white/70">est. value / mo</div></div>
            <div><div class="font-head text-[20px] font-bold">${usd(st.net_monthly)}</div><div class="text-[11px] text-white/70">net / mo</div></div>
          </div>
          <ul class="mt-3 flex flex-col gap-1.5">${st.tools.map((t) => html`<li class="flex items-center justify-between gap-2 text-[13px] bg-white/10 rounded-xl px-3 py-2"><button class="text-left font-semibold underline-offset-2 hover:underline" data-dossier="${t.tool_id}">${t.name}</button><span class="text-white/80 shrink-0">${t.monthly_cost ? usd2(t.monthly_cost) + "/mo" : "Free"}</span></li>`)}</ul>
          ${st.swaps.length ? html`<p class="text-[11.5px] text-amber-200 mt-2">${icon("info", "text-[14px] align-[-3px]")} ${st.swaps.join(" · ")}</p>` : ""}
          <p class="text-[11px] text-white/60 mt-2">Estimates, not guarantees. Every number is explained on each card. Start with a trial and check in after 30 days.</p>`
        : html`<p class="text-[13px] text-white/80 mt-2">Nothing clears the bar yet. See each job below for what would change that.</p>`}
      </div>
      <div class="flex flex-col gap-4 mt-4">${main.map(jobCard)}</div>
      ${later.length ? html`<details class="card p-4 mt-4"><summary class="flex items-center justify-between font-semibold text-[14px]">
        <span>${icon("add_circle", "text-[18px] align-[-4px]")} We could also look at: ${later.map((j) => j.label.toLowerCase()).join(", ")}</span>${icon("expand_more", "chev")}</summary>
        <div class="flex flex-col gap-4 mt-3">${later.map(jobCard)}</div></details>` : ""}
      ${sbaPanel()}
    </section>`);
  wireJobCards();
}

function jobCard(j) {
  const J = job(j.job), top = j.top;
  const alts = (j.options || []).filter((o) => !top || o.tool_id !== top.tool_id);
  return html`
    <article class="card overflow-hidden" aria-labelledby="job-${j.job}">
      <div class="h-1.5" style="background:${J.color}"></div>
      <div class="p-4 flex flex-col gap-3">
        <div class="flex items-center justify-between gap-2">
          <h2 id="job-${j.job}" class="flex items-center gap-2 font-head font-bold text-[16px]">${icon(J.icon, "text-[20px]")} ${j.label}</h2>
          <div class="flex items-center gap-1.5">${j.is_pain ? html`<span class="badge bg-soft2 text-ink">You asked</span>` : ""}${statusBadge(j.status)}</div>
        </div>
        ${j.facts.length ? html`<ul class="text-[13px] text-muted flex flex-col gap-0.5">${j.facts.map((f) => html`<li>• ${f}</li>`)}</ul>` : ""}
        ${j.status === "needs_info" ? missingForm(j) : ""}
        ${top ? optionBlock(top, true) : ""}
        ${j.status === "no_purchase" ? html`
          <div class="rounded-2xl bg-soft p-3 text-[13.5px]"><b>${j.headline}</b>
            ${j.breakeven ? html`<div class="mt-2"><div class="bar" role="img" aria-label="You have ${Math.round(j.breakeven.have)} of the ${Math.ceil(j.breakeven.needed)} needed"><span style="width:${Math.min(100, (j.breakeven.have / j.breakeven.needed) * 100)}%"></span></div>
              <div class="text-[11.5px] text-muted mt-1">You: ~${Math.round(j.breakeven.have)} · break-even: ~${Math.ceil(j.breakeven.needed)} ${j.breakeven.unit}</div></div>` : ""}</div>` : ""}
        ${j.status !== "needs_info" ? html`
          <details class="rounded-2xl border border-soft2"><summary class="p-3 flex items-center justify-between text-[13px] font-semibold">
            <span>${icon("calculate", "text-[18px] align-[-4px]")} How we estimated this</span>${icon("expand_more", "chev")}</summary>
            <div class="px-3 pb-3">${inputsTable(j.inputs)}
              ${j.calibration?.n ? html`<p class="text-[11.5px] text-good mt-2">Adjusted ×${j.calibration.factor} from ${j.calibration.n} owner check-ins.</p>` : html`<p class="text-[11.5px] text-muted mt-2">No owner check-ins for this job yet, so it's uncalibrated.</p>`}</div>
          </details>` : ""}
        ${alts.length ? html`
          <details class="rounded-2xl border border-soft2"><summary class="p-3 flex items-center justify-between text-[13px] font-semibold">
            <span>${icon("compare_arrows", "text-[18px] align-[-4px]")} ${alts.length} other option${alts.length === 1 ? "" : "s"} compared</span>${icon("expand_more", "chev")}</summary>
            <div class="px-3 pb-3 flex flex-col gap-2">${alts.map((o) => optionBlock(o, false))}
              <button class="btn btn-ghost !min-h-[38px] !text-[12.5px]" data-compare-job="${j.job}">${icon("table_chart", "text-[16px]")} Side-by-side table</button></div>
          </details>` : ""}
        ${j.disqualified?.length ? html`
          <details class="rounded-2xl border border-soft2"><summary class="p-3 flex items-center justify-between text-[13px] font-semibold text-muted">
            <span>${icon("block", "text-[18px] align-[-4px]")} ${j.disqualified.length} ruled out for you</span>${icon("expand_more", "chev")}</summary>
            <ul class="px-3 pb-3 text-[12.5px] flex flex-col gap-1">${j.disqualified.map((d) => html`<li><button class="font-semibold underline" data-dossier="${d.tool_id}">${d.name}</button>: ${d.reasons.join("; ")}</li>`)}</ul>
          </details>` : ""}
      </div>
    </article>`;
}

function optionBlock(o, isTop) {
  const dec = o.decision;
  return html`
    <div class="rounded-2xl ${isTop ? "bg-soft border border-soft2 p-3.5" : "border border-soft2 p-3"}">
      <div class="flex items-start gap-3">
        ${scorePill(o.score)}
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-1.5 flex-wrap"><button class="font-head font-bold text-[15.5px] text-left hover:underline" data-dossier="${o.tool_id}">${o.name}</button>
            ${o.kind === "builtin" ? html`<span class="badge ${KIND.builtin[1]}">${KIND.builtin[0]}</span>` : ""}
            ${o.evidence.strength === "thin" && o.kind !== "builtin" ? html`<span class="badge bg-amber-100 text-amber-900" title="Fewer than 20 independent ratings">Thin evidence</span>` : ""}</div>
          <div class="text-[12px] text-muted">${o.vendor} · ${o.plan}${o.cost_note ? ` · ${o.cost_note}` : ""}</div>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-2 mt-3 text-center">
        <div class="bg-white rounded-xl p-2"><div class="font-head font-bold text-[15px]">${o.monthly_cost == null ? "Quote" : o.monthly_cost === 0 ? "Free" : usd2(o.monthly_cost)}</div><div class="text-[10.5px] text-muted">cost / mo for you</div></div>
        <div class="bg-white rounded-xl p-2"><div class="font-head font-bold text-[15px] text-good">~${usd(o.monthly_value)}</div><div class="text-[10.5px] text-muted">value ${usd(o.monthly_value_low)}–${usd(o.monthly_value_high)}</div></div>
        <div class="bg-white rounded-xl p-2"><div class="font-head font-bold text-[15px] ${o.net_monthly > 0 ? "" : "text-bad"}">${o.net_monthly == null ? "?" : usd(o.net_monthly)}</div><div class="text-[10.5px] text-muted">net / mo</div></div>
      </div>
      ${isTop ? html`
        <details class="mt-2"><summary class="text-[12.5px] font-semibold text-accent py-1">Why ${o.score}/100? ${icon("expand_more", "chev text-[16px] align-[-4px]")}</summary>${breakdown(o.breakdown)}</details>
        <div class="text-[12px] text-muted mt-1">${o.trial ? html`<span>${icon("schedule", "text-[14px] align-[-3px]")} ${o.trial}</span>` : ""}${o.contract ? html` · <span>${o.contract}</span>` : ""}</div>
        ${o.unconfirmed_needs?.length ? html`<p class="text-[12px] text-warn mt-1">${icon("help", "text-[14px] align-[-3px]")} Not confirmed by the vendor: ${o.unconfirmed_needs.join(", ")}. Ask before you buy.</p>` : ""}
        <div class="flex gap-2 mt-3">
          ${dec ? html`<a href="#mytools" class="btn btn-ghost flex-1">${icon("check", "text-[18px]")} ${dec === "passed" ? "Passed" : dec === "trial" ? "Trying it" : dec === "adopted" ? "Using it" : "Cancelled"}</a>`
            : html`<button class="btn btn-primary flex-1" data-act="trial" data-tool="${o.tool_id}">${icon("play_arrow", "text-[18px]")} ${o.kind === "builtin" ? "Set it up" : "Start a trial"}</button>
                   <button class="btn btn-ghost" data-act="pass" data-tool="${o.tool_id}" aria-label="Pass on ${o.name}">Pass</button>`}
          <button class="btn btn-ghost" data-dossier="${o.tool_id}" aria-label="Details for ${o.name}">${icon("info", "text-[18px]")}</button>
        </div>` : html`<p class="text-[11.5px] text-muted mt-2">${o.breakdown.value.why[0]} · ${o.breakdown.evidence.why[0]}</p>`}
    </div>`;
}

function breakdown(b) {
  const rows = [["value", "Value for you"], ["fit", "Fit with your business"], ["evidence", "Customer evidence"], ["transparency", "Price & terms transparency"]];
  return html`<div class="flex flex-col gap-2.5 mt-2">${rows.map(([k, l]) => html`
    <div><div class="flex justify-between text-[12.5px] font-semibold"><span>${l}</span><span>${Math.round(b[k].points)}/${b[k].max}</span></div>
      <div class="bar mt-1"><span style="width:${(b[k].points / b[k].max) * 100}%"></span></div>
      <ul class="text-[11.5px] text-muted mt-1">${b[k].why.map((w) => html`<li>• ${w}</li>`)}</ul></div>`)}</div>`;
}

function inputsTable(inputs) {
  return html`<table class="w-full text-[12.5px] mt-1"><caption class="sr-only">Inputs used</caption><tbody>${inputs.map((i) => {
    const [ol, oc] = ORIGIN(i.origin);
    return html`<tr class="border-t border-soft2 align-top"><td class="py-1.5 pr-2">${i.label}${i.note ? html`<div class="text-[11px] text-muted">${i.note}</div>` : ""}
      ${(i.sources || []).map((s) => html`<div class="text-[11px]">${ext(s.url, s.title, "underline text-muted")}</div>`)}</td>
      <td class="py-1.5 pr-2 font-semibold whitespace-nowrap">${i.value}</td>
      <td class="py-1.5 text-right"><span class="badge ${oc}">${ol}</span>${i.grade && GRADE[i.grade] && i.origin !== "owner" ? html`<div class="text-[10px] text-muted mt-0.5">${GRADE[i.grade]}</div>` : ""}</td></tr>`;
  })}</tbody></table>`;
}

function missingForm(j) {
  return html`<form class="rounded-2xl bg-amber-50 border border-amber-200 p-3 flex flex-col gap-2" data-missing="${j.job}">
    <p class="text-[13px]">We won't guess these. Add them to see your options:</p>
    ${j.missing.map((m) => html`<label class="block"><span class="text-[12.5px] font-semibold">${m.label}</span><input class="field mt-1" inputmode="decimal" name="${m.field}"/></label>`)}
    <button class="btn btn-primary">Update</button></form>`;
}

function wireJobCards() {
  $$("[data-dossier]").forEach((b) => (b.onclick = () => openDossier(b.dataset.dossier)));
  $$("[data-act]").forEach((b) => (b.onclick = () => decide(b.dataset.tool, b.dataset.act, b)));
  $$("[data-compare-job]").forEach((b) => (b.onclick = () => openCompareJob(b.dataset.compareJob)));
  $$("[data-missing]").forEach((f) => (f.onsubmit = async (e) => {
    e.preventDefault();
    const metrics = {}; new FormData(f).forEach((v, k) => { const n = Number(String(v).replace(/[$,]/g, "")); if (String(v).trim() && !isNaN(n)) metrics[k] = n; });
    try { await api(`/api/businesses/${S.biz.id}`, { method: "PATCH", body: JSON.stringify({ metrics }) }); await refresh(); render(); toast("Updated", "auto_awesome"); } catch (err) { fail(err); }
  }));
}

async function decide(toolId, action, btn) {
  if (btn) btn.disabled = true;
  try {
    await post(`/api/businesses/${S.biz.id}/picks`, { tool_id: toolId, action });
    await refresh();
    if (action === "pass") { toast("Passed. It stays in Browse if you change your mind.", "do_not_disturb_on"); render(); }
    else { toast("Added to My tools with a setup checklist", "checklist"); location.hash = "#mytools"; }
  } catch (e) { fail(e); if (btn) btn.disabled = false; }
}

// ---------- swipe deck ----------
// One card per job: the best option the owner hasn't decided on yet. Pass on it and the next-best one appears.
function deckCards() {
  if (!S.rec) return [];
  const out = [];
  for (const j of S.rec.jobs) {
    if (!["recommend", "use_builtin"].includes(j.status)) continue;
    const decided = (j.options || []).some((o) => ["trial", "adopted"].includes(o.decision));
    if (decided) continue;
    const next = (j.options || []).find((o) => !o.decision && o.net_monthly != null && o.net_monthly > 0);
    if (next) out.push({ job: j, o: next });
  }
  return out;
}
function swipeCardHTML({ job: j, o }, pos) {
  const J = job(j.job), t = S.catalog.find((x) => x.id === o.tool_id) || {};
  if (pos > 0) return html`<div class="h-full rounded-[28px]" style="background:linear-gradient(160deg, ${J.color}33, #ffffff 45%)"></div>`;
  const good = (t.reviews || []).find((r) => r.relevant && (r.stars ?? 5) >= 4);
  const bad = (t.reviews || []).find((r) => r.relevant && r.stars != null && r.stars <= 2);
  const roi = o.monthly_cost > 0 ? o.monthly_value / o.monthly_cost : null;
  const stamp = (dir, label, cls, where) => html`<div class="stamp ${cls} absolute ${where} z-50 px-4 py-1.5 rounded-xl font-head text-[24px] font-black tracking-widest uppercase" data-stamp="${dir}">${label}</div>`;
  const rating = (t.ratings || []).find((r) => r.count > 0 && r.score != null);
  return html`
    ${stamp("right", o.kind === "builtin" ? "SET UP" : "TRY IT", "stamp-hire", "top-[44%] left-6 rotate-[-14deg]")}
    ${stamp("left", "PASS", "stamp-pass", "top-[44%] right-6 rotate-[14deg]")}
    <div class="relative px-5 pt-4 pb-3.5 text-white shrink-0" style="background:linear-gradient(135deg, #0e1c2f 0%, #0e1c2f 55%, ${J.color} 160%)">
      <div class="flex items-center justify-between gap-2">
        <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold bg-white/12 rounded-full pl-1.5 pr-3 py-1" style="background:rgba(255,255,255,.12)">
          <span class="w-6 h-6 rounded-full flex items-center justify-center" style="background:${J.color}">${icon(J.icon, "text-[15px] text-white")}</span>${j.label}</span>
        ${j.is_pain ? html`<span class="badge" style="background:rgba(255,255,255,.15)">You asked</span>` : ""}
      </div>
      <div class="flex items-end justify-between gap-3 mt-3">
        <div class="min-w-0">
          ${o.kind === "builtin" ? html`<span class="badge bg-emerald-400 text-emerald-950">Free · you already have it</span>` : ""}
          <h2 class="font-head font-bold text-[23px] leading-[1.05] mt-1">${o.name}</h2>
          <p class="text-[12px] text-white/70 mt-1 truncate">${o.vendor} · ${o.plan}</p>
        </div>
        <div class="shrink-0 text-center"><div class="w-16 h-16 rounded-2xl bg-white text-ink flex flex-col items-center justify-center shadow-lg">
          <span class="font-head text-[24px] font-bold leading-none">${o.score}</span><span class="text-[9px] uppercase tracking-wider text-muted mt-0.5">fit score</span></div></div>
      </div>
    </div>
    <div class="px-5 py-3.5 flex flex-col gap-2.5 flex-1 min-h-0">
      <div class="flex items-stretch gap-2">
        <div class="flex-1 rounded-2xl bg-emerald-50 border border-emerald-100 p-3">
          <div class="text-[10.5px] uppercase tracking-wider font-bold text-emerald-800">Worth to you</div>
          <div class="font-head text-[26px] font-bold text-good leading-tight">~${usd(o.monthly_value)}<span class="text-[12px] font-semibold">/mo</span></div>
          <div class="text-[11px] text-emerald-900/70">range ${usd(o.monthly_value_low)}–${usd(o.monthly_value_high)}</div></div>
        <div class="w-[38%] rounded-2xl bg-soft p-3">
          <div class="text-[10.5px] uppercase tracking-wider font-bold text-muted">Costs you</div>
          <div class="font-head text-[22px] font-bold leading-tight">${o.monthly_cost === 0 ? "Free" : usd2(o.monthly_cost)}</div>
          <div class="text-[11px] text-muted">${roi ? `${roi.toFixed(1)}× return` : "per month"}</div></div>
      </div>
      <p class="text-[12.5px] leading-snug text-ink/90 line-clamp-3">${j.facts.join(" ")}</p>
      <div class="flex flex-wrap gap-1.5">
        ${o.trial && !/not stated|not verified/i.test(o.trial) ? html`<span class="badge bg-soft2 text-ink !normal-case !tracking-normal !text-[11.5px]">${icon("schedule", "text-[14px]")} ${o.trial}</span>` : ""}
        <span class="badge bg-soft2 text-ink !normal-case !tracking-normal !text-[11.5px]">${icon("star", "text-[14px]")} ${rating ? `${rating.score}★ · ${rating.count.toLocaleString()} on ${rating.platform}` : "No independent ratings yet"}</span>
        ${o.unconfirmed_needs?.length ? html`<span class="badge bg-amber-100 text-amber-900 !normal-case !tracking-normal !text-[11.5px]">${icon("help", "text-[14px]")} ${o.unconfirmed_needs.join(", ")} unconfirmed</span>` : ""}
      </div>
      <div class="rounded-2xl border border-soft2 px-3 py-2.5">
        <div class="text-[10.5px] uppercase tracking-wider font-bold text-muted mb-1">Why this pick</div>
        <ul class="text-[12.5px] flex flex-col gap-0.5">${[o.breakdown.value.why[0], o.breakdown.fit.why.find((w) => /Connects|Made for/.test(w)), ...(o.breakdown.value.why.slice(1, 2))]
          .filter(Boolean).map((w) => html`<li class="flex gap-1.5">${icon("check_circle", "text-[15px] text-good mt-[1px]")}<span>${w.replace(/ \(\d+\/\d+\)$/, "")}</span></li>`)}</ul></div>
      <div class="mt-auto flex flex-col gap-1.5">
        ${good && !bad ? html`<blockquote class="text-[12px] bg-emerald-50 rounded-xl px-3 py-2 line-clamp-2">👍 “${good.quote}” <span class="text-muted">· ${good.author}</span></blockquote>` : ""}
        ${bad ? html`<blockquote class="text-[12px] bg-red-50 rounded-xl px-3 py-2 line-clamp-2">👎 “${bad.quote}” <span class="text-muted">· ${bad.author}</span></blockquote>` : ""}
        ${!good && !bad ? html`<div class="text-[12px] bg-amber-50 rounded-xl px-3 py-2">${o.kind === "builtin" ? "A free feature of software you already pay for: nothing new to buy or learn." : "No independent reviews found yet. We'd rather say so than invent a rating. Try it free first."}</div>` : ""}
      </div>
    </div>`;
}
function renderSwipe() {
  if (!S.rec) return renderStart();
  const cards = deckCards();
  view(html`
    <section aria-labelledby="sw-title" class="max-w-md mx-auto flex flex-col">
      <div class="flex items-center justify-between gap-2">
        <h1 id="sw-title" class="font-head text-[20px] font-bold">Quick decide</h1>
        <div class="flex items-center gap-1.5" aria-label="${cards.length} left">${S.rec.jobs.filter((j) => ["recommend", "use_builtin"].includes(j.status)).map((j) =>
          html`<span class="h-2 rounded-full transition-all ${cards.some((c) => c.job.job === j.job) ? (cards[0].job.job === j.job ? "w-6" : "w-2") : "w-2 opacity-30"}" style="background:${job(j.job).color}"></span>`)}
          <span class="text-[12px] text-muted ml-1">${cards.length ? `${cards.length} left` : "Done"}</span></div></div>
      <p class="text-[12px] text-muted">Right = try it · Left = pass · Tap = details · <a href="#foryou" class="underline">full breakdown</a></p>
      ${currentStory() ? html`<details class="mt-2 rounded-2xl px-3 py-1.5 text-[12.5px]" style="background:${currentStory().color}18"><summary class="flex items-center gap-2"><span class="text-[18px]">${currentStory().emoji}</span><span class="truncate"><b>You're ${currentStory().who}</b> · ${currentStory().role}</span>${icon("expand_more", "chev text-[16px] ml-auto")}</summary>
        <p class="text-muted pb-1.5">“${currentStory().quote}”</p></details>` : ""}
      <div id="card-stack" class="relative w-full mt-3" style="height:min(600px, calc(100dvh - 335px)); min-height:440px"></div>
      <div id="swipe-controls" class="flex items-center justify-center gap-4 mt-3 ${cards.length ? "" : "invisible"}">
        <button class="w-14 h-14 rounded-full bg-white border-2 border-red-200 shadow-lg text-red-500 flex items-center justify-center active:scale-90 transition-transform" data-dir="left" aria-label="Pass">${icon("close", "text-[28px]")}</button>
        <button class="w-12 h-12 rounded-full bg-white border border-line shadow text-ink flex items-center justify-center active:scale-90 transition-transform" data-dir="up" aria-label="See details">${icon("info", "text-[22px]")}</button>
        <button class="w-14 h-14 rounded-full bg-white border-2 border-emerald-200 shadow-lg text-emerald-600 flex items-center justify-center active:scale-90 transition-transform" data-dir="right" aria-label="Start a trial">${icon("favorite", "text-[28px]")}</button>
      </div>
    </section>`);
  const stack = $("#card-stack");
  if (!cards.length) {
    const decided = S.picks.filter((r) => ["trial", "adopted", "passed"].includes(r.pick.status));
    const need = S.rec.jobs.filter((x) => x.status === "needs_info");
    stack.style.height = "auto";
    stack.innerHTML = (decided.length ? html`
      <div class="card p-5 flex flex-col gap-3">
        <div class="text-center">${icon("done_all", "text-[40px] text-accent")}<h2 class="font-head font-bold text-[20px] mt-1">Deck done</h2>
          <p class="text-[13px] text-muted">You decided on ${decided.length} tool${decided.length === 1 ? "" : "s"}. Trials and checklists are in My tools.</p></div>
        <ul class="text-[13px] flex flex-col gap-1">${decided.map((r) => html`<li class="flex justify-between gap-2 bg-soft rounded-xl px-3 py-2"><span>${r.tool?.name}</span><span class="badge ${r.pick.status === "passed" ? "bg-slate-200 text-slate-700" : "bg-emerald-100 text-emerald-800"}">${r.pick.status === "passed" ? "Passed" : "Trying"}</span></li>`)}</ul>
        <div class="flex gap-2"><a href="#mytools" class="btn btn-primary flex-1">My tools</a><a href="#foryou" class="btn btn-ghost flex-1">Full breakdown</a></div>
        <p class="font-head font-bold text-[14px] mt-2">Swipe another owner's story</p>${storyCards()}
      </div>` : html`
      <div class="card p-5 flex flex-col gap-3">
        <div class="text-center">${icon("edit_note", "text-[40px] text-accent")}<h2 class="font-head font-bold text-[20px] mt-1">Nothing to swipe yet</h2>
          <p class="text-[13px] text-muted">${need.length ? "We don't guess. Add a few numbers and your cards appear:" : "Nothing pays for itself at your numbers right now. See why on the full breakdown."}</p></div>
        ${need.length ? html`<ul class="text-[13px] flex flex-col gap-1">${need.flatMap((x) => x.missing).map((m) => html`<li class="bg-amber-50 rounded-xl px-3 py-2">${m.label}</li>`)}</ul>
          <a href="#profile" class="btn btn-primary">${icon("edit", "text-[18px]")} Add my numbers</a>` : html`<a href="#foryou" class="btn btn-primary">See why</a>`}
        <p class="font-head font-bold text-[14px] mt-2">Or swipe as a demo owner</p>${storyCards()}
      </div>`).s;
    $$("[data-example]", stack).forEach((b) => (b.onclick = () => startStory(b.dataset.example)));
    return;
  }
  const visible = cards.slice(0, 3);
  visible.slice().reverse().forEach((c) => {
    const pos = visible.indexOf(c);
    const el = document.createElement("article");
    el.className = `absolute inset-0 rounded-[28px] bg-white shadow-2xl flex flex-col overflow-hidden border border-line/50 ${pos === 0 ? "card-drag cursor-grab" : "pointer-events-none"}`;
    el.style.transform = `translate3d(0, ${pos * 14}px, 0) scale(${1 - pos * 0.05})`;
    el.style.zIndex = String(30 - pos * 5);
    el.style.transition = "transform .3s cubic-bezier(.2,.9,.3,1), opacity .3s ease";
    el.setAttribute("aria-label", `${c.o.name} for ${c.job.label}`);
    el.innerHTML = swipeCardHTML(c, pos).s;
    if (pos === 0) { el.id = "top-card"; attachGestures(el); }
    stack.appendChild(el);
  });
  $$("#swipe-controls [data-dir]").forEach((b) => (b.onclick = () => swipe(b.dataset.dir)));
}
function attachGestures(card) {
  let x0 = null, y0 = 0, dx = 0, dy = 0;
  const stamps = Object.fromEntries($$("[data-stamp]", card).map((s) => [s.dataset.stamp, s]));
  const dirOf = (x, y) => (x > 90 ? "right" : x < -90 ? "left" : y < -90 && Math.abs(x) < 70 ? "up" : null);
  card.addEventListener("pointerdown", (e) => { x0 = e.clientX; y0 = e.clientY; dx = dy = 0; card.setPointerCapture(e.pointerId); card.style.transition = "none"; });
  card.addEventListener("pointermove", (e) => {
    if (x0 == null) return;
    dx = e.clientX - x0; dy = e.clientY - y0;
    card.style.transform = `translate3d(${dx}px, ${dy}px, 0) rotate(${dx * 0.06}deg)`;
    if (stamps.right) stamps.right.style.opacity = dx > 25 ? Math.min((dx - 25) / 80, 1) : 0;
    if (stamps.left) stamps.left.style.opacity = dx < -25 ? Math.min((-dx - 25) / 80, 1) : 0;
    card.style.boxShadow = dx > 25 ? "0 25px 50px -12px rgba(16,185,129,.45)" : dx < -25 ? "0 25px 50px -12px rgba(239,68,68,.45)" : "";
  });
  const end = () => {
    if (x0 == null) return;
    x0 = null;
    card.style.boxShadow = "";
    const dir = dirOf(dx, dy);
    if (dir) return swipe(dir);
    if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return swipe("up"); // a tap opens details
    card.style.transition = "transform .35s cubic-bezier(.175,.885,.32,1.25)";
    card.style.transform = "translate3d(0,0,0)";
    Object.values(stamps).forEach((s) => (s.style.opacity = 0));
  };
  card.addEventListener("pointerup", end);
  card.addEventListener("pointercancel", end);
}
let swiping = false;
async function swipe(dir) {
  const c = deckCards()[0];
  if (!c || swiping) return;
  const top = $("#top-card");
  if (dir === "up") {
    if (top) { top.style.transition = "transform .3s"; top.style.transform = "translate3d(0,0,0)"; $$("[data-stamp]", top).forEach((s) => (s.style.opacity = 0)); }
    return openDossier(c.o.tool_id);
  }
  swiping = true;
  if (top) {
    top.style.transition = "transform .4s ease-out, opacity .4s ease-out";
    top.style.transform = dir === "right" ? "translate3d(140%,40px,0) rotate(24deg)" : "translate3d(-140%,40px,0) rotate(-24deg)";
    top.style.opacity = "0";
  }
  try {
    await post(`/api/businesses/${S.biz.id}/picks`, { tool_id: c.o.tool_id, action: dir === "right" ? "trial" : "pass" });
    toast(dir === "right" ? `${c.o.name}: added to My tools with a setup checklist` : `Passed on ${c.o.name}`, dir === "right" ? "favorite" : "close");
    await refresh();
  } catch (e) { fail(e); }
  swiping = false;
  setTimeout(() => { if ((location.hash || "").startsWith("#swipe")) renderSwipe(); }, 250);
}
document.addEventListener("keydown", (e) => {
  if (!(location.hash || "").startsWith("#swipe") || !$("#sheet").classList.contains("hidden") || !$("#modal").classList.contains("hidden")) return;
  const dir = { ArrowLeft: "left", ArrowUp: "up", ArrowRight: "right" }[e.key];
  if (dir) { e.preventDefault(); swipe(dir); }
});

// ---------- compare ----------
function openCompareJob(jobKey) {
  const j = S.rec.jobs.find((x) => x.job === jobKey);
  showCompare(`Compare: ${j.label}`, j.options);
}
async function openCompareSelected() {
  if (!S.biz) {
    const tools = [...S.compare].map((id) => S.catalog.find((t) => t.id === id));
    return showCompareCatalog(tools);
  }
  const rows = await Promise.all([...S.compare].map((id) => api(`/api/businesses/${S.biz.id}/tools/${id}`)));
  const opts = rows.map((r, i) => r.option || { tool_id: [...S.compare][i], name: S.catalog.find((t) => t.id === [...S.compare][i]).name, ineligible: r.reasons.join("; ") || r.missing?.map((m) => m.label).join(", ") || "Not scored" });
  showCompare("Compare selected tools", opts);
}
function showCompare(title, opts) {
  const T = (id) => S.catalog.find((t) => t.id === id) || {};
  const row = (label, f) => html`<tr class="border-t border-soft2 align-top"><th scope="row" class="text-left py-2 pr-3 text-[12px] text-muted font-semibold whitespace-nowrap">${label}</th>${opts.map((o) => html`<td class="py-2 pr-3 text-[12.5px] min-w-[130px]">${o.ineligible ? (label === "Fit score" ? html`<span class="text-bad">${o.ineligible}</span>` : "") : f(o, T(o.tool_id))}</td>`)}</tr>`;
  openSheet(title, html`
    <div class="overflow-x-auto -mx-4 px-4"><table class="w-full"><thead><tr><th></th>${opts.map((o) => html`<th scope="col" class="text-left pb-2 pr-3 font-head text-[14px]"><button class="underline" data-dossier="${o.tool_id}">${o.name}</button></th>`)}</tr></thead><tbody>
      ${row("Fit score", (o) => html`<b class="text-[16px]">${o.score}</b>/100`)}
      ${row("Cost for you", (o) => (o.monthly_cost == null ? "Quote only" : o.monthly_cost === 0 ? "Free" : `${usd2(o.monthly_cost)}/mo`))}
      ${row("Plan", (o) => html`${o.plan}<div class="text-[11px] text-muted">${o.cost_note}</div>`)}
      ${row("Est. value", (o) => `~${usd(o.monthly_value)}/mo (${usd(o.monthly_value_low)}–${usd(o.monthly_value_high)})`)}
      ${row("Net", (o) => (o.net_monthly == null ? "?" : `${usd(o.net_monthly)}/mo`))}
      ${row("Ratings", (o, t) => (t.ratings || []).length ? (t.ratings || []).map((r) => html`<div>${r.score == null ? "No reviews" : `${r.score}★`} · ${r.count} on ${ext(r.url, r.platform)}</div>`) : "None found")}
      ${row("Evidence", (o) => `${o.evidence.strength} (${o.evidence.critical_reviews} critical of ${o.evidence.relevant_reviews} quoted)`)}
      ${row("Free trial", (o) => o.trial || "–")}
      ${row("Contract", (o) => o.contract || "–")}
      ${row("Must-haves", (o) => (o.unconfirmed_needs.length ? `Unconfirmed: ${o.unconfirmed_needs.join(", ")}` : "Met"))}
      ${row("Works with", (o, t) => (t.works_with || []).map(swName).join(", ") || "Standalone")}
      ${row("Price source", (o, t) => ext(t.pricing?.url || "#", EVIDENCE[t.pricing?.evidence] || "source"))}
    </tbody></table></div>`);
}
function showCompareCatalog(tools) {
  openSheet("Compare tools", html`<p class="text-[13px] text-muted mb-3">Set up your profile to see cost, value and fit for <b>your</b> business. Showing catalog facts only.</p>
    <div class="overflow-x-auto"><table class="w-full text-[12.5px]"><tbody>
      <tr><th></th>${tools.map((t) => html`<th class="text-left font-head text-[14px] pr-3">${t.name}</th>`)}</tr>
      <tr class="border-t border-soft2"><th class="text-left py-2 pr-3 text-muted">From</th>${tools.map((t) => html`<td class="pr-3">${priceFrom(t)}</td>`)}</tr>
      <tr class="border-t border-soft2"><th class="text-left py-2 pr-3 text-muted">Ratings</th>${tools.map((t) => html`<td class="pr-3">${ratingLine(t)}</td>`)}</tr>
      <tr class="border-t border-soft2"><th class="text-left py-2 pr-3 text-muted">Trial</th>${tools.map((t) => html`<td class="pr-3">${t.pricing.trial}</td>`)}</tr>
      <tr class="border-t border-soft2"><th class="text-left py-2 pr-3 text-muted">Contract</th>${tools.map((t) => html`<td class="pr-3">${t.pricing.contract}</td>`)}</tr>
    </tbody></table></div><a href="#start" class="btn btn-accent w-full mt-4" data-close>Set up my profile</a>`);
}

// ---------- browse ----------
const priceFrom = (t) => { const p = t.pricing; if (p.quote_only || !p.plans.length) return "Quote only"; const min = Math.min(...p.plans.map((x) => x.usd_month)); return min === 0 ? "Free" : `from ${usd2(min)}/mo`; };
const ratingLine = (t) => { const r = (t.ratings || []).filter((x) => x.count > 0 && x.score != null); return r.length ? r.map((x) => `${x.score}★ (${x.count.toLocaleString()} on ${x.platform})`).join(" · ") : "No independent ratings found"; };
function renderBrowse() {
  const q = S.q.toLowerCase();
  const list = S.catalog.filter((t) => (S.browseJob === "all" || t.jobs.includes(S.browseJob) || (S.browseJob === "candidate" && t.kind === "candidate"))
    && (!q || `${t.name} ${t.vendor} ${t.summary}`.toLowerCase().includes(q)));
  const tabs = [["all", "All"], ...Object.entries(JOBS).map(([k, v]) => [k, v.short]), ["candidate", "Newly discovered"]];
  view(html`
    <section aria-labelledby="br-title">
      <h1 id="br-title" class="font-head text-[22px] font-bold">Browse AI tools</h1>
      <p class="text-[13px] text-muted">${S.catalog.filter((t) => t.kind !== "candidate").length} researched tools. Real prices, real reviews (good and bad), sources linked. Retrieved ${S.catalog[0]?.retrieved || ""}.</p>
      <label class="block mt-3"><span class="sr-only">Search tools</span><input id="q" class="field" placeholder="Search: receptionist, invoices, Gmail…" value="${S.q}"/></label>
      <div class="flex gap-2 overflow-x-auto py-3 -mx-4 px-4" role="group" aria-label="Filter by job">${tabs.map(([k, l]) => html`<button class="chip shrink-0" data-tab="${k}" aria-pressed="${String(S.browseJob === k)}">${l}</button>`)}</div>
      <div class="flex flex-col gap-3">${list.map(toolTile)}${list.length ? "" : html`<p class="text-muted text-[13px]">No tools match.</p>`}</div>
      <div class="card p-4 mt-5">
        <h2 class="font-head font-bold text-[16px]">${icon("travel_explore", "text-[20px] align-[-4px]")} Know a tool we don't list?</h2>
        <p class="text-[12.5px] text-muted mt-1">Paste its pricing page or app-store listing. ShopFloor reads the page and an AI extracts a draft listing. It stays marked <b>unverified</b> and is never recommended until a person checks it.</p>
        <form id="disc" class="flex gap-2 mt-2"><label class="sr-only" for="disc-url">Tool URL</label><input id="disc-url" class="field" type="url" placeholder="https://…" required/><button class="btn btn-primary shrink-0">Add</button></form>
      </div>
    </section>
    ${S.compare.size ? html`<div class="fixed bottom-20 inset-x-4 max-w-md mx-auto z-30"><button id="cmp" class="btn btn-accent w-full shadow-xl">${icon("compare_arrows", "text-[18px]")} Compare ${S.compare.size} selected</button></div>` : ""}`);
  $("#q").oninput = (e) => { S.q = e.target.value; const pos = e.target.selectionStart; renderBrowse(); const n = $("#q"); n.focus(); n.setSelectionRange(pos, pos); };
  $$("[data-tab]").forEach((b) => (b.onclick = () => { S.browseJob = b.dataset.tab; renderBrowse(); }));
  $$("[data-dossier]").forEach((b) => (b.onclick = () => openDossier(b.dataset.dossier)));
  $$("[data-cmp]").forEach((c) => (c.onchange = () => { c.checked ? (S.compare.size < 3 ? S.compare.add(c.dataset.cmp) : (c.checked = false, toast("Compare up to 3 at a time", "info"))) : S.compare.delete(c.dataset.cmp); renderBrowse(); }));
  $("#cmp") && ($("#cmp").onclick = () => openCompareSelected().catch(fail));
  $("#disc").onsubmit = async (e) => {
    e.preventDefault(); const b = e.target.querySelector("button"); b.disabled = true; b.textContent = "Reading…";
    try { const t = await post("/api/discover", { url: $("#disc-url").value }); S.catalog = (await api("/api/catalog")).tools; S.browseJob = "candidate"; renderBrowse(); toast(`Added ${t.name} as an unverified candidate`, "travel_explore"); }
    catch (err) { fail(err); b.disabled = false; b.textContent = "Add"; }
  };
}
function toolTile(t) {
  const [kl, kc] = KIND[t.kind] || KIND.product;
  return html`
    <article class="card p-3.5 flex gap-3">
      <div class="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0" style="background:${job(t.jobs[0]).color}22">${icon(job(t.jobs[0]).icon, "text-[22px]")}</div>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1.5 flex-wrap"><button class="font-head font-bold text-[15px] hover:underline text-left" data-dossier="${t.id}">${t.name}</button><span class="badge ${kc}">${kl}</span></div>
        <p class="text-[12.5px] text-muted line-clamp-2">${t.summary}</p>
        <div class="text-[12px] mt-1"><b>${priceFrom(t)}</b> · <span class="text-muted">${ratingLine(t)}</span></div>
        ${t.verticals?.[0] !== "all" && t.verticals?.length ? html`<div class="text-[11.5px] text-muted">For ${t.verticals.join(", ").replace(/_/g, " ")}</div>` : ""}
      </div>
      ${t.kind !== "candidate" ? html`<label class="flex flex-col items-center justify-start gap-0.5 text-[10px] text-muted shrink-0 pt-1"><input type="checkbox" class="rounded w-5 h-5" data-cmp="${t.id}" ${S.compare.has(t.id) ? "checked" : ""} aria-label="Compare ${t.name}"/>Compare</label>` : ""}
    </article>`;
}

// ---------- dossier ----------
function openSheet(title, body) {
  const s = $("#sheet");
  s.innerHTML = html`<div class="max-w-3xl mx-auto px-4 pb-16">
    <div class="sticky top-0 bg-surface/95 backdrop-blur pt-safe z-10 flex items-center gap-2 py-3 border-b border-soft2 mb-4">
      <button class="w-10 h-10 rounded-full bg-soft2 flex items-center justify-center" data-close aria-label="Close">${icon("arrow_back")}</button>
      <h2 id="sheet-title" class="font-head font-bold text-[17px] truncate">${title}</h2></div>${body}</div>`.s;
  s.classList.remove("hidden"); document.body.style.overflow = "hidden";
  $$("[data-close]", s).forEach((b) => (b.onclick = closeSheet));
  $$("[data-dossier]", s).forEach((b) => (b.onclick = () => openDossier(b.dataset.dossier)));
  s.scrollTop = 0; $("[data-close]", s).focus();
}
function closeSheet() { $("#sheet").classList.add("hidden"); document.body.style.overflow = ""; }
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#sheet").classList.contains("hidden")) closeSheet(); });

async function openDossier(id) {
  const t = S.catalog.find((x) => x.id === id) || (await api(`/api/catalog/${id}`));
  const fit = S.biz && t.kind !== "candidate" ? await api(`/api/businesses/${S.biz.id}/tools/${id}`).catch(() => null) : null;
  const o = fit?.option, p = t.pricing;
  const rel = t.reviews.filter((r) => r.relevant), irr = t.reviews.filter((r) => !r.relevant);
  const stars = (n) => (n == null ? "" : "★".repeat(n) + "☆".repeat(5 - n));
  openSheet(t.name, html`
    <div class="flex items-start gap-3">
      <div class="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0" style="background:${job(t.jobs[0]).color}22">${icon(job(t.jobs[0]).icon, "text-[28px]")}</div>
      <div class="min-w-0"><div class="text-[12.5px] text-muted">${t.vendor} · ${t.jobs.map((j) => job(j).label).join(", ")}</div>
        <p class="text-[14px] mt-0.5">${t.summary}</p>
        <div class="flex gap-1.5 mt-1.5 flex-wrap"><span class="badge ${(KIND[t.kind] || KIND.product)[1]}">${(KIND[t.kind] || KIND.product)[0]}</span>${t.verticals?.[0] !== "all" ? html`<span class="badge bg-soft2 text-ink">For ${t.verticals.join(", ").replace(/_/g, " ")}</span>` : ""}</div></div>
    </div>

    <section class="card p-4 mt-4" aria-labelledby="d-fit"><h3 id="d-fit" class="font-head font-bold text-[15px]">For ${S.biz ? S.biz.name : "your business"}</h3>
      ${!S.biz ? html`<p class="text-[13px] text-muted mt-1">Set up your profile to see what this would cost and be worth for you.</p><a href="#start" class="btn btn-accent mt-2" data-close>Set up my profile</a>`
        : o ? html`<div class="mt-2">${optionBlock(o, true)}</div>`
        : html`<p class="text-[13px] mt-1">${fit?.reasons?.length ? html`<b>Ruled out:</b> ${fit.reasons.join("; ")}` : fit?.missing?.length ? html`Add ${fit.missing.map((m) => m.label).join(", ")} in your profile to score this.` : "Not scored for your business."}</p>`}
    </section>

    <section class="card p-4 mt-3" aria-labelledby="d-price"><h3 id="d-price" class="font-head font-bold text-[15px]">Pricing</h3>
      ${p.quote_only || !p.plans.length ? html`<p class="text-[13px] mt-1">Quote only. The vendor doesn't publish prices.</p>` : html`
        <table class="w-full text-[13px] mt-2"><thead><tr class="text-left text-[11.5px] text-muted"><th class="py-1">Plan</th><th>Price</th><th>Includes</th></tr></thead><tbody>
          ${p.plans.map((pl) => html`<tr class="border-t border-soft2 align-top"><td class="py-1.5 pr-2 font-semibold">${pl.name}</td><td class="pr-2 whitespace-nowrap">${pl.usd_month === 0 ? "Free" : usd2(pl.usd_month) + "/mo"}</td>
            <td class="text-[12px] text-muted">${pl.included != null && p.unit !== "flat" && p.unit !== "locations" ? `${pl.included.toLocaleString()} ${p.unit.replace("_", " ")}` : ""}${pl.overage != null && p.unit !== "users" ? `, then ${usd2(pl.overage)} each` : ""}${pl.notes ? html`<div>${pl.notes}</div>` : ""}</td></tr>`)}
        </tbody></table>`}
      <dl class="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-[12.5px] mt-3"><dt class="text-muted">Trial</dt><dd>${p.trial || "–"}</dd><dt class="text-muted">Contract</dt><dd>${p.contract || "–"}</dd>
        ${p.notes ? html`<dt class="text-muted">Note</dt><dd>${p.notes}</dd>` : ""}
        <dt class="text-muted">Source</dt><dd>${ext(p.url, EVIDENCE[p.evidence] || p.evidence)} · retrieved ${t.retrieved}</dd></dl>
    </section>

    <section class="card p-4 mt-3" aria-labelledby="d-rev"><h3 id="d-rev" class="font-head font-bold text-[15px]">What customers say</h3>
      ${t.ratings.length ? html`<ul class="mt-2 flex flex-col gap-1 text-[13px]">${t.ratings.map((r) => html`<li>${r.score == null ? "No reviews yet" : html`<b>${r.score}★</b>`} from ${r.count.toLocaleString()} on ${ext(r.url, r.platform)}${r.note ? html`<div class="text-[11.5px] text-muted">${r.note}</div>` : ""}</li>`)}</ul>` : ""}
      ${t.evidence_gap ? html`<p class="text-[12.5px] text-warn mt-2">${icon("help", "text-[15px] align-[-3px]")} ${t.evidence_gap}</p>` : ""}
      ${rel.length ? html`<ul class="mt-3 flex flex-col gap-2.5">${rel.map((r) => html`
        <li class="rounded-2xl ${r.stars != null && r.stars <= 2 ? "bg-red-50 border border-red-100" : "bg-soft"} p-3">
          <div class="text-[12px] flex justify-between gap-2"><span class="text-amber-600" aria-label="${r.stars} out of 5 stars">${stars(r.stars)}</span><span class="text-muted">${r.theme}</span></div>
          <blockquote class="text-[13.5px] mt-1">“${r.quote}”</blockquote>
          <div class="text-[11.5px] text-muted mt-1">${r.author}${r.date ? ` · ${r.date}` : ""} · ${ext(r.url, r.platform)}${r.relevance_note ? html`<div>${r.relevance_note}</div>` : ""}</div></li>`)}</ul>` : ""}
      ${irr.length ? html`<details class="mt-3"><summary class="text-[12.5px] font-semibold text-muted">${irr.length} review${irr.length === 1 ? "" : "s"} excluded as not about this product ${icon("expand_more", "chev text-[16px] align-[-4px]")}</summary>
        <ul class="mt-2 flex flex-col gap-2">${irr.map((r) => html`<li class="text-[12.5px] rounded-xl border border-soft2 p-2.5 text-muted">“${r.quote}” (${r.author}, ${ext(r.url, r.platform)})<div class="text-[11.5px] mt-0.5"><b>Why excluded:</b> ${r.relevance_note}</div></li>`)}</ul></details>` : ""}
      <p class="text-[11px] text-muted mt-3">Short verbatim excerpts, picked to show both praise and complaints. Platform verification labels are the platform's own claims.</p>
    </section>

    ${t.behavior ? html`<section class="card p-4 mt-3" aria-labelledby="d-try"><h3 id="d-try" class="font-head font-bold text-[15px]">Try it on your own example</h3>
      <p class="text-[12.5px] text-muted mt-1">Paste a real review, customer email or call note. We simulate how this tool says it behaves. <b>This is a simulation from the vendor's description, not output from ${t.name} itself.</b></p>
      <form id="try" class="mt-2 flex flex-col gap-2"><label class="sr-only" for="try-text">Your example</label><textarea id="try-text" class="field" rows="3" maxlength="1500" placeholder="e.g. 2 stars. Waited 40 minutes and the order was wrong."></textarea>
        <button class="btn btn-primary">${icon("science", "text-[18px]")} Simulate a reply</button></form><div id="try-out"></div>
      ${t.lab ? html`<p class="text-[12px] text-muted mt-3">${icon("fact_check", "text-[15px] align-[-3px]")} Safety scenarios (simulated): passed ${Math.round(t.lab.accuracy * t.lab.n_tasks)} of ${t.lab.n_tasks} on ${t.lab.model}, graded by a different model family. A tiny, mostly restaurant-based scenario set run on a simulation of the vendor's description, so it's <b>not</b> counted in the score. Testing the real product is in our 16-week plan.</p>` : ""}
    </section>` : ""}

    <section class="card p-4 mt-3"><h3 class="font-head font-bold text-[15px]">Capabilities</h3>
      <ul class="text-[13px] mt-1 grid grid-cols-2 gap-1">${Object.entries(t.capabilities || {}).map(([k, v]) => html`<li>${v === true ? "✅" : v === false ? "❌" : "❔"} ${k.replace(/_/g, " ")}${t.capability_notes?.[k] ? html`<div class="text-[11px] text-muted">${t.capability_notes[k]}</div>` : ""}</li>`)}</ul>
      <p class="text-[11px] text-muted mt-1">❔ = the vendor's pages don't say. We don't assume.</p>
      ${t.works_with?.length ? html`<p class="text-[12.5px] mt-2"><b>Works with:</b> ${t.works_with.map(swName).join(", ")}</p>` : ""}
      ${t.requires_any?.length ? html`<p class="text-[12.5px]"><b>Requires:</b> ${t.requires_any.map(swName).join(" or ")}</p>` : ""}
    </section>
    ${t.engage?.signup_url ? html`<a href="${t.engage.signup_url}" target="_blank" rel="noopener noreferrer" class="btn btn-accent w-full mt-4">${t.engage.cta || "Visit"} ${icon("open_in_new", "text-[16px]")}</a>
      <p class="text-[11px] text-muted text-center mt-1">ShopFloor takes no referral fees; rankings are never paid.</p>` : ""}`);
  $$("#sheet [data-act]").forEach((b) => (b.onclick = () => { closeSheet(); decide(b.dataset.tool, b.dataset.act, null); }));
  const form = $("#try");
  if (form) form.onsubmit = async (e) => {
    e.preventDefault(); const b = form.querySelector("button"); b.disabled = true;
    try { const r = await post(`/api/tools/${id}/try`, { text: $("#try-text").value });
      $("#try-out").innerHTML = html`<div class="rounded-2xl bg-soft p-3 mt-2"><div class="text-[11px] text-muted mb-1">SIMULATED · ${r.model}</div><p class="text-[13.5px] whitespace-pre-wrap">${r.reply}</p><p class="text-[11px] text-muted mt-1">${r.note}</p></div>`.s;
    } catch (err) { fail(err); } finally { b.disabled = false; }
  };
}

// ---------- my tools ----------
function renderMyTools() {
  const rows = S.picks.filter((r) => r.pick.status !== "passed");
  const passed = S.picks.filter((r) => r.pick.status === "passed");
  view(html`
    <section aria-labelledby="mt-title">
      <h1 id="mt-title" class="font-head text-[22px] font-bold">My tools</h1>
      <p class="text-[13px] text-muted">Set up, check in after 30 days, and cancel cleanly if it isn't working.</p>
      <div class="flex flex-col gap-4 mt-3">
        ${rows.length ? rows.map(pickCard) : html`<div class="card p-5 text-center"><p class="text-[14px]">Nothing yet.</p><a href="#foryou" class="btn btn-primary mt-3">See recommendations</a></div>`}
      </div>
      ${passed.length ? html`<p class="text-[12px] text-muted mt-4">Passed: ${passed.map((r) => r.tool?.name).join(", ")}</p>` : ""}
    </section>`);
  $$("[data-step]").forEach((c) => (c.onchange = async () => { try { await post(`/api/businesses/${S.biz.id}/picks/${c.dataset.pick}/steps/${c.dataset.step}`); await refresh(); } catch (e) { fail(e); } }));
  $$("[data-adopt]").forEach((b) => (b.onclick = async () => { try { await post(`/api/businesses/${S.biz.id}/picks/${b.dataset.adopt}/adopt`); await refresh(); render(); toast("Marked as in use", "verified"); } catch (e) { fail(e); } }));
  $$("[data-cancel]").forEach((b) => (b.onclick = () => cancelPick(b.dataset.cancel)));
  $$("[data-checkin]").forEach((f) => (f.onsubmit = async (e) => {
    e.preventDefault(); const inputs = {};
    new FormData(f).forEach((v, k) => { if (k !== "note" && String(v).trim() !== "") inputs[k] = Number(v); });
    try { await post(`/api/businesses/${S.biz.id}/picks/${f.dataset.checkin}/checkin`, { inputs, note: f.note.value }); await refresh(); render(); toast("Check-in saved. Thank you!", "insights"); } catch (err) { fail(err); }
  }));
  $$("[data-dossier]").forEach((b) => (b.onclick = () => openDossier(b.dataset.dossier)));
}
function pickCard(r) {
  const p = r.pick, t = r.tool || {}, e = p.estimate || {}, o = r.outcome;
  const done = p.checklist.filter((s) => s.done).length;
  const st = { trial: ["Trying", "bg-amber-100 text-amber-900"], adopted: ["In use", "bg-emerald-100 text-emerald-800"], cancelled: ["Cancelled", "bg-slate-200 text-slate-700"] }[p.status];
  return html`
    <article class="card p-4 flex flex-col gap-3">
      <div class="flex items-center justify-between gap-2"><button class="font-head font-bold text-[16px] hover:underline text-left" data-dossier="${p.tool_id}">${t.name}</button><span class="badge ${st[1]}">${st[0]}</span></div>
      <div class="text-[12.5px] text-muted">${job(p.job).label} · started ${r.days_since_start} day${r.days_since_start === 1 ? "" : "s"} ago · predicted ~${usd(e.monthly_value)}/mo (${usd(e.monthly_value_low)}–${usd(e.monthly_value_high)}) for ${e.monthly_cost === 0 ? "free" : usd2(e.monthly_cost) + "/mo"}</div>
      ${p.status !== "cancelled" ? html`
        <div><div class="text-[12.5px] font-semibold">Setup checklist · ${done}/${p.checklist.length}</div>
          <ul class="mt-1.5 flex flex-col gap-1">${p.checklist.map((s, i) => html`<li><label class="flex gap-2 text-[13px] items-start"><input type="checkbox" class="rounded mt-0.5" data-pick="${p.id}" data-step="${i}" ${s.done ? "checked" : ""}/> <span>${s.step}</span></label></li>`)}</ul></div>
        ${t.engage?.signup_url ? html`<p class="text-[12.5px]">${ext(t.engage.signup_url, t.engage.cta || "Open vendor site")}</p>` : ""}
        <details class="rounded-2xl border border-soft2" ${o ? "" : r.days_since_start >= 25 ? "open" : ""}><summary class="p-3 text-[13px] font-semibold flex justify-between">${icon("insights", "text-[18px] align-[-4px]")} ${o ? "Your check-in" : "30-day check-in"} ${icon("expand_more", "chev")}</summary>
          <div class="px-3 pb-3">
            ${o ? html`<div class="rounded-xl ${o.within_interval ? "bg-emerald-50" : "bg-amber-50"} p-3 text-[13px] mb-3">You reported <b>${usd(o.actual_monthly_usd)}/mo</b> vs our prediction of ${usd(o.predicted_monthly_usd)} (${usd(o.predicted_low)}–${usd(o.predicted_high)}): ${o.within_interval ? "inside our range." : o.actual_monthly_usd > o.predicted_high ? "better than we predicted." : "below our range."}
              ${o.days_since_start < 14 ? html`<div class="text-[11.5px] text-muted mt-1">Early check-in (day ${o.days_since_start}). Only check-ins after 14+ days feed the calibration.</div>` : ""}</div>` : ""}
            <form data-checkin="${p.id}" class="flex flex-col gap-2">
              ${r.questions.map((q) => html`<label class="block"><span class="text-[12.5px] font-semibold">${q.label}</span><input class="field mt-1" inputmode="decimal" name="${q.key}" value="${o?.reported_inputs?.[q.key] ?? ""}"/></label>`)}
              <label class="block"><span class="text-[12.5px] font-semibold">Anything else? (optional)</span><input class="field mt-1" name="note" maxlength="500" value="${o?.note || ""}"/></label>
              <button class="btn btn-primary">${o ? "Update check-in" : "Save check-in"}</button>
              <p class="text-[11px] text-muted">Self-reported. Your answers adjust future estimates for this job for every business, and we publish how accurate we've been.</p>
            </form></div></details>
        <div class="flex gap-2">${p.status === "trial" ? html`<button class="btn btn-primary flex-1" data-adopt="${p.id}">${icon("verified", "text-[18px]")} Keep it</button>` : ""}
          <button class="btn btn-ghost flex-1 !text-bad" data-cancel="${p.id}">${icon("logout", "text-[18px]")} Cancel / leave</button></div>`
      : html`<p class="text-[12.5px] text-muted">Cancelled ${new Date(p.cancelled_at).toLocaleDateString()}.</p>`}
    </article>`;
}
async function cancelPick(id) {
  const row = S.picks.find((r) => r.pick.id === id);
  const m = $("#modal");
  m.innerHTML = html`<div class="w-full max-w-md bg-white rounded-3xl p-5 shadow-2xl" role="document">
    <h3 class="font-head font-bold text-[18px]">Leave ${row.tool?.name}?</h3>
    <p class="text-[13px] text-muted mt-1">Vendor's stated terms: <b>${row.tool?.pricing?.contract || "not stated"}</b></p>
    <ol class="list-decimal pl-5 mt-3 text-[13px] flex flex-col gap-1">
      <li>Cancel in the vendor's billing page</li><li>Revoke its access to Google / QuickBooks / Xero (connected apps)</li><li>Turn off call forwarding if you set it up</li><li>Download your records below</li></ol>
    <div class="mt-4 flex flex-col gap-2"><button class="btn btn-primary" data-ok>Mark as cancelled & download my records</button><button class="btn btn-ghost" data-no>Keep it</button></div></div>`.s;
  m.classList.remove("hidden"); $("[data-no]", m).focus();
  const close = () => { m.classList.add("hidden"); m.innerHTML = ""; };
  $("[data-no]", m).onclick = close;
  $("[data-ok]", m).onclick = async () => {
    try { const r = await post(`/api/businesses/${S.biz.id}/picks/${id}/cancel`);
      const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(r.export, null, 2)], { type: "application/json" }));
      a.download = `shopfloor-${row.tool?.id}-records.json`; a.click(); URL.revokeObjectURL(a.href);
      window.open(r.cancel_url, "_blank", "noopener"); close(); await refresh(); render(); toast("Marked cancelled. Vendor page opened to finish.", "logout");
    } catch (e) { fail(e); }
  };
}

// ---------- research ----------
const fmtA = (v) => (v > 0 && v < 1 ? pct(v) : String(v));
function sbaPanel() {
  const r = S.research; if (!r) return "";
  return html`<section class="card p-4 mt-5" aria-labelledby="sba"><h2 id="sba" class="font-head font-bold text-[16px]">${icon("support_agent", "text-[20px] align-[-4px]")} Free help from the SBA</h2>
    <p class="text-[12.5px] text-muted mt-1">Bring your ShopFloor shortlist to a free advisor${S.biz?.zip ? ` near ${S.biz.zip}` : ""}.</p>
    <ul class="mt-2 flex flex-col gap-2">${r.sba_resources.map((s) => html`<li class="text-[13px]">${ext(s.url, s.name, "font-semibold underline")}<div class="text-[12px] text-muted">${s.why}</div></li>`)}</ul></section>`;
}
async function renderResearch() {
  const r = S.research, st = r.stats;
  const acc = await api("/api/accuracy").catch(() => ({ rows: [], reported: 0 }));
  const A = r.assumptions;
  view(html`
    <section aria-labelledby="rs-title" class="flex flex-col gap-4">
      <div><h1 id="rs-title" class="font-head text-[22px] font-bold">How we rate tools</h1>
        <p class="text-[13px] text-muted">Like a review site for AI tools, except the score is personal: it uses <b>your</b> numbers, and reviews are only one part of it.</p></div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
        ${[[st.products, "real products"], [st.builtins, "free built-ins"], [st.platform_ratings_counted.toLocaleString(), "platform ratings counted"], [st.reviews_quoted, "reviews quoted, with links"]].map(([n, l]) => html`<div class="card p-3 text-center"><div class="font-head text-[22px] font-bold">${n}</div><div class="text-[11.5px] text-muted">${l}</div></div>`)}
      </div>
      <div class="card p-4"><h2 class="font-head font-bold text-[16px]">The fit score (out of 100)</h2>
        <ol class="mt-2 flex flex-col gap-2 text-[13px]">
          <li><b>Value for you · 40</b>: estimated monthly value ÷ what it would cost <i>at your volume</i> (the right plan, plus overage), on a log scale. Free built-ins you already own count.</li>
          <li><b>Fit · 25</b>: made for your industry, connects to software you already use, meets your must-haves (Spanish, human hand-off). Unconfirmed = 0, not "probably".</li>
          <li><b>Customer evidence · 20</b>: independent ratings, shrunk toward 3★ when there are few. Reviews about a different product are down-weighted, and we say so.</li>
          <li><b>Transparency · 15</b>: published price, free trial, month-to-month terms.</li></ol>
        <p class="text-[12px] text-muted mt-2">Before scoring, hard rules remove tools that don't fit (wrong industry, software you don't have, over budget). We also tell you when <b>not</b> to buy: when a free feature you already have does the job, or when your volume is below break-even. The weights are our starting hypothesis; the 16-week plan validates them against owner outcomes.</p></div>
      <div class="card p-4"><h2 class="font-head font-bold text-[16px]">What the research told us, and what we built because of it</h2>
        <ul class="mt-2 flex flex-col gap-3">${r.context.map((c) => html`<li class="text-[13px]"><p>${c.claim} <span class="text-muted">(${ext(c.url, c.source, "underline")})</span></p><p class="text-[12.5px] mt-0.5"><b>→ So:</b> ${c.design_decision}</p></li>`)}</ul></div>
      <div class="card p-4"><h2 class="font-head font-bold text-[16px]">What reading ${st.reviews_quoted} real reviews taught us</h2>
        <ul class="mt-2 flex flex-col gap-2 text-[13px] list-disc pl-5">${r.review_findings.map((f) => html`<li>${f}</li>`)}</ul>
        <p class="text-[11.5px] text-muted mt-2">G2 and Capterra block automated collection, so they aren't used. Sample: the newest visible reviews on Trustpilot and the Xero App Store per product, keeping critical ones; ${st.reviews_excluded} excluded as off-topic, with the reason shown.</p></div>
      <div class="card p-4"><h2 class="font-head font-bold text-[16px]">Every assumption, and where it comes from</h2>
        <ul class="mt-2 flex flex-col">${Object.values(A).map((a) => html`<li class="border-t border-soft2 py-2.5">
          <div class="flex items-start justify-between gap-2"><span class="text-[13px] font-semibold">${a.label}</span>
            <span class="badge shrink-0 ${a.grade === "assumption" ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-800"}">${GRADE[a.grade] || a.grade}</span></div>
          <div class="text-[13px] mt-0.5">${a.low != null && a.high != null && a.low !== a.high ? `${fmtA(a.low)} / ${fmtA(a.mid)} / ${fmtA(a.high)} (low / mid / high)` : a.mid != null ? fmtA(a.mid) : a.by_group ? Object.entries(a.by_group).map(([k, v]) => `${k.replace("_", " ")} ${pct(v)}`).join(" · ") : ""}</div>
          ${a.note ? html`<div class="text-[11.5px] text-muted">${a.note}</div>` : ""}
          ${(a.sources || []).map((src) => html`<div class="text-[11.5px]">${ext(src.url, src.title, "underline text-muted")}</div>`)}</li>`)}</ul></div>
      <div class="card p-4"><h2 class="font-head font-bold text-[16px]">Our accuracy (owner-reported)</h2>
        ${acc.rows.length ? html`<table class="w-full text-[12.5px] mt-2"><thead><tr class="text-left text-muted"><th>Job</th><th>Check-ins</th><th>Avg error</th><th>In range</th><th>Correction</th></tr></thead><tbody>${acc.rows.map((x) => html`<tr class="border-t border-soft2"><td class="py-1.5">${job(x.job).short}</td><td>${x.reported_outcomes}</td><td>${x.mape == null ? "–" : pct(x.mape)}</td><td>${pct(x.interval_coverage)}</td><td>×${x.current_correction_factor}</td></tr>`)}</tbody></table>`
          : html`<p class="text-[13px] mt-1">No calibrated check-ins yet (${acc.reported} reported so far; only those 14+ days after starting count). We publish this table as it fills in rather than claiming accuracy we haven't measured.</p>`}</div>
      <div class="card p-4"><h2 class="font-head font-bold text-[16px]">What's real today, and what isn't yet</h2>
        <ul class="mt-2 text-[13px] flex flex-col gap-1.5">
          <li>✅ Real products, prices, plans, trial and contract terms, each with a source link and date</li>
          <li>✅ Real, attributed reviews and platform ratings, including the bad ones</li>
          <li>✅ Your own numbers, typed in or read from your call-log / invoice / sales export</li>
          <li>✅ Discovery: paste any product page and an AI drafts a listing (marked unverified)</li>
          <li>⚠️ "Try it" replies and safety scenarios <b>simulate</b> the vendor's described behavior; they are not the vendor's product</li>
          <li>⚠️ Some value assumptions (e.g. how many missed callers convert) have no good public source. They're labeled, and owner check-ins correct them</li>
          <li>🔜 Direct connections (QuickBooks, Square, Google) instead of CSV; vendor sandboxes for real testing; scheduled marketplace crawls</li></ul></div>
      ${sbaPanel()}
    </section>`);
}

boot().catch((e) => { $("#view").innerHTML = html`<div class="card p-5"><p class="font-semibold">Couldn't load ShopFloor.</p><p class="text-[13px] text-muted">${e.message}</p></div>`.s; });
