/* OmniSight Member 1 frontend. Demo fixtures are isolated and visibly labelled. */
(()=>{
"use strict";
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const stateMeta={
 detected:{label:"Detected",className:"detected"},
 proposed:{label:"Proposed",className:"proposed"},
 applied:{label:"Applied",className:"applied"},
 verified:{label:"Verified",className:"verified"},
 failed:{label:"Failed",className:"failed"},
 inconclusive:{label:"Inconclusive",className:"inconclusive"}
};
let data={scans:[],issues:[],targets:[],dashboard:null}, currentReview=null, toastTimer=null, loadGeneration=0;
// const stateOf = (i) => String(i.state || i.verification_state || i.status || "detected").toLowerCase().replace(/[\s-]+/g, "_").includes("verified") ? "verified" : normalizeState(i.state || i.verification_state || i.status);
function normalizeState(raw){
 const s=String(raw||"detected").toLowerCase().replace(/[\s-]+/g,"_");
 if(["verified","verified_resolved","resolved","passed"].includes(s))return "verified";
 if(["proposed","fix_proposed","awaiting_approval","pending_approval"].includes(s))return "proposed";
 if(["applied","fix_applied"].includes(s))return "applied";
 if(["failed","verification_failed","error"].includes(s))return "failed";
 if(["inconclusive","unknown","unconfirmed"].includes(s))return "inconclusive";
 return "detected";
}
function badge(raw){const key=normalizeState(raw),m=stateMeta[key];return `<span class="state-badge state-${m.className}"><i></i>${m.label}</span>`}
function severity(raw){const s=String(raw||"Unknown").toLowerCase();return `<span class="severity severity-${esc(s)}">${esc(raw||"Unknown")}</span>`}
function toast(msg){const t=$("#toast");t.textContent=msg;t.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove("show"),3200)}
function setState(el,kind,title,message){el.hidden=false;el.className=`state-panel state-${kind}`;el.innerHTML=`<span class="state-symbol">${kind==="loading"?"…":kind==="error"?"!":kind==="empty"?"—":"i"}</span><div><b>${esc(title)}</b><p>${esc(message)}</p></div>${kind==="error"?'<button class="text-link retry-button">Try again →</button>':""}`}
function clearState(el){el.hidden=true;el.innerHTML=""}
function setModeUI() {
  const footerMode = $("#footerMode");
  const scanModeFoot = $("#scanModeFoot");

  if (footerMode) {
    footerMode.textContent = "LIVE API";
  }

  if (scanModeFoot) {
    scanModeFoot.textContent =
      `API: ${window.OmniSightAPI.baseUrl}`;
  }
}

function renderMetrics() {
  const d = data.dashboard || {};

  const countVerified = data.issues.filter(
    i => normalizeState(i.state || i.verification_state || i.status) === "verified"
  ).length;

  const countAttention = data.issues.filter(
    i => normalizeState(i.state || i.verification_state || i.status) !== "verified"
  ).length;

  $("#metricScans").textContent = val(d.total_scans, data.scans.length);
  $("#metricIssues").textContent = val(d.issues_found, data.issues.length);
  $("#metricVerified").textContent = val(d.verified_resolved, countVerified);
  $("#metricAttention").textContent = val(d.needs_attention, countAttention);
  $("#navIssueCount").textContent = data.issues.length;
}

function val(v,fallback){return Number.isFinite(Number(v))&&v!==null?String(v):String(fallback)}
function scanStatus(s){const raw=String(s||"unknown").toLowerCase();let cls="neutral";if(raw.includes("complete")||raw==="success")cls="good";else if(raw.includes("partial")||raw.includes("pending")||raw.includes("running"))cls="warning";else if(raw.includes("fail")||raw.includes("error"))cls="bad";return `<span class="scan-badge scan-${cls}"><i></i>${esc(s||"Unknown")}</span>`}
function renderScans(){
 const rows=data.scans.slice(0,5);
 $("#recentScans").innerHTML=rows.map(s=>`<tr><td><div class="target-cell"><span class="target-mark">•</span><span><b>${esc(s.target||s.url||s.target_url||"Unnamed target")}</b><small>${esc(s.id||s.scan_id||"Scan")}</small></span></div></td><td>${esc(s.created_at||s.started_at||s.date||"—")}</td><td>${esc((s.viewports||s.viewport_sizes||[]).join("  ·  ")||s.viewport||"—")}</td><td>${scanStatus(s.status||s.state)}</td><td>${esc(s.issue_count??s.issues_found??"—")}</td></tr>`).join("");
 $("#historyRows").innerHTML=data.scans.map(s=>`<tr><td><b>${esc(s.id||s.scan_id||"—")}</b></td><td>${esc(s.target||s.url||s.target_url||"—")}</td><td>${esc(s.created_at||s.started_at||s.date||"—")}</td><td>${esc((s.viewports||s.viewport_sizes||[]).join("  ·  ")||s.viewport||"—")}</td><td>${scanStatus(s.status||s.state)}</td><td>${esc(s.issue_count??s.issues_found??"—")}</td></tr>`).join("");
 $("#recentEmpty").hidden=rows.length>0;$("#historyEmpty").hidden=data.scans.length>0;
}
function renderStatus(){
 const counts=Object.keys(stateMeta).map(k=>({key:k,count:data.issues.filter(i=>normalizeState(i.state||i.verification_state||i.status)===k).length}));
 const total=Math.max(data.issues.length,1);
 $("#statusBreakdown").innerHTML=counts.map(c=>`<div class="status-segment segment-${c.key}" style="width:${c.count/total*100}%"></div>`).join("");
 $("#statusLegend").innerHTML=counts.map(c=>`<div><i class="key-dot ${c.key}"></i><span>${stateMeta[c.key].label}</span><b>${c.count}</b></div>`).join("");
 const outstanding=data.issues.filter(i=>normalizeState(i.state||i.verification_state||i.status)!=="verified").sort((a,b)=>severityRank(b.severity)-severityRank(a.severity)).slice(0,3);
 $("#priorityIssues").innerHTML=outstanding.map(i=>`<button class="priority-row" data-review="${esc(i.id||i.issue_id)}"><span class="priority-mark">${esc((i.title||"I").slice(0,1))}</span><span class="priority-copy"><b>${esc(i.title||"Untitled issue")}</b><small>${esc(i.viewport||i.viewport_size||"Viewport unknown")}  ·  ${esc(i.type||i.issue_type||"Issue")}</small></span>${severity(i.severity)}<span class="row-arrow">→</span></button>`).join("");
 $("#priorityEmpty").hidden=outstanding.length>0;
}
function severityRank(s){return ({critical:5,high:4,medium:3,low:2,info:1})[String(s||"").toLowerCase()]||0}
function renderIssues() {
  const filter = $("#statusFilter").value;
  const q = $("#globalSearch").value.trim().toLowerCase();

  const list = data.issues.filter(i => {
    const st = normalizeState(
      i.state || i.verification_state || i.status
    );

    const text = `${i.id || i.issue_id || ""} ${i.title || ""} ${
      i.type || i.issue_type || ""} ${i.viewport || i.viewport_size || ""} ${
      i.description || i.summary || ""}`.toLowerCase();

    return (filter === "all" || st === filter) &&
      (!q || text.includes(q));
  });

  $("#issueSummary").textContent =
    `${list.length} issue${list.length === 1 ? "" : "s"} · backend response`;

  $("#issueList").innerHTML = list.map(i => {
    const id = i.id || i.issue_id;
    const view = i.viewport || i.viewport_size || "Not specified";
    const type = i.type || i.issue_type || "Unclassified";

    return `<article class="issue-row">
      <div class="issue-thumb" aria-hidden="true">
        <div class="thumb-top"><i></i><i></i><i></i></div>
        <div class="thumb-content"><span></span><span></span><i></i></div>
      </div>
      <div class="issue-main">
        <div class="issue-title-line">
          <h3>${esc(i.title || "Untitled issue")}</h3>
          ${severity(i.severity)}
        </div>
        <p>${esc(i.description || i.summary ||
          "No description was supplied by the backend.")}</p>
        <div class="issue-meta">
          <span>${esc(id || "ID unavailable")}</span>
          <span>${esc(type)}</span>
          <span>${esc(view)}</span>
        </div>
        <div class="issue-states">
          ${badge(i.state || i.verification_state || i.status)}
          <span class="evidence-hint">${
            i.before_screenshot || i.screenshot_url || i.evidence_screenshot
              ? "Evidence available"
              : "Evidence unavailable"
          }</span>
        </div>
      </div>
      <div class="issue-actions">
        <button class="button button-small button-light"
          data-review="${esc(id || "")}">Review issue →</button>
      </div>
    </article>`;
  }).join("");

  const state = $("#issuesState");
  state.hidden = list.length > 0;

  if (!list.length) {
    setState(
      state,
      "empty",
      "No matching issues",
      "Try a different status filter or search term."
    );
  }
}
function renderAll(){renderMetrics();renderScans();renderStatus();renderIssues()}
async function loadData() {
  const generation = ++loadGeneration;

  setModeUI();

  setState(
    $("#dashboardState"),
    "loading",
    "Loading dashboard",
    "Fetching current data from the backend."
  );

  $("#metricGrid").classList.add("is-loading");

  try {
    const results = await Promise.allSettled([
  window.OmniSightAPI.dashboard(),
  window.OmniSightAPI.scans(),
  window.OmniSightAPI.issues(),
  window.OmniSightAPI.targets()
]);

if (generation !== loadGeneration) return;

const getResult = (index, fallback) =>
  results[index].status === "fulfilled"
    ? results[index].value
    : fallback;

data = {
  dashboard: getResult(0, {}),
  scans: normalizeArray(getResult(1, [])),
  issues: normalizeArray(getResult(2, [])),
  targets: normalizeTargets(getResult(3, []))
};

    renderAll();
    fillTargets();

    clearState($("#dashboardState"));
    clearState($("#issuesState"));
    clearState($("#historyState"));

    if (!data.scans.length && !data.issues.length) {
      setState(
        $("#dashboardState"),
        "empty",
        "No data yet",
        "No scans or issues have been returned by the backend."
      );
    }
  } catch (error) {
    if (generation !== loadGeneration) return;

    data = {
      dashboard: null,
      scans: [],
      issues: [],
      targets: []
    };

    renderAll();
    fillTargets();

    setState(
      $("#dashboardState"),
      "error",
      "Backend unavailable",
      error.message
    );

    setState(
      $("#issuesState"),
      "empty",
      "No issues available",
      "Issues will appear when the backend returns them."
    );

    setState(
      $("#historyState"),
      "empty",
      "No scan history available",
      "Scan history will appear when the backend returns it."
    );
  } finally {
    $("#metricGrid").classList.remove("is-loading");
  }
}
function normalizeArray(v){return Array.isArray(v)?v:Array.isArray(v?.items)?v.items:Array.isArray(v?.results)?v.results:[]}

function normalizeTargets(v) {
  return normalizeArray(v).map(t => ({
    id: t.id ?? t.target_id ?? t.url ?? t.target_url,
    name: t.name ?? t.label ?? t.url ?? t.target_url ?? String(t.id),
    url: t.url ?? t.target_url ?? t.targetUrl ?? ""
  }));
}

function fillTargets() {
  const select = $("#target");
  if (!select) return;

  const previousValue = select.value;
  select.innerHTML = "";

  const targets = Array.isArray(data.targets) ? data.targets : [];

  if (!targets.length) {
    select.add(new Option("No targets available", ""));
    $("#targetHelp").textContent =
      "The backend returned no configured targets. Check the API connection.";
    console.error("No targets available in data.targets:", data.targets);
    return;
  }

  targets.forEach(target => {
    const url =
      target.url ||
      target.target_url ||
      target.targetUrl ||
      "";

    if (!url) {
      console.warn("Skipping target without URL:", target);
      return;
    }

    const option = new Option(target.name || url, url);
    option.dataset.url = url;
    select.add(option);
  });

  if ([...select.options].some(option => option.value === previousValue)) {
    select.value = previousValue;
  }

  $("#targetHelp").textContent =
    "Targets loaded from the connected backend.";
  console.log("Targets populated:", [...select.options].map(o => o.value));
}

function navigate(page){
 const pages=["overview","scan","issues","history","review"];
 if(!pages.includes(page))return;
 $$(".page").forEach(p=>p.classList.toggle("active",p.id==="page-"+page));
 $$(".nav-link").forEach(n=>n.classList.toggle("active",n.dataset.page===page));
 $("#breadcrumb").textContent=({overview:"Overview",scan:"New scan",issues:"Issues",history:"Scan history",review:"Fix review"})[page];
 $("#sidebar").classList.remove("open");window.scrollTo({top:0,behavior:"smooth"});
 if(page==="issues")renderIssues();
}

async function handleScan(e) {
  e.preventDefault();

  const desktop = $("#desktopViewport").checked;
  const mobile = $("#mobileViewport").checked;
  const select = $("#target");
  const option = select.options[select.selectedIndex];
  const url = option?.dataset.url || option?.value;

  if (!desktop && !mobile) {
    $("#scanFeedback").textContent = "Select at least one viewport.";
    return;
  }

  if (!url || !/^https?:\/\//i.test(url)) {
    $("#scanFeedback").textContent = "Select a valid target URL.";
    return;
  }

  const btn = $("#runScanButton");
  btn.disabled = true;
  $("#scanFeedback").textContent = "Running browser scan...";

  try {
    const result = await window.OmniSightAPI.createScan({
      url,
      viewports: [
        ...(desktop ? ["desktop"] : []),
        ...(mobile ? ["mobile"] : [])
      ]
    });

    $("#scanFeedback").textContent =
      `Scan completed: ${result.scan_id || result.id || "success"}.`;
    console.log("Scan result:", result);
    toast("Browser scan completed.");
  } catch (error) {
    console.error("Scan failed:", error);
    $("#scanFeedback").textContent = `Scan failed: ${error.message}`;
    toast("Scan request failed.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Run scan <span>↗</span>';
  }
}

function imagePanel(url,label){
 if(url)return `<figure class="screenshot-frame"><img src="${esc(url)}" alt="${esc(label)} screenshot" loading="lazy" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><div class="image-unavailable" hidden>Screenshot could not be loaded.</div><figcaption>${esc(label)}</figcaption></figure>`;
 return `<div class="screenshot-placeholder"><div class="placeholder-browser"><i></i><i></i><i></i></div><div class="placeholder-lines"><span></span><span></span><span></span></div><div class="placeholder-message">No screenshot supplied by the backend</div><small>${esc(label)}</small></div>`;
}
function openReview(id){
 const issue=data.issues.find(i=>String(i.id||i.issue_id)===String(id));if(!issue){toast("Issue details were not found in the current data.");return}
 currentReview=issue;navigate("review");
 const state=normalizeState(issue.state||issue.verification_state||issue.status);
 const before=issue.before_screenshot||issue.screenshot_url||issue.evidence_screenshot||issue.evidence?.before_screenshot||"";
 const after=issue.after_screenshot||issue.verification_screenshot||issue.evidence?.after_screenshot||"";
 $("#reviewContent").innerHTML=`<section class="surface review-main"><div class="review-title"><div><span class="eyebrow">${esc(issue.id||issue.issue_id||"ISSUE")}  ·  ${esc(issue.type||issue.issue_type||"Finding")}</span><h2>${esc(issue.title||"Untitled issue")}</h2></div>${badge(state)}</div><p class="review-description">${esc(issue.description||issue.summary||"No description provided.")}</p><div class="review-meta">${severity(issue.severity)}<span class="meta-pill">${esc(issue.viewport||issue.viewport_size||"Viewport unknown")}</span><span class="meta-pill">Scan: ${esc(issue.scan_id||"Not supplied")}</span></div><div class="review-section"><div class="section-heading"><div><span class="eyebrow">VISUAL EVIDENCE</span><h2>Before &amp; after</h2></div><span class="mini-label">Real backend images when available</span></div><div class="comparison-grid">${imagePanel(before,"Before")}${imagePanel(after,"After / verification")}</div><p class="image-caption">Missing screenshots are shown as placeholders, never replaced with invented evidence.</p></div><div class="review-section"><span class="eyebrow">PROPOSED CHANGE</span><h2>Suggested CSS</h2><pre class="css-proposal">${esc(issue.suggested_css||issue.proposed_css||"No CSS proposal supplied by the backend.")}</pre><p class="image-caption">Review this change before approval. This UI does not apply CSS directly to the target site.</p></div><div class="review-section"><span class="eyebrow">VERIFICATION OUTCOME</span><h2>Current result</h2><div class="verification-box state-${state}"><span class="verification-icon">${state==="verified"?"✓":state==="failed"?"!":state==="inconclusive"?"?":"•"}</span><div><b>${esc(issue.verification_outcome||stateMeta[state].label)}</b><p>${esc(issue.evidence||issue.verification_details||"No additional verification details supplied.")}</p></div></div></div><div class="review-actions" id="reviewActions"></div></section><aside class="surface review-aside"><span class="eyebrow">REVIEW CHECKLIST</span><h2>Before you approve</h2><ul class="checklist"><li><span>01</span><div><b>Confirm the issue</b><small>Check the viewport and supporting evidence.</small></div></li><li><span>02</span><div><b>Inspect the CSS</b><small>Make sure the proposal is scoped and safe.</small></div></li><li><span>03</span><div><b>Verify separately</b><small>Approval is not the same as a successful fix.</small></div></li></ul><div class="human-note"><b>Human approval required</b><p>Only a successful follow-up verification may move an issue to Verified.</p></div></aside>`;
 const actions=$("#reviewActions");
if (state === "proposed") actions.innerHTML = '<button class="button button-dark" id="approveFix">Approve proposal →</button><button class="button button-light" id="rejectFix">Reject proposal</button>';
else if (state === "applied") actions.innerHTML = '<button class="button button-dark" id="verifyFix">Run verification →</button>';

 else actions.innerHTML='<span class="action-note">Available actions depend on the current backend state.</span>';
}

async function reviewAction(action) {
  if (!currentReview) return;

  const id = currentReview.id || currentReview.issue_id;
  const buttons = $$("#reviewActions button");

  buttons.forEach(button => {
    button.disabled = true;
  });

  try {
    if (action === "approve") {
      await window.OmniSightAPI.approveFix(id);
    } else if (action === "reject") {
      await window.OmniSightAPI.rejectFix(id);
    } else if (action === "verify") {
      await window.OmniSightAPI.verifyFix(id);
    } else {
      return;
    }

    toast("Backend accepted the request. Reloading issue data.");
    await loadData();
    openReview(id);
  } catch (error) {
    toast(`Request failed: ${error.message}`);

    buttons.forEach(button => {
      button.disabled = false;
    });
  }
}
document.addEventListener("click",e=>{
 const page=e.target.closest("[data-page]");if(page){e.preventDefault();navigate(page.dataset.page);return}
 const review=e.target.closest("[data-review]");if(review){openReview(review.dataset.review);return}
 if (e.target.closest("#mobileMenu")) {
  const menuButton = $("#mobileMenu");
  const sidebar = $("#sidebar");
  const isOpen = sidebar.classList.toggle("open");

  menuButton.setAttribute("aria-expanded", String(isOpen));
  menuButton.setAttribute(
    "aria-label",
    isOpen ? "Close navigation" : "Open navigation"
  );
  return;
}
 if(e.target.closest("#refreshButton")){loadData();return}
 if(e.target.closest("#themeToggle")){document.body.classList.toggle("dark");return}
 if(e.target.closest("#backToIssues")){navigate("issues");return}
 if(e.target.closest("#approveFix")){reviewAction("approve");return}
 if(e.target.closest("#rejectFix")){reviewAction("reject");return}
 if(e.target.closest("#verifyFix")){reviewAction("verify");return}
 if(e.target.closest(".retry-button")){loadData();return}
});
$("#scanForm").addEventListener("submit",handleScan);
$("#statusFilter").addEventListener("change",renderIssues);
$("#globalSearch").addEventListener("input",()=>{if($("#globalSearch").value.trim())navigate("issues");renderIssues()});
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    $("#globalSearch").focus();
  }

  if (e.key === "Escape") {
    $("#sidebar").classList.remove("open");
    $("#mobileMenu").setAttribute("aria-expanded", "false");
    $("#mobileMenu").setAttribute("aria-label", "Open navigation");
  }
});
loadData();
})();
